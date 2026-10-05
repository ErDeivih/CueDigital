"""Los contactos: la misma persona apuntada una sola vez, y la migración que no fusiona.

**Qué defiende este fichero, en una frase:** que el programa **no junte a dos que no puede asegurar que
son el mismo**, que la migración de los nombres escritos **proponga y no cree hechos**, que **no toque
ni una letra** de lo que el agricultor escribió, y que se pueda deshacer.

Los seis casos que el ticket pide, y dónde están aquí:

  1. Que el mismo contacto **no se duplique al usarlo dos veces** → `TestLaMismaPersonaNoSeTecleaDosVeces`.
  2. Que **dos nombres parecidos no se fusionen solos** → `TestLoQueNoSePuedeAsegurarNoSeJunta`.
  3. Que la migración **no toque un texto histórico** → `TestLaMigracionNoTocaNiUnaLetra`.
  4. Que **revierta** → el mismo sitio.
  5. Que **de otra finca no se vea nada** → `TestDeOtraFincaNoSeVeNada`.
  6. Que **enlazar no borre el nombre** que él había escrito → `TestEnlazarNoBorraElNombre`.

Los nombres escritos de las pruebas se meten **directamente en la base y no por la API de cada
módulo**: lo que se está probando es la lectura de esos textos y los enlaces, no el alta de una factura
(que ya tiene sus propias 900 pruebas en `test_facturas.py`). Y así las ocho puertas se prueban de la
misma manera, que es lo que hace que la novena no se olvide.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import re

import pytest

from app import contactos as logica
from app import models, textos

RAIZ = pathlib.Path(__file__).resolve().parents[2]
COPIA_DE_LOS_TESTS = RAIZ / "backend" / "tests_js" / "contactos.test.js"
GUION_DE_MIGRACION = RAIZ / "backend" / "scripts" / "migrar_contactos.py"

# --------------------------------------------------------------------------
# Ayudas
# --------------------------------------------------------------------------

# Con qué se rellena cada tabla para que valga como «un papel con un nombre escrito». Solo lo
# obligatorio: lo que se está probando es el nombre, y todo lo demás puede faltar (que es justo lo que
# el programa tiene que soportar).
MINIMOS = {
    "facturas": {"fecha": dt.date(2026, 3, 12), "numero_factura": "2026/00123"},
    "recepciones": {"fecha": dt.date(2026, 3, 15), "numero_albaran": "A-2026-118"},
    "ventas_de_cosecha": {
        "fecha": dt.date(2026, 7, 10),
        "numero_albaran": "ALB-2026-9",
        "producto": "Trigo blando",
        "cantidad": 42000.0,
    },
    "analiticas": {
        "tipo": "suelo",
        "fecha_toma_muestra": dt.date(2026, 2, 14),
        "numero_informe": "2026/0417",
    },
    "productos_fitosanitarios": {"nombre_comercial": "Ejemplo 25 EC"},
    "aplicadores": {},
    "asesores": {},
}

# Las tablas que **cuelgan de la campaña** y no admiten un vacío: al escribir una fila de prueba hay
# que decirle de qué año es. Se pone aquí y no en cada prueba porque olvidarlo da un error de la base
# que no dice nada de lo que se está probando.
CON_CAMPANA = ("ventas_de_cosecha", "analiticas")


def _modelo(tabla: str):
    for mapper in models.Base.registry.mappers:
        if mapper.class_.__tablename__ == tabla:
            return mapper.class_
    raise AssertionError(f"no existe la tabla {tabla}")


@pytest.fixture
def escribir_nombre(db_sesion, cuenta, campana):
    """Escribe un nombre a mano en la tabla que se le diga, como lo escribe el agricultor.

    Devuelve el identificador de la fila, que es lo que hace falta para enlazarla.
    """

    def _escribir(tabla: str, campo: str, texto: str | None, **cambios) -> int:
        campos = {"explotacion_id": cuenta["explotacion_id"], **MINIMOS.get(tabla, {})}
        if tabla in CON_CAMPANA:
            campos["campana_id"] = campana["id"]
        campos.update(cambios)
        campos[campo] = texto
        fila = _modelo(tabla)(**campos)
        db_sesion.add(fila)
        db_sesion.commit()
        db_sesion.refresh(fila)
        return fila.id

    return _escribir


@pytest.fixture
def una_factura(escribir_nombre):
    """Una factura con el proveedor escrito a mano."""

    def _crear(nombre: str | None = "Cooperativa Agrícola de Peñaranda", **cambios) -> int:
        return escribir_nombre("facturas", "proveedor", nombre, **cambios)

    return _crear


def _la_revision(cliente, cabeceras) -> dict:
    respuesta = cliente.get("/api/contactos/migracion", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _la_propuesta(revision: dict, nombre: str) -> dict:
    for propuesta in revision["propuestas"]:
        if propuesta["nombre"] == nombre:
            return propuesta
    raise AssertionError(
        f"no hay ninguna propuesta llamada «{nombre}»: "
        f"{[propuesta['nombre'] for propuesta in revision['propuestas']]}"
    )


def _los_escritos(cliente, cabeceras, **params) -> list[dict]:
    respuesta = cliente.get("/api/contactos/escritos", headers=cabeceras, params=params)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _texto_de_la_factura(db_sesion, explotacion_id: int, factura_id: int) -> str | None:
    factura = db_sesion.get(models.Factura, factura_id)
    db_sesion.refresh(factura)
    assert factura.explotacion_id == explotacion_id
    return factura.proveedor


def _cuantas_filas(db_sesion, modelo) -> int:
    from sqlalchemy import func, select

    return int(db_sesion.scalar(select(func.count()).select_from(modelo)) or 0)


# --------------------------------------------------------------------------
# 1. La misma persona no se teclea dos veces
# --------------------------------------------------------------------------


class TestLaMismaPersonaNoSeTecleaDosVeces:
    def test_dos_facturas_del_mismo_proveedor_dan_una_sola_ficha(
        self, cliente, cuenta, una_factura
    ):
        """El caso que da sentido a todo el ticket: doce facturas, un solo proveedor."""
        una_factura()
        una_factura()
        una_factura()
        revision = _la_revision(cliente, cuenta["cabeceras"])
        propuesta = _la_propuesta(revision, "Cooperativa Agrícola de Peñaranda")
        assert len(propuesta["escritos"]) == 3
        assert propuesta["segura"] is True

        respuesta = cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [propuesta["clave"]]},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["fichas"] == 1
        assert respuesta.json()["enlaces"] == 3

        contactos = cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json()
        assert len(contactos) == 1
        assert contactos[0]["enlaces"] == 3

    def test_usar_la_ficha_dos_veces_no_crea_una_segunda_ficha(
        self, cliente, cuenta, una_factura
    ):
        """Enlazar por la puerta de enlazar, dos veces, sobre la misma ficha: una sola ficha."""
        primera = una_factura()
        segunda = una_factura(numero_factura="2026/00124")
        creada = cliente.post(
            "/api/contactos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Cooperativa Agrícola de Peñaranda", "papeles": ["proveedor"]},
        )
        assert creada.status_code == 201, creada.text
        contacto_id = creada.json()["id"]

        for factura_id in (primera, segunda):
            respuesta = cliente.post(
                f"/api/contactos/{contacto_id}/enlaces",
                headers=cuenta["cabeceras"],
                json={"tabla": "facturas", "campo": "proveedor", "registro_id": factura_id},
            )
            assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["enlaces"] == 2

        contactos = cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json()
        assert len(contactos) == 1
        assert contactos[0]["nombres_escritos"] == ["Cooperativa Agrícola de Peñaranda"]

    def test_el_mismo_nombre_en_una_factura_y_en_una_venta_le_da_dos_papeles(
        self, cliente, cuenta, escribir_nombre
    ):
        """**Los papeles se solapan**, y eso se ve en los papeles y no en una casilla.

        La misma cooperativa es el proveedor de la factura y el comprador de la venta. Con un solo
        papel habría que elegir uno; aquí salen los dos, y sale dicho de dónde viene cada uno.
        """
        escribir_nombre("facturas", "proveedor", "Cooperativa Agrícola de Peñaranda")
        escribir_nombre("ventas_de_cosecha", "comprador", "Cooperativa Agrícola de Peñaranda")
        revision = _la_revision(cliente, cuenta["cabeceras"])
        propuesta = _la_propuesta(revision, "Cooperativa Agrícola de Peñaranda")
        assert sorted(propuesta["papeles"]) == ["comprador", "proveedor"]

        cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [propuesta["clave"]]},
        )
        contactos = cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json()
        assert sorted(contactos[0]["papeles"]) == ["comprador", "proveedor"]


# --------------------------------------------------------------------------
# 2. Lo que no se puede asegurar no se junta
# --------------------------------------------------------------------------


class TestLoQueNoSePuedeAsegurarNoSeJunta:
    def test_una_tilde_de_menos_no_junta_dos_nombres(self, cliente, cuenta, una_factura):
        """El ticket lo dice con estas palabras: «un nombre con una tilde y otro sin ella»."""
        una_factura("Agrícola Peñaranda")
        una_factura("Agricola Penaranda", numero_factura="2026/00124")
        revision = _la_revision(cliente, cuenta["cabeceras"])
        parecidos = [p for p in revision["propuestas"] if p["motivo"] == "se_parecen"]
        assert len(parecidos) == 1, revision["propuestas"]
        assert parecidos[0]["segura"] is False
        assert parecidos[0]["nombres"] == ["Agricola Penaranda", "Agrícola Peñaranda"]
        # **Y cada una queda como su propia ficha**, que es exactamente «no se juntan»: el programa
        # propone dos, no una con los dos nombres dentro.
        seguras = [p for p in revision["propuestas"] if p["segura"]]
        assert sorted(len(p["escritos"]) for p in seguras) == [1, 1]
        assert revision["resumen"]["se_parecen"] == 1

    def test_una_razon_social_de_mas_no_junta_dos_nombres(self, cliente, cuenta, una_factura):
        """«Cooperativa X» y «Cooperativa X S.L.»: otra vez el caso del ticket."""
        una_factura("Cooperativa X")
        una_factura("Cooperativa X S.L.", numero_factura="2026/00124")
        revision = _la_revision(cliente, cuenta["cabeceras"])
        assert revision["resumen"]["se_parecen"] == 1
        for propuesta in revision["propuestas"]:
            if propuesta["segura"]:
                # **Ni una ficha segura lleva los dos nombres dentro.**
                assert propuesta["nombres"] == [propuesta["nombre"]], propuesta

    def test_el_mismo_nombre_con_dos_nif_no_se_junta(self, cliente, cuenta, escribir_nombre):
        """**Dos personas distintas con el mismo nombre.** Es el caso que el contrato pide en E5."""
        escribir_nombre(
            "facturas", "proveedor", "Juan García", proveedor_nif="12345678Z"
        )
        escribir_nombre(
            "facturas",
            "proveedor",
            "Juan García",
            proveedor_nif="87654321X",
            numero_factura="2026/00124",
        )
        revision = _la_revision(cliente, cuenta["cabeceras"])
        homonimos = [p for p in revision["propuestas"] if p["motivo"] == "el_mismo_nombre_dos_nif"]
        assert len(homonimos) == 1
        assert homonimos[0]["segura"] is False
        assert homonimos[0]["nifs"] == ["12345678Z", "87654321X"]
        assert revision["resumen"]["homonimos"] == 1

    def test_el_servidor_no_junta_lo_que_no_se_puede_aunque_se_lo_pidan(
        self, cliente, cuenta, una_factura
    ):
        """**El «no se fusiona» no puede vivir solo en la pantalla.**

        Se le manda la clave de la propuesta insegura como si fuera una segura. El servidor tiene que
        negarse y **no crear nada**, que es lo que impide que el fallo se pueda provocar desde fuera.
        """
        una_factura("Cooperativa X")
        una_factura("Cooperativa X S.L.", numero_factura="2026/00124")
        revision = _la_revision(cliente, cuenta["cabeceras"])
        parecida = [p for p in revision["propuestas"] if p["motivo"] == "se_parecen"][0]
        respuesta = cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [parecida["clave"]]},
        )
        assert respuesta.status_code == 409, respuesta.text
        assert cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json() == []

    def test_con_el_mismo_nif_si_se_pueden_juntar(self, cliente, cuenta, escribir_nombre):
        """La excepción del ticket: **el NIF es una prueba**, siempre que el nombre la acompañe.

        Las dos formas de escribirlo (con puntos y guiones, y sin ellos) son el mismo número: la ficha
        se apunta **con el NIF**, que es la prueba que acaba de permitir juntarlas. Y los dos nombres
        son la misma empresa escrita de dos maneras («Cooperativa Agricola de Peñaranda» y
        «COOPERATIVA AGRÍCOLA DE PEÑARANDA S.C.L.» se parecen), que es lo que exige la regla desde el
        arreglo del defecto 1 de la revisión: **el NIF no basta él solo**.
        """
        escribir_nombre(
            "facturas", "proveedor", "Cooperativa Agricola de Peñaranda", proveedor_nif="B-34.123.456"
        )
        escribir_nombre(
            "facturas",
            "proveedor",
            "COOPERATIVA AGRÍCOLA DE PEÑARANDA S.C.L.",
            proveedor_nif="b34123456",
            numero_factura="2026/00124",
        )
        revision = _la_revision(cliente, cuenta["cabeceras"])
        con_prueba = [p for p in revision["propuestas"] if p["motivo"] == "mismo_nif"]
        assert len(con_prueba) == 1
        assert con_prueba[0]["segura"] is True
        assert len(con_prueba[0]["escritos"]) == 2

        cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [con_prueba[0]["clave"]]},
        )
        contactos = cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json()
        assert len(contactos) == 1
        assert contactos[0]["nif"] == "B34123456"
        # **Las dos formas de escribirla siguen ahí**, cada una en su papel.
        assert len(contactos[0]["nombres_escritos"]) == 2

    # ----------------------------------------------------------------------
    # El defecto 1 de la revisión independiente: **el NIF no basta él solo**
    # ----------------------------------------------------------------------
    #
    # Las cuatro ramas de la regla, una por prueba, porque es el punto donde un fallo hace lo peor
    # que puede hacer este ticket: fusionar a dos que no son el mismo y **llamarlo seguro**.
    #
    #   1. NIF igual + nombre escrito igual      → segura (`mismo_nif`)      ← lo de siempre
    #   2. NIF igual + nombres que se parecen    → segura (`mismo_nif`)      ← lo de siempre
    #   3. NIF igual + nombres que NO se parecen → NO segura (motivo nuevo)  ← el arreglo
    #   4. NIF distinto + nombre escrito igual    → NO segura (`el_mismo_nombre_dos_nif`)

    def test_un_nif_con_dos_nombres_distintos_no_es_seguro(self, cliente, cuenta, escribir_nombre):
        """**El defecto de gravedad alta, con el caso que midió la revisión.**

        «Juan García López» y «Pedro López Ruiz» con el mismo NIF: uno de los dos papeles está mal
        escrito. Antes de este arreglo el programa los juntaba en una ficha, la marcaba como
        **segura**, la enseñaba en «Se pueden apuntar» y `migrar_contactos.py --migrar` la apuntaba
        sola, sin que el agricultor viera nada.
        """
        assert not logica.se_parecen("Juan García López", "Pedro López Ruiz"), (
            "esta prueba se apoya en que esos dos nombres NO se parecen"
        )
        escribir_nombre(
            "facturas", "proveedor", "Juan García López", proveedor_nif="B12345678"
        )
        escribir_nombre(
            "facturas",
            "proveedor",
            "Pedro López Ruiz",
            proveedor_nif="B12345678",
            numero_factura="2026/00999",
        )
        revision = _la_revision(cliente, cuenta["cabeceras"])
        # Ni una propuesta segura: **el NIF no puede fusionar a dos personas distintas**.
        assert [p["nombre"] for p in revision["propuestas"] if p["segura"]] == []
        dudosa = [p for p in revision["propuestas"] if not p["segura"]]
        assert [p["motivo"] for p in dudosa] == ["mismo_nif_nombres_distintos"]
        assert sorted(dudosa[0]["nombres"]) == ["Juan García López", "Pedro López Ruiz"]
        assert dudosa[0]["nifs"] == ["B12345678"], "el NIF que comparten tiene que enseñarse"
        assert revision["resumen"]["nif_con_nombres_distintos"] == 1
        assert revision["resumen"]["fichas"] == 0

        # Y si alguien manda su clave como si fuera segura, el servidor no apunta nada.
        respuesta = cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [dudosa[0]["clave"]]},
        )
        assert respuesta.status_code == 409, respuesta.text
        assert cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json() == []

    def test_el_guion_no_apunta_la_del_nif_con_nombres_distintos(self, tmp_path, capsys):
        """**Ni la pantalla ni el guion**: lo que no se puede asegurar no se apunta solo.

        El guion apunta «todas las seguras», así que lo que importa no es que él se acuerde de
        mirarlo: es que esa propuesta **no salga segura**. Se comprueba con el guion de verdad, sobre
        una base que se fabrica aquí (nunca la del agricultor), y con los dos NIF iguales.
        """
        ruta = tmp_path / "nif_repetido.db"
        _una_base_de_dos_facturas(
            ruta,
            [
                ("Juan García López", "B12345678"),
                ("Pedro López Ruiz", "B12345678"),
            ],
        )
        antes_textos = _huella_de_los_nombres(_el_guion(), ruta)

        codigo = _el_guion_corre(_el_guion(), "--base", str(ruta), "--migrar")
        salida = capsys.readouterr().out
        assert codigo == 0, salida
        # No hay ninguna ficha segura que apuntar, y el guion lo dice con esas palabras.
        assert "no hay ninguna ficha segura que apuntar" in salida, salida
        assert "el NIF es el mismo, pero los nombres no se parecen en nada" in salida, salida

        from sqlalchemy import func, select
        from sqlalchemy.orm import Session

        from app import database

        motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
        with Session(motor) as sesion:
            assert sesion.scalar(select(func.count()).select_from(models.Contacto)) == 0, (
                "el guion ha apuntado una ficha con dos personas distintas que solo comparten el NIF"
            )
        motor.dispose()
        # Y ni una letra de los papeles se ha tocado.
        assert _huella_de_los_nombres(_el_guion(), ruta) == antes_textos

    def test_el_mismo_nif_con_el_mismo_nombre_si_junta(self, cliente, cuenta, escribir_nombre):
        """La primera rama, para que el arreglo no se pase de listo: el nombre igual + el NIF igual.

        **Con un matiz que conviene entender**: «Cooperativa X» y «COOPERATIVA X» no son dos grupos que
        se juntan por el NIF, son **el mismo grupo** (la comparación no distingue mayúsculas), así que
        el motivo que sale es «está escrito igual en todas partes» y no «mismo NIF». Lo que importa, y
        es lo que se comprueba, es que **sigue siendo segura**: el arreglo del NIF no ha roto el caso
        bueno.
        """
        escribir_nombre("facturas", "proveedor", "Cooperativa X", proveedor_nif="B12345678")
        escribir_nombre(
            "facturas",
            "proveedor",
            "COOPERATIVA X",
            proveedor_nif="B12345678",
            numero_factura="2026/00124",
        )
        revision = _la_revision(cliente, cuenta["cabeceras"])
        seguras = [p for p in revision["propuestas"] if p["segura"]]
        assert len(seguras) == 1
        assert seguras[0]["motivo"] == "el_mismo_nombre", (
            "las mayúsculas no hacen dos grupos: es el mismo nombre escrito igual"
        )
        assert len(seguras[0]["escritos"]) == 2
        assert revision["resumen"]["nif_con_nombres_distintos"] == 0

    def test_tres_nombres_con_el_mismo_nif_y_uno_que_no_encaja_no_se_juntan(
        self, cliente, cuenta, escribir_nombre
    ):
        """**Dos a dos, no «cada uno con el primero».** Un grupo solo es seguro si ninguna pareja de sus
        nombres se contradice: con la comprobación floja, un tercer nombre distinto entraría por la
        puerta del que sí se parece al primero."""
        escribir_nombre("facturas", "proveedor", "Cooperativa X", proveedor_nif="B12345678")
        escribir_nombre(
            "facturas",
            "proveedor",
            "Cooperativa X S.L.",
            proveedor_nif="B12345678",
            numero_factura="2026/00124",
        )
        escribir_nombre(
            "facturas",
            "proveedor",
            "Transportes López",
            proveedor_nif="B12345678",
            numero_factura="2026/00125",
        )
        revision = _la_revision(cliente, cuenta["cabeceras"])
        assert [p["nombre"] for p in revision["propuestas"] if p["segura"]] == [], (
            "«Transportes López» se ha colado en la ficha del NIF por no comparar dos a dos"
        )
        dudosa = [p for p in revision["propuestas"] if not p["segura"]][0]
        assert dudosa["motivo"] == "mismo_nif_nombres_distintos"
        assert len(dudosa["escritos"]) == 3

    def test_el_nif_con_nombres_distintos_cruza_papeles_y_tampoco_se_junta(
        self, cliente, cuenta, escribir_nombre
    ):
        """El caso que la revisión midió cruzando papeles: un proveedor y un laboratorio con el mismo
        NIF acaban con `papeles: ['proveedor', 'laboratorio']` en una sola ficha."""
        escribir_nombre(
            "facturas", "proveedor", "Suministros Agrícolas Peñaranda", proveedor_nif="B12345678"
        )
        escribir_nombre(
            "analiticas",
            "laboratorio",
            "Agrolab Villamuriel",
            nif_laboratorio="B12345678",
        )
        revision = _la_revision(cliente, cuenta["cabeceras"])
        assert [p for p in revision["propuestas"] if p["segura"]] == []
        dudosa = [p for p in revision["propuestas"] if not p["segura"]][0]
        assert dudosa["motivo"] == "mismo_nif_nombres_distintos"
        assert sorted(dudosa["nombres"]) == ["Agrolab Villamuriel", "Suministros Agrícolas Peñaranda"]

    # ----------------------------------------------------------------------
    # El defecto 3 de la revisión: reenviar la misma confirmación
    # ----------------------------------------------------------------------

    def test_reenviar_la_misma_confirmacion_devuelve_su_resultado(
        self, cliente, cuenta, db_sesion, una_factura
    ):
        """**El contrato lo pide con estas palabras** (§2): «Reenviar el mismo comando devuelve su
        resultado; no crea otro movimiento».

        Y hay un camino de verdad, no es teoría: el botón de apuntar manda la petición, y un doble
        toque (con guantes, con el móvil lento) la manda otra vez. Antes, la segunda contestaba 409
        «la lista de nombres ha cambiado» — y era mentira: lo que había cambiado es que **el propio
        servidor** acababa de enlazar esos nombres. El agricultor leía que no se había apuntado nada
        cuando sí se había apuntado.
        """
        una_factura("Cooperativa Agrícola de Peñaranda")
        una_factura(numero_factura="2026/00124")
        revision = _la_revision(cliente, cuenta["cabeceras"])
        seguras = [p for p in revision["propuestas"] if p["segura"]]
        assert len(seguras) == 1
        clave = seguras[0]["clave"]

        primera = cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [clave]},
        )
        assert primera.status_code == 200, primera.text
        assert primera.json()["fichas"] == 1
        assert primera.json()["enlaces"] == 2
        assert primera.json()["avisos"] == []

        segunda = cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [clave]},
        )
        assert segunda.status_code == 200, (
            "reenviar la misma confirmación no puede contestar «la lista ha cambiado»: "
            f"contesta {segunda.status_code} {segunda.text}"
        )
        # **El mismo resultado que la primera vez**, para que reenviar sea inofensivo…
        assert segunda.json()["fichas"] == 1
        assert segunda.json()["enlaces"] == 2
        assert segunda.json()["contactos"] == primera.json()["contactos"]
        assert segunda.json()["nombres"] == primera.json()["nombres"]
        # …y diciendo que no se ha apuntado dos veces, que es la verdad.
        assert len(segunda.json()["avisos"]) == 1
        assert "ya estaba apuntada" in segunda.json()["avisos"][0]

        # Y sin duplicar nada: una ficha y dos enlaces, con dos reenvíos más.
        cliente.post(
            "/api/contactos/migracion/aplicar", headers=cuenta["cabeceras"], json={"claves": [clave]}
        )
        assert _cuantas_filas(db_sesion, models.Contacto) == 1
        assert _cuantas_filas(db_sesion, models.EnlaceDeContacto) == 2

    def test_una_clave_de_una_ficha_con_los_textos_repartidos_si_da_409(
        self, cliente, cuenta, escribir_nombre
    ):
        """Y el 409 sigue existiendo para lo que de verdad ha cambiado.

        Si los textos de esa propuesta **no** están todos enlazados con la misma ficha —uno sí y otro
        no, o cada uno con una ficha distinta—, entonces sí ha pasado algo, y se dice.
        """
        escribir_nombre("facturas", "proveedor", "Cooperativa Agrícola de Peñaranda")
        segunda = escribir_nombre(
            "facturas",
            "proveedor",
            "Cooperativa Agrícola de Peñaranda",
            numero_factura="2026/00124",
        )
        revision = _la_revision(cliente, cuenta["cabeceras"])
        clave = [p for p in revision["propuestas"] if p["segura"]][0]["clave"]
        primera = cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [clave]},
        )
        assert primera.status_code == 200, primera.text

        # El agricultor le quita el enlace a uno de los dos papeles: ahora la propuesta está a medias.
        ficha = cliente.get(
            f"/api/contactos/{primera.json()['contactos'][0]}", headers=cuenta["cabeceras"]
        ).json()
        el_de_la_segunda = [
            vivo for vivo in ficha["vivos"] if vivo["escrito"]["registro_id"] == segunda
        ][0]
        quitado = cliente.delete(
            f"/api/contactos/{ficha['id']}/enlaces/{el_de_la_segunda['id']}",
            headers=cuenta["cabeceras"],
        )
        assert quitado.status_code == 200, quitado.text

        respuesta = cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [clave]},
        )
        assert respuesta.status_code == 409, (
            "con la propuesta a medias (un texto enlazado y otro no) no se puede contestar «ya estaba»"
        )

    # ----------------------------------------------------------------------
    # El defecto 4 de la revisión: la clave tiene que cubrir el texto
    # ----------------------------------------------------------------------

    def test_confirmar_no_apunta_un_nombre_distinto_del_ensenado(
        self, cliente, cuenta, db_sesion, escribir_nombre
    ):
        """**«O se apunta lo que se enseñó, o no se apunta»** (§3.6 del documento).

        La clave era la huella de **dónde** están los textos (tabla, campo e identificador). Si entre
        mirar y confirmar el papel se corregía de una forma que no cambia la agrupación —pasar
        «Cooperativa X» a «COOPERATIVA X»—, la clave seguía valiendo y se apuntaba una ficha con un
        nombre que el agricultor **no había visto**.
        """
        escribir_nombre("facturas", "proveedor", "Cooperativa X", numero_factura="A")
        segundo = escribir_nombre(
            "facturas", "proveedor", "Cooperativa X", numero_factura="B"
        )
        revision = _la_revision(cliente, cuenta["cabeceras"])
        seguras = [p for p in revision["propuestas"] if p["segura"]]
        assert len(seguras) == 1
        ensenada = seguras[0]
        assert ensenada["nombre"] == "Cooperativa X"

        # Entre mirar y confirmar, el papel se corrige: la misma empresa, escrita de otra manera.
        fila = db_sesion.get(models.Factura, segundo)
        fila.proveedor = "COOPERATIVA X"
        db_sesion.commit()

        respuesta = cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [ensenada["clave"]]},
        )
        assert respuesta.status_code == 409, (
            "la clave no cubre el texto: se ha apuntado una ficha con un nombre que el agricultor no "
            f"había visto. Contesta {respuesta.status_code} {respuesta.text}"
        )
        assert _cuantas_filas(db_sesion, models.Contacto) == 0

    def test_la_clave_cambia_si_cambia_el_texto(self):
        """La comprobación de la regla, en pequeño y sin base de datos: la huella lleva el texto."""
        from app.routers import contactos_api

        escritos = [
            logica.Escrito("facturas", "proveedor", 1, "Cooperativa X"),
            logica.Escrito("facturas", "proveedor", 2, "Cooperativa X"),
        ]
        antes = contactos_api._la_clave(logica.proponer(escritos)[0])
        con_mayusculas = [
            logica.Escrito("facturas", "proveedor", 1, "COOPERATIVA X"),
            logica.Escrito("facturas", "proveedor", 2, "Cooperativa X"),
        ]
        despues = contactos_api._la_clave(logica.proponer(con_mayusculas)[0])
        assert antes != despues, "un cambio de mayúsculas entre mirar y confirmar tiene que notarse"
        # Y con los mismos textos, la misma clave: es lo que hace que reenviar sea inofensivo.
        iguales = [
            logica.Escrito("facturas", "proveedor", 1, "Cooperativa X"),
            logica.Escrito("facturas", "proveedor", 2, "Cooperativa X"),
        ]
        assert contactos_api._la_clave(logica.proponer(iguales)[0]) == antes

    def test_mayusculas_de_mas_si_es_el_mismo_nombre(self, cliente, cuenta, escribir_nombre):
        """Y lo contrario, para que la regla no se pase de lista: las mayúsculas no son otra persona."""
        escribir_nombre("facturas", "proveedor", "COOPERATIVA AGRÍCOLA DE PEÑARANDA")
        escribir_nombre(
            "facturas",
            "proveedor",
            "Cooperativa Agrícola de Peñaranda",
            numero_factura="2026/00124",
        )
        revision = _la_revision(cliente, cuenta["cabeceras"])
        assert [p for p in revision["propuestas"] if p["segura"]][0]["motivo"] == "el_mismo_nombre"
        assert revision["resumen"]["se_parecen"] == 0


# --------------------------------------------------------------------------
# 3 y 4. La migración no toca ni una letra, y se puede deshacer
# --------------------------------------------------------------------------


class TestLaMigracionNoTocaNiUnaLetra:
    def test_la_revision_no_escribe_nada(self, cliente, cuenta, db_sesion, una_factura):
        """**Mirar no es apuntar.** Ni una ficha, ni un papel, ni un enlace, ni un texto tocado."""
        una_factura("Cooperativa Agrícola de Peñaranda")
        una_factura("Cooperativa X S.L.", numero_factura="2026/00124")
        antes = (
            _cuantas_filas(db_sesion, models.Contacto),
            _cuantas_filas(db_sesion, models.EnlaceDeContacto),
            _cuantas_filas(db_sesion, models.PapelDeUnContacto),
        )
        _la_revision(cliente, cuenta["cabeceras"])
        _la_revision(cliente, cuenta["cabeceras"])
        despues = (
            _cuantas_filas(db_sesion, models.Contacto),
            _cuantas_filas(db_sesion, models.EnlaceDeContacto),
            _cuantas_filas(db_sesion, models.PapelDeUnContacto),
        )
        assert antes == despues == (0, 0, 0)

    def test_aplicar_no_cambia_ningun_texto_escrito(
        self, cliente, cuenta, db_sesion, escribir_nombre
    ):
        """El texto del papel se lee antes y después, letra a letra. **Ni una se mueve.**"""
        factura = escribir_nombre(
            "facturas", "proveedor", "  Cooperativa Agricola de Peñaranda  S.C.L. "
        )
        original = _texto_de_la_factura(db_sesion, cuenta["explotacion_id"], factura)
        revision = _la_revision(cliente, cuenta["cabeceras"])
        propuesta = [p for p in revision["propuestas"] if p["segura"]][0]
        respuesta = cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [propuesta["clave"]]},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["textos_tocados"] == 0
        assert _texto_de_la_factura(db_sesion, cuenta["explotacion_id"], factura) == original

    def test_aplicar_deja_apuntado_lo_que_decia_el_papel(
        self, cliente, cuenta, db_sesion, escribir_nombre
    ):
        """Y lo que decía queda guardado en el enlace, para poder decir si cambia después."""
        escribir_nombre("facturas", "proveedor", "Cooperativa Agrícola de Peñaranda")
        revision = _la_revision(cliente, cuenta["cabeceras"])
        propuesta = [p for p in revision["propuestas"] if p["segura"]][0]
        cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [propuesta["clave"]]},
        )
        enlace = db_sesion.query(models.EnlaceDeContacto).one()
        assert enlace.nombre_de_entonces == "Cooperativa Agrícola de Peñaranda"
        assert enlace.origen == "migracion"

    def test_deshacer_devuelve_la_base_a_como_estaba(self, cliente, cuenta, db_sesion, una_factura):
        """**Reversible de verdad**: los mismos textos, y ninguna ficha ni enlace de más."""
        primera = una_factura("Cooperativa Agrícola de Peñaranda")
        segunda = una_factura("Laboratorio Agrario de Villamurriel", numero_factura="2026/00124")
        textos_antes = [
            _texto_de_la_factura(db_sesion, cuenta["explotacion_id"], primera),
            _texto_de_la_factura(db_sesion, cuenta["explotacion_id"], segunda),
        ]
        revision = _la_revision(cliente, cuenta["cabeceras"])
        claves = [p["clave"] for p in revision["propuestas"] if p["segura"]]
        cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": claves},
        )
        assert _cuantas_filas(db_sesion, models.Contacto) == 2

        deshecho = cliente.post(
            "/api/contactos/migracion/deshacer", headers=cuenta["cabeceras"], json={}
        )
        assert deshecho.status_code == 200, deshecho.text
        assert deshecho.json()["fichas"] == 2
        assert deshecho.json()["enlaces"] == 2
        assert deshecho.json()["textos_tocados"] == 0
        assert _cuantas_filas(db_sesion, models.Contacto) == 0
        assert _cuantas_filas(db_sesion, models.EnlaceDeContacto) == 0
        assert _cuantas_filas(db_sesion, models.PapelDeUnContacto) == 0
        assert [
            _texto_de_la_factura(db_sesion, cuenta["explotacion_id"], primera),
            _texto_de_la_factura(db_sesion, cuenta["explotacion_id"], segunda),
        ] == textos_antes
        # Y los nombres vuelven a estar disponibles para enlazarlos, que es lo que hace que deshacer
        # no deje al agricultor peor que antes.
        assert len(_los_escritos(cliente, cuenta["cabeceras"], sin_enlazar=True)) == 2

    def test_deshacer_respeta_la_ficha_que_el_agricultor_ha_corregido(
        self, cliente, cuenta, una_factura
    ):
        """**Volver atrás no se lleva el trabajo suyo.** Una ficha corregida es suya y se queda."""
        una_factura("Cooperativa Agrícola de Peñaranda")
        revision = _la_revision(cliente, cuenta["cabeceras"])
        propuesta = [p for p in revision["propuestas"] if p["segura"]][0]
        cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [propuesta["clave"]]},
        )
        contacto = cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json()[0]
        corregida = cliente.put(
            f"/api/contactos/{contacto['id']}",
            headers=cuenta["cabeceras"],
            json={"nombre": "Cooperativa de Peñaranda", "telefono": "923 000 000"},
        )
        assert corregida.status_code == 200, corregida.text

        deshecho = cliente.post(
            "/api/contactos/migracion/deshacer", headers=cuenta["cabeceras"], json={}
        ).json()
        assert deshecho["fichas"] == 0
        assert len(deshecho["se_quedan"]) == 1
        assert "Cooperativa de Peñaranda" in deshecho["se_quedan"][0]
        quedan = cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json()
        assert [c["nombre"] for c in quedan] == ["Cooperativa de Peñaranda"]

    def test_si_la_propuesta_cambia_no_se_apunta_nada(self, cliente, cuenta, una_factura):
        """Confirmar una lista que ya no es la misma apuntaría algo distinto de lo que se enseñó."""
        una_factura("Cooperativa Agrícola de Peñaranda")
        revision = _la_revision(cliente, cuenta["cabeceras"])
        clave = [p for p in revision["propuestas"] if p["segura"]][0]["clave"]
        # Entra una factura nueva del mismo proveedor entre mirar y confirmar.
        una_factura(numero_factura="2026/00125")
        respuesta = cliente.post(
            "/api/contactos/migracion/aplicar",
            headers=cuenta["cabeceras"],
            json={"claves": [clave]},
        )
        assert respuesta.status_code == 409, respuesta.text
        assert cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json() == []


# --------------------------------------------------------------------------
# 6. Enlazar no borra el nombre
# --------------------------------------------------------------------------


class TestEnlazarNoBorraElNombre:
    def test_enlazar_deja_el_texto_del_papel_como_estaba(
        self, cliente, cuenta, db_sesion, escribir_nombre
    ):
        factura = escribir_nombre("facturas", "proveedor", "Cooperativa Agricola de Penaranda")
        creada = cliente.post(
            "/api/contactos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Cooperativa Agrícola de Peñaranda", "papeles": ["proveedor"]},
        ).json()
        respuesta = cliente.post(
            f"/api/contactos/{creada['id']}/enlaces",
            headers=cuenta["cabeceras"],
            json={"tabla": "facturas", "campo": "proveedor", "registro_id": factura},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert (
            _texto_de_la_factura(db_sesion, cuenta["explotacion_id"], factura)
            == "Cooperativa Agricola de Penaranda"
        )
        assert respuesta.json()["nombres_escritos"] == ["Cooperativa Agricola de Penaranda"]

    def test_quitar_el_enlace_deja_el_texto_del_papel_como_estaba(
        self, cliente, cuenta, db_sesion, escribir_nombre
    ):
        factura = escribir_nombre("facturas", "proveedor", "Cooperativa Agrícola de Peñaranda")
        creada = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "La coop"}
        ).json()
        ficha = cliente.post(
            f"/api/contactos/{creada['id']}/enlaces",
            headers=cuenta["cabeceras"],
            json={"tabla": "facturas", "campo": "proveedor", "registro_id": factura},
        ).json()
        enlace = ficha["vivos"][0]["id"]
        quitado = cliente.delete(
            f"/api/contactos/{creada['id']}/enlaces/{enlace}", headers=cuenta["cabeceras"]
        )
        assert quitado.status_code == 200, quitado.text
        assert quitado.json()["enlaces"] == 0
        assert (
            _texto_de_la_factura(db_sesion, cuenta["explotacion_id"], factura)
            == "Cooperativa Agrícola de Peñaranda"
        )

    def test_cambiar_el_nombre_de_la_ficha_no_cambia_la_factura(
        self, cliente, cuenta, db_sesion, escribir_nombre
    ):
        """**El contrato lo pide con estas palabras**: «cambiar nombre muestra vínculos sin alterar
        facturas históricas»."""
        factura = escribir_nombre("facturas", "proveedor", "Coop. de Peñaranda")
        creada = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "Coop. de Peñaranda"}
        ).json()
        cliente.post(
            f"/api/contactos/{creada['id']}/enlaces",
            headers=cuenta["cabeceras"],
            json={"tabla": "facturas", "campo": "proveedor", "registro_id": factura},
        )
        cambiada = cliente.put(
            f"/api/contactos/{creada['id']}",
            headers=cuenta["cabeceras"],
            json={"nombre": "Cooperativa Agrícola de Peñaranda S.C.L."},
        )
        assert cambiada.status_code == 200, cambiada.text
        assert cambiada.json()["nombre"] == "Cooperativa Agrícola de Peñaranda S.C.L."
        assert cambiada.json()["enlaces"] == 1
        assert (
            _texto_de_la_factura(db_sesion, cuenta["explotacion_id"], factura)
            == "Coop. de Peñaranda"
        )

    def test_se_dice_cuando_el_papel_ha_cambiado_desde_el_enlace(
        self, cliente, cuenta, db_sesion, escribir_nombre
    ):
        """El enlace no se rompe, pero **tampoco se calla**: puede que ya no sea el mismo."""
        factura = escribir_nombre("facturas", "proveedor", "Coop. de Peñaranda")
        creada = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "La coop"}
        ).json()
        cliente.post(
            f"/api/contactos/{creada['id']}/enlaces",
            headers=cuenta["cabeceras"],
            json={"tabla": "facturas", "campo": "proveedor", "registro_id": factura},
        )
        fila = db_sesion.get(models.Factura, factura)
        fila.proveedor = "Transportes López"
        db_sesion.commit()

        ficha = cliente.get(f"/api/contactos/{creada['id']}", headers=cuenta["cabeceras"]).json()
        assert ficha["enlaces"] == 1
        escrito = ficha["vivos"][0]["escrito"]
        assert escrito["texto_cambiado"] is True
        assert escrito["texto"] == "Transportes López"
        assert escrito["texto_de_entonces"] == "Coop. de Peñaranda"

    def test_una_puerta_que_no_existe_no_se_puede_enlazar(self, cliente, cuenta):
        """Por aquí entra un nombre de tabla del navegador: **no puede acabar en una consulta**."""
        creada = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "Alguien"}
        ).json()
        respuesta = cliente.post(
            f"/api/contactos/{creada['id']}/enlaces",
            headers=cuenta["cabeceras"],
            json={"tabla": "usuarios", "campo": "clave_hash", "registro_id": 1},
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_un_texto_no_puede_tener_dos_duenos(self, cliente, cuenta, una_factura):
        factura = una_factura()
        primera = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "Uno"}
        ).json()
        segunda = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "Otro"}
        ).json()
        cuerpo = {"tabla": "facturas", "campo": "proveedor", "registro_id": factura}
        assert (
            cliente.post(
                f"/api/contactos/{primera['id']}/enlaces",
                headers=cuenta["cabeceras"],
                json=cuerpo,
            ).status_code
            == 200
        )
        repetido = cliente.post(
            f"/api/contactos/{segunda['id']}/enlaces", headers=cuenta["cabeceras"], json=cuerpo
        )
        assert repetido.status_code == 409, repetido.text
        assert "Uno" in repetido.json()["detail"]
        # Y sigue teniendo un solo dueño.
        assert cliente.get(f"/api/contactos/{segunda['id']}", headers=cuenta["cabeceras"]).json()[
            "enlaces"
        ] == 0

    def test_enlazar_un_hueco_se_dice(self, cliente, cuenta, una_factura):
        factura = una_factura(nombre=None)
        creada = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "Alguien"}
        ).json()
        respuesta = cliente.post(
            f"/api/contactos/{creada['id']}/enlaces",
            headers=cuenta["cabeceras"],
            json={"tabla": "facturas", "campo": "proveedor", "registro_id": factura},
        )
        assert respuesta.status_code == 409, respuesta.text

    def test_un_documento_borrado_no_cuenta_como_vinculo(
        self, cliente, cuenta, db_sesion, una_factura
    ):
        """Si el agricultor borra la factura, el vínculo se queda huérfano y **no se cuenta**."""
        factura = una_factura()
        creada = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "La coop"}
        ).json()
        cliente.post(
            f"/api/contactos/{creada['id']}/enlaces",
            headers=cuenta["cabeceras"],
            json={"tabla": "facturas", "campo": "proveedor", "registro_id": factura},
        )
        assert cliente.get(f"/api/contactos/{creada['id']}", headers=cuenta["cabeceras"]).json()[
            "enlaces"
        ] == 1
        db_sesion.delete(db_sesion.get(models.Factura, factura))
        db_sesion.commit()
        ficha = cliente.get(f"/api/contactos/{creada['id']}", headers=cuenta["cabeceras"]).json()
        assert ficha["enlaces"] == 0
        assert ficha["vivos"] == []
        # Y ese nombre ya no se ofrece para enlazar: no está.
        assert _los_escritos(cliente, cuenta["cabeceras"]) == []


# --------------------------------------------------------------------------
# Los papeles
# --------------------------------------------------------------------------


class TestLosPapeles:
    def test_una_ficha_puede_tener_varios_papeles(self, cliente, cuenta):
        creada = cliente.post(
            "/api/contactos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Cooperativa Agrícola de Peñaranda", "papeles": ["proveedor", "comprador"]},
        )
        assert creada.status_code == 201, creada.text
        assert sorted(creada.json()["papeles"]) == ["comprador", "proveedor"]

        # Y se pueden marcar y desmarcar de uno en uno, sin tocar los demás.
        solo_uno = cliente.post(
            f"/api/contactos/{creada.json()['id']}/papeles",
            headers=cuenta["cabeceras"],
            json={"papel": "transportista", "puesto": True},
        )
        assert solo_uno.status_code == 200, solo_uno.text
        assert sorted(solo_uno.json()["papeles"]) == ["comprador", "proveedor", "transportista"]
        quitado = cliente.post(
            f"/api/contactos/{creada.json()['id']}/papeles",
            headers=cuenta["cabeceras"],
            json={"papel": "comprador", "puesto": False},
        )
        assert sorted(quitado.json()["papeles"]) == ["proveedor", "transportista"]

    def test_corregir_la_ficha_sin_hablar_de_los_papeles_no_le_quita_ninguno(self, cliente, cuenta):
        """**Un campo que no viene no es «quítalos todos».**

        Lo encontró la auditoría del 05/10/2026 leyendo el código de al lado, y no lo cazaba ninguna
        prueba: `ContactoEntrada.papeles` valía `[]` cuando la petición no lo mandaba, y guardar los
        papeles borra todo lo que no venga en la lista, así que **corregir el teléfono desde la API
        dejaba la ficha sin ninguno** —en silencio y sin que nadie lo hubiera pedido—. La pantalla manda
        siempre los papeles, así que solo se alcanzaba desde fuera; pero el contrato §2 pide comparación
        de cambios, no sobreescritura, y un dato que no se manda no se puede leer como un «ninguno».

        Y la otra mitad, que es lo que hace que la primera no sea una puerta cerrada: **quien quiere
        quitarlos lo dice** mandando `papeles: []`.
        """
        creada = cliente.post(
            "/api/contactos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Cooperativa Agrícola de Peñaranda", "papeles": ["proveedor", "comprador"]},
        ).json()
        assert sorted(creada["papeles"]) == ["comprador", "proveedor"]

        # 1. Se corrige el teléfono **sin decir nada de los papeles**: tienen que seguir los dos.
        corregida = cliente.put(
            f"/api/contactos/{creada['id']}",
            headers=cuenta["cabeceras"],
            json={"nombre": "Cooperativa Agrícola de Peñaranda", "telefono": "923 000 000"},
        )
        assert corregida.status_code == 200, corregida.text
        assert sorted(corregida.json()["papeles"]) == ["comprador", "proveedor"], (
            "corregir el teléfono le ha quitado los papeles a la ficha"
        )
        assert corregida.json()["telefono"] == "923 000 000", "y el teléfono sí se ha corregido"

        # 2. Y ahora sí se dice que no tiene ninguno: se quitan los dos.
        sin_papeles = cliente.put(
            f"/api/contactos/{creada['id']}",
            headers=cuenta["cabeceras"],
            json={"nombre": "Cooperativa Agrícola de Peñaranda", "papeles": []},
        )
        assert sin_papeles.json()["papeles"] == [], "quien manda la lista vacía los está quitando"

    def test_un_papel_que_no_existe_se_dice_y_no_se_guarda(self, cliente, cuenta):
        creada = cliente.post(
            "/api/contactos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Alguien", "papeles": ["proveedor", "inventado"]},
        )
        assert creada.status_code == 422, creada.text
        assert cliente.get("/api/contactos", headers=cuenta["cabeceras"]).json() == []
        # Y al marcar uno a mano, tampoco: ni se apunta ni se calla.
        buena = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "Alguien"}
        ).json()
        marcado = cliente.post(
            f"/api/contactos/{buena['id']}/papeles",
            headers=cuenta["cabeceras"],
            json={"papel": "inventado", "puesto": True},
        )
        assert marcado.status_code == 422, marcado.text
        assert cliente.get(f"/api/contactos/{buena['id']}", headers=cuenta["cabeceras"]).json()[
            "papeles"
        ] == []

    def test_los_papeles_que_dicen_sus_propios_papeles(self, cliente, cuenta, una_factura):
        """Si una factura suya está enlazada, es el proveedor: se dice, y lo marca él."""
        factura = una_factura()
        creada = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "La coop"}
        ).json()
        ficha = cliente.post(
            f"/api/contactos/{creada['id']}/enlaces",
            headers=cuenta["cabeceras"],
            json={"tabla": "facturas", "campo": "proveedor", "registro_id": factura},
        ).json()
        assert ficha["papeles"] == []
        assert ficha["papeles_segun_lo_escrito"] == ["proveedor"]

    def test_cada_papel_del_catalogo_tiene_su_texto_y_esta_en_la_interfaz(self, cliente):
        """Un papel sin palabras deja un botón en blanco, y eso no revienta nada: se ve mal."""
        respuesta = cliente.get("/api/interfaz")
        assert respuesta.status_code == 200
        vocabulario = respuesta.json()
        de_la_interfaz = [uno["valor"] for uno in vocabulario["papeles_de_un_contacto"]]
        assert de_la_interfaz == list(logica.PAPELES)
        for uno in vocabulario["papeles_de_un_contacto"]:
            assert uno["texto"].strip(), f"el papel {uno['valor']} sale sin nombre"

    def test_ninguna_clave_de_la_lista_de_campos_tiene_su_texto_de_fuera(self):
        """Cada puerta de enlace dice de dónde es con una clave, y esa clave tiene que tener texto.

        Es el fallo que este proyecto persigue: **un texto que falta no revienta, deja un hueco**, y
        aquí el hueco sería «el nombre de una factura» sin decir que es de una factura.
        """
        for enlace in logica.ENLACES:
            assert enlace.clave, f"{enlace.tabla}.{enlace.campo} no dice de dónde es"
            assert f"tabla_{enlace.clave}" in textos.CONTACTOS, (
                f"falta el texto de la tabla «{enlace.clave}»"
            )

    def test_cada_papel_del_catalogo_tiene_su_nombre(self):
        for papel in logica.PAPELES:
            assert papel in textos.CONTACTOS["papeles"], f"el papel {papel} no tiene nombre"
            assert textos.CONTACTOS["papeles"][papel].strip()


# --------------------------------------------------------------------------
# 5. De otra finca no se ve nada
# --------------------------------------------------------------------------


class TestDeOtraFincaNoSeVeNada:
    def test_la_ficha_de_otra_finca_no_se_ve(self, cliente, cuenta, crear_cuenta):
        otra = crear_cuenta("otro@ejemplo.test", "Otro", "11111111H")
        mia = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "Mi proveedor"}
        ).json()
        # 404 y no 403: no se filtra ni siquiera si existe.
        for respuesta in (
            cliente.get(f"/api/contactos/{mia['id']}", headers=otra["cabeceras"]),
            cliente.put(
                f"/api/contactos/{mia['id']}",
                headers=otra["cabeceras"],
                json={"nombre": "Lo que sea"},
            ),
            cliente.delete(f"/api/contactos/{mia['id']}", headers=otra["cabeceras"]),
            cliente.post(
                f"/api/contactos/{mia['id']}/papeles",
                headers=otra["cabeceras"],
                json={"papel": "proveedor", "puesto": True},
            ),
            cliente.post(
                f"/api/contactos/{mia['id']}/enlaces",
                headers=otra["cabeceras"],
                json={"tabla": "facturas", "campo": "proveedor", "registro_id": 1},
            ),
        ):
            assert respuesta.status_code == 404, respuesta.text
        assert cliente.get("/api/contactos", headers=otra["cabeceras"]).json() == []

    def test_el_nombre_escrito_de_otra_finca_no_se_puede_enlazar(
        self, cliente, cuenta, crear_cuenta, una_factura
    ):
        """El aislamiento no es solo de las fichas: **el nombre escrito también es suyo**."""
        otra = crear_cuenta("otro@ejemplo.test", "Otro", "11111111H")
        factura = una_factura()
        mia = cliente.post(
            "/api/contactos", headers=cuenta["cabeceras"], json={"nombre": "Mi proveedor"}
        ).json()
        respuesta = cliente.post(
            f"/api/contactos/{mia['id']}/enlaces",
            headers=otra["cabeceras"],
            json={"tabla": "facturas", "campo": "proveedor", "registro_id": factura},
        )
        assert respuesta.status_code == 404, respuesta.text
        assert cliente.get("/api/contactos/escritos", headers=otra["cabeceras"]).json() == []

    def test_la_revision_de_otra_finca_no_trae_nada_suyo(
        self, cliente, cuenta, crear_cuenta, una_factura
    ):
        una_factura("Cooperativa Agrícola de Peñaranda")
        otra = crear_cuenta("otro@ejemplo.test", "Otro", "11111111H")
        revision = _la_revision(cliente, otra["cabeceras"])
        assert revision["propuestas"] == []
        assert revision["total_escritos"] == 0


class TestSinValeDeEntrada:
    def test_sin_vale_no_se_ve_ni_se_toca_nada(self, cliente):
        for respuesta in (
            cliente.get("/api/contactos"),
            cliente.post("/api/contactos", json={"nombre": "Alguien"}),
            cliente.get("/api/contactos/1"),
            cliente.get("/api/contactos/escritos"),
            cliente.get("/api/contactos/migracion"),
            cliente.post("/api/contactos/migracion/aplicar", json={"claves": []}),
            cliente.post("/api/contactos/migracion/deshacer", json={}),
        ):
            assert respuesta.status_code == 401, respuesta.text


# --------------------------------------------------------------------------
# Lo que esta sección promete por escrito
# --------------------------------------------------------------------------


class TestLasPuertasSonLasQueSon:
    def test_las_siete_puertas_son_las_siete(self):
        """**La lista está escrita a mano y se comprueba a mano**, para que crezca a conciencia.

        El día que se añada una octava (el taller de una máquina, el transportista de una entrega),
        esta prueba falla y obliga a decidir dos cosas: si de verdad guarda un nombre escrito y con
        qué papel. Es el mismo trato que `correcciones.tablas_que_apuntan_a` hace con las tablas.
        """
        assert [(uno.tabla, uno.campo) for uno in logica.ENLACES] == [
            ("facturas", "proveedor"),
            ("recepciones", "proveedor"),
            ("ventas_de_cosecha", "comprador"),
            ("analiticas", "laboratorio"),
            ("productos_fitosanitarios", "proveedor"),
            ("aplicadores", "nombre"),
            ("asesores", "nombre"),
        ]

    def test_no_hay_dos_enlaces_al_mismo_sitio(self):
        sitios = [(uno.tabla, uno.campo) for uno in logica.ENLACES]
        assert len(sitios) == len(set(sitios)), "hay dos enlaces al mismo campo: dos verdades"

    def test_las_tablas_y_las_columnas_existen_de_verdad(self):
        """Una lista escrita a mano se queda vieja: esto la ata a los modelos."""
        for enlace in logica.ENLACES:
            modelo = _modelo(enlace.tabla)
            assert hasattr(modelo, enlace.campo), f"{enlace.tabla} ya no tiene {enlace.campo}"
            if enlace.campo_nif:
                assert hasattr(modelo, enlace.campo_nif)
            if enlace.campo_fecha:
                assert hasattr(modelo, enlace.campo_fecha)
            for columna in enlace.referencia:
                assert hasattr(modelo, columna)
            assert enlace.papel in logica.PAPELES

    def test_las_tres_tablas_nuevas_separan_las_fincas(self):
        """`explotacion_id` en las tres: es lo que impide que un agricultor vea lo de otro."""
        for tabla in ("contactos", "papeles_de_un_contacto", "enlaces_de_contacto"):
            assert "explotacion_id" in models.Base.metadata.tables[tabla].columns, (
                f"«{tabla}» no dice de qué finca es"
            )

    def test_dos_contactos_pueden_llamarse_igual(self):
        """**Y no es un descuido**: el contrato pide que dos homónimos no se mezclen (E5).

        Lo que sí es único es el enlace: un texto escrito no puede tener dos dueños.
        """
        unicas = [
            restriccion
            for restriccion in models.Contacto.__table__.constraints
            if restriccion.__class__.__name__ == "UniqueConstraint"
        ]
        assert unicas == [], "alguien ha puesto una restricción de unicidad en el nombre"
        unicos_del_enlace = [
            tuple(columna.name for columna in restriccion.columns)
            for restriccion in models.EnlaceDeContacto.__table__.constraints
            if restriccion.__class__.__name__ == "UniqueConstraint"
        ]
        assert unicos_del_enlace == [
            ("explotacion_id", "tabla", "campo", "registro_id")
        ], unicos_del_enlace


# --------------------------------------------------------------------------
# La copia de los textos que usan las pruebas del móvil
# --------------------------------------------------------------------------


def _los_textos_de_la_copia() -> set[str]:
    """Todas las cadenas que hay dentro del fichero de pruebas de JavaScript.

    Se sacan con una expresión regular y no con un analizador: el fichero es JavaScript y lo que se
    busca son las frases, que están todas entre comillas dobles. Si alguien cambia una, deja de estar.
    """
    copia = COPIA_DE_LOS_TESTS.read_text(encoding="utf-8")
    return set(re.findall(r'"([^"\n]*)"', copia))


def _todos_los_textos_de_contactos() -> list[str]:
    """Los textos de contactos, uno por uno, incluidos los de dentro del diccionario de los papeles."""
    salida: list[str] = []
    for clave, valor in textos.CONTACTOS.items():
        if isinstance(valor, dict):
            salida.extend(str(texto) for texto in valor.values())
        else:
            salida.append(str(valor))
    return salida


class TestLaCopiaDeLosTextosNoSeQuedaVieja:
    """**Un test que lee ficheros necesita su propia prueba** (`AGENTS.md`).

    La copia de los textos de `tests_js/contactos.test.js` es lo que hace que las pruebas de las cuatro
    pantallas comprueben algo: si a esa copia le falta una frase, la pantalla sale con un hueco en la
    prueba y **la prueba da por bueno cualquier cosa**. Es el mismo trato que el T10 le dio a la suya.
    """

    def test_la_copia_esta_y_tiene_textos(self):
        assert COPIA_DE_LOS_TESTS.exists(), "no encuentro la copia de los textos en tests_js"
        assert len(_los_textos_de_la_copia()) > 100, "la copia se ha quedado sin textos"

    def test_no_falta_ni_un_texto_del_servidor(self):
        copia = _los_textos_de_la_copia()
        faltan = sorted({texto for texto in _todos_los_textos_de_contactos() if texto not in copia})
        assert faltan == [], (
            "estos textos los sirve el servidor y no están en la copia de "
            "tests_js/contactos.test.js, así que las pruebas de las pantallas no los ven:\n"
            + "\n".join(f"  · {texto[:90]}" for texto in faltan)
        )

    def test_la_copia_lleva_todos_los_papeles(self):
        """Un papel que falte en la copia es un botón en blanco que ninguna prueba mira."""
        copia = COPIA_DE_LOS_TESTS.read_text(encoding="utf-8")
        faltan = [papel for papel in logica.PAPELES if f"    {papel}: " not in copia]
        assert faltan == [], f"a la copia le faltan papeles: {faltan}"

    def test_la_copia_lleva_las_tablas_donde_hay_un_nombre_escrito(self):
        """Cada puerta de enlace se nombra en pantalla con la clave `tabla_<clave>`.

        Si a la copia le falta una de esas frases, la prueba de la pantalla ve un rótulo vacío y no
        comprueba que el agricultor sepa de qué papel es el nombre.
        """
        copia = _los_textos_de_la_copia()
        faltan = sorted(
            {
                str(textos.CONTACTOS[f"tabla_{enlace.clave}"])
                for enlace in logica.ENLACES
                if f"tabla_{enlace.clave}" in textos.CONTACTOS
            }
            - copia
        )
        assert faltan == [], f"a la copia le faltan los nombres de las tablas: {faltan}"


class TestLaLogicaDeLosNombres:
    """La comparación de nombres, sin base de datos: es pura y se prueba sola."""

    def test_el_mismo_nombre_con_mayusculas_distintas_es_el_mismo(self):
        assert logica.clave_exacta("COOPERATIVA X") == logica.clave_exacta("Cooperativa X")

    def test_una_tilde_de_menos_no_es_el_mismo_nombre(self):
        assert logica.clave_exacta("José Pérez") != logica.clave_exacta("Jose Perez")
        assert logica.se_parecen("José Pérez", "Jose Perez") is True

    def test_una_razon_social_de_mas_se_parece(self):
        assert logica.se_parecen("Cooperativa X", "Cooperativa X S.L.") is True

    def test_dos_apellidos_distintos_no_se_parecen(self):
        assert logica.se_parecen("Transportes López", "Transportes Pérez") is False

    def test_un_nombre_y_su_mitad_no_se_parecen_por_error(self):
        """La regla del prefijo es por palabras, no por letras: «Juan» no es «Juana»."""
        assert logica.se_parecen("Juan", "Juana") is False

    def test_el_nif_se_compara_sin_puntos_ni_guiones(self):
        assert logica.nif_normalizado("B-34.123.456") == "B34123456"
        assert logica.nif_normalizado("  ") is None
        assert logica.nif_normalizado(None) is None

    def test_el_nombre_de_una_ficha_sale_del_que_mas_se_repite(self):
        """Con el mismo NIF y dos formas de escribirlo, gana la que él escribe más veces.

        Las dos formas tienen que ser **compatibles** (se parecen), que es lo que exige la regla desde
        el arreglo del defecto 1: «Cooperativa de Peñaranda» y «Cooperativa de Peñaranda S.C.L.» son la
        misma empresa escrita de dos maneras.
        """
        escritos = [
            logica.Escrito("facturas", "proveedor", 1, "Cooperativa de Peñaranda", "B1", "proveedor", "facturas"),
            logica.Escrito("facturas", "proveedor", 2, "Cooperativa de Peñaranda", "B1", "proveedor", "facturas"),
            logica.Escrito("facturas", "proveedor", 3, "Cooperativa de Peñaranda S.C.L.", "B1", "proveedor", "facturas"),
        ]
        propuestas = logica.proponer(escritos)
        assert len(propuestas) == 1
        assert propuestas[0].segura is True
        assert propuestas[0].nombre == "Cooperativa de Peñaranda"
        assert propuestas[0].motivo == "mismo_nif"

    def test_un_nif_con_dos_nombres_que_no_se_parecen_no_junta_ni_en_la_logica_pura(self):
        """La regla del defecto 1, sin base de datos: es la misma función que usa el guion."""
        escritos = [
            logica.Escrito("facturas", "proveedor", 1, "Juan García López", "B12345678"),
            logica.Escrito("facturas", "proveedor", 2, "Pedro López Ruiz", "B12345678"),
        ]
        propuestas = logica.proponer(escritos)
        assert len(propuestas) == 1
        assert propuestas[0].segura is False
        assert propuestas[0].motivo == "mismo_nif_nombres_distintos"
        assert propuestas[0].nifs == ["B12345678"]
        assert logica.nombres_compatibles("Juan García López", "Pedro López Ruiz") is False
        assert logica.nombres_compatibles("Cooperativa X", "COOPERATIVA X") is True
        assert logica.nombres_compatibles("Cooperativa X", "Cooperativa X S.L.") is True

    def test_un_nombre_en_blanco_no_propone_nada(self):
        assert logica.proponer([logica.Escrito("facturas", "proveedor", 1, "   ")]) == []

    def test_el_resumen_cuenta_los_cuatro_numeros(self):
        escritos = [
            logica.Escrito("facturas", "proveedor", 1, "Cooperativa X"),
            logica.Escrito("facturas", "proveedor", 2, "Cooperativa X"),
            logica.Escrito("facturas", "proveedor", 3, "Cooperativa X S.L."),
        ]
        resumen = logica.resumen_de_la_propuesta(logica.proponer(escritos))
        # Dos fichas que se pueden apuntar: «Cooperativa X» (con sus dos papeles) y «Cooperativa X
        # S.L.» por separado. **No una con las dos dentro**: eso sería fusionarlas.
        assert resumen["fichas"] == 2
        assert resumen["nombres"] == 3
        assert resumen["se_parecen"] == 1
        assert resumen["homonimos"] == 0

    def test_lo_que_se_parece_no_se_cuenta_como_ficha_a_apuntar(self):
        """El número que el agricultor lee como «esto se puede apuntar» **no incluye lo dudoso**."""
        escritos = [
            logica.Escrito("facturas", "proveedor", 1, "Juan García", nif="1A"),
            logica.Escrito("facturas", "proveedor", 2, "Juan García", nif="2B"),
        ]
        propuestas = logica.proponer(escritos)
        assert [p.segura for p in propuestas] == [False]
        assert logica.resumen_de_la_propuesta(propuestas)["fichas"] == 0
        assert logica.resumen_de_la_propuesta(propuestas)["homonimos"] == 1


# --------------------------------------------------------------------------
# El guion de la migración: mirar no toca nada, y el viaje de ida y vuelta cuadra
# --------------------------------------------------------------------------


def _el_guion():
    """El guion de la migración, cargado como módulo. **Se importa, no se ejecuta.**

    Es la misma forma de probarlo que la del guion del T02
    (`tests/test_aceptacion_copia_y_migracion.py`): así se prueban sus funciones de verdad y no una
    copia de lo que dicen.
    """
    import importlib.util

    especificacion = importlib.util.spec_from_file_location(
        "migrar_contactos_para_las_pruebas", GUION_DE_MIGRACION
    )
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def _una_base_de_dos_facturas(ruta, proveedores: list[tuple[str, str]]) -> None:
    """Una base pequeña con una finca y una factura **por cada** (nombre, NIF) que se le pase.

    Se fabrica aquí y no se copia la del agricultor: es la base sobre la que corre el guion de la
    migración en las pruebas, y tiene que ser de mentira.
    """
    from sqlalchemy.orm import Session

    from app import database

    motor = database.crear_engine(f"sqlite:///{pathlib.Path(ruta).as_posix()}")
    database.crear_tablas(motor)
    with Session(motor) as sesion:
        sesion.add(models.Explotacion(id=1, nombre="Finca de prueba", nif="70922320A"))
        sesion.flush()
        sesion.add(
            models.Campana(
                id=1,
                explotacion_id=1,
                anio=2026,
                fecha_inicio=dt.date(2025, 9, 1),
                fecha_fin=dt.date(2026, 8, 31),
            )
        )
        sesion.flush()
        for indice, (proveedor, nif) in enumerate(proveedores, start=1):
            sesion.add(
                models.Factura(
                    id=indice,
                    explotacion_id=1,
                    campana_id=1,
                    fecha=dt.date(2026, 3, indice),
                    proveedor=proveedor,
                    proveedor_nif=nif,
                    numero_factura=f"2026/0000{indice}",
                )
            )
        sesion.commit()
    motor.dispose()


def _una_base_con_nombres(ruta, con_tablas_nuevas: bool = True) -> None:
    """Una base pequeña con una finca y tres nombres escritos a mano.


    `con_tablas_nuevas=False` deja la base **como la del agricultor cuando todavía no se ha arrancado
    el programa con el T11**: sin las tres tablas de los contactos. Es el caso que se encontró
    ensayando sobre una copia de su base de verdad, y el que hace falta para comprobar que el informe
    no cambia nada.

    **Y desde el T12 las tres tablas se tiran DESPUÉS de apuntar las ventas, no antes** (03/10/2026).
    El motivo es del esquema y no se puede evitar: `ventas_de_cosecha.contacto_id` apunta a
    `contactos` desde el T12, y SQLite **no deja escribir en una tabla cuyo padre no existe**, ni
    aunque el valor que se escribe sea nulo (`no such table: main.contactos`). O sea que el orden de
    antes construía un estado que el programa no puede producir: en una instalación de verdad
    `crear_tablas()` crea las tablas de los contactos antes de que nadie apunte nada, así que «hay
    ventas apuntadas y no existe la tabla de contactos» no pasa nunca. Lo que sí es de verdad —y es
    lo que esta prueba comprueba— es la base que se encuentra el guion **antes de que el programa se
    arranque con el T11**: con sus tres ventas escritas y sin las tablas nuevas. Se llega a eso igual
    que antes, solo que en el orden que SQLite admite.
    """
    from sqlalchemy.orm import Session

    from app import database

    motor = database.crear_engine(f"sqlite:///{pathlib.Path(ruta).as_posix()}")
    database.crear_tablas(motor)
    with Session(motor) as sesion:
        sesion.add(models.Explotacion(id=1, nombre="Finca de prueba", nif="70922320A"))
        sesion.flush()
        sesion.add(
            models.Campana(
                id=1,
                explotacion_id=1,
                anio=2026,
                fecha_inicio=dt.date(2025, 9, 1),
                fecha_fin=dt.date(2026, 8, 31),
            )
        )
        sesion.flush()
        for indice, (comprador, albaran) in enumerate(
            (
                ("Cooperativa Agrícola de Peñaranda", "ALB-1"),
                ("Cooperativa Agrícola de Peñaranda", "ALB-2"),
                ("Cooperativa Agricola de Penaranda", "ALB-3"),
            ),
            start=1,
        ):
            sesion.add(
                models.VentaDeCosecha(
                    id=indice,
                    explotacion_id=1,
                    campana_id=1,
                    tipo="comercializada",
                    fecha=dt.date(2026, 7, indice),
                    producto="Trigo blando",
                    cantidad=1000.0,
                    unidad="kg",
                    comprador=comprador,
                    numero_albaran=albaran,
                )
            )
        sesion.commit()
    if not con_tablas_nuevas:
        # Ahora sí: se tiran las tres tablas del T11 y queda una base «de antes» de verdad.
        with motor.begin() as conexion:
            for tabla in ("enlaces_de_contacto", "papeles_de_un_contacto", "contactos"):
                conexion.exec_driver_sql(f'DROP TABLE IF EXISTS "{tabla}"')
    motor.dispose()


def _huella(ruta) -> str:
    import hashlib

    return hashlib.sha256(pathlib.Path(ruta).read_bytes()).hexdigest()


def _el_guion_corre(el_guion, *argumentos) -> int:
    """Ejecuta el guion como se ejecuta de verdad, con sus argumentos, y devuelve su código de salida."""
    import sys

    guardados = sys.argv
    sys.argv = ["migrar_contactos.py", *argumentos]
    try:
        return el_guion.main()
    finally:
        sys.argv = guardados


class TestElGuionDeLaMigracion:
    def test_el_informe_no_cambia_ni_un_byte_de_la_base(self, tmp_path, capsys):
        """**Mirar no puede cambiar nada, y esto se descubrió ensayando sobre la base de verdad.**

        La primera versión del guion ponía el esquema al día (creaba las tablas que faltaban) **también
        en el informe**, así que imprimía «no se ha tocado nada» después de haber tocado el esquema.
        Aquí se comprueba por el otro lado: la huella del fichero, antes y después.
        """
        ruta = tmp_path / "de_antes.db"
        _una_base_con_nombres(ruta, con_tablas_nuevas=False)
        antes = _huella(ruta)

        codigo = _el_guion_corre(_el_guion(), "--base", str(ruta))

        assert codigo == 0, capsys.readouterr().out
        assert _huella(ruta) == antes, "el informe ha cambiado la base del agricultor"
        salida = capsys.readouterr().out
        assert "no se ha tocado nada" in salida
        assert "las tablas de los contactos" in salida, (
            "no se dice que la base todavía no tiene las tablas nuevas"
        )
        # Y se propone lo que hay: dos nombres iguales (una ficha) y uno que se parece (no se junta).
        assert "Cooperativa Agrícola de Peñaranda" in salida
        assert "se parecen" in salida

    def test_el_viaje_de_ida_y_vuelta_cuadra_y_no_toca_los_nombres(self, tmp_path, capsys):
        """Apuntar y deshacer: las mismas filas que había, y **ni una letra escrita tocada**."""
        from sqlalchemy import func, select
        from sqlalchemy.orm import Session

        from app import database

        ruta = tmp_path / "ida_y_vuelta.db"
        _una_base_con_nombres(ruta)
        el_guion = _el_guion()
        antes = _huella_de_los_nombres(el_guion, ruta)

        assert _el_guion_corre(el_guion, "--base", str(ruta), "--migrar") == 0, capsys.readouterr().out
        salida = capsys.readouterr().out
        assert "textos escritos tocados: 0" in salida
        assert "huella de antes" in salida
        motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
        with Session(motor) as sesion:
            assert sesion.scalar(select(func.count()).select_from(models.Contacto)) == 2, (
                "no se han apuntado las dos fichas que había que apuntar"
            )
            assert sesion.scalar(select(func.count()).select_from(models.EnlaceDeContacto)) == 3
        motor.dispose()
        assert _huella_de_los_nombres(el_guion, ruta) == antes, (
            "la migración ha cambiado un nombre escrito a mano"
        )

        assert _el_guion_corre(el_guion, "--base", str(ruta), "--deshacer") == 0, capsys.readouterr().out
        motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
        with Session(motor) as sesion:
            assert sesion.scalar(select(func.count()).select_from(models.Contacto)) == 0
            assert sesion.scalar(select(func.count()).select_from(models.EnlaceDeContacto)) == 0
        motor.dispose()
        assert _huella_de_los_nombres(el_guion, ruta) == antes

    def test_la_migracion_del_guion_usa_la_misma_regla_que_la_pantalla(self, tmp_path, capsys):
        """**La regla de qué se puede juntar vive en un solo sitio**, y esa es la mitad del ticket.

        El guion llama a la puerta de la pantalla (`contactos_api.aplicar_la_migracion`) en vez de
        escribir las fichas él. Si tuviera su propia copia, un día la pantalla diría una cosa y el guion
        otra. Se comprueba leyendo el fichero: tiene que nombrar esa puerta.
        """
        codigo = GUION_DE_MIGRACION.read_text(encoding="utf-8")
        assert "api.aplicar_la_migracion(" in codigo
        assert "api.deshacer_la_migracion(" in codigo
        assert "logica.proponer(" in codigo
        # Y **ni un UPDATE**: lo único que se escribe son fichas y enlaces nuevos.
        assert "UPDATE " not in codigo.upper(), "el guion escribe en tablas de documentos"


def _huella_de_los_nombres(el_guion, ruta) -> str:
    """La huella que el propio guion calcula sobre lo escrito: es la que él comprueba antes y después."""
    return el_guion._huella_del_texto(pathlib.Path(ruta))
