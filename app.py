import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from supabase import create_client, Client
from streamlit_option_menu import option_menu
from datetime import datetime

# --- CONFIGURACIÓN DE CREDENCIALES ---
# Verifica que no haya espacios en estas cadenas
S_URL = "https://hffrbskyjwmkurwwdzcj.supabase.co"
S_KEY = "sb_publishable_H8uLitl0KwczBr2owTbTTA_uPCFoXGd"
G_KEY = "AIzaSyBm_tP0SlIJ86ERXcxMPZSvA7pEnfiPrqw"

st.set_page_config(page_title="Fitness OS Pro", layout="wide", page_icon="⚡")

# --- INICIALIZACIÓN ---
@st.cache_resource
def init_connections():
    # Supabase
    sb = create_client(S_URL, S_KEY)
    
    # Gemini: Configuración directa sin listar modelos para evitar el error de permisos
    genai.configure(api_key=G_KEY)
    
    # Usamos el modelo más estándar. Si da error de permisos aquí, la Key está mal.
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    return sb, model

# Manejo de error de inicialización para que la app no muera al cargar
try:
    supabase, gemini_model = init_connections()
except Exception as e:
    st.error(f"❌ Error de permisos con Google AI Studio: {e}")
    st.info("Revisa si tu API Key es correcta o si tu región permite el uso de Gemini.")
    st.stop()

# --- LÓGICA DE LOGIN ---
with st.sidebar:
    st.title("🔐 Acceso")
    user_input = st.text_input("Usuario", placeholder="Tu nombre").strip().lower()
    
    if not user_input:
        st.warning("Ingresa tu usuario para continuar.")
        st.stop()
    
    selected = option_menu(
        menu_title="Navegación",
        options=["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"],
        icons=['house', 'activity', 'egg', 'gear'],
        default_index=0,
    )

# --- FUNCIONES ---
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
            fig = px.line(df, x="date", y="weight_kg", color="exercise", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos. Ve a 'Entrenamientos'.")
    except Exception as e:
        st.error(f"Error Supabase: {e}")

elif selected == "Entrenamientos":
    st.header("Registrar Sesión")
    try:
        profile_exists = supabase.table("profiles").select("username").eq("username", user_input).execute()
        if not profile_exists.data:
            st.error("Crea tu perfil en 'Ajustes' primero.")
        else:
            with st.form("workout_form", clear_on_submit=True):
                ex = st.text_input("Ejercicio")
                c1, c2, c3 = st.columns(3)
                sets = c1.number_input("Series", 1, 10, 3)
                reps = c2.number_input("Reps", 1, 50, 10)
                weight = c3.number_input("Carga (kg)", 0.0, 500.0, 60.0)
                if st.form_submit_button("Guardar"):
                    supabase.table("workouts").insert({"username": user_input, "exercise": ex, "sets": sets, "reps": reps, "weight_kg": weight}).execute()
                    st.toast("¡Guardado!", icon="💪")
    except Exception as e:
        st.error(f"Error: {e}")

elif selected == "Nutrición":
    st.header("Planificación IA")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    if not res.data:
        st.warning("Falta perfil en Ajustes.")
    else:
        profile = res.data[0]
        m = calculate_macros(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], "Mantener")
        st.write(f"Calorías: {m['cal']:.0f}")
        if st.button("Generar Dieta"):
            try:
                resp = gemini_model.generate_content("Crea una dieta de 2000 kcal en una tabla.")
                st.markdown(resp.text)
            except Exception as e:
                st.error(f"La API de Google denegó el acceso: {e}")

elif selected == "Ajustes":
    st.header("Perfil")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    curr = res.data[0] if res.data else {}
    with st.form("settings"):
        w = st.number_input("Peso (kg)", 30.0, 200.0, float(curr.get('weight', 75)))
        h = st.number_input("Altura (cm)", 100.0, 250.0, float(curr.get('height', 175)))
        a = st.number_input("Edad", 15, 100, int(curr.get('age', 25)))
        g = st.selectbox("Género", ["Masculino", "Femenino"])
        act = st.selectbox("Actividad", [1.2, 1.375, 1.55, 1.725])
        if st.form_submit_button("Guardar"):
            supabase.table("profiles").upsert({"username": user_input, "weight": w, "height": h, "age": a, "gender": g, "activity_level": act}).execute()
            st.success("¡Perfil guardado!")
