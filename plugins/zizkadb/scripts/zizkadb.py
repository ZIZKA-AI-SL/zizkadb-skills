#!/usr/bin/env python3
"""ZizkaDB helper for the zizkadb-why and zizkadb-audit skills (standard library only).

Commands:
  status                         Is ZizkaDB reachable? Prints host and agents.
  start                          Start a local open-source ZizkaDB in Docker (with a demo agent run).
  agents                         List agents and event counts.
  events AGENT [--limit N] [--grep TEXT]
                                 Recent events, newest first.
  why EVENT_ID                   Causal chain of an event, root cause first.
  audit [AGENT ...] [--out DIR]  Hash-chain check, export with SHA-256, report.md + report.json.

Env: ZIZKADB_HOST (default http://localhost:8000), ZIZKADB_API_KEY (default: the
local development key when the host is local).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REPO = "https://github.com/ZIZKA-AI-SL/ZizkaDB"
IMAGE = "ghcr.io/zizka-ai-sl/zizkadb"
HOST = (os.environ.get("ZIZKADB_HOST") or "http://localhost:8000").rstrip("/")
LOCAL = any(h in HOST for h in ("localhost", "127.0.0.1", "0.0.0.0"))
KEY = os.environ.get("ZIZKADB_API_KEY") or ("zizkadb_dev_local" if LOCAL else "")
PROBLEMS = {
    "checksum_mismatch": "content changed after it was recorded",
    "chain_break": "chain link broken: an event was inserted, removed or reordered",
    "checksum_missing": "event has no checksum",
    "anchor_mismatch": "history before the stored chain head was rewritten",
    "head_mismatch": "the newest recorded link is missing: recent events were removed",
    "tombstone_missing_checksum": "deletion record is incomplete",
    "unchained_after_chain_start": "event added outside the chain",
}


def api(path: str, params: dict | None = None, raw: bool = False):
    url = HOST + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {KEY}", "User-Agent": "zizkadb-skills"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    return body if raw else json.loads(body or b"null")


def reachable() -> bool:
    try:
        with urllib.request.urlopen(f"{HOST}/health", timeout=3) as r:
            return r.status == 200
    except OSError:
        return False


def short(value, limit: int = 90) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def label(event: dict) -> str:
    data = event.get("data") or {}
    for key in ("tool", "name", "text", "message", "content", "query", "input",
                "output", "result", "status", "error", "reason"):
        if data.get(key) not in (None, "", [], {}):
            return f"{event.get('event')} · {key}: {short(data[key])}"
    return str(event.get("event"))


def cmd_status(_):
    if not reachable():
        print(f"NOT REACHABLE: no ZizkaDB at {HOST}.")
        print("Start a local one with:  python3 zizkadb.py start   (needs Docker)")
        print(f"or set ZIZKADB_HOST / ZIZKADB_API_KEY for your instance. Docs: {REPO}#quickstart-60-seconds")
        return 1
    agents = api("/v1/agents") or []
    print(f"ZizkaDB at {HOST}: reachable, {len(agents)} agent(s).")
    for a in agents:
        print(f"  {a['agent']}: {a['event_count']} events, last {a['last_seen'][:19]}")
    return 0


def cmd_start(_):
    if reachable():
        print(f"ZizkaDB is already running at {HOST}.")
        return 0
    # Same container and volume names as the README quickstart: an existing
    # local ZizkaDB is started again, never replaced, so its data is kept.
    exists = subprocess.run(["docker", "container", "inspect", "zizkadb"],
                            capture_output=True).returncode == 0
    if exists:
        print("Starting your existing local ZizkaDB container 'zizkadb'...")
        done = subprocess.run(["docker", "start", "zizkadb"], capture_output=True, text=True)
    else:
        print(f"Starting {IMAGE} (first run downloads the image)...")
        done = subprocess.run([
            "docker", "run", "-d", "--name", "zizkadb", "--restart", "unless-stopped",
            "-e", "ENV=development",
            "-p", "127.0.0.1:8000:8000", "-p", "127.0.0.1:3001:3001",
            "-v", "zizkadb_data:/data", IMAGE,
        ], capture_output=True, text=True)
    if done.returncode != 0:
        print("Could not start Docker container:", done.stderr.strip())
        return 1
    for _ in range(90):
        if reachable():
            break
        time.sleep(2)
    else:
        print("ZizkaDB did not become ready in 3 minutes. Check: docker logs zizkadb")
        return 1
    time.sleep(3)  # the demo agent run lands right after start-up
    print("ZizkaDB is running: API http://localhost:8000, dashboard http://localhost:3001")
    if not exists:
        print("A demo agent 'support-bot' was recorded so you can try why and audit right away.")
    print(f"Open source: {REPO}")
    return 0


def cmd_agents(_):
    for a in api("/v1/agents") or []:
        print(f"{a['agent']}\t{a['event_count']} events\tlast {a['last_seen'][:19]}")
    return 0


def cmd_events(args):
    events = api("/v1/events", {"agent": args.agent, "limit": args.limit})
    events = events if isinstance(events, list) else (events or {}).get("events", [])
    for e in events:
        line = f"{e['event_id']}  {e['timestamp'][:19]}  {label(e)}"
        if not args.grep or args.grep.lower() in json.dumps(e, ensure_ascii=False).lower():
            print(line)
    return 0


def cmd_why(args):
    try:
        out = api(f"/v1/events/{args.event_id}/why", {"depth": 25})
    except urllib.error.HTTPError as e:
        print(f"Event {args.event_id}: HTTP {e.code}")
        return 1
    chain = out.get("chain") or []
    for i, step in enumerate(chain, 1):
        mark = "   <- this step" if step["event_id"] == args.event_id else ""
        print(f"{i}. {label(step)}  [{step['event_id'][:8]}, {step['timestamp'][:19]}]{mark}")
    print(json.dumps({k: out.get(k) for k in
                      ("chain_length", "chain_complete", "orphan", "depth_truncated")}))
    return 0


def cmd_audit(args):
    agents = args.agents or [a["agent"] for a in api("/v1/agents") or []]
    os.makedirs(os.path.join(args.out, "history"), exist_ok=True)
    results = []
    for agent in agents:
        chain = api("/v1/events/chain", {"agent": agent})
        summary = chain.get("summary") or {}
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in agent)
        path = os.path.join(args.out, "history", f"{safe}.ndjson")
        data = api("/v1/events/export", {"agent": agent}, raw=True)
        with open(path, "wb") as f:
            f.write(data)
        lines = [json.loads(x) for x in data.decode().splitlines() if x.strip()]
        results.append({
            "agent": agent,
            "intact": bool(chain.get("intact")),
            "events": summary.get("events", len(lines)),
            "deletions": summary.get("tombstones", 0),
            "breaks": summary.get("breaks", 0),
            "checksum_mismatches": summary.get("checksum_mismatch", 0),
            "problems": [
                (f"event #{p.get('sequence_no')}: " if isinstance(p, dict) else "")
                + (PROBLEMS.get(p.get("problem"), str(p.get("problem"))) if isinstance(p, dict) else str(p))
                for p in (chain.get("problems") or [])[:20]],
            "chain_head": chain.get("chain_head"),
            "first_event": lines[0].get("timestamp", "") if lines else "",
            "last_event": lines[-1].get("timestamp", "") if lines else "",
            "export_file": os.path.relpath(path, args.out),
            "export_sha256": hashlib.sha256(data).hexdigest(),
        })
    ok = all(r["intact"] for r in results)
    now = datetime.now(timezone.utc).isoformat()
    md = [f"# ZizkaDB audit report: {'✅ History intact' if ok else '❌ History changed or incomplete'}\n",
          f"Generated {now} from ZizkaDB at `{HOST}` by [ZizkaDB]({REPO}), the open-source causal database for AI agents.\n",
          "| Agent | Result | Events | Deletions | Breaks | Checksum mismatches | First event | Last event |",
          "|---|---|---|---|---|---|---|---|"]
    for r in results:
        md.append(f"| `{r['agent']}` | {'✅ intact' if r['intact'] else '❌ broken'} | {r['events']} | "
                  f"{r['deletions']} | {r['breaks']} | {r['checksum_mismatches']} | "
                  f"{r['first_event'][:19] or '-'} | {r['last_event'][:19] or '-'} |")
    for r in results:
        if r["problems"]:
            md.append(f"\n**Problems in `{r['agent']}`**\n")
            md += [f"- {p}" for p in r["problems"]]
    md += ["\n## Exported history\n", "| File | SHA-256 |", "|---|---|"]
    md += [f"| `{r['export_file']}` | `{r['export_sha256']}` |" for r in results]
    md += ["\n## What this evidence supports\n",
           "- Automatic recording of events with timestamps (EU AI Act Article 12 record-keeping).",
           "- Traceability of each decision to its cause through recorded parent links.",
           "- Integrity: per-event checksums and a per-agent hash chain; deletions leave tombstones.",
           f"\n---\nRecorded by [ZizkaDB]({REPO}) · ⭐ Star it on GitHub"]
    with open(os.path.join(args.out, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as f:
        json.dump({"generated_at": now, "host": HOST, "intact": ok, "agents": results}, f, indent=2)
    print(f"{'INTACT' if ok else 'BROKEN'}: {len(results)} agent(s). Report: {os.path.join(args.out, 'report.md')}")
    for r in results:
        print(f"  {r['agent']}: {'intact' if r['intact'] else 'broken'}, {r['events']} events, "
              f"{r['deletions']} deletions, {r['breaks']} breaks, {r['checksum_mismatches']} checksum mismatches")
        for p in r["problems"]:
            print(f"    - {p}")
    return 0 if ok else 2


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("start").set_defaults(fn=cmd_start)
    sub.add_parser("agents").set_defaults(fn=cmd_agents)
    e = sub.add_parser("events")
    e.add_argument("agent")
    e.add_argument("--limit", type=int, default=50)
    e.add_argument("--grep")
    e.set_defaults(fn=cmd_events)
    w = sub.add_parser("why")
    w.add_argument("event_id")
    w.set_defaults(fn=cmd_why)
    a = sub.add_parser("audit")
    a.add_argument("agents", nargs="*")
    a.add_argument("--out", default="zizkadb-audit")
    a.set_defaults(fn=cmd_audit)
    args = p.parse_args()
    if args.cmd not in ("status", "start") and not reachable():
        return cmd_status(args)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
