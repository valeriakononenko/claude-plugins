---
description: Create a new doc of a given type from the template and register it in the type's Index.
argument-hint: "<type> [slug]"
---

Create a new doc. First read `docs/README.md` and `docs/<type>/README.md` to learn the naming rule and the
`Status` vocabulary for the requested type — never assume them.

Arguments: `$1` = doc type (e.g. `design`, `adr`, `runbooks`, `guides`, or a custom section); `$2` = optional
slug. If `$1` is missing or not a real section under `docs/`, list the available types from `docs/README.md`
and ask which one.

Do this:

1. **Resolve the filename** from the type's naming rule. The same rule applies to every type including
   `adr`: `<NNNN>-<created_at>-<slug>.md` where `created_at` is today (`YYYY-MM-DD`) and `<NNNN>` is the
   doc's running number within that type's folder, zero-padded to 4: the highest existing `<NNNN>` in
   `docs/<type>/` + 1, never reused (starts at `0001` for the first doc). For `adr`, that `<NNNN>` is also
   the ADR number written into the title and Index row. Derive the slug from `$2` or ask for a short title
   and kebab-case it.

2. **Create the file** by copying `docs/templates/doc-template.md` to `docs/<type>/<filename>`. Fill the
   header: today's date for `Date` and `Last verified`; a sensible starting `Status` from that type's
   lifecycle; leave `Module(s)`/`Related` as prompts if unknown.

3. **Owner = the real author**, derived from git, NOT the current user by default. For a brand-new file
   there is no git history yet, so confirm the intended owner with the user (offer the current git
   `user.name <user.email>` as the likely default but let them override).

4. **Register it**: add a row to `docs/<type>/README.md`'s `## Index` table
   (`Doc | Status | Owner | What it is`), keeping the table aligned. Insert it in `<NNNN>` order — for a new
   doc that means appending it at the end, so the table stays in creation order.

5. Report the path and remind the user to fill the body. Keep the file ≤120-col, no trailing whitespace.
