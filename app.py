import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from supabase import create_client, Client
from streamlit_option_menu import option_menu
from datetime import datetime

# --- CREDENCIALES ---
S_URL = "https://hffrbskyjwmkurwwdzcj.supabase.co"
S_KEY = "sb_publishable_H8uLitl0KwczBr2owTbTTA_uPCFoXGd"
G_KEY = "AIzaSyDzTgUsV45HNTDeqvBGzN8nbuax6dO35d4"

st.set_page_config(page_title="Fitness OS Pro", layout="wide", page_icon="⚡")

# --- INICIALIZACIÓN ---
@st.cache_resource
def init_connections():
    # Supabase
    sb = create_client(S_URL, S_KEY)
    # Gemini: Configuración base
    genai.configure(api_key=G_KEY)
    return sb

supabase = init_connections()

# --- LÓGICA DE LOGIN ---
with st.sidebar:
    st.title("🔐 Acceso")
    user_input = st.text_input("Usuario", placeholder="Tu nombre").strip().lower()
    
    if not user_input:
        st.warning("Ingresa tu usuario.")
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
            fig = px.line(df, x="date", y="weight_kg", color="exercise", markers=True, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin registros aún.")
    except Exception as e:
        st.error(f"Error: {e}")

elif selected == "Entrenamientos":
    st.header("Registrar Sesión")
    if not supabase.table("profiles").select("username").eq("username", user_input).execute().data:
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

elif selected == "Nutrición":
    st.header("Tu Plan Nutricional")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    if not res.data:
        st.warning("⚠️ Configura tu perfil en 'Ajustes'.")
    else:
        profile = res.data[0]
        goal = st.selectbox("Objetivo", ["Perder Grasa", "Mantener", "Ganar Músculo"])
        m = calculate_macros(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], goal)
        
        st.metric("Calorías Objetivo", f"{m['cal']:.0f} kcal")
        
        if st.button("Generar Dieta con IA"):
            with st.spinner("Llamando a Gemini..."):
                try:
                    # Forzamos el modelo gemini-pro que es el más estable ante errores 404
                    model = genai.GenerativeModel('gemini-pro')
                    prompt = (f"Genera una dieta de {m['cal']:.0f} calorías para un usuario {profile['gender']}. "
                             f"Macros: P:{m['p']:.0f}g, C:{m['c']:.0f}g, F:{m['f']:.0f}g. "
                             f"Formato: Tabla Markdown.")
                    resp = model.generate_content(prompt)
                    st.markdown(resp.text)
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.info("Intenta generar una nueva API Key en Google AI Studio.")

elif selected == "Ajustes":
    st.header(f"Perfil de {user_input.capitalize()}")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    curr = res.data[0] if res.data else {}

    with st.form("settings"):
        col1, col2 = st.columns(2)
        w = col1.number_input("Peso (kg)", 30.0, 200.0, float(curr.get('weight', 75)))
        h = col2.number_input("Altura (cm)", 100.0, 250.0, float(curr.get('height', 175)))
        a = col1.number_input("Edad", 15, 100, int(curr.get('age', 25)))
        g = col2.selectbox("Género", ["Masculino", "Femenino"], index=0 if curr.get('gender')=="Masculino" else 1)
        act = st.selectbox("Actividad", [1.2, 1.375, 1.55, 1.725], index=0)
        
        if st.form_submit_button("Guardar Perfil"):
            supabase.table("profiles").upsert({
                "username": user_input, "weight": w, "height": h, "age": a, 
                "gender": g, "activity_level": act
            }).execute()
            st.success("¡Perfil actualizado!")
