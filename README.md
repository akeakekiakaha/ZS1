# Teacher Finder · ZS1

Wyszukiwarka planu lekcji nauczycieli, sal i klas ZS1, uzupełniona o plan dzienny, tygodniowy oraz niezależne komunikaty o zmianach publikowane przez szkołę.

## Funkcje

- wyszukiwanie po kodzie nauczyciela, sali i oddziale;
- plan dzienny z wyborem dnia, klasy, nauczyciela lub sali;
- plan tygodniowy od poniedziałku do piątku dla wybranej klasy, nauczyciela lub sali;
- komunikaty o zmianach pobierane z [oficjalnej strony szkoły](https://www.zs-1.edu.pl/index.php/plan-lekcji/zmiany-do-planu);
- wyróżnianie lekcji, których dotyczą rozpoznane komunikaty;
- zachowanie oryginalnej treści każdego komunikatu, także gdy parser nie rozpozna wszystkich szczegółów;
- dwa niezależne harmonogramy GitHub Actions i ręczne uruchamianie obu importerów;
- bezpieczny zapis atomowy — nieudany import nie nadpisuje poprzedniej bazy.

## Dane i zasada działania zmian

- `data/lessons.json` — podstawowy plan pobierany przez `scripts/import_plans.py`.
- `data/changes.json` — komunikaty pobierane przez `scripts/import_changes.py`.

**Komunikaty nie modyfikują podstawowego planu.** Są osobną warstwą informacji. Parser próbuje rozpoznać datę, klasę, numery lekcji, grupę, nauczyciela i salę, ale zawsze zachowuje oryginalny tekst (`raw_text`). Informacja ogólna lub komunikat obejmujący kilka lekcji nie jest automatycznie zamieniany na pojedyncze zastępstwo.

Importer zmian pobiera aktualną treść strony szkoły. Jeśli strona nie zawiera daty albo rozpoznawalnych komunikatów, skrypt kończy się błędem i pozostawia poprzedni `changes.json` bez zmian.

## Uruchomienie lokalne

Wymagany Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python scripts/import_plans.py
python scripts/import_changes.py
python -m http.server 8000
```

Otwórz `http://localhost:8000` (nie uruchamiaj strony przez `file://`).

## Publikacja na GitHub Pages

1. Rozpakuj ZIP i wgraj całą zawartość folderu `teacher-finder` do repozytorium.
2. Włącz **Settings → Pages → Deploy from a branch → main → /(root)**.
3. W **Actions** upewnij się, że workflows są włączone.
4. Uruchom ręcznie workflow **Aktualizuj plany lekcji**.
5. Uruchom ręcznie workflow **Aktualizuj zmiany do planu**.
6. Po zakończeniu obu zadań sprawdź, czy `data/lessons.json` i `data/changes.json` zostały zaktualizowane.
7. Otwórz stronę GitHub Pages i przetestuj trzy widoki.

## Harmonogramy

| Proces | Harmonogram | Strefa |
|---|---|---|
| Pełny plan (`update-plans.yml`) | Niedziela, 20:17 | `Europe/Warsaw` |
| Zmiany (`update-changes.yml`) | Codziennie, 21:00 | `Europe/Warsaw` |

GitHub Actions obsługuje strefę `Europe/Warsaw`, więc harmonogram uwzględnia zmianę czasu CET/CEST. GitHub może uruchomić zadanie z niewielkim opóźnieniem. Każdy workflow ma również opcję `workflow_dispatch` do ręcznego uruchomienia.

## Struktura projektu

```text
teacher-finder/
├── .github/workflows/
│   ├── update-plans.yml
│   └── update-changes.yml
├── data/
│   ├── lessons.json
│   └── changes.json
├── scripts/
│   ├── import_plans.py
│   └── import_changes.py
├── app.js
├── index.html
├── styles.css
├── requirements.txt
└── README.md
```

## Ważne ograniczenia i kontrola

- Pierwszy import planu i pierwszy import zmian należy uruchomić ręcznie po wgraniu projektu; ZIP zawiera początkowe, puste pliki danych.
- Parser planu pozostaje dotychczasowym parserem Optivum. Jeśli szkoła zmieni HTML, import przerwie się bez nadpisania poprzedniej bazy.
- Importer zmian rozpoznaje typowe wpisy z nagłówkami klas i numerami lekcji, ale treść komunikatów może być niejednoznaczna. Oryginalny tekst pozostaje widoczny w aplikacji.
- Automatyczne wyróżnienie konkretnej lekcji jest możliwe tylko wtedy, gdy komunikat zawiera dane pozwalające ją dopasować. Komunikaty ogólne są wyświetlane w sekcji zmian.
- Plan tygodniowy pokazuje dni poniedziałek–piątek; komunikaty są przypisywane do daty publikowanej na stronie szkoły i filtrowane do wybranego elementu.
- Kod nauczyciela nie jest mapowany na imię i nazwisko, jeśli plan źródłowy nie dostarcza takiego mapowania.
- Wyniki przedstawiają plan i komunikaty opublikowane przez szkołę; nie potwierdzają faktycznej obecności nauczyciela ani bieżącej realizacji zajęć.

## Źródła

- Plany: `https://zs-1.edu.pl/plany/uczniowie/`
- Zmiany: `https://www.zs-1.edu.pl/index.php/plan-lekcji/zmiany-do-planu`
