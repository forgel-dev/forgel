# Session State: Release audit: Localization does not satisfy the requirement that every reply follow the owner'

- Task: `20261123213155_release-audit-localization-does-not-sati`
- Session: 1
- Status: in progress

## Goal

Continue the task in the repository. The repository on disk is the source of
truth; re-read files with read_file when needed.

## Requirements

- The session determines the language of its answer from the owner's message: Russian for a Cyrillic message, French or Spanish when the message carries the words, diacritics or elisions characteristic of those languages, and English otherwise among Latin text.
- A message with no letters or no decisive language signal keeps the language the session is already using; a session that has not yet answered starts in English.
- The session's own wording — prompt, project line, task and release headings, plan headings, clarification messages, failure framing, next-step guidance, help and usage text, and the line shown when the session ends — exists in English, Russian, French and Spanish, and every composed sentence uses the wording of the current language.
- The set of composed strings is the same in all four languages: no composed element is missing from any of them, and no composed element is borrowed from another language while the owner's language is one of the four.
- The owner's sentence reaches the engine unaltered, and the engine's answer is shown as the engine returned it, so a model-composed answer is in the language the owner wrote in.
- Engine text that is not a model-composed answer — a refusal, a diagnostic or a raw error message — is never presented as the session's own wording: the session states the failure and the next step in the current language and shows the engine's own words as a distinctly marked quotation attributed to the engine.
- Engine-supplied data values — task identifiers, task states, versions, project keys — are shown as the engine reports them and are not translated.
- After a French message, every sentence the session composes is French and the engine's answer to that message is shown; the same holds for Spanish, Russian and English.
- A later message in another of the four languages changes the session's language before that reply is composed, and that reply and all following ones use the new language.
- When the engine fails under a non-English session, the failure line and the next step are in the owner's language and the engine's raw words appear only as the marked quotation.
- All previously delivered session behavior continues to hold unchanged: sentence intake, action selection, clarification, project switching, automatic state refresh, redaction and leaving the session.

## Acceptance Criteria

- A French owner message yields a reply in which every session-composed sentence is French and the engine's answer to that message is shown: no English session wording appears in it.
- A Spanish owner message yields a reply in which every session-composed sentence is Spanish and the engine's answer to that message is shown.
- A Russian owner message yields a reply in which every session-composed sentence is Russian and the engine's answer to that message is shown; the engine received that Russian sentence unaltered.
- An English owner message keeps every session-composed sentence English.
- The four languages carry the same set of composed strings, so no clarifying message, failure line, next-step hint or closing line is absent or borrowed from another language.
- A message without letters, sent after a French message, keeps French for the next reply.
- A French message sent after an English one produces a French reply and all following replies stay French until another language is signalled.
- An engine failure under a French session shows a French failure line and a French next step, and the engine's raw words appear only inside an attributed quotation.
- Engine-supplied values such as task identifiers, task states and versions appear exactly as the engine reported them under every supported language.
- All previously delivered behavior of the client still holds, proven by the client's existing verification passing unchanged.

## Constraints

- none

## Assumptions

- none

## Files Changed

- CHANGELOG.md
- README.md
- forgel_code/interactive.py
- forgel_code/languages.py
- tests/test_localization.py

## Actions

- run: ['python3', '-m', 'unittest', 'tests.test_interactive', '-v']
- read_file: forgel_code/engine.py
- read_file: forgel_code/commands.py
- read_file: forgel_code/cli.py
- write_file: forgel_code/interactive.py
- write_file: tests/test_localization.py
- run: ['python3', '-m', 'unittest', 'tests.test_localization', '-v']
- write_file: tests/test_localization.py
- run: ['python3', '-m', 'unittest', 'tests.test_localization', 'tests.test_interactive']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
- run: ['grep', '-rn', '-i', 'russian', 'README.md', 'CHANGELOG.md', 'forgel_code']
- read_file: README.md
- read_file: CHANGELOG.md
- write_file: README.md
- write_file: CHANGELOG.md
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
- write_file: README.md
- run: ['git', 'status', '--porcelain']
- run: ['git', 'diff', '--stat']
- write_file: forgel_code/languages.py

## Commands

- `['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']` -> exit 124
- `['python3', '-m', 'unittest', 'tests.test_interactive', '-v']` -> exit 0
- `['python3', '-m', 'unittest', 'tests.test_localization', '-v']` -> exit 1
- `['python3', '-m', 'unittest', 'tests.test_localization', 'tests.test_interactive']` -> exit 0
- `['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']` -> exit 0
- `['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']` -> exit 0
- `['git', 'status', '--porcelain']` -> exit 0
- `['git', 'diff', '--stat']` -> exit 0

## Recent Observations

- run git status --porcelain -> exit 0
- run git diff --stat -> exit 0
- write_file forgel_code/languages.py

## Next Step

Continue from the current repository state and the changed files.
