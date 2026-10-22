import pandas as pd
from datetime import datetime

def processar(df):
    # --- INÍCIO DA CORREÇÃO ---
    # Se o df for um dicionário (ex: várias abas do Excel), pega a primeira aba
    if isinstance(df, dict):
        df = list(df.values())[0]
    is_new_layout = len(df.columns) > 20 and 'Parceiro' in str(df.columns[20])
    
    if is_new_layout:
        # Apaga as colunas Z e U originais
        if len(df.columns) > 25: df = df.drop(df.columns[25], axis=1) 
        if len(df.columns) > 20: df = df.drop(df.columns[20], axis=1) 
        
        # Insere a coluna H (Cidade)
        df.insert(7, 'Cidade_Temp', None) 
        
        # Insere a nova coluna J e traz os dados
        df.insert(9, 'Nova_J', None)
        if len(df.columns) > 18:
            df.iloc[:, 9] = df.iloc[:, 18].values
            df = df.drop(df.columns[18], axis=1)
            
        # Insere a nova coluna N e traz os dados
        df.insert(13, 'Nova_N', None)
        if len(df.columns) > 18:
            df.iloc[:, 13] = df.iloc[:, 18].values
            df = df.drop(df.columns[18], axis=1)
            
        # Insere a coluna O (Taxa) no índice 14
        df.insert(14, 'Taxa_Temp', None) 
        
        # Copia os dados da última coluna (antiga AA) para a nova coluna O e apaga a última
        df.iloc[:, 14] = df.iloc[:, -1].values
        df = df.drop(df.columns[-1], axis=1)
        
        # Agora o DataFrame tem 26 colunas exatas. Renomeando pelo cabeçalho oficial:
        df.columns = [
            'ID Card', 'Nome do cliente', 'Benefício', 'Convênio', 'CPF do Beneficiário', 
            'Data de Nascimento', 'UF', 'Cidade', 'Data da Proposta', 'Produto', 
            'Nº Contrato', 'Qtd. Parcelas', 'Valor da Parcela', 'Tabela de Vendas', 'Taxa', 
            'Valor da Proposta', 'Valor do Saldo', 'Valor do Troco', 'Data de Pagamento', 
            'Status da Proposta', 'Sub-Status', 'Observações', 'Franquia', 'Equipe Responsável', 
            'Agente Responsável', 'Email Agente Responsável'
        ]

    # PARTE 1.5.1: Substituir vírgula por ponto apenas na coluna "Taxa"
    if 'Taxa' in df.columns:
        df['Taxa'] = df['Taxa'].apply(
            lambda x: str(x).replace(',', '.') if pd.notna(x) and str(x).strip() != "" else x
        )

    # PARTE 1.5.2: Correção de formato monetário nas demais colunas financeiras (L, P, Q, R)
    for c in [12, 15, 16, 17]:
        if c < len(df.columns):
            col_name = df.columns[c]
            df[col_name] = df[col_name].astype(object) 
            
            def arrumar_valor(v):
                if pd.isna(v) or str(v).strip() == "": return v
                s = str(v).replace('R$', '').replace(' ', '').replace('.', '')
                if ',' in s: s = s.replace(',', '.')
                try: return float(s)
                except: return v
            df[col_name] = df[col_name].apply(arrumar_valor)

    # PARTE 2: Buscar "Caixa" na coluna Tabela de Vendas e separar
    tab_idx = 13
    for idx_col, col in enumerate(df.columns):
        if 'tabela de vendas' in str(col).lower(): 
            tab_idx = idx_col
            break

    # Filtra as linhas
    mask_caixa = df.iloc[:, tab_idx].astype(str).str.contains('Caixa', case=False, na=False)
    
    df_caixa = df[mask_caixa].copy()
    df_restante = df[~mask_caixa].copy()
    
    data_hoje = datetime.now().strftime("%Y%m%d")
    
    return {
        f"Caixa_{data_hoje}.xlsx": df_caixa,
        f"BRB_produção_Propostas_{data_hoje}.xlsx": df_restante
    }