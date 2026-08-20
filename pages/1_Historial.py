import streamlit as st
import pandas as pd
import numpy as np
from utils import load_data, get_cached_date_summary

st.set_page_config(page_title="Historial por Fecha", layout="wide")
st.title("📊 Seguimiento de Sesión")

def calcular_estado_tendencia(ex_hist):
    """
    Normaliza a KG antes de calcular la pendiente (regresión lineal) 
    de las últimas 4 sesiones para evaluar si está Subiendo, en Descarga o en Meseta.
    """
    if len(ex_hist) < 4:
        return "🌱 Nuevo / Pocos datos"
    
    # Tomar las últimas 4 sesiones con datos válidos de peso
    ultimas_4 = ex_hist.dropna(subset=['Weight']).tail(4)
    if len(ultimas_4) < 4:
        return "🌱 Pocos datos"
    
    pesos_kg = []
    for _, row in ultimas_4.iterrows():
        peso = row['Weight']
        # Identificar la unidad si existe en el registro (por defecto busca 'Weight Unit')
        unidad = str(row.get('Weight Unit', 'lb')).lower()
        
        # Conversión inteligente a KG si está en libras
        if 'lb' in unidad:
            pesos_kg.append(peso * 0.453592)
        else:
            pesos_kg.append(peso)
    
    pesos_kg = np.array(pesos_kg)
    x = np.arange(len(pesos_kg))
    
    # Calcular pendiente (m) de la línea de regresión: y = mx + b
    pendiente_kg, _ = np.polyfit(x, pesos_kg, 1)
    
    # Umbral de 0.45 kg (~1 lb por sesión)
    UMBRAL_KG = 0.45 
    
    if pendiente_kg > UMBRAL_KG:
        return "🚀 Subiendo"
    elif pendiente_kg < -UMBRAL_KG:
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
                
                # --- 1. TABLA DE FUERZA (Peso / Reps) ---
                datos_fuerza = []
                for ex in cat_df['Exercise'].dropna().unique():
                    ex_hist = df[df['Exercise'] == ex].dropna(subset=['Weight', 'Reps']).sort_values('Date')
                    ex_current = cat_df[cat_df['Exercise'] == ex].dropna(subset=['Weight', 'Reps'])
                    
                    if not ex_current.empty:
                        last_row = ex_current.iloc[-1]
                        peso = last_row['Weight']
                        reps = last_row['Reps']
                        
                        # Fórmulas de estimación de Fuerza (Brzycki)
                        if reps > 0:
                            rm1 = peso / (1.0278 - (0.0278 * reps))
                        else:
                            rm1 = peso
                            
                        rm5 = rm1 * 0.87
                        rm10 = rm1 * 0.75
                        
                        # Evaluar tendencia matemática considerando la unidad
                        estado_tendencia = calcular_estado_tendencia(ex_hist)
                        
                        datos_fuerza.append({
                            "Ejercicio": ex,
                            "Peso": peso,
                            "Reps": int(reps),
                            "1RM": round(rm1, 1),
                            "5RM": round(rm5, 1),
                            "10RM": round(rm10, 1),
                            "Estado": estado_tendencia
                        })
                
                if datos_fuerza:
                    st.markdown("🏋️ **Ejercicios de Fuerza**")
                    df_f = pd.DataFrame(datos_fuerza)
                    st.dataframe(
                        df_f.set_index("Ejercicio"),
                        use_container_width=True,
                        column_config={
                            "Peso": st.column_config.NumberColumn("Peso", format="%.1f"),
                            "1RM": st.column_config.NumberColumn("1RM", format="%.1f"),
                            "5RM": st.column_config.NumberColumn("5RM", format="%.1f"),
                            "10RM": st.column_config.NumberColumn("10RM", format="%.1f"),
                        }
                    )

                # --- 2. TABLA DE CARDIO (Distancia / Duración) ---
                datos_cardio = []
                for ex in cat_df['Exercise'].dropna().unique():
                    ex_current = cat_df[cat_df['Exercise'] == ex]
                    cardio_rows = ex_current[ex_current['Distance'].notna() | ex_current['Time'].notna()]
                    
                    for _, row in cardio_rows.iterrows():
                        distancia = row.get('Distance', 0)
                        tiempo_str = str(row.get('Time', ''))
                        
                        velocidad_txt = "-"
                        try:
                            d_val = float(distancia) if pd.notna(distancia) else 0.0
                            if d_val > 0 and tiempo_str:
                                velocidad_txt = f"{d_val} km en {tiempo_str}"
                        except:
                            pass

                        datos_cardio.append({
                            "Ejercicio": ex,
                            "Distancia": f"{distancia} km" if pd.notna(distancia) else "-",
                            "Duración": tiempo_str if tiempo_str else "-",
                            "Detalle / Métrica": velocidad_txt
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