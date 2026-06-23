# ADRs (Architecture Decision Records)

*Why* a decision was taken — the context, the options weighed, and the choice. Short and **append-only**:
once accepted, an ADR is not rewritten; a later decision **supersedes** it with a new ADR. A design spec
argues *how/whether to build*; an ADR records the *decision* that came out of it.

## Index

| Doc                           | Status     | Owner | What it is              |
|-------------------------------|------------|-------|-------------------------|
| [ADR-NNNN <title>](<file>.md) | `<status>` | Name  | one-line summary of it. |

## Status lifecycle (required)

Each ADR lives at `docs/adr/ADR-<NNNN>-<YYYY-MM-DD>-<slug>.md` and opens with the **shared header** (see
[`../templates/doc-template.md`](../templates/doc-template.md)). Only the `Status` vocabulary is
ADR-specific:

| Status                   | Meaning                                                             |
|--------------------------|---------------------------------------------------------------------|
| `proposed`               | Written, under discussion; not yet decided.                         |
| `accepted`               | Decided and in effect.                                              |
| `superseded by ADR-NNNN` | Replaced by a later decision. Leave the doc in place; link forward. |

## Conventions

- **Numbering:** `ADR-<NNNN>` is sequential and **never reused** — the next ADR takes the highest existing
  number + 1. The number appears in the filename, the `# Title`, and the Index row.
- **Append-only:** don't rewrite an accepted ADR to reflect a new decision — write a new ADR and set the
  old one's `Status` to `superseded by ADR-NNNN`, with a `Related` link both ways.
- **One decision per ADR:** keep them small and focused so they can be superseded independently.
