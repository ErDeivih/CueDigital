# Tablas de nitrógeno de Castilla y León

`limites_y_periodos_mav_398_2022.json` se **extrae**, no se rellena a mano, del PDF íntegro
de la [Orden MAV/398/2022 en el BOCyL](https://bocyl.jcyl.es/boletines/2022/05/05/pdf/BOCYL-D-05052022-1.pdf).
El PDF oficial se conserva como `Orden_MAV_398_2022.pdf` para poder cotejar las cifras sin
depender de la red. El JSON incorpora la URL, fecha de descarga, tamaño y SHA-256 del PDF.

Desde `backend/`, con las dependencias de `requirements.txt` instaladas:

```text
../.venv/Scripts/python.exe scripts/bajar_nitratos_cyl.py
```

`--sin-descarga` reproduce el JSON a partir de la copia oficial guardada. El script se detiene
si cambian la cabecera, las páginas o el número de filas; obliga a revisar una nueva versión
en lugar de reinterpretarla silenciosamente.

El **Anexo III (BOCyL p. 20895)** da máximos por cultivo y secano/regadío. Las casillas
vacías se guardan como `null`, nunca como cero. La nota al pie permite ajustar el aporte
según la cosecha esperada y remite a la guía MAPA para cultivos no enumerados. El
**Anexo V (p. 20897)** da periodos por grupo y tipo de fertilizante. Incluye condiciones
relativas a siembra, recolección, riegos, parada vegetativa y excepciones que aquí se
conservan literalmente como texto, sin convertirlas en fechas inventadas. Los tipos
orgánicos A, B y C se describen en el **Anexo I (p. 20893)**.

El programa de actuación se aplica a explotaciones de **zonas vulnerables**. El listado
municipal oficial del Decreto 5/2020 se ha derivado del Excel de IDECyL y está en
[`data/zv_cyl.csv`](../zv_cyl.csv), con su [procedencia](../zv_cyl_fuentes/LEEME.md).
Cuando se conoce la pertenencia municipal y el nombre del cultivo coincide exactamente con
una fila del Anexo III, la aplicación avisa si el total apuntado supera la cifra publicada;
permite guardar el apunte y recuerda el ajuste por cosecha esperada. El listado municipal no
resuelve dudas sobre límites de una parcela ni confirma por sí solo cambios normativos
posteriores. Los periodos relativos del Anexo V siguen siendo información de consulta: no se
deducen fechas que la orden no da.
