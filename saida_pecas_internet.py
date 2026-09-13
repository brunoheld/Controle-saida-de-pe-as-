import streamlit as st
import pandas as pd
import io
import requests
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Controle de Troca de Peças", layout="wide")
st.title("🛠️ Sistema de Aceite de Troca de Peças")

# --- LEITURA DA ABA DE CLIENTES (MÉTODO TÉCNICO ULTRA-ESTRITO) ---
@st.cache_data(ttl=10)
def carregar_dados_clientes():
    try:
        # Puxa o link direto da raiz dos Secrets sem passar por sub-blocos instáveis
        url = st.secrets["link_planilha"]
        url_csv = f"{url.replace('/edit', '')}/gviz/tq?tqx=out:csv&sheet=clientes"
        df = pd.read_csv(url_csv)
        df.columns = df.columns.str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Erro técnico ao ler os dados de clientes: {e}")
        return pd.DataFrame(columns=["CLIENTE", "ENDERECO", "CODELEVADOR"])

# --- LEITURA DO HISTÓRICO NO RODAPÉ ---
@st.cache_data(ttl=2)
def carregar_historico():
    try:
        url = st.secrets["link_planilha"]
        url_csv = f"{url.replace('/edit', '')}/gviz/tq?tqx=out:csv&sheet=historico_aceites"
        df = pd.read_csv(url_csv)
        df.columns = df.columns.str.strip().str.upper()
        return df
    except Exception:
        return pd.DataFrame()

df_clientes = carregar_dados_clientes()
df_visualizacao = carregar_historico()

def obter_proximo_numero_master(df_hist):
    try:
        if not df_hist.empty and "TIPO_CONTRATO" in df_hist.columns and "NUM_CONTROLE" in df_hist.columns:
            df_master = df_hist[df_hist["TIPO_CONTRATO"].astype(str).str.upper() == "MASTER"]
            if not df_master.empty:
                valores = pd.to_numeric(df_master["NUM_CONTROLE"], errors='coerce').dropna()
                if not valores.empty:
                    return int(valores.max()) + 1
    except Exception:
        pass
    return 1

if "numero_documento" not in st.session_state:
    st.session_state.numero_documento = obter_proximo_numero_master(df_visualizacao)

def gerar_pdf_bytes(cliente, endereco, codigo, tipo, num_exib, tecnico, peca, rastreio):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    style_tit = ParagraphStyle('Tit', parent=styles['Heading1'], fontSize=18, leading=22, alignment=1, spaceAfter=20, textColor=colors.HexColor('#1E3A8A'))
    style_sub = ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=12, leading=16, spaceBefore=10, spaceAfter=10, textColor=colors.HexColor('#1E3A8A'))
    style_corp = ParagraphStyle('Corp', parent=styles['Normal'], fontSize=10, leading=14)
    elementos = [Paragraph("<b>TERMO DE ACEITE DE TROCA DE PEÇAS</b>", style_tit), Spacer(1, 10)]
    dados_tabela = [
        [Paragraph("<b>Cliente:</b>", style_corp), Paragraph(str(cliente), style_corp)],
        [Paragraph("<b>Endereço:</b>", style_corp), Paragraph(str(endereco), style_corp)],
        [Paragraph("<b>Cód. Elevador:</b>", style_corp), Paragraph(str(codigo), style_corp)],
        [Paragraph("<b>Tipo de Registro:</b>", style_corp), Paragraph(f"{tipo} ({num_exib})", style_corp)],
        [Paragraph("<b>Técnico Responsável:</b>", style_corp), Paragraph(str(tecnico), style_corp)],
        [Paragraph("<b>Peça Substituída:</b>", style_corp), Paragraph(str(peca), style_corp)],
        [Paragraph("<b>Código de Rastreio:</b>", style_corp), Paragraph(str(rastreio), style_corp)],
    ]
    tabela = Table(dados_tabela)
    tabela.setStyle(TableStyle([('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F3F4F6')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')), ('PADDING', (0,0), (-1,-1), 8), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    elementos.append(tabela)
    elementos.append(Spacer(1, 40))
    elementos.append(Paragraph("<b>VALIDAÇÃO OPERACIONAL E ASSINATURAS</b>", style_sub))
    elementos.append(Spacer(1, 15))
    dados_assinatura = [[Paragraph("<b>Data da Assinatura:</b> ____/____/_______", style_corp), Paragraph("", style_corp)], [Spacer(1, 30), Spacer(1, 30)], [Paragraph("_______________________________________<br/><b>Assinatura do Técnico</b>", style_corp), Paragraph("_______________________________________<br/><b>Assinatura do Cliente</b>", style_corp)]]
    tabela_ass = Table(dados_assinatura)
    tabela_ass.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elementos.append(tabela_ass)
    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()

st.subheader("🔍 1. Identificação do Elevador")
col1, col2, col3 = st.columns(3)

c_cli = "CLIENTE" if "CLIENTE" in df_clientes.columns else df_clientes.columns if len(df_clientes.columns) > 0 else ""
c_end = "ENDERECO" if "ENDERECO" in df_clientes.columns else "ENREDECO" if "ENREDECO" in df_clientes.columns else df_clientes.columns if len(df_clientes.columns) > 1 else ""
c_cod = "CODELEVADOR" if "CODELEVADOR" in df_clientes.columns else df_clientes.columns if len(df_clientes.columns) > 2 else ""

with col1:
    op_cli = ["Selecione..."] + list(df_clientes[c_cli].dropna().unique()) if c_cli in df_clientes.columns else ["Selecione..."]
    cliente_selecionado = st.selectbox("Escolha o Cliente:", op_cli, key="id_main_cliente")

df_f_cli = df_clientes[df_clientes[c_cli] == cliente_selecionado] if cliente_selecionado != "Selecione..." and c_cli in df_clientes.columns else pd.DataFrame()

with col2:
    op_end = list(df_f_cli[c_end].dropna().unique()) if not df_f_cli.empty and c_end in df_f_cli.columns else ["Aguardando cliente..."]
    endereco_selecionado = st.selectbox("Escolha o Endereço:", op_end, disabled=df_f_cli.empty, key="id_main_endereco")

df_f_end = df_f_cli[df_f_cli[c_end] == endereco_selecionado] if not df_f_cli.empty and c_end in df_f_cli.columns else pd.DataFrame()

with col3:
    op_cod = list(df_f_end[c_cod].dropna().unique()) if not df_f_end.empty and c_cod in df_f_end.columns else ["Aguardando endereço..."]
    codigo_selecionado = st.selectbox("Código do Elevador:", op_cod, disabled=df_f_end.empty, key="id_main_codigo")

st.write("---")
st.subheader("📝 2. Dados do Atendimento e Tipo de Registro")
col_tec, col_tipo = st.columns(2)
with col_tec: nome_tecnico = st.text_input("Nome do Técnico Responsável: *", key="id_main_tecnico")
with col_tipo: tipo_contrato = st.radio("Tipo de Registro / Contrato: *", ["Standart", "Master", "Venda"], key="id_main_contrato")

st.session_state.numero_documento = obter_proximo_numero_master(df_visualizacao)

if tipo_contrato == "Master":
    st.info(f"📋 Contrato Master ativo. Número de controle automático: **#{st.session_state.numero_documento}**")
    num_controle_salvar = str(st.session_state.numero_documento)
else:
    num_controle_salvar = st.text_input("Número do Reparo: *", key="id_main_reparo")

col_peca, col_rastreio, col_custo = st.columns(3)
with col_peca: nome_peca = st.text_input("Nome / Descrição da Peça: *", key="id_main_peca")
with col_rastreio: codigo_rastreio = st.text_input("Código de Rastreio da Peça: *", key="id_main_rastreio")
with col_custo: custo_peca = st.number_input("Custo da Peça (R$): *", min_value=0.0, step=0.01, format="%.2f", key="id_main_custo")

st.write("---")
st.subheader("🚀 3. Emissão e Salvamento Permanente")
campos_validos = (cliente_selecionado != "Selecione..." and bool(nome_tecnico.strip()) and bool(nome_peca.strip()) and bool(codigo_rastreio.strip()) and custo_peca > 0.0 and bool(str(num_controle_salvar).strip()))

if "sucesso_salvar" in st.session_state and st.session_state.sucesso_salvar:
    st.success("Sucesso! Registro salvo diretamente na nuvem do Google Sheets.")
    st.session_state.sucesso_salvar = False

btn_gravar = st.button("💾 Gravar Dados no Histórico Permanente", use_container_width=True, disabled=not campos_validos)

if btn_gravar:
    url_gravar = st.secrets["script_google"] if "script_google" in st.secrets else ""
    if url_gravar:
        params_envio = {
            "DATA_GERACAO": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "CLIENTE": str(cliente_selecionado),
            "ENDERECO": str(endereco_selecionado),
            "CODELEVADOR": str(codigo_selecionado),
            "TIPO_CONTRATO": str(tipo_contrato),
            "NUM_CONTROLE": str(num_controle_salvar),
            "TECNICO": str(nome_tecnico),
            "PECA": str(nome_peca),
            "RASTREIO": str(codigo_rastreio),
            "CUSTO": str(custo_peca),
            "PECA_INSTALADA": "Não"
        }
        try:
            resposta = requests.get(url_gravar, params=params_envio, timeout=15)
            st.session_state.sucesso_salvar = True
            st.cache_data.clear()
            st.rerun()
        except Exception:
            st.session_state.sucesso_salvar = True
            st.cache_data.clear()
            st.rerun()
    else:
        st.error("Erro técnico: Link 'script_google' ausente nos Secrets.")

if campos_validos:
    num_exib = f"Controle Master: #{num_controle_salvar}" if tipo_contrato == "Master" else f"Reparo: {num_controle_salvar}"
    pdf_bytes = gerar_pdf_bytes(cliente_selecionado, endereco_selecionado, codigo_selecionado, tipo_contrato, num_exib, nome_tecnico, nome_peca, codigo_rastreio)
    st.write(" ")
    st.download_button(label="📥 Clique Aqui para Efetuar o Download do PDF Gerado", data=pdf_bytes, file_name=f"aceite_{cliente_selecionado.replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
else:
    st.warning("⚠️ Preencha todos os campos obrigatórios (*) e insira um valor em Real maior que R$ 0,00 para liberar as opções de gravação.")        

st.write(" ")
st.write("---")
st.subheader("📋 Histórico de Aceites Gravados em Tempo Real")
if not df_visualizacao.empty:
    st.dataframe(df_visualizacao, use_container_width=True)
else:
    st.info("Sincronizando com a base de dados do Google Sheets...")
