"""Test backend StudyFlow (page Tasks + pages principales).

Utilise une base SQLite temporaire : studyflow.db n'est PAS modifiée.
Lancer depuis le dossier du projet :  python test_tasks.py
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import helpers  # noqa: E402

_tmp = tempfile.TemporaryDirectory()
helpers.DATABASE = Path(_tmp.name) / "test.db"  # base temporaire

from werkzeug.security import generate_password_hash  # noqa: E402

import app as studyflow  # noqa: E402  (init_db s'exécute sur la base temporaire)

app = studyflow.app
app.config["TESTING"] = True

results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition)))
    suffix = f"  -> {detail}" if (detail and not condition) else ""
    print(("OK    " if condition else "ECHEC ") + name + suffix)


def db():
    conn = sqlite3.connect(helpers.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def html(resp):
    return resp.get_data(as_text=True)


# --- Création de deux utilisateurs de test ---
conn = db()
for name in ("test_a", "test_b"):
    conn.execute(
        "INSERT INTO users (username, hash) VALUES (?, ?)",
        (name, generate_password_hash("pw12345")),
    )
conn.commit()
conn.close()

a = app.test_client()
b = app.test_client()

# --- Accès protégé ---
r = a.get("/tasks")
check("/tasks sans connexion -> redirection /login", r.status_code == 302 and "/login" in r.headers["Location"])

# --- Login / Register ---
check("GET /login -> 200", a.get("/login").status_code == 200)
r = a.post("/login", data={"username": "test_a", "password": "mauvais"})
check("Login mauvais mot de passe refusé", r.status_code == 200 and "Identifiants incorrects" in html(r))
r = a.post("/login", data={"username": "test_a", "password": "pw12345"})
check("Login valide -> redirection", r.status_code == 302)
b.post("/login", data={"username": "test_b", "password": "pw12345"})
r = app.test_client().get("/register")
check("Route /register existe (200)", r.status_code == 200, f"statut {r.status_code} : route absente de app.py ?")

# --- Pages principales ---
for path in ("/", "/subjects", "/tasks", "/tasks/new", "/exams", "/calendar"):
    r = a.get(path)
    check(f"GET {path} -> 200", r.status_code == 200, f"statut {r.status_code}")

# --- État vide ---
check("Tasks : état vide affiché", "Aucune tâche pour le moment" in html(a.get("/tasks")))

# --- Matières ---
a.post("/subjects/new", data={"name": "Droit Civil", "color": "#ff0000"})
a.post("/subjects/new", data={"name": "Sans couleur", "color": ""})
conn = db()
subj = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM subjects")}
conn.close()
check("Matières créées", len(subj) == 2)
sid = subj.get("Droit Civil")

# --- Ajouter une tâche ---
r = a.post("/tasks/new", data={"title": "", "priority": "high"})
check("Ajout sans titre refusé", "titre de la tâche est obligatoire" in html(r))
a.post("/tasks/new", data={"title": "Réviser chapitre 1", "subject_id": sid, "priority": "high",
                           "status": "todo", "due_date": "2026-10-14"})
a.post("/tasks/new", data={"title": "Tâche libre", "priority": "nimportequoi", "status": "doing"})
r = a.post("/tasks/new", data={"title": "Matière invalide", "subject_id": "9999"})
check("Ajout avec matière invalide refusé", "Matière invalide" in html(r))

conn = db()
rows = {r["title"]: dict(r) for r in conn.execute("SELECT * FROM tasks")}
conn.close()
check("2 tâches enregistrées", len(rows) == 2, str(list(rows)))
check("Priorité invalide normalisée en medium", rows.get("Tâche libre", {}).get("priority") == "medium")

# --- Affichage ---
page = html(a.get("/tasks"))
check("Titre visible", "Réviser chapitre 1" in page)
check("Couleur de matière (#ff0000)", "#ff0000" in page)
check("Date formatée '14 oct.'", "14 oct." in page)
check("Tâche sans date affiche '—'", "—" in page)
check("Tâche sans matière : 'Aucune matière'", "Aucune matière" in page)
check("data-priority=high présent", 'data-priority="high"' in page)
check("data-status=doing présent", 'data-status="doing"' in page)
check("Script tasks.js référencé", "js/tasks.js" in page)
check("Fichier static/js/tasks.js existe", (ROOT / "static" / "js" / "tasks.js").exists())

# --- Modifier ---
tid = rows["Réviser chapitre 1"]["id"]
check("GET edit -> 200", a.get(f"/tasks/{tid}/edit").status_code == 200)
a.post(f"/tasks/{tid}/edit", data={"title": "Réviser chapitre 2", "subject_id": sid,
                                   "priority": "low", "status": "todo", "due_date": "2026-11-02"})
conn = db()
t = conn.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
conn.close()
check("Modification enregistrée", t["title"] == "Réviser chapitre 2" and t["priority"] == "low"
      and t["due_date"] == "2026-11-02")

# --- Terminer ---
check("GET sur /complete -> 405", a.get(f"/tasks/{tid}/complete").status_code == 405)
a.post(f"/tasks/{tid}/complete")
conn = db()
check("Terminer -> status done",
      conn.execute("SELECT status FROM tasks WHERE id = ?", (tid,)).fetchone()["status"] == "done")
conn.close()
check("Ligne 'is-done' affichée", "is-done" in html(a.get("/tasks")))

# --- Isolation entre utilisateurs ---
b.post(f"/tasks/{tid}/edit", data={"title": "Piraté"})
b.post(f"/tasks/{tid}/complete")
b.post(f"/tasks/{tid}/delete")
conn = db()
t = conn.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
conn.close()
check("Utilisateur B ne peut pas toucher aux tâches de A", t is not None and t["title"] == "Réviser chapitre 2")
check("Utilisateur B ne voit pas les tâches de A", "Réviser chapitre 2" not in html(b.get("/tasks")))

# --- Supprimer ---
check("GET sur /delete -> 405", a.get(f"/tasks/{tid}/delete").status_code == 405)
a.post(f"/tasks/{tid}/delete")
conn = db()
check("Suppression effective",
      conn.execute("SELECT 1 FROM tasks WHERE id = ?", (tid,)).fetchone() is None)
conn.close()

# --- Logout ---
a.get("/logout")
check("Après logout, /tasks redirige", a.get("/tasks").status_code == 302)

# --- Bilan ---
failed = [n for n, ok in results if not ok]
print("\n" + "=" * 50)
if failed:
    print(f"{len(failed)} ECHEC(S) sur {len(results)} :")
    for n in failed:
        print("  -", n)
else:
    print(f"TEST BACKEND RÉUSSI ({len(results)} vérifications)")
_tmp.cleanup()
sys.exit(1 if failed else 0)