from flask import Flask, render_template, request, redirect, session
import mysql.connector
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret-key")

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "student_db")
    )

def create_tables():
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                email VARCHAR(150) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                age INT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) UNIQUE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                teacher_id INT,
                FOREIGN KEY (teacher_id) REFERENCES teachers (id) ON DELETE SET NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                course_id INT NOT NULL,
                enrollment_date DATE DEFAULT (CURRENT_DATE),
                FOREIGN KEY (student_id) REFERENCES students (id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
            )
        """)
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print("Database connection/table error:", e)

@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        if len(password) < 6:
            return render_template("register.html", error="Password must contain at least 6 characters.")
        hashed_password = generate_password_hash(password)
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, hashed_password))
            db.commit()
        except mysql.connector.Error:
            cursor.close()
            db.close()
            return render_template("register.html", error="Username or email already exists.")
        cursor.close()
        db.close()
        return redirect("/login")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()
        if user and check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            return redirect("/dashboard")
        return render_template("login.html", error="Invalid email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM students")
    student_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM teachers")
    teacher_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM courses")
    course_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM enrollments")
    enrollment_count = cursor.fetchone()[0]
    cursor.close()
    db.close()
    return render_template("dashboard.html", username=session["username"], student_count=student_count, teacher_count=teacher_count, course_count=course_count, enrollment_count=enrollment_count)

@app.route("/students")
def students():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM students ORDER BY id DESC")
    students = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("students.html", students=students)

@app.route("/students/add", methods=["GET", "POST"])
def add_student():
    if "user_id" not in session:
        return redirect("/login")
    if request.method == "POST":
        name = request.form["name"].strip()
        age = request.form["age"]
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO students (name, age) VALUES (%s, %s)", (name, age))
        db.commit()
        cursor.close()
        db.close()
        return redirect("/students")
    return render_template("add_student.html")

@app.route("/students/edit/<int:id>", methods=["GET", "POST"])
def edit_student(id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    cursor = db.cursor()
    if request.method == "POST":
        name = request.form["name"].strip()
        age = request.form["age"]
        cursor.execute("UPDATE students SET name = %s, age = %s WHERE id = %s", (name, age, id))
        db.commit()
        cursor.close()
        db.close()
        return redirect("/students")
    cursor.execute("SELECT * FROM students WHERE id = %s", (id,))
    student = cursor.fetchone()
    cursor.close()
    db.close()
    return render_template("edit_student.html", student=student)

@app.route("/students/delete/<int:id>", methods=["POST"])
def delete_student(id):
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM students WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    db.close()
    return redirect("/students")

@app.route("/students/search")
def search_students():
    if "user_id" not in session:
        return redirect("/login")
    keyword = request.args.get("keyword", "").strip()
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM students WHERE name LIKE %s ORDER BY id DESC", ("%" + keyword + "%",))
    students = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("students.html", students=students, keyword=keyword)

@app.route("/teachers", methods=["GET", "POST"])
def teachers():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    cursor = db.cursor()
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        cursor.execute("INSERT INTO teachers (name, email) VALUES (%s, %s)", (name, email))
        db.commit()
    cursor.execute("SELECT * FROM teachers ORDER BY id DESC")
    teachers = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("teachers.html", teachers=teachers)

@app.route("/courses", methods=["GET", "POST"])
def courses():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    cursor = db.cursor()
    if request.method == "POST":
        name = request.form["name"]
        teacher_id = request.form["teacher_id"]
        cursor.execute("INSERT INTO courses (name, teacher_id) VALUES (%s, %s)", (name, teacher_id))
        db.commit()
    cursor.execute("""
        SELECT courses.id, courses.name, teachers.name
        FROM courses LEFT JOIN teachers ON courses.teacher_id = teachers.id
        ORDER BY courses.id DESC
    """)
    courses = cursor.fetchall()
    cursor.execute("SELECT id, name FROM teachers ORDER BY name")
    teachers = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("courses.html", courses=courses, teachers=teachers)

@app.route("/enrollments", methods=["GET", "POST"])
def enrollments():
    if "user_id" not in session:
        return redirect("/login")
    db = get_db()
    cursor = db.cursor()
    if request.method == "POST":
        student_id = request.form["student_id"]
        course_id = request.form["course_id"]
        cursor.execute("INSERT INTO enrollments (student_id, course_id) VALUES (%s, %s)", (student_id, course_id))
        db.commit()
    cursor.execute("""
        SELECT enrollments.id, students.name, courses.name, enrollments.enrollment_date
        FROM enrollments
        INNER JOIN students ON enrollments.student_id = students.id
        INNER JOIN courses ON enrollments.course_id = courses.id
        ORDER BY enrollments.id DESC
    """)
    enrollments = cursor.fetchall()
    cursor.execute("SELECT id, name FROM students ORDER BY name")
    students = cursor.fetchall()
    cursor.execute("SELECT id, name FROM courses ORDER BY name")
    courses = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("enrollments.html", enrollments=enrollments, students=students, courses=courses)

if __name__ == "__main__":
    create_tables()
    app.run(host="0.0.0.0", port=5000, debug=True)