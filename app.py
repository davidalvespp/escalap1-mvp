import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database import get_connection, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "chave-dev-escalap1-segura")

def validar_disponibilidade(policial_id, data_servico, turno):
    conn = get_connection()
    # 1. Verifica afastamentos ativos na data do serviço (RF03)
    afastamento = conn.execute(
        """
        SELECT motivo, data_inicio, data_fim FROM Afastamento
        WHERE policial_id = ? AND ? BETWEEN data_inicio AND data_fim
        """,
        (policial_id, data_servico)
    ).fetchone()

    if afastamento:
        conn.close()
        return False, f"BLOQUEIO DE ESCALA: Policial em gozo de {afastamento['motivo']} até {afastamento['data_fim']}."

    # 2. Verifica duplicidade de turno na mesma data
    choque = conn.execute(
        """
        SELECT id FROM EscalaServico
        WHERE policial_id = ? AND data_servico = ? AND turno = ?
        """,
        (policial_id, data_servico, turno)
    ).fetchone()
    conn.close()

    if choque:
        return False, "BLOQUEIO DE ESCALA: Policial já escalado neste mesmo turno e data."

    return True, "Alocação validada e gravada com sucesso."

@app.route("/")
def index():
    init_db()
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    re = request.form.get("re", "").strip()
    senha = request.form.get("senha", "")
    conn = get_connection()
    policial = conn.execute("SELECT * FROM Policial WHERE re = ? AND ativo = 1", (re,)).fetchone()
    conn.close()

    if policial and check_password_hash(policial["senha_hash"], senha):
        session["usuario_id"] = policial["id"]
        session["usuario_nome"] = f"{policial['posto_grad']} {policial['nome_guerra']}"
        return redirect(url_for("nova_escala"))

    flash("Credenciais inválidas. Verifique seu RE e senha.", "danger")
    return redirect(url_for("index"))

@app.route("/escala/nova", methods=["GET", "POST"])
def nova_escala():
    if "usuario_id" not in session:
        return redirect(url_for("index"))

    conn = get_connection()
    if request.method == "POST":
        policial_id = request.form.get("policial_id")
        data_servico = request.form.get("data_servico")
        turno = request.form.get("turno")
        viatura_posto = request.form.get("viatura_posto", "").strip()

        apto, mensagem = validar_disponibilidade(policial_id, data_servico, turno)
        if apto:
            conn.execute(
                "INSERT INTO EscalaServico (policial_id, data_servico, turno, viatura_posto) VALUES (?, ?, ?, ?)",
                (policial_id, data_servico, turno, viatura_posto)
            )
            conn.commit()
            flash(mensagem, "success")
        else:
            flash(mensagem, "danger")

        conn.close()
        return redirect(url_for("visualizar_escala", data=data_servico))

    policiais = conn.execute("SELECT id, re, posto_grad, nome_guerra FROM Policial WHERE ativo = 1").fetchall()
    conn.close()
    return render_template("nova_escala.html", policiais=policiais)

@app.route("/escala/visualizar")
def visualizar_escala():
    if "usuario_id" not in session:
        return redirect(url_for("index"))

    data_filtro = request.args.get("data", "2026-11-20")
    conn = get_connection()
    escalas = conn.execute(
        """
        SELECT e.data_servico, e.turno, e.viatura_posto, p.posto_grad, p.nome_guerra, p.re
        FROM EscalaServico e
        JOIN Policial p ON e.policial_id = p.id
        WHERE e.data_servico = ?
        """,
        (data_filtro,)
    ).fetchall()
    conn.close()
    return render_template("visualizar_escala.html", escalas=escalas, data_filtro=data_filtro)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=False)
