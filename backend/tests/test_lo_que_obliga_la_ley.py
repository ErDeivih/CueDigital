"""Lo que el programa le dice al agricultor sobre la ley tiene que ser verdad, y estar a la vista.

Existe por dos motivos concretos, los dos de verdad:

1. **La frase que más se malinterpreta.** Mucha gente cree que está obligada a mandar el cuaderno a
   la Junta por internet. La ley dice lo contrario: lo obligatorio es **tener** el registro y poder
   enseñarlo; **enviarlo es voluntario** (artículo 10.2 del Real Decreto 1054/2022), y se puede
   llevar con **un programa propio** que tenga el contenido mínimo del anexo II (artículo 10.3). Si
   esa frase desaparece de la pantalla, el agricultor vuelve a creer que está obligado a usar la
   ventanilla de la Junta.

2. **Las fechas, que son lo que más fácilmente se queda viejo.** El programa enseña hasta cuándo se
   puede usar papel y desde cuándo el registro tiene que ser electrónico, y esa fecha **cambió dos
   veces**: el Real Decreto 34/2025 (21/01/2025) decía «hasta el 31 de diciembre de 2025» y el Real
   Decreto 1039/2025 (19/11/2025) lo dejó en **31/12/2026**. Una fecha escrita de memoria es una
   fecha que engaña a quien la lee.

Por eso las fechas están en `catalogos.py` **con su norma al lado** y aquí se comparan con
`docs/LO_QUE_OBLIGA_LA_LEY.md`, que es donde están las comillas literales de cada artículo y los
enlaces al BOE. Cambiar una fecha en el programa sin cambiar el documento rompe este test, y eso es
exactamente lo que tiene que pasar.
"""

from __future__ import annotations

from pathlib import Path

from app import catalogos, textos

RAIZ = Path(__file__).resolve().parents[2]
DOCUMENTO = RAIZ / "docs" / "LO_QUE_OBLIGA_LA_LEY.md"
README = RAIZ / "README.md"
TRASPASO = RAIZ / "docs" / "TRASPASO_A_OTRO_AGENTE.md"
CORREO = RAIZ / "docs" / "CORREO_LISTO_PARA_ENVIAR.md"


def _documento() -> str:
    return DOCUMENTO.read_text(encoding="utf-8")


def _plano(texto: str) -> str:
    """El texto sin negritas ni saltos de línea, para poder buscar frases enteras.

    Los documentos llevan `**negritas**` y están partidos en líneas a 100 columnas. Buscar una
    comilla literal en ellos sin quitar eso falla por motivos que no tienen nada que ver con lo que
    se quiere comprobar, y un test que falla por el formato deja de mirarse.
    """
    return " ".join(texto.replace("**", "").split())


class TestLaPantallaDiceLaVerdad:
    """Que se pueda leer sin saber dónde buscar: en Mi cuaderno y en la ayuda."""

    def test_mi_cuaderno_dice_que_mandarlo_es_voluntario(self, cliente):
        """Con el artículo delante, para que quien lo lea pueda comprobarlo en el BOE."""
        cuaderno = cliente.get("/api/interfaz").json()["cuaderno"]
        pista = cuaderno["ley_pista"]
        assert "obligatorio" in pista, "no dice qué es obligatorio"
        assert "voluntario" in pista, "no dice que mandarlo es voluntario"
        assert "artículo 10.2" in pista, "sin el artículo no se puede comprobar"
        assert "1054/2022" in pista, "y sin la norma tampoco"

    def test_la_ayuda_lo_explica_con_los_articulos(self, cliente):
        ayuda = cliente.get("/api/interfaz").json()["ayuda"]["pantalla"]
        for clave in (
            "ley_titulo",
            "ley_llevar",
            "ley_mandar",
            "ley_programa",
            "ley_fechas",
            "ley_cuando_obligatorio",
            "ley_sin_confirmar",
        ):
            assert clave in ayuda, f"a la ayuda le falta {clave}"
        assert "artículo 10.2" in ayuda["ley_mandar"]
        assert "1054/2022" in ayuda["ley_mandar"]
        assert "artículo 10.3" in ayuda["ley_programa"]
        assert "anexo II" in ayuda["ley_programa"], "el anexo II es lo que hace legal el programa"

    def test_el_documento_dice_cuanto_tiempo_se_guardan_los_papeles(self):
        """El plazo de conservación estaba como «falta confirmar» y ya está confirmado (ronda 35).

        Se comprueba la comilla literal del artículo 16.3 y, sobre todo, que **el documento diga de
        dónde sale** con su dirección y su fecha de comprobación: un dato legal sin la norma delante
        no vale para nada.
        """
        plano = _plano(_documento())
        assert "al menos durante los 3 años siguientes a su fecha de emisión" in plano, (
            "el documento no lleva la comilla literal del plazo de conservación"
        )
        assert "artículo 16.3" in plano, "no dice el artículo"
        assert "BOE-A-2012-11605" in plano, "no lleva la dirección oficial de la norma"
        assert "27/09/2026" in plano, "no dice cuándo se comprobó"
        # Y el plazo de volcado, que es del mismo artículo y decide cosas el día que se presente.
        assert "un mes desde la fecha de realización de los tratamientos" in plano

    def test_la_aplicacion_explica_cuanto_tiempo_se_guardan_los_papeles(self, cliente):
        """Y no solo en el documento: en la ayuda que lee el agricultor, con el artículo delante."""
        porques = cliente.get("/api/interfaz").json()["ayuda"]["porques"]
        assert "cuanto_tiempo_guardar" in porques, "la ayuda no lo explica"
        texto = porques["cuanto_tiempo_guardar"]
        assert "3 años" in texto
        assert "artículo 16.3" in texto, "sin el artículo no se puede comprobar"
        assert "1311/2012" in texto, "y sin la norma tampoco"
        # Y entra en el test general de jerga, como todos los textos que lee el agricultor.
        assert textos.PORQUE["cuanto_tiempo_guardar"] in textos.textos_visibles()

    def test_la_ayuda_dice_cuando_sera_obligatorio_de_verdad(self, cliente):
        """Y no solo «es voluntario»: también cuándo dejará de serlo, que es lo que decide cosas.

        Los umbrales son los de la disposición final única del Real Decreto 1054/2022 (redacción del
        Real Decreto 34/2025): más de 30 ha de cultivo, más de 5 ha de regadío o invernaderos de más
        de 0,1 ha.
        """
        texto = cliente.get("/api/interfaz").json()["ayuda"]["pantalla"]["ley_cuando_obligatorio"]
        assert "30 hectáreas" in texto
        assert "5 hectáreas de regadío" in texto
        assert "0,1 hectáreas" in texto
        assert "voluntario" in texto, "para las fincas pequeñas sigue siendo voluntario"

    def test_la_ayuda_dice_lo_que_todavia_no_esta_aclarado(self, cliente):
        """Prometer que «no hay que mandar nada nunca» sería tan falso como lo contrario.

        El artículo 16.1.5 del Real Decreto 1311/2012 dice que los datos «deberán ser
        proporcionados, al menos, con carácter mensual», y eso encaja mal con los artículos 10.2 y
        10.3 del Real Decreto 1054/2022. Mientras la Junta no conteste, se dice tal cual.
        """
        texto = cliente.get("/api/interfaz").json()["ayuda"]["pantalla"]["ley_sin_confirmar"]
        assert "preguntado" in texto
        assert "no está aclarada" in texto

    def test_no_se_dice_en_ninguna_pantalla_que_haya_que_mandarlo(self):
        """La regla, comprobada en todos los textos visibles de una vez.

        Es la forma de que la frase no se cuele en una pantalla nueva: se revisan todas.
        """
        prohibidas = (
            "hay que mandar",
            "obligatorio mandar",
            "obligatorio enviar",
            "es obligatorio enviarlo",
            "tienes que enviarlo",
        )
        for texto in textos.textos_visibles():
            bajo = texto.lower()
            for frase in prohibidas:
                assert frase not in bajo, f"un texto dice «{frase}»: {texto}"


class TestLasFechasSonLasDeLaNorma:
    def test_los_plazos_que_sirve_la_api_son_los_comprobados(self, cliente):
        plazos = cliente.get("/api/interfaz").json()["plazos_legales"]
        assert plazos["cuaderno_en_papel_hasta"] == "31/12/2026"
        assert plazos["productos_electronico_desde"] == "01/01/2027"
        assert plazos["abonos_obligatorio_desde"] == "01/01/2026"
        assert plazos["plan_de_abonado_obligatorio_desde"] == "01/09/2026"
        assert plazos["enviar_a_la_junta_es_voluntario"] is True
        assert plazos["se_puede_usar_un_programa_propio"] is True

    def test_las_constantes_llevan_su_norma_al_lado(self):
        """Las fechas viven en `catalogos.py`, y ahí tiene que estar escrito de dónde salen.

        Sin esto, el siguiente que toque una fecha no tiene forma de saber si es un dato comprobado
        o un número que alguien recordaba.
        """
        fuente = (RAIZ / "backend" / "app" / "catalogos.py").read_text(encoding="utf-8")
        trozo = fuente[fuente.index("Plazos legales") :]
        assert "RD 1311/2012" in trozo
        assert "1039/2025" in trozo, "la fecha del papel la cambió el RD 1039/2025, no el 34/2025"
        assert "RD 1051/2022" in trozo
        assert "LO_QUE_OBLIGA_LA_LEY.md" in trozo, "y el documento donde está todo comprobado"

    def test_el_documento_lleva_las_comillas_y_los_enlaces(self):
        documento = _plano(_documento())
        for norma in (
            "BOE-A-2022-23054",  # RD 1054/2022, el del CUE
            "BOE-A-2012-11605",  # RD 1311/2012, el del registro de tratamientos
            "BOE-A-2022-23052",  # RD 1051/2022, el de la nutrición sostenible
            "BOE-A-2025-23421",  # RD 1039/2025, el que movió la fecha del papel
        ):
            assert norma in documento, f"el documento no cita {norma}"
        # Los artículos se citan a veces al principio de la frase («Artículo 10.3 ...»), así que la
        # comprobación de la cita va sin distinguir mayúsculas; las comillas literales, con ellas.
        bajo = documento.lower()
        for cita in ("artículo 10.2", "artículo 10.3", "anexo ii"):
            assert cita in bajo, f"el documento no cita {cita}"
        assert "decidirán de forma voluntaria" in documento, "falta la comilla literal del 10.2"
        assert "en soporte papel hasta el 31 de diciembre de 2026" in documento
        assert "24/09/2026" in documento, "hay que decir cuándo se comprobó"

    def test_las_fechas_del_documento_son_las_del_programa(self):
        documento = _documento()
        for fecha in (
            catalogos.FECHA_FIN_CUADERNO_PAPEL,
            catalogos.FECHA_REGISTRO_ELECTRONICO_FITOSANITARIOS,
            catalogos.FECHA_REGISTRO_OBLIGATORIO_FERTILIZACION,
            catalogos.FECHA_PLAN_DE_ABONADO_OBLIGATORIO,
        ):
            escrita = fecha.strftime("%d/%m/%Y")
            assert escrita in documento, (
                f"el programa usa {escrita} y el documento comprobado no la recoge: "
                "una de las dos está vieja"
            )

    def test_el_plan_de_abono_dice_desde_cuando_es_obligatorio(self):
        """El plan dejó de ser cosa solo del regadío el 01/09/2026: el texto lo tiene que decir."""
        texto = textos.PLAN["obligatorio"]
        assert "1 de septiembre de 2026" in texto
        assert "regadío" in texto, "y el caso del regadío, que empezó antes"


class TestLaDocumentacionNoSeQuedaVieja:
    def test_el_readme_cita_las_normas_y_lleva_al_documento(self):
        readme = _plano(README.read_text(encoding="utf-8")).lower()
        assert "lo_que_obliga_la_ley.md" in readme, "el README tiene que llevar al documento"
        assert "artículo 10.2" in readme
        assert "artículo 10.3" in readme
        assert "31/12/2026" in readme
        assert "01/01/2027" in readme
        assert "01/09/2026" in readme, "el plan de abono también tiene fecha"

    def test_el_traspaso_cita_las_normas(self):
        traspaso = _plano(TRASPASO.read_text(encoding="utf-8"))
        assert "LO_QUE_OBLIGA_LA_LEY.md" in traspaso
        assert "1039/2025" in traspaso
        assert "10.2" in traspaso and "10.3" in traspaso

    def test_el_correo_lleva_la_pregunta_que_decide_si_hay_que_mandar_algo(self):
        """La contradicción entre el artículo 10.2 y el 16.1.5 tiene que estar preguntada.

        Si no se pregunta, el programa seguirá sin poder decirle al agricultor si tiene que volcar
        los datos a la Junta cada mes. Y eso no se puede contestar adivinando.
        """
        correo = _plano(CORREO.read_text(encoding="utf-8"))
        assert "con carácter mensual" in correo, "falta la cita del artículo 16.1.5"
        assert "CUECyL" in correo
        assert "volcarlos" in correo, "la pregunta es si hay que volcarlos, no si se pueden leer"
        assert "artículo 10.2" in correo and "artículo 10.3" in correo
