# 01_scope_protocol

## Objetivo
Cuantificar y comparar el horizonte de predictibilidad operativa H* de PM10 y PM2.5 en redes urbanas de Elche y Florencia mediante un protocolo rolling-origin sin fuga de datos y con baselines de persistencia explícitas.

## Alcance
- Ciudades: Elche (España) y Florencia (Italia).
- Estaciones: solo estaciones oficiales (red autonómica/regional/EEA) con histórico suficiente y medidas de PM10 y PM2.5.
- Contaminantes: PM10 y PM2.5.
- Frecuencia temporal: diaria.
- Horizonte máximo de predicción: Hmax = 7 días.

## Modelos permitidos
- Persistencia simple.
- Persistencia estacional (si aplica).
- ARIMA/SARIMA.
- Un único modelo de boosting (XGBoost o LightGBM) con lags tabulares y sin tuning agresivo.

## Protocolo de validación y preprocesado
- Validación temporal rolling-origin.
- Preprocesado estrictamente train-only en cada origen.
- Prohibido cualquier uso de información futura (sin data leakage).
- Misma estrategia de validación y mismas baselines para todas las estaciones y contaminantes.

## Métricas y horizontes
- Calcular métricas por horizonte h (h = 1..7).
- Calcular Skill(h) frente a persistencia.
- Derivar y reportar:
  - H
  - H*(relax)
  - H*(strict)

## Parametrización y reproducibilidad
- Toda la lógica de datos, modelado y evaluación debe parametrizarse por:
  - ciudad
  - estación
  - contaminante
- Estructura de carpetas:
  - `data_raw/`: datos originales.
  - `data_processed/`: datos listos para modelado.
  - `code/`: scripts de descarga, limpieza, validación, modelado, evaluación y figuras/tablas.

## Restricciones del diseño experimental
- No introducir modelos adicionales fuera de los tipos definidos.
- No alterar el protocolo rolling-origin ni las baselines de referencia sin solicitud explícita.
