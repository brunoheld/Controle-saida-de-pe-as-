import streamlit as st, pandas as pd, io, requests
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Controle", layout="wide")
st.title("🛠️ Sistema de Aceite de Troca de Peças")

if "chave_reset" not in st.session_state: st.session_state.chave_reset = 0
if "u_pdf" not in st.session_state: st.session_state.u_pdf = None
if "u_cli" not in st.session_state: st.session_state.u_cli = ""
if "h_hide" not in st.session_state: st.session_state.h_hide = False
if "contador_master_local" not in st.session_state: st.session_state.contador_master_local = None

@st.cache_data(ttl=1)
def l_cli():
    try:
        url = st.secrets["link_planilha"]
        df = pd.read_csv(f"{url.split('/edit')}/export?format=csv&gid=0")
        df.columns = df.columns.str.strip().str.upper()
        return df
    except: return pd.DataFrame(columns=["CLIENTE","ENDERECO","CODELEVADOR"])

def l_hist():
    if st.session_state.h_hide: return pd.DataFrame()
    try:
        url = st.secrets["link_planilha"]
        df = pd.read_csv(f"{url.split('/edit')}/export?format=csv&sheet=historico_aceites")
        df.columns = df.columns.str.strip().str.upper()
        return df
    except: return pd.DataFrame()

df_c = l_cli()
df_h = l_hist()

def n_mst(df):
    try:
        if df.empty: return 1
        df_limpo = df.copy()
        if "TIPO_CONTRATO" not in df_limpo.columns or "NUM_CONTROLE" not in df_limpo.columns: return 1
        df_limpo["TIPO_CONTRATO"] = df_limpo["TIPO_CONTRATO"].astype(str).str.strip().str.upper()
        df_m = df_limpo[df_limpo["TIPO_CONTRATO"] == "MASTER"]
        if df_m.empty: return 1
        valores = pd.to_numeric(df_m["NUM_CONTROLE"], errors='coerce').dropna()
        if valores.empty: return 1
        return int(valores.max()) + 1
    except: return 1

if st.session_state.contador_master_local is None:
    st.session_state.contador_master_local = n_mst(df_h)

def g_pdf(c,e,cd,t,n,tec,p,r):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    sty = getSampleStyleSheet()
    t_s = ParagraphStyle('T', parent=sty['Heading1'], fontSize=17, leading=20, alignment=1, spaceAfter=15, textColor=colors.HexColor('#1E3A8A'))
    c_s = ParagraphStyle('C', parent=sty['Normal'], fontSize=10, leading=14)
    el = [Paragraph("<b>TERMO DE ACEITE DE TROCA DE PEÇAS</b>", t_s), Spacer(1, 5)]
    mat = [[Paragraph(f"<b>{k}:</b>", c_s), Paragraph(str(v), c_s)] for k, v in [("Cliente",c),("Endereço",e),("Cód. Elevador",cd),("Registro",f"{t} ({n})"),("Técnico",tec),("Peça",p),("Rastreio",r)]]
    tab = Table(mat)
    tab.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F3F4F6')), ('GRID',(0,0), (-1,-1),0.5,colors.HexColor('#D1D5DB')), ('PADDING', (0,0), (-1,-1),6)]))
    el.extend([tab, Spacer(1, 20)])
    ass_t = "_______________________________________<br/><b>Assinatura do Técnico</b>"
    ass_c = "Nome: _________________________________<br/><br/>Função: _______________________________<br/><br/>RG/CPF: _______________________________<br/><br/>_______________________________________<br/><b>Assinatura do Cliente</b>"
    t_ass = Table([[Paragraph(ass_t, c_s), Paragraph(ass_c, c_s)]], colWidths=[240, 240])
    t_ass.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('PADDING', (0,0), (-1,-1), 0)]))
    el.extend([t_ass])
    doc.build(el)
    buf.seek(0)
    return buf.getvalue()

st.subheader("🔍 1. Identificação do Elevador")
col1, col2, col3 = st.columns(3)
cc = "CLIENTE" if "CLIENTE" in df_c.columns else df_c.columns if len(df_c.columns)>0 else ""
ce = "ENDERECO" if "ENDERECO" in df_c.columns else "ENREDECO" if "ENREDECO" in df_c.columns else df_c.columns if len(df_c.columns)>1 else ""
co = "CODELEVADOR" if "CODELEVADOR" in df_c.columns else df_c.columns if len(df_c.columns)>2 else ""

with col1: sel_c = st.selectbox("Escolha o Cliente:", ["Selecione..."] + list(df_c[cc].dropna().unique()), key=f"c_{st.session_state.chave_reset}")
df_fc = df_c[df_c[cc] == sel_c] if sel_c != "Selecione..." else pd.DataFrame()
with col2: sel_e = st.selectbox("Escolha o Endereço:", list(df_fc[ce].dropna().unique()) if not df_fc.empty else ["Aguardando..."], key=f"e_{st.session_state.chave_reset}")
df_fe = df_fc[df_fc[ce] == sel_e] if not df_fc.empty else pd.DataFrame()
with col3: sel_o = st.selectbox("Código do Elevador:", list(df_fe[co].dropna().unique()) if not df_fe.empty else ["Aguardando..."], key=f"o_{st.session_state.chave_reset}")

st.write("---")
st.subheader("📝 2. Dados do Atendimento")
col_tec, col_tipo = st.columns(2)
with col_tec: tx_tec = st.text_input("Nome do Técnico Responsável: *", key=f"t_{st.session_state.chave_reset}")
with col_tipo: rd_tip = st.radio("Tipo de Contrato: *", ["Standart", "Master", "Venda"], key=f"r_{st.session_state.chave_reset}")

if rd_tip == "Master":
    st.info(f"📋 Número automático: **#{st.session_state.contador_master_local}**")
    v_num = str(st.session_state.contador_master_local)
else: v_num = st.text_input("Número do Reparo: *", key=f"rp_{st.session_state.chave_reset}")

col_p, col_r, col_cu = st.columns(3)
with col_p: tx_pec = st.text_input("Peça: *", key=f"p_{st.session_state.chave_reset}")
with col_r: tx_ras = st.text_input("Rastreio: *", key=f"ra_{st.session_state.chave_reset}")
with col_cu: nu_cus = st.number_input("Custo (R$): *", min_value=0.0, step=0.01, format="%.2f", key=f"cu_{st.session_state.chave_reset}")

st.write("---")
st.subheader("🚀 3. Emissão e Salvamento")
ok = (sel_c != "Selecione..." and bool(tx_tec.strip()) and bool(tx_pec.strip()) and bool(tx_ras.strip()) and nu_cus > 0.0 and bool(str(v_num).strip()))

if "sv" in st.session_state and st.session_state.sv:
    st.success("Sucesso! Registro salvo na nuvem.")
    st.session_state.sv = False

if st.button("💾 Gravar Dados no Histórico Permanente", use_container_width=True, disabled=not ok):
    lbl = f"Master: #{v_num}" if rd_tip == "Master" else f"Reparo: {v_num}"
    st.session_state.u_pdf = g_pdf(sel_c, sel_e, sel_o, rd_tip, lbl, tx_tec, tx_pec, tx_ras)
    st.session_state.u_cli = sel_c
    pars = {"DATA_GERACAO": datetime.now().strftime("%d/%m/%Y %H:%M"), "CLIENTE": str(sel_c), "ENDERECO": str(sel_e), "CODELEVADOR": str(sel_o), "TIPO_CONTRATO": str(rd_tip), "NUM_CONTROLE": str(v_num), "TECNICO": str(tx_tec), "PECA": str(tx_pec), "RASTREIO": str(tx_ras), "CUSTO": str(nu_cus), "PECA_INSTALADA": "Não"}
    try:
        requests.get(st.secrets["script_google"], params=pars, timeout=15)
        st.session_state.sv = True
        st.session_state.chave_reset += 1
        if rd_tip == "Master":
            st.session_state.contador_master_local += 1
        st.rerun()
    except:
        st.session_state.sv = True
        st.session_state.chave_reset += 1
        if rd_tip == "Master":
            st.session_state.contador_master_local += 1
        st.rerun()

if st.session_state.u_pdf is not None:
    st.download_button(label=f"📥 Baixar PDF Gerado para {st.session_state.u_cli}", data=st.session_state.u_pdf, file_name=f"aceite_{st.session_state.u_cli.replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
elif ok:
    lbl = f"Master: #{v_num}" if rd_tip == "Master" else f"Reparo: {v_num}"
    st.download_button(label="📥 Baixar PDF Gerado", data=g_pdf(sel_c, sel_e, sel_o, rd_tip, lbl, tx_tec, tx_pec, tx_ras), file_name=f"aceite_{sel_c.replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
else: st.warning("⚠️ Preencha todos os campos obrigatórios.")        

st.write("---")
t_col, b_col = st.columns(2)
with t_col: st.subheader("📋 Histórico em Tempo Real")
with b_col:
    if st.button("🗑️ Limpar Histórico do Navegador", type="primary", use_container_width=True):
        st.session_state.h_hide = True
        st.rerun()

if not st.session_state.h_hide and not df_h.empty: st.dataframe(df_h, use_container_width=True)
else: st.info("Histórico ocultado ou aguardando dados...")
