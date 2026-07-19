import base64
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app
)
print("ADMIN.PY LOADED")
admin_bp = Blueprint("admin", __name__)
from database import get_connection
from capture_face import capture_faces

from werkzeug.utils import secure_filename
import os



#---------------- Login Page ----------------
@admin_bp.route("/admin")
def login():

    return render_template("admin/login.html")


#---------------- Login ----------------#
@admin_bp.route("/login", methods=["POST"])
def check_login():

    username=request.form["username"]
    password=request.form["password"]

    print("Username:", username)
    print("Password:", password)

    conn=get_connection()

    cursor=conn.cursor(dictionary=True, buffered=True)

    cursor.execute(

        "SELECT * FROM admin WHERE username=%s AND password=%s",

        (username,password)

    )

    admin=cursor.fetchone()

    cursor.close()

    conn.close()

    if admin:

        session["admin"]=admin["username"]

        return redirect(url_for("admin.dashboard"))

    flash("Invalid Username or Password")

    return redirect(url_for("admin.login"))


#------------Dashboard -------------
@admin_bp.route("/dashboard")
def dashboard():

    if "admin" not in session:
        return redirect("/")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(DISTINCT department) AS total FROM students")
    departments = cursor.fetchone()["total"]

    cursor.execute("SELECT * FROM students ORDER BY id DESC LIMIT 10")
    students = cursor.fetchall()
    

    cursor.close()
    conn.close()

    return render_template("admin/dashboard.html",
    total_students=total_students,
    present_today=0,
    departments=departments,
    total_attendance=0,
    students=students
 )

#-----notifications ----
@admin_bp.route("/notifications")
def admin_notifications():

    if "admin" not in session:
        return redirect("/")

    return render_template("admin/notifications.html")

#------ send notification ----  
@admin_bp.route("/send_notification", methods=["POST"])
def send_notification():

    if "admin" not in session:
        return redirect(url_for("admin.login"))

    title = request.form["title"]
    message = request.form["message"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO notifications(title, message)
        VALUES(%s, %s)
    """, (title, message))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Notification Sent Successfully!")

    return redirect(url_for("admin.admin_notifications"))



#---------------- Logout ----------------#
@admin_bp.route("/logout")
def logout():
    session.clear()

    flash("Logged Out Successfully")

    return redirect("/")



# ------------Add Student--------------
@admin_bp.route("/add_student", methods=["GET","POST"])
def add_student():

    if "admin" not in session:
        return redirect("/")

    return render_template("admin/add_student.html")





#-------------------- save student ----------------#
@admin_bp.route("/save_student", methods=["POST"])
def save_student():

    if "admin" not in session:
        return redirect("/")

    name = request.form["name"]
    department = request.form["department"]
    course=request.form["course"]
    semester = request.form["semester"]
    email = request.form["email"]
    phone = request.form["phone"]

    prefixes = {
    "Engineering":"ENG",
    "Science":"SCI",
    "Arts":"ART",
    "Commerce":"COM",
    "Management":"MGT",
    "Education":"EDU",
    "Law":"LAW"
    }

    prefix = prefixes.get(department,"STD")

    conn = get_connection()

    cursor = conn.cursor(dictionary=True, buffered=True)

    year=datetime.now().year

    cursor.execute("""
    SELECT COUNT(*) total
    FROM students
    WHERE department=%s
    """,(department,))

    count = cursor.fetchone()["total"]+1

    roll=f"{prefix}{year}{count:03d}"
    

    # Default password for every new student
    default_password = "123456"

    photo = request.files["photo"]

    filename = ""

    if photo and photo.filename != "":

        filename = secure_filename(photo.filename)

        os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)

        save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)

        photo.save(save_path)



    cursor.execute("""
        INSERT INTO students
        (
        roll_no,
        name,
        department,
        course,
        semester,
        email,
        phone,
        photo,
        password
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """,
    (
        roll,
        name,
        department,
        course,
        semester,
        email,
        phone,
        filename,
        default_password
    ))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Student Added Successfully!")

    return redirect(url_for("admin.view_students"))

    




# --------------View Students-------------
@admin_bp.route("/students")
def view_students():

    if "admin" not in session:
        return redirect("/")

    conn = get_connection()

    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM students ORDER BY id DESC")

    students = cursor.fetchall()

    cursor.close()

    conn.close()

    return render_template(
    "admin/students.html",
    students=students
    )

#----------- admin attendance request ----------------
@admin_bp.route("/attendance_requests")
def pending_attendance():

    if "admin" not in session:
        return redirect(url_for("admin.login"))

    conn = get_connection()

    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""

        SELECT

            attendance_requests.*,

            students.name,

            students.roll_no

        FROM attendance_requests

        JOIN students

        ON attendance_requests.student_id = students.id

        WHERE status='Pending'

        ORDER BY attendance_date DESC

    """)

    requests = cursor.fetchall()

    cursor.close()

    conn.close()

    return render_template(

        "admin/attendance_requests.html",

        requests=requests

    )


# ---------------- Approve Attendance ----------------
@admin_bp.route("/approve_attendance/<int:id>")
def approve_attendance(id):

    if "admin" not in session:
        return redirect(url_for("admin.login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    # Get request details
    cursor.execute("""
        SELECT *
        FROM attendance_requests
        WHERE id=%s
    """, (id,))

    request_data = cursor.fetchone()

    if request_data:

        # Insert into attendance table
       cursor.execute("""
        INSERT INTO attendance
     (
        student_id,
        attendance_date,
        attendance_time,
        status
    )
     VALUES (%s, %s, %s, %s)
     """, (
    request_data["student_id"],
    request_data["attendance_date"],
    request_data["attendance_time"],
    "Present"
     ))

        # Update request status
    cursor.execute("""
            UPDATE attendance_requests
            SET status='Approved'
            WHERE id=%s
        """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Attendance Approved Successfully!")

    return redirect(url_for("admin.pending_attendance"))


# ---------------- Reject Attendance ----------------
@admin_bp.route("/reject_attendance/<int:id>")
def reject_attendance(id):

    if "admin" not in session:
        return redirect(url_for("admin.login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("""
        UPDATE attendance_requests
        SET status='Rejected'
        WHERE id=%s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Attendance Rejected!")

    return redirect(url_for("admin.pending_attendance"))


#------------- Edit Student ------------------
@admin_bp.route("/edit_student/<int:id>", methods=["GET", "POST"])
def edit_student(id):

    if "admin" not in session:
        return redirect(url_for("admin.login"))

    conn = get_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    # ---------------- Update Student ----------------
    if request.method == "POST":

        roll_no = request.form["roll_no"]
        name = request.form["name"]
        department = request.form["department"]
        semester = request.form["semester"]
        email = request.form["email"]
        phone = request.form["phone"]

        photo = request.files.get("photo")

        # ---------------- If New Photo Uploaded ----------------
        if photo and photo.filename != "":

            filename = secure_filename(photo.filename)

            os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)

            photo.save(
                os.path.join(
                    current_app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

            sql = """
            UPDATE students
            SET
                roll_no=%s,
                name=%s,
                department=%s,
                semester=%s,
                email=%s,
                phone=%s,
                photo=%s
            WHERE id=%s
            """

            values = (
                roll_no,
                name,
                department,
                semester,
                email,
                phone,
                filename,
                id
            )

        # ---------------- Without New Photo ----------------
        else:

            sql = """
            UPDATE students
            SET
                roll_no=%s,
                name=%s,
                department=%s,
                semester=%s,
                email=%s,
                phone=%s
            WHERE id=%s
            """

            values = (
                roll_no,
                name,
                department,
                semester,
                email,
                phone,
                id
            )

        cursor.execute(sql, values)
        conn.commit()

        cursor.close()
        conn.close()

        flash("Student Updated Successfully!")

        return redirect(url_for("admin.view_students"))

    # ---------------- Load Student Data ----------------
    cursor.execute(
        "SELECT * FROM students WHERE id=%s",
        (id,)
    )

    student = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("admin/edit_student.html",student=student)

    
#------------- delete student -------------------
@admin_bp.route("/delete_student/<int:id>", methods=["POST"])
def delete_student(id):

    if "admin" not in session:
        return redirect(url_for("admin.login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM students WHERE id=%s",
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    flash("Student Deleted Successfully!")

    return redirect(url_for("admin.view_students"))



# --------------Capture Face-----------
@admin_bp.route("/capture")
def capture():

    if "admin" not in session:
        return redirect(url_for("admin.login"))

    conn = get_connection()

    cursor = conn.cursor(dictionary=True, buffered=True)

    cursor.execute("SELECT roll_no,name FROM students")

    students = cursor.fetchall()

    cursor.close()

    conn.close()

    return render_template("admin/capture.html",students=students)



#---------------- capture face--------------
@admin_bp.route("/capture_face", methods=["POST"])
def capture_student():

    if "admin" not in session:
        return redirect(url_for("admin.login"))

    roll_no = request.form["roll_no"]

    capture_faces(roll_no)

    flash("Face Dataset Captured Successfully!")

    return redirect(url_for("admin/capture"))



# -------------Reports-------------
@admin_bp.route("/reports")
def reports():

    if "admin" not in session:
        return redirect(url_for("admin.login"))

    return render_template("admin/reports.html")


#----------------- Reset Student Password ----------------
@admin_bp.route("/reset_student_password/<int:id>")
def reset_student_password(id):

    if "admin" not in session:
        return redirect(url_for("admin.login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE students
        SET password=%s
        WHERE id=%s
    """, ("123456", id))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Student password reset successfully!")

    return redirect(url_for("admin.view_students"))

#---------------- Forgot Password ----------------#
@admin_bp.route("/forgot")
def forgot():

    return render_template("admin/forgot_password.html")

    

#---------------- Reset Password ----------------#
@admin_bp.route("/reset", methods=["POST"])
def reset():

    username = request.form["username"]
    question = request.form["question"]
    answer = request.form["answer"]
    newpassword = request.form["newpassword"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE admin
        SET password=%s
        WHERE username=%s
        AND security_question=%s
        AND security_answer=%s
    """, (
        newpassword,
        username,
        question,
        answer
    ))

    rows = cursor.rowcount

    conn.commit()

    cursor.close()
    conn.close()

    if rows > 0:
        flash("Password Changed Successfully!")
    else:
        flash("Invalid Username, Security Question or Answer!")

    return redirect(url_for("admin.login"))