import pandas as pd
import numpy as np
from datetime import datetime
import glob

def processar(df):
    data_hoje_br = datetime.now().strftime("%d/%m/%Y")
    data_hoje_nome = datetime.now().strftime("%Y%m%d")
    
    def arranca_ponto_zero(val):
        if pd.isna(val) or str(val).strip() == '' or str(val).strip().lower() == 'nan': return ''
        try: return str(int(float(val)))
        except:
            txt = str(val).strip()
            if txt.endswith('.0'): return txt[:-2]
            return txt

    # Nova função universal: formata TODAS as colunas financeiras ou decimais
    def aplicar_formato_br(df_alvo):
        for col in df_alvo.columns:
            if df_alvo[col].dtype in ['float64', 'float32'] or any(p in str(col).upper() for p in ['VAL_', 'PCL_', 'PCR_']):
                def converte_br(val):
                    if pd.isna(val) or str(val).strip() == '': return ''
                    v_str = str(val).strip()
                    try:
                        if isinstance(val, (int, float)):
                            return f"{val:.2f}".replace('.', ',')
                        v_str = v_str.replace('R$', '').strip()
                        if ',' in v_str and '.' in v_str:
                            v_str = v_str.replace('.', '').replace(',', '.')
                        elif ',' in v_str:
                            v_str = v_str.replace(',', '.')
                        return f"{float(v_str):.2f}".replace('.', ',')
                    except:
                        return v_str.replace('.', ',')
                df_alvo[col] = df_alvo[col].apply(converte_br)
        return df_alvo

    if 'Número da Operação (NBC Consig)' in df.columns or 'Número da Proposta (Função)' in df.columns:
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
        
        if not df.empty:
            total_rows = len(df)
            def format_date(serie): return pd.to_datetime(serie, errors='coerce', dayfirst=True).dt.strftime('%d/%m/%Y').fillna(serie).astype(str).replace('nan', '').values
            
            dict_nbc['NOM_BANCO'] = ["NBC Bank"] * total_rows
            dict_nbc['NUM_PROPOSTA'] = df.iloc[:, 0].apply(arranca_ponto_zero).astype(object) if len(df.columns) > 0 else ""
            dict_nbc['DSC_TIPO_PROPOSTA_EMPRESTIMO'] = ["Novo"] * total_rows
            if len(df.columns) > 15: dict_nbc['DSC_PRODUTO'] = df.iloc[:, 15].astype(object)
            dict_nbc['DAT_CTR_INCLUSAO'] = [data_hoje_br] * total_rows
            if len(df.columns) > 16: dict_nbc['DSC_SITUACAO_EMPRESTIMO'] = df.iloc[:, 16].astype(object)
            if len(df.columns) > 4: dict_nbc['DAT_EMPRESTIMO'] = format_date(df.iloc[:, 4]) 
            dict_nbc['COD_EMPREGADOR'] = ["11350"] * total_rows
            dict_nbc['DSC_CONVENIO'] = ["INSS"] * total_rows
            if len(df.columns) > 13: dict_nbc['NOM_PRODUTOR_VENDA'] = df.iloc[:, 13].astype(object) 
            if len(df.columns) > 14: dict_nbc['NIC_CTR_USUARIO'] = df.iloc[:, 14].apply(arranca_ponto_zero).astype(object)
            if len(df.columns) > 2: dict_nbc['COD_CPF_CLIENTE'] = df.iloc[:, 2].apply(arranca_ponto_zero).astype(object)
            if len(df.columns) > 3: dict_nbc['NOM_CLIENTE'] = df.iloc[:, 3].astype(object)
            if len(df.columns) > 5: dict_nbc['QTD_PARCELA'] = df.iloc[:, 5].apply(arranca_ponto_zero).astype(object)
            if len(df.columns) > 6: dict_nbc['VAL_PRESTACAO'] = df.iloc[:, 6].astype(object) 
            if len(df.columns) > 7: dict_nbc['VAL_BRUTO'] = df.iloc[:, 7].astype(object) 
            if len(df.columns) > 10: dict_nbc['PCL_TAXA_EMPRESTIMO'] = df.iloc[:, 10].astype(object)
            dict_nbc['DSC_TIPO_FORMULARIO_EMPRESTIMO'] = ["Digital"] * total_rows

        df_nbc_out = pd.DataFrame(dict_nbc).fillna('')
        df_nbc_out = aplicar_formato_br(df_nbc_out)  # APLICA A CORREÇÃO EM TUDO AQUI
        return {f"NBC_WB_{data_hoje_nome}": df_nbc_out}

    else:
        df_rl_out = df.copy()
        if len(df_rl_out.columns) > 1:
            nome_col_0 = df_rl_out.columns[0]
            df_rl_out[nome_col_0] = df_rl_out.iloc[:, 1].apply(arranca_ponto_zero).astype(object)
        if len(df_rl_out.columns) > 0:
            col_names = df_rl_out.columns.tolist()
            col_names[0] = "NR.PROP. "
            df_rl_out.columns = col_names

        dict_contratos = {}
        arquivos_relatorio = glob.glob("*relatorio-producao*.xls*")
        if arquivos_relatorio:
            try:
                df_rel = pd.read_excel(arquivos_relatorio[0])
                if len(df_rel.columns) > 14:
                    s1_keys = df_rel.iloc[:, 0].apply(arranca_ponto_zero)
                    mask = (s1_keys != '')
                    dict_contratos = dict(zip(s1_keys[mask], df_rel.iloc[:, 14][mask]))
            except:
                pass

        def map_rl_key(k):
            k_limpo = arranca_ponto_zero(k)
            if not k_limpo: return ""
            return dict_contratos.get(k_limpo, "")

        if len(df_rl_out.columns) > 28:
            nome_col_28 = df_rl_out.columns[28]
            df_rl_out[nome_col_28] = df_rl_out.iloc[:, 0].apply(map_rl_key).apply(arranca_ponto_zero).astype(object)

        df_rl_out = aplicar_formato_br(df_rl_out) # APLICA NO PROCV TAMBÉM POR SEGURANÇA
        return {f"NBC_producao_{data_hoje_nome}": df_rl_out.fillna('')}