import pandas as pd
import numpy as np
from datetime import datetime

def processar(df: pd.DataFrame) -> dict:
    # Se o df for um dicionário (ex: várias abas do Excel), pega a primeira aba
    if isinstance(df, dict):
        df = list(df.values())[0]
    # --- FIM DA CORREÇÃO ---
    
    df = df.copy()

    # =====================================================================
    # 1. Coluna A (Logo): Achar "TOTAL" e apagar da linha dele para baixo
    # =====================================================================
    if "Logo" in df.columns:
        mask_total = df["Logo"].astype(str).str.strip().str.upper() == "TOTAL"
        if mask_total.any():
            idx_total = mask_total.idxmax()
            pos_corte = df.index.get_loc(idx_total)
            df = df.iloc[:pos_corte].copy()

    # =====================================================================
    # 2. Coluna E (Matriz): Buscar a palavra "IARGO" e excluir as linhas
    # =====================================================================
    if "Matriz" in df.columns:
        df = df[~df["Matriz"].astype(str).str.upper().str.contains("IARGO", na=False)].copy()

    # =====================================================================
    # 3. Coluna I (Adesão): buscar por "0" e "-1" e apagar linhas
    # =====================================================================
    if "Adesão" in df.columns:
        val_i = df["Adesão"].astype(str).str.strip().str.replace(".", ",")
        df = df[~val_i.isin(["0", "-1", "0,0", "-1,0"])].copy()

    # =====================================================================
    # 4. Coluna J (Status Proposta): Excluir "Excluída PN" e "Aguardado Exclusão"
    # =====================================================================
    if "Status Proposta" in df.columns:
        val_j = df["Status Proposta"].astype(str).str.strip().str.upper()
        cond_excluir_j = val_j.isin(["EXCLUÍDA PN", "AGUARDADO EXCLUSÃO"])
        df = df[~cond_excluir_j].copy()

    # =====================================================================
    # 5. Coluna L: "Saque complementar"/"Saque autorizado", e regras Q, J, P, R
    # =====================================================================
    cols_regra = ["Tipo Saque", "Vlr Produção", "Status Proposta", "Vlr Saque Efetivo", "Vlr Proposta"]
    if all(c in df.columns for c in cols_regra):
        val_q = df["Vlr Produção"].astype(str).str.strip().str.replace(".", ",")
        cond_q_zero = val_q.isin(["0", "0,0", "0,00"])

        val_l = df["Tipo Saque"].astype(str).str.strip().str.upper()
        cond_l = val_l.isin(["SAQUE COMPLEMENTAR", "SAQUE AUTORIZADO"])

        val_j_aprov = df["Status Proposta"].astype(str).str.strip().str.upper()
        cond_j_aprov = (val_j_aprov == "APROVADO")

        cond_geral = cond_l & cond_q_zero & cond_j_aprov

        df.loc[cond_geral, "Status Proposta"] = "integrado"
        df.loc[cond_geral, "Vlr Saque Efetivo"] = "0"
        df.loc[cond_geral, "Vlr Proposta"] = "0"

    # =====================================================================
    # 6. Coluna Z (Cliente CPF) e AA (Cliente): preencher vazias
    # =====================================================================
    if "Cliente CPF" in df.columns:
        val_cpf = df["Cliente CPF"].astype(str).str.strip()
        vazia_z = df["Cliente CPF"].isna() | (val_cpf == "") | (val_cpf.str.lower() == "nan")
        df.loc[vazia_z, "Cliente CPF"] = "191"

    if "Cliente" in df.columns:
        val_cliente = df["Cliente"].astype(str).str.strip()
        vazia_aa = df["Cliente"].isna() | (val_cliente == "") | (val_cliente.str.lower() == "nan")
        df.loc[vazia_aa, "Cliente"] = "não informado"

    # =====================================================================
    # 7. Coluna AF (Data - Produção): verifica se o ano é "1900" e copia de AE
    # =====================================================================
    if "Data - Produção" in df.columns and "Data - Adesão" in df.columns:
        ano_1900 = df["Data - Produção"].astype(str).str.contains("1900", na=False)
        df.loc[ano_1900, "Data - Produção"] = df.loc[ano_1900, "Data - Adesão"]

    # =====================================================================
    # 8. Colunas CK (Grupo Produto) e CS (Tipo Produto)
    # =====================================================================
    if "Grupo Produto" in df.columns and "Tipo Produto" in df.columns:
        val_ck = df["Grupo Produto"].astype(str).str.strip().str.upper()
        val_cs = df["Tipo Produto"].astype(str).str.strip().str.upper()
        
        cond_ck = val_ck.isin(["CONSIGNADO", "CONSIGNADO PRIVADO"])
        cond_cs_ndef = val_cs.isin(["NÃO DEFINIDO", "NAO DEFINIDO"])
        df.loc[cond_ck & cond_cs_ndef, "Tipo Produto"] = "NOVO"

        val_cs_atualizado = df["Tipo Produto"].astype(str).str.strip().str.upper()
        cond_cs_novo = (val_cs_atualizado == "NOVO")
        
        if "Vlr Produção" in df.columns and "Vlr Proposta" in df.columns:
            df.loc[cond_ck & cond_cs_novo, "Vlr Proposta"] = df.loc[cond_ck & cond_cs_novo, "Vlr Produção"]

    # =====================================================================
    # 9. Apagar as colunas
    # =====================================================================
    colunas_certas = [
        "Logo", "Grupo Código", "Grupo Econômico", "Matriz Código", "Matriz", "Loja Código", "Loja", "Loja UF", 
        "Adesão", "Status Proposta", "Codigo Numero Interno", "Tipo Saque", "Forma Pagamento", "Usuário", 
        "Qtd Emissão", "Vlr Saque Efetivo", "Vlr Produção", "Vlr Proposta", "Valor Seguro", "Qtd Adesão", 
        "Vlr Premio Efetivo", "Vlr Limite Conta", "Vlr Proposta Cancelada", "Chave Login Loja Consultor", 
        "CPF Usuário", "Cliente CPF", "Cliente", "Cliente UF", "Cliente Cidade", "Cliente Endereço", 
        "Data - Adesão", "Data - Produção", "Data - Integração", "Data - Pagamento", "Data - Primeira Entrega Fisico", 
        "Tipo Documento", "Statu Formalização", "Classificação Formalização", "Seguro", "CodigoDeBarra", "CPF Agente", 
        "Código Logo", "Cliente Data Nascimento", "Situação Operação Saque", "Status Seguro", "Data Seguro", 
        "Tipo Formalização", "ADE Elegível Seguro", "ADE com Seguro", "Protocolo Recebimento", "Data Último Protocolo", 
        "Ativação Token", "Ind. Cliente Analfabeto", "Tipo Beneficio", "Cliente DDD", "Cliente Telefone", "TelefoneDDD1", 
        "TelefoneNro1", "TelefoneDDD2", "TelefoneNro2", "TelefoneDDD3", "TelefoneNro3", "TelefoneDDD4", "TelefoneNro4", 
        "Celular_DDD", "Celular_Nro", "DataUnica", "Nr. Proposta", "Percentual Taxa Mensal Contrato", "Produto", 
        "Grupo Produto", "Tipo Produto", "Prazo", "Vlr. TAC"
    ]

    cols_existentes = [c for c in colunas_certas if c in df.columns]
    df = df[cols_existentes].copy()

    # Troca o nome da coluna de 'Prazo' para 'Qtd. Total Parcela'
    df.rename(columns={"Prazo": "Qtd. Total Parcela"}, inplace=True)

    # =====================================================================
    # 10. Formatação Final
    # =====================================================================
    # 10.1: Corrigindo as Datas
    colunas_data = [c for c in df.columns if "Data" in c or c == "Adesão"]
    for col in colunas_data:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime('%d/%m/%Y')
        else:
            mask_hora = df[col].astype(str).str.contains("00:00:00", na=False)
            if mask_hora.any():
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d/%m/%Y').fillna(df[col])

    # 10.2: Lógica robusta que não usa o to_numeric problemático
    def limpar_para_numero(x):
        if pd.isna(x) or str(x).strip().lower() == 'nan' or str(x).strip() == '':
            return np.nan
        
        if isinstance(x, str):
            texto = x.strip()
            # Se encontrar formato com vírgula, prepara para o Python ler como Float
            if ',' in texto:
                texto = texto.replace('.', '')  # Remove pontos de milhar
                texto = texto.replace(',', '.') # Troca a vírgula pelo ponto decimal do Python
            try:
                num = float(texto)
                return round(num, 8) # Arredonda para matar dízimas da memória
            except ValueError:
                return x # Se for palavra (ex: "APROVADO"), mantém palavra
        elif isinstance(x, (float, int)):
            return round(x, 8)
        
        return x

    # Colunas que DEVEM continuar como texto
    cols_texto = colunas_data + ["Cliente CPF", "CPF Usuário", "CPF Agente", "CodigoDeBarra", 
                                 "TelefoneNro1", "TelefoneNro2", "TelefoneNro3", "TelefoneNro4", "Celular_Nro"]

    for col in df.columns:
        if col not in cols_texto:
            # 1. Limpa os valores célula por célula
            df[col] = df[col].apply(limpar_para_numero)
            
            # 2. Verifica SE a coluna é inteiramente composta de números
            # Se for, converte tudo para Float de uma vez
            if df[col].dropna().apply(lambda x: isinstance(x, (int, float))).all():
                df[col] = df[col].astype(float)

    # =====================================================================
    # 11. Coluna BQ ("Percentual Taxa Mensal Contrato"): Arredondar para 4 casas
    # =====================================================================
    col_bq = "Percentual Taxa Mensal Contrato"
    if col_bq in df.columns:
        # Pega o número limpo e apenas ajusta o arredondamento para 4 casas decimais de forma segura
        df[col_bq] = df[col_bq].apply(lambda x: round(float(x), 4) if pd.notna(x) and isinstance(x, (int, float)) else x)

    # =====================================================================
    # 12. Retorno com nome dinâmico
    # =====================================================================
    hoje = datetime.now()
    
    # Dicionário simples para mapear o número do mês para a sigla em português
    meses_pt = {
        1: 'JAN', 2: 'FEV', 3: 'MAR', 4: 'ABR', 5: 'MAI', 6: 'JUN',
        7: 'JUL', 8: 'AGO', 9: 'SET', 10: 'OUT', 11: 'NOV', 12: 'DEZ'
    }
    
    mes_sigla = meses_pt[hoje.month]
    data_formatada = hoje.strftime("%Y%m%d") # Formato: 20260930
    
    # Monta a string final da chave
    nome_chave = f"BMG_digitação_POWERBI_{mes_sigla}_{data_formatada}"

    # Retorna o dicionário
    return {nome_chave: df}