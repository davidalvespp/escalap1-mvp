import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from database import init_db, get_connection

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "escalap1-chave-secreta-segura-2026")

# Inicializa o esquema e a carga base ao carregar o modulo
init_db()


def validar_disponibilidade(conn, policial_id: int, data_servico: str, turno: str) -> tuple[bool, str]:
    """
    Motor sincrono de validacao de regras de negocio da Secao P1.
    Bloqueia alocacoes se o militar estiver afastado ou ja escalado no mesmo turno/data.
    """
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
        return render_template("login.html"), 401

    return render_template("login.html")


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
    return render_template("nova_escala.html", policiais=policiais)


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
    return render_template("visualizar_escala.html", escalas=escalas)


if __name__ == "__main__":
    app.run(debug=False)


if __name__ == "__main__":
    app.run(debug=False)
