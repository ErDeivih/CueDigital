# Revisión independiente del T11 — contactos reutilizables, enlaces y migración de textos

**Qué es esto.** No es la suite del ticket ni un resumen de ella: es **el intento de romperla**. Lo que
hay aquí está medido con mis propias pruebas contra bases temporales, y cada defecto lleva el comando,
la salida literal y **quién lo habría cazado**. Lo que no he podido comprobar está en la sección 7,
escrita antes de que nadie la pidiera, y lo que he intentado romper y **no he podido** está en la 6,
porque eso también es un resultado y hay que decirlo.

**Qué reviso.** `docs/CONTRATO_IMPLEMENTACION_CRM.md` (T11/E5, S15 y el contrato del núcleo: tablas,
fichas, aislamiento, anulación y reenvío), la entrega `docs/T11_CONTACTOS.md` y el código de
`backend/app/contactos.py`, `backend/app/routers/contactos_api.py`, `backend/scripts/migrar_contactos.py`,
`backend/web/react/pantallas/contactos.js`, `backend/web/react/pantallas/revision_de_contactos.js`,
`backend/web/app.js`, los tres modelos nuevos de `backend/app/models.py`, y las pruebas del ticket.

**Fecha de la revisión:** 02/10/2026, de 21:06 a 21:50 (hora local).
**No se ha abierto la base del agricultor.** `backend/cuedigital.db` sigue con **446.464 bytes** y
sha256 `71456B0B1E1FE444…` (comprobado al empezar y al terminar: la misma). Todas las pruebas de aquí
van contra bases en la carpeta temporal, y los nombres escritos se fabrican en ellas.

**Veredicto en una línea:** el ticket está **bien construido en lo que más miedo daba** —el aislamiento
entre fincas, el «un texto, un solo dueño», el «enlazar no borra el nombre» y el «deshacer no se lleva
el trabajo del agricultor» los he atacado a fondo y **no he podido romperlos**—, pero tiene **cuatro
defectos**: uno **de gravedad alta** que va justo contra la regla que gobierna el ticket (una fusión que
no se puede asegurar, marcada como segura y aplicada sola por el guion) y tres medios/bajos, de los
cuales uno es **el hueco de pruebas que ya escondió un botón en el T10**.

---

## 1. Cómo se ejecuta y qué sale

```bash
# Python: la suite entera, dos veces (el árbol se movió entre las dos)
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests -q --junit-xml=$env:TEMP\rev11.xml      # 21:08 → 3677, 0 fallos, 0 errores, 1 saltada
..\.venv\Scripts\python.exe -m pytest tests -q --junit-xml=$env:TEMP\rev11_b.xml    # 21:22 → 3678, 0 fallos, 0 errores, 1 saltada

# JavaScript
node --test "tests_js/*.test.js"      # 852 pruebas, 852 en verde, 0 fallos (21:26)
```

**En el momento de entregar esto, con `backend/tests/test_revision_t11.py` (el fichero de esta
revisión) dentro del repositorio, la suite entera ejecuta 3686 pruebas con 5 fallos**: cuatro son los
defectos de la sección 4 (los que hay que arreglar o decidir) y el quinto es el guardián de los
recuentos, que se queja de que la documentación diga 3678 — la sección 8 lo cuenta con las medidas y con
el aviso de que **el árbol sigue creciendo mientras se escribe esto**.

```bash
..\.venv\Scripts\python.exe -m pytest tests/test_revision_t11.py -q
# 6 pruebas: 2 pasan (lo que se midió y no se pudo romper) y 4 fallan (los cuatro defectos)
```

Los recuentos, medidos (no copiados de la documentación): **3677** pruebas de Python a las 21:08 y
**3678** a las 21:22; **852** de JavaScript; las 55 del ticket de Python y las 32 de JavaScript que dice
su informe, contadas una por una. Y después el árbol siguió creciendo: a las 21:33 la suite **ejecuta
3686** con el fichero de esta revisión dentro, y a las 21:37 `--collect-only` **recoge 3688 con él y
3682 sin él** (sumando lo que recoge cada fichero). Las dos formas de contar no dan exactamente el mismo
número —3686 ejecutadas contra 3688 recogidas—, así que **el número que va a los tres documentos hay que
medirlo al actualizarlos, no copiarlo de aquí**. La sección 8 lo cuenta por qué.

---

## 2. El árbol se movía: cuatro fotos

| Foto | Hora | Qué pasó |
|---|---|---|
| **A** | 21:06 – 21:08 | Empiezo. `contactos.py` 26.793 B (19:57), `contactos_api.py` 41.240 B (20:27), `contactos.js` 17.097 B, `contactos.test.js` 38.729 B, `docs/T11_CONTACTOS.md` 27.716 B, `AGENTS.md` decía **3677**. Suite: 3677, 0 fallos. |
| **B** | 21:19 – 21:22 | **Alguien seguía trabajando**: `contactos.js` → 17.243 B (21:19:52, el rótulo del botón de buscar), `contactos.test.js` → 38.775 B (21:20:11), `docs/T11_CONTACTOS.md` → 28.806 B (21:22:34), y `AGENTS.md`/`README.md`/`LO_QUE_PIDE_LA_JUNTA.md` (21:21–21:23) pasan a **3678**. |
| **C** | 21:22:37 | Snapshot con huellas y **re-medición de todo** sobre la foto B: la suite ejecuta 3678, 0 fallos, y los cuatro defectos siguen ahí (los tres ficheros que los provocan —`contactos.py`, `contactos_api.py`, `models.py`— no se movieron). |
| **D** | 21:27 – 21:30 | **Se mueve otra vez**: `backend/tests/conftest.py` (21:27:30; con él, la suite recoge **3682** sin el fichero de esta revisión, cuatro más que cuando se actualizaron los documentos) y `docs/T11_CONTACTOS.md` (21:30:30, 28.806 → **31.710** B: le añaden el §8, «Tres cosas que salieron mal, contadas como fueron», que cuenta el esquema puesto al día por el informe, la puerta `articulos.proveedor` y el rótulo del botón de buscar). **Ese §8 corrige una cosa que yo iba a reportar**: el §5 citaba «§7.3» para el cambio del rótulo y ahora cita «§8.3», que es donde está. |

> **Lo que quiero que quede claro:** los defectos 1, 3 y 4 están medidos sobre `contactos.py` (19:57) y
> `contactos_api.py` (20:27), que **no** han cambiado desde el principio de la revisión. El defecto 2
> (los botones) lo he vuelto a medir sobre `contactos.test.js` de las 21:20 y sigue igual. Los ficheros
> que se movieron después de empezar están marcados en la tabla de arriba, y **la foto C es la que
> manda** en todo lo que digo de la pantalla.

Huellas de la foto C (16 primeros dígitos de sha256), por si alguien vuelve a mirar:

| Fichero | Tamaño | Hora | sha256 |
|---|---|---|---|
| `backend/app/contactos.py` | 26793 | 19:57:48 | `05B40631B3A2EFD3` |
| `backend/app/routers/contactos_api.py` | 41240 | 20:27:37 | `C10688BF0C3E47D0` |
| `backend/app/models.py` | 124888 | 19:42:49 | `1F37978BFDDB9471` |
| `backend/app/schemas.py` | 108745 | 21:10:27 | `DDC98E354E4C39C1` |
| `backend/app/textos.py` | 327602 | 20:45:31 | `824015535B1EBD90` |
| `backend/web/app.js` | 705283 | 21:04:17 | `F591BBCB53DF4A7D` |
| `backend/scripts/migrar_contactos.py` | 17409 | 20:28:08 | `59FBB476625BD2AE` |
| `backend/web/react/pantallas/contactos.js` | 17243 | 21:19:52 | `40AA165534947422` |
| `backend/web/react/pantallas/revision_de_contactos.js` | 9034 | 19:56:21 | `09896C544B3B3995` |
| `backend/tests/test_contactos.py` | 55879 | 20:50:13 | `8904CAF27028B347` |
| `backend/tests_js/contactos.test.js` | 38775 | 21:20:11 | `21DFA86A71D76573` |
| `backend/cuedigital.db` (no se toca) | 446464 | 30/09 18:05 | `71456B0B1E1FE444` |

> Y en la **foto D** (21:27–21:30) se movieron otros dos ficheros que **no** son de los defectos:
> `backend/tests/conftest.py` (19317 B, 21:27:30) y `docs/T11_CONTACTOS.md` (31710 B, 21:30:30, con el
> §8 nuevo). Ninguno de los dos cambia lo que digo de `contactos.py`, `contactos_api.py` ni de las
> pantallas.

---

## 3. Contrato por contrato: qué he probado y qué ha salido

| Lo que promete el contrato / el informe | Cómo lo he atacado | Resultado |
|---|---|---|
| **§3.1** «No se fusiona nada que no se pueda asegurar» | Dos nombres distintos con el mismo NIF; una factura y un análisis con el mismo NIF; el mismo nombre con dos NIF; una tilde de menos; un «S.L.» de más | **Dos de estos salen mal**: el NIF une sin mirar el nombre (**defecto 1**). Los otros tres, correctos (409 y la base vacía) |
| **§3.2** «El número del "se parecen" está medido» | Recomputo las cinco razones con `difflib` y las comparo con los números publicados | **Cierto**: 0,9474 / 0,9231 / 0,8889 / 0,8889 / 0,8824, exactos, y 0,93 en el hueco |
| **§3.3** El enlace va en su propia tabla y los documentos no se tocan | Guion y router leídos buscando `UPDATE`; textos de las facturas medidos antes y después de migrar y de deshacer | **Cierto** (ver sección 6) |
| **§3.4** «Un texto escrito no puede tener dos dueños» | Dos fichas pidiendo el mismo texto; reenvío del mismo enlace; la restricción única en el modelo | **Cierto**: 409 con el nombre del dueño y **una sola fila** en la base |
| **§3.5** Dos contactos pueden llamarse igual | Dos altas a mano con el mismo nombre; restricción única buscada en el modelo | **Cierto** |
| **§3.6** «O se apunta lo que se enseñó, o no se apunta» | Una factura nueva entre mirar y confirmar; **una corrección del texto** entre mirar y confirmar; una clave segura junto a una insegura | Factura nueva → 409 ✅; las tres comprobaciones **antes** de escribir nada ✅; pero un cambio de forma del texto entra sin decir nada (**defecto 4**) |
| **§3.6** Reenviar un comando devuelve su resultado (contrato §2) | Mandar dos veces la misma confirmación | **Falla**: 409 y «la lista ha cambiado» cuando no ha cambiado (**defecto 3**). No duplica ✅ |
| **§3.7** «Deshacer no se lleva el trabajo del agricultor» | Migración, luego ficha a mano, enlace a mano y una ficha de la migración corregida; deshacer | **Cierto** (ver sección 6), con una salvedad de la API en la sección 5 |
| **§3.8** El guion hace exactamente lo mismo que la pantalla | `migrar_contactos.py` leído y ejecutado de verdad sobre una base antigua que fabrico yo | **Cierto**: llama a `aplicar_la_migracion`/`deshacer_la_migracion`, usa `proponer`, y **ni un `UPDATE`** |
| **§3.9** El informe del guion no toca el esquema | Base con las tres tablas del T11 borradas: huella sha256 del fichero antes y después y lista de tablas | **Cierto**: la huella no cambia y no aparece ninguna tabla |
| **Aislamiento entre explotaciones** (gravedad alta en este proyecto) | Siete ataques cruzados entre dos fincas (leer, corregir, borrar, papeles, enlazar, enlazar a un documento ajeno, quitar un enlace ajeno) | **Cierto: 404 en los siete**, y la otra finca no ve ni una ficha ni un nombre escrito |
| **Estados de pantalla y «no se sabe»** | `es_empresa` con tres respuestas; campos vacíos; `anulada` con tres respuestas; papel inventado | **Cierto**: `None` viaja como `None`, `""` se guarda como `None`, y el papel inventado da 422 **sin guardar la mitad** |
| **Los botones hacen algo** (§5 del encargo) | Las 19 acciones de T11 buscadas en `tests_js/`: ¿se pulsan? | **No se pulsa ninguna** (**defecto 2**) |
| **Jerga y colores** | Suite entera (los tres guardianes de jerga y el de `DESIGN.md`) | **Cierto**: en verde |
| **Recuentos de la documentación** | Cuento yo, con `pytest` y con `node --test` | **Cierto** con el árbol de las 21:22 (3678 y 852) |

---

## 4. Los cuatro defectos

### Defecto 1 · El NIF fusiona dos nombres que no se parecen, y lo marca como **seguro** — gravedad **alta**

**Qué pasa exactamente.** `app/contactos.py::proponer` une dos grupos de nombres cuando comparten un
NIF único (`el_unico_nif`), y **no comprueba en ningún momento que los nombres tengan algo que ver**.
La tabla del §3.1 del informe dice «Son **el mismo nombre** y llevan el mismo NIF → se juntan»: la
primera mitad de esa frase no está en el código. Un NIF tecleado mal (el más fácil de los errores: un
dígito, un número de otro proveedor, un CIF repetido) funde **dos personas distintas** en una sola
ficha, con `motivo="mismo_nif"` y `segura=true`. Y como es segura: **no sale en «se parecen»**, la
pantalla la enseña en «Se pueden apuntar» con su botón, «APUNTARLAS TODAS» la incluye, y
`scripts/migrar_contactos.py --migrar` apunta **todas** las seguras sin preguntar. El agricultor acaba
con un proveedor y otro dentro de la misma ficha, y el segundo nombre solo se ve dentro de los enlaces.

**Cómo lo he provocado** (base temporal, dos facturas, el mismo NIF en las dos):

```python
finca.factura("Juan García López", proveedor_nif="B12345678")
finca.factura("Pedro López Ruiz",  proveedor_nif="B12345678", numero_factura="2026/00999")
logica.se_parecen("Juan García López", "Pedro López Ruiz")   # → False
GET /api/contactos/migracion
```

**Salida literal:**

```
  papel 1: factura 1 de «Juan García López», NIF B12345678
  papel 2: factura 2 de «Pedro López Ruiz»,  NIF B12345678 (el mismo, mal tecleado)
  ¿se parecen esos dos nombres? False
  propuesta «Juan García López» segura=True motivo=mismo_nif nombres=['Juan García López', 'Pedro López Ruiz'] nifs=['B12345678'] escritos=2
  resumen: {'fichas': 1, 'nombres': 2, 'se_parecen': 0, 'homonimos': 0}
  propuestas SEGURAS (las que el guion apunta solo, con --migrar): 1
  aplicar -> 200 {"fichas": 1, "enlaces": 2, "textos_tocados": 0, "nombres": ["Juan García López"], "avisos": [], "contactos": [1]}
  fichas en la base: 1
    ficha: «Juan García López» enlaces=2 nombres_escritos=['Juan García López', 'Pedro López Ruiz']
```

Y no hace falta que sean del mismo tipo de papel. Un proveedor y un laboratorio con el mismo NIF:

```
    propuesta «Suministros Agrícolas Peñaranda» segura=True motivo=mismo_nif
    nombres=['Agrolab Villamuriel', 'Suministros Agrícolas Peñaranda'] papeles=['proveedor', 'laboratorio']
    aplicar -> 200 {"fichas": 1, "enlaces": 2, ...}
```

El propio guion lo cuenta como si fuera una virtud, y ahí está el problema de lectura: para él
**cualquier** coincidencia de NIF es una prueba.

```
    |     · «Cooperativa X»  (3 nombres, Quien te vende el producto)
    |         por qué: los papeles comparten el mismo NIF (B12345678), y eso es una prueba
```

**Qué debería pasar.** Que el NIF una **solo** cuando los nombres además lo permitan: o están escritos
igual, o se parecen (la regla que ya existe, `se_parecen`). Si comparten NIF y los nombres no se
parecen en nada, eso no es una prueba: es **una de las dos cosas mal escrita**, y hay que enseñarlo en
«Estos los tienes que mirar tú» con los dos nombres y los dos NIF delante, como ya se hace con el mismo
nombre y dos NIF distintos. (Se puede discutir cuál es la regla exacta; lo que no se puede sostener es
que hoy la fusión sea silenciosa, automática y se llame «segura».)

**Prueba que lo habría cazado:** ninguna de las 55. `TestLoQueNoSePuedeAsegurarNoSeJunta` prueba el
mismo nombre con dos NIF y dos nombres que se parecen, pero **nunca dos nombres distintos con el mismo
NIF**, que es el caso que hoy se fusiona. La única prueba que junta por NIF
(`test_con_el_mismo_nif_si_se_pueden_juntar`, línea 295) usa dos formas del **mismo** nombre
—«Cooperativa Agricola de Peñaranda» y «COOPERATIVA AGRÍCOLA DE PEÑARANDA S.C.L.»—, que además cazaría
la regla del prefijo por palabras: **es el caso en el que la unión es correcta**, así que la prueba pasa
en verde con el defecto dentro. Y `TestLaLogicaDeLosNombres::test_el_nif_se_compara_sin_puntos_ni_guiones`
prueba que «B-34.123.456» y «b34123456» son el mismo número, que también es correcto. Queda fijado en
`tests/test_revision_t11.py::TestDefecto1ElNifNoPuedeFusionarDosNombresQueNoSeParecen`.

---

### Defecto 2 · Ningún botón de contacto se pulsa en ninguna prueba de JavaScript — gravedad **media**

**Qué pasa exactamente.** Las 32 pruebas de `tests_js/contactos.test.js` **pintan los componentes** con
`renderToStaticMarkup` y miran los `data-accion` que salen en el HTML. Eso comprueba que la pantalla
*pinta*; **no comprueba que el botón haga nada**. En este programa todos los clics los atiende un
**manejador delegado** de `app.js` que lee `data-accion`: un botón cuya acción no llegue al manejador se
pinta, se pulsa y **no pasa nada**, sin ningún error. Es exactamente el fallo que en el T10 escondió
`siembra-nueva` —un botón que no pintaba ninguna pantalla—, y que solo se encontró porque una prueba lo
pulsaba.

**Cómo lo he provocado** (contando lo que hay y lo que no hay):

```powershell
cd F:\EspacioCodigo\CueDigital\backend
(Select-String -Path tests_js\contactos.test.js -Pattern "pulsar|dispatchEvent|manejadores\.click|dataset").Count   # → 0
(Select-String -Path tests_js\interfaz.test.js -Pattern "contacto-" ).Count                                          # → 0
(Select-String -Path tests_js\semillas.test.js -Pattern "async function pulsar").Count                               # → 1
```

**Salida literal** (mi comprobación de las 19 acciones, una por una, en los tres ficheros de `tests_js`):

```
  ¿Se PULSA alguna vez? (se busca un clic de verdad: pulsar/click/dispatchEvent sobre
  el boton, o llamar al manejador delegado que lee data-accion)
    contactos.test.js: mecanismo de pulsar en el fichero = False
    interfaz.test.js: mecanismo de pulsar en el fichero = True
    rutas.test.js: mecanismo de pulsar en el fichero = False
  ¿alguna prueba carga app.js y dispara un clic sobre una accion de contactos?
    «contacto-» dentro de tests_js/interfaz.test.js: 0 apariciones
```

Y el T10, que es el ticket de al lado y el mismo día, **sí lo hace** (`tests_js/semillas.test.js`,
línea 976):

```js
async function pulsar(entorno, accion, datos = {}) {
  const elemento = { dataset: { accion, ...datos } };
  elemento.closest = () => elemento;
  await entorno.manejadores.click({ target: { closest: () => elemento } });
```

**Qué debería pasar.** Que los botones que **escriben** en el cuaderno se pulsen de verdad contra el
manejador: crear, guardar, borrar (con su confirmación), marcar un papel, enlazar, desenlazar, confirmar
la propuesta, apuntarlas todas y deshacer. No hace falta un navegador ni `jsdom`: hace falta copiar el
`pulsar(...)` que ya existe en `tests_js/semillas.test.js` y en `tests_js/interfaz.test.js`.

**Prueba que lo habría cazado:** es el propio defecto; queda fijado en
`tests/test_revision_t11.py::TestDefecto2LosBotonesDeLosContactosNoSePulsanEnNingunaPrueba`.

> **Y una cosa que hice para no acusar en falso, porque este hueco esconde defectos de verdad.** Me
> monté la comprobación que falta por otro camino: pinté las cuatro pantallas **con los textos reales
> del servidor** (`renderToStaticMarkup`, 106 claves de `textos.CONTACTOS`) y, para cada uno de los 19
> botones, comparé los `data-*` que lleva en el HTML con los `elemento.dataset.X` que `app.js` lee en su
> rama. **Resultado: 19 acciones pintadas, 0 problemas, y ningún botón sin ninguna palabra.** Es decir:
> **no he encontrado un botón roto**; lo que he encontrado es que nadie lo comprueba. Eso lo digo aquí y
> en la sección 6, porque un hueco de pruebas y un defecto no son lo mismo.

---

### Defecto 3 · Reenviar la misma confirmación contesta 409 y le dice al agricultor algo que no es verdad — gravedad **media**

**Qué pasa exactamente.** `POST /api/contactos/migracion/aplicar` recalcula la propuesta con los textos
**libres** y busca la clave pedida. La primera vez enlaza los nombres; en el reenvío, esos mismos
nombres ya tienen dueño (los ha enlazado el propio servidor hace un segundo), así que ya no están en la
propuesta, la clave no aparece y contesta **409** con el mensaje `C4_la_propuesta_ha_cambiado`:

> «La lista de nombres ha cambiado desde que la miraste, así que no he apuntado nada. Vuelve a mirarla
> y apunta lo que quieras apuntar.»

La segunda frase es falsa: **sí se ha apuntado**. El contrato (§2, «Escrituras y revisiones») pide lo
contrario: *«Cada comando de negocio lleva identificador único de petición… Reenviar el mismo comando
devuelve su resultado; no crea otro movimiento.»* No se duplica nada —eso está bien—, pero el reenvío no
devuelve su resultado, y encima miente sobre lo que ha pasado.

**Cómo lo he provocado** (el mismo `POST` dos veces con la misma clave; el camino es real: el botón de
apuntar no se deshabilita mientras se envía, así que un doble toque con guantes hace exactamente esto):

```python
claves = [p["clave"] for p in finca.revision()["propuestas"] if p["segura"]]
finca.aplicar(claves)   # primera vez
finca.aplicar(claves)   # el reenvío
```

**Salida literal:**

```
  claves a confirmar: ['6604dba5c9197bb4']
  primera vez  -> 200 {"fichas": 1, "enlaces": 2, "textos_tocados": 0, "nombres": ["Cooperativa X"], "avisos": [], "contactos": [1]}
  segunda vez (EL MISMO reenvio) -> 409 La lista de nombres ha cambiado desde que la miraste, así que no he apuntado nada. Vuelve a mirarla y apunta lo que quie
  fichas=1 enlaces=2 (deben ser 1 y 2: no se ha duplicado)
```

**Qué debería pasar.** Cualquiera de las dos salidas honestas: devolver el mismo resultado (la ficha ya
está apuntada), o contestar 200 diciendo que ya estaba apuntado. Lo que no vale es decir que la lista ha
cambiado cuando lo único que ha cambiado es que el servidor hizo su trabajo.

**Prueba que lo habría cazado:** ninguna. Sus tres pruebas de la migración comprueban la primera
confirmación, la clave desconocida y la clave insegura, pero **no el reenvío de la misma**. Queda fijado
en `tests/test_revision_t11.py::TestDefecto3ReenviarLaMismaConfirmacion`.

---

### Defecto 4 · La clave de la propuesta no cubre el texto, así que se puede confirmar algo distinto de lo que se enseñó — gravedad **baja**

**Qué pasa exactamente.** `contactos_api._la_clave` es la huella de **dónde** están los textos
(`tabla:campo:registro_id`), no de lo que dicen. Si entre mirar y confirmar el texto cambia **de una
forma que no cambia la agrupación** (mayúsculas, espacios), la clave sigue valiendo: el servidor
recalcula la propuesta, la encuentra, y apunta una ficha con el **nombre nuevo**, que no es el que se le
enseñó al agricultor. El §3.6 promete «o se apunta lo que se enseñó, o no se apunta», y aquí se apunta
otra cosa. El daño es pequeño (hoy solo entran cambios de mayúsculas y espacios, porque cualquier otro
cambio reagrupa y la clave deja de existir), pero la promesa es la promesa, y es la misma familia que
la clave de reenvío del almacén.

**Cómo lo he provocado:**

```python
ensenada = la propuesta  # «Cooperativa X», clave 6604dba5c9197bb4
# entre mirar y confirmar, el papel se corrige:
finca.escribir_factura(f2, "COOPERATIVA X")
finca.aplicar([ensenada["clave"]])
```

**Salida literal:**

```
  Caso B: entre mirar y confirmar se cambia SOLO la forma de escribirlo (mayusculas)
    se ensena: «Cooperativa X» clave=6604dba5c9197bb4
    ahora los papeles dicen: 'COOPERATIVA X'
    aplicar con la clave de antes -> 200 {"fichas": 1, "enlaces": 2, "textos_tocados": 0, "nombres": ["COOPERATIVA X"], "avisos": [], "contactos": [1]}
      ficha creada: «COOPERATIVA X» (lo que se enseno era «Cooperativa X»)
```

**Qué debería pasar.** Que la huella incluya **el texto** de los escritos que forman la propuesta. Así
cualquier corrección entre mirar y confirmar cambia la clave y el servidor contesta 409, como ya hace
con los demás cambios (comprobado: corregir el nombre de una factura **sí** da 409, porque reagrupa).

**Prueba que lo habría cazado:** la prueba del §3.6 cubre la factura nueva (409) pero no la corrección
del texto. Queda fijado en `tests/test_revision_t11.py::TestDefecto4LaClaveNoCubreElTexto`.

---

## 5. Imprecisiones de la documentación (medidas, sin prueba que falle, y digo por qué)

No son defectos del programa y **no he escrito pruebas que fallen por ellas**, porque un rojo que no se
puede arreglar en el código acaba en un `xfail` y un `xfail` acaba tapando otra cosa. Pero el informe se
lee para decidir, así que lo digo con la medida delante.

1. **§3.1, la tabla: «Son el mismo nombre y llevan el mismo NIF → se juntan».** El código no comprueba
   la primera mitad de la frase (defecto 1). Es el renglón que más se va a leer de ese documento,
   porque es la excepción que el ticket admite.
2. **§1.3 y §3.4: «con el texto tal y como lo escribió él».** Lo que devuelve el servidor pasa por
   `contactos.limpia()`, que colapsa los espacios de dentro. Medido:
   `lo que hay escrito en la factura: '  Cooperativa   X  '` → `lo que devuelve el servidor: 'Cooperativa X'`.
   El texto guardado en la factura **no se toca** (eso es verdad y es lo importante), y el schema dice
   de sí mismo «`texto` es el nombre original y no se toca nunca»: son las dos frases las que se pasan
   de largas. Cuando el aviso de «ahí pone otra cosa» compara, compara ya limpio: si el agricultor
   corrigiera solo los espacios, el programa no diría nada.
3. **«Sin vale de sesión: 401 en las siete puertas»** (§5) y **«las siete puertas, sin repetir»** (§5).
   En el mismo documento, §2 habla de **doce puertas HTTP**, y «las siete puertas» es como se llaman en
   `contactos.py` los **siete sitios donde hay un nombre escrito**. La prueba
   (`TestSinValeDeEntrada`) comprueba 401 en **siete rutas HTTP**, que son un subconjunto de las doce
   (las otras cinco —`PUT`/`DELETE` de una ficha, papeles, enlazar y desenlazar— dependen del mismo
   `UsuarioActual`, así que están cubiertas por el mismo mecanismo). Se lee como si fueran todas.
4. **`PUT /api/contactos/{id}` sin `papeles` borra los papeles de la ficha.** Medido: al corregir una
   ficha de la migración mandando solo el nombre y el teléfono, sus papeles pasan de 1 a 0. La pantalla
   los manda siempre (`recogeLaFichaDeContacto` los lee del estado), así que **no es alcanzable desde el
   agricultor**; pero la puerta trata un campo ausente como «quítalos todos», y eso, con dos usuarios
   editando a la vez, es una pérdida de trabajo silenciosa (el contrato §2 pide «comparación de cambios,
   no sobreescritura»).
5. **Las tres tablas nuevas no guardan autor ni versión.** El contrato §2 pide, para toda entidad de
   negocio, «autor, fecha de creación, versión y estado de anulación». `contactos` tiene `creado_en` y
   nada más: no se puede saber quién apuntó una ficha, y `aplicar_la_migracion` no deja rastro en
   `auditoria` (sí lo dejan corregir, borrar y deshacer, que pasan por `correcciones`). El §6 del
   informe no lo declara entre sus límites.
6. **El recuento del §5 se ha quedado corto, y no es culpa suya.** El informe dice «3678 pruebas, 0
   fallos» con el árbol de las 21:22, y era verdad en ese momento (yo lo medí: 3678). A las 21:37 la
   suite recoge **3682** sin contar el fichero de esta revisión: **cuatro pruebas más**, recogidas con
   `backend/tests/conftest.py` del 21:27:30. Los tres documentos siguen diciendo 3678, así que el
   guardián `test_lista_de_la_junta.py::test_el_numero_de_pruebas_de_python_es_el_de_verdad` se pone rojo
   con la suite entera **aunque esta revisión no hubiera añadido nada**. Es exactamente el fallo que el
   §6.2 del informe declara como riesgo, y el que este proyecto ya ha pagado dos veces en el mismo día:
   **un número escrito a mano en tres documentos se queda viejo solo**.

---

## 6. Lo que he intentado romper y **no** he podido (medido, no supuesto)

Esto también es un resultado, y en este proyecto vale tanto como los defectos.

1. **Aislamiento entre fincas (lo más grave si se rompe).** Dos cuentas de verdad, un contacto y una
   factura con su enlace en la finca uno, y **siete ataques** desde la finca dos:

   ```
   GET la ficha de otra finca: 404            PUT la ficha de otra finca: 404
   DELETE la ficha de otra finca: 404         POST un papel en la ficha de otra finca: 404
   POST un enlace en la ficha de otra finca: 404
   POST un enlace de MI ficha a la factura de OTRA finca: 404
   DELETE el enlace de otra finca: 404
   la finca dos ve contactos: ['Contacto de Dos', 'Mia']
   la finca dos ve nombres escritos: []
   la finca dos ve propuestas: []
   ```

   404 y no 403, como manda la casa: desde fuera no se puede ni saber si existe.
2. **Un texto escrito, dos dueños.** La segunda ficha que pide el mismo texto recibe
   `409 Ese nombre ya está enlazado con la ficha Cooperativa Agrícola de Peñaranda. Si no es el mismo,
   quítalo de allí primero.`, y en la base sigue habiendo **una sola fila** de enlace. Reenviar el mismo
   enlace, otras 409 y ni una fila más.
3. **Duplicar al reintentar.** Marcar el mismo papel tres veces deja **2 filas** (los dos papeles
   distintos) y no tres; reenviar la confirmación no crea una segunda ficha ni enlaces de más; borrar
   una ficha deja sus nombres **libres otra vez** para que se puedan volver a enlazar.
4. **«No se sabe» convertido en cero o en permiso.** `es_empresa` con tres respuestas: `None` vuelve
   como `None`, `True` como `True`, `False` como `False`, y `telefono=""` / `nif="   "` se guardan como
   `None` («no lo sé»), no como cadena vacía. `anulada` tiene tres respuestas (`True`/`False`/`None` =
   «esa tabla no lo dice»). El papel inventado da 422 y **no guarda la ficha a medias**.
5. **§3.7, deshacer, de verdad.** Migración (2 fichas, 4 enlaces), luego el agricultor se apunta una
   ficha a mano **y** le enlaza un nombre, y corrige una de las de la migración. Deshacer:
   `{"fichas": 1, "enlaces": 4, "se_quedan": ["Cooperativa X no se ha quitado: la has corregido o le has
   enlazado algo tú, así que es tuya."], "textos_tocados": 0}` → quedan las dos fichas suyas, con sus
   enlaces, y los cuatro nombres escritos vuelven a estar sin dueño. Los textos de las facturas,
   idénticos. (La prueba que lo fija está en el fichero de esta revisión.)
6. **§3.9, el informe del guion no toca el esquema.** Fabricando yo una base «vieja» (todo el esquema
   actual menos las tres tablas del T11) y pasándole el guion sin `--migrar`:

   ```
   tablas nuevas tras el informe: []
   huella antes:   849e082e94702f4ca99f3d7feebd2e44b16112556ca662d0427265dd3152f93e
   huella despues: 849e082e94702f4ca99f3d7feebd2e44b16112556ca662d0427265dd3152f93e
   ```

   Con las tablas ya puestas (`651.264` bytes) pasa lo mismo, y `--migrar` y `--deshacer` funcionan de
   verdad, con `SinCuenta` (`usuario_id = None`) y la huella de los nombres idéntica antes y después.
7. **§3.8, la misma regla que la pantalla.** El guion nombra `api.aplicar_la_migracion`,
   `api.deshacer_la_migracion` y `logica.proponer`, y **no tiene ni un `UPDATE`** (ni él ni el router).
8. **Todo o nada.** Una clave segura y una insegura en la misma petición, en los dos órdenes: 409 y
   **cero fichas y cero enlaces** creados.
9. **El aviso de que el papel ha cambiado.** Enlazar, corregir la factura y leer la ficha:
   `texto = 'Cooperativa Y'`, `texto_de_entonces = 'Cooperativa X'`, `texto_cambiado = True`.
10. **Los botones, por el lado que sí se puede comprobar sin navegador.** Las 19 acciones de T11 salen
    pintadas en algún escenario, **cada botón lleva los `data-*` que el manejador lee** (`data-id`,
    `data-papel`/`data-puesto`, `data-tabla`/`data-campo`/`data-registro`, `data-clave`), y **ningún
    botón se queda sin palabra** (incluido el cambio de las 21:19 del rótulo de buscar, que sigue
    diciendo «BUSCAR» / «VERLAS TODAS»).
11. **La caché del campo.** `service-worker.js` lleva los dos ficheros nuevos en `FICHEROS` y sube a
    `cuedigital-2026-10-03-66`, que es la versión del pie en `app.js` (`VERSION_DE_LA_APLICACION`).
12. **El umbral del «se parecen».** Los cinco números del §3.2 recomputados salen **exactos**, y el
    umbral (0,93) cae en el hueco medido (0,9231 – 0,9474). *(Lo que el número no caza, y conviene
    saberlo: una errata en un nombre **corto** —«Juan»/«Juna», 0,7500; «Agrolab»/«Agrolav», 0,8571— no
    llega al umbral. No es un defecto de este ticket, porque la dirección segura es no juntar, y la
    regla de «uno es el principio del otro» sí caza los nombres con apellido; pero el comentario del
    código promete que una errata siempre avisa, y no siempre avisa.)*

---

## 7. Lo que **no** he podido comprobar

1. **El ensayo del §5 sobre la copia de la base de verdad.** Mi encargo prohíbe abrir y copiar
   `backend/cuedigital.db`, así que **no lo he reproducido**: lo he hecho con una base que fabrico yo
   (esquema actual sin las tres tablas del T11) y con bases temporales de la suite. Lo que el informe
   cuenta de ese ensayo (la huella que no cambia, 1 ficha y 1 enlace, y el «en la finca de David hay 0
   nombres escritos») no lo he verificado, y no puedo.
2. **La comprobación en un navegador de verdad (§5: «30 de 30 en verde», las capturas a 390, 1024 y
   1440 px).** El guion vivía en la carpeta temporal y se borró; no he podido volver a lanzarlo. Lo que
   sí he comprobado es **de qué se puede fiar uno**: `scripts/comprobar_en_un_navegador.py` **no tiene
   ni una mención de «contactos»** (0 apariciones), así que sus dos pantallas nuevas **no** están
   cubiertas por la comprobación del coordinador —la petición del §7.1 es correcta—, y `scripts/humo.py`
   no tiene ninguna comprobación de contactos (la única palabra «contactos» del fichero es la del
   correo de la Junta, línea 1299). **Ninguna de mis medidas dice que las pantallas se dibujen en un
   navegador de verdad**: eso está sin comprobar por mi parte.
3. **El aspecto en el móvil de verdad** (sol, guantes, 50-70 años). No he visto las capturas ni he
   medido nada a 390 px.
4. **El uso con muchos papeles.** Mis pruebas usan 2, 3 y 6 nombres escritos, como la suite. Una base
   con cientos de facturas repetidas no la he probado, y ahí `_los_escritos` recorre **todas** las filas
   de siete tablas en cada carga de la lista de contactos (`listar` llama a `_los_escritos` y luego a
   `_los_papeles` por cada ficha): es la parte del ticket que no está medida y que el §6.1 del informe
   declara. **No he medido el tiempo**, así que no digo que sea lento: digo que no lo sé.
5. **Dos cosas a la vez.** No he probado dos peticiones simultáneas (dos pestañas, dos usuarios). El
   aislamiento y la unicidad del enlace tienen que aguantarlo, y una carrera entre dos enlaces al mismo
   texto acabaría en un error de la restricción única (500) en vez de un 409: no lo he provocado.
6. **El reenvío desde el móvil sin cobertura.** No aplica por dónde va: los contactos escriben con
   `mandarCambio`, que **no pasa por la cola** (`enviarOApuntar` es la que encola, y solo la usan los
   apuntes). Así que el «bucle del móvil al reenviar» de otros tickets **no tiene camino aquí**, y por
   eso no lo he podido atacar. Lo único parecido es el doble toque del defecto 3.
7. **La retirada de una ficha con papel o enlace huérfano**: no he probado qué pasa si se borra una
   fila de otra tabla por detrás (por ejemplo, un `DELETE` de factura por SQL). El código dice que un
   enlace sin documento no se cuenta ni se enseña; **lo he leído, no lo he provocado**.

---

## 8. Lo que cuesta esta revisión, dicho antes de que se pregunte

- **`backend/tests/test_revision_t11.py` deja la suite en 5 fallos** mientras los cuatro defectos
  existan: los 4 de la sección 4 (que no se pueden relajar ni borrar; cuando se arregle cada uno, su
  prueba se pone verde sola) y el guardián de los recuentos. **Sin ese fichero, el guardián también se
  pone rojo**, porque los tres documentos dicen 3678 y la suite recoge 3682: eso ya no es cosa de esta
  revisión, es que el árbol creció cuatro pruebas después de que se actualizaran.
- **El número de los tres documentos** (`README.md` línea 1378, `AGENTS.md` línea 45 y
  `docs/LO_QUE_PIDE_LA_JUNTA.md` línea 22) hay que volver a **medirlo** al actualizarlos: con el fichero
  de esta revisión dentro y el árbol de las 21:37 son **3688** los recogidos y **3686** los ejecutados, y
  esa diferencia de dos la cuento yo aquí en vez de esconderla. Lo digo yo en vez de dejar que se
  descubra con el guardián en rojo.
- **No he tocado ni una línea del código de T11 ni de sus pruebas.** Lo único que he creado son
  `docs/REVISION_T11.md` (este informe) y `backend/tests/test_revision_t11.py`.

---

## 9. Resumen

**Cuatro defectos.** Uno **alto** (el NIF fusiona dos nombres que no se parecen y lo llama «seguro», y el
guion lo aplica solo: es exactamente la fusión que el ticket existe para impedir), dos **medios** (los
botones de contacto no se pulsan en ninguna prueba de JavaScript —el hueco que en el T10 escondió un
botón que no pintaba nada—, y reenviar la misma confirmación contesta 409 diciendo que la lista ha
cambiado cuando no ha cambiado) y uno **bajo** (la clave de la propuesta no cubre el texto, así que se
puede apuntar un nombre distinto del que se enseñó). Aparte, seis imprecisiones de la documentación,
medidas y sin prueba que falle, con su motivo.

**Lo que no he podido romper, y lo digo con las medidas delante:** el aislamiento entre fincas (siete
ataques, siete 404), el «un texto escrito no puede tener dos dueños» (409 con el nombre del dueño, una
sola fila), el «enlazar no borra el nombre», el «deshacer no se lleva el trabajo del agricultor» (ficha
y enlace hechos a mano que sobreviven, `textos_tocados: 0`), el «el informe del guion no toca ni un
byte», el «el guion usa la misma regla que la pantalla y no tiene ni un `UPDATE`», el «todo o nada» de
la confirmación, los tres estados de `es_empresa`, el umbral medido del «se parecen», y que cada botón
de las cuatro pantallas lleve los datos que su manejador lee.

**Lo que el ticket tiene de bueno, y no es cortesía:** la decisión de §3.3 —el enlace en su propia tabla
en vez de un `contacto_id` en cada documento— es la que hace que deshacer sea borrar lo que se creó y
que ningún papel histórico se toque, y está sostenida por el código, por el guion y por las pruebas. Y
las tres tablas nuevas llevan su `explotacion_id` y todo pasa por `obtener_de_la_explotacion`: el
aislamiento, que es lo que más caro se paga en este proyecto, está bien hecho.
