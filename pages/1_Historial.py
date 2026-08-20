import streamlit as st
import pandas as pd
from utils import load_data, get_cached_date_summary

st.set_page_config(page_title="Historial por Fecha", layout="wide")
st.title("📊 Seguimiento de Sesión")

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
                        
                        if reps > 0:
                            rm1 = peso / (1.0278 - (0.0278 * reps))
                        else:
                            rm1 = peso
                            
                        rm5 = rm1 * 0.87
                        rm10 = rm1 * 0.75
                        
                        es_meseta = False
                        if len(ex_hist) >= 4:
                            ultimos_pesos = ex_hist['Weight'].tail(4).values
                            if len(set(ultimos_pesos)) == 1 and ultimos_pesos[0] > 0:
                                es_meseta = True
                        
                        datos_fuerza.append({
                            "Ejercicio": ex,
                            "Peso (kg)": peso,
                            "Reps": int(reps),
                            "1RM": round(rm1, 1),
                            "5RM": round(rm5, 1),
                            "10RM": round(rm10, 1),
                            "Estado": "⚠️ Meseta" if es_meseta else "✅ Activo"
                        })
                
                if datos_fuerza:
                    st.markdown("🏋️ **Ejercicios de Fuerza**")
                    df_f = pd.DataFrame(datos_fuerza)
                    st.dataframe(
                        df_f.set_index("Ejercicio"),
                        use_container_width=True,
                        column_config={
                            "Peso (kg)": st.column_config.NumberColumn("Peso (kg)", format="%.1f"),
                            "1RM": st.column_config.NumberColumn("1RM (kg)", format="%.1f"),
                            "5RM": st.column_config.NumberColumn("5RM (kg)", format="%.1f"),
                            "10RM": st.column_config.NumberColumn("10RM (kg)", format="%.1f"),
                        }
                    )

                # --- 2. TABLA DE CARDIO (Distancia / Duración) ---
                datos_cardio = []
                for ex in cat_df['Exercise'].dropna().unique():
                    ex_current = cat_df[cat_df['Exercise'] == ex]
                    # Identificar si tiene registros de distancia o tiempo
                    cardio_rows = ex_current[ex_current['Distance'].notna() | ex_current['Time'].notna()]
                    
                    for _, row in cardio_rows.iterrows():
                        dist = row.get('Time') # O distancia según aplique
                        distancia = row.get('Distance', 0)
                        tiempo_str = str(row.get('Time', ''))
                        
                        # Intentar calcular velocidad o ritmo básico si hay datos válidos
                        # Asumimos que Time viene en formato texto o minutos y Distance en km
                        velocidad_txt = "-"
                        try:
                            # Si la distancia y el tiempo son convertibles a números (ej. tiempo en minutos)
                            d_val = float(distancia) if pd.notna(distancia) else 0.0
                            # Si guardas el tiempo como minutos totales o string, adaptamos una métrica visual limpia:
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