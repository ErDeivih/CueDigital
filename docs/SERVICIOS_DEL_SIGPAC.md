# Los mapas y los datos del SIGPAC: qué hay y de dónde sale

> **Comprobado el 24/09/2026** contra los servicios de verdad, con las coordenadas y los códigos de
> la parcela del agricultor. Este documento existe porque el programa ahora **enseña un mapa y
> elige la parcela tocándolo**, y eso no se puede sostener sobre «creo que hay un servicio».
>
> Todo lo de aquí es **público, sin clave ni registro**, y del FEGA y del IGN (organismos
> públicos). El catálogo de servicios del SIGPAC está en <https://sigpac-hubcloud.es/>, y cada
> consulta tiene su página de ejemplo en
> <https://sigpac-hubcloud.es/html/csp/descServicio.html>.

---

## 1. Los mapas (las imágenes que ve el agricultor)

| Qué se ve | Servicio | Dirección | Comprobado |
|---|---|---|---|
| **La foto del campo** (ortofoto aérea oficial) | WMS del IGN, PNOA | `https://www.ign.es/wms-inspire/pnoa-ma`, capa `OI.OrthoimageCoverage` | ✅ devuelve un JPEG de la zona de su parcela, con el mismo aspecto que el visor del SIGPAC |
| **Los linderos de los recintos** | WMS del SIGPAC | `https://sigpac-hubcloud.es/wms`, capa `recinto` | ✅ devuelve un PNG con las líneas de los recintos |
| **Lo que se declaró como cultivo** | WMS del SIGPAC | misma dirección, capa `cultivo_declarado` | ✅ devuelve un PNG |
| **Elementos del paisaje** | WMS del SIGPAC | mismas, capas `e_paisaje`, `e_paisaje_linea`, `e_paisaje_punto` | Publicadas en el catálogo |

Los dos son WMS **1.3.0** (`GetCapabilities`, `GetMap` y `GetFeatureInfo`) y devuelven `image/png`
o `image/jpeg`. Con `EPSG:4326` el orden de la caja es **latitud, longitud** (es la norma de la
versión 1.3.0, y equivocarlo pone al agricultor en otra provincia).

**Decisión del proyecto:** las imágenes se piden al WMS oficial y **no se guardan**; los linderos
exactos se dibujan con la geometría que devuelve el servicio de consultas, que es la misma que ya
se usa para dibujar la forma de cada parcela. No se usa ninguna librería de mapas: el programa no
tiene paso de compilación y no lo va a tener por un mapa.

## 2. Las once consultas (los datos)

Todas en `https://sigpac-hubcloud.es/servicioconsultassigpac/`, y las once están **documentadas
con su dirección exacta** en la página del catálogo. En el paréntesis, para qué las usa el
programa:

| Consulta | Dirección | Uso aquí |
|---|---|---|
| Propiedades de un recinto, por códigos | `query/recinfo/[pr]/[mu]/[ag]/[zo]/[po]/[pa]/[re].json` | Traer la parcela: superficie, uso, pendiente, dibujo |
| Propiedades de un recinto, **por coordenadas** | `query/recinfobypoint/[srid]/[x]/[y].json` | **Tocar el mapa** |
| Referencia de un recinto, **por coordenadas** | `query/refrecinbycoord/[srid]/[x]/[y].json` | Tocar el mapa (versión ligera) |
| Centroide de un recinto | `query/recincentroid/[pr]/[mu]/[ag]/[zo]/[po]/[pa]/[re].json` | Para centrar el mapa en una parcela |
| **Referencia catastral** de una parcela | `query/refcatparcela/[pr]/[mu]/[ag]/[zo]/[po]/[pa].json` | Rellenar la `ReferenciaCatastral` que pide el anexo II |
| Propiedades de todos los recintos de una parcela | `query/recinfoparc/[pr]/[mu]/[ag]/[zo]/[po]/[pa].json` | Enseñar los trozos de una parcela |
| Intersección con **nitratos** | `intersection/nitratos/[pr]/[mu]/[ag]/[zo]/[po]/[pa]/[re].json` | Saber si la tierra está en zona vulnerable |
| Intersección con **Red Natura** | `intersection/red_natura/…/[re].json` | Pendiente de usar |
| Intersección con **montanera** | `intersection/montanera/…/[re].json` | Pendiente de usar |
| Intersección con **fitosanitarios** | `intersection/fitosanitarios/…/[re].json` | Pendiente de usar |
| Intersección con **pastos permanentes** | `intersection/pastos/…/[re].json` | Pendiente de usar |

Todas tienen versión `.geojson` además de `.json`. Las respuestas van **comprimidas con gzip** (el
cliente HTTP lo descomprime solo).

### Lo que devuelve una intersección, y por qué importa

```
[ ]                                     → el recinto NO está en esa capa
[ { …, "surface_intersection": 555.59,  → la superficie de la parte que sí cae dentro (m²)
      "surface_tpc": 100 } ]            → y el PORCENTAJE del recinto que cae dentro
```

Los dos nombres son los del servicio y su significado está en su página de ejemplo. El programa
distingue **tres** casos, y no es un detalle: lista con elementos («sí está, y este %»), lista
vacía («no está»), y **cualquier otra cosa** («no se sabe»). Confundir el tercero con el segundo
haría que el programa dijera «tu parcela no está en zona de nitratos» sin saberlo.

### Lo que se comprobó, con datos reales

| Comprobación | Resultado |
|---|---|
| Propiedades del recinto en un punto de su parcela | `37/70/0/0/503/53/1`, 9,055 ha, uso `TA`, pendiente 1,2, altitud 838, con dibujo |
| Referencia catastral de su parcela | `37070A503000510000AQ` (**20 caracteres**) |
| Intersección con nitratos de **su** recinto | `[ ]` → **no** está en zona vulnerable |
| Intersección con nitratos de un recinto de El Bohodón (Ávila, INE 05036) | `surface_tpc: 100`, `surface_intersection: 555,59 m²` → sí está |

> **Ojo con esto, que importa en el mapa:** el punto que se probó cae en la parcela **53**, que es
> la **vecina** de la suya (la 51). Un dedo en una linde es otra parcela. Por eso la pantalla del
> mapa tiene que enseñar **qué trozo ha encontrado y su superficie** antes de darlo de alta, y por
> eso el agricultor tiene la última palabra.

## 3. Las listas de códigos

- `https://sigpac-hubcloud.es/codigossigpac/cod_uso_sigpac.json` → los 34 usos del suelo
- `cod_producto.json` (933 productos), `cod_aprovechamiento.json`, `cod_incidencia.json`,
  `cod_region_2023.json`

Están descargadas en `data/sigpac/` con su `LEEME.md`. Se actualizan con
`python scripts/bajar_sigpac.py`.

## 4. La descarga por teselas y la API de descarga

- **Teselas vectoriales (MVT)**: `https://sigpac-hubcloud.es/mvt/[capa]@3857@geojson/{z}/{x}/{y}.geojson`
  (campaña vigente y `mvt/anterior/` para la anterior). No se usa: para lo que hace falta aquí, la
  consulta por caja de la API de descarga es más simple.
- **OGC API Features**: `https://sigpac-hubcloud.es/ogcapi`, colección `recintos`, que **acepta
  `bbox`** (comprobado). Es la que se usa para saber qué recintos hay en lo que se está viendo en
  el mapa, porque devuelve la geometría de todos ellos de una vez.

## 5. Licencia y condiciones

Datos del SIGPAC (FEGA) publicados bajo **licencia Creative Commons BY 4.0**, según el documento
«Publicación de nuevos servicios SIGPAC de consulta y divulgación de datos del SIGC» (Reglamento de
Ejecución (UE) 2023/138, conjunto de datos de alto valor). La ortofoto es del **IGN** (PNOA), del
mismo modo de acceso público. Se puede guardar y redistribuir diciendo de dónde sale: por eso cada
fichero derivado de `data/` lleva su procedencia, su huella y su script.

## 6. Lo que el programa NO hace con esto, y por qué

- **No guarda las imágenes del mapa.** Son grandes y caducan; los datos sí se guardan, y con ellos
  se puede volver a pintar la parcela sin conexión.
- **No supone que el código de municipio del SIGPAC sea el del INE.** Está comprobado con la
  parcela del agricultor y con los 387 municipios del listado de IDECyL (ver
  [`LO_QUE_OBLIGA_LA_LEY.md`](LO_QUE_OBLIGA_LA_LEY.md) y el README), pero si algún día no cuadrara,
  la búsqueda no devolvería recintos (no devolvería recintos equivocados).
- **No decide por el agricultor**: cuando hay varias posibilidades (una linde, una parcela con
  varios trozos, una intersección parcial con la zona de nitratos), se le enseña y elige él.
