"""Revisión independiente de T06 — el mapa y las tierras, y la ficha de versiones.

**Qué es este fichero.** No comprueba que T06 funcione: intenta **demostrar que está mal**, contrato
por contrato, como pidió el coordinador. Cada clase es uno de los diez contratos del encargo, y
dentro de cada una hay dos clases de pruebas:

  · las que **pasan** y dejan escrito qué se ha atacado y qué aguanta (sirven para saber qué valía
    esta revisión), y
  · las que **fallan** mientras el defecto exista: son el producto del trabajo, y cada una lleva en su
    docstring qué le pasa al agricultor y en qué fichero y línea está la causa.

**Lo que NO hace este fichero.** No toca `backend/cuedigital.db` (ni para leer: la suite fija
`CUEDIGITAL_DATABASE_URL` a una carpeta temporal en `conftest.py`) y no modifica ningún fichero que ya
existía. Se escriben datos sintéticos por la API sobre la base temporal de la suite.

**Datos de verdad y datos inventados, dicho por delante.** El agricultor tiene **64 tierras y ninguna
con su forma medida** (`docs/T06_MAPA_Y_TIERRA.md`, §1.7), así que:
  · lo que se puede probar con la **forma** de sus datos (tierras sin forma, sin cultivo, sin
    hectáreas, sin referencia, sin versión, y los recuentos que salen de ahí) se prueba **sin
    inventar geometrías**: `Test1`, `Test3`, `Test4`, `Test5`, `Test6` y `Test9` son de ese tipo; y
  · lo que necesita una forma medida (el vínculo con el mapa, la caja, el dibujo, el ancho real de
    una finca) se prueba con **formas sintéticas**, porque en los datos reales no hay ni una. Está
    dicho en cada prueba que lo hace: `Test2`, `Test7` y la mitad de `Test8`.
  · **Ninguna prueba de este fichero ha leído la base del agricultor.** La única medida que se ha
    hecho sobre sus datos está contada en `docs/REVISION_T06.md`, y se hizo sobre una copia temporal
    que se borró al terminar.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

import pytest

from app import geo, models, textos
from app.database import engine

RAIZ = Path(__file__).resolve().parents[1]
APP_JS = RAIZ / "web" / "app.js"
TIERRAS_MAPA_JS = RAIZ / "web" / "react" / "pantallas" / "tierras_mapa.js"

# Una forma de verdad, del tamaño de una parcela, en Salamanca.
UN_WKT = "POLYGON((-5.5600 40.9000, -5.5500 40.9000, -5.5500 40.9100, -5.5600 40.9100, -5.5600 40.9000))"
OTRO_WKT = "POLYGON((-5.5000 40.9500, -5.4900 40.9500, -5.4900 40.9600, -5.5000 40.9600, -5.5000 40.9500))"
# Un grado entero al este: a esta latitud son unos 84 km. Es una finca **ancha**, y está a propósito:
# es el caso de una explotación con tierras repartidas, que es lo que hace que este programa se cuide
# de «no saltar a otra provincia».
WKT_MUY_AL_ESTE = (
    "POLYGON((-4.5500 40.9000, -4.5400 40.9000, -4.5400 40.9100, -4.5500 40.9100, -4.5500 40.9000))"
)
# Un punto y una línea: son geometrías que **no tienen anillos** (`geo.anillos_de_un_wkt` los
# descarta), así que una tierra puede tener `geometria` escrita y no tener forma que dibujar.
WKT_DE_UN_PUNTO = "POINT(-5.5550 40.9050)"


# ---------------------------------------------------------------------------
# Ayudantes
# ---------------------------------------------------------------------------


def _vista(cliente, cuenta, **parametros) -> dict:
    respuesta = cliente.get("/api/parcelas/vista", headers=cuenta["cabeceras"], params=parametros)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _tierra(datos: dict, alias: str) -> dict:
    encontrada = next((tierra for tierra in datos if tierra["alias"] == alias), None)
    assert encontrada is not None, f"no está «{alias}»: {[t['alias'] for t in datos]}"
    return encontrada


def _crear_campana(cliente, cuenta, anio: int) -> dict:
    respuesta = cliente.post(
        "/api/campanas",
        headers=cuenta["cabeceras"],
        json={
            "anio": anio,
            "fecha_inicio": f"{anio - 1}-10-01",
            "fecha_fin": f"{anio}-09-30",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _un_recinto(parcela_id: int, **cambios) -> dict:
    datos = {
        "parcela_id": parcela_id,
        "poligono": 503,
        "numero_parcela": 51,
        "numero_recinto": 1,
        "geometria": UN_WKT,
        "area_sigpac_ha": 2.7923,
    }
    datos.update(cambios)
    return datos


def _importar(cliente, cuenta, campana_id: int, recintos: list[dict], *, fuente: str = "sigpac") -> dict:
    respuesta = cliente.post(
        "/api/versiones/aplicar",
        headers=cuenta["cabeceras"],
        json={"campana_id": campana_id, "fuente": fuente, "recintos": recintos},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _ensayar(cliente, cuenta, campana_id: int, recintos: list[dict], *, fuente: str = "sigpac") -> dict:
    respuesta = cliente.post(
        "/api/versiones/previsualizar",
        headers=cuenta["cabeceras"],
        json={"campana_id": campana_id, "fuente": fuente, "recintos": recintos},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _las_versiones(cliente, cuenta, **parametros) -> list[dict]:
    respuesta = cliente.get("/api/versiones", headers=cuenta["cabeceras"], params=parametros)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _huella_de_una_tabla(conexion, tabla: str) -> str:
    """La huella de todo lo que hay en una tabla: cuántas filas y qué valores.

    Es la misma cuenta que usa `database._huella_de_una_tabla` para comprobar una copia de seguridad
    (nombre de cada columna delante, y el `repr` de cada valor), escrita aquí para no depender de una
    función privada de otro módulo. `repr` distingue el `0` del `0.0` y del `None`, que es justo lo
    que hay que distinguir cuando se comprueba que una operación no ha tocado ni una fila.

    **Y se lee sin hablar el idioma de un solo motor** (02/10/2026). Antes se leían los nombres de las
    columnas con `PRAGMA table_info(...)` y las filas con `ORDER BY rowid`: las dos cosas son **de
    SQLite**, así que al correr la suite contra PostgreSQL —que es la base de producción— estas dos
    pruebas (`Test4EnsayarNoEscribe` y `Test5CompararNoEscribeNiInventa`) fallaban con
    `syntax error at or near "PRAGMA"`. Los nombres de las columnas y la clave los da el **modelo**, que
    es el mismo en los dos motores, y el orden de las filas se fija por la clave primaria, que es lo que
    hace que la huella sea **determinista** (sin un orden fijo, la misma tabla daría huellas distintas en
    cada lectura y la prueba no mediría nada).
    """
    del_modelo = models.Base.metadata.tables[tabla]
    columnas = [columna.name for columna in del_modelo.columns]
    claves = [columna.name for columna in del_modelo.primary_key.columns] or columnas[:1]
    orden = ", ".join(f'"{nombre}"' for nombre in claves)
    resumen = hashlib.sha256("|".join(columnas).encode("utf-8"))
    cuantas = 0
    for fila in conexion.execute(f'SELECT * FROM "{tabla}" ORDER BY {orden}'):
        resumen.update(b"\x1e")
        resumen.update("|".join(repr(valor) for valor in fila).encode("utf-8", "replace"))
        cuantas += 1
    resumen.update(b"\x1d")
    resumen.update(str(cuantas).encode("utf-8"))
    return resumen.hexdigest()


def _retrato_de_la_base() -> dict[str, str]:
    """La huella de **todas** las tablas del modelo, para medir antes y después.

    Se lee con el motor de la aplicación (el de los tests, que es temporal) y no con una copia del
    fichero: así lo que se mide es exactamente lo que ha quedado guardado después de las peticiones.
    """
    retrato: dict[str, str] = {}
    with engine.connect() as conexion:
        cruda = conexion.connection.driver_connection
        for tabla in models.Base.metadata.sorted_tables:
            retrato[tabla.name] = _huella_de_una_tabla(cruda, tabla.name)
    return retrato


def _sin_tildes(texto) -> str:
    """El mismo quitador de tildes que usa el buscador de la pantalla (`nucleo.sinTildes`).

    Mira el original: quita las tildes (`NFD` y fuera los diacríticos), pasa a minúsculas, **junta los
    espacios de dentro** y quita los de los extremos. Las tres cosas cuentan, y por eso se copian las
    tres: si la copia normalizara de menos, esta revisión mediría contra otra cosa.
    """
    plano = unicodedata.normalize("NFD", str(texto if texto is not None else ""))
    sin_acentos = "".join(caracter for caracter in plano if unicodedata.category(caracter) != "Mn")
    return re.sub(r"\s+", " ", sin_acentos).lower().strip()


# --- Lo que hacen las pantallas, leído de las pantallas ---------------------
#
# Estas tres funciones leen el JavaScript **de verdad** y sacan de ahí la regla con la que se juzga el
# servidor. Es a propósito: si mañana la pantalla cambia de criterio, estas pruebas tienen que decirlo
# en vez de seguir midiendo contra una copia que ya no es la que corre.


def _la_regla_de_las_hectareas_de_la_fila() -> str:
    """El campo del que sale lo que se lee en la columna «Hectáreas» de la tabla.

    `app.js` monta `superficie_texto` para cada fila y `tierras_mapa.js` enseña «Sin hectáreas dichas»
    cuando ese texto viene vacío. Se lee la línea del código en vez de suponerla.
    """
    fuente = APP_JS.read_text(encoding="utf-8")
    encontrado = re.search(r"superficie_texto: lasHectareasONada\(([^)]*)\)", fuente)
    assert encontrado is not None, (
        "no se encuentra en app.js la línea que prepara «superficie_texto» para la tabla de tierras: "
        "si ha cambiado, esta revisión tiene que volver a leerla antes de juzgar nada"
    )
    return encontrado.group(1)


def _la_fila_ensena_sin_hectareas(tierra: dict) -> bool:
    """Si la fila dice «Sin hectáreas dichas».

    `lasHectareasONada` (app.js) devuelve vacío con `null`, `undefined` o `""`, y solo con eso, así
    que la etiqueta sale exactamente cuando el valor viene vacío.
    """
    assert _la_regla_de_las_hectareas_de_la_fila().strip() == "tierra.superficie_ha", (
        "la columna de las hectáreas ya no se llena con `tierra.superficie_ha`: esta revisión estaba "
        "midiendo otra cosa"
    )
    return tierra.get("superficie_ha") in (None, "")


def _los_estados_de_revision_que_conoce_la_pantalla() -> list[str]:
    """La lista cerrada de estados con la que filtra la pantalla (`tierras_mapa.js`)."""
    fuente = TIERRAS_MAPA_JS.read_text(encoding="utf-8")
    encontrado = re.search(r"REVISIONES_CONOCIDAS = \[([^\]]*)\]", fuente)
    assert encontrado is not None, "no se encuentra REVISIONES_CONOCIDAS en tierras_mapa.js"
    return re.findall(r'"([^"]+)"', encontrado.group(1))


def _lo_que_deja_la_pantalla(tierras: list[dict], filtro: dict) -> list[dict]:
    """La misma criba que hace `filtrarLasTierras` (tierras_mapa.js), escrita en Python.

    Se copia aquí para poder contar en el servidor lo mismo que cuenta la pantalla. La copia se
    contrasta con el original en `test_la_criba_de_la_pantalla_es_la_que_se_esta_midiendo`, así que no
    es una copia libre: si el JavaScript cambia, esa prueba lo dice.
    """
    conocidos = _los_estados_de_revision_que_conoce_la_pantalla()
    revision = filtro.get("revision") if filtro.get("revision") in conocidos else ""
    buscado = _sin_tildes(filtro.get("q") or "").strip()
    # El pueblo y lo sembrado se cotejan **normalizados** (sin tildes, sin mayúsculas y con los
    # espacios de dentro juntos): es lo que hace `paraBuscar` = `nucleo.sinTildes` en la pantalla.
    pueblo = _sin_tildes(filtro.get("municipio") or "")
    sembrado = _sin_tildes(filtro.get("cultivo") or "")
    salida = []
    for tierra in tierras:
        if buscado:
            en_el_nombre = buscado in _sin_tildes(tierra.get("alias"))
            en_la_referencia = buscado in _sin_tildes(tierra.get("referencia"))
            if not en_el_nombre and not en_la_referencia:
                continue
        cultivo = filtro.get("cultivo")
        if cultivo == "sin_cultivo":
            if tierra.get("cultivo_clave"):
                continue
        elif sembrado and _sin_tildes(tierra.get("cultivo_clave")) != sembrado:
            continue
        municipio = filtro.get("municipio")
        if municipio == "sin_pueblo":
            if tierra.get("municipio"):
                continue
        elif pueblo and _sin_tildes(tierra.get("municipio")) != pueblo:
            continue
        if revision == "sin_version":
            if tierra.get("estado_revision"):
                continue
        elif revision and tierra.get("estado_revision") != revision:
            continue
        pac = filtro.get("pac")
        if pac == "con_referencia" and not tierra.get("tiene_referencia_completa"):
            continue
        if pac == "sin_referencia" and tierra.get("tiene_referencia_completa"):
            continue
        if pac == "con_hectareas" and not tierra.get("tiene_hectareas_dichas"):
            continue
        if pac == "sin_hectareas" and tierra.get("tiene_hectareas_dichas"):
            continue
        salida.append(tierra)
    return salida


def _todas_las_claves(dato, camino: str = "") -> list[str]:
    """Todas las claves de un JSON anidado, con su camino (`tierras[].alias`)."""
    claves: list[str] = []
    if isinstance(dato, dict):
        for clave, valor in dato.items():
            claves.append(f"{camino}.{clave}")
            claves.extend(_todas_las_claves(valor, f"{camino}.{clave}"))
    elif isinstance(dato, list):
        for valor in dato:
            claves.extend(_todas_las_claves(valor, f"{camino}[]"))
    return claves


def _todos_los_decimales(dato, camino: str = "") -> list[tuple[str, float]]:
    """Todos los valores decimales de un JSON anidado, con su camino."""
    encontrados: list[tuple[str, float]] = []
    if isinstance(dato, dict):
        for clave, valor in dato.items():
            encontrados.extend(_todos_los_decimales(valor, f"{camino}.{clave}"))
    elif isinstance(dato, list):
        for valor in dato:
            encontrados.extend(_todos_los_decimales(valor, f"{camino}[]"))
    elif type(dato) is float:
        encontrados.append((camino, dato))
    return encontrados


# ---------------------------------------------------------------------------
# 1. Los recuentos de la vista cuadran con las filas
# ---------------------------------------------------------------------------


class Test1LosRecuentosCuadranConLasFilas:
    """**El contrato más importante del ticket**: el pie y los filtros dicen lo mismo que la lista.

    Se prueba con tierras sin forma, sin cultivo, sin hectáreas, sin referencia y sin versión, que son
    las cinco cosas que el encargo nombra. Es la forma de los datos de verdad del agricultor (64
    tierras, ninguna con forma, 10 sin decir el cultivo): **no hace falta inventar geometrías**.
    """

    @pytest.fixture
    def una_finca_desigual(self, cliente, cuenta, crear_parcela):
        """Cinco tierras, cada una con un hueco distinto, y una sexta completa."""
        crear_parcela(alias="A sin forma", geometria=None, superficie_ha=None)
        crear_parcela(alias="B sin cultivo", geometria=None, superficie_ha=1.5)
        crear_parcela(alias="C con todo", poligono=503, numero_parcela=51, numero_recinto=1,
                      superficie_ha=2.4, municipio="Macotera")
        crear_parcela(alias="D sin pueblo", geometria=None, superficie_ha=0.9, municipio="")
        crear_parcela(alias="E sin referencia", poligono=None, numero_parcela=None,
                      numero_recinto=None, superficie_ha=3.1)
        return _vista(cliente, cuenta)

    def test_la_criba_de_la_pantalla_es_la_que_se_esta_midiendo(self):
        """La copia en Python de `filtrarLasTierras` tiene que ser la del JavaScript de verdad.

        Sin esta prueba, las de abajo medirían contra una copia que podría haberse quedado atrás —y
        una revisión que mide contra su propia copia no vale nada—. Se comprueban las seis marcas que
        de verdad deciden: los tres campos de texto **con su normalización**, la lista cerrada de
        revisiones y los dos pares de hechos de la PAC. Esta prueba se puso roja el 02/10/2026 a las
        18:20, cuando el fichero de la pantalla cambió de «cotejo literal» a «cotejo sin tildes»: hizo
        lo que tenía que hacer.
        """
        fuente = TIERRAS_MAPA_JS.read_text(encoding="utf-8")
        for trozo in (
            'filtro.cultivo === "sin_cultivo"',
            "paraBuscar(tierra.cultivo_clave) !== sembrado",
            "paraBuscar(tierra.municipio) !== pueblo",
            "tierra.estado_revision !== revision",
            "Boolean(tierra.tiene_referencia_completa)",
            "!tierra.tiene_hectareas_dichas",
            "paraBuscar(tierra.alias)",
            "paraBuscar(tierra.referencia)",
        ):
            assert trozo in fuente, f"la criba de la pantalla ya no dice «{trozo}»: revisa la copia"
        # Y la normalización de la pantalla es la de `nucleo.sinTildes`: tildes fuera, minúsculas y
        # espacios de dentro juntos. La copia de arriba tiene que hacer las tres cosas.
        assert _sin_tildes("  Peñaranda   DE Bracamonte ") == "penaranda de bracamonte"
        assert set(_los_estados_de_revision_que_conoce_la_pantalla()) == {
            "sin_revisar",
            "revisado",
            "con_dudas",
            "sin_version",
        }

    def test_cada_opcion_de_cada_filtro_deja_salir_las_tierras_que_dice(self, cliente, cuenta, una_finca_desigual):
        """**El número del filtro y las filas que salen al aplicarlo tienen que cuadrar, uno a uno.**

        Se recorre **cada** opción de los cuatro filtros (lo sembrado, el pueblo, la revisión y lo que
        se puede declarar), se aplica la misma criba que aplica la pantalla y se cuentan las filas.
        Si un filtro dijera 7 y salieran 6, el agricultor deja de fiarse de todo lo demás.
        """
        vista = una_finca_desigual
        tierras = vista["tierras"]
        filtros = vista["filtros"]
        campos = {
            "cultivos": "cultivo",
            "municipios": "municipio",
            "revisiones": "revision",
            "pac": "pac",
        }
        comprobadas = 0
        for grupo, campo in campos.items():
            for opcion in filtros[grupo]:
                salen = _lo_que_deja_la_pantalla(tierras, {campo: opcion["valor"]})
                assert len(salen) == opcion["cuantas"], (
                    f"el filtro «{grupo}.{opcion['valor']}» dice {opcion['cuantas']} y salen "
                    f"{len(salen)}: {[t['alias'] for t in salen]}"
                )
                comprobadas += 1
        # Y se han mirado de verdad: cinco huecos distintos tienen que dar opciones de sobra.
        assert comprobadas >= 6, f"solo se han comprobado {comprobadas} opciones de filtro"

    def test_el_pie_de_la_finca_entera_cuadra_con_las_filas(self, cliente, cuenta, una_finca_desigual):
        """Los recuentos del pie, uno por uno, contra lo que enseña cada fila.

        Aquí se miden los cuatro que se pueden medir sin discusión: el total, las que tienen forma
        (y su pareja «sin forma»), las que no dicen el cultivo y las que no tienen ninguna versión de
        este año. **El de las hectáreas se mide aparte**, en su propia prueba, porque ahí es donde
        está el defecto.
        """
        vista = una_finca_desigual
        tierras = vista["tierras"]
        totales = vista["totales"]

        assert totales["tierras"] == len(tierras)
        assert totales["con_forma"] + totales["sin_forma"] == totales["tierras"]
        assert totales["sin_forma"] == sum(1 for t in tierras if not t["tiene_forma"])
        # La fila enseña «SIN FORMA» exactamente cuando `tiene_forma` es falso.
        assert totales["sin_forma"] == sum(1 for t in tierras if not t["tiene_forma"])
        # Y la fila enseña «Sin decir qué tiene» exactamente cuando el texto del cultivo viene vacío.
        assert totales["sin_cultivo"] == sum(1 for t in tierras if not t["cultivo"])
        assert totales["sin_revision"] == sum(1 for t in tierras if t["estado_revision"] is None)

    def test_la_columna_de_las_hectareas_y_el_recuento_del_pie_usan_el_mismo_dato(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """**El contrato, escrito como contrato**: el pie cuenta lo mismo que enseñan las filas.

        Lo que dice esta prueba es una igualdad, no un número: *las tierras que el pie cuenta como «sin
        hectáreas dichas» tienen que ser exactamente las filas que enseñan esa etiqueta*, y el filtro
        tiene que ofrecerse cuando hay alguna y no ofrecerse cuando no hay ninguna.

        **Lo que encontró esta revisión (02/10/2026, sobre las 18:2x, y ya arreglado):** el servidor
        contaba «sin hectáreas dichas» con `tiene_hectareas_dichas`, que era
        `parcela.superficie_ha is not None **or** la versión del año tiene `area_declarada_ha``, mientras
        la columna «Hectáreas» de la tabla se llena **solo** con `superficie_ha` (`app.js`,
        `superficie_texto`) y `tierras_mapa.js` pinta «Sin hectáreas dichas» con el texto vacío. Una
        tierra importada del cuaderno de la Junta **sin la superficie cultivada** (queda en `None`, que
        es «no lo sé»: hallazgo A7 de `docs/T02_VALORES_POR_DEFECTO.md`) pero con las hectáreas que el
        agricultor declara en su versión, salía en la tabla con la etiqueta «Sin hectáreas dichas» y a
        la vez el pie decía que no había ninguna así y el filtro no se ofrecía: el agricultor que
        filtra por «sin hectáreas dichas» para saber qué le falta no ve la que le falta. El código se
        corrigió en `routers/parcelas.py` (`tiene_hectareas_dichas` ahora mira solo `superficie_ha`) y
        esta prueba se queda como el guardián de que las dos cosas no se vuelvan a separar.
        """
        parcela = crear_parcela(alias="De la Junta, sin superficie", geometria=None, superficie_ha=None)
        # El agricultor tiene declaradas las hectáreas de ese año: eso es una versión, y la versión
        # las trae. La superficie de la tierra sigue sin saberse.
        _importar(
            cliente,
            cuenta,
            campana["id"],
            [_un_recinto(parcela["id"], geometria=None, area_sigpac_ha=None, area_declarada_ha=2.5)],
            fuente="agricultor",
        )

        vista = _vista(cliente, cuenta)
        tierra = _tierra(vista["tierras"], "De la Junta, sin superficie")

        assert tierra["superficie_ha"] is None
        assert _la_fila_ensena_sin_hectareas(tierra), "esta prueba necesita una fila que diga «Sin hectáreas dichas»"
        assert tierra["area_declarada_ha"] == 2.5

        las_que_lo_ensenan = [t["alias"] for t in vista["tierras"] if _la_fila_ensena_sin_hectareas(t)]
        assert vista["totales"]["sin_hectareas"] == len(las_que_lo_ensenan), (
            f"el pie dice {vista['totales']['sin_hectareas']} tierras sin hectáreas dichas y hay "
            f"{len(las_que_lo_ensenan)} filas que enseñan esa etiqueta: {las_que_lo_ensenan}"
        )
        valores = [opcion["valor"] for opcion in vista["filtros"]["pac"]]
        assert ("sin_hectareas" in valores) == bool(las_que_lo_ensenan), (
            "el filtro «Sin hectáreas dichas» no sale cuando hay filas que lo dicen, o sale cuando no "
            f"hay ninguna (salen: {[o['texto'] for o in vista['filtros']['pac']]})"
        )

    def test_el_mismo_pueblo_escrito_de_dos_maneras_no_parte_el_recuento(self, cliente, cuenta, crear_parcela):
        """**DEFECTO (media).** El servidor junta las formas de escribirlo por mayúsculas y la pantalla también por tildes.

        **Qué pasa.** El 02/10/2026, a las 18:20, la pantalla cambió de cotejar el pueblo y lo sembrado
        «tal cual» a cotejarlos con `paraBuscar` (`nucleo.sinTildes`: **tildes fuera, minúsculas y los
        espacios de dentro juntos**), y el servidor se puso al día a medias: junta las opciones del
        filtro por `escrito.upper()` (`routers/parcelas.py`, `juntando_sin_mayusculas`), que quita las
        mayúsculas **pero no las tildes ni los espacios de dentro**. Las dos normalizaciones no son la
        misma, así que una tierra escrita «MACHACON» y otra «Machacón» salen como **dos opciones con su
        recuento partido**, y al elegir cualquiera de las dos la pantalla enseña las dos tierras: el
        número del filtro dice 3 y salen 4.

        **Y este caso está a un paso de sus datos, medido sobre la copia del agricultor**: en su
        cuaderno hay **3 tierras con el pueblo escrito `MACHACON`** (sin tilde: vienen del cuaderno de
        la Junta, que escribe lo que pone el papel) y la lista oficial del INE, que es de donde el
        formulario coge el pueblo cuando se elige, lo escribe **`Machacón`** (comprobado en
        `data/municipios_cyl.csv`). El día que apunte una tierra más eligiendo su pueblo de la lista,
        tendrá las dos formas en la misma finca.

        **Qué le pasa al agricultor.** Elige su pueblo en el filtro y ve dos entradas del mismo pueblo,
        una diciendo «3 tierras» que le enseña cuatro. Es el mismo daño que el del filtro que dice 7 y
        enseña 6: deja de creerse los números que acompañan a los filtros, que son justo los que usa
        para saber qué le falta por rellenar. (El segundo caso de la prueba, el de los dos espacios, es
        el mismo fallo por el otro lado: el agricultor teclea el nombre cuando no lo encuentra en la
        lista.)
        """
        crear_parcela(alias="Del cuaderno", municipio="MACHACON", geometria=None)
        crear_parcela(alias="Del cuaderno 2", municipio="MACHACON", geometria=None)
        crear_parcela(alias="Del cuaderno 3", municipio="MACHACON", geometria=None)
        crear_parcela(alias="De la lista oficial", municipio="Machacón", geometria=None)
        crear_parcela(alias="Con dos espacios", municipio="Calvarrasa  de Arriba", geometria=None)
        crear_parcela(alias="Con uno", municipio="Calvarrasa de Arriba", geometria=None)

        vista = _vista(cliente, cuenta)
        tierras = vista["tierras"]
        desajustes = []
        for opcion in vista["filtros"]["municipios"]:
            salen = _lo_que_deja_la_pantalla(tierras, {"municipio": opcion["valor"]})
            if len(salen) != opcion["cuantas"]:
                desajustes.append(
                    f"«{opcion['valor']}» dice {opcion['cuantas']} y salen {len(salen)} "
                    f"({[t['alias'] for t in salen]})"
                )

        assert desajustes == [], (
            "el filtro del pueblo y las filas que enseña no cuadran cuando el mismo pueblo está escrito "
            "de dos maneras: " + "; ".join(desajustes)
        )

    def test_lo_declarado_en_la_version_tiene_que_verse_donde_se_cuenta(self, cliente, cuenta, campana, crear_parcela):
        """**DEFECTO (baja).** `area_declarada_ha` se sirve en cada fila de la vista y no lo lee nadie.

        La vista manda, por cada tierra, **las hectáreas que el agricultor declara en su versión del
        año** (`TierraEnLaVista.area_declarada_ha`, y el comentario del esquema dice para qué: *«De ella
        salen el estado de revisión y las hectáreas declaradas»*). Buscado en todo `backend/web/`, ese
        dato **no lo lee ninguna pantalla**: la columna «Hectáreas» de la tabla se llena solo con
        `superficie_ha` (`app.js`, la línea de `superficie_texto`) y `tierras_mapa.js` no menciona
        `area_declarada_ha` en ningún sitio. Es la familia de fallo que `AGENTS.md` §4 llama «un dato
        que existe y no tiene puerta»: está en el modelo, viaja en la respuesta y no hay forma de verlo.

        **Qué le pasa al agricultor.** Declara las hectáreas de una tierra —es el dato que el cuaderno de
        la Junta pide aparte, «Superficie Cultivada»— y en la tabla de sus tierras no hay ni una columna
        donde aparezca: la que hay enseña la superficie del recinto, que es otra cosa. Si no se quiere
        enseñar ahí, lo coherente es no mandarla en esa respuesta; pero hoy se manda para que nadie la use.

        *(El recuento del pie **sí** la usaba cuando se encontró este hueco, y era el otro extremo del
        defecto de las hectáreas: al arreglarlo, este dato se ha quedado sin ningún uso en esa pantalla.)*
        """
        parcela = crear_parcela(alias="De la Junta, sin superficie", geometria=None, superficie_ha=None)
        _importar(
            cliente, cuenta, campana["id"],
            [_un_recinto(parcela["id"], geometria=None, area_sigpac_ha=None, area_declarada_ha=2.5)],
            fuente="agricultor",
        )

        vista = _vista(cliente, cuenta)
        tierra = _tierra(vista["tierras"], "De la Junta, sin superficie")
        assert tierra["area_declarada_ha"] == 2.5, "esta prueba necesita el dato servido en la fila"

        regla_de_la_columna = _la_regla_de_las_hectareas_de_la_fila()
        lee_la_pantalla = "area_declarada_ha" in TIERRAS_MAPA_JS.read_text(encoding="utf-8")

        assert "area_declarada_ha" in regla_de_la_columna or lee_la_pantalla, (
            "las hectáreas declaradas que trae la versión (`area_declarada_ha`) se sirven en cada fila "
            f"y no las enseña ninguna columna: la de hectáreas se llena con «{regla_de_la_columna}» y "
            "`tierras_mapa.js` no menciona ese dato en ningún sitio"
        )

    def test_dos_fuentes_del_mismo_ano_no_se_deciden_por_el_orden_de_importacion(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """**Lo que aguanta, medido**, y una frase del documento que no era lo que hacía el código.

        `docs/T06_MAPA_Y_TIERRA.md` §1.4 dice que de la versión salen el estado de revisión y las
        hectáreas declaradas y que es **«la más nueva de la campaña que se está llevando, y una sola
        por tierra»**. El código (`routers/parcelas.py`) cogía la primera que salía de una consulta
        ordenada por `(parcela_id, clave)` y se quedaba con ella (`versiones.setdefault`); dos versiones
        del mismo año con la misma clave —el SIGPAC y el agricultor, que el propio ticket dice que es
        un caso normal— **empataban**, así que decidía el orden interno de la base.

        **Aquí se intentó romper por ahí con SQLite y no se pudo**, y eso quedó escrito como una
        limitación: el ganador (medido: la versión del `fuente` que va antes por orden alfabético, o sea
        `agricultor` antes que `sigpac`) era estable en SQLite, y encima era la dirección buena —lo que
        declara el agricultor manda sobre lo que dice el SIGPAC—, pero **no había ninguna línea que
        dijera que eso era lo que se quería**: era el orden que le salía al plan de la consulta.

        **Y el 02/10/2026, al correr la suite entera contra PostgreSQL, esta prueba se puso roja**: en el
        motor de producción el plan devolvía la otra, así que la misma tierra enseñaba
        `sin_revisar/SIGPAC/None` en vez de `revisado/lo que dijiste tú/2.5`. **El defecto era real y
        estaba en producción**, invisible desde SQLite. El arreglo está en el código y no aquí: el
        desempate es ahora explícito (`versiones_de_recinto.PRIORIDAD_DE_FUENTES`: lo medido en el campo,
        lo que declara el agricultor, su cuaderno de la Junta y por último la importación oficial), así
        que el resultado **no depende de cómo se llame el motor ni del orden en que se importó**.

        Esta prueba se queda exactamente como estaba —es la que destapó el fallo—; lo que cambió es lo
        que mide: antes comprobaba, sin saberlo, el orden que le salía a la base; ahora comprueba una
        regla escrita.
        """
        una = crear_parcela(alias="Gemela A", geometria=None, superficie_ha=None)
        otra = crear_parcela(alias="Gemela B", geometria=None, superficie_ha=None)

        # A: primero el SIGPAC (sin revisar) y después el agricultor (revisado, con sus hectáreas).
        _importar(
            cliente, cuenta, campana["id"],
            [_un_recinto(una["id"], poligono=503, numero_parcela=51, numero_recinto=1,
                         area_declarada_ha=None, estado_revision=None)],
            fuente="sigpac",
        )
        _importar(
            cliente, cuenta, campana["id"],
            [_un_recinto(una["id"], poligono=503, numero_parcela=51, numero_recinto=1,
                         area_declarada_ha=2.5, estado_revision="revisado")],
            fuente="agricultor",
        )
        # B: los mismos dos, en el orden contrario.
        _importar(
            cliente, cuenta, campana["id"],
            [_un_recinto(otra["id"], poligono=503, numero_parcela=51, numero_recinto=1,
                         area_declarada_ha=2.5, estado_revision="revisado")],
            fuente="agricultor",
        )
        _importar(
            cliente, cuenta, campana["id"],
            [_un_recinto(otra["id"], poligono=503, numero_parcela=51, numero_recinto=1,
                         area_declarada_ha=None, estado_revision=None)],
            fuente="sigpac",
        )

        vista = _vista(cliente, cuenta)
        primera = _tierra(vista["tierras"], "Gemela A")
        segunda = _tierra(vista["tierras"], "Gemela B")
        assert len(_las_versiones(cliente, cuenta, parcela_id=primera["id"])) == 2
        assert len(_las_versiones(cliente, cuenta, parcela_id=segunda["id"])) == 2

        assert (primera["estado_revision"], primera["fuente_texto"], primera["area_declarada_ha"]) == (
            segunda["estado_revision"],
            segunda["fuente_texto"],
            segunda["area_declarada_ha"],
        ), (
            "dos tierras idénticas, con las mismas dos versiones del mismo año, enseñan cosas distintas "
            "según el orden en que se importaron: "
            f"A={primera['estado_revision']}/{primera['fuente_texto']}/{primera['area_declarada_ha']} y "
            f"B={segunda['estado_revision']}/{segunda['fuente_texto']}/{segunda['area_declarada_ha']}"
        )


# ---------------------------------------------------------------------------
# 2. Una tierra sin forma no desaparece, y al mapa no se le inventa nada
# ---------------------------------------------------------------------------


class Test2LaTierraSinFormaYElMapa:
    def test_sin_ninguna_forma_no_hay_caja_ni_un_centro_inventado(self, cliente, cuenta, crear_parcela):
        """**Datos reales por su forma**: es la finca del agricultor (ninguna tierra con forma).

        Sin ninguna forma medida no hay nada que dibujar, y la respuesta no puede traer ni una
        coordenada por la que abrir el mapa: ni una caja, ni un centro, ni un rincón por defecto. Se
        comprueba que **no hay ningún decimal en toda la respuesta**, que es la forma más fuerte de
        decir «aquí no se ha inventado ningún sitio».
        """
        crear_parcela(alias="Sin forma 1", geometria=None, superficie_ha=None)
        crear_parcela(alias="Sin forma 2", geometria=None, superficie_ha=None)

        vista = _vista(cliente, cuenta)

        assert vista["mapa"]["hay_forma"] is False
        assert vista["mapa"]["caja"] is None
        assert vista["mapa"]["tierras_con_forma"] == 0
        assert [t["anillos"] for t in vista["tierras"]] == [[], []]
        assert [t["tiene_forma"] for t in vista["tierras"]] == [False, False]
        decimales = _todos_los_decimales(vista)
        assert decimales == [], f"sin formas, la respuesta no puede traer coordenadas: {decimales}"

    def test_la_caja_envuelve_todas_las_formas_y_no_se_queda_corta(self, cliente, cuenta, crear_parcela):
        """**Con formas sintéticas** (en los datos reales no hay ninguna): la envolvente las contiene todas.

        El contrato 2 lo dice así: «con formas la caja tiene que contenerlas todas». Se comprueba contra
        **los anillos que la propia respuesta manda**, uno por uno, y contra **el campo que la respuesta
        declara como la envolvente** (`extension` si está, y si no `caja`), que es lo que hace que la
        prueba siga valiendo si mañana se le cambia el nombre.

        **Por dónde se ha atacado, y qué pasó de verdad.** El 02/10/2026, sobre las 18:35, la caja pasó
        a ser «la parte que se puede pedir» (recortada al medio grado que acepta el servicio de mapas,
        que es el arreglo del defecto D7) y las tierras de fuera **se salían de ella**: la respuesta
        decía que esa caja envolvía las formas y no era verdad. La prueba se puso roja (esta misma, con
        un multipolígono partido en dos trozos a un grado de distancia) y el arreglo fue añadir
        `extension`, la envolvente sin recortar. Lo que exige la prueba es la invariante, no un nombre:
        **si un campo dice envolver todas las formas, las envuelve**.
        """
        multiparte = (
            "MULTIPOLYGON(((-5.56 40.90, -5.55 40.90, -5.55 40.91, -5.56 40.91, -5.56 40.90)),"
            "((-4.56 40.80, -4.55 40.80, -4.55 40.81, -4.56 40.81, -4.56 40.80)))"
        )
        crear_parcela(alias="Partida en dos", geometria=multiparte)
        crear_parcela(alias="Otra", geometria=OTRO_WKT)

        vista = _vista(cliente, cuenta)
        mapa = vista["mapa"]
        envolvente = mapa.get("extension") or mapa.get("caja")

        assert envolvente is not None, "con formas, la respuesta tiene que decir por dónde se abre el mapa"
        for tierra in vista["tierras"]:
            for anillo in tierra["anillos"]:
                for longitud, latitud in anillo:
                    assert envolvente["oeste"] <= longitud <= envolvente["este"], (
                        f"«{tierra['alias']}» se sale por el oeste de la caja que dice envolver las formas"
                    )
                    assert envolvente["sur"] <= latitud <= envolvente["norte"], (
                        f"«{tierra['alias']}» se sale por el sur de la caja que dice envolver las formas"
                    )

    def test_los_dos_recuentos_de_forma_de_la_misma_respuesta_cuadran(self, cliente, cuenta, crear_parcela):
        """**DEFECTO (baja).** La misma respuesta dice «0 tierras con forma» y «1 tierra con forma».

        `totales.con_forma` cuenta las tierras con anillos **de verdad** (`tiene_forma`, que sale de
        `geo.anillos_de_un_wkt`), y `mapa.tierras_con_forma` cuenta las que tienen **el texto de la
        geometría** (`routers/parcelas.py`, `_el_mapa_de_la_finca`:
        `sum(1 for tierra in tierras if tierra.geometria)`). Son dos cosas distintas: una geometría
        puede estar escrita y no tener ni un anillo —un `POINT`, una línea o un polígono degenerado—,
        y entonces los dos números de la misma respuesta se contradicen. Además, `hay_forma` es falso
        con `tierras_con_forma` en 1, que es afirmar y negar lo mismo en dos campos seguidos.

        Lo pide el contrato 1 de esta revisión con sus palabras: los recuentos de la vista tienen que
        cuadrar con las filas. Hoy este campo no lo lee ninguna pantalla (se ha buscado en
        `backend/web/`), así que es **baja**: es una cifra que el servidor da mal y que el día que
        alguien pinte en pantalla dirá lo contrario que el pie.
        """
        crear_parcela(alias="Con un punto", geometria=WKT_DE_UN_PUNTO)
        crear_parcela(alias="Con forma", geometria=UN_WKT)

        vista = _vista(cliente, cuenta)

        assert vista["totales"]["con_forma"] == 1, "esta prueba necesita una sola tierra con anillos"
        assert vista["mapa"]["tierras_con_forma"] == vista["totales"]["con_forma"], (
            "la misma respuesta cuenta "
            f"{vista['mapa']['tierras_con_forma']} tierras con forma en el mapa y "
            f"{vista['totales']['con_forma']} en los totales de la tabla; y `hay_forma` dice "
            f"{vista['mapa']['hay_forma']} con una tierra que tiene geometría escrita y ningún anillo"
        )


# ---------------------------------------------------------------------------
# 3. Un dato ausente no es cero
# ---------------------------------------------------------------------------


class Test3UnDatoAusenteNoEsCero:
    def test_una_tierra_sin_superficie_no_se_convierte_en_cero_hectareas(self, cliente, cuenta, crear_parcela):
        """`None` es «no lo sé» y no un cero, ni en la tierra ni en lo que suma T06.

        Se mira la respuesta entera: ninguna cifra de superficie puede aparecer como `0.0` en una
        tierra cuya superficie no se sabe, y no puede haber ningún total de hectáreas (que es la otra
        forma de inventar: sumar los huecos como cero).
        """
        crear_parcela(alias="Sin hectáreas", superficie_ha=None, geometria=None)
        crear_parcela(alias="Con hectáreas", superficie_ha=2.43, geometria=None)

        vista = _vista(cliente, cuenta)
        sin = _tierra(vista["tierras"], "Sin hectáreas")

        assert sin["superficie_ha"] is None
        assert sin["superficie_sigpac_ha"] is None
        assert sin["area_declarada_ha"] is None
        assert not any(
            type(valor) is float and valor == 0.0
            for _, valor in _todos_los_decimales(vista)
        ), "hay un 0,0 en la respuesta de una finca donde no se ha medido nada que sea cero"

    def test_una_tierra_sin_version_no_se_cuenta_como_sin_revisar(self, cliente, cuenta, crear_parcela, campana):
        """«Sin revisar» y «sin ninguna versión» no son lo mismo, y el pie no los mezcla.

        Es la misma regla que el filtro: decir «sin revisar» de una tierra de la que nadie ha dicho
        nada afirmaría que alguien la miró. Se comprueba que el estado de revisión **no se rellena**
        cuando no hay versión, y que el recuento del pie usa `None` y no `sin_revisar`.
        """
        crear_parcela(alias="Sin versiones", geometria=None)

        vista = _vista(cliente, cuenta)
        tierra = _tierra(vista["tierras"], "Sin versiones")

        assert tierra["estado_revision"] is None
        assert tierra["estado_revision_texto"] is None
        assert tierra["anio_de_la_version"] is None
        assert tierra["fuente_texto"] is None
        assert vista["totales"]["sin_revision"] == 1
        # Y la campaña sí se dice, aunque ninguna tierra tenga versión suya.
        assert vista["campana_anio"] == campana["anio"]


# ---------------------------------------------------------------------------
# 4. Ensayar una importación no escribe
# ---------------------------------------------------------------------------


class Test4EnsayarNoEscribe:
    def test_previsualizar_cien_veces_no_cambia_ni_una_fila(self, cliente, cuenta, campana, crear_parcela):
        """Cien previsualizaciones y la huella de **todas** las tablas igual, antes y después.

        Es la medida entera y no una muestra: se guarda la huella de cada tabla del modelo (cuántas
        filas, los nombres de las columnas y el `repr` de cada valor) antes de empezar y se compara al
        terminar. Se incluye lo que el contrato nombra: ninguna versión nueva, ninguna fila tocada y
        **ni un apunte de auditoría**.
        """
        parcela = crear_parcela(alias="El Prado", geometria=None, superficie_ha=None)
        _importar(
            cliente, cuenta, campana["id"],
            [_un_recinto(parcela["id"], geometria=None, area_sigpac_ha=0.93)],
            fuente="sigpac",
        )
        antes = _retrato_de_la_base()
        versiones_antes = len(_las_versiones(cliente, cuenta))

        lote = {
            "campana_id": campana["id"],
            "fuente": "cuaderno_de_la_junta",
            "recintos": [
                _un_recinto(parcela["id"], poligono=503, numero_parcela=51, numero_recinto=2,
                            geometria=None, area_declarada_ha=0.9),
            ],
        }
        for _ in range(100):
            respuesta = cliente.post(
                "/api/versiones/previsualizar", headers=cuenta["cabeceras"], json=lote
            )
            assert respuesta.status_code == 200, respuesta.text
            assert respuesta.json()["aplicada"] is False

        despues = _retrato_de_la_base()
        cambiadas = [tabla for tabla in antes if antes[tabla] != despues[tabla]]
        assert cambiadas == [], f"ensayar cien veces ha cambiado {cambiadas}"
        assert len(_las_versiones(cliente, cuenta)) == versiones_antes

    def test_el_ensayo_ensena_el_mismo_plan_que_el_apunte_de_verdad(self, cliente, cuenta, campana, crear_parcela):
        """Lo que se enseña antes de apuntar no puede diferir de lo que pasa después."""
        parcela = crear_parcela(alias="El Prado", geometria=None, superficie_ha=None)
        recintos = [_un_recinto(parcela["id"], geometria=None, area_sigpac_ha=0.93)]

        ensayo = _ensayar(cliente, cuenta, campana["id"], recintos)
        aplicado = _importar(cliente, cuenta, campana["id"], recintos)

        for campo in ("nuevos", "cambiados", "iguales", "sin_forma", "recintos_en_el_lote"):
            assert ensayo[campo] == aplicado[campo], f"el ensayo y el apunte no dicen lo mismo de «{campo}»"
        assert ensayo["aplicada"] is False and aplicado["aplicada"] is True


# ---------------------------------------------------------------------------
# 5. Comparar dos campañas no escribe y no se inventa los estados
# ---------------------------------------------------------------------------


class Test5CompararNoEscribeNiInventa:
    def test_los_cuatro_estados_salen_de_los_datos(self, cliente, cuenta, campana, crear_parcela):
        """`igual / cambiado / desaparecido / nuevo`, uno de cada, montados a mano.

        Se monta una finca de tres tierras y dos campañas: una versión igual en las dos, una que
        cambia (la forma), una que solo está en el año viejo y una que solo está en el nuevo. Después
        se cuenta lo que dice la comparación y se compara con lo que hay: los cuatro números tienen
        que ser 1, 1, 1 y 1. **Con formas sintéticas**, porque en los datos reales no hay ninguna.
        """
        la_igual = crear_parcela(alias="Igual", geometria=None)
        la_cambiada = crear_parcela(alias="Cambiada", geometria=None)
        la_que_se_va = crear_parcela(alias="Se va", geometria=None)
        la_nueva = crear_parcela(alias="Nueva", geometria=None)
        antes = _crear_campana(cliente, cuenta, 2025)
        despues = campana

        _importar(cliente, cuenta, antes["id"], [
            _un_recinto(la_igual["id"]),
            _un_recinto(la_cambiada["id"], numero_recinto=2),
            _un_recinto(la_que_se_va["id"], numero_recinto=3),
        ])
        _importar(cliente, cuenta, despues["id"], [
            _un_recinto(la_igual["id"]),
            _un_recinto(la_cambiada["id"], numero_recinto=2, area_sigpac_ha=3.1),
            _un_recinto(la_nueva["id"], numero_recinto=4),
        ])

        respuesta = cliente.get(
            "/api/versiones/comparar-explotacion",
            headers=cuenta["cabeceras"],
            params={"campana_antes": antes["id"], "campana_despues": despues["id"]},
        )

        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert (datos["iguales"], datos["cambiados"], datos["desaparecidos"], datos["nuevos"]) == (1, 1, 1, 1)
        assert datos["iguales"] + datos["cambiados"] + datos["desaparecidos"] + datos["nuevos"] == len(
            datos["cambios"]
        )
        # Y el porqué de cada uno, que es la mitad del valor: el cambiado dice **qué** cambió.
        cambiado = next(c for c in datos["cambios"] if c["estado"] == "cambiado")
        assert cambiado["que_cambio"], "un recinto cambiado sin decir qué cambió"
        assert all(c["que_cambio"] == [] for c in datos["cambios"] if c["estado"] == "igual")

    def test_comparar_veinte_veces_no_cambia_ni_una_fila(self, cliente, cuenta, campana, crear_parcela):
        """Comparar solo lee: veinte veces y las huellas de todas las tablas iguales."""
        parcela = crear_parcela(alias="El Prado", geometria=None)
        antes = _crear_campana(cliente, cuenta, 2025)
        _importar(cliente, cuenta, antes["id"], [_un_recinto(parcela["id"], area_sigpac_ha=0.9)])
        _importar(cliente, cuenta, campana["id"], [_un_recinto(parcela["id"], area_sigpac_ha=0.95)])
        retrato = _retrato_de_la_base()

        for _ in range(20):
            respuesta = cliente.get(
                "/api/versiones/comparar",
                headers=cuenta["cabeceras"],
                params={
                    "parcela_id": parcela["id"],
                    "campana_antes": antes["id"],
                    "campana_despues": campana["id"],
                },
            )
            assert respuesta.status_code == 200, respuesta.text
            assert (respuesta.json()["iguales"], respuesta.json()["cambiados"]) == (0, 1)

        assert _retrato_de_la_base() == retrato, "comparar veinte veces ha escrito algo"

    def test_sin_versiones_las_dos_campanas_dan_cero_y_no_dicen_que_todo_esta_bien(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """Una lista vacía no puede leerse como «todo bien»: 0 de todo, y el porqué a la vista.

        Con dos campañas y ninguna versión, la comparación no puede inventarse un estado ni decir que
        no ha cambiado nada como si hubiera mirado algo: son cuatro ceros sobre cero recintos, y la
        pantalla (que es quien lo sabe) dice que no hay versiones de dos años. Aquí se comprueba la
        mitad del servidor: que no hay ni un cambio inventado y que los cuatro números son cero.
        """
        crear_parcela(alias="Sin versiones", geometria=None)
        antes = _crear_campana(cliente, cuenta, 2025)

        respuesta = cliente.get(
            "/api/versiones/comparar-explotacion",
            headers=cuenta["cabeceras"],
            params={"campana_antes": antes["id"], "campana_despues": campana["id"]},
        )

        datos = respuesta.json()
        assert (datos["iguales"], datos["cambiados"], datos["desaparecidos"], datos["nuevos"]) == (0, 0, 0, 0)
        assert datos["cambios"] == []


# ---------------------------------------------------------------------------
# 6. Aislamiento entre explotaciones: 404, no 403
# ---------------------------------------------------------------------------


class Test6AislamientoEntreFincas:
    @pytest.fixture
    def otra_finca_con_datos(self, cliente, crear_cuenta):
        """Otra finca de verdad, con su tierra, su campaña y su versión: identificadores reales."""
        otro = crear_cuenta(correo="otro@ejemplo.test", nombre="Otro", nif="12345678Z")
        campana = cliente.get("/api/campanas/actual", headers=otro["cabeceras"]).json()
        respuesta = cliente.post(
            "/api/parcelas",
            headers=otro["cabeceras"],
            json={"alias": "Del otro", "geometria": UN_WKT, "superficie_ha": 9.9},
        )
        assert respuesta.status_code == 201, respuesta.text
        parcela = respuesta.json()
        respuesta = cliente.post(
            "/api/versiones/aplicar",
            headers=otro["cabeceras"],
            json={"campana_id": campana["id"], "fuente": "sigpac", "recintos": [_un_recinto(parcela["id"])]},
        )
        assert respuesta.status_code == 200, respuesta.text
        return {"cuenta": otro, "campana": campana, "parcela": parcela}

    def test_la_vista_no_ve_ni_una_tierra_de_la_otra_finca(self, cliente, cuenta, crear_parcela, otra_finca_con_datos):
        """Ni las tierras, ni sus anillos, ni su caja: la caja tampoco puede envolver una tierra ajena."""
        crear_parcela(alias="Mía", geometria=OTRO_WKT)

        vista = _vista(cliente, cuenta)

        assert [t["alias"] for t in vista["tierras"]] == ["Mía"]
        assert vista["totales"]["tierras"] == 1
        assert vista["mapa"]["tierras_con_forma"] == 1
        caja = vista["mapa"]["caja"]
        assert caja["oeste"] >= -5.51 and caja["este"] <= -5.48, (
            "la caja de mi finca envuelve la forma de una tierra de otra finca"
        )

    def test_las_versiones_de_una_tierra_ajena_contestan_404_y_no_403(self, cliente, cuenta, otra_finca_con_datos):
        """`404`, no `403`: no se dice si ese identificador existe en el cuaderno de otro."""
        ajena = otra_finca_con_datos["parcela"]["id"]

        respuesta = cliente.get("/api/versiones", headers=cuenta["cabeceras"], params={"parcela_id": ajena})

        assert respuesta.status_code == 404, respuesta.text
        assert respuesta.status_code != 403

    def test_las_versiones_de_una_campana_ajena_contestan_404(self, cliente, cuenta, otra_finca_con_datos):
        respuesta = cliente.get(
            "/api/versiones",
            headers=cuenta["cabeceras"],
            params={"campana_id": otra_finca_con_datos["campana"]["id"]},
        )

        assert respuesta.status_code == 404, respuesta.text

    def test_comparar_con_una_tierra_o_una_campana_ajena_contesta_404(self, cliente, cuenta, campana, otra_finca_con_datos):
        """Las dos puertas de la comparación: la tierra y las dos campañas."""
        respuesta = cliente.get(
            "/api/versiones/comparar",
            headers=cuenta["cabeceras"],
            params={
                "parcela_id": otra_finca_con_datos["parcela"]["id"],
                "campana_antes": campana["id"],
                "campana_despues": campana["id"],
            },
        )
        assert respuesta.status_code == 404, respuesta.text

        respuesta = cliente.get(
            "/api/versiones/comparar-explotacion",
            headers=cuenta["cabeceras"],
            params={
                "campana_antes": otra_finca_con_datos["campana"]["id"],
                "campana_despues": campana["id"],
            },
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_la_vista_pide_sesion_y_el_mapa_no_lleva_datos_de_nadie(self, cliente, cuenta, crear_parcela):
        """La vista es del agricultor y sin vale no se abre; el mapa es de datos oficiales.

        `/api/mapa/estado` se sirve sin sesión **a propósito** (lo dice su docstring: no lleva datos
        de nadie), así que lo que hay que comprobar no es que pida sesión sino que de verdad no lleve
        ni un dato de la finca: ni una tierra, ni un identificador, ni un nombre.
        """
        crear_parcela(alias="El Prado secreto", geometria=UN_WKT)

        sin_vale = cliente.get("/api/parcelas/vista")
        assert sin_vale.status_code == 401, sin_vale.text

        estado = cliente.get("/api/mapa/estado")
        assert estado.status_code == 200
        crudo = json.dumps(estado.json(), ensure_ascii=False)
        assert "El Prado secreto" not in crudo, "el estado del mapa lleva el nombre de una tierra de la finca"
        # Y ninguna clave de la respuesta es una lista de tierras ni un identificador de la finca.
        claves = set(_todas_las_claves(estado.json()))
        assert not [clave for clave in claves if clave.endswith(".alias") or clave.endswith(".parcela_id")], (
            f"el estado del mapa lleva datos de la finca: {sorted(claves)}"
        )
        assert "tierras" not in estado.json(), "el estado del mapa no puede devolver tierras"


# ---------------------------------------------------------------------------
# 7. Las capas del mapa
# ---------------------------------------------------------------------------


class Test7LasCapasDelMapa:
    def test_cada_capa_dice_que_ensena_de_quien_es_y_de_cuando(self, cliente):
        """La leyenda, el servicio y la fecha salen del servidor y **cada capa dice lo suyo**.

        Se comprueba que las tres leyendas son distintas entre sí (una leyenda que valiera para las
        tres no diría nada), que salen de `textos.py` —donde vive todo lo que lee el agricultor—, y
        que la fecha no se inventa: no hay fecha y se dice por qué.
        """
        datos = cliente.get("/api/mapa/estado").json()
        leyendas = [capa["leyenda"] for capa in datos["capas"].values()]

        assert len(set(leyendas)) == 3, "dos capas distintas dicen lo mismo, así que la leyenda no informa"
        for capa in datos["capas"].values():
            assert capa["leyenda"] in textos.TIERRA_Y_MAPA.values(), "una leyenda escrita fuera de textos.py"
            assert capa["servicio"].strip(), "una capa sin decir de quién es"
            assert capa["fecha"] is None, "la capa trae una fecha que ningún servicio publica"
            assert capa["fecha_texto"] == textos.TIERRA_Y_MAPA["fecha_sin_saber"]
        assert datos["leyenda_de_mis_tierras"] == textos.TIERRA_Y_MAPA["leyenda_mis_tierras"]

    def test_lo_que_hace_falta_para_decir_que_una_capa_no_se_puede_ocultar_lo_lee_alguien(self):
        """**DEFECTO (baja).** `se_puede_ocultar` se sirve y no lo lee ninguna pantalla.

        El contrato de T06 pide «que una capa que no se puede ocultar lo diga». El servidor contesta
        `se_puede_ocultar` (hoy `true` en las tres, escrito a mano en `routers/mapa.py`), y **no hay
        ni una línea en `backend/web/` que lea ese campo**: se ha buscado en todo el JavaScript y solo
        aparece en el servidor y en las pruebas. Es decir, el día que una capa no se pueda quitar, el
        agricultor no tendrá forma de saberlo: el dato está y no tiene puerta (la familia de fallo que
        `AGENTS.md` §4 describe como la que más se repite en este proyecto).

        Lo que le pasa al agricultor hoy: nada, porque las tres se pueden quitar. Por eso es baja. Lo
        que se está comprobando aquí es que **no hay ninguna forma de que se lo diga**.
        """
        fuentes = "\n".join(
            fichero.read_text(encoding="utf-8")
            for fichero in (RAIZ / "web").rglob("*.js")
        )
        assert "se_puede_ocultar" not in fuentes, (
            "ninguna pantalla lee `se_puede_ocultar`: el aviso de «esta capa no se puede quitar» no "
            "existe en la interfaz, y el campo que lo haría posible se sirve para nada"
        )

    def test_cuando_el_servicio_del_mapa_no_esta_se_dice_y_no_se_sirve_media_imagen(self, cliente, monkeypatch):
        """**Con un doble**: el programa no depende de internet para probar esto.

        Se sustituye la llamada al servicio de fuera por una que falla, y se comprueba que el
        agricultor recibe un aviso en castellano (el mismo texto que enseña la pantalla) y no una
        imagen rota ni un 200 con un cuerpo que no es una imagen.
        """
        from app import sigpac
        from app.routers import mapa

        def no_contesta(*_argumentos, **_cambios):
            raise sigpac.SigpacNoContesta("el servicio no está")

        monkeypatch.setattr(sigpac, "pedir_imagen_del_mapa", no_contesta)

        respuesta = cliente.get(
            "/api/mapa/imagen",
            params={"capa": "foto", "oeste": -5.56, "sur": 40.90, "este": -5.55, "norte": 40.91},
        )

        assert respuesta.status_code == 503, respuesta.text
        assert respuesta.json()["detail"] == textos.MAPA["sin_conexion"]
        assert not respuesta.headers.get("content-type", "").startswith("image/"), (
            "se ha servido como imagen una respuesta que no lo es"
        )
        assert mapa.LADO_MINIMO_GRADOS > 0  # el import sigue siendo el del programa

    def test_la_caja_que_da_la_vista_la_tiene_que_aceptar_el_mismo_programa(self, cliente, cuenta, crear_parcela, monkeypatch):
        """**DEFECTO (media), encontrado y arreglado durante la revisión.** La vista daba una caja que el propio programa rechazaba.

        **Lo que pasaba.** `_el_mapa_de_la_finca` agrandaba la caja si era **más pequeña** que el mínimo
        que acepta el servicio de mapas, pero **no la recortaba si era más grande** que el máximo
        (`mapa.LADO_MAXIMO_GRADOS`, 0,5 grados: unos 55 km de norte a sur y unos 42 de este a oeste).
        `/api/mapa/imagen` sí lo comprueba y contesta **422**. El servidor entregaba a la pantalla una
        caja que él mismo no servía.

        **Qué le pasaba al agricultor.** Abre el mapa de sus tierras y no ve ninguna foto: el `<img>`
        falla y el aviso que lee es el de «no se ha podido traer la imagen… puede ser la cobertura o que
        el servicio no conteste» (`textos.TIERRA_Y_MAPA["imagen_no_llega"]`), que es **mentira**: su
        cobertura está bien y el servicio contesta; lo que pasa es que su finca es más ancha de lo que
        este programa sabe enseñar de una vez. Se queda sin mapa y con una pista que no lleva a ningún
        sitio.

        **Con formas sintéticas**, y a propósito: una explotación con tierras a 60 km unas de otras es de
        lo más normal en Castilla y León —es justo el caso contra el que el contrato avisa («el mapa no
        debe saltar a otra provincia»)—, y en los datos reales del agricultor esto no se puede ver porque
        **no tiene ni una forma medida** (0 de 64).

        **Cómo se arregló (02/10/2026, sobre las 18:35)**: la caja que se devuelve se queda en el máximo
        que el servicio acepta y la respuesta dice que la finca no cabe entera
        (`se_puede_ensenar_entera`), con la finca completa aparte (`extension`); la pantalla lee ese
        aviso y lo dice en el mapa. Esta prueba exige las dos mitades: **que la caja que da la vista se
        pueda pedir** y que, si la finca no cabe, se diga y la pantalla lo lea.
        """
        # Solo se sustituye el proveedor externo. La caja y el endpoint siguen siendo reales.
        import io
        from PIL import Image
        from app import sigpac

        imagen = io.BytesIO()
        Image.new("RGB", (1, 1)).save(imagen, format="PNG")
        llamadas = []

        def proveedor(capa, oeste, sur, este, norte, ancho, alto):
            llamadas.append((capa, oeste, sur, este, norte, ancho, alto))
            return imagen.getvalue(), "image/png"

        monkeypatch.setattr(sigpac, "pedir_imagen_del_mapa", proveedor)
        crear_parcela(alias="Al oeste", geometria=UN_WKT)
        crear_parcela(alias="Al este", geometria=WKT_MUY_AL_ESTE)

        vista = _vista(cliente, cuenta)
        mapa = vista["mapa"]
        caja = mapa["caja"]
        lado = max(caja["este"] - caja["oeste"], caja["norte"] - caja["sur"])

        respuesta = cliente.get(
            "/api/mapa/imagen",
            params={
                "capa": "foto",
                "oeste": caja["oeste"],
                "sur": caja["sur"],
                "este": caja["este"],
                "norte": caja["norte"],
                "ancho": 900,
                "alto": 600,
            },
        )
        assert respuesta.status_code == 200, (
            f"la vista da una caja de {lado:.3f} grados y el propio programa la rechaza con "
            f"{respuesta.status_code}. La pantalla, delante de ese fallo, enseña «puede ser la cobertura», "
            "que no es lo que pasa"
        )

        assert respuesta.content == imagen.getvalue()
        assert respuesta.headers["content-type"].startswith("image/png")
        assert llamadas == [("foto", caja["oeste"], caja["sur"], caja["este"], caja["norte"], 900, 600)]

        # Y la otra mitad: si esta finca es más ancha que lo que el servicio acepta, la respuesta tiene
        # que decirlo y la pantalla tiene que leerlo.
        extension = mapa.get("extension") or caja
        ancho_de_verdad = max(extension["este"] - extension["oeste"], extension["norte"] - extension["sur"])
        if ancho_de_verdad > 0.5:
            assert mapa.get("se_puede_ensenar_entera") is False, (
                "la finca mide más de medio grado (no se puede enseñar de una vez en una imagen) y la "
                "respuesta no lo dice"
            )
            assert "se_puede_ensenar_entera" in APP_JS.read_text(encoding="utf-8"), (
                "la vista dice que la finca no cabe entera y la pantalla no lee ese aviso: pediría la "
                "imagen con una caja que el programa rechaza y el agricultor leería «puede ser la "
                "cobertura» delante de un fallo que no tiene que ver con la cobertura"
            )


# ---------------------------------------------------------------------------
# 8. Ni una cifra inventada
# ---------------------------------------------------------------------------


class Test8NiUnaCifraInventada:
    def test_no_hay_ni_un_total_ni_una_media_ni_un_porcentaje(self, cliente, cuenta, crear_parcela):
        """El servidor no da ninguna cifra que no sea un dato o un recuento.

        Se recorre el JSON entero buscando campos que suenen a cuenta hecha por el servidor (total,
        media, porcentaje, suma…) fuera del bloque `totales`, que son **recuentos de filas** y están
        declarados uno a uno.
        """
        crear_parcela(alias="Con hectáreas", superficie_ha=2.43, geometria=UN_WKT)
        crear_parcela(alias="Sin hectáreas", superficie_ha=None, geometria=None)

        vista = _vista(cliente, cuenta)

        sospechosas = [
            clave
            for clave in _todas_las_claves(vista)
            if clave != ".totales"
            and not clave.startswith(".totales.")
            and any(palabra in clave.lower() for palabra in ("total", "media", "porcentaje", "suma", "promedio"))
        ]
        assert sospechosas == [], f"hay cifras calculadas por el servidor donde no se esperaban: {sospechosas}"

    def test_no_hay_ni_un_decimal_fuera_de_los_datos_de_una_tierra(self, cliente, cuenta, crear_parcela):
        """Todos los decimales de la respuesta, uno por uno, y de dónde sale cada uno.

        Es la comprobación que impide que se cuele «un total de hectáreas» o «el área media» sin que
        nadie lo note: la lista de sitios donde puede haber un decimal está escrita entera, y cualquier
        decimal nuevo hace fallar esta prueba con su camino exacto. **Con una forma sintética**, para
        que haya caja y anillos que comprobar.

        La lista se ha actualizado **dos veces** el 02/10/2026, y las dos veces porque el decimal nuevo
        era legítimo y venía de un arreglo: `extension`, que es la envolvente sin recortar de la finca
        (el arreglo de D7, para que recortar la caja no pierda dónde están las tierras de fuera). Eso
        es lo que tiene que pasar: el decimal se justifica aquí en vez de colarse.
        """
        crear_parcela(alias="Con hectáreas", superficie_ha=2.43, geometria=UN_WKT, poligono=503,
                      numero_parcela=51, numero_recinto=1)
        crear_parcela(alias="Sin hectáreas", superficie_ha=None, geometria=None)

        vista = _vista(cliente, cuenta)
        permitidos = {
            ".tierras[].superficie_ha",
            ".tierras[].superficie_sigpac_ha",
            ".tierras[].area_declarada_ha",
            ".tierras[].anillos[][][]",
            ".mapa.caja.oeste",
            ".mapa.caja.sur",
            ".mapa.caja.este",
            ".mapa.caja.norte",
            ".mapa.extension.oeste",
            ".mapa.extension.sur",
            ".mapa.extension.este",
            ".mapa.extension.norte",
        }
        de_mas = sorted({camino for camino, _ in _todos_los_decimales(vista)} - permitidos)

        assert de_mas == [], f"decimales que no salen de ningún dato de la finca: {de_mas}"

    def test_los_numeros_del_ensayo_son_los_del_servidor(self, cliente, cuenta, campana, crear_parcela):
        """Los recuentos del ensayo se pueden comprobar contra lo que hay guardado.

        Se ensaya un lote de tres recintos y se comprueba que los cuatro números que devuelve son los
        que salen de contar los recintos de verdad: tres en el lote, tres nuevos (ninguna tierra tenía
        versión) y ninguno sin forma. Nada calculado en la pantalla.
        """
        una = crear_parcela(alias="Una", geometria=None)
        otra = crear_parcela(alias="Otra", geometria=None)
        tercera = crear_parcela(alias="Tercera", geometria=None)

        plan = _ensayar(cliente, cuenta, campana["id"], [
            _un_recinto(una["id"], numero_recinto=1),
            _un_recinto(otra["id"], numero_recinto=2),
            _un_recinto(tercera["id"], numero_recinto=3, geometria=None),
        ])

        assert plan["recintos_en_el_lote"] == 3
        assert plan["nuevos"] == 3 and plan["iguales"] == 0 and plan["cambiados"] == 0
        assert plan["sin_forma"] == 1
        assert plan["nuevos"] + plan["iguales"] + plan["cambiados"] == plan["recintos_en_el_lote"]
        assert plan["tierras_nuevas"] == 0, "las tres tierras ya existían: no se da de alta ninguna"


# ---------------------------------------------------------------------------
# 9. Los textos viven en textos.py
# ---------------------------------------------------------------------------


class Test9LosTextos:
    def test_los_dos_bloques_nuevos_estan_servidos_y_sin_jerga(self, cliente, cuenta, crear_parcela):
        """Las dos pantallas nuevas piden sus palabras a `/api/interfaz`, y ninguna lleva jerga.

        Se comprueba clave por clave (que no falte ninguna: una clave que no llega es una frase en
        blanco delante del agricultor) y, además, que los dos bloques están registrados en
        `textos_visibles()`, que es lo que hace que el guardián de la jerga los mire.
        """
        interfaz = cliente.get("/api/interfaz").json()
        assert interfaz["tierras"] == textos.TIERRA_Y_MAPA
        assert interfaz["versiones"] == textos.VERSIONES_EN_PANTALLA

        visibles = textos.textos_visibles()
        for bloque in (textos.TIERRA_Y_MAPA, textos.VERSIONES_EN_PANTALLA):
            for clave, frase in bloque.items():
                assert frase, f"el texto «{clave}» está vacío"
                assert frase in visibles, f"«{clave}» no está en textos_visibles(), así que no se revisa"
                for prohibida in textos.PALABRAS_PROHIBIDAS:
                    assert prohibida.lower() not in frase.lower(), f"«{clave}» lleva jerga: «{prohibida}»"

    def test_la_respuesta_de_la_vista_no_lleva_jerga(self, cliente, cuenta, crear_parcela, campana):
        """Ni una respuesta nueva con jerga, y no solo los textos: también los códigos y los nombres."""
        crear_parcela(alias="El Prado", geometria=None, superficie_ha=None)
        interfaz = cliente.get("/api/interfaz").json()
        vista = _vista(cliente, cuenta)
        # La vista trae los textos enteros: se quitan para mirar lo demás (los datos).
        del vista["textos"], vista["textos_de_las_versiones"]
        crudo = json.dumps(vista, ensure_ascii=False)
        crudo += json.dumps(cliente.get("/api/mapa/estado").json(), ensure_ascii=False)
        crudo += json.dumps(interfaz["tierras"], ensure_ascii=False)
        crudo += json.dumps(interfaz["versiones"], ensure_ascii=False)

        for prohibida in textos.PALABRAS_PROHIBIDAS:
            assert prohibida.lower() not in crudo.lower(), f"una respuesta nueva lleva jerga: «{prohibida}»"

    def test_la_etiqueta_del_recuento_de_sin_forma_del_ensayo_no_puede_ser_la_de_no_se_sabe(self):
        """**DEFECTO (baja).** El ensayo llama «No se sabe» al número de recintos sin forma.

        `app.js`, al preparar el ensayo de una importación, pone las seis líneas de números. Las cinco
        primeras usan su etiqueta del servidor; la sexta —la de los recintos que vienen sin polígono—
        reutiliza el texto `version.no_se_sabe`, que en `textos.py` quiere decir «No se sabe», y que es
        la frase que se usa cuando un **área** no se conoce. El agricultor lee «No se sabe  3» donde el
        dato es «3 recintos sin forma», y «no se sabe» ahí sugiere que hay tres cosas que el programa
        no ha podido mirar.

        No lo puede cazar la prueba de «ni una frase escrita a mano» del fichero de JavaScript, y eso
        es justo lo que se enseña aquí: esa prueba comprueba que la frase **exista** en la copia de los
        textos, no que se esté usando para lo que es. Hace falta una clave propia (por ejemplo
        «recintos sin forma») en `VERSIONES_EN_PANTALLA`.
        """
        fuente = APP_JS.read_text(encoding="utf-8")
        bloque = re.search(r"function elEnsayoPreparado\(\).*?\n}", fuente, re.S)
        assert bloque is not None, "no se encuentra el ensayo en app.js"
        assert "textos.no_se_sabe" not in bloque.group(0), (
            "el ensayo pone la etiqueta «No se sabe» al recuento de recintos sin forma: no es un dato "
            "que no se sepa, es un recuento de recintos a los que no les ha llegado el polígono"
        )
        assert "sin_forma" in textos.VERSIONES_EN_PANTALLA or any(
            "forma" in clave and "sin" in clave for clave in textos.VERSIONES_EN_PANTALLA
        ), (
            "no hay ninguna clave en VERSIONES_EN_PANTALLA para decir «recintos sin forma»: por eso "
            "`app.js` reutiliza la de «No se sabe»"
        )


# ---------------------------------------------------------------------------
# 10. `asegurar_indices()`: poner al día un índice sin tocar una fila
# ---------------------------------------------------------------------------


def _un_motor_temporal(tmp_path, nombre: str):
    from sqlalchemy import create_engine

    motor = create_engine(f"sqlite:///{(tmp_path / nombre).as_posix()}", future=True)
    return motor


def _columnas_obligatorias(conexion, tabla: str) -> list[tuple[str, str]]:
    """Las columnas que hay que rellenar sí o sí para poder meter una fila de prueba."""
    salida = []
    for _, nombre, tipo, obligatoria, defecto, clave in conexion.execute(f'PRAGMA table_info("{tabla}")'):
        if clave or defecto is not None or not obligatoria:
            continue
        salida.append((nombre, (tipo or "").upper()))
    return salida


def _un_valor_de_prueba(tipo: str):
    if "INT" in tipo:
        return 1
    if any(palabra in tipo for palabra in ("REAL", "FLOA", "DOUB", "NUM", "DEC")):
        return 1.0
    if "BOOL" in tipo:
        return 0
    if any(palabra in tipo for palabra in ("DATE", "TIME")):
        return "2026-01-01 00:00:00"
    return "x"


def _meter_una_fila(conexion, tabla: str, **valores) -> None:
    """Mete una fila de prueba sin pelearse con las claves foráneas (que se apagan antes).

    Los valores que se pasan mandan; del resto de columnas obligatorias se pone uno cualquiera del
    tipo que toque. Es lo que hace falta para medir «esto no ha tocado ninguna fila» sin montar media
    finca.
    """
    columnas = dict(_columnas_obligatorias(conexion, tabla))
    columnas.update(valores)
    nombres = ", ".join(f'"{nombre}"' for nombre in columnas)
    huecos = ", ".join("?" for _ in columnas)
    conexion.execute(
        f'INSERT INTO "{tabla}" ({nombres}) VALUES ({huecos})', list(columnas.values())
    )


def _retrato_del_motor(motor) -> dict[str, str]:
    retrato = {}
    with motor.connect() as conexion:
        for tabla in models.Base.metadata.sorted_tables:
            existe = conexion.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (tabla.name,)
            ).fetchone()
            if existe:
                retrato[tabla.name] = _huella_de_una_tabla(conexion.connection.driver_connection, tabla.name)
    return retrato


def _la_definicion_del_indice(motor, nombre: str) -> str | None:
    with motor.connect() as conexion:
        fila = conexion.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name = ?", (nombre,)
        ).fetchone()
    return fila[0] if fila else None


class Test10AsegurarIndices:
    def test_en_la_base_de_la_aplicacion_no_hay_nada_que_poner_al_dia(self):
        """En una base recién creada, `asegurar_indices` no encuentra nada: ni crea ni cambia.

        Si esto fallara, el programa estaría tirando y volviendo a crear un índice **en cada
        arranque**, que es el tipo de trabajo silencioso que nadie mira y que un día se lleva por
        delante lo que no debe.
        """
        from app.database import asegurar_indices

        assert asegurar_indices() == ([], [])
        assert asegurar_indices() == ([], [])

    def test_sin_ninguna_tabla_no_revienta_ni_crea_nada(self, tmp_path):
        """Una base vacía (una instalación a medio nacer) no puede romper el arranque."""
        from app.database import asegurar_indices

        motor = _un_motor_temporal(tmp_path, "vacia.db")

        assert asegurar_indices(motor) == ([], [])
        with motor.connect() as conexion:
            tablas = conexion.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        assert tablas == [], "asegurar_indices no puede crear tablas: eso es cosa de crear_tablas"

    def test_un_indice_que_falta_se_crea_y_no_toca_ni_una_fila(self, tmp_path):
        """El índice que falta se crea, y la huella de **todas** las filas queda igual."""
        from app.database import asegurar_indices

        motor = _un_motor_temporal(tmp_path, "sin_indice.db")
        models.Base.metadata.create_all(bind=motor)
        with motor.begin() as conexion:
            crudo = conexion.connection.driver_connection
            crudo.execute("PRAGMA foreign_keys=OFF")
            _meter_una_fila(crudo, "parcelas", alias="Una tierra")
            crudo.execute('DROP INDEX IF EXISTS "ix_recepcion_albaran"')
        antes = _retrato_del_motor(motor)

        creados, cambiados = asegurar_indices(motor)

        assert creados == ["ix_recepcion_albaran"], creados
        assert cambiados == []
        assert _la_definicion_del_indice(motor, "ix_recepcion_albaran") is not None
        assert _retrato_del_motor(motor) == antes, "crear un índice ha cambiado alguna fila"

    def test_un_indice_cambiado_se_pone_al_dia_y_no_toca_ni_una_fila(self, tmp_path):
        """El índice que cambió se tira y se vuelve a crear, y las filas siguen siendo las mismas.

        Es el caso que motivó la función (D3 de la revisión de T05 y T09): una instalación que ya
        había arrancado con el índice viejo. Aquí se monta ese índice viejo a mano —único a secas,
        sin la condición de las anuladas— y se comprueba que se pone al día y que **ni una fila
        cambia**.
        """
        from app.database import asegurar_indices

        motor = _un_motor_temporal(tmp_path, "indice_viejo.db")
        models.Base.metadata.create_all(bind=motor)
        with motor.begin() as conexion:
            crudo = conexion.connection.driver_connection
            crudo.execute("PRAGMA foreign_keys=OFF")
            _meter_una_fila(crudo, "recepciones", clave_de_reenvio="reenvio-1", anulada=0)
            _meter_una_fila(crudo, "recepciones", clave_de_reenvio=None, anulada=0)
            crudo.execute('DROP INDEX IF EXISTS "uq_recepcion_reenvio"')
            crudo.execute(
                'CREATE UNIQUE INDEX "uq_recepcion_reenvio" ON recepciones (explotacion_id, clave_de_reenvio)'
            )
        antes = _retrato_del_motor(motor)
        assert "WHERE" not in (_la_definicion_del_indice(motor, "uq_recepcion_reenvio") or "")

        creados, cambiados = asegurar_indices(motor)

        assert cambiados == ["uq_recepcion_reenvio"], (creados, cambiados)
        assert creados == []
        definicion = _la_definicion_del_indice(motor, "uq_recepcion_reenvio") or ""
        assert "WHERE" in definicion.upper(), definicion
        assert _retrato_del_motor(motor) == antes, "poner al día un índice ha cambiado alguna fila"

    def test_si_un_indice_no_se_puede_crear_la_base_se_queda_entera_y_se_dice_en_castellano(self, tmp_path):
        """**DEFECTO (media).** Con datos que incumplen un índice, el programa **no arranca** y no lo explica.

        **Qué pasa.** `asegurar_indices` no atrapa los fallos al crear un índice, y `crear_tablas` se
        llama al arrancar (`main.py`, en el ciclo de vida), donde **solo se atrapa `RuntimeError`**
        para contarle al agricultor qué ha pasado y qué hacer. Cualquier otro fallo —y crear un índice
        único sobre datos que lo incumplen da `IntegrityError`/`OperationalError`— sale como una traza
        de Python en inglés y **el programa no se abre**. Antes de esta función esto no podía pasar:
        los índices de una tabla que ya existía no se tocaban nunca.

        **El caso concreto**, y no es inventado: una instalación cuyo fichero tenía filas repetidas
        antes de que el índice existiera (o después de una edición a mano, o de una restauración a
        medias). El arranque siguiente se encuentra con que hay que crear el índice único y no puede.

        **Lo que NO pasa, y se comprueba también**: la base **no se queda a medias**. La transacción de
        SQLite deshace el `DROP INDEX`, así que o el índice está entero o no está, y las filas quedan
        como estaban. El defecto no es que rompa datos: es que deja al agricultor sin programa y sin
        una frase que le diga qué hacer (la misma regla que `main.py` ya tiene escrita para el otro
        caso: «una traza de Python en la consola no le dice nada a quien lo ha puesto en marcha»).
        """
        from app.database import asegurar_indices

        motor = _un_motor_temporal(tmp_path, "choque.db")
        models.Base.metadata.create_all(bind=motor)
        with motor.begin() as conexion:
            crudo = conexion.connection.driver_connection
            crudo.execute("PRAGMA foreign_keys=OFF")
            crudo.execute('DROP INDEX IF EXISTS "uq_recepcion_reenvio"')
            _meter_una_fila(crudo, "recepciones", clave_de_reenvio="la-misma", anulada=0)
            _meter_una_fila(crudo, "recepciones", clave_de_reenvio="la-misma", anulada=0)
        antes = _retrato_del_motor(motor)

        fallo = None
        try:
            asegurar_indices(motor)
        except Exception as error:  # noqa: BLE001 - lo que se está midiendo es justo qué sale
            fallo = error

        # Lo bueno, primero: nada a medias. Ni un índice a medio crear, ni una fila tocada.
        assert fallo is not None, "esta prueba necesita que crear el índice único falle"
        assert _la_definicion_del_indice(motor, "uq_recepcion_reenvio") is None
        assert _retrato_del_motor(motor) == antes, "el fallo ha dejado la base cambiada"

        # Y lo que está mal: el fallo no es de los que el programa sabe explicar.
        assert isinstance(fallo, RuntimeError), (
            f"al no poder crear un índice sale {type(fallo).__name__} («{fallo}»), y `main.py` solo "
            "atrapa RuntimeError para contarle al agricultor qué ha pasado y qué hacer: con este fallo "
            "el programa no arranca y solo queda una traza de Python en inglés"
        )


# ---------------------------------------------------------------------------
# 11. La lista de la vista no puede quedarse vieja
# ---------------------------------------------------------------------------


class Test11LaVistaNoSeQuedaVieja:
    def test_despues_de_apuntar_una_tierra_la_vista_no_puede_seguir_contando_la_de_antes(self):
        """**DEFECTO (media-alta).** La vista se pide una vez por sesión y nadie la olvida.

        **Qué pasa.** `app.js` pide `/api/parcelas/vista` **solo si no la tiene** (`abrirLasTierrasDelMapa`:
        `if (!t06.vista) { await cargarLaVistaDeLasTierras(); }`) y la guarda en `estado.t06.vista`, que
        **no se vacía nunca**: en todo `app.js` no hay ni un `t06.vista = null`, ni una segunda llamada
        a `cargarLaVistaDeLasTierras`, ni nada que la pida al cerrar la pantalla. El comentario de la
        cabecera dice «no se vuelve a pedir mientras la pantalla esté abierta (salvo que se fuerce)»:
        **no hay ninguna forma de forzarlo**.

        **Qué le pasa al agricultor.** Apunta una tierra en el asistente (o corrige el nombre de una, o
        borra la que no era), vuelve a esta pantalla —que es la que existe para ver todas sus tierras—
        y **la tierra nueva no está**, el pie sigue diciendo las de antes, y el mapa y los filtros tampoco
        la tienen. En la misma sesión, la pantalla de siempre («mis cosas», que sí se recarga) dice 65 y
        esta dice 64. Y una tierra borrada sigue apareciendo: si la toca, el botón de «ver lo que ha
        sido» lleva a una dirección que ya no existe. El riesgo de verdad es el de siempre con una lista
        vieja: volver a apuntar la tierra que cree que no se guardó.

        Se comprueba en el código de la pantalla, que es donde está el fallo: o la vista se pide al
        abrirla siempre, o hay alguna forma de olvidarla. Cualquiera de las dos cosas vale; hoy no hay
        ninguna.
        """
        fuente = APP_JS.read_text(encoding="utf-8")
        bloque = re.search(r"async function abrirLasTierrasDelMapa\(\).*?\n}", fuente, re.S)
        assert bloque is not None, "no se encuentra `abrirLasTierrasDelMapa` en app.js: revisa esta prueba"
        se_pide_solo_si_no_esta = "if (!t06.vista)" in bloque.group(0)

        assert (not se_pide_solo_si_no_esta) or ("t06.vista = null" in fuente), (
            "la vista de las tierras se pide una sola vez por sesión y ninguna parte del programa la "
            "olvida: después de apuntar, corregir o borrar una tierra, esta pantalla sigue enseñando la "
            "lista y los recuentos de antes"
        )

    def test_la_pantalla_de_una_tierra_recarga_sus_versiones_al_abrirla(self):
        """**Lo que aguanta**, y conviene que quede escrito al lado de lo de arriba.

        La ficha de una tierra **sí** vuelve a pedir sus versiones cada vez que se abre
        (`cargarLasVersionesDeUnaTierra`), así que la comparación y el ensayo no se quedan viejos. El
        problema es solo de la vista de las tierras.
        """
        fuente = APP_JS.read_text(encoding="utf-8")
        assert "t06.versiones = (await apiJson(" in fuente
        assert "await cargarLasVersionesDeUnaTierra(t06.versionParcela)" in fuente
        bloque = re.search(r"async function abrirLasVersionesDeUnaTierra\(.*?\n}", fuente, re.S)
        assert bloque is not None and "cargarLasVersionesDeUnaTierra" in bloque.group(0), (
            "la ficha de una tierra ya no vuelve a pedir sus versiones al abrirla"
        )


# ---------------------------------------------------------------------------
# Lo que se ha probado y no ha salido nada, dicho para que se pueda juzgar
# ---------------------------------------------------------------------------


class Test12LoQueAguanta:
    """Cosas que se han atacado y **no** se han podido romper. Se dejan escritas a propósito: un
    informe que solo cuenta los fallos no dice cuánto se ha mirado."""

    def test_pedir_la_vista_dos_veces_da_exactamente_lo_mismo(self, cliente, cuenta, campana, crear_parcela):
        """Nada de la vista depende del azar ni del orden interno de la base."""
        parcela = crear_parcela(alias="El Prado", geometria=UN_WKT, superficie_ha=None)
        _importar(cliente, cuenta, campana["id"], [_un_recinto(parcela["id"], area_declarada_ha=1.75)])

        primera = _vista(cliente, cuenta)
        segunda = _vista(cliente, cuenta)

        assert primera == segunda

    def test_los_anillos_van_en_el_orden_que_se_puede_dibujar(self, cliente, cuenta, crear_parcela):
        """Cada anillo es una lista de pares [longitud, latitud] cerrada, y ninguno se mezcla con otro.

        Con un multipolígono, que es donde una lista plana de puntos dibujaría una raya entre trozos.
        """
        multiparte = (
            "MULTIPOLYGON(((-5.56 40.90, -5.55 40.90, -5.55 40.91, -5.56 40.91, -5.56 40.90)),"
            "((-5.50 40.95, -5.49 40.95, -5.49 40.96, -5.50 40.96, -5.50 40.95)))"
        )
        crear_parcela(alias="Partida", geometria=multiparte)

        tierra = _tierra(_vista(cliente, cuenta)["tierras"], "Partida")

        assert len(tierra["anillos"]) == 2
        for anillo in tierra["anillos"]:
            assert all(len(punto) == 2 for punto in anillo)
            # Cada anillo se queda en su trozo: no hay ni un punto del otro dentro.
            longitud_media = sum(punto[0] for punto in anillo) / len(anillo)
            assert longitud_media < -5.51 or longitud_media > -5.50

    def test_la_busqueda_por_nombre_y_por_referencia_es_la_misma_que_la_del_servidor(
        self, cliente, cuenta, crear_parcela
    ):
        """El buscador tiene que encontrar por nombre **y por referencia**, sin tildes y sin mayúsculas.

        Se comprueba sobre lo que devuelve el servidor (que trae las dos cosas en cada fila), así que
        lo que se mide es que la pantalla tenga con qué: el nombre y la referencia de cada tierra.
        """
        crear_parcela(alias="Peñaranda alto", ref_sigpac="37-455-12-3", geometria=None)
        crear_parcela(alias="El prado", ref_sigpac="37-455-99-1", geometria=None)

        tierras = _vista(cliente, cuenta)["tierras"]

        assert [t["alias"] for t in _lo_que_deja_la_pantalla(tierras, {"q": "penaranda"})] == ["Peñaranda alto"]
        assert [t["alias"] for t in _lo_que_deja_la_pantalla(tierras, {"q": "455-99"})] == ["El prado"]
        assert _lo_que_deja_la_pantalla(tierras, {"q": "no existe"}) == []
