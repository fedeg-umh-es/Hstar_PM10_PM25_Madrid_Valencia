# ANCLA DEL PROYECTO
## H* PM10/PM2.5 Valencia–Madrid

---

## 1. Propósito de este documento

Este documento fija el **marco no negociable** del proyecto y debe gobernar dos planos a la vez:

- **la ejecución experimental**,
- **la escritura del paper**.

Su función es evitar deriva metodológica, inflación narrativa y decisiones que rompan la comparabilidad o introduzcan fuga de datos.

---

## 2. Pregunta central del proyecto

> **¿Hasta qué horizonte temporal las predicciones de PM10 y PM2.5 superan a la persistencia en Valencia y Madrid bajo un protocolo rolling-origin estricto y libre de fuga de datos?**

---

## 3. Objetivo operativo

- **2 ciudades**: Valencia y Madrid
- **2 contaminantes**: PM10 y PM2.5
- **1 horizonte multi-paso común**: h = 1, …, 7 días
- Protocolo **rolling-origin, expanding-window, train-only**
- Baseline principal: **persistencia simple**
- Baseline complementario: **persistencia estacional (lag 7 días)**

**Resultado central**: curvas **Skill(h)** y descriptores **H*_relax** y **H*_strict**.

---

## 4. Tesis metodológica

> La utilidad real de un modelo de predicción ambiental no se demuestra por tener menor error absoluto en abstracto, sino por mantener skill positivo frente a persistencia, horizonte a horizonte, bajo evaluación temporal estricta y sin fuga de datos.

---

## 5. Protocolo bloqueado

### 5.1 Unidades de análisis
Cada combinación **ciudad × contaminante × estación** se procesa como unidad independiente.

### 5.2 Frecuencia
Serie diaria.

### 5.3 Horizonte
h = 1, 2, 3, 4, 5, 6, 7 días.

### 5.4 Validación
- Rolling-origin, expanding window
- Avance cronológico estricto
- Sin particiones aleatorias
- Sin k-fold estándar
- Sin barajado temporal

### 5.5 Preprocesado
**Train-only** en cada iteración:
- escalado,
- imputación,
- selección de variables,
- transformaciones,
- construcción de lags y features.

### 5.6 Baselines
- **Principal**: persistencia simple  
  \[
  \hat{y}_{t+h} = y_t
  \]
- **Complementario**: persistencia estacional (lag 7 días)  
  \[
  \hat{y}_{t+h} = y_{t+h-7}
  \]

La persistencia estacional **nunca sustituye** al baseline principal.

### 5.7 Modelos permitidos
- **ARIMA/SARIMA** — familia lineal
- **XGBoost** — familia no lineal basada en árboles

### 5.8 Métrica principal
\[
Skill(h) = 1 - \frac{RMSE_{model}(h)}{RMSE_{baseline}(h)}
\]

### 5.9 Descriptores obligatorios
- **H*_relax**: máximo \( h \) tal que \( Skill(h) > 0 \), aunque existan huecos intermedios
- **H*_strict**: longitud del mayor intervalo contiguo con \( Skill(h) > 0 \)

---

## 6. Regla de interpretación

El orden de lectura de resultados es obligatorio:

1. **¿Hay skill positivo frente a persistencia?**
2. **¿En qué horizontes aparece?**
3. **¿Es continuo o fragmentado?**
4. **¿Cuál es H*_relax?**
5. **¿Cuál es H*_strict?**
6. **¿Cómo cambia según ciudad, contaminante y estación?**

**Solo después de esto** se comentan diferencias entre SARIMA y XGBoost.

---

## 7. Fuentes de datos

| Ciudad | Contaminantes | Fuente | Fichero base |
|---|---|---|---|
| Valencia | PM10, PM2.5 | RVVCCA | `rvvcca.csv` → `rvvcca_long.csv` |
| Madrid | PM10, PM2.5 | Ayuntamiento de Madrid | `201200-1-calidad-aire-horario-csv.csv` → `madrid_long.csv` |

### Series inicialmente preparadas
- **46** series ciudad × estación × contaminante

### Series excluidas por longitud efectiva insuficiente
- **Madrid PM10**: estación **55**
- **Valencia PM10**: estación **Olivereta**
- **Valencia PM2.5**: estación **Olivereta**

### Corpus final válido
- **43** series válidas:
  - **25 Madrid** = 14 PM10 + 11 PM2.5
  - **18 Valencia** = 10 PM10 + 8 PM2.5

---

## 8. Pipeline de ejecución

```bash
# Valencia
python3 code/convert_wide_to_long.py
python3 code/query_eea_stations_v2.py \
  --input /Users/federicogarciacrespi/Downloads/rvvcca_long.csv \
  --output-dir data_pm
python3 code/build_daily_pm_series.py \
  --input-dir data_pm --output-dir data_pm_daily --agg mean
python3 code/run_rolling_skill.py \
  --batch --input-dir data_pm_daily --output-dir results_valencia

# Madrid
python3 code/convert_madrid_to_long.py
python3 code/query_eea_stations_v2.py \
  --input /Users/federicogarciacrespi/Downloads/madrid_long.csv \
  --output-dir data_pm
python3 code/build_daily_pm_series.py \
  --input-dir data_pm --output-dir data_pm_daily --agg mean
python3 code/run_rolling_skill.py \
  --batch --input-dir data_pm_daily --output-dir results
```

---

## 9. Resultados validados (nivel de patrón, no tabla congelada)

### 9.1 Baseline principal
- Persistencia simple produjo:
  - `H_relax = 0`
  - `H_strict = 0`
- Esto se observó en las 43 series válidas.
- Su función es fijar el zero-skill reference del marco H*.

### 9.2 SARIMA
- Alcanzó `H_relax = 7` días en todas las series válidas según el resumen global del manuscrito.
- Su `H_strict` fue sistemáticamente menor que `H_relax`, lo que confirma fragmentación de skill y hace operativamente más relevante `H_strict` que `H_relax`.

### 9.3 XGBoost
- Alcanzó `H_relax = 7` días en la gran mayoría de series.
- Presentó mayor variabilidad y mayor fragmentación que SARIMA, incluyendo colapso a `H_relax = 0` en algunas estaciones PM10 de Madrid.

### 9.4 Persistencia estacional
- Generó skill positivo aislado en algunos horizontes, pero no una ventana operativa contigua robusta.

### 9.5 Patrón empírico central
- Valencia fue, en términos generales, más predecible que Madrid.
- PM2.5 mostró mayor continuidad de skill que PM10.
- La utilidad operativa real depende de `H_strict`, no solo de `H_relax`.

### 9.6 Regla de gobernanza sobre resultados

Este ancla no debe congelar medianas concretas como verdad permanente del proyecto.
Las cifras finas deben leerse del manuscrito y de los CSV auditados, no de este documento.
El ancla fija patrones, reglas y estructura interpretativa.

---

## 10. Estado actual del manuscrito

| Componente | Estado |
|---|---|
| Título | ✅ |
| Abstract | ✅ |
| Introducción | ✅ |
| Data sources / preprocessing | ✅ |
| Validation protocol | ✅ |
| Results | ✅ |
| Discussion | ✅ |
| Conclusions | ✅ |
| Tablas y figuras | ✅ |
| Compilación LaTeX | ✅ |
| PDF legible y coherente | ✅ |
| Cover letter / paquete editorial | ⏳ según revista objetivo |

### Nota

El manuscrito está en fase de cierre editorial, no de reparación metodológica.

---

## 11. Estructura argumental obligatoria del paper

El paper debe sostener esta secuencia:

1. Problema de la literatura:
   - validación temporal débil,
   - riesgo de leakage,
   - ausencia de persistencia,
   - reporting insuficiente horizonte a horizonte.
2. Solución propuesta:
   - rolling-origin,
   - expanding window,
   - preprocesado train-only,
   - baseline explícito,
   - curvas Skill(h).
3. Descriptores operativos:
   - H*_relax = alcance total
   - H*_strict = continuidad útil real
4. Lectura empírica:
   - ciudad,
   - contaminante,
   - estación,
   - continuidad vs fragmentación del skill.
5. Mensaje final:
   - no importa solo si el modelo mejora el error,
   - importa hasta cuándo mejora a persistencia de manera operativamente útil.

---

## 12. Movimientos no permitidos

Queda prohibido:
- usar particiones aleatorias,
- usar k-fold estándar,
- usar preprocesado global,
- omitir persistencia simple,
- sustituir la lectura por RMSE/MAE sin Skill(h),
- reportar solo H*_relax cuando el perfil sea fragmentado,
- convertir el paper en una comparación de “modelos ganadores”,
- introducir arquitecturas fuera de SARIMA/XGBoost,
- mantener en el manuscrito restos activos de Alicante/Elche como dominio experimental principal,
- congelar en este ancla cifras antiguas que ya no coincidan con el paper vivo.

---

## 13. Mandato final
- Primero rigor temporal
- Después comparación con persistencia
- Después lectura horizonte a horizonte
- Solo al final comparación entre modelos

Si una decisión mejora el brillo del resultado pero debilita la validez del protocolo, esa decisión queda descartada.

---

## 14. Frase rectora del proyecto

No estamos buscando el modelo más llamativo. Estamos midiendo, con rigor, hasta cuándo un modelo es realmente útil frente a persistencia.
