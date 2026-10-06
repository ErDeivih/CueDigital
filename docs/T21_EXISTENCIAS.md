# T21 — Las existencias cuadran, y las vistas físicas dicen lo mismo

> **Qué es este documento.** El informe del ticket T21: qué se ha hecho, **qué se ha comprobado, con qué
> comando y qué número salió**, los **bloques literales** que el coordinador tiene que integrar en los
> ficheros compartidos (con su ancla exacta) y lo que **no** se ha podido comprobar.
>
> **Ficheros de este ticket** (y solo estos):
>
> | Fichero | Qué es |
> |---|---|
> | `backend/app/existencias.py` | La lógica pura del saldo físico y la relación producto ↔ artículo ↔ lote por identificador. |
> | `backend/tests/test_las_existencias_cuadran.py` | Las pruebas, contra la API de verdad. |
> | `docs/T21_EXISTENCIAS.md` | **Nuevo.** Este informe. |
>
> **No se ha tocado ningún otro fichero.** Lo que hace falta cambiar en los compartidos va aquí como
> bloque literal, con su ancla.
>
> **Punto de partida, dicho para que no se confunda con un trabajo desde cero:** al empezar, en el
> árbol **ya había** una versión de `app/existencias.py` y de `tests/test_las_existencias_cuadran.py`
> (una pasada anterior del mismo ticket), y **las dos tenían fallos que se ven al correrlas**: cinco
> pruebas en rojo, dos de ellas por errores de los propios escenarios (el alta de un trabajo con
> reenvío se daba por hecho con un `201` cuando devuelve `200`; y la corrección de un trabajo se
> mandaba sin `campana_id`, `tipo` ni `fecha`, que la puerta exige) y tres por lo que se esperaba
> (el cableado y los textos compartidos). Lo que hay aquí es esa base **corregida, medida y ampliada**
> con lo que faltaba: el filtro de los movimientos anulados, la lista de pendientes, la prueba de que
> las frases viven en `textos.py`, las pruebas en rojo hechas a propósito, y este informe. El detalle,
> en el apartado 4.6.


---

## 1. Qué es cada cosa, y cuál es la única fuente de verdad

En este programa hay **dos libros** y el encargo dice que no se suman. Para poder decirlo sin
confundirse, cada hecho tiene su nombre y su tabla:

| Hecho | Qué es | De dónde sale (tabla / columnas) | Quién lo mueve |
|---|---|---|---|
| **Compra** | Lo que se pagó. **No es mercancía dentro.** | `facturas` + `lineas_de_factura` (`cantidad`, `unidad`, `producto_id`, `fertilizante_id`) | `POST /api/facturas` |
| **Recepción** | La mercancía que **llega**: el albarán, con su lote. Es **lo único que mete existencias**. | `recepciones` + `lineas_de_recepcion` → `lotes` + `movimientos_de_existencias` (`tipo="entrada"`, `origen_tipo="recepcion"`) | `POST /api/almacen/recepciones` |
| **Consumo** | Lo que sale para gastarse, **con un apunte detrás**. | `movimientos_de_existencias` (`tipo="salida"`, `origen_tipo` ∈ `servicios.APUNTES_QUE_GASTAN`) | `POST /api/almacen/salidas` (y `POST /api/trabajos`, que la llama por dentro) |
| **Existencia física conocida** | El saldo: `entradas − salidas − mermas + ajustes`. | `movimientos_de_existencias` | Nadie: se calcula |

Y las dos cosas que **no son** existencias, aunque lo parezcan:

* **Una merma no es un consumo.** Se resta del saldo (está en la cuenta) pero **no es producto echado en
  la tierra**, y por eso `existencias.es_consumo` dice que no.
* **Una compra sin albarán no es una existencia.** Se declara aparte
  (`servicios.lo_comprado_que_no_ha_entrado`, `GET /api/almacen/existencias` → `comprado_sin_entrar`).

### La única fuente de verdad de «te queda» para un artículo

> **El libro de movimientos del almacén, por artículo.** Tabla `movimientos_de_existencias`, filtrada por
> `articulo_id` y contada por **`servicios.saldo_de_un_conjunto`** (la única resta del programa: los
> cuatro tipos, los movimientos anulados y las unidades que no se cuadran ya están resueltos ahí).
> La vista que hay que pintar la monta **`existencias.el_saldo_fisico_de_una_cesta`**.

El módulo nuevo **no reescribe esa resta**: `existencias.el_saldo_fisico` llama a
`servicios.saldo_de_un_conjunto` y devuelve su resultado tal cual. Hay una prueba que ata las dos
(`test_el_saldo_no_se_calcula_dos_veces_distinto`, con 40 − 6 − 1 − 0,5 = **32,5** por los dos caminos).

Lo que la cesta dice de ese producto (`compra_apuntada`, `consumo_apuntado`) **viaja al lado del saldo
físico y no se le suma ni se le resta**. Por eso la vista no tiene ningún «total»: un número que mezcle
lo comprado con lo que hay no significa nada.

---

## 2. Cómo se relacionan producto ↔ artículo ↔ lote, y qué pasa cuando no se puede

**Por identificador, nunca por el nombre.** Las columnas exactas:

| De | A | Columna |
|---|---|---|
| `Articulo` | `ProductoFitosanitario` | `Articulo.producto_id` → `productos_fitosanitarios.id` |
| `Articulo` | `Fertilizante` | `Articulo.fertilizante_id` → `fertilizantes.id` |
| `Lote` | `Articulo` | `Lote.articulo_id` → `articulos.id` |
| `MovimientoDeExistencias` | `Articulo` / `Lote` | `.articulo_id` / `.lote_id` |
| `MovimientoDeExistencias` | Al apunte que lo gastó | `origen_tipo` + `origen_id` (sin clave foránea: son cuatro tablas) |
| `LineaDeRecepcion` | La línea de la factura | `LineaDeRecepcion.linea_factura_id` |

Las funciones que lo aplican, todas en `app/existencias.py`:

* `la_relacion_por_identificador(articulos)` → `{"producto": {producto_id: articulo_id}, "fertilizante":
  {...}}`, sacado de esas columnas.
* `el_articulo_de_una_ficha(clase, ficha_id, relacion)` → el artículo, o `None`.
* `la_ficha_de_un_articulo(articulo)` → la vuelta (`("producto", 7)`).
* `los_lotes_de_un_articulo` / `los_movimientos_de_un_articulo` → por `articulo_id` (y `lote_id`).
* `los_apuntes_por_ficha(movimientos, articulos)` → los consumos del almacén agrupados por la ficha de
  la cesta a la que pertenecen, que es lo que permite cruzarlos con lo apuntado.

**Cuando no se puede establecer la equivalencia, queda pendiente y se dice. Nunca un cero:**

* Un producto de la cesta **sin artículo** sale en `pendientes` con `saldo_fisico: null`,
  `motivo_codigo: "A24_el_producto_no_tiene_articulo"` y su compra apuntada al lado, para poder
  revisarlo. **No se busca «el artículo que se llame parecido»**: está prohibido por el encargo y hay dos
  pruebas que lo fijan (`test_dos_fichas_con_el_mismo_nombre_no_se_unen` y
  `test_un_producto_sin_articulo_queda_pendiente_y_no_en_cero`).
* Un artículo **sin ficha de la cesta** y **sin haber entrado nunca** (cero movimientos) queda
  `pendiente` con el aviso `A26`: ese cero es una entrada que falta, no un saldo.
* Un producto **comprado y sin recibir** (hay número de compra y cero movimientos) queda `pendiente`
  con `A26` y, además, aparece en `compra_sin_entrar`. **Nunca se convierte en existencias.**
* Un saldo que **no se puede saber** (falta la cantidad de una entrada, falta la unidad, o las unidades
  no se pueden comparar) sale con `saldo_fisico: null` y el motivo que ya existe en el programa
  (`AL30`, `AL32`, `AL31`) o el que se propone aquí (`A27`).
* Si dos artículos reclaman la misma ficha, manda **el de identificador más bajo** (regla escrita, no
  parecido) y el otro sigue saliendo con su propio saldo: no se pierde ninguno.

### El mismo consumo por dos puertas (para no contarlo dos veces)

Un tratamiento apuntado en el cuaderno (`/api/tratamientos`) y la salida que ese mismo tratamiento
provoca en el almacén (`POST /api/almacen/salidas` con `origen_tipo="tratamiento"`,
`origen_id=<id del tratamiento>`) son **el mismo consumo visto por dos puertas**. Lo que hace el módulo:

* El saldo físico lo resta **una vez**, porque la salida es la que tiene el lote.
* `la_deduplicacion(apuntes, movimientos)` reconoce el par **por `(origen_tipo, origen_id)`** y devuelve
  `del_almacen`, `solo_en_la_cesta` y `el_mismo_consumo` con el aviso `A25`.
* Un apunte **sin** salida viva queda en `solo_en_la_cesta`: su consumo no ha movido ningún envase, y eso
  se dice en vez de dar por hecho que salió.
* **Dos salidas del mismo apunte no se tiran** (dos garrafas gastadas en el mismo tratamiento): se
  cuentan las dos y se dice cuántas son (`salidas_del_almacen`).
* Una salida anulada —o cuyo apunte está anulado— **no cruza nada**: si cruzara, el mismo consumo
  seguiría «contado» después de anularlo y el producto no volvería.

---

## 3. Los bloques literales para integrar

### 3.1. `backend/app/textos.py` — las cinco frases (obligatorio) — **YA INTEGRADO**

> **Estado (07/10/2026): el coordinador ya lo ha integrado** (commit «Las cinco frases del T21
> (existencias), integradas») y las dos pruebas que dependían de esto están **en verde**. El bloque se
> deja aquí tal cual: es el que lee `test_el_informe_lleva_las_frases_de_este_ticket` con
> `ast.literal_eval`, así que **no se toca a la ligera**.

Va junto a los otros `MENSAJES.update(` del fichero (los hay en las líneas 6321, 6607, 6697, 7117,
7405, 7597, 7741 y 7935). Las cinco frases son **literalmente** las de `existencias.MENSAJES`, y una
prueba lo comprueba leyendo este bloque:

Ancla: donde el fichero tiene su `MENSAJES.update(`. El bloque de debajo es el que hay que pegar dentro,
con sus cinco claves y su cierre. **Se lee con `ast.literal_eval`, así que las cinco frases de aquí abajo
son literalmente las del fichero** (lo comprueba una prueba); por eso no se tocan a la ligera.

```
MENSAJES.update({
    "A24_el_producto_no_tiene_articulo": (
        "Este producto no está enlazado con nada del almacén, así que de lo que te queda no se "
        "puede decir nada aquí. Enlázalo con un artículo del almacén y las dos pantallas dirán lo "
        "mismo."
    ),
    "A25_los_dos_libros_dicen_lo_mismo": (
        "Este consumo está apuntado en el cuaderno y en el almacén: es el mismo, y contarlo dos "
        "veces diría que has echado el doble. Cuenta una vez."
    ),
    "A26_el_libro_viejo_no_tiene_saldo_fisico": (
        "De este producto el cuaderno sabe lo que compraste y lo que llevas echado, pero en el "
        "almacén no hay ninguna entrada suya: lo comprado no está dentro hasta que llegue el "
        "albarán. Apunta la entrada cuando llegue y aquí saldrá lo que te queda de verdad."
    ),
    "A27_unidades_que_no_se_pueden_restar": (
        "Esto se lleva en {unidad} y lo que hay apuntado está en {otra}. No se pueden restar: un "
        "litro y un kilo no son lo mismo, y hace falta la densidad del producto."
    ),
    "A28_no_hay_articulo_del_que_sacar_el_saldo": (
        "Ni el cuaderno ni el almacén tienen una ficha de la que sacar lo que te queda. "
        "Apunta de qué producto se trata y volverá a salir la cuenta."
    ),
})
```

`A27` no lo referencia **ninguna línea** del módulo: es la frase que le corresponde a un saldo que no se
puede restar por mezclar unidades, y hoy ese caso lo explica `textos.MENSAJES["A21_unidades_distintas"]`
(que ya existe). Se propone para que el caso tenga sus propias palabras; si el coordinador prefiere no
añadirlo, basta con quitar `A27` de este bloque **y** de `existencias.MENSAJES`, y la prueba
`TestLosTextosDeEsteTicket::test_cada_hueco_se_puede_rellenar` dirá cuál falta. `A28` sí se usa, en el
texto que se enseña cuando hay una cantidad pero consta en qué se mide.

Y en `textos_visibles()` (línea 5435) hace falta que estas cinco entren en la revisión de jerga: el
diccionario ya se recorre, así que basta con que estén dentro de `MENSAJES`. Si el coordinador mantiene
una lista aparte de códigos nuevos que se revisan, añádanse los cinco.

### 3.2. `backend/app/servicios.py` — el saldo físico, relacionado con la cesta

**Dónde va:** dentro del bloque del almacén, **después** de `movimientos_del_almacen` (que termina en la
línea 1620) y **antes** de `lo_comprado_que_no_ha_entrado` (línea 1744). **Por qué ahí:** es la pieza que
la decisión escrita en la cabecera del bloque (líneas 1138–1166) dejaba pendiente: el saldo del libro se
calcula solo con movimientos, y ahora hay que **relacionarlo con la cesta por identificador**.

Ancla: `def lo_comprado_que_no_ha_entrado(`

```python
def el_saldo_fisico_de_una_cesta(db: Session, *, explotacion_id: int) -> dict:
    """El saldo **físico** de cada artículo, relacionado con la cesta **por identificador**.

    Es la pieza que hace que las dos pantallas que enseñan «te queda» digan lo mismo. Hasta hoy la cesta
    (`situacion_de_la_cesta`) contestaba con facturas menos tratamientos y el almacén con el libro de
    movimientos, y los dos números podían no parecerse. Aquí se juntan **sin sumarlos**: el número que se
    enseña es el físico, y lo que dice la cesta viaja al lado con su nombre.

    La lógica pura —qué es una entrada, qué es un consumo y cómo se relacionan producto, artículo y
    lote— vive en `app/existencias.py`, que se prueba sin base de datos ni servidor. Aquí solo se leen
    las filas y se le pasan.

    **Lo que no se hace:** unir dos cosas por el nombre, sumar los dos libros, ni convertir en cero un
    producto que no tenga artículo. Un dato sin correlación **queda pendiente** y se declara
    (`pendientes`, con su aviso `A24`).

    **Devuelve `por_articulo` con la clave `articulo_id`**, que es el identificador del artículo del
    almacén (`Articulo.id`). Es `None` cuando el producto de la cesta **no tiene artículo**: entonces el
    producto no está en `por_articulo` y sale en `pendientes`. La puerta de la cesta se queda con ese
    `articulo_id` y **no vuelve a relacionar nada**: relacionar dos veces es como un día las dos
    relaciones dicen cosas distintas.

    `apuntes` es la lista de consumos ya apuntados en el cuaderno (los tratamientos de la campaña, con
    `origen_tipo="tratamiento"`). Se pasan para poder decir «este consumo está apuntado y no ha salido de
    ningún envase», que es una de las cosas que hay que revisar. Sin ellos, el cruce se hace con los
    propios movimientos del almacén y se detecta igual el mismo consumo por las dos puertas.
    """
    articulos = list(
        db.scalars(
            select(models.Articulo).where(models.Articulo.explotacion_id == explotacion_id)
        )
    )
    movimientos = movimientos_del_almacen(
        db, explotacion_id=explotacion_id, solo_los_que_cuentan=True
    )
    apuntes = [
        {
            "origen_tipo": "tratamiento",
            "origen_id": tratamiento.id,
            "producto_id": tratamiento.producto_id,
            "cantidad": tratamiento.cantidad_total,
            "unidad": (tratamiento.unidad_cantidad_aplicada or "").strip()
            or legal.unidad_de_una_dosis(tratamiento.unidad_dosis),
        }
        for tratamiento in db.scalars(
            select(models.TratamientoFitosanitario).where(
                models.TratamientoFitosanitario.explotacion_id == explotacion_id,
                models.TratamientoFitosanitario.anulado.is_(False),
            )
        )
    ]
    # **La relación se calcula una vez, aquí**, y viaja en la respuesta: así la puerta de la cesta no
    # tiene que volver a relacionar por su cuenta (y no puede equivocarse haciéndolo de otra manera).
    relacion = existencias.la_relacion_por_identificador(
        [
            {
                "id": articulo.id,
                "producto_id": articulo.producto_id,
                "fertilizante_id": articulo.fertilizante_id,
            }
            for articulo in articulos
        ]
    )
    por_producto: dict[int, dict] = {}
    for fila in situacion_de_la_cesta(db, explotacion_id=explotacion_id, campana_id=None):
        por_producto[fila["producto_id"]] = {
            "producto_id": fila["producto_id"],
            # El identificador del artículo del almacén, que es lo que engancha las dos vistas. `None`
            # es «este producto no tiene artículo», y entonces sale en `pendientes` con su aviso.
            "articulo_id": existencias.el_articulo_de_una_ficha(
                "producto", fila["producto_id"], relacion
            ),
            "nombre_comercial": fila["nombre_comercial"],
            "numero_registro": fila["numero_registro"],
            "unidad_compra": fila["unidad_compra"],
            "comprado": fila["comprado"],
            "comprado_de_donde": fila["comprado_de_donde"],
            "gastado": fila["gastado"],
            "apuntes": fila["apuntes"],
        }
    vista = existencias.el_saldo_fisico_de_una_cesta(
        list(por_producto.values()),
        [
            {
                "id": articulo.id,
                "nombre": articulo.nombre,
                "categoria": articulo.categoria,
                "unidad": articulo.unidad,
                "producto_id": articulo.producto_id,
                "fertilizante_id": articulo.fertilizante_id,
            }
            for articulo in articulos
        ],
        movimientos,
        apuntes=apuntes,
        compra_sin_entrar=lo_comprado_que_no_ha_entrado(db, explotacion_id=explotacion_id),
    )
    return {
        "por_articulo": {fila.articulo_id: fila for fila in vista["articulos"]},
        "por_producto": por_producto,
        "pendientes": vista["pendientes"],
        "compra_sin_entrar": vista["compra_sin_entrar"],
        "avisos": vista["avisos"],
        "sin_saldo_conocido": vista["sin_saldo_conocido"],
        "descuadres": vista["descuadres"],
    }
```

Y el `import`, arriba del fichero (el orden alfabético de la línea 16 lo deja así):

```python
from . import borradores, catalogos, correcciones, existencias, geo, legal, models, textos
```

**Y el consumo de esa función, en la puerta de la cesta.** En `backend/app/routers/maestros.py`, en
`situacion_de_la_cesta` (línea 290), después de calcular `filas` (línea 316) y antes del bucle que quita
la ficha del producto (línea 323):

```python
    # **El saldo físico, que es el número que hay que enseñar.** Lo comprado y lo echado siguen ahí
    # (`comprado`, `gastado`), pero como lo que son: lo que dicen los papeles. El «te queda» de verdad
    # sale del libro de movimientos, relacionado por identificador. Si un producto no tiene artículo, su
    # `saldo_fisico` es `null` con su motivo (`A24`) y **no un cero**.
    saldos = servicios.el_saldo_fisico_de_una_cesta(db, explotacion_id=explotacion.id)
    for fila in filas:
        # La relación **ya viene hecha** desde `servicios`, por el identificador del artículo
        # (`saldos["por_producto"][producto_id]["articulo_id"]`). Aquí no se relaciona otra vez: si se
        # hiciera por el nombre, la pantalla y el almacén podrían decir cosas distintas del mismo
        # producto.
        suyo = saldos["por_articulo"].get(
            saldos["por_producto"].get(fila["producto_id"], {}).get("articulo_id")
        )
        fila["saldo_fisico"] = suyo.saldo_fisico if suyo else None
        fila["saldo_fisico_conocido"] = bool(suyo and suyo.se_puede_saber)
        fila["situacion"] = suyo.situacion if suyo else "pendiente"
        fila["motivo_fisico"] = (suyo.que_pasa or suyo.motivo) if suyo else textos.MENSAJES["A24_el_producto_no_tiene_articulo"]
        fila["lotes_del_articulo"] = suyo.lotes if suyo else []
        fila["el_mismo_consumo"] = suyo.el_mismo_consumo if suyo else []
```

**Ojo con el enganche, y esta es la decisión que conviene no deshacer:** `situacion_de_la_cesta`
devuelve `producto_id` y **no** `articulo_id`, así que la correspondencia la hace
`existencias.el_articulo_de_una_ficha("producto", producto_id, relación)` —la misma función que usa el
módulo— **dentro de `el_saldo_fisico_de_una_cesta`**, y la devuelve en `por_producto[producto_id]
["articulo_id"]`. La puerta de la cesta **no vuelve a relacionar nada**: lee ese `articulo_id` y con él
busca su renglón en `por_articulo`.

El motivo de hacerlo así y no al revés: relacionar dos veces es como un día las dos relaciones dicen
cosas distintas, y este ticket existe justo para que no pase eso. **Un `articulo_id` que nadie rellena
sería peor que no tenerlo**: la pantalla diría «este producto no tiene artículo» para todos.

Y para los productos **sin artículo**, que no aparecen en `saldos["por_articulo"]` (su `articulo_id` es
`None` y no hay renglón), la puerta tiene que servir el `pendiente` de `saldos["pendientes"]`
(buscándolo por `ficha_id == producto_id`), con `saldo_fisico: null` y `A24`. Así el dato antiguo queda
**pendiente y no en cero**.

> **Cuidado con la palabra `queda`: hay dos y significan cosas distintas.** Esto no es un detalle de
> nombres, es la trampa donde se pierde el encargo:
>
> * **`producto["queda"]`** (en `situacion_de_la_cesta`, línea 1129 de `servicios.py`) es la cuenta
>   vieja: **lo comprado por factura menos lo echado**. Se queda como está, porque es lo que dicen los
>   papeles y hay pantallas que lo enseñan así.
> * **`articulo["queda"]`** (en `servicios.existencias_del_almacen`, el que lee
>   `web/react/pantallas/libro_del_almacen.js` en las líneas 106 y 180) es el **saldo físico** de los
>   movimientos: el número de verdad.
>
> Por eso el campo nuevo de la cesta se llama **`saldo_fisico`** y no `queda`: si se llamara `queda`,
> habría dos `queda` con dos significados en la misma pantalla y el siguiente que lo lea no sabría cuál
> está mirando. **El nombre distinto es la mitad de la protección.**

### 3.3. `backend/app/routers/almacen_api.py` — la vista física en su puerta

En `ver_las_existencias` (línea 1504), dentro del diccionario que se devuelve (línea 1551), añadir:

```python
        # **La vista que tienen que consultar todas las pantallas que enseñan «te queda».** Se monta con
        # lo que ya se ha leído arriba y **no suma los dos libros**: cada artículo sale una vez con su
        # `saldo_fisico`, y la cesta (cuando la haya) va al lado.
        "el_saldo_fisico": existencias.el_saldo_fisico_de_una_cesta(
            [],
            [
                {
                    "id": fila["articulo_id"],
                    "nombre": fila["nombre"],
                    "categoria": fila["categoria"],
                    "unidad": fila["unidad"],
                    "producto_id": fila["producto_id"],
                    "fertilizante_id": fila["fertilizante_id"],
                }
                for fila in filas
            ],
            servicios.movimientos_del_almacen(
                db, explotacion_id=explotacion.id, solo_los_que_cuentan=True
            ),
            compra_sin_entrar=servicios.lo_comprado_que_no_ha_entrado(
                db, explotacion_id=explotacion.id
            ),
        ),
```

y el `import` de arriba (línea 49):

```python
from .. import existencias, models, servicios, textos
```

Nota: `existencias` **no** puede importar `servicios` en la cabecera de su módulo si `servicios` importa
`existencias` (sería un ciclo). Hoy `existencias` importa `servicios`, así que **el import va en
`servicios.py` y en los routers, no al revés**. Si el coordinador prefiere el sentido contrario, el
cambio es mover `from . import servicios` dentro de las dos funciones que lo usan
(`el_saldo_fisico` y `saldo_de…`), pero entonces hay que volver a correr las pruebas.

### 3.4. Lo que **no** hace falta tocar

* **`models.py`: nada.** El enlace por identificador ya existe (`Articulo.producto_id`,
  `Articulo.fertilizante_id`, `Lote.articulo_id`, `MovimientoDeExistencias.lote_id`, `origen_tipo` +
  `origen_id`). Este ticket no añade columnas ni tablas, y por eso no hay nada que «poner al día» al
  arrancar.
* **`schemas.py`: nada obligatorio.** La respuesta de la cesta es un `dict` sin `response_model`, así que
  los campos nuevos viajan solos. Si se quiere apretar el contrato, el esquema de salida tendría que
  llevar `saldo_fisico: float | None`, `saldo_fisico_conocido: bool`, `situacion: str`,
  `motivo_fisico: str` y `lotes_del_articulo: list[dict]`, y **`saldo_fisico` tiene que admitir `None`**:
  un `float` a secas convertiría «no lo sé» en un error de validación, que es peor.
* **`facturas_api.py`: nada.** El «comprado» sigue saliendo de las facturas, como manda la decisión de
  la línea 1138 de `servicios.py`. Lo que cambia es que la pantalla tiene al lado el número físico.

---

## 4. Lo comprobado, con el comando y el número

### 4.1. El comando

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests/test_las_existencias_cuadran.py -q --junit-xml=$env:TEMP\ex.xml
[xml]$x = Get-Content $env:TEMP\ex.xml -Raw; "$($x.testsuites.testsuite.tests) / $($x.testsuites.testsuite.failures)"
```

(No se ha corrido la suite entera a propósito: hay otros agentes en el árbol. Solo este fichero.)

### 4.2. Los números

**Última pasada, con el bloque 3.1 ya integrado por el coordinador:**

```
61 / 2      (tests / failures del XML)
```

| Momento | `tests` / `failures` | Qué fallaba |
|---|---|---|
| Punto de partida (lo que ya había en el árbol) | — | Cinco en rojo: dos por errores de los escenarios, dos esperando al cableado y una del texto compartido |
| Corregidos los escenarios y añadidas las pruebas del informe | **61 / 4** | 2 del cableado + 2 del informe (las dos por contradicciones de este documento, ya arregladas) |
| Con el bloque 3.1 integrado por el coordinador | **61 / 2** | las 2 del cableado: ver 4.4 |
| **Pasada final (estado entregado)** | **61 / 2** | las 2 que **esperan al cableado** |

Las **59 pruebas que pasan ya** cubren, entre otras cosas:

* La aritmética pura: 40 − 6 = **34**; el saldo negativo se devuelve tal cual; sin cantidad o sin unidad
  el saldo es `None` con su motivo y **no un cero**; los lotes suman el total (15 + 20 = 35).
* La relación por identificador: dos fichas con el mismo nombre **no se unen**; con dos artículos
  reclamando la misma ficha manda el de identificador más bajo.
* El mismo consumo por dos puertas: `del_almacen` = 1, `solo_en_la_cesta` = 0, `es_el_mismo_consumo` =
  `True`; con una salida de 1 L y un apunte de 2 L devuelve `False`; con la cantidad `None`, `None`
  (los tres finales: sí, no, no lo he podido comprobar).
* **Contra la API de verdad** (`TestClient`, con los fixtures `cliente`, `cuenta`, `crear_parcela`,
  `campana`): recepción de 40 L por `POST /api/almacen/recepciones`; el trabajo que gasta 6 L por
  `POST /api/trabajos` con `insumos`; y entonces **`/api/almacen/existencias` dice 34, el lote dice 34 y
  la vista física dice 34**, con `situacion == "cuadra"` y `salidas == 6`. Reenviar el albarán devuelve
  **200** y sigue habiendo **1** entrada de 40. La factura posterior se engancha al albarán y el almacén
  sigue con **40** (no 80), con la cesta diciendo `comprado == 40`. Anular el trabajo devuelve **40** a
  todas las vistas y deja el movimiento en el libro con `cuenta == False`. Corregir de 6 a 10 deja el
  saldo en **30** por todas las vistas y **una sola** salida viva; corregir a 2 lo deja en **38**.
  Anular el tratamiento devuelve el consumo **sin tocar el libro**.
* Los textos: las cinco frases existen, no llevan jerga y cada hueco se rellena.

### 4.3. Las pruebas en rojo, hechas a propósito

La regla de la casa es que **cada arreglo se pruebe en rojo**: romperlo a propósito, mirar el rojo con su
frase, y deshacer la rotura. Se midió con una sonda temporal (que aplicaba la rotura, corría la suite y
restauraba el fichero; la sonda se borró al terminar). Lo que salió:

1. **Quitar el módulo** (mover `app/existencias.py` a `app/existencias.py.bak`):
   `pytest tests/test_las_existencias_cuadran.py -q` → **1 error de colección**,
   `ImportError: cannot import name 'existencias' from 'app'`, y **ninguna prueba ejecutada**. Es la
   comprobación de que el fichero no aprueba «por vacío»: sin módulo, no hay verde. Fichero restaurado.
2. **P2 — que un consumo deje de cruzarse** (`es_consumo` devolvía `False` siempre, así que la cesta y el
   almacén contaban cada uno el suyo): **61 / 12**, con rojas
   `test_una_entrada_es_lo_que_mete_mercancia_y_una_salida_lo_que_la_gasta`,
   `test_el_apunte_con_su_salida_es_el_mismo_consumo`,
   `test_dos_salidas_del_mismo_apunte_son_dos_consumos_y_ninguna_se_tira`,
   `test_si_no_se_puede_comprobar_que_son_el_mismo_no_se_afirma`,
   `test_el_mismo_consumo_por_dos_puertas_no_se_resta_dos_veces`,
   `test_el_consumo_del_trabajo_se_cruza_con_el_apunte_y_no_se_cuenta_dos_veces` y
   `test_el_tratamiento_y_su_salida_bajan_el_almacen_una_sola_vez`. Arreglo repuesto.
3. **P3 — convertir en cero lo que no se sabe** (si `saldo_de_un_conjunto` decía `None`, la vista ponía
   `0.0`): **61 / 9**, con rojas `test_sin_la_cantidad_de_una_entrada_no_se_sabe_lo_que_queda_y_no_es_cero`,
   `test_los_litros_y_los_kilos_no_se_restan`,
   `test_sin_unidad_no_se_hace_la_cuenta_y_se_dice_que_falta_la_unidad` y
   `test_cuando_no_se_puede_saber_el_texto_es_el_motivo`. Arreglo repuesto.
4. **P4 — unir dos cosas por el nombre** (`la_relacion_por_identificador` enganchaba una ficha a un
   artículo sin `producto_id`, «porque se llama parecido»): **61 / 6**, y la roja que lo caza es
   `test_dos_fichas_con_el_mismo_nombre_no_se_unen`. Arreglo repuesto.

Cada rotura se deshizo **inmediatamente** y la sonda imprimía al final `el fichero vuelve a su sitio:
True`. Después de cada una, la pasada siguiente volvió al mismo número de fallos que antes (61 / 2).

### 4.4. Lo que **no** pasa todavía, y es lo esperado

**2 pruebas en rojo** de 61, y las dos son la aceptación del encargo esperando a que se cablee el saldo
físico en las dos pantallas que enseñan «te queda»:

| Prueba | Por qué está en rojo | Se pone verde cuando |
|---|---|---|
| `TestLoQueEsperaAlCableado::test_la_cesta_sirve_el_saldo_fisico_de_cada_producto` | `GET /api/productos/cesta/situacion` todavía no devuelve `saldo_fisico` por producto (comprobado: `servicios` no importa `existencias`) | Se integre el bloque 3.2 |
| `TestLoQueEsperaAlCableado::test_la_vista_de_las_existencias_dice_el_mismo_saldo` | Lo mismo, medido contra el número del almacén (que sí dice 34) | Se integren 3.2 y 3.3 |

Están escritas enteras y con mensaje propio (dicen qué campo falta y dónde está el bloque) en vez de
saltarse con un `skip`: una prueba saltada se olvida, y una prueba roja con la frase «falta el cableado»
es lo que hace que el ticket no se dé por cerrado antes de tiempo.

Y las dos que **ya están en verde** por el bloque 3.1: `test_el_informe_lleva_las_frases_de_este_ticket`
(lee las cinco frases del informe con `ast.literal_eval` y las compara con `existencias.MENSAJES`) y
`test_las_frases_estan_en_el_sitio_donde_vive_todo_el_texto` (exige que las cinco estén en
`textos.MENSAJES` y digan lo mismo).

### 4.5. Lo que **no** se ha podido comprobar

* **Que la pantalla (el navegador) enseñe el número.** No se ha tocado el frontend: es del coordinador y
  las pantallas viven en `backend/web/react/`. Lo comprobado llega hasta la API.
* **El número que devolverá el endpoint de la cesta.** Depende del cableado (3.2), que no es de este
  ticket. Lo que sí está medido es que la lógica, alimentada con **los mismos datos que hoy sirven las
  puertas de verdad**, da 34.
* **La suite entera.** A propósito: hay otros agentes en el árbol. No se ha corrido `pytest` completo ni
  `tests_js`.
* **La prueba de humo** (`scripts/humo.py`) contra un servidor de verdad: no se ha levantado servidor.
* **La base del agricultor** (`backend/cuedigital.db`): no se ha abierto, ni leído, ni copiado. Todo lo
  medido va contra la base temporal de `tests/conftest.py`.
* **PostgreSQL.** Las pruebas han corrido sobre SQLite. El módulo es lógica pura y no escribe SQL, así
  que no debería haber diferencia, pero **no está medido**.

### 4.6. El punto de partida, y lo que se le ha corregido

Al empezar, `app/existencias.py` y `tests/test_las_existencias_cuadran.py` **ya existían** en el árbol
(una pasada anterior del mismo ticket). Se midió qué fallaba y se corrigió:

| Qué fallaba | Qué se ha hecho |
|---|---|
| `TestElCasoDelEncargo::test_reenviar_el_trabajo_no_duplica_el_consumo`: el alta se daba por buena con `assert respuesta.status_code == 201`, y el reenvío devuelve **200** | Se separó `_pedir_trabajo` (devuelve la respuesta) de `_un_trabajo` (exige el 201), y el reenvío se comprueba con su **200** y su `ya_estaba: True` |
| Las dos pruebas de corrección mandaban `PUT /api/trabajos/{id}` solo con `insumos`, y la puerta pide el cuerpo entero (`TrabajoEntrada`): **422** y `{"loc":["body","campana_id"],"msg":"Field required"}` | Nuevo `_corregir_trabajo`, que manda `campana_id`, `tipo`, `fecha`, `parcela_id` y `superficie_ha` además de los insumos. Ahora corregir de 6 a 10 da **30** y corregir a 2 da **38** |
| La vista física se alimentaba con **todos** los movimientos, anulados incluidos: después de anular, el saldo se quedaba en **34** en vez de volver a **40** | Nuevo `_el_libro_que_cuenta` (`solo_los_que_cuentan=True`), que es lo que hay que pasarle al saldo |
| `los_apuntes_por_ficha` metía también las salidas anuladas, así que el mismo consumo seguía cruzándose después de anularlo | Se añadió `servicio_contado(movimiento)` a ese filtro, y lo mismo a `la_deduplicacion` |
| `el_saldo_fisico_de_una_cesta` marcaba como «usadas» todas las fichas vistas, **aunque no tuvieran artículo**, así que el producto sin correspondencia no salía en `pendientes` | Se separó `productos_con_articulo` de las fichas vistas: ahora el producto sin artículo **queda pendiente** (`A24`), que es lo que pide el encargo |
| La prueba del texto sin unidad pedía un número («34,00») cuando el caso real es que **sin unidad no se puede hacer la cuenta** | Se reescribió: exige `saldo_fisico is None`, `motivo_codigo == "AL32_falta_la_unidad"` y que el texto hable de «en qué se miden» |
| No había ninguna prueba de que las cinco frases vivan en `textos.py` | `test_las_frases_estan_en_el_sitio_donde_vive_todo_el_texto`, en rojo hasta que se integre el bloque 3.1 |
| No había informe | Este documento, con los bloques literales y sus anclas, atado al código por `TestElInformeDiceLoMismoQueElCodigo` |
| El bloque 3.2 se contradecía: la función devolvía `producto_id` y la puerta buscaba `_articulo_id`, que **no lo rellenaba nadie** (lo cazó el coordinador) | Decidido y escrito: **`el_saldo_fisico_de_una_cesta` devuelve `articulo_id` por producto** (lo calcula con `existencias.el_articulo_de_una_ficha`) y la puerta de la cesta lee ese `articulo_id`; el `_articulo_id` desaparece del informe |
| El bloque 3.1 del informe llevaba el texto `MENSAJES.update({` **también en la prosa**, así que la extracción se comía la nota y `ast.literal_eval` reventaba | La prosa ya no lleva esa cadena: solo está en el bloque de código, que es lo que se lee |
| La prueba de los bloques pedía `from . import existencias`, que no es la línea que hay que pegar | Ahora pide la línea literal del `import` de `servicios.py` y las piezas de los tres bloques (`MENSAJES.update({`, `def el_saldo_fisico_de_una_cesta(`, `saldo_fisico`, `situacion`, `el_saldo_fisico`, `articulo_id`) |

Y una cosa que **no** se ha tocado del punto de partida, porque estaba bien: el reparto en once clases
(qué es cada cosa, la relación por identificador, el saldo, el mismo consumo, la vista, la propuesta de
artículo, los textos, el caso del encargo, las dos puertas y el cableado) y las decisiones que ya estaban
escritas en la cabecera del módulo.

---

## 5. Lo que se ha decidido, y conviene no deshacer

1. **El saldo físico es el del almacén y no se recalcula en ningún otro sitio.** `existencias.el_saldo_fisico`
   llama a `servicios.saldo_de_un_conjunto`. Si alguien escribe una segunda resta «más clara», un día las
   dos dirán cosas distintas y nadie sabrá cuál mirar. Motivo: es la única función que ya sabe de los
   cuatro tipos de movimiento, de las anulaciones y de las unidades que no se cuadran.
2. **Lo que dice la cesta no se suma ni se resta al saldo: se enseña al lado.** Nada de «si la cesta dice
   34 y el almacén 40, pongo 34». El número que se enseña es el físico, y el otro viaja con su nombre
   (`compra_apuntada`, `consumo_apuntado`) para poder revisarlo.
3. **La relación es por identificador y el nombre no une nada.** Es literal del encargo y tiene dos
   pruebas. Unir por parecido es como se mete el producto de un envase en la cuenta de otro.
4. **Un dato sin correspondencia queda `pendiente` con su aviso, nunca en cero.** Un cero es una
   afirmación («no queda producto») y el encargo prohíbe hacerla sin saberlo.
5. **`None` para «no se puede saber», con su motivo.** Si `saldo_de_un_conjunto` dice `None`, la vista
   dice `None` y su motivo. Nunca `0.0`.
6. **El mismo consumo se reconoce por `(origen_tipo, origen_id)` y solo entre los movimientos que
   cuentan.** No se compara por producto ni por cantidad: dos tratamientos distintos del mismo producto
   con la misma cantidad son dos consumos de verdad. Y una salida anulada no cruza nada, para que anular
   devuelva el producto.
7. **Dos salidas del mismo apunte no se tiran.** El almacén permite gastar dos garrafas en el mismo
   trabajo, y las dos son consumos. La deduplicación solo evita volver a restar el apunte de la cesta, no
   borra movimientos.
8. **Los tres finales también aquí: sí, no, y no lo he podido comprobar.** Cuando faltan las cantidades
   para afirmar que dos apuntes son el mismo consumo, se devuelve `None` y no se afirma.
9. **La deduplicación no resta: solo decide qué apunte no hay que volver a restar, y lo dice.** Si
   restara, el litro contaría dos veces por el otro lado, que es el fallo que el encargo prohíbe.
10. **El artículo sin ficha de la cesta no es un error.** Una semilla o el aceite del taller no son
    productos de la cesta y tienen su saldo. Lo único que se dice de ellos, si nunca ha entrado nada, es
    que falta la entrada.
11. **Un documento de más de 500 caracteres no cabe en `movimientos_de_existencias.motivo`.** El módulo
    devuelve las frases y no las escribe en `motivo`; quien las persista tiene que cortarlas (el
    programa ya lo hace así: `almacen_api.apuntar_un_movimiento` corta a 500). No se ha tocado nada de
    eso.
12. **Las frases viven en `textos.py`.** El módulo las tiene escritas para poder probarlas y para que el
    bloque de este informe se lea con `ast.literal_eval`, pero **el texto que ve el agricultor sigue
    siendo el de `textos.py`**, y hay dos pruebas que atan las dos copias.

---

## 6. Resumen de una línea

`app/existencias.py` da la pieza que faltaba —qué es una entrada, qué es un consumo, y cómo se relacionan
producto, artículo y lote **por identificador**— y la vista que hace que **todas las pantallas que
enseñan «te queda» consulten el mismo saldo físico**; de las **61 pruebas** del fichero, **59 pasan ya**
(recepción 40 → consumo 6 → **34** en las tres vistas, el reenvío no duplica, la corrección y la anulación
actualizan todo, y la factura posterior no añade entrada) y **2 quedan en rojo** con su frase hasta que se
cablee el saldo físico en las dos pantallas (bloques 3.2 y 3.3). El bloque 3.1 (las cinco frases) ya está
integrado y sus dos pruebas están en verde.
