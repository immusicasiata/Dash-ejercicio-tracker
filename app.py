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
        return df.dropna(how='all')
    except: 
        return pd.DataFrame()

def save_data(df):
    conn.update(data=df)
    st.cache_data.clear()

def format_clean(val):
    try:
        f_val = float(val)
        return int(f_val) if f_val.is_integer() else f_val
    except: 
        return val

st.title("📅 Panel de Entrenamiento")
df = load_data()

# Selector de fecha principal
selected_date = st.date_input("Selecciona fecha:", pd.to_datetime("today"))
selected_date = pd.to_datetime(selected_date)

# Filtrar para el día seleccionado
daily_df = df[df['Date'].dt.date == selected_date.date()].copy()

if not daily_df.empty:
    st.subheader(f"Registros del {selected_date.strftime('%d/%m/%Y')}")
    
    # Agrupamos por categoría (Grupo Muscular)
    for category in daily_df['Category'].unique():
        with st.expander(f"💪 {category}", expanded=True):
            cat_df = daily_df[daily_df['Category'] == category]
            
            for exercise in cat_df['Exercise'].unique():
                ex_df = cat_df[cat_df['Exercise'] == exercise]
                
                # 1. Obtener la unidad con lógica robusta
                most_freq_unit = ""
                for unit_col in ['Weight Unit', 'Distance Unit']:
                    if unit_col in ex_df.columns:
                        units = ex_df[unit_col].dropna()
                        if not units.empty:
                            most_freq_unit = units.mode().iloc[0]
                            break
                
                if not most_freq_unit and 'Exercise' in df.columns:
                    hist_ex = df[df['Exercise'] == exercise]
                    for unit_col in ['Weight Unit', 'Distance Unit']:
                        if unit_col in hist_ex.columns:
                            units = hist_ex[unit_col].dropna()
                            if not units.empty:
                                most_freq_unit = units.mode().iloc[0]
                                break

                # 2. Definir Título
                if most_freq_unit and str(most_freq_unit).strip() != "":
                    st.markdown(f"**{exercise} ({most_freq_unit})**")
                else:
                    st.markdown(f"**{exercise}**")
                
                # 3. Interfaz táctil optimizada por cada serie existente
                for idx, row in ex_df.iterrows():
                    is_cardio = pd.notna(row.get('Distance')) or pd.notna(row.get('Time'))
                    
                    if is_cardio:
                        col1, col2, col_btn = st.columns([2, 2, 1])
                        curr_dist = format_clean(row['Distance']) if pd.notna(row['Distance']) else 0.0
                        curr_time = str(row['Time']) if pd.notna(row['Time']) else ""
                        
                        with col1:
                            new_dist = st.number_input("Distancia", value=float(curr_dist), step=0.1, key=f"dist_{idx}_{selected_date}", label_visibility="collapsed")
                        with col2:
                            new_time = st.text_input("Duración", value=curr_time, key=f"time_{idx}_{selected_date}", label_visibility="collapsed")
                        with col_btn:
                            if st.button("💾", key=f"save_c_{idx}_{selected_date}"):
                                df.loc[idx, 'Distance'] = new_dist if new_dist > 0 else None
                                df.loc[idx, 'Time'] = new_time if new_time else None
                                save_data(df)
                                st.success("¡Guardado!")
                                st.rerun()
                    else:
                        col1, col2, col_btn = st.columns([2, 2, 1])
                        w_val = format_clean(row['Weight']) if pd.notna(row['Weight']) else 0
                        is_int_w = isinstance(w_val, int)
                        
                        curr_r = int(row['Reps']) if pd.notna(row['Reps']) else 0
                        
                        with col1:
                            new_w = st.number_input(
                                "Peso", 
                                value=int(w_val) if is_int_w else float(w_val), 
                                step=5.0, 
                                format="%d" if is_int_w else "%.1f",
                                key=f"w_{idx}_{selected_date}", 
                                label_visibility="collapsed"
                            )
                        with col2:
                            new_r = st.number_input("Reps", value=int(curr_r), step=1, format="%d", key=f"r_{idx}_{selected_date}", label_visibility="collapsed")
                        with col_btn:
                            if st.button("💾", key=f"save_w_{idx}_{selected_date}"):
                                df.loc[idx, 'Weight'] = new_w if new_w > 0 else None
                                df.loc[idx, 'Reps'] = new_r if new_r > 0 else None
                                save_data(df)
                                st.success("¡Guardado!")
                                st.rerun()
                
                # 4. Botón para AGREGAR UNA NUEVA SERIE a este ejercicio
                if st.button(f"➕ Agregar serie a {exercise}", key=f"add_row_{exercise}_{selected_date}"):
                    is_cardio_ex = pd.notna(ex_df.iloc[0].get('Distance')) or pd.notna(ex_df.iloc[0].get('Time'))
                    
                    new_row = {
                        'Date': selected_date,
                        'Exercise': exercise,
                        'Category': category,
                        'Weight': None,
                        'Weight Unit': most_freq_unit if not is_cardio_ex else None,
                        'Reps': None,
                        'Distance': None,
                        'Distance Unit': most_freq_unit if is_cardio_ex else None,
                        'Time': None,
                        'Comment': None
                    }
                    
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(df)
                    st.success("¡Nueva serie añadida!")
                    st.rerun()
                
                st.divider()
else:
    st.info("No hay registros en esta fecha.")

# --- FUNCIONALIDAD DE COPIAR RUTINA ---
st.divider()
with st.expander("🔄 Copiar rutina de otro día"):
    source_date = st.date_input("Fecha a copiar:", pd.to_datetime("today") - pd.Timedelta(days=1))
    source_df = df[df['Date'].dt.date == pd.to_datetime(source_date).date()]
    
    if not source_df.empty:
        st.write("Vista previa de la rutina a copiar:")
        st.dataframe(
            source_df[['Exercise', 'Category', 'Weight', 'Reps', 'Distance', 'Time']], 
            use_container_width=True,
            hide_index=True
        )
        
        if st.button("Copiar esta rutina al día seleccionado"):
            new_entries = source_df.copy()
            new_entries['Date'] = selected_date
            save_data(pd.concat([df, new_entries], ignore_index=True))
            st.success("¡Rutina copiada exitosamente!")
            st.rerun()
    else:
        st.warning("No hay datos registrados en esa fecha para copiar.")