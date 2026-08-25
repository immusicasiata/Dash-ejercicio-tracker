import streamlit as st
import pandas as pd
from utils import (
    load_data, 
    save_data_local, 
    sync_to_github, 
    get_cached_date_summary, 
    calcular_series_531, 
    calcular_series_5x5, 
    format_clean, 
    update_cell
)

st.set_page_config(page_title="Panel de Entrenamiento", layout="wide")

# --- 1. CONFIGURACIÓN DEL ENTRENADOR EN LA BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Entrenador Inteligente")
    
    programa_activo = st.selectbox(
        "Programa de fuerza:", 
        ["5/3/1 (Periodización)", "5x5 (Progresión Lineal)"],
        index=0
    )
    
    semana_activa = None
    if programa_activo == "5/3/1 (Periodización)":
        st.markdown("Selecciona la semana para calcular las series sugeridas.")
        semana_activa = st.radio(
            "Fase del ciclo actual:",
            ["Semana 1 (3x5)", "Semana 2 (3x3)", "Semana 3 (5, 3, 1)", "Semana 4 (Descarga)"]
        )
    else:
        st.info("El programa 5x5 buscará tu récord a 5 repeticiones y le sumará 2.5 kg para generar 5 series de 5 repeticiones.")

st.title("📅 Panel de Entrenamiento")
df = load_data()

selected_date = st.date_input("Selecciona fecha:", pd.to_datetime("today"))
selected_date = pd.to_datetime(selected_date)

daily_df = df[df['Date'].dt.date == selected_date.date()].copy()

if not daily_df.empty:
    
    col_title, col_save = st.columns([2, 1])
    with col_title:
        st.subheader(f"Registros del {selected_date.strftime('%d/%m/%Y')}")
    with col_save:
        if st.button("☁️ Guardar Cambios en la Nube", type="primary", use_container_width=True):
            with st.spinner("Sincronizando con GitHub..."):
                success, msg = sync_to_github(df)
                if success:
                    st.success("¡Rutina respaldada exitosamente!")
                else:
                    st.error(f"Error al sincronizar: {msg}")
            
    st.write("") 
    
    ordered_exercises = daily_df['Exercise'].unique()
    
    for exercise in ordered_exercises:
        ex_df = daily_df[daily_df['Exercise'] == exercise]
        category = ex_df.iloc[0]['Category'] if 'Category' in ex_df.columns else "Sin Categoría"
        
        hist_ex = df[(df['Exercise'] == exercise) & (df['Date'].dt.date != selected_date.date())].dropna(subset=['Weight', 'Reps'])
        max_weight_hist = 0.0
        max_reps_per_weight = {}
        
        if not hist_ex.empty:
            max_weight_hist = hist_ex['Weight'].max()
            grouped_hist = hist_ex.groupby('Weight')['Reps'].max()
            max_reps_per_weight = grouped_hist.to_dict()
        
        most_freq_unit = ""
        for unit_col in ['Weight Unit', 'Distance Unit']:
            if unit_col in ex_df.columns:
                units = ex_df[unit_col].dropna()
                if not units.empty:
                    most_freq_unit = units.mode().iloc[0]
                    break
        
        header_title = f"{exercise} {f'({most_freq_unit})' if most_freq_unit else ''}"
        with st.expander(header_title, expanded=True):
            
            for idx, row in ex_df.iterrows():
                is_cardio = pd.notna(row.get('Distance')) or pd.notna(row.get('Time'))
                
                # Usamos directamente el índice 'idx' del DataFrame para que la clave sea única e inalterable
                if is_cardio:
                    col1, col2, col_btn_del = st.columns([2.5, 2.5, 0.7])
                    curr_dist = format_clean(row['Distance'])
                    curr_time = str(row['Time']) if pd.notna(row['Time']) else ""
                    
                    key_dist = f"dist_{idx}"
                    key_time = f"time_{idx}"
                    
                    with col1:
                        st.number_input(
                            "Distancia", 
                            value=curr_dist, 
                            step=0.1, 
                            format="%.1f", 
                            key=key_dist, 
                            on_change=update_cell, 
                            args=(idx, 'Distance', key_dist),
                            label_visibility="collapsed"
                        )
                    with col2:
                        st.text_input(
                            "Duración", 
                            value=curr_time, 
                            key=key_time, 
                            on_change=update_cell, 
                            args=(idx, 'Time', key_time),
                            label_visibility="collapsed"
                        )
                    with col_btn_del:
                        if st.button("🗑️", key=f"del_c_{idx}", help="Borrar serie"):
                            # Limpiamos del session_state solo la clave de la fila que estamos borrando
                            for k in [key_dist, key_time]:
                                if k in st.session_state:
                                    del st.session_state[k]
                            df.drop(idx, inplace=True)
                            save_data_local(df)
                            st.rerun()
                else:
                    col_w, col_r, col_badges, col_btn_del = st.columns([2, 2, 2, 0.7])
                    curr_w = format_clean(row['Weight'])
                    curr_r = int(row['Reps']) if pd.notna(row['Reps']) else 0
                    
                    key_w = f"w_{idx}"
                    key_r = f"r_{idx}"
                    
                    with col_w:
                        st.number_input(
                            "Peso", 
                            value=curr_w, 
                            step=5.0, 
                            format="%.1f", 
                            key=key_w, 
                            on_change=update_cell, 
                            args=(idx, 'Weight', key_w),
                            label_visibility="collapsed"
                        )
                    with col_r:
                        st.number_input(
                            "Reps", 
                            value=curr_r, 
                            step=1, 
                            key=key_r, 
                            on_change=update_cell, 
                            args=(idx, 'Reps', key_r),
                            label_visibility="collapsed"
                        )
                    
                    with col_badges:
                        badges_html = ""
                        check_w = curr_w if curr_w > 0 else 0
                        check_r = curr_r if curr_r > 0 else 0
                        
                        if check_w > 0 and check_w >= max_weight_hist and max_weight_hist > 0:
                            badges_html += "🔥 <span style='color:#FF4B4B; font-weight:bold;'>Máx Peso</span> "
                        
                        if check_w > 0 and check_r > 0:
                            historical_max_reps_for_w = max_reps_per_weight.get(check_w, 0)
                            if historical_max_reps_for_w > 0:
                                if check_r > historical_max_reps_for_w:
                                    badges_html += "🏆 <span style='color:#FFD700; font-weight:bold;'>Récord Reps</span>"
                                elif check_r == historical_max_reps_for_w:
                                    badges_html += "🤝 <span style='color:#4A90E2; font-weight:bold;'>Iguala Récord</span>"
                        
                        if badges_html:
                            st.markdown(f"<div style='padding-top: 8px; font-size: 0.85em;'>{badges_html}</div>", unsafe_allow_html=True)

                    with col_btn_del:
                        if st.button("🗑️", key=f"del_w_{idx}", help="Borrar serie"):
                            # Limpiamos solo los inputs de esta fila específica de la memoria
                            for k in [key_w, key_r]:
                                if k in st.session_state:
                                    del st.session_state[k]
                            df.drop(idx, inplace=True)
                            save_data_local(df)
                            st.rerun()
            
            st.write("")
            
            # --- 2. BOTONES DE ACCIÓN POR EJERCICIO ---
            is_cardio_ex = pd.notna(ex_df.iloc[0].get('Distance')) or pd.notna(ex_df.iloc[0].get('Time'))
            
            col_add, col_prog, col_del_ex = st.columns([1.3, 1.7, 1])
            
            with col_add:
                if st.button(f"➕ Agregar serie", key=f"add_row_{exercise}"):
                    new_row = {
                        'Date': selected_date, 'Exercise': exercise, 'Category': category,
                        'Weight Unit': most_freq_unit if not is_cardio_ex else None
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_data_local(df)
                    st.rerun()
            
            with col_prog:
                if not is_cardio_ex:
                    btn_label = "💡 Cargar 5/3/1" if programa_activo == "5/3/1 (Periodización)" else "💡 Cargar 5x5"
                    
                    if st.button(btn_label, key=f"btn_prog_{exercise}"):
                        historial_ejercicio = df[(df['Exercise'] == exercise) & (df['Date'].dt.date != selected_date.date())]
                        
                        if programa_activo == "5/3/1 (Periodización)":
                            series_sugeridas = calcular_series_531(historial_ejercicio, exercise, semana_activa)
                        else:
                            series_sugeridas = calcular_series_5x5(historial_ejercicio, exercise)
                        
                        if series_sugeridas:
                            nuevas_series = []
                            for s in series_sugeridas:
                                nuevas_series.append({
                                    'Date': selected_date, 
                                    'Exercise': exercise, 
                                    'Category': category,
                                    'Weight': s["Weight"],
                                    'Reps': s["Reps"],
                                    'Weight Unit': most_freq_unit
                                })
                            df = pd.concat([df, pd.DataFrame(nuevas_series)], ignore_index=True)
                            save_data_local(df)
                            st.rerun()
                        else:
                            st.warning("No hay historial previo para este ejercicio para calcular los pesos.")
                            
            with col_del_ex:
                if st.button(f"🗑️ Borrar Ejercicio", key=f"del_ex_{exercise}", type="primary"):
                    # Limpiamos las llaves de session_state de todas las filas que pertenecían a este ejercicio
                    for idx_ex in ex_df.index:
                        for k in [f"w_{idx_ex}", f"r_{idx_ex}", f"dist_{idx_ex}", f"time_{idx_ex}"]:
                            if k in st.session_state:
                                del st.session_state[k]
                    df.drop(ex_df.index, inplace=True)
                    save_data_local(df)
                    st.rerun()
else:
    st.info("No hay registros en esta fecha.")

st.divider()
with st.expander("➕ Agregar nuevo ejercicio al día"):
    existing_categories = sorted(df['Category'].dropna().unique().tolist()) if 'Category' in df.columns else []
    if existing_categories:
        selected_category = st.selectbox("Categoría:", existing_categories, key="new_ex_cat")
        cat_history = df[df['Category'] == selected_category]['Exercise'].dropna().unique().tolist()
        options = sorted(list(set(cat_history))) + ["➕ Otro"]
        chosen = st.selectbox("Ejercicio:", options, key="new_ex_name")
        name = st.text_input("Nombre:", key="custom_ex_name") if chosen == "➕ Otro" else chosen
        unit = st.selectbox("Unidad:", ["kg", "lbs", "Sin unidad"], key="new_unit_select")
        
        if st.button("Guardar e iniciar", key="btn_save_new_ex"):
            if name.strip():
                u = unit if unit != "Sin unidad" else None
                df = pd.concat([df, pd.DataFrame([{'Date': selected_date, 'Exercise': name.strip(), 'Category': selected_category, 'Weight Unit': u}])], ignore_index=True)
                save_data_local(df)
                st.rerun()
    else:
        st.warning("No hay categorías.")

st.divider()
with st.expander("🔄 Copiar rutina de otro día"):
    s_date = st.date_input("Fecha a copiar:", pd.to_datetime("today") - pd.Timedelta(days=1))
    s_date = pd.to_datetime(s_date)
    
    if not df.empty:
        date_summary = get_cached_date_summary(df)
        if date_summary:
            dates_only = [item[0] for item in date_summary]
            date_labels = [item[1] for item in date_summary]
            selected_label_idx = st.selectbox("Selecciona fecha:", range(len(dates_only)), format_func=lambda x: date_labels[x], key="copy_date_select")
            target_date = pd.to_datetime(dates_only[selected_label_idx])
            
            source_entries = df[df['Date'].dt.date == target_date.date()].copy()
            if not source_entries.empty:
                st.write(f"Vista previa ({target_date.strftime('%d/%m/%Y')}):")
                st.dataframe(source_entries[['Category', 'Exercise', 'Weight', 'Reps']].drop_duplicates(), use_container_width=True, hide_index=True)
                if st.button("Copiar rutina seleccionada", key="btn_execute_copy"):
                    new_entries = source_entries.copy()
                    new_entries['Date'] = selected_date
                    df = pd.concat([df, new_entries], ignore_index=True)
                    save_data_local(df)
                    st.success("¡Copiado!")
                    st.rerun()
            else:
                st.warning("No hay registros en esa fecha.")
        else:
            st.info("No hay historial disponible.")