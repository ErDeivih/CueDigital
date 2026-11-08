# Capturas de la app nueva (`/nuevo/`)

Todas están hechas contra el servidor de verdad, con la finca de ejemplo y, cuando se indica, con el
**GeoPackage real de Salamanca** ya descargado en la caché. Las móviles son **390×844** y **360×640**,
el tamaño de un teléfono normal; las de escritorio se guardan aparte (`armazon-1024.png`,
`armazon-1440.png`).

Se regeneran con `backend/scripts/comprobar_el_armazon_nuevo.py <url>` (móvil y contornos) y con
`backend/scripts/probar_geopackage_real.py` / `pintar_las_parcelas_del_cliente.py` (cliente y mapas).
**Ninguna captura sustituye a una prueba**: el arnés comprueba, antes de disparar la foto, que la
vista no desborda, que cada botón mide al menos 44 px y que su centro no está tapado
(`elementFromPoint`).

## Móvil, vista por vista (390 y 360)

| Fichero | Qué enseña |
|---|---|
| `movil-hoy-390.png` / `movil-hoy-360.png` | La portada con el cuaderno de hoy y los avisos |
| `movil-tierras-390.png` / `movil-tierras-360.png` | La lista de tierras, con buscador y filtros |
| `movil-ficha-390.png` / `movil-ficha-360.png` | La ficha de una tierra, con su mapa y «Apuntar un trabajo» |
| `movil-apuntar-390.png` / `movil-apuntar-360.png` | Apuntar: tierra, fecha, hectáreas, apero y guardar |
| `movil-calendario-390.png` / `movil-calendario-360.png` | El calendario del mes con los totales |
| `movil-trabajos-390.png` / `movil-trabajos-360.png` | Los trabajos con filtros y descarga |
| `movil-productos-390.png` / `movil-productos-360.png` | Productos y abonos, con la dosis por hectárea |
| `movil-cuaderno-390.png` / `movil-cuaderno-360.png` | El cuaderno guiado: lo que falta y lo que bloquea |
| `movil-facturas-390.png` / `movil-facturas-360.png` | La factura leída y su revisión |
| `movil-sigpac-390.png` / `movil-sigpac-360.png` | La ventana del SIGPAC, a pantalla completa |

## Contornos reales del GeoPackage de Salamanca

| Fichero | Qué enseña |
|---|---|
| `cliente-real-ficha-390.png` / `cliente-real-ficha-360.png` | Una tierra que casó con el mapa real, con la ortofoto y su contorno |
| `cliente-real-sigpac-390.png` | La ventana del SIGPAC de esa tierra, buscando su referencia real y con el recinto dibujado |
| `cliente-real-1-390.png` … `cliente-real-5-390.png` | Las **cinco parcelas del cliente** (El Prado, El Alto, La Vega, Las Eras y El Visor), cada una con su contorno real. La quinta se dio de alta con la **referencia del visor (seis números)**; el programa cogió el recinto porque esa parcela tiene uno solo |
| `cliente-contornos.png` | Montaje de los cuatro mapas con ortofoto que genera `pintar_las_parcelas_del_cliente.py` |
| `cliente-contornos-sin-red.png` | Lo mismo sin red: el contorno dibujado por el programa y el mapa con su 503 declarado |

Las cuatro tierras se dieron de alta **solo con su referencia del SIGPAC** y el programa rellenó los
códigos; el mapa se aplicó con `POST /api/sigpac/cache/37/contornos` sobre el `.gpkg` real.
