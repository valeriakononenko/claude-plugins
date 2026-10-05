# pr

A Claude Code plugin that shepherds an open pull request to merge: it waits for the checks, fixes whatever fails,
works through every review, rebases when the base runs ahead, and hands the calls that are yours to make back to you
as weighed options.

## What it gives you

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

## Usage

Run `/pr:watch` (the current branch's PR) or `/pr:watch 412`, or ask in plain language:

- "watch the PR I just opened"
- "CI is red on #412, fix it"
- "address the review comments"

The watch does not end on green: between passes a background `wait` polls the PR every minute and wakes the agent
when checks finish, a review comes in, someone else pushes, or the PR falls behind its base. It ends when the PR is
merged or closed, or when you tell it to stop.

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
