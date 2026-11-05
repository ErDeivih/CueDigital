titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: La interfaz nueva ya está en pie en /nuevo/: armazón, «Hoy» y «Mis parcelas», recorrible a 390, 1024 y 1440 px, con los cuatro estados y verificado en Chrome de verdad (0 fallos). El SIGPAC ya guarda uso, coeficiente de regadío, región y admisibilidad, y puede descargar y cachear el mapa por provincia. La app vieja sigue viva en / hasta que la nueva cubra cada recorrido. Falta el cuaderno guiado, los productos con dosis, las facturas de foto y el histórico de la PAC.
estado: en-curso
tarea: implementada la primera entrega de la interfaz nueva y la parte de SIGPAC (atributos y caché), con pruebas y navegador
nivel: 2
siguiente: conectar el cuaderno guiado y los productos con dosis en /nuevo/, y abrir el GeoPackage para importar recintos
bloqueado: nada duro; siguen pendientes de terceros las licencias (CIT, IGN), los formatos del expediente y del Cuecyl, y los vídeos correctos de SIGPAC
fecha: 2026-11-05

## Lo que se ha hecho en esta sesion

1. **La interfaz nueva (`/nuevo/`)**, con la app vieja intacta en `/`:
   - **Armazón**: barra superior (finca, campaña, conexión, cuenta), barra lateral en tableta/PC y
     barra inferior de cinco destinos en el móvil, con el botón de apuntar en el centro.
   - **«Hoy»**: la finca delante, contador de tierras, botón principal de apuntar y lo último apuntado.
   - **«Mis parcelas»**: contador con hectáreas y municipios, buscador, **lista agrupada por municipio**
     (las parcelas no están todas juntas), **mapa real** con la ortofoto del IGN y los linderos, zoom,
     selector de zona y **panel de la tierra** con sus datos del SIGPAC y **sus otros años**.
   - **Los cuatro estados de verdad**: cargando (primer pintado siempre), error con reintentar, vacío
     con el botón que lo arregla y sin permiso con el enlace a entrar.
   - **Doctrina §8 aplicada**: sin textos de desarrollador, sin explicar cálculos, sin relleno; los
     textos del agricultor viven en `modelo.js` y no llevan jerga prohibida.
2. **Verificación en navegador de verdad** (`scripts/comprobar_el_armazon_nuevo.py`, Chrome por CDP,
   con la explotación de 64 tierras): **0 fallos a 390, 1024 y 1440 px**, sin scroll horizontal, con la
   navegación cambiando según el ancho, 5 municipios agrupados, 64 filas, mapa con imagen, panel con
   alias y otros años, y los cuatro estados. Capturas en `docs/capturas-nuevo/`.
3. **SIGPAC (AGR-3, primera mitad)**:
   - `Parcela` gana `coef_regadio`, `region` y `admisibilidad` (CSP), y se **guardan al dar de alta**
     desde el SIGPAC; nulo = no consta, nunca 0. Se ven también en `/sigpac/buscar` y en la auditoría.
   - **Descarga por provincia con caché**: `GET /sigpac/cache` y `POST /sigpac/cache/{provincia}`
     (con permiso de modificar, comprobado **antes** de salir a la red). Listado del FEGA → enlace de la
     provincia → ZIP verificado con su `.gpkg` dentro → sha256 y ficha con campaña, fecha de validez,
     licencia CC BY 4.0 y cita al FEGA/Catastro. `fetch` inyectable: los tests no salen a internet.
   - Queda **pendiente abrir el GeoPackage** e importar sus recintos (necesita leer SQLite/GDAL del
     `.gpkg`); hoy se entrega la descarga fiable y cacheada, no su contenido.
4. **API nueva**: `GET /api/nuevo/hoy` y `GET /api/nuevo/tierras`, con sesión y finca obligatorias,
   aislamiento probado y nada inventado (sin tierras son cero; sin superficie el total es nulo, no una
   suma a medias).
5. **La app vieja sigue viva**: `/` no se ha tocado y sus recorridos siguen funcionando; se retirará
   pantalla a pantalla cuando la nueva cubra cada uno.

## La última pasada, sobre este mismo HEAD

    Python       5743 recogidas · 5741 superadas, 2 omitidas, 0 fallos
    JavaScript   1245 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440         0 fallos
    capturas                                        7 en docs/capturas-nuevo/

## Lo que sigue abierto

- **Conectar en `/nuevo/`** el cuaderno guiado, los productos y abonos con dosis por hectárea, los
  favoritos y las facturas de foto (el diseño ya está aprobado; falta implementarlo).
- **Abrir el GeoPackage** descargado e importar sus recintos (segunda mitad de AGR-3), y el streaming
  para no traer 628 MB a memoria.
- **El histórico de la PAC** por años y la evolución de una tierra (AGR-10), con los canales
  verificados; y la importación de recintos por campaña.
- **Pendiente de terceros**: licencia del SHP de CyL (CIT) y de la ortofoto PNOA (IGN); formato de
  «Documentos del expediente» y del Cuecyl de años anteriores; los **dos vídeos correctos de SIGPAC**
  (los pasados no eran); valores de los catálogos oficiales.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
