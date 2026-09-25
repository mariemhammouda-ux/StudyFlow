"""Test de la page Statistiques. Base TEMPORAIRE : studyflow.db n'est pas modifiée.
Lancer depuis le dossier du projet :  python test_statistics.py"""
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import helpers  # noqa: E402

_tmp = tempfile.TemporaryDirectory()
helpers.DATABASE = Path(_tmp.name) / "test.db"

from werkzeug.security import generate_password_hash  # noqa: E402

import app as studyflow  # noqa: E402

app = studyflow.app
app.config["TESTING"] = True
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(("OK    " if cond else "ECHEC ") + name + (f"  -> {detail}" if detail and not cond else ""))


def db():
    conn = sqlite3.connect(helpers.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def page(client):
    r = client.get("/statistics")
    return r.status_code, r.get_data(as_text=True)


def add(user, subject, day, minutes):
    conn = db()
    conn.execute("INSERT INTO study_sessions (user_id, subject_id, started_at, duration_min) VALUES (?,?,?,?)",
                 (user, subject, day, minutes))
    conn.commit(); conn.close()


conn = db()
for n in ("test_a", "test_b", "test_c"):
    conn.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (n, generate_password_hash("pw12345")))
conn.execute("INSERT INTO subjects (user_id, name, color) VALUES (1, 'Droit', '#ff0000')")
conn.execute("INSERT INTO subjects (user_id, name, color) VALUES (1, 'Maths', '#00ff00')")
conn.execute("INSERT INTO subjects (user_id, name) VALUES (2, 'Algo')")
conn.execute("INSERT INTO tasks (user_id, subject_id, title, status) VALUES (1, 1, 'T1', 'done')")
conn.execute("INSERT INTO tasks (user_id, subject_id, title, status) VALUES (1, 1, 'T2', 'todo')")
conn.commit(); conn.close()

a, b, c, anon = (app.test_client() for _ in range(4))
for cl, n in ((a, "test_a"), (b, "test_b"), (c, "test_c")):
    cl.post("/login", data={"username": n, "password": "pw12345"})

r = anon.get("/statistics")
check("Déconnecté : redirection vers /login", r.status_code == 302 and "/login" in r.headers["Location"])

# --- Aucune session ---
code, html = page(c)
check("Aucune session : page 200 + état vide", code == 200 and "Aucune session d'étude" in html)
code, html = page(a)
check("Aucune session (avec matières/tâches) : 200 et '1/2' tâches", code == 200 and "Aucune session d'étude" in html and "1/2" in html)

# --- Une seule session ---
today = date.today()
add(1, 1, today.isoformat(), 60)
code, html = page(a)
check("Une session : 200, total et moyenne '1h 00m', 1 session", code == 200 and html.count("1h 00m") >= 2 and "Droit" in html)
check("Une session : matière la plus étudiée = Droit", "Matière la plus étudiée" in html and "Droit" in html)

# --- Plusieurs sessions, matières, jours ---
add(1, 1, today.isoformat(), 30)                                  # même jour
add(1, 2, (today - timedelta(days=40)).isoformat(), 45)           # autre mois
add(1, None, (today - timedelta(days=3)).isoformat(), 15)        # sans matière
add(1, 1, today.isoformat() + "T14:30:00", 20)                    # format du Pomodoro
code, html = page(a)
check("Total = 170 min -> '2h 50m'", "2h 50m" in html)
check("Moyenne = 34 min -> '34 min'", "34 min" in html)
check("Sessions : 5", '<div class="st-card-value">5</div>' in html)
check("Sans matière + Maths listées", "Sans matière" in html and "Maths" in html)
check("Barre d'aujourd'hui = 60+30+20 = '1h 50m'", 'st-bar-value">1h 50m' in html)
check("Courbe : polyline + 6 points de mois", "<polyline points=" in html and html.count('class="st-dot"') == 6)
check("Mois actuel dans les libellés", studyflow.MOIS_COURT[today.month - 1].capitalize() in html)
check("Tâches par matière : Droit 1/2, Maths 0/0", "1/2" in html and "0/0" in html)
check("Matière la plus étudiée ignore 'Sans matière'", 'st-card-value st-card-value-text">Droit' in html)

# --- Isolation ---
add(2, 3, today.isoformat(), 15)
code, html = page(b)
check("B voit ses données (Algo, 15 min)", code == 200 and "Algo" in html and "15 min" in html)
check("B ne voit rien de A (Droit, Maths, 2h 50m)", "Droit" not in html and "Maths" not in html and "2h 50m" not in html)
code, html = page(a)
check("A ne voit rien de B (Algo)", "Algo" not in html)

# --- Cas limites ---
conn = db(); conn.execute("DELETE FROM subjects WHERE id = 1"); conn.commit(); conn.close()
code, html = page(a)
check("Matière supprimée : page OK, sessions en 'Sans matière'", code == 200 and "Sans matière" in html and "Droit" not in html)

failed = [n for n, ok in results if not ok]
print("\n" + "=" * 50)
print(f"{len(failed)} ECHEC(S) sur {len(results)}" if failed else f"TEST STATISTIQUES RÉUSSI ({len(results)} vérifications)")
for n in failed:
    print("  -", n)
_tmp.cleanup()
sys.exit(1 if failed else 0)