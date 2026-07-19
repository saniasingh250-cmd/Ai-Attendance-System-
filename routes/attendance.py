from flask import Blueprint, render_template

attendance_bp = Blueprint(
    "attendance",
    __name__
)

# --------------Take Attendance------------
@attendance_bp.route("/")
def take_attendance():
    return render_template("attendance.html")