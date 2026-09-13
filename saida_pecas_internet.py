import streamlit as st
import pandas as pd
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Controle de Troca de Peças", layout="wide")
st.title("🛠️ Sistema de Aceite de Troca de Peças")
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def carregar_dados_clientes():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = pd.read_csv(f"{url.replace('/edit', '')}/gviz/tq?tqx=out:csv&sheet=clientes")
        df.columns = df.columns.str.strip().str.upper()
        return df
    except Exception as e:
        st.error(f"Erro ao ler os dados da planilha: {e}")
        return pd.DataFrame(columns=["CLIENTE", "ENDERECO", "CODELEVADOR"])

df_clientes = carregar_dados_clientes()

def obter_proximo_numero_master():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df_hist = pd.read_csv(f"{url.replace('/edit', '')}/gviz/tq?tqx=out:csv&sheet=historico_aceites")
        df_hist.columns = df_hist.columns.str.strip().str.upper()
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

st.sidebar.title("📌 Menu de Opções")
opcao_menu = st.sidebar.radio("Selecione a tela:", ["📝 Gerar Aceite", "🔍 Consultar Histórico"])

if opcao_menu == "📝 Gerar Aceite":
    st.subheader("🔍 1. Identificação do Elevador")
    col1, col2, col3 = st.columns(3)
    c_cli = "CLIENTE" if "CLIENTE" in df_clientes.columns else df_clientes.columns[0] if len(df_clientes.columns) > 0 else ""
    c_end = "ENDERECO" if "ENDERECO" in df_clientes.columns else "ENREDECO" if "ENREDECO" in df_clientes.columns else df_clientes.columns[1] if len(df_clientes.columns) > 1 else ""
    c_cod = "CODELEVADOR" if "CODELEVADOR" in df_clientes.columns else df_clientes.columns[2] if len(df_clientes.columns) > 2 else ""
    with col1:
        op_cli = ["Selecione..."] + list(df_clientes[c_cli].dropna().unique()) if c_cli in df_clientes.columns else ["Selecione..."]
        cliente_selecionado = st.selectbox("Escolha o Cliente:", op_cli)
    df_f_cli = df_clientes[df_clientes[c_cli] == cliente_selecionado] if cliente_selecionado != "Selecione..." and c_cli in df_clientes.columns else pd.DataFrame()
    with col2:
        op_end = list(df_f_cli[c_end].dropna().unique()) if not df_f_cli.empty and c_end in df_f_cli.columns else ["Aguardando cliente..."]
        endereco_selecionado = st.selectbox("Escolha o Endereço:", op_end, disabled=df_f_cli.empty)
    df_f_end = df_f_cli[df_f_cli[c_end] == endereco_selecionado] if not df_f_cli.empty and c_end in df_f_cli.columns else pd.DataFrame()
    with col3:
        op_cod = list(df_f_end[c_cod].dropna().unique()) if not df_f_end.empty and c_cod in df_f_end.columns else ["Aguardando endereço..."]
        codigo_selecionado = st.selectbox("Código do Elevador:", op_cod, disabled=df_f_end.empty)

    st.write("---")
    st.subheader("📝 2. Dados do Atendimento e Tipo de Registro")
    col_tec, col_tipo = st.columns(2)
    with col_tec: nome_tecnico = st.text_input("Nome do Técnico Responsável: *")
    with col_tipo: tipo_contrato = st.radio("Tipo de Registro / Contrato: *", ["Standart", "Master", "Venda"])
    st.session_state.numero_documento = obter_proximo_numero_master()
    if tipo_contrato == "Master":
        st.info(f"📋 Contrato Master ativo. Número de controle automático: **#{st.session_state.numero_documento}**")
        num_controle_salvar = str(st.session_state.numero_documento)
    else:
        num_controle_salvar = st.text_input("Número do Reparo: *")
    col_peca, col_rastreio, col_custo = st.columns(3)
    with col_peca: nome_peca = st.text_input("Nome / Descrição da Peça: *")
    with col_rastreio: codigo_rastreio = st.text_input("Código de Rastreio da Peça: *")
    with col_custo: custo_peca = st.number_input("Custo da Peça (R$): *", min_value=0.0, step=0.01, format="%.2f")

    st.write("---")
    st.subheader("🚀 3. Emissão e Salvamento Permanente")
    campos_validos = (cliente_selecionado != "Selecione..." and bool(nome_tecnico.strip()) and bool(nome_peca.strip()) and bool(codigo_rastreio.strip()) and custo_peca > 0.0 and bool(str(num_controle_salvar).strip()))
    btn_gravar = st.button("💾 Gravar Dados no Histórico Permanente", use_container_width=True, disabled=not campos_validos)
    if btn_gravar:
        novo = {"DATA_GERACAO": datetime.now().strftime("%d/%m/%Y %H:%M"), "CLIENTE": str(cliente_selecionado), "ENDERECO": str(endereco_selecionado), "CODELEVADOR": str(codigo_selecionado), "TIPO_CONTRATO": str(tipo_contrato), "NUM_CONTROLE": str(num_controle_salvar), "TECNICO": str(nome_tecnico), "PECA": str(nome_peca), "RASTREIO": str(codigo_rastreio), "CUSTO": float(custo_peca), "PECA_INSTALADA": "Não"}
        try:
            url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            df_hist = pd.read_csv(f"{url.replace('/edit', '')}/gviz/tq?tqx=out:csv&sheet=historico_aceites")
            df_final = pd.concat([df_hist, pd.DataFrame([novo])], ignore_index=True)
            conn.update(worksheet="historico_aceites", data=df_final)
            st.success("Sucesso! Registro salvo diretamente no Google Sheets.")
            if "numero_documento" in st.session_state: del st.session_state.numero_documento
        except Exception as e: st.error(f"Erro ao salvar na planilha: {e}.")
    if campos_validos:
        num_exib = f"Controle Master: #{num_controle_salvar}" if tipo_contrato == "Master" else f"Reparo: {num_controle_salvar}"
        pdf_bytes = gerar_pdf_bytes(cliente_selecionado, endereco_selecionado, codigo_selecionado, tipo_contrato, num_exib, nome_tecnico, nome_peca, codigo_rastreio)
        st.write(" ")
        st.download_button(label="📥 Clique Aqui para Efetuar o Download do PDF Gerado", data=pdf_bytes, file_name=f"aceite_{cliente_selecionado.replace(' ', '_')}.pdf", mime="application/pdf", use_container_width=True)
    else: st.warning("⚠️ Preencha todos os campos obrigatórios (*) e insira um valor em Real maior que R$ 0,00 para liberar as opções de gravação e download.")        

elif opcao_menu == "🔍 Consultar Histórico":
    st.subheader("📋 Histórico de Aceites Gravados em Tempo Real")
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df_vis = pd.read_csv(f"{url.replace('/edit', '')}/gviz/tq?tqx=out:csv&sheet=historico_aceites")
        if not df_vis.empty: st.dataframe(df_vis, use_container_width=True)
        else: st.info("Nenhum registro encontrado no histórico do Google Sheets.")
    except Exception as e: st.error(f"Não foi possível carregar o histórico: {e}")
