# StudyFlow
#### Video Demo:<https://vimeo.com/1230238281?share=copy>
StudyFlow est une application web développée avec **Python et Flask** pour aider les étudiants à organiser leurs études et à suivre leur progression.

## Fonctionnalités

* 🔐 Inscription et connexion
* 📚 Gestion des matières
* ✅ Gestion des tâches
* 📝 Gestion des examens
* 📅 Calendrier
* ⏱️ Pomodoro
* 📖 Gestion des sessions d'étude
* 📊 Statistiques
* 👤 Profil utilisateur
* ⚙️ Paramètres
* 🌙 Thème clair / sombre

## Technologies utilisées

* **Python**
* **Flask**
* **SQLite**
* **HTML5**
* **CSS3**
* **JavaScript**
* **Jinja2**

## Structure du projet

```text
StudyFlow/
│
├── static/
│   ├── css/
│   │   └── style.css
│   │
│   └── js/
│       ├── sta.js
│       └── tasks.js
│
├── templates/
│   ├── auth_layout.html
│   ├── calendar.html
│   ├── exam_form.html
│   ├── exams.html
│   ├── index.html
│   ├── layout.html
│   ├── login.html
│   ├── profile.html
│   ├── register.html
│   ├── settings.html
│   ├── statistics.html
│   ├── study_session_form.html
│   ├── study_sessions.html
│   ├── subject_form.html
│   ├── subjects.html
│   ├── task_form.html
│   ├── tasks.html
│   └── timer.html
│
├── .gitignore
├── app.py
├── helpers.py
├── init_db.py
├── requirements.txt
├── schema.sql
├── studyflow.db
│
└── README.md
```

## Description des principaux fichiers

### `app.py`

Contient le fonctionnement principal de l'application Flask :

* routes
* authentification
* gestion des matières
* gestion des tâches
* gestion des examens
* calendrier
* Pomodoro
* sessions d'étude
* statistiques
* profil
* paramètres

### `helpers.py`

Contient les fonctions utilitaires utilisées par l'application, notamment la protection des pages nécessitant une connexion.

### `schema.sql`

Contient la structure de la base de données SQLite.

### `init_db.py`

Permet d'initialiser la base de données à partir du schéma SQL.

### `templates/`

Contient les pages HTML de l'application utilisant **Jinja2**.

### `static/css/style.css`

Contient le style visuel de StudyFlow.

### `static/js/`

Contient les scripts JavaScript utilisés pour certaines fonctionnalités de l'application.

## Base de données

StudyFlow utilise **SQLite**.

Les principales tables utilisées sont :

* `users`
* `subjects`
* `tasks`
* `exams`
* `study_sessions`

La base de données locale est stockée dans :

```text
studyflow.db
```

## Installation

### 1. Ouvrir le projet

```bash
cd StudyFlow
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Initialiser la base de données

```bash
python init_db.py
```

### 4. Lancer l'application

```bash
python app.py
```

Puis ouvrir dans le navigateur :

```text
http://127.0.0.1:5000
```

###AI Assistance

Pendant le développement de StudyFlow, j'ai utilisé des outils
d'intelligence artificielle, notamment ChatGPT, comme assistants de
programmation pour obtenir des explications, déboguer certaines
erreurs et recevoir des suggestions d'implémentation.

J'ai testé, vérifié et adapté le code utilisé dans le projet.
## Utilisation

Après la création d'un compte, l'étudiant peut :

1. Ajouter ses matières.
2. Créer et gérer ses tâches.
3. Ajouter ses examens.
4. Consulter son calendrier.
5. Utiliser le Pomodoro pour ses sessions de travail.
6. Enregistrer ses sessions d'étude.
7. Consulter ses statistiques.
8. Modifier son profil.
9. Personnaliser l'apparence de l'application.

## Tests

Le projet contient également plusieurs fichiers de test :

```text
test_tasks.py
test_statistics.py
Test study sessions.py
```

Ils permettent de vérifier certaines fonctionnalités de l'application.

## Objectif du projet

StudyFlow a été développé comme projet d'apprentissage afin de mettre en pratique plusieurs notions de développement web :

* programmation Python
* développement avec Flask
* bases de données SQL
* développement frontend
* authentification
* opérations CRUD
* JavaScript
* organisation d'une application web


## Auteur

**Mariem Hammouda**

StudyFlow est un projet personnel développé dans le cadre de mon apprentissage du développement web avec Python, Flask, SQLite, HTML, CSS et JavaScript.

© 2026 Mariem Hammouda. Tous droits réservés.

