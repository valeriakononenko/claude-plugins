<!-- docs:start -->
## Docs (docs/)

This project keeps structured documentation under `docs/`, managed by the `docs` skill.

**Before** working on an area, check `docs/` for context first — there may be a **design spec** (*why* it's
built this way), an **ADR** (a binding decision you must not silently break), a **runbook** (a known issue
and its fix), or a **guide** (the routine procedure). Reading the relevant doc first is usually faster and
safer than re-deriving it from the code.

**After** a change that implements, obsoletes, or otherwise acts on what a doc describes, update that doc in
the same change — bump its `Status` and `Last verified`, fix its README `Index` row, and bring the body to its
final state.

A branch (PR) is **one documentation session**: docs record the final state it delivers, not the route. What
was tried and dropped inside the branch is deleted from the doc, not annotated as reverted — unless you ask
to keep it as a rejected alternative. Motivation + end result, and written for a reader with no context:
short sentences, lists over paragraphs, no filler.

Find the right doc:

- **Taxonomy + file naming:** `docs/README.md` (the source of truth for doc types).
- **Browse by type:** the `## Index` table in each `docs/<type>/README.md`.
- **By module/scope:** `grep -rn '^- \*\*Module(s):' docs` then match the area you're touching.
- **By keyword:** `grep -rni '<keyword>' docs`.
<!-- docs:end -->
