import streamlit as st
import pandas as pd
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Hub de Emissão - Aceite de Peças", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- ESTILIZAÇÃO CUSTOMIZADA (CSS) ---
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stMetric { background-color: #F8FAFC; padding: 15px; border-radius: 10px; border: 1px solid #E2E8F0; }
        div[data-testid="stExpander"] { border: 1px solid #CBD5E1 !important; border-radius: 8px !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🛠️ Hub de Emissão de Termos de Aceite")
st.markdown("Gerencie, audite e emita os PDFs dos chamados recebidos via **Microsoft Forms**.")

# --- CONEXÃO COM O GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=15)
def carregar_dados():
    try:
        df = conn.read(worksheet="historico_aceites", ttl=0)
        for col in ["NUM_CONTROLE", "CLIENTE", "TIPO_CONTRATO", "CUSTO"]:
            if col not in df.columns:
                df[col] = ""
        df["CUSTO"] = pd.to_numeric(df["CUSTO"], errors='coerce').fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Sheets: {e}")
        return pd.DataFrame()

df_hist = carregar_dados()

# --- FUNÇÃO AUXILIAR: PRÓXIMO NÚMERO MASTER ---
def calcular_proximo_master(df):
    if not df.empty and "NUM_CONTROLE" in df.columns:
        df_master = df[df["TIPO_CONTRATO"] == "Master"]
        if not df_master.empty:
            valores = pd.to_numeric(df_master["NUM_CONTROLE"], errors='coerce').dropna()
            if not valores.empty:
                return int(valores.max()) + 1
    return 1

# --- REPORTLAB: GERADOR DE PDF ---
def gerar_pdf_bytes(cliente, endereco, codigo, tipo, num_exib, tecnico, peca, rastreio):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    style_titulo = ParagraphStyle('T', parent=styles['Heading1'], fontSize=18, leading=22, alignment=1, spaceAfter=20, textColor=colors.HexColor('#1E3A8A'))
    style_sub = ParagraphStyle('S', parent=styles['Heading2'], fontSize=12, leading=16, spaceBefore=10, spaceAfter=10, textColor=colors.HexColor('#1E3A8A'))
    style_corpo = ParagraphStyle('C', parent=styles['Normal'], fontSize=10, leading=14)
    
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
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#F3F4F6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
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

# --- BLOCOS DE MÉTRICAS (KPIs DO PAINEL) ---
st.write("---")
if not df_hist.empty:
    total_chamados = len(df_hist)
    pendentes_master = len(df_hist[(df_hist["TIPO_CONTRATO"] == "Master") & ((df_hist["NUM_CONTROLE"] == "") | (df_hist["NUM_CONTROLE"].isna()) | (df_hist["NUM_CONTROLE"] == "nan"))])
    custo_total = df_hist["CUSTO"].sum()
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric(label="Total de Chamados Capturados", value=total_chamados)
    with m2:
        st.metric(label="Contratos Master Aguardando ID", value=pendentes_master, delta="Atenção" if pendentes_master > 0 else "OK")
    with m3:
        st.metric(label="Volume Financeiro em Peças", value=f"R$ {custo_total:,.2f}")

st.write("---")

# --- CONTEÚDO PRINCIPAL ---
if df_hist.empty:
    st.info("Nenhum dado integrado na planilha 'historico_aceites' ainda.")
else:
    col_lista, col_visor = st.columns([1.1, 1.9])
    
    with col_lista:
        st.markdown("### 📋 Seleção de Chamado")
        
        df_hist['identificador_visual'] = [
            f"[{row['DATA_GERACAO']}] {row['CLIENTE']} ({row['TIPO_CONTRATO']})" 
            for idx, row in df_hist.iterrows()
        ]
        
        lista_opcoes = list(df_hist['identificador_visual'].values)
        selecionado = st.radio("Escolha um chamado enviado pelo Forms para analisar:", lista_opcoes, label_visibility="collapsed")
        
        # Extrai a linha selecionada como uma Série do Pandas usando .iloc[0]
        index_selecionado = df_hist[df_hist['identificador_visual'] == selecionado].index
        row_foco = df_hist[df_hist['identificador_visual'] == selecionado].iloc[0]

    with col_visor:
        st.markdown("### 🔎 Painel de Validação e Emissão de PDF")
        
        with st.container():
            st.markdown(f"#### Registro Corrente: *{row_foco.get('CLIENTE', '')}*")
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**📍 Endereço:**\n{row_foco.get('ENDERECO', 'N/A')}")
            c2.markdown(f"**🛗 Cód. Elevador:**\n`{row_foco.get('CODELEVADOR', 'N/A')}`")
            c3.markdown(f"**📆 Recebido em:**\n{row_foco.get('DATA_GERACAO', 'N/A')}")
            
            st.write(" ")
            
            c4, c5, c6 = st.columns(3)
            c4.markdown(f"**👤 Técnico:**\n{row_foco.get('TECNICO', 'N/A')}")
            c5.markdown(f"**📄 Contrato:**\n`{row_foco.get('TIPO_CONTRATO', 'N/A')}`")
            
            tipo_contrato = str(row_foco.get("TIPO_CONTRATO", ""))
            num_atual = str(row_foco.get("NUM_CONTROLE", "")).strip()
            
            if tipo_contrato == "Master" and (num_atual == "" or num_atual == "nan" or pd.isna(row_foco["NUM_CONTROLE"])):
                id_calculado = calcular_proximo_master(df_hist)
                c6.markdown(f"**🔢 Nº Controle:**\n<span style='color:#EF4444;font-weight:bold;'>Gerando #{id_calculado}</span>", unsafe_allow_html=True)
                num_final = str(id_calculado)
                deve_gravar_id_sheets = True
            else:
                c6.markdown(f"**🔢 Nº Controle:**\n`{num_atual}`")
                num_final = num_atual
                deve_gravar_id_sheets = False
                
            st.write(" ")
            st.markdown(f"📦 **Peça Aplicada:** {row_foco.get('PECA', 'N/A')} | **Rastreio:** `{row_foco.get('RASTREIO', 'N/A')}` | **Valor:** R$ {row_foco.get('CUSTO', 0.0):.2f}")
            
            st.write("---")
            
            if deve_gravar_id_sheets:
                st.warning("⚠️ Este contrato do tipo Master precisa ter o seu número sequencial fixado no banco de dados antes de liberar o PDF final.")
                if st.button("💾 Chancelar e Fixar Número Master", use_container_width=True, type="primary"):
                    try:
                        df_hist.at[index_selecionado, "NUM_CONTROLE"] = num_final
                        df_salvar = df_hist.drop(columns=['identificador_visual'])
                        conn.update(worksheet="historico_aceites", data=df_salvar)
                        st.success(f"Sucesso! Número #{num_final} atrelado permanentemente ao cliente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Falha ao salvar modificação: {e}")
            else:
                exib_pdf = f"Controle Master: #{num_final}" if tipo_contrato == "Master" else f"Reparo: {num_final}"
                
                pdf_data = gerar_pdf_bytes(
                    str(row_foco.get("CLIENTE", "")), 
                    str(row_foco.get("ENDERECO", "")), 
                    str(row_foco.get("CODELEVADOR", "")),
                    tipo_contrato, 
                    exib_pdf, 
                    str(row_foco.get("TECNICO", "")), 
                    str(row_foco.get("PECA", "")), 
                    str(row_foco.get("RASTREIO", ""))
                )
                
                st.download_button(
                    label="📥 Imprimir / Gerar PDF do Termo de Aceite",
                    data=pdf_data,
                    file_name=f"Termo_Aceite_{str(row_foco.get('CLIENTE', ''))}.pdf".replace(' ', '_'),
                    mime="application/pdf",use_container_width=True)
                st.write(" ")with st.expander("📊 Ver Tabela Geral do Banco de Dados Completo (Google Sheets)"):st.dataframe(df_hist.drop(columns=['identificador_visual'], errors='ignore'), use_container_width=True)
