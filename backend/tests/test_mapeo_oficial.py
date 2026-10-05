"""El mapeo al formato oficial: que no sea una lista de buenas intenciones.

Lo que se prueba:

1. **Que cada campo oficial que se dice mapear existe de verdad en el esquema**, en esa ruta,
   con ese nombre y con un tipo compatible. Si alguien escribe mal un nombre, salta.
2. **Que los obligatorios son exactamente los que el esquema declara obligatorios.** Ni uno de
   más ni uno de menos: una lista de obligatorios mal hecha es peor que no tenerla.
3. **Que ningún catálogo es inventado**: todos tienen que estar entre los que nombra el
   descriptor oficial.
4. **Que la fecha que producimos la acepta el patrón oficial**, y que la ISO **no** lo cumple.
   Esto último es un hallazgo, no una opinión: se comprueba contra el patrón del esquema.
5. **Que si tuviéramos los códigos, lo que armamos validaría**, y que sin ellos no valida. Es
   la forma de enseñar que el bloqueo son los códigos y no la estructura.
"""

from __future__ import annotations

import datetime as dt
import json
import re

import pytest

from app import catalogos_siex, iuws, iuws_cliente, iuws_descriptor, iuws_mapeo, models

TRATAMIENTO = "ActividadesExplotacion.TratamFito"


def esquema() -> dict:
    return json.loads(iuws.RUTA_ESQUEMA_OFICIAL.read_text(encoding="utf-8"))


def nodo_de_un_bloque(bloque: str) -> dict:
    """El objeto oficial del bloque, sea de explotación o de actividades."""
    raiz = esquema()["properties"]["CUADERNO"]["items"]["properties"]
    for seccion in ("DatosExplotacion", "ActividadesExplotacion"):
        bloques = raiz[seccion]["properties"]
        if bloque in bloques:
            return bloques[bloque]["items"]
    raise KeyError(bloque)


def nodo_del_tratamiento() -> dict:
    return nodo_de_un_bloque("TratamFito")


class TestCadaCampoExisteEnElEsquema:
    """Las mismas garantías para **todos** los bloques mapeados a mano, no solo para uno.

    Si un bloque nuevo se mapea y alguien escribe mal un nombre de campo, esto lo dice con el
    nombre del bloque delante.
    """

    @pytest.mark.parametrize("bloque", iuws_mapeo.bloques_mapeados())
    def test_todos_los_campos_declarados_estan_en_el_esquema(self, bloque):
        """Con las diferencias del descriptor declaradas en el módulo.

        Se dejan escritas, con su motivo, para no perder el hallazgo ni ocultarlo en un test.
        """
        propiedades = nodo_de_un_bloque(bloque)["properties"]
        for campo in iuws_mapeo.correspondencia_de_un_bloque(bloque):
            if iuws_mapeo.campo_que_el_esquema_no_tiene(bloque, campo.ruta):
                continue
            assert campo.ruta in propiedades, f"{bloque}.{campo.ruta} no está en el esquema"

    @pytest.mark.parametrize("bloque", iuws_mapeo.bloques_mapeados())
    def test_las_excepciones_son_las_declaradas_y_ninguna_mas(self, bloque):
        """Si aparece otra diferencia entre los dos documentos, esto la saca a la luz.

        Es la comprobación que convierte «hay una excepción» en «hay **esta** excepción».
        """
        propiedades = set(nodo_de_un_bloque(bloque)["properties"])
        de_fuera = {
            campo.ruta
            for campo in iuws_mapeo.correspondencia_de_un_bloque(bloque)
            if campo.ruta not in propiedades
        }
        assert de_fuera == set(iuws_mapeo.CAMPOS_QUE_EL_ESQUEMA_NO_TIENE.get(bloque, ()))

    @pytest.mark.parametrize("bloque", iuws_mapeo.bloques_mapeados())
    def test_el_tipo_de_cada_campo_es_compatible_con_el_del_esquema(self, bloque):
        """Ni texto donde va un número, ni número donde va un objeto.

        Hay un campo al que el esquema **no le pone tipo**: `SiembraPlantacion.FechaAdquisicion`
        solo tiene el patrón de fecha. Cuando pasa eso se comprueba que al menos tenga el patrón, y
        se dice: saltárselo en silencio sería tapar el caso en vez de entenderlo.
        """
        propiedades = nodo_de_un_bloque(bloque)["properties"]
        for campo in iuws_mapeo.correspondencia_de_un_bloque(bloque):
            if iuws_mapeo.campo_que_el_esquema_no_tiene(bloque, campo.ruta):
                continue
            definicion = propiedades[campo.ruta]
            del_esquema = definicion.get("type")
            if del_esquema is None:
                assert "pattern" in definicion, (
                    f"{bloque}.{campo.ruta}: el esquema no le pone tipo ni patrón"
                )
                continue
            assert del_esquema in iuws_mapeo.TIPOS_COMPATIBLES[campo.tipo], (
                f"{bloque}.{campo.ruta}: decimos {campo.tipo} y el esquema dice {del_esquema}"
            )

    @pytest.mark.parametrize("bloque", iuws_mapeo.bloques_mapeados())
    def test_los_obligatorios_son_exactamente_los_del_esquema(self, bloque):
        """La lista de obligatorios se coteja entera: ni uno de más ni uno de menos."""
        del_esquema = set(nodo_de_un_bloque(bloque)["required"])
        nuestros = {
            c.ruta for c in iuws_mapeo.correspondencia_de_un_bloque(bloque) if c.obligatorio
        }
        assert nuestros == del_esquema, f"{bloque}: los obligatorios no cuadran"

    @pytest.mark.parametrize("bloque", iuws_mapeo.bloques_mapeados())
    def test_los_nombres_oficiales_son_los_del_esquema_con_su_mayuscula(self, bloque):
        """`IdAjenaTratamFito`, no `IdAjenaTratamFITO` ni `idAjenaTratamFito`."""
        propiedades = set(nodo_de_un_bloque(bloque)["properties"])
        for campo in iuws_mapeo.correspondencia_de_un_bloque(bloque):
            if iuws_mapeo.campo_que_el_esquema_no_tiene(bloque, campo.ruta):
                continue
            assert campo.oficial in propiedades
            assert campo.oficial == campo.ruta


class TestElRiegoYLaSiembra:
    """Los dos bloques de `Labor` mapeados a mano, y lo que dicen de dónde está el trabajo."""

    def test_la_siembra_no_necesita_ningun_catalogo(self):
        """Es el bloque más cerca de poder mandarse: lo único que le falta es el código de la
        parcela.

        Es un dato que cambia la conversación: a la siembra no hay que pedirle nada a FEGA salvo
        la respuesta sobre las parcelas.
        """
        resumen = iuws_mapeo.resumen_de_un_bloque("SiembraPlantacion")
        assert resumen["catalogos"] == []
        assert resumen["obligatorios"] == 9
        assert resumen["obligatorios_que_se_pueden"] == [
            "IdAjenaSiembraPlant",
            "SiembraPlantacion",
            "FechaInicio",
            "FechaFin",
            "MaterialTratado",
            "MaterialAdquirido",
            "FechaAdquisicion",
            "Cantidad",
        ]
        # La maquinaria ya no está aquí: desde la ronda 4 la siembra (que es una labor) dice
        # con qué máquina se hizo, así que pasó de «no lo tenemos» a «a medias». Lo que sigue
        # faltando es el resto de los datos de la máquina y, sobre todo, el código de la DGC.
        assert resumen["no_lo_tenemos"] == ["DGCs"]
        assert "Maquinaria" in resumen["a_medias"]

    def test_la_convencion_de_siembra_o_plantacion_esta_escrita_en_el_descriptor(self):
        """No se ha supuesto: el descriptor dice «1 Siembra 0 Plantación», con esas palabras.

        Por eso este campo se da por bueno y los demás códigos no: la diferencia es que este está
        escrito en el documento oficial y los otros hay que pedirlos.
        """
        campos = {
            c.campo: c for c in iuws_descriptor.campos_del_bloque("SiembraPlantacion")
        }
        descripcion = campos["SiembraPlantacion"].descripcion
        assert "1 Siembra" in descripcion and "0 Plantación" in descripcion
        assert campos["SiembraPlantacion"].catalogo is None, "no es un catálogo"

    def test_el_riego_solo_necesita_dos_catalogos_y_el_de_la_parcela(self):
        resumen = iuws_mapeo.resumen_de_un_bloque("Riego")
        assert resumen["obligatorios"] == 7
        assert resumen["catalogos"] == ["Sistema de Riego", "Unidades de Medida", "Origen del agua de riego"]
        # Los dos obligatorios que necesitan código, y las tablas que ya se conocen.
        assert resumen["catalogos_con_tabla"] == {
            "Sistema de Riego": "SIST_RIEGO",
            "Unidades de Medida": "UNIDADES_MEDIDA",
        }
        assert resumen["catalogos_sin_tabla_localizada"] == ["Origen del agua de riego"]
        assert resumen["obligatorios_que_se_pueden"] == [
            "IdAjenaRiego",
            "FechaInicio",
            "FechaFin",
            "Cantidad",
        ]

    def test_el_numero_de_contador_del_agua_ya_se_recoge(self):
        """Es opcional para el interfaz y el cuaderno ya lo guarda: no hay nada que hacer."""
        campos = {c.oficial: c for c in iuws_mapeo.correspondencia_de_un_bloque("Riego")}
        assert campos["NumContador"].estado == iuws_mapeo.SE_PUEDE
        assert campos["NumContador"].de == "numero_contador"

    def test_los_bloques_mapeados_estan_entre_los_del_cuaderno(self):
        """No se puede mapear un bloque que no exista en el esquema."""
        del_mapa = {fila["bloque"] for fila in iuws_mapeo.mapa_del_cuaderno()}
        assert set(iuws_mapeo.bloques_mapeados()) <= del_mapa

    def test_el_total_cuadra_y_dice_cuantos_quedan_por_mapear(self):
        resumen = iuws_mapeo.resumen_de_los_bloques_mapeados()
        assert resumen["bloques_mapeados"] == [
            "MedidaPreventivaCultural",
            "TratamFito",
            "Riego",
            "SiembraPlantacion",
            "Cosecha",
            "Pastoreo",
            "DatosCubierta",
            "LaboresCulturales",
            "Analitica",
            "ComercializacionVD",
            "UsoSemillaTratada",
            "PlanAbonado",
            "AltaDGC",
            "CambioCultivoDGC",
            "EnergiaUtilizada",
            "TratamientosPostCosecha",
            "TratamientosEdifInstalaciones",
            "Fertilizacion",
        ]
        assert resumen["obligatorios"] == sum(
            b["obligatorios"] for b in resumen["detalle"].values()
        )
        assert resumen["obligatorios_que_se_pueden"] == sum(
            len(b["obligatorios_que_se_pueden"]) for b in resumen["detalle"].values()
        )
        # Los que faltan siguen saliendo por su nombre.
        assert resumen["bloques_sin_mapear"] == []
        assert "Riego" not in resumen["bloques_sin_mapear"]
        assert "Fertilizacion" in resumen["bloques_mapeados"]


class TestLosTresBloquesNuevos:
    @pytest.mark.parametrize(
        ("bloque", "modelo"),
        [
            ("MedidaPreventivaCultural", models.MedidaPreventivaDeclarada),
            ("Analitica", models.Analitica),
            ("ComercializacionVD", models.VentaDeCosecha),
            ("UsoSemillaTratada", models.Labor),
            ("PlanAbonado", models.PlanAbonado),
            ("AltaDGC", models.Parcela),
            ("CambioCultivoDGC", models.ParcelaCultivo),
            ("TratamientosPostCosecha", models.TratamientoFitosanitario),
            ("TratamientosEdifInstalaciones", models.TratamientoFitosanitario),
            ("Fertilizacion", models.RegistroFertilizacion),
        ],
    )
    def test_las_fuentes_que_se_declaran_existen_en_el_cuaderno(self, bloque, modelo):
        """Ninguna fuente se inventa: o es una columna de verdad, o está declarada como calculada.

        Los campos calculados (el cultivo precedente, por ejemplo) no son columnas y no pueden
        serlo: se deducen de otros datos. Están declarados uno a uno en
        `iuws_mapeo.CAMPOS_CALCULADOS` **a propósito**, para que añadir uno sea una decisión
        escrita y no un nombre que no existe en ninguna parte.
        """
        columnas = set(modelo.__table__.columns.keys())
        for campo in iuws_mapeo.correspondencia_de_un_bloque(bloque):
            if campo.de:
                assert (
                    campo.de in columnas or campo.de in iuws_mapeo.CAMPOS_CALCULADOS
                ), f"{bloque}.{campo.oficial}: falta {campo.de}"

    def test_los_catalogos_pendientes_salen_del_descriptor(self):
        oficiales = {nombre for nombre, _ in iuws_descriptor.catalogos_que_pide()}
        for bloque in (
            "MedidaPreventivaCultural", "Analitica", "ComercializacionVD",
            "UsoSemillaTratada", "PlanAbonado",
            "AltaDGC", "CambioCultivoDGC", "EnergiaUtilizada",
            "TratamientosPostCosecha", "TratamientosEdifInstalaciones", "Fertilizacion",
        ):
            for campo in iuws_mapeo.correspondencia_de_un_bloque(bloque):
                if campo.catalogo:
                    assert campo.catalogo in oficiales

    def test_los_campos_disponibles_y_pendientes_no_se_confunden(self):
        resumen = iuws_mapeo.resumen_de_los_bloques_mapeados()
        assert len(resumen["bloques_mapeados"]) == 18
        assert resumen["bloques_sin_mapear"] == []
        assert resumen["obligatorios"] == 113
        # 61 desde la ronda 6: la herramienta del plan de abono se pregunta con un sí o un no,
        # igual que la pide el anexo, así que mapea directo sin ningún catálogo (en la ronda 5
        # eran 60, al preguntarse la fecha del tratamiento de la semilla). El número sube cuando el
        # cuaderno recoge un dato más, y eso es lo que se quiere que pase.
        assert resumen["obligatorios_que_se_pueden"] == 61
        assert iuws_mapeo.resumen_de_un_bloque("MedidaPreventivaCultural")[
            "obligatorios_que_se_pueden"
        ] == []

    def test_el_plan_no_copia_fosforo_y_potasio_a_sus_oxidos(self):
        campos = {c.oficial: c for c in iuws_mapeo.correspondencia_de_un_bloque("PlanAbonado")}
        assert campos["NecesidadUFP2O5"].estado == iuws_mapeo.A_MEDIAS
        assert campos["NecesidadUFK2O"].estado == iuws_mapeo.A_MEDIAS
        assert campos["NecesidadUFN"].estado == iuws_mapeo.SE_PUEDE


class TestNingunCatalogoEsInventado:
    def test_todos_los_catalogos_que_se_citan_los_nombra_el_descriptor(self):
        """El descriptor es el que manda: si un catálogo no está ahí, no se cita.

        Esto es lo que impide el atajo de «pongo el nombre que me suena».
        """
        del_descriptor = {nombre for nombre, _ in iuws_descriptor.catalogos_que_pide()}
        for campo in iuws_mapeo.correspondencia_del_tratamiento():
            if campo.catalogo:
                assert campo.catalogo in del_descriptor, (
                    f"{campo.catalogo} no lo nombra el descriptor oficial"
                )

    def test_el_resumen_lo_dice_y_no_se_deja_ninguno_sin_confirmar(self):
        resumen = iuws_mapeo.resumen_del_tratamiento()
        assert resumen["catalogos"], "el bloque de tratamientos necesita catálogos"
        assert resumen["catalogos"] == resumen["catalogos_confirmados_por_el_descriptor"]

    def test_dice_cuales_de_sus_catalogos_ya_tienen_tabla_y_cuales_hay_que_preguntar(self):
        """«Faltan los catálogos» no es un recado; esto sí.

        De los cuatro que necesita este bloque, dos ya tienen tabla localizada en SIEX por
        coincidir el nombre exactamente, y dos no: esos son los que hay que preguntar.
        """
        resumen = iuws_mapeo.resumen_del_tratamiento()
        assert resumen["catalogos_con_tabla"]["Eficacia del tratamiento"] == "EFICACIA_TRATAMIENTO"
        assert resumen["catalogos_con_tabla"]["Justificación de la Actuación"] == (
            "JUSTIFICACION_ACTUACION"
        )
        assert "Plagas" in resumen["catalogos_sin_tabla_localizada"]
        assert "tipos de producto" in resumen["catalogos_sin_tabla_localizada"]
        assert set(resumen["catalogos_con_tabla"]) | set(
            resumen["catalogos_sin_tabla_localizada"]
        ) == set(resumen["catalogos"])


def todos_los_campos_mapeados():
    """Todos los campos de todos los bloques mapeados a mano, con su bloque delante.

    Las reglas de los estados no se aplican a un bloque: se aplican a todos. Si no, un bloque
    nuevo podría saltárselas sin que nadie se enterara.
    """
    for bloque in iuws_mapeo.bloques_mapeados():
        for campo in iuws_mapeo.correspondencia_de_un_bloque(bloque):
            yield bloque, campo


class TestLosEstadosDicenLaVerdad:
    def test_los_estados_son_los_cuatro_que_hay(self):
        for _bloque, campo in todos_los_campos_mapeados():
            assert campo.estado in iuws_mapeo.ESTADOS

    def test_lo_que_se_puede_no_necesita_catalogo_ni_le_falta_el_dato(self):
        for bloque, campo in todos_los_campos_mapeados():
            if campo.estado == iuws_mapeo.SE_PUEDE:
                assert campo.de is not None, f"{bloque}.{campo.oficial}: ¿de dónde sale?"
                assert campo.catalogo is None

    def test_lo_que_necesita_catalogo_dice_cual(self):
        """Con una excepción, y declarada: `LaboresCulturales.TipoLabor`.

        El descriptor no cita ningún catálogo para ese campo, así que no se puede ni saber de
        dónde salen los códigos. Se queda sin nombre de catálogo y con la nota explicando qué hay
        que preguntar, y aquí se exige que la excepción sea **la declarada**, no cualquiera.
        """
        for bloque, campo in todos_los_campos_mapeados():
            if campo.estado != iuws_mapeo.HACE_FALTA_CATALOGO:
                continue
            if iuws_mapeo.campo_sin_catalogo_citado(bloque, campo.oficial):
                assert campo.catalogo is None
                assert campo.nota.strip(), "y se explica qué falta"
                continue
            assert campo.catalogo, f"{bloque}.{campo.oficial}: falta el catálogo y no se dice cuál"

    def test_lo_que_nos_falta_a_nosotros_se_explica(self):
        """`a_medias` y `no_lo_tenemos` dependen de nosotros, así que hay que decir qué falta.

        Sin la explicación, un estado así no vale para nada: nadie sabe qué pantalla escribir.
        """
        for bloque, campo in todos_los_campos_mapeados():
            if campo.estado in (iuws_mapeo.A_MEDIAS, iuws_mapeo.NO_LO_TENEMOS):
                assert campo.nota.strip(), f"{bloque}.{campo.oficial}: falta la explicación"

    def test_el_resumen_cuadra(self):
        """Los cuatro grupos tienen que sumar los campos: ni uno perdido ni contado dos veces."""
        resumen = iuws_mapeo.resumen_del_tratamiento()
        suma = (
            len(resumen["se_pueden"])
            + len(resumen["hacen_falta_catalogos"])
            + len(resumen["a_medias"])
            + len(resumen["no_lo_tenemos"])
        )
        assert suma == resumen["campos"]
        assert resumen["obligatorios"] == len(nodo_del_tratamiento()["required"])

    def test_los_que_dependen_de_fega_son_los_de_los_catalogos(self):
        """La distinción que da sentido al módulo: FEGA no es lo mismo que una pantalla nuestra."""
        resumen = iuws_mapeo.resumen_del_tratamiento()
        assert "ProblematicaFito" in resumen["hacen_falta_catalogos"]
        assert "Justificaciones" in resumen["hacen_falta_catalogos"]
        # `Eficacia` empezó en «no lo tenemos» y pasó aquí el día que el cuaderno empezó a
        # preguntarla: el dato ya se recoge, lo que falta es el código. Es exactamente el
        # movimiento que busca este módulo, y por eso se fija en un test.
        assert "Eficacia" in resumen["hacen_falta_catalogos"]
        assert "Eficacia" not in resumen["no_lo_tenemos"]

    def test_lo_que_depende_de_nosotros_esta_dicho(self):
        """`DGCs` sigue siendo lo único que no recogemos, y se dice por qué."""
        resumen = iuws_mapeo.resumen_del_tratamiento()
        assert resumen["no_lo_tenemos"] == ["DGCs"]

    def test_el_aplicador_ya_se_puede_armar(self):
        """`AplicacionManual` se pregunta desde que se mapeó: eso desbloquea un campo obligatorio.

        Si esto vuelve a «a medias», es que se ha dejado de preguntar en alguna pantalla.
        """
        campos = {c.oficial: c for c in iuws_mapeo.correspondencia_del_tratamiento()}
        assert campos["IdentificadorAplicador"].estado == iuws_mapeo.SE_PUEDE
        assert campos["IdentificadorAplicador"].de == "aplicador_id"


class TestElMapaDelCuadernoEntero:
    """El mapa de los 18 bloques se saca de los dos documentos oficiales, no a mano."""

    def test_estan_los_dieciocho_bloques(self):
        """3 de datos de la explotación y 15 de actividades: los que tiene el esquema."""
        mapa = iuws_mapeo.mapa_del_cuaderno()
        assert len(mapa) == 18
        assert sum(1 for f in mapa if f["seccion"] == "DatosExplotacion") == 3
        assert sum(1 for f in mapa if f["seccion"] == "ActividadesExplotacion") == 15

    def test_ningun_bloque_se_queda_sin_su_bloque_del_descriptor(self):
        """El fallo de las llaves que faltan hacía aparecer bloques «sin descriptor».

        Esto es la misma comprobación que la de la tabla, pero vista desde el mapa: si algún día
        vuelve a pasar, el mapa lo dice en vez de callarse.
        """
        resumen = iuws_mapeo.resumen_del_cuaderno()
        assert resumen["bloques_sin_descriptor"] == []
        for fila in iuws_mapeo.mapa_del_cuaderno():
            assert fila["bloque_en_el_descriptor"], fila["bloque"]

    def test_los_obligatorios_de_cada_bloque_son_los_del_esquema(self):
        """Ni uno de más ni uno de menos: la lista sale del esquema, no de una copia."""
        raiz = iuws_mapeo.esquema()["properties"]["CUADERNO"]["items"]["properties"]
        for seccion, bloque, obligatorios in iuws_mapeo.bloques_del_cuaderno():
            del_esquema = set(raiz[seccion]["properties"][bloque]["items"]["required"])
            fila = next(
                f for f in iuws_mapeo.mapa_del_cuaderno() if f["bloque"] == bloque
            )
            assert {c["campo"] for c in fila["campos"]} == del_esquema

    def test_ningun_catalogo_del_mapa_es_inventado(self):
        """Todos tienen que estar entre los que el descriptor nombra. Sin excepciones."""
        del_descriptor = {nombre for nombre, _ in iuws_descriptor.catalogos_que_pide()}
        for fila in iuws_mapeo.mapa_del_cuaderno():
            for campo in fila["campos"]:
                for catalogo in campo["catalogos"]:
                    assert catalogo in del_descriptor, (fila["bloque"], campo["campo"], catalogo)

    def test_un_contenedor_trae_los_catalogos_de_dentro(self):
        """`ProblematicaFito` no necesita un catálogo: necesita los cuatro de sus listas.

        Si el mapa solo mirara el campo, diría que no hace falta ninguno y la lista de la compra
        saldría incompleta justo en lo que más bloquea.
        """
        fila = next(f for f in iuws_mapeo.mapa_del_cuaderno() if f["bloque"] == "TratamFito")
        campos = {c["campo"]: c for c in fila["campos"]}
        problematica = campos["ProblematicaFito"]
        assert problematica["contenedor"] is True
        assert set(problematica["catalogos"]) == {
            "Plagas",
            "Enfermedades",
            "Malas Hierbas",
            "Reguladores del crecimiento y otros",
        }
        assert campos["Eficacia"]["catalogos"] == ["Eficacia del tratamiento"]
        assert campos["Justificaciones"]["catalogos"] == ["Justificación de la Actuación"]

    def test_un_campo_sin_catalogo_en_su_bloque_dice_donde_se_cita(self):
        """`Riego.SistemaRiego` no dice de qué catálogo sale, y en otro bloque sí.

        Se apunta como **información**, no como conclusión: que sea el mismo catálogo es lo más
        probable y no se puede afirmar. Con esto se puede ir a preguntar.
        """
        fila = next(f for f in iuws_mapeo.mapa_del_cuaderno() if f["bloque"] == "Riego")
        campos = {c["campo"]: c for c in fila["campos"]}
        assert campos["SistemaRiego"]["catalogos"] == []
        assert campos["SistemaRiego"]["catalogo_en_otro_bloque"] == "Sistema de Riego"

    def test_casi_todos_los_bloques_obligan_a_decir_en_que_parcela(self):
        """Y eso es lo que el cuaderno todavía no sabe traducir a código de DGC.

        Es el bloqueo que alcanza a más sitios a la vez, así que se cuenta y se dice.
        """
        resumen = iuws_mapeo.resumen_del_cuaderno()
        assert resumen["bloques_que_necesitan_las_parcelas"] == 9

    def test_el_resumen_cuadra_y_dice_cuantos_catalogos_hacen_falta(self):
        resumen = iuws_mapeo.resumen_del_cuaderno()
        assert resumen["bloques"] == len(resumen["mapa"])
        assert resumen["obligatorios"] == sum(f["obligatorios"] for f in resumen["mapa"])
        assert resumen["catalogos"], "sin catálogos, el mapa no dice nada útil"
        assert len(resumen["catalogos_con_tabla"]) + len(resumen["catalogos_sin_tabla"]) == len(
            resumen["catalogos"]
        )
        suma = sum(c["campos"] for c in resumen["catalogos"])
        cuenta = sum(
            len(campo["catalogos"]) for fila in resumen["mapa"] for campo in fila["campos"]
        )
        assert suma == cuenta

    def test_los_que_ya_tienen_tabla_son_los_que_se_cruzaron(self):
        """La tabla de SIEX de cada catálogo sale del cruce exacto, no de una lista aparte."""
        resumen = iuws_mapeo.resumen_del_cuaderno()
        for catalogo in resumen["catalogos"]:
            tabla = catalogos_siex.catalogo_de_siex(catalogo["nombre"])
            assert catalogo["tabla_de_siex"] == (tabla["id"] if tabla else None)


class TestDeQueTablaNuestraSaleCadaBloque:
    """De qué dato nuestro sale cada bloque oficial, y dónde están los agujeros."""

    def test_ningun_bloque_oficial_se_queda_sin_mirar(self):
        """Ni un bloque sin decir de dónde sale, ni una entrada de un bloque que no existe.

        Las dos direcciones: si algún día se añade un bloque al esquema, esto se pone en rojo y
        obliga a decidir de dónde sale.
        """
        del_mapa = {fila["bloque"] for fila in iuws_mapeo.mapa_del_cuaderno()}
        de_la_tabla = {entrada.bloque for entrada in iuws_mapeo.DE_DONDE_SALE_CADA_BLOQUE}
        assert de_la_tabla == del_mapa

    def test_las_tablas_que_se_nombran_existen_de_verdad(self):
        """Si alguien renombra una tabla del cuaderno, esto lo dice en vez de mentir."""
        from app import models

        for entrada in iuws_mapeo.DE_DONDE_SALE_CADA_BLOQUE:
            if entrada.tabla is None:
                continue
            assert hasattr(models, entrada.tabla), f"no existe la tabla {entrada.tabla}"
            assert hasattr(getattr(models, entrada.tabla), "__table__")

    def test_el_unico_bloque_del_que_no_tenemos_nada_es_la_energia(self):
        """Y se dice por qué: la app oficial de Castilla y León tampoco lo pide."""
        assert iuws_mapeo.bloques_sin_tabla() == ("EnergiaUtilizada",)
        entrada = iuws_mapeo.de_donde_sale("EnergiaUtilizada")
        assert entrada.tabla is None
        assert "a propósito" in entrada.nota or "tampoco lo pide" in entrada.nota

    def test_una_tabla_cubre_siete_bloques_oficiales(self):
        """`Labor` sola cubre siete: el cuaderno apunta las labores por su tipo.

        Es el dato que hace falta para saber dónde está el trabajo: de los 18 bloques, 7 salen de
        la misma tabla y 3 de los tratamientos.
        """
        resumen = iuws_mapeo.resumen_del_cuaderno()
        varios = resumen["tablas_que_cubren_varios_bloques"]
        assert len(varios["Labor"]) == 7
        assert set(varios["Labor"]) == {
            "UsoSemillaTratada",
            "Cosecha",
            "SiembraPlantacion",
            "DatosCubierta",
            "Pastoreo",
            "LaboresCulturales",
            "Riego",
        }
        assert len(varios["TratamientoFitosanitario"]) == 3
        assert "TratamFito" in varios["TratamientoFitosanitario"]

    def test_cada_fila_del_mapa_trae_de_donde_sale(self):
        for fila in iuws_mapeo.mapa_del_cuaderno():
            assert "de_donde_sale" in fila
            assert "tabla" in fila["de_donde_sale"]


class TestLaFechaOficial:
    def test_una_fecha_se_convierte_al_formato_que_pide_el_interfaz(self):
        assert iuws_mapeo.fecha_oficial(dt.date(2026, 5, 1)) == "01/05/2026"

    def test_la_iso_se_convierte_y_no_se_manda_tal_cual(self):
        """El hallazgo, comprobado: `2026-05-01` **no** cumple el patrón oficial."""
        patron = iuws_mapeo.PATRON_DE_FECHA_OFICIAL
        assert not re.fullmatch(patron, "2026-05-01"), "si esto pasa, el esquema ha cambiado"
        assert iuws_mapeo.fecha_oficial("2026-05-01") == "01/05/2026"
        assert re.fullmatch(patron, iuws_mapeo.fecha_oficial("2026-05-01"))

    def test_el_patron_es_el_del_esquema_de_verdad(self):
        """No una copia que se quede vieja: el mismo texto, leído del esquema."""
        del_esquema = nodo_del_tratamiento()["properties"]["FechaInicio"]["pattern"]
        assert del_esquema == iuws_mapeo.PATRON_DE_FECHA_OFICIAL

    def test_tambien_vale_un_datetime_y_lo_que_ya_esta_bien(self):
        assert iuws_mapeo.fecha_oficial(dt.datetime(2026, 5, 1, 7, 30)) == "01/05/2026"
        assert iuws_mapeo.fecha_oficial("01/05/2026") == "01/05/2026"
        assert iuws_mapeo.fecha_oficial("1-5-2026") == "1-5-2026"

    def test_sin_fecha_o_con_basura_devuelve_nada_y_no_una_fecha_inventada(self):
        """Nunca la de hoy: eso sería un dato falso con formato válido."""
        for valor in (None, "", "   ", "ayer", "2026-13-45", 0):
            assert iuws_mapeo.fecha_oficial(valor) is None, f"{valor!r} no debería dar fecha"

    def test_la_fecha_oficial_la_acepta_el_esquema(self):
        """La prueba que cuenta: el validador oficial, no nuestro patrón copiado."""
        cuerpo = {
            "CUADERNO": [
                {
                    "CAExplotacion": "13",
                    "IdTitular": "70922320A",
                    "CodigoRea": "ES130000008847",
                    "UnidadGestora": "B12345678",
                    "ActividadesExplotacion": {
                        "TratamFito": [
                            {
                                "IdAjenaTratamFito": 14,
                                "FechaInicio": iuws_mapeo.fecha_oficial(dt.date(2026, 5, 1)),
                                "FechaFin": iuws_mapeo.fecha_oficial(dt.date(2026, 5, 1)),
                                "DGCs": [{"CodigoDGC": 1}],
                                "ProblematicaFito": {},
                                "Justificaciones": [{"JustAct": 20}],
                                "IdentificadorAplicador": [
                                    {
                                        "AplicadorEmpresa": {"NumROPO": "1234"},
                                        # El esquema exige **uno** de los tres: número de ROMA,
                                        # número de REGANIP o nuestro propio identificador de
                                        # equipo (`oneOf`). Aquí se pone el de ROMA, que es el
                                        # que el cuaderno sí guarda.
                                        "EquipoAplicador": {
                                            "AplicacionManual": False,
                                            "NumROMA": "ROMA-123",
                                        },
                                    }
                                ],
                                "Eficacia": 3,
                            }
                        ]
                    },
                }
            ]
        }
        assert iuws_cliente.errores_del_esquema(cuerpo) == []


class TestElIdentificadorOficial:
    def test_es_un_numero_y_no_el_identificador_de_la_aplicacion(self):
        """`CD-70922320A-T-14` es buen identificador para nosotros y no vale para el interfaz.

        El campo oficial es `integer`, así que se manda el número de la fila. Se deja escrito
        porque es justo lo que parece que vale y no vale.
        """
        class Fila:
            id = 14

        assert iuws_mapeo.identificador_oficial(Fila()) == 14
        assert isinstance(iuws_mapeo.identificador_oficial(Fila()), int)
        assert iuws.id_ajeno("70922320A", "tratamiento", 14) == "CD-70922320A-T-14"

    def test_el_campo_oficial_es_un_entero(self):
        tipos = nodo_del_tratamiento()["properties"]["IdAjenaTratamFito"]["type"]
        assert tipos == "integer"

    def test_sin_fila_o_con_una_imposible_no_devuelve_nada(self):
        class SinId:
            pass

        class Cero:
            id = 0

        class Enorme:
            id = iuws_mapeo.MAXIMO_IDENTIFICADOR + 1

        for registro in (SinId(), Cero(), Enorme(), None):
            assert iuws_mapeo.identificador_oficial(registro) is None


class TestElBloqueoEstaDondeSeDice:
    def test_sin_los_codigos_el_tratamiento_no_valida(self):
        """Y esto es exactamente lo que hay hoy: la estructura puede estar bien y no bastar."""
        cuerpo = {
            "CUADERNO": [
                {
                    "CAExplotacion": "13",
                    "IdTitular": "70922320A",
                    "CodigoRea": "ES130000008847",
                    "UnidadGestora": "B12345678",
                    "ActividadesExplotacion": {
                        "TratamFito": [
                            {
                                "IdAjenaTratamFito": 14,
                                "FechaInicio": "01/05/2026",
                                "FechaFin": "01/05/2026",
                            }
                        ]
                    },
                }
            ]
        }
        fallos = iuws_cliente.errores_del_esquema(cuerpo)
        assert fallos, "un tratamiento a medias no puede pasar por bueno"
        # Se dice **qué** falta, que es lo que sirve para trabajar.
        for esperado in ("DGCs", "ProblematicaFito", "Justificaciones", "Eficacia"):
            assert any(esperado in fallo for fallo in fallos), fallos
