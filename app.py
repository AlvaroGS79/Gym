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

# --- 2. MOTOR DE NUTRICIÓN DINÁMICO ---
def get_nutrition_logic(w, h, a, g, act, goal):
    # Cálculo de Tasa Metabólica Basal (Mifflin-St Jeor)
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "Masculino" else -161)
    tdee = bmr * act
    
    # Ajuste por objetivo
    adj = {"Perder Grasa": -500, "Mantener": 0, "Ganar Músculo": 400}
    target_cal = tdee + adj.get(goal, 0)
    
    # Reparto de Macros: Proteína 2g/kg, Grasa 0.8g/kg, Resto Carbohidratos
    prot = w * 2.0
    fat = w * 0.8
    carbs = (target_cal - (prot * 4) - (fat * 9)) / 4
    
    return {"cal": round(target_cal), "p": round(prot), "f": round(fat), "c": round(carbs)}

def generate_diet_template(macros, diet_type):
    # --- CÁLCULOS DE GRAMAJES POR COMIDA ---
    # Desayuno (25% Carbohidratos diarios)
    cant_avena = round((macros['c'] * 0.25) / 0.6) 
    
    # Almuerzo (45% Carbohidratos y 40% Proteína)
    cant_arroz = round((macros['c'] * 0.45) / 0.28) 
    cant_pollo = round((macros['p'] * 0.40) / 0.23) 
    
    # Merienda (Decisión de porción basada en volumen calórico)
    # Si necesitas más de 2200 kcal, doblamos la proteína en merienda
    porcion_merienda = 2 if macros['cal'] > 2200 else 1
    
    # Cena (30% Proteína y gestión de carbohidratos restantes)
    cant_proteina_cena = round((macros['p'] * 0.35) / 0.20) 
    # Solo añadimos patata en la cena si sobran muchos carbos (volumen/ganar músculo)
    cant_patata_cena = round((macros['c'] * 0.15) / 0.17) if macros['c'] > 200 else 0

    if diet_type == "Omnívora":
        menu = {
            "Desayuno": f"Bowl de {cant_avena}g de Avena con 1 plátano y un puñado de nueces.",
            "Almuerzo": f"{cant_pollo}g de Pechuga de pollo con {cant_arroz}g de Arroz cocido y brócoli al vapor.",
            "Merienda": f"{porcion_merienda} Yogur(es) griego(s) natural(es) con una pieza de fruta.",
            "Cena": f"{cant_proteina_cena}g de Salmón o Ternera magra con una gran ensalada mixta." + (f" Acompaña con {cant_patata_cena}g de patata cocida." if cant_patata_cena > 0 else "")
        }
    else: # Opción Vegana
        menu = {
            "Desayuno": f"Bowl de {cant_avena}g de Avena con leche de soja, chía y fruta.",
            "Almuerzo": f"{cant_pollo}g de Tofu firme salteado con {cant_arroz}g de Quinoa y verduras.",
            "Merienda": f"{30 * porcion_merienda}g de Frutos secos variados y una fruta.",
            "Cena": f"{cant_proteina_cena}g de Seitán o Tempeh a la plancha con espárragos." + (f" Acompaña con {cant_patata_cena}g de patata al horno." if cant_patata_cena > 0 else "")
        }

    return f"""
    ### 📅 Tu Menú Personalizado Ajustado
    *Basado en tu objetivo actual: **{macros['cal']} kcal*** *Reparto de macros: P: {macros['p']}g | C: {macros['c']}g | G: {macros['f']}g*
    
    ---
    ☕ **Desayuno:** {menu['Desayuno']}
    
    🍽️ **Almuerzo:** {menu['Almuerzo']}
    
    🍎 **Merienda:** {menu['Merienda']}
    
    🌙 **Cena:** {menu['Cena']}
    
    ---
    *💡 Consejo: Si ves que la cena no incluye patata, es porque tu objetivo requiere un control más estricto de carbohidratos nocturnos.*
    """

# --- 3. NAVEGACIÓN ---
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
            st.info("No hay datos. ¡Registra tus entrenamientos!")
    except Exception as e:
        st.error(f"Error de base de datos: {e}")

elif selected == "Entrenamientos":
    st.header("Registrar Nueva Sesión")
    with st.form("workout_form", clear_on_submit=True):
        ex = st.text_input("Nombre del Ejercicio")
        c1, c2, c3 = st.columns(3)
        s = c1.number_input("Series", 1, 10, 3)
        r = c2.number_input("Reps", 1, 50, 10)
        w = c3.number_input("Peso (kg)", 0.0, 500.0, 50.0)
        if st.form_submit_button("Guardar Entrenamiento"):
            supabase.table("workouts").insert({"username": user_input, "exercise": ex, "sets": s, "reps": r, "weight_kg": w}).execute()
            st.toast("¡Guardado!", icon="🏋️")

elif selected == "Nutrición":
    st.header("Planificación Dietética Real")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    if not res.data:
        st.warning("⚠️ Primero configura tu perfil en la pestaña de 'Ajustes'.")
    else:
        profile = res.data[0]
        goal = st.selectbox("Cambiar Objetivo", ["Perder Grasa", "Mantener", "Ganar Músculo"])
        
        # Calcular macros y renderizar menú
        m = get_nutrition_logic(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], goal)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Kcal Diarias", f"{m['cal']}")
        c2.metric("Proteína (P)", f"{m['p']}g")
        c3.metric("Carbos (C)", f"{m['c']}g")
        
        st.divider()
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
        act = st.selectbox("Actividad Diaria", [1.2, 1.375, 1.55, 1.725], 
                          format_func=lambda x: {1.2:"Sedentario", 1.375:"Ligero", 1.55:"Moderado", 1.725:"Intenso"}[x])
        diet_t = st.selectbox("Preferencia Alimenticia", ["Omnívora", "Vegana"])
        
        if st.form_submit_button("Guardar Perfil"):
            supabase.table("profiles").upsert({
                "username": user_input, "weight": weight, "height": height, 
                "age": age, "gender": gender, "activity_level": act, "diet_type": diet_t
            }).execute()
            st.success("✅ Perfil actualizado. ¡Tus macros han sido recalculados!")
