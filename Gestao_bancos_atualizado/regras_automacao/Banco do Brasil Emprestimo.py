import pandas as pd
from datetime import datetime

def processar(dict_dfs):
    # Extrai o primeiro (e único) DataFrame do dicionário enviado pelo Streamlit
    nome_aba, df = list(dict_dfs.items())[0]

    while len(df.columns) < 24: 
        df[f'Unnamed_Col_{len(df.columns)}'] = None
    
    c22 = df.columns[22]
    c23 = df.columns[23]
    
    df[c22] = df[c22].astype(object)
    df[c23] = df[c23].astype(object)
    
    mask_x = df[c23].isna() | (df[c23].astype(str).str.strip() == '')
    df.loc[mask_x, c23] = "Não Informado"
    df.loc[mask_x, c22] = "191"
    
    df = df.sort_values(by=[c22, c23], ascending=[True, True])
    
    hoje = datetime.now()
            
    # Dicionário simples para mapear o número do mês para a sigla em português
    meses_pt = {1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6',7: '7', 8: '8', 9: '9', 10: '10', 11: '11', 12: '12'}
            
    mes_sigla = meses_pt[hoje.month]
    data_formatada = hoje.strftime("%Y%m%d") # Formato: 20260930
            
    # Monta a string final da chave
    nome_chave = (f"ProducaoMensalBD_{mes_sigla}_{data_formatada}")
        
    # Retorna o dicionário
    return {nome_chave: df}