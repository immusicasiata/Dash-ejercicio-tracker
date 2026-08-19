import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Registrar Entrenamiento", page_icon="📝", layout="wide")

COLUMNS = [
    'Date', 'Exercise', 'Category', 'Weight', 'Weight Unit', 
    'Reps', 'Distance', 'Distance Unit', 'Time', 'Comment'
]

# Crear la conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    """Carga los datos desde Google Sheets descartando filas vacías."""
    try:
        df = conn.read()
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Error al leer de Google Sheets: {e}")
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    """Guarda y actualiza los datos en Google Sheets limpiando la caché."""
    try:
        conn.update(data=df)
        st.cache_data.clear()
        st.success("¡Entrenamiento sincronizado exitosamente con Google Sheets!")
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {e}")

st.title("📝 Registrar Entrenamiento")

# Cargar datos para alimentar los selectores dinámicos
df = load_data()

with st.form("workout_form"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_input = st.date_input("Fecha", datetime.date.today())
        
        # 1. Selección de categoría
        category = st.selectbox("Categoría", ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Cardio"])
        
        # 2. Filtrar ejercicios únicos basados estrictamente en la categoría seleccionada
        if not df.empty and 'Exercise' in df.columns and 'Category' in df.columns:
            ejercicios_filtrados = sorted(
                df[df['Category'] == category]['Exercise'].dropna().unique().tolist()
            )
        else:
            ejercicios_filtrados = []
            
        opciones_ejercicio = ["(Escribir nuevo ejercicio)"] + ejercicios_filtrados
        
        # 3. Menú desplegable filtrado por categoría
        ejercicio_seleccionado = st.selectbox("Selecciona un Ejercicio:", opciones_ejercicio)
        
        if ejercicio_seleccionado == "(Escribir nuevo ejercicio)":
            exercise = st.text_input("Nombre del nuevo ejercicio")
        else:
            exercise = ejercicio_seleccionado
        
    with col2:
        weight = st.number_input("Peso", min_value=0.0, step=1.0, format="%.1f")
        weight_unit = st.selectbox("Unidad de Peso", ["lbs", "kg"])
        reps = st.number_input("Repeticiones", min_value=0, step=1)
            
    with col3:
        distance = st.number_input("Distancia (opcional)", min_value=0.0, step=0.1)
        distance_unit = st.selectbox("Unidad de Distancia", ["", "km", "mi", "m"])
        time_val = st.text_input("Tiempo (opcional, ej. 00:30:00)")
        
    comment = st.text_area("Comentarios (opcional)")
    
    submitted = st.form_submit_button("Guardar Entrenamiento")
    
    if submitted:
        if exercise.strip() == "":
            st.error("Por favor, ingresa o selecciona el nombre del ejercicio.")
        else:
            new_entry = {
                'Date': date_input.strftime("%Y-%m-%d"),
                'Exercise': exercise,
                'Category': category,
                'Weight': weight if weight > 0 else None,
                'Weight Unit': weight_unit,
                'Reps': reps if reps > 0 else None,
                'Distance': distance if distance > 0 else None,
                'Distance Unit': distance_unit if distance != "" else None,
                'Time': time_val if time_val else None,
                'Comment': comment if comment else None
            }
            
            with st.spinner('Guardando en Google Sheets...'):
                df_current = load_data()
                df_updated = pd.concat([df_current, pd.DataFrame([new_entry])], ignore_index=True)
                save_data(df_updated)