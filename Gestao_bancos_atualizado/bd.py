import sqlite3, os, hashlib, base64, streamlit as st
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def hash_senha(senha): return hashlib.sha256(senha.encode()).hexdigest()

@st.cache_data(show_spinner=False)
def obter_base64_imagem(nome_base):
    pastas_img = [
        os.path.join(BASE_DIR, "imagens"),
        "imagens",
        os.path.join(BASE_DIR, "abas", "imagens")
    ]
    for pasta in pastas_img:
        for ext in ['png', 'jpg', 'jpeg', 'PNG', 'JPG', 'JPEG']:
            caminho = os.path.join(pasta, f"{nome_base}.{ext}")
            if os.path.exists(caminho):
                mime = 'jpeg' if ext.lower() in ['jpg', 'jpeg'] else 'png'
                try:
                    with open(caminho, 'rb') as f:
                        return f"url('data:image/{mime};base64,{base64.b64encode(f.read()).decode()}')"
                except: pass
    return "none"

PASTA_ESTILOS = os.path.join(BASE_DIR, "estilos")

@st.cache_data(show_spinner=False)
def _ler_css(caminho, _mtime):
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read()

def aplicar_css(*nomes):
    """Injeta um ou mais arquivos .css da pasta 'estilos/' (com cache; recarrega sozinho se o arquivo mudar)."""
    blocos = []
    for nome in nomes:
        arq = nome if nome.endswith(".css") else f"{nome}.css"
        caminho = os.path.join(PASTA_ESTILOS, arq)
        if os.path.exists(caminho):
            try:
                blocos.append(_ler_css(caminho, os.path.getmtime(caminho)))
            except Exception:
                pass
    if blocos:
        st.markdown(f"<style>{''.join(blocos)}</style>", unsafe_allow_html=True)

_CACHE_CAMINHOS_DB = {}

def _encontrar_caminho_db(nomes_possiveis, padrao):
    if padrao in _CACHE_CAMINHOS_DB and os.path.exists(_CACHE_CAMINHOS_DB[padrao]):
        return _CACHE_CAMINHOS_DB[padrao]
    pastas_busca = [
        BASE_DIR,
        os.path.join(BASE_DIR, "bancos"),
        os.path.join(BASE_DIR, "bancos_de_dados"),
        os.path.join(BASE_DIR, "db"),
        os.path.join(BASE_DIR, "dados"),
        os.path.join(BASE_DIR, "database"),
        os.path.join(BASE_DIR, "abas"),
        "."
    ]
    for pasta in pastas_busca:
        if os.path.exists(pasta) and os.path.isdir(pasta):
            for f in nomes_possiveis:
                caminho = os.path.join(pasta, f)
                if os.path.exists(caminho) and os.path.isfile(caminho):
                    _CACHE_CAMINHOS_DB[padrao] = caminho
                    return caminho
    # Se existir alguma pasta dedicada de banco criada pelo usuário, salva lá; senão na raiz
    for sub in ["bancos", "bancos_de_dados", "db", "dados", "database"]:
        p_sub = os.path.join(BASE_DIR, sub)
        if os.path.exists(p_sub) and os.path.isdir(p_sub):
            res = os.path.join(p_sub, padrao)
            _CACHE_CAMINHOS_DB[padrao] = res
            return res
    res = os.path.join(BASE_DIR, padrao)
    _CACHE_CAMINHOS_DB[padrao] = res
    return res

def conectar_banco():
    db = _encontrar_caminho_db(['bancos.db', 'bancos', 'banco.db', 'banco'], 'bancos.db')
    c = sqlite3.connect(db, timeout=10, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def conectar_banco_virtaus():
    db = _encontrar_caminho_db(['virtaus.db', 'virtaus', 'banco_virtaus.db'], 'virtaus.db')
    c = sqlite3.connect(db, timeout=10, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def extrair_assinatura_padrao_arquivo(nome_arq):
    """
    Extrai o esqueleto/padrão de um nome de arquivo de robô:
    - Remove extensão (.xlsx, .csv, .txt, etc.)
    - Substitui sequências de dígitos (datas, horas, códigos) por '#'
    - Normaliza espaços e maiúsculas
    Ex: 'Rel_Pan_20261022_01.xlsx' -> 'REL_PAN_#_#'
    """
    import re
    s = str(nome_arq or '').strip()
    if not s or s.lower() in ['nan', 'none']:
        return ''
    s = re.sub(r'\.[a-zA-Z0-9]{2,5}$', '', s)
    s = re.sub(r'\d+', '#', s)
    s = re.sub(r'[\s\-_]+', '_', s).strip('_').upper()
    return s

def inicializar_banco_virtaus():
    conn = conectar_banco_virtaus()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS virtaus_registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_planilha TEXT,
            arquivo TEXT,
            tipo_origem TEXT,
            origem TEXT NOT NULL,
            data_ref TEXT NOT NULL,
            data_iso TEXT,
            status TEXT NOT NULL,
            motivo TEXT DEFAULT '',
            lidas INTEGER DEFAULT 0,
            processadas INTEGER DEFAULT 0,
            pendentes INTEGER DEFAULT 0,
            forma_processamento TEXT DEFAULT '',
            data_importacao TEXT NOT NULL,
            usuario_nome TEXT DEFAULT 'Sistema'
        );
        CREATE TABLE IF NOT EXISTS virtaus_origens_config (
            origem TEXT PRIMARY KEY,
            is_robo INTEGER DEFAULT 0,
            padrao_arquivo TEXT DEFAULT ''
        );
    """)
    for col, tbl in [("forma_processamento", "virtaus_registros"), ("padrao_arquivo", "virtaus_origens_config")]:
        try:
            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} TEXT DEFAULT ''")
            conn.commit()
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

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
    try: conn.execute("ALTER TABLE usuarios ADD COLUMN email TEXT DEFAULT ''"); conn.commit()
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
    inicializar_banco_virtaus()

def enviar_codigo_email(destinatario, assunto, codigo, nome_destino="Utilizador"):
    """
    Envia código de 6 dígitos por e-mail via SMTP.
    Lê credenciais da tabela configuracoes (smtp_email, smtp_senha, smtp_servidor, smtp_porta)
    ou variáveis de ambiente. Retorna (enviado_smtp: bool, msg_detalhe: str)
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    conn = conectar_banco()
    cfg = {r['chave']: r['valor'] for r in conn.execute("SELECT chave, valor FROM configuracoes WHERE chave LIKE 'smtp_%'").fetchall()}
    conn.close()

    smtp_user = cfg.get('smtp_email') or os.environ.get('SMTP_EMAIL', '')
    smtp_pass = cfg.get('smtp_senha') or os.environ.get('SMTP_SENHA', '')
    smtp_host = cfg.get('smtp_servidor') or os.environ.get('SMTP_SERVIDOR', 'smtp.gmail.com')
    try:
        smtp_port = int(cfg.get('smtp_porta') or os.environ.get('SMTP_PORTA', 587))
    except:
        smtp_port = 587

    if not smtp_user or not smtp_pass:
        return False, "Servidor de e-mail (SMTP) ainda não configurado no painel de Administração."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = f"Painel de Integrações <{smtp_user}>"
        msg["To"] = destinatario

        corpo_html = f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif; background:#0f1115; color:#e2e8f0; padding:30px; border-radius:12px; max-width:480px; margin:auto; border:1px solid #232834;">
            <h2 style="color:#3b82f6; margin-top:0;">Painel de Integrações</h2>
            <p>Olá, <b>{nome_destino}</b>!</p>
            <p>Utilize o código de verificação abaixo para concluir a sua solicitação:</p>
            <div style="background:#161b26; border:1px solid #2e3646; border-radius:8px; padding:16px; text-align:center; font-size:28px; font-weight:800; letter-spacing:6px; color:#60a5fa; margin:20px 0;">
                {codigo}
            </div>
            <p style="font-size:12px; color:#64748b;">Se não solicitou este código, ignore este e-mail.</p>
        </div>
        """
        msg.attach(MIMEText(corpo_html, "html", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [destinatario], msg.as_string())
        return True, "Código enviado para o seu e-mail!"
    except Exception as e:
        return False, f"Falha ao enviar e-mail ({e})."

def importar_planilha_virtaus(arquivos):
    """
    Importa um ou mais arquivos XLSX/CSV do Virtaus para o banco de dados independente (virtaus.db).
    Pega: Origem | Data | Status (+ ID, Arquivo, Tipo Origem, Lidas, Processadas, Pendentes).
    Retorna (qtd_inseridos, qtd_arquivos, msg_erro)
    """
    import pandas as pd
    inicializar_banco_virtaus()
    if not isinstance(arquivos, list):
        arquivos = [arquivos]
    
    conn = conectar_banco_virtaus()
    total_inseridos = 0
    arqs_lidos = 0
    agora_str = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")
    usr_nome = st.session_state.get('usuario_nome', 'Sistema')

    def norm_col(c):
        import unicodedata
        s = ''.join(ch for ch in unicodedata.normalize('NFD', str(c).strip().lower()) if unicodedata.category(ch) != 'Mn')
        return s

    def norm_txt(v):
        import unicodedata
        return ''.join(ch for ch in unicodedata.normalize('NFD', str(v or '').strip().upper()) if unicodedata.category(ch) != 'Mn')

    for arq in arquivos:
        try:
            nome_arq = getattr(arq, 'name', 'Arquivo.xlsx')
            if nome_arq.lower().endswith('.csv'):
                try:
                    df = pd.read_csv(arq, sep=None, engine='python', dtype=str)
                except:
                    arq.seek(0)
                    df = pd.read_csv(arq, sep=';', encoding='latin1', dtype=str)
                lista_dfs = [df]
            else:
                # Lê todas as abas da planilha Excel caso tenha mais de uma aba
                abas_excel = pd.read_excel(arq, sheet_name=None, dtype=str)
                lista_dfs = list(abas_excel.values()) if isinstance(abas_excel, dict) else [abas_excel]
            
            for df in lista_dfs:
                if df is None or df.empty:
                    continue

                # Mapear colunas com prioridade para correspondência exata
                mapa_cols = {norm_col(c): c for c in df.columns}
                
                def achar_col(possiveis):
                    for p in possiveis:
                        if p in mapa_cols:
                            return mapa_cols[p]
                    for k, orig in mapa_cols.items():
                        for p in possiveis:
                            if k == p or k.startswith(p + ' ') or k.endswith(' ' + p):
                                return orig
                    for k, orig in mapa_cols.items():
                        for p in possiveis:
                            if p in k:
                                return orig
                    return None

                col_origem = achar_col(['origem', 'banco'])
                col_data = achar_col(['data', 'data_ref', 'dt'])
                col_status = achar_col(['status', 'situacao', 'estado'])
                col_id = achar_col(['id', 'codigo'])
                col_arquivo = achar_col(['arquivo', 'ficheiro', 'file'])
                col_tipo_origem = achar_col(['tipo origem', 'tipo_origem', 'tipoorigem'])
                col_lidas = achar_col(['lidas', 'lida'])
                col_proc = achar_col(['processadas', 'processada'])
                col_pend = achar_col(['pendentes', 'pendente'])
                col_motivo = achar_col(['motivo', 'observacao', 'detalhe', 'erro', 'mensagem'])
                col_forma_proc = achar_col(['forma de processamento', 'forma_de_processamento', 'formadeprocessamento', 'forma processamento'])
                col_processamento = mapa_cols.get('processamento')

                if not col_origem and not col_status and not col_arquivo:
                    continue

                registros_inserir = []

                for _, row in df.iterrows():
                    # Ignora apenas linhas 100% em branco na planilha
                    if all(str(v or '').strip().lower() in ['', 'nan', 'none', 'null'] for v in row.values):
                        continue

                    origem_val = str(row.get(col_origem, '') or '').strip() if col_origem else ''
                    if origem_val.lower() in ['nan', 'none', 'null']:
                        origem_val = ''
                    
                    tipo_orig_val = str(row.get(col_tipo_origem, '') or '').strip() if col_tipo_origem else ''
                    if tipo_orig_val.lower() in ['nan', 'none', 'null']:
                        tipo_orig_val = ''

                    if not origem_val:
                        origem_val = tipo_orig_val if tipo_orig_val else 'SEM ORIGEM'
                    
                    status_val = str(row.get(col_status, '') or '').strip() if col_status else ''
                    if not status_val or status_val.lower() in ['nan', 'none', 'null']:
                        status_val = 'PROCESSADO'

                    # Data
                    raw_data = str(row.get(col_data, '') or '').strip() if col_data else ''
                    data_ref = ''
                    data_iso = ''
                    dt_parsed = None
                    if raw_data and raw_data.lower() not in ['nan', 'none', 'null']:
                        parte_data = raw_data.split(' ')[0].strip()
                        for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%y']:
                            try:
                                dt_parsed = datetime.strptime(parte_data, fmt).date()
                                break
                            except:
                                pass
                        if not dt_parsed:
                            try:
                                dt_parsed = pd.to_datetime(raw_data, dayfirst=True).date()
                            except:
                                pass
                        if dt_parsed:
                            data_ref = dt_parsed.strftime('%d/%m/%Y')
                            data_iso = dt_parsed.strftime('%Y-%m-%d')
                        else:
                            data_ref = raw_data
                    else:
                        dt_parsed = (datetime.now() - timedelta(days=1)).date()
                        data_ref = dt_parsed.strftime('%d/%m/%Y')
                        data_iso = dt_parsed.strftime('%Y-%m-%d')

                    id_plan = str(row.get(col_id, '') or '').strip() if col_id else ''
                    if id_plan.lower() in ['nan', 'none', 'null']: id_plan = ''
                    if id_plan.endswith('.0'): id_plan = id_plan[:-2]
                    
                    arq_val = str(row.get(col_arquivo, '') or '').strip() if col_arquivo else nome_arq
                    if not arq_val or arq_val.lower() in ['nan', 'none', 'null']: arq_val = nome_arq

                    # Forma de processamento / Processamento (normaliza acentos para pegar ROBÔ, ROBO, ROBÔ, AUTOMÁTICO, etc.)
                    fp_raw_1 = str(row.get(col_forma_proc, '') or '').strip() if col_forma_proc else ''
                    fp_raw_2 = str(row.get(col_processamento, '') or '').strip() if col_processamento else ''
                    if fp_raw_1.lower() in ['nan', 'none', 'null']: fp_raw_1 = ''
                    if fp_raw_2.lower() in ['nan', 'none', 'null']: fp_raw_2 = ''
                    fp_norm = norm_txt(f"{fp_raw_1} {fp_raw_2}")

                    forma_proc_norm = ''
                    if any(k in fp_norm for k in ['ROBO', 'BOT', 'AUTOMATICO', 'API', 'INTEGRA']):
                        forma_proc_norm = 'ROBO'
                    elif 'MANUAL' in fp_norm:
                        forma_proc_norm = 'MANUAL'

                    def to_int(v):
                        try:
                            s = str(v or '0').strip().replace('.', '').replace(',', '.')
                            return int(float(s))
                        except:
                            return 0

                    lidas_val = to_int(row.get(col_lidas, 0)) if col_lidas else 0
                    proc_val = to_int(row.get(col_proc, 0)) if col_proc else 0
                    pend_val = to_int(row.get(col_pend, 0)) if col_pend else 0

                    motivo_val = ''
                    if col_motivo:
                        m_raw = str(row.get(col_motivo, '') or '').strip()
                        if m_raw.lower() not in ['nan', 'none', '']:
                            motivo_val = m_raw
                    if not motivo_val:
                        if ':' in status_val:
                            motivo_val = status_val.split(':', 1)[1].strip()
                        elif ' - ' in status_val:
                            motivo_val = status_val.split(' - ', 1)[1].strip()
                        else:
                            motivo_val = status_val

                    # Atualiza apenas se já existir exatamente o mesmo ID da planilha no banco
                    existe = None
                    if id_plan:
                        existe = conn.execute("SELECT id, forma_processamento FROM virtaus_registros WHERE id_planilha = ?", (id_plan,)).fetchone()

                    if existe:
                        fp_salvar = forma_proc_norm if forma_proc_norm else (existe['forma_processamento'] or '')
                        conn.execute("""
                            UPDATE virtaus_registros 
                            SET arquivo=?, tipo_origem=?, origem=?, data_ref=?, data_iso=?, status=?, motivo=?, lidas=?, processadas=?, pendentes=?, forma_processamento=?, data_importacao=?, usuario_nome=?
                            WHERE id=?
                        """, (arq_val, tipo_orig_val, origem_val, data_ref, data_iso, status_val, motivo_val, lidas_val, proc_val, pend_val, fp_salvar, agora_str, usr_nome, existe['id']))
                        total_inseridos += 1
                        continue

                    registros_inserir.append((
                        id_plan, arq_val, tipo_orig_val, origem_val, data_ref, data_iso,
                        status_val, motivo_val, lidas_val, proc_val, pend_val, forma_proc_norm, agora_str, usr_nome
                    ))

                if registros_inserir:
                    conn.executemany("""
                        INSERT INTO virtaus_registros 
                        (id_planilha, arquivo, tipo_origem, origem, data_ref, data_iso, status, motivo, lidas, processadas, pendentes, forma_processamento, data_importacao, usuario_nome)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, registros_inserir)
                    total_inseridos += len(registros_inserir)

            arqs_lidos += 1
        except Exception as e:
            conn.close()
            return total_inseridos, arqs_lidos, str(e)

    conn.commit()
    conn.close()
    return total_inseridos, arqs_lidos, None

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
            if hora_loop.weekday() < 5 and 5 <= hora_loop.hour <= 22 and not conn.execute("SELECT id FROM historico WHERE banco_id = ? AND data_hora LIKE ?", (b_id, hora_loop.strftime("%d/%m/%Y às %H:") + "%")).fetchone():
                registros.append((b_id, b_nome, 'Status Alterado', 'INTEGRADO (Robô Automático)', hora_loop.strftime("%d/%m/%Y às %H:00:00"), 0, 'Sistema'))
                if hora_loop.date() == agora.date(): teve_atualizacao_hoje = True
            hora_loop += timedelta(hours=1)
            
        if registros:
            conn.executemany("INSERT INTO historico (banco_id, banco_nome, acao, detalhes, data_hora, usuario_id, usuario_nome) VALUES (?,?,?,?,?,?,?)", registros)
            if teve_atualizacao_hoje: conn.execute("UPDATE bancos SET status='INTEGRADO', motivo_erro='', motivo_pendencia='', ultima_atualizacao=? WHERE id=?", (agora.strftime("%d/%m/%Y às %H:%M"), b_id))
    conn.commit(); conn.close()
