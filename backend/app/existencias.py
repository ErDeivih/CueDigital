"""Las existencias físicas: **una sola verdad para «te queda»** (T21).

## El problema que resuelve este fichero

En este programa hay dos libros y **hasta hoy no se hablaban**:

  · **La cesta** (`servicios.situacion_de_la_cesta`, `GET /api/productos/cesta/situacion`): «compraste
    tanto, llevas echado tanto, te queda tanto». Lo comprado sale de las **líneas de las facturas**
    (`lineas_de_factura`) y lo gastado de los **tratamientos** (`TratamientoFitosanitario`). Es una
    cuenta, no un depósito: no se guarda nada.
  · **El almacén** (T09, `servicios.existencias_del_almacen`, `GET /api/almacen/existencias`):
    existencias **físicas por envases y lotes**, con la recepción del albarán
    (`recepcion` → `lote` → `movimiento de entrada`) y los consumos que salen (`salida`).

Un trabajo que gasta de un envase mueve el libro del almacén y la cesta no se entera; y al revés, la
cesta resta un tratamiento que en el almacén sigue contando. Resultado: dos pantallas del mismo
programa dicen dos cosas distintas del **mismo artículo**, que es el fallo que este ticket prohíbe.

## La decisión, escrita para que nadie la deshaga sin leerla

1. **Comprar, recibir, consumir y tener son cuatro hechos distintos** y aquí se llaman por su nombre:
   la **compra** es una factura; la **recepción** es un albarán con su lote, y es lo único que mete
   mercancía; el **consumo** es lo que sale con un apunte detrás (un tratamiento, un abono, una
   siembra, una labor); y la **existencia física conocida** es el saldo de los movimientos.
   Ver `ClaseDeHecho`.

2. **La única fuente de verdad de «te queda» para un artículo es el libro de movimientos.** Se calcula
   con `entradas − salidas − mermas + ajustes` sobre `movimientos_de_existencias`, artículo por
   artículo, y **lo sabe calcular el programa de una sola forma**: `servicios.saldo_de_un_conjunto`.
   Este módulo **no hace esa cuenta otra vez**: ordena, relaciona y audita, y para el número manda a
   esa función. Dos restas distintas para el mismo saldo es como se empieza a mentir sin querer.

3. **Producto, artículo y lote se relacionan por identificador, nunca por el nombre.**
   `Articulo.producto_id` → `productos_fitosanitarios.id`, `Articulo.fertilizante_id` →
   `fertilizantes.id`, y `Lote.articulo_id` / `MovimientoDeExistencias.lote_id` → `lotes.id`. Dos
   fichas con el mismo nombre (`Glifosato 36 SL` escrito distinto en dos sitios) **no se unen**: unir
   por parecido es exactamente como se cuela el producto de otro envase. Ver `la_relacion_por_identificador`.

4. **Los dos libros no se suman.** Lo que está comprado por factura y todavía no ha entrado **no es
   existencia**: es una compra pendiente de recibir (`servicios.lo_comprado_que_no_ha_entrado`), y
   sumarla sería contar cada litro dos veces. Aquí se devuelve en su propio apartado, con la palabra
   «pendiente».

5. **Un dato antiguo sin correspondencia queda pendiente, no se convierte en cero.** Un producto de la
   cesta sin artículo en el almacén sale con `saldo_fisico = None` y su aviso (`A24`), y un producto
   del que no se puede hacer la cuenta sale con `None` y el motivo de siempre (`A20`, `A21`). **Un
   cero diría que no queda producto**, y eso es una afirmación que nadie ha hecho.

6. **El mismo consumo no se cuenta dos veces.** Un tratamiento apuntado a mano (`productos_fitosanitarios`
   → cesta) y la salida que ese mismo tratamiento provoca en el almacén (`MovimientoDeExistencias` con
   `origen_tipo="tratamiento"`) son **el mismo consumo visto por dos puertas**. El saldo físico lo
   resta **una vez**, porque la salida es la que tiene el lote; y lo que sí se hace es **decirlo**
   (`la_deduplicacion`, `A25`), porque quien suma las dos columnas a mano contaría dos veces.

## Qué NO hace este fichero

No toca la base, no importa `models` y no escribe ninguna frase de pantalla: **las frases viven en
`app/textos.py`** y aquí solo van sus códigos (`MENSAJES`, en `CODIGOS_DE_TEXTO`). Tampoco cambia
ninguna cuenta que ya exista: sustituir un número por otro sin decirlo es justo lo contrario de lo que
se pide. Lo que hace es dar **la pieza que faltaba** para que las dos vistas puedan consultar el mismo
saldo, y decir en voz alta cuándo no se puede.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import legal, servicios, textos

# --------------------------------------------------------------------------
# Los cuatro hechos, que no son lo mismo
# --------------------------------------------------------------------------


class ClaseDeHecho:
    """Cómo se llama cada cosa, para poder decirlo en la pantalla sin confundirlas.

    Existe para que en el código —y en la respuesta de la API— no se use «comprado» para hablar de algo
    que se ha recibido: **comprar y recibir son hechos distintos**, y el agricultor que ve «comprado
    40 L» cuando el camión no ha llegado todavía está leyendo una mentira.
    """

    COMPRA = "compra"  # una factura (lineas_de_factura): lo que se pagó
    RECEPCION = "recepcion"  # un albarán con su lote (recepciones): lo que entró de verdad
    CONSUMO = "consumo"  # lo que salió con un apunte detrás (movimientos tipo salida)
    EXISTENCIA = "existencia"  # el saldo de los movimientos: lo que hay, si se puede saber


# Los cuatro tipos de movimiento, con su signo en la cuenta. Es la misma verdad que
# `servicios.saldo_de_un_conjunto` (que es quien hace la resta); aquí está para poder decir **cómo
# entra cada hecho en el saldo** sin volver a escribir la aritmética.
SIGNO_DE_CADA_TIPO = {
    "entrada": 1,
    "salida": -1,
    "merma": -1,
    "ajuste": 1,
}

# Un consumo sale del almacén con un apunte del cuaderno detrás. La lista buena es
# `servicios.APUNTES_QUE_GASTAN`; esta copia existe solo para poder decir en la respuesta **qué clase
# de apunte** sostiene cada salida, y una prueba comprueba que dice lo mismo que la del programa.
APUNTES_QUE_GASTAN = servicios.APUNTES_QUE_GASTAN

# Dos cantidades de la misma cuenta no cuadran por debajo de esto. Es la misma tolerancia que usa el
# almacén para no avisar por un redondeo (`almacen_api.sacar_de_un_lote`).
TOLERANCIA = 1e-9

# La categoría del almacén que corresponde a cada ficha de la cesta. Se usa **solo cuando hay que
# crear el artículo que falta** (para no dejarlo como «otras cosas»): lo que de verdad decide si dos
# cosas son la misma no es esto, es el identificador.
CATEGORIA_DE_UNA_FICHA = {"producto": "fitosanitario", "fertilizante": "abono"}


# --------------------------------------------------------------------------
# Los textos: los códigos y las frases
#
# **Las frases viven en `app/textos.py` y esta es la propuesta para el coordinador** (el bloque
# literal está en `docs/T21_EXISTENCIAS.md`). Se quedan escritas aquí para que un test pueda comprobar
# que existen, que no llevan jerga y que cada hueco se rellena: un mensaje que se pide y sale en blanco
# es lo primero que hace desconfiar de un programa.
# --------------------------------------------------------------------------

MENSAJES: dict[str, str] = {
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
}
# La lista de códigos, para que una prueba pueda exigir que todos tengan su frase y que ninguno se
# quede fuera de la revisión de jerga del proyecto.
CODIGOS_DE_TEXTO: tuple[str, ...] = tuple(MENSAJES)


def mensaje(codigo: str, **huecos) -> str:
    """La frase de ese código, con sus huecos rellenos.

    Se rellena aquí y no en la pantalla por el mismo motivo que en todo el programa: un texto que se
    escribe en dos sitios acaba diciendo dos cosas. Y si un hueco no se rellena, revienta **en la
    prueba**, no delante del agricultor con un `{unidad}` en medio de la frase.
    """
    return MENSAJES[codigo].format(**huecos)


# --------------------------------------------------------------------------
# La relación producto ↔ artículo ↔ lote, que va **por identificador**
# --------------------------------------------------------------------------


def la_relacion_por_identificador(articulos: list[dict]) -> dict[str, dict[int, int]]:
    """Qué artículo del almacén es cada ficha de la cesta, por identificador y por nada más.

    Devuelve dos mapas —`{"producto": {producto_id: articulo_id}, "fertilizante": {...}}`— sacados del
    enganche que ya existe en la tabla (`Articulo.producto_id` y `Articulo.fertilizante_id`).

    **Lo que no se hace, y es la mitad del encargo: no se une por el nombre.** Si un producto de la
    cesta no tiene artículo, no se busca «el artículo que se llama parecido»: se queda **sin
    equivalencia**, que es un estado que se puede declarar. Unir dos cosas por su nombre es como se
    mete el producto de un envase en la cuenta de otro, y eso no se puede deshacer después.

    Cuando **dos artículos reclaman la misma ficha** (pasa: el mismo producto dado de alta dos veces en
    el almacén), se devuelve el de identificador más bajo y **no se elige por parecido**: es una regla
    escrita, para que el resultado sea el mismo hoy y mañana. La otra ficha sigue en el almacén con su
    saldo, y en la vista aparece como un artículo sin producto de la cesta.
    """
    relacion: dict[str, dict[int, int]] = {"producto": {}, "fertilizante": {}}
    for articulo in sorted(articulos, key=lambda fila: fila["id"]):
        for clase, columna in (("producto", "producto_id"), ("fertilizante", "fertilizante_id")):
            ficha_id = articulo.get(columna)
            if ficha_id is None or ficha_id in relacion[clase]:
                continue
            relacion[clase][ficha_id] = articulo["id"]
    return relacion


def el_articulo_de_una_ficha(
    clase: str, ficha_id: int | None, relacion: dict[str, dict[int, int]]
) -> int | None:
    """El artículo de esa ficha de la cesta, o `None` si no hay ninguno que le corresponda.

    `None` **no** es «no queda nada»: es «de este producto no hay nada en el almacén con lo que
    relacionarlo», y quien lo pinte tiene que decirlo. Ver `A24`.
    """
    if ficha_id is None:
        return None
    return relacion.get(clase, {}).get(ficha_id)


def la_ficha_de_un_articulo(articulo: dict) -> tuple[str, int] | None:
    """La ficha de la cesta de la que sale un artículo: `("producto", 7)` o `("fertilizante", 3)`.

    Es la vuelta de `la_relacion_por_identificador`. Si un artículo tiene las dos —no debería, pero la
    tabla no lo impide— manda el producto, que es la ficha de la que sale lo que se echa.
    """
    if articulo.get("producto_id") is not None:
        return "producto", articulo["producto_id"]
    if articulo.get("fertilizante_id") is not None:
        return "fertilizante", articulo["fertilizante_id"]
    return None


def los_lotes_de_un_articulo(lotes: list[dict], *, articulo_id: int) -> list[dict]:
    """Los envases de ese artículo. **Por `Lote.articulo_id`, no por el nombre del artículo.**

    Se devuelven ordenados por caducidad —y los que no tienen caducidad apuntada al final— por el mismo
    motivo que en el almacén: lo que se estropea antes es lo que hay que gastar antes, y un lote del
    que no se sabe cuándo caduca no es «el que más dura».
    """
    suyos = [lote for lote in lotes if lote.get("articulo_id") == articulo_id]

    def el_orden(lote: dict):
        caduca = lote.get("fecha_caducidad")
        return (caduca is None, caduca or "", lote.get("id") or 0)

    return sorted(suyos, key=el_orden)


def los_movimientos_de_un_articulo(
    movimientos: list[dict], *, articulo_id: int, lote_id: int | None = None
) -> list[dict]:
    """Los movimientos de ese artículo (y de ese envase, si se dice cuál), por identificador."""
    devueltos = [fila for fila in movimientos if fila.get("articulo_id") == articulo_id]
    if lote_id is not None:
        devueltos = [fila for fila in devueltos if fila.get("lote_id") == lote_id]
    return devueltos


# --------------------------------------------------------------------------
# Qué es una entrada y qué es un consumo
# --------------------------------------------------------------------------


def es_entrada(movimiento: dict) -> bool:
    """Lo que mete mercancía en el almacén. **La mercancía entra con el albarán, no con la factura.**

    Una entrada con `origen_tipo="factura"` también cuenta como entrada —es una compra sin albarán en
    la mano, que existe y hay que poder apuntar—, pero lo que la hace ser una entrada es **haber
    llegado**, no el papel que la sostiene. Por eso el tipo manda sobre el origen.
    """
    return servicio_contado(movimiento) and movimiento.get("tipo") == "entrada"


def es_consumo(movimiento: dict) -> bool:
    """Lo que sale para gastarse: un tratamiento, un abono, una siembra o una labor.

    **Una merma no es un consumo** y por eso no entra aquí: lo que se rompe o se derrama no se ha
    echado en la tierra, y contarlo como gastado diría que el producto se aplicó. Se resta igual del
    saldo (está en `SIGNO_DE_CADA_TIPO`), pero no es «lo que llevas echado».
    """
    return servicio_contado(movimiento) and movimiento.get("tipo") == "salida"


def es_un_consumo_con_apunte(movimiento: dict) -> bool:
    """Un consumo que sale de un apunte del cuaderno, que es lo que permite comprobarlo y revertirlo.

    Una salida con `origen_tipo="manual"` —la tabla lo permite— no tiene apunte detrás y por eso no
    puede cruzarse con la cesta: se cuenta, pero no se puede decir de qué trabajo salió.
    """
    return es_consumo(movimiento) and movimiento.get("origen_id") is not None


def servicio_contado(movimiento: dict) -> bool:
    """Si este movimiento entra en la cuenta **hoy**, según lo que ya decidió el almacén.

    Es la regla de que nada se borra: un movimiento anulado, o cuyo apunte está anulado, sigue en el
    libro pero no cuenta (`servicios.un_movimiento_cuenta`). Aquí no se decide otra vez: se lee el
    `cuenta` que ya viene calculado en la fila. Si no viniera, **se da por contado**, que es lo que
    hace la API que no conoce anulaciones; nunca se inventa un «no cuenta», que escondería mercancía.
    """
    return bool(movimiento.get("cuenta", True))


def la_clave_de_un_consumo(movimiento: dict) -> tuple[str, int] | None:
    """Con qué se reconoce que dos apuntes son **el mismo consumo**: su clase y su identificador.

    Es `(origen_tipo, origen_id)` —«el tratamiento 12», «la labor 7»— y nada más. **No se compara por
    producto ni por cantidad**: dos tratamientos distintos del mismo producto con la misma cantidad son
    dos consumos de verdad, y unirlos escondería producto echado.
    """
    if not es_un_consumo_con_apunte(movimiento):
        return None
    return str(movimiento.get("origen_tipo")), int(movimiento["origen_id"])


def la_deduplicacion(apuntes: list[dict], movimientos: list[dict]) -> dict:
    """Separa los consumos que ya están contados en el almacén de los que solo están en la cesta.

    Devuelve `{"del_almacen": [...], "solo_en_la_cesta": [...], "el_mismo_consumo": [...]}`:

      · **`del_almacen`** — los apuntes que **ya tienen su salida** en el libro de movimientos. No hay
        que restarlos otra vez: la salida es la que tiene el lote, y la resta del saldo físico ya la
        hizo el almacén. Son los que se cuentan **una vez**.
      · **`solo_en_la_cesta`** — los que no tienen ninguna salida viva. Su consumo no ha movido ningún
        envase, así que el saldo físico **no lo conoce**, y eso hay que decirlo (`A26`): un almacén sin
        entradas de ese producto no está «a cero», está sin datos.
      · **`el_mismo_consumo`** — el detalle de los primeros, con lo que dice cada libro, para poder
        enseñar por qué no se suman.

    **Lo que esto no hace es restar.** El saldo físico ya viene restado por el almacén; aquí solo se
    decide qué apunte **no** hay que volver a restar, y se dice. Si esto restara, el mismo litro
    contaría dos veces por el otro lado, que es el fallo que el encargo prohíbe.
    """
    ya_contados: dict[tuple[str, int], list[dict]] = {}
    for movimiento in movimientos:
        # Solo los que cuentan hoy: un consumo anulado no justifica nada.
        if not servicio_contado(movimiento):
            continue
        clave = la_clave_de_un_consumo(movimiento)
        if clave is not None:
            ya_contados.setdefault(clave, []).append(movimiento)

    del_almacen: list[dict] = []
    solo_en_la_cesta: list[dict] = []
    el_mismo: list[dict] = []
    for apunte in apuntes:
        clave = _la_clave_del_apunte(apunte)
        if clave is None:
            # Un apunte del que no se sabe de dónde sale no se puede cruzar con nada, así que se cuenta
            # en la cesta y se dice que el almacén no lo conoce. No se tira: se declara.
            solo_en_la_cesta.append(apunte)
            continue
        salidas = ya_contados.get(clave)
        if salidas:
            del_almacen.append(apunte)
            el_mismo.append(
                {
                    "origen_tipo": clave[0],
                    "origen_id": clave[1],
                    # Cuántos movimientos del almacén salen de ese mismo apunte. **Puede ser más de
                    # uno** —dos garrafas gastadas en el mismo tratamiento— y por eso se cuenta en
                    # lugar de dar por hecho que son uno: cada garrafa es un consumo distinto del
                    # mismo trabajo, y el saldo ya las tiene todas.
                    "salidas_del_almacen": len(salidas),
                    "cantidad_en_el_almacen": sum(
                        fila.get("cantidad") or 0.0 for fila in salidas
                    ),
                    "unidad_en_el_almacen": next(
                        ((fila.get("unidad") or "").strip() for fila in salidas if fila.get("unidad")),
                        "",
                    ),
                    "cantidad_en_la_cesta": apunte.get("cantidad"),
                    # El aviso solo se pone cuando quien suma las dos columnas a mano **contaría dos
                    # veces de verdad**, que es cuando las dos cantidades coinciden: entonces son el
                    # mismo consumo. Con una salida de 1 L y un apunte de 2 L no se puede afirmar que
                    # sean el mismo, y no se afirma (`None`).
                    "es_el_mismo_consumo": _son_la_misma_cantidad(
                        apunte.get("cantidad"),
                        sum(fila.get("cantidad") or 0.0 for fila in salidas),
                    ),
                    "mensaje": MENSAJES["A25_los_dos_libros_dicen_lo_mismo"],
                }
            )
        else:
            solo_en_la_cesta.append(apunte)
    return {
        "del_almacen": del_almacen,
        "solo_en_la_cesta": solo_en_la_cesta,
        "el_mismo_consumo": el_mismo,
    }


def _son_la_misma_cantidad(una, otra) -> bool | None:
    """¿Estas dos cantidades son la misma? `None` cuando falta alguna y no se puede afirmar.

    Tres finales y no dos, como en la comprobación de una firma: sí, no, y **no lo he podido
    comprobar**. Decir «no» cuando falta un dato sería acusar al agricultor de haber apuntado dos
    cosas distintas, y no lo sabemos.
    """
    if una is None or otra is None:
        return None
    return abs(float(una) - float(otra)) <= TOLERANCIA


# --------------------------------------------------------------------------
# La cuenta del saldo físico: **la manda el almacén**
# --------------------------------------------------------------------------


def el_saldo_fisico(
    movimientos: list[dict], *, articulo: dict | None = None, relacion: dict | None = None
) -> dict:
    """Lo que queda de un artículo, contado **solo con los movimientos del almacén**.

    No hay una segunda resta aquí: se llama a `servicios.saldo_de_un_conjunto`, que es la única que
    sabe hacerla (y la que ya está probada con los cuatro tipos de movimiento, con un lote sin
    cantidad y con dos unidades que no se pueden comparar). Escribir la aritmética otra vez sería la
    forma de que un día las dos dijeran cosas distintas y nadie supiera cuál mirar.

    Lo que **sí** añade esta función es la identidad del artículo —sus nombres, su unidad y los lotes
    de los que sale— y la respuesta a «¿se puede saber?». Y lo que devuelve cuando no se puede saber es
    `saldo: None` con su motivo, **nunca un cero**: un cero diría que no queda producto, y el agricultor
    iría a comprar por nada.
    """
    articulo = articulo or {}
    unidad_del_articulo = (articulo.get("unidad") or "").strip() or None
    cuenta = servicios.saldo_de_un_conjunto(list(movimientos), unidad_del_articulo)
    return {
        "articulo_id": articulo.get("id"),
        "nombre": articulo.get("nombre"),
        "categoria": articulo.get("categoria") or "otros",
        "unidad": cuenta.get("unidad") or unidad_del_articulo,
        # **Lo que entró de verdad** (el albarán), que no es lo que se compró.
        "entradas": cuenta.get("entradas"),
        "salidas": cuenta.get("salidas"),
        "mermas": cuenta.get("mermas"),
        "ajustes": cuenta.get("ajustes"),
        "movimientos": cuenta.get("movimientos"),
        "sin_movimientos": cuenta.get("sin_movimientos"),
        "movimientos_sin_cantidad": cuenta.get("movimientos_sin_cantidad"),
        "movimientos_sin_unidad": cuenta.get("movimientos_sin_unidad"),
        "unidades_que_no_cuadran": cuenta.get("unidades_que_no_cuadran"),
        "saldo": cuenta.get("saldo"),
        "se_puede_saber": cuenta.get("saldo") is not None,
        "motivo_codigo": cuenta.get("motivo_codigo") or "",
        "motivo": cuenta.get("motivo") or "",
        # Dónde está: por lotes, que es lo que hace falta para saber si el envase que se va a gastar es
        # el de la partida que ha avisado el fabricante.
        "lotes": _los_lotes_con_su_cuenta(movimientos, articulo=articulo),
        # De qué ficha de la cesta sale, si sale de alguna. `None` es «este artículo es cosa suya»
        # (una semilla, el aceite del taller) y no es un error.
        "de_la_cesta": (
            {"clase": la_ficha_de_un_articulo(articulo)[0], "ficha_id": la_ficha_de_un_articulo(articulo)[1]}
            if la_ficha_de_un_articulo(articulo)
            else None
        ),
    }


def _los_lotes_con_su_cuenta(movimientos: list[dict], *, articulo: dict) -> list[dict]:
    """Cada envase con su saldo, para poder contestar «¿y esto de qué lote es?».

    Un lote **sin ningún movimiento** sale a cero, y eso se sabe (no es un «no se puede saber»): el
    envase está dado de alta y no ha entrado ni salido nada de él. Los que tienen movimientos se
    cuentan con la misma función que el total, uno por uno.
    """
    por_lote: dict[int, list[dict]] = {}
    for movimiento in movimientos:
        lote_id = movimiento.get("lote_id")
        if lote_id is None:
            continue
        por_lote.setdefault(int(lote_id), []).append(movimiento)
    return [
        {
            "lote_id": lote_id,
            "saldo": servicios.saldo_de_un_conjunto(
                suyos, (articulo.get("unidad") or "").strip() or None
            ).get("saldo"),
            "movimientos": len(suyos),
        }
        for lote_id, suyos in sorted(por_lote.items())
    ]


# --------------------------------------------------------------------------
# La vista: cada artículo una vez, con el mismo saldo para todas las pantallas
# --------------------------------------------------------------------------


@dataclass
class ElCuadreDeUnArticulo:
    """Un artículo, con su saldo físico y lo que la cesta dice de él. **Es lo que hay que pintar.**

    Esta es la pieza que hace que dos pantallas no puedan decir cosas distintas: el número de «te
    queda» es **uno** —`saldo_fisico`— y todo lo demás son sus motivos. La cesta aparece al lado
    (`compra_apuntada`, `consumo_apuntado`) **como lo que es**: un libro de papel, no unas existencias.
    """

    articulo_id: int | None
    nombre: str | None
    categoria: str
    unidad: str | None
    # Lo que hay, de verdad, según los movimientos. `None` = no se puede saber (y entonces se dice por
    # qué). Nunca un cero que signifique «no se sabe».
    saldo_fisico: float | None
    se_puede_saber: bool
    motivo_codigo: str
    motivo: str
    entradas: float | None
    salidas: float | None
    mermas: float | None
    ajustes: float | None
    movimientos: int
    lotes: list[dict] = field(default_factory=list)
    # La ficha de la cesta de la que sale este artículo (`producto` o `fertilizante`), si sale de
    # alguna. Es el lazo por identificador, no por nombre.
    de_la_cesta: dict | None = None
    # Lo que dice el otro libro. **No se suma al saldo**: está aquí para poder enseñarlo y para saber
    # si los dos están de acuerdo.
    compra_apuntada: float | None = None
    comprado_de_donde: str = ""
    consumo_apuntado: float | None = None
    apuntes_de_consumo: int = 0
    # `cuadra` | `pendiente` | `desconocido` | `descuadre`. Ver `la_situacion`.
    situacion: str = "desconocido"
    que_pasa: str = ""
    # Los consumos que este libro **no** vuelve a restar porque ya los restó el almacén, y el aviso de
    # que el mismo consumo está apuntado por las dos puertas. Ver `la_deduplicacion`.
    consumos_que_no_se_cuentan_dos_veces: int = 0
    el_mismo_consumo: list[dict] = field(default_factory=list)
    # Los apuntes que la cesta conoce y el almacén no: su consumo **no ha movido ningún envase**.
    apuntes_que_no_estan_en_el_almacen: list[dict] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def la_situacion(row: ElCuadreDeUnArticulo) -> tuple[str, str]:
    """En qué estado está el cuadre de un artículo, y con qué palabras se dice.

    Cuatro estados, y ninguno se puede confundir con otro:

      · **`cuadra`** — hay saldo físico conocido y todo lo que está apuntado está dentro del almacén.
        Las dos pantallas pueden enseñar el mismo número sin explicar nada.
      · **`pendiente`** — hay algo apuntado que **no tiene correspondencia** con el almacén (un consumo
        que no ha movido ningún envase, o un producto sin artículo). No es un descuadre y **no es un
        cero**: es trabajo de revisión, y se dice cuál.
      · **`desconocido`** — no se puede saber el saldo, y se dice por qué (falta la cantidad de una
        entrada, falta la unidad, o las unidades no se pueden comparar). Aquí no hay número que
        enseñar, y ponerlo sería inventárselo.
      · **`descuadre`** — hay saldo físico y lo que dice el otro libro no cabe en él. Señala que falta
        apuntar una entrada o que hay una salida de más; **no se corrige solo**.
    """
    avisos = list(row.avisos)
    if not row.se_puede_saber:
        return "desconocido", row.motivo
    # **Lo comprado que no ha entrado.** Se conoce el número de la compra y no hay ni un movimiento: la
    # mercancía no está en el almacén porque **no ha llegado**, y eso se dice en vez de dejar un cero
    # pelado que el agricultor leería como «no me queda». Es la respuesta literal al encargo: lo que no
    # tiene correspondencia queda pendiente.
    if row.movimientos == 0 and row.compra_apuntada:
        avisos.append(MENSAJES["A26_el_libro_viejo_no_tiene_saldo_fisico"])
        return "pendiente", " ".join(parte for parte in avisos if parte)
    if row.apuntes_que_no_estan_en_el_almacen or row.de_la_cesta is None:
        # Un artículo del almacén que no sale de ninguna ficha de la cesta (una semilla, el aceite del
        # taller) **no es un error**: tiene su saldo y con eso basta. Lo que sí hay que decir es que
        # **no ha entrado nunca**, porque entonces el cero es una falta de la entrada y no un saldo.
        if row.de_la_cesta is None and row.movimientos == 0:
            avisos.append(MENSAJES["A26_el_libro_viejo_no_tiene_saldo_fisico"])
        return "pendiente", " ".join(parte for parte in avisos if parte)
    if row.consumo_apuntado is not None and row.saldo_fisico is not None:
        # La cesta puede decir que se ha echado más de lo que ha entrado por el almacén. **No es una
        # acusación ni un cero**: es la señal de que falta apuntar una entrada, y se dice.
        if row.consumo_apuntado > (row.entradas or 0.0) + TOLERANCIA:
            avisos.append(textos.MENSAJES["A22_gastado_mas_que_comprado"])
            return "descuadre", " ".join(parte for parte in avisos if parte)
    return "cuadra", " ".join(parte for parte in avisos if parte)


def los_articulos_en_el_saldo_fisico(
    articulos: list[dict],
    movimientos: list[dict],
) -> list[ElCuadreDeUnArticulo]:
    """Un renglón por artículo del almacén, con **su** saldo físico y **sus** lotes.

    Se recorre el artículo y no el movimiento a propósito: un artículo del que no se ha movido nada
    —uno dado de alta y todavía sin albarán— tiene que salir también, porque su ausencia en la lista se
    leería como «esto no existe» y lo que pasa es que está a cero, que es una cosa que sí se sabe.
    """
    devueltos: list[ElCuadreDeUnArticulo] = []
    for articulo in sorted(articulos, key=lambda fila: (fila.get("nombre") or "", fila["id"])):
        suyos = los_movimientos_de_un_articulo(movimientos, articulo_id=articulo["id"])
        saldo = el_saldo_fisico(suyos, articulo=articulo)
        devueltos.append(
            ElCuadreDeUnArticulo(
                articulo_id=articulo["id"],
                nombre=articulo.get("nombre"),
                categoria=saldo["categoria"],
                unidad=saldo["unidad"],
                saldo_fisico=saldo["saldo"],
                se_puede_saber=saldo["se_puede_saber"],
                motivo_codigo=saldo["motivo_codigo"],
                motivo=saldo["motivo"],
                entradas=saldo["entradas"],
                salidas=saldo["salidas"],
                mermas=saldo["mermas"],
                ajustes=saldo["ajustes"],
                movimientos=saldo["movimientos"] or 0,
                lotes=saldo["lotes"],
                de_la_cesta=saldo["de_la_cesta"],
            )
        )
    return devueltos


def el_saldo_fisico_de_una_cesta(
    filas_de_la_cesta: list[dict],
    articulos: list[dict],
    movimientos: list[dict],
    *,
    apuntes: list[dict] | None = None,
    compra_sin_entrar: list[dict] | None = None,
) -> dict:
    """**La vista que hay que servir en todas las pantallas que enseñan «te queda».**

    Toma lo que devuelven las dos puertas que ya existen —las filas de la cesta
    (`situacion_de_la_cesta`), los artículos y los movimientos del almacén— y devuelve una lista en la
    que **cada artículo sale una vez, con un solo saldo**: el físico. La cesta viaja al lado, con su
    nombre y su número, para que se pueda revisar de dónde sale cada cosa.

    Devuelve:

      · **`articulos`** — cada artículo del almacén, con su `saldo_fisico` y su `situacion`.
      · **`pendientes`** — lo que **no** se ha podido relacionar: productos de la cesta que no tienen
        ningún artículo con el que enlazar. Su `saldo_fisico` es `None` con el aviso `A24`. Es la
        respuesta a «un dato antiguo sin correspondencia queda pendiente, no se convierte en cero».
      · **`compra_sin_entrar`** — lo comprado por factura que todavía no ha llegado. **No se suma a las
        existencias**: se declara aparte, que es lo que ya hace el almacén.
      · **`sin_saldo_conocido`** y **`descuadres`** — los artículos que no se pueden contar y los que
        señalan que falta un apunte. Los dos se cuentan para que la pantalla pueda decir «hay cinco
        cosas que revisar» sin tener que recorrer la lista.
      · **`avisos`** — los artículos, con nombre, que hay que mirar. Un número sin su nombre no se
        puede arreglar.

    Y una cosa que **no** devuelve: ninguna suma de los dos libros. No hay un «total» que mezcle lo
    comprado con lo que hay, porque ese número no significa nada.

    `apuntes` es **opcional y casi nunca hace falta**: sin él, la lista de consumos sale de los propios
    movimientos del almacén (`los_apuntes_por_ficha`), que es suficiente para reconocer el mismo consumo
    apuntado por las dos puertas. Se pasa cuando quien llama **sí** conoce los apuntes de la cesta que
    todavía no han movido ningún envase: así se puede decir «este consumo está apuntado y no ha salido de
    ningún lote», que es una de las cosas que hay que revisar.
    """
    compra_sin_entrar = compra_sin_entrar or []
    relacion = la_relacion_por_identificador(articulos)
    renglones = los_articulos_en_el_saldo_fisico(articulos, movimientos)

    por_articulo = {fila.articulo_id: fila for fila in renglones}
    # **Las fichas que sí han encontrado su artículo**, que es lo único que exime a un producto de la
    # lista de pendientes. Apuntar aquí todas las fichas vistas —aunque no tuvieran artículo— dejaría
    # fuera de la revisión justo los productos que hay que revisar.
    productos_con_articulo: set[tuple[str, int]] = set()

    for fila_de_la_cesta in sorted(
        filas_de_la_cesta, key=lambda fila: (fila.get("nombre_comercial") or "", fila.get("producto_id") or 0)
    ):
        clase, ficha_id = _la_ficha_de_una_fila_de_la_cesta(fila_de_la_cesta)
        if clase is None or ficha_id is None:
            continue
        articulo_id = el_articulo_de_una_ficha(clase, ficha_id, relacion)
        if articulo_id is None or articulo_id not in por_articulo:
            continue
        productos_con_articulo.add((clase, ficha_id))
        renglon = por_articulo[articulo_id]
        _pegar_la_cesta_al_articulo(
            renglon,
            fila_de_la_cesta,
            apuntes=apuntes,
            movimientos=movimientos,
            articulos=articulos,
        )

    for renglon in renglones:
        renglon.situacion, renglon.que_pasa = la_situacion(renglon)

    pendientes = _los_productos_sin_articulo(filas_de_la_cesta, productos_con_articulo)

    for renglon in renglones:
        if renglon.situacion == "pendiente" and renglon.que_pasa:
            renglon.avisos = _sin_repetir(renglon.avisos + [renglon.que_pasa])

    avisos = [
        {"articulo_id": fila.articulo_id, "nombre": fila.nombre, "que_pasa": fila.que_pasa}
        for fila in renglones
        if fila.que_pasa
    ]
    avisos += [
        {"articulo_id": None, "nombre": fila["nombre"], "que_pasa": fila["motivo"]}
        for fila in pendientes
    ]

    return {
        "articulos": renglones,
        "cuantos": len(renglones),
        "pendientes": pendientes,
        "cuantos_pendientes": len(pendientes),
        "compra_sin_entrar": compra_sin_entrar,
        "cuantos_sin_entrar": len(compra_sin_entrar),
        "sin_saldo_conocido": sum(1 for fila in renglones if not fila.se_puede_saber),
        "descuadres": sum(1 for fila in renglones if fila.situacion == "descuadre"),
        "avisos": avisos,
        # La clase de cada hecho, con su nombre, para que la pantalla no tenga que inventarse el
        # vocabulario: comprar, recibir, consumir y tener no son lo mismo.
        "que_es_cada_cosa": {
            "compra": ClaseDeHecho.COMPRA,
            "recepcion": ClaseDeHecho.RECEPCION,
            "consumo": ClaseDeHecho.CONSUMO,
            "existencia": ClaseDeHecho.EXISTENCIA,
        },
    }


def _la_ficha_de_una_fila_de_la_cesta(fila: dict) -> tuple[str | None, int | None]:
    """De qué ficha habla una fila de la cesta. Se aceptan los dos nombres del identificador.

    `producto_id` es el nombre del campo en la respuesta de `/api/productos/cesta/situacion`. La cesta
    también lleva abonos en otras vistas (`/api/facturas/resumen`), y ahí la clave es la otra. Se
    aceptan las dos formas a propósito: la pantalla no tiene que traducir nada.

    Y **una fila sin identificador no habla de ninguna ficha** (los dos `None`): devolver una ficha
    inventada sería unirlas por lo que se parecen, que es justo lo que no se puede hacer.
    """
    if fila.get("producto_id") is not None:
        return "producto", int(fila["producto_id"])
    if fila.get("fertilizante_id") is not None:
        return "fertilizante", int(fila["fertilizante_id"])
    return None, None


def _pegar_la_cesta_al_articulo(
    renglon: ElCuadreDeUnArticulo,
    fila_de_la_cesta: dict,
    *,
    apuntes: list[dict],
    movimientos: list[dict],
    articulos: list[dict],
) -> None:
    """Pone en el renglón lo que dice la cesta de ese artículo, **sin cambiarle el saldo**.

    Aquí está la mitad del encargo que más fácil es hacer mal: la tentación es «si la cesta dice 34 y el
    almacén dice 40, pongo 34». No: el saldo físico es el del almacén y la cesta se enseña **al lado**,
    con su nombre (`compra_apuntada`, `consumo_apuntado`), para que quien mire pueda revisar. Cambiar el
    número sin decirlo sería inventarse unas existencias.

    El cruce de consumos se hace **por identificador y solo con los de esta ficha**: un consumo del
    artículo A no puede justificar el apunte del producto B, aunque los dos se llamen parecido.
    """
    renglon.compra_apuntada = fila_de_la_cesta.get("comprado")
    renglon.comprado_de_donde = fila_de_la_cesta.get("comprado_de_donde") or ""
    renglon.consumo_apuntado = fila_de_la_cesta.get("gastado")
    renglon.apuntes_de_consumo = int(fila_de_la_cesta.get("apuntes") or 0)

    ficha = _la_ficha_de_una_fila_de_la_cesta(fila_de_la_cesta)
    por_ficha = los_apuntes_por_ficha(movimientos, articulos)
    # Si quien llama ya trae los apuntes de la cesta, mandan ellos: son los que dicen **de qué apunte**
    # sale cada consumo, incluido el que todavía no ha movido ningún envase. Si no los trae, se usan los
    # del almacén, que es lo que permite detectar el mismo consumo sin ayuda de nadie.
    suyos = [
        apunte
        for apunte in (apuntes or por_ficha.get(ficha, []))
        if _la_clave_del_apunte(apunte) is not None
        and _la_ficha_de_una_fila_de_la_cesta(apunte) == ficha
    ]
    deduplicado = la_deduplicacion(suyos, movimientos)
    renglon.consumos_que_no_se_cuentan_dos_veces = len(deduplicado["del_almacen"])
    renglon.el_mismo_consumo = [fila for fila in deduplicado["el_mismo_consumo"]]
    renglon.apuntes_que_no_estan_en_el_almacen = deduplicado["solo_en_la_cesta"]

    if renglon.el_mismo_consumo:
        renglon.avisos = _sin_repetir(
            renglon.avisos + [MENSAJES["A25_los_dos_libros_dicen_lo_mismo"]]
        )
    if renglon.apuntes_que_no_estan_en_el_almacen and not renglon.se_puede_saber:
        # Si además no se puede saber el saldo, el motivo que manda es el del saldo: es el que dice qué
        # falta para poder contestar.
        return
    if renglon.apuntes_que_no_estan_en_el_almacen:
        renglon.avisos = _sin_repetir(
            renglon.avisos + [MENSAJES["A26_el_libro_viejo_no_tiene_saldo_fisico"]]
        )


def los_apuntes_por_ficha(
    movimientos: list[dict], articulos: list[dict]
) -> dict[tuple[str, int], list[dict]]:
    """Los consumos del almacén, agrupados por **la ficha de la cesta** a la que pertenecen.

    Es la pieza que permite cruzar los dos libros sin adivinar nada: un movimiento sabe de qué artículo
    es (`MovimientoDeExistencias.articulo_id`), el artículo sabe de qué ficha sale
    (`Articulo.producto_id` / `fertilizante_id`) y el movimiento dice de qué apunte sale
    (`origen_tipo` + `origen_id`). Con las tres cosas se sabe **de qué producto es cada consumo**, y eso
    es lo que hace falta para no contarlo dos veces.

    Se agrupa aquí y no en quien llama para que la traducción de nombres la haga un solo sitio: `apuntes`
    es como se llaman los consumos dentro de este módulo, y `producto_id` es como se llama la ficha en
    la respuesta de la cesta.
    """
    la_ficha_de_cada_articulo = {
        articulo["id"]: la_ficha_de_un_articulo(articulo) for articulo in articulos
    }
    por_ficha: dict[tuple[str, int], list[dict]] = {}
    for movimiento in movimientos:
        # **Solo los que cuentan.** Una salida anulada —o cuyo apunte está anulado, que es la mitad de la
        # regla de que una anulación revierte el efecto— no ha gastado nada, así que no puede aparecer
        # como el consumo de nadie: si apareciera, el mismo consumo seguiría cruzándose después de
        # anularlo y la vista diría que no ha vuelto el producto.
        if not es_consumo(movimiento) or not servicio_contado(movimiento):
            continue
        ficha = la_ficha_de_cada_articulo.get(movimiento.get("articulo_id"))
        if ficha is None:
            # Un consumo de un artículo que no sale de ninguna ficha (una labor con gasóleo, por
            # ejemplo): se cuenta en el almacén y no se cruza con la cesta, porque no hay con qué.
            continue
        apunte = dict(movimiento)
        apunte["producto_id"] = ficha[1] if ficha[0] == "producto" else None
        apunte["fertilizante_id"] = ficha[1] if ficha[0] == "fertilizante" else None
        por_ficha.setdefault(ficha, []).append(apunte)
    return por_ficha


def _la_clave_del_apunte(apunte: dict) -> tuple[str, int] | None:
    """Con qué se reconoce un apunte de consumo de la cesta: su clase y su identificador.

    **No se usa el producto ni el nombre**: el apunte dice de qué apunte sale (`origen_tipo`), y eso es
    lo que permite cruzarlo con la salida del almacén sin adivinar nada.
    """
    if apunte.get("origen_id") is None or not apunte.get("origen_tipo"):
        return None
    return str(apunte["origen_tipo"]), int(apunte["origen_id"])


def _los_productos_sin_articulo(
    filas_de_la_cesta: list[dict], usados: set[tuple[str, int]]
) -> list[dict]:
    """Los productos de la cesta que **no tienen ningún artículo** con el que relacionarse.

    No se les pone un cero ni se busca «el artículo que se llame parecido»: se devuelven con
    `saldo_fisico: None` y su aviso, porque eso es un dato que hay que revisar a mano. Es la respuesta
    literal al encargo: *un dato antiguo sin correspondencia debe quedar pendiente, no convertirse en
    cero*.
    """
    pendientes: list[dict] = []
    for fila in sorted(
        filas_de_la_cesta, key=lambda x: (x.get("nombre_comercial") or "", x.get("producto_id") or 0)
    ):
        clase, ficha_id = _la_ficha_de_una_fila_de_la_cesta(fila)
        if clase is None or ficha_id is None or (clase, ficha_id) in usados:
            continue
        pendientes.append(
            {
                "clase": clase,
                "ficha_id": ficha_id,
                "nombre": fila.get("nombre_comercial"),
                "unidad": (fila.get("unidad_compra") or "").strip() or None,
                "compra_apuntada": fila.get("comprado"),
                "consumo_apuntado": fila.get("gastado"),
                # **Nunca un cero**: no hay artículo, así que no hay existencias que enseñar.
                "saldo_fisico": None,
                "se_puede_saber": False,
                "motivo_codigo": "A24_el_producto_no_tiene_articulo",
                "motivo": MENSAJES["A24_el_producto_no_tiene_articulo"],
                "situacion": "pendiente",
            }
        )
    return pendientes


def _sin_repetir(frases: list[str]) -> list[str]:
    """Las frases, sin repetir y sin perder el orden. Una pantalla con la misma frase tres veces parece
    rota aunque no lo esté."""
    vistas: list[str] = []
    for frase in frases:
        if frase and frase not in vistas:
            vistas.append(frase)
    return vistas


# --------------------------------------------------------------------------
# Lo que el coordinador necesita para crear el artículo que falta
# --------------------------------------------------------------------------


def el_articulo_que_falta_de_una_ficha(
    fila_de_la_cesta: dict, *, explotacion_id: int
) -> dict | None:
    """Los datos del artículo que hay que crear para una ficha de la cesta que no tiene ninguno.

    **Es una propuesta, no un hecho**: no se crea nada solo porque la cesta tenga un producto. Lo que
    hace esta función es decir qué artículo *habría que dar de alta* para que las dos vistas empezaran a
    hablar del mismo sitio, con el enlace por identificador ya puesto (`producto_id` o
    `fertilizante_id`), su categoría y **su unidad si se sabe**.

    Y si no se sabe la unidad, se queda en blanco: un producto de la cesta sin `unidad_compra` no pasa a
    ser «litros» por conveniencia. Es la misma regla del almacén (`Articulo.unidad` vacío = no se sabe).

    Devuelve `None` cuando la fila no dice de qué ficha habla: sin identificador no hay nada que enlazar,
    y unirlos por el nombre está prohibido.
    """
    clase, ficha_id = _la_ficha_de_una_fila_de_la_cesta(fila_de_la_cesta)
    if clase is None or ficha_id is None:
        return None
    nombre = (fila_de_la_cesta.get("nombre_comercial") or "").strip()
    if not nombre:
        return None
    return {
        "explotacion_id": explotacion_id,
        "nombre": nombre[:200],
        "categoria": CATEGORIA_DE_UNA_FICHA[clase],
        "unidad": (fila_de_la_cesta.get("unidad_compra") or "").strip()[:10] or None,
        "producto_id": ficha_id if clase == "producto" else None,
        "fertilizante_id": ficha_id if clase == "fertilizante" else None,
        # El número de registro, que es lo que identifica al producto sin lugar a dudas y lo que se
        # enseña cuando alguien pregunta de dónde salió. Puede no estar, y entonces no se pone.
        "numero_registro": (fila_de_la_cesta.get("numero_registro") or "").strip() or None,
        "como_se_ha_decidido": "por el identificador de la ficha, no por el nombre",
    }


# --------------------------------------------------------------------------
# Lo que hay que decir en la pantalla
# --------------------------------------------------------------------------


def el_texto_de_un_saldo(renglon: ElCuadreDeUnArticulo) -> str:
    """Lo que se lee en la pantalla para un artículo: el saldo **o el motivo de no poder decirlo**.

    Nunca devuelve «0» cuando no se sabe, y nunca deja al agricultor sin saber qué hacer: cuando no hay
    número, hay motivo, y el motivo dice dónde se arregla.

    El número se escribe **en castellano** (con coma decimal), que es como se lee bien en esta
    aplicación, y sin unidad no se enseña solo: «34» sin decir de qué no significa nada.
    """
    if not renglon.se_puede_saber:
        return renglon.motivo or textos.MENSAJES["A20_sin_cantidad_comprada"]
    numero = legal.formatea_numero(renglon.saldo_fisico)
    if renglon.unidad:
        return f"{numero} {renglon.unidad}"
    return f"{numero} ({MENSAJES['A28_no_hay_articulo_del_que_sacar_el_saldo']})"
