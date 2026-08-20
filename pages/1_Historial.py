import streamlit as st
import pandas as pd
from utils import load_data

st.set_page_config(page_title="Historial", layout="wide")

st.title("📊 Análisis de Entrenamiento")

df = load_data()

if not df.empty:
    # 1. Filtro inicial por Grupo Muscular (Categoría)
    st.subheader("Filtro de Análisis")
    categorias = sorted(df['Category'].dropna().unique())
    selected_cat = st.selectbox("Selecciona el grupo muscular a evaluar:", categorias)
    
    # Filtrar datos por la categoría seleccionada
    df_cat = df[df['Category'] == selected_cat].copy()
    df_cat['Tonelaje'] = df_cat['Weight'] * df_cat['Reps']
    
    st.divider()
    
    tab1, tab2, tab3 = st.tabs(["⚖️ Volumen y Tonelaje", "📈 Progresión por Ejercicio", "🏆 Salón de la Fama"])

    with tab1:
        st.subheader(f"Carga de Trabajo: {selected_cat}")
        df_cat['Semana'] = df_cat['Date'].dt.to_period('W').dt.start_time
        volumen_semanal = df_cat.groupby(['Semana', 'Exercise'])['Tonelaje'].sum().unstack().fillna(0)
        st.bar_chart(volumen_semanal)

    with tab2:
        st.subheader("Tendencia de Fuerza (1RM Estimado)")
        # Solo ejercicios que pertenecen a esta categoría
        ejercicios_cat = sorted(df_cat['Exercise'].dropna().unique())
        selected_ex = st.selectbox("Selecciona ejercicio del grupo:", ejercicios_cat)
        
        ex_data = df_cat[df_cat['Exercise'] == selected_ex].dropna(subset=['Weight', 'Reps']).sort_values('Date')
        
        if not ex_data.empty:
            # Fórmula de Brzycki
            ex_data['1RM_Est'] = ex_data['Weight'] / (1.0278 - 0.0278 * ex_data['Reps'])
            st.line_chart(ex_data.set_index('Date')['1RM_Est'])
        else:
            st.info("No hay suficientes datos de fuerza para este ejercicio.")

    with tab3:
        st.subheader(f"Mejores Marcas en {selected_cat}")
        pr_df = df_cat.groupby('Exercise')[['Weight', 'Reps']].max().reset_index()
        st.dataframe(pr_df, use_container_width=True)

else:
    st.info("No hay datos cargados para analizar.")