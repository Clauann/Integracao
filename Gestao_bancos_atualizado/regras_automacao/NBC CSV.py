import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def processar(dict_dfs):
    data_hoje_br = datetime.now().strftime("%d/%m/%Y")
    data_hoje_nome = datetime.now().strftime("%Y%m%d")
    
    def arranca_ponto_zero(val):
        if pd.isna(val): return ''
        txt = str(val).strip()
        if txt == '' or txt.lower() in ['nan', 'none', 'nat']: return ''
        try: return str(int(float(txt)))
        except: return txt[:-2] if txt.endswith('.0') else txt

    # Formata TODAS as colunas financeiras ou decimais para o padrão BR (0,00)
    def aplicar_formato_br(df_alvo):
        for col in df_alvo.columns:
            # Pega colunas que são float ou que tenham palavras-chave de valor no nome
            if df_alvo[col].dtype in ['float64', 'float32'] or any(p in str(col).upper() for p in ['VAL_', 'PCL_', 'PCR_', 'TAXA']):
                def converte_br(val):
                    if pd.isna(val) or str(val).strip() == '' or str(val).strip().lower() in ['nan', 'none', 'nat']: 
                        return ''
                    
                    v_str = str(val).strip().replace('R$', '')
                    try:
                        # Trata ponto e vírgula corretamente para converter em float
                        if ',' in v_str and '.' in v_str:
                            v_str = v_str.replace('.', '').replace(',', '.')
                        elif ',' in v_str:
                            v_str = v_str.replace(',', '.')
                        
                        # Força 2 casas decimais e troca ponto por vírgula (Ex: 98.0 -> "98,00")
                        return f"{float(v_str):.2f}".replace('.', ',')
                    except:
                        # Se não conseguir converter, mantém o original
                        return str(val).replace('.', ',')
                        
                df_alvo[col] = df_alvo[col].apply(converte_br)
        return df_alvo
    
    def extrair_data_br(val):
        if pd.isna(val) or str(val).strip() == '' or str(val).strip().lower() in ['nan', 'none', 'nat']: return None
        if isinstance(val, (datetime, pd.Timestamp)): return datetime(val.year, val.month, val.day)
        if isinstance(val, (int, float)):
            try: return datetime(1899, 12, 30) + timedelta(days=int(val))
            except: pass
        
        str_val = str(val).strip()
        if len(str_val) >= 10 and str_val[2] == '/' and str_val[5] == '/':
            try: return datetime(int(str_val[6:10]), int(str_val[3:5]), int(str_val[0:2]))
            except: pass
        
        try:
            dt = pd.to_datetime(str_val, dayfirst=True, errors='coerce')
            if not pd.isna(dt): return datetime(dt.year, dt.month, dt.day)
        except: pass
        return None

    # 1. Identificar quem é a Sheet1 e quem é a RL22E_v1 nos arquivos enviados
    df_sheet1 = None
    df_rl = None

    # Se o usuário mandou só 1 arquivo ou não mandou nada, vamos tratar a primeira opção do dicionário
    if not isinstance(dict_dfs, dict):
        dict_dfs = {"Upload": dict_dfs}

    for nome, df in dict_dfs.items():
        cols_upper = [str(c).upper().strip() for c in df.columns]
        # Regra de identificação da Base Sheet1 (NBC)
        if 'NÚMERO DA OPERAÇÃO (NBC CONSIG)' in cols_upper or 'NÚMERO DA PROPOSTA (FUNÇÃO)' in cols_upper or len(df.columns) <= 20:
            df_sheet1 = df.copy()
        # Se for muito larga, é a RL22E
        elif len(df.columns) >= 28:
            df_rl = df.copy()

    resultados_finais = {}
    dict_contratos = {}

    # =====================================================================
    # PROCESSAMENTO ETAPA 1: SHEET1 -> WORKBANK NBC
    # =====================================================================
    if df_sheet1 is not None:
        if len(df_sheet1.columns) > 0:
            chaves_col_a = df_sheet1.iloc[:, 0].apply(arranca_ponto_zero)
            df_sheet1 = df_sheet1[chaves_col_a != ''].reset_index(drop=True)

        # Preenche dicionário para o PROCV
        if len(df_sheet1.columns) > 14:
            for k, v in zip(df_sheet1.iloc[:, 0], df_sheet1.iloc[:, 14]):
                chave = arranca_ponto_zero(k)
                if chave and chave not in dict_contratos:
                    dict_contratos[chave] = arranca_ponto_zero(v)

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
        
        dict_nbc = {col: '' for col in colunas_wb}
        if not df_sheet1.empty:
            total_rows = len(df_sheet1)
            def format_date(serie): return pd.to_datetime(serie, errors='coerce', dayfirst=True).dt.strftime('%d/%m/%Y').fillna(serie).astype(str).replace(['nan', 'NaT', 'None'], '').values
            
            dict_nbc['NOM_BANCO'] = ["NBC Bank"] * total_rows
            dict_nbc['NUM_PROPOSTA'] = df_sheet1.iloc[:, 0].apply(arranca_ponto_zero).astype(object) if len(df_sheet1.columns) > 0 else ""
            dict_nbc['DSC_TIPO_PROPOSTA_EMPRESTIMO'] = ["Novo"] * total_rows
            if len(df_sheet1.columns) > 15: dict_nbc['DSC_PRODUTO'] = df_sheet1.iloc[:, 15].astype(object)
            dict_nbc['DAT_CTR_INCLUSAO'] = [data_hoje_br] * total_rows
            if len(df_sheet1.columns) > 16: dict_nbc['DSC_SITUACAO_EMPRESTIMO'] = df_sheet1.iloc[:, 16].astype(object)
            if len(df_sheet1.columns) > 4: dict_nbc['DAT_EMPRESTIMO'] = format_date(df_sheet1.iloc[:, 4]) 
            dict_nbc['COD_EMPREGADOR'] = ["11350"] * total_rows
            dict_nbc['DSC_CONVENIO'] = ["INSS"] * total_rows
            if len(df_sheet1.columns) > 13: dict_nbc['NOM_PRODUTOR_VENDA'] = df_sheet1.iloc[:, 13].astype(object) 
            if len(df_sheet1.columns) > 14: dict_nbc['NIC_CTR_USUARIO'] = df_sheet1.iloc[:, 14].apply(arranca_ponto_zero).astype(object)
            if len(df_sheet1.columns) > 2: dict_nbc['COD_CPF_CLIENTE'] = df_sheet1.iloc[:, 2].apply(arranca_ponto_zero).astype(object)
            if len(df_sheet1.columns) > 3: dict_nbc['NOM_CLIENTE'] = df_sheet1.iloc[:, 3].astype(object)
            if len(df_sheet1.columns) > 5: dict_nbc['QTD_PARCELA'] = df_sheet1.iloc[:, 5].apply(arranca_ponto_zero).astype(object)
            if len(df_sheet1.columns) > 6: dict_nbc['VAL_PRESTACAO'] = df_sheet1.iloc[:, 6].astype(object) 
            if len(df_sheet1.columns) > 7: dict_nbc['VAL_BRUTO'] = df_sheet1.iloc[:, 7].astype(object) 
            if len(df_sheet1.columns) > 10: dict_nbc['PCL_TAXA_EMPRESTIMO'] = df_sheet1.iloc[:, 10].astype(object)
            dict_nbc['DSC_TIPO_FORMULARIO_EMPRESTIMO'] = ["Digital"] * total_rows

        df_nbc_out = pd.DataFrame(dict_nbc).fillna('')
        df_nbc_out = aplicar_formato_br(df_nbc_out)
        resultados_finais[f"NBC_WB_{data_hoje_nome}"] = df_nbc_out

    # =====================================================================
    # PROCESSAMENTO ETAPA 2: RL22E_v1 -> PRODUÇÃO NBC
    # =====================================================================
    if df_rl is not None:
        df_rl_out = df_rl.copy()
        
        # Limpar linhas vazias
        if len(df_rl_out.columns) > 1:
            chaves_col_b = df_rl_out.iloc[:, 1].apply(arranca_ponto_zero)
            df_rl_out = df_rl_out[chaves_col_b != ''].reset_index(drop=True)
            
            nome_col_0 = df_rl_out.columns[0]
            nome_col_1 = df_rl_out.columns[1]
            df_rl_out[nome_col_0] = df_rl_out[nome_col_1].apply(arranca_ponto_zero).astype(object)
            df_rl_out[nome_col_1] = df_rl_out[nome_col_1].apply(arranca_ponto_zero).astype(object)

        if len(df_rl_out.columns) > 0:
            col_names = df_rl_out.columns.tolist()
            col_names[0] = "NR.PROP. "
            df_rl_out.columns = col_names

        # Procv
        def map_rl_key(k):
            k_limpo = arranca_ponto_zero(k)
            return dict_contratos.get(k_limpo, "") if k_limpo else ""

        if len(df_rl_out.columns) > 28:
            nome_col_28 = df_rl_out.columns[28]
            df_rl_out[nome_col_28] = df_rl_out.iloc[:, 0].apply(map_rl_key).apply(arranca_ponto_zero).astype(object)

        # Ajuste Datas IARGO
        if len(df_rl_out.columns) > 22:
            col_F, col_G, col_W = df_rl_out.columns[5], df_rl_out.columns[6], df_rl_out.columns[22]
            for idx in df_rl_out.index:
                val_W = str(df_rl_out.at[idx, col_W]) if not pd.isna(df_rl_out.at[idx, col_W]) else ""
                if "iargo" not in val_W.lower():
                    dataF = extrair_data_br(df_rl_out.at[idx, col_F])
                    dataG = extrair_data_br(df_rl_out.at[idx, col_G])
                    if dataF is not None and dataG is not None and dataF > dataG:
                        df_rl_out.at[idx, col_F] = df_rl_out.at[idx, col_G]

        df_rl_out = aplicar_formato_br(df_rl_out)
        resultados_finais[f"NBC_producao_{data_hoje_nome}"] = df_rl_out.fillna('')

    return resultados_finais