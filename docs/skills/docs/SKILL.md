---
name: docs
description: >
  Track and maintain the repo documentation under docs/ (design specs, ADRs, runbooks, guides, and any
  custom sections) and its templates. Use whenever the user asks in plain language to write/create a doc of
  any type ("write a runbook for…", "add an ADR about…", "draft a design spec / guide for…", "document
  this"), or to move, rename, review, or audit a doc; when adding/updating a doc header, Status, Owner, or a
  type README Index; when adding a new doc section/type; when a code change may have made a doc's Status
  stale (e.g. a PR merged, a feature shipped, a file renamed); when filing the outcome of a plan under the
  right doc; or when the user asks to review docs / list doc statuses / check what's outdated.
---

# Tracking docs/

`docs/README.md` is the **source of truth** — read it first. It lists the doc types (the "Doc types"
section = this project's section set), the file-naming rules, and the shared header. Each
`docs/<type>/README.md` carries that type's `Status lifecycle` and any type-specific sections; the shared
header is defined once in `docs/templates/doc-template.md`, not repeated per type. There is
**no separate config file** — the taxonomy lives in these READMEs. This skill is the *procedure*; the
READMEs are the *spec*. Don't duplicate the spec here — if it changes, the READMEs win.

## Natural-language requests (no slash command needed)

The user does **not** need to invoke a command — act on plain-language requests by following the matching
procedure below. The `/docs:*` commands are just deterministic shortcuts for the same actions.

- "write a runbook for…", "add an ADR about…", "draft a guide / design spec for…", "document this" →
  *Creating a doc*, then write the body following that type's README structure.
- "add a new doc section / doc type for…" → *Adding a custom section*.
- "what docs are outdated / stale", "review the docs" → *Keeping statuses honest* (verify, don't trust).
- "list doc statuses", "show me the docs dashboard" → the *Audit helpers* status dump.
- "rename / move this doc" → *Renaming / moving a doc*.

When you create a doc from a plain-language request, also **write its body**, not just the header + Index
row — follow the body structure in that type's README (e.g. a runbook's Symptom / Procedure / Verification /
Related). Ask only for what you genuinely can't infer (e.g. the owner of a brand-new file).

**If `docs/` doesn't exist yet** (no `docs/README.md`), the project hasn't been scaffolded. Don't hand-roll
the tree — tell the user to run `/docs:init` first (it copies the templates and default sections from
the plugin), then proceed.

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

## Finding the right doc (AI navigation)

When working on the codebase, consult docs **before** re-deriving things from scratch — a doc may already
explain the *why* (design/ADR) or the *gotcha* (runbook). Find it fast without reading the whole tree:

- **Browse by type:** the `## Index` table in each `docs/<type>/README.md` (`Doc | Status | Owner | What it
  is`) — the quickest overview of what exists.
- **By module/scope:** `grep -rn '^- \*\*Module(s):' docs` then match the area you're touching. The
  `Module(s)` header field is the primary navigation key — keep it filled when creating docs.
- **By keyword:** `grep -rni '<keyword>' docs`.
- **Follow `Related`:** a doc's `Related` line links to the ADRs/runbooks/specs around it.

The project's `CLAUDE.md` carries a docs block pointing here (added by `/docs:init`), so this
"check docs first" habit stays in context even outside this skill.

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
   rule from its README. The same rule applies to every type including ADRs: `<NNNN>-<created_at>-<slug>`,
   `<NNNN>` = the doc's running number within that type's folder, zero-padded to 4 = highest existing
   `<NNNN>` in `docs/<type>/` + 1, never reused (starts at `0001`). For ADRs that `<NNNN>` is also the ADR
   number used in the title and cross-references.
2. Fill the header. **Owner = the real author** — derive from git, do NOT default to the current user:
   `git log --diff-filter=A --follow --format='%an <%ae>' -- <path> | tail -1`. Untracked/new file →
   confirm the owner with the user rather than assuming.
3. Add a row to that type's README `## Index` table (`Doc | Status | Owner | What it is`), in `<NNNN>`
   order — append a new doc at the end so the table stays in creation order.

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
  `Status` **and** `Last verified`, update its README Index row, and bring the body to its final state. For a
  **runbook** also consider an `## Update <date>` note, per the rules below; other types never get one. Steps
  an **earlier, already-merged** change made obsolete get annotated in place rather than deleted; steps this
  branch itself invalidated are simply deleted (see below).

## One branch = one documentation session

The branch (PR) you're on is a single documentation session — not the chat session, not the individual edit.
Docs record the **final** state that branch delivers, never the route to it:

1. Before editing a doc, see what this branch already did to it — that's your session so far, even if it was
   written in an earlier chat:
   ```bash
   base=$(git merge-base HEAD origin/HEAD 2>/dev/null || git merge-base HEAD main)
   git diff "$base" HEAD -- <doc>   # plus the unstaged working copy
   ```
2. If you documented something earlier in this branch and then changed course, **delete it from the doc** —
   don't leave it annotated as reverted, superseded, or "we initially tried". As far as the doc is
   concerned it never happened. Same for something the user decided not to implement after all.
3. Never write a session narrative ("first A, then B", "moved X and moved it back", "after review we…").
   Git carries that.
4. Only exception: the user explicitly asks to keep a **rejected approach** (typical for ADRs) — one or two
   lines, with the reason it lost. Not a diary of the attempt.
5. Applies to Update notes too: one note per branch, rewritten in place as the branch evolves.
6. What survives: the motivation and the end result. Nothing intermediate.

## Writing style

Write for a reader with **no context and no time** — a newcomer, or the same person mid-incident:

- Short sentences, plain language, no undefined jargon. Say what it is and why it matters in the first two
  lines; details after.
- Prefer a list, table, or command block over a paragraph; one action per step.
- Cut filler: no hedging, no restating the obvious, no narration.

Load-bearing for runbooks especially — they're read under pressure.

## Update notes (runbooks only, one per PR, motivation only)

`## Update <YYYY-MM-DD>` notes belong to **runbooks and nothing else** — remediation keeps moving, so *why it
moved* is worth recording next to it. Never add one to a design spec, ADR, guide, or custom-section doc:

- `design/` → bump `Status` (`poc` → `wip` → `staged` → `done`) and rewrite the body.
- `adr/` → append-only: a new ADR supersedes it; never patch a decision.
- `guides/` → evergreen: rewrite the steps in place and bump `Last verified`.
- custom sections → follow the same default (no notes) unless that section's README says otherwise.

In a runbook, keep notes rare and thin:

1. **Add one only if the motivation is worth recording** — the *why* behind the change that a reader can't
   get from `git diff`. If the diff speaks for itself, the runbook gets **no note**; just update the body and
   the header.
2. **One note per change-set (PR), not per edit.** Check the branch diff for this doc (see *One branch = one
   documentation session*) — if this branch already added a note, rewrite that note instead of adding another.
3. **A runbook created in this same PR gets no note.** Its body *is* the change; notes start with the next PR
   that touches it.
4. **Write the motivation, not the diff.** Why it changed / what forced it / what it now means for the
   reader. What exactly changed is already in git — never restate it.
5. **Bullet points preferred**, prose allowed; at most 5 lines either way. One trailing reference (PR #,
   issue) is fine.
6. Append at the end of the runbook, newest last.

Example note at the end of a runbook:

```markdown
## Update 2026-08-04

- Retry limit was hit in production, so the backoff described here no longer holds.
- Kept the manual fallback: the new path only covers idempotent calls (#412).
```

## Filing a plan's outcome under the right doc

When you produce or execute a plan, make it land in the docs:

1. **Map each work item to a doc type** using the *purpose* lines in `docs/README.md` (a build decision →
   `design/` or `adr/`; an off-happy-path fix → `runbooks/`; a routine procedure → `guides/`). Work with no
   home yet → create a stub via *Creating a doc* so there is always a doc to attribute it to.
2. **Record the outcome in the doc body** — what now holds, in final form. Only in a **runbook**, and only if
   the motivation isn't readable from the diff, add a dated `## Update <date>` note per *Update notes* above
   (one per PR, ≤5 lines; a runbook created in this same PR gets none). Plan items dropped along the way are
   not documented at all.
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
