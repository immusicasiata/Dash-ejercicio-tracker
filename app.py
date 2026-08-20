import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Panel de Entrenamiento", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def load_data():
    try:
        df = conn.read()
        df['Date'] = pd.to_datetime(df['Date'])
        return df.dropna(how='all')
    except: return pd.DataFrame()

def save_data(df):
    conn.update(data=df)
    st.cache_data.clear()

def format_clean(val):
    try:
        f_val = float(val)
        return int(f_val) if f_val.is_integer() else f_val
    except: return val

st.title("📅 Panel de Entrenamiento")
df = load_data()

selected_date = st.date_input("Selecciona fecha:", pd.to_datetime("today"))
selected_date = pd.to_datetime(selected_date)
daily_df = df[df['Date'].dt.date == selected_date.date()].copy()

if not daily_df.empty:
    st.subheader(f"Registros del {selected_date.strftime('%d/%m/%Y')}")
    
    # Agrupamos por categoría para editar de forma organizada
    for category in daily_df['Category'].unique():
        with st.expander(f"💪 {category}", expanded=True):
            cat_df = daily_df[daily_df['Category'] == category]
            
            for exercise in cat_df['Exercise'].unique():
                ex_df = cat_df[cat_df['Exercise'] == exercise]
                
                # 1. Título con unidad más frecuente
                unit_cols = ['Weight Unit', 'Distance Unit']
                all_units = ex_df[unit_cols].stack().dropna()
                most_freq_unit = all_units.mode().iloc[0] if not all_units.empty else ""
                st.markdown(f"**{exercise} ({most_freq_unit})**")
                
                # 2. Selección de columnas para mostrar/editar
                if ex_df['Distance'].notna().any() or ex_df['Time'].notna().any():
                    cols = ['Distance', 'Time', 'Comment']
                    display_names = {'Distance': 'Distancia', 'Time': 'Duración', 'Comment': 'Nota'}
                else:
                    cols = ['Weight', 'Reps', 'Comment']
                    display_names = {'Weight': 'Peso', 'Reps': 'Repeticiones', 'Comment': 'Nota'}
                
                # Editor interactivo por ejercicio
                edited_ex = st.data_editor(ex_df[cols].rename(columns=display_names), use_container_width=True)
                
                # Botón de guardado local para este grupo
                if st.button(f"Guardar cambios en {exercise}", key=f"btn_{exercise}"):
                    # Lógica para actualizar el DF principal
                    updated_ex = edited_ex.rename(columns={v: k for k, v in display_names.items()})
                    df.loc[ex_df.index, cols] = updated_ex
                    save_data(df)
                    st.rerun()
else:
    st.info("No hay registros en esta fecha.")

# 3. FUNCIONALIDAD DE COPIAR RUTINA
st.divider()
with st.expander("🔄 Copiar rutina de otro día"):
    source_date = st.date_input("Fecha a copiar:", pd.to_datetime("today") - pd.Timedelta(days=1))
    source_df = df[df['Date'].dt.date == pd.to_datetime(source_date).date()]
    
    if not source_df.empty:
        st.write("Vista previa de la rutina a copiar:")
        st.dataframe(source_df[['Exercise', 'Category', 'Weight', 'Reps', 'Distance', 'Time']], use_container_width=True)
        
        if st.button("Copiar esta rutina al día seleccionado"):
            new_entries = source_df.copy()
            new_entries['Date'] = selected_date
            save_data(pd.concat([df, new_entries], ignore_index=True))
            st.success("Rutina copiada.")
            st.rerun()