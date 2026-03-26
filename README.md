# Hstar_PM10_PM25_Elche_Florencia

Repositorio de investigación para estimar y comparar el horizonte de predictibilidad operativa **H\*** de **PM10** y **PM2.5** en redes urbanas de **Elche** y **Florencia**, con frecuencia diaria y **Hmax = 7 días**.

## Utilidad del repositorio

Este repo centraliza un pipeline reproducible para:
- descargar y organizar datos oficiales de calidad del aire;
- limpiar y preparar series temporales con preprocesado **train-only**;
- entrenar modelos permitidos (persistencia, ARIMA/SARIMA y un único boosting);
- evaluar rendimiento por horizonte con validación **rolling-origin** sin leakage;
- calcular **Skill(h)** frente a persistencia y derivar **H**, **H*(relax)** y **H*(strict)**;
- generar tablas y figuras comparables para el manuscrito.

## Aplicación en la investigación

La aplicación principal es dar soporte metodológico y computacional al paper:
- cuantificando hasta qué horizonte las predicciones superan de forma robusta a la persistencia;
- comparando diferencias entre contaminantes (PM10 vs PM2.5), ciudades y estaciones;
- manteniendo un protocolo homogéneo para que las diferencias observadas se atribuyan a la dinámica de los datos y no a cambios de método.

## Alcance experimental bloqueado

Las decisiones de diseño experimental están fijadas en:
- [01_scope_protocol.md](/Users/federicogarciacrespi/Public/Hstar_PM10_PM25_Elche_Florencia/01_scope_protocol.md)
- [02_outline_paper.md](/Users/federicogarciacrespi/Public/Hstar_PM10_PM25_Elche_Florencia/02_outline_paper.md)

## Estructura de trabajo prevista

- `data_raw/`: datos originales.
- `data_processed/`: datos listos para modelado.
- `code/`: scripts de descarga, limpieza, modelado, evaluación y visualización.

## Estado

Proyecto en fase de definición y montaje del pipeline experimental base.
