# Design specs

*How / whether to build* something: the goal, the constraints, the approach, and the trade-offs weighed.
A design spec is forward-looking — it argues for a direction before (or while) it is built. The *why* of a
single locked-in decision belongs in an ADR; *what to do off the happy path* belongs in a runbook.

## Index

| Doc                  | Status     | Owner | What it is              |
|----------------------|------------|-------|-------------------------|
| [<title>](<file>.md) | `<status>` | Name  | one-line summary of it. |

## Status lifecycle (required)

Each design spec lives at `docs/design/<YYYY-MM-DD>-<slug>.md` (date = when first written) and opens with
the **shared header** (see [`../templates/doc-template.md`](../templates/doc-template.md)). Only the
`Status` vocabulary is design-specific:

| Status      | Meaning                                                             |
|-------------|---------------------------------------------------------------------|
| `poc`       | Proof-of-concept / exploratory; not committed to.                   |
| `wip`       | Actively being designed or built.                                   |
| `staged`    | Designed and built, waiting to roll out / be enabled.               |
| `done`      | Shipped and in use; the spec reflects what was built.               |
| `abandoned` | Not pursued. Keep the doc with a short note on why, for the record. |

Keep the header current — bump `Status` as the work moves, and `Last verified` whenever you re-check the
spec against reality. `Owner` is the one person accountable for driving the design; re-assign on handoff
rather than leaving it stale.
