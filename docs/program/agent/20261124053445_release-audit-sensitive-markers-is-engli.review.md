# Task Review: Release audit: `SENSITIVE_MARKERS` is English/Russian only. French/Spanish phrases such as `cré

- Task: `20261124053445_release-audit-sensitive-markers-is-engli`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-24T11:48:50+00:00

## Summary

The attributed change widens the session's sensitive-request guard to French and Spanish by adding an accent-, case- and whitespace-insensitive folding pass and a verb-stem + object-noun matcher for project creation, credential setting and configuration change; the audited phrases and their low-variation forms (other verb form, other word order, no diacritics) resolve to 'sensitive' before any engine call, while ordinary French/Spanish conversation still resolves to 'say'. English and Russian paths are untouched (the legacy SENSITIVE_MARKERS check still runs first and English-overlapping nouns are the ones already guarded), the refusal wording for French and Spanish now states the boundary and names the explicit client command `forgel-code` in the same style as the existing refusal (shown unmasked so the session's own wording is not mangled by the credential masker), and the CHANGELOG entry states the behavior without volatile implementation detail. Tests were extended with detection, refusal, no-passthrough and ordinary-conversation cases, and the two author-added style tests were replaced by command-naming tests covering the same refusal behavior. QA passed all acceptance checks; no unrelated, temporary or generated file is included.

## Requirements

- FR-1: A free-text input expressing a sensitive explicit action is refused and redirected in every accepted language, at minimum English, Russian, French and Spanish.: pass — resolve() keeps the English/Russian marker check and adds a folded French/Spanish check that returns kind 'sensitive' before any forwarding.
- FR-2: Covered actions are at least project creation, credential setting/defining and configuration/setting changes.: pass — SENSITIVE_ACTIONS pairs create/credential/configuration families; credential nouns are reachable from create, set and change verbs, configuration only from change verbs — matching the named families.
- FR-3: Common French and Spanish phrasings are detected, including 'crée un projet', 'crear un proyecto', 'définir le mot de passe' and 'cambiar la configuración'.: pass — Stems 'cree'/'crea', 'defin' and 'cambi' with nouns 'projet', 'proyecto', 'mot de passe' (multi-word sequence match) and 'configuracion'; all four are in the audited test tuples.
- FR-4: Detection covers ordinary variation in verb form and word order, not one fixed phrase per action.: pass — Prefix stems accept inflections and the matcher requires verb+noun anywhere in the sentence, so both orders work; tests cover 'créer', 'crea', 'crear', 'definis', 'un nouveau projet', 'un proyecto nuevo'.
- FR-5: Detection is insensitive to case, accents/diacritics and leading/trailing/repeated whitespace.: pass — _fold lower-cases, strips diacritics and collapses whitespace; test asserts folded equality for accented and whitespace-padded input and the no-diacritics variants are refused in tests.
- FR-6: A refused input is never passed onward to the engine's free-text entry.: pass — Sensitive resolution returns 'continue' after writing the message, before the engine call; the test asserts no 'say'/'use'/'task' call and no call containing the phrase.
- FR-7: The refusal tells the user the action is not performed from free text and points to the explicit commands, in the same style as the existing refusal.: pass — French and Spanish messages keep the opening boundary statement and add a pointer to the explicit `forgel-code` command with the three actions, mirroring the English/Russian wording pattern.
- FR-8: English and Russian detection produces exactly the results it produces today.: pass — The legacy SENSITIVE_MARKERS check runs first and is unchanged; the new matcher keys on Latin stems with French/Spanish nouns, and English words overlapping the noun lists ('token', 'password', 'secret', 'configuration') are already legacy markers, so no new English outcome arises; Cyrillic cannot match Latin stems.
- FR-9: Non-sensitive free text still reaches the engine unchanged in all four languages.: pass — Detection requires a verb stem and an object noun; ordinary greeting/question cases are asserted to resolve to 'say' and to reach the stub with the unchanged text.
- FR-10: Refusal and forwarding decisions are deterministic for the same input.: pass — resolve() is a pure function over constants and folded text; no randomness, ordering or state is involved.
- FR-11: The existing automated tests keep their expectations and pass.: pass — QA reports the local suite and environment checks passing; the only removed tests are the two style tests this same task added, replaced by the command-naming tests named in the justification.
- AC-6 (review-only): The refusal answer names the explicit commands for the requested action and reads in the existing style.: pass — Read directly: both messages state '... ne sont jamais exécutées à partir d'une phrase' / 'nunca se ejecutan a partir de una frase' and then name `forgel-code` together with creating a project, setting a password/token/key and changing the configuration, in the same construction as the pre-existing refusal.

## Blocking

- none

## Test Removals

- line:def test_a_french_refusal_reads_in_the_existing_style(self) -> None:
- line:def test_a_spanish_refusal_reads_in_the_existing_style(self) -> None:

- tests/test_localization.py::SensitiveRefusalTest::test_a_french_refusal_reads_in_the_existing_style: replaced -> tests/test_localization.py::SensitiveRefusalTest::test_a_french_refusal_names_the_explicit_commands
- tests/test_localization.py::SensitiveRefusalTest::test_a_spanish_refusal_reads_in_the_existing_style: replaced -> tests/test_localization.py::SensitiveRefusalTest::test_a_spanish_refusal_names_the_explicit_commands
