import sqlite3, os, hashlib, base64, streamlit as st
from datetime import datetime, timedelta

def hash_senha(senha): return hashlib.sha256(senha.encode()).hexdigest()

def obter_base64_imagem(nome_base):
    for ext in ['png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG']:
        caminho = f"imagens/{nome_base}.{ext}"
        if os.path.exists(caminho):
            mime = 'jpeg' if ext.lower() in ['jpg', 'jpeg'] else 'png'
            try:
                with open(caminho, 'rb') as f:
                    return f"url('data:image/{mime};base64,{base64.b64encode(f.read()).decode()}')"
            except: pass
    return "none"

def conectar_banco():
    for f in ['bancos.db', 'bancos', 'banco.db', 'banco']:
        if os.path.exists(f) and os.path.isfile(f): db = f; break
    else: db = 'bancos.db'
    c = sqlite3.connect(db, timeout=10, check_same_thread=False); c.row_factory = sqlite3.Row; return c

def registrar_historico(conn, banco_id, banco_nome, acao, det="", data_acao=None):
    dh = data_acao or datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    conn.execute('INSERT INTO historico (banco_id, banco_nome, acao, detalhes, data_hora, usuario_id, usuario_nome) VALUES (?,?,?,?,?,?,?)', 
                 (banco_id, banco_nome, acao, det, dh, st.session_state.get('usuario_id', 0), st.session_state.get('usuario_nome', 'Sistema')))

def inicializar_banco():
    conn = conectar_banco()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bancos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, logo_url TEXT, status TEXT DEFAULT 'PENDENTE', motivo_erro TEXT DEFAULT '', ultimo_erro TEXT DEFAULT '', ultima_atualizacao TEXT, lixeira INTEGER DEFAULT 0, ordem INTEGER DEFAULT 0, motivo_pendencia TEXT DEFAULT '', ultimo_erro_data TEXT DEFAULT '', motivo_pendencia_data TEXT DEFAULT '', observacao TEXT DEFAULT ''); 
        CREATE TABLE IF NOT EXISTS historico (id INTEGER PRIMARY KEY AUTOINCREMENT, banco_id INTEGER, banco_nome TEXT NOT NULL, acao TEXT NOT NULL, detalhes TEXT, data_hora TEXT NOT NULL); 
        CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT); 
        CREATE TABLE IF NOT EXISTS motivos_padrao (id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, login TEXT UNIQUE NOT NULL, senha TEXT NOT NULL, is_admin INTEGER DEFAULT 0);
    """)
    for col, tipo in [("ordem", "INTEGER DEFAULT 0"), ("motivo_pendencia", "TEXT DEFAULT ''"), ("ultimo_erro_data", "TEXT DEFAULT ''"), ("motivo_pendencia_data", "TEXT DEFAULT ''"), ("observacao", "TEXT DEFAULT ''"), ("banco_id", "INTEGER"), ("is_robo", "INTEGER DEFAULT -1"), ("usuario_id", "INTEGER DEFAULT 0"), ("usuario_nome", "TEXT DEFAULT 'Sistema'")]:
        try: 
            if col in ['banco_id', 'usuario_id', 'usuario_nome']: conn.execute(f"ALTER TABLE historico ADD COLUMN {col} {tipo}")
            else: 
                conn.execute(f"ALTER TABLE bancos ADD COLUMN {col} {tipo}")
                if col == 'is_robo': conn.execute("UPDATE bancos SET is_robo = 1 WHERE nome LIKE '%ROBÔ%' OR nome LIKE '%ROBO%'"); conn.execute("UPDATE bancos SET is_robo = 0 WHERE is_robo = -1")
            conn.commit()
        except sqlite3.OperationalError: pass
    
    try: conn.execute("ALTER TABLE usuarios ADD COLUMN is_admin INTEGER DEFAULT 0"); conn.commit()
    except sqlite3.OperationalError: pass
    for col in ['perm_relatorios', 'perm_adicionar', 'perm_editar', 'perm_status']:
        try: conn.execute(f"ALTER TABLE usuarios ADD COLUMN {col} INTEGER DEFAULT 1"); conn.commit()
        except sqlite3.OperationalError: pass
        
    try: conn.execute("ALTER TABLE usuarios ADD COLUMN perm_usuarios INTEGER DEFAULT 0"); conn.commit()
    except sqlite3.OperationalError: pass
        
    conn.execute("UPDATE usuarios SET is_admin = 1 WHERE login = 'admin' OR id = 1"); conn.commit()
    
    if conn.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0] == 0:
        conn.execute('INSERT INTO usuarios (nome, login, senha, is_admin) VALUES (?, ?, ?, 1)', ('Administrador', 'admin', hash_senha('admin123')))
    if conn.execute('SELECT COUNT(*) FROM bancos WHERE ordem != 0').fetchone()[0] == 0: conn.execute('UPDATE bancos SET ordem = id')
    if conn.execute('SELECT COUNT(*) FROM motivos_padrao').fetchone()[0] == 0:
        conn.executemany('INSERT INTO motivos_padrao (texto) VALUES (?)', [("Aguardando retorno do banco",), ("Sem prioridade hoje",), ("Aguardando aprovação interna",), ("Banco fora do ar",), ("Documentação pendente",)])
    
    if conn.execute("SELECT COUNT(*) FROM bancos").fetchone()[0] == 0:
        lista = ["BB_Consig", "BB Conta digital", "Pan MASTER", "PAN INDICADOS", "BANRISUL", "BMG", "BRB", "DAYCOVAL CARTÃO", "DAYCOVAL CONSIGNADO", "BTW", "C6 AP", "C6 INDICADOS", "CAIXA", "CAPITAL", "CRED CAPITAL", "FACTA AP (TEM O ROBÔ E O DE 10 HRS)", "FACTA AD (TEM O ROBÔ E O DE 10 HRS)", "CREFISA", "CREFAZ", "FUTURO", "HAPPY", "MCC", "NBC", "WORKBANK NBC", "NEON", "ICRED", "ICRED WORKBANK", "QUALIBANK", "DIGIO", "AMIGOZ CONSIGNADO", "AMIGOZ CARTÃO", "SAFRA", "SANTANDER NOVO", "SANTANDER REFIN", "PRESENÇA", "ACREDITO", "C6 AUTO", "C6 CAR EQUITY", "BMG INDICADOS", "PARANA"]
        agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
        for i, n in enumerate(lista, 1): 
            c = conn.execute('INSERT INTO bancos (nome, ultima_atualizacao, ordem, is_robo) VALUES (?, ?, ?, ?)', (n, agora, i, 1 if ('ROBO' in n.upper() or 'ROBÔ' in n.upper()) else 0))
            registrar_historico(conn, c.lastrowid, n, "Banco Adicionado", "Importação inicial automática.")
    conn.commit(); conn.close()

def verificar_rotinas():
    conn = conectar_banco()
    hoje, hoje_str = datetime.now(), datetime.now().strftime("%Y-%m-%d")
    
    row = conn.execute("SELECT valor FROM configuracoes WHERE chave = 'ultimo_reset_diario'").fetchone()
    if not row: conn.execute("INSERT INTO configuracoes (chave, valor) VALUES ('ultimo_reset_diario', ?)", (hoje_str,))
    elif row['valor'] != hoje_str:
        if hoje.weekday() < 5:
            conn.execute("UPDATE bancos SET observacao = CASE WHEN status = 'ERRO' THEN '⚠️ Lembrete: Banco com falha no dia ' || ultimo_erro_data || ' (' || motivo_erro || ')' ELSE '' END, status = 'PENDENTE', motivo_pendencia = '', motivo_pendencia_data = '', motivo_erro = '', ultima_atualizacao = ? WHERE lixeira = 0", (hoje.strftime("%d/%m/%Y às %H:%M"),))
            registrar_historico(conn, 0, "SISTEMA", "Reset Diário Automático", "Bancos resetados para PENDENTE.")
        conn.execute("UPDATE configuracoes SET valor = ? WHERE chave = 'ultimo_reset_diario'", (hoje_str,))
        
    banco = conn.execute("SELECT id, nome FROM bancos WHERE nome LIKE '%ICRED%' AND (nome LIKE '%ROBÔ%' OR nome LIKE '%ROBO%') AND lixeira = 0 LIMIT 1").fetchone()
    if banco:
        b_id, b_nome, agora = banco['id'], banco['nome'], datetime.now()
        row_hist = conn.execute("SELECT data_hora FROM historico WHERE banco_id = ? ORDER BY id DESC LIMIT 1", (b_id,)).fetchone()
        try: ultima_data = datetime.strptime(row_hist['data_hora'].replace(' às ', ' '), "%d/%m/%Y %H:%M:%S") if row_hist else agora.replace(hour=5, minute=0, second=0, microsecond=0)
        except: ultima_data = agora.replace(hour=5, minute=0, second=0, microsecond=0)
        
        ultima_data = max(ultima_data, agora - timedelta(days=3))
        hora_loop = ultima_data.replace(minute=0, second=0, microsecond=0) + (timedelta(hours=1) if ultima_data.minute > 0 or ultima_data.second > 0 else timedelta())
        
        registros, teve_atualizacao_hoje = [], False
        while hora_loop <= agora:
            if 5 <= hora_loop.hour <= 22 and not conn.execute("SELECT id FROM historico WHERE banco_id = ? AND data_hora LIKE ?", (b_id, hora_loop.strftime("%d/%m/%Y às %H:") + "%")).fetchone():
                registros.append((b_id, b_nome, 'Status Alterado', 'INTEGRADO (Robô Automático)', hora_loop.strftime("%d/%m/%Y às %H:00:00"), 0, 'Sistema'))
                if hora_loop.date() == agora.date(): teve_atualizacao_hoje = True
            hora_loop += timedelta(hours=1)
            
        if registros:
            conn.executemany("INSERT INTO historico (banco_id, banco_nome, acao, detalhes, data_hora, usuario_id, usuario_nome) VALUES (?,?,?,?,?,?,?)", registros)
            if teve_atualizacao_hoje: conn.execute("UPDATE bancos SET status='INTEGRADO', motivo_erro='', motivo_pendencia='', ultima_atualizacao=? WHERE id=?", (agora.strftime("%d/%m/%Y às %H:%M"), b_id))
    conn.commit(); conn.close()