---
name: docs
description: >
  Track and maintain the repo documentation under docs/ (design specs, ADRs, runbooks, guides, and any
  custom sections) and its templates. Use when creating, moving, renaming, reviewing, or auditing any doc;
  when adding/updating a doc header, Status, Owner, or a type README Index; when a code change may have made
  a doc's Status stale (e.g. a PR merged, a feature shipped, a file renamed); when filing the outcome of a
  plan under the right doc; or when the user asks to review docs / list doc statuses / check what's outdated.
---

# Tracking docs/

`docs/README.md` is the **source of truth** — read it first. It lists the doc types (the "Doc types"
section = this project's section set), the file-naming rules, and the shared header. Each
`docs/<type>/README.md` carries that type's `Status lifecycle` and any type-specific sections; the shared
header is defined once in `docs/templates/doc-template.md`, not repeated per type. There is
**no separate config file** — the taxonomy lives in these READMEs. This skill is the *procedure*; the
READMEs are the *spec*. Don't duplicate the spec here — if it changes, the READMEs win.

## Learn the taxonomy first

Before acting, read `docs/README.md` to get the section set and per-section purpose, then the relevant
`docs/<type>/README.md` for that type's `Status` vocabulary and naming rule. Custom sections work
automatically because you read them from the READMEs rather than assuming a fixed list. The default project
ships four types:

- `docs/design/` — *how/whether to build* (Status: `poc | wip | staged | done | abandoned`)
- `docs/adr/` — *why a decision was taken* (Status: `proposed | accepted | superseded by ADR-NNNN`)
- `docs/runbooks/` — *what to do off the happy path* (Status: `open | in PR #NNN | applied <date>`)
- `docs/guides/` — *routine repeatable how-to* (Status: `draft | current | deprecated`)
- `docs/templates/` — **not** a doc type: reusable sources with no header/lifecycle
  (`doc-template.md`, `doc-section-template.md`).

Always confirm against the actual READMEs — a project may have added, removed, or renamed sections.

## Shared header (identical fields/names/order across all types)

```
- **Date:**          when first written
- **Last verified:** when contents were last checked against reality   ← bump on every real review
- **Owner:**         exactly ONE accountable person, Name <email>
- **Status:**        type-specific value (read the type README)
- **Module(s):**     scope (free-text)
- **Related:**       links (free-text)
```

## Creating a doc

1. Copy `docs/templates/doc-template.md` to `docs/<type>/<naming>.md`, where `<naming>` follows that type's
   rule from its README (default `<created_at>-<slug>`; ADRs `ADR-<NNNN>-<created_at>-<slug>`, NNNN =
   highest existing + 1, never reused).
2. Fill the header. **Owner = the real author** — derive from git, do NOT default to the current user:
   `git log --diff-filter=A --follow --format='%an <%ae>' -- <path> | tail -1`. Untracked/new file →
   confirm the owner with the user rather than assuming.
3. Add a row to that type's README `## Index` table (`Doc | Status | Owner | What it is`).

## Adding a custom section

When the user wants a new doc type:

1. Create `docs/<dir>/README.md` from `docs/templates/doc-section-template.md`: fill the type name, how it
   differs from the others, the `Status lifecycle` table (its vocabulary), and the naming rule. Don't
   repeat the shared header — it's defined in `docs/templates/doc-template.md`.
2. Add one line for it to the "Doc types" list in `docs/README.md` (dir, one-line purpose, link to its
   README) so the taxonomy stays discoverable.
3. That's it — no other registration. The section is now part of the taxonomy you read on the next run.

## Keeping statuses honest (the load-bearing part)

A written Status reflects the moment it was written — **verify before trusting it**, especially when asked
"what's outdated":

- A `in PR #NNN` doc → check if the PR merged (`git log --oneline | grep '#NNN'`) and the code landed; if so
  it's `applied` (or `done`).
- A doc that names a symbol/file/flag → confirm it still exists before repeating the claim
  (`grep`/`git log`). Renamed/deleted → the doc is stale.
- A `staged`/`open` doc → check the code/infra signal it depends on actually hasn't changed.
- When a code change you just made (or learned shipped) implements, obsoletes, or otherwise acts on what a
  doc describes, update that doc **in the same change, proactively — without being asked**: bump its
  `Status` **and** `Last verified`, update its README Index row, and add a short dated `## Update <date>`
  note capturing what landed (version, PR #, test). Annotate any now-superseded steps rather than deleting
  them.

## Filing a plan's outcome under the right doc

When you produce or execute a plan, make it land in the docs:

1. **Map each work item to a doc type** using the *purpose* lines in `docs/README.md` (a build decision →
   `design/` or `adr/`; an off-happy-path fix → `runbooks/`; a routine procedure → `guides/`). Work with no
   home yet → create a stub via *Creating a doc* so there is always a doc to attribute it to.
2. **Record what was done** under the matching doc as a dated `## Update <date>` note (what landed: version,
   PR #, test) — append, don't rewrite history.
3. **Drive the status**: bump the doc's `Status` and `Last verified`, and update its README Index row. An
   `in PR #NNN` becomes `applied <date>` when the PR merges; a `wip` design becomes `done` when it ships.
4. Keep the plan artifact itself out of `docs/` (it's ephemeral); link to it from the doc's `Related` if
   useful.

## Renaming / moving a doc

`git mv` it, then re-grep and fix **every** reference — other docs, the type README Index, the root
`docs/README.md`, the repo `README.md`, `CLAUDE.md`, and any CI that points at the file:
`grep -rn '<old-name>' . --include='*.md' --include='*.yml' | grep -v node_modules`.

## Audit helpers

Dump every doc's Status + Owner:
```bash
for f in $(find docs -name '*.md' ! -name 'README.md' ! -path '*/templates/*'); do
  printf '%s\t%s\t%s\n' "${f#docs/}" \
    "$(grep -m1 -E '^- \*\*Status:\*\*' "$f" | sed -E 's/.*Status:\*\* *//')" \
    "$(grep -m1 -E '^- \*\*Owner:\*\*'  "$f" | sed -E 's/.*Owner:\*\* *//')"
done
```

Find broken local links in a README (run from the file's dir):
```bash
grep -oE '\]\([^)]+\)' <file>.md | sed -E 's/^\]\(//;s/\)$//' | while read -r l; do
  case "$l" in http*) continue;; esac; p="${l#./}"; p="${p%%#*}"
  test -e "$p" && echo "OK   $l" || echo "MISS $l"; done
```

## Before pushing

Reformat changed `.md` (the user runs IntelliJ Reformat, Option-Cmd-L). Author already-formatted:
≤120-col lines, aligned tables, no trailing whitespace.
