# Task Review: Make the install.sh PATH check strictly bounded and keep the profile byte-identical on re-install

- Task: `20261122174453_make-the-install-sh-path-check-strictly-`
- Project: `forgel-1d2bf685`
- Verdict: **FAIL**
- Finished: 2026-11-22T18:34:35+00:00

## Summary

The install.sh work itself looks sound: the fresh-shell check is bounded by a watchdog implemented with POSIX sh primitives only (sleep + background job + `kill -TERM`, grace, `kill -KILL` on the process group/tree), the timeout is recorded before signalling so it deterministically wins the success decision (CHECK_STATUS=124), the bound is configurable through FORGEL_CODE_TIMEOUT with a ten-second default, the temporary directory is created with umask 077 under a random token and removed by cleanup_check, and the block append/removal pair was reworked with a separator comment plus trailing-newline detection so install/install and install/uninstall are byte-stable. All QA gates pass, including the hang test and `sh -n install.sh`. What blocks the change is repository hygiene: the attributed commit also adds `err.txt`, `out.txt` and `tests/test_zz_probe.py`, which are not in the specification's affected files (`install.sh`, `tests/test_install.py`, `tests/test_readme_install.py`) and are debug output / probe leftovers rather than product artifacts; `test_zz_probe.py` in particular is collected by the suite and adds a scratch module with a sort-order name next to the real installer tests.

## Requirements

- FR-1: The fresh-shell check runs under a hard time bound, sending a graceful stop at the bound and a forceful stop of the remaining process tree after a short grace period.: pass — bounded_run starts a watchdog subshell that counts up to the limit, writes the timed-out marker, calls signal_run TERM, sleeps VERIFY_GRACE, then signal_run KILL. signal_run signals the process group when the checked shell leads its own group and otherwise walks process_tree, so forked children are reached.
- FR-2: A timed-out or signalled check is a failure and never reported as a verified PATH.: pass — The marker file is created before the signals are delivered, so the main branch sees `[ -e "$timed_out" ]` deterministically and forces CHECK_STATUS=124; verify_profile can then only fail. The AC-1 hang test passes.
- FR-3: Success requires the reported path to exactly equal the launcher path just written; wrong path, empty answer, non-zero status or timeout is a failure.: pass — CHECK_COMMAND reports the resolved path with a prefix, and the parsed value is compared against LAUNCHER; a non-zero CHECK_STATUS or 124 short-circuits. Acceptance check for the wrong/never-answering shell passes.
- FR-4: On failure the installer prints the profile file, the checked login shell, the written PATH block and the observed PATH to stderr and exits non-zero.: pass — The failure path emits these fields on stderr and returns a non-zero status; the AC-1 check asserts the report names the profile file and the observed PATH.
- FR-5: Check temporary files live in an owner-only, unpredictably named directory and are removed on success, mismatch, timeout and interruption.: pass — create_check_dir uses `(umask 077 && mkdir -m 700 ...)` under $TMPDIR with a random_token derived from /dev/urandom, and cleanup_check rm -rf's it; the trap-driven interruption path calls the same cleanup_check.
- FR-6: No process started by the check and no file created by it is left behind.: pass — cleanup_check terminates and reaps the watcher and the checked child, signal_run KILL is applied again, and the directory is removed; the QA cleanup test (no stray child, no temp file or directory) passes.
- FR-7: A second install over the same profile leaves the file byte-identical to the file after the first install, with no accumulated blank lines.: pass — add_profile_block removes the previous block first and appends unconditionally through print_block, with no additional blank line; the byte-comparison test passes.
- FR-8: Dropping the block restores the file exactly, including whether the file ended with a trailing newline and the original final line.: pass — ends_with_newline records the terminator state, the awk rewrite suppresses the final terminator when the input had none, and MARKER_SEPARATOR records the no-final-newline case so both the separator line and its newline are removed with the block.
- FR-9: install.sh stays POSIX sh and the bounded check works without GNU coreutils timeout on macOS and Linux.: pass — The watchdog is built from sh background jobs, `sleep` and `kill`; no `timeout`/`gtimeout`/`setsid`/`flock` is invoked, in line with the stub dependency contract, and `sh -n install.sh` passes.
- FR-10: Existing behaviour is preserved (login shell detection incl. the dscl branch, profile selection, FORGEL_CODE_PROFILE, both opt-outs, idempotent --uninstall, --help, exit 2 on unknown argument).: pass — detect_login_shell, account_login_shell, profile_path, no_profile_edit, usage and the argument handling are untouched by the attributed diff; the existing installer and detection tests still pass.
- FR-11: Each fixed defect gets a test in the repository suite; no existing test is weakened, deleted or loosened.: pass — No test removal was detected and the diff does not relax existing assertions; the new bounded-check, cleanup, permission and byte-identical tests are added to tests/test_install.py. Note that an unrelated scratch module was also added (see blocking).
- FR-12: The time bound is configurable through the existing FORGEL_CODE_TIMEOUT with a usable default when unset.: pass — verify_limit accepts a positive integer FORGEL_CODE_TIMEOUT and falls back to DEFAULT_VERIFY_LIMIT=10 otherwise; VERIFY_GRACE=2 is the grace period.
- AC-4: The full repository test suite passes, including installer, shell-detection, opt-out, uninstall and packaging tests.: pass — Recorded as pass by the QA gate and by the `python -m pytest -q` acceptance command.
- Repository hygiene: the change touches only the files the specification attributes to the task and adds no scratch or debug artifacts to the repository.: fail — The attributed commit adds `err.txt` and `out.txt` at the repository root and `tests/test_zz_probe.py`. None of them is in the specification's Affected Files (install.sh, tests/test_install.py, tests/test_readme_install.py); they read as captured command output and a throwaway probe collected by the suite.

## Blocking

- Committed scratch artifacts: `err.txt`, `out.txt` and `tests/test_zz_probe.py` are added by the attributed commit but belong to no requirement and no affected file. They are debug output and probe leftovers in the public repository, and the probe module is collected by pytest as a test alongside the real installer tests. They must be deleted (or, if `test_zz_probe.py` is intended as coverage, it must be folded into tests/test_install.py with a real assertion).

## Test Removals

- none


