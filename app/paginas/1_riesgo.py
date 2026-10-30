"""Página 1 · Riesgo de un pedido. Elige/edita un pedido y consulta POST /riesgo."""
import pandas as pd
import requests
import streamlit as st

import comun

CONTRATO17 = ["order_id","order_purchase_timestamp","order_approved_at","order_delivered_carrier_date",
              "order_delivered_customer_date","order_estimated_delivery_date","estado_cliente","n_items",
              "n_vendedores","precio_total","flete_total","peso_total_g","fotos_promedio","categoria",
              "estado_vendedor","tipo_pago","cuotas_max"]

ok = comun.estado_api()

comun.encabezado("Riesgo de mala reseña",
                 "Elige un pedido de ejemplo, ajústalo si quieres y pregúntale a la API qué tan probable es "
                 "que reciba una reseña de 1 o 2 estrellas.", etiqueta="★ Riesgo de un pedido")

muestra = comun.cargar_csv("pedidos_muestra.csv")
comun.exigir(muestra, "Falta `app/data/pedidos_muestra.csv`.")

# --- Elegir un pedido de ejemplo y ajustarlo (barra de controles) ---
etiquetas = (muestra["order_id"].str[:8] + "…  ·  " + muestra["estado_cliente"] +
             "  ·  $" + muestra["precio_total"].round(0).astype(int).astype(str))
with st.container(border=True, key="card-toolbar"):
    t1, t2 = st.columns([0.5, 0.5], gap="large")
    with t1:
        i = st.selectbox("Pedido de ejemplo", muestra.index, format_func=lambda k: etiquetas[k])
    with t2:
        extra = st.slider("Días de retraso extra (simulación)", -10, 30, 0,
                          help="Suma días a la fecha de entrega para ver cómo cambia el riesgo.")
fila = muestra.loc[i]

pedido = fila[CONTRATO17].astype(object).where(fila[CONTRATO17].notna(), None).to_dict()
if extra != 0 and pedido["order_delivered_customer_date"]:
    nueva = pd.to_datetime(pedido["order_delivered_customer_date"]) + pd.Timedelta(days=extra)
    pedido["order_delivered_customer_date"] = nueva.strftime("%Y-%m-%d %H:%M:%S")

# --- Presentación del pedido agrupada por tema (mismos 17 campos que se envían a la API) ---
GRUPOS = {
    "Fechas": [("Compra", "order_purchase_timestamp"), ("Pago aprobado", "order_approved_at"),
               ("Entrega al transportista", "order_delivered_carrier_date"),
               ("Entrega al cliente", "order_delivered_customer_date"),
               ("Fecha prometida", "order_estimated_delivery_date")],
    "Pedido": [("Artículos", "n_items"), ("Vendedores", "n_vendedores"), ("Precio total", "precio_total"),
               ("Flete total", "flete_total"), ("Peso total (g)", "peso_total_g"),
               ("Fotos promedio", "fotos_promedio"), ("Categoría", "categoria")],
    "Pago y geografía": [("Tipo de pago", "tipo_pago"), ("Cuotas máximas", "cuotas_max"),
                         ("Estado del cliente", "estado_cliente"), ("Estado del vendedor", "estado_vendedor")],
}


def _fmt(campo, v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '<span style="color:#8A93A6">—</span>'
    if campo in ("precio_total", "flete_total"):
        return f"${float(v):,.2f}"
    return str(v)


c1, c2 = st.columns([0.52, 0.48], gap="large")
with c1:
    with st.container(border=True, key="card-pedido"):
        st.markdown(f"**Pedido que se enviará a la API** &nbsp; "
                    f'<span class="ol-pill blue">{pedido["order_id"][:12]}…</span>', unsafe_allow_html=True)
        filas_html = []
        for tema, campos in GRUPOS.items():
            filas_html.append(f'<tr><th class="l" colspan="2" style="position:static;background:#F4F6FB;'
                              f'color:#2348F2">{tema}</th></tr>')
            for etiqueta, campo in campos:
                marca = (' <span class="ol-pill down">+%d días</span>' % extra
                         if campo == "order_delivered_customer_date" and extra > 0 else
                         (' <span class="ol-pill up">%d días</span>' % extra
                          if campo == "order_delivered_customer_date" and extra < 0 else ""))
                filas_html.append(f'<tr><td class="l" style="color:#5B6478">{etiqueta}</td>'
                                  f'<td class="l"><b>{_fmt(campo, pedido[campo])}</b>{marca}</td></tr>')
        st.markdown('<div class="ol-tbl" style="max-height:none"><table>' + "".join(filas_html) +
                    "</table></div>", unsafe_allow_html=True)

with c2:
    # --- Interacción: cálculo automático al cambiar el pedido o los días (misma llamada a la API) ---
    auto = st.toggle("Calcular automáticamente al cambiar el pedido", value=True,
                     help="Si lo apagas, el riesgo se calcula solo al pulsar el botón.")
    if "historial" not in st.session_state:
        st.session_state["historial"] = []
    cache = st.session_state.setdefault("respuestas", {})   # no repetir la misma consulta a la API

    def consultar(ped):
        clave = (ped["order_id"], ped["order_delivered_customer_date"])
        if clave not in cache:
            r = comun.post_riesgo(ped)
            if r.status_code != 200:
                return None, r
            cache[clave] = r.json()
        return cache[clave], None

    pedir = False
    if not ok:
        st.warning("La API no responde: no se puede calcular el riesgo ahora.")
    else:
        boton = st.button("Calcular riesgo", type="primary", icon=":material/query_stats:", width="stretch",
                          disabled=auto)
        pedir = auto or boton

    if ok and pedir:
        try:
            res, error = consultar(pedido)
        except requests.RequestException:
            st.error("La API no respondió a tiempo. Intenta de nuevo en un minuto."); st.stop()
        if error is not None:
            try:                                             # FastAPI responde JSON; Render/errores 500, texto o HTML
                detalle = error.json().get("detail", "")
            except ValueError:
                detalle = error.text[:300]
            st.error(f"La API rechazó el pedido (código {error.status_code}): {detalle}")
        else:
            prob, umb = res["probabilidad"], res["umbral"]
            alto = res["riesgo_alto"]
            col = comun.COLOR["riesgo"] if alto else comun.COLOR["ok"]
            msg = "🔴 Riesgo alto: contactar al cliente." if alto else "🟢 Riesgo normal."

            # Comparación con el mismo pedido sin días extra (otra consulta al mismo endpoint)
            comparacion = ""
            if extra != 0:
                base = fila[CONTRATO17].astype(object).where(fila[CONTRATO17].notna(), None).to_dict()
                try:
                    res0, _ = consultar(base)
                except requests.RequestException:
                    res0 = None
                if res0:
                    d = (prob - res0["probabilidad"]) * 100
                    tono = "down" if d > 0 else "up"
                    comparacion = (f'<p class="cmp">Sin retraso extra: <b>{res0["probabilidad"]*100:.0f}%</b> → '
                                   f'con {extra:+d} días: <b>{prob*100:.0f}%</b> '
                                   f'<span class="ol-pill {tono}">{d:+.0f} puntos</span></p>')

            pct = round(prob * 100)
            st.markdown(
                f'<div class="ol-result ol-anim" style="--c:{col}">'
                f'<p class="k">Probabilidad de 1–2 estrellas</p>'
                f'<p class="big ol-count" style="--to:{pct}"><span>{pct}%</span></p>'
                f'<div class="ol-meter"><span class="rail"></span>'
                f'<span class="fill" style="width:{min(prob, 1)*100:.1f}%"></span>'
                f'<span class="umb" style="left:{umb*100:.1f}%"><span>umbral {umb*100:.0f}%</span></span>'
                f'<span class="tick" style="left:0">0%</span>'
                f'<span class="tick" style="right:0">100%</span></div>'
                f'<p class="msg">{msg}</p>{comparacion}</div>', unsafe_allow_html=True)
            st.caption(f"Umbral de riesgo alto (10% más riesgoso): **{umb*100:.0f}%**. "
                       "La línea blanca de la barra marca ese umbral.")

            # Historial de simulaciones de la sesión (cada combinación pedido + días, una vez)
            etiqueta = f'{pedido["order_id"][:6]}… {extra:+d} d'
            hist = st.session_state["historial"]
            if not hist or hist[-1]["etiqueta"] != etiqueta:
                hist.append({"etiqueta": etiqueta, "prob": prob, "alto": alto})
                del hist[:-12]
            with st.expander("Respuesta completa de la API", icon=":material/data_object:"):
                st.json(res)
    elif ok:
        with st.container(border=True, key="card-espera"):
            st.markdown("#### ¿Qué tan riesgoso es este pedido?")
            st.write("Pulsa **Calcular riesgo** para consultar la API. Si la probabilidad alcanza el "
                     "umbral del 10% más riesgoso, la app sugiere contactar al cliente.")

# --- Historial: compara las simulaciones de esta sesión ---
hist = st.session_state.get("historial", [])
if len(hist) >= 2:
    import plotly.graph_objects as go
    with st.container(border=True, key="card-historial"):
        st.subheader("Tus simulaciones")
        st.caption("Cada barra es un cálculo de esta sesión. Cambia el pedido o los días de retraso y "
                   "compara cómo se mueve el riesgo frente al umbral.")
        umb_h = cache_umb = None
        try:
            umb_h = next(iter(st.session_state["respuestas"].values()))["umbral"]
        except StopIteration:
            pass
        figh = go.Figure(go.Bar(
            x=[h["etiqueta"] for h in hist], y=[h["prob"] * 100 for h in hist],
            marker_color=[comun.COLOR["riesgo"] if h["alto"] else comun.COLOR["ok"] for h in hist],
            marker_line_width=0, text=[f'{h["prob"]*100:.0f}%' for h in hist], textposition="outside",
            cliponaxis=False, hovertemplate="%{x}<br>Probabilidad: %{y:.0f}%<extra></extra>"))
        if umb_h is not None:
            figh.add_hline(y=umb_h * 100, line_dash="dash", line_color=comun.COLOR["estrella"], line_width=2,
                           annotation_text=f"umbral {umb_h*100:.0f}%", annotation_font_color="#5B6478")
        figh.update_layout(height=260, yaxis_title="Probabilidad (%)", hovermode="closest", bargap=0.35,
                           yaxis=dict(range=[0, max(100, max(h["prob"] for h in hist) * 110)]))
        st.plotly_chart(comun.fig_olist(figh), width="stretch", theme=None, config={"displayModeBar": False})
        if st.button("Borrar historial", icon=":material/delete:"):
            st.session_state["historial"] = []
            st.rerun()
