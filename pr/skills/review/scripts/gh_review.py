#!/usr/bin/env python3
"""GitHub pull-request reviewer helper for the pr:review skill, built on the gh CLI.

`context` returns what a review starts from in one JSON document: the PR and its description, commits and files, the
Jira keys found in the branch, title, commits and description, the checks, every bot finding with whether it was
answered, the viewer's earlier reviews and threads, and the review ledger. `jira` reads the task behind a key.
`post` publishes one review — a body, new inline threads and replies in earlier threads — atomically, as a pending
review that is submitted at the end or deleted on failure. `ledger` and `record` keep the per-PR ledger of problems
(posted, fixed, dismissed…) that makes a re-review pick up where the last one stopped.

Requires an authenticated gh (`gh auth status`); `jira` reads JIRA_ORG, JIRA_EMAIL and JIRA_TOKEN from the
environment, ./.env or ~/.jira.env. Every command prints JSON to stdout.
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

EVENTS = ("COMMENT", "REQUEST_CHANGES", "APPROVE")
FAILED_CONCLUSIONS = {"FAILURE", "TIMED_OUT", "CANCELLED", "STARTUP_FAILURE", "ACTION_REQUIRED", "ERROR"}
PASSED_CONCLUSIONS = {"SUCCESS", "NEUTRAL", "SKIPPED"}
PENDING_STATES = {"QUEUED", "IN_PROGRESS", "WAITING", "PENDING", "REQUESTED", "EXPECTED"}
JIRA_KEY_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9]{1,9}-[1-9][0-9]{0,6})(?![0-9])")
NOT_JIRA_PREFIXES = {"UTF", "SHA", "ISO", "RFC", "CVE", "CWE", "GHSA", "HTTP", "TLS", "SSL", "AES", "RSA", "ES", "PR"}
JIRA_REQUIRED = ("JIRA_ORG", "JIRA_EMAIL", "JIRA_TOKEN")
JIRA_DOTENV = (".env", os.path.expanduser("~/.jira.env"))
CRITERIA_FIELD_RE = re.compile(r"acceptance|criteria|definition of done|criterios|aceptaci", re.I)
BOT_BODY_LIMIT = 4000
LEDGER_HOME = Path(os.environ.get("PR_REVIEW_HOME") or os.path.expanduser("~/.claude/pr-review"))

CONTEXT_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  viewer { login }
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      id number url title body state isDraft author { login }
      headRefName headRefOid baseRefName baseRefOid mergeStateStatus reviewDecision changedFiles
      reviewRequests(first: 20) {
        nodes { requestedReviewer { ... on User { login } ... on Team { slug } ... on Bot { login } } }
      }
      commits(first: 100) { totalCount nodes { commit { oid messageHeadline messageBody } } }
      files(first: 100) { nodes { path additions deletions changeType } }
      latest: commits(last: 1) { nodes { commit { statusCheckRollup { state contexts(first: 100) { nodes {
        __typename
        ... on CheckRun { name status conclusion detailsUrl checkSuite { workflowRun { databaseId } } }
        ... on StatusContext { context state targetUrl }
      } } } } } }
      reviewThreads(first: 100) { nodes {
        id isResolved isOutdated path line originalLine
        comments(first: 50) { nodes {
          id author { __typename login } body createdAt isMinimized url
        } }
      } }
      reviews(last: 100) { nodes {
        id author { __typename login } state body submittedAt commit { oid } isMinimized url
      } }
      comments(last: 100) { nodes { id author { __typename login } body createdAt isMinimized url } }
    }
  }
}
"""

PR_ID_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  viewer { login }
  repository(owner: $owner, name: $repo) { pullRequest(number: $number) { id headRefOid author { login } } }
}
"""

ADD_REVIEW = """
mutation($pr: ID!, $commit: GitObjectID!) {
  addPullRequestReview(input: {pullRequestId: $pr, commitOID: $commit}) { pullRequestReview { id } }
}
"""

ADD_THREAD = """
mutation($review: ID!, $path: String!, $body: String!, $line: Int!, $side: DiffSide!, $startLine: Int,
         $startSide: DiffSide) {
  addPullRequestReviewThread(input: {pullRequestReviewId: $review, path: $path, body: $body, line: $line,
                                     side: $side, startLine: $startLine, startSide: $startSide}) {
    thread { id comments(first: 1) { nodes { id url } } }
  }
}
"""

ADD_REPLY = """
mutation($review: ID!, $thread: ID!, $body: String!) {
  addPullRequestReviewThreadReply(input: {pullRequestReviewId: $review, pullRequestReviewThreadId: $thread,
                                          body: $body}) {
    comment { id url }
  }
}
"""

SUBMIT_REVIEW = """
mutation($review: ID!, $event: PullRequestReviewEvent!, $body: String) {
  submitPullRequestReview(input: {pullRequestReviewId: $review, event: $event, body: $body}) {
    pullRequestReview { id url state submittedAt }
  }
}
"""

DELETE_REVIEW = """
mutation($review: ID!) { deletePullRequestReview(input: {pullRequestReviewId: $review}) { pullRequestReview { id } } }
"""

RESOLVE_THREAD = """
mutation($thread: ID!) { resolveReviewThread(input: {threadId: $thread}) { thread { id isResolved } } }
"""


def gh(*args, stdin=None):
    try:
        done = subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True)
    except FileNotFoundError:
        raise GhError("gh is not installed: https://cli.github.com")
    if done.returncode != 0:
        raise GhError(f"gh {' '.join(args[:2])} failed: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout


def graphql(query, **variables):
    payload = {"query": query, "variables": {k: v for k, v in variables.items() if v is not None}}
    result = json.loads(gh("api", "graphql", "--input", "-", stdin=json.dumps(payload)))
    if result.get("errors"):
        raise GhError("GraphQL: " + "; ".join(e.get("message", str(e)) for e in result["errors"]))
    return result["data"]


def emit(value):
    json.dump(value, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def read_json(path):
    return json.loads(sys.stdin.read() if path == "-" else Path(path).read_text())


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    name = login(actor).lower()
    return (actor or {}).get("__typename") == "Bot" or name.endswith("[bot]") or name.endswith("-bot")


def clip(text, limit=BOT_BODY_LIMIT):
    return text if len(text) <= limit else text[:limit] + f"\n… [{len(text) - limit} more characters]"


def jira_keys(branch, title, commits, body):
    found = {}
    sources = [("branch", branch), ("title", title)]
    sources += [("commit", f"{c['messageHeadline']}\n{c['messageBody']}") for c in commits]
    sources.append(("description", body or ""))
    for source, text in sources:
        for key in JIRA_KEY_RE.findall(text or ""):
            if key.split("-")[0] in NOT_JIRA_PREFIXES:
                continue
            entry = found.setdefault(key, {"key": key, "sources": []})
            if source not in entry["sources"]:
                entry["sources"].append(source)
    rank = {"branch": 0, "title": 1, "commit": 2, "description": 3}
    return sorted(found.values(), key=lambda e: (min(rank[s] for s in e["sources"]), -len(e["sources"])))


def check_entry(node):
    if node["__typename"] == "StatusContext":
        state = node["state"]
        outcome = "pending" if state in PENDING_STATES else "passed" if state == "SUCCESS" else "failed"
        return {"name": node["context"], "outcome": outcome, "raw": state, "url": node["targetUrl"]}
    conclusion = node.get("conclusion")
    if node["status"] != "COMPLETED" or conclusion is None:
        outcome = "pending"
    elif conclusion in PASSED_CONCLUSIONS:
        outcome = "passed"
    else:
        outcome = "failed"
    run = (node.get("checkSuite") or {}).get("workflowRun") or {}
    return {"name": node["name"], "outcome": outcome, "raw": conclusion or node["status"],
            "runId": run.get("databaseId"), "url": node["detailsUrl"]}


def comment_entry(c, limit=None):
    body = clip(c["body"], limit) if limit else c["body"]
    return {"id": c["id"], "author": login(c["author"]), "isBot": is_bot(c["author"]), "body": body,
            "createdAt": c["createdAt"], "isMinimized": c["isMinimized"], "url": c["url"]}


def thread_entry(t):
    return {"threadId": t["id"], "path": t["path"], "line": t["line"] or t["originalLine"],
            "isResolved": t["isResolved"], "isOutdated": t["isOutdated"],
            "comments": [comment_entry(c) for c in t["comments"]["nodes"]]}


def bot_findings(pr):
    """Every finding a bot left, with whether it is still open and what humans answered."""
    findings = []
    for t in pr["reviewThreads"]["nodes"]:
        comments = t["comments"]["nodes"]
        if not comments or not is_bot(comments[0]["author"]):
            continue
        first = comments[0]
        status = "open" if not t["isResolved"] else "hidden" if first["isMinimized"] else "resolved"
        findings.append({
            "kind": "thread", "id": t["id"], "author": login(first["author"]), "status": status,
            "path": t["path"], "line": t["line"] or t["originalLine"], "isOutdated": t["isOutdated"],
            "body": clip(first["body"]), "url": first["url"], "createdAt": first["createdAt"],
            "replies": [comment_entry(c, 1500) for c in comments[1:]],
        })
    for c in pr["comments"]["nodes"]:
        if is_bot(c["author"]):
            findings.append({"kind": "comment", "id": c["id"], "author": login(c["author"]),
                             "status": "hidden" if c["isMinimized"] else "open", "body": clip(c["body"]),
                             "url": c["url"], "createdAt": c["createdAt"]})
    for r in pr["reviews"]["nodes"]:
        if is_bot(r["author"]) and r["body"].strip():
            findings.append({"kind": "review", "id": r["id"], "author": login(r["author"]),
                             "status": "hidden" if r["isMinimized"] else "open", "body": clip(r["body"]),
                             "url": r["url"], "createdAt": r["submittedAt"], "commit": (r["commit"] or {}).get("oid")})
    return findings


def ledger_path(owner, name, number):
    return LEDGER_HOME / owner / name / f"{number}.json"


def load_ledger(owner, name, number):
    path = ledger_path(owner, name, number)
    if not path.exists():
        return {"pr": f"{owner}/{name}#{number}", "task": None, "reviews": [], "problems": {}}
    return json.loads(path.read_text())


def save_ledger(owner, name, number, ledger):
    path = ledger_path(owner, name, number)
    path.parent.mkdir(parents=True, exist_ok=True)
    ledger["updatedAt"] = now_iso()
    path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n")
    return path


def next_problem_id(ledger):
    numbers = [int(k[1:]) for k in ledger["problems"] if re.fullmatch(r"P\d+", k)]
    return f"P{max(numbers, default=0) + 1}"


def collect_context(owner, name, number):
    data = graphql(CONTEXT_QUERY, owner=owner, repo=name, number=number)
    viewer = data["viewer"]["login"]
    pr = data["repository"]["pullRequest"]
    commits = [n["commit"] for n in pr["commits"]["nodes"]]
    latest = pr["latest"]["nodes"][0]["commit"] if pr["latest"]["nodes"] else {}
    rollup = latest.get("statusCheckRollup") or {}
    checks = [check_entry(n) for n in (rollup.get("contexts") or {}).get("nodes", [])]
    requested = [(r["requestedReviewer"] or {}).get("login") or (r["requestedReviewer"] or {}).get("slug")
                 for r in pr["reviewRequests"]["nodes"]]
    threads = pr["reviewThreads"]["nodes"]
    viewer_reviews = [
        {"id": r["id"], "state": r["state"], "body": r["body"], "submittedAt": r["submittedAt"],
         "commit": (r["commit"] or {}).get("oid"), "url": r["url"]}
        for r in pr["reviews"]["nodes"] if login(r["author"]) == viewer and r["state"] != "PENDING"
    ]
    ledger = load_ledger(owner, name, number)
    reviewed = [r["commit"] for r in ledger["reviews"] if r.get("commit")] or [r["commit"] for r in viewer_reviews]
    return {
        "viewer": viewer,
        "pr": {
            "repo": f"{owner}/{name}", "number": pr["number"], "url": pr["url"], "title": pr["title"],
            "body": pr["body"], "state": pr["state"], "isDraft": pr["isDraft"], "author": login(pr["author"]),
            "viewerIsAuthor": login(pr["author"]) == viewer, "head": pr["headRefName"], "headSha": pr["headRefOid"],
            "base": pr["baseRefName"], "baseSha": pr["baseRefOid"], "mergeStateStatus": pr["mergeStateStatus"],
            "reviewDecision": pr["reviewDecision"], "reviewRequestedFromViewer": viewer in requested,
            "changedFiles": pr["changedFiles"],
        },
        "jiraKeys": jira_keys(pr["headRefName"], pr["title"], commits, pr["body"]),
        "commits": [{"sha": c["oid"], "headline": c["messageHeadline"], "body": c["messageBody"]} for c in commits],
        "commitsTruncated": pr["commits"]["totalCount"] > len(commits),
        "files": [{"path": f["path"], "change": f["changeType"], "additions": f["additions"],
                   "deletions": f["deletions"]} for f in pr["files"]["nodes"]],
        "filesTruncated": pr["changedFiles"] > len(pr["files"]["nodes"]),
        "checks": {"rollup": rollup.get("state"),
                   **{k: sum(1 for c in checks if c["outcome"] == k) for k in ("pending", "failed", "passed")},
                   "notPassed": [c for c in checks if c["outcome"] != "passed"]},
        "botFindings": bot_findings(pr),
        "viewerReviews": viewer_reviews,
        "viewerThreads": [thread_entry(t) for t in threads
                          if t["comments"]["nodes"] and login(t["comments"]["nodes"][0]["author"]) == viewer],
        "otherOpenThreads": [thread_entry(t) for t in threads
                             if not t["isResolved"] and t["comments"]["nodes"]
                             and login(t["comments"]["nodes"][0]["author"]) != viewer
                             and not is_bot(t["comments"]["nodes"][0]["author"])],
        "lastReviewedSha": reviewed[-1] if reviewed else None,
        "ledgerPath": str(ledger_path(owner, name, number)),
        "ledger": ledger,
        "nextProblemId": next_problem_id(ledger),
    }


def diff_lines(owner, name, number):
    """Map path → {"RIGHT": {line: hunk}, "LEFT": {line: hunk}} for every line a review comment may anchor to."""
    lines = {}
    page = 1
    while True:
        files = json.loads(gh("api", f"repos/{owner}/{name}/pulls/{number}/files?per_page=100&page={page}"))
        for f in files:
            sides = lines.setdefault(f["filename"], {"RIGHT": {}, "LEFT": {}})
            hunk = 0
            left = right = 0
            for row in (f.get("patch") or "").split("\n"):
                header = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", row)
                if header:
                    hunk += 1
                    left, right = int(header.group(1)), int(header.group(2))
                elif row.startswith("+"):
                    sides["RIGHT"][right] = hunk
                    right += 1
                elif row.startswith("-"):
                    sides["LEFT"][left] = hunk
                    left += 1
                elif row.startswith(" "):
                    sides["RIGHT"][right] = hunk
                    sides["LEFT"][left] = hunk
                    left += 1
                    right += 1
        if len(files) < 100:
            return lines
        page += 1


def anchor_problem(comment, lines):
    """Why the comment cannot be an inline thread, or None when its lines are part of the diff."""
    sides = lines.get(comment["path"])
    if sides is None:
        return "file is not part of the PR diff"
    side = comment.get("side", "RIGHT")
    hunk = sides[side].get(comment["line"])
    if hunk is None:
        return f"line {comment['line']} ({side}) is not in the diff"
    start = comment.get("startLine")
    if start and sides[comment.get("startSide", side)].get(start) != hunk:
        return f"lines {start}-{comment['line']} are not in one diff hunk"
    return None


def permalink(owner, name, sha, comment):
    lines = f"L{comment['startLine']}-L{comment['line']}" if comment.get("startLine") else f"L{comment['line']}"
    return f"https://github.com/{owner}/{name}/blob/{sha}/{comment['path']}#{lines}"


def compose_body(spec, outside, owner, name, sha):
    body = (spec.get("body") or "").rstrip()
    if not outside:
        return body
    items = [f"- {permalink(owner, name, sha, c)}\n\n{indent(c['body'])}" for c in outside]
    section = f"**{spec.get('outsideHeading', 'Outside the diff')}**\n\n" + "\n\n".join(items)
    return f"{body}\n\n{section}" if body else section


def indent(text):
    return "\n".join(f"  {row}" if row else "" for row in text.strip().split("\n"))


def validate_spec(spec, args, viewer, author, head):
    event = spec.get("event")
    if event not in EVENTS:
        raise GhError(f"event must be one of {', '.join(EVENTS)}")
    if spec.get("commit") != head:
        raise GhError(f"the PR head moved to {head}; the review was built on {spec.get('commit')}. Re-check first.")
    if event == "APPROVE" and not args.approved_by_user:
        raise GhError("APPROVE needs --approved-by-user: approve only after the user confirmed it for this head")
    if event != "COMMENT" and viewer == author:
        raise GhError(f"{viewer} authored this PR; GitHub only allows COMMENT on your own PR")
    if event != "APPROVE" and not (spec.get("body") or spec.get("comments") or spec.get("replies")):
        raise GhError("nothing to post: body, comments and replies are all empty")


def cmd_context(args):
    emit(collect_context(*resolve_pr(args.pr, args.repo)))


def cmd_post(args):
    owner, name, number = resolve_pr(args.pr, args.repo)
    spec = read_json(args.spec)
    meta = graphql(PR_ID_QUERY, owner=owner, repo=name, number=number)
    pr = meta["repository"]["pullRequest"]
    viewer, head = meta["viewer"]["login"], pr["headRefOid"]
    validate_spec(spec, args, viewer, login(pr["author"]), head)

    lines = diff_lines(owner, name, number)
    inline, outside = [], []
    for comment in spec.get("comments", []):
        reason = anchor_problem(comment, lines)
        if reason:
            outside.append({**comment, "notInline": reason})
        else:
            inline.append(comment)
    body = compose_body(spec, outside, owner, name, head)
    if args.dry_run:
        emit({"event": spec["event"], "commit": head, "body": body, "inline": inline, "movedToBody": outside,
              "replies": spec.get("replies", [])})
        return

    review_id = graphql(ADD_REVIEW, pr=pr["id"], commit=head)["addPullRequestReview"]["pullRequestReview"]["id"]
    posted, replied = [], []
    try:
        for c in inline:
            side = c.get("side", "RIGHT")
            thread = graphql(ADD_THREAD, review=review_id, path=c["path"], body=c["body"], line=c["line"],
                             side=side, startLine=c.get("startLine"),
                             startSide=c.get("startSide", side) if c.get("startLine") else None)
            thread = thread["addPullRequestReviewThread"]["thread"]
            posted.append({**c, "threadId": thread["id"], "url": thread["comments"]["nodes"][0]["url"]})
        for r in spec.get("replies", []):
            reply = graphql(ADD_REPLY, review=review_id, thread=r["threadId"], body=r["body"])
            replied.append({**r, "url": reply["addPullRequestReviewThreadReply"]["comment"]["url"]})
        review = graphql(SUBMIT_REVIEW, review=review_id, event=spec["event"], body=body or None)
        review = review["submitPullRequestReview"]["pullRequestReview"]
    except GhError:
        graphql(DELETE_REVIEW, review=review_id)
        raise
    resolved = [graphql(RESOLVE_THREAD, thread=r["threadId"])["resolveReviewThread"]["thread"]
                for r in replied if r.get("resolve")]

    ledger = load_ledger(owner, name, number)
    ledger["reviews"].append({"id": review["id"], "url": review["url"], "event": spec["event"], "commit": head,
                              "submittedAt": review["submittedAt"], "kind": spec.get("kind", "review")})
    for c in posted + outside:
        if c.get("problem"):
            entry = ledger["problems"].setdefault(c["problem"], {"id": c["problem"]})
            entry.update({k: c[k] for k in ("title", "severity", "path", "line", "startLine", "side") if k in c})
            entry.update({"status": "posted", "postedIn": review["id"], "postedAt": head,
                          "threadId": c.get("threadId"), "url": c.get("url") or review["url"],
                          "inline": "threadId" in c, "body": c["body"]})
    for r in replied:
        if r.get("problem"):
            entry = ledger["problems"].setdefault(r["problem"], {"id": r["problem"], "threadId": r["threadId"]})
            entry.setdefault("rounds", []).append({"commit": head, "status": r.get("status"), "url": r["url"]})
            if r.get("status"):
                entry["status"] = r["status"]
    save_ledger(owner, name, number, ledger)
    emit({"review": review, "threads": [{k: p.get(k) for k in ("problem", "threadId", "url")} for p in posted],
          "replies": [{k: r.get(k) for k in ("problem", "threadId", "url", "status")} for r in replied],
          "resolved": resolved, "movedToBody": [{k: c.get(k) for k in ("problem", "path", "line", "notInline")}
                                                for c in outside]})


def cmd_ledger(args):
    owner, name, number = resolve_pr(args.pr, args.repo)
    ledger = load_ledger(owner, name, number)
    emit({"path": str(ledger_path(owner, name, number)), "nextProblemId": next_problem_id(ledger), **ledger})


def cmd_record(args):
    owner, name, number = resolve_pr(args.pr, args.repo)
    update = read_json(args.spec)
    ledger = load_ledger(owner, name, number)
    if "task" in update:
        ledger["task"] = update["task"]
    stamp = now_iso()
    for problem in update.get("problems", []):
        entry = ledger["problems"].setdefault(problem["id"], {"id": problem["id"]})
        if problem.get("status") and problem["status"] != entry.get("status"):
            entry.setdefault("history", []).append({"status": problem["status"], "at": stamp})
        entry.update(problem)
    path = save_ledger(owner, name, number, ledger)
    emit({"path": str(path), "nextProblemId": next_problem_id(ledger), **ledger})


def jira_credentials():
    env = {k: os.environ.get(k, "") for k in JIRA_REQUIRED}
    for candidate in JIRA_DOTENV:
        if all(env.values()):
            break
        try:
            text = Path(candidate).read_text()
        except OSError:
            continue
        for row in text.splitlines():
            key, sep, value = row.strip().partition("=")
            if sep and key.strip() in env and not env[key.strip()]:
                env[key.strip()] = value.strip().strip('"').strip("'")
    missing = [k for k in JIRA_REQUIRED if not env[k]]
    if missing:
        raise GhError(f"Missing {', '.join(missing)} (environment, ./.env or ~/.jira.env)")
    return env


def jira_get(env, path, params):
    url = f"https://{env['JIRA_ORG'].strip()}.atlassian.net/rest/api/3/{path}?{urllib.parse.urlencode(params)}"
    auth = base64.b64encode(f"{env['JIRA_EMAIL']}:{env['JIRA_TOKEN']}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        raise GhError(f"Jira GET {path} failed with HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")


def adf_text(node, depth=0):
    """Flatten Atlassian Document Format into readable Markdown-ish text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    kind = node.get("type")
    children = node.get("content") or []
    if kind == "text":
        text = node.get("text", "")
        for mark in node.get("marks") or []:
            if mark["type"] == "code":
                text = f"`{text}`"
            elif mark["type"] == "link":
                text = f"[{text}]({mark['attrs'].get('href')})"
        return text
    if kind == "hardBreak":
        return "\n"
    if kind in ("mention", "emoji", "status", "date"):
        attrs = node.get("attrs") or {}
        return attrs.get("text") or attrs.get("shortName") or attrs.get("timestamp") or ""
    if kind in ("inlineCard", "blockCard", "embedCard"):
        return (node.get("attrs") or {}).get("url", "")
    if kind in ("media", "mediaSingle", "mediaGroup"):
        return "[attachment]"
    if kind == "codeBlock":
        return "```\n" + "".join(adf_text(c) for c in children) + "\n```"
    if kind == "heading":
        return "#" * (node.get("attrs") or {}).get("level", 2) + " " + "".join(adf_text(c) for c in children)
    if kind in ("bulletList", "orderedList"):
        rows = []
        for i, item in enumerate(children, 1):
            marker = f"{i}." if kind == "orderedList" else "-"
            rows.append("  " * depth + f"{marker} " + adf_text(item, depth + 1).strip())
        return "\n".join(rows)
    if kind == "listItem":
        return "\n".join(adf_text(c, depth) for c in children)
    if kind == "taskItem":
        done = (node.get("attrs") or {}).get("state") == "DONE"
        return f"[{'x' if done else ' '}] " + "".join(adf_text(c) for c in children)
    if kind == "tableRow":
        return "| " + " | ".join(adf_text(c, depth).replace("\n", " ") for c in children) + " |"
    if kind in ("paragraph", "tableCell", "tableHeader"):
        return "".join(adf_text(c, depth) for c in children)
    if kind == "blockquote":
        return "\n".join("> " + row for row in "\n\n".join(adf_text(c, depth) for c in children).split("\n"))
    if kind == "rule":
        return "---"
    separator = "\n" if kind in ("table", "taskList") else "\n\n"
    return separator.join(t for t in (adf_text(c, depth) for c in children) if t)


def cmd_jira(args):
    env = jira_credentials()
    issue = jira_get(env, f"issue/{args.key}", {"fields": "*all", "expand": "names"})
    fields, names = issue["fields"], issue.get("names", {})
    site = f"https://{env['JIRA_ORG'].strip()}.atlassian.net"
    criteria = {names.get(k, k): adf_text(v) for k, v in fields.items()
                if v and CRITERIA_FIELD_RE.search(names.get(k, "")) and isinstance(v, (str, dict))}
    links = []
    for link in fields.get("issuelinks") or []:
        for direction, other in (("outward", link.get("outwardIssue")), ("inward", link.get("inwardIssue"))):
            if other:
                links.append({"relation": link["type"][direction], "key": other["key"],
                              "summary": other["fields"]["summary"], "status": other["fields"]["status"]["name"]})
    parent = fields.get("parent")
    comments = (fields.get("comment") or {}).get("comments") or []
    emit({
        "key": issue["key"], "url": f"{site}/browse/{issue['key']}", "type": fields["issuetype"]["name"],
        "status": fields["status"]["name"], "summary": fields["summary"],
        "priority": (fields.get("priority") or {}).get("name"),
        "assignee": (fields.get("assignee") or {}).get("displayName"),
        "labels": fields.get("labels") or [],
        "fixVersions": [v["name"] for v in fields.get("fixVersions") or []],
        "description": adf_text(fields.get("description")),
        "acceptanceCriteria": criteria,
        "parent": {"key": parent["key"], "summary": parent["fields"]["summary"],
                   "type": parent["fields"]["issuetype"]["name"]} if parent else None,
        "subtasks": [{"key": s["key"], "summary": s["fields"]["summary"], "status": s["fields"]["status"]["name"]}
                     for s in fields.get("subtasks") or []],
        "links": links,
        "comments": [{"author": (c.get("author") or {}).get("displayName"), "created": c["created"],
                      "body": adf_text(c.get("body"))} for c in comments[-args.comments:]] if args.comments else [],
    })


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def pr_args(p):
        p.add_argument("--pr", help="PR number, URL or branch (default: the current branch's PR)")
        p.add_argument("--repo", help="OWNER/REPO when not run inside the repository")

    p = sub.add_parser("context", help="PR, task keys, commits, files, checks, bot findings, earlier reviews, ledger")
    p.add_argument("pr", nargs="?", help="PR number, URL or branch (default: the current branch's PR)")
    p.add_argument("--repo", help="OWNER/REPO when not run inside the repository")
    p.set_defaults(fn=cmd_context)

    p = sub.add_parser("jira", help="Read a Jira issue: description, acceptance criteria, parent, links, comments")
    p.add_argument("key", help="Issue key, e.g. SHOP-123")
    p.add_argument("--comments", type=int, default=10, help="Keep the newest N comments (0 = none)")
    p.set_defaults(fn=cmd_jira)

    p = sub.add_parser("post", help="Publish one review: body, new inline threads and replies, then the event")
    p.add_argument("spec", help="Path to the review spec JSON, or - for stdin")
    p.add_argument("--dry-run", action="store_true", help="Validate anchors and print what would be posted")
    p.add_argument("--approved-by-user", action="store_true", help="Required for APPROVE")
    pr_args(p)
    p.set_defaults(fn=cmd_post)

    p = sub.add_parser("ledger", help="Show the review ledger of the PR")
    p.add_argument("pr", nargs="?", help="PR number, URL or branch (default: the current branch's PR)")
    p.add_argument("--repo", help="OWNER/REPO when not run inside the repository")
    p.set_defaults(fn=cmd_ledger)

    p = sub.add_parser("record", help="Merge problems (by id) and the task key into the ledger")
    p.add_argument("spec", help="Path to the update JSON, or - for stdin")
    pr_args(p)
    p.set_defaults(fn=cmd_record)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.fn(args)
    except GhError as e:
        sys.exit(str(e))


class GhError(Exception):
    pass


if __name__ == "__main__":
    main()
