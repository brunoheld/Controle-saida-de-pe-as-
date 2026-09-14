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
st.set_page_config(page_title="Controle de Troca de Peças", layout="wide")
st.title("🛠️ Painel de Controle e Emissão de Aceites")

# --- CONEXÃO COM O GOOGLE SHEETS via LINK PÚBLICO (Secrets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- LEITURA DO HISTÓRICO VINDO DO MS FORMS ---
@st.cache_data(ttl=10)  # Atualiza a cada 10 segundos para pegar novos envios do Forms rápido
def carregar_historico():
    try:
        return conn.read(worksheet="historico_aceites", ttl=0)
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        return pd.DataFrame()

df_hist = carregar_historico()

# --- CÁLCULO DO PRÓXIMO NÚMERO MASTER EM TEMPO REAL ---
def obter_proximo_numero_master(df):
    if "TIPO_CONTRATO" in df.columns and "NUM_CONTROLE" in df.columns:
        df_master = df[df["TIPO_CONTRATO"] == "Master"]
        if not df_master.empty:
            valores = pd.to_numeric(df_master["NUM_CONTROLE"], errors='coerce').dropna()
            if not valores.empty:
                return int(valores.max()) + 1
    return 1

# --- GERADOR DE PDF EM MEMÓRIA ---
def gerar_pdf_bytes(cliente, endereco, codigo, tipo, num_exib, tecnico, peca, rastreio):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    style_titulo = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=18, leading=22, alignment=1, spaceAfter=20, textColor=colors.HexColor('#1E3A8A'))
    style_sub = ParagraphStyle('Sub', parent=styles['Heading2'], fontSize=12, leading=16, spaceBefore=10, spaceAfter=10, textColor=colors.HexColor('#1E3A8A'))
    style_corpo = ParagraphStyle('Corpo', parent=styles['Normal'], fontSize=10, leading=14)
    
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
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elementos.append(tabela)
    elementos.append(Spacer(1, 40))
    
    elementos.append(Paragraph("<b>VALIDAÇÃO OPERACIONAL E ASSINATURAS</b>", style_sub))
    elementos.append(Spacer(1, 15))
    
    dados_assinatura = [
        [Paragraph("<b>Data da Assinatura:</b> ____/____/_______", style_corpo), Paragraph("", style_corpo)],
        [Spacer(1, 30), Spacer(1, 30)],
        [Paragraph("_______________________________________<br/><b>Assinatura do Técnico</b>", style_corpo),
         Paragraph("_______________________________________<br/><b>Assinatura do Cliente</b>", style_corpo)]
    ]
    
    tabela_ass = Table(dados_assinatura)
    tabela_ass.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP')
    ]))
    elementos.append(tabela_ass)
    
    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()

# --- MENU LATERAL ---
st.sidebar.title("📌 Menu de Opções")
opcao_menu = st.sidebar.radio("Selecione a tela:", ["📋 Aguardando Emissão", "🔍 Histórico Geral"])

# ==============================================================================
# TELA: AGUARDANDO EMISSÃO (Dados vindos do Forms que precisam gerar PDF)
# ==============================================================================
if opcao_menu == "📋 Aguardando Emissão":
    st.subheader("Filas de Registros vindos do Microsoft Forms")
    
    if df_hist.empty:
        st.info("Nenhum dado encontrado na planilha.")
    else:
        # Registros que ainda não tem NUM_CONTROLE preenchido (ou seja, novos do Forms) ou todos para re-emissão
        # Para facilitar, vamos listar os registros e permitir que o usuário selecione um para processar.
        df_hist['Index_Original'] = df_hist.index # Guarda o index original para atualizar o sheet correto
        
        # Cria uma lista amigável para o Selectbox
        opcoes_registro = []
        for idx, row in df_hist.iterrows():
            opcoes_registro.append(f"Fila {idx} - {row.get('CLIENTE', 'Sem Nome')} ({row.get('DATA_GERACAO', '')})")
            
        registro_selecionado_str = st.selectbox("Selecione o chamado para processar e gerar PDF:", opciones_registro)
        
        if registro_selecionado_str:
            # Extrai o index original de volta
            idx_selecionado = int(registro_selecionado_str.split(" ")[1])
            row_atual = df_hist.loc[idx_selecionado]
            
            st.write("---")
            st.markdown("### 🔍 Dados do Chamado Selecionado")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Cliente", str(row_atual.get("CLIENTE", "")))
            col2.metric("Endereço", str(row_atual.get("ENDERECO", "")))
            col3.metric("Cód. Elevador", str(row_atual.get("CODELEVADOR", "")))
            
            col4, col5, col6 = st.columns(3)
            col4.metric("Técnico", str(row_atual.get("TECNICO", "")))
            col5.metric("Tipo Contrato", str(row_atual.get("TIPO_CONTRATO", "")))
            
            # Lógica do número de controle
            tipo_contrato = row_atual.get("TIPO_CONTRATO", "")
            num_atual = str(row_atual.get("NUM_CONTROLE", ""))
            
            # Se for Master e estiver vazio na planilha, calcula na hora
            if tipo_contrato == "Master" and (num_atual == "" or pd.isna(num_atual) or num_atual == "nan"):
                proximo_num = obter_proximo_numero_master(df_hist)
                st.warning(f"📋 Contrato Master detectado sem número. Próximo número disponível: **#{proximo_num}**")
                num_final = str(proximo_num)
                precisa_salvar_id = True
            else:
                num_final = num_atual
                precisa_salvar_id = False
                col6.metric("Nº Controle/Reparo", num_final)

            col7, col8, col9 = st.columns(3)
            col7.write(f"**Peça:** {row_atual.get('PECA', '')}")
            col8.write(f"**Rastreio:** {row_atual.get('RASTREIO', '')}")
            col9.write(f"**Custo:** R$ {row_atual.get('CUSTO', 0.0):.2f}")
            
            st.write("---")
            
            # Se for um ID Master novo gerado pelo Streamlit, precisamos salvar de volta na planilha para fixar ele
            if precisa_salvar_id:
                if st.button("💾 Validar e Fixar Número Master na Planilha", use_container_width=True):
                    try:
                        # Atualiza a célula específica no DataFrame e manda de volta pro Sheets
                        df_hist.at[idx_selecionado, "NUM_CONTROLE"] = num_final
                        # Remove a coluna temporária antes de salvar
                        df_salvar = df_hist.drop(columns=['Index_Original'])
                        conn.update(worksheet="historico_aceites", data=df_salvar)
                        st.success("Número Master gravado com sucesso no histórico!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar planilha: {e}")
            
            # Botão de download do PDF sempre ativo para o chamado selecionado
            num_exib_pdf = f"Controle Master: #{num_final}" if tipo_contrato == "Master" else f"Reparo: {num_final}"
            pdf_bytes = gerar_pdf_bytes(
                row_atual.get("CLIENTE", ""), row_atual.get("ENDERECO", ""), row_atual.get("CODELEVADOR", ""), 
                tipo_contrato, num_exib_pdf, row_atual.get("TECNICO", ""), row_atual.get("PECA", ""), row_atual.get("RASTREIO", ""))
            
            st.download_button(
                label="📥 Efetuar o Download do PDF Gerado", 
                data=pdf_bytes, 
                file_name=f"aceite_{str(row_atual.get('CLIENTE', '')).replace(' ', '_')}.pdf", 
                mime="application/pdf", 
                use_container_width=True
            )

# ==============================================================================
# TELA: HISTÓRICO GERAL
# ==============================================================================
elif opcao_menu == "🔍 Histórico Geral":
    st.subheader("Histórico Completo de Sincronizações (Forms + Sheets)")
    
    if not df_hist.empty:
        # Remove coluna temporária se ela existir
        df_exibir = df_hist.drop(columns=['Index_Original'], errors='ignore')
        st.dataframe(df_exibir, use_container_width=True)
    else:
        st.info("Nenhum dado registrado.")
