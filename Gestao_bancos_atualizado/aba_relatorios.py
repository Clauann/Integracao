import streamlit as st, pandas as pd, io
from datetime import datetime, date
from bd import conectar_banco
try: import plotly.graph_objects as go; TEM_PLOTLY = True
except ImportError: TEM_PLOTLY = False

def eh_banco_robo(b, h_list=None):
    d = dict(b) if b else {}
    textos = [
        str(d.get('nome', '')),
        str(d.get('banco_nome', '')),
    ]
    if h_list:
        for h in h_list:
            hd = dict(h)
            textos.extend([
                str(hd.get('banco_nome', '')),
                str(hd.get('acao', '')),
                str(hd.get('detalhes', '')),
            ])
    texto_unificado = " ".join(textos).upper()
    return bool(d.get('is_robo', 0)) or ('ICRED ROBÔ' in texto_unificado) or ('ICRED ROBO' in texto_unificado) or ('ROBÔ' in texto_unificado) or ('ROBO' in texto_unificado)

def contar_integracoes_robo(h_list, b=None, eh_hoje=False):
    """Conta quantas vezes o robô foi integrado no dia (soma +1 a cada clique/registro no histórico)."""
    qtd = 0
    for h in h_list:
        acao, det = str(h['acao']).upper(), str(h['detalhes']).upper()
        if "INTEGRADO" in acao or "INTEGRADO" in det:
            qtd += 1
    # Caso o status atual do banco hoje esteja INTEGRADO mas ainda não tenha registro no histórico
    if qtd == 0 and eh_hoje and b is not None:
        st_raw = str(dict(b).get('status') or '').upper().strip()
        if "INTEGRADO" in st_raw:
            qtd = 1
    return qtd

def extrair_status_historico(h_list):
    for h in h_list:
        acao, det = str(h['acao']).upper(), str(h['detalhes']).upper()
        if "INTEGRADO" in acao or "INTEGRADO" in det: return 'INTEGRADO'
        if "ERRO" in acao or "FALHA" in acao or "ERRO" in det or "FALHA" in det: return 'ERRO'
        if "MOTIVO" in acao or "JUSTIFICADO" in det or "JUSTIFICADO" in acao: return 'JUSTIFICADO'
    return None

def extrair_status_atual(b):
    d = dict(b)
    st_raw = str(d.get('status') or '').upper().strip()
    if 'INTEGRADO' in st_raw: return 'INTEGRADO'
    if 'ERRO' in st_raw or 'FALHA' in st_raw: return 'ERRO'
    if 'JUSTIFICADO' in st_raw or d.get('motivo_pendencia'): return 'JUSTIFICADO'
    return 'PENDENTE'

def pagina_relatorios():
    adm = st.session_state.get('is_admin', 0) == 1
    p_rel = adm or st.session_state.get('perm_relatorios', 0) == 1
    
    if not p_rel: st.error("Acesso restrito."); return
    st.markdown('<div class="header-container"><span class="header-title" style="color:#007bff;">📊 Relatórios e Indicadores</span></div>', unsafe_allow_html=True)
    datas_sel = st.columns([3, 7])[0].date_input("📅 Filtrar por Período:", value=[], format="DD/MM/YYYY")
    d_i, d_f = (datas_sel[0], datas_sel[-1]) if len(datas_sel) >= 1 else (None, None)
    st.markdown(f"<div style='color:#c9a6ff; font-weight:600; padding-bottom:15px;'>Dias úteis de {d_i.strftime('%d/%m/%Y')} a {d_f.strftime('%d/%m/%Y')}</div>" if d_i and d_f else "<div style='color:#8a8f99; padding-bottom:15px;'></div>", unsafe_allow_html=True)

    conn = conectar_banco()
    bcs, hist_bruto = conn.execute("SELECT * FROM bancos WHERE lixeira = 0").fetchall(), conn.execute("SELECT * FROM historico ORDER BY id DESC").fetchall()
    conn.close()
    
    df_hist_data, hist_lookup, hist_nome_lookup = [], {}, {}
    for h in hist_bruto:
        try: 
            dia_key = h['data_hora'][:10]
            d_obj = datetime.strptime(dia_key, '%d/%m/%Y').date()
            h_dict = dict(h); h_dict['data_dt'] = d_obj; df_hist_data.append(h_dict)
            hist_lookup.setdefault(dia_key, {}).setdefault(h['banco_id'], []).append(h)
            nome_h = str(h_dict.get('banco_nome') or '').upper().strip()
            if nome_h:
                hist_nome_lookup.setdefault(dia_key, {}).setdefault(nome_h, []).append(h)
        except: pass
            
    i, p, j, e, robos_i, robos_p, robos_j, robos_e = 0, 0, 0, 0, 0, 0, 0, 0
    hoje_str = date.today().strftime("%d/%m/%Y")
    
    if d_i and d_f:
        df_tabela = pd.DataFrame([row for row in df_hist_data if d_i <= row['data_dt'] <= d_f and row['data_dt'].weekday() < 5])
        for dia_date in [d.date() for d in pd.date_range(d_i, d_f) if d.weekday() < 5]:
            dia_str = dia_date.strftime("%d/%m/%Y")
            dia_hist = hist_lookup.get(dia_str, {})
            dia_hist_nome = hist_nome_lookup.get(dia_str, {})
            eh_hoje = (dia_date == date.today())
            
            for b in bcs:
                nome_b = str(dict(b).get('nome') or dict(b).get('banco_nome') or '').upper().strip()
                h_list = dia_hist.get(b['id']) or dia_hist_nome.get(nome_b) or []
                is_r = eh_banco_robo(b, h_list)
                
                if is_r:
                    # Robô: soma +1 a cada clique/registro de INTEGRADO no histórico
                    qtd_int = contar_integracoes_robo(h_list, b, eh_hoje=eh_hoje)
                    if qtd_int > 0:
                        i += qtd_int
                        robos_i += qtd_int
                else:
                    # Bancos manuais: mantém a contagem normal (1 por banco por dia)
                    st_hist = extrair_status_historico(h_list)
                    if eh_hoje:
                        st_atual = extrair_status_atual(b)
                        st_calc = st_atual if st_atual != 'PENDENTE' else (st_hist or 'PENDENTE')
                    else:
                        st_calc = st_hist or 'PENDENTE'

                    if st_calc == 'INTEGRADO': i += 1
                    elif st_calc == 'ERRO': e += 1
                    elif st_calc == 'JUSTIFICADO': j += 1
                    else: p += 1
    else:
        df_tabela = pd.DataFrame([row for row in df_hist_data if row['data_dt'].weekday() < 5])
        dia_hist = hist_lookup.get(hoje_str, {})
        dia_hist_nome = hist_nome_lookup.get(hoje_str, {})
        
        for b in bcs:
            nome_b = str(dict(b).get('nome') or dict(b).get('banco_nome') or '').upper().strip()
            h_list = dia_hist.get(b['id']) or dia_hist_nome.get(nome_b) or []
            is_r = eh_banco_robo(b, h_list)
            
            if is_r:
                # Robô: soma +1 a cada clique/registro de INTEGRADO no dia de hoje
                qtd_int = contar_integracoes_robo(h_list, b, eh_hoje=True)
                if qtd_int > 0:
                    i += qtd_int
                    robos_i += qtd_int
            else:
                # Bancos manuais: mantém a contagem normal
                if date.today().weekday() >= 5:
                    st_calc = 'INTEGRADO'
                else:
                    st_atual = extrair_status_atual(b)
                    st_hist = extrair_status_historico(h_list)
                    st_calc = st_atual if st_atual != 'PENDENTE' else (st_hist or 'PENDENTE')

                if st_calc == 'INTEGRADO': i += 1
                elif st_calc == 'ERRO': e += 1
                elif st_calc == 'JUSTIFICADO': j += 1
                else: p += 1

    total_robos = robos_i + robos_p + robos_j + robos_e
    t = i + p + j + e

    st.markdown('<div class="section-title">📈 Status (Visão Geral)</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for col, tit, val, cor in zip(cols, ['Integrados','Pendentes','Justificados','Erros'], [i, p, j, e], ['#28a745','#aaa','#6f42c1','#dc3545']):
        col.markdown(f'<div class="stat-card"><h3>{tit}</h3><div class="number" style="color:{cor};">{val}</div></div>', unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.8])
    with c1:
        st.markdown('<div class="section-title">📊 TOTAL</div>', unsafe_allow_html=True)
        if TEM_PLOTLY:
            fig = go.Figure(data=[go.Bar(x=['Integrados','Pendentes','Justificados','Erros'], y=[i,p,j,e], marker=dict(color=['#28a745','#6c757d','#6f42c1','#dc3545']), text=[i,p,j,e], textposition='auto')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e1e1e1', size=12), height=280, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(visible=False), xaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="section-title">🎯 Performance (Robôs X Manuais X GERAL)</div>', unsafe_allow_html=True)
        if TEM_PLOTLY:
            fig_pies = go.Figure()
            def add_pie(vals, title, domain, label_prefix):
                if sum(vals) > 0: fig_pies.add_trace(go.Pie(labels=['Integrados','Pendentes','Justificados','Com Erro'], values=[max(v, sum(vals)*0.01) if v>0 else 0 for v in vals], customdata=list(zip(vals, [f"{(v/sum(vals))*100:.1f}%".replace('.0%', '%') for v in vals])), hole=0.7, domain=dict(x=domain), marker=dict(colors=['#28a745','#6c757d','#6f42c1','#dc3545'], line=dict(color='#0f1115', width=3)), textinfo='none', hovertemplate=f'<b>%{{label}} ({title})</b><br>%{{customdata[0]}} banco(s) · %{{customdata[1]}}<extra></extra>', name=title))
            add_pie([robos_i, robos_p, robos_j, robos_e], "Robôs", [0, 0.3], "Robôs")
            add_pie([i-robos_i, p-robos_p, j-robos_j, e-robos_e], "Manuais", [0.35, 0.65], "Manuais")
            add_pie([i, p, j, e], "Total", [0.7, 1.0], "Geral")
            
            anns = []
            if total_robos > 0: anns.append(dict(text=f"<span style='font-size:24px; font-weight:800; color:#fff'>{total_robos}</span><br><span style='font-size:13px;color:#8a8f99'>Robôs</span>", x=0.15, y=0.5, showarrow=False, xanchor='center', yanchor='middle'))
            if t - total_robos > 0: anns.append(dict(text=f"<span style='font-size:24px; font-weight:800; color:#fff'>{t - total_robos}</span><br><span style='font-size:13px;color:#8a8f99'>Manuais</span>", x=0.5, y=0.5, showarrow=False, xanchor='center', yanchor='middle'))
            if t > 0: anns.append(dict(text=f"<span style='font-size:24px; font-weight:800; color:#fff'>{t}</span><br><span style='font-size:13px;color:#8a8f99'>Geral</span>", x=0.85, y=0.5, showarrow=False, xanchor='center', yanchor='middle'))
            
            fig_pies.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=280, margin=dict(l=0, r=0, t=10, b=40), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(color='#e1e1e1', size=13)), annotations=anns)
            st.plotly_chart(fig_pies, use_container_width=True)

    with st.container(key="card_historico"):
        st.markdown('<div class="section-title">📜 Tabela de Histórico</div>', unsafe_allow_html=True)
        if not df_tabela.empty:
            buf = io.BytesIO(); df_tabela.to_csv(buf, index=False, sep=';', encoding='utf-8-sig'); e1, e2 = st.columns([1, 2])
            e1.download_button("📊 Exportar Histórico (CSV)", buf.getvalue(), f"historico_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True); e2.caption(f"{len(df_tabela)} registo(s) encontrado(s).")
            st.dataframe(df_tabela[['data_hora', 'banco_id', 'banco_nome', 'acao', 'detalhes', 'usuario_nome']], column_config={"banco_id": st.column_config.NumberColumn("ID Banco", format="%d")}, hide_index=True, use_container_width=True, height=380)
        else: st.info("Nenhum registo encontrado no histórico.")
    
    with st.expander("⚙️ Configurações avançadas"):
        st.markdown('<div style="color:#dc3545;font-weight:bold;margin-bottom:10px;">🗑️ Limpar Histórico do Período</div>', unsafe_allow_html=True)
        if st.button("🔥 Apagar Registos Filtrados", use_container_width=True, disabled=not st.checkbox("Sim, compreendo que a remoção é irreversível.", key="conf_apg")):
            if not df_tabela.empty and df_tabela['id'].tolist():
                conn = conectar_banco(); conn.execute(f"DELETE FROM historico WHERE id IN ({','.join(map(str, df_tabela['id'].tolist()))})"); conn.commit(); conn.close()
            st.success("Apagado!"); st.rerun()