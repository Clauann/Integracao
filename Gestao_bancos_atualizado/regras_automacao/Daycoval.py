import pandas as pd
import unicodedata
from datetime import datetime

def processar(df):
    # --- INÍCIO DA CORREÇÃO ---
    # Se o df for um dicionário (ex: várias abas do Excel), pega a primeira aba
    if isinstance(df, dict):
        df = list(df.values())[0]
    if len(df.columns) > 16:
        c10 = df.columns[10]
        c16 = df.columns[16]
        
        print(f"Coluna 10 (K) identificada como: '{c10}'")
        print(f"Coluna 16 (Q) identificada como: '{c16}'")
        
        def normalizar_txt(s):
            if pd.isna(s):
                return ""
            # Remove acentos, converte para maiúsculas e limpa espaços duplos
            txt = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('utf-8').upper()
            return " ".join(txt.split())
        
        q_norm = df.iloc[:, 16].apply(normalizar_txt)
        k_norm = df.iloc[:, 10].apply(normalizar_txt)
        
        # Mostra no console os 5 primeiros valores únicos para você conferir se é a coluna certa
        print("Valores encontrados na Coluna Q (16):", q_norm.unique()[:5])
        print("Valores encontrados na Coluna K (10):", k_norm.unique()[:5])
        
        # Usa contains na coluna Q também para evitar perda por textos complementares
        cond_q = q_norm.str.contains("FORMALIZACAO CONCLUIDA", regex=False)
        cond_k = k_norm.str.contains("CART", regex=False) | k_norm.str.contains("CREDITO EM CONTA", regex=False)
        
        df_filtrado = df[cond_q & cond_k].reset_index(drop=True).copy()
        
        # TRAVA DE SEGURANÇA: só substitui se encontrar pelo menos 1 linha
        if len(df_filtrado) > 0:
            df = df_filtrado
            print(f"Filtro aplicado com sucesso! {len(df)} linhas mantidas.")
        else:
            print("ATENÇÃO: Nenhuma linha atendeu aos critérios! Verifique no log acima se as colunas 10 e 16 estão corretas.")
            # Se quiser que retorne a planilha original em vez de apagar tudo quando der erro, deixe como está.
        
    data_hoje = datetime.now().strftime("%Y%m%d")
    return {f"Daycoval_Cartao_{data_hoje}": df}