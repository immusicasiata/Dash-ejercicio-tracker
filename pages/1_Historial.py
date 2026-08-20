import streamlit as st
import pandas as pd
from utils import load_data

st.set_page_config(page_title="Historial", layout="wide")
st.title("📊 Análisis de Entrenamiento")

df = load_data()
if not df.empty:
    df_ana = df.copy()
    df_ana['Tonelaje'] = df_ana['Weight'] * df_ana['Reps']
    
    tab1, tab2, tab3 = st.tabs(["⚖️ Volumen y Tonelaje", "📈 Progresión por Ejercicio", "🏆 Salón de la Fama"])

    with tab1:
        st.subheader("Carga de Trabajo Semanal")
        df_ana['Semana'] = df_ana['Date'].dt.to_period('W').dt.start_time
        volumen_semanal = df_ana.groupby(['Semana', 'Category'])['Tonelaje'].sum().unstack().fillna(0)
        st.bar_chart(volumen_semanal)

    with tab2:
        st.subheader("Tendencia de Fuerza (1RM Estimado)")
        ejercicios = sorted(df_ana['Exercise'].dropna().unique())
        selected_ex = st.selectbox("Selecciona ejercicio:", ejercicios)
        ex_data = df_ana[df_ana['Exercise'] == selected_ex].dropna(subset=['Weight', 'Reps']).sort_values('Date')
        ex_data['1RM_Est'] = ex_data['Weight'] / (1.0278 - 0.0278 * ex_data['Reps'])
        st.line_chart(ex_data.set_index('Date')['1RM_Est'])

    with tab3:
        st.subheader("Tus Mejores Marcas")
        pr_df = df_ana.groupby('Exercise')[['Weight', 'Reps']].max().reset_index()
        st.dataframe(pr_df, use_container_width=True)
else:
    st.info("No hay datos suficientes para mostrar el historial.")