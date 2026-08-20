import streamlit as st
import pandas as pd
import numpy as np
from utils import load_data, get_cached_date_summary

st.set_page_config(page_title="Historial por Fecha", layout="wide")
st.title("📊 Seguimiento de Sesión")

def calcular_estado_tendencia(ex_hist):
    """
    Normaliza a KG y calcula la tendencia de las últimas 4 sesiones 
    mediante regresión lineal (umbral de 0.45 kg ~ 1 lb).
    """
    if len(ex_hist) < 4:
        return "🌱 Nuevo / Pocos datos"
    
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
            
            # --- 1. BLOQUE DE FUERZA ---
            datos_fuerza = []
            ejercicios_fuerza = df_sesion[df_sesion['Weight'].notna() & df_sesion['Reps'].notna()]['Exercise'].unique()
            
            for ex in ejercicios_fuerza:
                # Todas las series del ejercicio en la fecha seleccionada
                series_dia = df_sesion[df_sesion['Exercise'] == ex].copy()
                
                # Calcular 1RM para cada serie del día y extraer la mejor
                series_dia['1RM_dia'] = series_dia.apply(
                    lambda row: row['Weight'] / (1.0278 - (0.0278 * row['Reps'])) if row['Reps'] > 0 else row['Weight'], 
                    axis=1
                )
                mejor_serie_dia = series_dia.loc[series_dia['1RM_dia'].idxmax()]
                
                # Historial completo para calcular el récord histórico (Best 1RM) y tendencia
                ex_hist = df[df['Exercise'] == ex].dropna(subset=['Weight', 'Reps']).sort_values('Date')
                ex_hist['1RM_calc'] = ex_hist.apply(
                    lambda row: row['Weight'] / (1.0278 - (0.0278 * row['Reps'])) if row['Reps'] > 0 else row['Weight'], 
                    axis=1
                )
                mejor_1rm_historico = ex_hist['1RM_calc'].max()
                
                datos_fuerza.append({
                    "Ejercicio": ex,
                    "Peso (Día)": mejor_serie_dia['Weight'],
                    "Reps (Día)": int(mejor_serie_dia['Reps']),
                    "Best 1RM": round(mejor_1rm_historico, 1),
                    "5RM (Obj)": round(mejor_1rm_historico * 0.87, 1),
                    "10RM (Obj)": round(mejor_1rm_historico * 0.75, 1),
                    "Estado": calcular_estado_tendencia(ex_hist)
                })
            
            if datos_fuerza:
                st.markdown("### 🏋️ Ejercicios de Fuerza")
                st.dataframe(
                    pd.DataFrame(datos_fuerza).set_index("Ejercicio"),
                    use_container_width=True,
                    column_config={
                        "Peso (Día)": st.column_config.NumberColumn("Peso (Día)", format="%.1f"),
                        "Best 1RM": st.column_config.NumberColumn("Best 1RM", format="%.1f"),
                        "5RM (Obj)": st.column_config.NumberColumn("5RM (Obj)", format="%.1f"),
                        "10RM (Obj)": st.column_config.NumberColumn("10RM (Obj)", format="%.1f"),
                    }
                )

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
                    "Duración": str(tiempo),
                    "Detalle": f"{distancia} km en {tiempo}" if pd.notna(distancia) else "-"
                })
                
            if datos_cardio:
                st.markdown("### 🏃 Ejercicios de Cardio / Resistencia")
                st.dataframe(pd.DataFrame(datos_cardio).set_index("Ejercicio"), use_container_width=True)
                
        else:
            st.warning("No hay registros en la fecha seleccionada.")
    else:
        st.info("No hay historial disponible.")
else:
    st.info("No hay datos cargados para analizar.")