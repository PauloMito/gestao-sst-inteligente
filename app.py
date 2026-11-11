import os
import sqlite3
import calendar
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

CAMINHO_BANCO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "prestolabor.db",
)

def conectar_banco():
    conexao = sqlite3.connect(CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao

STATUS_1 = "Aguardando a posição do técnico"
STATUS_2 = "Disponível para análise"
STATUS_3 = "Em análise"
STATUS_4 = "Aguardando correção"
STATUS_5 = "Retorno da correção para análise"
STATUS_6 = "Em reanálise"
STATUS_7 = "Avaliação concluída"

STATUS_INICIAL = STATUS_1
STATUS_VALIDOS = {STATUS_1, STATUS_2, STATUS_3, STATUS_4, STATUS_5, STATUS_6, STATUS_7,}

TRANSICOES = {
    (STATUS_1, "disponibilizar", "tecnico"): STATUS_2,
    (STATUS_2, "iniciar_analise", "adenilson"): STATUS_3,
    (STATUS_3, "solicitar_correcao", "adenilson"): STATUS_4,
    (STATUS_4, "devolver_correcao", "tecnico"): STATUS_5,
    (STATUS_5, "iniciar_reanalise", "adenilson"): STATUS_6,
    (STATUS_6, "solicitar_correcao", "adenilson"): STATUS_4,
    (STATUS_3, "concluir_avaliacao", "adenilson"): STATUS_7,
    (STATUS_6, "concluir_avaliacao", "adenilson"): STATUS_7,
}

ACOES_POR_STATUS = {STATUS_1: [("disponibilizar", "Disponibilizar", "tecnico")],
STATUS_2: [("iniciar_analise", "Iniciar análise", "adenilson")],
STATUS_3: [("solicitar_correcao", "Solicitar correção", "adenilson"), ("concluir_avaliacao", "Concluir avaliação", "adenilson"),],
STATUS_4: [("devolver_correcao", "Devolver correção", "tecnico")],
STATUS_5: [("iniciar_reanalise", "Iniciar reanálise", "adenilson")],
STATUS_6: [("solicitar_correcao", "Solicitar nova correção", "adenilson"), ("concluir_avaliacao", "Concluir avaliação", "adenilson"),],
STATUS_7: [],}

def criar_tabela():
    """Cria as tabelas e migra empresas existentes para o modelo de ciclos.
    A coluna empresas.status é mantida por compatibilidade com bancos antigos,
    mas o status oficial de cada atendimento passa a ficar em ciclos_atendimento.
    """
    conexao = conectar_banco()
    try:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cnpj TEXT NOT NULL,
                tecnico TEXT NOT NULL,
                unidade TEXT NOT NULL,
                vencimento TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """)

        # Migração leve: adiciona a periodicidade se o banco já existia.
        colunas = {
            coluna["name"]
            for coluna in conexao.execute("PRAGMA table_info(empresas)").fetchall()
        }
        if "periodicidade" not in colunas:
            conexao.execute(
                "ALTER TABLE empresas ADD COLUMN periodicidade TEXT NOT NULL DEFAULT 'anual'"
            )

        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS ciclos_atendimento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                ano_referencia INTEGER NOT NULL,
                vencimento TEXT NOT NULL,
                status TEXT NOT NULL,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id) ON DELETE CASCADE,
                UNIQUE (empresa_id, ano_referencia)
            )
            """
        )
        conexao.execute(
            "CREATE INDEX IF NOT EXISTS idx_ciclos_ano_vencimento "
            "ON ciclos_atendimento (ano_referencia, vencimento)"
        )

        # Migra cada empresa antiga: o status existente é preservado no primeiro
        # ciclo, correspondente ao ano do vencimento originalmente cadastrado.
        empresas_antigas = conexao.execute(
            "SELECT id, vencimento, status FROM empresas"
        ).fetchall()
        for empresa in empresas_antigas:
            try:
                vencimento_base = date.fromisoformat(empresa["vencimento"])
            except (TypeError, ValueError):
                # Não cria ciclo com data inválida. A empresa continua no banco
                # para que o dado possa ser corrigido sem perda de cadastro.
                continue

            status_legado = empresa["status"]
            if status_legado not in STATUS_VALIDOS:
                status_legado = STATUS_INICIAL

            vencimento_ciclo = calcular_vencimento_anual(
                vencimento_base, vencimento_base.year
            )
            conexao.execute(
                """
                INSERT OR IGNORE INTO ciclos_atendimento
                    (empresa_id, ano_referencia, vencimento, status)
                VALUES (?, ?, ?, ?)
                """,
                (
                    empresa["id"],
                    vencimento_base.year,
                    vencimento_ciclo.isoformat(),
                    status_legado,
                ),
            )

        conexao.commit()
    finally:
        conexao.close()

def listar_empresas():
    """Lista os cadastros permanentes, mostrando o status do ciclo mais recente.
    A listagem é mantida para facilitar a integração com o template inicial.
    Os painéis operacionais devem usar o status do ciclo específico.
    """
    conexao = conectar_banco()
    try:
        registros = conexao.execute(
            """
            SELECT
                e.id, e.nome, e.cnpj, e.tecnico, e.unidade,
                e.vencimento, e.periodicidade,
                COALESCE(
                    (SELECT c.status
                     FROM ciclos_atendimento c
                     WHERE c.empresa_id = e.id
                     ORDER BY c.ano_referencia DESC
                     LIMIT 1),
                    e.status
                ) AS status
            FROM empresas e
            ORDER BY e.id DESC
            """
        ).fetchall()
        return [dict(registro) for registro in registros]
    finally:
        conexao.close()

def calcular_vencimento_anual(vencimento_original, ano_consulta):
    """Calcula a ocorrência anual, tratando datas como 29 de fevereiro."""
    ultimo_dia = calendar.monthrange(ano_consulta, vencimento_original.month)[1]
    dia = min(vencimento_original.day, ultimo_dia)
    return date(ano_consulta, vencimento_original.month, dia)

def obter_empresa(conexao, empresa_id):
    return conexao.execute(
        """
        SELECT id, nome, cnpj, tecnico, unidade, vencimento, periodicidade
        FROM empresas
        WHERE id = ?
        """,
        (empresa_id,),
    ).fetchone()

def garantir_ciclo(conexao, empresa_id, ano_referencia):
    """Cria sob demanda o ciclo anual e retorna seu registro.

    Não cria anos futuros em lote. Cada ano passa a existir quando o sistema
    precisa dele, mantendo o horizonte de recorrência aberto.
    """
    empresa = obter_empresa(conexao, empresa_id)
    if empresa is None:
        return None

    try:
        vencimento_base = date.fromisoformat(empresa["vencimento"])
    except (TypeError, ValueError):
        return None

    if ano_referencia < vencimento_base.year:
        return None

    vencimento = calcular_vencimento_anual(vencimento_base, ano_referencia)
    conexao.execute(
        """
        INSERT OR IGNORE INTO ciclos_atendimento
            (empresa_id, ano_referencia, vencimento, status)
        VALUES (?, ?, ?, ?)
        """,
        (empresa_id, ano_referencia, vencimento.isoformat(), STATUS_INICIAL),
    )

    return conexao.execute(
        """
        SELECT id, empresa_id, ano_referencia, vencimento, status
        FROM ciclos_atendimento
        WHERE empresa_id = ? AND ano_referencia = ?
        """,
        (empresa_id, ano_referencia),
    ).fetchone()

def mudar_status(status_atual, acao, usuario):
    chave = (status_atual, acao, usuario)
    if chave not in TRANSICOES:
        raise ValueError("Transição não permitida.")
    return TRANSICOES[chave]

def validar_mes(mes_recebido):
    """Valida YYYY-MM e retorna (texto, datetime); usa o mês atual se inválido."""
    mes_atual = date.today().strftime("%Y-%m")
    try:
        data_mes = datetime.strptime(mes_recebido, "%Y-%m")
        if data_mes.strftime("%Y-%m") != mes_recebido:
            raise ValueError
        return mes_recebido, data_mes
    except (ValueError, TypeError):
        return mes_atual, datetime.strptime(mes_atual, "%Y-%m")

@app.route("/", methods=["GET", "POST"])
def inicio():
    mensagem = ""

    if request.method == "POST":
        acao = request.form.get("acao", "")

        if acao == "cadastrar":
            nome = request.form.get("empresa", "").strip()
            cnpj = request.form.get("cnpj", "").strip()
            tecnico = request.form.get("tecnico", "").strip()
            unidade = request.form.get("unidade", "").strip()
            vencimento_texto = request.form.get("vencimento", "").strip()

            if not all([nome, cnpj, tecnico, unidade, vencimento_texto]):
                mensagem = "Preencha todos os campos do cadastro."
            else:
                try:
                    vencimento_base = date.fromisoformat(vencimento_texto)
                except ValueError:
                    mensagem = "Informe uma data de vencimento válida."
                else:
                    conexao = conectar_banco()
                    try:
                        cursor = conexao.execute(
                            """
                            INSERT INTO empresas
                                (nome, cnpj, tecnico, unidade, vencimento,
                                 status, periodicidade)
                            VALUES (?, ?, ?, ?, ?, ?, 'anual')
                            """,
                            (
                                nome,
                                cnpj,
                                tecnico,
                                unidade,
                                vencimento_base.isoformat(),
                                STATUS_INICIAL,
                            ),
                        )
                        empresa_id = cursor.lastrowid

                        # O primeiro ciclo corresponde ao ano informado no cadastro.
                        garantir_ciclo(conexao, empresa_id, vencimento_base.year)
                        conexao.commit()
                    finally:
                        conexao.close()
                    return redirect(url_for("inicio"))

        # Compatibilidade temporária com formulários antigos que enviem
        # empresa_id. Os templates novos deverão enviar ciclo_id diretamente.
        elif acao == "transicionar":
            try:
                empresa_id = int(request.form.get("empresa_id", ""))
                acao_status = request.form.get("acao_status", "")
                usuario = request.form.get("usuario", "")
                ano_formulario = request.form.get("ano_referencia", "").strip()
                ano_referencia = int(ano_formulario) if ano_formulario else date.today().year

                conexao = conectar_banco()
                try:
                    ciclo = garantir_ciclo(conexao, empresa_id, ano_referencia)
                    if ciclo is None:
                        mensagem = "Empresa não encontrada ou sem ciclo para esse ano."
                    else:
                        novo_status = mudar_status(ciclo["status"], acao_status, usuario)
                        conexao.execute(
                            """
                            UPDATE ciclos_atendimento
                            SET status = ?, atualizado_em = CURRENT_TIMESTAMP
                            WHERE id = ?
                            """,
                            (novo_status, ciclo["id"]),
                        )
                        conexao.commit()
                finally:
                    conexao.close()

                if not mensagem:
                    return redirect(url_for("inicio"))
            except (ValueError, TypeError):
                mensagem = "Não foi possível realizar essa transição."

    return render_template(
        "index.html",
        empresas=listar_empresas(),
        acoes_por_status=ACOES_POR_STATUS,
        mensagem=mensagem,
    )

@app.route("/excluir/<int:empresa_id>", methods=["POST"])
def excluir_empresa(empresa_id):
    conexao = conectar_banco()
    try:
        cursor = conexao.execute(
            "DELETE FROM empresas WHERE id = ?", (empresa_id,)
        )
        conexao.commit()
        if cursor.rowcount == 0:
            return "Empresa não encontrada.", 404
    finally:
        conexao.close()
    return redirect(url_for("inicio"))


# ---------------------------------------------------------------------------
# PAINEL DE ANÁLISE
# ---------------------------------------------------------------------------


@app.route("/adenilson")
def painel_adenilson():
    mes_selecionado, data_mes = validar_mes(request.args.get("mes", ""))
    ano = data_mes.year
    mes = data_mes.month

    if mes == 12:
        proximo_mes_data = date(ano + 1, 1, 1)
    else:
        proximo_mes_data = date(ano, mes + 1, 1)

    if mes == 1:
        data_anterior = date(ano - 1, 12, 1)
    else:
        data_anterior = date(ano, mes - 1, 1)

    mes_anterior = data_anterior.strftime("%Y-%m")
    mes_proximo = proximo_mes_data.strftime("%Y-%m")

    nomes_meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]
    mes_legivel = f"{nomes_meses[mes - 1].capitalize()} de {ano}"

    conexao = conectar_banco()
    try:
        cadastros = conexao.execute(
            """
            SELECT id, nome, cnpj, tecnico, unidade, vencimento, periodicidade
            FROM empresas
            ORDER BY nome ASC
            """
        ).fetchall()

        empresas = []
        for cadastro in cadastros:
            try:
                vencimento_base = date.fromisoformat(cadastro["vencimento"])
            except (TypeError, ValueError):
                continue

            # A recorrência anual mantém o mês-base e só ocorre a partir do
            # ano do vencimento original.
            if ano < vencimento_base.year or vencimento_base.month != mes:
                continue

            ciclo = garantir_ciclo(conexao, cadastro["id"], ano)
            if ciclo is None:
                continue

            empresa = dict(cadastro)
            empresa["id"] = cadastro["id"]  # ID do cadastro da empresa
            empresa["empresa_id"] = cadastro["id"]
            empresa["ciclo_id"] = ciclo["id"]
            empresa["ano_referencia"] = ciclo["ano_referencia"]
            empresa["vencimento"] = ciclo["vencimento"]
            empresa["status"] = ciclo["status"]
            empresas.append(empresa)

        conexao.commit()
    finally:
        conexao.close()

    indicadores = {
        "disponiveis": sum(e["status"] == STATUS_2 for e in empresas),
        "em_analise": sum(e["status"] == STATUS_3 for e in empresas),
        "aguardando_correcao": sum(e["status"] == STATUS_4 for e in empresas),
        "concluidas": sum(e["status"] == STATUS_7 for e in empresas),
    }

    return render_template(
        "adenilson.html",
        empresas=empresas,
        indicadores=indicadores,
        acoes_por_status=ACOES_POR_STATUS,
        mes_selecionado=mes_selecionado,
        mes_anterior=mes_anterior,
        mes_proximo=mes_proximo,
        mes_legivel=mes_legivel,
    )


@app.route("/adenilson/<int:ciclo_id>/transicionar", methods=["POST"])
def adenilson_transicionar(ciclo_id):
    acao = request.form.get("acao_status", "")
    mes = request.form.get("mes", "")
    acoes_permitidas = {
        "iniciar_analise",
        "solicitar_correcao",
        "iniciar_reanalise",
        "concluir_avaliacao",
    }
    if acao not in acoes_permitidas:
        return "Ação não permitida.", 400

    conexao = conectar_banco()
    try:
        ciclo = conexao.execute(
            "SELECT id, status FROM ciclos_atendimento WHERE id = ?",
            (ciclo_id,),
        ).fetchone()
        if ciclo is None:
            return "Ciclo de atendimento não encontrado.", 404

        try:
            novo_status = mudar_status(ciclo["status"], acao, "adenilson")
        except ValueError:
            return "Transição de status não permitida.", 400

        conexao.execute(
            """
            UPDATE ciclos_atendimento
            SET status = ?, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (novo_status, ciclo_id),
        )
        conexao.commit()
    finally:
        conexao.close()

    mes_retorno, _ = validar_mes(mes)
    return redirect(url_for("painel_adenilson", mes=mes_retorno))


# ---------------------------------------------------------------------------
# PAINEL DO TÉCNICO
# ---------------------------------------------------------------------------


@app.route("/tecnico")
def painel_tecnico():
    # O painel do técnico usa o mesmo horizonte mensal do painel do Adenilson.
    mes_selecionado, data_mes = validar_mes(request.args.get("mes", ""))
    ano = data_mes.year
    mes = data_mes.month

    if mes == 12:
        proximo_mes_data = date(ano + 1, 1, 1)
    else:
        proximo_mes_data = date(ano, mes + 1, 1)

    if mes == 1:
        data_anterior = date(ano - 1, 12, 1)
    else:
        data_anterior = date(ano, mes - 1, 1)

    mes_anterior = data_anterior.strftime("%Y-%m")
    mes_proximo = proximo_mes_data.strftime("%Y-%m")

    nomes_meses = [
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ]
    mes_legivel = f"{nomes_meses[mes - 1].capitalize()} de {ano}"

    conexao = conectar_banco()
    try:
        cadastros = conexao.execute(
            """
            SELECT id, nome, cnpj, tecnico, unidade, vencimento, periodicidade
            FROM empresas
            ORDER BY nome ASC
            """
        ).fetchall()

        empresas = []
        for cadastro in cadastros:
            try:
                vencimento_base = date.fromisoformat(cadastro["vencimento"])
            except (TypeError, ValueError):
                continue

            # Não apresenta ciclos antes do ano-base nem em meses diferentes
            # do mês de vencimento contratado.
            if ano < vencimento_base.year or vencimento_base.month != mes:
                continue

            ciclo = garantir_ciclo(conexao, cadastro["id"], ano)
            if ciclo is None:
                continue

            empresa = dict(cadastro)
            empresa["empresa_id"] = cadastro["id"]
            empresa["ciclo_id"] = ciclo["id"]
            empresa["ano_referencia"] = ciclo["ano_referencia"]
            empresa["vencimento"] = ciclo["vencimento"]
            empresa["status"] = ciclo["status"]
            empresas.append(empresa)

        conexao.commit()
    finally:
        conexao.close()

    indicadores = {
        "aguardando": sum(e["status"] == STATUS_1 for e in empresas),
        "aguardando_correcao": sum(e["status"] == STATUS_4 for e in empresas),
        "total": len(empresas),
    }

    return render_template(
        "tecnico.html",
        empresas=empresas,
        indicadores=indicadores,
        STATUS_1=STATUS_1,
        STATUS_2=STATUS_2,
        STATUS_3=STATUS_3,
        STATUS_4=STATUS_4,
        STATUS_5=STATUS_5,
        STATUS_6=STATUS_6,
        STATUS_7=STATUS_7,
        mes_selecionado=mes_selecionado,
        mes_anterior=mes_anterior,
        mes_proximo=mes_proximo,
        mes_legivel=mes_legivel,
    )

@app.route("/tecnico/<int:ciclo_id>/disponibilizar", methods=["POST"])
def tecnico_disponibilizar(ciclo_id):
    return _transicionar_ciclo_tecnico(ciclo_id, "disponibilizar")


@app.route("/tecnico/<int:ciclo_id>/devolver-correcao", methods=["POST"])
def tecnico_devolver_correcao(ciclo_id):
    return _transicionar_ciclo_tecnico(ciclo_id, "devolver_correcao")


def _transicionar_ciclo_tecnico(ciclo_id, acao):
    # O mês consultado vem oculto no formulário para que, após a ação,
    # o técnico retorne exatamente ao mesmo período do calendário.
    mes = request.form.get("mes", "")
    conexao = conectar_banco()
    try:
        ciclo = conexao.execute(
            "SELECT id, status FROM ciclos_atendimento WHERE id = ?",
            (ciclo_id,),
        ).fetchone()
        if ciclo is None:
            return "Ciclo de atendimento não encontrado.", 404

        try:
            novo_status = mudar_status(ciclo["status"], acao, "tecnico")
        except ValueError:
            return "Transição de status não permitida.", 400

        conexao.execute(
            """
            UPDATE ciclos_atendimento
            SET status = ?, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (novo_status, ciclo_id),
        )
        conexao.commit()
    finally:
        conexao.close()

    mes_retorno, _ = validar_mes(mes)
    return redirect(url_for("painel_tecnico", mes=mes_retorno))


# Cria as tabelas e executa a migração ao importar a aplicação.
criar_tabela()


if __name__ == "__main__":
    app.run(debug=True)
