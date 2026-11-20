# Release audit 20261120225130120934_forgel-code-0-1-0

- Round: 2
- Verdict: fail
- At: 2026-11-20T22:58:32+00:00

## Summary

The change set implements the test extra and metadata emission, and the test suite passes, but the README test-extra install URL points at v0.1.1 instead of the 0.1.0 release tag, so the documented install path is broken; minor documentation and lint issues remain.

## Findings

- [major] code: README's new test-extra install command points at `.../refs/tags/v0.1.1.tar.gz[test]`, while the release record, changelog and release id are 0.1.0 (`v0.1.0`). Users following the release docs will fetch a wrong or nonexistent tag, breaking the documented test-extra install path. — Change the URL to `v0.1.0` (or the actual published tag) and add a README-test assertion that the tag matches the package/release version so it cannot drift.
- [minor] code: README's new sentence says the checkout suite 'needs nothing but the Python standard library', but `tests/test_extras.py`'s `OfflineExtraInstallTest` calls `_pip_python()` and fails if no Python 3.9+ with pip is available, so the documented no-install command can fail on a stdlib-only interpreter. — Reword the claim to say no package installation is required, or make the pip test skip when pip is unavailable while keeping the offline install test in environments with pip.
- [minor] code: `_build_backend.py` adds `import re` but never uses it; this can fail the project's `make lint` check. — Remove the unused import or use it.
