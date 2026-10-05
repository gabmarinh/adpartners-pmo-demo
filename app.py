import os
import pandas as pd
import streamlit as st
import plotly.express as px
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import FileReadTool

# ---------------- CONFIGURACIÓN DE LA PÁGINA ----------------
st.set_page_config(page_title="Pluxow & AD Partners AI Demos", page_icon="🚀", layout="wide")

# ---------------- CONFIGURACIÓN DE SEGURIDAD ----------------
os.environ["CREWAI_TOOLS_ALLOW_UNSAFE_PATHS"] = "true"
groq_key = st.secrets["GROQ_API_KEY"] if "GROQ_API_KEY" in st.secrets else os.environ.get("GROQ_API_KEY", "")

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
# DEMO 1: ASISTENTE RAG
# ==========================================================
if demo_seleccionada == "Demo 1: Asistente Normativas PMO":
    st.title("🤖 Asistente de Normativas PMO")
    
    md_path = "normativas_pmo_demo.md"

    def crear_agente_pmo():
        md_tool = FileReadTool(file_path=md_path)
        
        # BYPASS: Le decimos que es OpenAI, pero apuntamos a la URL de Groq
        motor_blindado = LLM(
            model="openai/llama-3.3-70b-versatile",
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=0
        )
        
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
                    st.error(f"Error interno del servidor: {e}")

# ==========================================================
# DEMO 2: TABLERO INTELIGENTE
# ==========================================================
elif demo_seleccionada == "Demo 2: Tablero Tracking Beneficios":
    st.title("📊 Tablero de Control: KPIs y Estado RAG")
    
    csv_path = "proyectos_kpi.csv"
    
    try:
        df = pd.read_csv(csv_path)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Proyectos", len(df))
        m2.metric("Proyectos On Track", len(df[df['Estado_RAG'] == 'Green']))
        m3.metric("Proyectos en Riesgo", len(df[df['Estado_RAG'] == 'Amber']))
        m4.metric("Proyectos Críticos", len(df[df['Estado_RAG'] == 'Red']))
        
        col_pie1, col_pie2 = st.columns(2)
        with col_pie1:
            st.plotly_chart(px.pie(df, names='Estado_RAG', hole=0.4, title='Estado RAG', color='Estado_RAG', color_discrete_map={'Green':'#28a745', 'Amber':'#ffc107', 'Red':'#dc3545'}), use_container_width=True)
        with col_pie2:
            st.plotly_chart(px.pie(df, names='Nivel_Riesgo', hole=0.4, title='Nivel de Riesgo', color='Nivel_Riesgo', color_discrete_map={'Bajo':'#28a745', 'Medio':'#ffc107', 'Alto':'#dc3545'}), use_container_width=True)

        st.divider()

        def color_rag(val):
            if val == 'Green': return 'background-color: #28a745; color: white; font-weight: bold;'
            elif val == 'Amber': return 'background-color: #ffc107; color: black; font-weight: bold;'
            elif val == 'Red': return 'background-color: #dc3545; color: white; font-weight: bold;'
            return ''
        
        st.subheader("Detalle Operativo de Proyectos")
        st.dataframe(df.style.map(color_rag, subset=['Estado_RAG']), use_container_width=True)

        st.divider()

        if st.button("Generar Reporte Ejecutivo con IA 🧠", type="primary"):
            with st.spinner("El Analista Financiero IA está procesando los KPIs..."):
                datos_texto = df.to_markdown(index=False)
                
                # BYPASS: Le decimos que es OpenAI, pero apuntamos a la URL de Groq
                motor_blindado = LLM(
                    model="openai/llama-3.3-70b-versatile",
                    api_key=groq_key,
                    base_url="https://api.groq.com/openai/v1",
                    temperature=0
                )
                
                analista_financiero = Agent(
                    role='Analista Senior de PMO y Riesgos',
                    goal='Analizar KPIs financieros y cruzar el estado RAG con niveles de riesgo.',
                    backstory='Auditor experto de AD Partners. Eres preciso y te enfocas en mitigación de riesgos.',
                    llm=motor_blindado, 
                    verbose=True, 
                    allow_delegation=False
                )
                tarea_analisis = Task(
                    description=f"Analiza la siguiente matriz:\n\n{datos_texto}\n\nConcéntrate explícitamente en proyectos 'Red' y 'Amber'.", 
                    expected_output="Un reporte ejecutivo estructurado evaluando el riesgo y desviaciones.", 
                    agent=analista_financiero
                )
                reporte_final = str(Crew(agents=[analista_financiero], tasks=[tarea_analisis], process=Process.sequential).kickoff())
                
                st.success("Reporte generado.")
                st.info(reporte_final)

    except FileNotFoundError:
        st.error(f"No se encontró el archivo CSV en la ruta especificada.")

# ==========================================================
# PANEL DE ADMINISTRACIÓN
# ==========================================================
elif demo_seleccionada == "⚙️ Panel de Administración":
    st.title("⚙️ Gestión de Base de Conocimientos")
    if st.session_state.role != "admin":
        st.error("🚫 ACCESO DENEGADO")
    else:
        st.success("✅ Acceso Autorizado: Perfil Administrador")
        st.markdown("Función de subida de archivos deshabilitada en la versión Demo Cloud.")
