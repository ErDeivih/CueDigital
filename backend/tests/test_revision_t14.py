"""Revisión independiente del T14 (maquinaria e inspecciones): las pruebas de lo que se encontró.

QUÉ ES ESTE FICHERO, Y POR QUÉ ESTÁ APARTE DE `test_t14_maquinaria.py`

Las 58 pruebas del ticket comprueban lo que el ticket dice que hace, y lo comprueban bien: que no
se calcula ninguna fecha, que las cinco obligaciones salen separadas, que el aislamiento entre
fincas contesta 404, que anular deja de contar. Este fichero es lo contrario: **intenta romper el
ticket**. **16 de sus 24 pruebas están en rojo** (una por defecto encontrado) y las **8 verdes** son
puertas que he recorrido al revisar y que quiero dejar atadas con su prueba. El motivo de cada una
está contado en su comentario y en `docs/REVISION_T14.md`.

CÓMO DISTINGUIR LOS DOS TIPOS DE PRUEBA

  · Las de **comportamiento** llaman a la API como lo haría la pantalla y comprueban lo que
    contesta hoy (y lo que debería contestar).
  · Las **estáticas** leen el código de `web/app.js` y de la pantalla, porque el defecto vive en
    el navegador y la suite de Python no puede pulsar botones. Se dice en cada una. No sustituyen
    a una prueba de recorrido en `tests_js/` (que es donde habría que escribirlas): sirven para
    que el defecto no vuelva sin que salte algo.

Lo que **no** se toca desde aquí: ni una línea del ticket. Todo esto es información para quien
decida qué se arregla y en qué orden.
"""

from __future__ import annotations

import ast
import datetime as dt
import pathlib
import re

from app import maquinaria, textos

RAIZ = pathlib.Path(__file__).resolve().parents[2]
WEB = RAIZ / "backend" / "web"
APP_JS = WEB / "app.js"
LA_PANTALLA = WEB / "react" / "pantallas" / "maquinaria.js"
TESTS_JS = RAIZ / "backend" / "tests_js"

HOY = dt.date.today()


def _dias(dias: int) -> str:
    return (HOY + dt.timedelta(days=dias)).isoformat()


# --------------------------------------------------------------------------
# Ayudas para leer el código de la pantalla (las pruebas estáticas)
# --------------------------------------------------------------------------


def el_codigo_de_la_aplicacion() -> str:
    return APP_JS.read_text(encoding="utf-8")


def el_bloque_de_la_maquinaria() -> str:
    """El trozo de `app.js` que prepara los datos de estas pantallas.

    Va desde `estadoDeLaMaquinaria` (donde empieza la sección) hasta el manejador de clics. Es
    donde se componen las frases que el agricultor lee en la tarjeta y en la tabla.
    """
    codigo = el_codigo_de_la_aplicacion()
    principio = codigo.index("function estadoDeLaMaquinaria()")
    final = codigo.index("// -------------------------------------------------------------------- eventos")
    return codigo[principio:final]


def los_textos_que_copia_el_test_de_javascript() -> dict[str, str]:
    """El diccionario `MAQUINARIA` que el test del móvil usa en lugar de lo que sirve el servidor."""
    copia = (TESTS_JS / "maquinaria.test.js").read_text(encoding="utf-8")
    bloque = copia.split("const MAQUINARIA = {", 1)[1].split("\n};", 1)[0]
    suyos: dict[str, str] = {}
    for clave, valor in re.findall(r"^\s*([a-z_0-9]+):\s*(.*?),\s*$", bloque, re.M):
        try:
            suyos[clave] = ast.literal_eval(valor)
        except (ValueError, SyntaxError):
            continue
    return suyos


# --------------------------------------------------------------------------
# Ayudas para llamar a la API, como lo hace el ticket
# --------------------------------------------------------------------------


def crear_maquina(cliente, cabeceras, **cambios) -> dict:
    datos = {
        "nombre": "El Landini",
        "clase": "tractor",
        "propiedad": "propia",
        "disponibilidad": "disponible",
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/maquinaria", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def la_ficha(cliente, cabeceras, maquina_id: int) -> dict:
    respuesta = cliente.get(f"/api/maquinaria/{maquina_id}", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def declarar(cliente, cabeceras, maquina_id: int, tipo: str, **cambios) -> dict:
    datos = {"aplicabilidad": "si", "origen": "documento", **cambios}
    respuesta = cliente.put(
        f"/api/maquinaria/{maquina_id}/obligaciones/{tipo}", headers=cabeceras, json=datos
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def apuntar_inspeccion(cliente, cabeceras, maquina_id: int, **cambios) -> dict:
    datos = {"tipo": "iteaf", "fecha": "2024-03-01", "resultado": "favorable"}
    datos.update(cambios)
    respuesta = cliente.post(
        f"/api/maquinaria/{maquina_id}/inspecciones", headers=cabeceras, json=datos
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# ==========================================================================
# 1. Lo que se enseña tiene que estar en el código (y lo que está, usarse)
# ==========================================================================


class TestLoQueSeEnsenyaEstaEnElCodigo:
    """El defecto que más veces ha aparecido en este proyecto: un texto que no existe.

    Cuando una clave no está, `t("maquinaria", {})` devuelve `undefined` y **la frase sale en
    pantalla con la palabra «undefined» dentro**, en inglés y en medio de una frase en castellano.
    `nucleo.rellena` lo evita a propósito para los huecos de una plantilla («si falta un dato, se
    deja el hueco tal cual… un "undefined" asusta y no dice nada»), pero una clave que no existe
    no pasa por ahí: se lee tal cual.
    """

    def test_la_tarjeta_del_movil_no_ensena_la_palabra_undefined(self):
        """**El defecto grave de este ticket.** La tarjeta del móvil compone tres renglones con
        `m.<clave>` y dos de esas claves **no existen** en `textos.MAQUINARIA_DE_LA_FINCA`:

            proxima: `${m.proxima_revision}: ${…}`   →  «undefined: ITV el 12/05/2026»
            papeles: `${m.documentacion}: ${…}`      →  «undefined: 1 papel»

        Los dos nombres existen en `textos.TABLA` (son los de la tabla del ordenador), y es ahí de
        donde hay que sacarlos. David lee esa tarjeta en el móvil, en el campo: «undefined: 1
        papel» no es una errata, es una frase que no se entiende.

        **CORREGIDA EL 05/10/2026 POR EL COORDINADOR, Y HAY QUE DECIR POR QUÉ.** Tal y como se escribió,
        esta prueba **no podía pasar con el defecto arreglado**: exigía que el código siguiera teniendo
        la forma exacta que produce el `undefined` (`assert "`${m.proxima_revision}:" in bloque`) y que
        las dos claves estuvieran en `MAQUINARIA_DE_LA_FINCA`. El arreglo que el propio párrafo de
        arriba pide —«es ahí de donde hay que sacarlos», de `textos.TABLA`— **quita esa forma y no
        duplica las claves**, así que las dos afirmaciones se ponen rojas con el defecto ya arreglado.
        Lo que se comprueba ahora es el contrato de verdad, que caza el defecto igual y sigue valiendo
        con cualquiera de los dos arreglos posibles: **si el renglón se compone con `m.<clave>`, esa
        clave tiene que existir**; y si se saca de los rótulos de la tabla, tiene que sacarse de ahí.
        """
        bloque = el_bloque_de_la_maquinaria()
        for clave in ("proxima_revision", "documentacion"):
            if f"`${{m.{clave}}}:" in bloque:
                assert clave in textos.MAQUINARIA_DE_LA_FINCA, (
                    f"la tarjeta del móvil compone «{clave}: …» con `m.{clave}` y esa clave no existe "
                    "en `textos.MAQUINARIA_DE_LA_FINCA`: en pantalla se lee «undefined: …». O se saca "
                    "de `textos.TABLA` —que es de donde la saca la tabla del ordenador— o se le pone "
                    "su frase aquí."
                )
        # Y con el arreglo que se aplicó, los dos rótulos salen de los de la tabla: se exige que de
        # verdad se tomen de ahí, para que no vuelvan a quedarse sin frase.
        for clave in ("proxima_revision", "documentacion"):
            assert f'col("{clave}")' in bloque or clave in textos.MAQUINARIA_DE_LA_FINCA, (
                f"el renglón de «{clave}» no se puede componer: no está en `MAQUINARIA_DE_LA_FINCA` ni "
                "se saca de los rótulos de la tabla"
            )

    def test_todas_las_claves_que_usa_la_maquinaria_existen(self):
        """El barrido entero, para que no quede otra igual: **todas** las claves de la maquinaria
        que se nombran en `app.js` (y en la pantalla) tienen que existir en `textos.py`.

        Se mira en `m.<clave>` (el diccionario de la maquinaria, que en `app.js` es
        `t("maquinaria", {})` y en el componente es `textos.maquinaria`) y en las claves escritas
        de la forma `t("maquinaria.<clave>")`.
        """
        bloque = el_bloque_de_la_maquinaria()
        pantalla = LA_PANTALLA.read_text(encoding="utf-8")
        claves = set(re.findall(r"(?<![A-Za-z_0-9])m\.([a-z][a-z_0-9]*)", bloque))
        claves |= set(re.findall(r"(?<![A-Za-z_0-9])m\.([a-z][a-z_0-9]*)", pantalla))
        escritas = set(
            re.findall(r"t\(\s*[\"'`]maquinaria\.([a-z][a-z_0-9]*)", el_codigo_de_la_aplicacion())
        )
        # Lo que se compone con `${…}` no se puede sacar por texto (`situacion_${…}`, `que_es_${…}`):
        # se exige que **todas** las respuestas posibles tengan su frase, que es lo que hace falta.
        for situacion in (
            "no_se_si_toca",
            "no_aplica",
            "sin_inspeccion",
            "no_favorable",
            "sin_fecha",
            "vencida",
            "proxima",
            "vigente",
        ):
            assert f"situacion_{situacion}" in textos.MAQUINARIA_DE_LA_FINCA, situacion
        for obligacion in maquinaria.OBLIGACIONES:
            assert f"que_es_{obligacion}" in textos.MAQUINARIA_DE_LA_FINCA, obligacion

        # Los prefijos que van dentro de una plantilla (`m.situacion_${…}`) acaban en `_` y no son
        # una clave: se quitan de la lista.
        todas = {una for una in (claves | escritas) if not una.endswith("_")}
        faltan = sorted(una for una in todas if una not in textos.MAQUINARIA_DE_LA_FINCA)
        assert faltan == [], (
            f"estas claves se usan en la pantalla de la maquinaria y no están en `textos.py`: "
            f"{faltan} (en pantalla salen como «undefined»)"
        )

    def test_la_copia_de_los_textos_del_test_del_movil_dice_lo_que_sirve_el_servidor(self):
        """La copia que el test de JavaScript usa en lugar del servidor tiene que decir **lo mismo**.

        Todas las pantallas del proyecto tienen esta prueba en `tests/test_interfaz.py`
        (`test_la_copia_lleva_los_textos_de_…`), y existe por un motivo escrito allí: «sin esto, la
        copia podría quedarse con una frase vieja y el test de la pantalla comprobaría una pantalla
        que el agricultor no tiene —y pasaría—». La maquinaria no la tiene, y la copia se escribió
        **abreviada**: 35 de sus 172 textos dicen otra cosa que lo que sirve `/api/interfaz`.

        Los que más importan son justo los del ticket: `clasificacion_falta`,
        `campo_proxima_fecha_pista` y `form_inspeccion_pista` son tres de las frases que explican
        que **el programa no calcula la fecha**, y el test las comprueba en su versión corta.
        """
        copia = los_textos_que_copia_el_test_de_javascript()
        del_servidor = textos.MAQUINARIA_DE_LA_FINCA
        distintas = {
            clave: (del_servidor[clave], dicho)
            for clave, dicho in copia.items()
            if clave in del_servidor and del_servidor[clave] != dicho
        }
        assert distintas == {}, (
            "la copia de `tests_js/maquinaria.test.js` dice otra cosa que el servidor en "
            f"{len(distintas)} textos: {sorted(distintas)}"
        )

    def test_ningun_texto_de_la_maquinaria_se_queda_sin_usar(self):
        """Y al revés: un texto que existe y no se enseña en ningún sitio.

        **Se mira el programa, no sus copias de los tests**: las copias de `tests_js/` nombran claves
        que la aplicación no usa (por eso valen menos que el original), así que aquí solo se leen
        `app/` y `web/`. Y lo que sale, sale con nombre y apellidos:

          · **`guarda_el_papel`** es el caso que importa: es **el único texto del proyecto que dice
            que los papeles de las inspecciones hay que poder enseñarlos tres años**, y no se lee en
            ninguna pantalla.
          · `proxima_fecha_pista` y `documento_pista` son las pistas escritas para el campo de la
            próxima fecha y el del papel: se enseñan sus primas (`campo_…_pista`), así que estas dos
            se quedaron de una versión anterior.
          · `equipo_ya_esta`, `apuntar_otra_inspeccion`, `arreglada_el`, `sin_arreglar`,
            `sin_arreglar_desde`, `la_maquina` y `fijate` son textos que se escribieron y se
            sustituyeron por otros (los `_texto` que sí usa la pantalla).
        """
        codigo = ""
        for carpeta in ("app", "web"):
            for fichero in (RAIZ / "backend" / carpeta).rglob("*"):
                if (
                    fichero.is_file()
                    and fichero.suffix in (".py", ".js", ".html", ".css")
                    and fichero.name != "textos.py"
                ):
                    codigo += fichero.read_text(encoding="utf-8", errors="replace") + "\n"
        # Las claves que se componen por dentro (singular/plural y las respuestas de una lista) no se
        # buscan: se nombran con `${…}`, y su comprobación es la de arriba.
        dinamicas = ("_uno", "_una", "_varios")
        candidatas = [
            clave
            for clave in textos.MAQUINARIA_DE_LA_FINCA
            if not clave.endswith(dinamicas)
            and not clave.startswith(("situacion_", "que_es_", "clase_", "propiedad_", "origen_"))
            and clave
            not in (
                "aplicabilidad_si",
                "aplicabilidad_no",
                "aplicabilidad_no_se",
                "disponibilidad_disponible",
                "disponibilidad_no_disponible",
                "disponibilidad_no_se",
                "resultado_favorable",
                "resultado_desfavorable",
                "resultado_no_consta",
                "obligacion_itv",
                "obligacion_iteaf",
                "obligacion_mantenimiento",
                "obligacion_seguro",
                "obligacion_roma",
            )
        ]
        sin_usar = [
            clave
            for clave in candidatas
            if not re.search(r"(?<![A-Za-z_0-9])" + re.escape(clave) + r"(?![A-Za-z_0-9])", codigo)
        ]
        assert sin_usar == [], f"estos textos de la maquinaria no se enseñan en ningún sitio: {sin_usar}"


# ==========================================================================
# 2. Corregir una máquina: las tres respuestas que se pierden por el camino
# ==========================================================================


class TestCorregirUnaMaquina:
    """El camino que el propio ticket señala como el que más se usa: «la matrícula mal copiada, las
    horas, el número de ROMA o la clasificación técnica».

    Hoy ese camino **no funciona**: al abrir «Corregir esta máquina» el formulario enseña las tres
    preguntas (clase, propiedad y disponibilidad) **sin ninguna respuesta marcada**, y al guardar
    manda las tres vacías. El servidor contesta 422 con ««» no es una de las clases de máquina que
    se pueden elegir», que es lo que lee el agricultor que acaba de ver la clase puesta.
    """

    def test_la_ficha_preparada_lleva_la_clase_la_propiedad_y_la_disponibilidad(self):
        """Por qué sale sin marcar: la ficha que se prepara **no lleva el valor en crudo**.

        `unaMaquinaPreparada` devuelve `clase_texto`, `propiedad_texto` y `disponibilidad_texto`
        (para leer), pero **no** `clase`, `propiedad` ni `disponibilidad`. El formulario marca la
        opción elegida con `elegido("clase") = b.clase || maquina.clase || ""`, y `maquina.clase` es
        `undefined`: las tres preguntas salen en blanco aunque el agricultor las contestó el primer
        día.
        """
        bloque = el_bloque_de_la_maquinaria()
        preparada = bloque.split("function unaMaquinaPreparada(", 1)[1].split("\n}", 1)[0]
        faltan = [
            campo
            for campo in ("clase", "propiedad", "disponibilidad")
            if not re.search(rf"^\s*{campo}:", preparada, re.M)
        ]
        assert faltan == [], (
            "la ficha preparada no lleva el valor en crudo de "
            f"{faltan}: el formulario de corregir no puede marcar la respuesta que ya estaba "
            "puesta (y el de guardar no la puede mandar)"
        )

    def test_corregir_una_maquina_no_manda_las_tres_respuestas_vacias(self):
        """Y el otro extremo: lo que se manda al corregir.

        `recogeLaMaquina` las lee así: `clase: b.clase || ""`. El borrador de una corrección nace
        vacío (`maquina-corregir` hace `suyo.borrador = {}`), y en el borrador **solo** entra lo que
        el agricultor vuelva a pulsar. Si solo corrige la matrícula —que es el caso que el ticket
        pone por delante—, se manda `clase: ""`, `propiedad: ""`, `disponibilidad: ""`.

        Ejecutando esa misma función con el código real (`node`, extrayendo `recogeLaMaquina` de
        `app.js`) sale exactamente esto:

            {"nombre": "El Landini", "clase": "", "clasificacion_tecnica": "Tractor agrícola de
             ruedas", "matricula": "1234 ABD", "propiedad": "", "horas": 2400, "disponibilidad": ""}

        Lo que tiene que hacer es partir de lo que ya está guardado (`maquina.clase`), como el
        propio formulario hace con los campos de texto (`escrito(id, "matricula")`).
        """
        bloque = el_bloque_de_la_maquinaria()
        recoge = bloque.split("function recogeLaMaquina(", 1)[1].split("\n}", 1)[0]
        malas = [
            campo
            for campo in ("clase", "propiedad", "disponibilidad")
            if re.search(rf"^\s*{campo}:\s*b\.{campo}\s*\|\|\s*[\"']{{2}}", recoge, re.M)
        ]
        assert malas == [], (
            f"al corregir una máquina se mandan vacías {malas}: el borrador de la corrección nace "
            "vacío, así que corregir solo la matrícula contesta 422 y no guarda nada. Hay que "
            "partir de lo que ya está guardado (como hacen los campos de texto)."
        )

    def test_el_servidor_rechaza_lo_que_hoy_manda_la_pantalla(self, cliente, cuenta):
        """El defecto, por el camino largo: se apunta la máquina, se corrige **solo la matrícula**
        y se manda lo que hoy compone la pantalla.

        La primera parte (lo que manda la pantalla) da 422; la segunda (lo que debería mandar) se
        guarda. Las dos juntas son el defecto entero: el servidor está bien, y la pantalla manda un
        hueco donde había una respuesta.
        """
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras, matricula="1234 ABC")
        lo_que_manda_la_pantalla = {
            "nombre": "El Landini",
            "clase": "",
            "clasificacion_tecnica": None,
            "matricula": "1234 ABD",
            "propiedad": "",
            "horas": None,
            "disponibilidad": "",
        }
        respuesta = cliente.put(
            f"/api/maquinaria/{maquina['id']}", headers=cabeceras, json=lo_que_manda_la_pantalla
        )
        assert respuesta.status_code == 200, (
            "corregir solo la matrícula tiene que guardarse; lo que contesta hoy es "
            f"{respuesta.status_code}: {respuesta.text}"
        )


# ==========================================================================
# 3. Reenviar sin duplicar: la clave que la pantalla no manda
# ==========================================================================


class TestReenviarSinDuplicar:
    """El caso A12 del contrato, que el ticket dice cubrir con `clave_de_reenvio`.

    En el servidor está cubierto y probado. Lo que falta es la otra mitad: **ninguna pantalla de
    este ticket manda la clave**. En el resto del programa la clave se pide al abrir el formulario
    (`claveDeReenvio`, en `app.js`, con su motivo escrito: «si se pidiera al guardar, dos
    pulsaciones del mismo botón mandarían dos claves distintas»), y aquí no se pide en ningún
    formulario: se apunta la máquina, la inspección o la avería sin ella.
    """

    def test_la_pantalla_manda_la_clave_de_reenvio_en_lo_que_apunta(self):
        bloque = el_bloque_de_la_maquinaria()
        guardar = bloque.split("async function guardarLoDeLaMaquinaria()", 1)[1].split(
            "\n// ----", 1
        )[0]
        assert guardar.count("clave_de_reenvio") >= 3, (
            "los tres formularios de la maquinaria (la máquina, la inspección y la avería) tienen "
            "que mandar `clave_de_reenvio`, como los demás apuntes del programa: sin ella, dos "
            "pulsaciones del botón (o un reintento) apuntan dos veces lo mismo y el servidor no "
            "puede saber que es el mismo apunte"
        )

    def test_sin_clave_dos_envios_del_mismo_apunte_son_dos_inspecciones(self, cliente, cuenta):
        """El efecto, medido: sin clave, el servidor **no puede** reconocer el reenvío.

        No es un defecto del servidor —la clave la tiene que traer quien apunta—, pero es la razón
        por la que la mitad que falta en la pantalla es un defecto de verdad: el mismo apunte
        mandado dos veces deja dos inspecciones en el cuaderno, y en una inspección de verdad eso es
        decir que le pasaron dos.
        """
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        primera = apuntar_inspeccion(cliente, cabeceras, maquina["id"], fecha="2024-03-01")
        segunda = apuntar_inspeccion(cliente, cabeceras, maquina["id"], fecha="2024-03-01")
        assert primera["id"] != segunda["id"]
        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        assert len(ficha["inspecciones"]) == 2, (
            "sin `clave_de_reenvio` el servidor no puede deduplicar: es lo que le pasa hoy a la "
            "pantalla, que no la manda"
        )

    def test_la_clave_de_reenvio_no_se_confunde_entre_maquinas(self, cliente, cuenta):
        """Y el reenvío tiene que cerrarse **por máquina**.

        La consulta que lo reconoce mira la finca y la clave, pero no la máquina: si llega la misma
        clave para otra máquina —un guion que importe de una lista, un cliente nuevo, o una clave
        reutilizada—, se contesta **la inspección de la otra máquina** y la segunda no se apunta.
        El agricultor cree que la ha apuntado y no está.
        """
        cabeceras = cuenta["cabeceras"]
        tractor = crear_maquina(cliente, cabeceras, nombre="El Landini", clase="tractor")
        remolque = crear_maquina(cliente, cabeceras, nombre="El remolque", clase="remolque")
        la_del_tractor = apuntar_inspeccion(
            cliente, cabeceras, tractor["id"], tipo="itv", clave_de_reenvio="cola-1"
        )
        la_del_remolque = apuntar_inspeccion(
            cliente, cabeceras, remolque["id"], tipo="itv", clave_de_reenvio="cola-1"
        )
        assert la_del_remolque["id"] != la_del_tractor["id"], (
            "la misma clave para otra máquina no puede contestar la inspección de la primera: hay "
            "que cerrar el reenvío por máquina y obligación, no solo por finca"
        )
        assert len(la_ficha(cliente, cabeceras, remolque["id"])["inspecciones"]) == 1
        assert len(la_ficha(cliente, cabeceras, tractor["id"])["inspecciones"]) == 1


# ==========================================================================
# 4. Nada se borra sin rastro
# ==========================================================================


class TestNadaSeBorraSinRastro:
    def test_quitar_una_maquina_deja_escrito_lo_que_se_habia_declarado(self, cliente, cuenta, db_sesion):
        """Quitar una máquina se lleva por delante **lo que se había declarado de ella**, y eso
        desaparece sin dejar rastro.

        La máquina sí queda en la auditoría (la borra `correcciones.borrar`, que guarda la fila
        entera). Las obligaciones que colgaban de ella se borran antes con una sentencia
        (`delete(ObligacionDeMaquina)`), y **de esas no queda nada escrito**: la declaración de que
        «la ITV de este remolque no le toca, y lo dice el papel», con su origen, se pierde. La regla
        de la casa es la contraria: se borra o se anula, pero se sabe que estuvo.

        También se pierde el rastro de las que el agricultor había contestado y corregido: la
        auditoría sí guarda las correcciones de una obligación, pero no su borrado.
        """
        from app import models
        from sqlalchemy import select

        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras, nombre="El remolque", clase="remolque")
        declarar(cliente, cabeceras, maquina["id"], "itv", aplicabilidad="no", origen="documento")
        declarar(cliente, cabeceras, maquina["id"], "roma", aplicabilidad="si", origen="documento")

        respuesta = cliente.delete(f"/api/maquinaria/{maquina['id']}", headers=cabeceras)
        assert respuesta.status_code == 200, respuesta.text

        rastro = list(
            db_sesion.scalars(
                select(models.Auditoria).where(
                    models.Auditoria.entidad.in_(
                        ("maquina", "obligacion_de_maquina", "obligaciones_de_maquina")
                    )
                )
            )
        )
        de_la_maquina = [una for una in rastro if una.entidad == "maquina"]
        assert de_la_maquina, "la máquina tiene que dejar su rastro"
        de_las_obligaciones = [
            una for una in rastro if una.entidad != "maquina"
        ]
        assert de_las_obligaciones, (
            "quitar una máquina borra sus obligaciones declaradas sin dejar rastro en la "
            "auditoría: lo que el agricultor había contestado (y de dónde salía) desaparece"
        )


# ==========================================================================
# 5. Lo que ya estaba escrito no puede desaparecer de la vista
# ==========================================================================


class TestLoQueYaEstabaEscrito:
    def test_traer_un_equipo_con_proxima_iteaf_pero_sin_ultima_no_pierde_la_fecha(
        self, cliente, cuenta
    ):
        """Traer un equipo del cuaderno puede hacer **desaparecer una fecha que ya estaba escrita**.

        En el cuaderno se puede apuntar la fecha de la próxima ITEAF sin apuntar la de la última
        (`EquipoEntrada` admite las dos por separado, y la pantalla de la hoja 1.3 las pregunta por
        separado). `traer_un_equipo_del_cuaderno` solo trae lo que hay dentro de
        `if equipo.fecha_iteaf is not None`, así que en ese caso **no trae ni la inspección ni la
        obligación**: el equipo deja de salir en «equipos que todavía no están en esta lista»
        (porque ya está enlazado) y su ficha dice «No se sabe si le toca», mientras el cuaderno
        sigue teniendo el 01/03/2029 escrito. La fecha está en la base y **no se ve por ningún
        lado de esta pantalla**, que es justo lo que la puerta de calidad del ticket quiere evitar.
        """
        cabeceras = cuenta["cabeceras"]
        equipo = cliente.post(
            "/api/equipos",
            headers=cabeceras,
            json={
                "nombre": "Pulverizador grande",
                "tipo": "Atomizador",
                "fecha_proxima_iteaf": "2029-03-01",
            },
        )
        assert equipo.status_code == 201, equipo.text
        assert equipo.json()["fecha_iteaf"] is None

        traida = cliente.post(
            f"/api/maquinaria/desde-equipo/{equipo.json()['id']}", headers=cabeceras
        )
        assert traida.status_code == 201, traida.text
        maquina_id = traida.json()["id"]

        tabla = cliente.get("/api/maquinaria", headers=cabeceras).json()
        ficha = la_ficha(cliente, cabeceras, maquina_id)
        su_iteaf = {una["tipo"]: una for una in ficha["obligaciones"]}["iteaf"]
        a_la_vista = (
            su_iteaf["proxima_fecha"]
            or ficha["resumen"]["proxima_revision"]["fecha"]
            or any(uno["id"] == equipo.json()["id"] for uno in tabla["equipos_sin_ficha"])
        )
        assert a_la_vista, (
            "la fecha de la próxima ITEAF que el agricultor ya tenía escrita en el cuaderno "
            "(01/03/2029) no se ve en ninguna parte de la maquinaria: no se trajo como inspección y "
            "el equipo ya no sale en «equipos que todavía no están en esta lista»"
        )

    def test_una_fecha_ya_pasada_no_se_queda_sin_la_palabra_vencida(self, cliente, cuenta):
        """Una fecha que ya pasó, apuntada, y que el programa **no dice que haya pasado**.

        Si nadie ha declarado si la obligación le toca, la situación es «no se sabe si le toca», y
        de ahí no se sale: la cuenta de vencidas no la cuenta, no sale el aviso M4 y la tabla
        escribe «ITV el 12/05/2024» **sin ninguna palabra al lado** (el renglón «Vencida» no se
        pone, porque la palabra sale de la situación). El aviso que sí sale —M9, «no has dicho si le
        toca»— no habla de la fecha.

        Es el caso de una máquina que se trae del cuaderno o de una ficha a la que le faltó
        contestar una pregunta: la fecha está, pasó, y el agricultor tiene que compararla de cabeza.
        """
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras, nombre="El Landini")
        # Sin declarar la ITV: nadie ha dicho si le toca.
        apuntar_inspeccion(
            cliente, cabeceras, maquina["id"], tipo="itv", fecha="2019-01-10", proxima_fecha=_dias(-40)
        )
        tabla = cliente.get("/api/maquinaria", headers=cabeceras).json()
        revision = tabla["maquinas"][0]["resumen"]["proxima_revision"]
        avisos = cliente.get(
            "/api/maquinaria/avisos", headers=cabeceras, params={"maquina_id": maquina["id"]}
        ).json()
        codigos = [aviso["codigo"] for aviso in avisos]
        assert revision["vencidas"] >= 1 or "M4_una_inspeccion_esta_vencida" in codigos, (
            "hay una fecha apuntada que ya pasó y el programa no dice en ninguna parte que esté "
            f"vencida: la cuenta dice {revision['vencidas']} vencidas y los avisos son {codigos}"
        )


# ==========================================================================
# 6. El guardián de las fechas: que no se pueda colar por otro fichero
# ==========================================================================


class TestNoSeCalculaNingunaFecha:
    """El ticket tiene su guardián (`test_no_hay_ninguna_funcion_que_sume_dias_a_una_fecha`) y hace
    bien: lee el código del módulo y exige que no haya ni un `timedelta`. Pero **solo lee ese
    fichero**, y el sitio donde una fecha calculada entraría de verdad es otro: el router, que es
    quien escribe `proxima_fecha` en la fila, y la pantalla, que es quien la enseña.

    Comprobado a mano (y deshecho después: ver `docs/REVISION_T14.md`): metiendo en el router un
    `datos.fecha + dt.timedelta(days=365)` cuando el papel no trae la fecha de la próxima, el
    guardián del ticket **sigue en verde**. Las pruebas de aquí ensanchan el guardián a los tres
    ficheros, que es lo que hace falta para que la trampa del ticket esté de verdad cerrada.
    """

    def test_ni_el_modulo_ni_el_router_suman_dias_a_una_fecha(self):
        from app.routers import maquinaria_api

        for modulo, nombre in ((maquinaria, "app/maquinaria.py"), (maquinaria_api, "el router")):
            fuente = pathlib.Path(modulo.__file__).read_text(encoding="utf-8")
            for prohibido in ("timedelta", "relativedelta", "dateutil"):
                assert prohibido not in fuente, (
                    f"{nombre} hace aritmética con fechas («{prohibido}»): la próxima fecha es la "
                    "que trae el papel, y el plazo por clasificación técnica (L07) no está "
                    "transcrito"
                )

    def test_la_pantalla_no_suma_dias_para_ensenar_una_fecha(self):
        """Y la tercera puerta: el JavaScript. Ni el fichero de la pantalla ni el bloque de la
        maquinaria de `app.js` pueden sumar días: lo que se enseña es lo que contestó el servidor.

        Se deja fuera `app.js` entero a propósito, porque ahí sí hay aritmética de fechas legítima
        (el plazo de seguridad de un tratamiento, `d.setDate`), y esto es solo la maquinaria.
        """
        pantalla = LA_PANTALLA.read_text(encoding="utf-8")
        bloque = el_bloque_de_la_maquinaria()
        for codigo, nombre in ((pantalla, "react/pantallas/maquinaria.js"), (bloque, "app.js")):
            for prohibido in ("setDate", "getTime()", "addDays", "sumarDias", "+ 365"):
                assert prohibido not in codigo, (
                    f"{nombre} calcula fechas («{prohibido}»): la fecha que se enseña tiene que "
                    "ser la del papel"
                )


# ==========================================================================
# 7. La máquina que también es un equipo del cuaderno: dos fichas para lo mismo
# ==========================================================================


class TestLaMaquinaQueTambienEsUnEquipoDelCuaderno:
    """Lo que el ticket promete por escrito: «corregirlo una vez lo corrige en los dos sitios y **no
    hay dos fichas de la misma máquina**» (`models.Maquinaria`, cabecera, y el docstring de
    `traer_un_equipo_del_cuaderno`).

    Y lo que pasa: son dos fichas. La corrección se guarda en una y la otra se queda como estaba.
    """

    def _traer(self, cliente, cabeceras, **cambios):
        datos = {
            "nombre": "Pulverizador grande",
            "tipo": "Atomizador",
            "numero_roma": "ROMA-1234",
            "numero_serie": "SN-1",
        }
        datos.update(cambios)
        equipo = cliente.post("/api/equipos", headers=cabeceras, json=datos).json()
        traida = cliente.post(
            f"/api/maquinaria/desde-equipo/{equipo['id']}", headers=cabeceras
        ).json()
        return equipo, traida

    def test_corregir_la_maquina_corrige_el_equipo_del_cuaderno(self, cliente, cuenta):
        """El número de ROMA que se corrige en la ficha nueva **no llega a la hoja 1.3**.

        La hoja 1.3 del cuaderno de la Junta —el papel y el fichero que se le entregan— se compone
        de `EquipoAplicacion` (`routers/cuaderno._fila_de_la_maquina`: nombre, tipo, número de ROMA,
        número de serie y las dos fechas de la ITEAF). El programa dice que corregir una vez lo
        corrige en los dos sitios, así que David corrige ahí el ROMA que copió mal… y el cuaderno
        que manda a la Junta sigue llevando el número viejo, sin que nada se lo diga.
        """
        cabeceras = cuenta["cabeceras"]
        equipo, maquina = self._traer(cliente, cabeceras)
        respuesta = cliente.put(
            f"/api/maquinaria/{maquina['id']}",
            headers=cabeceras,
            json={
                "nombre": "Pulverizador grande",
                "clase": "equipo_de_aplicacion",
                "propiedad": "propia",
                "disponibilidad": "no_se",
                "numero_roma": "ROMA-9999",
                "numero_serie": "SN-2",
                "equipo_aplicacion_id": equipo["id"],
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        del_cuaderno = [
            uno
            for uno in cliente.get("/api/equipos", headers=cabeceras).json()
            if uno["id"] == equipo["id"]
        ][0]
        assert del_cuaderno["numero_roma"] == "ROMA-9999", (
            "el número de ROMA corregido en la maquinaria no llega al equipo del cuaderno: la hoja "
            "1.3 que se le entrega a la Junta sigue llevando el número viejo ("
            f"{del_cuaderno['numero_roma']}), y el programa dice que son la misma máquina"
        )

    def test_la_iteaf_apuntada_en_la_maquinaria_llega_al_cuaderno(self, cliente, cuenta):
        """Y lo mismo con la fecha: la ITEAF se apunta en la ficha nueva, y la hoja 1.3 sigue
        llevando la de antes (o ninguna).

        El cuaderno de la Junta pide, en su hoja 1.3, la fecha de la última ITEAF y la de la
        siguiente. Si el agricultor las apunta donde el programa le dice que se apuntan —la ficha
        de la máquina—, **el papel que se entrega no las lleva**.
        """
        cabeceras = cuenta["cabeceras"]
        equipo, maquina = self._traer(cliente, cabeceras, fecha_iteaf=None, fecha_proxima_iteaf=None)
        declarar(cliente, cabeceras, maquina["id"], "iteaf")
        apuntar_inspeccion(
            cliente,
            cabeceras,
            maquina["id"],
            tipo="iteaf",
            fecha="2026-05-01",
            resultado="favorable",
            proxima_fecha="2032-05-01",
        )
        del_cuaderno = [
            uno
            for uno in cliente.get("/api/equipos", headers=cabeceras).json()
            if uno["id"] == equipo["id"]
        ][0]
        assert del_cuaderno["fecha_proxima_iteaf"] == "2032-05-01", (
            "la ITEAF apuntada en la ficha de la máquina no llega al equipo del cuaderno: la hoja "
            "1.3 sigue sin fecha (o con la vieja)"
        )

    def test_dos_maquinas_no_pueden_ser_el_mismo_equipo_del_cuaderno(self, cliente, cuenta):
        """Y el enlace es único: un equipo del cuaderno **es** una máquina, no dos.

        `desde-equipo` contesta 409 si ya está enlazado (y tiene su prueba), pero por la puerta del
        alta y de la corrección se puede enlazar el mismo equipo a dos fichas distintas: quedan dos
        máquinas que dicen ser el mismo pulverizador, y la que se corrija después no se sabrá cuál
        es.
        """
        cabeceras = cuenta["cabeceras"]
        equipo, maquina = self._traer(cliente, cabeceras)
        segunda = cliente.post(
            "/api/maquinaria",
            headers=cabeceras,
            json={
                "nombre": "El mismo pulverizador, otra vez",
                "clase": "equipo_de_aplicacion",
                "propiedad": "no_se",
                "disponibilidad": "no_se",
                "equipo_aplicacion_id": equipo["id"],
            },
        )
        assert segunda.status_code == 409, (
            "el mismo equipo del cuaderno no puede estar enlazado a dos máquinas: hay que "
            f"comprobarlo también en el alta y en la corrección (contesta {segunda.status_code})"
        )


# ==========================================================================
# 8. Apuntar una inspección desde la pantalla: el botón que no hace nada
# ==========================================================================


class TestApuntarUnaInspeccionDesdeLaPantalla:
    """**El defecto más grave de este ticket**: la única puerta que tiene una inspección no se abre.

    `papelesParaElegir()` (en `app.js`) lee la lista de papeles así:

        return (estado.documentos || []).map((papel) => ({…}));

    y `estado.documentos` **no es una lista**: es lo que devuelve `GET /api/documentos`, que es un
    objeto con la lista dentro (`{textos, documentos: [...], carpetas, …}`, ver
    `routers/documentos_api.listar`). Como `estado.documentos` se carga al entrar (`cargarDatos`),
    en cuanto el agricultor tiene la aplicación abierta esa rama es el objeto, y
    `objeto.map` no existe.

    Medido con el código real (extrayendo la función de `app.js` y llamándola con la forma que
    devuelve el servidor):

        REVIENTA: TypeError: (estado.documentos || []).map is not a function

    Y esa función se llama **solo** desde `formularioDeUnaInspeccion`, así que lo que revienta es
    el formulario de apuntar (y el de corregir) una inspección: la pantalla no se repinta y el
    agricultor pulsa el botón y no pasa nada. El resto del programa lee la misma variable bien
    (`(estado.documentos || {}).documentos`), así que es un despiste de este fichero.
    """

    def test_la_lista_de_papeles_tiene_la_forma_que_lee_el_formulario(self, cliente, cuenta):
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        assert isinstance(datos, dict), "el servidor devuelve un objeto, no una lista"
        assert isinstance(datos.get("documentos"), list)

        bloque = el_bloque_de_la_maquinaria()
        papeles = bloque.split("function papelesParaElegir()", 1)[1].split("\n}", 1)[0]
        assert re.search(r"estado\.documentos\s*\|\|\s*\[\]", papeles) is None, (
            "`papelesParaElegir` trata `estado.documentos` como una lista, y lo que hay ahí es el "
            "objeto de `GET /api/documentos` (`{documentos: [...]}`): al abrir el formulario de una "
            "inspección revienta con «(estado.documentos || []).map is not a function» y el botón "
            "APUNTAR UNA INSPECCIÓN no hace nada. Hay que leer `(estado.documentos || {}).documentos`"
        )


# ==========================================================================
# 9. Lo que sí está bien (y conviene dejar atado)
# ==========================================================================

class TestLoQueEstaBien:
    """Pruebas que hoy pasan: no son defectos, son las puertas que he comprobado una por una al
    revisar el ticket. Están aquí para que se vea qué se miró de verdad y para que no se rompan."""

    def test_cada_puerta_de_la_maquinaria_comprueba_que_el_objeto_es_de_esta_finca(self):
        """**Ruta por ruta**, que es la primera cosa que se mira cuando hay un fallo de aislamiento.

        Se sacan del propio router, no de una lista escrita a mano: por cada ruta que lleve un
        identificador en el camino, la función que la atiende tiene que pasar por
        `obtener_de_la_explotacion` o por una de las ayudas que lo hacen.
        """
        import inspect

        from app.routers import maquinaria_api

        ayudas = (
            "obtener_de_la_explotacion",
            "_la_inspeccion_de_esta_maquina",
            "_la_averia_de_esta_maquina",
            # **El del cuenta-horas** (CRM-07 #8, 15/10/2026). Comprueba `lectura.id`, `maquina_id` **y**
            # `explotacion_id`, o sea que filtra por finca y por maquina a la vez. Se anade aqui porque
            # este barrido mira **nombres** en el codigo de cada ruta, y un ayudante que no este en la
            # lista sale como «sin comprobar» aunque compruebe: lo que no se hace es **renombrarlo** para
            # que pase, que seria tapar el barrido en vez de mantenerlo.
            # ***Que filtre de verdad lo dicen las pruebas de acceso cruzado***, no esta linea:
            # `test_las_lecturas_del_contador` intenta corregir y anular una lectura de otra finca y de
            # otra maquina de la misma finca, y las dos tienen que contestar 404.
            "_la_lectura_de_esta_maquina",
            # **El de las reservas** (CRM-07 #9, 17/10/2026). Comprueba `reserva.id`, `maquina_id` **y**
            # `explotacion_id`: una reserva es de **su** maquina, y el camino lo dice. Se anade por el mismo
            # motivo que el de las lecturas -el barrido mira **nombres**-, y **sin renombrarlo**: lo que
            # filtra de verdad lo dicen las pruebas de acceso cruzado.
            "_la_reserva_de_esta_maquina",
            "_el_papel_es_de_esta_finca",
            "_el_equipo_es_de_esta_finca",
        )
        sin_comprobar = []
        miradas = 0
        for ruta in maquinaria_api.router.routes:
            if "{" not in ruta.path:
                continue
            miradas += 1
            fuente = inspect.getsource(ruta.endpoint)
            if not any(ayuda in fuente for ayuda in ayudas):
                sin_comprobar.append(f"{sorted(ruta.methods)[0]} {ruta.path}")
        assert miradas >= 12, "el barrido no está mirando las rutas del router"
        assert sin_comprobar == [], (
            f"estas rutas no comprueban que el objeto sea de esta finca: {sin_comprobar}"
        )

    def test_el_papel_de_otra_finca_no_se_puede_enlazar_al_corregir_una_inspeccion(
        self, cliente, cuenta, crear_cuenta
    ):
        """El caso feo del aislamiento, por la puerta de la corrección: enlazar el documento de otra
        finca a una inspección mía. Tiene que ser 404 (no 403: no se cuenta si existe)."""
        otra = crear_cuenta("vecino@ejemplo.com")
        papel_ajeno = cliente.post(
            "/api/documentos",
            headers=otra["cabeceras"],
            json={"titulo": "Un papel de otra finca", "tipo": "otros", "fecha": "2024-03-01"},
        ).json()
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        inspeccion = apuntar_inspeccion(cliente, cabeceras, maquina["id"])
        respuesta = cliente.put(
            f"/api/maquinaria/{maquina['id']}/inspecciones/{inspeccion['id']}",
            headers=cabeceras,
            json={
                "tipo": "iteaf",
                "fecha": "2024-03-01",
                "resultado": "favorable",
                "documento_id": papel_ajeno["id"],
            },
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_una_maquina_no_se_puede_enlazar_con_el_equipo_de_otra_finca(
        self, cliente, cuenta, crear_cuenta
    ):
        """Y el otro enlace: apuntar una máquina diciendo que es un equipo de otra finca."""
        otra = crear_cuenta("vecino@ejemplo.com")
        ajeno = cliente.post(
            "/api/equipos", headers=otra["cabeceras"], json={"nombre": "El suyo"}
        ).json()
        respuesta = cliente.post(
            "/api/maquinaria",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "El Landini",
                "clase": "tractor",
                "propiedad": "propia",
                "disponibilidad": "disponible",
                "equipo_aplicacion_id": ajeno["id"],
            },
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_una_obligacion_sin_declarar_no_se_lee_como_que_no_le_toca(self, cliente, cuenta):
        """La regla número uno del proyecto, comprobada otra vez y por su camino más corto: una
        máquina recién apuntada **no** tiene nada en regla y **no** dice que no le toque nada."""
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(
            cliente, cabeceras, propiedad=maquinaria.NO_SE, disponibilidad=maquinaria.NO_SE
        )
        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        suyas = {una["tipo"]: una for una in ficha["obligaciones"]}
        assert set(suyas) == set(maquinaria.OBLIGACIONES), "la ficha enseña siempre las cinco"
        for tipo, obligacion in suyas.items():
            assert obligacion["aplicabilidad"] == maquinaria.NO_SE, tipo
            assert obligacion["situacion"] == maquinaria.SITUACION_NO_SE_SI_TOCA, tipo
            assert obligacion["proxima_fecha"] is None, tipo
            assert obligacion["resultado"] == maquinaria.NO_CONSTA, tipo
        assert ficha["resumen"]["disponibilidad"] == maquinaria.NO_SE
        assert ficha["maquina"]["propiedad"] == maquinaria.NO_SE

    def test_anular_una_inspeccion_la_saca_de_la_ultima_y_del_aviso(self, cliente, cuenta):
        """Anular no borra y **deja de contar**, también en los avisos: la puerta que el ticket
        promete en su §1 y que hay que poder comprobar por el camino de la lista."""
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        declarar(cliente, cabeceras, maquina["id"], "itv")
        vencida = apuntar_inspeccion(
            cliente, cabeceras, maquina["id"], tipo="itv", fecha="2019-01-10", proxima_fecha=_dias(-30)
        )
        antes = cliente.get("/api/maquinaria/avisos", headers=cabeceras).json()
        assert "M4_una_inspeccion_esta_vencida" in [a["codigo"] for a in antes]
        cliente.post(
            f"/api/maquinaria/{maquina['id']}/inspecciones/{vencida['id']}/anular",
            headers=cabeceras,
            json={"motivo": "Esa inspección era de otro tractor"},
        )
        despues = cliente.get("/api/maquinaria/avisos", headers=cabeceras).json()
        assert "M4_una_inspeccion_esta_vencida" not in [a["codigo"] for a in despues]
        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        assert ficha["inspecciones"][0]["anulado"] is True
        assert {una["tipo"]: una for una in ficha["obligaciones"]}["itv"]["situacion"] == (
            maquinaria.SITUACION_SIN_INSPECCION
        )

