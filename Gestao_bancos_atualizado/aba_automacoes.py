import streamlit as st
import pandas as pd
import io, os
import importlib.util
import tkinter as tk
from tkinter import filedialog

PASTA_REGRAS = "regras_automacao"

if not os.path.exists(PASTA_REGRAS):
    os.makedirs(PASTA_REGRAS)

def listar_regras_python():
    regras = {}
    for f in os.listdir(PASTA_REGRAS):
        if f.endswith(".py") and not f.startswith("__"):
            nome_exibicao = f.replace(".py", "").replace("_", " ").upper()
            regras[nome_exibicao] = {"tipo": "py", "caminho": os.path.join(PASTA_REGRAS, f)}
    return regras

def executar_script_python(caminho, df):
    nome_mod = os.path.basename(caminho)[:-3]
    spec = importlib.util.spec_from_file_location(nome_mod, caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.processar(df)

# --- MODAL DO GESTOR DE CÓDIGOS ---
@st.dialog("🛠️ Gestor de Códigos Python", width="large")
def modal_gestor_codigos(opcoes):
    tab_editar, tab_criar = st.tabs(["✏️ Editar Regra", "➕ Criar Nova Regra"])
    
    with tab_editar:
        if opcoes:
            script_editar = st.selectbox("Escolha o script que deseja modificar:", list(opcoes.keys()), key="seletor_edicao")
            caminho_script = opcoes[script_editar]["caminho"]
            
            try:
                with open(caminho_script, "r", encoding="utf-8") as f:
                    conteudo_atual = f.read()
            except Exception as e:
                conteudo_atual = f"# Erro ao ler ficheiro: {e}"
            
            novo_conteudo = st.text_area(
                f"A editar: {os.path.basename(caminho_script)}", 
                value=conteudo_atual, 
                height=450,
                key=f"area_edicao_{script_editar}"
            )
            
            if st.button("💾 Guardar Alterações", type="primary", key="btn_salvar_edicao", use_container_width=True):
                try:
                    with open(caminho_script, "w", encoding="utf-8") as f:
                        f.write(novo_conteudo)
                    st.success("✅ Código atualizado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao guardar o ficheiro: {e}")
        else:
            st.info("Nenhuma regra encontrada. Utilize o separador ao lado para criar a primeira.")
    
    with tab_criar:
        nome_novo_arquivo = st.text_input("Nome do novo ficheiro (sem .py):", placeholder="ex: formatacao_vendas")
        conteudo_novo = st.text_area(
            "Insira o código Python:", 
            value="def processar(df):\n    # Introduza a sua lógica de automação aqui\n    \n    return df", 
            height=450, 
            key="area_novo"
        )
        
        if st.button("💾 Criar Novo Código", type="primary", key="btn_criar_novo", use_container_width=True):
            if nome_novo_arquivo:
                nome_arquivo_limpo = nome_novo_arquivo.strip().replace(" ", "_").lower()
                if not nome_arquivo_limpo.endswith(".py"):
                    nome_arquivo_limpo += ".py"
                
                caminho_novo = os.path.join(PASTA_REGRAS, nome_arquivo_limpo)
                
                if os.path.exists(caminho_novo):
                    st.error("Já existe um ficheiro com esse nome! Escolha outro nome ou edite-o no separador ao lado.")
                else:
                    try:
                        with open(caminho_novo, "w", encoding="utf-8") as f:
                            f.write(conteudo_novo)
                        st.success(f"✅ Ficheiro `{nome_arquivo_limpo}` criado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar o ficheiro: {e}")
            else:
                st.warning("Por favor, introduza um nome para o novo ficheiro.")
# --- FIM DO MODAL ---

def pagina_automacoes():
    st.markdown('<div class="header-container"><span class="header-title" style="color: #28a745;"> Automações de Planilha</span></div>', unsafe_allow_html=True)
    
    opcoes = listar_regras_python()

    # --- BOTÃO DISCRETO PARA ABRIR O GESTOR ---
    is_admin = st.session_state.get('is_admin', 0) == 1
    tem_permissao_codigo = st.session_state.get('perm_codigos', 0) == 1

    if is_admin or tem_permissao_codigo:
        # Colocamos o botão alinhado à direita (opcional, mas fica bem organizado)
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write("Coloque os seus scripts `.py` na pasta `regras_automacao`.")
        with col2:
            if st.button("💻 Gestor de Códigos", use_container_width=True):
                modal_gestor_codigos(opcoes)
    else:
        st.write("Coloque os seus scripts `.py` na pasta `regras_automacao`.")

    opcoes = listar_regras_python()

    if not opcoes:
        st.warning(f"Nenhuma regra encontrada. Adicione ficheiros `.py` na pasta `{PASTA_REGRAS}`.")
        return

    if 'dataframes_processados' not in st.session_state:
        st.session_state['dataframes_processados'] = []

    regra_selecionada = st.selectbox("Escolha qual a automação ira aplicar:", list(opcoes.keys()))
    arquivos = st.file_uploader("Selecione as planilhas (.xlsx)", type=['xlsx'], accept_multiple_files=True)
    nome_saida = st.text_input("Nome do arquivo de saída", placeholder="Ex: Planilha_Final")

    if not arquivos:
        st.session_state['dataframes_processados'] = []

    if arquivos and st.button("Processar Planilhas", type="primary"):
        with st.spinner(f"A processar: {regra_selecionada}..."):
            processados = []
            info_regra = opcoes[regra_selecionada]

            for i, file in enumerate(arquivos):
                base_name = nome_saida if nome_saida else file.name.rsplit('.', 1)[0]
                if len(arquivos) > 1: 
                    base_name += f"_{i+1}"

                try:
                    df = pd.read_excel(file, dtype=str)
                    resultado = executar_script_python(info_regra["caminho"], df)

                    if isinstance(resultado, dict):
                        for sufixo, df_export in resultado.items():
                            nome_limpo = sufixo.replace('.xlsx', '')
                            processados.append((nome_limpo, df_export))
                    elif isinstance(resultado, tuple):
                        processados.append((base_name, resultado[0]))
                        if not resultado[1].empty:
                            processados.append((f"{base_name}_CAIXA", resultado[1]))
                    else:
                        processados.append((base_name, resultado))

                except Exception as e:
                    st.error(f"Erro ao processar o ficheiro {file.name}: {e}")

            st.session_state['dataframes_processados'] = processados

    if st.session_state.get('dataframes_processados'):
        st.success("✅ Arquivo(s) processado(s) com sucesso!")
        st.write("Clique no botão abaixo para escolher a pasta e o formato (.xlsx ou .csv) onde deseja guardar:")
        
        for base_name, df_export in st.session_state['dataframes_processados']:
            if st.button(f"💾 Escolher local para salvar: {base_name}", key=f"btn_{base_name}"):
                
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
                    try:
                        if caminho_salvar.endswith('.csv'):
                            df_export.to_csv(caminho_salvar, index=False, sep=';', encoding='latin1')
                        else:
                            with pd.ExcelWriter(caminho_salvar, engine='openpyxl') as writer:
                                df_export.to_excel(writer, sheet_name='Sheet1', index=False)
                                
                        st.success(f"Arquivo salvo com sucesso em: `{caminho_salvar}`")
                    except Exception as e:
                        st.error(f"Erro ao salvar o arquivo: {e}")

if __name__ == "__main__":
    pagina_automacoes()