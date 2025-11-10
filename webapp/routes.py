import datetime
from io import BytesIO
from typing import Optional

import pandas as pd
from flask import Blueprint, Response, flash, redirect, render_template, request, send_file, url_for

from .db import (
    add_student,
    get_attendance_by_student,
    get_attendance_for_date_stage_section,
    get_attendance_report_between_dates,
    get_distinct_stages,
    get_sections_for_stage,
    get_students,
    get_students_by_stage_section,
    search_students,
    get_students_filtered,
    update_student,
    delete_student,
    upsert_attendance_for_date,
    bulk_import_students,
)
from .utils_export import dataframe_to_excel_bytes, dataframe_to_pdf_bytes


bp = Blueprint("main", __name__)


@bp.route("/")
def index() -> str:
    today = datetime.date.today()
    students = get_students()
    df_today = get_attendance_for_date_stage_section(today)
    present = int((df_today.status == "present").sum()) if not df_today.empty else 0
    absent = int((df_today.status == "absent").sum()) if not df_today.empty else 0
    return render_template("index.html", total=len(students), present=present, absent=absent)


@bp.route("/students", methods=["GET", "POST"])
def students_page() -> str:
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        exam_number = request.form.get("exam_number", "").strip()
        stage = request.form.get("stage", "").strip()
        section = request.form.get("section", "").strip()
        lab = request.form.get("lab", "").strip()
        if not name or not exam_number or not stage:
            flash("يرجى إدخال الاسم والرقم الامتحاني والمرحلة.", "danger")
        else:
            ok, msg = add_student(name, exam_number, stage, section, lab)
            if ok:
                flash("تم حفظ الطالب بنجاح.", "success")
                return redirect(url_for("main.students_page"))
            else:
                flash(msg or "فشل الحفظ.", "danger")
    students = get_students()
    return render_template("students.html", students=students)


@bp.route("/search", methods=["GET"]) 
def search_page() -> str:
    q_name = request.args.get("name", "").strip()
    q_exam = request.args.get("exam", "").strip()
    q_lab = request.args.get("lab", "").strip()
    results = search_students(name_contains=q_name, exam_number=q_exam, lab=q_lab or None)
    selected_exam = request.args.get("selected_exam", "")
    att = []
    if selected_exam:
        att = get_attendance_by_student(selected_exam)
    return render_template("search.html", results=results, att=att, selected_exam=selected_exam)


@bp.route("/attendance", methods=["GET", "POST"]) 
def attendance_page() -> str:
    stages = ["الكل"] + get_distinct_stages(defaults=["الأولى", "الثانية", "الثالثة", "الرابعة"]) 
    stage = request.values.get("stage", stages[0])
    sections = ["الكل"] + (get_sections_for_stage(stage) if stage != "الكل" else [])
    section = request.values.get("section", sections[0])
    lab = request.values.get("lab", "الكل")
    subject = request.values.get("subject", "الكل")
    date_str = request.values.get("date")
    selected_date = datetime.date.fromisoformat(date_str) if date_str else datetime.date.today()

    students_df = get_students_by_stage_section(
        None if stage == "الكل" else stage,
        None if section == "الكل" else section,
        None if lab == "الكل" else lab,
    )
    # Convert DataFrame to list of dicts for proper template rendering
    students_list = students_df.to_dict('records') if not students_df.empty else []
    
    att_df = get_attendance_for_date_stage_section(
        date=selected_date,
        stage=None if stage == "الكل" else stage,
        section=None if section == "الكل" else section,
        lab=None if lab == "الكل" else lab,
        subject=None if subject == "الكل" else subject,
    )
    prefill = {}
    if not att_df.empty:
        for _, r in att_df.iterrows():
            prefill[str(r["exam_number"])]= r["status"]

    if request.method == "POST":
        subject_val = request.form.get("subject", "")
        saved = 0
        for s in students_list:
            exam_no = str(s.get("exam_number", ""))
            val = request.form.get(f"status_{exam_no}")
            if val:
                if upsert_attendance_for_date(exam_no, selected_date, val, subject_val):
                    saved += 1
        flash(f"تم حفظ {saved} سجل/سجلات.", "success")
        return redirect(url_for("main.attendance_page", stage=stage, section=section, lab=lab, subject=subject, date=selected_date.isoformat()))

    return render_template(
        "attendance.html",
        stages=stages,
        stage=stage,
        sections=sections,
        section=section,
        lab=lab,
        subject=subject,
        selected_date=selected_date,
        students_list=students_list,
        prefill=prefill,
    )


@bp.route("/export", methods=["GET"]) 
def export_page() -> str:
    stages = ["الكل"] + get_distinct_stages(defaults=["الأولى", "الثانية", "الثالثة", "الرابعة"]) 
    stage = request.args.get("stage", stages[0])
    sections = ["الكل"] + (get_sections_for_stage(stage) if stage != "الكل" else [])
    section = request.args.get("section", sections[0])
    lab = request.args.get("lab", "الكل")
    subject = request.args.get("subject", "الكل")
    start = request.args.get("start")
    end = request.args.get("end")
    start_date = datetime.date.fromisoformat(start) if start else datetime.date.today().replace(day=1)
    end_date = datetime.date.fromisoformat(end) if end else datetime.date.today()

    df = get_attendance_report_between_dates(
        start_date,
        end_date,
        None if stage == "الكل" else stage,
        None if section == "الكل" else section,
        None if lab == "الكل" else lab,
        None if subject == "الكل" else subject,
    )
    return render_template("export.html", stages=stages, sections=sections, stage=stage, section=section, lab=lab, subject=subject, start_date=start_date, end_date=end_date, df=df)


@bp.get("/export/excel")
def export_excel() -> Response:
    stage = request.args.get("stage")
    section = request.args.get("section")
    lab = request.args.get("lab")
    subject = request.args.get("subject")
    start = request.args.get("start")
    end = request.args.get("end")
    start_date = datetime.date.fromisoformat(start) if start else datetime.date.today().replace(day=1)
    end_date = datetime.date.fromisoformat(end) if end else datetime.date.today()
    df = get_attendance_report_between_dates(start_date, end_date, None if stage in (None, "الكل") else stage, None if section in (None, "الكل") else section, None if lab in (None, "الكل") else lab, None if subject in (None, "الكل") else subject)
    data = dataframe_to_excel_bytes(df)
    return send_file(BytesIO(data), download_name=f"attendance_{start_date}_to_{end_date}.xlsx", as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@bp.get("/export/pdf")
def export_pdf() -> Response:
    stage = request.args.get("stage")
    section = request.args.get("section")
    lab = request.args.get("lab")
    subject = request.args.get("subject")
    start = request.args.get("start")
    end = request.args.get("end")
    start_date = datetime.date.fromisoformat(start) if start else datetime.date.today().replace(day=1)
    end_date = datetime.date.fromisoformat(end) if end else datetime.date.today()
    df = get_attendance_report_between_dates(start_date, end_date, None if stage in (None, "الكل") else stage, None if section in (None, "الكل") else section, None if lab in (None, "الكل") else lab, None if subject in (None, "الكل") else subject)
    data = dataframe_to_pdf_bytes(df, title=f"تقرير الحضور ({start_date} - {end_date})")
    return send_file(BytesIO(data), download_name=f"attendance_{start_date}_to_{end_date}.pdf", as_attachment=True, mimetype="application/pdf")


@bp.route("/manage", methods=["GET", "POST"]) 
def manage_students() -> str:
    if request.method == "POST":
        action = request.form.get("action")
        if action == "import":
            # Excel import
            if "excel_file" not in request.files:
                flash("لم يتم اختيار ملف.", "danger")
                return redirect(url_for("main.manage_students"))
            f = request.files["excel_file"]
            if f.filename == "":
                flash("لم يتم اختيار ملف.", "danger")
                return redirect(url_for("main.manage_students"))
            if not (f.filename.endswith(".xlsx") or f.filename.endswith(".xls")):
                flash("الملف يجب أن يكون بصيغة Excel (.xlsx أو .xls)", "danger")
                return redirect(url_for("main.manage_students"))
            try:
                df = pd.read_excel(f)
                # Expect columns: الاسم, الرقم الامتحاني, المرحلة, الشعبة (optional), المختبر (optional)
                students_list = []
                for _, row in df.iterrows():
                    students_list.append({
                        "name": str(row.get("الاسم", "")),
                        "exam_number": str(row.get("الرقم الامتحاني", "")),
                        "stage": str(row.get("المرحلة", "")),
                        "section": str(row.get("الشعبة", "")),
                        "lab": str(row.get("المختبر", "")),
                    })
                added, errors = bulk_import_students(students_list)
                flash(f"تم استيراد {added} طالب. {errors} خطأ." if errors else f"تم استيراد {added} طالب بنجاح.", "success" if not errors else "warning")
            except Exception as e:
                flash(f"خطأ في قراءة الملف: {str(e)}", "danger")
            return redirect(url_for("main.manage_students"))
        sid = int(request.form.get("id", "0"))
        if action == "delete":
            delete_student(sid)
            flash("تم حذف الطالب.", "success")
            return redirect(url_for("main.manage_students"))
        elif action == "update":
            name = request.form.get("name", "").strip()
            exam_number = request.form.get("exam_number", "").strip()
            stage = request.form.get("stage", "").strip()
            section = request.form.get("section", "").strip()
            lab = request.form.get("lab", "").strip()
            ok, msg = update_student(sid, name, exam_number, stage, section, lab)
            if ok:
                flash("تم تحديث معلومات الطالب.", "success")
            else:
                flash(msg or "تعذر التحديث.", "danger")
            return redirect(url_for("main.manage_students"))

    # filters
    q_name = request.args.get("name", "").strip()
    q_exam = request.args.get("exam", "").strip()
    q_stage = request.args.get("stage") or None
    q_section = request.args.get("section") or None
    q_lab = request.args.get("lab") or None
    students = get_students_filtered(q_name, q_exam, q_stage, q_section, q_lab)
    stages = get_distinct_stages(defaults=["الأولى", "الثانية", "الثالثة", "الرابعة"]) 
    sections = []
    if q_stage:
        sections = get_sections_for_stage(q_stage)
    return render_template("manage.html", students=students, stages=stages, sections=sections, filters={"name": q_name, "exam": q_exam, "stage": q_stage or "", "section": q_section or "", "lab": q_lab or ""})


