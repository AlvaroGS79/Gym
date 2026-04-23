import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from streamlit_option_menu import option_menu

# --- 1. CONFIGURACIÓN ---
S_URL = "https://hffrbskyjwmkurwwdzcj.supabase.co"
S_KEY = "sb_publishable_H8uLitl0KwczBr2owTbTTA_uPCFoXGd"

st.set_page_config(page_title="Fitness OS Elite", layout="wide", page_icon="⚡")

@st.cache_resource
def init_connections():
    return create_client(S_URL, S_KEY)

supabase = init_connections()

# --- 2. MOTOR DE NUTRICIÓN AVANZADO ---
def get_nutrition_logic(w, h, a, g, act, goal):
    bmr = (10 * w) + (6.25 * h) - (5 * a) + (5 if g == "Masculino" else -161)
    tdee = bmr * act
    adj = {"Perder Grasa": -500, "Mantener": 0, "Ganar Músculo": 450}
    target_cal = tdee + adj.get(goal, 0)
    
    # Macros optimizados
    prot = w * 2.1 # Ligeramente superior para preservar masa
    fat = w * 0.9  # Optimización hormonal
    carbs = (target_cal - (prot * 4) - (fat * 9)) / 4
    return {"cal": round(target_cal), "p": round(prot), "f": round(fat), "c": round(carbs), "agua": round(w * 0.035, 1)}

def generate_professional_view(m, diet_type, goal):
    # --- CÁLCULO DE BLOQUES DINÁMICOS ---
    c_des, p_des = round((m['c']*0.20)/0.6), round((m['p']*0.20)/0.12)
    c_alm, p_alm = round((m['c']*0.45)/0.28), round((m['p']*0.35)/0.23)
    c_mer, p_mer = round((m['c']*0.15)/0.20), round((m['p']*0.15)/0.15)
    c_cen, p_cen = round((m['c']*0.20)/0.17), round((m['p']*0.30)/0.20)

    # --- DISEÑO DE INTERFAZ ---
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
        
        st.info(f"💧 **Objetivo Hidratación:** Beber {m['agua']} Litros de agua al día.")

    with tab_suples:
        st.markdown("### 🧬 Suplementación Recomendada (Evidencia Científica)")
        s1, s2, s3 = st.columns(3)
        with s1:
            st.success("**Creatina Monohidrato**")
            st.write("5g diarios. Mejora fuerza y recuperación.")
        with s2:
            st.success("**Proteína Whey**")
            st.write("1 scoop si no llegas a la proteína sólida.")
        with s3:
            if goal == "Perder Grasa":
                st.warning("**Cafeína / Té Verde**")
                st.write("Aumenta el metabolismo basal.")
            else:
                st.warning("**Omega 3**")
                st.write("2g diarios para salud articular y cardiovascular.")

    with tab_compra:
        st.markdown("### 🛍️ Imprescindibles en tu carrito")
        st.table(pd.DataFrame({
            "Categoría": ["Proteína", "Carbohidratos", "Grasas", "Varios"],
            "Alimentos": ["Pollo, Pescado, Huevos, Yogur", "Avena, Arroz, Patatas, Pan Int.", "Aceite Oliva, Nueces, Aguacate", "Brócoli, Espinacas, Fruta"]
        }))

# --- 3. INTERFAZ Y NAVEGACIÓN ---
with st.sidebar:
    st.title("⚡ Fitness OS Elite")
    u = st.text_input("Usuario").strip().lower()
    if not u: st.stop()
    sel = option_menu("Menú", ["Dashboard", "Entrenamientos", "Nutrición", "Ajustes"], 
                      icons=['house', 'activity', 'egg', 'gear'], menu_icon="cast")

if sel == "Dashboard":
    st.header(f"Centro de Mando: {u.capitalize()}")
    res = supabase.table("workouts").select("*").eq("username", u).order("date").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.plotly_chart(px.line(df, x="date", y="weight_kg", color="exercise", markers=True, template="plotly_dark"), use_container_width=True)
    else: st.info("Sin registros. Dale caña al entrenamiento.")

elif sel == "Entrenamientos":
    st.header("Log de Entrenamiento")
    with st.form("w_form", clear_on_submit=True):
        ex = st.text_input("Nombre del Ejercicio (Ej: Sentadilla)")
        c1, c2, c3 = st.columns(3)
        s, r, w = c1.number_input("Series", 1, 10, 3), c2.number_input("Reps", 1, 50, 10), c3.number_input("Peso (kg)", 0.0, 500.0, 50.0)
        if st.form_submit_button("Registrar Levantamiento"):
            supabase.table("workouts").insert({"username": u, "exercise": ex, "sets": s, "reps": r, "weight_kg": w}).execute()
            st.toast("¡Entrenamiento guardado!", icon="💪")

elif sel == "Nutrición":
    res = supabase.table("profiles").select("*").eq("username", u).execute()
    if not res.data: st.warning("Configura tu perfil en Ajustes.")
    else:
        p = res.data[0]
        st.header(f"Plan de Alimentación para {goal := st.selectbox('Objetivo', ['Perder Grasa', 'Mantener', 'Ganar Músculo'])}")
        m = get_nutrition_logic(p['weight'], p['height'], p['age'], p['gender'], p['activity_level'], goal)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔥 Calorías", f"{m['cal']}")
        c2.metric("🥩 Prot", f"{m['p']}g")
        c3.metric("🍚 Carbs", f"{m['c']}g")
        c4.metric("🥑 Grasa", f"{m['f']}g")
        
        generate_professional_view(m, p.get('diet_type', 'Omnívora'), goal)

elif sel == "Ajustes":
    st.header("Configuración Biométrica")
    res = supabase.table("profiles").select("*").eq("username", u).execute()
    curr = res.data[0] if res.data else {}
    with st.form("s_form"):
        col1, col2 = st.columns(2)
        we = col1.number_input("Peso (kg)", 30.0, 200.0, float(curr.get('weight', 75.0)))
        he = col2.number_input("Altura (cm)", 100.0, 250.0, float(curr.get('height', 175.0)))
        ag = col1.number_input("Edad", 15, 90, int(curr.get('age', 25)))
        ge = col2.selectbox("Género", ["Masculino", "Femenino"], index=0 if curr.get('gender')=="Masculino" else 1)
        ac = st.selectbox("Nivel de Actividad", [1.2, 1.375, 1.55, 1.725], format_func=lambda x: {1.2:"Sedentario", 1.375:"Ligero", 1.55:"Moderado", 1.725:"Intenso"}[x])
        dt = st.selectbox("Dieta", ["Omnívora", "Vegana"])
        if st.form_submit_button("Actualizar Todo"):
            supabase.table("profiles").upsert({"username": u, "weight": we, "height": he, "age": ag, "gender": ge, "activity_level": ac, "diet_type": dt}).execute()
            st.success("✅ Datos actualizados.")
