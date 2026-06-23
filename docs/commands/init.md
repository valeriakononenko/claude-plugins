---
description: Scaffold a docs/ system (README, templates, default sections) into the current project.
argument-hint: "[target dir, default: docs]"
---

Scaffold the docs/ documentation system into this project. The plugin's source templates live under
`${CLAUDE_PLUGIN_ROOT}/templates/`.

Target docs directory: `$1` if given, otherwise `docs`.

Do this:

1. **Check state.** If the target dir already exists, do NOT overwrite anything — treat this as a
   gap-fill: only create the files/dirs that are missing, and report exactly what you added vs. left alone.

2. **Root README.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/docs-readme.md` to `<target>/README.md`. Replace
   `<project>` with the real project name (infer from the repo dir name or `package.json`/`Cargo.toml`/etc.;
   ask only if ambiguous).

3. **Templates.** Copy `${CLAUDE_PLUGIN_ROOT}/templates/doc-template.md` and
   `${CLAUDE_PLUGIN_ROOT}/templates/doc-section-template.md` into `<target>/templates/`.

4. **Default sections.** For each of `design`, `adr`, `runbooks`, `guides`: create `<target>/<type>/` and
   copy `${CLAUDE_PLUGIN_ROOT}/templates/sections/<type>.md` to `<target>/<type>/README.md`.

5. **CLAUDE.md pointer (AI navigation).** So Claude consults the docs while working, add a managed block to
   the project's root `CLAUDE.md` from `${CLAUDE_PLUGIN_ROOT}/templates/claude-md-block.md`:
   - If `CLAUDE.md` doesn't exist, create it with that block.
   - If it exists with a `<!-- docs:start -->`…`<!-- docs:end -->` block, **replace** the
     content between the markers (idempotent — never duplicate it).
   - If it exists without the markers, append the block.
   - If `<target>` is not the default `docs`, adjust the paths inside the block to point at `<target>/`.

6. **Report.** Print the resulting tree, note whether `CLAUDE.md` was created/updated/left alone, and remind
   the user that `<target>/README.md`'s "Doc types" list + the per-type READMEs are the taxonomy source of
   truth (no separate config file), and that they can add custom sections with `/docs:section`.

Keep all generated `.md` already-formatted: ≤120-col lines, aligned tables, no trailing whitespace. Do not
add code comments to anything outside the templates' existing HTML comments.
