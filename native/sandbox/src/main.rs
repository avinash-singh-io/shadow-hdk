//! `shadow-hdk-linux-sandbox` — the kit's Linux confinement helper (Epic 0010, D123, D133).
//!
//! Invoked by `LocalEnvironment` exactly as `sandbox-exec` is on macOS: it confines *itself* —
//! Landlock for the filesystem, seccomp for the network — and `exec`s the command, so there is
//! one process, in the leash's process group, exiting with the command's own code. The mode's
//! policy and the D36 proof stay on the Python side; this binary is the syscalls a child has to
//! make on itself before `exec`, which the parent cannot make for it.
//!
//! ```text
//! shadow-hdk-linux-sandbox --mode read-only|workspace-write [--root <dir>]... -- <argv>...
//! shadow-hdk-linux-sandbox --probe
//! ```
//!
//! Exit codes that are the helper's own: **120** it cannot confine (no Landlock; a ruleset the
//! kernel did not enforce; seccomp refused) — stderr says why; **121** usage; **126** / **127**
//! the command could not be executed / was not found. Anything else is the command's.

mod args;
#[cfg(target_os = "linux")]
mod linux;

use std::process::ExitCode;

use args::Command;

const NAME: &str = "shadow-hdk-linux-sandbox";
const VERSION: &str = env!("CARGO_PKG_VERSION");

const EXIT_CANNOT_CONFINE: u8 = 120;
const EXIT_USAGE: u8 = 121;
#[cfg(target_os = "linux")]
const EXIT_CANNOT_EXECUTE: u8 = 126;
#[cfg(target_os = "linux")]
const EXIT_NOT_FOUND: u8 = 127;

fn main() -> ExitCode {
    match args::parse(std::env::args_os().skip(1)) {
        Ok(command) => run(command),
        Err(usage) => {
            eprintln!("{NAME}: {usage}");
            ExitCode::from(EXIT_USAGE)
        }
    }
}

/// One JSON line, hand-written so the release binary carries no serialiser: three fields, the
/// Python side reads them with `json.loads`.
fn say_probe(landlock_abi: i32, supported: bool) {
    println!(
        "{{\"version\":\"{VERSION}\",\"landlock_abi\":{landlock_abi},\"supported\":{supported}}}"
    );
}

#[cfg(target_os = "linux")]
fn run(command: Command) -> ExitCode {
    use std::os::unix::process::CommandExt;

    match command {
        Command::Probe => {
            let probe = linux::probe();
            say_probe(probe.landlock_abi, probe.supported);
            match probe.why {
                None => ExitCode::SUCCESS,
                Some(why) => {
                    eprintln!("{NAME}: cannot confine: {why}");
                    ExitCode::from(EXIT_CANNOT_CONFINE)
                }
            }
        }
        Command::Run { mode, roots, argv } => {
            for root in &roots {
                if !root.is_dir() {
                    eprintln!(
                        "{NAME}: --root {} is not a directory\n{}",
                        root.display(),
                        args::USAGE
                    );
                    return ExitCode::from(EXIT_USAGE);
                }
            }
            if let Err(why) = linux::confine(mode, &roots) {
                eprintln!("{NAME}: cannot confine: {why}");
                return ExitCode::from(EXIT_CANNOT_CONFINE);
            }
            // `exec` replaces this process on success and returns only the failure: the
            // environment and the working directory are inherited untouched, `argv[0]` is
            // searched on `PATH` as a shell would.
            let failed = std::process::Command::new(&argv[0]).args(&argv[1..]).exec();
            eprintln!("{NAME}: cannot run {}: {failed}", argv[0].to_string_lossy());
            match failed.raw_os_error() {
                Some(libc::ENOENT) => ExitCode::from(EXIT_NOT_FOUND),
                _ => ExitCode::from(EXIT_CANNOT_EXECUTE),
            }
        }
    }
}

/// Off Linux the helper builds — so the crate lints, unit-tests and packages on every developer
/// machine and under `uv sync --all-packages` — and honours its contract by refusing: it cannot
/// confine here. macOS is `sandbox-exec`'s; Windows is Epic 0010 Phase 43's.
#[cfg(not(target_os = "linux"))]
fn run(command: Command) -> ExitCode {
    if command == Command::Probe {
        say_probe(0, false);
    }
    eprintln!(
        "{NAME}: cannot confine: this helper confines on Linux only ({} here)",
        std::env::consts::OS
    );
    ExitCode::from(EXIT_CANNOT_CONFINE)
}
