import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Registrar", page_icon="📝")

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    return conn.read().dropna(how='all')

def save_data(df):
    conn.update(data=df)
    st.cache_data.clear()

st.title("📝 Registrar Entrenamiento")
df = load_data()

with st.form("workout_form"):
    date_input = st.date_input("Fecha", datetime.date.today())
    category = st.selectbox("Categoría", ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Cardio"])
    
    # Filtro dinámico de ejercicios
    ejercicios_filtrados = sorted(df[df['Category'] == category]['Exercise'].dropna().unique().tolist())
    opciones = ["(Escribir nuevo)"] + ejercicios_filtrados
    ejercicio_seleccionado = st.selectbox("Ejercicio:", opciones)
    
    exercise = st.text_input("Nombre del ejercicio") if ejercicio_seleccionado == "(Escribir nuevo)" else ejercicio_seleccionado
    
    col1, col2 = st.columns(2)
    weight = col1.number_input("Peso", min_value=0.0)
    reps = col2.number_input("Repeticiones", min_value=0, step=1)
    
    if st.form_submit_button("Guardar"):
        new_row = pd.DataFrame([{'Date': date_input, 'Exercise': exercise, 'Category': category, 'Weight': weight, 'Reps': reps}])
        save_data(pd.concat([df, new_row], ignore_index=True))
        st.success("Guardado!")