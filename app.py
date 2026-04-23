import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURACIÓN Y CONEXIÓN ---
S_URL = "https://hffrbskyjwmkurwwdzcj.supabase.co"
S_KEY = "sb_publishable_H8uLitl0KwczBr2owTbTTA_uPCFoXGd"

st.set_page_config(page_title="Fitness OS Elite", layout="wide", page_icon="⚡")

@st.cache_resource
def init_connections():
    return create_client(S_URL, S_KEY)

supabase = init_connections()

# --- 2. MOTOR DE NUTRICIÓN ---
def get_nutrition_logic(w, h, a, g, act, goal):
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "Masculino" else -161)
    tdee = bmr * act
    adj = {"Perder Grasa": -500, "Mantener": 0, "Ganar Músculo": 450}
    target_cal = tdee + adj.get(goal, 0)
    
    prot = w * 2.1 
    fat = w * 0.9  
    carbs = (target_cal - (prot * 4) - (fat * 9)) / 4
    return {"cal": round(target_cal), "p": round(prot), "f": round(fat), "c": round(carbs), "agua": round(w * 0.035, 1)}

def generate_professional_view(m, diet_type, goal):
    c_des, p_des = round((m['c']*0.20)/0.6), round((m['p']*0.20)/0.12)
    c_alm, p_alm = round((m['c']*0.45)/0.28), round((m['p']*0.35)/0.23)
    c_mer, p_mer = round((m['c']*0.15)/0.20), round((m['p']*0.15)/0.15)
    c_cen, p_cen = round((m['c']*0.20)/0.17), round((m['p']*0.30)/0.20)

    st.subheader("📋 Plan Nutricional de Alto Rendimiento")
    tab_menu, tab_suples, tab_compra = st.tabs(["🍽️ Menú Diario", "💊 Suplementación", "🛒 Lista de Compra"])

    with tab_menu:
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("### 🌅 Mañana")
                st.write(f"**Desayuno:** {c_des}g Avena + 1 fruta + {p_des}g Claras o Yogur.")
                st.write(f"**Almuerzo:** {p_alm}g Pollo/Pavo + {c_alm}g Arroz + 150g Verdura.")
        with c2:
            with st.container(border=True):
                st.markdown("### 🌙 Tarde/Noche")
                st.write(f"**Merienda:** {c_mer}g Pan integral + {p_mer}g Atún/Pavo.")
                st.write(f"**Cena:** {p_cen}g Pescado/Ternera + {c_cen}g Patata + Ensalada.")
        st.info(f"💧 **Hidratación:** Beber {m['agua']} Litros de agua al día.")

    with tab_suples:
        st.markdown("### 🧬 Suplementación Recomendada")
        s1, s2, s3 = st.columns(3)
        with s1:
            st.success("**Creatina**")
            st.write("5g diarios. Mejora fuerza y potencia muscular.")
        with s2:
            st.success("**Proteína Whey**")
            st.write("1 scoop si te falta proteína sólida en el día.")
        with s3:
            st.warning("**Omega 3 / Cafeína**")
            st.write("Omega 3 para inflamación; Cafeína para enfoque en el gym.")

    with tab_compra:
        st.table(pd.DataFrame({
            "Categoría": ["Proteína", "Carbos", "Grasas"],
            "Alimentos": ["Pollo, Pescado, Huevos, Pavo", "Avena, Arroz, Patata, Pan Int.", "Aceite Oliva, Nueces, Aguacate"]
        }))

# --- 3. NAVEGACIÓN ---
with st.sidebar:
    st.title("⚡ Fitness OS Elite")
    u = st.text_input("Usuario").strip().lower()
    if not u: st.stop()
    sel = option_menu("Menú", ["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"], 
                      icons=['house', 'activity', 'egg', 'gear'], menu_icon="cast")

# --- 4. VISTAS ---
if sel == "Dashboard":
    st.header(f"📊 Análisis de Progreso: {u.capitalize()}")
    res = supabase.table("workouts").select("*").eq("username", u).order("date").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        df['date'] = pd.to_datetime(df['date'])
        # Cálculo de Volumen de Carga: Series * Reps * Peso
        df['Volumen Total (kg)'] = df['sets'] * df['reps'] * df['weight_kg']
        
        tab_indiv, tab_gral = st.tabs(["🎯 Ejercicio Individual", "🌍 Vista General"])
        
        with tab_indiv:
            ejercicio_sel = st.selectbox("Selecciona un ejercicio:", df['exercise'].unique())
            df_filtered = df[df['exercise'] == ejercicio_sel]
            
            fig_indiv = px.line(df_filtered, x="date", y="weight_kg", 
                                title=f"Evolución de Carga en {ejercicio_sel}",
                                markers=True, text="reps",
                                labels={"weight_kg": "Peso (kg)", "date": "Fecha"},
                                template="plotly_dark", color_discrete_sequence=['#00CC96'])
            
            fig_indiv.update_traces(textposition="top center")
            st.plotly_chart(fig_indiv, use_container_width=True)
            st.caption("💡 Los números sobre los puntos indican las repeticiones logradas.")

        with tab_gral:
            st.subheader("Volumen de Trabajo Total (Sobrecarga Progresiva)")
            fig_gral = px.area(df, x="date", y="Volumen Total (kg)", color="exercise",
                               title="Comparativa de Volumen por Ejercicio",
                               template="plotly_dark",
                               color_discrete_sequence=px.colors.qualitative.Bold)
            st.plotly_chart(fig_gral, use_container_width=True)
            st.write("💡 Si el área total crece hacia arriba, estás aumentando tu capacidad de trabajo.")
    else:
        st.info("No hay registros. Guarda tus sesiones en la pestaña de Entrenamientos.")

elif sel == "Entrenamientos":
    st.header("Log de Entrenamiento")
    with st.form("w_form", clear_on_submit=True):
        ex = st.text_input("Nombre del Ejercicio")
        c1, c2, c3 = st.columns(3)
        s, r, w = c1.number_input("Series", 1, 10, 3), c2.number_input("Reps", 1, 50, 10), c3.number_input("Peso (kg)", 0.0, 500.0, 50.0)
        if st.form_submit_button("Registrar Levantamiento"):
            supabase.table("workouts").insert({"username": u, "exercise": ex, "sets": s, "reps": r, "weight_kg": w}).execute()
            st.toast("¡Guardado!", icon="💪")

elif sel == "Nutrición":
    res = supabase.table("profiles").select("*").eq("username", u).execute()
    if not res.data: st.warning("Configura tu perfil en Ajustes.")
    else:
        p = res.data[0]
        goal = st.selectbox("Selecciona tu objetivo", ["Perder Grasa", "Mantener", "Ganar Músculo"])
        st.header(f"Plan de Alimentación: {goal}")
        
        m = get_nutrition_logic(p['weight'], p['height'], p['age'], p['gender'], p['activity_level'], goal)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔥 Calorías", f"{m['cal']}")
        c2.metric("🥩 Prot", f"{m['p']}g")
        c3.metric("🍚 Carbs", f"{m['c']}g")
        c4.metric("🥑 Grasa", f"{m['f']}g")
        
        generate_professional_view(m, p.get('diet_type', 'Omnívora'), goal)

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
            st.success("¡Datos guardados!")
