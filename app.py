import os
import mysql.connector
from flask import Flask, render_template_string, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "student_collab_secret_key"  # Required for session management

def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "mysql-121b7093-anay-35b4.c.aivencloud.com"),
        port=int(os.environ.get("DB_PORT", 21628)),
        user=os.environ.get("DB_USER", "avnadmin"),
        password=os.environ.get("DB_PASSWORD", "YOUR_AIVEN_PASSWORD_HERE"),
        database=os.environ.get("DB_NAME", "student_collab_db")
    )

# =====================================================================
# 1. LOGIN ROUTE & AUTHENTICATION
# =====================================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        # Check user in the Users table
        cursor.execute("SELECT * FROM Users WHERE email = %s;", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session["user_id"] = user["user_id"]
            session["full_name"] = user["full_name"]
            session["role"] = user["role"]  # 'Student', 'Mentor', or 'Admin'[cite: 1, 4]

            # Route based on role
            if user["role"] == "Admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("student_dashboard"))
        else:
            error = "Invalid email address. Try admin@college.edu or aarav@college.edu"

    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =====================================================================
# 2. STUDENT DASHBOARD (The 5-Section Platform)
# =====================================================================
@app.route("/student/dashboard", methods=["GET"])
def student_dashboard():
    if "user_id" not in session or session.get("role") != "Student":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT skill_id, skill_name, category FROM Skills ORDER BY skill_name;")
    all_skills = cursor.fetchall()

    cursor.execute("""
        SELECT u.user_id, u.full_name, u.email, u.department, u.graduation_year,
               GROUP_CONCAT(CONCAT(s.skill_name, ' (', us.proficiency, ')') SEPARATOR ', ') AS skills_list
        FROM Users u
        LEFT JOIN User_Skills us ON u.user_id = us.user_id
        LEFT JOIN Skills s ON us.skill_id = s.skill_id
        WHERE u.role = 'Student'
        GROUP BY u.user_id
        ORDER BY u.user_id DESC;
    """)
    students = cursor.fetchall()

    cursor.execute("SELECT * FROM Open_Projects_View ORDER BY project_id DESC;")
    open_projects = cursor.fetchall()

    selected_student_id = request.args.get("student_id", default=session["user_id"], type=int)
    cursor.execute("""
        SELECT p.project_id, p.title AS project_title, p.description, s.skill_name, us.proficiency
        FROM Projects p
        JOIN Project_Skills ps ON p.project_id = ps.project_id
        JOIN Skills s ON ps.skill_id = s.skill_id
        JOIN User_Skills us ON s.skill_id = us.skill_id
        WHERE us.user_id = %s AND p.status = 'Open';
    """, (selected_student_id,))
    matched_projects = cursor.fetchall()

    cursor.execute("SELECT project_id, title, status, max_team_size FROM Projects ORDER BY project_id DESC;")
    all_projects = cursor.fetchall()

    cursor.execute("""
        SELECT p.project_id, p.title AS project_title, u.full_name, tm.role_in_team, tm.join_status
        FROM Team_Members tm
        JOIN Projects p ON tm.project_id = p.project_id
        JOIN Users u ON tm.user_id = u.user_id
        ORDER BY p.project_id DESC;
    """)
    team_members = cursor.fetchall()

    selected_proj_id = request.args.get("project_id", default=2, type=int)
    cursor.execute("""
        SELECT t.task_id, t.task_title, u.full_name AS assigned_student, t.deadline, t.task_status
        FROM Tasks t
        LEFT JOIN Users u ON t.assigned_to = u.user_id
        WHERE t.project_id = %s
        ORDER BY t.task_id DESC;
    """, (selected_proj_id,))
    tasks = cursor.fetchall()

    cursor.execute("SELECT user_id, full_name, email, department FROM Users WHERE role = 'Mentor';")
    mentors = cursor.fetchall()

    cursor.execute("""
        SELECT mr.request_id, p.title AS project_name, u.full_name AS mentor_name, 
               u.department, mr.pitch_message, mr.request_status
        FROM Mentor_Requests mr
        JOIN Projects p ON mr.project_id = p.project_id
        JOIN Users u ON mr.mentor_id = u.user_id
        ORDER BY mr.request_id DESC;
    """)
    mentor_requests = cursor.fetchall()

    cursor.execute("""
        SELECT ps.showcase_id, p.title, p.description, u.full_name AS lead_name, 
               ps.github_repo_url, ps.live_demo_url, ps.upvotes
        FROM Project_Showcase ps
        JOIN Projects p ON ps.project_id = p.project_id
        JOIN Users u ON p.creator_id = u.user_id
        WHERE ps.is_approved = TRUE
        ORDER BY ps.upvotes DESC;
    """)
    showcase = cursor.fetchall()

    cursor.execute("SELECT status, COUNT(*) AS count FROM Projects GROUP BY status;")
    admin_stats = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template_string(
        STUDENT_TEMPLATE,
        all_skills=all_skills,
        students=students,
        open_projects=open_projects,
        selected_student_id=selected_student_id,
        matched_projects=matched_projects,
        all_projects=all_projects,
        team_members=team_members,
        tasks=tasks,
        selected_proj_id=selected_proj_id,
        mentors=mentors,
        mentor_requests=mentor_requests,
        showcase=showcase,
        admin_stats=admin_stats
    )


# =====================================================================
# 3. ADMIN DASHBOARD (Separate Admin Access Control)
# =====================================================================
@app.route("/admin/dashboard", methods=["GET"])
def admin_dashboard():
    if "user_id" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Admin Analytics View metrics[cite: 1, 4]
    cursor.execute("SELECT * FROM Admin_Dashboard_Stats;")
    stats = cursor.fetchone()

    # Unapproved Showcase submissions awaiting Admin approval[cite: 1, 4]
    cursor.execute("""
        SELECT ps.showcase_id, p.title, p.description, u.full_name AS lead_name, 
               ps.github_repo_url, ps.is_approved
        FROM Project_Showcase ps
        JOIN Projects p ON ps.project_id = p.project_id
        JOIN Users u ON p.creator_id = u.user_id;
    """)
    all_showcases = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template_string(ADMIN_TEMPLATE, stats=stats, showcases=all_showcases)

@app.route("/admin/approve_showcase/<int:showcase_id>", methods=["POST"])
def approve_showcase(showcase_id):
    if session.get("role") != "Admin":
        return redirect(url_for("login"))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Project_Showcase SET is_approved = TRUE, approved_by_admin = %s WHERE showcase_id = %s;", (session["user_id"], showcase_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("admin_dashboard"))


# =====================================================================
# STUDENT ACTION ROUTES
# =====================================================================
@app.route("/register_student", methods=["POST"])
def register_student():
    full_name = request.form["full_name"]
    email = request.form["email"]
    department = request.form["department"]
    grad_year = request.form["grad_year"]
    proficiency = request.form.get("proficiency", "Intermediate")
    selected_skills = request.form.getlist("skill_ids")

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Users (full_name, email, password_hash, role, department, graduation_year)
            VALUES (%s, %s, 'hash_pass', 'Student', %s, %s);
        """, (full_name, email, department, grad_year))
        new_user_id = cursor.lastrowid

        for skill_id in selected_skills:
            cursor.execute("""
                INSERT INTO User_Skills (user_id, skill_id, proficiency)
                VALUES (%s, %s, %s);
            """, (new_user_id, skill_id, proficiency))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("student_dashboard") + "#register-section")

@app.route("/add_skill", methods=["POST"])
def add_skill():
    skill_name = request.form["skill_name"]
    category = request.form["category"]
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT IGNORE INTO Skills (skill_name, category) VALUES (%s, %s);", (skill_name, category))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("student_dashboard") + "#register-section")

@app.route("/create_project", methods=["POST"])
def create_project():
    creator_id = request.form["creator_id"]
    title = request.form["title"]
    description = request.form["description"]
    max_size = request.form["max_size"]
    req_skills = request.form.getlist("req_skill_ids")

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Projects (creator_id, title, description, max_team_size, status)
            VALUES (%s, %s, %s, %s, 'Open');
        """, (creator_id, title, description, max_size))
        new_proj_id = cursor.lastrowid

        cursor.execute("""
            INSERT IGNORE INTO Team_Members (project_id, user_id, role_in_team, join_status)
            VALUES (%s, %s, 'Project Lead', 'Accepted');
        """, (new_proj_id, creator_id))

        for sid in req_skills:
            cursor.execute("""
                INSERT IGNORE INTO Project_Skills (project_id, skill_id, is_mandatory)
                VALUES (%s, %s, TRUE);
            """, (new_proj_id, sid))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("student_dashboard") + "#projects-section")

@app.route("/join_team", methods=["POST"])
def join_team():
    project_id = request.form["project_id"]
    user_id = request.form["user_id"]
    role_in_team = request.form["role_in_team"]

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT IGNORE INTO Team_Members (project_id, user_id, role_in_team, join_status)
            VALUES (%s, %s, %s, 'Accepted');
        """, (project_id, user_id, role_in_team))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("student_dashboard") + "#teams-section")

@app.route("/add_task", methods=["POST"])
def add_task():
    proj_id = request.form["project_id"]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Tasks (project_id, assigned_to, task_title, deadline, task_status)
        VALUES (%s, %s, %s, %s, 'To_Do');
    """, (proj_id, request.form["assigned_to"], request.form["task_title"], request.form["deadline"]))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("student_dashboard", project_id=proj_id) + "#teams-section")

@app.route("/update_task_status/<int:task_id>/<string:new_status>/<int:proj_id>")
def update_task_status(task_id, new_status, proj_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Tasks SET task_status = %s WHERE task_id = %s;", (new_status, task_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("student_dashboard", project_id=proj_id) + "#teams-section")

@app.route("/request_mentor", methods=["POST"])
def request_mentor():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Mentor_Requests (project_id, mentor_id, pitch_message)
        VALUES (%s, %s, %s);
    """, (request.form["project_id"], request.form["mentor_id"], request.form["pitch"]))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("student_dashboard") + "#mentors-section")

@app.route("/upvote/<int:showcase_id>")
def upvote(showcase_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Project_Showcase SET upvotes = upvotes + 1 WHERE showcase_id = %s;", (showcase_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("student_dashboard") + "#showcase-section")

@app.route("/")
def index():
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
