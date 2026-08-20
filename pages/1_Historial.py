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
        # Conversión a KG para consistencia
        if 'lb' in unidad:
            pesos_kg.append(peso * 0.453592)
        else:
            pesos_kg.append(peso)
    
    pesos_kg = np.array(pesos_kg)
    x = np.arange(len(pesos_kg))
    pendiente_kg, _ = np.polyfit(x, pesos_kg, 1)
    
    # Pendiente mayor a 0.45kg/sesión (~1 lb/sesión) indica tendencia
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
            
            categorias_sesion = sorted(df_sesion['Category'].dropna().unique())
            
            for cat in categorias_sesion:
                st.markdown(f"### 💪 {cat}")
                cat_df = df_sesion[df_sesion['Category'] == cat]
                
                # --- 1. TABLA DE FUERZA ---
                datos_fuerza = []
                for ex in cat_df['Exercise'].dropna().unique():
                    ex_hist = df[df['Exercise'] == ex].dropna(subset=['Weight', 'Reps']).sort_values('Date')
                    ex_current = cat_df[cat_df['Exercise'] == ex].dropna(subset=['Weight', 'Reps'])
                    
                    if not ex_current.empty:
                        last_row = ex_current.iloc[-1]
                        
                        # Cálculo del MEJOR RM histórico
                        ex_hist['1RM_calc'] = ex_hist.apply(
                            lambda row: row['Weight'] / (1.0278 - (0.0278 * row['Reps'])) if row['Reps'] > 0 else row['Weight'], 
                            axis=1
                        )
                        mejor_1rm_historico = ex_hist['1RM_calc'].max()
                        
                        # Tendencia basada en el peso real levantado (últimas 4 sesiones)
                        estado_tendencia = calcular_estado_tendencia(ex_hist)
                        
                        datos_fuerza.append({
                            "Ejercicio": ex,
                            "Peso (Día)": last_row['Weight'],
                            "Reps (Día)": int(last_row['Reps']),
                            "Best 1RM": round(mejor_1rm_historico, 1),
                            "5RM (Obj)": round(mejor_1rm_historico * 0.87, 1),
                            "10RM (Obj)": round(mejor_1rm_historico * 0.75, 1),
                            "Estado": estado_tendencia
                        })
                
                if datos_fuerza:
                    st.markdown("🏋️ **Ejercicios de Fuerza**")
                    df_f = pd.DataFrame(datos_fuerza)
                    st.dataframe(
                        df_f.set_index("Ejercicio"),
                        use_container_width=True,
                        column_config={
                            "Peso (Día)": st.column_config.NumberColumn("Peso (Día)", format="%.1f"),
                            "Best 1RM": st.column_config.NumberColumn("Best 1RM", format="%.1f"),
                            "5RM (Obj)": st.column_config.NumberColumn("5RM (Obj)", format="%.1f"),
                            "10RM (Obj)": st.column_config.NumberColumn("10RM (Obj)", format="%.1f"),
                        }
                    )

                # --- 2. TABLA DE CARDIO ---
                datos_cardio = []
                for ex in cat_df['Exercise'].dropna().unique():
                    ex_current = cat_df[cat_df['Exercise'] == ex]
                    cardio_rows = ex_current[ex_current['Distance'].notna() | ex_current['Time'].notna()]
                    
                    for _, row in cardio_rows.iterrows():
                        distancia = row.get('Distance', 0)
                        tiempo_str = str(row.get('Time', ''))
                        datos_cardio.append({
                            "Ejercicio": ex,
                            "Distancia": f"{distancia} km" if pd.notna(distancia) else "-",
                            "Duración": tiempo_str,
                            "Detalle": f"{distancia} km en {tiempo_str}" if (distancia and tiempo_str) else "-"
                        })
                
                if datos_cardio:
                    st.markdown("🏃 **Ejercicios de Cardio / Resistencia**")
                    df_c = pd.DataFrame(datos_cardio)
                    st.dataframe(df_c.set_index("Ejercicio"), use_container_width=True)
                
                st.write("")
        else:
            st.warning("No hay registros en la fecha seleccionada.")
    else:
        st.info("No hay historial disponible.")
else:
    st.info("No hay datos cargados para analizar.")