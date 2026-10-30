"""Funciones compartidas de la app Olist: dirección de la API (desde st.secrets),
llamadas con manejo de errores, y carga de los CSV precalculados."""
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import requests
import streamlit as st

DATA = Path(__file__).parent / "data"


def api_url() -> str:
    if st.session_state.get("API_URL_manual"):
        return st.session_state["API_URL_manual"].rstrip("/")
    try:
        return st.secrets["API_URL"].rstrip("/")      # función avanzada: st.secrets
    except Exception:
        return "http://127.0.0.1:8000"


@st.cache_data(ttl=600, show_spinner=False)            # función avanzada: @st.cache_data
def _get(url: str) -> dict:
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return r.json()


def post_riesgo(pedido: dict, intentos: int = 4):
    """Render responde 502/503/504 mientras despierta o reinicia la API: reintenta con espera creciente."""
    with st.spinner("Consultando la API… (si estaba dormida puede tardar hasta un minuto)"):
        for k in range(intentos):
            r = requests.post(f"{api_url()}/riesgo", json=pedido, timeout=90)
            if r.status_code not in (502, 503, 504) or k == intentos - 1:
                return r
            time.sleep(5 * (k + 1))


def estado_api() -> bool:
    """Barra lateral con el estado de la API. Devuelve True si responde."""
    estilos()
    with st.sidebar:
        st.markdown(
            '<div class="ol-brand"><span class="ol-mark">★</span><span class="ol-name">Olist</span></div>'
            '<p class="ol-brand-sub">Del pedido a la reseña · modelo de riesgo (vía API), comentarios '
            'y segmentación</p>', unsafe_allow_html=True)
        animar_al_ver()
        try:
            _get(f"{api_url()}/")
            st.success("API en línea")
            ok = True
        except requests.RequestException:
            st.error("No se pudo conectar con la API. Si está en Render, el plan gratuito la "
                     "**duerme** tras 15 min: abre su link, espera ~1 min y recarga.")
            ok = False
        with st.popover("⚙️ Configurar API"):           # función avanzada: st.popover
            st.text_input("URL de la API", value=api_url(), key="API_URL_manual",
                          help="En producción se define en Secrets como API_URL.")
            if st.button("Reintentar"):
                st.cache_data.clear(); st.rerun()
    return ok


@st.cache_data(show_spinner=False)
def cargar_csv(nombre: str):
    p = DATA / nombre
    return pd.read_csv(p) if p.exists() else None


@st.cache_data(show_spinner=False)
def cargar_texto(nombre: str):
    p = DATA / nombre
    return p.read_text(encoding="utf-8") if p.exists() else None


def exigir(obj, msg):
    if obj is None:
        st.error(msg); st.stop()



# =====================================================================================
#  Capa de diseño (solo presentación: no cambia ningún cálculo ni ninguna cifra)
# =====================================================================================
COLOR = {
    "azul": "#2348F2", "marino": "#0B1736", "estrella": "#F5B400", "riesgo": "#E5484D",
    "ok": "#12A594", "neutro": "#8A93A6", "texto_suave": "#5B6478", "rejilla": "#E4E8F1",
    "banda": "rgba(35, 72, 242, 0.14)",
}
COLORES_GRUPO = ["#2348F2", "#F5B400", "#E5484D", "#12A594", "#7B61FF", "#5B6478"]
# Cifras de la validación por fecha (salen del notebook; son las mismas de la Ficha del modelo)
FICHA = {"precision_10": 0.666, "regla_retraso": 0.621, "azar": 0.146, "umbral": 0.2708,
         "mejora_azar": 4.55, "mejora_regla": 1.07}   # mejoras tal como las imprime el notebook

COLOR_SENTIMIENTO = {"negative": "#E5484D", "neutral": "#8A93A6", "positive": "#12A594"}
NOMBRE_SENTIMIENTO = {"negative": "Negativo", "neutral": "Neutro", "positive": "Positivo"}


# Color con significado para los segmentos de vendedores: el de más retraso, rojo (riesgo).
COLOR_SEGMENTO = {
    "Entrega lenta / alto retraso": "#E5484D",
    "Grandes multicategoría": "#2348F2",
    "Bajo ticket / flete alto": "#F5B400",
    "Nicho premium confiable": "#12A594",
}


def color_grupos(grupos) -> dict:
    """Color fijo por grupo según su significado; los nombres desconocidos toman un color de la paleta."""
    libres = [c for c in COLORES_GRUPO if c not in COLOR_SEGMENTO.values()] + COLORES_GRUPO
    out, k = {}, 0
    for g in sorted(grupos):
        if g in COLOR_SEGMENTO:
            out[g] = COLOR_SEGMENTO[g]
        else:
            out[g] = libres[k % len(libres)]; k += 1
    return out


def fig_olist(fig):
    """Aplica la identidad de la app a una figura de Plotly."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", size=13, color=COLOR["marino"]),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=COLOR["rejilla"],
                        font=dict(family="Plus Jakarta Sans, sans-serif", color=COLOR["marino"])),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    fig.update_yaxes(gridcolor=COLOR["rejilla"], zeroline=False, title_font_color=COLOR["texto_suave"])
    fig.update_xaxes(showgrid=False, linecolor="#C9D0DE", title_font_color=COLOR["texto_suave"])
    return fig


def encabezado(titulo: str, bajada: str, etiqueta: str = ""):
    eti = f'<p class="ol-kicker">{etiqueta}</p>' if etiqueta else ""
    st.markdown(f'<div class="ol-head">{eti}<h1 class="ol-title">{titulo}</h1>'
                f'<p class="ol-lede">{bajada}</p></div>', unsafe_allow_html=True)


def chip(texto: str, color: str) -> str:
    return f'<span class="ol-chip"><span class="ol-dot" style="background:{color}"></span>{texto}</span>'


def banda_kpis(items: list[dict]):
    """Banda de indicadores: cada item tiene lab, val y opcionalmente unidad y nota (HTML)."""
    celdas = []
    for it in items:
        uni = f'<small>{it["unidad"]}</small>' if it.get("unidad") else ""
        nota = f'<div class="note">{it["nota"]}</div>' if it.get("nota") else ""
        celdas.append(f'<div class="ol-kpi"><p class="lab">{it["lab"]}</p>'
                      f'<div class="val">{it["val"]}{uni}</div>{nota}</div>')
    st.markdown(f'<div class="ol-kpis" style="--n:{len(items)}">{"".join(celdas)}</div>',
                unsafe_allow_html=True)


def estrellas(n: int) -> str:
    n = int(n)
    return ('<span class="ol-stars" aria-label="' + f"{n} de 5" + '">' +
            "".join(f'<i class="{"on" if k < n else ""}">★</i>' for k in range(5)) + "</span>")


def punto_elegido(evento):
    """Índice del punto elegido con un clic en un gráfico de Plotly (o None)."""
    try:
        pts = evento["selection"]["points"]
        return pts if pts else None
    except (KeyError, TypeError):
        return None


_JS_VISTO = """
<script>
(function () {
  if (window.__olVisto) return;
  window.__olVisto = true;
  var d = document;
  d.documentElement.classList.add('ol-js');   // sin esta clase, todo se anima al cargar
  var SEL = '.js-plotly-plot, .ol-anim';
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('ol-visto'); io.unobserve(e.target); }
    });
  }, { threshold: 0, rootMargin: '0px 0px -12% 0px' });
  function buscar() {
    d.querySelectorAll(SEL).forEach(function (el) {
      if (!el.__olObs) { el.__olObs = true; io.observe(el); }
    });
  }
  // Puntos que crecen desde su propio centro: Plotly los ubica con transform="translate(x,y)",
  // así que se toma ese (x,y) como origen del crecimiento. Retraso por grupo y por punto.
  var POP = [['.st-key-pca .scatterlayer .trace', 0.38, 0.0025, 0.5],
             ['.st-key-graf_cruce .scatterlayer .trace', 0, 0.07, 0.7],
             ['.st-key-graf_resumen .scatterlayer .trace', 0, 0.06, 0.8]];
  function crecer() {
    POP.forEach(function (cfg) {
      d.querySelectorAll(cfg[0]).forEach(function (tr, ti) {
        tr.querySelectorAll('.points path').forEach(function (pt, pi) {
          if (pt.__olPop) return;
          var t = pt.getAttribute('transform') || '', a = t.indexOf('translate(');
          if (a < 0) return;
          var m = t.slice(a + 10, t.indexOf(')', a)).split(/[ ,]+/);
          m = [null, m[0], m[1]];
          if (!m[1] || !m[2]) return;
          pt.__olPop = true;
          pt.style.transformBox = 'view-box';
          pt.style.transformOrigin = m[1] + 'px ' + m[2] + 'px';
          pt.style.setProperty('--d', (ti * cfg[1] + Math.min(pi * cfg[2], cfg[3])).toFixed(3) + 's');
          pt.classList.add('ol-pop');
        });
      });
    });
  }
  function todo() { buscar(); crecer(); }
  todo();
  new MutationObserver(todo).observe(d.body, { childList: true, subtree: true });
})();
</script>
"""


def animar_al_ver():
    """Las animaciones arrancan cuando cada gráfico o bloque aparece en pantalla al bajar."""
    try:
        st.html(_JS_VISTO, unsafe_allow_javascript=True)
    except TypeError:
        pass


def estilos():
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = """
<style>
[data-testid="stMainBlockContainer"] { max-width: 1280px; padding-top: 2.2rem; }
[data-testid="stSidebar"] [data-testid="stHtml"] { display: none; }

/* ---------- Encabezado ---------- */
.ol-head { margin: 0 0 1.1rem 0; }
.ol-kicker { display: inline-flex; align-items: center; gap: .4rem; margin: 0 0 .55rem 0;
  font-size: .78rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #2348F2; }
.ol-head h1.ol-title { font-weight: 800; font-size: clamp(2rem, 3.6vw, 2.75rem); line-height: 1.05;
  letter-spacing: -.02em; color: #0B1736; margin: 0 0 .5rem 0; padding: 0; }
.ol-lede { color: #5B6478; font-size: 1.02rem; line-height: 1.55; max-width: 48rem; margin: 0; }

/* ---------- Marca en la barra lateral ---------- */
.ol-brand { display: flex; align-items: center; gap: .6rem; margin: .2rem 0 .25rem 0; }
.ol-mark { display: grid; place-items: center; width: 2rem; height: 2rem; border-radius: .55rem;
  background: #2348F2; color: #F5B400; font-size: 1.15rem; line-height: 1; }
.ol-name { font-weight: 800; font-size: 1.5rem; letter-spacing: -.02em; color: #FFFFFF; }
.ol-brand-sub { color: #9AA6C2; font-size: .86rem; line-height: 1.45; margin: 0 0 .7rem 0; }

/* ---------- Tarjetas ---------- */
[data-testid="stMain"] [class*="st-key-card-"] { background: #FFFFFF; padding: 1.1rem 1.3rem;
  box-shadow: 0 1px 2px rgba(11, 23, 54, .04); }
[data-testid="stMain"] [data-testid="stMetric"] { background: #FFFFFF; }

/* ---------- Banda de indicadores ---------- */
[data-testid="stMarkdownContainer"]:has(> .ol-kpis),
[data-testid="stMarkdownContainer"]:has(> .ol-groups) { container-type: inline-size; }
.ol-kpis { display: grid; grid-template-columns: repeat(var(--n, 3), minmax(0, 1fr));
  background: #FFFFFF; border: 1px solid #DCE1EC; border-radius: .6rem; margin: .4rem 0 1rem 0; }
.ol-kpi { padding: 1rem 1.3rem; border-left: 1px solid #E4E8F1; min-width: 0; }
.ol-kpi:first-child { border-left: 0; }
.ol-kpi .lab { color: #5B6478; font-size: .88rem; margin: 0 0 .3rem 0; }
.ol-kpi .val { font-weight: 800; font-size: clamp(1.5rem, 3cqi, 2rem); line-height: 1.1; color: #0B1736;
  letter-spacing: -.02em; }
.ol-kpi .val small { font-size: 1rem; font-weight: 600; color: #5B6478; margin-left: .25rem; }
.ol-kpi .note { color: #5B6478; font-size: .84rem; margin-top: .35rem; }
@container (max-width: 760px) {
  .ol-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ol-kpi { border-left: 0; border-top: 1px solid #E4E8F1; } .ol-kpi:nth-child(-n+2) { border-top: 0; }
  .ol-kpi:nth-child(even) { border-left: 1px solid #E4E8F1; } }

.ol-pill { display: inline-block; border-radius: 999px; padding: .08rem .6rem; font-size: .8rem; font-weight: 600; }
.ol-pill.up { background: #E3F6F2; color: #0B7A6C; } .ol-pill.down { background: #FDE8E9; color: #B42329; }
.ol-pill.flat { background: #EEF1F7; color: #5B6478; } .ol-pill.blue { background: #E8EDFF; color: #1A35B8; }

.ol-chip { display: inline-flex; align-items: center; gap: .45rem; font-size: .88rem; font-weight: 600;
  color: #0B1736; background: #FFFFFF; border: 1px solid #DCE1EC; border-radius: 999px; padding: .2rem .75rem .2rem .55rem; }
.ol-dot { width: .6rem; height: .6rem; border-radius: 50%; display: inline-block; }

/* ---------- Estrellas ---------- */
.ol-stars { letter-spacing: .05em; white-space: nowrap; }
.ol-stars i { font-style: normal; color: #D5DBE7; } .ol-stars i.on { color: #F5B400; }

/* ---------- Resultado de riesgo ---------- */
.ol-result { border-radius: .7rem; padding: 1.3rem 1.4rem; color: #FFFFFF; background: #0B1736;
  border-left: .55rem solid var(--c, #12A594); }
.ol-result .k { color: #B9C3DB; font-size: .9rem; margin: 0 0 .2rem 0; }
.ol-result .big { font-weight: 800; font-size: clamp(2.6rem, 5vw, 3.6rem); line-height: 1; letter-spacing: -.03em; margin: 0; }
.ol-result .msg { display: inline-flex; align-items: center; gap: .5rem; margin: .8rem 0 0 0; font-weight: 700;
  font-size: 1rem; color: var(--c, #12A594); background: rgba(255,255,255,.07); border-radius: 999px; padding: .3rem .85rem; }
.ol-meter { position: relative; margin: 1.6rem 0 .3rem 0; height: 2.6rem; }
.ol-meter .rail { position: absolute; left: 0; right: 0; top: .9rem; height: .7rem; border-radius: 999px;
  background: linear-gradient(90deg, #12A594 0%, #F5B400 55%, #E5484D 100%); opacity: .25; }
.ol-meter .fill { position: absolute; left: 0; top: .9rem; height: .7rem; border-radius: 999px; background: var(--c);
  transform-origin: left center; }
.ol-meter .umb { position: absolute; top: .45rem; width: 2px; height: 1.6rem; background: #FFFFFF; transform: translateX(-1px); }
.ol-meter .umb span { position: absolute; top: -1.35rem; left: 50%; transform: translateX(-50%); white-space: nowrap;
  font-size: .75rem; color: #B9C3DB; }
.ol-meter .tick { position: absolute; top: 1.9rem; font-size: .72rem; color: #8F9BB8; }

/* ---------- Comentarios ---------- */
.ol-comments { display: grid; gap: .7rem; }
.ol-comment { background: #FFFFFF; border: 1px solid #DCE1EC; border-radius: .6rem; padding: .85rem 1.05rem;
  border-left: .3rem solid var(--c, #8A93A6); }
.ol-comment .top { display: flex; flex-wrap: wrap; align-items: center; gap: .55rem .9rem; margin-bottom: .4rem; font-size: .86rem; color: #5B6478; }
.ol-comment p { margin: 0; color: #0B1736; line-height: 1.5; }

/* ---------- Grupos (segmentación) ---------- */
.ol-groups { display: grid; grid-template-columns: repeat(var(--n, 4), minmax(0, 1fr)); gap: .9rem; margin: .4rem 0 1rem 0; }
.ol-group { background: #FFFFFF; border: 1px solid #DCE1EC; border-radius: .6rem; padding: 1rem 1.1rem; border-top: .3rem solid var(--c); }
.ol-group .gname { font-weight: 700; font-size: 1rem; margin: 0; }
.ol-group .gcount { font-weight: 800; font-size: 2.1rem; line-height: 1; margin: .5rem 0 .15rem 0; letter-spacing: -.02em; }
.ol-group .gcount small { font-size: .95rem; font-weight: 600; color: #5B6478; margin-left: .25rem; }
.ol-group dl { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .45rem .6rem; margin: .7rem 0 .6rem 0;
  padding-top: .65rem; border-top: 1px solid #EEF1F7; }
.ol-group dt { color: #5B6478; font-size: .76rem; } .ol-group dd { margin: .05rem 0 0 0; font-weight: 700; font-size: .95rem; }
.ol-group .accion { font-size: .88rem; line-height: 1.45; color: #2B3550; margin: 0; padding-top: .55rem; border-top: 1px solid #EEF1F7; }
@container (max-width: 860px) { .ol-groups { grid-template-columns: repeat(2, minmax(0, 1fr)); } }

/* ---------- Tablas animadas ---------- */
.ol-tbl { overflow: auto; max-height: 30rem; border: 1px solid #DCE1EC; border-radius: .6rem; background: #FFFFFF; }
.ol-tbl table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; margin: 0; font-size: .86rem; }
.ol-tbl th { white-space: normal; line-height: 1.2; vertical-align: bottom; }
.ol-tbl th { position: sticky; top: 0; z-index: 1; background: #F4F6FB; color: #5B6478; font-weight: 600;
  text-align: right; padding: .5rem .55rem; border-bottom: 1px solid #DCE1EC; }
.ol-tbl td { text-align: right; padding: .42rem .55rem; border-bottom: 1px solid #EEF1F7; white-space: nowrap; border-left: 0; border-right: 0; }
.ol-tbl th.l, .ol-tbl td.l { text-align: left; }
.ol-tbl tr:last-child td { border-bottom: 0; }
.ol-tbl tbody tr:hover td { background: #F7F9FE; }
.ol-barcell { display: flex; align-items: center; gap: .5rem; min-width: 7rem; }
.ol-track { flex: 1; height: .42rem; background: #EEF1F7; border-radius: 999px; overflow: hidden; }
.ol-fill { display: block; height: 100%; background: #2348F2; border-radius: 999px; transform-origin: left center; }
.ol-num { min-width: 2.6rem; text-align: right; }

/* ============ Animaciones (arrancan al aparecer en pantalla) ============ */
@keyframes ol-barrido { from { clip-path: inset(-10% 100% -10% 0); } to { clip-path: inset(-10% -2% -10% 0); } }
@keyframes ol-aparecer { from { opacity: 0; } to { opacity: 1; } }
@keyframes ol-subir { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@keyframes ol-crecer-x { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@keyframes ol-crecer-y { from { transform: scaleY(0); } to { transform: scaleY(1); } }
@keyframes ol-materializar { from { opacity: 0; filter: blur(6px); } to { opacity: 1; filter: blur(0); } }

/* Gráficos: líneas con barrido, barras que crecen, puntos que aparecen */
.js-plotly-plot .scatterlayer .trace { animation: ol-barrido 1.4s cubic-bezier(.4, 0, .2, 1) both; }
.js-plotly-plot .scatterlayer .points path { animation: ol-aparecer .45s ease 1.1s backwards; }
.js-plotly-plot .barlayer .point path { transform-box: fill-box; transform-origin: 50% 100%;
  animation: ol-crecer-y .7s cubic-bezier(.2, .7, .2, 1) both; }
.js-plotly-plot .barlayer .bartext { animation: ol-aparecer .4s ease .8s both; }
.js-plotly-plot .heatmaplayer, .js-plotly-plot .imagelayer { animation: ol-materializar .9s ease .1s both; }
.js-plotly-plot .layer-above .annotation { animation: ol-aparecer .5s ease .7s both; }

/* Bloques HTML con animación */
.ol-anim .ol-kpi, .ol-anim .ol-group, .ol-anim .ol-comment { animation: ol-subir .55s cubic-bezier(.2, .7, .2, 1) both; }
.ol-anim > :nth-child(2), .ol-anim .ol-kpi:nth-child(2) { animation-delay: .08s; }
.ol-anim > :nth-child(3), .ol-anim .ol-kpi:nth-child(3) { animation-delay: .16s; }
.ol-anim > :nth-child(4), .ol-anim .ol-kpi:nth-child(4) { animation-delay: .24s; }
.ol-anim > :nth-child(5) { animation-delay: .32s; } .ol-anim > :nth-child(6) { animation-delay: .40s; }
.ol-anim > :nth-child(n+7) { animation-delay: .46s; }
.ol-tbl.ol-anim { animation: ol-barrido 1s cubic-bezier(.4, 0, .2, 1) both; }
.ol-tbl.ol-anim .ol-fill { animation: ol-crecer-x .8s cubic-bezier(.2, .7, .2, 1) both;
  animation-delay: calc(.3s + var(--i, 0) * .035s); }
.ol-result.ol-anim { animation: ol-subir .5s ease both; }
.ol-result.ol-anim .fill { animation: ol-crecer-x 1.1s cubic-bezier(.2, .7, .2, 1) .25s both; }
.ol-result.ol-anim .big { animation: ol-aparecer .6s ease .15s both; }




/* Ficha: el documento dentro de una tarjeta, con jerarquía clara */
.st-key-card-ficha { padding: 1.6rem 2rem !important; }
.st-key-card-ficha h1 { font-size: 1.6rem !important; font-weight: 800; letter-spacing: -.02em; }
.st-key-card-ficha h2 { font-size: 1.2rem !important; font-weight: 800; color: #2348F2; margin-top: 1.4rem !important;
  padding-top: 1rem; border-top: 1px solid #EEF1F7; }
.st-key-card-ficha li { margin-bottom: .25rem; }
.st-key-card-ficha strong { color: #0B1736; }


/* Tabla de vendedores en pantallas angostas: oculta Estado, Flete relativo y Categorías */
[data-testid="stMarkdownContainer"]:has(> .ol-tbl-vend) { container-type: inline-size; }
@container (max-width: 900px) {
  .ol-tbl-vend th:nth-child(2), .ol-tbl-vend td:nth-child(2), .ol-tbl-vend th:nth-child(7), .ol-tbl-vend td:nth-child(7),
  .ol-tbl-vend th:nth-child(10), .ol-tbl-vend td:nth-child(10) { display: none; }
  .ol-tbl-vend .ol-barcell { min-width: 5.5rem; }
  .ol-tbl-vend td:nth-child(3) { white-space: normal; min-width: 7.5rem; }
}


/* Riesgo: la probabilidad cuenta de 0 al valor final */
@property --num { syntax: "<integer>"; initial-value: 0; inherits: false; }
@keyframes ol-contar { from { --num: 0; } to { --num: var(--to); } }
@supports (animation-timeline: auto) or (font-palette: normal) {
  .ol-result .ol-count span { display: none; }
  .ol-result .ol-count::after { content: counter(n) "%"; counter-reset: n var(--num);
    animation: ol-contar 1.1s cubic-bezier(.2, .7, .2, 1) .15s both; }
}
.ol-result .cmp { margin: .75rem 0 0 0; font-size: .92rem; color: #D7DDEC; }
.ol-result .cmp b { color: #FFFFFF; }

/* El conteo de la probabilidad también espera a que el bloque se vea */
html.ol-js .ol-anim:not(.ol-visto) .ol-count::after { animation-play-state: paused !important; }


/* Puntos que crecen desde su centro (mapa de vendedores, tabla cruzada, resumen) */
@keyframes ol-pop { 0% { scale: 0; } 70% { scale: 1.12; } 100% { scale: 1; } }
.st-key-pca .scatterlayer .trace, .st-key-graf_cruce .scatterlayer .trace,
.st-key-graf_resumen .scatterlayer .trace { animation: none; }
.st-key-pca .scatterlayer .points path, .st-key-graf_cruce .scatterlayer .points path,
.st-key-graf_resumen .scatterlayer .points path { animation: none; }
.js-plotly-plot .scatterlayer .points path.ol-pop { animation: ol-pop .55s cubic-bezier(.2, .8, .3, 1) both;
  animation-delay: var(--d, 0s); }
.st-key-graf_cruce .scatterlayer .text text { animation: ol-aparecer .4s ease .75s both; }


/* Fichas de segmento: se elevan al pasar el mouse; la elegida se resalta y las demás se atenúan */
.ol-group { transition: translate .2s ease, box-shadow .2s ease, filter .25s ease; }
.ol-group:hover { translate: 0 -3px; box-shadow: 0 8px 20px rgba(11, 23, 54, .08); }
.ol-group.sel { box-shadow: 0 0 0 2px var(--c), 0 10px 24px rgba(11, 23, 54, .10); }
.ol-group.dim { filter: grayscale(.7) opacity(.5); }
.ol-group dd + .ol-pill { margin-top: .2rem; font-size: .72rem; }
/* Barras horizontales del perfil: crecen desde la izquierda */
.st-key-graf_perfil .js-plotly-plot .barlayer .point path { transform-origin: 0% 50%; animation-name: ol-crecer-x; }
.st-key-graf_perfil .js-plotly-plot .barlayer .point:nth-child(2) path { animation-delay: .1s; }
.st-key-graf_perfil .js-plotly-plot .barlayer .point:nth-child(3) path { animation-delay: .2s; }
.st-key-graf_perfil .js-plotly-plot .barlayer .point:nth-child(4) path { animation-delay: .3s; }


/* Resumen: tarjetas de las preguntas del proyecto */
.ol-q p.ol-q-num { display: flex; align-items: center; gap: .55rem; color: #5B6478; font-weight: 600; margin: 0 0 .55rem 0; }
.ol-q p.ol-q-num span { display: inline-grid; place-items: center; width: 1.6rem; height: 1.6rem; border-radius: .45rem;
  background: #2348F2; color: #FFFFFF; font-weight: 800; font-size: .85rem; }
.ol-q p.ol-q-big { font-weight: 800; font-size: clamp(1.7rem, 3vw, 2.3rem); line-height: 1.05; letter-spacing: -.02em;
  color: #0B1736; margin: 0 0 .45rem 0; }
.ol-q p.ol-q-txt { color: #2B3550; line-height: 1.55; margin: 0 0 .3rem 0; }
[class*="st-key-card-q"] { transition: translate .2s ease, box-shadow .2s ease; }
[class*="st-key-card-q"]:hover { translate: 0 -3px; box-shadow: 0 10px 24px rgba(11, 23, 54, .08) !important; }
[class*="st-key-card-q"] [data-testid="stPageLink"] p { font-weight: 700; color: #2348F2; }


/* Resumen: el círculo bajo el mouse se resalta */
.st-key-graf_resumen .js-plotly-plot .scatterlayer .points path { cursor: pointer; transition: stroke-width .15s ease; }
.st-key-graf_resumen .js-plotly-plot .scatterlayer .points path:hover { stroke: #0B1736 !important; stroke-width: 3px !important; }
.st-key-graf_resumen .js-plotly-plot .hoverlayer .hovertext path { filter: drop-shadow(0 6px 14px rgba(11, 23, 54, .25)); }


/* Ficha como acordeón: cada pregunta se despliega con una animación suave */
.st-key-card-ficha p.ol-ficha-t { font-weight: 800; font-size: 1.55rem; letter-spacing: -.02em; color: #0B1736;
  margin: 0 0 .4rem 0; line-height: 1.2; }
.st-key-card-ficha [data-testid="stExpander"] details { border: 1px solid #E4E8F1; border-radius: .6rem;
  background: #FFFFFF; transition: border-color .2s ease, box-shadow .2s ease; }
.st-key-card-ficha [data-testid="stExpander"] details:hover { border-color: #B7C3F7; }
.st-key-card-ficha [data-testid="stExpander"] details[open] { border-color: #2348F2;
  box-shadow: 0 6px 18px rgba(35, 72, 242, .08); }
.st-key-card-ficha [data-testid="stExpander"] summary p { font-weight: 700; font-size: 1.05rem; color: #0B1736; }
.st-key-card-ficha [data-testid="stExpander"] details[open] summary p { color: #2348F2; }
@keyframes ol-desplegar { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: none; } }
.st-key-card-ficha [data-testid="stExpander"] details[open] [data-testid="stExpanderDetails"] {
  animation: ol-desplegar .35s ease both; }

/* Pausa hasta que el elemento se ve (el script agrega .ol-visto) */
html.ol-js :is(.js-plotly-plot, .ol-anim):not(.ol-visto),
html.ol-js :is(.js-plotly-plot, .ol-anim):not(.ol-visto) * { animation-play-state: paused !important; }

@media (prefers-reduced-motion: reduce) { .js-plotly-plot *, .ol-anim, .ol-anim * { animation: none !important; } }
</style>
"""
