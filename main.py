from __future__ import annotations

import html
import json
import random
import urllib.parse
from collections import defaultdict
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List, Tuple

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MAX_ATTEMPTS = 300


@dataclass(frozen=True)
class SubjectAssignment:
    subject: str
    teacher: str
    weekly_periods: int


@dataclass(frozen=True)
class ClassConfig:
    name: str
    subjects: List[SubjectAssignment]


def parse_classes(raw_payload: str) -> List[ClassConfig]:
    data = json.loads(raw_payload)
    classes: List[ClassConfig] = []

    if not isinstance(data, list) or not data:
        raise ValueError("Classes payload must be a non-empty JSON array.")

    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("Each class entry must be a JSON object.")

        class_name = str(entry.get("name", "")).strip()
        raw_subjects = entry.get("subjects")
        if not class_name:
            raise ValueError("Each class must have a non-empty 'name'.")
        if not isinstance(raw_subjects, list) or not raw_subjects:
            raise ValueError(f"Class '{class_name}' must provide a non-empty 'subjects' list.")

        subjects: List[SubjectAssignment] = []
        seen_subjects = set()
        for raw_subject in raw_subjects:
            if not isinstance(raw_subject, dict):
                raise ValueError(f"Subjects for class '{class_name}' must be JSON objects.")
            subject = str(raw_subject.get("name", "")).strip()
            teacher = str(raw_subject.get("teacher", "")).strip()
            periods = int(raw_subject.get("weekly_periods", 0))

            if not subject or not teacher:
                raise ValueError(
                    f"Class '{class_name}' has a subject with missing name/teacher."
                )
            if periods <= 0:
                raise ValueError(
                    f"Class '{class_name}' subject '{subject}' must have weekly_periods > 0."
                )
            if subject in seen_subjects:
                raise ValueError(f"Class '{class_name}' has duplicate subject '{subject}'.")

            seen_subjects.add(subject)
            subjects.append(SubjectAssignment(subject=subject, teacher=teacher, weekly_periods=periods))

        classes.append(ClassConfig(name=class_name, subjects=subjects))

    return classes


def validate_capacity(classes: List[ClassConfig], periods_per_day: int) -> int:
    total_slots = len(DAYS) * periods_per_day
    for class_cfg in classes:
        required_periods = sum(sub.weekly_periods for sub in class_cfg.subjects)
        if required_periods > total_slots:
            raise ValueError(
                f"Class '{class_cfg.name}' requires {required_periods} periods/week, "
                f"but only {total_slots} slots are available."
            )
    return total_slots


def generate_timetables(
    classes: List[ClassConfig], periods_per_day: int, *, seed: int | None = None
) -> Dict[str, List[List[str]]]:
    if periods_per_day <= 0:
        raise ValueError("periods_per_day must be positive.")

    validate_capacity(classes, periods_per_day)
    rng = random.Random(seed)

    for _ in range(MAX_ATTEMPTS):
        remaining: Dict[str, Dict[str, int]] = {
            class_cfg.name: {sub.subject: sub.weekly_periods for sub in class_cfg.subjects}
            for class_cfg in classes
        }
        teachers_for_class_subject: Dict[Tuple[str, str], str] = {
            (class_cfg.name, sub.subject): sub.teacher
            for class_cfg in classes
            for sub in class_cfg.subjects
        }
        tables: Dict[str, List[List[str]]] = {
            class_cfg.name: [["Free" for _ in range(periods_per_day)] for _ in DAYS]
            for class_cfg in classes
        }

        failed = False
        for day_idx, _day in enumerate(DAYS):
            for period_idx in range(periods_per_day):
                busy_teachers: set[str] = set()
                class_order = [class_cfg.name for class_cfg in classes]
                rng.shuffle(class_order)

                for class_name in class_order:
                    candidates = [
                        subject
                        for subject, count in remaining[class_name].items()
                        if count > 0
                        and teachers_for_class_subject[(class_name, subject)] not in busy_teachers
                    ]

                    if not candidates:
                        if all(count == 0 for count in remaining[class_name].values()):
                            continue
                        failed = True
                        break

                    candidates.sort(
                        key=lambda s: (remaining[class_name][s], rng.random()),
                        reverse=True,
                    )
                    chosen = candidates[0]
                    teacher = teachers_for_class_subject[(class_name, chosen)]

                    tables[class_name][day_idx][period_idx] = f"{chosen} ({teacher})"
                    remaining[class_name][chosen] -= 1
                    busy_teachers.add(teacher)

                if failed:
                    break
            if failed:
                break

        if failed:
            continue

        all_done = all(
            remaining[class_cfg.name][sub.subject] == 0
            for class_cfg in classes
            for sub in class_cfg.subjects
        )
        if all_done:
            return tables

    raise ValueError(
        "Could not generate a conflict-free timetable with current constraints. "
        "Try increasing periods/day, reducing subject load, or adding teachers."
    )


def teacher_load(tables: Dict[str, List[List[str]]]) -> Dict[str, int]:
    load: Dict[str, int] = defaultdict(int)
    for class_table in tables.values():
        for day in class_table:
            for slot in day:
                if slot != "Free":
                    teacher = slot.split("(")[-1].rstrip(")")
                    load[teacher] += 1
    return dict(sorted(load.items(), key=lambda item: item[0]))


DEFAULT_CONFIG = json.dumps(
    [
        {
            "name": "Class 8A",
            "subjects": [
                {"name": "Math", "teacher": "Sharma", "weekly_periods": 6},
                {"name": "English", "teacher": "Patel", "weekly_periods": 5},
                {"name": "Science", "teacher": "Rao", "weekly_periods": 5},
                {"name": "History", "teacher": "Iyer", "weekly_periods": 4},
            ],
        },
        {
            "name": "Class 8B",
            "subjects": [
                {"name": "Math", "teacher": "Sharma", "weekly_periods": 6},
                {"name": "English", "teacher": "Patel", "weekly_periods": 5},
                {"name": "Science", "teacher": "Sen", "weekly_periods": 5},
                {"name": "Geography", "teacher": "Iyer", "weekly_periods": 4},
            ],
        },
    ],
    indent=2,
)


def render_page(
    *,
    classes_json: str,
    periods_per_day: int,
    error: str | None = None,
    tables: Dict[str, List[List[str]]] | None = None,
    loads: Dict[str, int] | None = None,
) -> str:
    safe_json = html.escape(classes_json)
    error_html = f'<p class="error">Error: {html.escape(error)}</p>' if error else ""

    tables_html = ""
    if tables:
        load_rows = "".join(
            f"<tr><td>{html.escape(teacher)}</td><td>{count}</td></tr>"
            for teacher, count in (loads or {}).items()
        )

        sections = [
            f"""
            <div class=\"card\">
              <h2>Teacher Weekly Load</h2>
              <table>
                <tr><th>Teacher</th><th>Assigned Periods</th></tr>
                {load_rows}
              </table>
            </div>
            """
        ]

        for class_name, rows in tables.items():
            header = "".join(f"<th>Period {idx + 1}</th>" for idx in range(len(rows[0])))
            body_rows = []
            for day_idx, row in enumerate(rows):
                slots = "".join(f"<td>{html.escape(slot)}</td>" for slot in row)
                body_rows.append(
                    f"<tr><td><strong>{DAYS[day_idx]}</strong></td>{slots}</tr>"
                )

            sections.append(
                f"""
                <div class=\"card\">
                  <h2>{html.escape(class_name)}</h2>
                  <table>
                    <tr><th>Day</th>{header}</tr>
                    {''.join(body_rows)}
                  </table>
                </div>
                """
            )

        tables_html = "\n".join(sections)

    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>School Timetable Planner</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; background: #f8fafc; }}
    .card {{ background: white; border-radius: 10px; padding: 1rem 1.25rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 1rem; }}
    h1, h2 {{ margin-top: 0; }}
    textarea {{ width: 100%; min-height: 260px; font-family: monospace; font-size: 0.95rem; }}
    input[type='number'] {{ width: 90px; padding: 0.3rem; }}
    button {{ background: #2563eb; color: white; border: none; padding: 0.5rem 0.9rem; border-radius: 6px; cursor: pointer; }}
    button:hover {{ background: #1d4ed8; }}
    table {{ border-collapse: collapse; width: 100%; margin: 0.75rem 0 1.25rem; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 0.45rem; text-align: center; }}
    th {{ background: #eff6ff; }}
    .error {{ color: #b91c1c; font-weight: bold; }}
    .hint {{ color: #334155; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Multi-Class Timetable Planner</h1>
    <p class="hint">Generate practical weekly schedules for multiple classes while preventing teacher double-booking in the same period.</p>
    <form method="post">
      <label for="periods_per_day"><strong>Periods per day:</strong></label>
      <input id="periods_per_day" name="periods_per_day" type="number" min="1" value="{periods_per_day}" required>
      <p><strong>Classes JSON:</strong></p>
      <textarea id="classes_json" name="classes_json" required>{safe_json}</textarea>
      <p><button type="submit">Generate Timetable</button></p>
    </form>
    {error_html}
  </div>
  {tables_html}
</body>
</html>
"""


class TimetableHandler(BaseHTTPRequestHandler):
    def _send_html(self, html_body: str) -> None:
        encoded = html_body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        self._send_html(render_page(classes_json=DEFAULT_CONFIG, periods_per_day=7))

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        form = urllib.parse.parse_qs(payload)

        classes_json = form.get("classes_json", [DEFAULT_CONFIG])[0]
        periods_raw = form.get("periods_per_day", ["7"])[0]

        error = None
        tables = None
        loads = None

        try:
            periods_per_day = int(periods_raw)
            classes = parse_classes(classes_json)
            tables = generate_timetables(classes, periods_per_day)
            loads = teacher_load(tables)
        except (ValueError, json.JSONDecodeError) as exc:
            periods_per_day = int(periods_raw) if periods_raw.isdigit() else 7
            error = str(exc)

        self._send_html(
            render_page(
                classes_json=classes_json,
                periods_per_day=periods_per_day,
                error=error,
                tables=tables,
                loads=loads,
            )
        )


def run_server(port: int = 5000) -> None:
    server = HTTPServer(("0.0.0.0", port), TimetableHandler)
    print(f"Timetable planner running on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
