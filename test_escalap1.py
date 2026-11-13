import os
import pytest
import database
from app import app, validar_disponibilidade

@pytest.fixture
def client(tmp_path):
    # Isola o banco SQLite em diretório temporário para cada execução de teste
    database.DB_PATH = str(tmp_path / "test_escalap1.db")
    database.init_db()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_unitario_bloqueio_afastamento_ferias(client):
    """Teste Unitário: Deve bloquear Sd PM Oliveira (id=2) em gozo de férias até 25/11/2026."""
    apto, msg = validar_disponibilidade(policial_id=2, data_servico="2026-11-20", turno="Diurno (06h-18h)")
    assert apto is False
    assert "BLOQUEIO DE ESCALA" in msg
    assert "Férias" in msg

def test_unitario_alocacao_policial_apto(client):
    """Teste Unitário: Deve aprovar Cb PM Santos (id=3) sem afastamentos ativos."""
    apto, msg = validar_disponibilidade(policial_id=3, data_servico="2026-11-20", turno="Diurno (06h-18h)")
    assert apto is True
    assert "validada" in msg

def test_integracao_login_e_bloqueio_rota_escala(client):
    """Teste de Integração: Autenticação segura + submissão POST bloqueada + conferência na grade."""
    # 1. Tentativa de login inválido
    resp_invalido = client.post("/login", data={"re": "148920-1", "senha": "errada"}, follow_redirects=True)
    assert "Credenciais inválidas" in resp_invalido.get_data(as_text=True)

    # 2. Login válido (Cb PM Silva)
    resp_valido = client.post("/login", data={"re": "148920-1", "senha": "12345678"}, follow_redirects=True)
    assert resp_valido.status_code == 200
    assert "Alocação de Policial" in resp_valido.get_data(as_text=True)

    # 3. Submissão de alocação válida (Cb PM Santos - id=3)
    resp_ok = client.post("/escala/nova", data={
        "policial_id": "3",
        "data_servico": "2026-11-20",
        "turno": "Diurno (06h-18h)",
        "viatura_posto": "VTR M-14101 — Radiopatrulha"
    }, follow_redirects=True)
    html_ok = resp_ok.get_data(as_text=True)
    assert "Alocação validada e gravada com sucesso" in html_ok
    assert "Santos" in html_ok

    # 4. Submissão de alocação bloqueada por férias (Sd PM Oliveira - id=2)
    resp_bloqueio = client.post("/escala/nova", data={
        "policial_id": "2",
        "data_servico": "2026-11-20",
        "turno": "Diurno (06h-18h)",
        "viatura_posto": "VTR M-14102 — Radiopatrulha"
    }, follow_redirects=True)
    html_bloqueio = resp_bloqueio.get_data(as_text=True)
    assert "BLOQUEIO DE ESCALA" in html_bloqueio
    assert "Oliveira" not in html_bloqueio

def test_integracao_bloqueio_duplicidade_turno_e_logout(client):
    """Teste de Integração: Bloqueio de turno duplicado na mesma data e encerramento de sessão."""
    client.post("/login", data={"re": "148920-1", "senha": "12345678"})
    client.post("/escala/nova", data={
        "policial_id": "4",
        "data_servico": "2026-11-20",
        "turno": "Noturno (18h-06h)",
        "viatura_posto": "Guarda do Quartel"
    })
    # Tenta escalar o mesmo policial novamente no mesmo turno/data
    apto, msg = validar_disponibilidade(policial_id=4, data_servico="2026-11-20", turno="Noturno (18h-06h)")
    assert apto is False
    assert "já escalado" in msg

    resp_logout = client.get("/logout", follow_redirects=True)
    assert "Acesso Restrito" in resp_logout.get_data(as_text=True)
