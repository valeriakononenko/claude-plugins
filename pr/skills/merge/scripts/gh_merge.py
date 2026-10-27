#!/usr/bin/env python3
"""Merge helper for the pr:merge skill, built on the gh and git CLIs.

`ready` says whether a PR can be merged now — only the viewer's own PRs ever can — and how this repository merges: the
methods it allows, the one its base branch history shows (squash commits titled "… (#n)", merge commits "Merge pull
request #n"), auto-merge and merge queue, and every blocker. `merge` merges the PR with a given method, pinned to the
head commit that was checked, and deletes the remote branch unless GitHub does it or other PRs still target it; on a PR
someone already merged it only deletes the remote branch. `branches` fetches with --prune and classifies every local
branch: delete (its PR is merged, or its upstream is gone and its content is in the base), update (yours and behind the
base: merge the base in and push), fast-forward (someone else's, behind its upstream), or ask (merged with extra
commits, closed unmerged, diverged from its upstream).

Requires an authenticated gh (`gh auth status`) and git 2.38+. Every command prints JSON to stdout.
"""
import argparse
import json
import re
import subprocess
import sys

sys.dont_write_bytecode = True

METHODS = ("squash", "merge", "rebase")
FAILED_CONCLUSIONS = {"FAILURE", "TIMED_OUT", "CANCELLED", "STARTUP_FAILURE", "ACTION_REQUIRED", "ERROR"}
PASSED_CONCLUSIONS = {"SUCCESS", "NEUTRAL", "SKIPPED"}
PENDING_STATES = {"QUEUED", "IN_PROGRESS", "WAITING", "PENDING", "REQUESTED", "EXPECTED"}
SQUASH_SUBJECT_RE = re.compile(r"\(#\d+\)$")
MERGE_SUBJECT_RE = re.compile(r"^Merge pull request #\d+")
HISTORY_DEPTH = 30

PR_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  viewer { login }
  repository(owner: $owner, name: $repo) {
    squashMergeAllowed mergeCommitAllowed rebaseMergeAllowed autoMergeAllowed deleteBranchOnMerge
    viewerDefaultMergeMethod squashMergeCommitTitle squashMergeCommitMessage
    pullRequest(number: $number) {
      number url title state isDraft isCrossRepository author { login }
      headRefName headRefOid baseRefName mergeable mergeStateStatus reviewDecision
      autoMergeRequest { mergeMethod }
      mergeCommit { oid }
      mergedBy { login }
      commits(last: 1) { nodes { commit { statusCheckRollup { contexts(first: 100) { nodes {
        __typename
        ... on CheckRun { name status conclusion isRequired(pullRequestNumber: $number) }
        ... on StatusContext { context state isRequired(pullRequestNumber: $number) }
      } } } } } }
    }
  }
}
"""

BASE_QUERY = """
query($owner: String!, $repo: String!, $base: String!, $ref: String!, $depth: Int!) {
  repository(owner: $owner, name: $repo) {
    mergeQueue(branch: $base) { id }
    ref(qualifiedName: $ref) { target { ... on Commit {
      history(first: $depth) { nodes { oid messageHeadline parents { totalCount } } }
    } } }
  }
}
"""


class GhError(Exception):
    pass


def run(cmd, cwd=None, stdin=None, check=True):
    try:
        done = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True)
    except FileNotFoundError:
        raise GhError(f"{cmd[0]} is not installed")
    if check and done.returncode != 0:
        raise GhError(f"{' '.join(cmd[:3])} failed: {done.stderr.strip() or done.stdout.strip()}")
    return done


def gh(*args, stdin=None):
    return run(["gh", *args], stdin=stdin).stdout


def git(*args, cwd=None, check=True):
    return run(["git", *args], cwd=cwd, check=check).stdout.strip()


def git_ok(*args, cwd=None):
    return run(["git", *args], cwd=cwd, check=False).returncode == 0


def graphql(query, **variables):
    args = ["api", "graphql", "-f", f"query={query}"]
    for name, value in variables.items():
        args += ["-F" if isinstance(value, int) else "-f", f"{name}={value}"]
    result = json.loads(gh(*args))
    if result.get("errors"):
        raise GhError("GraphQL: " + "; ".join(e.get("message", str(e)) for e in result["errors"]))
    return result["data"]


def emit(value):
    json.dump(value, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def resolve_pr(ref, repo):
    """Return (owner, name, number) for a PR number, URL or branch; the current branch's PR when ref is None."""
    args = ["pr", "view", *([ref] if ref else []), "--json", "number,url"]
    if repo:
        args += ["--repo", repo]
    view = json.loads(gh(*args))
    owner, name = view["url"].split("github.com/")[1].split("/")[:2]
    return owner, name, view["number"]


def check_outcome(node):
    if node["__typename"] == "StatusContext":
        state = node["state"]
        return "pending" if state in PENDING_STATES else "passed" if state == "SUCCESS" else "failed"
    conclusion = node.get("conclusion")
    if node["status"] != "COMPLETED" or conclusion is None:
        return "pending"
    return "passed" if conclusion in PASSED_CONCLUSIONS else "failed"


def summarize_checks(pr):
    nodes = pr["commits"]["nodes"]
    rollup = (nodes[0]["commit"].get("statusCheckRollup") or {}) if nodes else {}
    summary = {"passed": 0, "failed": [], "pending": [], "requiredFailed": [], "requiredPending": []}
    for node in (rollup.get("contexts") or {}).get("nodes", []):
        name = node.get("name") or node.get("context")
        outcome = check_outcome(node)
        if outcome == "passed":
            summary["passed"] += 1
            continue
        summary[outcome].append(name)
        if node.get("isRequired"):
            summary["requiredFailed" if outcome == "failed" else "requiredPending"].append(name)
    return summary


def allowed_methods(repo):
    flags = {"squash": "squashMergeAllowed", "merge": "mergeCommitAllowed", "rebase": "rebaseMergeAllowed"}
    return [m for m in METHODS if repo[flags[m]]]


def history_convention(history, allowed, default):
    """Infer the merge method from the base branch's recent commits; fall back to the viewer's default."""
    counts = {"squash": 0, "merge": 0, "other": 0}
    for commit in history:
        if commit["parents"]["totalCount"] > 1 and MERGE_SUBJECT_RE.match(commit["messageHeadline"]):
            counts["merge"] += 1
        elif commit["parents"]["totalCount"] == 1 and SQUASH_SUBJECT_RE.search(commit["messageHeadline"]):
            counts["squash"] += 1
        else:
            counts["other"] += 1
    if len(allowed) == 1:
        return allowed[0], "only method allowed", counts
    seen = [m for m in ("squash", "merge") if m in allowed and counts[m]]
    if seen:
        method = max(seen, key=lambda m: counts[m])
        return method, f"{counts[method]} of the last {len(history)} base commits", counts
    if "rebase" in allowed and counts["other"]:
        return "rebase", "no squash or merge commits on the base", counts
    fallback = (default or "").lower()
    return (fallback if fallback in allowed else allowed[0]), "viewer's default method", counts


def blockers_of(pr, checks, auto, viewer):
    found = []
    author = (pr["author"] or {}).get("login")
    if author != viewer:
        found.append(f"not your PR: opened by {author}")
    if pr["state"] == "CLOSED":
        found.append("closed without merging")
    if pr["isDraft"]:
        found.append("draft")
    if pr["mergeable"] == "CONFLICTING" or pr["mergeStateStatus"] == "DIRTY":
        found.append("conflicts with the base")
    if pr["mergeStateStatus"] == "BEHIND":
        found.append("behind the base and branch protection requires it up to date")
    if pr["reviewDecision"] == "CHANGES_REQUESTED":
        found.append("changes requested")
    if pr["reviewDecision"] == "REVIEW_REQUIRED":
        found.append("approving review required")
    if checks["requiredFailed"]:
        found.append("required checks failed: " + ", ".join(checks["requiredFailed"]))
    if checks["requiredPending"] and not auto:
        found.append("required checks pending: " + ", ".join(checks["requiredPending"]))
    if pr["mergeStateStatus"] == "BLOCKED" and not found and not checks["requiredPending"]:
        found.append("blocked by branch protection or rulesets")
    return found


def collect_ready(owner, name, number):
    data = graphql(PR_QUERY, owner=owner, repo=name, number=number)
    repo = data["repository"]
    pr = repo["pullRequest"]
    base = graphql(BASE_QUERY, owner=owner, repo=name, base=pr["baseRefName"],
                   ref=f"refs/heads/{pr['baseRefName']}", depth=HISTORY_DEPTH)["repository"]
    history = ((base.get("ref") or {}).get("target") or {}).get("history", {}).get("nodes", [])
    allowed = allowed_methods(repo)
    method, why, counts = history_convention(history, allowed, repo["viewerDefaultMergeMethod"])
    viewer = data["viewer"]["login"]
    checks = summarize_checks(pr)
    queue = bool(base.get("mergeQueue"))
    auto_possible = queue or repo["autoMergeAllowed"]
    hard = blockers_of(pr, checks, auto=False, viewer=viewer)
    waiting_only = bool(checks["requiredPending"]) and blockers_of(pr, checks, auto=True, viewer=viewer) == []
    return {
        "viewer": viewer,
        "pr": {
            "number": pr["number"], "url": pr["url"], "title": pr["title"], "state": pr["state"],
            "isDraft": pr["isDraft"], "author": (pr["author"] or {}).get("login"),
            "isCrossRepository": pr["isCrossRepository"], "head": pr["headRefName"], "headOid": pr["headRefOid"],
            "base": pr["baseRefName"], "mergeable": pr["mergeable"], "mergeStateStatus": pr["mergeStateStatus"],
            "reviewDecision": pr["reviewDecision"], "autoMerge": (pr["autoMergeRequest"] or {}).get("mergeMethod"),
            "mergeCommit": (pr["mergeCommit"] or {}).get("oid"), "mergedBy": (pr["mergedBy"] or {}).get("login"),
        },
        "checks": checks,
        "repo": {
            "allowedMethods": allowed, "viewerDefault": repo["viewerDefaultMergeMethod"],
            "autoMergeAllowed": repo["autoMergeAllowed"], "mergeQueue": queue,
            "deleteBranchOnMerge": repo["deleteBranchOnMerge"],
            "squashTitle": repo["squashMergeCommitTitle"], "squashMessage": repo["squashMergeCommitMessage"],
        },
        "convention": {
            "method": method, "why": why, "counts": counts,
            "recent": [c["messageHeadline"] for c in history[:8]],
        },
        "blockers": hard,
        "ready": not hard,
        "canAutoMerge": waiting_only and auto_possible,
        "unstable": bool(checks["failed"]) and not checks["requiredFailed"],
    }


def cmd_ready(args):
    emit(collect_ready(*resolve_pr(args.pr, args.repo)))


def delete_remote_branch(owner, name, ready):
    pr = ready["pr"]
    if pr["author"] != ready["viewer"]:
        return False, f"not your PR: opened by {pr['author']}"
    if ready["repo"]["deleteBranchOnMerge"]:
        return False, "GitHub deletes head branches on merge in this repository"
    if pr["isCrossRepository"]:
        return False, "the head branch lives in a fork"
    ref = f"repos/{owner}/{name}/git/ref/heads/{pr['head']}"
    if run(["gh", "api", ref, "--silent"], check=False).returncode != 0:
        return False, "already deleted"
    dependents = json.loads(gh("pr", "list", "--repo", f"{owner}/{name}", "--base", pr["head"], "--state", "open",
                               "--json", "number"))
    if dependents:
        return False, "open PRs target it: " + ", ".join(f"#{d['number']}" for d in dependents)
    gone = run(["gh", "api", "-X", "DELETE", f"repos/{owner}/{name}/git/refs/heads/{pr['head']}"], check=False)
    if gone.returncode != 0:
        return False, gone.stderr.strip() or "delete failed"
    return True, None


def cmd_merge(args):
    owner, name, number = resolve_pr(args.pr, args.repo)
    before = collect_ready(owner, name, number)
    if before["pr"]["state"] == "MERGED":
        deleted, kept = delete_remote_branch(owner, name, before)
        emit({"pr": number, "url": before["pr"]["url"], "alreadyMerged": True, "state": "MERGED",
              "mergedBy": before["pr"]["mergedBy"], "mergeCommit": before["pr"]["mergeCommit"],
              "remoteBranchDeleted": deleted, "remoteBranchKept": kept})
        return
    if not args.method:
        raise GhError("--method is required to merge an open PR")
    if args.method not in before["repo"]["allowedMethods"] and not before["repo"]["mergeQueue"]:
        raise GhError(f"{args.method} is not allowed here: {', '.join(before['repo']['allowedMethods'])}")
    if before["blockers"] and not (args.auto and before["canAutoMerge"]):
        raise GhError("not mergeable: " + "; ".join(before["blockers"]))
    head = args.match_head or before["pr"]["headOid"]
    command = ["pr", "merge", str(number), "--repo", f"{owner}/{name}", f"--{args.method}",
               "--match-head-commit", head]
    if args.auto:
        command.append("--auto")
    if args.subject:
        command += ["--subject", args.subject]
    if args.body_file:
        command += ["--body-file", args.body_file]
    gh(*command, stdin=sys.stdin.read() if args.body_file == "-" else None)
    after = collect_ready(owner, name, number)
    result = {
        "pr": after["pr"]["number"], "url": after["pr"]["url"], "alreadyMerged": False, "method": args.method,
        "headOid": head,
        "state": after["pr"]["state"], "mergeCommit": after["pr"]["mergeCommit"],
        "autoMerge": after["pr"]["autoMerge"], "remoteBranchDeleted": False, "remoteBranchKept": None,
    }
    if after["pr"]["state"] == "MERGED":
        result["remoteBranchDeleted"], result["remoteBranchKept"] = delete_remote_branch(owner, name, after)
    emit(result)


def default_base(remote):
    head = git("symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD", check=False)
    if head:
        return head.split("/", 1)[1]
    return json.loads(gh("repo", "view", "--json", "defaultBranchRef"))["defaultBranchRef"]["name"]


def local_branches():
    fmt = "%(refname:short)%00%(objectname)%00%(upstream:track)%00%(worktreepath)"
    rows = []
    for line in git("for-each-ref", "refs/heads", f"--format={fmt}").splitlines():
        branch, oid, track, worktree = line.split("\0")
        remote = git("config", f"branch.{branch}.remote", check=False)
        merge = git("config", f"branch.{branch}.merge", check=False)
        rows.append({
            "name": branch, "oid": oid, "worktree": worktree or None,
            "upstream": f"{remote}/{merge.removeprefix('refs/heads/')}" if remote and merge else None,
            "upstreamBranch": merge.removeprefix("refs/heads/") or None,
            "upstreamGone": track == "[gone]",
            "aheadUpstream": int(m.group(1)) if (m := re.search(r"ahead (\d+)", track)) else 0,
            "behindUpstream": int(m.group(1)) if (m := re.search(r"behind (\d+)", track)) else 0,
        })
    return rows


def content_in(base_ref, branch):
    """True when merging the branch into base_ref would change nothing — also after a squash merge."""
    if git_ok("merge-base", "--is-ancestor", branch, base_ref):
        return True
    merged = run(["git", "merge-tree", "--write-tree", base_ref, branch], check=False)
    if merged.returncode != 0:
        return False
    return merged.stdout.split("\n", 1)[0].strip() == git("rev-parse", f"{base_ref}^{{tree}}")


def find_pr(head):
    prs = json.loads(gh("pr", "list", "--head", head, "--state", "all", "--limit", "20",
                        "--json", "number,state,author,headRefOid,baseRefName,url,mergedAt"))
    for state in ("OPEN", "MERGED", "CLOSED"):
        found = sorted((p for p in prs if p["state"] == state), key=lambda p: p.get("mergedAt") or "", reverse=True)
        if found:
            p = found[0]
            return {"number": p["number"], "state": p["state"], "author": (p["author"] or {}).get("login"),
                    "headOid": p["headRefOid"], "base": p["baseRefName"], "url": p["url"]}
    return None


def relation_to_pr_head(oid, pr_head):
    if oid == pr_head:
        return "at-pr-head", 0
    if not git_ok("cat-file", "-e", f"{pr_head}^{{commit}}"):
        return "pr-head-unknown", None
    if git_ok("merge-base", "--is-ancestor", oid, pr_head):
        return "behind-pr-head", 0
    if git_ok("merge-base", "--is-ancestor", pr_head, oid):
        return "ahead-of-pr-head", int(git("rev-list", "--count", f"{pr_head}..{oid}"))
    return "diverged-from-pr-head", None


def authored_only_by(email, base_ref, branch):
    authors = set(git("log", "--format=%ae", f"{base_ref}..{branch}").split())
    return authors <= {email}


def is_dirty(worktree):
    return bool(worktree) and bool(git("status", "--porcelain", cwd=worktree))


def classify(row, base_ref, viewer, email):
    branch = row["name"]
    pr = find_pr(row["upstreamBranch"] or branch)
    row["pr"] = pr
    row["inBase"] = content_in(base_ref, branch)
    row["unmergedCommits"] = int(git("rev-list", "--count", f"{base_ref}..{branch}"))
    row["behindBase"] = int(git("rev-list", "--count", f"{branch}..{base_ref}"))
    row["mine"] = (pr["author"] == viewer) if pr else authored_only_by(email, base_ref, branch)
    row["dirty"] = is_dirty(row["worktree"])

    if pr and pr["state"] == "MERGED":
        relation, extra = relation_to_pr_head(row["oid"], pr["headOid"])
        row["prHead"] = relation
        if relation in ("at-pr-head", "behind-pr-head") or row["inBase"]:
            return "delete", f"PR #{pr['number']} merged"
        if relation == "ahead-of-pr-head":
            return "ask", f"PR #{pr['number']} merged, but the branch has {extra} commits after it"
        return "ask", f"PR #{pr['number']} merged, but the branch does not match its head"
    if row["upstreamGone"] and row["inBase"]:
        return "delete", "upstream deleted and its content is already in the base"
    if pr and pr["state"] == "CLOSED" and not row["inBase"]:
        return "ask", f"PR #{pr['number']} closed without merging"
    if row["upstreamGone"]:
        return "ask", "upstream deleted without a merged PR, and its content is not in the base"
    if row["aheadUpstream"] and row["behindUpstream"]:
        return "ask", f"diverged from {row['upstream']}"
    if not row["mine"]:
        if row["behindUpstream"]:
            return "fast-forward", f"someone else's branch, {row['behindUpstream']} behind {row['upstream']}"
        return "skip", "someone else's branch"
    if row["behindBase"]:
        return "update", f"{row['behindBase']} commits behind {base_ref}"
    if row["behindUpstream"]:
        return "fast-forward", f"{row['behindUpstream']} behind {row['upstream']}"
    return "up-to-date", None


def cmd_branches(args):
    if not args.no_fetch:
        git("fetch", "--prune", args.remote)
    base = args.base or default_base(args.remote)
    base_ref = f"{args.remote}/{base}"
    viewer = gh("api", "user", "--jq", ".login").strip()
    email = git("config", "user.email", check=False)
    current = git("branch", "--show-current", check=False) or None
    main_worktree = git("rev-parse", "--path-format=absolute", "--git-common-dir").removesuffix("/.git")
    rows = local_branches()

    base_row = next((r for r in rows if r["name"] == base), None)
    if base_row:
        base_row["dirty"] = is_dirty(base_row["worktree"])
        ahead = int(git("rev-list", "--count", f"{base_ref}..{base}"))
        behind = int(git("rev-list", "--count", f"{base}..{base_ref}"))
        base_row["action"] = "ask" if ahead else "fast-forward" if behind else "up-to-date"
        base_row["reason"] = f"{ahead} local commits not on {base_ref}" if ahead else None

    plan = []
    for row in rows:
        if row["name"] == base:
            continue
        row["action"], row["reason"] = classify(row, base_ref, viewer, email)
        row["push"] = row["action"] == "update" and bool(row["upstream"]) and not row["upstreamGone"]
        plan.append(row)

    emit({
        "viewer": viewer, "remote": args.remote, "base": base, "baseRef": base_ref,
        "baseOid": git("rev-parse", base_ref), "current": current, "mainWorktree": main_worktree,
        "baseBranch": base_row,
        "branches": plan,
        "counts": {a: sum(1 for r in plan if r["action"] == a)
                   for a in ("delete", "update", "fast-forward", "ask", "skip", "up-to-date")},
    })


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ready", help="Can the PR merge now, and how does this repository merge")
    p.add_argument("pr", nargs="?", help="PR number, URL or branch (default: the current branch's PR)")
    p.add_argument("--repo", help="OWNER/REPO when not run inside the repository")
    p.set_defaults(fn=cmd_ready)

    p = sub.add_parser("merge", help="Merge the PR, pinned to its checked head, and delete the remote branch")
    p.add_argument("pr", nargs="?", help="PR number, URL or branch (default: the current branch's PR)")
    p.add_argument("--repo", help="OWNER/REPO when not run inside the repository")
    p.add_argument("--method", choices=METHODS, help="Required unless the PR is already merged")
    p.add_argument("--auto", action="store_true", help="Enable auto-merge / join the merge queue")
    p.add_argument("--match-head", help="Head sha the PR must still have (default: the head `ready` saw)")
    p.add_argument("--subject", help="Merge commit subject (default: the repository's setting)")
    p.add_argument("--body-file", help="Merge commit body file, or - for stdin (default: the repository's setting)")
    p.set_defaults(fn=cmd_merge)

    p = sub.add_parser("branches", help="Fetch with --prune and classify every local branch")
    p.add_argument("--remote", default="origin")
    p.add_argument("--base", help="Base branch (default: the remote's HEAD)")
    p.add_argument("--no-fetch", action="store_true")
    p.set_defaults(fn=cmd_branches)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.fn(args)
    except GhError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
