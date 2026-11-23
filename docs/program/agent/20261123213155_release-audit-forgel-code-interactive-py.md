# Agent Run: Release audit: `forgel_code/interactive.py`'s `redact()` does not keep key material out of the

- Task: `20261123213155_release-audit-forgel-code-interactive-py`
- Status: `done`
- Repository: `code`
- Steps: 11
- Finished: 2026-11-23T23:00:41+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- A value that starts with a separator character is not treated as a value, so the bare-label prose rule keeps deciding those cases.
- A quoted run is masked strictly between its quotes; for an unclosed quote the rest of the line after the opening quote is masked.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 1
- Handoffs: 0
- Model calls: 11
- Estimated input tokens (all calls): 345054
- Provider input/output tokens: 353935 / 31793
- Provider cache hit/miss tokens: 315136 / 38799
- Estimated prompt at the end: 45855 tokens
- State: not needed

## Specification (`docs/program/specs/20261123213155_release-audit-forgel-code-interactive-py.md`)

# Task Spec: Release audit: `forgel_code/interactive.py`'s `redact()` does not keep key material out of the

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: `forgel_code/interactive.py`'s `redact()` does not keep key material out of the |
| Project | — |
| Task | `20261123213155_release-audit-forgel-code-interactive-py` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T22:33:41+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The interactive session's key-material masking is unreliable. It recognises a secret only in a narrow shape: a label and its value must be joined in the one form the masking expects, and only the token immediately after the label is replaced. Separated forms, authorization schemes, quoted values, Russian secret labels, environment-style compound labels and generic key names therefore slip through or are only partly masked, so key material the owner typed or that the engine echoed back can appear in clear on the session screen. At the same time the masking has no stated boundary against ordinary prose, so a message that merely mentions a token or a password risks being altered or left free by guesswork rather than by a rule.

**Outcome:** The screen shows every secret-bearing form the client can display with its value replaced by one visible marker, while a sentence that merely talks about a token, password or secret is displayed byte-for-byte unchanged. The boundary between a bound value and ordinary prose is a single stated rule, and every listed form has exactly one expected outcome that no implementation has to guess.

## Product Intent

Forgel Code is a thin, human-facing display over the engine's own commands (D-002, D-004). Progress and answers must reach the owner faithfully, yet the screen must never become a leak of the key material the owner or the engine mentions.

## User Experience

The owner reads an engine reply, task list, release state or error message as the engine wrote it, except that a value bound to a secret label appears as [redacted]. A sentence such as 'Password updated.' or 'Secret rotation scheduled' reads unchanged, while 'set password swordfish' or 'the token abc' shows the value masked. The owner can share the screen without a value escaping, and still understands what the engine said.

## Roadmap

—

## Goals

- Every secret-bearing form the client can display is masked whole, with the surrounding text unchanged.
- The boundary between a bound value and ordinary prose is one stated rule, applied wherever the label occurs, so each listed form has exactly one expected outcome.
- Benign prose mentioning a token, password or secret is displayed byte-for-byte unchanged.
- An engine reply, task state or error that carries key material reaches the screen with no fragment of the value visible.
- Masking is stable under repetition and does not disturb the client's other behaviour.

## Non-Goals

- Changing how a sentence is interpreted and turned into an engine command
- Adding, removing or re-parameterising any engine operation
- Changing the wording of the marker as it appears elsewhere in the product
- Masking values that no secret label binds (versions, counts, project keys, greetings)
- Hunting for key material that carries no label at all
- Any change on the engine side; the engine still produces the text, the client still decides what reaches the screen
- Reading, storing, forwarding or validating the value; masking only rewrites text on its way to the screen

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself. | User decision log D-002, user 2026-11-16 18:31 |
| — | The client's working name is Forgel Code; it is installed as forgel-code, follows a Pareto 20/80 scope and imports nothing from the engine. | User decision log D-004, user accepted the proposal 2026-11-16 18:34 |

## Functional Requirements

- **FR-1**: A masked value is replaced by the single visible marker [redacted]. Everything else in the message - the label, its separator, the authorization scheme word, quotation marks, spaces, punctuation and line breaks - stays byte-for-byte identical.
- **FR-2**: A secret label is a case-insensitive word, or a compound whose segments are joined by '.', '_' or '-', in which at least one segment names key material: token, secret, password, passwd, passphrase, api key or apikey, credential, key, authorization, bearer; or which is a Russian word beginning with one of the stems парол-, секрет-, токен-, ключ-. A word that merely contains such a sequence inside itself is not a label.
- **FR-3**: After a label, one or more ':' or '=' characters, with or without surrounding spaces, bind the following value, and the whole value is masked. The value is the entire run of non-whitespace characters up to the next whitespace or the end of the line; when it begins with a quote character (", ', « or `), the value is the whole quoted run, including spaces, up to the matching closing quote or the end of the line.
- **FR-4**: A label followed by whitespace and then a quoted run binds that run even without a separator; the quoted content is masked and the quotation marks stay visible.
- **FR-5**: A recognised authorization scheme word (bearer, basic, digest, negotiate, ntlm, oauth, oauth2, jwt, hmac, hawk, apikey, sso, scram-sha-1, scram-sha-256, aws4-hmac-sha256) directly after a label or after its separator stays visible and the token after the scheme is masked; this holds with and without a separator and takes precedence over the bare-label rule, so the scheme word itself is never treated as a value.
- **FR-6**: A label followed only by whitespace binds the next word as a value and masks it, unless that word is recognised everyday prose. A word is recognised everyday prose when it belongs to the client's fixed vocabulary of common English and Russian function and narrative words (articles, prepositions, pronouns, conjunctions, auxiliaries and copulas, and the ordinary verbs and nouns used to narrate work), compared case-insensitively after ignoring trailing sentence punctuation, and it carries no key-material markers - no digits, no mixed case inside the word and no value punctuation. Any other word after a label is a bound value and is masked. This rule applies wherever the label appears in the sentence, at the start or in the middle.
- **FR-7**: A copula or auxiliary between a label and the following word is skipped when judging that word, and the copula itself stays visible; the word after it decides between prose and bound value by the same rule.
- **FR-8**: Sentences in which the word after a label is recognised everyday prose are displayed byte-for-byte unchanged; in particular, a password or secret that was updated, rotated or scheduled is not a value.
- **FR-9**: Words that are not recognised everyday prose after a bare label are masked wherever they occur, including 'token abc', 'токен abc123', 'the token abc' and 'set password swordfish'.
- **FR-10**: Masking is stable: text that already carries the marker is returned unchanged, a value is never masked twice, and the marker itself is never treated as a value to mask.
- **FR-11**: Every text the session displays - an engine reply, a task title, plan text, release state and engine error text - is masked by these rules before it reaches the screen, so no fragment of a bound value appears anywhere in the session output.
- **FR-12**: The session's other display and interpretation behaviour is unchanged, and the previously supported masking guarantees (separator-joined values, visible authorization scheme, Russian labels, compound labels, idempotence) keep holding.

## User Stories

- As the owner of a project, I want a value bound to a token, password or secret to appear as [redacted] on the session screen, so that I can share my screen or a transcript without leaking key material.
- As the owner, I want a sentence that merely reports that a password was updated or that a secret rotation is scheduled to read exactly as written, so that masking never hides the engine's actual message from me.
- As the owner, I want an engine reply or error that echoes key material to reach me masked, so that a careless engine message cannot leak a value into my terminal.

## Acceptance Criteria

- **AC-1**: Separator-bound values are masked whole: 'token:abc123' shows 'token:[redacted]', 'password: hunter2' shows 'password: [redacted]', 'password = hunter2' shows 'password = [redacted]', and 'password==hunter2' shows 'password==[redacted]'.
- **AC-2**: An authorization scheme stays visible and its credential is masked: 'Authorization: Bearer abc123' shows 'Authorization: Bearer [redacted]' and 'the token Bearer secretvalue' shows 'the token Bearer [redacted]'.
- **AC-3**: Russian and compound labels are masked: 'токен: abc123' shows 'токен: [redacted]', 'AWS_SECRET_ACCESS_KEY=abc' shows 'AWS_SECRET_ACCESS_KEY=[redacted]', and 'пароль: hunter2', 'db_password=hunter2', 'aws.secret.key: hunter2' and 'api-key=hunter2' each show their value as [redacted].
- **AC-4**: Benign prose is displayed byte-for-byte unchanged: 'Password updated.' and 'Secret rotation scheduled' come back identical, and so do 'the token is missing', 'rotate the password please', 'send the secret later', 'release: 0.1.1 open', an empty message and 'нажмите на кнопку (дважды)!'.
- **AC-5**: A bare label followed by a word that is not recognised everyday prose is masked wherever the label sits: 'token abc' shows 'token [redacted]', 'токен abc123' shows 'токен [redacted]', 'the token abc' shows 'the token [redacted]', and 'set password swordfish' shows 'set password [redacted]'.
- **AC-6**: A quoted value is masked whole with its quotation marks visible: 'password: "hunter2 and more"' shows 'password: "[redacted]"'.
- **AC-7**: Masking is idempotent: masking already-masked text returns it unchanged, and each masked result carries exactly one marker per masked value.
- **AC-8**: An engine reply, a task title and an engine error that contain a bound value reach the screen masked; a reply containing 'токен: abc123' and 'Authorization: Bearer abc123' shows neither value fragment anywhere in the session output.
- **AC-9**: No other behaviour changes: every behaviour that worked before this change still works afterwards.

## Scope Boundaries

- Structured recognition of secret-bearing text on the way to the screen: label, separator, authorization scheme, quoted value, Russian label, compound and environment-style label, generic key name
- One stated rule that separates a bound value from ordinary prose, applied wherever the label appears in the sentence
- Masking the whole bound value, not a fragment of it
- Masking applied consistently to every text the session shows, including engine replies, task and plan state, release state and error text
- Making each listed form demonstrable as an executable example in the client's own test area
- Changing how a sentence is interpreted and turned into an engine command
- Adding, removing or re-parameterising any engine operation
- Changing the wording of the marker as it appears elsewhere in the product
- Masking values that no secret label binds (versions, counts, project keys, greetings)
- Hunting for key material that carries no label at all
- Any change on the engine side; the engine still produces the text, the client still decides what reaches the screen
- Reading, storing, forwarding or validating the value; masking only rewrites text on its way to the screen

## Risks

- The decided rule trades a small amount of over-masking for safety: an everyday word missing from the recognised vocabulary makes a benign sentence mask the following word, which is visible noise but never a leak, and no required example depends on it.
- The illustrative shape heuristic and the required masking of 'abc' and 'swordfish' cannot both hold; the specification chooses the vocabulary rule, so anyone expecting the shape-based heuristic will see the extra masking as a defect.
- The engine belongs to another project and may shape its output differently over time; masking is defined over the displayed text, so such a difference is not observed here.
- An unquoted value containing spaces is masked only up to the first space, so the remainder of such a value stays visible; this matches the previously pinned behaviour but remains a known limit of a label-bound secret.
- Over-broad Russian stem matching may mask an ordinary Russian word that begins with a described stem, and an over-narrow vocabulary may mask a legitimate narrative word; both are accepted as the safe direction and are not pinned beyond the named examples.
- Applying masking to every displayed text (plan text, release state, errors) could change other behaviour if it is done unevenly, which is why the unchanged-behaviour criterion is part of acceptance.

## Open Questions

- None.

## Assumptions

- The defect's illustrative shape heuristic (mask only a token carrying digits, mixed case or value punctuation) cannot be the deciding rule, because it would leave 'abc' and 'swordfish' visible, which the required examples forbid; the deciding rule is therefore the prose vocabulary: a word after a bare label is a value unless it is a recognised everyday prose word that carries no key-material markers.
- 'Entire value rather than only the next token' is read as: a separator binds one whole value, and a quoted value is masked across its spaces; an unquoted value still ends at the first whitespace, because the session's existing behaviour masks only that run and keeps the following words.
- The marker text stays [redacted], because the screen already shows that word today and owners already read it that way.
- The prose vocabulary is finite and maintained by the client; the words that make the benign examples benign belong to it, and words like 'abc', 'swordfish' and 'hunter2' do not.
- Separator binding is unconditional after a separator, so 'Secret: rotation' is masked while 'Secret rotation scheduled' is not; the separator is what makes the binding explicit.
- Two adjacent labels in one message are handled one after another, each according to these rules.
- The quoted-run rule applies to the quote characters commonly used in English and Russian typing, and an unclosed quote masks to the end of the line.

## Related Documents

- FORGEL.md
- AGENTS.md
- README.md
- forgel_code/interactive.py
- tests/test_redact.py

## Revision History

- v1 - initial specification of the structured redactor.
- v2 - rewritten after rejection: the whitespace form's prose exemption and the bound-value rule are now one stated rule (a bare label binds the next word unless that word is recognised everyday prose carrying no key-material markers, applied wherever the label appears), and acceptance states both directions - 'Password updated.' and 'Secret rotation scheduled' unchanged, 'the token abc' and 'set password swordfish' masked - so no form has two expected outcomes.
- v3 - removed process and engineering wording from constraints, acceptance, risks and assumptions; the unchanged-behaviour statement is now expressed as behaviour rather than as a reference to an existing suite.


## Summary

Fixed the two remaining review failures in `redact()` and pinned both forms with executable tests. A quoted value is now masked only between its quotation marks, so the quote characters stay visible for every supported pair and for the bare-label form, and an unclosed quote keeps its opening quote while masking the rest of the line. A run of `:`/`=` separators (spaces included) is now consumed as visible text, so every separator character survives and only the following value is masked. `tests/test_redact.py` gained `test_a_quoted_value_is_masked_between_its_quotes`, `test_every_separator_character_stays_visible` and a one-marker-per-value test, and the existing idempotence test now covers the quoted form and `password==hunter2`. Verified with `python -m pytest -q tests/test_redact.py` (15 tests, 32 subtests, passed) and the full suite `python -m pytest -q` (270 passed, 187 subtests passed).

## Files Changed

- `forgel_code/interactive.py`
- `tests/test_redact.py`

## Commands

- `["python", "-m", "pytest", "-q", "tests/test_redact.py"]` → exit 0
- `["python", "-m", "pytest", "-q"]` → exit 0
- `["python", "-m", "pytest", "-q", "tests/test_redact.py"]` → exit 0

## Final Test Output

```
...............                          [100%]
15 passed, 32 subtests passed in 1.96s

```

## Actions

- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: forgel_code/interactive.py
- read_file: tests/test_redact.py
- write_file: forgel_code/interactive.py
- write_file: tests/test_redact.py
- run: ['python', '-m', 'pytest', '-q', 'tests/test_redact.py']
- run: ['python', '-m', 'pytest', '-q']
