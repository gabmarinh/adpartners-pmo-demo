import os
import tempfile
import pandas as pd
import streamlit as st
import plotly.express as px
import pymupdf4llm
from crewai import Agent, Task, Crew, Process, LLM

# ---------------- CONFIGURACIÓN DE LA PÁGINA ----------------
st.set_page_config(page_title="Pluxow & AD Partners AI Demos", page_icon="🚀", layout="wide")

# ---------------- CONFIGURACIÓN DE SEGURIDAD ----------------
os.environ["CREWAI_TOOLS_ALLOW_UNSAFE_PATHS"] = "true"

try:
    groq_key = st.secrets["GROQ_API_KEY"]
except Exception:
    groq_key = os.environ.get("GROQ_API_KEY", "")

# ---------------- SISTEMA DE LOGIN ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔒 Acceso a la Plataforma PMO</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Pluxow + Practical Thinking Group</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Ingresar", use_container_width=True)
            
            if submit:
                if usuario == "admin" and password == "admin123":
                    st.session_state.logged_in = True
                    st.session_state.role = "admin"
                    st.session_state.username = "Administrador"
                    st.rerun()
                elif usuario == "consultor" and password == "user123":
                    st.session_state.logged_in = True
                    st.session_state.role = "consultor"
                    st.session_state.username = "Consultor PMO"
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Intente nuevamente.")
        
        st.info("**Cuentas de prueba para la Demo:**\n\nDueño: `admin` / `admin123`\n\nEmpleado: `consultor` / `user123`")
    st.stop() 

# ---------------- MENÚ LATERAL ----------------
st.sidebar.title("🚀 Menú de Soluciones AI")
st.sidebar.success(f"👤 Bienvenido, **{st.session_state.username}**")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.rerun()

st.sidebar.divider()
demo_seleccionada = st.sidebar.radio(
    "Seleccione el entorno:", 
    ["Demo 1: Asistente Normativas PMO", "Demo 2: Tablero Tracking Beneficios", "⚙️ Panel de Administración"]
)

# ==========================================================
# MOTOR DE IA GLOBAL
# ==========================================================
@st.cache_resource
def iniciar_motor_ia():
    return LLM(
        model="openai/openai/gpt-oss-120b",
        api_key=groq_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=0
    )

motor_blindado = iniciar_motor_ia()

# ==========================================================
# FUNCIONES DE EXTRACCIÓN AUTOMATIZADA (CACHÉ)
# ==========================================================
@st.cache_data(show_spinner=False)
def extraer_texto_pdf(pdf_bytes):
    # Guardamos el PDF en un archivo temporal seguro en la nube
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    # Transformamos el PDF a Markdown puro
    texto_md = pymupdf4llm.to_markdown(tmp_path)
    os.remove(tmp_path) # Limpiamos el servidor
    return texto_md

# ==========================================================
# DEMO 1: ASISTENTE RAG (AHORA CON LECTURA DINÁMICA DE PDF)
# ==========================================================
if demo_seleccionada == "Demo 1: Asistente Normativas PMO":
    st.title("🤖 Asistente de Normativas PMO")
    st.markdown("Sube el **Manual de Metodología (PDF)** original. La plataforma lo leerá automáticamente.")
    
    archivo_pdf = st.file_uploader("Cargar documento (PDF)", type=["pdf"])
    ruta_pdf_local = "manual_pmo.pdf"
    
    texto_documento = ""
    
    # Lógica híbrida: Si el usuario sube un archivo, lo procesa. Si no, usa el predeterminado.
    if archivo_pdf is not None:
        with st.spinner("Transformando PDF con IA (Esto tomará unos segundos)..."):
            texto_documento = extraer_texto_pdf(archivo_pdf.read())
        st.success("✅ Documento procesado e inyectado en la memoria del Agente.")
    else:
        if os.path.exists(ruta_pdf_local):
            with open(ruta_pdf_local, "rb") as f:
                texto_documento = extraer_texto_pdf(f.read())
            st.info("Usando el manual predeterminado. Puedes subir uno nuevo arriba.")
        else:
            st.warning("No hay documento base. Por favor, sube un archivo PDF para comenzar.")

    # Sistema de Chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ej: ¿Cuáles son los pasos para cerrar un proyecto?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            if not texto_documento:
                st.error("No hay ningún documento cargado para analizar.")
            else:
                with st.spinner("Analizando normativas..."):
                    try:
                        # Ya no usamos FileReadTool. Pasamos el texto directo para evitar bugs de bases de datos.
                        agente_normativo = Agent(
                            role='Especialista en Normativas PMO',
                            goal='Responder dudas basándose EXCLUSIVAMENTE en el texto proporcionado.',
                            backstory='Auditor estricto. Nunca inventas información. Buscas en el manual y respondes con viñetas claras.',
                            llm=motor_blindado, 
                            verbose=True, 
                            allow_delegation=False
                        )
                        tarea = Task(
                            description=f'Aquí tienes el manual completo de la empresa:\n\n{texto_documento}\n\nResponde detalladamente a esta pregunta del usuario basándote solo en el texto superior: "{prompt}"', 
                            expected_output='Respuesta detallada y estructurada.', 
                            agent=agente_normativo
                        )
                        resultado = str(Crew(agents=[agente_normativo], tasks=[tarea], process=Process.sequential).kickoff())
                        st.markdown(resultado)
                        st.session_state.messages.append({"role": "assistant", "content": resultado})
                    except Exception as e:
                        st.error(f"Error en el procesamiento: {e}")

# ==========================================================
# DEMO 2: TABLERO INTELIGENTE (AHORA CON LECTURA DE EXCEL)
# ==========================================================
elif demo_seleccionada == "Demo 2: Tablero Tracking Beneficios":
    st.title("📊 Tablero de Control y Análisis Financiero")
    st.markdown("Sube tu matriz de **Indicadores PMO original (Excel)**. El sistema lo analizará en tiempo real.")
    
    archivo_excel = st.file_uploader("Cargar Matriz (Excel)", type=["xlsx", "xls"])
    ruta_excel_local = "kpis_pmo.xlsx"
    
    df = None
    try:
        if archivo_excel is not None:
            df = pd.read_excel(archivo_excel, engine="openpyxl")
        elif os.path.exists(ruta_excel_local):
            df = pd.read_excel(ruta_excel_local, engine="openpyxl")
            st.info("Usando matriz predeterminada. Puedes subir un Excel nuevo arriba.")
        else:
            st.warning("Sube un archivo Excel para visualizar los datos.")
            
        if df is not None:
            # Mostrar vista previa de los datos brutos
            st.subheader("Datos Extraídos")
            st.dataframe(df.head(10), use_container_width=True)
            st.divider()

            if st.button("Generar Auditoría con IA 🧠", type="primary"):
                with st.spinner("El Analista IA está procesando el archivo Excel..."):
                    # Convertimos el DataFrame limpio a Markdown para la IA
                    datos_texto = df.to_markdown(index=False)
                    
                    analista_financiero = Agent(
                        role='Auditor Senior de PMO',
                        goal='Analizar los datos del Excel y detectar riesgos, desviaciones y anomalías.',
                        backstory='Eres un analista de AD Partners obsesionado con los datos. Encuentras patrones que los humanos no ven.',
                        llm=motor_blindado, 
                        verbose=True, 
                        allow_delegation=False
                    )
                    tarea_analisis = Task(
                        description=f"Analiza profundamente esta matriz de datos financieros/operativos:\n\n{datos_texto}\n\nIdentifica los puntos críticos, proyectos con problemas o cuellos de botella y redacta un reporte ejecutivo para la gerencia.", 
                        expected_output="Un reporte ejecutivo estructurado (Diagnóstico, Hallazgos, Recomendaciones).", 
                        agent=analista_financiero
                    )
                    reporte_final = str(Crew(agents=[analista_financiero], tasks=[tarea_analisis], process=Process.sequential).kickoff())
                    
                    st.success("Reporte de Auditoría Generado.")
                    st.info(reporte_final)

    except Exception as e:
        st.error(f"Error al leer el archivo Excel. Asegúrate de que el formato sea correcto. Detalle: {e}")

# ==========================================================
# PANEL DE ADMINISTRACIÓN
# ==========================================================
elif demo_seleccionada == "⚙️ Panel de Administración":
    st.title("⚙️ Gestión Interna")
    if st.session_state.role != "admin":
        st.error("🚫 ACCESO DENEGADO")
    else:
        st.success("✅ Acceso Autorizado: Perfil Administrador")
        st.markdown("La plataforma ahora procesa archivos dinámicamente. Módulos locales deshabilitados.")
