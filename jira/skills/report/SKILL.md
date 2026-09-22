---
name: report
description: >
  Post a report into a Jira issue as a well-formatted comment built from Atlassian Document Format (ADF) nodes —
  a verdict panel, facts with the key numbers highlighted, recommended actions — written through the REST API
  (never wiki markup, never raw Markdown). Also drafts the plain-language reply to the reporter as a separate
  purple note panel, and an internal note for another team as a blue info panel. Use whenever the user asks to
  post / save / add a report, findings, an investigation result, a diagnosis or a status update as a Jira comment
  ("post this to SHOP-812", "save the analysis to the ticket", "add the findings as a comment"), to draft a reply
  to the reporter or customer on a ticket, to leave an internal note for another team, or to fix up a comment that
  was just posted.
---

# Post a Jira report (ADF)

Turns an investigation, a diagnosis or a status update into a Jira comment that reads well: a one-line verdict in a
coloured panel, the facts that support it, and what to do next. The body is always **ADF nodes** — Jira comments do
not parse Markdown, and wiki markup (`h3.`, `{{…}}`) renders half-broken.

The bundled script converts a Markdown-lite body into ADF and posts it:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/report/scripts/jira_comment.py" <command> …
```

Environment: `JIRA_ORG` (the `<org>` in `https://<org>.atlassian.net`), `JIRA_EMAIL`, `JIRA_TOKEN` — read from the
environment, then `./.env`, then `~/.jira.env`. Issue lookups (`issue`, `search`, `users`, …) live in the sibling
`jira:ticket` script; use them to read the issue before writing about it.

## Three comment types, three colours

One audience per comment. Never merge a report with a reply draft — the reader must be able to copy one of them and
send it without editing anything out.

| Comment                        | Heading                                                    | Panel           |
|--------------------------------|------------------------------------------------------------|-----------------|
| Report / findings              | `### <subject> — <scope> (<period>)`                       | verdict colour  |
| Draft reply to the reporter    | `### Draft reply — plain language (review before sending)` | `note` (purple) |
| Internal note for another team | `### For <team>:`                                          | `info` (blue)   |

**Verdict colour** on a report: `success` — clean, nothing to do; `warning` — degraded, or the fault is on the
reporting side; `error` — broken on our side; `info` — neutral, informational. `note` and `info` are reserved for
the two draft types, so the audience is obvious from the colour alone.

## Rules for every comment

- **Write in the language the issue is kept in** (default English). Chat with the user in whatever language they use;
  the Jira artifact does not follow the chat.
- **State the finding, cite the system of record.** Name the database, table, service, dashboard, metric or source
  file the fact comes from — never the tool you used to get there. "The `orders` table has 5 715 rows with an empty
  `region`", not "my query showed…" or "the analyzer printed…".
- **Never write about internal tooling or housekeeping.** No mention that a note, doc or runbook was written, that a
  script, query or skill was fixed, that a memory was saved, or which selector turned out to be wrong. Those belong
  in the repo, not in the ticket.
- **Lead with the answer.** The verdict is the first thing after the heading; the evidence supports it, it does not
  build up to it.
- **Numbers, not adjectives.** "76.3% (18 402 / 24 117)" beats "most". Put the key number in `**bold**` and every
  identifier, field, table or value in `` `code` ``.
- **Only claim what the data proves.** Mark a hypothesis as a hypothesis, and say what would confirm it.

## The report

```
### <subject> — <scope> (<period>)

::: panel warning
**Verdict:** <one sentence: what is wrong, and what is confirmed healthy>
:::

<one line of identifying context: ids, versions, environment>

#### <check / area>

- <fact with the **key number** and the `identifier`>
- <fact, with the source of record named>

#### Recommended actions

1. <action, in the order someone should do it>
2. <action>
```

Keep it to what the reader must know: sections per check, bullets for facts, a numbered list for the actions. A
`codeBlock` (fenced, with the language) is worth it only for raw output someone will re-read — a query, a stack
trace, a log line. A period in the heading (`2026-09-01 → 09-21`) saves every bullet from repeating dates.

## Draft reply to the reporter

A suggestion someone reviews and sends, so make it copy-paste-ready: one purple `note` panel wrapping the whole
message as paragraphs — greeting, thank-you, what happened in plain terms, the request, the outcome branches, close.

- **Plain language.** No ids, field names, table names, timestamps, ticket keys, internal terms. Say what the reader
  sees, not what the system does.
- **Minimum detail.** Cut dates, counts, measured values and the chronology — they belong in the report comment. One
  sentence naming the likely cause carries everything the reader needs; every extra fact is something to misread.
- **Hedge the cause.** It is the leading hypothesis, not a settled verdict: "our main hypothesis at this point is…".
  Avoid absolutes while anything is still being confirmed.
- **Never explain the root cause.** When something was fixed, say it was identified and fixed — not the mechanism,
  not the internal term for it. The only cause worth describing is one the reader must act on, and then only its
  visible effect.
- **Do not invent their situation.** Offer environmental causes as possibilities, never as facts about a setup nobody
  has seen.
- **Ask directly, once.** No soft preambles ("Could you help us with one thing?", "Would you mind…"), and never
  justify a request by what it buys us ("so we can diagnose it better") — the reader's goal is a working thing, not
  a better diagnosis. Ask and stop.
- **Never route a risky action to the wrong person.** Anything that can damage something, void a warranty or lose
  data goes to whoever owns that system, not to the person who reported the problem.
- **Never promise an outcome.** No refunds, replacements, coverage or timelines — a promise in a draft becomes a
  commitment the moment it is sent. State the next step and stop.
- **Thank them for what they actually sent** — the screenshot only if there is one; otherwise for reporting it, and
  if there is nothing to acknowledge, drop the line.
- **End with a next step, not a verdict.** Two branches make it actionable, and each says what *the reader* does
  next: "if X, then nothing is wrong"; "if it still happens, contact <owner> to check <thing>".

```
### Draft reply — plain language (review before sending)

::: panel note
Hello <Name>,

Thank you for <what they actually sent>.

<what happened / the likely cause, in plain words>

<the request, stated directly>

- <branch 1 — what it means if the check looks fine>
- <branch 2 — what to do if it still happens>

Please let us know how it goes — we are happy to help.

Best regards,
:::
```

## Internal note for another team

Same shape as the reply draft, different colour, opposite content rules: this is one colleague briefing another, so
ids, field names, keys and the root cause are all welcome. Keep it short and actionable — what was done, what the
other team should do or watch for, what to tell the reporter.

```
### For <team>:

::: panel info
<what we did and what was actually wrong>

<what they should do next, or a numbered list when there is more than one step>
:::
```

## Body syntax

Write Markdown-lite; the script converts it to ADF nodes.

| Body                                 | ADF                                                                   |
|--------------------------------------|-----------------------------------------------------------------------|
| `::: panel warning` … `:::`          | `panel`, `attrs.panelType`: `info` `note` `success` `warning` `error` |
| `### text` / `#### text`             | `heading` with `attrs.level` (3 for sections, 4 for sub-sections)     |
| `- item`                             | `bulletList` → `listItem` → `paragraph`                               |
| `1. item`                            | `orderedList` → `listItem` → `paragraph`                              |
| `> quoted`                           | `blockquote`                                                          |
| ```` ```sql ```` … ```` ``` ````     | `codeBlock` with `attrs.language`                                     |
| `---`                                | `rule`                                                                |
| blank line / single newline          | new `paragraph` / `hardBreak` inside one                              |
| `**bold**`, `` `code` ``, `[t](url)` | text marks `strong`, `code`, `link`                                   |

Headings and lists work inside a panel; panels do not nest. Tables and `@`-mentions are not supported — write names
as plain text. A body file that already holds an ADF document (JSON starting with `{"type": "doc"`) is posted
unchanged, which is the escape hatch for nodes Markdown-lite cannot express:

```json
{
  "type": "text",
  "text": "76.3% usable",
  "marks": [
    {
      "type": "strong"
    }
  ]
}
```

## Procedure

1. **Read the issue first** (`jira_issue.py issue <KEY>`, and `comments <KEY>` here) — so the comment answers what
   the ticket actually asks and does not repeat what is already there.
2. **Assemble the content** from the session: the verdict, the facts behind it, the actions. Apply the rules above,
   pick the comment type and its colour.
3. **Write the body** to a file and check the conversion offline if the structure is unusual:
   `jira_comment.py adf body.md`.
4. **Show the draft in chat and wait for a yes.** Show the rendered text (heading, panel colour, sections) — not the
   ADF. A reply draft is shown in full, word for word, because it is what someone will send.
5. **Post** `jira_comment.py post <KEY> body.md`. Each comment type is its own call — a report and a reply draft are
   two comments, in that order.
6. **Relay** the comment URL and its id.
7. **Revising** a comment you just posted: `post <KEY> body.md --comment-id <id>` replaces it in place instead of
   adding a second one. On a service desk project, `--internal` keeps the comment off the portal.

## Script commands

| Command                                  | Returns (JSON)                                                    |
|------------------------------------------|-------------------------------------------------------------------|
| `adf <body\|->`                          | The ADF document built from the body (offline).                   |
| `post <KEY> <body\|-> [--comment-id ID]` | `commentId` + `url`; `--comment-id` updates in place.             |
| `post … --internal` / `--dry-run`        | Service desk internal comment / the REST payload without posting. |
| `comments <KEY> [--limit N]`             | Newest comments with id, author, dates and a preview.             |

## Guardrails

- Never post without the user's explicit go-ahead, and never post a reply draft they have not read in full.
- One audience per comment; never merge a report, a reply draft and an internal note.
- Never send a plain-text or wiki-markup body — everything goes through the ADF conversion.
- Do not put internal tooling, housekeeping or "how we found it" into any comment.
- Do not invent facts to fill a section: a check that was not run is left out, not guessed.
- Update your own comment rather than posting a corrected copy underneath it.
