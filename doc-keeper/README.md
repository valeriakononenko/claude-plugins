# doc-keeper

A Claude Code plugin that brings a consistent `docs/` documentation system to **any** project: scaffold the
layout, add your own doc sections, file plan outcomes under the right doc, and keep doc statuses honest.

## What it gives you

- A `docs/` tree with a root `README.md` as the **source of truth** for doc types, naming, and the shared
  header.
- Four default doc types — `design/`, `adr/`, `runbooks/`, `guides/` — each with its own README (purpose,
  `Index` table, `Status lifecycle`).
- Reusable `templates/` for new docs and new sections.
- A `docs` skill that keeps statuses honest, files plan outcomes, and fixes references on rename/move.

The taxonomy lives entirely in the READMEs — there is **no separate config file**. Adding a custom section
is: one line in `docs/README.md` + one new `docs/<type>/README.md`. The skill reads both and learns it.

## Install

This plugin is published from the `claude-plugins` marketplace (the parent repo). Add the marketplace, then
install:

```
/plugin marketplace add <path-or-url to claude-plugins>
/plugin install doc-keeper@claude-plugins
```

## Commands

| Command                         | What it does                                                          |
|---------------------------------|-----------------------------------------------------------------------|
| `/doc-keeper:init [dir]`        | Scaffold `docs/` (README, templates, default sections) into the repo. |
| `/doc-keeper:new <type> [slug]` | Create a doc from the template and register it in the type's Index.   |
| `/doc-keeper:section <dir>`     | Add a custom doc section with its own README and status vocabulary.   |
| `/doc-keeper:audit [scope]`     | Verify statuses, flag stale docs, find broken README links.           |
| `/doc-keeper:status [type]`     | Fast read-only one-line-per-doc status table.                         |

## The skill

The bundled `docs` skill activates automatically when you create/move/review docs, edit a header or status,
file a plan's outcome, or ask "what's outdated". It reads the taxonomy from the project's READMEs, so it
adapts to whatever sections that project has.
