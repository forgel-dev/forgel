# Task Review: Release audit: Localization does not satisfy the requirement that every reply follow the owner'

- Task: `20261123213155_release-audit-localization-does-not-sati`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-23T23:46:44+00:00

## Summary

The attributed change implements the four-language session contract in forgel_code/interactive.py: the MESSAGES table now carries the identical key set in English, Russian, French and Spanish, language_of detects Russian by Cyrillic, French and Spanish by characteristic letters, words and elisions, keeps the current language when a message carries no word-like signal, and starts in English; the real engine error path now composes a localized failure line plus a localized next step and shows the engine's raw words as an attributed quotation instead of as the session's own voice, while the owner's sentence still reaches the engine unaltered and engine data values are passed through untouched. The new tests/test_localization.py exercises the French, Spanish, Russian and English replies, the unaltered passthrough, the signal-free continuation, the mid-session switch, the localized failure framing with the quoted raw text, and the equal key set across the four languages; the pre-existing suites (test_interactive, test_redact) are untouched and the environment test and e2e checks pass, so intake, action selection, clarification, project switching, state refresh, redaction and leaving the session are shown to still hold. The only uncommitted files are README.md and CHANGELOG.md, correctly escalated because revision 3 removed the user-documentation item from this task, and they are not part of the committed diff.

## Requirements

- FR-1: the session determines its answer language from the owner's message (Cyrillic -> Russian, French/Spanish words, diacritics or elisions, English otherwise among Latin text).: pass — language_of checks Cyrillic first, then counts French/Spanish letters, listed words and French elisions, and falls back to English for other Latin text; DetectionTest covers all four plus an elision.
- FR-2: a message with no letters or no decisive signal keeps the current language; a session that has not yet answered starts in English.: pass — language_of takes the current language as default 'en' and keeps it when no word-like signal is present; tests cover '123', 't-1', '?!' and the default English start.
- FR-3: the session's own prompt, project line, task and release headings, plan headings, clarification messages, failure framing, next step, help/usage text and closing line exist in all four languages and every composed sentence uses the current one.: pass — MESSAGES covers project/project_none, tasks/tasks_empty, release/release_unknown, plan/plan_item, all clarifications, sensitive, failure, engine_quote, next_step, no_reply and left in en/ru/fr/es; the prompt is the language-neutral 'forgel> ' and the session has no separate help prose.
- FR-4: the set of composed strings is the same in all four languages, with no missing or borrowed element.: pass — WordingSetTest asserts every key has exactly the en/ru/fr/es set with non-empty text, and that lookup in an unsupported language raises instead of borrowing another language.
- FR-5: the owner's sentence reaches the engine unaltered and the engine's answer is shown as returned.: pass — Tests assert the recorded argv equals ['say','--text',<owner sentence>,'--json'] and that the echoed engine answer appears in the reply.
- FR-6: engine refusals, diagnostics and raw errors are shown as a distinctly marked quotation attributed to the engine under owner-language framing.: pass — The failure key no longer interpolates raw engine text; failure, engine_quote and next_step are composed per language, and the French failure test checks the quotation line is the only place the raw words appear.
- FR-7: engine-supplied values (task ids, states, versions, project keys) are shown as reported and not translated.: pass — Values are passed through from the payload; test_engine_values_are_shown_as_the_engine_reported_them checks t-1, t-2, ready, done, 0.1.1 and open under a French session.
- FR-8: after a French message every composed sentence is French and the engine's answer is shown; same for Spanish, Russian and English.: pass — OwnerLanguageTest covers fr, es, ru and en replies, asserting the expected wording and the absence of the English wording for fr/es/ru.
- FR-9: a later message in another of the four languages changes the language before that reply is composed, and following replies use the new language.: pass — test_a_later_message_in_another_language_moves_the_session and test_following_replies_stay_in_the_signalled_language show the switch and its persistence; the signal-free continuation test shows stability.
- FR-10: under a non-English session an engine failure shows the failure line and next step in the owner's language with the raw words only in the marked quotation.: pass — FailureFramingTest drives a stderr failure under a French session and checks the French failure line, French next step, the French quotation marker, the absence of English framing and that the raw text occurs on exactly the quotation line.
- FR-11: previously delivered session behavior still holds (intake, action selection, clarification, project switching, state refresh, redaction, leaving).: pass — The attributed change does not alter intake, actions, clarifications, project handling or refresh; tests/test_interactive.py and tests/test_redact.py are unchanged and the environment test/e2e checks pass.
- AC-1: a French owner message yields only French session wording and shows the engine's answer.: pass — test_a_french_message_composes_every_sentence_in_french checks the French wording set, the absence of English wording, the echoed answer and the unaltered argv; the acceptance check also passed.
- AC-2: a Spanish owner message yields Spanish wording and shows the engine's answer.: pass — test_a_spanish_message_composes_every_sentence_in_spanish covers it.
- AC-3: a Russian owner message yields Russian wording, shows the engine's answer, and the engine received the Russian sentence unaltered.: pass — test_a_russian_message_reaches_the_engine_unaltered asserts the wording, the exact argv and the echoed answer.
- AC-4: an English owner message keeps every composed sentence English.: pass — test_an_english_message_keeps_every_sentence_english drives 'status' and checks the English wording set.
- AC-5: the four languages carry the same set of composed strings, so no clarification, failure line, next-step hint or closing line is missing or borrowed.: pass — WordingSetTest enforces the identical key set and the no-fallback lookup.
- AC-6: a message without letters, sent after a French message, keeps French.: pass — test_a_message_without_letters_keeps_the_current_language after FRENCH sends '123' and asserts French wording with no English wording afterwards.
- AC-7: a French message sent after an English one produces a French reply and following replies stay French until another language is signalled.: pass — test_a_later_message_in_another_language_moves_the_session and test_following_replies_stay_in_the_signalled_language show the switch and its persistence; the accepted residual risk covers a short or mixed message being classified once.
- AC-8: an engine failure under a French session shows a French failure line and next step, with the raw words only in the attributed quotation.: pass — FailureFramingTest asserts exactly that, including that the raw text occurs only on the quotation line and that English framing is absent.
- AC-9: engine-supplied values such as task ids, states and versions appear exactly as reported under every supported language.: pass — Values are never rewritten by the client; the test verifies the reported ids, states, version and release state under the French session.
- AC-10: all previously delivered client behavior still holds, proven by the existing verification passing unchanged.: pass — No test removal is attributed; tests/test_interactive.py and tests/test_redact.py are unchanged and the QA environment test and e2e checks pass.

## Blocking

- none

## Test Removals

- none


