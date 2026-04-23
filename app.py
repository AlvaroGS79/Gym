import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from supabase import create_client, Client
from streamlit_option_menu import option_menu
from datetime import datetime
from typing import Dict, Any

# --- 1. VERIFICACIÓN DE SECRETOS ---
def check_secrets():
    required = ["SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY"]
    missing = [k for k in required if k not in st.secrets]
    if missing:
        st.error(f"Faltan secretos en el archivo TOML: {', '.join(missing)}")
        st.info("Asegúrate de que 'secrets.toml' esté dentro de una carpeta llamada '.streamlit'")
        st.stop()

check_secrets()

# --- 2. INICIALIZACIÓN ---
@st.cache_resource
def init_connections() -> tuple[Client, Any]:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    return sb, model

supabase, gemini_model = init_connections()

# ID de prueba (Debe ser un formato UUID válido)
USER_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

# --- 3. FUNCIONES DE APOYO ---
def calculate_macros(w, h, a, g, act, goal):
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "Masculino" else -161)
    tdee = bmr * act
    adj = {"Perder Grasa": -500, "Mantener": 0, "Ganar Músculo": 400}
    target = tdee + adj.get(goal, 0)
    return {"cal": target, "p": w * 2.0, "f": w * 0.8, "c": (target - (w*2*4) - (w*0.8*9))/4}

# --- 4. NAVEGACIÓN ---
with st.sidebar:
    selected = option_menu("Fitness OS", ["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"], 
                          icons=['house', 'activity', 'egg', 'gear'])

# --- 5. VISTAS ---
if selected == "Dashboard":
    st.header("Visualización de Progreso")
    
    try:
        # Consulta segura
        res = supabase.table("workouts").select("*").eq("user_id", USER_ID).order("date").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            fig = px.line(df, x="date", y="weight_kg", color="exercise", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay entrenamientos. ¡Registra el primero!")
    except Exception as e:
        st.error(f"Error de conexión con la base de datos: {e}")

elif selected == "Entrenamientos":
    st.header("Nuevo Registro")
    with st.form("workout_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        ex = c1.text_input("Ejercicio")
        dt = c2.date_input("Fecha", datetime.now())
        s, r, w = st.columns(3)
        sets = s.number_input("Series", 1, 10, 3)
        reps = r.number_input("Reps", 1, 50, 10)
        weight = w.number_input("Peso (kg)", 0.0, 500.0, 60.0)
        
        if st.form_submit_button("Registrar"):
            try:
                supabase.table("workouts").insert({
                    "user_id": USER_ID, "exercise": ex, "date": str(dt), 
                    "sets": sets, "reps": reps, "weight_kg": weight
                }).execute()
                st.toast("Guardado correctamente", icon="✅")
            except Exception as e:
                st.error(f"Error al guardar: {e}")

elif selected == "Nutrición":
    st.header("Dieta IA")
    try:
        profile = supabase.table("profiles").select("*").eq("id", USER_ID).single().execute().data
        if not profile:
            st.warning("Configura tu perfil en Ajustes primero.")
        else:
            goal = st.selectbox("Objetivo", ["Perder Grasa", "Mantener", "Ganar Músculo"])
            m = calculate_macros(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], goal)
            
            st.write(f"### Calorías Objetivo: {m['cal']:.0f} kcal")
            if st.button("Generar Plan"):
                with st.spinner("Cocinando..."):
                    prompt = f"Dieta de {m['cal']:.0f} kcal. Tipo: {profile['diet_type']}. Alergias: {profile['allergies']}. Formato: Tabla."
                    resp = gemini_model.generate_content(prompt)
                    st.markdown(resp.text)
    except Exception:
        st.error("Error al obtener perfil. ¿Has guardado tus datos en Ajustes?")

elif selected == "Ajustes":
    st.header("Perfil")
    # Intentar cargar datos actuales de forma segura
    try:
        curr = supabase.table("profiles").select("*").eq("id", USER_ID).single().execute().data or {}
    except:
        curr = {}

    with st.form("settings"):
        c1, c2 = st.columns(2)
        w = c1.number_input("Peso (kg)", 30.0, 200.0, float(curr.get('weight', 75)))
        h = c2.number_input("Altura (cm)", 100.0, 250.0, float(curr.get('height', 175)))
        a = c1.number_input("Edad", 15, 90, int(curr.get('age', 25)))
        g = c2.selectbox("Género", ["Masculino", "Femenino"])
        act = st.select_slider("Actividad", [1.2, 1.375, 1.55, 1.725], value=float(curr.get('activity_level', 1.2)))
        diet = st.text_input("Tipo de Dieta (Omnívora, Vegana...)", curr.get('diet_type', 'Omnívora'))
        
        if st.form_submit_button("Guardar"):
            try:
                supabase.table("profiles").upsert({
                    "id": USER_ID, "weight": w, "height": h, "age": a, "gender": g,
                    "activity_level": act, "diet_type": diet
                }).execute()
                st.success("Perfil actualizado")
            except Exception as e:
                st.error(f"Error al guardar perfil: {e}")
