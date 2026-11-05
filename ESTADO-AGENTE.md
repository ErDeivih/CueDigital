titulo: CueDigital — la herramienta del agricultor de Castilla y León
resumen: CueDigital ya deja meter tierras por su código o eligiéndolas en una ventana del SIGPAC con la parcela resaltada, importar el cuaderno de un cliente sin teclear nada (reconoce las parcelas y rellena la finca), ver el mapa coloreado con la ficha al clicar, y enseña en «Hoy» qué falta para el cuaderno, los gastos y las ventas. La conexión bancaria PSD2 (solo lectura) está investigada con dos agregadores, pero parada: ninguno publica precio y hay que pedir presupuestos. Siguen pendientes la PAC de años anteriores y las pantallas propias de gastos y facturas.
estado: en-curso
tarea: implementada la segunda entrega de la app nueva (tierras SIGPAC, importar el cuaderno, mapa coloreado, gastos/ventas y qué falta) e investigada la conexión bancaria
nivel: 2
siguiente: cargar la PAC y los registros de años anteriores, y las pantallas propias de gastos e ingresos y de facturas; pedir los dos presupuestos de PSD2
bloqueado: PSD2 queda a la espera de que David apruebe el gasto (precios no publicados, nivel 3); y siguen pendientes de terceros las licencias (CIT, IGN), los formatos del expediente y del Cuecyl antiguo
fecha: 2026-11-05

## Lo que se ha hecho en esta segunda entrega

La lista de David está copiada en `WALL.md`, casilla por casilla, con la evidencia al lado. Estado:

1. **Tierras (lo primero de su lista) — HECHO**. En `/nuevo/` → «Mis parcelas» → «Añadir tierras»:
   - por la **referencia del SIGPAC** (o los siete números), «Buscar» trae los recintos con
     superficie, uso, pendiente y dibujo, se marcan y se añaden en bloque;
   - la **ventana del SIGPAC** abre la ortofoto en la zona de los recintos y **dibuja cada uno
     resaltado con su color y su etiqueta** (el servidor manda ahora sus puntos); el clic en el mapa
     sirve para elegir y añadir;
   - la tierra se ve **catalogada** (uso, coeficiente, región, admisibilidad) y se puede **editar
     nombre y superficie**; lo del SIGPAC se muestra y no se toca.
2. **Importar el cuaderno de un cliente — HECHO**. Se sube el Cuecyl `.xlsx` y el programa **reconoce
   cada referencia SIGPAC, crea las tierras que faltan sin duplicar** y **rellena el titular de la
   finca** (nombre, NIF, registro, dirección…). Verificado subiendo el cuaderno de ejemplo en Chrome:
   la lista pasa de 65 a 72 tierras. El **municipio no se rellena** a propósito: el cuaderno no lo
   trae y deducirlo del nombre de la localidad sería inventar.
3. **Mapa del cliente — HECHO**. Coloreado por uso o cultivo, con leyenda de palabra + color, y clic
   en la parcela (o en la fila) para ver su ficha y sus otros años.
4. **Leer facturas (OCR) — CONFIRMADO**. Ya estaba: `app/facturas.py` + `app/ocr.py` leen PDF, escaneo
   y foto y devuelven una propuesta que el agricultor revisa. La precisión sobre facturas reales sigue
   sin medir (el corpus está aparcado por decisión de David); en «Hoy» se ve el número de facturas.
5. **Gastos e ingresos — HECHO en «Hoy»**. Tarjetas con gastos (total y pendiente) y ventas (total,
   cobrado y pendiente), con las cuentas del servidor y sin mezclar importes que no son comparables.
   El alta y el detalle siguen en la app vieja.
6. **PSD2 solo lectura — INVESTIGADO Y PARADO (nivel 3)**. `docs/PSD2-AGREGADORES.md`: la vía correcta
   es contratar un AISP autorizado (no sacar licencia); hay 5+ candidatos con API de solo lectura,
   sandbox y consentimiento en el banco. **Ninguno publica precio** (mínimo mensual + presupuesto), así
   que no se puede elegir «la más barata»: hay que pedir dos presupuestos y que David apruebe el gasto.
   **No se ha escrito código de PSD2**: sin contrato no entra.
7. **Cuaderno guiado — HECHO**. En «Hoy», bloque «falta para el cuaderno» con el número, **qué falta**
   y **dónde se arregla**, sacado de lo que hay apuntado de verdad.

**La app vieja sigue viva en `/`** y sus 27 pantallas funcionan; el armazón nuevo enlaza a ella en lo
que aún no está migrado, así que no hay ningún recorrido roto.

## La última pasada, sobre este mismo HEAD

    Python       5766 recogidas · 5764 superadas, 2 omitidas, 0 fallos
    JavaScript   1256 superadas, 0 fallos
    armazón nuevo en Chrome a 390/1024/1440 y el alta/importación      0 fallos
    capturas                                            8 en docs/capturas-nuevo/

## Lo que sigue abierto

- **PAC y registros de años anteriores**: importar los **recintos por campaña de la Junta**
  (canal verificado 2023–2026) y la PAC de esos años; crear la explotación desde el fichero. No hay
  fichero oficial de la solicitud PAC: la vía es la app de la Junta con certificado.
- **Pantallas propias** de gastos e ingresos y de facturas en `/nuevo/` (hoy son tarjetas y enlaces a
  la app vieja), y el cuaderno guiado del día a día (apuntar en 30 segundos).
- **PSD2**: dos presupuestos y aprobación del gasto; después, conectar cuentas en modo solo lectura.
- **Pendiente de terceros**: licencia del SHP de CyL (CIT) y de la ortofoto PNOA (IGN); formato de
  «Documentos del expediente» y del Cuecyl de años anteriores; valores de los catálogos oficiales.
- Límites respetados: **no se ha tocado el `.env` ni las fixtures de firma**, no se ha abierto ni
  cambiado de rama y no se usa GitHub Actions. Push selectivo al final de la sesión.
