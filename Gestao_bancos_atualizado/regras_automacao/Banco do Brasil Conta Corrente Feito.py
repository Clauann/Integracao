import pandas as pd
from datetime import datetime

def processar(df):
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
    
    data_hoje = datetime.now().strftime("%Y%m%d")
    return {f"ProducaoMensalCC_9_{data_hoje}": df}