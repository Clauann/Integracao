import pandas as pd
from datetime import datetime

def processar(dict_dfs):
    # Como o Streamlit envia um dicionário, extraímos o primeiro (e único) DataFrame dele
    # Pegamos o nome da aba e o DataFrame em si
    nome_aba, df = list(dict_dfs.items())[0]

    # Força a remoção de caracteres invisíveis (BOM) e espaços no nome de todas as colunas
    df.columns = [str(col).replace('\ufeff', '').replace('ï»¿', '').strip() for col in df.columns]
    
    while len(df.columns) < 13: 
        df[f'Unnamed_{len(df.columns)}'] = None
    
    c12 = df.columns[12]
    c5 = df.columns[5]
    
    df[c12] = df[c12].astype(object)
    df[c12] = df[c5].values
    
    cols = list(df.columns)
    cols[12] = "Produto"
    df.columns = cols
    
    keep_cols = [idx for idx in range(len(df.columns)) if idx != 5]
    df = df.iloc[:, keep_cols]
    
    hoje = datetime.now()
        
    # Dicionário simples para mapear o número do mês para a sigla em português
    meses_pt = {1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6',7: '7', 8: '8', 9: '9', 10: '10', 11: '11', 12: '12'}
        
    mes_sigla = meses_pt[hoje.month]
    data_formatada = hoje.strftime("%Y%m%d") # Formato: 20260930
        
    # Monta a string final da chave
    nome_chave = f"ProducaoMensalCC_{mes_sigla}_{data_formatada}"
    
    # Retorna o dicionário atualizado para o Streamlit guardar
    return {nome_chave: df}