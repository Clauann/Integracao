import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import io
import importlib.util
import tkinter as tk
from tkinter import filedialog
from bd import aplicar_css

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if os.path.basename(os.path.dirname(os.path.abspath(__file__))).lower() == "abas" else os.path.dirname(os.path.abspath(__file__))
PASTA_REGRAS = os.path.join(BASE_DIR, "regras_automacao") if os.path.exists(os.path.join(BASE_DIR, "regras_automacao")) else "regras_automacao"

if not os.path.exists(PASTA_REGRAS):
    os.makedirs(PASTA_REGRAS, exist_ok=True)

def listar_regras_python():
    regras = {}
    pastas_busca = [PASTA_REGRAS]
    if "regras_automacao" not in pastas_busca and os.path.exists("regras_automacao"):
        pastas_busca.append("regras_automacao")
    for pasta in pastas_busca:
        if os.path.exists(pasta):
            for f in sorted(os.listdir(pasta)):
                if f.endswith(".py") and not f.startswith("__"):
                    nome_exibicao = f.replace(".py", "").replace("_", " ").upper()
                    caminho_full = os.path.join(pasta, f)
                    regras[nome_exibicao] = {"tipo": "py", "caminho": caminho_full, "arquivo": f}
    return regras

def executar_script_python(caminho, dict_dfs):
    nome_mod = os.path.basename(caminho)[:-3]
    spec = importlib.util.spec_from_file_location(nome_mod, caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.processar(dict_dfs)

def regra_eh_apenas_csv(nome_regra, info_regra, nome_saida=""):
    """Verifica se o nome da regra, nome do arquivo .py, conteúdo do script ou nome de saída contém 'CSV'."""
    if "CSV" in str(nome_regra).upper() or "CSV" in str(nome_saida).upper():
        return True
    arq = str(info_regra.get("arquivo", "")).upper()
    if "CSV" in arq:
        return True
    try:
        with open(info_regra["caminho"], "r", encoding="utf-8", errors="ignore") as f:
            conteudo = f.read().upper()
            if "CSV" in conteudo:
                return True
    except Exception:
        pass
    return False

def pagina_automacoes():
    aplicar_css("automacoes")

    st.markdown('<div class="header-container" style="margin-bottom:18px;"><span class="header-title" style="color:#fff; font-size:1.9em;">Automações de Planilhas</span></div>', unsafe_allow_html=True)

    opcoes = listar_regras_python()

    if not opcoes:
        st.info(f"Nenhuma regra encontrada na pasta `{PASTA_REGRAS}`.")
        return

    if 'dataframes_processados' not in st.session_state:
        st.session_state['dataframes_processados'] = []

    col_esq, col_dir = st.columns([1.1, 1.3], gap="large")

    with col_esq:
        st.markdown(f'<div class="auto-panel"><div class="auto-panel-title"><span>1. Configuração da Regra</span><span class="auto-badge">{len(opcoes)} regras disponíveis</span></div></div>', unsafe_allow_html=True)
        regra_selecionada = st.selectbox(
            "Selecione a regra de automação",
            list(opcoes.keys())
        )
        info_regra = opcoes[regra_selecionada]
        apenas_csv_preview = regra_eh_apenas_csv(regra_selecionada, info_regra)
        formato_label = "Apenas CSV (detectado no código)" if apenas_csv_preview else "Excel (.xlsx) ou CSV (.csv)"
        st.caption(f"Ficheiro: `{info_regra.get('arquivo', os.path.basename(info_regra['caminho']))}` · Formato de saída: **{formato_label}**")

        nome_saida = st.text_input(
            "Nome do ficheiro de saída (opcional)",
            placeholder="Ex: Planilha_Final"
        )

    with col_dir:
        st.markdown('<div class="auto-panel"><div class="auto-panel-title"><span>2. Ficheiros de Entrada e Execução</span></div></div>', unsafe_allow_html=True)
        arquivos = st.file_uploader(
            "Selecione ou arraste as planilhas (.xlsx ou .csv)",
            type=['xlsx', 'csv'],
            accept_multiple_files=True
        )

        if not arquivos:
            st.session_state['dataframes_processados'] = []

        executar_btn = st.button(
            "Processar Planilhas",
            type="primary",
            use_container_width=True,
            disabled=not bool(arquivos)
        )

    if arquivos and executar_btn:
        with st.spinner(f"A processar: {regra_selecionada}..."):
            processados = []
            try:
                dict_entrada = {}
                for file in arquivos:
                    if file.name.lower().endswith('.csv'):
                        df_temp = pd.read_csv(file, sep=';', encoding='latin1', dtype=str)
                        dict_entrada[file.name] = df_temp
                    else:
                        abas = pd.read_excel(file, sheet_name=None, dtype=str)
                        for nome_aba, df_aba in abas.items():
                            chave = nome_aba if len(abas) > 1 else file.name
                            dict_entrada[chave] = df_aba

                resultado = executar_script_python(info_regra["caminho"], dict_entrada)
                base_name = nome_saida.strip() if nome_saida and nome_saida.strip() else "Planilha_Saida"

                if isinstance(resultado, dict):
                    for sufixo, df_export in resultado.items():
                        so_csv_item = regra_eh_apenas_csv(regra_selecionada, info_regra, sufixo)
                        nome_limpo = sufixo.replace('.xlsx', '').replace('.csv', '')
                        processados.append((nome_limpo, df_export, so_csv_item))
                elif isinstance(resultado, tuple):
                    so_csv_item = regra_eh_apenas_csv(regra_selecionada, info_regra, base_name)
                    processados.append((base_name, resultado[0], so_csv_item))
                    if len(resultado) > 1 and isinstance(resultado[1], pd.DataFrame) and not resultado[1].empty:
                        processados.append((f"{base_name}_CAIXA", resultado[1], so_csv_item))
                elif isinstance(resultado, pd.DataFrame):
                    so_csv_item = regra_eh_apenas_csv(regra_selecionada, info_regra, base_name)
                    processados.append((base_name, resultado, so_csv_item))

                st.session_state['dataframes_processados'] = processados
            except Exception as e:
                st.error(f"Erro ao processar ficheiros: {e}")

    if st.session_state.get('dataframes_processados'):
        st.write("")
        st.markdown('<div class="section-title" style="font-size:15px;">Ficheiros Processados</div>', unsafe_allow_html=True)

        for idx_p, item_proc in enumerate(st.session_state['dataframes_processados']):
            if len(item_proc) == 3:
                base_name, df_export, so_csv = item_proc
            else:
                base_name, df_export = item_proc
                so_csv = regra_eh_apenas_csv(regra_selecionada, info_regra, base_name)

            fmt_tag = "Formato exclusivo: CSV" if so_csv else "Formatos: XLSX / CSV"
            st.markdown(
                f'<div class="result-box">'
                f'<div class="result-box-header">'
                f'<span class="result-box-title">{base_name}</span>'
                f'<span class="result-box-meta">{len(df_export)} linhas · {len(df_export.columns)} colunas · {fmt_tag}</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            if so_csv:
                b_col1, b_col2 = st.columns(2, gap="small")
                with b_col1:
                    if st.button(f"Escolher local para salvar (.CSV): {base_name}", key=f"btn_tk_{idx_p}_{base_name}", type="primary", use_container_width=True):
                        try:
                            root = tk.Tk()
                            root.attributes('-topmost', True)
                            root.withdraw()
                            caminho_salvar = filedialog.asksaveasfilename(
                                defaultextension=".csv",
                                filetypes=[("Ficheiro CSV (*.csv)", "*.csv")],
                                initialfile=f"{base_name}.csv",
                                title=f"Guardar {base_name} (CSV)"
                            )
                            root.destroy()
                            if caminho_salvar:
                                if not caminho_salvar.lower().endswith('.csv'):
                                    caminho_salvar += '.csv'
                                df_export.to_csv(caminho_salvar, index=False, sep=';', encoding='latin1')
                                st.success(f"Guardado em: `{caminho_salvar}`")
                        except Exception as e:
                            st.error(f"Erro ao guardar: {e}")
                with b_col2:
                    buf_csv = io.BytesIO()
                    df_export.to_csv(buf_csv, index=False, sep=';', encoding='utf-8-sig')
                    st.download_button(
                        f"Baixar .CSV ({base_name})",
                        data=buf_csv.getvalue(),
                        file_name=f"{base_name}.csv",
                        mime="text/csv",
                        key=f"dl_csv_{idx_p}_{base_name}",
                        use_container_width=True
                    )
            else:
                b_col1, b_col2, b_col3 = st.columns([1.4, 1.1, 1.1], gap="small")
                with b_col1:
                    if st.button(f"Escolher local para salvar: {base_name}", key=f"btn_tk_{idx_p}_{base_name}", type="primary", use_container_width=True):
                        try:
                            root = tk.Tk()
                            root.attributes('-topmost', True)
                            root.withdraw()
                            caminho_salvar = filedialog.asksaveasfilename(
                                defaultextension=".xlsx",
                                filetypes=[("Planilha Excel (*.xlsx)", "*.xlsx"), ("Ficheiro CSV (*.csv)", "*.csv")],
                                initialfile=f"{base_name}.xlsx",
                                title=f"Onde deseja guardar {base_name}?"
                            )
                            root.destroy()
                            if caminho_salvar:
                                if caminho_salvar.lower().endswith('.csv'):
                                    df_export.to_csv(caminho_salvar, index=False, sep=';', encoding='latin1')
                                else:
                                    with pd.ExcelWriter(caminho_salvar, engine='openpyxl') as writer:
                                        df_export.to_excel(writer, sheet_name='Sheet1', index=False)
                                st.success(f"Guardado em: `{caminho_salvar}`")
                        except Exception as e:
                            st.error(f"Erro ao guardar: {e}")
                with b_col2:
                    try:
                        buf_xlsx = io.BytesIO()
                        with pd.ExcelWriter(buf_xlsx, engine='openpyxl') as writer:
                            df_export.to_excel(writer, sheet_name='Sheet1', index=False)
                        st.download_button(
                            f"Baixar .XLSX ({base_name})",
                            data=buf_xlsx.getvalue(),
                            file_name=f"{base_name}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_xlsx_{idx_p}_{base_name}",
                            use_container_width=True
                        )
                    except Exception:
                        pass
                with b_col3:
                    buf_csv = io.BytesIO()
                    df_export.to_csv(buf_csv, index=False, sep=';', encoding='utf-8-sig')
                    st.download_button(
                        f"Baixar .CSV ({base_name})",
                        data=buf_csv.getvalue(),
                        file_name=f"{base_name}.csv",
                        mime="text/csv",
                        key=f"dl_csv_{idx_p}_{base_name}",
                        use_container_width=True
                    )

            with st.expander(f"Pré-visualizar dados ({base_name})", expanded=False):
                st.dataframe(df_export.head(100), use_container_width=True, hide_index=True, height=250)

if __name__ == "__main__":
    pagina_automacoes()
