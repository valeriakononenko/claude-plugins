#!/usr/bin/env python3
"""Jira Cloud REST v3 helper for the jira:report skill: post, update and list issue comments written as ADF.

The comment body is Markdown-lite (same dialect as the jira:ticket description) plus panel directives:

    ::: panel warning
    **Verdict:** the import job is dropping rows.
    :::

A body file that already contains an ADF document (JSON with "type": "doc") is posted unchanged.

Credentials come from JIRA_ORG, JIRA_EMAIL and JIRA_TOKEN (environment first, then ./.env, then ~/.jira.env);
the Markdown-lite conversion, the HTTP client and the credential loading are reused from the jira:ticket script.
Every command prints JSON to stdout so the calling agent can read it back.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ticket" / "scripts"))
try:
    from jira_issue import Jira, JiraError, credentials, emit, text_to_adf
except ImportError:
    sys.exit(
        "Cannot import jira_issue.py from the ticket skill. Both skills ship in the jira plugin; "
        "expected it at <plugin>/skills/ticket/scripts/jira_issue.py."
    )

PANEL_TYPES = ("info", "note", "success", "warning", "error")
PANEL_OPEN_RE = re.compile(rf"^:::\s*(?:panel\s+)?({'|'.join(PANEL_TYPES)})\s*$", re.IGNORECASE)
PANEL_CLOSE_RE = re.compile(r"^:::\s*$")
PREVIEW_LIMIT = 120


def read_body(path):
    return sys.stdin.read() if path == "-" else Path(path).read_text()


def as_adf_document(raw):
    """Return the ADF document for a body: parsed as-is when it is already ADF, converted otherwise."""
    stripped = raw.strip()
    if stripped.startswith("{"):
        try:
            parsed = json.loads(stripped)
        except ValueError:
            parsed = None
        if isinstance(parsed, dict) and parsed.get("type") == "doc":
            parsed.setdefault("version", 1)
            return parsed
    return body_to_adf(raw)


def panel_node(panel_type, lines):
    content = text_to_adf("\n".join(lines))["content"]
    return {
        "type": "panel",
        "attrs": {"panelType": panel_type.lower()},
        "content": content or [{"type": "paragraph", "content": [{"type": "text", "text": " "}]}],
    }


def body_to_adf(text):
    """Convert a Markdown-lite body with ::: panel <type> directives into an ADF document node."""
    blocks = []
    plain = []
    panel_type = None
    panel_lines = []

    def flush_plain():
        if any(line.strip() for line in plain):
            blocks.extend(text_to_adf("\n".join(plain))["content"])
        plain.clear()

    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if panel_type is None:
            opening = PANEL_OPEN_RE.match(stripped)
            if opening:
                flush_plain()
                panel_type = opening.group(1)
                continue
            plain.append(line)
            continue
        if PANEL_CLOSE_RE.match(stripped):
            blocks.append(panel_node(panel_type, panel_lines))
            panel_type, panel_lines = None, []
            continue
        panel_lines.append(line)
    if panel_type is not None:
        blocks.append(panel_node(panel_type, panel_lines))
    flush_plain()
    return {"type": "doc", "version": 1, "content": blocks}


def comment_url(jira, key, comment_id):
    return f"{jira.browse_url(key)}?focusedCommentId={comment_id}"


def plain_text(node):
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        return " ".join(plain_text(child) for child in node.get("content", []))
    return ""


def cmd_adf(_jira, args):
    emit(as_adf_document(read_body(args.body)))


def cmd_post(jira, args):
    document = as_adf_document(read_body(args.body))
    payload = {"body": document}
    if args.internal:
        payload["properties"] = [{"key": "sd.public.comment", "value": {"internal": True}}]
    if args.dry_run:
        emit({"issue": args.key, "commentId": args.comment_id, "payload": payload})
        return
    if args.comment_id:
        posted = jira.request("PUT", f"issue/{args.key}/comment/{args.comment_id}", body=payload)
        action = "updated"
    else:
        posted = jira.request("POST", f"issue/{args.key}/comment", body=payload)
        action = "created"
    emit({
        "issue": args.key,
        "commentId": posted["id"],
        "action": action,
        "url": comment_url(jira, args.key, posted["id"]),
    })


def cmd_comments(jira, args):
    page = jira.request(
        "GET",
        f"issue/{args.key}/comment",
        {"maxResults": args.limit, "orderBy": "-created"},
    )
    rows = []
    for comment in page.get("comments", []):
        preview = " ".join(plain_text(comment.get("body")).split())
        rows.append({
            "id": comment["id"],
            "author": (comment.get("author") or {}).get("displayName"),
            "created": comment.get("created"),
            "updated": comment.get("updated"),
            "preview": preview[:PREVIEW_LIMIT] + ("…" if len(preview) > PREVIEW_LIMIT else ""),
            "url": comment_url(jira, args.key, comment["id"]),
        })
    emit(rows)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("adf", help="Print the ADF document built from a body file (offline)")
    p.add_argument("body", help="Path to the body file, or - for stdin")
    p.set_defaults(fn=cmd_adf, offline=True)

    p = sub.add_parser("post", help="Post a comment on an issue, or update one with --comment-id")
    p.add_argument("key", help="Issue key, e.g. SHOP-812")
    p.add_argument("body", help="Path to the body file, or - for stdin")
    p.add_argument("--comment-id", help="Update this comment in place instead of adding a new one")
    p.add_argument("--internal", action="store_true", help="Service desk only: post as an internal comment")
    p.add_argument("--dry-run", action="store_true", help="Print the REST payload instead of posting")
    p.set_defaults(fn=cmd_post)

    p = sub.add_parser("comments", help="List the newest comments on an issue with their ids")
    p.add_argument("key")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(fn=cmd_comments)
    return parser


def main():
    args = build_parser().parse_args()
    offline = getattr(args, "offline", False) or (args.command == "post" and args.dry_run)
    jira = None
    if not offline:
        env = credentials()
        jira = Jira(env["JIRA_ORG"], env["JIRA_EMAIL"], env["JIRA_TOKEN"], env["JIRA_PROJECT_KEY"])
    try:
        args.fn(jira, args)
    except JiraError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
