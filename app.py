import streamlit as st
import pandas as pd
from utils import load_data, save_data, get_cached_date_summary

st.set_page_config(page_title="Panel de Entrenamiento", layout="wide")

def format_clean(val):
    try: 
        return float(val)
    except: 
        return 0.0

st.title("📅 Panel de Entrenamiento")
df = load_data()

selected_date = st.date_input("Selecciona fecha:", pd.to_datetime("today"))
selected_date = pd.to_datetime(selected_date)

daily_df = df[df['Date'].dt.date == selected_date.date()].copy()

if not daily_df.empty:
    st.subheader(f"Registros del {selected_date.strftime('%d/%m/%Y')}")
    
    # Orden cronológico de los ejercicios
    ordered_exercises = daily_df['Exercise'].unique()
    
    for exercise in ordered_exercises:
        ex_df = daily_df[daily_df['Exercise'] == exercise]
        category = ex_df.iloc[0]['Category'] if 'Category' in ex_df.columns else "Sin Categoría"
        
        hist_ex = df[df['Exercise'] == exercise].dropna(subset=['Weight', 'Reps'])
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
        
        # Expandible por ejercicio (reemplaza al st.markdown con emoji)
        header_title = f"{exercise} {f'({most_freq_unit})' if most_freq_unit else ''}"
        with st.expander(header_title, expanded=True):
            
            for idx, row in ex_df.iterrows():
                is_cardio = pd.notna(row.get('Distance')) or pd.notna(row.get('Time'))
                
                if is_cardio:
                    col1, col2, col_btn_save, col_btn_del = st.columns([2, 2, 0.7, 0.7])
                    curr_dist = format_clean(row['Distance'])
                    curr_time = str(row['Time']) if pd.notna(row['Time']) else ""
                    
                    with col1:
                        new_dist = st.number_input("Distancia", value=curr_dist, step=0.1, format="%.1f", key=f"dist_{idx}_{selected_date}", label_visibility="collapsed")
                    with col2:
                        new_time = st.text_input("Duración", value=curr_time, key=f"time_{idx}_{selected_date}", label_visibility="collapsed")
                    with col_btn_save:
                        if st.button("💾", key=f"save_c_{idx}_{selected_date}"):
                            df.loc[idx, 'Distance'] = new_dist if new_dist > 0 else None
                            df.loc[idx, 'Time'] = new_time if new_time else None
                            save_data(df)
                            st.rerun()
                    with col_btn_del:
                        if st.button("🗑️", key=f"del_c_{idx}_{selected_date}", help="Borrar serie"):
                            df.drop(idx, inplace=True)
                            save_data(df)
                            st.rerun()
                else:
                    col_w, col_r, col_badges, col_btn_save, col_btn_del = st.columns([1.8, 1.8, 1.4, 0.7, 0.7])
                    curr_w = format_clean(row['Weight'])
                    curr_r = int(row['Reps']) if pd.notna(row['Reps']) else 0
                    
                    with col_w:
                        new_w = st.number_input("Peso", value=curr_w, step=5.0, format="%.1f", key=f"w_{idx}_{selected_date}", label_visibility="collapsed")
                    with col_r:
                        new_r = st.number_input("Reps", value=int(curr_r), step=1, key=f"r_{idx}_{selected_date}", label_visibility="collapsed")
                    
                    with col_badges:
                        badges_html = ""
                        check_w = curr_w if curr_w > 0 else 0
                        check_r = curr_r if curr_r > 0 else 0
                        
                        if check_w > 0 and check_w >= max_weight_hist and max_weight_hist > 0:
                            badges_html += "🔥 <span style='color:#FF4B4B; font-weight:bold;'>Máx Peso</span> "
                        
                        if check_w > 0 and check_r > 0:
                            historical_max_reps_for_w = max_reps_per_weight.get(check_w, 0)
                            if check_r >= historical_max_reps_for_w and historical_max_reps_for_w > 0:
                                badges_html += "🏆 <span style='color:#FFD700; font-weight:bold;'>Récord Reps</span>"
                        
                        if badges_html:
                            st.markdown(f"<div style='padding-top: 8px; font-size: 0.85em;'>{badges_html}</div>", unsafe_allow_html=True)

                    with col_btn_save:
                        if st.button("💾", key=f"save_w_{idx}_{selected_date}"):
                            df.loc[idx, 'Weight'] = new_w if new_w > 0 else None
                            df.loc[idx, 'Reps'] = new_r if new_r > 0 else None
                            save_data(df)
                            st.rerun()
                    with col_btn_del:
                        if st.button("🗑️", key=f"del_w_{idx}_{selected_date}", help="Borrar serie"):
                            df.drop(idx, inplace=True)
                            save_data(df)
                            st.rerun()
            
            st.write("")
            col_add, col_del_ex = st.columns([1.5, 1])
            with col_add:
                if st.button(f"➕ Agregar serie", key=f"add_row_{exercise}_{selected_date}"):
                    is_cardio_ex = pd.notna(ex_df.iloc[0].get('Distance')) or pd.notna(ex_df.iloc[0].get('Time'))
                    new_row = {
                        'Date': selected_date, 'Exercise': exercise, 'Category': category,
                        'Weight Unit': most_freq_unit if not is_cardio_ex else None
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(df)
                    st.rerun()
            with col_del_ex:
                if st.button(f"🗑️ Borrar Ejercicio", key=f"del_ex_{exercise}_{selected_date}", type="primary"):
                    df.drop(ex_df.index, inplace=True)
                    save_data(df)
                    st.rerun()
else:
    st.info("No hay registros en esta fecha.")

st.divider()
with st.expander("➕ Agregar nuevo ejercicio al día"):
    existing_categories = sorted(df['Category'].dropna().unique().tolist()) if 'Category' in df.columns else []
    if existing_categories:
        selected_category = st.selectbox("Categoría:", existing_categories, key=f"new_ex_cat_{selected_date}")
        cat_history = df[df['Category'] == selected_category]['Exercise'].dropna().unique().tolist()
        options = sorted(list(set(cat_history))) + ["➕ Otro"]
        chosen = st.selectbox("Ejercicio:", options, key=f"new_ex_name_{selected_date}")
        name = st.text_input("Nombre:", key=f"custom_ex_{selected_date}") if chosen == "➕ Otro" else chosen
        unit = st.selectbox("Unidad:", ["kg", "lbs", "Sin unidad"], key=f"new_unit_{selected_date}")
        
        if st.button("Guardar e iniciar", key=f"btn_save_new_{selected_date}"):
            if name.strip():
                u = unit if unit != "Sin unidad" else None
                df = pd.concat([df, pd.DataFrame([{'Date': selected_date, 'Exercise': name.strip(), 'Category': selected_category, 'Weight Unit': u}])], ignore_index=True)
                save_data(df)
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
                if st.button("Copiar rutina seleccionada"):
                    new_entries = source_entries.copy()
                    new_entries['Date'] = selected_date
                    save_data(pd.concat([df, new_entries], ignore_index=True))
                    st.success("¡Copiado!")
                    st.rerun()
            else:
                st.warning("No hay registros en esa fecha.")
        else:
            st.info("No hay historial disponible.")