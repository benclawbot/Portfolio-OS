from __future__ import annotations

import re

_IMAGE_MARKER = re.compile(r"<\s*(?:img|picture)\b|!\[[^\]]*\]\([^\)]+\)", re.IGNORECASE)
_HTML_START = re.compile(r"<\s*(p|div|picture|table)\b", re.IGNORECASE)


def extract_hero_banner(markdown: str) -> str:
    """Return a leading image/banner block, excluding headings and body copy."""
    lines = markdown.replace("\r\n", "\n").splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines):
        return ""

    first = lines[index].strip()
    if first.startswith("#"):
        return ""

    if _HTML_START.search(first):
        captured: list[str] = []
        depth = 0
        started = False
        for line in lines[index:]:
            stripped = line.strip()
            if stripped.startswith("#") and depth == 0:
                break
            captured.append(line)
            opens = len(re.findall(r"<\s*(p|div|picture|table)\b[^>]*>", line, re.IGNORECASE))
            closes = len(re.findall(r"<\s*/\s*(p|div|picture|table)\s*>", line, re.IGNORECASE))
            if opens:
                started = True
            depth += opens - closes
            if started and depth <= 0:
                break
        block = "\n".join(captured).strip()
        return block if _IMAGE_MARKER.search(block) else ""

    if _IMAGE_MARKER.search(first):
        captured = []
        for line in lines[index:]:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                break
            if not (_IMAGE_MARKER.search(stripped) or stripped.startswith("[") or stripped.startswith("<!--")):
                break
            captured.append(line)
        block = "\n".join(captured).strip()
        return block if _IMAGE_MARKER.search(block) else ""

    return ""
