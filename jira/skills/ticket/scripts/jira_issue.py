#!/usr/bin/env python3
"""Jira Cloud REST v3 helper for the jira:ticket skill: lookups, ADF conversion, issue creation and linking.

Credentials come from JIRA_SITE, JIRA_EMAIL and JIRA_TOKEN (environment first, then ./.env, then ~/.jira.env).
JIRA_SITE is the Atlassian site URL; JIRA_PROJECT_KEY is the default project offered to the user.
Every command prints JSON to stdout so the calling agent can read it back.
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REQUIRED_KEYS = ("JIRA_SITE", "JIRA_EMAIL", "JIRA_TOKEN")
OPTIONAL_KEYS = ("JIRA_PROJECT_KEY",)
DOTENV_CANDIDATES = (".env", os.path.expanduser("~/.jira.env"))
ACCOUNT_ID_RE = re.compile(r"^[0-9a-f]{24}$|^[0-9]+:[0-9a-f-]{36}$")


class JiraError(Exception):
    def __init__(self, status, body, method, path):
        self.status = status
        self.method = method
        self.path = path
        try:
            parsed = json.loads(body)
            messages = parsed.get("errorMessages", []) + [f"{k}: {v}" for k, v in parsed.get("errors", {}).items()]
            detail = "; ".join(messages) or body
        except (ValueError, AttributeError):
            detail = body
        super().__init__(f"Jira {method} {path} failed with HTTP {status}: {detail}")


def load_dotenv(path):
    values = {}
    try:
        text = Path(path).read_text()
    except OSError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def credentials():
    keys = REQUIRED_KEYS + OPTIONAL_KEYS
    env = {k: os.environ.get(k, "") for k in keys}
    for candidate in DOTENV_CANDIDATES:
        if all(env[k] for k in REQUIRED_KEYS):
            break
        for key, value in load_dotenv(candidate).items():
            if key in env and not env[key]:
                env[key] = value
    missing = [k for k in REQUIRED_KEYS if not env[k]]
    if missing:
        sys.exit(
            f"Missing {', '.join(missing)}. Export them or put them in ./.env or ~/.jira.env "
            f"(JIRA_SITE like https://<org>.atlassian.net, JIRA_TOKEN = Atlassian API token; "
            f"optional JIRA_PROJECT_KEY)."
        )
    return env


class Jira:
    def __init__(self, site, email, token, default_project=""):
        self.site = site.rstrip("/")
        self.default_project = default_project or None
        self.auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    def request(self, method, path, params=None, body=None):
        url = f"{self.site}/rest/api/3/{path}"
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Basic {self.auth}", "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as res:
                raw = res.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            raise JiraError(e.code, e.read().decode(errors="replace"), method, path) from None

    def browse_url(self, key):
        return f"{self.site}/browse/{key}"


INLINE_RE = re.compile(
    r"(`[^`]+`)"
    r"|(\*\*[^*]+\*\*)"
    r"|\[([^\]]+)\]\((https?://[^)\s]+)\)"
    r"|(https?://[^\s<>()\"']+)"
)


def text_node(text, marks=None):
    node = {"type": "text", "text": text}
    if marks:
        node["marks"] = marks
    return node


def inline_nodes(text):
    nodes = []
    pos = 0
    for m in INLINE_RE.finditer(text):
        if m.start() > pos:
            nodes.append(text_node(text[pos:m.start()]))
        code, strong, label, href, url = m.groups()
        if code:
            nodes.append(text_node(code[1:-1], [{"type": "code"}]))
        elif strong:
            nodes.append(text_node(strong[2:-2], [{"type": "strong"}]))
        elif label:
            nodes.append(text_node(label, [{"type": "link", "attrs": {"href": href}}]))
        elif url:
            nodes.append(text_node(url, [{"type": "link", "attrs": {"href": url}}]))
        pos = m.end()
    if pos < len(text):
        nodes.append(text_node(text[pos:]))
    return nodes or [text_node(" ")]


def paragraph(lines):
    content = []
    for i, line in enumerate(lines):
        content.extend(inline_nodes(line))
        if i < len(lines) - 1:
            content.append({"type": "hardBreak"})
    return {"type": "paragraph", "content": content}


BULLET_RE = re.compile(r"^[-*]\s+(.*)")
ORDERED_RE = re.compile(r"^\d+[.)]\s+(.*)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")
RULE_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")


def starts_block(stripped):
    return (
        not stripped
        or stripped.startswith("```")
        or stripped.startswith(">")
        or bool(RULE_RE.match(stripped) or HEADING_RE.match(stripped) or BULLET_RE.match(stripped) or ORDERED_RE.match(stripped))
    )


def collect_list(lines, i, item_re):
    items = []
    while i < len(lines):
        m = item_re.match(lines[i].strip())
        if not m:
            break
        item_lines = [m.group(1)]
        i += 1
        while i < len(lines) and lines[i].startswith((" ", "\t")) and lines[i].strip():
            item_lines.append(lines[i].strip())
            i += 1
        items.append({"type": "listItem", "content": [paragraph(item_lines)]})
    return items, i


def text_to_adf(text):
    """Convert a markdown-lite description into an ADF document node (type doc, version 1)."""
    lines = text.replace("\r\n", "\n").split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("```"):
            language = stripped[3:].strip()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            node = {"type": "codeBlock"}
            if language:
                node["attrs"] = {"language": language}
            if code:
                node["content"] = [text_node("\n".join(code))]
            blocks.append(node)
            continue
        if RULE_RE.match(stripped):
            blocks.append({"type": "rule"})
            i += 1
            continue
        heading = HEADING_RE.match(stripped)
        if heading:
            blocks.append({"type": "heading", "attrs": {"level": len(heading.group(1))}, "content": inline_nodes(heading.group(2))})
            i += 1
            continue
        if BULLET_RE.match(stripped):
            items, i = collect_list(lines, i, BULLET_RE)
            blocks.append({"type": "bulletList", "content": items})
            continue
        if ORDERED_RE.match(stripped):
            items, i = collect_list(lines, i, ORDERED_RE)
            blocks.append({"type": "orderedList", "content": items})
            continue
        if stripped.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            inner = text_to_adf("\n".join(quote))["content"]
            blocks.append({"type": "blockquote", "content": inner or [paragraph([" "])]})
            continue
        para = []
        while i < len(lines) and not starts_block(lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        blocks.append(paragraph(para))
    return {"type": "doc", "version": 1, "content": blocks}


def emit(data):
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def read_spec(path):
    raw = sys.stdin.read() if path == "-" else Path(path).read_text()
    return json.loads(raw)


def cmd_whoami(jira, _args):
    me = jira.request("GET", "myself")
    emit({
        "accountId": me["accountId"],
        "displayName": me["displayName"],
        "email": me.get("emailAddress"),
        "site": jira.site,
        "defaultProject": jira.default_project,
    })


def cmd_projects(jira, args):
    page = jira.request("GET", "project/search", {"query": args.query, "maxResults": 50, "orderBy": "name"})
    emit([{"key": p["key"], "name": p["name"], "type": p.get("projectTypeKey")} for p in page.get("values", [])])


def cmd_issue_types(jira, args):
    project = jira.request("GET", f"project/{args.project}")
    types = [
        {"name": t["name"], "description": t.get("description", ""), "hierarchyLevel": t.get("hierarchyLevel")}
        for t in project.get("issueTypes", [])
        if not t.get("subtask")
    ]
    emit(types)


def cmd_users(jira, args):
    users = jira.request("GET", "user/assignable/search", {"project": args.project, "query": args.query, "maxResults": 50})
    emit([
        {"accountId": u["accountId"], "displayName": u["displayName"], "email": u.get("emailAddress"), "active": u.get("active")}
        for u in users
        if u.get("accountType", "atlassian") == "atlassian"
    ])


def search(jira, jql, limit, fields):
    page = jira.request("GET", "search/jql", {"jql": jql, "fields": ",".join(fields), "maxResults": limit})
    return page.get("issues", [])


def issue_row(issue):
    f = issue["fields"]
    row = {
        "key": issue["key"],
        "summary": f.get("summary"),
        "status": (f.get("status") or {}).get("name"),
        "type": (f.get("issuetype") or {}).get("name"),
    }
    if "assignee" in f:
        row["assignee"] = (f.get("assignee") or {}).get("displayName")
    if f.get("parent"):
        row["parent"] = {"key": f["parent"]["key"], "summary": f["parent"]["fields"]["summary"]}
    if "labels" in f:
        row["labels"] = f.get("labels") or []
    return row


def cmd_epics(jira, args):
    jql = f'project = "{args.project}" AND issuetype = Epic AND statusCategory != Done'
    if args.query:
        jql += f' AND text ~ "{args.query}"'
    jql += " ORDER BY updated DESC"
    emit([issue_row(i) for i in search(jira, jql, args.limit, ["summary", "status", "issuetype"])])


def cmd_search(jira, args):
    fields = ["summary", "status", "issuetype", "assignee", "parent", "labels"]
    emit([issue_row(i) for i in search(jira, args.jql, args.limit, fields)])


def cmd_issue(jira, args):
    issue = jira.request("GET", f"issue/{args.key}", {"fields": "summary,status,issuetype,assignee,parent,labels,issuelinks"})
    row = issue_row(issue)
    links = []
    for link in issue["fields"].get("issuelinks", []):
        if "outwardIssue" in link:
            links.append({"relation": link["type"]["outward"], "issue": link["outwardIssue"]["key"]})
        if "inwardIssue" in link:
            links.append({"relation": link["type"]["inward"], "issue": link["inwardIssue"]["key"]})
    row["links"] = links
    row["url"] = jira.browse_url(issue["key"])
    emit(row)


def cmd_link_types(jira, _args):
    types = jira.request("GET", "issueLinkType")["issueLinkTypes"]
    emit([{"name": t["name"], "outward": t["outward"], "inward": t["inward"]} for t in types])


def cmd_labels(jira, args):
    labels = []
    start = 0
    while True:
        page = jira.request("GET", "label", {"startAt": start, "maxResults": 1000})
        labels.extend(page.get("values", []))
        if page.get("isLast", True) or not page.get("values"):
            break
        start += len(page["values"])
    if args.query:
        q = args.query.lower()
        labels = [l for l in labels if q in l.lower()]
    emit(labels)


def cmd_adf(_jira, args):
    spec = read_spec(args.spec)
    emit(text_to_adf(spec["description"] if isinstance(spec, dict) else spec))


def resolve_assignee(jira, project, value):
    if ACCOUNT_ID_RE.match(value):
        return value
    users = jira.request("GET", "user/assignable/search", {"project": project, "query": value, "maxResults": 20})
    exact = [u for u in users if value.lower() in (u["displayName"].lower(), (u.get("emailAddress") or "").lower())]
    candidates = exact or users
    if len(candidates) != 1:
        names = ", ".join(f'{u["displayName"]} ({u["accountId"]})' for u in candidates) or "none"
        sys.exit(f"Assignee {value!r} is ambiguous or unknown in project {project}. Candidates: {names}")
    return candidates[0]["accountId"]


def resolve_link(link_types, relation):
    rel = relation.strip().lower()
    for t in link_types:
        if rel in (t["name"].lower(), t["outward"].lower()):
            return t["name"], "outward"
        if rel == t["inward"].lower():
            return t["name"], "inward"
    known = "; ".join(f'{t["name"]}: "{t["outward"]}" / "{t["inward"]}"' for t in link_types)
    sys.exit(f"Unknown link relation {relation!r}. Known: {known}")


def link_body(type_name, direction, new_key, other_key):
    outward, inward = (new_key, other_key) if direction == "outward" else (other_key, new_key)
    return {"type": {"name": type_name}, "outwardIssue": {"key": outward}, "inwardIssue": {"key": inward}}


def validate_spec(spec):
    required = ["project", "type", "summary", "description", "assignee"]
    missing = [k for k in required if not spec.get(k)]
    if missing:
        sys.exit(f"Spec is missing required fields: {', '.join(missing)}. An issue is never created without an assignee.")
    bad_labels = [l for l in spec.get("labels", []) if re.search(r"\s", l)]
    if bad_labels:
        sys.exit(f"Jira labels cannot contain whitespace: {bad_labels}. Use hyphens instead.")
    for link in spec.get("links", []):
        if not link.get("issue") or not link.get("relation"):
            sys.exit(f"Each link needs 'issue' and 'relation': {link}")


def cmd_create(jira, args):
    spec = read_spec(args.spec)
    validate_spec(spec)
    fields = {
        "project": {"key": spec["project"]},
        "issuetype": {"name": spec["type"]},
        "summary": spec["summary"].strip(),
        "description": text_to_adf(spec["description"]),
    }
    if spec.get("labels"):
        fields["labels"] = spec["labels"]
    if spec.get("epic"):
        fields["parent"] = {"key": spec["epic"]}
    if args.dry_run:
        fields["assignee"] = {"id": spec["assignee"]}
        emit({"fields": fields, "links": spec.get("links", [])})
        return
    links = []
    if spec.get("links"):
        link_types = jira.request("GET", "issueLinkType")["issueLinkTypes"]
        links = [(*resolve_link(link_types, l["relation"]), l["issue"]) for l in spec["links"]]
    fields["assignee"] = {"id": resolve_assignee(jira, spec["project"], spec["assignee"])}
    created = jira.request("POST", "issue", body={"fields": fields})
    key = created["key"]
    link_results = []
    for type_name, direction, other_key in links:
        try:
            jira.request("POST", "issueLink", body=link_body(type_name, direction, key, other_key))
            link_results.append({"issue": other_key, "type": type_name, "direction": direction, "ok": True})
        except JiraError as e:
            link_results.append({"issue": other_key, "type": type_name, "direction": direction, "ok": False, "error": str(e)})
    emit({"key": key, "url": jira.browse_url(key), "links": link_results})


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("whoami", help="Verify credentials and show the current user").set_defaults(fn=cmd_whoami)

    p = sub.add_parser("projects", help="List projects, optionally filtered by name/key")
    p.add_argument("query", nargs="?")
    p.set_defaults(fn=cmd_projects)

    p = sub.add_parser("issue-types", help="List non-subtask issue types available in a project")
    p.add_argument("project")
    p.set_defaults(fn=cmd_issue_types)

    p = sub.add_parser("users", help="List users assignable in a project, optionally filtered by name/email")
    p.add_argument("project")
    p.add_argument("query", nargs="?")
    p.set_defaults(fn=cmd_users)

    p = sub.add_parser("epics", help="List open epics in a project, optionally filtered by text")
    p.add_argument("project")
    p.add_argument("query", nargs="?")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(fn=cmd_epics)

    p = sub.add_parser("search", help="Run a JQL query")
    p.add_argument("jql")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("issue", help="Show one issue with its parent and links")
    p.add_argument("key")
    p.set_defaults(fn=cmd_issue)

    sub.add_parser("link-types", help="List issue link types with outward/inward wording").set_defaults(fn=cmd_link_types)

    p = sub.add_parser("labels", help="List existing labels, optionally filtered by substring")
    p.add_argument("query", nargs="?")
    p.set_defaults(fn=cmd_labels)

    p = sub.add_parser("adf", help="Print the ADF document built from a spec's description (or a raw JSON string)")
    p.add_argument("spec", help="Path to the spec JSON, or - for stdin")
    p.set_defaults(fn=cmd_adf, offline=True)

    p = sub.add_parser("create", help="Create the issue described by a spec JSON, then add its links")
    p.add_argument("spec", help="Path to the spec JSON, or - for stdin")
    p.add_argument("--dry-run", action="store_true", help="Print the REST payload instead of creating")
    p.set_defaults(fn=cmd_create)
    return parser


def main():
    args = build_parser().parse_args()
    offline = getattr(args, "offline", False) or (args.command == "create" and args.dry_run)
    jira = None
    if not offline:
        env = credentials()
        jira = Jira(env["JIRA_SITE"], env["JIRA_EMAIL"], env["JIRA_TOKEN"], env["JIRA_PROJECT_KEY"])
    try:
        args.fn(jira, args)
    except JiraError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
