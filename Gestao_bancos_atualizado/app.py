import streamlit as st, os
from bd import conectar_banco, hash_senha, obter_base64_imagem, inicializar_banco, verificar_rotinas

# Importar as lógicas de cada aba
from aba_integracoes import pagina_principal
from aba_relatorios import pagina_relatorios
from aba_automacoes import pagina_automacoes
from aba_lixeira import pagina_lixeira
from aba_admin import pagina_admin

_icone = "imagens/logo.png" if os.path.exists("imagens/logo.png") else "🏦"
st.set_page_config(page_title="Painel de Integrações", page_icon=_icone, layout="wide", initial_sidebar_state="expanded")

inicializar_banco(); verificar_rotinas()

img_int, img_fal, img_jus, img_edi = obter_base64_imagem("INTEGRADO"), obter_base64_imagem("FALHA"), obter_base64_imagem("JUSTIFICADO"), obter_base64_imagem("EDITAR")
st.markdown(f"""<style>
:root{{--img-int:{img_int};--img-fal:{img_fal};--img-jus:{img_jus};--img-edi:{img_edi}}}
#MainMenu,footer,.stAppDeployButton{{display:none!important}}
header[data-testid="stHeader"]{{background-color:transparent!important}}
.stApp{{background-color:#0f1115}}
.block-container{{padding-top:2.5rem!important; max-width:100% !important; padding-right:2rem !important;}}
.stApp:has(section[data-testid="stSidebar"][aria-expanded="false"]) .block-container{{padding-left:70px!important}}
*{{font-family:'Segoe UI',Tahoma,sans-serif}}
h1,h2,h3,h4,.stMarkdown p{{color:#e1e1e1}}
section[data-testid="stSidebar"]{{background-color:#12141a!important;border-right:1px solid #222630!important;min-width:250px!important;transition:all .3s ease!important}}
section[data-testid="stSidebar"][aria-expanded="false"]{{transform:translateX(0)!important;width:60px!important;min-width:60px!important}}
section[data-testid="stSidebar"][aria-expanded="false"] .sidebar-logo,section[data-testid="stSidebar"][aria-expanded="false"] .nav-title,section[data-testid="stSidebar"][aria-expanded="false"] .user-welcome,section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarCollapseButton"]{{display:none!important}}
section[data-testid="stSidebar"][aria-expanded="false"] .stButton>button{{width:34px!important;min-width:34px!important;padding-left:8px!important;padding-right:0!important;overflow:hidden!important;white-space:nowrap!important}}
[data-testid="collapsedControl"]{{left:14px!important;top:15px!important;z-index:99999!important;background-color:transparent!important}}
section[data-testid="stSidebar"] .stButton>button{{background-color:transparent!important;color:#aaa!important;border:none!important;text-align:left!important;justify-content:flex-start!important;padding:12px 16px!important;font-size:15px!important;font-weight:600!important;border-radius:8px!important;margin-bottom:4px;transition:all .2s ease!important}}
section[data-testid="stSidebar"] .stButton>button:hover{{background-color:#1a1d24!important;color:#007bff!important;transform:translateX(4px)}}
section[data-testid="stSidebar"][aria-expanded="false"] .stButton>button:hover{{transform:translateX(2px)!important}}
.header-container{{display:flex;align-items:center;gap:15px;border-bottom:1px solid #222630;padding-bottom:15px;margin-bottom:25px}}
.header-logo{{height:42px;border-radius:6px}}
.header-title{{font-weight:400;color:#fff;font-size:2.2em;margin:0}}
.bank-card{{background:#1a1d24;border:1px solid #2a2d35;border-radius:12px;padding:20px 25px;margin-bottom:15px}}
.bank-name{{font-size:21px;font-weight:700;color:#fff;display:flex;align-items:center}}
.update-time{{font-size:13px;color:#7a7f8a}}
.logo-box{{width:55px;height:55px;border-radius:12px;background:#fff;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:22px;color:#1a1d24}}
.status-wrap{{display:flex;flex-direction:column;align-items:flex-end;gap:6px}}
.status-pill{{display:inline-flex;align-items:center;gap:8px;font-size:13px;font-weight:700;background-color:#12141a;padding:6px 14px;border-radius:20px;border:1px solid #222630}}
.dot{{width:10px;height:10px;border-radius:50%}}
.dot.grey{{background-color:#6c757d}}
.dot.green{{background-color:#28a745}}
.dot.red{{background-color:#dc3545}}
.dot.roxo{{background-color:#6f42c1}}
.motivo-chip{{font-size:12px;padding:4px 12px;border-radius:12px;max-width:320px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.motivo-chip.red{{background:#2a1417;color:#ff8a94;border:1px solid #4a1c22}}
.motivo-chip.roxo{{background:#201530;color:#c9a6ff;border:1px solid #3d275c}}
.obs-chip{{font-size:11px;color:#f0ad4e;background:#332512;border:1px solid #5a411e;padding:2px 8px;border-radius:10px;margin-top:4px}}
.stat-card{{background:#1a1d24;border:1px solid #2a2d35;border-radius:10px;padding:22px;text-align:center}}
.stat-card h3{{margin:0;font-size:13px;color:#aaa}}
.stat-card .number{{font-size:34px;font-weight:800;margin-top:8px}}
.section-title{{font-size:17px;font-weight:700;color:#fff;margin-bottom:14px}}
div[data-testid="stDateInput"]>div,div[data-testid="stPopover"]>button,iframe[title="st_keyup.st_keyup"]{{height:42px!important;min-height:42px!important;margin-bottom:0!important;display:block!important}}

/* --- ESTILOS DOS BOTÕES DE AÇÃO (CORREÇÃO DEFINITIVA) --- */
/* Identifica o bloco de botões por estar dentro de outro bloco de colunas */
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] button {{
    background-color: transparent !important;
    border: 1px solid #2a2d35 !important;
    border-radius: 8px !important;
    transition: all .25s ease-in-out !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] button p {{
    color: #8a8f99 !important;
    font-weight: 600 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    transition: color .2s ease-in-out !important;
    margin: 0 !important;
}}

/* 1. Integrar (Primeira Coluna Interna) */
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(1) button:hover {{
    border-color: #28a745 !important;
    background-color: rgba(40,167,69,.15) !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(1) button:hover p {{
    color: #28a745 !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(1) button p::before {{
    content: '' !important;
    display: inline-block !important;
    width: 18px !important;
    height: 18px !important;
    background-image: var(--img-int) !important;
    background-size: contain !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
}}

/* 2. Falha (Segunda Coluna Interna) */
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(2) button:hover {{
    border-color: #dc3545 !important;
    background-color: rgba(220,53,69,.15) !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(2) button:hover p {{
    color: #dc3545 !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(2) button p::before {{
    content: '' !important;
    display: inline-block !important;
    width: 18px !important;
    height: 18px !important;
    background-image: var(--img-fal) !important;
    background-size: contain !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
}}

/* 3. Justificar (Terceira Coluna Interna) */
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(3) button:hover {{
    border-color: #6f42c1 !important;
    background-color: rgba(111,66,193,.15) !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(3) button:hover p {{
    color: #c9a6ff !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(3) button p::before {{
    content: '' !important;
    display: inline-block !important;
    width: 18px !important;
    height: 18px !important;
    background-image: var(--img-jus) !important;
    background-size: contain !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
}}

/* 4. Editar (Quarta Coluna Interna) */
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(4) button:hover {{
    border-color: #ffc107 !important;
    background-color: rgba(255,193,7,.15) !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(4) button:hover p {{
    color: #ffc107 !important;
}}
[data-testid="stHorizontalBlock"] [data-testid="stHorizontalBlock"] > div:nth-child(4) button p::before {{
    content: '' !important;
    display: inline-block !important;
    width: 18px !important;
    height: 18px !important;
    background-image: var(--img-edi) !important;
    background-size: contain !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
}}
</style>""", unsafe_allow_html=True)

if st.query_params: st.query_params.clear()

if 'usuario_id' not in st.session_state:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br><h2 style='text-align: center; color: #007bff;'>Acesso Corporativo</h2>", unsafe_allow_html=True)
        with st.form("form_login"):
            login_user = st.text_input("Utilizador")
            senha_user = st.text_input("Palavra-passe", type="password")
            if st.form_submit_button("Entrar no Painel", use_container_width=True):
                conn_login = conectar_banco()
                usr = conn_login.execute("SELECT * FROM usuarios WHERE login = ?", (login_user,)).fetchone()
                conn_login.close()
                if usr and usr['senha'] == hash_senha(senha_user):
                    st.session_state.update(dict(usr))
                    st.session_state['usuario_id'] = usr['id']
                    st.session_state['usuario_nome'] = usr['nome']
                    st.rerun()
                else:
                    st.error("Credenciais inválidas. Verifique os dados introduzidos.")
    st.stop()

if 'usuario_id' in st.session_state:
    conn_check = conectar_banco()
    u_atual = conn_check.execute("SELECT * FROM usuarios WHERE id = ?", (st.session_state['usuario_id'],)).fetchone()
    conn_check.close()
    if not u_atual:
        st.session_state.clear(); st.rerun()
    else:
        st.session_state.update(dict(u_atual))
        st.session_state['usuario_id'] = u_atual['id']
        st.session_state['usuario_nome'] = u_atual['nome']

adm = st.session_state.get('is_admin', 0) == 1
p_rel = adm or st.session_state.get('perm_relatorios', 0) == 1
p_usr = adm or st.session_state.get('perm_usuarios', 0) == 1

if "pagina" not in st.session_state: st.session_state.pagina = "principal"

with st.sidebar:
    logo_sidebar = obter_base64_imagem("logo")
    if logo_sidebar != "none": st.markdown(f'<div class="sidebar-logo" style="display:flex;justify-content:center;padding:6px 0 18px 0;"><img src="{logo_sidebar[5:-2]}" style="height:38px;border-radius:6px;"></div>', unsafe_allow_html=True)
    
    st.markdown(f"<div class='user-welcome' style='padding:10px 5px; color:#e1e1e1; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>👤 Olá, {st.session_state.get('usuario_nome', 'Utilizador')}</div>", unsafe_allow_html=True)
    
    if st.button("Encerrar Sessão", use_container_width=True): 
        st.session_state.clear()
        st.rerun()
        
    st.markdown("<div class='nav-title' style='padding:4px 0 15px 5px;color:#6c757d;font-size:12px;font-weight:700;'>MENU DE NAVEGAÇÃO</div>", unsafe_allow_html=True)
    
    if st.button("📱\u00A0\u00A0\u00A0\u00A0Integrações", use_container_width=True): st.session_state.pagina = "principal"; st.rerun()
    if p_rel and st.button("📊\u00A0\u00A0\u00A0\u00A0Relatórios", use_container_width=True): st.session_state.pagina = "relatorios"; st.rerun()
    if st.button("⚡\u00A0\u00A0\u00A0\u00A0Automações", use_container_width=True): st.session_state.pagina = "automacoes"; st.rerun()
    
    if adm or p_usr:
        if st.button("🗑️\u00A0\u00A0\u00A0\u00A0Lixeira", use_container_width=True): st.session_state.pagina = "lixeira"; st.rerun()
        if st.button("⚙️\u00A0\u00A0\u00A0\u00A0Administração", use_container_width=True): st.session_state.pagina = "admin"; st.rerun()

# Controle de Roteamento de Páginas
if st.session_state.pagina == "principal":
    pagina_principal()
elif st.session_state.pagina == "relatorios":
    pagina_relatorios()
elif st.session_state.pagina == "lixeira":
    pagina_lixeira()
elif st.session_state.pagina == "admin":
    pagina_admin()
elif st.session_state.pagina == "automacoes":
    pagina_automacoes()