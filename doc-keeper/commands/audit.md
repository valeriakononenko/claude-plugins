---
description: Audit all docs — report statuses, flag stale ones, find broken README links.
argument-hint: "[type or path, default: all]"
---

Audit the project's documentation for staleness and broken references. Scope: `$1` if given (a type dir or
a path), otherwise all of `docs/`.

First read `docs/README.md` to learn the section set and each type's `Status` vocabulary.

Run the audit:

1. **Status + Owner dump.** For every doc (excluding `README.md` and `templates/`), collect its `Status`,
   `Owner`, and `Last verified`:
   ```bash
   for f in $(find docs -name '*.md' ! -name 'README.md' ! -path '*/templates/*'); do
     printf '%s\t%s\t%s\n' "${f#docs/}" \
       "$(grep -m1 -E '^- \*\*Status:\*\*' "$f" | sed -E 's/.*Status:\*\* *//')" \
       "$(grep -m1 -E '^- \*\*Owner:\*\*'  "$f" | sed -E 's/.*Owner:\*\* *//')"
   done
   ```

2. **Verify, don't trust** (this is the point of the audit):
   - `in PR #NNN` → did the PR merge? `git log --oneline | grep '#NNN'`. If merged + code landed, it should
     be `applied`/`done` — flag it.
   - A doc that names a symbol/file/flag → `grep`/`git log` to confirm it still exists. Gone/renamed → flag
     the doc as stale.
   - `staged`/`open`/`wip` → check the code or infra signal it waits on hasn't already changed.
   - `Last verified` far in the past relative to recent changes in its `Module(s)` → flag for re-verify.

3. **Broken links.** For each README, check local links resolve:
   ```bash
   grep -oE '\]\([^)]+\)' <file>.md | sed -E 's/^\]\(//;s/\)$//' | while read -r l; do
     case "$l" in http*) continue;; esac; p="${l#./}"; p="${p%%#*}"
     test -e "$p" && echo "OK   $l" || echo "MISS $l"; done
   ```

4. **Index drift.** Check each type README `## Index` lists every doc in its dir, with a matching `Status`.

Report a concise table of findings grouped by severity (stale / mismatched / broken-link / index-drift),
each with the file and the suggested fix. Do NOT edit anything — this is read-only; offer to fix on request.
For a large tree, delegate the per-doc verification to the `doc-auditor` subagent in parallel.
