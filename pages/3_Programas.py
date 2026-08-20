import streamlit as st

st.set_page_config(page_title="Programas de Fuerza", page_icon="💪", layout="wide")

st.title("💪 Programas de Entrenamiento")
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