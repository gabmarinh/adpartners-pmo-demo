import os
import pandas as pd
import streamlit as st
import plotly.express as px
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import FileReadTool

# --- PARCHE DE SEGURIDAD PARA EVITAR EL BUG DE CACHÉ DE LITELLM ---
try:
    import crewai.llms.cache as crew_cache
    crew_cache.mark_cache_breakpoint = lambda msg: msg
except Exception:
    pass
# ------------------------------------------------------------------

# ---------------- CONFIGURACIÓN DE LA PÁGINA ----------------
st.set_page_config(page_title="Pluxow & AD Partners AI Demos", page_icon="🚀", layout="wide")

# ---------------- CONFIGURACIÓN DE SEGURIDAD ----------------
os.environ["CREWAI_TOOLS_ALLOW_UNSAFE_PATHS"] = "true"

# Extracción segura de la API Key para la nube
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
    # Conexión limpia a Groq con el modelo oficial vigente
    return LLM(
        model="groq/gpt-oss-120b", 
        api_key=groq_key,
        temperature=0
    )

motor_blindado = iniciar_motor_ia()

# ==========================================================
# DEMO 1: ASISTENTE RAG
# ==========================================================
if demo_seleccionada == "Demo 1: Asistente Normativas PMO":
    st.title("🤖 Asistente de Normativas PMO")
    
    md_path = "normativas_pmo_demo.md"

    def crear_agente_pmo():
        md_tool = FileReadTool(file_path=md_path)
        
        return Agent(
            role='Especialista en Normativas PMO',
            goal='Responder dudas basándose exclusivamente en el documento Markdown.',
            backstory='Consultor experto. Siempre justificas tu respuesta extrayendo datos exactos del archivo proporcionado.',
            tools=[md_tool], 
            llm=motor_blindado, 
            verbose=True, 
            allow_delegation=False
        )

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
            with st.spinner("Buscando en repositorios..."):
                try:
                    agente = crear_agente_pmo()
                    tarea = Task(
                        description=f'Lee el contenido del archivo y responde la siguiente duda del usuario: "{prompt}"', 
                        expected_output='Respuesta detallada y estructurada en viñetas.', 
                        agent=agente
                    )
                    crew = Crew(agents=[agente], tasks=[tarea], process=Process.sequential)
                    resultado = str(crew.kickoff())
                    st.markdown(resultado)
                    st.session_state.messages.append({"role": "assistant", "content": resultado})
                except Exception as e:
                    st.error(f"Error en el servidor: {e}")

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
        # Definir el archivo a procesar
        archivo_a_leer = archivo_excel if archivo_excel is not None else (ruta_excel_local if os.path.exists(ruta_excel_local) else None)
        
        if archivo_a_leer is not None:
            # 1. Leemos las hojas específicas del archivo de Romina
            # La hoja NDP tiene los presupuestos (Fila 2 es el header)
            df_ndp = pd.read_excel(archivo_a_leer, sheet_name="NDP", header=1, engine="openpyxl")
            # La hoja DRP tiene los riesgos (Fila 2 es el header)
            df_drp = pd.read_excel(archivo_a_leer, sheet_name="DRP", header=1, engine="openpyxl").dropna(subset=['ID_Proyecto'])
            
            # 2. Unimos los datos usando el ID del proyecto
            df = pd.merge(df_ndp, df_drp[['ID_Proyecto', 'Perfil de Riesgo del Proyecto']], on='ID_Proyecto', how='left')
            
            # 3. Transformamos la data cruda a los KPIs de semáforo que espera el Dashboard
            def mapear_rag(estado):
                estado = str(estado).lower()
                if 'dentro' in estado: return 'Green'
                elif 'moderado' in estado: return 'Amber'
                else: return 'Red'
                
            def mapear_riesgo(perfil):
                perfil = str(perfil).lower()
                if 'alto' in perfil: return 'Alto'
                elif 'moderado' in perfil: return 'Medio'
                else: return 'Bajo'

            df['Estado_RAG'] = df['Estado de Presupuesto'].apply(mapear_rag)
            df['Nivel_Riesgo'] = df['Perfil de Riesgo del Proyecto'].apply(mapear_riesgo)
            
            # Limpiamos las columnas para mostrar una tabla ejecutiva
            df_ejecutivo = df[['ID_Proyecto', 'Nombre_Proyecto', 'Estado_RAG', 'Nivel_Riesgo', 'Presupuesto', 'Consumo Real Total', 'Variación (%)']].copy()
            
            if archivo_excel is None:
                st.info("Usando matriz predeterminada. Puedes subir un Excel nuevo arriba.")
            
            # --- Renderizado del Dashboard ---
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Proyectos", len(df_ejecutivo))
            m2.metric("Proyectos On Track", len(df_ejecutivo[df_ejecutivo['Estado_RAG'] == 'Green']))
            m3.metric("Proyectos en Riesgo", len(df_ejecutivo[df_ejecutivo['Estado_RAG'] == 'Amber']))
            m4.metric("Proyectos Críticos", len(df_ejecutivo[df_ejecutivo['Estado_RAG'] == 'Red']))
            
            col_pie1, col_pie2 = st.columns(2)
            with col_pie1:
                st.plotly_chart(px.pie(df_ejecutivo, names='Estado_RAG', hole=0.4, title='Estado RAG', color='Estado_RAG', color_discrete_map={'Green':'#28a745', 'Amber':'#ffc107', 'Red':'#dc3545'}), use_container_width=True)
            with col_pie2:
                st.plotly_chart(px.pie(df_ejecutivo, names='Nivel_Riesgo', hole=0.4, title='Nivel de Riesgo', color='Nivel_Riesgo', color_discrete_map={'Bajo':'#28a745', 'Medio':'#ffc107', 'Alto':'#dc3545'}), use_container_width=True)

            st.divider()

            def color_rag(val):
                if val == 'Green': return 'background-color: #28a745; color: white; font-weight: bold;'
                elif val == 'Amber': return 'background-color: #ffc107; color: black; font-weight: bold;'
                elif val == 'Red': return 'background-color: #dc3545; color: white; font-weight: bold;'
                return ''
            
            st.subheader("Detalle Operativo de Proyectos")
            st.dataframe(df_ejecutivo.style.map(color_rag, subset=['Estado_RAG']), use_container_width=True)

            st.divider()

            if st.button("Generar Auditoría con IA 🧠", type="primary"):
                with st.spinner("El Analista IA está procesando el archivo Excel..."):
                    datos_texto = df_ejecutivo.to_markdown(index=False)
                    
                    analista_financiero = Agent(
                        role='Auditor Senior de PMO',
                        goal='Analizar los datos del Excel y detectar riesgos, desviaciones y anomalías.',
                        backstory='Eres un analista de AD Partners obsesionado con los datos. Encuentras patrones que los humanos no ven.',
                        llm=motor_blindado, 
                        verbose=True, 
                        allow_delegation=False
                    )
                    tarea_analisis = Task(
                        description=f"Analiza profundamente esta matriz de datos financieros/operativos:\n\n{datos_texto}\n\nIdentifica los puntos críticos (proyectos Red y Amber), cuellos de botella y redacta un reporte ejecutivo para la gerencia.", 
                        expected_output="Un reporte ejecutivo estructurado (Diagnóstico, Hallazgos, Recomendaciones).", 
                        agent=analista_financiero
                    )
                    reporte_final = str(Crew(agents=[analista_financiero], tasks=[tarea_analisis], process=Process.sequential).kickoff())
                    
                    st.success("Reporte de Auditoría Generado.")
                    st.info(reporte_final)
        else:
            st.warning("Sube un archivo Excel para visualizar los datos.")

    except Exception as e:
        st.error(f"Error al leer la matriz. Detalle técnico: {e}")

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
