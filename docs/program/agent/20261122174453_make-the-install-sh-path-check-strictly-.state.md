# Session State: Make the install.sh PATH check strictly bounded and keep the profile byte-identical on re-install

- Task: `20261122174453_make-the-install-sh-path-check-strictly-`
- Session: 3
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- The fresh-shell check runs under a hard time bound; when the bound elapses the checked shell process is sent a graceful termination signal, and after a short grace period is forcefully stopped together with any remaining process in its group.
- The timeout outcome is part of the success decision: a timed-out or signalled check is a failure and is never reported as a verified PATH.
- Success is declared only when the path reported by the fresh login shell for forgel-code exactly equals the launcher path the installer just wrote; any other path, an empty answer, a non-zero shell exit status or a timeout is a failure.
- On failure the installer prints a report that names the edited profile file, the login shell that was checked, the PATH block that was written and the PATH the fresh shell reported, and exits with a non-zero status.
- Temporary files created by the check live in a directory usable only by the current user (owner-only permissions), carry unpredictable names, and are removed on every outcome — success, mismatch, timeout and interruption.
- After the check finishes, no process started by it and no file created by it is left behind.
- A second install over the same profile leaves the file byte-identical to the file after the first install; repeated installs do not accumulate blank lines.
- Dropping the block restores the file content exactly as it was before the block was added, including whether the file ended with a trailing newline and the original file's existing final line.
- install.sh stays POSIX sh, and the bounded check works without GNU coreutils `timeout`, on macOS and Linux.
- Existing behaviour is preserved: login shell detection (including the macOS directory-service branch), profile selection, FORGEL_CODE_PROFILE, FORGEL_CODE_NO_MODIFY_PATH, idempotent --uninstall across candidate profiles including ~/.bashrc and FORGEL_CODE_PROFILE, --help, and exit code 2 for an unknown argument.
- Each fixed defect gets a test in the repository test suite; no existing test is weakened, deleted or loosened.
- The time bound is configurable through the existing FORGEL_CODE_TIMEOUT variable and has a default that keeps the installer usable when the variable is unset.

## Acceptance Criteria

- A check against a shell that never answers and ignores the graceful stop signal ends within a bounded time with a non-zero exit status and a report naming the profile file and the observed PATH.
- The shell-inspection test finishes, leaves no stray child process and leaves no temporary file or temporary directory behind.
- Installing twice over the same profile produces a file byte-identical to the file after the first install, and dropping the block restores the original content exactly.
- The full repository test suite passes, including the existing installer, shell-detection, opt-out, uninstall and packaging tests.
- Temporary files created by the check are not readable by other users and are absent after both a successful and a failed check.
- install.sh parses as POSIX sh and contains no invocation of GNU `timeout`.

## Constraints

- POSIX sh only; no dependency on GNU coreutils.
- No new documented environment variables; existing variables keep their meaning.
- Keep the current verification bound unless a documented reason forces a different value.
- User-facing output in English, matching the existing installer tone.
- All committed artifacts in English.

## Assumptions

- The whole fix stays inside install.sh and its tests; the client package and CHANGELOG are untouched.
- The verification bound stays at its current value; no new environment variable is added for it.
- The private temporary location is created under the system temporary directory with owner-only permissions and removed on every exit path.
- The release of the installer fix is re-checked and published by the normal release process after the fix is accepted; no version or tag is chosen here.

## Files Changed

- err.txt
- install.sh
- out.txt
- tests/test_install.py
- tests/test_zz_probe.py

## Actions

- read_file: install.sh
- recall
- read_file: tests/test_install.py
- read_file: tests/test_zz_probe.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_zz_probe.py', '-s']
- read_file: install.sh
- recall
- read_file: tests/test_install.py
- read_file: tests/test_zz_probe.py
- recall
- write_file: tests/test_zz_probe.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_zz_probe.py', '-s']
- write_file: install.sh
- read_file: tests/test_install.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install.py', '-k', 'ShellDetection or Watchdog or OptOut or Uninstall or ProfileOverride', '-x']
- read_file: tests/test_readme_install.py
- write_file: tests/test_install.py
- delete_file: tests/test_zz_probe.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_install.py', '-k', 'Bounded or ByteStability', '-x']
- write_file: tests/test_install.py

## Commands

- `['python', '-m', 'pytest', '-q', 'tests/test_install.py', '-x', '-k', 'InstallerTest']` -> exit 0
- `['python', '-m', 'pytest', '-q', 'tests/test_install.py', '-k', 'Watchdog or ShellDetection or OptOut or Uninstall or ProfileOverride']` -> exit 1
- `['python', '-m', 'pytest', '-q', 'tests/test_zz_probe.py', '-s']` -> exit 0
- `['python', '-m', 'pytest', '-q', 'tests/test_zz_probe.py', '-s']` -> exit 0
- `['python', '-m', 'pytest', '-q', 'tests/test_install.py', '-k', 'ShellDetection or Watchdog or OptOut or Uninstall or ProfileOverride', '-x']` -> exit 0
- `['python', '-m', 'pytest', '-q', 'tests/test_install.py', '-k', 'Bounded or ByteStability', '-x']` -> exit 1

## Recent Observations

- delete_file tests/test_zz_probe.py
- run python -m pytest -q tests/test_install.py -k 'Bounded or ByteStability' -x -> exit 1
- write_file tests/test_install.py

## Next Step

Continue from the current repository state and the changed files.
