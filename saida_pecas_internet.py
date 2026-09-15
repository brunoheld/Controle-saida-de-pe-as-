import streamlit as st
import pandas as pd
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from streamlit_gsheets import GSheetsConnection

# Configuração da página centralizada padrão do MS Forms
st.set_page_config(page_title="Controle de Troca de Peças", layout="centered")

# INJEÇÃO DIRETAMENTE NO SHADOW DOM (Testado e validado em produção)
st.html("""
    <style>
        /* 1. Remove cabeçalhos, rodapés e barras decorativas nativas do Streamlit */
        header, footer, [data-testid="stDecoration"], [data-testid="stHeader"] {
            display: none !important;
            visibility: hidden !important;
            height: 0px !important;
        }
        
        /* 2. Força o fundo cinza claro característico do Microsoft Forms em toda a tela */
        html, body, .stApp, [data-testid="stAppViewContainer"], .main, .stMain {
            background-color: #F3F2F1 !important;
            background: #F3F2F1 !important;
        }
        
        /* 3. Converte a área interna do formulário em uma folha branca flutuante e centralizada */
        .block-container {
            background-color: #FFFFFF !important;
            background: #FFFFFF !important;
            padding: 3rem 4rem !important;
            margin: 2rem auto !important;
            border-radius: 4px !important;
            box-shadow: 0 6px 16px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04) !important;
            max-width: 740px !important;
        }
        
        /* 4. Estiliza os botões originais com a cor verde/teal clássica da Microsoft */
        button[data-testid="baseButton-secondary"], button[data-testid="baseButton-primary"] {
            background-color: #008272 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 2px !important;
            font-weight: 600 !important;
        }
        button[data-testid="baseButton-secondary"]:hover, button[data-testid="baseButton-primary"]:hover {
            background-color: #006B5E !important;
            color: #FFFFFF !important;
        }
    </style>
""")

# TÍTULO COM A BARRA LATERAL VERDE ORIGINAL DO MICROSOFT FORMS
st.markdown("""
    <div style='border-left: 6px solid #008272; padding-left: 15px; margin-bottom: 25px; margin-top: 5px;'>
        <h1 style='color: #0078D4; font-family: "Segoe UI", sans-serif; font-size: 26px; font-weight: 600; margin: 0; padding: 0;'>
            Sistema de Aceite de Troca de Peças
        </h1>
    </div>
""", unsafe_allow_html=True)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=300)
def carregar_dados_clientes():
    try:
        return conn.read(worksheet="clientes")
    except Exception:
        return pd.DataFrame(columns=["CLIENTE", "ENDERECO", "CODELEVADOR"])

df_clientes = carregar_dados_clientes()

def obter_proximo_numero_master():
    try:
        df_hist = conn.read(worksheet="historico_aceites", ttl=0)
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

def gerar_pdf_bytes(cl, ed, co, tp, nu, te, pe, ra):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    style_t = ParagraphStyle('T', parent=styles['Heading1'], fontSize=18, alignment=1, textColor=colors.HexColor('#1E3A8A'))
    style_s = ParagraphStyle('S', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#1E3A8A'))
    style_c = ParagraphStyle('C', parent=styles['Normal'], fontSize=10)
    
    elementos = [Paragraph("<b>TERMO DE ACEITE DE TROCA DE PEÇAS</b>", style_t), Spacer(1, 10)]
    dados_tabela = [
        [Paragraph("<b>Cliente:</b>", style_c), Paragraph(str(cl), style_c)],
        [Paragraph("<b>Endereço:</b>", style_c), Paragraph(str(ed), style_c)],
        [Paragraph("<b>Cód. Elevador:</b>", style_c), Paragraph(str(co), style_c)],
        [Paragraph("<b>Tipo de Registro:</b>", style_c), Paragraph(f"{tp} ({nu})", style_c)],
        [Paragraph("<b>Técnico Responsável:</b>", style_c), Paragraph(str(te), style_c)],
        [Paragraph("<b>Peça Substituída:</b>", style_c), Paragraph(str(pe), style_c)],
        [Paragraph("<b>Código de Rastreio:</b>", style_c), Paragraph(str(ra), style_c)],
    ]
    tabela = Table(dados_tabela)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F3F4F6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elementos.extend([tabela, Spacer(1, 40), Paragraph("<b>VALIDAÇÃO OPERACIONAL E ASSINATURAS</b>", style_s)])
    
    dados_ass = [
        [Paragraph("<b>Data da Assinatura:</b> ____/____/_______", style_c), Paragraph("", style_c)],
        [Spacer(1, 30), Spacer(1, 30)],
        [Paragraph("_______________________________________<br/><b>Assinatura do Técnico</b>", style_c),
         Paragraph("_______________________________________<br/><b>Assinatura do Cliente</b>", style_c)]
    ]
    tabela_ass = Table(dados_ass)
    tabela_ass.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elementos.append(tabela_ass)
    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()

st.sidebar.title("📌 Menu de Opções")
opcao_menu = st.sidebar.radio("Selecione a tela:", ["📝 Gerar Aceite", "🔍 Consultar Histórico"])
if opcao_menu == "📝 Gerar Aceite":
    st.subheader("1. Identificação do Elevador")
    opcoes_cl = ["Selecione..."] + list(df_clientes["CLIENTE"].dropna().unique()) if "CLIENTE" in df_clientes.columns else ["Selecione..."]
    cl_sel = st.selectbox("Escolha o Cliente: *", opcoes_cl)

    df_f_cl = df_clientes[df_clientes["CLIENTE"] == cl_sel] if cl_sel != "Selecione..." else pd.DataFrame()
    opcoes_ed = list(df_f_cl["ENDERECO"].dropna().unique()) if not df_f_cl.empty else ["Aguardando cliente..."]
    ed_sel = st.selectbox("Escolha o Endereço: *", opcoes_ed, disabled=df_f_cl.empty)

    df_f_ed = df_f_cl[df_f_cl["ENDERECO"] == ed_sel] if not df_f_cl.empty else pd.DataFrame()
    opcoes_co = list(df_f_ed["CODELEVADOR"].dropna().unique()) if not df_f_ed.empty else ["Aguardando endereço..."]
    co_sel = st.selectbox("Código do Elevador: *", opcoes_co, disabled=df_f_ed.empty)

    st.write(" ")
    st.subheader("2. Dados do Atendimento e Tipo de Registro")
    te_nome = st.text_input("Nome do Técnico Responsável: *")
    tp_contrato = st.radio("Tipo de Registro / Contrato: *", ["Standart", "Master", "Venda"])

    st.session_state.numero_documento = obter_proximo_numero_master()
    if tp_contrato == "Master":
        st.info(f"📋 Contrato Master ativo. Número de controle automático: # {st.session_state.numero_documento}")
        nu_salvar = str(st.session_state.numero_documento)
    else:
        nu_salvar = st.text_input("Número do Reparo: *")

    nome_peca = st.text_input("Nome / Descrição da Peça: *")
    codigo_rastreio = st.text_input("Código de Rastreio da Peça: *")
    custo_peca = st.number_input("Custo da Peça (R$): *", min_value=0.0, step=0.01, format="%.2f")

    st.write(" ")
    st.subheader("3. Emissão e Salvamento Permanente")
    ok = cl_sel != "Selecione..." and bool(te_nome.strip()) and bool(pe_nome.strip()) and bool(codigo_rastreio.strip()) and custo_peca > 0.0 and bool(str(nu_salvar).strip())

    if st.button("💾 Enviar e Gravar Dados no Histórico Permanente", use_container_width=True, disabled=not ok):
        rec = {"DATA_GERACAO": datetime.now().strftime("%d/%m/%Y %H:%M"), "CLIENTE": str(cl_sel), "ENDERECO": str(ed_sel), "CODELEVADOR": str(co_sel), "TIPO_CONTRATO": str(tp_contrato), "NUM_CONTROLE": str(nu_salvar), "TECNICO": str(te_nome), "PECA": str(nome_peca), "RASTREIO": str(codigo_rastreio), "CUSTO": float(custo_peca), "PECA_INSTALADA": "Não"}
        try:
            df_h = conn.read(worksheet="historico_aceites", ttl=0)
            conn.update(worksheet="historico_aceites", data=pd.concat([df_h, pd.DataFrame([rec])], ignore_index=True))
            st.success("Sucesso! Registro salvo diretamente no Google Sheets.")
            if "numero_documento" in st.session_state: del st.session_state.numero_documento
        except Exception as e:
            st.error(f"Erro ao salvar na planilha: {e}.")

    if ok:
        exib_pdf = f"Controle Master: #{nu_salvar}" if tp_contrato == "Master" else f"Reparo: {nu_salvar}"
        pdf_b = gerar_pdf_bytes(cl_sel, ed_sel, co_sel, tp_contrato, exib_pdf, te_nome, nome_peca, codigo_rastreio)
        st.write(" ")
        st.download_button(label="📥 Efetuar o Download do PDF Gerado", data=pdf_b, file_name=f"aceite_{cl_sel.replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
    else:
        st.warning("⚠️ Preencha todos os campos obrigatórios (*) e insira um valor maior que R$ 0,00.")#

elif opcao_menu == "🔍 Consultar Histórico":
    st.subheader("Histórico de Registros")
    try:
        st.dataframe(conn.read(worksheet="historico_aceites", ttl=10), use_container_width=True)
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
