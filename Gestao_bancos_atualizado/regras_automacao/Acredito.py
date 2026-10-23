import pandas as pd
import unicodedata
from datetime import datetime

CABECALHO_PADRAO = [
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

COLUNA_DATA_INTEGRACAO = "Data Integração"


def _converter_data_integracao(serie):
    """
    Garante que 'Data Integração' seja do tipo data (datetime).
    - Valores que já são data permanecem iguais.
    - Textos que representam data são convertidos para o mesmo dia e horário.
    - Vazios continuam vazios.
    - Se algum texto NÃO puder ser interpretado como data, o valor original é
      mantido (nenhum dado é perdido) e um aviso é exibido.
    """
    # Já é datetime: nada a fazer
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie

    def _converter_valor(valor):
        if pd.isna(valor):
            return pd.NaT
        if isinstance(valor, (datetime, pd.Timestamp)):
            return pd.Timestamp(valor)
        texto = str(valor).strip()
        if texto == "":
            return pd.NaT
        # Formatos ISO (aaaa-mm-dd ...) são lidos como estão; dd/mm/aaaa usa dia primeiro
        dayfirst = "/" in texto
        return pd.to_datetime(texto, dayfirst=dayfirst, errors="coerce")

    convertida = serie.map(_converter_valor)

    # Onde havia valor mas a conversão falhou, preserva o original
    falhas = convertida.isna() & serie.notna() & (serie.astype(str).str.strip() != "")
    if falhas.any():
        print(
            f"AVISO: {int(falhas.sum())} valor(es) de '{COLUNA_DATA_INTEGRACAO}' "
            f"não puderam ser convertidos para data e foram mantidos como estavam."
        )
        convertida = convertida.astype(object)
        convertida[falhas] = serie[falhas]
        return convertida

    return pd.to_datetime(convertida)


def _padronizar(df):
    """Padroniza UM dataframe: normaliza colunas e organiza na ordem do cabeçalho padrão."""
    # Se for um dicionário (várias abas do Excel), pega a primeira aba
    if isinstance(df, dict):
        df = list(df.values())[0]

    df = df.copy()

    # Unicode NFD -> NFC e remove espaços extras nos nomes das colunas
    df.columns = [unicodedata.normalize('NFC', str(col)).strip() for col in df.columns]

    cabecalho_norm = [unicodedata.normalize('NFC', col).strip() for col in CABECALHO_PADRAO]

    # Reindex traz os dados nas colunas certas (ausentes ficam vazias)
    df_final = df.reindex(columns=cabecalho_norm)

    # Devolve os nomes exatamente como no cabeçalho original
    df_final.columns = CABECALHO_PADRAO

    # Padroniza o tipo da coluna Data Integração (sempre data)
    df_final[COLUNA_DATA_INTEGRACAO] = _converter_data_integracao(df_final[COLUNA_DATA_INTEGRACAO])

    return df_final


def processar(entrada):
    """
    Aceita:
      - um DataFrame
      - um dicionário {nome_arquivo_ou_aba: DataFrame}
      - uma lista de DataFrames / dicionários (vários arquivos)
    Retorna um dicionário com UM único DataFrame unificado.
    """
    if isinstance(entrada, pd.DataFrame):
        itens = [entrada]
    elif isinstance(entrada, dict):
        itens = list(entrada.values())
    elif isinstance(entrada, (list, tuple)):
        itens = list(entrada)
    else:
        raise TypeError("Entrada deve ser DataFrame, dict ou lista de DataFrames.")

    # Padroniza cada arquivo individualmente (inclui o tipo de Data Integração)
    padronizados = [_padronizar(item) for item in itens]

    # Empilha todos em um só, sem alterar nenhum dado
    df_unificado = pd.concat(padronizados, ignore_index=True)

    # Chave com a data de hoje (mesmo padrão do código original)
    data_formatada = datetime.now().strftime("%Y%m%d")
    nome_chave = f"Acredto_Producao_{data_formatada}"

    return {nome_chave: df_unificado}