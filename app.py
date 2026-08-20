import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Panel de Control", page_icon="📅", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        df = conn.read()
        df['Date'] = pd.to_datetime(df['Date'])
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame()

st.title("📅 Panel de Entrenamiento")
df = load_data()

# Selector de fecha
selected_date = st.date_input("Selecciona una fecha para ver tu entrenamiento:", pd.to_datetime("today"))
selected_date = pd.to_datetime(selected_date)

# Filtrar datos
daily_df = df[df['Date'].dt.date == selected_date.date()]

if not daily_df.empty:
    st.subheader(f"Entrenamiento del {selected_date.strftime('%d/%m/%Y')}")
    
    # Agrupar por categoría (Grupo Muscular)
    for category in daily_df['Category'].unique():
        with st.expander(f"💪 {category}", expanded=True):
            cat_df = daily_df[daily_df['Category'] == category]
            
            # Agrupar por ejercicio para ver las series
            for exercise in cat_df['Exercise'].unique():
                ex_df = cat_df[cat_df['Exercise'] == exercise]
                st.markdown(f"**{exercise}**")
                
                # Mostrar tabla simplificada de series
                st.table(ex_df[['Weight', 'Weight Unit', 'Reps', 'Comment']].rename(
                    columns={'Weight': 'Peso', 'Weight Unit': 'Unidad', 'Reps': 'Reps', 'Comment': 'Nota'}
                ))
else:
    st.info("No hay registros de entrenamiento para la fecha seleccionada.")