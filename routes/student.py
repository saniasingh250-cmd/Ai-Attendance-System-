import os
import base64
from flask import current_app
from werkzeug.utils import secure_filename
from datetime import date, datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)
student_bp = Blueprint("student", __name__)
from database import get_connection




# ---------------- Student Login Page ----------------

@student_bp.route("/student")
def student_login_page():

    return render_template("student/student_login.html")


# ---------------- Student Login ----------------

@student_bp.route("/student/login", methods=["POST"])
def student_login():

    roll_no = request.form["roll_no"]
    password = request.form["password"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT *
        FROM students
        WHERE roll_no=%s
        AND password=%s
    """, (roll_no, password))

    student = cursor.fetchone()

    cursor.close()
    conn.close()

    if student:

        session["student_id"] = student["id"]
        session["student_name"] = student["name"]

        return redirect(url_for("student.student_dashboard"))
    else:
     flash("Invalid Roll No or Password")
    return redirect(url_for("student.student_login_page"))

    


# ---------------- Student Dashboard ----------------
@student_bp.route("/student/dashboard")
def student_dashboard():

    if "student_id" not in session:
        return redirect(url_for("student.student_login_page"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    # Student Details
    cursor.execute(
        "SELECT * FROM students WHERE id=%s",
        (session["student_id"],)
    )
    student = cursor.fetchone()

    # Today's Attendance Status
    today = date.today()
    today_status = "Not Submitted"

    # Check Approved Attendance
    cursor.execute("""
        SELECT status
        FROM attendance
        WHERE student_id=%s
        AND attendance_date=%s
        LIMIT 1
    """, (session["student_id"], today))

    attendance_row = cursor.fetchone()

    if attendance_row:
        today_status = attendance_row["status"]

    else:
        # Check Attendance Request
        cursor.execute("""
            SELECT status
            FROM attendance_requests
            WHERE student_id=%s
            AND attendance_date=%s
            LIMIT 1
        """, (session["student_id"], today))

        request_row = cursor.fetchone()

        if request_row:
            today_status = request_row["status"]

    # Attendance History
    cursor.execute("""
        SELECT *
        FROM attendance
        WHERE student_id=%s
        ORDER BY attendance_date DESC
    """, (session["student_id"],))

    attendance = cursor.fetchall()

    # Total Attendance
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE student_id=%s
    """, (session["student_id"],))

    total = cursor.fetchone()["total"]

    # Present Count
    cursor.execute("""
        SELECT COUNT(*) AS present
        FROM attendance
        WHERE student_id=%s
        AND status='Present'
    """, (session["student_id"],))

    present = cursor.fetchone()["present"]

    # Percentage
    percent = 0
    if total > 0:
        percent = round((present / total) * 100)

    cursor.close()
    conn.close()

    return render_template(
        "student/student_dashboard.html",
        student=student,
        attendance=attendance,
        total=total,
        present=present,
        percent=percent,
        today_status=today_status
    )


#--------------student mark attendance-----------------
@student_bp.route("/student/mark_attendance")
def attendance_capture_page():

    if "student_id" not in session:
        return redirect(url_for("student.student_login_page"))

    return render_template("student/student_mark_attendance.html")

#---------------- Submit Attendance ----------------
@student_bp.route("/student/submit_attendance", methods=["POST"])
def submit_attendance_request():

    if "student_id" not in session:
        return redirect(url_for("student.student_login_page"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    today = date.today()

    now = datetime.now().time()
    photo = request.form.get("photo")


    filename = None

    if photo:

     image_data = photo.split(",")[1]

    folder = os.path.join("static", "attendance")

    os.makedirs(folder, exist_ok=True)

    filename = f"{session['student_id']}_{int(datetime.now().timestamp())}.jpg"

    filepath = os.path.join(folder, filename)

    with open(filepath, "wb") as f:
        f.write(base64.b64decode(image_data))
    cursor.execute("""

        SELECT *

        FROM attendance_requests

        WHERE student_id=%s

        AND attendance_date=%s

    """,

    (session["student_id"], today))

    already = cursor.fetchone()

    if already:

     if already["status"] == "Rejected":

        cursor.execute("""
        DELETE FROM attendance_requests
        WHERE id=%s
        """, (already["id"],))

        conn.commit()

    else:

        flash("Today's attendance has already been submitted.")

        # Insert New Attendance Request
    cursor.execute("""
        INSERT INTO attendance_requests
        (student_id, attendance_date, attendance_time, status, photo)
        VALUES (%s,%s,%s,%s,%s)
        """,
    (
    session["student_id"],
    today,
    now,
    "Pending",
    filename
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Attendance submitted successfully. Waiting for admin approval.")

    return redirect(url_for("student.student_dashboard"))



#-------------student attendance history----------------
@student_bp.route("/student/attendance_history")
def attendance_history():

    if "student_id" not in session:
        return redirect(url_for("student.student_login_page"))

    conn = get_connection()

    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT attendance_date,
               attendance_time,
               status
        FROM attendance
        WHERE student_id=%s
        ORDER BY attendance_date DESC,
                 attendance_time DESC
    """, (session["student_id"],))

    attendance = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "student/student_attendance_history.html",
        attendance=attendance
    )

#-----------student calendar----------------
@student_bp.route("/student/attendance_calendar")
def attendance_calendar():

    if "student_id" not in session:
        return redirect(url_for("student.student_login_page"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT attendance_date,
               status
        FROM attendance
        WHERE student_id=%s
    """, (session["student_id"],))

    attendance = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "student/attendance_calendar.html",
        attendance=attendance
    )

#----------student edit profile----------------
@student_bp.route("/student/edit_profile")
def edit_profile():

    if "student_id" not in session:
        return redirect(url_for("student.student_login_page"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute(
        "SELECT * FROM students WHERE id=%s",
        (session["student_id"],)
    )

    student = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        "student/edit_profile.html",
        student=student
    )
#--------- student update profile----------------
@student_bp.route("/student/update_profile", methods=["POST"])
def update_student_profile():

    if "student_id" not in session:
        return redirect(url_for("student.student_login_page"))

    student_id = session["student_id"]

    email = request.form["email"]
    phone = request.form["phone"]
    address = request.form["address"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    # Current photo
    cursor.execute(
        "SELECT photo FROM students WHERE id=%s",
        (student_id,)
    )

    student = cursor.fetchone()

    filename = student["photo"]

    photo = request.files.get("photo")

    if photo and photo.filename != "":

        filename = secure_filename(photo.filename)

        upload_folder = os.path.join(
            "static",
            "uploads"
        )

        os.makedirs(upload_folder, exist_ok=True)

        photo.save(
            os.path.join(upload_folder, filename)
        )

    cursor.execute("""
        UPDATE students
        SET
            email=%s,
            phone=%s,
            address=%s,
            photo=%s
        WHERE id=%s
    """,
    (
        email,
        phone,
        address,
        filename,
        student_id
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Profile Updated Successfully")

    return redirect(
        url_for("student.edit_profile")
    )


#-------- student notifications----------------
@student_bp.route("/student/notifications")
def student_notifications():

    if "student_id" not in session:
        return redirect(url_for("student.student_login_page"))

    conn = get_connection()

    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        SELECT *
        FROM notifications
        ORDER BY created_at DESC
    """)

    notifications = cursor.fetchall()

    cursor.close()

    conn.close()

    return render_template(
        "student/notifications.html",
        notifications=notifications
    )


# ---------------- Logout ----------------

@student_bp.route("/student/logout")
def student_logout():

    session.clear()

    flash("Logged Out Successfully")

    return redirect(url_for("student.student_login_page"))
