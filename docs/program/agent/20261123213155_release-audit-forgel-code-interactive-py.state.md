# Session State: Release audit: `forgel_code/interactive.py`'s `redact()` does not keep key material out of the

- Task: `20261123213155_release-audit-forgel-code-interactive-py`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- Masking means: for a recognized secret-bearing label, the value bound to that label is replaced by a single fixed mask marker while the label is preserved, so the original value does not appear anywhere in the displayed text.
- A value following a recognized secret keyword and a colon, with or without intervening whitespace, is masked.
- A value following a recognized secret keyword and an equals sign, with or without surrounding whitespace, is masked.
- A value following a recognized secret keyword and whitespace (the previously supported single-token form) continues to be masked.
- A value that follows a recognized secret keyword plus a colon or whitespace and then an authorization scheme word is masked; the scheme word may remain visible, the credential after it may not.
- Secret keywords are recognized in English and in Russian; a Russian secret label followed by a colon, an equals sign or whitespace masks its value exactly as an English label does.
- A compound label containing a secret keyword as one of its segments is treated as a secret-bearing label; the whole label may remain visible but its bound value is masked.
- Label recognition is case-insensitive, including for non-English labels.
- Text not bound to a recognized secret-bearing label is displayed unchanged, including ordinary sentences that merely contain the word for a secret without a bound value.
- The label text itself is preserved next to the mask so the user can tell what kind of value was hidden.
- Masking is applied to every engine reply and every engine error before it is shown in the session, with no path by which engine output reaches the screen unmasked.
- Masking already-masked text neither errors nor reveals a value, and masking empty or secret-free text returns it unchanged.
- Previously working session behavior continues to work, including the masking forms that already worked.

## Acceptance Criteria

- A message containing a secret label followed directly by a colon and a value is displayed with the value replaced by the mask marker and the value absent from the displayed text.
- A message containing a secret label, a colon, an authorization scheme word and a credential is displayed with the label and surrounding wording preserved and the credential replaced by the mask marker.
- A message containing a Russian secret label followed by a colon and a value is displayed with the value replaced by the mask marker.
- A message containing a compound label built from several segments, one of which is a secret keyword, joined to a value is displayed with the value replaced by the mask marker.
- A message containing a secret label joined to a value by an equals sign with no surrounding spaces is displayed with the value replaced by the mask marker.
- A message that merely mentions a secret word without binding a value to it is displayed unchanged.
- A message with no secret-bearing label is displayed byte-for-byte unchanged, including punctuation, spacing and wording.
- Masking the same message twice produces the same displayed result as masking it once, and masking empty text succeeds and yields empty text.
- Every engine reply and every engine error that reaches the session display is masked under these rules, with no displayed engine text bypassing masking.
- For each recognized form above, the secret value does not appear as a substring anywhere in what the user is shown for that message.
- Previously working session behavior does not regress.

## Constraints

- none

## Assumptions

- none

## Files Changed

- forgel_code/interactive.py

## Actions

- read_file: forgel_code/interactive.py
- read_file: tests/test_interactive.py
- read_file: forgel_code/session.py
- read_file: forgel_code/render.py
- read_file: forgel_code/engine.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py
- write_file: forgel_code/interactive.py

## Commands

- none

## Recent Observations

- write_file forgel_code/interactive.py
- write_file forgel_code/interactive.py
- write_file forgel_code/interactive.py

## Next Step

Continue from the current repository state and the changed files.
