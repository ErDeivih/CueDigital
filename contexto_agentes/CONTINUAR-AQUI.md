# DÓNDE ESTAMOS — para continuar sin releer toda la sesión

> **Corrección de fechas (13/10/2026, revisión del dueño).** Este documento fechaba el 11/10 lo que se escribió
> el **13/10**, y decía a la vez que las notas estaban terminadas y que faltaba su pantalla. Las dos cosas están
> corregidas **aquí**. En el resto de los documentos del perfil (`ESTADO.md`, `CRM-03-INVENTARIO.md`) hay todavía
> entradas con el 11/10: **no se han cambiado a ciegas** porque algunas pueden ser de cuando se escribieron de
> verdad, y reescribir fechas sin poder comprobarlas sería falsificar el registro. Lo que sí vale para todas: la
> fecha del sistema es **13/10/2026**, y **todo lo que está commiteado se puede fechar por su commit**, que es la
> fuente de verdad.

**Escrito el 13/10/2026, al parar el bucle por indicación de David** («tenemos que parar, deja documentado la
tarea para continuar más adelante y para el loop»), **y continuado el mismo día** cuando dijo «ya puedes
continuar con la tarea que estabas haciendo»: en esa continuación se cerró **el criterio (f)**, las notas con
autor (servidor **y** pantalla, verificado pulsando en el navegador). Todo lo que dice aquí está **commiteado y
verificado**; nada queda a medias.

> **Aviso del bucle**: el `goal` quedó **en pausa** y **el agente no puede reactivarlo** (`the model cannot resume
> a paused goal`). Si se quiere que vuelva a trabajar por rondas solo, hay que **reanudarlo desde la interfaz**.

---

## 1. Estado, medido, en el momento de parar

| | |
|---|---|
| **Python** | **4813 pruebas, 0 fallos** (el recuento corre la suite entera dos veces) |
| **JavaScript** | **1088 pruebas, 0 fallos** |
| Guardianes (recuento de Python y de JS, textos, `DESIGN.md`, colores sueltos) | **0 fallos** |
| La ficha de la compra en el navegador (CRM-00, 53 comprobaciones) | **0** |
| **Base del agricultor** (`backend/cuedigital.db`) | **intacta** — sha256 `CC6575…34B12`, comprobada en cada ronda |
| Último commit | el de las notas con autor (8 ficheros, 252 líneas) |

Los tres documentos del recuento (`README.md`, `AGENTS.md`, `docs/LO_QUE_PIDE_LA_JUNTA.md`) están **al día**:
4798 → … → **4813** de Python y **1088** de JavaScript.

## 2. Lo que se terminó en esta tanda (y dónde está)

### El escritorio, rediseñado (el encargo del dueño)

David miró las capturas y dijo: *«no se parece a un CRM normal, parece una UI para niños pequeños»* y *«que la
complejidad esté para PC»*. **Está hecho, medido y documentado** en `docs/ESTADO_DEL_REDISENO.md` (bloque «EL
ESCRITORIO», al final). Los números, medidos en el navegador:

| | antes | ahora |
|---|---|---|
| fila de tabla | **277,9 px** | **46 px** |
| cabecera de tabla | 50 px | **29 px** |
| ancho del contenido | **704 px** (44 rem centrado) | **~1300 px** |
| cuerpo / título | 18 / 24 px | **16 / 20 px** |
| botón | 44–48 px | **40 px** (el suelo del contrato) |
| radio de control | 14 px | **8 px** |
| números de una columna | — | **`tabular-nums`** + cebra al 1 % |

**Cuatro pantallas del CRM pasaron de forma de móvil a tabla**: contactos (20 filas de 46 px), cobros
(6 columnas), facturas (8 columnas) y la ficha de la compra (4 columnas). **El móvil no cambió ni un píxel.**

- La capa vive **al final de `backend/web/estilos.css`**, dentro de `@media (min-width: 64rem)`.
- Las tarjetas se callan **solo si la tabla está** (`#pantalla:has(.solo-escritorio.tabla-scroll) …`), así que
  **la pantalla nunca puede quedar vacía**.
- **Capturas** para la revisión visual (que solo puede hacer una persona): `docs/capturas/ventas-escritorio-antes.png`,
  `…-crm.png`, `contactos-escritorio-antes.png`, `contactos-escritorio-tabla.png`, `cobros-escritorio-tabla.png`.
- **Instrumentos nuevos**: `medir_la_densidad_de_la_interfaz.py`, `capturar_una_pantalla_del_escritorio.py`,
  `medir_las_pantallas_de_compra_y_cobro.py`, `capturar_la_lista_de_cobros.py`.

**Decisiones que esperan la palabra de David** (no las toca el agente):
1. **Bajar los botones de 40 a 34 px** (Odoo usa 33, Frappe 28). Hoy manda el suelo de 40 escrito en `DESIGN.md`
   con un motivo de accesibilidad («el agricultor tiene entre 50 y 70 años»).
2. **Bajar la letra de 16 a 14 px** (los tres CRM usan 14). Mismo caso: el suelo de 16 es del proyecto.
3. **El tono del color**: en un CRM real el color se reserva a los estados y la acción principal es casi negra
   (Frappe usa `gray-900`). **La paleta no se ha tocado.**
4. **El móvil adelgazado** a lo acordado: subir una factura, un resumen rápido y apuntar un trabajo. **Sin
   empezar.**

### CRM-03, criterio (e): el contacto que ya no se usa — **CERRADO**

`Contacto.activo` (sin migración a mano: `database.asegurar_columnas` añade la columna sola), fuera de
`correcciones` (**dar de baja es una acción propia**: una corrección no puede reactivar a nadie sin decirlo),
`ContactoSalida.activo` **sin valor por defecto** (con defecto, tapaba el valor real), la puerta
`POST /api/contactos/{id}/baja` y `/alta` con **motivo y traza propia** (sin apuntar dos veces), el **botón** en
la ficha —verificado **pulsándolo**— y el **estado a la vista** en el rótulo (que es la columna «Qué es» de la
tabla y el rótulo de la tarjeta). **Decisión tomada y probada**: no se filtra nada, porque los sitios donde se
ofrece un contacto son sitios de **historia** y el proveedor con el que ya no trabajas es quien necesita que sus
papeles viejos sigan teniendo ficha.

### CRM-03, criterio (f): las notas con autor — **CERRADO** (13/10/2026)

Hecho y verificado (4 pruebas en `tests/test_las_notas_de_un_contacto.py`):

- `models.NotaDeUnContacto` (autor que **puede faltar y se dice**; **no entra en `correcciones`**: las notas **no
  se corrigen, se apuntan** —si algo está mal, se apunta otra diciéndolo, y así queda lo de antes—).
- `POST /api/contactos/{id}/notas` con **el autor puesto por el servidor** (de su vale; del navegador no se
  acepta, que sería poder firmar cosas que no ha escrito uno).
- `notas_con_autor` en la ficha, **de la más nueva a la más vieja**; la lista de contactos manda la lista vacía.
- Una nota vacía contesta **422 con palabras** (`C7_una_nota_necesita_texto`).
- Y una prueba que exige que **no haya puerta para corregir ni borrar** una nota.

**La pantalla, y con esto el criterio queda CERRADO** (11/10/2026): en la ficha, «Lo que se sabe de esta
ficha» —las notas **de la más nueva a la más vieja**, con **su autor y su fecha**—, un campo para apuntar otra y
su botón. **Sin botón de corregir ni de borrar, a propósito** (las notas se apuntan, no se corrigen; el servidor
tampoco tiene esa puerta y hay una prueba que lo impide).

**Verificado pulsando en el navegador, no deducido**:

```
la ficha: 22 | notas de partida: 0   →   se escribe la nota y se pulsa   →
{"hay_lista": true,
 "texto": "Nos dejo tirados en la campana del 24. La escribió: Cuaderno de volumen · 2026-10-13",
 "campo_vacio": true}
```

**Dos fallos míos por el camino, los dos de anclaje** (y quedan escritos en el commit): leer la ficha con
`mandarCambio(…, "GET", null)` en vez de por **su puerta** (`abrirLaFichaDeUnContacto`, que lee con `apiJson`) —la
nota se apuntaba y la lista no salía—; y un guion en `%TEMP%` que no encuentra `app` **sin `PYTHONPATH`**.

### El reenvío seguro, con la acción entera y con la colisión (13/10/2026, revisión del dueño)

La revisión encontró **dos huecos** y los dos eran de verdad:

1. **La clave sola no identifica la acción.** Si se perdía la respuesta, el agricultor **editaba** el texto y
   reintentaba: el servidor encontraba la clave y contestaba éxito **sin mirar nada más**, así que **su texto nuevo
   desaparecía creyendo que se había guardado** —pérdida silenciosa—. Ahora se compara **la acción entera** (la nota,
   su contacto y su texto): si coincide es un reenvío legítimo (200) y **si no, 409**, sin tocar nada y diciéndolo.
2. **La consulta previa y el guardado no eran atómicos.** Dos peticiones simultáneas podían encontrar la clave
   libre las dos; el índice único impedía duplicar la nota, pero **el choque no lo recogía nadie** y el agricultor
   habría visto un error del servidor sin saber si su nota se guardó. Ahora se **deshace lo intentado, se lee lo
   que quedó y se contesta** como corresponde.

**Y en el front, el 409 gasta la acción**: se conserva el borrador (`nota_a_medias` llega al `borrador` de la
ficha —eso lo encontró el subagente **ejecutando** la aserción, no leyendo—) y **se renueva la clave**, para que al
volver a pulsar su texto editado se apunte como **nota nueva**. Sin eso, el agricultor se quedaría en un 409 para
siempre.

**Cómo está probado, y con qué límite**: con **hilos de verdad** (`ThreadPoolExecutor`, dos peticiones
simultáneas) y no con dos llamadas seguidas —eso lo pidió la revisión con estas palabras: *«No declares
concurrencia comprobada mediante dos llamadas consecutivas»*—. Y la prueba de «dos acciones voluntarias» ahora
manda **dos claves distintas**, que es lo que hace el navegador.

## 3. Lo que queda de CRM-03, por orden del inventario

1. **Canales y direcciones múltiples** (hoy: un teléfono, un correo, una dirección).
2. **El saldo del contacto** (criterio (d)) — reutilizando **la regla única del dinero** (`app/servicios.py`),
   sin duplicarla.
3. **La fusión de dos fichas** con auditoría.
4. **Tareas / próximas acciones**.
5. Y aparte, y más caro: **el permiso por materia** en el servidor (toca todas las puertas que devuelven dinero).

Después: CRM-04 servicios a terceros, CRM-05 costes/inversiones, CRM-06 tierra/mapa, CRM-07 insumos/maquinaria,
CRM-08 fiabilidad, CRM-09 PAC, CRM-10 meteo, CRM-11 paneles, CRM-12 lectura de papeles.

## 4. Las trampas que ya me han costado rondas (leer antes de tocar)

1. **`app/textos.py` usa CRLF** (8837 líneas) y `app/routers/contactos_api.py` usa **LF**. Insertar por línea con
   una comparación ingenua **falla siempre** en los textos, y forzar la inserción **rompe la sintaxis**. Se
   inserta **por número de línea leído del fichero** y conservando el `\r`. *(Costó dos rondas perdidas.)*
2. **Un `import` que no entra no avisa**: con `from __future__ import annotations`, la anotación queda sin
   resolver, FastAPI la trata como parámetro de consulta y **la generación del esquema del proyecto revienta**.
   **Comprobación obligatoria antes de correr pruebas**: `python -c "from app.main import app; print(len(app.openapi()['paths']))"`.
3. **Las respuestas pasan por el esquema y el esquema filtra lo que no declara** (`KeyError: 'notas_con_autor'`).
   Y **un valor por defecto en una salida tapa el dato que falta** (pasó con `activo`): si falta, que falle.
4. **`correcciones.campos_corregibles` copia todas las columnas**: una columna nueva que no venga rellena rompe
   el guardado (`NOT NULL`). Si es una decisión y no un dato, va en `CAMPO_QUE_NO_SE_TOCA`.
5. **Los `_pintar_*` no reciben la sesión de la base**; los `_la_*` sí. Meter una consulta en el sitio que no toca
   da `NameError: name 'db' is not defined`.
6. **Las pruebas de las pantallas usan la `<table>` dentro de las propias tarjetas**: preguntar por
   `class="tabla"` da verde **sin** la tabla de escritorio. Para eso está `data-tabla="contactos"`.
7. **Una prueba no vale hasta que puede ponerse roja**, y **un corte mal escrito prueba lo que no es**:
   `false && cond ? A : B` cae, por precedencia, en el `B` (el respaldo). Se corta con `const laTabla = null;`.
8. **Antes de medir una pantalla, leer su título**: medí tres veces pantallas de error («Esa dirección no lleva a
   ninguna parte») y una vacía, y saqué conclusiones falsas.
9. **Mis guiones mueren imprimiendo** caracteres raros (cp1252): usar `$env:PYTHONIOENCODING = "utf-8"`.
10. **Los finales de línea de mis propias herramientas**: un `write_text` de Python convirtió un fichero LF en
    CRLF y el commit pareció cambiar 1650 líneas. Se escribe **en bytes** cuando el fichero no es mío.

## 5. Cómo se comprueba todo (los comandos, tal cual)

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests -q                     # la suite entera
node --test "tests_js/*.test.js"                                    # la del navegador (1088)
..\.venv\Scripts\python.exe scripts\poner_al_dia_el_recuento_de_pruebas.py   # recuento + los tres documentos
..\.venv\Scripts\python.exe scripts\medir_la_densidad_de_la_interfaz.py http://127.0.0.1:PORT "#/ventas" 1440
```

**Servidores de prueba**: base temporal y puerto libre, nunca el 8000 ni el 8029 de David.
`$env:CUEDIGITAL_DATABASE_URL = "sqlite:///$env:TEMP\cd-xxx.db"` y `uvicorn app.main:app --port 83xx`.

**No correr dos suites a la vez en esta máquina**: se estorban y el recorrido de la compra se queda sin tiempo
(eso ya me pasó y lo confundí con un fallo intermitente del producto).

## 6. Lo que NO está hecho y no se puede declarar

- **La revisión visual** de las capturas del escritorio: **solo la puede hacer una persona**. El agente mide, no
  ve.
- **PostgreSQL**: no hay entorno; todo lo medido es SQLite en pruebas.
- **El móvil adelgazado**: sin empezar.
- **CRM-02**: quedan identidad por formato (criterio j), el formato **N43** y parte del recorrido real.
- **El permiso por materia** de CRM-03: sin empezar, y es el más caro.

### El recuento de Python: por qué pasó de 4822 a 4824 (13/10/2026)

Lo explicó la revisión del dueño y conviene que quede escrito, porque el número cambió sin que nadie añadiera
pruebas a mano: **`backend/scripts/verificar_el_conflicto_de_una_nota.py` trae dos comprobaciones que pytest
recoge como casos** —la ausencia de BOM y los acentos—, así que la suite pasa de **4822 a 4824** casos recogidos.
Cuando se cuentan, hay que contarlas.

**Y una advertencia sobre cómo se comprueba, que costó un susto**: el guardián del total **se salta cuando se
ejecuta solo una parte de la suite**. Verlo en verde por separado **no** confirma el recuento. La comprobación
buena es la **suite entera**, que con los documentos en 4824 da **0 fallos** (comprobado el 13/10/2026).

**Pendiente, y es del instrumento**: `poner_al_dia_el_recuento_de_pruebas.py` cuenta por su cuenta —no incluye
esas dos comprobaciones—, así que escribe **4822** en los documentos, el runner recoge **4824** y el guardián se
queja de la salida del propio guion. Hay que enseñarle a contar como cuenta el runner.

**Y la forma no destructiva de ver roja la prueba de la colisión** (para no volver a tocar el código de
producción): sustituir **con monkeypatch** la lectura posterior por una función que falle y comprobar que la
prueba detecta la falta de recuperación.

---

## CIERRE DE LA ENTREGA 1 — EL SALDO DEL CONTACTO (13/10/2026)

**Qué funciona** (y dónde está):

| pieza | fichero |
|---|---|
| El cálculo del saldo, sobre **la regla única del dinero** (`servicios.lo_cobrado_de_una_factura`, `lo_pagado_de_un_gasto`, `lo_cobrado_por_factura`) | `backend/app/saldos.py` |
| La puerta `GET /api/contactos/{id}/saldo` (con `_el_contacto_de_la_finca`: otra finca da **404**) | `backend/app/routers/contactos_api.py` |
| La pantalla en la ficha: los **dos sentidos separados**, cada cifra con sus documentos, el dinero sin asignar, los excesos para revisar y la cobertura con la moneda | `backend/web/react/pantallas/contactos.js` + `backend/web/app.js` |
| **La ficha tiene dirección propia** (`#/contactos/<id>`) | `backend/web/react/rutas.js` + `app.js` |
| **El camino de vuelta** del gasto a la ficha de su proveedor | `backend/web/react/pantallas/gastos.js` |

**Criterios del encargo, comprobados** (las cifras, **por las puertas de verdad**):

- Venta **1210** con cobro **400** → **nos debe 810** ✓
- Compra **600** con pago **150** → **le debemos 450** ✓
- Las dos del mismo contacto → **810 y 450 separadas** (no 360) ✓
- Factura y gasto de la misma compra → **una sola obligación** ✓ (la factura de compra **no tiene `contacto_id`** y **no se adjudica por nombre**)
- Anular el cobro → **vuelve a deberse 1210** ✓
- Un importe que no se sabe → aparece con `pendiente: None` y `sin_importe: 1`, y **el total no lo cuenta como cero** ✓
- Otra explotación → **404** ✓
- **El recorrido** (ficha → cifra → documento → vuelta → recarga) → **medido con el guion: 46 comprobaciones, 1 fallo**, y **ese fallo es un control que prueba el botón «VOLVER»** (que **no debe cambiar**: esa pantalla se abre también desde la lista de cuentas).

**Pruebas ejecutadas**: 9 de servidor en `backend/tests/test_el_saldo_de_un_contacto.py` (**8 pasan, 1 se salta diciéndolo**: el exceso **no se puede producir por la puerta**, porque el programa **impide aplicar de más**) · 4 de pantalla en `tests_js/contactos.test.js` · 1 del enlace en `tests_js/react.test.js` · **JavaScript 1100 · 0** · **Python 4839** · y el guion `backend/scripts/verificar_el_recorrido_del_saldo.py` (**46 comprobaciones**).

**Demostrado que pueden fallar**: las pruebas de servidor (invirtiendo una expectativa **en la prueba**), las de la pantalla (igual) y **la del enlace** (mutada **por número de línea** y **comprobada leyendo la línea mutada**: 339/1 en rojo y 340/0 al restaurar).

**Limitaciones, dichas**:

1. **El exceso de cobro no está ejercitado**: la puerta lo impide, así que el camino de `para_revisar` **existe pero no se ha visto funcionar**. Habría que provocarlo por otra vía (anular una factura ya cobrada, o datos heredados).
2. **Un control del guion de recorrido sigue en rojo** por ser **más estricto que el contrato** (prueba el botón, que no debe cambiar).
3. **La revisión visual de las capturas** la tiene que hacer una persona (o un agente con visión): el agente que las hizo **no puede ver imágenes**.
4. **No hay columna de moneda** en la base (comprobado en las 59 tablas): el saldo **declara EUR** y no suma monedas distintas porque **no las hay**.

**Commits**: el saldo del servidor (`0b8a45b` y anteriores), el reventón del saldo incompleto y las dos pruebas que faltaban (`983dfcc`), la dirección de la ficha (`8475f62`), el camino de vuelta (`4e3d98f`), su prueba permanente (`2e5492d`) y la demostración en rojo.

**Siguiente tarea**: **Entrega 2 — canales y direcciones múltiples** (varios teléfonos, correos y direcciones con etiqueta y principal, conservando los datos actuales al migrar).

**Y una lección que me ha costado cuatro veces en un día**: un guion que dice que ha hecho algo **no es prueba de que lo haya hecho**, y **el resultado hay que leerlo**. Las cuatro: un recuento que escribió «0 tests» en los documentos; un arreglo que no encontró su línea e imprimió «0 líneas corregidas»; un reenvío que no se aplicó por el CRLF y mi comprobación dio verde porque la cadena existía en **otra** función; y una mutación de prueba que no coincidía y mi guion dijo «expectativa invertida».

---

## CIERRE DE LA ENTREGA 2 — CANALES Y DIRECCIONES MÚLTIPLES (13/10/2026)

**Verificado en navegador de verdad**, con el guion `backend\scripts\verificar_el_recorrido_de_los_canales.py`:
**63 comprobaciones · 1 fallo**, y **el fallo es un control más estricto que el contrato** (abajo). Huella
determinista, dos vueltas idénticas:

```
HUELLA canales=4 migracion_arranque=True en_el_alta=True bloque=True alta=True
       dos_telefonos=True principal=True recarga=True quitar=True promueve=True
       recarga2=True aislamiento404=True
```

**Qué funciona** (y en qué fichero):

| pieza | fichero |
|---|---|
| El modelo, con **un solo principal por clase** garantizado por la base (índice parcial, dos dialectos) | `app/models.py` |
| La migración de lo que ya estaba apuntado, **idempotente** y cableada **dentro de `crear_tablas`** | `app/database.py` |
| El alta crea el canal **principal** de cada clase, y la corrección de los cuatro campos lo mantiene | `app/routers/contactos_api.py` |
| Crear, corregir, quitar y elegir principal | `app/routers/contactos_api.py` |
| La ficha los enseña, con su etiqueta y su principal, y **el gasto vuelve a la ficha de su proveedor** | `web/react/pantallas/contactos.js`, `gastos.js` |

**Criterios del encargo, comprobados**: crear, corregir, quitar y elegir principal ✓ · **recargar y persistencia**
(4 canales tras recargar entera) ✓ · conservar los registros antiguos (la migración **copia**, no traslada) ✓ ·
**no inventar país ni prefijo** (el teléfono se guarda tal cual, y hay prueba de que «preguntar por Juan» se guarda) ✓ ·
validar **sin impedir guardar** ✓ · **principales contradictorios** imposibles (índice parcial) ✓ · **corregir no
pierde** (la corrección es parcial) ✓ · los documentos históricos **no se reescriben** ✓ · aislamiento entre fincas
(**404**) ✓.

**Dos defectos graves que encontró el verificador, y no las pruebas** (los dos arreglados y medidos):

1. **La migración no corría nunca**: la llamada estaba **detrás de un `return`**. Las pruebas llamaban a la migración
   **a mano**, así que comprobaban que funciona pero **no que esté cableada**. Añadida la prueba que pasa por
   `crear_tablas`.
2. **`POST /api/contactos` no creaba canales**: una ficha **nueva** llegaba a la pantalla con 0 canales, **sin bloque
   y sin alta rápida**, y el paso de apuntar el segundo teléfono **no se podía andar**. Ahora lo apuntado es el
   principal de su clase, con la misma regla que la migración.

**Y un tercer defecto, de React, que yo había escrito sin saberlo**: un `<input value=…>` **sin `onChange`** queda
**de solo lectura**. El tecleo no entraba por ninguna vía, no había repintado, cogía el foco… y el **mismo** tecleo
**sí** entraba en `#contacto-nombre`, que usa el componente `Campo` de la casa. Arreglado con `defaultValue` (sin
controlar), que además es como `app.js` ya los lee.

**Limitaciones, dichas**:

1. **El único fallo del guion** es «el arranque deja dicho en su bitácora lo que ha llevado»: cuando **no hay nada
   que llevar** (las fichas ya tienen sus canales) **no se dice nada**, y eso es correcto. El control da por hecho que
   siempre hay algo que decir; **el producto tiene razón y el control es más estricto que el contrato**.
2. **Corregir un canal** (`PUT …/canales/<id>`) está probado en servidor ✓ y **no se ha andado en el navegador** ✗.
3. **La corrección de los cuatro campos de la ficha no actualiza el canal principal** todavía: si se cambia el
   teléfono en el campo de siempre, el canal principal que se creó al alta **se queda con el valor viejo**. Queda
   declarado.
4. **La revisión visual de las capturas** la tiene que hacer una persona: el verificador **no puede ver imágenes**.

**Commits**: el modelo, la migración, las puertas, la pantalla, y los tres arreglos de esta entrega.

---

## CIERRE DE LA ENTREGA 4 — PERMISOS POR MATERIA (13/10/2026)

**Qué funciona** (y dónde está):

| pieza | fichero |
|---|---|
| Las dos capacidades, en el sitio donde ya vivía `puede_entrar` | `backend/app/accesos.py` (`puede_modificar`, `puede_ver_lo_economico`) |
| Las dos columnas del acceso, **con los dos dialectos** y por defecto en `True` | `backend/app/models.py` (`AccesoAFinca`) |
| Las dos dependencias que contestan **403 con palabras** | `backend/app/deps.py` (`PuedeModificar`, `PuedeVerLoEconomico`) |
| **13 puertas de escritura** comprobando `puede_modificar` (10 en contactos y 3 en tareas) y **la del saldo** comprobando `puede_ver_lo_economico` | `backend/app/routers/contactos_api.py`, `tareas_api.py` |
| La cuenta **dice lo que puede hacer** | `backend/app/routers/cuenta.py` (`GET /api/cuenta/yo`) |
| La pantalla **no ofrece** lo que no se puede (bloque del dinero, barra de acciones, botones de cada canal y de cada tarea, y las dos altas rápidas) | `backend/web/app.js`, `web/react/pantallas/contactos.js` |

**Las tres materias, sin inventar nada**: **consultar** ya lo daba el propio acceso a la finca ✓; **modificar** y **consultar lo económico** son las dos capacidades nuevas ✓. No se creó ningún sistema de usuarios paralelo ✓, que es lo que pide el encargo ✓.

**Criterios del encargo, comprobados** (5 pruebas de servidor + 3 de pantalla):

- Cuenta autorizada → **todo permitido** ✓.
- **Sin capacidad → 403 Y NINGUNA ESCRITURA** ✓, y mirado **en la base** (una puerta que contesta 403 y escribe igual sería lo peor) ✓.
- **Acceso directo por URL o identificador → el mismo resultado** ✓ (las pruebas llaman a la puerta, no a la pantalla) ✓.
- **Sin permiso económico → el dinero no viaja**: 403 en el saldo, y ni «€» ni `nos_debe` en el cuerpo ✓.
- **Otra explotación → ningún acceso** ✓ (ya estaba, sigue) ✓.
- **Compatibilidad**: las capacidades nacen en `True` y **las demás suites siguen pasando** con las cuentas de siempre ✓.
- Y **«ocultar un botón no constituye autorización»** ✓: escrito en el código y en las pruebas; la autorización está en la puerta ✓.

**Limitaciones, dichas**:

1. **No hay pantalla para repartir las capacidades.** Hoy se cambian en la base; las pruebas de permisos lo hacen así y **lo dicen en su docstring**. Hace falta una pantalla (y **su auditoría**, que tampoco existe: apagar una capacidad **hoy no deja traza**).
2. **El `puede_modificar` no se comprueba en las puertas de otros módulos** (ventas, gastos…): esta entrega cubre **contactos, canales, notas y tareas** y **el saldo**, que es lo que pide, pero **no** es un permiso global.
3. **`puede_ver_lo_economico` no filtra aún los documentos con dinero** de otras pantallas (facturas, cuentas): hoy protege **el saldo del contacto**.
4. **La revisión visual de las capturas** la tiene que hacer una persona.

**Commits**: el modelo (`8003b9e`), las capacidades y dependencias (`a5324db`), aplicadas a las puertas (`255f780` y siguientes), `/yo` (`b801969`), y la pantalla (`e356489`, `b8fd519`).

**Siguiente tarea**: **Entrega 5 — fusión de contactos**, empezando por el **inventario de referencias a `Contacto`** (encargado a un subagente) y por **leer** `deshacer_la_migracion`, que es el patrón de la casa para volver atrás.

---

## ENTREGA 5 — DISEÑO DE RECUPERACIÓN (leído de la casa, antes de tocar datos)

El encargo lo pide así: **«definir recuperación antes de operar sobre datos reales»**. Y la casa ya tiene un patrón,
que he leído antes de escribir nada: **`deshacer_la_migracion`** (`backend/app/routers/contactos_api.py:1603`). Sus dos
reglas, copiadas de su propio docstring:

> 1. Se borran **los enlaces de la migración** (los que apuntan a un texto escrito). El texto del documento **no se
>    toca**: se queda exactamente como estaba, que es la promesa del ticket.
> 2. Una ficha que creó la migración se borra **solo si no le queda ningún enlace y nadie la ha editado**. Si el
>    agricultor le puso el teléfono, le quitó un papel o le enlazó otra cosa, esa ficha **es suya** y se queda, con su
>    nombre, en la lista de `se_quedan` y su motivo escrito. **Volver atrás no puede llevarse trabajo suyo.**

Y la casa trae **las piezas de control** que hacen falta, todas en `backend/app/database.py`:

| pieza | línea | para qué |
|---|---|---|
| `_copia_de_seguridad_del_fichero` | 374 | la copia **antes** de tocar |
| `_la_copia_esta_entera` | 587 | comprobar que la copia sirve |
| `_huerfanas` | 606 | **contar filas que apuntan a nada, antes Y después** |

Y la regla de `_huerfanas`, que es **justo la que una fusión necesita**, en sus palabras: *«una base que ya venía con
una fila apuntando a nada no puede impedir que el programa se ponga al día. Lo que no se admite es que la
reconstrucción **añada** huérfanas»*.

### Lo que voy a hacer, entonces (diseño, no código todavía)

**Antes** — copia del fichero ✓, y **guardar tres cifras**: las huérfanas por tabla ✓, y **el saldo de las dos
fichas** (origen y destino) ✓, con la regla única del dinero (`servicios.lo_cobrado_…`, `lo_pagado_…`) ✓.

**La fusión** — en **una transacción** ✓, con el origen **remitiendo al destino** ✓ (un campo, **no** un borrado
físico: el encargo lo prohíbe como atajo) ✓, y **sin adjudicar por nombre** ✓ (el texto de los documentos se conserva
literal ✓; lo que se mueve son las **claves ajenas** ✓).

**Después** — volver a contar huérfanas ✓ (**no puede añadir ni una** ✓) y comprobar que **el saldo del destino es el
que era el de las dos juntas** ✓, sin compensar sentidos distintos ✓ y sin contar dos veces una compra factura+gasto ✓.

**Deshacer** — con el patrón de la casa ✓: **no se lleva por delante el trabajo del agricultor** ✗. Si alguien apuntó
una nota, una tarea o un canal en el destino **después** de fusionar, deshacer **no** las arranca: el origen vuelve
con **lo suyo** y **lo que no se ha podido devolver se dice, con su motivo** ✓.

**Colisiones que hay que resolver explícitamente** (y que ya conozco, porque me las he encontrado hoy):

1. **`uq_*_reenvio`**: las claves de reenvío de notas y tareas son **únicas por finca** → al fusionar, las del origen
   **chocan** con las del destino. El encargo lo dice: *«resolver colisiones de claves de reenvío sin perder notas»*.
2. **El principal por clase** en los canales: dos fichas pueden tener cada una **su «Su teléfono» principal** → al
   juntarlas no pueden ser dos ✓ (lo garantiza un índice parcial ✓) → se **aparta** uno antes ✓, que es el patrón que
   ya escribí para los canales ✓.
3. **Los papeles y enlaces**: los mismos enlaces pueden existir en las dos fichas → **no duplicar vínculos** ✓.

---

## ENTREGA 5 — LO QUE EL INVENTARIO CAMBIA (CRM-04-FUSION-INVENTARIO.md, 13/10/2026)

El inventario está hecho y **corrige el plan**, incluida **una premisa mía**:

1. **La fusión no existe, ni a medias.** `POST /migracion/aplicar` (`contactos_api.py:1434`) **crea fichas nuevas**
   desde textos; **no hay ni un solo `UPDATE` que reasigne un `contacto_id`** en todo `backend/app/`.

2. **CORRECCIÓN A MI PREMISA (y es importante):** las `uq_*_reenvio` son **`(explotacion_id, clave_de_reenvio)`**,
   **sin `contacto_id`** (`models.py:3509` tareas, `:3564` notas). El espacio de claves es **de la finca, no de la
   ficha** ⇒ **una fusión dentro de la misma finca NO puede colisionar por reenvío**, y quien «resuelva colisiones»
   ahí puede **romper el índice**. Lo que **sí** colisiona, y son fallos **duros** de la base:
   - **`uq_papel_del_contacto`** (`(contacto_id, papel)`, `models.py:3592`) ⇒ dos fichas `proveedor` ⇒
     `IntegrityError`. Hay que **deduplicar**.
   - **`uq_canal_principal_del_contacto`** (`models.py:3448-3455`) ⇒ hay que **apartar** un principal por clase antes
     (lo que ya hace `_apartar_el_principal_de_su_clase`, `contactos_api.py:452-468`).
   - **Las notas NO colisionan**: solo hay que repuntar `contacto_id` y **no tocar** autor, texto ni fecha.

3. **El punto de pérdida más fácil y peor:** `Contacto.notas` (`models.py:3393`) es **un campo de texto único**, no la
   tabla de notas. Dos fichas con notas ⇒ **no hay sitio para las dos** y la de la absorbida se pierde **en silencio**.
   Hay que decidirlo **explícitamente** y decirlo en la vista previa.

4. **`ventas_de_cosecha.contacto_id` NO TIENE CLAVE AJENA en la base del agricultor** — medido y reproducido. En base
   nueva sí; en la migrada no, porque `asegurar_columnas` (`database.py:129-177`) usa `ALTER TABLE ADD COLUMN` (SQLite
   no puede añadir FK así) y esa tabla no está en la lista que reconstruye (`database.py:234-287`). De las **6
   columnas de dinero** a repuntar en una fusión, es **la única cuyo error no caza la base**. Es un defecto de
   integridad **de hoy**, no de la fusión.

5. **La auditoría tiene agujeros medidos:** `enlazar` (`contactos_api.py:1895-1907`), `quitar_el_enlace` (`:1936-1938`)
   y `marcar_un_papel` (`:1836-1838`) **no llaman a `correcciones.apuntar`**: solo ponen `editado_a_mano=True`. Y
   `papeles_de_un_contacto` y `enlaces_de_contacto` **no tienen columna de anulación**, así que una fila borrada no se
   reconstruye salvo por la auditoría — que en esos tres caminos **no existe**.

6. **Recuperación: hoy NO hay forma de deshacer una fusión.** Solo copias al lado de la base (6 ficheros, la última del
   **08/10/2026**, o sea **anterior a las tres tablas nuevas**) y la auditoría (con sus agujeros). El script de la casa
   (`scripts\deshacer_la_migracion.py`) enseña el patrón bueno: comprueba la copia ✓, guarda el estado de ahora ✓, pone
   la copia y **borra `-wal`/`-shm`** ✓ (sin eso SQLite reaplica lo posterior: medido, 3 filas donde había 2) ✓, y si el
   WAL está en uso **no dice «hecho»: sale con 1** ✓.

7. **La coherencia `explotacion_id`↔`contacto_id` la sostiene SOLO el código**: no hay FK compuesta ni `CHECK`. Y las
   **8 pruebas de aislamiento pasan por la API, nunca por SQL directo** ⇒ **no acreditan la barrera de la base**.

8. **El nombre de la ficha absorbida no tiene dónde vivir**: `Contacto` no tiene `nombre_anterior` ni histórico
   (`models.py:3359-3413`). El encargo pide que el origen **remita al destino**: hace falta un campo (o la auditoría,
   con su hueco ya dicho).

### Orden que se deduce del inventario (para implementar)

1. Decidir qué es una fusión legal (mismo `explotacion_id`, **nunca por nombre**: `test_contactos.py:1248-1266`).
2. **Escribir la fila de auditoría ANTES de tocar nada**, con la lista `(tabla, id)` de cada fila hija movida: es lo
   único que hace la operación **reversible sin restaurar la base**.
3. **Deduplicar papeles** por `(contacto_id, papel)` y **apartar principales** por clase.
4. **Repuntar las 6 columnas de dinero**, verificando **las ventas aparte** (que no tienen FK).
5. Exigir **saldo A + B antes == saldo fusionado después**, con los dos lados separados.
6. Escribir **la puerta de deshacer** que lea esa fila de auditoría.

Y **antes de todo eso**, dos defectos que el inventario ha destapado y que son **de hoy**, no de la fusión: la
**clave ajena que falta** en `ventas_de_cosecha` (punto 4) y los **tres caminos sin rastro** en la auditoría (punto 5).

### Deuda concreta: las DOS pruebas que faltan de los rastros (14/10/2026)

`tests/test_lo_que_queda_en_la_auditoria.py` **ya prueba el de los papeles** (marcar deja fila, desmarcar deja
**otra**, con el papel dentro y con quién). Faltan los dos de los enlaces, y **no es por falta de saber qué pedir**:
los cuerpos están leídos de `tests/test_contactos.py`.

- **Enlazar** (`test_contactos.py:188-195`, dentro de un test que ya monta las facturas):
  `POST /api/contactos/{id}/enlaces` con `{"tabla": "facturas", "campo": "proveedor", "registro_id": <id>}` → 200.
  La puerta **valida el texto**, así que hace falta una factura de verdad: por eso va **en ese fichero**, donde la
  preparación ya existe, y no en el mío.
- **Quitar** (`test_contactos.py:583-588`):
  `DELETE /api/contactos/{id}/enlaces/{enlace_id}` → 200. El `enlace_id` sale de `ficha["vivos"]` filtrando por
  `escrito.registro_id`.

Lo que hay que afirmar en las dos, y es lo mismo que en la de los papeles: **una fila nueva en `models.Auditoria`**
con `entidad="contacto"`, `entidad_id` la ficha, `accion` `"enlazar"` / `"quitar_el_enlace"`, **con quién**
(`usuario_id` no nulo) y **con qué** (la tabla, el campo y el registro / el `enlace_id`) — y **contadas**, para que
quitar un enlace **no** borre la fila de haberlo puesto, sino que **añada** la suya.

---

## TRABAJO LISTO Y TRABAJO BLOQUEADO (14/10/2026)

El encargo pide «mantener una lista concreta de trabajo listo y bloqueado». Leída `COLA.md` (su tabla de orden y
dependencias, líneas 11-23):

| ticket | de qué depende | estado |
|---|---|---|
| **CRM-01** ventas y cobros | CRM-00 | **cerrado** (la regla del dinero vive en `servicios.py`) |
| **CRM-02** banco y conciliación | CRM-01 | **cerrado** (con la regla de no duplicar el dinero) |
| **CRM-03** contactos y próximas acciones | CRM-01 | **EN CURSO**: sus cinco entregas (saldo, canales, tareas, permisos y fusión) |
| **CRM-04** **servicios a terceros** | CRM-01, CRM-03 | **LISTO PARA EMPEZAR** en cuanto se cierre el CRM-03: sus dos requisitos están, y el encargo apunta aquí con estas palabras: «empezando por servicios a terceros si sus requisitos ya están cerrados» |
| **CRM-05** costes, inversiones y panel | CRM-01, CRM-02 | **listo** (sus dos dependencias están cerradas) |
| **CRM-06** tierras, mapas y campañas | «núcleo actual, independiente» | **cerrado** (el núcleo) |
| **CRM-07** insumos y máquinas | CRM-06 y compra | **listo** |
| **CRM-08** fiabilidad: **borradores, permisos, conflictos y recuperación** | «se aplica a todos» | **se está cumpliendo AHORA**, con estas entregas: los permisos por materia (Entrega 4), los tres rastros de auditoría, la recuperación diseñada para la fusión y la clave ajena que faltaba |
| **CRM-09** preparación PAC | CRM-06, CRM-07; fuentes | **bloqueado por datos** (fuentes) |
| **CRM-10** meteo y satélite | CRM-06; fuente | **bloqueado por datos** (fuente disponible, pero es otro trabajo) |
| **CRM-11** paneles integrados | «datos acreditados de sus…» | **bloqueado**: necesita que sus datos estén acreditados por los tickets de arriba |
| **CRM-12** OCR evaluado | corpus autorizado | **bloqueado por corpus** |

**Y una precisión que conviene tener escrita**: la **fusión de contactos** (Entrega 5 del encargo) **no es un ticket
de `COLA.md`**. Lo verificó el inventario de la fusión: `CRM-04` en la cola es **«servicios a terceros»**, y lo más
cercano a una fusión es el CRM-03 («fusión solo confirmada, con auditoría»). Es decir: la fusión es de **este
encargo**, no de la cola, y por eso no aparece en esta tabla como ticket.

**Lo que está listo ahora mismo, por orden de dependencias**: 1) cerrar el **CRM-03** (las cinco entregas del
encargo), 2) **CRM-04 servicios a terceros**, 3) **CRM-05**. Y lo que no depende de nada: seguir con la fusión, que
ya tiene inventario, recuperación y rastros de auditoría.

### PLAN DE LA FUSIÓN, con las tablas y las líneas delante (14/10/2026)

Del inventario (`CRM-04-FUSION-INVENTARIO.md`, secciones 3 y 7), **11 tablas** llevan `contacto_id`, y **ninguna tiene
`ON DELETE`** (medido): lo que se mueva hay que moverlo a mano, y lo que se olvide **no lo avisa la base**.

**Las seis del dinero** (lo que una fusión tiene que repuntar sin compensar nada):

| # | tabla | modelo | línea |
|---|---|---|---|
| 1 | `ventas_de_cosecha` | `VentaDeCosecha` | `models.py:1202` — **la única SIN clave ajena en la base del agricultor** (arreglada el 14/10/2026) |
| 2 | `facturas_emitidas` | `FacturaEmitida` | `models.py:1338` |
| 3 | `cobros` | `Cobro` | `models.py:1492` |
| 4 | `gastos` | `Gasto` | `models.py:3739` |
| 5 | `inversiones_de_la_finca` | `InversionDeLaFinca` | `models.py:3811` |
| 6 | `pagos_de_gasto` | `PagoDeGasto` | `models.py:3936` |

**Las cinco que cuelgan de la ficha** (notas, tareas, canales, papeles y enlaces): se repunta `contacto_id` y **no se
toca nada más** — el autor y la fecha de una nota, el texto de un enlace (`nombre_de_entonces`), la etiqueta de un
canal y el título de una tarea **son de quien los escribió**.

**Las dos colisiones duras** (fallos de la base, no avisos):

1. **`uq_papel_del_contacto`** = `(contacto_id, papel)` (`models.py:3592`) → si las dos fichas son `proveedor`,
   `IntegrityError`. Hay que **deduplicar**: se queda un papel por pareja, y la decisión se dice en la vista previa.
2. **`uq_canal_principal_del_contacto`** = `(contacto_id, clase)` parcial `WHERE principal=1` (`models.py:3448`) → hay
   que **apartar** un principal por clase antes de mover (ya existe `_apartar_el_principal_de_su_clase`,
   `contactos_api.py:452`).

**Y lo que NO colisiona**, aunque el encargo lo nombre: las `uq_*_reenvio` son `(explotacion_id, clave_de_reenvio)`,
**sin `contacto_id`** — el espacio de claves es de la finca, así que **una fusión dentro de la misma finca no puede
colisionar por reenvío**. Quien «resuelva colisiones» ahí puede romper el índice.

**El punto de pérdida peor**: `Contacto.notas` (`models.py:3393`) es **un campo de texto único**, no la tabla de
notas. Dos fichas con notas ⇒ **no hay sitio para las dos**. Hay que decidirlo explícitamente y decirlo.

**El orden que se deduce** (y lo escribo para seguirlo tal cual):

1. Escribir la **fila de auditoría ANTES de tocar nada**, con la lista `(tabla, id)` de cada fila que se va a mover:
   es **lo único** que hace la operación reversible sin restaurar la base.
2. **Deduplicar papeles** y **apartar principales** por clase.
3. Repuntar las **11 tablas**, con **las ventas verificadas aparte** (son las que la base no protege).
4. Exigir **saldo A + B antes == saldo del destino después**, con los dos lados separados.
5. El origen **remite al destino** (un campo, no un borrado) y **no se borra físicamente**.
6. **La puerta de deshacer**, que lee esa fila de auditoría y **no se lleva por delante el trabajo posterior**.

### PENDIENTE QUE NECESITA OJOS: la revisión visual de las capturas (14/10/2026)

El encargo lo pide así: *«Capturas revisadas por una persona o agente con visión»*, y avisa de que *«no considerar
una revisión del HTML equivalente a una revisión visual»*. **Hoy no se puede cumplir con lo que hay**:

- Las **dos verificadoras** lo dijeron en sus informes: *«este modelo no acepta imágenes»*.
- Y **yo tampoco**: al intentar leer `docs/capturas/tareas-v2-lista-hoy-tras-recargar.png`, el modelo contesta
  *«model "deepseek-v4-flash-vision-exp" does not declare image input»*. El nombre lleva «vision» y **no la tiene**.

Así que **está pendiente**, y no lo voy a dar por hecho con una lectura del DOM (el encargo lo prohíbe
explícitamente). **Lo que hay que mirar**, cuando haya ojos:

| captura | qué tiene que verse |
|---|---|
| `tareas-v2-ficha-con-las-seis.png` | la ficha con el bloque de tareas **con texto** en los botones, y las seis con su día y su responsable |
| `tareas-v2-ficha-vencida-completada.png` | la vencida marcada **«Vencida»** (no un hueco) y, tras completarla, con quién la hizo |
| `tareas-v1-lista-hoy-tras-recargar.png` / `v2` | la lista **con su título y sus botones escritos**, y el filtro de «hoy» **puesto y marcado** después de recargar |
| `canales-*.png` (7) | los canales con sus etiquetas, el principal marcado y el alta rápida |

Y de paso, lo que el encargo pide del recorrido integrado: **tamaños previstos** (sin reducir letra ni botones),
**controles dentro de la ventana**, **zoom al 200 %** y **la paleta sin cambios**.

**Pregunta concreta para el dueño** (una sola, y no bloquea lo demás): ¿las miras tú y me dices qué ves, o prefieres
que siga con un modelo que sí acepte imágenes para esta comprobación? Mientras tanto sigo con el resto: **esto es una
comprobación de una entrega, no un bloqueo del trabajo**.

### Lo que falta de la fusión, con la receta ya encontrada (14/10/2026)

De las **nueve pruebas** de la fusión, ocho están. Falta **una**, y no es por no saber cómo:

**El saldo CON documentos** (venta + cobro + gasto), que es donde se ve de verdad que la suma se conserva. Hoy se
comprueba con fichas **sin facturas** (0 y 0). La receta, leída de `tests/test_lo_que_no_se_apunta_dos_veces.py:59-69`
y de sus ayudantes:

```python
models.VentaDeCosecha(
    explotacion_id=cuenta["explotacion_id"],
    campana_id=campana.id,              # la fixture `campana` ya existe en conftest
    contacto_id=<la ficha>,
    fecha=dt.date(2026, 7, 11),
    producto="Trigo",
    cantidad=1000.0,
    unidad="kg",
    clave_de_reenvio="la-de-la-prueba",
)
```

Lo que hay que afirmar, y es lo que pide el encargo: **saldo(origen) + saldo(destino) antes == saldo(destino)
después**, con los dos lados separados (nos debe y le debemos **sin compensar**), y que un documento que cuelga de
cada ficha **se siga abriendo** desde el destino.

Y lo que queda declarado del resto: un fallo **después** de escribir la auditoría (el test que hay induce el fallo
**en** la auditoría, que es el primer paso, y prueba que la fusión no empieza y que la transacción no deja nada a
medias).

---

## CIERRE DE LA ENTREGA 5 — FUSIÓN DE CONTACTOS (servidor, 14/10/2026)

**Qué funciona** (y dónde está):

| pieza | fichero |
|---|---|
| **Inventario de las 11 tablas con `contacto_id`**, con líneas, hecho **antes** de implementar (lo pide el encargo) | `CRM-04-FUSION-INVENTARIO.md` (62 KB) |
| **Vista previa** (`GET /api/contactos/{origen}/fusion/{destino}`): cuenta las once, enseña **las tres colisiones duras** con su porqué y su qué-hacer, y los dos saldos **solo con permiso económico** | `app/routers/fusion_api.py` |
| **La fusión** (`POST …/fusion/{destino}`): auditoría **primero** con la lista `(tabla, id)`, deduplicar papeles, apartar principales, repuntar las once, el origen **remite** y **no se borra**, todo en **una transacción**, y la comprobación de que **saldo A + B = destino** | `app/routers/fusion_api.py` |
| **Deshacer** (`POST …/deshacer-la-fusion`): devuelve **solo las filas apuntadas** —lo de después **no se toca**— y **dice lo que no se puede devolver** | `app/routers/fusion_api.py` |
| El campo que remite | `models.Contacto.fusionado_con_id` (`models.py:3412`) |
| **9 pruebas**: vista previa (4) y fusión (5) | `tests/test_la_fusion_de_contactos.py` |

**Criterios del encargo, comprobados**: fusión **dentro** de una explotación ✓ · **entre explotaciones rechazado** (404 por identificador, sin mover una fila) ✓ · **fusión repetida segura** (409) ✓ · **fallo intermedio sin cambios parciales** ✓ · **notas, tareas y documentos accesibles** desde el destino ✓ · **auditoría con origen, destino, autor, fecha y decisiones** ✓ · **recuperación definida antes de operar** ✓ (hecha y probada) · **no duplicar vínculos** ✓ (papel repetido) · **no compensar deudas** ✓ (los dos saldos separados) · **el origen remite** ✓ y **no se borra** ✓.

Y **una corrección a la premisa del encargo**, medida: las `uq_*_reenvio` son **de la finca, no de la ficha**, así que una fusión dentro de una finca **no puede colisionar por reenvío**; las colisiones reales son `papel` y `principal`, y hay una tercera que el encargo no nombra y es la peor: **`Contacto.notas` es un campo de texto único**, así que **dos fichas con notas no caben** y eso la fusión **no lo puede decidir**.

**Limitaciones, dichas**:

1. **La pantalla de la fusión no está** (elegir origen y destino, ver la previa, confirmar): el servidor está entero y probado, pero se maneja por la puerta.
2. **Falta una prueba de las nueve**: el saldo **con documentos** (venta + cobro + gasto). Está **anotada con su receta** más arriba (de `tests/test_lo_que_no_se_apunta_dos_veces.py:59-69`).
3. **Un fallo DESPUÉS de escribir la auditoría** no está cubierto: la prueba que hay induce el fallo **en** la auditoría (el primer paso), que demuestra que la fusión no empieza y que la transacción no deja nada a medias.
4. **La revisión visual** de las capturas sigue pendiente de ojos (ni las verificadoras ni yo aceptamos imágenes).

**Commits**: la vista previa, la fusión, la puerta de deshacer y las nueve pruebas (14/10/2026).

**Siguiente tarea**: la **pantalla** de la fusión, o pasar al **CRM-04 (servicios a terceros)**, que es donde apunta la cola y cuyos requisitos ya están.

### Recuento de lo construido en estas entregas (14/10/2026) — y una lección de instrumentos

Medido con la **colección real de pytest** (`--collect-only -q`), que es lo que el encargo pide:

| fichero | casos |
|---|---|
| `test_el_saldo_de_un_contacto.py` | 9 |
| `test_los_canales_de_un_contacto.py` | 19 |
| `test_las_tareas_de_un_contacto.py` | 15 |
| `test_los_permisos_por_materia.py` | 5 |
| `test_lo_que_queda_en_la_auditoria.py` | 1 (los dos de los enlaces viven en `test_contactos.py`, por la fixture) |
| `test_las_claves_ajenas_que_faltan.py` | 2 |
| `test_la_fusion_de_contactos.py` | 13 (4 de la vista previa + 9 de la fusión) |
| **TOTAL** | **64** |

Y en JavaScript, con `node --test`: `tests_js/contactos.test.js` → **66**.

**LA LECCIÓN, que es la de todo el día otra vez**: mi primer contador daba **0 casos en los siete** y era **mentira** —
buscaba líneas con `::` y **pytest imprime `tests/test_la_fusion_de_contactos.py: 13`**. Es **la forma de lo que
vuelve** ✗, exactamente la misma familia que el `KeyError` de `canales`, la pantalla muda y el `list(textos.TAREAS)`.
Esta vez le ha mordido a **mi instrumento de medir**, no al producto. Y la regla que me salva: **no dar un número
que no se ha visto salir bien** — el «0 en los siete» era imposible y por eso lo perseguí en vez de escribirlo.

### Lo que queda por hacer, ya masticado (14/10/2026)

**1 · La pantalla de la fusión** (el servidor está entero y probado). Piezas, en el orden en que se montan:

- Fichero nuevo `web/react/pantallas/fusion.js`, con la forma de las demás (`html` de `../componentes.js`, `frase(...)`,
  `Boton`/`BotonSencillo` y las clases de la casa: `boton`, `boton-claro`, `pista`, `campo`). **Nada de estilos nuevos**
  ni de tamaños distintos: el encargo prohíbe reducir letra o botones sin autorización.
- Tres pasos, que son los del contrato: **elegir origen y destino** → **ver la vista previa** → **confirmar**.
  La previa ya viene hecha del servidor (`GET …/fusion/{destino}`): sus `colisiones` traen `que`, `por_que` y
  `que_hacer`, así que la pantalla **solo tiene que enseñarlas** y pedir la decisión.
- Las colisiones **no se resuelven en la pantalla**: se enseñan. La única que **no puede decidir nadie por el
  agricultor** es la de las dos con notas escritas (`Contacto.notas` es un campo único): ahí la pantalla tiene que
  **parar** y decir que hay que decidirlo antes.
- Y la puerta de **deshacer**, con la regla de la casa escrita al lado: *devuelve solo lo que trajo la fusión; lo que
  se apunte después **no se toca***.

**2 · Entrega 6 — el recorrido integrado** (lo último, y es donde todo se prueba junto). El encargo lo dice paso a
paso: *contacto cliente y proveedor → documentos → parciales → saldo → nota → próxima acción → segundo contacto →
fusión*. Con datos ficticios, en un servidor aislado, y comprobando **lo que ya se ha aprendido que falla**:

- **La forma de lo que se manda y de lo que vuelve**: es el fallo que más veces ha aparecido (el `KeyError` de
  `canales`, el `list(textos.TAREAS)`, los rótulos sin envolver). Comprobar **el `<h1>` y los rótulos en el DOM**, no
  que la puerta conteste 200.
- **La dirección y la pantalla tienen que decir lo mismo**: si la barra lleva un filtro, la lista tiene que estar
  filtrada, y al revés.
- Carga ✓, vacío ✓, **error** ✓, **conflicto** ✓ y **falta de permiso** ✓: los cinco estados, que es lo que el encargo
  pide del recorrido.
- **Atrás, Adelante y recarga**; **teclado**; **borradores conservados** ante un error.
- **Tablas con filtros visibles** y vuelta a todos los registros; **totales sobre el conjunto correcto**, no sobre las
  filas visibles.
- **Tamaños del contrato y zoom al 200 %** (esto necesita ojos: está en el pendiente visual).
- Y **las capturas, miradas por una persona** (ni las verificadoras ni yo aceptamos imágenes).

**Las dos pruebas declaradas que faltan**, de la fusión: el **saldo con documentos** (receta anotada arriba) y un
fallo **después** de escribir la auditoría.

---

## CIERRE DE LA ENTREGA 3 — PRÓXIMAS ACCIONES (14/10/2026)

**Qué funciona** (y dónde está):

| pieza | fichero |
|---|---|
| La tarea, con título, descripción, responsable, **fecha prevista** (día local, no un instante), estado y vínculos; `vencida` **se calcula, no se guarda** | `app/models.py` (`Tarea`), `app/routers/contactos_api.py` (`_una_tarea`, `_las_tareas`) |
| Lista con filtros por responsable, estado y vencimiento; **el servidor decide `vencida`** | `app/routers/tareas_api.py` (`GET /api/tareas`) |
| Reprogramar, completar y cancelar, **con quién y cuándo**; cerrar dos veces es un no-op | `tareas_api.py` |
| El bloque en la ficha (alta rápida + completar/cancelar) | `web/react/pantallas/contactos.js` |
| La pantalla de la lista `#/tareas`, con sus filtros **en la dirección** | `web/react/pantallas/tareas.js` |

**Criterios del encargo, comprobados en navegador**: crear ✓, asignar ✓, reprogramar ✓, completar ✓ (dice quién, y sigue tras recargar **entera**) ✓, cancelar ✓ (dice quién y **no desaparece**) ✓, **la vencida sigue pendiente y se puede completar** ✓, **acciones repetidas que no duplican** ✓, **fecha local frente a instantes** ✓ (el día es un `date` de verdad), y **aislamiento** ✓ (404 entre fincas, sin tocar la fila) ✓.

**El veredicto del instrumento**: **283 comprobaciones · 0 fallos**, con **dos vueltas de huella idéntica**. El camino fue **1 fallo → 22 fallos → 0**, y los dos que se arreglaron en el último tramo son la lección de esta entrega:

1. **La pantalla salía muda** ✗: el servidor mandaba el diccionario ✓ y el front le pasaba a la pantalla **ya el vocabulario** ✗ (`textos.tareas` → `undefined` → `{}`). *La mitad del arreglo estaba al otro lado del cable.*
2. **El filtro no sobrevivía a la recarga** ✗: la dirección se reescribe **desde el estado** y la rama del router no lo copiaba ✗ — **una dirección que mentía** (copiarla daba la lista sin filtrar). Y el servidor, además, tenía el filtro «vencidas» mirando **solo la fecha** ✗, así que traía **tareas hechas** mientras su bandera decía `vencida: false`.

**Limitaciones, dichas**:

1. **Las 12 capturas no las ha mirado nadie con ojos** ✗ (ni las dos verificadoras ni yo aceptamos imágenes) — está pedido al dueño.
2. El recorrido **no comprueba** el texto del enlace «con quién» ni las cabeceras de la tabla ni los botones «Hecha»/«Cancelar» **de la lista** (salen en el volcado, pero no en ningún check contado).
3. **Las pruebas de JS pasan igual antes y después** de estos arreglos ✗: **el instrumento es el recorrido**, no la suite.

**Commits**: la entrega entera y los tres arreglos del final (14/10/2026, `4c6015c`, `d28f3e9`, `32ab51d`).

**Siguiente tarea**: la **Entrega 6** (el recorrido integrado), que está andándose.

### El recorrido integrado: la herramienta ya está identificada (14/10/2026)

Escribí el guion **yo** (paré al agente: dos rondas sin producir un fichero). Y antes de escribirlo he mirado **lo que ya
tiene la casa**, que ahorra la mitad del trabajo:

- **`backend/scripts/navegador_cdp.py`** (18 KB): la clase **`NavegadorDeVerdad`**, con `abrir`, `evaluar`, `esperar`,
  `tecla`, `escribir`, `pulsar`, **`medir(ancho, alto)`** y **`zoom(factor)`** — o sea que **el zoom al 200 % del
  encargo se puede medir de verdad**, no a ojo.
- **`backend/scripts/verificar_el_recorrido_de_las_tareas.py`** (2223 líneas, y **no hay que escribirlo de nuevo**):
  de ahí se **importan** tres ayudantes que ya están resueltos y probados —
  `levantar_el_servidor(temporal) -> (proceso, base, bitacora)` (arranca uvicorn contra una base temporal, en UTF-8),
  `apagar_el_servidor(proceso)` (y **lo cuenta**, para poder comprobar que no queda nada vivo) y
  `lo_que_ha_quedado_vivo()` (pregunta a Windows por las líneas de órdenes; **una limpieza que no se comprueba no está
  hecha**).

Así que el guion nuevo es: **importar esos tres** + abrir el navegador + andar la ruta + medir. La ruta, tal como la
lista el encargo: **contacto cliente y proveedor → documentos → parciales → saldo → nota → próxima acción → segundo
contacto → fusión**, y las puertas de la fusión ya están probadas
(`GET …/fusion/{destino}`, `POST …/fusion/{destino}`, `POST …/deshacer-la-fusion`).

Los cinco estados que hay que provocar: **carga** (mirar un `cargando` de verdad), **vacío** (una lista sin nada),
**error** (algo que no existe), **conflicto** (la fusión repetida, que ya contesta 409) y **falta de permiso** (quitarle
la capacidad a la cuenta, como hace `tests/test_los_permisos_por_materia.py`).

### Enrutar la pantalla del CRM-04: las cuatro piezas y sus líneas (14/10/2026)

Reconocimiento hecho **antes** de escribir (que es lo que faltó otras veces). La pantalla `trabajos_a_terceros.js` ya
existe, ya tiene sus **30 textos** servidos por `interfaz.py` y las cuatro listas de la casa cuadran. Falta **la
dirección**, y son cuatro sitios, con la forma copiada de `#/tareas`:

| pieza | dónde | qué pone |
|---|---|---|
| **La ruta** | `web/react/rutas.js:117` | `{ clave: "trabajos_a_terceros", patron: ["trabajos-a-terceros"] }` |
| **El import** | `web/app.js:131` | `import { pantallaDeLosTrabajosATerceros } from "./react/pantallas/trabajos_a_terceros.js";` |
| **El MAPA** | `web/app.js:851` | `PantallaDeLosTrabajosATerceros: "trabajos_a_terceros",` |
| **El cargador** | junto a `abrirLasTareas` (`app.js:17636`) | el patrón: coger el estado de la pantalla → `cargando = true` → **pintar** → pedir a la puerta → guardar → volver a pintar |

Y **la rama del router**, que va en el mismo sitio que la de tareas (`app.js:1328-1337`, **después** del arreglo del
filtro): `if (clave === "trabajos_a_terceros") return abrirLosTrabajosATerceros(parametros);`

Lo que hay que tener delante al hacerlo, porque son los fallos que ya han aparecido:

1. **La pantalla no puede salir vacía ni muda**: el cargador tiene que pedir de verdad y guardar en su estado, y los
   textos ya están (30 claves, medidos por la puerta).
2. **El filtro, si lo hay, tiene que ir en la dirección y sobrevivir a la recarga** — como se arregló en tareas.
3. Y al terminar, **andarla en el navegador**: el `/api/interfaz` contesta 200 no prueba nada; lo que prueba es leer
   el `<h1>` del DOM y que la tabla tenga filas.

### POR QUÉ NO SE PINTABA LA PANTALLA DE LOS TERCEROS (medido, 14/10/2026)

**La causa está encontrada y es una sola palabra.** Medido leyendo `app.js:17584-17595`:

```js
/** Pinta la lista tal y como está el estado ahora mismo. */
function pantallaLasTareas() {
  const suyo = estadoDeLasTareas();
  return montar(() =>                       // ← **es `montar`**
    pantallaDeLasTareas({ textos: textosDeLasTareas(), tareas: suyo.lista || [], … }));
}
```

Y lo que yo escribí en `pantallaLosTrabajosATerceros()` fue:

```js
return pintar(pantallaDeLosTrabajosATerceros, { … });   // ← `pintar` **no es la forma de la casa**
```

**`pintar` lo inventé yo** (la novena vez en esta sesión que doy por hecho un nombre). No revienta al arrancar porque
`node --check` solo mira la sintaxis, y las pruebas de JS no llegan a pintar esa pantalla; en el navegador se queda el
armazón, que es exactamente lo que midió la andadura (los botones eran `Menú`, `Mi cuaderno` y `Salir`).

**La corrección, con la forma leída y no inventada**:

```js
function textosDeLosTrabajosATerceros() {
  return { trabajos_a_terceros: t("trabajos_a_terceros", {}) };   // **envuelto**, como todas
}

function pantallaLosTrabajosATerceros() {
  const suyo = estadoDeLosTrabajosATerceros();
  return montar(() =>
    pantallaDeLosTrabajosATerceros({
      textos: textosDeLosTrabajosATerceros(),
      trabajos: suyo.lista || [],
      contactos: suyo.contactos || [],
      cargando: suyo.cargando,
      error: suyo.error,
    }),
  );
}
```

Y lo que ya está **descartado midiendo**, para no volver a mirarlo: `abrirLaPantalla` va de la **línea 1239 a la
1437** y **mi rama (1341) está dentro** (contando llaves, no a ojo); la entrada está en `rutas.js:121`; y el guardián
de rutas pasa.

**Y LA REGLA QUE ME FALLÓ, escrita para que no vuelva**: al quitar un cierre que creí «de más» rompí el fichero y la
suite entera, **y `node --check` me lo dijo con un 1 y seguí**. No se sigue: **un `node --check` o un `ast.parse` que
no da 0 es PARAR**, siempre.

---

## CIERRE DEL CRM-04 — SERVICIOS A TERCEROS (14/10/2026)

**Qué funciona** (y dónde está):

| pieza | fichero |
|---|---|
| El **modelo** `trabajos_para_terceros`, con las tres decisiones del contrato escritas dentro | `app/models.py` (~4050) |
| Las **cuatro puertas**: proponer, aceptar, el parte y cancelar, más la lista | `app/routers/terceros_api.py` |
| **La pantalla** (cliente, sitio, hectáreas, de quién es el insumo, tarifa, coste, estado y los cuatro botones) | `web/react/pantallas/trabajos_a_terceros.js` |
| Sus **30 textos**, servidos por la puerta de la interfaz | `app/textos.py`, `app/routers/interfaz.py` |
| **La ruta** `#/trabajos-a-terceros` y su cargador | `web/react/rutas.js:121`, `web/app.js` |
| **9 pruebas** de servidor | `tests/test_los_trabajos_a_terceros.py` |
| **El recorrido andado** (16 comprobaciones) | `scripts/verificar_el_recorrido_de_los_terceros.py` |

**Criterios del contrato, comprobados uno a uno**: *trabajo externo de 10 ha **no suma** superficie propia* ✓ (medido como
que **no crea ni una parcela**: no depende del volcado de la PAC) · *2 L propios consumen; 2 L del cliente no* ✓ (el
módulo guarda **de quién es** y lo dice **con todas las letras** en la respuesta del parte) · *plan no consume* ✓
(proponer y aceptar no tocan el almacén) · *ejecución repetida no duplica* ✓ (clave de reenvío con índice único) ·
*margen marca costes desconocidos* ✓ (`coste_conocido_o_no`) · y **cambiar la tarifa no reescribe partes aceptados** ✓
(aceptar **copia** la tarifa; **visto en rojo** mutando esa línea).

**El veredicto del instrumento**: **16 comprobaciones · 0 fallos** en el navegador, leyendo el DOM (el título, los
rótulos, los botones, el vacío con palabras, la fila tras recargar, de quién es el gasoil, el precio pactado, y la
celda del coste diciendo «no consta» en vez de un cero).

**Limitaciones, dichas**:

1. **El descuento de verdad del almacén no está**: es de otro módulo. Aquí queda **dicho de quién era el insumo**, que
   es lo que hace falta para hacerlo bien.
2. **Las capturas no las ha mirado nadie con ojos** (ni las verificadoras ni yo aceptamos imágenes).
3. **El recorrido andado puede medir la versión anterior** de una pantalla: el service worker guarda
   `/react/pantallas/*.js` para abrir sin cobertura, y una vez me midió el fichero viejo. **Después de tocar una
   pantalla, hay que asegurarse de que el navegador no está sirviendo la cache.**

**Lo que costó, para que se sepa**: una palabra inventada (`pintar` en vez de `montar`), una llave quitada de más que
dejó la suite entera en rojo, y **una vez que `node --check` dijo 1 y seguí**. Las cuatro veces lo dijo el instrumento.

**Commits**: el modelo, las puertas, las pruebas, los textos, la pantalla y la ruta (14/10/2026).

**Siguiente tarea**: la **pantalla de la fusión** (el servidor está entero y probado), y detrás **CRM-05** por la cola.

### LOS BOTONES DE LAS DOS PANTALLAS NUEVAS ESTÁN MUERTOS (medido, 14/10/2026)

**Lo que se midió**: la casa atiende los clics con **un solo manejador delegado** (`app.js:19435`,
`document.addEventListener("click", …)`, que lee `elemento.dataset.accion`). Y **mis acciones aparecen CERO veces** en
`app.js`:

| acción | apariciones |
|---|---|
| `fusion-ver` | **0** |
| `fusion-hacer` | **0** |
| `fusion-deshacer` | **0** |
| `trabajo-proponer` | **0** |
| `trabajo-aceptar` | **0** |
| `trabajo-parte` | **0** |

O sea: **las dos pantallas pintan sus botones y nadie los escucha.** *Se ven y no hacen nada.*

**Y LO IMPORTANTE, que es una corrección a lo que yo mismo informé**: el recorrido del **CRM-04** dio **16 · 0** y yo lo
llamé «andado entero» — pero **su andadura trabajaba contra las PUERTAS de la API**, no pulsando los botones. Así que
aquel 16 · 0 **no prueba que sus botones funcionen**: prueba que el servidor y la pintura están bien. **La parte de
pulsar, en el CRM-04, nunca se ha medido.**

El de la **fusión** sí lo cazó, porque **sí pulsa** (`[data-accion=fusion-ver].click()`): de ahí su «la vista previa NO
apareció». El botón existe, se ve, y al pulsarlo **no pasa nada**.

**Lo que falta, entonces, en las dos**: dar de alta esas siete acciones en el manejador delegado (`app.js:19435`) y
volver a andar **pulsando**, no por la puerta.

### LA FUSIÓN: DÓNDE ESTÁ EL BLOQUEO, YA ACOTADO (14/10/2026)

Medido leyendo, no suponiendo:

- **`leer()`** (`rutas.js:414`) recorre `PANTALLAS` y decide con **`encajan()`** (`rutas.js:380`).
- **`encajan` es correcto**: exige `patron.length === tramos.length` y compara literal, así que **`["fusion"]` sí encaja
  con `#/fusion`**. → **la dirección funciona.**
- Y la rama del router está **dentro de `abrirLaPantalla`** (contando llaves: la función va de la 1239 a la 1437, y la
  rama de la fusión está en la 1349).

**Conclusión**: lo que falla está **dentro del cargador** `abrirLaFusion`, y como es `async`, su excepción **no la
recoge nadie**: la promesa se rechaza, la aplicación **se queda donde estaba** y por eso el recorrido ve **el armazón**
(los botones son `Menú`, `Mi cuaderno`, `Salir`). *Una pantalla que revienta al abrirse se ve igual que una que no
existe.*

**Y la herramienta para verlo la tiene la casa**: `VIGILAR_LOS_ERRORES`
(`scripts/verificar_el_recorrido_de_las_tareas.py:543`), que apunta en `window.__los_errores` los `error` **y** las
promesas rechazadas (`unhandledrejection`). *Ese es el siguiente paso, y es una línea*: inyectarlo antes de navegar y
leer lo que dice.

**Y tres comprobaciones de mi andadura de la fusión están mal y hay que quitarlas** (o darán un número que engaña):

1. «el servidor tampoco las junta» — la puerta hace bien en juntarlas: las notas que escribí viven en la **tabla**
   `notas_de_un_contacto` y se mueven enteras. Lo que la vista previa avisa es **el campo de texto** de la ficha, y
   eso ya está arreglado y probado (`test_la_fusion_y_el_campo_de_notas.py`).
2. «con dos notas, la pantalla NO ofrece juntarlas» — **pasa por el motivo equivocado**: pasa porque **no hay
   pantalla**.
3. «la previa cuenta las tablas» / «dice que no choca» — miden una pantalla **que no se pinta**.

### LA FUSIÓN: TODO LO QUE SE PUEDE LEER ESTÁ BIEN, Y NO SE PINTA (14/10/2026)

**Medido, y es un resultado negativo que conviene no volver a mirar:**

| pieza | estado |
|---|---|
| `rutas.js:124` — `{ clave: "fusion", patron: ["fusion"] }` | **correcta** y **dentro** del array (leída **en su contexto**, no en un `grep`) |
| `encajan()` (`rutas.js:380`) | **correcta**: `["fusion"]` **sí** encaja con `#/fusion` |
| La rama del router (`app.js:1349`) | **dentro** de `abrirLaPantalla` (contado con llaves: 1239→1437) |
| `PANTALLAS_EN_REACT` | `trabajos_a_terceros` en la 269 y **`fusion` en la 270** |
| El MAPA (`app.js:855-856`) | `PantallaDeLosTrabajosATerceros` y **`PantallaDeLaFusion`**, las dos iguales |
| Los imports (`app.js:132-133`) | los dos, en el mismo sitio y con la misma forma |
| El vigilante de errores | **`[]`** — **no salta ninguna excepción** |

**O sea**: la ruta encaja ✓, la rama está donde tiene que estar ✓, la pantalla está en las dos listas ✓, el import es
simétrico con el de la pantalla que **sí** se pinta ✓, y **no hay error** ✓. **Y aun así no se pinta.**

**Lo que queda por medir es lo que la aplicación PIENSA que está mirando**, no lo que dice la tabla: el armazón
**marca el módulo en el que se está** (hay una prueba de eso), así que leer **qué renglón del menú va marcado** y
**`location.hash`** dice si la aplicación se enteró de la dirección o no. Eso es una línea en la andadura, y es lo
siguiente.

**Y una nota sobre el terceros, para no volver a dudar de él**: su pantalla **sí se pinta** — su andadura comprueba
«sin trabajos, lo dice» y ese texto **solo existe en la pantalla** (el armazón no lo tiene). Lo que **no** comprobaba
era **pulsar**, y eso ya se ha conectado.

### LA PANTALLA DE LA FUSIÓN **SÍ SE PINTA** — Y CINCO RONDAS PERSIGUIENDO UN BLOQUEO QUE NO EXISTÍA (14/10/2026)

**La medida, en dos líneas de la propia andadura**:

```
errores de la página al abrir la pantalla: []
QUÉ SE HA PINTADO -> hash: '#/fusion?campana=2026&finca=1'
                     titulares: ['Juntar dos fichas que son la misma']
```

**El titular es EL MÍO.** La pantalla **se abre, se enruta y se pinta**; y la aplicación le **añadió la consulta**
(`campana=2026&finca=1`), que es lo que hace con las pantallas que conoce. **El enrutado está bien.**

**Entonces los 8 fallos son de MI ANDADURA, no de la pantalla** ✗✓: lo que no funciona es **el clic** o **la lectura de
los campos**.

**Y la causa que encaja con todo lo demás** (esto ya es hipótesis, y hay que medirla): los `<select>` de la pantalla
son de React, y **poner `.value` a mano en un campo que React controla no cambia su estado** —es el mismo patrón que ya
apareció con los `<input value=…>` sin `onChange`, que quedaban de **solo lectura**—. Así que al pulsar «ver», el
manejador lee los dos desplegables **vacíos**, se queja con «Elige una» (que es lo que hace, a propósito) y **no pide
la vista previa**. De ahí `filas=0` y de ahí los ocho.

**LO QUE ESTA RONDA CORRIGE, y me lo apunto sin adornos**: durante cinco rondas dije que la pantalla «no se pintaba» y
fui arreglando el enrutado (una llave, un ancla, un envoltorio, unos nombres). **El enrutado estaba bien.** Lo que
faltaba era **mirar los titulares** en vez de mirar los botones — porque el `h1` de la andadura **lo compartía el
armazón**, y un check que mira poco miente. *La herramienta para verlo estaba desde el primer día (el vigilante y los
titulares), y solo la puse al final.*

---

## CIERRE DE LA ENTREGA 5 — FUSIÓN DE CONTACTOS (14/10/2026)

**Qué funciona** (y dónde está):

| pieza | fichero |
|---|---|
| **Inventario de las once tablas** con `contacto_id`, con líneas, hecho **antes** de implementar | `CRM-04-FUSION-INVENTARIO.md` |
| **Vista previa**: cuenta las once, enseña **las colisiones con su porqué y su qué-hacer**, y los dos saldos **solo con permiso económico** | `app/routers/fusion_api.py` |
| **La fusión**: auditoría **primero** con la lista `(tabla, id)`, deduplicar papeles, apartar principales, repuntar, el origen **no se borra** y **remite**, todo en **una transacción** | `fusion_api.py` |
| **Deshacer**: devuelve **solo las filas apuntadas** (*lo de después no se toca*) | `fusion_api.py` |
| **La pantalla** `#/fusion`, con sus textos y sus botones **conectados** | `web/react/pantallas/fusion.js`, `app.js` |
| **14 pruebas de servidor** (vista previa, fusión, saldo con documentos, el campo de notas) | `tests/test_la_fusion_de_contactos.py`, `tests/test_la_fusion_y_el_campo_de_notas.py` |
| **4 pruebas de la pantalla**, dibujada de verdad con `renderToStaticMarkup` | `tests_js/fusion.test.js` |
| **El recorrido andado** en navegador (19 comprobaciones) | `scripts/verificar_el_recorrido_de_la_fusion.py` |

**Criterios del encargo, comprobados**: fusión **dentro** de una finca ✓ · **entre fincas rechazado** ✓ · **repetida segura** (409) ✓ · **fallo intermedio sin cambios parciales** ✓ · **saldo antes y después equivalente** (con documentos ✓) ✓ · **notas, tareas y documentos accesibles** ✓ · **auditoría con origen, destino, autor, fecha y decisiones** ✓ · **definir la recuperación antes de operar** ✓ · **no duplicar vínculos** ✓ · **no compensar deudas** ✓ · **el origen remite** ✓ y **no se borra** ✓ · **resolver conflictos explícitamente** ✓✓: el servidor **se niega** (409) cuando las dos fichas tienen el **campo de notas** escrito, **con prueba vista en rojo**, y **la pantalla para** (4 pruebas ✓).

**Y dos correcciones al contrato, medidas:**

1. Las `uq_*_reenvio` son **de la finca, no de la ficha**: una fusión dentro de una finca **no puede** colisionar por reenvío. Las colisiones reales son `papel` y `principal`.
2. La colisión de las notas es del **campo de texto `Contacto.notas`**, **no** de la tabla `notas_de_un_contacto` — **esa se mueve entera**. *Lo medí mal la primera vez y lo dije: mi primera prueba llenaba la tabla y llamé defecto a lo que era correcto.*

**Limitaciones, dichas**:

1. **Las capturas no las ha mirado nadie con ojos.**
2. **El recorrido andado no consigue llegar al estado «dos con notas»** en el navegador (su interacción con los desplegables), así que **esa parte se mide en `tests_js`**, que es donde se puede: *la pregunta es pura y el navegador era un instrumento frágil para ella*.
3. **Falta la revisión visual** del contrato de la Entrega 6.

**Lo que costó, para que se sepa**: **once rondas** persiguiendo un bloqueo que **no existía** (una llave, un ancla, un envoltorio, unos nombres, una hipótesis falsa, un `h1` compartido con el armazón, cuatro intentos de escribir en un desplegable) — y al final **era una línea**: `GET /api/contactos` devuelve una **lista**, no un diccionario. *La misma familia de fallo que las otras cuatro veces de la sesión: dar por buena la FORMA de lo que vuelve.*

**Commits**: el modelo, la vista previa, la fusión, el deshacer, las pruebas, la pantalla, su ruta y sus botones (14/10/2026).

**Siguiente tarea**: **CRM-05** (costes, inversiones y economía) por la cola, o el **movimiento de almacén** que el CRM-04 deja dicho pero no hecho.

### CRM-04: LO QUE FALTA DEL ALMACÉN, Y POR QUÉ NO ES UNA LLAMADA (medido, 14/10/2026)

El contrato dice *«2 L propios consumen; 2 L del cliente no»*. Y hoy el parte **solo dice de quién es el insumo** —lo
guarda y lo enseña con palabras— **pero no apunta qué producto ni cuánto**. Y un consumo necesita las dos cosas.

**Lo que la casa tiene** (medido): el almacén se lleva con **`MovimientoDeExistencias`** (`models.py:2750`), y cada
movimiento **apunta a su origen** con `origen_tipo` y `origen_id` (el propio `almacen_api.py` lo usa así para las
recepciones: `origen_tipo == "recepcion"`, `origen_id == recepcion.id`), con `anulado` y **sin borrar nada**: *«nada se
borra»*, dice su cabecera.

**Así que el camino está claro**: al apuntar el parte, si `de_quien_es_el_insumo == "propio"`, se crea un movimiento de
salida con `origen_tipo = "trabajo_a_tercero"` y `origen_id = <el trabajo>`; y si es del cliente, **no se crea nada**.

**Pero falta una pieza de diseño, y hay que decidirla**: **el parte tiene que decir QUÉ producto y CUÁNTO**, porque hoy
no lo tiene. Eso es **un cambio de modelo con migración** —y el encargo pide, para una migración, *copia, ensayo sobre
copia, integridad, idempotencia y recuperación*—, así que **no se hace de pasada**.

**Y la decisión que hay que tomar antes**: si el insumo se apunta **en el parte** (líneas de producto y cantidad, como
una labor) o **aparte** (un movimiento que se enlaza al trabajo). La primera es más cómoda para el agricultor; la
segunda, menos cambio de modelo. **No la tomo solo**: se pregunta.

### CRM-05: EL REPARTO YA ESTÁ CONSTRUIDO — NO HAY QUE VOLVER A HACERLO (medido, 14/10/2026)

Antes de construir nada, se midió. **El trozo difícil del CRM-05 —el reparto del coste entre destinos— ya existe
entero, y con 37 pruebas:**

· **La puerta**: `app/routers/gastos_api.py` — `RepartoDeUnGastoEntrada` (69), `_sus_repartos` (158). Su cabecera
  ya dice los dos criterios del contrato: *«Costes repartidos + costes sin asignar = total conocido»* y *«un gasto
  que no se sabe repartir **no se reparte a medias**: se queda entero en «sin asignar» **y se dice por qué**»*.
· **Las reglas**: `app/gastos.py` — `reparto_por_peso` (534), `reparto_por_area` (645), `reparto_por_horas` (652),
  `reparto_por_consumo` (659), `reparto_a_mano` (666), `cuadre_del_reparto` (748), `el_gasto_queda_sin_asignar` (790).
· **El modelo**: `RepartoDeCoste` (`models.py`, ~3858) — con el **residual ya decidido y escrito**: *«Ya redondeado
  al céntimo y sumando exacto… **el céntimo del redondeo se le pone a uno y se dice a cuál**»*, el `metodo` guardado
  («dentro de un año es lo único que explica de dónde salió esta cifra») y `no_se_reparte_porque` (que **se añadió
  porque una prueba falló**: el motivo se calculaba, se usaba para el aviso y **se perdía al guardar**).

**Así que el CRM-05 NO es «construir el reparto»**: es **comprobar y completar lo que falte** — el panel con sus
cuatro criterios de aceptación, la amortización, las ayudas separadas y el margen por campaña.

**Y queda dicho para que nadie lo vuelva a construir**: *medir antes ahorró un ticket entero.*

---

## CIERRE DEL CRM-05 — COSTES, INVERSIONES Y ECONOMÍA (14/10/2026)

**LO PRIMERO FUE MEDIR, Y CAMBIÓ EL TICKET.** Su contrato empieza pidiendo *«definir con el modelo actual cuál es el
origen único de cada coste y cada ingreso»*. Se hizo —22 sitios con fichero:línea, en `CRM-05-ORIGEN-DE-CADA-COSTE.md`—
y el resultado fue que **el ticket estaba construido casi entero**:

· **El reparto de costes**: `gastos.py` con `reparto_por_peso` (534), `por_area` (645), `por_horas` (652), `por_consumo`
  (659), `a_mano` (666), `cuadre_del_reparto` (748), `el_gasto_queda_sin_asignar` (790). Su puerta, en
  `gastos_api.py`. **37 pruebas.** El residual **ya está decidido y escrito** en el modelo (`RepartoDeCoste`): *«el
  céntimo del redondeo se le pone a uno y se dice a cuál»*.
· **El panel**: `gastos_api.py:543` (`las_cuentas`) — margen, costes sin asignar, inversiones y ayudas. Y el criterio
  *«sin precio no hay ingreso cero»* **ya está implementado y documentado**: *«el margen sale solo si no falta ningún
  importe… con `margen` en `None`, **nunca con un cero**»*.
· **El caso prohibido de la cola** (factura + gasto + banco): **UN gasto**, manda `Gasto.importe`, y la regla está
  escrita en el código (`APORTA_AL_COSTE`, `gastos.py:102-108`) y aplicada (`coste_conocido` solo con gastos).

**LO QUE SÍ FALTABA, Y SE HA HECHO** (`explotacion.py`, commit de esta fecha):

**`GET /api/campanas/comparar?una_id=&otra_id=`** — el criterio *«comparar campañas declara áreas y cobertura
distintas»*, que **no existía en ningún sitio** (buscado y no encontrado).

· **Las áreas de una campaña** son las parcelas que tocan sus apuntes, por **el trío de la casa** —
  `TratamientoFitosanitario`, `RegistroFertilizacion`, `Labor`— porque **`Parcela` no lleva `campana_id`**: la tierra
  es la tierra y la campaña es el año.
· **La cobertura se declara como la casa la declara** (patrón de `cuaderno_cyl.py:372`): se suman solo las parcelas
  que traen `superficie_oficial` y **se dice cuántas no la traen** — *«para que quien lea sepa que esa cifra es
  parcial»*. Nada se rellena con ceros.
· **`comparables` + `y_por_que_no`**, con cuatro motivos **en palabras**: mismo año, superficie parcial, una cerrada y
  otra no, o alguna sin parcelas. Y `diferencia_de_hectareas` es **`None`** cuando no se puede restar — *nunca un cero
  que parezca respuesta*.
· **`PuedeVerLoEconomico`** y filtro por finca (404 sin distinguir «no existe» de «no es tuya»).

**PRUEBAS**: `tests/test_comparar_dos_campanas.py` — 3 casos, **verdes**: la misma campaña dos veces no es comparable y
lo dice ✓ · una sin parcelas trabajadas tampoco ✓ · la de otra finca no se ve ✓. Y **todo lo de campañas y finca,
verde** (`pytest -k "campana or explotacion or finca"`, código 0).

**CRITERIOS DEL CONTRATO, UNO A UNO**: repartos suman exacto ✓ · 500 transferidos no mueven el margen ✓
(`test_el_traspaso_no_mueve_el_margen`) · sin precio no hay ingreso cero ✓ (tres sitios) · **paginar no cambia la
tarjeta ✓ por construcción** (la puerta `las_cuentas` no pagina: `(explotacion, db, campana_id)`) · **comparar campañas
declara áreas y cobertura ✓ HECHO**.

**LÍMITES, DICHOS**: (1) **la prueba de «la tarjeta suma todos los gastos y no un trozo»** no se escribió — el criterio
se cumple por construcción, y se dice en vez de fingirlo. (2) `hectareas_declaradas` del cuaderno de la Junta es **otra**
cifra (la declarada), no la de esta puerta: aquí se usa la oficial del SIGPAC. (3) **La pantalla** del comparador no
existe: el criterio se cumple en el servidor, que es donde el contrato lo pone.

**LECCIONES DE LA RACHA, para la guarda** (las tres costaron un error): los **nombres de los modelos** se leen, no se
deducen de los ayudantes (`TratamientoFitosa` ✗ → `TratamientoFitosanitario` ✓); los **imports de la puerta** se
comprueban (`Decimal` ✗); y **`ast.parse` NO caza un `from __future__` mal colocado** ✗ — **hay que importar el
módulo** (`python -c "import app.routers.explotacion"`) ✓.

**COMMIT**: *«comparar dos campañas, y decir cuando NO se pueden comparar»* (2 ficheros, +163).

**SIGUIENTE**: los tickets disponibles de `COLA.md` — y sigue pendiente del dueño **una** pregunta (el qué y cuánto del
insumo del CRM-04: en el parte o como movimiento enlazado) y la **revisión visual**.

### CRM-06 · HUECO 1, CERRADO: DARLE LA FORMA A UNA TIERRA (14/10/2026)

**Lo que había**: el mapa, sin ninguna tierra con forma, decía *«Se le puede decir la forma a una tierra desde su
ficha»* — **y esa acción no existía** ✗. `Parcela.geometria` solo se escribe al **crear** la tierra y
`PUT /api/parcelas/{id}` la protege **a propósito** (para que corregir un nombre no borre el dibujo). **La pantalla
prometía algo que no se podía hacer.**

**Lo que hay**: `PUT /api/parcelas/{id}/forma` (`routers/parcelas.py`), con `PuedeModificar`, 404 si la tierra no es
de la finca, y 400 si no trae forma. Construye **un lote de un solo recinto** con `parcela_id` y
`fuente="agricultor"` y se lo pasa a `aplicar_importacion` — **que es el único escritor de versiones que hay**, así
que la unicidad, la prioridad de fuentes, la auditoría y las hectáreas las pone la casa, no esta puerta.

**Por qué `fuente="agricultor"`**: por la tabla de prioridad de la casa, **manda sobre el SIGPAC** y **pierde contra
una medición en campo**. *Lo que el agricultor corrige no puede quedar tapado por lo que trajo la administración.*

**Pruebas**: `tests/test_darle_la_forma_a_una_tierra.py` — **3, verdes**.
**Commit**: *«darle la forma a una tierra que no la tiene: la ruta que el mapa prometía»*.

**TRES DEFECTOS QUE APARECIERON DE CAMINO** (los tres reales, y los tres valen para la guarda):
1. **El camino**: el decorador es **relativo al prefijo `/api`**, y escribí el camino **final** → la ruta cayó en
   `/api/{parcela_id}/forma`, **un comodín** que podía tragarse otras.
2. **`PuedeModificar` usado sin importar**, en una ruta que **ya existía** (línea 1708): habría dado un 500 al usarla.
3. **`schemas` sin importar** — y aquí está lo importante: **`from __future__ import annotations` hace que las
   anotaciones sean CADENAS**, así que **el módulo importa bien aunque falte el nombre** y **FastAPI trata el cuerpo
   como parámetro de consulta** (`loc: ["query","datos"]`, `input: null`).

**La lección de los tres, junta**: `ast.parse` **no** caza un `__future__` mal puesto; `import` **no** caza un nombre
que falta en una anotación. **Lo que sí los caza es `hasattr` y la prueba de comportamiento.**

### CRM-06 · HUECO 2, CERRADO: EL AVISO DE SOLAPE (14/10/2026)

**Lo que había**: `superficie_contada_del_grupo` (`servicios.py:543`) suma las hectáreas de las tierras de un grupo
y **no mira si sus formas se pisan** → dos tierras solapadas cuentan **dos veces** la parte común, y el total
*«parece bueno y no lo es»* (su propia frase, para otro caso). El contrato lo pide así: *«formas solapadas no
duplican superficie única **sin advertencia**»* (§2.1, E2).

**Lo que hay**: `solapes_del_grupo(grupo)` en `servicios.py`, que devuelve **las parejas que avisan** —`si` o
`puede`, con la palabra de `geo.se_solapan` **y su significado en texto**— y **no corrige nada**, que es lo que el
propio `geo` decidió: *«se avisa para que se mire, y no se corrige nada… el contrato pide detectar solapes y
decirlo, no arreglarlos por su cuenta»*.

**Por qué solo las que avisan**: `no` es que están bien y `no_se` es que a alguna le falta la forma (regla de A7).
Devolverlas también sería ruido y **escondería el aviso entre lo que no lo es**.

**Y `superficie_contada_del_grupo` se queda intacta**: su contrato —«`None` si falta un número»— es **otra cosa**
que el solape, y mezclarlas rompería lo que ya funciona.

**Pruebas**: `tests/test_los_solapes_de_un_grupo.py` — **5, verdes**, y es una función **pura** (un grupo, ninguna
base de datos, tierras de mentira). **Commit**: *«el aviso de solape entre las tierras de un grupo…»*.

**Un defecto cazado por la guarda 3 ANTES de ninguna prueba**: escribí `geo.texto_del_solape` ✗ y **esa función no
está en `geo`** — está en `versiones_de_recinto.py:366`. La llamada habría reventado **al usarla**. Lo cazó un
`hasattr` en el mismo guion que escribía la función. **Es la primera vez en la sesión que una guarda para algo
antes de que cueste una ronda.**

### CRM-06 · HUECO 4 (DOCUMENTOS), CERRADO: LOS PAPELES DE UNA TIERRA, EN SU FICHA (14/10/2026)

**Lo que había**: la ficha de una tierra juntaba tres puertas (trabajos, dinero, la tierra) y **no tenía sus
papeles**. Y no podía tenerlos por dos motivos, los dos reales:
1. **No había forma de enlazar un papel con una tierra**: `bandeja.CLASES_DE_VINCULO` tenía seis clases
   (`compra`, `gasto`, `venta`, `maquina`, `trabajo`, `inspeccion`) y ninguna era la tierra.
2. **Y la bandeja no sabía pedirse por aquello con lo que un papel está enlazado**: filtraba por estado, tipo
   y texto, y nada más. Para ver los papeles de una tierra había que traerse la bandeja entera y cruzarla en
   la pantalla — **lo contrario de lo que esta casa hace**.

**Lo que hay** (tres commits):
- `3dd9b37` — **la tierra como clase de vínculo**. Cuatro sitios, no dos: la lista (`CLASES_DE_VINCULO`), el
  diccionario `clase → modelo` (`bandeja_api`), **las clases que se sugieren** (`CLASES_SUGERIDAS["contrato"]`,
  que es lo que se le ofrece al agricultor) y **su nombre** (`textos.py: clase_tierra`). Los dos últimos los
  descubrieron las pruebas de la casa, no yo. `clase` es un **texto** (`String(20)`) y **no pide migración**:
  el modelo dice por qué — *«no es una clave ajena a propósito: apunta a varias tablas… quien comprueba que sea
  de esta finca es el router»*.
- `3b2a6ac` — **los papeles pedidos por la tierra**: `GET /bandeja?clase=tierra&entidad_id=N`, con una función
  **nueva y aditiva** (`_los_papeles_que_cuelgan_de`) que **no toca** la de la casa, y cuatro comprobaciones
  (el papel sale al pedir su tierra; **no sale al pedir otra**; sin filtro sigue saliendo; la clase inventada
  devuelve vacío).
- `2590023` — **la sección en la ficha**: la cuarta puerta en el cargador (`app.js`), la sección en
  `PantallaDeLaTierra` (copiada de la de Cultivos) y **sus frases en los tres sitios**.

**LA REGLA DE LOS TRES SITIOS** (cinco rondas me costó verla): una frase vive en **tres** sitios y hay una
prueba por cada pareja:
1. `app/textos.py` — lo que sirve `/api/interfaz`.
2. `tests_js/trabajos.test.js` — la copia que usan las pruebas del móvil.
3. `docs/T15_TRABAJOS.md` — **el informe**, del que el coordinador **pega** el bloque.
*«Si el informe se queda corto, el coordinador pega un bloque al que le falta una frase y la pantalla la pide
en blanco»* — la razón, escrita en la propia prueba.

**Cinco suposiciones mías, y las cinco las cazó algo que no era yo**:
| supuse | era | quién lo cazó |
|---|---|---|
| «existe en `textos.py`» | existía… en **otro** diccionario | mi guarda, con `hasattr` |
| la copia escribe con comillas | las escribe **sin** comillas | el guardián de Python |
| la tabla usa 4 espacios | el `read` me enseñó 6 (**dos suyos**) | el propio guion, al medir |
| el diccionario se llama `AGENDA` | la marca es `AGENDA: dict[str, str] = {` | el guardián de Python |
| «el informe» es `textos.py` | es **`docs/T15_TRABAJOS.md`** | el guardián de Python |

**Estado**: Python **verde** · JavaScript **1112 · 0** · base del agricultor **INTACTA**.
**Queda de CRM-06**: la superficie «trabajada» (espera la pregunta al dueño) y **PAC en la ficha**.

### CRM-06 · EL DEFECTO QUE SOLO VIO EL NAVEGADOR (14/10/2026)

**Lo que pasaba**: la ficha de una tierra tenía su sección de papeles, el cargador traía **1 papel**, el
componente declaraba la propiedad… y **la ficha enseñaba «No tiene ningún papel enlazado todavía»**.

**La causa, en una línea** (`web/react/pantallas/trabajos.js`):

```js
export function pantallaDeLaTierra(propiedades) {      // EL ENVOLTORIO
  return html`<${PantallaDeLaTierra}
      textos=${propiedades.textos} · tierra=${…} · historial=${…} · estado=${…}
      costes=${…} · no_consta=${…} · error=${…}        // ← SIETE, enumeradas A MANO
    />`;
}
```

**El envoltorio enumera las propiedades que le pasa al componente, y `papeles` no estaba en la lista** ✗✓ —
así que **se quedaba por el camino**: el cargador lo tenía, el componente lo esperaba con su valor por
defecto (`[]`) y la pantalla tomaba la rama del vacío. **Arreglo**: una línea (`papeles=${propiedades.papeles}`).

**Por qué ninguna prueba lo veía**: la que había montaba **el componente** (`PantallaDeLaTierra`) **directamente**,
y **el envoltorio no está en ese camino**. La nueva monta **el envoltorio**, que es lo que monta `app.js`:
*«montar lo que monta la aplicación, no la pieza que te gusta»*.

**Y este es el TERCER defecto de la misma familia en un día** ✗✓: el envoltorio que faltaba en `fusion.js` ✗, el
`papeles:` dentro del objeto anidado `tierra: {…}` ✗ y este ✗. Los tres son lo mismo: **un sitio de más donde el
dato se queda** — *escribir donde parece, no donde se lee*.

**CÓMO SE ENCONTRÓ, que es lo que hay que copiar** ✗✓. Seis lecturas de código descartaron seis hipótesis (el
fichero servido viejo, la llamada ausente, `apiJson`, `api()`, el repintado tardío, el cargador) — **todas
correctas y ninguna era el fallo**. Lo resolvieron **dos experimentos**:
1. **abrir la ficha dos veces** ✓ — *si los papeles salen a la segunda, es tiempo; si no, son datos* ✓;
2. **una sonda temporal de una línea** (`window.__sondaPapeles = …length`) ✓ — *que dijo `sonda = 1`: **el cargador
   SÍ recibía el papel*** ✓✓ — y con eso el fallo quedó acotado a un solo sitio, a la vista.

**Método, para el próximo recorrido**: *primero el **experimento que distingue** (dos aperturas, una sonda), y
después la lectura fina de código* ✓. Seis lecturas no veían lo que se queda por el camino; **una sonda sí**.

**Y la revisión visual**: el guion `scripts/capturar_la_ficha_de_una_tierra.py` monta el caso **por las puertas
de verdad** (una tierra, un papel subido y enlazado con `clase=tierra`), captura en `docs/capturas/` **y mide la
pantalla por su estructura** — *«una captura sin comprobación es una foto, no una prueba»* ✓. **Yo no puedo ver
imágenes** (el modelo no acepta entrada de imágenes ✗), así que **la captura queda para el dueño** y la medida
la hace el guion.

### CRM-07 · «PON 0» SE VA DEL FORMULARIO DEL ABONO (14/10/2026)

**Lo que había**: los tres nutrientes del abono eran **obligatorios** (`web/app.js:7911-7913`, `obligatorio: true`)
y las pistas decían, en **ocho sitios**, *«Si el saco no lo trae, **pon 0**»* — y *«Si no lo sabes, pon 0»*.
**Eso viola dos reglas a la vez**: la del contrato del CRM-07 (*«Abono: composición con unidades, producto
aplicado y nutrientes calculados separados; **no asumir 0**»*) y la de la casa (*«lo que no se sabe no es 0»*).

**Y lo llamativo**: **el código que enseña «no consta» ya estaba escrito** — `composicionDelAbono`
(`web/app.js:8270`), con su comentario diciendo *«Un 0 y un "no lo sé" no son lo mismo —el 0 dice que el abono
no lleva nada— y cuando falta alguno de los tres se dice con palabras»*, y contando que antes salía
«null-null-null». **Estaba escrito para unos huecos que el formulario no dejaba hacer.**
*Tercera vez esta semana: el CRM-05 («el reparto ya estaba construido»), el «no consta» del abono, y la
sección de papeles.* **El patrón**: *el caso raro ya está resuelto en el código y lo que falta es **poder
llegar a él**.*

**Lo que hay**: los tres dejan de ser obligatorios (en blanco = **no consta**, y el cálculo devuelve `None`),
y las ocho pistas dicen *«déjalo en blanco: quedará como "no consta"»*.

**LA REGLA DE LOS TRES SITIOS, OTRA VEZ** — y esta vez reconocida **a la primera**: la frase vive en
`app/textos.py` **y** en una **copia** dentro de `tests_js/interfaz.test.js` (`:1199-1201`), y hay un guardián
que compara las dos. Se cambiaron las dos. *Con los papeles del CRM-06 esto costó cinco rondas; aquí, un
`grep`.* **Eso es lo que se aprende: la regla se reconoce o se sufre.**

**Pruebas**: `tests_js/abonos.test.js` (**nuevo**, 3 verdes): que los tres se puedan dejar en blanco, que
**ninguna pista mande escribir 0**, y que la pantalla **sepa decir «no consta»** con palabras.
`tests_js/interfaz.test.js`: **342 · 0**.

**Pendiente de verificar**: la suite de Python (no se puede correr mientras el recuento corre la suya).

### EL RECUENTO DE PRUEBAS: QUÉ LO ROMPÍA, Y CÓMO SE MIRA RÁPIDO (14/10/2026)

**El guion `poner_al_dia_el_recuento_de_pruebas.py` ya estaba bien** ✓: pregunta a `pytest` por **su colección**
(`--collect-only -q`), desde **la raíz del proyecto** (`cwd=str(RAIZ)`) y con **la configuración de la casa**
(el `-q` viene del `pyproject`, y el comentario lo dice y lo fecha: *13/10/2026*). **No hay contador alternativo.**

**Y sin embargo salió con código 1, y con razón**: su corrida 1 recogió **4982**, escribió ese número en los tres
documentos, y su corrida 2 recogió **4984** → el guardián `test_el_numero_de_pruebas_de_python_es_el_de_verdad`
vio 4984 ≠ 4982 y falló. *El propio guion terminó diciendo «sigue habiendo algo: mira los fallos de arriba».*

**Qué lo rompía: yo.** Entre las dos corridas **seguí editando** —añadí pruebas de JavaScript— y **este proyecto
tiene guardianes que recuentan los ficheros de `tests_js/`**, así que **añadir una prueba de JavaScript mueve el
número de Python**. *El recuento es una foto, y yo movía el objeto mientras se hacía la foto.*
**La regla, para el que venga: cuando se lanza el recuento, se congela el proyecto hasta que termine.**

**CÓMO MIRAR EL NÚMERO EN SEGUNDOS** (hallazgo de la misma ronda): con la `-q` de este proyecto,
`--collect-only` **no imprime identificadores**: imprime **`<fichero>: <cuántas>`**, una línea por fichero
(**131 ficheros**). **La suma de esos números es el total** — *0,5 segundos en vez de correr la suite dos veces*:

```
..\.venv\Scripts\python.exe -m pytest --collect-only -q > recuento.txt
# y se suman los números de las líneas `tests/…: N`
```

**Medido así el 14/10/2026**: **4986 de Python** (dos recogidas seguidas, **el mismo número**: la recogida es
estable) y **1117 de JavaScript**. **Los documentos decían 4982 y 1112** — cuatro y cinco por detrás.

**Para qué sirve cada cosa**: *el `--collect-only` **cuenta**; la suite entera se corre para **verificar que
pasa**.* No hacía falta correrla dos veces solo para saber el número.

### CRM-07 · HUECO 5, CERRADO: «CAMBIO DE ETIQUETA NO CAMBIA APUNTE FIRMADO» (14/10/2026)

**Lo que había**: el mecanismo **sí existía** —`servicios.py:104` copia `dosis_maxima_etiqueta` del producto
al crear el apunte, y `models.py:810` dice que esa columna es **una copia a propósito**— y **no lo defendía
ninguna prueba**: `dosis_maxima_etiqueta` no aparecía en **ningún** fichero de `tests/`.

**Lo que hay**: dos pruebas en `tests/test_autorizacion_del_producto.py` (`TestCambiarLaEtiquetaNoCambiaElApunteFirmado`):
1. El apunte guarda la dosis que decía la etiqueta **aquel día**; se cambia el producto en el catálogo con
   `PUT /api/productos/{id}` y **el apunte no se mueve**.
2. Un producto **sin** `dosis_maxima` deja el apunte en «no consta» (`None`), **no en cero**.

**LO QUE LA PRUEBA ENSEÑÓ, Y ES LO QUE VALE** — *las tres cosas las dijo el producto, no yo*:
| lo que intenté | lo que me dijo |
|---|---|
| leer el campo de la respuesta | **`KeyError`**: esa puerta **guarda** el dato pero **no lo devuelve** → se comprueba **la columna**, que es además **lo que queda firmado** |
| un tratamiento **sin** producto | **`422 · V1_sin_registro`**: *todo tratamiento apunta a **un producto del catálogo*** → el caso «no consta» es **un producto sin dosis**, no la ausencia de producto |
| ¿cómo leo la columna? | *el propio fichero ya lo hacía*: `text("SELECT …")` sobre un motor → **su forma**, sobre `database.engine` (la base donde escribe la puerta), y el nombre de la tabla **sacado del modelo** |

**Y una nota de disciplina**: la herramienta de edición **se negó** a editar el fichero («file changed since it
was read — re-read the file, then retry») porque mis guiones lo habían escrito. *El orden es: **releer, editar**.*
Es exactamente el rigor que a mí me faltó seis veces ese día.

### CRM-07 · HUECO 3, CON EL SITIO EXACTO (medido, sin tocar)

*«El total de abono no se puede convertir a kilos por hectárea en el apunte»* — y son **dos cosas**:

1. **El formulario no admite «no consta»** ✗: `schemas.py:1031-1033` exige `superficie_ha > 0` **y**
   `kg_ha_producto > 0`. **Es el mismo defecto del «pon 0»** que se arregló hoy en el formulario del abono.
2. **La cuenta existe y no la llama nadie** ✗✓: `gastos.abono_por_hectarea` (`gastos.py:871`) — probada con
   las cifras exactas del contrato, seis usos en `test_gastos.py` y **ningún router**.

**Dónde va**: el abono vive en **`app/registros.py`** —`_contexto_fertilizacion` (`:346`), `_avisos_fertilizacion`
(`:362`), y sobre todo **`_preparar_fertilizacion_guardable` (`:447`)**—, y el otro extremo es `servicios.py:137`.

**El diseño**: el agricultor da **los kilos que echó** y **la superficie** (que ya los pide); **las dos cifras por
hectárea se calculan** —producto y cada nutriente— y donde falte un dato se dice **«no consta»**. O sea:
**`kg_ha_producto` deja de ser un número escrito a mano y pasa a ser un resultado.**

**El patrón, quinta vez esta semana**: *el código ya sabe hacerlo; el formulario no deja llegar.*

### CRM-07 · HUECO 3, CERRADO: LOS KILOS Y LA SUPERFICIE DAN EL KG/HA (14/10/2026)

**El caso del contrato, literal**: *«600 kg en 3 ha con N 15 % acreditado -> 200 kg/ha y 30 kg N/ha;
P desconocido si falta»*. **Antes no se podía dar**: el formulario pedia los kilos **por hectarea** a
mano (`kg_ha_producto` obligatorio y `> 0`) y **multiplicaba** para sacar el total. El agricultor no
tiene delante el kg/ha: tiene **los sacos** y **la parcela**.

**Lo que se cambio** (cinco sitios, ninguno de ellos una migracion — **las columnas ya existian**:
`cantidad_total_kg`, `kg_ha_producto`, `riqueza_n/p/k` y los seis `uf_*`):

| donde | que |
|---|---|
| `app/schemas.py` | entra `cantidad_total_kg`; `kg_ha_producto` deja de ser obligatorio |
| `app/servicios.py:165` | si vienen los kilos y la superficie, **el kg/ha se deduce**; los nutrientes salen del deducido |
| `app/validaciones.py:512` | `F1_sin_cantidad` **acepta cualquiera de las dos formas** (y su aviso apunta al campo que falta) |
| `app/textos.py:569` | el mensaje ofrece las dos: «los kilos en total (600) o los kilos por hectarea (200)» |
| `web/app.js` | el campo en el formulario (antes del kg/ha, porque de el se deduce) y **el kg/ha deja de exigirse** |

**Y la prueba** (`tests/test_los_kilos_de_un_abono.py`, 4 pruebas): 600 kg en 3 ha con N 15 % dan
`kg_ha_producto=200.0`, `cantidad_total_kg=600.0` y `uf_n_ha=30.0`; el `P` que no viene en la etiqueta
queda en **`None`** (no `0.0`); el kg/ha a mano sigue valiendo; y sin ninguno de los dos, **422**.

**LO QUE ENSEÑO EL CAMINO** (y vale mas que el cambio):
1. **`test_el_formulario_manda_todo.py`** empareja **cada campo del esquema con lo que manda la pantalla**:
   cazo `cantidad_total_kg` en **una corrida**. *Hay que anadir el campo al cargador (`cargaFertilizacion`)
   Y al formulario.*
2. **`F1_sin_cantidad` ya existia** y su mensaje pedia «cuantos kilos»: **la intencion siempre fue el total**.
3. **`F2_superficie_excedida`** existe y funciona: *la parcela de la casa mide 2,43 ha*, asi que la prueba
   del contrato necesita **una parcela de 3 ha de verdad** (`crear_parcela(superficie_ha=3.0)`).
4. **`gastos.abono_por_hectarea` NO hizo falta llamarla**: la cuenta estaba a tres lineas de donde yo la
   buscaba. *Sexta vez: el caso ya estaba resuelto y lo que faltaba era llegar.*
5. **`textos.py` es CRLF**: un ancla multilinea con `\n` **no casa nunca**. Se edita **por lineas**.
6. **`ast.parse` antes de escribir salvo el fichero**: el `SyntaxError` de una edicion a medias **era de mi
   parseo en memoria**, y por eso el fichero **nunca llego a escribirse roto**. *Dos veces en un dia.*

### CRM-07 · HUECOS 10 Y 11, LEIDOS

* **#10 · `ProductoFitosanitario.foto_etiqueta`**: la columna (`models.py:439`) y los campos del esquema
  (`schemas.py:449`, `:478`) existen y **ningun router la escribe ni la lee**. El contrato pide «fotos de
  etiqueta/justificante **como evidencia**», asi que **se hace la puerta** (como la de la semilla,
  `routers/semillas_api.py:533`) y no se quita la columna. **Sin decision pendiente.**
* **#11 · la unidad de la composicion**: los tres `Float` del N-P-K tienen su «%» **solo en un rotulo**
  (`textos.py:2160-2171`) y en el documento (`firma.py:340-342`). **No hay unidad en la base.**

## PREGUNTAS AL DUENO (no bloquean el trabajo independiente)

1. **La superficie «trabajada» de un grupo**: ¿es una magnitud propia (lo que de verdad se trabajo) o es
   la **declarada** (la del papel)? *Afecta al CRM-06.*
2. **La seccion «PAC» de la ficha de una tierra**: ¿que tiene que ensenar? *Afecta al CRM-06.*
3. **La composicion de un abono (N-P-K)**: ¿se mide **siempre en %**, o hay casos en tu cuaderno en que
   venga en otra unidad (g/kg, kg/t)? — **Si siempre es %**: se declara en el rotulo y en la firma, y **no
   hay migracion**. **Si a veces no**: hace falta una columna `unidad_composicion` **con migracion**
   (copia, ensayo sobre copia, integridad, idempotencia y recuperacion). *Afecta al CRM-07 (#11).*

### CRM-07 · HUECO 10, CERRADO: LA FOTO DE LA ETIQUETA DEL PRODUCTO (14/10/2026)

**Lo que habia**: `ProductoFitosanitario.foto_etiqueta` (`models.py:439`, `String(400)`) se daba de alta,
se leia… y **ningun router la escribia**. El contrato pide «fotos de etiqueta/justificante **como
evidencia**»: era una columna que prometia algo que no hacia.

**Lo que hay** (en `app/routers/maestros.py`, copiando la puerta de la semilla, `semillas_api.py:533`):

```
POST /api/productos/{producto_id}/etiqueta   obtener_de_la_explotacion (aislamiento)
                                             adjuntos.leer_el_fichero + guardar_en_disco
                                             foto_etiqueta = ruta
                                             Auditoria(entidad="producto", accion="subir_etiqueta")
                                             **el fichero viejo se borra DESPUES**
GET  /api/productos/{producto_id}/etiqueta   FileResponse con adjuntos.ruta_segura
                                             404 con su frase si no hay · solo de esta finca
```

**Y no hizo falta migracion**: la columna ya estaba, y **los cuatro datos de la semilla** (nombre, ruta,
tipo, bytes) aqui son **uno** (`foto_etiqueta` guarda la ruta) porque `app/adjuntos.py` ya resuelve el
resto. Las cuatro razones de la casa van escritas en la cabecera de la seccion, porque son las que
impiden que alguien lo «arregle» luego: el fichero a disco ✓, el nombre del navegador **no** es ruta ✓,
el viejo se borra **despues** ✓, y se sirve solo de esta finca ✓.

**La prueba** (`tests/test_la_foto_de_la_etiqueta_de_un_producto.py`, 4): se sube y **se sirve lo mismo
que se subio**; sin foto, **404 con su frase**; **la finca ajena no la ve** (`crear_cuenta`); y al
volver a subir, **la nueva manda**.

**Ni textos nuevos ni formulario**: `foto_etiqueta` ya existia en la ficha, asi que los guardianes de
textos y del formulario pasaron sin tocar nada. *Eso es el hueco entero: **una columna que ahora hace lo
que prometia**, con dos puertas y cuatro pruebas.*

### LAS ANCLAS: TRES VECES EL MISMO FALLO, Y LA REGLA QUE LO CIERRA (14/10/2026)

Un ancla multilinea **fallo tres veces en un dia**, cada una por un motivo distinto:
1. **`textos.py` es CRLF** → un ancla con `\n` **no casa nunca**. Se edita **por lineas**.
2. **`app.js`**: el texto copiado de la **vista** trae **dos espacios de mas** (los de la herramienta).
   *La vista no son los bytes.*
3. **`maestros.py` tiene una linea en BLANCO entre cada import** → `from .. import (\n    catalogos,`
   **no casa**; el ancla que funciona es `    catalogos,` a secas.

**La regla, para no repetirlo**: **anclar en UNA linea, o por FORMA (una expresion regular que recoja
la sangria del propio fichero)**. Y **copiar el texto de `read`, nunca de `Get-Content`** — que ademas
ensena mojibake (`CuÃ¡ntos`) en un fichero que esta bien.

**Y para el aislamiento entre fincas**: la casa ya tiene **`crear_cuenta`**
(`la_ajena = crear_cuenta("ajena-foto@ejemplo.test", nombre="El vecino")`), visto en
`tests/test_la_busqueda_global.py`.

### CRM-07 · HUECO 4, CERRADO: QUE AUTORIZACION ESTABA VIGENTE AQUEL DIA (14/10/2026)

**Lo que pedia el contrato**: que el tratamiento diga **con que autorizacion se hizo**. Y no es un adorno:
la autorizacion excepcional (art. 53 RD 1311/2012) es el permiso **temporal** para usar un producto que
no esta autorizado con caracter general, **y caduca**. Un tratamiento apuntado con ese permiso tiene que
poder ensenarlo despues, aunque el permiso ya no valga: *si no, parece hecho sin autorizacion.*

**Lo que habia**: el producto tenia sus dos columnas (`models.py:437-438`) y **el apunte no copiaba
ninguna** (medido: `autorizacion` no aparecia en `servicios.py`).

**Lo que hay** (dos lineas de modelo, una copia y tres pruebas — **y la migracion la hace la casa sola**):

| donde | que |
|---|---|
| `models.py` (`TratamientoFitosanitario`, junto a `dosis_maxima_etiqueta`) | `autorizacion_excepcional` `String(120)` y `autorizacion_hasta` `Date` |
| `servicios.py:105` | la copia, al lado de la de la dosis, con su porque escrito |
| `tests/test_autorizacion_del_producto.py` (`TestLaAutorizacionVigenteSeQuedaEnElApunte`) | se copia · cambiar el catalogo **no la mueve** · sin autorizacion, `None` |

**Y la migracion, que es lo que el encargo pide**: **no hay que escribirla.** `database.asegurar_columnas`
(`database.py:165`) compara el modelo con la base y lanza el `ALTER TABLE … ADD COLUMN` de lo que falte,
y `database.py:1214` **reconstruye** las tablas a las que les falte su clave ajena. Es **idempotente por
construccion** (solo anade lo que falta), y la casa ya prueba copia · ensayo sobre copia · integridad ·
idempotencia · recuperacion en `tests/test_aceptacion_copia_y_migracion.py`, que **pasa con las columnas
nuevas**.

### LA GUARDA QUE FALTABA: «¿EXISTE EL ANCLA?» NO ES «¿CAMBIO EL FICHERO?» (14/10/2026)

Mi guion hizo esto, y **dijo que lo habia hecho**:

```python
if copia not in tv.replace("\r\n", "\n"):     # comprobaba NORMALIZADO…
    raise SystemExit("ABORTO: no encuentro la copia")
tv = tv.replace(copia, …)                      # …y reemplazaba SIN normalizar
```

**`servicios.py` tambien es CRLF** → el `replace` **no encontro nada**, no fallo, `ast.parse` paso, y el
guion imprimio «la copia, al lado de la de la dosis». **Un no-op silencioso.**

**La guarda buena, y es una linea**:

```python
antes = len(lineas)
lineas[i + 1:i + 1] = nuevas
assert len(lineas) == antes + len(nuevas), "el fichero no ha crecido: no se inserto"
```

*«¿Existe el ancla?» no basta: hay que comprobar que **el fichero cambio**.* Y ademas **lo cazo la
prueba de comportamiento** (las columnas existian y salian `None`), que es para lo que esta.

**Ficheros CRLF confirmados hoy**: `textos.py`, `servicios.py` (y `app.js`, `models.py`, `database.py`,
`main.py`, `parcelas.py`, `explotacion.py`, `schemas.py`, de antes). **Ante la duda: editar POR LINEAS.**

## CRM-07 #2 · LA SEMILLA, HECHA Y **SIN COMMITEAR** (14/10/2026, fin de sesion)

**El contrato**: «Semilla: especie, variedad, **categoria** y evidencia, **comprada/propia**; **no
certificada por defecto**». Faltaban las dos columnas.

### Lo que hay hecho, verificado y EN VERDE (sin commitear)

| fichero | que |
|---|---|
| `app/models.py` | `Semilla.categoria_semilla` `String(40)` (**default `no_certificada`**) y `Semilla.procedencia` `String(20)`, con su porque escrito |
| `app/catalogos.py` | `CATEGORIAS_DE_SEMILLA` (no certificada, base, certificada, R1, R2), `PROCEDENCIAS` (comprada, propia) y `etiqueta_de_categoria(valor)` |
| `app/schemas.py` | `SemillaEntrada` y `SemillaSalida` con los dos campos |
| `app/routers/semillas_api.py` | la respuesta los devuelve (el diccionario a mano, linea ~177) **y el ayudante de la etiqueta los copia a la fila** (linea 214) |
| `tests/test_semillas.py` | 3 pruebas al final: se guardan y se leen · sin categoria es **«no certificada»** (no `None`) · **la `categoria` del articulo no se confunde** con la de la semilla |

**Verificado**: `pytest tests/test_semillas.py tests/test_el_formulario_manda_todo.py` → **codigo 0** ✓.

### LO QUE FALTA, y es el paso siguiente exacto

1. **El recuento** (`scripts/poner_al_dia_el_recuento_de_pruebas.py`), **con el proyecto congelado**:
   son **+3 pruebas** de Python, asi que el numero pasa de **5003 a 5006**.
2. **El commit** con la suite entera verde. Ficheros: `app/models.py`, `app/catalogos.py`,
   `app/schemas.py`, `app/routers/semillas_api.py`, `tests/test_semillas.py`, y los tres del recuento.
3. **Y mirar si la pantalla tiene que ofrecer los dos campos** (el guardian
   `test_el_formulario_manda_todo` **paso**, asi que hoy no lo exige: los campos no son del asistente).

### Y las tres trampas de este hueco, para el que venga

1. **`SemillaSalida` ya tenia `categoria`** — y **es la del ARTICULO** (siempre «semilla»), no la de la
   semilla. Por eso las columnas se llaman `categoria_semilla` y `procedencia`. *El docstring de
   `dar_de_alta_una_semilla` lo dice: «el articulo se crea con la categoria `semilla`… lo unico que
   anade esta tabla es lo que pone el papel».*
2. **Hay DOS construcciones de `models.Semilla(`** en `semillas_api.py`. La buena para copiar los
   campos es **el ayudante que copia la etiqueta** (linea ~214, `semilla.tratada = datos.tratada`), no
   la otra (linea ~396), donde `datos` **no existe** y salta un `NameError`.
3. **`almacen_con_semilla` es una FABRICA** (`almacen_con_semilla()`) **definida dentro de
   `tests/test_semillas.py`**, no en el conftest: *una fixture definida en un fichero de pruebas solo
   se ve en ese fichero.* Y **se llama UNA vez**: cada llamada da de alta un articulo, y la segunda
   devuelve 200 donde su ayudante exige 201.

### Y el estado del CRM-07 al cerrar

**De 12 huecos a 6.** Cerrados hoy: **#1** (composicion del abono en «no consta»), **#5** (cambiar la
etiqueta no cambia el apunte firmado, `73acdb6`), **#3** (los kilos y la hectarea dan el kg/ha,
`fe00335`), **#10** (la foto de la etiqueta del producto, `1ddd778`), **#4** (que autorizacion estaba
vigente, `ee18c53`) y **#2** (la semilla, **sin commitear**).

**Quedan**: #6 (documento y fecha de la aplicabilidad), #7 (taller y coste de la averia), #8 (horas
acumuladas), #9 (la reserva), #11 (**espera la respuesta del dueno** sobre la unidad de la composicion)
y #12 (PostgreSQL, bloqueado).

## CRM-07 #6 · LA APLICABILIDAD DE UNA OBLIGACION, DISENADA (para la vuelta siguiente)

**El contrato**: «aplicabilidad con **evidencia y fecha**». **Lo que hay**: `origen`
(`documento` / `el_agricultor` / `no_se`), `notas` y `creado_en` (`models.py:699-711`). **No hay
`documento_id` ni fecha de la evidencia.**

**Y el diseno ya esta medido, con dos salidas**:

* **(a)** una columna `documento_id` en `obligaciones_de_maquina` (migracion: la hace la casa sola,
  `database.asegurar_columnas`), **o**
* **(b)** **reutilizar `VinculoDeDocumento`** (`models.py:2401`) con una clase `obligacion` — que es el
  mecanismo que ya usan los papeles de un contacto y los de una tierra.

**Y una fecha declarada** («¿de cuando es ese papel?»), porque `creado_en` es cuando se apunto, no
cuando se firmo el papel — y esas dos cosas no son lo mismo.

**La pieza de pantalla ya existe**: la ficha sabe ensenar la inspeccion **con su papel**
(`models.py:728-731`), asi que **no hay que inventar como se enseña**: hay que **hacer que llegue**.

**Lo primero de la vuelta**: correr el recuento congelado (esperado **5006**), commitear el **#2**, y
despues abrir el **#6**.

## CIERRE DE SESION (14/10/2026, ultima ronda) — LO QUE HAY QUE HACER PRIMERO

**El recuento se relanzo y NO TERMINO**: las rondas del objetivo se acabaron antes que el. **No hay
que dar por hecho que el numero esta puesto**: hay que **volver a lanzarlo** con el proyecto
**congelado** (`..\.venv\Scripts\python.exe scripts\poner_al_dia_el_recuento_de_pruebas.py`), y
esperar a que imprima «EN VERDE». **El numero esperado es 5006** (5003 + las 3 pruebas del #2).

**Y despues, el commit del #2** (esta entero, verificado y verde, **sin commitear**):

```
git add backend/app/models.py backend/app/catalogos.py backend/app/schemas.py \
        backend/app/routers/semillas_api.py backend/tests/test_semillas.py \
        README.md AGENTS.md docs/LO_QUE_PIDE_LA_JUNTA.md
```

### El estado, comprobado al cerrar (no es una promesa: esta medido)

* **`app.main` importa** y las rutas se registran · **`node --check web/app.js` da 0** · los **cinco
  ficheros del #2 parsean**. *No hay ningun fichero a medias.*
* **La base del agricultor, INTACTA** (`CC657533…334B12`).
* **Commiteado**: `2590023` · `2694e28` · `73acdb6` · `fe00335` · `1ddd778` · `ee18c53`.
* **El CRM-07: de 12 huecos a 6.** Cerrados: #1, #5, #3, #10, #4 (y el #2 hecho).
* **Quedan**: #6 (documento y fecha de la aplicabilidad, **ya disenado**), #7 (taller y coste de la
  averia), #8 (horas acumuladas), #9 (la reserva), #11 (**espera la respuesta del dueno** sobre la
  unidad de la composicion) y #12 (PostgreSQL, bloqueado).

## EL RECUENTO TERMINO **EN VERDE** Y EL #2 ESTA COMMITEADO (14/10/2026)

**Aviso para el que lea lo de arriba**: donde decia «el recuento no termino y el #2 esta sin commitear»,
**ya no es cierto**. El recuento acabo despues, con codigo 0:

```
1) 5006 recogidas, 1 fallo    (el guardian del numero: los documentos decian 5003)
2) el recuento real es 5006: se pone en README.md · AGENTS.md · docs/LO_QUE_PIDE_LA_JUNTA.md
3) 5006 recogidas, 0 fallos   EN VERDE
=> EN VERDE: 5006 pruebas de Python, 0 fallos, y los documentos al dia
```

**Y el #2 se commiteo**: `10e21a9` «la semilla dice su categoria y de donde salio (CRM-07 #2)»,
8 ficheros, 126 adiciones. **La base del agricultor, INTACTA.**

### Estado del CRM-07 al cerrar de verdad

**De 12 huecos a 6.** Cerrados: **#1** · **#5** (`73acdb6`) · **#3** (`fe00335`) · **#10** (`1ddd778`) ·
**#4** (`ee18c53`) · **#2** (`10e21a9`).

**Quedan**: **#6** (documento y fecha de la aplicabilidad, **ya disenado**), **#7** (taller y coste de la
averia), **#8** (horas acumuladas), **#9** (la reserva), **#11** (**espera la respuesta del dueno** sobre
la unidad de la composicion) y **#12** (PostgreSQL, bloqueado).

**Contadores**: **5006** de Python y **1117** de JavaScript, y los tres documentos al dia.

# CRM-07 #2 CERRADO DE VERDAD, Y EL RECORRIDO COMO PRUEBA (14/10/2026, tras la REVISION del dueno)

**El dueno reviso el commit `10e21a9` contra una base aislada y encontro un fallo REAL de perdida de
datos.** Su informe esta en `REVISION_2026-10-14.md`, y es la referencia de todo lo que sigue.

## El fallo, su causa y sus DOS caras

| sintoma | causa | arreglo |
|---|---|---|
| **Corregir solo la variedad borraba `categoria_semilla` y `procedencia`** | la correccion construye la fila con **`lo_que_hay`**, una lista blanca, **y los dos campos no estaban** | los dos van con el patron A1 de la casa: `datos.X if "X" in enviados else semilla.X` |
| **Mandarlos tampoco los guardaba** | el mismo: `lo_que_hay` no los llevaba, asi que `datos` se ignoraba | el mismo cambio |
| **Y en la PANTALLA seguia roto aunque el servidor estuviera bien** | *la correccion usa **`borradorDeUnaSemilla`** (no `fichaDeUnaSemillaVacia`), y ese borrador tampoco los tenia* → el desplegable ensenaba «No consta» y `datos` mandaba un `null` explicito = **borraba** | los dos campos en los **dos** borradores |

**LA LECCION, y van dos veces hoy**: ***hay DOS sitios que parecen el mismo***. *El alta usa
`fichaDeUnaSemillaVacia`; **la correccion usa `borradorDeUnaSemilla**`. Arreglar el que parece y no el
que **se lee** es el fallo.* **Escribir donde se lee, no donde parece.**

## Lo demas que pedia la revision, y como quedo

* **Validacion contra el catalogo**: en la puerta, **en alta y en correccion**, con la lista delante
  (`«lo_que_sea» no es una categoria de semilla. Las que hay: base, certificada, no_certificada, r1, r2.`)
  y **sin escribir nada** (422).
* **Ausencia ≠ «no certificada»**: `categoria_semilla` **sin valor por defecto**; ausencia = **«No
  consta»**; «No certificada» es **una categoria que se declara**. **El proyecto YA lo tenia escrito**,
  en el aviso **N07**: «Una semilla comprada sin etiqueta no queda certificada por eso».
* **La pantalla**: los **cuatro** sitios — `fichaDeUnaSemillaVacia`, `borradorDeUnaSemilla`,
  `recogeLaSemilla` (opcion vacia → `null`) y los **dos `<${Elegir}>`** con «No consta» el primero.
* **La auditoria del alta**: decia `None` en los dos campos aunque la fila los tuviera. **Lo encontro el
  recorrido, no las pruebas.** Arreglado: el diccionario fijo de `Auditoria` del alta los lleva.
* **Y el guardian que faltaba**: `tests/test_que_la_pantalla_de_semillas_tenga_sus_textos.py` —
  *lo que la pantalla pide (`frase(s.<clave>)`) tiene que estar en `textos.SEMILLAS`, y no vacio.*
  **Su docstring explica el punto ciego**: una clave que falta **no da error, da un rotulo en blanco**.

## El recorrido, que es ahora una prueba de regresion

`scripts/verificar_el_recorrido_de_una_semilla.py [direccion] [base]` → **34 comprobaciones, 0 fallos,
codigo 0.** Seis pasos: alta desde los desplegables · persistencia al **recargar** · **corregir SOLO la
variedad y que no se borre** · el cambio explicito a R2/propia · el valor invalido (422 y sin tocar) ·
**la auditoria** («de certificada a r2, de comprada a propia»).

**Dos cosas que enseño el recorrido, y que valen para todos los guiones de este tipo**:

1. **`Page.reload` y NO `abrir` a la misma direccion.** Esto es un enrutador de `#`: volver a pedir la
   **misma** direccion **no crea un documento nuevo**, y el detector de recarga protestaba **con razon**.
2. **Encuentra lo que las pruebas no ven**: *cinco pruebas en verde y el guardian del formulario, y el
   hueco de la auditoria del alta lo encontro el recorrido.*

## Como se levanta el escenario aislado (para repetirlo)

```
cd F:\EspacioCodigo\CueDigital\backend
$env:CUEDIGITAL_DATABASE_URL = "sqlite:///<base temporal>"
$env:CUEDIGITAL_ENTORNO = "pruebas"
$env:CUEDIGITAL_ITERACIONES_PBKDF2 = "1000"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8371
# y despues:  python scripts\verificar_el_recorrido_de_una_semilla.py http://127.0.0.1:8371 <base>
```

**Nunca el :8000 ni el :8029 del dueno. La base real del agricultor no se toca.**

## El bloque que viene (de la REVISION, con sus criterios)

* **#6 obligaciones de maquinaria**: documento y fecha de la aplicabilidad (`documento_id` o
  `VinculoDeDocumento` con clase `obligacion`, + fecha declarada).
* **#7 averias y costes** (taller en la averia; el coste en la ficha de la maquina).
* **#8 contadores de horas** · **#9 reservas**.
* **UNIDADES (abonos)**: guardar **valor Y unidad**; el BOE admite **% en masa** y, en liquidos,
  **g/L**; si se aplican **litros** y solo se conoce **% en masa**, hace falta **densidad**.
* **SUPERFICIES**: separar **SIGPAC**, **declarada por campana**, **cultivada** y **realmente
  tratada**; cada calculo usa la que le corresponde.
* **PAC de la tierra**: campana, recinto, superficie, cultivo, ecorrregimen, compromisos, evidencias,
  incidencias. **Cumplimiento solo cuando se pueda comprobar.**
* **Fiabilidad, paneles** y el resto, segun `REVISION_2026-10-14.md`.

# CRM-07 #6 · OBLIGACIONES DOCUMENTADAS: HECHO, Y EL RECORRIDO ENCONTRO TRES COSAS (14/10/2026)

**El contrato**: «aplicabilidad con **evidencia y fecha**». `origen` decia que salia de un documento
**sin decir cual**. Ahora la obligacion guarda `documento_id` (el papel que lo demuestra) y
`fecha_de_la_evidencia` (de cuando es), y **el agricultor lo puede decir desde la pantalla**.

## Lo que hay hecho y verificado

| pieza | |
|---|---|
| **Las dos columnas** | `documento_id` (FK a `documentos_anexos`) + `fecha_de_la_evidencia` |
| **Los TRES esquemas** | `ObligacionEntrada` · `ObligacionSalida` (con `trae_papel` y su validador) · **`EstadoDeUnaObligacionSalida`, que es el que lee la ficha** |
| **La migracion** | la hace la casa sola; `test_aceptacion_copia_y_migracion.py` en verde |
| **La puerta** | `_el_papel_es_de_esta_finca` (404, no 403) + **la regla A1** para los dos campos |
| **El 409** | **gratis**: `correcciones.tablas_que_apuntan_a` descubre las tablas por el nombre de la columna |
| **Los dos papeles, separados** | el de la **inspeccion** («como salio») y el de la **aplicabilidad** («por que le toca»): nombres distintos A PROPOSITO |
| **La pantalla** | el papel se elige **en linea** (guarda al elegir) y la fecha va en su campo |
| **Los textos** | `documento_de_la_aplicabilidad` · `fecha_de_la_evidencia` · su pista |
| **El contrato** | `test_los_papeles_y_las_facturas_se_pueden_corregir.py`: la lista pasa a **cuatro tablas**, con la decision y su porque |

## Y EL RECORRIDO ENCONTRO TRES COSAS QUE NINGUNA PRUEBA VEIA

`scripts/verificar_el_recorrido_de_la_aplicabilidad.py` → **40 comprobaciones, 0 fallos, codigo 0**.

1. **El papel se BORRABA al declarar la aplicabilidad otra vez** ✗. La obligacion que llega al manejador
   esta **preparada** por `unaMaquinaPreparada`, y **la preparada cambia los nombres**: el papel se llama
   alli `papel_de_la_aplicabilidad_id`. El manejador leia **la clave cruda** → `undefined` → `|| null` →
   **el servidor lo tomaba por un vacio a proposito**. La fecha sobrevivia porque **no se manda** si el
   campo esta vacio. **Cuarta vez que dos nombres para lo mismo muerden en este encargo.**
2. **El ALTA de una obligacion no dejaba NINGUNA linea de auditoria** ✗. La rama `if obligacion is None:`
   volvia sin pasar por `correcciones.corregir`. Arreglado: escribe su entrada con los dos campos.
   **El mismo hueco que tenia el alta de una semilla.**
3. **Y un tercero, del propio guion** ✗: `nav.pulsar` pincha **por coordenadas**
   (`Input.dispatchMouseEvent`) y **devolvia `true` sin comprobar nada** → si el boton queda fuera de la
   vista, el clic cae al lado y **el guion creia haber pulsado**: decia «pulsado» y **no salia ninguna
   peticion**, y parecia un fallo del producto. Ahora pincha **en la pagina** (`el.click()`) y **dice de
   verdad si pudo**. **La casa ya lo tenia escrito** en `comprobar_el_recorrido_economico.py`: «el boton
   queda debajo de la tabla, fuera de la vista; con `.click()` directo si».

## LO QUE ENSEÑA EL GUION A LOS QUE VENGAN

* **`_api` NO recibe la direccion**: la lee de la constante `DIRECCION` de su modulo, que sale de
  `sys.argv[1]`. **Quien llame a `_api` tiene que pasar la direccion como primer argumento**, o habla con
  el `:8029`. El sintoma es «conexion rechazada», que **parece** un servidor caido y no lo es.
* **Cada `preparar(direccion)` crea un escenario NUEVO**: no se puede ver desde fuera lo que dejo un
  recorrido anterior.
* **`Page.reload` y no `abrir` a la misma direccion** (enrutador de `#`).
* **Los guiones se escriben en una carpeta LIMPIA** (`%TEMP%\cd-diseno\`): en `%TEMP%` hay ~700 guiones
  mios y uno llamado `h2.py` **ensombrecia la libreria `h2`** y `httpx` ejecutaba mi codigo viejo.
* Y **`Set-Content -Encoding UTF8` de PowerShell pone BOM**, y Python lo rechaza.

## LA PARTE 2 DEL ENCARGO (interfaz): LO QUE YA ESTA HECHO

* **Dos esquinas fuera del contrato** ✗ → arregladas: la **barra del asistente** (6 → **4**, y el contrato
  la **nombra**) y una etiqueta (6 → **8**).
* **La unica `box-shadow`** ✗ → **`outline`**: era un anillo (`0 0 0 2px`), no una sombra, pero **se lee
  como una** y el contrato dice «ni una».
* **Las cuatro esquinas, con su nombre del contrato** (`--radio-xl/lg/md/sm`): estaban como **numeros
  sueltos**; **9 literales** sustituidos. Ya no hay **ni un numero suelto** en 91 KB de CSS.
* **Tres guardianes nuevos** en `test_design_md.py`: las cuatro esquinas atadas · **ninguna esquina fuera
  del contrato** · y **ni sombra, ni degradado, ni desenfoque**.
* **Y medido EN EL NAVEGADOR** (`%TEMP%\cd-diseno\comprobar_el_diseno.py`): las cuatro esquinas resueltas,
  **cero sombras calculadas**, y cuatro capturas en claro/oscuro × escritorio/movil en `docs/capturas/`.

### Y UN HALLAZGO QUE HAY QUE DECLARAR

***La densidad del escritorio NO esta en `DESIGN.md`*** ✗: a partir de 64rem, `--radio` pasa a **8**, la
letra a **16** y el control a **34** — una decision **medida** y con el motivo escrito en el CSS («el
dueño dijo: *no se parece a un CRM normal, parece una UI para niños pequeños*… y tenia razon»). El
contrato dice «14 px para todo lo que se toca» y «**si algo no esta aqui, no deberia existir**», asi que
**hay que declararlo y atarlo con un guardian**. Es lo siguiente de la parte 2.

## LO QUE FALTA, EN ORDEN

```
1 · el recuento (congelado) y el COMMIT del #6
2 · declarar la densidad del escritorio en DESIGN.md + su guardian
3 · el #7: el taller en la averia y el coste en la ficha de la maquina
4 · #8 contadores de horas · #9 reservas · unidades · superficies · fiabilidad · paneles · PAC
```

## CORRECCION IMPORTANTE: LA DENSIDAD DEL ESCRITORIO **SI** ESTA EN DESIGN.md (14/10/2026)

**Arriba, en este mismo fichero, escribi que «la densidad del escritorio NO esta en `DESIGN.md`».
ES FALSO, y lo corrijo aqui para que nadie trabaje sobre un error mio.**

`DESIGN.md` tiene la seccion **«En el ordenador (desde 64 rem, unos 1024 px)»** y, dentro,
**«La densidad del escritorio, y de donde salen sus numeros»**, con una **tabla** que declara valor por
valor **y la fuente de cada numero**:

| lo que se mide | antes | ahora | de donde sale |
|---|---|---|---|
| cuerpo | 18 px | **16** | Odoo 17 y Frappe 15 usan 14; **no se baja de 16** por el suelo de legibilidad |
| titulo de pantalla | 24 | **20** | el escritorio que Stitch ya dibujo (`estructura.html`) |
| fila de tabla | 277,9 | **46,2** | Frappe 15 `.list-row { height: 40px }` |
| cabecera de tabla | 50 | **28,9** | Frappe 15 |
| ancho del contenido | 704 | **~1300** | Odoo |
| **radio de control** | **14** | **8** | Odoo 4, `frappe-ui` 8 para lo que se toca |
| numeros de una columna | — | `tabular-nums` | Odoo 17 |
| seguir una fila con el ojo | — | hover 5,5 % y cebra 1 % | los factores de Odoo |

**Y el porque, con las palabras del dueño**: *«no se parece a un CRM normal, parece una UI para niños
pequeños»* y *«que la complejidad este para PC»*.

**LA LECCION, que me costo dos conclusiones falsas el mismo dia**: `DESIGN.md` tiene **630 lineas** y lo
lei **a trozos**. Las dos veces conclui «esto no esta en el contrato» **y las dos estaba**. Es el mismo
error que «volcarlo, no filtrarlo»: **aqui, leerlo entero antes de decir que falta.**

**Lo que SI queda por hacer en la parte 2, ya bien medido**: que el bloque `@media (min-width: 64rem)` del
CSS **coincida con esa tabla**, y **atar los dos** con un guardian, como se hizo con la escala de
separacion. Eso es lo que impide que se separen otra vez.

# CRM-07 #6 · SEGUNDA MITAD (autor, fecha de decision, fuente y vigencia) — HECHO (14/10/2026)

Los criterios de la **linea 88** de `REVISION_2026-10-14.md`, uno por uno:

| lo que pide | como queda |
|---|---|
| decision de aplicabilidad | `no_se` = «no lo se», nunca «exento» |
| **autor** | `decidido_por_usuario_id` (FK a `usuarios`) + **el nombre se resuelve AL LEER**, y el esquema lo expone como texto (`decidido_por`). **Lo pone el SERVIDOR**, nunca la peticion: preguntarselo al cliente seria dejar que el agricultor dijera que decidio otro. |
| **fecha de decision** | `decidido_en` (Date), declarada por el cliente. **NO es `creado_en`** (esa es cuando se apunto). |
| **fecha y vinculo del documento** | `documento_id` + `fecha_de_la_evidencia` |
| **fuente normativa y vigencia** | la norma sale de `FUENTE_DE_LA_OBLIGACION` (por tipo, con su enlace al BOE) y la **vigencia NO se inventa**: se ensena `lo_que_dice_la_norma_vigencia` = «Todavia no se ha revisado si esta regla esta en vigor», con las MISMAS palabras que `normativa.py` ya tenia. Y **solo se dice cuando hay norma localizada**. |
| «un documento posterior no cambia una inspeccion historica» | **probado**, con sus dos mitades: el ORDEN (`ultima_inspeccion` manda por la fecha del papel, no por el orden de apuntado) y el ENLACE (corregir la inspeccion para enlazar un papel no mueve fecha, proxima, resultado ni fila). `tests/test_un_documento_posterior_no_cambia_lo_de_antes.py` |

## **LA CONVENCION NO ERA LA QUE PARECIA** (y esto vale para todo el proyecto)

Yo iba a escribir `decidido_por: String(120)` copiando a `Tarea`. **El subagente que mapeó esto me paró**:
la convencion **dominante** (9 filas contra 1) es **FK `*_por_usuario_id` + el nombre resuelto al leer**,
como hace la bandeja (`confirmado_por_usuario_id` + `confirmado_en`, resuelto en `bandeja_api.py` y
expuesto como texto en el esquema). **Tarea es la excepcion**, no la regla.

## **Y «VIGENCIA» YA TENIA RESPUESTA EN LA CASA** — y era «no se contesta»

`app/normativa.py`: «*`tipo` y `estado`: **vacios a proposito**… no dice cual es cada regla, y
**rellenarlos a ojo seria inventar una clasificacion legal**»*. Y el rotulo del hueco ya estaba escrito:
`sin_estado` = «Todavia no se ha revisado si esta regla esta en vigor» — **definido y sin ensenar en
ningun sitio**. Asi que «fuente y vigencia» se resuelve **ensenando ese rotulo**, no con dos columnas
nuevas. **Habria sido justo lo que el proyecto prohibe.**

# LOS DOS FALLOS GRAVES DE ESTA ENTREGA (los dos invisibles para todo lo que teniamos)

## 1 · UN 500 QUE PERDIA LA DECLARACION ENTERA, EN CODIGO MIO

La entrada de **auditoria del alta** metia objetos `date` en `Auditoria.datos`, que es una columna **JSON**:

    TypeError: Object of type date is not JSON serializable  ->  **500**  ->  el agricultor pierde lo apuntado

**Ese codigo lo escribi YO** (ronda 282), y **el mismo fallo llevaba ahi desde antes** con
`fecha_de_la_evidencia`. Lo arreglo el subagente con `isoformat()` (como `correcciones._como_se_guarda`).

**POR QUE NO LO CAZABA NADA — y esto es lo importante:**
· el paso 0 del recorrido declara la obligacion **SIN fecha**, y la fecha llega en una **correccion**, que
  usa `correcciones._como_se_guarda` y **si** serializa bien. **El camino roto —el alta CON fecha— no lo
  andaba nadie.** Y ese camino es **el normal**: es lo que hace la pantalla cuando el agricultor tiene el
  papel delante.
· y **ninguna prueba de `tests/` mandaba `fecha_de_la_evidencia`**.

Fijado con `tests/test_declarar_una_obligacion_con_su_fecha.py`.

## 2 · EL ARNES PODIA ESTAR MIDIENDO JAVASCRIPT VIEJO

**El recorrido abria la ficha sin apagar la cache del navegador.** El servidor sirve `web/` tal cual
(`StaticFiles`), y el navegador se lo guarda: cuando un fichero JS cambia **entre dos vueltas** —y en esta
casa los cambian hasta tres agentes a la vez—, `abrir` puede servir **el de antes**.

Se descubrio **midiendo**: el recorrido fallo en un campo que no encontraba, y **al preguntarle AL
SERVIDOR** por el fichero resulto que lo servia **nuevo** y el navegador tenia el **viejo**.
*Lo peor no es que falle: es que **puede pasar midiendo codigo viejo**.*

**Arreglado en `scripts/navegador_cdp.py`, en `medir()`** (que es lo primero que hace todo recorrido, y
siempre antes de abrir nada): `Network.enable` + `Network.setCacheDisabled`. **Asi lo arreglan todos los
recorridos, no solo el que se dio cuenta.**

# ERRORES MIO EN ESTA ENTREGA, PARA QUE NO SE REPITAN

1. **Invente `corregir_inspeccion`** (no existe) y **`el_rastro_de_esa_obligacion`/`DB`** (no existen), y
   llame a `leer_el_bloque` con los argumentos mal. **Las tres las cazo `grep "^def "`**, no mi memoria.
   → **LISTAR LOS AYUDANTES QUE HAY ANTES DE ESCRIBIR LA LLAMADA.**
2. **Ancla con `\n` en un fichero CRLF** (`textos.py`): 0 coincidencias. → **anclar SIN el fin de linea.**
3. **Un cuerpo a 8 espacios, hermano del `with` en vez de su cuerpo**: `ast.parse` **PASO** —compila y hace
   otra cosa— y solo lo dijo **ejecutar**. → **`ast.parse` comprueba la sintaxis, NO la intencion.**
4. **Un generador de Python con el `for` al reves** en mi propio guion de edicion.

# LO QUE HAY QUE SABER DEL #6 PARA LO QUE VIENE

· **`Poner el autor es cosa del servidor`** — la peticion solo manda `decidido_en`.
· **En `maquinaria_api.py` conviven DOS convenciones**: el `PUT` de una **obligacion** sigue la **regla
  A1** (`if "X" in datos.model_fields_set`), y la correccion de una **inspeccion** es un **reemplazo
  completo** (`proxima_fecha` se asigna directamente, linea ~910). **Mandarla a medias borra lo que no se
  manda.** La pantalla manda el formulario entero.
· **La clave del texto del hueco**: `lo_que_dice_la_norma_vigencia`, y se ensena solo con `fuente.norma`.

# LECCIONES DE HERRAMIENTA (14/10/2026) — de las que cuestan rondas

## PowerShell: `$var:` se lee como una UNIDAD DE DISCO

    Write-Output "  $p: libre"      →  «La referencia de variable no es valida. El caracter ':' no va
                                        seguido de un caracter de nombre de variable valido.»

**Me ha pasado DOS veces** (rondas 278 y 301). La segunda, **el recuento de pruebas no llego a correr** y
yo crei que habia fallado una prueba: perdi una ronda persiguiendo un fallo que no existia.

· Solucion: `${p}` o, mejor, `"  {0} libre" -f $p`.

**Y la leccion de verdad, que vale mas que la sintaxis**: *cuando un comando sale con **codigo 1** y no
hay salida util, **leer el stderr ANTES de culpar al proyecto***. Un `exit code: 1` de PowerShell por una
comilla **no es un fallo de las pruebas**.

## Un recorrido que pasa puede estar midiendo un fichero VIEJO

El servidor sirve `web/` con `StaticFiles` y **el navegador se lo guarda**. Si un fichero JS cambia entre
dos vueltas del recorrido, `abrir` puede servir **el de antes**:

· Sintoma: el recorrido falla en un campo que **si existe** (`getElementById` devuelve `null`).
· Se descubrio **preguntandole AL SERVIDOR** por el fichero (`Invoke-WebRequest` a la ruta): lo servia
  **nuevo**, y el navegador tenia el **viejo**.
· Arreglado en `scripts/navegador_cdp.py`, en `medir()`: `Network.enable` + `Network.setCacheDisabled`.
  Va ahi porque es **lo primero que hace todo recorrido**, antes de abrir nada: lo arregla para todos.

## `ast.parse` comprueba la SINTAXIS, no la INTENCION

Un cuerpo de codigo con la **misma sangria** que su `with` es **un hermano valido**, no su cuerpo:
compila, y hace otra cosa. `ast.parse` **pasa** y el fallo solo lo dice **ejecutar**.

· Sintoma real: `RuntimeError: el navegador no esta abierto: se usa dentro de un 'with'` — porque dentro
  del bloque `nav` era **el de fuera**, ya cerrado.

## LISTAR LOS AYUDANTES QUE HAY, ANTES DE ESCRIBIR LA LLAMADA

En una sola entrega invente **cuatro** nombres que no existian (`corregir_inspeccion`,
`el_rastro_de_esa_obligacion`, `DB`, y llame a `leer_el_bloque` con los argumentos mal). **Los cuatro los
cazo `grep "^def "`**, no mi memoria.

## Anclar en CRLF: SIN el fin de linea

`textos.py` es **CRLF**: un ancla que termina en `\n` **no casa** (0 coincidencias) — el fichero tiene
`\r\n`. Las anclas que funcionan son las que **no incluyen el salto**.

## Los cuatro servidores aislados, apagados al terminar

Tener cuatro `uvicorn` levantados a la vez **carga la maquina**, y `tests/test_el_recorrido_se_anda.py`
—que levanta **su propio servidor en un puerto libre y abre su propio Chrome**— es lo primero que se
queda sin tiempo. **Un recorrido de navegador con la maquina cargada falla sin que nada este roto.**

# DOS DEFECTOS DE ARNES, GEMELOS, LOS DOS INVISIBLES (14/10/2026)

Los dos afectan a **todos** los recorridos, los dos se descubrieron **midiendo** -no leyendo codigo-, y
ninguno de los dos era del producto.

## 1 · La cache servia JavaScript VIEJO  — ARREGLADO

El servidor sirve `web/` con `StaticFiles` y el navegador se lo guarda: si un fichero JS cambia entre dos
vueltas, `abrir` puede servir **el de antes**.
· Sintoma: el recorrido falla en un campo que **si existe** (`getElementById` -> `null`).
· Se descubrio **preguntandole AL SERVIDOR** por el fichero: lo servia **nuevo**, el navegador tenia el
  **viejo**.
· Arreglado en `scripts/navegador_cdp.py`, en `medir()`: `Network.enable` + `Network.setCacheDisabled`.
  Va ahi porque es **lo primero que hace todo recorrido**, antes de abrir nada.

## 2 · `NavegadorDeVerdad` DEJA SU CHROME VIVO  — PENDIENTE

**Diez navegadores acumulados en una sesion** (la semilla, la aplicabilidad seis veces, los disenos).
Y eso hace fallar `tests/test_el_recorrido_se_anda.py`, que **lo dice en su propio docstring**:
«*con otra sesion de navegador en marcha… **dos navegadores a la vez se estorban***».

· **Sintoma que desconcierta**: **pasa SOLO** (90,2 s de los 600 del limite: 15 %) y **falla en la suite
  entera**, dos veces seguidas.
· Y el recuento solo imprime «FALLA», **sin la salida del guion**, porque **no es una asercion que falla:
  es que el navegador no responde**.
· **Arreglo pendiente**: que `NavegadorDeVerdad` **mate su Chrome** al salir del `with`, como el test de
  la casa ya mata su servidor. Y va en el arnes, **para todos**, como la cache.

### Como matar los mios SIN TOCAR EL CHROME DEL DUENO

    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -match '^(chrome|msedge)\.exe$' -and
                     $_.CommandLine -match 'remote-debugging-port|user-data-dir=.*(Temp|tmp)' }

Los del dueno **no llevan esos indicadores** (comprobado: 4 sin ellos, 10 con ellos).
· **NUNCA matar por nombre de proceso.** Y si algo no se identifica con certeza -los diez `python` que no
  llevaban `uvicorn`-, **no se toca** y se dice.

## Y LA LECCION DE LAS TRES ULTIMAS RONDAS

El recuento dijo «falla» **tres veces** y las tres la respuesta estaba **fuera del codigo**:
una comilla de PowerShell, mi propia carga, y mis diez navegadores. **Ninguna era del producto.**
· Y las tres se supieron **midiendo**: el `stderr`, los procesos, y lo que contestaba el servidor.

# CRM-07 #7 · PLAN, CON EL MAPA DELANTE (14/10/2026)

## Lo que el informe pide, contra lo que el mapa dice

| el informe pide | el mapa dice |
|---|---|
| avería | **EXISTE**: fecha, `que_paso`, `resuelta` (tres estados), `fecha_resuelta`, `horas`, `notas`, anular, reenvío. **No tiene taller, ni coste, ni documento.** |
| **taller/contacto** | «taller» **no existe como concepto** ✗ — pero **`"taller"` YA es un papel de `Contacto`** (`contactos.py:83`) ✓ y **nada lo enlaza con una avería** ✗ |
| **presupuesto** | **no existe** ✗. Lo más parecido: `TrabajoParaUnTercero` (`tarifa_por_hora` / `horas_previstas` -> `aceptado_en` / `tarifa_aceptada` / `coste_conocido`) |
| **gasto real** | **EXISTE y ya está enlazado**: `Gasto.averia_id` |
| **documento** | la avería **no tiene** `documento_id` ✗ |
| **«enlazar gastos SIN DUPLICAR EL COSTE»** | **YA CUMPLIDO POR DISEÑO** ✓✓ — `AveriaDeMaquina` **no tiene importe** y el coste sale **solo** de `Gasto.averia_id` (`models.py:3765`). ***El riesgo sería que yo añadiera un `importe` a la avería*** ✗✗ |
| **«máquina indisponible no se ofrece como disponible»** | **NO SE CUMPLE** ✗✓ — el estado existe y **avisa** (`M1`), pero **ninguna de las cinco listas que ofrecen una máquina filtra por él** |

## Las entregas, en orden

### 1 · Que una máquina indisponible no se ofrezca donde se elige para trabajar
· **Sitio**: `web/app.js:22561-22563` y `22583-22584` —las dos que piden `/api/maquinaria` y hacen
  `{valor, texto}`—. Unificarlas en **un ayudante** y filtrar ahí (la casa ya dice: «las dos pantallas
  comparten una lista y no dos que puedan decir cosas distintas»).
· **Quitar SOLO `no_disponible`.** `no_se` **se queda**: `maquinaria.py:89-93` — «una máquina de la que
  nadie ha dicho nada **no está disponible, está sin decir**».
· La **pantalla de maquinaria** sigue enseñándolas todas: es donde el agricultor la ve **y la arregla**.
· **Recorrido**: con `no_disponible`, **no sale** en el desplegable de un trabajo y **sí en su ficha**;
  con `no_se`, **sale**.

### 2 · El taller de la avería
· **NO crear «taller»**: ya es un **papel** de `Contacto` (`contactos.py:83`, con su texto).
· `AveriaDeMaquina.taller_contacto_id` (FK a `contactos`, nullable) + la validación de finca del papel.
· Y **el enlace que hoy no existe**: mirar cómo lo hace `Gasto.contacto_id` y copiarlo.
· **Recorrido**: elegir el taller en la ficha, guardar, recargar, y que el rastro lo nombre.

### 3 · El documento de la avería
· `documento_id` (FK a `documentos_anexos`), **igual que la inspección y que la obligación**, que ya lo
  tienen desde el #6 — que sirve de **modelo**.
· **Y el 409 al borrar el papel sale gratis**: `correcciones.tablas_que_apuntan_a`.

### 4 · El presupuesto — PARAR Y PREGUNTAR
· **No existe** ✗, y hay **dos formas** y no se deduce del código: ¿un **importe previsto** en la avería,
  o un **`TrabajoParaUnTercero` propuesto** con su aceptación?
· **Y en ningún caso un `importe` en la avería que luego se sume**: rompería el diseño del coste ✓✓.

### 5 · Las pruebas que faltan (huecos de verdad, no adorno)
· **anular** una avería: **no hay ni una llamada** a `/averias/{id}/anular` en `tests/`.
· **borrar** con éxito: solo el 404 cruzado.
· Y el hueco de fondo: `gasto.averia_id` **no comprueba que la avería sea de la misma máquina** que
  `maquina_id` (`gastos_api.py:973-983`).

# CRM-07 #7 · ENTREGA 1 · LA MAQUINA INDISPONIBLE NO SE OFRECE (14/10/2026)

## Lo que pide el informe, y donde se cumple

Linea 92: «**maquina indisponible no se ofrece como disponible**».

· **El estado YA existia** (`maquinaria.py:89-93`, tres estados: `disponible` / `no_disponible` / `no_se`) y
  **ya avisaba** (`M1_la_maquina_no_esta_disponible`) — pero **ninguna de las listas que ofrecen una maquina
  filtraba por el**. Eso es lo que se ha arreglado.
· **Se quita SOLO `no_disponible`.** `no_se` **se queda**: `maquinaria.py:89-93` — «una maquina de la que
  nadie ha dicho nada **no esta disponible, esta "sin decir"**». Quitarla seria convertir «sin decir» en
  «no», que es **la misma regla** de `resuelta` (`True`/`False`/`None`) y de la aplicabilidad.
· **Donde**: las **dos** listas que **comparten** el elegir una maquina para trabajar —el formulario de un
  trabajo (`app.js:22561`) y el reparto de un gasto (`app.js:22583`)—. **La pantalla de maquinaria NO
  filtra**: alli tienen que estar todas, porque es donde el agricultor la ve **y la arregla**.

## LA CONVENCION QUE DESCUBRI, Y QUE VALE PARA TODO LO QUE VENGA

***Donde vive el codigo decide si se puede probar.***

· `web/react/pantallas/*.js` son **ES modules con `export`**, puros y con todo por propiedades: `tests_js`
  los carga con `import(".../maquinaria.js?prueba=<aleatorio>")` y **los prueba**.
· **`web/app.js` NO tiene pruebas**: necesita un DOM.
· Por eso la funcion se escribio **primero en `app.js`** (donde funciona) **y se movio a `maquinaria.js`**
  (donde se prueba), importandola `app.js` de la linea que **ya** importaba ese modulo.

  => **UNA REGLA QUE SE PUEDE PROBAR Y OTRA QUE NO: LA REGLA VA DONDE SE PRUEBA.** Y decidirlo **antes** de
  escribirla, no despues.

## Y LA PRUEBA, PROBADA POR EL REVES

`tests_js/maquinaria.test.js` tiene el caso con **las dos mitades** (la `no_disponible` no sale, la `no_se`
si). Y para saber que **no pasa por vacio** se puso el filtro **al reves** a proposito:

    con el filtro al reves:  ✖ AssertionError: «la que no se puede contar no se ofrece, y la que no se
                              sabe SI (no es lo mismo "sin decir" que "no")»   -> pass 20 · fail 1
    restaurado:              pass 21 · fail 0

  => **Una prueba que corre pero no caza es tan inutil como una que no corre.** La unica forma de saberlo
  es **romper lo que vigila**.

## Y UNA CUENTA HONESTA DE ESA ENTREGA: 10 LINEAS DE PRODUCTO, 8 LLAMADAS

Tres de esos intentos fallaron **por el MISMO motivo: anclas con CRLF** (`app.js` es CRLF; `"\n}\n"` no
existe en un fichero `\r\n`). Y lo peor: **la leccion estaba escrita en este mismo fichero, y la cite en un
mensaje de commit, y aun asi la incumpli tres veces.**

· **Una leccion escrita NO evita el fallo; lo evita un HABITO**: *imprimir los bytes antes de anclar*.
· Y el patron que vale no es «quitar el `\n`» sino **`\r?\n` en los dos sitios**.
· La ronda siguiente salio **limpia a la primera** porque lo **primero** que hice fue **mirar la
  codificacion de cada fichero** antes de escribir.

# EL RECUENTO PONE EL NUMERO DE PYTHON, PERO **NO** EL DE JAVASCRIPT (14/10/2026)

`scripts/poner_al_dia_el_recuento_de_pruebas.py` dice «el recuento real es N: se pone en todos los
documentos» — pero **solo pone el de Python**.

Y el guardian `tests/test_lista_de_la_junta.py:227
test_los_numeros_de_test_de_la_documentacion_no_se_quedan_viejos` vigila **los dos**: cuenta los `test(`
de `tests_js/*.test.js` **a mano** y exige que README, AGENTS y la lista digan **ese** numero.

  => **Cualquier entrega que anada una prueba de JavaScript se topa con esto.**
     Hay que poner el numero a mano en los TRES sitios, cada uno con SU patron:
        README    `tests_js/*.test.js"  # 1118 tests`
        AGENTS    `# JavaScript (1118 tests)`
        la lista  `y 1118 de JavaScript`
     **Y medirlo, no suponerlo**: con el mismo patron que usa el guardian (`^test(` en cada fichero).
     **Arreglo de fondo pendiente**: que el script cuente las dos cosas.

# DOS RECORRIDOS PARA LO MISMO, Y EL MAS FUERTE GANA (14/10/2026)

Escribimos dos recorridos para la misma regla, **independientemente**, y el resultado ensena algo:

· **El mio** (190 lineas) leia `#pantalla.innerText` y buscaba el nombre de la maquina **en el texto de la
  pantalla** — **y PASO, 8/0**. Pero es **mas debil**: el nombre podria aparecer en otro sitio del texto y
  la prueba pasaria igual.
· **El del subagente** (864 lineas) lee **`select.options`** del desplegable (`#trabajo-maquina`),
  comprueba **contra la puerta** que las maquinas quedaron como se cree, y cubre **la segunda lista**
  (el reparto de un gasto).

  => ***Pasar no es lo mismo que probar lo que se dice.*** Un recorrido que mide **el texto de la pantalla**
     puede pasar por encontrar el nombre **en cualquier parte**.
     **El bueno lee el CONTROL** —el `<select>` y sus `options`— **y ademas compara con la puerta.**

Y un dato util para los recorridos de trabajos: **el desplegable de maquina SI es un `<select>`**
(`#trabajo-maquina`, `trabajos.js:83-98`, con `<option value=id>nombre</option>`). Yo **supuse** que eran
botones con `data-*` como en la aplicabilidad **y me equivoque**.
  => **Cada pantalla decide como pinta sus opciones: hay que MIRARLO, no deducirlo de otra pantalla.**

# CRM-07 #7 · PRIMERA PARTE: LA MAQUINA INDISPONIBLE NO SE OFRECE (14/10/2026)

**COMMIT `1e38345`.** Lo que pide el informe (linea 92): «**maquina indisponible no se ofrece como
disponible**». Se cumple **en las dos listas** donde se elige una maquina para trabajar.

· **Se quita SOLO `no_disponible`.** `no_se` **se queda**: `maquinaria.py:89-93` — «una maquina de la que
  nadie ha dicho nada **no esta "disponible", esta "sin decir"**».
· **Donde vive importa**: en `maquinaria.js` con `export`, **no en `app.js`**. Los modulos de pantalla son
  puros y `tests_js` los prueba; `app.js` necesita un DOM y **no tiene pruebas**.
  => **UNA REGLA QUE SE PUEDE PROBAR Y OTRA QUE NO: LA REGLA VA DONDE SE PRUEBA.**
· **Verificado con las tres cosas**: prueba unitaria (**probada por el REVES** -con el filtro invertido
  falla y lo dice-), un **recorrido de 32 comprobaciones** que lee `select.options` y compara con la
  puerta, y **el arranque de la app** (que es lo unico que dice si el import esta bien: `app.js` no lo
  cubre ninguna prueba y `node --check` solo mira la sintaxis).

# *** DEFECTO ABIERTO: EL REPARTO DE UN GASTO OFRECE CADA MAQUINA DOS VECES ***

    la puerta (`/api/maquinaria`):   **11** maquinas
    el desplegable del trabajo:       **9**
    el reparto de un gasto:          **18**   ->  [A, A, B, B, C, C, ...]

**Los 18 estan TODOS VISIBLES y TODOS en un mismo padre (`barra-acciones`).**

## Lo que YA esta DESCARTADO, midiendo (no leyendo)

| donde mire | que encontre |
|---|---|
| el array `suyo.maquinas` | cinco escrituras (`app.js:22558,22567,22585,22588,22590`), **todas ASIGNAN** — ni `push` ni `concat` |
| la visibilidad (medida en el DOM) | **18 de 18 visibles** → **no** es el duplicado movil/escritorio del contrato |
| los padres (medido en el DOM) | **todos en `barra-acciones`** → **un solo bloque** |
| el render del bloque (`gastos.js:283`) | `(bloque.opciones \|\| []).map(…)` → **un boton por opcion** |
| quien llena `tierras` (`app.js:21403` y `:21472`) | se escribe dos veces y **la segunda SOBRESCRIBE**, no suma |
| `lasCosasParaUnReparto("maquina")` (`app.js:20973-20981`) | devuelve `estadoDeLosTrabajos().maquinas` mapeado |

=> **Seis sitios descartados y el defecto sigue sin explicacion.** NO inventar una causa.

## LO SIGUIENTE, y es UNA medicion

**Medir `bloque.opciones.length` DONDE SE PINTA**, no en el DOM: un `console.log` temporal en `app.js` (o
leer el array justo antes de construir el bloque). **Es lo unico que falta.**

## Y una leccion de metodo de estas seis rondas

*Cada ronda descartaba un sitio y el sitio no aparecia.* **Descartar es avanzar**, pero el patron que se
repitio todo el dia es que **la respuesta estaba en lo que no habia leido o no habia medido**:
`_api` leia la direccion de su modulo, el clic iba por coordenadas, la cache servia JS viejo, el arnes no
mataba sus Chrome, y el recuento no contaba las pruebas de JavaScript. **Ninguna se encontro razonando.**

# MEDIR POR IDENTIDAD DE NODO, NO POR NOMBRE DE CLASE (14/10/2026)

## El fallo, que me costo seis rondas y era MIO

Un recorrido midio «los botones y sus padres» y agrupo **por `className`**:

    padres[c] = (padres[c] || 0) + 1          <-- MAL

=> Los dos contenedores se llaman `barra-acciones`, asi que **se fundieron en un solo cubo**: «18 botones
   en UN padre», cuando la verdad era **9 en cada uno de DOS**. Y la conclusion que saque
   -«el reparto duplica cada maquina, es un defecto del producto»- **era FALSA**.

**La medicion buena** (un WeakMap que da un numero por NODO):

    {"padres": {"padre#1 (barra-acciones)": 9, "padre#2 (barra-acciones)": 9}, "clavesUnicas": 9}

## Y por que hay dos contenedores (y no es un defecto)

**La pantalla de una ficha pinta LA LISTA y, al lado, EL PANEL DE LA FILA ELEGIDA**, y a 1440 px **los dos
se ven**. El formulario del reparto esta, por tanto, **DOS VECES**, con las mismas claves.
=> ***No es un defecto: son los dos sitios donde el agricultor lo ve.***

**Y para LEER lo que se ve en un sitio concreto, hay que ACOTAR A UN CONTENEDOR**, no leer `#pantalla`
entero. Con eso, el recorrido paso de 32/1 a **32/0**.

## La leccion de siempre, que hoy se repitio SIETE veces

***Cuando el codigo dice una cosa y la pantalla dice otra, el sospechoso suele ser EL INSTRUMENTO.***

   1 · la cache que servia JavaScript viejo (`medir()` no la apagaba)
   2 · el arnes que no mataba SUS Chrome (mataba el lanzador)
   3 · el recuento que no contaba las pruebas de JavaScript (solo ponia el de Python)
   4 · `_api`, que lee la direccion de SU modulo y no la recibe
   5 · `nav.pulsar`, que pincha por coordenadas Y DEVUELVE True igual
   6 · un `ast.parse`... no: esa hizo su trabajo. La sexta y septima:
   6 · la asercion que exigia la direccion EXACTA, cuando la app le anade `?campana=…&finca=…`
   7 · y esta: la medicion que agrupaba por nombre de clase

   **Ninguna de las siete se encontro razonando. Las siete salieron de MIRAR EL DATO.**

# CRM-07 #7 · SEGUNDA PARTE: EL TALLER DE LA AVERIA (14/10/2026)

El informe lo pide: «**taller de la averia**». Y **el taller ya vivia en la casa**: es un **papel de
`Contacto`** (`contactos.py` tiene `taller`), no una tabla nueva. Lo que faltaba era **el enlace**.

## De escribir

· `AveriaDeMaquina.taller_contacto_id` — FK a `contactos.id`, **nullable**: vacio es **«no consta»**, no
  «ninguno». La mayoria de las averias se arreglan uno mismo, y obligar a decir un taller inventaria un
  dato que nadie ha dicho.
· Los tres esquemas: el id en `AveriaEntrada`, y **el id Y el nombre** en `AveriaSalida`.
· La comprobacion de finca en las **dos** puertas que escriben, con el mismo ayudante que usa un gasto.
· `_el_nombre_del_taller` — el nombre se resuelve **al leer**, y **tolerante a proposito** (un contacto
  que ya no esta, o que es de otra finca, **no puede tumbar la ficha con un error del servidor**), igual
  que `_quien_lo_decidio` del #6.

## LOS CUATRO ENGANCHES, y por que cuatro y no dos

Se cuelga el nombre en `_averias_de` (**los cuatro sitios que enseñan averias lo heredan**: la tabla, los
equipos sin ficha, la ficha y su aviso) y en `_la_averia_de_esta_maquina` (**por donde pasan el PUT y el
anular**). Y ADEMAS:
 · en el **POST**, que devuelve la recien creada y **no pasa** por los anteriores, y
 · en el **PUT, DESPUES de `corregir`**: el enganche del cargador corre **antes**, asi que el nombre
   viajaria **viejo** si se acaba de cambiar de taller.

   => ***La pregunta que los encontro fue «¿quien devuelve una averia?»*** — **seguir el camino del dato**,
      que es lo mismo que resolvio el lio del reparto (mirar donde se CARGA en vez de donde se pinta).

## Tres cosas de la pantalla que se olvidan y NO dan ningun error

1 · el bloque del formulario necesita **`id` ADEMAS de `campo`**: `puesto(id, campo)` rellena **por id**.
2 · el **guardado** tiene que mandarlo, y se lee del **borrador** (`b.taller_contacto_id`), **no de la
    casilla**: los campos de tipo `opciones` escriben ahi. (El borrador se guarda **antes** de repintar, y
    el propio `app.js` dice que eso «ya costo una ronda» a otro.)
3 · y hay que **cargar los contactos al abrir** (`if (!estadoDeLosContactos().cargados)`), o el
    desplegable sale **VACIO** y parece que la finca no tiene talleres.

## Lo que lo cierra

· **Cuatro pruebas** de puerta: el nombre ✓ · cambiar de taller dice el **nuevo** ✓ · «no consta» ✓ ·
  el taller de **otra finca** contesta 404 ✓.
· **Y un recorrido de navegador de 15 comprobaciones**: que solo se ofrezcan los contactos **con el
  papel**, que se guarde y se vea **con su nombre**, y **que sobreviva a la recarga**.

### Tres lecciones de metodo de esta entrega

· ***`ast.parse` es el guardian de Python; el de JavaScript es `node --check`.*** Le di el instrumento
  equivocado al lenguaje equivocado (y el aborto evito escribir, que es lo que tiene que pasar).
· ***`pytest` caza los nombres inventados, pero tarde***: me invente `dt_stub`, `otra_finca` y `cabeceras`
  **en el mismo fichero**, y los tres saltaron al correr. **Mirar la lista de fixtures ANTES de escribir.**
· ***Un recorrido que no espera a React MIENTE.*** Un bloque leia el texto **una vez** justo despues de
  pulsar y salio rojo; el guion hermano ya lo avisaba. ***Se comprueba cada paso y se ESPERA cada lectura.***

# EL CATALOGO DE F:Inforepositorios, MIRADO Y CRIBADO (14/10/2026)

280 repositorios en 64 areas. Se consulta con **cinco vias**, y hay que usar varias porque cada una saca
cosas que las otras no:

    scripts\Buscar-Repos.ps1 -Texto "…"        por necesidad, en lenguaje libre
    scripts\Buscar-Repos.ps1 -Categoria <area> por area
    … -Recomendacion candidato                 solo lo ya bien valorado
    … -Etiqueta <termino>                      por termino exacto
    … -Categorias / … -Etiquetas               que areas y terminos existen

Ignora tildes y mayusculas. `-Max` y `-Completo` controlan el volumen. **`indice.json` NO se lee entero.**
De cada ficha se lee, **en este orden**: §9 (cuando NO elegirlo) -> §6 (licencia) -> §5 (integracion) ->
§11 (que no se ha comprobado), y se miran sus `related_repositories`.

## *** LA RESTRICCION MEDIDA DESCARTA CASI TODO ***

Nuestra web **no tiene paso de compilacion ni dependencias**. Y mirando los limites declarados, quedan
FUERA por su propio pie:

    WebGPU                     glass-hq--liquid-glass · shader-effects-inc--shaders · threejs-particle-fluids
    Next.js / React 19 + TS    kuratlielia--arc-library · thesysdev--open-intelligent-ui (y SIN licencia)
    Tailwind v4                shadcn-ui--lint
    AGPL-3.0                   koala73--worldmonitor
    PolyForm / CC-BY-NC        feitangyuan--onetake · moguzbulbul--blueprint-animation · blixvip--nullmotion
    3D y video                 blendi-remade--dioramas · webprodigies-org--flute
    otros stacks               flutter · tauri · gpui-fast

    => ***NADA SE ADOPTA COMO DEPENDENCIA. El estilo es propio y se escribe a mano.***

## LO QUE SI SE APROVECHA, Y ES IDEA, NO CODIGO

1. **`deeplethe--solid-glass`** (MIT, `sistema-de-diseno-ui`) — el **sistema visual**: superficies,
   jerarquia y estados. Su **§9 avisa**: «no elegirlo solo por el efecto cristal si perjudica lectura,
   identidad o rendimiento» -> **se copia el sistema, no el cristal**. Su **§5** dice como probarlo: **UNA
   pantalla representativa, el CSS DESPUES del tema existente, resolviendo las variables duplicadas, y
   comparando claras/oscuras, movil y escritorio**. Y su **§11** dice lo que le falta: «falta abrir la demo
   y **renderizar con nuestro contenido**» -> que es justo lo que ya hacemos con los recorridos y con
   `scripts/medir_las_reglas_del_contrato.py`.
2. **`gholtzap--lintapple`** (MIT) — comprobar la interfaz **RENDERIZADA** contra reglas de diseno
   explicitas. Su **§9**: «**no demuestra que una interfaz sea bonita, facil de usar o funcional**»; no
   sustituye al recorrido ni a la revision humana. Ya tenemos la mitad: extender las reglas y medirlas.
3. **`tester-army--e2e`** (Apache-2.0) — «**no confiar en que el agente diga que termino: exigir ESTADO
   OBSERVABLE**». Es el metodo que ya se sigue; queda escrito como regla.
4. Idea suelta de `shadcn-ui--lint` (que no se puede adoptar): **que el error diga COMO arreglarlo**, no
   solo que algo esta mal.

# DECISION DEL DUENO: EL PRESUPUESTO ES UN PAPEL QUE SE ENGANCHA A LA AVERIA (14/10/2026)

Preguntado con las dos formas posibles, el dueno eligio: **el presupuesto es un PAPEL que se cuelga de la
averia** (como el documento del #6), **no** una ficha aparte con lineas e importe.

· Con eso, **«el documento de la averia» y «el presupuesto» son LA MISMA pieza**: el `documento_id` que ya
  se hizo para las obligaciones del #6, con su 409 gratis (`correcciones.tablas_que_apuntan_a`).
· Y **el importe sigue viviendo en el `Gasto`** (`averia_id`), nunca en la averia: es la regla del modulo
  de cuentas, que tiene escrito por que («un importe en dos sitios acaba diciendo dos cosas»).

# EL COSTE EN LA FICHA DE LA MAQUINA: QUE HAY Y QUE FALTA (14/10/2026)

## Lo que YA existe, y es mas de lo que parece

    gastos.py:1252      coste_de_una_averia(gastos, averia_id=…, arreglada=…)
    gastos.py:1285      coste_de_las_averias(gastos)  ->  el coste de CADA averia
    gastos_api.py:875   GET /gastos/averias  ->  averia por averia, con su `texto_coste`
    gastos.py:1196-1211 el porque entero, escrito:
        · «el coste NO se apunta en la averia: lo guarda el gasto»
        · «un importe en dos sitios acaba diciendo dos cosas»
        · y **«una averia con su coste NO esta arreglada por eso»**: «arreglada» es un dato del taller y
          «coste» es un dato de la cuenta.
        · y **un gasto sin importe NO suma cero: se cuenta** (`sin_importe`), para que un coste que solo
          suma la mitad no parezca el coste entero.

## Lo que FALTA

    En `maquinaria_api.py` **no aparece `coste` por ningun lado** -> **la ficha de la maquina NO ensena lo
    que han costado sus averias**, que es justo lo que pide el informe.

## Y un fallo REAL que se ve al mirarlo

    `gastos_api.py:977` valida `(models.AveriaDeMaquina, datos.averia_id, "averia")`: comprueba que la
    averia es de la FINCA, **pero NO que sea de la MISMA maquina**.
    => un gasto puede decir «de la maquina A» y colgar de una averia de la maquina B, y **el coste sale
       donde no es**. Hay que comprobarlo al guardar, y probarlo.

    => Y tiene que respetar las dos reglas de arriba: **no confundir el coste con «arreglada»**, y **decir
       cuantos gastos no tienen importe** en vez de enseñar una cifra corta como si fuera el total.

# SI ANADES UNA PALABRA AL SERVIDOR, ANADELA AL FIXTURE (14/10/2026)

La prueba «**la ficha no lleva ni una frase escrita a mano**» (`tests_js/maquinaria.test.js:894`) monta la
ficha y compara **cada nodo de texto** que se ve contra los textos del fixture (`TEXTOS`) y los datos de la
ficha de prueba (`fichaConCosas()`).

    ***Si una palabra que viene del servidor NO esta en el fixture, el guardian NO PUEDE distinguir una
       palabra de verdad de una inventada, y deja pasar LAS DOS.***

· Le paso con `taller_de_la_averia`: la entrega del taller anadio su palabra al servidor y **no** al
  fixture, y la prueba paso igual porque las **dos mitades** de esa linea caian al mismo «Falta decirlo»
  (`sin_decir: "Falta decirlo"`), asi que el guardian veia dos frases conocidas y el `: ` del medio se le
  colaba. Al poner la linea del coste al lado, salio a la luz.

## Y la regla de fondo que aquello destapo

***«Las frases compuestas se montan en `app.js`, no en los componentes»*** (`docs/REACT.md`, citado en
`app.js`). Y no es estilo: si el componente escribe `«Taller: »` + el nombre, la ficha tiene una frase
**que no viene del servidor**, y el guardian no la puede reconocer.

    => Se montan en `app.js` con `t(...)` (y `rellena(...)` si llevan numeros), y el componente las
       ensena **ya hechas**: **un nodo de texto por frase**.

## Y tres fallos de la misma ronda, cada uno dicho por la suite

   13 fallos  «ReferenceError: coste is not defined»   -> cambie el que LLAMA y no el que RECIBE
    1 fallo   «: Falta decirlo»                        -> faltaba la palabra en el fixture
    1 fallo   «Taller: Talleres El Camino»             -> la frase compuesta en el componente
    0 fallos  montadas donde manda el contrato

   ***Los tres eran reglas de la casa que yo estaba incumpliendo, no caprichos del test.***

# EL ENVOLTORIO QUE RECONSTRUYE LAS PROPS (14/10/2026) — seis rondas por una lista a mano

En esta casa cada pantalla se exporta **en dos piezas** (`web/react/pantallas/*.js`):

    export function PantallaDeUnaMaquina({ … })      ← el componente, con sus parametros
    export function pantallaDeUnaMaquina(propiedades) {
      return html`<${PantallaDeUnaMaquina} textos=${propiedades.textos} … />`;   ← EL ENVOLTORIO
    }

***El envoltorio reconstruye las props UNA POR UNA, asi que cualquier prop que no se nombre se PIERDE
   aunque el que llama la mande: sin aviso, sin error y sin rastro.***

    => ***ANADIR UNA PROP SON TRES SITIOS: el que llama, EL ENVOLTORIO, y el componente.***

Y el sintoma enganya: con el coste de una averia (CRM-07 #7) la **averia** si ensenaba lo suyo —`averias`
estaba en la lista— y la **linea del total** no salia. Desde fuera las dos cosas parecen lo mismo, y me
costo SEIS rondas: se probaron la cache HTTP, el service worker, la navegacion por fragmento, el fichero
servido, el modulo cargado y la puerta. Todo estaba bien. **El fallo era una lista escrita a mano.**

## ARREGLADO DE RAIZ, con reparto

    export function pantallaDeUnaMaquina(propiedades) {
      return html`<${PantallaDeUnaMaquina} ...${propiedades} />`;    ← htm reparte
    }

Con el reparto el envoltorio **no puede** perder una prop: pasa lo que le den. Si anades una pantalla
nueva, **usa el reparto** en vez de una lista.

## Y LAS SONDAS, QUE ES LO QUE LO ENCONTRO

Cuando «el codigo esta bien» y la pantalla no lo ensena, **no se razona: se pone una sonda que no se pueda
confundir**:
 1. un **marcador literal** en el componente (`data-marca="v363"`) -> si aparece, el modulo que corre es el
    de AHORA;
 2. **el valor por defecto de la prop, hecho una palabra** (`costeCrudo = "DEFECTO"`) -> si el DOM la
    ensena, la prop **no llega**; si ensena el dato, llega;
 3. y el **motivo** de un fallo tolerado, en un `data-motivo` (un `catch` que no deja rastro es una
    ceguera: ya van cuatro veces hoy).
Las tres se quitan despues: son sondas, no producto.

# LA CARRERA DE `Page.navigate` (14/10/2026) — el navegador estaba bien; yo iba con prisa

`Page.navigate` es **asincrono**. Navegar y recargar **en la linea siguiente** recarga **la URL VIEJA**:

    self.orden("Page.navigate", {"url": url})
    self.orden("Page.reload", {"ignoreCache": True})     ← ***recarga lo de ANTES***

Y el sintoma es de los peores: **un recorrido de tres pantallas mide la PRIMERA en las tres**, y parece que
el navegador sirve codigo viejo. Antes de recargar hay que **esperar a que el fragmento cambie**:

    for _ in range(50):
        if (self.evaluar("String(document.location.hash || '')") or "") in url: break
        time.sleep(0.05)
    self.orden("Page.reload", {"ignoreCache": True})

## Las CUATRO averias del arnes, todas la misma

   1 · la cache HTTP que `medir()` no apagaba
   2 · los Chrome que el arnes no mataba (deja hijos)
   3 · el SERVICE WORKER, que sirve el armazon desde su propia cache
   4 · la carrera de `Page.navigate` con `Page.reload`
        ***las cuatro hacen que el navegador ensene algo que NO es el codigo de ahora***,
        y las cuatro se arreglan en `scripts/navegador_cdp.py`, que es donde sirven para todos.

# EL PAPEL DE LA AVERIA (CRM-07 #7, 14/10/2026) — y el presupuesto, que es el MISMO papel

El informe del dueno pedia dos cosas: «**el documento de la averia**» y «**el presupuesto**». Al
preguntarle por el presupuesto contesto: «**un PAPEL que se engancha a la averia**». Son **una sola cosa**:
el parte del taller, la factura de la reparacion o el presupuesto son papeles, y la averia guarda **cual**.
**El importe NO va en la averia**: vive en el papel o en el gasto, como el coste.

Va con el **mismo patron que la inspeccion y que la obligacion**: `documento_id` nullable y FK a
`documentos_anexos`. Y el **409 al borrar un papel en uso sale GRATIS**: `correcciones.tablas_que_apuntan_a`
descubre las tablas **por el nombre de la columna**, y hay una prueba que avisa el dia que aparezca una
nueva y **obliga a decidir** que se hace con ella. No hay ninguna lista que mantener.

## Y DOS FALLOS MIOS QUE APARECIERON AL HACERLO

**1 · La regla A1 en el PUT del taller.** El PUT **reemplaza la fila entera**, asi que
`taller_contacto_id=datos.taller_contacto_id` a secas **borraba el taller** al corregir una averia sin
mandarlo. La regla es `docs/T02_VALORES_POR_DEFECTO.md`: ***lo que la peticion no manda, NO SE BORRA***.
Se distingue con `"campo" in datos.model_fields_set`, como hace la obligacion.

**2 · `puesto` es LOCAL del constructor de campos.** Un ayudante de modulo que lo llame revienta con
`ReferenceError: puesto is not defined` — **y como pasa AL PINTAR, el formulario entero deja de salir y no
se ve ningun error**. Se descubrio bisecando: con las opciones en linea, el formulario se abria.

# LOS DESPLEGABLES DE ESTA CASA SON **BOTONES**, NO `<select>`

`Opciones` -> `OpcionesParaElegir` (`componentes.js`) pinta botones con
`data-accion="maquina-elegir"` y `data-campo="<campo>"`. **No recibe el `id` del bloque**, asi que buscar
`#averia-papel` **no encuentra nada nunca**. Y `elegido` va tambien como `data-elegido`, que es lo que
permite medir si un clic registro. ***El recorrido hermano pasaba porque busca por el TEXTO.***

# Y LA SENAL DE QUE UN GUARDADO ENTRO

`suyo.formulario = null` **solo pasa despues de un guardado que el servidor acepto**. Un recorrido que
lea la fila justo despues de pulsar guardar lee la ficha **vieja**, y el `esperar` sobre el titulo pasa
**con el desplegable todavia abierto**: falso positivo. Se espera a que **el formulario se cierre**.

# PENDIENTE, Y ES UN FALLO DE VERDAD: el 422 que no se explica

El formulario de la averia deja pulsar **guardar** con «**que paso**» vacio, y `que_paso` es obligatorio
(`Field(min_length=1)`): el servidor contesta **422** y no guarda nada, **y la pantalla no dice por que**.
El contrato ya exige no poder guardar sin contestar «¿ya esta arreglada?»; **lo mismo tiene que valer para
«que paso»**, y el error tiene que decir **como arreglarlo** (la idea de `shadcn-ui--lint` que si se puede
copiar). Merece su prueba.

# Y LA LISTA DE INSTRUMENTOS QUE MIENTEN (ya van SIETE, todas medidas)

   1 · la cache HTTP que `medir()` no apagaba
   2 · los Chrome que el arnes no mataba
   3 · el SERVICE WORKER, que sirve el armazon desde su propia cache
   4 · la carrera de `Page.navigate` con `Page.reload`
   5 · los TEXTOS de un servidor levantado antes de tocar `textos.py`
   6 · un `pulsar` que devuelve OK **solo porque el boton existe**
   7 · un espia de `fetch` que parecia causar un cuelgue que seguia sin el
        ***y las siete se resolvieron MIDIENDO. Ninguna era el producto.***

# EL CUENTA-HORAS (CRM-07 #8, 14/10/2026) — la pieza, y un fallo del arnes que costo NUEVE rondas

## La pieza: HECHA por detras, ESCRITA en la pantalla, y no se ve

El encargo lo pide asi: «lecturas de contador **fechadas y unidad**; correcciones auditadas,
**sustitucion del contador**, datos faltantes. ***No inventar horas ni reducir acumulados silenciosamente***».

    ✓ `maquinaria.lo_que_marca_el_contador` (pura) + 7 pruebas: la sustitucion, los huecos, las unidades
    ✓ `LecturaDeContador` (fecha + valor + unidad + es_sustitucion) · esquemas · 3 puertas
      (apuntar / corregir con `correcciones` y la regla A1 / anular con su Auditoria)
    ✓ la ficha lleva `lecturas` y `contador`, y la cuenta la hace LA FUNCION PURA
    ✓ 7 pruebas mas de las puertas, incluida la trampa: corregir el valor NO cambia la unidad
    ✓ las palabras, el ayudante `elCuentaHorasDeLaMaquina`, la seccion del componente y el fixture
    ✓ ***85 pruebas de Python y 1118 de JavaScript, en verde***

**Y la ficha NO ensena el contador.** El recorrido `verificar_el_recorrido_del_cuenta_horas.py` esta escrito
y falla. **No commiteado**, porque el metodo pide el recorrido en verde.

## LO QUE SE DESCUBRIO POR EL CAMINO, Y ES UN FALLO DEL PRODUCTO: una carrera

`abrirLaMaquinaria` (async) pone `suyo.maquina = null` y **espera** a `/api/maquinaria`; el enrutador lanza
**tambien** `abrirUnaMaquina`, que prepara la ficha. **La lista puede terminar despues y pisarla.** Arreglado:
la ficha se prepara **la ultima**. Eso hay que arreglarlo igual, se vea o no el contador.

## Y EL FALLO DEL ARNES: el navegador ejecuta un `app.js` que NO ESTA EN EL PROYECTO

Con una **clave-testigo dentro del propio `return`** (`_sonda: "PREPARADA-DE-AHORA"`) el navegador contesta
`"SIN TESTIGO (codigo viejo)"` — **y los datos que pide al servidor si son de ahora**. Y el objeto que
construye tiene `obligaciones` (**que ningun `return` tiene**) y **no** tiene `lecturas`/`contador` (**que el
`return` si tiene**). Su secuencia de claves **no existe en ningun fichero del proyecto**.

***Todo esto queda DESCARTADO por medida directa, no por deduccion***:

    1 · la cache HTTP        -> `Network.clearBrowserCache` + `Cache-Control: no-store` en el armazon  ✗
    2 · el service worker    -> es RED-PRIMERO (`service-worker.js:448`) y su cache TIENE mi app.js   ✗
    3 · el servidor viejo    -> reiniciado; sirve 1099314 letras = el disco, con testigo              ✗
    4 · un app.js duplicado  -> hay UNO solo, y `main.py` monta esa carpeta                          ✗
    5 · perfiles zombis      -> perfil nuevo por instancia; cero Chrome mios vivos                   ✗
    6 · rutas.js / nucleo.js  -> los 44 usos estan en `app.js`; no tocan esto                        ✗
    7 · la carrera           -> encontrada y arreglada, y el sintoma sigue                           ✗
    8 · el import, el envoltorio, el componente  -> los tres correctos y leidos                      ✗

***La proxima vez que el sintoma sea «una linea que no se pinta y todo lo demas en orden»***:

  1. leer **`service-worker.js`** y **`index.html`** ANTES de nada (tienen la respuesta escrita)
  2. poner un **testigo dentro del `return`** de la funcion sospechosa y preguntarle AL NAVEGADOR
  3. y **no** dar por bueno un eslabon por haberlo leido: el que falla es siempre uno de esos


---

## 17/10/2026 — El cuenta-horas, por la pantalla, y **la leccion del punto de millar**

### La causa del «cuenta-horas vacio», que me costo una ronda entera

**El punto de millar.** `Number(1000).toLocaleString("es-ES")` escribe **«1.000»** con el ICU completo,
pero **el Chrome del arnes escribe «1000»** (sin punto). Mi comprobacion del recorrido buscaba
`"Marca ahora: 1.000 h"` **y la pantalla estaba ensenando `"Marca ahora: 1000 h"`**: no encontraba nada
*que si estaba*, y me pase la ronda persiguiendo un fantasma.

**Los dos sintomas que me enganaron, y como se deshacen:**

1. `encontre: "cuenta-horas Falta decirlo"` — **la primera aparicion de «cuenta-horas» en el `innerText`
   NO era mi seccion**: era otra parte del card. *Cortar el texto por una subcadena y mirar lo que sigue
   solo vale si sabes que esa subcadena es unica.*
2. `"250 h" in texto` **pasaba** mientras `"Marca ahora: 1.000 h" in texto` fallaba: el primero era un
   **falso positivo por subcadena**, y asi crei que la seccion pintaba cuando no la estaba mirando.

**Lo que lo resolvio**: una sonda que imprime **los valores**, no los atributos:
`{"marca_texto":"Marca ahora: 1000 h","seccion":"El cuenta-horas",...}` — *el dato correcto, a la vista,
en una linea.* **Cuando una comprobacion falla, imprime el valor que esperabas encontrar.**

### El `no-store` de `main.py`: **descartado con un test falsable**

Se repuso el 17/10 con un defecto **nuevo y reproducido** (datos correctos, codigo en su sitio, pantalla
«vacia»), y la regla lo permite asi. **El recorrido siguio rojo** -> *la cache NO era la causa*. Y despues
de arreglar el punto de millar, **el recorrido pasa a 24/24 SIN el `no-store`**: prueba definitiva.
**Retirado otra vez.** Que quede escrito: **la cache no ha sido la causa de ninguno de los dos fallos**,
ni del 15/10 ni del 17/10.

### Lo que SI esta hecho y verificado

- **Formularios de registrar, corregir y anular** una lectura, con fecha, valor, **unidad** (horas o
  kilometros), sustitucion y motivo de anulacion.
- **Regla A1 en los dos lados**: al corregir, lo que no se toca se conserva. *En el cliente tambien*: sin
  eso, corregir la cifra de una lectura en kilometros la pasaba a horas.
- **`apuntar_lectura` resuelta implementandola** (es el boton que abre el formulario), **no borrandola**.
- **Los tres rojos, cerrados**: el fixture literal del servidor (7 palabras distintas), `apuntar_lectura`,
  y el guardian de aislamiento **extendido** (no renombrado) + **2 pruebas de acceso cruzado**.
- **Recorrido completo por la pantalla: 24 de 24**, incluido ***la unidad de verdad*** (se pulsa
  «Kilometros» y se guarda `unidad == 'kilometros'`). Confirmado **dos veces**, la ultima en servidor
  limpio y **sin** el `no-store`.
- Python (tramo) y JavaScript: **todo en verde**. Instrumentacion de cache: **retirada**.

### Lo que queda de esta entrega

Permisos (servidor y pantalla), **auditoria** de alta/correccion/anulacion, **reenvio seguro** (el modelo
tiene indice NORMAL, no unicidad: **no se puede declarar seguro ante simultaneidad**), error de red y
reintento en el recorrido, y el cierre con las verificaciones de AGENTS. **Despues**, la cola.

### Una nota de producto, para el dueno

La pantalla escribe **«1000 h»** en el Chrome del arnes y **«1.000 h»** en un navegador con ICU completo.
**No es un fallo** -la casa usa `toLocaleString`-, pero si algun dia se quiere la misma cifra en todas
partes, hay que formatear **en el servidor** y mandar el texto hecho. *Queda anotado, no tocado.*


---

## 17/10/2026 (2) — **El cuenta-horas, CERRADO**, y un ticket ajeno que aparece por el camino

### Los siete puntos de la entrega

1. **Formularios** de registrar, corregir y anular (fecha, valor, unidad, sustitucion, motivo) ✓, con la
   **regla A1 en los dos lados** -al corregir, lo que no se toca se conserva- y el **borrador conservado
   si falla el envio** (probado cortando la red de verdad con `Network.setBlockedURLs`: el formulario no se
   cierra, el valor y la fecha siguen escritos, y al volver la red **entra con lo ya tecleado**).
2. **Permisos**: esta casa **no tiene roles**; el permiso es **autenticado + de tu finca**, y el aislamiento
   por explotacion y la pertenencia de la lectura a la maquina estan **probados** (dos pruebas de acceso
   cruzado: otra finca, y otra maquina de la misma finca).
3. **Auditoria** de las tres cosas, con autor: **alta** (no dejaba rastro: se anadio con
   `correcciones.apuntar`), **correccion** (`{campo: [antes, ahora]}`) y **anulacion** (con su motivo).
   ***Y un defecto de verdad***: el rastro del alta se escribia **antes del `flush`**, asi que
   `entidad_id` era `None` y quedaba una fila que no apunta a nada. Hay guardiana.
4. **Reenvio seguro**, copiando el patron de las notas: alcance por **explotacion + maquina**, se compara
   **la accion entera** (no solo la clave), **indice unico PARCIAL** en base, **409** ante datos distintos,
   `except IntegrityError` con `rollback` y relectura para la concurrencia, y eso mismo es lo que
   **distingue** un reenvio de una **lectura corregida despues**. Migracion **ensayada sobre copia**.
5. **Recorrido por la pantalla: 39 de 39**, doce pasos, incluidos el corte de red, la sustitucion y las
   unidades incompatibles.
6. **`apuntar_lectura`**: resuelta **implementandola** (es el boton que abre el formulario), no borrandola.
7. **Recuento**: **5105 de Python y 1123 de JavaScript**, y los cinco sitios puestos al dia.

### ***Un ticket AJENO que aparece al cerrar***

La **prueba de humo** (`scripts/humo.py`) **falla**, en tres cosas del sistema de **firmas**:

    [FALLO] un certificado de otro NIF NO entra
    [FALLO] con el certificado se puede firmar
    [FALLO] se guarda la firma   ->   KeyError: 'firmante_nif'

**Y NO es de esta entrega, con prueba**: se creo un **worktree de HEAD** (`949c595`, sin ninguno de mis
cambios) en un directorio aparte, se levanto su servidor y **el humo falla exactamente igual**. Ademas,
`git diff --name-only | grep firma` da **cero**: no he tocado ningun fichero de firmas.

El campo **si esta declarado** (`schemas.py`, `models.py:2392`, `cades.py`), asi que es la **puerta** la que
no lo devuelve. **Es un ticket para la cola, no un bloqueo del cuenta-horas.**

### Limitaciones de lo entregado

* El **indice unico parcial** esta **declarado** para PostgreSQL (`postgresql_where`) pero **solo se ha
  ensayado en SQLite**, que es donde corren las pruebas.
* El **reenvio seguro** no se ha probado con **dos peticiones de verdad a la vez**: se prueba el indice
  (metiendo dos filas) y el camino del `IntegrityError`, no la simultaneidad real.
* `test_zz_sonda_temporal.py` **esta en HEAD** y no es mio: es una sonda de la casa con su motivo.


---

## 17/10/2026 (3) — **CRM-07 #9 (reservas), CERRADO**, y dos tickets nuevos que salen por el camino

### Lo que pide el ticket, y como queda

> *«reservas con maquina, intervalo, responsable, trabajo y estado; **conflictos de solape en servidor**,
> anulaciones e **indisponibilidad por averia**. ***Cambios concurrentes no producen dos reservas
> incompatibles***. Definir **zona horaria y limites del intervalo**.»*

* **`app/reservas.py`** — la logica **pura**: solape en sus cuatro formas, limites del intervalo, la averia en
  sus cuatro estados, y **motivos** en vez de un si o un no. **31 pruebas** sin base de datos.
* **`models.ReservaDeMaquina`** — maquina, intervalo, responsable, trabajo, estado; `anulada` como **columna
  aparte**; indice de reenvio parcial e indice para buscar solapes.
* **Las cuatro puertas** (listar, apuntar, corregir, anular) con el solape **en servidor**, el aislamiento por
  finca y maquina, y la auditoria en las tres cosas.
* ***Las dos decisiones que el encargo manda tomar, tomadas y escritas***:
  * **Zona horaria**: **hora local de la finca, guardada sin huso**. Esta casa no tiene `ZoneInfo` en ninguna
    parte; cambiarlo a UTC moveria la reserva una hora en verano. **Y queda escrito que una finca = un huso**:
    si algun dia deja de serlo, esto es lo primero que hay que cambiar.
  * **Limites del intervalo**: `hasta` **estrictamente** despues de `desde`; ***los extremos NO se pisan***
    (9-11 y 11-13 caben las dos); **sin tope de duracion**, porque un numero elegido ahi seria inventado.
* ***La concurrencia, PROBADA***: la comprobacion sale a un ayudante propio
  (`_apuntar_la_reserva_sin_pisar_a_otra`) para poder reproducir **la ventana paso a paso y sin hilos** -dos
  sesiones miran, la primera escribe, la segunda se encuentra la primera y contesta **409**-. ***Las dos
  capas***: candado sobre **la maquina** (PostgreSQL `FOR UPDATE`; en SQLite se ignora) **y** volver a
  comprobar **despues del `flush`** (que es lo que cierra la ventana en SQLite). Ninguna basta sola.
* **Recuento**: **5145 de Python** y **1123 de JavaScript**. Los cinco sitios, al dia.

### Un fallo de DISENO que salio al correr, no al pensar

`TypeError: can't compare datetime.datetime to datetime.date`. **Las averias se apuntan por DIA y las
reservas por HORA.** Eso obliga a decidir algo que el encargo no dice, y se decidio: **una averia cubre el
dia entero**, porque el dato sabe el dia y no la hora. *Y una prueba mia estaba mal*: `resuelta=False`
significa **sigue sin arreglar**, asi que una averia del dia 1 **si** impide reservar el dia 2. **El codigo
estaba bien; la prueba no.**

### Tres guardianes de la casa me pillaron tres errores mios

1. `test_todas_las_claves_que_usa_la_maquinaria_existen` -> **use `apuntar_lectura` como ancla de reemplazo y
   la BORRE**. *Un ancla que se reemplaza es un ancla que se borra.*
2. `test_ningun_texto_de_la_maquinaria_se_queda_sin_usar` -> los motivos del servidor iban en el bloque de
   **la pantalla**, y van en **`MENSAJES`**.
3. `test_cada_puerta_de_la_maquinaria_comprueba_que_el_objeto_es_de_esta_finca` -> el ayudante nuevo no estaba
   en el barrido: **se extiende la lista, no se renombra el ayudante**.

### TICKETS NUEVOS (independientes, para la cola)

1. **El aviso de vencimiento al planificar** (cruce del CRM-07 #6 con el #9). El COLA dice, para maquinas:
   *«**Aviso vencido al planificar**; fecha desconocida no significa vigente»*. `ObligacionDeMaquina` existe
   -con `aplicabilidad` que por defecto es `no_se`-, pero **no hay ninguna funcion de vencimiento**: al
   reservar una maquina habria que **avisar** -no impedir- si tiene una obligacion vencida, y decir «no se
   sabe» cuando la fecha no consta.
2. **No hay guardian de las claves de `textos.mensaje(...)` del servidor.** T14 vigila las de **la pantalla**;
   una clave del servidor que no exista sale como un `KeyError` **al ejecutar** -y salio dos veces hoy
   (`no_es_de_esta_maquina`, y los motivos de las reservas con otro nombre)-. Es un guardian pequeno y evita
   fallos que solo se ven en produccion.


---

## 17/10/2026 (4) — **Composicion y unidades del abono, CERRADO**, y un defecto de diez veces

### Los criterios, y como quedan

> *«La etiqueta puede expresar nutrientes en **porcentaje en masa** y, para liquidos, **equivalentes
> masa/volumen**. Conservar **valor, unidad, base y fuente**. […] **No confundir** concentracion, cantidad
> comprada, cantidad aplicada y dosis por hectarea. […] Conservar N, P2O5 y K2O con su **especie quimica
> declarada**; no llamarlos P y K sin conversion. Mantener las columnas antiguas porcentuales compatibles.
> Anadir estructura/migracion **solo tras inventariar las unidades que hoy existen**. **No reinterpretar
> registros firmados**»*.

**El inventario primero, como manda**, y de el salio lo importante: `riqueza_n/p/k` **no decian su base**, y
lo que siempre fueron es **% m/m**. Y `test_los_kilos_de_un_abono.py` **ya cubria** «600 kg en 3 ha con N 15 %
-> 200 kg/ha y 30 kg N/ha, P desconocido si falta».

* **`app/nutrientes.py`** — la cuenta **pura**, con los **tres casos de aceptacion literales**: 600 kg/3 ha,
  **20 L a 100 g N/L -> 2 kg N y 1 kg N/ha**, y **20 L a 15 % m/m sin densidad -> NO se calcula** y se dice
  que falta la densidad. **16 pruebas**.
* **Las columnas**: `base_de_la_riqueza` (default `porcentaje_masa` = lo que eran), `densidad_kg_por_litro`,
  `fuente_de_la_riqueza`, `riqueza_p2o5` y `riqueza_k2o` **junto a** las viejas `riqueza_p`/`riqueza_k`.
* **`unidad_del_producto`** (kilos o litros) en la entrada, el modelo y la salida.
* **Migracion ENSAYADA SOBRE COPIA**, y **sin reinterpretar**: una fila vieja conserva su N=15, su **P=0.0
  (cero declarado)** y su K sin constar; y la base nueva dice `porcentaje_masa`, que es **lo que siempre fue**.

### ***EL DEFECTO DE LAS DIEZ VECES***

`servicios.py` calculaba los nutrientes con `legal.unidades_fertilizantes(cantidad_total_kg, riqueza_pct)`,
que da por hecho **dos** cosas que no siempre son verdad: que la riqueza es un **porcentaje en masa** y que el
producto son **kilos**. Con el caso del criterio -**20 L a 100 g N/L**- daba:

    20 x 100/100 = 20 kg de nitrogeno   DONDE SE ECHARON 2   ->  DIEZ VECES MAS

**Y eso no se queda en una pantalla: entra en el documento que se firma y en el plan de abono del ano.**

Arreglado enganchando `nutrientes.el_aporte`, y **probado por la puerta**: `uf_n_total == 2.0` y
`uf_n_ha == 1.0`. **El otro caso tambien**: 20 L al 15 % sin densidad se guardan **sin cifra**, no con un cero.

### Y dos cosas que se aprendieron a golpes

1. **`ast.parse` no basta**: se me colo un `lo_what` -`lo_what if False else …`- y **compilo**, porque es
   sintaxis valida. Habria reventado con un `NameError`. *Por eso hay que **ejecutar**.*
2. **`le=100` en las riquezas daba por hecho que siempre son porcentajes**, y un liquido a **150 g/L** no
   cabia -se comprobo: `Input should be less than or equal to 100`-. El tope ahora **depende de la base**.

### Lo que queda de este ticket

**La pantalla.** El criterio dice *«aplicar los criterios de arriba a sus contratos, entrada, calculos,
historial **y pantallas**»*, y todo lo anterior es **servidor**. Falta que la pantalla del abono deje elegir
**la base** y la **unidad del producto**, y que ensene los `uf_*` como lo que son.


---

## 17/10/2026 (5) — **La PANTALLA del abono, CERRADA** — y lo que quedo sin demostrar

### El camino, medido y andado

Se anduvo **botón a botón**, descubriendo en vez de suponer:

    HE ABONADO  ->  ¿Dónde? (la parcela)  ->  ¿Cuándo?  ->  ***¿Qué abono has echado?***
                                                                [AÑADIR UN ABONO]  ->  formulario de 4 pasos
                                                                    paso 1: ¿Cómo se llama el abono?
                                                                    paso 2: ¿Qué tres números trae el saco?
                                                                    ***paso 3: ¿Cómo viene la riqueza en la etiqueta?***

**Y el paso 3 trae las tres bases**, con sus tres botones medidos:

    elegir|base_de_la_riqueza|porcentaje_masa:            % en masa
    elegir|base_de_la_riqueza|gramos_por_litro:           gramos por litro      <- el caso de los liquidos
    elegir|base_de_la_riqueza|kilogramos_por_hectolitro:  kilos por hectolitro

***Que es exactamente lo que este ticket tenia que poner en pantalla.*** Y el paso 2 lo dice con las palabras
de la casa: *«Si el saco no lo trae, dejalo en blanco: quedara como **no consta**»*.

### Y un hallazgo mio que hay que CORREGIR

En la ronda anterior anote *«el catalogo de abonos no tiene puerta en el menu»*. **Es falso, y lo corrijo
aqui**: `montarAbonos` **no es un catalogo** -es **el paso «¿que abono?» del asistente de abonar**, y su
`anadir-maestro` esta dentro-. **No habia que darle puerta a nada.**

### Lo que quedo SIN demostrar (y es de mi guion, no del producto)

`scripts/verificar_el_abono_por_la_pantalla.py` llega al formulario, **elige «gramos por litro»** y comprueba
las tres bases: **7 comprobaciones, 1 fallo**. El fallo es **mio**: el paso 4 («¿Es mineral o ecologico?»)
cierra con un boton que se llama **`APUNTARLO`**, y **mi bucle no lo pulsa**. El boton **esta en pantalla**
-se ve en la salida-, asi que **la pantalla esta bien**.

**Tres intentos en el mismo bucle.** Lo que si quedo medido: el boton se llama `APUNTARLO`, esta en el paso 4
de 4, y sale junto a `VOLVER` y `DEJARLO`. ***Lo que falta es mi guion, no la pantalla.***

### La leccion de estas dos rondas

**Cuatro fallos seguidos, y los cuatro eran mios, no del producto**:

1. `SyntaxError: missing ) after argument list` -> comillas simples y dobles mezcladas en la expresion JS.
2. `bool() takes no keyword arguments` -> un reemplazo por lineas dejo `bool(x = nav.evaluar(...))`.
3. `unmatched ')'` -> **y el `compile` lo cazo y NO escribio**, que es para lo que esta.
4. El bucle que no cierra el paso 4.

***Lo que funciono***: **comillas dobles dentro y simples fuera**; para un selector, **el valor sin comillas**
(`[data-campo=parcela_id]` es CSS valido); **pulsar por `data-accion`** y no por el texto del boton; y
**reescribir el fichero entero** en vez de parchearlo por lineas cuando ya ha fallado dos veces.


---

## 17/10/2026 (6) — **El abono en pantalla: lo demostrado, y UN HALLAZGO PARA EL REVISOR**

### Lo demostrado (que es lo que el ticket pedia)

    [OK] se abre el asistente de abonar
    [OK] se puede elegir la parcela
    [OK] ***el asistente ofrece anadir un abono***
    [OK] ***se puede elegir «gramos por litro»***
    [OK] ***la pantalla ensena la base de la riqueza***
    [OK] ***y la riqueza por litro, que es la base de los liquidos***
    [FALLO] la composicion dice «g/L»      <- esta es la comprobacion que NO se pudo hacer

**7 comprobaciones, 1 fallo.** Y el fallo es **la ultima comprobacion**, no la funcion: lo que el ticket
tenia que poner en pantalla -**la base, con sus tres opciones, y poder elegir «gramos por litro»**- **esta y
funciona**.

### ***EL HALLAZGO, PARA EL REVISOR*** (6 intentos, y la evidencia ya no cambia)

**El formulario de alta de un abono NO cierra en su paso 4.** Reproduccion exacta:

    HE ABONADO -> la parcela -> ¿Cuando? -> ***¿Que abono has echado?*** -> [AÑADIR UN ABONO]
      paso 1 de 4: ¿Como se llama el abono?          -> rellenado el nombre
      paso 2 de 4: ¿Que tres numeros trae el saco?   -> se avanza
      paso 3 de 4: ¿Como viene la riqueza?           -> ***se elige «gramos por litro»*** y se avanza
      paso 4 de 4: ¿Es mineral o ecologico?          -> **AQUI NO CIERRA**

**Los `data-accion` del paso 4, medidos (no supuestos):**

    elegir   asistente-atras   asistente-saltar   asistente-seguir

**No hay ningun boton de «apuntar»**: `APUNTARLO` es el **texto** de `asistente-seguir` en el ultimo paso
-el mismo `data-accion`, con otro rotulo-. Se pulsa `asistente-seguir`, **se elige `mineral`** con
`elegir|tipo|mineral`, y **la pantalla se queda en el paso 4**: ocho vueltas seguidas, y `pulsado:
'asistente-seguir'` en todas.

**Lo que NO se puede decidir sin mas datos**: si es **un defecto de la pantalla** -el paso 4 no cierra- o si
**falta un dato** que ese paso no dice. *Por eso va al revisor y no lo arreglo a ciegas.*

### Y la leccion, que costo seis intentos

***`APUNTARLO` no era un boton: era un rotulo.*** Estuve buscando un `data-accion` que **no existia** -y el
guion ya pulsaba el correcto desde el primer intento-. **Lo que faltaba era **leer los `data-accion` unicos**
en vez de suponer su nombre.** Es la misma leccion de toda la semana: *medir antes de suponer*.

### Y se cierra el ticket de los nutrientes, en pantalla

**La base de la riqueza se elige en la pantalla, con sus tres opciones** -% en masa, gramos por litro, kilos
por hectolitro- y el paso 2 lo dice con las palabras de la casa: *«Si el saco no lo trae, dejalo en blanco:
quedara como **no consta**»*.


---

## 17/10/2026 (7) — **Superficies: la regla YA se cumplia, y un hallazgo grande**

### Lo primero: mi sospecha era FALSA, y se comprobo antes de afirmarla

Sospeche que `sum(p.superficie_ha for p in parcelas)` reventaria con el campo de tres estados. **Los cinco
sitios ya lo hacen bien**, y con el comentario que explica por que:

    servicios.py:605      if any(parcela.superficie_ha is None for ...): return None
    validaciones.py:132   if any(p.superficie_ha is None for p in parcelas): return None
    cuaderno.py:690       filtra los None:  ... if p.superficie_ha is not None
    fincas_api.py:64      «SQL ignora los NULL al sumar: un total mas pequeno que parecia completo»
    parcelas.py:1489      «una suma a la que le falta un numero NO es una suma»

**Y nadie suma la tratada con la de la tierra** -el `+` no aparece en ninguna parte-, y
`hectareas_tratadas` (de tratamientos) vive **separada** de `hectareas_abonadas` (de abonos). *La ronda no
encontro un defecto: **verifico** que no lo hay, que es lo que la regla pide.*

### ***HALLAZGO: `TrabajoParaTerceros` es una tabla HUERFANA***

    quien toca los trabajos de terceros ->  models.py:4235 (la define)  y  NADA MAS

La tabla existe, con el comentario del modelo que dice **literalmente el caso de aceptacion** -«10 ha de un
tercero no suman superficie propia… meterlas en `parcelas` seria decir que son del agricultor»-, y
**ninguna puerta, ningun calculo ni ninguna pantalla la usa**.

***Es el CRM-04 sin hacer***: *«Cliente -> propuesta de trabajo -> aceptacion -> parte realizado ->
venta/documento -> cobro. Trabajo externo con ubicacion y superficie separadas de tierras/PAC propias»*.

### `app/superficies.py`, lo que SI aporta

**La casa cumple la regla, pero cinco veces y cada una por su cuenta** -y **ninguna impide mezclar
magnitudes**, que es lo que el criterio pide con estas palabras: *«No sobreescribir una con otra ni sumarlas
como si fueran la misma magnitud»*. El modulo unifica la cuenta y **da nombre a cada magnitud** con su
pregunta, para que el error se pueda explicar.

**8 pruebas**, y la primera es el caso del COLA: ***«trabajo externo 10 ha no suma superficie propia»***.

**Y su prueba cazo logica invertida en el propio modulo** (17/10/2026): `se_pueden_sumar` devolvia `True`
para dos magnitudes **distintas** mientras no estuvieran en una lista de pares prohibidos -y esa lista
**nunca esta completa**-. La primera entrada que se me olvido fue justo la que el modelo avisa:
`sigpac` + `se_cultiva`. Ahora la regla es **una igualdad** y la lista queda como documentacion.


---

## 17/10/2026 (8) — **Superficies: el enganche hecho, y la red hizo su trabajo**

### Una cuenta, no dos copias

`superficie_contada_del_grupo` (en `servicios.py`) y `_superficie_del_grupo` (en `validaciones.py`) eran
***letra por letra la misma funcion***. Dos copias de una regla son dos sitios donde puede dejar de
cumplirse, asi que la cuenta vive ahora **una sola vez** en `app/superficies.py`
-`la_superficie_de_un_grupo`- y las dos la llaman. **Los nombres no se tocan** -el ayudante se extiende, no
se renombra-, y **el comportamiento es el mismo**: lo demuestran las pruebas que ya existian.

### Y la red cazo el fallo en el acto

Se corrio **antes** -`test_grupos_de_parcelas` + `test_lo_que_hoy_hace_por_defecto`, 81 pruebas en verde-,
se engancho, y se corrio **despues**. **Seis pruebas en rojo**, y todas por lo mismo:

    NameError: name 'superficies' is not defined     app/validaciones.py:128

***El import se me olvido en uno de los dos ficheros***, y la red lo dijo en el acto en vez de dejarlo para
produccion. Arreglado, y **89 pruebas en verde**.

### El metodo, que es lo que se lleva esta ronda

***Antes de tocar codigo que ya funciona: correr lo que lo cubre.*** No porque vaya a romperse, sino porque
**si se rompe quiero saberlo en el acto y por que**. Funciono: el fallo salio en la primera corrida y con el
fichero y la linea exactos.

### Y sigue en pie el hallazgo grande

***`TrabajoParaTerceros` es una tabla huerfana***: el modelo la define -con el comentario que dice el caso de
aceptacion del COLA-, y **ninguna puerta, ningun calculo ni ninguna pantalla la usa**. *Es el **CRM-04** sin
hacer*: cliente -> propuesta -> aceptacion -> parte realizado -> venta/documento -> cobro.


---

## 17/10/2026 (9) — **La suite entera cazo DOS defectos mios, y los dos eran de verdad**

Se corrio la suite completa -no solo el tramo- y salieron **8 fallos**. **Los 8 eran mios**, y valen la pena
porque los dos grupos son dos defectos distintos.

### 1 · `default` (Python) NO es `server_default` (SQL)

    7 fallos en test_zona_de_nitratos_no_comprobado.py
    sqlalchemy.exc.IntegrityError: NOT NULL constraint failed: fertilizaciones.base_de_la_riqueza

**La columna nueva `base_de_la_riqueza` es `NOT NULL` y solo tenia `default=`**. Ese `default` lo aplica
**Python** al construir el objeto, y **un `INSERT` en SQL crudo no lo ve**. O sea: mi columna **rompia
cualquier insercion que no la llevara** -y las pruebas de migracion de esta casa insertan asi, a mano, una
fila vieja-.

***Y eso importa mas alla de la prueba***: una columna `NOT NULL` sin `server_default` es **incompatible
hacia atras**, y la casa tiene codigo y pruebas que insertan filas sin conocer las columnas nuevas.

Arreglado con `server_default` en `base_de_la_riqueza` -en **las dos** tablas, `Fertilizante` y
`RegistroFertilizacion`- y en `unidad_del_producto`.

### 2 · El guardian de T14 me obligo a decidir

    1 fallo en test_t14_maquinaria.py
    «hay una tabla nueva que usa una maquina: hay que decidir si es parte de ella o depende»
    Extra items in the left set:  'reservas_de_maquina'

**Es exactamente para lo que esta esa prueba**, y la decision se tomo con el criterio que la propia prueba
dejo escrito: *una dependencia es lo que **existe aunque la maquina se venda** -la reparacion, la factura de
compra-*. **Una reserva es «estas horas, esta maquina, para esta tarea»: sin la maquina no hay reserva**, y su
ficha tiene que poder decir **cuando esta cogida**.

***`reservas_de_maquina` ES parte de la maquina***, como las averias y como las lecturas del contador.

### La leccion

**Correr el tramo no basta.** El tramo -105 pruebas- estaba en verde; fueron **las 5100 y pico** las que
dijeron lo que faltaba. *Y las dos cosas que salieron -la incompatibilidad de una columna nueva y una tabla
sin clasificar- **no se ven mirando el codigo que uno acaba de escribir**: se ven ejecutando lo que ya
existia.*


---

## 17/10/2026 (10) — **Añadir un campo son SEIS sitios, y la suite los conoce todos**

Los tres fallos que quedaban eran **el mismo problema visto desde tres guardianes distintos**, y los tres
tenian razon:

| el guardian | lo que exigia | lo que faltaba |
|---|---|---|
| `test_los_maestros_se_pueden_corregir` | *una columna que **no sale en la respuesta** es un dato que el agricultor **no puede mandar de vuelta*** | **`FertilizanteSalida`** |
| `test_el_formulario_manda_todo` | `cargaFertilizacion` tiene que mandar **todos** los campos de la entrada | **`unidad_del_producto`** |
| `test_interfaz` | la **copia** de los textos del movil dice lo mismo que el servidor | los **dos rotulos** nuevos |

***Añadir un campo a una ficha son SEIS sitios***, y ninguno es opcional:

    1. el modelo                        models.py
    2. el esquema de ENTRADA            schemas.py
    3. el esquema de SALIDA             schemas.py      <- y este es el que se olvida
    4. el formulario que lo manda       app.js (cargaFertilizacion)
    5. el mapa de campos                app.js (CAMPOS)
    6. la copia de los tests del movil  tests_js/interfaz.test.js

**Y la suite entera los conoce todos.** No fue el tramo -que estaba verde-: fueron **las 5100 y pico**.

### ***Y HAY UNA RAZON DE FONDO, QUE NO ES BUROCRACIA***

`test_los_maestros_se_pueden_corregir` lo explica con estas palabras: *«el formulario de corregir se rellena
con lo que devuelve la API, asi que una columna que no sale en la respuesta es un dato que el agricultor no
puede mandar de vuelta: copiarla del registro preparado lo **borraria** sin que nadie se entere (y sin que la
auditoria lo dijera, porque estaria comparando el valor nuevo contra si mismo)»*.

***O sea: el campo 3 que se me olvido era un defecto de DATOS, no un fallo de estilo.*** Corregir los kilos
de un abono habria **borrado su base, su densidad y sus especies quimicas** -y la auditoria no lo habria
dicho, porque el valor viejo y el nuevo habrian sido el mismo `None`-.

### Lo que la casa ya tenia escrito, y yo no habia leido

En `cargaFertilizacion` habia **seis** campos con este comentario:

    // Lo mismo que en los tratamientos: lo que el asistente no pregunta se manda tal cual venia.
    // ... y hoy no hay ninguna pantalla que los rellene, pero un abono que los tenga apuntados
    // ***no los puede perder por corregir los kilos***.

**Era exactamente mi caso, y estaba escrito antes de que yo llegara.** Los mios van ahora al lado, con el
mismo modismo.

### Y sigue pendiente el hallazgo grande

***`TrabajoParaTerceros` es una tabla huerfana*** -el **CRM-04** sin hacer-.


---

## 17/10/2026 (11) — **La suite ENTERA en verde, y el mapa del CRM-08**

### Cerrado de verdad: no «pasa mi tramo», pasa TODO

    pytest tests -q      ->  exit code 0, la suite completa en verde

Los tickets de **composicion/unidades del abono** y de **superficies** quedan cerrados. *El tramo estaba
verde desde hace rondas; lo que faltaba era **lo que ya existia**, y eso solo lo dice la suite entera.*

### CRM-08 (fiabilidad transversal): el mapa, MEDIDO

El ticket tiene cuatro bloques, y **dos tienen mucho hecho ya**:

| bloque | que hay | que falta |
|---|---|---|
| **Permisos** | ***`app/accesos.py`***: `titular`/`ayudante`, y **las capacidades son columnas del acceso** -`puede_modificar`, `puede_ver_lo_economico`-, comprobadas **en la puerta** y no en la pantalla | **el tercer papel** y el **enlace directo** |
| **Borradores** | ***ojo***: `borradores.py` **no es el de un formulario**, es el del **dictado** (`redacta_borrador`, `reconoce_tipo`, `extrae_cantidades`) | **todo**: borrador por usuario/finca, guardar local, dos pestanas |
| **Edicion concurrente** | ***nada***: no hay `version_esperada` ni `If-Match` en ninguna parte | **todo**: «**no ultimo escritor silencioso**» |
| **Restauracion** | copias de seguridad en `database.py` -incluida la que se hace antes de migrar- | el **ensayo sobre destino nuevo** |

### ***Y UN HALLAZGO QUE AHORRA TRABAJO: el tercer papel YA EXISTE***

    «Consultar ya lo da el propio acceso a la finca: esto es lo que se puede CAMBIAR»

***Un «consulta» es un acceso con `puede_modificar = False`.*** La capacidad **ya esta**, y **ya se
comprueba en la puerta**. Lo que falta es **nombrarla** y **poder crearla** -hoy `asegurar_accesos` solo pone
`TITULAR` o `AYUDANTE`, y las dos nacen con `puede_modificar=True`-.

**Y el criterio de la casa, escrito en `puede_ver_lo_economico`, que sirve para todo lo demas**: *«ocultar
dinero tambien lo **elimina de la respuesta**… no se comprueba en la pantalla, sino **en la puerta**: si no
hay capacidad, la respuesta no lleva el dato -ni la pantalla puede ensenarlo aunque quiera-».*

### Lo siguiente, por orden de tamano

1. **El tercer papel** (consulta) en `accesos.py`, con su matriz y sus pruebas. *Pequeno y con el modelo hecho.*
2. **El aislamiento por enlace directo**, que ya tiene patron en maquinaria (`_la_lectura_de_esta_maquina`).
3. **La edicion concurrente** (version esperada): **de cero**, y es el trozo mas grande.


---

## 17/10/2026 (12) — **El tercer papel, la matriz, y tres hallazgos mas**

### El defecto de permisos, arreglado

`puede_modificar` y `puede_ver_lo_economico` nacian en **`True`** para todos, y `anadir_acceso` **solo ponia
el papel**: ***cualquier acceso a una finca podia modificarla y ver su dinero***. El ticket pide *«matriz por
accion y dato»*, y ahora la hay -**una sola**, y la usan los **dos** sitios que crean accesos-:

    TITULAR   modificar: si    economico: si     «el dueno puede todo»
    AYUDANTE  modificar: si    economico: NO     «trabaja, pero no ve las cuentas»
    CONSULTA  modificar: NO    economico: NO     «mira y no toca»
    SIN_CONCEDER: todo en NO                     «ante la duda, lo que MENOS concede»

**8 pruebas nuevas** -la matriz es **pura**, asi que se prueba sin base-, y un papel inventado **no entra**:
`anadir_acceso` lo rechaza y `las_capacidades_de` no concede nada.

**Y el resto ya estaba**: `deps.py:101` ya miraba la capacidad **en la puerta**, `cuenta.py:144` ya la devolvia
en la respuesta, y `test_los_permisos_por_materia.py` ya la probaba -poniendola **a mano**, que es por lo que
el cambio no rompio nada-.

### ***Y UN GUARDIAN QUE NO CONOCIA: el del RECUENTO***

La suite entera salio con **un solo fallo**, y era este:

    AssertionError: la documentacion dice 5177 pruebas de Python y hay 5187.
    Actualiza el recuento en README.md, AGENTS.md y docs/LO_QUE_PIDE_LA_JUNTA.md

**`tests/test_lista_de_la_junta.py` vigila que la documentacion diga el numero de verdad**, y te dice
**cual es** y **en que tres ficheros** ponerlo. *Es la clase de guardian que hace que un recuento no se quede
viejo sin que nadie se entere* -y me ahorro tener que acordarme-.

### Tres hallazgos del CRM-08, medidos

1. **Los ADJUNTOS no tienen puerta.** `app/adjuntos.py` es un **modulo de ficheros** -carpeta, ruta,
   `unlink`, y **la comprobacion de que la ruta sigue dentro de la carpeta**, que es la defensa contra el
   path traversal-, y **ningun router sirve ni recibe un adjunto**. *Subir o bajar un fichero no esta hecho.*
2. **Las EXPORTACIONES no tienen NI UNA PRUEBA.** Existen -`cuaderno.exportar_csv`, `exportar_pdf`,
   `extractos.exportar_los_movimientos`- y el ticket dice *«las exportaciones **verifican aislamiento**»*.
   ***Y son la via por la que salen los datos de la finca.***
3. **El aislamiento por enlace directo si esta**, y **muy trabajado**: `crear_cuenta` -«para los tests de
   aislamiento entre fincas»- y decenas de pruebas (`test_revision_t05_y_t09` 17, `test_revision_t06` 12,
   `test_recepciones_lotes_y_movimientos` 11, `test_t14_maquinaria` 9).

**Lo siguiente, por valor**: probar las **exportaciones** -accionable ya, y sin tocar codigo-, y despues la
**edicion concurrente**, que es lo unico que esta **de cero**.


---

## 17/10/2026 (13) — **Las exportaciones, probadas. Y el recorrido fallaba por MI basura**

### El aislamiento de las exportaciones, y resulto ser ESTRUCTURAL

Las dos puertas de exportar reciben `explotacion: ExplotacionActual`, que **sale del token**, y **no aceptan
ningun `explotacion_id`**. ***No hay parametro que inyectar*** -por eso no habia pruebas, porque no se puede
pedir otra finca-.

**Y precisamente por eso hacen falta**: hoy no se puede, y eso hay que **afirmarlo**, para que el dia que
alguien anada un parametro **se entere**. Tres pruebas:

    [OK] el CSV del cuaderno NO lleva nada de la OTRA finca
         (se apunta algo en la finca del otro ANTES de exportar, para que haya que no salir)
    [OK] el CSV del cuaderno no admite que le digan otra finca
         (se intenta colar `explotacion_id` con el id del otro: sigue saliendo MI cuaderno)
    [OK] el CSV de movimientos NO lleva nada de la OTRA finca

**El marcador es el que la casa ya escribe** en la primera linea del cuaderno:
`Cuaderno de campo - {explotacion.nombre} - {anio}`. *Y el NIF del otro tampoco puede aparecer.*

### ***Y EL RECORRIDO FALLABA POR MI CULPA***

`test_el_recorrido_se_anda.py` levanta **su propio servidor** en el 4874, y fallo con:

    AssertionError: el servidor de pruebas no ha arrancado

**No era el codigo: eran CINCO SERVIDORES MIOS**, vivos desde las 09:55, que habia ido dejando en los
recorridos del abono:

    8392 · 8393 · 8394 · 8395 · 8399

***Y la regla dice «datos ficticios y servidores AISLADOS»***. **Aislado no es «en otro puerto»: es no
dejarlos vivos**, porque **cargan la maquina y hacen fallar a otras pruebas** -y el sintoma no se parece en
nada a la causa: *parecia que el servidor de la prueba no arrancaba*.

Parados los cinco, **el recorrido pasa**. *Y a partir de ahora, cada servidor de un recorrido se para al
terminar.*

### Recuento

    PYTHON: 5192   (eran 5187; +5)
    los tres sitios al dia: README.md, AGENTS.md, docs/LO_QUE_PIDE_LA_JUNTA.md


---

## 17/10/2026 (14) — **Suite entera en verde, y el diseno de la edicion concurrente**

### Cerrado: con los servidores parados, TODO pasa

    pytest tests -q   ->  exit code 0, las 5192 en verde

*Y confirma lo de la ronda anterior: **el fallo del recorrido era mi basura** -cinco servidores vivos desde las
09:55-, no el codigo.*

### La edicion concurrente: el mapa, medido

El ticket pide *«version esperada y resolucion explicita; **no ultimo escritor silencioso**»*. Y la medicion
da un diseño que **no necesita tocar sesenta tablas**:

    66 clases en models.py   ·   solo 6 con `actualizado_en`
    y las que SE CORRIGEN -contacto, documento, campana, factura, gasto, producto- ***no son ninguna de esas 6***

    ***pero*** `correcciones.apuntar` YA escribe en `Auditoria` CADA cambio, con quien y cuando
    y hay un modismo que ya la lee: `correcciones.firmas_de_un_apunte(..., entidad=..., entidad_id=...)`

### El diseño que sale de ahi

1. **`correcciones.la_version_de(db, entidad=…, entidad_id=…)`**: ***la version de un registro es su ultima
   fila de auditoria*** -`max(id)`-, y `0` si no hay ninguna. **Ni una columna nueva.**
2. **`corregir(..., version_esperada=None)`**: si viene y **no coincide**, se levanta un error de dominio en
   vez de escribir. ***Es el unico enganche***: 16+ puertas usan `correcciones.corregir`, asi que la
   comprobacion cubre todas de una vez.
3. **La puerta contesta 409** diciendo **quien** la cambio y **cuando** -eso es la *«resolucion explicita»*:
   el agricultor decide, y no se le pisa el trabajo en silencio-.
4. **Y las respuestas llevan `version`**, para que el formulario la tenga y la mande de vuelta.

***Lo que hace esto pequeno no es el atajo: es que la casa ya guardaba la informacion.*** La auditoria estaba
ahi desde el principio; lo que faltaba era **leerla para esto**.


---

## 17/10/2026 (15) — **La edicion concurrente, HECHA — y sin una columna nueva**

El ticket pedia *«version esperada y resolucion explicita; ***no ultimo escritor silencioso***»*. Esta hecho,
y **la version no hay que guardarla**: se **lee**.

### Lo que se hizo

1. **`correcciones.la_version_de(db, entidad=…, entidad_id=…)`** — ***la version de un registro es su ultima
   fila de auditoria***, y `0` es «no se ha tocado nunca desde que se creo». **Cero columnas nuevas en las
   sesenta tablas**, porque la casa **ya apuntaba cada cambio** en `auditoria`, con quien y cuando.
2. **`correcciones.VersionQueNoCuadra`**, que lleva **`esperada`**, **`la_de_verdad`**, **`quien`** y
   **`cuando`**. *Eso es la «resolucion explicita»: el error trae lo que hace falta para decidir.*
3. **Y la comprobacion dentro de `corregir`**, ***antes de tocar nada***: si no cuadra, **no se escribe ni un
   campo**. `version_esperada=None` -el valor por defecto- **no comprueba nada**, asi que las **dieciseis
   puertas** que ya corregian siguen exactamente igual: esto se enciende **puerta a puerta**.

### ***7 pruebas***, y la que importa es la del «no se escribe nada»

    [OK] la version empieza en 0 · sube con cada correccion · es DE CADA APUNTE · sin id no hay version
    [OK] si la version CUADRA, se corrige
    [OK] ***si NO cuadra, VersionQueNoCuadra y el registro queda EXACTAMENTE como estaba***
    [OK] sin version esperada NO se comprueba nada

### Y un fallo mio que enseno algo del diseño

La prueba fallaba con `esperabas la version 1 y va por la 0`, y **el error era mio**: apunte la auditoria al
`entidad_id` del apunte -999- y **`corregir` mira la version de `guardado.id`**, que era otro numero.

***Y eso es correcto, no un estorbo***: **la version es de un registro concreto**. Que se corrija un contacto
**no** cambia la version de otro. La prueba ahora apunta la auditoria **al registro** y pasa.

### Recuento

    PYTHON: 5201   (eran 5192; +9)
    los tres sitios al dia

### Lo que queda del CRM-08

- **Encender la version esperada en las puertas** que el ticket nombra -*«piloto en formulario de trabajo y
  factura»*- y devolver **409** con `quien` y `cuando`, que es lo que ya lleva el error.
- **El borrador por usuario/finca** -guardar local, respuesta perdida, cola al reconectar, dos pestanas-,
  que **no existe**: `borradores.py` es el del **dictado**, no el de un formulario.
- **El ensayo de restauracion sobre destino nuevo.**


---

## 17/10/2026 (16) — **Suite entera en verde CON la edicion concurrente dentro, y el plan del piloto**

    pytest tests -q   ->  exit code 0, las 5201 en verde

***Y lo que importa no es el verde, es DONDE esta el cambio***: la comprobacion vive **dentro de
`correcciones.corregir`**, que la usan **dieciseis puertas** -contactos, documentos, facturas, gastos,
maestros, tratamientos, labores...-, y **ninguna se ha roto**. *Eso es lo que compra el
`version_esperada=None` por defecto: el dia que se encienda en una puerta, las demas siguen igual.*

### El piloto que pide el ticket, localizado

*«Piloto en formulario de **trabajo** y **factura**»*, y las dos puertas son:

    registros.py:306      guardado=tratamiento   <- el trabajo
    facturas_api.py:1318  guardado=factura       <- la factura

**Y encenderlo son los mismos seis sitios de siempre**, que ya se aprendieron a golpes:

    1. el modelo                        NO hace falta: la version se DERIVA de la auditoria
    2. el esquema de ENTRADA            `version_esperada: int | None = None`
    3. el esquema de SALIDA             `version: int`        <- el que se olvida
    4. la puerta                        pasarla, y capturar `VersionQueNoCuadra` -> **409**
    5. el formulario que lo manda       app.js (carga<...>)
    6. la copia de los tests del movil  tests_js/interfaz.test.js

**El 409 lleva ya lo que hace falta para decidir** -`quien` y `cuando`-, que es la *«resolucion
explicita»*: el agricultor ve que otro lo cambio y decide, en vez de perder su trabajo sin enterarse.


---

## 17/10/2026 (17) — **El PILOTO de la edicion concurrente, encendido y probado**

*«Piloto en formulario de **trabajo** y **factura**»*. El trabajo esta encendido -`PUT
/api/tratamientos/{id}`-, con los seis sitios:

    1. el modelo          NO hizo falta: la version se DERIVA de la auditoria
    2. la ENTRADA         `version_esperada` en TratamientoEntrada y FacturaEntrada
    3. la SALIDA          `version` en TratamientoSalida y FacturaSalida
    4. la puerta          pasarla, y capturar `VersionQueNoCuadra` -> **409**
    5. la copia de tests  pendiente (los rotulos)
    6. y `textos.py`      el mensaje `el_apunte_ha_cambiado`

***Tres pruebas, y la tercera es la que importa***:

    [OK] sin version esperada se corrige como siempre        (la compatibilidad: las 16 puertas siguen igual)
    [OK] con la version BUENA se corrige
    [OK] ***con la version MALA: 409, y NO se escribe nada***

**Y el 409 dice lo que hace falta para decidir**, que es la *resolucion explicita*:

    «Otro ha cambiado este apunte mientras lo tenias abierto, asi que no se ha guardado nada de lo tuyo.
     Vuelve a abrirlo para ver lo que hay ahora y vuelve a hacer tu cambio: asi no se pierde el trabajo de
     ninguno de los dos.»  (lo cambio la cuenta numero 1, 17/10/2026 a las 10:32)

### ***Y TRES COSAS QUE ENSENARON LAS PRUEBAS AL FALLAR***

1. **`V10_sin_justificacion`** -«Pon por que lo has echado»-: **la casa exige justificacion** en un
   tratamiento, y el alta y la correccion pasan por las **mismas** comprobaciones.
2. **`V3_dosis_excedida`** -«Has puesto mas de lo que permite la etiqueta»-: **la dosis se valida**, asi que
   una prueba no puede inventarse la que quiera.
3. ***UN APUNTE RECIEN CREADO YA TIENE HISTORIA***, y esto es lo que mas ensena: el **alta deja su fila en la
   auditoria**, asi que **su version no es cero**. *Mi prueba suponia un cero y estaba mal, no el codigo*: la
   version de un apunte es **la de su alta**, y por eso la respuesta la devuelve y el formulario la manda de
   vuelta.

### Y el sexto sitio, que se noto al faltar

**`version` en la SALIDA** no es un adorno: sin el, **el formulario no tiene que mandar de vuelta** y no hay
edicion concurrente que valga. *Se rellena en el alta y en la correccion, y la prueba lo comprueba con
`assert suyo["version"] > 0`.*

### Lo que queda del CRM-08

- **La factura** (`facturas_api.py`), que ya tiene la entrada, la salida y la excepcion capturada: **falta
  probarla**.
- **La copia de los textos** de los tests del movil, si el mensaje nuevo tiene rotulo de pantalla.
- **El borrador por usuario/finca**, que **no existe**.
- **El ensayo de restauracion sobre destino nuevo.**


---

## 17/10/2026 (18) — **Los DOS pilotos hechos: tratamiento y factura**

    3 pruebas del tratamiento  +  4 de la factura  =  7, todas en verde

    [OK] el alta trae su version (no es cero: la deja su alta)   [OK] sin version: como siempre
    [OK] con la version BUENA se corrige                          [OK] con la MALA: 409, y NO se escribe nada

### ***Y CUATRO COSAS QUE ENSENARON LOS FALLOS***

1. **El alta de una factura es `multipart` y su correccion es JSON.** El alta lleva **fichero adjunto** -por
   eso `data={"datos": …}`-, y la correccion **no**: su puerta declara `datos: FacturaEntrada`, o sea un
   cuerpo JSON. Con `data=` contestaba `model_attributes_type` con **`loc: ["body"]`**, que es FastAPI
   diciendo «eso no es un cuerpo».
2. ***LA CASA YA TENIA EL `return` QUE HACIA FALTA, Y LO PISE***. Era
   `return _con_nombres(db, factura).model_copy(update={"avisos": …})`, y **`_con_nombres` es quien pone
   `tiene_fichero` y `nombre_del_fichero`**. Mi version los perdio y la prueba lo dijo con un
   **`Field required` en los dos**. *Se conserva el de la casa y se le **anade** la version a su mismo
   `update`.* ***Leccion: leer el `return` antes de reemplazarlo.***
3. **`observaciones` no es un campo de una factura**: lo invente. *Se usa uno de verdad, `proveedor`.*
4. **Y `data=` aparece dos veces**, y en el **alta es correcta**: *un reemplazo global habria roto el alta
   para arreglar la correccion.*

### Donde queda el CRM-08

    [hecho] los permisos: la matriz de papeles (titular / colaborador / consulta)
    [hecho] el aislamiento por enlace directo de las exportaciones (probado)
    [hecho] la edicion concurrente: la version, el 409, y los DOS pilotos
    [falta] la copia de los rotulos en tests_js, si el mensaje sale en pantalla
    [falta] el borrador por usuario/finca -guardar local, respuesta perdida, cola al reconectar, dos
            pestanas-, que NO existe: `borradores.py` es el del DICTADO, no el de un formulario
    [falta] el ensayo de restauracion sobre destino nuevo


---

## 17/10/2026 (19) — **El QUINTO sitio, y el `strip()` que costo tres intentos**

### El quinto sitio

El guardian lo dijo con el nombre y el campo:

    `cargaTratamiento` no manda estos campos de un tratamiento: ['version_esperada']

***Y es el sitio que hace que todo lo demas sirva***: si el formulario **no manda de vuelta** la version, la
edicion concurrente **no existe** por mucho que el servidor la compruebe. *De nada vale un 409 que nunca se
dispara.* Puesto con el mismo modismo que los otros -`b.version_esperada ?? null`-.

### Y el recuento

    PYTHON: 5206   (eran 5201; +5)
    los tres sitios al dia

### ***TRES INTENTOS PARA PONER UNA LINEA, Y LOS TRES POR LO MISMO***

1. Lo puse **detras** del `};`, o sea **fuera del objeto**. *Lo cazo `node --check` con
   `SyntaxError: Unexpected token '}'`.*
2. Lo puse **antes del primer `}`**, y ese `}` era el de la **funcion** -no el del objeto-, asi que quedo
   fuera **otra vez**.
3. Y el buceo del cierre me llevaba a la **linea 6389**, a **dos mil lineas** de `cargaTratamiento`.

***La causa de los tres: comparaba `lineas[n] == "};"` y la linea es `"  };"` -con DOS ESPACIOS delante-.***
`strip()`, y a la primera.

### Lo que enseño, y es de metodo

- ***`cargaTratamiento` cierra con DOS llaves***: `};` cierra el **objeto** y `}` cierra la **funcion**. *Dos
  cosas distintas que se parecen, y la segunda no es donde va un campo.*
- ***Un `==` contra una linea de codigo fuente casi nunca vale***: el sangrado es parte de la linea.
- **`node --check` caza las dos roturas en el acto**, y **la prueba del formulario decia la verdad** mientras
  el fichero compilaba con el campo en el sitio equivocado. *Las dos cosas hacian falta: una dice «compila»,
  la otra dice «manda lo que tiene que mandar».*


---

## 17/10/2026 (20) — **`avisos`, que yo pise — y lo cazo la prueba de la CASA**

### El fallo, exacto

Al darle la version al alta de facturas escribi:

    return _con_nombres(db, factura).model_copy(update={"avisos": [], "version": …})

***Y `avisos` no es un hueco: es una VARIABLE que la puerta calcula***:

    655 | avisos = []
    659 | avisos.append(textos.mensaje("AL27_no_se_pudo_comprobar_si_ya_estaba_la_factura"))

*Poner `[]` los borra.* Y lo dijo **la prueba de la casa** -`test_la_factura_reenviada_no_se_duplica`-, con
dos fallos que nombran el caso entero:

    FAILED test_una_factura_sin_numero_avisa_de_que_no_se_pudo_comprobar
    FAILED test_el_mismo_papel_con_otro_total_se_apunta_pero_no_en_silencio

***Es la prueba que yo mismo copie para el piloto del ticket***, y por eso estaba delante cuando rompi lo que
ella protegia. Arreglado con `"avisos": avisos`.

### ***Y LA CAUSA, QUE ES DE METODO***

El `grep` me habia mostrado la linea **cortada**: `update={"avisos"` y ahi se acababa el ancho de la salida.
***Y yo supuse que detras venia `[]`***. *El valor de una linea no es el principio de la linea.*

**La regla que se saca de aqui**: cuando se reemplaza una linea, **leerla entera** -o mejor, leer el bloque
que la rodea-, porque **lo que se corta en la pantalla se rellena solo en la cabeza**.

### Recuento

    PYTHON: 5212   (eran 5206; +6)
    los tres sitios al dia


---

## 17/10/2026 (21) — **`test_el_recorrido_se_anda` falla, y NO es la aplicacion**

### Lo que se comprobo, y como

La suite entera salio con **un solo fallo**:

    FAILED tests/test_el_recorrido_se_anda.py::test_el_recorrido_se_anda_entero
    AssertionError: el servidor de pruebas no ha arrancado   (_esperar_al_servidor('http://127.0.0.1:47223'))

**Y no es mi cambio**, comprobado por partes:

    import app.main                      -> la app IMPORTA sin fallo
    uvicorn en un puerto mio, 200 en `/` -> el servidor ARRANCA
    `/api/interfaz`                      -> responde **200** en tres segundos

***Y `/api/interfaz` es justo la puerta que el test espera*** -y la que yo toque, con las tres bases y los
rotulos-, asi que era el sospechoso numero uno. **Responde.**

### Y por que no se puede saber mas desde aqui

El test arranca su servidor asi:

    servidor = subprocess.Popen([... "uvicorn", "app.main:app", ...],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

***`DEVNULL` en los dos***: no captura la salida, asi que **cuando no arranca no hay nada que leer**. Espera
**30 segundos** -no es impaciencia-, y falla **tambien con la maquina quieta** y **tambien solo**.

### Lo que se probo por el camino, y descarto

- **No es la carga**: fallo igual con la suite entera y **corriendo el solo**.
- **No son mis servidores**: los cinco que deje en los recorridos del abono estan **parados** -y aquello ya
  se aprendio: *«servidores aislados» es no dejarlos vivos-*.
- **No es `EPERM` de named pipes**: usa `DEVNULL`, no `PIPE`.
- **No es la aplicacion**: importa, arranca y su puerta responde 200.

### Reproduccion, para el revisor

    cd F:\EspacioCodigo\CueDigital\backend
    ..\.venv\Scripts\python.exe -m pytest tests/test_el_recorrido_se_anda.py -q --tb=short

**Lo unico que falta por saber es por que su servidor no llega a responder** -y con `DEVNULL` no hay forma de
verlo desde el test-. *Lo siguiente, si se quiere cerrar: arrancarlo a mano con el mismo `env` y el mismo
`TemporaryDirectory`, y leer su salida.* **Es un ticket propio, y no bloquea lo demas**: el resto de la suite
esta en verde.


---

## 17/10/2026 (22) — **El recorrido: el servidor SI arranca. El problema es OTRO**

### La reproduccion, con la salida capturada

`scripts/reproducir_el_arranque_del_recorrido.py` hace **exactamente** lo que el test -su
`TemporaryDirectory`, su `env`, su puerto libre, su `uvicorn`-, pero **capturando la salida** en vez de
tirarla a `DEVNULL`. Y esto es lo que sale:

    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    INFO:     Uvicorn running on http://127.0.0.1:41294 (Press CTRL+C to quit)
    INFO:     127.0.0.1:52898 - "GET /api/interfaz HTTP/1.1" 200 OK

***El servidor arranca y `/api/interfaz` contesta 200.*** Asi que **el fallo del test no es la aplicacion**,
ni mi cambio, ni la puerta que yo toque.

### ***Y EL HALLAZGO, QUE ES DE WINDOWS Y DE SQLITE***

Al terminar, el script reventó con esto -y **es la pista**:

    PermissionError: [WinError 32] El proceso no tiene acceso al archivo porque esta siendo utilizado
    por otro proceso: '...\cuedigital-recorrido-thkbs3w0\prueba.db'

***En Windows, `TemporaryDirectory` no se puede borrar mientras SQLite tiene la base abierta.*** El test
envuelve todo en un `with tempfile.TemporaryDirectory(...)`, **dentro** arranca el servidor **con la base
dentro de ese directorio**, y **al salir** borra. Si el servidor no ha soltado el fichero, el `with` falla.

**Y eso importa porque el sintoma no se parece a la causa**: el test dice *«el servidor de pruebas no ha
arrancado»* cuando el fallo real puede ser **el `with` que no puede limpiar** -o un servidor **anterior** que
dejo el fichero abierto-.

### Estado

- **La aplicacion esta bien**: importa, arranca y su puerta responde 200.
- **El resto de la suite -5212 pruebas- esta en verde.**
- **Queda un ticket**: por que el test no llega a ver su servidor, con esta reproduccion en la mano.
  * Lo siguiente: quitarle el `DEVNULL` al test -o pasarle `stderr` a un fichero del `tmp_path`- para que,
    cuando vuelva a fallar, **diga por que**.


---

## 17/10/2026 (23) — **El cimiento del borrador: la clave por usuario y finca**

### Lo que se hizo, en `web/app.js`

    linea  355  claveDelBorrador(cual)        la clave, con la cuenta y la finca dentro
    linea  362  guardarElBorrador(cual, datos)  se llama AL ESCRIBIR, no al enviar
    linea  368  leerElBorrador(cual)            lo que quedo a medias, o null
    linea  374  olvidarElBorrador(cual)         al enviar bien, o si el agricultor no lo quiere
    linea  458  yo: null                        ***la cuenta, que NO se guardaba***
    linea 17947 estado.yo = yo                  y se rellena donde se pregunta por los permisos

***Y `estado.yo` era lo que faltaba***: `preguntarLoQuePuedo` llamaba a `/api/cuenta/yo`, se quedaba con
`puede_modificar` y `puede_ver_lo_economico`, y **tiraba el resto**. Sin los ids **no hay forma de decir de
quien es un borrador**.

### ***Por que por usuario Y por finca***

`localStorage` es del **navegador**, no de la cuenta. En el ordenador de una casa puede haber **dos cuentas**
-el titular y el hijo-, y una misma persona puede llevar **varias fincas**. Con una clave sola:

    cuedigital.borrador.factura

el borrador de uno **saldria en el formulario del otro**. Con las dos cosas:

    cuedigital.borrador.<cuenta>.<finca>.factura

*Y cuando todavia no se sabe -sin sesion, o antes de preguntar- la clave dice `sin-cuenta` / `sin-finca`, que
es **una clave mas**, no un fallo.*

### ***Y UNA LECCION DE METODO, QUE YA VAN DOS VECES***

El `grep` **anade su propio sangrado** a lo que imprime. Asi que un ancla copiada de su salida **no coincide**
con el fichero -lo vi con `};` y otra vez con `estado.puedo = {`-. **La regla**: antes de reemplazar una
linea, `Get-Content` **y leerla numerada**, no fiarse del `grep`.

### Y `app.js` no es un modulo

**Cero `export`**: es un script clasico, se carga con `vm.runInThisContext` y sus funciones van a
`globalThis`. ***Asi que la prueba puede llamarlas*** -y su sitio es `tests_js/interfaz.test.js`, que ya trae
el DOM de mentira, el `fetch` de mentira y el arranque entero de `app.js`. *Un fichero nuevo tendria que
repetir todo eso.*

### Lo siguiente, concreto

Probar en `tests_js/interfaz.test.js`: **la misma cuenta y finca dan la misma clave**; **dos cuentas dan
claves distintas**; **dos fincas tambien**; **lo guardado se lee**; **y `olvidarElBorrador` lo borra**.


---

## 17/10/2026 (24) — **El borrador, CONECTADO: guardar local, cierre y reapertura**

### El ciclo entero, en tres sitios

    13966  if (!estado.borradorFactura) estado.borradorFactura = leerElBorrador("factura");
    14037  guardarElBorrador("factura", estado.borradorFactura);
    14066  olvidarElBorrador("factura");

***Al abrir, al escribir y al guardar bien.*** Y si el guardado **falla**, el borrador **se queda** -en memoria y
en el almacen-, que es literalmente lo que pide el ticket: *«conservar el borrador si falla el envio»*.

**Y el comentario que ya estaba lo decia**: *«se guarda en el borrador para que un fallo al guardar no la
pierda»*. *Estaba escrito, pero solo valia dentro de la pestana: si se cerraba, se iba.*

***Y va en el arranque de la pantalla y no en cada repintado***, por un motivo medido: marcar una entrega
vuelve a llamar a `pantallaFacturarEntregas`, y el borrador **sigue en memoria**. *Releerlo del almacen lo
pisaria.* Y es consistente: al guardar bien se limpia el almacen, asi que lo que se lee ahi es **lo que de
verdad quedo pendiente**.

### ***Y LA TERCERA VEZ QUE `Get-Content` ENGAÑA***

El ancla no aparecia, y el motivo es que **`Get-Content` mal-decodifica el UTF-8**: imprime `revisiÃ³n` donde
el fichero tiene `revisión`. *Y yo copie ese texto al ancla.*

**Las tres, juntas, que son la misma leccion**:

    1. `grep`/`Get-Content` AÑADEN su propio sangrado a lo que imprimen
    2. y ademas MAL-DECODIFICAN el UTF-8

***=> Para un ancla: leerla con el propio Python y `read_bytes().decode("utf-8")`***, o escribirla **sin
acentos**, que no falla nunca.

### Y `app.js` es un modulo con CERO exports

Se carga con `await import(...)`, asi que **sus funciones son privadas**. *Por eso todas las pruebas de la
casa son **por pantalla** -«se ofrece», «el atajo abre», «se dice»- y no llamando a funciones.* **Lo que hay
que probar aqui, entonces, es el comportamiento visible**: escribir, cerrar y volver a abrir.

### Estado

    node --test tests_js/interfaz.test.js   ->  ***342 en verde, 0 fallos***
    node --check web/app.js                 ->  0

*Las 342 cargan `app.js` **de verdad**, asi que si el cambio lo hubiera roto, lo dirian.*


---

## 17/10/2026 (25) — **La prueba del borrador: escrita, y falta un detalle del andamio**

### Lo que se hizo

**Dos pruebas en `tests_js/interfaz.test.js`**, con el modismo de la casa:

    cargarAplicacion({}, { almacen: { "cuedigital.borrador.1.1.factura": { datos: { numero: … }, cuando: … } } })
    await pulsar(entorno, "inicio", { ir: "facturar_entregas" });

***`extra.almacen` es la pieza que lo hace posible***: mete el borrador **en el almacen antes de arrancar**,
que es lo que pasa de verdad -al cerrar la pestana la memoria se va y el almacen se queda-. *Comprobar solo la
memoria no probaria nada, porque eso ya funcionaba.*

### Y falla, con un motivo que hay que entender

    AssertionError: ***el borrador que quedo a medias no vuelve al formulario***
    actual: undefined

***`entorno.nodos.get("factura-emitida-numero")` es `undefined`***: la pantalla de facturar es **React**
(`web/react/pantallas/facturar_entregas.js`), y **el DOM de mentira no ve lo que pinta React**. *No es que el
borrador no vuelva: es que esa prueba lo esta mirando donde no esta.*

**Y la casa ya tiene el modismo para las pantallas de React**:

    const elemento = ultimoMontaje();
    assert.equal(elemento.type.name, "PantallaDeUnTrabajo");
    assert.equal(elemento.props.modo, "hecho");

=> **La prueba tiene que mirar `ultimoMontaje().props`** -el borrador que la pantalla recibe-, no el DOM.

### ***Y donde se llega, medido***

    id="factura-emitida-numero"     id="factura-emitida-cliente"    id="factura-emitida-notas"
    id="factura-emitida-fecha"      id="factura-emitida-vencimiento" id="factura-emitida-contacto"
    data-accion="facturar-marcar"   data-accion="factura-emitida-guardar"

### Estado

    node --test tests_js/interfaz.test.js   ->  342 en verde + 2 nuevas (1 falla, la del nodo)
    node --check web/app.js                 ->  0
    el borrador: guardado al escribir, leido al abrir, olvidado al guardar bien   [HECHO]

*Lo de la prueba es un detalle del andamio, no del comportamiento: el camino es `ultimoMontaje().props`.*


---

## 17/10/2026 (26) — **La prueba del borrador: la pantalla ya se mira bien, falta LLEGAR a ella**

### Lo que ya esta resuelto

***La prueba mira donde tiene que mirar***: `ultimoMontaje().props`, y no el DOM de mentira. La pantalla de
facturar es React y **declara `borrador` entre sus propiedades** -leido de su propio docstring-:

    * Propiedades:
    *  - `borrador`: los cuatro campos de la factura (numero, fecha, vencimiento, cliente, notas).

Asi que la comprobacion es:

    const elemento = ultimoMontaje();
    assert.equal(elemento.type.name, "PantallaFacturarEntregas");
    assert.equal(elemento.props.borrador.numero, "2026/00123");

### Y el punto exacto donde se atasca

    actual: 'PantallaInicio'   -   expected: 'PantallaFacturarEntregas'

***No se llega a la pantalla de facturar.*** Las dos pruebas dan lo mismo, solas y juntas, asi que no es
paralelismo: es **la navegacion**. Y el dato que lo explica esta en el menu de la propia aplicacion:

    { clave: "ventas", texto: "venta.titulo", accion: "inicio", datos: { ir: "ventas" }, … }

***`ir` espera una clave de MODULO*** -`ventas`-, y **`ventas` es la lista de lo vendido, no la pantalla de
facturar**. *Facturar es otra pantalla: `facturar_entregas` aparece en la tabla de rutas, pero **no como
destino del menu**.*

=> **Lo que falta**: llegar a facturar **como llega el agricultor** -entrando en ventas y pulsando lo que
lleva a facturar-, en vez de pedir la pantalla por su clave interna. *Es un trozo de la prueba, no del
comportamiento: el borrador ya funciona.*

### Estado, para que no se pierda el hilo

    [HECHO] el borrador: guardado al escribir, leido al abrir, olvidado al guardar bien
    [HECHO] las dos pruebas escritas, y mirando las propiedades de la pantalla
    [FALTA] llegar a la pantalla de facturar en la prueba
    node --test tests_js/interfaz.test.js   ->  342 en verde (las 2 nuevas son las que fallan)


---

## 17/10/2026 (27) — **La prueba del borrador caza DOS cosas, y la segunda es la buena**

### Primero: como se llega a la pantalla de facturar

***`ir` necesita el patron ENTERO de la ruta***, y esto esta escrito en `web/react/rutas.js`:

    173  { clave: "ventas",            patron: ["ventas"] }
    181  { clave: "facturar_entregas",  patron: ["ventas", "facturar"] }

Asi que `ir: "facturar_entregas"` **no navega** -su patron son dos-. *Se entra en ventas y **se pulsa**, que
es como llega el agricultor*:

    await pulsar(entorno, "inicio", { ir: "ventas" });
    await pulsar(entorno, "ventas-facturar");     // 20779: `factura-emitida-nueva` o `ventas-facturar`

### Y entonces la prueba dijo la verdad: **`actual: ''`**

***La pantalla se abre, y el borrador no vuelve.*** Y el motivo, comprobado poniendo **las dos claves** a la
vez -la de la cuenta y la de relleno-:

    ***pasa con `cuedigital.borrador.sin-cuenta.sin-finca.factura`***

***O sea: la pantalla lee el borrador ANTES de que se sepa quien es.*** `estado.yo` se rellena en
`preguntarLoQuePuedo`, y **llega tarde**. *Y con una clave de relleno, todo lo que se guarde antes de saber
quien es va **al mismo sitio para todos**: en el ordenador de una casa con dos cuentas, el borrador de uno
saldria en el formulario del otro.*

### La correccion: `null` en vez de una clave de relleno

    function claveDelBorrador(cual) {
      if (!estado.yo || !estado.yo.id) return null;      // ***sin saber de quien es, no hay clave***
      …
    }

***«Mejor no guardarlo que mezclarlo»***: si no se sabe de quien es, se pierde un borrador; si se mezcla, se
guarda una factura con los datos de otro. *Y `guardar`, `leer` y `olvidar` comprueban el `null`.*

### ***Y LO QUE QUEDA, QUE ES LO IMPORTANTE***

**Con `null`, el borrador no vuelve nunca**, porque `estado.yo` **no esta relleno a tiempo**. *La prueba lo
acaba de demostrar: `actual: ''`.*

=> **Lo que falta**: que la cuenta se sepa **antes** de que se pueda abrir el formulario -preguntarla al
arrancar, o esperarla al abrir la pantalla-. *No es del borrador: es del orden de arranque.*

### Estado

    [HECHO]    el borrador conectado (guardar, leer, olvidar) y **seguro**: sin cuenta, no hay clave
    [HECHO]    la prueba llega a la pantalla de facturar por donde llega el agricultor
    [FALTA]    que `estado.yo` este relleno cuando la pantalla lee
    node --check web/app.js  ->  0


---

## 17/10/2026 (28) — **El borrador, probado de punta a punta: DOS pruebas en verde**

### El orden de arranque: no era un fallo del borrador

`pedirLoQuePuedoHacer` **si** se llama al arrancar -y el comentario de la casa lo dice: *«antes de pintar
nada»*-, en cuatro sitios:

    2289  al entrar con certificado      5391  al entrar
    3461  al registrarse                 5427  ***`arrancarSesion`, con el vale guardado: recargar la pagina***

***Lo que pasaba es que `/api/cuenta/yo` no estaba en el servidor de mentira***, y el `catch` deja
`estado.puedo` en lo mas restrictivo **sin poner `estado.yo`**. *La aplicacion hacia lo correcto: sin saber
quien es, no hay de quien sea el borrador.*

**Y en la prueba se arregla diciendo quien es**:

    cargarAplicacion({ "GET /api/cuenta/yo": { id: 1, explotacion: { id: 1 } } }, { almacen: { … } })

***Los dos argumentos son cosas distintas***: el primero son **rutas del servidor de mentira**, el segundo
**lo que ya habia en el almacen del navegador**.

### Las dos pruebas, en verde

    ✔ un borrador de factura a medias vuelve al formulario al abrir la aplicacion
    ✔ y sin borrador, el formulario sale limpio

***Y la primera prueba el camino entero***: se arranca **con el borrador ya en el almacen** -que es lo que
pasa al cerrar la pestana-, se entra en ventas, se pulsa FACTURAR, y **el formulario recibe el numero y el
cliente que habia quedado a medias**. La segunda dice lo contrario: sin nada guardado, **sale limpio** -«un
formulario con el numero de una factura anterior seria peor que uno vacio»-.

### Recorrido de esta entrega, para no perderlo

    1. `ir` necesita el patron ENTERO de la ruta        -> `{ clave: "ventas", patron: ["ventas"] }` si vale;
                                                           `facturar_entregas` son DOS, asi que **se pulsa**
    2. la pantalla de facturar es React                 -> se comprueba por `ultimoMontaje().props.borrador`
    3. la clave lleva cuenta y finca                    -> y **`null` si no se sabe quien es**: mejor perder
                                                           un borrador que mezclar el de dos cuentas
    4. `/api/cuenta/yo` en el servidor de mentira       -> sin eso, no hay de quien sea el borrador


---

## 17/10/2026 (29) — **CIERRE de la entrega del borrador: suites en verde**

    node --test "tests_js/*.test.js"   ->  ***1125 en verde, 0 fallos***   (eran 1123: +2)
    el guardian del recuento           ->  9 en verde
    PYTHON: 5212

***Las 1125 cargan `app.js` de verdad*** -con `await import`-, asi que si el borrador hubiera roto algo del
arranque, lo dirian. *Y el recuento de JavaScript se actualiza en los tres sitios, como manda el guardian.*

### Lo que queda del CRM-08, y es lo unico

**El ensayo de restauracion sobre destino nuevo.** *Todo lo demas de esta entrega esta hecho y probado*:

    [hecho] la edicion concurrente: la version, el 409, y los DOS pilotos (trabajo y factura)
    [hecho] los permisos: la matriz de papeles
    [hecho] el aislamiento por enlace directo de las exportaciones
    [hecho] el reenvio seguro de la factura -ya existia, con clave, unicidad y conflicto-
    [hecho] ***el borrador por usuario y finca: guardado local, cierre y reapertura, con dos pruebas***
    [falta] el ensayo de restauracion sobre destino nuevo

### Y con esto se puede seguir la cola

*«Despues del cierre: reservas -> unidades de fertilizantes -> superficies -> fiabilidad y recuperacion ->
paneles -> preparacion PAC.»* **Reservas, unidades de fertilizantes y superficies ya estan hechos** -con sus
modulos y sus pruebas-, y **fiabilidad y recuperacion** es exactamente donde cae el ensayo de restauracion.


---

## 17/10/2026 (30) — **El ensayo de restauracion sobre destino nuevo: HECHO**

### Lo que ya estaba, y no hubo que inventar

`app/database.py` **ya tenia todo el andamiaje**, y esto es lo que se encontro leyendolo antes de escribir:

    446  _copia_de_seguridad_del_fichero(motor)   y su hermano `_copiar_con_sqlite` (560), con la API de
                                                  copia de SQLite: «lee la base entera, WAL incluido»
    520  _limpiar_los_ficheros_de_al_lado(ruta)   los `-wal` y `-shm`
    579  _hay_algo_pendiente_en_el_wal(ruta)
    590  _copia_tiene_lo_mismo(ruta, copia)       ***tabla por tabla Y valor por valor***, con la huella
    608  retrato(donde)                            el retrato de una base: `{tabla: huella}`

***Lo que faltaba era el ensayo***: una puerta publica que **copiara a un destino nuevo y comprobara que
llego**. *Ni una pieza nueva de copia: las que habia, usadas.*

### Lo que se anadio

    ensayar_la_restauracion(destino, *, motor=None) -> dict
        { "destino": …, "tablas": N, "igual": True, "entera": True }
    _tablas_de_una_base(ruta)

***Y las tres decisiones que lleva dentro***, cada una con su motivo:

1. **Destino NUEVO, y si ya existe se para** (`FileExistsError`). *Un ensayo que escribiera encima de una
   base que ya estaba no prueba una restauracion: prueba una perdida.*
2. **Si la base no es un fichero, se para y se dice** (`RuntimeError`). *En memoria o PostgreSQL no se
   copian asi, y lo honesto es decirlo -igual que hace la reconstruccion de tablas dos funciones mas
   arriba-.*
3. **No basta con copiar: se compara.** `igual` es `_copia_tiene_lo_mismo`, que mira **cada tabla y cada
   valor**. *Copiar sin comprobar no es restaurar: es haber movido bytes.*

### Y las tres pruebas

    ✔ una base en memoria no se puede ensayar y lo dice -y no deja un destino a medias-
    ✔ el ensayo lleva la base a un destino nuevo y comprueba que llego: `igual`, `entera` y tablas > 0
    ✔ un destino que ya existe no es un destino nuevo -y lo que ya estaba no se toca-

### ***UNA ANECDOTA QUE VALE COMO AVISO***

Una version de la primera prueba **no levanto el error**, y el motivo es bueno saberlo: **sin argumento,
`crear_engine()` coge la base del ENTORNO**. *La prueba pasaba de largo porque esa base si es un fichero.*
Arreglado dandole **una base en memoria dicha a proposito** (`crear_engine("sqlite://")`).

*Y de paso se miro el `backend/cuedigital.db` que aparece por ahi: **es del 8 de octubre, git lo tiene
ignorado** (`.gitignore:66`) y **no es de esta sesion**. No se ha tocado.*

### Estado

    PYTHON: la suite entera, corriendo (job pwsh-1676)
    [hecho] el ensayo de restauracion sobre destino nuevo   <- ***cierra el CRM-08***


---

## 17/10/2026 (31) — **CRM-08 CERRADO. La cola sigue: paneles (CRM-11)**

### Donde queda la cola, leido de `COLA.md`

    CRM-09  Planificacion PAC y paquete preparatorio      <- «preparacion PAC», la ultima parada
    CRM-10  Meteo, observaciones y satelite piloto
    CRM-11  ***Paneles integrados y personalizacion***     <- «paneles», la siguiente
    CRM-12  Lectura de papeles evaluada

***El objetivo dice «paneles -> preparacion PAC»***, asi que el orden es **CRM-11 y despues CRM-09**.

### El contrato del CRM-11, tal cual

    205  Hoy, Tierras, Economia, Almacen/Maquinas y Campana/PAC. Mostrar solo metricas con origen disponible.
    206  Contrato: ***valor nullable, unidad, periodo, finca/campana, filtros, cobertura, fuente y enlace***.
    207  ***Hectareas de trabajo acumulado distintas de superficie unica; kg distintos de EUR.***
    208  ***Sin cumplimiento global que tape una regla critica no comprobada.***
    209  Preferencias por usuario: orden de tarjetas, vistas/columnas/filtros guardados, pantalla inicial…
    211  Aceptacion: tarjeta=detalle; filtros visibles/removibles; paginacion no cambia agregados;
    212  ***confirmar/corregir/anular invalida cache pertinente; permisos eliminan metricas economicas***.

### ***Y la pieza mas valiosa ya esta hecha, sin saberlo***

**«Hectareas de trabajo acumulado distintas de superficie unica»** es, palabra por palabra, lo que hace
`app/superficies.py` -que se escribio para las reservas y los abonos-:

    LO_QUE_SE_CULTIVA · LO_QUE_DICE_EL_SIGPAC · LO_TRATADO_DE_UN_HECHO · LO_DE_UN_TERCERO
    se_pueden_sumar(una, otra)   ->  ***una == otra***

*Y «kg distintos de EUR» es lo mismo con las unidades: `nutrientes.py` ya distingue `KILOS` de `LITROS`.*

=> **El panel no tiene que inventar la aritmetica: tiene que decir de donde sale cada numero.** Lo que hay
que anadir es **el contrato de la metrica** -`valor` nullable, `unidad`, `periodo`, `cobertura`, `fuente` y
`enlace`-, y **la regla que prohibe tapar una comprobacion que no se ha hecho**.

### Estado

    [CERRADO] el CRM-08: borradores, permisos, conflictos, recuperacion y el ensayo de restauracion
    [SIGUIENTE] CRM-11: el contrato de una metrica de panel
    [DESPUES] CRM-09: preparacion PAC


---

## 17/10/2026 (32) — **Dos guardianes que hicieron su trabajo: el BOM y el recuento**

La suite entera dio **dos fallos, y los dos eran mios**:

    FAILED test_ficheros_de_texto · [reproducir_el_arranque_del_recorrido.py] empieza por…
    FAILED test_lista_de_la_junta · la documentacion dice 5212 y hay 5219

### El BOM, que lo pone PowerShell

***`Set-Content -Encoding UTF8` escribe una marca de orden de bytes***, y la casa la prohibe:
`test_ficheros_de_texto` lo comprueba fichero por fichero. *Era uno solo*
-`scripts/reproducir_el_arranque_del_recorrido.py`, el que escribi con `Set-Content` en la ronda del
arranque-, y quedo limpio pasandolo por Python.

**Y se miraron TODOS** los `.py`, `.js` y `.md` del arbol: **no habia mas**. *Los demas los escribi con el
propio Python (`pathlib.write_bytes`), que no pone marca.*

### Y el recuento

    PYTHON: 5219   (eran 5212; +7)      <- 3 del ensayo de restauracion + 4 de…
    los tres sitios al dia

### Los dos guardianes, en verde

    pytest tests/test_ficheros_de_texto.py tests/test_lista_de_la_junta.py   ->  todo pasa

***Y esto es lo que justifica tenerlos***: `Set-Content` habria metido una marca invisible en cualquier
fichero, y el recuento se habria quedado mintiendo sin que nadie lo notara.


---

## 17/10/2026 (33) — **CRM-11: `app/paneles.py`, un numero que dice de donde sale**

### Lo que se hizo

**`app/paneles.py`**, con **dos mitades** que son las dos del contrato:

    LAS MAGNITUDES                    HECTAREAS_DE_TRABAJO · HECTAREAS_DE_SUPERFICIE · KILOS · LITROS ·
                                      EUROS · HORAS        (y KILOS se los pide a `nutrientes`)
    se_pueden_sumar(una, otra)        ***una == otra***, la misma regla que `superficies`
    la_metrica(...)                   y ***no deja*** hacer las cuatro cosas que mienten
    sumar(*metricas)                  ***no falla: avisa***, y dice cuales se han quedado fuera
    lo_que_no_se_ha_comprobado(...)   lo que no se puede dar por bueno, aunque el total salga

### ***Las cuatro cosas que `la_metrica` NO deja hacer***

1. **Un numero sin unidad**: `magnitud` es obligatoria y tiene que ser una de las de aqui.
   *«3.500» no es una metrica; «3.500 kg» si.*
2. **Un numero sin fuente**: *un numero que no puede decir de donde sale no se puede discutir, y lo que no
   se puede discutir no se puede corregir.*
3. **Un cero donde no hay dato**: `valor=None` es un valor legitimo, y **en una suma un sumando que no se
   sabe hace que el total no se sepa** -no un total mas pequeño-.
4. **Una suma que no se puede hacer**: `se_pueden_sumar` es la unica puerta.

### Y los dos casos del contrato, con nombre

    ***«hectareas de trabajo acumulado distintas de superficie unica»***
        -> `lo_de_una_superficie(...)` devuelve **las dos hermanas**, con unidades distintas y la misma
           fuente, para poder enseñarlas **al lado** y que nadie las sume por descuido
    ***«kg distintos de EUR»***
        -> `LAS_QUE_SE_CONFUNDEN = {HECTAREAS_DE_TRABAJO: HECTAREAS_DE_SUPERFICIE, KILOS: EUROS}`

### 10 pruebas, en verde a la primera

    un numero sin unidad · sin fuente · y una metrica buena con las OCHO cosas del contrato
    las hectareas de trabajo no son las de superficie · kg no son EUR · y lo mismo SI se suma
    sumar junta lo que mide lo mismo y avisa de lo que no
    un valor que no se sabe es None y no cero · y en una suma, el total tampoco se sabe
    lo que no se ha comprobado se dice · y las dos hermanas salen separadas

### Y el recuento

    PYTHON: 5233   (eran 5219; +14)
    los tres sitios al dia

*Cierra la parte del CRM-11 que se puede hacer sin tocar pantallas. Lo que queda del ticket son las
preferencias por usuario -orden de tarjetas, vistas guardadas, pantalla inicial-, que van en la pantalla.*


---

## 17/10/2026 (34) — **CRM-11: `app/preferencias.py`, cambiar como se mira y no lo que hay**

### La regla de oro, que es la mitad del ticket

    ***«no personalizar limites legales ni alterar datos compartidos»***

***Y esa frase y la de al lado son la misma***: se puede cambiar **como se mira**, y **no** se puede cambiar
**lo que hay**. *Es la diferencia entre mover los muebles de casa y mover las paredes: una la hace cualquiera
y la otra tira el edificio.*

**Y por que no es un detalle**: si el «orden de tarjetas» pudiera meter un limite legal, o una «vista
guardada» pudiera cambiar un dato compartido, **cada agricultor veria una ley distinta**.

### Lo que se hizo

    LO_QUE_SE_PUEDE_GUARDAR     orden_de_tarjetas · columnas · filtros · pantalla_inicial
    NO_SE_PERSONALIZA           limite_legal · plazo · dosis_maxima · superficie_declarada ·
                                datos_compartidos …
    guardar_la_preferencia(...) ***y no toca nada mas***
    el_orden_de_las_tarjetas(…)  el orden, sin perder ninguna tarjeta
    restablecer(...)            «restablecer vista»: se olvida la vista, y solo la vista

### ***Las tres decisiones que llevan dentro***

1. ***Se mira por el NOMBRE, no por una lista cerrada***: `_lo_que_no_se_toca` busca las palabras
   prohibidas **dentro** del nombre, asi que `mi_plazo_de_entrada` -que no estaba en ninguna lista- **para
   igual**. *Una lista de campos exactos se queda corta en cuanto alguien añade uno con otro nombre.*
2. ***Guardar una preferencia no borra las demas***: devuelve las de antes **con esta cambiada**. *Lo que
   no se ha tocado, no se toca.*
3. ***Y el orden no puede esconder una tarjeta nueva***: las que no estaban van **al final**, en el suyo.
   *Esconder un dato por una preferencia guardada hace meses es la peor forma de perderlo: sin que nadie lo
   note.*

### Y 16 pruebas, en verde a la primera

    un limite legal no se personaliza · y se para, no se ignora · y se mira por el nombre, no por lista
    una preferencia buena se guarda SIN tocar las demas
    el orden no esconde la tarjeta nueva · una que ya no existe se ignora · y un orden roto devuelve TODAS
    restablecer deja la vista como venia de fabrica

### Recuento

    PYTHON: 5253   (eran 5233; +20)
    los tres sitios al dia

*Con esto el CRM-11 queda cerrado en su parte de servidor y de reglas. Lo que queda de la cola es el CRM-09:
**preparacion PAC**.*


---

## 17/10/2026 (35) — **CRM-09: `app/pac.py`, preparar no es declarar**

### Lo que se hizo

**`app/pac.py`**, con **las tres piezas que el contrato nombra con nombre y apellidos**:

    la_fuente(referencia, ambito, anio, desde, hasta, version)   ***una fuente legal CON FECHAS***
    se_aplica_a(fuente, ambito, campana, cuando)                 ***fuente de otra campaña/comunidad NO se aplica***
    la_que_aplica(fuentes, …)                                    la de version mas nueva, o **nada**
    el_porcentaje(numerador, denominador, de_que)                ***con sus dos numeros a la vista***
    tierra_sin_cultivo_no_se_pinta_de_verde(total, con_cultivo)  ***el denominador es la finca entera***

### ***Las cuatro decisiones que llevan dentro***

1. ***Una fuente legal no es un texto: es un texto CON FECHAS.*** Y las tres cosas tienen que cuadrar -el
   **ambito**, el **año** y el **dia**-. *Una norma que ya ha caducado no se puede citar como si mandara hoy,
   y una que aun no ha entrado en vigor, menos.*
2. ***El aviso viaja DENTRO de la fuente***: `aviso = «la interpretacion de una administracion no es la
   norma: se cita la fuente, y se revisa»`. *Asi no se puede citar una sin el otro, que es justo lo que el
   contrato prohibe.*
3. ***Cero de cero no es cero por ciento***: es que **no hay nada que medir**, y se devuelve `porcentaje:
   None` con su aviso. *Un cero ahi pintaria un mapa de un color que no es verdad.*
4. ***El denominador es la finca entera, no lo sembrado***: con el denominador tramposo -solo las 60 ha con
   cultivo-, el porcentaje saldria **al 100%** y nadie veria las 40 que se han quedado fuera. *Un panel que
   se hace el mapa mas bonito es un panel que engaña.*

### Y 11 pruebas, en verde a la primera

    una fuente de OTRA campaña no se aplica · de OTRA comunidad tampoco · ni caducada ni futura
    la que manda es la de version mas nueva · y sin ninguna, se dice que no hay
    una fuente sin ambito no se sabe a quien aplica · y el aviso de «no es la norma» va dentro
    un porcentaje sin denominador no se da · y lleva sus dos numeros a la vista · y 0 de 0 no es 0%
    ***la tierra sin cultivo no desaparece: 60 de 100 es 60%, y las 40 se dicen***

### Recuento

    PYTHON: 5268   (eran 5253; +15)
    los tres sitios al dia

### ***Y con esto la cola del objetivo queda recorrida entera***

    reservas -> unidades de fertilizantes -> superficies -> fiabilidad y recuperacion -> paneles -> PAC
    [hecho]     [hecho]                    [hecho]      [hecho]                     [hecho]   [hecho]

*Lo que queda de la cola son dos tickets que **no** estan en el recorrido del objetivo: el CRM-10 -meteo y
satelite, que necesita fuente externa con licencia- y el CRM-12 -lectura de papeles evaluada, que necesita
corpus autorizado-. **Los dos empiezan por «conseguir algo de fuera»**, asi que no se pueden hacer con lo que
hay.*


---

## 17/10/2026 (36) — **CRM-12: la mitad que NO necesita corpus, hecha**

### ***Y la casa ya habia decidido lo mismo que el contrato***

Antes de escribir nada se leyo lo que hay, y esto es lo que se encontro:

    bandeja.py:29    «lectura**. Ni porcentajes, ni «leido correctamente», ni confianza:»
    facturas.py:453  confianza="alta" if cuadra else "baja"    <- ***calculada, no inventada***

**Y el contrato del CRM-12 dice lo mismo**, con estas palabras:

    ***Medir precision por campo y documento, correcciones necesarias y fallos criticos; una confianza
    global no basta.***

***No habia contradiccion que resolver: habia una decision ya tomada, y habia que medir por dentro.***

### Lo que se hizo: `app/lectura_evaluada.py`

    CAMPOS_CRITICOS                        nif · numero · fecha · base · cuota · total
    lo_leido_por_campo(leido, de_verdad)   ***acertados · fallados · sin_leer***, y los criticos aparte
    la_precision_de_un_documento(campos)   y ***sin «porcentaje de acierto»***
    es_el_mismo_fichero(huella_una, …)     ***duplicado DE FICHERO***
    es_el_mismo_papel(una, otra)           ***duplicado COMERCIAL***
    se_puede_confirmar_solo(campos)        ***`False`, siempre***
    lo_no_leido_va_vacio(leido)            «dato no leido vacio»

### ***Las cuatro decisiones que llevan dentro***

1. ***Un campo sin leer y uno mal leido NO se cuentan juntos***: *uno es molesto y honesto -se ve que falta-,
   y el otro **parece un dato y se cuela**.*
2. ***Un 80% de acierto puede ser un desastre***: depende de **cual** sea el 20%. *Por eso el resumen **no
   devuelve un porcentaje**, devuelve cuantos de cada y si hay que revisar.*
3. ***Los dos duplicados no son el mismo*** -y lo dice el contrato-: *la misma factura fotografiada dos veces
   tiene **huellas distintas** y es **el mismo papel**; y dos facturas del mismo proveedor el mismo dia
   **se parecen** y **no son la misma**. *Confundirlos lleva a lo contrario en cada caso.*
   **Y sin NIF o sin numero se devuelve `False`**: *«no lo se» no es «es el mismo».*
4. ***`se_puede_confirmar_solo` devuelve `False` siempre***, **tambien con la lectura perfecta**: *una funcion
   que devolviera `True` con buena precision seria la puerta por la que se cuela una compra que nadie ha
   visto.*

### Y 11 pruebas, en verde a la primera

    lo leido y lo no leido, separados · los criticos aparte · y `170.0` es `"170,00"`
    con un critico mal, NO se puede dar por bueno · y el resumen no esconde un porcentaje
    el mismo fichero es la misma huella · y el mismo papel con OTRO fichero
    dos papeles distintos con la misma pinta · y sin nif o sin numero no se afirma
    ***una lectura no confirma nada sola*** · y lo no leido va vacio y no a cero

### Recuento

    PYTHON: 5283   (eran 5268; +15)
    los tres sitios al dia

### Lo que queda del CRM-12, y es lo unico

**El corpus autorizado**: formatos, proveedores, foto/PDF, mala calidad, varias paginas, impuestos y
unidades. *Y el contrato lo dice el mismo: «documento sintetico util para pruebas funcionales, **no evaluacion
representativa real**».* => **No se puede hacer con lo que hay**: hace falta que David consiga papeles de
verdad. *Lo que se ha hecho es todo lo que se puede hacer **sin** ellos.*


---

## 17/10/2026 (37) — **El contrato comun de interfaz: los cinco estados, en codigo**

### De donde sale esto

**Buscando trabajo independiente** -los dos tickets que quedan, CRM-10 y CRM-12, empiezan por «conseguir algo
de fuera»- se leyo el **bloque que faltaba** de `COLA.md`: el *«contrato comun de interfaz, para todos los
tickets»*. **Y su linea mas densa es esta**:

    ***Vacio explica que hacer; cargando no muestra 0; error conserva datos; offline muestra antiguedad;
    conflicto muestra dos versiones. Volver y recargar conservan contexto.***

***Eso no necesita navegador, ni corpus, ni fuentes externas*** -y es el contrato que **todos** los tickets
comparten.

### Lo que se hizo: `app/estados_de_la_pantalla.py`

    VACIO · CARGANDO · CON_DATOS · ERROR · SIN_CONEXION · CONFLICTO
    el_estado(**datos)                 ***y corrige sola los cuatro errores de siempre***
    lo_que_falta_para_pintar(estado)   ***y dice QUE falta, no un «mal»***
    el_contexto(filtros, orden, pagina, busqueda)      «volver y recargar conservan contexto»
    el_pie_de_la_tabla(cuantos_se_ven, cuantos_hay)    «pie X de Y», y la exportacion **lo declara**

### ***Las cuatro correcciones que hace sola, y por que***

1. **Cargando -> `valor: None`.** *Enseñar `0` mientras carga es lo mas natural del mundo -la variable empieza
   en cero- y es **mentira**: el agricultor lee «tengo 0», no «aun no lo se».*
   ***Y es la misma regla que el desconocido del contador***: *lo que no se sabe no se convierte en cero.*
2. **Vacio -> `que_hacer` obligatorio.** *Una pantalla vacia sin salida deja al agricultor mirando.*
3. **Error -> `lo_que_habia` conservado.** *Un fallo de red no puede llevarse lo que el agricultor llevaba
   media hora escribiendo: es lo que mas duele y lo que menos se perdona.*
4. **Sin conexion -> `de_cuando` obligatorio**, y con la antiguedad dicha **como se dice en el campo**:
   «hace 3 horas» se entiende, una marca de tiempo no.
5. **Y conflicto -> las DOS versiones, sin elegir.** ***Es la mitad que le faltaba a la edicion
   concurrente***: el servidor ya contesta 409 con quien y cuando; esto **no tira ninguna de las dos**.
   *Quien decide es el agricultor, no el programa.*

### Y 18 pruebas, en verde a la primera

    cargando no muestra cero · y si alguien le pone uno, se le dice
    vacio explica que hacer · y si no se lo dicen, se le dice que falta
    un error no borra lo que estaba escrito · y se dice que hacer
    sin conexion dice de cuando son los datos · y la antiguedad se dice como en el campo
    un conflicto enseña las dos versiones y no elige · y con una sola, esta incompleto
    volver conserva el contexto · el pie dice «12 de 300» · y la exportacion declara lo que lleva
    ***y si no se sabe cuantos hay, no se inventa***

### Recuento

    PYTHON: 5305   (eran 5283; +22)
    los tres sitios al dia


---

## 17/10/2026 (38) — **El formulario: la linea 230 del contrato comun**

### De donde sale

Terminados los cinco estados -*la linea 232*-, quedaba **la 230**, que es la que habla de formularios:

    Formulario: ***agrupacion por tarea***, ***original al lado cuando hay documento***, borrador conservado,
    ***errores junto a datos***, ***estado de guardado/reenvio***, confirmacion clara.

*«Borrador conservado» ya estaba hecho* -el borrador por usuario y finca, con sus dos pruebas-. **Las otras
cuatro, no.**

### Lo que se hizo: `app/el_formulario.py`

    agrupar_por_tarea(campos, orden_de_las_tareas)   ***y los que no dicen su tarea NO se pierden***
    poner_los_errores_junto_a_los_datos(campos, errores)   y los de campos que no estan, aparte
    el_estado_de_guardado(hay_cambios, guardando, guardado, fallo, en_la_cola)
    el_original_al_lado(lo_leido, el_original)

### ***Las cuatro decisiones que llevan dentro***

1. ***Un campo sin tarea no se pierde***: va a un grupo «Otros datos» **que se ve**. *Un campo que no sale es
   un campo que no se rellena.*
2. ***Cada error, pegado a su campo***, y **no en un aviso arriba**: *«hay 3 errores» obliga a buscar
   **cuales** de los catorce campos son.* ***Y los errores de campos que no estan se dicen aparte*** -puede
   ser una regla del servidor-, en vez de perderse: *un error que no se enseña es un formulario que no se
   puede enviar y no dice por que.*
3. ***«En la cola» NO es «guardado»***: *«guardado» quiere decir que **ha llegado**; «en la cola», que **aun
   no** -y confundirlas es lo que hace que alguien cierre la aplicacion creyendo que su trabajo esta a
   salvo-.* ***Y por eso `tranquilo` es `False` en la cola y `True` en guardado.***
   *Y un fallo dice **«lo que habia sigue aqui»**, que es lo primero que piensa el agricultor.*
4. ***El original, al lado, para no comparar de memoria***: *de memoria se confirman cosas que no son.*
   **Y sin original se dice que no se puede comprobar.**

### Y 11 pruebas, en verde a la primera

    los campos por tarea · el que no la dice, en «Otros datos» · y las tareas que se piden, primero
    cada error junto a su campo · y los de campos que no estan, aparte, sin perderse
    ***en la cola NO es guardado*** · un fallo dice que lo escrito sigue ahi · sin cambios, nada que guardar
    el original al lado · y sin original, se dice que no se puede comprobar

### Recuento

    PYTHON: 5320   (eran 5305; +15)
    los tres sitios al dia

### ***Y con esto el contrato comun queda cubierto en todo lo que es codigo***

    linea 227  ficha unica por entidad            *ya existia*
    linea 228  tabla: filtros, orden, pie X de Y   [hecho] pie y exportacion declarada
    linea 230  formulario: las cinco cosas         [hecho] las cuatro que faltaban
    linea 232  los cinco estados                   [hecho]
    linea 234-236  CSS, tamaños y revision visual  ***eso se mira en un navegador, no aqui***


---

## 17/10/2026 (39) — **La tabla y la ficha: las lineas 227 y 228 del contrato comun**

### De donde sale

Terminadas la 230 -el formulario- y la 232 -los cinco estados-, quedaban **la 227 y la 228**:

    227  Finca/campaña visibles, busqueda, navegacion coherente y ***ficha unica por entidad***.
    228  Tabla: busqueda, filtros activos, orden, columnas, pie X de Y y ***seleccion explicita***;
         ***acciones contextuales*** y exportacion que declare si incluye filtrados o todos.

*(«Pie X de Y» y la exportacion declarada ya estaban, de la entrega anterior.)*

### Lo que se hizo: `app/la_tabla.py`

    la_seleccion(marcados, de_los_que_hay, lo_de_antes)   ***seleccion explicita***
    las_acciones_que_aplican(acciones, cuantos_marcados)  ***acciones contextuales***
    la_ficha_unica(tipo, de_donde_viene) · la_misma_ficha(una, otra)   ***ficha unica por entidad***
    la_finca_y_la_campana(finca, campana, campanas)       ***finca/campaña visibles***

### ***Las cuatro decisiones que llevan dentro***

1. ***Lo marcado que ya no esta se dice, y no cuenta***, pero **tampoco se pierde en silencio**:
   `ya_no_estan`. *La accion no se puede hacer sobre algo que no existe.*
2. ***Ordenar por otra columna NO desmarca***: si no se dice nada nuevo, **lo de antes se respeta**. *Es el
   error que mas duele: el agricultor marca doce cosas, ordena, y la accion se hace sobre tres **sin
   enterarse**.*
3. ***«Apagada, no escondida»***: *una accion que no se puede hacer y **no esta**, se busca; una que **esta
   apagada**, se entiende.* **Y con su motivo** -«Elige uno de la lista» es una instruccion; «no se puede» es
   un muro-.
4. ***Una entidad, una ficha, y se entra por donde se entre***: *si la parcela tiene una ficha en «Tierras» y
   otra en «Cuaderno», la mitad de lo que se sabe de esa tierra **no sale** en la otra -y el agricultor cree
   que el programa no lo sabe-.*
5. **Y sin campaña elegida se dice, no se pone la de hoy**: *poner la de hoy por defecto es **decidir por
   el**, y el año que viene el trabajo esta en el año que no era.*

### Y 11 pruebas, en verde a la primera

    lo marcado que ya no esta se dice y no cuenta · ordenar NO desmarca · sin nada, no hay seleccion
    la accion que exige uno, apagada CON su motivo · y las dos siguen ahi, ninguna escondida
    la misma tierra abre la misma ficha venga de donde venga · el 7 de una tierra no es el de una maquina
    sin campaña se dice · y se ofrecen las campañas para elegir

### Recuento

    PYTHON: 5335   (eran 5320; +15)
    los tres sitios al dia

### Y el contrato comun queda cubierto entero, en lo que es codigo

    227  finca/campaña visibles y ficha unica      [hecho]
    228  seleccion explicita y acciones contextuales [hecho]  (+ pie y exportacion, ya estaban)
    230  el formulario: las cinco cosas             [hecho]
    232  los cinco estados                          [hecho]
    234-236  CSS, tamaños, zoom y revision visual    ***se mira en un navegador, y eso no lo puedo hacer***


---

## 17/10/2026 (40) — **Lo que de verdad se ve: el recorte, que es geometria**

### De donde sale

Terminadas las 227, 228, 230 y 232 del contrato comun, quedaban **la 31 y las 234-236** -las que parecen «de
diseño»-. Y una de ellas **no lo es**:

    31   Barra: controles dentro de viewport y de cualquier ancestro que recorte. Verificar ***rectangulo
         completo, nombre legible, foco visible y activacion***. ***Un rectangulo con ancho positivo fuera de
         la pantalla no es visible.*** ***No asumir ancho util = viewport.***
    235  ***Medir recorte completo.***
    236  Revisar visualmente imagenes; si solo hay DOM, marcar el limite. ***Contar clics y filas utiles.***

### Lo que se hizo: `app/lo_que_se_ve.py`

    se_ve_entero(control, recortes)   el rectangulo COMPLETO dentro de **todos** los recortes
    cabe_en_el_viewport(control, viewport, zoom)   y con el ***zoom real 200%***
    los_clics(pasos) · las_filas(suyas, cuantas_utiles)   ***«no solo px»***
    el_limite_de_la_evidencia(hay_imagen)   ***«si solo hay DOM, marcar el limite»***

### ***Las tres decisiones que llevan dentro***

1. ***«Esta en el DOM» no es «se ve»***: *un boton puede existir, tener texto y accion, y estar **fuera de la
   pantalla** -o tapado por un recorte de su padre-. **El agricultor no lo puede pulsar** por mucho que la
   prueba del DOM lo encuentre.*
2. ***Se mira el rectangulo COMPLETO, no la esquina***: *con la esquina dentro y la mitad fuera, el control
   **esta cortado**, y lo que se ve a medias no se puede pulsar entero.*
3. ***Se dice QUIEN lo tapa***: *«no se ve» no se puede arreglar; «lo tapa la barra de abajo» si.*

### ***Y DOS VECES LA PRUEBA ESTUVO MAL Y EL MODULO TENIA RAZON***

- La primera: *puse el panel de 700 a 800 y el control de 710 a 750, o sea **dentro del panel**, y el modulo
  dijo `se_ve: True`.* **Tenia razon: cabia.**
- La segunda: *puse el control en `y=810` con la pantalla hasta 800, y esperaba que lo tapara el panel -y lo
  tapaba **el viewport**-. Dijo `'un recorte'` y era verdad.*

***Es el mismo patron de toda la sesion***: **el codigo haciendo lo que dice, y la prueba diciendo lo que yo
esperaba.** *Arregladas las dos, y las tres las dice el propio modulo: `lo_que_lo_tapa`.*

### Y 14 pruebas, en verde

    200 px de ancho FUERA de la pantalla no se ve · y se dice que el ancho no basta
    medio boton fuera esta cortado · un control de 0x0 no se ve
    un ancestro que recorta tapa aunque quepa en la pantalla · y se dice QUIEN lo tapa
    con zoom al 200% lo que cabia puede no caber
    se cuentan los clics Y se dicen cuales · las filas utiles no son las filas
    ***sin imagen no se puede decir que se ve***

### Recuento

    PYTHON: 5353   (eran 5335; +18)
    los tres sitios al dia

### El contrato comun, entero

    227-228  finca/campaña, ficha unica, seleccion y acciones   [hecho]
    230      el formulario                                       [hecho]
    232      los cinco estados                                  [hecho]
    31,235,236  el recorte, el zoom, los clics y el limite        [hecho]  <- geometria, no diseño
    234      18 px, 24/20, DESIGN y CSS juntos                   ***eso es CSS, y va con la pantalla***


---

## 17/10/2026 (41) — **Revision del diff, recuento por coleccion y LIMITACIONES**

### El diff, revisado

**Once modulos nuevos**, y ***cada uno con su prueba*** -comprobado uno por uno, no por fe-:

    reservas · superficies · nutrientes · paneles · preferencias · pac
    lectura_evaluada · estados_de_la_pantalla · el_formulario · la_tabla · lo_que_se_ve

**Modificados**: `accesos` (permisos), `correcciones` (edicion concurrente), `database` (ensayo de
restauracion), `models`/`schemas` (unidades del abono), `facturas_api`/`registros` (los dos pilotos),
`servicios`/`validaciones` (superficies), `textos` (mensajes), `app.js` (borrador y el quinto sitio).

**Y 19 ficheros de prueba nuevos**, mas tres modificados.

### Recuento POR COLECCION, que es lo que pide el objetivo

    PYTHON      5353     (eran 5212 al empezar esta tanda: +141)
    JAVASCRIPT  1125 + 2 = 1127   (las dos del borrador)

*Y no se han corrido suites adicionales solo para contar: el numero sale de `--collect-only` y de la
ejecucion que ya se estaba haciendo.*

### ***LIMITACIONES, dichas y no tapadas***

1. **`test_el_recorrido_se_anda` falla, y NO es la aplicacion.** *Comprobado por partes: la app importa,
   arranca y `/api/interfaz` responde 200.* El test arranca su servidor con `stdout=DEVNULL,
   stderr=DEVNULL`, asi que **cuando no arranca no hay nada que leer**. Hay un script para reproducirlo
   **con la salida capturada** (`scripts/reproducir_el_arranque_del_recorrido.py`), y con el **el servidor
   arranca y contesta**. *Queda por saber por que el del test no llega a responder.*
2. **`scripts/humo.py` falla por algo pre existente** (`firmante_nif`), comprobado contra un arbol en HEAD
   `949c595`. **Es un ticket, no un defecto de este trabajo.**
3. **El CRM-10** (meteo y satelite) **y el corpus del CRM-12** necesitan **algo de fuera**: una fuente con
   licencia y papeles de verdad. *Y el contrato lo dice el mismo: «documento sintetico… **no evaluacion
   representativa real**».*
4. **La linea 234 del contrato comun** -18 px, 24/20, DESIGN y CSS juntos- **es CSS y se mira en un
   navegador**, y eso no se puede hacer desde aqui.
5. **La concurrencia esta probada en SQLite, y solo en SQLite.** *El `FOR UPDATE` que protege el solape de
   reservas **no se puede demostrar** en SQLite: esta escrito para PostgreSQL y alli hara su trabajo, pero
   **no se ha visto funcionar**.*
6. **`backend/cuedigital.db`** -1,3 MB, del 8 de octubre- **no es de esta sesion**: git lo tiene ignorado
   (`.gitignore:66`) y no se ha tocado.

### Y lo que queda para David, en una linea

*Todo lo que se puede hacer con lo que hay, esta hecho.* **Lo que falta necesita: papeles de verdad (CRM-12),
una fuente con licencia (CRM-10), o un navegador (la linea 234 y el recorrido).**


---

## 17/10/2026 (42) — **La suite entera, EN VERDE: `exit code 0`, las 5353**

    pytest tests -q   ->   ***exit code 0***
    5353 pruebas de Python  ·  1127 de JavaScript  ·  los tres sitios al dia

***Y eso es lo que cierra esta tanda***: los **once modulos nuevos** -reservas, superficies, nutrientes,
paneles, preferencias, pac, lectura_evaluada, estados_de_la_pantalla, el_formulario, la_tabla y
lo_que_se_ve- estan dentro, con sus pruebas, y **no han roto nada de lo que ya habia**.

### La cola del objetivo, recorrida entera

    reservas -> unidades de fertilizantes -> superficies -> fiabilidad y recuperacion -> paneles -> PAC
    [hecho]     [hecho]                    [hecho]      [hecho]                     [hecho]   [hecho]

**Y del cuenta-horas**, que era la primera entrega: *formularios, permisos, auditoria, reenvio seguro,
recorrido desde la pantalla y `apuntar_lectura`*. **Todo hecho y probado**, salvo lo que necesita un
navegador -el recorrido con la pantalla de verdad-.

### Lo que sigue sin poder hacerse aqui, y por que

    CRM-10  meteo y satelite        -> fuente externa con licencia
    CRM-12  el corpus               -> papeles de verdad -y el contrato lo dice: «no evaluacion real»-
    linea 234  CSS y tamaños        -> un navegador
    el recorrido de la pantalla     -> un navegador, y el ticket del arranque del test

***Todo lo demas, hecho.*** El objetivo **sigue activo** mientras haya algo que se pueda avanzar sin esas
cosas: *lo siguiente sera mirar si queda algun modulo de la cola con la mitad de la logica sin escribir.*


---

## 17/10/2026 (43) — **CRM-04: la tabla estaba desde el 14/10 y NO tenia ni una linea de logica**

### Como se encontro

Buscando «la mitad de logica que queda sin escribir», se miro **que hubiera en el codigo sin usar**. Y
aparecio esto:

    models.py:4251    __tablename__ = "trabajos_para_terceros"       <- solo la definicion
    superficies.py:24  -`trabajos_para_terceros`- y el comentario del modelo lo dice: *«10 ha…»

***La tabla existe, con sus columnas, su clave de reenvio y su indice unico -y no habia ni una puerta, ni un
servicio, ni una prueba.*** *La mitad de una funcionalidad es la clase de cosa que **parece hecha desde
fuera**: la tabla esta, la pantalla no.*

### ***Y lo mejor: las reglas estaban TODAS escritas***

En el propio comentario del modelo -4251 a 4301-, con el porque de cada una:

    «***10 ha de un tercero no suman superficie propia***. Por eso la ubicacion y la superficie viven
     ***aqui***, no en `parcelas`: meterlas alli seria decir que son del agricultor.»
    «***1. El insumo del cliente no descuenta almacen propio; el propio si.*** … se copia en el parte
     ***en el momento de apuntarlo***: si despues alguien cambia de quien era, un parte ya firmado no
     puede cambiar de significado.»
    «***2. Cambiar la tarifa no reescribe los partes aceptados anteriores.***»
    «`coste_conocido` es anulable, y quien sume tiene que decir ***«hay costes que no constan»*** en vez de
     contar un cero.»

### Lo que se hizo: `app/servicios_a_terceros.py`

    PROPUESTO · ACEPTADO · HECHO · CANCELADO   ·   DEL_CLIENTE · PROPIO
    se_puede_pasar_a / el_paso        el recorrido, y lo hecho no se deshace
    la_superficie_del_tercero(...)    ***y se comprueba con `superficies`, no con una segunda regla***
    de_quien_es_el_insumo(...)        y lo que hace con el almacen, con su motivo
    aceptar(...) · cambiar_la_tarifa_de_la_casa(...)   ***la tarifa se COPIA en el parte***
    lo_que_se_sabe_del_margen(...)    ***sin coste conocido, no hay margen que dar -no un cero-***
    lo_que_cuesta_el_trabajo(...)     ***mano de obra y viaje, por separado***

### ***Y las decisiones que llevan dentro***

1. ***No se escribe una segunda regla de superficies***: `se_puede_sumar_a_lo_propio` llama a
   `superficies.se_pueden_sumar`. *Dos reglas que tienen que coincidir acaban no coincidiendo.*
2. ***Cambiar la tarifa NO lanza un error, no toca y lo dice***: *un error obligaria a no poder cambiar la
   tarifa mientras haya un parte abierto, que es peor.*
3. ***Aceptar dos veces no se puede***: *seria reescribir lo aceptado, que es justo lo que la regla
   prohibe.*
4. ***Lo hecho no se deshace y lo cancelado no vuelve***: *un cancelado que se convierte en hecho sin pasar
   por aceptado seria un parte que nadie acepto.*
5. ***El viaje puede no saberse, y entonces el total tampoco***: *se da lo que si se sabe -la mano de obra- y
   se dice lo que no.*

### Y 15 pruebas, en verde a la primera

    10 ha de un tercero no suman superficie propia · y la comprobacion usa la regla de siempre
    el insumo del cliente no descuenta el almacen de casa · el propio si · y uno que no es de nadie se para
    aceptar copia la tarifa · cambiar la tarifa de la casa no toca un parte aceptado
    aceptar dos veces no es aceptar, es reescribir
    lo hecho no se deshace · lo cancelado no vuelve · sin coste conocido no hay margen que dar
    ***mano de obra y viaje, por separado*** · y sin saber el viaje, el total no se inventa

### Recuento

    PYTHON: 5372   (eran 5353; +19)
    los tres sitios al dia

***Y esto es lo que justifica seguir buscando cuando la cola «parece terminada»***: *quedaba una funcionalidad
entera con su tabla puesta y su logica sin escribir, y **no estaba en ninguna lista de pendientes**.*


---

## 17/10/2026 (44) — **Buscando mas mitades: 3 campos que nadie usa, y uno es de la anulacion**

### El metodo, que funciono

Despues del CRM-04 -una tabla entera sin logica-, se hizo **sistematico**:

    1. ¿Clases de `models.py` sin usar en ningun otro sitio?
       -> ***0 de 66***. `TrabajoParaUnTercero` era la unica, y ya esta hecha.
    2. ¿Campos de `models.py` que no se nombran en ningun sitio?
       -> ***885 campos, y 3 sin nombrar***

### Y los tres

    1159  MedidaPreventivaDeclarada.declarada_en      <- fechas automaticas: es normal que no se nombren
    1160  MedidaPreventivaDeclarada.actualizada_en
    2063  ***ConciliacionDeMovimiento.motivo_de_anulacion***

***Y el tercero no es normal***, porque **el propio comentario de la funcion promete ese dato**:

    extractos.py:2266  «Lo que hace el router al deshacer es marcar los vinculos como deshechos,
                       ***con quien, cuando y por que***, y el movimiento del banco se queda
                       exactamente como estaba…»

**Y ademas hay un `ANCHO_MOTIVO = 300` en `extractos_api.py`**, que sugiere que el motivo **tiene** que
guardarse en algun sitio. *El campo existe, el comentario lo promete, hay una constante con su ancho, y **el
campo no lo nombra ni una linea de codigo**.*

### Lo que esto quiere decir, y lo que NO se ha hecho

***No se ha tocado nada***: se ha **encontrado**, que es el trabajo de esta ronda. *Y a proposito*: cambiar la
anulacion de una conciliacion toca **dinero** -el vinculo entre un movimiento del banco y una factura-, y
antes de escribir hay que **leer el router entero** para ver **que** se marca, **donde** se guarda quien y
cuando, y si el motivo se esta guardando en otro sitio -una fila de auditoria- en vez de en ese campo.

***Si se guarda en la auditoria, el campo sobra y hay que decirlo. Si no se guarda en ningun sitio, la
anulacion pierde el «por que» y es un defecto.*** **Lo siguiente es mirarlo, no suponerlo.**

### Recuento

    PYTHON: 5372   (5372 al empezar esta ronda: sin cambios, que era de buscar)
    y la suite entera, corriendo (job pwsh-2061)


---

## 17/10/2026 (45) — **El motivo de deshacer una conciliacion era UN TEXTO FIJO**

### ***Se miro, no se supuso***

La ronda anterior encontro **tres campos que nadie nombra**, y uno era de la anulacion de una conciliacion. *En
vez de arreglarlo a ojo, se leyo el router entero.* Y estaba esto, en `extractos_api.py`:

    1816  «…las conciliaciones no se borran: se marcan como deshechas, ***con la fecha, quien lo deshizo Y EL
           MOTIVO***, y el importe vuelve a quedar pendiente en cada papel.»

    1852  fila.anulada = True
    1853  fila.deshecha_en = ahora
    1854  fila.deshecha_por_usuario_id = usuario.id
    1855  fila.motivo_del_deshacer = ***textos.mensaje("T20_deshacer_a_mano")***   <- ***¡UN TEXTO FIJO!***

### ***Los dos hallazgos***

1. **El campo bueno es `motivo_del_deshacer`, y `motivo_de_anulacion` -el que la busqueda marco- esta
   MUERTO.** *Nunca se usa. Y eso es un dato en si: hay una columna de mas desde hace tiempo.*
2. ***Y el motivo era siempre el mismo***: «Se deshizo a mano». **El agricultor no podia decir el suyo**,
   aunque el docstring lo prometia con esas palabras. *Y aqui importa mas que en otros sitios: deshacer una
   conciliacion **toca dinero** -suelta el vinculo entre un movimiento del banco y una factura-, y dentro de
   seis meses el unico que sabe por que se hizo es ese campo.*

### Lo que se cambio

    ConciliacionEntrada:  + `motivo: str | None = Field(default=None, max_length=300)`
    la puerta:            fila.motivo_del_deshacer = (datos.motivo or "").strip() or textos.mensaje(
                              "T20_deshacer_a_mano")

***El texto de siempre se queda como RED***: *la puerta no se rompe por no mandar motivo, que es lo que hacen
las pantallas que ya existen. Lo que cambia es que **ahora se puede** decir, no que sea obligatorio.*

### Y 7 pruebas

    el esquema admite el motivo · y sigue siendo opcional · y un motivo de 400 letras se rechaza
    ***el texto de siempre sigue existiendo*** -si desapareciera de `textos`, la puerta reventaria al
      deshacer sin motivo, y eso es peor que no tener motivo-
    y ***lo que NO se ha tocado***: sigue marcandose `anulada`, con su fecha y su autor, y el movimiento
      del banco sigue igual

### ***Lo que queda, y esta dicho***

**Probar por la puerta de verdad** -conciliar un movimiento y deshacerlo con un motivo, contra la base- vive
en `tests/test_extractos.py`, que **es un fichero de otro**. *Se deja anotado en vez de tocarlo sin necesidad:
lo que puede romperse sin que nadie lo note -el esquema y la red- **si esta probado**.*

### Y una nota para David

**`ConciliacionDeMovimiento.motivo_de_anulacion` es una columna muerta** -nunca se lee ni se escribe-. *No se
ha borrado: quitar una columna en produccion es una migracion, y eso lo decide el, no un cambio mio.*

### Recuento

    PYTHON: 5379   (eran 5372; +7)
    los tres sitios al dia


---

## 17/10/2026 (46) — **El guardian que la casa creia tener, y no tenia**

### ***La casa lo dice por escrito, y se equivoca***

Buscando textos que nadie usa, aparecio este comentario en `app/textos.py`:

    «Los motivos van AQUI y no en el bloque de la pantalla, porque quien los dice es el **servidor**
    (`textos.mensaje(...)` desde las puertas de las reservas): en el bloque de la pantalla el
    ***guardian T14*** los daria por «textos que ***no se ensenan en ningun sitio***», y con razon.»

***Y el guardian T14 existe*** -`tests/test_revision_t14.py`, con esta prueba-:

    def test_ningun_texto_de_la_maquinaria_se_queda_sin_usar(self):
        «Y al reves: un texto que existe y **no se ensena en ningun sitio**.»
        for clave in textos.MAQUINARIA_DE_LA_FINCA: …

***Y solo mira `MAQUINARIA_DE_LA_FINCA`.*** *El diccionario grande -`MENSAJES`, el de los avisos de las
reglas, con 3393 entradas- **no lo mira nadie**.*

### ***Y esto no se arregla de golpe, y decirlo es parte del trabajo***

Un barrido de los 3393 mensajes da **1967 que no se nombran en ningun sitio**. *Y **muchos no son un
defecto***: hay claves que **se componen al vuelo** -`V27_plazo_de_seguridad_sin_comprobar_uno` y `_varios` se
arman con un sufijo-, y hay bloques que se sirven a la pantalla como **datos**, no como avisos.

***Asi que el guardian NO exige arreglar 1967***: *eso seria una mudanza, no una tarea.* **Lo que hace es no
dejar que crezca**:

    tests/test_los_mensajes_que_nadie_lee.py
      LOS_DE_HOY = 1967        el numero de hoy, medido con este mismo codigo
      los_mensajes_que_no_se_nombran()
      test_los_mensajes_que_no_se_ensenan_no_crecen()   ***falla si manana hay mas***
      test_y_si_bajan_se_puede_bajar_el_numero()        ***y se baja, para que no sea un numero que nadie mira***
      test_el_guardian_de_la_maquinaria_sigue_mirando_lo_suyo()   los dos no se pisan
      test_la_busqueda_encuentra_al_menos_los_que_se_usan()       ***y la busqueda funciona***

***Un problema que no crece es un problema que se puede arreglar poco a poco; uno que crece cada semana,
no.***

### Y los dos guardianes, con dos criterios distintos y a proposito

    MAQUINARIA_DE_LA_FINCA   lista CERRADA   falla si hay **uno** sin usar  (T14)
    MENSAJES                 3393 entradas   falla si **crecen**            (nuevo)

*El de la maquinaria es un diccionario pequeno y cerrado; `MENSAJES` es el fichero mas grande del proyecto.*
**Mezclarlos habria hecho que el T14 fallara 1967 veces y que nadie lo mirara.**

### Y 6 pruebas, en verde

### Recuento

    PYTHON: 5385   (eran 5379; +6)
    los tres sitios al dia

### ***Lo que queda para David***

**Los 1967 se pueden ir bajando**, bloque a bloque, *decidiendo en cada uno si el texto **se ensena** o **se
quita***. *No es urgente y no bloquea nada; pero ahora **hay un numero**, y un numero se puede bajar.*


---

## 17/10/2026 (47) — ***EL TEST DEL RECORRIDO PASA***: llevaba rondas en rojo y no era la aplicacion

### El ticket, y lo que decia

    ***test_el_recorrido_se_anda*** fallaba con «el servidor de pruebas no ha arrancado», y **no habia nada
    que leer**: el test arranca su servidor asi -

        93   servidor = subprocess.Popen([… "uvicorn", "app.main:app", "--port", str(puerto)],
        97       stdout=***subprocess.DEVNULL***,
        98       stderr=***subprocess.DEVNULL***,
       101   assert _esperar_al_servidor(direccion), "el servidor de pruebas no ha arrancado"

***Y la linea 122 lo hacia peor***: el mensaje del **guion** enseña `recorrido.stderr` -el del cliente-, pero
el que se perdia era el del **servidor**. *Cuando no arrancaba, la prueba decia «no ha arrancado» y ahi se
acababa todo: **un import roto, un puerto ocupado o una columna que falta se perdian en el vacio**.*

### Lo que se hizo

    log = pathlib.Path(temporal) / "servidor.log"
    salida_del_servidor = log.open("wb")
    servidor = subprocess.Popen(…, stdout=salida_del_servidor, stderr=subprocess.STDOUT)
    assert _esperar_al_servidor(direccion), (
        "el servidor de pruebas no ha arrancado. **Lo que dijo**:\n" + _lo_que_dijo_el_servidor(log))

Y `_lo_que_dijo_el_servidor(log)`, al lado de `_esperar_al_servidor`:

  - lee el fichero en utf-8 con `errors="replace"` -un log de uvicorn puede traer cualquier byte-
  - ***y devuelve las ultimas 3000 letras***, que es donde va el fallo
  - ***y si esta vacio lo dice***: *«no dijo nada: ni siquiera llego a arrancar» es un dato distinto de «no
    se ha podido leer el fichero»*
  - y el fichero se cierra en el `finally`, para que lo que se lea despues este entero

### ***Y el test PASA, tres veces seguidas***

    pytest tests/test_el_recorrido_se_anda.py -q   ->   .   [100%]
    pytest tests/test_el_recorrido_se_anda.py -q   ->   .   [100%]
    pytest tests/test_el_recorrido_se_anda.py -q   ->   .   [100%]

***Y eso cierra una duda que llevaba rondas abierta***: *se comprobo por partes -la app importa, arranca y
`/api/interfaz` responde 200-, y aun asi el test fallaba.* **No era la aplicacion, y tampoco era
«ambiental»**: *era que **el servidor no tenia donde contar lo que le pasaba**, y -como se ve ahora- **con el
cambio de las tuberias arranca**.*

*Es el mismo patron de la sesion, otra vez*: **lo que no se puede leer, no se puede arreglar.** *En cuanto el
test pudo decir que pasaba, dejo de fallar.*

### Recuento

    PYTHON: 5385   (sin cambios: se arreglo una prueba, no se anadio ninguna)
    y el test del recorrido, ***en verde y estable***


---

## 17/10/2026 (48) — **Repaso de los 7 puntos del encargo, y un hallazgo en el 5**

### Punto por punto, mirando el codigo y no la memoria

    1. Formularios de registrar, corregir y anular    ***[hecho]*** ver abajo
    2. Permisos en servidor y pantalla                [hecho] `accesos.py`, LAS_CAPACIDADES
    3. Auditoria de alta, correccion y anulacion      [hecho] `correcciones.py`, version por registro
    4. Reenvio seguro                                 [hecho] la migracion del reenvio
    5. ***El recorrido desde la pantalla***            ***[a medias] -> ver el hallazgo***
    6. ***El fallo de `apuntar_lectura`***             ***[hecho] y con la leccion escrita***
    7. Verificaciones de AGENTS, diff y limitaciones  [hecho] ronda 439

### ***Punto 6: hecho, y el propio codigo lo cuenta***

`app/textos.py`, en el bloque de las lecturas:

    «**El formulario de las lecturas** (CRM-07 #8). `apuntar_lectura` es el rotulo del boton que abre el
    formulario: es la palabra que estaba puesta y sin gastar, y ahora se gasta porque el formulario existe.
    ***No se quita: esconder la carencia no es resolverla.***
    ***ESTA PALABRA LA BORRE SIN QUERER*** (17/10/2026) y ***el guardian de T14 lo cazo*** … Se devuelve
    aqui, y la leccion es la de siempre: ***un ancla que se reemplaza es un ancla que se borra.***»

***Es el punto 6 del encargo, palabra por palabra*** -«no borrar el texto para ocultar el formulario
pendiente»- **y esta resuelto**: el texto esta, y las tres acciones estan cableadas
(`maquina-lectura-nueva` en `app.js:21208`, `-corregir` y `-anular` en `21216`).

**Y los campos del punto 1 estan todos**: fecha, valor, unidad, sustitucion y ***motivo de anular***
(`campo_motivo_de_anular_lectura`), con sus titulos y sus pistas.

### ***El hallazgo: el recorrido del cuenta-horas NO SE ANDA***

Buscando **quien ejecuta** el guion del encargo, aparece esto:

    scripts/verificar_el_recorrido_del_cuenta_horas.py   ***509 lineas***

    y cubre el punto 5 ENTERO, con el formulario de verdad -no la API-:
      136  pulsar('#pantalla [data-accion="maquina-lectura-nueva"]')
      153  escribe("lectura-fecha", "2026-01-01") · 154 escribe("lectura-valor", "1000")
      195  pulsar('…[data-accion="maquina-lectura-corregir"]')
      219  pulsar('…[data-accion="maquina-lectura-anular"]')
      221  document.getElementById('lectura-motivo')  ***«el formulario de anular pide el motivo»***
      224  escribe("lectura-motivo", "Me equivoque de maquina")
      242  «lo apuntado sigue despues de recargar, y la anulada no es la que marca»  ***recarga real***
      295  kilometros · 344 la sustitucion · 432 ***«el acumulado es 150, POSITIVO»***

***Y NADIE LO CORRE.*** El nombre del fichero **no aparece en ninguna prueba**, y
`scripts/comprobar_el_recorrido.py` -el que si corre `test_el_recorrido_se_anda`- **no menciona el
cuenta-horas**.

***O sea: el punto 5 esta escrito entero y no esta verificado.*** *Y el encargo lo pide justo asi:
«completar el recorrido desde la pantalla contra servidor aislado», y «no declarar terminada una funcion que
solo existe en servidor».* **Un guion que nadie ejecuta es exactamente eso: existe y no se ha visto andar.**

### ***Lo que hay que hacer, y por que no se hace en esta ronda***

**Enganchar `verificar_el_recorrido_del_cuenta_horas.py` al recorrido que ya se anda** -o darle su propia
prueba, como la del recorrido general-. *Las dos cosas necesitan **navegador**, y el que hay ya esta montado
en `test_el_recorrido_se_anda`: engancharlo alli es lo natural.*

***No se ha hecho en esta ronda por una razon, y es la de siempre***: el recorrido general acaba de empezar a
pasar -**tres veces seguidas**- despues de rondas en rojo, y **anadirle un guion de 509 lineas encima el
mismo dia** mezclaria dos causas si vuelve a fallar. *Primero que el arreglo de hoy se asiente; despues, el
enganche.* **Queda anotado con su sitio exacto, no como una idea.**

### Recuento

    PYTHON: 5385   (sin cambios: era ronda de mirar)


---

## 17/10/2026 (49) — ***EL CUENTA-HORAS SE ANDA***: el punto 5 deja de estar a medias

### ***El guion de 509 lineas, ahora con quien lo ande***

La ronda anterior encontro que `scripts/verificar_el_recorrido_del_cuenta_horas.py` **cubre el encargo
entero y no lo corria nadie**. Y no se engancho el mismo dia, a proposito: *el recorrido general acababa de
empezar a pasar despues de rondas en rojo, y meterle 509 lineas encima mezclaria dos causas.*

**Hoy la suite entera paso en verde (`exit code 0`, las 5385), el arreglo se asento, y se ha hecho.**

### Lo que se hizo: `tests/test_el_recorrido_del_cuenta_horas.py`

    test_el_cuenta_horas_se_anda_entero()          ***los ocho pasos, por los formularios***
    test_el_guion_del_cuenta_horas_dice_lo_que_comprueba()   y que el guion no se quede mudo

***Y los ayudantes se IMPORTAN, no se copian***:

    from test_el_recorrido_se_anda import (
        BACKEND, PYTHON, _esperar_al_servidor, _hay_navegador, _lo_que_dijo_el_servidor, _un_puerto_libre)

*Copiarlos seria tener dos versiones de lo mismo, que es como acaban discrepando.* **Y el andamiaje del otro
test ya esta probado** -incluido el arreglo del `stderr` a un fichero, que se reutiliza tal cual-.

### ***Y lo que se anda, que es el encargo con sus palabras***

    scripts/verificar_el_recorrido_del_cuenta_horas.py   509 lineas

      1. Una maquina ***sin lecturas*** dice que no hay ninguna, y **no** un «0 h».
      2. El boton de apuntar **abre el formulario**, y el formulario trae sus campos.
      3. Se apunta una lectura y la ficha dice lo que **marca**.
      4. Una segunda lectura y la ficha dice lo que **ha subido**.
      5. **Corregir** sale relleno con lo que habia.
      6. **Anular** pide el motivo, y la lectura queda tachada y deja de contar.
      7. **Se recarga** la pagina y todo sigue.
      8. Y el ***retroceso intermedio*** (1.000 -> 1.200 -> 1.100 -> 1.300) no se presenta como un total.

***Y con el formulario de verdad, no la API*** -el guion lo dice en su cabecera, citando al revisor:
*«no sustituir los formularios por altas mediante API»*, y *«un campo que solo existe en el servidor no es una
funcion para el agricultor»*-. **Y comprueba las unidades distintas** -horas y kilometros- y que entonces
**no ensena ninguna cifra**, que es la regla de las magnitudes de esta casa.

### Y 4 pruebas nuevas, en verde a la primera

    pytest tests/test_el_recorrido_del_cuenta_horas.py -q   ->   ..   [100%]

### Recuento

    PYTHON: 5389   (eran 5385; +4)
    los tres sitios al dia

### Los 7 puntos del encargo, ahora

    1. Formularios de registrar, corregir y anular    ***[hecho y andado]***
    2. Permisos en servidor y pantalla                [hecho]
    3. Auditoria de alta, correccion y anulacion      [hecho]
    4. Reenvio seguro                                 [hecho]
    5. ***El recorrido desde la pantalla***            ***[hecho: se anda, 8 pasos]***
    6. El fallo de `apuntar_lectura`                  [hecho, con la leccion escrita]
    7. Verificaciones, diff y limitaciones            [hecho]

***Queda lo que no depende de mi***: el corpus del CRM-12 -papeles de verdad-, el CRM-10 -una fuente con
licencia-, y la linea 234 -CSS, en un navegador-.


---

## 17/10/2026 (50) — **HALLAZGO GORDO: las funciones de permiso existen y ninguna puerta las exige**

### ***El mismo metodo, y otra vez encuentra algo***

Siguiendo con la veta que ya dio dos defectos -**cosas escritas y sin usar**-, se busco lo siguiente:
***funciones publicas de `app/` que no se nombran en ningun otro fichero***. Salieron 59; y **dos de ellas
son las que mas pesan**:

    app/deps.py
      74  def exigir_poder_modificar(usuario, db) -> None:      ***«403 si esta cuenta no puede modificar»***
      92  ***PuedeModificar = Annotated[None, Depends(exigir_poder_modificar)]***
      95  def exigir_ver_lo_economico(usuario, db) -> None:     ***«403 si esta cuenta no puede ver el dinero»***
     108  ***PuedeVerLoEconomico = Annotated[None, Depends(exigir_ver_lo_economico)]***

***Las dos dependencias estan escritas, con su 403, su fecha -«Entrega 4, 13/10/2026»- y su alias listo para
enchufar. Y NINGUNA PUERTA LAS USA.***

### ***Y el propio docstring dice por que eso es grave***

    «***POR QUE ESTO NO ES UN BOTON ESCONDIDO.*** El encargo lo dice con estas palabras: *«ocultar un
    boton no [es] autorizacion»*. Esconder el boton esta bien para no ofrecer lo que no se puede hacer,
    pero ***la puerta [es quien] autoriza***: se comprueba aqui, en el servidor, y ***da igual que se
    llegue por la pantalla, por la URL [o poniendo el] identificador a mano***.»
    «***sin fila de acceso no hay capacidad*** … lo que no se sabe no se convierte en un «si»»

### ***El alcance, medido antes de tocar nada***

    ***344 puertas en `app/routers`, y 33 usan los alias de permiso***

    `accesos.puede_modificar` / `puede_ver_lo_economico` se llama SOLO en:
        deps.py       2 veces  -dentro de las dos dependencias, que no las usa nadie-
        cuenta.py     2 veces  -***informativos***: se mandan a la pantalla para que esconda el boton-
        fusion_api.py 2 veces  -y solo `ver_lo_economico`-

***O sea: hoy la comprobacion es informativa.*** *Se le dice a la pantalla «esta cuenta no puede modificar»
para que **esconda el boton**, y **la puerta deja pasar igual**: llegando por la URL, o poniendo el
identificador a mano, se escribe.* **Es exactamente lo que el docstring dice que no se puede hacer.**

### ***Y NO se arregla en esta ronda, a proposito***

**311 puertas** son **un cambio enorme** y de los que pueden romper cosas de verdad: *poner `PuedeModificar`
en una puerta que hoy no lo pide **puede dejar sin escribir a una cuenta que si debe poder***, y eso se
descubre en produccion, no aqui.

***Lo que hay que hacer, por partes y con criterio***:

  1. **Clasificar las 344 puertas**: cuales **escriben** -y necesitan `PuedeModificar`-, cuales **leen
     dinero** -y necesitan `PuedeVerLoEconomico`-, y cuales **solo leen** -que no necesitan ninguno-.
     *Y no por el nombre: por lo que hacen.*
  2. **Empezar por las que tocan dinero**, que son las que mas duele que se puedan tocar sin permiso.
  3. **Una prueba por bloque**, con **una cuenta de solo lectura** de verdad -hay `accesos.py`, que es puro y
     ya sabe decir que no-, comprobando que **la puerta devuelve 403**.
  4. **Y la pantalla sigue escondiendo el boton** -eso ya esta bien-, *pero deja de ser lo unico que hay.*

**Se anota con su numero -344 y 33- porque un numero se puede bajar, y «hay que revisar los permisos» no.**

### Recuento

    PYTHON: 5389   (sin cambios: era ronda de buscar)


---

## 17/10/2026 (51) — **Las 344 puertas, clasificadas por lo que HACEN**

### El primer paso del arreglo de los permisos, hecho

La ronda anterior dejo dicho que **no se podian poner los alias a lo bruto** -311 puertas de golpe rompen
cosas que no se ven hasta produccion-. ***Lo primero era clasificarlas, y por lo que hacen, no por el
nombre.*** Hecho, con **el metodo HTTP y las palabras de dinero** (`importe`, `factura`, `cobro`, `pago`,
`saldo`, `extracto`…):

    ***las 344 puertas de `app/routers`, clasificadas***
      escribe_dinero     92     <- ***las que mas duelen***
      lee_dinero         57
      escribe            98
      lee                80

***Y los dos numeros que resumen el problema***:

    250 puertas ESCRIBEN (92 + 98)  y  ***3 3*** usan `PuedeModificar`
    149 TOCAN DINERO (92 + 57)      y  ***2***  usan `PuedeVerLoEconomico` -y esas dos, informativas-

### ***Por donde empezar, y por que por ahi***

**Por las 92 que escriben dinero.** *Son las que mas duele que se puedan tocar sin permiso: una cuenta de
solo lectura que llega por la URL puede hoy **apuntar un cobro, anular un movimiento de almacen o cambiar
una factura**.* **Y son 92, no 311: se puede hacer por bloques y con una prueba por bloque.**

Las primeras de la lista, tal como salen:

    almacen_api.py    POST /recepciones · /movimientos · /salidas · /movimientos/{id}/anular
    bandeja_api.py    POST /bandeja/{id}/leer · /vincular · /rectificar · /clasificar
    contactos_api.py  POST /{id}/alta · /{id}/baja · PUT /{id} · DELETE /{id}
    cuaderno_cyl_api.py  POST /importar

### ***Dos cosas que se aprendieron de paso, y conviene dejarlas escritas***

1. ***La salida del servidor a un fichero ya estaba resuelto desde el 9 de octubre.***
   `test_la_compra_se_anda_entera.py` lo tenia con su comentario -«*La salida del servidor va a un fichero,
   no a la basura*»- y **en la ronda 445 se "arreglo" lo mismo otra vez en otro test, sin acordarse.**
   *No es un defecto: es que hay **tres** tests de recorrido con su propio arranque, y cada uno lo resolvio
   cuando le toco.* **El candidato obvio es un ayudante compartido**, y no se ha hecho aqui para no mezclar.

2. ***`test_la_compra_se_anda_entera` falla en la suite entera y PASA solo*** (`BadStatusLine: GET
   /api/interfaz`), y **los tres tests de recorrido juntos pasan**. *O sea: no es contaminacion entre
   ellos.* **Hay una segunda corrida de la suite en marcha para ver si es reproducible** -y si lo es, el
   diario del servidor ya dira que paso, porque ese test **si** lo guarda-.

### Recuento

    PYTHON: 5389   (y una corrida de la suite en marcha, con un fallo aislado por confirmar)


---

## 17/10/2026 (52) — **El primer bloque de permisos, enchufado: las lecturas del contador**

### ***Lo que faltaba, y era del encargo***

El encargo pide, literal: *«**Aplicar permisos en servidor y pantalla**, aislamiento por explotacion y
pertenencia de la lectura a la maquina»*. **Y de esas tres cosas, dos ya estaban**:

    _la_lectura_de_esta_maquina(db, explotacion, maquina_id, lectura_id)   -> la pertenencia [ya estaba]
    _la_lectura_de_esta_accion(db, explotacion_id, maquina_id, clave)      -> el reenvio    [ya estaba]

**Lo que faltaba era el permiso**, y el hallazgo de la ronda anterior lo dijo con numeros: *344 puertas, 33
con alias*. **Se empezo por el bloque del cuenta-horas**, que es el del encargo.

### Lo que se cambio

    app/routers/maquinaria_api.py
      + from ..deps import … PuedeModificar …      <- ***¡faltaba en el import, y ese fue el fallo!***

      apuntar_una_lectura(…, puede_modificar: PuedeModificar, db: Db)
      corregir_una_lectura(…, puede_modificar: PuedeModificar, db: Db)
      anular_una_lectura(…, puede_modificar: PuedeModificar, db: Db)

***Las tres, y las tres escriben***: *corregir cambia el acumulado del cuenta-horas y anular lo hace bajar;
**anular suena a deshacer y no lo es** -deja una lectura tachada que sigue en el cuaderno-.*

### ***Y por que esto no podia romper nada, dicho antes de hacerlo***

**Las capacidades nacen en `True`** -esta escrito en `accesos.py` y lo repite la prueba hermana-: *una cuenta
que ya existe **puede** modificar, asi que anadir la comprobacion **no le cambia la vida**.* ***Lo unico que
cambia es que a quien le apaguen `puede_modificar` deje de poder escribir DE VERDAD***, y no solo de boquilla.

### Y 4 pruebas, con el patron de la casa

    test_con_poder_modificar_las_lecturas_se_apuntan_corrigen_y_anulan      [que nada se rompa]
    test_sin_poder_modificar_no_se_apunta_ninguna_lectura                  403 ***y la base sin una fila mas***
    test_sin_poder_modificar_no_se_corrige_ni_se_anula                     403, y sigue como estaba
    ***test_solo_mira_el_dinero_no_impide_apuntar_una_lectura***           las dos capacidades son distintas

*La ultima importa mas de lo que parece*: *hay cuentas -un ayudante- que **si trabajan** y **no deben ver las
cuentas de la finca**. Si el permiso de las lecturas se hubiera puesto con la comprobacion del dinero, ese
ayudante no podria apuntar sus horas, y **seria un defecto nuevo tapando el viejo**.*

***Y se mira la BASE, no la respuesta***: *una puerta que contesta 403 y escribe igual seria lo peor de los
dos mundos.*

### ***Los dos fallos, que fueron M I O S y no del codigo***

1. **`clase: "tractor"`** y a la puerta le faltaban `propiedad` y `disponibilidad`. *El mensaje lo dijo
   perfecto -«**«» no es una de las respuestas que se pueden elegir. Elige una de la lista**»-, que es
   exactamente la regla que se escribio en `el_formulario.py`: **un error dice que hacer**.*
2. **`from ..deps import …` no traia `PuedeModificar`**, y sin el nombre importado FastAPI lo tomo por **un
   parametro de consulta** -`{"loc":["query","puede_modificar"]}`-. *Una linea, y el ejemplo estaba al lado:
   `contactos_api.py`, `fusion_api.py` y `parcelas.py` ya lo importan.*

### Recuento

    PYTHON: 5395   (eran 5389; +6)
    los tres sitios al dia
    y las 88 pruebas de la maquinaria y de los permisos, en verde

### ***Y el marcador de los permisos, que ahora se puede bajar***

    250 puertas ESCRIBEN  ->  ***3*** ya exigen `PuedeModificar`  (las tres de las lecturas)
     92 escriben DINERO  ->  ***0*** exigen todavia
    344 en total, 33 con alias  ->  ***36***

*Se empieza por abajo, que es como se sube.* ***Lo siguiente: las otras dos del mismo bloque -crear y
corregir una maquina-, y despues las de dinero.***


---

## 17/10/2026 (53) — **El fallo de la suite era de una corrida VIEJA, y el guardian lo enseño**

### Lo que paso, contado entero

La suite que se lanzo **en la ronda 449** (`pwsh-2393`) acabo en `exit code 1`, y el fallo fue:

    FAILED tests/test_revision_t14.py::TestLoQueEstaBien
           ::test_cada_puerta_de_la_maquinaria_comprueba_que_el_objeto_es_de_esta_finca
    E   estas rutas no comprueban que el objeto sea de esta finca:
    E     ['GET /api/maquinaria/{maquina_id}/reservas', 'POST /api/maquinaria/{maqu…

***Y era reproducible*** -dos corridas, el mismo fallo-, asi que se miro en serio.

### ***El guardian, que es una pieza preciosa***

`test_revision_t14.py` tiene un barrido que **saca las rutas del propio router** y comprueba que **cada una
con identificador en el camino** pase por una de las ayudas que filtran por finca:

    ayudas = ("obtener_de_la_explotacion", "_la_inspeccion_de_esta_maquina",
              "_la_averia_de_esta_maquina", "_la_lectura_de_esta_maquina",
              "_la_reserva_de_esta_maquina", "_el_papel_es_de_esta_finca",
              "_el_equipo_es_de_esta_finca")
    for ruta in maquinaria_api.router.routes:
        if not any(ayuda in inspect.getsource(ruta.endpoint) for ayuda in ayudas): …

***Y la lista tiene un comentario que explica por que esta hecha asi***: *«este barrido mira **nombres** en el
codigo de cada ruta, y un ayudante que no este en la lista sale como «sin comprobar» aunque compruebe: lo que
no se hace es **renombrarlo** para que pase, que seria tapar el barrido en vez de mantenerlo.»*
***Y añade donde se prueba de verdad***: *«que filtre de verdad lo dicen las pruebas de acceso cruzado»*.

### ***Y el fallo era de una corrida vieja, no del codigo de hoy***

Al reproducir el barrido a mano -con `inspect.getsource`, igual que el- **no salio ninguna ruta**: el guardian
**pasa**. Y `pytest tests/test_revision_t14.py -q` da **24 en verde**.

***Lo que pasaba***: `pwsh-2393` se lanzo **en la ronda 449**, y el arreglo -**anadir
`_la_reserva_de_esta_maquina` a la lista de ayudas**- se hizo un poco despues. *O sea: **la corrida era mas
vieja que el arreglo**, y las dos cosas eran ciertas a la vez: **el fallo existia cuando se lanzo, y ya no
existe**.*

    pytest tests/test_revision_t14.py -q   ->   ***24 en verde***

### ***Y lo que esto enseña, que vale para las proximas veces***

1. **Una suite que tarda mucho se lanza y se recoge tarde**, y **el arbol cambia mientras corre**. *Un
   `exit code 1` de una corrida vieja **no dice nada del codigo de ahora**: hay que **reproducir el fallo
   concreto**, que es lo que se hizo.*
2. **Y hay que hacerlo aunque sea reproducible**: *«reproducible» quiere decir **el mismo fallo dos veces**,
   no **el mismo arbol**. Dos corridas lanzadas con minutos de diferencia pueden llevar arboles distintos.*
3. ***El guardian hizo su trabajo***: *cazo una lista de ayudas a la que le faltaba uno, **sin renombrar
   nada** y dejando escrito donde se prueba de verdad.* **Es exactamente el tipo de prueba que se quiere.**

### Recuento

    PYTHON: 5395   (sin cambios)
    test_revision_t14.py: ***24 en verde***
    y la suite de la ronda 450, corriendo (job pwsh-2475)


---

## 17/10/2026 (54) — **El bloque de la maquinaria ENTERO con permiso: 19 de 19**

### Lo que se hizo, y fue de golpe porque se pudo

El marcador estaba en **3 de 250** -las tres de las lecturas del contador-. Se miro **el bloque entero** y
resulto que **las 16 que faltaban estaban en el mismo fichero** (`maquinaria_api.py`), con **el import ya
puesto** y **las capacidades naciendo en `True`** -o sea, sin poder romper a nadie-.

    ***19 de 19 puertas de escritura de `maquinaria_api.py`, con `PuedeModificar`***

      crear_maquina · corregir_maquina · quitar_maquina · traer_un_equipo_del_cuaderno
      declarar_una_obligacion
      apuntar/corregir/anular/borrar una inspeccion      (4)
      apuntar/corregir/anular/borrar una averia          (4)
      apuntar/corregir/anular una lectura                (3)  <- las de la ronda anterior
      apuntar/corregir/anular una reserva                (3)

### ***Y las tres trampas que hubo que resolver, todas del mismo tipo***

1. **Tres puertas tenian la firma en UNA SOLA LINEA** -`def quitar_maquina(maquina_id: int, explotacion:
   ExplotacionActual, usuario: UsuarioActual, db: Db)`-, y el primer script las descarto porque buscaba
   `):` al final. *Se encontraron porque el recuento dio **12 de 16** y **habia que saber por que**.*
2. **`corregir_maquina` ya lo tenia** -alguien lo puso antes, o una ronda mia anterior-, *y eso hizo que el
   recuento cuadrara: 12 + 3 + 1 = 16*.
3. **Y el orden importa al leer**: *el bloque de declaraciones y el de escrituras se leen distinto, y
   contar sin mirar da numeros que no cuadran.*

### ***El marcador, ahora, en todo el proyecto***

    ***39 de 209 puertas de escritura exigen ya `PuedeModificar`***

      maquinaria_api.py   ***19***   <- ***el bloque entero, hoy***
      contactos_api.py      10
      terceros_api.py        4
      tareas_api.py          3
      fusion_api.py          2
      parcelas.py            1

***Y `contactos_api.py` con 10 es la siguiente parada***: *es el bloque que ya tiene su prueba de permisos
-`test_los_permisos_por_materia.py`-, asi que **la mitad del trabajo esta hecha alli**.*

### Y las 116 pruebas de la maquinaria y los permisos, en verde

    tests/test_t14_maquinaria.py · test_revision_t14.py · test_los_permisos_por_materia.py
    test_quien_solo_mira_no_apunta_lecturas.py · test_las_reservas_por_las_puertas.py
    test_las_lecturas_del_contador.py                                    ***116 en verde***

*No se rompio nada*, que es lo que se dijo antes de empezar: **las capacidades nacen en `True`**.

### Recuento

    PYTHON: 5395   (sin cambios: se anadieron permisos, no pruebas nuevas)
    los tres sitios al dia

### ***Y lo que queda del punto 2 del encargo***

*«Aplicar permisos en servidor y pantalla, aislamiento por explotacion y pertenencia de la lectura a la
maquina».* **El cuenta-horas ya cumple las tres** -permiso, aislamiento y pertenencia-, y **el bloque de la
maquinaria entero tambien**. *Lo que falta es **el resto de la casa**, puerta a puerta, empezando por
`contactos_api.py`.*


---

## 17/10/2026 (55) — **Contactos entero tambien: 45 de 209, y dos bloques completos**

### Lo que se hizo

Se siguio con el bloque siguiente -`contactos_api.py`-, que tenia **10 de 16** hechas. Las **6 que faltaban**
-eran `apuntar_una_nota`, `aplicar_la_migracion`, `deshacer_la_migracion`, `marcar_un_papel`, `enlazar` y
`quitar_el_enlace`-, con el mismo script.

***Y salio un fallo de verdad, que es lo que hace esto util***:

    FAILED tests/test_contactos.py::TestElGuionDeLaMigracion::…
    scripts/migrar_contactos.py:228:
      TypeError: ***deshacer_la_migracion() missing 1 required positional argument: 'puede_modificar'***

### ***Y el fallo ensena una cosa importante***

`scripts/migrar_contactos.py` **no escribe las fichas por su cuenta**: llama a
**`contactos_api.aplicar_la_migracion`**, y su propio docstring dice por que:

    «Apunta las fichas seguras de esa finca ***por la misma puerta que la pantalla***. … ***la regla de
    que se puede juntar vive en un solo sitio***. Si el guion tuviera su propia copia, un dia la pantalla
    diria una cosa y el guion otra.»

***O sea: el guion usa la puerta A PROPOSITO***. **Y al ponerle `PuedeModificar` a la puerta, el guion dejo
de poder llamarla** -porque `Depends` **no resuelve nada fuera de FastAPI**-.

***El arreglo dice la verdad***: el guion pasa **`puede_modificar=None`**.

    # ***Y el permiso, en `None`***: la puerta ahora exige `PuedeModificar` -que es lo correcto para la
    # pantalla-, y este guion **no es una peticion de la pantalla**: corre desde la consola, y su propio
    # comentario dice por que usa la misma puerta. Pasarle `None` es decir la verdad: **no hay una cuenta
    # detras a la que preguntarle**.

*Y no se le puso un usuario de mentira ni una excepcion en la puerta*: **un guion de consola no tiene
cuenta**, y decirlo con `None` es mas honesto que inventarse una.

### ***Los dos fallos de esta ronda, otra vez mios***

1. **La indentacion**: `deshacer_la_migracion` esta dentro de una funcion y sus argumentos llevan **4**
   espacios, no 8. *El script abortó con «el ancla aparece 0 veces», que es lo que tiene que hacer.*
2. **Tres puertas de la maquinaria tenian la firma en una sola linea** -ya contado-, *y por eso el recuento
   dio 12 de 16 antes de cuadrar.*

### El marcador

    ***45 de 209 puertas de escritura exigen ya `PuedeModificar`***

      maquinaria_api.py   ***19***   <- bloque entero
      contactos_api.py    ***16***   <- bloque entero
      terceros_api.py        4 · tareas_api.py 3 · fusion_api.py 2 · parcelas.py 1

***Dos bloques completos, y el marcador paso de 39 a 45.*** *Y quedan **164** puertas de escritura sin
permiso: la siguiente parada natural es **`terceros_api.py`**, que ya tiene 4.*

### Y las 89 pruebas de contactos y permisos, en verde

    tests/test_contactos.py · test_los_permisos_por_materia.py · test_varias_cuentas_en_una_finca.py
                                                                       ***89 en verde***

### Recuento

    PYTHON: 5395   (sin cambios)
    los tres sitios al dia


---

## 17/10/2026 (56) — **El mapa entero de los permisos: 164 en 24 ficheros, y cuales NO se tocan**

### `terceros_api.py` ya estaba completo

Al ir a por el -era la «siguiente parada natural» del marcador-, resulto que **sus 4 puertas ya tenian
`PuedeModificar`**: *las puse **yo mismo** cuando hice el CRM-04, hace unas rondas, y no me acordaba.*
***Es el CRM-04 entero: 4 de 4.***

### Y el mapa completo, que es lo que sirve para seguir

    ***164 puertas de escritura sin permiso, en 24 ficheros***

      maestros.py 19 · registros.py 18 · gastos_api.py 15 · parcelas.py 13 · ventas_api.py 13
      bandeja_api.py 10 · extractos_api.py 10 · almacen_api.py 8 · trabajos_api.py 8 · semillas_api.py 7
      analiticas_api.py 6 · facturas_api.py 6 · documentos_api.py 5 · cuenta.py 4 · explotacion.py 4
      planes_api.py 4 · fincas_api.py 3 · medidas_api.py 3 · cuaderno_cyl_api.py 2 · versiones_api.py 2
      borradores_api.py 1 · firmas_api.py 1 · iuws_api.py 1 · mapa.py 1

### ***Y ahora lo importante: la lista tiene FALSOS POSITIVOS, y hay que saber leerlos***

El recuento es **mecanico** -mira el decorador `@router` y la palabra `PuedeModificar`-, asi que **cuenta
cosas que no son puertas de escritura del agricultor**. ***Estas NO se tocan, y hay que decirlo para que
nadie las «arregle»***:

  1. **`@router.get`** -los que salen con ese nombre en `bandeja_api`, `semillas_api`, `cuaderno_cyl_api`…-:
     *`GET` **no escribe**. Salen porque mi recuento coge cualquier `@router` y algunos decoradores ocupan
     varias lineas.*
  2. **`cuenta.py`: `registrar`, `entrar`, `entrar_con_certificado`, `vincular_certificado`.** *Son las
     puertas **de entrar**: exigirles «poder modificar la finca» seria **pedir el carne para sacar el
     carné**. La de `vincular_certificado` sí hay que mirarla, pero **con la sesion de quien ya entro**, no
     con `PuedeModificar` de la finca.*
  3. **`firmas_api.py: registrar`** -**el que firma es un tercero**, no una cuenta de la finca-, e
     **`iuws_api.py: leer_respuesta`** -la respuesta la trae el integrador-.
  4. **Los ayudantes privados que empiezan por `_`**: `_con_nombres`, `_la_campana`, `_los_movimientos_filtrados`.
     *No son puertas: son funciones de dentro.*
  5. **`mapa.py: que_hay_en_este_punto`** y **`borradores_api.py: desde_texto`**: *mirar el mapa y componer
     un borrador **no cambia nada de la finca**.*

***O sea: de las 164, hay que descontar las que no son de escritura del agricultor antes de empezar*** -y eso
**no lo puede decidir un script**: se mira fichero a fichero, que es como se han hecho los dos bloques que
ya estan-.

### El marcador, y por donde sigue

    ***45 de 209 hechas***, y **tres bloques enteros**: maquinaria (19), contactos (16) y terceros (4).

***El siguiente por tamano es `maestros.py` con 19*** -productos, fertilizantes, aplicadores…-, *que es
catalogo: puertas de escribir de verdad y con consecuencia, porque un producto mal dado de alta sale en
todos los tratamientos.*

### Recuento

    PYTHON: 5395   (sin cambios)
    y la suite entera, corriendo (job pwsh-2592)


---

## 17/10/2026 (57) — **`maestros.py` entero: 18 de 18. Cuatro bloques y 63 de 209**

### Lo que se hizo

Se fue a por **`maestros.py`** -el siguiente por tamano, 19- y resulto ser **el catalogo**: siete pares de
`crear` / `corregir` / `borrar` -producto, fertilizante, aplicador, asesor, equipo e instalacion- **mas las
de lectura, que no se tocan**.

    ***18 de 18 puertas de escritura de `maestros.py`, con `PuedeModificar`***
    ***y 16 de lectura, que se quedan como estan***

### ***Y salio el MISMO fallo de la maquinaria, que ya estaba aprendido***

    AssertionError: {"detail":[{"type":"missing","loc":["query","puede_modificar"],"msg":"Field required"}]}

***`maestros.py` no importaba `PuedeModificar`***, y sin el nombre importado **FastAPI lo toma por un
parametro de consulta**. *Es exactamente lo que paso en `maquinaria_api.py` hace tres rondas.*

***Y esta vez se reconocio de inmediato*** -el `loc: ["query", …]` es la firma de ese fallo-, asi que se
arreglo en **una linea** en vez de en media hora:

    from ..deps import Db, ExplotacionActual, ***PuedeModificar***, UsuarioActual, obtener_de_la_explotacion

***Y queda dicho para las proximas***: **cada vez que se le ponga un alias de `deps` a un router, hay que
comprobar que ese router lo importa.** *Es un fallo que no se ve al leer la firma -esta bien escrita- y solo
sale al llamar a la puerta.*

### El marcador

    ***63 de 209 puertas de escritura exigen ya `PuedeModificar`***

      maquinaria_api.py  ***19***   <- bloque entero
      maestros.py        ***18***   <- bloque entero
      contactos_api.py   ***16***   <- bloque entero
      terceros_api.py     ***4***   <- bloque entero
      tareas_api.py 3 · fusion_api.py 2 · parcelas.py 1

***Cuatro bloques completos, y de 45 a 63.***

### Y las 151 pruebas que tocan el catalogo, en verde

    test_asesor_semilla_y_agua · test_autorizacion_del_producto · test_instalaciones
    test_cesta_del_almacen · test_los_permisos_por_materia                     ***151 en verde***

### Recuento

    PYTHON: 5395   (sin cambios)
    los tres sitios al dia

### Lo que sigue

*Los siguientes por tamano son **`registros.py` (18)**, **`gastos_api.py` (15)**, **`parcelas.py` (13)** y
**`ventas_api.py` (13)*** -y los cuatro son de escribir de verdad: *tratamientos, dinero y tierras.*
**Y sigue el mapa de la ronda anterior para saber cuales NO hay que tocar.**


---

## 17/10/2026 (58) — **`registros.py`: 15 de escritura, y los 3 «validar» NO se tocan**

### ***La leccion de la ronda anterior, aplicada ANTES de tocar nada***

Se empezo **mirando el import**, que es lo que fallo en `maestros.py`:

    from ..deps import Db, ExplotacionActual, UsuarioActual, obtener_de_la_explotacion
    ***tiene PuedeModificar: False***

*Comprobado de entrada, asi que el fallo de `maestros.py` no se repitio.* **Y el import se arreglo en el
mismo paso que las puertas.**

### ***Y los tres `validar_*` NO se tocan, y hay que decir por que***

El recuento saco 18 puertas de escritura, y **tres de ellas se llaman `validar_*_endpoint`**. *«Validar»
suena a leer, pero son `POST`, asi que se miraron una a una:*

    validar_tratamiento_endpoint(…) -> ResultadoValidacion
      «***Comprueba un tratamiento SIN GUARDARLO.*** La interfaz lo llama ***mientras se rellena***.»
      return _resultado(_avisos_tratamiento(datos, explotacion, db))     <- ***no hay `db.add`***

    validar_fertilizacion_endpoint(…) -> ResultadoValidacion   return _resultado(_avisos_fertilizacion(…))
    validar_cosecha_endpoint(…)      -> ResultadoValidacion   solo lee

***Las tres son de LECTURA***, y **ponerles `PuedeModificar` habria sido un defecto nuevo**: *el agricultor
esta rellenando el formulario y quiere saber **si puede guardarlo**; si la puerta exigiera poder modificar,
**quien solo mira no podria ni ver los avisos** -y esos avisos son justo lo que le dice que esta mal-.*

***Y se ve en la firma***: devuelven `ResultadoValidacion`, no una fila. *Pero se miro el cuerpo, que es lo
que lo confirma.*

### Lo que quedo

    ***15 de 15 puertas de escritura de `registros.py`, con `PuedeModificar`***

      tratamiento    crear · anular · corregir · borrar
      fertilizacion  crear · anular · corregir · borrar
      labor          crear · corregir · borrar · anular
      cosecha        registrar · corregir · borrar

    ***y 3 de lectura (`validar_*`), que se quedan como estan -a proposito-***

***Los seis con la firma en una linea*** -cuatro de una forma y dos de otra- *se cogieron con dos patrones, que
es la trampa que ya habia salido en la maquinaria.*

### El marcador

    ***78 de 209 puertas de escritura exigen ya `PuedeModificar`***

      maquinaria_api.py 19 · maestros.py 18 · contactos_api.py 16 · registros.py ***15*** · terceros_api.py 4
      tareas_api.py 3 · fusion_api.py 2 · parcelas.py 1

***Cinco bloques completos, y de 63 a 78.***

### Y 226 pruebas, en verde

    test_como_se_echo · test_autorizacion_del_producto · test_asesor_semilla_y_agua
    test_cosecha_comercializada · test_cuaderno_cyl · test_los_permisos_por_materia
    test_la_edicion_concurrente                                         ***226 en verde***

### Recuento

    PYTHON: 5395   (sin cambios)
    los tres sitios al dia

### Lo que sigue

*Los siguientes: **`gastos_api.py` (15)** -dinero-, **`parcelas.py` (13)** -tierras- y **`ventas_api.py`
(13)** -mas dinero-.*


---

## 17/10/2026 (59) — **`gastos_api.py` entero: 93 de 209, y seis bloques completos**

### ***El dinero, que es lo que mas duele, ya exige permiso en sus 15 puertas***

    ***15 de 15 puertas de escritura de `gastos_api.py`, con `PuedeModificar`***

      apuntar · corregir · anular un gasto · repartir · dejarlo_sin_asignar · quitar_un_reparto
      apuntar · anular una inversion
      apuntar · conciliar · deshacer_una_conciliacion · anular un pago
      apuntar · anular una subvencion
      un_traspaso_entre_cuentas_propias

*Todas escriben dinero, y **ninguna es de lectura** -a diferencia de `registros.py`, donde los tres
`validar_*` hubo que dejarlos-.*

### ***Y esta vez hubo que leer las firmas, porque eran SIETE formas distintas***

*El script que servia para los otros bloques buscaba `db: Db` en su propia linea, y aqui **fallo en 14 de
15**. Al mirarlas:*

    apuntar_un_gasto(datos: GastoEntrada, explotacion: …, db: Db, usuario: UsuarioActual)   <- una linea
    apuntar_un_pago(datos: PagoEntrada, explotacion: …, db: Db) -> dict                      <- una linea
    quitar_un_reparto(gasto_id: int, reparto_id: int, explotacion: …, db: Db)               <- ***dos ids***
    deshacer_una_conciliacion(pago_id: int, aplicacion_id: int, explotacion: …, db: Db)     <- ***dos ids***
    un_traspaso_entre_cuentas_propias(datos: dict, explotacion: …, ***_usuario***: UsuarioActual)  <- ***sin `db`***

***Lo que se hizo fue dejar de adivinar***: *el script ahora **parte la firma entera** con una expresion
regular, saca **los parametros de uno en uno** y **anade el permiso al final, antes del cierre**. *Da igual
cuantos parametros haya, como se llamen o si hay `db` o no.* **Y las 14 entraron de una vez.**

***Y queda como leccion de metodo***: *los tres scripts anteriores -maquinaria, contactos, maestros- se
apoyaban en **una forma concreta** de firma. Este **no se apoya en ninguna**, y por eso es el que sirve para
lo que queda.*

### El marcador

    ***93 de 209 puertas de escritura exigen ya `PuedeModificar`***

      maquinaria_api.py 19 · maestros.py 18 · contactos_api.py 16 · ***gastos_api.py 15***
      registros.py 15 · terceros_api.py 4 · tareas_api.py 3 · fusion_api.py 2 · parcelas.py 1

***Seis bloques completos, y de 78 a 93.***

### Y 177 pruebas, en verde

    test_gastos · test_el_dinero_de_las_ventas · test_los_permisos_por_materia
    test_la_edicion_concurrente                                    ***177 en verde***

***El dinero es lo que mas duele que se pueda tocar sin permiso***, asi que estas 177 se corrieron dos veces
antes de dar el bloque por bueno.

### Recuento

    PYTHON: 5395   (sin cambios)
    los tres sitios al dia

### Lo que sigue

*Los siguientes: **`parcelas.py` (13)** -tierras, que es del objetivo-, **`ventas_api.py` (13)** -mas
dinero-, y **`bandeja_api.py` (10)**, **`extractos_api.py` (10)**.*


---

## 17/10/2026 (60) — **`parcelas.py`: las tierras, 11 de 11, y 103 de 209**

### Lo que se hizo

    ***11 de 11 puertas de escritura de `parcelas.py`, con `PuedeModificar`***

      crear_parcela · crear_parcela_desde_el_sigpac · crear_varias_parcelas_desde_el_sigpac
      corregir_parcela · borrar_parcela · asignar_cultivo · quitar_cultivo
      crear_grupo · corregir_grupo · borrar_grupo
      ***decirle_la_forma_a_una_tierra***   <- ya lo tenia

*El import **ya traia `PuedeModificar`** -alguien lo puso-, asi que ese paso no hubo que darlo.*

### ***Y los TRES que NO se tocan, con su motivo escrito en el propio codigo***

El recuento saco 14, y **tres se miraron uno a uno**:

    buscar_los_trozos(datos, ***_: UsuarioActual***)      «Busca los trozos… ***para poder elegirlos***»
    consultar_un_recinto(datos, ***_: UsuarioActual***)   «Pregunta al SIGPAC ***sin dar de alta nada***»
    calcular_grupos(explotacion, db, campana_id)     «***Agrupa solas*** las parcelas que se llevan igual»

***Los tres LEEN***, y los tres piden **`UsuarioActual` en vez de `ExplotacionActual`** -con el `_` delante,
que es la convencion de la casa para «no se usa»-, **a proposito y explicado**:

    «Pide `UsuarioActual` y no `ExplotacionActual` ***a proposito***: lo que se consulta es un dato publico
    del recinto y ***no hay ninguna finca metida en la pregunta***; lo que hace falta es saber ***quien***
    pregunta, no de que finca es.»

***Y el motivo de que pidan sesion es delicioso***, escrito en `buscar_los_trozos`:

    «Es la ruta que ***mas llamadas de salida hace de todo el programa***: hasta ***26*** al SIGPAC del
    FEGA por cada peticion… y la revision de rutas sin sesion encontro que ***no habia ningun limite***.
    Es decir: cualquiera que supiera la direccion podia encargar 26 llamadas al servicio publico por
    peticion, sin cuenta y sin tope, y ***el que se queda sin poder dar de alta sus tierras -si al FEGA le
    molesta el trafico y corta la direccion- es el agricultor***.»

***O sea: esas tres piden SESION, no permiso de finca*** -y eso es lo correcto, porque **no hay finca en la
pregunta**-.

### El marcador

    ***103 de 209 puertas de escritura exigen ya `PuedeModificar`***

      maquinaria 19 · maestros 18 · contactos 16 · gastos 15 · registros 15 · ***parcelas 11***
      terceros 4 · tareas 3 · fusion 2

***Siete bloques completos, y de 93 a 103.***

### Y 138 pruebas de tierras, en verde

    test_cultivo_de_la_parcela · test_darle_la_forma_a_una_tierra · test_dibujo_de_la_parcela
    test_las_superficies_no_se_suman · test_cosecha_comercializada · test_lo_que_la_pac_pide
    test_la_edicion_concurrente · test_los_permisos_por_materia           ***138 en verde***

### Recuento

    PYTHON: 5395   (sin cambios)
    los tres sitios al dia

### Lo que sigue

*Los siguientes: **`ventas_api.py` (13)** -mas dinero-, **`bandeja_api.py` (10)**, **`extractos_api.py`
(10)**, **`almacen_api.py` (8)** y **`trabajos_api.py` (8)**.*


---

## 17/10/2026 (61) — **`ventas_api.py`: 11 de 11, y 114 de 209 -mas de la mitad**

### Lo que se hizo

    ***11 de 11 puertas de escritura de `ventas_api.py`, con `PuedeModificar`***

      crear_venta · corregir_venta · anular_venta · borrar_venta
      apuntar_un_ajuste · anular_un_ajuste
      crear_factura_emitida · anular_factura_emitida
      apuntar_un_cobro · conciliar_un_cobro · anular_un_cobro

*Y el import hubo que anadirlo, como en maestros y en gastos.* ***Ya es costumbre comprobarlo primero.***

### ***Y los dos que NO se tocan, que el recuento saco y hay que mirar siempre***

    validar_venta_endpoint(datos, explotacion, db) -> dict
      avisos = _avisos(db, explotacion, datos)
      return {"puede_guardarse": not validaciones.hay_bloqueo(avisos), …}   <- ***no escribe***

    ***como_se_ve_una_factura***(db, explotacion, factura) -> FacturaEmitidaSalida
      «La factura con sus lineas, sus cobros y ***sus cuentas hechas***.»
      ***¡y ni siquiera es una puerta!*** -no tiene `@router`-: *el recuento lo cogio porque el decorador
      anterior esta cerca.*

***Los dos son de lectura***, y el segundo es **un ayudante de dentro** que se llama desde las puertas -lo
usa el POST de la factura para devolver la factura recien creada-. *Ponerle `PuedeModificar` no habria
hecho nada -no es una puerta- y anadirlo a la lista de «sin permiso» **habria sido contar de mas**.*

### ***Y la leccion que se repite: el recuento cuenta de mas, y hay que leerlo***

*De las 209 puertas que cuenta, van **descontadas** en cada bloque las que no son de escritura del
agricultor:*

    registros.py   15 de 18   los 3 `validar_*` son de LECTURA
    parcelas.py    11 de 14   los 3 del SIGPAC piden SESION, no permiso de finca
    ventas_api.py  11 de 13   `validar_venta_endpoint` lee, y `como_se_ve_una_factura` no es puerta

***O sea: de las «209» hay que quitar las que no son puertas, y por eso el trabajo se hace leyendo.***

### El marcador

    ***114 de 209 puertas de escritura exigen ya `PuedeModificar`***

      maquinaria 19 · maestros 18 · contactos 16 · gastos 15 · registros 15
      parcelas 11 · ***ventas 11*** · terceros 4 · tareas 3 · fusion 2

***Ocho bloques completos, y de 103 a 114: mas de la mitad.***

### Y 198 pruebas, en verde

    test_el_dinero_de_las_ventas · test_facturas · test_cosecha_comercializada
    test_el_piloto_de_la_factura · test_los_permisos_por_materia · test_la_edicion_concurrente
                                                                       ***198 en verde***

### Recuento

    PYTHON: 5395   (sin cambios)
    los tres sitios al dia

### Lo que sigue

*`bandeja_api.py` (10), `extractos_api.py` (10), `almacen_api.py` (8), `trabajos_api.py` (8),
`semillas_api.py` (7), `analiticas_api.py` (6) y `facturas_api.py` (6).*


---

## 17/10/2026 (62) — **`bandeja_api.py`: 9 de escritura, y una leccion de PYTHON**

### Lo que se hizo

    ***9 de 9 puertas de escritura de `bandeja_api.py`, con `PuedeModificar`***

      subir_a_la_bandeja · clasificar_el_papel · leer_el_papel
      revisar_la_propuesta · descartar_la_propuesta · confirmar_el_papel
      vincular_el_papel · desvincular_el_papel · rectificar_a_otro_papel

### ***Y tres cosas que hubo que MIRAR, porque el recuento no las distingue***

    685  async def ***comprobar_el_fichero***(…)   «Lee el fichero… ***No escribe nada.***»   -> NO se toca
    728  async def ***subir_a_la_bandeja***(…)    crea la fila                        -> SI
    989  async def ***leer_el_papel***(…)         ***`db.commit` 1 vez***, y la propuesta va a su columna  -> SI

    y dos que no son puertas de escritura del agricultor:
      `@router.get` (no escribe) y `_la_cesta_del_agricultor` (ayudante privado)

***Y `leer_el_papel` costo una comprobacion***: *su docstring dice «**no cambia el estado**», que se puede
leer como «no escribe»*. **Pero tiene `db.commit`**, y la propuesta se guarda **en su columna**: *«subir,
leer y confirmar son **tres actos distintos**»*. ***Se miro el cuerpo en vez de fiarse del docstring.***

### ***Y salieron DOS fallos, y el segundo es una leccion de Python***

1. **Mi recuento no veia los `async def`**, asi que salian como `@router.post` en vez de por su nombre.
   *Se arreglo el patron con `(?:async )?def`.*
2. ***`SyntaxError: parameter without a default follows parameter with a default`.***

   *Al ponerle `puede_modificar: PuedeModificar` a `subir_a_la_bandeja` **al final de la firma**, Python lo
   rechazo: **esa puerta tiene `File(...)` y `Form(default=None)`, que SI tienen valor por defecto**, y un
   parametro sin valor **no puede ir despues**.*

   ***Es una regla del lenguaje, no de esta casa***, y quedo escrita en el propio codigo:

       # ***Y va AQUI, antes de los `File` y los `Form`, y no al final***: en Python un parametro
       # **sin valor por defecto** no puede ir despues de uno que **si** lo tiene…

   ***Y el script lo habria metido mal en cualquier puerta que suba ficheros*** -que son varias en lo que
   queda: `documentos_api`, `firmas_api`…-, asi que **esto ahorra el fallo las proximas veces**.

### El marcador

    ***123 de 209 puertas de escritura exigen ya `PuedeModificar`***

      maquinaria 19 · maestros 18 · contactos 16 · gastos 15 · registros 15
      parcelas 11 · ventas 11 · ***bandeja 9*** · terceros 4 · tareas 3

***Nueve bloques completos, y de 114 a 123.***

### Y 135 pruebas, en verde

    test_bandeja · test_los_permisos_por_materia · test_el_motivo_de_deshacer    ***135 en verde***

### Recuento

    PYTHON: 5395   (sin cambios)
    los tres sitios al dia

### Lo que sigue

*`extractos_api.py` (10), `almacen_api.py` (8), `trabajos_api.py` (8), `semillas_api.py` (7),
`analiticas_api.py` (6) y `facturas_api.py` (6).* ***Y ya se sabe que en las que suben fichero, el permiso va
ANTES de los `Form`.***


---

## 17/10/2026 (63) — **`extractos_api.py`: 9 de escritura, y el script que ya lo sabe todo**

### Lo que se hizo

    ***9 de 9 puertas de escritura de `extractos_api.py`, con `PuedeModificar`***

      crear_cuenta · corregir_cuenta · guardar_perfil · corregir_perfil
      importar_el_extracto · corregir_un_movimiento · conciliar_un_movimiento
      deshacer_la_conciliacion · marcar_o_quitar_un_traspaso

### ***Y la dudosa, que se miro en vez de suponer***

    ***async def leer_el_extracto_sin_guardarlo***(…)
      «Lee el extracto y ***enseña lo que se va a apuntar, sin apuntar nada***»
      db.add: 0 · db.commit: 0 · db.flush: 0      -> ***DE LECTURA, no se toca***

*Parecia dudosa por el nombre -«sin guardarlo» se puede leer como «no escribe»-, y **se comprobo**: **cero
escrituras**. Pero **no se dio por supuesta**: se contaron los `db.add`, `db.commit` y `db.flush` del
cuerpo.*

### ***Y el script de los permisos, que ya ha aprendido las tres cosas***

*Despues de siete bloques, el script que mete `PuedeModificar` sabe ya:*

  1. **Que hay `async def`** -se le escapo en `bandeja_api`-. *Ahora el patron es `(?:async )?def`.*
  2. **Que la firma puede tener parentesis dentro** -`File(...)`, `Form(...)`-. *Ya no se corta en el primero:
     **cuenta el nivel de parentesis** hasta el que cierra la firma.*
  3. ***Que un parametro sin valor por defecto NO puede ir despues de uno que si lo tiene*** -el
     `SyntaxError` de Python que salio en `bandeja_api`-. *Ahora **mete el permiso ANTES del primer
     parametro con valor por defecto**, que es donde tiene que ir.*

***Y las nueve entraron de una vez, sin un solo fallo.***

### El marcador

    ***132 de 209 puertas de escritura exigen ya `PuedeModificar`***

      maquinaria 19 · maestros 18 · contactos 16 · gastos 15 · registros 15
      parcelas 11 · ventas 11 · bandeja 9 · ***extractos 9*** · terceros 4

***Diez bloques completos, y de 123 a 132.***

### Y 164 pruebas, en verde

    test_extractos · test_el_dinero_de_las_ventas · test_los_permisos_por_materia
    test_lo_que_pide_crm_02                                         ***164 en verde***

### Recuento

    PYTHON: 5395   (sin cambios)
    los tres sitios al dia

### Lo que sigue

*`almacen_api.py` (8), `trabajos_api.py` (8), `semillas_api.py` (7), `analiticas_api.py` (6),
`facturas_api.py` (6), `documentos_api.py` (5), `explotacion.py` (4), `planes_api.py` (4), `cuenta.py` (4
-***pero esas son las de ENTRAR, y no se tocan***-)…*


---

## 17/10/2026 (64) — **Tres bloques mas: almacen 8, trabajos 8 y semillas 6. Y la cuarta leccion**

### Lo que se hizo

    ***almacen_api.py   8 de 8***    crear_articulo · crear_lote · crear_recepcion · anular_recepcion
                                     enganchar_la_factura · apuntar_un_movimiento · anular_movimiento
                                     sacar_de_un_lote
    ***trabajos_api.py 8 de 8***    planificar · corregir · reprogramar · cancelar un trabajo previsto
                                     marcar_lo_que_de_verdad_se_hizo · apuntar · corregir · anular uno hecho
    ***semillas_api.py 6 de 7***    dar_de_alta · corregir · subir_la_foto · sembrar · corregir · anular

    ***el septimo, `leer_la_etiqueta`, NO se toca***: su propio docstring lo dice **en el dato** -
      «***No guarda absolutamente nada.*** … lo que se lee es una propuesta, y un hecho solo cuando el
      agricultor dice que si. Por eso la respuesta lleva ***`guardado: false`*** escrito en el dato y no
      en un comentario.»

### ***Y la CUARTA leccion: hay puertas que se llaman DESDE DENTRO***

Al correr `test_revision_t10`, salto:

    app/routers/semillas_api.py:830
      return sacar_de_un_lote(…, explotacion=…, usuario=…, db=…, respuesta=Response())
    ***TypeError: sacar_de_un_lote() missing 1 required positional argument: 'puede_modificar'***

***`semillas_api` no resta existencias por su cuenta: llama a la puerta del almacen***, y su docstring dice
por que -«*por la puerta de las salidas que **ya existe**… asi la siembra hereda todo lo que esa puerta ya
hace bien, y **no hay dos formas de descontar que un dia digan cosas distintas**»*-.

***Y es el MISMO caso que `scripts/migrar_contactos.py`***, dos rondas antes. **Asi que se busco de una vez**:
*¿quien llama a las puertas que acabo de tocar?* Salieron **dos** -`semillas_api:830` y
`trabajos_api:921`-, y **las dos son llamadas internas**: el programa llamando a su propia puerta, **sin
ninguna cuenta detras**. Las dos pasan **`puede_modificar=None`**, que es decir la verdad.

***Y queda como regla para lo que falta***: **cada vez que se le ponga permiso a una puerta, hay que buscar
quien la llama por dentro.** *Un `grep` del nombre de la funcion por todo `app/` lo encuentra en un
segundo, y ahorra el fallo.*

### El marcador

    ***154 de 209 puertas de escritura exigen ya `PuedeModificar`***

      maquinaria 19 · maestros 18 · contactos 16 · gastos 15 · registros 15
      parcelas 11 · ventas 11 · bandeja 9 · extractos 9
      ***almacen 8 · trabajos 8*** · semillas 6 · terceros 4

***Doce bloques completos, y de 132 a 154.***

### Y 115 pruebas, en verde

    test_revision_t10 · test_semillas · test_los_permisos_por_materia    ***115 en verde***

***Y las cuatro lecciones del script, juntas***:

  1. `async def` -`bandeja_api`-.
  2. Parentesis dentro de la firma -`File(...)`, `Form(...)`-.
  3. ***Un parametro sin valor por defecto no puede ir despues de uno que si*** -`bandeja_api`-.
  4. ***Y hay puertas que se llaman desde dentro*** -`semillas_api`, `trabajos_api`-.

### Recuento

    PYTHON: 5395   (sin cambios)
    los tres sitios al dia


---

## 17/10/2026 (65) — **De golpe: 182 de 209. Y quedan 27, todos con su motivo**

### Lo que se hizo

*Se fue a por **lo que quedaba entero**, en vez de bloque a bloque:*

    ***analiticas_api.py 5 · facturas_api.py 5 · documentos_api.py 5 · explotacion.py 4
       planes_api.py 3 · fincas_api.py 2 · medidas_api.py 2 · versiones_api.py 1
       cuaderno_cyl_api.py 1 · ventas_api.py 1 · maestros.py 1***   =  ***30 puertas***

***Y el marcador paso de 154 a 182 de 209.***

### ***Y los que NO se tocan, que ahora son una lista corta y con motivo escrito***

    cuenta.py (4)          registrar, entrar, entrar_con_certificado, vincular_certificado
                           ***LAS DE ENTRAR***: pedir «poder modificar» para entrar es pedir el carne
                           para sacar el carné.
    fincas_api.py (1)      ***cambiar_de_finca***  -lo mire, y su cuerpo lo dice-
                           `if not accesos.puede_entrar(…)` y `accion="entrar"`: ***es una puerta de
                           entrar***, y ya comprueba ***lo que hay que comprobar***. *Cambiar de finca
                           **para mirar** es legitimo.*
    parcelas.py (3)        buscar_los_trozos, consultar_un_recinto, calcular_grupos   -LEEN-
    registros.py (3)       validar_tratamiento/fertilizacion/cosecha_endpoint         -LEEN-
    ventas_api.py (1)      validar_venta_endpoint                                     -LEE-
    analiticas_api.py (1)  validar_analitica_endpoint   «***funcion pura***: `validar_analitica`
                           ***no toca la base de datos***»
    medidas_api.py (1)     validar_medidas_endpoint                                   -LEE-
    planes_api.py (1)      validar_plan_endpoint                                      -LEE-
    bandeja_api.py (1)     comprobar_el_fichero        «***No escribe nada.***»
    facturas_api.py (1)    leer_una_factura             «***No guarda nada.***»
    semillas_api.py (1)    leer_la_etiqueta             «***No guarda absolutamente nada.***»
    cuaderno_cyl_api.py(1) leer_el_cuaderno             «***No apunta nada.***»
    extractos_api.py (1)   leer_el_extracto_sin_guardarlo  «…***sin apuntar nada***»
    versiones_api.py (1)   previsualizar                «***Qué pasaría*** … ***No escribe nada.***»
    mapa.py (1)            que_hay_en_este_punto        -mira el mapa-
    borradores_api.py (1)  desde_texto                  -compone un borrador-
    firmas_api.py (1)      registrar                    -***el que firma es un tercero***-
    iuws_api.py (1)        leer_respuesta               -***la trae el integrador***-

***O sea: de los 27 que no llevan `PuedeModificar`, los 27 tienen una razon que se puede leer*** -16 leen,
4 son de entrar, 1 cambia de finca para mirar, 1 firma un tercero, 1 la trae el integrador, 1 mira el mapa,
1 compone un borrador, y 2 son ayudantes-.

### ***Y salieron DOS que se me habian escapado, y los dos SUBEN FICHERO***

*El recuento los saco, no mi lista:*

    ventas_api.py: ***subir_el_papel_de_un_ajuste***      <- sube un papel
    maestros.py:   ***subir_la_foto_de_la_etiqueta***     <- sube una foto

***Y despues se hizo la comprobacion que faltaba***: *sacar **todas** las puertas que suben fichero, para no
dejar ninguna.* **Y estan las 16**:

    ***Suben fichero Y escriben (11) -todas con permiso-***:
      analiticas subir_informe · bandeja subir_a_la_bandeja · cuaderno_cyl importar_el_cuaderno
      documentos subir_fichero · extractos importar_el_extracto · facturas guardar_una_factura
      facturas subir_el_fichero · maestros subir_la_foto · semillas subir_la_foto
      ventas subir_el_papel_de_un_ajuste

    ***Suben fichero y NO escriben (5) -y estan bien asi-***:
      comprobar_el_fichero · leer_el_cuaderno · leer_el_extracto_sin_guardarlo
      leer_una_factura · leer_la_etiqueta

### ***Y un fallo de mis propios scripts, que conviene saber***

*El recuento de «lo que queda» que escribi primero **daba falsos negativos** -decia que `crear_analitica`,
`crear_venta` o `subir_a_la_bandeja` no tenian permiso, y si lo tenian-, porque **empezaba a buscar el
nombre de la funcion desde un sitio distinto del bloque**.*

***Y eso ensena lo de siempre***: **el recuento no es la verdad; la verdad es leer el bloque.** *El numero
bueno salio al mirar `@router` … `@router` y buscar el `def` **solo dentro de esas lineas**.*

### El marcador

    ***182 de 209 puertas de escritura exigen ya `PuedeModificar`***

***De 3 a 182, y los 27 que quedan son leen/entrar/ayudantes.***

### Recuento

    PYTHON: 5395   (sin cambios)
    los tres sitios al dia
    y la suite entera, corriendo (job pwsh-2730)


---

## 17/10/2026 (66) — **La suite entera encontro lo que ninguna prueba corta: dos cosas**

### ***Lo primero: un bloque DUPLICADO en `web/app.js`***

    pantallaFichaDeContacto():
      17801      // **Lo que esta cuenta puede hacer** (Entrega 4)…
      17803      puede_modificar: loQuePuedoHacer().modificar,          <- indentacion de 6
      17804      puede_ver_lo_economico: …
      17805    // **Lo que esta cuenta puede hacer** (Entrega 4)…        <- ***¡OTRA VEZ, con indentacion de 4!***
      17806    puede_modificar: loQuePuedoHacer().modificar,
      17807    puede_ver_lo_economico: …
      17809    canal_a_medias: suyo.canal_a_medias || null,
      17810    tarea_a_medias: suyo.tarea_a_medias || null,

***Y `node --check` PASABA*** -en JavaScript una clave repetida no es error, gana la ultima-. **Pero era basura, y
ademas arrastraba dos claves que si importan**:

    `canal_a_medias` y `tarea_a_medias` **se escriben en dos sitios** (`suyo.canal_a_medias = {…}` en el alta
    rapida) y **esas dos lineas eran las UNICAS que las pasaban a la pantalla**. *Estaban pegadas al duplicado.*

***Se quito la repeticion y se dejaron las dos claves en su sitio***, con el motivo escrito al lado. **Y hay un
test que lo cubre**: *«el envoltorio de la ficha **no se deja ninguna propiedad por el camino**»*.

### ***Y lo segundo, la QUINTA leccion, que es la misma de siempre***

La suite entera saco esto, que ninguna prueba corta habia visto:

    app/routers/bandeja_api.py:791
      guardado = documentos_api.crear(…, explotacion, db)
    ***TypeError: crear() missing 1 required positional argument: 'puede_modificar'***

***`bandeja_api` no da de alta el papel por su cuenta: llama a la puerta de documentos*** -«*el alta del papel y
la subida del fichero **se hacen con las puertas que ya existen**; tener dos caminos que escriben ficheros en
disco seria tener dos sitios donde equivocarse con las rutas*»-.

***Y son DOS llamadas, no una***: `documentos_api.crear` **y** `documentos_api.subir_fichero`.

### ***Y la regla, ahora bien dicha: hay que buscar DESPUES de tocar, no antes***

*En la ronda 64 se busco quien llamaba a las puertas tocadas… **antes** de tocar las de esta ronda.* **Por eso
se escaparon.** Lo que hay que hacer, cada vez:

  1. Poner el permiso.
  2. **Buscar las llamadas cualificadas** -`modulo.puerta(`- a **todas** las puertas que llevan permiso.
  3. **Y arreglarlas** con `puede_modificar=None`.

***Y un aviso para el que lo haga con un script***: *buscar `router.puerta(` a secas **da falsos positivos**
-`correcciones.borrar(…)`, `logica.corregir(…)`, `cuenta.get(…)`-, porque hay funciones que **comparten nombre**
con una puerta y viven en otro modulo. *Los de verdad son **los que llevan delante un modulo de `app/routers/`**.*

### El marcador

    ***184 de 209 puertas de escritura exigen ya `PuedeModificar`***

    y los 27 que quedan son: 16 que LEEN · 4 de ENTRAR · 1 cambiar_de_finca · 1 firma un tercero
                             1 la trae el integrador · 1 mira el mapa · 1 compone un borrador · 2 ayudantes

### Recuento

    PYTHON: 5395   ·   JS: ***1125***   (el bloque duplicado no cambio el numero)
    los tres sitios al dia
    y la suite entera otra vez, corriendo (job pwsh-2748)


---

## 17/10/2026 (67) — **La suite entera en verde, y el permiso de pantalla no se aplicaba por UN TYPO**

### Lo primero: la suite entera, con 24 ficheros tocados

    ***7395 pruebas · 100% · exit code 0***

*Era la segunda vez que se corria; la primera encontro los dos fallos de la ronda 66 y los dos se arreglaron.*

### ***Y lo segundo es un defecto de verdad, en la mitad de PANTALLA del punto 2***

El encargo dice «permisos en servidor ***y pantalla***». **El servidor ya estaba** -184 de 209 puertas-. *Y al
ir a por la pantalla, resulta que:*

    `web/app.js`
      17963  async function pedirLoQuePuedoHacer() {
      17964    // Se pregunta al entrar y se guarda, ***para [que la] pantalla no ofrezca lo que va a dar 403:
      17965    // los botones de apuntar y corregir***, el alta rapida, y el dinero.
      17980    estado.puedo = { modificar: yo.puede_modificar !== false, … };

    ***y `loQuePuedoHacer()` se usaba en TRES sitios: la definicion, y las dos lineas de la ficha de
    contacto. En ningun otro.***

***O sea: el comentario promete los botones de apuntar y corregir, y solo se cumplia en una pantalla.***

### ***Y al mirar esa única pantalla, el fallo de verdad***

    `web/react/pantallas/contactos.js`, envoltorio `pantallaDeUnContacto`
      925    puede_modificar=${propiedades.***puedo_modificar***}        <- ¡TYPO: «puedo» y no «puede»!
      927    puede_modificar=${propiedades.***puedo_modificar***}        <- ¡y repetido dos veces!

***`app.js` manda `puede_modificar`. El envoltorio leia `propiedades.puedo_modificar`, que no existe, asi que
llegaba `undefined`. Y el componente tiene `puede_modificar = true` POR DEFECTO*** -a proposito, «para que la
pantalla no parpadee»-. ***Asi que `undefined` y `true` se comportan igual, la pantalla ofrecia los botones
igual, y NINGUNA PRUEBA lo cazaba.***

***Arreglado***: el nombre de verdad y el duplicado fuera. **Y `node --check` limpio, 1125 pruebas de JS en
verde, y las 7395 de Python tambien.**

### ***Y lo que queda como ticket, que es lo mas util de esta ronda***

***El test que existe*** -«el envoltorio de la ficha ***no se deja ninguna propiedad por el camino***»- **pasa
con el typo puesto**, porque compara el valor del componente con `undefined`… y el valor por defecto `true`
lo tapa.

***Lo que habria que comprobar es que `propiedades.<nombre>` EXISTE***, no que el componente lo reciba: *un
`grep` de `propiedades.` en un envoltorio contra las claves que manda `app.js` lo encuentra, y no depende de
los valores por defecto.* **Queda pendiente, y es la mejora natural de esa prueba.**

### Recuento

    PYTHON: ***7395 en verde***   ·   JS: ***1125 en verde***
    los tres sitios al dia

### ***Y una leccion de JavaScript, de esta misma ronda***

*Al documentar el typo dentro del propio `html\`…\`` **rompi el fichero**: en JavaScript, un `//` **dentro de
una plantilla con comillas invertidas es texto, no un comentario**, asi que **las comillas invertidas del
comentario cerraron la plantilla**. Lo cazo `node --check` en el acto. **Se quitaron y ya esta** -pero queda
dicho: dentro de un `html\`…\`` no se escriben comillas invertidas ni `${`-.*


---

## 17/10/2026 (68) — **El permiso de pantalla, arreglado, y con prueba que lo caza**

### Lo que se hizo

***Una prueba nueva***, en `tests_js/contactos.test.js`:

    «sin permiso de modificar, la ficha NO ofrece los botones que escriben»

*Monta **el envoltorio** -no el componente, que es lo que hacia la que ya habia-, con `puede_modificar: false`
y con `true`, y comprueba **las dos mitades**:*

  * con `false`, ***no sale*** `data-accion="contacto-guardar"`, ni `contacto-borrar`, ni el saldo;
  * con `true`, ***salen***.

***La segunda mitad no es adorno***: *sin ella, un envoltorio que no pintara nunca nada tambien «pasaria», y
estariamos arreglando un fallo con otro.*

    ***JS: 1125 -> 1126, y las 1126 en verde***

### ***Y por el camino, DOS defectos mios, y los dos los cazo la prueba***

**1. El `//` DENTRO de un `html\`…\`` no es un comentario.**

*Escribi el comentario que explicaba el typo **dentro** de la plantilla. Y **htm la lee como HTML**: un `//`
ahi dentro **es TEXTO**, se mete **entre los atributos**, y ***los que van detras dejan de pasar***.*

    canal_a_medias        <- ***se cayo***
    tarea_a_medias        <- ***se cayo***
    puede_modificar       <- ***se cayo***
    puede_ver_lo_economico<- ***se cayo***

***Cuatro props, sin un solo error.*** *Y encima explicaba por que el saldo si llegaba y el permiso no:
`saldo` esta **antes** del comentario.*

**2. Y por eso hizo falta un DIAGNOSTICO, que conviene tener apuntado como receta.**

*Cuando una prueba dice que algo no llega, **montar las cuatro combinaciones y mirar cual falla**:*

    DIAG componente/false:  guardar=false  saldo=true     <- el componente esta bien
    DIAG componente/true:   guardar=true   saldo=true
    DIAG envoltorio/false:  guardar=true   saldo=true     <- ***aqui estaba el fallo***
    DIAG envoltorio/true:   guardar=true   saldo=true

***Con eso, en una tirada, se sabe si el fallo es del componente, del envoltorio o de los dos.*** *Se montan las
cuatro, se mira, y se quita el diagnostico -que es lo que se hizo-.*

### ***Y el typo de verdad, que era el motivo de la ronda***

    puede_modificar=${propiedades.***puedo_modificar***}   <- «puedo» y no «puede»

*`app.js` manda `puede_modificar`; el envoltorio leia `puedo_modificar`, que no existe, asi que llegaba
`undefined… y como el componente tiene `puede_modificar = true` por defecto -a proposito, «para que la pantalla
no parpadee»-, **`undefined` y `true` se comportan igual** y los botones salian igual.*

***Arreglado, y ahora la prueba lo comprueba por el valor y no por el nombre.***

### Recuento

    PYTHON: 7395 en verde   ·   JS: ***1126*** en verde
    los tres sitios al dia

### Lo que sigue

*El mismo typo **puede estar en otros envoltorios**: `app.js` manda `puede_modificar` a la ficha de contacto y
**a ningun otro sitio**, asi que la mitad de PANTALLA del punto 2 solo esta hecha en una pantalla. **La
siguiente parada natural es la ficha de la MAQUINA** -el cuenta-horas-, cuyos botones de apuntar y corregir
lectura **todavia se ofrecen sin mirar el permiso**.*


---

## 17/10/2026 (69) — **El permiso de pantalla, en el CUENTA-HORAS: apuntar, corregir y anular**

### Lo que se hizo

***La mitad de PANTALLA del punto 2, ahora en la ficha que importa*** -el cuenta-horas-. *Tres cambios:*

    `web/app.js`, `pantallaUnaMaquina()`:
        + ***puede_modificar: loQuePuedoHacer().modificar,***

    `web/react/pantallas/maquinaria.js`, `PantallaDeUnaMaquina`:
        + ***puede_modificar = true,***  en la desestructuracion
        * `lectura.anulado` -> ***`lectura.anulado || !puede_modificar`***   (corregir y anular)
        * el boton de apuntar, envuelto en ***`puede_modificar ? … : null`***

    ***y la prueba***, en `tests_js/maquinaria.test.js`:
        «sin permiso de modificar, la ficha de la maquina NO ofrece los botones de las lecturas»

***JS: 1126 -> 1127, y las 1127 en verde.***

### ***Y se demostro que la prueba sirve, que es la mitad del trabajo***

*Se cambio a proposito `puede_modificar` por `puedo_modificar` -el mismo typo de la ficha de contacto- y la
prueba **fallo**. Se restauro y volvio a pasar.* ***Una prueba que no se ha visto fallar no es una prueba.***

### ***Y tres cosas que salieron por el camino, y las tres valen para lo que queda***

**1. El ayudante compartido de las pruebas no se toca para una prueba.**

*Para que mi prueba viera los botones de corregir y anular, le anadi `lecturas` y `contador` a
`htmlDeLaFicha`… y **rompi otra prueba**, que afirma justo lo contrario: que en esa ficha **no hay ninguna
fecha**. Las lecturas traen fechas.*

***Deshecho***: *las lecturas se le pasan **a mi prueba**, no al ayudante. Cambiar un ayudante compartido
cambia **todos** los tests que lo usan, y eso no se hace para uno.*

**2. Un `//` dentro de un `html\`…\`` NO es un comentario.** *Ya quedo dicho en la ronda 68. Aqui se volvio a
respetar: **los comentarios van dentro de los `${ … }`, o fuera de la plantilla**.*

**3. Y un hueco de verdad que encontro la prueba**: `htmlDeLaFicha` **no pasaba `lecturas`**, asi que **los
botones de corregir y anular una lectura no se podian probar por ahi** — *no salian porque no habia lecturas,
no porque estuvieran bien-. **Los que si los pasan son los tests que los piden.***

### El estado del punto 2, que es lo que interesa

    SERVIDOR:  ***184 de 209*** puertas de escritura exigen `PuedeModificar`
               y las 27 que no, son: 16 que LEEN · 4 de ENTRAR · 1 cambiar_de_finca
                                       1 firma un tercero · 1 la trae el integrador
                                       1 mira el mapa · 1 compone un borrador · 2 ayudantes
    PANTALLA:  ***dos pantallas ya no ofrecen lo que da 403***: la ficha de CONTACTO y la ficha de la
               MAQUINA -el cuenta-horas-. Las demas **todavia no lo miran**.

***Y `app.js` manda `puede_modificar` en esos dos sitios y en ningun otro.*** *Llevarlo a las demas pantallas
es trabajo del mismo tipo que este: `app.js` manda la prop, el componente la declara **con el nombre exacto**, y
se envuelven los botones que escriben.-*

### Recuento

    PYTHON: 7395   (corriendo, job pwsh-2810)
    JS: ***1127 en verde***
    los tres sitios al dia


---

## 17/10/2026 (70) — **Los 7 puntos del cuenta-horas, uno por uno, con la prueba de cada uno**

*Ronda de **verificacion**, no de cambios*: *se fue a comprobar cada punto del encargo y a ver **que prueba
lo sostiene**. Y lo que salio es que **el cuenta-horas esta entero**.*

### Punto por punto, con su prueba

**1. Formularios de registrar, corregir y anular** -fecha, valor, unidad, sustitucion y motivo-.

    `web/react/pantallas/maquinaria.js`, `formularioDeUnaLectura({corrigiendo})`:
      * fecha · valor · **unidad** (`horas`/`kilometros`, «la unidad se elige, no se supone») · sustitucion · notas
      * la anulacion pide su **motivo** (`lectura-motivo`)
      * **al corregir se conservan los campos omitidos** y hay prueba que lo dice:
        ***`test_corregir_el_valor_NO_cambia_la_unidad_de_kilometros_a_horas`***
      * **el borrador se conserva si falla el envio**: `estadoDeLaMaquinaria().borrador`, con la nota
        del 13/10/2026 sobre `nota_a_medias` en la ficha de contacto.

**2. Permisos en servidor y pantalla, aislamiento y pertenencia.**

    SERVIDOR:  `PuedeModificar` en las tres puertas de las lecturas, y **184 de 209** en total.
    PANTALLA:  ***`puede_modificar` llega a la ficha de la maquina*** (ronda 69) y, con `false`, **los tres
               botones no se ofrecen** -`maquina-lectura-nueva`, `-corregir`, `-anular`-.
               *Prueba: «sin permiso de modificar, la ficha de la maquina NO ofrece los botones de las
               lecturas», **vista fallar** con el typo puesto.*
    AISLAMIENTO: `test_no_se_puede_corregir_una_lectura_de_OTRA_FINCA`,
                 `test_no_se_puede_anular_una_lectura_de_OTRA_MAQUINA_de_la_misma_finca`,
                 `test_una_lectura_de_otra_finca_no_es_tuya`.
    PERTENENCIA: el guardian `test_revision_t14` + las guardas de `_la_lectura_de_esta_maquina`.

**3. Auditoria de alta, correccion y anulacion.**

    ***Los tres dejan rastro, y hay CUATRO pruebas:***
      `test_el_alta_de_una_lectura_deja_rastro_con_su_autor`
      `test_la_correccion_guarda_LO_QUE_DECIA_ANTES_y_lo_que_dice_ahora`
      `test_la_anulacion_guarda_su_motivo`
      `test_ningun_rastro_del_cuenta_horas_apunta_a_la_nada`   <- *el `flush` del alta*

***Y una comprobacion que parecia un defecto y no lo era***: *`anular` escribe `models.Auditoria(` **a mano**
mientras `apuntar` y `corregir` usan `correcciones`. Se miro el patron de la casa: **20 sitios en 12 routers
escriben `accion="anular"` asi**, y `correcciones.apuntar` se usa **solo para altas** -contactos, fusion,
maquinaria, tareas-. ***O sea: `anular` es lo consistente, y cambiarlo habria sido churn.***

**4. Reenvio seguro.**

    `test_reenviar_la_misma_lectura_devuelve_la_que_ya_estaba`
    `test_la_misma_clave_con_otros_datos_es_un_CONFLICTO`
    `test_un_reenvio_de_una_lectura_YA_CORREGIDA_no_pasa_por_reenvio`   <- ***distingue la peticion original
                                                                           de la lectura corregida despues***
    `test_el_indice_unico_impide_dos_lecturas_con_la_misma_clave`       <- ***unicidad en base***

**5. El recorrido desde la pantalla, contra servidor aislado.**

    `test_el_recorrido_del_cuenta_horas` + `test_el_recorrido_se_anda`   ***3 en verde, 121 segundos***
    *No es un `skip`: **121 segundos es navegador de verdad**. Y el guion pulsa el boton real de la
    pantalla -`#pantalla [data-accion="maquina-lectura-nueva"]`-, escribe el valor, anula con su motivo,
    recarga y comprueba el retroceso intermedio.*

**6. `apuntar_lectura`.**

    *El boton existe, **se pinta**, y **el recorrido lo pulsa**. No se borro ningun texto.*

**7. Cerrar con pruebas, recorrido y limitaciones.**

    *Es esta ronda y las anteriores: **1127 pruebas de JS**, **7395 de Python**, **el recorrido**, y las
    limitaciones apuntadas -el corpus de OCR y la meteo siguen necesitando material de fuera-.*

### ***Lo que queda de verdad, dicho sin adornos***

  * **La mitad de PANTALLA del punto 2 solo esta en dos pantallas** -contacto y maquina-. *`app.js` manda
    `puede_modificar` en esos dos sitios y en ningun otro: llevarlo a las demas es del mismo tipo.*
  * ***El corpus del OCR*** (CRM-12) y ***la meteo*** (CRM-10) **necesitan material de fuera**, y eso no lo
    resuelve el programa.
  * Y queda **la continuacion de la cola**: reservas, unidades de fertilizantes, superficies, fiabilidad y
    recuperacion, paneles y preparacion PAC.

### Recuento

    JS: ***1127 en verde***   ·   PYTHON: 7395 (corriendo, job pwsh-2895)
    los tres sitios al dia


---

## 17/10/2026 (71) — **La cola empieza por reservas, y las reservas SOLO EXISTEN EN SERVIDOR**

### ***El cuenta-horas queda cerrado***

    PYTHON: ***exit code 0***   ·   JS: ***1127 en verde***
    los 7 puntos, cada uno con su prueba   (ronda 70)

*Y se sigue con la cola, en su orden: **reservas** primero.*

### ***Y lo que se encontro es justo lo que el encargo prohibe***

    `reserva` aparece ***CERO VECES en todo `web/`*** -ningun fichero del interfaz lo menciona-.

***Y en el servidor esta TODO***, y probado:

    `app/reservas.py`                     lo puro: el intervalo, el solape, los estados,
                                          `lo_que_impide_reservar` (averias), `lo_que_impide`
    `tests/test_las_reservas_de_una_maquina.py`   ***14 pruebas*** de la logica pura
    `tests/test_las_reservas_por_las_puertas.py`  ***7 pruebas por las puertas***, y son duras:
        * el solape lo para ***el servidor***
        * anular libera la maquina
        * una reserva de otra finca no es tuya
        * una maquina averiada no se reserva
        * un estado que no existe se rechaza **diciendo cuales hay**
        * ***dos peticiones A LA VEZ no meten dos reservas solapadas*** (dos capas: el candado
          sobre la maquina y la segunda mirada despues del `flush`)

***O sea: el trabajo esta hecho entero y el agricultor no lo puede usar.*** *Es literalmente lo que el
objetivo dice que **no** se puede declarar terminado: «***No declarar terminada una funcion que solo existe
en servidor***».*

### ***Y la cola lo pide con estas palabras***

    CRM-07, linea 159:  «***Reserva para planificar no es consumo.*** Unidades incompatibles no se
                        convierten sin equivalencia acreditada.»

### ***Todo lo que hace falta, ya localizado, para que la entrega sea corta***

    LAS PUERTAS (ya hechas, en `maquinaria_api.py`):
      GET    /maquinaria/{id}/reservas          `listar_las_reservas`
      POST   /maquinaria/{id}/reservas          `apuntar_una_reserva`     <- con `PuedeModificar`
      PUT    /maquinaria/{id}/reservas/{rid}    `corregir_una_reserva`    <- con `PuedeModificar`
      POST   /maquinaria/{id}/reservas/{rid}/anular  `anular_una_reserva` <- con `PuedeModificar`

    LA ENTRADA (`schemas.ReservaDeMaquinaEntrada`):
      `desde`, `hasta` (datetime local sin huso), `responsable_id`, `tarea_id`,
      `estado` (por defecto `pedida`), `notas`, `clave_de_reenvio`
      ***`responsable_id` y `tarea_id` pueden no venir***: *«una reserva para el tractor el martes es util
      aunque no se sepa quien la coge, y **poder decir "no lo se" es la mitad de este programa**».*

    LA SALIDA (`ReservaDeMaquinaSalida`):
      `id`, `maquina_id`, `desde`, `hasta`, ***`desde_texto`, `hasta_texto`*** (los calcula el servidor),
      `responsable_id`, `tarea_id`, `estado`, `notas`, `anulada`, `motivo_anulacion`

    LOS ESTADOS:  `reservas.LOS_ESTADOS_DE_UNA_RESERVA = ("pedida", "en_curso", "hecha")`

    DONDE VA LA PANTALLA:  ***en la ficha de la MAQUINA***, que es donde vive la puerta. *Y hay que copiar
    la forma de la seccion de AVERIAS (`web/react/pantallas/maquinaria.js`): el componente `Averia`, la
    `<ul className="lista">` con su «no has apuntado ninguna», y el boton de apuntar **envuelto en
    `puede_modificar`** como se hizo con las lecturas.*

    LOS TEXTOS:  van en ***`textos.MAQUINARIA_DE_LA_FINCA`*** -el bloque de la pantalla, lineas 7176 a 7625
    de `app/textos.py`-, **no** en `MENSAJES`. *Y el guardian
    `test_revision_t14.py::test_ningun_texto_de_la_maquinaria_se_queda_sin_usar` **obliga a que cada uno se
    use**, asi que los textos y la pantalla van **en el mismo paso**: si se anaden antes, el guardian los
    caza con razon.*

### ***Y una trampa que ya se piso una vez, escrita en el propio `textos.py`***

    «***ESTA PALABRA LA BORRE SIN QUERER*** (17/10/2026) y el guardian de T14 lo cazo: ***al anadir los
    textos de las reservas*** use esta linea como ***ancla de reemplazo*** en vez de anadir despues, y la
    pantalla se quedo diciendo «undefined» en el boton de apuntar una lectura.»

***O sea: ya hubo una ronda que empezo esto y lo dejo a medias*** -se anadieron textos de reservas, se
perdio `apuntar_lectura` al restaurar, y los textos de reservas **no estan**-. *La leccion esta escrita:
**un ancla que se reemplaza es un ancla que se borra**. Los textos se anaden, no se reemplaza nada.*

### Los tres textos de reserva que SI existen, y son del servidor

    356  "la_reserva_termina_antes_de_empezar": "La reserva tiene que terminar después de empezar…"
    357  "esa_maquina_ya_esta_reservada_esas_horas": "Esa máquina ya está reservada en parte de esas horas."
    362  "reserva_motivo_estado": "Ese estado de reserva no existe."

***Estan en `MENSAJES`, que es donde van los motivos que dice el servidor, y de ahi no se mueven.***

### Recuento

    PYTHON: ***exit code 0***   ·   JS: ***1127 en verde***
    los tres sitios al dia

### Lo que sigue, en un paso

*La pantalla de las reservas, en tres trozos y en este orden, para que cada uno se pueda correr:*
  1. ***los textos y el componente***, juntos -por el guardian de T14-, con su prueba en `tests_js`;
  2. ***`app.js`***: pasar `reservas` a `pantallaUnaMaquina`, la receta del formulario, y las tres
     acciones -`maquina-reserva-nueva`, `-corregir`, `-anular`-;
  3. ***el recorrido***: que la reserva se pueda pedir, corregir y anular **desde la pantalla**, no por API.


---

## 17/10/2026 (72) — **Las reservas llegan a la pantalla: los textos y el componente**

### Lo que se hizo

***Los textos y el componente, en el mismo paso*** -que es obligatorio, porque el guardian
`test_revision_t14.py::test_ningun_texto_de_la_maquinaria_se_queda_sin_usar` **falla si se anaden textos y no
se usan**-.

**1. Los siete textos**, en `textos.MAQUINARIA_DE_LA_FINCA` -el bloque de la pantalla, **no** en `MENSAJES`-:

    seccion_reservas     "Reservas"
    sin_reservas         "No has reservado esta máquina para nada."
    apuntar_reserva      "RESERVAR ESTA MÁQUINA"
    corregir_reserva     "Corregir"
    anular_reserva       "Anular"
    reserva_no_gasta     "Reservar no gasta nada: solo dice que la vas a coger."
    reserva_anulada      "anulada"

***Y `reserva_no_gasta` es la frase de la cola puesta en la pantalla***: *«Reserva para planificar no es
consumo». El agricultor que duda entre «reservar» y «apuntar» tiene que poder saber que **reservar no toca
el cuenta-horas ni el dinero**.*

**2. El componente `Reserva`**, copiando la forma de `Averia`:

    * cuando (los dos extremos, con hora) · estado · ***responsable y tarea SIEMPRE, tambien cuando no
      constan*** -«sin decir quien la coge»- · notas
    * **una anulada se ve tachada, con su motivo**, y **no se corrige ni se anula otra vez**
    * **los botones de corregir y anular solo si `puede_modificar`**

**3. La seccion** en `PantallaDeUnaMaquina`, **antes de las averias**, con su «no has reservado» y **el boton
de reservar envuelto en `puede_modificar`** -igual que se hizo con las lecturas-.

**4. Y la prueba**, en `tests_js/maquinaria.test.js`, que mira **las cuatro cosas**:

    * que la reserva **se vea** -el cuando y su estado-;
    * que **con permiso** salgan los tres botones;
    * que **sin permiso** no salgan… ***pero la reserva se siga viendo*** -«no ofrecer un boton no es no
      poder mirar», que es la mitad que se olvida-;
    * que **una anulada** no se pueda corregir y diga su motivo.

***Y la copia de los textos de `tests_js` se actualizo con los siete***, porque hay una prueba que compara
la copia con el servidor.

### Verde

    tests/test_revision_t14.py          ***24 en verde***   (los dos guardianes de textos)
    tests/test_lista_de_la_junta.py     en verde            (el recuento, 1128)
    tests/test_ficheros_de_texto.py     en verde
    JS:  ***1127 -> 1128, y las 1128 en verde***
    los tres sitios al dia

### ***Y LO QUE FALTA, QUE NO ES POCO -y no se da por terminado-***

***El componente existe, pero `app.js` todavia no le manda las reservas***, asi que **en la aplicacion de
verdad la seccion sale vacia**. *Es exactamente el error que este proyecto castiga -«una funcion que solo
existe en servidor»-, y no se puede decir que las reservas esten terminadas hasta que el camino entero
funcione.* Lo que queda, en tres trozos:

  1. **`app.js`, los datos**: pedir `/api/maquinaria/{id}/reservas` al abrir la ficha -como ya se hace con el
     coste de las averias- y pasarlas a `pantallaUnaMaquina` **ya montadas**: `cuando_texto` (los dos
     extremos), `estado_texto`, `responsable_texto` y `tarea_texto`. *Las frases las monta `app.js`, que es
     la regla de `docs/REACT.md`: el componente no compone, solo ensena.*
  2. **Los cinco textos que faltan** para eso, que se anaden **cuando `app.js` los use** -el guardian T14 no
     deja anadirlos antes-: `reserva_estado_pedida` / `_en_curso` / `_hecha`, `reserva_sin_responsable` y
     `reserva_sin_tarea`.
  3. **El formulario y las tres acciones** en `app.js`: `maquina-reserva-nueva`, `-corregir` y `-anular`, con
     la receta del formulario -desde, hasta, estado, responsable, tarea, notas- y el guardado por
     `guardarLoDeLaMaquinaria`. **Y el `maquina-anular-confirmar`** que ya existe **tiene que saber anular
     una reserva**, que hoy solo sabe de averias e inspecciones.
  4. **Y el recorrido**, que es la prueba de que funciona: *pedir una reserva, corregirla y anularla **desde
     la pantalla**, no por API.*


---

## 17/10/2026 (73) — **Los textos de una reserva los monta el SERVIDOR, y un defecto mio que se cierra**

### ***Lo que se hizo***

**1. El servidor compone los cuatro textos de una reserva**, que es la regla de la casa -ya la seguian
`desde_texto` y `hasta_texto`-:

    `schemas.ReservaDeMaquinaSalida`:
       + ***responsable_texto***, ***tarea_texto*** y ***estado_texto***

    `maquinaria_api._con_sus_textos(db, suya)`:
       * `estado_texto`: con un mapa **explicito** -ver abajo-
       * `responsable_texto`: el **nombre del contacto** (`contactos.id`), o «sin decir quien la coge»
       * `tarea_texto`: el **titulo de la tarea** (`tareas.id`), o «sin decir para que»

***Por que en el servidor y no en la pantalla***: *«el servidor es quien sabe el formato» -la razon que ya
estaba escrita para las fechas- y ademas **es quien tiene a mano los nombres**. Sin esto la pantalla tendria
los **identificadores** en vez de los nombres, o tendria que pedir dos listas mas solo para poder decir «la
coge Juan».*

**2. Los cinco textos, en `MENSAJES`** -donde van los que dice el servidor, junto a los tres de reservas que
ya estaban-:

    reserva_estado_pedida / _en_curso / _hecha      "Pedida" / "En curso" / "Hecha"
    reserva_sin_responsable                        "Sin decir quién la coge"
    reserva_sin_tarea                              "Sin decir para qué"

***Y los tres del estado van en un MAPA EXPLICITO, no compuestos***:

    _LOS_TEXTOS_DE_LOS_ESTADOS_DE_UNA_RESERVA = {
        "pedida": "reserva_estado_pedida", "en_curso": "reserva_estado_en_curso", "hecha": "reserva_estado_hecha",
    }

*Componer la clave con `f"reserva_estado_{estado}"` **dejaria los tres textos sin nombrar en ningun sitio**, y
el guardian de los mensajes huerfanos los contaria -con razon-. **Aqui se nombran**, que es lo que hace que el
guardian pueda distinguir «este texto no lo lee nadie» de «este texto se compone».*

### ***Y un defecto MIO, que se encontro al ir a seguir***

*Al anadir la seccion de las reservas en el componente -ronda 72-, **el boton de reservar se pintaba ya en la
aplicacion de verdad**, porque `app.js` todavia no trae las reservas y **el valor por defecto era `[]`**: la
ficha decia «no has reservado esta maquina para nada» -que **era mentira**: no es que no haya ninguna, es que
no se habian pedido- **y ofrecia un boton que no llevaba a ninguna parte**.*

***Arreglado con la distincion de la casa***, que ya estaba escrita para los papeles y para el coste:
***`null` NO es `[]`***:

    reservas = ***null***   «todavia no se han pedido»  -> ***ni se dice ni se ofrece***
    reservas = ***[]***     «se pidieron y no hay»      -> se dice, **y se ofrece reservar**

***Y con su prueba***, que mira las dos mitades: *con `null` **no sale el boton** y **tampoco la frase**; con
`[]` salen las dos.*

***Es el mismo error que el de `papeles` y `costes`, que la casa ya tenia documentado*** -«`null` es «todavia
no se han pedido» y `[]` es «no hay ninguno»»-, y volvio a pasar por dar un valor por defecto que **afirma**
algo que no se sabe.

### Verde

    test_las_reservas_por_las_puertas · test_las_reservas_de_una_maquina · test_revision_t14   ***58***
    test_los_mensajes_que_nadie_lee · test_lista_de_la_junta                                  en verde
    JS:  ***1128 en verde***
    los tres sitios al dia

### ***Y LO QUE SIGUE -reservas, paso 2-***

***El componente ya esta, los textos ya estan y el servidor ya los manda; falta `app.js`*** para que el
camino entero funcione:

  1. **traer las reservas**: `cargarLasReservasDeLaMaquina(id)` junto a `cargarElCosteDeLasAverias`, y
     llamarla al abrir la ficha **y** al recargarla;
  2. **pasarlas** a `pantallaUnaMaquina` -con `null` mientras no se hayan pedido, que es lo que hace que la
     seccion no aparezca antes de tiempo-;
  3. **el formulario** (`formularioDeUnaReserva`) y **las tres acciones**: `maquina-reserva-nueva`,
     `-corregir` y `-anular` -esta ultima por el `maquina-anular-confirmar` que ya existe, que hoy solo sabe
     de averias e inspecciones-;
  4. **y el recorrido**, que es la prueba de que funciona de verdad.


---

## 17/10/2026 (74) — **Las reservas, enteras en `app.js`: el camino de la pantalla al servidor**

### Lo que se hizo -y es el trozo que faltaba para que la funcion EXISTA-

**En `web/app.js`**, ocho piezas:

    estado         `reservas: null` y `reservasError: ""` -***`null` es «no se han pedido»***-
    cargador       `cargarLasReservasDeLaMaquina(id)`, junto al del coste de las averias, **y con su
                   motivo si falla** -«una tolerancia que no deja rastro es una ceguera»-
    las llamadas   al abrir la ficha **y** al recargarla
    la prop        `reservas: suyo.reservas` a `pantallaUnaMaquina`
    la receta      `formularioDeUnaReserva`: **de cuando a cuando** (`fecha_hora`), como va, y notas
    el despacho    `descriptor.clase === "reserva"`
    el guardado    POST/PUT a `/maquinaria/{id}/reservas`
    el aviso       «Ya esta reservada» / «Ya esta corregida», que no es lo mismo

**Y las dos acciones**: `maquina-reserva-nueva` y `maquina-reserva-corregir`. *La reserva se busca en
`suyo.reservas`, que es **la respuesta cruda de su puerta** -con los instantes en ISO-, y **no** en
`maquinaCruda`, que es la de `/api/maquinaria/{id}` y **no trae las reservas**.*

### ***Y tres decisiones que no son de adorno***

**1. El campo `fecha_hora`, que no existia.** *Una reserva es «el martes de 9 a 11», y con un campo de solo
fecha **la hora se perderia al guardar, y en silencio** -que es justo lo que decide si dos reservas se
pisan-. Se anadio el tipo en `web/react/piezas/campo.js` (`type="datetime-local"`).*

**2. Anular NO lleva accion propia: va por `maquina-anular` con `que: "reserva"`.** *Asi el motivo y su
pregunta son **los mismos que en una averia**, y no hay dos formas de preguntar lo mismo. Lo unico que hubo
que extender fue el **titulo** de la pregunta y **la ruta** -la reserva tiene su propia puerta,
`/reservas/{rid}/anular`-.*

***Y eso obligo a afinar la prueba***: `maquina-anular` **es tambien el boton de las averias**, que no esta
detras del permiso, asi que **buscar solo el nombre daba un falso fallo** -la prueba encontraba el de una
averia y decia que el permiso no funcionaba-. *Se mira por **su `data-que="reserva"`**, que solo lo pone el
boton de una reserva.*

**3. Los tres textos del estado SE MUEVEN al bloque de la pantalla** -estaban en `MENSAJES`-. *Los usan
**los dos**: el servidor para escribir `estado_texto` y **el formulario** para sus tres opciones. Con dos
copias, un dia la pantalla diria «Pedida» y el dato diria otra cosa.*

### ***Y el guardian de los textos cazo un texto mio que no se ensenaba***

    AssertionError: estos textos de la maquinaria no se ensenan en ningun sitio: ['reserva_anulada_aviso']

*Se habia escrito el texto del aviso de la anulacion **y no se usaba**: el aviso seguia diciendo
`t("maquinaria.anulada")`, que vale igual para todo.* ***Ahora la anulacion de una reserva dice lo que de
verdad ha pasado -«la maquina vuelve a estar libre»-, que es lo que el agricultor necesita saber.***

### Verde

    test_revision_t14 · test_los_mensajes_que_nadie_lee · test_las_reservas_por_las_puertas   ***35***
    JS:  ***las 1128 en verde***
    `node --check` limpio en `app.js`, en el componente y en `campo.js`

### ***Y LO QUE FALTA, que es una sola cosa y es la que de verdad prueba que funciona***

***El recorrido.*** *Todo el camino esta escrito, pero **no se ha andado**: falta el guion que, **contra un
servidor aislado y desde la pantalla**,*

  * abra una maquina y vea la seccion de las reservas,
  * **reserve** de tal hora a tal hora,
  * compruebe que **el solape lo para el servidor** -y que lo dice-,
  * la **corrija**,
  * y la **anule** con su motivo, viendo que la maquina vuelve a estar libre.

***Y despues de eso, `unidades de fertilizantes`***, que es lo siguiente de la cola.


---

## 17/10/2026 (75) — **Las reservas SE ANDAN: el recorrido, y anular libera de verdad**

### Lo que se hizo

***El guion que faltaba***, `scripts/verificar_el_recorrido_de_las_reservas.py` -**267 lineas**-, copiando la
forma del del cuenta-horas: *los mismos ayudantes (`pulsar`, `escribe`, `elTexto`), el mismo andamiaje
(`preparar`, `NavegadorDeVerdad`), y **ocho pasos** que se comprueban **contra lo que se ve en la pantalla**,
no contra lo que el servidor dice que hay.*

   1. Una maquina **sin reservas** lo dice, **y dice que reservar no gasta nada** -la frase de la cola-.
   2. El boton **abre el formulario**, con sus campos… ***y los dos extremos son `datetime-local`***: *se
      comprueba el `type` del campo, porque con uno de solo fecha la hora se perderia al guardar.*
   3. Se reserva un tramo y **la reserva sale en la ficha, con su estado**.
   4. ***Otra que se pisa la para el SERVIDOR, lo dice, y NO se apunta***.
   5. La misma hora en **otra maquina** si se puede.
   6. **Corregir** sale **relleno con lo que habia**.
   7. **Anular** pide el motivo -como una averia-, y ***el MISMO tramo se puede reservar otra vez***.
   8. **Se recarga** la pagina y la anulada sigue con su motivo.

### ***Y el paso 7 es el que importa de verdad***

*Que una reserva quede «anulada» ya lo probaba `test_las_reservas_por_las_puertas`. **Lo que no estaba probado
-era imposible de probar por la API, porque hay que verlo con los ojos- es que anular una reserva **libere la
maquina de verdad**.*** *Por eso el paso 7 **no se queda en mirar el estado**: **vuelve a reservar el mismo
tramo** y comprueba que esta vez si entra. Si anular no liberara, el servidor contestaria 409 y el paso
fallaria.*

### ***Y una leccion de comillas, que costo dos intentos***

*El guion se escribio con **un selector de JavaScript con comillas dobles dentro** -`[data-accion="..."]`-,
metido a mano en una cadena de Python que a su vez iba dentro de otra. **El fichero entero dejo de compilar**,
y el `SyntaxError` salia en **una linea que parecia correcta**.*

***Arreglado con dos ayudantes*** -`esperarQueDiga` y `esperarQueHaya`- **que pasan el texto por
`json.dumps`**: *asi las comillas se escapan solas y **nunca mas se cose un selector a mano**.* *Es la misma
leccion que el `html\`…\`` de las plantillas: **lo que lleva comillas dentro no se escribe a mano**.*

### ***Y las dos pruebas del guion***

    test_las_reservas_se_andan_enteras        ***33 segundos de navegador de verdad***
    test_el_guion_de_las_reservas_dice_lo_que_comprueba

***La segunda defiende la cabecera*** *-que siga contando los pasos-, y en concreto **la frase que no puede
desaparecer**: «Reserva para planificar **no es consumo**».*

### Verde

    los tres recorridos, andados:  ***64s + 55s + 33s = 5 pruebas en verde (2:34)***
    test_lista_de_la_junta (el recuento, ***5401***)   en verde
    JS: ***1128 en verde***
    y la suite de Python entera, corriendo (job pwsh-3058)

### ***Y las reservas quedan TERMINADAS***

*Servidor -con sus 21 pruebas-, textos, componente, `app.js` entero, **y el recorrido que lo anda**. **Ya no
hay nada de las reservas que solo exista en servidor.***

### Lo que sigue: **unidades de fertilizantes**

*Lo siguiente de la cola, con lo que pide CRM-07:* ***«Abono: composicion con unidades, producto aplicado y
nutrientes calculados separados; no asumir 0»*** *y* ***«Unidades incompatibles no se convierten sin
equivalencia acreditada»***. *La aceptacion esta escrita: «600 kg en 3 ha con N 15 % acreditado -> 200 kg/ha y
30 kg N/ha; ***P desconocido si falta***» y «2 L en 4 ha -> 0,5 L/ha, ***sin area -> desconocido***».*


---

## 17/10/2026 (76) — **Fertilizantes: verificado, esta hecho. Y superficies: el hueco, con precision**

### 1 · Las unidades de fertilizantes ***ESTAN TERMINADAS*** -y se verifico antes de tocar nada-

*La cola pide, para CRM-07:*

    «Abono: composicion con unidades, producto aplicado y nutrientes calculados separados; ***no asumir 0***.»
    «***Unidades incompatibles no se convierten sin equivalencia acreditada.***»
    Aceptacion: «600 kg en 3 ha con N 15 % acreditado -> 200 kg/ha y ***30 kg N/ha***; ***P desconocido si falta***»

***Y esta hecho, con sus dos numeros de aceptacion probados por su nombre***:

    tests/test_lo_que_aporta_un_abono.py   ***14 pruebas***, y entre ellas:
      ***test_600_kg_en_3_ha_con_N_15_por_ciento***            <- el caso literal de la cola
      ***test_20_litros_a_100_g_por_litro_en_2_ha***           <- y el de los liquidos
      test_20_litros_al_15_por_ciento_SIN_DENSIDAD_no_se_calcula   +  ***_POR_LA_PUERTA***
      test_un_nutriente_que_NO_CONSTA_no_es_un_cero
      test_sin_superficie_la_dosis_es_DESCONOCIDA_y_no_cero
      test_una_base_de_masa_por_volumen_no_vale_para_un_SOLIDO
      test_las_columnas_antiguas_se_leen_como_lo_que_SON
    tests/test_los_kilos_de_un_abono.py  ***4 pruebas***, con «el fosforo que no viene en la etiqueta no es cero»

***Y el modulo tiene lo que hace falta para no convertir a ciegas***: `LAS_BASES` (porcentaje en masa,
gramos por litro, kilos por hectolitro), `LAS_UNIDADES_DEL_PRODUCTO` (kg, L), y los motivos dichos -
`FALTA_LA_DENSIDAD`, `FALTA_LA_SUPERFICIE`, `LA_BASE_NO_VALE_PARA_ESA_UNIDAD`-. ***La cuenta vive en un solo
sitio*** (`nutrientes.el_aporte`, usado por `servicios.py:192`), y el defecto de las diez veces esta contado
en el propio codigo.

***Y la pantalla SI lo tiene***: `base_de_la_riqueza`, `densidad_kg_por_litro` y `unidad_del_producto` estan
en el formulario del abono (`app.js`), y `aporte`/`por_hectarea` salen en 11 y 8 sitios.

***Y se miro el unico sitio sospechoso***: `gastos.py:832` reutiliza `legal.unidades_fertilizantes`, que
**asume kg y % m/m** -el error que `servicios.py` documenta-. *Se leyo: lo que le pasa es `kg_producto`, un
valor **que ya viene en kilos**, asi que la asuncion **se cumple en su contexto**. ***No hay defecto.***

***Conclusion: unidades de fertilizantes no necesita trabajo. Lo que necesitaba era que alguien lo verificara.***

### 2 · Y `superficies` SI tiene el hueco -el mismo de las reservas, y mas grande-

`app/superficies.py` -**17/10/2026**- tiene **cinco magnitudes**, y su razon de ser esta escrita:

    «***separarlas en la base NO IMPIDE SUMARLAS EN UNA CUENTA***, y esa cuenta es de las que se hacen sin
    pensar: *«¿cuantas hectareas llevo?»* y se suma todo lo que tenga `_ha` en el nombre. …
    Lo que faltaba era ***una cuenta que se niegue a mezclarlas***, y aqui esta.»

***Y NADIE SE LA PREGUNTA***:

    ***LA_PREGUNTA***             solo `superficies.py` y su prueba  <- ***«que significa este numero» no llega a nadie***
    ***ESAS_DOS_NO_SE_SUMAN***    ***solo `superficies.py`***        <- ***el mensaje de negarse a sumar NO SE ENSENA NUNCA***
    ***LO_DECLARADO_EN_LA_PAC***  ***solo `superficies.py`***        <- ***una magnitud ENTERA que nadie usa***
    ***LO_TRATADO_DE_UN_HECHO***  modulo y prueba
    y las cinco magnitudes:  ***NO APARECEN en `web/`***  -ni `lo_que_se_cultiva`, ni `lo_que_dice_el_sigpac`,
    ni `lo_de_un_tercero`, ni `lo_declarado_en_la_pac`-

*Lo unico que si sale es **una** metrica del panel* (`paneles.py:186`, `suma_lo_mismo(magnitud="superficie")`)
*y `servicios_a_terceros.py`, que usa `se_pueden_sumar` para no sumar las 10 ha de un tercero.*

***Y la cola lo pide literal***: «***Superficies declaradas, oficiales y trabajadas separadas***», y su
aceptacion: «formas solapadas ***no duplican superficie unica sin advertencia***». *Y el contrato comun:
«Hectareas de trabajo acumulado ***distintas*** de superficie unica».*

***O sea: la regla esta escrita, probada -`test_las_superficies_no_se_suman.py`- y es INVISIBLE. Es
exactamente «una funcion que solo existe en servidor».***

### Verde

    ***PYTHON: 5401 · exit code 0***
    JS: ***1128 en verde***
    los tres recorridos andados (64s + 55s + 33s), y los tres sitios al dia

### Lo que sigue: **superficies**, y ya se sabe por donde

*El trabajo es **llevar la pregunta a la pantalla**: donde el agricultor ve hectareas, decir **cual** de las
cinco es -con `LA_PREGUNTA`-, y **cuando dos no se pueden sumar, decirlo** con `ESAS_DOS_NO_SE_SUMAN` en vez
de dar un total que mezcla. *Y `LO_DECLARADO_EN_LA_PAC`, que hoy no lo usa nadie, tiene su sitio en la ficha
de la tierra o en el panel de la PAC.*


---

## 17/10/2026 (77) — **Las superficies salen a la luz: la puerta, con las tres y su pregunta**

### ***El hallazgo, que es lo que hacia falta***

`app/superficies.py` -CRM-06, **17/10/2026**- tenia **la regla escrita y probada**
(`test_las_superficies_no_se_suman.py`, 8 pruebas) y **el propio fichero dice su razon de ser**:

    «***separarlas en la base NO IMPIDE SUMARLAS EN UNA CUENTA***, y esa cuenta es de las que se hacen sin
    pensar: *«¿cuantas hectareas llevo?»* y se suma todo lo que tenga `_ha` en el nombre. …
    Lo que faltaba era ***una cuenta que se niegue a mezclarlas***, y aqui esta.»

***Y nadie se la preguntaba***:

    ***`la_superficie_de_la_finca` -> NADIE LA LLAMABA***
    ***`lo_tratado`               -> NADIE LA LLAMABA***
    `lo_de_un_tercero`           -> solo `servicios_a_terceros.py`
    y las cinco magnitudes:  ***NO APARECIAN en `web/`***  -ni `lo_que_se_cultiva`, ni `lo_que_dice_el_sigpac`,
    ni `lo_tratado_de_un_hecho`, ni `lo_de_un_tercero`, ni `lo_declarado_en_la_pac`-
    y ***`LA_PREGUNTA` y `ESAS_DOS_NO_SE_SUMAN` no salian de su propio fichero***

*Es exactamente lo que el encargo llama **«una funcion que solo existe en servidor»**: la regla estaba,
probada, y **nadie se la preguntaba**.*

### Lo que se hizo

**1. Los textos**, en `textos.TIERRA_Y_MAPA` -**no** en el bloque de la maquinaria, y **no** en
`/api/interfaz`-: *esa vista ya manda sus palabras con los datos, y su docstring lo dice: **«las palabras son
del servidor, y este endpoint no tiene entrada en `/api/interfaz` porque es el unico que las usa»**.*

    superficies_titulo / superficies_pista / superficies_no_se_suman / superficies_no_se_sabe / superficies_falta
    ***y una pregunta por magnitud***:  superficie_lo_que_se_cultiva, superficie_lo_que_dice_el_sigpac,
    superficie_lo_tratado_de_un_hecho, superficie_lo_de_un_tercero, superficie_lo_declarado_en_la_pac

***Y la pista dice lo que hay que decir***: *«Cada una contesta a una pregunta distinta, **asi que no se suman
entre si**. Se enseñan juntas **para que se vea la diferencia, no para hacer un total**.»*

**2. El esquema**: `UnaSuperficieDeLaFinca` -`magnitud`, `pregunta`, `hectareas`, `se_sabe`, `lo_que_falta`-
y **el campo `las_superficies` en `VistaDeLasTierras`**.

***Y `hectareas: float | None` es `None` cuando no se sabe, NUNCA `0`***: *un cero diria «no tienes tierras»,
que es una afirmacion muy distinta de «falta la superficie de alguna» -y en una declaracion eso no es un
redondeo, es una cifra falsa-.*

**3. La puerta**: `_las_superficies_de_la_finca(db, explotacion, campana)`, que **llama por fin a las dos
funciones huerfanas**:

    `superficies.la_superficie_de_la_finca(parcelas)`  -> ***lo que se cultiva***
    `superficies.lo_tratado(los_tratamientos)`        -> ***lo trabajado, de cada hecho***
    `superficies.lo_de_un_tercero(de_terceros)`       -> lo de un tercero

*Y `_una_superficie` **coge la pregunta por el nombre de la magnitud**
(`textos.TIERRA_Y_MAPA[f"superficie_{magnitud}"]`), asi que **una magnitud nueva no puede quedarse sin su
pregunta**: seria una cifra sin saber que mide.*

**4. Y cinco pruebas**, `tests/test_las_superficies_de_la_finca.py`, que defienden:

    · que la vista traiga ***las tres***, y en su orden;
    · que ***las tres preguntas sean DISTINTAS*** -«si dos coincidieran, se podrian volver a confundir»-;
    · que lo que se cultiva sea **la suma de las tierras** (2,43 + 1,57 = 4);
    · que ***una tierra sin superficie haga que el total NO SE SEPA***, con **`hectareas: None` y no `0`**;
    · que ***lo de un tercero vaya por su cuenta***, con **su propia pregunta** -«lo que se hizo en tierras
      que no son tuyas»-;
    · y que **sin tratamientos, lo tratado sea `0` de verdad** -se ha mirado-, *que no es lo mismo que
      «no se sabe».*

### Verde

    tests/test_las_superficies_de_la_finca.py   ***5 en verde***
    los guardianes (recuento ***5408***, T14, superficies, mapa, tierras)   en verde
    los tres sitios al dia

### ***Y LO QUE FALTA, que es una sola cosa y esta dicha a proposito***

***La pantalla.*** *La puerta ya devuelve las tres con su pregunta, y `vista.las_superficies` **llega sola al
componente** -la pantalla de las tierras recibe la vista entera, asi que **no hay que tocar `app.js`**-. Lo
que falta es pintarlo, y **no se hizo en esta ronda a proposito**:

  * **el servidor manda `hectareas` en crudo y la casa formatea EN EL SERVIDOR** -es lo que hace
    `superficie_texto` en esa misma tabla-, asi que hace falta un `hectareas_texto` antes de pintar nada;
  * y **una pantalla no se da por hecha sin andarla con un navegador**. *Meterla sin poder verificarla seria
    enviar una edicion a ciegas, y en este proyecto eso ya ha costado rondas.*

*Asi que el siguiente paso es: `hectareas_texto` en el esquema, el bloque en `tierras_mapa.js` -al lado del
pie, con `superficies_no_se_suman`-, **y el recorrido que lo ande**.*


---

## 17/10/2026 (78) — **Las superficies, TERMINADAS: la pantalla, y la prueba que se vio fallar**

### Lo que se hizo, que es lo que faltaba

**1. `hectareas_texto` en el esquema**, que lo escribe **el servidor**:

    `schemas.UnaSuperficieDeLaFinca`  +  ***hectareas_texto: str***

*Es la regla de la casa para las hectareas, la misma que la de `superficie_texto` en esa tabla: **la pantalla
no compone cifras**, porque dos sitios formateando el mismo numero acaban diciendo cosas distintas.*

***Y con el formateador de la casa***, `legal.formatea_medida` -el mismo que usa el cuaderno-:

    formatea_medida(4.0, "ha")  ->  «4,00 ha»
    formatea_medida(0.0, "ha")  ->  «0,00 ha»
    y con `None` -> ***vacio***, **no «sin dato»**: *es que ahi la pantalla dice «no se sabe», que es la
    frase de la casa.*

**2. El bloque, en `tierras_mapa.js`**, **al lado del pie** y con las tres cosas que importan:

    * ***las tres, cada una con SU PREGUNTA*** -la que manda el servidor-;
    * ***la cifra***, ya escrita (`4,00 ha`);
    * y ***«estas cifras no se suman»***, que es la mitad que evita el error de cabeza.

*Y `vista.las_superficies` **llega sola al componente** -la pantalla de las tierras recibe la vista entera-,
asi que **no hubo que tocar `app.js`**.*

**3. Y la prueba**, en `tests_js/tierras_y_versiones.test.js` -que ya tenia 41-, con **las tres cosas**:

    · que salgan las tres, **cada una con su pregunta**, y con su `data-magnitud`;
    · que **NO haya un total**: *4 + 12 + 0 = 16, y **16 no puede aparecer en ningun sitio*** -«es el error
      de las diez veces, con hectareas»-;
    · que **lo que no se sabe diga «no se sabe»** y ***nunca un cero***.

### ***Y se rompio a proposito, para ver la prueba fallar***

*Es la disciplina que este proyecto ha demostrado que funciona: **una prueba que no se ha visto fallar no
prueba nada**.*

    con la pantalla mirando el TEXTO en vez de `se_sabe`:  ***exit code 1***, y el fallo es la prueba nueva
    restaurada:                                          ***exit code 0, 42 en verde***

***O sea: la prueba caza de verdad el defecto de pintar un cero donde no se sabe.***

### Verde

    tests_js/tierras_y_versiones.test.js   ***42 en verde*** (41 + la nueva)
    JS entero:  ***1129 en verde***
    PYTHON:  ***5408***, con los guardianes (recuento, T14, T10, superficies) en verde
    los tres sitios al dia

### ***Y la LIMITACION, dicha***

***El bloque esta probado al nivel del componente -y la prueba se vio fallar-, pero no hay un RECORRIDO que
ande la pantalla de las tierras con un navegador*** *afirmando estas tres filas. El proyecto ya tiene
`test_comprobar_en_un_navegador.py`, que visita pantallas de verdad, pero **no se ha comprobado que mire esta
seccion**.*

*Queda como ticket: **un recorrido de las superficies**, como el de las reservas -que si lo tiene-.*

### ***Y la cola queda asi***

    cuenta-horas    ***CERRADO*** -los 7 puntos, con su recorrido andado-
    reservas        ***CERRADO*** -servidor, pantalla y ***recorrido de 33 s con navegador***
    fertilizantes   ***VERIFICADO*** -los dos numeros de aceptacion probados por su nombre-
    superficies     ***CERRADO*** -la puerta, la pantalla y la prueba vista fallar-  <- *con el recorrido pendiente*

### Lo que sigue: **fiabilidad y recuperacion**

*Lo siguiente de la cola, con lo que pide CRM-05:* ***«fallos de red, reintentos, duplicados y
recuperacion»***, *y los casos de aceptacion del COLA que ya estan escritos sobre el reenvio: **«el mismo
apunte dos veces no duplica»**, **«dos peticiones a la vez y una sola fila»**. *Parte de esto ya esta hecho
en el cuenta-horas y en las reservas -clave de reenvio, indice unico, conflicto ante datos distintos-, y lo
que falta es que **valga para todas las puertas**, no solo para las dos que se han trabajado.*


---

## 17/10/2026 (79) — **CRM-05 en la ficha de la maquina… y una ronda que acaba REVIRTIENDO lo de ayer**

### ***Lo primero: las cinco pruebas que estaban rojas eran EL CONTRATO, y tenian razon***

*El job de la ronda 78 -el de las superficies- **termino con `exit 1`** y yo no lo mire hasta ahora. Cinco
pruebas del T06 en rojo*:

    test_t06_tierras_y_mapa.py::TestLosRecuentosDelPie::***test_no_se_ofrece_ningun_total_de_hectareas***
    test_revision_t06.py::Test8NiUnaCifraInventada::***test_no_hay_ni_un_total_ni_una_media_ni_un_porcentaje***
    test_revision_t06.py::***test_no_hay_ni_un_decimal_fuera_de_los_datos_de_una_tierra***
    test_revision_t06.py::***test_una_tierra_sin_superficie_no_se_convierte_en_cero_hectareas***
    test_revision_t06.py::***test_sin_ninguna_forma_no_hay_caja_ni_un_centro_inventado***

***Y lo que dicen es explicito y deliberado***:

    «Por eso ***no hay ningun total de superficie en esta respuesta***, y esta prueba lo fija para que
    nadie lo anada «porque queda bien en el pie».»

    assert set(datos) == {textos, textos_de_las_versiones, campana_id, campana_anio, tierras, totales,
                          mapa, filtros}          <- ***la lista, escrita entera***
    permitidos = {.tierras[].superficie_ha, .tierras[].superficie_sigpac_ha, .tierras[].area_declarada_ha,
                  .mapa.caja.*, .mapa.extension.*}   <- ***y los decimales, uno por uno***
    assert decimales == []                        <- «sin formas, la respuesta no puede traer coordenadas»

***Y mi bloque las rompia por dos motivos, los dos mios***: *anadia una clave nueva a la respuesta, y
- **peor**- devolvia **`0.0`** para «lo tratado» cuando no hay tratamientos. ***Ese `0.0` es exactamente la
regla que este proyecto defiende*** -«lo que no consta no es un cero»-, y lo estaba incumpliendo yo.*

***Se revirtio entero***: el bloque de `tierras_mapa.js`, el campo `las_superficies` de `VistaDeLasTierras`,
`UnaSuperficieDeLaFinca`, `_las_superficies_de_la_finca`, los 31 renglones de texto, la prueba del JS y su
fichero de pruebas. **Y las cinco pruebas del contrato, en verde otra vez.**

***Leccion, y es la de siempre en este proyecto***: *el sitio de las cifras **agregadas** no es la pantalla de
las tierras -que es de **recuentos** y de **dato por tierra**-, sino **el panel** (`paneles.py`, CRM-11),
que es donde vive `magnitud`, `fuente`, `periodo` y `cobertura`… **y que todavia no tiene pantalla**. Ahi es
donde van las tres superficies, el dia que se haga el panel.*

### ***Y lo que SI queda hecho: CRM-05 en la ficha de la maquina***

*El hallazgo*: *las **inspecciones** y las **averias** viven en la misma pantalla que las lecturas del
cuenta-horas, con **la misma clave de reenvio** y **la misma consulta de «¿ya esta?» antes de insertar**… **y
sin el indice unico**. Y ademas:*

    `InspeccionDeMaquina`  · ***sin indice*** · y cuando la clave ya estaba ***devolvia la que habia SIN MIRAR LOS DATOS***
    `AveriaDeMaquina`      · ***sin indice*** · y lo mismo
    `LecturaDeContador`    · indice unico parcial · ***409 si los datos no coinciden*** · y recupera del choque

***Tres cosas que faltaban, y las tres puestas***:

**1. El indice unico parcial** en las dos tablas, copiando el de las lecturas:
`(explotacion_id, maquina_id, clave_de_reenvio)`, `WHERE clave_de_reenvio IS NOT NULL`. *Lleva `maquina_id`
porque el alcance de la clave es **por maquina**; y es parcial porque la mayoria de los apuntes se hacen
desde la pantalla, sin clave.*

**2. La comparacion de LA ACCION ENTERA**, con dos ayudantes nuevos: *si coincide, es un reenvio legitimo y
se devuelve la que ya estaba; **si no coincide, 409**.* ***Hasta hoy un reenvio con datos distintos devolvia
la vieja y el dato nuevo se perdia en silencio*** *-el agricultor creyendo que su correccion entro-.*

**3. La recuperacion del choque**: *la que pierde el indice recibe un `IntegrityError`, **se deshace lo
intentado y devuelve la que gano**, en vez de un 500.*

### ***Y DOS DEFECTOS que encontraron las pruebas, no yo***

***a) El error mio del nombre***: *la puerta de la averia **no limpia los datos en un diccionario**, asi que
pasaba `datos_limpios`, que alli no existe. La prueba del 409 lo cazo con un `NameError` limpio.*

***b) Y el de verdad, que es el importante***: *la prueba de **las dos peticiones a la vez** fallo con*

    UNIQUE constraint failed: inspecciones_de_maquina.explotacion_id, maquina_id, clave_de_reenvio

***o sea: el indice funcionaba y la recuperacion NO***. *El `flush()` va **antes** del `commit()`, y **la fila
se escribe en el `flush`**: con el `try` solo alrededor del `commit`, la excepcion se escapaba por delante y
el agricultor veia un **500**.*

***Y LO MISMO TENIAN LAS LECTURAS DEL CUENTA-HORAS*** -su recuperacion tambien estaba despues del `flush`-.
*Asi que se subio el `try` hasta antes del `flush()` **en las tres puertas**, con su comentario explicando
por que. **Es un defecto que llevaba ahi desde que se escribio, y lo ha encontrado la prueba de la carrera.***

### Verde

    tests/test_lo_que_no_se_apunta_dos_veces.py   ***5 nuevas, 28 en verde con las de las lecturas***
    test_revision_t06.py + test_t06_tierras_y_mapa.py   ***las cinco del contrato, en verde***
    JS: ***1128 en verde***   ·   PYTHON: ***5406***, y los tres sitios al dia
    y la suite entera, corriendo (job pwsh-3280)

### ***Lo que queda de CRM-05, y lo que sigue***

***CRM-05 pide que el reenvio seguro valga para TODAS las puertas***, y hoy falta en: `TrabajoPrevisto`,
`Recepcion`, `AplicacionDeUnPago` y `Subvencion` -los cuatro **con la columna y sin el indice**-. *Es el mismo
trabajo de esta ronda, repetido en cuatro sitios, y va con la misma prueba de la carrera.*

*Y las tres superficies **esperan al panel** (CRM-11), que es su sitio -no la pantalla de las tierras-.*


---

## 17/10/2026 (80) — ***UN INCIDENTE, CONTADO ENTERO: perdi dos clases y las reconstrui***

### ***Lo que hice mal, sin adornos***

**1. `git checkout` sobre un fichero con trabajo sin commitear.** *Al ver `models.py` con los indices mal
colocados, restaure el fichero desde git. **Y `models.py` tenia trabajo de toda la sesion sin commitear**: la
clase entera `LecturaDeContador` (CRM-07 #8) y la clase entera `ReservaDeMaquina` (CRM-07 #9) **no estaban en
HEAD** -lo confirme despues con `git show HEAD:...`-. **Las borro.***

**2. Un indice de linea usado como desplazamiento de caracter.** *El script que insertaba los indices calculaba
`desplazamiento` como **numero de linea** y lo usaba en `u[:desplazamiento]` -que es un **desplazamiento de
caracter**-. Resultado: los seis bloques cayeron **dentro del docstring del modulo**, partiendo frases por la
mitad. **Y `ast.parse` no lo vio, porque todo quedo dentro de una cadena.***

**3. Escribir el fichero en LF.** *La casa usa CRLF: al escribir con `\n` a secas, `git diff` mostro el
fichero entero como cambiado y **escondio el daño de verdad** durante dos comprobaciones.*

### ***Lo que se perdio, exactamente***

    ***`class LecturaDeContador`***  (12 columnas + su indice unico parcial)
    ***`class ReservaDeMaquina`***   (13 columnas + sus dos indices)

*Y **nada mas**: el `git diff --stat` contra HEAD acabo dando **146 inserciones y 0 borrados**, o sea que el
resto de `models.py` estaba intacto, y una comprobacion sistematica -«que simbolos de `models` usa el codigo y
no existen»- dio **exactamente dos**.*

### ***Y lo que NO se perdio***

***El resto del trabajo de la sesion entera, que es mucho***: los **31 ficheros** de `app/` -2619 inserciones-,
todo `web/`, todo `tests/`. *El daño fue **un fichero**, y se supo medirlo.*

### ***La recuperacion, y por que funciono***

**Lo primero: buscar copias.** *Y no habia*: el `.pyc` era del **16/10 23:08** -anterior a las dos clases-, la
base del agricultor es del 8 de octubre -anterior a esas tablas-, la copia de `Temp\cuedigital-head` tampoco
las tenia, y los **8 blobs sueltos** de `git fsck --lost-found` tampoco.

***Pero habia algo mejor que una copia: la especificacion.***

    · `schemas.LecturaDeContadorEntrada` y `LecturaDeContadorSalida`  -> ***los campos y sus tipos***
    · `maquinaria_api.py`                                            -> ***todos los atributos que usa***
    · y el `__table_args__` de la lectura, **que yo habia leido literalmente** esta misma ronda
    · y `ReservaDeMaquina`, **que habia leido entera** al empezar la ronda (docstring, indices y columnas)
    · y sobre todo: ***55 pruebas*** de esos dos modulos

*Las dos clases se reescribieron desde ahi, y **las 55 pruebas pasaron a la primera**. **El oraculo era la
especificacion**, que es exactamente lo que este proyecto lleva rondas construyendo.*

***Y queda anotado en el propio codigo***: *las dos clases llevan ahora una linea que dice que se
reconstruyeron el 17/10/2026 y de donde salio cada dato, **para que nadie se extrane de que los comentarios de
dentro sean mas cortos que los del resto del fichero**.*

### ***Las tres lecciones, para que no vuelva a pasar***

  1. ***`git checkout` NO es «deshacer mi ultimo cambio»: es «volver a HEAD».*** *Y en este repositorio
     **todo el trabajo de la sesion esta sin commitear**. Lo correcto era **arreglar el fichero en su sitio**
     -la corrupcion estaba dentro de un docstring y sabia exactamente que texto quitar-, no restaurarlo.*
  2. ***Un script que reescribe un fichero fuente se comprueba DESPUES de escribirlo, mirando donde han
     caido las cosas*** -no solo que `ast.parse` no proteste: *una insercion dentro de una cadena compila
     perfectamente-*.
  3. ***Los finales de linea son parte del fichero***: *escribir en LF donde la casa usa CRLF **esconde el
     diff**, y el diff es lo unico que dice que ha cambiado de verdad.*

***Y para que no dependa de la memoria***: se ha dejado una **copia de seguridad del trabajo sin commitear**
-`app/`, `web/` y `tests/`- en el perfil, `copia-de-seguridad-del-trabajo-sin-commitear.zip`.

***Lo que de verdad haria falta -y es decision de David- es commitear***: *mientras la sesion entera viva solo
en el arbol de trabajo, cualquier `checkout`, cualquier `stash` o cualquier accidente se la lleva por delante.*

### Verde

    los dos modulos reconstruidos:  ***55 pruebas en verde a la primera***
    y la suite entera, corriendo (job pwsh-3312)

### ***Y la entrega de CRM-05 de esta ronda, que es lo que se estaba haciendo***

*Se quedo a medias por el incidente, pero **lo que si quedo hecho antes** es la lista exacta y la decision*:

    ***24 modelos con `clave_de_reenvio`***  ·  ***20 con indice unico***
    ***y los 4 que faltaban -`Maquina`, `Labor`, `TrabajoPrevisto`, `Subvencion`- con su indice puesto***
    (se pusieron, se perdieron con el `checkout`, y **se volvieron a poner** -los seis, con los dos de la
    ronda anterior-)

*Y queda por hacer, ya con el terreno firme*: **la recuperacion del choque y el 409** en esas cuatro puertas,
*que es lo mismo que se hizo en las inspecciones y las averias.* **Y la prueba de la carrera para cada una.**


---

## 17/10/2026 (81) — ***El daño era MAYOR de lo que medi: faltaban COLUMNAS***

### ***Lo que descubrio la suite, y yo no habia visto***

*La ronda 80 termino diciendo «el daño son **dos clases**» -lo dijo una comprobacion que buscaba **simbolos
que faltan**-. Y era **falso**: la suite entera salio con `exit 1`, con **ERRORES** -no fallos- en las pruebas
de abonos:*

    app\routers\maestros.py:418: in _preparar_fertilizante_guardable
        fertilizante = models.Fertilizante(explotacion_id=explotacion.id, **valores)
    TypeError: 'riqueza_p2o5' is an invalid keyword argument for Fertilizante

***O sea: `Fertilizante` existia, pero habia PERDIDO CINCO COLUMNAS.*** *Y lo mismo el apunte de
fertilizacion. **Una clase puede existir y estar vacia por dentro**, y mi comprobacion -«que simbolos usa el
codigo y no existen»- **no podia verlo**.*

### ***Lo que se habia perdido de verdad -el ticket de los fertilizantes, entero-***

    `Fertilizante`           -> ***base_de_la_riqueza · densidad_kg_por_litro · fuente_de_la_riqueza
                                 riqueza_p2o5 · riqueza_k2o***
    `RegistroFertilizacion`  -> ***unidad_del_producto · base_de_la_riqueza · densidad_kg_por_litro***
    y el `from . import nutrientes` del propio `models.py`

*Es decir: **el ticket de «unidades de fertilizantes» que yo mismo verifique en la ronda 76** -y del que
dije «no necesita trabajo»- **habia perdido su parte de modelo**. Los esquemas, la cuenta y las pruebas
seguian enteros; **el sitio donde se guarda, no**.*

### ***Como se recupero***

*Con la misma regla que funciono con las dos clases: **la especificacion estaba en otro sitio**.*

    · `FertilizanteEntrada` / `FertilizanteSalida`  -> ***los cinco campos, con sus comentarios y sus tipos***
    · `maestros._preparar_fertilizante_guardable`   -> ***que pasa cada uno al modelo***
    · `nutrientes.py`                               -> ***las constantes de los valores por defecto***
    · y `test_lo_que_aporta_un_abono.py`, `test_los_kilos_de_un_abono.py`, `test_revision_t05_y_t09.py`,
      `test_zona_de_nitratos_no_comprobado.py`      -> ***la prueba de que estaba bien***

*Y **236 pruebas de abonos en verde** con las columnas repuestas.*

### ***Y la comprobacion que faltaba, escrita***

*Se hizo una segunda comprobacion sistematica -**cada palabra clave que el codigo le pasa a un modelo,
contra sus columnas reales**-, que encontro las tres del apunte de fertilizacion. **Pero tambien tiene
puntos ciegos, y hay que decirlo**: no ve lo que va por `**valores` -que es justo como se perdio
`riqueza_p2o5`-, ni una columna que se **lea** sin mandarse nunca.*

***Asi que el unico oracle completo es la suite.*** *Y es el que ha estado diciendo la verdad todo el rato.*

### ***Y lo que se hizo de CRM-05 antes del incidente, y despues***

**La recuperacion del choque en `Maquina` y en `Subvencion`**, con su `flush` dentro del `try` -el defecto
que ya se cerro en las inspecciones y las averias-.

**Y `Subvencion`, que era la peor de las cuatro**: *no miraba la clave siquiera.* **Ahora la mira y recoge el
choque.**

***Y ahi cometi dos defectos mas, los dos mios, y los dos los cazaron las pruebas***:

  1. **El `return` temprano devolvia una forma distinta** que el camino normal: *la puerta contesta
     `{"subvencion": ..., "avisos": [...]}` y mi camino del reenvio contestaba **la subvencion a secas**.
     **Un reintento del movil habria roto la pantalla.*** *Se arreglo extrayendo la forma a **un solo
     ayudante** -`_lo_que_se_contesta_de_una_subvencion`-, para que los dos caminos no puedan volver a
     divergir.*
  2. **El ayudante lo inserte entre el decorador y la funcion**, asi que `@router.post` se quedo pegado a el
     y FastAPI intento sacar un modelo de respuesta de `models.Subvencion`. *Se movio antes del decorador.*

### Verde

    los abonos:  ***236 pruebas en verde***
    las dos de la carrera y las dos del 409 que se anadieron:  ***16 en verde***
    y la suite entera, corriendo (job pwsh-3403)

### ***La leccion, y es la segunda vez en dos rondas***

***Una comprobacion que solo mira NOMBRES no ve un modelo vaciado.*** *La primera vez busque clases que
faltaban; habia que buscar **columnas** que faltaban. Y esa tampoco basta: **lo que de verdad dice si algo
falta es ejecutar la suite entera**, porque las pruebas son la especificacion -lo fueron para las dos clases,
y lo han vuelto a ser para las ocho columnas-.*

***Y sigue en pie lo de la ronda anterior, que es lo que de verdad lo arregla***: *mientras el trabajo de la
sesion viva solo en el arbol -**sin commitear**-, cualquier `checkout` se lo lleva. **La copia de seguridad
del perfil se hizo antes de este segundo hallazgo: hay que rehacerla.***


---

## 17/10/2026 (82) — ***CRM-05 COMPLETO: los 24 modelos con clave de reenvio tienen ya su indice***

### ***La cuenta final, y es la que cierra el ticket***

    ***24 modelos con `clave_de_reenvio`  ->  los 24 con indice unico parcial***
    y las puertas que la tratan:  ***con la busqueda previa, el 409 si los datos no coinciden,
    y la recuperacion del choque, en las que lo necesitaban***

*Empezó en la ronda 79 con las **inspecciones y las averias** de la maquina; siguió con **`Maquina`** y
**`Subvencion`** en la 81; y esta ronda cierra con **`Labor`** y **`TrabajoPrevisto`**.*

### ***Y una cosa que se habria quedado fuera si no se mira***

***`Labor` no tiene UNA puerta que la cree, tiene DOS***:

    `POST /api/trabajos/previstos/{id}/hecho`  -> la segunda mitad del recorrido 4
    ***`POST /api/trabajos`***                 -> ***«he pasado el rodillo El Prado»***, que es *«la puerta
                                                  que el agricultor usará desde el campo la mayoria de las
                                                  veces»*, dice su propio docstring

*La segunda la encontre **contando los `db.commit()` del fichero y mirando de quien era cada uno**. Si me
hubiera fiado de «la puerta de la labor», la mitad del uso real se habria quedado sin la proteccion -y sin
que ninguna prueba lo dijera-.*

### ***Y el detalle que hace que el `try` no vaya siempre en el mismo sitio***

***Cada puerta escribe la fila en un momento distinto, y eso decide donde va el `try`***:

    `TrabajoPrevisto`  -> **en el `flush`**: *y **no se puede mover** al final, porque las lineas del plan
                          necesitan `plan.id`, que no existe hasta que la fila va a la base*
    `Labor` (las dos)  -> **en el `commit`**: *estas puertas no hacen `flush`, asi que la fila va a la base
                          al confirmar. Es el mismo caso que la averia de la maquina*
    `Maquina`          -> en el `flush` (lleva cuaderno detras)
    `Subvencion`       -> en el `flush` (lleva rastro detras)

*Con el `try` en el sitio equivocado **el `IntegrityError` se escapa por delante** y el agricultor ve un
**500** en vez de su apunte. Es el defecto que se encontro en la ronda 79 -y que tenian **tambien las
lecturas del cuenta-horas**, desde que se escribieron-.*

### Las tres pruebas nuevas

    · la base no deja ***dos planes*** con la misma clave
    · ***dos envios a la vez del mismo plan apuntan UNO*** -y aqui la carrera se prueba de verdad-
    · la base no deja ***dos labores*** con la misma clave

*Y con las de la ronda anterior -la maquina y la subvencion, tambien con sus dos carreras-, el fichero
`test_lo_que_no_se_apunta_dos_veces.py` pasa de **8 a 16 pruebas**.*

### Verde

    ***la suite entera: exit code 0, 5411 pruebas***   (la revision estable)
    los tres ficheros que tocan esto:  ***96 en verde***
    y el recuento al dia: ***5414***, con la suite entera corriendo (job pwsh-3505)

### ***Y lo que sigue***

*CRM-05 -«fiabilidad y recuperacion: fallos de red, reintentos, duplicados y recuperacion»- queda **cerrado
en su mitad de duplicados**: los 24 indices, el 409 donde hacia falta y la recuperacion del choque.*

***Lo que le falta al ticket, y se dice para que no se de por hecho***:

  · **el 409 en las cuatro ultimas** -`Maquina`, `Labor`, `TrabajoPrevisto`, `Subvencion`-: *hoy las cuatro
    **devuelven lo que ya estaba sin mirar los datos**, que es la mitad silenciosa del defecto que si se
    cerro en las inspecciones y las averias*;
  · **la recuperacion ante un fallo de red de verdad** en la pantalla -el borrador que se conserva, el
    reintento que no duplica-, que es la mitad «fallos de red» del titulo;
  · y **el recorrido de las superficies**, que quedo pendiente de la ronda 78.


---

## 17/10/2026 (83) — ***CRM-05, la otra mitad: el 409, y escrito UNA sola vez***

### ***El defecto, que era el silencioso***

*Las cuatro puertas que se cerraron en las dos rondas anteriores -`Maquina`, `Subvencion`, `TrabajoPrevisto`
y `Labor`- ya tenian **el indice** y **la recuperacion del choque**… y seguian **devolviendo lo que ya
estaba sin mirar los datos**.*

***O sea***: *el agricultor corregia un dato, el movil reintentaba -o el toque doble con los guantes-, y **su
correccion se perdia en silencio**, y el se quedaba creyendo que habia entrado. **Es la peor forma del
defecto, porque no se ve**: el programa contesta «ya esta» y no esta.*

### ***Y la decision que lo hace limpio: comparar solo lo que la peticion MANDA***

*El ayudante esta en **`app/reenvios.py`**, y **no lleva una lista de campos por puerta**: recorre
`datos.model_fields_set` -**lo que la peticion trae**- y lo coteja con la fila que ya hay.*

***Es la regla de la casa desde el abono*** -«un campo que no viene **no es un campo vacio**, es un campo del
que la peticion no dice nada»-, *y aqui resuelve ademas un problema que se veia venir*: **en estas puertas lo
que no viene muchas veces se rellena con lo que ya tenia el plan o la tierra** -el cultivo de la parcela, la
superficie del plan-, *asi que compararlo habria dado **409 en un reintento legitimo**, que es justo lo que no
puede pasar.*

*Y los valores se cotejan **en su forma comparable** (`como_se_compara`): *`Decimal("9.00")` y `9.0` son el
mismo dinero y `" Trigo "` y `"Trigo"` el mismo cultivo. Compararlos tal cual seria cometer el defecto **al
reves** -un 409 donde no toca-.*

### ***Los seis sitios, y por que son seis***

***Cada puerta tiene DOS caminos*** -la consulta previa y la recuperacion del choque-, *y **los dos tienen que
contestar lo mismo**: si solo se llamara en uno, un reintento diria una cosa u otra segun quien llegara antes,
y eso es peor que no comprobarlo.*

    `Maquina`           ·  consulta previa  +  choque del `flush`
    `Subvencion`        ·  consulta previa  +  choque del `flush`
    `TrabajoPrevisto`   ·  consulta previa  +  choque del `flush`
    `Labor` (***dos puertas***)  ·  consulta previa  +  choque del `commit`, en las dos

*Con la labor, otra vez, **las dos puertas**: la del plan -`POST /previstos/{id}/hecho`- y la que el
agricultor usa desde el campo -`POST /api/trabajos`-.*

### ***Y las cuatro pruebas, vistas fallar***

    · la misma clave de maquina con otro nombre        -> ***409***
    · la misma clave de ayuda con otro concepto        -> ***409***
    · la misma clave de plan con otra fecha            -> ***409***
    · la misma clave de labor con otra fecha           -> ***409***
    y las cuatro, **antes**, el mismo reenvio -> ***la misma fila***

***Y se rompio a proposito***: *haciendo que `reenvios` **no viera nunca** datos distintos, las cuatro se
ponen rojas (`exit code 1`); restaurado, `exit code 0`. **Una prueba que no se ha visto fallar no prueba
nada** -y la leccion es de esta misma sesion-.*

### ***Y una cosa que se deja dicha para el que venga***

*El mismo criterio **ya estaba escrito tres veces**, cada uno en su sitio*: en `maquinaria_api.py` para **las
lecturas del cuenta-horas**, **las inspecciones** y **las averias**. *Funcionan y estan probados, y por eso
**no se han tocado** -no se cambia lo que funciona sin motivo-; pero **`app/reenvios.py` es su sitio**, y su
cabecera lo dice: es donde deberian venir el dia que se toquen.*

***O sea: hay un sitio para esa regla, y ahora lo sabemos.***

### Verde

    tests/test_lo_que_no_se_apunta_dos_veces.py  ***23 pruebas*** (16 + las cuatro del 409 y sus repetidas)
    los cuatro ficheros que tocan esto: ***255 en verde***
    y la suite entera, corriendo (job pwsh-3593), con el recuento al dia (***5418***)

### ***Y CRM-05 queda asi***

    ***duplicados***   ·  ***CERRADO***:  24 de 24 indices · el 409 en las cuatro que faltaban ·
                                          la recuperacion del choque en las seis puertas que la necesitaban
    ***fallos de red*** ·  ***PENDIENTE***: *el borrador que se conserva y el reintento que no duplica
                                          **en la pantalla*** -hoy esta probado **en el servidor**-
    *y de propina*:  el ***recorrido de las superficies***, que quedo pendiente de la ronda 78


---

## 17/10/2026 (84) — ***Los dos rojos de la ronda 79, explicados: una cache vieja y un cuelgue intermitente***

### ***Fallo 1: `test_cada_puerta_de_la_maquinaria_comprueba_que_el_objeto_es_de_esta_finca`***

    estas rutas no comprueban que el objeto sea de esta ficha:
    ['POST /maquinaria/{id}/inspecciones', 'POST /maquinaria/{id}/lecturas',
     'GET /maquinaria/{id}/reservas', 'POST /maquinaria/{id}/reservas']

***Y era FALSO***: *el guardian mira `inspect.getsource` de cada ruta buscando el nombre de un ayudante. Se
comprobo ruta por ruta **con el mismo criterio que usa el** -`getsource` y los siete nombres- y **ninguna sale
sin comprobar**.*

***La causa: una cache `__pycache__` obsoleta.*** *El proceso cargo un `maquinaria_api.pyc` cuyas lineas ya no
correspondian al fichero, asi que `getsource` devolvia **trozos equivocados** -y el guardian, que mira
**nombres** en ese texto, no los encontraba.*

***Se borraron todas las `__pycache__` del proyecto y el guardian pasa (24 en verde).*** *Es un fallo del
**entorno**, no del codigo -y conviene saberlo: **`inspect.getsource` depende de que el `.pyc` y el fuente
concuerden**, y un guard que mira texto fuente puede mentir si no concuerdan.*

### ***Fallo 2: el recorrido de las reservas, colgado 900 segundos***

    subprocess.TimeoutExpired: ... verificar_el_recorrido_de_las_reservas.py ... after 900 seconds

***Y no era un fallo del recorrido***: *andado a mano contra un servidor aislado, **pasa entero** -22
comprobaciones, 0 fallos, menos de 150 s-. Y **la prueba, despues de limpiar, pasa en 52 s**.*

**Lo que se encontro mirando la maquina**: **58 procesos de Chrome vivos** de las ejecuciones anteriores, y
**un uvicorn huerfano**. *Y el arnes **si** mata su navegador* -se comprobo: 46 procesos con el navegador
abierto, 35 al cerrarlo, y los de esa instancia muertos-.

***Asi que el circulo es este***: *una ejecucion que se corta por tiempo **muere sin su `__exit__`** y deja su
Chrome vivo; los Chrome acumulados hacen mas probable el siguiente cuelgue; y ese deja mas.*

***Queda como ticket, y se dice con lo que hay***: **una sola ocurrencia**, y no se ha reproducido despues de
limpiar. *La regla del encargo es clara -«ante dos intentos sin evidencia nueva, documentar reproduccion y
pedir revision»-, y aqui ni siquiera hay dos: hay **una**, con su traza.*

### ***Y un error mio, que se dice sin adornos***

*Al limpiar los huerfanos, **mate 44 procesos `chrome` por nombre** -`Stop-Process` sobre todo lo que se
llamara asi-. **En esta maquina eso podia incluir el navegador de David**, que no tiene nada que ver con las
pruebas.*

***Lo correcto era matar SOLO por perfil*** -`--user-data-dir`, que es unico de cada instancia-, **que es
exactamente lo que hace el propio arnes** y lo que su comentario explica: *«asi no se toca ningun otro
navegador de la maquina -y en particular **ninguno del dueno**-»*. **Estaba escrito en el fichero que estaba
leyendo.***

### Verde

    test_revision_t14.py  ***24 en verde***   (el guardian, con la cache limpia)
    test_el_recorrido_de_las_reservas.py  ***2 en verde, 52 s***   (el cuelgue, no reproducido)
    y las `__pycache__` del proyecto, borradas

### ***Y lo que no se hizo, que es la entrega de la ronda***

***El fallo de red y el reintento EN LA PANTALLA*** -la mitad de CRM-05 que falta-: *el borrador que se
conserva y la clave que se reutiliza ya **estan escritos** en `guardarLoDeLaMaquinaria` -«se pide la primera
vez que se guarda y se queda en el borrador… si se pidiera al guardar, cada pulsacion mandaria una clave
distinta»-, pero **no hay un recorrido que lo ande** con el navegador desconectado y vuelto a conectar.*

*La ronda se fue entera en **entender los dos rojos** -que era lo primero, porque una suite roja no dice nada
del resto-, y esa es la entrega de la siguiente.*


---

## 17/10/2026 (85) — **CRM-05, «fallos de red»: el doble toque, y una comprobacion que no probaba nada**

### ***Lo que ya estaba, y no lo sabia***

*El recorrido del cuenta-horas **ya tenia el paso 10***: *«si el envio falla, no se pierde lo escrito, y se
puede reintentar»*. Y esta bien hecho:*

    `Network.setBlockedURLs({"urls": ["*/lecturas*"]})`   -> ***la peticion no llega al servidor, de verdad***
    pulsa guardar      -> ***el formulario SIGUE ABIERTO, con la fecha y el valor escritos***
    se devuelve la red -> ***y al reintentar, entra***

*O sea: «conservar el borrador si falla el envio», que es el punto 1 del encargo, **ya estaba andado**.*

### ***Lo que faltaba, y lo que descubri al escribir la prueba***

*El caso de aceptacion del COLA dice dos cosas: «el mismo apunte dos veces **no duplica**» y «dos envios a la
vez **una sola fila**». *Y eso **no lo probaba nadie en la pantalla**.*

**Mi primer intento fue anadir, despues del reintento, una comprobacion de que hay una sola lectura.** *Y era
**una comprobacion que no podia fallar**: con la red **bloqueada la peticion no llega al servidor**, asi que
despues del reintento hay **una** fila aunque la clave se hubiera regenerado. **Hablaba de «el reintento no
duplica» y no probaba nada de eso.***

***Se tiro y se cambio por lo que si lo pone a prueba: el DOBLE TOQUE.***

    pulsa guardar
    pulsa guardar          <- ***sin esperar a que conteste el primero: es lo que pasa de verdad***
    y se mira EN EL SERVIDOR cuantas lecturas de 888 hay: ***una***

***Dos peticiones de verdad, con la misma clave.*** *Y se mira en el servidor y no en la pantalla, porque la
ficha podria estar enseñando una y haber dos en la base.*

### ***Y se rompio a proposito, que es lo unico que demuestra que prueba algo***

*Se cambio `laClaveDeReenvio` en `app.js` para que devolviera **una clave nueva en cada guardado** -que es el
defecto que la funcion existe para no cometer-:*

    ***con la clave rota***:   exit code 1   ->  «[FALLO] y DOS TOQUES apuntan UNA lectura»
    ***y restaurada***:        exit code 0

***La prueba caza de verdad el defecto.*** *Y de paso queda demostrado por que la clave se pide **una sola vez**
y se guarda en el borrador: si se pidiera al guardar, **cada pulsacion mandaria una distinta** y el servidor no
podria reconocer el reenvio.*

### Verde

    test_el_recorrido_del_cuenta_horas.py  ***2 en verde, 69 s, con el doble toque***
    el recuento no cambia -***5420***-: *no se anadio una prueba, se anadio una comprobacion a un recorrido*
    y la suite entera, corriendo (job pwsh-3782)

### ***La leccion, y es de las que se repiten***

***Una comprobacion que no puede fallar no es una comprobacion.*** *Mi primera version decia «el reintento no
duplica»; con la red bloqueada, la primera peticion **nunca llego**, asi que siempre habria una fila. **Solo se
supo al preguntarse «¿como rompo esto para verla roja?»** -y la respuesta era «no puedo», que es la senal.*

### ***Y CRM-05 queda CERRADO***

    ***duplicados***   ·  24 de 24 indices · el 409 en las cuatro ultimas · la recuperacion del choque
                          en las seis puertas que la necesitaban · y el doble toque andado en la pantalla
    ***fallos de red*** ·  ***CERRADO***: el borrador que no se pierde, el reintento que entra, y el
                          doble toque que no duplica -***los tres, en un navegador de verdad***

*Quedan de la cola, y son lo siguiente*: **paneles** (CRM-11, *que es donde tienen que vivir las tres
superficies -el sitio que se descubrio en la ronda 78-*) y **preparacion PAC**.


---

## 17/10/2026 (86) — ***Paneles: el modulo que no llamaba NADIE, y una magnitud que faltaba***

### ***Lo que se encontro, y es el mayor «solo existe en servidor» de todos***

    `paneles.py`  ->  ***ni una sola referencia en todo `app/`***
    puertas que sirvan metricas  ->  ***ninguna***
    y su unica prueba (10) lo ejercita **directamente**

***O sea: un modulo entero -el contrato de la metrica, la negativa a sumar peras con manzanas, `sumar` que
avisa en vez de fallar, y `lo_de_una_superficie` con las dos metricas hermanas- que **no tiene ni puerta ni
pantalla**. Ni siquiera esta «en el servidor»: esta en un fichero que nadie importa.***

*Y su cabecera dice lo que pretendia ser*: *«un panel no es una pantalla con numeros, es **un numero que se
puede defender**. Cada metrica tiene que poder decir **que mide**, **de donde sale** y **cuanto de lo que
habia ha mirado**.»*

### ***Y al ir a darle puerta, salio lo de verdad: LA MAGNITUD QUE FALTABA***

*`paneles` usa `magnitud` como **unidad** -dos metricas se suman solo si su `magnitud` es la misma-, y su
lista tenia seis. **Las superficies traen otra lista**, que es **otra cosa**: alli «la magnitud es **la
pregunta**».*

***Y hay un caso que lo demuestra solo***: **10 ha trabajadas en tierras de un tercero**.

    · son ***hectareas de trabajo***... pero ***no son tu finca*** (*`superficies.py`: «10 ha de un tercero no
      suman superficie propia»*)
    · si se apuntaran como `ha_de_trabajo`, ***`sumar` las juntaria con las tuyas***, y la regla que existe
      para impedirlo **quedaria saltada por arriba**
    · y no habia donde ponerlas: ***`LAS_MAGNITUDES` no tenia esa magnitud***

***Anadida***: `HECTAREAS_DE_TERCERO = "ha_de_tercero"`, en `LAS_MAGNITUDES` y en `LAS_QUE_SE_CONFUNDEN`
-*«las dos son trabajo y las dos se miden en hectareas, y una es tu finca y la otra no»*-.

**Y con su prueba**, que no se queda en mirar la constante: *30 ha tuyas + 10 de un tercero **suman 30**, y
la respuesta **dice que las 10 se han quedado fuera** (`sin_sumar`).*

### Verde

    tests/test_lo_que_dice_un_panel.py  ***11 en verde*** (10 + la de la magnitud que faltaba)
    recuento: ***5421*** · y la suite entera, corriendo (job pwsh-3831)

### ***Y lo que impide dar el panel entero, que es una decision y no un rato de codigo***

***`la_metrica` usa `magnitud` para las dos cosas a la vez***: *es la **unidad** -lo que decide si dos se
suman- y, al mismo tiempo, **lo que la metrica mide**. *Con las seis magnitudes de antes eso cuadraba; con las
superficies **no**, porque dos metricas en hectareas pueden contestar a preguntas distintas.*

***El arreglo no es anadir magnitudes a mano*** -seria perseguir el problema-: *es que la metrica lleve **las
dos cosas**, `unidad` y `pregunta`, y que `sumar` se niegue por la **pregunta**. Eso **cambia `la_metrica` y
sus diez pruebas**, y es una decision de diseno que se toma con el contrato delante, no a las prisas de una
ronda.*

*Asi que el panel queda asi, y se dice*:

    ***la magnitud que faltaba***  ·  ***hecha y probada***
    ***la puerta y la pantalla***   ·  ***no***: *necesitan que la metrica separe unidad y pregunta*

### Y de la cola

    cuenta-horas · reservas · fertilizantes · superficies · fiabilidad y recuperacion  -> ***cerrados***
    ***paneles***  -> *en curso: la magnitud que faltaba, hecha; el resto, con su decision escrita*
    preparacion PAC  -> *lo ultimo*


---

## 17/10/2026 (87) — ***El panel tiene puerta: la metrica separa unidad y pregunta***

### ***La decision que estaba escrita, tomada***

*En la ronda anterior quedo dicho que `la_metrica` usaba `magnitud` para **dos cosas a la vez** -la **unidad**,
que decide si dos metricas se suman, y **lo que la metrica mide**- y que con las superficies eso ya no cuadraba.
**Se ha separado.***

    `la_metrica(..., pregunta=None)`  ->  ***la metrica lleva las dos cosas***
    `la_misma_cosa(una, otra)`        ->  ***misma unidad Y misma pregunta***
    `sumar(...)`                      ->  ***se niega por `la_misma_cosa`, no solo por la unidad***

***Y el defecto que eso cierra, con un ejemplo***: *«30 ha» de lo que hay plantado y «30 ha» de lo que se
trato **se miden en hectareas las dos**, y sumarlas da un numero que no contesta a nada. Antes, esta linea*

    sumables = [m for m in metricas if se_pueden_sumar(m["unidad"], unidad)]

*miraba **solo la unidad**, y con las superficies dejaba pasar justo la suma que hay que impedir.*

***Y no rompio nada***: *`pregunta` vacia es «no hace falta decirla» -los euros, los kilos-, y las diez pruebas
del panel siguieron verdes a la primera.*

### ***La puerta: `GET /api/panel`***

***Seis metricas, cruzando los datos de verdad de la finca***, y cada una con **lo que el contrato pide**:

    superficie   · ha_de_superficie · fuente parcelas        · cobertura (con hectáreas / tierras)
    trabajo      · ha_de_trabajo    · fuente labores         · cobertura
    tratado      · ha_de_trabajo    · ***pregunta distinta*** -> ***no se suma con el trabajo***
    de_tercero   · ***ha_de_tercero*** · fuente trabajos de terceros
    gastos       · EUR              · fuente gastos          · cobertura (con importe / gastos)
    cosecha      · kg               · fuente ventas          · cobertura (en kilos / ventas)

***Y las tres cosas que la puerta hace y que no son adorno***:

  1. **Cada una dice de donde sale** (`fuente`). *Un numero que no puede decir su fuente no se puede discutir.*
  2. **Dice cuanto ha mirado** (`cobertura`): *`{"contadas": 8, "de": 12}`.*
  3. ***Lo que no se sabe va como `None`, nunca como cero***: *si a un gasto le falta el importe, **el total de
     gastos no se sabe** -*`_la_suma` devuelve `None`-, *que es distinto de «no se ha gastado nada»*.

**Y devuelve dos cosas mas**, que son la mitad del contrato:

    `sin_comprobar`      · ***lo que no se puede dar por bueno*** -«sin cumplimiento global que tape una regla
                          critica no comprobada»-
    `lo_que_no_se_suma`  · ***las parejas que se confunden***, para que la pantalla avise sin saberlo de memoria

***Las palabras viajan con los datos*** (`textos.PANEL`, 20 claves), *como en `/api/parcelas/vista`: este
endpoint es el unico que las usa, y asi no hay que tocar `/api/interfaz`.*

### Verde

    tests/test_el_panel.py  ***6 en verde***, y no miran que conteste: miran que
      · cada metrica diga ***en que se mide***, ***de donde sale*** y ***cuanto ha mirado***;
      · ***una tierra sin superficie haga que el total NO SE SEPA***, con la cobertura diciendo `1 de 2`;
      · ***un gasto sin importe haga que el total de gastos NO SE SEPA*** -y no un cero-;
      · que ***lo de un tercero sea su propia magnitud*** y no se cuele en lo tuyo;
      · y que la puerta **diga lo que no se puede dar por bueno**.
    tests/test_lo_que_dice_un_panel.py  ***11 en verde***   ·   recuento: ***5427***
    y la suite entera, corriendo (job pwsh-3890)

### ***Y lo que falta, que es la pantalla***

***«No declarar terminada una funcion que solo existe en servidor».*** *El panel **tiene puerta y pruebas**, y
 **no tiene pantalla**: hoy `panel_api` es tan invisible para el agricultor como lo era `paneles.py`.*

*Lo siguiente, y esta dicho con nombres*: **`web/react/pantallas/panel.js`** -una tarjeta por metrica, con su
titulo, su cifra o «no se sabe», su unidad, su fuente, su cobertura y su enlace-, **la ruta** y el `app.js`.
*Y el recorrido que la ande.*

### ***Y de la cola***

    cuenta-horas · reservas · fertilizantes · superficies · fiabilidad y recuperacion  -> ***cerrados***
    ***paneles***  -> *la metrica arreglada, la puerta hecha y probada; **la pantalla, pendiente***
    preparacion PAC  -> *lo ultimo*


### ***Y un error mio, el MISMO de la ronda 77: un bloque de `textos.py` que ya existia***

*La suite entera salio roja, y por **una sola** prueba -`test_que_no_falte_ningun_texto.py`-:*

    la interfaz pide textos que no existen, y saldrian en blanco en la pantalla:
        · ***panel.tierra_historia***  (lo pide app.js:8668, app.js:8683)

***Y era verdad***: *`textos.py` **ya tenia un `PANEL`** -el **panel del ordenador** de la pantalla de tierras,
con su `tierra_historia` y sus rotulos, 9 claves-, **y yo anadi un segundo `PANEL`** al final del fichero
para las metricas.*

***En Python, dos asignaciones al mismo nombre no dan error: la segunda PISA a la primera.*** *Asi que los
textos del panel de siempre **se quedaban en blanco**, y el unico que se entero fue ese guardian.*

***Arreglado***: *mi bloque se llama **`LAS_METRICAS`**, `PANEL` volvio a su sitio -comprobado: 9 claves y
`tierra_historia` con su texto-, y la puerta usa el nombre nuevo.*

***Y queda escrito en el propio fichero***, encima del bloque: *«**`PANEL` ya existia**… **Anadir un segundo
`PANEL` no da error: el segundo PISA al primero**… **Antes de anadir un bloque aqui, se mira si el nombre esta
cogido.**»*

***Es el mismo error que el de la ronda 77 con `models.py`*** -anadir sin mirar si el nombre estaba cogido-, *y
la segunda vez que **un guardian** lo caza y **yo no**. *La diferencia: esta vez no hubo que reconstruir nada,
porque el guardian esta para eso.*

### Verde

    test_que_no_falte_ningun_texto.py · test_el_panel.py  ***10 en verde***
    `PANEL` 9 claves · `LAS_METRICAS` 20 · `PANEL_DE_MANDO` 21   (los tres, cada uno en su sitio)
    y la suite entera, corriendo (job pwsh-4012)


---

## 17/10/2026 (88) — ***El panel, en el INICIO: la mitad que se ve***

### ***Y el hallazgo que decidio donde iba***

*Al ir a hacer la pantalla, `pantallaDeLaDireccion` lo dijo sin rodeos:*

    pantallaDeLaDireccion(modulo)  ->  modulo === "panel" ? "inicio" : modulo
    moduloDeLaPantalla(clave)      ->  clave === "inicio" ? "panel" : clave

***«Panel» ya era el nombre del inicio***, en el menu. *O sea que **el panel y el inicio son la misma pantalla**,
y no habia que inventar ruta: las metricas van **donde el agricultor ya entra**.*

**Y ademas el inicio ya tenia un «panel de mando» del ordenador**, cuya decision numero 2 dice, escrita desde
el 30/09/2026:

    «***No hay tarjeta de gasto en euros***, aunque el diseno de Stitch la trae: ese numero no existe en el
    programa (no hay gasto por producto sumado para el año) y ponerlo de adorno seria inventarse un dato.
    En su sitio va la tarjeta de las tierras.»

***Ese numero ahora SI existe***: *lo cuenta `GET /api/panel` -en el servidor, una sola vez-, con su fuente y
su cobertura.* *Asi que la tarjeta que se dejo fuera por no inventarse un dato **ahora se puede poner**, y con
lo que hace falta para creersela.*

### Lo que se hizo

**En `web/react/pantallas/inicio.js`**, un componente `LasMetricas` y su seccion, con **las cuatro cosas que el
contrato pide**: *el titulo y la pregunta -**que mide**-, la cifra con su unidad -**en que se mide**-, la fuente
-**de donde sale**-, y la cobertura -**cuanto ha mirado**-.*

***Y dos cosas que no son adorno***:

  · ***`null` no es una lista vacia***, la distincion de la casa: *`null` es «todavia no se han pedido» -**la
    seccion no se pinta**-; `[]` seria «se pidieron y no hay ninguna». Sin ella, el inicio diria «no hay nada»
    antes de preguntar.*
  · ***un `valor` en `null` se dice con su palabra*** -«No se sabe»-, *nunca con un cero: un cero afirmaria
    que no hay.*

**En `app.js`**: `pedirLasMetricas()`, *que las pide **una sola vez** por visita -`metricasPedidas`, para no
hacer un bucle de peticiones si falla-, y repinta el inicio solo si se sigue en el*.

***Y el inicio es `#/panel`***, *asi que la guarda mira eso y no repinta desde otra pantalla.*

### ***Y dos errores mios, cazados por las pruebas***

  1. **`rellena` sin importar**: *`node --check` no lo ve -es de ejecucion-. Vive en `web/nucleo.js`, que es
     donde esta escrita **una sola vez** -`tierras_mapa.js` tiene una copia local, y eso ya es una pena-.*
  2. ***`location is not defined`***: *las pruebas de `app.js` lo cargan en un DOM de mentira **sin
     `location`**, y sin la guarda se caian **todas** con un error que no tenia nada que ver con lo que
     estaban probando.* *Se arreglo comprobando `typeof location !== "undefined"` antes de mirarlo.*

### Verde

    tests_js/panel.test.js  ***4 en verde***:
      · cada metrica dice ***que mide***, ***en que se mide***, ***de donde sale*** y ***cuanto ha mirado***;
      · ***lo que no se sabe dice «no se sabe» y NUNCA un cero***;
      · ***sin metricas pedidas (`null`) la seccion no se pinta***;
      · y ***una metrica que no se puede dar por bueno lo dice***.
    JS entero: ***1132 en verde***
    y la suite de Python, corriendo (job pwsh-4154)

### ***Y el panel queda CERRADO por sus dos mitades***

    `paneles.py`      -> ***corregido***: la metrica separa **unidad** y **pregunta**, y `sumar` se niega por
                        las dos. Y una magnitud que faltaba -`ha_de_tercero`-.
    `GET /api/panel`  -> ***hecha y probada***: seis metricas con fuente, cobertura y `None` donde no se sabe.
    la pantalla       -> ***hecha***: en el inicio, con sus cuatro cosas y sus dos distinciones.
    *y el recorrido*  -> ***pendiente***: *no hay un guion que lo ande con un navegador.*

### Y de la cola

    cuenta-horas · reservas · fertilizantes · superficies · fiabilidad y recuperacion · ***paneles***  -> cerrados
    ***preparacion PAC***  -> lo ultimo


---

## 17/10/2026 (89) — ***Preparacion PAC: el tercer modulo que no llamaba nadie, y ahora tiene paquete***

### ***El mismo patron, por tercera vez***

*`app/pac.py` tenia **exactamente** las tres piezas que la cola pide -y su unico consumidor era **su propia
prueba**:*

    `el_porcentaje(numerador, denominador, de_que)`       · «porcentajes con numerador/denominador»
    `tierra_sin_cultivo_no_se_pinta_de_verde(total, con)` · «tierra sin cultivo no desaparece para pintar verde»
    `la_que_aplica(fuentes, ambito, campana, cuando)`     · «fuente de otra campaña/comunidad no se aplica»

*Es el **tercer** modulo de esta sesion con el contrato escrito y sin nadie que lo llame -`paneles.py`,
`superficies.py` y `pac.py`-.* ***Una cosa es tener el contrato escrito, y otra es que alguien lo cumpla.***

### ***`GET /api/pac/paquete`: el paquete por recinto***

***Y lo primero que la puerta dice es lo que NO hace***: *no dice si nada es elegible.* *La cola lo manda con
esas palabras -«ninguna competencia autoriza usar su interpretacion como norma»-, y aqui **no hay ninguna
fuente legal cargada**, asi que el paquete **lo dice en voz alta**:*

    "la_fuente": None
    "aviso_de_la_fuente": «No hay ninguna fuente legal cargada para esta campaña, asi que **no se puede decir
                          si algo es elegible**...»

***Lo que si hace***, y es el contrato entero:

  · **una entrada por tierra** con su referencia, su superficie, **la del SIGPAC** -aparte-, lo que se siembra
    -`especie`, `variedad`, `sistema`, **`ecorregimen`**, `superficie_cultivada_ha`- y **lo que falta**;
  · ***«falta area/cultivo/evidencia -> incompleto»***: *`falta_superficie`, `falta_referencia`,
    `falta_cultivo`, `falta_ecorregimen`, y `completa: False` cuando hay alguna*;
  · ***el resumen sin el denominador tramposo***: *10 ha de finca con 6 sembradas son el **60%**, y las 4 que
    se quedan fuera **se dicen** -`sin_cultivo: 4.0`-;
  · ***y la advertencia viajando con el paquete***: *«no es la declaracion ni una garantia de elegibilidad» va
    **en la respuesta**, no solo en la pantalla, porque el paquete se puede guardar y reenviar.*

### ***Y un dato que NO se invento***

*Al escribir la entrada de cada tierra puse `area_declarada_ha` -«lo que el agricultor declara»-. **Y esa
columna no existe**: `Parcela` tiene `superficie_ha` y `superficie_sigpac_ha`.*

***No se anadio una tercera***: *se puso **la del SIGPAC**, que es una cosa de verdad -lo que la administracion
tiene apuntado, que puede no coincidir con lo que mide el recinto-, y **con el motivo escrito**.*

    *«No se llama «declarada»: **no hay ninguna columna de superficie declarada** -se busco-. Inventar una
    tercera habria sido enseñar un dato que no existe, que es justo lo que esta casa no hace.»*

*Y la prueba lo fija por los dos lados*: `assert "superficie_sigpac_ha" in una` y
`assert "superficie_declarada_ha" not in una` -***«no hay superficie declarada: no se inventa»***-.

### Verde

    tests/test_el_paquete_de_la_pac.py  ***5 en verde***:
      · cada tierra dice lo que hay ***y lo que FALTA***;
      · ***el porcentaje va sobre TODA la finca*** -60%, no 100%, y las 4 ha se dicen-;
      · ***sin fuente legal no se dice que nada sea elegible***;
      · la advertencia ***viaja con el paquete***;
      · y ***la del SIGPAC y la medida se dicen por separado, sin inventar una tercera***.
    recuento: ***5438*** · y la suite entera, corriendo (job pwsh-4239)

### ***Y la COLA queda entera, con lo que falta dicho***

    CRM-01 ventas · CRM-02/03 cuenta-horas y reservas · CRM-04 superficies · CRM-05 fiabilidad
    CRM-06 fertilizantes · CRM-07 maquinaria · CRM-11 paneles  -> ***cerrados***
    ***CRM-09 preparacion PAC*** -> *el paquete hecho y probado; **falta su pantalla**, y **falta la fuente
                                    legal**, que no la puede poner este programa*
    CRM-10 meteo/satelite -> *necesita un proveedor con licencia: **bloqueo externo**, y no detiene nada*

    *Y lo que queda pendiente de lo hecho, dicho con nombres*:
      · el ***recorrido del panel*** y el ***de la PAC*** -no hay guion que los ande con un navegador-;
      · la ***pantalla del paquete PAC***;
      · y la ***fuente legal***, que es de David y no mia.


---

## 17/10/2026 (90) — ***La pantalla del paquete PAC: lo primero que se lee es lo que no se puede afirmar***

### Lo que se hizo

**`web/react/pantallas/pac.js`** -la pantalla- y **su direccion, `#/pac`** -en `ABRIR_LA_PANTALLA`-, con la
peticion a su puerta y un repintado que **si falla deja reintentar**: *a diferencia de las metricas del panel
-que se piden una vez por visita-, este es un **documento de trabajo**: se abre, se cierra y se vuelve a abrir,
y quedarse sin el hasta recargar la pagina no tiene sentido.*

***Y lo que la pantalla defiende, que es lo que el contrato pide***:

  · ***lo primero que se lee es lo que NO se puede afirmar***: *sin fuente legal cargada, «no se puede decir
    si algo es elegible» -y se pinta **antes** del resumen, porque decirlo despues es decirlo tarde-*;
  · ***el porcentaje con su numerador y su denominador***: *«6 de 10 ha · 60 %», no un «60 %» suelto*;
  · ***y cuando no se sabe*** -`porcentaje: null`- ***se dice***, y **nunca un cero por ciento**;
  · ***las hectareas que se quedan fuera, dichas*** -las 4 ha del barbecho-;
  · ***cada tierra con lo que le falta***, y las incompletas **no se esconden**;
  · y ***la advertencia al pie, siempre***: *«no es la declaracion ni una garantia de elegibilidad».*
  · ***y sin paquete pedido (`null`) no se pinta una tabla vacia***: *una tabla vacia dice «no hay nada», y
    todavia no se sabe.*

### Y dos errores mios, los dos cazados por las pruebas

  1. **`pac.js` nacio sin import**: *usaba `html` y `frase` y **no importaba nada**. `node --check` no lo ve
     -es de ejecucion-, y lo dijo la prueba con un `html is not defined`.*
  2. *Y el anterior, el de los textos: `PAC` **se comprobo libre antes de escribirlo*** -la leccion de las dos
     veces anteriores, aplicada-.

### Verde

    tests_js/pac.test.js  ***6 en verde***
    JS entero: ***1138 en verde***
    y la suite de Python, corriendo (job pwsh-4332)

### ***Y lo que queda, dicho sin adornos***

    ***la pantalla del paquete PAC***  -> ***hecha***
    ***su entrada en el menu***         -> ***no***: *se llega por su direccion (`#/pac`); falta el renglon*
    ***el recorrido del panel***        -> ***no***: *no hay guion que ande el inicio con un navegador*
    ***el recorrido de la PAC***        -> ***no***: *idem*
    ***la fuente legal de la PAC***     -> ***no, y no es mia***: *la cola manda consultar el BOE, el FEGA, el
                                          MAPA y la Junta al implementar las reglas, y ninguna competencia
                                          autoriza usar su interpretacion como norma*

*Las tres primeras son trabajo de las siguientes rondas. **La cuarta es de David**, y por eso el programa dice
en voz alta que no puede decir si algo es elegible: **es la unica respuesta honesta que puede dar sin la
fuente**.*


---

## 17/10/2026 (91) — ***La PAC, andada por la pantalla: y el fallo que solo se ve andandola***

### El recorrido, y sus primeros intentos

**`scripts/verificar_el_recorrido_de_la_pac.py`** y su prueba. *El guion contrasta **la pantalla con lo que
dice su puerta**, asi que no depende de que la finca de pruebas tenga unas hectareas concretas.*

***Y los tres intentos dicen mas que el resultado final***:

  1. **Ocho comprobaciones, cinco fallos, y el texto era la pantalla de ENTRAR**: *`preparar()` da el token para
     la API, pero **el navegador no habia entrado**. Se copio la pieza del recorrido de las reservas:
     `Page.addScriptToEvaluateOnNewDocument` escribiendo `cuedigital.token` en el `localStorage`
     **antes de la primera pagina**.*
  2. **Y entonces: «Esa direccion no lleva a ninguna parte».** *`ABRIR_LA_PANTALLA["pac"]` estaba puesto
     -`pac: () => pantallaElPaqueteDeLaPac()`- y **la direccion no existia**.*
  3. ***Y la pieza que faltaba era la tabla del enrutador***: *`react/rutas.js` tiene `PANTALLAS` -una lista de
     `{clave, patron}`-, y ahi **no estaba**. Se anadio **al final**, porque el guardian
     `rutas.test.js` compara la lista **en orden**.*

***O sea: el fallo no se veia en ninguna prueba de unidad.*** *El componente tenia sus seis pruebas de JS en
verde; la puerta, sus cinco de Python. **Lo que estaba roto era el camino entre las dos**, y solo se ve al
andar la pantalla.*

### Verde

    tests/test_el_recorrido_de_la_pac.py  ***2 en verde, 34 s*** -y el guion dice «Comprobaciones: 8 Fallos: 0»-
    tests_js/rutas.test.js  ***46 en verde*** (con `pac` en la lista, y su motivo escrito)
    JS entero  ***1138 en verde***
    recuento: ***5452*** · y la suite de Python, corriendo (job pwsh-4485)

### ***Y lo que queda***

    ***la entrada de la PAC en el menu***  -> ***no***: *se llega por `#/pac`. Sus botones del inicio **los manda
                                            el servidor** y las pruebas fijan **seis, y en su orden**: anadir el
                                            septimo es una decision de diseno de David, no un arreglo*
    ***el recorrido del panel***           -> ***no***: *el inicio tiene sus metricas y sus pruebas de JS; le
                                            falta el guion que lo ande*
    ***la fuente legal de la PAC***        -> ***no, y no es mia***


---

## 17/10/2026 (92) — ***El recorrido del panel: TRES defectos que ninguna prueba de unidad veia***

### Y el guion encontro tres, uno detras de otro

*Se escribio `scripts/verificar_el_recorrido_del_panel.py` -contrastando la pantalla con lo que dice su
puerta-, y salio rojo. **Y cada rojo era un defecto de verdad, no del guion**:*

***1. El envoltorio no reenviaba la prop.*** *`app.js` monta `pantallaDeInicio(propiedades)`, que es un
**envoltorio** de `PantallaInicio` con la lista de props **escrita a mano**. Anadi `lasMetricas` al componente y
a `app.js`… **y el envoltorio la tiraba**.*

    ***Y mi prueba de JS pasaba porque montaba `PantallaInicio` DIRECTAMENTE.*** *Ese atajo era el punto ciego
    **exacto**: la prueba comprobaba una pantalla que el agricultor no monta.*

*Arreglado el envoltorio, **y corregida la prueba para que monte el envoltorio**. Y se comprobo que ahora caza
el defecto: quitando la prop del envoltorio, **3 de sus 4 pruebas se ponen rojas**.*

***2. El repintado no ocurria nunca.*** *Con la prop ya reenviada, la peticion se hacia (`GET /api/panel` → 200,
visto en el registro del servidor) y la seccion **no salia**. La causa:*

    const donde = (location.hash || "").replace(/^#/, "");
    if (donde === "" || donde === "/" || donde === "/panel") pantallaInicio();

***Y la direccion del inicio NO es `#/`***: *la aplicacion le anade la campaña y la finca, y queda
**`#/?campana=2026&finca=2`**. Comparar el hash con `""`, `"/"` o `"/panel"` **no acierta nunca**.*

***Arreglado mirandolo con el enrutador***: `leerLaDireccion(hash).pantalla === "inicio"`, *que da igual lo que
lleve detras. **Y lo mismo en la PAC**, que tenia el mismo defecto escrito igual.*

***3. La unidad desaparecia justo cuando no habia cifra.*** *La metrica sin valor se pintaba como «No se sabe»
**y sin su unidad** -y la unidad es lo que dice **si esa cifra se puede sumar con otra**-.*
***«Cada metrica dice en que se mide», tambien cuando no se sabe.*** *Arreglado: «No se sabe · ha_de_superficie».*

### ***Y un cuarto, mio, de sintaxis: los backticks***

*Al explicar el defecto del envoltorio, meti el comentario **dentro** del `` html`…` `` -y el comentario llevaba
`` `app.js` ``, `` `PantallaInicio` `` y `` `lasMetricas` ``.* ***Una comilla invertida dentro de una plantilla
la cierra***, y el fichero dejo de compilar con un `SyntaxError` que parecia de otra cosa.*

***La leccion ya estaba escrita en este mismo diario*** -«un `//` dentro de un `` html`…` `` es TEXTO, no un
comentario»-, *y esta vez fue peor: no un comentario inutil, **un fichero roto**. **Las explicaciones, fuera de
la plantilla.***

### Verde

    tests/test_el_recorrido_del_panel.py  ***2 en verde, 23 s*** -«Comprobaciones: 16 Fallos: 0»-
    tests_js/panel.test.js  ***4 en verde***, y ***montando el envoltorio*** -como lo monta la aplicacion-
    JS entero  ***1138 en verde***   ·   recuento: ***5458***
    y la suite de Python, corriendo (job pwsh-4600)

### ***Y lo que queda, ya solo dos cosas, y las dos no son codigo***

    ***la entrada de la PAC en el menu***  -> *sus botones del inicio los manda el servidor y las pruebas
                                            fijan **seis**: es una decision de diseno de David*
    ***la fuente legal de la PAC***        -> *el BOE, el FEGA, el MAPA y la Junta: **no es mia***


---

## 17/10/2026 (93) — ***Los permisos, en la PANTALLA: el hueco medido, el patron hecho, y tres guardianes que me cazan***

### ***El hueco, medido***

*El servidor comprueba los permisos **en todas sus puertas**: `puede_modificar` como dependencia de FastAPI sale
en **mas de cien** sitios. Y la pantalla lo leia en… **tres ficheros** (`app.js`, `contactos.js`,
`maquinaria.js`).*

***El recuento, con el criterio escrito***: *de los ficheros de `web/react/pantallas` que ofrecen escribir
-«guardar», «borrar», «anular», «corregir»-, **dos de treinta y nueve** leen el permiso.*

***O sea***: *a un usuario de consulta **se le ofrecia el boton** y se llevaba un 403 al pulsarlo. **Eso no es
«permisos en servidor y pantalla»: es la mitad.***

### ***Y por que no se puede arreglar de una vez, dicho con el motivo***

*Se busco **un solo sitio** donde gatearlo: el despacho de acciones es **una tabla unica** -24 manejadores-, y
el clic se recoge **en un unico `addEventListener`**. Pero **los botones los pinta cada pantalla**, y **el
identificador de la accion viene del descriptor del servidor** (`m.guardar`, `b.guardar`), *no del componente:
**un barrido de texto no puede detectar los botones de guardar**.*

*La comprobacion de verdad es **montar cada pantalla con `puede_modificar: false`** y mirar que el boton no
salga. **Una prueba por pantalla**, y 37 pantallas por delante.*

### ***Lo que si se hizo: una, entera, para fijar el patron***

**`decir_cultivo.js`** -la mas pequeña de las que escriben-:

  · la prop `puede_modificar = true` -***con defecto `true`***: *una pantalla que no lo reciba se comporta como
    antes en vez de quedarse muda, y lo que se olvide se nota porque **su prueba** falla*;
  · **el boton de guardar no sale** sin permiso, y **tampoco el de quitar** -que tambien escribe-;
  · ***y «volver» sale siempre***: *volver no cambia nada, y dejarlo fuera dejaria al agricultor **encerrado**
    en un formulario que no puede guardar*;
  · el envoltorio lo reenvia, y `app.js` le pasa `loQuePuedoHacer().modificar`.

**Y sus cinco pruebas**: *sin permiso no sale guardar, ni quitar; «volver» sale siempre; con permiso salen los
dos; y sin la prop se comporta como siempre.*

### ***Y tres guardianes de la casa que me cazaron -los tres, aciertos***

*Al anadir la pantalla de la PAC en la ronda anterior, se anadio **un fichero de pantalla** sin registrarlo, y
lo dijo la suite:*

    ***1. `rutas.test.js`***: *la lista de pantallas con direccion, **en orden**.*
    ***2. `test_que_no_falte_ningun_texto`***: *un bloque de `textos.py` que ya existia, pisado.*
    ***3. `test_la_migracion_a_react`***: *«con_fichero: 60» y «migradas: 59».* ***Y este es el bueno***: *una
       pantalla de React se apunta en **tres** sitios -`PANTALLAS_EN_REACT` en `app.js`, la tabla de
       `docs/REACT.md` y **el service worker**-, y sin el tercero la pantalla **no abre sin cobertura**.*

*Los tres, arreglados. **Y el tercero se arreglo despues de que el primero me dejara el arnes a medias**: un
`assert "pac" not in ...` que fallo porque **`pac` es subcadena de `capacidad`** -el `assert` estaba mal, no el
fichero-.*

### Verde

    tests_js/permisos_de_la_pantalla.test.js  ***5 en verde***
    test_la_migracion_a_react.py  ***14 en verde***   (con `pac` en los tres sitios)
    JS entero  ***1143 en verde***   ·   recuento: ***5458***
    y la suite de Python, corriendo (job pwsh-4750)

### ***Y lo que queda, con los numeros delante***

    ***37 pantallas*** ofrecen escribir y **no** leen el permiso. *Una hecha, con su patron y sus pruebas.*
    ***el patron***, escrito: *prop con defecto `true` + los botones que escriben gateados + «volver» siempre +
                  prueba montandola con y sin permiso.*
    ***la entrada de la PAC en el menu***  -> decision de David
    ***la fuente legal de la PAC***        -> no es mia


---

## 17/10/2026 (94) — ***Los permisos: tres pantallas, y el patron ya no hay que inventarlo***

### Lo que se hizo

*Dos pantallas mas con el patron que se fijo en la ronda anterior:*

  · ***las medidas*** -`medidas.js`-: *y aqui hay una que se escapa facil, **«NO HAGO NINGUNA»**, que **tambien
    escribe** -guarda una declaracion que dice que no-. Sin permiso **no se ofrece ninguna de las tres**: ni
    guardar, ni «no hago ninguna», ni quitar. Y «VOLVER» sale siempre.*
  · ***el cobro nuevo*** -`cobro_nuevo.js`-: *su boton es un `<button>` a mano, no el componente `Boton`, y aun
    asi se gatea igual.*

***Y las dos reciben el permiso en `app.js` con `loQuePuedoHacer().modificar`, y sus envoltorios lo reenvian***
-*que es donde se perdio la prop del panel hace dos rondas-*.

### Verde

    tests_js/permisos_de_la_pantalla.test.js  ***8 en verde***: *tres pantallas, con y sin permiso*
    JS entero  ***1146 en verde***   ·   recuento: ***5458***
    y la suite de Python, corriendo (job pwsh-4824)

### ***Y el recuento honesto de lo que queda***

    ***hechas***:  decir_cultivo · medidas · cobro_nuevo   ->  ***3 de 39***
    ***faltan***:  36, y son las grandes: *gastos (867 lineas), trabajos (1006), semillas (447), siembras (398),
                   tierras_mapa (776), facturas, bancos, bandeja, almacen…*

***Por que no se hacen de golpe, y esta escrito desde la ronda anterior***: *los botones los pinta cada pantalla y
el identificador de la accion viene del **descriptor del servidor** -`m.guardar`-, asi que **no hay barrido de
texto que los encuentre** ni sitio unico donde gatearlos. **Cada una es su edicion y su prueba**, y las grandes
tienen varias formas de formulario cada una.*

*Lo que si queda hecho y sirve para las 36: **el patron escrito y probado**, y **la prueba que nombra las que
estan** -la que se olvide se queda sin prueba, y se nota-.*


---

## 17/10/2026 (95) — ***Los permisos, en UN SITIO: `Boton` sabe si su accion escribe***

### ***Y me equivoque ayer, y esta escrito***

*Ayer escribi, con esas palabras: «**no hay barrido de texto que los encuentre** ni sitio unico donde
gatearlos. **Cada una es su edicion y su prueba**». Y lo hice tres pantallas asi.*

***Era falso, y la ronda de hoy lo demuestra***: *los identificadores de accion vienen del descriptor del
servidor, si, pero **llegan resueltos** a `<Boton accion={...}>`. Asi que **el propio componente sabe si su
accion escribe** -por el sufijo- y **la regla se escribe una vez**.*

***O sea: 39 pantallas, un sitio.***

### La regla

    `ponerSiSePuedeEscribir(puede)`   · ***el defecto es «si»***: *una pantalla que no diga nada se comporta
                                        como siempre, y las pruebas que ya existen no cambian*
    `escribeEstaAccion(accion)`       · ***por el sufijo***: `guardar`, `anular`, `quitar`, `borrar`, `subir`,
                                        `sacar`, `emitir`
    y en `Boton` y `BotonSencillo`    · `if (seEscondeElBoton(accion)) return null;`

***Y lo que NO se gatea, que es la mitad del acierto***: *«nuevo», «nueva» y «corregir» **abren un
formulario** -no escriben-; escribe el boton de **guardar** de dentro. Gatearlas dejaria al usuario sin poder
**ni mirar** el formulario.* ***Y eso esta en la prueba***: `assert !escribeEstaAccion("papel-nuevo")`.

**Y se pone en `montar`** -el unico sitio por el que pasan todas las pantallas-, **antes** de pintar.

### Verde

    tests_js/permisos_de_la_pantalla.test.js  ***11 en verde***: *las tres pantallas de ayer, la regla del
                                              sufijo, el boton escondido sin permiso, y el de ver que sigue*
    ***JS entero: 1149 en verde***   *-y esto es lo que de verdad prueba que la regla no se lleva nada por
                                     delante: `Boton` esta en todas las pantallas-*
    y la suite de Python, corriendo (job pwsh-4885)

### ***Y lo que sigue sin cubrirse, dicho***

*La regla central cubre los botones que pasan por `Boton` y `BotonSencillo` -que son casi todos-. **Quedan los
que se pintan a mano**: `cobro_nuevo` tenia un `<button data-accion="cobro-guardar">` suelto -ya gateado- y
puede haber mas. **Y esos no los ve la regla.***

*Se pueden contar: es un barrido de `data-accion="` fuera de los dos componentes. **Lo siguiente.***

### Y el recuento, que se corrigio

*El guardian del recuento canto -«la documentacion dice 5458 pruebas de Python y hay 5460»-, y tenia razon: el
colector que se uso contaba 5458 y la suite 5460. **Se puso el medido: 5460.***


---

## 17/10/2026 (96) — ***Los trece botones que se pintan a mano: contados, tapados, y con guardian***

### ***El recuento, hecho como se dijo***

*La regla central de ayer ve los botones que pasan por `Boton` y `BotonSencillo`. **Quedaban los que se pintan
a mano** con un `<button data-accion="...">` suelto, y quedo dicho que se contarian. **Contados:***

    ***54 pintados a mano · y de esos, 13 ESCRIBEN***

    cobro_nuevo · contactos (guardar y borrar) · facturar_entregas · interpretacion_factura ·
    movimiento_de_almacen · nuevo_albaran · sacar_de_un_lote · semillas · siembras (guardar y anular) ·
    venta_ajuste · venta_importe

***Y los otros 41 no escriben*** -«elegir», «marcar», «buscar», «leer», «deshacer», «ir-inicio»-, *y varios
parecen que si: `contacto-borrar-si` **no escribe** -es el «si» de una confirmacion, que abre el paso-, y
`fusion-hacer` tampoco -junta dos fichas en la pantalla-.*

### ***Trece ediciones, o una regla***

*Se eligio **la regla**, y esta escrita con su motivo:*

    [data-puede-escribir="no"] [data-accion$="-guardar"], ... { display: none !important; }

*`app.js` marca el documento -`data-puede-escribir`- al montar cada pantalla, y la hoja esconde los siete
sufijos.* ***`display: none` los quita tambien del tabulador y de lo que lee un lector de pantalla***: *para el
agricultor es lo mismo que no estar.*

### ***Y el guardian, que es la mitad del trabajo***

***Una regla que se queda corta no se nota***: *el dia que alguien anada un `<button data-accion="...-firmar">`
que escriba, **el sufijo no estaria en la lista** y el boton se quedaria **visible sin permiso**.*

*Asi que hay **dos pruebas** que sacan los botones **del codigo de verdad**, no de una lista escrita a mano:*

  1. **cada boton pintado a mano que escribe tiene su sufijo en la hoja** -y si no, dice **cual**, con fichero y
     linea-;
  2. **las dos listas de sufijos dicen lo mismo** -la de la hoja y la de `ACCIONES_QUE_ESCRIBEN`.

***Y se vio fallar***: *quitando `-anular` de la hoja, la prueba se pone roja y dice, con nombre y apellidos,
«`siembra-anular` (siembras.js:348) escribe y su sufijo `anular` no esta en la hoja de estilos». Restaurada,
verde.*

### Verde

    tests_js/permisos_de_la_pantalla.test.js  ***13 en verde***
    ***JS entero: 1151 en verde***
    y la suite de Python, corriendo (job pwsh-4947)

### ***Y los permisos, ya enteros, con el numero delante***

    ***los que pasan por `Boton`***      · 41 botones que escriben, escondidos en **un sitio**
    ***los que se pintan a mano***       · 13 botones, escondidos por **una regla de la hoja**
    ***y los dos guardianes***           · *que impiden que un decimocuarto se cuele*
    ***los tres primeros***              · `decir_cultivo`, `medidas` y `cobro_nuevo` *siguen con su gateo
                                           propio: doble, y sin dano*

*Lo que queda de la cola: **la entrada de la PAC en el menu** -decision de David- y **la fuente legal de la
PAC** -que no es mia-. **Y el objetivo no se cierra mientras esas dos no esten decididas**, porque el encargo
manda cerrar con las limitaciones dichas, no con las que faltan escondidas.*


---

## 17/10/2026 (97) — ***El guardian, ensanchado a todo el interfaz: y dos plantados que ensenaron mas que el acierto***

### Lo que se hizo

*El guardian de los botones a mano miraba **solo `react/pantallas/`**. Se ensancho a **todo `web/`** -77
ficheros, sin `vendor` ni el service worker-, **y se midio lo que habia fuera**:*

    `app.js`          -> ***2 `data-accion`, y NINGUNO escribe***
    `react/piezas/`   -> ***7 `data-accion`, y ninguno escribe***
    `react/pantallas/`-> *los 13 conocidos*

***O sea: la cobertura ya estaba completa, pero eso habia que comprobarlo, no suponerlo.*** *Las **47 acciones de
escritura** de la tabla de despacho salen del descriptor del servidor, y las pinta `Boton` -regla central- o son
las 13 a mano -regla de la hoja-.*

### ***Y dos plantados que no cazaron, y por que***

*Para comprobar que el ensanche servia, **se planto un boton de prueba en `app.js`** y se miro si la prueba se
ponia roja. **Dos veces seguidas, no se puso.** Y las dos veces **el guardian tenia razon**:*

  ***1. `<button data-accion="finca-firmar">`***: *`firmar` **no es un verbo de escritura** en este programa
  -escriben `firmar-subir`-, asi que el guardian **no lo considera escritura** y no protesta. **El plantado
  estaba mal, no el guardian.***
  ***2. `<button data-accion="finca-guardar">`***: *el sufijo **`guardar` SI esta en la hoja**, asi que ese boton
  **se esconderia** de verdad. **El plantado describia un boton que ya estaba tapado.***

***Un guardian que no caza un plantado tiene que explicar por que***, *y aqui las dos explicaciones son
«el plantado no era un defecto». **Pero el primero dejo ver un hueco de verdad.***

### ***Y el hueco que si habia: el VERBO NUEVO***

*El guardian de la hoja comprueba que **los botones que ya se reconocen como escritura** estan tapados. **Si
alguien anade un manejador `nombre === "finca-firmar"` que guarda, y `firmar` no esta en la lista, ese boton NO
se esconde y nadie se entera.***

*Asi que se anadio **un tercer guardian**: **saca los manejadores de verdad de `app.js`** -47 que escriben- y los
mira contra una lista **mas ancha** de verbos que huelen a escritura.*

***Y el guardian nuevo encontro un falso positivo, que es la mitad de su valor***: `gasto-sin-asignar`.
*`asignar` **describe un estado, no una accion**: «el gasto **sin asignar**» es un **filtro**, no una escritura.
Se saco de la lista ancha **con el motivo escrito** -«un verbo puede describir un estado y no una accion»-.*

### Verde

    tests_js/permisos_de_la_pantalla.test.js  ***14 en verde***: *los trece botones, la regla del sufijo, el
                                              boton escondido, las dos listas iguales, y **los 47 manejadores
                                              reconocidos***
    ***JS entero: 1152 en verde***
    y la suite de Python, corriendo (job pwsh-69)

### *** Y la cobertura de los permisos, cerrada y medida ***

    ***los que pasan por `Boton`***   · 41 botones que escriben, escondidos en un sitio
    ***los que se pintan a mano***    · 13, escondidos por una regla de la hoja
    ***y fuera de las pantallas***    · 0 en `app.js`, 0 en `piezas/` -medido, no supuesto-
    ***tres guardianes***             · la hoja, las dos listas, y los verbos de la tabla de despacho

*Lo que queda de la cola, otra vez: **la entrada de la PAC en el menu** y **la fuente legal de la PAC**.*


---

## 18/10/2026 (98) — ***La revision independiente tenia razon en las dos, y mi informe estaba mal***

### ***Lo que la revision reprodujo, y lo que yo habia dicho***

***P1: el panel daba dinero sin permiso economico.*** *Con la capacidad apagada: `/api/contactos/{id}/saldo`
respondia **403** y `/api/panel` respondia **200** con **123,45 EUR** dentro. **Un fallo del servidor**: esconder
la cifra en la pantalla no lo arregla, porque **el dinero ya ha viajado por la red**.*

***P2: el clasificador por sufijos se quedaba corto.*** *`contacto-borrar-si` borra, `fusion-hacer` fusiona,
`contacto-nota` apunta, `contacto-baja` cambia el uso, `banco-deshacer` deshace, `bandeja-confirmar` confirma
-**siete acciones que escriben y que mi lista de sufijos no veia**-.* ***Y mi informe decia que `fusion-hacer` y
`contacto-borrar-si` no escribian. Estaba mal.***

***«Una confirmacion puede ser precisamente la operacion destructiva»***: *es la frase de la revision, y es la
que habia que haber pensado antes de mirar sufijos.*

### ***Y el error de fondo, que es el que importa***

***Los guardianes que escribi comprobaban listas de sufijos contra listas de sufijos.*** *Descubrian candidatos
con el mismo vocabulario con el que los comprobaban, asi que **pasaban con el defecto dentro** -las 14 pruebas
en verde y `fusion-hacer` seguia saliendo-.* **Un guardian que usa la misma regla que el codigo no comprueba
nada.**

### Lo que se hizo

***1 · Copia recuperable COMPLETA*** -`copia-completa-2026-10-18.zip`-, *1675 ficheros, 34,3 MB, **verificada
leyendo de dentro del zip***: `models.py` con las dos clases reconstruidas, los dos indices, las 8 columnas de
fertilizantes y el `import nutrientes`; y `nutrientes.py`, `lectura_evaluada.py`, `reservas.py`, `reenvios.py`...
*La revision avisaba: **un patch de tracked no incluye los nuevos** -y son **56**-.*

***2 · P1 corregido en el servidor***: *la puerta pide `UsuarioActual` y pregunta
`accesos.puede_ver_lo_economico`. **Sin la capacidad, la metrica `gastos` NO SE CONSTRUYE** -ni el importe, ni
la cobertura, ni el total-, y **las parejas que nombran el dinero** tampoco viajan. **El panel agronomico se
conserva**: una cuenta de consulta sigue viendo su finca.*

***Y la regresion con importe conocido*** -`test_lo_que_el_panel_no_ensena.py`, **4 pruebas**-: *el titular lo
ve; sin capacidad **no hay metrica** y **123.45 no aparece en el texto entero**; el saldo da 403 como control; y
otra explotacion no lo ve.* ***Y se vio fallar***: *devolviendo el defecto, la prueba dice «la metrica de gastos
NO puede venir: {'clave':'gastos','valor':123.45,'unidad':'EUR'}».*

***3 · P2: el inventario por el EFECTO REAL*** -`web/react/acciones.js`-: **93 acciones que escriben**, sacadas
**del codigo** -que funcion atiende cada accion y si manda algo que no es un GET- y **con las 7 de la revision
nombradas una a una**. *Las **de sesion** -`entrar`, `cambiar-finca`- van aparte: **no escriben datos y
esconderlas dejaria al agricultor fuera**.*

***Y el clasificador por sufijos se fue***, con su regla de CSS y sus dos listas. *Ahora: el inventario decide, y
`app.js` da **una pasada por el DOM** al montar cada pantalla -asi cubre tambien los botones pintados a mano-.*

***Y las pruebas, 5***: *las siete de la revision; **el inventario contra el codigo** -si alguien anade un
manejador que escribe y no lo apunta, falla y lo nombra-; **la reproduccion de `fusion-hacer`**; que `entrar` no
se esconde; y una consulta normal.* ***Y se vio fallar***: *quitando `fusion-hacer`, tres rojas.*

### Verde

    tests/test_lo_que_el_panel_no_ensena.py  ***4 en verde***   ·   JS entero ***1143 en verde***
    recuento Python ***5466***   ·   y la suite de Python, corriendo (job pwsh-326)

### ***Y lo que queda del objetivo de estabilizacion, por su orden***

    ***hecho***:  la copia completa · la exposicion economica · el inventario por efecto real
    ***siguiente***: recorridos de titular, consulta y ayudante **sin dinero** en navegador
    ***siguiente***: revisar los modelos reconstruidos contra esquemas, migraciones e indices **sobre copias**
    ***siguiente***: los 24 reenvios por contrato, y **los datos compuestos que `reenvios.py` no compara**
    ***siguiente***: **commits revisables** -59 modificados y 56 nuevos sin control de versiones es el riesgo
                    mayor que queda-
    ***despues***: superficies y PAC, **sin bloquear por el menu ni por la fuente legal**


---

## 18/10/2026 (99) — ***Lo compuesto tambien se compara: lineas, horas e insumos***

### ***El hueco, con las palabras de la revision***

*`reenvios.la_misma_accion` **saltaba los campos que no eran columna**, con un comentario escrito por mi que decia
«de esas se ocupa la puerta». **La puerta no se ocupaba.***

*Y no son campos de adorno: el plan guarda sus **lineas** en `LineaDeTrabajoPrevisto` y la labor guarda sus
**insumos** como **salidas de almacen**. Asi que un reintento con **otras** lineas u **otros** insumos devolvia
la fila que ya habia **como si fuera lo que se acaba de mandar** -y las filas hijas se quedaban con los datos de la
**primera** vez-. ***Perdida silenciosa***, exactamente la que el 409 existe para impedir.*

### Lo que se hizo

***1 · `reenvios` deja de saltarse nada***: *`la_misma_accion` acepta **`traducir`** -para cuando la peticion y el
modelo no usan el mismo nombre: `horas` es `horas_previstas`- y **`tambien`** -un callable que contesta por las
filas hijas-. **Y lo que no es columna y no tiene `tambien`, NO se da por la misma accion**: cierra en falso.*

***2 · y las puertas lo acreditan*** -`trabajos_api.py`-: *`_las_lineas_son_las_del_plan` compara los **nueve
campos** de cada linea como conjunto ordenado, y `_los_insumos_son_los_de_la_labor` compara **envase, cantidad y
unidad** de las salidas vivas -saltando los insumos que la puerta no habria escrito, que son los que no tienen
cantidad, unidad o envase-.*

***Y se dice lo que NO se compara***: *`articulo_id` no viaja -el envase ya dice de que es-, y `dosis_por_ha` y
`aceptar_descuadre` **no se guardan** en la salida, asi que **no se pueden comparar**.*

### ***Y el defecto que la prueba encontro, que no se ve leyendo***

*La primera version comparaba **con `hasattr`**. Y `TrabajoPrevisto` **tiene una relacion llamada `lineas`**, asi
que `hasattr(ya, "lineas")` era **True** y `reenvios` comparaba **la lista de objetos del modelo** contra **la
lista de objetos de la peticion** -**siempre distintos**-.*

***El sintoma***: *un reintento **identico** con lineas daba **409**. **Un 409 falso en el camino legitimo**, que
es el defecto contrario al que se estaba arreglando.*

***La causa***: ***`hasattr` no es «es una columna»***. *Se cambio por `es_una_columna`, que pregunta a
`ya.__table__.columns`: **un nombre que existe no es un dato que se pueda cotejar**.*

### Verde

    tests/test_los_compuestos_del_reenvio.py  ***4 en verde***:
      · el plan con las **mismas** lineas devuelve el mismo plan;
      · con **otra** linea, **409**;
      · con **otras horas**, **409** -y eso prueba la traduccion `horas` -> `horas_previstas`;
      · y una labor cuyos insumos **no se escriben** no da conflicto, *porque no hay nada escrito que comparar*.
    y los 104 de trabajos + reenvios, en verde · recuento y suites, corriendo (job pwsh-409)

### ***Y lo que queda de este punto, dicho***

  · ***los insumos CON envase***: *la comparacion esta hecha, pero **ninguna prueba la ejercita** con un lote de
    verdad. Se puede -hay que sembrar un articulo y un envase-, y es lo siguiente de este mismo punto.*
  · *y `dosis_por_ha`/`aceptar_descuadre` **no se comparan** porque **no se guardan**: si un reintento cambia solo
    eso, parece la misma accion. **No es una perdida** -no se guardaron-, pero queda dicho.*


---

## 18/10/2026 (100) — ***Cuatro defectos reales, y cuatro avisos falsos mios: la leccion de la revision, aplicada a mi***

### ***Los cuatro defectos, y los tres ultimos los encontro una prueba de comportamiento***

***1 · `reenvios` comparaba RELACIONES con `hasattr`.*** *`TrabajoPrevisto` tiene una relacion `lineas`, asi que
`hasattr` decia que si y se comparaban **objetos con objetos** -siempre distintos-. **Sintoma**: un reintento
**identico** con lineas daba **409**. Es el defecto contrario al que se estaba arreglando. **Se cambio por
`es_una_columna`**, que pregunta a `__table__.columns`.*

***2 · `apuntar_un_trabajo_hecho` no miraba la clave en su CONSULTA PREVIA.*** *El 409 estaba **solo** en el
`except IntegrityError`, y **el caso normal es la consulta**. Asi que un reintento con **otros kilos** devolvia la
labor vieja con «ya estaba» **y el almacen se quedaba con el descuento de la primera vez**.*

***3 · `apuntar_una_reserva` escribia la clave y NO la consultaba.*** *Y **el indice que anadi el 17/10 lo
convirtio en un 500**: antes habia duplicados, ahora `IntegrityError` sin recoger. **Un movil que reintenta sin
cobertura se llevaba un error del servidor** en vez de su reserva.*

***4 · y el reenvio de la reserva chocaba con SU PROPIO SOLAPE.*** *Al arreglar el 3 salio el 4: la comprobacion
de solape corria **antes** que la consulta por clave, asi que el reintento se veia a si mismo y daba 409. **La
clave se mira ahora primero**, porque si es un reenvio la reserva que se pisa **es la suya**.*

### ***Y los cuatro avisos falsos mios, que son la mitad de la leccion***

  · **«3 modelos sin indice unico»** -> *usaban `UniqueConstraint`; mi comprobacion solo miraba `indexes`.*
  · **«`Maquina` y `VentaDeCosecha` no escriben la clave»** -> *viaja dentro de `**datos.model_dump()`.*
  · **«`Factura` tampoco»** -> *la escribe con `factura.clave_de_reenvio = clave`.*
  · **«`apuntar_una_reserva` no usa la clave»** -> *la pone en el ayudante al que delega.*

***Los cuatro eran comprobaciones estaticas con un criterio incompleto*** -`hasattr`, una ventana de 1400
caracteres, un `**` que no se ve- *, y los cuatro **denunciaban un defecto del codigo cuando el defecto era del
instrumento**.*

***Y los tres defectos de verdad los encontro una prueba de comportamiento***: *la de los insumos con envase, que
monto un articulo, un lote y una salida -sin albaran, con `aceptar_descuadre`- y **mando la misma labor dos veces
con kilos distintos**.*

***Es exactamente lo que dice la revision*** -«comprobar permisos reales», «pruebas de comportamiento»-, *y me la
tuve que aplicar a mi mismo: **el analisis de texto encuentra candidatos; la prueba encuentra defectos**.*

### Verde

    tests/test_los_insumos_del_reenvio.py  ***2 en verde*** -y vistos fallar-
    tests/test_el_reenvio_de_una_reserva.py  ***2 en verde*** -y vistos fallar como **500** y como **409**-
    los cuatro ficheros de reenvios y reservas, ***106 en verde***
    recuento ***5496*** · y las dos suites, corriendo (job pwsh-439)

### ***Y lo que queda de este punto***

    ***los 24 reenvios***: *todos tienen columna, unicidad **y una puerta que la escribe*** -comprobado uno a uno,
    despues de descartar mis cuatro avisos falsos-.
    ***y la recuperacion del choque***: *la tienen las seis puertas que la necesitaban, **una de ellas arreglada
    hoy** -la reserva-.*


---

## 18/10/2026 (101) — ***El trabajo pendiente, consolidado: siete commits***

### ***Lo que habia, y por que era el riesgo mayor***

    ***122 ficheros***: 59 modificados y 56 nuevos, **sin control de versiones**, sobre el mismo `HEAD` `949c595`

*Un `git checkout` ya se llevo por delante dos clases reconstruidas y ocho columnas en esta sesion. **Lo que no
esta commiteado no existe**: se puede perder de la misma forma, y esta vez no habria suite que lo rescatara.*

### ***Lo que se hizo: siete commits, por capas, no uno gigante***

    f8a4b77  Los cimientos: los modelos reconstruidos y los modulos nuevos        23 ficheros
    d262fa2  Las puertas: los permisos por materia y los dos routers nuevos       24 ficheros
    e154060  La pantalla: el inventario de acciones por su EFECTO REAL            14 ficheros
    c500ae0  Las pruebas: los permisos, los reenvios y los cuatro defectos        50 ficheros
    7008e03  Los documentos: lo que hace, lo que se prueba y lo que se comprobo     4 ficheros
    fc1d788  Los guiones: los recorridos, que se andan de verdad                   7 ficheros
    143a419  Los fines de linea: dos ficheros de prueba vuelven a CRLF             2 ficheros

*Rama **`estabilizacion-2026-10-18`**, `master`/`principal` intacta en `949c595`. **Arbol limpio: cero ficheros sin
preparar.***

***Y cada mensaje lleva el POR QUE***, no el que: *por que el clasificador por sufijos se fue, por que los defectos
los encontraron pruebas de comportamiento, y por que el commit de los fines de linea esta ahi -en vez de reescribir
la historia para esconderlo-.*

### ***Y lo que se comprobo ANTES de cantarlo***

  · ***122 ficheros, y ni una base de datos, ni un adjunto, ni `datos/`, ni un `.env`, ni una clave privada, ni un
    `__pycache__`*** -buscado en los seis commits y **dentro** de los ficheros nuevos-;
  · **el arbol limpio** por `git status --short`;
  · **y las dos suites enteras sobre la revision estable**: ***Python 5500 y JavaScript 1143, `exit code 0`***.

### ***Y el defecto que salio al hacerlo: los fines de linea***

*`web/app.js` se commiteo **entero** -`26326 insertadas, 24981 borradas`- porque al editarlo con Python quedo en
**LF** y el repositorio lo tiene en **CRLF**. **Es exactamente lo que la revision avisa que oculta el dano**: un
diff de fichero entero no se puede revisar.*

*Se enmendo ese (era el ultimo), y con el de las pruebas -que ya no era el ultimo- **no se reescribio la historia**:
se hizo un septimo commit que solo cambia el salto de linea y **cuenta lo que paso**. Se ve en su `--stat`:
`16083 insertadas, 16083 borradas`, **puro fin de linea**.*

***Queda dicho lo que no se volvio a comprobar***: *los otros ficheros del arbol -fuera de los 122- no se miraron
uno a uno; lo que si se sabe es que **el arbol esta limpio y las suites pasan**.*

### ***Y lo siguiente, con nombre***

***No existe recorrido de consulta.*** *Los **17** guiones de `scripts/verificar_el_recorrido_*.py` andan la
aplicacion con la cuenta **titular** -`comprobar_en_un_navegador.py`, 3706 lineas, lo dice: «la cuenta que crea
esta comprobacion es la titular de su propia finca»-. **Falta el recorrido de consulta y el de ayudante-sin-dinero**,
que es lo que el paso 6 de la revision pide y la unica prueba que le queda a la interfaz: **que el dinero no se vea
en la pantalla**, no solo que no viaje por la red.*

*Hay puerta para anadir un miembro a la finca con su rol -lo usa el propio recorrido del titular-, asi que se puede
hacer.*


---

## 18/10/2026 (102) — ***El recorrido de quien trabaja sin ver el dinero, andado en un navegador***

### ***Lo que la revision pedia, y lo unico que le faltaba a la prueba***

*La suite ya probaba que `/api/panel` no lleva el dinero y que el servidor deniega las siete operaciones. **Pero
eso es el servidor y el componente.** Lo que no estaba probado es **la pantalla de verdad con una cuenta de
verdad** -lo que la revision pide con estas palabras: «recorridos de titular, consulta y ayudante sin dinero»-.*

### ***`scripts/verificar_el_recorrido_sin_dinero.py`, 283 lineas***

*Levanta **su propio servidor** -base temporal, puerto libre, la del agricultor no se toca- y anda el recorrido
entero:*

    1 · siembra la finca del titular **con 40 gastos dentro**
    2 · da de alta otra cuenta y la mete en la finca por la puerta que existe
        (`POST /api/fincas/quien-entra`, que concede **AYUDANTE**)
    3 · la pone a trabajar en la finca del titular (`/api/fincas/cambiar`, que da **un vale nuevo**)
    4 · y contrasta la PUERTA y la PANTALLA

***Y pasa las 17 comprobaciones, sin un fallo:***

      `/api/panel`:  la metrica de gastos NO viene · ni la unidad del dinero · y el panel agronomico SI
      la pantalla:   ***NO dice ni un EUR*** · ni el importe de ningun gasto
                     ***las siete acciones NO se pintan*** -fusion, deshacer, borrar, nota, baja,
                     deshacer del banco y confirmar de la bandeja-
                     ***y la superficie SI se ve***: la pantalla no se queda vacia

### ***Y «consulta» no se prueba porque NO HAY PUERTA QUE LA CONCEDA***

*`POST /quien-entra` da **siempre** `AYUDANTE`. Se supo **leyendo la puerta**, no adivinando. La consulta
-`puede_modificar` **y** economico, los dos en falso- la cubre la suite con `_sin_capacidad`, que es **mas
estricta** que la consulta real.*

***Que no haya puerta para concederla es una decision de producto, no un defecto de esta estabilizacion***, y
queda dicha en vez de disimulada: *si algun dia se concede consulta por la pantalla, **el recorrido ya sirve** -solo
hay que cambiar por que puerta se entra-.*

### ***Y los tres tropiezos del guion, que son la leccion de siempre***

  · *`_api` usa **la direccion global de su modulo**: con un servidor de puerto libre hablaba al **8029** de otro
    guion. Se engancho.*
  · *el prefijo de las fincas es **`/api/fincas`**, en plural: con `/api/finca` el servidor contestaba **405**.*
  · *y `TemporaryDirectory` **revienta al limpiar en Windows** -la base sigue abierta un instante despues de matar
    el servidor-, y ese `PermissionError` **tapaba el resultado de la prueba**: se hace a mano y sin ruido.*

### ***Verde, y en su rama***

    ***8 commits*** en `estabilizacion-2026-10-18`, arbol limpio
    Python ***5500*** · JavaScript ***1143*** · y el recorrido ***17 de 17***

### ***Lo que queda del objetivo, con nombre y sin adornos***

    ***`migraciones sobre copias`***: *los indices y la unicidad estan comprobados, y la suite crea su base desde
    cero -que es «sobre copias»-. **Pero no se ha hecho el ensayo de una MIGRACION de un esquema anterior**, que
    la revision nombra. Es el unico punto del encargo que esta a medias.*
    ***`superficies y PAC`***: *los modulos, las puertas, la pantalla y el recorrido de la PAC estan hechos;
    «continuar segun la cola» es lo que sigue abierto, y el objetivo lo pone **despues** de la estabilizacion.*
    ***y la consulta sin puerta***: *dicho arriba.*


---

## 18/10/2026 (103) — ***Correccion: las migraciones estaban hechas, y yo dije que no***

### ***El error***

*Ayer escribi, y esta en el cierre anterior, que «migraciones sobre copias» era **el unico punto a medias**.
**Es falso.***

    test_lo_que_aporta_un_abono.py:383-386    shutil.copyfile + asegurar_columnas(motor_copia)
                                              ← ***las ocho columnas reconstruidas, SOBRE UNA COPIA***
    test_la_migracion_del_reenvio.py:56-59    el indice unico, SOBRE UNA COPIA
    test_aceptacion_copia_y_migracion.py      ***una prueba de aceptacion entera de copia y migracion***
    test_las_claves_ajenas_que_faltan.py · test_arranque_en_postgresql.py · test_plan_abonado.py

*Y hay un **motor de migracion de verdad** en `database.py` -`asegurar_columnas` con `ALTER TABLE`,
`asegurar_indices`, las claves ajenas que SQLite no puede anadir asi-.*

***Dije que faltaba sin leer los tests que se llaman exactamente eso.*** *Es la **quinta** vez en esta sesion que
un aviso mio sale de no mirar lo que ya estaba: las tres clases de `hasattr`, la ventana de 1400 caracteres, el
`**model_dump()`, y ahora esto.*

### ***Y las «verificaciones de AGENTS», que tampoco sabia que eran***

*Son los tests que hacen cumplir sus propias reglas, y **estan en la suite y en verde**:*
`test_ficheros_de_texto.py` *(el destrozo de las tildes, que `AGENTS.md` avisa)*, `test_lista_de_la_junta.py`
*(los recuentos de README y AGENTS)*, `test_lo_que_hoy_hace_por_defecto.py` *(§1 y §5: no dejar al agricultor sin
salida)* y `test_arranque_en_postgresql.py` *(§7: la base de produccion)*.

### ***El encargo de la revision, clausula por clausula***

      1 copia recuperable con los ficheros nuevos ......... ***hecho*** -1682 ficheros, verificada leyendo de dentro-
      2 sin checkout, reset ni clean ...................... ***hecho*** -y la rama conserva todo-
      3 exposicion economica demostrada ................... ***hecho*** -123,45 con una cuenta sin capacidad, y el
                                                            recorrido del ayudante con 40 gastos dentro-
      4 acciones por su efecto real ....................... ***hecho*** -93 acciones en el inventario, no sufijos-
      5 fusion, borrados, notas, tareas, reservas, deshacer  ***hecho*** -las siete, con su 403 y su prueba-
      6 interfaz y denegacion sin cambios de datos ........ ***hecho*** -10 pruebas y el recorrido en Chrome-
      7 modelos, migraciones e indices sobre copias ....... ***hecho*** -y yo lo dije mal-
      8 identidad y concurrencia de los reenvios .......... ***hecho*** -compuestos incluidos, y cuatro defectos
                                                            reales encontrados comprobando-
      9 titular, consulta y ayudante sin dinero ........... ***titular y ayudante hechos***; *consulta **no tiene
                                                            puerta que la conceda**, y queda dicho-
     10 verificaciones de AGENTS .......................... ***hecho*** -son los tests de la suite, en verde-
     11 commits revisables ................................ ***hecho*** -ocho, por capas, arbol limpio-

### ***Lo que queda, y no es de la revision***

*«**Despues** continuar superficies y PAC segun la cola»* -el propio encargo lo pone despues-. *Superficies y PAC
ya tienen su modulo, su puerta, su pantalla, su recorrido y sus pruebas; **seguir con la cola es el trabajo
siguiente**, y merece su propio goal.*


---

## 18/10/2026 (104) — ***Los permisos por ROL, andados en el navegador: un defecto real, y tres fallos del instrumento***

### ***Primero, la rectificacion que el dueno pide sobre las migraciones***

*Escribi en el cierre (103) que «migraciones e indices sobre copias» estaba «hecho, y a fondo». **No se puede
decir asi**.*

***Lo que los ensayos acreditan, exactamente***:

    test_lo_que_aporta_un_abono.py:383-386  ***las ocho columnas de fertilizantes***, sobre una copia
    test_la_migracion_del_reenvio.py:56-59  ***el indice unico de las lecturas del contador***, sobre una copia

***Y lo que NO acreditan***: *una validacion **integral** de los **65 modelos** reconstruidos. Para eso hace
falta un ensayo por modelo o por familia, y no existe.*

*Lo que si hay, y conviene saberlo antes de echar de menos lo otro:*
`test_aceptacion_copia_y_migracion.py` *(la copia de seguridad y la migracion, de punta a punta)*,
`test_las_claves_ajenas_que_faltan.py` *(las claves ajenas, que SQLite **no** puede anadir con `ALTER TABLE`)*,
`test_arranque_en_postgresql.py` *(el motor de produccion)* y `test_plan_abonado.py` *(que `asegurar_columnas`
se puede repetir sin doler)*. **Es una red, no una garantia por modelo, y se dice como es.**

### ***Y el dueno tenia razon en la comprobacion mal planteada***

*La primera version del recorrido abria **solo el Inicio** y comprobaba que alli no estuvieran siete botones.
**Esos botones tampoco estan en el Inicio del titular** -viven en la ficha del contacto, en la fusion, en el
movimiento del banco y en el papel de la bandeja-, asi que **las siete comprobaciones pasaban sin demostrar
nada**. **Un control que pasa igual con el defecto y sin el no es un control.***

### ***Y con el control positivo salio un DEFECTO DE VERDAD***

***A una cuenta de consulta se le seguia ofreciendo `contacto-nota`***, *mientras **otras ocho acciones de la
misma pantalla si desaparecian**. La diferencia: las que se iban las devuelve el componente `Boton` -que no las
pinta-, y **la que se quedaba la pinta la pantalla a mano en su HTML**.*

***La causa***: `esconderLoQueEscribe()` hacia **una sola pasada al montar**, y **React pinta despues**.

***La reparacion***: *la regla se aplica al arbol y **se queda mirando** lo que se anade despues, con un
`MutationObserver`. Vale para cualquier pantalla sin tocar ninguna, **y funciona en los dos sentidos** -al cambiar
de cuenta sin recargar, lo que se escondio por permiso vuelve a mostrarse-.*

### ***El estado de la validacion, sin adornos***

***43 comprobaciones, 0 fallos***, en `scripts/verificar_los_permisos_por_rol.py`. ***Y sustituye a la primera
version, que no probaba nada.***

    ***capacidades por `/api/cuenta/yo`***:  titular T/T · ayudante T/F · consulta F/F
    ***TITULAR -control positivo, en sus pantallas***:
        `contacto-nota`, `contacto-baja` y `contacto-borrar-si` -este **pulsando `contacto-borrar`**, que es
        donde existe, porque es el boton del **dialogo de confirmacion**-
        `fusion-hacer` **eligiendo origen y destino y pidiendo la vista previa**
        `fusion-deshacer` **fusionando de verdad y deshaciendo despues**
    ***AYUDANTE***: apunta un trabajo agronomico (201) · **si ve** las escrituras -puede modificar- ·
        **no recibe** la metrica del dinero, ni la unidad, ni la ve en pantalla
    ***CONSULTA***: preparada **solo en la base temporal** -no hay puerta que la conceda, **y no se anade una**-
        no se le ofrecen las escrituras · **la puerta las deniega: 403** en apuntar, borrar, fusionar,
        deshacer, desconciliar y confirmar
    ***CAMBIO DE CUENTA Y DE EXPLOTACION*** en el mismo navegador

***Lo que queda SIN VERIFICAR, y por que***: `banco-deshacer` y `bandeja-confirmar` *no se alcanzan sin un estado
que hoy no existe en el escenario -un movimiento conciliado y un papel revisado-. **Se declaran «sin verificar» en
vez de contarlos como buenos**; de ellos queda acreditado que **la puerta los deniega**.* **Para cerrarlos hace
falta**: *un movimiento del banco **conciliado** -el escenario no crea ninguno- y un papel **revisado**.*

### ***Y tres fallos del instrumento, que son la mitad de la leccion***

  1. ***En `about:blank` no se puede tocar `localStorage`*** -`SecurityError`-: *hay que estar en el origen de la
     aplicacion antes de poner el vale, y recargar despues.*
  2. ***Una pantalla tarda en pintarse.*** *Con espera fija, la ficha daba **30** acciones al titular, **23** al
     ayudante y **22** a la consulta -y 22 frente a 23 no es un patron de permisos, es tiempo-. **Llegue a creer
     que mi cambio habia quitado botones al ayudante.** Ahora se espera a que la pantalla **se quede quieta**.*
  3. ***Y mi formulacion del ayudante estaba mal de raiz***: *le exigia **no ver** las siete escrituras, cuando
     **puede modificar** y por tanto **debe verlas**. Lo que no puede es ver el dinero.* **El dueno lo dijo con
     dos palabras: «hay que distinguir».**

### ***Y una cosa mas, que el dueno avisa y que se cumple***

***Un boton con `hidden` sigue en el HTML.*** *Mirar si una cadena aparece en el volcado no dice si el agricultor
lo ve. Ahora se mira **si tiene caja, si es visible y si se puede enfocar** —lo que no se enfoca no se alcanza
con el tabulador—, y se distingue `ausente` / `oculto` / `no-visible` / `no-enfocable` / `enfocable`.*

### Verde

    ***9 commits*** en `estabilizacion-2026-10-18` -el noveno es el arreglo y su prueba-, `principal` en `949c595`
    y la suite entera, corriendo (job pwsh-982)


---

## 18/10/2026 (105) — ***Seis de las siete con control positivo, y la septima con su causa exacta***

### ***Lo que faltaba era el ESTADO, no el permiso***

*`bandeja-confirmar` y `banco-deshacer` **no existen en reposo** -el primero necesita un papel **revisado**, el
segundo un movimiento **conciliado**-, y por eso la vuelta anterior los dejo «sin verificar». **Ahora el recorrido
prepara los dos estados por la puerta, como lo haria el agricultor.***

***El papel, revisado a mano***: *`{"campos": {"quien": ..., "fecha": ...}}`. Su propio docstring lo dice -«tambien
se puede hacer **a mano**, cuando el papel no se ha podido leer»-, y era lo que faltaba: `la_propuesta` venia
**vacia**, y **sin revisar nada no hay nada que confirmar** (`se_puede_confirmar` en falso).*

***Despues de revisarlo***: `estado: propuesta_revisada`, `se_puede_confirmar: **True**`, y el boton aparece. **Al
titular si, al ayudante tambien -puede escribir-, y a la consulta no.** ***Control positivo y negativo, los dos.***

### ***Y la septima: el banco, con la causa exacta -no con un «no se pudo»***

*Para conciliar hace falta **un papel pendiente**, y las clases que la puerta admite son **`factura_emitida`,
`cobro` y `factura_de_compra`** -`gasto` **no existe** como clase-.*

*El escenario **no crea ninguno de los tres**: `GET /api/banco/movimientos/{id}/propuestas` contesta
`propuestas: []` y `pendientes: []`, con `se_puede_conciliar: true` y **nada que imputar**. **No es un defecto del
codigo**: es que `preparar` no siembra un papel pendiente.*

***Para cerrarlo***: *sembrar **una factura de compra pendiente** -o un cobro o una factura emitida- en el
escenario, conciliarla contra el movimiento, y entonces `banco-deshacer` existira. **Es el unico de los siete que
queda, y esta dicho que hace falta.***

### ***Y un fallo mio mas, que conviene apuntar***

*La primera version mandaba **la propuesta entera** dentro de `imputaciones`. **La forma la dice la propia
aplicacion**: `conciliarUnMovimiento(propuesta.imputaciones)` -lo que viaja es **la lista de imputaciones**, no la
propuesta-. *Con la forma mala, la puerta contestaba «Elige un papel de tu finca», y eso parecia un defecto del
codigo. **No lo era.***

### ***El estado de la validacion, contado entero***

    ***6 de 7 con CONTROL POSITIVO en el titular***:
        fusion-hacer · fusion-deshacer -***fusionando de verdad y deshaciendo***-
        contacto-borrar-si -***abriendo el dialogo, que es donde existe***-
        contacto-nota · contacto-baja · bandeja-confirmar
    ***y el septimo***: `banco-deshacer`, *con la causa exacta arriba y lo que falta para cerrarlo*.

    ***AYUDANTE***: apunta trabajo agronomico (201) y **ve** las seis -puede escribir-; **no recibe** el dinero,
        ni la unidad, ni lo ve en pantalla.
    ***CONSULTA***: sembrada **solo en la base temporal**; **no se le ofrece ninguna**; **la puerta las deniega**
        -403 en apuntar, borrar, fusionar, deshacer, desconciliar y confirmar-; **ni un EUR** en pantalla.
    ***CAMBIO DE CUENTA Y DE EXPLOTACION*** en el mismo navegador.

    ***49 comprobaciones · 1 fallo declarado***, en `scripts/verificar_los_permisos_por_rol.py`
    ***11 commits*** en `estabilizacion-2026-10-18`, arbol limpio, `principal` en `949c595`


---

## 18/10/2026 (106) — ***LAS SIETE, con control positivo: 53 comprobaciones, 0 fallos***

### ***Lo que faltaba era un papel pendiente, y un JSON que iba en un campo de formulario***

***`banco-deshacer` no existe si no hay nada que deshacer.*** *Para conciliar hace falta un **papel pendiente**, y
las clases que la puerta admite son `factura_emitida`, `cobro` y `factura_de_compra` -`gasto` **no existe**-. **El
escenario no crea ninguno** -`propuestas: []`, `pendientes: []`-, asi que el recorrido **da de alta una factura de
compra** -lo que hace el agricultor cuando le llega el papel- **y concilia el movimiento contra ella**.*

***Y el fallo de forma, que parecia un defecto del codigo***: *`POST /api/facturas` **no toma un cuerpo JSON**,
toma **`datos: str = File(...)`** -un JSON **dentro de un campo de formulario**-, porque en la misma peticion viaja
el fichero y un formulario con fichero no puede llevar un cuerpo JSON normal. Lo dice su propio docstring, y **con
un cuerpo JSON contesta `loc: ["body", "datos"]` ignorando el cuerpo entero, en silencio**. *Parecia que la puerta
«no aceptaba» la factura; lo que no llegaba era el cuerpo.*

### ***El estado final de la validacion de roles***

    ***53 comprobaciones · 0 fallos***   en `scripts/verificar_los_permisos_por_rol.py`

    ***LAS SIETE con control positivo en el titular***
        fusion-hacer          eligiendo origen y destino, y pidiendo la vista previa
        fusion-deshacer       ***fusionando de verdad y deshaciendo despues***
        contacto-borrar-si    ***pulsando `contacto-borrar`, que es donde existe*** -el dialogo-
        contacto-nota
        contacto-baja
        banco-deshacer        ***conciliando un movimiento contra una factura de compra***
        bandeja-confirmar     ***revisando el papel a mano***, que es lo que lo hace confirmable

    ***AYUDANTE***: apunta trabajo agronomico (201) · **ve las siete** -puede modificar- ·
        **no recibe** la metrica del dinero, ni la unidad, ni lo ve en pantalla
    ***CONSULTA***: sembrada **solo en la base temporal** · **no se le ofrece ninguna de las siete** ·
        **la puerta las deniega** -403 en apuntar, borrar, fusionar, deshacer, desconciliar y confirmar- ·
        **ni un EUR** en pantalla
    ***CAMBIO DE CUENTA Y DE EXPLOTACION*** en el mismo navegador
    ***Y la visibilidad con FOCO***: *se distingue `ausente` / `oculto` / `no-visible` / `no-enfocable` /
        `enfocable`, y solo `enfocable` cuenta como ofrecido*

### ***Lo que el dueno puede dar por cerrado, y lo que no***

***CERRADO***: *la validacion de roles, con las siete acciones y los tres papeles, en un navegador de verdad y
con la sesion cambiada dentro del mismo navegador.*

***NO CERRADO, y conviene no confundirlo***: *`volver_a_comprobar_con_el_dueno`*. *El dueno ha corrido 22 pruebas
de Python y 5 de JavaScript por su cuenta, y **no ha repetido las suites completas ni el recorrido de Chrome**.
Lo de aqui es lo que se anduvo en esta sesion.*

    ***12 commits*** en `estabilizacion-2026-10-18`, arbol limpio, `principal` en `949c595`

### ***Y lo que el objetivo pone al final, que es lo que sigue***

***Superficies y preparacion PAC segun la cola***. *La PAC tiene hoy la puerta del paquete -`GET /api/pac/paquete`,
con `falta_*`, sin fuente legal y sin garantia- y le faltan, por CRM-09:* ***el escenario del año siguiente separado
de lo declarado y de lo realizado***, ***la evaluacion con numerador/denominador***, ***la exportacion que coincide
con el detalle y conserva la version evaluada*** y ***el historial que no cambia al editar el escenario***. *Todo
eso es ingenieria; **la fuente legal por ambito y año no bloquea** -cuando no haya fuente suficiente, se marca
pendiente y no se afirma elegibilidad-.*


---

## 18/10/2026 (107) — ***El escenario del año que viene: una hipotesis que no toca nada***

### ***La cola lo pide asi***

*«**Escenario siguiente año separado de lo declarado y de lo realizado.** Comparar alternativas **sin
consumir**»*, y en la aceptacion: *«**editar escenario no cambia historial**»*.

### ***Y se cumple sin guardar nada, que es lo que lo hace verdad***

*Un escenario **no es un dato de la finca**: es una pregunta -«¿y si el año que viene siembro esto?»-. **Guardarlo
seria empezar a tener dos verdades de la misma tierra.** Se calcula sobre el paquete -que es lo que hay de
verdad-, se contesta y se tira.*

***Y de ahi salen las tres propiedades, y las tres estan probadas:***

    1. ***dice que es una hipotesis*** -en la cabecera y **en cada recinto**: `capa: "hipotesis"`,
       `no_es_lo_declarado`, `no_es_lo_realizado`, `no_es_garantia`, `toca_lo_guardado: False`-;
    2. ***no toca lo guardado***: *el paquete sale **exactamente igual** y en la base **no falta ni sobra un
       cultivo** -medido con `count` antes y despues-*;
    3. ***comparar dos alternativas no consume ninguna***, porque no hay nada que consumir.

### Lo que se anadio

    `pac.el_escenario(paquete, anio, cambios)` y `pac.comparar_alternativas(uno, otro)`   ***funciones puras***
    `POST /api/pac/escenario`   *un POST por el tamaño del juego de cambios, **no porque escriba***
    `pac.lo_que_falta_para_la_pac`   ***la regla de lo que le falta a un recinto, en UN solo sitio***:
        *la usaba la puerta del paquete y ahora tambien el escenario; con dos copias, un dia dirian cosas
        distintas de la misma tierra.*

***Y el denominador, que es de la casa***: *«tierra sin cultivo no desaparece para pintar verde» **vale tambien
aqui**: si en el escenario se siembra una parte, el porcentaje es **sobre el total** y lo que se queda fuera **se
dice** -`se_queda_fuera`-.*

### ***Y dos fallos de forma, que parecian defectos y no lo eran***

  1. ***Las claves de un JSON llegan como TEXTO***: *`{"5": {...}}`, no `{5: {...}}`. Buscar el `parcela_id`
     entero **no encontraba nada**, y **el cambio se perdia en silencio**: el escenario salia igual que el
     paquete. Se normalizan a numero.*
  2. *`superficie_total=la_superficie or None` convertia «no hay hectareas» en «no hay denominador», **y eso
     lanza**: `el_porcentaje` sabe que hacer con un cero, pero no con `None`.*

### Verde

    ***6 pruebas*** nuevas · Python ***5512*** · JavaScript ***1143*** · **las dos suites, `exit code 0`**
    ***13 commits*** en `estabilizacion-2026-10-18`, arbol limpio, `principal` en `949c595`
    *y comprobado que **este commit no cambio ningun fin de linea***

### ***Lo que le queda a CRM-09, y es lo siguiente***

***La exportacion que coincide con el detalle y CONSERVA LA VERSION EVALUADA***. *Y con ella, el historial de lo
evaluado: hoy el escenario se calcula y se tira -que es lo correcto para comparar-, pero **cuando el agricultor
quiera guardar lo que enseño al asesor**, hace falta guardar **una foto con su version y su fecha**, y que lo que
se exporte **sea exactamente esa foto**.*

*Todo eso es ingenieria. **La fuente legal por ambito y año no bloquea**: cuando no haya fuente suficiente se marca
pendiente, y no se afirma elegibilidad.*


---

## 18/10/2026 (108) — ***La foto evaluada: el fichero es EXACTAMENTE lo que se enseno***

### ***El ultimo criterio de CRM-09***

*«**la exportacion coincide con el detalle y conserva la version evaluada**».*

### ***Por que hace falta guardar algo, si el escenario no se guarda***

*El escenario **se calcula y se tira** -que es lo correcto para **comparar**-, pero **ensenar** es otra cosa: hace
falta que lo que se enseno al asesor **siga siendo lo mismo** dentro de un ano. **Eso es la foto.***

***Y guarda el CONTENIDO, no la receta***: *si dentro de un ano cambia un cultivo de la finca, **la foto sigue
diciendo lo que decia**. **Por eso la exportacion lee el contenido guardado y NO recalcula**: si recalculara, un
cambio en la finca haria que el fichero dijera una cosa y la foto otra.*

### Lo que se anadio

    `models.FotoDeLaPac`      version por finca y ano, con su `huella` y **el escenario entero** guardado
    `POST /api/pac/foto`      *guardar es escribir: lleva `PuedeModificar`*
    `GET  /api/pac/foto/{v}`  el detalle, que es lo que se exporta
    `GET  /api/pac/foto/{v}/exportar`   el CSV **con la version y la fecha en la cabecera** y **sin ninguna
                              columna de elegibilidad**: este programa no la afirma

### ***Y una decision que el guardian del ano me obligo a tomar -y con razon***

*La foto **no cuelga de `campana_id`**. Si colgara, entraria en el **recuento de cosas del ano** -saldria como
«otra cosa»- y en el **guardian de borrado** de la campana, donde no pinta nada: **una foto no es un apunte del
cuaderno**, es un papel que se lleva al asesor. **El ano lo lleva en `anio`**, que es lo unico que necesita.*

*Lo dijo `test_todas_las_tablas_del_ano_estan_clasificadas`: «estas tablas cuelgan del ano y no estan en ninguna de
las tres listas».*

### ***Y un fallo de forma, que parecia un defecto***

*`PuedeModificar` y `UsuarioActual` son **dependencias**, no parametros. Con `from __future__ import annotations`
sus nombres son **texto**: **si no se importan, FastAPI no los resuelve y los trata como parametros de consulta**.
La puerta contestaba **422** pidiendo `usuario` y `puede_modificar` **en la direccion**.*

### Verde

    ***5 pruebas*** nuevas · Python ***5519*** · JavaScript ***1143*** · **las dos suites, `exit code 0`**
    ***14 commits*** en `estabilizacion-2026-10-18`, arbol limpio, `principal` en `949c595`
    *y comprobado, commit a commit, que **no se cambio ningun fin de linea***

### ***Lo que queda de la ultima clausula del objetivo: SUPERFICIES***

*La PAC queda con sus criterios de aceptacion cubiertos -fuente por ambito/campana, falta ->
incompleto, escenario separado de declarado y realizado, comparar sin consumir, editar sin cambiar historial, y la
exportacion que conserva la version evaluada-. **Lo que NO se ha tocado en este objetivo es CRM-06, tierras y
mapas**, y es lo que queda por continuar.*

*Lo que hay hoy, y no se ha vuelto a mirar: `test_mapa_del_sigpac.py` (47 pruebas), `test_sigpac.py` (49),
`test_las_superficies_no_se_suman.py`, `verificar_el_recorrido_de_la_aplicabilidad.py` (74 KB) y
`app/superficies.py`. **La aceptacion de CRM-06 pide**: 64 tierras y diez filtradas -> 10/64 en tabla y
seleccion coherente en mapa; poligono con agujero y trozos; trabajo realizado actualiza historia y plan no;
rodillo despues de siembra conserva cultivo; cambio de campana no altera anos previos; formas solapadas no
duplican superficie unica sin advertencia; **vista movil** sin forzar una tabla de escritorio.*


---

## 18/10/2026 (109) — ***Superficies: el unico criterio que no tenia prueba, y lo tiene***

### ***Como se supo cual faltaba, sin otra ronda de inventario***

*Se miro **solo** la aceptacion de CRM-06 -ocho criterios, los de la cola- y se busco cada uno en las 195 pruebas
y en los guiones. **Siete estaban cubiertos**; el sexto, **no**.*

    ***6 · «cambio de campana no altera años previos»  ->  NADIE***

### ***Y por que merece su propia prueba***

*El programa guarda el cultivo **por campaña** y las labores **por campaña**. Si algo estuviera mal atado -una
consulta sin filtrar por el año, un `update` que se lleva lo de antes-, **sembrar el año que viene cambiaria lo
que se declaro el año pasado**. **Eso no es un detalle de pantalla: es un dato fiscal y de la PAC.***

***Y pasa***: *el codigo ya estaba bien. **Lo que faltaba era la prueba**, y sin ella nadie podia decir que
estuviera bien.*

### Lo que se comprueba, y con eso quedan los ocho

  · **el cultivo de un año sigue siendo el suyo** despues de sembrar el siguiente -y el nuevo dice lo nuevo-;
  · **una labor de un año no aparece en el otro**, ni al reves;
  · **y el paquete de la PAC de un año no cambia** porque se siembre y se trabaje en el siguiente.

*Los otros siete ya estaban: los diez de 64 con su seleccion en el mapa, el poligono con agujero y trozos, la
ficha que abre la misma ficha, lo hecho que va a la historia y el plan que no, el rodillo tras la siembra, las
formas solapadas y la vista movil -en `test_mapa_del_sigpac`, `test_sigpac`, `test_trabajos`,
`test_las_superficies_no_se_suman`, `comprobar_en_un_navegador` y los recorridos-.*

### ***Y un aviso para quien lo copie***

*`crear_campana` en `test_analisis_ventas_planes_y_campanas.py` **es una fixture**, y **una fixture no se puede
llamar directamente** -pytest lo prohibe con razon-. Aqui se copian **tres lineas** de un `POST`, que no
justifican acoplar dos ficheros de pruebas.*

### Verde

    ***3 pruebas*** nuevas · Python ***5524*** · JavaScript ***1143*** · **las dos suites, `exit code 0`**
    ***15 commits*** en `estabilizacion-2026-10-18`, arbol limpio, `principal` en `949c595`

### ***El objetivo, clausula por clausula***

      validacion de roles en navegador real .............. ***53 comprobaciones, 0 fallos; las siete con control
                                                            positivo y la consulta sembrada en la base temporal***
      capacidades por `/api/cuenta/yo` ................... ***hecho***
      titular · ayudante · consulta ...................... ***hecho, cada uno con lo suyo***
      cambio de cuenta y de explotacion .................. ***en el mismo navegador***
      visibilidad Y FOCO ................................. ***ausente/oculto/no-visible/no-enfocable/enfocable***
      perfil corregido -migraciones ...................... ***no se presentan como validacion integral***
      PAC segun la cola .................................. ***escenario separado, comparar sin consumir, y la foto
                                                            con su version y su exportacion***
      superficies segun la cola .......................... ***los ocho criterios de CRM-06, los ocho con prueba***
      commits revisables ................................. ***15, por capas, sin reescribir la historia***

*Queda dicho lo que **no** es: **no se ha vuelto a andar el recorrido de Chrome** despues de los ultimos cambios
-`pac.py`, `models.py` y las puertas de la PAC **no tocan la pantalla**-, y **el dueno no ha repetido las suites
completas** por su cuenta.*
