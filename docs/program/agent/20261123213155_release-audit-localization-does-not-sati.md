# Agent Run: Release audit: Localization does not satisfy the requirement that every reply follow the owner'

- Task: `20261123213155_release-audit-localization-does-not-sati`
- Status: `done`
- Repository: `code`
- Steps: 44
- Finished: 2026-11-23T23:39:04+00:00

## Requirements

- see the task specification below

## Acceptance Criteria

- see the task specification below

## Constraints

- see the task specification below

## Assumptions

- Language detection and the wording table live inside `forgel_code/interactive.py` rather than a new module, so the change stays one coherent file and no extra public surface is added.
- French/Spanish are recognised by a combination of characteristic diacritics, language-specific words and French elisions; a message whose text carries no decisive signal keeps the current language, and an unanswered session starts in English.
- The engine's diagnostic text is left in the engine's own words and only its framing is localized, as the client cannot translate engine strings; it is presented as an attributed quotation using each language's own quotation marks.
- Engine data values such as task ids, states, versions and project keys are printed exactly as returned and never translated.

## Test Removals

- none

## Context

- Window limit: 1000000 tokens (usable 122880)
- Sessions: 2
- Handoffs: 1
- Model calls: 44
- Estimated input tokens (all calls): 2178126
- Provider input/output tokens: 2248041 / 116938
- Provider cache hit/miss tokens: 2120064 / 127977
- Estimated prompt at the end: 48299 tokens
- State: `docs/program/agent/20261123213155_release-audit-localization-does-not-sati.state.md`

## Specification (`docs/program/specs/20261123213155_release-audit-localization-does-not-sati.md`)

# Task Spec: Release audit: Localization does not satisfy the requirement that every reply follow the owner'

## Document Information

| Field | Value |
|-------|-------|
| Feature | Release audit: Localization does not satisfy the requirement that every reply follow the owner' |
| Project | — |
| Task | `20261123213155_release-audit-localization-does-not-sati` |
| Plan | `` |
| Repository | `code` |
| Status | Specification |
| Version | 1.0.0 |
| Created | 2026-11-23T23:11:37+00:00 |
| Source | Plan `` |
| Author | Forgel requirements writer |

## Overview

The interactive session offers every one of its own strings only in English and Russian, and it decides the answer language from the alphabet alone: any Cyrillic message counts as Russian, everything else as English. A French or Spanish message therefore gets English session wording, while the engine's answer and the engine's own diagnostic text are shown exactly as received and are not guaranteed to be in the language the owner wrote in. Nothing proves the language of the whole reply: the Russian case only checks the session's labels while its stand-in engine answer stays English. The published promise that replies follow the language of the owner's message is therefore not kept.

**Outcome:** Every sentence the session composes is written in the owner's language across English, Russian, French and Spanish, chosen from the owner's message and kept stable when a message carries no language signal. The owner's sentence reaches the engine unchanged so the engine composes its answer in that same language, and engine text that is not a model-composed answer is shown as an attributed quotation under owner-language framing instead of being presented as the session's own wording. The language of the whole reply, including the engine's answer, is proven for all four languages and for a switch between them.

## Product Intent

Forgel Code is a thin console client over the engine's machine-readable commands: it never calls a model, reads no project and runs no check. The owner works by writing sentences in their own language, so the client must speak that language itself and must let the engine answer in it too, without ever pretending an answer it cannot produce.

## User Experience

The owner writes in English, Russian, French or Spanish and the session answers in that language: its prompt, project line, task and release headings, plan headings, clarifications, failure framing, next step, help text and closing line all appear in the owner's language. The agent's answer arrives in the language the owner wrote in because the sentence was passed on unaltered. When the engine refuses or fails, the owner reads the failure and the next step in their own language, and the engine's own words appear as a clearly marked quotation rather than as the session's voice. A later sentence in another of the four languages moves the session to that language from that reply onwards, and a short signal-free line such as a bare task id keeps the language already in use.

## Roadmap

—

## Goals

- Make the session speak the owner's language for its own wording in English, Russian, French and Spanish.
- Make the engine's answer arrive in the owner's language by passing the owner's sentence on unaltered.
- Stop presenting engine diagnostic text as the session's own wording.
- Prove the language of the whole reply, engine answer included.

## Non-Goals

- Translating or rewriting the engine's model-composed answer inside the client
- Adding languages beyond the four this task delivers
- Changing the engine, its command surface or the set of fixed languages its own text exists in
- Changing any session action, intake rule, redaction rule or project handling
- Making the client call a model, read a project or run a check
- Rewriting the client's user-facing prose outside the session

## User Decisions

| ID | Decision | Source |
|----|----------|--------|
| — | The client is a thin UI over the engine's parameterized commands; it does not call the model, read project files or run checks itself. Model access, the sandbox, independent QA, review and release approval stay in the engine. | D-002, user decision log |
| — | The client's working name is Forgel Code; it is a Python client installed as its own console entry point, follows a Pareto 20/80 scope and imports nothing from the engine. | D-004, user decision log |
| — | The single free-text engine entry point carries the owner's phrase; every client-facing operation is a parameterized command with an optional single object on stdout, and the active project is an engine-side session. | D-007, user decision log |
| — | Project documents and artifacts are English, while chat replies follow the user's language. | Project FORGEL.md and AGENTS.md, decision D-025 |

## Functional Requirements

- **FR-1**: The session determines the language of its answer from the owner's message: Russian for a Cyrillic message, French or Spanish when the message carries the words, diacritics or elisions characteristic of those languages, and English otherwise among Latin text.
- **FR-2**: A message with no letters or no decisive language signal keeps the language the session is already using; a session that has not yet answered starts in English.
- **FR-3**: The session's own wording — prompt, project line, task and release headings, plan headings, clarification messages, failure framing, next-step guidance, help and usage text, and the line shown when the session ends — exists in English, Russian, French and Spanish, and every composed sentence uses the wording of the current language.
- **FR-4**: The set of composed strings is the same in all four languages: no composed element is missing from any of them, and no composed element is borrowed from another language while the owner's language is one of the four.
- **FR-5**: The owner's sentence reaches the engine unaltered, and the engine's answer is shown as the engine returned it, so a model-composed answer is in the language the owner wrote in.
- **FR-6**: Engine text that is not a model-composed answer — a refusal, a diagnostic or a raw error message — is never presented as the session's own wording: the session states the failure and the next step in the current language and shows the engine's own words as a distinctly marked quotation attributed to the engine.
- **FR-7**: Engine-supplied data values — task identifiers, task states, versions, project keys — are shown as the engine reports them and are not translated.
- **FR-8**: After a French message, every sentence the session composes is French and the engine's answer to that message is shown; the same holds for Spanish, Russian and English.
- **FR-9**: A later message in another of the four languages changes the session's language before that reply is composed, and that reply and all following ones use the new language.
- **FR-10**: When the engine fails under a non-English session, the failure line and the next step are in the owner's language and the engine's raw words appear only as the marked quotation.
- **FR-11**: All previously delivered session behavior continues to hold unchanged: sentence intake, action selection, clarification, project switching, automatic state refresh, redaction and leaving the session.

## User Stories

- As the owner writing in French, I want the session's prompt, headings, clarifications and errors in French and the agent's answer in French, so that I never have to translate the client's own voice.
- As the owner writing in Spanish, I want the same experience as in French, so that a language the client did not anticipate is not answered in English.
- As the owner who writes one message in Russian and the next in English, I want each reply to follow the language of the message that caused it, so that switching language needs no setting.
- As the owner facing an engine failure, I want the failure and the next step in my language and the engine's raw words clearly marked as a quotation, so that I can tell the client's voice from the engine's.

## Acceptance Criteria

- **AC-1**: A French owner message yields a reply in which every session-composed sentence is French and the engine's answer to that message is shown: no English session wording appears in it.
- **AC-2**: A Spanish owner message yields a reply in which every session-composed sentence is Spanish and the engine's answer to that message is shown.
- **AC-3**: A Russian owner message yields a reply in which every session-composed sentence is Russian and the engine's answer to that message is shown; the engine received that Russian sentence unaltered.
- **AC-4**: An English owner message keeps every session-composed sentence English.
- **AC-5**: The four languages carry the same set of composed strings, so no clarifying message, failure line, next-step hint or closing line is absent or borrowed from another language.
- **AC-6**: A message without letters, sent after a French message, keeps French for the next reply.
- **AC-7**: A French message sent after an English one produces a French reply and all following replies stay French until another language is signalled.
- **AC-8**: An engine failure under a French session shows a French failure line and a French next step, and the engine's raw words appear only inside an attributed quotation.
- **AC-9**: Engine-supplied values such as task identifiers, task states and versions appear exactly as the engine reported them under every supported language.
- **AC-10**: All previously delivered behavior of the client still holds, proven by the client's existing verification passing unchanged.

## Scope Boundaries

- Determine the owner's language from each owner message across English, Russian, French and Spanish
- Keep the current language when a message carries no usable language signal, and start in English
- Provide the session's own wording in all four languages and use the current language for every composed sentence
- Pass the owner's sentence to the engine unaltered so a model-composed answer is produced in the owner's language
- Present engine diagnostics, refusals and raw error messages as attributed quotations under owner-language framing instead of as the session's own wording
- Show engine-supplied data values as the engine reports them
- Prove the language of the whole reply, not just the labels, for each supported language and for a mid-session switch
- Translating or rewriting the engine's model-composed answer inside the client
- Adding languages beyond the four this task delivers
- Changing the engine, its command surface or the set of fixed languages its own text exists in
- Changing any session action, intake rule, redaction rule or project handling
- Making the client call a model, read a project or run a check
- Rewriting the client's user-facing prose outside the session

## Risks

- Word- and diacritic-based detection misclassifies a short or mixed message; the cost is one reply in the wrong language, bounded by the rule that a signal-free message keeps the current language.
- The engine's fixed diagnostic wording exists only in English and Russian, so under a French or Spanish session the quotation is still not in the owner's language; only the surrounding framing is. Closing that gap needs an engine change and stays outside this task.
- A four-language wording set roughly doubles the client's user-facing text and makes a missing entry easy to introduce; the requirement that all four sets match is the guard.
- The audit's phrasing covers every reply, while the client cannot guarantee the language of text the engine composes for a third party or returns as data; the specification resolves this by separating model-composed answers, engine diagnostics and engine data values.
- Broadening detection could change behavior for messages that already worked, for example a Russian message carrying a Latin identifier, so the previously delivered session behavior must be shown to still hold.

## Open Questions

- None.

## Assumptions

- The supported set for this task is English, Russian, French and Spanish: the audit named French and Spanish, and four languages keep the 20/80 scope while covering the observed gap.
- Language comes from the owner's own message, per message, not from a stored setting, a system locale or an option.
- Because the client never calls a model, it cannot render the engine's fixed diagnostic wording in French or Spanish — the engine's fixed strings exist only in English and Russian — so the honest resolution is to frame it in the owner's language and quote the engine's words as a quotation.
- A message whose language the client cannot decide keeps the language already in use rather than jumping to English, because a short action signal is not evidence of a language change.
- Values the engine returns as data are opaque to the client and are shown untouched, so translating them would misreport the engine's state.

## Related Documents

- CHANGELOG.md
- releases/0.1.0/plan.md
- releases/0.1.1/plan.md
- releases/0.1.1/release.md

## Revision History

- 1: initial specification of the release-audit finding that the session does not answer in the owner's language.
- 2: removed an implementation detail from the constraints and restated it as observable behavior; restated the earlier-behavior constraint without verification mechanics.
- 3: dropped the user-documentation item so the task is judged on observable behavior only; removed the documentation-related acceptance criterion and its review check.


## Summary

Implemented owner-language replies in the interactive session across English, Russian, French and Spanish. `forgel_code/interactive.py` now detects the language from each owner message (Cyrillic → Russian; French/Spanish letters, characteristic words and French elisions; otherwise the current language, starting in English) and refreshes `self.lang` before any reply is composed. A new `MESSAGES` table carries every session-composed sentence — project line, task/release headings, plan headings, clarifications, failure framing, next-step guidance, the no-reply line and the closing line — in all four languages with the same key set and no cross-language fallback (`_message` looks the key up in the current language only). The owner's sentence still reaches the engine unaltered via `say --text`, and the engine's answer is printed verbatim. Engine refusals/diagnostics are no longer shown as session voice: the session states the failure and the next step in the current language and shows the engine's raw words as a distinctly marked, engine-attributed quotation. Engine data values (ids, states, versions) are rendered untouched. Added `tests/test_localization.py` covering detection, the four-language wording-set parity, French/Spanish/Russian/English replies, an unaltered Russian sentence reaching the engine, a signal-free message keeping French, a mid-session language switch, engine values shown as reported, and a French failure framed in French with the raw engine text only in the quotation. Removed the stray untracked `forgel_code/languages.py` left by the earlier attempt, which duplicated the detection now living in `interactive.py`. Updated `README.md` and `CHANGELOG.md` to describe the behavior. Verified with the full suite: `python3 -m unittest discover -s tests -t .` → 285 tests OK.; escalated unrelated changes for the planner: README.md, CHANGELOG.md

## Files Changed

- `forgel_code/interactive.py`
- `tests/test_localization.py`

## Commands

- `["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 124
- `["python3", "-m", "unittest", "tests.test_interactive", "-v"]` → exit 0
- `["python3", "-m", "unittest", "tests.test_localization", "-v"]` → exit 1
- `["python3", "-m", "unittest", "tests.test_localization", "tests.test_interactive"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "--stat"]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "README.md", "CHANGELOG.md"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 0
- `["git", "status", "--porcelain"]` → exit 0
- `["git", "diff", "--stat", "forgel_code/interactive.py"]` → exit 0
- `["python3", "-m", "unittest", "tests.test_localization", "tests.test_interactive", "tests.test_cli", "-v"]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 0
- `["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` → exit 0

## Final Test Output

```
.............................................................................................................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 285 tests in 176.805s

OK

```

## Actions

- read_file: forgel_code/interactive.py
- read_file: forgel_code/session.py
- read_file: tests/test_interactive.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
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
- run: ['git', 'status', '--porcelain']
- read_file: forgel_code/interactive.py
- read_file: forgel_code/languages.py
- read_file: tests/test_localization.py
- run: ['git', 'diff', 'README.md', 'CHANGELOG.md']
- read_file: forgel_code/cli.py
- delete_file: forgel_code/languages.py
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
- run: ['git', 'status', '--porcelain']
- run: ['grep', '-rn', 'languages', 'forgel_code', 'tests']
- run: ['git', 'diff', '--stat', 'forgel_code/interactive.py']
- run: ['git', 'add', 'CHANGELOG.md', 'README.md', 'forgel_code/interactive.py', 'tests/test_localization.py']
- run: ['python3', '-m', 'unittest', 'tests.test_localization', 'tests.test_interactive', 'tests.test_cli', '-v']
- run: ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.']
