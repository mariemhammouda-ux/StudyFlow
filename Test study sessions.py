"""Test des Sessions d'étude. Utilise une base TEMPORAIRE : studyflow.db n'est pas modifiée.
Lancer depuis le dossier du projet :  python test_study_sessions.py"""
import sqlite3
import sys
import tempfile
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


def html(r):
    return r.get_data(as_text=True)


def rows():
    conn = db()
    data = [dict(r) for r in conn.execute("SELECT * FROM study_sessions ORDER BY id")]
    conn.close()
    return data


# Deux utilisateurs, chacun avec une matière
conn = db()
for n in ("test_a", "test_b"):
    conn.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (n, generate_password_hash("pw12345")))
conn.execute("INSERT INTO subjects (user_id, name, color) VALUES (1, 'Droit', '#ff0000')")
conn.execute("INSERT INTO subjects (user_id, name, color) VALUES (2, 'Maths', '#00ff00')")
conn.commit()
conn.close()
SUBJ_A, SUBJ_B = 1, 2

a, b, anon = app.test_client(), app.test_client(), app.test_client()

for path in ("/study-sessions", "/study-sessions/new", "/study-sessions/1/edit"):
    r = anon.get(path)
    check(f"Sans connexion : {path} -> /login", r.status_code == 302 and "/login" in r.headers["Location"])

a.post("/login", data={"username": "test_a", "password": "pw12345"})
b.post("/login", data={"username": "test_b", "password": "pw12345"})

check("Liste vide : 200 + état vide", (lambda r: r.status_code == 200 and "Aucune séance d'étude" in html(r))(a.get("/study-sessions")))
r = a.get("/study-sessions/new")
check("Formulaire : 200, matière de A visible, matière de B absente",
      r.status_code == 200 and "Droit" in html(r) and "Maths" not in html(r))

# --- Ajouter ---
r = a.post("/study-sessions/new", data={"subject_id": SUBJ_A, "session_date": "2026-09-24",
                                        "duration_min": "90", "notes": "Chapitre 1 <b>x</b>"})
check("Ajout valide -> redirection", r.status_code == 302)
s = rows()
check("Séance enregistrée pour A avec la bonne matière/durée/date",
      len(s) == 1 and s[0]["user_id"] == 1 and s[0]["subject_id"] == SUBJ_A
      and s[0]["duration_min"] == 90 and s[0]["started_at"] == "2026-09-24")

# --- Refus ---
def refuse(label, data, msg):
    before = len(rows())
    r = a.post("/study-sessions/new", data=data)
    check(label, r.status_code == 200 and msg in html(r) and len(rows()) == before)

ok = {"subject_id": SUBJ_A, "session_date": "2026-09-24", "duration_min": "30"}
refuse("Matière d'un autre utilisateur refusée", {**ok, "subject_id": SUBJ_B}, "Matière invalide")
refuse("Matière inexistante refusée", {**ok, "subject_id": "9999"}, "Matière invalide")
refuse("Matière '1.0' refusée ou normalisée sans erreur serveur", {**ok, "subject_id": "abc"}, "Matière invalide")
refuse("Date invalide refusée", {**ok, "session_date": "2026-13-45"}, "date de la séance est invalide")
refuse("Date vide refusée", {**ok, "session_date": ""}, "date de la séance est invalide")
refuse("Durée 0 refusée", {**ok, "duration_min": "0"}, "durée doit être")
refuse("Durée texte refusée", {**ok, "duration_min": "abc"}, "durée doit être")
refuse("Durée > 1440 refusée", {**ok, "duration_min": "5000"}, "durée doit être")
r = a.post("/study-sessions/new", data={**ok, "subject_id": "1.0"})
check("subject_id '1.0' : pas d'erreur 500", r.status_code in (200, 302))
conn = db(); conn.execute("DELETE FROM study_sessions WHERE id > 1"); conn.commit(); conn.close()

# --- Ajout sans matière ---
a.post("/study-sessions/new", data={"subject_id": "", "session_date": "2026-09-25", "duration_min": "45"})
check("Ajout sans matière autorisé", rows()[-1]["subject_id"] is None and rows()[-1]["duration_min"] == 45)

# --- Affichage ---
page = html(a.get("/study-sessions"))
check("Liste : matière, durée '1h 30m', date '24 sept. 2026'",
      "Droit" in page and "1h 30m" in page and "24 sept. 2026" in page)
check("Liste : '45 min' et 'Sans matière'", "45 min" in page and "Sans matière" in page)
check("Notes échappées (pas de HTML brut)", "<b>x</b>" not in page and "&lt;b&gt;x&lt;/b&gt;" in page)
check("Total affiché '2h 15m'", "2h 15m au total" in page)
check("Séance la plus récente en premier", page.index("25 sept.") < page.index("24 sept."))
check("Liste de B ne montre pas les séances de A", "Droit" not in html(b.get("/study-sessions")))

# --- Séance du Pomodoro (avec heure) puis modification ---
conn = db()
conn.execute("INSERT INTO study_sessions (user_id, subject_id, started_at, duration_min) VALUES (1, 1, '2026-09-20T14:30:00', 25)")
conn.commit(); conn.close()
pomo_id = rows()[-1]["id"]
check("Séance du Pomodoro visible dans la liste", "20 sept. 2026" in html(a.get("/study-sessions")))
check("GET edit -> 200 avec valeurs", (lambda r: r.status_code == 200 and 'value="2026-09-20"' in html(r) and 'value="25"' in html(r))(a.get(f"/study-sessions/{pomo_id}/edit")))
a.post(f"/study-sessions/{pomo_id}/edit", data={"subject_id": "", "session_date": "2026-09-21", "duration_min": "50", "notes": "modifiée"})
m = [x for x in rows() if x["id"] == pomo_id][0]
check("Modification enregistrée, heure du Pomodoro conservée",
      m["started_at"] == "2026-09-21T14:30:00" and m["duration_min"] == 50 and m["notes"] == "modifiée" and m["subject_id"] is None)
r = a.post(f"/study-sessions/{pomo_id}/edit", data={"subject_id": SUBJ_B, "session_date": "2026-09-21", "duration_min": "50"})
check("Modification avec matière d'un autre refusée",
      "Matière invalide" in html(r) and [x for x in rows() if x["id"] == pomo_id][0]["subject_id"] is None)

# --- Isolation ---
before = rows()
r = b.get(f"/study-sessions/{pomo_id}/edit")
check("B ne peut pas ouvrir l'édition d'une séance de A", r.status_code == 302)
b.post(f"/study-sessions/{pomo_id}/edit", data={"subject_id": "", "session_date": "2026-01-01", "duration_min": "1", "notes": "piraté"})
b.post(f"/study-sessions/{pomo_id}/delete")
check("B ne peut ni modifier ni supprimer une séance de A", rows() == before)
check("GET sur /delete -> 405", a.get(f"/study-sessions/{pomo_id}/delete").status_code == 405)

# --- Suppression ---
a.post(f"/study-sessions/{pomo_id}/delete")
check("Suppression effective", all(x["id"] != pomo_id for x in rows()))
r = a.post(f"/study-sessions/{pomo_id}/delete", follow_redirects=True)
check("Supprimer une séance inexistante : message 'introuvable'", "introuvable" in html(r))

# --- Compatibilité avec les statistiques (date(started_at)) ---
conn = db()
n = conn.execute("SELECT COUNT(*) c FROM study_sessions WHERE user_id = 1 AND date(started_at) = '2026-09-24'").fetchone()["c"]
conn.close()
check("date(started_at) fonctionne avec une date sans heure", n == 1)

failed = [n for n, ok in results if not ok]
print("\n" + "=" * 50)
print(f"{len(failed)} ECHEC(S) sur {len(results)}" if failed else f"TEST SESSIONS RÉUSSI ({len(results)} vérifications)")
for n in failed:
    print("  -", n)
_tmp.cleanup()
sys.exit(1 if failed else 0)