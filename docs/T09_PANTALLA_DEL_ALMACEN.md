# T09 — La pantalla del almacén

**Qué es esto.** El ticket T09 tenía dos mitades: el servidor (el artículo, el lote, el movimiento y la
recepción, con sus quince rutas en `backend/app/routers/almacen_api.py`) y **la pantalla**, que es lo que
faltaba. El servidor ya estaba terminado y verificado (128 pruebas). Aquí se cuenta **la pantalla**: qué
se puede hacer ya desde el móvil y desde el ordenador, qué ficheros se han tocado, qué pruebas lo
sostienen, **qué falta en la API** y **lo que no se ha podido comprobar**.

Fecha: 03/10/2026.

---

## 1. Qué se puede hacer ahora (una línea por cosa)

1. **Apuntar un albarán con sus líneas** — artículo (de la lista o el nombre del papel), cantidad,
   unidad, nº de lote, caducidad, envase y dónde se guarda — y al guardarlo el servidor crea los lotes y
   las entradas del libro. Con los tres finales: se guarda (y se dice que la mercancía ya está dentro),
   falta un dato y se dice cuál, o **no se ha podido comprobar** (sin cobertura se queda en el móvil y se
   manda solo, y si el papel no trae número se dice que no se ha podido comprobar si ya estaba).
2. **Ver lo recibido y abrir un albarán** — la lista de lo que ha llegado (con su número, su proveedor,
   su fecha y cuántas líneas trajo) y su ficha, con lo que venía línea a línea, de qué lote era cada cosa
   y hasta cuándo vale.
3. **Ver las existencias por artículo y por envase**, con lo que queda **de cada lote** y el desglose de
   sus movimientos uno debajo de otro (entró, salió, se perdió, conteo distinto), diciendo cuáles no
   cuentan y por qué. **Cuando el saldo no se sabe, se dice que no se sabe** («No se puede saber lo que
   queda») con su motivo, nunca con un 0.
4. **El aviso de «comprado y aún sin entrar»**: lo que está en facturas y no ha entrado, para que nadie
   crea que el programa ha perdido producto. Va aparte y **no se suma** nunca a las existencias.
5. **Apuntar una merma, un ajuste o una entrada sin papel**, con su motivo obligatorio, y ver después el
   movimiento en el libro con su «no cuenta y por qué» cuando lo esté (un albarán anulado, un apunte
   anulado).
6. **Anular un albarán** con su motivo: no se borra nada y sus entradas dejan de contar.
7. **Sacar de un envase lo que se gastó en un apunte** — el botón vive **en el apunte**, en «mi cuaderno»
   —, la cantidad **la dice el apunte** (el servidor la copia; no se teclea) y el resultado enseña **las
   dos cuentas con su nombre**: «Lo que se ha sacado del envase» y «Cuánto por hectárea». Cuando el apunte
   solo trae lo de cada hectárea, el programa **pide el total** en vez de multiplicarlo. Y si lo que sale
   deja el envase en negativo, se avisa con los números y el agricultor decide («sí, la diferencia es de
   verdad»).
8. **Enganchar la factura que llega después** a un albarán ya recibido, con la propuesta del servidor
   (`posibles-recepciones`): la pantalla **propone y no escribe** —elegir la factura solo pregunta—, y el
   enganche **no lleva ni una cantidad**, porque la mercancía entró una vez, el día del albarán.

---

## 2. Ficheros creados y tocados

### Nuevos

| Fichero | Qué es |
|---|---|
| `backend/web/react/pantallas/libro_del_almacen.js` | El libro: lo que ha llegado, lo que queda envase por envase y lo que ha pasado. |
| `backend/web/react/pantallas/nuevo_albaran.js` | El alta del albarán, con sus líneas. |
| `backend/web/react/pantallas/recepcion.js` | La ficha de un albarán: sus líneas, anularlo y decir de qué factura es. |
| `backend/web/react/pantallas/movimiento_de_almacen.js` | Una merma, un ajuste o una entrada sin papel. |
| `backend/web/react/pantallas/sacar_de_un_lote.js` | Sacar de un envase lo que se gastó en un apunte. |
| `backend/web/react/pantallas/enganchar_la_factura.js` | Decir de qué factura es un albarán (propuesta del servidor). |
| `docs/T09_PANTALLA_DEL_ALMACEN.md` | Este documento. |

### Tocados

| Fichero | Qué se le ha hecho |
|---|---|
| `backend/app/textos.py` | **Solo añadiendo**: 178 textos nuevos en el bloque `LIBRO_DEL_ALMACEN`, que se sirve **dentro de `cesta`** (el porqué, abajo). Ningún texto existente se ha cambiado. |
| `backend/web/app.js` | Las seis pantallas, el estado del libro, las acciones del manejador de clics, las dos direcciones nuevas, los botones que las abren, la versión (a `2026-10-03-63`) y un aviso más en el retorno de `enviarOApuntar` (el estado del 4xx). |
| `backend/web/react/pantallas/cesta.js` | **Un botón**: «VER EL LIBRO DEL ALMACÉN». La cesta sigue enseñando exactamente los mismos números que antes. |
| `backend/web/react/pantallas/mi_cuaderno.js` | No se ha tocado (el botón de sacar del almacén se le pasa en sus `acciones` desde `app.js`). |
| `backend/web/react/rutas.js` | Las dos direcciones: `#/almacen/libro` y `#/almacen/recepcion/<id>`. |
| `backend/web/service-worker.js` | Los seis ficheros nuevos en `FICHEROS` y la caché a `cuedigital-2026-10-03-63`. |
| `backend/tests_js/interfaz.test.js` | La copia de los textos del almacén, los mensajes `AL*` que se usan antes de llamar al servidor, y **21 pruebas nuevas** (20 del almacén y 1 del botón del apunte). |
| `backend/tests_js/rutas.test.js` | Las dos direcciones nuevas en la tabla y el identificador de la ficha del albarán. |
| `docs/REACT.md` | La tabla de pantallas (seis filas nuevas) y la cuenta de la lista `PANTALLAS_EN_REACT`. |

### Lo que NO se ha tocado (y se dice, porque es la mitad del encargo)

- **Nada del servidor** salvo `textos.py`: `almacen_api.py`, `models.py`, `schemas.py`, `servicios.py`,
  `database.py`, `main.py`, `interfaz.py` y el resto de los routers están **exactamente igual**.
- **`docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md`** (es del coordinador), `scripts/**` y las **pruebas de
  Python** (ni una línea).
- **La cesta vieja sigue funcionando igual**: `pantallaCesta()` no cambia de comportamiento, y la prueba
  que fija que `/api/productos/cesta/situacion` devuelve lo mismo sigue pasando (la suite del servidor de
  T09 y `tests/test_cesta_del_almacen.py` en verde).

---

## 3. Las decisiones que hay que entender antes de tocar esto

### 3.1. El servidor cuenta, la pantalla no

Ni una resta, ni una suma, ni una conversión en los componentes: lo que queda, lo que entró, lo que salió
y **lo que va por hectárea** llegan contados del servidor, con su etiqueta. Es lo que impide el error de
diez veces («dos litros» por hectárea no son dos litros gastados): la cantidad de una salida **la dice el
apunte**, y el total y la dosis se enseñan en **dos filas distintas, cada una con su nombre**.

### 3.2. Un dato que no se sabe no es un cero (y no se enseña una cuenta a medias)

- Un envase del que no consta la cantidad o la unidad sale con **«No se puede saber lo que queda»** y el
  motivo del servidor. Nunca con un 0, que diría que no queda nada.
- Una caducidad que no se ha mirado **no se cuenta como vigente**: son tres estados (caducado, en fecha y
  «no se sabe cuándo caduca»), y los tres se dicen con palabras además del color.
- Las **cuatro cuentas de un artículo** (entró, salió, se perdió, conteo distinto) **solo se enseñan
  cuando suman todo lo que hay**. Si el servidor dice que hay movimientos sin cantidad, sin unidad o
  unidades que no se pueden comparar, se callan: un «Entró 0,00» con una entrada de la que no se sabe
  cuánto parecería que no entró nada. **Esto se vio en una captura**, no en un test.

### 3.3. Lo que se apunta sin cobertura se queda en el móvil, con su clave de reenvío

La clave se pide **al abrir el formulario**, no al guardar: si se pidiera al guardar, dos pulsaciones del
mismo botón (o el reenvío de la cola del móvil, que manda el mismo cuerpo) llevarían claves distintas y el
mismo albarán entraría dos veces en el almacén. Hay una prueba que comprueba que las dos pulsaciones
mandan **la misma clave**, y otra que comprueba que un albarán nuevo lleva una clave nueva.

### 3.4. Proponer no es escribir

La pantalla de enganchar la factura **no tiene ningún campo de cantidad**, y hay una prueba que mira que,
al abrirla y al elegir una factura, **no se ha mandado ningún POST**: solo cuando el agricultor dice
«sí, es esta» se manda el enganche, con las líneas que el servidor ha casado y sin una sola cantidad.

### 3.5. Los textos viven dentro del bloque del almacén (`cesta`), y por qué

`/api/interfaz` sirve los bloques **por su nombre, uno a uno** (`routers/interfaz.py`), y
`textos.ALMACEN` **no está en esa lista** (sirve `cesta`, no `almacen`). Un bloque nuevo en `textos.py`
**no llegaría a la pantalla**: el componente pediría `t("almacen.…")` y el texto saldría en blanco. Y los
textos que llegan solo dentro de una respuesta de la API **no se guardan en el móvil**, así que sin
cobertura la pantalla saldría vacía justo cuando más falta hace.

Por eso los 178 textos nuevos viven en `CESTA` (el bloque del almacén, que sí se sirve y que el móvil se
guarda para abrir sin cobertura), con el prefijo `libro_` y **añadidos sin tocar ninguno de los que ya
estaban**. El arreglo limpio es **una línea en `routers/interfaz.py`**:

```python
"almacen": textos.ALMACEN,
```

…y `"libro": textos.LIBRO_DEL_ALMACEN`. **No se ha hecho porque este ticket no podía tocar los routers**
(«nada del servidor salvo `textos.py`»). Está en la lista de lo que falta, abajo, con lo demás.

---

## 4. Lo que falta en la API (no se ha tocado: se dice)

1. **`textos.ALMACEN` no se sirve en `/api/interfaz`.** Es el motivo de la decisión 3.5. Se arregla con
   una línea (`"almacen": textos.ALMACEN`) y entonces los textos podrían volver a su bloque.
2. **`FertilizacionSalida` no devuelve `fertilizante_id`.** Para saber de qué envase sale un abono, la
   pantalla tiene que **casar el nombre** del abono del apunte con el nombre del artículo del almacén
   (comparados como los compara el servidor: sin tildes, sin mayúsculas y sin espacios de más). Con un
   `fertilizante_id` en la respuesta sería exacto, como ya lo es el de un tratamiento (`producto_id`). Hay
   una prueba de que, si no casa ninguno, la pantalla dice «de esto no hay nada apuntado todavía en el
   almacén» en vez de enseñar los envases de otro producto.
3. **`LineaDeRecepcionSalida` no devuelve el envase ni el sitio donde se guardó** (`presentacion`,
   `contenido_por_envase` y `ubicacion` viven en el `Lote`, y la línea del albarán no los devuelve). La
   ficha del albarán los enseña **buscándolos en las existencias** por el identificador del lote, y cuando
   ese dato no está cargado esas dos filas no se pintan. Con tres campos más en la respuesta, la ficha se
   armaría sola.
4. **No hay ninguna puerta para dar de alta un artículo suelto desde la pantalla.**
   `POST /api/almacen/articulos` existe (y su comentario dice para qué: «la semilla que se guarda de un
   año para otro, un producto que ya estaba en la nave»), pero **no tiene pantalla**: lo que ya estaba en
   el almacén antes de usar el programa se apunta como una entrada a mano, y si el artículo no existe
   todavía hay que apuntar un albarán escrito a mano, que es la única puerta que crea artículos. Es la
   diferencia entre «puedo apuntar lo que ya tenía» y «puedo darlo de alta como es debido», y queda dicho
   aquí.
5. **Ninguna respuesta del almacén lleva un código de error, solo el número de estado y el texto.** Para
   distinguir «este apunte solo trae la dosis» de «el envase se queda en negativo» (los dos son 409) la
   pantalla mira el estado y, en el primer caso, el texto del mensaje. Con un `codigo` en el cuerpo
   (como el `motivo_codigo` que ya llevan las cuentas) se podría mirar el código y no la frase.

---

## 5. Las pruebas

### JavaScript: `cd backend; node --test "tests_js/*.test.js"`

**734 pruebas, 734 en verde** (antes de este trabajo: 712). **Se han añadido 21**: veinte del almacén y
una del botón del apunte en la tabla del cuaderno. Las tres que comprobaban los botones de un apunte se
han **actualizado** (no borrado): ahora hay tres botones y el primero es el del almacén.

Las veinte pruebas del almacén, cada una en una frase:

1. desde el almacén se llega al libro, y llega con lo que ha llegado, lo que queda y lo que ha pasado;
2. lo comprado que todavía no ha entrado se dice, para que nadie crea que se ha perdido;
3. un saldo que no se sabe se dice como que no se sabe, y nunca como un cero;
4. las existencias llegan por envase, con su caducidad y el desglose de cada lote;
5. apuntar un albarán con sus líneas, de punta a punta;
6. el mismo albarán se manda con la misma clave de reenvío las dos veces;
7. un albarán que ya estaba apuntado se dice, y no se cuenta dos veces;
8. un albarán apuntado sin cobertura se queda en el móvil y se manda solo;
9. un albarán sin número dice que no se ha podido comprobar si ya estaba;
10. una línea sin decir qué ha llegado no se manda: se dice cuál falta;
11. una línea sin unidad se manda como que no se sabe, no como un cero;
12. la merma pide el motivo antes de apuntar nada;
13. una cantidad sin unidad no se resta a ciegas: se dice y no se hace la cuenta;
14. sacar de un envase desde el apunte: la cantidad la dice el apunte y salen las dos cuentas con su nombre;
15. el apunte que solo trae lo de cada hectárea pide el total en vez de multiplicarlo;
16. si lo que sale deja el envase en negativo, se avisa y hay que decir que la diferencia es de verdad;
17. enganchar la factura propone y no escribe: solo se engancha cuando el agricultor dice que sí;
18. las cuentas de un artículo solo se enseñan cuando se pueden sumar enteras;
19. el libro y la ficha de un albarán tienen su dirección, y recargar las abre;
20. la copia de los textos del almacén dice lo mismo que el servidor (y la que comprueba que ese lector
    funciona, que es la regla de esta casa: **un test que lee ficheros necesita su propia prueba**).

### Python (las que vigilan la interfaz)

```bash
cd backend
../.venv/Scripts/python.exe -m pytest tests/test_interfaz.py tests/test_la_migracion_a_react.py \
  tests/test_los_botones_hacen_algo.py tests/test_el_armazon_del_ordenador.py \
  tests/test_que_no_falte_ningun_texto.py tests/test_sin_jerga.py tests/test_la_version_visible.py \
  -q -p no:randomly --junit-xml=$env:TEMP\ui.xml
```

**167 pruebas, 0 fallos** (leído del XML). Incluye los guardianes que vigilan lo que este trabajo toca:
que ningún texto se quede sin servir, que no haya jerga, que todo botón pintado tenga quien lo atienda,
que la migración a React esté completa, que la caché del campo lleve los ficheros nuevos y que la versión
del pie y la de la caché sean la misma.

### Un aviso: el recuento de pruebas de la documentación

Al añadir 21 pruebas de JavaScript, **el recuento escrito en `README.md`, `AGENTS.md` y
`docs/LO_QUE_PIDE_LA_JUNTA.md` (712) se queda viejo**, y hay una prueba de Python que lo exige
(`tests/test_lista_de_la_junta.py::TestElResumenCuadraConLaTabla::test_los_numeros_de_test_de_la_documentacion_no_se_quedan_viejos`).
Esa prueba **no está en la lista de las que este ticket manda dejar en verde**, y esos tres ficheros **no
están en la lista de los que se pueden tocar**, así que **no se han tocado**: queda apuntado aquí con las
tres líneas exactas que hay que cambiar (de 712 a 734).

- `README.md`: `tests_js/*.test.js"   # 712 tests`
- `AGENTS.md`: `# JavaScript (712 tests)`
- `docs/LO_QUE_PIDE_LA_JUNTA.md`: `y 712 de JavaScript`

### Comprobado en un navegador de verdad

```bash
CUEDIGITAL_DATABASE_URL=sqlite:///<temporal> CUEDIGITAL_SECRETO=lo-que-sea \
  CUEDIGITAL_ADJUNTOS=<temporal> ../.venv/Scripts/python.exe -m uvicorn app.main:app --port 8024
../.venv/Scripts/python.exe scripts/comprobar_en_un_navegador.py http://127.0.0.1:8024
```

**Resultado: la interfaz se abre y se dibuja en un navegador de verdad** — todas las rutas que recorre el
guion (17 pantallas y 7 paradas del asistente, más la versión de ordenador, 1024 px y 720 px) en verde,
sin el aviso de emergencia de React y sin que ningún paso se quede sin encontrar lo que busca. El servidor
de la prueba se ha dejado parado y su carpeta temporal borrada.

Y además se miraron **a ojo** las pantallas nuevas, con capturas hechas con el mismo guion (sin
modificarlo), a **dos anchos: 500×1400 (móvil) y 1440×900 (ordenador)**: el libro, la ficha de un
albarán, el alta de un albarán, la merma, sacar de un envase, la propuesta de factura y las dos
direcciones (`#/almacen/libro` y `#/almacen/recepcion/<id>`) abiertas directamente. **De mirarlas
salieron dos arreglos de verdad**: el «Entró 0,00» de las cuentas a medias (decisión 3.2) y el rótulo
«El papel no lo dice» en el formulario de una merma, que no tiene ningún papel detrás. Y un tercero, que
solo se ve en un navegador: la ficha abierta **por su dirección** enseñaba menos que la abierta desde el
libro (le faltaban el envase y el sitio), porque las existencias llegaban después del primer pintado.

---

## 6. Lo que NO se ha hecho, y por qué

1. **La tabla del ordenador para estas listas.** El libro, la lista de albaranes y las existencias van en
   tarjetas, como las otras listas que aún no tienen tabla (lo dice `docs/REACT.md`: «las tablas de las
   listas que quedan» están pendientes). El libro del almacén se usa de pie en el almacén, que es donde
   las tarjetas son lo correcto; el día que le toque tabla, la pieza ya está hecha.
2. **Dar de alta un artículo suelto** desde la pantalla (punto 4 de lo que falta en la API).
3. **Anular un movimiento del libro.** El servidor tiene su puerta (`POST /api/almacen/movimientos/{id}/anular`,
   con su motivo) y la pantalla **no la ofrece**: el ticket pedía la merma y el ajuste con su motivo, y
   anular un movimiento no estaba en la lista. Lo que sí se ve es **si cada movimiento cuenta o no y por
   qué**, que es lo que hace falta para entender una resta que no cuadra.
4. **Las cinco pantallas nuevas no se recorren en `scripts/comprobar_en_un_navegador.py`**, porque ese
   guion no es de este ticket y no se puede modificar. Están comprobadas con las capturas de arriba y por
   las pruebas que pulsan botones; **añadirlas a su lista `PANTALLAS` es el siguiente paso natural** y son
   cuatro líneas.

---

## 7. Lo que no se ha podido comprobar

1. **El enganche de una factura con las líneas descuadradas a propósito** (una línea del albarán que se
   facturó en dos): el camino está implementado (se mandan las líneas casadas que propone el servidor) y
   probado con el servidor de mentira, pero no se ha probado contra el servidor de verdad con un caso de
   esos.
2. **Un albarán real de un proveedor de verdad**: los datos de las pruebas y de las capturas son de
   ejemplo (una cooperativa inventada).
3. **La cola del móvil mandando un albarán de verdad sin cobertura**: se ha comprobado que lo apuntado se
   queda en el móvil con su clave de reenvío y que el servidor reconoce la clave (su propia prueba, de la
   mitad del servidor), pero **no se ha cortado la red de un móvil real**.
4. **La pantalla con 60 albaranes y 200 movimientos.** Con tres líneas y tres movimientos se ve bien; el
   desglose de cada envase enseña todos sus movimientos, y **no se ha medido qué pasa con un libro muy
   largo** (el servidor no pagina). Si algún día molesta, lo que hay que hacer es paginar en el servidor,
   no recortar en la pantalla.
5. **El aspecto en un móvil de verdad, con el sol de frente.** Eso exige la prueba con tres agricultores
   (apartado 5.18 del documento del MVP) y no se puede hacer desde aquí.
