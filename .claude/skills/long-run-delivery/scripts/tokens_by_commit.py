#!/usr/bin/env python3
"""Token usage of a Claude Code session, split by git commit (= by lot) or by hour.

Reads the session transcripts (~/.claude/projects/<slug>/*.jsonl), where every assistant
message carries its real `usage`. Stdlib only.

    python tokens_by_commit.py                 # project = current directory, buckets = its commits
    python tokens_by_commit.py --by hour       # no git repo, or finer view
    python tokens_by_commit.py --project C:/path/to/repo --since 2026-11-12

Columns: turns = API calls ; out = output tokens (what you pay most for) ; new = input written to
the cache (cache_creation + uncached input) ; read = input re-read from the cache (cheap, but it is
what grows with a long context). A lot whose `read/turn` climbs is a lot that needed a /compact.
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def slug(path: Path) -> str:
    # Claude Code names the transcript folder after the project path, every non-alphanumeric char -> "-"
    return "".join(c if c.isalnum() else "-" for c in str(path.resolve()))


def messages(folder: Path, since: datetime):
    seen = set()
    for fichier in sorted(folder.glob("*.jsonl")):
        with fichier.open(encoding="utf-8", errors="replace") as f:
            for ligne in f:
                try:
                    d = json.loads(ligne)
                except json.JSONDecodeError:
                    continue
                m = d.get("message") or {}
                u = m.get("usage")
                if d.get("type") != "assistant" or not u or m.get("id") in seen:
                    continue  # a streamed message is written several times: count it once
                seen.add(m.get("id"))
                t = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
                if t >= since:
                    yield t, m.get("model", "?"), u


def commits(repo: Path):
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "log", "--reverse", "--format=%cI\t%h %s"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    res = []
    for ligne in out.splitlines():
        quand, label = ligne.split("\t", 1)
        res.append((datetime.fromisoformat(quand).astimezone(timezone.utc), label))
    return res


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project", type=Path, default=Path.cwd())
    p.add_argument("--by", choices=["commit", "hour"], default="commit")
    p.add_argument("--since", default="1970-01-01", help="ISO date; ignore older messages")
    a = p.parse_args()

    folder = Path.home() / ".claude" / "projects" / slug(a.project)
    if not folder.is_dir():
        sys.exit(f"No transcripts for this project: {folder}")
    since = datetime.fromisoformat(a.since).replace(tzinfo=timezone.utc)
    marks = commits(a.project) if a.by == "commit" else []
    if a.by == "commit" and not marks:
        print("(no git history here: falling back to --by hour)\n")

    lignes = defaultdict(lambda: defaultdict(int))  # (order, label, model) -> counters
    for t, model, u in messages(folder, since):
        if marks:
            # the work done BEFORE a commit belongs to that commit
            i = next((k for k, (quand, _) in enumerate(marks) if t <= quand), len(marks))
            label = marks[i][1] if i < len(marks) else "(after the last commit)"
            cle = (i, label[:62], model)
        else:
            h = t.astimezone().strftime("%Y-%m-%d %Hh")
            cle = (h, h, model)
        c = lignes[cle]
        c["turns"] += 1
        c["out"] += u.get("output_tokens", 0)
        c["new"] += u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
        c["read"] += u.get("cache_read_input_tokens", 0)

    k = lambda n: f"{n / 1000:,.0f}k".replace(",", " ")
    print(f"{'bucket':<62} {'model':<18} {'turns':>5} {'out':>7} {'new':>8} {'read':>9} {'read/turn':>9}")
    total = defaultdict(int)
    for (_, label, model), c in sorted(lignes.items(), key=lambda x: (x[0][0], x[0][2])):
        print(f"{label:<62} {model.replace('claude-', ''):<18} {c['turns']:>5} {k(c['out']):>7} "
              f"{k(c['new']):>8} {k(c['read']):>9} {k(c['read'] / c['turns']):>9}")
        for cle, v in c.items():
            total[cle] += v
    if total["turns"]:
        print(f"{'TOTAL':<62} {'':<18} {total['turns']:>5} {k(total['out']):>7} {k(total['new']):>8} "
              f"{k(total['read']):>9} {k(total['read'] / total['turns']):>9}")


if __name__ == "__main__":
    main()
