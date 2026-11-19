#!/usr/bin/env python3
"""excavate: dig into a git history and report what the commits confess.

Reads git log and reports the cursed files (touched by reverts), the
hotspots (changed most often), the file pairs that always change
together, and an ownership map by top level folder. Zero dependencies.
Requires git on PATH. Python 3.8+.
"""

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from itertools import combinations

SEP = "\x1f"
PAIR_FILE_LIMIT = 40


def git_log(root, since=None):
    cmd = ["git", "-C", root, "log", f"--format=COMMIT{SEP}%an{SEP}%s", "--name-only"]
    if since:
        cmd.append(f"--since={since}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git log failed")
    commits = []
    current = None
    for line in proc.stdout.splitlines():
        if line.startswith("COMMIT" + SEP):
            _, author, subject = line.split(SEP, 2)
            current = {"author": author, "subject": subject, "files": []}
            commits.append(current)
        elif line.strip() and current is not None:
            current["files"].append(line.strip())
    return commits


def analyze(commits):
    changes = Counter()
    reverts = Counter()
    pairs = Counter()
    authors = Counter()
    dir_authors = defaultdict(Counter)
    for commit in commits:
        files = sorted(set(commit["files"]))
        authors[commit["author"]] += 1
        is_revert = "revert" in commit["subject"].lower()
        for path in files:
            changes[path] += 1
            if is_revert:
                reverts[path] += 1
            top = path.split("/")[0] if "/" in path else "(root)"
            dir_authors[top][commit["author"]] += 1
        if 1 < len(files) <= PAIR_FILE_LIMIT:
            for pair in combinations(files, 2):
                pairs[pair] += 1
    ownership = {}
    for folder, counter in sorted(dir_authors.items()):
        total = sum(counter.values())
        owner, count = counter.most_common(1)[0]
        ownership[folder] = {
            "owner": owner, "commits": count, "total": total,
            "share": round(100 * count / total) if total else 0,
        }
    return {
        "commits": len(commits),
        "authors": dict(authors.most_common()),
        "files_changed": len(changes),
        "hotspots": changes.most_common(),
        "cursed": reverts.most_common(),
        "cochange": [(list(pair), n) for pair, n in pairs.most_common()],
        "ownership": ownership,
    }


def render(report, top):
    lines = []
    lines.append(f"Commits: {report['commits']}   Authors: {len(report['authors'])}   Files ever changed: {report['files_changed']}")
    lines.append("")
    lines.append("CURSED FILES (touched by revert commits)")
    if report["cursed"]:
        for path, n in report["cursed"][:top]:
            lines.append(f"  {n:>4} reverts   {path}")
    else:
        lines.append("  none found. A peaceful history.")
    lines.append("")
    lines.append("HOTSPOTS (most changed files)")
    for path, n in report["hotspots"][:top]:
        lines.append(f"  {n:>4} changes   {path}")
    lines.append("")
    lines.append("ALWAYS TOGETHER (file pairs changed in the same commit)")
    shown = [(p, n) for p, n in report["cochange"] if n >= 2][:top]
    if shown:
        for (a, b), n in shown:
            lines.append(f"  {n:>4} times   {a}  +  {b}")
    else:
        lines.append("  no pair changed together more than once.")
    lines.append("")
    lines.append("OWNERSHIP MAP (dominant author per top level folder)")
    for folder, info in report["ownership"].items():
        lines.append(f"  {folder:<24} {info['owner']}  ({info['share']}% of {info['total']} commits)")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="excavate",
        description="Dig into a git history and report what the commits confess.",
    )
    parser.add_argument("--root", default=".", help="repository to dig (default: current directory)")
    parser.add_argument("--top", type=int, default=10, help="rows per section (default: 10)")
    parser.add_argument("--since", default=None, help="only commits after this date, as git understands it")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    try:
        commits = git_log(args.root, args.since)
    except RuntimeError as exc:
        print(f"excavate: {exc}", file=sys.stderr)
        return 2
    if not commits:
        print("excavate: no commits found.", file=sys.stderr)
        return 2
    report = analyze(commits)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
