---
description: Fast read-only one-line-per-doc status table (no verification).
argument-hint: "[type, default: all]"
---

Print a quick state-of-play table of all docs — no verification, just what the headers say. Scope: `$1` if
given (a type dir), otherwise all of `docs/`.

Collect Status + Owner + Last verified for every doc and print a single aligned table grouped by type:

```bash
for f in $(find docs -name '*.md' ! -name 'README.md' ! -path '*/templates/*' | sort); do
  printf '%s\t%s\t%s\t%s\n' "${f#docs/}" \
    "$(grep -m1 -E '^- \*\*Status:\*\*'        "$f" | sed -E 's/.*Status:\*\* *//')" \
    "$(grep -m1 -E '^- \*\*Owner:\*\*'         "$f" | sed -E 's/.*Owner:\*\* *//')" \
    "$(grep -m1 -E '^- \*\*Last verified:\*\*' "$f" | sed -E 's/.*Last verified:\*\* *//')"
done
```

Render as a Markdown table (`Doc | Status | Owner | Last verified`), grouped by type dir. This is the cheap
dashboard; for verification of whether those statuses are actually true, use `/doc-keeper:audit`.
