import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Panel de Entrenamiento", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        df = conn.read()
        df['Date'] = pd.to_datetime(df['Date'])
        # Forzar tipos numéricos para evitar el TypeError
        numeric_cols = ['Weight', 'Reps', 'Distance']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.dropna(how='all')
    except: 
        return pd.DataFrame()

def save_data(df):
    numeric_cols = ['Weight', 'Reps', 'Distance']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    conn.update(data=df)
    st.cache_data.clear()

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
    
    # Agrupamos por categoría
    for category in daily_df['Category'].unique():
        with st.expander(f"💪 {category}", expanded=True):
            cat_df = daily_df[daily_df['Category'] == category]
            
            for exercise in cat_df['Exercise'].unique():
                ex_df = cat_df[cat_df['Exercise'] == exercise]
                
                # --- CÁLCULO DE RÉCORDS Y MÁXIMOS HISTÓRICOS ---
                hist_ex = df[df['Exercise'] == exercise].dropna(subset=['Weight', 'Reps'])
                max_weight_hist = 0.0
                max_reps_per_weight = {}
                
                if not hist_ex.empty:
                    max_weight_hist = hist_ex['Weight'].max()
                    # Agrupar por peso y encontrar el máximo de reps histórico para cada uno
                    grouped_hist = hist_ex.groupby('Weight')['Reps'].max()
                    max_reps_per_weight = grouped_hist.to_dict()
                
                # Obtener la unidad
                most_freq_unit = ""
                for unit_col in ['Weight Unit', 'Distance Unit']:
                    if unit_col in ex_df.columns:
                        units = ex_df[unit_col].dropna()
                        if not units.empty:
                            most_freq_unit = units.mode().iloc[0]
                            break
                
                if most_freq_unit and str(most_freq_unit).strip() != "":
                    st.markdown(f"**{exercise} ({most_freq_unit})**")
                else:
                    st.markdown(f"**{exercise}**")
                
                for idx, row in ex_df.iterrows():
                    is_cardio = pd.notna(row.get('Distance')) or pd.notna(row.get('Time'))
                    
                    if is_cardio:
                        col1, col2, col_btn = st.columns([2, 2, 1])
                        curr_dist = format_clean(row['Distance'])
                        curr_time = str(row['Time']) if pd.notna(row['Time']) else ""
                        
                        with col1:
                            new_dist = st.number_input("Distancia", value=curr_dist, step=0.1, format="%.1f", key=f"dist_{idx}_{selected_date}", label_visibility="collapsed")
                        with col2:
                            new_time = st.text_input("Duración", value=curr_time, key=f"time_{idx}_{selected_date}", label_visibility="collapsed")
                        with col_btn:
                            if st.button("💾", key=f"save_c_{idx}_{selected_date}"):
                                df.loc[idx, 'Distance'] = new_dist if new_dist > 0 else None
                                df.loc[idx, 'Time'] = new_time if new_time else None
                                save_data(df)
                                st.rerun()
                    else:
                        # Distribución visual para dar espacio a los badges de récords
                        col_w, col_r, col_badges, col_btn = st.columns([1.8, 1.8, 1.4, 0.9])
                        curr_w = format_clean(row['Weight'])
                        curr_r = int(row['Reps']) if pd.notna(row['Reps']) else 0
                        
                        with col_w:
                            new_w = st.number_input("Peso", value=curr_w, step=5.0, format="%.1f", key=f"w_{idx}_{selected_date}", label_visibility="collapsed")
                        with col_r:
                            new_r = st.number_input("Reps", value=int(curr_r), step=1, key=f"r_{idx}_{selected_date}", label_visibility="collapsed")
                        
                        with col_badges:
                            # Lógica para mostrar indicadores dinámicos basados en el input actual o guardado
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
                            else:
                                st.markdown("")

                        with col_btn:
                            if st.button("💾", key=f"save_w_{idx}_{selected_date}"):
                                df.loc[idx, 'Weight'] = new_w if new_w > 0 else None
                                df.loc[idx, 'Reps'] = new_r if new_r > 0 else None
                                save_data(df)
                                st.rerun()
                
                if st.button(f"➕ Agregar serie a {exercise}", key=f"add_row_{exercise}_{selected_date}"):
                    is_cardio_ex = pd.notna(ex_df.iloc[0].get('Distance')) or pd.notna(ex_df.iloc[0].get('Time'))
                    new_row = {
                        'Date': selected_date, 'Exercise': exercise, 'Category': category,
                        'Weight Unit': most_freq_unit if not is_cardio_ex else None
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(df)
                    st.rerun()
                st.divider()
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
    # Obtener fechas únicas que tengan registros ordenadas de más reciente a más antigua
    if not df.empty and 'Date' in df.columns:
        valid_df = df.dropna(subset=['Date']).copy()
        valid_df['Date_Only'] = valid_df['Date'].dt.date
        
        # Crear un diccionario o lista de fechas con sus categorías correspondientes
        date_summary = []
        for d in sorted(valid_df['Date_Only'].unique(), reverse=True):
            cats = valid_df[valid_df['Date_Only'] == d]['Category'].dropna().unique()
            cats_str = ", ".join(cats) if len(cats) > 0 else "Sin categoría"
            date_summary.append((d, f"{d.strftime('%d/%m/%Y')} — 🦾 [{cats_str}]"))
            
        if date_summary:
            # Extraer solo las tuplas de fechas y las etiquetas formateadas
            dates_only = [item[0] for item in date_summary]
            date_labels = [item[1] for item in date_summary]
            
            selected_label_idx = st.selectbox(
                "Selecciona la fecha a copiar:", 
                range(len(dates_only)), 
                format_func=lambda x: date_labels[x],
                key="copy_date_select"
            )
            s_date = pd.to_datetime(dates_only[selected_label_idx])
            
            # Filtrar y previsualizar los ejercicios del día seleccionado
            source_entries = df[df['Date'].dt.date == s_date.date()].copy()
            
            if not source_entries.empty:
                st.write(f"Vista previa de la rutina:")
                preview_df = source_entries[['Category', 'Exercise', 'Weight', 'Reps', 'Distance']].drop_duplicates()
                st.dataframe(preview_df, use_container_width=True, hide_index=True)
                
                if st.button("Copiar rutina seleccionada", key="btn_confirm_copy"):
                    new_entries = source_entries.copy()
                    new_entries['Date'] = selected_date
                    save_data(pd.concat([df, new_entries], ignore_index=True))
                    st.success("¡Rutina copiada con éxito!")
                    st.rerun()
            else:
                st.warning("No hay registros en la fecha seleccionada.")
        else:
            st.info("No hay historial disponible para copiar.")
    else:
        st.warning("No hay datos en el sistema.")