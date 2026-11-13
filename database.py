import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "escalap1.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Policial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            re TEXT NOT NULL UNIQUE,
            posto_grad TEXT NOT NULL,
            nome_guerra TEXT NOT NULL,
            perfil TEXT NOT NULL DEFAULT 'operador_p1',
            senha_hash TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Afastamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policial_id INTEGER NOT NULL,
            motivo TEXT NOT NULL,
            data_inicio TEXT NOT NULL,
            data_fim TEXT NOT NULL,
            FOREIGN KEY (policial_id) REFERENCES Policial(id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS EscalaServico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policial_id INTEGER NOT NULL,
            data_servico TEXT NOT NULL,
            turno TEXT NOT NULL,
            viatura_posto TEXT NOT NULL,
            FOREIGN KEY (policial_id) REFERENCES Policial(id)
        );
    """)

    # Carga inicial fictícia para demonstração e testes
    cursor.execute("SELECT COUNT(*) FROM Policial")
    if cursor.fetchone()[0] == 0:
        senha_padrao = generate_password_hash("12345678")
        policiais = [
            ("148920-1", "Cb PM", "Silva", "operador_p1", senha_padrao, 1),
            ("195432-8", "Sd PM", "Oliveira", "operador_p1", senha_padrao, 1),
            ("132110-4", "Cb PM", "Santos", "chefia_p1", senha_padrao, 1),
            ("188741-2", "Sd PM", "Pereira", "operador_p1", senha_padrao, 1),
        ]
        cursor.executemany(
            "INSERT INTO Policial (re, posto_grad, nome_guerra, perfil, senha_hash, ativo) VALUES (?, ?, ?, ?, ?, ?)",
            policiais
        )
        # Afasta o Sd PM Oliveira (id=2) em férias para testar o bloqueio
        cursor.execute(
            "INSERT INTO Afastamento (policial_id, motivo, data_inicio, data_fim) VALUES (?, ?, ?, ?)",
            (2, "Férias", "2026-11-10", "2026-11-25")
        )

    conn.commit()
    conn.close()
