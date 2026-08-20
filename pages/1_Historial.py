import streamlit as st
import pandas as pd
import numpy as np
from utils import load_data, get_cached_date_summary

st.set_page_config(page_title="Historial por Fecha", layout="wide")
st.title("📊 Seguimiento de Sesión")

def calcular_estado_tendencia(ex_hist):
    if len(ex_hist) < 4:
        return "🌱 Pocos datos"
    
    ultimas_4 = ex_hist.dropna(subset=['Weight']).tail(4)
    if len(ultimas_4) < 4:
        return "🌱 Pocos datos"
    
    pesos_kg = []
    for _, row in ultimas_4.iterrows():
        peso = row['Weight']
        unidad = str(row.get('Weight Unit', 'lb')).lower()
        if 'lb' in unidad:
            pesos_kg.append(peso * 0.453592)
        else:
            pesos_kg.append(peso)
    
    pesos_kg = np.array(pesos_kg)
    x = np.arange(len(pesos_kg))
    pendiente_kg, _ = np.polyfit(x, pesos_kg, 1)
    
    if pendiente_kg > 0.45:
        return "🚀 Subiendo"
    elif pendiente_kg < -0.45:
        return "🔋 Descarga"
    else:
        return "⚠️ Meseta"

df = load_data()

if not df.empty and 'Date' in df.columns:
    date_summary = get_cached_date_summary(df)
    
    if date_summary:
        dates_only = [item[0] for item in date_summary]
        date_labels = [item[1] for item in date_summary]
        
        selected_label_idx = st.selectbox(
            "Selecciona la fecha de entrenamiento a evaluar:", 
            range(len(dates_only)), 
            format_func=lambda x: date_labels[x]
        )
        target_date = pd.to_datetime(dates_only[selected_label_idx])
        
        df_sesion = df[df['Date'].dt.date == target_date.date()].copy()
        
        if not df_sesion.empty:
            st.divider()
            st.subheader(f"Resumen de la Sesión: {target_date.strftime('%d/%m/%Y')}")
            
            datos_fuerza = []
            datos_alta_rep = []
            ejercicios_fuerza = df_sesion[df_sesion['Weight'].notna() & df_sesion['Reps'].notna()]['Exercise'].unique()
            
            for ex in ejercicios_fuerza:
                series_dia = df_sesion[df_sesion['Exercise'] == ex].copy()
                
                series_dia['1RM_dia'] = series_dia.apply(
                    lambda row: row['Weight'] / (1.0278 - (0.0278 * row['Reps'])) if row['Reps'] > 0 else row['Weight'], 
                    axis=1
                )
                mejor_serie_dia = series_dia.loc[series_dia['1RM_dia'].idxmax()]
                
                reps_dia = int(mejor_serie_dia['Reps'])
                peso_dia = mejor_serie_dia['Weight']
                
                ex_hist = df[df['Exercise'] == ex].dropna(subset=['Weight', 'Reps']).sort_values('Date')
                estado_tendencia = calcular_estado_tendencia(ex_hist)
                
                if reps_dia > 20:
                    volumen_dia = peso_dia * reps_dia
                    ex_hist['Volumen_hist'] = ex_hist['Weight'] * ex_hist['Reps']
                    mejor_volumen_historico = ex_hist['Volumen_hist'].max()
                    
                    datos_alta_rep.append({
                        "Ejercicio": ex,
                        "Peso (Día)": peso_dia,
                        "Reps (Día)": reps_dia,
                        "Volumen (Día)": round(volumen_dia, 1),
                        "Best Volumen": round(mejor_volumen_historico, 1),
                        "Estado": estado_tendencia
                    })
                else:
                    ex_hist['1RM_calc'] = ex_hist.apply(
                        lambda row: row['Weight'] / (1.0278 - (0.0278 * row['Reps'])) if row['Reps'] > 0 else row['Weight'], 
                        axis=1
                    )
                    mejor_1rm_historico = ex_hist['1RM_calc'].max()
                    
                    datos_fuerza.append({
                        "Ejercicio": ex,
                        "Peso (Día)": peso_dia,
                        "Reps (Día)": reps_dia,
                        "Best 1RM": round(mejor_1rm_historico, 1),
                        "5RM": round(mejor_1rm_historico * 0.87, 1),
                        "10RM": round(mejor_1rm_historico * 0.75, 1),
                        "Estado": estado_tendencia
                    })
            
            # --- RENDERIZAR FUERZA TRADICIONAL EN TARJETAS ---
            if datos_fuerza:
                st.markdown("### 🏋️ Ejercicios de Fuerza")
                for item in datos_fuerza:
                    with st.container(border=True):
                        st.markdown(f"**{item['Ejercicio']}** &nbsp;&nbsp; `{item['Estado']}`")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Peso Día", f"{item['Peso (Día)']} kg/lb")
                        c2.metric("Reps Día", item['Reps (Día)'])
                        c3.metric("Best 1RM", f"{item['Best 1RM']}")
                        c4.metric("5RM / 10RM", f"{item['5RM']} / {item['10RM']}")

            # --- RENDERIZAR ALTA REPETICIÓN EN TARJETAS ---
            if datos_alta_rep:
                st.markdown("### 🔥 Alta Repetición / Resistencia (>20 Reps)")
                for item in datos_alta_rep:
                    with st.container(border=True):
                        st.markdown(f"**{item['Ejercicio']}** &nbsp;&nbsp; `{item['Estado']}`")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Peso / Reps", f"{item['Peso (Día)']} × {item['Reps (Día)']}")
                        c2.metric("Volumen Día", f"{item['Volumen (Día)']}")
                        c3.metric("Best Volumen", f"{item['Best Volumen']}")

            # --- 2. BLOQUE DE CARDIO ---
            datos_cardio = []
            ejercicios_cardio = df_sesion[df_sesion['Distance'].notna() | df_sesion['Time'].notna()]['Exercise'].unique()
            
            for ex in ejercicios_cardio:
                row = df_sesion[df_sesion['Exercise'] == ex].iloc[-1]
                distancia = row.get('Distance')
                tiempo = row.get('Time', '-')
                
                datos_cardio.append({
                    "Ejercicio": ex,
                    "Distancia": f"{distancia} km" if pd.notna(distancia) else "-",
                    "Duración": str(tiempo)
                })
                
            if datos_cardio:
                st.markdown("### 🏃 Ejercicios de Cardio / Resistencia")
                for item in datos_cardio:
                    with st.container(border=True):
                        st.markdown(f"**{item['Ejercicio']}**")
                        c1, c2 = st.columns(2)
                        c1.metric("Distancia", item['Distancia'])
                        c2.metric("Duración", item['Duración'])
                
        else:
            st.warning("No hay registros en la fecha seleccionada.")
    else:
        st.info("No hay historial disponible.")
else:
    st.info("No hay datos cargados para analizar.")