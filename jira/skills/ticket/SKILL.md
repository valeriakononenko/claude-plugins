---
name: ticket
description: >
  Create a Jira issue (task, bug, story) with a business-oriented summary and a description that states the business
  problem before the technical details, written to Jira as ADF nodes via the REST API. Always asks for the project,
  the assignee, the issue type when unclear, a parent epic, linked issues and labels, then shows a numbered draft and
  creates only after the user confirms. Use whenever the user asks to create / file / open / raise a Jira ticket,
  task, bug or story ("create a Jira task for…", "file a bug about…", "open a ticket for this"), or to turn a
  finding, TODO, incident or discussion into a Jira issue.
---

# Create a Jira ticket

Turns whatever the user has (a bug report, a TODO, a finding, a chat thread, an NFR) into a well-formed Jira issue.
The bundled script `${CLAUDE_PLUGIN_ROOT}/skills/ticket/scripts/jira_issue.py` does every Jira call: lookups,
Markdown-lite → ADF conversion, issue creation and linking. Python 3 stdlib only, no install step.

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/ticket/scripts/jira_issue.py" <command> …
```

Environment: `JIRA_SITE` (`https://<org>.atlassian.net`), `JIRA_EMAIL`, `JIRA_TOKEN` (required) and
`JIRA_PROJECT_KEY` (optional default project to offer). Read from the environment, then `./.env`, then
`~/.jira.env`. If `whoami` fails, tell the user which variable is missing and stop; never guess a site.

## Writing rules

**Summary** — business-oriented, short (aim for ≤ 10 words, never a sentence with a period). A manager with no
technical background must understand the value or the pain from the summary alone. No component names, class names,
stack traces, PR numbers or jargon. Describe the outcome or the problem, not the implementation.

| Avoid                                              | Prefer                                             |
|----------------------------------------------------|----------------------------------------------------|
| Fix NPE in `OrderStatusHandler` on payment webhook | Customers see outdated order status after paying   |
| Migrate `packages/api` to the new build pipeline   | Faster, cheaper API deployments (platform upgrade) |
| Add cache invalidation on PaymentConfirmed event   | Order page shows paid status within seconds        |

**Description** — always two parts, in this order, as separate paragraphs / sections:

1. **Business problem** first: why the company needs this — who is affected (customers, support, ops, revenue), what
   hurts today, what changes when it is done. Plain language, no code.
2. **Technical details** after that, as their own paragraphs (use a `## Technical details` heading): current
   behaviour, root cause if known, proposed change, affected modules, acceptance criteria, links to code/PRs/logs.

**Purely technical tasks (NFR — non-functional requirements)** such as refactors, upgrades, migrations, observability,
performance and security work: keep the same two-part shape. The business part says in one or two sentences that this
is a technical/platform task and what high-level goal it serves (reliability, cost, delivery speed, security, unblocking
future features) so managers understand *why it is on the board*; the technical part states the goal precisely enough
for engineers to start. Mark the summary so its nature is clear, e.g. a trailing `(platform)` / `(tech debt)` /
`(security)` tag.

**Description syntax** — write Markdown-lite; the script converts it to ADF nodes (`doc` → `heading`, `paragraph` with
`hardBreak`, `bulletList`, `orderedList`, `codeBlock`, `blockquote`, `rule`; inline `code`, `**strong**`, links):

- Blank line between blocks; single newline inside a paragraph = line break.
- `## Heading`, `- bullet`, `1. numbered`, `> quote`, `---` rule, fenced ```` ``` ```` code with optional language.
- Inline: `` `code` ``, `**bold**`, `[text](https://…)` or a bare URL.
- Nothing else is interpreted; tables and mentions are not supported — put names as plain text.

Write the ticket in the language the user's Jira is kept in; default to English when unsure.

## Procedure

Do the reading and lookups first, then ask **everything still missing in one round** (use `AskUserQuestion`, one
question per gap, with concrete options from the lookups). Never create without the user's explicit "go".

1. **Understand the ask.** Read the code/logs/thread the user points at. Decide what the business problem is and
   which details are technical. Draft the summary and description following the writing rules.

2. **Verify access** with `whoami` once per session. Its `defaultProject` is `JIRA_PROJECT_KEY`, if set.

3. **Project / scope — always ask.** Run `projects` (optionally with a query) and offer the likely ones, with
   `defaultProject` pre-selected when present. If the user named a project key in the request, still confirm it in
   the draft, but you may skip a separate question.

4. **Issue type.** Run `issue-types <PROJECT>`. Pick it yourself only when it is obvious from the content *and* the
   project offers it (a defect with reproduction → `Bug`; a single project type like `Task` → that). If there is any
   doubt (feature vs. task, story vs. task, improvement vs. bug), **ask**, listing the project's types.

5. **Assignee — always ask, never leave empty.** Run `users <PROJECT> [name]` to offer real assignable people. If the
   user says "me", resolve via `whoami`. Store the `accountId`. A ticket without a person is never created.

6. **Epic — propose, user decides.** Run `epics <PROJECT> [keywords]` (open epics, newest first). Suggest the best
   match with its key and summary, or say none fits; offer "no epic" as an explicit option. Skip only when the project
   has no `Epic` issue type.

7. **Linked issues — always ask.** Ask whether existing tickets should be linked and how. Offer the relations from
   `link-types` in plain words (e.g. `blocks`, `is blocked by`, `relates to`, `duplicates`, `is caused by`). Relation
   wording is read as "NEW ISSUE <relation> OTHER ISSUE". Use `issue <KEY>` or `search '<jql>'` to check candidates
   the user mentions vaguely; quote project keys in JQL (`project = "SHOP"`).

8. **Labels — always confirm.** If the user mentioned a component/module/service the problem belongs to, add its
   name as a label (lower-case, hyphens, no spaces). Run `labels <substring>` to reuse an existing spelling instead
   of inventing a near-duplicate. Propose the label list and ask what to add or drop.

9. **Show the draft and wait for confirmation.** Present a numbered list, exactly in this order, then the full
   description below it, and ask for a yes / edits:

   ```
   1. Project:       SHOP
   2. Type:          Bug
   3. Summary:       Customers see outdated order status after paying
   4. Assignee:      Jane Doe
   5. Epic:          SHOP-640 — Checkout reliability   (or: none)
   6. Labels:        order-status, backend
   7. Linked issues: is blocked by SHOP-774; relates to SHOP-701   (or: none)

   Description:
   <the Markdown-lite text>
   ```

   Any edit → apply it and show the numbered list again. Only an explicit confirmation moves to step 10.

10. **Create.** Write the spec JSON to a temporary file and run `create <spec.json>`; use `--dry-run` first if you
    changed the description syntax and want to see the ADF payload. Spec shape:

    ```json
    {
      "project": "SHOP",
      "type": "Bug",
      "summary": "Customers see outdated order status after paying",
      "description": "## Business problem\n…\n\n## Technical details\n…",
      "assignee": "<accountId>",
      "labels": ["order-status", "backend"],
      "epic": "SHOP-640",
      "links": [{"issue": "SHOP-774", "relation": "is blocked by"}, {"issue": "SHOP-701", "relation": "relates to"}]
    }
    ```

    `epic` and `links` are optional; omit them when the user chose none. The script refuses a spec without
    `assignee` and labels containing whitespace.

11. **Report.** Give the key and URL from the output, the assignee, the epic and every link. If a link failed the
    output says so per link — report it and offer to retry, the issue itself already exists.

## Script commands

| Command                             | Returns (JSON)                                                   |
|-------------------------------------|------------------------------------------------------------------|
| `whoami`                            | Current user (`accountId`, `displayName`) — credential check.    |
| `projects [query]`                  | Project keys and names.                                          |
| `issue-types <PROJECT>`             | Non-subtask issue types available in the project.                |
| `users <PROJECT> [query]`           | Assignable users with `accountId`.                               |
| `epics <PROJECT> [query] [--limit]` | Open epics, newest first.                                        |
| `search '<jql>' [--limit]`          | Issues with status, type, assignee, parent, labels.              |
| `issue <KEY>`                       | One issue with its parent and existing links.                    |
| `link-types`                        | Link types with outward / inward wording.                        |
| `labels [substring]`                | Existing labels (all, or filtered).                              |
| `adf <spec.json\|->`                | The ADF document built from the spec's description (offline).    |
| `create <spec.json\|-> [--dry-run]` | Created `key` + `url` + per-link result; dry-run prints payload. |

## Guardrails

- Never create an issue without: confirmed project, confirmed assignee, confirmed draft.
- Never silently change a confirmed field — re-show the draft after any edit.
- Do not put technical jargon in the summary; move it to the technical section.
- Do not invent epics, labels or link targets — everything offered must come from a lookup or from the user.
- One ticket per request unless the user explicitly asks for several; then run the full procedure per ticket.
