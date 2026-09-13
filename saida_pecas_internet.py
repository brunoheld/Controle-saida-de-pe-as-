import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Controle", layout="wide")
st.title("🛠️ Sistema de Aceite de Troca de Peças")

if "chave_reset" not in st.session_state: st.session_state.chave_reset = 0
if "contador_master_local" not in st.session_state: st.session_state.contador_master_local = None

@st.cache_data(ttl=5)
def l_cli():
    try:
        url = st.secrets["link_planilha"]
        df = pd.read_csv(f"{url.split('/edit')[0]}/export?format=csv&gid=0")
        df.columns = df.columns.str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar clientes: {e}")
        return pd.DataFrame(columns=["CLIENTE","ENDERECO","CODELEVADOR"])

def l_hist():
    try:
        url = st.secrets["link_planilha"]
        df = pd.read_csv(f"{url.split('/edit')[0]}/export?format=csv&sheet=historico_aceites")
        df.columns = df.columns.str.strip().str.upper()
        return df
    except:
        return pd.DataFrame()

df_c = l_cli()
df_h = l_hist()

def n_mst(df):
    try:
        if df.empty or "TIPO_CONTRATO" not in df.columns or "NUM_CONTROLE" not in df.columns: return 1
        df_limpo = df.copy()
        df_limpo["TIPO_CONTRATO"] = df_limpo["TIPO_CONTRATO"].astype(str).str.strip().str.upper()
        df_m = df_limpo[df_limpo["TIPO_CONTRATO"] == "MASTER"]
        if df_m.empty: return 1
        valores = pd.to_numeric(df_m["NUM_CONTROLE"], errors='coerce').dropna()
        if valores.empty: return 1
        return int(valores.max()) + 1
    except:
        return 1

if st.session_state.contador_master_local is None:
    st.session_state.contador_master_local = n_mst(df_h)

st.subheader("🔍 1. Identificação do Elevador")
col1, col2, col3 = st.columns(3)
cc = "CLIENTE" if "CLIENTE" in df_c.columns else df_c.columns[0] if len(df_c.columns)>0 else ""
ce = "ENDERECO" if "ENDERECO" in df_c.columns else "ENREDECO" if "ENREDECO" in df_c.columns else df_c.columns[1] if len(df_c.columns)>1 else ""
co = "CODELEVADOR" if "CODELEVADOR" in df_c.columns else df_c.columns[2] if len(df_c.columns)>2 else ""

with col1:
    sel_c = st.selectbox("Escolha o Cliente:", ["Selecione..."] + list(df_c[cc].dropna().unique()), key=f"c_{st.session_state.chave_reset}")
df_fc = df_c[df_c[cc] == sel_c] if sel_c != "Selecione..." else pd.DataFrame()

with col2:
    sel_e = st.selectbox("Escolha o Endereço:", list(df_fc[ce].dropna().unique()) if not df_fc.empty else ["Aguardando..."], key=f"e_{st.session_state.chave_reset}")
df_fe = df_fc[df_fc[ce] == sel_e] if not df_fc.empty else pd.DataFrame()

with col3:
    sel_o = st.selectbox("Código do Elevador:", list(df_fe[co].dropna().unique()) if not df_fe.empty else ["Aguardando..."], key=f"o_{st.session_state.chave_reset}")

st.write("---")
st.subheader("📝 2. Dados do Atendimento")
col_tec, col_tipo = st.columns(2)
with col_tec: tx_tec = st.text_input("Nome do Técnico Responsável: *", key=f"t_{st.session_state.chave_reset}")
with col_tipo: rd_tip = st.radio("Tipo de Contrato: *", ["Standart", "Master", "Venda"], key=f"r_{st.session_state.chave_reset}")

if rd_tip == "Master":
    st.info(f"📋 Número automático: **#{st.session_state.contador_master_local}**")
    v_num = str(st.session_state.contador_master_local)
else:
    v_num = st.text_input("Número do Reparo: *", key=f"rp_{st.session_state.chave_reset}")

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
    pars = {
        "DATA_GERACAO": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "CLIENTE": str(sel_c),
        "ENDERECO": str(sel_e),
        "CODELEVADOR": str(sel_o),
        "TIPO_CONTRATO": str(rd_tip),
        "NUM_CONTROLE": str(v_num),
        "TECNICO": str(tx_tec),
        "PECA": str(tx_pec),
        "RASTREIO": str(tx_ras),
        "CUSTO": str(nu_cus),
        "PECA_INSTALADA": "Não"
    }
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

st.write("---")
st.subheader("📋 Histórico em Tempo Real")
if not df_h.empty:
    st.dataframe(df_h, use_container_width=True)
else:
    st.info("Aguardando sincronização de dados...")
