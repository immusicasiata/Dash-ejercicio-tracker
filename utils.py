import io
import os
import uuid
import streamlit as st
import pandas as pd
from github import Github, GithubException

LOCAL_FILE = "entrenamientos_local.parquet"

def get_github_repo():
    token = st.secrets["github"]["token"]
    repo_name = st.secrets["github"]["repo"]
    g = Github(token)
    return g.get_repo(repo_name)

@st.cache_data
def load_data():
    df = None
    if os.path.exists(LOCAL_FILE):
        try:
            df = pd.read_parquet(LOCAL_FILE, engine='pyarrow')
        except Exception:
            pass

    if df is None or df.empty:
        try:
            repo = get_github_repo()
            file_path = st.secrets["github"].get("file_path", "entrenamientos.parquet")
            branch = st.secrets["github"].get("branch", "main")
            
            contents = repo.get_contents(file_path, ref=branch)
            parquet_bytes = contents.decoded_content
            df = pd.read_parquet(io.BytesIO(parquet_bytes), engine='pyarrow')
        except Exception:
            df = pd.DataFrame(columns=['row_id', 'Date', 'Category', 'Exercise', 'Weight', 'Reps', 'Distance', 'Time', 'Weight Unit', 'Program', 'Week'])

    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
            
    numeric_cols = ['Weight', 'Reps', 'Distance']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'row_id' not in df.columns or df['row_id'].isnull().any() or df['row_id'].duplicated().any():
        df['row_id'] = [str(uuid.uuid4()) for _ in range(len(df))]
        
    for col_meta in ['Program', 'Week']:
        if col_meta not in df.columns:
            df[col_meta] = None
        
    return df.dropna(how='all').reset_index(drop=True)

def save_data_local(df):
    if 'row_id' not in df.columns or df['row_id'].isnull().any():
        df['row_id'] = [str(uuid.uuid4()) for _ in range(len(df))]
        
    numeric_cols = ['Weight', 'Reps', 'Distance']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    df_clean = df.reset_index(drop=True)
    df_clean.to_parquet(LOCAL_FILE, index=False, engine='pyarrow')
    st.cache_data.clear()

def sync_to_github(df):
    try:
        repo = get_github_repo()
        file_path = st.secrets["github"].get("file_path", "entrenamientos.parquet")
        branch = st.secrets["github"].get("branch", "main")
        
        if 'row_id' not in df.columns or df['row_id'].isnull().any():
            df['row_id'] = [str(uuid.uuid4()) for _ in range(len(df))]
            
        df_clean = df.reset_index(drop=True)
        buffer = io.BytesIO()
        df_clean.to_parquet(buffer, index=False, engine='pyarrow')
        content_bytes = buffer.getvalue()
        
        try:
            contents = repo.get_contents(file_path, ref=branch)
            repo.update_file(
                path=file_path,
                message="update: sincronización manual a la nube",
                content=content_bytes,
                sha=contents.sha,
                branch=branch
            )
        except GithubException:
            repo.create_file(
                path=file_path,
                message="feat: inicialización de entrenamientos",
                content=content_bytes,
                branch=branch
            )
        return True, "Sincronizado correctamente."
    except Exception as e:
        return False, str(e)

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

def format_clean(val):
    try: 
        return float(val)
    except: 
        return 0.0

def update_cell(row_id, col, key_name):
    new_val = st.session_state.get(key_name)
    current_df = load_data()
    
    if col in ['Weight', 'Reps', 'Distance']:
        try:
            new_val = float(new_val) if new_val is not None and float(new_val) > 0 else None
        except (ValueError, TypeError):
            new_val = None
    elif col == 'Time':
        new_val = str(new_val).strip() if new_val and str(new_val).strip() else None
        
    mask = current_df['row_id'] == row_id
    if mask.any():
        current_df.loc[mask, col] = new_val
        save_data_local(current_df)

def obtener_semana_objetivo_ejercicio(df, ejercicio, fecha_seleccionada):
    if df.empty or 'Week' not in df.columns:
        return "Semana 1 (3x5)"

    fecha_sel_dt = pd.to_datetime(fecha_seleccionada).date()
    df_hoy = df[(df['Exercise'] == ejercicio) & (df['Date'].dt.date == fecha_sel_dt)]
    
    if not df_hoy.empty and 'Week' in df_hoy.columns:
        semana_hoy = df_hoy['Week'].dropna()
        if not semana_hoy.empty:
            return semana_hoy.iloc[0]

    df_pasado = df[
        (df['Exercise'] == ejercicio) & 
        (df['Date'].dt.date < fecha_sel_dt) & 
        (df['Program'] == '5/3/1')
    ].dropna(subset=['Date', 'Week'])

    if df_pasado.empty:
        return "Semana 1 (3x5)"

    ultima_fecha = df_pasado['Date'].max()
    ultima_semana = df_pasado[df_pasado['Date'] == ultima_fecha]['Week'].iloc[0]

    secuencia = ["Semana 1 (3x5)", "Semana 2 (3x3)", "Semana 3 (5, 3, 1)", "Semana 4 (Descarga)"]

    try:
        idx = secuencia.index(ultima_semana)
        return secuencia[(idx + 1) % len(secuencia)]
    except ValueError:
        return "Semana 1 (3x5)"

def obtener_estado_programa_ejercicio(df, ejercicio, fecha_seleccionada=None):
    if df.empty or 'Program' not in df.columns or 'Week' not in df.columns:
        return None, None
        
    hist_ej = df[(df['Exercise'] == ejercicio) & (df['Program'].notna())].dropna(subset=['Date'])
    if fecha_seleccionada:
        fecha_sel_dt = pd.to_datetime(fecha_seleccionada).date()
        hist_ej = hist_ej[hist_ej['Date'].dt.date < fecha_sel_dt]
        
    if hist_ej.empty:
        return None, None
        
    latest_date = hist_ej['Date'].max()
    latest_entries = hist_ej[hist_ej['Date'] == latest_date]
    if latest_entries.empty:
        return None, None
    prog = latest_entries['Program'].iloc[0] if 'Program' in latest_entries.columns else None
    week = latest_entries['Week'].iloc[0] if 'Week' in latest_entries.columns else None
    return prog, week

def obtener_estado_actual_programa(df):
    if df.empty or 'Program' not in df.columns or 'Week' not in df.columns:
        return None, None
    df_prog = df.dropna(subset=['Program', 'Date'])
    if df_prog.empty:
        return None, None
    latest_date = df_prog['Date'].max()
    latest_entries = df_prog[df_prog['Date'] == latest_date]
    if latest_entries.empty:
        return None, None
    prog = latest_entries['Program'].dropna().iloc[0] if not latest_entries['Program'].dropna().empty else None
    week = latest_entries['Week'].dropna().iloc[0] if not latest_entries['Week'].dropna().empty else None
    return prog, week

def calcular_series_531(df_historial, ejercicio, semana):
    if df_historial.empty:
        return []
        
    # Se filtran series de más de 20 reps para evitar errores de cálculo de 1RM
    hist_ej = df_historial[(df_historial['Exercise'] == ejercicio) & (df_historial['Reps'] <= 20)].dropna(subset=['Weight', 'Reps']).copy()
    if hist_ej.empty:
        return []

    hist_ej['1RM_Est'] = hist_ej['Weight'] * (36 / (37 - hist_ej['Reps']))
    mejor_1rm = hist_ej['1RM_Est'].max()
    tm = mejor_1rm * 0.90

    esquemas = {
        "Semana 1 (3x5)": ([0.65, 0.75, 0.85], [5, 5, 5]),
        "Semana 2 (3x3)": ([0.70, 0.80, 0.90], [3, 3, 3]),
        "Semana 3 (5, 3, 1)": ([0.75, 0.85, 0.95], [5, 3, 1]),
        "Semana 4 (Descarga)": ([0.40, 0.50, 0.60], [5, 5, 5])
    }
    
    porcentajes, reps = esquemas.get(semana, ([0.65, 0.75, 0.85], [5, 5, 5]))
    
    series_sugeridas = []
    for p, r in zip(porcentajes, reps):
        peso_calc = round((tm * p) / 2.5) * 2.5
        series_sugeridas.append({"Weight": peso_calc, "Reps": r})
        
    return series_sugeridas

def calcular_series_5x5(df_historial, ejercicio):
    if df_historial.empty:
        return []
        
    # Se filtran series de más de 20 reps para evitar errores de cálculo de 1RM
    hist_ej = df_historial[(df_historial['Exercise'] == ejercicio) & (df_historial['Reps'] <= 20)].dropna(subset=['Weight', 'Reps']).copy()
    if hist_ej.empty:
        return []

    hist_ej['1RM_Est'] = hist_ej['Weight'] * (36 / (37 - hist_ej['Reps']))
    max_peso_5reps = hist_ej[hist_ej['Reps'] >= 5]['Weight'].max()
    
    if pd.isna(max_peso_5reps): 
        max_peso_5reps = hist_ej['1RM_Est'].max() * 0.75
        
    peso_objetivo = max_peso_5reps + 2.5
    
    series_sugeridas = []
    for _ in range(5):
        series_sugeridas.append({"Weight": peso_objetivo, "Reps": 5})
        
    return series_sugeridas