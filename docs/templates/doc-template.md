# <Title>

<one-line summary of what this doc is — drop if the title already says it>

- **Date:** <YYYY-MM-DD>            <!-- when first written -->
- **Last verified:** <YYYY-MM-DD>   <!-- when contents were last checked against reality -->
- **Owner:** Name <email>           <!-- the one person accountable for this doc -->
- **Status:** <value>               <!-- type-specific lifecycle value — see the type's README -->
- **Module(s):** …                  <!-- affected modules / scope -->
- **Related:** …                    <!-- links: issues, ADRs, runbooks, other repos, tickets -->

<!--
Skeleton for a SINGLE doc — copy to docs/<type>/<NNNN>-<created_at>-<slug>.md, the same rule for every type
including ADRs. <NNNN> = the doc's running number within its type's folder, zero-padded to 4 and starting at
0001; the next doc takes the highest existing <NNNN> in that folder + 1, never reused. For ADRs that <NNNN>
is also the ADR number used in its title and cross-references. Fill the header, delete these comments,
write the body.
To start a docs/<type>/README.md instead, use doc-section-template.md.

Shared-header rules — identical for every doc type, so all docs read the same way:
- Field set, names, and order are identical across all types; only the `Status` vocabulary differs per
  type (see the type's own README for its allowed values).
- `Date`, `Last verified`, `Owner`, and `Status` are required; `Module(s)` and `Related` are free-text.
- Each doc has exactly one owner — re-assign on handoff rather than leaving it stale.
-->

## <First section>

…
