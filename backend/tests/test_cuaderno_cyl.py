"""Traer las tierras del cuaderno de la Junta (el Cuecyl): la lectura y el alta.

Estos tests son de dos clases, y las dos hacen falta:

1. **La lectura** (`app/cuaderno_cyl.py`): que del fichero salgan los datos que pone el papel,
   sin inventarse nada. Se prueban los casos difíciles que trae el cuaderno de verdad: una tierra
   partida en tres líneas, la casilla de nitratos en blanco (que **no** es un «no»), la especie
   con la variedad detrás de un punto, una línea sin recinto y la nota al pie debajo de la tabla.
2. **El alta** (`POST /api/cuaderno-cyl/importar`): que las tierras acaben en el cuaderno del
   agricultor, que **no se dupliquen** al subir el mismo fichero dos veces, que no se pise nada de
   lo que él ya había escrito y que lo que no se puede apuntar se diga.

El fichero de prueba `tests/datos/cuaderno_cyl_de_ejemplo.xlsx` está fabricado con datos
inventados (ver `tests/datos/LEEME.md`): los cuadernos de verdad llevan el nombre, el NIF y las
tierras de una persona, y eso no entra en el repositorio.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from app import cuaderno_cyl, models, textos

FICHERO_DE_EJEMPLO = Path(__file__).resolve().parent / "datos" / "cuaderno_cyl_de_ejemplo.xlsx"


@pytest.fixture
def cuaderno() -> cuaderno_cyl.CuadernoLeido:
    return cuaderno_cyl.leer_cuaderno(FICHERO_DE_EJEMPLO.read_bytes())


def _subir(cliente, cabeceras, ruta: str, nombre: str = "CuadernoExplotacion_12345678Z.xlsx"):
    """Sube el cuaderno de ejemplo, como lo haría el navegador."""
    return cliente.post(
        ruta,
        headers=cabeceras,
        files={"fichero": (nombre, FICHERO_DE_EJEMPLO.read_bytes())},
    )


def _parcelas(cliente, cabeceras) -> list[dict]:
    return cliente.get("/api/parcelas", headers=cabeceras).json()


class TestLeerElCuaderno:
    """La lectura del fichero, sin base de datos ni servidor por medio."""

    def test_el_fichero_de_ejemplo_esta(self):
        assert FICHERO_DE_EJEMPLO.exists(), (
            "falta el cuaderno de ejemplo; se fabrica con "
            "`python scripts/hacer_cuaderno_de_ejemplo.py`"
        )

    def test_se_leen_las_hojas_y_el_ano_de_la_campana(self, cuaderno):
        assert cuaderno.anio == 2026
        # Las 25 hojas del cuaderno oficial, para poder decir «esto es el cuaderno de la Junta»
        # y no «esto es un Excel cualquiera».
        assert len(cuaderno.hojas) == 25
        assert cuaderno_cyl.HOJA_PARCELAS in cuaderno.hojas

    def test_se_leen_los_datos_del_titular(self, cuaderno):
        generales = cuaderno.generales
        assert generales.nombre == "EXPLOTACIÓN DE EJEMPLO"
        assert generales.nif == "12345678Z"
        assert generales.registro_autonomico == "9999999999"
        assert generales.direccion == "CALLE DEL EJEMPLO, 1"
        assert generales.localidad == "PUEBLO DE EJEMPLO"
        assert generales.codigo_postal == "00000"
        assert generales.correo == "ejemplo@ejemplo.test"

    def test_el_registro_nacional_vacio_no_se_come_el_autonomico(self, cuaderno):
        """El fallo que tenía esto antes de arreglarlo, y por eso está escrito aquí.

        En la hoja 1.1, el «Nº Registro de Explotaciones Nacional» está **vacío** y a su derecha
        está la etiqueta del autonómico. Leyendo «la celda de al lado» sin más, el número
        autonómico acababa apuntado como nacional: dos datos distintos con el mismo valor, y uno
        de ellos falso. En blanco tiene que quedarse en blanco.
        """
        assert cuaderno.generales.registro_nacional == ""
        assert cuaderno.generales.registro_autonomico == "9999999999"

    def test_la_errata_del_telefono_de_la_plantilla_no_estorba(self, cuaderno):
        """El cuaderno oficial escribe «Telófono» con tilde en la primera o.

        Es una errata de la plantilla de la Junta. Si el lector buscara «Teléfono» no encontraría
        nada y el teléfono se perdería sin decir nada.
        """
        assert cuaderno.generales.telefono_movil == "600000000"
        # Y el fijo, que está vacío en el papel, no se lleva por delante al móvil que va al lado.
        assert cuaderno.generales.telefono_fijo == ""

    def test_las_lineas_de_parcela_se_leen_enteras(self, cuaderno):
        # 8 líneas en el papel, 7 apuntables: la octava no dice el recinto.
        assert len(cuaderno.parcelas) == 7
        assert cuaderno.lineas_ilegibles == [8]
        assert cuaderno.lineas_en_el_papel == 8
        primera = cuaderno.parcelas[0]
        assert primera.orden == 1
        assert primera.ref_sigpac == "99-99-0-0-1-1-1"
        assert primera.municipio_nombre == "PUEBLO DE EJEMPLO"
        assert primera.uso_sigpac == "TA"
        assert primera.superficie_sigpac_ha == 1.09
        assert primera.superficie_cultivada_ha == 1.09
        assert primera.especie == "CEBADA"
        assert primera.ecorregimen == "P3"
        assert primera.sistema == "secano"

    def test_una_linea_sin_recinto_se_cuenta_y_se_dice(self, cuaderno):
        avisos = " ".join(cuaderno.avisos)
        assert "8" in avisos, "no se dice qué línea no se ha podido leer"
        assert "polígono, la parcela o el recinto" in avisos

    def test_la_especie_y_la_variedad_van_separadas(self, cuaderno):
        """El cuaderno las escribe juntas, separadas por un punto: «VEZA VELLOSA.VILLANA»."""
        con_variedad = [linea for linea in cuaderno.parcelas if linea.variedad]
        assert len(con_variedad) == 1
        assert con_variedad[0].especie == "VEZA VELLOSA"
        assert con_variedad[0].variedad == "VILLANA"

    def test_una_tierra_partida_en_trozos_se_ve_como_trozos(self, cuaderno):
        """Es el caso del recinto que en el cuaderno de verdad sale tres veces.

        En el ejemplo, el recinto 1 de la parcela 5 del polígono 1 sale tres veces: barbecho
        4,44 ha y dos trozos de avena (0,46 y 0,13). Si esto se leyera como una sola tierra de
        5,07 ha, el programa dejaría echar producto para 5 hectáreas de avena cuando hay 0,13.
        """
        assert cuaderno.tierras == 5
        partidas = cuaderno.tierras_partidas
        assert partidas == {"99-99-0-0-1-5-1": 3}
        trozos = [linea for linea in cuaderno.parcelas if linea.ref_sigpac == "99-99-0-0-1-5-1"]
        assert [linea.especie for linea in trozos] == [
            "BARBECHO TRADICIONAL",
            "AVENA",
            "AVENA",
        ]
        assert [linea.superficie_cultivada_ha for linea in trozos] == [4.44, 0.46, 0.13]

    def test_la_casilla_de_nitratos_tiene_tres_estados(self, cuaderno):
        """Puesta es sí, marcada «No» es no, y en blanco es «no lo sé».

        Es la regla de todo el programa: lo que no está comprobado no se apunta como un «no».
        Un «no» de relleno, en un cuaderno que mira un inspector, es un dato falso.
        """
        valores = [linea.zona_nitratos for linea in cuaderno.parcelas]
        assert valores.count(True) == 1
        assert valores.count(False) == 1
        assert valores.count(None) == 5

    def test_una_linea_sin_secano_ni_regadio_se_cuenta(self, cuaderno):
        sin_sistema = [linea for linea in cuaderno.parcelas if not linea.sistema]
        assert len(sin_sistema) == 1
        assert cuaderno.resumen()["sin_secano_regadio"] == 1

    def test_las_fechas_se_leen_como_fechas(self, cuaderno):
        primera = cuaderno.parcelas[0]
        assert primera.fecha_inicio == dt.date(2025, 10, 1)
        assert primera.fecha_fin == dt.date(2026, 7, 31)

    def test_la_nota_al_pie_no_se_apunta_como_parcela(self, cuaderno):
        """Debajo de la tabla hay una nota que empieza por «El titular podrá a añadir…».

        El lector tiene que parar ahí. Si no parara, esa nota sería una parcela más.
        """
        assert all(linea.especie in {
            "CEBADA", "VEZA VELLOSA", "BARBECHO TRADICIONAL", "AVENA", "MAIZ", "TRIGO BLANDO",
        } for linea in cuaderno.parcelas)

    def test_el_resumen_cuadra(self, cuaderno):
        resumen = cuaderno.resumen()
        # Los números tienen que cuadrar: 8 líneas en el papel = 7 leídas + 1 sin poder.
        assert resumen["lineas"] == 8
        assert resumen["lineas_leidas"] == 7
        assert resumen["lineas_ilegibles"] == 1
        assert resumen["tierras"] == 5
        assert resumen["hectareas_declaradas"] == 14.52
        assert resumen["hectareas_sigpac"] == 24.7
        # Y **ninguna línea de este cuaderno se queda sin superficie**: si alguna no la trajera, la suma de
        # arriba sería parcial y hay que poder decirlo (ver la prueba de al lado).
        assert resumen["lineas_sin_superficie"] == 0
        assert resumen["en_zona_nitratos"] == 1
        assert resumen["cultivos"] == [
            "AVENA",
            "BARBECHO TRADICIONAL",
            "CEBADA",
            "MAIZ",
            "TRIGO BLANDO",
            "VEZA VELLOSA",
        ]
        assert resumen["municipios"] == ["OTRO PUEBLO DE EJEMPLO", "PUEBLO DE EJEMPLO"]

    def test_una_linea_sin_superficie_no_suma_cero_hectareas(self, cuaderno):
        """**Un dato que no consta no es un cero** (03/10/2026, la misma regla que A7).

        Una línea del cuaderno de la Junta a la que le falta la casilla de «Superficie Cultivada (ha)» se
        contaba como 0 hectáreas: la suma salía **más pequeña que la verdad y parecía completa**. Ahora se
        suman solo las que la traen, y el resumen dice **cuántas líneas no la traen**, para que nadie lea una
        cifra parcial creyendo que está entera.
        """
        import dataclasses

        lineas = list(cuaderno.parcelas)
        sin_superficie = dataclasses.replace(lineas[0], superficie_cultivada_ha=None)
        cuaderno.parcelas = [sin_superficie] + lineas[1:]

        resumen = cuaderno.resumen()

        assert resumen["lineas_sin_superficie"] == 1
        assert resumen["hectareas_declaradas"] == round(
            sum(linea.superficie_cultivada_ha for linea in lineas[1:]), 2
        ), "la línea sin superficie no puede restar ni sumar nada a la cifra"
        assert resumen["hectareas_declaradas"] < 14.52, (
            "la prueba necesita que la línea que se ha vaciado tuviera superficie"
        )


class TestCuandoElFicheroNoEsElCuaderno:
    """Lo que pasa cuando alguien sube otra cosa. Se dice en cristiano, no con un error técnico."""

    def test_un_fichero_que_no_es_excel(self):
        with pytest.raises(cuaderno_cyl.CuadernoIlegible) as problema:
            cuaderno_cyl.leer_cuaderno(b"esto no es un Excel, es texto")
        assert "no se puede abrir" in str(problema.value)

    def test_un_excel_que_no_es_el_cuaderno(self):
        from openpyxl import Workbook

        libro = Workbook()
        libro.active["A1"] = "Mis cuentas"
        buffer = _bytes_de(libro)
        with pytest.raises(cuaderno_cyl.CuadernoIlegible) as problema:
            cuaderno_cyl.leer_cuaderno(buffer)
        assert "no parece el cuaderno de la Junta" in str(problema.value)

    def test_sin_fichero(self):
        with pytest.raises(cuaderno_cyl.CuadernoIlegible) as problema:
            cuaderno_cyl.leer_cuaderno(b"")
        assert "No has subido ningún fichero" in str(problema.value)


def _bytes_de(libro) -> bytes:
    import io

    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


class TestLeerPorLaApi:
    """La puerta `/leer`: mira el fichero y **no apunta nada**."""

    def test_se_lee_y_se_cuenta_lo_que_trae(self, cliente, cuenta):
        respuesta = _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/leer")
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["anio"] == 2026
        assert datos["titular"] == "EXPLOTACIÓN DE EJEMPLO"
        assert datos["registro_autonomico"] == "9999999999"
        assert datos["resumen"]["lineas"] == 8
        assert datos["resumen"]["lineas_leidas"] == 7
        assert datos["resumen"]["tierras"] == 5
        assert len(datos["lineas"]) == 7
        assert datos["lineas"][0]["ref_sigpac"] == "99-99-0-0-1-1-1"
        assert datos["lineas"][0]["especie"] == "CEBADA"

    def test_leer_no_apunta_ninguna_parcela(self, cliente, cuenta):
        """Lo más importante de esta puerta: mirar no es tocar."""
        assert _parcelas(cliente, cuenta["cabeceras"]) == []
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/leer")
        assert _parcelas(cliente, cuenta["cabeceras"]) == []

    def test_un_fichero_que_no_es_el_cuaderno_da_un_aviso_claro(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/cuaderno-cyl/leer",
            headers=cuenta["cabeceras"],
            files={"fichero": ("factura.pdf", b"%PDF-1.4 lo que sea")},
        )
        assert respuesta.status_code == 422
        assert "cuaderno" in respuesta.json()["detail"].lower()

    def test_un_excel_cualquiera_lo_dice_sin_palabras_raras(self, cliente, cuenta):
        from openpyxl import Workbook

        libro = Workbook()
        libro.active["A1"] = "Otra cosa"
        respuesta = cliente.post(
            "/api/cuaderno-cyl/leer",
            headers=cuenta["cabeceras"],
            files={"fichero": ("cuaderno.xlsx", _bytes_de(libro))},
        )
        assert respuesta.status_code == 422
        assert "no parece el cuaderno de la Junta" in respuesta.json()["detail"]

    def test_hace_falta_entrar(self, cliente):
        respuesta = cliente.post(
            "/api/cuaderno-cyl/leer",
            files={"fichero": ("cuaderno.xlsx", FICHERO_DE_EJEMPLO.read_bytes())},
        )
        assert respuesta.status_code == 401


class TestTraerLasTierras:
    """La puerta `/importar`: aquí sí se apunta."""

    def test_se_apuntan_las_tierras_del_cuaderno(self, cliente, cuenta):
        respuesta = _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["creadas"] == 7
        assert datos["ya_estaban"] == 0
        assert datos["con_cultivo"] == 0
        # La línea 8 del cuaderno no dice el recinto, así que no se puede apuntar y se cuenta.
        assert datos["sin_apuntar"] == 1
        assert datos["lineas_leidas"] == 8
        assert datos["tierras_en_el_cuaderno"] == 5
        assert datos["anio"] == 2026

        parcelas = _parcelas(cliente, cuenta["cabeceras"])
        # Siete tierras apuntadas, y **una más por cada trozo**: el recinto partido en tres.
        assert len(parcelas) == 7
        referencias = sorted(p["ref_sigpac"] for p in parcelas)
        assert referencias.count("99-99-0-0-1-5-1") == 3

    def test_la_superficie_es_la_que_se_cultiva_y_la_del_recinto_va_aparte(
        self, cliente, cuenta
    ):
        """La hoja 2.1 del cuaderno pide las dos superficies por separado, y no son lo mismo."""
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        parcelas = _parcelas(cliente, cuenta["cabeceras"])
        trozos = [p for p in parcelas if p["ref_sigpac"] == "99-99-0-0-1-5-1"]
        assert sorted(p["superficie_ha"] for p in trozos) == [0.13, 0.46, 4.44]
        # Y la del recinto entero (5,07) está guardada en los tres trozos, porque es la oficial.
        assert {p["superficie_sigpac_ha"] for p in trozos} == {5.07}

    def test_el_nombre_de_cada_tierra_sale_del_papel(self, cliente, cuenta):
        """Sin nombres inventados: lo que el agricultor ve en su cuaderno."""
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        alias = sorted(p["alias"] for p in _parcelas(cliente, cuenta["cabeceras"]))
        assert "1/1-1 CEBADA (1.09 ha)" in alias
        assert "1/5-1 AVENA (0.13 ha)" in alias

    def test_se_apunta_el_cultivo_de_cada_tierra(self, cliente, cuenta):
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        parcelas = _parcelas(cliente, cuenta["cabeceras"])
        primera = next(p for p in parcelas if p["ref_sigpac"] == "99-99-0-0-1-1-1")
        cultivos = cliente.get(
            f"/api/parcelas/{primera['id']}/cultivos", headers=cuenta["cabeceras"]
        ).json()
        assert len(cultivos) == 1
        assert cultivos[0]["especie"] == "CEBADA"
        assert cultivos[0]["sistema"] == "secano"
        assert cultivos[0]["ecorregimen"] == "P3"
        assert cultivos[0]["superficie_cultivada_ha"] == 1.09

    def test_la_zona_de_nitratos_se_apunta_solo_cuando_el_papel_la_marca(self, cliente, cuenta):
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        parcelas = _parcelas(cliente, cuenta["cabeceras"])
        por_referencia = {p["ref_sigpac"]: p["zona_vulnerable_nitratos"] for p in parcelas}
        assert por_referencia["99-99-0-0-1-1-1"] is True
        assert por_referencia["99-99-0-0-2-10-1"] is False
        # Y las que están en blanco se quedan sin saber: ni un «no» de relleno.
        assert por_referencia["99-99-0-0-1-2-1"] is None

    def test_el_pueblo_y_el_uso_vienen_del_cuaderno(self, cliente, cuenta):
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        parcelas = _parcelas(cliente, cuenta["cabeceras"])
        de_otro_pueblo = next(p for p in parcelas if p["ref_sigpac"] == "99-99-0-0-2-11-2")
        assert de_otro_pueblo["municipio"] == "OTRO PUEBLO DE EJEMPLO"
        assert de_otro_pueblo["uso_sigpac"] == "TA"
        assert de_otro_pueblo["poligono"] == 2
        assert de_otro_pueblo["numero_parcela"] == 11
        assert de_otro_pueblo["numero_recinto"] == 2

    def test_los_datos_del_titular_se_rellenan(self, cliente, cuenta):
        respuesta = _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        rellenados = respuesta.json()["titular_rellenado"]
        assert "nº de registro de la explotación" in rellenados
        assert "dirección" in rellenados

        finca = cliente.get("/api/mi-finca", headers=cuenta["cabeceras"]).json()
        assert finca["registro_autonomico"] == "9999999999"
        assert finca["direccion"] == "CALLE DEL EJEMPLO, 1"
        assert finca["localidad"] == "PUEBLO DE EJEMPLO"
        assert finca["telefono"] == "600000000"
        assert finca["correo"] == "ejemplo@ejemplo.test"

    def test_los_datos_del_titular_no_pisan_lo_que_ya_estaba(self, cliente, cuenta):
        """Lo que el agricultor ya había escrito no se toca.

        Se le cambia el nombre a la explotación (y se le deja sin teléfono) y después se trae el
        cuaderno: el nombre tiene que quedarse como él lo puso, y el teléfono se rellena porque
        estaba vacío.
        """
        finca = cliente.get("/api/mi-finca", headers=cuenta["cabeceras"]).json()
        cliente.put(
            "/api/mi-finca",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "Como lo llamo yo",
                "nif": finca["nif"],
                "provincia": "SALAMANCA",
                "municipio": "MI PUEBLO",
            },
        )
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        despues = cliente.get("/api/mi-finca", headers=cuenta["cabeceras"]).json()
        assert despues["nombre"] == "Como lo llamo yo"
        assert despues["municipio"] == "MI PUEBLO"
        assert despues["registro_autonomico"] == "9999999999"
        assert despues["telefono"] == "600000000"

    def test_subirlo_dos_veces_no_duplica_las_tierras(self, cliente, cuenta):
        """La prueba de verdad de que el emparejamiento está bien.

        Se sube el mismo cuaderno dos veces y la segunda vez no puede apuntar ni una tierra más.
        """
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        cuantas_antes = len(_parcelas(cliente, cuenta["cabeceras"]))
        segunda = _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar").json()
        assert segunda["creadas"] == 0
        assert segunda["ya_estaban"] == 7
        assert len(_parcelas(cliente, cuenta["cabeceras"])) == cuantas_antes

    def test_los_dos_trozos_de_avena_no_se_confunden_entre_ellos(self, cliente, cuenta):
        """Los dos trozos de avena del mismo recinto se distinguen por las hectáreas.

        Si la clave para saber si una tierra ya está apuntada fuera solo la referencia y el
        cultivo, los dos trozos de avena (0,46 y 0,13 ha) se tomarían por el mismo y uno de los
        dos se perdería: el agricultor tendría una tierra de menos sin enterarse.
        """
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        avena = [
            p
            for p in _parcelas(cliente, cuenta["cabeceras"])
            if p["ref_sigpac"] == "99-99-0-0-1-5-1"
        ]
        assert len(avena) == 3
        assert sorted(p["superficie_ha"] for p in avena) == [0.13, 0.46, 4.44]

    def test_una_tierra_que_ya_estaba_sin_cultivo_se_queda_con_el_del_cuaderno(
        self, cliente, cuenta
    ):
        """El agricultor apuntó su parcela por la referencia y no dijo qué siembra.

        El cuaderno lo dice, así que se aprovecha la tierra que ya tenía en vez de crear otra al
        lado: si se creara otra, tendría la misma tierra dos veces y no sabría cuál es la buena.
        """
        alta = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={
                "alias": "La de arriba",
                "ref_sigpac": "99-99-0-0-1-1-1",
                "municipio": "PUEBLO DE EJEMPLO",
                "provincia": "PROVINCIA DE EJEMPLO",
                "superficie_ha": 1.09,
            },
        )
        assert alta.status_code == 201, alta.text

        datos = _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar").json()
        assert datos["con_cultivo"] == 1
        assert datos["creadas"] == 6

        suyas = _parcelas(cliente, cuenta["cabeceras"])
        assert len(suyas) == 7  # 6 nuevas + la que ya tenía (no 8)
        la_suya = next(p for p in suyas if p["alias"] == "La de arriba")
        cultivos = cliente.get(
            f"/api/parcelas/{la_suya['id']}/cultivos", headers=cuenta["cabeceras"]
        ).json()
        assert [c["especie"] for c in cultivos] == ["CEBADA"]

    def test_si_la_tierra_ya_tenia_otro_cultivo_no_se_cambia(self, cliente, cuenta):
        """Si el agricultor dice que ahí hay otra cosa, manda lo suyo.

        Puede ser que el cuaderno de la Junta esté sin actualizar, o que él haya cambiado lo que
        siembra. En cualquier caso, la tierra ya tiene cultivo declarado en esa campaña: el
        cuaderno no lo pisa, y se apunta como una tierra nueva si es una línea distinta.
        """
        parcela = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={
                "alias": "Mi tierra",
                "ref_sigpac": "99-99-0-0-1-1-1",
                "superficie_ha": 1.09,
            },
        ).json()
        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        # La campaña del cuaderno (2026) es la del año en curso en el ejemplo, así que se declara
        # el cultivo que él dice.
        cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={"campana_id": campana["id"], "especie": "GIRASOL"},
        )

        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        cultivos = cliente.get(
            f"/api/parcelas/{parcela['id']}/cultivos", headers=cuenta["cabeceras"]
        ).json()
        assert [c["especie"] for c in cultivos] == ["GIRASOL"]

    def test_lo_que_no_se_puede_apuntar_se_cuenta(self, cliente, cuenta):
        """Los números del resumen tienen que cuadrar, y lo que no entra se dice.

        El cuaderno de ejemplo trae 8 líneas y una no dice el recinto: 7 se apuntan y 1 se queda
        fuera. Si el resumen dijera «8» sin más, el agricultor no sabría que le falta una tierra.
        """
        datos = _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar").json()
        assert datos["sin_apuntar"] == 1
        assert datos["lineas_leidas"] == datos["creadas"] + datos["sin_apuntar"]
        assert any("no dicen el polígono" in aviso for aviso in datos["avisos"])

    def test_se_apunta_la_campana_del_cuaderno(self, cliente, cuenta):
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        campanas = cliente.get("/api/campanas", headers=cuenta["cabeceras"]).json()
        assert 2026 in [c["anio"] for c in campanas]

    def test_queda_apuntado_en_la_auditoria(self, cliente, cuenta, db_sesion):
        """Un alta de 7 tierras de golpe tiene que poder explicarse después."""
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        acciones = [
            fila.accion
            for fila in db_sesion.query(models.Auditoria).all()
        ]
        assert "traer_tierras_del_cuaderno_de_la_junta" in acciones
        assert "crear_desde_el_cuaderno_de_la_junta" in acciones

    def test_cada_explotacion_ve_solo_lo_suyo(self, cliente, cuenta, crear_cuenta):
        _subir(cliente, cuenta["cabeceras"], "/api/cuaderno-cyl/importar")
        otra = crear_cuenta("otro@ejemplo.test", nombre="Otra finca")
        assert _parcelas(cliente, otra["cabeceras"]) == []
        # Y la otra finca puede traer su cuaderno sin pisar el de la primera.
        _subir(cliente, otra["cabeceras"], "/api/cuaderno-cyl/importar")
        assert len(_parcelas(cliente, otra["cabeceras"])) == 7
        assert len(_parcelas(cliente, cuenta["cabeceras"])) == 7


class TestLosTextosDeLaPantalla:
    """Traer el cuaderno es una pantalla, y las pantallas se sirven con sus textos."""

    def test_los_textos_se_sirven(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        assert datos["cuaderno_cyl"]["titulo"] == textos.CUADERNO_CYL["titulo"]
        assert datos["cuaderno_cyl"]["confirmar"]

    def test_se_dice_de_donde_se_descarga(self, cliente):
        datos = cliente.get("/api/cuaderno-cyl/estado").json()
        assert "particulares.ayg.jcyl.es" in datos["de_donde"]
        assert ".xlsx" in datos["tipos_de_fichero"]

    def test_los_textos_no_llevan_jerga(self):
        for clave, valor in textos.CUADERNO_CYL.items():
            assert not textos.palabras_prohibidas_encontradas(valor), (clave, valor)
