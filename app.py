import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from streamlit_option_menu import option_menu
from datetime import datetime

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
S_URL = "https://hffrbskyjwmkurwwdzcj.supabase.co"
S_KEY = "sb_publishable_H8uLitl0KwczBr2owTbTTA_uPCFoXGd"

st.set_page_config(page_title="Fitness OS Pro", layout="wide", page_icon="💪")

@st.cache_resource
def init_connections():
    return create_client(S_URL, S_KEY)

supabase = init_connections()

# --- 2. LÓGICA DE NUTRICIÓN Y MENÚS ---
def get_nutrition_logic(w, h, a, g, act, goal):
    # Fórmula Mifflin-St Jeor
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "Masculino" else -161)
    tdee = bmr * act
    
    # Ajuste por objetivo (Calorías)
    adj = {"Perder Grasa": -500, "Mantener": 0, "Ganar Músculo": 400}
    target_cal = tdee + adj.get(goal, 0)
    
    # Reparto de Macros
    prot = w * 2.0
    fat = w * 0.8
    carbs = (target_cal - (prot * 4) - (fat * 9)) / 4
    
    return {"cal": round(target_cal), "p": round(prot), "f": round(fat), "c": round(carbs)}

def generate_diet_template(macros, diet_type):
    # Cálculo dinámico de gramos según macros actuales
    # Avena seca: 60% carbs | Arroz cocido: 28% carbs | Pollo cocinado: 23% prot
    cant_avena = round((macros['c'] * 0.25) / 0.6) 
    cant_arroz = round((macros['c'] * 0.45) / 0.28) 
    cant_pollo = round((macros['p'] * 0.45) / 0.23) 
    cant_proteina_cena = round((macros['p'] * 0.35) / 0.20) 

    if diet_type == "Omnívora":
        menu = {
            "Desayuno": f"Bowl de {cant_avena}g de Avena con 1 plátano y 4 nueces.",
            "Almuerzo": f"{cant_pollo}g de Pechuga de pollo con {cant_arroz}g de Arroz cocido y Brócoli.",
            "Merienda": "1 Yogur griego natural con una pieza de fruta.",
            "Cena": f"{cant_proteina_cena}g de Pescado blanco o Salmón con ensalada mixta."
        }
    else: # Vegana
        menu = {
            "Desayuno": f"Bowl de {cant_avena}g de Avena con leche de soja y chía.",
            "Almuerzo": f"{cant_pollo}g de Tofu firme con {cant_arroz}g de Quinoa y verduras.",
            "Merienda": "30g de Almendras y una pera.",
            "Cena": f"{cant_proteina_cena}g de Seitán o Tempeh con puré de patata."
        }

    return f"""
    ### 📅 Menú Diario Ajustado
    *Cálculo para: **{macros['cal']} kcal*** *Reparto: **P:{macros['p']}g | C:{macros['c']}g | G:{macros['f']}g***
    
    ---
    ☕ **Desayuno:** {menu['Desayuno']}
    
    🍽️ **Almuerzo:** {menu['Almuerzo']}
    
    🍎 **Merienda:** {menu['Merienda']}
    
    🌙 **Cena:** {menu['Cena']}
    
    ---
    *💡 Nota: Los gramos de arroz son para peso ya COCINADO. El pollo también.*
    """

# --- 3. NAVEGACIÓN LATERAL ---
with st.sidebar:
    st.title("🔐 Acceso")
    user_input = st.text_input("Usuario", placeholder="Ej: Juan").strip().lower()
    if not user_input:
        st.warning("Escribe tu nombre para empezar.")
        st.stop()
    
    selected = option_menu(
        menu_title="Menú",
        options=["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"],
        icons=['house', 'activity', 'egg', 'gear'],
        default_index=0
    )

# --- 4. VISTAS ---

if selected == "Dashboard":
    st.header(f"Progreso de {user_input.capitalize()}")
    try:
        res = supabase.table("workouts").select("*").eq("username", user_input).order("date").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            fig = px.line(df, x="date", y="weight_kg", color="exercise", markers=True, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aún no tienes datos. ¡Registra tus pesos en la pestaña de Entrenamientos!")
    except Exception as e:
        st.error(f"Error de base de datos: {e}")

elif selected == "Entrenamientos":
    st.header("Registrar Nueva Sesión")
    with st.form("workout_form", clear_on_submit=True):
        ex = st.text_input("Ejercicio")
        c1, c2, c3 = st.columns(3)
        s = c1.number_input("Series", 1, 10, 3)
        r = c2.number_input("Repeticiones", 1, 50, 10)
        w = c3.number_input("Peso (kg)", 0.0, 500.0, 50.0)
        if st.form_submit_button("Guardar Entrenamiento"):
            supabase.table("workouts").insert({"username": user_input, "exercise": ex, "sets": s, "reps": r, "weight_kg": w}).execute()
            st.toast("¡Registro guardado!", icon="🏋️")

elif selected == "Nutrición":
    st.header("Tu Plan Nutricional")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    if not res.data:
        st.warning("⚠️ Debes configurar tus datos en la pestaña 'Ajustes' primero.")
    else:
        profile = res.data[0]
        goal = st.selectbox("¿Cuál es tu objetivo hoy?", ["Perder Grasa", "Mantener", "Ganar Músculo"])
        
        # Calculamos macros y generamos menú
        m = get_nutrition_logic(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], goal)
        
        # Mostrar métricas clave
        col1, col2, col3 = st.columns(3)
        col1.metric("Calorías Totales", f"{m['cal']} kcal")
        col2.metric("Proteína Diaria", f"{m['p']}g")
        col3.metric("Carbohidratos", f"{m['c']}g")
        
        st.divider()
        st.markdown(generate_diet_template(m, profile.get('diet_type', 'Omnívora')))

elif selected == "Ajustes":
    st.header("Configuración de Perfil")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    curr = res.data[0] if res.data else {}
    
    with st.form("settings"):
        col1, col2 = st.columns(2)
        weight = col1.number_input("Peso actual (kg)", 30.0, 200.0, float(curr.get('weight', 75.0)))
        height = col2.number_input("Altura (cm)", 100.0, 250.0, float(curr.get('height', 175.0)))
        age = col1.number_input("Edad", 15, 95, int(curr.get('age', 25)))
        gender = col2.selectbox("Género", ["Masculino", "Femenino"], index=0 if curr.get('gender')=="Masculino" else 1)
        
        act = st.selectbox(
            "Nivel de Actividad",
            options=[1.2, 1.375, 1.55, 1.725],
            format_func=lambda x: {
                1.2: "Sedentario (Oficina / Poco ejercicio)",
                1.375: "Ligero (Entreno 1-2 días)",
                1.55: "Moderado (Entreno 3-5 días)",
                1.725: "Intenso (Entreno 6-7 días)"
            }[x]
        )
        
        diet_t = st.selectbox("Preferencia de Dieta", ["Omnívora", "Vegana"])
        
        if st.form_submit_button("Guardar y Actualizar Perfil"):
            supabase.table("profiles").upsert({
                "username": user_input, "weight": weight, "height": height, 
                "age": age, "gender": gender, "activity_level": act, "diet_type": diet_t
            }).execute()
            st.success("✅ Perfil guardado. Ya puedes consultar tu menú en 'Nutrición'.")
