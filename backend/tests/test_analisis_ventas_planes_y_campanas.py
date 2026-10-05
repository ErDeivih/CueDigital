"""Borrar los análisis, las ventas, los planes, las medidas y las campañas (ronda 93).

LO QUE SE PRUEBA AQUÍ, Y POR QUÉ

David lo pidió con estas palabras: «recuerda también dejar borrar las cosas que introduzca porque
puede que me equivoque, o modificar también». La ronda 91 lo hizo con los apuntes del cuaderno, la
92 con las tierras y los grupos, y esta cierra lo que quedaba: los análisis de laboratorio, lo que
se ha vendido, el plan de abono del año, la declaración de medidas preventivas y las campañas.

Estas pruebas defienden lo mismo que las de las tierras, porque el problema es el mismo:

  1. **Borrar borra de verdad**: la cosa desaparece de su listado y de su informe, y el programa
     **sí sabe** que existió, porque queda entera en la auditoría (`correcciones`).
  2. **Lo que está en uso no se borra**, y no se contesta «no» a secas: se dice **cuántas cosas** lo
     usan y qué hay que hacer (409 con `textos.B5_en_uso` / `textos.B6_tiene_dentro`), y **no se
     borra nada** —ni la mitad de nada—.
  3. **Lo de otra finca contesta 404**, nunca 403: así no se filtra si un identificador existe.
  4. Y hay una prueba por cada decisión poco obvia de esta ronda: el análisis que está sosteniendo
     un plan, el plan con abonos enlazados, el abono que se echó en la parcela del plan sin
     enlazarlo, la campaña con cosas dentro, la campaña que se está llevando y el papel de la venta
     (que no existe: **las ventas no tienen fichero**, y eso se comprueba, no se supone).
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from sqlalchemy import select

from app import adjuntos, correcciones, models, textos
from app.routers import explotacion


def _auditoria(db, entidad: str, entidad_id: int, accion: str):
    """El rastro que ha dejado una corrección o un borrado."""
    return list(
        db.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == entidad,
                models.Auditoria.entidad_id == entidad_id,
                models.Auditoria.accion == accion,
            )
        )
    )


def _los_analisis(cliente, cabeceras) -> list[dict]:
    return cliente.get("/api/analiticas", headers=cabeceras).json()


def _las_ventas(cliente, cabeceras) -> list[dict]:
    return cliente.get("/api/ventas", headers=cabeceras).json()


def _los_planes(cliente, cabeceras) -> list[dict]:
    return cliente.get("/api/planes", headers=cabeceras).json()


def _las_campanas(cliente, cabeceras) -> list[dict]:
    return cliente.get("/api/campanas", headers=cabeceras).json()


def _la_declaracion(cliente, cabeceras) -> dict:
    return cliente.get("/api/medidas", headers=cabeceras).json()


@pytest.fixture
def crear_plan(cliente, cuenta, campana, parcela):
    """Un plan de abono completo y correcto, al que se le cambia lo que pruebe cada test.

    Son los mismos datos que manda la pantalla: sin cultivo, sin superficie y sin tierra, un plan
    no se puede guardar (`validaciones.validar_plan`), y aquí no se está probando eso.
    """

    def _crear(**cambios):
        datos = {
            "campana_id": campana["id"],
            "parcela_id": parcela["id"],
            "cultivo": "Trigo blando",
            "superficie_ha": 2.43,
            "necesidad_n": 100.0,
            "necesidad_p": 40.0,
            "necesidad_k": 60.0,
        }
        datos.update(cambios)
        respuesta = cliente.post("/api/planes", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


@pytest.fixture
def plan(crear_plan):
    return crear_plan()


@pytest.fixture
def crear_campana(cliente, cuenta):
    """Una campaña más, para poder corregirla y borrarla sin tocar la del año en curso.

    Los años se piden desde fuera y son siempre **relativos a la campaña que ya existe** (la del año
    en curso, que es la que crea el alta de la cuenta): así estas pruebas no dependen de en qué año
    se ejecuten, que es la forma más rápida de que una suite se ponga roja sola con el tiempo.
    """

    def _crear(anio: int, **cambios):
        datos = {"anio": anio, "fecha_inicio": f"{anio}-01-01", "fecha_fin": f"{anio}-12-31"}
        datos.update(cambios)
        respuesta = cliente.post("/api/campanas", headers=cuenta["cabeceras"], json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    return _crear


def _cuerpo_de_la_correccion(campana: dict, **cambios) -> dict:
    """Lo que se manda al corregir una campaña: lo mismo que devuelve la API, más los cambios.

    `cerrada` va siempre, y es a propósito (ver `schemas.CampanaCorreccion`): el formulario se
    rellena con lo que devuelve `CampanaSalida`, así que ese dato lo tiene en la mano, y omitirlo no
    puede significar «ábrela otra vez».
    """
    cuerpo = {
        "anio": campana["anio"],
        "fecha_inicio": campana["fecha_inicio"],
        "fecha_fin": campana["fecha_fin"],
        "cerrada": campana["cerrada"],
    }
    cuerpo.update(cambios)
    return cuerpo


# --------------------------------------------------------------------------
# Un análisis de laboratorio
# --------------------------------------------------------------------------


class TestUnAnalisis:
    def test_se_borra_y_desaparece_del_listado(self, cliente, cuenta, analitica):
        respuesta = cliente.delete(
            f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text
        assert _los_analisis(cliente, cuenta["cabeceras"]) == []
        assert (
            cliente.get(
                f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 404
        )

    def test_lo_borrado_queda_entero_en_el_rastro(self, cliente, cuenta, db_sesion, analitica):
        """El cuaderno no lo enseña y el programa sí sabe qué decía y qué día se borró.

        Se guarda el registro **entero**, números del boletín incluidos: si dentro de un año hay que
        explicar de dónde salió un abono, el análisis que se borró tiene que poder contarse.
        """
        cliente.delete(f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"])

        rastro = _auditoria(db_sesion, "analitica", analitica["id"], "borrar")
        assert len(rastro) == 1
        assert rastro[0].datos["tipo"] == "suelo"
        assert rastro[0].datos["laboratorio"] == "Laboratorio Agrario de Villamuriel"
        assert rastro[0].datos["numero_informe"] == "2026/0417"
        assert len(rastro[0].datos["parametros"]) == len(analitica["parametros"])
        assert rastro[0].fecha is not None

    def test_borrar_dos_veces_da_404_la_segunda(self, cliente, cuenta, analitica):
        assert (
            cliente.delete(
                f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 200
        )
        assert (
            cliente.delete(
                f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 404
        )

    def test_el_de_otra_finca_no_se_borra(self, cliente, cuenta, crear_cuenta, analitica):
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.delete(
            f"/api/analiticas/{analitica['id']}", headers=otro["cabeceras"]
        )

        assert respuesta.status_code == 404
        assert len(_los_analisis(cliente, cuenta["cabeceras"])) == 1

    def test_sin_entrar_no_se_borra(self, cliente, cuenta, analitica):
        assert cliente.delete(f"/api/analiticas/{analitica['id']}").status_code == 401

    def test_el_que_sostiene_un_plan_de_abono_no_se_borra(
        self, cliente, cuenta, db_sesion, analitica, crear_plan
    ):
        """EL CASO QUE JUSTIFICA ESTA COMPROBACIÓN.

        El plan guarda de qué análisis salió: es el papel que justifica los números que se van a
        echar. Si el análisis desapareciera, el plan seguiría diciendo que se apoya en él y no
        habría nada que enseñar: el cuaderno estaría justificando el abono con un papel que ya no
        está.
        """
        plan = crear_plan(analitica_id=analitica["id"])

        respuesta = cliente.delete(
            f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == textos.mensaje_con_cuenta("B5_en_uso", 1)
        # Y no se ha borrado nada: ni el análisis, ni el plan que se apoya en él.
        assert len(_los_analisis(cliente, cuenta["cabeceras"])) == 1
        guardado = cliente.get(f"/api/planes/{plan['id']}", headers=cuenta["cabeceras"]).json()
        assert guardado["analitica_id"] == analitica["id"]
        assert _auditoria(db_sesion, "analitica", analitica["id"], "borrar") == []

    def test_si_lo_usan_dos_planes_los_cuenta_todos(self, cliente, cuenta, analitica, crear_plan):
        """Dos planes del mismo análisis (dos tierras, por ejemplo) se cuentan los dos."""
        crear_plan(analitica_id=analitica["id"], cultivo="Trigo blando")
        crear_plan(analitica_id=analitica["id"], cultivo="Cebada")

        respuesta = cliente.delete(
            f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 409
        detalle = respuesta.json()["detail"]
        assert "2 apuntes" in detalle, detalle
        assert "corrige esto en vez de borrarlo" in detalle, detalle

    def test_cuando_el_plan_deja_de_apoyarse_en_el_analisis_ya_se_puede_borrar(
        self, cliente, cuenta, analitica, crear_plan
    ):
        """La salida que da el mensaje: corregir el plan para que no lo use, y después borrarlo."""
        plan = crear_plan(analitica_id=analitica["id"])
        cliente.put(
            f"/api/planes/{plan['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": plan["campana_id"],
                "parcela_id": plan["parcela_id"],
                "cultivo": plan["cultivo"],
                "superficie_ha": plan["superficie_ha"],
                "analitica_id": None,
            },
        )

        respuesta = cliente.delete(
            f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text
        assert _los_analisis(cliente, cuenta["cabeceras"]) == []

    def test_al_borrarlo_se_va_tambien_su_boletin_del_disco(
        self, cliente, cuenta, db_sesion, analitica
    ):
        """Dejar el PDF ahí sería basura del agricultor ocupando sitio para siempre.

        Es el mismo cuidado que tiene subir un boletín nuevo encima del viejo: el fichero que se
        deja de usar se borra. Y lo que había queda escrito en el rastro, con su nombre.
        """
        cliente.post(
            f"/api/analiticas/{analitica['id']}/informe",
            headers=cuenta["cabeceras"],
            files={"fichero": ("boletin.pdf", io.BytesIO(b"%PDF-1.4 hola"), "application/pdf")},
        )
        db_sesion.expire_all()
        ruta = db_sesion.scalar(
            select(models.Analitica).where(models.Analitica.id == analitica["id"])
        ).fichero_ruta
        assert ruta
        en_disco = adjuntos.carpeta_de_adjuntos() / ruta
        assert en_disco.is_file(), "el boletín se ha subido y no está donde dice la base de datos"

        cliente.delete(f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"])

        assert not en_disco.exists(), "el boletín se ha quedado en el disco, huérfano"
        rastro = _auditoria(db_sesion, "analitica", analitica["id"], "borrar")
        assert rastro[0].datos["fichero_nombre"] == "boletin.pdf"
        assert rastro[0].datos["fichero_ruta"] == ruta

    def test_un_analisis_sin_boletin_se_borra_igual(self, cliente, cuenta, analitica):
        """Casi todos los análisis no tienen papel subido: eso no puede impedir borrarlos."""
        assert analitica["fichero_nombre"] is None

        respuesta = cliente.delete(
            f"/api/analiticas/{analitica['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text


# --------------------------------------------------------------------------
# Lo que se ha vendido
# --------------------------------------------------------------------------


class TestUnaVenta:
    def test_se_borra_y_desaparece_del_listado_y_del_informe(
        self, cliente, cuenta, crear_venta
    ):
        venta = crear_venta()

        respuesta = cliente.delete(f"/api/ventas/{venta['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 200, respuesta.text
        assert _las_ventas(cliente, cuenta["cabeceras"]) == []
        informe = cliente.get("/api/ventas/informe", headers=cuenta["cabeceras"]).json()
        assert informe["cuantas"] == 0

    def test_lo_borrado_queda_entero_en_el_rastro(self, cliente, cuenta, db_sesion, crear_venta):
        """Con el producto, la cantidad, el comprador y el albarán: lo que hay que explicar."""
        venta = crear_venta()

        cliente.delete(f"/api/ventas/{venta['id']}", headers=cuenta["cabeceras"])

        rastro = _auditoria(db_sesion, "venta_cosecha", venta["id"], "borrar")
        assert len(rastro) == 1
        assert rastro[0].datos["producto"] == "Trigo blando"
        assert rastro[0].datos["cantidad"] == 42000.0
        assert rastro[0].datos["comprador"] == "Cooperativa Agrícola de Peñaranda"
        assert rastro[0].datos["numero_albaran"] == "ALB-2026-118"
        assert rastro[0].datos["parcela_id"] == venta["parcela_id"]

    def test_borrar_dos_veces_da_404_la_segunda(self, cliente, cuenta, crear_venta):
        venta = crear_venta()
        assert (
            cliente.delete(f"/api/ventas/{venta['id']}", headers=cuenta["cabeceras"]).status_code
            == 200
        )
        assert (
            cliente.delete(f"/api/ventas/{venta['id']}", headers=cuenta["cabeceras"]).status_code
            == 404
        )

    def test_la_de_otra_finca_no_se_borra(self, cliente, cuenta, crear_cuenta, crear_venta):
        venta = crear_venta()
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.delete(f"/api/ventas/{venta['id']}", headers=otro["cabeceras"])

        assert respuesta.status_code == 404
        assert len(_las_ventas(cliente, cuenta["cabeceras"])) == 1

    def test_sin_entrar_no_se_borra(self, cliente, cuenta, crear_venta):
        venta = crear_venta()
        assert cliente.delete(f"/api/ventas/{venta['id']}").status_code == 401

    def test_al_borrarla_lo_vendido_deja_de_contar(self, cliente, cuenta, crear_venta):
        """Es una venta apuntada de más: las cuentas del año tienen que dejar de contarla."""
        venta = crear_venta()
        antes = cliente.get("/api/ventas/resumen", headers=cuenta["cabeceras"]).json()
        assert antes["ventas"] == 1

        cliente.delete(f"/api/ventas/{venta['id']}", headers=cuenta["cabeceras"])

        despues = cliente.get("/api/ventas/resumen", headers=cuenta["cabeceras"]).json()
        assert despues["ventas"] == 0
        fila = next(f for f in despues["filas"] if f["que"] == textos.VENTA["vendido"])
        assert fila["kilos"] == 0

    def test_una_venta_anulada_tambien_se_puede_borrar(self, cliente, cuenta, crear_venta):
        """Anular y borrar son dos cosas, y las dos hacen falta.

        Anular deja la venta tachada, con su motivo, dentro del cuaderno —y por eso sigue ahí—.
        Borrar la quita: si el agricultor ya la había anulado y después se da cuenta de que aquello
        no pasó, tiene que poder dejar el año limpio.
        """
        venta = crear_venta()
        cliente.post(
            f"/api/ventas/{venta['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de comprador"},
        )

        respuesta = cliente.delete(f"/api/ventas/{venta['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 200, respuesta.text


# --------------------------------------------------------------------------
# El plan de abono del año
# --------------------------------------------------------------------------


class TestUnPlanDeAbono:
    def test_se_borra_y_desaparece_del_listado(self, cliente, cuenta, plan):
        respuesta = cliente.delete(f"/api/planes/{plan['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 200, respuesta.text
        assert _los_planes(cliente, cuenta["cabeceras"]) == []
        assert (
            cliente.get(
                f"/api/planes/{plan['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 404
        )

    def test_lo_borrado_queda_entero_en_el_rastro(
        self, cliente, cuenta, db_sesion, crear_plan, analitica
    ):
        """Con el cultivo, las hectáreas, las necesidades y el análisis en el que se apoyaba."""
        plan = crear_plan(analitica_id=analitica["id"])

        cliente.delete(f"/api/planes/{plan['id']}", headers=cuenta["cabeceras"])

        rastro = _auditoria(db_sesion, "plan_abonado", plan["id"], "borrar")
        assert len(rastro) == 1
        assert rastro[0].datos["cultivo"] == "Trigo blando"
        assert rastro[0].datos["superficie_ha"] == 2.43
        assert rastro[0].datos["necesidad_n"] == 100.0
        assert rastro[0].datos["analitica_id"] == analitica["id"]

    def test_borrar_dos_veces_da_404_la_segunda(self, cliente, cuenta, plan):
        assert (
            cliente.delete(f"/api/planes/{plan['id']}", headers=cuenta["cabeceras"]).status_code
            == 200
        )
        assert (
            cliente.delete(f"/api/planes/{plan['id']}", headers=cuenta["cabeceras"]).status_code
            == 404
        )

    def test_el_de_otra_finca_no_se_borra(self, cliente, cuenta, crear_cuenta, plan):
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.delete(f"/api/planes/{plan['id']}", headers=otro["cabeceras"])

        assert respuesta.status_code == 404
        assert len(_los_planes(cliente, cuenta["cabeceras"])) == 1

    def test_sin_entrar_no_se_borra(self, cliente, cuenta, plan):
        assert cliente.delete(f"/api/planes/{plan['id']}").status_code == 401

    def test_el_plan_con_abonos_apuntados_contra_el_no_se_borra(
        self, cliente, cuenta, db_sesion, campana, parcela, fertilizante, plan, nueva_fertilizacion
    ):
        """LA DECISIÓN DE ESTA PARTE, Y POR QUÉ.

        Un apunte de abono puede decir contra qué plan se echó, y eso es lo que contesta la pregunta
        que más se hace en una inspección: si lo que echaste estaba previsto o no. Si el plan
        desapareciera, ese apunte seguiría teniendo su abono y su cantidad —que es lo obligatorio—
        pero se quedaría sin decir contra qué previsión se echó.
        """
        abono = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(plan_id=plan["id"]),
        )
        assert abono.status_code == 201, abono.text

        respuesta = cliente.delete(f"/api/planes/{plan['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == textos.mensaje_con_cuenta("B5_en_uso", 1)
        # Y no se ha borrado nada: el plan sigue, y el abono sigue diciendo de qué plan salió.
        assert len(_los_planes(cliente, cuenta["cabeceras"])) == 1
        guardado = cliente.get("/api/fertilizaciones", headers=cuenta["cabeceras"]).json()[0]
        assert guardado["plan_id"] == plan["id"]
        assert _auditoria(db_sesion, "plan_abonado", plan["id"], "borrar") == []

    def test_dos_abonos_enlazados_se_cuentan_los_dos(
        self, cliente, cuenta, fertilizante, plan, nueva_fertilizacion
    ):
        for fecha in ("2026-02-20", "2026-03-20"):
            respuesta = cliente.post(
                "/api/fertilizaciones",
                headers=cuenta["cabeceras"],
                json=nueva_fertilizacion(plan_id=plan["id"], fecha=fecha),
            )
            assert respuesta.status_code == 201, respuesta.text

        respuesta = cliente.delete(f"/api/planes/{plan['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 409
        assert "2 apuntes" in respuesta.json()["detail"], respuesta.json()["detail"]
        assert len(_los_planes(cliente, cuenta["cabeceras"])) == 1

    def test_un_abono_echado_en_la_parcela_del_plan_sin_enlazarlo_no_lo_protege(
        self, cliente, cuenta, fertilizante, plan, nueva_fertilizacion
    ):
        """La otra mitad de la decisión, y conviene que esté escrita.

        Nadie se acuerda de enlazar cada abono a mano, así que el programa cuenta **todos** los
        abonos de la parcela para avisar de que te has pasado del plan. Pero un abono que no dice
        «este plan» no pierde nada porque el plan desaparezca: sigue diciendo lo que de verdad se
        echó, que es lo que el cuaderno tiene que guardar. Por eso no lo protege.
        """
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=nueva_fertilizacion(),
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["plan_id"] is None, "este abono no está enlazado a ningún plan"

        borrado = cliente.delete(f"/api/planes/{plan['id']}", headers=cuenta["cabeceras"])

        assert borrado.status_code == 200, borrado.text
        assert _los_planes(cliente, cuenta["cabeceras"]) == []
        # Y el abono sigue donde estaba: lo que se ha ido es la previsión, no lo que se echó.
        assert len(cliente.get("/api/fertilizaciones", headers=cuenta["cabeceras"]).json()) == 1

    def test_borrar_el_plan_no_se_lleva_el_analisis_en_el_que_se_apoyaba(
        self, cliente, cuenta, crear_plan, analitica
    ):
        """Un plan se apoya en un análisis; al revés no hay nada que sostener.

        Borrar la previsión no puede llevarse el boletín del laboratorio, que vale para varios años
        y para más cosas que ese plan.
        """
        plan = crear_plan(analitica_id=analitica["id"])

        cliente.delete(f"/api/planes/{plan['id']}", headers=cuenta["cabeceras"])

        assert len(_los_analisis(cliente, cuenta["cabeceras"])) == 1


# --------------------------------------------------------------------------
# La declaración de medidas preventivas
# --------------------------------------------------------------------------


class TestLasMedidasPreventivas:
    def test_se_quita_la_declaracion_y_la_finca_vuelve_a_estar_sin_declarar(
        self, cliente, cuenta, declarar_medidas
    ):
        declarar_medidas(["rotacion", "muestreo"])

        respuesta = cliente.delete("/api/medidas", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["declarada"] is False
        assert datos["cuantas"] == 0
        assert datos["aplicadas"] == []
        assert datos["mensaje"] == textos.MEDIDAS["sin_declarar"]
        assert all(medida["aplicada"] is False for medida in datos["medidas"])
        # Y siguen saliendo las diez preguntas: la pantalla tiene que poder volver a preguntar.
        assert len(datos["medidas"]) == 10
        assert _la_declaracion(cliente, cuenta["cabeceras"])["declarada"] is False

    def test_no_es_lo_mismo_que_decir_que_no_haces_ninguna(
        self, cliente, cuenta, declarar_medidas
    ):
        """LA DECISIÓN DE ESTA PARTE, Y ES LA RAZÓN DE QUE ESTE ENDPOINT EXISTA.

        El `PUT` con la lista vacía significa «he dicho que no hago ninguna»: es una respuesta, y el
        programa la guarda como tal (`declarada_ninguna`). El `DELETE` significa «todavía no he
        dicho nada»: la declaración no existe y el programa vuelve a preguntar (`sin_declarar`). Son
        dos cosas distintas, y ninguna se puede decir con la otra.
        """
        cliente.put(
            "/api/medidas", headers=cuenta["cabeceras"], json={"aplicadas": []}
        )
        dicho_que_ninguna = _la_declaracion(cliente, cuenta["cabeceras"])
        assert dicho_que_ninguna["declarada"] is True
        assert dicho_que_ninguna["mensaje"] == textos.MEDIDAS["declarada_ninguna"]

        cliente.delete("/api/medidas", headers=cuenta["cabeceras"])
        sin_declarar = _la_declaracion(cliente, cuenta["cabeceras"])
        assert sin_declarar["declarada"] is False
        assert sin_declarar["mensaje"] == textos.MEDIDAS["sin_declarar"]
        assert sin_declarar["mensaje"] != dicho_que_ninguna["mensaje"]

    def test_despues_se_puede_volver_a_declarar(self, cliente, cuenta, declarar_medidas):
        """Quitar la declaración no deja la pantalla bloqueada: se vuelve a marcar y ya está."""
        declarar_medidas(["rotacion"])
        cliente.delete("/api/medidas", headers=cuenta["cabeceras"])

        declaracion = declarar_medidas(["trampeo", "higiene"])

        assert declaracion["declarada"] is True
        assert set(declaracion["aplicadas"]) == {"trampeo", "higiene"}

    def test_lo_declarado_queda_en_el_rastro(self, cliente, cuenta, db_sesion, declarar_medidas):
        """Se borran las filas, y el programa **sí sabe** qué había declarado y qué día lo quitó.

        Se mira una marcada y una sin marcar: las dos se van, y las dos quedan escritas con lo que
        decían. Que se vayan también las no marcadas es la decisión que se explica en
        `medidas_api.quitar_la_declaracion`: no son un historial, son las preguntas de hoy que
        quedaron en blanco, y mientras existan la finca sigue «declarada».
        """
        declarar_medidas(["rotacion", "muestreo"], observaciones={"rotacion": "Cada tres años"})
        db_sesion.expire_all()
        filas = {
            fila.medida: fila
            for fila in db_sesion.scalars(select(models.MedidaPreventivaDeclarada))
        }
        assert filas["rotacion"].aplicada is True
        assert filas["muestreo"].aplicada is True
        assert filas["trampeo"].aplicada is False, (
            "el PUT deja una fila por cada medida del catálogo"
        )

        cliente.delete("/api/medidas", headers=cuenta["cabeceras"])

        rotacion = _auditoria(db_sesion, "medida_preventiva", filas["rotacion"].id, "borrar")
        assert len(rotacion) == 1
        assert rotacion[0].datos["medida"] == "rotacion"
        assert rotacion[0].datos["aplicada"] is True
        assert rotacion[0].datos["observaciones"] == "Cada tres años"
        assert rotacion[0].fecha is not None

        sin_marcar = _auditoria(db_sesion, "medida_preventiva", filas["trampeo"].id, "borrar")
        assert len(sin_marcar) == 1
        assert sin_marcar[0].datos["aplicada"] is False

    def test_no_queda_ninguna_fila_de_la_declaracion(
        self, cliente, cuenta, db_sesion, declarar_medidas
    ):
        """La finca está «sin declarar», y eso quiere decir que no queda ninguna fila.

        Se mira la tabla de verdad y no lo que devuelve la API a propósito: mientras quedara una
        sola fila —aunque estuviera sin marcar—, el listado seguiría diciendo que la finca está
        declarada, y el agricultor leería una frase que no ha dicho.
        """
        declarar_medidas(["rotacion"])

        cliente.delete("/api/medidas", headers=cuenta["cabeceras"])

        db_sesion.expire_all()
        assert db_sesion.scalars(select(models.MedidaPreventivaDeclarada)).all() == []

    def test_quitar_la_declaracion_dos_veces_no_rompe_nada(self, cliente, cuenta):
        """Aquí no hay identificador, así que la segunda vez no puede dar 404: no hay nada que
        quitar.

        Es distinto de borrar dos veces un análisis o una venta (esos sí dan 404 la segunda, porque
        el identificador ya no existe). `DELETE /api/medidas` no borra «una cosa»: deja la finca sin
        declaración, y volver a pedirlo deja la finca igual de sin declarar.
        """
        primera = cliente.delete("/api/medidas", headers=cuenta["cabeceras"])
        segunda = cliente.delete("/api/medidas", headers=cuenta["cabeceras"])

        assert primera.status_code == 200
        assert segunda.status_code == 200
        assert segunda.json()["declarada"] is False

    def test_no_toca_las_medidas_que_se_apuntaron_en_cada_tratamiento(
        self, cliente, cuenta, declarar_medidas, nuevo_tratamiento
    ):
        """Lo que se apuntó en un tratamiento es lo que pasó ese día, y eso no se toca.

        La declaración de la finca alimenta los tratamientos nuevos, pero no reescribe los que ya
        están: quitar la declaración no puede cambiar apuntes del cuaderno que ya se hicieron.
        """
        declarar_medidas(["rotacion", "muestreo"])
        tratamiento = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(medidas=["rotacion", "muestreo"]),
        ).json()

        cliente.delete("/api/medidas", headers=cuenta["cabeceras"])

        guardado = cliente.get(
            f"/api/tratamientos/{tratamiento['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert set(guardado["medidas"]) == {"rotacion", "muestreo"}

    def test_sin_entrar_no_se_quita_la_declaracion(self, cliente, cuenta, declarar_medidas):
        declarar_medidas(["rotacion"])

        assert cliente.delete("/api/medidas").status_code == 401
        assert _la_declaracion(cliente, cuenta["cabeceras"])["declarada"] is True

    def test_una_finca_no_quita_la_declaracion_de_la_otra(
        self, cliente, cuenta, crear_cuenta, declarar_medidas
    ):
        """Borrar la declaración es de la finca de quien lo pide, y de ninguna más."""
        declarar_medidas(["rotacion", "muestreo"])
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.delete("/api/medidas", headers=otro["cabeceras"])

        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["declarada"] is False, "la suya estaba sin declarar y sigue así"
        mia = _la_declaracion(cliente, cuenta["cabeceras"])
        assert mia["declarada"] is True
        assert set(mia["aplicadas"]) == {"rotacion", "muestreo"}


# --------------------------------------------------------------------------
# Las campañas
# --------------------------------------------------------------------------


class TestCorregirUnaCampana:
    def test_se_corrige_el_ano_y_las_fechas(self, cliente, cuenta, campana, crear_campana):
        """El caso que trajo esta ronda: un año mal escrito, o unas fechas que no son las del
        ciclo."""
        equivocada = crear_campana(anio=campana["anio"] + 1)
        buena = campana["anio"] - 1

        respuesta = cliente.put(
            f"/api/campanas/{equivocada['id']}",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_la_correccion(
                equivocada,
                anio=buena,
                fecha_inicio=f"{buena}-07-01",
                fecha_fin=f"{buena + 1}-06-30",
            ),
        )

        assert respuesta.status_code == 200, respuesta.text
        corregida = respuesta.json()
        assert corregida["id"] == equivocada["id"]
        assert corregida["anio"] == buena
        assert corregida["fecha_inicio"] == f"{buena}-07-01"
        assert corregida["fecha_fin"] == f"{buena + 1}-06-30"

    def test_corregir_no_crea_otra_campana(self, cliente, cuenta, campana, crear_campana):
        """El identificador es el mismo, y eso importa: de él cuelga **el año entero** apuntado.

        Si corregir creara otra campaña, todos los tratamientos, abonos, labores, análisis y ventas
        de ese año se quedarían colgando del año mal escrito, y el año bueno saldría vacío.
        """
        equivocada = crear_campana(anio=campana["anio"] + 1)
        buena = campana["anio"] - 1
        antes = len(_las_campanas(cliente, cuenta["cabeceras"]))

        cliente.put(
            f"/api/campanas/{equivocada['id']}",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_la_correccion(equivocada, anio=buena),
        )

        campanas = _las_campanas(cliente, cuenta["cabeceras"])
        assert len(campanas) == antes
        assert equivocada["id"] in [c["id"] for c in campanas]
        assert [c["id"] for c in campanas if c["anio"] == buena] == [equivocada["id"]]

    def test_lo_que_habia_queda_en_el_rastro(
        self, cliente, cuenta, db_sesion, campana, crear_campana
    ):
        """Corregir es cambiar **esa** campaña, y lo de antes queda escrito campo por campo."""
        equivocada = crear_campana(anio=campana["anio"] + 1)
        buena = campana["anio"] - 1

        cliente.put(
            f"/api/campanas/{equivocada['id']}",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_la_correccion(equivocada, anio=buena),
        )

        rastro = _auditoria(db_sesion, "campana", equivocada["id"], "corregir")
        assert len(rastro) == 1
        assert rastro[0].datos["anio"] == [equivocada["anio"], buena]
        assert rastro[0].fecha is not None

    def test_se_puede_cerrar_el_ano_y_volver_a_abrirlo(self, cliente, cuenta, campana):
        """`cerrada` es el dato que dice que el año se ha terminado; y se puede deshacer.

        Se puede volver a abrir a propósito: si al cerrar el año se quedó algo sin apuntar, la
        salida tiene que ser arreglarlo, no quedarse con un año cerrado a medias.
        """
        assert campana["cerrada"] is False

        cerrada = cliente.put(
            f"/api/campanas/{campana['id']}",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_la_correccion(campana, cerrada=True),
        ).json()
        assert cerrada["cerrada"] is True

        abierta = cliente.put(
            f"/api/campanas/{campana['id']}",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_la_correccion(cerrada, cerrada=False),
        ).json()
        assert abierta["cerrada"] is False

    def test_hay_que_decir_si_esta_cerrada_o_no(self, cliente, cuenta, campana, crear_campana):
        """Y no se puede omitir, y es una decisión: omitirla no puede abrir un año cerrado.

        El formulario se rellena con lo que devuelve la API, que incluye `cerrada`. Si el campo
        fuera opcional, corregir solo las fechas de un año cerrado lo **volvería a abrir** sin que
        nadie lo hubiera pedido, y eso es un cambio en el cuaderno que el agricultor no ha hecho.
        """
        otro_ano = crear_campana(anio=campana["anio"] + 1)
        cliente.put(
            f"/api/campanas/{otro_ano['id']}",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_la_correccion(otro_ano, cerrada=True),
        )

        respuesta = cliente.put(
            f"/api/campanas/{otro_ano['id']}",
            headers=cuenta["cabeceras"],
            json={
                "anio": campana["anio"] - 1,
                "fecha_inicio": otro_ano["fecha_inicio"],
                "fecha_fin": otro_ano["fecha_fin"],
            },
        )

        assert respuesta.status_code == 422
        en_lista = [
            c for c in _las_campanas(cliente, cuenta["cabeceras"]) if c["id"] == otro_ano["id"]
        ]
        assert en_lista[0]["cerrada"] is True, "la corrección rechazada no ha abierto el año"
        assert en_lista[0]["anio"] == otro_ano["anio"]

    def test_no_se_puede_corregir_a_un_ano_que_ya_esta_creado(
        self, cliente, cuenta, campana, crear_campana
    ):
        """No puede haber dos campañas con el mismo año: los apuntes no sabrían dónde ir.

        Se comprueba antes de guardar porque lo impide la base de datos (`uq_campana_anio`): sin
        esta comprobación el agricultor vería un fallo del programa en vez de que se lo digan.
        """
        otra = crear_campana(anio=campana["anio"] + 1)

        respuesta = cliente.put(
            f"/api/campanas/{otra['id']}",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_la_correccion(otra, anio=campana["anio"]),
        )

        assert respuesta.status_code == 409
        assert str(campana["anio"]) in respuesta.json()["detail"]
        en_lista = [c for c in _las_campanas(cliente, cuenta["cabeceras"]) if c["id"] == otra["id"]]
        assert en_lista[0]["anio"] == otra["anio"], "la campaña se ha quedado como estaba"

    def test_las_fechas_al_reves_se_rechazan(self, cliente, cuenta, campana, crear_campana):
        """La misma regla que al crear el año, porque es el mismo dato."""
        otro_ano = crear_campana(anio=campana["anio"] + 1)

        respuesta = cliente.put(
            f"/api/campanas/{otro_ano['id']}",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_la_correccion(
                otro_ano,
                fecha_inicio=f"{campana['anio']}-12-31",
                fecha_fin=f"{campana['anio']}-01-01",
            ),
        )

        assert respuesta.status_code == 422
        en_lista = [
            c for c in _las_campanas(cliente, cuenta["cabeceras"]) if c["id"] == otro_ano["id"]
        ]
        assert en_lista[0]["fecha_inicio"] == otro_ano["fecha_inicio"]

    def test_corregir_no_cambia_el_dia_en_que_se_creo_la_campana(
        self, cliente, cuenta, db_sesion, campana, crear_campana
    ):
        """«Cuándo se creó» no es un dato que se corrija, y hay que cuidarlo a mano.

        `correcciones` protege las columnas que no se corrigen nunca, y en su lista está
        `creado_en`; la de la campaña se llama `creada_en` —en femenino, como «la campaña»—, así que
        se le escapa. Sin copiarla, corregir el año de una campaña le pondría la fecha de creación
        en blanco y la base de datos no lo admitiría: la corrección fallaría con un fallo del
        programa en vez de decir nada. Es el mismo cuidado que se tuvo con las tierras.
        """
        otro_ano = crear_campana(anio=campana["anio"] + 1)
        db_sesion.expire_all()
        antes = db_sesion.scalar(
            select(models.Campana).where(models.Campana.id == otro_ano["id"])
        ).creada_en
        assert antes is not None

        respuesta = cliente.put(
            f"/api/campanas/{otro_ano['id']}",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_la_correccion(otro_ano, anio=campana["anio"] - 1),
        )
        assert respuesta.status_code == 200, respuesta.text

        db_sesion.expire_all()
        despues = db_sesion.scalar(
            select(models.Campana).where(models.Campana.id == otro_ano["id"])
        ).creada_en
        assert despues == antes

    def test_la_campana_de_otra_finca_no_se_toca(
        self, cliente, cuenta, crear_cuenta, campana, crear_campana
    ):
        otro_ano = crear_campana(anio=campana["anio"] + 1)
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.put(
            f"/api/campanas/{otro_ano['id']}",
            headers=otro["cabeceras"],
            json=_cuerpo_de_la_correccion(otro_ano, anio=campana["anio"] - 1),
        )

        assert respuesta.status_code == 404
        en_lista = [
            c for c in _las_campanas(cliente, cuenta["cabeceras"]) if c["id"] == otro_ano["id"]
        ]
        assert en_lista[0]["anio"] == otro_ano["anio"]

    def test_sin_entrar_no_se_corrige_ninguna_campana(
        self, cliente, cuenta, campana, crear_campana
    ):
        otro_ano = crear_campana(anio=campana["anio"] + 1)

        respuesta = cliente.put(
            f"/api/campanas/{otro_ano['id']}", json=_cuerpo_de_la_correccion(otro_ano)
        )

        assert respuesta.status_code == 401


class TestBorrarUnaCampana:
    def test_se_borra_la_que_esta_vacia(self, cliente, cuenta, campana, crear_campana):
        de_mas = crear_campana(anio=campana["anio"] + 1)
        antes = len(_las_campanas(cliente, cuenta["cabeceras"]))

        respuesta = cliente.delete(
            f"/api/campanas/{de_mas['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text
        despues = _las_campanas(cliente, cuenta["cabeceras"])
        assert len(despues) == antes - 1
        assert de_mas["id"] not in [c["id"] for c in despues]

    def test_lo_borrado_queda_entero_en_el_rastro(
        self, cliente, cuenta, db_sesion, campana, crear_campana
    ):
        """Con su año, sus fechas y si estaba cerrada: el programa sabe qué año se quitó."""
        de_mas = crear_campana(anio=campana["anio"] + 1)
        anio = de_mas["anio"]

        cliente.delete(f"/api/campanas/{de_mas['id']}", headers=cuenta["cabeceras"])

        rastro = _auditoria(db_sesion, "campana", de_mas["id"], "borrar")
        assert len(rastro) == 1
        assert rastro[0].datos["anio"] == anio
        assert rastro[0].datos["fecha_inicio"] == f"{anio}-01-01"
        assert rastro[0].datos["fecha_fin"] == f"{anio}-12-31"
        assert rastro[0].datos["cerrada"] is False
        assert rastro[0].fecha is not None

    def test_borrar_dos_veces_da_404_la_segunda(self, cliente, cuenta, campana, crear_campana):
        de_mas = crear_campana(anio=campana["anio"] + 1)
        assert (
            cliente.delete(
                f"/api/campanas/{de_mas['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 200
        )
        assert (
            cliente.delete(
                f"/api/campanas/{de_mas['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 404
        )

    def test_la_campana_de_otra_finca_no_se_borra(
        self, cliente, cuenta, crear_cuenta, campana, crear_campana
    ):
        de_mas = crear_campana(anio=campana["anio"] + 1)
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.delete(
            f"/api/campanas/{de_mas['id']}", headers=otro["cabeceras"]
        )

        assert respuesta.status_code == 404
        assert de_mas["id"] in [c["id"] for c in _las_campanas(cliente, cuenta["cabeceras"])]

    def test_sin_entrar_no_se_borra_ninguna_campana(self, cliente, cuenta, campana, crear_campana):
        de_mas = crear_campana(anio=campana["anio"] + 1)
        assert cliente.delete(f"/api/campanas/{de_mas['id']}").status_code == 401

    def test_la_que_tiene_apuntes_dentro_no_se_borra(
        self, cliente, cuenta, db_sesion, campana, crear_campana, parcela, producto
    ):
        """Borrarla se llevaría por delante el cuaderno de ese año, y eso no puede pasar.

        Es el año entero: los tratamientos, los abonos, las labores, las cosechas, el cultivo
        declarado, los análisis, las ventas y los planes apuntan a la campaña por su identificador.
        """
        de_mas = crear_campana(anio=campana["anio"] + 1)
        apunte = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": de_mas["id"],
                "fecha": f"{de_mas['anio']}-05-05",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 2.43,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert apunte.status_code == 201, apunte.text

        respuesta = cliente.delete(
            f"/api/campanas/{de_mas['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == textos.MENSAJES["B6_tiene_dentro_uno"]
        # Y no se ha borrado nada: la campaña sigue y el apunte sigue dentro de ella.
        assert de_mas["id"] in [c["id"] for c in _las_campanas(cliente, cuenta["cabeceras"])]
        guardado = cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()[0]
        assert guardado["campana_id"] == de_mas["id"]
        assert _auditoria(db_sesion, "campana", de_mas["id"], "borrar") == []

    def test_lo_que_hay_dentro_se_cuenta_de_todas_las_tablas(
        self, cliente, cuenta, campana, crear_campana, parcela, producto, crear_plan
    ):
        """La cuenta no se queda en una tabla: suma todo lo que hay apuntado en ese año.

        Se apuntan cuatro cosas de cuatro tablas distintas (un tratamiento, una labor, una venta y
        un plan) para comprobar que se cuentan las cuatro. Nunca se sabe por dónde va a empezar el
        agricultor a vaciar el año, y decirle «hay 1 cosa» cuando hay cuatro sería mentirle.
        """
        de_mas = crear_campana(anio=campana["anio"] + 1)
        anio = de_mas["anio"]
        cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": de_mas["id"],
                "fecha": f"{anio}-05-05",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 2.43,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": de_mas["id"],
                "tipo": "labrar",
                "fecha": f"{anio}-03-15",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
            },
        )
        cliente.post(
            "/api/ventas",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": de_mas["id"],
                "tipo": "comercializada",
                "fecha": f"{anio}-07-10",
                "producto": "Trigo blando",
                "cantidad": 1000.0,
                "unidad": "kg",
                "parcela_id": parcela["id"],
            },
        )
        crear_plan(campana_id=de_mas["id"])

        respuesta = cliente.delete(
            f"/api/campanas/{de_mas['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 409
        detalle = respuesta.json()["detail"]
        assert "4 cosas" in detalle, detalle
        assert "Bórralas o cámbialas de sitio antes" in detalle, detalle

    def test_el_aviso_de_lo_que_hay_dentro_lleva_la_cuenta(self):
        """El aviso del plural, comprobado aparte, porque aquí hubo un fallo escondido de verdad.

        **Lo que pasaba**: el texto del plural de `B6` estaba escrito con el hueco `{cuantas}` y el
        ayudante del programa (`textos.mensaje_con_cuenta`) rellena `{cuantos}`. Con **una** cosa dentro
        no se notaba —el texto del singular no lleva hueco—, pero con dos o más la llamada reventaba con
        `KeyError`: borrar una campaña con el año lleno habría dado **un fallo del programa en vez del
        aviso con su cuenta**. Lo encontró la prueba del apartado de arriba, y durante un rato el router
        lo esquivó componiendo el texto a mano.

        **Lo que se hizo**: se corrigió el texto (`{cuantas}` → `{cuantos}`) y el router volvió a usar el
        ayudante de siempre, que es lo que hace el resto del programa. Esta prueba defiende las dos
        cosas: que el aviso sale con su número y que **hay un solo camino** para contar cosas —si alguien
        vuelve a escribir un texto de cuenta con el hueco equivocado, esto falla—.
        """
        from app.routers import explotacion

        assert explotacion._mensaje_de_lo_que_hay_dentro(2) == textos.mensaje_con_cuenta(
            "B6_tiene_dentro", 2
        )
        assert "2 cosas" in explotacion._mensaje_de_lo_que_hay_dentro(2)
        assert "4 cosas" in explotacion._mensaje_de_lo_que_hay_dentro(4)
        assert explotacion._mensaje_de_lo_que_hay_dentro(1) == (
            textos.MENSAJES["B6_tiene_dentro_uno"]
        )

    def test_la_campana_que_se_esta_llevando_no_se_borra_si_tiene_algo_dentro(
        self, cliente, cuenta, campana, parcela, producto
    ):
        """La del año en curso es la que devuelve `/api/campanas/actual`, y no se puede tirar.

        Es el año en el que la aplicación apunta todo lo que no dice el año: si desapareciera con el
        cuaderno dentro, se perdería el año que se está llevando, que es justo lo que mira una
        inspección. Se contesta con la cuenta de lo que hay dentro, como en cualquier otra campaña.
        """
        actual = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        assert actual["id"] == campana["id"]
        cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": f"{campana['anio']}-05-05",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 2.43,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )

        respuesta = cliente.delete(
            f"/api/campanas/{campana['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == textos.MENSAJES["B6_tiene_dentro_uno"]
        sigue = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        assert sigue["id"] == campana["id"]

    def test_la_campana_vacia_de_mas_se_puede_borrar_y_la_actual_es_la_de_antes(
        self, cliente, cuenta, campana, crear_campana
    ):
        """DECISIÓN QUE CONVIENE LEER ENTERA: la campaña vacía del año que se está llevando se
        borra.

        La protección de verdad es la de arriba —con algo dentro no se borra, y eso incluye a la
        del año en curso—. Pero **vacía sí se puede borrar**, y es a propósito: es la única forma
        que hay de deshacer un año creado por error o de más. `PUT` no puede fundir dos años en uno
        (no puede haber dos campañas con el mismo año), así que si no se pudiera borrar, ese año de
        más se quedaría como «el año que estás llevando» para siempre, y en cuanto se apuntara algo
        dentro ya no habría ninguna forma de quitarlo. Bloquearlo cambiaría un error corregible por
        un error para siempre.

        Al borrarlo, la aplicación pasa a llevar el año anterior, que es un año de verdad y que sale
        en pantalla al lado del saludo. Está contado en el informe de la ronda: si se quiere impedir
        del todo, hace falta un texto nuevo en `textos.py` que diga por qué (los que hay contarían
        «0 apuntes» y eso sería mentirle al agricultor).
        """
        de_mas = crear_campana(anio=campana["anio"] + 1)
        actual = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        assert actual["id"] == de_mas["id"], "la de más es la que se está llevando ahora"

        respuesta = cliente.delete(
            f"/api/campanas/{de_mas['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text
        actual = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        assert actual["id"] == campana["id"]
        assert actual["anio"] == campana["anio"]

    def test_si_se_borra_el_unico_ano_se_puede_volver_a_crear(
        self, cliente, cuenta, campana
    ):
        """Lo peor que puede pasar al borrar la última campaña, comprobado: se vuelve a crear.

        Borrar la única campaña deja la finca como una recién dada de alta: `GET
        /api/campanas/actual` contesta con el mensaje que ya existe («todavía no hay ningún año
        creado») y los apuntes piden un año. Y `POST /api/campanas` lo vuelve a crear, así que no se
        pierde nada que no se pueda recuperar en un paso.
        """
        assert (
            cliente.delete(
                f"/api/campanas/{campana['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 200
        )
        assert _las_campanas(cliente, cuenta["cabeceras"]) == []
        assert cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).status_code == 404

        otra_vez = cliente.post(
            "/api/campanas",
            headers=cuenta["cabeceras"],
            json={
                "anio": campana["anio"],
                "fecha_inicio": campana["fecha_inicio"],
                "fecha_fin": campana["fecha_fin"],
            },
        )

        assert otra_vez.status_code == 201, otra_vez.text
        assert cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).status_code == 200


# --------------------------------------------------------------------------
# La cuenta y las rutas: lo que hace que esto no se estropee con el tiempo
# --------------------------------------------------------------------------


class TestLoQueDiceElAnoQueTieneDentro:
    """/api/campanas cuenta lo que hay dentro de cada año **dicho por lo que es** (30/09/2026).

    POR QUÉ EXISTE ESTA PRUEBA, CON EL FALLO QUE LA TRAJO. La pantalla de los años decía «Tiene 54 cosas
    apuntadas dentro» del 2026 y «mi cuaderno», del mismo año, decía «0 apuntes en el cuaderno». Las dos
    cosas eran verdad —las 54 eran las tierras con su cultivo dicho, que también cuelgan del año— y el
    agricultor no podía entenderlo. Se vio en la revisión de la interfaz del 30/09/2026, mirando la
    aplicación con sus 64 tierras de verdad.

    Lo que se comprueba aquí es que el servidor manda los tres números separados y que **suman el total**
    (que es el que impide borrar el año).
    """

    def test_el_desglose_suma_el_total(
        self, cliente, cuenta, campana, crear_campana, parcela, producto, crear_plan
    ):
        de_mas = crear_campana(anio=campana["anio"] + 1)
        anio = de_mas["anio"]
        # Dos apuntes del cuaderno (un producto y una labor), una venta, un plan y el cultivo de la tierra.
        for ruta, cuerpo in (
            (
                "/api/tratamientos",
                {
                    "fecha": f"{anio}-05-05",
                    "superficie_tratada_ha": 2.43,
                    "justificacion": "Vi la plaga o la hierba en el campo",
                    "producto_id": producto["id"],
                    "dosis": 0.5,
                },
            ),
            (
                "/api/labores",
                {
                    "tipo": "labrar",
                    "fecha": f"{anio}-03-15",
                    "superficie_ha": 2.43,
                },
            ),
            (
                "/api/ventas",
                {
                    "tipo": "comercializada",
                    "fecha": f"{anio}-07-10",
                    "producto": "Trigo blando",
                    "cantidad": 1000.0,
                    "unidad": "kg",
                },
            ),
        ):
            respuesta = cliente.post(
                ruta,
                headers=cuenta["cabeceras"],
                json={"campana_id": de_mas["id"], "parcela_id": parcela["id"], **cuerpo},
            )
            assert respuesta.status_code == 201, respuesta.text
        crear_plan(campana_id=de_mas["id"])
        cultivo = cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={"campana_id": de_mas["id"], "especie": "TRIGO BLANDO", "sistema": "secano"},
        )
        assert cultivo.status_code == 201, cultivo.text

        suya = next(una for una in _las_campanas(cliente, cuenta["cabeceras"]) if una["id"] == de_mas["id"])

        # Los tres números, cada uno por lo que es: los apuntes del cuaderno son el producto y la labor.
        assert suya["apuntes"] == 2, suya
        assert suya["tierras_con_cultivo"] == 1, suya
        assert suya["otras_cosas"] == 2, suya  # la venta y el plan
        # Y **suman el total**, que es lo que decide si el año se puede quitar.
        assert suya["cuantas_cosas"] == 5, suya
        assert (
            suya["apuntes"] + suya["tierras_con_cultivo"] + suya["otras_cosas"]
            == suya["cuantas_cosas"]
        )

    def test_un_ano_sin_nada_dentro_dice_cero_apuntes(
        self, cliente, cuenta, campana, crear_campana, parcela
    ):
        """Un año vacío tiene los cuatro números en cero, y eso **no es un dato inventado**: se ha contado."""
        vacia = crear_campana(anio=campana["anio"] + 2)
        suya = next(
            una for una in _las_campanas(cliente, cuenta["cabeceras"]) if una["id"] == vacia["id"]
        )
        assert suya["cuantas_cosas"] == 0
        assert suya["apuntes"] == 0
        assert suya["tierras_con_cultivo"] == 0
        assert suya["otras_cosas"] == 0

    def test_el_cultivo_de_una_tierra_no_es_un_apunte(
        self, cliente, cuenta, campana, parcela
    ):
        """**El caso que trajo todo esto**: un año con las tierras dichas y ningún apunte.

        Es la situación de la cuenta de David (64 tierras con su cultivo y 0 apuntes), y la que hacía que la
        pantalla dijera «54 cosas apuntadas dentro» mientras el cuaderno decía «0 apuntes».
        """
        cultivo = cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={"campana_id": campana["id"], "especie": "CEBADA", "sistema": "secano"},
        )
        assert cultivo.status_code == 201, cultivo.text

        suya = next(
            una for una in _las_campanas(cliente, cuenta["cabeceras"]) if una["id"] == campana["id"]
        )
        assert suya["apuntes"] == 0, f"el cultivo de una tierra se está contando como apunte: {suya}"
        assert suya["tierras_con_cultivo"] == 1
        assert suya["cuantas_cosas"] == 1
        # Y el guardián del borrado sigue contando esa cosa: el año no se puede quitar de golpe.
        respuesta = cliente.delete(f"/api/campanas/{campana['id']}", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 409


class TestLoQueSeCuentaAntesDeBorrar:
    """Las cuentas se sacan de la base de datos, y estas pruebas las mantienen honestas."""

    def test_las_tablas_que_apuntan_a_un_analisis_y_a_un_plan_son_las_de_hoy(self):
        """Si mañana algo más apunta a un análisis o a un plan, esta prueba avisa.

        Sin ella, la cuenta se quedaría corta en silencio: borrar un análisis que sostiene dos cosas
        solo contaría una, y el agricultor leería «1 apunte» cuando hay dos.
        """
        assert [
            modelo.__tablename__ for modelo in correcciones.tablas_que_apuntan_a("analitica_id")
        ] == ["planes_abonado"]
        assert [
            modelo.__tablename__ for modelo in correcciones.tablas_que_apuntan_a("plan_id")
        ] == ["fertilizaciones"]

    def test_las_tablas_que_apuntan_a_una_campana_son_las_de_hoy(self):
        """Las trece que hay hoy, por su nombre: es el año entero del cuaderno.

        **Y no están las dos del almacén** (`recepciones` y `movimientos_de_existencias`), y eso es
        una decisión, no un olvido: el libro del almacén (T09, 03/10/2026) **no cuelga del año** a
        propósito, porque no es un apunte del cuaderno y las tres listas de `explotacion.py` no lo
        reconocerían (caería en «otras cosas» sin decirlo). La campaña de una compra la guarda su
        factura y la de un consumo su apunte, y el libro se busca por fechas. El porqué entero, con lo
        que se probó, está en `models.MovimientoDeExistencias`, y hay una prueba que lo fija
        (`tests/test_recepciones_lotes_y_movimientos.py::test_el_almacen_no_cuelga_del_ano`).

        **La duodécima es `versiones_de_recinto`** (T05, 02/10/2026): la versión del recinto de cada
        tierra en cada campaña. Sí cuelga del año —una versión **es** de un año, y por eso se puede
        comparar con la de otro—, así que entra en esta lista y está clasificada en `OTRAS_COSAS` de
        `explotacion.py`: no es un apunte del cuaderno ni una tierra con su cultivo dicho, es la
        ficha de qué era esa tierra ese año. Y cuenta para el total, porque borrar el año se llevaría
        por delante la historia de sus recintos.

        **Y la decimotercera es `facturas_emitidas`** (T12, E6, 03/10/2026), que es lo que esta prueba
        pidió al añadirla: la factura nuestra de lo vendido sí cuelga del año —se emite para una
        campaña, y así la pantalla de los años la cuenta y no borra un año que tiene facturas sin
        decirlo— y está clasificada en `OTRAS_COSAS`. **El cobro NO está aquí, y también es una
        decisión**: el dinero entra un día y salda una factura, que es quien tiene la campaña; el
        porqué entero está en `models.Cobro`, y su prueba en `test_el_dinero_de_las_ventas.py`.

        **Y las cuatro de las cuentas** (T13, E7, 05/10/2026), que son las que esta prueba pidió al
        integrarlas: `gastos`, `inversiones_de_la_finca`, `repartos_de_coste` y `subvenciones`. Las
        cuatro cuelgan del año a propósito —un gasto es de la campaña en la que se consumió, una
        inversión es una compra de ese año y su reparto a la campaña se perdería con él, un reparto es
        a dónde fue cada trozo y una ayuda se pide y se cobra en un año— y las cuatro están
        clasificadas en `OTRAS_COSAS`. **El pago (`pagos_de_gasto`) NO está aquí, y es la misma
        decisión que con el cobro**: el dinero sale un día y salda un gasto, y es el gasto quien tiene
        la campaña; colgarlo del año obligaría a decidir de qué año es un pago de enero que salda la
        compra de diciembre, y esa decisión no la tiene el programa (`models.PagoDeGasto`).
        """
        assert [
            modelo.__tablename__ for modelo in correcciones.tablas_que_apuntan_a("campana_id")
        ] == [
            "analiticas",
            "documentos_anexos",
            "facturas",
            "facturas_emitidas",
            "fertilizaciones",
            "firmas",
            "gastos",
            "grupos_parcelas",
            "inversiones_de_la_finca",
            "labores",
            "parcela_cultivos",
            "planes_abonado",
            "repartos_de_coste",
            "subvenciones",
            "tratamientos",
            "ventas_de_cosecha",
            "versiones_de_recinto",
        ]

    def test_todas_las_tablas_del_ano_estan_clasificadas(self):
        """**Cada tabla que cuelga del año tiene que estar dicha en una de las tres listas** (30/09/2026).

        POR QUÉ EXISTE, CON EL FALLO QUE LA TRAJO. El año decía «Tiene 42 cosas apuntadas dentro» y el
        cuaderno del mismo año decía «0 apuntes en el cuaderno»: las dos eran verdad (las 42 eran las tierras
        con su cultivo dicho) y el agricultor no podía entenderlo. La pantalla ahora cuenta **tres cosas**
        (`APUNTES_DEL_CUADERNO`, `TIERRAS_CON_CULTIVO`, `OTRAS_COSAS`), y lo que no esté nombrado cae en
        «otras cosas» **en silencio**: contaría de más sin que nadie se entere. Esta prueba es la que avisa.

        Es la misma lección que la prueba de arriba (las tablas que apuntan a una campaña), aplicada a la
        clasificación: el día que se añada la duodécima tabla, esto falla y obliga a decidir qué es.
        """
        clasificadas = (
            set(explotacion.APUNTES_DEL_CUADERNO)
            | set(explotacion.TIERRAS_CON_CULTIVO)
            | set(explotacion.OTRAS_COSAS)
        )
        sin_clasificar = sorted(
            modelo.__name__
            for modelo in correcciones.tablas_que_apuntan_a("campana_id")
            if modelo.__name__ not in clasificadas
        )
        assert sin_clasificar == [], (
            "estas tablas cuelgan del año y no están en ninguna de las tres listas, así que se contarían "
            f"como «otras cosas» sin decirlo: {sin_clasificar}"
        )
        # Y al revés: nada nombrado que ya no exista (una tabla renombrada dejaría el nombre viejo aquí).
        existentes = {
            modelo.__name__ for modelo in correcciones.tablas_que_apuntan_a("campana_id")
        }
        sobran = sorted(clasificadas - existentes)
        assert sobran == [], f"estos nombres ya no son tablas que cuelguen del año: {sobran}"

    def test_los_apuntes_son_los_que_cuenta_el_cuaderno(self):
        """Los apuntes de un año son **tratamientos, abonos y labores**, y esos tres son lo que enseña el
        cuaderno. Si algún día se añadiera un cuarto tipo de apunte, tiene que entrar aquí a la vez.

        Es la decisión que hace que los dos números (el de la pantalla de los años y el de «mi cuaderno») no
        puedan contradecirse, que es lo que se arregló el 30/09/2026.
        """
        assert set(explotacion.APUNTES_DEL_CUADERNO) == {
            "TratamientoFitosanitario",
            "RegistroFertilizacion",
            "Labor",
        }
        # Y las tierras con su cultivo dicho son su tabla, que es la única que no es un apunte ni «otra cosa».
        assert set(explotacion.TIERRAS_CON_CULTIVO) == {"ParcelaCultivo"}

    def test_lo_que_apunta_a_una_venta_es_lo_que_el_t12_le_colgo(self):
        """Lo que apunta a una venta, comprobado y no supuesto (T12, 03/10/2026).

        ESTA PRUEBA DECÍA LO CONTRARIO, Y SE CAMBIA CON EL MOTIVO ESCRITO. Antes exigía que la lista
        de tablas que apuntan a `venta_id` estuviera **vacía**, y su propio texto lo decía: «el día
        que una tabla nueva apunte a una venta esta prueba falla y obliga a decidir». Ese día es hoy,
        y ha hecho exactamente su trabajo: el T12 le ha colgado dos cosas, y obliga a decidir qué se
        hace con cada una. Decidido, y está en `routers/ventas_api.borrar_venta`:

          · **`lineas_de_factura_emitida`** — la entrega dentro de una factura nuestra. Mientras la
            factura viva, **la entrega no se puede borrar** (409, y se dice en qué factura está): si
            se borrara, la factura seguiría contando un dinero cuya entrega ya no existe.
          · **`ajustes_de_entrega`** — las devoluciones y los ajustes de peso, humedad o calidad.
            **Se van con la entrega**, y cada uno deja su propio rastro en la auditoría: son parte de
            ella (una devolución sin la entrega no significa nada) y borrarlos de uno en uno sería
            pedirle al agricultor que deshaga su error en tres pasos.

        Y la segunda mitad sigue igual de cierta y por eso se queda: **la tabla de la entrega no tiene
        columnas de fichero**, así que borrarla no borra ningún papel. Lo que sí puede tener fichero
        es **un ajuste suyo** (la foto del básculero), y por eso `borrar_venta` ahora borra del disco
        lo que haya: si no, quedarían papeles del agricultor —con su nombre y su NIF— en la carpeta
        de adjuntos sin que nada los nombre.
        """
        assert [
            modelo.__tablename__ for modelo in correcciones.tablas_que_apuntan_a("venta_id")
        ] == ["ajustes_de_entrega", "lineas_de_factura_emitida"]
        assert not [
            columna
            for columna in correcciones.campos_corregibles(models.VentaDeCosecha)
            if "fichero" in columna
        ], "una venta ha empezado a tener fichero: hay que borrarlo del disco al borrar la venta"

        from app.main import app

        publicadas = {
            (metodo.upper(), ruta)
            for ruta, metodos in app.openapi()["paths"].items()
            for metodo in metodos
        }
        assert ("POST", "/api/ventas/{venta_id}/fichero") not in publicadas


class TestLaListaDeRutasNoSeHaRoto:
    """Borrar y corregir **se añaden**: nada de lo que ya había puede desaparecer por el camino."""

    def test_las_rutas_de_siempre_siguen_ahi(self):
        """Se mira la lista de rutas que publica la aplicación, no una respuesta.

        Así esta prueba caza una ruta que se pierda aunque su pantalla no se use en ninguna otra
        prueba del fichero. Se lee del esquema que la aplicación publica (`/openapi.json`) y no de
        `app.routes` porque los routers se incluyen en diferido y ahí solo se ven los envoltorios,
        no las rutas de dentro.
        """
        from app.main import app

        publicadas = {
            (metodo.upper(), ruta)
            for ruta, metodos in app.openapi()["paths"].items()
            for metodo in metodos
        }
        de_siempre = {
            ("GET", "/api/campanas"),
            ("POST", "/api/campanas"),
            ("GET", "/api/campanas/actual"),
            ("GET", "/api/analiticas"),
            ("POST", "/api/analiticas"),
            ("GET", "/api/analiticas/informe"),
            ("PUT", "/api/analiticas/{analitica_id}"),
            ("POST", "/api/analiticas/{analitica_id}/anular"),
            ("GET", "/api/analiticas/{analitica_id}/informe"),
            ("GET", "/api/ventas"),
            ("POST", "/api/ventas"),
            ("GET", "/api/ventas/informe"),
            ("GET", "/api/ventas/resumen"),
            ("PUT", "/api/ventas/{venta_id}"),
            ("POST", "/api/ventas/{venta_id}/anular"),
            ("GET", "/api/planes"),
            ("POST", "/api/planes"),
            ("PUT", "/api/planes/{plan_id}"),
            ("GET", "/api/planes/{plan_id}/resumen"),
            ("GET", "/api/medidas"),
            ("PUT", "/api/medidas"),
            ("GET", "/api/medidas/informe"),
            ("POST", "/api/medidas/validar"),
        }
        assert de_siempre <= publicadas, f"faltan rutas de antes: {sorted(de_siempre - publicadas)}"

        assert {
            ("PUT", "/api/campanas/{campana_id}"),
            ("DELETE", "/api/campanas/{campana_id}"),
            ("DELETE", "/api/analiticas/{analitica_id}"),
            ("DELETE", "/api/ventas/{venta_id}"),
            ("DELETE", "/api/planes/{plan_id}"),
            ("DELETE", "/api/medidas"),
        } <= publicadas, "faltan las rutas nuevas"

    def test_el_alta_y_el_listado_contestan_lo_mismo_que_antes(
        self, cliente, cuenta, campana, crear_campana, crear_venta, analitica, plan
    ):
        """Lo que ya hacían sigue haciéndolo igual: esto es añadir, no cambiar."""
        anterior = crear_campana(anio=campana["anio"] - 2)
        assert anterior["anio"] == campana["anio"] - 2
        assert anterior["cerrada"] is False
        assert anterior["fecha_inicio"] == f"{anterior['anio']}-01-01"

        venta = crear_venta()
        assert venta["producto"] == "Trigo blando"
        assert venta["cantidad"] == 42000.0

        assert len(_los_analisis(cliente, cuenta["cabeceras"])) == 1
        assert analitica["tipo"] == "suelo"
        assert len(_los_planes(cliente, cuenta["cabeceras"])) == 1
        assert plan["cultivo"] == "Trigo blando"
