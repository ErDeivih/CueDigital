"""Sacar el cuaderno de la Junta relleno: el fichero y la lista de lo que falta.

Estos tests comprueban las tres cosas que hacen falta para que esto valga:

1. **Que el fichero se escriba bien.** La prueba que más vale es la de ida y vuelta: se escribe el
   cuaderno con los datos de una explotación y **se vuelve a leer con el lector del cuaderno**
   (`app/cuaderno_cyl.py`). Si lo que se lee no es lo que se escribió, el fichero no sirve.
2. **Que lo que falta se diga.** El informe de lo que falta es la respuesta a «¿qué datos me piden?»,
   así que se comprueba que sale cuando falta algo (una tierra sin cultivo, un abono sin albarán…) y
   que **no sale** cuando está todo.
3. **Que no se invente nada.** Un dato que no está se queda en blanco en el fichero, nunca con un
   cero ni con un valor parecido.
"""

from __future__ import annotations

import datetime as dt
import io

from openpyxl import load_workbook

from app import cuaderno_cyl_exportar as exportar

CAMPANA = 2026


def _campana(cliente, cabeceras) -> dict:
    return cliente.get("/api/campanas/actual", headers=cabeceras).json()


def _parcela(cliente, cabeceras, alias="El Prado", **extra) -> dict:
    cuerpo = {
        "alias": alias,
        "ref_sigpac": "37-70-0-0-503-51",
        "municipio": "Calvarrasa de Arriba",
        "provincia": "Salamanca",
        "codigo_ine": "37070",
        "poligono": 503,
        "numero_parcela": 51,
        "numero_recinto": 1,
        "superficie_ha": 4.9,
        "uso_sigpac": "TA",
        "sistema": "secano",
    }
    cuerpo.update(extra)
    respuesta = cliente.post("/api/parcelas", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _finca_completa(cliente, cabeceras) -> dict:
    """Deja una explotación con una tierra, su cultivo, un abono, un tratamiento y una venta."""
    campana = _campana(cliente, cabeceras)
    parcela = _parcela(cliente, cabeceras)
    cliente.put(
        "/api/mi-finca",
        headers=cabeceras,
        json={
            "nombre": "David Pérez Velasco",
            "nif": "70922320A",
            "provincia": "Salamanca",
            "municipio": "Calvarrasa de Arriba",
            "registro_autonomico": "0837267320",
            "direccion": "C/ Río Segre 6",
            "localidad": "Salamanca",
            "codigo_postal": "37006",
            "telefono": "634597458",
            "correo": "david@ejemplo.test",
        },
    )
    cliente.post(
        f"/api/parcelas/{parcela['id']}/cultivos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "especie": "TRIGO BLANDO",
            "sistema": "secano",
            "ecorregimen": "P3",
        },
    )
    abono = cliente.post(
        "/api/fertilizantes",
        headers=cabeceras,
        # Las tres riquezas, que es lo que manda el formulario de la aplicación
        # (`app.js`, los tres campos del bloque «abono.riqueza» son obligatorios). Se declaran las
        # tres **a propósito**: desde el cambio de A6 (`docs/T02_VALORES_POR_DEFECTO.md`), una
        # riqueza que no se manda se queda en «no se sabe» y el fósforo y el potasio de un nitrato
        # amónico son un cero de verdad, no un hueco. Hay otra prueba, más abajo, para el caso
        # contrario: la ficha sin composición.
        json={
            "nombre": "Nitrato amónico 33,5",
            "tipo": "mineral",
            "riqueza_n": 33.5,
            "riqueza_p": 0.0,
            "riqueza_k": 0.0,
        },
    ).json()
    cliente.post(
        "/api/fertilizaciones",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-03-20",
            "parcela_id": parcela["id"],
            "superficie_ha": 4.9,
            "fertilizante_id": abono["id"],
            "kg_ha_producto": 200,
            "numero_albaran": "A-2026-88",
            "tipo_fertilizacion": "cobertera",
        },
    )
    producto = cliente.post(
        "/api/productos",
        headers=cabeceras,
        json={
            "nombre_comercial": "Glifosato 36 SL",
            "numero_registro": "24.123",
            "materia_activa": "Glifosato",
            "dosis_maxima": 4,
            "unidad_dosis": "L/ha",
            "plazo_seguridad_dias": 7,
            "unidad_compra": "L",
        },
    ).json()
    aplicador = cliente.post(
        "/api/aplicadores",
        headers=cabeceras,
        json={
            "nombre": "David Pérez Velasco",
            "nif": "70922320A",
            "numero_ropo": "ROPO-123",
            "numero_carne": "C-37070-123",
            "tipo_carne": "Cualificado",
        },
    ).json()
    equipo = cliente.post(
        "/api/equipos",
        headers=cabeceras,
        json={
            "nombre": "Pulverizador del tractor",
            "tipo": "pulverizador",
            "marca": "Hardy",
            "modelo": "Master 2000",
            "numero_roma": "ROMA-37070-001",
            "fecha_adquisicion": "2019-05-01",
            "fecha_iteaf": "2024-06-15",
            "fecha_proxima_iteaf": "2027-06-15",
        },
    ).json()
    tratamiento = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-04-10",
            "parcela_id": parcela["id"],
            "superficie_tratada_ha": 4.9,
            "justificacion": "Vi la hierba en el campo",
            "plaga": "Hierbas adventicias",
            "producto_id": producto["id"],
            "dosis": 3,
            "eficacia": "buena",
            "aplicador_id": aplicador["id"],
            "equipo_id": equipo["id"],
        },
    )
    assert tratamiento.status_code == 201, tratamiento.text
    return {"parcela": parcela, "campana": campana, "producto": producto, "equipo": equipo}


def _descargar(cliente, cabeceras) -> bytes:
    respuesta = cliente.get("/api/cuaderno-cyl/exportar", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.content[:2] == b"PK"  # un .xlsx es un ZIP
    return respuesta.content


class TestElFicheroQueSeSaca:
    """El cuaderno escrito, hoja por hoja."""

    def test_tiene_las_veinticinco_hojas_del_cuaderno_oficial(self, cliente, cuenta):
        contenido = _descargar(cliente, cuenta["cabeceras"])
        libro = load_workbook(io.BytesIO(contenido))
        assert libro.sheetnames == exportar.HOJAS
        assert len(libro.sheetnames) == 25

    def test_la_portada_lleva_los_datos_del_titular(self, cliente, cuenta):
        _finca_completa(cliente, cuenta["cabeceras"])
        libro = load_workbook(io.BytesIO(_descargar(cliente, cuenta["cabeceras"])))
        hoja = libro["1.1. INF. GRAL"]
        assert hoja["G7"].value == "David Pérez Velasco"
        assert hoja["R7"].value == "70922320A"
        assert hoja["P8"].value == "0837267320"
        assert hoja["C9"].value == "C/ Río Segre 6"

    def test_las_tierras_salen_con_su_referencia_y_su_cultivo(self, cliente, cuenta):
        _finca_completa(cliente, cuenta["cabeceras"])
        libro = load_workbook(io.BytesIO(_descargar(cliente, cuenta["cabeceras"])))
        hoja = libro["2.1. DATOS PARCELAS"]
        assert hoja["Q2"].value == CAMPANA
        assert hoja["Q2"].value == 2026
        # La primera línea de parcela: la fila 14, como en el cuaderno oficial.
        assert hoja["B14"].value == "1"
        assert hoja["C14"].value == "37"
        assert hoja["D14"].value == "70-Calvarrasa de Arriba"
        assert hoja["G14"].value == "503"
        assert hoja["H14"].value == "51"
        assert hoja["I14"].value == "1"
        assert hoja["M14"].value == "TRIGO BLANDO"
        assert hoja["N14"].value == "P3"
        assert hoja["O14"].value == "S"

    def test_los_tratamientos_salen_con_su_producto_y_su_registro(self, cliente, cuenta):
        _finca_completa(cliente, cuenta["cabeceras"])
        libro = load_workbook(io.BytesIO(_descargar(cliente, cuenta["cabeceras"])))
        hoja = libro["3.1. REG. FIT. x P."]
        assert hoja["J12"].value == "Glifosato 36 SL"
        assert hoja["K12"].value == "24.123"
        assert hoja["L12"].value == "3"
        assert hoja["H12"].value == "David Pérez Velasco"  # el aplicador
        assert hoja["I12"].value == "Pulverizador del tractor"  # la máquina
        assert hoja["M12"].value == "buena"  # la eficacia

    def test_el_abono_sale_con_su_albaran_y_su_tipo(self, cliente, cuenta):
        """Es lo que pide la hoja 6, y es de donde salen las facturas."""
        _finca_completa(cliente, cuenta["cabeceras"])
        libro = load_workbook(io.BytesIO(_descargar(cliente, cuenta["cabeceras"])))
        hoja = libro["6. REG. FERTILIZ"]
        assert hoja["D11"].value == "Nitrato amónico 33,5"
        assert hoja["G11"].value == "A-2026-88"
        assert hoja["H11"].value == "33.5/0/0"
        assert hoja["I11"].value == "200"
        # AC es el código del cuaderno para el abonado de cobertera.
        assert hoja["J11"].value == "AC"

    def test_la_maquina_sale_con_su_roma_y_sus_fechas(self, cliente, cuenta):
        _finca_completa(cliente, cuenta["cabeceras"])
        libro = load_workbook(io.BytesIO(_descargar(cliente, cuenta["cabeceras"])))
        hoja = libro["1.2., 1.3. y 1.4. INF. GRAL"]
        assert hoja["C20"].value == "Pulverizador del tractor"
        assert hoja["E20"].value == "ROMA-37070-001"
        assert hoja["G20"].value == "01/05/2019"
        assert hoja["I20"].value == "15/06/2024"

    def test_la_persona_sale_con_su_ropo_y_su_carne_marcado(self, cliente, cuenta):
        _finca_completa(cliente, cuenta["cabeceras"])
        libro = load_workbook(io.BytesIO(_descargar(cliente, cuenta["cabeceras"])))
        hoja = libro["1.2., 1.3. y 1.4. INF. GRAL"]
        assert hoja["C11"].value == "David Pérez Velasco"
        assert hoja["D11"].value == "70922320A"
        assert hoja["E11"].value == "ROPO-123"
        # La cruz va en la columna del carné cualificado.
        assert hoja["G11"].value == "X"
        assert hoja["F11"].value in ("", None)

    def test_las_lineas_se_numeran_igual_que_en_la_hoja_de_las_parcelas(self, cliente, cuenta):
        """El cuaderno identifica la parcela por su número de orden, así que tiene que cuadrar."""
        campana = _campana(cliente, cuenta["cabeceras"])
        _parcela(cliente, cuenta["cabeceras"], alias="La primera")
        segunda = _parcela(
            cliente,
            cuenta["cabeceras"],
            alias="La segunda",
            poligono=504,
            numero_parcela=11,
        )
        libro = load_workbook(io.BytesIO(_descargar(cliente, cuenta["cabeceras"])))
        hoja = libro["2.1. DATOS PARCELAS"]
        assert hoja["G14"].value == "503"
        assert hoja["G15"].value == "504"
        # Y en el abonado de esa segunda tierra, el número de orden es el 2.
        abono = cliente.post(
            "/api/fertilizantes", headers=cuenta["cabeceras"], json={"nombre": "Urea", "riqueza_n": 46}
        ).json()
        cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-03-01",
                "parcela_id": segunda["id"],
                "superficie_ha": 1.5,
                "fertilizante_id": abono["id"],
                "kg_ha_producto": 100,
            },
        )
        libro = load_workbook(io.BytesIO(_descargar(cliente, cuenta["cabeceras"])))
        assert libro["6. REG. FERTILIZ"]["C11"].value == "2"

    def test_no_se_inventa_ningun_dato(self, cliente, cuenta):
        """Una explotación vacía: el fichero sale con las hojas y **sin un solo número inventado**."""
        libro = load_workbook(io.BytesIO(_descargar(cliente, cuenta["cabeceras"])))
        hoja = libro["6. REG. FERTILIZ"]
        assert hoja["D11"].value in (None, "")
        assert hoja["I11"].value in (None, "")
        # Y la portada tiene las etiquetas puestas, con sus huecos.
        assert libro["1.1. INF. GRAL"]["B7"].value == "NOMBRE Y APELLIDOS O RAZÓN SOCIAL:"


class TestLaIdaYVuelta:
    """Lo que se escribe se tiene que poder leer con el lector del cuaderno.

    Es la prueba más fuerte que se le puede hacer a un escritor: si el fichero que saca el programa
    no se puede volver a leer con el mismo lector que lee los de la Junta, es que no es el cuaderno.
    """

    def test_el_cuaderno_escrito_se_vuelve_a_leer(self, cliente, cuenta):
        cuenta_explotacion = cliente.get("/api/mi-finca", headers=cuenta["cabeceras"]).json()["nombre"]
        desde = cliente.post(
            "/api/cuaderno-cyl/leer",
            headers=cuenta["cabeceras"],
            files=_fichero_de_ejemplo(),
        ).json()
        cliente.post(
            "/api/cuaderno-cyl/importar",
            headers=cuenta["cabeceras"],
            files=_fichero_de_ejemplo(),
        )
        exportado = _descargar(cliente, cuenta["cabeceras"])
        leido = exportar.lee_lo_escrito(exportado)

        # El lector tiene que sacar lo mismo que tenía el cuaderno del que se trajeron las tierras.
        assert leido.anio == desde["anio"]
        assert len(leido.parcelas) == desde["resumen"]["lineas_leidas"]
        primeras = [linea.ref_sigpac for linea in leido.parcelas]
        assert primeras == [linea["ref_sigpac"] for linea in desde["lineas"]]
        # Del titular: el del cuaderno de ejemplo **no** pisa al del agricultor. La importación solo
        # rellena huecos (es una decisión de todo el programa), así que lo que sale es el nombre de
        # la cuenta, que es el suyo.
        assert leido.generales.nombre == cuenta_explotacion or leido.generales.nombre
        assert leido.generales.nombre != "EXPLOTACIÓN DE EJEMPLO"


def _fichero_de_ejemplo() -> dict:
    """El fichero del cuaderno de ejemplo, que es el que usan los tests del lector."""
    from pathlib import Path

    ruta = Path(__file__).resolve().parent / "datos" / "cuaderno_cyl_de_ejemplo.xlsx"
    return {"fichero": ("CuadernoExplotacion_12345678Z.xlsx", ruta.read_bytes())}


class TestLoQueFalta:
    """El informe de lo que falta: la respuesta a «¿qué datos me piden?»."""

    def test_una_explotacion_vacia_los_pide_todos(self, cliente, cuenta):
        datos = cliente.get("/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]).json()
        assert datos["cuantas_faltan"] > 0
        que_falta = " ".join(falta["que_falta"] for falta in datos["faltan"])
        # Los cuatro grandes: las tierras, las máquinas, quién echa el producto y el plan de abono.
        # Se busca la frase entera de cada uno y no dos palabras sueltas: desde la ronda 28 la lista
        # de lo que falta también habla de las hojas que no se escriben solas, y ahí aparece «tus
        # tierras» de pasada (la hoja 2.2). Comprobar dos palabras sueltas daba por bueno un texto
        # que no era el que se quería comprobar.
        assert "sin ellas no hay cuaderno" in que_falta
        assert "las máquinas" in que_falta
        assert "quién echa los productos" in que_falta
        assert "el plan de abonado del año" in que_falta
        # Y cada cosa dice dónde se pone: sin eso, el agricultor no sabe qué hacer con la lista.
        assert all(falta["donde_se_pone"] for falta in datos["faltan"])

    def test_con_la_finca_completa_ya_no_pide_esas_cosas(self, cliente, cuenta):
        _finca_completa(cliente, cuenta["cabeceras"])
        datos = cliente.get("/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]).json()
        que_falta = " ".join(falta["que_falta"] for falta in datos["faltan"])
        assert "sin ellas no hay cuaderno" not in que_falta
        assert "las máquinas" not in que_falta
        assert "quién echa los productos" not in que_falta
        # El plan de abono sigue faltando: no se ha hecho ninguno.
        assert "el plan de abonado del año" in que_falta

    def test_dice_lo_que_le_falta_a_un_abono(self, cliente, cuenta):
        """Un abono sin nº de albarán se apunta, pero el cuaderno lo pide: hay que decirlo."""
        campana = _campana(cliente, cuenta["cabeceras"])
        parcela = _parcela(cliente, cuenta["cabeceras"])
        abono = cliente.post(
            "/api/fertilizantes", headers=cuenta["cabeceras"], json={"nombre": "Urea", "riqueza_n": 46}
        ).json()
        cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-03-01",
                "parcela_id": parcela["id"],
                "superficie_ha": 1.5,
                "fertilizante_id": abono["id"],
                "kg_ha_producto": 100,
            },
        )
        datos = cliente.get("/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]).json()
        que_falta = " ".join(falta["que_falta"] for falta in datos["faltan"])
        assert "nº de albarán" in que_falta
        assert "de fondo, de cobertera o fertirrigación" in que_falta

    def test_a_una_maquina_sin_roma_no_se_le_pide_el_roma(self, cliente, cuenta):
        """Una mochila no se inscribe en el ROMA ni se inspecciona: pedirlo sería pedir un dato que
        no existe. Es la diferencia entre las tres pestañas de la app oficial."""
        cliente.post(
            "/api/equipos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Mochila de la espalda", "titularidad": "no_roma"},
        )
        datos = cliente.get("/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]).json()
        que_falta = " ".join(falta["que_falta"] for falta in datos["faltan"])
        assert "la fecha de la última inspección" not in que_falta
        assert "el nº de inscripción en el ROMA" not in que_falta

    def test_a_una_maquina_con_roma_si_se_le_pide(self, cliente, cuenta):
        cliente.post(
            "/api/equipos",
            headers=cuenta["cabeceras"],
            json={"nombre": "Pulverizador", "titularidad": "propia", "marca": "Hardy"},
        )
        datos = cliente.get("/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]).json()
        que_falta = " ".join(falta["que_falta"] for falta in datos["faltan"])
        assert "el nº de inscripción en el ROMA" in que_falta
        assert "la fecha de la última inspección" in que_falta

    def test_dice_que_las_facturas_hacen_falta(self, cliente, cuenta):
        datos = cliente.get("/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]).json()
        que_falta = " ".join(falta["que_falta"] for falta in datos["faltan"])
        assert "las facturas de lo que compras" in que_falta

    def test_las_hojas_del_cuaderno_se_sirven_con_su_nombre(self, cliente, cuenta):
        datos = cliente.get("/api/cuaderno-cyl/hojas", headers=cuenta["cabeceras"]).json()
        assert len(datos["hojas"]) == 25
        titulos = {hoja["nombre"]: hoja["titulo"] for hoja in datos["hojas"]}
        assert titulos["2.1. DATOS PARCELAS"] == "Las parcelas"
        assert titulos["6. REG. FERTILIZ"] == "Abonado"


class TestElFicheroSeDescarga:
    def test_se_descarga_con_el_nombre_de_la_junta(self, cliente, cuenta):
        respuesta = cliente.get("/api/cuaderno-cyl/exportar", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        assert "CuadernoExplotacion_70922320A" in respuesta.headers["content-disposition"]
        assert "spreadsheetml" in respuesta.headers["content-type"]

    def test_hace_falta_entrar(self, cliente):
        assert cliente.get("/api/cuaderno-cyl/exportar").status_code == 401

    def test_queda_apuntado_en_la_auditoria(self, cliente, cuenta, db_sesion):
        from app import models

        _descargar(cliente, cuenta["cabeceras"])
        acciones = [fila.accion for fila in db_sesion.query(models.Auditoria).all()]
        assert "sacar_el_cuaderno_de_la_junta" in acciones

    def test_cada_finca_saca_solo_lo_suyo(self, cliente, cuenta, crear_cuenta):
        _finca_completa(cliente, cuenta["cabeceras"])
        otra = crear_cuenta("otro@ejemplo.test", nombre="Otra finca")
        libro = load_workbook(io.BytesIO(_descargar(cliente, otra["cabeceras"])))
        # La finca de la otra cuenta está vacía: su portada lleva **su** nombre, no el del
        # primero, y no tiene ni una sola tierra del otro.
        assert libro["1.1. INF. GRAL"]["G7"].value == "Otra finca"
        assert libro["2.1. DATOS PARCELAS"]["B14"].value in (None, "")


class TestElInventarioDeLasHojas:
    """Las 25 hojas del cuaderno: cada una o la escribe el programa o se dice qué le falta.

    Esto existe porque el cuaderno oficial tiene quince hojas que este programa todavía no escribe
    solo, y hasta la ronda 28 solo se avisaba de dos: **trece hojas se entregaban en blanco sin que
    el programa dijera nada**, y el agricultor no tenía forma de saber si le faltaban datos o si era
    el programa el que no las escribía. Un inventario a medias es peor que no tenerlo, porque quien
    lo lee se fía.
    """

    def test_las_dos_listas_juntas_son_las_veinticinco_hojas(self):
        """Ni una hoja olvidada, ni una inventada: la suma tiene que ser el cuaderno entero."""
        rellenas = set(exportar.HOJAS_QUE_SE_RELLENAN)
        sin_rellenar = set(exportar.HOJAS_QUE_NO_SE_RELLENAN)

        assert not (rellenas & sin_rellenar), "una hoja no puede estar en las dos listas"
        assert rellenas | sin_rellenar == set(exportar.HOJAS), (
            "hay hojas del cuaderno que no están ni en las que se escriben ni en las que no: "
            f"{sorted(set(exportar.HOJAS) - (rellenas | sin_rellenar))}"
        )
        assert len(exportar.HOJAS) == 25
        assert len(rellenas) + len(sin_rellenar) == 25

    def test_cada_hoja_que_no_se_escribe_dice_que_pide_y_que_falta(self):
        """De cada hoja pendiente se sabe qué pide, dónde se apunta y qué falta para escribirla."""
        for nombre, apunte in exportar.HOJAS_QUE_NO_SE_RELLENAN.items():
            for clave in ("que_pide", "donde_se_apunta", "que_falta_para_escribirla"):
                assert apunte.get(clave), f"a la hoja «{nombre}» le falta «{clave}»"
            # «Ya se hará» no vale: hay que decir qué haría falta de verdad.
            assert "columnas" in apunte["que_falta_para_escribirla"] or "preguntar" in (
                apunte["que_falta_para_escribirla"]
            ), f"la hoja «{nombre}» no dice qué falta para poder escribirla"
            # Y si se cuentan apuntes, tiene que haber nombre para contarlos.
            if apunte.get("apuntes"):
                assert apunte["apuntes"] in exportar.COMO_SE_LLAMAN

    def test_el_informe_dice_lo_que_falta_en_las_quince_hojas_que_no_se_escriben(self, cliente, cuenta):
        datos = cliente.get("/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]).json()
        por_hoja: dict[str, list[dict]] = {}
        for falta in datos["faltan"]:
            por_hoja.setdefault(falta["hoja"], []).append(falta)

        for nombre in exportar.HOJAS_QUE_NO_SE_RELLENAN:
            assert nombre in por_hoja, f"la hoja «{nombre}» no se escribe y el informe no dice nada"
            assert len(por_hoja[nombre]) == 1, f"la hoja «{nombre}» sale más de una vez"
            falta = por_hoja[nombre][0]
            assert "no la escribe sola" in falta["que_falta"]
            # Y dónde se termina a mano, con la dirección oficial del cuaderno de la Junta.
            assert "particulares.ayg.jcyl.es" in falta["donde_se_pone"], (
                f"la hoja «{nombre}» no dice dónde se termina a mano"
            )

    def test_el_informe_cuenta_los_apuntes_que_ya_estan_apuntados(self, cliente, cuenta):
        """Si los datos están, el informe lo dice: lo que falta es la hoja, no el dato."""
        campana = _campana(cliente, cuenta["cabeceras"])
        parcela = _parcela(cliente, cuenta["cabeceras"])
        producto = cliente.post(
            "/api/productos",
            headers=cuenta["cabeceras"],
            json={
                "nombre_comercial": "Glifosato 36 SL",
                "numero_registro": "24.123",
                "unidad_dosis": "L/ha",
                "unidad_compra": "L",
            },
        ).json()
        # Un tratamiento que se le hizo a la semilla: va en la hoja 3.2, no en la de las parcelas.
        cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-02-01",
                "tipo": "semilla_tratada",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 4.9,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.3,
            },
        )
        # Y un riego, que va en la hoja del riego de los ecorregímenes.
        riego = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "riego",
                "fecha": "2026-07-05",
                "parcela_id": parcela["id"],
                "superficie_ha": 4.9,
                "volumen_agua": 1200,
                "unidad_agua": "m3",
                "origen_agua": "pozo",
                "sistema_riego": "aspersion",
                "numero_contador": "C-12345",
            },
        )
        assert riego.status_code == 201, riego.text

        datos = cliente.get("/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]).json()
        que_falta = {falta["hoja"]: falta["que_falta"] for falta in datos["faltan"]}

        assert "1 apunte de semilla tratada" in que_falta["3.2. REG. USO SEMILLA TRAT."]
        assert "1 riego" in que_falta["9.1.1. INF. RIEGO"]
        # Y el riego dice de dónde se saca el dato, que es lo que hace falta para copiarlo.
        assert "regar" in que_falta["9.1.1. INF. RIEGO"]

    def test_un_tratamiento_de_una_nave_no_se_escribe_en_la_hoja_de_las_parcelas(
        self, cliente, cuenta, campana, parcela, producto, instalacion
    ):
        """La hoja 3.1 es la de las **parcelas**: un tratamiento de una nave va en la 3.4.

        Antes se escribían todos juntos en la 3.1 y el de la nave salía con la casilla «Id. Parcelas»
        vacía, que es justo lo que mira quien revisa un cuaderno.
        """
        cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-06-10",
                "tipo": "instalaciones",
                "instalacion_id": instalacion["id"],
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )

        libro = load_workbook(io.BytesIO(_descargar(cliente, cuenta["cabeceras"])))
        assert libro["3.1. REG. FIT. x P."]["B12"].value in (None, ""), (
            "el tratamiento de la nave se ha escrito en la hoja de las parcelas"
        )

        datos = cliente.get("/api/cuaderno-cyl/que-falta", headers=cuenta["cabeceras"]).json()
        que_falta = {falta["hoja"]: falta["que_falta"] for falta in datos["faltan"]}
        assert "1 tratamiento de nave o almacén" in que_falta["3.4. REG. TRAT. ALMACEN"], (
            "el tratamiento de la nave no se cuenta en su hoja: se perdería sin decir nada"
        )

    def test_la_documentacion_cuenta_las_mismas_hojas(self):
        """Lo que dice la documentación y lo que hace el programa tienen que ser el mismo número.

        Es el fallo que ya pasó una vez en este proyecto con la lista de la Junta: un total escrito a
        mano que deja de ser verdad y que nadie nota hasta que alguien se fía de él. Aquí el número
        sale del propio programa, no de la cabeza de quien escribe el documento.
        """
        from pathlib import Path

        texto = (Path(__file__).resolve().parents[2] / "docs" / "CUADERNO_DE_LA_JUNTA.md").read_text(
            encoding="utf-8"
        )
        rellenas = len(exportar.HOJAS_QUE_SE_RELLENAN)
        sin_rellenar = len(exportar.HOJAS_QUE_NO_SE_RELLENAN)

        assert f"{rellenas} se escriben solas" in texto, (
            f"la documentación no dice que {rellenas} hojas se escriban solas"
        )
        assert f"{sin_rellenar} no**" in texto, (
            f"la documentación no dice que {sin_rellenar} hojas no se rellenen todavía"
        )

    def test_los_tratamientos_de_la_parcela_si_se_escriben(self, cliente, cuenta):
        """Lo que sí es de la parcela sigue saliendo: la corrección no se lleva nada por delante."""
        _finca_completa(cliente, cuenta["cabeceras"])
        libro = load_workbook(io.BytesIO(_descargar(cliente, cuenta["cabeceras"])))
        hoja = libro["3.1. REG. FIT. x P."]
        fila = [hoja.cell(row=12, column=columna).value for columna in range(2, 15)]
        assert "Glifosato 36 SL" in fila
        assert "24.123" in fila
