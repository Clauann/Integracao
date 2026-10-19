import pandas as pd
from datetime import datetime

def processar(df):
    # No TypeScript:
    # 1. Deleta B:B (índice 1 original) -> desloca tudo 1 coluna para a esquerda
    # 2. Deleta AN:AO (índices 39 e 40 após o deslocamento, que são os índices 40 e 41 originais)
    drop_idx = []
    if len(df.columns) > 1: drop_idx.append(1)
    if len(df.columns) > 40: drop_idx.append(40)
    if len(df.columns) > 41: drop_idx.append(41)
    
    keep_cols = [idx for idx in range(len(df.columns)) if idx not in drop_idx]
    df = df.iloc[:, keep_cols].copy()

    # Índices após as exclusões: N = 13, O = 14, V = 21
    if len(df.columns) > 21:
        # Converte N (13) e V (21) para object para permitir atribuição sem conflito de tipagem
        df.iloc[:, 13] = df.iloc[:, 13].astype(object)
        df.iloc[:, 21] = df.iloc[:, 21].astype(object)
        
        n_vals = pd.to_numeric(df.iloc[:, 13], errors='coerce')
        o_vals = pd.to_numeric(df.iloc[:, 14], errors='coerce')
        
        # Condição: N e O são numéricos e N > O
        mask = (n_vals > o_vals) & n_vals.notna() & o_vals.notna()
        
        # Ajusta N para não ser maior que O
        df.iloc[mask.values, 13] = df.iloc[mask.values, 14].values
        
        # Se N > O e a coluna V for "REFINANCIAMENTO", marca como recorrente
        v_mask = mask & (df.iloc[:, 21].notna()) & (df.iloc[:, 21].astype(str).str.strip() == "REFINANCIAMENTO")
        df.iloc[v_mask.values, 21] = " REFINANCIAMENTO - RECORRENTE"
        
    data_hoje = datetime.now().strftime("%Y%m%d")
    return {f"Crefisa_CP_produção_{data_hoje}": df}