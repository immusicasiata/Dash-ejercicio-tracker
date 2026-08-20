import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Panel de Control", page_icon="📅", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        df = conn.read()
        df['Date'] = pd.to_datetime(df['Date'])
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return pd.DataFrame()

def format_clean(val):
    """Convierte a entero si es un número entero exacto, de lo contrario lo deja igual."""
    try:
        f_val = float(val)
        return int(f_val) if f_val.is_integer() else f_val
    except:
        return val

st.title("📅 Panel de Entrenamiento")
df = load_data()

selected_date = st.date_input("Selecciona una fecha:", pd.to_datetime("today"))
selected_date = pd.to_datetime(selected_date)

daily_df = df[df['Date'].dt.date == selected_date.date()]

if not daily_df.empty:
    st.subheader(f"Entrenamiento del {selected_date.strftime('%d/%m/%Y')}")
    
    for category in daily_df['Category'].unique():
        with st.expander(f"💪 {category}", expanded=True):
            cat_df = daily_df[daily_df['Category'] == category]
            
            for exercise in cat_df['Exercise'].unique():
                ex_df = cat_df[cat_df['Exercise'] == exercise]
                
                # 1. Determinar la unidad más frecuente para el título
                unit_cols = ['Weight Unit', 'Distance Unit']
                all_units = ex_df[unit_cols].stack().dropna()
                most_freq_unit = all_units.mode().iloc[0] if not all_units.empty else ""
                
                # 2. Definir Título con la unidad entre paréntesis
                title = f"{exercise} ({most_freq_unit})" if most_freq_unit else exercise
                st.markdown(f"**{title}**")
                
                # 3. Preparar columnas según sea fuerza o cardio
                if ex_df['Distance'].notna().any() or ex_df['Time'].notna().any():
                    df_display = ex_df[['Distance', 'Time']].rename(columns={
                        'Distance': 'Distancia', 
                        'Time': 'Duración'
                    })
                else:
                    df_display = ex_df[['Weight', 'Reps']].rename(columns={
                        'Weight': 'Peso', 
                        'Reps': 'Repeticiones'
                    })
                
                # Aplicar formato sin decimales usando .map() (compatible con pandas moderno)
                df_display = df_display.map(format_clean)
                
                st.table(df_display.reset_index(drop=True))
else:
    st.info("No hay registros de entrenamiento para la fecha seleccionada.")

# --- FUNCIONALIDAD: DUPLICAR RUTINA ---
st.divider()
with st.expander("🔄 Copiar rutina de otro día"):
    source_date = st.date_input("Seleccionar fecha para copiar:", pd.to_datetime("today") - pd.Timedelta(days=1))
    source_df = df[df['Date'].dt.date == source_date]
    
    if not source_df.empty:
        st.write(f"Rutina encontrada para el {source_date.strftime('%d/%m/%Y')}. Edita los valores y presiona el botón:")
        
        # Filtramos solo las columnas editables
        editable_df = source_df[['Exercise', 'Category', 'Weight', 'Reps', 'Distance', 'Time']].copy()
        
        # El data_editor permite al usuario cambiar los valores antes de guardar
        edited_df = st.data_editor(editable_df, use_container_width=True)
        
        if st.button("Guardar esta rutina hoy"):
            # Creamos el nuevo DF con la fecha de hoy
            today = pd.to_datetime("today").normalize()
            new_entries = edited_df.copy()
            new_entries['Date'] = today
            
            # Reincorporamos las unidades (opcional: aquí simplemente las mantenemos o las ponemos por defecto)
            # Para simplicidad, las unimos con el DF original para mantener la estructura
            df_updated = pd.concat([df, new_entries], ignore_index=True)
            
            # Guardar
            conn.update(data=df_updated)
            st.cache_data.clear()
            st.success("¡Rutina copiada y guardada para hoy!")
            st.rerun()
    else:
        st.warning("No hay registros en la fecha seleccionada.")