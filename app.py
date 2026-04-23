import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from streamlit_option_menu import option_menu
from datetime import datetime

# --- CONFIGURACIÓN DE CREDENCIALES ---
S_URL = "https://hffrbskyjwmkurwwdzcj.supabase.co"
S_KEY = "sb_publishable_H8uLitl0KwczBr2owTbTTA_uPCFoXGd"

st.set_page_config(page_title="Fitness OS Pro - Edición Estable", layout="wide", page_icon="💪")

# --- INICIALIZACIÓN ---
@st.cache_resource
def init_connections():
    return create_client(S_URL, S_KEY)

supabase = init_connections()

# --- LÓGICA DE LOGIN ---
with st.sidebar:
    st.title("🔐 Acceso")
    user_input = st.text_input("Usuario", placeholder="Tu nombre").strip().lower()
    
    if not user_input:
        st.warning("Escribe tu nombre para entrar.")
        st.stop()
    
    selected = option_menu(
        menu_title="Fitness Menu",
        options=["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"],
        icons=['house', 'activity', 'egg', 'gear'],
        default_index=0,
    )

# --- MOTOR DE NUTRICIÓN (Lógica Pura) ---
def get_nutrition_logic(w, h, a, g, act, goal):
    # TMB (Mifflin-St Jeor)
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "Masculino" else -161)
    tdee = bmr * act
    
    # Ajuste por objetivo
    adj = {"Perder Grasa": -500, "Mantener": 0, "Ganar Músculo": 400}
    target_cal = tdee + adj.get(goal, 0)
    
    # Macros: Proteína (2g/kg), Grasa (0.8g/kg), Resto Carbos
    prot = w * 2.0
    fat = w * 0.8
    carbs = (target_cal - (prot * 4) - (fat * 9)) / 4
    
    return {
        "cal": round(target_cal),
        "p": round(prot),
        "f": round(fat),
        "c": round(carbs)
    }

def generate_diet_template(macros, diet_type):
    # Diccionario de alimentos según tipo de dieta
    food_db = {
        "Omnívora": {
            "P": "Pollo, Ternera, Huevos, Salmón",
            "C": "Arroz, Avena, Patata, Fruta",
            "F": "Aguacate, Frutos secos, Aceite de Oliva"
        },
        "Vegana": {
            "P": "Tofu, Seitan, Lentejas, Tempeh",
            "C": "Quinoa, Pasta Integral, Legumbres",
            "F": "Semillas de Chía, Nueces, Tahini"
        }
    }
    db = food_db.get(diet_type, food_db["Omnívora"])
    
    template = f"""
    ### 🥗 Tu Plan Dietético Sugerido
    Basado en tus macros: **{macros['cal']} kcal** (P: {macros['p']}g | C: {macros['c']}g | G: {macros['f']}g)

    | Comida | Sugerencia de Menú | Fuentes Principales |
    | :--- | :--- | :--- |
    | **Desayuno** | Avena con frutas y frutos secos | {db['C']} y {db['F']} |
    | **Almuerzo** | Proteína a la plancha con arroz y verduras | {db['P']} y {db['C']} |
    | **Merienda** | Batido o yogur con semillas | {db['P']} y {db['F']} |
    | **Cena** | Ensalada completa con proteína ligera | {db['P']} y {db['F']} |
    
    *Nota: Las cantidades deben pesarse para ajustarse a tus {macros['cal']} kcal.*
    """
    return template

# --- VISTAS ---
if selected == "Dashboard":
    st.header(f"Progreso de {user_input.capitalize()}")
    try:
        res = supabase.table("workouts").select("*").eq("username", user_input).order("date").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            fig = px.line(df, x="date", y="weight_kg", color="exercise", markers=True, title="Fuerza en el tiempo")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos todavía. Registra tus pesos en la pestaña de Entrenamientos.")
    except Exception as e:
        st.error(f"Error de base de datos: {e}")

elif selected == "Entrenamientos":
    st.header("Registrar Sesión")
    res_prof = supabase.table("profiles").select("username").eq("username", user_input).execute()
    if not res_prof.data:
        st.error("⚠️ Crea tu perfil en 'Ajustes' primero.")
    else:
        with st.form("workout_form", clear_on_submit=True):
            ex = st.text_input("Nombre del Ejercicio")
            c1, c2, c3 = st.columns(3)
            s = c1.number_input("Series", 1, 10, 3)
            r = c2.number_input("Reps", 1, 50, 10)
            w = c3.number_input("Peso (kg)", 0.0, 500.0, 50.0)
            if st.form_submit_button("Guardar"):
                supabase.table("workouts").insert({"username": user_input, "exercise": ex, "sets": s, "reps": r, "weight_kg": w}).execute()
                st.toast("¡Entrenamiento guardado!", icon="🏋️")

elif selected == "Nutrición":
    st.header("Cálculo Nutricional")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    if not res.data:
        st.warning("Configura tus datos en 'Ajustes' para ver tus macros.")
    else:
        profile = res.data[0]
        goal = st.selectbox("Objetivo", ["Perder Grasa", "Mantener", "Ganar Músculo"])
        m = get_nutrition_logic(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], goal)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Calorías", f"{m['cal']}")
        col2.metric("Proteína", f"{m['p']}g")
        col3.metric("Carbos", f"{m['c']}g")
        col4.metric("Grasas", f"{m['f']}g")
        
        st.divider()
        st.markdown(generate_diet_template(m, profile.get('diet_type', 'Omnívora')))

elif selected == "Ajustes":
    st.header("Tu Perfil")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    curr = res.data[0] if res.data else {}
    
    with st.form("settings"):
        col1, col2 = st.columns(2)
        weight = col1.number_input("Peso (kg)", 30.0, 200.0, float(curr.get('weight', 70.0)))
        height = col2.number_input("Altura (cm)", 100.0, 250.0, float(curr.get('height', 170.0)))
        age = col1.number_input("Edad", 15, 90, int(curr.get('age', 25)))
        gender = col2.selectbox("Género", ["Masculino", "Femenino"], index=0 if curr.get('gender')=="Masculino" else 1)
        act = st.selectbox("Actividad", [1.2, 1.375, 1.55, 1.725], 
                          format_func=lambda x: {1.2:"Sedentario", 1.375:"Ligero", 1.55:"Moderado", 1.725:"Intenso"}[x])
        diet_t = st.selectbox("Tipo de Dieta", ["Omnívora", "Vegana"])
        
        if st.form_submit_button("Guardar Perfil"):
            supabase.table("profiles").upsert({
                "username": user_input, "weight": weight, "height": height, 
                "age": age, "gender": gender, "activity_level": act, "diet_type": diet_t
            }).execute()
            st.success("¡Perfil guardado correctamente!")
