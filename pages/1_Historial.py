import streamlit as st
import pandas as pd
import numpy as np
from utils import load_data

st.set_page_config(page_title="Historial Avanzado", layout="wide")
st.title("📊 Análisis de Entrenamiento Avanzado")

df = load_data()
if not df.empty:
    categorias = sorted(df['Category'].dropna().unique())
    selected_cat = st.selectbox("Filtro: Selecciona grupo muscular", categorias)
    df_cat = df[df['Category'] == selected_cat].copy()
    df_cat['Tonelaje'] = df_cat['Weight'] * df_cat['Reps']
    
    tab1, tab2, tab3 = st.tabs(["⚖️ Volumen y Fatiga", "⚠️ Alertas de Meseta", "📈 Seguimiento y RM"])

    with tab1:
        st.subheader("Volumen Sostenido vs Fatiga")
        # Media móvil de 3 sesiones para ver la tendencia real sin el ruido del día a día
        df_cat['Vol_Movil'] = df_cat.groupby('Exercise')['Tonelaje'].transform(lambda x: x.rolling(3, min_periods=1).mean())
        st.area_chart(df_cat.pivot_table(index='Date', columns='Exercise', values='Vol_Movil', aggfunc='sum'))
        st.caption("Gráfico: Volumen acumulado por sesión con suavizado de 3 sesiones. Si el área es plana o cae tras picos altos, hay fatiga excesiva.")

    with tab2:
        st.subheader("Detección de Estancamientos (Mesetas)")
        # Lógica: Si el peso no sube en 4 sesiones seguidas, es una meseta
        for ex in df_cat['Exercise'].unique():
            ex_data = df_cat[df_cat['Exercise'] == ex].sort_values('Date')
            if len(ex_data) >= 4:
                ultimos_pesos = ex_data['Weight'].tail(4).values
                if len(set(ultimos_pesos)) == 1: # Mismo peso 4 veces seguidas
                    st.warning(f"⚠️ Meseta detectada en **{ex}**: Peso estancado en {ultimos_pesos[-1]}kg")
        
    with tab3:
        st.subheader("Estimaciones de Fuerza (RM)")
        ejercicios_cat = sorted(df_cat['Exercise'].dropna().unique())
        selected_ex = st.selectbox("Ejercicio:", ejercicios_cat)
        
        data_ex = df_cat[df_cat['Exercise'] == selected_ex].dropna(subset=['Weight', 'Reps'])
        
        # Fórmulas de estimación
        # 1RM (Epley), 10RM (estimado inverso aprox)
        data_ex['1RM'] = data_ex['Weight'] * (1 + data_ex['Reps'] / 30)
        data_ex['10RM'] = data_ex['1RM'] * 0.75 
        
        st.line_chart(data_ex.set_index('Date')[['1RM', '10RM']])
        
        st.write("### Resumen actual")
        last_session = data_ex.iloc[-1]
        st.metric("1RM Estimado Actual", f"{last_session['1RM']:.1f} kg")
        st.metric("10RM Estimado", f"{last_session['10RM']:.1f} kg")

else:
    st.info("No hay datos suficientes.")