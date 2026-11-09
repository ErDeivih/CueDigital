"""Qué rutas se sirven **sin pedir sesión**, y por qué cada una.

POR QUÉ EXISTE ESTE FICHERO (03/10/2026)
========================================

En este programa hay dos maneras de que una ruta se sirva sin sesión, y **ninguna de las dos se ve
en una prueba que pasa**:

* que se escriba **a propósito** y con motivo (la pantalla de entrar tiene que poder entrar);
* que se escriba **sin darse cuenta** —se olvida el `UsuarioActual` en la firma, o se copia una
  ruta de al lado— y entonces queda abierta **para siempre y sin que nadie lo diga**.

La segunda pasó: la revisión ruta por ruta de T01 encontró **26 rutas sin sesión**, de las cuales
**cuatro «deberían pedir sesión»** (`docs/T01_REVISION_RUTAS_SIN_SESION.md`, §3.17 a §3.20) y
**siete más llamaban a servicios de fuera sin ningún límite** (§5.1 y §5.2). Eso se escribió en un
documento y ahí se quedó: **seis semanas después seguía igual**, porque un documento no se pone
rojo. Y en el mismo sitio se descubrió lo contrario: `GET /api/sigpac/estado`, que es público
porque no lleva datos de nadie, devolvía además **la ruta absoluta de una carpeta del servidor**
(`sigpac.py`, `"ruta": str(RUTA_DATOS)`) para que cualquiera supiera dónde están los datos.

Este fichero convierte ese documento en una prueba. **No dice que una ruta pública esté mal**:
dice que **toda ruta pública tiene que estar escrita aquí, con su motivo**, y que ninguna otra
puede aparecer sin que alguien lo vea.

CÓMO LO MIRA, Y POR QUÉ ASÍ
==========================

**Leyendo el árbol de dependencias de la aplicación, sin hacer ni una sola petición.** Se recorre
lo que la aplicación publica y, de cada ruta, se mira si en su cadena de dependencias está
`deps.usuario_actual` (o `deps.explotacion_actual`, que lo llama). Es lo que de verdad decide si
hay que entrar.

Y se hace así, y no pidiendo las rutas una por una, por dos motivos que no son teóricos:

1. **Pedirlas tiene efectos.** Entre las rutas sin sesión están `POST /api/cuenta/registro`, que
   **crea datos**, y las del SIGPAC y el mapa, que **salen a internet** (hasta 26 llamadas al FEGA
   por una sola petición). Una prueba que preguntara «¿me dejas?» a todas las rutas, además de no
   probar nada, se pasaría el día creando cuentas y llamando a servicios públicos.
2. **Un 422 no distingue nada.** Si se pidiera una ruta sin cuerpo, la respuesta podría ser un
   error de validación en vez de un 401, y «no me has dejado» se confundiría con «me lo has pedido
   mal». El árbol de dependencias no tiene esa ambigüedad.

Lo que sí se pide de verdad —seis rutas, con su cuerpo y con su vale— está al final del fichero,
con **su caso de control al lado**: primero se comprueba que con vale contestan 200 (es decir, que
lo que se manda es correcto) y después que sin vale contestan 401. Si el cuerpo no valiera, la
primera mitad lo diría, y el 401 de la segunda no podría venir de otra cosa.

LO QUE ESTE FICHERO **NO** HACE, Y QUEDA APUNTADO
=================================================

Lo que falta de T01 sigue faltando, y se dice aquí para que no se lea como hecho:

* **El límite de peticiones** (§5.2: «¿Hay algún límite? **No hay ninguno**»). Es lo que de verdad
  protege a las rutas que salen a internet, y incluidas las que ya piden sesión: un límite por
  cuenta es mejor que un límite por dirección IP. Va después de cerrar las que se podían cerrar.
* **`GET /api/mapa/imagen` no puede pedir sesión** tal y como está la pantalla: se pide con un
  `<img src>` y un `<img>` no manda cabeceras. Para cerrarla hay que cambiar antes la pantalla a
  `fetch` + memoria, y su caché **se vacía entera al llenarse**, cosa que desde fuera se puede
  provocar (§3.15).
* **`GET /api/iuws/version?llamar=1`** sale a la Junta sin identificarse: hasta dos llamadas de
  15 s por petición (§3.21).
* **`GET /api/zonas-vulnerables/estado`** recarga el catálogo oficial en **cada** petición (§3.14).
* Y las cuatro que sí se han cerrado hoy quedan probadas aquí abajo, no solo escritas.
"""

from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

from app import deps

# --------------------------------------------------------------------------
# Las rutas que se sirven sin sesión, una por una y con su motivo
# --------------------------------------------------------------------------
#
# **Añadir una ruta aquí es una decisión, no un trámite**: si no se puede escribir el motivo en una
# frase, probablemente la ruta no tenga que ser pública. La prueba comprueba que el motivo está
# escrito, y comprueba que **no hay ninguna otra** ruta sin sesión fuera de esta lista.
RUTAS_PUBLICAS_DECLARADAS: dict[tuple[str, str], str] = {
    ("GET", "/health"): (
        "Un sistema de vigilancia tiene que poder preguntar si el programa está vivo, y la "
        "respuesta no dice nada de nadie."
    ),
    ("GET", "/api/normativa"): (
        "**La normativa** (07/10/2026): las diez reglas de la matriz, iguales para todos los agricultores, sin "
        "un solo dato de nadie. Es el vocabulario de esa pantalla, como `/api/interfaz` es el de las demas: la "
        "pantalla las necesita antes de saber de quien es la finca, y no hay nada que proteger."
    ),
    ("GET", "/api"): (
        "La portada de la API: dice qué es el programa y por dónde se empieza. No lleva datos."
    ),
    ("POST", "/api/cuenta/registro"): (
        "Hay que poder darse de alta sin tener cuenta. **Es la única ruta sin sesión de toda la API "
        "que escribe en la base de datos** (T01 §3.10), y por eso es la que más necesita un límite "
        "de altas por dirección y por tiempo: hoy no tiene ninguno."
    ),
    ("POST", "/api/cuenta/entrar"): (
        "Hay que poder entrar sin tener cuenta. Necesita límite de intentos por cuenta y por "
        "dirección, con retardo o bloqueo, y apuntar los intentos fallidos (T01 §3.11)."
    ),
    ("GET", "/api/cuenta/certificado/estado"): (
        "La pantalla de entrar pregunta si el navegador trae certificado **antes** de entrar: sin "
        "esto no sabría si enseñar el botón."
    ),
    ("POST", "/api/cuenta/entrar-con-certificado"): (
        "Es la forma de entrar con certificado: sin sesión por definición. El NIF lo pone el "
        "servidor web que valida el certificado."
    ),
    ("GET", "/api/municipios"): (
        "La lista oficial de municipios del INE (2.248): la pantalla la necesita para dar de alta "
        "la cuenta y una tierra. No dice nada de ninguna finca."
    ),
    ("GET", "/api/interfaz"): (
        "Los textos de la pantalla que hay que enseñar **antes** de entrar: la pantalla de entrar "
        "es parte de la aplicación y sus palabras vienen de aquí."
    ),
    ("GET", "/api/ayuda"): "Los textos de ayuda: son los mismos para todo el mundo.",
    ("GET", "/api/ayuda/{campo}"): "Lo mismo, campo a campo: qué quiere decir cada dato.",
    ("GET", "/api/cuaderno-cyl/estado"): (
        "Dice si están los ficheros del cuaderno de la Junta. Sirve para explicar cómo importarlo "
        "y no lleva datos de la finca."
    ),
    ("GET", "/api/cuaderno-cyl/hojas"): (
        "El catálogo de hojas del cuaderno de la Junta: es el documento oficial, igual para todos."
    ),
    ("GET", "/api/mapa/estado"): (
        "Si hay capas de mapa configuradas y cuáles. No lleva datos de ninguna finca. **Se puede "
        "cerrar**: lo marcó como público el inventario de T01 y nadie lo ha necesitado desde "
        "fuera; queda apuntado."
    ),
    ("GET", "/api/mapa/imagen"): (
        "**No puede pedir sesión**: la pantalla la pide con un `<img src>` (`app.js:6590`) y un "
        "`<img>` no manda cabeceras. Necesita un límite por dirección y una caché que no se pueda "
        "vaciar desde fuera (T01 §3.15)."
    ),
    ("GET", "/api/sigpac/estado"): (
        "Qué datos oficiales del SIGPAC hay descargados, para poder decir «traer los datos». "
        "**Desde el 03/10/2026 ya no dice la ruta de la carpeta del servidor**, que era lo que "
        "este mismo inventario pidió quitar (T01 §3.13)."
    ),
    ("GET", "/api/zonas-vulnerables/estado"): (
        "Si está cargado el listado oficial de zonas vulnerables a los nitratos. Recarga el "
        "catálogo en cada petición: necesita límite o caché (T01 §3.14)."
    ),
    ("GET", "/api/maquinaria/que-falta"): (
        "«Lo que el programa todavía no sabe calcular» de la maquinaria: es la misma lista para "
        "todo el mundo y la pantalla de ayuda la enseña sin abrir ninguna máquina (T14)."
    ),
    ("GET", "/api/gastos/que-falta"): (
        "Lo mismo para las cuentas (T13, 05/10/2026): **la misma lista para todo el mundo**, porque "
        "es lo que el programa todavía no calcula (la amortización, el extracto del banco y el "
        "resumen del IVA) con lo que es y de quién depende. No lleva ni un dato de ninguna finca: la "
        "respuesta es `gastos.QUE_FALTA`, una constante del módulo."
    ),
    ("GET", "/api/trabajos/que-falta"): (
        "Y lo mismo para los trabajos (T15, 05/10/2026): lo que el programa no sabe hacer de un "
        "trabajo (la lluvia no acredita nascencia, la nascencia solo la dice quien la ha visto), lo "
        "que le falta al módulo para funcionar entero, y sus listas cerradas (los estados, los tipos "
        "y los aperos). **Ni un dato de ninguna finca**: todo sale de constantes de `trabajos.py` y "
        "`trabajos_api.py`."
    ),
    ("GET", "/api/iuws/version"): (
        "No es una ruta para personas: dice qué versión del interfaz de la Junta está configurada "
        "y la usa el técnico de la integración. **`?llamar=1` sale a la Junta sin identificarse** "
        "(hasta 2 llamadas de 15 s por petición): necesita vale o límite (T01 §3.21)."
    ),
    ("GET", "/api/iuws/comprobar-de-verdad"): (
        "La comprobación del técnico contra la Junta: es una herramienta de integración y no "
        "guarda nada de nadie. **Sale a la Junta al llamarla**, así que necesita vale o límite "
        "como las demás (T01 §3.22)."
    ),
    ("POST", "/api/iuws/leer-respuesta"): (
        "Lee una respuesta de la Junta que se pega a mano, para escribir a soporte. No guarda nada."
    ),
    ("GET", "/api/iuws/mensajes"): (
        "El catálogo de mensajes de error de la Junta, con su significado: es documentación."
    ),
    ("POST", "/api/observabilidad/pantalla"): (
        "**El aviso de qué pantalla se ha abierto** (09/11/2026), que manda la pantalla nueva al "
        "cambiar de vista. **No puede pedir sesión**: se manda con `sendBeacon`, que no permite "
        "cabeceras, y puede llegar desde la pantalla de entrar, antes de tener vale. Tampoco "
        "lleva ni un dato del agricultor: solo el nombre de la vista, y lo que no vale se "
        "descarta. Un aviso roto contesta siempre 204, nunca un 5xx."
    ),
    ("GET", "/api/observabilidad/resumen"): (
        "**El resumen de lo medido** (09/11/2026), para quien mantiene el programa. No se protege "
        "con sesión sino con la cabecera `X-Observabilidad`, comparada en tiempo constante con "
        "`CUEDIGITAL_OBSERVABILIDAD_TOKEN`: **sin token configurado contesta 404** (la herramienta "
        "no existe para nadie) y con el token mal, 403. No lleva datos de ninguna finca ni de "
        "ninguna cuenta: contadores por pantalla, plantillas de ruta y el embudo con fincas "
        "distintas por etapa."
    ),
}


# --------------------------------------------------------------------------
# Leer el árbol de la aplicación sin hacer ninguna petición
# --------------------------------------------------------------------------


def _funciones_de_la_cadena(dependencia, vistos: set | None = None) -> set:
    """Todas las funciones de una cadena de dependencias, sin repetir."""
    if vistos is None:
        vistos = set()
    funcion = getattr(dependencia, "call", None)
    if funcion is not None:
        vistos.add(funcion)
    for sub in dependencia.dependencies:
        _funciones_de_la_cadena(sub, vistos)
    return vistos


def _pide_sesion(ruta: APIRoute) -> bool:
    """Si para atender esta ruta hay que entrar.

    `usuario_actual` es la puerta; `explotacion_actual` la llama, así que sirve cualquiera de las
    dos. Se buscan las dos **por su función**, no por el nombre del parámetro: así da igual cómo
    se llame el argumento en la firma.
    """
    suyas = _funciones_de_la_cadena(ruta.dependant)
    return bool(suyas & {deps.usuario_actual, deps.explotacion_actual})


def _rutas_publicadas(objeto, prefijo: str = "") -> list[tuple[str, APIRoute]]:
    """Todas las rutas de la aplicación, con su camino completo.

    **Por qué no vale `app.routes` a secas.** FastAPI envuelve los routers incluidos
    (`_IncludedRouter`) y ahí dentro no se ven las rutas hasta que se pide una: en `app.routes`
    hay 32 objetos y **solo 2 son rutas de verdad**, cuando la aplicación publica 247. Por eso se
    entra en el router original de cada envoltorio. Y por eso la primera prueba del fichero
    comprueba que este recorrido ve **exactamente** lo mismo que el esquema publicado: si algún
    día una versión nueva de FastAPI cambia esa manera de envolver, esa prueba se pone roja con un
    mensaje que dice qué hacer, en vez de dejar este fichero mirando al aire y en verde.
    """
    salida: list[tuple[str, APIRoute]] = []
    for elemento in getattr(objeto, "routes", []):
        if isinstance(elemento, APIRoute):
            salida.append((prefijo + elemento.path, elemento))
            continue
        contexto = getattr(elemento, "include_context", None)
        suyo = getattr(contexto, "prefix", "") or getattr(elemento, "prefix", "") or ""
        interno = getattr(elemento, "original_router", None) or elemento
        if hasattr(interno, "routes"):
            salida.extend(_rutas_publicadas(interno, prefijo + suyo))
    return salida


def _pares_publicados() -> set[tuple[str, str]]:
    """Los pares «método + camino» que la aplicación publica, según su propio esquema."""
    from app.main import app

    return {
        (metodo.upper(), camino)
        for camino, metodos in app.openapi()["paths"].items()
        for metodo in metodos
        if metodo.upper() not in ("HEAD", "OPTIONS")
    }


def _pares_con_sesion() -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """`(con sesión, sin sesión)` leídos del árbol de dependencias."""
    from app.main import app

    con_sesion: set[tuple[str, str]] = set()
    sin_sesion: set[tuple[str, str]] = set()
    for camino, ruta in _rutas_publicadas(app):
        for metodo in ruta.methods:
            if metodo in ("HEAD", "OPTIONS"):
                continue
            (con_sesion if _pide_sesion(ruta) else sin_sesion).add((metodo, camino))
    return con_sesion, sin_sesion


# --------------------------------------------------------------------------
# 1. El recorrido ve lo que hay que ver
# --------------------------------------------------------------------------


def test_el_recorrido_ve_todas_las_rutas_de_la_aplicacion():
    """**La prueba que mantiene viva a las demás.**

    Si el recorrido del árbol dejara de ver rutas —porque una versión nueva de FastAPI envuelve
    los routers de otra manera—, la prueba de abajo compararía la lista declarada contra una lista
    incompleta y **diría que todo está bien**. Esto lo impide: el recorrido tiene que ver
    **exactamente** los mismos pares «método + camino» que la aplicación publica.
    """
    con_sesion, sin_sesion = _pares_con_sesion()
    vistas = con_sesion | sin_sesion
    publicadas = _pares_publicados()

    assert vistas == publicadas, (
        "el recorrido del árbol de dependencias no ve lo mismo que la aplicación publica.\n"
        f"  publica y no se ve ({len(publicadas - vistas)}): "
        f"{sorted(publicadas - vistas)[:6]}\n"
        f"  se ve y no se publica ({len(vistas - publicadas)}): "
        f"{sorted(vistas - publicadas)[:6]}\n"
        "  Si esto falla por una versión nueva de FastAPI, hay que arreglar `_rutas_publicadas`: "
        "mientras no se arregle, esta prueba no puede vigilar nada."
    )


# --------------------------------------------------------------------------
# 2. Ninguna ruta se sirve sin sesión sin estar declarada
# --------------------------------------------------------------------------


def test_ninguna_ruta_sin_sesion_se_queda_sin_declarar():
    """El guardián: **toda** ruta pública está en la lista, con su motivo, o esto se pone rojo.

    Un `UsuarioActual` que se olvida en la firma no rompe nada, no cambia ninguna respuesta que
    las pruebas miren y no se nota nunca. Esta es la única prueba del proyecto que lo nota.
    """
    _, sin_sesion = _pares_con_sesion()
    declaradas = set(RUTAS_PUBLICAS_DECLARADAS)

    no_declaradas = sin_sesion - declaradas
    assert not no_declaradas, (
        "hay rutas que se sirven sin pedir sesión y no están declaradas:\n  "
        + "\n  ".join(f"{metodo} {camino}" for metodo, camino in sorted(no_declaradas))
        + "\n\nO se les pone su `UsuarioActual`/`ExplotacionActual` en la firma —lo normal— o se "
        "añaden a `RUTAS_PUBLICAS_DECLARADAS` **con el motivo escrito**, que es lo que obliga a "
        "que la decisión sea una decisión y no un olvido."
    )


def test_la_lista_de_publicas_no_tiene_rutas_que_ya_no_existen():
    """Y al revés: la lista no puede quedarse con rutas viejas.

    Una lista que no se limpia deja de describir el programa y acaba sirviendo de excusa: si una
    ruta se borra o se cierra, su línea tiene que desaparecer de aquí.
    """
    publicadas = _pares_publicados()
    sobran = set(RUTAS_PUBLICAS_DECLARADAS) - publicadas
    assert not sobran, (
        "en `RUTAS_PUBLICAS_DECLARADAS` hay rutas que la aplicación ya no publica:\n  "
        + "\n  ".join(f"{metodo} {camino}" for metodo, camino in sorted(sobran))
    )


def test_cada_ruta_publica_dice_por_que():
    """Una ruta pública sin motivo escrito es un olvido con buena letra."""
    for (metodo, camino), motivo in RUTAS_PUBLICAS_DECLARADAS.items():
        assert isinstance(motivo, str) and len(motivo.strip()) >= 30, (
            f"{metodo} {camino}: el motivo está vacío o no dice nada. Escribe **por qué** esta "
            "ruta no puede pedir sesión."
        )
        assert "?" != motivo.strip(), f"{metodo} {camino}: el motivo es un interrogante"


def test_las_que_llaman_a_servicios_de_fuera_lo_dicen():
    """Las rutas públicas que **salen a internet** tienen que decirlo en su motivo.

    No es un adorno: son las que pueden convertir esta instalación en un repetidor contra los
    servicios del FEGA, del Catastro o de la Junta, y son las que necesitan el límite que todavía
    no hay (T01 §5.1 y §5.2).
    """
    salen_fuera = {
        ("GET", "/api/mapa/imagen"),
        ("GET", "/api/zonas-vulnerables/estado"),
        ("GET", "/api/iuws/version"),
        ("GET", "/api/iuws/comprobar-de-verdad"),
    }
    assert salen_fuera <= set(RUTAS_PUBLICAS_DECLARADAS)
    for par in sorted(salen_fuera):
        motivo = RUTAS_PUBLICAS_DECLARADAS[par]
        assert any(
            palabra in motivo.lower()
            for palabra in ("límite", "limite", "caché", "cache", "sin identificarse", "no dice")
        ), f"{par[0]} {par[1]}: no se dice nada de que sale a un servicio de fuera ni de su límite"


# --------------------------------------------------------------------------
# 3. Las que se cerraron el 03/10/2026: comprobadas de verdad, con su control
# --------------------------------------------------------------------------


class _ElSigpacDeMentira:
    """Una respuesta vacía del SIGPAC, para no salir a internet ni en el caso de un fallo.

    Está aquí por un motivo concreto: si alguien **volviera a abrir** una de estas rutas, la
    prueba tiene que ponerse roja **sin** llegar a llamar al FEGA. Con esto, la petición se queda
    en casa y la prueba falla por el 200 en vez del 401, que es lo que tiene que pasar.
    """

    status_code = 200
    text = "[]"
    content = b"[]"
    headers = {"content-type": "application/json"}

    def raise_for_status(self) -> None:
        """`httpx` la llama, así que una respuesta de mentira tiene que tenerla.

        Sin esto, la ruta del `sigpac` se lleva un `AttributeError`, lo cuenta como «no se ha
        podido preguntar» y contesta 503: el caso de control diría que el cuerpo de la prueba está
        mal cuando el que estaba mal era el de mentira.
        """
        return None


@pytest.fixture
def sin_salir_a_internet(monkeypatch):
    import httpx

    monkeypatch.setattr(httpx, "get", lambda url, **k: _ElSigpacDeMentira())


def _con_y_sin_vale(cliente, cuenta, metodo: str, camino: str, cuerpo: dict | None = None) -> tuple:
    """Pide la ruta con vale y sin vale. **El control primero**: con vale tiene que contestar 200.

    Si el cuerpo no valiera, el primer `assert` lo diría, y el 401 del segundo no podría venir de
    un error de validación. Sin este control, la prueba pasaría por el motivo equivocado.
    """
    opciones = {"json": cuerpo} if cuerpo is not None else {}
    con_vale = cliente.request(metodo, camino, headers=cuenta["cabeceras"], **opciones)
    assert con_vale.status_code == 200, (
        f"{metodo} {camino} con vale tendría que contestar 200 y contesta "
        f"{con_vale.status_code}: {con_vale.text[:200]}. El cuerpo de esta prueba no vale, así que "
        "el 401 de abajo no probaría nada."
    )
    sin_vale = cliente.request(metodo, camino, **opciones)
    return con_vale, sin_vale


class TestLasQueSeCerraronElTresDeOctubre:
    """Las seis rutas que se han cerrado hoy, cerradas de verdad y con su caso de control.

    Las cuatro primeras son las que el inventario de T01 marcó como «**debería** pedir sesión»
    (§3.17 a §3.20): llevaban seis semanas abiertas. La quinta y la sexta son las dos que salen a
    servicios de fuera en bloque —hasta 26 llamadas al FEGA la una, hasta 3 al SIGPAC y al
    Catastro la otra, por cada petición y sin ningún límite— y cuyas únicas pantallas ya mandaban
    su vale, así que cerrarlas no le quita nada al agricultor.
    """

    def test_consultar_un_recinto_del_sigpac(self, cliente, cuenta, sin_salir_a_internet):
        _, sin_vale = _con_y_sin_vale(
            cliente, cuenta, "POST", "/api/sigpac/consultar", {"ref_sigpac": "37-22-0-0-501-427-1"}
        )
        assert sin_vale.status_code == 401, sin_vale.text

    def test_buscar_los_trozos_de_una_parcela(self, cliente, cuenta, sin_salir_a_internet):
        _, sin_vale = _con_y_sin_vale(
            cliente, cuenta, "POST", "/api/sigpac/buscar", {"referencia": "37:70:0:0:503:51"}
        )
        assert sin_vale.status_code == 401, sin_vale.text

    def test_tocar_el_mapa(self, cliente, cuenta, sin_salir_a_internet):
        _, sin_vale = _con_y_sin_vale(
            cliente, cuenta, "POST", "/api/mapa/punto", {"x": -5.5547, "y": 40.9073}
        )
        assert sin_vale.status_code == 401, sin_vale.text

    def test_validar_un_plan_de_abonado(self, cliente, cuenta, campana):
        _, sin_vale = _con_y_sin_vale(
            cliente,
            cuenta,
            "POST",
            "/api/planes/validar",
            {"campana_id": campana["id"], "cultivo": "Trigo", "superficie_ha": 2.43},
        )
        assert sin_vale.status_code == 401, sin_vale.text

    def test_validar_un_analisis(self, cliente, cuenta, campana):
        _, sin_vale = _con_y_sin_vale(
            cliente,
            cuenta,
            "POST",
            "/api/analiticas/validar",
            {
                "campana_id": campana["id"],
                "tipo": "suelo",
                "fecha_toma_muestra": "2026-02-14",
                "laboratorio": "Un laboratorio",
                "parametros": [{"clave": "ph", "valor": 7.4}],
            },
        )
        assert sin_vale.status_code == 401, sin_vale.text

    def test_validar_las_medidas_preventivas(self, cliente, cuenta):
        _, sin_vale = _con_y_sin_vale(
            cliente, cuenta, "POST", "/api/medidas/validar", {"aplicadas": ["rotacion"]}
        )
        assert sin_vale.status_code == 401, sin_vale.text


# --------------------------------------------------------------------------
# 4. Y lo que el estado del SIGPAC dejó de decir
# --------------------------------------------------------------------------


class TestElEstadoDelSigpacYaNoDiceDondeEstaLaCarpeta:
    """`GET /api/sigpac/estado` es público **a propósito**, así que lo que devuelve importa.

    Devolvía `"ruta": str(RUTA_DATOS)`: la ruta absoluta de una carpeta del servidor, con el
    usuario con el que corre el programa dentro. Es exactamente el tipo de dato que no se pone en
    una respuesta pública, y estaba ahí desde el primer día (T01 §3.13: «quitar `ruta`»).
    """

    def test_no_dice_la_ruta_de_la_carpeta_del_servidor(self, cliente):
        datos = cliente.get("/api/sigpac/estado").json()
        assert "ruta" not in datos, (
            "el estado del SIGPAC vuelve a decir dónde está la carpeta de datos del servidor"
        )

    def test_lo_que_si_dice_sigue_diciendolo(self, cliente):
        """**El control**: se ha quitado un campo, no la información útil.

        Sin esto, borrar la respuesta entera también dejaría la prueba de arriba en verde, y la
        pantalla se quedaría sin poder decir si los datos del SIGPAC están descargados.
        """
        datos = cliente.get("/api/sigpac/estado").json()
        assert datos["cargados"] is True, "los datos del SIGPAC están descargados y hay que decirlo"
        assert datos["productos"] == 933
        assert "Creative Commons" in datos["licencia"]
        assert datos["textos"]["titulo"]

    def test_ninguna_respuesta_publica_lleva_una_ruta_de_fichero(self, cliente, cuenta):
        """Y una comprobación que no depende de nombres de campo.

        Se recorre la respuesta entera —en cualquier nivel— buscando algo que parezca una ruta de
        fichero del servidor: una barra invertida de Windows, o una barra inclinada al principio de
        un texto. Así se caza también el día que alguien meta la ruta dentro de un texto, que es
        como se cuelan estas cosas.
        """
        datos = cliente.get("/api/sigpac/estado").json()

        sospechosas: list[str] = []

        def mirar(valor, donde: str) -> None:
            if isinstance(valor, dict):
                for clave, dentro in valor.items():
                    mirar(dentro, f"{donde}.{clave}")
            elif isinstance(valor, list):
                for indice, dentro in enumerate(valor):
                    mirar(dentro, f"{donde}[{indice}]")
            elif isinstance(valor, str):
                if "\\" in valor or ":\\" in valor or valor.startswith("/"):
                    sospechosas.append(f"{donde} = {valor!r}")

        mirar(datos, "estado")
        assert not sospechosas, (
            "la respuesta pública del estado del SIGPAC lleva algo que parece una ruta del "
            "servidor:\n  " + "\n  ".join(sospechosas)
        )


# --------------------------------------------------------------------------
# 5. Y una cuenta de las que quedan, para que el número no se pierda
# --------------------------------------------------------------------------


def test_las_publicas_que_quedan_son_las_que_estan_escritas():
    """El recuento, medido: **26 rutas sin sesión**, todas declaradas.

    Estaba en **24** cuando se hizo el inventario de T01. Las cinco que faltan son las cuatro que
    «deberían pedir sesión» y la búsqueda del SIGPAC; más otras dos que se han cerrado por el
    mismo motivo (el toque en el mapa), y a cambio han entrado tres nuevas que sí lo dicen
    (`GET /api/maquinaria/que-falta`, del ticket de maquinaria, y `GET /api/gastos/que-falta` y
    `GET /api/trabajos/que-falta`, de las cuentas del T13 y de los trabajos del T15: las tres son la
    misma lista de «lo que el programa todavía no calcula» para todo el mundo).

    **Y dos más desde el 09/11/2026**, las de la observabilidad: el aviso de pantalla (que se manda
    con `sendBeacon` y no puede llevar cabeceras) y el resumen de lo medido, que se protege con
    **su token**, no con la sesión del agricultor. Las dos llevan su motivo escrito arriba.

    El número no es el objetivo —una ruta pública con motivo es tan buena como una cerrada—; lo
    que importa es que **esté escrito y que cuadre**, y eso es lo que se comprueba aquí.
    """
    _, sin_sesion = _pares_con_sesion()
    assert len(sin_sesion) == 26, (
        f"hay {len(sin_sesion)} rutas sin sesión y estaban contadas 26: "
        f"{sorted(sin_sesion)}"
    )
    assert sin_sesion == set(RUTAS_PUBLICAS_DECLARADAS)


def test_queda_escrito_lo_que_falta_por_hacer():
    """La lista de lo pendiente, en el propio fichero, para que no se pierda al cerrar la ronda.

    Es una prueba de documentación y se hace a propósito: lo que se ha decidido **no** hacer hoy
    tiene que estar donde el siguiente lo lea, no solo en un documento de seguimiento. Si alguien
    arregla uno de estos, esta prueba le obliga a actualizar la frase.
    """
    pendiente = __doc__ or ""
    for asunto in ("límite de peticiones", "mapa/imagen", "iuws/version", "zonas-vulnerables"):
        assert asunto in pendiente, (
            f"en la cabecera de este fichero falta lo que queda pendiente sobre «{asunto}»"
        )
