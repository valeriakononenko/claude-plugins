#!/usr/bin/env python3
"""GitHub pull-request helper for the pr:watch skill, built on the gh CLI.

One `state` call returns everything the watch loop needs in a single JSON document: the PR head, every check on the
head commit with its outcome, the unresolved review threads, the latest review per reviewer, the top-level comments
and the reviewers still pending. `logs` prints the failing part of each failed GitHub Actions job, `reply` answers a
review thread, `resolve` resolves one, `close` resolves it and hides its comments, `hide` minimizes any comment or
review body, and `wait` polls the PR until something needs the watcher: checks finished, new review activity, the
branch fell behind its base or into conflict, someone else pushed, or the PR was merged or closed.

Requires an authenticated gh (`gh auth status`). Every command prints JSON to stdout.
"""
import argparse
import json
import subprocess
import sys
import time

sys.dont_write_bytecode = True

HIDE_REASONS = ("RESOLVED", "OUTDATED", "DUPLICATE", "OFF_TOPIC")
FAILED_CONCLUSIONS = {"FAILURE", "TIMED_OUT", "CANCELLED", "STARTUP_FAILURE", "ACTION_REQUIRED", "ERROR"}
PASSED_CONCLUSIONS = {"SUCCESS", "NEUTRAL", "SKIPPED"}
PENDING_STATES = {"QUEUED", "IN_PROGRESS", "WAITING", "PENDING", "REQUESTED", "EXPECTED"}
BASE_EVENTS = {"BEHIND": "behind", "DIRTY": "conflicts"}
WAIT_RETRIES = 5

STATE_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  viewer { login }
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      number url title state isDraft author { login }
      headRefName headRefOid baseRefName baseRefOid mergeable mergeStateStatus reviewDecision
      headRepository { nameWithOwner }
      reviewRequests(first: 20) {
        nodes { requestedReviewer { ... on User { login } ... on Team { slug } ... on Bot { login } } }
      }
      commits(last: 1) { nodes { commit { oid statusCheckRollup { state contexts(first: 100) { nodes {
        __typename
        ... on CheckRun {
          name status conclusion detailsUrl databaseId
          checkSuite { app { slug } workflowRun { databaseId workflow { name } } }
        }
        ... on StatusContext { context state targetUrl }
      } } } } } }
      reviewThreads(first: 100) { nodes {
        id isResolved isOutdated path line originalLine
        comments(first: 50) { nodes {
          id databaseId author { __typename login } body createdAt isMinimized minimizedReason url
        } }
      } }
      reviews(last: 50) { nodes {
        id author { __typename login } state body submittedAt commit { oid } isMinimized minimizedReason url
      } }
      comments(last: 50) { nodes {
        id databaseId author { __typename login } body createdAt isMinimized minimizedReason url
      } }
    }
  }
}
"""

REPLY_MUTATION = """
mutation($thread: ID!, $body: String!) {
  addPullRequestReviewThreadReply(input: {pullRequestReviewThreadId: $thread, body: $body}) {
    comment { id url }
  }
}
"""

RESOLVE_MUTATION = """
mutation($thread: ID!) { resolveReviewThread(input: {threadId: $thread}) { thread { id isResolved } } }
"""

THREAD_COMMENTS_QUERY = """
query($id: ID!) { node(id: $id) { ... on PullRequestReviewThread { comments(first: 1) { nodes { id } } } } }
"""

MINIMIZED_QUERY = """
query($id: ID!) { node(id: $id) { ... on Minimizable { isMinimized minimizedReason } } }
"""

UNMINIMIZE_MUTATION = """
mutation($id: ID!) { unminimizeComment(input: {subjectId: $id}) { unminimizedComment { isMinimized } } }
"""

MINIMIZE_MUTATION = """
mutation($id: ID!, $reason: ReportedContentClassifiers!) {
  minimizeComment(input: {subjectId: $id, classifier: $reason}) { minimizedComment { isMinimized minimizedReason } }
}
"""


class GhError(Exception):
    pass


def gh(*args, stdin=None):
    try:
        done = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True)
    except FileNotFoundError:
        raise GhError("gh is not installed: https://cli.github.com")
    if done.returncode != 0:
        raise GhError(f"gh {' '.join(args[:2])} failed: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


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


def read_body(path):
    return sys.stdin.read() if path == "-" else open(path).read()


def resolve_pr(ref, repo):
    """Return (owner, name, number) for a PR number, URL or branch; the current branch's PR when ref is None."""
    args = ["pr", "view", *([ref] if ref else []), "--json", "number,url"]
    if repo:
        args += ["--repo", repo]
    view = json.loads(gh(*args))
    owner, name = view["url"].split("github.com/")[1].split("/")[:2]
    return owner, name, view["number"]


def login(actor):
    return (actor or {}).get("login") or "ghost"


def is_bot(actor):
    return (actor or {}).get("__typename") == "Bot"


def comment_entry(c):
    return {"id": c["id"], "author": login(c["author"]), "isBot": is_bot(c["author"]), "body": c["body"],
            "createdAt": c["createdAt"], "isMinimized": c["isMinimized"], "url": c["url"]}


def check_entry(node):
    if node["__typename"] == "StatusContext":
        state = node["state"]
        outcome = "pending" if state in PENDING_STATES else "passed" if state == "SUCCESS" else "failed"
        return {"name": node["context"], "kind": "status", "outcome": outcome, "raw": state, "url": node["targetUrl"]}
    run = (node.get("checkSuite") or {}).get("workflowRun") or {}
    conclusion = node.get("conclusion")
    if node["status"] != "COMPLETED" or conclusion is None:
        outcome = "pending"
    elif conclusion in PASSED_CONCLUSIONS:
        outcome = "passed"
    else:
        outcome = "failed"
    return {
        "name": node["name"],
        "kind": "actions" if run else "check",
        "app": ((node.get("checkSuite") or {}).get("app") or {}).get("slug"),
        "workflow": (run.get("workflow") or {}).get("name"),
        "outcome": outcome,
        "raw": conclusion or node["status"],
        "runId": run.get("databaseId"),
        "jobId": node["databaseId"] if run else None,
        "url": node["detailsUrl"],
    }


def latest_reviews(nodes):
    """Keep the newest review per author, plus every review whose body is still visible."""
    newest = {}
    for review in nodes:
        newest[login(review["author"])] = review["id"]
    return [
        {
            "id": r["id"],
            "author": login(r["author"]),
            "isBot": is_bot(r["author"]),
            "state": r["state"],
            "body": r["body"],
            "commit": (r.get("commit") or {}).get("oid"),
            "submittedAt": r["submittedAt"],
            "url": r["url"],
            "isMinimized": r["isMinimized"],
            "latest": newest[login(r["author"])] == r["id"],
        }
        for r in nodes
        if newest[login(r["author"])] == r["id"] or (r["body"].strip() and not r["isMinimized"])
    ]


def collect_state(owner, name, number):
    data = graphql(STATE_QUERY, owner=owner, repo=name, number=number)
    pr = data["repository"]["pullRequest"]
    commit = pr["commits"]["nodes"][0]["commit"] if pr["commits"]["nodes"] else {}
    rollup = commit.get("statusCheckRollup") or {}
    checks = [check_entry(n) for n in (rollup.get("contexts") or {}).get("nodes", [])]
    summary = {k: sum(1 for c in checks if c["outcome"] == k) for k in ("pending", "failed", "passed")}
    threads = [
        {
            "threadId": t["id"],
            "path": t["path"],
            "line": t["line"] or t["originalLine"],
            "isOutdated": t["isOutdated"],
            "comments": [comment_entry(c) for c in t["comments"]["nodes"]],
        }
        for t in pr["reviewThreads"]["nodes"]
        if not t["isResolved"]
    ]
    resolved_visible = [
        {"threadId": t["id"], "path": t["path"], "line": t["line"] or t["originalLine"],
         "commentId": t["comments"]["nodes"][0]["id"], "author": login(t["comments"]["nodes"][0]["author"])}
        for t in pr["reviewThreads"]["nodes"]
        if t["isResolved"] and t["comments"]["nodes"]
        and is_bot(t["comments"]["nodes"][0]["author"]) and not t["comments"]["nodes"][0]["isMinimized"]
    ]
    pending_reviewers = [
        (r["requestedReviewer"] or {}).get("login") or (r["requestedReviewer"] or {}).get("slug")
        for r in pr["reviewRequests"]["nodes"]
    ]
    return {
        "viewer": data["viewer"]["login"],
        "pr": {
            "repo": f"{owner}/{name}",
            "number": pr["number"],
            "url": pr["url"],
            "title": pr["title"],
            "state": pr["state"],
            "isDraft": pr["isDraft"],
            "author": login(pr["author"]),
            "head": pr["headRefName"],
            "headRepo": (pr["headRepository"] or {}).get("nameWithOwner"),
            "headSha": pr["headRefOid"],
            "base": pr["baseRefName"],
            "baseSha": pr["baseRefOid"],
            "mergeable": pr["mergeable"],
            "mergeStateStatus": pr["mergeStateStatus"],
            "reviewDecision": pr["reviewDecision"],
            "pendingReviewers": [r for r in pending_reviewers if r],
        },
        "checks": {"rollup": rollup.get("state"), **summary, "items": checks},
        "unresolvedThreads": threads,
        "resolvedVisibleThreads": resolved_visible,
        "reviews": latest_reviews(pr["reviews"]["nodes"]),
        "comments": [comment_entry(c) for c in pr["comments"]["nodes"] if not c["isMinimized"]],
    }


def tail(text, lines):
    kept = text.rstrip("\n").split("\n")
    return "\n".join(kept[-lines:]) if lines and len(kept) > lines else "\n".join(kept)


def cmd_state(args):
    emit(collect_state(*resolve_pr(args.pr, args.repo)))


def cmd_logs(args):
    owner, name, number = resolve_pr(args.pr, args.repo)
    state = collect_state(owner, name, number)
    out = []
    for check in state["checks"]["items"]:
        if check["outcome"] != "failed":
            continue
        entry = {k: check[k] for k in ("name", "kind", "workflow", "raw", "runId", "jobId", "url") if k in check}
        if check["kind"] == "actions" and check["jobId"]:
            try:
                log = gh("run", "view", "--repo", f"{owner}/{name}", "--job", str(check["jobId"]), "--log-failed")
                entry["log"] = tail(log, args.lines) or "(no failed-step output; open the url)"
            except GhError as e:
                entry["log"] = f"(log unavailable: {e})"
        else:
            entry["log"] = "(not a GitHub Actions job; read it at the url)"
        out.append(entry)
    emit({"headSha": state["pr"]["headSha"], "failed": out})


def cmd_reply(args):
    data = graphql(REPLY_MUTATION, thread=args.thread, body=read_body(args.body))
    emit(data["addPullRequestReviewThreadReply"]["comment"])


def cmd_resolve(args):
    emit(graphql(RESOLVE_MUTATION, thread=args.thread)["resolveReviewThread"]["thread"])


def minimize(subject, reason):
    """Hide a comment or review body; re-classifies an already hidden one, which minimizeComment alone ignores."""
    current = graphql(MINIMIZED_QUERY, id=subject)["node"] or {}
    if "isMinimized" not in current:
        raise GhError(f"{subject} is not a comment or review that can be hidden")
    if current["isMinimized"]:
        if (current.get("minimizedReason") or "").upper() == reason:
            return {"id": subject, **current}
        graphql(UNMINIMIZE_MUTATION, id=subject)
    done = graphql(MINIMIZE_MUTATION, id=subject, reason=reason)["minimizeComment"]["minimizedComment"]
    return {"id": subject, **done}


def cmd_hide(args):
    emit(minimize(args.subject, args.reason))


def cmd_close(args):
    thread = graphql(RESOLVE_MUTATION, thread=args.thread)["resolveReviewThread"]["thread"]
    node = graphql(THREAD_COMMENTS_QUERY, id=args.thread)["node"] or {}
    first = ((node.get("comments") or {}).get("nodes") or [None])[0]
    emit({**thread, "comment": minimize(first["id"], args.reason) if first else None})


def activity(state):
    """Everything others wrote on the PR, as node id → body, so both new and edited items show up."""
    items = [c for t in state["unresolvedThreads"] for c in t["comments"]] + state["reviews"] + state["comments"]
    return {i["id"]: i["body"] for i in items if i["author"] != state["viewer"]}


def wait_events(before, now):
    pr = now["pr"]
    if pr["state"] != "OPEN":
        return [pr["state"].lower()]
    events = []
    if pr["headSha"] != before["pr"]["headSha"]:
        events.append("head-moved")
    elif before["checks"]["pending"] and not now["checks"]["pending"]:
        events.append("checks-done")
    status = pr["mergeStateStatus"]
    if status in BASE_EVENTS and status != before["pr"]["mergeStateStatus"]:
        events.append(BASE_EVENTS[status])
    if activity(now).items() - activity(before).items():
        events.append("review")
    return events


def wait_summary(events, before, now):
    seen = activity(before)
    return {
        "events": events,
        "pr": now["pr"],
        "checks": {k: now["checks"][k] for k in ("rollup", "pending", "failed", "passed")},
        "newActivity": [i for i, body in activity(now).items() if seen.get(i) != body],
    }


def poll(owner, name, number):
    for attempt in range(WAIT_RETRIES):
        try:
            return collect_state(owner, name, number)
        except GhError:
            if attempt == WAIT_RETRIES - 1:
                raise
            time.sleep(30)


def cmd_wait(args):
    target = resolve_pr(args.pr, args.repo)
    before = poll(*target)
    deadline = time.monotonic() + args.timeout if args.timeout else None
    while True:
        if deadline and time.monotonic() >= deadline:
            emit(wait_summary(["timeout"], before, before))
            return
        time.sleep(args.interval)
        now = poll(*target)
        events = wait_events(before, now)
        if events:
            emit(wait_summary(events, before, now))
            return
        if now["pr"]["mergeStateStatus"] == "UNKNOWN":
            now["pr"]["mergeStateStatus"] = before["pr"]["mergeStateStatus"]
        before = now


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    for command, fn, help_text in (
        ("state", cmd_state, "Snapshot: head, checks, unresolved threads, reviews, comments, pending reviewers"),
        ("logs", cmd_logs, "Failed-step output of every failed GitHub Actions job on the head commit"),
    ):
        p = sub.add_parser(command, help=help_text)
        p.add_argument("pr", nargs="?", help="PR number, URL or branch (default: the current branch's PR)")
        p.add_argument("--repo", help="OWNER/REPO when not run inside the repository")
        if command == "logs":
            p.add_argument("--lines", type=int, default=150, help="Keep the last N lines per job (0 = all)")
        p.set_defaults(fn=fn)

    p = sub.add_parser("wait", help="Poll the PR until something needs the watcher, then print what happened")
    p.add_argument("pr", nargs="?", help="PR number, URL or branch (default: the current branch's PR)")
    p.add_argument("--repo", help="OWNER/REPO when not run inside the repository")
    p.add_argument("--interval", type=int, default=60, help="Seconds between polls")
    p.add_argument("--timeout", type=int, default=3600, help="Stop with a `timeout` event after N seconds (0 = never)")
    p.set_defaults(fn=cmd_wait)

    p = sub.add_parser("reply", help="Reply inside a review thread")
    p.add_argument("thread", help="Thread node id (PRRT_…) from `state`")
    p.add_argument("body", help="Path to the reply body, or - for stdin")
    p.set_defaults(fn=cmd_reply)

    p = sub.add_parser("resolve", help="Resolve a review thread")
    p.add_argument("thread", help="Thread node id (PRRT_…) from `state`")
    p.set_defaults(fn=cmd_resolve)

    p = sub.add_parser("close", help="Resolve a review thread and hide it (minimize its first comment)")
    p.add_argument("thread", help="Thread node id (PRRT_…) from `state`")
    p.add_argument("--reason", choices=HIDE_REASONS, default="RESOLVED")
    p.set_defaults(fn=cmd_close)

    p = sub.add_parser("hide", help="Hide (minimize) a comment or review body")
    p.add_argument("subject", help="Node id from `state`: IC_… (top-level), PRRC_… (inline) or PRR_… (review body)")
    p.add_argument("--reason", choices=HIDE_REASONS, default="RESOLVED")
    p.set_defaults(fn=cmd_hide)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.fn(args)
    except GhError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
