# Guides

*How to do a routine, repeatable task*: local setup, build, deploy, release, regression. Evergreen —
written to be followed again and again, and kept current. A guide is the happy path; a runbook is what to
do when you fall off it.

## Index

| Doc                  | Status     | Owner | What it is              |
|----------------------|------------|-------|-------------------------|
| [<title>](<file>.md) | `<status>` | Name  | one-line summary of it. |

## Status lifecycle (required)

Each guide lives at `docs/guides/<NNNN>-<YYYY-MM-DD>-<slug>.md` (`<NNNN>` = its running number within
`guides/`, zero-padded to 4; date = when first written) and opens with the **shared header** (see
[`../templates/doc-template.md`](../templates/doc-template.md)). Only the `Status` vocabulary is
guide-specific:

| Status       | Meaning                                                                         |
|--------------|---------------------------------------------------------------------------------|
| `draft`      | Being written; not yet trustworthy to follow.                                   |
| `current`    | Verified and safe to follow. Bump `Last verified` each time you re-check it.    |
| `deprecated` | Superseded or no longer applicable. Keep it with a pointer to what replaces it. |

A guide's value is being correct — re-verify `current` guides periodically and bump `Last verified`. `Owner`
is the one person accountable for keeping the guide accurate; re-assign on handoff rather than leaving it
stale.
