import streamlit as st
import pandas as pd
from utils import load_data, save_data_local

st.set_page_config(page_title="Entrenador Personal", layout="wide")

# --- 1. INICIALIZAR EL CARRITO DE ACCESORIOS ---
if "accesorios_temporales" not in st.session_state:
    st.session_state["accesorios_temporales"] = []

st.title("🏋️ Entrenador Personal")
df = load_data()

if not df.empty:
    # --- 2. CONFIGURACIÓN DEL EJERCICIO PRINCIPAL ---
    st.header("1. Ejercicio Principal")
    col_prog, col_ej = st.columns(2)
    
    with col_prog:
        programa = st.selectbox("Programa de fuerza:", ["5x5 (Progresión Lineal)", "5/3/1 (Periodización)"])
    
    with col_ej:
        ejercicios_historicos = sorted(df['Exercise'].dropna().unique().tolist())
        ejercicio_elegido = st.selectbox("Selecciona el ejercicio base:", ejercicios_historicos)
    
    hist_ej = df[df['Exercise'] == ejercicio_elegido].dropna(subset=['Weight', 'Reps'])
    
    rutina_hoy = []
    categoria_principal = "Sin Categoría"
    rutina_editada = pd.DataFrame()

    if not hist_ej.empty:
        categoria_principal = hist_ej.iloc[0]['Category'] if 'Category' in hist_ej.columns else "Fuerza"
        
        # Cálculos de RM y Max 5 Reps
        hist_ej['1RM_Est'] = hist_ej['Weight'] * (36 / (37 - hist_ej['Reps']))
        mejor_1rm = hist_ej['1RM_Est'].max()
        max_peso_5reps = hist_ej[hist_ej['Reps'] >= 5]['Weight'].max()
        if pd.isna(max_peso_5reps): max_peso_5reps = mejor_1rm * 0.75
        
        st.caption(f"**1RM Estimado:** {mejor_1rm:.1f} | **Máx histórico 5 Reps:** {max_peso_5reps:.1f}")
        
        # Lógica de los programas
        if programa == "5x5 (Progresión Lineal)":
            peso_objetivo = max_peso_5reps + 2.5
            for i in range(5):
                rutina_hoy.append({'Exercise': ejercicio_elegido, 'Weight': peso_objetivo, 'Reps': 5})
                
        elif programa == "5/3/1 (Periodización)":
            semana = st.radio("Fase del ciclo:", ["Semana 1 (3x5)", "Semana 2 (3x3)", "Semana 3 (5, 3, 1)"], horizontal=True)
            tm = mejor_1rm * 0.90 # Training Max
            
            if semana == "Semana 1 (3x5)":
                porcentajes, reps = [0.65, 0.75, 0.85], [5, 5, 5]
            elif semana == "Semana 2 (3x3)":
                porcentajes, reps = [0.70, 0.80, 0.90], [3, 3, 3]
            else:
                porcentajes, reps = [0.75, 0.85, 0.95], [5, 3, 1]
                
            for p, r in zip(porcentajes, reps):
                peso_calc = round((tm * p) / 2.5) * 2.5
                rutina_hoy.append({'Exercise': ejercicio_elegido, 'Weight': peso_calc, 'Reps': r})
        
        st.write("Vista previa (Editable):")
        df_rutina = pd.DataFrame(rutina_hoy)
        rutina_editada = st.data_editor(df_rutina, key="rutina_editor", hide_index=True, use_container_width=True)
    else:
        st.warning("No hay suficientes datos históricos para calcular las progresiones de este ejercicio.")

    st.divider()

    # --- 3. ACCESORIOS (El "Carrito") ---
    st.header("2. Añadir Accesorios")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        # Permitimos elegir del historial o crear uno nuevo
        opciones_acc = ejercicios_historicos + ["➕ Nuevo Ejercicio..."]
        nombre_acc_sel = st.selectbox("Ejercicio Accesorio", opciones_acc, key="sel_acc")
        
        if nombre_acc_sel == "➕ Nuevo Ejercicio...":
            nombre_acc = st.text_input("Escribe el nombre del accesorio")
        else:
            nombre_acc = nombre_acc_sel
            
    with col2:
        series_acc = st.number_input("Series", min_value=1, step=1, value=3)
    with col3:
        reps_acc = st.number_input("Reps", min_value=1, step=1, value=10)
    with col4:
        peso_acc = st.number_input("Peso (opcional)", min_value=0.0, step=1.0, value=0.0)
        
    if st.button("➕ Añadir a la lista"):
        if nombre_acc:
            st.session_state["accesorios_temporales"].append({
                "Exercise": nombre_acc,
                "Sets": series_acc,
                "Reps": reps_acc,
                "Weight": peso_acc if peso_acc > 0 else None,
                "Category": "Accesorio" # Categoría genérica para que no falle el app.py
            })
            st.rerun()
        else:
            st.warning("Por favor, ingresa o selecciona un nombre para el ejercicio.")

    # Vista previa del carrito de accesorios
    if st.session_state["accesorios_temporales"]:
        st.markdown("**Accesorios acumulados:**")
        df_acc_view = pd.DataFrame(st.session_state["accesorios_temporales"])
        st.dataframe(df_acc_view, use_container_width=True)
        
        if st.button("↩️ Deshacer último accesorio"):
            st.session_state["accesorios_temporales"].pop()
            st.rerun()

    st.divider()

    # --- 4. ENVÍO FINAL A LA BASE DE DATOS LOCAL ---
    st.header("3. Iniciar Entrenamiento")
    
    if st.button("🚀 Enviar todo a la rutina de hoy", type="primary", use_container_width=True):
        rutina_final_lista = []
        fecha_hoy = pd.to_datetime("today").normalize()
        
        # Empaquetar el ejercicio principal (ya viene como 1 fila = 1 serie desde el data_editor)
        if not rutina_editada.empty:
            for _, row in rutina_editada.iterrows():
                rutina_final_lista.append({
                    'Date': fecha_hoy,
                    'Category': categoria_principal,
                    'Exercise': row['Exercise'],
                    'Weight': row['Weight'],
                    'Reps': row['Reps']
                })
                
        # Desempaquetar los accesorios (Multiplicar filas según el número de 'Sets')
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
            # Convertir a DataFrame y unir al historial
            df_nuevos = pd.DataFrame(rutina_final_lista)
            df_actualizado = pd.concat([df, df_nuevos], ignore_index=True)
            
            # Guardar en local (app.py lo leerá automáticamente)
            save_data_local(df_actualizado)
            
            # Vaciar el carrito de sesión
            st.session_state["accesorios_temporales"] = []
            
            st.success("¡Rutina programada exitosamente! Ve a la pestaña de 'Registro' para comenzar.")
        else:
            st.error("No has configurado ningún ejercicio para guardar.")
else:
    st.info("No hay datos en la base de datos local. Registra algo primero en la pestaña principal.")