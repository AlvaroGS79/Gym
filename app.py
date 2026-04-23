import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from streamlit_option_menu import option_menu
from datetime import datetime

# --- 1. CONFIGURACIÓN ---
S_URL = "https://hffrbskyjwmkurwwdzcj.supabase.co"
S_KEY = "sb_publishable_H8uLitl0KwczBr2owTbTTA_uPCFoXGd"

st.set_page_config(page_title="Fitness OS Pro", layout="wide", page_icon="💪")

@st.cache_resource
def init_connections():
    return create_client(S_URL, S_KEY)

supabase = init_connections()

# --- 2. LÓGICA DE NUTRICIÓN ---
def get_nutrition_logic(w, h, a, g, act, goal):
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "Masculino" else -161)
    tdee = bmr * act
    adj = {"Perder Grasa": -500, "Mantener": 0, "Ganar Músculo": 400}
    target_cal = tdee + adj.get(goal, 0)
    prot = w * 2.0
    fat = w * 0.8
    carbs = (target_cal - (prot * 4) - (fat * 9)) / 4
    return {"cal": round(target_cal), "p": round(prot), "f": round(fat), "c": round(carbs)}

def generate_diet_template(macros, diet_type):
    menus = {
        "Omnívora": {
            "Desayuno": "Bowl de 80g de Avena con 1 plátano y 4 nueces.",
            "Almuerzo": "200g de Pechuga de pollo con 100g de Arroz y Brócoli.",
            "Merienda": "1 Yogur griego natural con una manzana.",
            "Cena": "150g de Salmón a la plancha con ensalada de tomate."
        },
        "Vegana": {
            "Desayuno": "2 Tostadas integrales con medio aguacate y chía.",
            "Almuerzo": "200g de Tofu firme con 100g de Quinoa y verduras.",
            "Merienda": "Puñado de 30g de almendras y una pera.",
            "Cena": "Hamburguesa de seitán con puré de patata y espárragos."
        }
    }
    op = menus.get(diet_type, menus["Omnívora"])
    return f"""
    ### 📅 Menú del Día (Decidido)
    *Macros objetivo: {macros['cal']} kcal | P: {macros['p']}g | C: {macros['c']}g | G: {macros['f']}g*
    
    ---
    ☕ **Desayuno:** {op['Desayuno']}
    
    🍽️ **Almuerzo:** {op['Almuerzo']}
    
    🍎 **Merienda:** {op['Merienda']}
    
    🌙 **Cena:** {op['Cena']}
    
    ---
    *Nota: Bebe al menos 2L de agua al día.*
    """

# --- 3. NAVEGACIÓN ---
with st.sidebar:
    st.title("🔐 Acceso")
    user_input = st.text_input("Usuario", placeholder="Tu nombre").strip().lower()
    if not user_input:
        st.warning("Introduce tu usuario.")
        st.stop()
    
    selected = option_menu("Menú", ["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"], 
                          icons=['house', 'activity', 'egg', 'gear'], default_index=0)

# --- 4. VISTAS (IDENTACIÓN CRÍTICA AQUÍ) ---
if selected == "Dashboard":
    st.header(f"Progreso de {user_input.capitalize()}")
    try:
        res = supabase.table("workouts").select("*").eq("username", user_input).order("date").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            fig = px.line(df, x="date", y="weight_kg", color="exercise", markers=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos. Registra algo en Entrenamientos.")
    except Exception as e:
        st.error(f"Error: {e}")

elif selected == "Entrenamientos":
    st.header("Registrar Sesión")
    with st.form("workout_form", clear_on_submit=True):
        ex = st.text_input("Ejercicio")
        c1, c2, c3 = st.columns(3)
        s = c1.number_input("Series", 1, 10, 3)
        r = c2.number_input("Reps", 1, 50, 10)
        w = c3.number_input("Peso (kg)", 0.0, 500.0, 50.0)
        if st.form_submit_button("Guardar"):
            supabase.table("workouts").insert({"username": user_input, "exercise": ex, "sets": s, "reps": r, "weight_kg": w}).execute()
            st.toast("¡Guardado!", icon="🏋️")

elif selected == "Nutrición":
    st.header("Tu Plan Nutricional")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    if not res.data:
        st.warning("Configura tus Ajustes primero.")
    else:
        profile = res.data[0]
        goal = st.selectbox("Objetivo", ["Perder Grasa", "Mantener", "Ganar Músculo"])
        m = get_nutrition_logic(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], goal)
        st.markdown(generate_diet_template(m, profile.get('diet_type', 'Omnívora')))

elif selected == "Ajustes":
    st.header("Ajustes de Perfil")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    curr = res.data[0] if res.data else {}
    with st.form("settings"):
        col1, col2 = st.columns(2)
        weight = col1.number_input("Peso (kg)", 30.0, 200.0, float(curr.get('weight', 70.0)))
        height = col2.number_input("Altura (cm)", 100.0, 250.0, float(curr.get('height', 170.0)))
        age = col1.number_input("Edad", 15, 90, int(curr.get('age', 25)))
        gender = col2.selectbox("Género", ["Masculino", "Femenino"], index=0 if curr.get('gender')=="Masculino" else 1)
        act = st.selectbox("Actividad", [1.2, 1.375, 1.55, 1.725], format_func=lambda x: {1.2:"Sedentario", 1.375:"Ligero", 1.55:"Moderado", 1.725:"Intenso"}[x])
        diet_t = st.selectbox("Dieta", ["Omnívora", "Vegana"])
        if st.form_submit_button("Guardar Perfil"):
            supabase.table("profiles").upsert({"username": user_input, "weight": weight, "height": height, "age": age, "gender": gender, "activity_level": act, "diet_type": diet_t}).execute()
            st.success("¡Perfil guardado!")
