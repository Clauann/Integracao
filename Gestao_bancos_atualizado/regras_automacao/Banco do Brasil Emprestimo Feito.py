import pandas as pd
from datetime import datetime

def processar(df):
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
    
    data_hoje = datetime.now().strftime("%Y%m%d")
    return {f"ProducaoMensalBD_9_{data_hoje}": df}