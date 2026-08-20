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

def format_clean(val):
    """Convierte a entero si es un número, de lo contrario devuelve el string."""
    try:
        f_val = float(val)
        return int(f_val) if f_val.is_integer() else f_val
    except:
        return val

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
                
                # 1. Determinar la unidad más frecuente para el título
                unit_cols = ['Weight Unit', 'Distance Unit']
                all_units = ex_df[unit_cols].stack().dropna()
                most_freq_unit = all_units.mode().iloc[0] if not all_units.empty else ""
                
                # 2. Definir Título
                title = f"{exercise} ({most_freq_unit})" if most_freq_unit else exercise
                st.markdown(f"**{title}**")
                
                # 3. Preparar columnas y limpiar formato
                if ex_df['Distance'].notna().any() or ex_df['Time'].notna().any():
                    df_display = ex_df[['Distance', 'Time']].rename(columns={
                        'Distance': 'Distancia', 
                        'Time': 'Duración'
                    })
                else:
                    df_display = ex_df[['Weight', 'Reps']].rename(columns={
                        'Weight': 'Peso', 
                        'Reps': 'Repeticiones'
                    })
                
                # Aplicar redondeo/formateo a todo el DF
                df_display = df_display.applymap(format_clean)
                
                st.table(df_display.reset_index(drop=True))
else:
    st.info("No hay registros de entrenamiento para la fecha seleccionada.")