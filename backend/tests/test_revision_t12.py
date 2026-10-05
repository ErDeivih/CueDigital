"""Revisión independiente del T12: el dinero de las ventas (entregas, facturas y cobros).

## Qué es este fichero

No es la suite del ticket: es **el intento de romperla**. Cada prueba de aquí dice qué promesa del
informe `docs/T12_VENTAS.md` está atacando; las que llevan `DEFECTO` en el nombre **fallan mientras el
defecto exista** y pasan cuando se arregle, y llevan escrito **qué le pasaría al agricultor**.

## Foto del árbol (medida el 03/10/2026 a las 01:21:43, hora local)

| Fichero | Tamaño | Hora | sha256 (16 primeros) |
|---|---|---|---|
| `backend/app/dinero.py` | 19501 | 23:40:05 | `479E2BE4476CDD32` |
| `backend/app/ventas.py` | 17287 | 22:42:01 | `DB56505CA224A136` |
| `backend/app/routers/ventas_api.py` | 96891 | 01:03:34 | `C1E704BF77BEF90C` |
| `backend/app/models.py` | 154169 | 00:25:13 | `227664A1EC703778` |
| `backend/app/schemas.py` | 121294 | 23:27:36 | `C1BCCCF5D3B4A4FD` |
| `backend/app/textos.py` | 352385 | 00:43:29 | `7FA5ECEED3FE8072` |
| `backend/web/app.js` | 754318 | 00:18:18 | `DBEAA55DACCB8076` |
| `backend/web/react/pantallas/ventas.js` | 11326 | 00:18:23 | `9B9E4863246317DD` |
| `backend/web/react/piezas/tabla.js` | 11628 | 18:42:44 | `20D7FAC32A072929` |
| `backend/tests/test_el_dinero_de_las_ventas.py` | 93830 | 01:09:31 | `208E7903316082C5` |
| `backend/tests_js/react.test.js` | 390054 | 23:19:47 | `1AD57296E1812606` |
| `backend/tests_js/interfaz.test.js` | 660785 | 23:55:04 | `A5DD9D918B0192D1` |
| `docs/T12_VENTAS.md` | 43641 | 01:18:50 | `4056A4A98146C73F` |

> **El árbol se movió mientras se revisaba.** `docs/T12_VENTAS.md` y
> `tests/test_el_dinero_de_las_ventas.py` se editaron a las 01:09 y a las 01:18, **después** de empezar
> esta revisión (la primera lectura del informe decía «3.792 pruebas» y la última dice «3.793», que es
> lo que mide `pytest --collect-only`: **3793 tests collected**). Los defectos de aquí se han vuelto a
> medir sobre la última versión de los ficheros de código, que no han cambiado desde las 01:03.

## Los doce defectos

1. **`POST /api/ventas/{id}/ajustes` revienta con un 500** con cuatro entradas mal formadas (importe
   con decimales como número de JSON, importe o cantidad que no son números, fecha en castellano). El
   mismo cuerpo contra `/api/cobros` contesta 422 con una frase: aquí no hay esquema que valide.
2. **Texto de longitud libre en columnas con tope.** Nueve campos del dinero se aceptan con más letras
   de las que caben en su `varchar`: en SQLite se guardan y no pasa nada, **en PostgreSQL falla la
   operación entera** (500). Es el mismo defecto que ya llegó a producción con `auditoria.accion`.
3. **Un importe que no cabe en su columna (`VARCHAR(24)`) revienta en PostgreSQL** con un `DataError`.
4. **`GET /api/ventas` (la lista) no trae las cuentas del dinero y dice `facturada: false`** de una
   entrega que está dentro de una factura cobrada a medias.
5. **La tabla de S12 pone el rótulo «De dónde» encima de los botones** y no pinta nunca el valor de esa
   columna: el servidor manda doce columnas y la pantalla escribe once celdas más la de las acciones.
6. **Los tres enlaces con la ficha del cliente (`contacto_id`) no tienen puerta**: la columna existe,
   el endpoint la valida y ninguna pantalla la pregunta.
7. **28 de las 30 acciones nuevas del dinero no se pulsan en ninguna prueba** de JavaScript: solo se
   comprueba que su `data-accion` está pintado.
8. **El pie convierte «no se sabe» en `0,00 €`** cuando ninguna entrega del año tiene importe (A08).
9. **Un cobro que redondea a cero se acepta y se guarda como `0,00 €`**, que es justo lo que su propio
   aviso dice que no se admite.
10. **El aviso de la entrega repetida sale con el hueco en blanco** («ya está dentro de la factura .»)
    y dice algo que no es: esa entrega no está en ninguna factura.
11. **Una factura anulada enseña `0,00 €` y «0 entregas»**, aunque sus líneas siguen en la base.
12. **Una prueba del propio ticket se pone roja en PostgreSQL por construcción**: empieza con
    `assert engine.dialect.name == "sqlite"`, así que el viaje de ida y vuelta del importe por la base
    **no se comprueba en el motor de producción**.

## Cómo se ejecuta

```bash
cd backend
../.venv/Scripts/python.exe -m pytest tests/test_revision_t12.py -q
```

Y en PostgreSQL, que es donde salen dos de los tres defectos graves:

```bash
$env:CUEDIGITAL_SUITE_SOBRE="postgresql+psycopg://postgres:pruebas@127.0.0.1:55432/cuedigital_revision"
../.venv/Scripts/python.exe -m pytest tests/test_revision_t12.py -q
```

## Datos y bases

Todo va contra la base temporal que fija `conftest.py` (o la de PostgreSQL que se pida con
`CUEDIGITAL_SUITE_SOBRE`). **Ninguna prueba toca `backend/cuedigital.db`.** El único fichero del disco
que se lee, además de los del repositorio, es `web/app.js`, y solo para contar acciones y mirar qué
campos manda cada pantalla.
"""

from __future__ import annotations

import json
import pathlib
import re

from app import dinero, models, textos

RAIZ = pathlib.Path(__file__).resolve().parents[2]
APP_JS = RAIZ / "backend" / "web" / "app.js"
TESTS_JS = RAIZ / "backend" / "tests_js"

# El texto que no cabe en las columnas de 200, 120, 80 y 20 caracteres. Se usa el mismo para todos los
# casos y se compara con el ancho que declara el modelo, no con un número escrito a mano.
LARGO = "L" * 250


def _el_cuerpo_de_una_funcion(codigo: str, nombre: str) -> str:
    """El texto de una función de `app.js`, desde su declaración hasta la siguiente de primer nivel.

    Es el mismo tipo de lectura que ya usan los guardianes de `tests/test_interfaz.py` sobre ese
    fichero: se busca la cabecera y se corta en la línea que empieza otra función.
    """
    empieza = codigo.find(f"function {nombre}(")
    assert empieza != -1, f"no encuentro la función {nombre} en app.js"
    resto = codigo[empieza:]
    siguiente = re.search(r"\n(?:async )?function \w+\(", resto)
    return resto[: siguiente.start()] if siguiente else resto


def _las_acciones_de_la_pantalla_del_dinero() -> list[str]:
    """Las acciones del T12 que el manejador de clics de `app.js` sabe atender.

    Se reconocen por su prefijo, que es el de este ticket: `ventas-`, `venta-`, `ajuste-`, `facturar-`,
    `facturas-emitidas-`, `factura-emitida-`, `cobro-` y `cobros-`. Las de `factura-nueva`, `factura-leer`
    y compañía **no** entran: son las facturas de compra del T09.
    """
    codigo = APP_JS.read_text(encoding="utf-8")
    prefijos = (
        "ventas-", "venta-", "ajuste-", "facturar-", "facturas-emitidas-",
        "factura-emitida-", "cobro-", "cobros-",
    )
    acciones = set()
    for accion in re.findall(r'nombre === "([^"]+)"', codigo):
        if accion.startswith(prefijos):
            acciones.add(accion)
    return sorted(acciones)


def _las_acciones_que_se_pulsan() -> set[str]:
    """Las acciones que alguna prueba de JavaScript pulsa de verdad, por el manejador delegado."""
    pulsadas: set[str] = set()
    for fichero in TESTS_JS.glob("*.test.js"):
        texto = fichero.read_text(encoding="utf-8")
        pulsadas.update(re.findall(r'pulsar\(\s*(?:entorno|contexto)?\s*,?\s*"([^"]+)"', texto))
    return pulsadas


def _un_entrega_con(cuenta, campana, **cambios) -> dict:
    """El cuerpo de una entrega, para poder mandarlo desde cada prueba como le convenga."""
    datos = {
        "campana_id": campana["id"],
        "tipo": "comercializada",
        "fecha": "2026-07-10",
        "producto": "Trigo blando",
        "variedad": "Craklin",
        "cantidad": 42000.0,
        "unidad": "kg",
        "lote": "L-2026-07",
        "comprador": "Cooperativa Agrícola de Peñaranda",
        "numero_albaran": "ALB-2026-118",
    }
    datos.update(cambios)
    return datos


def _crear(cliente, cuenta, campana, **cambios) -> dict:
    respuesta = cliente.post(
        "/api/ventas", headers=cuenta["cabeceras"], json=_un_entrega_con(cuenta, campana, **cambios)
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _facturar(peticion, sesion, entrega_ids, **cambios) -> dict:
    """Manda una factura con esas entregas. Los dos primeros nombres **no** son `cliente` y `cuenta`
    a propósito: `cliente` es una de las columnas de la factura y chocaría con el parámetro."""
    cuerpo = {"fecha": "2026-07-20", "entregas": list(entrega_ids)}
    cuerpo.update(cambios)
    return peticion.post("/api/facturas-emitidas", headers=sesion["cabeceras"], json=cuerpo)


def _mandar_sin_reventar(llamada):
    """Hace una petición y devuelve `(estado, texto)`, **aunque el servidor reviente**.

    Hace falta porque el cliente de pruebas de `conftest.py` está puesto con
    `raise_server_exceptions` por defecto: cuando el endpoint lanza (un `DataError` de PostgreSQL, un
    `ErrorDeDinero`) la excepción sube hasta la prueba en vez de llegar como un 500. Lo que se está
    midiendo es justo esa excepción, así que se recoge y se cuenta como un 500.
    """
    try:
        respuesta = llamada()
    except Exception as fallo:  # noqa: BLE001 — es justo lo que se está midiendo
        return 500, f"{type(fallo).__name__}: {fallo}".split("[SQL:")[0].strip()
    return respuesta.status_code, respuesta.text


# --------------------------------------------------------------------------
# DEFECTO 1: el ajuste de una entrega revienta con un 500
# --------------------------------------------------------------------------


class TestDefecto1ElAjusteRevientaConUn500:
    """`POST /api/ventas/{id}/ajustes` recibe un `dict` crudo y llama a `dinero.a_decimal`,
    `dinero.de_texto` y `date.fromisoformat` **sin ningún esquema que valide antes**.

    Lo que pasa: un importe mandado como número de JSON (que es como lo manda cualquier cliente que no
    sea esta pantalla), un importe o una cantidad que no son números, o una fecha escrita en
    castellano, lanzan `ErrorDeDinero`/`ValueError` **dentro del endpoint** y el servidor contesta
    **500**. Lo que debería pasar: un 422 con la frase escrita para el agricultor, como ya hace
    `POST /api/cobros`, que sí tiene esquema y contesta 422 con el mismo cuerpo.

    Por qué importa: el móvil **reintenta los 5xx** (`app.js`, `mandarPendientes`: «el servidor está de
    mal humor: se reintenta luego»), así que un 500 que no se arregla solo se queda en la cola para
    siempre. Y un apunte de dinero que se pierde con una pantalla que dice «no se ha podido» es
    exactamente lo que este programa no puede hacer.
    """

    CASOS = [
        ("el importe como número de coma flotante", {"importe": -1.5}),
        ("el importe como texto que no es un número", {"importe": "muchos"}),
        ("la cantidad como texto que no es un número", {"cantidad": "como mil"}),
        ("la fecha escrita en castellano", {"importe": "-1.00", "fecha": "10/07/2026"}),
    ]

    def test_defecto_1_una_entrada_mal_escrita_no_puede_tumbar_el_servidor(
        self, cliente, cuenta, campana
    ):
        entrega = _crear(cliente, cuenta, campana, importe="121.00")
        for nombre, cambio in self.CASOS:
            cuerpo = {
                "tipo": "peso",
                "origen": "cliente",
                "motivo": "la báscula dio menos kilos",
                "importe": "-1.00",
            }
            cuerpo.update(cambio)
            estado, texto = _mandar_sin_reventar(
                lambda cuerpo=cuerpo: cliente.post(
                    f"/api/ventas/{entrega['id']}/ajustes",
                    headers=cuenta["cabeceras"],
                    json=cuerpo,
                )
            )
            assert estado < 500, (
                f"con {nombre}, el servidor contesta {estado}: {texto[:200]}. Lo que tiene que pasar "
                "es un 422 con la frase del agricultor (como en /api/cobros). Un 5xx en un apunte de "
                "dinero se queda en la cola del móvil reintentándose para siempre."
            )


# --------------------------------------------------------------------------
# DEFECTO 2: texto de longitud libre en columnas con tope
# --------------------------------------------------------------------------


class TestDefecto2LoQueSeAceptaTieneQueCaberEnSuColumna:
    """El mismo defecto que ya llegó a producción con `auditoria.accion` (30 caracteres), otra vez.

    Los nueve campos de abajo se rellenan con texto libre —un nombre, una referencia del banco, la
    evidencia de un ajuste, el número de una factura— y todos acaban en una columna con tope.
    **SQLite no comprueba la longitud de un `VARCHAR`**, así que en el ordenador del agricultor no pasa
    nada; **PostgreSQL sí**, y como la fila se escribe en la misma transacción, lo que falla entero es
    la operación: un 500 y el apunte sin guardar.

    Lo que debería pasar, en cualquiera de los dos motores: o el texto se rechaza con una frase (422),
    o se guarda **cabiendo**. Lo que no puede pasar es aceptarlo y guardarlo entero en un sitio donde
    no cabe, porque entonces el mismo programa funciona en un motor y no en el otro.
    """

    def _los_campos(self, cliente, cuenta, campana, db_sesion):
        """Cada campo: cómo se manda, su ancho declarado y cómo se lee lo que ha quedado guardado."""
        def nueva():
            return _crear(cliente, cuenta, campana, importe="121.00")

        def anchura(modelo, columna):
            return modelo.__table__.columns[columna].type.length

        casos = []

        # --- El ajuste de una entrega
        entrega = nueva()
        casos.append((
            "ajustes_de_entrega.evidencia_descripcion",
            anchura(models.AjusteDeEntrega, "evidencia_descripcion"),
            lambda: cliente.post(
                f"/api/ventas/{entrega['id']}/ajustes",
                headers=cuenta["cabeceras"],
                json={
                    "tipo": "peso", "origen": "bascula", "motivo": "menos kilos",
                    "importe": "-1.00", "evidencia_descripcion": LARGO,
                },
            ),
            lambda cuerpo: json.dumps(
                cliente.get(
                    f"/api/ventas/{entrega['id']}/ajustes", headers=cuenta["cabeceras"]
                ).json(),
                ensure_ascii=False,
            ),
        ))

        # --- El cobro: la referencia del banco y el nombre del cliente
        for columna, campo in (("referencia", "referencia"), ("cliente", "cliente")):
            casos.append((
                f"cobros.{columna}",
                anchura(models.Cobro, columna),
                lambda campo=campo: cliente.post(
                    "/api/cobros",
                    headers=cuenta["cabeceras"],
                    json={"importe": "1.00", "forma": "transferencia", campo: LARGO},
                ),
                lambda cuerpo, campo=campo: json.dumps(cuerpo, ensure_ascii=False),
            ))

        # --- La factura: su número, su cliente y su NIF
        for columna, campo in (("numero", "numero"), ("cliente", "cliente"), ("cliente_nif", "cliente_nif")):
            casos.append((
                f"facturas_emitidas.{columna}",
                anchura(models.FacturaEmitida, columna),
                lambda campo=campo: _facturar(
                    cliente, cuenta, [nueva()["id"]], **{campo: LARGO}
                ),
                lambda cuerpo, campo=campo: json.dumps(cuerpo, ensure_ascii=False),
            ))

        # --- La entrega: el comprador, el albarán y la clave de reenvío
        for columna, campo in (("comprador", "comprador"), ("numero_albaran", "numero_albaran")):
            casos.append((
                f"ventas_de_cosecha.{columna}",
                anchura(models.VentaDeCosecha, columna),
                lambda campo=campo: cliente.post(
                    "/api/ventas",
                    headers=cuenta["cabeceras"],
                    json=_un_entrega_con(cuenta, campana, **{campo: LARGO}),
                ),
                lambda cuerpo: json.dumps(cuerpo, ensure_ascii=False),
            ))
        casos.append((
            "ventas_de_cosecha.clave_de_reenvio",
            anchura(models.VentaDeCosecha, "clave_de_reenvio"),
            lambda: cliente.post(
                "/api/ventas",
                headers=cuenta["cabeceras"],
                json=_un_entrega_con(cuenta, campana, clave_de_reenvio=LARGO),
            ),
            # Esta no vuelve por la API, así que se lee **de la base**: es el dato que se guardó.
            lambda cuerpo: str(
                (
                    db_sesion.execute(
                        models.VentaDeCosecha.__table__.select().where(
                            models.VentaDeCosecha.id == cuerpo["id"]
                        )
                    ).first()
                ).clave_de_reenvio
                or ""
            ),
        ))
        return casos

    def test_defecto_2_un_texto_que_no_cabe_no_se_puede_aceptar_en_silencio(
        self, cliente, cuenta, campana, db_sesion
    ):
        largos = []
        for nombre, ancho, mandar, leer in self._los_campos(cliente, cuenta, campana, db_sesion):
            assert ancho and ancho < len(LARGO), f"{nombre} no tiene tope: {ancho}"
            estado, texto = _mandar_sin_reventar(mandar)
            if estado >= 500:
                largos.append(
                    f"{nombre}: el servidor contesta {estado} y la operación entera se pierde "
                    f"(no cabe en varchar({ancho})): {texto[:120]}"
                )
                continue
            if estado != 201:
                continue  # rechazado con una frase: es una forma válida de arreglarlo
            guardado = leer(json.loads(texto))
            # Lo que la prueba tiene que ver es el **valor guardado**, no la respuesta: se lee del
            # JSON con los espacios de más quitados, que es lo único que distingue una cadena larga.
            if LARGO in guardado:
                largos.append(
                    f"{nombre}: se ha aceptado (201) un texto de {len(LARGO)} caracteres en una "
                    f"columna de {ancho}"
                )
        assert not largos, (
            "hay campos del dinero que aceptan texto que no cabe en la columna donde lo guardan:\n  "
            + "\n  ".join(largos)
            + "\nEn SQLite no se nota (no comprueba la longitud de un VARCHAR); en PostgreSQL falla "
            "la operación entera y el agricultor ve «no se ha podido»."
        )


# --------------------------------------------------------------------------
# DEFECTO 3: un importe que no cabe en su columna
# --------------------------------------------------------------------------


class TestDefecto3UnImporteQueNoCabeEnSuColumna:
    """La columna del dinero admite **24 caracteres** (`dinero.MAXIMO_DE_CIFRAS`) y `dinero.a_texto` no
    mira cuántos ocupa lo que devuelve: un importe con 22 cifras enteras se guarda como
    `"999999999999999999999999.99"`, que son 27.

    En SQLite entra (201). En PostgreSQL es un `StringDataRightTruncation` y el servidor contesta 500:
    la entrega no se apunta y el agricultor no sabe por qué. Es la misma familia que el `varchar(30)`
    del rastro, y sale por la puerta del dinero.
    """

    EL_QUE_NO_CABE = "999999999999999999999999.99"  # 27 caracteres

    def test_defecto_3_el_importe_guardado_tiene_que_caber_en_su_columna(
        self, cliente, cuenta, campana
    ):
        assert len(self.EL_QUE_NO_CABE) > dinero.MAXIMO_DE_CIFRAS, "el número de prueba ya cabría"
        estado, texto = _mandar_sin_reventar(
            lambda: cliente.post(
                "/api/ventas",
                headers=cuenta["cabeceras"],
                json=_un_entrega_con(cuenta, campana, importe=self.EL_QUE_NO_CABE),
            )
        )
        if estado == 201:
            guardado = dinero.a_texto(dinero.a_decimal(json.loads(texto)["importe"]))
            raise AssertionError(
                f"se ha aceptado (201) un importe que no cabe en su columna: «{guardado}» mide "
                f"{len(guardado)} caracteres y la columna {dinero.MAXIMO_DE_CIFRAS}. En SQLite entra; "
                "en PostgreSQL la operación entera falla con un DataError y el agricultor ve un 500."
            )
        assert estado < 500, (
            f"el servidor contesta {estado} al guardar un importe grande: {texto[:200]}. Lo que tiene "
            "que pasar es una frase (422) que diga que ese importe no puede ser."
        )


# --------------------------------------------------------------------------
# DEFECTO 4: la lista no dice lo mismo que la ficha
# --------------------------------------------------------------------------


class TestDefecto4LaListaNoDiceLoMismoQueLaFicha:
    """`GET /api/ventas` llama a `con_nombres(db, venta)` **sin pasarle la explotación**, así que
    `_las_cuentas_en_la_salida` no se ejecuta: la lista devuelve la entrega con
    `importe_total: None`, `texto_importe: ""`, `cobrado: null`, `pendiente: null`, `estado: ""`,
    `etiqueta_estado: ""` y **`facturada: false`**… de una entrega que está dentro de una factura con
    un cobro a medias.

    `facturada: false` no es un hueco: es una afirmación falsa, que es la peor forma de un dato que no
    se sabe (el programa dice «no está facturada» en vez de «no lo he mirado»). La ficha
    (`GET /api/ventas/{id}`) y la tabla (`/api/ventas/tabla`) sí lo dicen bien: **tres puertas del
    mismo dato y dos contestan distinto**.
    """

    def test_defecto_4_la_lista_y_la_ficha_dicen_lo_mismo_del_dinero(
        self, cliente, cuenta, campana
    ):
        entrega = _crear(cliente, cuenta, campana, importe="121.00")
        factura = _facturar(cliente, cuenta, [entrega["id"]], numero="F-1").json()
        cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"importe": "40.00", "factura_emitida_id": factura["id"], "forma": "efectivo"},
        )
        ficha = cliente.get(f"/api/ventas/{entrega['id']}", headers=cuenta["cabeceras"]).json()
        en_la_lista = [
            venta
            for venta in cliente.get("/api/ventas", headers=cuenta["cabeceras"]).json()
            if venta["id"] == entrega["id"]
        ][0]
        for campo in ("importe_total", "cobrado", "pendiente", "texto_importe_total",
                      "texto_cobrado", "texto_pendiente", "estado", "facturada"):
            assert en_la_lista[campo] == ficha[campo], (
                f"la lista de ventas dice {campo}={en_la_lista[campo]!r} y la ficha de la misma "
                f"entrega dice {campo}={ficha[campo]!r}. La tabla (`/api/ventas/tabla`) coincide con "
                "la ficha, así que la que miente es la lista."
            )


# --------------------------------------------------------------------------
# DEFECTO 5: el rótulo de la última columna de la tabla
# --------------------------------------------------------------------------


class TestDefecto5LaUltimaColumnaDeLaTabla:
    """La pieza `Tabla` (`web/react/piezas/tabla.js`) pinta **una cabecera por columna** y, al final de
    cada fila, **la celda de las acciones** (los botones). Por eso quien prepara una tabla escribe una
    celda menos que columnas tiene: la última columna es la de las acciones.

    En la tabla de S12 eso no se cumple: el servidor manda **doce columnas de datos** —la última, `donde`
    («De dónde»)— y `pantallaVentas` escribe once celdas más la de acciones. El resultado, medido
    renderizando la pantalla con la tabla de verdad (`renderToStaticMarkup`):

        cabeceras: [..., "Albarán", "De dónde"]
        celdas:    [..., "ALB-2026-118", "PONER EL IMPORTE"]

    O sea: el rótulo **«De dónde» cae encima de los botones** y el valor de esa columna **no se pinta
    nunca** en el ordenador (en la tarjeta del móvil sí). El rótulo de las acciones existe ya en los
    textos del servidor (`textos.VENTA["tabla_acciones"]`, «Acciones») y **no lo usa nadie**: es la
    columna que falta.

    El arreglo más corto es añadirla al final de `ventas_api.COLUMNAS_DE_LA_TABLA` (sin clave de dato,
    `ordenable=False`), con lo que la pantalla escribe las doce celdas y la decimotercera es la de los
    botones. Si se arregla en `app.js` (que añada él la columna de acciones y escriba una celda por
    cada columna del servidor), esta prueba habrá que reescribirla para mirar la pantalla en vez de la
    respuesta: lo que no puede quedar es el rótulo de una columna de datos encima de los botones.
    """

    def test_defecto_5_la_ultima_columna_es_la_de_las_acciones(self, cliente, cuenta, campana):
        _crear(cliente, cuenta, campana, importe="121.00")
        tabla = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        columnas = tabla["columnas"]
        ultima = columnas[-1]
        assert ultima["clave"] == "acciones", (
            f"la última columna de la tabla es «{ultima['clave']}» («{ultima['texto']}») y la pantalla "
            "escribe una celda menos que columnas porque da por hecho que la última es la de las "
            "acciones: su rótulo acaba encima de los botones y su valor no se pinta. La columna que "
            "falta lleva el rótulo que ya está en los textos del servidor: "
            f"«{textos.VENTA['tabla_acciones']}»."
        )
        assert ultima["texto"] == textos.VENTA["tabla_acciones"]
        assert not ultima["ordenable"], "la columna de las acciones no se puede ordenar"
        # Y todas las columnas de datos siguen estando: no se arregla quitando «De dónde».
        claves = [columna["clave"] for columna in columnas]
        for esperada in ("cliente", "producto", "fecha", "cantidad", "importe", "vencimiento",
                         "cobrado", "pendiente", "donde"):
            assert esperada in claves, f"falta la columna «{esperada}»: {claves}"


# --------------------------------------------------------------------------
# DEFECTO 6: los enlaces con la ficha del cliente no tienen puerta
# --------------------------------------------------------------------------


class TestDefecto6LosEnlacesConLaFichaDelCliente:
    """El T12 añade tres columnas `contacto_id` (en la entrega, en la factura y en el cobro) y el
    informe las presenta como la mitad de lo que hace falta para contestar «¿cuánto me debe la
    cooperativa?» **sin comparar nombres a ojo** (§1.3 y §3.1 de `docs/T12_VENTAS.md`).

    El endpoint las valida (`_comprobar_sitio`) y el modelo las guarda… pero **ninguna pantalla las
    pregunta**: en `app.js`, la pantalla del importe se limita a devolver `contacto_id: entrega.contacto_id`
    (para no borrarlo al corregir) y ni la factura ni el cobro lo mandan siquiera. Es el fallo que
    `AGENTS.md` §4 llama el que más veces ha pagado este proyecto: **un campo en el modelo sin pantalla
    que lo pregunte**, el mismo que tuvo el cultivo del año anterior y los datos de la portada del
    cuaderno. El informe §3.8 presume de que «los cuatro campos del dinero tienen su puerta»: estos
    tres no la tienen.
    """

    def test_defecto_6_las_tres_columnas_nuevas_se_preguntan_en_alguna_pantalla(self):
        codigo = APP_JS.read_text(encoding="utf-8")
        sin_puerta = []
        for funcion, donde in (
            ("guardarElImporteDeUnaEntrega", "la pantalla del importe de una entrega"),
            ("guardarLaFacturaEmitida", "la pantalla de hacer la factura"),
            ("guardarElCobro", "la pantalla de apuntar un cobro"),
        ):
            cuerpo = _el_cuerpo_de_una_funcion(codigo, funcion)
            # La puerta es un campo del formulario: se lee con `leer(...)` y se manda. Devolver el
            # valor que ya traía (`contacto_id: entrega.contacto_id`) no es una puerta.
            if not re.search(r"contacto_id:\s*(?:Number\(\s*)?leer\(", cuerpo):
                sin_puerta.append(f"{donde} ({funcion}) no pregunta el contacto")
        assert not sin_puerta, (
            "el cliente de una entrega, de una factura y de un cobro no se puede enlazar con su ficha "
            "desde ninguna pantalla:\n  " + "\n  ".join(sin_puerta)
            + "\nLa columna existe, el endpoint la comprueba y el informe la presenta como la forma de "
            "saber cuánto debe cada cliente: o se pregunta, o no se promete."
        )


# --------------------------------------------------------------------------
# DEFECTO 7: los botones del dinero no se pulsan en ninguna prueba
# --------------------------------------------------------------------------


class TestDefecto7LosBotonesDelDinero:
    """`tests_js/react.test.js` comprueba los botones nuevos **mirando el HTML** (`data-accion="…"`), y
    eso solo demuestra que están pintados: que `app.js` sepa atenderlos no lo prueba nadie.

    Medido: de las **30 acciones del dinero** que el manejador de clics de `app.js` sabe atender
    (`ventas-`, `venta-`, `ajuste-`, `facturar-`, `facturas-emitidas-`, `factura-emitida-`, `cobro-`),
    solo **dos** se pulsan en alguna prueba (`ventas-nueva` y `ventas-ver`). Las otras **28** —poner el
    importe, guardarlo, apuntar un ajuste, hacer la factura, cobrar, conciliar, anular, buscar, los dos
    filtros…— no se ejecutan ni una vez. Es el hueco que en el T10 escondió un botón roto y en el T11
    dejó las cuatro pantallas de contactos sin probar.

    (Las diez acciones de `factura-nueva`, `factura-leer`, `factura-mano`, `factura-guardar`,
    `factura-papel-…` y `facturas-abrir` **no** entran en esta cuenta: son las facturas de compra del
    T09 y sí se pulsan.)

    (Comprobado aparte, para que se lea entero: **las 20 funciones que esos botones llaman existen** en
    `app.js`, así que hoy no hay ninguno roto: lo que falta es la prueba que lo demuestre.)
    """

    def test_defecto_7_cada_accion_del_dinero_se_pulsa_en_alguna_prueba(self):
        acciones = _las_acciones_de_la_pantalla_del_dinero()
        assert len(acciones) >= 30, f"solo se han encontrado {len(acciones)} acciones del dinero"
        pulsadas = _las_acciones_que_se_pulsan()
        sin_pulsar = [accion for accion in acciones if accion not in pulsadas]
        assert not sin_pulsar, (
            f"{len(sin_pulsar)} de las {len(acciones)} acciones del dinero no se pulsan en ninguna "
            "prueba de JavaScript (solo se comprueba que su `data-accion` está pintado): "
            + ", ".join(sin_pulsar)
        )


# --------------------------------------------------------------------------
# DEFECTO 8: el pie convierte «no se sabe» en cero
# --------------------------------------------------------------------------


class TestDefecto8ElPieNoConvierteLoQueNoSeSabeEnCero:
    """El caso A08 dice: «Venta con 8.000 kg y sin precio → cantidad conocida, importe pendiente; **no
    ingreso cero**». La fila lo cumple (su importe sale vacío y el aviso dice que a una entrega le falta
    el importe), pero **el pie y los totales no**: con una sola entrega, de la que no se sabe el
    importe, el pie dice

        «1 entrega · 0,00 € · pendiente 0,00 €»

    y `totales["importe"]` es `"0.00"`. Es un total que afirma que este año se ha vendido por cero euros,
    que es justo lo que el A08 prohíbe: «no lo sé» y «cero» no son lo mismo. Un año entero de entregas
    sin precio daría «0,00 €» en el número más grande de la pantalla.
    """

    def test_defecto_8_el_pie_no_dice_cero_euros_cuando_no_se_sabe(
        self, cliente, cuenta, campana
    ):
        _crear(cliente, cuenta, campana, producto="Cebada", cantidad=8000.0, importe=None)
        tabla = cliente.get("/api/ventas/tabla", headers=cuenta["cabeceras"]).json()
        assert tabla["totales"]["sin_importe"] == 1, "la prueba no ha montado el caso A08"
        assert "0,00 €" not in tabla["pie"], (
            f"el pie dice «{tabla['pie']}» de una entrega cuyo importe no se sabe. Cero euros y «no lo "
            "sé» no son lo mismo: el pie tiene que decir que el importe no se sabe."
        )


# --------------------------------------------------------------------------
# DEFECTO 9: un cobro que redondea a cero
# --------------------------------------------------------------------------


class TestDefecto9UnCobroQueRedondeaACero:
    """`apuntar_un_cobro` comprueba `importe <= 0` **antes** de redondear al céntimo, así que un cobro
    de `0.004` se acepta (201), se guarda como `"0.00"` y la pantalla lo enseña como «0,00 €»: un
    movimiento de cero euros en la lista, que es exactamente lo que el propio aviso del endpoint dice
    que no se admite («Un cobro de cero euros no es un cobro»).

    Lo que debería pasar: rechazarlo con esa misma frase, porque lo que se va a guardar es cero.
    """

    def test_defecto_9_un_cobro_de_cuatro_milesimas_no_es_un_cobro(self, cliente, cuenta, campana):
        respuesta = cliente.post(
            "/api/cobros",
            headers=cuenta["cabeceras"],
            json={"importe": "0.004", "forma": "efectivo"},
        )
        if respuesta.status_code == 201:
            cobro = respuesta.json()["cobro"]
            raise AssertionError(
                f"se ha aceptado un cobro de «0.004» y queda guardado y enseñado como "
                f"«{cobro['texto_importe']}» (importe {cobro['importe']}): un renglón de cero euros en "
                "la lista de lo que ha entrado. El endpoint ya dice que un cobro de cero euros no es un "
                "cobro; lo que falta es comprobarlo sobre lo que se guarda, no sobre lo que llega."
            )
        assert respuesta.status_code < 500


# --------------------------------------------------------------------------
# DEFECTO 10: el aviso de la entrega repetida en la misma petición
# --------------------------------------------------------------------------


class TestDefecto10ElAvisoDeLaEntregaRepetida:
    """Cuando la misma entrega viaja dos veces en la misma petición de facturar, el endpoint contesta
    con el aviso `D6_esa_entrega_ya_esta_facturada` **con el número vacío**, y el agricultor lee:

        «Esa entrega ya está dentro de la factura . Una entrega no puede estar en dos facturas…»

    Dos defectos en una frase: el hueco en blanco donde iba el nombre, y que **dice algo que no es** —
    esa entrega no está en ninguna factura; lo que pasa es que se ha mandado dos veces en la misma
    petición—. La prueba del ticket (`test_la_misma_entrega_reenviada_no_se_factura_dos_veces`) comprueba
    el 422, no lo que se lee.
    """

    def test_defecto_10_el_aviso_no_sale_con_el_hueco_en_blanco(self, cliente, cuenta, campana):
        entrega = _crear(cliente, cuenta, campana, importe="121.00")
        respuesta = _facturar(cliente, cuenta, [entrega["id"], entrega["id"]])
        assert respuesta.status_code == 422, respuesta.text
        detalle = json.dumps(respuesta.json(), ensure_ascii=False)
        assert "factura ." not in detalle and "factura  " not in detalle, (
            f"el aviso sale con el hueco en blanco: {detalle[:220]}. Que la entrega que se ha mandado "
            "dos veces no está en ninguna factura: lo que hay que decir es eso, no que está dentro de "
            "una factura sin nombre."
        )


# --------------------------------------------------------------------------
# DEFECTO 11: una factura anulada enseña cero
# --------------------------------------------------------------------------


class TestDefecto11UnaFacturaAnuladaEnseñaCero:
    """«Anular no borra nada» y «anular la factura libera sus entregas» son ciertas en los datos: las
    líneas se quedan en la base con su `anulada` y su motivo. Lo que no es cierto es lo que **enseña**
    la ficha: `como_se_ve_una_factura` solo mira las líneas vivas, así que la factura anulada contesta
    `texto_total: "0,00 €"` y `entregas: 0`.

    O sea que el documento que se emitió —121,00 €, con su entrega dentro— pasa a leerse como una
    factura de cero euros, que es la misma trampa del A08 («no lo sé» convertido en cero) aplicada a un
    documento. Para mirar dentro de un año qué se emitió y por qué se anuló, lo que hay que ver es lo
    que ponía, no un cero.
    """

    def test_defecto_11_la_factura_anulada_sigue_diciendo_lo_que_decia(
        self, cliente, cuenta, campana
    ):
        entrega = _crear(cliente, cuenta, campana, importe="121.00")
        factura = _facturar(cliente, cuenta, [entrega["id"]], numero="F-1").json()
        assert factura["texto_total"] == "121,00 €", factura["texto_total"]
        anulada = cliente.post(
            f"/api/facturas-emitidas/{factura['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me equivoqué al agrupar"},
        )
        assert anulada.status_code == 200, anulada.text
        vista = cliente.get(
            f"/api/facturas-emitidas/{factura['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert vista["anulada"] is True
        assert vista["texto_total"] != "0,00 €" and vista["entregas"] != 0, (
            f"la factura anulada enseña «{vista['texto_total']}» y {vista['entregas']} entregas, "
            "aunque lo que se emitió fue «121,00 €» con una entrega dentro y sus líneas siguen en la "
            "base con su motivo de anulación. Un documento anulado no es un documento de cero euros."
        )


# --------------------------------------------------------------------------
# DEFECTO 12: una prueba del ticket se pone roja en PostgreSQL por construcción
# --------------------------------------------------------------------------

EL_FICHERO_DEL_TICKET = RAIZ / "backend" / "tests" / "test_el_dinero_de_las_ventas.py"


class TestDefecto12LaPruebaQueSoloCorreEnSQLite:
    """**Medido corriendo la suite contra PostgreSQL** (base propia, ver el comando del informe):

    ```
    tests/test_el_dinero_de_las_ventas.py -q -x
    ........F
    FAILED TestElDineroNoPierdeCentimos::test_el_importe_va_y_vuelve_de_la_base_sin_perder_ni_un_centimo
    E   assert engine.dialect.name == "sqlite", engine.dialect.name
    E   AssertionError: postgresql
    ```

    Ese test —«el importe va y vuelve de la base sin perder ni un céntimo», que es la promesa central del
    ticket— empieza **parándose** cuando el motor no es SQLite, así que **en el motor de producción no
    se comprueba**, y encima deja la suite en rojo por un motivo que no es el programa: el informe dice
    que las cuatro pruebas en rojo son las de recuentos de documentación y que «ninguna otra», y en
    PostgreSQL hay una quinta que es de este mismo fichero.

    Además, la mitad del test **sí valdría** en PostgreSQL (las líneas que comprueban que el importe
    vuelve igual por la API y que en la base está guardado como `"0.10"`); lo único que no vale es el
    `SELECT typeof(importe)`, que es sintaxis de SQLite. La receta del propio proyecto para eso está
    escrita: `tests/test_arranque_en_postgresql.py` **se salta diciendo por qué**, no falla. Y el
    `pytest.skip` no es un adorno: el mismo dato se puede comprobar en PostgreSQL
    (`pg_typeof`, o `information_schema.columns.data_type = 'character varying'`), que es donde el
    «texto decimal y no un número» importa de verdad.
    """

    def test_defecto_12_ninguna_prueba_del_ticket_se_para_por_el_motor(self):
        codigo = EL_FICHERO_DEL_TICKET.read_text(encoding="utf-8")
        paradas = [
            (numero, linea.strip())
            for numero, linea in enumerate(codigo.splitlines(), start=1)
            if re.search(r"assert\s+engine\.dialect\.name\s*==", linea)
        ]
        assert not paradas, (
            "hay una prueba del ticket que se para cuando el motor no es SQLite:\n  "
            + "\n  ".join(f"línea {numero}: {linea}" for numero, linea in paradas)
            + "\nEn PostgreSQL esa prueba sale en rojo (medido) y el viaje de ida y vuelta del importe "
            "por la base se queda sin comprobar en el motor de producción. O se comprueba también allí "
            "(lo que no vale es `typeof`, que es sintaxis de SQLite), o se salta con `pytest.skip` "
            "diciendo por qué, como hace test_arranque_en_postgresql.py."
        )
