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
                
                # 3. Selección estricta de columnas
                if ex_df['Distance'].notna().any() or ex_df['Time'].notna().any():
                    cols = ['Distance', 'Time']
                    display_names = {'Distance': 'Distancia', 'Time': 'Duración'}
                else:
                    cols = ['Weight', 'Reps']
                    display_names = {'Weight': 'Peso', 'Reps': 'Repeticiones'}
                
                to_edit = ex_df[cols].rename(columns=display_names)
                to_edit = to_edit.map(format_clean)
                
                # 4. Editor interactivo con hide_index=True
                edited_ex = st.data_editor(
                    to_edit, 
                    use_container_width=True, 
                    num_rows="dynamic",
                    hide_index=True,
                    key=f"editor_{exercise}_{selected_date}"
                )
                
                # 5. Botón de guardado
                if st.button(f"Guardar {exercise}", key=f"btn_{exercise}"):
                    updated_ex = edited_ex.rename(columns={v: k for k, v in display_names.items()})
                    df.loc[ex_df.index, cols] = updated_ex
                    save_data(df)
                    st.success(f"¡{exercise} actualizado!")
                    st.rerun()
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