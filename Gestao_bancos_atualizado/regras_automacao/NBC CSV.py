import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta

# Ajusta o gravador do Pandas/Openpyxl para aplicar a máscara brasileira (dd/mm/yyyy)
# em objetos de data nativa, removendo o formato YYYY-MM-DD HH:MM:SS
try:
    from pandas.io.excel._openpyxl import OpenpyxlWriter
    _orig_value_with_fmt = OpenpyxlWriter._value_with_fmt

    def _custom_value_with_fmt(self, val):
        v, fmt = _orig_value_with_fmt(self, val)
        if isinstance(val, (datetime, date, pd.Timestamp)):
            return v, "dd/mm/yyyy"
        return v, fmt

    OpenpyxlWriter._value_with_fmt = _custom_value_with_fmt
except Exception:
    pass


def processar(dict_dfs):
    data_hoje_br = datetime.now().strftime("%d/%m/%Y")
    data_hoje_nome = datetime.now().strftime("%Y%m%d")

    # =====================================================================
    # FUNÇÕES AUXILIARES BLINDADAS
    # =====================================================================
    def eh_vazio(val):
        if val is None or pd.isna(val):
            return True
        txt = str(val).strip()
        return txt == '' or txt.lower() in ['nan', 'none', 'nat', '<na>']

    # Retorna string de número inteiro limpo (para o CSV e chaves do PROCV)
    def limpar_inteiro_str(val):
        if eh_vazio(val):
            return ''
        txt = str(val).strip()
        txt_limpo = txt.replace('.', '').replace('-', '').replace('/', '')
        try:
            if txt.endswith('.0'):
                return str(int(float(txt)))
            return str(int(float(txt_limpo)))
        except:
            return txt[:-2] if txt.endswith('.0') else txt

    # Retorna int nativo do Python ou None (para colunas inteiras do Excel)
    def para_int_nativo(val):
        s = limpar_inteiro_str(val)
        if s != '' and s.lstrip('-').isdigit():
            try:
                return int(s)
            except:
                return None
        return None

    # Retorna float nativo do Python ou None (para colunas de valor/taxa do Excel)
    def para_float_nativo(val):
        if eh_vazio(val):
            return None
        if isinstance(val, (int, float, np.number)):
            return float(val)
        v_str = str(val).strip().replace('R$', '').strip()
        try:
            if ',' in v_str and '.' in v_str:
                v_str = v_str.replace('.', '').replace(',', '.')
            elif ',' in v_str:
                v_str = v_str.replace(',', '.')
            return float(v_str)
        except:
            return None

    # Retorna str limpa ou None (para colunas de texto do Excel)
    def para_str_nativo(val):
        if eh_vazio(val):
            return None
        txt = str(val)
        return txt[:-2] if txt.endswith('.0') else txt

    # Formata números para o CSV imitando o comportamento nativo do VBA no Brasil
    def formatar_num_csv_br(val):
        if eh_vazio(val):
            return ''
        v_str = str(val).strip().replace('R$', '').strip()
        try:
            if ',' in v_str and '.' in v_str:
                v_str = v_str.replace('.', '').replace(',', '.')
            elif ',' in v_str:
                v_str = v_str.replace(',', '.')
            num = round(float(v_str), 4)
            if num.is_integer():
                return str(int(num))
            fmt = f"{num:.2f}".rstrip('0').rstrip('.')
            return fmt.replace('.', ',')
        except:
            return v_str.replace('.', ',')

    # Extrai objeto date nativo (sem HH:MM:SS) ou None
    def extrair_data_br(val):
        if eh_vazio(val):
            return None
        if isinstance(val, (datetime, pd.Timestamp)):
            return date(val.year, val.month, val.day)
        if isinstance(val, date):
            return val
        if isinstance(val, (int, float, np.number)):
            try:
                return (datetime(1899, 12, 30) + timedelta(days=int(val))).date()
            except:
                pass

        str_val = str(val).strip()
        # Formato DD/MM/YYYY
        if len(str_val) >= 10 and str_val[2] == '/' and str_val[5] == '/':
            try:
                return date(int(str_val[6:10]), int(str_val[3:5]), int(str_val[0:2]))
            except:
                pass
        # Formato YYYY-MM-DD
        if len(str_val) >= 10 and str_val[4] == '-' and str_val[7] == '-':
            try:
                return date(int(str_val[0:4]), int(str_val[5:7]), int(str_val[8:10]))
            except:
                pass

        try:
            dt = pd.to_datetime(str_val, dayfirst=True, errors='coerce')
            if not pd.isna(dt):
                return date(dt.year, dt.month, dt.day)
        except:
            pass
        return None

    def formatar_data_str(val):
        dt = extrair_data_br(val)
        return dt.strftime('%d/%m/%Y') if dt is not None else ''

    # =====================================================================
    # 1. IDENTIFICAÇÃO DOS ARQUIVOS (SEM DEPENDER DO NOME DA ABA)
    # =====================================================================
    df_sheet1 = None
    df_rl = None

    if not isinstance(dict_dfs, dict):
        dict_dfs = {"Upload": dict_dfs}

    for nome, df in dict_dfs.items():
        if df is None or df.empty:
            continue
        cols_upper = [str(c).upper().strip() for c in df.columns]

        # Ignora se for a própria aba de saída "workbank NBC" (61 colunas)
        if 'NUM_BANCO' in cols_upper and 'NOM_BANCO' in cols_upper:
            continue

        # Identifica a base RL (pelo cabeçalho ou por ter entre 28 e 45 colunas)
        if any(c in cols_upper for c in ['DT.CAD.', 'DT.BASE', 'VLR.LIQ', 'OPERACAO']) or (28 <= len(df.columns) <= 45):
            df_rl = df.copy()
        # Identifica a base Sheet1 (pelo cabeçalho ou por ter até 25 colunas)
        elif (
            'NÚMERO DA OPERAÇÃO (NBC CONSIG)' in cols_upper
            or 'NÚMERO DA PROPOSTA (FUNÇÃO)' in cols_upper
            or (10 <= len(df.columns) <= 25)
        ):
            df_sheet1 = df.copy()

    resultados_finais = {}
    dict_contratos = {}

    # =====================================================================
    # ETAPA 1: PROCESSAMENTO DA BASE SHEET1 -> WORKBANK NBC (CSV)
    # =====================================================================
    if df_sheet1 is not None and not df_sheet1.empty:
        chaves_col_a = df_sheet1.iloc[:, 0].apply(limpar_inteiro_str)
        df_sheet1 = df_sheet1[chaves_col_a.str.isdigit()].reset_index(drop=True)

        if len(df_sheet1.columns) > 14:
            for k, v in zip(df_sheet1.iloc[:, 0], df_sheet1.iloc[:, 14]):
                chave = limpar_inteiro_str(k)
                val_o = limpar_inteiro_str(v)
                if chave and chave not in dict_contratos:
                    dict_contratos[chave] = val_o

        colunas_wb = [
            "NUM_BANCO", "NOM_BANCO", "NUM_PROPOSTA", "NUM_CONTRATO", "DSC_TIPO_PROPOSTA_EMPRESTIMO",
            "COD_PRODUTO", "DSC_PRODUTO", "DAT_CTR_INCLUSAO", "DSC_SITUACAO_EMPRESTIMO", "DAT_EMPRESTIMO",
            "COD_EMPREGADOR", "DSC_CONVENIO", "COD_ORGAO", "NOM_ORGAO", "COD_PRODUTOR_VENDA",
            "NOM_PRODUTOR_VENDA", "NIC_CTR_USUARIO", "COD_CPF_CLIENTE", "NOM_CLIENTE", "DAT_NASCIMENTO",
            "NUM_IDENTIDADE", "NOM_LOGRADOURO", "NUM_PREDIO", "DSC_CMPLMNT_ENDRC", "NOM_BAIRRO",
            "NOM_LOCALIDADE", "SIG_UNIDADE_FEDERACAO", "COD_ENDRCMNT_PSTL", "NUM_TELEFONE", "NUM_TELEFONE_CELULAR",
            "NOM_MAE", "NOM_PAI", "NUM_BENEFICIO", "QTD_PARCELA", "VAL_PRESTACAO",
            "VAL_BRUTO", "VAL_SALDO_RECOMPRA", "VAL_SALDO_REFINANCIAMENTO", "VAL_LIQUIDO", "PCR_PMT_PAGO_REF",
            "DAT_CREDITO", "DAT_CONFIRMACAO", "VAL_REPASSE", "PCL_COMISSAO_AGENTE", "VAL_COMISSAO",
            "VAL_SEGURO", "COD_UNIDADE_EMPRESA", "COD_SITUACAO_EMPRESTIMO", "DAT_ESTORNO", "DSC_OBSERVACAO",
            "NUM_CPF_AGENTE", "NUM_OBJETO_ECT", "PCL_TAXA_EMPRESTIMO", "DSC_TIPO_FORMULARIO_EMPRESTIMO", "DSC_TIPO_CREDITO_EMPRESTIMO",
            "NOM_GRUPO_UNIDADE_EMPRESA", "COD_PROPOSTA_EMPRESTIMO", "COD_GRUPO_UNIDADE_EMPRESA", "COD_TIPO_FUNCAO", "COD_TIPO_PROPOSTA_EMPRESTIMO",
            "COD_LOJA_DIGITACAO"
        ]

        total_rows = len(df_sheet1)
        dict_nbc = {col: [''] * total_rows for col in colunas_wb}

        def tratar_dsc_produto(val):
            if eh_vazio(val):
                return ''
            s = str(val).strip()
            try:
                num = float(s.replace(',', '.'))
                return str(int(num)) if num.is_integer() else str(num).replace('.', ',')
            except:
                return s

        if total_rows > 0:
            dict_nbc['NOM_BANCO'] = ["NBC Bank"] * total_rows
            dict_nbc['NUM_PROPOSTA'] = df_sheet1.iloc[:, 0].apply(limpar_inteiro_str).tolist()
            dict_nbc['DSC_TIPO_PROPOSTA_EMPRESTIMO'] = ["Novo"] * total_rows
            if len(df_sheet1.columns) > 15:
                dict_nbc['DSC_PRODUTO'] = df_sheet1.iloc[:, 15].apply(tratar_dsc_produto).tolist()
            dict_nbc['DAT_CTR_INCLUSAO'] = [data_hoje_br] * total_rows
            if len(df_sheet1.columns) > 16:
                dict_nbc['DSC_SITUACAO_EMPRESTIMO'] = df_sheet1.iloc[:, 16].fillna('').astype(str).str.strip().replace(['nan', 'None', '<NA>'], '').tolist()
            if len(df_sheet1.columns) > 4:
                dict_nbc['DAT_EMPRESTIMO'] = df_sheet1.iloc[:, 4].apply(formatar_data_str).tolist()
            dict_nbc['COD_EMPREGADOR'] = ["11350"] * total_rows
            dict_nbc['DSC_CONVENIO'] = ["INSS"] * total_rows
            if len(df_sheet1.columns) > 13:
                dict_nbc['NOM_PRODUTOR_VENDA'] = df_sheet1.iloc[:, 13].fillna('').astype(str).str.strip().replace(['nan', 'None', '<NA>'], '').tolist()
            if len(df_sheet1.columns) > 14:
                dict_nbc['NIC_CTR_USUARIO'] = df_sheet1.iloc[:, 14].apply(limpar_inteiro_str).tolist()
            if len(df_sheet1.columns) > 2:
                dict_nbc['COD_CPF_CLIENTE'] = df_sheet1.iloc[:, 2].apply(limpar_inteiro_str).tolist()
            if len(df_sheet1.columns) > 3:
                dict_nbc['NOM_CLIENTE'] = df_sheet1.iloc[:, 3].fillna('').astype(str).str.strip().replace(['nan', 'None', '<NA>'], '').tolist()
            if len(df_sheet1.columns) > 5:
                dict_nbc['QTD_PARCELA'] = df_sheet1.iloc[:, 5].apply(limpar_inteiro_str).tolist()
            if len(df_sheet1.columns) > 6:
                dict_nbc['VAL_PRESTACAO'] = df_sheet1.iloc[:, 6].apply(formatar_num_csv_br).tolist()
            if len(df_sheet1.columns) > 7:
                dict_nbc['VAL_BRUTO'] = df_sheet1.iloc[:, 7].apply(formatar_num_csv_br).tolist()
            if len(df_sheet1.columns) > 10:
                dict_nbc['PCL_TAXA_EMPRESTIMO'] = df_sheet1.iloc[:, 10].apply(formatar_num_csv_br).tolist()
            dict_nbc['DSC_TIPO_FORMULARIO_EMPRESTIMO'] = ["Digital"] * total_rows

        df_nbc_out = pd.DataFrame(dict_nbc).fillna('')
        resultados_finais[f"NBC_WB_{data_hoje_nome}"] = df_nbc_out

    # =====================================================================
    # ETAPA 2: PROCESSAMENTO DA BASE RL22E_v1 -> PRODUÇÃO NBC (EXCEL)
    # =====================================================================
    if df_rl is not None and not df_rl.empty:
        if len(df_rl.columns) > 1:
            chaves_col_b = df_rl.iloc[:, 1].apply(limpar_inteiro_str)
            df_rl = df_rl[chaves_col_b.str.isdigit()].reset_index(drop=True)

        total_rl = len(df_rl)
        col_names = df_rl.columns.tolist()
        if len(col_names) > 0:
            col_names[0] = "NR.PROP. "

        cols_int = {0, 1, 4, 8, 9, 10, 19, 21, 23, 25, 27, 28}
        cols_float = {11, 12, 13, 14, 15, 16, 17, 18}

        dados_colunas = {}

        # Extrai F (5), G (6) e W (22) como objetos date puros (sem hora) para aplicar a regra IARGO
        lista_dt_f = [extrair_data_br(v) for v in df_rl.iloc[:, 5]] if len(col_names) > 5 else []
        lista_dt_g = [extrair_data_br(v) for v in df_rl.iloc[:, 6]] if len(col_names) > 6 else []
        lista_w = [str(v) if not eh_vazio(v) else '' for v in df_rl.iloc[:, 22]] if len(col_names) > 22 else [''] * total_rl

        for r_idx in range(total_rl):
            if "iargo" not in lista_w[r_idx].lower():
                if lista_dt_f[r_idx] is not None and lista_dt_g[r_idx] is not None:
                    if lista_dt_f[r_idx] > lista_dt_g[r_idx]:
                        lista_dt_f[r_idx] = lista_dt_g[r_idx]

        for c_idx, nome_col in enumerate(col_names):
            if c_idx in (0, 1):
                serie_vals = [para_int_nativo(v) for v in df_rl.iloc[:, 1]]
            elif c_idx == 28:
                serie_vals = [
                    para_int_nativo(dict_contratos.get(limpar_inteiro_str(v), None))
                    for v in df_rl.iloc[:, 1]
                ]
            elif c_idx == 5:
                serie_vals = lista_dt_f
            elif c_idx == 6:
                serie_vals = lista_dt_g
            elif c_idx == 7:
                serie_vals = [extrair_data_br(v) for v in df_rl.iloc[:, 7]]
            elif c_idx in cols_int:
                serie_vals = [para_int_nativo(v) for v in df_rl.iloc[:, c_idx]]
            elif c_idx in cols_float:
                serie_vals = [para_float_nativo(v) for v in df_rl.iloc[:, c_idx]]
            else:
                serie_vals = [para_str_nativo(v) for v in df_rl.iloc[:, c_idx]]

            dados_colunas[nome_col] = pd.Series(serie_vals, dtype=object)

        df_rl_out = pd.DataFrame(dados_colunas, dtype=object)
        resultados_finais[f"NBC_producao_{data_hoje_nome}"] = df_rl_out

    return resultados_finais