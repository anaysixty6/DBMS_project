COLLAB CAMPUS - FINAL COLLEGE PROJECT PACKAGE
================================================

PROJECT IDEA
Collab Campus helps college students discover projects, find teammates based on skills,
pitch project ideas, join teams, and coordinate tasks and updates.

TECHNOLOGY
- Frontend: HTML, CSS, Jinja templates
- Backend: Python Flask
- Database: MySQL
- Database connection: mysql-connector-python
- Password security: Werkzeug password hashing

PROJECT FILES
- app.py                 Main Flask application and page routes
- database.py            MySQL connection settings
- collab_campus.sql      Database tables, indexes, views, triggers and sample queries
- setup_demo_data.py     Creates demonstration users and sample records on a clean database
- reset_admin.py         Resets the sample admin password if sample admin exists
- templates/             HTML pages
- static/style.css       Website styling
- SHOWCASE_GUIDE.txt     Demo sequence and viva preparation

DATABASE SETUP
1. Open MySQL Workbench.
2. Open collab_campus.sql and execute it on a FRESH database.
3. If you have already created the database and tables using the same final SQL script,
   do not execute the CREATE TABLE/VIEW/TRIGGER script again.
4. Open database.py and replace YOUR_MYSQL_PASSWORD with your local MySQL password.
5. Install dependencies:
      pip install -r requirements.txt
6. For a clean database with no users, run:
      python setup_demo_data.py
   The script stops if users already exist, to avoid duplicate demo records.

SAMPLE DEMO ACCOUNTS (created by setup_demo_data.py)
Admin:
  Email: admin@collabcampus.com
  Password: admin123

Student:
  Email: anay@example.com
  Password: student123

RUN THE APPLICATION
1. Open the project folder in VS Code.
2. Open the terminal in that folder.
3. Run:
      python app.py
4. Visit:
      http://127.0.0.1:5000

STUDENT FEATURES
- Register with name, email, department, year and skills
- Secure password hashing
- Student dashboard
- Skill-based project recommendations
- Browse approved projects
- Pitch project ideas for admin approval
- Browse teams and request to join
- Team leader can accept or reject requests
- View joined teams
- Post and view project updates
- Receive notifications
- View assigned tasks and update task status

ADMIN FEATURES
- Admin dashboard with student/project/pending-pitch counts
- View registered students
- Approve or reject project pitches
- Approved project gets a team; the database trigger adds the pitcher as team leader
- View teams and member counts
- Add hackathon/event records
- Add skills
- Receive notifications

DATABASE CONCEPTS
- Tables and relationships
- Primary keys and foreign keys
- One-to-many and many-to-many relationships
- Joins, subqueries and aggregate functions
- Views
- Basic indexes
- Triggers
- Audit log
- CRUD operations

IMPORTANT DATABASE NOTES
- The project uses a simple beginner-friendly schema.
- It does not use stored procedures, stored functions, or transaction commands in SQL.
- Basic trigger code uses MySQL DELIMITER and BEGIN/END blocks.
- The Flask database connection uses autocommit=True to keep the Python side straightforward.
- Team-capacity and duplicate-membership rules are checked by database triggers.
- Admin/student page access is checked in Flask routes.

SHOWCASE PREPARATION
- Start MySQL before starting Flask.
- Start Flask with python app.py.
- Use a browser with two sessions (normal and private/incognito) to show student and admin roles.
- Use the sample accounts above if setup_demo_data.py was run.
- Do not show your actual MySQL password during the presentation.

SECURITY / SCOPE
This is an educational local showcase project, not a production deployment.
Before public deployment, use a strong secret key, environment variables, HTTPS,
CSRF protection, stricter validation and production server settings.
