# Explicación del Proyecto Final · Olist

Documento para entender y **defender** el proyecto de punta a punta. Cada parte explica el *qué* y, sobre
todo, el *por qué*. Las cifras son las de la ejecución real del notebook.

---

## Visión general y arquitectura

Olist conecta tiendas pequeñas con grandes marketplaces. Una reseña de 1–2 estrellas daña la reputación
del vendedor y de la plataforma. Atención al cliente puede llamar a ~1 de cada 10 pedidos **antes** de que
el cliente escriba. El proyecto construye la herramienta que decide **a quién llamar primero**, más
análisis de los comentarios y de los vendedores.

La arquitectura separa el **cerebro** del **rostro**: el modelo vive detrás de una **API (FastAPI en
Render)** y la pantalla es una **app (Streamlit)** que la consulta. El modelo nunca sale del servidor, y la
API la puede usar a la vez una app web, una móvil o un chatbot.

Flujo: la **base del curso (Postgres/`final`)** → el **notebook** hace SQL, modelos y métricas y genera los
artefactos (`modelo_riesgo.joblib`, `preparacion.py`, CSVs) → la **API** carga el `.joblib` y responde
`/riesgo` → la **app** le pregunta a la API y lee los CSVs.

---

## Parte 1 · Datos (SQL + contrato)

Una sola consulta que une 7 tablas y produce **una fila por pedido entregado y con reseña**, con las 18
columnas del **contrato** en orden exacto. La verificación da `True` y **77,303 pedidos**.

Decisiones clave (porque un pedido puede tener varios artículos, pagos y reseñas):

- **Varios artículos:** se agregan por pedido (`items`): `n_items`, `n_vendedores` (distintos), sumas de
  precio y flete; peso y fotos en `peso_fotos`. La **categoría** y el **estado del vendedor** se toman del
  **artículo 1** (`order_item_id = 1`).
- **Varios pagos:** `tipo_pago` = el del pago de **mayor monto** (`ARRAY_AGG ... ORDER BY payment_value
  DESC`), `cuotas_max` = máximo de cuotas.
- **Varias reseñas:** se usa la **más reciente** (`DISTINCT ON (order_id) ... ORDER BY
  review_answer_timestamp DESC`). `mala_resena = 1` si es de 1 o 2 estrellas.
- **Filtro:** solo `delivered` con fecha de entrega conocida.

El *contrato* es un acuerdo fijo: el modelo, la API y el calificador usan las mismas 18 columnas. Si el
modelo pidiera una columna fuera del contrato, no correría con los pedidos ocultos.

---

## Parte 2 · Modelo de riesgo (lo central, 25 pts)

**Qué se predice y cuándo:** la probabilidad de `mala_resena = 1` **en el momento de la entrega**. En ese
momento se conocen las fechas del pedido (incluida la entrega real), los artículos, los pagos y la
geografía. **No se conoce nada de la reseña** → usar su texto, largo o fechas sería *fuga de datos*.

**`preparacion.py` y `crear_variables`:** todas las variables se calculan a partir de las 17 columnas del
contrato, sin fuga. Las principales: días de entrega, **retraso vs. fecha estimada**, `entregado_tarde`,
días de aprobación/despacho/tránsito, flete relativo, precio por artículo, calendario de la compra, y las
categóricas (tipo de pago, estado del cliente/vendedor, categoría). Esta función se importa **tanto en el
notebook como en la API**, por eso va en su propio archivo.

**El pipeline** empieza con `FunctionTransformer(crear_variables)`, luego un `ColumnTransformer`
(imputación + one-hot para categóricas) y el clasificador. Así el `.joblib` **recibe las columnas crudas
del contrato** y hace todo adentro: por eso la prueba `cargado.predict_proba(pedidos[CONTRATO[:-1]])`
funciona, y la API solo pasa el pedido tal cual.

**Validación por fecha** (nunca al azar): se entrena con los pedidos más antiguos y se valida con los más
recientes (corte 2018-03-01). En series temporales, partir al azar "ve el futuro" y da un error
falsamente bueno.

**Métrica = precisión en el 10% de mayor riesgo:** de los pedidos que el modelo marca como más riesgosos,
qué proporción tuvo de verdad mala reseña. Es lo que le importa al negocio (acertar en los pocos clientes
a los que se puede llamar), no la exactitud global (un modelo que dice "nunca" acierta 85% y es inútil).

**Resultados reales:**

| | Precisión@10% (validación) |
|---|---|
| **XGBoost (elegido)** | **0.666** |
| Regresión logística | 0.612 |
| Regla del retraso | 0.621 |
| Azar (tasa base) | 0.146 |

El XGBoost le gana a la **regla del retraso** (×1.07) y al **azar** (×4.55). Variables más importantes:
`entregado_tarde` (0.46), `retraso_vs_estimada`, `n_items`. Le gana a la regla del retraso **por poco**, y
eso es honesto: el retraso ya explica gran parte de las malas reseñas; el modelo aporta al sumar geografía,
categoría y tamaño del pedido. El modelo final se entrena con **todos** los pedidos y se guarda; el
**umbral del 10%** (0.271) es el que la API usa para `riesgo_alto`.

**Respuestas a las preguntas:** (1) mejora ×1.07 sobre el retraso y ×4.5 sobre el azar; (2) las tres
variables de entrega/tamaño, con sentido de negocio; (3) en un periodo con pocos retrasos perdería su
señal principal y se parecería más al azar.

---

## Parte 3B · Segmentación de vendedores (10 pts)

Elegimos 3B porque es autocontenida (no depende de datos ocultos) y da una lectura comercial. Con SQL se
arma **una fila por vendedor con ≥10 pedidos entregados** (1,005 vendedores): pedidos, ventas, flete
relativo, ticket medio, tasa de retraso, días de entrega, categorías.

Preparación: `log1p` a las variables con cola larga (pedidos, ventas, ticket, categorías) y `StandardScaler`
(K-Means usa distancias). Se eligió **k = 4** con el coeficiente de silueta (máximo en k=4, 0.199) **y** el
criterio de negocio. PCA a 2 componentes (60% de la varianza) para dibujarlos. Los grupos se nombran
**por su perfil, no por su número** (K-Means numera al azar).

| Segmento | Rasgo | Acción |
|---|---|---|
| Grandes multicategoría | mucho volumen y catálogo | cuentas clave, logística por volumen |
| Entrega lenta / alto retraso | 18% de retraso, entrega lenta | plan de SLA; es el que más malas reseñas genera |
| Bajo ticket / flete alto | ventas bajas, flete 35% del precio | renegociar/subsidiar flete |
| Nicho premium confiable | ticket alto, poco retraso | fidelizar, usar de benchmark |

---

## Parte 4 · Deep learning: sentimiento (15 pts)

Un modelo **preentrenado** de Hugging Face (`cardiffnlp/twitter-xlm-roberta-base-sentiment`, entiende
portugués) clasifica una muestra de 1,200 comentarios como positive/neutral/negative. Se usa la GPU de
Colab. **Importante:** los comentarios son **tema de análisis**, no variable del modelo de riesgo (ahí
siguen prohibidos: son posteriores a la entrega).

Se comparan con las estrellas (1–2 negativo, 3 neutro, 4–5 positivo): **coincidencia 70.7%**. La mayor
confusión está en los **neutros (3★)** y en positivos que el modelo marca como neutros. Los desacuerdos se
clasifican: textos cortos o con ironía → error del modelo; 5★ con queja en el texto → la nota no concuerda
con lo escrito. Lo que el texto agrega sobre la estrella: el **motivo** (retraso, producto dañado,
diferencia con la foto), que sí es accionable.

---

## Extra · Red neuronal vs XGBoost (+5)

Red densa de Keras con la **misma división por fecha y mismas variables**, con *early stopping*. Resultado:
red neuronal **0.650** vs XGBoost **0.666**. En datos de tabla con pocas variables y clases
desbalanceadas, el gradient boosting iguala o gana y entrena mucho más rápido; la red necesita más datos y
ajuste para brillar.

---

## Parte 5 · Despliegue (15 pts)

**API (FastAPI en Render):** `GET /` (estado) y `POST /riesgo`. Recibe las 17 columnas del contrato
validadas con **Pydantic** (precio negativo o campo obligatorio faltante → **422**). Carga el `.joblib` y
el umbral una sola vez al arrancar; `riesgo_alto` es `True` si la probabilidad alcanza el umbral del 10%.
El `requirements.txt` fija **las versiones del Colab** que entrenó el modelo (si no coinciden, el `.joblib`
no carga — lo comprobamos: con otra versión de scikit-learn falla al abrir).

**App (Streamlit):** multipágina (`st.navigation` + `st.Page`) con la URL de la API en `st.secrets`:
- **Riesgo de un pedido:** elige/edita un pedido, llama a `POST /riesgo`, muestra probabilidad y si es
  riesgo alto; un deslizador de "retraso extra" muestra cómo sube el riesgo.
- **Comentarios:** la tabla cruzada estrellas × sentimiento y los desacuerdos (Parte 4).
- **Segmentación:** mapa PCA, perfiles y acción por segmento (Parte 3B).
- **Ficha del modelo:** la ficha y las métricas clave.

Si la API no responde (Render duerme el plan gratuito), la app muestra un **mensaje claro**, no un error.

---

## Parte 6 · Ficha del modelo (en `ficha_modelo.md`)

Documento corto para quien decide: para qué sirve y para qué no, datos y periodo, qué tan bien funciona
(vs azar y vs regla), límites, a quién afecta un error, y recomendación de uso con supervisión humana.

---

## Guía de defensa (preguntas probables)

**P. ¿Por qué no es fuga usar `order_delivered_customer_date`?** Porque el modelo predice *en el momento de
la entrega*: esa fecha ya ocurrió. Lo que no existe aún es la reseña.

**P. ¿Por qué precisión en el 10% y no exactitud?** Porque solo 1 de cada ~7 pedidos tiene mala reseña: un
modelo que diga "nunca" acierta 85% y no sirve. Importa acertar en los pocos clientes a los que se puede
llamar.

**P. ¿Por qué validación por fecha?** Para no "ver el futuro". Al azar, el modelo entrenaría con días que
rodean al de prueba y el error se vería falsamente bueno.

**P. ¿Por qué el modelo le gana por poco a la regla del retraso?** Porque el retraso ya explica casi todo.
Es información honesta para la ficha; el valor extra del modelo está en combinar retraso con geografía,
categoría y tamaño.

**P. ¿Por qué `preparacion.py` separado?** Para que el notebook y la API usen exactamente las mismas
variables. El `.joblib` guarda una referencia a `crear_variables`, por eso el archivo debe estar junto a la
API.

**P. ¿Por qué el `.joblib` no cargó una vez?** Por versiones distintas de scikit-learn. Por eso el
`requirements.txt` de la API fija las versiones del Colab.

**P. ¿Por qué k = 4 en la segmentación?** Es el máximo de la silueta y da cuatro grupos accionables; la
métrica y el negocio coinciden.

**P. ¿Qué pasa con la precisión en junio–agosto (datos del docente)?** Será distinta a 0.666: el periodo
oculto es otro. Lo importante es que la validación honesta por fecha ya supera claramente al azar y a la
regla del retraso.
