"""La semilla, la foto de la etiqueta y la siembra (T10, 03/10/2026).

Estas pruebas son el contrato del ticket, y están escritas alrededor de las cinco cosas que **no se
pueden romper**:

  1. **Lo que no se sabe no se convierte en cero.** Ni el poder germinativo, ni la pureza, ni la
     dosis, ni la cantidad total, ni lo que queda en el almacén. Un hueco es una pregunta; un cero es
     una afirmación falsa, y en un cuaderno que se firma eso importa.
  2. **La dosis por hectárea no es la cantidad total**, y los litros no son los kilos. Es un error de
     diez veces, es el corazón de este ticket y aquí tiene sus casos.
  3. **Una siembra descuenta del almacén una sola vez**, aunque el móvil reenvíe la petición.
  4. **Corregir y anular no dejan dos descuentos.** Anular devuelve lo que salió sin tocar el libro.
  5. **Una etiqueta leída no crea una semilla sin confirmar**, y de otra finca no se ve nada.

Sobre la lectura de la foto, con lo que se ha podido comprobar de verdad: del texto de una etiqueta
(un `.txt` o un PDF, que es por donde pasa **cualquier** lectura una vez el lector de fotos ha hecho su
trabajo) hay pruebas que corren en cualquier ordenador; y hay además una prueba con **una foto de
verdad** (el papel dibujado y rasterizado, que es lo que sale del móvil) que se salta sola si en el
ordenador no está puesto el programa que lee fotos, igual que hacen las pruebas de las facturas.
"""

from __future__ import annotations

import io
import os
import pathlib

import pytest

from app import ocr, semillas, textos

# --------------------------------------------------------------------------
# Una etiqueta de verdad, escrita como la escribe una casa de semillas
# --------------------------------------------------------------------------

ETIQUETA_DE_VERDAD = "\n".join(
    [
        "SEMILLAS DEL DUERO S.L.",
        "CASA COMERCIAL: SEMILLAS DEL DUERO",
        "ESPECIE: VEZA COMUN",
        "VARIEDAD: VILLALOBOS",
        "PROVEEDOR: COOPERATIVA AGRICOLA DE PEÑARANDA",
        "N.º DE LOTE: 4471-A",
        "FECHA DE ENVASADO: 12/01/2026",
        "FECHA DE CADUCIDAD: 12/01/2028",
        "PODER GERMINATIVO: 92 %",
        "PUREZA: 99,2 %",
        "DOSIS RECOMENDADA: 120 kg/ha",
        "SEMILLA NO TRATADA",
    ]
)

# Y la misma etiqueta como la escriben otras: sin poder germinativo, sin pureza, con la caducidad en
# mes y año, y con una dosis que no dice si es por hectárea. **Es el caso que de verdad hay que saber
# leer**, porque lo que no viene no se puede apuntar y hay que decirlo.
ETIQUETA_A_MEDIAS = "\n".join(
    [
        "ESPECIE: TRIGO BLANDO",
        "VARIEDAD: CRAKLIN",
        "LOTE: 2026/0417",
        "CADUCIDAD: 02/2027",
        "DOSIS: 180 kg",
    ]
)


def _subir_etiqueta(cliente, cabeceras, contenido: bytes | None = None, nombre: str = "etiqueta.pdf"):
    """Sube una etiqueta por la puerta de verdad.

    El fichero es un **PDF con las letras dentro**, que es como lo manda una casa de semillas al
    vender: por ahí se lee sin ningún programa de más. El texto suelto que se usa en las pruebas de
    los campos no entra por aquí a propósito, porque la puerta de los ficheros acepta lo mismo que
    acepta un boletín de laboratorio (PDF o foto), y un `.txt` no es ninguna de las dos cosas.
    """
    if contenido is None:
        contenido = _etiqueta_en_pdf(ETIQUETA_DE_VERDAD.split("\n"))
    return cliente.post(
        "/api/semillas/etiqueta",
        headers=cabeceras,
        files={"fichero": (nombre, contenido, "application/pdf")},
    )


def _etiqueta_en_pdf(lineas: list[str]) -> bytes:
    """El papel, como un PDF con las letras dentro (que es como lo manda una casa de semillas)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=A4)
    alto = 800
    for linea in lineas:
        lienzo.drawString(50, alto, linea)
        alto -= 16
    lienzo.save()
    return buffer.getvalue()


def _etiqueta_en_foto(lineas: list[str]) -> bytes:
    """Y el mismo papel como una foto: se dibuja el PDF y se hace una imagen de la página.

    Es exactamente lo que pasa cuando el agricultor le hace una foto a la etiqueta del saco.
    """
    import pypdfium2 as pdfium

    documento = pdfium.PdfDocument(_etiqueta_en_pdf(lineas))
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


# --------------------------------------------------------------------------
# Lo que hay montado: un almacén con semilla, para poder sembrarla
# --------------------------------------------------------------------------


@pytest.fixture
def almacen_con_semilla(cliente, cuenta):
    """Un albarán con 500 kg de semilla dentro: de ahí sale lo que se siembre.

    Se usa la puerta de verdad del almacén (el albarán) en vez de escribir filas a mano: así lo que se
    prueba es el camino que hace el agricultor, y el artículo, el lote y la entrada son los de verdad.
    """

    def _crear(
        cantidad: float = 500.0,
        unidad: str = "kg",
        numero_albaran: str = "ALB-2026-77",
        numero_lote: str = "4471-A",
    ) -> dict:
        respuesta = cliente.post(
            "/api/almacen/recepciones",
            headers=cuenta["cabeceras"],
            json={
                "fecha": "2026-01-20",
                "proveedor": "Cooperativa Agrícola de Peñaranda",
                "numero_albaran": numero_albaran,
                "lineas": [
                    {
                        "nombre": "Veza común Villalobos",
                        "categoria": "semilla",
                        "cantidad": cantidad,
                        "unidad_de_la_cantidad": unidad,
                        "numero_lote": numero_lote,
                        "fecha_caducidad": "2028-01-12",
                        "presentacion": "saco",
                        "contenido_por_envase": 25.0,
                    }
                ],
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        existencias = cliente.get(
            "/api/almacen/existencias", headers=cuenta["cabeceras"]
        ).json()
        articulo = next(
            fila for fila in existencias["articulos"] if fila["nombre"] == "Veza común Villalobos"
        )
        su_lote = next(
            de_lote for de_lote in articulo["lotes"] if de_lote["numero_lote"] == numero_lote
        )
        return {
            "articulo_id": articulo["articulo_id"],
            "lote_id": su_lote["lote_id"],
            "recepcion": respuesta.json(),
            "cantidad": cantidad,
            "unidad": unidad,
        }

    return _crear


def _dar_de_alta_la_semilla(cliente, cuenta, almacen, **cambios):
    datos = {
        "articulo_id": almacen["articulo_id"],
        "unidad": almacen["unidad"],
        "especie": "Veza común",
        "variedad": "Villalobos",
        "casa_comercial": "Semillas del Duero",
        "proveedor": "Cooperativa Agrícola de Peñaranda",
        "numero_lote_proveedor": "4471-A",
        "dosis_recomendada_por_ha": 120.0,
        "unidad_dosis": "kg/ha",
        "fecha_envasado": "2026-01-12",
        "fecha_caducidad": "2028-01-12",
        "poder_germinativo_pct": 92.0,
        "pureza_pct": 99.2,
        "tratada": False,
    }
    datos.update(cambios)
    respuesta = cliente.post("/api/semillas", headers=cuenta["cabeceras"], json=datos)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _sembrar(cliente, cuenta, *, semilla_id, parcela_id, lote_id=None, **cambios):
    datos = {
        "semilla_id": semilla_id,
        "parcela_id": parcela_id,
        "lote_id": lote_id,
        "fecha": "2026-03-01",
        "superficie_ha": 1.0,
        "dosis_por_ha": 200.0,
        "unidad_dosis": "kg/ha",
        "cantidad_total": 200.0,
        "unidad_cantidad": "kg",
        "clave_de_reenvio": "siembra-de-prueba-1",
    }
    datos.update(cambios)
    return cliente.post("/api/siembras", headers=cuenta["cabeceras"], json=datos)


def _queda(cliente, cuenta, articulo_id: int):
    existencias = cliente.get("/api/almacen/existencias", headers=cuenta["cabeceras"]).json()
    return next(
        fila for fila in existencias["articulos"] if fila["articulo_id"] == articulo_id
    )


# --------------------------------------------------------------------------
# 1. Leer la etiqueta de una semilla: lo que se lee y lo que no
# --------------------------------------------------------------------------


class TestLeerLaEtiqueta:
    """Lo que se saca del papel, y sobre todo **lo que no se saca**."""

    def test_los_campos_de_una_etiqueta_de_verdad(self):
        leida = semillas.lo_que_dice_la_etiqueta(semillas.EtiquetaLeida(), ETIQUETA_DE_VERDAD)
        assert leida.especie == "VEZA COMUN"
        assert leida.variedad == "VILLALOBOS"
        assert leida.casa_comercial == "SEMILLAS DEL DUERO"
        assert leida.proveedor == "COOPERATIVA AGRICOLA DE PEÑARANDA"
        assert leida.numero_lote_proveedor == "4471-A"
        assert leida.dosis_recomendada_por_ha == 120.0
        assert leida.unidad_dosis == "kg/ha"
        assert leida.fecha_envasado is not None
        assert leida.fecha_envasado.isoformat() == "2026-01-12"
        assert leida.fecha_caducidad.isoformat() == "2028-01-12"
        assert leida.poder_germinativo_pct == 92.0
        assert leida.pureza_pct == 99.2
        assert leida.tratada is False

    def test_una_dosis_sin_decir_por_hectarea_no_se_apunta_como_dosis(self):
        """«DOSIS: 180 kg» **no** son 180 kg por hectárea: puede ser lo que lleva el saco.

        Es el error de diez veces del T10 y aquí se ve: no se apunta nada, se dice lo que pone el
        papel y se deja que lo mire quien lo tiene delante.
        """
        leida = semillas.lo_que_dice_la_etiqueta(semillas.EtiquetaLeida(), ETIQUETA_A_MEDIAS)
        assert leida.dosis_recomendada_por_ha is None
        assert leida.unidad_dosis == ""
        assert any("180" in duda for duda in leida.dudas), leida.dudas

    def test_una_caducidad_de_mes_y_ano_no_se_completa_con_un_dia_inventado(self):
        leida = semillas.lo_que_dice_la_etiqueta(semillas.EtiquetaLeida(), ETIQUETA_A_MEDIAS)
        assert leida.fecha_caducidad is None
        assert any("02/2027" in duda for duda in leida.dudas), leida.dudas

    def test_lo_que_no_viene_se_queda_vacio_y_no_es_un_cero(self):
        """El poder germinativo y la pureza no vienen en todas las etiquetas, y eso se dice."""
        leida = semillas.lo_que_dice_la_etiqueta(semillas.EtiquetaLeida(), ETIQUETA_A_MEDIAS)
        assert leida.poder_germinativo_pct is None
        assert leida.pureza_pct is None
        assert leida.tratada is None, "«no lo dice» no es «no viene tratada»"

    def test_una_semilla_sin_tratar_no_se_lee_como_tratada(self):
        """«SEMILLA NO TRATADA» contiene la palabra «tratada»: leerla al revés sería un dato grave."""
        sin_tratar = semillas.lo_que_dice_la_etiqueta(
            semillas.EtiquetaLeida(), "ESPECIE: CEBADA\nSEMILLA NO TRATADA"
        )
        assert sin_tratar.tratada is False
        tratada = semillas.lo_que_dice_la_etiqueta(
            semillas.EtiquetaLeida(), "ESPECIE: CEBADA\nSEMILLA TRATADA CON IMIDACLOPRID"
        )
        assert tratada.tratada is True

    def test_una_etiqueta_que_no_habla_de_la_caducidad_lo_dice(self):
        leida = semillas.lo_que_dice_la_etiqueta(
            semillas.EtiquetaLeida(), "ESPECIE: CEBADA\nVARIEDAD: PEWTER"
        )
        assert leida.fecha_caducidad is None
        assert any("caduc" in duda for duda in leida.dudas), leida.dudas

    def test_un_porcentaje_sin_el_signo_no_se_toma_por_un_porcentaje(self):
        leida = semillas.lo_que_dice_la_etiqueta(
            semillas.EtiquetaLeida(), "ESPECIE: CEBADA\nPUREZA: 99,2\nGERMINACION: 95"
        )
        assert leida.pureza_pct is None
        assert leida.poder_germinativo_pct is None

    def test_lo_que_se_ha_leido_se_cuenta_y_se_dice(self):
        leida = semillas.lo_que_dice_la_etiqueta(semillas.EtiquetaLeida(), ETIQUETA_DE_VERDAD)
        assert "especie" in leida.leidos
        assert "poder_germinativo_pct" in leida.leidos
        assert leida.resumen()["cuantos"] == len(leida.leidos)
        sin_nada = semillas.lo_que_dice_la_etiqueta(semillas.EtiquetaLeida(), "hola")
        assert sin_nada.leidos == []


class TestLaFotoDeLaEtiquetaEsUnaPropuesta:
    """La etiqueta se lee por HTTP, y **leer no escribe nada**."""

    def test_una_etiqueta_leida_no_crea_una_semilla_sin_confirmar(self, cliente, cuenta):
        """El corazón de la regla: **sin confirmación no hay semilla**.

        Se lee la etiqueta y se comprueba que no hay ni semilla, ni artículo en el almacén, ni nada
        apuntado. La respuesta lo dice en el dato (`guardado: false`), no en un comentario.
        """
        respuesta = _subir_etiqueta(cliente, cuenta["cabeceras"])
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["guardado"] is False
        assert datos["especie"] == "VEZA COMUN"
        assert datos["poder_germinativo_pct"] == 92.0
        assert datos["campos_leidos"], "la respuesta tiene que decir qué se ha leído"

        assert cliente.get("/api/semillas", headers=cuenta["cabeceras"]).json() == []
        existencias = cliente.get("/api/almacen/existencias", headers=cuenta["cabeceras"]).json()
        assert existencias["articulos"] == []
        assert cliente.get("/api/siembras", headers=cuenta["cabeceras"]).json() == []

    def test_la_lectura_no_deja_ningun_fichero_en_el_disco(self, cliente, cuenta):
        """Tampoco el fichero: lo que no se ha confirmado no ocupa sitio en ninguna parte."""
        raiz = pathlib.Path(os.environ["CUEDIGITAL_ADJUNTOS"])
        antes = sorted(ruta for ruta in raiz.rglob("*") if ruta.is_file())
        _subir_etiqueta(cliente, cuenta["cabeceras"])
        despues = sorted(ruta for ruta in raiz.rglob("*") if ruta.is_file())
        assert despues == antes

    def test_una_foto_de_verdad_se_lee(self, cliente, cuenta):
        """La prueba de que el camino de la foto funciona: un papel dibujado y rasterizado.

        Se salta sola si en este ordenador no está puesto el programa que lee fotos, igual que las
        pruebas de las facturas: un test que depende de que otro programa esté instalado es una
        lotería.
        """
        solo_si_hay_lector()
        respuesta = cliente.post(
            "/api/semillas/etiqueta",
            headers=cuenta["cabeceras"],
            files={
                "fichero": (
                    "etiqueta.png",
                    _etiqueta_en_foto(ETIQUETA_DE_VERDAD.split("\n")),
                    "image/png",
                )
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["como_se_leyo"] == "foto"
        assert datos["hay_lector"] is True
        # Del papel se han leído los números y la variedad; lo que salga con erratas es justo lo que
        # el agricultor corrige, y por eso se enseña entero.
        assert "variedad" in datos["campos_leidos"], datos
        assert datos["texto_crudo"], "el texto que se ha leído se enseña para poder comprobarlo"

    def test_una_etiqueta_en_pdf_se_lee_sin_lector_de_fotos(self, cliente, cuenta):
        """El PDF de la casa de semillas trae las letras dentro: no hace falta ningún programa más."""
        respuesta = cliente.post(
            "/api/semillas/etiqueta",
            headers=cuenta["cabeceras"],
            files={
                "fichero": (
                    "etiqueta.pdf",
                    _etiqueta_en_pdf(ETIQUETA_DE_VERDAD.split("\n")),
                    "application/pdf",
                )
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["como_se_leyo"] == "pdf"
        assert datos["especie"] == "VEZA COMUN"
        assert datos["unidad_dosis"] == "kg/ha"

    def test_sin_lector_de_fotos_se_dice_y_no_se_inventa(self, cliente, cuenta, monkeypatch):
        """El tercer final: **no lo he podido comprobar**. Ni «bien» ni «mal»."""
        monkeypatch.setattr(ocr, "programa", lambda: None)
        monkeypatch.setattr(ocr, "hay_lector", lambda: False)
        respuesta = cliente.post(
            "/api/semillas/etiqueta",
            headers=cuenta["cabeceras"],
            files={"fichero": ("etiqueta.png", b"\x89PNG\r\n\x1a\nfalsa", "image/png")},
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["hay_lector"] is False
        assert datos["campos_leidos"] == []
        assert datos["avisos"], "tiene que decir por qué no se ha podido leer"
        assert cliente.get("/api/semillas", headers=cuenta["cabeceras"]).json() == []


# --------------------------------------------------------------------------
# 2. Un dato que no se sabe no es un cero
# --------------------------------------------------------------------------


class TestLoQueNoSeSabeNoEsCero:
    def test_una_semilla_sin_poder_germinativo_no_lo_convierte_en_cero(
        self, cliente, cuenta, almacen_con_semilla
    ):
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(
            cliente,
            cuenta,
            almacen,
            poder_germinativo_pct=None,
            pureza_pct=None,
            tratada=None,
        )
        assert semilla["poder_germinativo_pct"] is None
        assert semilla["pureza_pct"] is None
        assert semilla["tratada"] is None
        # Y al volver a leerla, sigue siendo «no lo sé» y no un cero.
        leida = cliente.get(f"/api/semillas/{semilla['id']}", headers=cuenta["cabeceras"]).json()
        assert leida["poder_germinativo_pct"] is None
        assert leida["tratada"] is None

    def test_un_envase_del_que_no_se_sabe_la_cantidad_no_queda_a_cero(self, cliente, cuenta):
        """Un albarán sin cantidad legible: el saldo es «no se puede saber», nunca 0."""
        cliente.post(
            "/api/almacen/recepciones",
            headers=cuenta["cabeceras"],
            json={
                "fecha": "2026-01-20",
                "proveedor": "Cooperativa Agrícola de Peñaranda",
                "numero_albaran": "ALB-2026-78",
                "lineas": [{"nombre": "Semilla sin cantidad legible", "categoria": "semilla"}],
            },
        )
        existencias = cliente.get("/api/almacen/existencias", headers=cuenta["cabeceras"]).json()
        articulo = existencias["articulos"][0]
        semilla = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"articulo_id": articulo["articulo_id"]},
        ).json()
        assert semilla["queda"]["saldo"] is None, semilla["queda"]
        assert semilla["queda"]["motivo"], "tiene que decir por qué no se puede saber"

    def test_una_siembra_sin_cantidad_no_apunta_un_cero_y_dice_que_no_descuenta(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()

        respuesta = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
            superficie_ha=None,
            dosis_por_ha=None,
            unidad_dosis=None,
            cantidad_total=None,
            unidad_cantidad=None,
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["cantidad_total"] is None, "un hueco, no un cero"
        assert datos["dosis_por_ha"] is None
        assert datos["descuenta"] is False
        assert datos["no_descuenta_porque"], "tiene que decir por qué no se ha descontado nada"
        # Y el almacén sigue igual: no se ha restado «lo que sea».
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 500.0


# --------------------------------------------------------------------------
# 3. La dosis y la cantidad total no se confunden (ni litros con kilos)
# --------------------------------------------------------------------------


class TestLaDosisNoEsLaCantidadTotal:
    def test_si_solo_dan_la_dosis_el_total_se_calcula_y_se_dice(self):
        cifras = semillas.cuadra_las_dos_cifras(
            dosis_por_ha=200.0,
            unidad_dosis="kg/ha",
            cantidad_total=None,
            unidad_cantidad=None,
            superficie_ha=2.5,
        )
        assert cifras["cantidad_total"] == 500.0
        assert cifras["cantidad_total_calculada"] is True
        assert cifras["unidad_cantidad"] == "kg", "la unidad sale del numerador de la dosis"
        assert cifras["avisos"], "un número calculado se dice, no se calla"

    def test_si_solo_dan_el_total_la_dosis_se_calcula_y_se_dice(self):
        cifras = semillas.cuadra_las_dos_cifras(
            dosis_por_ha=None,
            unidad_dosis=None,
            cantidad_total=500.0,
            unidad_cantidad="kg",
            superficie_ha=2.5,
        )
        assert cifras["dosis_por_ha"] == 200.0
        assert cifras["dosis_calculada"] is True
        assert cifras["unidad_dosis"] == "kg/ha"
        assert cifras["avisos"]

    def test_sin_superficie_no_se_puede_calcular_la_que_falta_y_se_pide(self):
        cifras = semillas.cuadra_las_dos_cifras(
            dosis_por_ha=200.0,
            unidad_dosis="kg/ha",
            cantidad_total=None,
            unidad_cantidad=None,
            superficie_ha=None,
        )
        assert cifras["cantidad_total"] is None, "no se inventa: se pide"
        assert "cantidad_total" in cifras["falta"]
        assert "superficie_ha" in cifras["falta"]
        assert cifras["cantidad_total_calculada"] is False

    def test_la_dosis_y_el_total_son_dos_numeros_distintos(self):
        """2 L en 4 ha son 0,5 L/ha: **el mismo número significa cosas distintas según dónde esté**."""
        cifras = semillas.cuadra_las_dos_cifras(
            dosis_por_ha=None,
            unidad_dosis=None,
            cantidad_total=2.0,
            unidad_cantidad="L",
            superficie_ha=4.0,
        )
        assert cifras["cantidad_total"] == 2.0, "el total no se convierte en la dosis"
        assert cifras["dosis_por_ha"] == 0.5, "la dosis es la cuenta, no el total"

    def test_los_litros_no_se_comparan_con_los_kilos(self):
        """Sin la densidad, pasar de litros a kilos es inventar. Se dice y no se convierte nada."""
        cifras = semillas.cuadra_las_dos_cifras(
            dosis_por_ha=2.0,
            unidad_dosis="L/ha",
            cantidad_total=100.0,
            unidad_cantidad="kg",
            superficie_ha=1.0,
        )
        assert any("comparar" in aviso for aviso in cifras["avisos"]), cifras["avisos"]
        assert cifras["cantidad_total"] == 100.0 and cifras["dosis_por_ha"] == 2.0

    def test_cuando_las_dos_cifras_no_cuadran_se_dicen_los_dos_numeros(self):
        cifras = semillas.cuadra_las_dos_cifras(
            dosis_por_ha=200.0,
            unidad_dosis="kg/ha",
            cantidad_total=100.0,
            unidad_cantidad="kg",
            superficie_ha=1.0,
        )
        assert cifras["no_cuadra"], "la aritmética es la prueba"
        assert "200" in cifras["no_cuadra"] and "100" in cifras["no_cuadra"]
        # Pero no se bloquea ni se cambia ningún número: el agricultor puede tener razón.
        assert cifras["dosis_por_ha"] == 200.0 and cifras["cantidad_total"] == 100.0

    def test_una_cantidad_negativa_no_se_apunta(self):
        cifras = semillas.cuadra_las_dos_cifras(
            dosis_por_ha=-2.0,
            unidad_dosis="kg/ha",
            cantidad_total=None,
            unidad_cantidad=None,
            superficie_ha=1.0,
        )
        assert cifras["dosis_por_ha"] is None
        assert cifras["avisos"]


# --------------------------------------------------------------------------
# 4. La semilla que se siembra sale del almacén, una sola vez
# --------------------------------------------------------------------------


class TestSembrarDescuentaDelAlmacen:
    def test_una_siembra_descuenta_del_almacen(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()

        respuesta = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["descuenta"] is True
        assert datos["movimiento_id"]
        assert datos["no_descuenta_porque"] in ("", None)
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 300.0

        # Y el movimiento del libro dice de dónde salió, que es lo que pide una inspección.
        movimientos = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        salida = [m for m in movimientos if m["tipo"] == "salida"]
        assert len(salida) == 1
        assert salida[0]["origen_tipo"] == "siembra"
        assert salida[0]["origen_id"] == datos["id"]
        assert salida[0]["cantidad"] == 200.0 and salida[0]["unidad"] == "kg"

    def test_reenviar_la_misma_siembra_no_descuenta_dos_veces(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        """El móvil sin cobertura reintenta con la misma clave: **una salida, no dos**."""
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        primera = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        )
        assert primera.status_code == 201
        segunda = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        )
        assert segunda.status_code == 200, segunda.text
        assert segunda.json()["id"] == primera.json()["id"]
        assert any("ya estaba" in aviso for aviso in segunda.json()["avisos"])
        assert len(cliente.get("/api/siembras", headers=cuenta["cabeceras"]).json()) == 1
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 300.0

    def test_dos_siembras_distintas_descuentan_las_dos(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        for clave in ("siembra-a", "siembra-b"):
            respuesta = _sembrar(
                cliente,
                cuenta,
                semilla_id=semilla["id"],
                parcela_id=tierra["id"],
                lote_id=almacen["lote_id"],
                cantidad_total=50.0,
                dosis_por_ha=None,
                unidad_dosis=None,
                clave_de_reenvio=clave,
            )
            assert respuesta.status_code == 201, respuesta.text
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 400.0

    def test_no_se_puede_descontar_de_un_envase_de_otra_semilla(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        """El envase tiene que ser suyo: si no, el libro diría que salió de un saco que sigue lleno."""
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        otro = cliente.post(
            "/api/almacen/recepciones",
            headers=cuenta["cabeceras"],
            json={
                "numero_albaran": "ALB-2026-99",
                "proveedor": "Otra casa",
                "lineas": [{"nombre": "Cebada Pewter", "categoria": "semilla", "cantidad": 10}],
            },
        )
        assert otro.status_code == 201, otro.text
        existencias = cliente.get("/api/almacen/existencias", headers=cuenta["cabeceras"]).json()
        cebada = next(f for f in existencias["articulos"] if f["nombre"] == "Cebada Pewter")
        respuesta = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=cebada["lotes"][0]["lote_id"],
        )
        assert respuesta.status_code == 400, respuesta.text
        assert "envase" in respuesta.json()["detail"].lower()

    def test_cuando_lo_que_sale_deja_el_envase_en_negativo_se_avisa_y_no_se_apunta(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        """Nunca se impide registrar lo que de verdad pasó, pero no se apunta a escondidas."""
        almacen = almacen_con_semilla(cantidad=100.0)
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        respuesta = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
            cantidad_total=500.0,
            dosis_por_ha=None,
            unidad_dosis=None,
        )
        assert respuesta.status_code == 409, respuesta.text
        assert cliente.get("/api/siembras", headers=cuenta["cabeceras"]).json() == []
        # Y con la confirmación del agricultor, sí: lo que pasó se puede registrar.
        segunda = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
            cantidad_total=500.0,
            dosis_por_ha=None,
            unidad_dosis=None,
            aceptar_descuadre=True,
        )
        assert segunda.status_code == 201, segunda.text
        assert segunda.json()["descuenta"] is True
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == -400.0


# --------------------------------------------------------------------------
# 5. Corregir y anular una siembra sin que queden dos descuentos
# --------------------------------------------------------------------------


class TestCorregirYAnularUnaSiembra:
    def test_corregir_la_cantidad_deja_un_solo_descuento_vivo(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        siembra = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        ).json()
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 300.0

        corregida = cliente.put(
            f"/api/siembras/{siembra['id']}",
            headers=cuenta["cabeceras"],
            json={
                "semilla_id": semilla["id"],
                "parcela_id": tierra["id"],
                "lote_id": almacen["lote_id"],
                "fecha": "2026-03-01",
                "superficie_ha": 1.0,
                "cantidad_total": 60.0,
                "unidad_cantidad": "kg",
                "dosis_por_ha": None,
                "unidad_dosis": None,
            },
        )
        assert corregida.status_code == 200, corregida.text
        datos = corregida.json()
        assert datos["cantidad_total"] == 60.0
        assert datos["dosis_por_ha"] == 60.0 and datos["dosis_calculada"] is True
        assert datos["descuenta"] is True
        # **440 = 500 − 60**, y no 240 (dos descuentos) ni 440 con la salida vieja contando.
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 440.0

        movimientos = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        salidas = [m for m in movimientos if m["tipo"] == "salida"]
        assert len(salidas) == 2, "la salida vieja no se borra: se queda, tachada"
        vivas = [m for m in salidas if m["cuenta"]]
        assert len(vivas) == 1 and vivas[0]["cantidad"] == 60.0
        anulada = [m for m in salidas if not m["cuenta"]][0]
        assert anulada["cantidad"] == 200.0
        assert anulada["no_cuenta_porque"], "tiene que decir por qué no cuenta"

    def test_anular_una_siembra_devuelve_al_almacen_lo_que_salio(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        siembra = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        ).json()
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 300.0

        anulada = cliente.post(
            f"/api/siembras/{siembra['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "Me equivoqué de tierra"},
        )
        assert anulada.status_code == 200, anulada.text
        assert anulada.json()["anulada"] is True
        assert anulada.json()["descuenta"] is False
        # La semilla vuelve a estar donde estaba, **sin tocar el libro**.
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 500.0
        movimientos = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        salidas = [m for m in movimientos if m["tipo"] == "salida"]
        assert len(salidas) == 1, "el movimiento sigue ahí: nada se borra"
        assert salidas[0]["cuenta"] is False
        assert "anulada" in (salidas[0]["no_cuenta_porque"] or "").lower()

    def test_una_siembra_anulada_no_se_corrige_y_se_dice(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        siembra = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        ).json()
        cliente.post(
            f"/api/siembras/{siembra['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "No era esa tierra"},
        )
        respuesta = cliente.put(
            f"/api/siembras/{siembra['id']}",
            headers=cuenta["cabeceras"],
            json={"semilla_id": semilla["id"], "parcela_id": tierra["id"]},
        )
        assert respuesta.status_code == 409, respuesta.text
        assert cliente.get("/api/siembras", headers=cuenta["cabeceras"]).json()[0]["anulada"] is True

    def test_anular_sin_motivo_no_vale(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        siembra = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        ).json()
        respuesta = cliente.post(
            f"/api/siembras/{siembra['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "no"},
        )
        assert respuesta.status_code == 422, respuesta.text

    def test_corregir_una_siembra_que_no_descontaba_y_ahora_si(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        """Faltaba la cantidad y ahora se sabe: la corrección saca la semilla del almacén."""
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        siembra = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
            superficie_ha=None,
            dosis_por_ha=None,
            unidad_dosis=None,
            cantidad_total=None,
            unidad_cantidad=None,
        ).json()
        assert siembra["descuenta"] is False
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 500.0

        corregida = cliente.put(
            f"/api/siembras/{siembra['id']}",
            headers=cuenta["cabeceras"],
            json={
                "semilla_id": semilla["id"],
                "parcela_id": tierra["id"],
                "lote_id": almacen["lote_id"],
                "cantidad_total": 80.0,
                "unidad_cantidad": "kg",
                "superficie_ha": 0.4,
            },
        )
        assert corregida.status_code == 200, corregida.text
        assert corregida.json()["descuenta"] is True
        assert corregida.json()["dosis_por_ha"] == 200.0
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 420.0

    def test_corregir_no_pierde_la_marca_de_reenvio(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela, db_sesion
    ):
        """Si la marca se perdiera, un reenvío del móvil apuntaría la siembra otra vez."""
        from app import models

        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        siembra = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        ).json()
        cliente.put(
            f"/api/siembras/{siembra['id']}",
            headers=cuenta["cabeceras"],
            json={
                "semilla_id": semilla["id"],
                "parcela_id": tierra["id"],
                "cantidad_total": 60.0,
                "unidad_cantidad": "kg",
            },
        )
        guardada = db_sesion.get(models.Siembra, siembra["id"])
        assert guardada.clave_de_reenvio == "siembra-de-prueba-1"
        reenvio = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        )
        assert reenvio.status_code == 200, "el reenvío tiene que reconocer la siembra corregida"
        assert len(cliente.get("/api/siembras", headers=cuenta["cabeceras"]).json()) == 1
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 440.0


# --------------------------------------------------------------------------
# 6. La semilla como artículo del almacén y su etiqueta guardada
# --------------------------------------------------------------------------


class TestLaSemillaEsUnArticuloDelAlmacen:
    def test_dar_de_alta_una_semilla_la_mete_en_el_almacen(
        self, cliente, cuenta
    ):
        respuesta = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "Veza común Villalobos",
                "unidad": "kg",
                "especie": "Veza común",
                "tratada": None,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["categoria"] == "semilla"
        articulos = cliente.get("/api/almacen/articulos", headers=cuenta["cabeceras"]).json()
        assert [a["nombre"] for a in articulos] == ["Veza común Villalobos"]
        assert articulos[0]["categoria"] == "semilla"

    def test_no_se_crea_dos_veces_el_mismo_articulo(
        self, cliente, cuenta, almacen_con_semilla
    ):
        """La etiqueta de una semilla que ya entró por albarán se cuelga de **su** artículo."""
        almacen = almacen_con_semilla()
        primera = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        otra_vez = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"articulo_id": almacen["articulo_id"]},
        )
        assert otra_vez.status_code == 409, otra_vez.text
        articulos = cliente.get("/api/almacen/articulos", headers=cuenta["cabeceras"]).json()
        assert len(articulos) == 1, "no puede haber dos artículos para la misma semilla"
        assert primera["articulo_id"] == articulos[0]["id"]

    def test_una_dosis_sin_unidad_se_rechaza_diciendo_qué_falta(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"nombre": "Semilla suelta", "dosis_recomendada_por_ha": 120.0},
        )
        assert respuesta.status_code == 400, respuesta.text
        assert "mide" in respuesta.json()["detail"]

    def test_la_foto_de_la_etiqueta_se_guarda_y_se_sirve(self, cliente, cuenta):
        semilla = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"nombre": "Veza común Villalobos", "unidad": "kg"},
        ).json()
        assert semilla["tiene_foto"] is False
        subida = cliente.post(
            f"/api/semillas/{semilla['id']}/etiqueta",
            headers=cuenta["cabeceras"],
            files={"fichero": ("etiqueta.png", b"\x89PNG\r\n\x1a\nfoto", "image/png")},
        )
        assert subida.status_code == 200, subida.text
        assert subida.json()["tiene_foto"] is True
        servida = cliente.get(
            f"/api/semillas/{semilla['id']}/etiqueta", headers=cuenta["cabeceras"]
        )
        assert servida.status_code == 200
        assert servida.content == b"\x89PNG\r\n\x1a\nfoto"

    def test_el_nombre_del_fichero_no_decide_la_ruta(self, cliente, cuenta):
        """Un nombre como `../../app/main.py` no puede escribir fuera de su carpeta."""
        raiz = pathlib.Path(os.environ["CUEDIGITAL_ADJUNTOS"]).resolve()
        antes = {ruta for ruta in raiz.rglob("*") if ruta.is_file()}
        semilla = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"nombre": "Semilla con nombre raro", "unidad": "kg"},
        ).json()
        cliente.post(
            f"/api/semillas/{semilla['id']}/etiqueta",
            headers=cuenta["cabeceras"],
            files={"fichero": ("../../app/main.py", b"contenido", "image/png")},
        )
        nuevos = [ruta for ruta in raiz.rglob("*") if ruta.is_file() and ruta not in antes]
        assert len(nuevos) == 1, nuevos
        assert raiz in nuevos[0].parents, "el fichero se ha escrito fuera de la carpeta"
        assert ".." not in nuevos[0].name
        # Y el fichero de verdad del programa sigue donde estaba: nada de sobrescribir código.
        assert nuevos[0].read_bytes() == b"contenido"

    def test_corregir_la_etiqueta_deja_rastro(self, cliente, cuenta, db_sesion):
        from app import models

        semilla = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"nombre": "Cebada Pewter", "unidad": "kg", "poder_germinativo_pct": 95.0},
        ).json()
        corregida = cliente.put(
            f"/api/semillas/{semilla['id']}",
            headers=cuenta["cabeceras"],
            json={"poder_germinativo_pct": 90.0},
        )
        assert corregida.status_code == 200, corregida.text
        assert corregida.json()["poder_germinativo_pct"] == 90.0
        assert corregida.json()["nombre"] == "Cebada Pewter", "el nombre no se pierde al corregir"
        rastro = db_sesion.query(models.Auditoria).filter_by(entidad="semilla", accion="corregir")
        assert rastro.count() == 1
        assert rastro.first().datos["poder_germinativo_pct"] == [95.0, 90.0]


# --------------------------------------------------------------------------
# 7. De otra finca no se ve nada
# --------------------------------------------------------------------------


class TestDeOtraFincaNoSeVeNada:
    def test_la_semilla_de_otra_finca_no_se_ve(
        self, cliente, cuenta, almacen_con_semilla, crear_cuenta
    ):
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        otro = crear_cuenta("otro@ejemplo.test", "Otro agricultor", "12345678Z")

        assert cliente.get("/api/semillas", headers=otro["cabeceras"]).json() == []
        assert (
            cliente.get(f"/api/semillas/{semilla['id']}", headers=otro["cabeceras"]).status_code
            == 404
        )
        assert (
            cliente.put(
                f"/api/semillas/{semilla['id']}",
                headers=otro["cabeceras"],
                json={"nombre": "Robada"},
            ).status_code
            == 404
        )
        # **404 y no 403**: no se filtra si el identificador existe en otra finca.
        assert (
            cliente.get(
                f"/api/semillas/{semilla['id']}/etiqueta", headers=otro["cabeceras"]
            ).status_code
            == 404
        )

    def test_la_siembra_de_otra_finca_no_se_ve(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela, crear_cuenta
    ):
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        siembra = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        ).json()
        otro = crear_cuenta("otro@ejemplo.test", "Otro agricultor", "12345678Z")

        assert cliente.get("/api/siembras", headers=otro["cabeceras"]).json() == []
        assert (
            cliente.get(f"/api/siembras/{siembra['id']}", headers=otro["cabeceras"]).status_code
            == 404
        )
        assert (
            cliente.post(
                f"/api/siembras/{siembra['id']}/anular",
                headers=otro["cabeceras"],
                json={"motivo": "no es mía"},
            ).status_code
            == 404
        )
        # Y no puede sembrar con la semilla de otro: no la ve.
        respuesta = _sembrar(
            cliente, otro, semilla_id=semilla["id"], parcela_id=1, lote_id=None
        )
        assert respuesta.status_code == 404, respuesta.text

    def test_sin_vale_de_sesion_no_se_ve_nada(self, cliente):
        for ruta in ("/api/semillas", "/api/siembras"):
            assert cliente.get(ruta).status_code == 401, ruta


# --------------------------------------------------------------------------
# 8. Lo que cazó la revisión del ticket (03/10/2026)
# --------------------------------------------------------------------------


class TestLoQueCazoLaRevision:
    """Los ocho defectos que encontró la revisión, con su prueba aquí para que no vuelvan.

    Están en `tests/test_revision_t10.py` (el documento de la revisión) y **también aquí**: esta es la
    prueba del ticket, la que se ejecuta con el resto de la suite y la que un día avisará si alguien
    toca esto sin leer por qué estaba así.
    """

    def test_una_siembra_anulada_y_vuelta_a_apuntar_vuelve_a_descontar(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        """Antes la siembra nueva se creaba pero **su salida no**, porque la puerta del almacén
        encontraba la salida vieja por la clave de reenvío y la daba por buena. El almacén se quedaba
        diciendo que la semilla seguía en la nave y la respuesta decía que no descontaba «porque no se
        sabe de qué envase sale», con el envase escrito en la misma respuesta."""
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        primera = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
            clave_de_reenvio="la-cola-1",
        ).json()
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 300.0
        cliente.post(
            f"/api/siembras/{primera['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me equivoqué de tierra"},
        )
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 500.0
        # La cola del móvil reenvía **la misma petición**, con la misma clave: es lo que hace.
        otra = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
            clave_de_reenvio="la-cola-1",
        )
        assert otra.status_code == 201, otra.text
        datos = otra.json()
        assert datos["id"] != primera["id"], "es una siembra nueva, no la anulada"
        assert datos["descuenta"] is True, datos["no_descuenta_porque"]
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 300.0

    def test_una_segunda_salida_a_mano_para_la_misma_siembra_no_descuenta_dos_veces(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        """Una siembra saca la semilla de **un** envase: una segunda salida por otro envase sería
        descontar dos veces el mismo hecho."""
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        siembra = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        ).json()
        segundo = almacen_con_semilla(
            cantidad=300.0, numero_albaran="ALB-2026-78", numero_lote="4471-B"
        )
        assert segundo["articulo_id"] == almacen["articulo_id"], "es otro envase de la misma semilla"
        respuesta = cliente.post(
            "/api/almacen/salidas",
            headers=cuenta["cabeceras"],
            json={
                "apunte_tipo": "siembra",
                "apunte_id": siembra["id"],
                "lote_id": segundo["lote_id"],
                "cantidad": 200.0,
                "unidad": "kg",
            },
        )
        movimientos = cliente.get("/api/almacen/movimientos", headers=cuenta["cabeceras"]).json()
        vivas = [
            movimiento
            for movimiento in movimientos
            if movimiento["origen_tipo"] == "siembra"
            and movimiento["origen_id"] == siembra["id"]
            and movimiento["cuenta"]
        ]
        assert len(vivas) == 1, (
            f"la misma siembra ha descontado {len(vivas)} veces (respuesta {respuesta.status_code})"
        )

    def test_sin_tratamiento_no_se_lee_como_tratada(self):
        """Las negaciones son más de una: buscar solo «sin tratar» marcaba como tratada la frase más
        normal de un saco, justo al revés de lo que dice el papel."""
        for papel in (
            "SEMILLA SIN TRATAMIENTO",
            "NO LLEVA TRATAMIENTO",
            "NO SE HA APLICADO NINGÚN TRATAMIENTO",
        ):
            leida = semillas.lo_que_dice_la_etiqueta(semillas.EtiquetaLeida(), papel)
            assert leida.tratada is False, f"«{papel}» dice que no viene tratada"
        afirmada = semillas.lo_que_dice_la_etiqueta(
            semillas.EtiquetaLeida(), "SEMILLA TRATADA CON FUNGICIDA"
        )
        assert afirmada.tratada is True

    def test_la_unidad_de_la_dosis_se_guarda_en_su_forma_corta(self):
        """«120 kg por hectárea» es la misma unidad que «120 kg/ha», y se guardaba `kgporhectarea`:
        eso no es una unidad, y dejaba sin opción el desplegable de la dosis."""
        assert semillas._unidad_de("120 kg/ha") == "kg/ha"
        assert semillas._unidad_de("120 kg") == "kg"
        assert semillas._unidad_de("120 kg por hectárea") == "kg/ha"
        assert semillas._unidad_de("120 kilos/hectárea") == "kg/ha"
        leida = semillas.lo_que_dice_la_etiqueta(
            semillas.EtiquetaLeida(), "DOSIS RECOMENDADA: 120 kg por hectárea"
        )
        assert leida.dosis_recomendada_por_ha == 120.0
        assert leida.unidad_dosis == "kg/ha"

    def test_una_semilla_que_no_ha_entrado_nunca_no_dice_que_queda_cero(self, cliente, cuenta):
        """Sin albarán y sin ningún movimiento no se puede contar nada: el saco puede estar entero en
        la nave. «Te queda 0» es una afirmación, y el programa no la puede sostener."""
        semilla = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"nombre": "Veza que compré sin albarán", "unidad": "kg"},
        ).json()
        assert semilla["queda"]["saldo"] is None, semilla["queda"]
        assert semilla["queda"]["motivo"], "y tiene que decir por qué"

    def test_una_correccion_parcial_no_borra_lo_que_no_manda(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        """«Al corregir, lo que el formulario no pregunta tiene que viajar igual»: sin esto, corregir
        la cantidad desde fuera dejaba la siembra **sin fecha**."""
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        siembra = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        ).json()
        respuesta = cliente.put(
            f"/api/siembras/{siembra['id']}",
            headers=cuenta["cabeceras"],
            json={"semilla_id": semilla["id"], "parcela_id": tierra["id"], "cantidad_total": 150.0},
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["fecha"] == "2026-03-01", "la fecha que ya constaba no puede desaparecer"
        assert datos["superficie_ha"] == 1.0, "ni las hectáreas"
        assert datos["lote_id"] == almacen["lote_id"], "ni el envase del que sale"
        assert datos["cantidad_total"] == 150.0
        # Y con la corrección parcial sigue descontando: 500 − 150.
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 350.0

    def test_la_unidad_leida_es_siempre_una_de_las_que_ofrece_el_programa(self):
        """«2 L/ha», «2 l/ha» y «2 litros/ha» son la misma unidad, y tiene que quedar como `L/ha`:
        si no, el desplegable de la dosis se queda sin esa opción y la siembra acaba sin unidad (y sin
        descontar del almacén). Lo cazó la segunda pasada de la revisión."""
        for papel, esperada in (
            ("DOSIS: 2 L/ha", "L/ha"),
            ("DOSIS: 2 l/ha", "L/ha"),
            ("DOSIS: 2 litros/ha", "L/ha"),
            ("DOSIS: 250 g/ha", "g/ha"),
            ("DOSIS: 120 kg por hectárea", "kg/ha"),
        ):
            leida = semillas.lo_que_dice_la_etiqueta(semillas.EtiquetaLeida(), papel)
            assert leida.unidad_dosis == esperada, f"«{papel}» se lee como {leida.unidad_dosis!r}"
            assert leida.unidad_dosis in semillas.UNIDADES_DE_DOSIS, (
                f"{leida.unidad_dosis!r} no está entre las que ofrece la pantalla"
            )

    def test_la_semilla_de_una_siembra_no_se_cambia_y_se_dice_por_que(
        self, cliente, cuenta, almacen_con_semilla, crear_parcela
    ):
        """Cambiarla en silencio devolvía la semilla al almacén sola y dejaba la siembra diciendo que
        se sembró otra cosa."""
        almacen = almacen_con_semilla()
        semilla = _dar_de_alta_la_semilla(cliente, cuenta, almacen)
        tierra = crear_parcela()
        siembra = _sembrar(
            cliente,
            cuenta,
            semilla_id=semilla["id"],
            parcela_id=tierra["id"],
            lote_id=almacen["lote_id"],
        ).json()
        otra = cliente.post(
            "/api/semillas",
            headers=cuenta["cabeceras"],
            json={"nombre": "Trigo Craklin", "unidad": "kg"},
        ).json()
        respuesta = cliente.put(
            f"/api/siembras/{siembra['id']}",
            headers=cuenta["cabeceras"],
            json={"semilla_id": otra["id"], "parcela_id": tierra["id"]},
        )
        assert respuesta.status_code == 409, respuesta.text
        assert "anula" in respuesta.json()["detail"].lower(), respuesta.json()["detail"]
        leida = cliente.get(f"/api/siembras/{siembra['id']}", headers=cuenta["cabeceras"]).json()
        assert leida["semilla_id"] == semilla["id"], "la semilla ha cambiado en silencio"
        assert leida["descuenta"] is True, "y sigue descontando"
        assert _queda(cliente, cuenta, almacen["articulo_id"])["saldo"] == 300.0


# --------------------------------------------------------------------------
# 9. La copia de los textos que usan las pruebas de JavaScript
# --------------------------------------------------------------------------


class TestLaCopiaDeLosTextosNoSeQuedaVieja:
    """**Un test que lee ficheros necesita su propia prueba** (la regla de esta casa).

    Las pruebas de JavaScript comprueban la pantalla contra una copia de los textos del servidor: si
    esa copia se quedara atrás, el test daría por buena una pantalla que el agricultor no tiene (es el
    fallo que ya pasó con `plan.herramienta`, que salía en blanco en el test). Aquí se lee el fichero
    de JavaScript y se comprueba, clave por clave, que dice lo mismo que el servidor.
    """

    def test_la_copia_lleva_los_textos_de_las_semillas(self):
        import pathlib
        import re

        raiz = pathlib.Path(__file__).resolve().parents[2]
        fichero = raiz / "backend" / "tests_js" / "semillas.test.js"
        assert fichero.is_file(), "no está la copia de los textos en las pruebas de JavaScript"
        codigo = fichero.read_text(encoding="utf-8")
        encontrado = re.search(r"const TEXTOS = \{(.*?)\n\};", codigo, re.S)
        assert encontrado, "no encuentro la copia de los textos en `semillas.test.js`"
        copia = encontrado.group(1)

        for clave in (
            "titulo",
            "explica",
            "vacia",
            "anadir",
            "leer_etiqueta",
            "ficha_titulo",
            "especie",
            "dosis_recomendada",
            "poder_germinativo",
            "pureza",
            "no_lo_dice",
            "tratada",
            "lo_que_queda",
            "sin_saber_lo_que_queda",
            "siembras_titulo",
            "siembra_dosis",
            "siembra_cantidad_total",
            "calculado",
            "guardar_siembra",
        ):
            valor = textos.SEMILLAS[clave]
            assert valor.replace('"', '\\"') in copia or valor in copia, (
                f"la copia de los textos de JavaScript no lleva `{clave}`, o lo lleva cambiado: "
                f"el test comprobaría una pantalla que el agricultor no tiene ({valor!r})"
            )

    def test_la_copia_lleva_los_mensajes_que_la_pantalla_usa(self):
        import pathlib

        raiz = pathlib.Path(__file__).resolve().parents[2]
        codigo = (raiz / "backend" / "tests_js" / "semillas.test.js").read_text(encoding="utf-8")
        for codigo_mensaje in ("SM16_no_se_puede_sacar_sin_cantidad", "SM20_la_siembra_ya_estaba"):
            assert textos.MENSAJES[codigo_mensaje] in codigo, (
                f"la copia de los mensajes no lleva {codigo_mensaje}"
            )



# --------------------------------------------------------------------------
# La categoria de la semilla y de donde salio (CRM-07 #2, 14/10/2026)
# --------------------------------------------------------------------------
#
# **Lo que pide el contrato**: «Semilla: especie, variedad, **categoria** y evidencia,
# **comprada/propia**; **no certificada por defecto**». Y faltaban las dos columnas.
#
# **Ojo con la trampa**: `SemillaSalida` **ya tenia** un campo `categoria` — y es la del **ARTICULO**,
# no la de la semilla. Por eso estas columnas se llaman `categoria_semilla` y `procedencia`.


def _una_semilla_con_categoria(cliente, cuenta, almacen_con_semilla, **cambios):
    # **La fabrica se llama UNA vez**: cada llamada da de alta un articulo, y la segunda daria 200
    # en vez de 201 (que es lo que su propio ayudante exige).
    el_almacen = almacen_con_semilla()
    datos = {
        "articulo_id": el_almacen["articulo_id"],
        "unidad": el_almacen["unidad"],
        "especie": "Veza comun",
        "variedad": "Villalobos",
        "casa_comercial": "Semillas del Duero",
        "categoria_semilla": "certificada",
        "procedencia": "comprada",
    }
    datos.update(cambios)
    return cliente.post("/api/semillas", headers=cuenta["cabeceras"], json=datos)


def test_la_semilla_guarda_su_categoria_y_de_donde_salio(cliente, cuenta, almacen_con_semilla):
    respuesta = _una_semilla_con_categoria(cliente, cuenta, almacen_con_semilla)
    assert respuesta.status_code == 201, respuesta.text
    suya = respuesta.json()
    assert suya["categoria_semilla"] == "certificada", suya.get("categoria_semilla")
    assert suya["procedencia"] == "comprada"

    # Y se lee del listado, no solo del alta: un dato que se guarda y no se devuelve no llega a
    # ninguna pantalla.
    listado = cliente.get("/api/semillas", headers=cuenta["cabeceras"])
    assert listado.status_code == 200, listado.text
    la_suya = next(s for s in listado.json() if s["id"] == suya["id"])
    assert la_suya["categoria_semilla"] == "certificada"
    assert la_suya["procedencia"] == "comprada"


def test_sin_categoria_la_semilla_no_consta_y_no_se_inventa_una(cliente, cuenta, almacen_con_semilla):
    """**CORREGIDO el 14/10/2026, y el motivo importa.**

    *Antes* esta prueba exigia `"no_certificada"` cuando no se mandaba categoria. **Estaba mal**: *no
    haber registrado la etiqueta **no demuestra** que el lote carezca de certificacion*, y el
    reglamento de semillas distingue categorias y remite a reglamentos tecnicos por especie. Ausencia
    es **«no consta»** (`None`), no una categoria. *«No certificada» sigue siendo una de las que se
    pueden declarar* — y eso lo prueba la prueba de al lado.
    """
    respuesta = _una_semilla_con_categoria(
        cliente, cuenta, almacen_con_semilla, categoria_semilla=None, procedencia=None
    )
    assert respuesta.status_code == 201, respuesta.text
    suya = respuesta.json()
    assert suya["categoria_semilla"] is None, (
        f"sin categoria, la semilla dice «no consta»: vino {suya.get('categoria_semilla')!r}"
    )
    assert suya["procedencia"] is None


def test_la_categoria_declarada_se_guarda_tal_cual(cliente, cuenta, almacen_con_semilla):
    # Y cuando el agricultor **sabe** que no esta certificada, lo dice él: es una categoria, no un hueco.
    respuesta = _una_semilla_con_categoria(
        cliente, cuenta, almacen_con_semilla, categoria_semilla="no_certificada"
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["categoria_semilla"] == "no_certificada"


def test_la_categoria_del_articulo_no_se_confunde_con_la_de_la_semilla(
    cliente, cuenta, almacen_con_semilla
):
    # La trampa medida: `categoria` (la del articulo) y `categoria_semilla` son **dos cosas**.
    respuesta = _una_semilla_con_categoria(cliente, cuenta, almacen_con_semilla, categoria_semilla="r1")
    assert respuesta.status_code == 201, respuesta.text
    suya = respuesta.json()
    assert suya["categoria_semilla"] == "r1"
    assert suya["categoria"] != "r1", (
        "la categoria de la semilla ha pisado la del articulo: son dos campos distintos"
    )


# --------------------------------------------------------------------------
# Las cuatro pruebas de aceptacion de la revision (14/10/2026)
# --------------------------------------------------------------------------
#
# *El fallo que encontró el dueño*: **corregir solo la variedad borraba los dos campos**. La causa
# era que la corrección construye la fila con una lista blanca (`lo_que_hay`) en la que no estaban.
# *Y estos cuatro casos son los que la revision exige, uno por uno.*


def _corregir(cliente, cuenta, semilla, **cambios):
    return cliente.put(
        f"/api/semillas/{semilla['id']}", headers=cuenta["cabeceras"], json=cambios
    )


def _la_ficha(cliente, cuenta, semilla_id) -> dict:
    listado = cliente.get("/api/semillas", headers=cuenta["cabeceras"])
    assert listado.status_code == 200, listado.text
    return next(s for s in listado.json() if s["id"] == semilla_id)


def test_corregir_la_variedad_conserva_la_categoria_y_la_procedencia(
    cliente, cuenta, almacen_con_semilla
):
    """**El fallo que encontró el dueño, con su caso exacto.**

    Antes: la corrección construía la fila con `lo_que_hay`, que no incluía los dos campos → **la
    variedad sola los ponía a `null`**. Es el defecto A1 de `docs/T02_VALORES_POR_DEFECTO.md`:
    **«lo que la petición no manda, no se borra»**.
    """
    alta = _una_semilla_con_categoria(cliente, cuenta, almacen_con_semilla)
    assert alta.status_code == 201, alta.text
    suya = alta.json()
    assert (suya["categoria_semilla"], suya["procedencia"]) == ("certificada", "comprada")

    corregida = _corregir(cliente, cuenta, suya, variedad="Otra variedad")
    assert corregida.status_code == 200, corregida.text
    despues = _la_ficha(cliente, cuenta, suya["id"])

    assert despues["variedad"] == "Otra variedad", "la variedad no se corrigio"
    assert despues["categoria_semilla"] == "certificada", (
        f"corregir la variedad ha BORRADO la categoria: {despues['categoria_semilla']!r}"
    )
    assert despues["procedencia"] == "comprada", (
        f"corregir la variedad ha BORRADO la procedencia: {despues['procedencia']!r}"
    )


def test_corregir_los_dos_campos_si_los_cambia_y_deja_rastro(cliente, cuenta, almacen_con_semilla):
    # Y mandandolos, se guardan: era el segundo caso que no funcionaba.
    alta = _una_semilla_con_categoria(cliente, cuenta, almacen_con_semilla)
    assert alta.status_code == 201, alta.text
    suya = alta.json()

    corregida = _corregir(cliente, cuenta, suya, categoria_semilla="r2", procedencia="propia")
    assert corregida.status_code == 200, corregida.text
    despues = _la_ficha(cliente, cuenta, suya["id"])
    assert despues["categoria_semilla"] == "r2", despues["categoria_semilla"]
    assert despues["procedencia"] == "propia", despues["procedencia"]


def test_el_vacio_explicito_conserva_su_significado(cliente, cuenta, almacen_con_semilla):
    # **Vacío explícito ≠ no enviado**: mandar `None` a propósito dice «no consta», y se guarda así.
    alta = _una_semilla_con_categoria(cliente, cuenta, almacen_con_semilla)
    suya = alta.json()

    corregida = _corregir(cliente, cuenta, suya, categoria_semilla=None)
    assert corregida.status_code == 200, corregida.text
    despues = _la_ficha(cliente, cuenta, suya["id"])
    assert despues["categoria_semilla"] is None, (
        "el vacio explicito tiene que dejar «no consta», no conservar lo de antes"
    )
    assert despues["procedencia"] == "comprada", "y lo que NO se mando, se conserva"


def test_una_categoria_inventada_se_rechaza_sin_escribir(cliente, cuenta, almacen_con_semilla):
    # **Valor inválido: error claro y NINGUNA escritura.** Es el criterio literal de la revision.
    alta = _una_semilla_con_categoria(cliente, cuenta, almacen_con_semilla)
    suya = alta.json()

    respuesta = _corregir(cliente, cuenta, suya, categoria_semilla="lo_que_sea")
    assert respuesta.status_code == 422, respuesta.text
    assert "categoria" in respuesta.text.lower(), respuesta.text

    despues = _la_ficha(cliente, cuenta, suya["id"])
    assert despues["categoria_semilla"] == "certificada", (
        "un valor invalido NO puede escribir nada: la semilla se ha quedado tocada"
    )
    assert despues["variedad"] == "Villalobos"
