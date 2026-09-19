//! Confinement on Linux: Landlock for the filesystem (and TCP where the kernel has it), seccomp
//! for sockets, both applied by this process to itself — the field's shape (Codex's
//! `codex-linux-sandbox`), Epic 0010 D133 — and then `exec`. No namespaces, no root, no daemon:
//! Landlock is a kernel LSM any unprivileged process may apply to itself, which is what survives
//! Ubuntu 24.04's default AppArmor policy where bubblewrap's user namespace does not.
//!
//! **What this file decides and what it does not.** The *policy* — which mode allows what — is the
//! environment's, written in `adapters/environment/local.py` beside the seatbelt profile it
//! mirrors: reads everywhere (the interpreter must read its own installation), writes beneath the
//! roots for `workspace-write` and nowhere for `read-only`, the null, zero, random and terminal
//! devices writable in both because devices are not files (BUG-023), the network denied. This file
//! is the syscalls that make it so. The *proof* that it did — a write outside watched failing, a
//! socket watched refused, a write inside watched landing — is the Python side's (D36), before any
//! confined mode opens; nothing here is trusted for having run.

use std::collections::BTreeMap;
use std::fmt;
use std::path::{Path, PathBuf};

use landlock::{
    ABI, Access, AccessFs, AccessNet, CompatLevel, Compatible, Ruleset, RulesetAttr,
    RulesetCreatedAttr, RulesetStatus, path_beneath_rules,
};
use seccompiler::{
    BpfProgram, SeccompAction, SeccompCmpArgLen, SeccompCmpOp, SeccompCondition, SeccompFilter,
    SeccompRule, TargetArch,
};

use crate::args::Mode;

/// The Landlock ABI this helper is written against (Linux 6.10: `ioctl` on devices scoped). The
/// crate degrades best-effort on an older kernel — ABI 4 on Ubuntu 24.04's 6.8 — and the proof
/// on the Python side decides whether what remained is enough. The crate's own guidance: pick the
/// ABI you tested against at build time; never derive it from the running kernel.
const TARGET_ABI: ABI = ABI::V5;

/// `landlock_create_ruleset(NULL, 0, LANDLOCK_CREATE_RULESET_VERSION)` answers the ABI version.
const LANDLOCK_CREATE_RULESET_VERSION: u32 = 1;

/// Writable in every confined mode: writing to these changes nothing in the world, and `git`
/// opens `/dev/null` read-write at startup (BUG-023). `/dev/pts` is the terminal a command may
/// have been given; `/dev/ptmx` lets one allocate a pseudo-terminal of its own.
const DEVICES: [&str; 8] = [
    "/dev/null",
    "/dev/zero",
    "/dev/full",
    "/dev/random",
    "/dev/urandom",
    "/dev/tty",
    "/dev/ptmx",
    "/dev/pts",
];

/// What `--probe` reports: the kernel's ABI, and whether this helper can confine here.
pub struct Probe {
    pub landlock_abi: i32,
    pub supported: bool,
    pub why: Option<String>,
}

/// Why confinement could not be applied — the helper exits 120 with this on stderr.
#[derive(Debug)]
pub struct CannotConfine(String);

impl fmt::Display for CannotConfine {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl std::error::Error for CannotConfine {}

impl From<landlock::RulesetError> for CannotConfine {
    fn from(error: landlock::RulesetError) -> Self {
        CannotConfine(format!("Landlock: {error}"))
    }
}

impl From<seccompiler::Error> for CannotConfine {
    fn from(error: seccompiler::Error) -> Self {
        CannotConfine(format!("seccomp: {error}"))
    }
}

impl From<seccompiler::BackendError> for CannotConfine {
    fn from(error: seccompiler::BackendError) -> Self {
        CannotConfine(format!("seccomp: {error}"))
    }
}

/// The running kernel's Landlock ABI — 0 when Landlock is absent (`ENOSYS`) or built but not
/// enabled at boot (`EOPNOTSUPP`; `lsm=` without `landlock`).
pub fn kernel_abi() -> i32 {
    // SAFETY: a raw syscall with a null attribute pointer and size 0 is the documented way to ask
    // the kernel for its Landlock ABI version; it touches no memory of ours.
    let answered = unsafe {
        libc::syscall(
            libc::SYS_landlock_create_ruleset,
            std::ptr::null::<libc::c_void>(),
            0usize,
            LANDLOCK_CREATE_RULESET_VERSION,
        )
    };
    if answered < 0 { 0 } else { answered as i32 }
}

pub fn probe() -> Probe {
    let landlock_abi = kernel_abi();
    if landlock_abi < 1 {
        return Probe {
            landlock_abi,
            supported: false,
            why: Some(no_landlock()),
        };
    }
    match seccomp_filter() {
        Ok(_) => Probe {
            landlock_abi,
            supported: true,
            why: None,
        },
        Err(why) => Probe {
            landlock_abi,
            supported: false,
            why: Some(why.to_string()),
        },
    }
}

fn no_landlock() -> String {
    "this kernel has no Landlock — absent before Linux 5.13, or disabled at boot (`lsm=` without \
     `landlock`); bubblewrap is the fallback"
        .to_string()
}

/// Confine this process for `mode`, writes allowed beneath `roots`. Everything after this call
/// — including the `exec` — runs inside.
pub fn confine(mode: Mode, roots: &[PathBuf]) -> Result<(), CannotConfine> {
    if kernel_abi() < 1 {
        return Err(CannotConfine(no_landlock()));
    }
    let filter = seccomp_filter()?; // built before Landlock, so a filter that cannot be built
    landlock(mode, roots)?; // is found before anything was restricted
    seccompiler::apply_filter(&filter)?;
    Ok(())
}

fn landlock(mode: Mode, roots: &[PathBuf]) -> Result<(), CannotConfine> {
    // Every filesystem access right the ABI has is *handled*: what is not allowed by a rule below
    // is denied. TCP bind and connect are handled too where the kernel has them (ABI 4) and no
    // rule allows any port — seccomp denies the socket first; this is the second lock.
    let ruleset = Ruleset::default()
        .set_compatibility(CompatLevel::BestEffort)
        .handle_access(AccessFs::from_all(TARGET_ABI))?
        .handle_access(AccessNet::from_all(TARGET_ABI))?
        .create()?
        .add_rules(path_beneath_rules(["/"], AccessFs::from_read(TARGET_ABI)))?
        .add_rules(path_beneath_rules(
            existing(&DEVICES),
            AccessFs::from_all(TARGET_ABI),
        ))?;
    let ruleset = match mode {
        Mode::ReadOnly => ruleset,
        Mode::WorkspaceWrite => {
            ruleset.add_rules(path_beneath_rules(roots, AccessFs::from_all(TARGET_ABI)))?
        }
    };
    let status = ruleset.restrict_self()?;
    if status.ruleset == RulesetStatus::NotEnforced {
        return Err(CannotConfine(
            "Landlock did not enforce the ruleset on this kernel".to_string(),
        ));
    }
    if !status.no_new_privs {
        return Err(CannotConfine(
            "PR_SET_NO_NEW_PRIVS was not set; a setuid program could shed the sandbox".to_string(),
        ));
    }
    Ok(())
}

/// Paths that exist on this machine, so a missing device is not an error (a container without
/// `/dev/ptmx`, say) — `path_beneath_rules` skips them anyway; this keeps the intent explicit.
fn existing<'a>(paths: &'a [&'a str]) -> impl Iterator<Item = &'a Path> + 'a {
    paths.iter().map(Path::new).filter(|p| p.exists())
}

/// `socket()` with any domain but `AF_UNIX` fails with `EPERM`, and so does `io_uring_setup`:
/// io_uring can open and connect sockets without a `socket` syscall, so a filter that stopped at
/// `socket` would have stopped nothing. Everything else is allowed — the filter is about the
/// network, not about syscalls in general; the filesystem is Landlock's.
fn seccomp_filter() -> Result<BpfProgram, CannotConfine> {
    let arch = TargetArch::try_from(std::env::consts::ARCH)
        .map_err(|_| CannotConfine(format!("seccomp: no filter for {}", std::env::consts::ARCH)))?;
    let not_unix = SeccompRule::new(vec![SeccompCondition::new(
        0,
        SeccompCmpArgLen::Dword,
        SeccompCmpOp::Ne,
        libc::AF_UNIX as u64,
    )?])?;
    let rules: BTreeMap<i64, Vec<SeccompRule>> = BTreeMap::from([
        (libc::SYS_socket, vec![not_unix]),
        (libc::SYS_io_uring_setup, vec![]), // no condition: refused whatever the arguments
    ]);
    let filter = SeccompFilter::new(
        rules,
        SeccompAction::Allow,
        SeccompAction::Errno(libc::EPERM as u32),
        arch,
    )?;
    Ok(filter.try_into()?)
}
