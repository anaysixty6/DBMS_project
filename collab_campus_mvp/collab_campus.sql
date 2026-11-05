-- COLLAB CAMPUS - SIMPLE MYSQL DATABASE
-- Beginner-friendly version for a college DBMS project.
-- No timestamps, ENGINE settings, stored functions, procedures, triggers,
-- DECLARE statements, or transaction commands.

CREATE DATABASE IF NOT EXISTS collab_campus;
USE collab_campus;

-- 1. USERS: stores student and admin details
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'student',
    department VARCHAR(80),
    year_of_study INT,
    bio TEXT
);

-- 2. SKILLS: list of available skills
CREATE TABLE skills (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(60) NOT NULL UNIQUE
);

-- 3. STUDENT_SKILLS: skills selected by each student
CREATE TABLE student_skills (
    user_id INT,
    skill_id INT,
    skill_level VARCHAR(20) DEFAULT 'beginner',
    PRIMARY KEY (user_id, skill_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

-- 4. EVENTS: hackathons and competitions
CREATE TABLE events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(120) NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE
);

-- 5. PROJECTS: projects pitched by students or added by admin
CREATE TABLE projects (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    pitched_by INT NOT NULL,
    event_id INT,
    status VARCHAR(20) DEFAULT 'pending',
    max_team_size INT DEFAULT 4,
    FOREIGN KEY (pitched_by) REFERENCES users(user_id),
    FOREIGN KEY (event_id) REFERENCES events(event_id)
);

-- 6. PROJECT_SKILLS: skills required for each project
CREATE TABLE project_skills (
    project_id INT,
    skill_id INT,
    PRIMARY KEY (project_id, skill_id),
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

-- 7. TEAMS: one team for each project
CREATE TABLE teams (
    team_id INT AUTO_INCREMENT PRIMARY KEY,
    team_name VARCHAR(100) NOT NULL,
    project_id INT NOT NULL UNIQUE,
    leader_id INT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (leader_id) REFERENCES users(user_id)
);

-- 8. TEAM_MEMBERS: students belonging to teams
CREATE TABLE team_members (
    team_id INT,
    user_id INT,
    PRIMARY KEY (team_id, user_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 9. JOIN_REQUESTS: requests sent by students to join teams
CREATE TABLE join_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    user_id INT NOT NULL,
    message VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    UNIQUE (team_id, user_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 10. TASKS: tasks assigned to team members
CREATE TABLE tasks (
    task_id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    assigned_to INT,
    title VARCHAR(150) NOT NULL,
    description TEXT,
    due_date DATE,
    status VARCHAR(20) DEFAULT 'todo',
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (assigned_to) REFERENCES users(user_id)
);

-- 11. PROJECT_UPDATES: announcements and progress updates
CREATE TABLE project_updates (
    update_id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    posted_by INT NOT NULL,
    content TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (posted_by) REFERENCES users(user_id)
);

-- 12. NOTIFICATIONS: notifications shown to students
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    message VARCHAR(500) NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 13. AUDIT_LOG: records important changes made by the admin
CREATE TABLE audit_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    action VARCHAR(30) NOT NULL,
    record_id INT NOT NULL,
    old_value VARCHAR(255),
    new_value VARCHAR(255)
);

-- BASIC INDEXES
-- Indexes help MySQL find records faster when these columns are searched.

CREATE INDEX idx_student_skills_skill
ON student_skills(skill_id);

CREATE INDEX idx_project_skills_skill
ON project_skills(skill_id);

CREATE INDEX idx_projects_status
ON projects(status);

CREATE INDEX idx_tasks_assigned_to
ON tasks(assigned_to);

CREATE INDEX idx_join_requests_status
ON join_requests(status);

CREATE INDEX idx_notifications_user_read
ON notifications(user_id, is_read);

-- SIMPLE VIEWS

-- View 1: Student details with their skills
CREATE VIEW student_profile AS
SELECT u.user_id, u.full_name, u.department, u.year_of_study,
       GROUP_CONCAT(s.skill_name) AS skills
FROM users u
LEFT JOIN student_skills ss ON u.user_id = ss.user_id
LEFT JOIN skills s ON ss.skill_id = s.skill_id
WHERE u.role = 'student'
GROUP BY u.user_id, u.full_name, u.department, u.year_of_study;

-- View 2: Project details with the name of the student who pitched it
CREATE VIEW project_details AS
SELECT p.project_id, p.title, p.description, p.status,
       u.full_name AS pitched_by, p.max_team_size
FROM projects p
JOIN users u ON p.pitched_by = u.user_id;

-- View 3: Team details with the number of members
CREATE VIEW team_details AS
SELECT t.team_id, t.team_name, p.title AS project_name,
       COUNT(tm.user_id) AS total_members, p.max_team_size
FROM teams t
JOIN projects p ON t.project_id = p.project_id
LEFT JOIN team_members tm ON t.team_id = tm.team_id
GROUP BY t.team_id, t.team_name, p.title, p.max_team_size;

-- View 4: Tasks assigned to students
CREATE VIEW student_tasks AS
SELECT t.task_id, t.title AS task_name, t.due_date, t.status,
       u.full_name AS student_name, p.title AS project_name
FROM tasks t
JOIN users u ON t.assigned_to = u.user_id
JOIN projects p ON t.project_id = p.project_id;

-- View 5: Projects waiting for admin approval
CREATE VIEW pending_projects AS
SELECT p.project_id, p.title, p.description, u.full_name AS pitched_by
FROM projects p
JOIN users u ON p.pitched_by = u.user_id
WHERE p.status = 'pending';

-- SAMPLE QUERIES

-- 1. Display all students
SELECT * FROM users WHERE role = 'student';

-- 2. Display all available skills
SELECT * FROM skills;

-- 3. Find approved projects
SELECT * FROM projects WHERE status = 'approved';

-- 4. Find projects matching a student's skills (replace 1 with student user_id)
SELECT DISTINCT p.project_id, p.title, p.description
FROM projects p
JOIN project_skills ps ON p.project_id = ps.project_id
JOIN student_skills ss ON ps.skill_id = ss.skill_id
WHERE ss.user_id = 1 AND p.status = 'approved';

-- 5. Display teams with available places
SELECT t.team_id, t.team_name, p.title AS project_name,
       p.max_team_size - COUNT(tm.user_id) AS available_places
FROM teams t
JOIN projects p ON t.project_id = p.project_id
LEFT JOIN team_members tm ON t.team_id = tm.team_id
GROUP BY t.team_id, t.team_name, p.title, p.max_team_size
HAVING COUNT(tm.user_id) < p.max_team_size;

-- 6. Display a student's tasks (replace 1 with student user_id)
SELECT * FROM student_tasks WHERE task_id IN (
    SELECT task_id FROM tasks WHERE assigned_to = 1
);

-- 7. Display updates for a project (replace 1 with project_id)
SELECT * FROM project_updates WHERE project_id = 1;

-- 8. Display unread notifications for a student (replace 1 with user_id)
SELECT * FROM notifications
WHERE user_id = 1 AND is_read = FALSE;


-- BASIC TRIGGERS
-- Triggers run automatically when the specified database action happens.

DELIMITER $$

-- Trigger 1: Add the team leader as the first team member.
CREATE TRIGGER add_leader_to_team
AFTER INSERT ON teams
FOR EACH ROW
BEGIN
    INSERT INTO team_members (team_id, user_id)
    VALUES (NEW.team_id, NEW.leader_id);
END$$

-- Trigger 2: Do not allow a student to join a team that is already full.
CREATE TRIGGER check_team_capacity
BEFORE INSERT ON team_members
FOR EACH ROW
BEGIN
    IF
        (SELECT COUNT(*)
         FROM team_members
         WHERE team_id = NEW.team_id)
        >=
        (SELECT p.max_team_size
         FROM teams t
         JOIN projects p ON t.project_id = p.project_id
         WHERE t.team_id = NEW.team_id)
    THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'This team is already full';
    END IF;
END$$

-- Trigger 3: Do not allow a student to join two teams for the same project.
CREATE TRIGGER check_one_team_per_project
BEFORE INSERT ON team_members
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT *
        FROM team_members tm
        JOIN teams t ON tm.team_id = t.team_id
        WHERE tm.user_id = NEW.user_id
          AND t.project_id = (
              SELECT project_id
              FROM teams
              WHERE team_id = NEW.team_id
          )
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Student is already in a team for this project';
    END IF;
END$$

-- Trigger 4: When a join request is accepted, add the student to the team.
CREATE TRIGGER accept_team_join_request
AFTER UPDATE ON join_requests
FOR EACH ROW
BEGIN
    IF NEW.status = 'accepted' AND OLD.status = 'pending' THEN
        INSERT INTO team_members (team_id, user_id)
        VALUES (NEW.team_id, NEW.user_id);
    END IF;
END$$

-- Trigger 5: Record project status changes in the audit_log table.
CREATE TRIGGER record_project_status_change
AFTER UPDATE ON projects
FOR EACH ROW
BEGIN
    IF OLD.status <> NEW.status THEN
        INSERT INTO audit_log
            (table_name, action, record_id, old_value, new_value)
        VALUES
            ('projects', 'STATUS CHANGE', NEW.project_id, OLD.status, NEW.status);
    END IF;
END$$

DELIMITER ;
