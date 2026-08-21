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
    # 1. Intentar cargar desde el archivo local (Ultra rápido y seguro contra recargas)
    if os.path.exists(LOCAL_FILE):
        try:
            df = pd.read_parquet(LOCAL_FILE, engine='pyarrow')
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
            return df
        except Exception:
            pass

    # 2. Si no existe archivo local (ej. se reinició el servidor de Streamlit), traer desde GitHub
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
                
        # Crear la copia local para futuras lecturas rápidas
        df.to_parquet(LOCAL_FILE, index=False, engine='pyarrow')
        return df.dropna(how='all')
    
    except Exception:
        # 3. DataFrame por defecto si no existe en absoluto
        return pd.DataFrame(columns=['Date', 'Category', 'Exercise', 'Weight', 'Reps', 'Distance', 'Time', 'Weight Unit'])

def save_data_local(df):
    """Guarda los cambios inmediatamente en el disco local del servidor. No hace commits a GitHub."""
    numeric_cols = ['Weight', 'Reps', 'Distance']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    df.to_parquet(LOCAL_FILE, index=False, engine='pyarrow')
    st.cache_data.clear() # Limpia caché para que la interfaz se actualice al instante

def sync_to_github(df):
    """Envía el archivo local a GitHub. Se ejecuta solo al presionar el botón de la nube."""
    try:
        repo = get_github_repo()
        file_path = st.secrets["github"].get("file_path", "entrenamientos.parquet")
        branch = st.secrets["github"].get("branch", "main")
        
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False, engine='pyarrow')
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