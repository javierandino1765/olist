"""Preparación de variables para el modelo de riesgo de mala reseña (Olist).

Se importa desde el notebook y desde la API. `crear_variables` recibe un DataFrame
con las 17 columnas del contrato (sin `mala_resena`) y devuelve las variables del
modelo. No hay fuga de información: solo usa lo que se conoce EN EL MOMENTO DE LA
ENTREGA (fechas del pedido, artículos, pagos y geografía); nada de la reseña.
"""
import numpy as np
import pandas as pd

FECHAS = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
          "order_delivered_customer_date", "order_estimated_delivery_date"]

NUMERICAS = ["n_items", "n_vendedores", "precio_total", "flete_total", "peso_total_g",
             "fotos_promedio", "cuotas_max", "flete_relativo", "precio_por_item",
             "dias_entrega", "retraso_vs_estimada", "dias_estimados", "dias_aprobacion",
             "dias_a_carrier", "dias_carrier_a_cliente", "entregado_tarde",
             "compra_hora", "compra_dia_semana", "compra_mes"]

CATEGORICAS = ["tipo_pago", "estado_cliente", "estado_vendedor", "categoria"]


def crear_variables(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    for c in FECHAS:
        if c in d.columns:
            d[c] = pd.to_datetime(d[c], errors="coerce")

    def dias(a, b):
        return (d[a] - d[b]).dt.total_seconds() / 86400.0

    out = pd.DataFrame(index=d.index)
    # Numéricas directas del contrato
    for c in ["n_items", "n_vendedores", "precio_total", "flete_total",
              "peso_total_g", "fotos_promedio", "cuotas_max"]:
        out[c] = pd.to_numeric(d[c], errors="coerce")
    # Derivadas de montos
    out["flete_relativo"] = out["flete_total"] / out["precio_total"].replace(0, np.nan)
    out["precio_por_item"] = out["precio_total"] / out["n_items"].replace(0, np.nan)
    # Derivadas de fechas (todas conocidas al entregar)
    out["dias_entrega"]          = dias("order_delivered_customer_date", "order_purchase_timestamp")
    out["retraso_vs_estimada"]   = dias("order_delivered_customer_date", "order_estimated_delivery_date")
    out["dias_estimados"]        = dias("order_estimated_delivery_date", "order_purchase_timestamp")
    out["dias_aprobacion"]       = dias("order_approved_at", "order_purchase_timestamp")
    out["dias_a_carrier"]        = dias("order_delivered_carrier_date", "order_purchase_timestamp")
    out["dias_carrier_a_cliente"] = dias("order_delivered_customer_date", "order_delivered_carrier_date")
    out["entregado_tarde"]       = (out["retraso_vs_estimada"] > 0).astype(int)
    # Calendario de la compra
    out["compra_hora"]        = d["order_purchase_timestamp"].dt.hour
    out["compra_dia_semana"]  = d["order_purchase_timestamp"].dt.dayofweek
    out["compra_mes"]         = d["order_purchase_timestamp"].dt.month
    # Categóricas (nulos -> "desconocido")
    for c in CATEGORICAS:
        out[c] = d[c].where(d[c].notna(), "desconocido").astype(str)

    return out[NUMERICAS + CATEGORICAS]
