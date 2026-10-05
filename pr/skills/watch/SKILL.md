---
name: watch
description: >
  Shepherd an open pull request to green: wait for its GitHub Actions / checks, fix whatever fails at the root cause,
  then work through every review (human and bot): fix what is clearly fixable, reply where the reviewer is wrong,
  and hand the architectural and trade-off calls back to the user as weighed options with a recommendation. Commits
  and pushes the fixes to the PR branch and repeats until checks pass and no actionable review is left. Use right
  after a PR is opened or pushed, and whenever the user asks to watch / babysit / shepherd a PR, to get CI green, to
  fix failing checks or actions, to address / handle / work through review comments, or to "take care of the PR".
---

# Watch a pull request

Takes a PR from "opened" to "green, every review answered". Two duties, in a loop:

1. **Checks.** Wait for every check on the head commit. A failure is fixed at its root cause, verified locally and
   pushed.
2. **Reviews.** Every unresolved thread, review body and top-level comment is read against the current code, then
   fixed, answered or escalated to the user.

The loop stops when the checks pass, no actionable feedback is left, and only the user's decisions remain.

The bundled script gathers the PR state in one call and answers review threads:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/watch/scripts/gh_pr.py" <command> …
```

It needs an authenticated `gh` (`gh auth status`). With no PR argument it uses the current branch's PR.

## Authority

Invoking this skill authorizes **new commits pushed to the PR's head branch**, and replies on the PR. Nothing else:

- Never force-push, amend, rebase or squash pushed commits, and never push to the base branch or another branch.
- Never merge, close, mark ready / draft, request or dismiss reviews, or edit the PR title and description.
- Never weaken a gate to get green: no skipped or deleted tests, no `continue-on-error`, no `--no-verify`, no lowered
  coverage or lint thresholds, no `# noqa` / `@ts-ignore` / `eslint-disable` to silence a real finding, no retrying a
  genuine failure until it passes. A change to what CI enforces (workflow files, thresholds, required checks) is a
  decision for the user.

## Triage review feedback

Read each item **against the current code** — a later bot pass saying "no issues" is not proof an earlier finding
was fixed, and an outdated thread may still be valid on the moved lines. Then sort it into exactly one bucket:

- **Fix** — bugs, missed edge cases, error handling, security findings with a local fix, missing or weak tests,
  naming, readability, dead code, docs, typos, style: one obvious right answer within the PR's scope. Fix it, verify,
  push, reply with the commit.
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

## Procedure

1. **Locate the PR and sync.** `gh_pr.py state [<pr>]`. Check out the head branch (`gh pr checkout <n>`) and pull. If
   the working tree is dirty, stop and ask — never stash or discard the user's changes. If the PR is from a fork you
   cannot push to, or is merged / closed, report and stop.
2. **Wait for the checks** when any are pending: run `gh pr checks <n> --watch --interval 30` in the background and
   continue when it exits — meanwhile, triage the reviews that are already there.
3. **Fix failing checks** as above.
4. **Work the reviews.** From `state`: every `unresolvedThreads` entry, every `reviews` body (`CHANGES_REQUESTED`
   first), and every top-level `comments` entry not written by `viewer`. Triage each, apply all the Fix items, collect
   the Decide items.
5. **Commit and push.** Group related fixes into a few focused commits in the repository's message style (one per
   failing check or review topic beats one per comment), run the relevant tests and linters, then `git push`.
6. **Reply on the PR**, in the language the PR is written in, after the push so the commit exists:
    - Fix: `gh_pr.py reply <threadId> -` with a line on what changed and the short sha.
    - Answer: the reason and the evidence, in one or two sentences, without defensiveness.
    - Resolve (`gh_pr.py resolve <threadId>`) threads opened by bots once fixed or answered. Leave threads opened by
      people for them to resolve, unless the user says otherwise.
    - A review body or top-level comment has no thread: answer with one `gh pr comment <n> --body-file -` that covers
      them all, not one comment each.
    - Decide items get no reply until the user has chosen.
7. **Loop.** A push starts new checks and often a new bot review: back to step 2. Stop when the checks are green and
   nothing actionable is left, or when everything left is waiting on the user.
8. **Ask the decisions** (see above), implement the answers, and go back to step 5.
9. **Report** in chat:
    - checks: passing / failing, with anything rerun as flaky or blocked outside the PR;
    - what was fixed, each with its commit sha, and the threads answered or resolved;
    - decisions still open, and reviewers who have not reviewed yet (`pendingReviewers`).

Reviews that arrive later are not seen by one run. To keep watching, run it on an interval — `/loop 15m /pr:watch
<n>` — and the next tick picks up whatever came in.

## Script commands

| Command                              | Returns (JSON)                                                         |
|--------------------------------------|------------------------------------------------------------------------|
| `state [<pr>] [--repo OWNER/REPO]`   | `viewer`, `pr`, `checks`, `unresolvedThreads`, `reviews`, `comments`   |
| `logs [<pr>] [--repo …] [--lines N]` | Each failed check with its failed-step log tail (150 lines, `0` = all) |
| `reply <threadId> <body\|->`         | The new comment's `id` and `url`                                       |
| `resolve <threadId>`                 | The thread's `id` and `isResolved`                                     |

`pr` holds the head branch and sha, base, review decision and `pendingReviewers`; each check carries an `outcome`
of `pending`, `passed` or `failed`. `<pr>` is a number, a URL or a branch. Thread ids (`PRRT_…`) come from `state`.

## Guardrails

- Push only new commits to the PR's head branch; never rewrite history, merge, or touch another branch.
- Never make CI green by weakening it, and never retry a real failure into passing.
- Never decide an architectural or trade-off question on the user's behalf; never reply to a Decide item before the
  user has chosen.
- Never resolve a thread whose point is not addressed in the code or answered in the thread.
- Do not invent a check result or a reviewer's intent: unreadable logs or ambiguous comments are reported as such.
