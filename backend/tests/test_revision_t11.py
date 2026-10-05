"""Revisión independiente del T11: contactos reutilizables, enlaces y migración de textos.

## Qué es este fichero

No es la suite del ticket: es **el intento de romperla**. Cada prueba de aquí dice qué promesa del
informe `docs/T11_CONTACTOS.md` está atacando; las que llevan `DEFECTO` en el nombre **fallan mientras
el defecto exista** y pasan cuando se arregle, y llevan escrito **qué le pasaría al agricultor**.

## Foto del árbol (medida el 02/10/2026 a las 21:22:37, hora local)

| Fichero | Tamaño | Hora | sha256 (16 primeros) |
|---|---|---|---|
| `backend/app/contactos.py` | 26793 | 19:57:48 | `05B40631B3A2EFD3` |
| `backend/app/routers/contactos_api.py` | 41240 | 20:27:37 | `C10688BF0C3E47D0` |
| `backend/app/models.py` | 124888 | 19:42:49 | `1F37978BFDDB9471` |
| `backend/app/schemas.py` | 108745 | 21:10:27 | `DDC98E354E4C39C1` |
| `backend/app/textos.py` | 327602 | 20:45:31 | `824015535B1EBD90` |
| `backend/web/app.js` | 705283 | 21:04:17 | `F591BBCB53DF4A7D` |
| `backend/web/react/pantallas/contactos.js` | 17243 | **21:19:52** | `40AA165534947422` |
| `backend/tests_js/contactos.test.js` | 38775 | **21:20:11** | `21DFA86A71D76573` |
| `docs/T11_CONTACTOS.md` | 28806 | **21:22:34** | `29E2C3E8DDF45880` |

> **El árbol se movía mientras se revisaba.** Estos tres últimos ficheros se editaron **después** de
> empezar la revisión (21:19–21:22). Los defectos de aquí se han vuelto a medir sobre esa última
> versión, y el `pytest` de la suite entera que sostiene los recuentos es de las 21:22 (3678 pruebas,
> 0 fallos, 1 saltada). La primera pasada, a las 21:08, dio 3677: el número se movió con el árbol.

## Los cuatro defectos

1. **El NIF fusiona dos nombres que no se parecen.** `contactos.proponer` une por NIF sin mirar si los
   nombres tienen algo que ver, así que un NIF tecleado mal funde a dos personas distintas en una ficha
   y la marca como **segura**: el guion `--migrar` la apunta solo y el agricultor no ve ningún aviso.
2. **Ningún botón de contacto se pulsa en ninguna prueba de JavaScript.** `tests_js/contactos.test.js`
   solo pinta los componentes y mira los `data-accion` del HTML; el manejador de clics de `app.js` no se
   ejecuta ni una vez con una acción de contactos. Es el hueco que en el T10 escondió `siembra-nueva`.
3. **Reenviar la misma confirmación contesta 409 y dice una mentira.** El segundo envío de la misma
   clave responde «la lista de nombres ha cambiado desde que la miraste», y no ha cambiado nada. El
   contrato (§2) pide que reenviar un comando devuelva su resultado.
4. **La clave de la propuesta no cubre el texto.** Si entre mirar y confirmar alguien cambia la forma de
   escribir un nombre (mayúsculas o espacios), la clave sigue valiendo y la ficha se apunta con un
   nombre **distinto del que se enseñó**, en contra de lo que dice el §3.6 del informe.

## Cómo se ejecuta

```bash
cd backend
../.venv/Scripts/python.exe -m pytest tests/test_revision_t11.py -q
```

## Datos sintéticos

Los nombres escritos se meten **directamente en la base de pruebas** (como en `test_contactos.py`): lo
que se está probando es la lectura de esos textos y la fusión, no el alta de una factura. Ninguna prueba
toca `backend/cuedigital.db`: el `conftest.py` fija la base a una carpeta temporal antes de importar
`app`.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re
from itertools import combinations

import pytest
from sqlalchemy import func, select

from app import contactos as logica
from app import models

RAIZ = pathlib.Path(__file__).resolve().parents[2]
TESTS_JS = RAIZ / "backend" / "tests_js"

# Las tablas donde se escribe un nombre en estas pruebas, con lo mínimo para que la fila valga.
MINIMOS = {
    "facturas": {"fecha": dt.date(2026, 3, 12), "numero_factura": "2026/00123"},
    "analiticas": {
        "tipo": "suelo",
        "fecha_toma_muestra": dt.date(2026, 2, 14),
        "numero_informe": "2026/0417",
    },
}
CON_CAMPANA = ("analiticas",)


# --------------------------------------------------------------------------
# Ayudantes (propios, para no depender de `test_contactos.py`)
# --------------------------------------------------------------------------


def _modelo(tabla: str):
    for mapper in models.Base.registry.mappers:
        if mapper.class_.__tablename__ == tabla:
            return mapper.class_
    raise AssertionError(f"no existe la tabla {tabla}")


@pytest.fixture
def escribir(db_sesion, cuenta, campana):
    """Escribe un nombre a mano en la tabla que se le diga. Devuelve el identificador de la fila."""

    def _escribir(tabla: str, campo: str, texto: str, **cambios) -> int:
        datos = {"explotacion_id": cuenta["explotacion_id"], **MINIMOS.get(tabla, {})}
        if tabla in CON_CAMPANA:
            datos["campana_id"] = campana["id"]
        datos.update(cambios)
        datos[campo] = texto
        fila = _modelo(tabla)(**datos)
        db_sesion.add(fila)
        db_sesion.commit()
        db_sesion.refresh(fila)
        return fila.id

    return _escribir


def _la_revision(cliente, cabeceras) -> dict:
    respuesta = cliente.get("/api/contactos/migracion", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _aplicar(cliente, cabeceras, claves: list[str]):
    return cliente.post(
        "/api/contactos/migracion/aplicar", headers=cabeceras, json={"claves": claves}
    )


def _cuantas(db_sesion, modelo_) -> int:
    return int(db_sesion.scalar(select(func.count()).select_from(modelo_)) or 0)


def _una_ficha(cliente, cabeceras, contacto_id: int) -> dict:
    respuesta = cliente.get(f"/api/contactos/{contacto_id}", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# ==========================================================================
# DEFECTO 1 — el NIF une dos nombres que no se parecen
# ==========================================================================


class TestDefecto1ElNifNoPuedeFusionarDosNombresQueNoSeParecen:
    """**El caso más feo de todos, porque la fusión se marca como segura y nadie la ve.**

    La tabla del §3.1 del informe dice: «Son **el mismo nombre** y llevan el mismo NIF → se juntan».
    Pero `contactos.proponer` no comprueba la primera mitad: une por NIF **cualquier** pareja de
    grupos con un NIF único, sin mirar si los nombres se parecen. Un NIF tecleado mal en una factura es
    lo más fácil del mundo, y el resultado es que dos personas distintas acaban en la misma ficha, con
    `motivo="mismo_nif"`, `segura=True` y **sin aparecer en «se parecen»**.

    Y no se queda en la pantalla: `scripts/migrar_contactos.py --migrar` apunta **todas** las propuestas
    seguras, así que esto le pasa al agricultor sin que toque nada.

    Se comprueban las dos mitades: la propuesta no puede ser segura, y aplicar todas las seguras no puede
    dejar a esos dos nombres en la misma ficha.
    """

    def test_dos_nombres_distintos_con_el_mismo_nif_no_pueden_ir_a_la_misma_ficha(
        self, cliente, cuenta, escribir
    ):
        # Dos proveedores que no se parecen en nada, con el mismo NIF (uno de los dos mal tecleado).
        escribir("facturas", "proveedor", "Juan García López", proveedor_nif="B12345678")
        escribir(
            "facturas",
            "proveedor",
            "Pedro López Ruiz",
            proveedor_nif="B12345678",
            numero_factura="2026/00999",
        )
        assert not logica.se_parecen("Juan García López", "Pedro López Ruiz"), (
            "las dos pruebas de este defecto se apoyan en que estos dos nombres NO se parecen"
        )

        revision = _la_revision(cliente, cuenta["cabeceras"])
        for propuesta in revision["propuestas"]:
            if not propuesta["segura"]:
                continue
            nombres = sorted({uno["texto"] for uno in propuesta["escritos"]})
            for uno, otro in combinations(nombres, 2):
                assert logica.se_parecen(uno, otro) or (
                    logica.clave_exacta(uno) == logica.clave_exacta(otro)
                ), (
                    f"«{uno}» y «{otro}» van a la MISMA ficha solo porque comparten el NIF, y el "
                    "programa la marca como segura. Un NIF tecleado mal funde a dos personas distintas "
                    "y el guion --migrar lo hace solo, sin avisar: mire si los nombres se parecen "
                    "antes de juntarlos, y si no, enséñelos en «se parecen» para que decida el "
                    "agricultor."
                )

        # Y la segunda mitad, que es la que le pasa al agricultor: apuntar las seguras no puede
        # dejar a esos dos nombres en la misma ficha.
        seguras = [una["clave"] for una in revision["propuestas"] if una["segura"]]
        respuesta = _aplicar(cliente, cuenta["cabeceras"], seguras)
        assert respuesta.status_code == 200, respuesta.text
        for contacto in cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json():
            assert not (
                "Juan García López" in contacto["nombres_escritos"]
                and "Pedro López Ruiz" in contacto["nombres_escritos"]
            ), (
                f"la ficha «{contacto['nombre']}» se ha quedado con los dos nombres escritos: esos dos "
                "proveedores no son la misma persona y solo los une un NIF"
            )


# ==========================================================================
# DEFECTO 2 — ningún botón de contacto se pulsa en ninguna prueba
# ==========================================================================


class TestDefecto2LosBotonesDeLosContactosNoSePulsanEnNingunaPrueba:
    """**Se comprueba que la pantalla pinta, no que el botón haga.**

    En este programa TODOS los clics los atiende **un manejador delegado** de `app.js` que lee
    `data-accion`. Un botón cuyo `data-accion` no llegue al manejador **se pinta, se pulsa y no hace
    nada**: no salta ningún error y el agricultor se queda mirando la pantalla. Justo eso escondió en el
    T10 el botón `siembra-nueva`, que **no pintaba ninguna pantalla**, y solo se encontró porque una
    prueba lo pulsaba.

    Las 32 pruebas de `tests_js/contactos.test.js` **pintan los componentes** con
    `renderToStaticMarkup` y leen los `data-accion` del HTML: no hay ni un `pulsar(...)`, ni un
    `dispatchEvent`, ni una llamada al manejador. El T10 sí lo hace en el fichero de al lado
    (`tests_js/semillas.test.js`, `async function pulsar(entorno, accion, datos)`, que carga `app.js` en
    un DOM de mentira y llama al manejador delegado), así que no es una limitación del proyecto: es un
    hueco de este ticket.

    Esta prueba pide que **los botones que cambian algo** se pulsen de verdad: crear, guardar, borrar,
    marcar un papel, enlazar, desenlazar, confirmar la propuesta y deshacer. No pide una prueba por
    botón ni un navegador: pide lo mismo que hace el T10.
    """

    # Los botones que escriben en el cuaderno. Los de navegar (`contactos-ver`, `ir-inicio`,
    # `contactos-buscar`) se quedan fuera a propósito: lo que este defecto persigue es la acción que
    # parece hecha y no lo está.
    SE_TIENEN_QUE_PULSAR = (
        "contacto-nuevo",
        "contacto-guardar",
        "contacto-borrar-si",
        "contacto-papel",
        "contacto-enlazar-abrir",
        "contacto-enlazar",
        "contacto-desenlazar",
        "contactos-revisar-abrir",
        "contacto-migracion-apuntar",
        "contacto-migracion-todas",
        "contacto-migracion-deshacer",
    )

    @staticmethod
    def _se_pulsa_en_algun_sitio(ficheros: dict[str, str], accion: str) -> list[str]:
        """En qué fichero de `tests_js` se **pulsa** esa acción (no solo se pinta)."""
        pulsar = re.compile(
            r"(pulsar\s*\(|dispatchEvent|manejadores\.click|\bclick\s*\()"
        )
        sitios = []
        for nombre, texto in ficheros.items():
            for linea in texto.splitlines():
                if f'"{accion}"' in linea and pulsar.search(linea):
                    sitios.append(f"{nombre}: {linea.strip()}")
                    break
        return sitios

    def test_los_botones_que_escriben_en_el_cuaderno_se_pulsan_de_verdad(self):
        ficheros = {
            fichero.name: fichero.read_text(encoding="utf-8")
            for fichero in sorted(TESTS_JS.glob("*.test.js"))
        }
        sin_pulsar = [
            accion
            for accion in self.SE_TIENEN_QUE_PULSAR
            if not self._se_pulsa_en_algun_sitio(ficheros, accion)
        ]
        assert sin_pulsar == [], (
            "hay botones de los contactos que ninguna prueba pulsa: se comprueba que se pintan, no que "
            "hagan nada. Un botón cuyo data-accion no llegue al manejador de app.js se pulsa y no pasa "
            "nada, sin ningún error. Copia lo que ya hace el T10 en tests_js/semillas.test.js "
            "(pulsar(entorno, accion, datos) contra el manejador delegado) al menos para: "
            + ", ".join(accion for accion in sin_pulsar)
        )


# ==========================================================================
# DEFECTO 3 — reenviar la misma confirmación
# ==========================================================================


class TestDefecto3ReenviarLaMismaConfirmacion:
    """**El contrato §2 lo dice con todas las letras:** «Cada comando de negocio lleva identificador
    único de petición… Reenviar el mismo comando devuelve su resultado; no crea otro movimiento».

    Aquí no se duplica nada (eso está bien y se comprueba), pero el segundo envío contesta **409** con
    «La lista de nombres ha cambiado desde que la miraste, así que no he apuntado nada» — y **no ha
    cambiado nada**: el servidor ha sido él mismo, al enlazar lo que acaba de apuntar. El agricultor lee
    que el programa no ha apuntado nada cuando sí lo ha hecho.

    Y tiene un camino de verdad, no es teoría: el botón de apuntar **no se deshabilita mientras se
    envía** (`app.js` pone `cargando` y repinta, pero el botón sigue pulsable), así que un doble toque
    —que es lo que hace un agricultor con guantes— produce exactamente esto.

    Vale cualquiera de las dos salidas honestas: devolver el mismo resultado, o decir que ya estaba
    apuntado. Lo que no vale es decir que la lista ha cambiado cuando no ha cambiado.
    """

    def test_reenviar_la_misma_clave_no_puede_decir_que_la_lista_ha_cambiado(
        self, cliente, cuenta, escribir, db_sesion
    ):
        escribir("facturas", "proveedor", "Cooperativa Agrícola de Peñaranda")
        escribir(
            "facturas",
            "proveedor",
            "Cooperativa Agrícola de Peñaranda",
            numero_factura="2026/00124",
        )
        revision = _la_revision(cliente, cuenta["cabeceras"])
        seguras = [una for una in revision["propuestas"] if una["segura"]]
        assert len(seguras) == 1, [una["nombre"] for una in revision["propuestas"]]
        clave = seguras[0]["clave"]

        primera = _aplicar(cliente, cuenta["cabeceras"], [clave])
        assert primera.status_code == 200, primera.text
        assert primera.json()["fichas"] == 1, primera.text

        segunda = _aplicar(cliente, cuenta["cabeceras"], [clave])
        assert segunda.status_code == 200, (
            f"reenviar la misma confirmación contesta {segunda.status_code}: "
            f"{segunda.json().get('detail')!r}. No ha cambiado nada —lo ha enlazado el propio servidor—, "
            "así que el agricultor está leyendo que no se ha apuntado nada cuando sí se ha apuntado. "
            "Devuelve el resultado de la primera vez, o di que ya estaba apuntado."
        )
        # Y sin duplicar: esto ya estaba bien y tiene que seguir estándolo.
        assert _cuantas(db_sesion, models.Contacto) == 1
        assert _cuantas(db_sesion, models.EnlaceDeContacto) == 2


# ==========================================================================
# DEFECTO 4 — la clave no cubre el texto
# ==========================================================================


class TestDefecto4LaClaveNoCubreElTexto:
    """El §3.6 promete: «o se apunta lo que se enseñó, o no se apunta».

    La clave de una propuesta es la huella de **dónde** están los textos (`tabla:campo:id`), no de lo
    que dicen. Si entre mirar y confirmar cambia solo la forma de escribirlos —mayúsculas o espacios, que
    no cambian la agrupación—, la clave sigue siendo la misma y el servidor apunta la ficha con el
    nombre **nuevo**, que no es el que se le enseñó al agricultor.

    Se arregla metiendo **el texto** en la huella: entonces la clave cambia y el servidor contesta 409,
    como con cualquier otro cambio.
    """

    def test_confirmar_no_puede_crear_una_ficha_con_un_nombre_distinto_del_ensenado(
        self, cliente, cuenta, escribir, db_sesion
    ):
        escribir("facturas", "proveedor", "Cooperativa X", numero_factura="A")
        segundo = escribir("facturas", "proveedor", "Cooperativa X", numero_factura="B")
        revision = _la_revision(cliente, cuenta["cabeceras"])
        seguras = [una for una in revision["propuestas"] if una["segura"]]
        assert len(seguras) == 1, [una["nombre"] for una in revision["propuestas"]]
        ensenada = seguras[0]
        assert ensenada["nombre"] == "Cooperativa X"

        # Entre mirar y confirmar, el papel se corrige: la misma empresa, escrita de otra manera.
        fila = db_sesion.get(models.Factura, segundo)
        fila.proveedor = "COOPERATIVA X"
        db_sesion.commit()

        respuesta = _aplicar(cliente, cuenta["cabeceras"], [ensenada["clave"]])
        if respuesta.status_code == 200:
            creadas = respuesta.json()["contactos"]
            assert creadas, respuesta.text
            for contacto_id in creadas:
                ficha = _una_ficha(cliente, cuenta["cabeceras"], contacto_id)
                assert ficha["nombre"] == ensenada["nombre"], (
                    f"se enseñó «{ensenada['nombre']}» y se ha apuntado «{ficha['nombre']}»: la clave "
                    "no cubre el texto, así que un cambio hecho entre mirar y confirmar entra sin que "
                    "el agricultor lo vea. Mete los textos en la huella de la propuesta o contesta 409, "
                    "como con cualquier otro cambio."
                )
        else:
            assert respuesta.status_code == 409, (
                f"con la propuesta cambiada solo se puede contestar 409, y contesta "
                f"{respuesta.status_code}: {respuesta.text}"
            )
            assert _cuantas(db_sesion, models.Contacto) == 0


# ==========================================================================
# Lo que se ha medido y NO se ha podido romper
# ==========================================================================


class TestLoQueSeHaMedidoYNoSeHaPodidoRomper:
    """Las dos cosas que esta revisión comprobó a fondo y salieron bien.

    No defienden un defecto: **fijan lo que hoy es verdad** para que no se pierda por el camino.
    """

    def test_el_umbral_del_se_parecen_sigue_siendo_el_que_se_midio(self):
        """Los cinco números del §3.2, recomputados: no se han elegido a ojo, y siguen ahí.

        Existe porque el umbral es lo único que separa un aviso de una fusión, y bajarlo un pelo
        empezaría a avisar de que «Cooperativa X» y «Cooperativa Z» podrían ser la misma.
        """
        import difflib

        def ratio(uno: str, otro: str) -> float:
            return difflib.SequenceMatcher(
                None, logica.clave_parecida(uno), logica.clave_parecida(otro)
            ).ratio()

        medidos = [
            ("laboratorio agrario", "laboratorio agragio", 0.9474, True),
            ("cooperativa x", "cooperativa z", 0.9231, False),
            ("juan", "juana", 0.8889, False),
            ("luis", "luisa", 0.8889, False),
            ("transportes lopez", "transportes perez", 0.8824, False),
        ]
        for uno, otro, publicado, avisa in medidos:
            assert round(ratio(uno, otro), 4) == publicado, (
                f"«{uno}» / «{otro}» ya no da {publicado}: vuelve a medir el umbral y actualiza el §3.2"
            )
            assert logica.se_parecen(uno, otro) is avisa, f"«{uno}» / «{otro}» avisa al revés"
        assert 0.9231 < logica.UMBRAL_DE_PARECIDO < 0.9474, (
            "el umbral se ha salido del hueco medido: por debajo avisa de dos empresas distintas y por "
            "encima deja de avisar de una errata"
        )

    def test_deshacer_no_se_lleva_lo_que_el_agricultor_ha_hecho_despues(
        self, cliente, cuenta, escribir, db_sesion
    ):
        """El §3.7, hecho de verdad: migración, luego trabajo a mano, y a deshacer.

        Lo que la revisión comprobó y salió bien: la ficha que el agricultor se apunta **después** de la
        migración, y el enlace que hace él a mano, sobreviven a `deshacer`; lo que se va es solo lo que
        puso la migración, y ni una letra de los papeles cambia.
        """
        escribir("facturas", "proveedor", "Cooperativa Agrícola de Peñaranda")
        escribir(
            "facturas",
            "proveedor",
            "Cooperativa Agrícola de Peñaranda",
            numero_factura="2026/00124",
        )
        escribir("analiticas", "laboratorio", "Laboratorio Agrario de Villamuriel")
        textos_antes = [
            fila.proveedor
            for fila in db_sesion.scalars(select(models.Factura).order_by(models.Factura.id))
        ]

        seguras = [
            una["clave"]
            for una in _la_revision(cliente, cuenta["cabeceras"])["propuestas"]
            if una["segura"]
        ]
        assert _aplicar(cliente, cuenta["cabeceras"], seguras).status_code == 200

        # El trabajo del agricultor, DESPUÉS de la migración.
        suyo = cliente.post(
            "/api/contactos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Taller de Nemesio", "telefono": "979 000 000"},
        ).json()
        suelta = escribir("facturas", "proveedor", "Transportes Sin Dueño")
        enlace = cliente.post(
            f"/api/contactos/{suyo['id']}/enlaces",
            headers=cuenta["cabeceras"],
            json={"tabla": "facturas", "campo": "proveedor", "registro_id": suelta},
        )
        assert enlace.status_code == 200, enlace.text

        deshecho = cliente.post(
            "/api/contactos/migracion/deshacer", headers=cuenta["cabeceras"], json={}
        )
        assert deshecho.status_code == 200, deshecho.text

        fichas = cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json()
        suyos = [una for una in fichas if una["nombre"] == "Taller de Nemesio"]
        assert suyos, (
            "deshacer se ha llevado la ficha que el agricultor se apuntó después de la migración: "
            f"las que quedan son {[una['nombre'] for una in fichas]}"
        )
        assert suyos[0]["enlaces"] == 1, (
            "deshacer se ha llevado el enlace que hizo el agricultor a mano"
        )
        assert _una_ficha(cliente, cuenta["cabeceras"], suyo["id"])["vivos"], enlace.text

        # Y ni una letra de los papeles ha cambiado.
        db_sesion.expire_all()
        textos_despues = [
            fila.proveedor
            for fila in db_sesion.scalars(
                select(models.Factura).where(models.Factura.id <= 2).order_by(models.Factura.id)
            )
        ]
        assert textos_despues == textos_antes, (textos_antes, textos_despues)
