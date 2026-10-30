"""App Olist · del pedido a la reseña. Multipágina (st.navigation + st.Page).
La app nunca carga el modelo: le pregunta a la API y lee los CSV precalculados."""
import streamlit as st

st.set_page_config(page_title="Olist · Riesgo de reseña", page_icon="🛒", layout="wide")

paginas = {
    "Resumen": [
        st.Page("paginas/0_resumen.py", title="Resumen", icon=":material/dashboard:", default=True),
    ],
    "Modelo": [
        st.Page("paginas/1_riesgo.py", title="Riesgo de un pedido", icon=":material/warning:"),
        st.Page("paginas/4_ficha.py", title="Ficha del modelo", icon=":material/description:"),
    ],
    "Análisis": [
        st.Page("paginas/2_comentarios.py", title="Comentarios", icon=":material/reviews:"),
        st.Page("paginas/3_segmentacion.py", title="Segmentación de vendedores", icon=":material/scatter_plot:"),
    ],
}
st.navigation(paginas, position="sidebar").run()
