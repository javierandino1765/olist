"""Página 2 · Comentarios (Parte 4). Sentimiento del texto vs estrellas."""
import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import comun

comun.estado_api()

comun.encabezado("Comentarios: ¿coincide el texto con las estrellas?",
                 "Un modelo preentrenado de Hugging Face (portugués) clasifica el sentimiento del comentario; "
                 "lo comparamos con las estrellas que puso el cliente.", etiqueta="★ Comentarios")

s = comun.cargar_csv("sentimiento_muestra.csv")
comun.exigir(s, "Falta `app/data/sentimiento_muestra.csv` (lo genera la Parte 4 del notebook).")

coincide = (s["estrellas_lbl"] == s["sentimiento"]).mean()
orden = ["negative", "neutral", "positive"]
NOM = comun.NOMBRE_SENTIMIENTO

comun.banda_kpis([
    {"lab": "Comentarios analizados", "val": f"{len(s):,}"},
    {"lab": "Coincidencia texto vs estrellas", "val": f"{coincide*100:.1f}%"},
])

# --- Tabla cruzada (mismos datos que antes), dibujada como 9 cuadros independientes:
#     cada celda aparece por separado y responde al clic. Interacción: cambiar la vista y elegir una celda ---
tab = pd.crosstab(s["estrellas_lbl"], s["sentimiento"]).reindex(index=orden, columns=orden).fillna(0)
with st.container(border=True, key="card-cruce"):
    h1, h2 = st.columns([0.6, 0.4], vertical_alignment="bottom")
    h1.subheader("Estrellas vs sentimiento")
    vista_cruce = h2.segmented_control("Ver como", ["Conteo", "% por fila"], default="Conteo",
                                       key="vista_cruce", label_visibility="collapsed")
    pct_fila = vista_cruce == "% por fila"
    g1, g2 = st.columns([0.62, 0.38], gap="large")
    cx, cy, cz, ct, cc = [], [], [], [], []
    for fi in orden:
        total_fila = tab.loc[fi].sum() or 1
        for co in orden:
            n = int(tab.loc[fi, co])
            cx.append(NOM[co]); cy.append(NOM[fi]); cz.append(n)
            valor = n / total_fila * 100 if pct_fila else n
            cc.append(valor)
            ct.append(f"{valor:.0f}%" if pct_fila else f"{n:,}")
    tope = max(cc) or 1
    fig = go.Figure(go.Scatter(
        x=cx, y=cy, mode="markers+text", text=ct, customdata=cz,
        textfont=dict(size=17, family="Plus Jakarta Sans, sans-serif",
                      color=["#FFFFFF" if v / tope > 0.55 else "#0B1736" for v in cc]),
        marker=dict(size=92, symbol="square", color=cc, cmin=0, cmax=tope, line=dict(width=0),
                    colorscale=[[0, "#EEF2FF"], [0.35, "#9DB0FF"], [1, "#2348F2"]]),
        hovertemplate="Estrellas: %{y}<br>Texto: %{x}<br>%{customdata} comentarios<extra></extra>",
        selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=0.35))))
    fig.update_layout(height=380, xaxis_title="Sentimiento del texto (modelo)",
                      yaxis_title="Estrellas (cliente)", clickmode="event+select", hovermode="closest")
    # Límites fijos y y invertido: mismo orden que antes (negativo arriba)
    fig.update_xaxes(range=[-0.6, 2.6], showline=False, ticks="")
    fig.update_yaxes(range=[2.6, -0.6], showgrid=False, ticks="")
    with g1:
        ev = st.plotly_chart(comun.fig_olist(fig), width="stretch", theme=None, on_select="rerun",
                             selection_mode="points", key="graf_cruce", config={"displayModeBar": False})
    pts = comun.punto_elegido(ev)
    inv = {v: k for k, v in NOM.items()}
    celda = (inv.get(pts[0].get("y")), inv.get(pts[0].get("x"))) if pts else None
    with g2:
        if celda and None not in celda:
            n = int(tab.loc[celda[0], celda[1]])
            pf = n / (tab.loc[celda[0]].sum() or 1) * 100
            acuerdo = celda[0] == celda[1]
            st.markdown(f"**Estrellas {NOM[celda[0]].lower()} · texto {NOM[celda[1]].lower()}**")
            st.markdown(f'<p style="font-size:2.4rem;font-weight:800;margin:.2rem 0">{n:,}'
                        f'<span style="font-size:1rem;color:#5B6478;font-weight:600"> comentarios</span></p>',
                        unsafe_allow_html=True)
            st.markdown(comun.chip("Acuerdo" if acuerdo else "Desacuerdo",
                                   comun.COLOR["ok"] if acuerdo else comun.COLOR["riesgo"]) +
                        f' &nbsp;<span class="ol-pill flat">{pf:.0f}% de su fila</span>', unsafe_allow_html=True)
            st.caption("Abajo se muestran los comentarios de esta celda. Haz clic en otra celda para cambiar.")
        else:
            st.markdown("**Cómo leer la tabla**")
            st.write("Cada cuadro cuenta comentarios según sus estrellas (filas) y lo que dice el texto "
                     "(columnas). La diagonal es acuerdo.")
            st.caption("Cambia a **% por fila** para comparar grupos de estrellas de distinto tamaño. "
                       "Haz clic en un cuadro para ver sus comentarios.")
    st.caption("La diagonal es acuerdo. La mayor confusión está en los **neutros (3★)** y en positivos que el "
               "modelo marca como neutros: el texto a veces dice más —o menos— que la nota.")

# --- Comentarios: los desacuerdos (o la celda elegida) como tarjetas ---
if celda and None not in celda:
    st.subheader(f"Comentarios: estrellas {NOM[celda[0]].lower()}, texto {NOM[celda[1]].lower()}")
    base = s[(s["estrellas_lbl"] == celda[0]) & (s["sentimiento"] == celda[1])].copy()
else:
    st.subheader("Desacuerdos")
    base = s[s["estrellas_lbl"] != s["sentimiento"]].copy()

estrellas_disp = sorted(s["review_score"].unique())
f1, f2 = st.columns(2, gap="large")
with f1:
    filtro = st.pills("Filtrar por estrellas", estrellas_disp, selection_mode="multi", default=estrellas_disp,
                      format_func=lambda k: f"{int(k)} ★")
with f2:
    filtro_txt = st.pills("Filtrar por sentimiento del texto", orden, selection_mode="multi", default=orden,
                          format_func=lambda k: NOM[k], key="filtro_txt")
if not filtro:
    filtro = estrellas_disp
if not filtro_txt:
    filtro_txt = orden
filtrados = base[base["review_score"].isin(filtro) & base["sentimiento"].isin(filtro_txt)]
des = filtrados.head(50)

tarjetas = []
for _, r in des.iterrows():
    col = comun.COLOR_SENTIMIENTO.get(r["sentimiento"], "#8A93A6")
    texto = html.escape(str(r["review_comment_message"]))
    tarjetas.append(
        f'<div class="ol-comment" style="--c:{col}"><div class="top">{comun.estrellas(r["review_score"])}'
        f'<span>Estrellas: <b>{NOM.get(r["estrellas_lbl"], r["estrellas_lbl"])}</b></span>'
        f'{comun.chip("Texto: " + NOM.get(r["sentimiento"], r["sentimiento"]), col)}</div>'
        f'<p>{texto}</p></div>')
if tarjetas:
    st.markdown('<div class="ol-comments ol-anim">' + "".join(tarjetas) + "</div>", unsafe_allow_html=True)
    st.caption(f"Se muestran {len(des)} de {len(filtrados):,} comentarios (máximo 50).")
else:
    st.info("No hay comentarios con ese filtro.")
st.caption("Clasificación de los desacuerdos: textos muy cortos o con ironía → suele ser error del modelo; "
           "5★ con queja en el texto (o 1★ con texto neutro) → la nota no concuerda con lo escrito.")
