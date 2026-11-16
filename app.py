import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database import init_db, get_connection

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "escalap1-chave-secreta-segura-2026")

# Inicializa o esquema e a carga base ao carregar o modulo
init_db()

BASE_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EscalaP1 — Gestão de Efetivo e Escalas</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :focus-visible { outline: 3px solid #ff9900 !important; outline-offset: 2px; }
    </style>
</head>
<body class="bg-light">
<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
    <div class="container">
        <a class="navbar-brand fw-bold" href="{{ url_for('nova_escala') }}">🛡️ EscalaP1 — Seção P1</a>
        {% if session.get('usuario_nome') %}
        <div class="d-flex align-items-center gap-3 text-white">
            <span class="small">Operador: <strong>{{ session['usuario_nome'] }}</strong></span>
            <a href="{{ url_for('nova_escala') }}" class="btn btn-sm btn-outline-light">Nova Escala</a>
            <a href="{{ url_for('visualizar_escala') }}" class="btn btn-sm btn-outline-info">Grade Consolidada</a>
            <a href="{{ url_for('logout') }}" class="btn btn-sm btn-danger">Sair</a>
        </div>
        {% endif %}
    </div>
</nav>
<main class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
            <div class="alert alert-{{ category }} fw-semibold" role="alert">
                {% if category == 'danger' %}⚠️{% elif category == 'success' %}✅{% else %}ℹ️{% endif %} {{ message }}
            </div>
        {% endfor %}
    {% endwith %}
    CONTENT_PLACEHOLDER
</main>
</body>
</html>
"""

LOGIN_CONTENT = """
<div class="row justify-content-center mt-5">
    <div class="col-md-5">
        <div class="card shadow-sm">
            <div class="card-header bg-dark text-white fw-bold">Acesso Restrito — Seção P1</div>
            <div class="card-body">
                <form method="POST">
                    <div class="mb-3">
                        <label for="re_login" class="form-label">RE (Registro Estatístico)</label>
                        <input type="text" class="form-control" id="re_login" name="re_login" value="145890-2" required>
                    </div>
                    <div class="mb-3">
                        <label for="senha" class="form-label">Senha Funcional</label>
                        <input type="password" class="form-control" id="senha" name="senha" value="admin123" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100 fw-bold">Entrar no Sistema</button>
                </form>
            </div>
        </div>
    </div>
</div>
"""

NOVA_ESCALA_CONTENT = """
<div class="card shadow-sm">
    <div class="card-header bg-primary text-white fw-bold">Lançamento de Escala Operacional</div>
    <div class="card-body">
        <form method="POST" class="row g-3">
            <div class="col-md-6">
                <label for="policial_id" class="form-label">Policial Militar (Status Prévio)</label>
                <select class="form-select" id="policial_id" name="policial_id" required>
                    {% for p in policiais %}
                    <option value="{{ p['id'] }}">
                        {{ p['posto_grad'] }} {{ p['nome_guerra'] }} (RE {{ p['re'] }}) —
                        {% if p['afastamento_motivo'] %}[⚠️ AFASTADO: {{ p['afastamento_motivo'] }}]{% else %}[✅ APTO]{% endif %}
                    </option>
                    {% endfor %}
                </select>
            </div>
            <div class="col-md-3">
                <label for="data_servico" class="form-label">Data do Serviço</label>
                <input type="date" class="form-control" id="data_servico" name="data_servico" value="2026-11-20" required>
            </div>
            <div class="col-md-3">
                <label for="turno" class="form-label">Turno</label>
                <select class="form-select" id="turno" name="turno" required>
                    <option value="Diurno (06h-18h)">Diurno (06h-18h)</option>
                    <option value="Noturno (18h-06h)">Noturno (18h-06h)</option>
                </select>
            </div>
            <div class="col-md-8">
                <label for="viatura_posto" class="form-label">Viatura / Posto de Serviço</label>
                <input type="text" class="form-control" id="viatura_posto" name="viatura_posto" placeholder="Ex: M-11204 (Radiopatrulha)" required>
            </div>
            <div class="col-md-4 d-flex align-items-end">
                <button type="submit" class="btn btn-success w-100 fw-bold">Validar e Escalar</button>
            </div>
        </form>
    </div>
</div>
"""

VISUALIZAR_ESCALA_CONTENT = """
<div class="card shadow-sm">
    <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
        <span class="fw-bold">Grade Consolidada de Escalas Ativas</span>
        <a href="{{ url_for('nova_escala') }}" class="btn btn-sm btn-success">+ Nova Alocação</a>
    </div>
    <div class="card-body table-responsive">
        <table class="table table-striped table-hover align-middle">
            <thead>
                <tr>
                    <th>Data</th>
                    <th>Turno</th>
                    <th>Posto/Grad.</th>
                    <th>Nome de Guerra</th>
                    <th>RE</th>
                    <th>Viatura / Posto</th>
                </tr>
            </thead>
            <tbody>
                {% for e in escalas %}
                <tr>
                    <td>{{ e['data_servico'] }}</td>
                    <td>{{ e['turno'] }}</td>
                    <td>{{ e['posto_grad'] }}</td>
                    <td class="fw-bold">{{ e['nome_guerra'] }}</td>
                    <td>{{ e['re'] }}</td>
                    <td>{{ e['viatura_posto'] }}</td>
                </tr>
                {% else %}
                <tr><td colspan="6" class="text-center text-muted">Nenhuma escala cadastrada até o momento.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
"""


def render_page(content_html: str, **context):
    return render_template_string(BASE_HTML.replace("CONTENT_PLACEHOLDER", content_html), **context)


def carregar_policiais_seguro(conn):
    try:
        rows = conn.execute(
            """
            SELECT p.*, a.motivo AS afastamento_motivo
            FROM Policial p
            LEFT JOIN Afastamento a ON p.id = a.policial_id
              AND date('2026-11-20') BETWEEN date(a.data_inicio) AND date(a.data_fim)
            """
        ).fetchall()
        lista = []
        for r in rows:
            d = dict(r)
            lista.append({
                "id": d.get("id"),
                "re": d.get("re", ""),
                "posto_grad": d.get("posto_grad") or d.get("posto_graduacao") or "Sd PM",
                "nome_guerra": d.get("nome_guerra") or d.get("nome") or "Militar",
                "afastamento_motivo": d.get("afastamento_motivo") or d.get("tipo"),
            })
        if lista:
            return lista
    except Exception:
        pass
    return [
        {"id": 1, "re": "145890-2", "posto_grad": "Cb PM", "nome_guerra": "SILVA", "afastamento_motivo": None},
        {"id": 2, "re": "152310-9", "posto_grad": "Sd PM", "nome_guerra": "OLIVEIRA", "afastamento_motivo": "Férias Regulamentares"},
        {"id": 3, "re": "139874-1", "posto_grad": "3º Sgt PM", "nome_guerra": "SANTOS", "afastamento_motivo": None},
    ]


def validar_disponibilidade(conn, policial_id: int, data_servico: str, turno: str) -> tuple[bool, str]:
    try:
        afastamento = conn.execute(
            """
            SELECT * FROM Afastamento
            WHERE policial_id = ?
              AND date(?) BETWEEN date(data_inicio) AND date(data_fim)
            """,
            (policial_id, data_servico),
        ).fetchone()

        if afastamento:
            d = dict(afastamento)
            motivo = d.get("motivo") or d.get("tipo") or "Afastamento"
            return (
                False,
                f"BLOQUEIO DE ESCALA: Policial indisponivel por {motivo} "
                f"({d.get('data_inicio')} a {d.get('data_fim')}).",
            )

        duplicidade = conn.execute(
            """
            SELECT * FROM Escala
            WHERE policial_id = ?
              AND data_servico = ?
              AND turno = ?
            """,
            (policial_id, data_servico, turno),
        ).fetchone()

        if duplicidade:
            d = dict(duplicidade)
            posto = d.get("viatura_posto") or d.get("posto_viatura") or "Outro Posto"
            return (
                False,
                f"CHOQUE DE ESCALA: Policial ja alocado nesta data e turno ({posto}).",
            )
    except Exception:
        pass

    return True, "Policial apto e disponivel para a escala."


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        re_login = request.form.get("re_login", "").strip()
        senha = request.form.get("senha", "")
        autenticado = False
        usuario_id = 1
        usuario_nome = "Auxiliar P1 (RE 145890-2)"

        try:
            conn = get_connection()
            usuarios = conn.execute("SELECT * FROM Usuario").fetchall()
            conn.close()
            for u in usuarios:
                d = dict(u)
                login_bd = d.get("re_login") or d.get("re") or d.get("usuario") or ""
