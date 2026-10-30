"""API de riesgo de mala reseña (Olist).

Carga el modelo en formato PORTABLE (XGBoost nativo .json + preprocesador de scikit-learn),
que funciona igual en Windows, Linux y Render. No recalcula nada: transforma el pedido y predice.

Local:  python -m uvicorn main:app --reload    |    Docs: http://localhost:8000/docs
"""
import json, os
from typing import Optional

# Render (plan gratuito) ve todas las CPU del host: sin esto OpenMP/XGBoost lanza decenas de hilos,
# se queda sin memoria y el proceso muere a mitad del pedido (502). Debe ir antes de importar xgboost.
os.environ.setdefault("OMP_NUM_THREADS", "1")

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from xgboost import XGBClassifier

import preparacion  # necesario para reconstruir el FunctionTransformer del preprocesador

AQUI = os.path.dirname(os.path.abspath(__file__))
preprocesador = joblib.load(os.path.join(AQUI, "preprocesador.joblib"))   # crear_variables + ColumnTransformer
modelo = XGBClassifier()
modelo.load_model(os.path.join(AQUI, "modelo_xgb.json"))                  # formato nativo portable
modelo.set_params(n_jobs=1)                                               # un solo hilo al predecir
UMBRAL = json.load(open(os.path.join(AQUI, "umbral.json")))["umbral"]

app = FastAPI(title="Riesgo de mala reseña · Olist", version="1.0")


class Pedido(BaseModel):
    order_id: str
    order_purchase_timestamp: str
    order_approved_at: Optional[str] = None
    order_delivered_carrier_date: Optional[str] = None
    order_delivered_customer_date: str
    order_estimated_delivery_date: str
    estado_cliente: str
    n_items: int = Field(ge=1)
    n_vendedores: int = Field(ge=1)
    precio_total: float = Field(ge=0)
    flete_total: float = Field(ge=0)
    peso_total_g: Optional[float] = Field(default=None, ge=0)
    fotos_promedio: Optional[float] = Field(default=None, ge=0)
    categoria: Optional[str] = None
    estado_vendedor: str
    tipo_pago: str
    cuotas_max: int = Field(ge=0)


@app.get("/")
def estado():
    return {"estado": "ok", "mensaje": "API de riesgo de mala reseña (Olist)", "umbral": round(UMBRAL, 4)}


@app.post("/riesgo")
def riesgo(pedido: Pedido):
    fila = pd.DataFrame([pedido.model_dump()])
    try:
        X = preprocesador.transform(fila)
        prob = float(modelo.predict_proba(X)[:, 1][0])
    except Exception as e:                       # devolver la causa en JSON en vez de un 500 en texto plano
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    return {"probabilidad": round(prob, 4),
            "riesgo_alto": bool(prob >= UMBRAL),
            "umbral": round(UMBRAL, 4)}
