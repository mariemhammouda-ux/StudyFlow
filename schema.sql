-- StudyFlow — schéma SQLite
-- Un utilisateur possède des matières ; tâches, examens et sessions
-- peuvent (optionnellement) être liés à une matière.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    color TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, name),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'todo'
        CHECK (status IN ('todo', 'doing', 'done')),
    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('low', 'medium', 'high')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject_id INTEGER,
    title TEXT NOT NULL,
    exam_date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS study_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject_id INTEGER,
    started_at TEXT NOT NULL,
    duration_min INTEGER NOT NULL CHECK (duration_min > 0),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_subjects_user_name ON subjects(user_id, name);
CREATE INDEX IF NOT EXISTS idx_subjects_user_id ON subjects(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(user_id, due_date);
CREATE INDEX IF NOT EXISTS idx_exams_date ON exams(user_id, exam_date);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON study_sessions(user_id);
-- 1. Temps total étudié + nombre de sessions
SELECT
    COALESCE(SUM(duration_min), 0) AS total_minutes,
    COUNT(*) AS nb_sessions
FROM study_sessions
WHERE user_id = ?;


-- 2. Tâches terminées et restantes
SELECT
    COALESCE(SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END), 0) AS tasks_done,
    COALESCE(SUM(CASE WHEN status != 'done' THEN 1 ELSE 0 END), 0) AS tasks_remaining
FROM tasks
WHERE user_id = ?;


-- 3. Nombre d'examens à venir
SELECT COUNT(*) AS upcoming_exams
FROM exams
WHERE user_id = ?
  AND exam_date >= date('now');


-- 4. Liste des examens à venir
SELECT
    e.id,
    e.title,
    e.exam_date,
    s.name AS subject_name
FROM exams e
LEFT JOIN subjects s
    ON s.id = e.subject_id
    AND s.user_id = e.user_id
WHERE e.user_id = ?
  AND e.exam_date >= date('now')
ORDER BY e.exam_date ASC;


-- 5. Temps étudié par matière
SELECT
    ss.subject_id,
    COALESCE(s.name, 'Sans matière') AS subject_name,
    s.color,
    SUM(ss.duration_min) AS total_minutes,
    COUNT(*) AS nb_sessions
FROM study_sessions ss
LEFT JOIN subjects s
    ON s.id = ss.subject_id
    AND s.user_id = ss.user_id
WHERE ss.user_id = ?
GROUP BY ss.subject_id
ORDER BY total_minutes DESC;