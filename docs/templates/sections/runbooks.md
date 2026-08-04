# Runbooks

Step-by-step procedures and write-ups for work that takes the codebase meaningfully off the happy path:
incidents, silent-failure investigations, build-breaking quirks, and large cross-module refactors /
tech-debt. A runbook is *what to do when something is off*; a guide is *how to do a routine, repeatable
task*.

## Index

| Doc                  | Status     | Owner | What it is              |
|----------------------|------------|-------|-------------------------|
| [<title>](<file>.md) | `<status>` | Name  | one-line summary of it. |

## Status lifecycle (required)

Each runbook lives at `docs/runbooks/<NNNN>-<YYYY-MM-DD>-<slug>.md` (`<NNNN>` = its running number within
`runbooks/`, zero-padded to 4; date = when first written) and opens with the **shared header** (see
[`../templates/doc-template.md`](../templates/doc-template.md)). Only the `Status` vocabulary is
runbook-specific:

| Status           | Meaning                                                                                                                                                 |
|------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| `open`           | Diagnosed/written, remediation not yet started.                                                                                                         |
| `in PR #NNN`     | Fix is up for review; not merged.                                                                                                                       |
| `applied <date>` | Remediation merged/applied. For a runbook with several independent fixes, also append `— APPLIED <date> (PR #NNN)` to each section heading as it ships. |

Keep the header current — bump `Status` as work lands (e.g. `applied 2026-06-16 (PR #331)`) so the index
doubles as a quick state-of-play. `Owner` is the one person accountable for the runbook (the investigation,
or driving the remediation to `applied`); re-assign on handoff rather than leaving it stale.

## Body structure

After the header, a runbook lays out:

```markdown
# Runbook — <action / problem title>

## Symptom  (incidents)  / ## What this is  (refactors & reviews)

…

## Procedure / Stages

1. …

## Verification / Acceptance checklist

- [ ] …

## Related

Links to ADRs, related runbooks, tickets.

<!-- only from a later PR, and only if the motivation isn't in the diff — see Update notes below -->
## Update <YYYY-MM-DD>

- …
```

## Update notes

Runbooks are the **only** type that carries `## Update <YYYY-MM-DD>` notes — remediation keeps moving, so the
*why* behind a change is worth recording next to the procedure. A note is added only when that motivation
isn't readable from the diff: one per PR, motivation not changelog, ≤5 lines, bullet points preferred, newest
last. A runbook created in the same PR gets none. Full rules: `Update notes` in
[`../README.md`](../README.md).

## Writing style

A runbook is read by someone who has a problem right now — motivation and end state, as short as that can
be written:

- **No in-branch history.** A branch (PR) is one documentation session: what was tried and dropped inside it
  is deleted from the runbook, not annotated as reverted. Only a rejected alternative the user explicitly
  asks to keep stays, in a line or two with the reason.
- **No filler.** Plain language, short sentences, imperative steps. Drop restating the obvious, hedging, and
  "as we can see" narration.
- Prefer a list or a command block over a paragraph; keep a step to one action.

The shared rules these follow — `Writing style`, `One branch = one documentation session`, and
`Update notes` — live in [`../README.md`](../README.md).
