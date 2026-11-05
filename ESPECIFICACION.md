# Especificación — CueDigital

Estado: **borrador**. Documento de coordinación; el proyecto ya tiene sus documentos en `docs/`.

## Alcance nuevo (2026-11-04) — manda sobre lo anterior

David cambió el rumbo: **la interfaz anterior no le gustaba y el producto se rehace** como **la
herramienta digital del agricultor de Castilla y León** (cuaderno de campo, PAC y subvenciones,
parcelas del SIGPAC). El alcance vinculante está en [`ALCANCE-AGRICOLA.md`](ALCANCE-AGRICOLA.md) y
manda sobre la interfaz y sobre los datos de la Junta. La investigación que lo sostiene —con URL y
fecha en cada afirmación, y lo pendiente marcado— está en
[`docs/INVESTIGACION-AGRICOLA.md`](docs/INVESTIGACION-AGRICOLA.md); la propuesta de pantallas para
aprobar, en [`docs/ARQUITECTURA-DE-PANTALLAS.md`](docs/ARQUITECTURA-DE-PANTALLAS.md); y el aspecto,
en `designs/cue-agricola-design-system/` y `designs/cue-agricola/`.

**Orden de valor**: parcelas del SIGPAC → cuaderno apuntable en 30 s → campaña y ficha de parcela →
PAC/subvenciones → exportación. **No se reescribe el backend**: se conserva lo que sirve (firma,
contratos, datos). Reglas del 04/11: sin GitHub Actions, push selectivo, `.env` y fixtures de firma
intactos, autorización en el servidor con matriz de roles, y **toda afirmación de normativa o formato
con fuente y fecha o marcada como pendiente**.

## Decisión de coordinación anterior (2026-11-04)

**¿Qué corpus y qué proveedor para D08?**

- No se decide a ciegas: el agente **propone dos opciones concretas** con coste, licencia y límite de uso, y elige **la más barata que cumpla**.
- El corpus debe poder **citarse** (documento, página) y su licencia no puede impedir el uso en producción.
- Si las dos opciones tienen coste relevante, para y pregunta: es nivel 3.

## Decisión tomada (2026-11-04)

La regla anterior se ha aplicado y **está decidido**. Las dos opciones de cada decisión, medidas con
coste, licencia y límite de uso (URL y fecha en cada cifra), están en
[`docs/D08_CORPUS_Y_PROVEEDOR.md`](docs/D08_CORPUS_Y_PROVEEDOR.md):

| decisión | se elige (0 €) | la alternativa, para comparar |
|---|---|---|
| **Corpus** | facturas reales del titular y sus proveedores, **con permiso escrito**; se cita cada una por emisor, número y página | corpus públicos FATURA + CORD (CC BY 4.0), que **no miden** el NIF ni el IVA español |
| **Proveedor de OCR** | **Tesseract local** (ya construido, Apache 2.0) | Azure AI Document Intelligence: 1,50 USD/1.000 páginas |
| **Meteo y satélite** | **AEMET OpenData + Copernicus Data Space Ecosystem**, con atribución | Sentinel Hub plan Basic: **999 €/año + IVA** |

**Lo que sigue bloqueado, y de quién depende**: el **material del corpus** —30 facturas (10 en PDF,
10 escaneadas, 10 fotografiadas) con **permiso escrito del emisor** y los 7 valores de patrón de cada
una—. Es una aportación de David, **no un gasto**. Sin eso no se mide el OCR y **D08 no se cierra**;
lo que sí se puede hacer mientras tanto son las tareas D08-1 y D08-2 del `BACKLOG.md`. La decisión y su
motivo están en `DECISIONES.md`.

## Aprobación del diseño (2026-11-05), con ocho correcciones

David vio el sistema de diseño y los artboards y **dio el visto bueno con correcciones**. Se
incorporan a `docs/ARQUITECTURA-DE-PANTALLAS.md` (apartado 0) y al canvas:

1. **Parcelas en el mapa**: no tienen por qué estar juntas ni caber en una imagen → zoom, agrupación
   y selección; no se supone una finca única.
2. **Facturas de fotos**: leer la foto (OCR) y devolver una propuesta para revisar campo a campo.
3. **Cuaderno guiado**: decir qué necesita el apunte para ser válido, qué falta y avisar sin bloquear.
4. **Productos y abonos con dosis por hectárea** y total calculado.
5. **Favoritos** de productos, abonos y tratamientos.
6. **PAC y años anteriores**: importar o modificar registros para ver la evolución de una tierra,
   con **producción estimada por hectárea** y **variedad de semilla**.
7. **Registro de parcelas fácil**: guiado o importando la PAC de un año (los dos vídeos de referencia
   de David se incorporan cuando los pase).
8. **Panel de tierras con mapa**: seleccionar cada tierra y ver sus datos y sus registros de otros años.

Y la **doctrina §8** (`F:\EspacioCodigo\_flujo-dsh\DOCTRINA-CALIDAD.md`): **la interfaz no habla de
cómo está hecha**; los textos de desarrollador se borran, no se sustituyen.

## Reglas

- No tocar `.env` ni las fixtures de firma.
- Autorización en el servidor, con matriz de roles escrita.
- Pruebas de flujo, no de detalle: ver `F:\EspacioCodigo\_flujo-dsh\DOCTRINA-CALIDAD.md`.

## Decision de coordinacion (2026-11-04, noche) — el corpus de facturas queda aparcado

David no va a aportar ahora las 30 facturas con permiso escrito.

- **D08 queda aparcado** hasta que él lo traiga. No se bloquea nada más por eso.
- El trabajo hecho de D08 (dos opciones medidas, todas a coste 0) se queda como está: sirve cuando llegue el corpus.
- **Prioridad ahora: la aplicación del agricultor.** Interfaz nueva, SIGPAC, cuaderno de campo, campaña y PAC.
- Sigue en pie todo lo de ALCANCE-AGRICOLA.md, empezando por la investigación con fuente oficial.
