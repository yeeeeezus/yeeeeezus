#!/usr/bin/env python3
"""Regenerate the 'tail -f bounty-log' section of the profile README from the
CI-verified ledger at yeeeeezus/bounty-log.

Runs inside GitHub Actions on the profile repo (yeeeeezus/yeeeeezus).
Rewrites the block between <!--HUNT:START--> and <!--HUNT:END--> markers.
Exits 0 always; leaves README untouched if nothing changed.
"""
import json
import re
import sys
import urllib.request

LEDGER_URL = "https://raw.githubusercontent.com/yeeeeezus/bounty-log/main/ledger.json"
README_PATH = "README.md"

STATUS_BADGE = {
    "submitted": "🟢 open",
    "in_review": "🟡 in review",
    "merged": "🟣 merged",
    "paid": "✅ paid",
    "released": "⚪ released",
    "withdrawn": "⚪ withdrawn",
}


def fetch_ledger():
    with urllib.request.urlopen(LEDGER_URL, timeout=30) as resp:
        return json.load(resp)


def render(ledger_doc):
    entries = ledger_doc.get("ledger", [])
    active = [
        e for e in entries
        if e.get("status") not in ("released", "withdrawn")
    ]
    active.sort(key=lambda e: e.get("date", ""), reverse=True)

    lines = []
    if active:
        lines.append("| repo | issue | PR | status | est |")
        lines.append("|------|-------|----|--------|-----|")
        for e in active[:6]:
            est = e.get("bounty_est_usd")
            est_s = f"~${est}" if isinstance(est, (int, float)) and est > 0 else "—"
            repo = e.get("repo", "?")
            repo_s = f"[{repo}](https://github.com/{repo})"
            issue_s = f"[#{e.get('issue', '?')}]({e.get('issue_url', '#')})"
            if e.get("pr"):
                pr_s = f"[#{e['pr']}]({e.get('pr_url', '#')})"
            else:
                pr_s = "—"
            badge = STATUS_BADGE.get(e.get("status", ""), e.get("status", "?"))
            lines.append(f"| {repo_s} | {issue_s} | {pr_s} | {badge} | {est_s} |")
    else:
        lines.append("*no active hunts — scanner warming up*")

    paid = sum(
        e.get("verified_revenue_usd", 0) or 0
        for e in entries if e.get("status") == "paid"
    )
    pipeline = sum(
        e.get("bounty_est_usd", 0) or 0
        for e in active if e.get("status") in ("submitted", "in_review")
    )
    lines.append("")
    lines.append(
        f"`{len(active)} active hunt(s) · ~${pipeline} est pipeline · ${paid:.0f} verified paid`"
    )
    return "\n".join(lines)


def main():
    try:
        doc = fetch_ledger()
    except Exception as exc:  # network hiccup: never break the README
        print(f"ledger fetch failed: {exc}", file=sys.stderr)
        return 0

    block = render(doc)

    with open(README_PATH, encoding="utf-8") as fh:
        readme = fh.read()

    pattern = re.compile(r"(<!--HUNT:START-->\n?)(.*?)(\n?<!--HUNT:END-->)", re.S)
    if not pattern.search(readme):
        print("HUNT markers missing in README; nothing to do", file=sys.stderr)
        return 0

    new_readme = pattern.sub(
        lambda m: m.group(1) + block + "\n<!--HUNT:END-->",
        readme, count=1
    )
    if new_readme == readme:
        print("no changes")
        return 0

    with open(README_PATH, "w", encoding="utf-8") as fh:
        fh.write(new_readme)
    print("hunt table updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
