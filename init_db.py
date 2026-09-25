"""Crée studyflow.db et les tables. À lancer une fois : python init_db.py"""

from helpers import DATABASE, init_db

if __name__ == "__main__":
    init_db()
    print(f"Base créée : {DATABASE}")
