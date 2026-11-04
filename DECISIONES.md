# DECISIONES — CueDigital

> Decisiones **Nivel 2** del protocolo de autonomía: se deciden sin parar la sesión, se ejecutan,
> y se anotan aquí **con el motivo**. David las revisa cuando quiere.

## 2026-11-04 · D01-R1: los rechazos pasan a un buzón (una clave por rechazo) en las dos orillas

**Decisión**: el vaciado de la cola escribe los rechazos con `cola.rechazos`
(`cuedigital.rechazado.<id_local>`, una clave por rechazo) y la pantalla los lee de ahí; se deja de
usar el array compartido `cuedigital.rechazados.<cuenta>` para escribir, y lo que haya en ese array
**se migra** al buzón al arrancar.

**Motivo**: con el array, dos rechazos simultáneos leen los dos la misma lista, cada uno escribe la
suya, y **uno de los dos desaparece**: no queda pendiente ni rechazado. Es la misma carrera que se
cerró en los pendientes (una clave por intención), viva en el array de rechazos. El buzón ya estaba
escrito y probado (`nucleo.js`, `crearBuzonDeRechazos`); lo que faltaba era **conectar las dos
orillas a la vez**, porque conectar solo la escritura dejaba a la pantalla leyendo el array viejo y
mintiendo (medido: el recorrido de la cola pasó a 9 con 2 fallos; ver commit `d8f64ad`).

**Reversibilidad**: sí. Los datos no se borran: se copian al buzón, se verifica la copia y **solo
entonces** se borra el origen; si la copia falla, el origen se queda. Un JSON corrupto se conserva.
Volver atrás es dejar de leer el buzón.

**Dueño**: cada rechazo lleva su `cuenta`. La pantalla enseña solo los de la cuenta abierta (y los
sin dueño solo cuando no hay sesión), que es exactamente lo que hacía la clave con dueño. Un rechazo
de A no se le enseña a B.

**Lo que NO cambia**: la forma de un pendiente, el turno, la migración de pendientes, la API ni los
textos que ve el agricultor.

**Comprobado (2026-11-04)**
- `node --test "tests_js/*.test.js"`: **1.228 superadas, 0 fallos** (eran 1.221: +7, contadas por el
  guardián de la documentación, que por eso se ha actualizado).
- `scripts/verificar_que_la_cola_no_cruza_cuentas.py` contra servidor y Chromium de verdad:
  **9 comprobaciones, 0 fallos**. La tercera sección es la que vale aquí: un apunte que el servidor
  rechaza **se aparta en su propia clave** y **la pantalla dice el motivo leyéndolo de ahí**.
- `pytest` completo: se anota en `ESTADO-AGENTE.md` con el resultado medido, no con el que había.

## 2026-11-04 · D08: se eligen las tres opciones de **coste 0 €** (corpus, OCR y meteo/satélite)

**Decisión**: (1) **corpus** = facturas reales del titular y de sus proveedores, **con permiso escrito**
(modelo en el documento); (2) **proveedor de OCR** = **Tesseract local**, que es lo que ya está
construido; (3) **meteo y satélite** = **AEMET OpenData + Copernicus Data Space Ecosystem**.

**Motivo**: la regla de coordinación del 04/11 pide **dos opciones concretas con coste, licencia y
límite de uso, y elegir la más barata que cumpla**. Las tres decisiones están medidas contra las
páginas oficiales ese mismo día en [`docs/D08_CORPUS_Y_PROVEEDOR.md`](docs/D08_CORPUS_Y_PROVEEDOR.md):

- corpus: la opción de 0 € **es la única que mide los seis campos críticos** (el corpus público no
  tiene NIF ni IVA español, y FATURA es sintético);
- OCR: Tesseract es **0 €**, Apache 2.0 permite vender el producto, no tiene límite contractual y **la
  factura no sale del servidor**; la nube costaría 0,75 USD/año en un escenario y añade un tercero;
- meteo/satélite: AEMET + CDSE permiten **uso comercial con atribución**, cubren las dos necesidades y
  el uso estimado cabe con más del 95 % de margen; la alternativa comercial es **999 €/año + IVA**.

**Por qué es nivel 2 y no nivel 3**: el nivel 3 se dispara cuando **las dos** opciones tienen coste
relevante. Aquí **la más barata que cumple cuesta 0 € en las tres**, así que la elección **no
compromete dinero**. Lo único que falta es **material que solo puede aportar David** (las facturas con
su permiso), y eso es una petición, no una compra: está en el apartado 6 del documento.

**Reversibilidad**: sí. **No cambia** el esquema de la base de datos, ni las rutas, ni los textos del
agricultor, ni el `.env`, ni las fixtures de firma. El corpus se puede sustituir; el lector de OCR se
puede cambiar sin tocar `facturas.py` (la puerta única `texto_del_documento` ya está separada); una
fuente de meteo se puede cambiar guardando de nuevo su `fuente` y su `licencia`.

**Lo que NO se ha hecho, a propósito**: no se ha contratado nada, no se ha pagado nada y **no se ha
medido la precisión del OCR** con facturas de verdad, porque el corpus aún no existe. **D08 no queda
cerrado por esta decisión**: queda elegido el camino y medido el coste.

**Comprobado (2026-11-04)**
- Las cifras y licencias con URL y fecha en el documento, y **verificadas de forma independiente** por
  un revisor aparte (ver el registro del apartado 7 del documento).
- `pytest` y `node --test` sobre este HEAD: se anotan en `ESTADO-AGENTE.md` con el número medido.

## 2026-11-04 (noche) · Decisión de coordinación: **el corpus de D08 queda aparcado**

**Decisión de David, no del agente**: no va a aportar ahora las 30 facturas con permiso escrito, así
que el corpus queda **aparcado** hasta que lo traiga. Está escrito en
[`ESPECIFICACION.md`](ESPECIFICACION.md).

**Qué cambia**: **D08 no bloquea nada más**. El trabajo hecho —las dos opciones de cada decisión
(corpus, OCR, meteo/satélite), medidas con coste, licencia y límite, todas con la opción de 0 €
elegida— **se queda como está** en [`docs/D08_CORPUS_Y_PROVEEDOR.md`](docs/D08_CORPUS_Y_PROVEEDOR.md)
y sirve cuando llegue el corpus. No se busca otro corpus ni se mide el OCR.

**Qué no cambia**: nada de lo ya decidido en D08, ni el `.env`, ni las fixtures, ni el estado del
programa. La prioridad pasa a ser la aplicación del agricultor (`ALCANCE-AGRICOLA.md`).
