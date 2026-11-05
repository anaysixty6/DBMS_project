from database import get_db_connection
from werkzeug.security import generate_password_hash

conn = get_db_connection()
cur = conn.cursor(dictionary=True)

cur.execute("SELECT COUNT(*) AS total FROM users")
if cur.fetchone()["total"] > 0:
    print("Users already exist. Demo data was not added to avoid duplicates.")
    cur.close()
    conn.close()
    raise SystemExit

# Add administrator and sample students with hashed passwords.
people = [
    ("Admin User", "admin@collabcampus.com", "admin123", "admin", "Administration", None),
    ("Anay Sharma", "anay@example.com", "student123", "student", "Computer Science", 2),
    ("Rahul Verma", "rahul@example.com", "student123", "student", "Computer Science", 2),
    ("Priya Singh", "priya@example.com", "student123", "student", "Information Technology", 1),
    ("Aman Gupta", "aman@example.com", "student123", "student", "Computer Science", 2),
    ("Sneha Patel", "sneha@example.com", "student123", "Electronics", 1),
]
user_ids = {}
for name, email, password, role, department, year in people:
    cur.execute("""
        INSERT INTO users (full_name, email, password_hash, role, department, year_of_study)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (name, email, generate_password_hash(password), role, department, year))
    user_ids[email] = cur.lastrowid

skill_names = ["Python", "Java", "HTML", "CSS", "JavaScript", "Machine Learning", "SQL", "UI/UX Design"]
skill_ids = {}
for skill in skill_names:
    cur.execute("INSERT INTO skills (skill_name) VALUES (%s)", (skill,))
    skill_ids[skill] = cur.lastrowid

student_skill_map = {
    "anay@example.com": ["Python", "Machine Learning", "SQL"],
    "rahul@example.com": ["Python", "SQL"],
    "priya@example.com": ["UI/UX Design", "HTML", "CSS"],
    "aman@example.com": ["Machine Learning", "Python"],
    "sneha@example.com": ["Java", "JavaScript"],
}
for email, skills in student_skill_map.items():
    for skill in skills:
        cur.execute("INSERT INTO student_skills (user_id, skill_id) VALUES (%s, %s)",
                    (user_ids[email], skill_ids[skill]))

cur.execute("""
    INSERT INTO events (title, description, start_date, end_date)
    VALUES ('Campus CodeFest', 'A student hackathon and project showcase', '2026-12-10', '2026-12-11')
""")
event_id = cur.lastrowid

projects = [
    ("AI Attendance System", "An attendance platform using face recognition and machine learning.",
     user_ids["anay@example.com"], event_id, "approved", 4, ["Python", "Machine Learning", "SQL"]),
    ("Smart Campus App", "A student app for campus information, events and services.",
     user_ids["rahul@example.com"], event_id, "approved", 5, ["Java", "HTML", "JavaScript"]),
    ("Student Skill Matcher", "A platform that connects students to projects based on skills.",
     user_ids["aman@example.com"], event_id, "pending", 4, ["Python", "SQL", "UI/UX Design"]),
]
project_ids = []
for title, description, pitcher, event, status, max_size, skills in projects:
    cur.execute("""
        INSERT INTO projects (title, description, pitched_by, event_id, status, max_team_size)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (title, description, pitcher, event, status, max_size))
    project_id = cur.lastrowid
    project_ids.append(project_id)
    for skill in skills:
        cur.execute("INSERT INTO project_skills (project_id, skill_id) VALUES (%s, %s)",
                    (project_id, skill_ids[skill]))

# Approved projects get teams; the add_leader_to_team trigger adds each leader.
for project_id, team_name, leader_email in [
    (project_ids[0], "AI Innovators", "anay@example.com"),
    (project_ids[1], "Campus Coders", "rahul@example.com"),
]:
    cur.execute("INSERT INTO teams (team_name, project_id, leader_id) VALUES (%s, %s, %s)",
                (team_name, project_id, user_ids[leader_email]))

# Add a couple of extra members.
cur.execute("SELECT team_id FROM teams WHERE project_id=%s", (project_ids[0],))
team_one = cur.fetchone()["team_id"]
cur.execute("INSERT INTO team_members (team_id, user_id) VALUES (%s, %s)",
            (team_one, user_ids["priya@example.com"]))
cur.execute("INSERT INTO team_members (team_id, user_id) VALUES (%s, %s)",
            (team_one, user_ids["aman@example.com"]))

cur.execute("""
    INSERT INTO tasks (project_id, assigned_to, title, description, due_date, status)
    VALUES (%s, %s, 'Prepare sample dataset', 'Collect and organise sample records.', '2026-12-05', 'in_progress')
""", (project_ids[0], user_ids["anay@example.com"]))
cur.execute("""
    INSERT INTO tasks (project_id, assigned_to, title, description, due_date, status)
    VALUES (%s, %s, 'Design application screens', 'Prepare initial UI screens.', '2026-12-06', 'todo')
""", (project_ids[0], user_ids["priya@example.com"]))

cur.execute("INSERT INTO project_updates (project_id, posted_by, content) VALUES (%s, %s, %s)",
            (project_ids[0], user_ids["anay@example.com"], "Project kickoff completed."))
cur.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
            (user_ids["anay@example.com"], "Welcome to Collab Campus!"))

print("Demo data added successfully.")
print("Admin login: admin@collabcampus.com / admin123")
print("Sample student login: anay@example.com / student123")
cur.close()
conn.close()
