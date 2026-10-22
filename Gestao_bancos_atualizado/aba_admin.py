import streamlit as st, sqlite3
from bd import conectar_banco, hash_senha

@st.dialog("🛡️ Permissões de Utilizador")
def modal_permissoes(u):
    st.markdown(f"A alterar acessos de **{u['nome']}** (@{u['login']})")
    n_admin = st.toggle("👑 Administrador (Acesso Total)", value=bool(u['is_admin']))
    
    st.write("---")
    p_rel_ui = st.checkbox("📊 Aceder ao separador de Relatórios", value=bool(u['perm_relatorios']), disabled=n_admin)
    p_add_ui = st.checkbox("➕ Adicionar novos Bancos e Padrões", value=bool(u['perm_adicionar']), disabled=n_admin)
    p_edi_ui = st.checkbox("⚙️ Editar configurações dos Bancos", value=bool(u['perm_editar']), disabled=n_admin)
    p_sta_ui = st.checkbox("🔄 Alterar Estado (Integrar/Falhar/Justificar)", value=bool(u['perm_status']), disabled=n_admin)
    p_usr_ui = st.checkbox("👥 Gerir Utilizadores (Criar, Palavras-passe, Eliminar)", value=bool(u.get('perm_usuarios', 0)), disabled=n_admin)
    
    # NOVA PERMISSÃO AQUI
    p_cod_ui = st.checkbox("💻 Editar e Criar Códigos Python (Automações)", value=bool(u.get('perm_codigos', 0)), disabled=n_admin)
    
    if st.button("Guardar Modificações", type="primary", use_container_width=True):
        conn = conectar_banco()
        
        # Tenta atualizar. Se a coluna perm_codigos não existir no banco de dados, ele cria automaticamente e tenta de novo.
        try:
            conn.execute("UPDATE usuarios SET is_admin=?, perm_relatorios=?, perm_adicionar=?, perm_editar=?, perm_status=?, perm_usuarios=?, perm_codigos=? WHERE id=?", 
                         (int(n_admin), int(p_rel_ui), int(p_add_ui), int(p_edi_ui), int(p_sta_ui), int(p_usr_ui), int(p_cod_ui), u['id']))
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE usuarios ADD COLUMN perm_codigos INTEGER DEFAULT 0")
            conn.execute("UPDATE usuarios SET is_admin=?, perm_relatorios=?, perm_adicionar=?, perm_editar=?, perm_status=?, perm_usuarios=?, perm_codigos=? WHERE id=?", 
                         (int(n_admin), int(p_rel_ui), int(p_add_ui), int(p_edi_ui), int(p_sta_ui), int(p_usr_ui), int(p_cod_ui), u['id']))
            
        conn.commit(); conn.close()
        st.success("Permissões aplicadas em tempo real.")
        st.rerun()

@st.dialog("🔑 Alterar Palavra-passe")
def modal_senha(u):
    st.markdown(f"Defina a nova palavra-passe para **{u['nome']}** (@{u['login']})")
    n_senha = st.text_input("Nova Palavra-passe", type="password")
    c_senha = st.text_input("Confirmar Palavra-passe", type="password")
    
    if st.button("Guardar Palavra-passe", type="primary", use_container_width=True):
        if not n_senha:
            st.error("A palavra-passe não pode estar vazia.")
        elif n_senha != c_senha:
            st.error("As palavras-passe não coincidem!")
        else:
            conn = conectar_banco()
            conn.execute("UPDATE usuarios SET senha=? WHERE id=?", (hash_senha(n_senha), u['id']))
            conn.commit(); conn.close()
            st.success("Palavra-passe alterada com sucesso!")
            st.rerun()

def pagina_admin():
    adm = st.session_state.get('is_admin', 0) == 1
    p_usr = adm or st.session_state.get('perm_usuarios', 0) == 1
    
    if not (adm or p_usr): st.error("Acesso restrito."); return
        
    st.markdown('<div class="header-container"><span class="header-title" style="color: #ffc107;">⚙️ Painel de Administração</span></div>', unsafe_allow_html=True)
    
    with st.expander("➕ Adicionar Novo Utilizador", expanded=False):
        with st.form("form_novo_usuario", clear_on_submit=True):
            n_nome = st.text_input("Nome Completo")
            n_login = st.text_input("Nome de Utilizador")
            n_senha = st.text_input("Palavra-passe", type="password")
            n_admin = st.checkbox("👑 Atribuir perfil Administrador (Acesso total)")
            
            if st.form_submit_button("Criar Utilizador", use_container_width=True):
                if n_nome and n_login and n_senha:
                    conn = conectar_banco()
                    try:
                        # Verifica se a coluna nova já existe antes de fazer o INSERT
                        try:
                            conn.execute("SELECT perm_codigos FROM usuarios LIMIT 1")
                        except sqlite3.OperationalError:
                            conn.execute("ALTER TABLE usuarios ADD COLUMN perm_codigos INTEGER DEFAULT 0")
                            
                        conn.execute("INSERT INTO usuarios (nome, login, senha, is_admin, perm_relatorios, perm_adicionar, perm_editar, perm_status, perm_usuarios, perm_codigos) VALUES (?, ?, ?, ?, 1, 0, 0, 1, 0, 0)", 
                                     (n_nome, n_login, hash_senha(n_senha), int(n_admin)))
                        conn.commit(); st.success(f"Utilizador {n_nome} registado com sucesso!")
                    except sqlite3.IntegrityError: 
                        st.error("Este nome de utilizador já se encontra registado.")
                    finally: 
                        conn.close()
                else:
                    st.error("Preencha todos os campos obrigatórios.")

    st.write("---")
    st.markdown('<div class="section-title">👥 Gestão de Utilizadores</div>', unsafe_allow_html=True)
    
    conn = conectar_banco()
    usuarios = conn.execute("SELECT * FROM usuarios ORDER BY is_admin DESC, nome ASC").fetchall()
    conn.close()

    for u in usuarios:
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([3, 1.5, 2, 1.5, 1.5], vertical_alignment="center")
            
            c1.markdown(f"**{u['nome']}**<br><span style='color:#8a8f99;font-size:13px;'>@{u['login']}</span>", unsafe_allow_html=True)
            c2.markdown("👑 Admin" if u['is_admin'] else "👤 Personalizado")
            
            if c3.button("⚙️ Permissões", key=f"perm_{u['id']}", use_container_width=True):
                modal_permissoes(dict(u))
                
            if c4.button("🔑 Palavra-passe", key=f"pw_{u['id']}", use_container_width=True):
                modal_senha(dict(u))
                
            if u['id'] != st.session_state.get('usuario_id', 0):
                if c5.button("🗑️ Eliminar", key=f"del_{u['id']}", use_container_width=True, type="secondary"):
                    conn = conectar_banco()
                    conn.execute("DELETE FROM usuarios WHERE id = ?", (u['id'],))
                    conn.commit(); conn.close(); st.rerun()
            else:
                c5.caption(" (Conta Atual) ")
        st.write("---")