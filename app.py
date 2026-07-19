from flask import Flask, render_template
from routes.admin import admin_bp
from routes.student import student_bp
import os
 
print("APP.PY STARTED")

app = Flask(__name__)

app.secret_key = "attendance_secret"

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Register Blueprints
app.register_blueprint(admin_bp, url_prefix="/admin")
app.register_blueprint(student_bp, url_prefix="/student")


# Home Page
@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)