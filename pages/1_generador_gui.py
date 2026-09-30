import io
import unicodedata
import pandas as pd
import streamlit as st

# ==========================================
# ⚙️ CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Gestor y Visor 5/3/1", layout="wide", initial_sidebar_state="expanded"
)

CATEGORIAS_TORSO = {
    "chest", "back", "biceps", "triceps", "shoulders", 
    "hombros atrás", "hombro", "hombros", "pecho", 
    "espalda", "brazo", "brazos", "abs", "core", "upper", "torso",
}

CATEGORIAS_PIERNA = {
    "legs", "pierna", "piernas", "cuadriceps", "gluteo", 
    "femorales", "pantorrilla", "pantorrillas", "lower",
}

# Palabras clave ampliadas (sin importar tildes/mayúsculas)
KEYWORDS_FUERZA = [
    "press", "bench", "sentadilla", "squat", "peso muerto", "deadlift",
    "remo", "row", "jalon", "pulldown", "dominada", "pull up", "chin up", "thrust",
    "pecho plano", "pecho inclinado", "pecho declinado", "pecho barra",
    "hombro barra", "hombro mancuerna", "militar"
]

# ==========================================
# 🛠️ FUNCIONES DE PROCESAMIENTO
# ==========================================
def ordenar_ejercicios(lista_ejercicios, dicc_categorias=None):
    """
    Ordena: 1° Fuerza vs Accesorios | 2° Grupo Muscular | 3° Orden Alfabético
    """
    if dicc_categorias is None:
        dicc_categorias = {}
        
    unicos = list(dict.fromkeys(lista_ejercicios))

    def limpiar_texto(texto):
        texto = str(texto).lower()
        return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

    def es_fuerza(nombre):
        nom_limpio = limpiar_texto(nombre)
        return any(kw in nom_limpio for kw in KEYWORDS_FUERZA)

    def categoria(nombre):
        # Retorna el grupo muscular para usarlo como criterio de orden
        return str(dicc_categorias.get(nombre, "Otros")).strip().title()

    # (not es_fuerza) asegura que True (0) vaya antes que False (1)
    return sorted(unicos, key=lambda x: (not es_fuerza(x), categoria(x), str(x).lower()))


def formato_ejercicio(ex):
    """Agrega la etiqueta [Grupo Muscular] en los menús desplegables"""
    if "ex_to_cat" in st.session_state:
        cat = str(st.session_state["ex_to_cat"].get(ex, "")).strip().title()
        if cat and cat != "Nan":
            return f"[{cat}] {ex}"
    return ex


def procesar_historial_fitnotes(df_raw):
    df = df_raw.copy()
    df["Date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=True)

    if "Weight" in df.columns:
        df["Weight"] = pd.to_numeric(
            df["Weight"].astype(str).str.replace(",", "."), errors="coerce"
        )
    if "Reps" in df.columns:
        df["Reps"] = pd.to_numeric(df["Reps"], errors="coerce")

    fecha_limite = df["Date"].max() - pd.DateOffset(months=6)
    df_6m = df[df["Date"] >= fecha_limite].copy()

    # Mapear cada ejercicio a su categoría (grupo muscular) en FitNotes
    ex_to_cat = df_6m.groupby("Exercise")["Category"].first().to_dict()

    ejercicios_todos = df_6m["Exercise"].dropna().unique().tolist()
    ejercicios_torso = []
    ejercicios_pierna = []

    for ex in ejercicios_todos:
        cat_str = str(ex_to_cat.get(ex, "")).lower().strip()
        is_torso = any(c in cat_str for c in CATEGORIAS_TORSO)
        is_pierna = any(c in cat_str for c in CATEGORIAS_PIERNA)

        if is_torso:
            ejercicios_torso.append(ex)
        if is_pierna:
            ejercicios_pierna.append(ex)
        if not is_torso and not is_pierna:
            ejercicios_torso.append(ex)
            ejercicios_pierna.append(ex)

    # Ordenar aplicando la nueva lógica (Fuerza -> Músculo -> Alfabético)
    ejercicios_todos = ordenar_ejercicios(ejercicios_todos, ex_to_cat)
    ejercicios_torso = ordenar_ejercicios(ejercicios_torso, ex_to_cat)
    ejercicios_pierna = ordenar_ejercicios(ejercicios_pierna, ex_to_cat)

    return df_6m, ejercicios_todos, ejercicios_torso, ejercicios_pierna, ex_to_cat


def calcular_tm_inicial(df, ejercicio):
    if df is None or df.empty:
        return 0.0

    df_ej = df[
        (df["Exercise"] == ejercicio)
        & (df["Reps"] > 0)
        & (df["Reps"] <= 12)
        & (df["Weight"] > 0)
    ].copy()

    if df_ej.empty:
        return 0.0

    df_ej["1RM_Est"] = df_ej["Weight"] * (36 / (37 - df_ej["Reps"]))
    return float(df_ej["1RM_Est"].max() * 0.90)


def cargar_rutina_generada(archivo):
    try:
        if archivo.name.endswith(".csv"):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo)

        columnas_requeridas = {
            "Ciclo", "Semana Global", "Fase", "Día", 
            "Rol", "Ejercicio", "Peso Sugerido", "Reps Objetivo",
        }
        if not columnas_requeridas.issubset(set(df.columns)):
            st.error("El archivo no tiene el formato estándar de rutina generado. Columnas faltantes.")
            return None
        return df
    except Exception as e:
        st.error(f"Error al leer la rutina generada: {e}")
        return None


# ==========================================
# 🖥️ BARRA LATERAL (MODO DE NAVEGACIÓN)
# ==========================================
st.sidebar.title("🏋️‍♂️ Menú Principal")

modo_app = st.sidebar.radio(
    "Selecciona una opción:",
    ["🛠️ Crear Nueva Rutina", "👁️ Visualizar Rutina Cargada"],
    index=0,
)

st.sidebar.divider()

# ==========================================
# 🛠️ MODO 1: CREAR NUEVA RUTINA
# ==========================================
if modo_app == "🛠️ Crear Nueva Rutina":
    st.title("🛠️ Configuración y Generación de Rutina 5/3/1")

    with st.sidebar:
        st.header("📂 Historial de FitNotes")
        uploaded_fitnotes = st.file_uploader(
            "Sube tu CSV de historial", type=["csv"], key="fitnotes_file"
        )

        st.header("⚙️ Parámetros Globales")
        filtrar_categorias = st.toggle("Filtrar menús por Torso/Pierna", value=True)
        ciclos = st.number_input(
            "Cantidad de Ciclos", min_value=1, max_value=12, value=4, step=1
        )

        st.subheader("Descarga (Deload)")
        tipo_descarga = st.radio(
            "¿Frecuencia de descarga?",
            options=["Cada 2 ciclos (Semana 7)", "Cada 1 ciclo (Semana 4)"],
            index=0,
        )
        frecuencia_descarga = 2 if "2 ciclos" in tipo_descarga else 1

    df_hist = None
    ejercicios_todos, ejercicios_torso, ejercicios_pierna = [], [], []

    # Bloque de carga de datos
    if uploaded_fitnotes is not None:
        try:
            df_raw = pd.read_csv(uploaded_fitnotes)
            (
                df_hist, ejercicios_todos, ejercicios_torso, 
                ejercicios_pierna, ex_to_cat
            ) = procesar_historial_fitnotes(df_raw)
            st.session_state["ex_to_cat"] = ex_to_cat
            st.sidebar.success("✅ Archivo de historial cargado")
        except Exception as e:
            st.error(f"Error procesando historial: {e}")
    else:
        archivo_local = "Data_ejercicio - FitNotes_Export_2026_08_19_15_12_59.csv"
        try:
            df_raw = pd.read_csv(archivo_local)
            (
                df_hist, ejercicios_todos, ejercicios_torso, 
                ejercicios_pierna, ex_to_cat
            ) = procesar_historial_fitnotes(df_raw)
            st.session_state["ex_to_cat"] = ex_to_cat
            st.info(f"ℹ️ Usando historial local predeterminado: `{archivo_local}`")
        except Exception:
            st.warning("👈 Sube tu CSV de FitNotes en la barra lateral.")
            st.stop()

    if ejercicios_todos:
        configuracion_dias = {}
        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)

        columnas_ui = [
            (col1, "Día 1: Torso (Empuje/Tracción)", 5.0, "torso"),
            (col2, "Día 2: Pierna (Énfasis Cadera/Cuádriceps)", 10.0, "pierna"),
            (col3, "Día 3: Torso (Empuje/Tracción)", 5.0, "torso"),
            (col4, "Día 4: Pierna (Énfasis Cadera/Cuádriceps)", 10.0, "pierna"),
        ]

        for idx, (col, titulo, inc_default, tipo_dia) in enumerate(columnas_ui):
            dia_num = idx + 1
            with col:
                with st.container(border=True):
                    st.subheader(titulo)
                    if not filtrar_categorias:
                        opciones_disponibles = ejercicios_todos
                    elif tipo_dia == "torso":
                        opciones_disponibles = (
                            ejercicios_torso if ejercicios_torso else ejercicios_todos
                        )
                    else:
                        opciones_disponibles = (
                            ejercicios_pierna if ejercicios_pierna else ejercicios_todos
                        )

                    ej_princ = st.selectbox(
                        "Levantamiento Principal",
                        options=opciones_disponibles,
                        format_func=formato_ejercicio,
                        key=f"princ_{dia_num}",
                    )
                    
                    tm_calc = calcular_tm_inicial(df_hist, ej_princ)
                    st.caption(f"🎯 TM Inicial Calculado: **{tm_calc:.1f} lbs/kg**")

                    inc_val = st.number_input(
                        "Incremento por ciclo",
                        value=inc_default,
                        step=2.5,
                        key=f"inc_{dia_num}",
                    )
                    
                    ej_acc = st.multiselect(
                        "Accesorios (Opcional)",
                        options=opciones_disponibles,
                        format_func=formato_ejercicio,
                        key=f"acc_{dia_num}",
                    )

                    configuracion_dias[dia_num] = {
                        "principal": ej_princ,
                        "incremento": inc_val,
                        "accesorios": ej_acc,
                        "tm_actual": tm_calc,
                    }

        st.divider()

        if st.button("🚀 Calcular y Generar Rutina", type="primary", use_container_width=True):
            rutina = []
            numero_semana_global = 1

            esquema_semanas = {
                1: {"nombre": "Semana 1 (3x5)", "porcentajes": [0.65, 0.75, 0.85], "reps": [5, 5, 5]},
                2: {"nombre": "Semana 2 (3x3)", "porcentajes": [0.70, 0.80, 0.90], "reps": [3, 3, 3]},
                3: {"nombre": "Semana 3 (5, 3, 1)", "porcentajes": [0.75, 0.85, 0.95], "reps": [5, 3, 1]},
                "Descarga": {"nombre": "Semana Descarga", "porcentajes": [0.40, 0.50, 0.60], "reps": [5, 5, 5]},
            }

            for ciclo in range(1, ciclos + 1):
                for semana in [1, 2, 3]:
                    for dia, conf in configuracion_dias.items():
                        esquema = esquema_semanas[semana]
                        ej = conf["principal"]

                        for i, (p, r) in enumerate(zip(esquema["porcentajes"], esquema["reps"])):
                            peso_calc = round((conf["tm_actual"] * p) / 2.5) * 2.5
                            es_amrap = (i == 2)
                            reps_str = f"{r}+" if es_amrap else str(r)

                            rutina.append({
                                "Ciclo": ciclo,
                                "Semana Global": numero_semana_global,
                                "Fase": esquema["nombre"],
                                "Día": dia,
                                "Rol": "Principal",
                                "Ejercicio": ej,
                                "Peso Sugerido": max(0.0, peso_calc),
                                "Reps Objetivo": reps_str,
                            })

                        for acc in conf["accesorios"]:
                            rutina.append({
                                "Ciclo": ciclo,
                                "Semana Global": numero_semana_global,
                                "Fase": esquema["nombre"],
                                "Día": dia,
                                "Rol": "Accesorio",
                                "Ejercicio": acc,
                                "Peso Sugerido": "A sensaciones",
                                "Reps Objetivo": "3 x 10-15",
                            })
                    numero_semana_global += 1

                if ciclo % frecuencia_descarga == 0:
                    for dia, conf in configuracion_dias.items():
                        esquema = esquema_semanas["Descarga"]
                        ej = conf["principal"]
                        for p, r in zip(esquema["porcentajes"], esquema["reps"]):
                            peso_calc = round((conf["tm_actual"] * p) / 2.5) * 2.5
                            rutina.append({
                                "Ciclo": ciclo,
                                "Semana Global": numero_semana_global,
                                "Fase": esquema["nombre"],
                                "Día": dia,
                                "Rol": "Principal (Descarga)",
                                "Ejercicio": ej,
                                "Peso Sugerido": max(0.0, peso_calc),
                                "Reps Objetivo": str(r),
                            })
                    numero_semana_global += 1

                for dia in configuracion_dias:
                    configuracion_dias[dia]["tm_actual"] += configuracion_dias[dia]["incremento"]

            st.session_state["df_rutina"] = pd.DataFrame(rutina)
            st.success("✅ ¡Rutina generada exitosamente!")


# ==========================================
# 👁️ MODO 2: VISUALIZAR RUTINA EXISTENTE
# ==========================================
elif modo_app == "👁️ Visualizar Rutina Cargada":
    st.title("👁️ Cargar y Visualizar Rutina Generada")
    st.markdown("Sube un archivo de rutina preexistente en formato CSV o Excel para analizar su distribución y progresión.")

    archivo_rutina_subido = st.file_uploader(
        "Sube tu archivo de rutina (.csv o .xlsx)", type=["csv", "xlsx"], key="rutina_file",
    )

    if archivo_rutina_subido is not None:
        df_cargado = cargar_rutina_generada(archivo_rutina_subido)
        if df_cargado is not None:
            st.session_state["df_rutina"] = df_cargado
            st.success(f"✅ Rutina '{archivo_rutina_subido.name}' cargada correctamente.")

# ==========================================
# 📊 SECCIÓN DE VISUALIZACIÓN INTERACTIVA
# ==========================================
if "df_rutina" in st.session_state and st.session_state["df_rutina"] is not None:
    df_rutina = st.session_state["df_rutina"]

    st.divider()
    st.header("📊 Panel de Visualización")

    tipo_vista = st.radio(
        "Selecciona cómo deseas explorar la rutina:",
        ["📅 Vista por Semana Global / Ciclos", "🏋️ Vista por Ejercicio (Progreso)"],
        horizontal=True,
    )

    st.markdown("---")

    # ------------------------------------------
    # VISTA 1: POR SEMANA GLOBAL / CICLOS
    # ------------------------------------------
    if tipo_vista == "📅 Vista por Semana Global / Ciclos":
        num_ciclos = int(df_rutina["Ciclo"].max())
        pestañas_ciclos = st.tabs([f"🔄 Ciclo {c}" for c in range(1, num_ciclos + 1)])

        for idx_ciclo, tab in enumerate(pestañas_ciclos):
            ciclo_actual = idx_ciclo + 1
            with tab:
                df_ciclo = df_rutina[df_rutina["Ciclo"] == ciclo_actual]
                semanas_ciclo = df_ciclo.groupby(["Semana Global", "Fase"], sort=False)

                for (sem_global, fase_nombre), df_semana in semanas_ciclo:
                    with st.expander(f"📅 **Semana Global {sem_global}** — {fase_nombre}", expanded=True):
                        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                        cols_dias = [col_d1, col_d2, col_d3, col_d4]

                        for d_idx in range(1, 5):
                            with cols_dias[d_idx - 1]:
                                with st.container(border=True):
                                    st.markdown(f"### Día {d_idx}")
                                    df_dia = df_semana[df_semana["Día"] == d_idx]

                                    df_p = df_dia[df_dia["Rol"].str.contains("Principal")]
                                    if not df_p.empty:
                                        ej_nombre = df_p["Ejercicio"].iloc[0]
                                        st.markdown(f"🏋️ **{ej_nombre}**")

                                        for _, row in df_p.iterrows():
                                            st.markdown(f"• `{row['Peso Sugerido']}` × **{row['Reps Objetivo']}**")

                                    df_a = df_dia[df_dia["Rol"] == "Accesorio"]
                                    if not df_a.empty:
                                        st.caption("🧩 **Accesorios:**")
                                        for _, row in df_a.iterrows():
                                            st.markdown(f"• **{row['Ejercicio']}** *(3×10-15)*")

    # ------------------------------------------
    # VISTA 2: POR EJERCICIO A LO LARGO DE LOS CICLOS
    # ------------------------------------------
    else:
        # Recuperamos dicc de categorías si existe para poder ordenar y formatear
        dicc_cat_actual = st.session_state.get("ex_to_cat", {})
        lista_ejercicios_rutina = ordenar_ejercicios(df_rutina["Ejercicio"].unique().tolist(), dicc_cat_actual)

        col_sel, col_m1, col_m2 = st.columns([2, 1, 1])

        with col_sel:
            ejercicio_sel = st.selectbox(
                "Selecciona un ejercicio para ver su progresión:",
                options=lista_ejercicios_rutina,
                format_func=formato_ejercicio
            )

        df_ej = df_rutina[df_rutina["Ejercicio"] == ejercicio_sel].copy()
        es_principal = df_ej["Rol"].str.contains("Principal").any()

        with col_m1:
            st.metric("Total de Apariciones", f"{len(df_ej['Semana Global'].unique())} semanas")
        with col_m2:
            st.metric("Rol en Rutina", "Principal" if es_principal else "Accesorio")

        if es_principal:
            st.subheader(f"📈 Progresión de Cargas: {ejercicio_sel}")

            df_ej["Peso_Num"] = pd.to_numeric(df_ej["Peso Sugerido"], errors="coerce")

            df_top_sets = (
                df_ej.groupby(["Ciclo", "Semana Global", "Fase"])["Peso_Num"]
                .max()
                .reset_index()
            )

            st.line_chart(df_top_sets, x="Semana Global", y="Peso_Num", color="#FF4B4B")

            st.subheader("📋 Desglose Completo de Series por Semana")
            st.dataframe(
                df_ej[["Ciclo", "Semana Global", "Fase", "Día", "Peso Sugerido", "Reps Objetivo"]],
                use_container_width=True,
            )
        else:
            st.subheader(f"🧩 Programación de Accesorio: {ejercicio_sel}")
            st.info("Este ejercicio está asignado como accesorio 'A sensaciones'.")
            st.dataframe(
                df_ej[["Ciclo", "Semana Global", "Fase", "Día", "Reps Objetivo"]],
                use_container_width=True,
            )

    # ------------------------------------------
    # EXPORTACIÓN / DESCARGA
    # ------------------------------------------
    st.divider()
    st.subheader("📥 Exportar Rutina")

    col_csv, col_excel = st.columns(2)

    with col_csv:
        csv_bytes = df_rutina.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📄 Descargar como CSV",
            data=csv_bytes,
            file_name="Rutina_531.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_excel:
        try:
            buffer_excel = io.BytesIO()
            with pd.ExcelWriter(buffer_excel, engine="openpyxl") as writer:
                df_rutina.to_excel(writer, index=False, sheet_name="Rutina 531")
            st.download_button(
                label="📊 Descargar como Excel (.xlsx)",
                data=buffer_excel.getvalue(),
                file_name="Rutina_531.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception:
            st.caption("💡 *(Para descargar en Excel instala `openpyxl`, o usa el botón CSV)*")