const DATA_URL = "data/lessons.json";
const CHANGES_URL = "data/changes.json";
const DAYS = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"];
const state = { mode: "teacher", view: "search", lessons: [], changes: [], meta: {}, changesMeta: {} };
const input = document.querySelector("#search-input");
const results = document.querySelector("#results");
const labels = {
  teacher: ["KOD NAUCZYCIELA", "Np. Ga, Zi, WE…", "Wpisz kod nauczyciela, np. Ga albo WE.", "Wyszukaj nauczyciela"],
  room: ["NUMER SALI", "Np. 204, SG3, Aula…", "Wpisz numer lub oznaczenie sali.", "Wyszukaj salę"],
  class: ["ODDZIAŁ", "Np. 4B, 2A…", "Wpisz symbol klasy, np. 4B.", "Wyszukaj klasę"]
};
const fieldFor = category => category === "teacher" ? "teacher" : category === "room" ? "room" : "class_name";
const normalize = value => String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const sortLessons = list => [...list].sort((a,b) => (a.day_index-b.day_index) || (a.lesson_number-b.lesson_number) || String(a.class_name).localeCompare(String(b.class_name), "pl"));

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".tab").forEach(btn => {
    const active = btn.dataset.mode === mode;
    btn.classList.toggle("active", active); btn.setAttribute("aria-selected", String(active));
  });
  const [label, placeholder, hint, title] = labels[mode];
  document.querySelector("#search-label").textContent = label;
  input.placeholder = placeholder; document.querySelector("#search-hint").textContent = hint;
  document.querySelector("#results-title").textContent = title; renderSearch();
}
document.querySelectorAll(".tab").forEach(btn => btn.addEventListener("click", () => setMode(btn.dataset.mode)));
input.addEventListener("input", renderSearch);
document.querySelector("#clear-btn").addEventListener("click", () => { input.value = ""; input.focus(); renderSearch(); });

document.querySelectorAll(".view-tab").forEach(btn => btn.addEventListener("click", () => setView(btn.dataset.view)));
function setView(view) {
  state.view = view;
  document.querySelectorAll(".view-tab").forEach(btn => {
    const active = btn.dataset.view === view;
    btn.classList.toggle("active", active); btn.setAttribute("aria-pressed", String(active));
  });
  document.querySelectorAll(".view-panel").forEach(panel => panel.hidden = panel.id !== `${view}-view`);
  if (view === "day") renderDay();
  if (view === "week") renderWeek();
}
["day-select", "day-category", "day-filter"].forEach(id => document.getElementById(id).addEventListener(id === "day-filter" ? "input" : "change", renderDay));
["week-category", "week-filter"].forEach(id => document.getElementById(id).addEventListener(id === "week-filter" ? "input" : "change", renderWeek));

function renderLesson(item, changed = false) {
  return `<article class="lesson-card${changed ? " lesson-changed" : ""}">
    <div class="lesson-time">${esc(item.time || "—")}<small>${esc(item.day || DAYS[item.day_index] || "")}, lekcja ${esc(item.lesson_number)}</small></div>
    <div class="lesson-main"><strong>${esc(item.subject || "Zajęcia")}</strong><p>${esc(item.teacher || "—")} · ${esc(item.class_name || "—")}${item.group ? ` · grupa ${esc(item.group)}` : ""}</p></div>
    <div class="lesson-room">${esc(item.room || "Brak sali")}</div>${changed ? '<span class="changed-tag">ZMIANA</span>' : ""}
  </article>`;
}
function plural(n) { if (n===1) return "lekcja"; if (n%10>=2 && n%10<=4 && (n%100<12 || n%100>14)) return "lekcje"; return "lekcji"; }
function empty(title, description) { return `<div class="empty-state"><div class="empty-icon">⌕</div><h3>${esc(title)}</h3><p>${esc(description)}</p></div>`; }
function renderSearch() {
  const query = normalize(input.value);
  if (!query) { document.querySelector("#result-count").textContent = "—"; results.innerHTML = empty("Wpisz kod, salę lub klasę", "Wyniki pojawią się tutaj po wyszukaniu."); return; }
  const field = fieldFor(state.mode);
  const matches = sortLessons(state.lessons.filter(item => normalize(item[field]).includes(query)));
  document.querySelector("#result-count").textContent = `${matches.length} ${plural(matches.length)}`;
  results.innerHTML = matches.length ? matches.map(item => renderLesson(item, hasLessonChange(item))).join("") : empty("Brak wyników", state.lessons.length ? "Nie znaleziono pasujących lekcji. Sprawdź wpisaną frazę." : "Baza nie zawiera jeszcze pobranych planów. Uruchom importer zgodnie z README.");
}

function nextDateForDay(dayIndex) {
  const now = new Date();
  const target = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diff = (dayIndex - target.getDay() + 7) % 7;
  target.setDate(target.getDate() + diff);
  // If the selected weekday is today, retain today as the relevant date.
  return `${target.getFullYear()}-${String(target.getMonth()+1).padStart(2,"0")}-${String(target.getDate()).padStart(2,"0")}`;
}
function messageMatches(message, category, value) {
  if (!value) return true;
  const q = normalize(value);
  const field = category === "teacher" ? message.teacher : category === "room" ? message.room : message.class_name;
  return normalize(field).includes(q) || (category === "teacher" && normalize(field).startsWith(q)) || (category === "class" && normalize(message.raw_text).includes(q));
}
function messagesFor(date, category, value) {
  return state.changes.filter(m => (!m.date || m.date === date) && messageMatches(m, category, value));
}
function noticeMarkup(messages, date) {
  if (!messages.length) return `<div class="notice-empty">Brak opublikowanych komunikatów o zmianach dla ${esc(date)}.</div>`;
  return `<div class="notice-heading"><span class="notice-dot"></span> KOMUNIKATY O ZMIANACH · ${esc(date)}</div>` + messages.map(m => `<article class="notice-card"><div class="notice-meta">${esc(m.class_name || "Informacja ogólna")}${m.lesson_numbers?.length ? ` · lekcja${m.lesson_numbers.length>1?"e":""} ${m.lesson_numbers.map(esc).join(", ")}` : " · komunikat ogólny"}${m.group ? ` · grupa ${esc(m.group)}` : ""}</div><p>${esc(m.raw_text)}</p></article>`).join("");
}
function hasLessonChange(lesson) {
  return state.changes.some(m => m.date === nextDateForDay(lesson.day_index) && Array.isArray(m.lesson_numbers) && m.lesson_numbers.length > 0 && (!m.class_name || normalize(m.class_name) === normalize(lesson.class_name)) && m.lesson_numbers.includes(Number(lesson.lesson_number)) && (!m.group || (lesson.group && normalize(m.group) === normalize(lesson.group))));
}
function renderDay() {
  const day = Number(document.querySelector("#day-select").value);
  const category = document.querySelector("#day-category").value;
  const value = document.querySelector("#day-filter").value;
  const date = nextDateForDay(day);
  const lessons = sortLessons(state.lessons.filter(item => Number(item.day_index) === day && (!value || normalize(item[fieldFor(category)]).includes(normalize(value)))));
  document.querySelector("#day-count").textContent = `${lessons.length} ${plural(lessons.length)}`;
  document.querySelector("#day-changes").innerHTML = noticeMarkup(messagesFor(date, category, value), date);
  document.querySelector("#day-results").innerHTML = lessons.length ? lessons.map(item => renderLesson(item, hasLessonChange(item))).join("") : empty("Brak lekcji", value ? "Nie znaleziono zajęć dla wybranego elementu w tym dniu." : "Brak danych dla wybranego dnia.");
}
function renderWeek() {
  const category = document.querySelector("#week-category").value;
  const value = document.querySelector("#week-filter").value;
  if (!value.trim()) {
    document.querySelector("#week-count").textContent = "—";
    document.querySelector("#week-results").innerHTML = empty("Wybierz element planu", "Wpisz klasę, kod nauczyciela lub salę, aby wyświetlić tabelę tygodniową.");
    document.querySelector("#week-changes").innerHTML = "";
    return;
  }
  const field = fieldFor(category);
  const lessons = sortLessons(state.lessons.filter(item => normalize(item[field]).includes(normalize(value))));
  document.querySelector("#week-count").textContent = `${lessons.length} ${plural(lessons.length)}`;
  if (!lessons.length) {
    document.querySelector("#week-results").innerHTML = empty("Brak wyników", "Nie znaleziono planu dla podanego elementu.");
    document.querySelector("#week-changes").innerHTML = ""; return;
  }
  const numbers = [...new Set(lessons.map(x => Number(x.lesson_number)))].sort((a,b)=>a-b);
  const cells = numbers.map(number => `<tr><th class="period-cell">${number}</th>${DAYS.map((day, index) => {
    const dayLessons = lessons.filter(x => Number(x.day_index) === index && Number(x.lesson_number) === number);
    return `<td>${dayLessons.map(item => `<div class="week-lesson${hasLessonChange(item) ? " week-lesson-changed" : ""}"><strong>${esc(item.time || "—")}</strong><span>${esc(item.subject || "Zajęcia")}</span><small>${esc(item.teacher || "—")} · ${esc(item.room || "—")}${item.group ? ` · gr. ${esc(item.group)}` : ""}</small>${hasLessonChange(item) ? '<em>Zmiana</em>' : ""}</div>`).join("") || '<span class="cell-empty">—</span>'}</td>`;
  }).join("")}</tr>`).join("");
  document.querySelector("#week-results").innerHTML = `<table class="week-table"><thead><tr><th>Lekcja</th>${DAYS.map(day => `<th>${day}</th>`).join("")}</tr></thead><tbody>${cells}</tbody></table>`;
  const notices = DAYS.flatMap((_, index) => messagesFor(nextDateForDay(index), category, value));
  const unique = [...new Map(notices.map(m => [m.id || `${m.date}:${m.raw_text}`, m])).values()];
  document.querySelector("#week-changes").innerHTML = unique.length ? `<div class="notice-heading"><span class="notice-dot"></span> KOMUNIKATY DOTYCZĄCE WYBRANEGO ELEMENTU</div>${unique.map(m => `<article class="notice-card"><div class="notice-meta">${esc(m.date)} · ${esc(m.class_name || "Informacja ogólna")}${m.lesson_numbers?.length ? ` · lekcja ${m.lesson_numbers.map(esc).join(", ")}` : ""}</div><p>${esc(m.raw_text)}</p></article>`).join("")}` : `<div class="notice-empty">Brak komunikatów o zmianach pasujących do wybranego elementu w najbliższym tygodniu.</div>`;
}

async function loadJson(url) {
  const response = await fetch(`${url}?v=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Nie udało się pobrać ${url}`);
  return response.json();
}
async function loadData() {
  try {
    const [plans, changes] = await Promise.allSettled([loadJson(DATA_URL), loadJson(CHANGES_URL)]);
    if (plans.status === "fulfilled") {
      state.lessons = Array.isArray(plans.value.lessons) ? plans.value.lessons : [];
      state.meta = plans.value.meta || {};
    } else throw plans.reason;
    if (changes.status === "fulfilled") {
      state.changes = Array.isArray(changes.value.messages) ? changes.value.messages : [];
      state.changesMeta = changes.value.meta || {};
    }
    const planStamp = state.meta.updated_at ? new Date(state.meta.updated_at).toLocaleString("pl-PL") : "brak synchronizacji";
    const changeStamp = state.changesMeta.updated_at ? new Date(state.changesMeta.updated_at).toLocaleString("pl-PL") : "brak zmian";
    document.querySelector("#sync-label").textContent = state.lessons.length ? `Plan: ${planStamp} · zmiany: ${changeStamp}` : "Oczekiwanie na pierwszą synchronizację planu";
    renderSearch(); renderDay(); renderWeek();
  } catch (error) {
    document.querySelector("#sync-label").textContent = "Nie udało się wczytać planu";
    results.innerHTML = empty("Nie można wczytać bazy", "Sprawdź, czy aplikacja została opublikowana razem z folderem data.");
  }
}
loadData();
