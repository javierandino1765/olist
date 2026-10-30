"""Página 3 · Segmentación de vendedores (Parte 3B). K-Means + PCA (precalculado)."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import comun

ACCIONES = {
    "Grandes multicategoría": "Cuentas clave: soporte prioritario y tarifas de logística por volumen.",
    "Entrega lenta / alto retraso": "Plan de SLA: alertas de despacho y revisar transportistas. "
                                    "Es el segmento que más malas reseñas genera.",
    "Bajo ticket / flete alto": "Renegociar o subsidiar el flete; promover envío combinado o gratis desde un monto.",
    "Nicho premium confiable": "Fidelizar y usar como benchmark de servicio; ampliar su catálogo.",
}

comun.estado_api()

comun.encabezado("Segmentación de vendedores",
                 "K-Means agrupa a los vendedores por cómo operan (volumen, ticket, flete, retraso, entrega). "
                 "PCA los resume en dos ejes para dibujarlos.", etiqueta="★ Pregunta abierta · Opción 3B")

v = comun.cargar_csv("vendedores_segmentados.csv")
comun.exigir(v, "Falta `app/data/vendedores_segmentados.csv` (lo genera la Parte 3 del notebook).")

grupos = sorted(v["nombre_grupo"].unique())
colores = comun.color_grupos(grupos)
elegidos = st.pills("Grupos", grupos, selection_mode="multi", default=grupos)
if not elegidos:
    elegidos = grupos
vista = v[v["nombre_grupo"].isin(elegidos)]

# --- Perfil y acción por segmento (mismas cifras: medianas por grupo). Interacción: elegir la métrica
#     para comparar los grupos y hacer clic en una barra para destacar ese segmento ---
METRICAS = {
    "Pedidos": ("pedidos", lambda x: f"{x:.0f}", "pedidos (mediana)"),
    "Ticket": ("ticket_medio", lambda x: f"${x:.0f}", "ticket medio (mediana)"),
    "Retraso": ("tasa_retraso", lambda x: f"{x*100:.0f}%", "tasa de retraso (mediana)"),
    "Entrega": ("dias_entrega_prom", lambda x: f"{x:.0f} d", "días de entrega (mediana)"),
    "Vendedores": (None, lambda x: f"{x:.0f}", "vendedores en el segmento"),
}
with st.container(border=True, key="card-perfil"):
    st.subheader("Perfil y acción por segmento")
    metrica = st.segmented_control("Comparar segmentos por", list(METRICAS), default="Retraso",
                                   key="metrica_seg") or "Retraso"
    col_m, fmt_m, desc_m = METRICAS[metrica]
    valores = {g: (len(v[v["nombre_grupo"] == g]) if col_m is None
                   else float(v.loc[v["nombre_grupo"] == g, col_m].median())) for g in elegidos}
    orden_g = sorted(elegidos, key=lambda g: valores[g])
    b1, b2 = st.columns([0.58, 0.42], gap="large")
    figp = go.Figure(go.Bar(
        y=orden_g, x=[valores[g] for g in orden_g], orientation="h",
        marker_color=[colores[g] for g in orden_g], marker_line_width=0,
        text=[fmt_m(valores[g]) for g in orden_g], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>" + desc_m + ": %{text}<extra></extra>",
        unselected=dict(marker=dict(opacity=0.3))))
    figp.update_layout(height=max(220, 64 * len(orden_g)), xaxis_title=desc_m.capitalize(), bargap=0.3,
                       hovermode="closest", clickmode="event+select", margin=dict(l=10, r=50, t=10, b=10))
    figp.update_xaxes(showgrid=True, gridcolor=comun.COLOR["rejilla"],
                      tickformat=".0%" if col_m == "tasa_retraso" else None)
    with b1:
        evp = st.plotly_chart(comun.fig_olist(figp), width="stretch", theme=None, on_select="rerun",
                              selection_mode="points", key="graf_perfil", config={"displayModeBar": False})
    ptp = comun.punto_elegido(evp)
    foco = ptp[0].get("y") if ptp else None
    with b2:
        if foco in elegidos:
            sub = v[v["nombre_grupo"] == foco]
            def comp(col, f, invertir=False):
                vg, vt = sub[col].median(), v[col].median()
                tono = ("down" if vg > vt else "up") if invertir else "flat"
                return f'<span class="ol-pill {tono}">general {f(vt)}</span>'
            st.markdown(
                f'<div class="ol-group ol-anim" style="--c:{colores[foco]};border-top-width:.4rem">'
                f'<p class="gname">{foco}</p><div class="gcount">{len(sub)}<small>vendedores</small></div>'
                f'<dl><div><dt>Pedidos</dt><dd>{sub["pedidos"].median():.0f}</dd>'
                f'{comp("pedidos", lambda x: f"{x:.0f}")}</div>'
                f'<div><dt>Ticket</dt><dd>${sub["ticket_medio"].median():.0f}</dd>'
                f'{comp("ticket_medio", lambda x: f"${x:.0f}")}</div>'
                f'<div><dt>Retraso</dt><dd>{sub["tasa_retraso"].median()*100:.0f}%</dd>'
                f'{comp("tasa_retraso", lambda x: f"{x*100:.0f}%", True)}</div>'
                f'<div><dt>Entrega</dt><dd>{sub["dias_entrega_prom"].median():.0f} d</dd>'
                f'{comp("dias_entrega_prom", lambda x: f"{x:.0f} d", True)}</div></dl>'
                f'<p class="accion"><b>Acción:</b> {ACCIONES.get(foco, "")}</p></div>', unsafe_allow_html=True)
        else:
            st.markdown("**Elige un segmento**")
            st.write(f"El gráfico compara los segmentos por **{desc_m}**. Haz clic en una barra para ver "
                     "el perfil completo de ese segmento, comparado con el total de vendedores, y su acción.")
            st.caption("Cambia la métrica con los botones de arriba.")

# Fichas de todos los segmentos (el elegido queda resaltado)
fichas = []
for g in elegidos:
    sub = v[v["nombre_grupo"] == g]
    clase = " sel" if g == foco else (" dim" if foco else "")
    fichas.append(
        f'<div class="ol-group{clase}" style="--c:{colores[g]}"><p class="gname">{g}</p>'
        f'<div class="gcount">{len(sub)}<small>vendedores</small></div>'
        f'<dl><div><dt>Pedidos</dt><dd>{sub["pedidos"].median():.0f}</dd></div>'
        f'<div><dt>Ticket</dt><dd>${sub["ticket_medio"].median():.0f}</dd></div>'
        f'<div><dt>Retraso</dt><dd>{sub["tasa_retraso"].median()*100:.0f}%</dd></div>'
        f'<div><dt>Entrega</dt><dd>{sub["dias_entrega_prom"].median():.0f} d</dd></div></dl>'
        f'<p class="accion">{ACCIONES.get(g, "")}</p></div>')
st.markdown(f'<div class="ol-groups ol-anim" style="--n:{len(elegidos)}">{"".join(fichas)}</div>',
            unsafe_allow_html=True)

# --- Mapa PCA. Animación: los vendedores aparecen grupo por grupo. Interacción: seleccionar en el mapa ---
with st.container(border=True, key="card-pca"):
    st.subheader("Mapa de vendedores (PCA)")
    fig = px.scatter(vista, x="pca1", y="pca2", color="nombre_grupo", size="ventas", size_max=26,
                     hover_name="seller_id", hover_data={"pedidos": True, "tasa_retraso": ":.2f"},
                     custom_data=["seller_id"], color_discrete_map=colores, render_mode="svg",
                     labels={"pca1": "Componente 1", "pca2": "Componente 2", "nombre_grupo": "Grupo"})
    fig.update_traces(marker=dict(line=dict(color="#FFFFFF", width=0.8), opacity=0.82))
    fig.update_layout(height=460, legend=dict(orientation="h", y=-0.2, title_text=""), hovermode="closest")
    ev = st.plotly_chart(comun.fig_olist(fig), width="stretch", theme=None, on_select="rerun",
                         selection_mode=("points", "box", "lasso"), key="pca")
    st.caption("Selecciona vendedores en el mapa (clic, caja o lazo) para verlos en la tabla.")

pts = comun.punto_elegido(ev)
seleccion = [p["customdata"][0] for p in pts] if pts else []

# --- Detalle por vendedor: tabla con barras animadas (mismas columnas que antes) ---
st.subheader("Detalle por vendedor")
det = vista[vista["seller_id"].isin(seleccion)] if seleccion else vista
det = det.sort_values("ventas", ascending=False).reset_index(drop=True)
tope = float(v["pedidos"].max()) or 1.0
filas = []
for i, r in det.iterrows():
    ancho = max(0.0, min(100.0, float(r["pedidos"]) / tope * 100))
    filas.append(
        f'<tr style="--i:{min(i, 18)}"><td class="l" title="{r["seller_id"]}">{r["seller_id"][:8]}…</td>'
        f'<td class="l">{r["seller_state"]}</td>'
        f'<td class="l"><span class="ol-dot" style="background:{colores[r["nombre_grupo"]]}"></span> '
        f'{r["nombre_grupo"]}</td>'
        f'<td><div class="ol-barcell"><span class="ol-track"><span class="ol-fill" style="width:{ancho:.1f}%">'
        f'</span></span><span class="ol-num">{r["pedidos"]:,.0f}</span></div></td>'
        f'<td>${r["ventas"]:,.0f}</td><td>${r["ticket_medio"]:,.0f}</td><td>{r["flete_relativo"]:.2f}</td>'
        f'<td>{r["tasa_retraso"]:.2f}</td><td>{r["dias_entrega_prom"]:.1f}</td><td>{r["n_categorias"]:.0f}</td></tr>')
st.markdown(
    '<div class="ol-tbl ol-anim ol-tbl-vend"><table><thead><tr><th class="l">Vendedor</th><th class="l">Estado</th>'
    '<th class="l">Grupo</th><th class="l">Pedidos</th><th>Ventas</th><th>Ticket</th><th>Flete rel.</th>'
    '<th>Tasa retraso</th><th>Días entrega</th><th>Categorías</th></tr></thead><tbody>'
    + "".join(filas) + "</tbody></table></div>", unsafe_allow_html=True)
st.caption(f"{len(det):,} vendedores" + (" seleccionados en el mapa." if seleccion else ", ordenados por ventas.")
           )
