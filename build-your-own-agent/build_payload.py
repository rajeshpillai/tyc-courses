#!/usr/bin/env python3
"""Convert MODULE-0X.md files into a JSON payload for Tutor LMS.

Splits each module file into topic (module) + lessons, converts lesson bodies
to WordPress-friendly HTML, and drops the "Production notes" section, which is
for the course author only and must never reach the site.
"""
import json
import re
import sys
from pathlib import Path

import markdown

HERE = Path(__file__).parent
MODULE_FILES = sorted(HERE.glob("MODULE-*.md"))

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "attr_list"]


def split_module(text):
    """Return (module_title, module_intro, [(lesson_title, lesson_md), ...])."""
    m = re.search(r"^#\s+(.+)$", text, re.M)
    module_heading = m.group(1).strip()

    first_lesson = re.search(r"^##\s+Lesson\s", text, re.M)
    intro_block = text[m.end():first_lesson.start()] if first_lesson else ""

    intro_lines = [l.strip() for l in intro_block.splitlines() if l.strip()]
    summary = ""
    for line in intro_lines:
        if line.startswith("---"):
            continue
        summary = line.strip("*_")
        break

    lessons = []
    pattern = re.compile(r"^##\s+Lesson\s+[\d.]+\s+[—-]\s+(.+?)\s*$", re.M)
    marks = list(pattern.finditer(text))
    for i, mk in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[mk.end():end]
        # Stop at the author-only production notes section if it follows
        body = re.split(r"^##\s+Production notes", body, flags=re.M)[0]
        body = re.sub(r"\n---\s*$", "\n", body.rstrip()) + "\n"
        title = mk.group(1).strip()
        title = re.sub(r"[`*_]", "", title)
        lessons.append((title, body))
    return module_heading, summary, lessons


def to_html(md_text):
    html = markdown.markdown(md_text, extensions=MD_EXTENSIONS)
    # Tutor renders raw HTML; give tables a class the theme can style and make
    # them scrollable on phones, which the course explicitly targets.
    html = html.replace(
        "<table>",
        '<div class="tyc-table-wrap" style="overflow-x:auto"><table class="tyc-table">',
    ).replace("</table>", "</table></div>")
    return html


def main():
    payload = []
    for path in MODULE_FILES:
        text = path.read_text()
        heading, summary, lessons = split_module(text)
        payload.append(
            {
                "file": path.name,
                "topic_title": heading,
                "topic_summary": summary,
                "lessons": [
                    {"title": t, "html": to_html(b)} for t, b in lessons
                ],
            }
        )

    out = HERE / "payload.json"
    out.write_text(json.dumps(payload, indent=1))

    for mod in payload:
        print(f"{mod['file']}: {mod['topic_title']!r}  ({len(mod['lessons'])} lessons)")
        for lsn in mod["lessons"]:
            print(f"    - {lsn['title'][:66]:68} {len(lsn['html']):6} chars")
    total = sum(len(m["lessons"]) for m in payload)
    print(f"\nTotal: {len(payload)} topics, {total} lessons -> {out}")

    # Safety check: author-only content must never reach the site.
    blob = json.dumps(payload)
    banned = [
        "Production notes",
        "not for learners",
        "Check before shipping",
        "could not be verified",
        "unverified",
        "cuttable",
    ]
    leaked = [b for b in banned if b in blob]
    if leaked:
        for b in leaked:
            print(f"!! WARNING: '{b}' leaked into payload", file=sys.stderr)
        return 1
    print("Author-only content correctly excluded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
