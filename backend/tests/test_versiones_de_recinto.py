"""La identidad y las versiones del recinto (T05, 02/10/2026).

## Qué se prueba aquí, y por qué

El contrato (§2.1 y su entrega T05) pide tres cosas que hasta ahora no se podían hacer:

  1. **Guardar una versión por tierra, campaña y fuente**, con la referencia, si el polígono es
     válido, el área de la geometría, el área del SIGPAC y el área declarada —tres magnitudes
     distintas— y el estado de revisión.
  2. **Comparar** dos campañas y decir, por cada recinto, si está `igual`, `cambiado`,
     `desaparecido` o `nuevo`, **con el porqué**.
  3. **Importar un lote de recintos de forma repetible**: primero previsualizar sin tocar la base y
     después aplicar, de manera que aplicarlo dos veces no duplique nada.

Estas pruebas van **todas contra una base temporal** (la que prepara `conftest.py`; la base del
agricultor no se abre nunca) y con **datos construidos aquí**, salvo dos que leen respuestas de
verdad del SIGPAC guardadas en `data/sigpac/` para comprobar que el lote se puede montar con lo que
devuelve el conector, **sin salir a internet**.

Lo que se mide, y no se afirma:

  · **La idempotencia se cuenta.** Se guarda una foto de todas las filas de `versiones_de_recinto`
    antes y después de aplicar el lote por segunda vez, y se comparan las dos fotos enteras y el
    número de apuntes de la auditoría. No se dice «es idempotente»: se comprueba fila a fila.
  · **Las hectáreas declaradas** se comparan con las calculadas y con las del SIGPAC en el mismo
    recinto, para ver que son tres números distintos y que la declarada no se mueve.
  · **La versión de la campaña anterior** se lee otra vez después de importar la nueva y se compara
    con lo que decía antes, campo por campo.
  · **Lo que no se sabe** se comprueba que llega como vacío y **que no es cero**, en la respuesta de
    la API y no solo en la base.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from sqlalchemy import select

from app import catalogos, geo, models, sigpac
from app import versiones_de_recinto as versiones

RAIZ = pathlib.Path(__file__).resolve().parents[2]
RUTA_SIGPAC = RAIZ / "data" / "sigpac"

# --------------------------------------------------------------------------
# Los recintos con los que se trabaja
#
# Son los de la parcela 503, polígono 51 del municipio 70 de la provincia 37: los mismos números que
# usa la respuesta de verdad del SIGPAC que hay guardada en `data/sigpac/`. Los trozos se dibujan
# aquí a mano y miden lo que dicen medir: el primero es un cuadrado de unos 100 m de lado (0,93 ha
# medidos por el programa). El tercero es el mismo tipo de trozo, pero pegado al primero, para que se
# pisen de verdad.
# --------------------------------------------------------------------------

CUADRADO_1 = "POLYGON((-5.0 41.0,-4.999 41.0,-4.999 41.001,-5.0 41.001,-5.0 41.0))"
CUADRADO_1_MAS_GRANDE = "POLYGON((-5.0 41.0,-4.998 41.0,-4.998 41.002,-5.0 41.002,-5.0 41.0))"
CUADRADO_2_QUE_PISA_AL_1 = (
    "POLYGON((-4.9995 41.0005,-4.9985 41.0005,-4.9985 41.0015,-4.9995 41.0015,-4.9995 41.0005))"
)

REFERENCIA_1 = "37-70-0-0-503-51-1"
REFERENCIA_2 = "37-70-0-0-503-51-2"
REFERENCIA_3 = "37-70-0-0-503-51-3"

# Las formas que se ponen por defecto a los recintos 1 y 2, y nada al resto: los demás recintos de
# estas pruebas son los que **no traen forma**, que es uno de los casos que hay que cubrir.
FORMAS_POR_DEFECTO = {1: CUADRADO_1, 2: CUADRADO_2_QUE_PISA_AL_1}


def un_recinto(numero: int = 1, **cambios) -> dict:
    """Un recinto del lote, como lo mandaría el SIGPAC.

    Lo que se cambia en cada prueba se pasa por parámetro; lo que no se pasa **no viaja**, y ahí está
    la mitad de las pruebas de este fichero: lo que no viene se queda vacío y no se rellena solo.
    """
    datos = {
        "provincia": "37",
        "municipio": "70",
        "agregado": 0,
        "zona": 0,
        "poligono": 503,
        "numero_parcela": 51,
        "numero_recinto": numero,
        "geometria": FORMAS_POR_DEFECTO.get(numero),
        "area_sigpac_ha": 0.93,
        "uso_sigpac": "TA",
    }
    datos.update(cambios)
    return datos


# --------------------------------------------------------------------------
# Preparación
# --------------------------------------------------------------------------


@pytest.fixture
def crear_campana(cliente, cuenta):
    """Una campaña más, para poder comparar dos años.

    El año se pide **relativo a la campaña que ya existe** (la del año en curso, que la crea el alta
    de la cuenta), para que estas pruebas no dependan de en qué año se ejecuten.
    """

    def _crear(anio: int, **cambios):
        datos = {"anio": anio, "fecha_inicio": f"{anio}-01-01", "fecha_fin": f"{anio}-12-31"}
        datos.update(cambios)
        respuesta = cliente.post("/api/campanas", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


@pytest.fixture
def otra_campana(crear_campana, campana):
    """La campaña siguiente, que es con la que se compara casi todo."""
    return crear_campana(campana["anio"] + 1)


def _el_lote(campana: dict, recintos: list[dict], fuente: str = "sigpac", **cambios) -> dict:
    lote = {"campana_id": campana["id"], "fuente": fuente, "recintos": recintos}
    lote.update(cambios)
    return lote


def _previsualizar(cliente, cabeceras, lote) -> dict:
    respuesta = cliente.post("/api/versiones/previsualizar", headers=cabeceras, json=lote)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _aplicar(cliente, cabeceras, lote) -> dict:
    respuesta = cliente.post("/api/versiones/aplicar", headers=cabeceras, json=lote)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _las_versiones(cliente, cabeceras, **parametros) -> list[dict]:
    respuesta = cliente.get("/api/versiones", headers=cabeceras, params=parametros)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _la_tierra_de(cliente, cabeceras, numero_recinto: int) -> dict:
    tierras = cliente.get("/api/parcelas", headers=cabeceras).json()
    return [t for t in tierras if t["numero_recinto"] == numero_recinto][0]


def _la_foto_de_lo_guardado(db_sesion) -> list[dict]:
    """Todo lo que hay en `versiones_de_recinto`, campo por campo.

    Es lo que permite **medir** la idempotencia en vez de afirmarla: se guarda esta foto antes y
    después de aplicar el lote por segunda vez y se comparan las dos enteras.
    """
    filas = db_sesion.scalars(
        select(models.VersionDeRecinto).order_by(models.VersionDeRecinto.id)
    ).all()
    return [
        {
            "id": fila.id,
            "parcela_id": fila.parcela_id,
            "campana_id": fila.campana_id,
            "fuente": fila.fuente,
            "fecha_consulta": fila.fecha_consulta,
            "clave": fila.clave,
            "referencia": fila.referencia,
            "poligono_valido": fila.poligono_valido,
            "geometria": fila.geometria,
            "area_geometria_ha": fila.area_geometria_ha,
            "area_sigpac_ha": fila.area_sigpac_ha,
            "area_declarada_ha": fila.area_declarada_ha,
            "uso_sigpac": fila.uso_sigpac,
            "estado_revision": fila.estado_revision,
        }
        for fila in filas
    ]


def _cuantos_apuntes_de_la_version(db_sesion) -> int:
    """Cuántos apuntes de auditoría ha dejado la importación de recintos.

    Se cuentan **solo los de esta entidad** a propósito: el alta de la cuenta y todo lo demás también
    escribe en la auditoría, y contar todo mezclaría cosas que no vienen al caso.
    """
    return len(
        [
            apunte
            for apunte in db_sesion.scalars(select(models.Auditoria)).all()
            if apunte.entidad == "version_de_recinto"
        ]
    )


def _por_clave(versiones_de_la_lista: list[dict], referencia: str) -> dict:
    return [una for una in versiones_de_la_lista if una["referencia"] == referencia][0]


# --------------------------------------------------------------------------
# 1. Tres recintos: uno igual, uno cambiado y uno sin geometría
# --------------------------------------------------------------------------


class TestLosTresRecintosConSuOrigenYSuAnio:
    def test_uno_igual_uno_cambiado_y_uno_sin_forma(
        self, cliente, cuenta, campana, db_sesion
    ):
        """La prueba de aceptación de E2, tal cual la pide el contrato.

        «Tres recintos, uno cambiado y otro sin geometría, visibles con origen y año.»

        Se importa un lote con tres recintos —uno con su forma, otro con su forma y otro **sin
        forma**— y después el mismo lote con el segundo cambiado. La segunda vez el primero está
        **igual**, el segundo **cambiado** y el tercero sigue **sin forma**, y los tres se ven en la
        lista con su origen (el SIGPAC) y su año.
        """
        primero = un_recinto(1)
        segundo = un_recinto(2)
        tercero = un_recinto(3)  # sin geometría: `un_recinto` no le pone forma
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [primero, segundo, tercero]))

        # El segundo cambia de forma y de superficie del SIGPAC; el primero y el tercero, no.
        segundo_cambiado = un_recinto(
            2, geometria=CUADRADO_1_MAS_GRANDE, area_sigpac_ha=3.72
        )
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [primero, segundo_cambiado, tercero]),
        )

        assert (plan["nuevos"], plan["cambiados"], plan["iguales"], plan["sin_forma"]) == (
            0,
            1,
            2,
            1,
        ), plan
        cambiado = [uno for uno in plan["detalle"] if uno["estado"] == "cambiado"][0]
        assert cambiado["referencia"] == REFERENCIA_2
        # El porqué, con las tres cosas que se han movido: la forma que vino, **el área que mide esa
        # forma** (que es otra cosa y se guarda aparte) y la superficie que dice el SIGPAC.
        assert sorted(cambiado["que_cambia"]) == [
            "el área de la forma",
            "la forma del trozo",
            "la superficie del SIGPAC",
        ]

        # Y los tres se ven en la lista, con su origen y su año.
        versiones = _las_versiones(cliente, cuenta["cabeceras"])
        assert len(versiones) == 3
        for una in versiones:
            assert una["fuente"] == "sigpac"
            assert una["fuente_texto"] == "SIGPAC"
            assert una["anio"] == campana["anio"]
            assert una["campana_id"] == campana["id"]

        el_sin_forma = _por_clave(versiones, REFERENCIA_3)
        assert el_sin_forma["tiene_forma"] is False
        assert el_sin_forma["geometria"] is None
        assert el_sin_forma["area_geometria_ha"] is None
        assert "sin forma" in el_sin_forma["como_esta"].lower()

        # Los otros dos sí tienen forma, y el dibujo del trozo se puede medir.
        assert _por_clave(versiones, REFERENCIA_1)["tiene_forma"] is True
        assert _por_clave(versiones, REFERENCIA_1)["area_geometria_ha"] == pytest.approx(0.9331, abs=0.002)

        # El que cambió dice lo mismo en la lista que en el plan.
        assert _por_clave(versiones, REFERENCIA_2)["area_sigpac_ha"] == 3.72

    def test_un_recinto_sin_forma_entra_igual_y_se_ve_en_la_lista(
        self, cliente, cuenta, campana
    ):
        """«Un polígono ausente no se inventa» (contrato, E2), y además no desaparece.

        El recinto sin forma entra con su geometría vacía, sale en la lista y lo dice en su frase.
        Lo que no se hace es dibujarle nada ni sacarlo de la tabla.
        """
        plan = _aplicar(
            cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(3, alias="El alto")])
        )
        assert plan["nuevos"] == 1
        assert plan["sin_forma"] == 1

        versiones = _las_versiones(cliente, cuenta["cabeceras"])
        assert len(versiones) == 1
        assert versiones[0]["geometria"] is None
        assert versiones[0]["tiene_forma"] is False
        assert versiones[0]["dibujo"] if "dibujo" in versiones[0] else True  # no hay dibujo que dar
        # La tierra se ha dado de alta igual, con su nombre.
        assert versiones[0]["tierra"] == "El alto"

    def test_la_version_dice_de_que_fuente_viene_cada_cosa(
        self, cliente, cuenta, campana
    ):
        """El origen es la mitad del dato: lo que dijo el agricultor no es lo que dice el SIGPAC.

        El mismo recinto, del SIGPAC y del agricultor, son **dos versiones distintas**, cada una con
        su fuente. Mezclarlas haría imposible saber quién dijo qué.
        """
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1)], fuente="sigpac"),
        )
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(
                campana,
                [un_recinto(1, area_declarada_ha=0.8)],
                fuente="agricultor",
            ),
        )

        versiones = _las_versiones(cliente, cuenta["cabeceras"])
        assert len(versiones) == 2
        assert {una["fuente_texto"] for una in versiones} == {"SIGPAC", "Lo que dijiste tú"}
        del_agricultor = [una for una in versiones if una["fuente"] == "agricultor"][0]
        assert del_agricultor["area_declarada_ha"] == 0.8
        del_sigpac = [una for una in versiones if una["fuente"] == "sigpac"][0]
        assert del_sigpac["area_declarada_ha"] is None


# --------------------------------------------------------------------------
# 2. Cambiar de campaña no altera la historia
# --------------------------------------------------------------------------


class TestCambiarDeCampanaNoTocaLaHistoria:
    def test_la_version_de_la_campana_anterior_sigue_diciendo_lo_mismo(
        self, cliente, cuenta, campana, otra_campana, db_sesion
    ):
        """El contrato lo pide así: «cambio de campaña no altera la historia».

        Se importa el recinto en una campaña, se apunta **campo por campo** lo que quedó guardado, se
        importa el mismo recinto **cambiado** en la campaña siguiente y se vuelve a leer la versión
        de la primera campaña: tiene que estar exactamente igual, con su forma vieja y su área vieja.
        """
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))
        antes = _la_foto_de_lo_guardado(db_sesion)
        assert len(antes) == 1

        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(
                otra_campana,
                [un_recinto(1, geometria=CUADRADO_1_MAS_GRANDE, area_sigpac_ha=3.72)],
            ),
        )

        despues = _la_foto_de_lo_guardado(db_sesion)
        assert len(despues) == 2, "la campaña nueva tiene que ser una versión aparte"
        la_vieja = [fila for fila in despues if fila["campana_id"] == campana["id"]]
        assert la_vieja == antes, (
            "importar la campaña nueva ha cambiado lo que decía la campaña anterior"
        )
        # Y la vieja sigue con su forma y su superficie de entonces, no con las nuevas.
        assert la_vieja[0]["area_sigpac_ha"] == 0.93
        assert la_vieja[0]["geometria"] == CUADRADO_1

    def test_la_comparacion_dice_que_cambio_y_por_que(
        self, cliente, cuenta, campana, otra_campana
    ):
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1, area_declarada_ha=0.9)]),
        )
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(
                otra_campana,
                [un_recinto(1, geometria=CUADRADO_1_MAS_GRANDE, area_declarada_ha=0.9)],
            ),
        )
        tierra = _la_tierra_de(cliente, cuenta["cabeceras"], 1)

        respuesta = cliente.get(
            "/api/versiones/comparar",
            headers=cuenta["cabeceras"],
            params={
                "parcela_id": tierra["id"],
                "campana_antes": campana["id"],
                "campana_despues": otra_campana["id"],
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        comparacion = respuesta.json()

        assert (comparacion["iguales"], comparacion["cambiados"]) == (0, 1)
        assert (comparacion["desaparecidos"], comparacion["nuevos"]) == (0, 0)
        assert comparacion["anio_antes"] == campana["anio"]
        assert comparacion["anio_despues"] == otra_campana["anio"]
        assert comparacion["tierra"] == tierra["alias"]
        cambio = comparacion["cambios"][0]
        assert cambio["estado"] == "cambiado"
        assert cambio["que_cambio"] == ["la forma del trozo", "el área de la forma"]
        # Y trae las dos versiones enteras, para poder enseñarlas juntas.
        assert cambio["antes"]["area_sigpac_ha"] == 0.93
        assert cambio["despues"]["area_geometria_ha"] > cambio["antes"]["area_geometria_ha"]

    def test_una_version_que_no_cambio_sale_como_igual(
        self, cliente, cuenta, campana, otra_campana
    ):
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(otra_campana, [un_recinto(1)]))
        tierra = _la_tierra_de(cliente, cuenta["cabeceras"], 1)
        comparacion = cliente.get(
            "/api/versiones/comparar",
            headers=cuenta["cabeceras"],
            params={
                "parcela_id": tierra["id"],
                "campana_antes": campana["id"],
                "campana_despues": otra_campana["id"],
            },
        ).json()
        assert comparacion["iguales"] == 1
        assert comparacion["cambios"][0]["que_cambio"] == []


# --------------------------------------------------------------------------
# 3. El estado «desaparecido», y el «nuevo»
# --------------------------------------------------------------------------


class TestUnRecintoQueYaNoViene:
    def test_desaparecido_cuando_el_recinto_no_viene_en_el_lote_nuevo(
        self, cliente, cuenta, campana, otra_campana
    ):
        """«El estado desaparecido sale cuando un recinto que estaba ya no viene en el lote nuevo.»

        Y sale **por tierra**: en una finca entera, «un recinto desaparecido» solo significa algo si
        se sabe de qué tierra era.
        """
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1), un_recinto(2), un_recinto(3)]),
        )
        # En la campaña nueva vienen el 1 y el 3: el 2 ya no está.
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(otra_campana, [un_recinto(1), un_recinto(3)]))

        comparacion = cliente.get(
            "/api/versiones/comparar-explotacion",
            headers=cuenta["cabeceras"],
            params={"campana_antes": campana["id"], "campana_despues": otra_campana["id"]},
        )
        assert comparacion.status_code == 200, comparacion.text
        datos = comparacion.json()
        assert (datos["iguales"], datos["cambiados"]) == (2, 0)
        assert datos["desaparecidos"] == 1
        assert datos["nuevos"] == 0
        assert "1 desaparecidos" in datos["resumen"]

        el_que_falta = [uno for uno in datos["cambios"] if uno["estado"] == "desaparecido"][0]
        assert el_que_falta["referencia"] == REFERENCIA_2
        assert el_que_falta["antes"] is not None
        assert el_que_falta["despues"] is None
        assert el_que_falta["tierra"] == _la_tierra_de(cliente, cuenta["cabeceras"], 2)["alias"]

    def test_desaparecido_en_la_ficha_de_una_sola_tierra(
        self, cliente, cuenta, campana, otra_campana
    ):
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(2)]))
        tierra = _la_tierra_de(cliente, cuenta["cabeceras"], 2)
        # En la campaña nueva se importa otro recinto, pero no ese.
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(otra_campana, [un_recinto(1)]))

        comparacion = cliente.get(
            "/api/versiones/comparar",
            headers=cuenta["cabeceras"],
            params={
                "parcela_id": tierra["id"],
                "campana_antes": campana["id"],
                "campana_despues": otra_campana["id"],
            },
        ).json()
        assert comparacion["desaparecidos"] == 1
        assert comparacion["cambios"][0]["referencia"] == REFERENCIA_2

    def test_nuevo_cuando_el_recinto_no_estaba_antes(
        self, cliente, cuenta, campana, otra_campana
    ):
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(otra_campana, [un_recinto(1), un_recinto(3)]),
        )
        datos = cliente.get(
            "/api/versiones/comparar-explotacion",
            headers=cuenta["cabeceras"],
            params={"campana_antes": campana["id"], "campana_despues": otra_campana["id"]},
        ).json()
        assert (datos["iguales"], datos["nuevos"], datos["desaparecidos"]) == (1, 1, 0)
        el_nuevo = [uno for uno in datos["cambios"] if uno["estado"] == "nuevo"][0]
        assert el_nuevo["antes"] is None
        assert el_nuevo["despues"]["referencia"] == REFERENCIA_3


# --------------------------------------------------------------------------
# 4. La importación es repetible (idempotencia medida)
# --------------------------------------------------------------------------


class TestLaImportacionRepetible:
    def test_aplicarla_dos_veces_deja_exactamente_lo_mismo(
        self, cliente, cuenta, campana, db_sesion
    ):
        """**La prueba central de T05**, y está medida, no afirmada.

        Se aplica el lote, se guarda una foto de todas las filas de `versiones_de_recinto` (campo
        por campo) y el número de apuntes de la auditoría; se aplica **otra vez** el mismo lote y se
        vuelve a mirar todo. Ni una fila nueva, ni un campo distinto, ni un apunte de auditoría más.
        """
        lote = _el_lote(
            campana,
            [
                un_recinto(1, area_declarada_ha=0.9),
                un_recinto(2),
                un_recinto(3),
            ],
            fecha_consulta="2026-03-01",
        )
        primera = _aplicar(cliente, cuenta["cabeceras"], lote)
        assert (primera["aplicada"], primera["versiones_creadas"]) == (True, 3)

        foto = _la_foto_de_lo_guardado(db_sesion)
        auditoria = _cuantos_apuntes_de_la_version(db_sesion)
        tierras = cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()
        assert len(foto) == 3

        segunda = _aplicar(cliente, cuenta["cabeceras"], lote)

        assert segunda["versiones_creadas"] == 0
        assert segunda["versiones_actualizadas"] == 0
        assert segunda["tierras_creadas"] == []
        assert segunda["tierras_nuevas"] == 0
        assert segunda["iguales"] == 3
        assert (segunda["nuevos"], segunda["cambiados"]) == (0, 0)
        assert _la_foto_de_lo_guardado(db_sesion) == foto
        assert _cuantos_apuntes_de_la_version(db_sesion) == auditoria
        assert cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json() == tierras

        # Y una tercera vez, por si acaso el segundo intento hubiera dejado algo a medias.
        _aplicar(cliente, cuenta["cabeceras"], lote)
        assert _la_foto_de_lo_guardado(db_sesion) == foto
        assert _cuantos_apuntes_de_la_version(db_sesion) == auditoria

    def test_el_lote_repetido_con_orden_distinto_tampoco_duplica(
        self, cliente, cuenta, campana, db_sesion
    ):
        """El mismo lote con los recintos en otro orden es el mismo lote.

        Un fichero que se lee de otra manera, o un envío que se reordena por el camino, no puede
        crear tres versiones más.
        """
        recintos = [un_recinto(1), un_recinto(2), un_recinto(3)]
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, recintos))
        foto = _la_foto_de_lo_guardado(db_sesion)
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, list(reversed(recintos))),
        )
        assert _la_foto_de_lo_guardado(db_sesion) == foto

    def test_previsualizar_no_escribe_nada(self, cliente, cuenta, campana, db_sesion):
        """La otra mitad de la importación repetible: **primero se ensaya**.

        Después de previsualizar tres veces el mismo lote no hay ni una versión, ni una tierra nueva,
        ni un apunte de auditoría. Y el plan que devuelve la previsualización es el que se aplica
        después, para que lo que se enseña antes no pueda diferir de lo que pasa.
        """
        lote = _el_lote(campana, [un_recinto(1), un_recinto(2), un_recinto(3)])
        planes = [_previsualizar(cliente, cuenta["cabeceras"], lote) for _ in range(3)]
        assert planes[0] == planes[1] == planes[2]
        assert planes[0]["aplicada"] is False
        assert (planes[0]["nuevos"], planes[0]["cambiados"], planes[0]["iguales"]) == (3, 0, 0)
        assert planes[0]["tierras_nuevas"] == 3

        assert _la_foto_de_lo_guardado(db_sesion) == []
        assert cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json() == []
        assert _cuantos_apuntes_de_la_version(db_sesion) == 0

        aplicado = _aplicar(cliente, cuenta["cabeceras"], lote)
        assert aplicado["aplicada"] is True
        assert aplicado["nuevos"] == planes[0]["nuevos"]
        assert aplicado["diferencias_de_superficie"] == planes[0]["diferencias_de_superficie"]

        # El detalle es el mismo **salvo una cosa, y se dice cuál**: en la previsualización la tierra
        # todavía no existe, así que su identificador y su nombre están vacíos. No se le puede
        # inventar un identificador a algo que no se ha creado, y una previsualización que prometiera
        # un número que después no es el mismo sería peor que no darlo.
        sin_la_tierra = [
            {clave: valor for clave, valor in uno.items() if clave not in ("parcela_id", "tierra")}
            for uno in aplicado["detalle"]
        ]
        assert sin_la_tierra == [
            {clave: valor for clave, valor in uno.items() if clave not in ("parcela_id", "tierra")}
            for uno in planes[0]["detalle"]
        ]
        assert [uno["parcela_id"] for uno in planes[0]["detalle"]] == [None, None, None]
        assert all(uno["parcela_id"] is not None for uno in aplicado["detalle"])
        assert all(uno["tierra"] for uno in aplicado["detalle"])

    def test_un_cambio_de_verdad_si_se_escribe_y_se_apunta_en_la_auditoria(
        self, cliente, cuenta, campana, db_sesion
    ):
        """Lo contrario de la idempotencia, para que la prueba de arriba signifique algo.

        Si la segunda aplicación no escribiera **nunca**, la prueba anterior pasaría sin comprobar
        nada. Aquí se cambia un dato de verdad y se comprueba que la versión se actualiza y que la
        auditoría guarda lo que había.
        """
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))
        auditoria_antes = _cuantos_apuntes_de_la_version(db_sesion)

        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1, area_sigpac_ha=1.4, uso_sigpac="PR")]),
        )
        assert (plan["cambiados"], plan["versiones_actualizadas"]) == (1, 1)
        assert plan["versiones_creadas"] == 0
        assert len(_la_foto_de_lo_guardado(db_sesion)) == 1

        guardada = _la_foto_de_lo_guardado(db_sesion)[0]
        assert (guardada["area_sigpac_ha"], guardada["uso_sigpac"]) == (1.4, "PR")
        assert _cuantos_apuntes_de_la_version(db_sesion) == auditoria_antes + 1
        del_cambio = [
            apunte
            for apunte in db_sesion.scalars(select(models.Auditoria)).all()
            if apunte.entidad == "version_de_recinto" and apunte.accion == "actualizar"
        ][0]
        assert del_cambio.datos["antes"]["area_sigpac_ha"] == 0.93
        assert del_cambio.datos["ahora"]["area_sigpac_ha"] == 1.4
        assert sorted(del_cambio.datos["que_cambio"]) == ["el uso", "la superficie del SIGPAC"]


# --------------------------------------------------------------------------
# 5. Lo que no se sabe no es cero, y las hectáreas declaradas no se sustituyen
# --------------------------------------------------------------------------


class TestLoQueNoSeSabeNoEsCero:
    def test_un_recinto_sin_superficie_no_sale_con_cero_hectareas(
        self, cliente, cuenta, campana
    ):
        """Un hueco no se convierte en un cero. Es la regla de todo el proyecto (T02, A7).

        Se importa un recinto **sin ninguna superficie** —ni del SIGPAC ni declarada, y sin forma— y
        se comprueba en la respuesta de la API que las tres áreas llegan vacías. Un 0 ahí sería
        decir que la tierra no tiene hectáreas, que es justo lo que dejaba una tierra sin poder
        tratarse.
        """
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(
                campana,
                [
                    {
                        "provincia": "37",
                        "municipio": "70",
                        "agregado": 0,
                        "zona": 0,
                        "poligono": 503,
                        "numero_parcela": 51,
                        "numero_recinto": 9,
                    }
                ],
            ),
        )
        assert plan["nuevos"] == 1

        version = _las_versiones(cliente, cuenta["cabeceras"])[0]
        assert version["area_geometria_ha"] is None
        assert version["area_sigpac_ha"] is None
        assert version["area_declarada_ha"] is None
        assert version["area_sigpac_ha"] != 0
        assert version["fecha_consulta"] is None, (
            "la fecha de consulta no se rellena con la de hoy: el lote no la ha dicho"
        )
        # Y el programa lo dice, en vez de callarse: con una sola superficie no hay nada que comparar.
        diferencia = plan["diferencias_de_superficie"][0]
        assert diferencia["diferencia_ha"] is None
        assert "no hay nada que comparar" in diferencia["texto"]

        # Y la tierra recién creada tampoco tiene un cero donde no se sabe.
        tierra = _la_tierra_de(cliente, cuenta["cabeceras"], 9)
        assert tierra["superficie_ha"] is None
        assert tierra["superficie_sigpac_ha"] is None

    def test_la_fecha_de_consulta_se_guarda_cuando_el_lote_la_dice(
        self, cliente, cuenta, campana
    ):
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1)], fecha_consulta="2026-03-01"),
        )
        assert _las_versiones(cliente, cuenta["cabeceras"])[0]["fecha_consulta"] == "2026-03-01"

    def test_una_referencia_a_la_que_le_falta_el_recinto_no_es_valida(
        self, cliente, cuenta, campana
    ):
        """«Una referencia a la que le falta el recinto no lo es», y se dice cuál falta.

        El recinto se apunta igual —porque se sabe de qué tierra es, que se le dice— pero queda
        marcado: `poligono_valido` en falso y la frase diciendo qué le falta.
        """
        tierra = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={"alias": "Sin recinto", "superficie_ha": None},
        ).json()
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(
                campana,
                [
                    {
                        "parcela_id": tierra["id"],
                        "referencia": "37-70-0-0-503-51",  # seis números: falta el recinto
                        "geometria": CUADRADO_1,
                    }
                ],
            ),
        )
        assert plan["nuevos"] == 1
        version = _las_versiones(cliente, cuenta["cabeceras"], parcela_id=tierra["id"])[0]
        assert version["poligono_valido"] is False
        assert version["referencia"] is None
        assert version["numero_recinto"] is None
        assert "falta el número de recinto" in version["como_esta"]
        # Y lo que sí vino está guardado, tal y como vino.
        assert (version["provincia"], version["municipio"]) == ("37", "70")
        assert (version["poligono"], version["numero_parcela"]) == (503, 51)
        assert version["area_geometria_ha"] is not None


class TestLasHectareasDeclaradasNoSeSustituyen:
    def test_la_declarada_no_se_cambia_por_la_calculada_ni_por_la_del_sigpac(
        self, cliente, cuenta, campana
    ):
        """El contrato lo dice literal: «Nunca sustituir hectáreas declaradas por las calculadas».

        En un mismo recinto conviven tres números distintos: lo que mide la forma que vino
        (0,9331 ha), lo que dice el SIGPAC (0,93) y lo que declara el agricultor (1,2, que es más
        grande porque además lleva una franja que no está en el recinto). Los tres se guardan por
        separado, cada uno en su campo, y la declarada sigue siendo la declarada.
        """
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1, area_sigpac_ha=0.93, area_declarada_ha=1.2)]),
        )
        version = _las_versiones(cliente, cuenta["cabeceras"])[0]
        assert version["area_declarada_ha"] == 1.2
        assert version["area_sigpac_ha"] == 0.93
        assert version["area_geometria_ha"] == pytest.approx(0.9331, abs=0.002)
        assert len({
            version["area_declarada_ha"],
            version["area_sigpac_ha"],
            round(version["area_geometria_ha"], 3),
        }) == 3, "las tres magnitudes tienen que ser tres números distintos"

        # Y la tierra que se ha dado de alta lleva la declarada, no la del SIGPAC ni la medida.
        tierra = _la_tierra_de(cliente, cuenta["cabeceras"], 1)
        assert tierra["superficie_ha"] == 1.2
        assert tierra["superficie_sigpac_ha"] == 0.93
        assert tierra["superficie_oficial"] is False

    def test_una_importacion_que_no_trae_la_declarada_no_se_la_lleva_por_delante(
        self, cliente, cuenta, campana
    ):
        """Un dato que no viene no es un dato que se sabe que ya no está.

        El agricultor declara 1,2 ha. Al día siguiente el SIGPAC vuelve a mandar el recinto con la
        forma corregida y **sin decir nada de las hectáreas declaradas**: esas siguen donde estaban.
        """
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1, area_declarada_ha=1.2)]),
        )
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1, geometria=CUADRADO_1_MAS_GRANDE)]),
        )
        assert plan["cambiados"] == 1

        version = _las_versiones(cliente, cuenta["cabeceras"])[0]
        assert version["area_declarada_ha"] == 1.2, (
            "una importación que no menciona las hectáreas declaradas no puede borrarlas"
        )
        assert version["area_geometria_ha"] == pytest.approx(3.73, abs=0.01)
        assert version["area_declarada_ha"] != version["area_geometria_ha"]

    def test_una_tierra_nueva_sin_declarada_se_queda_sin_superficie_de_cultivo(
        self, cliente, cuenta, campana
    ):
        """Al dar de alta una tierra desde un lote **no se copia el SIGPAC a lo que se cultiva**.

        Son magnitudes distintas a propósito (`models.Parcela.superficie_ha`), así que si el lote no
        trae hectáreas declaradas la tierra se queda sin esa superficie —en blanco, no en cero— y con
        la del SIGPAC en su propio campo.
        """
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(4, area_sigpac_ha=2.5)]),
        )
        tierra = _la_tierra_de(cliente, cuenta["cabeceras"], 4)
        assert tierra["superficie_ha"] is None
        assert tierra["superficie_sigpac_ha"] == 2.5


# --------------------------------------------------------------------------
# 6. El aislamiento entre explotaciones
# --------------------------------------------------------------------------


class TestUnaTierraDeOtraFincaNoSeVe:
    def test_la_lista_no_trae_lo_de_otra_finca(self, cliente, cuenta, crear_cuenta, campana):
        """Lo de otra finca no se ve. Ni en la lista, ni contando."""
        otra = crear_cuenta("otro@ejemplo.test", nombre="Otro agricultor", nif="12345678Z")
        su_campana = cliente.get("/api/campanas/actual", headers=otra["cabeceras"]).json()
        _aplicar(
            cliente,
            otra["cabeceras"],
            _el_lote(su_campana, [un_recinto(1, alias="La suya")]),
        )
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1, alias="La mía")]))

        mias = _las_versiones(cliente, cuenta["cabeceras"])
        assert len(mias) == 1
        assert mias[0]["tierra"] == "La mía"
        assert "La suya" not in json.dumps(mias)

    def test_no_se_puede_listar_la_tierra_de_otra_finca(
        self, cliente, cuenta, crear_cuenta
    ):
        otra = crear_cuenta("otro@ejemplo.test", nombre="Otro agricultor", nif="12345678Z")
        suya = cliente.post(
            "/api/parcelas",
            headers=otra["cabeceras"],
            json={"alias": "La suya", "superficie_ha": 1.0},
        ).json()

        respuesta = cliente.get(
            "/api/versiones",
            headers=cuenta["cabeceras"],
            params={"parcela_id": suya["id"]},
        )
        # 404 y no 403: así no se dice si esa tierra existe en otro cuaderno.
        assert respuesta.status_code == 404

    def test_no_se_puede_importar_un_lote_contra_la_tierra_de_otra_finca(
        self, cliente, cuenta, crear_cuenta, campana, db_sesion
    ):
        """Y no solo no se ve: **no se puede escribir en ella**, ni de refilón.

        Se manda un lote que apunta a una tierra de otra finca y la importación se corta entera con
        un 404, sin guardar la parte que sí era suya. Un lote a medias sería peor que un lote
        rechazado: el agricultor creería que se ha importado todo.
        """
        otra = crear_cuenta("otro@ejemplo.test", nombre="Otro agricultor", nif="12345678Z")
        suya = cliente.post(
            "/api/parcelas",
            headers=otra["cabeceras"],
            json={"alias": "La suya", "superficie_ha": 1.0},
        ).json()

        respuesta = cliente.post(
            "/api/versiones/aplicar",
            headers=cuenta["cabeceras"],
            json=_el_lote(
                campana,
                [un_recinto(1), {"parcela_id": suya["id"], "geometria": CUADRADO_2_QUE_PISA_AL_1}],
            ),
        )
        assert respuesta.status_code == 404, respuesta.text
        assert _la_foto_de_lo_guardado(db_sesion) == [], "no se ha guardado ni el recinto bueno"

    def test_no_se_puede_comparar_con_la_campana_de_otra_finca(
        self, cliente, cuenta, crear_cuenta
    ):
        otra = crear_cuenta("otro@ejemplo.test", nombre="Otro agricultor", nif="12345678Z")
        su_campana = cliente.get("/api/campanas/actual", headers=otra["cabeceras"]).json()
        respuesta = cliente.get(
            "/api/versiones/comparar-explotacion",
            headers=cuenta["cabeceras"],
            params={"campana_antes": su_campana["id"], "campana_despues": su_campana["id"]},
        )
        assert respuesta.status_code == 404


# --------------------------------------------------------------------------
# 7. Solapes y diferencias de superficie
# --------------------------------------------------------------------------


class TestLosSolapesYLasSuperficies:
    def test_dos_recintos_que_se_pisan_se_dicen_y_no_se_corrige_nada(
        self, cliente, cuenta, campana, db_sesion
    ):
        """El contrato pide **detectar** los solapes y decirlo, no arreglarlos.

        Los dos recintos se pisan de verdad (el segundo tiene parte de su superficie dentro del
        primero). Se avisa, se dice con qué recinto y se guardan los dos tal y como vinieron: el
        programa no toca un vértice ni una hectárea por su cuenta.
        """
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1), un_recinto(2)]),
        )
        assert len(plan["solapes"]) == 1
        solape = plan["solapes"][0]
        assert solape["como"] == geo.SOLAPE_SEGURO
        assert {solape["referencia_a"], solape["referencia_b"]} == {REFERENCIA_1, REFERENCIA_2}
        assert "se pisan" in solape["como_texto"].lower()

        # Y no se ha corregido nada: las dos formas están guardadas tal cual.
        guardadas = {fila["referencia"]: fila["geometria"] for fila in _la_foto_de_lo_guardado(db_sesion)}
        assert guardadas[REFERENCIA_1] == CUADRADO_1
        assert guardadas[REFERENCIA_2] == CUADRADO_2_QUE_PISA_AL_1

    def test_una_tierra_cuyo_recinto_cambia_no_avisa_de_solape_consigo_misma(
        self, cliente, cuenta, campana
    ):
        """Un recinto que cambia de forma **no se pisa consigo mismo**, y no puede parecer que sí.

        La versión vieja de esa tierra sigue en la base hasta que se actualiza, y tiene la forma de
        antes. Si se comparara con la nueva, saldría «se pisan» en cada corrección de un recinto, que
        es un aviso falso y de los que hacen desconfiar de todos los demás.
        """
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1, geometria=CUADRADO_1_MAS_GRANDE)]),
        )
        assert plan["cambiados"] == 1
        assert plan["solapes"] == []

    def test_un_solape_con_lo_que_ya_estaba_guardado_tambien_se_ve(
        self, cliente, cuenta, campana
    ):
        """El solape que importa no siempre viene en el mismo lote.

        Se importa un recinto hoy y el de al lado la semana que viene: el aviso tiene que salir
        igual, porque el solape es entre dos recintos de la finca, no entre dos líneas de un fichero.
        """
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))
        plan = _previsualizar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(2)]))
        assert plan["nuevos"] == 1
        assert len(plan["solapes"]) == 1
        assert plan["solapes"][0]["referencia_a"] == REFERENCIA_2
        assert plan["solapes"][0]["como"] == geo.SOLAPE_SEGURO

    def test_dos_recintos_lejanos_no_se_avisan(self, cliente, cuenta, campana):
        lejos = un_recinto(
            5, geometria="POLYGON((-4.5 41.0,-4.499 41.0,-4.499 41.001,-4.5 41.001,-4.5 41.0))"
        )
        plan = _aplicar(
            cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1), lejos])
        )
        assert plan["solapes"] == []

    def test_una_diferencia_de_superficie_grande_sale_marcada(self, cliente, cuenta, campana):
        """Geometría contra SIGPAC contra declarada: cuando se llevan mucho, se avisa.

        El motivo está medido: el área calculada de un recinto oficial se separa un 0,13 % de la
        superficie que publica el SIGPAC (`tests/test_geo.py`). Aquí se le da al recinto una
        superficie declarada de 4 ha cuando la forma mide 0,93: eso no es cómo se mide, es que no
        cuadra, y el aviso sale con las dos cifras.
        """
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1, area_sigpac_ha=0.93, area_declarada_ha=4.0)]),
        )
        diferencia = plan["diferencias_de_superficie"][0]
        assert diferencia["aviso"] is True
        assert diferencia["diferencia_ha"] == pytest.approx(3.07, abs=0.01)
        assert diferencia["porcentaje"] > versiones.UMBRAL_DE_DIFERENCIA
        assert "no cuadran" in diferencia["texto"]
        # Y las tres cifras siguen cada una en su sitio: no se ha tocado ninguna para que cuadren.
        assert diferencia["area_declarada_ha"] == 4.0
        assert diferencia["area_sigpac_ha"] == 0.93
        assert diferencia["area_geometria_ha"] == pytest.approx(0.9331, abs=0.002)

    def test_una_diferencia_pequena_no_da_aviso_pero_se_dice(
        self, cliente, cuenta, campana
    ):
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1, area_sigpac_ha=0.933, area_declarada_ha=0.93)]),
        )
        diferencia = plan["diferencias_de_superficie"][0]
        assert diferencia["aviso"] is False
        assert diferencia["diferencia_ha"] is not None
        assert "cuadran" in diferencia["texto"]


# --------------------------------------------------------------------------
# 8. Lo que el lote dice mal, y no se arregla solo
# --------------------------------------------------------------------------


class TestLoQueElLoteNoSePuedeApuntar:
    def test_un_recinto_sin_referencia_ni_forma_no_se_apunta_y_se_dice(
        self, cliente, cuenta, campana, db_sesion
    ):
        """Un renglón vacío no se guarda «por si acaso»: se dice que no se sabe qué es."""
        plan = _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [{}]))
        assert plan["nuevos"] == 0
        assert len(plan["problemas"]) == 1
        assert "no se sabe cuál es" in plan["problemas"][0]
        assert _la_foto_de_lo_guardado(db_sesion) == []

    def test_una_referencia_a_medias_sin_decir_la_tierra_no_se_pega_a_ninguna(
        self, cliente, cuenta, campana, db_sesion
    ):
        """Sin el número de recinto no se sabe de qué tierra es, y no se elige una al azar.

        Es la regla de «nada se inventa» aplicada a una tierra: el programa no da de alta una tierra
        que no sabe identificar, y lo dice con lo que falta.
        """
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(
                campana,
                [{"provincia": "37", "municipio": "70", "poligono": 503, "numero_parcela": 51}],
            ),
        )
        assert plan["nuevos"] == 0
        assert "sin el número de recinto" in plan["problemas"][0]
        assert _la_foto_de_lo_guardado(db_sesion) == []
        assert cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json() == []

    def test_dos_recintos_distintos_para_la_misma_tierra_no_guardan_ninguno(
        self, cliente, cuenta, campana, db_sesion
    ):
        """Una tierra es un recinto: dos referencias distintas para la misma tierra se contradicen.

        **Este contrato cambió el 03/10/2026, y por eso la prueba dice otra cosa.** Antes se importaba
        **la primera** y se avisaba de la segunda. Lo encontró la revisión independiente: con eso, el
        mismo lote **en otro orden** dejaba guardado **otro** recinto, así que la importación dejaba de
        ser repetible y reescribía la versión y la auditoría con un cambio que nadie había pedido.

        Ahora no se guarda **ninguna** de las dos y se dice por qué, renglón a renglón: no se sabe cuál
        de los dos recintos es el bueno, y elegir por el orden en que vengan es elegir a cara o cruz.
        Es el mismo principio que con las tierras ambiguas: **no guardar es recuperable, guardar el que
        no es, no.** Lo que sigue prohibido es lo de antes: guardar la última y callarse, o dar de alta
        una tierra nueva para cada recinto («no duplique una tierra que ya existe con la misma
        referencia»).
        """
        tierra = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={"alias": "Una sola", "superficie_ha": 1.0},
        ).json()
        los_dos = [
            {"parcela_id": tierra["id"], "referencia": REFERENCIA_1, "geometria": CUADRADO_1},
            {"parcela_id": tierra["id"], "referencia": REFERENCIA_2, "geometria": CUADRADO_2_QUE_PISA_AL_1},
        ]
        plan = _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, los_dos))
        assert plan["nuevos"] == 0, "se ha guardado uno de los dos recintos contradictorios"
        assert plan["versiones_creadas"] == 0
        assert len(plan["problemas"]) == 2, "no se ha dicho nada de los dos recintos"
        assert all(
            "dos recintos distintos para la misma tierra" in problema
            for problema in plan["problemas"]
        ), plan["problemas"]
        assert _la_foto_de_lo_guardado(db_sesion) == [], "ha quedado algo guardado"
        assert len(cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()) == 1

        # **Y el orden no cambia el resultado**, que es el defecto que se estaba arreglando: los
        # mismos dos recintos al revés tienen que dejar exactamente lo mismo (nada).
        al_reves = _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, list(reversed(los_dos))))
        assert al_reves["nuevos"] == 0
        assert al_reves["versiones_creadas"] == 0
        assert len(al_reves["problemas"]) == 2
        assert _la_foto_de_lo_guardado(db_sesion) == [], "el orden del lote ha decidido algo"

    def test_el_aviso_de_la_contradiccion_dice_que_no_se_guarda_ninguno(
        self, cliente, cuenta, campana, db_sesion
    ):
        """**El aviso no puede decir lo contrario de lo que ha hecho el programa.**

        Lo encontró la auditoría del 05/10/2026 **leyendo el código de al lado**, no una prueba, porque
        no había ninguna que mirara el texto: el programa decía «**se ha tenido en cuenta el primero**»
        cuando en realidad **no guardaba ninguno**. La frase venía de cuando sí se importaba el primero
        y se avisaba del segundo; el contrato cambió el 03/10/2026 —no se guarda ninguno, porque no se
        sabe cuál de los dos vale— y **el texto se quedó atrás**.

        Y no es cosmética: el agricultor lee ese aviso con el papel delante, y si dice que el primero
        está guardado, mira el primero y da por bueno un recinto que **no se ha apuntado**.
        """
        los_dos = [un_recinto(1), un_recinto(1, geometria=CUADRADO_2_QUE_PISA_AL_1)]
        plan = _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, los_dos))

        assert plan["versiones_creadas"] == 0
        assert plan["nuevos"] == 0
        assert plan["problemas"], "no se ha dicho nada del lote contradictorio"
        # **Se compara en minúsculas a propósito.** La primera versión de esta prueba buscaba
        # «se ha tenido en cuenta el primero» tal cual, y no lo encontraba porque en el aviso va al
        # principio de la frase y empieza por mayúscula: la prueba pasaba **con el defecto puesto**. Se
        # descubrió volviendo a poner el defecto a propósito para ver si la prueba mordía, que es la
        # única forma de saber que una prueba sirve.
        dicho = " ".join(plan["problemas"]).lower()
        assert "no se ha dado de alta ninguno" in dicho, dicho
        assert "se ha tenido en cuenta el primero" not in dicho, (
            "el aviso dice que vale el primero y el programa no ha guardado ninguno: " + dicho
        )
        assert _la_foto_de_lo_guardado(db_sesion) == []

    def test_el_mismo_recinto_dos_veces_y_una_tercera_que_lo_contradice(
        self, cliente, cuenta, campana, db_sesion
    ):
        """Los tres renglones juntos: el aviso de la contradicción **sustituye** al del repetido.

        Es el caso que obligó a mirar **por qué** se saltó cada renglón y no solo si estaba saltado.
        Sin eso, el aviso del renglón repetido («se ha tenido en cuenta el primero») se ponía antes de
        saber que había una contradicción y ya no se quitaba, así que el ensayo decía **las dos cosas**
        de la misma tierra: que vale el primero y que no se ha guardado ninguno.
        """
        los_tres = [
            un_recinto(1),
            un_recinto(1),  # el mismo apunte otra vez: es el reenvío del móvil
            un_recinto(1, geometria=CUADRADO_2_QUE_PISA_AL_1),  # y este dice otra cosa
        ]
        plan = _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, los_tres))

        assert plan["nuevos"] == 0 and plan["versiones_creadas"] == 0
        dicho = " ".join(plan["problemas"]).lower()
        assert "se ha tenido en cuenta el primero" not in dicho, (
            "el ensayo dice que vale el primero y que no se ha guardado ninguno, a la vez: " + dicho
        )
        assert "no se ha dado de alta ninguno" in dicho, dicho
        assert _la_foto_de_lo_guardado(db_sesion) == []

    def test_el_ensayo_no_promete_tierras_que_no_va_a_dar_de_alta(
        self, cliente, cuenta, campana, db_sesion
    ):
        """**Lo que el ensayo promete es lo que pasa al aplicar.**

        El otro hallazgo de la auditoría del 05/10/2026, y del mismo tipo: en un lote contradictorio los
        renglones se marcan como saltados (no se guarda ninguno), pero el recuento `tierras_nuevas`
        **los contaba igual**, así que el ensayo decía «Tierras que se darían de alta: 2» y al aplicar no
        se creaba ninguna. El que mentía era **el ensayo**, que es justo lo que el agricultor lee antes de
        decidir si aplica.

        Se comprueban las dos mitades: el ensayo cuenta **cero**, y al aplicar de verdad tampoco se da de
        alta ninguna.
        """
        los_dos = [un_recinto(1), un_recinto(1, geometria=CUADRADO_2_QUE_PISA_AL_1)]

        ensayo = _previsualizar(cliente, cuenta["cabeceras"], _el_lote(campana, los_dos))
        assert ensayo["tierras_nuevas"] == 0, (
            f"el ensayo promete {ensayo['tierras_nuevas']} tierras nuevas y no se va a crear ninguna"
        )
        assert ensayo["detalle"] == [], "el ensayo enseña renglones que no se van a guardar"

        aplicado = _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, los_dos))
        assert aplicado["tierras_creadas"] == []
        assert aplicado["tierras_nuevas"] == 0
        assert cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json() == []

    def test_una_fuente_que_no_existe_se_rechaza_diciendo_cuales_valen(
        self, cliente, cuenta, campana, db_sesion
    ):
        respuesta = cliente.post(
            "/api/versiones/aplicar",
            headers=cuenta["cabeceras"],
            json=_el_lote(campana, [un_recinto(1)], fuente="lo que me dijo el vecino"),
        )
        assert respuesta.status_code == 400
        assert "no es una de las fuentes que se guardan" in respuesta.json()["detail"]
        assert "SIGPAC" in respuesta.json()["detail"]
        assert _la_foto_de_lo_guardado(db_sesion) == []

    def test_un_lote_sin_ano_se_rechaza(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/versiones/previsualizar",
            headers=cuenta["cabeceras"],
            json={"fuente": "sigpac", "recintos": [un_recinto(1)]},
        )
        assert respuesta.status_code == 400
        assert "de qué año" in respuesta.json()["detail"]

    def test_un_ano_que_no_esta_creado_se_rechaza(self, cliente, cuenta, campana):
        respuesta = cliente.post(
            "/api/versiones/previsualizar",
            headers=cuenta["cabeceras"],
            json={"anio": campana["anio"] + 7, "fuente": "sigpac", "recintos": [un_recinto(1)]},
        )
        assert respuesta.status_code == 404
        assert "no está creado" in respuesta.json()["detail"]

    def test_el_ano_se_puede_decir_por_su_numero(self, cliente, cuenta, campana):
        plan = _previsualizar(
            cliente,
            cuenta["cabeceras"],
            {"anio": campana["anio"], "fuente": "sigpac", "recintos": [un_recinto(1)]},
        )
        assert plan["campana_id"] == campana["id"]
        assert plan["anio"] == campana["anio"]


# --------------------------------------------------------------------------
# 9. Lo que la versión no toca
# --------------------------------------------------------------------------


class TestLaVersionNoTocaLaTierra:
    def test_el_alias_que_puso_el_agricultor_no_se_cambia(
        self, cliente, cuenta, campana
    ):
        """El alias es del agricultor y no viene de ninguna fuente: importar no lo renombra.

        El contrato lo dice así (§2.1): «previsualización de igual/cambiado/desaparecido/nuevo, sin
        modificar notas, alias o historia». Aquí se manda un lote con otro nombre para la misma
        tierra y el nombre que queda es el suyo.
        """
        tierra = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={
                "alias": "El Prado de arriba",
                "ref_sigpac": REFERENCIA_1,
                "poligono": 503,
                "numero_parcela": 51,
                "numero_recinto": 1,
                "superficie_ha": 2.43,
            },
        ).json()
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1, alias="Como diga el SIGPAC")]),
        )
        la_misma = cliente.get(
            f"/api/parcelas/{tierra['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert la_misma["alias"] == "El Prado de arriba"
        # Y el enlace ha sido por la referencia: no se ha creado una tierra de más.
        assert len(cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()) == 1
        assert _las_versiones(cliente, cuenta["cabeceras"])[0]["parcela_id"] == tierra["id"]

    def test_una_tierra_que_ya_existe_no_se_duplica_se_enlaza(
        self, cliente, cuenta, campana
    ):
        """«No duplique una tierra que ya existe con la misma referencia: la enlaza.»

        La tierra existe con la referencia completa del recinto. El lote trae esa misma referencia
        sin decir a qué tierra va: el programa la reconoce y la enlaza, sin dar de alta otra.
        """
        tierra = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={
                "alias": "La de siempre",
                "ref_sigpac": REFERENCIA_2,
                "poligono": 503,
                "numero_parcela": 51,
                "numero_recinto": 2,
                "superficie_ha": 1.0,
            },
        ).json()
        plan = _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(2)]))
        assert plan["tierras_nuevas"] == 0
        assert plan["tierras_creadas"] == []
        assert plan["detalle"][0]["parcela_id"] == tierra["id"]
        assert plan["detalle"][0]["tierra"] == "La de siempre"
        assert len(cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()) == 1

    def test_la_tierra_se_reconoce_por_sus_numeros_aunque_no_tenga_la_referencia_escrita(
        self, cliente, cuenta, campana
    ):
        """La referencia puede estar escrita de otra manera, o no estar: los números la identifican.

        Hay tierras dadas de alta a mano, o traídas del cuaderno de la Junta, **sin la referencia
        completa** pero con su polígono, su parcela y su recinto. Si la búsqueda se quedara solo en el
        texto de la referencia, el lote daría de alta una tierra repetida —justo lo que el contrato
        prohíbe—, así que se buscan también los números, y **con el recinto dentro**: sin él, dos
        tierras de la misma parcela serían indistinguibles y no se elegiría ninguna.
        """
        tierra = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={
                "alias": "Apuntada a mano",
                "poligono": 503,
                "numero_parcela": 51,
                "numero_recinto": 2,
                "superficie_ha": 1.0,
            },
        ).json()
        assert tierra["ref_sigpac"] is None

        plan = _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(2)]))
        assert plan["tierras_nuevas"] == 0
        assert plan["detalle"][0]["parcela_id"] == tierra["id"]
        assert len(cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()) == 1

    def test_el_estado_de_revision_empieza_en_sin_revisar(
        self, cliente, cuenta, campana
    ):
        """Importar no es revisar: nadie lo ha mirado todavía, y eso es lo que se guarda."""
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))
        version = _las_versiones(cliente, cuenta["cabeceras"])[0]
        assert version["estado_revision"] == "sin_revisar"
        assert version["estado_texto"] == "Sin revisar"

        # Y si la fuente dice que ya lo revisó (lo dice el cuaderno de la Junta), se guarda.
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(
                campana,
                [un_recinto(1, estado_revision="con_dudas")],
                fuente="cuaderno_de_la_junta",
            ),
        )
        del_cuaderno = [
            una
            for una in _las_versiones(cliente, cuenta["cabeceras"])
            if una["fuente"] == "cuaderno_de_la_junta"
        ][0]
        assert del_cuaderno["estado_revision"] == "con_dudas"
        assert del_cuaderno["fuente_texto"] == "Cuaderno de la Junta"


# --------------------------------------------------------------------------
# 10. Con lo que devuelve el SIGPAC de verdad
# --------------------------------------------------------------------------


class TestElLoteSeMontaConLoQueDevuelveElSigpac:
    """Dos pruebas que usan **respuestas de verdad del SIGPAC guardadas en `data/sigpac/`**.

    No salen a internet (`AGENTS.md` §3, «los tests no salen a internet»): leen los ficheros que se
    guardaron el día que se escribió el conector. Lo que demuestran es que un lote se puede montar
    con lo que devuelve el conector —los recintos de una parcela y, después, cada recinto con su
    forma, su superficie y su uso— sin traducir nada por medio.
    """

    def test_los_recintos_de_una_parcela_sirven_para_montar_el_lote(self):
        cuerpo = json.loads(
            (RUTA_SIGPAC / "recintos_de_ejemplo.json").read_text(encoding="utf-8")
        )
        recintos = sigpac.lee_recintos(cuerpo)
        assert len(recintos) == 1
        el_del_sigpac = recintos[0]
        assert el_del_sigpac.ref_sigpac == REFERENCIA_1

        # Y la consulta del recinto concreto (la que se hace después, cuando el agricultor ya ha
        # elegido el suyo) trae la forma, la superficie y el uso del **mismo** recinto.
        recinto = sigpac.lee_recinto(
            json.loads((RUTA_SIGPAC / "recinto_de_ejemplo_503_51.json").read_text(encoding="utf-8"))
        )
        assert recinto is not None
        assert recinto.referencia.como_texto() == REFERENCIA_1
        assert recinto.superficie == 4.9016
        assert recinto.wkt

        # Y el área de la forma que manda el SIGPAC cuadra con la superficie que él mismo publica
        # (4,893739 ha medidas frente a 4,9016 declaradas: un 0,16 %).
        assert geo.area_ha(recinto.wkt) == pytest.approx(recinto.superficie, rel=0.005)

    def test_el_recinto_de_verdad_del_sigpac_se_importa_con_sus_dos_superficies(
        self, cliente, cuenta, campana
    ):
        """El recinto oficial, importado como lo mandaría el SIGPAC.

        Entra con **su** superficie (4,9016 ha, la que publica el SIGPAC), con **el área medida de su
        forma** (4,893739 ha, que es otra cosa y se guarda aparte) y con su uso. Y las hectáreas
        declaradas se quedan en blanco: el SIGPAC no las dice, y nadie las puede inventar.
        """
        recinto = sigpac.lee_recinto(
            json.loads((RUTA_SIGPAC / "recinto_de_ejemplo_503_51.json").read_text(encoding="utf-8"))
        )
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(
                campana,
                [
                    {
                        "provincia": str(recinto.provincia),
                        "municipio": str(recinto.municipio),
                        "agregado": recinto.agregado,
                        "zona": recinto.zona,
                        "poligono": recinto.poligono,
                        "numero_parcela": recinto.parcela,
                        "numero_recinto": recinto.recinto,
                        "geometria": recinto.wkt,
                        "area_sigpac_ha": recinto.superficie,
                        "uso_sigpac": recinto.uso_sigpac,
                    }
                ],
            ),
        )
        assert plan["nuevos"] == 1

        version = _las_versiones(cliente, cuenta["cabeceras"])[0]
        assert version["referencia"] == REFERENCIA_1
        assert version["poligono_valido"] is True
        assert version["area_sigpac_ha"] == 4.9016
        assert version["area_geometria_ha"] == pytest.approx(4.893739, abs=1e-5)
        assert version["area_declarada_ha"] is None
        assert version["uso_sigpac"] == "TA"
        assert version["anio"] == campana["anio"]

        # La diferencia entre las dos superficies que se conocen es la del método de medida (0,16 %),
        # por debajo del umbral de aviso: está medido en `tests/test_geo.py`.
        diferencia = plan["diferencias_de_superficie"][0]
        assert diferencia["aviso"] is False
        assert diferencia["porcentaje"] == pytest.approx(0.0016, abs=0.0005)

    def test_el_pueblo_de_la_tierra_se_saca_del_listado_oficial(
        self, cliente, cuenta, campana
    ):
        """Provincia y municipio del SIGPAC son los códigos del INE, y con el listado se saben.

        Es la misma cuenta que hace el alta desde el SIGPAC (`routers/parcelas.py`): el recinto trae
        `37` y `070`, y el listado oficial dice a qué pueblo corresponde. **Si no lo encontrara, se
        quedaría en blanco**, que es la otra mitad de la regla: el nombre no se deduce del número.
        """
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))
        tierra = _la_tierra_de(cliente, cuenta["cabeceras"], 1)

        # El nombre se compara con el que dice el listado oficial que usa el programa, no con uno
        # escrito aquí a mano: si el INE cambia el nombre de un pueblo, esta prueba no se pone roja
        # por eso, y si alguien cambia la forma de buscar el pueblo, sí.
        del_listado = catalogos.municipio_por_codigo_ine("37070")
        assert del_listado is not None
        assert tierra["provincia"] == del_listado.provincia
        assert tierra["municipio"] == del_listado.nombre
        assert tierra["codigo_ine"] == "37070"

    def test_una_referencia_que_no_se_entiende_y_sin_tierra_no_se_apunta(
        self, cliente, cuenta, campana, db_sesion
    ):
        """Si el texto de la referencia no se entiende y no se dice a qué tierra va, no se adivina.

        El recinto trae una forma, sí, pero **no hay forma de saber de qué tierra es**: no se le
        puede pegar a una al azar ni dar de alta una tierra sin referencia —eso sería inventarse una
        tierra y, además, duplicarla la próxima vez—. Se dice lo que falta, que es lo que permite
        arreglarlo.
        """
        plan = _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [{"referencia": "no me acuerdo", "geometria": CUADRADO_1}]),
        )
        assert plan["nuevos"] == 0
        assert len(plan["problemas"]) == 1
        assert "sin el número de recinto" in plan["problemas"][0]
        assert _la_foto_de_lo_guardado(db_sesion) == []
        assert cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json() == []

    def test_sin_referencia_pero_diciendo_la_tierra_si_se_apunta(
        self, cliente, cuenta, campana
    ):
        """Y cuando el lote **sí** dice a qué tierra va, la forma sola basta: se guarda sin referencia.

        Es el caso de una medición en el campo: el agricultor dibuja el trozo y elige la tierra. La
        versión entra con su área calculada y con `poligono_valido` en falso, que es la verdad.
        """
        tierra = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={"alias": "Medida a mano", "superficie_ha": None},
        ).json()
        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(
                campana,
                [{"parcela_id": tierra["id"], "geometria": CUADRADO_1}],
                fuente="medicion_en_campo",
            ),
        )
        version = _las_versiones(cliente, cuenta["cabeceras"], parcela_id=tierra["id"])[0]
        assert version["fuente_texto"] == "Medido en el campo"
        assert version["referencia"] is None
        assert version["poligono_valido"] is False
        assert version["area_geometria_ha"] == pytest.approx(0.9331, abs=0.002)


class TestUnaReferenciaQueTienenVariasTierras:
    """Cuando la referencia **completa** la comparten varias tierras: no se elige ninguna.

    **Es el caso de este agricultor, no un caso raro.** Su cuaderno parte un mismo recinto del SIGPAC
    en varias líneas de cultivo, así que de sus 65 tierras solo 52 referencias son distintas: hay una
    (`37-70-0-0-507-24-1`) que comparten **nueve** tierras y otra que comparten seis.

    Aquí estaba el fallo que estas pruebas protegen: se buscaba por la referencia completa con
    `db.scalar(...)`, que devuelve **la primera** que coincida, y se decía que había **una** candidata.
    Resultado: la versión del recinto se le colgaba a una de las nueve tierras —la que saliera antes de
    la base— **sin decir nada**, y las otras ocho se quedaban sin ella en silencio. El agricultor
    habría visto la historia de un recinto colgada de la tierra que no es, y eso no se nota hasta que
    hay un problema con un lote y alguien pregunta dónde se fue.

    El mismo principio que ya se aplicaba a las referencias a medias: **no enlazar es recuperable;
    enlazar mal, no.**
    """

    def _una_tierra_con_la_referencia(self, cliente, cuenta, alias: str, referencia: str) -> dict:
        return cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={
                "alias": alias,
                "ref_sigpac": referencia,
                "poligono": 503,
                "numero_parcela": 51,
                "numero_recinto": 1,
                "superficie_ha": 1.0,
            },
        ).json()

    def test_con_una_sola_tierra_esa_referencia_se_enlaza(self, cliente, cuenta, campana):
        """El control: sin esto, la prueba de abajo pasaría aunque el enlace estuviera roto del todo."""
        tierra = self._una_tierra_con_la_referencia(cliente, cuenta, "La única", REFERENCIA_1)
        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))

        versiones = _las_versiones(cliente, cuenta["cabeceras"])
        assert len(versiones) == 1, "con una sola tierra que tenga esa referencia, se enlaza"
        assert versiones[0]["parcela_id"] == tierra["id"]

    def test_con_dos_tierras_no_se_le_cuelga_a_ninguna(self, cliente, cuenta, campana):
        """La referencia la tienen dos tierras: la versión no puede irse a una de las dos por suerte."""
        primera = self._una_tierra_con_la_referencia(cliente, cuenta, "TRIGO", REFERENCIA_1)
        segunda = self._una_tierra_con_la_referencia(cliente, cuenta, "BARBECHO", REFERENCIA_1)

        plan = _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))

        assert plan["problemas"], (
            "no ha dicho nada de que la referencia la tengan dos tierras: el agricultor no se entera"
        )
        assert _las_versiones(cliente, cuenta["cabeceras"]) == [], (
            "la versión se ha colgado de una de las dos tierras sin saber cuál era la buena"
        )
        for tierra in (primera, segunda):
            suyas = _las_versiones(cliente, cuenta["cabeceras"], parcela_id=tierra["id"])
            assert suyas == [], f"la tierra {tierra['alias']} no debería tener ninguna versión"

    def test_no_da_de_alta_una_tierra_nueva_para_la_referencia_compartida(
        self, cliente, cuenta, campana
    ):
        """Y no se resuelve el problema inventándose otra tierra: eso duplicaría lo que ya existe."""
        self._una_tierra_con_la_referencia(cliente, cuenta, "TRIGO", REFERENCIA_1)
        self._una_tierra_con_la_referencia(cliente, cuenta, "BARBECHO", REFERENCIA_1)
        antes = len(cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json())

        plan = _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))

        despues = len(cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json())
        assert despues == antes, "se ha dado de alta una tierra de más para el mismo recinto"
        assert plan["tierras_creadas"] == []

    def test_diciendo_a_que_tierra_va_si_se_puede_importar(self, cliente, cuenta, campana):
        """La salida que tiene el agricultor: decir cuál es. Entonces sí entra, y solo en esa."""
        primera = self._una_tierra_con_la_referencia(cliente, cuenta, "TRIGO", REFERENCIA_1)
        segunda = self._una_tierra_con_la_referencia(cliente, cuenta, "BARBECHO", REFERENCIA_1)

        _aplicar(
            cliente,
            cuenta["cabeceras"],
            _el_lote(campana, [un_recinto(1, parcela_id=segunda["id"])]),
        )

        las_de_la_segunda = _las_versiones(cliente, cuenta["cabeceras"], parcela_id=segunda["id"])
        assert len(las_de_la_segunda) == 1, "diciendo a qué tierra va, la versión entra"
        assert _las_versiones(cliente, cuenta["cabeceras"], parcela_id=primera["id"]) == [], (
            "y no se le cuelga también a la otra"
        )

    def test_la_ambiguedad_no_deja_rastro_en_la_base(self, cliente, cuenta, campana, db_sesion):
        """Saltarse el recinto no puede escribir nada a medias: ni versión, ni auditoría de más."""
        self._una_tierra_con_la_referencia(cliente, cuenta, "TRIGO", REFERENCIA_1)
        self._una_tierra_con_la_referencia(cliente, cuenta, "BARBECHO", REFERENCIA_1)
        antes = _la_foto_de_lo_guardado(db_sesion)

        _aplicar(cliente, cuenta["cabeceras"], _el_lote(campana, [un_recinto(1)]))

        assert _la_foto_de_lo_guardado(db_sesion) == antes, (
            "un recinto que no se puede enlazar ha dejado algo escrito"
        )
