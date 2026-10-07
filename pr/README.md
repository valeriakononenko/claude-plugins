# pr

A Claude Code plugin for both sides of a pull request. As the author, it shepherds your PR to merge: it waits for the
checks, fixes whatever fails, works through every review, rebases when the base runs ahead, and hands the calls that
are yours to make back to you as weighed options. As the reviewer, it reviews a colleague's PR against its Jira task,
previews the problems for you to pick from, and posts the ones you chose as one GitHub review.

## What it gives you

### Authoring: `pr:watch`

- A `pr:watch` skill that watches the PR until it is merged: after every push until the checks are green, and after
  green for new reviews, reruns and a base branch that moved on.
- **Failing checks fixed at the root cause**: reads the failed-step logs, reproduces the CI command locally, fixes,
  verifies and pushes. Flaky failures get one rerun; failures outside the PR (red base branch, missing secret) are
  reported, not worked around.
- **Reviews triaged** against the current code, human and bot alike: *fix* what has one obvious answer, *answer*
  what is mistaken or already handled with evidence, *decide* — architecture, contracts, dependencies, trade-offs,
  scope — goes back to you.
- **Review fixes test first**: a finding about behavior is first reproduced by a failing test, then fixed, and the
  test ships in the same commit as the fix. A test that passes on the current code turns the fix into an answer.
- **Addressed comments closed properly**: after the push, bot threads are resolved *and* hidden, bot findings posted
  as top-level comments and bot review bodies are hidden as Resolved (they have no resolve), and a second `state`
  confirms nothing addressed is left on screen. People's threads get a reply and stay theirs to resolve.
- **Rebased when the base runs ahead**: when the PR turns behind or conflicting, it is rebased onto the base, clear
  conflicts are resolved, the tests are rerun, and the result is pushed with `--force-with-lease`. A conflict that
  means choosing between the PR and what landed on the base comes back to you instead.
- **Decisions as briefs**: the reviewer's point, two or three options with benefit, cost and effort, "keep as is"
  when defensible, and one recommendation — then a question you answer in one click.
- **Guardrails**: new commits on the PR branch only — no merge, no history rewrite beyond the lease-protected rebase
  onto the base — and CI is never made green by weakening it (no skipped tests, `continue-on-error`, `--no-verify` or
  lowered thresholds).
- A dependency-free Python script on top of `gh` that returns the whole PR state as one JSON document, replies to
  and resolves review threads, and hides comments and review bodies.

### Reviewing: `pr:review`

- **Task first**: the context comes from the PR description and the Jira issue found by the conventional branch name
  (`feat/SHOP-123-…`), the title or the commits — description, acceptance criteria, parent and links.
- **Bots and CI first**: red checks, or bot findings left open or dismissed without a reason, send the PR back to the
  author with a short review before a human one.
- **Scoped analysis**: the change's logic against the task, regressions in what worked on the base branch, test
  coverage and security — always the last two — and nothing outside the task.
- **Summary first**: before any finding, a short summary of the problem the PR solves, how it solves it and what
  the tests cover — written from the diff, not copied from the description.
- **Preview before posting**: problems numbered P1, P2… with what is expected, what happens now and why it matters.
  Ask about any of them and get a deep dive ending in a proposed comment; pick what to post.
- **One review, GitHub style**: a short body and an inline thread per problem, posted atomically as one review;
  comments on code outside the diff move into the body as permalinks.
- **Re-reviews**: every earlier problem is checked as fixed, still open or worth a follow-up task, the new commits are
  checked for regressions, and fixed threads are answered and resolved.
- **A ledger per PR** remembers what was posted and what you dismissed — a dismissed problem is never raised again.
- **Approves only on your word**, for the exact head commit you confirmed.

## Install

```
/plugin marketplace add valeriakononenko/claude-plugins
/plugin install pr@divergence082-plugins
```

## Setup

Install the [GitHub CLI](https://cli.github.com) and log in with `gh auth login`. Check it works from the
repository the PR belongs to:

```
python3 ~/.claude/plugins/…/pr/skills/watch/scripts/gh_pr.py state
```

`pr:review` reads the task from Jira Cloud with the same variables as the `jira` plugin — `JIRA_ORG`, `JIRA_EMAIL`
and `JIRA_TOKEN`, from the environment, `./.env` or `~/.jira.env`. Without them it falls back to an Atlassian
connector, or to the PR description alone. Its ledger lives in `~/.claude/pr-review/` (`PR_REVIEW_HOME` moves it).

## Usage

### `pr:watch`

Run `/pr:watch` (the current branch's PR) or `/pr:watch 412`, or ask in plain language:

- "watch the PR I just opened"
- "CI is red on #412, fix it"
- "address the review comments"

The watch does not end on green: between passes a background `wait` polls the PR every minute and wakes the agent
when checks finish, a review comes in, someone else pushes, or the PR falls behind its base. It ends when the PR is
merged or closed, or when you tell it to stop.

### `pr:review`

Run `/pr:review 412` (or `/pr:review 412 SHOP-123` to name the task), or ask:

- "review #412"
- "they pushed fixes to #412, re-review it"

Answer the preview with `all`, `P1 P3` or `none`, or ask about any problem first. Then choose request changes,
comment or approve — nothing reaches GitHub before that.

## Script commands

### `watch/scripts/gh_pr.py`

All commands print JSON. `<pr>` is a number, a URL or a branch; without it, the current branch's PR.

| Command                              | What it does                                                                 |
|--------------------------------------|------------------------------------------------------------------------------|
| `state [<pr>] [--repo OWNER/REPO]`   | Head, checks with outcomes, unresolved threads, reviews, comments, reviewers |
| `logs [<pr>] [--repo …] [--lines N]` | Failed-step log tail of every failed GitHub Actions job on the head commit   |
| `reply <threadId> <body\|->`         | Reply inside a review thread                                                 |
| `resolve <threadId>`                 | Resolve a review thread                                                      |
| `close <threadId> [--reason R]`      | Resolve a review thread and hide it (`RESOLVED` by default)                  |
| `hide <id> [--reason R]`             | Hide a comment or review body, or change the reason of a hidden one          |
| `wait [<pr>] [--repo …]`             | Poll until checks finish, a review lands, the base runs ahead, or it merges  |

### `review/scripts/gh_review.py`

| Command                                   | What it does                                                            |
|-------------------------------------------|-------------------------------------------------------------------------|
| `context [<pr>] [--repo OWNER/REPO]`      | PR, Jira keys, commits, files, checks, bot findings, earlier reviews    |
| `jira <KEY>`                              | The Jira task: description, acceptance criteria, parent, links          |
| `post <spec\|-> [--pr …] [--dry-run]`     | Publish one review: body, inline threads, replies; `--approved-by-user` |
| `ledger [<pr>]`                           | The PR's review ledger: posted, fixed and dismissed problems            |
| `record <update\|-> [--pr …]`             | Merge problem statuses and the task key into the ledger                 |
