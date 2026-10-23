from datetime import datetime
import warnings
import numpy as np
import pandas as pd


def processar(df):
  # Oculta avisos do Pandas no terminal
  warnings.filterwarnings('ignore', category=UserWarning, module='pandas')

  # --- INÍCIO DA CORREÇÃO ---
  # Se o df for um dicionário (ex: várias abas do Excel), pega a primeira aba
  if isinstance(df, dict):
      df = list(df.values())[0]
  # --- FIM DA CORREÇÃO ---

  # Remove linhas completamente vazias caso existam na origem
  df = df.dropna(how='all').copy()

  # Mapeia os nomes das colunas da origem em maiúsculas
  cols_upper = {str(c).strip().upper(): c for c in df.columns}

  # 1. DELETA PROMOTORA 6507 (Remove '.0' caso o Excel leia como float)
  col_promotora = cols_upper.get('COD_PROMOTORA')
  if col_promotora:
    s_prom = (
        df[col_promotora]
        .fillna('')
        .astype(str)
        .str.replace(r'\.0$', '', regex=True)
        .str.strip()
    )
    df = df[~s_prom.eq('6507')].copy()

  # 2. LISTA PADRONIZADA DE CABEÇALHOS (Com QUITACAO_PARCELAS no final, igual ao VBA)
  lista_cabecalhos = (
      'NUM_BANCO|NOM_BANCO|NUM_PROPOSTA|NUM_CONTRATO|DSC_TIPO_PROPOSTA_EMPRESTIMO|COD_PRODUTO|DSC_PRODUTO|'
      'DAT_CTR_INCLUSAO|DSC_SITUACAO_EMPRESTIMO|DAT_EMPRESTIMO|COD_EMPREGADOR|DSC_CONVENIO|COD_ORGAO|NOM_ORGAO|'
      'COD_PRODUTOR_VENDA|NOM_PRODUTOR_VENDA|NIC_CTR_USUARIO|COD_CPF_CLIENTE|NOM_CLIENTE|DAT_NASCIMENTO|NUM_IDENTIDADE|'
      'NOM_LOGRADOURO|NUM_PREDIO|DSC_CMPLMNT_ENDRC|NOM_BAIRRO|NOM_LOCALIDADE|SIG_UNIDADE_FEDERACAO|COD_ENDRCMNT_PSTL|'
      'NUM_TELEFONE|NUM_TELEFONE_CELULAR|NOM_MAE|NOM_PAI|NUM_BENEFICIO|QTD_PARCELA|VAL_PRESTACAO|VAL_BRUTO|'
      'VAL_SALDO_RECOMPRA|VAL_SALDO_REFINANCIAMENTO|VAL_LIQUIDO|PCR_PMT_PAGO_REF|DAT_CREDITO|DAT_CONFIRMACAO|VAL_REPASSE|'
      'PCL_COMISSAO_AGENTE|VAL_COMISSAO|VAL_SEGURO|COD_UNIDADE_EMPRESA|COD_SITUACAO_EMPRESTIMO|DAT_ESTORNO|DSC_OBSERVACAO|'
      'NUM_CPF_AGENTE|NUM_OBJETO_ECT|PCL_TAXA_EMPRESTIMO|DSC_TIPO_FORMULARIO_EMPRESTIMO|DSC_TIPO_CREDITO_EMPRESTIMO|'
      'NOM_GRUPO_UNIDADE_EMPRESA|COD_PROPOSTA_EMPRESTIMO|COD_GRUPO_UNIDADE_EMPRESA|COD_TIPO_FUNCAO|'
      'COD_TIPO_PROPOSTA_EMPRESTIMO|COD_LOJA_DIGITACAO|QUITACAO_PARCELAS'
  ).split('|')

  # Cria o DataFrame de saída com o mesmo número de linhas do df filtrado
  df_out = pd.DataFrame(
      '', index=range(len(df)), columns=lista_cabecalhos, dtype=object
  )

  # 3. MAPEAMENTO DINÂMICO
  for col in lista_cabecalhos:
    col_upper = col.strip().upper()
    if col_upper in cols_upper:
      df_out[col] = df[cols_upper[col_upper]].values

  # Copia específica do VBA: QUITACAO_PARCELAS_1 (LookAt:=xlPart) -> QUITACAO_PARCELAS
  col_origem_quitacao = next(
      (
          orig_col
          for upper_name, orig_col in cols_upper.items()
          if 'QUITACAO_PARCELAS_1' in upper_name
      ),
      None,
  )
  if col_origem_quitacao:
    df_out['QUITACAO_PARCELAS'] = df[col_origem_quitacao].values

  # Blindagem contra resíduos nulos mantendo dtype=object
  bad_vals = ['nan', 'NaN', 'None', '<NA>', 'NaT']
  for col in df_out.columns:
    s = df_out[col].fillna('').astype(str)
    s = s.mask(s.isin(bad_vals), '')
    df_out[col] = s.astype(object)

  # 4. REGRAS ESPECÍFICAS DE COPIAR E MOVER
  # H (ICRED / DAT_CTR_INCLUSAO) -> J (WORKBANK / DAT_EMPRESTIMO)
  col_dat_ctr = cols_upper.get('DAT_CTR_INCLUSAO')
  if col_dat_ctr:
    s_dat = df[col_dat_ctr].fillna('').astype(str)
    df_out['DAT_EMPRESTIMO'] = s_dat.mask(s_dat.isin(bad_vals), '').values

  # BL (ICRED / COD_PROMOTORA) -> K (WORKBANK / COD_EMPREGADOR)
  if col_promotora:
    s_emp = df[col_promotora].fillna('').astype(str)
    df_out['COD_EMPREGADOR'] = s_emp.mask(s_emp.isin(bad_vals), '').values

  # Move AP (DAT_CONFIRMACAO) -> AO (DAT_CREDITO)
  df_out['DAT_CREDITO'] = df_out['DAT_CONFIRMACAO']

  # 5. LÓGICA DE APAGAR LINHAS (vE, vK, vL)
  vE = df_out['DSC_TIPO_PROPOSTA_EMPRESTIMO'].astype(str).str.strip()
  vK = (
      df_out['COD_EMPREGADOR']
      .astype(str)
      .str.replace(r'\.0$', '', regex=True)
      .str.strip()
  )
  df_out['COD_EMPREGADOR'] = vK.astype(object)
  vL = df_out['DSC_CONVENIO'].astype(str).str.strip()

  mask_del = (
      vE.str.contains('DIGITAL', case=False, na=False)
      | (vK == '')
      | vL.str.contains('SEGURO', case=False, na=False)
  )
  df_out = df_out[~mask_del].copy()

  # 6. TRADUÇÃO E CONCATENAÇÃO DE PRODUTOS
  vE_traduzido = (
      df_out['DSC_TIPO_PROPOSTA_EMPRESTIMO']
      .astype(str)
      .str.strip()
      .str.replace('portability-refin', 'Refin da Portabilidade', case=False)
      .str.replace('portability', 'Portabilidade', case=False)
      .str.replace('refinancing', 'Refinanciamento', case=False)
      .str.replace('new', 'Novo', case=False)
  )
  df_out['DSC_TIPO_PROPOSTA_EMPRESTIMO'] = vE_traduzido.astype(object)

  dsc_prod = (
      df_out['DSC_TIPO_PROPOSTA_EMPRESTIMO'].astype(str)
      + '-'
      + df_out['DSC_PRODUTO'].astype(str).str.strip()
  )
  df_out['DSC_PRODUTO'] = dsc_prod.str.replace(r'-$', '', regex=True).astype(
      object
  )

  df_out['DAT_CTR_INCLUSAO'] = datetime.now().strftime('%d/%m/%Y 00:00')
  df_out['DSC_TIPO_FORMULARIO_EMPRESTIMO'] = 'Digital'

  # Coluna AO (DAT_CREDITO): só mantém valor se DSC_SITUACAO_EMPRESTIMO = Operação Finalizada
  mask_sit = (
      ~df_out['DSC_SITUACAO_EMPRESTIMO']
      .astype(str)
      .str.contains(r'Opera[çc][ãa]o Finalizada', case=False, na=False)
  )
  df_out.loc[mask_sit, 'DAT_CREDITO'] = ''

  # 7. CÁLCULO DE SALDOS COM CONVERSÃO ROBUSTA
  def converte_numero(serie):
    def _parse(val):
      if pd.isna(val):
        return 0.0
      v_str = str(val).replace('R$', '').replace(' ', '').strip()
      if v_str in bad_vals or v_str == '':
        return 0.0
      if ',' in v_str and '.' in v_str:
        if v_str.rfind(',') > v_str.rfind('.'):
          v_str = v_str.replace('.', '').replace(',', '.')
        else:
          v_str = v_str.replace(',', '')
      elif ',' in v_str:
        v_str = v_str.replace(',', '.')
      try:
        return float(v_str)
      except Exception:
        return 0.0

    return serie.apply(_parse)

  val_AJ = converte_numero(df_out['VAL_BRUTO'])
  val_AM = converte_numero(df_out['VAL_LIQUIDO'])

  s_tipo = df_out['DSC_TIPO_PROPOSTA_EMPRESTIMO'].astype(str)
  mask_refin = s_tipo.str.contains(
      'Refinanciamento|Refin da Portabilidade', case=False, na=False
  )
  mask_novo = (~mask_refin) & s_tipo.str.contains('Novo', case=False, na=False)

  # Espelhamento matemático exato: VAL_SALDO_REFINANCIAMENTO = VAL_BRUTO - VAL_LIQUIDO
  df_out.loc[mask_refin, 'VAL_SALDO_REFINANCIAMENTO'] = (
      (val_AJ[mask_refin] - val_AM[mask_refin]).round(2).astype(object)
  )
  df_out.loc[mask_novo, 'VAL_BRUTO'] = val_AM[mask_novo].round(2).astype(object)

  # 8. FORMATAÇÕES ESPECÍFICAS (Datas e Moedas precisas)
  def format_date_custom(serie, include_time=False):
    temp = serie.astype(str).str.strip()
    temp = temp.mask(temp.isin(bad_vals + ['']), np.nan)

    partes = temp.dropna().str.extract(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})')
    usar_dayfirst = True
    if not partes.empty:
      p1 = pd.to_numeric(partes[0], errors='coerce')
      p2 = pd.to_numeric(partes[1], errors='coerce')
      if (p2 > 12).any() and not (p1 > 12).any():
        usar_dayfirst = False

    def _parse_dt(val):
      if pd.isna(val):
        return pd.NaT
      s_val = str(val).strip()
      if len(s_val) >= 10 and s_val[4:5] == '-' and s_val[7:8] == '-':
        return pd.to_datetime(s_val, errors='coerce', dayfirst=False)
      return pd.to_datetime(s_val, errors='coerce', dayfirst=usar_dayfirst)

    dt = temp.apply(_parse_dt)
    if include_time:
      return dt.dt.strftime('%d/%m/%Y %H:%M').fillna('').astype(object)
    return dt.dt.strftime('%d/%m/%Y').fillna('').astype(object)

  if 'DAT_EMPRESTIMO' in df_out.columns:
    df_out['DAT_EMPRESTIMO'] = format_date_custom(
        df_out['DAT_EMPRESTIMO'], include_time=True
    )
  if 'DAT_NASCIMENTO' in df_out.columns:
    df_out['DAT_NASCIMENTO'] = format_date_custom(df_out['DAT_NASCIMENTO'])
  if 'DAT_CREDITO' in df_out.columns:
    df_out['DAT_CREDITO'] = format_date_custom(df_out['DAT_CREDITO'])
  if 'DAT_CONFIRMACAO' in df_out.columns:
    df_out['DAT_CONFIRMACAO'] = format_date_custom(df_out['DAT_CONFIRMACAO'])
  if 'DAT_ESTORNO' in df_out.columns:
    df_out['DAT_ESTORNO'] = format_date_custom(df_out['DAT_ESTORNO'])

  colunas_numericas = [
      'QTD_PARCELA',
      'VAL_PRESTACAO',
      'VAL_BRUTO',
      'VAL_SALDO_RECOMPRA',
      'VAL_SALDO_REFINANCIAMENTO',
      'VAL_LIQUIDO',
      'VAL_REPASSE',
      'VAL_COMISSAO',
      'VAL_SEGURO',
      'PCL_COMISSAO_AGENTE',
      'PCR_PMT_PAGO_REF',
      'PCL_TAXA_EMPRESTIMO',
  ]

  def formatar_numero_preciso(val):
    if pd.isna(val) or str(val).strip() in bad_vals + ['']:
      return ''
    v_str = str(val).replace('R$', '').replace(' ', '').strip()
    try:
      if ',' in v_str and '.' in v_str:
        if v_str.rfind(',') > v_str.rfind('.'):
          v_str = v_str.replace('.', '').replace(',', '.')
        else:
          v_str = v_str.replace(',', '')
      elif ',' in v_str:
        v_str = v_str.replace(',', '.')

      f_val = round(float(v_str), 2)
      if f_val.is_integer():
        return str(int(f_val))
      else:
        return f'{f_val:.2f}'.rstrip('0').rstrip('.').replace('.', ',')
    except Exception:
      return str(val)

  for col in colunas_numericas:
    if col in df_out.columns:
      df_out[col] = df_out[col].apply(formatar_numero_preciso).astype(object)

  # 9. LIMPEZA FINAL
  colunas_para_limpar = [
      'COD_PRODUTO',
      'DAT_CONFIRMACAO',
      'VAL_SEGURO',
      'DSC_OBSERVACAO',
      'NUM_CPF_AGENTE',
      'PCL_TAXA_EMPRESTIMO',
      'COD_TIPO_PROPOSTA_EMPRESTIMO',
      'COD_LOJA_DIGITACAO',
  ]

  colunas_datas = [
      'DAT_EMPRESTIMO',
      'DAT_NASCIMENTO',
      'DAT_CREDITO',
      'DAT_CONFIRMACAO',
      'DAT_ESTORNO',
  ]

  for col in df_out.columns:
    if col in colunas_para_limpar:
      df_out[col] = ''
    else:
      s_col = df_out[col].fillna('').astype(str)
      s_col = s_col.mask(s_col.isin(bad_vals), '')

      if col not in colunas_numericas and col not in colunas_datas:
        s_col = s_col.str.replace(r'\.0$', '', regex=True)

      df_out[col] = s_col.astype(object)

  data_nome = datetime.now().strftime('%Y%m%d')
  return {f'Icred_Indicados_{data_nome}': df_out}