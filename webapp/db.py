import datetime
import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import pandas as pd


DB_PATH = Path(__file__).resolve().parent.parent / "attendance.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                exam_number TEXT NOT NULL UNIQUE,
                stage TEXT NOT NULL,
                section TEXT,
                lab TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('present','absent')),
                UNIQUE(student_id, date),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()

        # Migration: add lab column to students if missing
        cols_stud = {r[1] for r in c.execute("PRAGMA table_info(students)").fetchall()}
        if "lab" not in cols_stud:
            c.execute("ALTER TABLE students ADD COLUMN lab TEXT")
            conn.commit()

        # Migration: add subject column to attendance if missing
        cols_att = {r[1] for r in c.execute("PRAGMA table_info(attendance)").fetchall()}
        if "subject" not in cols_att:
            c.execute("ALTER TABLE attendance ADD COLUMN subject TEXT")
            conn.commit()
            # Update unique constraint to include subject
            c.execute("DROP INDEX IF EXISTS attendance_student_date_unique")
            # Drop old unique constraint if exists
            try:
                c.execute("CREATE UNIQUE INDEX IF NOT EXISTS attendance_student_date_subject_unique ON attendance(student_id, date, COALESCE(subject, ''))")
            except sqlite3.OperationalError:
                pass  # Index might already exist
            conn.commit()


def add_student(name: str, exam_number: str, stage: str, section: str = "", lab: str = "") -> Tuple[bool, str]:
    created_at = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO students(name, exam_number, stage, section, lab, created_at) VALUES (?,?,?,?,?,?)",
                (name, exam_number, stage, section, lab, created_at),
            )
        return True, ""
    except sqlite3.IntegrityError:
        return False, "الرقم الامتحاني موجود مسبقاً."


def get_students() -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT name, exam_number, stage, section, lab, created_at FROM students ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def search_students(name_contains: str = "", exam_number: str = "", lab: Optional[str] = None) -> List[dict]:
    name_like = f"%{name_contains}%" if name_contains else None
    with get_conn() as conn:
        where = []
        params: List[object] = []
        if exam_number:
            where.append("exam_number = ?"); params.append(exam_number)
        if name_like is not None and not exam_number:
            where.append("name LIKE ?"); params.append(name_like)
        if lab:
            where.append("lab = ?"); params.append(lab)
        sql = "SELECT id, name, exam_number, stage, section, lab FROM students"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY name"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_student_id_by_exam(exam_number: str) -> Optional[int]:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM students WHERE exam_number = ?", (exam_number,)).fetchone()
        return int(row["id"]) if row else None


def upsert_attendance_for_date(exam_number: str, date: datetime.date, status: str, subject: str = "") -> bool:
    student_id = get_student_id_by_exam(exam_number)
    if student_id is None:
        return False
    date_str = date.isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO attendance(student_id, date, status, subject)
            VALUES (?,?,?,?)
            ON CONFLICT(student_id, date, COALESCE(subject, '')) DO UPDATE SET status=excluded.status
            """,
            (student_id, date_str, status, subject),
        )
    return True


def get_attendance_for_date_stage_section(
    date: datetime.date,
    stage: Optional[str] = None,
    section: Optional[str] = None,
    lab: Optional[str] = None,
    subject: Optional[str] = None,
) -> pd.DataFrame:
    params: List[object] = [date.isoformat()]
    where = ["a.date = ?"]
    if stage:
        where.append("s.stage = ?")
        params.append(stage)
    if section:
        where.append("(s.section = ?)")
        params.append(section)
    if lab:
        where.append("(s.lab = ?)")
        params.append(lab)
    if subject:
        where.append("(COALESCE(a.subject, '') = ?)")
        params.append(subject)

    sql = f"""
        SELECT a.date, a.status, a.subject, s.name, s.exam_number, s.stage, s.section, s.lab
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        WHERE {' AND '.join(where)}
        ORDER BY s.stage, s.section, s.lab, s.name
    """
    with get_conn() as conn:
        df = pd.read_sql_query(sql, conn, params=params)
        return df


def get_students_by_stage_section(stage: Optional[str], section: Optional[str], lab: Optional[str] = None) -> pd.DataFrame:
    params: List[object] = []
    where: List[str] = []
    if stage:
        where.append("stage = ?")
        params.append(stage)
    if section:
        where.append("(section = ?)")
        params.append(section)
    if lab:
        where.append("(lab = ?)")
        params.append(lab)
    sql = "SELECT name, exam_number, stage, section, lab FROM students"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY name"
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def get_attendance_by_student(exam_number: str) -> List[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT a.date, a.status, a.subject
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            WHERE s.exam_number = ?
            ORDER BY a.date DESC
            """,
            (exam_number,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_attendance_report_between_dates(
    start_date: datetime.date,
    end_date: datetime.date,
    stage: Optional[str] = None,
    section: Optional[str] = None,
    lab: Optional[str] = None,
    subject: Optional[str] = None,
) -> pd.DataFrame:
    params: List[object] = [start_date.isoformat(), end_date.isoformat()]
    where = ["a.date BETWEEN ? AND ?"]
    if stage:
        where.append("s.stage = ?")
        params.append(stage)
    if section:
        where.append("(s.section = ?)")
        params.append(section)
    if lab:
        where.append("(s.lab = ?)")
        params.append(lab)
    if subject:
        where.append("(COALESCE(a.subject, '') = ?)")
        params.append(subject)
    sql = f"""
        SELECT a.date, a.subject, s.name, s.exam_number, s.stage, s.section, s.lab, a.status
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        WHERE {' AND '.join(where)}
        ORDER BY a.date, s.stage, s.section, s.lab, s.name
    """
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def get_distinct_stages(defaults: Optional[Iterable[str]] = None) -> List[str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT stage FROM students ORDER BY stage").fetchall()
        stages = [r[0] for r in rows]
    if defaults:
        for s in defaults:
            if s not in stages:
                stages.append(s)
    return stages


def get_sections_for_stage(stage: str) -> List[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT COALESCE(NULLIF(section,''),'') FROM students WHERE stage=? ORDER BY section",
            (stage,),
        ).fetchall()
        sections = [r[0] or "" for r in rows]
    return sorted([s for s in sections if s])


def update_student(student_id: int, name: str, exam_number: str, stage: str, section: str, lab: str) -> Tuple[bool, str]:
    try:
        with get_conn() as conn:
            conn.execute(
                """
                UPDATE students
                SET name=?, exam_number=?, stage=?, section=?, lab=?
                WHERE id=?
                """,
                (name, exam_number, stage, section, lab, student_id),
            )
        return True, ""
    except sqlite3.IntegrityError:
        return False, "الرقم الامتحاني مستخدم لطالب آخر."


def delete_student(student_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM students WHERE id=?", (student_id,))


def get_students_filtered(
    name_contains: str = "",
    exam_number: str = "",
    stage: Optional[str] = None,
    section: Optional[str] = None,
    lab: Optional[str] = None,
) -> List[dict]:
    where: List[str] = []
    params: List[object] = []
    if name_contains:
        where.append("name LIKE ?"); params.append(f"%{name_contains}%")
    if exam_number:
        where.append("exam_number = ?"); params.append(exam_number)
    if stage:
        where.append("stage = ?"); params.append(stage)
    if section:
        where.append("section = ?"); params.append(section)
    if lab:
        where.append("lab = ?"); params.append(lab)
    sql = "SELECT id, name, exam_number, stage, section, lab, created_at FROM students"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY name"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def bulk_import_students(students_list: List[dict]) -> Tuple[int, int]:
    """
    Bulk import students. Returns (success_count, error_count)
    Each dict should have: name, exam_number, stage, section (optional), lab (optional)
    """
    added = 0
    errors = 0
    with get_conn() as conn:
        for s in students_list:
            try:
                name = s.get("name", "").strip()
                exam_number = s.get("exam_number", "").strip()
                stage = s.get("stage", "").strip()
                section = s.get("section", "").strip()
                lab = s.get("lab", "").strip()
                if name and exam_number and stage:
                    conn.execute(
                        "INSERT INTO students(name, exam_number, stage, section, lab, created_at) VALUES (?,?,?,?,?,?)",
                        (name, exam_number, stage, section, lab, datetime.datetime.now().isoformat(timespec="seconds")),
                    )
                    added += 1
                else:
                    errors += 1
            except sqlite3.IntegrityError:
                errors += 1
        conn.commit()
    return added, errors
