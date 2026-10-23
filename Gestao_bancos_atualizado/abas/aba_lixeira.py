import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from bd import conectar_banco, registrar_historico

def pagina_lixeira():
    adm = st.session_state.get('is_admin', 0) == 1
    p_usr = adm or st.session_state.get('perm_usuarios', 0) == 1
    
    if not (adm or p_usr): st.error("Acesso restrito."); return
        
    st.markdown('<div class="header-container"><span class="header-title">🗑️ Lixeira de Bancos</span></div><p class="page-subtitle">Os bancos removidos ficam arquivados nesta área e podem ser repostos a qualquer momento.</p>', unsafe_allow_html=True)
    conn = conectar_banco(); bcs = conn.execute('SELECT * FROM bancos WHERE lixeira = 1 ORDER BY nome ASC').fetchall(); conn.close()
    if not bcs: st.markdown('<div class="empty-state"><div class="empty-state-icon">🍃</div><div class="empty-state-text">A lixeira está vazia.</div></div>', unsafe_allow_html=True)
    else:
        for b in bcs:
            with st.container():
                st.markdown(f'<div class="bank-card trash-card"><div class="bank-card-top">{f"<div class=logo-box><img src={b['logo_url']}></div>" if b["logo_url"] else f"<div class=logo-box>{b['nome'][:2].upper()}</div>"}<div class="bank-card-info"><div class="bank-name struck">{b["nome"]}</div><div class="update-time">Removido do painel principal</div></div></div></div>', unsafe_allow_html=True)
                if st.button(f"🔄 Restaurar {b['nome']}", key=f"res_{b['id']}", use_container_width=True): conn = conectar_banco(); conn.execute('UPDATE bancos SET lixeira = 0 WHERE id = ?', (b['id'],)); registrar_historico(conn, b['id'], b['nome'], "Banco Restaurado", "Retornado da lixeira."); conn.commit(); conn.close(); st.success(f"{b['nome']} restaurado!"); st.rerun()
