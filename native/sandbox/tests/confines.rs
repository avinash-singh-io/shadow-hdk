//! The helper watched denying and allowing on a Linux kernel (D36, D133). Compiled out
//! elsewhere: the crate builds on every OS so it can be linted and unit-tested, but only a Linux
//! kernel can prove what these assert. The `native` CI job runs them.
#![cfg(target_os = "linux")]

use std::path::{Path, PathBuf};
use std::process::{Command, Output};

const HELPER: &str = env!("CARGO_BIN_EXE_shadow-hdk-linux-sandbox");

fn probe() -> Output {
    Command::new(HELPER)
        .arg("--probe")
        .output()
        .expect("the helper runs")
}

/// The kernel this runs on has Landlock, or the helper says so and the rest cannot be proven here.
fn landlock_here() -> bool {
    let out = probe();
    match out.status.code() {
        Some(0) => true,
        Some(120) => {
            eprintln!("no Landlock on this kernel — the helper says so; the proofs below skip");
            false
        }
        other => panic!(
            "--probe exited {other:?}: {}",
            String::from_utf8_lossy(&out.stderr)
        ),
    }
}

fn run(mode: &str, roots: &[&Path], argv: &[&str]) -> Output {
    let mut command = Command::new(HELPER);
    command.arg("--mode").arg(mode);
    for root in roots {
        command.arg("--root").arg(root);
    }
    command.arg("--");
    command.args(argv);
    command.output().expect("the helper runs")
}

fn a_root() -> tempfile::TempDir {
    tempfile::Builder::new()
        .prefix("shadow-hdk-confines-")
        .tempdir()
        .unwrap()
}

fn shell(script: &str) -> Vec<&str> {
    vec!["sh", "-c", script]
}

#[test]
fn probe_reports_the_kernels_landlock_as_json() {
    let out = probe();
    let said: serde_json::Value = serde_json::from_slice(&out.stdout).expect("one JSON line");
    let abi = said["landlock_abi"].as_i64().expect("landlock_abi");
    let supported = said["supported"].as_bool().expect("supported");
    assert!(said["version"].as_str().is_some_and(|v| !v.is_empty()));
    match out.status.code() {
        Some(0) => assert!(supported && abi >= 1, "{said}"),
        Some(120) => assert!(!supported && abi == 0, "{said}"),
        other => panic!("exit {other:?}"),
    }
}

#[test]
fn a_write_inside_the_root_lands() {
    if !landlock_here() {
        return;
    }
    let root = a_root();
    let inside = root.path().join("inside.txt");
    let out = run(
        "workspace-write",
        &[root.path()],
        &shell(&format!("echo fine > {}", inside.display())),
    );
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    assert_eq!(std::fs::read_to_string(&inside).unwrap(), "fine\n");
}

#[test]
fn a_write_outside_the_root_is_denied_and_leaves_no_file() {
    if !landlock_here() {
        return;
    }
    let root = a_root();
    let elsewhere = a_root();
    let outside = elsewhere.path().join("escaped.txt");
    let out = run(
        "workspace-write",
        &[root.path()],
        &shell(&format!("echo bad > {}", outside.display())),
    );
    assert_ne!(out.status.code(), Some(0));
    assert!(
        !outside.exists(),
        "a confined command wrote outside the root"
    );
}

#[test]
fn every_root_is_writable_and_nothing_between_them() {
    if !landlock_here() {
        return;
    }
    let one = a_root();
    let two = a_root();
    let between = a_root();
    let script = format!(
        "echo 1 > {} && echo 2 > {}",
        one.path().join("a").display(),
        two.path().join("b").display()
    );
    let out = run(
        "workspace-write",
        &[one.path(), two.path()],
        &shell(&script),
    );
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    let out = run(
        "workspace-write",
        &[one.path(), two.path()],
        &shell(&format!("echo 3 > {}", between.path().join("c").display())),
    );
    assert_ne!(out.status.code(), Some(0));
    assert!(!between.path().join("c").exists());
}

#[test]
fn read_only_denies_a_write_in_the_root_and_allows_the_null_device() {
    if !landlock_here() {
        return;
    }
    let root = a_root();
    let inside = root.path().join("sneaky.txt");
    let out = run(
        "read-only",
        &[],
        &shell(&format!("echo x > {}", inside.display())),
    );
    assert_ne!(out.status.code(), Some(0));
    assert!(!inside.exists(), "read-only let a command write");
    // Devices are not files (BUG-023): `git` opens /dev/null read-write at startup.
    let out = run(
        "read-only",
        &[],
        &shell("echo x > /dev/null && cat /dev/null && echo ok"),
    );
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
    assert_eq!(String::from_utf8_lossy(&out.stdout).trim(), "ok");
}

#[test]
fn reads_are_open_everywhere() {
    if !landlock_here() {
        return;
    }
    let out = run(
        "read-only",
        &[],
        &shell("cat /etc/hostname > /dev/null && ls / > /dev/null"),
    );
    assert_eq!(
        out.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&out.stderr)
    );
}

fn python() -> Option<PathBuf> {
    ["python3", "python"].iter().find_map(|name| which(name))
}

fn which(name: &str) -> Option<PathBuf> {
    std::env::var_os("PATH").and_then(|paths| {
        std::env::split_paths(&paths)
            .map(|dir| dir.join(name))
            .find(|candidate| candidate.is_file())
    })
}

#[test]
fn an_internet_socket_is_refused_and_a_unix_socket_is_not() {
    if !landlock_here() {
        return;
    }
    let Some(python) = python() else {
        eprintln!("no python on PATH — the socket proof skips");
        return;
    };
    let python = python.to_string_lossy().into_owned();
    let root = a_root();
    let inet = run(
        "workspace-write",
        &[root.path()],
        &[
            &python,
            "-c",
            "import socket; socket.socket(socket.AF_INET); print('OPENED')",
        ],
    );
    assert_ne!(
        inet.status.code(),
        Some(0),
        "an internet socket opened inside the sandbox"
    );
    assert!(!String::from_utf8_lossy(&inet.stdout).contains("OPENED"));
    let inet6 = run(
        "workspace-write",
        &[root.path()],
        &[
            &python,
            "-c",
            "import socket; socket.socket(socket.AF_INET6); print('OPENED')",
        ],
    );
    assert_ne!(inet6.status.code(), Some(0));
    let unix = run(
        "workspace-write",
        &[root.path()],
        &[
            &python,
            "-c",
            "import socket; socket.socket(socket.AF_UNIX); print('OPENED')",
        ],
    );
    assert_eq!(
        unix.status.code(),
        Some(0),
        "{}",
        String::from_utf8_lossy(&unix.stderr)
    );
    let connect = run(
        "workspace-write",
        &[root.path()],
        &[
            &python,
            "-c",
            "import socket; s = socket.socket(); s.settimeout(2); \
             print('REACHED' if s.connect_ex(('127.0.0.1', 22)) == 0 else 'DENIED')",
        ],
    );
    assert!(!String::from_utf8_lossy(&connect.stdout).contains("REACHED"));
}

#[test]
fn io_uring_cannot_be_set_up() {
    if !landlock_here() {
        return;
    }
    let Some(python) = python() else {
        return;
    };
    let python = python.to_string_lossy().into_owned();
    let root = a_root();
    // io_uring would make sockets past seccomp; `io_uring_setup` is refused with EPERM.
    let script = "import ctypes, os, sys; libc = ctypes.CDLL(None, use_errno=True); \
                  nr = {'x86_64': 425, 'aarch64': 425}[os.uname().machine]; \
                  params = ctypes.create_string_buffer(120); \
                  r = libc.syscall(nr, 1, params); \
                  print('ERRNO', ctypes.get_errno() if r < 0 else 0)";
    let out = run("workspace-write", &[root.path()], &[&python, "-c", script]);
    let said = String::from_utf8_lossy(&out.stdout);
    assert!(
        said.contains("ERRNO 1"),
        "io_uring_setup was not refused with EPERM: {said}"
    );
}

#[test]
fn the_childs_exit_code_passes_through() {
    if !landlock_here() {
        return;
    }
    let root = a_root();
    let out = run("workspace-write", &[root.path()], &shell("exit 7"));
    assert_eq!(out.status.code(), Some(7));
}

#[test]
fn a_command_that_is_not_found_is_127_and_named() {
    if !landlock_here() {
        return;
    }
    let root = a_root();
    let out = run("workspace-write", &[root.path()], &["/no/such/binary"]);
    assert_eq!(out.status.code(), Some(127));
    assert!(String::from_utf8_lossy(&out.stderr).contains("/no/such/binary"));
}

#[test]
fn a_usage_error_is_121_and_says_the_usage() {
    let out = Command::new(HELPER)
        .args(["--mode", "full", "--", "true"])
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(121));
    assert!(String::from_utf8_lossy(&out.stderr).contains("usage:"));
}

#[test]
fn the_environment_and_the_working_directory_reach_the_child() {
    if !landlock_here() {
        return;
    }
    let root = a_root();
    let out = Command::new(HELPER)
        .args(["--mode", "workspace-write", "--root"])
        .arg(root.path())
        .args(["--", "sh", "-c", "echo $SHADOW_HDK_PROBE; pwd"])
        .env("SHADOW_HDK_PROBE", "carried")
        .current_dir(root.path())
        .output()
        .unwrap();
    let said = String::from_utf8_lossy(&out.stdout);
    assert!(said.contains("carried"), "{said}");
    assert!(
        said.contains(
            &root
                .path()
                .canonicalize()
                .unwrap()
                .to_string_lossy()
                .to_string()
        ),
        "{said}"
    );
}
