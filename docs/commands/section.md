---
description: Add a custom doc section (its own README, status vocabulary, naming) to docs/.
argument-hint: "<dir>"
---

Add a custom documentation section to this project's `docs/`. A section is a new doc type with its own
directory, README, status lifecycle, and naming rule.

Argument: `$1` = the directory/slug for the new section (kebab-case, e.g. `research`, `proposals`,
`postmortems`). If missing, ask for it.

First read `docs/README.md` so the new section fits the existing structure and you don't clash with an
existing type.

Gather (ask the user, suggest sensible defaults):

- **Name** — display heading for the type README (e.g. "Research notes").
- **Purpose** — one line: what this type is *for* and how it differs from the others.
- **Naming rule** — default `<NNNN>-<created_at>-<slug>` (`<NNNN>` = per-folder running number, zero-padded
  to 4); only change if there's a reason.
- **Status vocabulary** — the lifecycle values + meanings for this type.

Then do this:

1. Create `docs/$1/README.md` from `docs/templates/doc-section-template.md`, filling in the name, the
   one-paragraph "what it is / how it differs", the `Index` table skeleton, and the `Status lifecycle`
   table from the values gathered. Do **not** repeat the shared header in the section README — it lives in
   `docs/templates/doc-template.md`; only the `Status` vocabulary is this type's own.

2. Add one line for the new section to the "Doc types" list in `docs/README.md` (dir, one-line purpose,
   link to its README), placed sensibly among the existing entries.

3. Report the new section and note that the skill will pick it up automatically on the next run (the
   taxonomy lives in these READMEs — there's nothing else to register).

Keep everything ≤120-col, tables aligned, no trailing whitespace.
