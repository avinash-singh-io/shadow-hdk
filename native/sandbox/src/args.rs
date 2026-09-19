//! The helper's arguments — RED: the contract's tests, the parser to follow.

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
        let Command::Run { mode, roots, .. } = parsed(&["--mode", "read-only", "--", "true"]).unwrap()
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
}
