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
    
    # Pestañas de análisis
    tab1, tab2, tab3 = st.tabs(["📈 Seguimiento y RM", "⚖️ Volumen y Fatiga", "⚠️ Alertas de Meseta"])

    with tab1:
        st.subheader(f"Estado de Fuerza Actual — {selected_cat}")
        st.write("Estimaciones calculadas a partir del último registro de cada ejercicio:")
        
        ejercicios_cat = sorted(df_cat['Exercise'].dropna().unique())
        datos_sesion = []
        
        for ex in ejercicios_cat:
            ex_data = df_cat[df_cat['Exercise'] == ex].dropna(subset=['Weight', 'Reps']).sort_values('Date')
            
            if not ex_data.empty:
                last_row = ex_data.iloc[-1]
                peso = last_row['Weight']
                reps = last_row['Reps']
                
                # Fórmulas de estimación (Brzycki)
                if reps > 0:
                    rm1 = peso / (1.0278 - (0.0278 * reps))
                else:
                    rm1 = peso
                    
                rm5 = rm1 * 0.87
                rm10 = rm1 * 0.75
                
                # Chequeo de Meseta (últimas 4 sesiones con mismo peso)
                es_meseta = False
                if len(ex_data) >= 4:
                    ultimos_pesos = ex_data['Weight'].tail(4).values
                    if len(set(ultimos_pesos)) == 1 and ultimos_pesos[0] > 0:
                        es_meseta = True
                
                datos_sesion.append({
                    "Ejercicio": ex,
                    "Último Peso (kg)": peso,
                    "Últimas Reps": int(reps),
                    "1RM": round(rm1, 1),
                    "5RM": round(rm5, 1),
                    "10RM": round(rm10, 1),
                    "Estado": "⚠️ Meseta" if es_meseta else "✅ Activo"
                })
        
        if datos_sesion:
            df_resumen = pd.DataFrame(datos_sesion)
            st.dataframe(
                df_resumen.set_index("Ejercicio"),
                use_container_width=True,
                column_config={
                    "Último Peso (kg)": st.column_config.NumberColumn("Último Peso (kg)", format="%.1f"),
                    "1RM": st.column_config.NumberColumn("1RM (kg)", format="%.1f"),
                    "5RM": st.column_config.NumberColumn("5RM (kg)", format="%.1f"),
                    "10RM": st.column_config.NumberColumn("10RM (kg)", format="%.1f"),
                }
            )
        else:
            st.info("No hay registros suficientes para calcular RM en este grupo muscular.")

    with tab2:
        st.subheader("Volumen Sostenido vs Fatiga")
        # Media móvil para ver tendencia real sin el ruido diario
        df_cat['Vol_Movil'] = df_cat.groupby('Exercise')['Tonelaje'].transform(lambda x: x.rolling(3, min_periods=1).mean())
        
        pivot_vol = df_cat.pivot_table(index='Date', columns='Exercise', values='Vol_Movil', aggfunc='sum')
        st.area_chart(pivot_vol)
        st.caption("Gráfico: Volumen acumulado suavizado (media móvil de 3 sesiones). Útil para ver si el tonelaje sube de forma sostenida sin fatiga excesiva.")

    with tab3:
        st.subheader("Detección Global de Estancamientos (Mesetas)")
        st.write("Analizando las últimas 4 sesiones registradas por ejercicio:")
        
        meseta_encontrada = False
        for ex in df_cat['Exercise'].unique():
            ex_data = df_cat[df_cat['Exercise'] == ex].sort_values('Date')
            if len(ex_data) >= 4:
                ultimos_pesos = ex_data['Weight'].tail(4).values
                if len(set(ultimos_pesos)) == 1 and ultimos_pesos[0] > 0: 
                    st.warning(f"⚠️ Meseta detectada en **{ex}**: El peso se ha mantenido estancado en {ultimos_pesos[-1]}kg durante las últimas 4 sesiones.")
                    meseta_encontrada = True
        
        if not meseta_encontrada:
            st.success("¡Excelente! No se detectaron estancamientos críticos en este grupo muscular.")

else:
    st.info("No hay datos cargados para analizar.")