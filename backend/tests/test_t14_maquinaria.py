"""Pruebas del T14 (E8): la maquinaria y sus inspecciones, separadas y con su fuente.

QUÉ SE PRUEBA AQUÍ, Y POR QUÉ CADA COSA

El ticket tiene una trampa y una puerta de calidad, y las dos se comprueban aquí antes que nada:

  1. **No se calcula ningún plazo por el nombre ni por la clase de la máquina.** El contrato lo dice
     literal: «No calcular plazo solo por "tractor" o "sulfatadora"; pedir la clasificación técnica
     necesaria». Las pruebas de `TestNoSeInventaNingunaFecha` lo demuestran por varios caminos: dos
     máquinas idénticas con nombres distintos dan exactamente los mismos estados y los mismos avisos; una
     máquina que aplica una obligación y no tiene inspección **no enseña ninguna fecha** y pide la
     clasificación; y la fecha que se enseña en «próxima revisión» es **la que se apuntó**, ni un día más.
  2. **`EquipoAplicacion` no es «la maquinaria».** `TestElEquipoDeEcharProductoNoEsLaMaquinaria` da de
     alta un tractor y un remolque sin número de ROMA y sin ITEAF, y comprueba que el programa **no se
     los pide**; y comprueba que los equipos del cuaderno que ya existían **no desaparecen**, sino que se
     traen a la lista sin copiar nada que no se sepa.

Y después, las tres cosas que el contrato pide de una ficha de maquinaria: las **cinco obligaciones
separadas** (ITV, ITEAF, mantenimiento, seguro y ROMA), cada una con aplicabilidad, fuente, última
inspección, resultado, próxima fecha y documento; los **avisos al planificar un trabajo**; y el
**registro de averías**. Más el aislamiento entre fincas, la corrección, la anulación y el reenvío sin
duplicar, que son reglas de la casa.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app import maquinaria, models, textos
from app.routers import maquinaria_api

HOY = dt.date.today()


def _dias(dias: int) -> str:
    return (HOY + dt.timedelta(days=dias)).isoformat()


# --------------------------------------------------------------------------
# Ayudas
# --------------------------------------------------------------------------


def crear_maquina(cliente, cabeceras, **cambios):
    """Da de alta una máquina con los tres campos que el esquema exige, y devuelve lo que contesta."""
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


def la_ficha(cliente, cabeceras, maquina_id):
    respuesta = cliente.get(f"/api/maquinaria/{maquina_id}", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def sus_obligaciones(ficha) -> dict:
    return {una["tipo"]: una for una in ficha["obligaciones"]}


def declarar(cliente, cabeceras, maquina_id, tipo, aplicabilidad="si", origen="documento", **cambios):
    datos = {"aplicabilidad": aplicabilidad, "origen": origen, **cambios}
    respuesta = cliente.put(
        f"/api/maquinaria/{maquina_id}/obligaciones/{tipo}", headers=cabeceras, json=datos
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def apuntar_inspeccion(cliente, cabeceras, maquina_id, **cambios):
    datos = {"tipo": "iteaf", "fecha": "2024-03-01", "resultado": "favorable"}
    datos.update(cambios)
    respuesta = cliente.post(
        f"/api/maquinaria/{maquina_id}/inspecciones", headers=cabeceras, json=datos
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def apuntar_averia(cliente, cabeceras, maquina_id, **cambios):
    datos = {"fecha": "2026-04-01", "que_paso": "Se rompió el eje del ventilador", "resuelta": False}
    datos.update(cambios)
    respuesta = cliente.post(f"/api/maquinaria/{maquina_id}/averias", headers=cabeceras, json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def crear_papel(cliente, cabeceras, titulo="Certificado de la ITEAF"):
    """Un papel de «los papeles», que es donde se guarda el certificado de una inspección.

    **Se apunta como «otros» porque no hay un tipo de papel para un certificado de inspección**: el
    catálogo de tipos (`catalogos.TIPOS_DOCUMENTO`) tiene contrato, factura, albarán de Sigfito y otros,
    y el contrato del CRM pide «inspección» entre los tipos de la bandeja documental (S10, que es del
    T08). Queda apuntado en el informe del ticket: el enlace funciona con cualquier papel, pero el día
    que exista ese tipo, este certificado irá al suyo.
    """
    respuesta = cliente.post(
        "/api/documentos",
        headers=cabeceras,
        json={"titulo": titulo, "tipo": "otros", "fecha": "2024-03-01"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --------------------------------------------------------------------------
# 1. La trampa del ticket: no se inventa ninguna fecha ni ninguna obligación
# --------------------------------------------------------------------------


class TestNoSeInventaNingunaFecha:
    """El corazón del ticket: el programa no deduce qué le toca a una máquina por cómo se llama."""

    def test_una_maquina_nueva_no_tiene_ninguna_obligacion_dada_por_buena(self, cliente, cuenta):
        """**Aquí está el valor por defecto que este ticket no podía repetir.**

        Una máquina recién apuntada no tiene ninguna obligación declarada, y la ficha enseña las cinco
        en «no se sabe». Un valor de partida que dijera «no le hace falta» —o «no necesita inspección»—
        convertiría «no lo sé» en «cumple», que es exactamente lo que el contrato prohíbe en su §9.
        """
        maquina = crear_maquina(cliente, cuenta["cabeceras"])
        ficha = la_ficha(cliente, cuenta["cabeceras"], maquina["id"])

        obligaciones = sus_obligaciones(ficha)
        assert len(ficha["obligaciones"]) == 5, "la ficha separa las cinco obligaciones, siempre"
        for tipo in maquinaria.OBLIGACIONES:
            assert obligaciones[tipo]["aplicabilidad"] == "no_se", tipo
            assert obligaciones[tipo]["situacion"] == maquinaria.SITUACION_NO_SE_SI_TOCA, tipo
            assert obligaciones[tipo]["proxima_fecha"] is None, tipo
            assert obligaciones[tipo]["resultado"] == "no_consta", tipo
        # Y se dice en la pantalla, con el aviso que pide el dato: no calla ni supone.
        assert any(aviso["codigo"] == "M9_no_se_si_esa_inspeccion_le_toca" for aviso in ficha["avisos"])

    def test_el_nombre_y_la_clase_no_cambian_lo_que_le_toca(self, cliente, cuenta):
        """**La trampa, comprobada por el camino corto**: dos máquinas con los mismos datos y nombres
        distintos —«Tractor» y «Sulfatadora», que son los dos del contrato— dan exactamente lo mismo.

        Si alguien metiera algún día una regla del tipo «esto es un tractor, luego le toca la ITV»,
        esta prueba se pone roja sin necesidad de saber qué regla era.
        """
        cabeceras = cuenta["cabeceras"]
        tractor = crear_maquina(cliente, cabeceras, nombre="Tractor", clase="tractor")
        sulfatadora = crear_maquina(
            cliente, cabeceras, nombre="Sulfatadora", clase="equipo_de_aplicacion"
        )
        for maquina in (tractor, sulfatadora):
            declarar(cliente, cabeceras, maquina["id"], "iteaf")
            apuntar_inspeccion(cliente, cabeceras, maquina["id"], fecha="2024-03-01")

        una = sus_obligaciones(la_ficha(cliente, cabeceras, tractor["id"]))
        otra = sus_obligaciones(la_ficha(cliente, cabeceras, sulfatadora["id"]))
        for tipo in maquinaria.OBLIGACIONES:
            assert una[tipo]["situacion"] == otra[tipo]["situacion"], tipo
            assert una[tipo]["proxima_fecha"] == otra[tipo]["proxima_fecha"], tipo
            assert una[tipo]["aplicabilidad"] == otra[tipo]["aplicabilidad"], tipo

    def test_una_obligacion_que_aplica_y_sin_inspeccion_pide_el_dato_y_no_ensena_fecha(
        self, cliente, cuenta
    ):
        """Aplica la ITV, no hay ninguna inspección apuntada y **el programa no enseña ninguna fecha**.

        Lo que hace es decirlo (`M7…`) y pedir la clasificación técnica, que es lo que el contrato manda:
        «pedir la clasificación técnica necesaria». Una fecha calculada aquí sería un dato inventado con
        la misma cara que uno verdadero.
        """
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras, nombre="Tractor", clase="tractor")
        declarar(cliente, cabeceras, maquina["id"], "itv")

        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        itv = sus_obligaciones(ficha)["itv"]
        assert itv["aplicabilidad"] == "si"
        assert itv["situacion"] == maquinaria.SITUACION_SIN_INSPECCION
        assert itv["proxima_fecha"] is None and itv["dias"] is None
        assert ficha["resumen"]["proxima_revision"]["fecha"] is None
        assert ficha["resumen"]["proxima_revision"]["sin_fecha"] >= 1
        assert any(aviso["codigo"] == "M7_no_hay_ninguna_inspeccion_apuntada" for aviso in ficha["avisos"])
        # Y la clasificación técnica, que es lo que hay que mirar, está vacía y se dice que falta.
        assert ficha["maquina"]["clasificacion_tecnica"] is None

    def test_la_fecha_que_se_ensena_es_la_que_se_apunto_y_ni_un_dia_mas(self, cliente, cuenta):
        """La «próxima fecha» es **la del papel**, copiada. Ni sumada ni redondeada ni deducida.

        Se prueba con una fecha rara a propósito (un 29 de febrero y una fecha que no es múltiplo de
        nada): si alguien metiera un cálculo, el resultado dejaría de coincidir con lo apuntado.
        """
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        declarar(cliente, cabeceras, maquina["id"], "iteaf")
        apuntar_inspeccion(
            cliente, cabeceras, maquina["id"], fecha="2024-02-29", proxima_fecha="2031-02-28"
        )
        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        assert sus_obligaciones(ficha)["iteaf"]["proxima_fecha"] == "2031-02-28"
        assert ficha["resumen"]["proxima_revision"]["fecha"] == "2031-02-28"

    def test_sin_la_fecha_de_la_proxima_se_dice_que_no_se_sabe(self, cliente, cuenta):
        """El papel trae la inspección pero **no la fecha de la próxima**: se dice, no se rellena."""
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        declarar(cliente, cabeceras, maquina["id"], "itv")
        apuntar_inspeccion(cliente, cabeceras, maquina["id"], tipo="itv", fecha="2024-03-01")

        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        itv = sus_obligaciones(ficha)["itv"]
        assert itv["situacion"] == maquinaria.SITUACION_SIN_FECHA
        assert itv["proxima_fecha"] is None
        assert any(
            aviso["codigo"] == "M8_la_inspeccion_no_trae_la_proxima_fecha" for aviso in ficha["avisos"]
        )

    def test_una_inspeccion_sin_resultado_no_es_una_inspeccion_favorable(self, cliente, cuenta):
        """`resultado` nace en «no lo pone el papel», que no es «favorable».

        El esquema no admite un resultado vacío por accidente: se manda «no_consta» explícito, que es lo
        que hace la pantalla cuando el papel no dice cómo salió, y que es **lo contrario** de dar por
        buena la inspección.
        """
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        declarar(cliente, cabeceras, maquina["id"], "iteaf")
        inspeccion = apuntar_inspeccion(
            cliente, cabeceras, maquina["id"], fecha="2024-03-01", proxima_fecha="2029-03-01",
            resultado="no_consta",
        )
        assert inspeccion["resultado"] == "no_consta"
        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        assert sus_obligaciones(ficha)["iteaf"]["resultado"] == "no_consta"
        # La fecha del papel sigue valiendo (está en regla *hasta esa fecha*), pero el resultado no se
        # convierte en favorable por eso.
        assert sus_obligaciones(ficha)["iteaf"]["situacion"] == maquinaria.SITUACION_VIGENTE
        assert sus_obligaciones(ficha)["iteaf"]["resultado"] != "favorable"

    def test_los_valores_por_defecto_del_modelo_no_son_permisivos(self):
        """Los tres campos donde un valor de partida sería una afirmación que nadie ha hecho.

        Se mira **el modelo**, no la pantalla, porque es donde se cuela el defecto: un `default="no"` en
        la aplicabilidad de una obligación convertiría «no lo sé» en «no le toca» en cualquier sitio que
        cree una fila sin decirlo, incluido un guion de importación.
        """
        assert models.Maquina.propiedad.default.arg == "no_se"
        assert models.Maquina.disponibilidad.default.arg == "no_se"
        assert models.ObligacionDeMaquina.aplicabilidad.default.arg == "no_se"
        assert models.ObligacionDeMaquina.origen.default.arg == "no_se"
        assert models.InspeccionDeMaquina.resultado.default.arg == "no_consta"
        # Y la disponibilidad y la propiedad no tienen un `False`/0 escondido por ningún lado.
        assert models.Maquina.horas.default is None or models.Maquina.horas.nullable

    def test_la_clase_y_la_propiedad_y_la_disponibilidad_hay_que_decirlas(self, cliente, cuenta):
        """Faltando una de las tres, no se guarda: no hay un valor por defecto que decida por nadie."""
        for falta in ("clase", "propiedad", "disponibilidad"):
            datos = {
                "nombre": "El Landini",
                "clase": "tractor",
                "propiedad": "propia",
                "disponibilidad": "disponible",
            }
            del datos[falta]
            respuesta = cliente.post("/api/maquinaria", headers=cuenta["cabeceras"], json=datos)
            assert respuesta.status_code == 422, f"{falta}: {respuesta.text}"

    def test_lo_que_falta_esta_dicho_con_su_dependencia(self):
        """Lo que no se puede calcular se declara: qué es, para qué hace falta y de quién depende.

        Es la receta de `AGENTS.md` («cuando algo oficial no se puede hacer entero»), y aquí es el
        trabajo legal **L07** de la matriz normativa: la clasificación técnica por máquina real.
        """
        claves = {lo["clave"] for lo in maquinaria.QUE_FALTA}
        assert "plazos_de_las_inspecciones" in claves
        for lo in maquinaria.QUE_FALTA:
            assert lo["que"] and lo["para_que"] and lo["de_quien_depende"]
            assert "L07" in lo["de_quien_depende"]

    def test_no_hay_ninguna_funcion_que_sume_dias_a_una_fecha(self):
        """El guardián más directo: **el módulo de la maquinaria no hace aritmética con fechas**.

        Se lee su propio código fuente y se exige que no aparezca un `timedelta`. Es tosco a propósito:
        el día que alguien escriba el cálculo de plazos, tendrá que venir aquí a quitar esta prueba y a
        explicar de dónde sale el plazo y con qué fuente, que es justo lo que el ticket pide.
        """
        import inspect

        fuente = inspect.getsource(maquinaria)
        assert "timedelta" not in fuente, (
            "la maquinaria no puede calcular fechas: el plazo por clasificación técnica no está "
            "transcrito (L07). Si se ha transcrito, esta prueba se cambia explicando la fuente."
        )


# --------------------------------------------------------------------------
# 2. Las cinco obligaciones, separadas y con su fuente
# --------------------------------------------------------------------------


class TestLasCincoObligacionesSeparadas:
    def test_la_ficha_trae_las_cinco_en_su_orden_y_con_su_nombre(self, cliente, cuenta):
        maquina = crear_maquina(cliente, cuenta["cabeceras"])
        ficha = la_ficha(cliente, cuenta["cabeceras"], maquina["id"])
        assert [una["tipo"] for una in ficha["obligaciones"]] == list(maquinaria.OBLIGACIONES)
        assert [una["tipo"] for una in ficha["obligaciones"]] == [
            "itv",
            "iteaf",
            "mantenimiento",
            "seguro",
            "roma",
        ]

    def test_cada_obligacion_tiene_aplicabilidad_fuente_ultima_resultado_fecha_y_documento(
        self, cliente, cuenta
    ):
        """Lo que el contrato pide campo por campo, comprobado en una obligación de verdad."""
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        papel = crear_papel(cliente, cabeceras)
        declarar(cliente, cabeceras, maquina["id"], "iteaf", origen="documento")
        apuntar_inspeccion(
            cliente,
            cabeceras,
            maquina["id"],
            fecha="2024-03-01",
            resultado="favorable",
            proxima_fecha="2029-03-01",
            documento_id=papel["id"],
        )

        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        iteaf = sus_obligaciones(ficha)["iteaf"]
        assert iteaf["aplicabilidad"] == "si"
        assert iteaf["origen_de_la_aplicabilidad"] == "documento"
        assert iteaf["ultima_inspeccion"]["fecha"] == "2024-03-01"
        assert iteaf["resultado"] == "favorable"
        assert iteaf["proxima_fecha"] == "2029-03-01"
        assert iteaf["documento_id"] == papel["id"]
        assert iteaf["trae_papel"] is True
        # Y la fuente de la obligación (la norma que tenemos, o lo que falta) va en la respuesta.
        assert "1702/2011" in iteaf["fuente"]["norma"]
        assert iteaf["fuente"]["url"].startswith("https://www.boe.es/")
        assert iteaf["fuente"]["que_falta"]

    def test_la_itv_y_la_iteaf_son_dos_cosas_distintas_y_con_fuente_distinta(self, cliente, cuenta):
        """El documento de la casa lo avisa: «No llamar a ITEAF "ITV" en las etiquetas»."""
        ficha = la_ficha(cliente, cuenta["cabeceras"], crear_maquina(cliente, cuenta["cabeceras"])["id"])
        itv, iteaf = sus_obligaciones(ficha)["itv"], sus_obligaciones(ficha)["iteaf"]
        assert itv["fuente"]["norma"] != iteaf["fuente"]["norma"]
        assert "920/2017" in itv["fuente"]["norma"]
        assert textos.MAQUINARIA_DE_LA_FINCA["obligacion_itv"] == "ITV"
        assert textos.MAQUINARIA_DE_LA_FINCA["obligacion_iteaf"] == "ITEAF"

    def test_las_obligaciones_de_las_que_no_tenemos_norma_lo_dicen(self):
        """De dos de las cinco no hay ninguna norma transcrita y **se dice**, no se rellena.

        Es la regla de la casa: lo que falta se declara con lo que es y de quién depende. Y el
        mantenimiento y el seguro están justo ahí: nadie ha transcrito una norma que obligue a un
        mantenimiento con plazo ni al seguro de una máquina agrícola, así que el programa no la supone.
        """
        for tipo in ("mantenimiento", "seguro"):
            fuente = maquinaria.FUENTE_DE_LA_OBLIGACION[tipo]
            assert fuente["norma"] is None
            assert fuente["que_falta"]
        assert maquinaria.FUENTE_DE_LA_OBLIGACION["roma"]["url"] is None
        assert "1.3" in maquinaria.FUENTE_DE_LA_OBLIGACION["roma"]["norma"]

    def test_declarar_dos_veces_la_misma_obligacion_corrige_y_no_duplica(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        primera = declarar(cliente, cabeceras, maquina["id"], "itv", aplicabilidad="no_se")
        segunda = declarar(cliente, cabeceras, maquina["id"], "itv", aplicabilidad="si")
        assert primera["id"] == segunda["id"], "hay una sola respuesta por máquina y obligación"
        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        assert sus_obligaciones(ficha)["itv"]["aplicabilidad"] == "si"

    def test_una_obligacion_que_no_existe_se_rechaza_con_su_frase(self, cliente, cuenta):
        maquina = crear_maquina(cliente, cuenta["cabeceras"])
        respuesta = cliente.put(
            f"/api/maquinaria/{maquina['id']}/obligaciones/plan_de_abonado",
            headers=cuenta["cabeceras"],
            json={"aplicabilidad": "si", "origen": "documento"},
        )
        assert respuesta.status_code == 422
        assert "cinco" in respuesta.json()["detail"]

    def test_una_aplicabilidad_inventada_se_rechaza(self, cliente, cuenta):
        maquina = crear_maquina(cliente, cuenta["cabeceras"])
        respuesta = cliente.put(
            f"/api/maquinaria/{maquina['id']}/obligaciones/itv",
            headers=cuenta["cabeceras"],
            json={"aplicabilidad": "creo_que_si", "origen": "documento"},
        )
        assert respuesta.status_code == 422
        assert "respuestas" in respuesta.json()["detail"]

    def test_una_inspeccion_desfavorable_no_se_tapa_con_una_fecha_futura(self, cliente, cuenta):
        """Si el papel dice que salió desfavorable, la máquina no está en regla aunque traiga fecha.

        Manda lo que dice el papel: es lo único honesto, y una fecha de la próxima en el futuro no
        convierte un resultado desfavorable en un cumplimiento.
        """
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        declarar(cliente, cabeceras, maquina["id"], "itv")
        apuntar_inspeccion(
            cliente,
            cabeceras,
            maquina["id"],
            tipo="itv",
            fecha="2024-03-01",
            resultado="desfavorable",
            proxima_fecha=_dias(400),
        )
        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        itv = sus_obligaciones(ficha)["itv"]
        assert itv["situacion"] == maquinaria.SITUACION_NO_FAVORABLE
        assert itv["proxima_fecha"] == _dias(400), "la fecha del papel se sigue enseñando"
        assert any(
            aviso["codigo"] == "M6_la_ultima_inspeccion_no_fue_favorable"
            for aviso in ficha["avisos"]
        )


# --------------------------------------------------------------------------
# 3. Una inspección sin documento se apunta y se dice que no lo trae
# --------------------------------------------------------------------------


class TestUnaInspeccionSinPapel:
    def test_se_apunta_sin_papel_y_la_respuesta_lo_dice(self, cliente, cuenta):
        """El contrato lo pide así: se apunta y **se dice que no lo trae**. Hay certificados que están
        en el taller, y no poder apuntar la inspección por eso sería peor que apuntarla sin el papel."""
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        inspeccion = apuntar_inspeccion(cliente, cabeceras, maquina["id"], fecha="2024-03-01")
        assert inspeccion["documento_id"] is None
        assert inspeccion["trae_papel"] is False

        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        assert ficha["resumen"]["documentacion"] == {"inspecciones": 1, "con_papel": 0, "sin_papel": 1}
        assert sus_obligaciones(ficha)["iteaf"]["trae_papel"] is False

    def test_con_papel_se_cuenta_y_se_puede_abrir_cual_es(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        papel = crear_papel(cliente, cabeceras)
        apuntar_inspeccion(cliente, cabeceras, maquina["id"], documento_id=papel["id"])
        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        assert ficha["resumen"]["documentacion"] == {"inspecciones": 1, "con_papel": 1, "sin_papel": 0}
        assert sus_obligaciones(ficha)["iteaf"]["documento_id"] == papel["id"]

    def test_el_papel_de_otra_finca_no_vale(self, cliente, cuenta, crear_cuenta):
        """Y contesta **404, no 403**, como todo el programa: no se cuenta si el identificador existe."""
        otra = crear_cuenta("otro@ejemplo.com")
        papel_ajeno = crear_papel(cliente, otra["cabeceras"], titulo="Un papel de otra finca")
        maquina = crear_maquina(cliente, cuenta["cabeceras"])
        respuesta = cliente.post(
            f"/api/maquinaria/{maquina['id']}/inspecciones",
            headers=cuenta["cabeceras"],
            json={"tipo": "iteaf", "fecha": "2024-03-01", "documento_id": papel_ajeno["id"]},
        )
        assert respuesta.status_code == 404, respuesta.text


# --------------------------------------------------------------------------
# 4. Los avisos al planificar un trabajo, y las averías
# --------------------------------------------------------------------------


class TestAvisosAlPlanificarUnTrabajo:
    def test_una_inspeccion_vencida_sale_en_los_avisos_de_planificar(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras, nombre="El Landini")
        declarar(cliente, cabeceras, maquina["id"], "itv")
        apuntar_inspeccion(
            cliente,
            cabeceras,
            maquina["id"],
            tipo="itv",
            fecha="2019-01-10",
            proxima_fecha=_dias(-10),
            resultado="favorable",
        )
        avisos = cliente.get(
            "/api/maquinaria/avisos", headers=cabeceras, params={"maquina_id": maquina["id"]}
        )
        assert avisos.status_code == 200, avisos.text
        codigos = [aviso["codigo"] for aviso in avisos.json()]
        assert "M4_una_inspeccion_esta_vencida" in codigos
        el_suyo = next(a for a in avisos.json() if a["codigo"] == "M4_una_inspeccion_esta_vencida")
        assert el_suyo["urgente"] is True
        assert "El Landini" in el_suyo["mensaje"] and "ITV" in el_suyo["mensaje"]

    def test_una_inspeccion_al_caer_tambien_y_una_vigente_no(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        al_caer = crear_maquina(cliente, cabeceras, nombre="Al caer")
        declarar(cliente, cabeceras, al_caer["id"], "iteaf")
        apuntar_inspeccion(cliente, cabeceras, al_caer["id"], proxima_fecha=_dias(20))

        tranquila = crear_maquina(cliente, cabeceras, nombre="Tranquila")
        declarar(cliente, cabeceras, tranquila["id"], "iteaf")
        apuntar_inspeccion(cliente, cabeceras, tranquila["id"], proxima_fecha=_dias(900))

        avisos = cliente.get("/api/maquinaria/avisos", headers=cabeceras).json()
        de_al_caer = [a for a in avisos if a["maquina_id"] == al_caer["id"]]
        de_tranquila = [a for a in avisos if a["maquina_id"] == tranquila["id"]]
        assert "M5_una_inspeccion_caduca_pronto" in [a["codigo"] for a in de_al_caer]
        assert de_tranquila == [], "una inspección vigente no es un aviso al planificar"

    def test_la_fecha_del_trabajo_es_la_que_decide(self, cliente, cuenta):
        """`fecha` es el día del trabajo: una inspección que vence en marzo no impide el trabajo de hoy."""
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        declarar(cliente, cabeceras, maquina["id"], "itv")
        apuntar_inspeccion(cliente, cabeceras, maquina["id"], tipo="itv", proxima_fecha="2027-03-01")

        # Trabajando en el año 2027 después de esa fecha: vencida.
        en_2028 = cliente.get(
            "/api/maquinaria/avisos",
            headers=cabeceras,
            params={"maquina_id": maquina["id"], "fecha": "2028-01-01"},
        ).json()
        assert "M4_una_inspeccion_esta_vencida" in [a["codigo"] for a in en_2028]
        # Y el mismo día del papel: vigente (no caducada todavía).
        antes = cliente.get(
            "/api/maquinaria/avisos",
            headers=cabeceras,
            params={"maquina_id": maquina["id"], "fecha": "2026-01-01"},
        ).json()
        assert "M4_una_inspeccion_esta_vencida" not in [a["codigo"] for a in antes]

    def test_una_maquina_no_disponible_avisa_antes_de_contar_con_ella(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras, disponibilidad="no_disponible")
        avisos = cliente.get("/api/maquinaria/avisos", headers=cabeceras).json()
        assert "M1_la_maquina_no_esta_disponible" in [a["codigo"] for a in avisos]

    def test_una_averia_sin_arreglar_avisa_y_una_arreglada_no(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        rota = crear_maquina(cliente, cabeceras, nombre="La rota")
        apuntar_averia(cliente, cabeceras, rota["id"], resuelta=False, fecha="2026-04-01")
        arreglada = crear_maquina(cliente, cabeceras, nombre="La arreglada")
        apuntar_averia(
            cliente,
            cabeceras,
            arreglada["id"],
            resuelta=True,
            fecha="2026-04-01",
            fecha_resuelta="2026-04-10",
        )
        avisos = cliente.get("/api/maquinaria/avisos", headers=cabeceras).json()
        de_la_rota = [a["codigo"] for a in avisos if a["maquina_id"] == rota["id"]]
        de_la_arreglada = [a["codigo"] for a in avisos if a["maquina_id"] == arreglada["id"]]
        assert "M3_tiene_una_averia_sin_arreglar" in de_la_rota
        assert de_la_arreglada == []

    def test_la_averia_no_cambia_sola_la_disponibilidad(self, cliente, cuenta):
        """Dos datos distintos que se enseñan juntos y **no se mezclan**: una máquina con una avería
        apuntada puede estar trabajando (con el apero que sí va), y quien lo sabe es el agricultor."""
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras, disponibilidad="disponible")
        apuntar_averia(cliente, cabeceras, maquina["id"], resuelta=False)
        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        assert ficha["maquina"]["disponibilidad"] == "disponible"
        assert ficha["resumen"]["disponibilidad"] == "disponible"

    def test_una_averia_no_se_puede_apuntar_sin_decir_si_esta_arreglada(self, cliente, cuenta):
        maquina = crear_maquina(cliente, cuenta["cabeceras"])
        respuesta = cliente.post(
            f"/api/maquinaria/{maquina['id']}/averias",
            headers=cuenta["cabeceras"],
            json={"fecha": "2026-04-01", "que_paso": "Se rompió el eje"},
        )
        assert respuesta.status_code == 422, "«no lo sé» se manda, no se deja en blanco"


# --------------------------------------------------------------------------
# 5. La puerta de calidad: EquipoAplicacion no es «la maquinaria»
# --------------------------------------------------------------------------


class TestElEquipoDeEcharProductoNoEsLaMaquinaria:
    def test_un_tractor_sin_roma_y_sin_iteaf_se_apunta_y_no_se_le_pide_ninguno(self, cliente, cuenta):
        """La prueba que el inventario del T01 pedía y que **no se podía escribir** por falta del modelo.

        Un tractor sin número de ROMA y sin ITEAF se da de alta, y el programa **no le pide ninguno de
        los dos**: no hay ninguna respuesta que lo bloquee ni ningún aviso que los reclame.
        """
        cabeceras = cuenta["cabeceras"]
        tractor = crear_maquina(
            cliente, cabeceras, nombre="El Landini", clase="tractor", numero_roma=None,
            clasificacion_tecnica=None,
        )
        assert tractor["numero_roma"] is None

        ficha = la_ficha(cliente, cabeceras, tractor["id"])
        de_roma = sus_obligaciones(ficha)["roma"]
        assert de_roma["aplicabilidad"] == "no_se", "nadie ha dicho que a este tractor le toque el ROMA"
        assert de_roma["situacion"] == maquinaria.SITUACION_NO_SE_SI_TOCA
        # Ni un aviso le pide el ROMA ni la ITEAF: lo que falta es que él diga qué le toca.
        assert all("ROMA" not in aviso["mensaje"] or aviso["codigo"].startswith("M9") for aviso in ficha["avisos"])

    def test_un_remolque_y_un_apero_no_comparten_el_vencimiento_de_un_tractor(self, cliente, cuenta):
        """El caso del documento de la casa: «tractor, remolque y equipo de aplicación no comparten un
        vencimiento universal». Aquí se comprueba que el programa no se lo inventa: cada uno tiene sus
        propias obligaciones declaradas, y las que nadie ha declarado están en «no se sabe»."""
        cabeceras = cuenta["cabeceras"]
        tractor = crear_maquina(cliente, cabeceras, nombre="Tractor", clase="tractor")
        remolque = crear_maquina(cliente, cabeceras, nombre="Remolque", clase="remolque")
        declarar(cliente, cabeceras, tractor["id"], "itv")
        declarar(cliente, cabeceras, remolque["id"], "itv", aplicabilidad="si")
        # Al remolque se le apunta su ITV y al tractor la suya, con fechas distintas.
        apuntar_inspeccion(
            cliente, cabeceras, tractor["id"], tipo="itv", fecha="2024-01-01", proxima_fecha="2027-01-01"
        )
        apuntar_inspeccion(
            cliente, cabeceras, remolque["id"], tipo="itv", fecha="2025-06-01", proxima_fecha="2030-06-01"
        )
        su_tractor = sus_obligaciones(la_ficha(cliente, cabeceras, tractor["id"]))
        su_remolque = sus_obligaciones(la_ficha(cliente, cabeceras, remolque["id"]))
        assert su_tractor["itv"]["proxima_fecha"] == "2027-01-01"
        assert su_remolque["itv"]["proxima_fecha"] == "2030-06-01"
        # Y las que nadie ha declarado, en «no se sabe», en los dos.
        assert su_tractor["iteaf"]["situacion"] == maquinaria.SITUACION_NO_SE_SI_TOCA
        assert su_remolque["seguro"]["situacion"] == maquinaria.SITUACION_NO_SE_SI_TOCA

    def test_los_equipos_del_cuaderno_que_no_estan_en_la_lista_se_ensenan_aparte(self, cliente, cuenta):
        """**Lo que ya estaba apuntado no puede desaparecer de la vista.**

        El equipo de echar producto vive en la hoja 1.3 del cuaderno (otra tabla, otro sentido). La lista
        de maquinaria es nueva y más ancha; lo que no se puede hacer es dejar al agricultor creyendo que
        el pulverizador que ya tenía apuntado se ha perdido.
        """
        cabeceras = cuenta["cabeceras"]
        equipo = cliente.post(
            "/api/equipos",
            headers=cabeceras,
            json={
                "nombre": "Pulverizador grande",
                "tipo": "Atomizador",
                "numero_roma": "ROMA-9876",
                "fecha_iteaf": "2024-03-01",
                "fecha_proxima_iteaf": "2029-03-01",
            },
        )
        assert equipo.status_code == 201, equipo.text
        tabla = cliente.get("/api/maquinaria", headers=cabeceras).json()
        assert tabla["total"] == 0
        sin_ficha = tabla["equipos_sin_ficha"]
        assert [uno["nombre"] for uno in sin_ficha] == ["Pulverizador grande"]
        assert sin_ficha[0]["numero_roma"] == "ROMA-9876"
        assert sin_ficha[0]["fecha_proxima_iteaf"] == "2029-03-01"

    def test_traer_el_equipo_lo_enlaza_y_no_inventa_la_clasificacion(self, cliente, cuenta):
        """Al traerlo se copia **lo que ya estaba escrito** y se deja vacío lo que no se sabe.

        En particular: la **clasificación técnica se queda vacía** aunque la máquina sea un pulverizador.
        Deducirla del nombre («si es un pulverizador, es de tal clasificación») es justo lo que el
        contrato prohíbe.
        """
        cabeceras = cuenta["cabeceras"]
        equipo = cliente.post(
            "/api/equipos",
            headers=cabeceras,
            json={
                "nombre": "Pulverizador grande",
                "tipo": "Atomizador",
                "numero_roma": "ROMA-9876",
                "numero_serie": "SN-1",
                "marca": "Hardy",
                "fecha_iteaf": "2024-03-01",
                "fecha_proxima_iteaf": "2029-03-01",
            },
        ).json()
        respuesta = cliente.post(f"/api/maquinaria/desde-equipo/{equipo['id']}", headers=cabeceras)
        assert respuesta.status_code == 201, respuesta.text
        traida = respuesta.json()
        assert traida["equipo_aplicacion_id"] == equipo["id"]
        assert traida["numero_roma"] == "ROMA-9876"
        assert traida["numero_serie"] == "SN-1"
        assert traida["marca"] == "Hardy"
        assert traida["clase"] == "equipo_de_aplicacion"
        assert traida["clasificacion_tecnica"] is None, "no se deduce del nombre ni del tipo"
        assert traida["propiedad"] == "propia"
        assert traida["disponibilidad"] == "no_se"

        # Y la inspección que ya estaba apuntada en el cuaderno se trae como inspección, con su fecha y
        # su próxima fecha, y con el resultado en «no lo pone el papel», que es la verdad.
        ficha = la_ficha(cliente, cabeceras, traida["id"])
        iteaf = sus_obligaciones(ficha)["iteaf"]
        assert iteaf["aplicabilidad"] == "si"
        assert iteaf["ultima_inspeccion"]["fecha"] == "2024-03-01"
        assert iteaf["resultado"] == "no_consta"
        assert iteaf["proxima_fecha"] == "2029-03-01"
        assert iteaf["trae_papel"] is False, "el cuaderno no tenía el certificado guardado aquí"
        # Y ya no sale en la lista de «equipos sin ficha».
        tabla = cliente.get("/api/maquinaria", headers=cabeceras).json()
        assert tabla["equipos_sin_ficha"] == []

    def test_traer_el_mismo_equipo_dos_veces_no_hace_dos_fichas(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        equipo = cliente.post(
            "/api/equipos", headers=cabeceras, json={"nombre": "La mochila", "tipo": "Mochila"}
        ).json()
        primera = cliente.post(f"/api/maquinaria/desde-equipo/{equipo['id']}", headers=cabeceras)
        assert primera.status_code == 201
        segunda = cliente.post(f"/api/maquinaria/desde-equipo/{equipo['id']}", headers=cabeceras)
        assert segunda.status_code == 409
        # El aviso dice **cuál es ya esa máquina**, porque el mismo mensaje se usa también cuando el
        # enlace se intenta por el alta o por la corrección (un equipo es una máquina, no dos).
        assert "La mochila" in segunda.json()["detail"]
        assert cliente.get("/api/maquinaria", headers=cabeceras).json()["total"] == 1

    def test_no_se_puede_borrar_el_equipo_que_la_maquinaria_tiene_enlazado(self, cliente, cuenta):
        """Si se borrara, la hoja 1.3 del cuaderno se quedaría sin el número de ROMA y sin la fecha.

        La cuenta de dependencias se saca de las tablas de verdad, así que al añadir el enlace apareció
        sola; lo que se comprueba aquí es que el borrado la mira y contesta 409 en vez de dejar la fila
        apuntando a algo que ya no existe.
        """
        cabeceras = cuenta["cabeceras"]
        equipo = cliente.post(
            "/api/equipos",
            headers=cabeceras,
            json={"nombre": "Pulverizador grande", "numero_roma": "ROMA-1"},
        ).json()
        cliente.post(f"/api/maquinaria/desde-equipo/{equipo['id']}", headers=cabeceras)
        respuesta = cliente.delete(f"/api/equipos/{equipo['id']}", headers=cabeceras)
        assert respuesta.status_code == 409, respuesta.text
        assert "en uso" in respuesta.json()["detail"] or "usa" in respuesta.json()["detail"]

    def test_las_tablas_que_usan_una_maquina_son_las_de_hoy(self):
        """La cuenta que decide si una máquina se puede quitar, contra las tablas de verdad.

        Hoy **ninguna** tabla del cuaderno apunta a una máquina fuera de su propia ficha (las
        obligaciones, las inspecciones y las averías son parte de ella: ver
        `maquinaria_api.TABLAS_QUE_SON_PARTE_DE_LA_MAQUINA`). El día que una labor diga con qué tractor
        se hizo, esta prueba se pone roja y obliga a decidir: contarla como dependencia —y contestar 409—
        o escribir por qué no.
        """
        from app import correcciones

        todas = [modelo.__tablename__ for modelo in correcciones.tablas_que_apuntan_a("maquina_id")]
        assert set(todas) == set(maquinaria_api.TABLAS_QUE_SON_PARTE_DE_LA_MAQUINA)
        assert maquinaria_api._tablas_que_usan_una_maquina() == []


# --------------------------------------------------------------------------
# 6. La tabla
# --------------------------------------------------------------------------


class TestLaTabla:
    def test_trae_lo_que_pide_el_contrato_de_cada_maquina(self, cliente, cuenta):
        """Máquina, tipo, matrícula o serie, propiedad, horas, próxima revisión, papeles y disponibilidad."""
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(
            cliente,
            cabeceras,
            nombre="El Landini",
            matricula="1234 ABC",
            horas=1234.5,
            numero_roma="ROMA-1",
        )
        declarar(cliente, cabeceras, maquina["id"], "itv")
        apuntar_inspeccion(
            cliente, cabeceras, maquina["id"], tipo="itv", fecha="2024-01-01", proxima_fecha="2027-01-01"
        )
        tabla = cliente.get("/api/maquinaria", headers=cabeceras).json()
        fila = tabla["maquinas"][0]
        assert fila["nombre"] == "El Landini"
        assert fila["clase"] == "tractor"
        assert fila["matricula"] == "1234 ABC"
        assert fila["propiedad"] == "propia"
        assert fila["horas"] == 1234.5
        assert fila["disponibilidad"] == "disponible"
        assert fila["resumen"]["proxima_revision"]["fecha"] == "2027-01-01"
        assert fila["resumen"]["proxima_revision"]["tipo"] == "itv"
        assert fila["resumen"]["documentacion"]["inspecciones"] == 1

    def test_los_totales_son_del_conjunto_y_no_de_lo_que_se_ve(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        crear_maquina(cliente, cabeceras, nombre="Una")
        rota = crear_maquina(cliente, cabeceras, nombre="Otra", disponibilidad="no_disponible")
        apuntar_averia(cliente, cabeceras, rota["id"], resuelta=False)
        tabla = cliente.get("/api/maquinaria", headers=cabeceras).json()
        assert tabla["total"] == 2
        assert tabla["con_avisos"] == 2
        assert tabla["con_avisos_urgentes"] == 1

    def test_la_tabla_lleva_lo_que_falta_por_saber(self, cliente, cuenta):
        """La tabla dice «próxima revisión: —» y **cuántas obligaciones no tienen fecha**: sin esa
        cuenta, el agricultor creería que con la fecha que ve está todo mirado."""
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        declarar(cliente, cabeceras, maquina["id"], "itv")
        tabla = cliente.get("/api/maquinaria", headers=cabeceras).json()
        revision = tabla["maquinas"][0]["resumen"]["proxima_revision"]
        assert revision["fecha"] is None
        assert revision["sin_fecha"] >= 1, "las cinco obligaciones sin declarar y una sin inspección"
        assert tabla["que_falta"], "la pantalla tiene que poder decir lo que el programa no calcula"

    def test_sin_maquinas_la_tabla_esta_vacia_y_lo_dice(self, cliente, cuenta):
        tabla = cliente.get("/api/maquinaria", headers=cuenta["cabeceras"]).json()
        assert tabla["maquinas"] == [] and tabla["total"] == 0


# --------------------------------------------------------------------------
# 7. Aislamiento entre fincas (404, no 403)
# --------------------------------------------------------------------------


class TestAislamientoEntreFincas:
    def test_la_maquina_de_otra_finca_no_se_ve_ni_se_toca(self, cliente, cuenta, crear_cuenta):
        otra = crear_cuenta("vecino@ejemplo.com")
        mia = crear_maquina(cliente, cuenta["cabeceras"])
        # Ni leerla…
        assert cliente.get(f"/api/maquinaria/{mia['id']}", headers=otra["cabeceras"]).status_code == 404
        # Ni corregirla…
        correccion = {
            "nombre": "La tuya ahora",
            "clase": "tractor",
            "propiedad": "propia",
            "disponibilidad": "disponible",
        }
        assert (
            cliente.put(
                f"/api/maquinaria/{mia['id']}", headers=otra["cabeceras"], json=correccion
            ).status_code
            == 404
        )
        # Ni borrarla…
        assert cliente.delete(f"/api/maquinaria/{mia['id']}", headers=otra["cabeceras"]).status_code == 404
        # Ni mirar sus avisos por identificador.
        assert cliente.get(
            "/api/maquinaria/avisos", headers=otra["cabeceras"], params={"maquina_id": mia["id"]}
        ).json() == []

    def test_la_inspeccion_de_otra_finca_no_se_toca(self, cliente, cuenta, crear_cuenta):
        otra = crear_cuenta("vecino@ejemplo.com")
        mia = crear_maquina(cliente, cuenta["cabeceras"])
        inspeccion = apuntar_inspeccion(cliente, cuenta["cabeceras"], mia["id"])
        # Con la máquina de la otra finca no existe nada…
        assert (
            cliente.delete(
                f"/api/maquinaria/{mia['id']}/inspecciones/{inspeccion['id']}", headers=otra["cabeceras"]
            ).status_code
            == 404
        )
        # …y con una máquina suya, la inspección de la otra finca tampoco se encuentra.
        suya = crear_maquina(cliente, otra["cabeceras"])
        assert (
            cliente.delete(
                f"/api/maquinaria/{suya['id']}/inspecciones/{inspeccion['id']}", headers=otra["cabeceras"]
            ).status_code
            == 404
        )
        # Y la inspección sigue donde estaba.
        ficha = la_ficha(cliente, cuenta["cabeceras"], mia["id"])
        assert len(ficha["inspecciones"]) == 1

    def test_la_averia_de_otra_finca_no_se_toca(self, cliente, cuenta, crear_cuenta):
        otra = crear_cuenta("vecino@ejemplo.com")
        mia = crear_maquina(cliente, cuenta["cabeceras"])
        averia = apuntar_averia(cliente, cuenta["cabeceras"], mia["id"])
        suya = crear_maquina(cliente, otra["cabeceras"])
        assert (
            cliente.delete(
                f"/api/maquinaria/{suya['id']}/averias/{averia['id']}", headers=otra["cabeceras"]
            ).status_code
            == 404
        )

    def test_la_obligacion_de_otra_finca_no_se_declara(self, cliente, cuenta, crear_cuenta):
        otra = crear_cuenta("vecino@ejemplo.com")
        mia = crear_maquina(cliente, cuenta["cabeceras"])
        respuesta = cliente.put(
            f"/api/maquinaria/{mia['id']}/obligaciones/itv",
            headers=otra["cabeceras"],
            json={"aplicabilidad": "si", "origen": "documento"},
        )
        assert respuesta.status_code == 404


# --------------------------------------------------------------------------
# 8. Corregir, anular y reenviar sin duplicar
# --------------------------------------------------------------------------


class TestCorregirAnularYReenviar:
    def test_el_movil_que_reintenta_no_apunta_dos_inspecciones(self, cliente, cuenta):
        """El caso A12 del contrato: el móvil repite el envío al reconectar y **no se duplica nada**."""
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        primera = apuntar_inspeccion(cliente, cabeceras, maquina["id"], clave_de_reenvio="cola-1")
        segunda = apuntar_inspeccion(cliente, cabeceras, maquina["id"], clave_de_reenvio="cola-1")
        assert primera["id"] == segunda["id"]
        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        assert len(ficha["inspecciones"]) == 1

    def test_el_movil_que_reintenta_no_apunta_dos_averias(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        primera = apuntar_averia(cliente, cabeceras, maquina["id"], clave_de_reenvio="averia-1")
        segunda = apuntar_averia(cliente, cabeceras, maquina["id"], clave_de_reenvio="averia-1")
        assert primera["id"] == segunda["id"]
        assert len(la_ficha(cliente, cabeceras, maquina["id"])["averias"]) == 1

    def test_corregir_una_inspeccion_no_crea_otra_y_queda_en_el_rastro(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        inspeccion = apuntar_inspeccion(cliente, cabeceras, maquina["id"], fecha="2024-03-01")
        respuesta = cliente.put(
            f"/api/maquinaria/{maquina['id']}/inspecciones/{inspeccion['id']}",
            headers=cabeceras,
            json={
                "tipo": "iteaf",
                "fecha": "2024-03-02",
                "resultado": "favorable",
                "proxima_fecha": "2029-03-02",
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        corregida = respuesta.json()
        assert corregida["id"] == inspeccion["id"]
        assert corregida["fecha"] == "2024-03-02"
        assert len(la_ficha(cliente, cabeceras, maquina["id"])["inspecciones"]) == 1

        from app.database import SessionLocal
        from sqlalchemy import select

        with SessionLocal() as sesion:
            rastro = list(
                sesion.scalars(
                    select(models.Auditoria).where(
                        models.Auditoria.entidad == "inspeccion_de_maquina",
                        models.Auditoria.accion == "corregir",
                    )
                )
            )
        assert rastro, "la corrección tiene que dejar rastro en la auditoría"
        assert rastro[0].datos["fecha"] == ["2024-03-01", "2024-03-02"]

    def test_anular_una_inspeccion_la_deja_pero_deja_de_contar(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        declarar(cliente, cabeceras, maquina["id"], "itv")
        equivocada = apuntar_inspeccion(
            cliente, cabeceras, maquina["id"], tipo="itv", fecha="2020-01-01", proxima_fecha=_dias(-100)
        )
        assert sus_obligaciones(la_ficha(cliente, cabeceras, maquina["id"]))["itv"]["situacion"] == (
            maquinaria.SITUACION_VENCIDA
        )
        respuesta = cliente.post(
            f"/api/maquinaria/{maquina['id']}/inspecciones/{equivocada['id']}/anular",
            headers=cabeceras,
            json={"motivo": "Esa inspección era de otro tractor"},
        )
        assert respuesta.status_code == 200, respuesta.text
        anulada = respuesta.json()
        assert anulada["anulado"] is True and anulada["motivo_anulacion"]
        # Sigue en el cuaderno…
        ficha = la_ficha(cliente, cabeceras, maquina["id"])
        assert [una["id"] for una in ficha["inspecciones"]] == [equivocada["id"]]
        # …pero ya no cuenta: la obligación vuelve a «no hay ninguna inspección apuntada».
        assert sus_obligaciones(ficha)["itv"]["situacion"] == maquinaria.SITUACION_SIN_INSPECCION

    def test_borrar_una_inspeccion_deja_el_rastro(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        inspeccion = apuntar_inspeccion(cliente, cabeceras, maquina["id"])
        respuesta = cliente.delete(
            f"/api/maquinaria/{maquina['id']}/inspecciones/{inspeccion['id']}", headers=cabeceras
        )
        assert respuesta.status_code == 200, respuesta.text
        assert la_ficha(cliente, cabeceras, maquina["id"])["inspecciones"] == []

        from app.database import SessionLocal
        from sqlalchemy import select

        with SessionLocal() as sesion:
            entidades = list(
                sesion.scalars(
                    select(models.Auditoria.entidad).where(models.Auditoria.accion == "borrar")
                )
            )
        assert "inspeccion_de_maquina" in entidades

    def test_una_averia_se_corrige_para_decir_que_ya_esta_arreglada(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        averia = apuntar_averia(cliente, cabeceras, maquina["id"], resuelta=False)
        respuesta = cliente.put(
            f"/api/maquinaria/{maquina['id']}/averias/{averia['id']}",
            headers=cabeceras,
            json={
                "fecha": averia["fecha"],
                "que_paso": averia["que_paso"],
                "resuelta": True,
                "fecha_resuelta": "2026-04-15",
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["resuelta"] is True
        avisos = cliente.get("/api/maquinaria/avisos", headers=cabeceras).json()
        assert [a for a in avisos if a["maquina_id"] == maquina["id"]] == []

    def test_quitar_una_maquina_con_inspecciones_dentro_se_dice_y_no_se_hace(self, cliente, cuenta):
        """Nada se borra sin rastro: quitar la máquina se llevaría por delante lo que le pasaron."""
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        apuntar_inspeccion(cliente, cabeceras, maquina["id"])
        respuesta = cliente.delete(f"/api/maquinaria/{maquina['id']}", headers=cabeceras)
        assert respuesta.status_code == 409, respuesta.text
        assert "inspección" in respuesta.json()["detail"]
        # Y con una sola, el mensaje está en singular (la regla de la casa).
        assert "1 inspección" in respuesta.json()["detail"]

    def test_quitar_una_maquina_sin_nada_dentro_la_quita_con_su_rastro(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        declarar(cliente, cabeceras, maquina["id"], "itv")
        respuesta = cliente.delete(f"/api/maquinaria/{maquina['id']}", headers=cabeceras)
        assert respuesta.status_code == 200, respuesta.text
        assert cliente.get(f"/api/maquinaria/{maquina['id']}", headers=cabeceras).status_code == 404
        assert cliente.get("/api/maquinaria", headers=cabeceras).json()["total"] == 0

    def test_corregir_una_maquina_es_la_misma_ficha_y_lo_dice_la_auditoria(self, cliente, cuenta):
        cabeceras = cuenta["cabeceras"]
        maquina = crear_maquina(cliente, cabeceras)
        respuesta = cliente.put(
            f"/api/maquinaria/{maquina['id']}",
            headers=cabeceras,
            json={
                "nombre": "El Landini",
                "clase": "tractor",
                "propiedad": "propia",
                "disponibilidad": "no_disponible",
                "clasificacion_tecnica": "Tractor agrícola de ruedas",
                "matricula": "1234 ABC",
                "numero_roma": "ROMA-99",
                "horas": 2400,
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        corregida = respuesta.json()
        assert corregida["id"] == maquina["id"]
        assert corregida["clasificacion_tecnica"] == "Tractor agrícola de ruedas"
        assert corregida["numero_roma"] == "ROMA-99"

    def test_una_maquina_sin_nombre_se_rechaza_con_su_frase(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/maquinaria",
            headers=cuenta["cabeceras"],
            json={"nombre": "   ", "clase": "tractor", "propiedad": "propia", "disponibilidad": "no_se"},
        )
        assert respuesta.status_code == 422, respuesta.text
        assert "nombre" in respuesta.json()["detail"].lower()

    def test_una_clase_inventada_se_rechaza_con_su_frase(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/maquinaria",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "El trasto",
                "clase": "nave_espacial",
                "propiedad": "propia",
                "disponibilidad": "disponible",
            },
        )
        assert respuesta.status_code == 422
        assert "clase" in respuesta.json()["detail"]


# --------------------------------------------------------------------------
# 9. Los textos y lo que se sirve a la pantalla
# --------------------------------------------------------------------------


class TestLosTextosDeLaMaquinaria:
    def test_la_interfaz_sirve_las_cinco_obligaciones_con_su_nombre_y_su_explicacion(
        self, cliente, cuenta
    ):
        respuesta = cliente.get("/api/interfaz")
        assert respuesta.status_code == 200
        datos = respuesta.json()
        obligaciones = datos["obligaciones_de_una_maquina"]
        assert [una["valor"] for una in obligaciones] == list(maquinaria.OBLIGACIONES)
        for una in obligaciones:
            assert una["texto"] and una["que_es"], una
        # Y se distingue la ITV de la ITEAF, que es la confusión que el documento de la casa señala.
        assert "No es la ITV" in dict(
            (una["valor"], una["que_es"]) for una in obligaciones
        )["iteaf"]

    def test_la_interfaz_sirve_lo_que_el_programa_no_calcula(self, cliente, cuenta):
        datos = cliente.get("/api/interfaz").json()
        assert [lo["clave"] for lo in datos["maquinaria_que_falta"]]
        assert datos["maquinaria"]["titulo"]
        assert datos["clases_de_maquina"] and datos["disponibilidades_de_una_maquina"]
        assert datos["resultados_de_una_inspeccion"]

    def test_los_textos_de_la_maquinaria_pasan_el_test_de_jerga(self):
        visibles = textos.textos_visibles()
        for clave, texto in textos.MAQUINARIA_DE_LA_FINCA.items():
            assert texto in visibles, f"{clave} no se revisa"
        for clave, texto in textos.MENSAJES_DE_LA_MAQUINARIA.items():
            assert texto in visibles, f"{clave} no se revisa"
            assert not textos.palabras_prohibidas_encontradas(texto), clave

    def test_las_columnas_de_la_tabla_de_maquinaria_estan_dichas(self):
        for clave in (
            "maquinaria_etiqueta",
            "maquina",
            "tipo_maquina",
            "matricula_o_serie",
            "propiedad",
            "horas",
            "proxima_revision",
            "documentacion",
            "disponibilidad",
        ):
            assert textos.TABLA[clave]
