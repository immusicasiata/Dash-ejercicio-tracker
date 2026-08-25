import uuid
import streamlit as st
import pandas as pd
from utils import (
    load_data, 
    save_data_local, 
    sync_to_github, 
    get_cached_date_summary, 
    obtener_semana_objetivo_ejercicio,
    obtener_estado_programa_ejercicio,
    calcular_series_531, 
    calcular_series_5x5, 
    format_clean, 
    update_cell
)

st.set_page_config(page_title="Panel de Entrenamiento", layout="wide")

df = load_data()

with st.sidebar:
    st.header("⚙️ Entrenador Inteligente")
    
    programa_activo = st.selectbox(
        "Programa global por defecto:", 
        ["5/3/1 (Periodización)", "5x5 (Progresión Lineal)"],
        index=0
    )
    
    semana_manual = "Automático"
    if programa_activo == "5/3/1 (Periodización)":
        st.markdown("ℹ️ *Cada ejercicio calcula su semana de forma independiente.*")
        semana_manual = st.selectbox(
            "Sobreescribir semana al cargar (Opcional):",
            ["Automático", "Semana 1 (3x5)", "Semana 2 (3x3)", "Semana 3 (5, 3, 1)", "Semana 4 (Descarga)"],
            index=0,
            help="Al seleccionar una semana, solo se aplicará al ejercicio donde presiones el botón de cargar."
        )
    else:
        st.info("El programa 5x5 calculará 5 series de 5 reps sumando 2.5 kg a tu récord previo a 5 reps.")

st.title("📅 Panel de Entrenamiento")

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
        ex_df = daily_df[daily_df['Exercise'] == exercise].reset_index(drop=True)
        category = ex_df.iloc[0]['Category'] if 'Category' in ex_df.columns else "Sin Categoría"
        
        # Filtro de categorías excluidas
        cat_str = str(category).lower()
        is_excluded_from_strength = "alta repetición" in cat_str or "resistencia" in cat_str or "cardio" in cat_str
        is_cardio_ex = pd.notna(ex_df.iloc[0].get('Distance')) or pd.notna(ex_df.iloc[0].get('Time'))
        
        hist_ex_global = df[(df['Exercise'] == exercise) & (df['Date'].dt.date < selected_date.date())]
        hist_ex = hist_ex_global.dropna(subset=['Weight', 'Reps'])
        
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
        
        # CÁLCULO AUTOMÁTICO INDEPENDIENTE (Permanece visible en el título)
        semana_objetivo_auto = obtener_semana_objetivo_ejercicio(df, exercise, selected_date)
        prog_previo, semana_previa = obtener_estado_programa_ejercicio(df, exercise, selected_date)
        
        prog_en_dia = ex_df.iloc[0].get('Program')
        week_en_dia = ex_df.iloc[0].get('Week')
        
        # El título del encabezado SIEMPRE refleja el estado automático o el estado ya guardado
        if is_excluded_from_strength or is_cardio_ex:
            estado_badge = ""
        elif pd.notna(prog_en_dia) and pd.notna(week_en_dia):
            estado_badge = f" [{prog_en_dia} - {week_en_dia}]"
        elif semana_previa:
            estado_badge = f" [{prog_previo}: {semana_previa} ➡️ Sugerida: {semana_objetivo_auto.split()[0]} {semana_objetivo_auto.split()[1]}]"
        else:
            estado_badge = f" [Inicio de Ciclo ➡️ {semana_objetivo_auto.split()[0]} {semana_objetivo_auto.split()[1]}]"
        
        header_title = f"{exercise} {f'({most_freq_unit})' if most_freq_unit else ''}{estado_badge}"
        
        with st.expander(header_title, expanded=False):
            
            for i, row in ex_df.iterrows():
                row_id = row['row_id']
                is_cardio = pd.notna(row.get('Distance')) or pd.notna(row.get('Time'))
                
                if is_cardio:
                    col1, col2, col_btn_del = st.columns([2.5, 2.5, 0.7])
                    curr_dist = format_clean(row['Distance'])
                    curr_time = str(row['Time']) if pd.notna(row['Time']) else ""
                    
                    key_dist = f"dist_{row_id}"
                    key_time = f"time_{row_id}"
                    
                    with col1:
                        st.number_input("Distancia", value=curr_dist, step=0.1, format="%.1f", key=key_dist, on_change=update_cell, args=(row_id, 'Distance', key_dist), label_visibility="collapsed")
                    with col2:
                        st.text_input("Duración", value=curr_time, key=key_time, on_change=update_cell, args=(row_id, 'Time', key_time), label_visibility="collapsed")
                    with col_btn_del:
                        if st.button("🗑️", key=f"del_c_{row_id}", help="Borrar serie"):
                            for k in [key_dist, key_time]:
                                if k in st.session_state: del st.session_state[k]
                            df = df[df['row_id'] != row_id]
                            save_data_local(df)
                            st.rerun()
                else:
                    col_w, col_r, col_badges, col_btn_del = st.columns([2, 2, 2, 0.7])
                    curr_w = format_clean(row['Weight'])
                    curr_r = int(row['Reps']) if pd.notna(row['Reps']) else 0
                    
                    key_w = f"w_{row_id}"
                    key_r = f"r_{row_id}"
                    
                    with col_w:
                        st.number_input("Peso", value=curr_w, step=5.0, format="%.1f", key=key_w, on_change=update_cell, args=(row_id, 'Weight', key_w), label_visibility="collapsed")
                    with col_r:
                        st.number_input("Reps", value=curr_r, step=1, key=key_r, on_change=update_cell, args=(row_id, 'Reps', key_r), label_visibility="collapsed")
                    
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
                        if st.button("🗑️", key=f"del_w_{row_id}", help="Borrar serie"):
                            for k in [key_w, key_r]:
                                if k in st.session_state: del st.session_state[k]
                            df = df[df['row_id'] != row_id]
                            save_data_local(df)
                            st.rerun()
            
            st.write("")
            
            col_add, col_prog, col_del_ex = st.columns([1.3, 1.7, 1])
            
            with col_add:
                if st.button(f"➕ Agregar serie", key=f"add_row_{exercise}"):
                    new_row = {
                        'row_id': str(uuid.uuid4()),
                        'Date': selected_date, 
                        'Exercise': exercise, 
                        'Category': category,
                        'Weight Unit': most_freq_unit if not is_cardio_ex else None
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_data_local(df)
                    st.rerun()
            
            with col_prog:
                if not is_cardio_ex and not is_excluded_from_strength:
                    # Determina qué semana usar solo al presionar el botón
                    semana_a_cargar = semana_manual if semana_manual != "Automático" else semana_objetivo_auto
                    
                    if programa_activo == "5/3/1 (Periodización)":
                        btn_label = f"💡 Cargar 5/3/1 ({semana_a_cargar.split()[0]} {semana_a_cargar.split()[1]})"
                    else:
                        btn_label = "💡 Cargar 5x5"
                    
                    if st.button(btn_label, key=f"btn_prog_{exercise}"):
                        if programa_activo == "5/3/1 (Periodización)":
                            series_sugeridas = calcular_series_531(hist_ex_global, exercise, semana_a_cargar)
                            prog_val = "5/3/1"
                            week_val = semana_a_cargar
                        else:
                            series_sugeridas = calcular_series_5x5(hist_ex_global, exercise)
                            prog_val = "5x5"
                            week_val = "Progresión 5x5"
                        
                        if series_sugeridas:
                            nuevas_series = []
                            for s in series_sugeridas:
                                nuevas_series.append({
                                    'row_id': str(uuid.uuid4()),
                                    'Date': selected_date, 
                                    'Exercise': exercise, 
                                    'Category': category,
                                    'Weight': s["Weight"],
                                    'Reps': s["Reps"],
                                    'Weight Unit': most_freq_unit,
                                    'Program': prog_val,
                                    'Week': week_val
                                })
                            df = pd.concat([df, pd.DataFrame(nuevas_series)], ignore_index=True)
                            save_data_local(df)
                            st.rerun()
                        else:
                            st.warning("No hay historial previo para este ejercicio para calcular los pesos.")
                            
            with col_del_ex:
                if st.button(f"🗑️ Borrar Ejercicio", key=f"del_ex_{exercise}", type="primary"):
                    target_ex_rows = df[(df['Date'].dt.date == selected_date.date()) & (df['Exercise'] == exercise)]
                    for r_id in target_ex_rows['row_id']:
                        for k in [f"w_{r_id}", f"r_{r_id}", f"dist_{r_id}", f"time_{r_id}"]:
                            if k in st.session_state: del st.session_state[k]
                    df = df[~((df['Date'].dt.date == selected_date.date()) & (df['Exercise'] == exercise))]
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
                new_row = {
                    'row_id': str(uuid.uuid4()),
                    'Date': selected_date, 
                    'Exercise': name.strip(), 
                    'Category': selected_category, 
                    'Weight Unit': u
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data_local(df)
                st.rerun()
    else:
        st.warning("No hay categorías.")

st.divider()
with st.expander("🔄 Copiar rutina de otro día (con avance inteligente)"):
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
                st.dataframe(source_entries[['Category', 'Exercise', 'Weight', 'Reps', 'Program', 'Week']].drop_duplicates(), use_container_width=True, hide_index=True)
                
                auto_avanzar_531 = st.checkbox("Avanzar automáticamente la semana de 5/3/1 por cada ejercicio", value=True)
                
                if st.button("Copiar rutina seleccionada", key="btn_execute_copy"):
                    new_entries = source_entries.copy()
                    new_entries['Date'] = selected_date
                    new_entries['row_id'] = [str(uuid.uuid4()) for _ in range(len(new_entries))]
                    
                    if auto_avanzar_531:
                        processed_dfs = []
                        for ex_name, group in new_entries.groupby('Exercise'):
                            cat_group_str = str(group['Category'].iloc[0] if 'Category' in group.columns else "").lower()
                            es_excluido = "alta repetición" in cat_group_str or "resistencia" in cat_group_str or "cardio" in cat_group_str
                            
                            mask_prog = (group['Program'] == '5/3/1') & (group['Week'].notna())
                            prog_rows = group[mask_prog].copy()
                            non_prog_rows = group[~mask_prog].copy()
                            
                            if not prog_rows.empty and not es_excluido:
                                last_week_copied = prog_rows['Week'].iloc[0]
                                secuencia = ["Semana 1 (3x5)", "Semana 2 (3x3)", "Semana 3 (5, 3, 1)", "Semana 4 (Descarga)"]
                                try:
                                    idx = secuencia.index(last_week_copied)
                                    siguiente_semana = secuencia[(idx + 1) % len(secuencia)]
                                except ValueError:
                                    siguiente_semana = "Semana 1 (3x5)"
                                
                                hist_previo = df[(df['Exercise'] == ex_name) & (df['Date'].dt.date < selected_date.date())]
                                nuevas_sugerencias = calcular_series_531(hist_previo, ex_name, siguiente_semana)
                                
                                if nuevas_sugerencias:
                                    base_row = prog_rows.iloc[0].to_dict()
                                    recalculated_rows = []
                                    for s in nuevas_sugerencias:
                                        r_copy = base_row.copy()
                                        r_copy['row_id'] = str(uuid.uuid4())
                                        r_copy['Weight'] = s['Weight']
                                        r_copy['Reps'] = s['Reps']
                                        r_copy['Week'] = siguiente_semana
                                        recalculated_rows.append(r_copy)
                                    
                                    if not non_prog_rows.empty:
                                        df_combinado = pd.concat([pd.DataFrame(recalculated_rows), non_prog_rows], ignore_index=True)
                                        processed_dfs.append(df_combinado)
                                    else:
                                        processed_dfs.append(pd.DataFrame(recalculated_rows))
                                else:
                                    processed_dfs.append(group)
                            else:
                                processed_dfs.append(group)
                        
                        new_entries = pd.concat(processed_dfs, ignore_index=True)
                    
                    df = pd.concat([df, new_entries], ignore_index=True)
                    save_data_local(df)
                    st.success("¡Rutina copiada y adaptada inteligentemente por ejercicio!")
                    st.rerun()
            else:
                st.warning("No hay registros en esa fecha.")
        else:
            st.info("No hay historial disponible.")