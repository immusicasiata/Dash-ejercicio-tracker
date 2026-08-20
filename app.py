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
    except: return pd.DataFrame()

def save_data(df):
    conn.update(data=df)
    st.cache_data.clear()

st.title("📅 Panel de Entrenamiento")
df = load_data()

# 1. Selector de fecha
selected_date = st.date_input("Selecciona fecha:", pd.to_datetime("today"))
selected_date = pd.to_datetime(selected_date)

# 2. PANEL DE EDICIÓN (Reemplaza la visualización estática)
st.subheader(f"Registros del {selected_date.strftime('%d/%m/%Y')}")
daily_df = df[df['Date'].dt.date == selected_date.date()].copy()

if not daily_df.empty:
    # Columnas editables directamente
    cols_to_edit = ['Exercise', 'Category', 'Weight', 'Reps', 'Distance', 'Time', 'Comment']
    edited_df = st.data_editor(daily_df[cols_to_edit], use_container_width=True)
    
    if st.button("Guardar cambios en esta fecha"):
        # Actualizamos el DF principal
        df.loc[daily_df.index, cols_to_edit] = edited_df
        save_data(df)
        st.success("Cambios guardados.")
        st.rerun()
else:
    st.info("No hay registros.")

# 3. FUNCIONALIDAD DE COPIAR RUTINA
st.divider()
with st.expander("🔄 Copiar rutina de otro día"):
    source_date = st.date_input("Fecha a copiar:", pd.to_datetime("today") - pd.Timedelta(days=1))
    source_df = df[df['Date'].dt.date == pd.to_datetime(source_date).date()]
    
    if not source_df.empty:
        st.write("Vista previa de la rutina a copiar:")
        st.table(source_df[['Exercise', 'Category', 'Weight', 'Reps', 'Distance', 'Time']])
        
        if st.button("Copiar esta rutina al día seleccionado"):
            new_entries = source_df.copy()
            new_entries['Date'] = selected_date
            save_data(pd.concat([df, new_entries], ignore_index=True))
            st.success("Rutina copiada.")
            st.rerun()
    else:
        st.warning("No hay datos en esa fecha.")