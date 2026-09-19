//! The helper's arguments: one contract, parsed by hand so the binary carries no argument
//! library. The Python side (`adapters/environment/local.py`) is the only caller and builds
//! exactly this shape; a usage error is a bug on one side or the other, never a user's typo.

use std::ffi::OsString;
use std::fmt;
use std::path::PathBuf;

pub const USAGE: &str = "usage:\n  \
    shadow-hdk-linux-sandbox --mode read-only|workspace-write [--root <dir>]... -- <argv>...\n  \
    shadow-hdk-linux-sandbox --probe";

/// The environment's two confined modes. `full` never reaches the helper: the Python side hands
/// the argv through untouched for it.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    ReadOnly,
    WorkspaceWrite,
}

impl Mode {
    fn named(name: &str) -> Option<Self> {
        match name {
            "read-only" => Some(Mode::ReadOnly),
            "workspace-write" => Some(Mode::WorkspaceWrite),
            _ => None,
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
pub enum Command {
    /// Say what this kernel has, as one JSON line, and exit 0 or 120.
    Probe,
    /// Confine this process for `mode` with writes allowed beneath `roots`, then exec `argv`.
    Run {
        mode: Mode,
        roots: Vec<PathBuf>,
        argv: Vec<OsString>,
    },
}

/// A usage error: what was wrong, and the usage line after it. Exit 121.
#[derive(Debug)]
pub struct UsageError(String);

impl fmt::Display for UsageError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}\n{USAGE}", self.0)
    }
}

impl std::error::Error for UsageError {}

fn usage(what: impl Into<String>) -> UsageError {
    UsageError(what.into())
}

/// Parse the words after the program name.
pub fn parse<I>(words: I) -> Result<Command, UsageError>
where
    I: IntoIterator<Item = OsString>,
{
    let mut words = words.into_iter();
    let mut mode: Option<Mode> = None;
    let mut roots: Vec<PathBuf> = Vec::new();
    let mut probe = false;
    let mut argv: Option<Vec<OsString>> = None;

    while let Some(word) = words.next() {
        match word.to_str() {
            Some("--probe") => probe = true,
            Some("--mode") => {
                let value = words.next().ok_or_else(|| usage("--mode needs a value"))?;
                let name = value
                    .to_str()
                    .ok_or_else(|| usage("--mode needs a value"))?;
                mode = Some(Mode::named(name).ok_or_else(|| {
                    usage(format!(
                        "--mode {name:?} is not a confined mode: the modes are read-only and \
                         workspace-write (full never reaches the helper)"
                    ))
                })?);
            }
            Some("--root") => {
                let value = words
                    .next()
                    .ok_or_else(|| usage("--root needs a directory"))?;
                let root = PathBuf::from(value);
                if !root.is_absolute() {
                    return Err(usage(format!(
                        "--root {} is not absolute; the caller resolves roots",
                        root.display()
                    )));
                }
                roots.push(root);
            }
            Some("--") => {
                let rest: Vec<OsString> = words.by_ref().collect();
                if rest.is_empty() {
                    return Err(usage("nothing to run after --"));
                }
                argv = Some(rest);
                break;
            }
            _ => {
                return Err(usage(format!(
                    "unknown argument {:?}; the command comes after --",
                    word.to_string_lossy()
                )));
            }
        }
    }

    if probe {
        if mode.is_some() || !roots.is_empty() || argv.is_some() {
            return Err(usage("--probe stands alone"));
        }
        return Ok(Command::Probe);
    }
    let Some(argv) = argv else {
        return Err(usage("a command to run is required after --"));
    };
    let Some(mode) = mode else {
        return Err(usage("--mode is required"));
    };
    if mode == Mode::ReadOnly && !roots.is_empty() {
        return Err(usage(
            "--root is for workspace-write; read-only writes nowhere but the devices",
        ));
    }
    Ok(Command::Run { mode, roots, argv })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::OsString;
    use std::path::PathBuf;

    fn parsed(words: &[&str]) -> Result<Command, UsageError> {
        parse(words.iter().map(OsString::from))
    }

    #[test]
    fn probe_stands_alone() {
        assert!(matches!(parsed(&["--probe"]), Ok(Command::Probe)));
        assert!(parsed(&["--probe", "--", "true"]).is_err());
    }

    #[test]
    fn a_run_names_the_mode_every_root_and_the_command_after_the_dashes() {
        let command = parsed(&[
            "--mode",
            "workspace-write",
            "--root",
            "/a",
            "--root",
            "/b",
            "--",
            "sh",
            "-c",
            "true",
        ])
        .unwrap();
        let Command::Run { mode, roots, argv } = command else {
            panic!("not a run");
        };
        assert_eq!(mode, Mode::WorkspaceWrite);
        assert_eq!(roots, vec![PathBuf::from("/a"), PathBuf::from("/b")]);
        assert_eq!(argv, vec![OsString::from("sh"), "-c".into(), "true".into()]);
    }

    #[test]
    fn read_only_takes_no_root() {
        let Command::Run { mode, roots, .. } =
            parsed(&["--mode", "read-only", "--", "true"]).unwrap()
        else {
            panic!("not a run");
        };
        assert_eq!(mode, Mode::ReadOnly);
        assert!(roots.is_empty());
        let refused = parsed(&["--mode", "read-only", "--root", "/a", "--", "true"]).unwrap_err();
        assert!(refused.to_string().contains("--root"), "{refused}");
    }

    #[test]
    fn full_never_reaches_the_helper() {
        let refused = parsed(&["--mode", "full", "--", "true"]).unwrap_err();
        assert!(refused.to_string().contains("full"), "{refused}");
        assert!(refused.to_string().contains("read-only"), "{refused}");
    }

    #[test]
    fn a_relative_root_is_refused() {
        let refused =
            parsed(&["--mode", "workspace-write", "--root", "here", "--", "true"]).unwrap_err();
        assert!(refused.to_string().contains("absolute"), "{refused}");
    }

    #[test]
    fn the_command_is_required_and_so_are_the_dashes() {
        assert!(parsed(&["--mode", "workspace-write"]).is_err());
        assert!(parsed(&["--mode", "workspace-write", "--"]).is_err());
        assert!(parsed(&["--mode", "workspace-write", "true"]).is_err());
        assert!(parsed(&[]).is_err());
    }

    #[test]
    fn an_unknown_flag_and_a_missing_value_are_usage_errors_that_say_the_usage() {
        let unknown = parsed(&["--jail", "--", "true"]).unwrap_err();
        assert!(unknown.to_string().contains("--jail"), "{unknown}");
        assert!(unknown.to_string().contains("usage:"), "{unknown}");
        let missing = parsed(&["--mode"]).unwrap_err();
        assert!(missing.to_string().contains("--mode"), "{missing}");
    }

    #[test]
    fn the_mode_is_required_for_a_run() {
        let refused = parsed(&["--", "true"]).unwrap_err();
        assert!(refused.to_string().contains("--mode"), "{refused}");
    }

    #[test]
    fn the_words_after_the_dashes_are_the_commands_even_when_they_look_like_flags() {
        let Command::Run { argv, .. } =
            parsed(&["--mode", "read-only", "--", "ls", "--mode", "--"]).unwrap()
        else {
            panic!("not a run");
        };
        assert_eq!(
            argv,
            vec![OsString::from("ls"), "--mode".into(), "--".into()]
        );
    }
}
