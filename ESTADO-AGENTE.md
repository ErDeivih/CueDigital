titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: CueDigital ya apunta el día a día completo desde el móvil (labor, tratamiento, abono y siembra) con avisos del servidor y ficha refrescada, y el GeoPackage del SIGPAC se ha probado con el fichero REAL de Salamanca (599,7 MB, 1.011.578 recintos): abre en 1–2 ms, busca el recinto en 2,7 ms y el contorno coincide con el del SIGPAC al milímetro. La prueba real destapó y corrigió tres fallos que el fichero sintético no veía (sistema de coordenadas 0, columnas csp/dn_surface y superficie en m²). Queda pendiente el streaming de la descarga (638 MB en RAM) y la limpieza del GeoPackage guardado.
estado: en-curso
tarea: probado el GeoPackage con el fichero real de una provincia y cerrado el apunte del día a día (tratamientos, abonos y siembras) en la app nueva
nivel: 2
siguiente: streaming de la descarga del GeoPackage y limpieza de caché; PAC de años anteriores y pantallas propias de PAC y gastos
bloqueado: PSD2 (nivel 3, sin coste publicado y sin gasto aprobado); y siguen pendientes de terceros las licencias (CIT, IGN) y los formatos del expediente y del Cuecyl antiguo
fecha: 2026-11-07

## Lo que se ha hecho en esta ronda

1. **GeoPackage con el fichero REAL de una provincia** (prioridad de David): Salamanca 37, campaña 2026.
   - **599,7 MB de ZIP → 1.070 MB de `.gpkg` con 1.011.578 recintos** (descarga medida: 168 s).
   - **Abrir: 1–2 ms** (el `.gpkg` se guarda al lado del ZIP y se abre directamente: antes eran 6,4–55,6 s
     descomprimiendo 1 GB en cada llamada). Validado por tamaño del miembro, fecha y que abra con sqlite;
     si está cortado o ilegible, se vuelve a extraer; si no se puede cachear, cae al temporal y lo dice.
   - **Buscar el recinto `37-70-0-0-503-51-1`: 2,7 ms**; `contornos_de_las_parcelas`: **18 ms** (antes
     6,4–55,6 s).
   - **El WKT coincide con el SIGPAC**: 17/17 puntos, centro a 0,001 m, caja a 0,005 m y superficie
     **4,9016 ha = 4,9016 ha** (0,0000 % de desvío).
   - **Tres fallos que solo se ven con el fichero real, ya corregidos**: (a) el SIGPAC pone `srs_id = 0`
     en cada geometría y el sistema va en `gpkg_geometry_columns` (4258): antes se rechazaba el mapa
     entero; (b) las columnas reales son **`csp`** y **`dn_surface`**, que no estaban entre los nombres
     aceptados (superficie y CSP salían vacíos); (c) **`dn_surface` viene en m²**, no en ha: antes cada
     parcela salía **10.000 veces más grande**. Ahora se convierte por el nombre de la columna.
   - **33 pruebas sin red** (21 + 7 de caché + 5 de nombres/sistema/m²) y script real
     `backend/scripts/probar_geopackage_real.py` que repite la medida (8 s con la caché caliente).
2. **Apuntar del día a día completo** en `/nuevo/`: la vista «Apuntar» tiene **cuatro pestañas**:
   - **Labor**: apero del vocabulario del servidor, fecha, hectáreas y nota.
   - **Tratamiento**: producto con materia activa, dosis máxima y plazo; dosis por hectárea, **total
     calculado**, plaga, justificación y nota; los avisos 422 del servidor se enseñan tal cual.
   - **Abono**: **kg/ha o kg totales** (nunca los dos), total calculado, fecha y nota.
   - **Siembra**: semilla con su variedad y **dosis kg/ha**; si la finca no tiene semillas dadas de alta,
     se ofrece **apuntarla como siembra del cuaderno** (`/api/labores`), sin inventar semillas.
   - Al guardar: aviso, ficha refrescada y siguiente paso («Ver el trabajo de hoy», «Ver el calendario»).
   - **Verificado guardando de verdad en Chrome a 390 y 360**: tratamiento (producto con registro,
     dosis, justificación; 201 y el apunte en la base), abono (kg/ha, 201) y siembra del cuaderno
     (Trigo, 210 kg/ha; 201), con **0 px de desborde en las cuatro pestañas** a los dos anchos y
     «Guardar» siempre al alcance del pulgar. La ficha se refresca y propone el siguiente paso.
3. **Limpieza**: el único servidor que se levanta es el de las verificaciones (uvicorn temporal) y se
   apaga al terminar; no queda ningún proceso de CueDigital escuchando.

## La última pasada, sobre este mismo HEAD

    Python       5909 recogidas · 5907 superadas, 2 omitidas, 0 fallos
    JavaScript   1297 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440, móvil 390/360, ficha, apuntar (4 pestañas), calendario,
    filtros, facturas, cuaderno, productos y ventana del SIGPAC                        0 fallos
    GeoPackage real (Salamanca)                                                     OK, 22 s en caliente
    capturas                                            19 en docs/capturas-nuevo/

## Lo que sigue abierto

- **Streaming de la descarga del GeoPackage**: hoy bajar una provincia carga **638 MB en RAM**; toca
  escribir a disco por trozos (en `sigpac_cache.py`).
- **Limpieza de la caché**: conviven ZIP (600 MB) y `.gpkg` (1.070 MB) por provincia; hacen falta
  política de limpieza y decisión de borrar el ZIP tras extraer.
- **PAC de años anteriores** y recintos por campaña de la Junta; pantallas propias de PAC y gastos.
- **PSD2**: dos presupuestos y decisión de gasto de David; sin código hasta contrato.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
