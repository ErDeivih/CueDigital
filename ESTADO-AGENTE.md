titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: CueDigital ya apunta el día a día completo desde el móvil (labor, tratamiento, abono y siembra) y el GeoPackage REAL del SIGPAC tiene puerta en la ventana de selección: se elige la provincia ya guardada y se traen los contornos de toda la finca, con el resultado en palabras y la atribución del FEGA. Verificado en Chrome aplicando de verdad el mapa de Salamanca (1 contorno puesto) y con el bloque sin desbordar a 390 y 360. Quedan pendientes declarados el streaming de la descarga, la limpieza de la caché y la cola sin cobertura.
estado: en-curso
tarea: cerrado el apunte del día a día completo y la puerta a los contornos del GeoPackage real desde la ventana del SIGPAC, con la interfaz móvil medida
nivel: 2
siguiente: streaming de la descarga del GeoPackage y limpieza de caché; cola sin cobertura; PAC de años anteriores y pantallas propias de PAC y gastos
bloqueado: PSD2 (nivel 3, sin coste publicado y sin gasto aprobado); y siguen pendientes de terceros las licencias (CIT, IGN) y los formatos del expediente y del Cuecyl antiguo
fecha: 2026-11-07

## Lo que se ha hecho en esta ronda

1. **El apunte del día a día, cerrado de verdad**: la vista «Apuntar» de `/nuevo/` tiene cuatro
   pestañas —**labor, tratamiento, abono y siembra**— y se ha verificado **guardando en Chrome** a
   390 px: tratamiento con producto registrado, dosis por hectárea y justificación (**201**), abono en
   kg/ha (**201**) y siembra del cuaderno (**201**, Trigo 210 kg/ha). La ficha se refresca con «Hoy en
   esta tierra» y ofrece el siguiente paso. Las cuatro pestañas dan **0 px de desborde** a 390×844 y
   360×640, sin solapamientos.
2. **Puerta al GeoPackage real desde la ventana del SIGPAC** (lo que faltaba: el dato existía y no se
   podía pedir): tarjeta «Los contornos de toda la finca» que:
   - pide `GET /api/sigpac/cache` y enseña las provincias ya guardadas con su campaña y validez;
   - avisa de que **solo rellena la forma** de las tierras que ya tienes (no toca superficie, uso ni
     municipio);
   - trae los contornos con `POST /api/sigpac/cache/{provincia}/contornos` y da el resultado en
     palabras: **«1 contorno puesto · 21 tierras sin códigos del SIGPAC»** (la finca de ejemplo no
     tiene referencias completas; se dice, no se inventa);
   - muestra la **atribución y licencia del FEGA**;
   - si no hay mapa guardado **no dispara ninguna descarga de 600 MB**: lo dice y remite a prepararla.
   - **Verificado con el GeoPackage real de Salamanca** (599,7 MB, 1.011.578 recintos) aplicado desde la
     ventana: el servidor abrió el `.gpkg` guardado, casó la tierra y devolvió el contorno en ms.
3. **Móvil primero**: la ventana sigue a pantalla completa a 390×844 y 360×640; el bloque nuevo mide
   358/328 px y **0 px de desborde**; el botón «Traer los contornos» mide **56 px** de alto; el scroll
   es de la ventana y no de la página de detrás. A 1024 el bloque no desborda.
4. **Limpieza**: el único servidor que se levanta es el de las verificaciones (uvicorn temporal) y se
   apaga al terminar; no queda ningún proceso de CueDigital escuchando.

## La última pasada, sobre este mismo HEAD

    Python       5910 recogidas · 5908 superadas, 2 omitidas, 0 fallos
    JavaScript   1301 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440, móvil 390/360, ficha, apuntar (4 pestañas guardando),
    calendario, filtros, facturas, cuaderno, productos y ventana del SIGPAC con contornos reales
                                                                                    0 fallos
    GeoPackage real (Salamanca) aplicado desde la ventana                         OK (1 contorno)
    capturas                                            19 en docs/capturas-nuevo/

## Lo que sigue abierto

- **Streaming de la descarga del GeoPackage**: bajar una provincia carga **638 MB en RAM**; toca
  escribir a disco por trozos (en `sigpac_cache.py`).
- **Limpieza de la caché**: conviven ZIP (600 MB) y `.gpkg` (1.070 MB) por provincia; falta política de
  limpieza y decidir si se borra el ZIP tras extraer.
- **Cola sin cobertura** del apunte y **cosecha comercializada** en la app nueva.
- **PAC de años anteriores** y recintos por campaña de la Junta; pantallas propias de PAC y gastos.
- **PSD2**: dos presupuestos y decisión de gasto de David; sin código hasta contrato.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
