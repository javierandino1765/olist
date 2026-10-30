# Ficha del modelo · Riesgo de mala reseña (Olist)

Documento corto para quien decide si usar el modelo, sin necesidad de saber de machine learning.

## 1. Para qué sirve (y para qué no)

Estima, **en el momento en que un pedido se entrega**, la probabilidad de que el cliente deje una
**mala reseña** (1 o 2 estrellas). Sirve para **priorizar a qué clientes llamar primero**: atención al
cliente solo alcanza para ~1 de cada 10 pedidos, y el modelo ordena ese 10% por riesgo.

**No sirve** para castigar vendedores, decidir quién trabaja, ni para predecir con días de anticipación:
solo funciona una vez que el pedido ya fue entregado.

## 2. Datos

- Fuente: datos públicos de Olist (comercio electrónico de Brasil), esquema `final` del curso.
- Periodo de entrenamiento: pedidos comprados entre **septiembre 2016 y mayo 2018**.
- Tamaño: **77,304 pedidos** entregados y con reseña (una fila por pedido).
- Se excluyó: pedidos no entregados o sin reseña, y los comprados **desde el 1 de junio de 2018**
  (los reserva el docente para evaluar; así el modelo se entrena con el pasado y se prueba con el futuro).

## 3. Qué tan bien funciona

Evaluado **por fecha** (se entrena con los pedidos más antiguos y se valida con los más recientes):

- **Precisión en el 10% de mayor riesgo: 0.663.** De cada 10 clientes que el modelo marca como más
  riesgosos, cerca de **7 (6.6) iban de verdad a dejar mala reseña**.
- Contra el **azar** (llamar al 10% al azar), que acierta **0.146**: **×4.5 mejor** (de cada 10 llamadas al azar, solo 1 o 2 acertarían).
- Contra la **regla del retraso** (llamar a los más atrasados), que acierta **0.621**: le gana, pero
  **por poco** (×1.07). Es honesto decirlo: el retraso ya explica gran parte de las malas reseñas; el
  modelo aporta al sumarle la geografía, la categoría y el tamaño del pedido.
- Las tres variables que más pesan: **entregado tarde**, **días de retraso** y **número de artículos**.

## 4. Límites conocidos

- Depende mucho del **retraso**: en un periodo con muy pocos retrasos perdería poder y se parecería más
  al azar.
- Entrenado con 2016–2018: no conoce cambios de temporada, campañas ni eventos nuevos.
- No usa el **texto** de la reseña (eso ocurre después de la entrega); el texto se analiza aparte (Parte 4).
- La precisión que calcule el docente con junio–agosto 2018 **será distinta** a 0.663: el periodo oculto
  es otro.

## 5. A quién afecta un error

- **Falso positivo** (marca riesgo y el cliente estaba contento): se gasta una llamada de más; costo bajo.
- **Falso negativo** (no lo marca y sí deja mala reseña): se pierde la oportunidad de resolver a tiempo.
- **Mal uso:** si alguien usara esto para **penalizar vendedores** por "riesgo", castigaría a vendedores
  con problemas de logística que no siempre controlan (transportistas, distancia). El modelo es para
  **priorizar llamadas**, no para sancionar.

## 6. Recomendación

- Úsenlo como **lista de llamadas**: cada día, contactar el 10% de mayor riesgo de los pedidos recién
  entregados.
- **Supervisión humana:** la persona de atención decide; el modelo solo ordena la fila.
- **Revisión:** medir la precisión real cada mes y re-entrenar si cae o si cambian los patrones de entrega.
