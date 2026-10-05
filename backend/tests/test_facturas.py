"""Las facturas de compra: leerlas del papel, confirmarlas y que sirvan para el cuaderno.

Estos tests son de tres clases, y las tres hacen falta:

1. **La lectura** (`app/facturas.py`): que de un PDF y de una foto salga lo que pone el papel —el
   proveedor, su NIF, el número, la fecha, los totales y cada línea con su cantidad, su unidad, su
   precio y su importe—, y que cuando algo no cuadre **se diga** en vez de darse por bueno.
2. **Los endpoints**: que leer no guarde nada, que al confirmar se guarde lo que dice el
   agricultor, que el fichero quede como justificante, que nada se borre y que una finca no vea las
   facturas de otra.
3. **El cuadre**: que «lo comprado» salga de las facturas, que se pueda comparar con lo echado, y
   que cuando las unidades no sean comparables **no se reste** y se diga por qué.

Las facturas de prueba **se fabrican aquí mismo** con `reportlab` (que ya es una dependencia del
proyecto) y con datos inventados: las facturas de verdad llevan el NIF y los precios de una persona
y eso no entra en el repositorio.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from openpyxl import Workbook  # noqa: F401  (se usa para probar que un Excel no vale como factura)

from app import facturas, ocr, servicios, textos

NIF_DEL_AGRICULTOR = "70922320A"
NIF_DEL_PROVEEDOR = "F37012345"

# Una factura de ejemplo, escrita como la escribe una cooperativa de verdad: el membrete arriba, los
# datos de la factura, el cliente y una tabla con código, descripción, cantidad, unidad, precio e
# importe, y los totales al final.
LINEAS_DE_LA_FACTURA = [
    "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
    "C/ Mayor 12 - 37300 Peñaranda de Bracamonte (Salamanca)",
    "N.I.F.: F37012345",
    "",
    "FACTURA Nº 2026/00123",
    "Fecha: 15/03/2026",
    "",
    "Cliente: DAVID PEREZ VELASCO",
    "N.I.F.: 70922320A",
    "",
    "Codigo   Descripcion                          Cant.  Ud    Precio     Importe",
    "00123    GLIFOSATO 36% SL 20 L                  2    UD     85,00      170,00",
    "00456    NITRATO AMONICO 33,5%               1000    KG      0,45      450,00",
    "00789    TRIGO BLANDO SEMILLA CERTIFICADA     500    KG      0,38      190,00",
    "",
    "                                              Base imponible:           810,00",
    "                                              IVA 21%:                  170,10",
    "                                              TOTAL FACTURA:            980,10",
]


def factura_en_pdf(lineas: list[str] | None = None) -> bytes:
    """Fabrica un PDF con texto de verdad, como el que manda un proveedor por correo."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=A4)
    alto = 800
    for linea in lineas if lineas is not None else LINEAS_DE_LA_FACTURA:
        lienzo.drawString(50, alto, linea)
        alto -= 16
    lienzo.save()
    return buffer.getvalue()


def factura_en_foto(lineas: list[str] | None = None) -> bytes:
    """El mismo papel, pero como una foto: se dibuja el PDF y se hace una imagen de la página.

    Es exactamente lo que pasa cuando el agricultor le hace una foto a la factura, y es la prueba
    de verdad de que el lector de fotos sirve para algo.
    """
    import pypdfium2 as pdfium

    documento = pdfium.PdfDocument(factura_en_pdf(lineas))
    try:
        imagen = documento[0].render(scale=3).to_pil()
        salida = io.BytesIO()
        imagen.save(salida, format="PNG")
        return salida.getvalue()
    finally:
        documento.close()


def solo_si_hay_lector() -> None:
    if not ocr.hay_lector():
        pytest.skip("en este ordenador no está instalado el programa que lee las fotos")


def _pdf_sin_texto() -> bytes:
    """Un PDF vacío: por dentro no hay letras, como el que sale de un escáner.

    Es el caso que hay que saber distinguir de un PDF que sí trae el texto: si no se distingue, o
    se intenta leer letras que no están, o se le dice al agricultor que su factura no vale.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    canvas.Canvas(buffer, pagesize=A4).save()
    return buffer.getvalue()


def _subir(cliente, cabeceras, ruta: str, contenido: bytes, nombre: str = "factura.pdf"):
    return cliente.post(
        ruta,
        headers=cabeceras,
        files={"fichero": (nombre, contenido, "application/pdf")},
    )


class TestLeerLosNumeros:
    """Los formatos de número de una factura española. Es donde se pierde un dato sin enterarse."""

    def test_los_tres_formatos(self):
        # Español con miles y decimales, español sin miles, y el inglés que se cuela a veces.
        assert facturas.numero_espanol("1.234,56") == 1234.56
        assert facturas.numero_espanol("1234,56") == 1234.56
        assert facturas.numero_espanol("1234.56") == 1234.56
        assert facturas.numero_espanol("1,234.56") == 1234.56
        assert facturas.numero_espanol("810") == 810.0
        assert facturas.numero_espanol("0,45") == 0.45

    def test_mil_doscientos_treinta_y_cuatro_no_es_uno_coma_dos_mil(self):
        """«1.234» en una factura española son mil doscientos treinta y cuatro.

        Leerlo como 1,234 sería un error de mil veces en el importe de una línea, y es justo el
        tipo de fallo que no se ve a ojo.
        """
        assert facturas.numero_espanol("1.234") == 1234.0

    def test_lo_que_no_es_un_numero_no_inventa_un_cero(self):
        assert facturas.numero_espanol("") is None
        assert facturas.numero_espanol("no lo sé") is None


class TestLeerUnaFacturaEnPdf:
    """La lectura de un PDF que trae el texto dentro: tiene que salir todo."""

    @pytest.fixture
    def leida(self) -> facturas.FacturaLeida:
        return facturas.leer_factura(factura_en_pdf(), nif_del_agricultor=NIF_DEL_AGRICULTOR)

    def test_el_proveedor_y_su_nif(self, leida):
        assert leida.proveedor == "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L."
        assert leida.proveedor_nif == NIF_DEL_PROVEEDOR

    def test_el_nif_del_agricultor_no_se_toma_por_el_del_proveedor(self, leida):
        """En una factura hay dos NIF y el del agricultor ya se sabe: el proveedor es el otro.

        Sin esto, la mitad de las facturas saldrían con el NIF del propio agricultor como proveedor.
        """
        assert leida.proveedor_nif != NIF_DEL_AGRICULTOR

    def test_el_numero_y_la_fecha(self, leida):
        assert leida.numero_factura == "2026/00123"
        assert leida.fecha.isoformat() == "2026-03-15"

    def test_los_totales(self, leida):
        assert leida.base_imponible == 810.0
        assert leida.cuota_iva == 170.10
        assert leida.tipo_iva_pct == 21.0
        assert leida.total == 980.10
        assert leida.cuadra_el_total is True

    def test_las_lineas_de_producto(self, leida):
        assert len(leida.lineas) == 3
        primera = leida.lineas[0]
        assert "GLIFOSATO" in primera.descripcion
        assert primera.cantidad == 2.0
        assert primera.unidad == "ud"
        assert primera.precio_unitario == 85.0
        assert primera.importe == 170.0
        assert primera.cuadra is True
        assert primera.confianza == "alta"

    def test_la_cuenta_de_cada_linea_cuadra(self, leida):
        assert [linea.cuadra for linea in leida.lineas] == [True, True, True]
        assert leida.suman_las_lineas is True

    def test_el_tipo_de_iva_no_se_confunde_con_la_cuota(self, leida):
        """«IVA 21%: 170,10» tiene dos números y el tipo no es la cuota."""
        assert leida.tipo_iva_pct == 21.0
        assert leida.cuota_iva == 170.10

    def test_no_se_quejan_de_nada(self, leida):
        assert leida.avisos == []

    def test_se_dice_que_se_leyo_del_pdf(self, leida):
        assert leida.como_se_leyo == "pdf"


class TestElNumeroDeFactura:
    """El número de factura es lo que más se estropea al leer una foto, y es un dato que el cuaderno pide."""

    def test_el_masculino_ordinal_leido_como_asterisco(self):
        """El lector de letras lee «Nº» como «N*» a menudo. Hay que entenderlo igual.

        Es un fallo que se encontró probando la lectura de una foto **con el idioma español
        instalado**: con el inglés el «Nº» salía bien y con el español salía «N*», y el número de
        factura se perdía sin que nada avisara de otra cosa.
        """
        lineas = [
            linea.replace("FACTURA Nº 2026/00123", "FACTURA N* 2026/00123")
            for linea in LINEAS_DE_LA_FACTURA
        ]
        leida = facturas.leer_factura(factura_en_pdf(lineas))
        assert leida.numero_factura == "2026/00123"

    def test_tambien_vale_con_punto_y_con_numero(self):
        for escrito in ("FACTURA N.º 2026/00123", "FACTURA NUM. 2026/00123", "Nº FACTURA 2026/00123"):
            lineas = [
                linea.replace("FACTURA Nº 2026/00123", escrito) for linea in LINEAS_DE_LA_FACTURA
            ]
            leida = facturas.leer_factura(factura_en_pdf(lineas))
            assert leida.numero_factura == "2026/00123", escrito


class TestElIdiomaDelLector:
    """Se dice con qué idioma se ha leído, porque de eso depende que las palabras salgan bien."""

    def test_el_estado_dice_si_hay_lector_y_que_idioma(self):
        estado = ocr.estado()
        assert "hay_lector" in estado
        assert isinstance(estado["idiomas"], list)
        assert estado["nota"]

    def test_el_proyecto_puede_traer_sus_propios_idiomas(self):
        """Los idiomas del proyecto se usan sin tocar la instalación del sistema.

        Se descargan con `scripts/bajar_idioma_ocr.py` a `data/ocr/tessdata`. Aquí se comprueba que
        el programa los encuentra, que es lo que hace que el español funcione sin permisos de
        administrador.
        """
        carpeta = ocr.carpeta_de_idiomas()
        if not carpeta:
            pytest.skip("este proyecto no trae idiomas propios descargados")
        assert "spa" in ocr.idiomas_disponibles()


class TestLeerUnaFacturaEnFoto:
    """La misma factura, pero en imagen: aquí es donde entra el lector de letras."""

    @pytest.fixture
    def leida(self) -> facturas.FacturaLeida:
        solo_si_hay_lector()
        return facturas.leer_factura(factura_en_foto(), nif_del_agricultor=NIF_DEL_AGRICULTOR)

    def test_se_leen_las_tres_lineas_con_sus_numeros(self, leida):
        """Las tres líneas, con cantidad, unidad, precio e importe, y las tres cuadran.

        En la prueba se vio que una raya de la tabla se colaba como carácter suelto y una línea no
        se leía: por eso el lector admite ese ruido y hay un test que lo comprueba.
        """
        assert len(leida.lineas) == 3
        assert [linea.cantidad for linea in leida.lineas] == [2.0, 1000.0, 500.0]
        assert [linea.unidad for linea in leida.lineas] == ["ud", "kg", "kg"]
        assert [linea.importe for linea in leida.lineas] == [170.0, 450.0, 190.0]
        assert [linea.cuadra for linea in leida.lineas] == [True, True, True]

    def test_los_totales_tambien(self, leida):
        assert leida.base_imponible == 810.0
        assert leida.total == 980.10
        assert leida.cuadra_el_total is True

    def test_se_dice_que_se_leyo_de_una_foto(self, leida):
        assert leida.como_se_leyo == "foto"

    def test_si_el_lector_solo_tiene_ingles_se_avisa(self, leida):
        """Los números se leen bien en cualquier idioma, pero las palabras con eñe no.

        Se avisa en vez de disimularlo: el agricultor tiene que saber dónde mirar.
        """
        if "spa" in (leida.idioma_del_lector or ""):
            pytest.skip("el lector tiene el idioma español instalado")
        assert any("idioma inglés" in aviso for aviso in leida.avisos)


class TestCuandoNoSePuedeLeer:
    def test_sin_fichero(self):
        leida = facturas.leer_factura(b"")
        assert "No has subido ningún fichero" in " ".join(leida.avisos)

    def test_un_fichero_que_no_es_una_factura(self):
        """Un texto suelto: se lee, no hay líneas ni totales, y se dice."""
        leida = facturas.leer_factura(b"Esto no es una factura, son mis notas del tractor.")
        assert leida.lineas == []
        assert any("No he reconocido ninguna línea" in aviso for aviso in leida.avisos)

    def test_un_texto_pegado_se_lee_sin_lector_de_letras(self):
        """Un proveedor puede mandar la factura en texto. Se lee tal cual, sin OCR."""
        leida = facturas.leer_factura(
            "\n".join(LINEAS_DE_LA_FACTURA).encode("utf-8"),
            nif_del_agricultor=NIF_DEL_AGRICULTOR,
        )
        assert leida.como_se_leyo == "texto"
        assert leida.total == 980.10
        assert len(leida.lineas) == 3

    def test_si_no_hay_lector_de_letras_se_dice(self, monkeypatch):
        """Sin el programa instalado, la aplicación **no** se queda muda ni se inventa nada."""
        monkeypatch.setattr(ocr, "programa", lambda: None)
        monkeypatch.setattr(ocr, "hay_lector", lambda: False)
        leida = facturas.leer_factura(factura_en_foto())
        assert any("no está instalado" in aviso for aviso in leida.avisos)
        assert leida.lineas == []

    def test_un_pdf_sin_letras_sin_lector_lo_dice_claro(self, monkeypatch):
        """Un PDF escaneado (por dentro una imagen) y sin lector: se explica qué hacer.

        Es el caso de la factura que llega escaneada, que es muy común, en un ordenador donde no
        está instalado el lector.
        """
        monkeypatch.setattr(ocr, "hay_lector", lambda: False)
        leida = facturas.leer_factura(_pdf_sin_texto())
        assert any("escaneo" in aviso for aviso in leida.avisos)
        assert leida.lineas == []


class TestUnaLineaQueNoCuadra:
    """Si cantidad × precio no da el importe, hay que decirlo: puede ser una columna mal leída."""

    def test_se_marca_la_linea_y_se_avisa(self):
        lineas = list(LINEAS_DE_LA_FACTURA)
        # El importe de la primera línea no es 2 × 85.
        lineas[11] = "00123    GLIFOSATO 36% SL 20 L                  2    UD     85,00       99,00"
        leida = facturas.leer_factura(factura_en_pdf(lineas))
        primera = leida.lineas[0]
        assert primera.cantidad == 2.0
        assert primera.importe == 99.0
        assert primera.cuadra is False
        assert any("no da el importe" in aviso for aviso in leida.avisos)

    def test_si_las_lineas_no_suman_la_base_se_avisa(self):
        lineas = list(LINEAS_DE_LA_FACTURA)
        lineas[15] = "                                              Base imponible:           999,00"
        leida = facturas.leer_factura(factura_en_pdf(lineas))
        assert leida.base_imponible == 999.0
        assert leida.suman_las_lineas is False
        assert any("Puede faltar alguna línea" in aviso for aviso in leida.avisos)

    def test_si_la_base_mas_el_iva_no_da_el_total_se_avisa(self):
        lineas = list(LINEAS_DE_LA_FACTURA)
        lineas[17] = "                                              TOTAL FACTURA:           500,00"
        leida = facturas.leer_factura(factura_en_pdf(lineas))
        assert leida.cuadra_el_total is False
        assert any("no da el total" in aviso for aviso in leida.avisos)

    def test_sin_numero_de_factura_se_avisa(self):
        """El número de factura lo pide el cuaderno: si no se lee, hay que decirlo."""
        lineas = [linea for linea in LINEAS_DE_LA_FACTURA if "FACTURA Nº" not in linea]
        leida = facturas.leer_factura(factura_en_pdf(lineas))
        assert leida.numero_factura == ""
        assert any("número de factura" in aviso for aviso in leida.avisos)


class TestSugerirElProducto:
    """La factura dice «GLIFOSATO 36% SL»: el programa tiene que saber que es el de tu cesta."""

    def test_por_el_numero_de_registro(self):
        lineas = list(LINEAS_DE_LA_FACTURA)
        lineas[11] = (
            "00123    GLIFOSATO 36% SL 20 L  Nº reg. 24.123   2    UD     85,00      170,00"
        )
        leida = facturas.leer_factura(
            factura_en_pdf(lineas),
            productos=[
                {"id": 7, "nombre_comercial": "Glifosato 36", "numero_registro": "24.123"},
                {"id": 8, "nombre_comercial": "Otro", "numero_registro": "99.999"},
            ],
        )
        primera = leida.lineas[0]
        assert primera.numero_registro == "24.123"
        assert primera.producto_sugerido_id == 7
        assert primera.como_se_sugiere == "por el número de registro"

    def test_por_el_nombre(self):
        leida = facturas.leer_factura(
            factura_en_pdf(),
            productos=[
                {"id": 7, "nombre_comercial": "Glifosato 36 SL", "numero_registro": None},
            ],
        )
        assert leida.lineas[0].producto_sugerido_id == 7
        assert leida.lineas[0].como_se_sugiere == "por el nombre"

    def test_si_no_lo_tiene_no_se_sugiere_nada(self):
        leida = facturas.leer_factura(factura_en_pdf(), productos=[])
        assert all(linea.producto_sugerido_id is None for linea in leida.lineas)


class TestLaPuertaDeLeer:
    """`POST /api/facturas/leer`: mira el documento y **no guarda nada**."""

    def test_lee_y_no_guarda(self, cliente, cuenta):
        respuesta = _subir(
            cliente, cuenta["cabeceras"], "/api/facturas/leer", factura_en_pdf()
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["proveedor"].startswith("COOPERATIVA")
        assert datos["numero_factura"] == "2026/00123"
        assert datos["total"] == 980.10
        assert len(datos["lineas"]) == 3
        assert datos["resumen"]["lineas_que_cuadran"] == 3
        assert cliente.get("/api/facturas", headers=cuenta["cabeceras"]).json() == []

    def test_sugiere_el_producto_de_su_cesta(self, cliente, cuenta):
        cliente.post(
            "/api/productos",
            headers=cuenta["cabeceras"],
            json={
                "nombre_comercial": "Glifosato 36 SL",
                "numero_registro": "24.123",
                "dosis_maxima": 4,
                "unidad_dosis": "L/ha",
                "cantidad_comprada": 20,
                "unidad_compra": "L",
            },
        )
        respuesta = _subir(
            cliente, cuenta["cabeceras"], "/api/facturas/leer", factura_en_pdf()
        )
        primera = respuesta.json()["lineas"][0]
        assert primera["producto_sugerido"] == "Glifosato 36 SL"
        assert primera["producto_sugerido_id"] is not None

    def test_si_ya_la_ha_subido_lo_dice(self, cliente, cuenta):
        """Subir dos veces la misma foto es lo que hace todo el mundo: hay que avisar.

        Ojo con el detalle que enseña este test: se guarda **el mismo fichero** y se vuelve a
        subir. No vale con fabricar dos PDF iguales, porque dos PDF hechos por separado no son
        iguales byte a byte (llevan dentro la fecha en que se hicieron), y la huella no coincidiría.
        """
        la_misma = factura_en_pdf()
        guardada = _guardar(cliente, cuenta, la_misma)
        respuesta = _subir(cliente, cuenta["cabeceras"], "/api/facturas/leer", la_misma)
        assert respuesta.json()["ya_estaba"] == guardada["id"]

    def test_un_fichero_que_no_vale_se_rechaza_con_su_lista(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/facturas/leer",
            headers=cuenta["cabeceras"],
            files={"fichero": ("virus.exe", b"MZ...", "application/x-msdownload")},
        )
        assert respuesta.status_code == 422
        assert "no vale" in respuesta.json()["detail"]

    def test_hace_falta_entrar(self, cliente):
        respuesta = cliente.post(
            "/api/facturas/leer",
            files={"fichero": ("factura.pdf", factura_en_pdf(), "application/pdf")},
        )
        assert respuesta.status_code == 401

    def test_se_dice_si_hay_lector_de_fotos(self, cliente, cuenta):
        datos = cliente.get("/api/facturas/estado", headers=cuenta["cabeceras"]).json()
        assert datos["textos"]["titulo"] == textos.FACTURAS["titulo"]
        assert "hay_lector" in datos["lector"]
        assert "pdf" in datos["tipos_de_fichero"]


def _guardar(cliente, cuenta, contenido: bytes, datos: dict | None = None) -> dict:
    """Guarda una factura como lo hace la pantalla: los datos y el fichero en la misma petición."""
    cuerpo = {
        "fecha": "2026-03-15",
        "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
        "proveedor_nif": NIF_DEL_PROVEEDOR,
        "numero_factura": "2026/00123",
        "base_imponible": 810.0,
        "cuota_iva": 170.10,
        "tipo_iva_pct": 21.0,
        "total": 980.10,
        "leida_por": "pdf",
        "lineas": [
            {
                "descripcion": "GLIFOSATO 36% SL 20 L",
                "cantidad": 2,
                "unidad": "ud",
                "precio_unitario": 85.0,
                "importe": 170.0,
            }
        ],
    }
    if datos:
        cuerpo.update(datos)
    respuesta = cliente.post(
        "/api/facturas",
        headers=cuenta["cabeceras"],
        data={"datos": json.dumps(cuerpo)},
        files={"fichero": ("factura.pdf", contenido, "application/pdf")},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


class TestGuardarLaFactura:
    def test_se_guarda_lo_que_dice_el_agricultor(self, cliente, cuenta):
        guardada = _guardar(cliente, cuenta, factura_en_pdf())
        assert guardada["numero_factura"] == "2026/00123"
        assert guardada["total"] == 980.10
        assert len(guardada["lineas"]) == 1
        assert guardada["lineas"][0]["cuadra"] is True
        assert guardada["tiene_fichero"] is True

    def test_la_factura_queda_en_su_campana(self, cliente, cuenta):
        """La campaña sale del **año del papel**, no del día en que se sube."""
        guardada = _guardar(cliente, cuenta, factura_en_pdf())
        assert guardada["campana_id"] is not None
        campanas = cliente.get("/api/campanas", headers=cuenta["cabeceras"]).json()
        assert 2026 in [campana["anio"] for campana in campanas]

    def test_el_fichero_se_puede_ver_despues(self, cliente, cuenta):
        guardada = _guardar(cliente, cuenta, factura_en_pdf())
        respuesta = cliente.get(
            f"/api/facturas/{guardada['id']}/fichero", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200
        assert respuesta.content[:4] == b"%PDF"

    def test_una_factura_sin_fichero_tambien_se_guarda(self, cliente, cuenta):
        """Quien apunta la factura a mano, sin foto, tiene que poder hacerlo."""
        respuesta = cliente.post(
            "/api/facturas",
            headers=cuenta["cabeceras"],
            data={
                "datos": json.dumps(
                    {
                        "fecha": "2026-04-01",
                        "proveedor": "Ferretería del pueblo",
                        "numero_factura": "F-77",
                        "total": 45.0,
                        "leida_por": "a mano",
                        "lineas": [{"descripcion": "Guantes", "importe": 45.0}],
                    }
                )
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["tiene_fichero"] is False
        assert cliente.get(
            f"/api/facturas/{respuesta.json()['id']}/fichero", headers=cuenta["cabeceras"]
        ).status_code == 404

    def test_se_puede_enganchar_a_un_producto_de_su_cesta(self, cliente, cuenta):
        producto = cliente.post(
            "/api/productos",
            headers=cuenta["cabeceras"],
            json={
                "nombre_comercial": "Glifosato 36 SL",
                "numero_registro": "24.123",
                "dosis_maxima": 4,
                "unidad_dosis": "L/ha",
                "unidad_compra": "L",
            },
        ).json()
        guardada = _guardar(
            cliente,
            cuenta,
            factura_en_pdf(),
            {
                "lineas": [
                    {
                        "descripcion": "GLIFOSATO 36% SL 20 L",
                        "cantidad": 40,
                        "unidad": "L",
                        "precio_unitario": 4.25,
                        "importe": 170.0,
                        "producto_id": producto["id"],
                    }
                ]
            },
        )
        assert guardada["lineas"][0]["producto_id"] == producto["id"]
        assert guardada["lineas"][0]["producto"] == "Glifosato 36 SL"

    def test_no_se_puede_enganchar_a_un_producto_de_otra_finca(
        self, cliente, cuenta, crear_cuenta
    ):
        """Los datos de una finca no se mezclan con los de otra, ni por error."""
        otra = crear_cuenta("otro@ejemplo.test", nombre="Otra finca")
        ajeno = cliente.post(
            "/api/productos",
            headers=otra["cabeceras"],
            json={
                "nombre_comercial": "Suyo",
                "dosis_maxima": 1,
                "unidad_dosis": "L/ha",
                "unidad_compra": "L",
            },
        ).json()
        respuesta = cliente.post(
            "/api/facturas",
            headers=cuenta["cabeceras"],
            data={
                "datos": json.dumps(
                    {
                        "numero_factura": "X-1",
                        "lineas": [{"descripcion": "Algo", "producto_id": ajeno["id"]}],
                    }
                )
            },
        )
        assert respuesta.status_code == 404

    def test_queda_apuntado_en_la_auditoria(self, cliente, cuenta, db_sesion):
        from app import models

        _guardar(cliente, cuenta, factura_en_pdf())
        acciones = [fila.accion for fila in db_sesion.query(models.Auditoria).all()]
        assert "guardar_factura" in acciones


class TestAnularUnaFactura:
    def test_sin_motivo_no_se_anula(self, cliente, cuenta):
        guardada = _guardar(cliente, cuenta, factura_en_pdf())
        respuesta = cliente.post(
            f"/api/facturas/{guardada['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": ""},
        )
        assert respuesta.status_code == 422
        assert "por qué" in respuesta.json()["detail"]

    def test_con_motivo_queda_anulada_y_el_fichero_sigue(self, cliente, cuenta):
        """Nada se borra: anular una factura es dejar dicho que no vale, con su motivo."""
        guardada = _guardar(cliente, cuenta, factura_en_pdf())
        anulada = cliente.post(
            f"/api/facturas/{guardada['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Era un albarán, no una factura"},
        ).json()
        assert anulada["anulada"] is True
        assert anulada["motivo_anulacion"] == "Era un albarán, no una factura"
        # Y sigue estando, con su fichero.
        assert cliente.get("/api/facturas", headers=cuenta["cabeceras"]).json() == []
        con_anuladas = cliente.get(
            "/api/facturas", headers=cuenta["cabeceras"], params={"incluir_anuladas": True}
        ).json()
        assert len(con_anuladas) == 1
        assert cliente.get(
            f"/api/facturas/{guardada['id']}/fichero", headers=cuenta["cabeceras"]
        ).status_code == 200


class TestElCuadre:
    """Lo comprado contra lo echado: la pregunta que hace un inspector."""

    def test_lo_comprado_sale_de_las_facturas(self, cliente, cuenta):
        producto = cliente.post(
            "/api/productos",
            headers=cuenta["cabeceras"],
            json={
                "nombre_comercial": "Glifosato 36 SL",
                "dosis_maxima": 4,
                "unidad_dosis": "L/ha",
                "unidad_compra": "L",
            },
        ).json()
        _guardar(
            cliente,
            cuenta,
            factura_en_pdf(),
            {
                "lineas": [
                    {
                        "descripcion": "GLIFOSATO 36% SL 20 L",
                        "cantidad": 40,
                        "unidad": "L",
                        "precio_unitario": 4.25,
                        "importe": 170.0,
                        "producto_id": producto["id"],
                    }
                ]
            },
        )
        cesta = cliente.get("/api/productos/cesta/situacion", headers=cuenta["cabeceras"]).json()
        fila = cesta["productos"][0]
        assert fila["comprado"] == 40.0
        assert fila["comprado_de_donde"] == "facturas"
        assert fila["compras"][0]["numero_factura"] == "2026/00123"
        assert fila["compras"][0]["proveedor"].startswith("COOPERATIVA")

    def test_si_las_unidades_no_se_pueden_comparar_no_se_resta(self, cliente, cuenta):
        """Comprado en botes y el producto llevado en litros: **no se resta**, se dice por qué.

        Es la misma regla que ya seguía la cesta. Restar sin poder sería inventarse un número, y en
        un almacén eso es peor que no contestar.
        """
        producto = cliente.post(
            "/api/productos",
            headers=cuenta["cabeceras"],
            json={
                "nombre_comercial": "Glifosato 36 SL",
                "dosis_maxima": 4,
                "unidad_dosis": "L/ha",
                "unidad_compra": "L",
            },
        ).json()
        _guardar(
            cliente,
            cuenta,
            factura_en_pdf(),
            {
                "lineas": [
                    {
                        "descripcion": "GLIFOSATO 36% SL 20 L",
                        "cantidad": 2,
                        "unidad": "ud",
                        "precio_unitario": 85.0,
                        "importe": 170.0,
                        "producto_id": producto["id"],
                    }
                ]
            },
        )
        cesta = cliente.get("/api/productos/cesta/situacion", headers=cuenta["cabeceras"]).json()
        fila = cesta["productos"][0]
        assert fila["comprado"] is None
        assert fila["comprado_de_donde"] == "facturas"
        assert "ud" in fila["motivo"] or "L" in fila["motivo"]

    def test_la_ficha_del_producto_sigue_valiendo_si_no_hay_facturas(self, cliente, cuenta):
        """El que apunta la compra en la ficha del producto, sin facturas, no pierde su número."""
        cliente.post(
            "/api/productos",
            headers=cuenta["cabeceras"],
            json={
                "nombre_comercial": "Glifosato 36 SL",
                "dosis_maxima": 4,
                "unidad_dosis": "L/ha",
                "cantidad_comprada": 20,
                "unidad_compra": "L",
            },
        )
        cesta = cliente.get("/api/productos/cesta/situacion", headers=cuenta["cabeceras"]).json()
        fila = cesta["productos"][0]
        assert fila["comprado"] == 20.0
        assert fila["comprado_de_donde"] == "ficha"

    def test_una_factura_anulada_no_cuenta(self, cliente, cuenta):
        producto = cliente.post(
            "/api/productos",
            headers=cuenta["cabeceras"],
            json={
                "nombre_comercial": "Glifosato 36 SL",
                "dosis_maxima": 4,
                "unidad_dosis": "L/ha",
                "unidad_compra": "L",
            },
        ).json()
        guardada = _guardar(
            cliente,
            cuenta,
            factura_en_pdf(),
            {
                "lineas": [
                    {
                        "descripcion": "GLIFOSATO",
                        "cantidad": 40,
                        "unidad": "L",
                        "precio_unitario": 4.25,
                        "importe": 170.0,
                        "producto_id": producto["id"],
                    }
                ]
            },
        )
        cliente.post(
            f"/api/facturas/{guardada['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Estaba repetida"},
        )
        cesta = cliente.get("/api/productos/cesta/situacion", headers=cuenta["cabeceras"]).json()
        assert cesta["productos"][0]["comprado"] is None

    def test_el_resumen_dice_de_que_factura_sale_cada_compra(self, cliente, cuenta):
        producto = cliente.post(
            "/api/productos",
            headers=cuenta["cabeceras"],
            json={
                "nombre_comercial": "Glifosato 36 SL",
                "dosis_maxima": 4,
                "unidad_dosis": "L/ha",
                "unidad_compra": "L",
            },
        ).json()
        _guardar(
            cliente,
            cuenta,
            factura_en_pdf(),
            {
                "lineas": [
                    {
                        "descripcion": "GLIFOSATO",
                        "cantidad": 40,
                        "unidad": "L",
                        "producto_id": producto["id"],
                        "importe": 170.0,
                    }
                ]
            },
        )
        resumen = cliente.get("/api/facturas/resumen", headers=cuenta["cabeceras"]).json()
        assert len(resumen) == 1
        assert resumen[0]["nombre_comercial"] == "Glifosato 36 SL"
        assert resumen[0]["comprado"] == 40.0
        assert resumen[0]["compras"][0]["proveedor"].startswith("COOPERATIVA")


class TestCadaFincaVeLoSuyo:
    def test_las_facturas_de_otra_finca_no_se_ven(self, cliente, cuenta, crear_cuenta):
        _guardar(cliente, cuenta, factura_en_pdf())
        otra = crear_cuenta("otro@ejemplo.test", nombre="Otra finca")
        assert cliente.get("/api/facturas", headers=otra["cabeceras"]).json() == []

    def test_no_se_puede_ver_la_factura_de_otra_finca(self, cliente, cuenta, crear_cuenta):
        guardada = _guardar(cliente, cuenta, factura_en_pdf())
        otra = crear_cuenta("otro@ejemplo.test", nombre="Otra finca")
        assert (
            cliente.get(
                f"/api/facturas/{guardada['id']}", headers=otra["cabeceras"]
            ).status_code
            == 404
        )

    def test_no_se_puede_ver_su_fichero(self, cliente, cuenta, crear_cuenta):
        guardada = _guardar(cliente, cuenta, factura_en_pdf())
        otra = crear_cuenta("otro@ejemplo.test", nombre="Otra finca")
        assert (
            cliente.get(
                f"/api/facturas/{guardada['id']}/fichero", headers=otra["cabeceras"]
            ).status_code
            == 404
        )


class TestLaFacturaLlegaAlCuaderno:
    """El nº de factura y el de albarán son datos que el cuaderno de la Junta pide."""

    def test_el_abono_puede_llevar_su_numero_de_albaran_y_su_tipo(self, cliente, cuenta):
        """La hoja 6 del cuaderno pide «Nº de albarán» y «Tipo de fertilización» (F, AF o AC)."""
        parcela = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={"alias": "El Prado", "superficie_ha": 2.43},
        ).json()
        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        abono = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Nitrato amónico 33,5", "tipo": "mineral", "riqueza_n": 33.5},
        ).json()

        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-03-20",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "fertilizante_id": abono["id"],
                "kg_ha_producto": 200,
                "numero_albaran": "A-2026-88",
                "tipo_fertilizacion": "cobertera",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["numero_albaran"] == "A-2026-88"
        assert respuesta.json()["tipo_fertilizacion"] == "cobertera"

    def test_el_tipo_de_fertilizacion_solo_admite_lo_que_dice_el_cuaderno(self, cliente, cuenta):
        """F (fertirrigación), AF (fondo) o AC (cobertera): cualquier otra cosa es un error nuestro."""
        parcela = cliente.post(
            "/api/parcelas",
            headers=cuenta["cabeceras"],
            json={"alias": "El Prado", "superficie_ha": 2.43},
        ).json()
        campana = cliente.get("/api/campanas/actual", headers=cuenta["cabeceras"]).json()
        abono = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Nitrato", "riqueza_n": 33.5},
        ).json()
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-03-20",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "fertilizante_id": abono["id"],
                "kg_ha_producto": 200,
                "tipo_fertilizacion": "inventado",
            },
        )
        assert respuesta.status_code == 422
