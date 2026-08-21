import pandas as pd

# 1. Cargar el archivo CSV actual
df = pd.read_csv("Data_ejercicio - FitNotes_Export_2026_08_19_15_12_59.csv")

# 2. Asegurar que la columna de fecha mantenga el formato correcto
if 'Date' in df.columns:
    df['Date'] = pd.to_datetime(df['Date'])

#print(df)

# 3. Guardar en formato Parquet comprimido
df.to_parquet("entrenamientos.parquet", index=False, engine='pyarrow')

print("¡Migración a Parquet completada con éxito!")
