import streamlit as st
import pandas as pd
from utils import load_data, save_data_local, get_cached_date_summary

st.set_page_config(page_title="Entrenador Personal", layout="wide")

# --- 1. INICIALIZAR EL CARRITO DE ACCESORIOS ---
if "accesorios_temporales" not in st.session_state:
    st.session_state["accesorios_temporales"] = []

st.title("🏋️ Entrenador Personal")
df = load_data()

if not df.empty:
    categorias_historicas = sorted(df['Category'].dropna().unique().tolist()) if 'Category' in df.columns else []
    
    # --- 2. CONFIGURACIÓN DEL PROGRAMA DE FUERZA ---
    st.header("1. Configuración del Programa")
    
    col_prog, col_fase = st.columns([1.5, 2.5])
    with col_prog:
        # 5/3/1 configurado como primera opción por defecto (index=0)
        programa = st.selectbox(
            "Programa de fuerza:", 
            ["5/3/1 (Periodización)", "5x5 (Progresión Lineal)"],
            index=0
        )
    
    semana = None
    with col_fase:
        if programa == "5/3/1 (Periodización)":
            semana = st.radio(
                "Fase del ciclo 5/3/1:", 
                ["Semana 1 (3x5)", "Semana 2 (3x3)", "Semana 3 (5, 3, 1)"], 
                horizontal=True
            )

    st.divider()

    # --- 3. EVALUACIÓN Y SELECCIÓN POR FECHA HISTÓRICA ---
    st.header("2. Evaluar y Cargar Rutina Histórica")
    
    date_summary = get_cached_date_summary(df)
    rutina_principal_generada = []

    if date_summary:
        dates_list = [item[0] for item in date_summary]
        labels_list = [item[1] for item in date_summary]
        
        # Selector de fecha a evaluar
        selected_idx = st.selectbox(
            "Selecciona la fecha de entrenamiento a evaluar:",
            range(len(dates_list)),
            format_func=lambda x: labels_list[x]
        )
        eval_date = dates_list[selected_idx]
        
        # Ejercicios realizados en esa fecha específica
        df_eval_date = df[df['Date'].dt.date == eval_date]
        ex_on_date = df_eval_date['Exercise'].dropna().unique().tolist()
        
        # Filtro multiselect para escoger qué ejercicios usar de ese día
        ejercicios_seleccionados = st.multiselect(
            "Selecciona los ejercicios a los que deseas aplicar el programa hoy:",
            options=ex_on_date,
            default=ex_on_date
        )
        
        # Generar las series para todos los ejercicios seleccionados
        for exercise in ejercicios_seleccionados:
            hist_ej = df[df['Exercise'] == exercise].dropna(subset=['Weight', 'Reps'])
            
            if not hist_ej.empty:
                cat_ej = hist_ej.iloc[0]['Category'] if 'Category' in hist_ej.columns else "Fuerza"
                
                # Estimación de 1RM
                hist_ej['1RM_Est'] = hist_ej['Weight'] * (36 / (37 - hist_ej['Reps']))
                mejor_1rm = hist_ej['1RM_Est'].max()
                max_peso_5reps = hist_ej[hist_ej['Reps'] >= 5]['Weight'].max()
                if pd.isna(max_peso_5reps): 
                    max_peso_5reps = mejor_1rm * 0.75
                
                # Lógica 5/3/1
                if programa == "5/3/1 (Periodización)":
                    tm = mejor_1rm * 0.90  # Training Max
                    if semana == "Semana 1 (3x5)":
                        porcentajes, reps = [0.65, 0.75, 0.85], [5, 5, 5]
                    elif semana == "Semana 2 (3x3)":
                        porcentajes, reps = [0.70, 0.80, 0.90], [3, 3, 3]
                    else:
                        porcentajes, reps = [0.75, 0.85, 0.95], [5, 3, 1]
                        
                    for p, r in zip(porcentajes, reps):
                        peso_calc = round((tm * p) / 2.5) * 2.5
                        rutina_principal_generada.append({
                            'Exercise': exercise,
                            'Category': cat_ej,
                            'Weight': peso_calc,
                            'Reps': r
                        })
                
                # Lógica 5x5
                elif programa == "5x5 (Progresión Lineal)":
                    peso_objetivo = max_peso_5reps + 2.5
                    for _ in range(5):
                        rutina_principal_generada.append({
                            'Exercise': exercise,
                            'Category': cat_ej,
                            'Weight': peso_objetivo,
                            'Reps': 5
                        })

        if rutina_principal_generada:
            st.write("Vista previa de ejercicios principales ajustados (Editable):")
            df_rutina_principal = pd.DataFrame(rutina_principal_generada)
            rutina_principal_editada = st.data_editor(
                df_rutina_principal[['Exercise', 'Category', 'Weight', 'Reps']], 
                key="editor_principal", 
                hide_index=True, 
                use_container_width=True
            )
        else:
            st.warning("Selecciona al menos un ejercicio de la fecha evaluada.")
            rutina_principal_editada = pd.DataFrame()
    else:
        st.info("No hay fechas en el historial para evaluar.")
        rutina_principal_editada = pd.DataFrame()

    st.divider()

    # --- 4. ACCESORIOS (El "Carrito") ---
    st.header("3. Añadir Accesorios Opcionales")
    
    col_cat_acc, col_ej_acc, col_sets, col_reps, col_weight = st.columns([1.2, 1.8, 1, 1, 1])
    
    with col_cat_acc:
        cat_acc_filtro = st.selectbox("Grupo Muscular:", ["Todos"] + categorias_historicas, key="filtro_cat_acc")
        
    with col_ej_acc:
        if cat_acc_filtro == "Todos":
            ejercicios_acc_historicos = sorted(df['Exercise'].dropna().unique().tolist())
        else:
            ejercicios_acc_historicos = sorted(df[df['Category'] == cat_acc_filtro]['Exercise'].dropna().unique().tolist())
            
        opciones_acc = ejercicios_acc_historicos + ["➕ Nuevo Ejercicio..."]
        nombre_acc_sel = st.selectbox("Ejercicio Accesorio", opciones_acc, key="sel_acc")
        
        if nombre_acc_sel == "➕ Nuevo Ejercicio...":
            nombre_acc = st.text_input("Nombre del nuevo ejercicio")
            cat_final_acc = cat_acc_filtro if cat_acc_filtro != "Todos" else "Accesorio"
        else:
            nombre_acc = nombre_acc_sel
            try:
                cat_final_acc = df[df['Exercise'] == nombre_acc].iloc[0]['Category']
            except:
                cat_final_acc = "Accesorio"
            
    with col_sets:
        series_acc = st.number_input("Series", min_value=1, step=1, value=3)
    with col_reps:
        reps_acc = st.number_input("Reps", min_value=1, step=1, value=10)
    with col_weight:
        peso_acc = st.number_input("Peso", min_value=0.0, step=1.0, value=0.0)
        
    if st.button("➕ Añadir accesorio"):
        if nombre_acc:
            st.session_state["accesorios_temporales"].append({
                "Exercise": nombre_acc,
                "Sets": series_acc,
                "Reps": reps_acc,
                "Weight": peso_acc if peso_acc > 0 else None,
                "Category": cat_final_acc 
            })
            st.rerun()
        else:
            st.warning("Por favor, ingresa o selecciona un nombre para el ejercicio.")

    if st.session_state["accesorios_temporales"]:
        st.markdown("**Accesorios acumulados:**")
        df_acc_view = pd.DataFrame(st.session_state["accesorios_temporales"])
        st.dataframe(df_acc_view[['Exercise', 'Sets', 'Reps', 'Weight']], use_container_width=True)
        
        if st.button("↩️ Deshacer último accesorio"):
            st.session_state["accesorios_temporales"].pop()
            st.rerun()

    st.divider()

    # --- 5. ENVÍO FINAL A LA BASE DE DATOS LOCAL ---
    st.header("4. Iniciar Entrenamiento")
    
    if st.button("🚀 Enviar todo a la rutina de hoy", type="primary", use_container_width=True):
        rutina_final_lista = []
        fecha_hoy = pd.to_datetime("today").normalize()
        
        # 1. Empaquetar los ejercicios principales procesados con 5/3/1 o 5x5
        if not rutina_principal_editada.empty:
            for _, row in rutina_principal_editada.iterrows():
                rutina_final_lista.append({
                    'Date': fecha_hoy,
                    'Category': row['Category'],
                    'Exercise': row['Exercise'],
                    'Weight': row['Weight'],
                    'Reps': row['Reps']
                })
                
        # 2. Desempaquetar los accesorios
        for acc in st.session_state["accesorios_temporales"]:
            for _ in range(acc["Sets"]):
                rutina_final_lista.append({
                    'Date': fecha_hoy,
                    'Category': acc['Category'],
                    'Exercise': acc['Exercise'],
                    'Weight': acc['Weight'],
                    'Reps': acc['Reps']
                })
        
        if rutina_final_lista:
            df_nuevos = pd.DataFrame(rutina_final_lista)
            df_actualizado = pd.concat([df, df_nuevos], ignore_index=True)
            save_data_local(df_actualizado)
            
            st.session_state["accesorios_temporales"] = []
            st.success("¡Rutina cargada! Pasa a la pestaña de 'Registro' para iniciar tu entrenamiento.")
        else:
            st.error("No hay ejercicios seleccionados para enviar.")
else:
    st.info("No hay datos en la base de datos local. Registra algo primero en la pestaña principal.")