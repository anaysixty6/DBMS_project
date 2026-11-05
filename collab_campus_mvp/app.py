from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection

app = Flask(__name__)
app.secret_key = "change-this-to-a-long-random-secret"

def login_required(role=None):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please login first.")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("You are not allowed to access that page.")
                return redirect(url_for("dashboard"))
            return function(*args, **kwargs)
        return wrapper
    return decorator

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT skill_id, skill_name FROM skills ORDER BY skill_name")
    skills = cur.fetchall()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        department = request.form.get("department", "").strip()
        year = request.form.get("year", "")
        selected_skills = request.form.getlist("skills")

        if not all([name, email, password, department, year]):
            flash("Please complete all required fields.")
        else:
            cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                flash("This email is already registered.")
            else:
                hashed = generate_password_hash(password)
                cur.execute(
                    """INSERT INTO users
                    (full_name, email, password_hash, role, department, year_of_study)
                    VALUES (%s, %s, %s, 'student', %s, %s)""",
                    (name, email, hashed, department, int(year))
                )
                user_id = cur.lastrowid
                for skill_id in selected_skills:
                    cur.execute(
                        "INSERT INTO student_skills (user_id, skill_id) VALUES (%s, %s)",
                        (user_id, int(skill_id))
                    )
                flash("Registration successful. Please login.")
                cur.close()
                conn.close()
                return redirect(url_for("login"))

    cur.close()
    conn.close()
    return render_template("register.html", skills=skills)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["user_id"]
            session["name"] = user["full_name"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required()
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    uid = session["user_id"]

    if session["role"] == "admin":
        cur.execute("SELECT COUNT(*) AS total FROM users WHERE role='student'")
        students = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM projects")
        projects = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM projects WHERE status='pending'")
        pending = cur.fetchone()["total"]
        cur.execute("SELECT * FROM projects WHERE status='pending' ORDER BY project_id DESC")
        pending_projects = cur.fetchall()
        cur.close()
        conn.close()
        return render_template("admin_dashboard.html", students=students,
                               projects=projects, pending=pending,
                               pending_projects=pending_projects)

    cur.execute("SELECT COUNT(*) AS total FROM team_members WHERE user_id=%s", (uid,))
    team_count = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) AS total FROM tasks WHERE assigned_to=%s AND status <> 'done'", (uid,))
    task_count = cur.fetchone()["total"]
    cur.execute("""
        SELECT p.project_id, p.title, p.description, p.max_team_size,
               COUNT(DISTINCT ps.skill_id) AS total_skills,
               COUNT(DISTINCT ss.skill_id) AS matched_skills
        FROM projects p
        JOIN project_skills ps ON p.project_id = ps.project_id
        LEFT JOIN student_skills ss ON ss.skill_id = ps.skill_id AND ss.user_id = %s
        WHERE p.status='approved'
        GROUP BY p.project_id, p.title, p.description, p.max_team_size
        ORDER BY matched_skills DESC
        LIMIT 4
    """, (uid,))
    recommendations = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("student_dashboard.html", team_count=team_count,
                           task_count=task_count, recommendations=recommendations)

@app.route("/projects")
@login_required("student")
def projects():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    uid = session["user_id"]
    cur.execute("""
        SELECT p.project_id, p.title, p.description, p.max_team_size,
               u.full_name AS pitcher,
               COUNT(DISTINCT ps.skill_id) AS total_skills,
               COUNT(DISTINCT ss.skill_id) AS matched_skills
        FROM projects p
        JOIN users u ON p.pitched_by=u.user_id
        LEFT JOIN project_skills ps ON p.project_id=ps.project_id
        LEFT JOIN student_skills ss ON ss.skill_id=ps.skill_id AND ss.user_id=%s
        WHERE p.status='approved'
        GROUP BY p.project_id, p.title, p.description, p.max_team_size, u.full_name
        ORDER BY p.project_id DESC
    """, (uid,))
    project_list = cur.fetchall()
    cur.execute("SELECT project_id FROM teams")
    existing_teams = {row["project_id"] for row in cur.fetchall()}
    cur.close()
    conn.close()
    for p in project_list:
        total = p["total_skills"] or 0
        p["match_percent"] = round((p["matched_skills"] or 0) * 100 / total) if total else 0
        p["has_team"] = p["project_id"] in existing_teams
    return render_template("projects.html", projects=project_list)

@app.route("/pitch", methods=["GET", "POST"])
@login_required("student")
def pitch():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT skill_id, skill_name FROM skills ORDER BY skill_name")
    skills = cur.fetchall()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        max_size = request.form.get("max_team_size", "4")
        selected = request.form.getlist("skills")
        if not title or not description:
            flash("Please enter a project title and description.")
        else:
            cur.execute("""
                INSERT INTO projects (title, description, pitched_by, status, max_team_size)
                VALUES (%s, %s, %s, 'pending', %s)
            """, (title, description, session["user_id"], int(max_size)))
            project_id = cur.lastrowid
            for sid in selected:
                cur.execute("INSERT INTO project_skills (project_id, skill_id) VALUES (%s, %s)",
                            (project_id, int(sid)))
            cur.execute("SELECT user_id FROM users WHERE role='admin'")
            for admin in cur.fetchall():
                cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
                            (admin["user_id"], "A new project pitch is waiting for approval: " + title))
            flash("Your project pitch has been submitted for admin approval.")
            cur.close()
            conn.close()
            return redirect(url_for("dashboard"))
    cur.close()
    conn.close()
    return render_template("pitch.html", skills=skills)

@app.route("/teams")
@login_required("student")
def teams():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT t.team_id, t.team_name, t.leader_id, p.project_id,
               p.title AS project_title, p.max_team_size,
               COUNT(tm.user_id) AS members
        FROM teams t
        JOIN projects p ON p.project_id=t.project_id
        LEFT JOIN team_members tm ON tm.team_id=t.team_id
        WHERE p.status='approved'
        GROUP BY t.team_id, t.team_name, t.leader_id, p.project_id,
                 p.title, p.max_team_size
        HAVING COUNT(tm.user_id) < p.max_team_size
        ORDER BY t.team_id DESC
    """)
    team_list = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("teams.html", teams=team_list)

@app.route("/join/<int:team_id>", methods=["POST"])
@login_required("student")
def join_team(team_id):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id FROM team_members WHERE team_id=%s AND user_id=%s",
                (team_id, session["user_id"]))
    already_member = cur.fetchone()
    cur.execute("SELECT request_id, status FROM join_requests WHERE team_id=%s AND user_id=%s",
                (team_id, session["user_id"]))
    existing_request = cur.fetchone()

    if already_member:
        flash("You are already a member of this team.")
    elif existing_request and existing_request["status"] == "pending":
        flash("You have already sent a request to this team.")
    else:
        message = request.form.get("message", "").strip()
        try:
            if existing_request:
                cur.execute(
                    "UPDATE join_requests SET status='pending', message=%s WHERE request_id=%s",
                    (message, existing_request["request_id"])
                )
            else:
                cur.execute("""
                    INSERT INTO join_requests (team_id, user_id, message)
                    VALUES (%s, %s, %s)
                """, (team_id, session["user_id"], message))
            cur.execute("SELECT leader_id, team_name FROM teams WHERE team_id=%s", (team_id,))
            team = cur.fetchone()
            if team:
                cur.execute(
                    "INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
                    (team["leader_id"], session["name"] + " requested to join " + team["team_name"])
                )
            flash("Join request sent.")
        except Exception as error:
            flash("Could not send request. The team may be full or unavailable.")
            print(error)

    cur.close()
    conn.close()
    return redirect(url_for("teams"))

@app.route("/team-requests")
@login_required("student")
def team_requests():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT jr.request_id, jr.team_id, jr.message, jr.status,
               u.full_name AS applicant, t.team_name, p.title AS project_title
        FROM join_requests jr
        JOIN teams t ON jr.team_id = t.team_id
        JOIN projects p ON t.project_id = p.project_id
        JOIN users u ON jr.user_id = u.user_id
        WHERE t.leader_id = %s AND jr.status = 'pending'
        ORDER BY jr.request_id DESC
    """, (session["user_id"],))
    requests_list = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("team_requests.html", requests=requests_list)

@app.route("/team-request/<int:request_id>/<action>", methods=["POST"])
@login_required("student")
def update_team_request(request_id, action):
    if action not in ["accepted", "rejected"]:
        flash("Invalid action.")
        return redirect(url_for("team_requests"))

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT jr.request_id, jr.user_id, jr.team_id, t.team_name
        FROM join_requests jr
        JOIN teams t ON jr.team_id = t.team_id
        WHERE jr.request_id = %s AND t.leader_id = %s
          AND jr.status = 'pending'
    """, (request_id, session["user_id"]))
    request_row = cur.fetchone()

    if not request_row:
        flash("You can only manage pending requests for your own teams.")
    else:
        try:
            cur.execute("UPDATE join_requests SET status=%s WHERE request_id=%s",
                        (action, request_id))
            if action == "accepted":
                # The database trigger adds the applicant to team_members.
                message = "Your request to join " + request_row["team_name"] + " was accepted."
            else:
                message = "Your request to join " + request_row["team_name"] + " was rejected."
            cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
                        (request_row["user_id"], message))
            flash("Join request " + action + ".")
        except Exception as error:
            flash("Could not process request. Check team capacity and membership rules.")
            print(error)

    cur.close()
    conn.close()
    return redirect(url_for("team_requests"))


@app.route("/task/<int:task_id>/status", methods=["POST"])
@login_required("student")
def update_task_status(task_id):
    new_status = request.form.get("status")
    if new_status not in ["todo", "in_progress", "done"]:
        flash("Invalid task status.")
        return redirect(url_for("my_tasks"))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        UPDATE tasks
        SET status=%s
        WHERE task_id=%s AND assigned_to=%s
    """, (new_status, task_id, session["user_id"]))
    if cur.rowcount:
        flash("Task status updated.")
    else:
        flash("Task not found or not assigned to you.")
    cur.close()
    conn.close()
    return redirect(url_for("my_tasks"))

@app.route("/my-tasks")
@login_required("student")
def my_tasks():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT t.task_id, t.title, t.description, t.due_date, t.status, p.title AS project_title
        FROM tasks t JOIN projects p ON p.project_id=t.project_id
        WHERE t.assigned_to=%s ORDER BY t.due_date
    """, (session["user_id"],))
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("tasks.html", tasks=tasks)

@app.route("/admin/projects")
@login_required("admin")
def admin_projects():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT p.project_id, p.title, p.description, p.status,
               p.max_team_size, u.full_name AS pitcher
        FROM projects p JOIN users u ON p.pitched_by=u.user_id
        ORDER BY p.project_id DESC
    """)
    project_list = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin_projects.html", projects=project_list)

@app.route("/admin/project/<int:project_id>/<action>", methods=["POST"])
@login_required("admin")
def update_project(project_id, action):
    if action not in ["approved", "rejected"]:
        flash("Invalid action.")
        return redirect(url_for("admin_projects"))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("UPDATE projects SET status=%s WHERE project_id=%s",
                (action, project_id))
    cur.execute("SELECT pitched_by, title FROM projects WHERE project_id=%s", (project_id,))
    project_info = cur.fetchone()
    if project_info:
        cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
                    (project_info["pitched_by"], "Your project '" + project_info["title"] + "' was " + action + "."))
    if action == "approved":
        cur.execute("SELECT team_id FROM teams WHERE project_id=%s", (project_id,))
        if not cur.fetchone():
            cur.execute("SELECT title, pitched_by FROM projects WHERE project_id=%s",
                        (project_id,))
            project = cur.fetchone()
            if project:
                cur.execute("""
                    INSERT INTO teams (team_name, project_id, leader_id)
                    VALUES (%s, %s, %s)
                """, (project["title"] + " Team", project_id, project["pitched_by"]))
                # Database trigger adds the leader to team_members.
    flash("Project status updated.")
    cur.close()
    conn.close()
    return redirect(url_for("admin_projects"))

@app.route("/admin/events", methods=["GET", "POST"])
@login_required("admin")
def admin_events():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        cur.execute("""
            INSERT INTO events (title, description, start_date, end_date)
            VALUES (%s, %s, %s, %s)
        """, (request.form["title"], request.form.get("description", ""),
              request.form.get("start_date") or None,
              request.form.get("end_date") or None))
        flash("Event added.")
    cur.execute("SELECT * FROM events ORDER BY event_id DESC")
    events = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin_events.html", events=events)


@app.route("/my-teams")
@login_required("student")
def my_teams():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT t.team_id, t.team_name, t.leader_id, p.project_id,
               p.title AS project_title, u.full_name AS leader_name
        FROM team_members tm
        JOIN teams t ON tm.team_id=t.team_id
        JOIN projects p ON t.project_id=p.project_id
        JOIN users u ON t.leader_id=u.user_id
        WHERE tm.user_id=%s
        ORDER BY t.team_id DESC
    """, (session["user_id"],))
    team_list = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("my_teams.html", teams=team_list)

@app.route("/project-updates", methods=["GET", "POST"])
@login_required("student")
def project_updates():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        project_id = request.form.get("project_id")
        content = request.form.get("content", "").strip()
        cur.execute("""
            SELECT tm.user_id
            FROM team_members tm
            JOIN teams t ON tm.team_id=t.team_id
            WHERE t.project_id=%s AND tm.user_id=%s
        """, (project_id, session["user_id"]))
        is_member = cur.fetchone()
        if is_member and content:
            cur.execute("INSERT INTO project_updates (project_id, posted_by, content) VALUES (%s, %s, %s)",
                        (project_id, session["user_id"], content))
            cur.execute("""
                SELECT tm.user_id
                FROM team_members tm JOIN teams t ON tm.team_id=t.team_id
                WHERE t.project_id=%s AND tm.user_id<>%s
            """, (project_id, session["user_id"]))
            for member in cur.fetchall():
                cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
                            (member["user_id"], "A new update was posted to your project."))
            flash("Project update posted.")
        else:
            flash("Only project team members can post updates.")
    cur.execute("""
        SELECT p.project_id, p.title
        FROM projects p JOIN teams t ON p.project_id=t.project_id
        JOIN team_members tm ON tm.team_id=t.team_id
        WHERE tm.user_id=%s
    """, (session["user_id"],))
    my_projects = cur.fetchall()
    cur.execute("""
        SELECT pu.content, pu.project_id, p.title AS project_title,
               u.full_name AS posted_by
        FROM project_updates pu
        JOIN projects p ON pu.project_id=p.project_id
        JOIN users u ON pu.posted_by=u.user_id
        JOIN teams t ON t.project_id=p.project_id
        JOIN team_members tm ON tm.team_id=t.team_id
        WHERE tm.user_id=%s
        ORDER BY pu.update_id DESC
    """, (session["user_id"],))
    updates = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("project_updates.html", projects=my_projects, updates=updates)

@app.route("/notifications")
@login_required()
def notifications():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM notifications WHERE user_id=%s ORDER BY notification_id DESC",
                (session["user_id"],))
    notification_list = cur.fetchall()
    cur.execute("UPDATE notifications SET is_read=TRUE WHERE user_id=%s",
                (session["user_id"],))
    cur.close()
    conn.close()
    return render_template("notifications.html", notifications=notification_list)

@app.route("/admin/students")
@login_required("admin")
def admin_students():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT user_id, full_name, email, department, year_of_study
        FROM users WHERE role='student' ORDER BY full_name
    """)
    students = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin_students.html", students=students)


@app.route("/admin/skills", methods=["GET", "POST"])
@login_required("admin")
def admin_skills():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    if request.method == "POST":
        skill_name = request.form.get("skill_name", "").strip()
        if skill_name:
            try:
                cur.execute("INSERT INTO skills (skill_name) VALUES (%s)", (skill_name,))
                flash("Skill added.")
            except Exception:
                flash("This skill may already exist.")
    cur.execute("SELECT * FROM skills ORDER BY skill_name")
    skills_list = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin_skills.html", skills=skills_list)

@app.route("/admin/teams")
@login_required("admin")
def admin_teams():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT t.team_id, t.team_name, p.title AS project_title,
               u.full_name AS leader_name, COUNT(tm.user_id) AS member_count,
               p.max_team_size
        FROM teams t
        JOIN projects p ON t.project_id=p.project_id
        JOIN users u ON t.leader_id=u.user_id
        LEFT JOIN team_members tm ON t.team_id=tm.team_id
        GROUP BY t.team_id, t.team_name, p.title, u.full_name, p.max_team_size
        ORDER BY t.team_id DESC
    """)
    teams_list = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("admin_teams.html", teams=teams_list)

if __name__ == "__main__":
    app.run(debug=True)
