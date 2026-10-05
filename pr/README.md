# pr

A Claude Code plugin that shepherds an open pull request to green: it waits for the checks, fixes whatever fails,
works through every review, and hands the calls that are yours to make back to you as weighed options.

## What it gives you

- A `pr:watch` skill that runs a loop over the PR until checks pass and no actionable review is left.
- **Failing checks fixed at the root cause**: reads the failed-step logs, reproduces the CI command locally, fixes,
  verifies and pushes. Flaky failures get one rerun; failures outside the PR (red base branch, missing secret) are
  reported, not worked around.
- **Reviews triaged** against the current code, human and bot alike: *fix* what has one obvious answer, *answer*
  what is mistaken or already handled with evidence, *decide* — architecture, contracts, dependencies, trade-offs,
  scope — goes back to you.
- **Decisions as briefs**: the reviewer's point, two or three options with benefit, cost and effort, "keep as is"
  when defensible, and one recommendation — then a question you answer in one click.
- **Guardrails**: new commits on the PR branch only — no force-push, no merge, no history rewrite — and CI is never
  made green by weakening it (no skipped tests, `continue-on-error`, `--no-verify` or lowered thresholds).
- A dependency-free Python script on top of `gh` that returns the whole PR state as one JSON document and replies to
  and resolves review threads.

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

One run ends when the checks are green and everything left is waiting on you. Reviews that arrive later are picked
up by running it on an interval: `/loop 15m /pr:watch 412`.

## Script commands

### `watch/scripts/gh_pr.py`

All commands print JSON. `<pr>` is a number, a URL or a branch; without it, the current branch's PR.

| Command                              | What it does                                                                 |
|--------------------------------------|------------------------------------------------------------------------------|
| `state [<pr>] [--repo OWNER/REPO]`   | Head, checks with outcomes, unresolved threads, reviews, comments, reviewers |
| `logs [<pr>] [--repo …] [--lines N]` | Failed-step log tail of every failed GitHub Actions job on the head commit   |
| `reply <threadId> <body\|->`         | Reply inside a review thread                                                 |
| `resolve <threadId>`                 | Resolve a review thread                                                      |
