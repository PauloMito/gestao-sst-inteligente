STATUS_1 = "Aguardando a posição do técnico"
STATUS_2 = "Disponível para análise"
STATUS_3 = "Em análise"
STATUS_4 = "Aguardando correção"
STATUS_5 = "Retorno da correção para análise"
STATUS_6 = "Em reanálise"
STATUS_7 = "Avaliação concluída, produção dos documentos liberada"

TRANSICOES = {
    # O técnico disponibiliza a renovação - Tupla com chave(estamos verificando três condições simultaneamente)
    (STATUS_1, "disponibilizar", "tecnico"): STATUS_2,
    # Adenilson inicia a primeira análise
    (STATUS_2, "iniciar_analise", "adenilson"): STATUS_3,
    # Adenilson solicita correção durante a análise
    (STATUS_3, "solicitar_correcao", "adenilson"): STATUS_4,
    # O técnico devolve a correção
    (STATUS_4, "devolver_correcao", "tecnico"): STATUS_5,
    # Adenilson inicia a reanálise
    (STATUS_5, "iniciar_reanalise", "adenilson"): STATUS_6,
    # Adenilson solicita nova correção durante a reanálise
    (STATUS_6, "solicitar_correcao", "adenilson"): STATUS_4,
    # Adenilson conclui a primeira análise
    (STATUS_3, "concluir_avaliacao", "adenilson"): STATUS_7,
    # Adenilson conclui a reanálise
    (STATUS_6, "concluir_avaliacao", "adenilson"): STATUS_7,
}

def mudar_status(status_atual, acao, usuario):
    chave = (status_atual, acao, usuario)
    if chave not in TRANSICOES:
        raise ValueError(
            f"Transição não permitida!\n"
            f"Status atual: {status_atual}\n"
            f"Ação solicitada: {acao}\n"
            f"Usuário: {usuario}"
        )
    return TRANSICOES[chave]