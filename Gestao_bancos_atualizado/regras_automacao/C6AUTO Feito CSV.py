import pandas as pd
import numpy as np
import re
from datetime import datetime

def processar(df, retornar_csv_bytes=False):
    # Trabalhar com cópia e garantir nomes de colunas numéricos (0, 1, 2...)
    df = df.copy()
    
    # 0. Garante que o DataFrame tem pelo menos até a coluna AJ para não dar erro
    cols_to_add = max(0, 40 - df.shape[1])
    if cols_to_add > 0:
        for _ in range(cols_to_add):
            df[df.shape[1]] = np.nan
    df.columns = range(df.shape[1])
    
    # 1. Coluna "AF" - Criar 1 coluna do lado esquerdo (índice 31)
    df.insert(31, 'AF_new', np.nan)
    df.columns = range(df.shape[1])
    
    # 2. Separar texto da coluna "AE" (índice 30) por hífen (-)
    # Mantém o comportamento exato do Texto para Colunas do Excel/VBA
    split_ae = df[30].astype(str).str.split('-', n=1, expand=True)
    df[30] = split_ae[0].str.strip() if 0 in split_ae.columns else df[30]
    df[31] = split_ae[1] if 1 in split_ae.columns else np.nan
    
    # 3. Coluna "E" - Adicionar 4 colunas do lado esquerdo (índice 4)
    df.insert(4, 'E_new', np.nan)
    df.insert(5, 'F_new', np.nan)
    df.insert(6, 'G_new', np.nan)
    df.insert(7, 'H_new', np.nan)
    df.columns = range(df.shape[1])
    
    # 4 e 5. Copiar "D" (índice 3) para "E" (índice 4) e separar por hífen (-)
    df[4] = df[3]
    split_e = df[4].astype(str).str.split('-', expand=True)
    for i in range(min(4, split_e.shape[1])):
        df[4 + i] = split_e[i].str.strip()
        
    # 6. Coluna "K" (Antiga G, agora índice 10) - Deixar apenas "PROPOSTA PAGA"
    mask_paga = df[10].astype(str).str.strip().str.upper() == "PROPOSTA PAGA"
    df = df[mask_paga].copy()
    
    # 7. Coluna "U" (Antiga Q, agora índice 20) - Separar quem tem "CG" para o Equity
    mask_cg = df[20].astype(str).str.contains("CG", case=False, na=False)
    
    df_equity = df[mask_cg].copy()
    df_auto = df[~mask_cg].copy()

    # Cabeçalho padrão (61 Colunas)
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
    
    data_hoje_br = datetime.now().strftime("%d/%m/%Y")
    data_hoje_nome = datetime.now().strftime("%Y%m%d")

    # ==========================================================
    # FUNÇÕES AUXILIARES DE FORMATAÇÃO FIEL AO CSV PADRÃO
    # ==========================================================
    def formata_data(serie):
        """Converte datas para DD/MM/YYYY sem jamais inverter dia e mês."""
        def parse_dt(val):
            if pd.isna(val) or str(val).strip() in ['', 'nan', 'NaT', 'None']:
                return ''
            # Se já for objeto datetime/Timestamp do Pandas/Excel
            if hasattr(val, 'strftime'):
                return val.strftime('%d/%m/%Y')
            # Se for número serial do Excel
            if isinstance(val, (int, float, np.number)):
                try:
                    return (pd.to_datetime('1899-12-30') + pd.to_timedelta(float(val), 'D')).strftime('%d/%m/%Y')
                except:
                    pass
            
            s = str(val).strip()
            s_data = s.split(' ')[0].split('T')[0]
            
            # 1. Formato ISO vindo do Excel/Pandas: YYYY-MM-DD ou YYYY/MM/DD
            m_iso = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$', s_data)
            if m_iso:
                ano, mes, dia = m_iso.groups()
                return f"{int(dia):02d}/{int(mes):02d}/{ano}"
                
            # 2. Formato BR: DD/MM/YYYY ou DD-MM-YYYY
            m_br = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$', s_data)
            if m_br:
                dia, mes, ano = m_br.groups()
                return f"{int(dia):02d}/{int(mes):02d}/{ano}"
                
            # 3. Formato BR com ano de 2 dígitos: DD/MM/YY
            m_br2 = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{2})$', s_data)
            if m_br2:
                dia, mes, ano2 = m_br2.groups()
                ano = f"20{ano2}" if int(ano2) < 50 else f"19{ano2}"
                return f"{int(dia):02d}/{int(mes):02d}/{ano}"
                
            # 4. Serial do Excel em formato texto
            if re.match(r'^\d{5}(\.0+)?$', s_data):
                try:
                    return (pd.to_datetime('1899-12-30') + pd.to_timedelta(float(s_data), 'D')).strftime('%d/%m/%Y')
                except:
                    pass
            return s

        return serie.apply(parse_dt).values

    def converte_numero(serie):
        """Converte para float sem apagar o ponto decimal de números vindos do Excel."""
        def parse_num(v):
            if pd.isna(v):
                return 0.0
            # Se já é int ou float nativo do Excel/Pandas, retorna direto!
            if isinstance(v, (int, float, np.number)):
                return float(v)
            s = str(v).strip()
            if not s or s.lower() in ['nan', 'none', 'nat']:
                return 0.0
            s = s.replace('R$', '').replace('r$', '').strip()
            # Se tiver ponto e vírgula juntos (ex: 1.426,80)
            if ',' in s and '.' in s:
                if s.rfind(',') > s.rfind('.'):
                    s = s.replace('.', '').replace(',', '.')
                else:
                    s = s.replace(',', '')
            elif ',' in s:
                s = s.replace(',', '.')
            # Se tiver apenas ponto (ex: '1426.8'), mantém o ponto como decimal
            try:
                return float(s)
            except:
                return 0.0
        return serie.apply(parse_num).values

    def formata_moeda_wb(valores_float):
        """
        Formata igual ao CSV padrão:
        - 30000.0 -> '30000'
        - 17826.8 -> '17826,8'
        - 106754.31 -> '106754,31'
        """
        saida = []
        for v in valores_float:
            if pd.isna(v):
                saida.append('0')
                continue
            v_round = round(float(v), 2)
            if v_round == 0:
                saida.append('0')
            else:
                s = f"{v_round:.2f}".rstrip('0').rstrip('.').replace('.', ',')
                saida.append(s)
        return saida

    def formata_inteiro_wb(serie):
        """Limpa códigos/CPFs numéricos removendo '.0' e zeros à esquerda como o Excel faz."""
        def parse_int_str(v):
            if pd.isna(v) or str(v).strip() in ['', 'nan', 'None']:
                return ''
            if isinstance(v, (int, float, np.number)):
                return str(int(round(float(v))))
            s = str(v).strip()
            if s.endswith('.0'):
                s = s[:-2]
            if s.isdigit():
                return str(int(s))
            return s
        return serie.apply(parse_int_str).values

    # ==========================================================
    # PREENCHIMENTO "WORKBANK C6AUTO"
    # ==========================================================
    dict_auto = {col: '' for col in colunas_wb} 
    if not df_auto.empty:
        total_auto = len(df_auto)
        liq_auto = converte_numero(df_auto[25])
        seg_auto = converte_numero(df_auto[32])
        bruto_auto = liq_auto + seg_auto

        dict_auto['NOM_BANCO'] = ["C6 Auto"] * total_auto
        dict_auto['NUM_PROPOSTA'] = df_auto[20].fillna('').astype(str).str.strip().values
        dict_auto['NUM_CONTRATO'] = formata_inteiro_wb(df_auto[0])
        dict_auto['DSC_TIPO_PROPOSTA_EMPRESTIMO'] = ["Novo"] * total_auto
        dict_auto['DSC_PRODUTO'] = df_auto[18].fillna('').astype(str).str.strip().values
        dict_auto['DAT_CTR_INCLUSAO'] = [data_hoje_br] * total_auto
        dict_auto['DSC_SITUACAO_EMPRESTIMO'] = ["PROPOSTA PAGA"] * total_auto
        dict_auto['DAT_EMPRESTIMO'] = formata_data(df_auto[1])
        dict_auto['COD_EMPREGADOR'] = formata_inteiro_wb(df_auto[4])
        dict_auto['DSC_CONVENIO'] = ["C6 auto"] * total_auto
        dict_auto['NOM_PRODUTOR_VENDA'] = df_auto[3].fillna('').astype(str).str.strip().values
        dict_auto['NIC_CTR_USUARIO'] = ["C6 auto - Lojista"] * total_auto
        dict_auto['COD_CPF_CLIENTE'] = formata_inteiro_wb(df_auto[12])
        dict_auto['NOM_CLIENTE'] = df_auto[13].fillna('').astype(str).str.strip().values
        dict_auto['QTD_PARCELA'] = ['0'] * total_auto
        dict_auto['VAL_PRESTACAO'] = ['0'] * total_auto
        dict_auto['VAL_BRUTO'] = formata_moeda_wb(bruto_auto)
        dict_auto['VAL_LIQUIDO'] = formata_moeda_wb(liq_auto)
        dict_auto['DAT_CREDITO'] = formata_data(df_auto[1])
        dict_auto['VAL_SEGURO'] = formata_moeda_wb(seg_auto)
        dict_auto['PCL_TAXA_EMPRESTIMO'] = ['0'] * total_auto
        dict_auto['DSC_TIPO_FORMULARIO_EMPRESTIMO'] = ["Digital"] * total_auto

    df_auto_out = pd.DataFrame(dict_auto).fillna('')

    # ==========================================================
    # PREENCHIMENTO "WORKBANK C6CAREQUITY"
    # ==========================================================
    dict_equity = {col: '' for col in colunas_wb}
    if not df_equity.empty:
        total_equity = len(df_equity)
        liq_eq = converte_numero(df_equity[25])
        seg_eq = converte_numero(df_equity[32])
        bruto_eq = liq_eq + seg_eq

        dict_equity['NOM_BANCO'] = ["C6 Auto"] * total_equity
        dict_equity['NUM_PROPOSTA'] = df_equity[20].fillna('').astype(str).str.strip().values
        dict_equity['NUM_CONTRATO'] = formata_inteiro_wb(df_equity[0])
        dict_equity['DSC_TIPO_PROPOSTA_EMPRESTIMO'] = ["Novo"] * total_equity
        dict_equity['COD_PRODUTO'] = ["1"] * total_equity
        dict_equity['DSC_PRODUTO'] = ["Car Equity - Normal"] * total_equity
        dict_equity['DAT_CTR_INCLUSAO'] = [data_hoje_br] * total_equity
        dict_equity['DSC_SITUACAO_EMPRESTIMO'] = ["PROPOSTA PAGA"] * total_equity
        dict_equity['DAT_EMPRESTIMO'] = formata_data(df_equity[1])
        dict_equity['COD_EMPREGADOR'] = formata_inteiro_wb(df_equity[4])
        dict_equity['NOM_PRODUTOR_VENDA'] = formata_inteiro_wb(df_equity[34]) if 34 in df_equity.columns else [""] * total_equity
        dict_equity['NIC_CTR_USUARIO'] = df_equity[35].fillna('').astype(str).values if 35 in df_equity.columns else [""] * total_equity 
        dict_equity['COD_CPF_CLIENTE'] = formata_inteiro_wb(df_equity[12])
        dict_equity['NOM_CLIENTE'] = df_equity[13].fillna('').astype(str).str.strip().values
        dict_equity['QTD_PARCELA'] = ['0'] * total_equity
        dict_equity['VAL_PRESTACAO'] = ['0'] * total_equity
        dict_equity['VAL_BRUTO'] = formata_moeda_wb(bruto_eq)
        dict_equity['VAL_LIQUIDO'] = formata_moeda_wb(liq_eq)
        dict_equity['DAT_CREDITO'] = formata_data(df_equity[1])
        dict_equity['VAL_SEGURO'] = formata_moeda_wb(seg_eq)
        dict_equity['PCL_TAXA_EMPRESTIMO'] = ['0'] * total_equity
        dict_equity['DSC_TIPO_FORMULARIO_EMPRESTIMO'] = ["Digital"] * total_equity

    df_equity_out = pd.DataFrame(dict_equity).fillna('')

    # Se quiser que a própria função já retorne os arquivos prontos em CSV (bytes UTF-8 + CRLF)
    if retornar_csv_bytes:
        return {
            f"C6Auto_Padrao_WB_{data_hoje_nome}.csv": df_auto_out.to_csv(sep=';', index=False, lineterminator='\r\n').encode('utf-8'),
            f"CarEquity_Padrao_WB_{data_hoje_nome}.csv": df_equity_out.to_csv(sep=';', index=False, lineterminator='\r\n').encode('utf-8')
        }

    return {
        f"C6Auto_Padrao_WB_{data_hoje_nome}": df_auto_out,
        f"CarEquity_Padrao_WB_{data_hoje_nome}": df_equity_out
    }