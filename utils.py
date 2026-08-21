import io
import streamlit as st
import pandas as pd
from github import Github, GithubException

def get_github_repo():
    token = st.secrets["github"]["token"]
    repo_name = st.secrets["github"]["repo"]
    g = Github(token)
    return g.get_repo(repo_name)

@st.cache_data
def load_data():
    try:
        repo = get_github_repo()
        file_path = st.secrets["github"].get("file_path", "entrenamientos.parquet")
        branch = st.secrets["github"].get("branch", "main")
        
        # Lectura del archivo Parquet remoto
        contents = repo.get_contents(file_path, ref=branch)
        parquet_bytes = contents.decoded_content
        
        df = pd.read_parquet(io.BytesIO(parquet_bytes), engine='pyarrow')
        
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            
        numeric_cols = ['Weight', 'Reps', 'Distance']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        return df.dropna(how='all')
    except Exception:
        # DataFrame por defecto si aún no existe el archivo en GitHub
        return pd.DataFrame(columns=['Date', 'Category', 'Exercise', 'Weight', 'Reps', 'Distance', 'Time', 'Weight Unit'])

def save_data(df):
    try:
        numeric_cols = ['Weight', 'Reps', 'Distance']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        repo = get_github_repo()
        file_path = st.secrets["github"].get("file_path", "entrenamientos.parquet")
        branch = st.secrets["github"].get("branch", "main")
        
        # Conversión del DataFrame a buffer Parquet en memoria
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False, engine='pyarrow')
        content_bytes = buffer.getvalue()
        
        try:
            # Actualización del archivo en GitHub
            contents = repo.get_contents(file_path, ref=branch)
            repo.update_file(
                path=file_path,
                message="update: actualización automática de entrenamientos",
                content=content_bytes,
                sha=contents.sha,
                branch=branch
            )
        except GithubException:
            # Creación inicial si no existe el archivo
            repo.create_file(
                path=file_path,
                message="feat: inicialización de entrenamientos",
                content=content_bytes,
                branch=branch
            )
            
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Error al sincronizar con GitHub API: {e}")

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