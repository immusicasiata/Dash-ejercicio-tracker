import io
import os
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
    if os.path.exists(LOCAL_FILE):
        try:
            df = pd.read_parquet(LOCAL_FILE, engine='pyarrow')
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
            # IMPORTANTE: Forzar índices limpios al cargar desde local
            return df.dropna(how='all').reset_index(drop=True)
        except Exception:
            pass

    try:
        repo = get_github_repo()
        file_path = st.secrets["github"].get("file_path", "entrenamientos.parquet")
        branch = st.secrets["github"].get("branch", "main")
        
        contents = repo.get_contents(file_path, ref=branch)
        parquet_bytes = contents.decoded_content
        df = pd.read_parquet(io.BytesIO(parquet_bytes), engine='pyarrow')
        
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            
        numeric_cols = ['Weight', 'Reps', 'Distance']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        # IMPORTANTE: Limpiar índices antes de guardar localmente
        df = df.dropna(how='all').reset_index(drop=True)
        df.to_parquet(LOCAL_FILE, index=False, engine='pyarrow')
        return df
    
    except Exception:
        return pd.DataFrame(columns=['Date', 'Category', 'Exercise', 'Weight', 'Reps', 'Distance', 'Time', 'Weight Unit'])

def save_data_local(df):
    """Guarda los cambios inmediatamente en el servidor asegurando índices limpios."""
    numeric_cols = ['Weight', 'Reps', 'Distance']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # IMPORTANTE: Reindexar antes de guardar para evitar desalineaciones en la interfaz
    df_clean = df.reset_index(drop=True)
    df_clean.to_parquet(LOCAL_FILE, index=False, engine='pyarrow')
    st.cache_data.clear()

def sync_to_github(df):
    """Envía el archivo local a GitHub manteniendo la integridad de los índices."""
    try:
        repo = get_github_repo()
        file_path = st.secrets["github"].get("file_path", "entrenamientos.parquet")
        branch = st.secrets["github"].get("branch", "main")
        
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
    """Convierte un valor numérico a float limpio de forma segura."""
    try: 
        return float(val)
    except: 
        return 0.0

def update_cell(idx, col, key_name):
    """Actualiza una celda en el DataFrame local asegurando el índice correcto."""
    new_val = st.session_state.get(key_name)
    current_df = load_data()
    
    if col in ['Weight', 'Reps', 'Distance']:
        try:
            new_val = float(new_val) if new_val is not None and float(new_val) > 0 else None
        except (ValueError, TypeError):
            new_val = None
    elif col == 'Time':
        new_val = str(new_val).strip() if new_val and str(new_val).strip() else None
        
    if idx in current_df.index:
        current_df.loc[idx, col] = new_val
        save_data_local(current_df)

def calcular_series_531(df_historial, ejercicio, semana):
    """Calcula las 3 series de 5/3/1 basándose en el 1RM histórico absoluto del ejercicio."""
    if df_historial.empty:
        return []
        
    hist_ej = df_historial[df_historial['Exercise'] == ejercicio].dropna(subset=['Weight', 'Reps'])
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
    """Calcula las 5 series de 5 repeticiones basándose en la mejor marca a 5 reps + 2.5kg."""
    if df_historial.empty:
        return []
        
    hist_ej = df_historial[df_historial['Exercise'] == ejercicio].dropna(subset=['Weight', 'Reps'])
    if hist_ej.empty:
        return []

    hist_ej['1RM_Est'] = hist_ej['Weight'] * (36 / (37 - hist_ej['Reps']))
    mejor_1rm = hist_ej['1RM_Est'].max()
    
    max_peso_5reps = hist_ej[hist_ej['Reps'] >= 5]['Weight'].max()
    
    if pd.isna(max_peso_5reps): 
        max_peso_5reps = mejor_1rm * 0.75
        
    peso_objetivo = max_peso_5reps + 2.5
    
    series_sugeridas = []
    for _ in range(5):
        series_sugeridas.append({"Weight": peso_objetivo, "Reps": 5})
        
    return series_sugeridas