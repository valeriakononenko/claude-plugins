# Docs

Project documentation for `<project>`.

## Doc types

Pick the directory by what the doc is *for*:

- **Design spec** (`design/`) — *how / whether to build* something: goal, constraints, approach. See
  [`design/README.md`](design/README.md).
- **ADR** (`adr/`) — *why* a decision was taken. Short, append-only; supersede rather than rewrite. See
  [`adr/README.md`](adr/README.md).
- **Runbook** (`runbooks/`) — *what to do when something is off the happy path*: incidents, one-off
  refactors, build-breaking quirks. See [`runbooks/README.md`](runbooks/README.md).
- **Guide** (`guides/`) — *how to do a routine, repeatable task*: local setup, deploy, regression.
  Evergreen, kept current. See [`guides/README.md`](guides/README.md).

<!-- Add custom sections here as one line each (dir, one-line purpose, link to its README), then create
     docs/<dir>/README.md from templates/doc-section-template.md. The skill reads this list to learn the
     project's doc taxonomy — this list + the per-type READMEs are the source of truth, there is no
     separate config file. -->

`templates/` is not a doc type — it holds reusable sources (see [Templates](#templates) below).

How to tell the doc types apart lives **here** in this file, not repeated in each type README. The section
order each `<type>/README.md` itself follows is captured in
[`templates/doc-section-template.md`](templates/doc-section-template.md).

## Templates

`templates/` holds reusable files that are consumed elsewhere (to start a new doc or a new section) — not
standalone docs, so they don't carry the doc header or a lifecycle:

- [`templates/doc-template.md`](templates/doc-template.md) — skeleton for a **single doc**
  (`<type>/<NNNN>-<created_at>-<slug>.md`): `# Title`, a one-line
  what-it-is, the shared metadata header, then the body. It carries the shared-header field rules every
  doc follows — identical field set, names, and order across all types; only the `Status` vocabulary
  differs per type.
- [`templates/doc-section-template.md`](templates/doc-section-template.md) — skeleton for a **type
  `README.md`** (`<type>/README.md`): the type's name + how it differs from the other types, the `Index`
  table, the `Status lifecycle` table, and any type-specific sections. The shared header is **not** repeated
  per type — it lives in `doc-template.md`. Fixes the section order every type README shares.

## File naming

Every doc is named `<NNNN>-<created_at>-<slug>.md`, the same rule for all types including ADRs. `<NNNN>` is
the doc's running number **within its type's folder**, zero-padded to 4 (`0001`, `0002`, …); `created_at` =
`YYYY-MM-DD`, the day it was first written (e.g. `0001-2026-06-16-cache-invalidation.md`). `<NNNN>` starts
at `0001` and is **sequential and never reused** — the next doc in that folder takes the highest existing
`<NNNN>` there + 1, regardless of date. List Index rows in `<NNNN>` order so the table reads in creation
order.

For ADRs the `<NNNN>` is also the ADR number that appears in the doc's title and index and is used for
cross-references and supersession (see [`adr/README.md`](adr/README.md)).
