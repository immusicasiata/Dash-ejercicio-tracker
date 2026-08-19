import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Historial de Entrenamientos", page_icon="📊", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        df = conn.read()
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Error al leer de Google Sheets: {e}")
        return pd.DataFrame()

st.title("📊 Historial de Entrenamientos")

with st.spinner('Obteniendo datos...'):
    df = load_data()

if not df.empty:
    search_term = st.text_input("🔍 Buscar ejercicio específico:")
    if search_term:
        df_display = df[df['Exercise'].str.contains(search_term, case=False, na=False)]
    else:
        df_display = df
        
    st.dataframe(df_display.sort_values(by="Date", ascending=False), use_container_width=True)
    
    if 'Weight' in df.columns:
        st.divider()
        st.subheader("📈 Tendencia de Progresión")
        df['Weight'] = pd.to_numeric(df['Weight'], errors='coerce')
        
        top_exercises = df['Exercise'].value_counts().head(10).index
        selected_ex = st.selectbox("Selecciona un ejercicio para ver tu progresión de peso", top_exercises)
        
        ex_data = df[df['Exercise'] == selected_ex].copy()
        if not ex_data.empty:
            ex_data['Date'] = pd.to_datetime(ex_data['Date'])
            daily_max = ex_data.groupby('Date')['Weight'].max().reset_index()
            st.line_chart(daily_max.set_index('Date')['Weight'])
else:
    st.info("No hay datos de entrenamiento o la hoja está vacía.")