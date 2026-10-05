# Municipios de zonas vulnerables de Castilla y León

[`zv_cyl.csv`](../zv_cyl.csv) se deriva del [Excel oficial de IDECyL](https://opendata.jcyl.es/ficheros/carto/medioambiente/sostenibilidad/coad_cyl_vulnerab_nitrat.xlsx), enlazado desde su [ficha de metadatos](https://idecyl.jcyl.es/geonetwork/static/api/records/spagobcylsoscoavulnitz20). La fuente contiene **387 municipios y 24 zonas** del Decreto 5/2020. La provincia se obtiene de los dos primeros dígitos del código municipal con la [tabla oficial del INE](https://www.ine.es/daco/daco42/codmun/cod_provincia.htm). El nombre y el código de municipio proceden del Excel de IDECyL.

Se guardan copias de ambos originales y sus huellas SHA-256 en [`procedencia.json`](procedencia.json). Para volver a generar y comprobar el CSV desde esas copias, ejecutar desde `backend/`:

```text
../.venv/Scripts/python.exe scripts/bajar_zonas_vulnerables_cyl.py --sin-descarga
```

Sin `--sin-descarga` se descargan versiones nuevas. Si cambia la forma del Excel o su número de filas o zonas, el script se detiene para revisión. La ficha de IDECyL indica revisión de metadatos el 10/02/2026, pero **eso no demuestra por sí mismo que el Decreto 5/2020 no haya sido modificado**. Hay que confirmar la vigencia jurídica y la delimitación concreta ante la Junta cuando importe para una parcela. La aplicación usa coincidencia exacta de código INE o de municipio y provincia; con un municipio sin provincia ni código devuelve «no lo sé».
