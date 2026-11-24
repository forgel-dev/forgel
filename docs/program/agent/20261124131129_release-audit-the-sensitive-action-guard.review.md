# Task Review: Release audit: The sensitive-action guard is incomplete for required explicit actions. `SENSITI

- Task: `20261124131129_release-audit-the-sensitive-action-guard`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-24T14:08:51+00:00

## Summary

The attributed change closes the audit gap in the free-text sensitive-action guard and is internally consistent. `forgel_code/interactive.py` gains a second, clearly separated family of English/Russian verb+object patterns (`SENSITIVE_EN_RU_ACTIONS`) checked by `_asks_for_explicit_action` from `resolve`, so bare key wording (`key`/`ключ` without a credential term), bare configuration wording (`config`, `preferences`, `settings`, `конфиг`/`настройк`/`параметры`), and scaffolding wording (`scaffold`, `bootstrap`, `init`, `generate`, `заскаффолди`, `каркас`) are now refused, while the pre-existing marker and four-language guards are untouched, so no earlier refusal is lost or narrowed; a sentence that names only the object without an action verb still falls through to the engine, which is what the ordinary-conversation tests exercise. The English and Russian refusal wording is extended to state that the action needs the explicit operation and to name the client's own `forgel-code` command together with the actions it performs, following the same per-language `MESSAGES` mechanism already used for the interface language, and the French/Spanish wording is left as it was. `tests/test_sensitive_actions.py` drives every listed form of the three categories in both languages through the session over a logging stand-in engine, asserts the refusal, that the refusal names `forgel-code`, and that no request reaches the engine, and also pins ordinary conversational lines that must still pass through; no test is deleted or weakened and the full suite passes per QA. `CHANGELOG.md` carries one behaviour-level release note for the change. The verb+object co-occurrence style is the design already accepted for the four-language guard in the same module, so it is not a requirement violation here.

## Requirements

- A free-text request that asks to create, set or change key material is refused, including the bare key wording, in English and Russian.: pass — KEY_NOUNS/KEY_NOUN_STEMS are paired with the changing (incl. creating) verbs; 'create a key', 'set the key', 'put a new key here', 'создай ключ', 'задай ключ', 'смени ключ' are all covered, with credential-term forms still caught by the pre-existing markers.
- A free-text request that asks to change configuration is refused, including the bare configuration wording, in English and Russian.: pass — CONFIGURATION_NOUNS/STEMS cover config, configuration, preferences, settings and конфиг/настройк/опци/предпочтени/параметр against the change verbs; the listed English and Russian forms resolve to the sensitive kind.
- A free-text request that asks to create or scaffold a project is refused, including the bare scaffolding wording, in English and Russian.: pass — SCAFFOLD_NOUNS/STEMS (project, проект, каркас, скелет, шаблон, заготовк, болванк) are paired with the creating verbs only, so scaffolding wording such as 'scaffold a project', 'init a project', 'заскаффолди проект', 'сгенерируй каркас' is refused.
- A refused request is not sent to the engine and reports no action result.: pass — The sensitive kind is returned from resolve() before any command mapping, so no engine request is produced; the e2e acceptance check for the configuration case passed and the new tests observe the stand-in engine's request log.
- The refusal tells the user the action needs the explicit operation and names the operation to use.: pass — The English and Russian sensitive message now states that the actions are never carried out from a sentence and names the client's own explicit command `forgel-code` with the actions it performs; the tests assert the named operation is present.
- The refusal is presented in the interface language of the session.: pass — The message continues to come from the per-language MESSAGES table selected by the existing language mechanism; the change only rewrites the en and ru variants and leaves fr/es intact.
- Requests outside the guarded categories are still forwarded as before and no existing refusal is narrowed or lost.: pass — SENSITIVE_MARKERS, SENSITIVE_ACTIONS and the French/Spanish branch are unchanged and the new check is additive; sentences that name only a key, the configuration or a project without an action verb still fall through, and the ordinary lines in the new tests reach the engine.
- Automated tests assert, for every recognized form in each covered language and category, that the request is refused and that no engine request is made.: pass — tests/test_sensitive_actions.py enumerates key material, configuration and project forms in English and Russian, drives them through the session over a stub engine that logs every argv, and asserts both the refusal (including the named `forgel-code` operation) and the absence of a passthrough.
- The existing test suite passes unchanged in meaning; no test is weakened or deleted.: pass — No test removal was detected in the attributed commit, the new file is purely additive, and QA reports the full suite passing.
- Release notes describe the change at behaviour level.: pass — One CHANGELOG entry under Unreleased/Fixed describes the recognised wording, the in-session refusal, the no-passthrough guarantee and the named explicit command, without volatile implementation detail.

## Blocking

- none

## Test Removals

- none


