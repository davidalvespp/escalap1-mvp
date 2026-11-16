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


def validar_disponibilidade(conn, policial_id: int, data_servico: str, turno: str) -> tuple[bool, str]:
    afastamento = conn.execute(
        """
        SELECT motivo, data_inicio, data_fim
        FROM Afastamento
        WHERE policial_id = ?
          AND date(?) BETWEEN date(data_inicio) AND date(data_fim)
        """,
        (policial_id, data_servico),
    ).fetchone()

    if afastamento:
        return (
            False,
            f"BLOQUEIO DE ESCALA: Policial indisponivel por {afastamento['motivo']} "
            f"({afastamento['data_inicio']} a {afastamento['data_fim']}).",
        )

    duplicidade = conn.execute(
        """
        SELECT id, viatura_posto
        FROM Escala
        WHERE policial_id = ?
          AND data_servico = ?
          AND turno = ?
        """,
        (policial_id, data_servico, turno),
    ).fetchone()

    if duplicidade:
        return (
            False,
            f"CHOQUE DE ESCALA: Policial ja alocado nesta data e turno ({duplicidade['viatura_posto']}).",
        )

    return True, "Policial apto e disponivel para a escala."


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        re_login = request.form.get("re_login", "").strip()
        senha = request.form.get("senha", "")
        conn = get_connection()
        usuario = conn.execute("SELECT * FROM Usuario WHERE re_login = ?", (re_login,)).fetchone()
        conn.close()

        if usuario and check_password_hash(usuario["senha_hash"], senha):
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]
            return redirect(url_for("nova_escala"))

        flash("Credenciais invalidas. Verifique o RE e a senha funcional.", "danger")
        return render_page(LOGIN_CONTENT), 401

    return render_page(LOGIN_CONTENT)


@app.route("/logout")
def logout():
    session.clear()
    flash("Sessao encerrada com seguranca.", "info")
    return redirect(url_for("login"))


@app.route("/escala/nova", methods=["GET", "POST"])
def nova_escala():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()

    if request.method == "POST":
        policial_id = int(request.form.get("policial_id"))
        data_servico = request.form.get("data_servico", "").strip()
        turno = request.form.get("turno", "").strip()
        viatura_posto = request.form.get("viatura_posto", "").strip()

        apto, mensagem = validar_disponibilidade(conn, policial_id, data_servico, turno)
        if not apto:
            conn.close()
            flash(mensagem, "danger")
            return redirect(url_for("nova_escala"))

        conn.execute(
            """
            INSERT INTO Escala (policial_id, data_servico, turno, viatura_posto, criado_por)
            VALUES (?, ?, ?, ?, ?)
            """,
            (policial_id, data_servico, turno, viatura_posto, session["usuario_id"]),
        )
        conn.commit()
        conn.close()
        flash("Escala validada e registrada com sucesso!", "success")
        return redirect(url_for("visualizar_escala"))

    policiais = conn.execute(
        """
        SELECT p.id, p.re, p.posto_grad, p.nome_guerra, a.motivo AS afastamento_motivo
        FROM Policial p
        LEFT JOIN Afastamento a ON p.id = a.policial_id AND date('2026-11-20') BETWEEN a.data_inicio AND a.data_fim
        WHERE p.ativo = 1
        """
    ).fetchall()
    conn.close()
    return render_page(NOVA_ESCALA_CONTENT, policiais=policiais)


@app.route("/escala/visualizar")
def visualizar_escala():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    escalas = conn.execute(
        """
        SELECT e.id, e.data_servico, e.turno, e.viatura_posto,
               p.re, p.posto_grad, p.nome_guerra
        FROM Escala e
        INNER JOIN Policial p ON e.policial_id = p.id
        ORDER BY e.data_servico ASC, e.turno ASC
        """
    ).fetchall()
    conn.close()
    return render_page(VISUALIZAR_ESCALA_CONTENT, escalas=escalas)


if __name__ == "__main__":
    app.run(debug=False)
