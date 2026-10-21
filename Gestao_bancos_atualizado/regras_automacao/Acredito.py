import pandas as pd
import unicodedata
from datetime import datetime

def processar(df):
    # --- INÍCIO DA CORREÇÃO ---
    # Se o df for um dicionário (ex: várias abas do Excel), pega a primeira aba
    if isinstance(df, dict):
        df = list(df.values())[0]
    cabecalho_padrao = [
        "Nr Proposta", "Nome Cliente", "CPF Cliente", "Idade Cliente", "Grau de escolaridade",
        "Espécie Cliente", "Status Proposta", "Contrato Assinado?", "Produto", "Retenção",
        "RL?", "Convenio", "Corban", "Identificador do Usuário", "Usuário Digitador",
        "Valor Proposta", "Valor Liberado Cliente", "Data Cadastro", "Data Status",
        "Data Integração", "Qtd Parcelas", "Valor Parcela", "Taxa da Operação",
        "Limite pré aprovado", "Seguro", "Valor do seguro", "Plano",
        "Documento pessoal enviado?", "Documento pessoal pendente?", "Campos Pendentes",
        "Comprovante de residência enviado?", "Comprovante de residência pendente?",
        "Selfie enviada?", "Selfie pendente?", "Contracheque enviado?",
        "Contracheque pendente?", "Adicional enviado?", "Adicional pendente?",
        "Saldo Devedor Retornado", "Taxa Recalculada", "Taxa de aceite do Refin",
        "Recusa de Portabilidade CIP", "Data Envio CIP", "Data Retorno Saldo CIP",
        "Valor do Troco", "Valor do Troco Recalculado", "Percentual de Comissão",
        "Restricoes", "Observações", "Seguro aceito", "Seguro obrigatório",
        "Status dos Seguros", "Nome do Plano", "Porcentual de Prêmio", "Contrato Tabela Especial"
    ]
    
    # 1. TRATAMENTO DE UNICODE: Converte as colunas do arquivo (NFD) para o padrão (NFC) e remove espaços extras
    df.columns = [unicodedata.normalize('NFC', str(col)).strip() for col in df.columns]
    
    # 2. Faz a mesma normalização no nosso cabeçalho para garantir que o "match" seja perfeito
    cabecalho_padrao_norm = [unicodedata.normalize('NFC', col).strip() for col in cabecalho_padrao]
    
    # 3. Agora o reindex vai encontrar as colunas corretamente e trazer os dados em vez de deixar vazio!
    df_final = df.reindex(columns=cabecalho_padrao_norm)
    
    # 4. (Segurança) Devolvemos exatamente os nomes da lista original para a saída do Excel
    df_final.columns = cabecalho_padrao
    
    # 5. Gera a chave com a data de hoje
    hoje = datetime.now()
    data_formatada = hoje.strftime("%Y%m%d")
    nome_chave = f"Acredto_Producao_{data_formatada}"
    
    return {nome_chave: df_final}