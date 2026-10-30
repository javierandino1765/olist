"""Página de inicio · Resumen. Reúne en una pantalla las respuestas a las preguntas del proyecto.
No calcula nada nuevo: usa las mismas cifras de la Ficha y los mismos archivos de las demás páginas."""
import plotly.graph_objects as go
import streamlit as st

import comun

comun.estado_api()

comun.encabezado("Del pedido a la reseña",
                 "Lo esencial del proyecto en una pantalla: a quiénes llamar, qué dicen los clientes, qué tipos "
                 "de vendedores hay y cuánto confiar en el modelo.", etiqueta="★ Resumen")

F = comun.FICHA

# --- La idea central, interactiva: de cada 10 clientes que llamamos, ¿cuántos iban a dejar mala reseña? ---
with st.container(border=True, key="card-llamadas"):
    st.subheader("De cada 10 clientes que llamamos, ¿cuántos iban a dejar una mala reseña?")
    st.caption("Atención al cliente solo puede llamar a 1 de cada 10 pedidos. Cada fila muestra qué pasa si "
               "elige a quién llamar al azar, con la regla del retraso o con el modelo. Pasa el cursor sobre "
               "una persona para ver qué pasa con esa llamada.")
    filas = [("Al azar", F["azar"]), ("Regla del retraso", F["regla_retraso"]), ("Nuestro modelo", F["precision_10"])]
    xs, ys, colores, textos = [], [], [], []
    for nombre, p in filas:
        aciertos = p * 10
        for k in range(10):
            xs.append(k + 1); ys.append(nombre)
            lleno = k + 1 <= round(aciertos)
            colores.append(comun.COLOR["riesgo"] if lleno else "#DCE1EC")
            estado = ("🔴 <b>Iba a dejar 1–2 estrellas</b><br>la llamada llega a tiempo" if lleno
                      else "⚪ <b>Cliente satisfecho</b><br>la llamada no era necesaria")
            textos.append(f"<b>{nombre}</b> · llamada {k + 1} de 10<br>{estado}<br>"
                          f"<span style='color:#B9C3DB'>{aciertos:.1f} de cada 10 llamadas "
                          f"llegan a un cliente en riesgo</span>")
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="markers", marker=dict(size=30, symbol="circle", color=colores, line=dict(width=0)),
        hovertext=textos, hovertemplate="%{hovertext}<extra></extra>",
        hoverlabel=dict(bgcolor=comun.COLOR["marino"], bordercolor=comun.COLOR["marino"], align="left",
                        font=dict(color="#FFFFFF", size=13, family="Plus Jakarta Sans, sans-serif"))))
    for nombre, p in filas:
        fig.add_annotation(x=11.1, y=nombre, xanchor="left", showarrow=False,
                           text=f"<b>{p*10:.1f}</b> de 10", font=dict(size=15, color=comun.COLOR["marino"]))
    fig.update_layout(height=250, hovermode="closest", margin=dict(l=10, r=90, t=10, b=10))
    fig.update_xaxes(visible=False, range=[0.4, 11])
    fig.update_yaxes(showgrid=False, ticks="", categoryorder="array", categoryarray=[f[0] for f in filas])
    st.plotly_chart(comun.fig_olist(fig), width="stretch", theme=None, key="graf_resumen",
                    config={"displayModeBar": False})
    st.caption(f"Con el modelo, la precisión en el 10% de mayor riesgo es {F['precision_10']:.3f}: "
               f"unas {F['mejora_azar']:.2f} veces más que llamando al azar, y un poco más que la "
               "regla del retraso.")


# --- Las cuatro preguntas ---
def tarjeta(clave, numero, pregunta, titular, detalle, pagina, boton, icono):
    with st.container(border=True, key=f"card-q{clave}", height="stretch"):
        st.markdown(f'<div class="ol-q"><p class="ol-q-num"><span>{numero}</span>{pregunta}</p>'
                    f'<p class="ol-q-big">{titular}</p><p class="ol-q-txt">{detalle}</p></div>',
                    unsafe_allow_html=True)
        st.page_link(pagina, label=boton, icon=icono)


s = comun.cargar_csv("sentimiento_muestra.csv")
v = comun.cargar_csv("vendedores_segmentados.csv")

a, b = st.columns(2, gap="medium")
with a:
    tarjeta(1, 1, "¿A quiénes llamar primero?", f"Riesgo desde {F['umbral']*100:.0f}%",
            f"Un pedido entra en el 10% más riesgoso si su probabilidad de 1–2 estrellas alcanza el "
            f"{F['umbral']*100:.0f}%. Esos son los clientes que conviene llamar justo después de la entrega.",
            "paginas/1_riesgo.py", "Calcular el riesgo de un pedido", ":material/warning:")
with b:
    if s is not None:
        coincide = (s["estrellas_lbl"] == s["sentimiento"]).mean()
        tarjeta(2, 2, "¿Coincide el texto con las estrellas?", f"{coincide*100:.1f}% de acuerdo",
                f"En {len(s):,} comentarios, el sentimiento del texto coincide con las estrellas en "
                f"{coincide*100:.1f}% de los casos. Los desacuerdos muestran lo que la nota no dice.",
                "paginas/2_comentarios.py", "Leer los comentarios", ":material/reviews:")

c, d = st.columns(2, gap="medium")
with c:
    if v is not None:
        peor = v.groupby("nombre_grupo")["tasa_retraso"].median().idxmax()
        sub = v[v["nombre_grupo"] == peor]
        tarjeta(3, 3, "¿Qué tipos de vendedores hay?", f"{v['nombre_grupo'].nunique()} segmentos",
                f"El segmento con más retraso es «{peor}»: {len(sub)} vendedores con una tasa de retraso "
                f"mediana de {sub['tasa_retraso'].median()*100:.0f}%. Cada segmento tiene su propia acción.",
                "paginas/3_segmentacion.py", "Ver la segmentación", ":material/scatter_plot:")
with d:
    tarjeta(4, 4, "¿Cuánto confiar en el modelo?", f"Precisión {F['precision_10']:.3f}",
            f"De cada 10 clientes que llama, unos {F['precision_10']*10:.0f} iban a dejar mala reseña. "
            f"Supera al azar ({F['azar']:.3f}) y, por poco, a la regla del retraso ({F['regla_retraso']:.3f}).",
            "paginas/4_ficha.py", "Leer la ficha del modelo", ":material/description:")
