from flask import Flask, render_template, request, redirect, url_for
import os
import mysql.connector

def get_db():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        port=int(os.environ.get("DB_PORT", 4000)),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),  # <-- Must be os.environ.get, not a real password string
        database=os.environ.get("DB_NAME")
    )
import mysql.connector

app = Flask(__name__)

def get_db():
    return mysql.connector.connect(
        host=os.environ.get("mysql-121b7093-anay-35b4.c.aivencloud.com"),       # e.g., "mysql-xyz.aivencloud.com"
        port=int(os.environ.get("21628")),         # e.g., 18234 (keep as integer, no quotes)
        user=os.environ.get("avnadmin"),
        password=os.environ.get("AVNS_zsQqCZsuSRG6gjXmuOA"),
        database=os.environ.get("student_collab_db")          # or whatever you named your database
    )

@app.route("/", methods=["GET"])
def dashboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    active_tab = request.args.get("tab", default="market")

    # 1A: Project Market (SQL View)
    cursor.execute("SELECT * FROM Open_Projects_View;")
    open_projects = cursor.fetchall()

    # 1B: Skill Matching (4-Table JOIN)
    cursor.execute("SELECT user_id, full_name, department FROM Users WHERE role = 'Student';")
    students = cursor.fetchall()
    selected_student_id = request.args.get("student_id", default=4, type=int)
    
    cursor.execute("""
        SELECT p.project_id, p.title AS project_title, s.skill_name, us.proficiency
        FROM Projects p
        JOIN Project_Skills ps ON p.project_id = ps.project_id
        JOIN Skills s ON ps.skill_id = s.skill_id
        JOIN User_Skills us ON s.skill_id = us.skill_id
        WHERE us.user_id = %s AND p.status = 'Open';
    """, (selected_student_id,))
    matched_projects = cursor.fetchall()

    # 2A: Team Builder
    cursor.execute("""
        SELECT p.project_id, p.title AS project_title, u.full_name, tm.role_in_team, tm.join_status
        FROM Team_Members tm
        JOIN Projects p ON tm.project_id = p.project_id
        JOIN Users u ON tm.user_id = u.user_id
        ORDER BY p.project_id DESC;
    """)
    team_members = cursor.fetchall()

    # All projects for dropdowns
    cursor.execute("SELECT project_id, title, status FROM Projects;")
    all_projects = cursor.fetchall()

    # 2B: Task Manager (Stored Procedure)
    selected_proj_id = request.args.get("project_id", default=2, type=int)
    cursor.callproc("Get_Project_Tasks", [selected_proj_id])
    tasks = []
    for result in cursor.stored_results():
        tasks = result.fetchall()

    # 3: Mentor Hub & Mentor Request
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

    # 4A: Project Showcase
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

    # 4B: Admin Dashboard (GROUP BY Analytics)
    cursor.execute("SELECT status, COUNT(*) AS count FROM Projects GROUP BY status;")
    admin_stats = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        active_tab=active_tab,
        open_projects=open_projects,
        all_projects=all_projects,
        students=students,
        selected_student_id=selected_student_id,
        matched_projects=matched_projects,
        team_members=team_members,
        tasks=tasks,
        selected_proj_id=selected_proj_id,
        mentors=mentors,
        mentor_requests=mentor_requests,
        showcase=showcase,
        admin_stats=admin_stats
    )

# Trigger Route: Creates Project & Fires Auto_Add_Creator_To_Team Trigger
@app.route("/create_project", methods=["POST"])
def create_project():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Projects (creator_id, title, description, max_team_size, status)
        VALUES (%s, %s, %s, %s, 'Open');
    """, (request.form["creator_id"], request.form["title"], request.form["description"], request.form["max_size"]))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard", tab="teams"))

# Task Status Cycle Route (For Kanban Board)
@app.route("/update_task_status/<int:task_id>/<string:new_status>/<int:proj_id>")
def update_task_status(task_id, new_status, proj_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Tasks SET task_status = %s WHERE task_id = %s;", (new_status, task_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard", tab="teams", project_id=proj_id))

# Add New Task Route
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
    return redirect(url_for("dashboard", tab="teams", project_id=proj_id))

# Mentor Request Route
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
    return redirect(url_for("dashboard", tab="mentors"))

# Live Upvote Route for Project Showcase
@app.route("/upvote/<int:showcase_id>")
def upvote(showcase_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE Project_Showcase SET upvotes = upvotes + 1 WHERE showcase_id = %s;", (showcase_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for("dashboard", tab="showcase"))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
