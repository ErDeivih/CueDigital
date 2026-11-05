titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: CueDigital ya tiene el cuaderno guiado que dice qué falta para que el registro esté completo, agrupado por dónde se arregla y con el botón que lleva a cada pantalla; productos y abonos con su dosis por hectárea y el total calculado antes de apuntar; y el flujo que pidió David encadenado (foto a la factura o al envase → elegir tierra → trabajo del día → historial → calendario → filtros con cantidades). Además, el GeoPackage del SIGPAC ya se abre: lee los recintos y rellena con ellos los contornos de las tierras. PSD2 sigue parado a propósito: ningún proveedor publica precio y David no ha aprobado gasto.
estado: en-curso
tarea: implementados el cuaderno guiado, los productos/abonos con dosis por hectárea, el flujo encadenado y la apertura del GeoPackage para los contornos
nivel: 2
siguiente: probar el GeoPackage con un fichero real de 600 MB, llevar tratamientos/abonos/siembra/cosecha del día a día a la app nueva, y las pantallas de PAC y gastos
bloqueado: PSD2 (nivel 3, sin coste publicado y sin gasto aprobado); y siguen pendientes de terceros las licencias (CIT, IGN) y los formatos del expediente y del Cuecyl antiguo
fecha: 2026-11-05

## Lo que se ha hecho en esta ronda (bloque 4)

1. **Cuaderno guiado** (`/nuevo/`, «Cuaderno» en la barra): cabecera con **cuántas cosas faltan**,
   lista **agrupada por dónde se arregla** (finca, tierras, productos y máquinas, volcado a la Junta…),
   cada cosa con su «dónde» y el botón que lleva a esa pantalla (nueva cuando existe; a la app vieja
   cuando aún no). Lo que **bloquea el envío a la Junta** se dice con palabra, no solo color. Si no
   falta nada: «El cuaderno está completo». Con la finca de prueba: **29 secciones y 123 cosas**; al
   pie, «Abrir el cuaderno de la Junta».
2. **Productos y abonos con dosis por hectárea** (`/nuevo/`, «Productos»): pestañas de productos y
   abonos con buscador; cada producto con **dosis máxima por hectárea y su unidad**, materia activa y
   plazo de seguridad; cada abono con su **riqueza N/P/K**. «Apuntar en una tierra» con tierra, fecha,
   hectáreas, dosis por hectárea y **el total calculado antes de guardar**; se guarda en
   `/api/tratamientos` o `/api/fertilizaciones` y, si el servidor no deja, se enseña su aviso en
   palabras de agricultor (nada de «no se ha podido»). Verificado en Chrome: 24 productos y el total.
3. **El flujo que pidió David, encadenado**: **foto a la factura o al envase → elegir tierra →
   trabajo del día → historial → calendario → filtros por tipo con cantidades**. Las piezas ya estaban;
   ahora cada final propone el siguiente paso («Elige la tierra», «Ver el calendario», «Ver todos los
   trabajos», «Ver el trabajo de hoy»), para que el agricultor no se quede sin saber qué toca.
4. **El GeoPackage del SIGPAC, abierto** (segunda mitad de AGR-15): `app/geopackage_sigpac.py` lee el
   `.gpkg` de la caché **sin GDAL ni shapely** (descubre la tabla y la columna de geometría, descubre
   los atributos por su nombre, traduce el blob `GP`+WKB a WKT y anillos; Polygon y MultiPolygon; con
   Z/M o tipos raros se para con su código en vez de leerlos mal). La puerta
   `POST /api/sigpac/cache/{provincia}/contornos` rellena `geometria`/`dibujo` de las parcelas de la
   finca que casan por su referencia SIGPAC, es idempotente y no toca otra finca; 21 pruebas con un
   gpkg sintético, sin internet. **Falta probarlo con el fichero real de 600 MB** (streaming/índice) y
   decidir si el ZIP se guarda extraído.
5. **PSD2, sin proponer gasto**: `docs/PSD2-AGREGADORES.md` tiene ya la sección **«El coste, en
   claro»**. Resultado: **ningún proveedor publica precio de producción**; solo hay una cifra (sandbox
   de BBVA, 0 €); Tink publica «por usuario/mes» sin importe y GoCardless la unidad «requisición
   activa al mes» sin precio. El coste anual del escenario **no es calculable** sin presupuesto y no se
   inventa: se piden **dos presupuestos escritos** (Enable Banking y Powens/Unnax) y **decide David**,
   que no ha aprobado gasto. Sin código de PSD2 hasta contrato.

## La última pasada, sobre este mismo HEAD

    Python       5858 recogidas · 5856 superadas, 2 omitidas, 0 fallos
    JavaScript   1282 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440, ficha, apuntar, calendario, filtros, facturas,
    cuaderno guiado y productos con dosis                                            0 fallos
    capturas                                            15 en docs/capturas-nuevo/

## Lo que sigue abierto

- **Probar el GeoPackage con el fichero real** de una provincia (600 MB): tiempo, memoria y si hace
  falta índice propio o guardar el `.gpkg` extraído.
- **Tratamientos, abonos, siembra y cosecha del día a día** en la app nueva (el trabajo de suelo ya
  está) y la **cola sin cobertura**.
- **PAC de años anteriores** y recintos por campaña de la Junta; pantallas propias de PAC y gastos.
- **PSD2**: dos presupuestos y decisión de gasto de David; después, conectar cuentas en solo lectura.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
