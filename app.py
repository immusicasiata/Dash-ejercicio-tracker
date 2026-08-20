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

selected_date = st.date_input("Selecciona una fecha:", pd.to_datetime("today"))
selected_date = pd.to_datetime(selected_date)

daily_df = df[df['Date'].dt.date == selected_date.date()]

if not daily_df.empty:
    st.subheader(f"Entrenamiento del {selected_date.strftime('%d/%m/%Y')}")
    
    for category in daily_df['Category'].unique():
        with st.expander(f"💪 {category}", expanded=True):
            cat_df = daily_df[daily_df['Category'] == category]
            
            for exercise in cat_df['Exercise'].unique():
                ex_df = cat_df[cat_df['Exercise'] == exercise]
                st.markdown(f"**{exercise}**")
                
                # LÓGICA CONDICIONAL: ¿Es fuerza o es cardio?
                # Si hay datos en 'Distance' o 'Time', mostramos esas columnas
                if ex_df['Distance'].notna().any() or ex_df['Time'].notna().any():
                    cols_to_show = ['Distance', 'Distance Unit', 'Time']
                    df_display = ex_df[cols_to_show].rename(columns={
                        'Distance': 'Distancia', 
                        'Distance Unit': 'Unidad', 
                        'Time': 'Duración'
                    })
                else:
                    # Si no hay cardio, mostramos peso y reps
                    cols_to_show = ['Weight', 'Weight Unit', 'Reps']
                    df_display = ex_df[cols_to_show].rename(columns={
                        'Weight': 'Peso', 
                        'Weight Unit': 'Unidad', 
                        'Reps': 'Repeticiones'
                    })
                
                st.table(df_display.reset_index(drop=True))
else:
    st.info("No hay registros de entrenamiento para la fecha seleccionada.")