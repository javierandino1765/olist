# Proyecto Final · Olist: del pedido a la reseña

**Equipo:** Alexia Guevara · Oscar Villalta · Javier Andino · AIMLF1

Modelo de riesgo de mala reseña + segmentación de vendedores + sentimiento de comentarios, con una API
en Render y una app de Streamlit que la consume.

## Links

- App (Streamlit): ver `app_url.txt`
- API (Render), su `/docs` debe abrir: ver `api_url.txt`
- Repositorio: `https://github.com/<completar>`

## Estructura

```
Proyecto_Final.ipynb        # notebook ejecutado (Partes 1–6 + Extra)
preparacion.py              # crear_variables (sin fuga); se importa en el notebook y la API
modelo_riesgo.joblib        # pipeline final (crear_variables + preprocesamiento + XGBoost)
sentimiento_muestra.csv     # salida de la Parte 4
ficha_modelo.md             # ficha del modelo
api_url.txt / app_url.txt   # URLs publicadas
api/                        # main.py, requirements.txt, preparacion.py, modelo_riesgo.joblib, umbral.json
app/                        # streamlit_app.py, comun.py, paginas/, data/, .streamlit/config.toml
```

## Correr en local

API:
```bash
cd api && pip install -r requirements.txt && uvicorn main:app --reload
# http://localhost:8000/docs  ·  POST /riesgo
```
App:
```bash
cd app && pip install -r requirements.txt && streamlit run streamlit_app.py
```

## Desplegar

- **API en Render:** New → Web Service → Root Directory `api` · Build `pip install -r requirements.txt`
  · Start `uvicorn main:app --host 0.0.0.0 --port $PORT` · Free.
  **Importante:** `api/requirements.txt` fija las versiones del Colab que entrenó el `.joblib`
  (scikit-learn 1.6.1, xgboost 3.4.1, pandas 2.2.3, numpy 2.1.3); si no coinciden, el modelo no carga.
- **App en Streamlit Community Cloud:** Main file `app/streamlit_app.py` · Secrets:
  `API_URL = "https://<tu-api>.onrender.com"`.

## Contrato de la API

| Método y ruta | Recibe | Devuelve |
|---|---|---|
| `GET /` | nada | estado y umbral |
| `POST /riesgo` | las 17 columnas del contrato (sin `mala_resena`); fechas como texto, nulos opcionales | `{"probabilidad", "riesgo_alto", "umbral"}`; 422 si un campo obligatorio falta o un precio es negativo |
