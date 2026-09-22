# jira

A Claude Code plugin for writing Jira that both managers and engineers can read: issues with a business-oriented
summary and the business problem before the technical details, and comments that report an investigation as a
verdict panel, the facts behind it and what to do next. Everything is written as ADF nodes through the REST API.

## What it gives you

- A `jira:ticket` skill that turns a bug report, TODO, finding, incident or chat thread into a Jira issue.
- A `jira:report` skill that posts an investigation into an issue as a formatted comment — and, as separate
  comments, a plain-language reply draft for the reporter and an internal note for another team.
- **Writing rules** baked in: short business-value summary; description = business problem first, technical details
  as separate paragraphs; purely technical (NFR) tasks summarised so managers see *why* and engineers see *what*.
- **Guided questions**, asked in one round: project, assignee (mandatory), issue type when unclear, parent epic
  (proposed, user decides), linked issues and their relation, labels (component names become labels).
- A **numbered draft** (type, summary, assignee, epic, labels, linked issues) that must be confirmed before anything is
  created.
- **Report style** baked in: verdict first in a coloured panel (colour = verdict), facts with the key numbers in
  bold and identifiers in code, recommended actions as a numbered list — and a fixed colour per audience, purple for
  the reply draft, blue for the internal note.
- **Reply-draft rules** that keep a customer-facing message sendable: plain language, no internal identifiers or root
  cause, a hedged hypothesis, no promised outcomes, and a next step the reader can act on.
- Dependency-free Python scripts that write descriptions and comments as **ADF nodes** through the Jira Cloud REST
  API v3, add the issue links, and update a comment in place.

## Install

```
/plugin marketplace add <path-or-url to claude-plugins>
/plugin install jira@divergence082-plugins
```

## Setup

The script authenticates with an Atlassian API token over basic auth. Provide the variables via the environment,
`./.env` in the project you work from, or `~/.jira.env`:

```
JIRA_ORG=<your-org>          # the <your-org> in https://<your-org>.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_TOKEN=<Atlassian API token>
JIRA_PROJECT_KEY=SHOP        # optional: default project to offer
```

Create the token at <https://id.atlassian.com/manage-profile/security/api-tokens>. Check it works:

```
python3 ~/.claude/plugins/…/jira/skills/ticket/scripts/jira_issue.py whoami
```

## Usage

### Creating an issue

Run `/jira:ticket` or just ask in plain language — the skill activates on its own:

- "create a Jira task for the outdated order status after payment"
- "file a bug: the CSV export fails for accounts with more than 500 orders"
- "turn this finding into a Jira ticket"

Claude reads the context, drafts the summary and description, looks up projects / people / epics / labels / link
types in your Jira, asks for what is missing in one round, shows the numbered draft and creates the issue only after
you confirm. You get back the key, the URL and the result of every link.

### Posting a report

Run `/jira:report` or ask for it:

- "post the findings to SHOP-812"
- "save this analysis as a comment on the ticket"
- "draft a reply to the reporter"
- "leave an internal note for support"

Claude assembles the verdict, the facts and the actions from the session, writes them as a Markdown-lite body with
`::: panel <type>` directives, shows the rendered draft in chat and posts it only after you confirm. A report, a
reply draft and an internal note are always separate comments, each with its own panel colour.

## Script commands

### `ticket/scripts/jira_issue.py`

All commands print JSON. `adf` and `create --dry-run` work offline.

| Command                             | What it does                                                |
|-------------------------------------|-------------------------------------------------------------|
| `whoami`                            | Verify credentials, show the current user.                  |
| `projects [query]`                  | List projects.                                              |
| `issue-types <PROJECT>`             | List issue types available in a project.                    |
| `users <PROJECT> [query]`           | List assignable users with their `accountId`.               |
| `epics <PROJECT> [query] [--limit]` | List open epics.                                            |
| `search '<jql>' [--limit]`          | Run a JQL query (quote project keys: `project = "SHOP"`).   |
| `issue <KEY>`                       | Show one issue with parent and links.                       |
| `link-types`                        | List link types with their outward / inward wording.        |
| `labels [substring]`                | List existing labels.                                       |
| `adf <spec.json\|->`                | Print the ADF built from a spec's description.              |
| `create <spec.json\|-> [--dry-run]` | Create the issue and its links; dry-run prints the payload. |

Spec JSON accepted by `create`:

```json
{
  "project": "SHOP",
  "type": "Bug",
  "summary": "Customers see outdated order status after paying",
  "description": "## Business problem\n…\n\n## Technical details\n…",
  "assignee": "<accountId or unique display name>",
  "labels": [
    "order-status"
  ],
  "epic": "SHOP-640",
  "links": [
    {
      "issue": "SHOP-774",
      "relation": "is blocked by"
    }
  ]
}
```

The description is Markdown-lite: headings, paragraphs, bullet and numbered lists, quotes, rules, fenced code,
inline code, bold and links. The script converts it to ADF (`doc` / `heading` / `paragraph` / `bulletList` /
`orderedList` / `codeBlock` / `blockquote` / `rule` nodes with `hardBreak`, `code`, `strong` and `link` marks).
Link relations are read as "new issue *relation* other issue" and matched against the site's link types by name,
outward or inward wording.

### `report/scripts/jira_comment.py`

| Command                                  | What it does                                                   |
|------------------------------------------|----------------------------------------------------------------|
| `adf <body\|->`                          | Print the ADF built from a comment body (offline).             |
| `post <KEY> <body\|-> [--comment-id ID]` | Post a comment, or update that one in place.                   |
| `post … --internal`                      | Service desk: keep the comment off the customer portal.        |
| `post … --dry-run`                       | Print the REST payload instead of posting (offline).           |
| `comments <KEY> [--limit N]`             | List the newest comments with id, author, dates and a preview. |

A comment body is the same Markdown-lite plus `::: panel info|note|success|warning|error` … `:::` blocks, which
become ADF `panel` nodes. A body that already holds an ADF document (JSON starting with `{"type": "doc"`) is posted
unchanged.
