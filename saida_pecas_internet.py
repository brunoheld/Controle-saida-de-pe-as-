import streamlit as st
import pandas as pd
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from streamlit_gsheets import GSheetsConnection

# Configuração da página do navegador
st.set_page_config(page_title="Controle de Troca de Peças", layout="centered")

# --- CUSTOMIZAÇÃO COMPLETA DE LAYOUT ESTILO MICROSOFT FORMS ---
st.markdown("""
    <style>
        .stApp { background-color: #F3F2F1 !important; }
        .block-container {
            background-color: #FFFFFF !important;
            padding: 3rem 4rem !important;
            margin-top: 2rem !important;
            margin-bottom: 2rem !important;
            border-radius: 4px !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
            max-width: 740px !important;
        }
        h1 {
            color: #0078D4 !important;
            font-family: 'Segoe UI', sans-serif !important;
            font-size: 24px !important;
            font-weight: 600 !important;
            border-left: 6px solid #008272 !important;
            padding-left: 15px !important;
        }
        h3 {
            color: #323130 !important;
            font-family: 'Segoe UI', sans-serif !important;
            font-size: 16px !important;
            font-weight: 600 !important;
        }
        label, .stWidgetLabel p {
            color: #323130 !important;
            font-family: 'Segoe UI', sans-serif !important;
            font-size: 14px !important;
            font-weight: 600 !important;
        }
        div[data-baseweb="input"], div[data-baseweb="select"] {
            border: 1px solid #8A8886 !important;
            border-radius: 2px !important;
        }
        button[data-testid="baseButton-secondary"], button[data-testid="baseButton-primary"] {
            background-color: #008272 !important;
            color: #FFFFFF !important;
            border-radius: 2px !important;
            font-weight: 600 !important;
        }
        button[data-testid="baseButton-secondary"]:hover, button[data-testid="baseButton-primary"]:hover {
            background-color: #006B5E !important;
        }
        header, footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

st.title("Sistema de Aceite de Troca de Peças")
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300)
def carregar_dados_clientes():
    try:
        return conn.read(worksheet="clientes")
    except Exception as e:
        st.error(f"Erro ao carregar aba 'clientes': {e}")
        return pd.DataFrame(columns=["CLIENTE", "ENDERECO", "CODELEVADOR"])

df_clientes = carregar_dados_clientes()

def obter_proximo_numero_master():
    try:
        df_hist = conn.read(worksheet="historico_aceites", ttl=0)
        if "TIPO_CONTRATO" in df_hist.columns and "NUM_CONTROLE" in df_hist.columns:
            df_master = df_hist[df_hist["TIPO_CONTRATO"] == "Master"]
            if not df_master.empty:
                valores = pd.to_numeric(df_master["NUM_CONTROLE"], errors='coerce').dropna()
                if not valores.empty:
                    return int(valores.max()) + 1
    except Exception:
        pass
    return 1

if "numero_documento" not in st.session_state:
    st.session_state.numero_documento = obter_proximo_numero_master()

def gerar_pdf_bytes(cliente, endereco, codigo, tipo, num_exib, tecnico, peca, rastreio):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    style_titulo = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=18, alignment=1, textColor=colors.HexColor('#1E3A8A'))
    style_sub = ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#1E3A8A'))
    style_corpo = ParagraphStyle('Corpo', parent=styles['Normal'], fontSize=10)
    
    elementos = [Paragraph("<b>TERMO DE ACEITE DE TROCA DE PEÇAS</b>", style_titulo), Spacer(1, 10)]
    dados_tabela = [
        [Paragraph("<b>Cliente:</b>", style_corpo), Paragraph(str(cliente), style_corpo)],
        [Paragraph("<b>Endereço:</b>", style_corpo), Paragraph(str(endereco), style_corpo)],
        [Paragraph("<b>Cód. Elevador:</b>", style_corpo), Paragraph(str(codigo), style_corpo)],
        [Paragraph("<b>Tipo de Registro:</b>", style_corpo), Paragraph(f"{tipo} ({num_exib})", style_corpo)],
        [Paragraph("<b>Técnico Responsável:</b>", style_corpo), Paragraph(str(tecnico), style_corpo)],
        [Paragraph("<b>Peça Substituída:</b>", style_corpo), Paragraph(str(peca), style_corpo)],
        [Paragraph("<b>Código de Rastreio:</b>", style_corpo), Paragraph(str(rastreio), style_corpo)],
    ]
    tabela = Table(dados_tabela)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F3F4F6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elementos.append(tabela)
    elementos.append(Spacer(1, 40))
    elementos.append(Paragraph("<b>VALIDAÇÃO OPERACIONAL E ASSINATURAS</b>", style_sub))
    
    dados_assinatura = [
        [Paragraph("<b>Data da Assinatura:</b> ____/____/_______", style_corpo), Paragraph("", style_corpo)],
        [Spacer(1, 30), Spacer(1, 30)],
        [Paragraph("_______________________________________<br/><b>Assinatura do Técnico</b>", style_corpo),
         Paragraph("_______________________________________<br/><b>Assinatura do Cliente</b>", style_corpo)]
    ]
    tabela_ass = Table(dados_assinatura)
    tabela_ass.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elementos.append(tabela_ass)
    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()

st.sidebar.title("📌 Menu de Opções")
opcao_menu = st.sidebar.radio("Selecione a tela:", ["📝 Gerar Aceite", "🔍 Consultar Histórico"])
if opcao_menu == "📝 Gerar Aceite":
    st.subheader("1. Identificação do Elevador")
    opcoes_cliente = ["Selecione..."] + list(df_clientes["CLIENTE"].dropna().unique()) if "CLIENTE" in df_clientes.columns else ["Selecione..."]
    cliente_selecionado = st.selectbox("Escolha o Cliente: *", opcoes_cliente)

    df_filtrado_cliente = df_clientes[df_clientes["CLIENTE"] == cliente_selecionado] if cliente_selecionado != "Selecione..." else pd.DataFrame()
    opcoes_endereco = list(df_filtrado_cliente["ENDERECO"].dropna().unique()) if not df_filtrado_cliente.empty else ["Aguardando cliente..."]
    endereco_selecionado = st.selectbox("Escolha o Endereço: *", opcoes_endereco, disabled=df_filtrado_cliente.empty)

    df_filtrado_endereco = df_filtrado_cliente[df_filtrado_cliente["ENDERECO"] == endereco_selecionado] if not df_filtrado_cliente.empty else pd.DataFrame()
    opcoes_codigo = list(df_filtrado_endereco["CODELEVADOR"].dropna().unique()) if not df_filtrado_endereco.empty else ["Aguardando endereço..."]
    codigo_selecionado = st.selectbox("Código do Elevador: *", opcoes_codigo, disabled=df_filtrado_endereco.empty)

    st.write(" ")
    st.subheader("2. Dados do Atendimento e Tipo de Registro")
    nome_tecnico = st.text_input("Nome do Técnico Responsável: *")
    tipo_contrato = st.radio("Tipo de Registro / Contrato: *", ["Standart", "Master", "Venda"])

    st.session_state.numero_documento = obter_proximo_numero_master()
    if tipo_contrato == "Master":
        st.info(f"📋 Contrato Master ativo. Número de controle automático: # {st.session_state.numero_documento}")
        num_controle_salvar = str(st.session_state.numero_documento)
    else:
        num_controle_salvar = st.text_input("Número do Reparo: *")

    nome_peca = st.text_input("Nome / Descrição da Peça: *")
    codigo_rastreio = st.text_input("Código de Rastreio da Peça: *")
    custo_peca = st.number_input("Custo da Peça (R$): *", min_value=0.0, step=0.01, format="%.2f")

    st.write(" ")
    st.subheader("3. Emissão e Salvamento Permanente")
    campos_validos = (
        cliente_selecionado != "Selecione..." and
        bool(nome_tecnico.strip()) and
        bool(nome_peca.strip()) and
        bool(codigo_rastreio.strip()) and
        custo_peca > 0.0 and
        bool(str(num_controle_salvar).strip())
    )

    btn_gravar = st.button("💾 Enviar e Gravar Dados no Histórico Permanente", use_container_width=True, disabled=not campos_validos)
    if btn_gravar:
        novo_registro = {
            "DATA_GERACAO": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "CLIENTE": str(cliente_selecionado),
            "ENDERECO": str(endereco_selecionado),
            "CODELEVADOR": str(codigo_selecionado),
            "TIPO_CONTRATO": str(tipo_contrato),
            "NUM_CONTROLE": str(num_controle_salvar),
            "TECNICO": str(nome_tecnico),
            "PECA": str(nome_peca),
            "RASTREIO": str(codigo_rastreio),
            "CUSTO": float(custo_peca),
            "PECA_INSTALADA": "Não"
        }
        try:
            df_hist = conn.read(worksheet="historico_aceites", ttl=0)
            df_final = pd.concat([df_hist, pd.DataFrame([novo_registro])], ignore_index=True)
            conn.update(worksheet="historico_aceites", data=df_final)
            st.success(f"Sucesso! Registro salvo diretamente no Google Sheets.")
            if "numero_documento" in st.session_state:
                del st.session_state.numero_documento
        except Exception as e:
            st.error(f"Erro ao salvar na planilha: {e}.")

    if campos_validos:
        num_exib_pdf = f"Controle Master: #{num_controle_salvar}" if tipo_contrato == "Master" else f"Reparo: {num_controle_salvar}"
        pdf_bytes = gerar_pdf_bytes(cliente_selecionado, endereco_selecionado, codigo_selecionado, tipo_contrato, num_exib_pdf, nome_tecnico, nome_peca, codigo_rastreio)
        st.write(" ")
        st.download_button(label="📥 Efetuar o Download do PDF Gerado", data=pdf_bytes, file_name=f"aceite_{cliente_selecionado.replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
    else:
        st.warning("⚠️ Preencha todos os campos obrigatórios (*) e insira um valor maior que R$ 0,00.")

elif opcao_menu == "🔍 Consultar Histórico":
    st.subheader("Histórico de Registros")
    try:
        df_visualizar = conn.read(worksheet="historico_aceites", ttl=10)
        st.dataframe(df_visualizar, use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")

