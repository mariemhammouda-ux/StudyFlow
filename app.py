import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, url_for
from datetime import date, datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import close_db, get_db, init_db, login_required
app = Flask(__name__)
app.secret_key = "studyflow-dev-secret-key"
app.teardown_appcontext(close_db)

init_db()
@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    db = get_db()

    # ===== NOMBRE DE MATIÈRES =====
    subjects_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM subjects
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()["count"]

    # ===== TÂCHES =====
    tasks_total = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM tasks
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()["count"]

    tasks_done = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM tasks
        WHERE user_id = ?
          AND status = 'done'
        """,
        (user_id,),
    ).fetchone()["count"]

    tasks_remaining = tasks_total - tasks_done

    # ===== EXAMENS À VENIR =====
    exams_upcoming_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM exams
        WHERE user_id = ?
          AND exam_date >= date('now')
        """,
        (user_id,),
    ).fetchone()["count"]

    # ===== TEMPS D'ÉTUDE CETTE SEMAINE =====
    today = date.today()

    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    week_total_minutes = db.execute(
        """
        SELECT COALESCE(SUM(duration_min), 0) AS total_minutes
        FROM study_sessions
        WHERE user_id = ?
          AND date(started_at) BETWEEN ? AND ?
        """,
        (
            user_id,
            start_of_week.isoformat(),
            end_of_week.isoformat(),
        ),
    ).fetchone()["total_minutes"]

    # ===== TÂCHES À VENIR =====
    upcoming_tasks = db.execute(
        """
        SELECT
            tasks.*,
            subjects.name AS subject_name,
            subjects.color AS subject_color
        FROM tasks
        LEFT JOIN subjects
            ON tasks.subject_id = subjects.id
        WHERE tasks.user_id = ?
          AND tasks.status != 'done'
        ORDER BY
            CASE
                WHEN tasks.due_date IS NULL THEN 1
                ELSE 0
            END,
            tasks.due_date ASC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()

    # ===== EXAMENS À VENIR =====
    upcoming_exams = db.execute(
        """
        SELECT
            exams.*,
            subjects.name AS subject_name,
            subjects.color AS subject_color
        FROM exams
        LEFT JOIN subjects
            ON exams.subject_id = subjects.id
        WHERE exams.user_id = ?
          AND exams.exam_date >= date('now')
        ORDER BY exams.exam_date ASC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()

    return render_template(
        "index.html",
        subjects_count=subjects_count,
        tasks_total=tasks_total,
        tasks_done=tasks_done,
        tasks_remaining=tasks_remaining,
        exams_upcoming_count=exams_upcoming_count,
        week_total_minutes=week_total_minutes,
        upcoming_tasks=upcoming_tasks,
        upcoming_exams=upcoming_exams,
    )
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect("/")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Nom d’utilisateur et mot de passe obligatoires.")
            return render_template("login.html")

        db = get_db()
        user = db.execute(
            "SELECT id, username, hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if user is None or not check_password_hash(user["hash"], password):
            flash("Identifiants incorrects.")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect("/")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")

        if not username:
            flash("Le nom d’utilisateur est obligatoire.")
            return render_template("register.html")

        if not password:
            flash("Le mot de passe est obligatoire.")
            return render_template("register.html")

        if password != confirmation:
            flash("Les mots de passe ne correspondent pas.")
            return render_template("register.html")

        db = get_db()

        existing_user = db.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if existing_user is not None:
            flash("Ce nom d’utilisateur existe déjà.")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            (username, password_hash),
        )
        db.commit()

        flash("Compte créé avec succès. Vous pouvez maintenant vous connecter.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
@app.route("/subjects")
@login_required
def subjects():
    db = get_db()
    user_id = session["user_id"]

    subjects = db.execute(
        "SELECT id, name, color FROM subjects WHERE user_id = ? ORDER BY name COLLATE NOCASE",
        (user_id,),
    ).fetchall()

    return render_template("subjects.html", subjects=subjects)


@app.route("/subjects/new", methods=["GET", "POST"])
@login_required
def new_subject():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        color = request.form.get("color", "").strip()

        if not name:
            flash("Le nom de la matière est obligatoire.")
            return render_template(
                "subject_form.html",
                subject=None,
                form_action=url_for("new_subject"),
                title="Ajouter une matière",
            )

        db = get_db()
        user_id = session["user_id"]

        try:
            db.execute(
                "INSERT INTO subjects (user_id, name, color) VALUES (?, ?, ?)",
                (user_id, name, color or None),
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("Vous avez déjà une matière avec ce nom.")
            return render_template(
                "subject_form.html",
                subject=None,
                form_action=url_for("new_subject"),
                title="Ajouter une matière",
            )

        flash("Matière ajoutée.")
        return redirect(url_for("subjects"))

    return render_template(
        "subject_form.html",
        subject=None,
        form_action=url_for("new_subject"),
        title="Ajouter une matière",
    )


@app.route("/subjects/<int:subject_id>/edit", methods=["GET", "POST"])
@login_required
def edit_subject(subject_id):
    db = get_db()
    user_id = session["user_id"]

    subject = db.execute(
        "SELECT id, name, color FROM subjects WHERE id = ? AND user_id = ?",
        (subject_id, user_id),
    ).fetchone()

    if subject is None:
        flash("Matière introuvable.")
        return redirect(url_for("subjects"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        color = request.form.get("color", "").strip()

        if not name:
            flash("Le nom de la matière est obligatoire.")
            return render_template(
                "subject_form.html",
                subject=subject,
                form_action=url_for("edit_subject", subject_id=subject_id),
                title="Modifier la matière",
            )

        try:
            db.execute(
                "UPDATE subjects SET name = ?, color = ? WHERE id = ? AND user_id = ?",
                (name, color or None, subject_id, user_id),
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("Vous avez déjà une matière avec ce nom.")
            return render_template(
                "subject_form.html",
                subject=subject,
                form_action=url_for("edit_subject", subject_id=subject_id),
                title="Modifier la matière",
            )

        flash("Matière modifiée.")
        return redirect(url_for("subjects"))

    return render_template(
        "subject_form.html",
        subject=subject,
        form_action=url_for("edit_subject", subject_id=subject_id),
        title="Modifier la matière",
    )


@app.route("/subjects/<int:subject_id>/delete", methods=["POST"])
@login_required
def delete_subject(subject_id):
    db = get_db()
    user_id = session["user_id"]

    db.execute(
        "DELETE FROM subjects WHERE id = ? AND user_id = ?",
        (subject_id, user_id),
    )
    db.commit()

    flash("Matière supprimée.")
    return redirect(url_for("subjects"))
@app.route("/tasks")
@login_required
def tasks():
    db = get_db()
    user_id = session["user_id"]

    tasks = db.execute(
        """
        SELECT tasks.id, tasks.title, tasks.description, tasks.due_date,
               tasks.status, tasks.priority, subjects.name AS subject_name,
               subjects.color AS subject_color
        FROM tasks
        LEFT JOIN subjects ON subjects.id = tasks.subject_id
        WHERE tasks.user_id = ?
        ORDER BY
            CASE WHEN tasks.due_date IS NULL THEN 1 ELSE 0 END,
            tasks.due_date ASC
        """,
        (user_id,),
    ).fetchall()

    return render_template("tasks.html", tasks=tasks)


@app.route("/tasks/new", methods=["GET", "POST"])
@login_required
def new_task():
    db = get_db()
    user_id = session["user_id"]

    subjects = db.execute(
        "SELECT id, name FROM subjects WHERE user_id = ? ORDER BY name COLLATE NOCASE",
        (user_id,),
    ).fetchall()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date", "").strip()
        priority = request.form.get("priority", "medium")
        status = request.form.get("status", "todo")
        subject_id_raw = request.form.get("subject_id", "").strip()

        if not title:
            flash("Le titre de la tâche est obligatoire.")
            return render_template(
                "task_form.html",
                task=None,
                subjects=subjects,
                form_action=url_for("new_task"),
                title_page="Ajouter une tâche",
            )

        if priority not in ("low", "medium", "high"):
            priority = "medium"
        if status not in ("todo", "doing", "done"):
            status = "todo"

        subject_id = None
        if subject_id_raw:
            owned_subject = db.execute(
                "SELECT id FROM subjects WHERE id = ? AND user_id = ?",
                (subject_id_raw, user_id),
            ).fetchone()
            if owned_subject is None:
                flash("Matière invalide.")
                return render_template(
                    "task_form.html",
                    task=None,
                    subjects=subjects,
                    form_action=url_for("new_task"),
                    title_page="Ajouter une tâche",
                )
            subject_id = owned_subject["id"]

        db.execute(
            """
            INSERT INTO tasks (user_id, subject_id, title, description, due_date, status, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, subject_id, title, description or None, due_date or None, status, priority),
        )
        db.commit()

        flash("Tâche ajoutée.")
        return redirect(url_for("tasks"))

    return render_template(
        "task_form.html",
        task=None,
        subjects=subjects,
        form_action=url_for("new_task"),
        title_page="Ajouter une tâche",
    )


@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    db = get_db()
    user_id = session["user_id"]

    task = db.execute(
        "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id),
    ).fetchone()

    if task is None:
        flash("Tâche introuvable.")
        return redirect(url_for("tasks"))

    subjects = db.execute(
        "SELECT id, name FROM subjects WHERE user_id = ? ORDER BY name COLLATE NOCASE",
        (user_id,),
    ).fetchall()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        due_date = request.form.get("due_date", "").strip()
        priority = request.form.get("priority", "medium")
        status = request.form.get("status", "todo")
        subject_id_raw = request.form.get("subject_id", "").strip()

        if not title:
            flash("Le titre de la tâche est obligatoire.")
            return render_template(
                "task_form.html",
                task=task,
                subjects=subjects,
                form_action=url_for("edit_task", task_id=task_id),
                title_page="Modifier la tâche",
            )

        if priority not in ("low", "medium", "high"):
            priority = "medium"
        if status not in ("todo", "doing", "done"):
            status = "todo"

        subject_id = None
        if subject_id_raw:
            owned_subject = db.execute(
                "SELECT id FROM subjects WHERE id = ? AND user_id = ?",
                (subject_id_raw, user_id),
            ).fetchone()
            if owned_subject is None:
                flash("Matière invalide.")
                return render_template(
                    "task_form.html",
                    task=task,
                    subjects=subjects,
                    form_action=url_for("edit_task", task_id=task_id),
                    title_page="Modifier la tâche",
                )
            subject_id = owned_subject["id"]

        db.execute(
            """
            UPDATE tasks
            SET subject_id = ?, title = ?, description = ?, due_date = ?, status = ?, priority = ?
            WHERE id = ? AND user_id = ?
            """,
            (subject_id, title, description or None, due_date or None, status, priority, task_id, user_id),
        )
        db.commit()

        flash("Tâche modifiée.")
        return redirect(url_for("tasks"))

    return render_template(
        "task_form.html",
        task=task,
        subjects=subjects,
        form_action=url_for("edit_task", task_id=task_id),
        title_page="Modifier la tâche",
    )


@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    db = get_db()
    user_id = session["user_id"]

    db.execute(
        "DELETE FROM tasks WHERE id = ? AND user_id = ?",
        (task_id, user_id),
    )
    db.commit()

    flash("Tâche supprimée.")
    return redirect(url_for("tasks"))


@app.route("/tasks/<int:task_id>/complete", methods=["POST"])
@login_required
def complete_task(task_id):
    db = get_db()
    user_id = session["user_id"]

    db.execute(
        "UPDATE tasks SET status = 'done' WHERE id = ? AND user_id = ?",
        (task_id, user_id),
    )
    db.commit()

    flash("Tâche marquée comme terminée.")
    return redirect(url_for("tasks"))



@app.route("/exams/new", methods=["GET", "POST"])
@login_required
def new_exam():
    db = get_db()
    user_id = session["user_id"]

    subjects = db.execute(
        "SELECT id, name FROM subjects WHERE user_id = ? ORDER BY name COLLATE NOCASE",
        (user_id,),
    ).fetchall()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        exam_date = request.form.get("exam_date", "").strip()
        notes = request.form.get("notes", "").strip()
        subject_id_raw = request.form.get("subject_id", "").strip()

        if not title:
            flash("Le titre de l'examen est obligatoire.")
            return render_template(
                "exam_form.html",
                exam=None,
                subjects=subjects,
                form_action=url_for("new_exam"),
                title_page="Ajouter un examen",
            )

        if not exam_date:
            flash("La date de l'examen est obligatoire.")
            return render_template(
                "exam_form.html",
                exam=None,
                subjects=subjects,
                form_action=url_for("new_exam"),
                title_page="Ajouter un examen",
            )

        subject_id = None
        if subject_id_raw:
            owned_subject = db.execute(
                "SELECT id FROM subjects WHERE id = ? AND user_id = ?",
                (subject_id_raw, user_id),
            ).fetchone()
            if owned_subject is None:
                flash("Matière invalide.")
                return render_template(
                    "exam_form.html",
                    exam=None,
                    subjects=subjects,
                    form_action=url_for("new_exam"),
                    title_page="Ajouter un examen",
                )
            subject_id = owned_subject["id"]

        db.execute(
            """
            INSERT INTO exams (user_id, subject_id, title, exam_date, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, subject_id, title, exam_date, notes or None),
        )
        db.commit()

        flash("Examen ajouté.")
        return redirect(url_for("exams"))

    return render_template(
        "exam_form.html",
        exam=None,
        subjects=subjects,
        form_action=url_for("new_exam"),
        title_page="Ajouter un examen",
    )

# ============================================================
# À METTRE dans app.py
# 1) Ajoute ce bloc juste AVANT la route @app.route("/exams")
# 2) Remplace l'ancienne fonction exams() par celle-ci
# Les routes new_exam / edit_exam / delete_exam ne changent pas.
# ============================================================

MOIS_COURT = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
              "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MOIS_LONG = ["janvier", "février", "mars", "avril", "mai", "juin",
             "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def build_exam_item(row, today):
    """Prépare un examen pour l'affichage. Le compte à rebours est calculé ici, une seule fois."""
    item = {
        "id": row["id"],
        "title": row["title"],
        "notes": row["notes"],
        "subject_name": row["subject_name"],
        "color": row["subject_color"] or "var(--color-primary)",
    }
    try:
        d = date.fromisoformat(row["exam_date"][:10])
    except (TypeError, ValueError):
        item.update(day="–", month="", full_date=row["exam_date"] or "",
                    long_date=row["exam_date"] or "", days_left=None, countdown="")
        return item

    days = (d - today).days
    if days == 0:
        countdown = "Aujourd'hui"
    elif days == 1:
        countdown = "Demain"
    elif days > 1:
        countdown = f"Dans {days} jours"
    elif days == -1:
        countdown = "Hier"
    else:
        countdown = f"Il y a {-days} jours"

    item.update(
        day=d.day,
        month=MOIS_COURT[d.month - 1],
        full_date=f"{d.day} {MOIS_COURT[d.month - 1]} {d.year}",
        long_date=f"{JOURS[d.weekday()]} {d.day} {MOIS_LONG[d.month - 1]}",
        days_left=days,
        countdown=countdown,
    )
    return item


@app.route("/exams")
@login_required
def exams():
    db = get_db()
    user_id = session["user_id"]

    rows = db.execute(
        """
        SELECT exams.id, exams.title, exams.exam_date, exams.notes,
               subjects.name AS subject_name,
               subjects.color AS subject_color
        FROM exams
        LEFT JOIN subjects ON subjects.id = exams.subject_id
        WHERE exams.user_id = ?
        ORDER BY exams.exam_date ASC
        """,
        (user_id,),
    ).fetchall()

    today = date.today()
    upcoming, past = [], []

    for row in rows:
        item = build_exam_item(row, today)

        if item["days_left"] is not None and item["days_left"] >= 0:
            upcoming.append(item)
        else:
            past.append(item)

    past.reverse()

    view = "past" if request.args.get("view") == "past" else "upcoming"

    return render_template(
        "exams.html",
        upcoming=upcoming,
        past=past,
        next_exam=upcoming[0] if upcoming else None,
        shown=past if view == "past" else upcoming,
        view=view,
    )
@app.route("/exams/<int:exam_id>/edit", methods=["GET", "POST"])
@login_required
def edit_exam(exam_id):
    db = get_db()
    user_id = session["user_id"]

    exam = db.execute(
        "SELECT * FROM exams WHERE id = ? AND user_id = ?",
        (exam_id, user_id),
    ).fetchone()

    if exam is None:
        flash("Examen introuvable.")
        return redirect(url_for("exams"))

    subjects = db.execute(
        "SELECT id, name FROM subjects WHERE user_id = ? ORDER BY name COLLATE NOCASE",
        (user_id,),
    ).fetchall()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        exam_date = request.form.get("exam_date", "").strip()
        notes = request.form.get("notes", "").strip()
        subject_id_raw = request.form.get("subject_id", "").strip()

        if not title:
            flash("Le titre de l'examen est obligatoire.")
            return render_template(
                "exam_form.html",
                exam=exam,
                subjects=subjects,
                form_action=url_for("edit_exam", exam_id=exam_id),
                title_page="Modifier l'examen",
            )

        if not exam_date:
            flash("La date de l'examen est obligatoire.")
            return render_template(
                "exam_form.html",
                exam=exam,
                subjects=subjects,
                form_action=url_for("edit_exam", exam_id=exam_id),
                title_page="Modifier l'examen",
            )

        subject_id = None
        if subject_id_raw:
            owned_subject = db.execute(
                "SELECT id FROM subjects WHERE id = ? AND user_id = ?",
                (subject_id_raw, user_id),
            ).fetchone()
            if owned_subject is None:
                flash("Matière invalide.")
                return render_template(
                    "exam_form.html",
                    exam=exam,
                    subjects=subjects,
                    form_action=url_for("edit_exam", exam_id=exam_id),
                    title_page="Modifier l'examen",
                )
            subject_id = owned_subject["id"]

        db.execute(
            """
            UPDATE exams
            SET subject_id = ?, title = ?, exam_date = ?, notes = ?
            WHERE id = ? AND user_id = ?
            """,
            (subject_id, title, exam_date, notes or None, exam_id, user_id),
        )
        db.commit()

        flash("Examen modifié.")
        return redirect(url_for("exams"))

    return render_template(
        "exam_form.html",
        exam=exam,
        subjects=subjects,
        form_action=url_for("edit_exam", exam_id=exam_id),
        title_page="Modifier l'examen",
    )


@app.route("/exams/<int:exam_id>/delete", methods=["POST"])
@login_required
def delete_exam(exam_id):
    db = get_db()
    user_id = session["user_id"]

    db.execute(
        "DELETE FROM exams WHERE id = ? AND user_id = ?",
        (exam_id, user_id),
    )
    db.commit()

    flash("Examen supprimé.")
    return redirect(url_for("exams"))
# ============================================================
# À METTRE dans app.py : remplace TOUTE l'ancienne fonction
# calendar_page() (de @app.route("/calendar") jusqu'à son return).
# Le filtrage par user_id est conservé sur les deux requêtes.
# ============================================================

@app.route("/calendar")
@login_required
def calendar_page():
    db = get_db()
    user_id = session["user_id"]

    tasks_rows = db.execute(
        """
        SELECT tasks.id, tasks.title, tasks.due_date, tasks.status,
               subjects.name AS subject_name,
               subjects.color AS subject_color
        FROM tasks
        LEFT JOIN subjects ON subjects.id = tasks.subject_id
        WHERE tasks.user_id = ?
          AND tasks.due_date IS NOT NULL
        """,
        (user_id,),
    ).fetchall()

    exams_rows = db.execute(
        """
        SELECT exams.id, exams.title, exams.exam_date,
               subjects.name AS subject_name,
               subjects.color AS subject_color
        FROM exams
        LEFT JOIN subjects ON subjects.id = exams.subject_id
        WHERE exams.user_id = ?
        """,
        (user_id,),
    ).fetchall()

    events = []

    for task in tasks_rows:
        events.append(
            {
                "type": "task",
                "date": task["due_date"],
                "title": task["title"],
                "subject": task["subject_name"],
                "color": task["subject_color"],
                "status": task["status"],
                "url": url_for("edit_task", task_id=task["id"]),
            }
        )

    for exam in exams_rows:
        events.append(
            {
                "type": "exam",
                "date": exam["exam_date"],
                "title": exam["title"],
                "subject": exam["subject_name"],
                "color": exam["subject_color"],
                "url": url_for("edit_exam", exam_id=exam["id"]),
            }
        )

    return render_template("calendar.html", events=events)


@app.route("/timer")
@login_required
def timer_page():
    db = get_db()
    user_id = session["user_id"]

    today = date.today()
    yesterday = today - timedelta(days=1)

    # ---------------------------------------------------------
    # Matières de l'utilisateur
    # ---------------------------------------------------------
    subjects = db.execute(
        """
        SELECT id, name
        FROM subjects
        WHERE user_id = ?
        ORDER BY name COLLATE NOCASE
        """,
        (user_id,),
    ).fetchall()

    # ---------------------------------------------------------
    # Statistiques d'aujourd'hui
    # ---------------------------------------------------------
    today_stats = db.execute(
        """
        SELECT
            COUNT(*) AS sessions_count,
            COALESCE(SUM(duration_min), 0) AS total_minutes
        FROM study_sessions
        WHERE user_id = ?
          AND date(started_at) = ?
        """,
        (user_id, today.isoformat()),
    ).fetchone()

    today_sessions = today_stats["sessions_count"]
    today_focus_minutes = today_stats["total_minutes"]

    # Le schéma actuel ne possède pas de système de pauses.
    today_pauses = 0

    

    # ---------------------------------------------------------
    # 5 dernières sessions
    # ---------------------------------------------------------
    recent_rows = db.execute(
        """
        SELECT
            study_sessions.started_at,
            study_sessions.duration_min,
            subjects.name AS subject_name
        FROM study_sessions
        LEFT JOIN subjects
            ON subjects.id = study_sessions.subject_id
           AND subjects.user_id = study_sessions.user_id
        WHERE study_sessions.user_id = ?
        ORDER BY study_sessions.started_at DESC,
                 study_sessions.id DESC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()

    recent_sessions = []

    for row in recent_rows:
        started_at = row["started_at"]

        try:
            session_date = date.fromisoformat(started_at[:10])
        except (ValueError, TypeError):
            session_date = None

        # Date
        if session_date == today:
            when = "Aujourd'hui"
        elif session_date == yesterday:
            when = "Hier"
        elif session_date is not None:
            when = f"{session_date.day} {MOIS_COURT[session_date.month - 1]}"
        else:
            when = started_at

        # Heure
        if (
            isinstance(started_at, str)
            and len(started_at) >= 16
            and "T" in started_at
        ):
            when += f" à {started_at[11:13]}h{started_at[14:16]}"

        recent_sessions.append(
            {
                "subject_name": row["subject_name"] or "Sans matière",
                "duration_label": format_minutes(row["duration_min"]),
                "when_label": when,
            }
        )

    return render_template(
        "timer.html",
        subjects=subjects,

        # Aujourd'hui
        today_sessions=today_sessions,
        today_focus_label=format_minutes(today_focus_minutes),
        today_pauses=today_pauses,


        # Historique
        recent_sessions=recent_sessions,
    )
@app.route("/timer/save", methods=["POST"])
@login_required
def save_timer_session():
    db = get_db()
    user_id = session["user_id"]

    duration_min = request.form.get("duration_min", type=int)

    if duration_min is None or duration_min <= 0:
        flash("Veuillez entrer une durée valide.")
        return redirect(url_for("timer_page"))

    subject_id_raw = (request.form.get("subject_id") or "").strip()
    subject_id = None

    if subject_id_raw:
        owned_subject = db.execute(
            """
            SELECT id
            FROM subjects
            WHERE id = ? AND user_id = ?
            """,
            (subject_id_raw, user_id),
        ).fetchone()

        if owned_subject is None:
            flash("Matière invalide.")
            return redirect(url_for("timer_page"))

        subject_id = owned_subject["id"]

    db.execute(
        """
        INSERT INTO study_sessions (
            user_id,
            subject_id,
            started_at,
            duration_min
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            subject_id,
            datetime.now().isoformat(timespec="seconds"),
            duration_min,
        ),
    )

    db.commit()

    flash(f"Session de {duration_min} minutes enregistrée.")
    return redirect(url_for("timer_page"))
DAY_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
def last_months(today, count=6):
    year = today.year
    month = today.month

    months = []

    for _ in range(count):
        months.append((year, month))

        month -= 1

        if month == 0:
            month = 12
            year -= 1

    return list(reversed(months))
@app.route("/statistics")
@login_required
def statistics():
    db = get_db()
    user_id = session["user_id"]
    today = date.today()

    # ---------- 1. Résumé : total, nombre de sessions, moyenne ----------
    totals = db.execute(
        """
        SELECT COALESCE(SUM(duration_min), 0) AS total_minutes,
               COUNT(*) AS sessions_count
        FROM study_sessions
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    total_minutes = totals["total_minutes"]
    sessions_count = totals["sessions_count"]
    average_minutes = round(total_minutes / sessions_count) if sessions_count else 0

    # ---------- 2. Tâches complètes + taux de complétion ----------
    tasks_stats = db.execute(
        """
        SELECT
            COUNT(*) AS total_tasks,
            COALESCE(
                SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END),
                0
            ) AS completed_tasks
        FROM tasks
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    total_tasks = tasks_stats["total_tasks"]
    completed_tasks = tasks_stats["completed_tasks"]

    completion_percent = (
        round(completed_tasks * 100 / total_tasks)
        if total_tasks
        else 0
    )

    # Sessions de ce mois-ci
    month_start = today.replace(day=1)
    next_month = date(
        today.year + (today.month == 12),
        today.month % 12 + 1,
        1
    )


    month_count = db.execute(
        """
        SELECT COUNT(*) AS n
        FROM study_sessions
        WHERE user_id = ? AND started_at >= ? AND started_at < ?
        """,
        (user_id, month_start.isoformat(), next_month.isoformat()),
    ).fetchone()["n"]

    # ---------- 2. Cette semaine (lundi -> dimanche) ----------
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    weekly_rows = db.execute(
        """
        SELECT date(started_at) AS study_date,
               SUM(duration_min) AS total_minutes
        FROM study_sessions
        WHERE user_id = ? AND date(started_at) BETWEEN ? AND ?
        GROUP BY date(started_at)
        """,
        (user_id, start_of_week.isoformat(), end_of_week.isoformat()),
    ).fetchall()

    weekly = {row["study_date"]: row["total_minutes"] for row in weekly_rows}
    max_day = max(weekly.values(), default=0)

    week_days = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        minutes = weekly.get(day.isoformat(), 0)
        height = round(minutes * 100 / max_day) if max_day else 0
        if minutes > 0:
            height = max(height, 4)  # une barre très courte reste visible
        week_days.append(
            {
                "label": DAY_LABELS[i],
                "minutes": minutes,
                "value": format_minutes(minutes) if minutes else "",
                "height": height,
                "is_today": day == today,
            }
        )
    week_total_label = format_minutes(sum(d["minutes"] for d in week_days))

    # ---------- 3. Temps d'étude par matière ----------
    subject_rows = db.execute(
        """
        SELECT subjects.name AS name,
               subjects.color AS color,
               SUM(study_sessions.duration_min) AS total_minutes,
               COUNT(*) AS sessions_count
        FROM study_sessions
        LEFT JOIN subjects
               ON subjects.id = study_sessions.subject_id
              AND subjects.user_id = study_sessions.user_id
        WHERE study_sessions.user_id = ?
        GROUP BY study_sessions.subject_id
        ORDER BY total_minutes DESC
        """,
        (user_id,),
    ).fetchall()

    max_subject = max((r["total_minutes"] for r in subject_rows), default=0)
    study_by_subject = []
    top_subject = None

    for row in subject_rows:
        item = {
            "name": row["name"] or "Sans matière",
            "color": row["color"] or "var(--color-text-subtle)",
            "label": format_minutes(row["total_minutes"]),
            "percent": round(row["total_minutes"] * 100 / max_subject) if max_subject else 0,
        }
        study_by_subject.append(item)
        if top_subject is None and row["name"]:
            top_subject = item

    # ---------- 4. Évolution : 6 derniers mois ----------
    months = last_months(today, 6)
    first_year, first_month = months[0]

    month_rows = db.execute(
        """
        SELECT strftime('%Y-%m', started_at) AS month,
               SUM(duration_min) AS total_minutes
        FROM study_sessions
        WHERE user_id = ? AND started_at >= ?
        GROUP BY month
        """,
        (user_id, f"{first_year}-{first_month:02d}-01"),
    ).fetchall()

    by_month = {row["month"]: row["total_minutes"] for row in month_rows}
    values = [by_month.get(f"{y}-{m:02d}", 0) for y, m in months]
    max_month = max(values)

    month_points = []
    for i, ((y, m), minutes) in enumerate(zip(months, values)):
        x = (i + 0.5) * 100 / len(months)
        height = 8 + 84 * minutes / max_month if max_month else 8   # 8 % à 92 % de la hauteur
        label = MOIS_COURT[m - 1].capitalize()
        month_points.append(
            {
                "label": label,
                "x": round(x, 2),
                "y": round(height, 2),
                "svg_y": round(100 - height, 2),
                "title": f"{label} {y} : {format_minutes(minutes)}",
            }
        )
    line_points = " ".join(f"{p['x']},{p['svg_y']}" for p in month_points)

    # ---------- 5. Tâches par matière ----------
    task_rows = db.execute(
        """
        SELECT subjects.name AS name,
               subjects.color AS color,
               COUNT(tasks.id) AS total,
               COALESCE(SUM(CASE WHEN tasks.status = 'done' THEN 1 ELSE 0 END), 0) AS done
        FROM subjects
        LEFT JOIN tasks
               ON tasks.subject_id = subjects.id
              AND tasks.user_id = subjects.user_id
        WHERE subjects.user_id = ?
        GROUP BY subjects.id
        ORDER BY subjects.name COLLATE NOCASE
        """,
        (user_id,),
    ).fetchall()

    tasks_by_subject = [
        {
            "name": row["name"],
            "color": row["color"] or "var(--color-primary)",
            "done": row["done"],
            "total": row["total"],
            "percent": row["done"] * 100 // row["total"] if row["total"] else 0,
        }
        for row in task_rows
    ]

    return render_template(
        "statistics.html",
        sessions_count=sessions_count,
        month_count=month_count,
        total_label=format_minutes(total_minutes),
        average_label=format_minutes(average_minutes),
        week_total_label=week_total_label,
        top_subject=top_subject,
        week_days=week_days,
        study_by_subject=study_by_subject,
        month_points=month_points,
        line_points=line_points,
        tasks_by_subject=tasks_by_subject,
        completed_tasks=completed_tasks,
completion_percent=completion_percent,
    )
   
# ============================================================
# À COLLER dans app.py, tout à la fin, juste AVANT :
#     if __name__ == "__main__":
# (MOIS_COURT existe déjà dans ton app.py grâce au patch Examens.)
# ============================================================

def format_minutes(minutes):
    """90 -> '1h 30m' ; 45 -> '45 min'."""
    hours, mins = divmod(minutes or 0, 60)
    if hours:
        return f"{hours}h {mins:02d}m"
    return f"{mins} min"


def session_form_defaults(row=None):
    """Valeurs affichées dans le formulaire (vide + date du jour, ou séance existante)."""
    if row is None:
        return {
            "subject_id": "",
            "session_date": date.today().isoformat(),
            "duration_min": "",
            "notes": "",
        }
    return {
        "subject_id": row["subject_id"] or "",
        "session_date": row["started_at"][:10],
        "duration_min": row["duration_min"],
        "notes": row["notes"] or "",
    }


def read_session_form(db, user_id):
    """Lit et vérifie le formulaire. Retourne (valeurs, message_d_erreur).
    Si erreur : les valeurs sont celles tapées (pour réafficher le formulaire).
    Si tout est bon : subject_id est l'id vérifié (ou None) et duration_min un entier."""
    subject_id_raw = request.form.get("subject_id", "").strip()
    session_date = request.form.get("session_date", "").strip()
    duration_raw = request.form.get("duration_min", "").strip()
    notes = request.form.get("notes", "").strip()

    values = {
        "subject_id": subject_id_raw,
        "session_date": session_date,
        "duration_min": duration_raw,
        "notes": notes,
    }

    try:
        values["session_date"] = date.fromisoformat(session_date).isoformat()
    except ValueError:
        return values, "La date de la séance est invalide."

    if not duration_raw.isdigit() or not 1 <= int(duration_raw) <= 1440:
        return values, "La durée doit être un nombre de minutes entre 1 et 1440."

    subject_id = None
    if subject_id_raw:
        owned_subject = db.execute(
            "SELECT id FROM subjects WHERE id = ? AND user_id = ?",
            (subject_id_raw, user_id),
        ).fetchone()
        if owned_subject is None:
            return values, "Matière invalide."
        subject_id = owned_subject["id"]

    values["subject_id"] = subject_id
    values["duration_min"] = int(duration_raw)
    return values, None


@app.route("/study-sessions")
@login_required
def study_sessions():
    db = get_db()
    user_id = session["user_id"]

    rows = db.execute(
        """
        SELECT study_sessions.id, study_sessions.started_at,
               study_sessions.duration_min, study_sessions.notes,
               subjects.name AS subject_name,
               subjects.color AS subject_color
        FROM study_sessions
        LEFT JOIN subjects
               ON subjects.id = study_sessions.subject_id
              AND subjects.user_id = study_sessions.user_id
        WHERE study_sessions.user_id = ?
        ORDER BY study_sessions.started_at DESC, study_sessions.id DESC
        """,
        (user_id,),
    ).fetchall()

    items = []
    total_minutes = 0

    for row in rows:
        total_minutes += row["duration_min"]

        try:
            d = date.fromisoformat(row["started_at"][:10])
            date_label = f"{d.day} {MOIS_COURT[d.month - 1]} {d.year}"
        except ValueError:
            date_label = row["started_at"]

        items.append(
            {
                "id": row["id"],
                "subject_name": row["subject_name"],
                "color": row["subject_color"] or "var(--color-primary)",
                "date_label": date_label,
                "duration_label": format_minutes(row["duration_min"]),
                "notes": row["notes"],
            }
        )

    return render_template(
        "study_sessions.html",
        sessions=items,
        count=len(items),
        total_label=format_minutes(total_minutes),
    )


@app.route("/study-sessions/new", methods=["GET", "POST"])
@login_required
def new_study_session():
    db = get_db()
    user_id = session["user_id"]

    subjects = db.execute(
        "SELECT id, name FROM subjects WHERE user_id = ? ORDER BY name COLLATE NOCASE",
        (user_id,),
    ).fetchall()

    if request.method == "POST":
        values, error = read_session_form(db, user_id)

        if error:
            flash(error)
            return render_template(
                "study_session_form.html",
                form=values,
                subjects=subjects,
                form_action=url_for("new_study_session"),
                title_page="Nouvelle séance",
            )

        db.execute(
            """
            INSERT INTO study_sessions (user_id, subject_id, started_at, duration_min, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                values["subject_id"],
                values["session_date"],
                values["duration_min"],
                values["notes"] or None,
            ),
        )
        db.commit()

        flash("Séance ajoutée.")
        return redirect(url_for("study_sessions"))

    return render_template(
        "study_session_form.html",
        form=session_form_defaults(),
        subjects=subjects,
        form_action=url_for("new_study_session"),
        title_page="Nouvelle séance",
    )


@app.route("/study-sessions/<int:session_id>/edit", methods=["GET", "POST"])
@login_required
def edit_study_session(session_id):
    db = get_db()
    user_id = session["user_id"]

    row = db.execute(
        "SELECT * FROM study_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    ).fetchone()

    if row is None:
        flash("Séance introuvable.")
        return redirect(url_for("study_sessions"))

    subjects = db.execute(
        "SELECT id, name FROM subjects WHERE user_id = ? ORDER BY name COLLATE NOCASE",
        (user_id,),
    ).fetchall()

    if request.method == "POST":
        values, error = read_session_form(db, user_id)

        if error:
            flash(error)
            return render_template(
                "study_session_form.html",
                form=values,
                subjects=subjects,
                form_action=url_for("edit_study_session", session_id=session_id),
                title_page="Modifier la séance",
            )

        # On garde l'heure éventuelle enregistrée par le Pomodoro (partie après la date)
        started_at = values["session_date"] + row["started_at"][10:]

        db.execute(
            """
            UPDATE study_sessions
            SET subject_id = ?, started_at = ?, duration_min = ?, notes = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                values["subject_id"],
                started_at,
                values["duration_min"],
                values["notes"] or None,
                session_id,
                user_id,
            ),
        )
        db.commit()

        flash("Séance modifiée.")
        return redirect(url_for("study_sessions"))

    return render_template(
        "study_session_form.html",
        form=session_form_defaults(row),
        subjects=subjects,
        form_action=url_for("edit_study_session", session_id=session_id),
        title_page="Modifier la séance",
    )


@app.route("/study-sessions/<int:session_id>/delete", methods=["POST"])
@login_required
def delete_study_session(session_id):
    db = get_db()
    user_id = session["user_id"]

    cursor = db.execute(
        "DELETE FROM study_sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    db.commit()

    if cursor.rowcount == 0:
        flash("Séance introuvable.")
    else:
        flash("Séance supprimée.")
    return redirect(url_for("study_sessions"))
# ============================================================
# À AJOUTER dans app.py, avant "if __name__ == '__main__':"
# Nouvelles routes : profile, update_username, update_password, settings.
# Aucune route existante n'est modifiée.
# ============================================================

@app.route("/profile")
@login_required
def profile():
    db = get_db()
    user_id = session["user_id"]

    user = db.execute(
        "SELECT username, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    member_since = None
    if user and user["created_at"]:
        try:
            d = date.fromisoformat(user["created_at"][:10])
            member_since = f"{d.day} {MOIS_LONG[d.month - 1]} {d.year}"
        except ValueError:
            member_since = user["created_at"]

    return render_template("profile.html", user=user, member_since=member_since)


@app.route("/profile/username", methods=["POST"])
@login_required
def update_username():
    db = get_db()
    user_id = session["user_id"]

    new_username = request.form.get("username", "").strip()

    if not new_username:
        flash("Le nom d'utilisateur est obligatoire.")
        return redirect(url_for("profile"))

    existing = db.execute(
        "SELECT id FROM users WHERE username = ? AND id != ?",
        (new_username, user_id),
    ).fetchone()

    if existing is not None:
        flash("Ce nom d'utilisateur est déjà utilisé.")
        return redirect(url_for("profile"))

    db.execute(
        "UPDATE users SET username = ? WHERE id = ?",
        (new_username, user_id),
    )
    db.commit()

    session["username"] = new_username

    flash("Nom d'utilisateur mis à jour.")
    return redirect(url_for("profile"))


@app.route("/profile/password", methods=["POST"])
@login_required
def update_password():
    db = get_db()
    user_id = session["user_id"]

    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirmation = request.form.get("confirmation", "")

    user = db.execute(
        "SELECT hash FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    if user is None or not check_password_hash(user["hash"], current_password):
        flash("Mot de passe actuel incorrect.")
        return redirect(url_for("profile"))

    if not new_password:
        flash("Le nouveau mot de passe est obligatoire.")
        return redirect(url_for("profile"))

    if new_password != confirmation:
        flash("Les mots de passe ne correspondent pas.")
        return redirect(url_for("profile"))

    db.execute(
        "UPDATE users SET hash = ? WHERE id = ?",
        (generate_password_hash(new_password), user_id),
    )
    db.commit()

    flash("Mot de passe mis à jour.")
    return redirect(url_for("profile"))


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html")
if __name__ == "__main__":
    app.run(debug=True)