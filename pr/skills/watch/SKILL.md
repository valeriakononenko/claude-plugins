---
name: watch
description: >
  Shepherd an open pull request to merge: wait for its GitHub Actions / checks, fix whatever fails at the root cause,
  then work through every review (human and bot): fix what is clearly fixable, reply where the reviewer is wrong, and
  hand the architectural and trade-off calls back to the user as weighed options with a recommendation. Commits and
  pushes the fixes to the PR branch, resolves and hides the bot comments it addressed, rebases onto the base branch
  when the PR falls behind or into conflict, and keeps watching until the PR is merged. Use right after a PR is opened
  or pushed, and whenever the user asks to watch / babysit / shepherd a PR, to get CI green, to fix failing checks or
  actions, to address / handle / work through review comments, to resolve or close addressed comments, or to "take
  care of the PR".
---

# Watch a pull request

Takes a PR from "opened" to "merged". Three duties, in a loop:

1. **Checks.** Wait for every check on the head commit. A failure is fixed at its root cause, verified locally and
   pushed.
2. **Reviews.** Every unresolved thread, review body and top-level comment is read against the current code, then
   fixed, answered or escalated to the user — and once addressed, closed so the PR shows only what is still open.
3. **Base.** When the base branch moves on and the PR falls behind or into conflict, rebase onto it.

Green with every review answered is not the end: it is waiting. A new review, a rerun or a moved base can turn it red
again at any time, so the watch runs until the PR is merged or closed, or the user says to stop.

The bundled script gathers the PR state in one call and answers review threads:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/watch/scripts/gh_pr.py" <command> …
```

It needs an authenticated `gh` (`gh auth status`). With no PR argument it uses the current branch's PR.

## Authority

Invoking this skill authorizes **new commits pushed to the PR's head branch**, **rebasing that branch onto its base**
when the PR is behind or conflicting (pushed with `--force-with-lease`), replies on the PR, and resolving and hiding
**bot** comments once they are addressed. Nothing else:

- Never force-push except the lease-protected push of such a rebase; never amend, squash or otherwise rewrite pushed
  commits, and never push to the base branch or another branch.
- Never merge, close, mark ready / draft, request or dismiss reviews, or edit the PR title and description.
- Never weaken a gate to get green: no skipped or deleted tests, no `continue-on-error`, no `--no-verify`, no lowered
  coverage or lint thresholds, no `# noqa` / `@ts-ignore` / `eslint-disable` to silence a real finding, no retrying a
  genuine failure until it passes. A change to what CI enforces (workflow files, thresholds, required checks) is a
  decision for the user.

## Triage review feedback

Read each item **against the current code** — a later bot pass saying "no issues" is not proof an earlier finding
was fixed, and an outdated thread may still be valid on the moved lines. Then sort it into exactly one bucket:

- **Fix** — bugs, missed edge cases, error handling, security findings with a local fix, missing or weak tests,
  naming, readability, dead code, docs, typos, style: one obvious right answer within the PR's scope. Fix it test
  first (see below), verify, push, reply with the commit.
- **Answer** — the reviewer is mistaken, it is already handled, it is a question, or the bot finding is a false
  positive. Reply with the evidence (`file:line`, a test, the spec); no code change.
- **Decide** — more than one reasonable answer with real costs either way (see below). Do not touch the code or reply;
  bring it to the user as options.
- **Skip** — praise, a bot's "reviewing…" placeholder, CI summaries, duplicates of something already handled.

**Decide** is anything where choosing is the job, not typing:

- architecture and module boundaries, a new abstraction or layer, moving responsibility between components;
- public API, schema, wire format, migration or config contract changes; backward compatibility;
- new dependencies, swapping a library, a different algorithm or data structure with a different cost profile;
- performance vs. readability, consistency vs. availability, strictness vs. leniency — any genuine trade-off;
- widening scope ("while you're here, also…"), or splitting the PR;
- reviewers who disagree with each other, or a request that contradicts the ticket or an earlier decision;
- a fix whose blast radius goes beyond the PR's diff.

When unsure between Fix and Decide, it is Decide. A decision the user already made in this session is not re-asked.

## Fix review feedback test first

A review finding about behavior — a bug, a missed edge case, error handling, a security hole, a wrong result — is
covered by a test before the code is touched:

1. **Write the test** that pins down the reviewer's point, next to the existing tests and in their style: the input
   the reviewer describes and the result the code should give.
2. **Run it and watch it fail** for the reason the reviewer gave. A test that passes on the current code means the
   finding does not hold as stated: re-read the comment, and if it really is handled, the item moves to Answer with
   that test as the evidence (keep the test when it adds coverage).
3. **Write the fix**, the smallest change that makes the test pass, then run the test and the surrounding suite.
4. **Commit the test and the fix together**, so no pushed commit carries a red test, and name the test in the reply.

The same applies to a Decide item once the user has chosen. Changes with no behavior to assert — naming, typos, docs,
dead code, style, readability — skip the test. When a behavior finding cannot reasonably be tested (no test setup in
the repository, or only reachable through an external system), fix it without one and say why in the reply and the
report; never add a test framework to the PR to get there — that is a Decide.

## Bring decisions to the user

Present each one as a short, balanced brief — the reviewer's point taken seriously, not argued away:

```
### D1 · <the question, in one line> — <reviewer>, `path:line`

<two or three sentences: what the reviewer asks and what the code does today>

**A. <option>** — <what changes>. + <benefit> · − <cost / risk> · effort: <S/M/L>
**B. <option>** — <what changes>. + <benefit> · − <cost / risk> · effort: <S/M/L>
**C. Keep as is, explain in the thread** — + <benefit> · − <cost / risk>

**Recommendation: B** — <the one reason that tips it, tied to this codebase or this PR's goal>.
```

Usually two or three options, "keep as is" among them whenever it is defensible, and one recommendation. Then ask with
`AskUserQuestion` — one question per decision, up to four at a time, recommended option first and marked
"(Recommended)". Implement the chosen option like a Fix, and reply in the thread with what was decided.

## Fix failing checks

1. **Read the failure.** `gh_pr.py logs` prints the failed-step output of every failed Actions job. For a check that is
   not an Actions job (an external app or status), open its `url`. When the log is unavailable, fall back to
   `gh run view <runId> --log-failed`.
2. **Classify it.**
    - *Caused by the PR* — a test, type, lint, build or format error in or because of the diff. Fix it.
    - *Flaky / infrastructure* — a network timeout, runner lost, rate limit, a test that does not touch the diff and
      passes on the base branch. Rerun once with `gh run rerun <runId> --failed` and say so in the report. A second
      failure is no longer flaky: treat it as real.
    - *Not this PR's problem* — the base branch is red, a secret or permission is missing, a required service is down.
      Stop on that check and report it with the evidence; do not work around it in the PR.
3. **Reproduce locally** with the command CI ran (read it from the workflow file) before changing anything, and run
   it again after the fix. A fix that was not verified locally is only pushed when the step cannot run locally — and
   then the report says so.
4. **Fix the cause, not the symptom** — see the guardrails under Authority.
5. **Give up after three attempts** at the same check and hand it to the user with what was tried and what the logs
   say.

## Keep up with the base

Rebase when `wait` reports `behind` or `conflicts`, or `state` shows `mergeStateStatus` `BEHIND` (the base moved and
branch protection wants the PR up to date) or `DIRTY` (it no longer merges cleanly):

1. With a clean working tree on the head branch: `git fetch origin <base>` and `git rebase origin/<base>`.
2. **Conflicts.** Resolve one when the intent of both sides is clear and can be kept — imports, neighbouring edits, a
   symbol renamed on the base that the PR uses. When resolving means choosing between the PR's behavior and what
   landed on the base, `git rebase --abort` and bring it to the user as a Decide.
3. **Verify** with the build and the tests the PR touches before pushing. A break the rebase surfaced is fixed like a
   failing check, in a new commit on top.
4. `git push --force-with-lease`. A rejected lease means someone else pushed meanwhile: fetch, start over from their
   head, and never fall back to a plain `--force`.

A base that moved without making the PR behind or conflicting is not a reason to rebase: it restarts CI and resets the
reviewers' "viewed" files for nothing.

## Procedure

1. **Locate the PR and sync.** `gh_pr.py state [<pr>]`. Check out the head branch (`gh pr checkout <n>`) and pull. If
   the working tree is dirty, stop and ask — never stash or discard the user's changes. If the PR is from a fork you
   cannot push to, or is merged / closed, report and stop.
2. **Wait for the checks** when any are pending: start `gh_pr.py wait <n>` in the background (Bash
   `run_in_background`) — it exits with `checks-done` when they finish — and meanwhile triage the reviews that are
   already there. If the PR is already `BEHIND` or `DIRTY`, rebase first (see above): checks on a stale base are
   wasted.
3. **Fix failing checks** as above.
4. **Work the reviews.** From `state`: every `unresolvedThreads` entry, every `reviews` body (`CHANGES_REQUESTED`
   first), and every top-level `comments` entry not written by `viewer`. Triage each, apply all the Fix items — test
   first for behavior findings — and collect the Decide items.
5. **Commit and push.** Group related fixes into a few focused commits in the repository's message style (one per
   failing check or review topic beats one per comment), run the relevant tests and linters, then `git push`.
6. **Reply on the PR**, in the language the PR is written in, after the push so the commit exists:
    - Fix: `gh_pr.py reply <threadId> -` with a line on what changed, the test that covers it, and the short sha.
    - Answer: the reason and the evidence, in one or two sentences, without defensiveness.
    - A review body or top-level comment has no thread: answer with one `gh pr comment <n> --body-file -` that covers
      them all, not one comment each.
    - Decide items get no reply until the user has chosen.
    - Then close what was addressed (see below).
7. **Report** in chat at the end of each pass:
    - checks: passing / failing, with anything rerun as flaky or blocked outside the PR;
    - what was fixed, each with its commit sha, and the threads answered, resolved or hidden — saying which;
    - rebases, with the base sha they moved onto;
    - decisions still open, and reviewers who have not reviewed yet (`pendingReviewers`).
8. **Keep watching until the PR is merged.** While the PR is open, never end a turn without a `gh_pr.py wait <n>`
   running in the background — after a push, after green, and while decisions wait on the user (start it before
   asking). It polls every minute and wakes you with what happened:

   | Event                  | Do                                                                              |
   |------------------------|---------------------------------------------------------------------------------|
   | `checks-done`          | Step 3 for whatever failed; when all passed, wait again                         |
   | `review`               | Step 4 on the items in `newActivity` (new, or edited by a bot)                  |
   | `behind` / `conflicts` | Rebase (see Keep up with the base), then step 2                                 |
   | `head-moved`           | Someone else pushed: `git pull --ff-only`, re-read the diff, then step 2        |
   | `timeout`              | Nothing happened for an hour: `state` once to be sure, then wait again          |
   | `merged` / `closed`    | Final report and stop — the only way the watch ends, besides the user saying so |

   A check handed to the user after three attempts, or a decision still open, does not stop the watch: a new review
   or a moved base still needs you.
9. **Ask the decisions** (see above), implement the answers, and go back to step 5.

## Close what was addressed

GitHub has two independent states, and the UI words them almost the same, so the report always says which one changed:

- **Resolved** — review threads only (`PRRT_…`). A resolved thread still shows as a collapsed box.
- **Hidden** (minimized) — any single comment or review body, with a reason: `RESOLVED`, `OUTDATED`, `DUPLICATE`,
  `OFF_TOPIC`. Only this greys it out to a one-liner. Hiding the first comment of a thread collapses the whole thread.

A review is three separate things — its body (`PRR_…`), its inline comments (`PRRC_…`) inside threads, and any
top-level comments (`IC_…`) the same reviewer posts — and closing one leaves the others on screen.

Close an item only after the push, once its point is fixed in the code or answered in the thread:

| Item                              | Opened by a bot                              | Opened by a person          |
|-----------------------------------|----------------------------------------------|-----------------------------|
| Inline thread (`PRRT_…`)          | `close <threadId>`: resolve and hide         | Reply only; they resolve it |
| Top-level finding (`IC_…`)        | `hide <id>`: these have no resolve           | Reply only; never hide it   |
| Review body (`PRR_…`)             | `hide <id>` once all its findings are closed | Leave it                    |
| Superseded placeholder or summary | `hide <id> --reason OUTDATED`                | —                           |

The reason is `RESOLVED` for a fixed or answered finding, `DUPLICATE` for a repeat of one already closed, and
`OUTDATED` when the code it points at is gone. A thread's `isOutdated` (the diff moved under it) is unrelated to the
`OUTDATED` reason and is not a reason to close it. People's threads are resolved and their comments hidden only when
the user says so. A finding that is not addressed stays visible, and the report says so.

**Verify** by running `state` again: `resolvedVisibleThreads` (resolved bot threads still on screen) is empty, and
nothing that was closed is left in `unresolvedThreads`, `comments` or the visible review bodies.

## Script commands

| Command                                | Returns (JSON)                                                      |
|----------------------------------------|---------------------------------------------------------------------|
| `state [<pr>] [--repo OWNER/REPO]`     | `viewer`, `pr`, `checks`, threads, `reviews`, `comments` (below)    |
| `logs [<pr>] [--repo …] [--lines N]`   | Each failed check with its failed-step log tail (150, `0` = all)    |
| `reply <threadId> <body\|->`           | The new comment's `id` and `url`                                    |
| `resolve <threadId>`                   | The thread's `id` and `isResolved`                                  |
| `close <threadId> [--reason R]`        | The thread resolved and its first comment hidden (R: `RESOLVED`)    |
| `hide <id> [--reason R]`               | The comment or review body hidden; a hidden one gets the new reason |
| `wait [<pr>] [--repo …] [--timeout S]` | `events`, `pr`, check counts and `newActivity` (below)              |

`pr` holds the head branch and sha, base, review decision and `pendingReviewers`; each check carries an `outcome`
of `pending`, `passed` or `failed`. Threads come as `unresolvedThreads` and `resolvedVisibleThreads` (resolved bot
threads still on screen). Comments and reviews carry `isBot` and `isMinimized`; hidden top-level comments and
hidden review bodies are left out. `<pr>` is a number, a URL or a branch. All ids come from `state`.

`wait` polls `state` every `--interval` seconds (60) and exits on the first change that needs the watcher: `merged`,
`closed`, `head-moved`, `checks-done` (pending checks all finished), `behind`, `conflicts` (the merge state turned
`BEHIND` or `DIRTY`), `review` (a thread comment, review or top-level comment by anyone but `viewer` is new or edited),
or `timeout` after `--timeout` seconds (3600, `0` = never). Several events can come at once. Transient `gh` errors are
retried; it fails only after five in a row.

## Guardrails

- Push only new commits to the PR's head branch; the one exception is a rebase onto the base when the PR is behind or
  conflicting, pushed with `--force-with-lease`. Never rewrite history otherwise, merge, or touch another branch.
- Never stop watching an open PR on your own: keep a `wait` running until it is merged or closed.
- Never make CI green by weakening it, and never retry a real failure into passing.
- Never decide an architectural or trade-off question on the user's behalf; never reply to a Decide item before the
  user has chosen.
- Never fix a behavior finding before a test reproduces it, unless it cannot reasonably be tested and the reply says
  why.
- Never resolve or hide anything whose point is not addressed in the code or answered in the thread, and never resolve
  or hide a person's comment unless the user says so.
- Do not invent a check result or a reviewer's intent: unreadable logs or ambiguous comments are reported as such.
