"""Página 4 · Ficha del modelo (Parte 6). Muestra ficha_modelo.md y las métricas clave."""
import streamlit as st

import comun

comun.estado_api()

comun.encabezado("Ficha del modelo",
                 "Qué hace el modelo, qué tan bien funciona, dónde falla y para qué no debe usarse.",
                 etiqueta="★ Ficha del modelo")

# Mismas cifras de siempre (salen del notebook: validación por fecha)
comun.banda_kpis([
    {"lab": "Precisión en el 10% de mayor riesgo", "val": "0.663",
     "nota": '<span class="ol-pill up">×4.5 vs azar</span>'},
    {"lab": "Regla del retraso", "val": "0.621",
     "nota": '<span class="ol-pill flat">el modelo la supera (×1.07)</span>'},
    {"lab": "Umbral de riesgo alto", "val": "27%",
     "nota": '<span class="ol-pill flat">10% más riesgoso</span>'},
])

ficha = comun.cargar_texto("ficha_modelo.md")
comun.exigir(ficha, "Falta `app/data/ficha_modelo.md`.")

# El documento es el mismo ficha_modelo.md; solo se presenta como acordeón:
# el título y la introducción a la vista, y cada sección ("## ...") se despliega al hacer clic.
titulo, intro, secciones = "", [], []
for linea in ficha.splitlines():
    if linea.startswith("# ") and not titulo:
        titulo = linea[2:].strip()
    elif linea.startswith("## "):
        secciones.append([linea[3:].strip(), []])
    elif secciones:
        secciones[-1][1].append(linea)
    else:
        intro.append(linea)

PALABRAS_PREGUNTA = ("para qué", "qué", "a quién", "quién", "cómo", "cuándo", "cuánto", "dónde", "por qué")


def como_pregunta(nombre: str) -> str:
    """Agrega ¿? a los títulos que son preguntas ("1. Para qué sirve" → "1. ¿Para qué sirve?")."""
    numero, _, texto = nombre.partition(" ")
    if not numero.rstrip(".").isdigit():
        numero, texto = "", nombre
    if texto.lower().startswith(PALABRAS_PREGUNTA) and not texto.startswith("¿"):
        texto = f"¿{texto}?"
    return f"{numero} {texto}".strip()


with st.container(border=True, key="card-ficha"):
    st.markdown(f'<p class="ol-ficha-t">{titulo}</p>', unsafe_allow_html=True)
    st.markdown("\n".join(intro).strip())
    abrir = st.toggle("Abrir todas las respuestas", value=False, key="ficha_abrir")
    for nombre, cuerpo in secciones:
        with st.expander(como_pregunta(nombre), expanded=abrir):
            st.markdown("\n".join(cuerpo).strip())
