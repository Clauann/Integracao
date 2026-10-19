import streamlit as st, pandas as pd
from datetime import datetime, date
from bd import conectar_banco, registrar_historico, obter_base64_imagem
try: from st_keyup import st_keyup; TEM_KEYUP = True
except ImportError: TEM_KEYUP = False

@st.dialog("⚠️ Reportar Falha")
def modal_erro(b_id, b_nome, motivos, dh_acao, dh_atualizacao, suffix=""):
    data_card = dh_acao.split(' às')[0] if dh_acao else datetime.now().strftime("%d/%m/%Y")
    st.write(f"Banco: **{b_nome}** - Data do registo: **{data_card}**")
    k = f"erro_texto_{b_id}_{suffix}"
    if k not in st.session_state: st.session_state[k] = ""
    if motivos:
        st.caption("Clique num padrão:"); cols = st.columns(min(3, len(motivos)) or 1)
        for i, m in enumerate(motivos):
            with cols[i % len(cols)]: st.button(m, key=f"sug_{b_id}_{i}_{suffix}", use_container_width=True, on_click=lambda t=m: st.session_state.update({k: t}))
    motivo = st.text_input("Qual o motivo da falha?", key=k); c1, c2 = st.columns(2)
    if c1.button("Cancelar", use_container_width=True): st.rerun()
    if c2.button("Guardar Erro", use_container_width=True, type="primary") and motivo:
        conn = conectar_banco()
        if data_card == datetime.now().strftime("%d/%m/%Y"): conn.execute("UPDATE bancos SET status='ERRO', motivo_erro=?, ultimo_erro_data=?, motivo_pendencia='', ultima_atualizacao=? WHERE id=?", (motivo, data_card, dh_atualizacao, b_id))
        registrar_historico(conn, b_id, b_nome, "Falha Reportada", f"Motivo: {motivo}", dh_acao); conn.commit(); conn.close(); st.rerun()

@st.dialog("💬 Justificativa")
def modal_motivo(b_id, b_nome, motivos, dh_acao, dh_atualizacao, suffix=""):
    data_card = dh_acao.split(' às')[0] if dh_acao else datetime.now().strftime("%d/%m/%Y")
    st.write(f"Por que motivo **{b_nome}** não foi integrado em **{data_card}**?"); k = f"motivo_texto_{b_id}_{suffix}"
    if k not in st.session_state: st.session_state[k] = ""
    if motivos:
        st.caption("Clique em um padrão:"); cols = st.columns(min(3, len(motivos)) or 1)
        for i, m in enumerate(motivos):
            with cols[i % len(cols)]: st.button(m, key=f"s_mt_{b_id}_{i}_{suffix}", use_container_width=True, on_click=lambda t=m: st.session_state.update({k: t}))
    motivo = st.text_input("Justificativa", key=k); c1, c2 = st.columns(2)
    if c1.button("Cancelar", use_container_width=True): st.rerun()
    if c2.button("Guardar Motivo", use_container_width=True, type="primary") and motivo:
        conn = conectar_banco()
        if data_card == datetime.now().strftime("%d/%m/%Y"): conn.execute("UPDATE bancos SET status='JUSTIFICADO', motivo_pendencia=?, motivo_pendencia_data=?, ultima_atualizacao=? WHERE id=?", (motivo, data_card, dh_atualizacao, b_id))
        registrar_historico(conn, b_id, b_nome, "Motivo Registrado", motivo, dh_acao); conn.commit(); conn.close(); st.rerun()

@st.dialog("⚙️ Editar Banco")
def modal_editar(b, dh_acao, dh_atualizacao, suffix=""):
    data_card = dh_acao.split(' às')[0] if dh_acao else datetime.now().strftime("%d/%m/%Y")
    st.write(f"A editar informações de: **{b['nome']}** - Registo de **{data_card}**")
    n_nome, n_logo = st.text_input("Nome do banco", value=b['nome']), st.text_input("URL do Logótipo (opcional)", value=b['logo_url'] or "")
    status_atual = 'JUSTIFICADO' if b['status'] not in ['PENDENTE', 'INTEGRADO', 'ERRO', 'JUSTIFICADO'] and b['motivo_pendencia'] else b['status']
    n_status = st.selectbox("Estado Atual", ['PENDENTE', 'INTEGRADO', 'ERRO', 'JUSTIFICADO'], index=['PENDENTE', 'INTEGRADO', 'ERRO', 'JUSTIFICADO'].index(status_atual) if status_atual in ['PENDENTE', 'INTEGRADO', 'ERRO', 'JUSTIFICADO'] else 0)
    n_is_robo, n_obs = st.checkbox("🤖 Contabilizar no gráfico de Robôs?", value=bool(dict(b).get('is_robo', 0))), st.text_area("Lembrete / Observação", value=b['observacao'] or "", height=80)
    c1, c2 = st.columns(2)
    if c1.button("Cancelar", use_container_width=True): st.rerun()
    if c2.button("Guardar Modificações", use_container_width=True, type="primary"):
        conn = conectar_banco()
        if data_card == datetime.now().strftime("%d/%m/%Y"): conn.execute('UPDATE bancos SET nome=?, logo_url=?, status=?, observacao=?, is_robo=?, ultima_atualizacao=? WHERE id=?', (n_nome, n_logo, n_status, n_obs, int(n_is_robo), dh_atualizacao, b['id']))
        else: conn.execute('UPDATE bancos SET nome=?, logo_url=?, is_robo=? WHERE id=?', (n_nome, n_logo, int(n_is_robo), b['id']))
        conn.execute('UPDATE historico SET banco_nome=? WHERE banco_id=?', (n_nome, b['id']))
        registrar_historico(conn, b['id'], n_nome, "Edição Manual", f"Status alterado para {n_status}." + (f" Obs: {n_obs}" if n_obs else ""), dh_acao); conn.commit(); conn.close(); st.rerun()

def pagina_principal():
    adm = st.session_state.get('is_admin', 0) == 1
    p_add = adm or st.session_state.get('perm_adicionar', 0) == 1
    p_edi = adm or st.session_state.get('perm_editar', 0) == 1
    p_sta = adm or st.session_state.get('perm_status', 0) == 1

    lg = obter_base64_imagem("logo")
    st.markdown(f'<div class="header-container"><img src="{lg[5:-2]}" class="header-logo" style="margin-right: 10px;"><span class="header-title">Painel de Integrações</span></div>' if lg != "none" else '<div class="header-container"><span class="header-title">🏦 Painel de Integrações</span></div>', unsafe_allow_html=True)
    
    conn = conectar_banco()
    motivos = [m['texto'] for m in conn.execute('SELECT * FROM motivos_padrao ORDER BY texto ASC').fetchall()]
    bcs_pos = conn.execute('SELECT id, nome FROM bancos WHERE lixeira = 0 ORDER BY ordem ASC, id ASC').fetchall()

    t1, t2, _, t3, t4 = st.columns([2.5, 2.0, 1.5, 1.5, 1.5], gap="small", vertical_alignment="center")
    with t1: datas_sel = st.date_input("Filtrar Período", value=[], format="DD/MM/YYYY", label_visibility="collapsed")
    with t2: busca = st_keyup(" ", placeholder="🔎 Pesquisar...", label_visibility="collapsed", debounce=300) if TEM_KEYUP else st.text_input("Buscar", placeholder="🔎 Procurar banco...", label_visibility="collapsed")
    with t3:
        if p_add:
            with st.popover("Adicionar Banco", use_container_width=True):
                with st.form("form_add", clear_on_submit=True):
                    n_nm, n_lg, n_is_robo = st.text_input("Nome do Banco"), st.text_input("URL do Logótipo"), st.checkbox("É um robô?")
                    opc = ["No final da lista"] + [f"Antes de: {bx['nome']}" for bx in bcs_pos]
                    pos = st.selectbox("Onde adicionar?", opc)
                    if st.form_submit_button("Guardar", use_container_width=True) and n_nm:
                        conn2 = conectar_banco()
                        ordm = conn2.execute('SELECT COALESCE(MAX(ordem), 0) + 1 FROM bancos').fetchone()[0] if pos == "No final da lista" else conn2.execute('SELECT ordem FROM bancos WHERE id = ?', (bcs_pos[opc.index(pos)-1]['id'],)).fetchone()[0]
                        if pos != "No final da lista": conn2.execute('UPDATE bancos SET ordem = ordem + 1 WHERE ordem >= ?', (ordm,))
                        c = conn2.execute('INSERT INTO bancos (nome, logo_url, ultima_atualizacao, ordem, is_robo) VALUES (?, ?, ?, ?, ?)', (n_nm, n_lg, datetime.now().strftime("%d/%m/%Y às %H:%M"), ordm, int(n_is_robo)))
                        registrar_historico(conn2, c.lastrowid, n_nm, "Banco Adicionado", "Novo banco inserido.", datetime.now().strftime("%d/%m/%Y às %H:%M:%S"))
                        conn2.commit(); conn2.close(); st.success(f"{n_nm} adicionado!"); st.rerun()
    with t4:
        if p_add:
            with st.popover("Padrões", use_container_width=True):
                for m in motivos:
                    m_row = conn.execute('SELECT id FROM motivos_padrao WHERE texto = ?', (m,)).fetchone()
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f'<span style="background:#241a2e;color:#c9a6ff;border:1px solid #6f42c1;padding:4px 8px;border-radius:12px;font-size:12px;">{m}</span>', unsafe_allow_html=True)
                    if m_row and c2.button("✕", key=f"r_mt_{m_row['id']}"): conn2=conectar_banco(); conn2.execute('DELETE FROM motivos_padrao WHERE id=?', (m_row['id'],)); conn2.commit(); conn2.close(); st.rerun()
                with st.form("form_add_motivo", clear_on_submit=True):
                    n_mt = st.text_input("Novo motivo")
                    if st.form_submit_button("Adicionar", use_container_width=True) and n_mt: conn2=conectar_banco(); conn2.execute('INSERT INTO motivos_padrao (texto) VALUES (?)', (n_mt,)); conn2.commit(); conn2.close(); st.rerun()

    d_i, d_f = (datas_sel[0], datas_sel[-1]) if len(datas_sel) >= 1 else (None, None)
    is_hoje = not d_i or (d_i == date.today() and d_f == date.today())
    if not is_hoje and d_i and d_f: st.warning(f"🕒 **Modo Histórico**: A apresentar {d_i.strftime('%d/%m/%Y')} a {d_f.strftime('%d/%m/%Y')}.")

    bancos = conn.execute('SELECT * FROM bancos WHERE lixeira = 0 ORDER BY ordem ASC, id ASC').fetchall()
    bancos_processados = []
    
    if is_hoje:
        for b in bancos:
            b_dict = dict(b)
            if date.today().weekday() >= 5: status_calc, mt = 'INTEGRADO', 'Fim de semana (Automático)'
            else:
                status_calc = 'JUSTIFICADO' if b['status'] not in ['INTEGRADO','ERRO','PENDENTE'] and b['motivo_pendencia'] else b['status']
                mt = b['motivo_pendencia'] if status_calc == 'JUSTIFICADO' else (f"{b['motivo_erro']} ({b['ultimo_erro_data']})" if status_calc == 'ERRO' and b['ultimo_erro_data'] else b['motivo_erro']) if status_calc == 'ERRO' else ''
            b_dict.update({'status_calc': status_calc, 'mt_calc': mt, 'data_referencia': date.today().strftime("%d/%m/%Y"), 'dh_acao': None, 'dh_atualizacao': datetime.now().strftime("%d/%m/%Y às %H:%M")})
            bancos_processados.append(b_dict)
    else:
        hist_bruto = conn.execute("SELECT banco_id, acao, detalhes, data_hora FROM historico ORDER BY id DESC").fetchall()
        hist_lookup = {}
        for h in hist_bruto: hist_lookup.setdefault(h['data_hora'][:10], {})[h['banco_id']] = h
        if d_i and d_f:
            for dia in pd.date_range(d_i, d_f):
                dia_str, dia_hist = dia.strftime("%d/%m/%Y"), hist_lookup.get(dia.strftime("%d/%m/%Y"), {})
                for b in bancos:
                    status_calc, mt = ('INTEGRADO', 'Fim de semana (Automático)') if dia.weekday() >= 5 else ('PENDENTE', '')
                    if not dia.weekday() >= 5 and dia_hist.get(b['id']):
                        row, acao, det = dia_hist[b['id']], str(dia_hist[b['id']]['acao']).upper(), str(dia_hist[b['id']]['detalhes']).upper()
                        if "INTEGRADO" in acao or "INTEGRADO" in det: status_calc = 'INTEGRADO'
                        elif "ERRO" in acao or "FALHA" in acao or "ERRO" in det or "FALHA" in det: status_calc, mt = 'ERRO', f"{row['detalhes']} ({dia_str})"
                        elif "MOTIVO" in acao or "JUSTIFICADO" in det or "JUSTIFICADO" in acao: status_calc, mt = 'JUSTIFICADO', row['detalhes']
                    b_dict = dict(b); b_dict.update({'status_calc': status_calc, 'mt_calc': mt, 'data_referencia': dia_str, 'dh_acao': f"{dia_str} às {datetime.now().strftime('%H:%M:%S')}", 'dh_atualizacao': f"{dia_str} às {datetime.now().strftime('%H:%M')}"})
                    bancos_processados.append(b_dict)
    conn.close()

    if busca:
        termo = busca.strip().lower()
        bancos_processados = [b for b in bancos_processados if termo in b['nome'].lower() or termo in b['status_calc'].lower() or termo in (b['mt_calc'] or '').lower() or termo in (b.get('observacao') or '').lower() or (termo == 'falha' and b['status_calc'] == 'ERRO') or termo in b['data_referencia']]
    
    if not bancos_processados: st.info("Nenhum banco encontrado.")
    else:
        if len(bancos_processados) > 120: st.warning("⚠️ A exibir apenas os primeiros 120 cartões. Utilize a barra de pesquisa!"); bancos_processados = bancos_processados[:120]
        
        # --- NOVIDADE: Truque de estilo para os botões caberem em 3 colunas ---
        st.markdown("""
        <style>
        /* Força o texto a não quebrar linha, diminui a fonte e o espaçamento interno dos botões */
        [data-testid="stHorizontalBlock"]:has(>div:nth-child(4):last-child)>div button p {
            font-size: 11px !important;
            gap: 4px !important;
            white-space: nowrap !important;
        }
        [data-testid="stHorizontalBlock"]:has(>div:nth-child(4):last-child)>div button {
            padding-left: 2px !important;
            padding-right: 2px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 1. Voltamos para 3 cartões por linha!
        num_cols = 4 
        
        # 2. QUEBRA A LISTA DE BANCOS EM GRUPOS (LINHAS) DE 3 EM 3
        for i in range(0, len(bancos_processados), num_cols):
            # Adicionamos gap="small" para aproveitar melhor o espaço entre os cartões
            colunas_da_linha = st.columns(num_cols, gap="small")
            bancos_da_linha = bancos_processados[i:i + num_cols]
            
            # 3. COLOCA CADA BANCO DENTRO DE SUA RESPECTIVA COLUNA
            for j, b in enumerate(bancos_da_linha):
                with colunas_da_linha[j]:
                    suffix, (cr, tx, t_mt) = b['data_referencia'].replace('/',''), {'INTEGRADO':('green','INTEGRADO',''), 'ERRO':('red','ERRO',b['mt_calc']), 'JUSTIFICADO':('roxo','JUSTIFICADO',b['mt_calc'])}.get(b['status_calc'], ('grey','PENDENTE',''))
                    lg = f'<div class="logo-box"><img src="{b["logo_url"]}"></div>' if b['logo_url'] else f'<div class="logo-box">{b["nome"][:2].upper()}</div>'
                    chp = f'<div class="motivo-chip {cr}" title="{t_mt}">💬 {t_mt}</div>' if t_mt else ""
                    obs_chp = f'<div class="obs-chip" title="{b.get("observacao", "")}">📌 {b.get("observacao", "")}</div>' if b.get("observacao") else ""
                    nome_disp = f"{b['nome']} <span style='color:#007bff;font-size:12px;margin-left:8px;padding:2px 6px;border-radius:12px;background:#1a2333;font-weight:600;'>📅 {b['data_referencia']}</span>" if not is_hoje else b['nome']
                    
                    with st.container():
                        st.markdown(f'<div class="bank-card" style="display:flex; flex-direction:column; justify-content:space-between; gap:12px; height:170px;"><div style="display:flex;align-items:center;gap:12px;min-width:0;">{lg}<div style="min-width:0;"><div class="bank-name" style="font-size:16px;">{nome_disp}</div><div class="update-time">Atualizado: {b["ultima_atualizacao"]}</div>{obs_chp}</div></div><div class="status-wrap" style="align-items:flex-start; margin-top:5px;"><div class="status-pill"><span class="dot {cr}"></span> {tx}</div>{chp}</div></div>', unsafe_allow_html=True)
                        
                        botoes = []
                        if p_sta: botoes.extend(["Integrar", "Falha", "Justificar"])
                        if p_edi: botoes.append("Editar")
                        
                        if botoes:
                            btn_cols = st.columns(len(botoes), gap="small")
                            idx = 0
                            
                            if p_sta:
                                if btn_cols[idx].button("Integrar", key=f"ok_{b['id']}_{suffix}", use_container_width=True): 
                                    conn2 = conectar_banco()
                                    if (b['dh_acao'].split(' às')[0] if b['dh_acao'] else datetime.now().strftime("%d/%m/%Y")) == datetime.now().strftime("%d/%m/%Y"): conn2.execute("UPDATE bancos SET status='INTEGRADO', motivo_erro='', motivo_pendencia='', ultima_atualizacao=? WHERE id=?", (b['dh_atualizacao'], b['id']))
                                    registrar_historico(conn2, b['id'], b['nome'], "Status Alterado", "Marcado como INTEGRADO.", b['dh_acao']); conn2.commit(); conn2.close(); st.rerun()
                                idx += 1
                                
                                if btn_cols[idx].button("Falha", key=f"er_{b['id']}_{suffix}", use_container_width=True): 
                                    modal_erro(b['id'], b['nome'], motivos, b['dh_acao'], b['dh_atualizacao'], suffix)
                                idx += 1
                                
                                if btn_cols[idx].button("Justificar", key=f"mt_{b['id']}_{suffix}", use_container_width=True): 
                                    modal_motivo(b['id'], b['nome'], motivos, b['dh_acao'], b['dh_atualizacao'], suffix)
                                idx += 1
                                
                            if p_edi:
                                if btn_cols[idx].button("Editar", key=f"ed_{b['id']}_{suffix}", use_container_width=True): 
                                    modal_editar(b, b['dh_acao'], b['dh_atualizacao'], suffix)