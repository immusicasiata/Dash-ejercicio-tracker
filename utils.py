import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

@st.cache_data(ttl=60)
def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read()
        df['Date'] = pd.to_datetime(df['Date'])
        numeric_cols = ['Weight', 'Reps', 'Distance']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.dropna(how='all')
    except: 
        return pd.DataFrame()

def save_data(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    numeric_cols = ['Weight', 'Reps', 'Distance']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    conn.update(data=df)
    st.cache_data.clear()

@st.cache_data(ttl=3600)
def get_cached_date_summary(df_cached):
    if df_cached.empty or 'Date' not in df_cached.columns:
        return []
    valid_df = df_cached.dropna(subset=['Date']).copy()
    valid_df['Date_Only'] = valid_df['Date'].dt.date
    date_summary = []
    for d in sorted(valid_df['Date_Only'].unique(), reverse=True):
        cats = valid_df[valid_df['Date_Only'] == d]['Category'].dropna().unique()
        all_cats_str = " ".join([str(cat).lower() for cat in cats])
        date_icon = "🦵 " if any(k in all_cats_str for k in ['leg', 'pierna', 'cuadriceps', 'femorales', 'gluteo', 'pantorrilla', 'squat', 'lower']) else ("🦾 " if any(k in all_cats_str for k in ['chest', 'pecho', 'pectoral', 'back', 'espalda', 'dorsal', 'remo', 'pull', 'biceps', 'triceps', 'hombro', 'shoulder', 'upper', 'brazo', 'arm']) else "")
        cats_str = ", ".join(cats) if len(cats) > 0 else "Sin categoría"
        date_summary.append((d, f"{date_icon}{d.strftime('%d/%m/%Y')} — {cats_str}"))
    return date_summary