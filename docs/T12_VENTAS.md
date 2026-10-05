# T12 — Entregas, ventas, importes decimales y cobros parciales (E6); A06/A08

> **Contrato:** `docs/CONTRATO_IMPLEMENTACION_CRM.md`, línea 369: «T12 / E6 | Dependencia: T09, T11 |
> Entregas/ventas, importes decimales, cobros parciales; A06/A08». Pantalla **S12** (§4, línea 234) y los
> casos **A06** y **A08** (§6).
>
> **Lo que pedía el encargo, y dónde se contesta aquí:** separar lote cosechado / entrega / factura / cobro
> (§3.1), la tabla del contrato con su pie (§3.2), agrupar sin duplicar ingresos (§3.3), devoluciones y
> ajustes con evidencia y origen (§3.4), el histórico sin precio que no se convierte en cero (§3.5), el
> dinero sin perder céntimos (§3.6), y **que la emisión fiscal no se activa aquí** (§3.7).

---

## 1. Qué se puede hacer ahora (una línea por cosa)

1. **Apuntar una entrega** con su producto, sus kilos, su comprador y su albarán, **con o sin precio**: es
   la tabla `ventas_de_cosecha` de siempre, que no se ha duplicado.
2. **Ponerle el importe después** (`#/ventas/<id>/importe`): o el importe del papel, o el precio por kilo
   (y el programa calcula, redondeando **una sola vez** al final), más el vencimiento y **de qué cosecha
   salió** — el «lote cosechado» del contrato, que ya existía como la labor de tipo cosecha.
3. **Ver la tabla de S12** (`#/ventas`) con las **ocho columnas del contrato** —cliente, producto, fecha,
   cantidad, importe conocido, vencimiento, cobrado y pendiente— más el estado con su palabra, la partida,
   el albarán y de dónde salió; con **buscador**, dos filtros («solo lo que falta por cobrar» y «solo lo
   que no tiene importe»), orden por cualquier columna **hecho en el servidor** y **pie del conjunto
   filtrado** calculado por el servidor.
4. **Apuntar una devolución o un ajuste** de peso, humedad o calidad (`#/ventas/<id>/ajuste`): tipo,
   kilos y euros **con signo**, **origen** (cliente, báscula, laboratorio, acuerdo u otro) y **motivo**
   obligatorios; el papel (la foto del básculero, el boletín) se sube y va a disco; si no lo hay, se dice.
5. **Hacer la factura nuestra** (`#/ventas/facturas`): juntar una o varias entregas en un documento de
   gestión, con su número, su fecha, su vencimiento, su cliente y sus notas.
6. **Juntar entregas sin duplicar nada** (`#/ventas/facturar`): las que ya están en una factura salen con
   su aviso y no se pueden marcar; una entrega viva no puede estar en dos facturas vivas (lo impide un
   índice único en la base).
7. **Ver la ficha de la factura** (`#/ventas/facturas/<id>`): lo que va dentro (con la fotografía del día
   que se emitió), lo que te han pagado y lo que queda; y **la diferencia observada** si una entrega se
   corrigió después.
8. **Apuntar un cobro parcial** (`#/ventas/cobros/nuevo`): puede ser una parte, puede ir contra una
   factura o quedarse **sin asignar** hasta saber de cuál es, y admite forma, referencia y notas.
9. **Conciliar y deshacer** un cobro (`#/ventas/cobros`): decir de qué factura es o quitarle la
   asignación, **sin borrar el movimiento** ni el dinero.
10. **Anular con motivo y sin borrar**: una entrega (si no está facturada), una factura (si no tiene
    cobros; al anularla sus entregas quedan libres para rehacerla), un ajuste (el papel se queda en disco)
    y un cobro (la factura vuelve a deber lo que debía).
11. **Cuentas que cuadran por construcción**: el total de una factura **es** la suma de sus líneas; lo
    cobrado de una factura se reparte entre sus entregas **por orden** (la más antigua primero), de modo
    que **la suma de las filas es exactamente el pie**; y el resumen del año dice lo mismo que la tabla.
12. **Reenviar sin duplicar**: la misma entrega, el mismo ajuste, la misma factura y el mismo cobro,
    mandados dos veces (el móvil sin cobertura), devuelven **lo que ya había** y no crean otro.
13. **Aislamiento entre fincas** en las cuatro puertas nuevas: ver, cobrar contra, enlazar un ajuste y
    anular contestan **404** (no 403) con lo de otra explotación.

---

## 2. Ficheros

### Nuevos

| Fichero | Qué es |
|---|---|
| `backend/app/dinero.py` | El dinero: `Decimal` en el programa y **texto decimal canónico** en la base, redondeo al céntimo **hacia arriba** cuando sobra medio, lectura de un importe escrito a mano («1.234,56», «0,235»), formato español y el tipo de columna (`Dinero`, `Precio`). Rechaza los `float` a la cara. |
| `backend/app/ventas.py` | La lógica pura del dinero: los seis estados de una entrega, el importe con los ajustes aplicados, lo pendiente (nunca negativo), el reparto de un cobro entre las entregas de una factura, las listas cerradas de tipos de ajuste, orígenes y formas de cobro, y la cuenta que suma un conjunto de filas. |
| `backend/tests/test_el_dinero_de_las_ventas.py` | **63 pruebas nuevas**: los dos casos de aceptación, los números que fallarían con coma flotante, el reenvío, el aislamiento, el pie que cuadra con el detalle, los ajustes con origen y evidencia, el esquema, el rastro del cobro y la decisión de no activar la emisión fiscal. **Y dos más de la revisión (§10)**: el guardián de anchos y el viaje del importe por la base **en los dos motores** |
| `backend/web/react/pantallas/facturas_emitidas.js` | La lista de las facturas nuestras. |
| `backend/web/react/pantallas/facturar_entregas.js` | Juntar entregas en una factura (y las que ya están, dichas). |
| `backend/web/react/pantallas/factura_emitida.js` | La ficha: lo que va dentro, los pagos y lo que queda. |
| `backend/web/react/pantallas/venta_importe.js` | Poner el importe, el precio, el vencimiento y la cosecha de la que salió. |
| `backend/web/react/pantallas/venta_ajuste.js` | La devolución y los ajustes, con su origen y su papel. |
| `backend/web/react/pantallas/cobros.js` | La lista de lo que me han pagado, con lo que está sin asignar aparte. |
| `backend/web/react/pantallas/cobro_nuevo.js` | Apuntar un cobro (parcial o entero, con factura o sin ella). |
| `backend/web/react/piezas/campo_de_un_importe.js` | Las piezas compartidas por las cuatro pantallas que se rellenan: el campo, la lista de botones para elegir y **el aviso de que la factura no es un documento con validez oficial**. |

> **Siete pantallas, siete ficheros**, y no es una manía: `tests/test_la_migracion_a_react.py` exige que
> cada clave de `PANTALLAS_EN_REACT` tenga su fichero en `web/react/pantallas/` y que estén todos en la
> caché del campo. Un fichero con varias pantallas deja esa cuenta descuadrada y, sobre todo, deja pantallas
> que no se guardan para abrir sin cobertura.

### Tocados

> **La ronda de la revisión independiente (§10) ha vuelto a tocar varios de estos ficheros**: `dinero.py`,
> `schemas.py`, `textos.py`, `routers/ventas_api.py`, `web/app.js`, cuatro de las pantallas nuevas y los dos
> ficheros de pruebas. La tabla de §10.1 dice, defecto por defecto, qué se le hizo a cada uno.

| Fichero | Qué se le ha hecho |
|---|---|
| `backend/app/models.py` | **Columnas nuevas en `ventas_de_cosecha`** (`contacto_id`, `cosecha_id`, `importe`, `precio_unitario`, `vencimiento`, `clave_de_reenvio`) y su índice único parcial de reenvío; y **cuatro tablas nuevas**: `facturas_emitidas`, `lineas_de_factura_emitida`, `cobros` y `ajustes_de_entrega`. Las columnas de dinero son de tipo `dinero.Dinero`/`Precio`, no `Float`. |
| `backend/app/schemas.py` | La entrada y la salida de la entrega con el dinero; y los esquemas de la factura nuestra, sus líneas, los cobros, los ajustes y la tabla de S12. Los importes se declaran `Decimal` y **un validador rechaza los `float`**. |
| `backend/app/textos.py` | El vocabulario nuevo en `VENTA` (la tabla, el dinero, los estados, los ajustes) y dos diccionarios nuevos, `FACTURA_EMITIDA` y `COBRO`; los mensajes `D1`–`D11`; y **el aviso `dinero_fuera` cambia** (ver §3.6). Todos entran en `textos_visibles()`, así que pasan el test de jerga. |
| `backend/app/routers/ventas_api.py` | El grueso: la entrega con idempotencia y cuentas, la tabla de S12 con su pie, los ajustes (con su papel), la factura nuestra (crear, ver, anular) y los cobros (apuntar, conciliar, anular). Nada de esto emite un documento fiscal. |
| `backend/app/routers/interfaz.py` | Sirve `factura_emitida`, `cobro`, `tipos_de_ajuste` y `origenes_de_un_ajuste` con el resto del vocabulario (esto se guarda en el móvil: una pantalla sin cobertura tiene que tener sus palabras). |
| `backend/app/routers/explotacion.py` | `FacturaEmitida` entra en `OTRAS_COSAS` (la prueba que exige que toda tabla que cuelga del año esté clasificada avisó de que había que decidirlo). |
| `backend/app/routers/registros.py` | **Una comprobación que faltaba** al borrar una cosecha: si una entrega dice que salió de ella, no se borra y se dice cuántas la usan (§8.3). |
| `backend/web/app.js` | El cableado de las siete pantallas nuevas, la tabla de S12 preparada a mano, la carga del dinero en el arranque, las rutas y las acciones (`venta-importe`, `venta-ajuste`, `facturas-emitidas-ver`, `cobros-ver`…), y —esto es importante— **el borrador de una venta devuelve los cuatro campos del dinero** al corregirla, para no borrárselos (§8.4). |
| `backend/web/react/pantallas/ventas.js` | Se reescribe: de lista de tarjetas a **tabla del contrato** en el ordenador y tarjetas en el móvil, con su barra de buscar y filtrar, su pie, sus avisos y las acciones de cada entrega. |
| `backend/web/react/pantallas/cobros.js` | Se reescribe con el contenido del T12 (la lista de cobros), porque el fichero llevaba las cuatro pantallas del dinero y ahora hay una por fichero. |
| `backend/web/react/rutas.js` | Siete direcciones nuevas (`#/ventas/facturas`, `#/ventas/facturas/:id`, `#/ventas/facturar`, `#/ventas/cobros`, `#/ventas/cobros/nuevo`, `#/ventas/:id/importe`, `#/ventas/:id/ajuste`), con los tramos fijos delante de los identificadores. |
| `backend/web/service-worker.js` | Los ocho ficheros nuevos en la caché del campo y **la caché sube a `2026-10-03-67`** (con su explicación). |
| `backend/tests/test_contactos.py` | **Con su motivo escrito**: la base de prueba del T11 tiraba las tres tablas de contactos **antes** de apuntar las ventas, y desde el T12 `ventas_de_cosecha.contacto_id` apunta a `contactos`: SQLite no deja escribir en una tabla cuyo padre no existe, ni con el valor nulo. El orden se invierte (se apuntan las ventas y después se tiran las tablas), que deja el mismo estado —el que se encuentra el guion de migración— sin construir uno imposible. |
| `backend/tests/test_analisis_ventas_planes_y_campanas.py` | **Con su motivo escrito**: las dos pruebas que fijaban el esquema de entonces. La de las tablas del año pasa de doce a trece (`facturas_emitidas`), y la que exigía que **nada** apuntara a una venta pasa a exigir que apunten **las dos que el T12 le ha colgado** —era una prueba que se puso justo para este día: «si una tabla nueva apunta a una venta, esto avisa y obliga a decidir»—. |
| `backend/tests/test_cosecha_comercializada.py` | **Con su motivo escrito**: la prueba `test_no_hay_precio_ni_importe` se convierte en la del **A08** (sin precio, el importe es «no se sabe» y no cero) y la del texto de la pantalla se actualiza porque el aviso viejo («aquí no se apunta el precio») es mentira desde este ticket. No se ha borrado ninguna garantía: la que había (un hueco no es un cero) es la que se sigue comprobando. |
| `backend/tests_js/react.test.js` | **Con su motivo escrito**: las pruebas de la pantalla de ventas se rehacen contra la tabla nueva (columnas del contrato, pie del servidor, filtros, avisos del A08, acciones de cada entrega, ninguna frase a mano). |
| `backend/tests_js/interfaz.test.js` | El cableado de la pantalla de ventas (le llega la tabla **ya preparada**, con el pie del servidor) y un `asistente-saltar` menos, porque el asistente de la venta vuelve a tener los nueve pasos de antes (§3.8). **Y en la ronda de la revisión (§10), cinco pruebas nuevas** que pulsan las treinta acciones del dinero y miran lo que llega al servidor |
| `backend/tests_js/rutas.test.js` | Las siete pantallas nuevas en la tabla del enrutador, con su motivo. |

### Lo que **no** se ha tocado

`backend/cuedigital.db` (ni abrirla), `backend/scripts/humo.py`, `backend/scripts/comprobar_en_un_navegador.py`
(pasados tal cual, sin editarlos), `backend/tests/conftest.py`, `backend/tests/test_revision_t11.py`,
`docs/REVISION_T11.md`, `docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md`, `README.md`, `AGENTS.md`,
`docs/LO_QUE_PIDE_LA_JUNTA.md` y **`docs/REACT.md`** (ver §7: hace falta que lo alinee el coordinador, y por
eso hay dos pruebas en rojo que no se pueden arreglar desde aquí).

---

## 3. Las decisiones que hay que entender antes de tocar esto

### 3.1. Las cuatro cosas separadas, y por qué el «lote cosechado» **no** es una tabla nueva

El contrato empieza así: «Separar lote cosechado, entrega/albarán, factura emitida y cobro». Las cuatro
existen y son cuatro sitios distintos:

| Qué es | Dónde vive | Por qué |
|---|---|---|
| **El lote cosechado** | la labor de tipo cosecha (`/api/cosecha`), **la que ya existía** | El programa ya guarda qué se recogió, de qué producto y de qué tierra, con su cantidad. **Duplicarla habría sido tener dos listas de lo mismo**, que es el fallo que este proyecto más veces ha pagado. Lo que se ha añadido es el enlace: `VentaDeCosecha.cosecha_id`. |
| **La entrega (el albarán)** | `ventas_de_cosecha`, **la tabla de siempre** | Ya tenía el comprador, los kilos, la fecha y el número de albarán. Lo que le faltaba era el dinero, el vencimiento, la ficha del cliente y el enlace con la cosecha. |
| **La factura emitida** | `facturas_emitidas` (+ `lineas_de_factura_emitida`) | Es un documento **nuestro**, de gestión, que puede agrupar varias entregas y llegar semanas después. |
| **El cobro** | `cobros` | Es dinero que entra, y puede ser **una parte**. Es el único de los cuatro que es dinero cobrado en vez de dinero prometido. |

**El nombre «venta» se conserva para la entrega**, aunque el contrato hable de «entrega/albarán»: ya está en
las rutas, los textos, los papeles y las pruebas, y renombrarlo obligaría a migrar todo eso para no decir
nada nuevo. Está escrito en el modelo, con el motivo.

### 3.2. El dinero no se guarda como número, y no es una precaución de adorno

`app/dinero.py` guarda los importes como **texto decimal canónico** (`"121.00"`) y trabaja con
`decimal.Decimal`. Tres motivos, los tres medidos:

1. **En coma flotante, `0,10 + 0,20` no es `0,30`** (es `0,30000000000000004`). Con dos apuntes no se ve; con
   un año de entregas, el total de la pantalla y la suma de las filas dejan de coincidir por unos céntimos.
2. **SQLite no tiene un tipo decimal.** Un `Numeric` de SQLAlchemy allí acaba pasando por `float` (el
   dialecto lo dice: `supports_native_decimal = False`), o sea el mismo problema metido dentro del motor.
   Hay una prueba que mira con SQL en crudo que la columna guarda **texto** (`typeof(importe) == 'text'`).
3. **El redondeo por defecto de Python es «al par»**, y quien cuadra una cuenta a mano redondea al alza:
   aquí se usa `ROUND_HALF_UP`, y hay pruebas con `0,125`, `0,135` y `80,999` (que da `81,00`, no `80,99`).

Y una consecuencia del oficio: **el precio se guarda con las cifras que se pactaron** (`0,2350 €/kg`) y lo
único que se redondea es el **importe**, una sola vez, al final. Redondear el precio antes de multiplicar
por 42.000 kg daría 210 € de diferencia en una sola entrega, y en el sentido que perjudica al agricultor.
Hay una prueba que mide exactamente eso.

### 3.3. El dinero se cuenta una vez, y por eso está en el esquema y no en un comentario

Las tres puertas por las que un programa de cuentas duplica ingresos, cerradas:

1. **Agrupar entregas en una factura.** El importe de la factura **es la suma de sus líneas** (no hay una
   columna de total que se pueda escribir a mano y solapar), y una entrega viva solo puede estar en **una**
   factura viva: lo impide un **índice único parcial** (`uq_linea_de_factura_por_entrega`), no una
   comprobación amable que se puede olvidar.
2. **Reenviar la misma petición.** Cada una de las cuatro cosas lleva su **clave de reenvío**, con índice
   único parcial (entre los vivos, para que una anulada deje libre la clave). Reenviar devuelve lo que ya
   había, y el caso del cobro además lo **dice** (`ya_estaba`).
3. **Cobrar.** Un cobro se imputa a **una** factura y con **una** cantidad (`importe_imputado`), y lo que
   sobra queda «sin conciliar» con su cifra. Un pendiente **nunca es negativo**.

Y la pieza que hace que **el pie cuadre con las filas**: como una factura puede llevar varias entregas, el
dinero cobrado se reparte **por orden (la más antigua primero)** con `ventas.reparto_de_lo_cobrado`. Con el
importe repetido en cada fila (lo fácil), la suma daría el doble en una factura de dos entregas; con un
reparto por porcentaje, el programa se inventaría céntimos. Está probado con una factura de dos entregas y
un pago parcial.

### 3.4. Un ajuste que cambia el importe tiene que decir de dónde sale

Lo pide el contrato («con evidencia y origen») y es lo que impide el número suelto. Se exigen tres cosas:
**tipo** (devolución, peso, humedad o calidad), **origen** (cliente, báscula, laboratorio, acuerdo u otro) y
**motivo**. Las dos primeras son listas **cerradas** y la tercera es su frase. Además, un ajuste tiene que
**cambiar algo** (kilos o euros): uno que no ajusta nada no se apunta, y se dice por qué.

El **papel es opcional y se dice cuando no lo hay** («sin papel adjunto»): en el campo hay veces que el
boletín llega después, y bloquear el apunte por eso sería impedir apuntar lo que de verdad pasó. El fichero
va a disco con la ruta que pone el programa (nunca el nombre que manda el navegador), y hay una prueba que
lo comprueba **mirando el disco**.

### 3.5. Lo que no se sabe no se convierte en cero (A08)

Una entrega sin precio tiene el importe en `None`, no en `0.00`, y el estado es `sin_importe`. El pie de la
tabla dice **cuántas entregas no entran en la cuenta** («A 1 entrega le falta el importe, así que no entra
en estas cuentas»): un total que suma lo que hay y calla que le faltan importes parece que cuadra, y no
cuadra. Y **una entrega sin importe no se puede facturar**: se dice por qué y qué hacer (ponerle el importe),
no se deja al agricultor sin salida.

### 3.6. El aviso de la pantalla de ventas cambia, y con él una prueba

El texto decía: «Aquí no se apunta el precio ni lo que te han pagado. Lo que pide la ley de esta sección es
qué, cuánto y cuándo; las cuentas van aparte». Era verdad y era una decisión mientras el programa no llevaba
cuentas; **desde el T12 es mentira**, y dejar el texto viejo sería decirle al agricultor que no puede hacer
algo que sí puede. El nuevo dice dónde está el dinero y añade la mitad que no se puede quitar nunca: **la
factura que se hace desde esta pantalla es su cuenta de gestión, no un documento con validez oficial**. Las
dos pruebas que fijaban el texto viejo y la ausencia de importe se han actualizado **con el motivo escrito**
y comprobando lo que de aquellas decisiones sigue siendo sagrado (el hueco no es un cero).

### 3.7. Lo que se entrega **no** es una factura fiscal, y hay pruebas que lo impiden

El contrato lo dice con estas palabras: «La emisión fiscal completa requiere especificación normativa propia
antes de activarse como tal». Aquí no se ha activado:

- **Ni un impuesto**: la factura no tiene base imponible, ni cuota, ni tipo; su total **es la suma de lo
  entregado**.
- **Ni una palabra de ley en pantalla**: hay una prueba que recorre **todos** los textos de `VENTA`,
  `FACTURA_EMITIDA` y `COBRO` y falla si aparece «IVA», «Verifactu», «impuesto», «Hacienda» o «ley».
- **Ni una ruta que prometa un documento fiscal**: se mira lo que la aplicación **publica** en su esquema.
- Y **el aviso de que no es un documento con validez oficial se pinta en las tres pantallas de la factura**,
  desde una pieza con nombre propio (`AvisoNoOficial`) para que no se pueda quitar de una sin que se note.

### 3.8. El asistente de la venta **no** pregunta el dinero, y es una decisión medida

Se probó a meterlo (tres preguntas más: importe, precio, vencimiento, más la cosecha) y **se quitó** al
comprobar lo que costaba: el asistente es el recorrido **del campo** —«qué saqué, cuánto, cuándo y a
quién»— y el dinero se apunta después, en su pantalla, que es donde el caso A08 tiene sentido (una entrega
se apunta **sin precio** el día que sale de la finca y el importe se sabe cuando llega el papel del
comprador, que puede ser tres días después). Dos consecuencias que se han cuidado:

- **Los cuatro campos tienen su puerta** en la pantalla del importe (importe, precio, vencimiento y de qué
  cosecha salió): un campo del modelo sin pantalla que lo pregunte es el fallo que este proyecto ha pagado
  más veces.
- **Al corregir una venta no se le borra el dinero**: el borrador del asistente devuelve los cuatro campos
  del dinero aunque el asistente no los pregunte, porque el `PUT` es el mismo para el alta y para la
  corrección y lo que no viaja se queda en blanco. Es el mismo fallo que ya se documentó con la máquina al
  cosechar y con la portada del cuaderno, y hay una prueba que lo ata.

### 3.9. El orden de las columnas y el ancho: medido, no supuesto

La tabla de S12 se mira en un ordenador con ocho columnas y cuatro más opcionales, y sus acciones en la
última celda. **Desde la revisión (§10.1, defecto 5) esa última columna lleva su cabecera propia
(«Acciones», `textos.VENTA["tabla_acciones"]`)**: antes el rótulo de «De dónde» caía encima de los botones y
el valor de esa columna no se pintaba en el ordenador. Medido en un navegador de verdad: **a 1.024 px la
página entera medía 2.488 px de ancho** (la tabla empujaba la pantalla) y a 390 px también se salía. Está
arreglado metiendo la tabla en el contenedor de desplazamiento que ya existía para esto (`.tabla-scroll`):
ahora la tabla se desplaza dentro de su caja y el resto de la pantalla se queda quieta. Medido después:
**las siete pantallas caben a 390, 1.024 y 1.440 px**, y el orden de las columnas es el del contrato.

---

## 4. Lo que **no** se ha hecho, y por qué

1. **La emisión fiscal completa** (§3.7). No se ha hecho **a propósito**: el contrato dice que necesita
   especificación normativa propia, y aquí no hay ni impuestos ni numeración oficial. Lo que se entrega es
   la cuenta de gestión.
2. **La conciliación muchos a muchos** (un ingreso que salda tres facturas): es el ticket **T20** (S14). Lo
   que hay es un cobro → una factura, con su sobrante dicho aparte, y deshacer la asignación sin borrar el
   movimiento.
3. **La importación de extractos bancarios**: T20. Los cobros se apuntan a mano, con su referencia del
   banco guardada como texto.
4. **La factura electrónica y el envío telemático**: no es de este ticket y no se ha rozado.
5. **El papel del ajuste no se puede subir desde la pantalla** (solo desde la API,
   `POST /api/ventas/{id}/ajustes/{ajuste_id}/papel`): subir un fichero desde el navegador necesita el
   mismo camino de `FormData` que un boletín, y se ha preferido dejarlo dicho antes que entregar un botón a
   medias. **Es lo primero que se añadiría en la siguiente ronda.**
6. **La devolución no devuelve stock a ningún almacén**: la cosecha no está en el almacén (el almacén es de
   lo que se compra: T09). Una devolución de grano no tiene dónde volver, y decirlo es la verdad.
7. **No hay pantalla para «lote cosechado»**: la cosecha se apunta en su sitio (`/api/cosecha`, con su paso
   del asistente) y la entrega se enlaza desde la pantalla del importe. No se ha duplicado la pantalla de la
   cosecha.

---

## 5. Las pruebas, y lo que se midió

### Python

```
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests -q --junit-xml=$env:TEMP\t12.xml
```

- **3.818 pruebas recogidas y ejecutadas** (el `tests="3818"` del XML de `pytest` y el `3818` del mensaje
  del recuento; eran 3.793 antes de la ronda de la revisión, §10).
- **2 en rojo**, y los dos son recuentos de documentación que alinea el coordinador (§10.3):
  `test_el_numero_de_pruebas_de_python_es_el_de_verdad` y
  `test_los_numeros_de_test_de_la_documentacion_no_se_quedan_viejos`. (Los otros dos que salían en la
  primera entrega —`test_la_documentacion_dice_lo_mismo_que_el_codigo` y
  `test_el_informe_de_la_migracion_se_puede_contar`— **ya están en verde**: los alineó el coordinador.)
- **Ninguna otra**, y en particular pasan: el test de jerga, el de los ficheros de texto (codificación),
  el de la migración a React (ficheros y caché), el de los textos que existen, el de los botones, las doce
  pruebas de la revisión (§10) y las pruebas de los tickets anteriores (T05, T06, T09, T10, T11) **sin
  relajar ninguna**. Y las dos pruebas nuevas del guardián de anchos
  (`TestLoQueSeAceptaCabeDondeSeGuarda`): la que exige que **cada campo de texto del dinero declare el ancho
  de su columna, leído del modelo**, y la que exige que el importe más grande que se acepta **quepa** en la
  columna del dinero.

### JavaScript

```
node --test "tests_js/*.test.js"
```

**874 pruebas, 0 fallos** (la documentación dice 867; §10.3). Las nuevas de la primera entrega: la tabla con
las columnas del contrato y el pie del servidor, los avisos del A08, las acciones de cada entrega, la barra
de buscar y los dos filtros, el estado vacío contra el filtrado, el aviso de que la factura no es oficial, y
que **no hay ni una frase escrita a mano** en el componente. Y las **cinco de la revisión** (§10.1, defecto
7): las que **pulsan las treinta acciones del dinero** —una por una, mirando qué método, qué ruta y qué
cuerpo llegan al servidor— y que encontraron el defecto del número 13 (§10.2).

### El recorrido contra un servidor aislado

Servidor levantado **en el puerto 8132** (no el 8000, que es de David) con una base temporal **limpia** —el
guion exige una base nueva: con datos de una pasada anterior, «se puede crear la campaña anterior» falla por
el entorno y no por el programa— y `CUEDIGITAL_CONFIAR_EN_CABECERAS=1`:

```
CUEDIGITAL_DATABASE_URL=sqlite:///$env:TEMP/t12_aislado/humo.db  CUEDIGITAL_ADJUNTOS=$env:TEMP/t12_aislado/adjuntos
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8132
```

- **`scripts/humo.py http://127.0.0.1:8132` → 483 líneas `[OK  ]` y 0 `[FALLO]`**, `RESULTADO: todo
  correcto`. El guion es del coordinador y **el número que él da de su sección del dinero es 478**: la
  diferencia (483 medidas por mí, contando las líneas de la salida) **no la he investigado** —puede venir de
  comprobaciones que solo se ejecutan según lo que conteste el servidor, o de contar de otra manera— y la
  dejo dicha en vez de dar por buena una de las dos.
  Y una nota de entorno, por si vuelve a pasar: sin `$env:PYTHONIOENCODING="utf-8"` el guion **revienta al
  imprimir** una flecha (`→`) porque la consola de Windows usa `cp1252`. Es del entorno, no del programa.
- **`scripts/comprobar_en_un_navegador.py http://127.0.0.1:8132` → 336 comprobaciones, 0 fallos**,
  `RESULTADO: la interfaz se abre y se dibuja en un navegador de verdad` (36 de sus líneas son de las
  pantallas del dinero, y el número coincide con el que da el coordinador). Los dos guiones **sin editarlos**.

### Mis pantallas a 390, 1024 y 1440 px

Guion propio, temporal (no vive en el repositorio): importa del guion del coordinador las funciones que
hacen el hueco del ancho exacto (`pagina_estrecha`), abren el navegador (`abre`) y leen lo medido, **sin
tocar su fichero**. Comprueba dos cosas separadas, porque el volcado del navegador no baja dentro de un
hueco: los **textos** con `pagina_de_pantalla` (la pantalla de verdad, recorriendo la ruta **pulsando**) y
el **ancho** con `pagina_estrecha`.

```
RESULTADO: las 7 pantallas del dinero se dibujan y caben a 390, 1024 y 1440 px
  [OK] el orden de las columnas de la tabla es el del contrato:
       ['cliente','producto','fecha','cantidad','importe','vencimiento','cobrado','pendiente']
```

21 mediciones de ancho (7 pantallas × 3 anchos), todas con «se ha medido en un hueco de N px de verdad»,
«la aplicación está montada» (más de 2.000 caracteres) y **sin salirse**.

### Los dos casos de aceptación, con sus números

**A06** — «Factura 121 EUR, pago 40 EUR → pendiente 81; un segundo importe conciliado no crea una segunda
factura»: `test_un_pago_de_40_deja_81_pendientes` (121,00 − 40,00 = **81,00** exactos, y el aviso lo dice con
las dos cifras) y `test_un_segundo_importe_conciliado_no_crea_una_segunda_factura` (se cuentan las facturas
**antes y después** de cobrar los 81 que faltaban: hay **una**).

**A08** — «Venta con 8.000 kg y sin precio → cantidad conocida, importe pendiente; no ingreso cero»:
`test_la_cantidad_se_sabe_y_el_importe_no` (cantidad 8.000,00 kg, importe `None`, estado `sin_importe`,
`texto_importe` vacío) y `test_no_aparece_como_ingreso_de_cero_euros` (el resumen dice que a 1 entrega le
falta el importe, y la fila deja el importe **vacío**, no «0,00 €»).

### El dinero, con números que fallarían si estuviera mal

| Cuenta | Resultado exigido | Qué fallaría con coma flotante |
|---|---|---|
| 0,10 + 0,20 | `0,30` | `0,30000000000000004` |
| 21 % sobre 121,00 | `25,41` | céntimos arrastrados |
| `80,999` redondeado al céntimo | `81,00` | `80,99` si se redondea al par |
| 0,125 y 0,135 al céntimo | `0,13` y `0,14` | `0,12` y `0,14` (regla al par) |
| 42.000 kg × 0,2350 €/kg | `9.870,00 €` | `10.080,00 €` si se redondea el precio antes |
| Guardar y leer «0.10» | vuelve «0.10» y en la base es **texto** | un `Numeric` de SQLite pasa por `float` |

Y la prueba que cierra el círculo: **la suma de dos entregas de 0,10 € y 0,20 € es 0,30 €** pasando por la
base y por la tabla (`/api/ventas/tabla`), no solo en la aritmética.

### El pie que cuadra con el detalle

Con datos representativos (cuatro entregas: una **sin importe**, una suelta, **dos agrupadas** en una
factura con un **pago parcial** de 5.000,00 € y una **devolución** de −100,00 €), la prueba suma **las
filas de la tabla** y compara con el pie, uno por uno:

```
importe   10.270,00 €   (4 entregas, 1 sin importe)
facturado  9.970,00 €
cobrado    5.000,00 €
pendiente  4.970,00 €
```

Y el reparto del pago entre las dos entregas de la factura: **5.000,00 € van a la más antigua** (que valía
9.770,00 €, quedando 4.770,00) y la otra sale con sus 200,00 pendientes: **4.770 + 200 = 4.970**, exacto. La
suma de la columna «cobrado» **es** lo cobrado, sin repetirse.

### Varias campañas

Los datos de verdad no son de un solo año, y la campaña es una dimensión que no se deduce del calendario
(contrato §2). Se prueba con **dos campañas** y una entrega en cada una: la tabla y el resumen del año que se
está llevando **solo** cuentan sus entregas (300,00 € de importe), y pidiendo el año anterior sale la suya
con su dinero (100,00 €), sin mezclarse en ninguno de los dos sentidos.

### Reenvío, anulación y aislamiento

- **Reenvío**: la misma entrega, el mismo ajuste, la misma factura y el mismo cobro, mandados dos veces →
  devuelven el mismo identificador y las listas tienen **una** fila (y el pendiente no se mueve: 81,00 y no
  41,00).
- **Anulación**: un cobro anulado devuelve la deuda (121,00 pendientes otra vez) y volver a apuntarlo deja
  **0,00** y no 81,00; una factura con cobros no se quita (409 y se dice qué hacer); una entrega facturada
  no se borra ni se anula (409, y el aviso dice **en qué factura está**).
- **Aislamiento**: otra finca recibe **404** al leer la entrega, al leer la factura, al cobrar contra ella,
  al enlazarle un ajuste, al anular un cobro suyo y al enlazar una cosecha; y sus tres listas salen vacías.

### Datos y bases de prueba

Todo se ha probado **contra bases temporales** (`CUEDIGITAL_DATABASE_URL` a una carpeta temporal, con
`engine.dialect.name == 'sqlite'` comprobado antes de escribir nada) y adjuntos temporales. La base del
agricultor (`backend/cuedigital.db`) **no se ha abierto, ni copiado, ni usado**. La puesta al día del
esquema se ha probado con una base «vieja» hecha a mano: las seis columnas nuevas de `ventas_de_cosecha` se
añaden solas y la fila que ya estaba **conserva sus datos y se queda con el importe en blanco** (que es
«no lo sé», no cero: las ventas históricas sin precio no se convierten en ingresos de cero).

---

## 6. Lo que no he podido comprobar

1. ~~**PostgreSQL.**~~ **Ya medido** (ronda de la revisión, §10.3): sobre una base propia
   (`cuedigital_t12_final`, creada para esto y comprobando antes que ninguna otra suite la usaba), las **77
   pruebas del T12** —las 12 de la revisión y las 65 del ticket— pasan con **0 fallos**, y el viaje de ida y
   vuelta del importe se comprueba allí con `pg_typeof` (sale `character varying`: la columna guarda
   **texto**). Lo que sigue sin medirse es **la suite entera** (3.818 pruebas) en PostgreSQL: el resto tiene
   sus propios casos de motor y no es de este ticket.
2. **La subida del papel de un ajuste desde la pantalla**: la API está probada (con la comprobación de que
   el nombre que manda el navegador **no** se usa como ruta, mirando el disco), pero **el botón no existe**
   todavía.
3. **El comportamiento con dos peticiones simultáneas** (dos pestañas a la vez guardando la misma entrega):
   la protección está en la base (índice único parcial), que es donde tiene que estar, pero no he montado
   una prueba de concurrencia real.
4. **La lectura del cuaderno en papel** (`/api/cuaderno/faltantes` y el volcado oficial) **no incluye el
   dinero**: el cuaderno de la Junta pide producto, cantidad y fecha; el importe no va ahí. No lo he tocado
   y no he comprobado si el volcado oficial (IUWS) quiere algo de esto: **es de otro ticket** (T19/T22) y lo
   digo para que no se dé por hecho.
5. **El filtro de la tabla no guarda su vista** al salir y volver (el contrato §3 pide «vistas guardadas»):
   la lista de S12 no está en `LISTADOS` de `rutas.js` ni en `ORDEN_DE_ENTRADA` de `app.js`, y añadirla
   obliga a tocar las dos tablas a la vez. Queda dicho.

---

## 7. Lo que hace falta de otros, y lo que se pide

Estas pruebas estaban **en rojo a propósito** y no se podían arreglar desde este ticket, porque lo que hay
que cambiar son documentos que no me toca tocar (los alinea el coordinador al cerrar, como en los tickets
anteriores). **De las cuatro, dos ya están en verde** (el coordinador alineó `docs/REACT.md` y el informe de
la migración) y **las dos de recuentos siguen en rojo**. Los números están **medidos después del último
cambio**:

| Prueba | Qué dice | Qué hay que poner |
|---|---|---|
| `test_el_numero_de_pruebas_de_python_es_el_de_verdad` | la documentación dice **3.700** y hay **3.818** | **3.818** en `README.md`, `AGENTS.md` y `docs/LO_QUE_PIDE_LA_JUNTA.md` |
| `test_los_numeros_de_test_de_la_documentacion_no_se_quedan_viejos` | la documentación dice **867** de JavaScript y hay **874** | **874** en los tres |
| `test_la_documentacion_dice_lo_mismo_que_el_codigo` | `docs/REACT.md` no marca como migradas siete pantallas: `facturas_emitidas`, `facturar_entregas`, `factura_emitida`, `venta_importe`, `venta_ajuste`, `cobros`, `cobro_nuevo` | siete filas nuevas en su tabla, con «✅ En React» y su `pantallas/<nombre>.js` — **ya alineado por el coordinador: está en verde** |
| `test_el_informe_de_la_migracion_se_puede_contar` | las cuentas no cuadraban: `{"migradas": 48, "con_fichero": 48, "en_la_guia": 41, "en_la_cache": 48}` | lo mismo: la guía tiene que llevar las siete filas — **ya alineado: está en verde (48 pantallas, siete filas nuevas)** |

> **Nota, para que no se lea como un descuido:** al empezar este ticket el mismo guardián ya decía que había
> **3.704** pruebas de Python y la documentación decía 3.700 (o sea, ya iba cuatro por detrás). El ticket
> añadió **63 pruebas nuevas** en su fichero y **26 casos parametrizados** más (los que recorren los ficheros
> nuevos de `web/`), y los dos recuentos de JavaScript subieron **de 867 a 869**. **Y la ronda de la revisión
> (§10) los ha vuelto a subir**: 2 pruebas nuevas del guardián de anchos + 12 de la revisión en Python, y 5
> de las acciones del dinero en JavaScript, de modo que el número que hay que poner ahora es **3.818** y
> **874**, medidos.

### Las etiquetas del rastro de auditoría (esto es del defecto de producción del 02/10/2026)

`auditoria.accion` está declarada `String(80)` **en el fichero actual** (`app/models.py:1487‑1509`, con el
defecto contado dentro y la migración pendiente para una instalación de PostgreSQL que ya existiera), así que
el ensanchado **ya está hecho**: medido, `models.Auditoria.accion.type.length == 80` y
`models.Auditoria.entidad.type.length == 60`. Aun así, las etiquetas de este ticket se midieron una por una,
porque la regla del encargo era escribirlas de 30 caracteres o menos:

| Etiqueta | Mide | Dónde se escribe |
|---|---|---|
| `crear` | 5 | apuntar una entrega, un ajuste, una factura y un cobro |
| `anular` | 6 | anular una entrega, un ajuste, una factura y un cobro |
| `corregir` | 8 | corregir una entrega |
| `conciliar` | 9 | decir de qué factura es un cobro |
| `subir_papel` | 11 | subir el papel que demuestra un ajuste |
| `desconciliar` | 12 | quitarle la factura a un cobro |

**Ninguna se pasa de 30** (la más larga mide 12), así que no ha hecho falta acortar ninguna ni pedir nada. Y
las `entidad` que escribe el T12 —`venta_cosecha` (13), `ajuste_de_entrega` (17), `factura_emitida` (15),
`cobro` (5)— caben de sobra en su columna de 60.

> **Comprobado después del arreglo del coordinador** (él ensanchó la columna a 80 y reparó el fichero a mano
> tras un destrozo con PowerShell): medido, `accion` mide **80** y `entidad` **60**; mis cuatro tablas y las
> seis columnas de la entrega siguen intactas (`importe` es `VARCHAR(24)`, texto decimal y no `Float`); y de
> los **29 ficheros que este ticket ha tocado**, **ninguno tiene marca de orden de bytes y ninguno tiene
> restos de acentos destrozados** (se buscaron `Ã`, `Â`, `â€` y el carácter de reemplazo). El destrozo no llegó
> a nada de este ticket.

#### Un defecto del guardián que las vigila, encontrado al medirlas (y pedido, no arreglado)

`tests/test_las_etiquetas_del_rastro_caben.py` lee las etiquetas con `re.compile(r'accion="([^"]*)"')` sobre
`backend/app/**/*.py`. Su autor lo dio por bueno diciendo que **lee todas las etiquetas del código**; medido
con un guion que cuenta los sitios uno por uno, **no las lee todas**: tiene dos huecos, y los dos se vieron
midiendo las de este ticket. La comprobación, tal cual se corrió (da los números que siguen):

```python
import pathlib, re
# Lo que ve el guardián:
visible = re.compile(r'accion="([^"]*)"')
# Un sitio es INVISIBLE si después de la primera etiqueta sigue habiendo código (una expresión):
con_literal_delante = re.compile(r'accion="([^"]*)"\s*([^,\n]*)')
```

1. **Una etiqueta dentro de una expresión.** `accion="conciliar" if factura else "desconciliar"` (que es lo
   que había escrito yo) hace que el guardián vea la primera y **la segunda no**: `desconciliar`, la más
   larga de las mías, se quedaba **sin vigilar**. Hoy no pasa nada (12 de 80), pero es exactamente el defecto
   que el guardián existe para cazar: una etiqueta que crece sin que nadie lo mida. **Arreglado por mi parte**
   —la etiqueta se escribe entera en cada llamada, con su literal— porque hacerlo invisible era mi parte del
   problema: ahora el guardián ve **67 sitios en 32 formas distintas** (antes 66 y 31) y `desconciliar` está
   entre ellas. La prueba del rastro del cobro fija el comportamiento: `["crear", "desconciliar", "conciliar"]`.
   **Es un solo sitio en todo el programa** (medido: el único `accion=` cuyo valor es una expresión, aparte de
   `accion=accion` de `correcciones.py`, que es una variable y no una etiqueta).
2. **Una etiqueta dentro de un comentario o un docstring.** El guardián lee el fichero **con sus comentarios
   dentro**, así que un ejemplo escrito entre comillas dobles cuenta como etiqueta del programa. Se vio
   midiendo: mis tres comentarios de ejemplo subieron la cuenta **de 67 a 71** y metieron una etiqueta falsa
   (`...`) en la lista. Se ha limpiado mi parte (en los comentarios van comillas simples y el asunto contado),
   pero el hueco sigue ahí para el siguiente: un comentario puede hacer saltar el guardián por un texto que no
   es código, o **tapar** una etiqueta real. La receta del propio `AGENTS.md` («si un test lee ficheros y los
   interpreta, ese test necesita su propia prueba») apunta a quitar los comentarios antes de leer —como ya se
   hace con `quita_comentarios_js` para el JavaScript—; **no lo he tocado porque el fichero es del
   coordinador**.

### Lo que pedí que se añadiera a los dos guiones del coordinador (y ya está hecho por él)

No los he editado (son suyos). Lo que pedí, con lo que haría falta, **y lo que hay ahora**:

1. **`scripts/humo.py`**: un apartado del dinero, que recoja lo mismo que la prueba de contrato pero contra
   el servidor de verdad: apuntar una entrega **sin precio**, facturarla (y que conteste que no se puede),
   ponerle el importe, hacer la factura, cobrar **una parte** y comprobar que el pendiente es el número
   exacto; y reenviar el mismo cobro para ver que **no** se apunta dos veces. **Está hecho** (el
   coordinador lo cerró: su sección del dinero, **464 → 478 comprobaciones, 0 fallos**), y en mi pasada del
   §10.3 se ven sus comprobaciones del A08 y del A06 en verde: el importe pendiente en `None` en vez de
   cero, la factura que contesta 422, el pendiente 81 exacto, el cobro reenviado que no se duplica y el pie
   que cuenta las mismas filas que enseña.
2. **`scripts/comprobar_en_un_navegador.py`**:
   - **Una ruta a la tabla de lo que se vende** que compruebe, además de los textos, que **el pie y las
     filas dicen el mismo número**. **Está hecho**: las tres pantallas del dinero entran en su lista de
     anchos.
   - Y las tres pantallas nuevas del dinero a 390, 1.024 y 1.440 px: `#/ventas`, `#/ventas/facturas` y
     `#/ventas/cobros`. **Está hecho** (su guion pasó de **309 a 336 comprobaciones, 0 fallos**, y las tres
     caben enteras). Yo las había medido con un guion temporal que **usa sus funciones sin tocar su
     fichero** (ver §5).

---

## 8. Cuatro cosas que salieron mal, contadas como fueron

### 8.1. Las tarjetas del móvil salían **vacías** (y ningún test de mentira lo vio)

`app.js` prepara la tabla y el componente la coloca. Al preparar cada fila copié **las celdas** (que es lo
que la tabla necesita) y me dejé **los campos de la fila**: la tabla del ordenador salía perfecta y las
tarjetas del móvil salían con el nombre, la cantidad y todo el dinero en blanco (`<li><strong></strong><dl></dl>`).
Los 869 tests de JavaScript que había entonces pasaron; **lo cazó la comprobación del navegador del
coordinador** («las ventas:
se dibuja (A quién)») porque mira el HTML que se dibuja de verdad. Arreglado copiando la fila entera
(`...fila`) además de las celdas, y con el motivo escrito en el código.

### 8.2. La tabla medía 2.488 px de ancho en una pantalla de 1.024

Ocho columnas más la de los botones no caben a 1.024 px, y sin contenedor de desplazamiento **lo que se
desplazaba era la página entera**. Medido en un navegador real: 2.488 px de ancho en un hueco de 1.024. El
contrato pide que a 1.024 px «ninguna acción quede fuera por desplazamiento horizontal sin indicación». Está
arreglado con `.tabla-scroll` (que ya existía para esto) y vuelto a medir.

### 8.3. Una cosecha usada por una entrega **reventaba** al borrarla

`VentaDeCosecha.cosecha_id` es una clave ajena a `labores`, y borrar una cosecha usada por una entrega
habría dado un **fallo de la base en la cara del agricultor** (el `IntegrityError` sin traducir). Es el mismo
fallo que el proyecto ya arregló con las tierras y con los planes, y tenía su receta: se cuenta con
`correcciones.en_uso` (que saca las tablas de la base, no de una lista a mano) y se contesta 409 diciendo
**cuántas entregas la usan** y qué hacer. Tiene su prueba (singular y plural).

### 8.4. Corregir una venta le habría **borrado el dinero**

El asistente no pregunta el importe, el precio ni el vencimiento (decisión de §3.8), pero el `PUT` es el
mismo para el alta y para la corrección: **lo que no viaja se queda en blanco en el servidor**. O sea que
corregir los kilos de una entrega le habría borrado el importe y la habría devuelto a «sin importe» (el
A08), sin que nadie se enterara. Es el fallo que `AGENTS.md` documenta dos veces (el campo de la máquina al
cosechar y los datos de la portada del cuaderno) y se cerró igual: el borrador del asistente devuelve los
cuatro campos del dinero. Lo encontré revisando el recorrido de corrección antes de dar el ticket por
terminado, y ahora está escrito en el código con su motivo.

> Y una quinta, más pequeña: **el mismo identificador dos veces en la misma petición** de facturar hacía que
> la segunda línea tropezara con el índice único y el agricultor viera un fallo del programa en vez de una
> frase. Lo cazó una prueba de este mismo fichero; ahora se comprueba antes de escribir nada.

---

## 9. Resumen

- **Lo que se entrega**: la entrega con su dinero (que puede no saberse), la factura nuestra que agrupa
  entregas sin duplicar ingresos, los cobros parciales con su pendiente exacto, las devoluciones y los
  ajustes con origen y evidencia, y la tabla de S12 con su pie: siete pantallas nuevas, cuatro tablas
  nuevas y seis columnas nuevas en la tabla de siempre.
- **Los dos casos de aceptación**, comprobados con sus números: **A06** (121 − 40 = 81, y cobrar no crea
  facturas) y **A08** (8.000 kg sin precio: cantidad conocida, importe pendiente, **no** cero).
- **El dinero no pierde céntimos**: `Decimal` en el programa, texto decimal en la base, redondeo al céntimo
  al alza una sola vez, y ocho números que fallarían con coma flotante.
- **Lo medido (después de la revisión, §10)**: **3.818** pruebas de Python (2 en rojo, los dos recuentos de
  documentación que son del coordinador), **874** de JavaScript (0 fallos), `humo.py` contra un servidor
  aislado **483 comprobaciones, 0 fallos**, `comprobar_en_un_navegador.py` **336 comprobaciones, 0 fallos**,
  y mis siete pantallas dibujándose y cabiendo a **390, 1.024 y 1.440 px**.
- **Y la revisión independiente**: los **doce defectos** que encontró (`docs/REVISION_T12.md`), arreglados
  uno por uno y con sus doce pruebas en verde, **también en PostgreSQL** (§10).
- **Lo que falta, y está dicho**: el botón de subir el papel de un ajuste, la conciliación muchos a muchos
  (T20), las vistas guardadas de esta lista, y las cuatro filas y los dos guiones del coordinador (§7).

---

## 10. La revisión independiente: los doce defectos del T12, arreglados

> **De dónde sale esto.** El T12 se sometió a una revisión independiente: `docs/REVISION_T12.md` (el
> informe, con la foto del árbol y las medidas) y `backend/tests/test_revision_t12.py` (doce pruebas, **una
> por defecto**, todas en rojo al empezar, **en SQLite y en PostgreSQL**). El encargo de esta ronda fue
> arreglarlos **por orden de gravedad**, sin tocar ni el informe ni sus pruebas: los doce rojos tenían que
> ponerse verdes **arreglando el programa**, no aflojando la prueba.

### 10.1. Los doce, uno por uno

| # | Qué estaba mal (medido por la revisión) | Qué se ha hecho | Dónde |
|---|---|---|---|
| 1 | **`POST /api/ventas/{id}/ajustes` recibía un `dict` crudo**: un importe en número de JSON, un importe o una cantidad que no son números o una fecha en castellano daban **500** (`ErrorDeDinero`/`ValueError` dentro del endpoint), y el móvil **reintenta los 5xx**, así que el apunte se quedaba en la cola para siempre | Se ha escrito el esquema que faltaba, **`AjusteEntrada`**, con las mismas puertas que el cobro: `importe` como `Decimal` sin `float` y con tope, `cantidad` que tiene que ser un número, `fecha` como fecha y el ancho de cada columna. El endpoint lo declara (`datos: AjusteEntrada`) y ya no convierte nada dentro: lo que no vale contesta **422 con la frase del agricultor** | `backend/app/schemas.py`, `backend/app/routers/ventas_api.py` |
| 2 | **Nueve campos de texto del dinero sin tope**: se aceptaban 250 letras en un `varchar(120)`. En SQLite se guardaban; **en PostgreSQL fallaba la operación entera** (500). El mismo defecto que ya llegó a producción con `auditoria.accion` | Cada campo declara **el ancho de su columna, leído del modelo** (`_cabe_en_la_columna`), y un validador de una sola vez (`_revisa_lo_que_no_cabe`) rechaza con la frase del agricultor lo que no cabe. Los nueve campos, por la API, contestan 422 o no se guardan | `backend/app/schemas.py` |
| 2 bis | **Y el mismo riesgo, en todo el programa, son 170 campos** (lo midió el coordinador al revisar esto, no nueve): **ya está cerrado por otra vía** —una comprobación **antes de escribir**, en `database.py`, que contesta **422 y no 500**—, así que **estos nueve campos no pueden tumbar una operación aunque no llevaran su `max_length`**. Lo que aporta mi arreglo en ellos es **la frase en la puerta y antes de intentarlo** (comodidad: que el formulario lo diga), no tapar un agujero abierto. Queda dicho así para que nadie lo cuente como un agujero que sigue ahí | `backend/app/database.py` (del coordinador) y `backend/app/schemas.py` |
| 3 | **Un importe de 22 cifras enteras no cabe en la columna del dinero** (`VARCHAR(24)`): en SQLite entraba (201) y en PostgreSQL era un `DataError` (500) | Dos topes arriba, dichos con palabras: **99.999.999,99 €** para un importe y **999.999,999999** para un precio por unidad; `dinero.cabe_en_el_dinero` los comprueba en el esquema y `dinero.a_texto` **se niega a devolver un texto que no quepa** (24) | `backend/app/dinero.py`, `backend/app/schemas.py` |
| 4 | **`GET /api/ventas` no traía las cuentas del dinero**: decía `facturada: false`, `importe_total: null`, `estado: ""` de una entrega que estaba dentro de una factura cobrada a medias. **Tres puertas del mismo dato y dos contestaban distinto** | La lista calcula el reparto de lo cobrado por factura viva (igual que la ficha y la tabla) y llama a `con_nombres` con la explotación y el reparto: los ocho campos coinciden con los de la ficha, comparados uno por uno | `backend/app/routers/ventas_api.py` |
| 5 | **La tabla de S12 ponía «De dónde» encima de los botones**: el servidor mandaba doce columnas de datos y la pantalla escribía once celdas más la de acciones, así que el valor de esa columna **no se pintaba nunca** en el ordenador | La última columna es ya la de las acciones (`textos.VENTA["tabla_acciones"]`, sin clave de dato y sin poder ordenar), **obligatoria** como las otras seis: las doce de datos tienen su celda y la decimotercera la pinta la pieza `Tabla` | `backend/app/routers/ventas_api.py` |
| 6 | **Los tres `contacto_id` no tenían puerta**: la columna existía, el endpoint la validaba y **ninguna pantalla la preguntaba**, así que no se podía enlazar nada con la ficha del cliente | Las tres pantallas preguntan el contacto en una lista de **sus contactos** (con «sin enlazar» como primera opción) y lo mandan: `venta-contacto`, `factura-emitida-contacto` y `cobro-contacto`. Los textos son los del servidor | `backend/web/app.js`, `ventas/js`, `factura_emitida.js`, `cobro_nuevo.js`, `backend/app/textos.py` |
| 7 | **28 de las 30 acciones del dinero no se pulsaban en ninguna prueba**: solo se comprobaba que su `data-accion` estaba pintado | Cinco pruebas nuevas en `tests_js/interfaz.test.js` que **pulsan las 30**, una por una, y miran lo que llega al servidor: qué método, qué ruta y qué cuerpo | `backend/tests_js/interfaz.test.js` |
| 8 | **El pie convertía «no se sabe» en `0,00 €`**: con una entrega sin importe decía «1 entrega · 0,00 € · pendiente 0,00 €», que es lo que el A08 prohíbe | Cuando **ninguna** entrega de las contadas tiene importe, el pie no da ningún número: dice que el importe está sin apuntar (singular y plural). Con importes conocidos sigue igual | `backend/app/routers/ventas_api.py`, `backend/app/textos.py` |
| 9 | **Un cobro de `0,004` se aceptaba y se guardaba como `0,00 €`**: la comprobación de «cero euros no es un cobro» se hacía **antes** de redondear | Se redondea primero y se comprueba lo que se va a guardar: contesta 422 con la misma frase | `backend/app/routers/ventas_api.py` |
| 10 | **El aviso de la entrega repetida salía con el hueco en blanco** («ya está dentro de la factura .») y decía algo que no era: esa entrega no estaba en ninguna factura | Mensaje propio para lo que de verdad pasa (**la misma entrega viene dos veces en esta petición**), con su texto y sin nombre de factura | `backend/app/routers/ventas_api.py`, `backend/app/textos.py` |
| 11 | **Una factura anulada enseñaba `0,00 €` y «0 entregas»**: solo se miraban sus líneas vivas, aunque sus líneas siguen en la base con su motivo | La ficha de una factura quitada enseña **lo que decía** (su total y sus líneas, cada una dicha como anulada), su estado es «Quitada» y su pendiente es cero **de verdad** (una factura quitada no se debe), con el aviso de que lo que se ve es lo que decía | `backend/app/routers/ventas_api.py`, `backend/web/react/pantallas/factura_emitida.js`, `backend/app/textos.py` |
| 12 | **Una prueba del propio ticket se ponía roja en PostgreSQL por construcción**: empezaba con `assert engine.dialect.name == "sqlite"`, así que el viaje de ida y vuelta del importe **no se comprobaba en el motor de producción** | Se comprueba en los dos motores: el tipo guardado se pregunta con `typeof` en SQLite y con `pg_typeof` en PostgreSQL, y lo que importa —que la columna guarde **texto** y que el valor vuelva exacto— se mide igual. En los dos sale `text` / `character varying` | `backend/tests/test_el_dinero_de_las_ventas.py` |

### 10.2. El defecto que encontraron las pruebas nuevas (y número 13 de la lista)

Las pruebas del defecto 7 no solo pulsan los botones: **miran lo que sale hacia el servidor**. Y al
escribirlas salió un defecto que ninguna prueba de la API podía ver: **el `POST /api/cobros` salía sin
`clave_de_reenvio`**. La clave se leía del borrador (`borrador.clave`), pero **nadie la escribía nunca** en
los tres sitios donde se creaba: el campo estaba en el esquema, el servidor sabía usarlo, y la pantalla no
lo mandaba. Consecuencia en el campo: el móvil sin cobertura manda el cobro, no llega la respuesta, se
reintenta… y **el dinero entra apuntado dos veces**. Las pruebas de la API no lo veían porque ellas mandan
la clave a mano.

Arreglado en `pantallaCobroNuevo` (la clave nace con el borrador, como en el ajuste y en la factura) y
**con prueba**: la prueba del cobro comprueba que la petición lleva `clave_de_reenvio`, y comprueba además
que apuntar un cobro **no crea ninguna factura** (`POST /api/facturas-emitidas` no se ha llamado ni una vez),
que es la segunda mitad del A06.

### 10.3. Lo que se midió después del último cambio

Todo lo de abajo está medido **sobre el árbol actual**, después del último arreglo:

| Qué | Comando | Medido |
|---|---|---|
| Los doce defectos | `../.venv/Scripts/python.exe -m pytest tests/test_revision_t12.py -q` | **12 pruebas, 0 fallos, 0 errores** (antes: 12 rojos) |
| Los doce defectos **en PostgreSQL** | `$env:CUEDIGITAL_SUITE_SOBRE="postgresql+psycopg://postgres:pruebas@127.0.0.1:55432/cuedigital_t12_final"` y la misma orden | **12 de 12 en verde** (base propia, creada para esto; comprobado antes que ninguna otra suite estaba usándola) |
| El ticket entero, en PostgreSQL | ídem, `tests/test_el_dinero_de_las_ventas.py` | **65 pruebas + las 12 de la revisión = 77, 0 fallos** |
| La suite entera | `../.venv/Scripts/python.exe -m pytest tests -q` | **3.818 pruebas, 2 en rojo** y las dos son los recuentos de documentación (`README.md`, `AGENTS.md` y `docs/LO_QUE_PIDE_LA_JUNTA.md` dicen **3.700** y **867**; medido: **3.818** y **874**). Son del coordinador y no se han tocado |
| JavaScript | `node --test "tests_js/*.test.js"` | **874 pruebas, 0 fallos** (las 5 nuevas del defecto 7 dentro) |
| Servidor aislado (HTTP de verdad) | `../.venv/Scripts/python.exe scripts/humo.py http://127.0.0.1:8132`, con base temporal limpia y puerto propio | **483 comprobaciones, 0 fallos**, `RESULTADO: todo correcto` |
| Navegador de verdad | `../.venv/Scripts/python.exe scripts/comprobar_en_un_navegador.py http://127.0.0.1:8132` | **336 comprobaciones, 0 fallos**, `RESULTADO: la interfaz se abre y se dibuja en un navegador de verdad` (36 de sus líneas son de las pantallas del dinero) |
| Codificación de los 23 ficheros que este ticket ha tocado | guion propio: BOM, UTF-8 válido y los marcadores de destrozo | **ninguno tiene BOM ni mojibake**. Los tres aciertos que salen son **la propia lista de marcadores escrita en este documento**, no un destrozo |

**Y las etiquetas del rastro de auditoría**, que el encargo pidió medir (2 de octubre, el defecto que llegó
a producción): las seis del T12 miden **5, 6, 8, 9, 11 y 12** caracteres (`crear`, `anular`, `corregir`,
`conciliar`, `subir_papel`, `desconciliar`), **ninguna pasa de 30**; las cuatro entidades miden entre **5 y
17** (`cobro`, `venta_cosecha`, `factura_emitida`, `ajuste_de_entrega`) y caben en su columna de 60. La
columna `auditoria.accion` la ensanchó el coordinador a **80** (medido), así que sobra sitio para lo que
venga.

### 10.4. Lo que sigue sin poder comprobarse

1. **La suite entera en PostgreSQL**, no solo los dos ficheros del T12: son **77 pruebas** las que he
   medido allí. El resto de la suite tiene sus propios casos de motor (y su receta en
   `tests/test_arranque_en_postgresql.py`), y no es de este ticket.
2. **Los dos rojos de recuento** seguirán ahí hasta que el coordinador ponga **3.818** y **874** en los tres
   documentos (el número medido, no el que había).
3. **El botón de subir el papel de un ajuste** sigue sin puerta en la pantalla (el endpoint funciona y tiene
   prueba); es lo primero de la lista de pendientes y no lo pedía la revisión.
4. **`humo.py` y `comprobar_en_un_navegador.py` los he ejecutado, pero no los he tocado**: son del
   coordinador, y la sección del dinero de `humo.py` (464 → 478 comprobaciones) y las tres pantallas del
   dinero en la lista de anchos del navegador (309 → 336) son suyas, ya cerradas cuando corrí los dos
   guiones. Mi cuenta de líneas `[OK  ]` en `humo.py` fue **483** y la suya **478**: la diferencia está dicha
   arriba y sin resolver.
5. **Los tres `contacto_id` se prueban de mentira, no de verdad.** El `<select>` del contacto solo se pinta
   cuando la lista de contactos trae alguno, y la comprobación del navegador crea una cuenta **sin ningún
   contacto**: así que la puerta nueva se ha ejercitado en la prueba de JavaScript (con un contacto de
   mentira) y **nunca se ha dibujado en un navegador de verdad**. Es lo primero que habría que mirar si
   alguien quiere verla con los ojos.

---

## 11. La foto congelada (03/10/2026, al cerrar los doce defectos)

**Desde esta foto no se ha tocado código ni pruebas**: los tamaños y las horas son los del árbol con el que
se midió todo lo del §10.3, y este informe es lo único que se ha seguido escribiendo después (por eso no
aparece en su propia tabla). Los sha256 van con sus 16 primeros dígitos.

| Fichero | Bytes | Hora (local) | sha256 (16) |
|---|---|---|---|
| `backend/app/dinero.py` | 22.067 | 2026-10-03 01:53:23 | `24daeb6b5cdbc737` |
| `backend/app/schemas.py` | 131.880 | 2026-10-03 01:57:06 | `3ab2549d095e1616` |
| `backend/app/textos.py` | 355.981 | 2026-10-03 02:04:34 | `09dc91423a85c491` |
| `backend/app/routers/ventas_api.py` | 102.366 | 2026-10-03 02:10:17 | `4a38a7398884ebd7` |
| `backend/web/app.js` | 759.317 | 2026-10-03 02:19:43 | `5733a432714867b3` |
| `backend/web/react/pantallas/venta_importe.js` | 5.205 | 2026-10-03 02:05:01 | `9ee3706373c3e144` |
| `backend/web/react/pantallas/facturar_entregas.js` | 6.305 | 2026-10-03 02:05:24 | `4cf007be67b75951` |
| `backend/web/react/pantallas/factura_emitida.js` | 7.124 | 2026-10-03 02:10:29 | `608a9a48ffb76aa5` |
| `backend/web/react/pantallas/cobro_nuevo.js` | 5.039 | 2026-10-03 02:05:32 | `b0c9aabe51def4ea` |
| `backend/tests/test_el_dinero_de_las_ventas.py` | 100.050 | 2026-10-03 02:28:40 | `7e848e4378bfc500` |
| `backend/tests_js/interfaz.test.js` | 679.889 | 2026-10-03 02:19:55 | `ba7c2ac0b2571001` |

Los tres números medidos con esta foto: **3.818 pruebas de Python** (2 en rojo, los dos recuentos),
**874 de JavaScript** (0 fallos) y **48 pantallas en React** (los 48 ficheros de
`backend/web/react/pantallas/`, con las siete nuevas del T12 dentro).

**Este informe no está en la tabla a propósito**: es el único fichero que se ha seguido escribiendo después
de congelar el código y las pruebas (los arreglos de la revisión son los once de arriba, y estos dos de
`docs/`: este documento).
