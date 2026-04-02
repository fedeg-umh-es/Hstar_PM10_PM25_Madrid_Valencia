# 02_outline_paper

## Título tentativo
Horizontes de predictibilidad H* para PM10 y PM2.5 en redes urbanas: comparacion entre Madrid y Valencia.

## Estructura del manuscrito
1. Introducción
2. Datos y área de estudio
3. Protocolo experimental
4. Modelos
5. Resultados
6. Discusión
7. Conclusiones
8. Limitaciones y trabajo futuro

## Contenido por sección
### 1) Introducción
- Motivación: previsión operativa de calidad del aire.
- Pregunta principal: hasta qué horizonte es útil predecir PM10 y PM2.5.
- Contribución: comparación de H* entre ciudades, contaminantes y estaciones bajo protocolo homogéneo.

### 2) Datos y área de estudio
- Redes oficiales y criterios de selección de estaciones.
- Periodo temporal y disponibilidad de series.
- Variables utilizadas y controles de calidad.

### 3) Protocolo experimental
- Frecuencia diaria y horizonte Hmax = 7.
- Rolling-origin sin fuga de datos.
- Definición de particiones temporales y esquema de evaluación por horizonte.

### 4) Modelos
- Persistencia (simple y estacional si aplica).
- ARIMA/SARIMA.
- Boosting (XGBoost o LightGBM) con lags tabulares.

### 5) Resultados
- Métricas por horizonte, ciudad, estación y contaminante.
- Skill(h) frente a persistencia.
- Estimación de H, H*(relax), H*(strict).
- Figuras comparativas y tablas resumen.

### 6) Discusión
- Diferencias entre PM10 y PM2.5.
- Diferencias entre Madrid y Valencia.
- Robustez y utilidad operativa de los horizontes obtenidos.

### 7) Conclusiones
- Hallazgos principales.
- Implicaciones para sistemas de alerta y planificación urbana.

### 8) Limitaciones y trabajo futuro
- Cobertura espacial y temporal.
- Posibles extensiones metodológicas manteniendo el marco comparativo.
