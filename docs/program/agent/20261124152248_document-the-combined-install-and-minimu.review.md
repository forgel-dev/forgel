# Task Review: Document the combined install and minimum engine version

- Task: `20261124152248_document-the-combined-install-and-minimu`
- Project: `forgel-1d2bf685`
- Verdict: **PASS**
- Finished: 2026-11-25T15:58:17+00:00

## Summary

The change is documentation-only: README.md and CHANGELOG.md, both committed in one signed commit with nothing unrelated. The client front page now opens its install part with the single combined install action, states that it needs no option or follow-up step, drops the old precondition that the reader must supply the engine beforehand (the client-only route is reframed as the situation of an existing installation), documents the engine's own standalone install as a separate single-action path, names one concrete minimum supported engine version (0.1.0) with the refusal of an older engine, describes the repeat-install behaviour (install only when missing or strictly older, equal or newer left untouched, never downgraded), describes both the missing-engine and too-old-engine messages with their versions and remedy, and states that version output (plain and --json) and a diagnostic answer work without an engine while engine-backed commands fail with the actionable message. The added prose is behavioural, in English, has no step ordering, timing, duration, runtime bound or local-environment detail, and makes no promise about an unpublished release. The changelog entry under [Unreleased] -> Added covers the combined default install, the standalone engine install, the minimum supported engine version with its startup message, and the never-downgrade repeat-install behaviour. No tests were added, read or removed, consistent with the documentation-as-text rule, and no previously correct install statement was made false. No blocking defect was found.

## Requirements

- FR-1: The install part of the front page presents exactly one default install action before any other installation route and states it installs the engine and client together.: pass — The Install section opens with the combined statement and the single curl action; engine source, client-only, update and uninstall routes follow it.
- FR-2: The default install needs no additional option, flag or follow-up step.: pass — Stated explicitly: 'needs no option, flag or follow-up step'; the shown command is unqualified.
- FR-3: The page no longer requires the reader to obtain the engine themselves; an engine already required is framed as an existing installation.: pass — The old 'engine is then yours to supply ... before you use the client' precondition is replaced; the client-only route is described as the route for a reader whose engine is already in place.
- FR-4: The engine's standalone install is documented as a separate single-action path.: pass — New 'The engine on its own' subsection with the `forgel-install --source ... --install <version>` action, for a reader who wants the engine alone or already has the client.
- FR-5: One concrete minimum supported engine version is stated, with refusal of an older engine.: pass — 'The one minimum supported engine version is 0.1.0'; the client accepts that or newer and refuses engine-backed work below it.
- FR-6: The page states the repeat-install behaviour, including that an equal or newer engine is never taken backwards.: pass — Dedicated paragraph: client replaced, engine installed only when missing or strictly older, equal or newer left exactly as it is.
- FR-7: The missing-engine message is described as stating no engine was found, naming the minimum version and pointing at an install.: pass — The 'No engine' bullet names the engine, the 0.1.0 minimum and the combined install as the pointer.
- FR-8: The too-old-engine message is described as naming the found version and the minimum and pointing at the upgrade.: pass — The 'Too old' bullet states both the found and 0.1.0 minimum versions and points at re-running the combined install.
- FR-9: The page states that version and diagnostic output work without an engine while engine-backed commands fail with the message.: pass — Names `forgel-code --version`, `forgel-code --version --json` and the diagnostic answer `forgel-code --help`, then states every engine-backed command fails.
- FR-10: Statements are presented as shipped behaviour, with no internal structure, step ordering, timing, runtime bound, local environment or unpublished-release promise.: pass — The added prose is behavioural; the only version reference is the already published v0.2.0 installer URL.
- FR-11: Everything added is English and agrees with the shipped product; a disagreement is corrected in the documentation.: pass — Text is English and consistent with the rest of the page (installer name, source variable, declared minimum); no statement contradicts the retained install text.
- FR-12: The client's changelog gains an entry under unreleased changes covering the combined default install, the standalone engine install, the minimum supported engine version with its startup message, and the never-downgrade repeat install.: pass — One entry under [Unreleased] -> Added covers all four items.
- AC-1: The first installation route is a single action said to install engine and client together, with no other route before it.: pass — Verified by reading the Install section.
- AC-2: Nothing tells the reader to pre-install the engine in order to install the client.: pass — The former precondition is gone; the remaining statement about supplying an engine concerns engine-backed commands of an existing installation.
- AC-3: The engine's standalone install is documented as its own separate path.: pass — Own subsection and own command.
- AC-4: Exactly one concrete minimum supported engine version is stated together with the statement that an older engine is refused.: pass — 0.1.0 stated repeatedly and consistently; refusal stated.
- AC-5: The repeat-install paragraph states install only when missing or strictly older and that an equal or newer engine is left untouched.: pass — Present verbatim in behaviour terms.
- AC-6: Both startup messages are described and each is actionable.: pass — Missing-engine bullet names the minimum and an install; too-old bullet names found and minimum and an upgrade.
- AC-7: The page states version and diagnostic output work without an engine while engine-backed commands fail with the actionable message.: pass — Stated in the 'Engine version' subsection.
- AC-8: The added prose contains no internal structure, step ordering, timing, duration, runtime bound, local-environment detail or unpublished-release reference.: pass — Added prose is behaviour-only.
- AC-9: The changelog entry for unreleased changes covers all four user-visible items.: pass — Combined install, standalone engine install, minimum version with startup message, and never-downgrade repeat install are all present.
- AC-10: Every documented statement agrees with the shipped product and no previously correct install statement was made false.: pass — The rewritten install intro preserves the Python/pip requirement and the launcher/profile statements; no retained sentence contradicts the new install story.

## Blocking

- none

## Test Removals

- none


