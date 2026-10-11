"""La compra de punta a punta: proveedor, factura, recepción, lote, gasto y pagos (08/10/2026).

**Por qué existe.** El recorrido económico anterior acreditaba cifras **globales** -que el pendiente de la
explotación bajaba 663-, y eso **no** demuestra que una factura concreta haya quedado pagada: con reparto por
antigüedad el dinero puede haber ido a otras deudas. Aquí se monta **una compra identificable** y se comprueba
**por identificador**:

    proveedor -> factura 663 con lineas -> recepcion en las MISMAS unidades -> lote
              -> gasto vinculado a la factura -> pago de 200 aplicado A ESA deuda -> pago de 463

Y en cada paso se mira **su** fila, no el total: `pendiente 663 -> 463 -> 0`, **sus** aplicaciones de pago,
**su** saldo sin aplicar, y **las demas deudas sin cambios** (el resumen de la explotacion se contrasta
**ademas**, no en lugar de).

**A15, que ya estaba escrito en la casa** (`schemas.py:2604`): registrar la factura **no vuelve a meter la
mercancia**. Aquí se comprueba: las existencias suben **por la recepcion** y **no** por la factura.

Uso:  python scripts/comprobar_la_compra_de_punta_a_punta.py <direccion> <carpeta-de-capturas> <ruta-de-la-base>
"""

from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

DIRECCION = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8250"
CAPTURAS = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(".")
LA_BASE = sys.argv[3] if len(sys.argv) > 3 else ""

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import datos_representativos as datos  # noqa: E402

COMPROBACIONES = 0
FALLOS = 0
HALLAZGOS: list[str] = []

# Los numeros del caso, en un solo sitio.
TOTAL = 663.0
PRIMER_PAGO = 200.0
SEGUNDO_PAGO = 463.0
UNIDADES = [("Abono compuesto 15-15-15", "kg", 500.0, 2.0, 1000.0)]  # (nombre, unidad, cantidad, precio, importe)


def comprobar(bien: bool, que: str) -> bool:
    global COMPROBACIONES, FALLOS
    COMPROBACIONES += 1
    if bien:
        print(f"  [OK  ] {que}")
    else:
        FALLOS += 1
        print(f"  [FALLO] {que}")
    return bool(bien)


def hallazgo(texto: str) -> None:
    HALLAZGOS.append(texto)
    print(f"  [HALLAZGO] {texto}")


def _pedir(peticion: urllib.request.Request):
    """Devuelve (codigo, cuerpo). No lanza: interesa lo que contesta, incluido un rechazo."""
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            crudo = respuesta.read().decode("utf-8") or "{}"
            try:
                return respuesta.status, json.loads(crudo)
            except ValueError:
                return respuesta.status, {"crudo": crudo[:300]}
    except urllib.error.HTTPError as exc:
        crudo = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(crudo)
        except ValueError:
            return exc.code, {"crudo": crudo[:300]}


def get(camino: str, token: str):
    return _pedir(
        urllib.request.Request(f"{DIRECCION}{camino}", headers={"Authorization": f"Bearer {token}"})
    )


def post_json(camino: str, token: str, cuerpo: dict):
    return _pedir(
        urllib.request.Request(
            f"{DIRECCION}{camino}",
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="POST",
        )
    )


def post_form(camino: str, token: str, cuerpo: dict, fichero: tuple | None = None):
    """`multipart/form-data` con el JSON en el campo `datos`, que es como lo mandan las pantallas."""
    import httpx

    datos_del_formulario = {"datos": json.dumps(cuerpo)}
    if fichero is None:
        return httpx.post(
            f"{DIRECCION}{camino}", data=datos_del_formulario,
            headers={"Authorization": f"Bearer {token}"}, timeout=30,
        )
    nombre, contenido, tipo = fichero
    return httpx.post(
        f"{DIRECCION}{camino}", data=datos_del_formulario, files={"fichero": (nombre, contenido, tipo)},
        headers={"Authorization": f"Bearer {token}"}, timeout=30,
    )


def crear(camino: str, token: str, cuerpo: dict, fichero: tuple | None = None):
    """Crea **probando las dos formas** y diciendo cuál ha valido: así no se supone el formato.

    La casa tiene puertas que esperan `multipart` con el campo `datos` (facturas, gastos) y puertas que
    esperan **JSON** (recepciones). En vez de adivinarlo, se prueba `multipart` y, si contesta que falta
    `datos`, se prueba JSON. La que valga se dice en la salida.
    """
    respuesta = post_form(camino, token, cuerpo, fichero)
    if respuesta.status_code < 400:
        return respuesta.status_code, respuesta.json(), "multipart"
    if "datos" in str(respuesta.text):
        codigo, salida = post_json(camino, token, cuerpo)
        return codigo, salida, "json"
    try:
        return respuesta.status_code, respuesta.json(), "multipart"
    except ValueError:
        return respuesta.status_code, {"crudo": respuesta.text[:300]}, "multipart"


def put_json(camino: str, token: str, cuerpo: dict):
    """Corregir es un `PUT` con el **cuerpo entero**, igual que lo manda la pantalla."""
    return _pedir(
        urllib.request.Request(
            f"{DIRECCION}{camino}",
            data=json.dumps(cuerpo).encode("utf-8"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            method="PUT",
        )
    )


def las_existencias(token: str) -> dict:
    """{id_de_articulo: saldo}, leido de `articulos[].lotes[].saldo`, que es donde vive.

    La primera version suponia `existencias[].articulo_id/.saldo` y devolvia `{}` -medido-, que es
    exactamente como se cuelan las comprobaciones vacuas: `None -> None` y la luz verde. El saldo **se suma
    por LOTES**: un recorrido a ciegas que buscaba «el primer numero» devolvia `entradas` y parecia que el
    almacen no subia (500 quieto) mientras si subia a 1000.
    """
    _, suyo = get("/api/almacen/existencias", token)
    # **Las claves y las filas**, no el volcado entero: la respuesta trae también los **textos de la pantalla**
    # (`textos: {...}`), que ocupan el recorte y escondían justo lo que había que mirar -el saldo por lote-.
    if isinstance(suyo, dict):
        print(f"  (existencias: claves {sorted(suyo.keys())})")
        for uno in (suyo.get("articulos") or []):
            # Por **nombre**, no por el identificador: `articulo_id` es local de `main` y aqui no existe
            # (NameError, medido). El nombre del articulo es una constante del modulo y sirve para el volcado.
            if str(uno.get("nombre")) == UNIDADES[0][0] and (uno.get("lotes") or []):
                las_lotes = uno.get("lotes") or []
                print(f"    (mi articulo ({uno.get('articulo_id')}) tiene {len(las_lotes)} lote(s))")
                for lote in las_lotes:
                    numeros = {k: v for k, v in lote.items() if isinstance(v, (int, float, str))}
                    print(f"      (lote: {numeros})")
    else:
        print(f"  (existencias: {str(suyo)[:320]})")

    salida: dict = {}
    for uno in (suyo or {}).get("articulos") or []:
        su_id = uno.get("articulo_id")
        if su_id is None:
            continue
        total = 0.0
        for lote in uno.get("lotes") or []:
            try:
                total += float(lote.get("saldo") or 0)
            except (TypeError, ValueError):
                pass
        salida[su_id] = total
    if not salida:
        # **Que lo diga**: un diccionario vacio en silencio es una luz verde vacua esperando a pasar.
        claves = sorted(suyo.keys()) if isinstance(suyo, dict) else type(suyo).__name__
        print(f"  (OJO: no he sabido leer las existencias; la respuesta trae: {claves})")
    return salida


def el_rastro(entidad: str, entidad_id, accion: str | None = None) -> list[dict]:
    """Las entradas de auditoría de ese registro, **leidas de la base**, que es donde están.

    La API no expone el rastro, así que se lee de la base de la prueba (el tercer argumento). Se devuelve
    **la acción y la fecha**, no el volcado: lo que hay que comprobar es que la entrada existe y qué dice.
    """
    import sqlite3

    conexion = sqlite3.connect(f"file:{LA_BASE}?mode=ro", uri=True)
    conexion.row_factory = sqlite3.Row
    try:
        if accion is None:
            filas = conexion.execute(
                "select accion, datos from auditoria where entidad = ? and entidad_id = ?",
                (entidad, entidad_id),
            ).fetchall()
        else:
            filas = conexion.execute(
                "select accion, datos from auditoria where entidad = ? and entidad_id = ? and accion = ?",
                (entidad, entidad_id, accion),
            ).fetchall()
    finally:
        conexion.close()
    salida = []
    for fila in filas:
        try:
            sus_datos = json.loads(fila["datos"]) if fila["datos"] else {}
        except (TypeError, ValueError):
            sus_datos = {"crudo": str(fila["datos"])[:120]}
        salida.append({"accion": fila["accion"], "datos": sus_datos})
    return salida


def los_gastos(token: str) -> dict:
    _, suyos = get("/api/gastos", token)
    return suyos or {}


def el_por_pagar(token: str):
    """El resumen de la explotacion. `por_pagar` es un OBJETO con su importe (medido, no supuesto).

    Se usa **como contraste**, nunca como prueba: que el total baje 663 no dice cual factura se pago. La prueba
    es el pendiente de la factura, por su identificador.
    """
    suyo = (los_gastos(token) or {}).get("por_pagar")
    if isinstance(suyo, dict):
        suyo = suyo.get("importe")
    try:
        return float(suyo)
    except (TypeError, ValueError):
        return None


def el_de_id(suyos: dict, gasto_id: int) -> dict | None:
    """El gasto **por su identificador**, nunca por su concepto: el escenario tiene uno con el mismo texto."""
    for uno in (suyos or {}).get("gastos") or []:
        if uno.get("id") == gasto_id:
            return uno
    return None


def el_pendiente_de(suyos: dict, gasto_id: int):
    suyo = el_de_id(suyos, gasto_id)
    return None if suyo is None else float(suyo.get("pendiente") or 0)


def main() -> int:
    if not LA_BASE or LA_BASE.endswith("cuedigital.db"):
        print("=> falta la base temporal, o es la del agricultor: no se toca")
        return 1
    print(f"  (la base de la prueba no es la del agricultor: adelante)")

    volumen, escenario = datos._la_del_volumen(  # noqa: SLF001
        DIRECCION, f"compra{int(time.time())}", pathlib.Path(CAPTURAS), False
    )
    token = volumen.token
    print(f"  (la sesion: {volumen.nombre})")

    # ── 1. El proveedor y el producto ────────────────────────────────────────────────────────────────
    print("\n1) El proveedor y el producto")
    codigo, el_articulo, como = crear(
        "/api/almacen/articulos", token,
        {"nombre": "Abono compuesto 15-15-15", "categoria": "abono", "unidad": "kg"},
    )
    print(f"  (el articulo: {codigo} por {como}: {str(el_articulo)[:160]})")
    comprobar(codigo < 400 and isinstance(el_articulo, dict), "el articulo del abono se da de alta")
    articulo_id = (el_articulo or {}).get("id") or (((el_articulo or {}).get("articulo") or {}).get("id"))

    # ── 2. La factura de 663, con sus lineas ─────────────────────────────────────────────────────────
    print("\n2) La factura de 663 con sus lineas")
    numero = f"F-2026-{int(time.time()) % 10000:04d}"
    la_factura = {
        "fecha": "2026-10-05",
        "proveedor": "Suministros del Paramo, S.L.",
        "proveedor_nif": "B12345678",
        "numero_factura": numero,
        "base_imponible": 663.0,
        "cuota_iva": 0.0,
        "total": TOTAL,
        "leida_por": "a mano",
        "lineas": [
            {"descripcion": nombre, "cantidad": cantidad, "unidad": unidad, "precio": precio, "importe": importe}
            for (nombre, unidad, cantidad, precio, importe) in UNIDADES
        ],
    }
    codigo, factura, como = crear("/api/facturas", token, la_factura)
    print(f"  (la factura: {codigo} por {como}: {str(factura)[:200]})")
    comprobar(codigo < 400, f"la factura de {TOTAL:.0f} EUR entra con sus {len(UNIDADES)} linea(s)")
    factura_id = (factura or {}).get("id") or (((factura or {}).get("factura") or {}).get("id"))
    comprobar(bool(factura_id), f"y tiene identificador propio ({factura_id})")

    # ── 3. Las existencias ANTES de la recepcion (A15: la factura no mete mercancia) ─────────────────
    print("\n3) Las existencias, antes y despues de la recepcion")
    antes_de_recibir = las_existencias(token)
    saldo_antes = antes_de_recibir.get(articulo_id)
    print(f"  (existencias antes: {str(antes_de_recibir)[:200]})")
    print(f"  (saldo de mi articulo antes: {saldo_antes!r})")

    # ── 4. La recepcion, en las MISMAS unidades, y enganchada a la factura ───────────────────────────
    print("\n4) La recepcion de esos productos, en las mismas unidades")
    la_recepcion = {
        "fecha": "2026-10-05",
        "proveedor": "Suministros del Paramo, S.L.",
        "proveedor_nif": "B12345678",
        "numero_albaran": f"A-2026-{int(time.time()) % 10000:04d}",
        "factura_id": factura_id,
        "clave_de_reenvio": f"compra-{numero}",
        "lineas": [
            {"articulo_id": articulo_id, "nombre": nombre, "unidad": unidad, "cantidad": cantidad}
            for (nombre, unidad, cantidad, _precio, _importe) in UNIDADES
        ],
    }
    codigo, recepcion, como = crear("/api/almacen/recepciones", token, la_recepcion)
    print(f"  (la recepcion: {codigo} por {como}: {str(recepcion)[:240]})")
    comprobar(codigo < 400, "la recepcion de esos productos entra, con su lote")
    recepcion_id = (recepcion or {}).get("id") or (((recepcion or {}).get("recepcion") or {}).get("id"))

    despues_de_recibir = las_existencias(token)
    saldo_despues = despues_de_recibir.get(articulo_id)
    print(f"  (saldo de mi articulo despues: {saldo_despues!r})")
    try:
        subido = float(saldo_despues) - float(saldo_antes)
    except (TypeError, ValueError):
        subido = None
    comprobar(
        subido is not None and abs(subido - UNIDADES[0][2]) < 0.001,
        f"y las existencias suben **por la recepcion**, en las unidades pedidas ({saldo_antes!r} -> {saldo_despues!r})",
    )
    comprobar(
        recepcion_id is not None and str((recepcion or {}).get("factura_id")) == str(factura_id)
        or str(((recepcion or {}).get("recepcion") or {}).get("factura_id")) == str(factura_id),
        "y la recepcion queda **enganchada a la factura**",
    )

    # ── 5. El gasto, vinculado a la factura ──────────────────────────────────────────────────────────
    print("\n5) El gasto, vinculado a la factura")
    codigo, gasto, como = crear(
        "/api/gastos", token,
        {
            "concepto": f"Compra de abono, factura {numero}",
            "fecha": "2026-10-05",
            "vencimiento": "2026-11-05",
            "categoria": "abono",
            "proveedor": "Suministros del Paramo, S.L.",
            "proveedor_nif": "B12345678",
            "factura_id": factura_id,
            # **Los importes viajan como TEXTO** (medido: el gasto y el pago contestan 422 «Un importe no se
            # acepta como numero de…» si se mandan como numero; y el servidor los devuelve asi: '663.00').
            "base_imponible": f"{TOTAL:.2f}",
            "cuota_iva": "0.00",
            "total": f"{TOTAL:.2f}",
            "importe": f"{TOTAL:.2f}",
        },
    )
    print(f"  (el gasto: {codigo} por {como}: {str(gasto)[:240]})")
    comprobar(codigo < 400, "el gasto entra")
    gasto_id = (gasto or {}).get("id") or (((gasto or {}).get("gasto") or {}).get("id"))
    comprobar(bool(gasto_id), f"y tiene identificador propio ({gasto_id})")

    suyos = los_gastos(token)
    mio = el_de_id(suyos, gasto_id) or {}
    print(f"  (mi gasto, por identificador: {str(mio)[:260]})")
    comprobar(
        str(mio.get("factura_id")) == str(factura_id),
        f"y queda **vinculado a la factura** ({mio.get('factura_id')})",
    )
    pendiente_inicial = el_pendiente_de(suyos, gasto_id)
    comprobar(
        pendiente_inicial is not None and abs(pendiente_inicial - TOTAL) < 0.01,
        f"y su pendiente es el total de la factura ({pendiente_inicial!r})",
    )

    # Las **demas** deudas, congeladas: es lo que permite demostrar que el pago va a la mia.
    las_otras_antes = {
        uno.get("id"): uno.get("pendiente")
        for uno in (suyos or {}).get("gastos") or []
        if uno.get("id") != gasto_id
    }
    print(f"  (y hay {len(las_otras_antes)} deudas mas, que no se deben tocar)")
    resumen_antes = el_por_pagar(token)
    print(f"  (el resumen de la explotacion, antes de pagar: por pagar {resumen_antes!r})")

    # ── 6. El pago de 200, aplicado A ESA deuda ──────────────────────────────────────────────────────
    print(f"\n6) El pago de {PRIMER_PAGO:.0f}, aplicado a ESA deuda")
    codigo, pago, como = crear(
        "/api/gastos/pagos", token,
        {
            "importe": f"{PRIMER_PAGO:.2f}",
            "fecha": "2026-10-06",
            "proveedor": "Suministros del Paramo, S.L.",
            "forma": "transferencia",
            "clave_de_reenvio": f"pago-1-{numero}",
        },
    )
    print(f"  (el pago: {codigo} por {como}: {str(pago)[:200]})")
    comprobar(codigo < 400, f"el pago de {PRIMER_PAGO:.0f} EUR se apunta")
    pago_id = (pago or {}).get("id") or (((pago or {}).get("pago") or {}).get("id"))

    # **Aplicado EXPRESAMENTE a esa deuda**: se le dice al servidor **solo** ese gasto, en vez de dejarle
    # repartir por antiguedad entre todas. Es la diferencia entre acreditar esta factura y bajar un total.
    codigo, conciliado = post_json(
        f"/api/gastos/pagos/{pago_id}/conciliar", token,
        {"automatico": True, "gastos": [gasto_id], "aplicaciones": []},
    )[0:2]
    print(f"  (la conciliacion: {codigo}: {str(conciliado)[:240]})")
    comprobar(codigo < 400, "y se aplica **expresamente a esa deuda** (se le dice cual, no se le deja elegir)")

    suyos = los_gastos(token)
    pendiente_tras_200 = el_pendiente_de(suyos, gasto_id)
    print(f"  (el pendiente de MI factura: {pendiente_inicial!r} -> {pendiente_tras_200!r})")
    comprobar(
        pendiente_tras_200 is not None and abs((pendiente_inicial or 0) - pendiente_tras_200 - PRIMER_PAGO) < 0.01,
        f"y el pendiente de **esta** deuda baja {PRIMER_PAGO:.0f} ({pendiente_inicial!r} -> {pendiente_tras_200!r})",
    )
    las_otras_despues = {
        uno.get("id"): uno.get("pendiente")
        for uno in (suyos or {}).get("gastos") or []
        if uno.get("id") != gasto_id
    }
    # **Con sustancia**: si el pago no llego a crearse, que las demas deudas no se muevan **no dice nada** -es
    # una luz verde vacua, el defecto que el revisor me señalo en la entrega anterior-. Se exige que el pago
    # exista y que tenga aplicaciones **antes** de afirmar que lo demas sigue igual.
    comprobar(
        bool(pago_id)
        and pendiente_tras_200 is not None
        and abs((pendiente_inicial or 0) - pendiente_tras_200 - PRIMER_PAGO) < 0.01
        and las_otras_antes == las_otras_despues,
        f"y **las demas deudas no se mueven** ({len(las_otras_despues)} comprobadas, con el pago ya aplicado)",
    )

    # El resumen de la explotacion, **ademas**: contraste, no prueba.
    _, los_pagos = get("/api/gastos/pagos", token)
    mio_pago = next((uno for uno in (los_pagos or {}).get("pagos") or [] if uno.get("id") == pago_id), {})
    print(f"  (mi pago, por identificador: {str(mio_pago)[:240]})")
    aplicaciones = mio_pago.get("aplicaciones") or []
    comprobar(
        len(aplicaciones) >= 1 and all(str(uno.get("gasto_id")) == str(gasto_id) for uno in aplicaciones),
        f"y **sus** aplicaciones van a mi gasto ({len(aplicaciones)} aplicacion(es))",
    )
    comprobar(
        not (los_pagos or {}).get("sin_conciliar"),
        f"y no le queda saldo sin aplicar (sin_conciliar: {len((los_pagos or {}).get('sin_conciliar') or [])})",
    )

    # ── 7. El pago de 463, y la deuda a cero ─────────────────────────────────────────────────────────
    print(f"\n7) El pago de {SEGUNDO_PAGO:.0f}, y la deuda a cero")
    codigo, pago2, como = crear(
        "/api/gastos/pagos", token,
        {
            "importe": f"{SEGUNDO_PAGO:.2f}", "fecha": "2026-10-07",
            "proveedor": "Suministros del Paramo, S.L.", "forma": "transferencia",
            "clave_de_reenvio": f"pago-2-{numero}",
        },
    )
    pago2_id = (pago2 or {}).get("id") or (((pago2 or {}).get("pago") or {}).get("id"))
    comprobar(codigo < 400, f"el segundo pago de {SEGUNDO_PAGO:.0f} EUR se apunta")
    codigo = post_json(
        f"/api/gastos/pagos/{pago2_id}/conciliar", token,
        {"automatico": True, "gastos": [gasto_id], "aplicaciones": []},
    )[0]
    comprobar(codigo < 400, "y se aplica tambien expresamente a esa deuda")

    suyos = los_gastos(token)
    pendiente_final = el_pendiente_de(suyos, gasto_id)
    mio = el_de_id(suyos, gasto_id) or {}
    print(f"  (mi gasto, al final: {str(mio)[:260]})")
    comprobar(
        pendiente_final is not None and abs(pendiente_final) < 0.01,
        f"y **esta** factura queda pagada: pendiente {pendiente_inicial!r} -> {pendiente_tras_200!r} -> {pendiente_final!r}",
    )
    comprobar(
        str(mio.get("estado")) in ("pagado", "pago"),
        f"y su estado lo dice ({mio.get('estado')!r})",
    )

    # **Y el resumen de la explotacion, como CONTRASTE** (lo pide el encargo, y se hace en su sitio): el total
    # tiene que haber bajado **exactamente** lo que se pago. Pero esto **no** acredita cual factura se pago:
    # eso lo dice el pendiente de arriba, por su identificador. Si los dos numeros no cuadran, hay algo que
    # explicar, y por eso se comprueban los dos.
    resumen_despues = el_por_pagar(token)
    print(f"  (y despues de pagar: por pagar {resumen_despues!r})")
    comprobar(
        resumen_antes is not None
        and resumen_despues is not None
        and abs((resumen_antes - resumen_despues) - TOTAL) < 0.01,
        f"y el resumen de la explotacion baja lo pagado, {TOTAL:.0f} ({resumen_antes!r} -> {resumen_despues!r})",
    )

    # ── 8. A15: registrar la factura no vuelve a meter mercancia ─────────────────────────────────────
    print("\n8) A15: la factura no vuelve a meter la mercancia")
    las_de_ahora = las_existencias(token)
    print(f"  (saldo de mi articulo ahora: {las_de_ahora.get(articulo_id)!r})")
    comprobar(
        str(las_de_ahora.get(articulo_id)) == str(saldo_despues),
        f"y el almacen no ha cambiado desde la recepcion ({saldo_despues!r} -> {las_de_ahora.get(articulo_id)!r})",
    )

    # ── 9. Recepcion parcial, y factura POSTERIOR al albaran ─────────────────────────────────────────
    print("\n9) Recepcion parcial, y la factura despues del albaran")
    # El orden dificil: llega mercancia en dos veces **sin factura**, y la factura aparece despues. Es el caso
    # que el encargo pide y el que mi entrega anterior no acreditaba -una compra unica con sus vinculos-.
    saldo_antes_de_las_dos = (las_existencias(token).get(articulo_id))
    print(f"  (saldo antes de las dos entregas: {saldo_antes_de_las_dos!r})")

    las_parciales = []
    for cuantas in (300.0, 200.0):
        codigo, suya, como = crear(
            "/api/almacen/recepciones", token,
            {
                "fecha": "2026-10-08",
                "proveedor": "Suministros del Paramo, S.L.",
                "proveedor_nif": "B12345678",
                "numero_albaran": f"A-parcial-{int(cuantas)}-{int(time.time()) % 10000:04d}",
                "clave_de_reenvio": f"parcial-{int(cuantas)}-{numero}",
                "lineas": [
                    {"articulo_id": articulo_id, "nombre": UNIDADES[0][0], "unidad": UNIDADES[0][1], "cantidad": cuantas}
                ],
            },
        )
        suyo = (suya or {}).get("recepcion") or suya or {}
        print(f"  (recepcion parcial de {cuantas:.0f}: {codigo} por {como}: factura_id={suyo.get('factura_id')!r})")
        comprobar(codigo < 400, f"la entrega parcial de {cuantas:.0f} se apunta **sin factura**")
        comprobar(
            not suyo.get("factura_id"),
            f"y entra **sin factura** -la factura vendra despues- (factura_id: {suyo.get('factura_id')!r})",
        )
        las_parciales.append(suyo.get("id"))

    saldo_tras_las_dos = las_existencias(token).get(articulo_id)
    print(f"  (saldo tras las dos entregas: {saldo_tras_las_dos!r})")
    try:
        subido_parcial = float(saldo_tras_las_dos) - float(saldo_antes_de_las_dos)
    except (TypeError, ValueError):
        subido_parcial = None
    comprobar(
        subido_parcial is not None and abs(subido_parcial - 500.0) < 0.001,
        f"y las dos entregas suman lo suyo, **sin factura ninguna** ({saldo_antes_de_las_dos!r} -> {saldo_tras_las_dos!r})",
    )

    # Y ahora **la factura, despues**: se crea y se engancha por su propia puerta.
    codigo, factura2, como = crear(
        "/api/facturas", token,
        {
            "fecha": "2026-10-09",
            "proveedor": "Suministros del Paramo, S.L.",
            "proveedor_nif": "B12345678",
            "numero_factura": f"F-2026-post-{int(time.time()) % 10000:04d}",
            "base_imponible": 663.0,
            "cuota_iva": 0.0,
            "total": TOTAL,
            "leida_por": "a mano",
            "lineas": [
                {"descripcion": UNIDADES[0][0], "cantidad": 500.0, "unidad": UNIDADES[0][1], "precio": 2.0, "importe": 1000.0}
            ],
        },
    )
    factura2_id = (factura2 or {}).get("id") or ((factura2 or {}).get("factura") or {}).get("id")
    print(f"  (la factura posterior: {codigo} por {como}: id {factura2_id})")
    comprobar(codigo < 400 and bool(factura2_id), f"y la factura de despues entra ({factura2_id})")

    saldo_antes_de_enganchar = las_existencias(token).get(articulo_id)
    codigo, enganchada, como = crear(
        f"/api/almacen/recepciones/{las_parciales[0]}/factura", token, {"factura_id": factura2_id}
    )
    print(f"  (el enganche: {codigo} por {como}: {str(enganchada)[:200]})")
    suya = (enganchada or {}).get("recepcion") or enganchada or {}
    comprobar(
        codigo < 400 and str(suya.get("factura_id")) == str(factura2_id),
        f"y el albaran se engancha a la factura **por su puerta**, despues ({suya.get('factura_id')!r})",
    )
    saldo_tras_enganchar = las_existencias(token).get(articulo_id)
    print(f"  (saldo antes/despues de enganchar la factura: {saldo_antes_de_enganchar!r} -> {saldo_tras_enganchar!r})")
    comprobar(
        str(saldo_antes_de_enganchar) == str(saldo_tras_enganchar) and saldo_tras_enganchar is not None,
        "y **enganchar la factura no mete ni un kilo** (A15, con el saldo ya conocido)",
    )

    # ── 10. Corregir la factura: el rastro, los enlaces y el almacen quieto ───────────────────────────
    print("\n10) Corregir la factura: queda el rastro y no se mueve el almacen")
    # **Corregir es cambiar lo que decia el papel, y eso no mueve mercancia**: la factura no mete ni saca
    # nada del almacen (A15). Lo que si tiene que quedar es **el rastro** de que se corrigio, y **los
    # enlaces** que ya tenia (los albaranes que apuntan a ella) no pueden perderse al corregirla.
    saldo_antes_de_corregir = las_existencias(token).get(articulo_id)
    codigo, corregida = put_json(
        f"/api/facturas/{factura2_id}", token,
        {
            "fecha": "2026-10-09",
            "proveedor": "Suministros del Paramo, S.L.",
            "proveedor_nif": "B12345678",
            "numero_factura": f"F-2026-post-{int(time.time()) % 10000:04d}",
            "base_imponible": 663.0,
            "cuota_iva": 0.0,
            "total": TOTAL,
            "leida_por": "a mano",
            "lineas": [
                # Se cambia **la descripcion de la linea**: es una correccion de verdad y no toca el dinero,
                # asi que si algo se mueve tiene que ser por otro motivo y hay que verlo.
                {"descripcion": f"{UNIDADES[0][0]} (corregido)", "cantidad": 500.0,
                 "unidad": UNIDADES[0][1], "precio": 2.0, "importe": 1000.0}
            ],
        },
    )
    print(f"  (la correccion: {codigo} por PUT: total {str((corregida or {}).get('total'))!r})")
    comprobar(codigo < 400, f"la factura se puede corregir ({codigo})")

    rastro = el_rastro("factura", factura2_id, "corregir_lineas")
    print(f"  (entradas de auditoria 'corregir_lineas' de ESA factura: {len(rastro)})")
    comprobar(len(rastro) >= 1, f"y queda el rastro de la correccion en la auditoria ({len(rastro)} entrada/s)")

    saldo_tras_corregir = las_existencias(token).get(articulo_id)
    print(f"  (saldo antes/despues de corregir la factura: {saldo_antes_de_corregir!r} -> {saldo_tras_corregir!r})")
    comprobar(
        str(saldo_antes_de_corregir) == str(saldo_tras_corregir) and saldo_tras_corregir is not None,
        "y corregir la factura **no mueve el almacen** (A15 otra vez, por el otro camino)",
    )

    # Los enlaces: el albaran parcial sigue apuntando a la factura que se corrigio.
    _, las_recepciones = get("/api/almacen/recepciones", token)
    la_lista = las_recepciones if isinstance(las_recepciones, list) else (
        (las_recepciones or {}).get("recepciones") or []
    )
    enlazadas = [
        uno for uno in la_lista
        if str(uno.get("id")) == str(las_parciales[0]) and str(uno.get("factura_id")) == str(factura2_id)
    ]
    print(f"  (albaranes que siguen enganchados a la factura corregida: {len(enlazadas)})")
    comprobar(len(enlazadas) == 1, "y el albaran sigue enganchado a la factura, **despues de corregirla**")

    # ── 11. El pago agrupado: un dinero que salda DOS facturas ────────────────────────────────────────
    print("\n11) El pago agrupado: un dinero, dos facturas")
    # Hasta aqui los pagos iban **uno a una deuda**. Lo que falta del encargo es el caso normal de una
    # transferencia: **un solo dinero que paga varias facturas a la vez**, repartido por antiguedad, y sin
    # perder un centimo por el camino ni tocar las deudas que no son.
    las_dos_deudas = []
    for indice, importe in enumerate(("100.00", "250.00"), start=1):
        codigo, suyo, como = crear(
            "/api/gastos", token,
            {
                "concepto": f"Compra agrupada {indice}",
                "importe": importe,
                "fecha": f"2026-10-0{indice}",
                "categoria": "abono",
                "proveedor": "Suministros del Paramo, S.L.",
                "factura_id": factura2_id,
            },
        )
        su_id = (suyo or {}).get("id") or (((suyo or {}).get("gasto") or {}).get("id"))
        print(f"  (la deuda {indice} de {importe}: {codigo} por {como}: id {su_id})")
        comprobar(codigo < 400 and bool(su_id), f"la deuda {indice} ({importe} EUR) se apunta")
        las_dos_deudas.append(su_id)

    # Las demas deudas, para el contraste: no se pueden mover.
    antes = los_gastos(token)
    otras_antes = {
        uno.get("id"): uno.get("pendiente")
        for uno in (antes.get("gastos") or [])
        if uno.get("id") not in las_dos_deudas
    }

    codigo, agrupado, como = crear(
        "/api/gastos/pagos", token,
        {
            "importe": "350.00", "fecha": "2026-10-09",
            "proveedor": "Suministros del Paramo, S.L.", "forma": "transferencia",
            "clave_de_reenvio": f"pago-agrupado-{numero}",
        },
    )
    agrupado_id = (agrupado or {}).get("id") or (((agrupado or {}).get("pago") or {}).get("id"))
    print(f"  (el pago unico de 350: {codigo} por {como}: id {agrupado_id})")
    comprobar(codigo < 400 and bool(agrupado_id), "un solo pago de 350 EUR para las dos deudas")

    codigo, conciliado = post_json(
        f"/api/gastos/pagos/{agrupado_id}/conciliar", token,
        {"automatico": True, "gastos": las_dos_deudas, "aplicaciones": []},
    )
    print(f"  (el reparto: {codigo} por JSON)")
    comprobar(codigo < 400, "y se reparte entre **las dos**, por antiguedad")

    despues = los_gastos(token)
    pendientes = [el_pendiente_de(despues, su_id) for su_id in las_dos_deudas]
    print(f"  (pendiente de las dos deudas, por su id: {pendientes})")
    comprobar(
        all(uno is not None and abs(uno) < 0.01 for uno in pendientes),
        f"y **las dos** quedan saldadas, cada una por su identificador ({pendientes})",
    )

    aplicaciones = ((conciliado or {}).get("pago") or {}).get("aplicaciones") or (
        (conciliado or {}).get("aplicaciones") or []
    )
    aplicadas = sum(
        float(uno.get("importe") or 0) for uno in aplicaciones if isinstance(uno, dict)
    )
    print(f"  (aplicaciones del pago: {len(aplicaciones)}; suman {aplicadas!r} de 350)")
    comprobar(len(aplicaciones) == 2, f"y el pago dice **contra que dos** fue ({len(aplicaciones)} aplicacion/es)")
    comprobar(
        abs(aplicadas - 350.0) < 0.01,
        f"y no se pierde un centimo: lo aplicado es el dinero entero ({aplicadas!r} de 350.00)",
    )

    otras_despues = {
        uno.get("id"): uno.get("pendiente")
        for uno in (despues.get("gastos") or [])
        if uno.get("id") not in las_dos_deudas
    }
    comprobar(
        otras_antes == otras_despues,
        f"y **las demas deudas no se mueven** ({len(otras_antes)} comprobadas, una a una)",
    )

    # ── 12. Anular con auditoria: la mercancia y el papel son cosas distintas ─────────────────────────
    print("\n12) Anular: la mercancia y el papel son dos cosas distintas")
    # Lo que hay que acreditar aqui es la **separacion**: anular el albaran devuelve la mercancia (el
    # almacen baja lo que metio) **sin tocar la factura**; y anular la factura **no vacia el almacen**,
    # porque la factura no metio nada (A15). Y las dos anulaciones dejan su rastro.
    saldo_antes_de_anular_el_albaran = las_existencias(token).get(articulo_id)
    codigo, anulada_recepcion, como = crear(
        f"/api/almacen/recepciones/{las_parciales[0]}/anular", token,
        {"motivo": "venia de menos y se apunto de mas"},
    )
    print(f"  (anular el albaran de 300: {codigo} por {como})")
    comprobar(codigo < 400, "el albaran se puede anular con su motivo")

    saldo_tras_anular_el_albaran = las_existencias(token).get(articulo_id)
    try:
        bajado = float(saldo_antes_de_anular_el_albaran) - float(saldo_tras_anular_el_albaran)
    except (TypeError, ValueError):
        bajado = None
    print(f"  (saldo antes/despues de anular el albaran: {saldo_antes_de_anular_el_albaran!r} -> "
          f"{saldo_tras_anular_el_albaran!r}; ha bajado {bajado!r})")
    comprobar(
        bajado is not None and abs(bajado - 300.0) < 0.001,
        f"y anular el albaran devuelve **exactamente lo que metio** ({bajado!r} de 300)",
    )

    rastro = el_rastro("recepcion", las_parciales[0], "anular")
    print(f"  (entradas de auditoria de esa anulacion: {len(rastro)})")
    comprobar(len(rastro) >= 1, f"y la anulacion del albaran deja su rastro ({len(rastro)} entrada/s)")

    _, la_factura_tras_anular_el_albaran = get(f"/api/facturas/{factura2_id}", token)
    comprobar(
        str((la_factura_tras_anular_el_albaran or {}).get("total")) == str(TOTAL),
        "y **la factura sigue con su total**: anular el albaran no toca el papel",
    )

    saldo_antes_de_anular_la_factura = las_existencias(token).get(articulo_id)
    codigo, anulada_factura, como = crear(
        f"/api/facturas/{factura2_id}/anular", token,
        {"motivo": "el proveedor la rectifico"},
    )
    print(f"  (anular la factura: {codigo} por {como})")
    comprobar(codigo < 400, "y la factura se puede anular con su motivo")

    saldo_tras_anular_la_factura = las_existencias(token).get(articulo_id)
    print(f"  (saldo antes/despues de anular la factura: {saldo_antes_de_anular_la_factura!r} -> "
          f"{saldo_tras_anular_la_factura!r})")
    comprobar(
        str(saldo_antes_de_anular_la_factura) == str(saldo_tras_anular_la_factura)
        and saldo_tras_anular_la_factura is not None,
        "y **anular la factura no vacia el almacen**: no fue la factura la que metio la mercancia",
    )

    rastro = el_rastro("factura", factura2_id, "anular_factura")
    print(f"  (entradas de auditoria de la anulacion de la factura: {len(rastro)})")
    comprobar(len(rastro) >= 1, f"y la anulacion de la factura tambien deja su rastro ({len(rastro)} entrada/s)")

    # ── Resumen ──────────────────────────────────────────────────────────────────────────────────────
    print(f"\nComprobaciones: {COMPROBACIONES}   Fallos: {FALLOS}   Hallazgos: {len(HALLAZGOS)}")
    for uno in HALLAZGOS:
        print(f"  [HALLAZGO] {uno}")
    return 0 if FALLOS == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
