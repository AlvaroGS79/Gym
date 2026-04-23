import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from supabase import create_client, Client
from streamlit_option_menu import option_menu
from datetime import datetime
from typing import Dict, Any

# --- CONFIGURACIÓN DE CREDENCIALES ---
S_URL = "https://hffrbskyjwmkurwwdzcj.supabase.co"
S_KEY = "sb_publishable_H8uLitl0KwczBr2owTbTTA_uPCFoXGd"
G_KEY = "AIzaSyBm_tP0SlIJ86ERXcxMPZSvA7pEnfiPrqw"

st.set_page_config(page_title="Fitness OS Pro", layout="wide", page_icon="⚡")

# --- INICIALIZACIÓN ---
@st.cache_resource
def init_connections():
    sb = create_client(S_URL, S_KEY)
    genai.configure(api_key=G_KEY)
    
    # Intentamos cargar el modelo más compatible
    # gemini-1.5-flash es el estándar actual para el tier gratuito
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Prueba rápida de consistencia
        model.get_model_info
    except:
        model = genai.GenerativeModel('gemini-pro')
        
    return sb, model

supabase, gemini_model = init_connections()

# --- LÓGICA DE LOGIN ---
with st.sidebar:
    st.title("🔐 Acceso")
    user_input = st.text_input("Introduce tu Usuario", placeholder="Ej: JuanFit").strip().lower()
    
    if not user_input:
        st.warning("Escribe tu nombre de usuario para empezar.")
        st.stop()
    
    st.success(f"Sesión: {user_input}")
    st.divider()
    
    selected = option_menu(
        menu_title="Navegación",
        options=["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"],
        icons=['house', 'activity', 'egg', 'gear'],
        menu_icon="cast",
        default_index=0,
    )

# --- FUNCIONES DE CÁLCULO ---
def calculate_macros(w, h, a, g, act, goal):
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "Masculino" else -161)
    tdee = bmr * act
    adj = {"Perder Grasa": -500, "Mantener": 0, "Ganar Músculo": 400}
    target = tdee + adj.get(goal, 0)
    return {"cal": target, "p": w * 2.0, "f": w * 0.8, "c": (target - (w*2*4) - (w*0.8*9))/4}

# --- VISTAS ---

if selected == "Dashboard":
    st.header(f"Progreso de {user_input.capitalize()}")
    try:
        res = supabase.table("workouts").select("*").eq("username", user_input).order("date").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            fig = px.line(df, x="date", y="weight_kg", color="exercise", markers=True, template="plotly_dark", title="Evolución de Cargas")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aún no tienes registros. ¡Ve a la pestaña de Entrenamientos!")
    except Exception as e:
        st.error(f"Error al cargar Dashboard: {e}")

elif selected == "Entrenamientos":
    st.header("Registrar Nueva Sesión")
    check_profile = supabase.table("profiles").select("username").eq("username", user_input).execute()
    if not check_profile.data:
        st.error("❌ Primero debes crear tu perfil en la pestaña 'Ajustes'.")
    else:
        with st.form("workout_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            ex = c1.text_input("Ejercicio")
            dt = c2.date_input("Fecha", datetime.now())
            s, r, w = st.columns(3)
            sets = s.number_input("Series", 1, 10, 3)
            reps = r.number_input("Reps", 1, 50, 10)
            weight = w.number_input("Peso (kg)", 0.0, 500.0, 60.0)
            
            if st.form_submit_button("Guardar Entrenamiento"):
                supabase.table("workouts").insert({
                    "username": user_input, "exercise": ex, "date": str(dt), 
                    "sets": sets, "reps": reps, "weight_kg": weight
                }).execute()
                st.toast("¡Carga registrada!", icon="💪")

elif selected == "Nutrición":
    st.header("Tu Plan Dietético Personal")
    try:
        res = supabase.table("profiles").select("*").eq("username", user_input).execute()
        if not res.data:
            st.warning("⚠️ No hay datos de perfil. Configúralos en 'Ajustes'.")
        else:
            profile = res.data[0]
            goal = st.selectbox("Objetivo", ["Perder Grasa", "Mantener", "Ganar Músculo"])
            m = calculate_macros(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], goal)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Calorías", f"{m['cal']:.0f}")
            c2.metric("Proteína", f"{m['p']:.0f}g")
            c3.metric("Carbs", f"{m['c']:.0f}g")
            c4.metric("Grasas", f"{m['f']:.0f}g")
            
            if st.button("Generar Dieta con IA"):
                with st.spinner("Analizando requerimientos con Gemini..."):
                    prompt = f"Actúa como nutricionista. Dieta de {m['cal']:.0f} kcal. Macros: P:{m['p']:.0f}g, C:{m['c']:.0f}g, F:{m['f']:.0f}g. Tipo: {profile['diet_type']}. Formato: Tabla Markdown."
                    try:
                        resp = gemini_model.generate_content(prompt)
                        st.markdown(resp.text)
                    except Exception as ai_err:
                        st.error(f"Error de acceso al modelo: {ai_err}")
                        st.info("Revisando disponibilidad de modelos alternativos...")
                        # Intento de emergencia con modelo alternativo en caliente
                        emergency_model = genai.GenerativeModel('gemini-1.5-flash')
                        resp = emergency_model.generate_content(prompt)
                        st.markdown(resp.text)

    except Exception as e:
        st.error(f"Error en Nutrición: {e}")

elif selected == "Ajustes":
    st.header(f"Perfil de {user_input.capitalize()}")
    try:
        res = supabase.table("profiles").select("*").eq("username", user_input).execute()
        curr = res.data[0] if res.data else {}
    except:
        curr = {}

    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        w = col1.number_input("Peso (kg)", 30.0, 200.0, float(curr.get('weight', 75)))
        h = col2.number_input("Altura (cm)", 100.0, 250.0, float(curr.get('height', 175)))
        a = col1.number_input("Edad", 15, 100, int(curr.get('age', 25)))
        g = col2.selectbox("Género", ["Masculino", "Femenino"], index=0 if curr.get('gender')=="Masculino" else 1)
        
        act = st.select_slider(
            "Nivel de Actividad Diaria",
            options=[1.2, 1.375, 1.55, 1.725],
            value=float(curr.get('activity_level', 1.2)),
            format_func=lambda x: {1.2: "Sedentario", 1.375: "Ligero", 1.55: "Moderado", 1.725: "Intenso"}[x]
        )
        
        diet = st.text_input("Tipo de Dieta (ej: Vegana, Keto)", curr.get('diet_type', 'Omnívora'))
        
        if st.form_submit_button("Guardar Perfil"):
            supabase.table("profiles").upsert({
                "username": user_input, "weight": w, "height": h, "age": a, 
                "gender": g, "activity_level": act, "diet_type": diet
            }).execute()
            st.success("¡Perfil actualizado con éxito!")
