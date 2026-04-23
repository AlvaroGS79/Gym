import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from supabase import create_client, Client
from streamlit_option_menu import option_menu
from datetime import datetime
from typing import Dict, Any

# --- CONFIGURACIÓN DE CREDENCIALES (HARDCODED) ---
# Nota: Esto es solo para depuración. No compartas este archivo públicamente.
S_URL = "https://hffrbskyjwmkurwwdzcj.supabase.co"
S_KEY = "sb_publishable_H8uLitl0KwczBr2owTbTTA_uPCFoXGd"
G_KEY = "AIzaSyBm_tP0SlIJ86ERXcxMPZSvA7pEnfiPrqw"

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Fitness OS Ultimate", layout="wide", page_icon="🔥")

# --- INICIALIZACIÓN DE CLIENTES ---
@st.cache_resource
def init_connections() -> tuple[Client, Any]:
    # Conexión directa usando las variables de arriba
    sb = create_client(S_URL, S_KEY)
    genai.configure(api_key=G_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    return sb, model

try:
    supabase, gemini_model = init_connections()
except Exception as e:
    st.error(f"Error crítico de conexión: {e}")
    st.stop()

# ID de usuario persistente para pruebas
USER_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

# --- LÓGICA DE NEGOCIO ---
def calculate_macros(w, h, a, g, act, goal):
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "Masculino" else -161)
    tdee = bmr * act
    adj = {"Perder Grasa": -500, "Mantener": 0, "Ganar Músculo": 400}
    target = tdee + adj.get(goal, 0)
    # Proteína: 2g/kg, Grasa: 0.8g/kg, Resto: Carbohidratos
    p = w * 2.0
    f = w * 0.8
    c = (target - (p * 4) - (f * 9)) / 4
    return {"cal": target, "p": p, "f": f, "c": c}

# --- NAVEGACIÓN ---
with st.sidebar:
    selected = option_menu("Fitness OS", ["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"], 
                          icons=['house', 'activity', 'egg', 'gear'])

# --- VISTAS ---
if selected == "Dashboard":
    st.header("Visualización de Progreso")
    try:
        res = supabase.table("workouts").select("*").eq("user_id", USER_ID).order("date").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            fig = px.line(df, x="date", y="weight_kg", color="exercise", markers=True, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos. Registra tu primer entrenamiento en la pestaña correspondiente.")
    except Exception as e:
        st.error(f"Error al leer de Supabase: {e}")

elif selected == "Entrenamientos":
    st.header("Registro de Entrenamiento")
    with st.form("workout_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        ex = c1.text_input("Ejercicio (ej: Press de Banca)")
        dt = c2.date_input("Fecha", datetime.now())
        s, r, w = st.columns(3)
        sets = s.number_input("Series", 1, 10, 3)
        reps = r.number_input("Repeticiones", 1, 50, 10)
        weight = w.number_input("Carga (kg)", 0.0, 500.0, 60.0)
        
        if st.form_submit_button("Guardar Registro"):
            try:
                supabase.table("workouts").insert({
                    "user_id": USER_ID, "exercise": ex, "date": str(dt), 
                    "sets": sets, "reps": reps, "weight_kg": weight
                }).execute()
                st.toast("¡Entrenamiento guardado!", icon="💪")
            except Exception as e:
                st.error(f"Error al insertar datos: {e}")

elif selected == "Nutrición":
    st.header("Planificación Dietética IA")
    try:
        profile_res = supabase.table("profiles").select("*").eq("id", USER_ID).single().execute()
        profile = profile_res.data
        
        if not profile:
            st.warning("⚠️ Debes configurar tu perfil en 'Ajustes' antes de generar una dieta.")
        else:
            goal = st.selectbox("Objetivo", ["Perder Grasa", "Mantener", "Ganar Músculo"])
            m = calculate_macros(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], goal)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Kcal", f"{m['cal']:.0f}")
            c2.metric("Proteína", f"{m['p']:.0f}g")
            c3.metric("Carbs", f"{m['c']:.0f}g")
            c4.metric("Grasas", f"{m['f']:.0f}g")
            
            if st.button("Generar Dieta con Gemini"):
                with st.spinner("Generando plan personalizado..."):
                    prompt = f"Actúa como nutricionista. Dieta de {m['cal']:.0f} kcal. Macros: P:{m['p']:.0f}g, C:{m['c']:.0f}g, F:{m['f']:.0f}g. Dieta: {profile.get('diet_type', 'Omnívora')}. Alergias: {profile.get('allergies', 'Ninguna')}. Formato: Tabla Markdown."
                    resp = gemini_model.generate_content(prompt)
                    st.markdown(resp.text)
    except Exception as e:
        st.error(f"Error en el módulo de nutrición: {e}")

elif selected == "Ajustes":
    st.header("Ajustes de Usuario")
    try:
        curr_res = supabase.table("profiles").select("*").eq("id", USER_ID).execute()
        curr = curr_res.data[0] if curr_res.data else {}
    except:
        curr = {}

    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        w_val = col1.number_input("Peso (kg)", 30.0, 200.0, float(curr.get('weight', 75)))
        h_val = col2.number_input("Altura (cm)", 100.0, 250.0, float(curr.get('height', 175)))
        a_val = col1.number_input("Edad", 15, 100, int(curr.get('age', 25)))
        g_val = col2.selectbox("Género", ["Masculino", "Femenino"], index=0 if curr.get('gender') == "Masculino" else 1)
        act_val = st.select_slider("Actividad", [1.2, 1.375, 1.55, 1.725], value=float(curr.get('activity_level', 1.2)))
        diet_val = st.text_input("Preferencia Dieta", curr.get('diet_type', 'Omnívora'))
        
        if st.form_submit_button("Guardar Perfil"):
            try:
                supabase.table("profiles").upsert({
                    "id": USER_ID, "weight": w_val, "height": h_val, "age": a_val, 
                    "gender": g_val, "activity_level": act_val, "diet_type": diet_val
                }).execute()
                st.success("✅ Perfil actualizado en la nube.")
            except Exception as e:
                st.error(f"Error al guardar perfil: {e}")
