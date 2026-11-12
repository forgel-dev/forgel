# Jurisdiction Packs

A jurisdiction pack is **data**, not code. The core's jurisdiction layer reads it,
injects default requirements into the spec, records the evidence, and lets the
human production gate decide.

The purpose is to make the default path easier: jurisdiction requirements that
are always needed should not be retyped for every project. A draft pack is
strictly better than an ignored jurisdiction. The layer informs; it does not
block.

## Statuses

| Status | Meaning | Production |
|---|---|---|
| `draft` | Structure exists; rules may be incomplete. | Allowed with the compliance acknowledgement |
| `reviewed` | A named reviewer filled and signed the pack. | Allowed; still not a legal guarantee |
| `expired` | The review date passed. | Allowed with the compliance acknowledgement |

## Format

```yaml
id: ru
version: 2026.11
status: reviewed          # draft | reviewed | expired
region: ru
effective_from: 2026-11-01
reviewed_by: "legal counsel"
review_due: 2027-11-01
data_residency: required
legal_sources:
  - id: ...
    title: ...
    url: ...
mandatory_requirements:
  - id: RU-PD-001
    title: ...
    applies_when: ...
    requirement: ...
    verification: deterministic   # deterministic | manual | legal_review
    evidence: ...
prohibitions: []
required_evidence: []
```

## Rules

- Rules are data, not prompts.
- Deterministic checks are preferred. Ambiguous cases go to human review.
- The LLM may explain a rule and map it to a requirement, but it never certifies
  compliance.
- A pack is **not legal advice**. The user is responsible for regulatory
  compliance.
- If no pack matches, the generic draft is used and the gap is recorded.
- The core never blocks production on a pack. Approving production requires an
  explicit acknowledgement of the compliance disclaimer.

## Compliance Disclaimer

Forgel is a software development tool, not a law firm. Jurisdiction packs are
draft guidance, may be incomplete or out of date, and are not legal advice.
Forgel does not warrant that any generated product complies with the laws of any
jurisdiction. The user is responsible for reviewing the jurisdiction
requirements and for regulatory compliance. Approving a production deploy
confirms that responsibility.

## M0

`ru.json` is a **draft skeleton** with categories only. It contains no legal
conclusions. Production is allowed with the disclaimer and human
acknowledgement.
