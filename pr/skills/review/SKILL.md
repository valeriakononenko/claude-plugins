---
name: review
description: >
  Review someone else's pull request against its task: read the context from the PR description and the Jira issue
  found by the conventional branch name or commits, then check the change's logic, regressions against the base
  branch, test coverage and security — only what the task touches. Previews the problems numbered P1, P2… in chat,
  discusses any of them on request and proposes the wording, and after the user picks what to post publishes one
  GitHub review with inline threads. On a re-review checks every earlier problem was fixed, looks for new regressions,
  and never raises a problem the user dismissed. Sends the author back to bot findings and red CI first. Approves only
  when the user confirms. Use whenever the user asks to review a PR, look at / check a colleague's PR, re-review after
  changes, or "review #412".
---

# Review a pull request

Reviews a PR as the user's assistant: the analysis is yours, every word posted on GitHub is the user's call. Flow:

1. **Context** — what the task asks for, from the PR description and its Jira issue.
2. **Gate** — red CI or unanswered other/bot findings send the PR back to the author before a human review.
3. **Analysis** — logic, regressions against the base, tests, security, scoped to the task.
4. **Preview** — numbered problems in chat; the user asks about them, keeps some, dismisses others.
5. **Post** — one GitHub review: a short body and a thread per problem on the code.
6. **Re-review** — on the next round, every earlier problem is checked and new regressions are hunted.

The bundled script gathers the PR in one call, reads Jira, posts the review and keeps the ledger:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/review/scripts/gh_review.py" <command> …
```

It needs an authenticated `gh` (`gh auth status`); `jira` needs `JIRA_ORG`, `JIRA_EMAIL` and `JIRA_TOKEN` (the same
variables as the `jira` plugin: environment, `./.env` or `~/.jira.env`).

## Authority

Invoking this skill authorizes **reading** the PR, its repository and its Jira issue, and checking the head out into a
temporary worktree. Every write to GitHub — a review, a reply, resolving a thread — is shown to the user first and
posted only after they confirm it. Never:

- approve unless the user said so for **this head commit** (`post --approved-by-user`); a push after their "approve"
  needs a new confirmation;
- push, commit to the PR branch, merge, close, edit the PR, dismiss reviews or request reviewers;
- resolve or hide anyone else's comments — only the threads this review opened, once their problem is fixed;
- post a problem the user did not pick, or reword one after they approved the wording.

## The ledger

`~/.claude/pr-review/<owner>/<repo>/<number>.json` remembers, across sessions, each problem the review raised: its id,
title, location, status and thread. Statuses:

| Status      | Meaning                                                                 |
|-------------|-------------------------------------------------------------------------|
| `proposed`  | In the preview, not decided yet                                         |
| `posted`    | Published; `threadId` points at its thread (`inline: false` = in body)  |
| `dismissed` | The user rejected it — **never raise it again on this PR**, with reason |
| `fixed`     | Verified fixed on a later head                                          |
| `open`      | Verified still not fixed on a later head                                |
| `followup`  | Too big for this PR; suggested as a separate task                       |
| `withdrawn` | The reviewer (we) was wrong; the author's answer holds                  |

`post` records what it publishes; everything else is written with `record`. Ids continue across rounds: a re-review
numbers its new problems from `nextProblemId`, so P3 is the same problem in every round and in every chat.

**Dismissed means gone.** Before previewing, compare every candidate with the `dismissed` entries — the same root
cause counts as the same problem even when the line moved, the wording differs or it shows up in another file the PR
touches. A dismissed problem is only raised again when the code around it changed in a way that makes it a different
problem, and then the preview says so: "previously dismissed P4, but the new commit …".

## 1. Context

1. `gh_review.py context [<pr>]` — the PR, description, commits, files, checks, bot findings, the viewer's earlier
   reviews and threads, other reviewers' open threads, and the ledger.
2. **Find the task.** `jiraKeys` lists the keys found, best first: the conventional branch name (`feat/SHOP-123-…`), the
   title, commit messages (`fix(SHOP-123): …`), then the description. The user may also pass the key with the PR
   (`/pr:review 412 SHOP-123`). Read it with `gh_review.py jira <KEY>`: description, acceptance criteria, parent,
   subtasks, links, recent comments. A sub-task or a thin story → also read its parent. Without Jira credentials, use
   an Atlassian connector if one is available; with no key or no access, say so and review against the PR description
   alone. Several unrelated keys → ask which one the PR implements.
3. **Write down the task model** before reading the diff, in a few lines: what must change, the acceptance criteria,
   what must explicitly stay as it was, and what is out of scope. It is the yardstick for everything below and opens
   the preview.
4. **Check out the head** into a worktree, never into the user's working tree:
   `git fetch origin pull/<n>/head <base>` then `git worktree add --detach <tmp>/pr-<n> <headSha>` (the session
   scratchpad when there is one). Outside the repository, `gh repo clone <repo> <tmp>/<repo> -- --filter=blob:none`
   first. Diff against the merge base: `git diff $(git merge-base origin/<base> <headSha>)...<headSha>`. Remove the
   worktree when the review is done.

## 2. Gate: bots, other comments and CI first

A human review on top of red CI or ignored bot findings is wasted. From `context`:

- **CI** — `checks.failed > 0`. While checks are `pending`, start `gh pr checks <n> --watch` in the background and do
  the analysis meanwhile; decide the gate when they finish.
- **Bot findings** — each `botFindings` entry is one of:
    - *open* — an unresolved thread, or a visible top-level comment / review body with findings no one answered;
    - *answered* — fixed (check the code at that place on the head) or rejected with a reason in a reply;
    - *dismissed without reason* — resolved or hidden, but the code did not change and no reply explains why.

  Open and silently dismissed findings that are real block; a bot's summary, a "reviewing…" placeholder, praise or a
  finding that is plainly a false positive does not — say which ones you skipped and why.

When the gate fails, the preview leads with it (CI: the failing checks with links; bots: each blocking finding with
its link and one line on why it still matters). Then ask: post a short review asking the author to make CI green and
answer the bot findings first (REQUEST_CHANGES, or COMMENT on your own PR), continue to the full review anyway, or
stop. The gate review has only a body, recorded in the ledger with `"kind": "gate"`; the full review waits for the
next round.

## 3. Analysis

Review the change **as an implementation of the task**. Every problem must come out of the diff — something it
changed, added, removed or failed to add for the task. Not problems: issues that already existed in untouched code,
style the linters accept, personal taste, and "while you're here" ideas. A change that has nothing to do with the task
is raised once, as scope, and only when it carries risk.

Go through, in this order:

1. **Does it do the task?** Each acceptance criterion and each point of the task model: implemented, implemented
   differently, or missing. Edge cases the task implies: empty, null, zero, the maximum, duplicates, concurrent
   calls, retries, time zones, permissions of the different roles.
2. **Logic of the change.** Conditions and their negations, off-by-one, ordering, error handling and what the caller
   sees on failure, transactions and partial writes, idempotency, resource cleanup, caching and invalidation,
   migrations against existing data, config defaults per environment.
3. **Regressions against the base** — behavior that worked on `<base>` and breaks with the PR, without the task asking
   for it. For every changed or removed function, endpoint, query, event, schema, config key or default: find all its
   callers and consumers in the head tree (grep, not memory) and compare old and new behavior from their side —
   signatures, return values, thrown errors, nullability, ordering, side effects, permissions, performance on real
   data sizes. Removed code is read as carefully as added code. A behavior change the task demands is not a
   regression; one it does not mention is, until the PR description justifies it.
4. **Tests — always.** Every behavior the task adds or changes has a test that would fail without the change; bug
   fixes have a test reproducing the bug; error paths and the edge cases from step 1 are covered; assertions check
   outcomes, not just that nothing threw; mocks do not mock away the logic under test. Treat as red flags: tests
   deleted or loosened, `skip` / `only`, snapshots regenerated wholesale, expected values changed to match new output
   with no word in the task. Missing coverage of a behavior is a problem in its own right, anchored at the untested
   code.
5. **Security — always.** In what the PR touches: authentication and authorization on new or changed entry points
   (including object-level access — can user A read B's record by id?), input validation, injection (SQL, shell,
   template, path, header), SSRF and open redirects, secrets in code, config or logs, PII in logs and errors, unsafe
   deserialization, crypto and token handling, CORS and cookies, rate limits on expensive endpoints, new dependencies
   and their versions, workflow permissions and `pull_request_target` in CI changes.

**Prove before you claim.** Each problem needs a concrete scenario — this input, through this path, gives this result
— read from the code, not assumed. When it can be shown cheaply, show it in the worktree: a throwaway test or a quick
run (never committed, never pushed). Unsure after checking → it becomes a question to the author, marked as such in
the preview, not a claim. Prefer five real problems to fifteen plausible ones.

**Large PRs.** When the diff spans several independent areas, fan out with the Agent tool — one agent per area for
steps 2–3, and one for security across the whole diff — each given the task model, the diff range and this section;
verify what they report yourself before it reaches the preview.

## 4. Preview

In chat, in the user's language, nothing on GitHub yet:

```
**PR #412 · <title>** — <author>, <base> ← <head> @ <short sha>
**Task:** [SHOP-123](<url>) — <one-line summary>
**Task model:** <what must change; what must not>
**Acceptance:** ✅ <criterion> · ⚠️ <criterion, partially> · ❌ <criterion, missing>
**Checked:** logic · regressions on <base> · tests · security — <one line on what was looked at>

**Summary**
- **Problem:** <what was wrong or missing before this PR, and who felt it — one sentence>
- **Solution:** <how the PR solves it: the approach and the key pieces it touches, not a file list — 1–2 sentences>
- **Tests:** <what the new or changed tests cover, or that there are none>

### P1 · <problem in a few words> — `path/to/file.ts:42` · blocker
**Expected:** <what the task or the base behavior requires>
**Now:** <what the code does, with the scenario>
**Why it matters:** <the consequence: who breaks, what data, what risk>

### P2 · … · major
### P3 · … · question
```

The **Summary** comes before any problem, so the user knows what the PR is about before judging it. It is
written from the code and the task, not copied from the PR description: when the description claims something the
diff does not do, the summary says what the diff does. Keep each line short — the whole block reads in ten seconds.

Severity: **blocker** (wrong result, data loss, security hole, regression), **major** (a missing acceptance criterion,
untested behavior, a likely edge-case failure), **minor** (worth fixing, not blocking), **question** (needs the
author's answer). Order by severity. No problems → say so, with what was checked, and offer to approve (see Post).

Then ask in plain text: which to post — `all`, a list such as `P1 P3`, or `none` — and that they can ask about any
of them first. Record every previewed problem as `proposed` with `record`.

## 5. Discussion

When the user asks about a problem, dig into it rather than defend it: the call path and the code involved
(`file:line`), what happens on the base versus the head, a reproduction when it helps, how likely and how bad it is,
the fixes the author could make, and what the task says about it. If the discussion shows the problem does not hold,
say so plainly and propose dropping it.

End every discussion with the **proposed comment** — the exact text to post, in the PR's language:

```
P2 → `src/orders/service.ts:118`
> <the comment, as it will appear on GitHub>
```

Approved → it is used verbatim. Edited → use the edit. Rejected or "it's fine" → `dismissed`, with the user's reason
in the ledger, and it never comes back. A problem the user leaves unpicked when choosing what to post is dismissed too
— list those in the posting summary ("P2 and P5 will be recorded as dismissed") so the user can object.

## 6. Writing the comments

Each problem is one inline thread on the line where the fix belongs (the range with `startLine` when it spans lines;
`side: LEFT` for a line the PR deleted). Short, concrete, about the code, never about the author:

```
<the problem in one sentence>

**Expected:** <behavior the task or the base requires>
**Now:** <what this code does, with the input that shows it>
**Why it matters:** <the consequence>
```

- Three to six lines. Reference code as `` `name` `` or a `file:line` link; quote the task when the criterion is the
  point.
- A ```` ```suggestion ```` block only when the fix is small, certain and complete.
- A question is phrased as one ("What should happen when `items` is empty? Today it …").
- No severity labels, no P-ids, no "nit:", no praise padding.

The **review body** is short: the task it was checked against (key and link), one line on the verdict, and whatever
cannot sit on a line (a missing test file, a missing criterion). It does not repeat the threads. Comments on code
outside the diff move into the body automatically, as permalinks under "Outside the diff" (`outsideHeading` renames
it). Write the body and comments in the language the PR is written in.

## 7. Post

Show the final review — event, body and each comment with its anchor — then ask with `AskUserQuestion`:

- **Request changes** (recommended when a blocker or major is in it);
- **Comment** (only minors and questions, or the user's own PR — GitHub allows nothing else there);
- **Approve** — only when nothing blocking is left, and choosing it is the user's confirmation for this head;
- **Don't post**.

Write the spec and post it in one call; `--dry-run` first shows what lands inline and what moves to the body:

```json
{
  "commit": "<headSha the review was built on>",
  "event": "REQUEST_CHANGES",
  "kind": "review",
  "body": "Reviewed against [SHOP-123](…): …",
  "comments": [
    {"problem": "P1", "title": "…", "severity": "blocker", "path": "src/a.ts", "line": 42, "startLine": 40,
     "side": "RIGHT", "body": "…"}
  ],
  "replies": [
    {"problem": "P1", "threadId": "PRRT_…", "body": "…", "status": "fixed", "resolve": true}
  ]
}
```

`post` refuses when the head moved since the spec was built (re-check the new commits first), APPROVE without
`--approved-by-user`, and anything but COMMENT on the viewer's own PR. It builds a pending review, adds the threads and
replies, and submits it, so the PR gets one review and one notification; on an error the pending review is deleted.
Report the review link and what was recorded.

## 8. Re-review

`context` shows a re-review: `ledger.reviews` or `viewerReviews` is not empty. Without a ledger (reviewed elsewhere),
rebuild it from `viewerThreads` — each thread you opened is a problem, numbered in order — and `record` it first.

1. **Gate again** (section 2), against the new head.
2. **What changed since:** `git diff <lastReviewedSha> <headSha>` when the old head is an ancestor; after a rebase or
   force-push, `git range-diff <base>...<lastReviewedSha> <base>...<headSha>` and the full diff.
3. **Every earlier problem** in `posted` or `open`, read against the new code and the author's replies in its thread:
    - **fixed** — the scenario no longer happens (and a test covers it when one was asked for);
    - **open** — not fixed, or fixed partly; say precisely what is still wrong;
    - **followup** — the author argues, or it is clear, that the fix is large or beyond the task: recommend a separate
      task (offer to file it with the `jira` plugin) instead of blocking this PR;
    - **withdrawn** — the author's answer is right.
4. **Regressions in the new commits** — section 3 on the diff since the last review: fixes often break what was
   working. New problems get new ids.
5. **Preview** the round: a summary of what the new commits changed and how (the first round's Summary, for this
   round), each earlier problem with its new status (✅ fixed · ❌ open · ↗️ follow-up · ↩️ withdrawn), then the new
   problems. The same choosing, discussion and dismissal rules apply.
6. **Post** one review: a reply in each earlier thread (`replies`) — fixed ones resolved with `"resolve": true` and a
   one-line "Fixed in `<sha>`, thanks", open ones saying what is still missing — new threads for the new problems, and
   a body with the round's tally. Approve only on the user's word, as always.

## Guardrails

- Never post, reply, resolve or approve without the user's confirmation of that exact content; never approve on a
  head the user did not confirm.
- Never raise a dismissed problem again, in this round or any later one.
- Never claim a problem without a concrete scenario read from the code; uncertainty is a question, not a finding.
- Stay inside the task: no findings in untouched code, no style the tooling accepts, no scope creep.
- Always check tests and security, even when the task looks trivial.
- Read only: no commits, pushes or edits on the PR branch; the worktree is temporary and removed at the end.
- Do not invent the task: missing or unreadable Jira is reported, not filled in.

## Script commands

| Command                               | Returns (JSON)                                                   |
|---------------------------------------|------------------------------------------------------------------|
| `context [<pr>] [--repo OWNER/REPO]`  | PR, `jiraKeys`, commits, files, checks, `botFindings`, earlier   |
|                                       | reviews and threads, `otherOpenThreads`, ledger, `nextProblemId` |
| `jira <KEY> [--comments N]`           | Summary, type, status, description, acceptance criteria, parent, |
|                                       | subtasks, links, newest comments                                 |
| `post <spec\|-> [--pr …] [--dry-run]` | The submitted review, threads and replies with their urls        |
| `post … --approved-by-user`           | Required with `"event": "APPROVE"`                               |
| `ledger [<pr>]`                       | The ledger, its path and `nextProblemId`                         |
| `record <update\|-> [--pr …]`         | The ledger after merging `{"task": …, "problems": [{id, …}]}`    |

`<pr>` is a number, a URL or a branch; without it, the current branch's PR. `botFindings` entries carry `kind`
(`thread`, `comment`, `review`), `status` (`open`, `resolved`, `hidden`) and the human `replies` of a thread.
`PR_REVIEW_HOME` moves the ledger directory.
