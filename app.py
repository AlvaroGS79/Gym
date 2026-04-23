def generate_diet_template(macros, diet_type):
    # Diccionarios de menús fijos (decisiones tomadas)
    menus = {
        "Omnívora": {
            "Desayuno": "Bowl de 80g de Avena con 1 plátano y un puñado de nueces.",
            "Almuerzo": "200g de Pechuga de pollo con 100g de Arroz cocido y Brócoli.",
            "Merienda": "Batido de proteína de suero (1 scoop) con una manzana.",
            "Cena": "150g de Salmón a la plancha con una ensalada de espinacas y tomate."
        },
        "Vegana": {
            "Desayuno": "Tostadas de pan integral con medio aguacate y semillas de chía.",
            "Almuerzo": "200g de Tofu firme salteado con quinoa y verduras variadas.",
            "Merienda": "Yogur de soja sin azúcar con 30g de almendras.",
            "Cena": "Hamburguesa de seitán con puré de patata y espárragos trigueros."
        }
    }
    
    opciones = menus.get(diet_type, menus["Omnívora"])
    
    template = f"""
    ### 📅 Tu Menú Concreto para Hoy
    *Objetivo: {macros['cal']} kcal | Macros: P:{macros['p']}g, C:{macros['c']}g, G:{macros['f']}g*
    
    ---
    ☕ **Desayuno:** {opciones['Desayuno']}

    🍽️ **Almuerzo:** {opciones['Almuerzo']}

    🍎 **Merienda:** {opciones['Merienda']}

    🌙 **Cena:** {opciones['Cena']}
    
    ---
    💡 **Instrucción:** No intercambies alimentos. Sigue estas cantidades para asegurar el cumplimiento de tus **{macros['p']}g de Proteína**.
    """
    return template

# --- DENTRO DE ELIF SELECTED == "NUTRICIÓN" ---
elif selected == "Nutrición":
    st.header("Menú Diario Específico")
    res = supabase.table("profiles").select("*").eq("username", user_input).execute()
    
    if not res.data:
        st.warning("Configura tus datos en 'Ajustes' primero.")
    else:
        profile = res.data[0]
        goal = st.selectbox("Objetivo", ["Perder Grasa", "Mantener", "Ganar Músculo"])
        m = get_nutrition_logic(profile['weight'], profile['height'], profile['age'], profile['gender'], profile['activity_level'], goal)
        
        # Resumen rápido arriba
        c1, c2, c3 = st.columns(3)
        c1.metric("Calorías", f"{m['cal']} kcal")
        c2.metric("Proteína (P)", f"{m['p']}g")
        c3.metric("Carbos (C)", f"{m['c']}g")
        
        st.divider()
        
        # Generar el menú cerrado
        st.markdown(generate_diet_template(m, profile.get('diet_type', 'Omnívora')))
