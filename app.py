import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from supabase import create_client, Client
from streamlit_option_menu import option_menu
from datetime import datetime
from typing import Dict, Any

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Fitness OS Ultimate", layout="wide", page_icon="🔥")

# --- INICIALIZACIÓN DE CLIENTES ---
@st.cache_resource
def init_connections() -> tuple[Client, Any]:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    return sb, model

supabase, gemini_model = init_connections()

# --- CONSTANTES DE PRUEBA (Reemplazar con auth.user en Pro) ---
USER_ID = "00000000-0000-0000-0000-000000000000"

# --- LÓGICA DE NEGOCIO ---
def calculate_macros(w, h, a, g, act, goal):
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "Masculino" else -161)
    tdee = bmr * act
    adj = {"Perder Grasa": -500, "Mantener": 0, "Ganar Músculo": 400}
    target = tdee + adj.get(goal, 0)
    return {"cal": target, "p": w * 2.0, "f": w * 0.8, "c": (target - (w*2*4) - (w*0.8*9))/4}

def get_diet(params: Dict):
    prompt = f"Eres un nutricionista. Crea una dieta de {params['cal']:.0f} kcal. Macros: P:{params['p']:.0f}g, C:{params['c']:.0f}g, F:{params['f']:.0f}g. Tipo: {params['diet_type']}. Alergias: {params['allergies']}. Odia: {params['disliked']}. Formato: Markdown con tablas."
    return gemini_model.generate_content(prompt).text

# --- NAVEGACIÓN ---
with st.sidebar:
    selected = option_menu("Menú", ["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"], 
                          icons=['house', 'activity', 'egg', 'gear'])

# --- VISTAS ---
if selected == "Dashboard":
    st.header("Visualización de Progreso")
    data_container = st.empty()
    
    res = supabase.table("workouts").select("*").eq("user_id", USER_ID).order("date").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        fig = px.line(df, x="date", y="weight_kg", color="exercise", markers=True, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Registra datos en la pestaña de Entrenamientos.")

elif selected == "Entrenamientos":
    st.header("Nuevo Registro")
    with st.form("workout_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        ex = c1.text_input("Ejercicio (ej: Press Militar)")
        dt = c2.date_input("Fecha", datetime.now())
        s, r, w = st.columns(3)
        sets = s.number_input("Series", 1, 10, 3)
        reps = r.number_input("Reps", 1, 50, 10)
        weight = w.number_input("Peso (kg)", 0.0, 500.0, 60.0)
        
        if st.form_submit_button("Registrar Sesión"):
            supabase.table("workouts").insert({
                "user_id": USER_ID, "exercise": ex, "date": str(dt), 
                "sets": sets, "reps": reps, "weight_kg": weight
            }).execute()
            st.toast("¡Carga guardada!", icon="✅")

elif selected == "Nutrición":
    st.header("Asistente Nutricional IA")
    profile = supabase.table("profiles").select("*").eq("id", USER_ID).single().execute().data
    
    if not profile:
        st.warning("Primero configura tus datos en Ajustes.")
    else:
        goal = st.selectbox("Tu Objetivo", ["Perder Grasa", "Mantener", "Ganar Músculo"])
        m = calculate_macros(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], goal)
        
        # Dashboard de Macros
        cols = st.columns(4)
        cols[0].metric("Calorías", f"{m['cal']:.0f}")
        cols[1].metric("Proteína", f"{m['p']:.0f}g")
        cols[2].metric("Carbs", f"{m['c']:.0f}g")
        cols[3].metric("Grasas", f"{m['f']:.0f}g")
        
        if st.button("Generar Dieta (Gemini)") or st.session_state.get('regen'):
            with st.spinner("Generando plan personalizado..."):
                plan = get_diet({**m, "goal": goal, "diet_type": profile['diet_type'], 
                                "allergies": profile['allergies'], "disliked": profile['disliked_foods']})
                st.markdown(plan)
                st.button("🔄 Regenerar Dieta", on_click=lambda: st.session_state.update({'regen': True}))

elif selected == "Ajustes":
    st.header("Tu Perfil")
    curr = supabase.table("profiles").select("*").eq("id", USER_ID).single().execute().data or {}
    
    with st.form("settings_pro"):
        c1, c2 = st.columns(2)
        w = c1.number_input("Peso Actual (kg)", 30.0, 200.0, float(curr.get('weight', 75)))
        h = c2.number_input("Altura (cm)", 100.0, 250.0, float(curr.get('height', 175)))
        a = c1.number_input("Edad", 15, 90, int(curr.get('age', 25)))
        g = c2.selectbox("Género", ["Masculino", "Femenino"], index=0 if curr.get('gender')=="Masculino" else 1)
        act = st.select_slider("Nivel de Actividad", [1.2, 1.375, 1.55, 1.725], value=float(curr.get('activity_level', 1.2)))
        
        st.subheader("Filtros de IA")
        diet = st.selectbox("Estilo", ["Omnívora", "Keto", "Vegetariana", "Vegana"], index=0)
        allergies = st.text_input("Alergias", curr.get('allergies', ""))
        disliked = st.text_input("No me gusta", curr.get('disliked_foods', ""))
        
        if st.form_submit_button("Guardar Configuración"):
            supabase.table("profiles").upsert({
                "id": USER_ID, "weight": w, "height": h, "age": a, "gender": g,
                "activity_level": act, "diet_type": diet, "allergies": allergies, "disliked_foods": disliked
            }).execute()
            st.success("Ajustes guardados correctamente.")