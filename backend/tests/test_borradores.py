"""Tests del dictado: de una frase a un apunte a medio hacer.

Es la aplicación práctica de forzar la salida estructurada. Lo que se comprueba aquí,
sobre todo, es lo que NO hace: no se inventa un producto, no se inventa una fecha y no
adivina si "dos litros" son la dosis o el total.

Esa última es la prueba más importante de este fichero. Confundir la dosis con la
cantidad total es un error de diez veces en el dato que la ley mira para decidir si
una aplicación fue legal.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pytest

from app import borradores


# --------------------------------------------------------------------------
# Catálogos de mentira, para no levantar ni base de datos ni servidor
# --------------------------------------------------------------------------


@dataclass
class ParcelaFalsa:
    id: int
    alias: str
    superficie_ha: float


@dataclass
class ProductoFalso:
    id: int
    nombre_comercial: str
    numero_registro: str = "24.123"
    plazo_seguridad_dias: int = 21


@dataclass
class AbonoFalso:
    id: int
    nombre: str


PARCELAS = [
    ParcelaFalsa(1, "El Prado", 2.43),
    ParcelaFalsa(2, "El Prado Alto", 1.10),
    ParcelaFalsa(3, "La Vega", 5.00),
]
PRODUCTOS = [
    ProductoFalso(7, "Ejemplo 25 EC"),
    ProductoFalso(8, "Herbicida Total"),
]
ABONOS = [AbonoFalso(4, "Nitrato amónico 33,5%")]

HOY = dt.date(2026, 9, 21)


def borrador(texto: str) -> dict:
    return borradores.redacta_borrador(
        texto, parcelas=PARCELAS, productos=PRODUCTOS, abonos=ABONOS, hoy=HOY
    )


# --------------------------------------------------------------------------
# Normalización y números
# --------------------------------------------------------------------------


class TestNormalizacion:
    def test_quita_las_tildes(self):
        assert borradores.sin_tildes("Pulgón en el trigo") == "pulgon en el trigo"

    def test_la_ene_tambien_se_normaliza(self):
        # Sin esto, "araño rojo" no encontraría "arano rojo" y la plaga no se vería.
        assert borradores.sin_tildes("Araño") == "arano"


class TestCantidades:
    def test_lee_las_cifras_con_unidad(self):
        cantidades = borradores.extrae_cantidades("he echado 2,5 litros")
        assert len(cantidades) == 1
        assert cantidades[0].valor == 2.5
        assert cantidades[0].unidad == "L"

    def test_lee_los_numeros_escritos_con_palabra(self):
        """Un dictado casi nunca devuelve cifras: devuelve "dos litros"."""
        cantidades = borradores.extrae_cantidades("he echado dos litros")
        assert len(cantidades) == 1
        assert cantidades[0].valor == 2

    def test_lee_el_medio(self):
        cantidades = borradores.extrae_cantidades("medio litro de producto")
        assert cantidades[0].valor == 0.5

    def test_lee_las_hectareas(self):
        cantidades = borradores.extrae_cantidades("en dos hectareas y media")
        assert cantidades[0].valor == 2
        assert cantidades[0].unidad == "ha"

    def test_una_palabra_que_no_es_un_numero_no_cuenta(self):
        assert borradores.extrae_cantidades("he echado producto en el trigo") == []

    def test_la_primera_de_cada_unidad_es_la_que_vale(self):
        por_unidad = borradores.extrae_por_unidad("2 litros en 3 hectareas")
        assert por_unidad == {"L": 2, "ha": 3}


# --------------------------------------------------------------------------
# Fechas
# --------------------------------------------------------------------------


class TestFechas:
    def test_hoy(self):
        assert borradores.extrae_fecha("hoy he echado producto", HOY) == HOY

    def test_ayer(self):
        assert borradores.extrae_fecha("ayer eche herbicida", HOY) == dt.date(2026, 9, 20)

    def test_anteayer(self):
        assert borradores.extrae_fecha("anteayer", HOY) == dt.date(2026, 9, 19)

    def test_un_dia_con_su_mes(self):
        assert borradores.extrae_fecha("lo eche el 3 de mayo", HOY) == dt.date(2026, 5, 3)

    def test_el_mes_escrito_con_tilde(self):
        assert borradores.extrae_fecha("el 3 de mayo", HOY) == dt.date(2026, 5, 3)

    def test_la_fecha_en_cifras(self):
        assert borradores.extrae_fecha("el 03/05", HOY) == dt.date(2026, 5, 3)

    def test_la_fecha_con_ano(self):
        assert borradores.extrae_fecha("el 03/05/2025", HOY) == dt.date(2025, 5, 3)

    def test_una_fecha_lejana_en_el_futuro_se_entiende_del_ano_pasado(self):
        """En enero, "lo eché en diciembre" es del año pasado, no del que viene.

        Doce meses de diferencia no tienen sentido en un cuaderno, y la campaña
        agrícola no llega tan lejos.
        """
        enero = dt.date(2026, 1, 15)
        assert borradores.extrae_fecha("el 20 de diciembre", enero) == dt.date(2025, 12, 20)

    def test_sin_fecha_no_se_inventa_ninguna(self):
        assert borradores.extrae_fecha("he echado producto en el prado", HOY) is None

    def test_una_fecha_imposible_no_revienta(self):
        assert borradores.extrae_fecha("el 31 de febrero", HOY) is None


# --------------------------------------------------------------------------
# Reconocer parcelas, productos y abonos
# --------------------------------------------------------------------------


class TestReconocerNombres:
    def test_encuentra_la_parcela(self):
        encontrada, bruto = borradores.busca_por_nombre("en el prado", PARCELAS, "alias")
        assert encontrada.id == 1
        assert bruto == "prado"

    def test_gana_el_nombre_mas_largo(self):
        """"El Prado Alto" no puede quedar como "El Prado"."""
        encontrada, _ = borradores.busca_por_nombre("en el prado alto", PARCELAS, "alias")
        assert encontrada.id == 2

    def test_encuentra_el_producto_aunque_no_diga_la_formulacion(self):
        """Un agricultor dice "ejemplo 25", no "Ejemplo 25 EC"."""
        encontrado, _ = borradores.busca_por_nombre("con ejemplo 25", PRODUCTOS, "nombre_comercial")
        assert encontrado.id == 7

    def test_encuentra_el_abono_sin_la_riqueza(self):
        """"Nitrato amónico 33,5%" se dice "nitrato amonico"."""
        encontrado, _ = borradores.busca_por_nombre(
            "he abonado con nitrato amonico", ABONOS, "nombre"
        )
        assert encontrado.id == 4

    def test_lo_que_no_esta_no_se_inventa(self):
        encontrado, _ = borradores.busca_por_nombre("con roundup", PRODUCTOS, "nombre_comercial")
        assert encontrado is None

    def test_un_nombre_dentro_de_otra_palabra_no_cuenta(self):
        """Si no, la parcela "El Prado" aparecería cada vez que alguien dice "emprado"."""
        encontrado, _ = borradores.busca_por_nombre("el campo estaba emprado", PARCELAS, "alias")
        assert encontrado is None

    def test_hacen_falta_todas_las_palabras_del_nombre(self):
        """"prado" a secas no puede ser "El Prado Alto"."""
        encontrado, _ = borradores.busca_por_nombre("en el prado", PARCELAS, "alias")
        assert encontrado.id == 1, "debería quedarse con la que encaja entera"

    def test_da_igual_como_se_escriba(self):
        encontrado, _ = borradores.busca_por_nombre("en la VEGA", PARCELAS, "alias")
        assert encontrado.id == 3

    def test_un_nombre_sin_palabras_significativas_no_se_busca(self):
        """Un nombre de dos letras coincidiría con cualquier cosa."""
        raro = [ParcelaFalsa(9, "A1", 1.0)]
        encontrado, _ = borradores.busca_por_nombre("esto es a1 y mas cosas", raro, "alias")
        assert encontrado is None


# --------------------------------------------------------------------------
# Reconocer la intención
# --------------------------------------------------------------------------


class TestIntencion:
    def test_reconoce_un_tratamiento(self):
        assert borradores.reconoce_tipo("hoy he echado herbicida") == "tratamiento"

    def test_reconoce_un_abono(self):
        assert borradores.reconoce_tipo("he abonado el trigo") == "fertilizacion"

    def test_reconoce_una_cosecha(self):
        assert borradores.reconoce_tipo("he cogido la cosecha") == "cosecha"

    def test_reconoce_una_siembra(self):
        assert borradores.reconoce_tipo("he sembrado el trigo") == "siembra"

    def test_reconoce_un_riego(self):
        assert borradores.reconoce_tipo("he regado el prado") == "riego"

    def test_la_justificacion_del_aviso(self):
        assert borradores.reconoce_justificacion("por el aviso de la junta") == "Aviso de la Junta"

    def test_la_justificacion_del_tecnico(self):
        assert (
            borradores.reconoce_justificacion("me lo dijo mi tecnico")
            == "Me lo dijo mi técnico"
        )

    def test_la_justificacion_por_haberlo_visto(self):
        assert (
            borradores.reconoce_justificacion("habia pulgon en las hojas")
            == "Vi la plaga o la hierba en el campo"
        )

    def test_sin_motivo_no_se_inventa_la_justificacion(self):
        assert borradores.reconoce_justificacion("he echado producto en el prado") is None

    def test_reconoce_la_plaga(self):
        assert borradores.reconoce_plaga("habia pulgon") == "Pulgon"

    def test_reconoce_la_mala_hierba(self):
        assert borradores.reconoce_plaga("con mucha avena") == "Avena"


# --------------------------------------------------------------------------
# El borrador completo
# --------------------------------------------------------------------------


class TestBorrador:
    def test_una_frase_completa_sale_casi_entera(self):
        resultado = borrador(
            "hoy he echado ejemplo 25 en el prado, dos litros por hectarea, habia pulgon"
        )
        assert resultado["tipo"] == "tratamiento"
        assert resultado["datos"]["parcela_id"] == 1
        assert resultado["datos"]["producto_id"] == 7
        assert resultado["datos"]["fecha"] == "2026-09-21"
        assert resultado["datos"]["dosis"] == 2
        assert resultado["datos"]["plaga"] == "Pulgon"
        assert resultado["datos"]["justificacion"] == "Vi la plaga o la hierba en el campo"
        assert resultado["falta"] == []
        assert resultado["fuente"] == "reglas"

    def test_cada_dato_entendido_viene_con_su_campo(self):
        resultado = borrador("hoy he echado ejemplo 25 en el prado")
        campos = {entrada["campo"] for entrada in resultado["entendido"]}
        assert {"parcela_id", "producto_id", "fecha"} <= campos

    def test_lo_entendido_dice_que_palabras_lo_delataron(self):
        resultado = borrador("hoy he echado ejemplo 25 en el prado")
        de_parcela = next(e for e in resultado["entendido"] if e["campo"] == "parcela_id")
        assert de_parcela["bruto"].lower() == "prado"
        assert de_parcela["valor"] == "El Prado"

    def test_lo_que_no_se_entiende_se_queda_en_blanco_y_se_pregunta(self):
        resultado = borrador("hoy he echado algo en el prado")
        assert "producto_id" not in resultado["datos"]
        assert "producto_id" in [item["campo"] for item in resultado["falta"]]

    def test_una_frase_incomprensible_no_inventa_nada(self):
        resultado = borrador("bla bla bla")
        assert resultado["datos"] == {}
        assert resultado["entendido"] == []
        assert resultado["falta"]

    def test_un_producto_desconocido_no_se_inventa(self):
        resultado = borrador("he echado roundup en el prado")
        assert "producto_id" not in resultado["datos"]

    def test_una_parcela_desconocida_no_se_inventa(self):
        resultado = borrador("he echado ejemplo 25 en la finca de mi tio")
        assert "parcela_id" not in resultado["datos"]


class TestLaTrampaDeLosLitros:
    """"Dos litros" puede ser la dosis o el total. Aquí no se adivina."""

    def test_con_por_hectarea_es_la_dosis(self):
        resultado = borrador("he echado dos litros por hectarea en el prado")
        assert resultado["datos"]["dosis"] == 2

    def test_con_la_barra_de_hectarea_tambien(self):
        resultado = borrador("he echado 2 l/ha en el prado")
        assert resultado["datos"]["dosis"] == 2

    def test_sin_saber_la_superficie_no_se_coloca_y_se_avisa(self):
        """Confundir dosis con total es un error de diez veces. Se pregunta."""
        resultado = borrador("he echado dos litros en el prado")
        assert "dosis" not in resultado["datos"]
        sin_sitio = [e for e in resultado["entendido"] if e["campo"] is None]
        assert sin_sitio, "tiene que quedar constancia de que se ha oído"
        assert sin_sitio[0]["valor"] == 2

    def test_con_la_superficie_se_reparte_y_se_ensena_la_cuenta(self):
        resultado = borrador("he echado dos litros en dos hectareas del prado")
        assert resultado["datos"]["dosis"] == 1
        de_dosis = next(e for e in resultado["entendido"] if e["campo"] == "dosis")
        assert "2" in de_dosis["bruto"]
        assert "2.0 ha" in de_dosis["bruto"] or "2 ha" in de_dosis["bruto"]


class TestAbonos:
    def test_reconoce_el_abono_y_los_kilos(self):
        resultado = borrador("he abonado con nitrato amonico, 300 kilos por hectarea")
        assert resultado["tipo"] == "fertilizacion"
        assert resultado["datos"]["fertilizante_id"] == 4
        assert resultado["datos"]["kg_ha_producto"] == 300

    def test_las_toneladas_se_pasan_a_kilos(self):
        resultado = borrador("he echado una tonelada de nitrato amonico")
        assert resultado["datos"]["kg_ha_producto"] == 1000

    def test_un_abono_desconocido_no_se_inventa(self):
        resultado = borrador("he echado urea en el prado")
        assert "fertilizante_id" not in resultado["datos"]


class TestSuperficie:
    def test_la_superficie_dicha_se_respeta(self):
        resultado = borrador("he echado ejemplo 25 en dos hectareas de la vega")
        assert resultado["datos"]["superficie_tratada_ha"] == 2

    def test_no_se_puede_tratar_mas_de_lo_que_tiene_la_parcela(self):
        """La parcela manda: es la superficie que consta.

        Si el dictado dice nueve hectáreas en una parcela de 2,43, se queda en 2,43 y
        el servidor lo volverá a comprobar. Dejar pasar el nueve sería dejar pasar un
        dato imposible.
        """
        resultado = borrador("he echado ejemplo 25 en nueve hectareas del prado")
        assert resultado["datos"]["superficie_tratada_ha"] == 2.43

    def test_en_los_abonos_la_superficie_va_en_su_campo(self):
        resultado = borrador("he abonado con nitrato amonico tres hectareas de la vega")
        assert resultado["datos"]["superficie_ha"] == 3
        assert "superficie_tratada_ha" not in resultado["datos"]


class TestNumerosParaLeer:
    """"Dos litros" es un entero y "2,5 litros" un decimal. Los dos se leen igual."""

    def test_un_entero_no_lleva_decimales_de_adorno(self):
        assert borradores.numero_para_leer(2) == "2"

    def test_un_decimal_va_con_coma(self):
        assert borradores.numero_para_leer(2.5) == "2,5"

    def test_cuatro_decimales_se_respetan(self):
        # La superficie del SIGPAC viene con cuatro decimales (2,4317 ha).
        assert borradores.numero_para_leer(2.4317) == "2,4317"

    def test_nunca_sale_un_punto_decimal(self):
        assert "." not in borradores.numero_para_leer(2.43)

    def test_la_cuenta_de_la_dosis_se_ensena_sin_puntos(self):
        resultado = borrador("he echado dos litros en dos hectareas del prado")
        de_dosis = next(e for e in resultado["entendido"] if e["campo"] == "dosis")
        assert de_dosis["bruto"] == "2 L en 2 ha"
        assert "." not in de_dosis["bruto"]


class TestLoQueFalta:
    def test_un_tratamiento_necesita_parcela_fecha_motivo_y_producto(self):
        resultado = borrador("he echado producto")
        faltan = {item["campo"] for item in resultado["falta"]}
        assert faltan == {"parcela_id", "fecha", "justificacion", "producto_id"}

    def test_un_abono_necesita_sus_cuatro_cosas(self):
        resultado = borrador("he abonado")
        faltan = {item["campo"] for item in resultado["falta"]}
        assert faltan == {"parcela_id", "fecha", "fertilizante_id", "kg_ha_producto"}

    def test_cada_cosa_que_falta_trae_su_pregunta(self):
        resultado = borrador("he echado producto")
        for item in resultado["falta"]:
            assert item["etiqueta"], f"{item['campo']} no dice qué preguntar"

    def test_cuando_esta_todo_no_falta_nada(self):
        resultado = borrador(
            "hoy he echado dos litros por hectarea de ejemplo 25 en el prado, habia pulgon"
        )
        assert resultado["falta"] == []


# --------------------------------------------------------------------------
# El dictado por la API
# --------------------------------------------------------------------------


class TestElDictadoPorLaApi:
    """La lógica se prueba arriba sin servidor. Aquí se prueba que esté bien servida."""

    RUTA = "/api/borradores/desde-texto"

    def test_hace_falta_entrar(self, cliente):
        respuesta = cliente.post(self.RUTA, json={"texto": "he echado producto"})
        assert respuesta.status_code == 401

    def test_una_frase_que_no_es_frase_se_rechaza(self, cliente, cuenta):
        respuesta = cliente.post(
            self.RUTA, headers=cuenta["cabeceras"], json={"texto": "a"}
        )
        assert respuesta.status_code == 422

    def test_entiende_una_frase_de_verdad(self, cliente, cuenta, parcela, producto):
        respuesta = cliente.post(
            self.RUTA,
            headers=cuenta["cabeceras"],
            json={
                "texto": (
                    "hoy he echado ejemplo 25 ec en el prado, dos litros por hectarea, "
                    "habia pulgon"
                )
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["tipo"] == "tratamiento"
        assert datos["datos"]["parcela_id"] == parcela["id"]
        assert datos["datos"]["producto_id"] == producto["id"]
        assert datos["datos"]["dosis"] == 2
        assert datos["falta"] == []
        assert datos["fuente"] == "reglas"

    def test_no_guarda_nada_hasta_que_el_agricultor_lo_confirme(
        self, cliente, cuenta, parcela, producto
    ):
        """Un borrador es un borrador: no escribe en el cuaderno."""
        cliente.post(
            self.RUTA,
            headers=cuenta["cabeceras"],
            json={"texto": "hoy he echado ejemplo 25 en el prado, habia pulgon"},
        )
        listado = cliente.get("/api/tratamientos", headers=cuenta["cabeceras"])
        assert listado.json() == []

    def test_solo_ve_los_datos_de_su_finca(self, cliente, cuenta, parcela, producto, crear_cuenta):
        """El borrador no puede proponer una parcela o un producto de otro agricultor."""
        otro = crear_cuenta("otro@ejemplo.test")
        respuesta = cliente.post(
            self.RUTA,
            headers=otro["cabeceras"],
            json={"texto": "hoy he echado ejemplo 25 en el prado"},
        )
        datos = respuesta.json()
        assert "parcela_id" not in datos["datos"]
        assert "producto_id" not in datos["datos"]

    def test_cada_dato_entendido_trae_su_pregunta_escrita(
        self, cliente, cuenta, parcela, producto
    ):
        """La interfaz no compone frases: las recibe ya escritas."""
        respuesta = cliente.post(
            self.RUTA,
            headers=cuenta["cabeceras"],
            json={"texto": "hoy he echado ejemplo 25 en el prado"},
        )
        datos = respuesta.json()
        assert datos["entendido"]
        for entrada in datos["entendido"]:
            assert entrada["pregunta"], f"{entrada['etiqueta']} no trae pregunta"
            assert entrada["valor"]

    def test_lo_que_falta_se_pregunta_con_la_misma_frase_que_el_asistente(
        self, cliente, cuenta, parcela
    ):
        respuesta = cliente.post(
            self.RUTA,
            headers=cuenta["cabeceras"],
            json={"texto": "hoy he echado producto en el prado"},
        )
        preguntas = [item["pregunta"] for item in respuesta.json()["falta"]]
        assert preguntas
        assert all(preguntas)
        assert "¿Qué producto has echado?" in preguntas

    def test_una_frase_incomprensible_lo_dice_sin_inventar_nada(self, cliente, cuenta):
        respuesta = cliente.post(
            self.RUTA, headers=cuenta["cabeceras"], json={"texto": "bla bla bla"}
        )
        datos = respuesta.json()
        assert datos["datos"] == {}
        assert datos["entendido"] == []
        assert datos["nada_entendido"]

    def test_las_fechas_se_ensenan_como_las_lee_una_persona(self, cliente, cuenta, parcela, producto):
        respuesta = cliente.post(
            self.RUTA,
            headers=cuenta["cabeceras"],
            json={"texto": "el 3 de mayo he echado ejemplo 25 en el prado"},
        )
        de_fecha = next(e for e in respuesta.json()["entendido"] if e["campo"] == "fecha")
        assert de_fecha["valor"] == "03/05/2026"

    def test_los_numeros_se_ensenan_con_coma(self, cliente, cuenta, parcela, producto):
        """Los enteros que salen de una palabra ("dos litros") también se formatean."""
        respuesta = cliente.post(
            self.RUTA,
            headers=cuenta["cabeceras"],
            json={"texto": "hoy he echado dos litros por hectarea de ejemplo 25 en el prado"},
        )
        de_dosis = next(
            e for e in respuesta.json()["entendido"] if e["campo"] == "dosis"
        )
        assert de_dosis["valor"] == "2,00"
        assert de_dosis["bruto"] == "2 L/ha"
