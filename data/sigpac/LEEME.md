# Datos oficiales del SIGPAC

Estos ficheros **no los ha escrito nadie a mano**: los baja `backend/scripts/bajar_sigpac.py` de los servicios públicos del SIGPAC.

| Fichero | De dónde sale |
|---|---|
| `cod_uso_sigpac.json` | `https://sigpac-hubcloud.es/codigossigpac/cod_uso_sigpac.json` |
| `cod_producto.json` | `https://sigpac-hubcloud.es/codigossigpac/cod_producto.json` |
| `cod_aprovechamiento.json` | `https://sigpac-hubcloud.es/codigossigpac/cod_aprovechamiento.json` |
| `cod_incidencia.json` | `https://sigpac-hubcloud.es/codigossigpac/cod_incidencia.json` |
| `cod_region_2023.json` | `https://sigpac-hubcloud.es/codigossigpac/cod_region_2023.json` |
| `recinto_de_ejemplo.json` | `https://sigpac-hubcloud.es/servicioconsultassigpac/query/recinfo/37/22/0/0/501/427/1.json` |
| `recintos_de_ejemplo.json` | `https://sigpac-hubcloud.es/ogcapi/collections/recintos/items?provincia=37&municipio=70&poligono=503&parcela=51&limit=50&f=json` |
| `recinto_de_ejemplo_503_51.json` | `https://sigpac-hubcloud.es/servicioconsultassigpac/query/recinfo/37/70/0/0/503/51/1.json` |
| `recinto_de_un_punto.json` | `https://sigpac-hubcloud.es/servicioconsultassigpac/query/recinfobypoint/4326/-5.55470/40.90730.json` |
| `referencia_de_un_punto.json` | `https://sigpac-hubcloud.es/servicioconsultassigpac/query/refrecinbycoord/4326/-5.55470/40.90730.json` |
| `referencia_catastral_de_la_parcela.json` | `https://sigpac-hubcloud.es/servicioconsultassigpac/query/refcatparcela/37/70/0/0/503/51.json` |
| `recintos_de_la_parcela.json` | `https://sigpac-hubcloud.es/servicioconsultassigpac/query/recinfoparc/37/70/0/0/503/51.json` |
| `interseccion_nitratos_si.json` | `https://sigpac-hubcloud.es/servicioconsultassigpac/intersection/nitratos/5/36/0/0/6/5015/3.json` |
| `interseccion_nitratos_no.json` | `https://sigpac-hubcloud.es/servicioconsultassigpac/intersection/nitratos/37/70/0/0/503/51/1.json` |

Las once consultas del servicio están documentadas, con su dirección exacta, en
`https://sigpac-hubcloud.es/html/csp/descServicio.html` (una página de ejemplo por
consulta). El catálogo de servicios es `https://sigpac-hubcloud.es/`.

Servicio de listas de códigos y de consultas de SIGPAC, del FEGA. Publicados bajo
licencia Creative Commons BY 4.0 según el documento «Publicación de nuevos servicios
SIGPAC de consulta y divulgación de datos del SIGC» (Reglamento de Ejecución
2023/138, conjunto de datos de alto valor).

Para actualizarlos: `python scripts/bajar_sigpac.py` desde `backend/`.
