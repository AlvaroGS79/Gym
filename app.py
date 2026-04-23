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
    prot, fat = w * 2.0, w * 0.8
    carbs = (target_cal - (prot * 4) - (fat * 9)) / 4
    return {"cal": round(target_cal), "p": round(prot), "f": round(fat), "c": round(carbs)}

def generate_diet_view(macros, diet_type):
    # Gramajes base calculados
    cant_avena = round((macros['c'] * 0.25) / 0.6) 
    cant_arroz = round((macros['c'] * 0.45) / 0.28) 
    cant_pollo = round((macros['p'] * 0.45) / 0.23) 
    cant_proteina_cena = round((macros['p'] * 0.35) / 0.20)

    # --- MENÚ DEL DÍA ---
    st.subheader("📅 Tu Menú Sugerido (Hoy)")
    c1, c2 = st.columns(2)
    
    with c1:
        st.info(f"**Desayuno:** {cant_avena}g Avena + 1 fruta")
        st.info(f"**Almuerzo:** {cant_pollo}g Pollo + {cant_arroz}g Arroz + Verdura")
    with c2:
        st.info(f"**Merienda:** 1-2 Yogures griegos + nueces")
        st.info(f"**Cena:** {cant_proteina_cena}g Pescado/Ternera + Ensalada")

    # --- TABLA DE ALTERNATIVAS (EL CORAZÓN DE LA VARIEDAD) ---
    st.divider()
    st.subheader("🔄 Tabla de Intercambios (Varía tu dieta)")
    st.write("Si no quieres comer lo de arriba, sustituye por estas cantidades equivalentes:")

    tab1, tab2, tab3 = st.tabs(["🥩 Proteínas", "🍚 Carbohidratos", "🥑 Grasas"])

    with tab1:
        st.write(f"Para sustituir tus **{cant_pollo}g de Pollo**, puedes elegir:")
        st.table(pd.DataFrame({
            "Alimento": ["Pavo", "Ternera magra", "Atún natural", "Lomo de cerdo", "Claras de huevo"],
            "Cantidad Equivalente": [f"{cant_pollo}g", f"{round(cant_pollo*0.9)}g", f"{round(cant_pollo*0.8)}g", f"{round(cant_pollo*0.95)}g", f"{round(cant_pollo*1.5)}g"]
        }))

    with tab2:
        st.write(f"Para sustituir tus **{cant_arroz}g de Arroz**, puedes elegir:")
        st.table(pd.DataFrame({
            "Alimento": ["Pasta integral", "Patata cocida", "Quinoa", "Boniato", "Legumbres"],
            "Cantidad Equivalente": [f"{round(cant_arroz*0.9)}g", f"{round(cant_arroz*3.5)}g", f"{round(cant_arroz*1.1)}g", f"{round(cant_arroz*3.0)}g", f"{round(cant_arroz*1.2)}g"]
        }))

    with tab3:
        st.write("Fuentes de grasa recomendadas (Raciones de 10-15g):")
        st.markdown("- **Aguacate:** 1/4 de pieza mediana\n- **Aceite de oliva:** 1 cucharada sopera\n- **Frutos secos:** 10-12 unidades")

# --- 3. NAVEGACIÓN ---
with st.sidebar:
    st.title("🔐 Acceso")
    user_input = st.text_input("Usuario", placeholder="Tu nombre").strip().lower()
    if not user_input:
        st.warning("Introduce tu usuario.")
        st.stop()
    selected = option_menu("Menú", ["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"], icons=['house', 'activity', 'egg', 'gear'], default_index=0)

# --- 4. VISTAS ---
if selected == "Dashboard":
    st.header(f"Progreso de {user_input.capitalize()}")
    try:
        res = supabase.table("workouts").select("*").eq("username", user_input).order("date").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            fig = px.line(df, x="date", y="weight_kg", color="exercise", markers=True, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Sin datos registrados.")
    except Exception as e: st.error(f"Error: {e}")

elif selected == "Entrenamientos":
    st.header("Registrar Sesión")
    with st.form("workout_form", clear_on_submit=True):
        ex = st.text_input("Ejercicio")
        c1, c2, c3 = st.columns(3)
        s, r, w = c1.number_input("Series", 1, 10, 3), c2.number_input("Reps", 1, 50, 10), c3.number_input("Peso (kg)", 0.0, 500.0, 50.0)
        if st.form_submit_button("Guardar"):
            supabase.table("workouts").insert({"username": user_input, "exercise": ex, "sets": s, "reps": r, "weight_kg": w}).execute()
            st.toast("¡Guardado!", icon="🏋️")

elif selected == "Nutrición":
    st.header("Plan Nutricional Inteligente")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    if not res.data:
        st.warning("Configura tu perfil en 'Ajustes'.")
    else:
        profile = res.data[0]
        goal = st.selectbox("Objetivo", ["Perder Grasa", "Mantener", "Ganar Músculo"])
        m = get_nutrition_logic(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], goal)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Calorías", f"{m['cal']} kcal")
        c2.metric("Proteína", f"{m['p']}g")
        c3.metric("Carbos", f"{m['c']}g")
        
        st.divider()
        generate_diet_view(m, profile.get('diet_type', 'Omnívora'))

elif selected == "Ajustes":
    st.header("Perfil")
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
