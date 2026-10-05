"""Los cuatro defectos de «un dato que no se sabe acaba pareciendo un dato que sí se sabe».

**Qué era este fichero, y qué es ahora.** Nació como el **diagnóstico** de los cuatro apartados
A4, A5, A6 y A7 de `docs/T02_VALORES_POR_DEFECTO.md`: cada prueba reproducía el caso concreto que
describe el documento y **exigía el comportamiento de entonces**, que era el defectuoso. Servía
para saber exactamente qué se estaba cambiando y para poder comprobar que las pruebas nuevas fallan
con el código viejo delante.

Hoy los cuatro están cerrados, así que el fichero exige lo **contrario** que exigía, y en cada
prueba está escrito qué decía antes, por qué el comportamiento nuevo es el bueno y por qué el de
antes no lo era (`AGENTS.md` §1: una prueba se actualiza explicando el motivo, nunca se borra). Las
clases y las pruebas se han renombrado para que el nombre diga lo que de verdad comprueban
—`…NoVe…` pasó a ser `…YaVe…`—, y **ninguna se ha quitado**: las nueve de antes siguen aquí,
transformadas, y cada apartado tiene además sus casos de dato conocido, dato desconocido, grupo,
corrección y anulación, que es lo que pide el encargo.

**La regla que decide todos los casos.** `None` («no lo sé») no es `False` («no») ni `0` («es
cero»), y un dato que no se sabe **avisa y no bloquea**: el cuaderno tiene que recoger lo que de
verdad ha pasado en el campo; lo que no puede es callarse y dar a entender que lo ha comprobado.

**Las nueve pruebas de antes, una por una** (ninguna se ha borrado; el nombre viejo se quedó
describiendo el defecto, y el nuevo describe lo que ahora se exige):

| Antes se llamaba… | Ahora se llama… |
|---|---|
| `…por_grupo_no_cuentan_para_el_nitrogeno_de_la_tierra` | `…por_grupo_cuentan_para_el_nitrogeno_de_cada_tierra` |
| `…el_aviso_del_tope_no_salta_aunque_se_pase` | `…el_aviso_del_tope_ya_salta_cuando_se_pasa_de_verdad` |
| `el_control_los_mismos_abonos_apuntados_en_la_tierra_si_hacen_saltar_el_aviso` | *(igual: es el control y sigue valiendo)* |
| `un_producto_sin_plazo_se_puede_dar_de_alta_y_queda_sin_plazo` | *(igual: la puerta no se cierra)* |
| `cosechar_al_dia_siguiente_se_permite_sin_decir_nada` | `cosechar_con_un_plazo_desconocido_ya_no_pasa_en_silencio` |
| `la_ficha_y_el_abono_quedan_con_cero_nutrientes` | `la_ficha_y_el_abono_quedan_sin_composicion_no_con_cero` |
| `ese_cero_entra_en_el_documento_que_se_firma` | `ese_hueco_entra_en_el_documento_que_se_firma_como_no_se_sabe` |
| `la_tierra_importada_sin_superficie_cultivada_queda_con_cero_hectareas` | `…se_queda_sin_superficie` |
| `por_eso_el_tratamiento_siguiente_se_bloquea` | `esa_tierra_se_puede_tratar_y_el_aviso_dice_donde_se_arregla` |

| Apartado del documento | Lo que estaba mal | Lo que exige ahora este fichero |
|---|---|---|
| **A4** | Un abono apuntado por grupo no contaba para el tope de 170 kg de ninguna tierra | Cuenta en cada tierra del grupo a su dosis por hectárea, y lo que no se puede atribuir se declara |
| **A5** | Un plazo de seguridad que no se sabe se trataba como «no hay plazo» | Produce un aviso que dice que no se ha podido comprobar, y no bloquea |
| **A6** | Un abono sin composición eran «cero nutrientes», también en el documento firmado | La composición desconocida es desconocida en el cálculo, en el volcado y en lo que se firma |
| **A7** | Una superficie que no se sabe se convertía en 0 ha y cerraba la puerta a tratar la tierra | Es un dato pendiente: la tierra se puede tratar y el aviso dice dónde se arregla |

**Lo que NO hace.** No abre la base de datos del agricultor (la suite usa la suya, `AGENTS.md`
§3.10), no arranca ningún servidor y no escribe ningún fichero: el único cuaderno que se modifica
se modifica **en memoria** y se explica por qué donde se hace.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import pathlib

import pytest
from openpyxl import load_workbook

from app import cuaderno_cyl, firma, legal, models, servicios

# El cuaderno de la Junta de ejemplo que ya usan los tests del lector (`tests/test_cuaderno_cyl.py`).
FICHERO_DE_EJEMPLO = (
    pathlib.Path(__file__).resolve().parent / "datos" / "cuaderno_cyl_de_ejemplo.xlsx"
)

# El documento que describe los cuatro defectos, citado en cada prueba.
DOCUMENTO = "docs/T02_VALORES_POR_DEFECTO.md"

# La referencia del SIGPAC de la primera línea del cuaderno de ejemplo, que es la que se importa
# sin superficie cultivada en las pruebas de A7.
REFERENCIA_DE_LA_PRIMERA_LINEA = "99-99-0-0-1-1-1"


def _cuaderno_sin_la_superficie_cultivada() -> bytes:
    """El cuaderno de ejemplo, con la casilla «Superficie Cultivada (ha)» de su primera línea vacía.

    POR QUÉ SE VACÍA UNA CASILLA EN VEZ DE FABRICAR UN FICHERO. El caso que reproduce A7 es el de
    verdad: «la plantilla de la Junta dejó la casilla vacía en varias tierras»
    (`docs/T02_VALORES_POR_DEFECTO.md`, A7). El cuaderno de ejemplo del repositorio las trae todas
    rellenas, así que lo único honesto es **quitarle** ese valor: no se añade ningún dato
    inventado, se deja en blanco uno, que es exactamente lo que hace el papel de la Junta cuando
    no lo trae. Y en blanco es «no lo sé», que es como lo lee el propio lector
    (`cuaderno_cyl.py:711`).

    La columna se busca **con el mismo lector que usa el programa**
    (`cuaderno_cyl._columna_de_la_cabecera`, que va por el texto de la cabecera) y no por la letra
    de la columna: la plantilla de la Junta cambió entre 2024 y 2025, y con coordenadas fijas esta
    prueba se rompería sola o, peor, vaciaría otra celda sin que nadie se diera cuenta.
    """
    libro = load_workbook(io.BytesIO(FICHERO_DE_EJEMPLO.read_bytes()))
    hoja = libro[cuaderno_cyl.HOJA_PARCELAS]
    celdas = cuaderno_cyl._celdas(hoja)

    # La tabla se localiza igual que la localiza el lector: por la cabecera «Nº DE ORDEN».
    fila_cabecera = next(
        fila
        for fila, _columna, texto in celdas
        if cuaderno_cyl._sin_acentos(texto).startswith(
            cuaderno_cyl._sin_acentos(cuaderno_cyl.TEXTO_CABECERA_DE_ORDEN)
        )
    )
    filas_cabecera = (fila_cabecera, fila_cabecera + 1)
    columna_orden = cuaderno_cyl._columna_de_la_cabecera(
        celdas, cuaderno_cyl.CABECERAS_DE_PARCELA["orden"], filas=filas_cabecera
    )
    columna_cultivada = cuaderno_cyl._columna_de_la_cabecera(
        celdas, cuaderno_cyl.CABECERAS_DE_PARCELA["superficie_cultivada"], filas=filas_cabecera
    )
    assert columna_orden is not None and columna_cultivada is not None, (
        "el cuaderno de ejemplo tiene que traer la cabecera del número de orden y la de la "
        "superficie cultivada: si no, esta prueba no está vaciando lo que cree"
    )

    for fila in range(filas_cabecera[1] + 1, hoja.max_row + 1):
        if hoja.cell(row=fila, column=columna_orden).value == 1:
            hoja.cell(row=fila, column=columna_cultivada).value = None
            break
    else:  # pragma: no cover — solo pasaría si el cuaderno de ejemplo cambiara de forma
        raise AssertionError("no encuentro la primera línea del cuaderno de ejemplo")

    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


# --------------------------------------------------------------------------
# A4 — el tope de los 170 kg ya ve los abonos apuntados por grupo
# --------------------------------------------------------------------------


class TestA4ElTopeDeLos170KgYaVeLosAbonosPorGrupo:
    """A4 — «Cero nitrógeno en los abonos por grupo» (`docs/T02_VALORES_POR_DEFECTO.md`, A4).

    **EL DEFECTO QUE REPRODUCÍA ESTA CLASE.** `servicios.nitrogeno_organico_en_la_parcela` empezaba
    por `if parcela_id is None: return 0.0`, y un abono apuntado en un grupo de tierras **no lleva
    `parcela_id`**: es lo que manda la pantalla al elegir un grupo. Así que todo el estiércol o
    purín echado por grupo contaba **cero** para el tope de 170 kg de nitrógeno por hectárea y año
    de la Orden MAV/398/2022, y la regla `N1_estiercol_pasa_tope` no saltaba ni aunque se pasara de
    verdad: el programa **creía** estar comprobando un límite legal y no lo comprobaba.

    **LO QUE EXIGE AHORA, Y POR QUÉ ES LO BUENO.** Lo apuntado en un grupo **cuenta en cada tierra
    del grupo**, y con un criterio que no inventa nada: se le suma la dosis **por hectárea** del
    apunte (`uf_n_ha`), nunca los kilos totales del grupo repartidos entre las tierras. No es un
    reparto porque un grupo es una **unidad homogénea de cultivo** —`models.GrupoParcelas` dice
    «parcelas que se llevan igual»— y lo que se apuntó es lo que se echó **en cada hectárea** de ese
    conjunto: la misma cifra vale para cada tierra y se cuenta una vez en cada una. Repartir los
    kilos **totales** sí sería inventarse un reparto, y es lo que este código no hace nunca.

    **Y LO QUE NO SE PUEDE ATRIBUIR, SE DICE.** Si el apunte del grupo no cuadra con la superficie
    del grupo (se abonó una parte y no se sabe cuál) o si a alguna tierra del grupo le falta la
    superficie, el apunte **no se le suma** a la tierra, se cuenta aparte y sale el aviso
    `F8_aporte_por_grupo_sin_comprobar`, que no bloquea. Callar ahí sería volver al defecto de
    antes por la puerta de atrás: un cero que parece un dato.
    """

    # 2.500 kg/ha de un purín del 4 % de nitrógeno son 100 kg de nitrógeno por hectárea
    # (`uf = kg/ha × riqueza / 100`). Tres apuntes así son 300 kg N/ha, muy por encima de los 170
    # que permite la Orden MAV/398/2022 en un año.
    KILOS_DE_PURIN_POR_HECTAREA = 2500.0
    NITROGENO_DE_CADA_APUNTE = 100.0
    TRES_FECHAS = ("2026-02-10", "2026-03-10", "2026-04-10")

    @pytest.fixture
    def purin(self, cliente, cuenta):
        """Un purín con un 4 % de nitrógeno: 1.000 kg/ha son 40 kg N/ha."""
        respuesta = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Purín de cerdo", "tipo": "organico", "riqueza_n": 4.0},
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    @pytest.fixture
    def tierras_en_zona(self, crear_parcela):
        """Dos tierras de trigo en zona vulnerable a nitratos: ahí es donde vale el tope."""
        return [
            crear_parcela(alias="El Prado", zona_vulnerable_nitratos=True),
            crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True),
        ]

    @pytest.fixture
    def grupo(self, cliente, cuenta, tierras_en_zona):
        """Las dos tierras juntas: es la unidad de cultivo con la que se abona de una vez.

        Se devuelve el grupo tal y como lo da el **listado** y no el alta, porque la superficie
        sumada de las tierras (`superficie_total_ha`, que es la que se apunta al abonar todo el
        grupo) la trae el listado.
        """
        creado = cliente.post(
            "/api/grupos",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "Los trigos",
                "parcela_ids": [parcela["id"] for parcela in tierras_en_zona],
            },
        )
        assert creado.status_code == 201, creado.text
        grupos = cliente.get("/api/grupos", headers=cuenta["cabeceras"]).json()
        return next(grupo for grupo in grupos if grupo["id"] == creado.json()["id"])

    def _abonar_por_grupo(
        self, cliente, cuenta, campana, grupo, purin, fecha: str, superficie_ha: float | None = None
    ) -> dict:
        """Apunta un abono del grupo, como lo hace la pantalla: el grupo y ninguna tierra.

        `superficie_ha` se puede bajar a mano para probar el caso en que el apunte **no cubre todo
        el grupo**: entonces se abonó una parte y no se sabe cuál, que es lo que no se puede
        atribuir a ninguna tierra.
        """
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": fecha,
                "grupo_id": grupo["id"],
                "superficie_ha": (
                    grupo["superficie_total_ha"] if superficie_ha is None else superficie_ha
                ),
                "fertilizante_id": purin["id"],
                "kg_ha_producto": self.KILOS_DE_PURIN_POR_HECTAREA,
                "modo_aplicacion": "al suelo",
                "momento": "fondo",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def _abonar_en_la_tierra(self, cliente, cuenta, campana, parcela, purin, fecha: str) -> dict:
        """El mismo abono, pero apuntado en una tierra concreta (el caso que sí se contaba)."""
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": fecha,
                "parcela_id": parcela["id"],
                "superficie_ha": parcela["superficie_ha"],
                "fertilizante_id": purin["id"],
                "kg_ha_producto": self.KILOS_DE_PURIN_POR_HECTAREA,
                "modo_aplicacion": "al suelo",
                "momento": "fondo",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def _validar_en_la_tierra(self, cliente, cuenta, campana, parcela, purin, fecha: str) -> dict:
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": fecha,
                "parcela_id": parcela["id"],
                "superficie_ha": parcela["superficie_ha"],
                "fertilizante_id": purin["id"],
                "kg_ha_producto": self.KILOS_DE_PURIN_POR_HECTAREA,
                "modo_aplicacion": "al suelo",
                "momento": "fondo",
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        return respuesta.json()

    def _nitrogeno(self, db_sesion, cuenta, campana, parcela):
        return servicios.nitrogeno_organico_en_la_parcela(
            db_sesion,
            explotacion_id=cuenta["explotacion_id"],
            parcela_id=parcela["id"],
            campana_id=campana["id"],
        )

    def test_los_abonos_apuntados_por_grupo_cuentan_para_el_nitrogeno_de_cada_tierra(
        self, cliente, cuenta, campana, grupo, tierras_en_zona, purin, db_sesion
    ):
        """Tres abonos del grupo (300 kg N/ha de purín) y la tierra ya no está «a cero».

        ANTES esta prueba se llamaba «…no cuentan para el nitrogeno…» y exigía `organico == 0.0`,
        que era el defecto. Se ha dado la vuelta explicando el motivo: los tres apuntes existen, el
        dato está guardado y el tope es **por tierra**, así que esa tierra lleva 300 kg N/ha.
        """
        for fecha in self.TRES_FECHAS:
            abono = self._abonar_por_grupo(cliente, cuenta, campana, grupo, purin, fecha)
            # El apunte se guarda entero, con su nitrógeno calculado: el dato existe.
            assert abono["grupo_id"] == grupo["id"], "el abono tiene que quedar apuntado al grupo"
            assert abono["parcela_id"] is None, (
                "un abono de grupo se guarda sin tierra, que es lo que manda la pantalla al "
                "elegir el grupo: ahí está la raíz del defecto"
            )
            assert abono["uf_n_ha"] == self.NITROGENO_DE_CADA_APUNTE, (
                "2.500 kg/ha de un purín del 4 % son 100 kg de nitrógeno por hectárea"
            )

        # Y ahora el nitrógeno de esa tierra cuenta los tres:
        organico = self._nitrogeno(db_sesion, cuenta, campana, tierras_en_zona[0])
        assert organico.kg_n_ha == 3 * self.NITROGENO_DE_CADA_APUNTE, (
            "3 apuntes de 100 kg N/ha son 300 kg N/ha, y el tope de la Orden MAV/398/2022 es de "
            "170: antes devolvía 0,0 porque el apunte del grupo no lleva `parcela_id` "
            f"({DOCUMENTO}, A4)"
        )
        assert organico.apuntes == 3, "los tres apuntes entran en la cuenta"
        assert organico.sin_atribuir == 0, (
            "y entran enteros, no a medias: el apunte cubre todo el grupo y el grupo tiene su "
            "superficie, así que se pueden atribuir a esta tierra"
        )
        assert organico.esta_completo is True

    def test_por_eso_el_aviso_del_tope_ya_salta_cuando_se_pasa_de_verdad(
        self, cliente, cuenta, campana, grupo, tierras_en_zona, purin
    ):
        """Los tres abonos del grupo, y el cuarto —este en la tierra— ya no pasan en silencio.

        ANTES esta prueba se llamaba «…el aviso del tope no salta aunque se pase» y comprobaba que
        `N1_estiercol_pasa_tope` **no** estaba. Ahora tiene que estar, y con los números de verdad:
        300 que llevaba la tierra más 100 del nuevo son 400, muy por encima de 170.
        """
        for fecha in self.TRES_FECHAS:
            self._abonar_por_grupo(cliente, cuenta, campana, grupo, purin, fecha)

        resultado = self._validar_en_la_tierra(
            cliente, cuenta, campana, tierras_en_zona[0], purin, "2026-04-20"
        )
        avisos = {aviso["codigo"]: aviso for aviso in resultado["avisos"]}

        # La comprobación de que el montaje es el correcto: esa tierra está en zona de nitratos.
        assert "F3_zona_nitratos" in avisos, (
            "la tierra está en zona vulnerable a nitratos, así que la regla de los 170 kg le "
            "aplica: que no salga el aviso de abajo no es que no tocara comprobarlo"
        )
        assert resultado["puede_guardarse"] is True, (
            "el tope avisa y no bloquea: el cuaderno tiene que recoger lo que de verdad se echó"
        )

        assert "N1_estiercol_pasa_tope" in avisos, (
            "esa tierra lleva 400 kg N/ha de purín en el año (3 × 100 del grupo más 100 del "
            f"nuevo) y el tope es de 170: {DOCUMENTO}, A4"
        )
        mensaje = avisos["N1_estiercol_pasa_tope"]["mensaje"]
        assert "300,0" in mensaje, "el aviso tiene que decir lo que ya llevaba la tierra"
        assert "400,0" in mensaje, "y lo que llevaría con este"
        assert avisos["N1_estiercol_pasa_tope"]["bloquea"] is False
        assert "F8_aporte_por_grupo_sin_comprobar" not in avisos, (
            "aquí sí se ha podido atribuir todo: avisar de lo contrario sería ruido"
        )

    def test_el_control_los_mismos_abonos_apuntados_en_la_tierra_si_hacen_saltar_el_aviso(
        self, cliente, cuenta, campana, tierras_en_zona, purin
    ):
        """La prueba de que lo que falla no son los números, sino el camino del grupo.

        Los mismos tres apuntes de 2.500 kg/ha, pero **en la tierra**: el tercero avisa de que se
        pasa de los 170 kg. Esta prueba se queda como estaba a propósito: es el control de que el
        montaje mide lo que dice medir.
        """
        tierra = tierras_en_zona[1]
        for fecha in self.TRES_FECHAS[:2]:
            self._abonar_en_la_tierra(cliente, cuenta, campana, tierra, purin, fecha)

        resultado = self._validar_en_la_tierra(
            cliente, cuenta, campana, tierra, purin, self.TRES_FECHAS[2]
        )
        avisos = {aviso["codigo"]: aviso for aviso in resultado["avisos"]}
        assert "N1_estiercol_pasa_tope" in avisos, (
            "apuntando los mismos abonos en la tierra, el tercero pasa de los 170 kg y el "
            "programa tiene que avisar"
        )
        assert "200,0" in avisos["N1_estiercol_pasa_tope"]["mensaje"], (
            "el aviso tiene que decir lo que ya llevaba esa tierra: dos apuntes de 100 kg N/ha"
        )
        assert avisos["N1_estiercol_pasa_tope"]["bloquea"] is False, (
            "el tope avisa y no bloquea: el cuaderno tiene que recoger lo que de verdad se echó"
        )

    def test_lo_que_no_se_puede_atribuir_se_cuenta_aparte_y_se_dice(
        self, cliente, cuenta, campana, grupo, tierras_en_zona, purin, db_sesion
    ):
        """Un abono que solo cubre una parte del grupo **no se le suma a ninguna tierra**.

        Y no se calla: es el caso en que el agricultor abonó una parte de las tierras del grupo y el
        apunte no dice cuál. Sumárselo a todas sería inventarse un reparto; no sumarlo y no decir
        nada sería el defecto de antes, un cero que parece un dato.
        """
        # El grupo suma 4,86 ha y el apunte dice que se abonaron 2: no cuadra, y no se sabe qué
        # mitad del grupo fue.
        self._abonar_por_grupo(
            cliente, cuenta, campana, grupo, purin, "2026-02-10", superficie_ha=2.0
        )

        organico = self._nitrogeno(db_sesion, cuenta, campana, tierras_en_zona[0])
        assert organico.kg_n_ha == 0.0, "no se le puede sumar lo que no se sabe si recibió"
        assert organico.sin_atribuir == 1, "pero tampoco se puede perder de vista"
        assert organico.esta_completo is False

        resultado = self._validar_en_la_tierra(
            cliente, cuenta, campana, tierras_en_zona[0], purin, "2026-02-20"
        )
        avisos = {aviso["codigo"]: aviso for aviso in resultado["avisos"]}
        assert "F8_aporte_por_grupo_sin_comprobar" in avisos, (
            "el programa tiene que decir que no ha podido atribuir ese aporte, que es el tercer "
            f"final de `AGENTS.md`: {DOCUMENTO}, A4"
        )
        assert avisos["F8_aporte_por_grupo_sin_comprobar"]["bloquea"] is False, (
            "avisa y no bloquea: no se puede impedir apuntar el abono que se ha echado"
        )
        assert "1 abono" in avisos["F8_aporte_por_grupo_sin_comprobar"]["mensaje"], (
            "y lo dice en singular, que «1 abonos» es lo primero que hace desconfiar de un programa"
        )
        assert resultado["puede_guardarse"] is True

    def test_un_grupo_al_que_le_falta_una_superficie_tampoco_se_puede_sumar(
        self, cliente, cuenta, campana, crear_parcela, purin, db_sesion
    ):
        """A4 y A7 se juntan: sin la superficie del grupo no se sabe si el apunte lo cubrió entero.

        Es el caso de una tierra traída del cuaderno de la Junta sin superficie (A7). El total del
        grupo no se puede sumar —una suma a la que le falta un número es una parte— así que el
        aporte no se atribuye y **se dice**, en vez de dar por bueno el tope.
        """
        con_superficie = crear_parcela(alias="El Prado", zona_vulnerable_nitratos=True)
        sin_superficie = crear_parcela(
            alias="La Vega", zona_vulnerable_nitratos=True, superficie_ha=None
        )
        grupo = cliente.post(
            "/api/grupos",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "Los trigos",
                "parcela_ids": [con_superficie["id"], sin_superficie["id"]],
            },
        ).json()

        # Se apunta el abono del grupo entero con la superficie de la única tierra que la tiene.
        self._abonar_por_grupo(
            cliente, cuenta, campana, grupo, purin, "2026-02-10", superficie_ha=2.43
        )

        organico = self._nitrogeno(db_sesion, cuenta, campana, con_superficie)
        assert organico.kg_n_ha == 0.0, "no se puede comparar contra una superficie que no existe"
        assert organico.sin_atribuir == 1

    def test_el_apunte_de_grupo_no_cuenta_en_una_tierra_que_no_esta_en_el_grupo(
        self, cliente, cuenta, campana, grupo, tierras_en_zona, purin, crear_parcela, db_sesion
    ):
        """Fuera del grupo no se cuenta nada: el aporte es de las tierras del grupo, y de ninguna más."""
        de_fuera = crear_parcela(alias="El Prado de arriba", zona_vulnerable_nitratos=True)
        self._abonar_por_grupo(cliente, cuenta, campana, grupo, purin, "2026-02-10")

        organico = self._nitrogeno(db_sesion, cuenta, campana, de_fuera)
        assert organico.kg_n_ha == 0.0
        assert organico.sin_atribuir == 0, "no hay nada que atribuir: ese abono no era de esta tierra"

    def test_lo_anulado_no_cuenta_y_el_aviso_de_lo_que_no_se_pudo_atribuir_desaparece(
        self, cliente, cuenta, campana, grupo, tierras_en_zona, purin, db_sesion
    ):
        """Lo que se anuló no se echó, ni por grupo ni de ninguna manera.

        Y al anularlo, el aviso de «no lo he podido atribuir» tiene que irse con él: si se quedara,
        el programa estaría avisando de un aporte que ya no existe.
        """
        abono = self._abonar_por_grupo(
            cliente, cuenta, campana, grupo, purin, "2026-02-10", superficie_ha=2.0
        )
        assert self._nitrogeno(db_sesion, cuenta, campana, tierras_en_zona[0]).sin_atribuir == 1

        anulado = cliente.post(
            f"/api/fertilizaciones/{abono['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de tierras"},
        )
        assert anulado.status_code == 200, anulado.text

        organico = self._nitrogeno(db_sesion, cuenta, campana, tierras_en_zona[0])
        assert organico.kg_n_ha == 0.0
        assert organico.sin_atribuir == 0, "un apunte anulado no es un aporte que no se pudo atribuir"

        resultado = self._validar_en_la_tierra(
            cliente, cuenta, campana, tierras_en_zona[0], purin, "2026-02-20"
        )
        codigos = {aviso["codigo"] for aviso in resultado["avisos"]}
        assert "F8_aporte_por_grupo_sin_comprobar" not in codigos

    def test_al_corregir_el_abono_del_grupo_el_nitrogeno_de_la_tierra_se_recalcula(
        self, cliente, cuenta, campana, grupo, tierras_en_zona, purin, db_sesion
    ):
        """Corregir el apunte cambia lo que cuenta en la tierra, no se queda el número viejo."""
        abono = self._abonar_por_grupo(cliente, cuenta, campana, grupo, purin, "2026-02-10")
        assert self._nitrogeno(db_sesion, cuenta, campana, tierras_en_zona[0]).kg_n_ha == 100.0

        corregido = cliente.put(
            f"/api/fertilizaciones/{abono['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-10",
                "grupo_id": grupo["id"],
                "superficie_ha": grupo["superficie_total_ha"],
                "fertilizante_id": purin["id"],
                # La mitad de purín: 1.250 kg/ha son 50 kg N/ha.
                "kg_ha_producto": 1250.0,
                "modo_aplicacion": "al suelo",
                "momento": "fondo",
            },
        )
        assert corregido.status_code == 200, corregido.text

        organico = self._nitrogeno(db_sesion, cuenta, campana, tierras_en_zona[0])
        assert organico.kg_n_ha == 50.0, "la corrección tiene que llegar hasta el tope"
        assert organico.apuntes == 1, "y sigue siendo un apunte, no dos"

    def test_un_apunte_con_grupo_y_tierra_a_la_vez_cuenta_una_sola_vez(
        self, cliente, cuenta, campana, grupo, tierras_en_zona, purin, db_sesion
    ):
        """`parcela_id` y `grupo_id` a la vez: el agricultor dijo dónde, así que es de esa tierra.

        Contarlo además como aporte del grupo lo contaría dos veces, y duplicar un aporte es tan
        falso como perderlo.
        """
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-10",
                "parcela_id": tierras_en_zona[0]["id"],
                "grupo_id": grupo["id"],
                "superficie_ha": tierras_en_zona[0]["superficie_ha"],
                "fertilizante_id": purin["id"],
                "kg_ha_producto": self.KILOS_DE_PURIN_POR_HECTAREA,
                "modo_aplicacion": "al suelo",
                "momento": "fondo",
            },
        )
        assert respuesta.status_code == 201, respuesta.text

        organico = self._nitrogeno(db_sesion, cuenta, campana, tierras_en_zona[0])
        assert organico.kg_n_ha == 100.0, "una vez, no dos"
        assert organico.apuntes == 1


# --------------------------------------------------------------------------
# A5 — un plazo de seguridad que no se sabe es una comprobación pendiente
# --------------------------------------------------------------------------


class TestA5UnPlazoDeSeguridadQueNoSeSabeYaNoEsComoSinPlazo:
    """A5 — «Un plazo de seguridad que no se sabe se trata como “no hay plazo”» (A5 del documento).

    **EL DEFECTO QUE REPRODUCÍA ESTA CLASE.** El plazo de seguridad es opcional, tanto en la ficha
    del producto como en el apunte (`schemas.py`). Cuando no se sabe, vale `None`, y entonces
    `validaciones.validar_cosecha` **saltaba ese tratamiento y seguía con el siguiente**: no
    avisaba, no bloqueaba y no decía que no lo había podido comprobar. Y el respaldo por el catálogo
    de productos tampoco actuaba desde el endpoint, porque `registros.py` lo llamaba sin pasarle
    `producto_por_id`, así que el diccionario iba vacío y nunca encontraba nada. Resultado: se
    cosechaba al día siguiente de tratar y el cuaderno no decía ni una palabra.

    **LO QUE EXIGE AHORA, Y POR QUÉ ES LO BUENO.** El plazo desconocido es **una comprobación
    pendiente con su aviso** (`V27_plazo_de_seguridad_sin_comprobar`) y **nunca un permiso
    implícito**. No bloquea —el agricultor ha cogido la cosecha y el cuaderno tiene que recogerlo,
    y las reglas de la casa dicen que un dato que no se sabe avisa y no bloquea—, pero tampoco se
    calla, y dice qué hacer para que se pueda comprobar. Y el respaldo por catálogo **ahora sí
    funciona**: si el plazo se rellenó en la ficha del producto después de tratar, la comprobación
    de verdad (la que bloquea) vuelve a saltar.
    """

    FECHA_DEL_TRATAMIENTO = "2026-05-10"
    FECHA_DE_LA_COSECHA = "2026-05-11"

    @pytest.fixture
    def insecticida_sin_plazo(self, crear_producto):
        """Un producto del catálogo al que nadie le ha puesto el plazo de seguridad."""
        return crear_producto(
            nombre_comercial="Insecticida sin plazo en la etiqueta",
            plazo_seguridad_dias=None,
        )

    def _tratar(self, cliente, cuenta, nuevo_tratamiento, producto, fecha=None):
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(
                producto_id=producto["id"], fecha=fecha or self.FECHA_DEL_TRATAMIENTO
            ),
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def _comprobar(self, cliente, cuenta, campana, parcela, fecha=None):
        cuerpo = {
            "campana_id": campana["id"],
            "fecha": fecha or self.FECHA_DE_LA_COSECHA,
            "parcela_id": parcela["id"],
        }
        respuesta = cliente.post(
            "/api/cosecha/validar", headers=cuenta["cabeceras"], json=cuerpo
        )
        assert respuesta.status_code == 200, respuesta.text
        return cuerpo, {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}, respuesta

    def test_un_producto_sin_plazo_se_puede_dar_de_alta_y_queda_sin_plazo(
        self, insecticida_sin_plazo
    ):
        """La puerta del defecto: el catálogo admite productos de los que no se sabe el plazo.

        Sigue siendo verdad y **se queda como estaba**: la puerta no se cierra, porque el agricultor
        tiene que poder dar de alta un producto cuya etiqueta no dice el plazo (o que no ha mirado
        todavía). Lo que cambia es lo que pasa después al cosechar, que es lo que comprueban las
        pruebas de abajo.
        """
        assert insecticida_sin_plazo["plazo_seguridad_dias"] is None, (
            "el plazo es opcional y se puede quedar vacío: en la ficha no significa «no hay "
            "plazo», significa «no lo sé»"
        )

    def test_cosechar_con_un_plazo_desconocido_ya_no_pasa_en_silencio(
        self, cliente, cuenta, campana, parcela, insecticida_sin_plazo, nuevo_tratamiento
    ):
        """Se trata el 10 de mayo, se cosecha el 11, y el programa dice que no lo ha podido comprobar.

        ANTES esta prueba se llamaba «…se permite sin decir nada» y exigía `avisos == []`. Ahora
        exige el tercer estado: el aviso tiene que estar, no puede bloquear, y la cosecha se tiene
        que poder guardar igual —«el cuaderno tiene que recoger lo que de verdad ha pasado»—.
        """
        tratamiento = self._tratar(
            cliente, cuenta, nuevo_tratamiento, insecticida_sin_plazo
        )
        assert tratamiento["plazo_seguridad_dias"] is None, (
            "el apunte hereda el plazo del producto, y el producto no lo tiene"
        )
        assert tratamiento["fecha_fin_plazo_seguridad"] is None

        cuerpo, avisos, respuesta = self._comprobar(cliente, cuenta, campana, parcela)

        assert "V27_plazo_de_seguridad_sin_comprobar" in avisos, (
            "antes no salía ningún aviso: ni `V9_no_puedes_cosechar` ni uno que dijera que el "
            f"plazo no se ha podido comprobar ({DOCUMENTO}, A5). Ahora sale el tercero, que es el "
            "que faltaba"
        )
        assert avisos["V27_plazo_de_seguridad_sin_comprobar"]["bloquea"] is False, (
            "no saber no puede impedir apuntar la cosecha que se ha hecho"
        )
        assert respuesta.json()["puede_guardarse"] is True
        mensaje = avisos["V27_plazo_de_seguridad_sin_comprobar"]["mensaje"]
        assert "1 tratamiento" in mensaje, (
            "y lo cuenta en singular: «1 tratamiento», no «1 tratamiento(s)»"
        )
        assert "días de espera" in mensaje, "tiene que decir qué falta para poder comprobarlo"
        assert "Mis cosas" in mensaje, (
            "y dónde se arregla, que es la regla de `AGENTS.md`: no se deja al agricultor sin salida"
        )

        # Y no se queda en la comprobación previa: la cosecha se guarda de verdad…
        guardada = cliente.post("/api/cosecha", headers=cuenta["cabeceras"], json=cuerpo)
        assert guardada.status_code == 201, guardada.text
        assert guardada.json()["guardado"] is True
        # …pero con el aviso a cuestas, no en silencio.
        assert "V27_plazo_de_seguridad_sin_comprobar" in {
            aviso["codigo"] for aviso in guardada.json()["avisos"]
        }, "el aviso tiene que viajar con el apunte guardado, no quedarse en la pantalla anterior"

    def test_cuando_el_plazo_se_pone_en_la_ficha_despues_la_comprobacion_de_verdad_vuelve(
        self, cliente, cuenta, campana, parcela, insecticida_sin_plazo, nuevo_tratamiento
    ):
        """El respaldo por catálogo: el plazo se rellenó **después** de tratar, y ahora bloquea.

        Es el caso que `registros.py` no le pasaba a `validar_cosecha`: el diccionario iba vacío y
        el respaldo no encontraba nunca nada aunque la ficha del producto sí tuviera el plazo.
        """
        self._tratar(cliente, cuenta, nuevo_tratamiento, insecticida_sin_plazo)

        # Alguien mira la etiqueta y rellena el plazo de espera (21 días, como el producto de ejemplo).
        corregido = cliente.put(
            f"/api/productos/{insecticida_sin_plazo['id']}",
            headers=cuenta["cabeceras"],
            json={
                "nombre_comercial": insecticida_sin_plazo["nombre_comercial"],
                "plazo_seguridad_dias": 21,
            },
        )
        assert corregido.status_code == 200, corregido.text
        assert corregido.json()["plazo_seguridad_dias"] == 21

        _cuerpo, avisos, respuesta = self._comprobar(cliente, cuenta, campana, parcela)
        assert "V9_no_puedes_cosechar" in avisos, (
            "cosechar al día siguiente de tratar con un plazo de 21 días no se puede: ahora que el "
            "plazo se sabe, la comprobación de verdad tiene que saltar"
        )
        assert avisos["V9_no_puedes_cosechar"]["bloquea"] is True
        assert respuesta.json()["puede_guardarse"] is False
        assert "V27_plazo_de_seguridad_sin_comprobar" not in avisos, (
            "y ya no hay nada pendiente de comprobar: el aviso del tercer estado sobra"
        )

    def test_con_el_plazo_conocido_y_cumplido_no_se_avisa_de_nada(
        self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        """El control: cuando el plazo se sabe y ha pasado, no hay ni bloqueo ni aviso pendiente."""
        self._tratar(cliente, cuenta, nuevo_tratamiento, producto)
        _cuerpo, avisos, respuesta = self._comprobar(
            cliente, cuenta, campana, parcela, fecha="2026-06-15"
        )
        assert avisos == {}, "el producto de ejemplo tiene 21 días y se cosecha 45 días después"
        assert respuesta.json()["puede_guardarse"] is True

    def test_lo_anulado_no_pide_ninguna_comprobacion(
        self, cliente, cuenta, campana, parcela, insecticida_sin_plazo, nuevo_tratamiento
    ):
        """Un tratamiento anulado no puede dejar la cosecha «pendiente de comprobar» para siempre."""
        tratamiento = self._tratar(cliente, cuenta, nuevo_tratamiento, insecticida_sin_plazo)
        cliente.post(
            f"/api/tratamientos/{tratamiento['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de producto"},
        )
        _cuerpo, avisos, _respuesta = self._comprobar(cliente, cuenta, campana, parcela)
        assert avisos == {}, "lo que se anuló no se echó, así que no hay plazo que comprobar"

    def test_un_tratamiento_posterior_a_la_cosecha_no_cuenta(
        self, cliente, cuenta, campana, parcela, insecticida_sin_plazo, nuevo_tratamiento
    ):
        """Se cosecha el 11 y se trata el 20: ese tratamiento no tiene nada que ver con esta cosecha."""
        self._tratar(
            cliente, cuenta, nuevo_tratamiento, insecticida_sin_plazo, fecha="2026-05-20"
        )
        _cuerpo, avisos, _respuesta = self._comprobar(cliente, cuenta, campana, parcela)
        assert avisos == {}

    def test_la_prueba_del_tercer_estado_falla_con_el_codigo_viejo(self):
        """El aviso nuevo existe y **no** existía antes: es lo que hace que la prueba valga.

        Se comprueba aquí, con la regla pura (`validaciones.validar_cosecha`), sin pasar por el
        servidor: con el código de antes esto devolvía la lista vacía.
        """
        from app import validaciones

        class TratamientoFalso:
            fecha = dt.date(2026, 5, 10)
            plazo_seguridad_dias = None
            producto_id = None
            anulado = False

        avisos = validaciones.validar_cosecha(
            fecha_cosecha=dt.date(2026, 5, 11), tratamientos=[TratamientoFalso()]
        )
        assert [aviso.codigo for aviso in avisos] == [
            "V27_plazo_de_seguridad_sin_comprobar"
        ]


# --------------------------------------------------------------------------
# A6 — un abono sin composición no son «cero nutrientes»
# --------------------------------------------------------------------------


class TestA6UnAbonoSinComposicionYaNoSonCeroNutrientes:
    """A6 — «Un abono sin composición declarada son “cero nutrientes”, y eso entra en el
    documento firmado» (`docs/T02_VALORES_POR_DEFECTO.md`, A6).

    **EL DEFECTO QUE REPRODUCÍA ESTA CLASE.** `riqueza_n`, `riqueza_p` y `riqueza_k` de una ficha de
    abono eran `Float` **no nulo con defecto 0.0**, y lo mismo en el esquema de entrada: a un abono
    al que nadie le había dicho la composición se le ponía un `0.0` que quiere decir «no aporta
    nada», no «no lo sé». De ahí salían las unidades fertilizantes (`uf = kg/ha × riqueza / 100`),
    también a cero. Y ese cero **no se quedaba en una pantalla**: entraba en el texto canónico del
    cuaderno que se firma, con las líneas «Nitrógeno (%)», «Fósforo (%)», «Potasio (%)» y
    «Nitrógeno aportado (kg/ha)».

    **LO QUE EXIGE AHORA, Y POR QUÉ ES LO BUENO.** La composición desconocida es desconocida **en el
    cálculo, en la respuesta de la API, en el volcado a la Junta y en el texto que se firma**: no se
    puede calcular lo que aporta, así que no se calcula, y se dice «no se sabe» con las palabras que
    el documento ya usa para la zona de nitratos (`firma.numero_o_no_se`). Y **los históricos
    firmados no se tocan**: un apunte que ya estaba guardado con su `0.0` se sigue escribiendo «0»,
    exactamente igual que el día que se firmó, así que su huella sigue cuadrando y no hay que subir
    `VERSION_CANONICA`. Eso no es un detalle: cambiar la forma canónica invalidaría **todas** las
    firmas anteriores (`firma.py`).
    """

    KILOS_POR_HECTAREA = 5000.0

    @pytest.fixture
    def ficha_sin_composicion(self, cliente, cuenta):
        """Una ficha de abono a la que nadie le ha dicho la riqueza de N, P ni K."""
        respuesta = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Estiércol de la nave", "tipo": "organico"},
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def _abonar(self, cliente, cuenta, campana, parcela, ficha=None) -> dict:
        """Apunta el estiércol en la tierra: 5.000 kg/ha, que es un abono de verdad."""
        cuerpo = {
            "campana_id": campana["id"],
            "fecha": "2026-02-20",
            "parcela_id": parcela["id"],
            "superficie_ha": parcela["superficie_ha"],
            "kg_ha_producto": self.KILOS_POR_HECTAREA,
            "modo_aplicacion": "al suelo",
            "momento": "fondo",
        }
        if ficha is not None:
            cuerpo["fertilizante_id"] = ficha["id"]
        respuesta = cliente.post(
            "/api/fertilizaciones", headers=cuenta["cabeceras"], json=cuerpo
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def _contenido_firmado(self, cliente, cuenta, campana) -> str:
        preparado = cliente.get(
            "/api/firmas/preparar",
            headers=cuenta["cabeceras"],
            params={"entidad": "cuaderno", "campana_id": campana["id"]},
        )
        assert preparado.status_code == 200, preparado.text
        return preparado.json()["contenido"]

    def test_la_ficha_y_el_abono_quedan_sin_composicion_no_con_cero(
        self, cliente, cuenta, campana, parcela, ficha_sin_composicion
    ):
        """«No se sabe» entra por la puerta como «no se sabe», y no como un 0,0 que afirma.

        ANTES esta prueba se llamaba «…quedan con cero nutrientes» y exigía `(0.0, 0.0, 0.0)` en la
        ficha, en el apunte y en las unidades fertilizantes. Ahora exige `None` en los tres sitios,
        que es lo que de verdad pasa: nadie ha declarado la composición de ese estiércol.
        """
        assert (
            ficha_sin_composicion["riqueza_n"],
            ficha_sin_composicion["riqueza_p"],
            ficha_sin_composicion["riqueza_k"],
        ) == (None, None, None), (
            "la ficha contesta «no lo sé» en los tres nutrientes, no 0,0: el 0,0 afirmaba que ese "
            f"abono no lleva nada ({DOCUMENTO}, A6)"
        )

        abono = self._abonar(cliente, cuenta, campana, parcela, ficha_sin_composicion)
        assert abono["kg_ha_producto"] == self.KILOS_POR_HECTAREA, (
            "el abono se echó y se apuntó: 5.000 kg/ha"
        )
        assert (abono["riqueza_n"], abono["riqueza_p"], abono["riqueza_k"]) == (
            None,
            None,
            None,
        ), "y el apunte guarda la copia de la ficha, que aquí es un hueco"
        assert (abono["uf_n_ha"], abono["uf_p_ha"], abono["uf_k_ha"]) == (None, None, None), (
            "las unidades fertilizantes no se pueden calcular sin la riqueza, así que no se "
            "calculan: antes salían cero y el programa daba por hecho que ese estiércol no aporta "
            f"nitrógeno, fósforo ni potasio ({DOCUMENTO}, A6)"
        )
        assert abono["cantidad_total_kg"] > 0, (
            "lo que sí se sabe —los kilos de producto— se sigue calculando: 5.000 kg/ha por sus "
            "hectáreas"
        )

    def test_ese_hueco_entra_en_el_documento_que_se_firma_como_no_se_sabe(
        self, cliente, cuenta, campana, parcela, ficha_sin_composicion
    ):
        """El documento firmado dice «no se sabe», no «0»: un cero ahí es una afirmación.

        ANTES esta prueba exigía `"Nitrógeno (%): 0"`. Ahora exige la tercera respuesta, la misma
        que ya se escribe para la zona de nitratos que no se ha podido comprobar.
        """
        self._abonar(cliente, cuenta, campana, parcela, ficha_sin_composicion)
        contenido = self._contenido_firmado(cliente, cuenta, campana)

        assert "ABONOS (1)" in contenido, "el abono tiene que estar en el cuaderno que se firma"
        assert "Abono: Estiércol de la nave" in contenido, (
            "los huecos de abajo son los de este abono, el que se apuntó sin composición"
        )
        assert "Kilos por hectárea: 5000" in contenido, (
            "el abono se echó de verdad: 5.000 kg/ha"
        )
        assert "Nitrógeno (%): no se sabe" in contenido, (
            "el texto que se firma no puede decir que ese abono no lleva nitrógeno cuando lo que "
            f"pasa es que nadie lo ha declarado ({DOCUMENTO}, A6)"
        )
        assert "Fósforo (%): no se sabe" in contenido
        assert "Potasio (%): no se sabe" in contenido
        assert "Nitrógeno aportado (kg/ha): no se sabe" in contenido, (
            "y el nutriente aportado tampoco se puede calcular, que es la cifra que mira el plan "
            "de abono del año"
        )
        assert "Nitrógeno (%): 0" not in contenido, (
            "el cero es justo lo que no puede aparecer: se lee como «no aporta nada»"
        )

    def test_una_ficha_con_composicion_se_sigue_escribiendo_igual_que_siempre(
        self, cliente, cuenta, campana, parcela, fertilizante
    ):
        """Lo que sí se sabe no cambia ni una letra: 33,5 % y dos ceros de verdad.

        Es el control del arreglo, y también la razón de que **no** haya que subir
        `VERSION_CANONICA`: los números se escriben exactamente como antes.
        """
        self._abonar(cliente, cuenta, campana, parcela, fertilizante)
        contenido = self._contenido_firmado(cliente, cuenta, campana)
        assert "Nitrógeno (%): 33.5" in contenido
        assert "Fósforo (%): 0" in contenido, (
            "un nitrato amónico lleva 0 % de fósforo: ese cero es un dato, no un hueco, y se "
            "escribe como siempre"
        )
        assert "Potasio (%): 0" in contenido
        assert "Nitrógeno aportado (kg/ha): 1675" in contenido, "5.000 kg/ha al 33,5 % son 1.675"

    def test_los_apuntes_ya_guardados_con_su_cero_se_siguen_firmando_igual(
        self, cliente, cuenta, campana, parcela, db_sesion
    ):
        """**Esto es lo que conserva las firmas ya hechas.**

        Un apunte que el programa guardó antes del arreglo tiene `0.0` y sus `uf_*` a cero, y su
        texto canónico decía «0». Se escribe aquí una fila así, **tal y como la dejó el programa
        viejo**, y se comprueba que el texto que sale hoy es el mismo de entonces. Si cambiara,
        todas las firmas anteriores dejarían de cuadrar y el programa diría que el cuaderno se ha
        tocado, que es lo peor que puede decir.
        """
        db_sesion.add(
            models.RegistroFertilizacion(
                explotacion_id=cuenta["explotacion_id"],
                campana_id=campana["id"],
                fecha=dt.date(2026, 2, 20),
                parcela_id=parcela["id"],
                superficie_ha=2.43,
                fertilizante_nombre="Estiércol de la nave",
                tipo="organico",
                riqueza_n=0.0,
                riqueza_p=0.0,
                riqueza_k=0.0,
                kg_ha_producto=5000.0,
                cantidad_total_kg=12150.0,
                uf_n_ha=0.0,
                uf_p_ha=0.0,
                uf_k_ha=0.0,
                uf_n_total=0.0,
                uf_p_total=0.0,
                uf_k_total=0.0,
                en_zona_vulnerable=None,
            )
        )
        db_sesion.commit()

        contenido = self._contenido_firmado(cliente, cuenta, campana)
        assert "Nitrógeno (%): 0" in contenido, (
            "un cero guardado por el programa de antes se sigue escribiendo «0»: es lo que hace "
            "que la huella de un cuaderno ya firmado siga cuadrando"
        )
        assert "Nitrógeno aportado (kg/ha): 0" in contenido
        # Y ninguno de sus cuatro números se escribe «no se sabe»: el hueco es de las filas nuevas.
        # (El «no se sabe» de «En zona de nitratos» es otra cosa y es correcto: esa fila se escribió
        # con la zona sin comprobar, que es el tercer estado de A2.)
        for linea in ("Nitrógeno (%)", "Fósforo (%)", "Potasio (%)", "Nitrógeno aportado (kg/ha)"):
            assert f"{linea}: no se sabe" not in contenido, linea

    def test_la_version_de_la_forma_canonica_no_ha_subido(self):
        """Si hubiera que subirla, es que se ha cambiado el texto de los cuadernos firmados."""
        assert firma.VERSION_CANONICA == 1

    def test_al_apuntar_un_abono_sin_composicion_el_programa_lo_dice(
        self, cliente, cuenta, campana, parcela, ficha_sin_composicion
    ):
        """Un aviso que no bloquea, y que dice dónde se rellena la composición."""
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "parcela_id": parcela["id"],
                "superficie_ha": parcela["superficie_ha"],
                "fertilizante_id": ficha_sin_composicion["id"],
                "kg_ha_producto": self.KILOS_POR_HECTAREA,
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        avisos = {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}
        assert "F9_composicion_sin_comprobar" in avisos, (
            "sin composición no se puede calcular lo que aporta: callarlo dejaría creer que sí"
        )
        assert avisos["F9_composicion_sin_comprobar"]["bloquea"] is False
        assert "Mis cosas" in avisos["F9_composicion_sin_comprobar"]["mensaje"], (
            "y dice dónde se arregla"
        )
        assert respuesta.json()["puede_guardarse"] is True, (
            "el abono se echó: el cuaderno tiene que poder apuntarlo"
        )

    def test_un_abono_sin_ficha_tampoco_se_puede_calcular(
        self, cliente, cuenta, campana, parcela
    ):
        """El caso del estiércol de la nave apuntado sin ficha en el catálogo, tal cual."""
        abono = self._abonar(cliente, cuenta, campana, parcela, ficha=None)
        assert abono["riqueza_n"] is None
        assert abono["uf_n_ha"] is None
        assert abono["fertilizante_nombre"] is None
        assert abono["kg_ha_producto"] == self.KILOS_POR_HECTAREA

    def test_el_tope_de_nitrogeno_no_se_da_por_bueno_con_una_composicion_desconocida(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """En zona de nitratos, un purín sin composición **no se compara contra 170 como si fuera 0**.

        Antes, `uf_por_hectarea` con una riqueza 0 daba 0 y la comparación salía «no se pasa»: el
        programa daba por bueno el tope. Ahora no se puede comparar, y se dice por qué.
        """
        en_zona = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True)
        purin = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Purín del montón", "tipo": "organico"},
        ).json()
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "parcela_id": en_zona["id"],
                "superficie_ha": en_zona["superficie_ha"],
                "fertilizante_id": purin["id"],
                "kg_ha_producto": 5000.0,
            },
        )
        avisos = {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}
        assert "F9_composicion_sin_comprobar" in avisos
        assert "N1_estiercol_pasa_tope" not in avisos, (
            "no se puede decir que se pasa ni que no se pasa: el aporte no se puede calcular"
        )
        assert respuesta.json()["puede_guardarse"] is True

    def test_lo_que_ya_estaba_apuntado_sin_composicion_tambien_se_dice(
        self, cliente, cuenta, campana, parcela, ficha_sin_composicion, fertilizante
    ):
        """El nitrógeno del año es una parte de lo que se ha echado, y el agricultor lo sabe.

        Se apunta primero un estiércol sin composición y después uno con ella: el segundo aviso
        (`F10`) cuenta el hueco que ya había en la tierra.
        """
        self._abonar(cliente, cuenta, campana, parcela, ficha_sin_composicion)
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-03-01",
                "parcela_id": parcela["id"],
                "superficie_ha": parcela["superficie_ha"],
                "fertilizante_id": fertilizante["id"],
                "kg_ha_producto": 100.0,
            },
        )
        avisos = {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}
        assert "F10_lo_ya_apuntado_sin_composicion" in avisos, (
            "este abono sí tiene composición, pero el de febrero no: el total del año es parcial"
        )
        assert avisos["F10_lo_ya_apuntado_sin_composicion"]["bloquea"] is False
        assert "1 abono" in avisos["F10_lo_ya_apuntado_sin_composicion"]["mensaje"]
        assert "F9_composicion_sin_comprobar" not in avisos, (
            "este abono sí la tiene: no se avisa de lo que no pasa"
        )

    def test_un_apunte_anulado_sin_composicion_no_ensucia_la_cuenta(
        self, cliente, cuenta, campana, parcela, ficha_sin_composicion, fertilizante
    ):
        """Lo que se anuló no se echó, así que tampoco deja el total «a medias»."""
        abono = self._abonar(cliente, cuenta, campana, parcela, ficha_sin_composicion)
        cliente.post(
            f"/api/fertilizaciones/{abono['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Al final no lo eché"},
        )
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-03-01",
                "parcela_id": parcela["id"],
                "superficie_ha": parcela["superficie_ha"],
                "fertilizante_id": fertilizante["id"],
                "kg_ha_producto": 100.0,
            },
        )
        codigos = {aviso["codigo"] for aviso in respuesta.json()["avisos"]}
        assert "F10_lo_ya_apuntado_sin_composicion" not in codigos

    def test_al_corregir_el_abono_con_una_ficha_con_composicion_se_calcula(
        self, cliente, cuenta, campana, parcela, ficha_sin_composicion, fertilizante
    ):
        """Corregir es la salida del agricultor: le dice la composición y el apunte se recalcula."""
        abono = self._abonar(cliente, cuenta, campana, parcela, ficha_sin_composicion)
        assert abono["uf_n_ha"] is None

        corregido = cliente.put(
            f"/api/fertilizaciones/{abono['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "parcela_id": parcela["id"],
                "superficie_ha": parcela["superficie_ha"],
                "fertilizante_id": fertilizante["id"],
                "kg_ha_producto": 1000.0,
                "modo_aplicacion": "al suelo",
                "momento": "fondo",
            },
        )
        assert corregido.status_code == 200, corregido.text
        assert corregido.json()["riqueza_n"] == 33.5
        assert corregido.json()["uf_n_ha"] == 335.0, (
            "1.000 kg/ha de un 33,5 % son 335 kg de nitrógeno por hectárea"
        )

    def test_corregir_la_ficha_no_borra_una_composicion_que_ya_estaba(
        self, cliente, cuenta, fertilizante
    ):
        """Una corrección que no manda la composición **no la borra**.

        Es el mismo cuidado que se tuvo con la autorización del producto (A1): si un `None` de más
        borrara lo que el agricultor ya había copiado del saco, el cuaderno perdería un dato sin
        que nadie lo pidiera. Se mira `model_fields_set`.
        """
        corregido = cliente.put(
            f"/api/fertilizantes/{fertilizante['id']}",
            headers=cuenta["cabeceras"],
            json={"nombre": "Nitrato amónico 33,5% (el del saco nuevo)"},
        )
        assert corregido.status_code == 200, corregido.text
        assert corregido.json()["nombre"] == "Nitrato amónico 33,5% (el del saco nuevo)"
        assert corregido.json()["riqueza_n"] == 33.5, (
            "cambiar el nombre no puede borrar la composición: no se pidió"
        )
        assert corregido.json()["riqueza_p"] == 0.0
        assert corregido.json()["riqueza_k"] == 0.0

    def test_el_volcado_a_la_junta_deja_la_riqueza_en_blanco_y_lo_declara(
        self, cliente, cuenta, campana, parcela, ficha_sin_composicion
    ):
        """En la hoja 6, una casilla que nadie ha declarado sale **en blanco**, y se dice que falta.

        Es la regla que el propio volcado ya sigue en todo lo demás: «lo que no esté puesto sale en
        blanco, no con un cero ni con un dato inventado».
        """
        self._abonar(cliente, cuenta, campana, parcela, ficha_sin_composicion)
        fichero = cliente.get("/api/cuaderno-cyl/exportar", headers=cuenta["cabeceras"])
        assert fichero.status_code == 200, fichero.text
        libro = load_workbook(io.BytesIO(fichero.content))
        hoja = libro["6. REG. FERTILIZ"]
        assert hoja["H11"].value in (None, ""), (
            "escribir «0/0/0» sería rellenar con ceros lo que nadie ha declarado"
        )
        assert hoja["D11"].value == "Estiércol de la nave", "el abono sí está, con su nombre"
        assert str(hoja["I11"].value) == "5000", (
            "y con sus kilos por hectárea, que sí se saben"
        )
        faltantes = cliente.get(
            "/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]
        ).json()
        texto = json.dumps(faltantes, ensure_ascii=False)
        assert "composición" in texto, (
            "y lo que falta se nombra: un hueco sin decir de qué es un hueco que nadie rellena"
        )


# --------------------------------------------------------------------------
# A7 — una superficie que no se sabe es un dato pendiente, no 0 hectáreas
# --------------------------------------------------------------------------


class TestA7UnaSuperficieQueNoSeSabeYaNoEsCeroHectareas:
    """A7 — «Una superficie que no se sabe se convierte en 0 hectáreas, y la tierra deja de poder
    tratarse» (`docs/T02_VALORES_POR_DEFECTO.md`, A7).

    **EL DEFECTO QUE REPRODUCÍA ESTA CLASE.** Al importar el cuaderno de la Junta, la superficie que
    se cultiva se guardaba con `linea.superficie_cultivada_ha or 0.0`: si el papel traía la casilla
    en blanco —y la trae en blanco en varias tierras, porque es la plantilla de la Junta la que la
    deja vacía—, la tierra quedaba dada de alta con **0,00 ha**, que no es «no lo sé» sino «es
    cero». Y eso no era un número feo en una lista: con `superficie_ha == 0`, cualquier tratamiento
    de más de 0,0001 ha **bloqueaba** con `V4_superficie_excedida`, así que la tierra existía, se
    veía en la lista y era inutilizable. Justo debajo, en el mismo objeto, la superficie del recinto
    entero (`superficie_sigpac_ha`) **sí** se quedaba en blanco: dos criterios distintos para el
    mismo caso.

    **LO QUE EXIGE AHORA, Y POR QUÉ ES LO BUENO.** La superficie que no se sabe es **un dato
    pendiente**, nunca un cero: la tierra se puede tratar y abonar —el cuaderno tiene que recoger lo
    que ha pasado en el campo— y sale un aviso que dice **que falta la superficie y dónde se
    arregla**, que es la regla de `AGENTS.md` §5 («no dejes al agricultor sin salida»). **Nunca se
    copia sola otra superficie distinta**: la del recinto del SIGPAC es otra magnitud a propósito, y
    por eso lo único que se hace con ella es **proponerla** en el aviso para que el agricultor
    decida. Y los totales (el de la finca, el de un grupo) dicen que están incompletos en vez de
    sumar el hueco como cero.
    """

    def _importar_el_cuaderno_sin_superficie(self, cliente, cuenta) -> list[dict]:
        """Trae el cuaderno de la Junta con la primera línea sin superficie cultivada."""
        respuesta = cliente.post(
            "/api/cuaderno-cyl/importar",
            headers=cuenta["cabeceras"],
            files={
                "fichero": (
                    "CuadernoExplotacion_12345678Z.xlsx",
                    _cuaderno_sin_la_superficie_cultivada(),
                )
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        return cliente.get("/api/parcelas", headers=cuenta["cabeceras"]).json()

    def _la_tierra_sin_superficie(self, parcelas: list[dict]) -> dict:
        return next(
            parcela
            for parcela in parcelas
            if parcela["ref_sigpac"] == REFERENCIA_DE_LA_PRIMERA_LINEA
        )

    def test_la_tierra_importada_sin_superficie_cultivada_se_queda_sin_superficie(
        self, cliente, cuenta
    ):
        """En blanco en el papel es «no lo sé» en el cuaderno del agricultor, no 0,00 ha.

        ANTES esta prueba se llamaba «…queda con cero hectáreas» y exigía `superficie_ha == 0.0`.
        Ahora exige `None`, que es el tercer estado.
        """
        parcelas = self._importar_el_cuaderno_sin_superficie(cliente, cuenta)
        tierra = self._la_tierra_sin_superficie(parcelas)

        assert tierra["superficie_ha"] is None, (
            "el papel no decía la superficie cultivada, y 0,0 no significa «no lo sé» sino «es "
            f"cero»: la tierra quedaba inutilizable ({DOCUMENTO}, A7)"
        )
        assert tierra["superficie_sigpac_ha"] == 1.09, (
            "y la superficie del recinto entero sigue ahí, aparte: son dos magnitudes distintas y "
            "no se copian la una en la otra"
        )

        # Y las demás líneas del cuaderno sí traen su superficie: lo que falta es la de una,
        # no la columna entera. Sin esto, la prueba pasaría también si el lector no leyera nada.
        vecina = next(
            parcela for parcela in parcelas if parcela["ref_sigpac"] == "99-99-0-0-2-10-1"
        )
        assert vecina["superficie_ha"] == 2.0, (
            "la casilla que se ha dejado en blanco es una: las demás tierras del cuaderno "
            "conservan sus hectáreas"
        )

    def test_la_superficie_del_sigpac_no_se_copia_sola_en_la_cultivada(self, cliente, cuenta):
        """Proponer no es escribir: al importar, la cultivada se queda en blanco aunque haya SIGPAC.

        Es la decisión que pide el propio documento: «**No copiar.** Marcar la tierra como
        “superficie pendiente de comprobar” y dar la pantalla que la pida. Copiar el SIGPAC a la
        cultivada sería inventar».
        """
        parcelas = self._importar_el_cuaderno_sin_superficie(cliente, cuenta)
        tierra = self._la_tierra_sin_superficie(parcelas)
        assert tierra["superficie_ha"] is None, (
            "el recinto mide 1,09 ha y la superficie cultivada puede ser otra: se propone, no se "
            "escribe"
        )

    def test_esa_tierra_se_puede_tratar_y_el_aviso_dice_donde_se_arregla(
        self, cliente, cuenta, campana, producto
    ):
        """La tierra existe, se ve en la lista y **se puede tratar**: el apunte se guarda con aviso.

        ANTES esta prueba se llamaba «…el tratamiento siguiente se bloquea» y esperaba un 422 con
        `V4_superficie_excedida` bloqueando. Ahora espera un 201 con el aviso `V26` (la superficie
        del SIGPAC se propone) y **sin** `V4`: lo que no se puede comprobar no se puede dar por
        malo.
        """
        parcelas = self._importar_el_cuaderno_sin_superficie(cliente, cuenta)
        tierra = self._la_tierra_sin_superficie(parcelas)

        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": tierra["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert respuesta.status_code == 201, (
            "la tierra tiene la superficie pendiente, pero lo que ha pasado en el campo se "
            f"apunta: antes no dejaba guardarlo ({DOCUMENTO}, A7). {respuesta.text}"
        )

        # La comprobación previa es la que enseña el aviso, que es la que mira la pantalla.
        comprobacion = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": tierra["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert comprobacion.status_code == 200, comprobacion.text
        avisos = {aviso["codigo"]: aviso for aviso in comprobacion.json()["avisos"]}
        assert comprobacion.json()["puede_guardarse"] is True
        assert "V4_superficie_excedida" not in avisos, (
            "no se puede decir que se pasa de una superficie que no se conoce"
        )
        assert "V26_tierra_sin_superficie_con_la_del_sigpac" in avisos, (
            "y hay que decirlo con el aviso del tercer estado"
        )
        assert avisos["V26_tierra_sin_superficie_con_la_del_sigpac"]["bloquea"] is False
        mensaje = avisos["V26_tierra_sin_superficie_con_la_del_sigpac"]["mensaje"]
        assert "1,09" in mensaje, (
            "se le propone la superficie del recinto del SIGPAC para que él decida: proponer no es "
            "escribir"
        )
        assert "Mis cosas" in mensaje, (
            "y se le dice dónde se arregla, que es lo que exige `AGENTS.md` §5"
        )

    def test_sin_sigpac_el_aviso_lo_dice_sin_proponer_ninguna_cifra(
        self, cliente, cuenta, campana, crear_parcela, producto
    ):
        """Una tierra que ya era suya, sin superficie y sin recinto del SIGPAC: se dice y punto."""
        tierra = crear_parcela(alias="La del rincón", superficie_ha=None, ref_sigpac=None)
        assert tierra["superficie_sigpac_ha"] is None

        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": tierra["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        avisos = {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}
        assert "V25_tierra_sin_superficie" in avisos, (
            "sin ninguna superficie que proponer, el aviso sigue saliendo: lo que no vale es callar"
        )
        assert "V26_tierra_sin_superficie_con_la_del_sigpac" not in avisos
        assert respuesta.json()["puede_guardarse"] is True

    def test_un_abono_en_esa_tierra_tampoco_se_bloquea(self, cliente, cuenta, campana, fertilizante):
        """Lo mismo al abonar: `F2_superficie_excedida` no puede saltar contra un cero que no existe."""
        parcelas = self._importar_el_cuaderno_sin_superficie(cliente, cuenta)
        tierra = self._la_tierra_sin_superficie(parcelas)

        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "parcela_id": tierra["id"],
                "superficie_ha": 1.0,
                "fertilizante_id": fertilizante["id"],
                "kg_ha_producto": 300.0,
            },
        )
        assert respuesta.status_code == 201, (
            f"la tierra se tiene que poder abonar con la superficie pendiente: {respuesta.text}"
        )
        assert respuesta.json()["superficie_ha"] == 1.0

    def test_al_corregir_la_tierra_con_su_superficie_la_comprobacion_vuelve(
        self, cliente, cuenta, campana, producto
    ):
        """El agricultor arregla el dato y el programa vuelve a comprobar de verdad.

        Es el final del camino completo: se avisa, se da la salida, el agricultor la usa y a partir
        de ahí la comprobación de superficie otra vez manda. Sin esto, el aviso sería un cartel.
        """
        parcelas = self._importar_el_cuaderno_sin_superficie(cliente, cuenta)
        tierra = self._la_tierra_sin_superficie(parcelas)

        corregida = cliente.put(
            f"/api/parcelas/{tierra['id']}",
            headers=cuenta["cabeceras"],
            json={"alias": tierra["alias"], "superficie_ha": 1.09},
        )
        assert corregida.status_code == 200, corregida.text
        assert corregida.json()["superficie_ha"] == 1.09

        comprobacion = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": tierra["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        avisos = {aviso["codigo"]: aviso for aviso in comprobacion.json()["avisos"]}
        assert "V25_tierra_sin_superficie" not in avisos
        assert "V26_tierra_sin_superficie_con_la_del_sigpac" not in avisos
        assert comprobacion.json()["puede_guardarse"] is True

        # Y si ahora se pasa de verdad, sí bloquea: la comprobación no se ha apagado.
        excedida = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": tierra["id"],
                "superficie_tratada_ha": 5.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        avisos = {aviso["codigo"]: aviso for aviso in excedida.json()["avisos"]}
        assert avisos["V4_superficie_excedida"]["bloquea"] is True

    def test_el_total_de_un_grupo_no_suma_las_tierras_que_no_lo_traen(
        self, cliente, cuenta, crear_parcela
    ):
        """Una suma a la que le falta un número no es una suma: el total sale pendiente.

        Y se dice **cuántas** tierras no lo traen, para que la pantalla pueda explicarlo en vez de
        enseñar un hueco sin motivo.
        """
        con_superficie = crear_parcela(alias="El Prado")
        sin_superficie = crear_parcela(alias="La Vega", superficie_ha=None)
        cliente.post(
            "/api/grupos",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "Los trigos",
                "parcela_ids": [con_superficie["id"], sin_superficie["id"]],
            },
        )
        grupo = cliente.get("/api/grupos", headers=cuenta["cabeceras"]).json()[0]
        assert grupo["superficie_total_ha"] is None, (
            "devolver 2,43 daría un total que parece bueno y no lo es: es la superficie de una "
            "tierra, no la del grupo"
        )
        assert grupo["tierras_sin_superficie"] == 1

    def test_un_tratamiento_del_grupo_avisa_de_la_tierra_que_no_trae_superficie(
        self, cliente, cuenta, campana, crear_parcela, producto
    ):
        """El grupo tampoco se da por bueno: se dice que no se ha podido comprobar."""
        con_superficie = crear_parcela(alias="El Prado")
        sin_superficie = crear_parcela(alias="La Vega", superficie_ha=None)
        grupo = cliente.post(
            "/api/grupos",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "Los trigos",
                "parcela_ids": [con_superficie["id"], sin_superficie["id"]],
            },
        ).json()
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "grupo_id": grupo["id"],
                "superficie_tratada_ha": 2.43,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        avisos = {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}
        assert "V25_tierra_sin_superficie" in avisos
        assert "alguna tierra de este grupo" in avisos["V25_tierra_sin_superficie"]["mensaje"], (
            "el aviso tiene que decir de qué tierra habla: de una del grupo, no de «esta tierra»"
        )
        assert "V4_superficie_excedida_grupo" not in avisos

    def test_una_tierra_del_sigpac_sin_superficie_tampoco_se_queda_en_cero(
        self, cliente, cuenta, monkeypatch
    ):
        """El otro camino de alta: traer el recinto del SIGPAC cuando el servicio no manda la superficie.

        El SIGPAC puede no mandarla (`sigpac.py`: `superficie: float | None = None`), y antes esa
        línea era `recinto.superficie or 0.0`: la misma trampa que en el cuaderno de la Junta.
        """
        import httpx

        ruta = (
            pathlib.Path(__file__).resolve().parents[2]
            / "data"
            / "sigpac"
            / "recinto_de_ejemplo.json"
        )
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
        assert crudo[0]["superficie"] > 0, "la prueba necesita el ejemplo de verdad"
        # Se le quita la superficie, que es lo que hace el servicio cuando no la tiene.
        del crudo[0]["superficie"]

        class RespuestaFalsa:
            status_code = 200
            text = json.dumps(crudo)

            def raise_for_status(self):
                return None

        monkeypatch.setattr(httpx, "get", lambda url, **kwargs: RespuestaFalsa())

        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1", "alias": "El Prado"},
        )
        assert respuesta.status_code == 201, respuesta.text
        parcela = respuesta.json()
        assert parcela["superficie_ha"] is None, (
            "sin superficie que traer, la tierra se queda con la superficie pendiente, no con un "
            "cero que la deja sin poder tratarse"
        )
        assert parcela["superficie_oficial"] is False, (
            "y no se puede decir que la superficie es la oficial cuando no hay ninguna"
        )

    def test_una_tierra_normal_del_sigpac_sigue_trayendo_su_superficie(self, cliente, cuenta, monkeypatch):
        """El control: cuando el SIGPAC sí la manda, todo sigue como estaba."""
        import httpx

        ruta = (
            pathlib.Path(__file__).resolve().parents[2]
            / "data"
            / "sigpac"
            / "recinto_de_ejemplo.json"
        )
        crudo = json.loads(ruta.read_text(encoding="utf-8"))

        class RespuestaFalsa:
            status_code = 200
            text = json.dumps(crudo)

            def raise_for_status(self):
                return None

        monkeypatch.setattr(httpx, "get", lambda url, **kwargs: RespuestaFalsa())

        parcela = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1", "alias": "El Prado"},
        ).json()
        assert parcela["superficie_ha"] == crudo[0]["superficie"]
        assert parcela["superficie_oficial"] is True

    def test_la_regla_pura_no_dice_que_se_pasa_cuando_no_se_sabe_la_superficie(self):
        """`legal.supera_superficie` es cálculo puro: sin superficie no hay comparación posible.

        Se prueba aquí, sin servidor ni base de datos, porque es donde vive la decisión: si esto
        devolviera `True`, cualquier apunte bloquearía y volveríamos al defecto de A7.
        """
        assert legal.supera_superficie(5.0, None) is False, (
            "no se puede afirmar que se pasa de una superficie que no se conoce"
        )
        assert legal.supera_superficie(5.0, 2.43) is True, "el caso normal sigue igual"
        assert legal.supera_superficie(2.43, 2.43) is False

    def test_el_resumen_del_cuaderno_dice_cuantas_tierras_no_traen_superficie(self, cliente, cuenta):
        """El total de hectáreas no se inventa el hueco, y se cuenta aparte."""
        parcelas = self._importar_el_cuaderno_sin_superficie(cliente, cuenta)
        resumen = cliente.get("/api/cuaderno/resumen", headers=cuenta["cabeceras"]).json()
        assert resumen["tierras_sin_superficie"] == 1, (
            "hay que decir cuántas tierras no traen su superficie: si no, el total parece completo"
        )
        assert resumen["superficie_total_ha"] == round(
            sum(
                parcela["superficie_ha"]
                for parcela in parcelas
                if parcela["superficie_ha"] is not None
            ),
            2,
        ), "el total suma lo que se sabe, y no cuenta el hueco como cero"


# --------------------------------------------------------------------------
# A10 y A11 — el sistema de una tierra y de quién es una máquina no se inventan
# --------------------------------------------------------------------------


class TestA10UnSistemaQueNoSeSabeYaNoEsSecano:
    """A10 — «`sistema = "secano"` por defecto: lo que no se sabe se declara de secano»
    (`docs/T02_VALORES_POR_DEFECTO.md`, A10).

    **EL DEFECTO.** La columna nacía con `"secano"` por defecto, en la tierra, en el cultivo de la
    campaña y en el grupo, y el formulario ofrecía solo dos botones —secano y regadío— con el secano
    ya marcado. Así que una tierra de regadío cuyo dueño no tocaba el botón **quedaba declarada de
    secano** sin que nadie lo hubiera dicho, y eso no se quedaba en una lista: el sistema decide
    **contra qué columna del anexo III de la Orden MAV/398/2022 se compara el abonado**
    (`validaciones.py`), y la casilla «Secano/Regadío» de la hoja 2.1 del cuaderno de la Junta se
    escribía con una **«S»** (`cuaderno_cyl_exportar.py`), que es un papel que se firma.

    **LO QUE EXIGE AHORA.** `None` es «no lo sé», en los cuatro sitios donde el sistema se guarda
    —tierra, cultivo de la campaña, grupo y el que se trae del SIGPAC o del cuaderno de la Junta—, y
    con él:
      · la hoja 2.1 deja la casilla **en blanco** y el informe de lo que falta dice que falta ese
        dato (lo que no se sabe no se escribe, pero tampoco se calla);
      · la comparación con el anexo III **no se hace**, en vez de hacerse contra la columna que no es;
      · y quien lee el cuaderno entiende el hueco, porque `cuaderno_cyl._lee_sistema` ya decía «en
        blanco se queda en blanco».
    """

    def test_una_tierra_apuntada_sin_decir_el_sistema_se_queda_sin_sistema(self, cliente, cuenta):
        """Las dos formas de no decirlo —sin el campo y con el campo en blanco— dan «no lo sé».

        **Las dos, y a propósito**: un formulario que no pregunta el sistema no manda el campo, y uno
        que lo pregunta con la opción «no lo sé» manda un `null`. Si el defecto volviera por
        cualquiera de los dos lados —el valor por defecto del esquema o el del modelo—, esta prueba
        lo caza.
        """
        for cuerpo in (
            {"alias": "Sin el campo", "superficie_ha": 2.43},
            {"alias": "Con el campo vacío", "superficie_ha": 2.43, "sistema": None},
        ):
            respuesta = cliente.post("/api/parcelas", headers=cuenta["cabeceras"], json=cuerpo)
            assert respuesta.status_code == 201, respuesta.text
            assert respuesta.json()["sistema"] is None, (
                f"«{cuerpo['alias']}» salía de secano sin que nadie lo hubiera dicho: el abonado se "
                f"comparaba contra el límite que no es ({DOCUMENTO}, A10)"
            )

        # El control: cuando sí se dice, se guarda lo que se dice, y lo que no existe se rechaza.
        dice = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={"alias": "La de regadío", "superficie_ha": 2.43, "sistema": "regadio"},
        )
        assert dice.status_code == 201, dice.text
        assert dice.json()["sistema"] == "regadio"

        inventado = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={"alias": "La del invernadero", "superficie_ha": 2.43, "sistema": "invernadero"},
        )
        assert inventado.status_code == 422, (
            "«no lo sé» se admite, pero un sistema que no existe se sigue rechazando con la lista "
            "delante: lo que se ha abierto es el tercer estado, no la puerta a cualquier cosa"
        )

    def test_una_tierra_traida_del_sigpac_no_queda_de_secano_por_no_tocarlo(
        self, cliente, cuenta, monkeypatch
    ):
        """El caso que describe el documento: la tierra se trae del mapa y no se toca el sistema.

        El SIGPAC **no trae** el sistema de explotación: lo dice el agricultor. Y lo que no dice se
        queda en «no lo sé», no en el valor que más le conviene al programa.
        """
        import json
        import pathlib

        import httpx

        ruta = (
            pathlib.Path(__file__).resolve().parents[2]
            / "data"
            / "sigpac"
            / "recinto_de_ejemplo.json"
        )
        crudo = json.loads(ruta.read_text(encoding="utf-8"))

        class RespuestaFalsa:
            status_code = 200
            text = json.dumps(crudo)

            def raise_for_status(self):
                return None

        monkeypatch.setattr(httpx, "get", lambda url, **kwargs: RespuestaFalsa())

        # Sin decir el sistema: es lo que manda la pantalla del mapa cuando el agricultor no toca
        # ninguno de los botones (antes mandaba «secano» porque venía marcado).
        respuesta = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1", "alias": "El Prado"},
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["sistema"] is None, (
            "la tierra traída del mapa salía de secano sin que nadie lo hubiera dicho"
        )

        # Y el control: cuando sí se dice, se guarda lo que se dice. Sin esto, la prueba pasaría
        # también si el endpoint ignorara el sistema.
        regadio = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={
                "ref_sigpac": "37-22-0-0-501-427-2",
                "alias": "La Vega",
                "sistema": "regadio",
            },
        )
        assert regadio.status_code == 201, regadio.text
        assert regadio.json()["sistema"] == "regadio"

    def test_el_cultivo_declarado_sin_sistema_se_queda_sin_sistema(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """El cultivo de la campaña también: la columna `parcela_cultivos.sistema` nacía en «secano»."""
        tierra = crear_parcela(alias="La del regadío", sistema=None)
        respuesta = cliente.post(
            f"/api/parcelas/{tierra['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "especie": "Maíz",
                "superficie_cultivada_ha": 2.0,
            },
        )
        assert respuesta.status_code in (200, 201), respuesta.text
        cultivos = cliente.get(
            f"/api/parcelas/{tierra['id']}/cultivos", headers=cuenta["cabeceras"]
        ).json()
        assert cultivos[0]["sistema"] is None, (
            "el cultivo de la campaña quedaba de secano sin que nadie lo hubiera declarado"
        )

    def test_la_casilla_del_cuaderno_de_la_junta_sale_en_blanco_y_se_dice_por_que(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """La hoja 2.1: «S», «R» o **en blanco**, y el informe dice que falta ese dato.

        Aquí está la parte que se firma. Escribir «S» de una tierra que puede ser de regadío es
        declarar ante la Junta algo que el agricultor no ha dicho; dejarlo en blanco es lo que el
        propio lector del cuaderno entiende por «no lo han declarado».
        """
        import io

        from openpyxl import load_workbook

        crear_parcela(alias="La del regadío", sistema=None)
        libro = load_workbook(
            io.BytesIO(
                cliente.get("/api/cuaderno-cyl/exportar", headers=cuenta["cabeceras"]).content
            )
        )
        hoja = libro["2.1. DATOS PARCELAS"]
        assert hoja["O14"].value in (None, ""), (
            "la casilla «Secano/Regadío» se ha escrito sin saberlo: en el fichero de la Junta salía "
            f"una «S» de una tierra que puede ser de regadío ({DOCUMENTO}, A10)"
        )

        # Y no se calla: el informe de lo que falta pide el dato, con sus palabras.
        que_falta = " ".join(
            falta["que_falta"]
            for falta in cliente.get(
                "/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]
            ).json()["faltan"]
        )
        assert "si esa tierra es de secano o de regadío" in que_falta, (
            "el cuaderno sale con un hueco y el agricultor no se entera hasta que lo manda"
        )

    def test_con_el_sistema_declarado_la_casilla_se_sigue_escribiendo_igual(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """El control: secano es «S» y regadío es «R», como siempre."""
        import io

        from openpyxl import load_workbook

        crear_parcela(alias="La secana", sistema="secano")
        hoja = load_workbook(
            io.BytesIO(
                cliente.get("/api/cuaderno-cyl/exportar", headers=cuenta["cabeceras"]).content
            )
        )["2.1. DATOS PARCELAS"]
        assert hoja["O14"].value == "S"

        crear_parcela(
            alias="La de regadío", sistema="regadio", ref_sigpac="37-455-12-9", poligono=2
        )
        libro = load_workbook(
            io.BytesIO(
                cliente.get("/api/cuaderno-cyl/exportar", headers=cuenta["cabeceras"]).content
            )
        )
        hoja = libro["2.1. DATOS PARCELAS"]
        # Las tierras salen ordenadas por polígono, parcela y recinto: la de regadío es la segunda.
        assert hoja["O14"].value == "S"
        assert hoja["O15"].value == "R", "regadío sigue siendo «R»"

    def test_la_regla_pura_no_compara_el_abono_cuando_no_se_sabe_el_sistema(self):
        """El porqué de todo esto, en la función que decide: sin sistema no hay columna que aplicar.

        `nitratos_cyl.aporte_de` devuelve `None` cuando el sistema no es ni secano ni regadío, así que
        **no se compara contra ninguna de las dos columnas del anexo III**. Antes, con «secano» puesto
        por defecto, la comparación se hacía contra la columna del secano sin que nadie hubiera dicho
        que esa tierra lo fuera.
        """
        from app import nitratos_cyl

        assert nitratos_cyl.aporte_de("Cebada", None) is None, (
            "sin saber el sistema no se puede decir cuál es el aporte máximo que le toca"
        )
        assert nitratos_cyl.aporte_de("Cebada", "") is None
        # Los dos casos conocidos siguen igual: la cebada tiene su fila en el anexo III y sus dos
        # columnas, la del secano (105 kg) y la de regadío (135 kg).
        assert nitratos_cyl.aporte_de("Cebada", "secano")["maximo_kg_n_ha"] == 105.0
        assert nitratos_cyl.aporte_de("Cebada", "regadio")["maximo_kg_n_ha"] == 135.0


class TestA11UnaMaquinaSinDuenoConocidoYaNoEsTuya:
    """A11 — «`titularidad = "propia"` por defecto: la máquina de otro queda como tuya»
    (`docs/T02_VALORES_POR_DEFECTO.md`, A11).

    **EL DEFECTO.** El campo nacía en `"propia"`, así que dar de alta el pulverizador de la empresa
    de servicios —el caso que el propio código describe: las tres pestañas de la app oficial son
    «maquinaria propia», «maquinaria ajena» y «equipos NO ROMA»— lo dejaba en la lista de las
    máquinas propias, en la hoja 1.3 del cuaderno, y con su ITEAF como si la obligación de
    inspeccionarla fuera del agricultor.

    **LO QUE EXIGE AHORA.** `None` es «no consta de quién es». De quién es una máquina **no se deduce
    de ningún dato** (`docs/T02`, tabla de evidencias: «No se puede rellenar. Preguntar»), así que:
      · el equipo se guarda con la titularidad sin decir, y la pantalla ofrece «no lo sé»;
      · la ficha de la maquinaria se queda en «no se sabe» en vez de en «es tuya» — eso ya lo hacía
        `maquinaria.py`, y ahora el dato que le llega tampoco miente—;
      · y la hoja 1.3, que es **la de los equipos propios**, pregunta de quién es en vez de pedirle a
        ciegas el nº de ROMA y la fecha de la inspección.
    """

    def test_una_maquina_sin_decir_de_quien_es_no_queda_como_tuya(self, cliente, cuenta):
        """El alta: lo que no se dice se queda sin decir, y el informe lo pregunta."""
        equipo = cliente.post(
            "/api/equipos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Pulverizador de la empresa", "tipo": "Atomizador"},
        ).json()
        assert equipo["titularidad"] is None, (
            "la máquina de la empresa de servicios quedaba como propia sin que nadie lo hubiera "
            f"dicho, y en el cuaderno no se apunta igual una propia que una ajena ({DOCUMENTO}, A11)"
        )

        que_falta = " ".join(
            falta["que_falta"]
            for falta in cliente.get(
                "/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]
            ).json()["faltan"]
        )
        assert "si esa máquina es tuya, es de otro o no va inscrita en el ROMA" in que_falta, (
            "la hoja 1.3 es la de los equipos propios y no se pregunta de quién es la máquina"
        )
        assert "el nº de inscripción en el ROMA" not in que_falta, (
            "no se le puede pedir el ROMA a una máquina que puede no ir inscrita: primero se "
            "pregunta de quién es, y con la respuesta se pide lo que toque"
        )

    def test_con_la_titularidad_dicha_si_se_le_pide_lo_que_le_toca(self, cliente, cuenta):
        """El control, y es el que demuestra que lo de arriba no es «no preguntar nunca».

        Con la máquina dicha como propia, el informe pide su nº de ROMA y su última inspección; y con
        una mochila (un equipo NO ROMA) no pide ninguna de las dos cosas, porque no existen. Es la
        diferencia entre las tres pestañas de la app oficial, que ya estaba y sigue igual.
        """
        cliente.post(
            "/api/equipos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Pulverizador", "titularidad": "propia"},
        )
        que_falta = " ".join(
            falta["que_falta"]
            for falta in cliente.get(
                "/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]
            ).json()["faltan"]
        )
        assert "el nº de inscripción en el ROMA" in que_falta
        assert "la fecha de la última inspección" in que_falta

        cliente.post(
            "/api/equipos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Mochila de la espalda", "titularidad": "no_roma"},
        )
        # La mochila no cambia lo que se le pide al pulverizador: se mira solo su línea.
        que_falta = " ".join(
            falta["que_falta"]
            for falta in cliente.get(
                "/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]
            ).json()["faltan"]
        )
        assert "de la máquina «Mochila de la espalda»" not in que_falta, (
            "a una mochila no se le pide el ROMA ni la ITEAF: no se inscribe ni se inspecciona"
        )

    def test_la_ficha_de_la_maquinaria_no_se_inventa_de_quien_es(self, cliente, cuenta, monkeypatch):
        """Lo que ya hacía bien `maquinaria.py`, ahora con el dato bueno delante.

        `POST /api/maquinaria/desde-equipo/<id>` **no copia la titularidad como propiedad** salvo
        cuando dice «propia»: con el equipo sin decir, la ficha queda en «no lo sé». Antes esta rama
        no se podía recorrer por el camino normal —el equipo nunca llegaba sin titularidad, porque el
        modelo la ponía—, así que la prueba se hace aquí, con el alta de verdad.
        """
        equipo = cliente.post(
            "/api/equipos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Atomizador de alquiler", "tipo": "Atomizador"},
        ).json()
        traida = cliente.post(
            f"/api/maquinaria/desde-equipo/{equipo['id']}", headers=cuenta["cabeceras"]
        )
        assert traida.status_code == 201, traida.text
        assert traida.json()["propiedad"] == "no_se", (
            "la ficha de la maquinaria decía «es tuya» de una máquina que puede ser de otro"
        )
