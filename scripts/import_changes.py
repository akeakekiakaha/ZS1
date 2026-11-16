#!/usr/bin/env python3
"""Import the school's published timetable-change notices into data/changes.json.

The original notice text is always retained. Parsed fields are hints for matching
and never modify data/lessons.json.
"""
from __future__ import annotations
import json, re, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

SOURCE = "https://www.zs-1.edu.pl/index.php/plan-lekcji/zmiany-do-planu"
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "changes.json"
HEADERS = {"User-Agent": "TeacherFinder/1.0 (school timetable changes; daily respectful fetch)"}
CLASS_RE = re.compile(r"^(?:[1-5][A-Z]{1,3}|[1-5][A-Z]{1,2}\d?)$", re.I)
LESSON_RE = re.compile(r"\blekcja\s+(\d+(?:\s*[,–-]\s*\d+)*)", re.I)
GROUP_RE = re.compile(r"\bgrup(?:a|y)\s*([12])\b", re.I)
ROOM_RE = re.compile(r"\bs\.\s*([A-Za-z0-9]+)\b")
TEACHER_RE = re.compile(r"\bp\.?\s+((?:[A-ZĄĆĘŁŃÓŚŹŻ]\.?\s*)?[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż-]+)")


def atomic_write(payload):
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=OUTPUT.parent, delete=False) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        name = tmp.name
    Path(name).replace(OUTPUT)


def extract_content(soup):
    # Joomla article wrappers vary between templates; prefer the article body.
    candidates = soup.select(".item-page, .com-content-article, article, main")
    for node in candidates:
        text = node.get_text("\n", strip=True)
        if "Zmiany do planu" in text and re.search(r"\d{4}-\d{2}-\d{2}", text):
            return node
    for node in soup.select("nav, header, footer, .navigation, .breadcrumbs, .mod-menu"):
        node.decompose()
    return soup.body or soup


def parse_messages(html):
    soup = BeautifulSoup(html, "html.parser")
    content = extract_content(soup)
    # Keep line breaks, remove empty lines and duplicated navigation labels.
    lines = [re.sub(r"\s+", " ", x).strip() for x in content.get_text("\n", strip=True).splitlines()]
    lines = [x for x in lines if x and x.lower() not in {"poprzednia", "następna", "na skróty", "ważne"}]
    date = None
    page_title = ""
    for line in lines:
        m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", line)
        if m:
            date = m.group(1)
            page_title = line
            break
    if not date:
        raise RuntimeError("Nie znaleziono daty publikacji (YYYY-MM-DD) w komunikacie szkoły; poprzedni plik pozostaje bez zmian.")

    # Start after the date/title and ignore site footer/navigation.
    start = next((i for i, line in enumerate(lines) if date in line), 0) + 1
    body = []
    for line in lines[start:]:
        if line in {"Na skróty", "WAŻNE", "Sekretariat"}:
            break
        if line in {"Poprzednia", "Następna"}:
            continue
        body.append(line)

    messages = []
    current_class = None
    for line in body:
        if CLASS_RE.fullmatch(line):
            current_class = line.upper()
            continue
        if line.startswith("©") or len(line) < 3:
            continue
        lesson_numbers = []
        for match in LESSON_RE.findall(line):
            for part in re.split(r"\s*[,–-]\s*", match):
                if part.isdigit(): lesson_numbers.append(int(part))
        group_match = GROUP_RE.search(line)
        room_match = ROOM_RE.search(line)
        teacher_match = TEACHER_RE.search(line)
        lower = line.casefold()
        scope = "lesson" if lesson_numbers else ("class" if current_class else "general")
        messages.append({
            "id": f"{date}:{current_class or 'ogolne'}:{len(messages)+1}",
            "date": date,
            "class_name": current_class,
            "lesson_numbers": sorted(set(lesson_numbers)),
            "group": group_match.group(1) if group_match else None,
            "teacher": teacher_match.group(1).strip() if teacher_match else None,
            "room": room_match.group(1) if room_match else None,
            "scope": scope,
            "raw_text": line,
        })
    if not messages:
        raise RuntimeError("Strona została pobrana, ale nie rozpoznano żadnych komunikatów; poprzedni plik pozostaje bez zmian.")
    return date, page_title, messages


def main():
    print(f"Pobieram komunikaty: {SOURCE}")
    response = requests.get(SOURCE, headers=HEADERS, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    date, title, messages = parse_messages(response.text)
    now = datetime.now(ZoneInfo("Europe/Warsaw"))
    payload = {
        "meta": {
            "source": SOURCE,
            "updated_at": now.isoformat(),
            "published_date": date,
            "page_title": title,
            "message_count": len(messages),
            "status": "ok",
        },
        "messages": messages,
    }
    atomic_write(payload)
    print(f"Zapisano {len(messages)} komunikatów dla {date} do {OUTPUT}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"BŁĄD importu zmian: {exc}", file=sys.stderr)
        raise
