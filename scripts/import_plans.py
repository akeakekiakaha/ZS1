#!/usr/bin/env python3
"""
Pobiera listę oddziałów i ich plany z witryny ZS1, a następnie zapisuje
ujednoliconą bazę data/lessons.json.

Parser celowo przerywa synchronizację, jeśli nie potrafi rozpoznać struktury
strony. Dzięki temu błędny/niepełny import nie nadpisze poprzedniej bazy.
"""
from __future__ import annotations
import json, re, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

BASE = "https://zs-1.edu.pl/plany/uczniowie/"
LIST_URL = urljoin(BASE, "lista.html")
OUTPUT = Path(__file__).resolve().parents[1] / "data" / "lessons.json"
DAYS = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
HEADERS = {"User-Agent": "TeacherFinder/1.0 (school timetable index; respectful weekly fetch)"}
TIME_RE = re.compile(r"^\s*(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})\s*$")
GROUP_RE = re.compile(r"(?:[- ]([12]/2))$")
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

def fetch(url: str) -> str:
    response = SESSION.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text

def get_classes(html: str):
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for link in soup.select("a[href]"):
        href = link.get("href", "").strip()
        label = " ".join(link.get_text(" ", strip=True).split())
        if re.fullmatch(r"plany/o\d+\.html", href) and label:
            found.append({"class_name": label.split()[0].upper(), "label": label, "url": urljoin(BASE, href)})
    # Remove duplicate hrefs while preserving order.
    unique = {item["url"]: item for item in found}
    if not unique:
        raise RuntimeError("Nie znaleziono linków plany/oN.html na liście oddziałów.")
    return list(unique.values())

def cell_lines(cell):
    # Explicit <br> elements separate group entries. Inline formatting (e.g. <b>)
    # must not split a single entry into multiple fragments.
    from bs4 import NavigableString
    fragment = BeautifulSoup(str(cell), "html.parser")
    for br in fragment.find_all("br"):
        br.replace_with(NavigableString(" __TF_BREAK__ "))
    raw = fragment.get_text(" ", strip=True)
    return [" ".join(line.split()) for line in raw.split("__TF_BREAK__") if line.strip()]

def parse_lesson_line(line: str):
    line = re.sub(r"\s+", " ", line).strip()
    tokens = line.split()
    if len(tokens) < 3:
        return None
    # Optivum entries end in: subject, teacher code, room.
    room = tokens[-1]
    teacher = tokens[-2]
    subject = " ".join(tokens[:-2]).strip()
    if not subject or not re.fullmatch(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż#]{1,5}", teacher):
        return None
    group_match = GROUP_RE.search(subject)
    group = group_match.group(1) if group_match else ""
    subject = GROUP_RE.sub("", subject).strip()
    return {"subject": subject, "teacher": teacher, "room": room, "group": group}

def parse_plan(html: str, class_name: str):
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        raise RuntimeError(f"{class_name}: nie znaleziono tabeli planu.")
    # Choose the table with a header containing weekday names.
    table = None
    for candidate in tables:
        text = candidate.get_text(" ", strip=True).lower()
        if "poniedziałek" in text and "piątek" in text:
            table = candidate
            break
    if table is None:
        raise RuntimeError(f"{class_name}: nie rozpoznano tabeli tygodniowej.")
    rows = table.find_all("tr")
    lessons = []
    recognized_rows = 0
    for row in rows:
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) < 7:
            continue
        values = [c.get_text(" ", strip=True) for c in cells]
        # The time column is normally the second cell.
        time_value = values[1] if len(values) > 1 else ""
        time_match = TIME_RE.match(time_value)
        if not time_match:
            continue
        recognized_rows += 1
        lesson_number = re.sub(r"\D", "", values[0]) or str(recognized_rows)
        for day_index in range(5):
            cell_index = day_index + 2
            if cell_index >= len(cells):
                continue
            for line in cell_lines(cells[cell_index]):
                parsed = parse_lesson_line(line)
                if not parsed:
                    continue
                lessons.append({
                    "class_name": class_name,
                    "day": DAYS[day_index],
                    "day_index": day_index,
                    "lesson_number": int(lesson_number),
                    "time": f"{time_match.group(1)}–{time_match.group(2)}",
                    **parsed
                })
    if recognized_rows < 5:
        raise RuntimeError(f"{class_name}: rozpoznano tylko {recognized_rows} wierszy godzinowych.")
    return lessons

def main():
    print(f"Pobieram listę oddziałów: {LIST_URL}")
    classes = get_classes(fetch(LIST_URL))
    print(f"Znaleziono {len(classes)} oddziałów.")
    all_lessons, errors = [], []
    for item in classes:
        try:
            parsed = parse_plan(fetch(item["url"]), item["class_name"])
            if not parsed:
                raise RuntimeError("Plan nie zawiera rozpoznanych lekcji.")
            all_lessons.extend(parsed)
            print(f"OK {item['class_name']}: {len(parsed)} wpisów")
        except Exception as exc:
            errors.append(f"{item['class_name']}: {exc}")
            print(f"BŁĄD {item['class_name']}: {exc}", file=sys.stderr)

    # Fail closed: don't publish a partial snapshot if any class failed.
    if errors:
        raise RuntimeError("Synchronizacja niekompletna; poprzednia baza pozostaje bez zmian:\n" + "\n".join(errors))
    if len(classes) < 10 or len(all_lessons) < 20:
        raise RuntimeError("Podejrzanie mały wynik importu; nie nadpisuję poprzedniej bazy.")

    payload = {
        "meta": {
            "source": BASE,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "class_count": len(classes),
            "lesson_count": len(all_lessons),
            "classes": [{"class_name": c["class_name"], "label": c["label"]} for c in classes]
        },
        "lessons": all_lessons
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=OUTPUT.parent, delete=False) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        temp_name = tmp.name
    Path(temp_name).replace(OUTPUT)
    print(f"Zapisano {len(all_lessons)} lekcji z {len(classes)} oddziałów do {OUTPUT}")

if __name__ == "__main__":
    main()
