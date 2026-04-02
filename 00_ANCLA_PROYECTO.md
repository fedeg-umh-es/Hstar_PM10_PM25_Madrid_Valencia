# ANCLA DEL PROYECTO
## H* PM10/PM2.5 Madrid-Valencia

---

## 1. Proposito de este documento

Este documento fija el marco no negociable del proyecto y debe gobernar dos planos a la vez:

- la ejecucion experimental;
- la escritura del paper.

Su funcion es evitar deriva metodologica, inflacion narrativa y decisiones que rompan la comparabilidad o introduzcan fuga de datos.

---

## 2. Proyecto activo

- Experimento principal: Madrid-Valencia, PM10/PM2.5, frecuencia diaria, `Hmax = 7`.
- Paper fundacional previo: Elche/Alicante PM10.
- Material fuera de alcance principal: SO2 Alicante, archivado como experimento exploratorio.

Nada etiquetado como Alicante o SO2 debe interpretarse como parte del manuscrito principal Madrid-Valencia.

---

## 3. Pregunta central del proyecto

> ¿Hasta que horizonte temporal las predicciones de PM10 y PM2.5 superan a la persistencia en Madrid y Valencia bajo un protocolo rolling-origin estricto y libre de fuga de datos?

---

## 4. Objetivo operativo

- 2 ciudades: Madrid y Valencia
- 2 contaminantes: PM10 y PM2.5
- 1 horizonte multi-paso comun: h = 1, ..., 7 dias
- Protocolo rolling-origin, expanding window, train-only
- Baseline principal: persistencia simple

Resultado central: curvas `Skill(h)`, descriptores `H*_relax` y `H*_strict`.

---

## 5. Protocolo bloqueado

### 5.1 Unidades de analisis
Cada combinacion `ciudad x contaminante x estacion` se procesa como unidad independiente.

### 5.2 Frecuencia
Serie diaria.

### 5.3 Horizonte
h = 1, 2, 3, 4, 5, 6, 7 dias.

### 5.4 Validacion
- Rolling-origin, expanding window
- Avance cronologico estricto
- Sin particiones aleatorias, sin k-fold, sin barajado temporal

### 5.5 Preprocesado
Train-only en cada iteracion: escalado, imputacion, seleccion de variables, transformaciones.

### 5.6 Baselines
- Principal: persistencia simple, `y_hat(t+h) = y_t`
- Complementario: persistencia estacional de 7 dias, nunca sustituto del principal

### 5.7 Modelos permitidos
- ARIMA/SARIMA
- XGBoost

---

## 6. Corpus experimental oficial

- Series preparadas/procesadas: 46
- Series validas en el analisis final: 43
- Series excluidas: 3

### Desglose de series validas
- Madrid: 25
- Madrid PM10: 14
- Madrid PM2.5: 11
- Valencia: 18
- Valencia PM10: 10
- Valencia PM2.5: 8

### Series excluidas
- Madrid PM10: estacion 55
- Valencia PM10: Valencia Olivereta
- Valencia PM2.5: Valencia Olivereta

---

## 7. Regla de contabilidad experimental

- Se procesaron 46 combinaciones ciudad-estacion-contaminante.
- El analisis final incluye 43 series validas.
- Las 3 series excluidas no deben contarse como series analizadas aunque existan ficheros generados.

Esta regla debe mantenerse igual en Methods, tablas, resultados y captions.

---

## 8. Resultados validados

### Madrid
- 25 series validas: 14 PM10 y 11 PM2.5
- Persistencia simple: `H*_relax = H*_strict = 0` en todas
- SARIMA: `H*_relax = 7` en todas; mediana `H*_strict` de 2.5 dias en PM10 y 5 dias en PM2.5
- XGBoost: `H*_relax = 7` en la mayoria; colapso a 0 en PM10 estaciones 4 y 36; mediana `H*_strict` de 3 dias en PM10 y 5 dias en PM2.5

### Valencia
- 18 series validas: 10 PM10 y 8 PM2.5
- Persistencia simple: `H*_relax = H*_strict = 0` en todas
- SARIMA: mediana `H*_strict` de 5 dias en PM10 y 7 dias en PM2.5
- XGBoost: mediana `H*_strict` de 6.5 dias en PM10 y 7 dias en PM2.5

Patron clave: Valencia es sistematicamente mas predecible que Madrid en ambos contaminantes y modelos.

---

## 9. Mandato final

- Primero rigor temporal
- Despues comparacion con persistencia
- Despues lectura horizonte a horizonte
- Solo al final comparacion entre modelos

Si una decision mejora el brillo del resultado pero debilita la validez del protocolo, esa decision queda descartada.
