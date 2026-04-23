import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURACIÓN ---
S_URL = "https://hffrbskyjwmkurwwdzcj.supabase.co"
S_KEY = "sb_publishable_H8uLitl0KwczBr2owTbTTA_uPCFoXGd"

st.set_page_config(page_title="Fitness OS Pro", layout="wide", page_icon="💪")

@st.cache_resource
def init_connections():
    return create_client(S_URL, S_KEY)

supabase = init_connections()

# --- 2. MOTOR DE NUTRICIÓN AVANZADO ---
def get_nutrition_logic(w, h, a, g, act, goal):
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "Masculino" else -161)
    tdee = bmr * act
    adj = {"Perder Grasa": -500, "Mantener": 0, "Ganar Músculo": 400}
    target_cal = tdee + adj.get(goal, 0)
    
    # Macros: Proteína 2g/kg, Grasa 0.8g/kg, Resto Carbohidratos
    prot = w * 2.0
    fat = w * 0.8
    carbs = (target_cal - (prot * 4) - (fat * 9)) / 4
    return {"cal": round(target_cal), "p": round(prot), "f": round(fat), "c": round(carbs)}

def generate_diet_view(m, diet_type):
    # --- CÁLCULO DE GRAMAJES POR COMIDA ---
    # Desayuno (25% Carbos, 15% Proteína)
    c_des = round((m['c'] * 0.25) / 0.6) # Avena
    p_des = round((m['p'] * 0.15) / 0.10) # Yogur/Huevo
    
    # Almuerzo (40% Carbos, 35% Proteína)
    c_alm = round((m['c'] * 0.40) / 0.28) # Arroz
    p_alm = round((m['p'] * 0.35) / 0.23) # Pollo
    
    # Merienda (15% Carbos, 20% Proteína)
    c_mer = round((m['c'] * 0.15) / 0.20) # Pan/Fruta
    p_mer = round((m['p'] * 0.20) / 0.12) # Queso/Pavo
    
    # Cena (20% Carbos, 30% Proteína)
    c_cen = round((m['c'] * 0.20) / 0.17) # Patata
    p_cen = round((m['p'] * 0.30) / 0.20) # Pescado/Carne

    st.subheader("📅 Tu Menú Sugerido (Ajustado al Objetivo)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**☕ Desayuno:** {c_des}g Avena + 1 fruta + {p_des}g Yogur natural.")
        st.info(f"**🍽️ Almuerzo:** {p_alm}g Pollo/Pavo + {c_alm}g Arroz cocido + Verdura libre.")
    with col2:
        st.info(f"**🍎 Merienda:** {c_mer}g Pan integral con {p_mer}g de Pavo o Atún.")
        st.info(f"**🌙 Cena:** {p_cen}g Pescado o Ternera + {c_cen}g Patata cocida + Ensalada.")

    st.divider()
    st.subheader("🔄 Tabla de Variaciones Dinámica")
    st.write("¿No quieres lo de arriba? Usa estas cantidades para mantener tus macros:")

    t1, t2 = st.tabs(["🥩 Fuentes de Proteína", "🍚 Fuentes de Carbohidratos"])
    
    with t1:
        # La tabla se adapta a la cantidad de proteína del almuerzo
        st.table(pd.DataFrame({
            "Si no quieres Pollo...": ["Ternera Magra", "Pescado Blanco", "Salmón", "Huevos Enteros", "Seitán (Veg)"],
            "Come esta cantidad": [f"{round(p_alm*0.9)}g", f"{round(p_alm*1.1)}g", f"{round(p_alm*0.85)}g", f"{round(p_alm/30)} uds", f"{round(p_alm*1.2)}g"]
        }))
        
    with t2:
        # La tabla se adapta a la cantidad de arroz del almuerzo
        st.table(pd.DataFrame({
            "Si no quieres Arroz...": ["Pasta Cocida", "Patata Cocida", "Boniato", "Quinoa Cocida", "Pan Integral"],
            "Come esta cantidad": [f"{round(c_alm*0.9)}g", f"{round(c_alm*3.5)}g", f"{round(c_alm*3.0)}g", f"{round(c_alm*1.1)}g", f"{round(c_alm*0.5)}g"]
        }))

# --- 3. INTERFAZ ---
with st.sidebar:
    st.title("🔐 Acceso")
    u = st.text_input("Usuario").strip().lower()
    if not u: st.stop()
    sel = option_menu("Menú", ["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"], icons=['house', 'activity', 'egg', 'gear'])

if sel == "Dashboard":
    st.header(f"Progreso de {u.capitalize()}")
    res = supabase.table("workouts").select("*").eq("username", u).order("date").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.plotly_chart(px.line(df, x="date", y="weight_kg", color="exercise", markers=True, template="plotly_dark"), use_container_width=True)
    else: st.info("Registra datos en Entrenamientos.")

elif sel == "Entrenamientos":
    st.header("Registrar Sesión")
    with st.form("w_form", clear_on_submit=True):
        ex = st.text_input("Ejercicio")
        c1, c2, c3 = st.columns(3)
        s, r, w = c1.number_input("Series", 1, 10, 3), c2.number_input("Reps", 1, 50, 10), c3.number_input("Peso (kg)", 0.0, 500.0, 50.0)
        if st.form_submit_button("Guardar"):
            supabase.table("workouts").insert({"username": u, "exercise": ex, "sets": s, "reps": r, "weight_kg": w}).execute()
            st.toast("¡Guardado!", icon="🏋️")

elif sel == "Nutrición":
    st.header("Plan Nutricional 100% Dinámico")
    res = supabase.table("profiles").select("*").eq("username", u).execute()
    if not res.data: st.warning("Configura tu perfil en Ajustes.")
    else:
        p = res.data[0]
        goal = st.selectbox("Objetivo Actual", ["Perder Grasa", "Mantener", "Ganar Músculo"])
        m = get_nutrition_logic(p['weight'], p['height'], p['age'], p['gender'], p['activity_level'], goal)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Calorías", f"{m['cal']}")
        c2.metric("Proteína", f"{m['p']}g")
        c3.metric("Carbos", f"{m['c']}g")
        c4.metric("Grasas", f"{m['f']}g")
        
        st.divider()
        generate_diet_view(m, p.get('diet_type', 'Omnívora'))

elif sel == "Ajustes":
    st.header("Perfil")
    res = supabase.table("profiles").select("*").eq("username", u).execute()
    curr = res.data[0] if res.data else {}
    with st.form("s_form"):
        col1, col2 = st.columns(2)
        we = col1.number_input("Peso (kg)", 30.0, 200.0, float(curr.get('weight', 75.0)))
        he = col2.number_input("Altura (cm)", 100.0, 250.0, float(curr.get('height', 175.0)))
        ag = col1.number_input("Edad", 15, 90, int(curr.get('age', 25)))
        ge = col2.selectbox("Género", ["Masculino", "Femenino"], index=0 if curr.get('gender')=="Masculino" else 1)
        ac = st.selectbox("Actividad", [1.2, 1.375, 1.55, 1.725], format_func=lambda x: {1.2:"Sedentario", 1.375:"Ligero", 1.55:"Moderado", 1.725:"Intenso"}[x])
        dt = st.selectbox("Dieta", ["Omnívora", "Vegana"])
        if st.form_submit_button("Guardar Perfil"):
            supabase.table("profiles").upsert({"username": u, "weight": we, "height": he, "age": ag, "gender": ge, "activity_level": ac, "diet_type": dt}).execute()
            st.success("¡Perfil guardado!")
