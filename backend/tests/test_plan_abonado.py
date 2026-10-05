"""Tests del plan de abono del año, y del camino para actualizar sin perder datos.

Dos cosas se comprueban aquí:

1. **El plan y su comparación con lo que de verdad se ha echado.** Un plan sin saber si
   se está cumpliendo es un papel guardado en un cajón. Y lo que importa de verdad es
   que el programa avise cuando alguien se pasa de lo que tenía previsto.
2. **Que actualizar el programa sobre una base de datos con datos no reviente.** Ese
   fallo ya apareció una vez: `create_all` crea tablas nuevas pero no añade columnas a
   las que ya existen, y el agricultor se queda con un «no such column» y sin poder
   entrar.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text

from app import database


@pytest.fixture
def plan(cliente, cuenta, campana, parcela):
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


def abonar(cliente, cuenta, campana, parcela, fertilizante, **cambios):
    datos = {
        "campana_id": campana["id"],
        "fecha": "2026-02-20",
        "parcela_id": parcela["id"],
        "superficie_ha": 2.43,
        "fertilizante_id": fertilizante["id"],
        "kg_ha_producto": 300.0,
    }
    datos.update(cambios)
    return cliente.post("/api/fertilizaciones", headers=cuenta["cabeceras"], json=datos)


class TestElPlan:
    def test_se_hace_el_plan(self, plan):
        creado = plan()
        assert creado["cultivo"] == "Trigo blando"
        assert creado["necesidad_n"] == 100.0
        assert creado["superficie_ha"] == 2.43

    def test_se_lista_con_lo_que_llevas(self, cliente, cuenta, plan):
        plan()
        listado = cliente.get("/api/planes", headers=cuenta["cabeceras"]).json()
        assert len(listado) == 1
        assert listado[0]["aplicado_n"] == 0
        assert listado[0]["queda_n"] == 100.0

    def test_sin_planes_la_lista_esta_vacia(self, cliente, cuenta):
        assert cliente.get("/api/planes", headers=cuenta["cabeceras"]).json() == []

    def test_un_plan_se_puede_corregir(self, cliente, cuenta, plan):
        """Es una previsión, no un apunte: si cambia el tiempo, el plan se ajusta."""
        creado = plan()
        respuesta = cliente.put(
            f"/api/planes/{creado['id']}",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": creado["campana_id"],
                "parcela_id": creado["parcela_id"],
                "cultivo": "Trigo blando",
                "superficie_ha": 2.43,
                "necesidad_n": 80.0,
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["necesidad_n"] == 80.0

    def test_se_guarda_con_que_se_hizo_el_plan(self, cliente, cuenta, campana, parcela):
        """Con qué se elaboró el plan. El anexo II lo pide y no se preguntaba.

        Se guarda con una lista nuestra (a mano, con este programa, me lo hizo el técnico) porque
        el catálogo oficial de ese campo **no está publicado**: se dice en `iuws_mapeo.py` y no se
        supone la equivalencia. Igual que con la eficacia del tratamiento.
        """
        respuesta = cliente.post(
            "/api/planes",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "parcela_id": parcela["id"],
                "cultivo": "Trigo blando",
                "superficie_ha": 2.43,
                "herramienta": True,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["herramienta"] is True

        listado = cliente.get("/api/planes", headers=cuenta["cabeceras"]).json()
        assert listado[0]["herramienta"] is True

    def test_la_herramienta_del_plan_se_puede_dejar_sin_decir(self, cliente, cuenta, plan):
        """Es opcional: quien lo haya hecho de cabeza tiene que poder apuntarlo igual.

        Y no se pone un «no» de relleno: vacío es «no me lo ha dicho», que es distinto de
        «lo hice a mano».
        """
        creado = plan()
        assert creado["herramienta"] is None
        listado = cliente.get("/api/planes", headers=cuenta["cabeceras"]).json()
        assert listado[0]["herramienta"] is None

    def test_el_plan_dice_el_cultivo_del_ano_anterior(self, cliente, cuenta, campana, parcela):
        """El cultivo precedente **se calcula del historial**, no se pregunta.

        El anexo II lo pide en el plan de abono y el agricultor no tiene por qué acordarse de lo
        que sembró el año pasado: el programa ya lo sabe, porque cada campaña tiene sus cultivos
        declarados. Se deduce de ahí, así que si corrige el historial el plan dice la verdad nueva.
        """
        # La campaña de este año ya existe (la del cuaderno); se añade la del año pasado.
        anterior = cliente.post(
            "/api/campanas",
            headers=cuenta["cabeceras"],
            json={"anio": campana["anio"] - 1, "fecha_inicio": "2025-09-01", "fecha_fin": "2026-08-31"},
        )
        assert anterior.status_code == 201, anterior.text
        anterior = anterior.json()
        # Lo que se sembró el año pasado en esa parcela.
        sembrado = cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={"campana_id": anterior["id"], "especie": "Cebada", "sistema": "secano"},
        )
        assert sembrado.status_code == 201, sembrado.text
        plan = cliente.post(
            "/api/planes",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "parcela_id": parcela["id"],
                "cultivo": "Trigo blando",
                "superficie_ha": 2.43,
            },
        )
        assert plan.status_code == 201, plan.text

        listado = cliente.get("/api/planes", headers=cuenta["cabeceras"]).json()
        assert listado[0]["cultivo_precedente"] == "Cebada", (
            "no dice qué había el año anterior, y lo sabe"
        )

    def test_sin_campana_anterior_el_cultivo_precedente_es_no_lo_se(
        self, cliente, cuenta, campana, parcela
    ):
        """Sin campaña anterior no se inventa nada: no se sabe, y se dice con un vacío."""
        respuesta = cliente.post(
            "/api/planes",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "parcela_id": parcela["id"],
                "cultivo": "Trigo blando",
                "superficie_ha": 2.43,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        listado = cliente.get("/api/planes", headers=cuenta["cabeceras"]).json()
        assert listado[0]["cultivo_precedente"] is None

    def test_sin_cultivo_no_se_puede_hacer(self, cliente, cuenta, campana, parcela):
        respuesta = cliente.post(
            "/api/planes",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "parcela_id": parcela["id"],
                "cultivo": "",
                "superficie_ha": 2.43,
            },
        )
        assert respuesta.status_code == 422

    def test_sin_parcela_no_se_puede_hacer(self, cliente, cuenta, campana):
        respuesta = cliente.post(
            "/api/planes",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "cultivo": "Trigo",
                "superficie_ha": 2.43,
            },
        )
        assert respuesta.status_code == 422
        codigos = [a["codigo"] for a in respuesta.json()["detail"]["avisos"]]
        assert "V18_sin_parcela" in codigos

    def test_el_aviso_dice_qué_hacer(self, cliente, cuenta, campana):
        respuesta = cliente.post(
            "/api/planes/validar",
            headers=cuenta["cabeceras"],
            json={"campana_id": campana["id"], "cultivo": "", "superficie_ha": 2.43},
        )
        avisos = respuesta.json()["avisos"]
        assert any("cultivo" in a["mensaje"] for a in avisos), "no dice qué falta"
        assert all(a["mensaje"] for a in avisos), "hay un aviso sin texto"

    def test_cada_finca_ve_solo_sus_planes(self, cliente, cuenta, plan, crear_cuenta):
        plan()
        otro = crear_cuenta("otro@ejemplo.test")
        assert cliente.get("/api/planes", headers=otro["cabeceras"]).json() == []

    def test_no_se_puede_ver_un_plan_de_otra_finca(self, cliente, cuenta, plan, crear_cuenta):
        creado = plan()
        otro = crear_cuenta("otro@ejemplo.test")
        respuesta = cliente.get(f"/api/planes/{creado['id']}", headers=otro["cabeceras"])
        assert respuesta.status_code == 404


class TestLaComparacion:
    """Lo que de verdad sirve del plan: saber si se está cumpliendo."""

    def test_un_abono_contra_el_plan_se_cuenta(
        self, cliente, cuenta, campana, parcela, fertilizante, plan
    ):
        creado = plan()
        abonar(cliente, cuenta, campana, parcela, fertilizante, plan_id=creado["id"])

        datos = cliente.get(f"/api/planes/{creado['id']}", headers=cuenta["cabeceras"]).json()
        # 300 kg/ha al 33,5 % son 100,5 kg de nitrógeno por hectárea.
        assert datos["aplicado_n"] == pytest.approx(100.5)
        assert datos["apuntes"] == 1

    def test_el_resumen_dice_cuanto_queda(self, cliente, cuenta, campana, parcela, fertilizante, plan):
        creado = plan()
        abonar(cliente, cuenta, campana, parcela, fertilizante, plan_id=creado["id"])
        resumen = cliente.get(
            f"/api/planes/{creado['id']}/resumen", headers=cuenta["cabeceras"]
        ).json()
        fila_n = next(f for f in resumen["filas"] if f["nutriente"] == "N")
        assert fila_n["previsto"] == 100.0
        assert fila_n["aplicado"] == pytest.approx(100.5)
        assert fila_n["queda"] == pytest.approx(-0.5)

    def test_pasarse_del_plan_se_avisa(self, cliente, cuenta, campana, parcela, fertilizante, plan):
        """100,5 kg de nitrógeno contra un plan de 100: se ha pasado, y hay que decirlo."""
        creado = plan()
        abonar(cliente, cuenta, campana, parcela, fertilizante, plan_id=creado["id"])
        datos = cliente.get(f"/api/planes/{creado['id']}", headers=cuenta["cabeceras"]).json()
        assert datos["se_ha_pasado"] is True
        assert "más de lo que tenías previsto" in datos["mensaje"]

    def test_irse_justo_no_es_pasarse(self, cliente, cuenta, campana, parcela, fertilizante, plan):
        creado = plan(necesidad_n=100.5)
        abonar(cliente, cuenta, campana, parcela, fertilizante, plan_id=creado["id"])
        datos = cliente.get(f"/api/planes/{creado['id']}", headers=cuenta["cabeceras"]).json()
        assert datos["se_ha_pasado"] is False

    def test_un_abono_anulado_no_cuenta(self, cliente, cuenta, campana, parcela, fertilizante, plan):
        """Lo que se anuló no se echó, así que no puede contar para el plan."""
        creado = plan()
        registro = abonar(
            cliente, cuenta, campana, parcela, fertilizante, plan_id=creado["id"]
        ).json()
        cliente.post(
            f"/api/fertilizaciones/{registro['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de parcela"},
        )
        datos = cliente.get(f"/api/planes/{creado['id']}", headers=cuenta["cabeceras"]).json()
        assert datos["aplicado_n"] == 0
        assert datos["apuntes"] == 0
        assert datos["se_ha_pasado"] is False

    def test_un_abono_sin_enlazar_tambien_cuenta_en_el_plan(
        self, cliente, cuenta, campana, parcela, fertilizante, plan
    ):
        """ESTE ES EL TEST QUE IMPORTA DE VERDAD.

        Nadie va a acordarse de enlazar cada abono con el plan a mano. Si solo contaran
        los enlazados, el aviso de pasarse no saltaría casi nunca y el plan no serviría
        para nada: es un papel guardado en un cajón.
        """
        creado = plan()
        abonar(cliente, cuenta, campana, parcela, fertilizante)  # sin plan_id
        datos = cliente.get(f"/api/planes/{creado['id']}", headers=cuenta["cabeceras"]).json()
        assert datos["aplicado_n"] == pytest.approx(100.5)
        assert datos["se_ha_pasado"] is True

    def test_al_apuntar_sin_enlazar_tambien_avisa(
        self, cliente, cuenta, campana, parcela, fertilizante, plan
    ):
        """Y el aviso tiene que salir EN EL MOMENTO, sin decirle que enlace nada."""
        creado = plan()  # noqa: F841 — el plan tiene que existir para esa parcela
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "fertilizante_id": fertilizante["id"],
                "kg_ha_producto": 300.0,
            },
        )
        codigos = [a["codigo"] for a in respuesta.json()["avisos"]]
        assert "F5_plan_excedido" in codigos

    def test_un_abono_de_otra_parcela_no_cuenta(
        self, cliente, cuenta, campana, parcela, crear_parcela, fertilizante, plan
    ):
        creado = plan()
        otra = crear_parcela(alias="La Vega", superficie_ha=5.0)
        abonar(cliente, cuenta, campana, otra, fertilizante)
        datos = cliente.get(f"/api/planes/{creado['id']}", headers=cuenta["cabeceras"]).json()
        assert datos["aplicado_n"] == 0

    def test_un_abono_sin_plan_no_cuenta_si_no_hay_plan_para_esa_parcela(
        self, cliente, cuenta, campana, crear_parcela, fertilizante, plan
    ):
        plan()  # el plan es de «El Prado»
        otra = crear_parcela(alias="La Vega", superficie_ha=5.0)
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "parcela_id": otra["id"],
                "superficie_ha": 5.0,
                "fertilizante_id": fertilizante["id"],
                "kg_ha_producto": 300.0,
            },
        )
        codigos = [a["codigo"] for a in respuesta.json()["avisos"]]
        assert "F5_plan_excedido" not in codigos

    def test_sin_necesidades_lo_dice_en_vez_de_comparar(
        self, cliente, cuenta, campana, parcela
    ):
        creado = cliente.post(
            "/api/planes",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "parcela_id": parcela["id"],
                "cultivo": "Trigo",
                "superficie_ha": 2.43,
            },
        ).json()
        datos = cliente.get(f"/api/planes/{creado['id']}", headers=cuenta["cabeceras"]).json()
        assert "no se puede comparar" in datos["mensaje"]

    def test_al_apuntar_un_abono_avisa_si_te_pasas_del_plan(
        self, cliente, cuenta, campana, parcela, fertilizante, plan
    ):
        """El aviso tiene que salir EN EL MOMENTO, no cuando ya está apuntado."""
        creado = plan()
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "fertilizante_id": fertilizante["id"],
                "kg_ha_producto": 300.0,
                "plan_id": creado["id"],
            },
        )
        avisos = {a["codigo"]: a for a in respuesta.json()["avisos"]}
        assert "F5_plan_excedido" in avisos
        assert not avisos["F5_plan_excedido"]["bloquea"], (
            "el plan es una recomendación: no puede bloquear"
        )
        assert "100,0" in avisos["F5_plan_excedido"]["mensaje"]

    def test_dentro_del_plan_no_avisa(self, cliente, cuenta, campana, parcela, fertilizante, plan):
        creado = plan(necesidad_n=500.0)
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "fertilizante_id": fertilizante["id"],
                "kg_ha_producto": 300.0,
                "plan_id": creado["id"],
            },
        )
        codigos = [a["codigo"] for a in respuesta.json()["avisos"]]
        assert "F5_plan_excedido" not in codigos

    def test_con_el_plan_ya_no_avisa_de_que_falta(
        self, cliente, cuenta, campana, crear_parcela, fertilizante, plan
    ):
        """En regadío, tener el plan quita el aviso de que falta el plan."""
        regadio = crear_parcela(alias="El Regadío", sistema="regadio")
        creado = plan(parcela_id=regadio["id"])
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-20",
                "parcela_id": regadio["id"],
                "superficie_ha": 2.43,
                "fertilizante_id": fertilizante["id"],
                "kg_ha_producto": 100.0,
                "plan_id": creado["id"],
            },
        )
        codigos = [a["codigo"] for a in respuesta.json()["avisos"]]
        assert "F4_sin_plan_regadio" not in codigos


class TestActualizarSinPerderDatos:
    """El camino para poner al día una instalación que ya tiene datos dentro.

    Este fallo ya apareció una vez y es de los peores: el agricultor actualiza, el
    programa arranca, y al abrir el cuaderno revienta con un «no such column» y se queda
    sin poder entrar. `create_all` crea las tablas que no están, pero no toca las que ya
    existen.
    """

    def _motor_viejo(self, tmp_path, sentencia: str):
        motor = create_engine(f"sqlite:///{(tmp_path / 'vieja.db').as_posix()}")
        with motor.begin() as conexion:
            conexion.execute(text(sentencia))
        return motor

    def test_anade_una_columna_de_texto_que_falta(self, tmp_path):
        motor = self._motor_viejo(
            tmp_path,
            "CREATE TABLE parcelas (id INTEGER PRIMARY KEY, explotacion_id INTEGER, "
            "alias VARCHAR(120))",
        )
        anadidas, imposibles = database.asegurar_columnas(motor)
        assert "parcelas.superficie_ha" in anadidas
        columnas = {c["name"] for c in inspect(motor).get_columns("parcelas")}
        assert "superficie_ha" in columnas
        assert not imposibles, f"no debería haber columnas imposibles: {imposibles}"

    def test_una_columna_obligatoria_se_anade_con_su_valor_por_defecto(self, tmp_path):
        """SQLite no deja añadir una columna obligatoria sin valor. Se le pone el mismo
        que habría puesto Python, así las filas viejas quedan como si siempre hubiera
        estado ahí."""
        motor = self._motor_viejo(
            tmp_path,
            "CREATE TABLE instalaciones (id INTEGER PRIMARY KEY, explotacion_id INTEGER, "
            "alias VARCHAR(120))",
        )
        anadidas, _imposibles = database.asegurar_columnas(motor)
        assert "instalaciones.tipo" in anadidas
        with motor.begin() as conexion:
            conexion.execute(text("INSERT INTO instalaciones (id, explotacion_id, alias) VALUES (1, 1, 'X')"))
            fila = conexion.execute(text("SELECT tipo FROM instalaciones WHERE id = 1")).one()
        assert fila[0] == "almacen", "no se ha puesto el valor por defecto"

    def test_no_toca_las_columnas_que_ya_estan(self, tmp_path):
        """Ejecutarlo dos veces no puede romper nada ni duplicar columnas."""
        motor = self._motor_viejo(
            tmp_path,
            "CREATE TABLE parcelas (id INTEGER PRIMARY KEY, explotacion_id INTEGER, "
            "alias VARCHAR(120), superficie_ha FLOAT)",
        )
        primera, _ = database.asegurar_columnas(motor)
        segunda, _ = database.asegurar_columnas(motor)
        assert "parcelas.superficie_ha" not in primera
        assert segunda == [], "la segunda pasada no debería añadir nada"
        nombres = [c["name"] for c in inspect(motor).get_columns("parcelas")]
        assert nombres.count("superficie_ha") == 1

    def test_las_tablas_que_no_existen_se_ignoran(self, tmp_path):
        motor = self._motor_viejo(
            tmp_path, "CREATE TABLE parcelas (id INTEGER PRIMARY KEY, alias VARCHAR(120))"
        )
        anadidas, imposibles = database.asegurar_columnas(motor)
        assert anadidas, "debería haber añadido columnas a parcelas"
        assert all(nombre.startswith("parcelas.") for nombre in anadidas)

    def test_crear_tablas_deja_la_base_lista(self, tmp_path):
        motor = create_engine(f"sqlite:///{(tmp_path / 'nueva.db').as_posix()}")
        anadidas, imposibles = database.crear_tablas(motor)
        assert anadidas == [] and imposibles == []
        assert inspect(motor).has_table("planes_abonado")

    def test_los_planes_se_pueden_consultar_con_la_tabla_puesta_al_dia(self, tmp_path):
        """La prueba de que el arreglo sirve: una tabla a la antigua y una consulta real."""
        motor = self._motor_viejo(
            tmp_path,
            "CREATE TABLE planes_abonado (id INTEGER PRIMARY KEY, explotacion_id INTEGER, "
            "campana_id INTEGER, cultivo VARCHAR(120), superficie_ha FLOAT)",
        )
        database.asegurar_columnas(motor)
        with motor.begin() as conexion:
            conexion.execute(
                text(
                    "INSERT INTO planes_abonado (id, explotacion_id, campana_id, cultivo, "
                    "superficie_ha, necesidad_n, notas) VALUES (1, 1, 1, 'Trigo', 2.43, 100, 'x')"
                )
            )
            fila = conexion.execute(
                text("SELECT cultivo, necesidad_n, notas FROM planes_abonado WHERE id = 1")
            ).one()
        assert fila[0] == "Trigo"
        assert fila[1] == 100
