---
name: merge
description: >
  Merge a pull request the way the repository merges — squash, merge commit or rebase, read from its settings and the
  base branch history — once it is ready, then put the local branches in order: delete the ones whose PR is merged
  (squash-merged included), fast-forward the base, merge the base into your other branches, resolve the conflicts
  that have a clear answer and push them. Hands back a PR that is not ready, a conflict that means choosing between
  your branch and the base, and a merged branch that still has unpushed work. Use when the user asks to merge a PR,
  "merge #412", "ship it", or, after a merge, to clean up / sync / tidy local branches, delete merged branches, or
  bring the branches up to date with main.
---

# Merge a pull request and tidy the local branches

Two duties, in this order:

1. **Merge.** Check the PR can merge now and merge it with the method the repository uses. A PR that is not ready is
   reported, not forced.
2. **Sync.** Fetch with `--prune`, fast-forward the base, delete the local branches that are merged, and merge the
   base into the user's other branches and push them.

`/pr:merge --sync` (or "tidy my branches") skips step 1. Without a PR argument, step 1 takes the current branch's PR.

The bundled script reads the state; git and `gh` do the rest:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/gh_merge.py" <command> …
```

It needs an authenticated `gh` (`gh auth status`) and git 2.38+, and runs inside the repository.

## Authority

Invoking this skill authorizes **merging the PR it names** when it is the user's own and ready, **deleting that PR's
head branch** on the remote, **deleting local branches** the script classifies as `delete`, and **merge commits pushed
to the user's own branches**. Nothing else:

- Never merge someone else's PR — only the viewer's own, whoever asks — and never touch its remote branch.
- Never merge with `--admin`, never bypass a required check, review or merge queue, and never merge a PR other than
  the one named.
- Never force-push, rebase or otherwise rewrite a branch here; the base comes in as a merge commit.
- Never push a branch without an upstream, never push someone else's branch, and never push to the base.
- Never discard the user's work: a dirty worktree is stashed and restored, a branch with commits that are on no
  remote and in no merged PR is kept and asked about.

## Merge

1. `gh_merge.py ready [<pr>]`. It returns the PR, its checks (with the required ones), the repository's
   `allowedMethods`, `convention` (the method the base branch history shows, why, and its last subjects),
   `mergeQueue`, `autoMergeAllowed`, `blockers`, `ready`, `canAutoMerge` and `unstable`.
2. **Already merged** (`pr.state` `MERGED`, by anyone): nothing to merge. Run `gh_merge.py merge [<pr>]` without
   `--method` — it only deletes the remote branch if it is still there (`alreadyMerged: true`) — say who merged it
   (`mergedBy`, `mergeCommit`), and go on to the sync. **Closed** without merging: report it and offer the sync alone.
3. **Not ready.** Report every blocker in one list and stop:
    - not your PR → it is not yours to merge, and that is final: no offer to merge it anyway; the sync alone is fine;
    - failing checks, unaddressed reviews, conflicts or a branch behind its base → offer `pr:watch`, which fixes them;
    - only required checks still running and `canAutoMerge` → merge with `--auto` (step 5): GitHub merges it when they
      pass, and a merge queue takes it the same way;
    - draft, missing approval → the user's or a reviewer's move; say whose.
4. **Choose the method**: `convention.method`. It is the only allowed one, or what most recent PRs on the base used,
   or the user's default on GitHub. Ask only when the evidence is thin (`why` is the viewer's default and more than one
   method is allowed) or the user named another. `unstable` (non-required checks failing) is mentioned, not a stop.
5. `gh_merge.py merge [<pr>] --method <m> [--auto]`. The merge is pinned to the head `ready` saw: a push since then
   fails it, and the PR is read again. The commit title and body follow the repository's settings (`squashTitle`,
   `squashMessage`); pass `--subject` / `--body-file` only when the user asks or the repository's custom differs from
   its setting (e.g. squash bodies written from the PR description in recent history).
6. **Remote branch.** After a merge the script deletes the head branch unless GitHub does it (`deleteBranchOnMerge`),
   it lives in a fork, or open PRs target it (deleting it would close them) — `remoteBranchKept` says why.
7. **Auto-merge.** When the result is `autoMerge` rather than `MERGED`, wait for it with
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/watch/scripts/gh_pr.py" wait <n>` in the background and go on to the sync
   once it reports `merged`. A `checks-done` with failures, or `closed`, ends the skill with a report.

## Sync the local branches

1. **Read the plan.** `gh_merge.py branches` fetches `origin` with `--prune` and returns `base`, `baseRef`,
   `current`, `baseBranch` and every other local branch with an `action` and its `reason`:

    - `delete` — its PR is merged and the branch is at or behind the PR head, or its upstream is gone and its
      content is already in the base. Delete it.
    - `update` — the user's own and behind the base. Merge the base in, and push when `push` is true.
    - `fast-forward` — behind its upstream (someone pushed), or someone else's branch that is. `merge --ff-only`.
    - `ask` — merged with commits after the PR head, closed unmerged, upstream gone with unmerged work, or diverged
      from its upstream. Ask the user.
    - `skip` — someone else's branch with nothing to pull. `up-to-date` — nothing to do.

   "The user's own" means the PR's author is the viewer, or, without a PR, every commit not on the base is authored
   with the user's `user.email`. A PR checked out to review a colleague's work is theirs: it is never merged into or
   pushed.
2. **Where each branch is worked.** A branch checked out in a worktree (`worktree`) is updated there with
   `git -C <worktree> …`; any other branch is checked out in the main worktree. A `dirty` worktree is stashed first
   (`git stash push -u -m "pr:merge sync"`) and popped after; a pop that conflicts is left stashed and reported.
3. **Base first.** `baseBranch.action` `fast-forward`: `git -C <worktree> merge --ff-only <baseRef>` when it is
   checked out, else `git fetch . <baseRef>:<base>`. `ask` (local commits on the base) is reported and the base left
   alone; the other branches still merge `baseRef`.
4. **Delete.** `git branch -D <name>` — `-d` refuses a squash-merged branch, and the script has already proven it
   merged. The current branch is left for the base first. A branch checked out in another worktree: `git worktree
   remove <path>` when that worktree is clean, else keep both and report it.
5. **Update.** For each `update` branch: if it is also behind its upstream, `git merge --ff-only <upstream>` first;
   then `git merge --no-edit <baseRef>`.
    - **Conflicts.** Resolve one when the intent of both sides is clear and can be kept — imports, neighbouring edits,
      lockfiles regenerated with the project's tool, a symbol renamed on the base that the branch uses. When
      resolving means choosing between the branch's behavior and what landed on the base, `git merge --abort` and
      bring it to the user as a decision, the way `pr:watch` does: the two sides, the options, a recommendation.
    - **Verify** a resolved conflict with the build and the tests that cover the conflicting files before committing
      it. A clean merge is not tested here: CI runs on the push.
    - **Push** with a plain `git push` when `push` is true. A rejected push means the upstream moved meanwhile:
      `git fetch`, `git merge --no-edit <upstream>` (conflicts as above) and push again — never `--force`.
6. **Fast-forward** the `fast-forward` branches with `git merge --ff-only <upstream>`, or
   `git fetch . <upstream>:<name>` when the branch is not checked out.
7. **Ask** about the `ask` branches in one `AskUserQuestion` (up to four; the rest in the report), each with what is on
   it — `git log --oneline <baseRef>..<name>` — and the options that fit: delete, keep, push it as a new PR.
8. **Return** to the branch the user started on (or the base, if it was deleted) and restore its stash.

## Report

At the end, in chat:

- the merge: PR, method and why, merge commit sha, or auto-merge enabled; the remote branch deleted or kept and why;
- the base: fast-forwarded from → to, or left alone and why;
- deleted branches, each with its PR;
- updated branches: merged, conflicts resolved (which files, how verified), pushed or local only;
- fast-forwarded and skipped branches;
- what waits on the user: blockers, conflicts brought back as decisions, `ask` branches, a stash that did not pop.

## Script commands

| Command                                          | Returns (JSON)                                                 |
|--------------------------------------------------|----------------------------------------------------------------|
| `ready [<pr>] [--repo OWNER/REPO]`               | PR, checks, allowed methods, convention, merge queue, blockers |
| `merge [<pr>] --method M [--auto] [--subject …]` | `state`, `mergeCommit`, `autoMerge`, remote branch kept or not |
| `branches [--remote R] [--base B] [--no-fetch]`  | Base, base branch state, every local branch with its action    |

`<pr>` is a number, a URL or a branch; without it, the current branch's PR. `merge` refuses a PR with blockers unless
`--auto` is given and only required checks are pending, and a method the repository does not allow. On a PR that is
already merged it merges nothing, needs no `--method`, and only deletes the remote branch when it is still there.

## Guardrails

- Merge only the user's own PR, only the named one, only when `ready` (or with `--auto` when only required checks are
  pending); never `--admin`.
- Use the repository's method; never pick one the history contradicts without the user saying so.
- Delete only branches the script classifies as `delete`, and remove only clean worktrees.
- Never force-push, rebase or reset a branch; never push someone else's branch, a branch without an upstream, or the
  base.
- Never leave the user's uncommitted work anywhere but where it was, or in a reported stash.
- Never resolve a conflict by choosing a side when the choice changes behavior: that is the user's decision.
