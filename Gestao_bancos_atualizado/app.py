import streamlit as st, os, sys, importlib.util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ABAS = os.path.join(BASE_DIR, "abas")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
if os.path.exists(PASTA_ABAS) and PASTA_ABAS not in sys.path:
    sys.path.insert(0, PASTA_ABAS)

# Limpeza automática de arquivos aba_*.py duplicados que ainda estejam na raiz (quando já existem dentro de abas/)
if os.path.exists(PASTA_ABAS):
    for _arq_dup in ["aba_integracoes.py", "aba_relatorios.py", "aba_automacoes.py", "aba_lixeira.py", "aba_admin.py"]:
        _caminho_raiz = os.path.join(BASE_DIR, _arq_dup)
        _caminho_abas = os.path.join(PASTA_ABAS, _arq_dup)
        if os.path.exists(_caminho_abas) and os.path.exists(_caminho_raiz):
            try:
                os.remove(_caminho_raiz)
            except Exception:
                pass

from bd import conectar_banco, hash_senha, obter_base64_imagem, inicializar_banco, verificar_rotinas, aplicar_css
from datetime import datetime as _dt

_CACHE_MODULOS_ABA = {}

def _carregar_funcao_aba(nome_modulo, nome_funcao):
    """Carrega a função da aba com cache em memória (muito mais rápido) quer esteja em 'abas/' ou na raiz."""
    caminhos = [
        os.path.join(PASTA_ABAS, f"{nome_modulo}.py"),
        os.path.join(BASE_DIR, f"{nome_modulo}.py"),
    ]
    for c in caminhos:
        if os.path.exists(c):
            mtime = os.path.getmtime(c)
            cached = _CACHE_MODULOS_ABA.get(nome_modulo)
            if cached and cached[0] == mtime and cached[1] == c:
                return getattr(cached[2], nome_funcao)
            spec = importlib.util.spec_from_file_location(nome_modulo, c)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _CACHE_MODULOS_ABA[nome_modulo] = (mtime, c, mod)
            return getattr(mod, nome_funcao)
    raise ImportError(f"Não foi possível encontrar {nome_modulo}.py na raiz nem na pasta 'abas/'.")

_icone_path = os.path.join(BASE_DIR, "imagens", "logo.png")
_icone = _icone_path if os.path.exists(_icone_path) else "🏦"
st.set_page_config(page_title="Painel de Integrações", page_icon=_icone, layout="wide", initial_sidebar_state="expanded")

# Executa inicialização de tabelas apenas 1 vez por sessão e rotinas apenas a cada troca de hora
if "_banco_inicializado" not in st.session_state:
    inicializar_banco()
    st.session_state["_banco_inicializado"] = True

_agora_key = _dt.now().strftime("%Y-%m-%d-%H")
if st.session_state.get("_ult_rotina_key") != _agora_key:
    verificar_rotinas()
    st.session_state["_ult_rotina_key"] = _agora_key

# ---------- ESTILOS (todo o CSS está na pasta 'estilos/') ----------
img_int, img_fal, img_jus, img_edi = obter_base64_imagem("INTEGRADO"), obter_base64_imagem("FALHA"), obter_base64_imagem("JUSTIFICADO"), obter_base64_imagem("EDITAR")
st.markdown(f"<style>:root{{--img-int:{img_int};--img-fal:{img_fal};--img-jus:{img_jus};--img-edi:{img_edi}}}</style>", unsafe_allow_html=True)
aplicar_css("global", "botoes_cartoes")

if st.query_params: st.query_params.clear()

if 'usuario_id' not in st.session_state:
    aplicar_css("login")

    if "_modo_auth" not in st.session_state:
        st.session_state["_modo_auth"] = "login"

    c1, c2, c3 = st.columns([1.3, 1.5, 1.3])
    with c2:
        logo_login = obter_base64_imagem("logo")
        img_tag = f'<img src="{logo_login[5:-2]}" style="height:46px;border-radius:8px;margin-bottom:10px;">' if logo_login != "none" else ''

        if st.session_state["_modo_auth"] == "login":
            st.markdown(f"<div class='login-card-header'>{img_tag}<h2>Acesso Corporativo</h2><p>Introduza as suas credenciais para aceder ao painel</p></div>", unsafe_allow_html=True)
            with st.form("form_login"):
                login_user = st.text_input("Utilizador", placeholder="Digite o seu utilizador")
                senha_user = st.text_input("Palavra-passe", type="password", placeholder="••••••••")
                if st.form_submit_button("Entrar no Painel", type="primary", use_container_width=True):
                    conn_login = conectar_banco()
                    usr = conn_login.execute("SELECT * FROM usuarios WHERE login = ?", (login_user.strip(),)).fetchone()
                    conn_login.close()
                    if usr and usr['senha'] == hash_senha(senha_user):
                        st.session_state.update(dict(usr))
                        st.session_state['usuario_id'] = usr['id']
                        st.session_state['usuario_nome'] = usr['nome']
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas. Verifique os dados introduzidos.")

            # Botão abaixo do quadro de login apenas para alterar a palavra-passe
            st.write("")
            if st.button("Alterar Palavra-passe", use_container_width=True, key="btn_ir_rec"):
                st.session_state["_modo_auth"] = "recuperar"
                st.rerun()

        elif st.session_state["_modo_auth"] == "recuperar":
            st.markdown(f"<div class='login-card-header'>{img_tag}<h2>Alterar Palavra-passe</h2><p>Informe o seu utilizador e defina a nova palavra-passe</p></div>", unsafe_allow_html=True)
            with st.form("form_alterar_senha_login"):
                rec_login = st.text_input("Nome de Utilizador", placeholder="Digite o seu utilizador")
                nova_s1 = st.text_input("Nova Palavra-passe", type="password", placeholder="••••••••")
                nova_s2 = st.text_input("Confirmar Nova Palavra-passe", type="password", placeholder="••••••••")
                if st.form_submit_button("Guardar Nova Palavra-passe", type="primary", use_container_width=True):
                    if not rec_login.strip():
                        st.error("Informe o seu nome de utilizador.")
                    elif not nova_s1 or nova_s1 != nova_s2:
                        st.error("As palavras-passe não coincidem ou estão vazias.")
                    else:
                        conn_r = conectar_banco()
                        u_rec = conn_r.execute("SELECT id FROM usuarios WHERE LOWER(login)=LOWER(?)", (rec_login.strip(),)).fetchone()
                        if not u_rec:
                            conn_r.close()
                            st.error("Utilizador não encontrado.")
                        else:
                            conn_r.execute("UPDATE usuarios SET senha=? WHERE id=?", (hash_senha(nova_s1), u_rec['id']))
                            conn_r.commit()
                            conn_r.close()
                            st.session_state["_modo_auth"] = "login"
                            st.toast("Palavra-passe atualizada com sucesso!", icon="✅")
                            st.rerun()

            st.write("")
            if st.button("← Voltar para o Login", use_container_width=True, key="btn_back_login_2"):
                st.session_state["_modo_auth"] = "login"
                st.rerun()
    st.stop()

if 'usuario_id' in st.session_state and not st.session_state.get('_usr_verificado'):
    conn_check = conectar_banco()
    u_atual = conn_check.execute("SELECT * FROM usuarios WHERE id = ?", (st.session_state['usuario_id'],)).fetchone()
    conn_check.close()
    if not u_atual:
        st.session_state.clear(); st.rerun()
    else:
        st.session_state.update(dict(u_atual))
        st.session_state['usuario_id'] = u_atual['id']
        st.session_state['usuario_nome'] = u_atual['nome']
        st.session_state['_usr_verificado'] = True

adm = st.session_state.get('is_admin', 0) == 1
p_rel = adm or st.session_state.get('perm_relatorios', 0) == 1
p_usr = adm or st.session_state.get('perm_usuarios', 0) == 1
p_sta = adm or st.session_state.get('perm_status', 0) == 1
p_add = adm or st.session_state.get('perm_adicionar', 0) == 1
p_edi = adm or st.session_state.get('perm_editar', 0) == 1
p_cod = adm or st.session_state.get('perm_codigos', 0) == 1
p_aut = adm or p_sta or p_add or p_edi or p_cod

if "pagina" not in st.session_state: st.session_state.pagina = "principal"

def _botao_menu(rotulo, pagina_destino):
    """Botão do menu lateral; a página ativa fica destacada (type='primary' + CSS em global.css)."""
    ativo = st.session_state.pagina == pagina_destino
    if st.button(rotulo, use_container_width=True, type="primary" if ativo else "secondary", key=f"menu_{pagina_destino}"):
        st.session_state.pagina = pagina_destino
        st.rerun()

with st.sidebar:
    logo_sidebar = obter_base64_imagem("logo")
    if logo_sidebar != "none": st.markdown(f'<div class="sidebar-logo" style="display:flex;justify-content:center;align-items:center;width:100%;text-align:center;padding:4px 0 14px 0;"><img src="{logo_sidebar[5:-2]}" style="display:block;margin:0 auto;height:36px;max-height:36px;width:auto;max-width:120px;object-fit:contain;border-radius:6px;"></div>', unsafe_allow_html=True)
    
    st.markdown(f"<div class='user-welcome'>👤 Olá, {st.session_state.get('usuario_nome', 'Utilizador')}</div>", unsafe_allow_html=True)
        
    st.markdown("<div class='nav-title'>MENU DE NAVEGAÇÃO</div>", unsafe_allow_html=True)
    
    _botao_menu("📱\u00A0\u00A0\u00A0\u00A0Integrações", "principal")
    if p_rel: _botao_menu("📊\u00A0\u00A0\u00A0\u00A0Relatórios", "relatorios")
    if p_aut: _botao_menu("⚡\u00A0\u00A0\u00A0\u00A0Automações", "automacoes")
    if adm or p_usr:
        _botao_menu("🗑️\u00A0\u00A0\u00A0\u00A0Lixeira", "lixeira")
        _botao_menu("⚙️\u00A0\u00A0\u00A0\u00A0Administração", "admin")

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
    if st.button("🚪\u00A0\u00A0\u00A0\u00A0Encerrar Sessão", use_container_width=True, key="btn_sair"): 
        st.session_state.clear()
        st.rerun()

# Carrega e executa APENAS a aba ativa (muito mais rápido!)
if st.session_state.pagina == "principal":
    _carregar_funcao_aba("aba_integracoes", "pagina_principal")()
elif st.session_state.pagina == "relatorios":
    _carregar_funcao_aba("aba_relatorios", "pagina_relatorios")()
elif st.session_state.pagina == "lixeira":
    _carregar_funcao_aba("aba_lixeira", "pagina_lixeira")()
elif st.session_state.pagina == "admin":
    _carregar_funcao_aba("aba_admin", "pagina_admin")()
elif st.session_state.pagina == "automacoes":
    _carregar_funcao_aba("aba_automacoes", "pagina_automacoes")()
