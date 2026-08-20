import streamlit as st
import pandas as pd
from utils import load_data, get_cached_date_summary

st.set_page_config(page_title="Historial por Fecha", layout="wide")
st.title("📊 Seguimiento de Fuerza por Sesión")

df = load_data()

if not df.empty and 'Date' in df.columns:
    # Obtener el resumen de fechas disponibles usando la función auxiliar de utils
    date_summary = get_cached_date_summary(df)
    
    if date_summary:
        dates_only = [item[0] for item in date_summary]
        date_labels = [item[1] for item in date_summary]
        
        # Filtro principal por fecha
        selected_label_idx = st.selectbox(
            "Selecciona la fecha de entrenamiento a evaluar:", 
            range(len(dates_only)), 
            format_func=lambda x: date_labels[x]
        )
        target_date = pd.to_datetime(dates_only[selected_label_idx])
        
        # Filtrar datos de la fecha seleccionada
        df_sesion = df[df['Date'].dt.date == target_date.date()].copy()
        
        if not df_sesion.empty:
            st.divider()
            st.subheader(f"Resumen de la Sesión: {target_date.strftime('%d/%m/%Y')}")
            
            # Agrupar y recorrer por categoría (grupo muscular) dentro de esa fecha
            categorias_sesion = sorted(df_sesion['Category'].dropna().unique())
            
            for cat in categorias_sesion:
                st.markdown(f"### 💪 {cat}")
                cat_df = df_sesion[df_sesion['Category'] == cat]
                
                datos_tabla = []
                for ex in cat_df['Exercise'].dropna().unique():
                    # Buscamos el histórico completo del ejercicio para calcular RM y meseta
                    ex_hist = df[df['Exercise'] == ex].dropna(subset=['Weight', 'Reps']).sort_values('Date')
                    
                    # Registro específico de este ejercicio en la fecha seleccionada
                    ex_current = cat_df[cat_df['Exercise'] == ex].dropna(subset=['Weight', 'Reps'])
                    
                    if not ex_current.empty:
                        # Tomamos el mejor set o el último set registrado en esa fecha
                        last_row = ex_current.iloc[-1]
                        peso = last_row['Weight']
                        reps = last_row['Reps']
                        
                        # Fórmulas de estimación (Brzycki)
                        if reps > 0:
                            rm1 = peso / (1.0278 - (0.0278 * reps))
                        else:
                            rm1 = peso
                            
                        rm5 = rm1 * 0.87
                        rm10 = rm1 * 0.75
                        
                        # Chequeo de Meseta (últimas 4 sesiones globales con mismo peso)
                        es_meseta = False
                        if len(ex_hist) >= 4:
                            ultimos_pesos = ex_hist['Weight'].tail(4).values
                            if len(set(ultimos_pesos)) == 1 and ultimos_pesos[0] > 0:
                                es_meseta = True
                        
                        datos_tabla.append({
                            "Ejercicio": ex,
                            "Peso (kg)": peso,
                            "Reps": int(reps),
                            "1RM": round(rm1, 1),
                            "5RM": round(rm5, 1),
                            "10RM": round(rm10, 1),
                            "Estado": "⚠️ Meseta" if es_meseta else "✅ Activo"
                        })
                
                if datos_tabla:
                    df_resumen = pd.DataFrame(datos_tabla)
                    st.dataframe(
                        df_resumen.set_index("Ejercicio"),
                        use_container_width=True,
                        column_config={
                            "Peso (kg)": st.column_config.NumberColumn("Peso (kg)", format="%.1f"),
                            "Reps": st.column_config.NumberColumn("Reps", format="%d"),
                            "1RM": st.column_config.NumberColumn("1RM (kg)", format="%.1f"),
                            "5RM": st.column_config.NumberColumn("5RM (kg)", format="%.1f"),
                            "10RM": st.column_config.NumberColumn("10RM (kg)", format="%.1f"),
                        }
                    )
                else:
                    st.info(f"No hay registros de fuerza con peso/reps en {cat} para esta fecha.")
                
                st.write("") # Espaciador entre categorías
        else:
            st.warning("No hay registros en la fecha seleccionada.")
    else:
        st.info("No hay historial disponible.")
else:
    st.info("No hay datos cargados para analizar.")