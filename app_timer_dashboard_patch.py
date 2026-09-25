# ============================================================
# À METTRE dans app.py : REMPLACE l'ancienne fonction timer_page()
# (de @app.route("/timer") jusqu'à son return render_template(...)).
# Ne touche PAS à save_timer_session(), qui reste identique.
# Utilise MOIS_COURT (patch Examens) et format_minutes() (patch Sessions d'étude).
# ============================================================

DAILY_GOAL_SESSIONS = 8  # Aucun système de réglage n'existe encore : constante pour le moment.


@app.route("/timer")
@login_required
def timer_page():
    db = get_db()
    user_id = session["user_id"]
    today = date.today()
    yesterday = today - timedelta(days=1)

    subjects = db.execute(
        "SELECT id, name FROM subjects WHERE user_id = ? ORDER BY name COLLATE NOCASE",
        (user_id,),
    ).fetchall()

    # ---------- Aujourd'hui : sessions + temps de focus ----------
    today_stats = db.execute(
        """
        SELECT COUNT(*) AS sessions_count,
               COALESCE(SUM(duration_min), 0) AS total_minutes
        FROM study_sessions
        WHERE user_id = ? AND date(started_at) = ?
        """,
        (user_id, today.isoformat()),
    ).fetchone()

    today_sessions = today_stats["sessions_count"]
    today_focus_minutes = today_stats["total_minutes"]

    # Pas de suivi des pauses dans le schéma actuel : valeur fixe, expliquée dans la réponse.
    today_pauses = 0

    goal_percent = min(100, round(today_sessions * 100 / DAILY_GOAL_SESSIONS)) if DAILY_GOAL_SESSIONS else 0

    # ---------- Historique récent : 5 dernières sessions ----------
    recent_rows = db.execute(
        """
        SELECT study_sessions.started_at, study_sessions.duration_min,
               subjects.name AS subject_name
        FROM study_sessions
        LEFT JOIN subjects
               ON subjects.id = study_sessions.subject_id
              AND subjects.user_id = study_sessions.user_id
        WHERE study_sessions.user_id = ?
        ORDER BY study_sessions.started_at DESC, study_sessions.id DESC
        LIMIT 5
        """,
        (user_id,),
    ).fetchall()

    recent_sessions = []
    for row in recent_rows:
        started_at = row["started_at"]
        try:
            session_date = date.fromisoformat(started_at[:10])
        except ValueError:
            session_date = None

        if session_date == today:
            when = "Aujourd'hui"
        elif session_date == yesterday:
            when = "Hier"
        elif session_date is not None:
            when = f"{session_date.day} {MOIS_COURT[session_date.month - 1]}"
        else:
            when = started_at

        # L'heure n'existe que pour les sessions enregistrées par le Pomodoro (format complet avec "T").
        if len(started_at) >= 16 and "T" in started_at:
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
        today_sessions=today_sessions,
        today_focus_minutes=today_focus_minutes,
        today_focus_label=format_minutes(today_focus_minutes),
        today_pauses=today_pauses,
        daily_goal=DAILY_GOAL_SESSIONS,
        goal_percent=goal_percent,
        recent_sessions=recent_sessions,
    )