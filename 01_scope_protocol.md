# 01_scope_protocol.md — Experimental design (LOCKED)

## 1. Objetivo del estudio

Cuantificar y comparar el horizonte de predictabilidad operativa H* de PM10 y PM2.5 en redes urbanas de Elche y Florencia, bajo un protocolo rolling-origin sin fuga de datos y con baselines de persistencia explícitas. [file:1]

La pregunta central es: ¿hasta qué horizonte temporal las predicciones de PM10 y PM2.5 superan de forma robusta a la persistencia en Elche y Florencia, y cómo varía ese horizonte entre estaciones y entre contaminantes bajo un protocolo homogéneo? [file:1]

## 2. Dominios geográficos y estaciones

- Dominios:
  - Elche (España): red urbana oficial de calidad del aire.
  - Florencia (Italia): red urbana oficial de calidad del aire (ARPAT / equivalente) y datos reportados a EEA. [file:1]

- Criterios de selección de estaciones:
  - Estaciones urbanas o periurbanas que midan simultáneamente PM10 y PM2.5.
  - Series diarias con periodo histórico suficiente para aplicar validación rolling-origin con Hmax = 7 días.
  - Cumplir un criterio mínimo de completitud (porcentaje de datos válidos) que se definirá y documentará explícitamente.
  - Solo estaciones oficiales (no se incluyen estaciones experimentales de la UMH ni sensores low-cost). [file:1]

- Horquilla esperada:
  - Aproximadamente entre 3 y 8 estaciones válidas por ciudad tras aplicar filtros de calidad. [file:1]

## 3. Variables, frecuencia y horizonte

- Contaminantes núcleo:
  - PM10
  - PM2.5 [file:1]

- Frecuencia temporal:
  - Series diarias (un valor diario por contaminante, estación y día). [file:1]

- Horizonte máximo de predicción:
  - Hmax = 7 días (h = 1, 2, …, 7). [file:1]

Los dos contaminantes y las dos ciudades se evaluarán con la misma frecuencia y el mismo horizonte máximo.

## 4. Modelos permitidos

El estudio se limita intencionadamente a un conjunto sobrio de modelos, común a todas las estaciones y contaminantes:

- Baselines:
  - Persistencia simple (y_t+h = y_t).
  - Persistencia estacional si procede (por ejemplo, reutilizando el valor de hace 7 días) como baseline adicional documentada. [file:1]

- Modelos estadísticos:
  - ARIMA / SARIMA (implementación estándar, sin tuning extremo). [file:1]

- Modelo de machine learning tabular:
  - Un único modelo de boosting (XGBoost o LightGBM) entrenado con variables de entrada construidas a partir de lags de la propia serie (y, eventualmente, calendario simple).
  - Sin tuning agresivo: hiperparámetros razonables, comunes o con reglas sencillas. [file:1]

No se introducirán otros modelos (redes neuronales, ensembles complejos, etc.) salvo decisión explícita posterior, que deberá quedar registrada en este documento.

## 5. Protocolo de validación y preprocesado

- Validación temporal:
  - Rolling-origin (expanding window o esquema similar) en todas las estaciones y contaminantes, con el mismo diseño de orígenes de predicción. [file:1]

- Preprocesado:
  - “Train-only”: cualquier decisión de filtrado, imputación o transformación de datos que pueda inducir fuga de información se hará utilizando exclusivamente información del conjunto de entrenamiento.
  - No se utilizará información futura (respecto a cada origen) en ninguna etapa del pipeline. [file:1]

- Métricas e indicadores:
  - Cálculo de errores por horizonte h (1 a 7 días) para cada modelo y baseline.
  - Cálculo de Skill(h) relativo a la persistencia. [file:1]
  - Derivación de:
    - H (primer horizonte donde el modelo deja de ser útil).
    - H*(relax).
    - H*(strict).
  - Todas las definiciones seguirán el marco H/H* establecido en los trabajos previos (AE PM10 y paper cross-domain H*). [file:1]

## 6. Homogeneidad del protocolo

Para garantizar que las diferencias en H* se atribuyen a la dinámica física y a la red de medida, y no a cambios metodológicos, se fijan las siguientes restricciones:

- Mismos modelos (tipos) en todas las estaciones y contaminantes.
- Misma definición de baselines de persistencia.
- Misma frecuencia (diaria) y mismo horizonte máximo (7 días).
- Misma lógica de rolling-origin y de preprocesado train-only.
- Misma forma de calcular Skill(h), H, H*(relax) y H*(strict). [file:1]

Cualquier desviación de estas reglas debe quedar documentada en una sección de “Deviations from protocol” y justificada técnicamente.

## 7. Estado del diseño

Este archivo actúa como especificación de diseño experimental **bloqueada**:

- Las decisiones anteriores se consideran “experimental design locked”.
- No se cambiarán ciudades, contaminantes, frecuencia, Hmax ni familia de modelos sin abrir una nueva versión de este documento y dejar constancia del cambio. 
