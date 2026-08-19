import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

# Configuración de la página
st.set_page_config(page_title="Tracker de Fuerza", page_icon="🏋️‍♂️", layout="wide")

# Columnas exactas de FitNotes para mantener consistencia
COLUMNS = [
    'Date', 'Exercise', 'Category', 'Weight', 'Weight Unit', 
    'Reps', 'Distance', 'Distance Unit', 'Time', 'Comment'
]

# Crear la conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Lee los datos desde Google Sheets. Si hay un error, retorna un DF vacío con las columnas correctas."""
    try:
        # Se asume que los datos están en la primera hoja por defecto
        df = conn.read()
        return df
    except Exception as e:
        st.error(f"Error al leer de Google Sheets: {e}")
        return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    """Actualiza la hoja de cálculo con el nuevo DataFrame."""
    try:
        conn.update(data=df)
        st.success("¡Entrenamiento sincronizado exitosamente con Google Sheets!")
    except Exception as e:
        st.error(f"Error al guardar en Google Sheets: {e}")

st.title("🏋️‍♂️ Tracker de Entrenamiento y Fuerza")

tab1, tab2, tab3 = st.tabs(["📝 Registrar Entrenamiento", "📊 Historial y Análisis", "💪 Programas de Fuerza"])

# --- PESTAÑA 1: REGISTRO DE ENTRENAMIENTO ---
with tab1:
    st.header("Añadir nuevo registro")
    
    with st.form("workout_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date_input = st.date_input("Fecha", datetime.date.today())
            category = st.selectbox("Categoría", ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Cardio"])
            exercise = st.text_input("Ejercicio (ej. Flat Barbell Bench Press)")
            
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
                st.error("Por favor, ingresa el nombre del ejercicio.")
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
                
                with st.spinner('Sincronizando con Google Sheets...'):
                    df = load_data()
                    # Si el DF viene vacío o con NaNs, limpiamos para evitar problemas de formato
                    df = df.dropna(how='all') 
                    # Añadir el nuevo registro
                    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
                    save_data(df)

# --- PESTAÑA 2: HISTORIAL ---
with tab2:
    st.header("Historial de Entrenamientos")
    with st.spinner('Obteniendo datos...'):
        df = load_data()
    
    if not df.empty and not df.dropna(how='all').empty:
        # Asegurarse de que no haya filas completamente vacías
        df = df.dropna(how='all')
        
        search_term = st.text_input("🔍 Buscar ejercicio específico:")
        if search_term:
            df_display = df[df['Exercise'].str.contains(search_term, case=False, na=False)]
        else:
            df_display = df
            
        st.dataframe(df_display.sort_values(by="Date", ascending=False), use_container_width=True)
        
        if 'Weight' in df.columns:
            st.divider()
            st.subheader("📈 Tendencia de Progresión")
            # Convertir la columna Weight a numérico por si viene como texto desde Sheets
            df['Weight'] = pd.to_numeric(df['Weight'], errors='coerce')
            
            top_exercises = df['Exercise'].value_counts().head(10).index
            selected_ex = st.selectbox("Selecciona un ejercicio para ver tu progresión de peso", top_exercises)
            
            ex_data = df[df['Exercise'] == selected_ex].copy()
            if not ex_data.empty:
                ex_data['Date'] = pd.to_datetime(ex_data['Date'])
                daily_max = ex_data.groupby('Date')['Weight'].max().reset_index()
                st.line_chart(daily_max.set_index('Date')['Weight'])
    else:
        st.info("No hay datos de entrenamiento o la hoja está vacía.")

# --- PESTAÑA 3: PROGRAMAS DE FUERZA ---
with tab3:
    st.header("Programas de Entrenamiento Basados en Ciencia")
    st.markdown("Estos dos programas están extensamente validados en la literatura del entrenamiento de fuerza por su eficiente manejo del volumen y la **sobrecarga progresiva**.")
    
    col_prog1, col_prog2 = st.columns(2)
    
    with col_prog1:
        st.subheader("1. StrongLifts 5x5")
        st.write("""
        **Ideal para:** Principiantes e intermedios. Es uno de los mejores métodos para desarrollar fuerza base rápidamente de forma lineal.
        
        **Mecanismo:** Frecuencia alta de los levantamientos principales. Se alternan dos días de entrenamiento (A y B), descansando un día entre ellos.
        """)
        st.info("""
        **Entrenamiento A:**
        - Squat: 5x5
        - Bench Press: 5x5
        - Barbell Row: 5x5
        
        **Entrenamiento B:**
        - Squat: 5x5
        - Overhead Press: 5x5
        - Deadlift: 1x5
        """)
        
    with col_prog2:
        st.subheader("2. Método 5/3/1 de Jim Wendler")
        st.write("""
        **Ideal para:** Intermedios y avanzados que requieren periodización ondulante calculada sobre el 90% de su 1RM.
        """)
        st.success("""
        **Estructura del Ciclo (4 semanas):**
        - **Semana 1:** 3 series (65% x 5, 75% x 5, 85% x 5+)
        - **Semana 2:** 3 series (70% x 3, 80% x 3, 90% x 3+)
        - **Semana 3:** 3 series (75% x 5, 85% x 3, 95% x 1+)
        - **Semana 4:** Descarga
        """)