import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st, pandas as pd, io, html
from datetime import datetime, date, timedelta
from bd import conectar_banco, conectar_banco_virtaus, inicializar_banco_virtaus, importar_planilha_virtaus, aplicar_css
try: import plotly.graph_objects as go; TEM_PLOTLY = True
except ImportError: TEM_PLOTLY = False

MESES_PT = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}

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
    qtd = 0
    for h in h_list:
        acao, det = str(h['acao']).upper(), str(h['detalhes']).upper()
        if "INTEGRADO" in acao or "INTEGRADO" in det:
            qtd += 1
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

def classificar_cor_status_virtaus(st_txt):
    s = str(st_txt or '').upper()
    if s == 'DEMAIS':
        return '#64748b', 'grey'
    if any(k in s for k in ['SUCESSO', 'CONCLU', 'PROCESSAD', 'INTEGRADO', 'OK', 'FINALIZAD']):
        return '#10b981', 'green'
    if any(k in s for k in ['ERRO', 'FALHA', 'REJEITAD', 'INVALID', 'CANCELAD', 'PROBLEMA', 'RECUSAD']):
        return '#ef4444', 'red'
    if any(k in s for k in ['PENDENTE', 'AGUARDAND', 'FILA', 'ANDAMENTO', 'PROCESSANDO']):
        return '#f59e0b', 'roxo'
    return '#3b82f6', 'grey'

def agrupar_menores_3_porcento(labels, vals, custom_list):
    """Agrupa fatias com participação menor que 3% em 'DEMAIS' (usado apenas para Por Banco/Origem)."""
    total = sum(vals)
    if total == 0:
        return labels, vals, custom_list
    
    novos_labels, novos_vals, novos_custom = [], [], []
    demais_val = 0
    demais_itens = []
    
    for lbl, v, c in zip(labels, vals, custom_list):
        perc = (v / total) * 100.0
        if perc < 3.0:
            demais_val += v
            demais_itens.append(f"{lbl} ({v})")
        else:
            novos_labels.append(lbl)
            novos_vals.append(v)
            novos_custom.append(c)
            
    if demais_val > 0:
        novos_labels.append("DEMAIS")
        novos_vals.append(demais_val)
        resumo_demais = ", ".join(demais_itens[:8]) + ("..." if len(demais_itens) > 8 else "")
        novos_custom.append(resumo_demais)
        
    return novos_labels, novos_vals, novos_custom

def obter_mapa_robos_virtaus(origens_lista):
    """
    Retorna mapa_origens_robo: {origem: bool}
    """
    conn_v = conectar_banco_virtaus()
    cfg_rows = conn_v.execute("SELECT origem, is_robo FROM virtaus_origens_config").fetchall()
    conn_v.close()

    mapa_cfg = {}
    for r in cfg_rows:
        rd = dict(r)
        o_k = str(rd.get('origem') or '').strip().upper()
        if o_k:
            mapa_cfg[o_k] = bool(rd.get('is_robo', 0))

    resultado = {}
    for orig in origens_lista:
        o_up = str(orig or '').strip().upper()
        if not o_up:
            continue
        resultado[orig] = mapa_cfg.get(o_up, False)

    return resultado

def eh_registro_robo_virtaus(row, mapa_origens_robo):
    """
    Considera APENAS a coluna 'Forma de processamento' / 'Processamento' quando preenchida,
    ignorando nome do arquivo, tipo_origem ou origem!
    Caso a linha não tenha 'Forma de processamento' preenchida, usa apenas o que estiver marcado em 'Definir Robôs'.
    """
    fp_up = str(row.get('forma_processamento') or '').strip().upper()
    if fp_up == 'ROBO':
        return True
    if fp_up == 'MANUAL':
        return False

    orig = str(row.get('origem') or '').strip()
    return bool(mapa_origens_robo.get(orig, False))

def renderizar_relatorio_integracao():
    datas_sel = st.columns([3, 7])[0].date_input("Filtrar por Período", value=[], format="DD/MM/YYYY", key="dt_rel_integracao")
    d_i, d_f = (datas_sel[0], datas_sel[-1]) if len(datas_sel) >= 1 else (None, None)
    st.markdown(f"<div style='color:#94a3b8; font-size:13px; font-weight:600; padding-bottom:15px;'>Dias úteis de {d_i.strftime('%d/%m/%Y')} a {d_f.strftime('%d/%m/%Y')}</div>" if d_i and d_f else "<div style='padding-bottom:10px;'></div>", unsafe_allow_html=True)

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
                    qtd_int = contar_integracoes_robo(h_list, b, eh_hoje=eh_hoje)
                    if qtd_int > 0:
                        i += qtd_int
                        robos_i += qtd_int
                else:
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
                qtd_int = contar_integracoes_robo(h_list, b, eh_hoje=True)
                if qtd_int > 0:
                    i += qtd_int
                    robos_i += qtd_int
            else:
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

    st.markdown('<div class="section-title">Status (Visão Geral)</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for col, tit, val, cor in zip(cols, ['Integrados','Pendentes','Justificados','Erros'], [i, p, j, e], ['#28a745','#aaa','#6f42c1','#dc3545']):
        col.markdown(f'<div class="stat-card"><h3>{tit}</h3><div class="number" style="color:{cor};">{val}</div></div>', unsafe_allow_html=True)
    
    st.write("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.8])
    with c1:
        st.markdown('<div class="section-title">Total por Categoria</div>', unsafe_allow_html=True)
        if TEM_PLOTLY:
            fig = go.Figure(data=[go.Bar(x=['Integrados','Pendentes','Justificados','Erros'], y=[i,p,j,e], marker=dict(color=['#28a745','#6c757d','#6f42c1','#dc3545']), text=[i,p,j,e], textposition='auto')])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e1e1e1', size=12), height=280, margin=dict(l=10, r=10, t=10, b=10), yaxis=dict(visible=False), xaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="section-title">Performance (Robôs vs Manuais vs Geral)</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="section-title">Tabela de Histórico</div>', unsafe_allow_html=True)
        if not df_tabela.empty:
            buf = io.BytesIO(); df_tabela.to_csv(buf, index=False, sep=';', encoding='utf-8-sig'); e1, e2 = st.columns([1, 2])
            e1.download_button("Exportar Histórico (CSV)", buf.getvalue(), f"historico_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True); e2.caption(f"{len(df_tabela)} registo(s) encontrado(s).")
            st.dataframe(df_tabela[['data_hora', 'banco_id', 'banco_nome', 'acao', 'detalhes', 'usuario_nome']], column_config={"banco_id": st.column_config.NumberColumn("ID Banco", format="%d")}, hide_index=True, use_container_width=True, height=380)
        else: st.info("Nenhum registo encontrado no histórico.")
    
    with st.expander("Configurações avançadas"):
        st.markdown('<div style="color:#dc3545;font-weight:bold;margin-bottom:10px;">Limpar Histórico do Período</div>', unsafe_allow_html=True)
        if st.button("Apagar Registos Filtrados", use_container_width=True, disabled=not st.checkbox("Sim, compreendo que a remoção é irreversível.", key="conf_apg")):
            if not df_tabela.empty and df_tabela['id'].tolist():
                conn = conectar_banco(); conn.execute(f"DELETE FROM historico WHERE id IN ({','.join(map(str, df_tabela['id'].tolist()))})"); conn.commit(); conn.close()
            st.success("Apagado!"); st.rerun()

def montar_df_top10_com_demais(df_sub):
    """Retorna os 9 maiores bancos e agrupa o restante na 10ª linha ('10º DEMAIS')."""
    if df_sub.empty:
        return pd.DataFrame(columns=['origem', 'qtd', 'detalhe'])
    grp = df_sub.groupby('origem').size().reset_index(name='qtd').sort_values('qtd', ascending=False)
    if len(grp) > 9:
        top9 = grp.iloc[:9].copy()
        top9['detalhe'] = top9['origem']
        resto = grp.iloc[9:]
        resumo_resto = ", ".join([f"{r['origem']} ({r['qtd']})" for _, r in resto.head(8).iterrows()]) + ("..." if len(resto) > 8 else "")
        linha_demais = pd.DataFrame([{
            'origem': '10º DEMAIS',
            'qtd': int(resto['qtd'].sum()),
            'detalhe': f"Agrupado ({len(resto)} bancos): {resumo_resto}"
        }])
        return pd.concat([top9, linha_demais], ignore_index=True)
    else:
        grp['detalhe'] = grp['origem']
        return grp

def renderizar_relatorio_virtaus():
    inicializar_banco_virtaus()
    aplicar_css("uploader_compacto", "virtaus")

    conn_v = conectar_banco_virtaus()
    rows_v = conn_v.execute("SELECT * FROM virtaus_registros ORDER BY id DESC").fetchall()
    conn_v.close()

    todas_origens = sorted(list({str(r['origem']).strip() for r in rows_v if r['origem']}))

    adm = st.session_state.get('is_admin', 0) == 1
    p_sta = adm or st.session_state.get('perm_status', 0) == 1
    p_add = adm or st.session_state.get('perm_adicionar', 0) == 1
    p_edi = adm or st.session_state.get('perm_editar', 0) == 1

    # Barra Superior (Quadradinho original + Período + Filtro de Banco + Definir Robôs)
    c_up, c_flt_dt, c_flt_bco, c_cfg_robo = st.columns([1.6, 1.4, 1.6, 1.1], gap="small", vertical_alignment="center")
    
    with c_up:
        if p_sta or p_add:
            arqs_virtaus = st.file_uploader("Importar XLSX", type=["xlsx"], accept_multiple_files=True, key="uploader_virtaus_rel", label_visibility="collapsed")
            if arqs_virtaus:
                assinatura_v = "|".join(sorted([f"{a.name}:{a.size}" for a in arqs_virtaus]))
                if st.session_state.get('_ult_arq_virtaus_rel') != assinatura_v:
                    qtd, n_arqs, err = importar_planilha_virtaus(arqs_virtaus)
                    st.session_state['_ult_arq_virtaus_rel'] = assinatura_v
                    if err:
                        st.error(f"Erro ao importar: {err}")
                    else:
                        st.toast(f"{qtd} registo(s) importado(s) com sucesso.", icon="✅")
                        st.rerun()

    if not rows_v:
        with c_flt_dt:
            st.date_input("Período", value=[], format="DD/MM/YYYY", key="dt_rel_virtaus_empty", disabled=True, label_visibility="collapsed")
        with c_flt_bco:
            st.multiselect("Banco", options=[], placeholder="Filtrar banco...", disabled=True, label_visibility="collapsed")
        with c_cfg_robo:
            st.button("Definir Robôs", disabled=True, use_container_width=True)
        st.info("Nenhum registo do Virtaus importado. Arraste o ficheiro .xlsx no quadrado acima.")
        return

    df_v_full = pd.DataFrame([dict(r) for r in rows_v])
    mapa_robos = obter_mapa_robos_virtaus(todas_origens)

    def parse_dt_row(r):
        if r.get('data_iso'):
            try: return datetime.strptime(r['data_iso'], '%Y-%m-%d').date()
            except: pass
        try: return datetime.strptime(str(r.get('data_ref', ''))[:10], '%d/%m/%Y').date()
        except: return None

    df_v_full['dt_obj'] = df_v_full.apply(parse_dt_row, axis=1)
    df_v_full['is_robo'] = df_v_full.apply(lambda r: eh_registro_robo_virtaus(r, mapa_robos), axis=1)

    with c_flt_dt:
        datas_v = st.date_input("Período", value=[], format="DD/MM/YYYY", key="dt_rel_virtaus", label_visibility="collapsed")
    with c_flt_bco:
        bancos_sel = st.multiselect("Banco (Origem)", options=todas_origens, placeholder="Filtrar por banco...", label_visibility="collapsed")
    with c_cfg_robo:
        if p_edi or p_add or p_sta:
            with st.popover("Definir Robôs", use_container_width=True):
                st.markdown("<div class='virtaus-popover-title'>Origens que são Robôs</div><div class='virtaus-popover-desc'>Selecione as origens de robô. Nota: se tiver <b>'Manual'</b> na classificação ou no nome do arquivo vai para Manual, e se tiver <b>'Robô'</b> vai para Robô.</div>", unsafe_allow_html=True)
                atuais_robos = [o for o in todas_origens if mapa_robos.get(o, False)]
                selecionados_robos = st.multiselect(
                    "Origens Robô",
                    options=todas_origens,
                    default=atuais_robos,
                    label_visibility="collapsed",
                    key="ms_cfg_robos_virtaus"
                )
                if st.button("Guardar Classificação", type="primary", use_container_width=True, key="btn_salvar_robos_v"):
                    conn_v = conectar_banco_virtaus()
                    for o in todas_origens:
                        o_up = o.strip().upper()
                        val_r = 1 if o in selecionados_robos else 0
                        conn_v.execute(
                            "INSERT OR REPLACE INTO virtaus_origens_config (origem, is_robo) VALUES (?, ?)",
                            (o_up, val_r)
                        )
                    conn_v.commit()
                    conn_v.close()
                    st.toast("Classificação de Robôs/Manuais atualizada!", icon="✅")
                    st.rerun()

    df_v = df_v_full.copy()
    if len(datas_v) >= 1:
        di_v, df_v_dt = datas_v[0], datas_v[-1]
        df_v = df_v[df_v['dt_obj'].notnull() & (df_v['dt_obj'] >= di_v) & (df_v['dt_obj'] <= df_v_dt)]

    if bancos_sel:
        df_v = df_v[df_v['origem'].isin(bancos_sel)]

    if df_v.empty:
        st.warning("Nenhum registo encontrado para os filtros aplicados.")
        return

    st.write("")
    # Métricas + Média por Dia (Manual primeiro, depois Robô!)
    total_reg = len(df_v)
    qtd_robos = int(df_v['is_robo'].sum())
    qtd_manuais = total_reg - qtd_robos

    df_man_media = df_v[~df_v['is_robo']]
    df_rob_media = df_v[df_v['is_robo']]

    # Dias úteis únicos de cada modalidade (segunda a sexta), mantendo todos os arquivos (inclusive iCred) no cálculo!
    dias_uteis_man = max(1, len({d for d in df_man_media['dt_obj'].dropna() if d.weekday() < 5}))
    dias_uteis_rob = max(1, len({d for d in df_rob_media['dt_obj'].dropna() if d.weekday() < 5}))
    dias_uteis_tot = max(1, len({d for d in df_v['dt_obj'].dropna() if d.weekday() < 5}))

    media_dia_manual = round(qtd_manuais / dias_uteis_man)
    media_dia_robo = round(qtd_robos / dias_uteis_rob)
    media_dia_total = total_reg / dias_uteis_tot

    k1, k2, k3 = st.columns(3, gap="small")
    k1.markdown(f'<div class="stat-card compact"><h3>Total de Arquivos</h3><div class="number">{total_reg}</div><div class="stat-sub">{dias_uteis_tot} dia(s) · Média: <b>{media_dia_total:.1f}/dia</b></div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="stat-card compact"><h3>Manual vs Robô (Total)</h3><div class="number"><span class="txt-laranja">{qtd_manuais}</span> <span class="txt-sep">/</span> <span class="txt-azul">{qtd_robos}</span></div><div class="stat-sub"><span class="txt-laranja-claro">Manual</span> vs <span class="txt-azul-claro">Robô</span></div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="stat-card compact"><h3>Média por Dia (Manual / Robô)</h3><div class="number"><span class="txt-laranja">{media_dia_manual}</span> <span class="txt-sep">/</span> <span class="txt-azul">{media_dia_robo}</span></div><div class="stat-sub">arquivos por dia</div></div>', unsafe_allow_html=True)

    st.write("")

    # 1. EVOLUÇÃO MENSAL DE ARQUIVOS: JUNTO EM UM ÚNICO QUADRO COM MANUAL EM CIMA (LARANJA) E ROBÔ ABAIXO (AZUL)
    with st.container():
        st.markdown('<div class="section-title" style="font-size:15px; margin-bottom:6px;">Evolução Mensal de Arquivos (Últimos 6 Meses) e Variação (%) vs Mês Anterior</div>', unsafe_allow_html=True)
        st.markdown('<div class="legenda-mr"><span class="lm"><b>Manual</b> (em cima · Laranja)</span><span class="lr"><b>Robô</b> (abaixo · Azul)</span></div>', unsafe_allow_html=True)

        df_mes_base = df_v_full[df_v_full['origem'].isin(bancos_sel)].copy() if bancos_sel else df_v_full.copy()
        df_mes_base = df_mes_base[df_mes_base['dt_obj'].notnull()].copy()
        
        if not df_mes_base.empty and TEM_PLOTLY:
            from plotly.subplots import make_subplots

            df_mes_base['ano_mes'] = df_mes_base['dt_obj'].apply(lambda d: f"{d.year}-{d.month:02d}")
            df_mes_base['mes_label'] = df_mes_base['dt_obj'].apply(lambda d: f"{MESES_PT.get(d.month, d.month)}/{str(d.year)[2:]}")
            
            todos_meses = sorted(df_mes_base['ano_mes'].unique().tolist())
            # Exibe de 6 em 6 meses (últimos 6 meses cadastrados)
            meses_ord = todos_meses[-6:] if len(todos_meses) > 6 else todos_meses
            labels_x = [df_mes_base[df_mes_base['ano_mes'] == m]['mes_label'].iloc[0] for m in meses_ord]
            
            vals_total = [len(df_mes_base[df_mes_base['ano_mes'] == m]) for m in meses_ord]
            vals_robo = [int(df_mes_base[df_mes_base['ano_mes'] == m]['is_robo'].sum()) for m in meses_ord]
            vals_manual = [t_m - r_m for t_m, r_m in zip(vals_total, vals_robo)]

            def montar_textos_com_variacao(lista_valores):
                textos, hovers = [], []
                for idx_v, val_atual in enumerate(lista_valores):
                    if idx_v == 0:
                        textos.append(f"<b>{val_atual}</b>")
                        hovers.append("Mês base inicial")
                    else:
                        val_ant = lista_valores[idx_v - 1]
                        if val_ant > 0:
                            diff_pct = ((val_atual - val_ant) / val_ant) * 100.0
                            sinal = "+" if diff_pct >= 0 else ""
                            textos.append(f"<b>{val_atual}</b> ({sinal}{diff_pct:.1f}%)")
                            hovers.append(f"{sinal}{diff_pct:.1f}% vs {labels_x[idx_v - 1]} ({val_ant})")
                        elif val_atual > 0:
                            textos.append(f"<b>{val_atual}</b> (+100%)")
                            hovers.append(f"+100% vs {labels_x[idx_v - 1]} (0)")
                        else:
                            textos.append(f"<b>{val_atual}</b> (0%)")
                            hovers.append(f"0% vs {labels_x[idx_v - 1]}")
                return textos, hovers

            txts_man, hvs_man = montar_textos_com_variacao(vals_manual)
            txts_rob, hvs_rob = montar_textos_com_variacao(vals_robo)

            # Um único gráfico unificado: faixa superior = Manual (Laranja) | faixa inferior = Robô (Azul)
            fig_unificado = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.14,
                subplot_titles=(
                    "<span style='color:#fb923c;font-size:13px;'><b>Manual (Laranja)</b></span>",
                    "<span style='color:#60a5fa;font-size:13px;'><b>Robô (Azul)</b></span>"
                )
            )

            # Linha 1 (Em cima): Manual (Laranja)
            fig_unificado.add_trace(go.Scatter(
                x=labels_x,
                y=vals_manual,
                mode='lines+markers+text',
                name='Manual',
                text=txts_man,
                customdata=hvs_man,
                textposition='top center',
                textfont=dict(size=12.5, color='#f8fafc', family='Segoe UI, sans-serif'),
                line=dict(color='#ea580c', width=3.5),
                marker=dict(symbol='circle', color='#c2410c', size=11, line=dict(color='#ffffff', width=1.8)),
                cliponaxis=False,
                hovertemplate="<b>%{x} — Manual</b><br>Quantidade: <b>%{y}</b> arquivo(s)<br>Variação: %{customdata}<extra></extra>"
            ), row=1, col=1)

            # Linha 2 (Abaixo): Robô (Azul)
            fig_unificado.add_trace(go.Scatter(
                x=labels_x,
                y=vals_robo,
                mode='lines+markers+text',
                name='Robô',
                text=txts_rob,
                customdata=hvs_rob,
                textposition='top center',
                textfont=dict(size=12.5, color='#f8fafc', family='Segoe UI, sans-serif'),
                line=dict(color='#3b82f6', width=3.5),
                marker=dict(symbol='circle', color='#1d4ed8', size=11, line=dict(color='#ffffff', width=1.8)),
                cliponaxis=False,
                hovertemplate="<b>%{x} — Robô</b><br>Quantidade: <b>%{y}</b> arquivo(s)<br>Variação: %{customdata}<extra></extra>"
            ), row=2, col=1)

            max_m, min_m = max(vals_manual + [1]), min(vals_manual + [0])
            max_r, min_r = max(vals_robo + [1]), min(vals_robo + [0])
            
            fig_unificado.update_yaxes(
                visible=False,
                range=[max(-0.5, min_m * 0.65) if len(labels_x) > 1 else -0.5, max(max_m * 1.42, max_m + 5)],
                fixedrange=True,
                row=1, col=1
            )
            fig_unificado.update_yaxes(
                visible=False,
                range=[max(-0.5, min_r * 0.65) if len(labels_x) > 1 else -0.5, max(max_r * 1.42, max_r + 5)],
                fixedrange=True,
                row=2, col=1
            )
            fig_unificado.update_xaxes(
                type='category',
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                fixedrange=True,
                row=1, col=1
            )
            fig_unificado.update_xaxes(
                type='category',
                showgrid=False,
                zeroline=False,
                showticklabels=True,
                tickfont=dict(color='#e2e8f0', size=12.5),
                fixedrange=True,
                row=2, col=1
            )

            # Linha divisória sutil entre a faixa Manual (cima) e Robô (baixo) dentro do mesmo quadro
            fig_unificado.add_shape(
                type="line", xref="paper", yref="paper",
                x0=0.0, x1=1.0, y0=0.48, y1=0.48,
                line=dict(color="#232836", width=1, dash="dot")
            )

            for ann in fig_unificado['layout']['annotations']:
                ann['x'] = 0.01
                ann['xanchor'] = 'left'

            fig_unificado.update_layout(
                paper_bgcolor='#14171f',
                plot_bgcolor='#14171f',
                height=310,
                margin=dict(l=40, r=40, t=32, b=28),
                showlegend=False
            )
            st.plotly_chart(fig_unificado, use_container_width=True)

    st.write("")

    # 2. OS 10 MAIORES DE CADA UM SEPARADO (TOP 10 MANUAL + 10º DEMAIS  vs  TOP 10 ROBÔ + 10º DEMAIS)
    st.markdown('<div class="section-title" style="font-size:15px;">Comparação Top 10 Maiores Bancos (10º = DEMAIS) — Manual vs Robô (Separados)</div>', unsafe_allow_html=True)
    col_top_man, col_top_rob = st.columns(2, gap="large")

    df_so_manual = df_v[~df_v['is_robo']]
    df_so_robo = df_v[df_v['is_robo']]

    top10_man_df = montar_df_top10_com_demais(df_so_manual)
    top10_rob_df = montar_df_top10_com_demais(df_so_robo)

    def renderizar_barra_top10(df_top, titulo_graf, cor_barra):
        if df_top.empty:
            st.info(f"Sem registos para {titulo_graf} no período.")
            return
        df_plot = df_top.iloc[::-1]
        max_x = max(df_plot['qtd'].tolist() + [1])
        fig_b = go.Figure(go.Bar(
            y=df_plot['origem'],
            x=df_plot['qtd'],
            customdata=df_plot['detalhe'],
            orientation='h',
            marker=dict(color=cor_barra, line=dict(color='#0f1115', width=1)),
            text=[f"<b>{v}</b>" for v in df_plot['qtd']],
            textposition='outside',
            cliponaxis=False,
            textfont=dict(color='#f8fafc', size=12.5, family='Segoe UI, sans-serif'),
            hovertemplate="<b>%{y}</b><br>Arquivos: <b>%{x}</b><br>%{customdata}<extra></extra>"
        ))
        fig_b.update_layout(
            title=dict(text=f"<b>{titulo_graf}</b>", font=dict(size=14, color='#f8fafc'), x=0.01, y=0.96),
            paper_bgcolor='#14171f',
            plot_bgcolor='#14171f',
            height=420,
            margin=dict(l=15, r=55, t=42, b=25),
            showlegend=False,
            xaxis=dict(
                showgrid=True,
                gridcolor='#1e2433',
                zeroline=False,
                range=[0, max_x * 1.22],
                tickfont=dict(color='#cbd5e1', size=11.5)
            ),
            yaxis=dict(
                showgrid=False,
                automargin=True,
                tickfont=dict(color='#f8fafc', size=12)
            )
        )
        st.plotly_chart(fig_b, use_container_width=True)

    with col_top_man:
        if TEM_PLOTLY:
            renderizar_barra_top10(top10_man_df, "Top 10 Bancos — Manual (10º = DEMAIS)", "#ea580c")

    with col_top_rob:
        if TEM_PLOTLY:
            renderizar_barra_top10(top10_rob_df, "Top 10 Bancos — Robô (10º = DEMAIS)", "#3b82f6")

    st.write("")

    # 3. GRÁFICO DE PIZZA MAIOR (COM ESPAÇO AMPLO PARA OS NOMES EXTERNOS NÃO CORTAREM) + ORGANIZAÇÃO POR BANCOS E MOTIVOS
    col_grafico, col_motivos = st.columns([1.25, 1.25], gap="large")

    with col_grafico:
        st.markdown('<div class="section-title" style="font-size:15px;">Visão Geral Virtaus (Gráfico Único)</div>', unsafe_allow_html=True)
        modo_pizza = st.radio(
            "Agrupamento",
            ["Por Banco (Origem)", "Por Status / Motivo", "Manual vs Robô"],
            horizontal=True,
            label_visibility="collapsed",
            key="modo_pizza_virtaus"
        )

        if TEM_PLOTLY:
            if modo_pizza == "Por Banco (Origem)":
                # Mantém o agrupamento < 3% como "DEMAIS" APENAS para "Por Banco (Origem)"
                agrupado = df_v.groupby('origem').agg(
                    qtd=('id', 'count'),
                    status_resumo=('status', lambda x: ', '.join([f"{k} ({v})" for k, v in x.value_counts().items()]))
                ).reset_index().sort_values('qtd', ascending=False)
                labels_raw = agrupado['origem'].tolist()
                vals_raw = agrupado['qtd'].tolist()
                custom_raw = agrupado['status_resumo'].tolist()
                labels_pie, vals_pie, custom_pie = agrupar_menores_3_porcento(labels_raw, vals_raw, custom_raw)
                cores_pie = None
                hover_tmpl = "<b>%{label}</b><br>Registos: %{value} (%{percent})<br>Detalhes: %{customdata}<extra></extra>"

            elif modo_pizza == "Por Status / Motivo":
                agrupado = df_v.groupby('status').agg(
                    qtd=('id', 'count'),
                    bancos=('origem', lambda x: ', '.join(sorted(set(x))[:5]) + ('...' if len(set(x)) > 5 else ''))
                ).reset_index().sort_values('qtd', ascending=False)
                labels_pie = agrupado['status'].tolist()
                vals_pie = agrupado['qtd'].tolist()
                custom_pie = agrupado['bancos'].tolist()
                
                cores_pie = [classificar_cor_status_virtaus(s)[0] for s in labels_pie]
                paleta_extra = ['#10b981', '#ef4444', '#8b5cf6', '#3b82f6', '#f59e0b', '#06b6d4', '#f97316', '#ec4899', '#14b8a6', '#64748b']
                if len(set(cores_pie)) < min(len(cores_pie), 3):
                    cores_pie = [paleta_extra[idx % len(paleta_extra)] for idx in range(len(labels_pie))]
                hover_tmpl = "<b>%{label}</b><br>Quantidade: %{value} (%{percent})<br>Bancos: %{customdata}<extra></extra>"
            
            else:
                labels_pie = ["Manual", "Robô"]
                vals_pie = [qtd_manuais, qtd_robos]
                bcos_m = ", ".join(sorted(df_v[~df_v['is_robo']]['origem'].unique().tolist())[:6]) or "Nenhum"
                bcos_r = ", ".join(sorted(df_v[df_v['is_robo']]['origem'].unique().tolist())[:6]) or "Nenhum"
                custom_pie = [bcos_m, bcos_r]
                cores_pie = ['#ea580c', '#3b82f6']
                hover_tmpl = "<b>%{label}</b><br>Arquivos: %{value} (%{percent})<br>Principais Bancos: %{customdata}<extra></extra>"

            # Domínio central ajustado (x=[0.14, 0.86], y=[0.12, 0.88]) e margens amplas para que os nomes fora da pizza e as setinhas apareçam 100% sem cortar!
            fig_v = go.Figure(data=[go.Pie(
                labels=labels_pie,
                values=vals_pie,
                customdata=custom_pie,
                domain=dict(x=[0.14, 0.86], y=[0.12, 0.88]),
                hole=0.48,
                marker=dict(colors=cores_pie, line=dict(color='#0f1115', width=2.5)) if cores_pie else dict(line=dict(color='#0f1115', width=2.5)),
                textinfo='label+percent',
                textposition='outside',
                outsidetextfont=dict(size=12.5, color='#ffffff', family='Segoe UI, sans-serif'),
                automargin=True,
                pull=[0.02] * len(labels_pie),
                hovertemplate=hover_tmpl
            )])
            fig_v.update_layout(
                paper_bgcolor='#14171f',
                plot_bgcolor='#14171f',
                height=500,
                margin=dict(l=80, r=80, t=55, b=65),
                showlegend=True,
                legend=dict(orientation="h", yanchor="top", y=-0.04, xanchor="center", x=0.5, font=dict(color='#f8fafc', size=12)),
                annotations=[dict(text=f"<span style='font-size:24px;font-weight:800;color:#ffffff'>{total_reg}</span><br><span style='font-size:12px;color:#94a3b8'>Arquivos</span>", x=0.5, y=0.5, showarrow=False)]
            )
            st.plotly_chart(fig_v, use_container_width=True)

    with col_motivos:
        c_tit_m, c_busca_m = st.columns([1.2, 1.3], vertical_alignment="center")
        with c_tit_m:
            st.markdown('<div class="section-title" style="font-size:15px; margin-bottom:0;">Organização por Bancos e Motivos</div>', unsafe_allow_html=True)
        with c_busca_m:
            busca_motivos = st.text_input("Pesquisar banco, motivo, arquivo ou data", placeholder="🔎 Pesquisar banco, motivo ou manual/robô...", label_visibility="collapsed", key="busca_bancos_motivos_virtaus")

        df_motivos = df_v.copy()
        if busca_motivos and busca_motivos.strip():
            termo_m = busca_motivos.strip().lower()
            mask_m = (
                df_motivos['origem'].astype(str).str.lower().str.contains(termo_m, na=False) |
                df_motivos['status'].astype(str).str.lower().str.contains(termo_m, na=False) |
                df_motivos['motivo'].astype(str).str.lower().str.contains(termo_m, na=False) |
                df_motivos['arquivo'].astype(str).str.lower().str.contains(termo_m, na=False) |
                df_motivos['data_ref'].astype(str).str.lower().str.contains(termo_m, na=False) |
                (df_motivos['is_robo'] & ('robo' in termo_m or 'robô' in termo_m)) |
                ((~df_motivos['is_robo']) & ('manual' in termo_m))
            )
            df_motivos = df_motivos[mask_m]

        origens_unicas = sorted(df_motivos['origem'].dropna().unique().tolist())
        with st.container(height=500):
            if not origens_unicas:
                st.info("Nenhum banco ou motivo encontrado para esta pesquisa.")
            for orig in origens_unicas:
                sub = df_motivos[df_motivos['origem'] == orig]
                qtd_b = len(sub)
                orig_esc = html.escape(str(orig))
                
                linhas_html = []
                for _, r_item in sub.iterrows():
                    st_val = html.escape(str(r_item.get('status') or ''))
                    dt_val = html.escape(str(r_item.get('data_ref') or ''))
                    arq_item = html.escape(str(r_item.get('arquivo') or ''))
                    eh_r_item = bool(r_item.get('is_robo', False))
                    tag_item = '<span class="tag-tipo tag-robo">Robô</span>' if eh_r_item else '<span class="tag-tipo tag-manual">Manual</span>'
                    lidas_i = r_item.get('lidas', 0)
                    proc_i = r_item.get('processadas', 0)
                    pend_i = r_item.get('pendentes', 0)
                    cor_hex, _ = classificar_cor_status_virtaus(st_val)
                    det_num = f" · Lidas: {lidas_i} | Proc: {proc_i} | Pend: {pend_i}" if (lidas_i or proc_i or pend_i) else ""
                    
                    linha = (
                        f'<div class="bco-item-row" style="border-left: 3px solid {cor_hex};">'
                        f'<div class="bco-item-main">'
                        f'<div class="bco-item-status-line"><span style="color:{cor_hex};">{st_val}</span> {tag_item}</div>'
                        f'<div class="bco-item-file" title="{arq_item}">{arq_item}{det_num}</div>'
                        f'</div>'
                        f'<div class="bco-item-date">{dt_val}</div>'
                        f'</div>'
                    )
                    linhas_html.append(linha)

                card_completo = (
                    f'<div class="bco-group-card">'
                    f'<div class="bco-group-header">'
                    f'<span class="bco-group-name">{orig_esc}</span>'
                    f'<span class="bco-group-badge">{qtd_b} registo(s)</span>'
                    f'</div>'
                    f'{"".join(linhas_html)}'
                    f'</div>'
                )
                st.markdown(card_completo, unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    with st.container(key="card_tabela_virtaus"):
        st.markdown('<div class="section-title" style="font-size:14.5px;">Tabela de Registos (Origem | Data | Status)</div>', unsafe_allow_html=True)
        df_mostrar = df_v.copy()
        df_mostrar['modal_tipo'] = df_mostrar['is_robo'].apply(lambda x: 'Robô' if x else 'Manual')
        cols_exibir = ['origem', 'modal_tipo', 'data_ref', 'status', 'motivo', 'tipo_origem', 'arquivo', 'lidas', 'processadas', 'pendentes', 'data_importacao']
        cols_presentes = [c for c in cols_exibir if c in df_mostrar.columns]
        df_mostrar = df_mostrar[cols_presentes].rename(columns={
            'origem': 'Origem',
            'modal_tipo': 'Classificação',
            'data_ref': 'Data',
            'status': 'Status',
            'motivo': 'Motivo',
            'tipo_origem': 'Tipo Origem',
            'arquivo': 'Arquivo',
            'lidas': 'Lidas',
            'processadas': 'Processadas',
            'pendentes': 'Pendentes',
            'data_importacao': 'Importado em'
        })
        buf_v = io.BytesIO()
        df_mostrar.to_csv(buf_v, index=False, sep=';', encoding='utf-8-sig')
        ev1, ev2 = st.columns([1, 2])
        ev1.download_button("Exportar CSV", buf_v.getvalue(), f"virtaus_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
        ev2.caption(f"{len(df_mostrar)} registo(s) listado(s).")
        st.dataframe(df_mostrar, hide_index=True, use_container_width=True, height=300)

    if adm or p_edi:
        with st.expander("Gerir Dados do Virtaus"):
            if st.button("Apagar Registos Filtrados", use_container_width=True, disabled=not st.checkbox("Confirmo que desejo remover estes registos.", key="conf_apg_virtaus")):
                ids_remover = df_v['id'].tolist()
                if ids_remover:
                    conn_v = conectar_banco_virtaus()
                    conn_v.execute(f"DELETE FROM virtaus_registros WHERE id IN ({','.join(map(str, ids_remover))})")
                    conn_v.commit()
                    conn_v.close()
                    st.success("Registos removidos.")
                    st.rerun()

def pagina_relatorios():
    adm = st.session_state.get('is_admin', 0) == 1
    p_rel = adm or st.session_state.get('perm_relatorios', 0) == 1
    
    if not p_rel: st.error("Acesso restrito."); return

    if "tipo_relatorio_aba" not in st.session_state:
        st.session_state.tipo_relatorio_aba = "Integração"

    h_col1, h_col2 = st.columns([2.8, 1.2], vertical_alignment="center")
    with h_col1:
        titulo_aba = "Relatórios — Integrações" if st.session_state.tipo_relatorio_aba == "Integração" else "Relatórios — Virtaus"
        st.markdown(f'<div class="header-container" style="margin-bottom:10px;"><span class="header-title" style="color:#fff; font-size:1.9em;">{titulo_aba}</span></div>', unsafe_allow_html=True)
    with h_col2:
        b_int, b_vir = st.columns(2, gap="small")
        is_int = st.session_state.tipo_relatorio_aba == "Integração"
        if b_int.button("Integração", type="primary" if is_int else "secondary", use_container_width=True, key="btn_sel_rel_int"):
            st.session_state.tipo_relatorio_aba = "Integração"
            st.rerun()
        if b_vir.button("Virtaus", type="primary" if not is_int else "secondary", use_container_width=True, key="btn_sel_rel_vir"):
            st.session_state.tipo_relatorio_aba = "Virtaus"
            st.rerun()

    if st.session_state.tipo_relatorio_aba == "Integração":
        renderizar_relatorio_integracao()
    else:
        renderizar_relatorio_virtaus()
