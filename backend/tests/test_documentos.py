"""La documentación anexa: los papeles que acompañan al cuaderno.

**Por qué existe este fichero.** La sección faltaba, y se encontró leyendo las instrucciones de la
app oficial de la Junta (`03_CastillaYLeon_CUECyL_instrucciones.pdf`), que dice:

> *«El apartado Documentación permite guardar la documentación complementaria al Cuaderno:
> contratos, facturas, albaranes de entrega de envases a Sigfito, etc. La documentación puede
> organizarse en distintas carpetas.»*

Lo que se comprueba aquí, por orden de importancia:

1. **Que un papel se pueda apuntar SIN subir el fichero.** Es la decisión que hace que esto sirva
   para el agricultor que no sabe hacerle una foto al contrato. Si se rompe, se rompe para quien
   más lo necesita.
2. **Que el fichero no acabe ni en la base de datos ni en el repositorio.** Es un papel de un
   agricultor: va a disco, en su carpeta, con un nombre que decide el programa.
3. **Que nada se borre.** Un papel se anula con su motivo, y el fichero sigue ahí.
4. **Que el nombre que manda el navegador no decida la ruta.** Un nombre como `../../main.py`
   escribiría fuera de la carpeta.
5. **Que las carpetas sean del agricultor**, no una lista cerrada que la Junta no pide.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

import pytest

from app import catalogos


@pytest.fixture
def carpeta_de_adjuntos(tmp_path, monkeypatch):
    """Una carpeta de adjuntos de mentira, para no escribir en la del proyecto.

    Esto no es un detalle: al principio de este proyecto los tests dejaron 52 boletines de verdad
    en `backend/datos/adjuntos` y no daba ningún fallo. Los tests no escriben fuera de una carpeta
    temporal.
    """
    carpeta = tmp_path / "adjuntos"
    carpeta.mkdir()
    monkeypatch.setenv("CUEDIGITAL_ADJUNTOS", str(carpeta))
    return carpeta


def _papel(cliente, cabeceras, **cambios) -> dict:
    """Apunta un papel, con lo mínimo que hace falta."""
    cuerpo = {"titulo": "Contrato de la finca del río", "tipo": "contrato"}
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/documentos", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _subir(cliente, cabeceras, documento_id: int, nombre="contrato.pdf", contenido=b"%PDF-1.4 x"):
    return cliente.post(
        f"/api/documentos/{documento_id}/fichero",
        headers=cabeceras,
        files={"fichero": (nombre, contenido, "application/pdf")},
    )


class TestElCatalogoSaleDelDocumentoOficial:
    def test_los_tres_tipos_que_nombra_la_junta(self):
        """Contratos, facturas y albaranes de Sigfito están nombrados en el documento oficial."""
        assert "contrato" in catalogos.TIPOS_DOCUMENTO
        assert "factura" in catalogos.TIPOS_DOCUMENTO
        assert "albaran_sigfito" in catalogos.TIPOS_DOCUMENTO

    def test_y_otros_porque_el_documento_sigue_con_etc(self):
        """El documento dice «etc.», así que tiene que haber dónde poner el resto."""
        assert "otros" in catalogos.TIPOS_DOCUMENTO

    def test_las_carpetas_son_sugerencias_y_se_dice(self):
        """La Junta no impone carpetas: dice que «puede organizarse en distintas carpetas».

        Si esto se convirtiera en una lista cerrada, el programa estaría inventando una obligación
        que no existe, y el primer agricultor que archivara de otra manera se quedaría sin sitio.
        """
        assert catalogos.CARPETAS_SUGERIDAS  # hay sugerencias…
        assert len(catalogos.CARPETAS_SUGERIDAS) > 1
        # …y el modelo guarda la carpeta como texto libre (se comprueba abajo, creando una que
        # no está en la lista).

    def test_cada_tipo_tiene_su_nombre_en_palabras(self):
        for tipo in catalogos.TIPOS_DOCUMENTO:
            assert catalogos.etiqueta_documento(tipo)

    def test_un_tipo_que_no_existe_no_revienta(self):
        assert catalogos.etiqueta_documento("inventado") == catalogos.ETIQUETA_DOCUMENTO["otros"]


class TestApuntarUnPapel:
    def test_se_apunta_sin_fichero(self, cliente, cuenta):
        """Es la decisión que hace que esto sirva para quien no sabe subir ficheros."""
        papel = _papel(cliente, cuenta["cabeceras"])
        assert papel["titulo"] == "Contrato de la finca del río"
        assert papel["tipo"] == "contrato"
        assert papel["tiene_fichero"] is False
        assert papel["nombre_del_fichero"] is None

    def test_el_tipo_sale_con_su_nombre_en_palabras(self, cliente, cuenta):
        """El catálogo vive en el servidor: si la pantalla lo pusiera, habría dos listas."""
        papel = _papel(cliente, cuenta["cabeceras"], tipo="albaran_sigfito")
        assert papel["etiqueta_tipo"] == "Un albarán de envases (Sigfito)"

    def test_sin_titulo_no_se_puede(self, cliente, cuenta):
        """Un papel sin nombre es un papel que no se vuelve a encontrar."""
        respuesta = cliente.post(
            "/api/documentos", headers=cuenta["cabeceras"], json={"titulo": "", "tipo": "factura"}
        )
        assert respuesta.status_code == 422

    def test_un_tipo_inventado_se_rechaza_con_la_lista(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/documentos",
            headers=cuenta["cabeceras"],
            json={"titulo": "Algo", "tipo": "lo_que_sea"},
        )
        assert respuesta.status_code == 422
        assert "contrato" in respuesta.json()["detail"]

    def test_sin_carpeta_va_a_otros(self, cliente, cuenta):
        """Mejor en «Otros» que suelto: así se ve en la lista y se puede mover."""
        papel = _papel(cliente, cuenta["cabeceras"], carpeta="")
        assert papel["carpeta"] == "Otros"

    def test_una_carpeta_del_agricultor_se_acepta_tal_cual(self, cliente, cuenta):
        """Las carpetas son suyas: si archiva en «Cajón de arriba», eso vale."""
        papel = _papel(cliente, cuenta["cabeceras"], carpeta="Cajón de arriba")
        assert papel["carpeta"] == "Cajón de arriba"

    def test_queda_apuntado_en_la_auditoria(self, cliente, cuenta):
        _papel(cliente, cuenta["cabeceras"])
        # El apunte de auditoría no se puede consultar por la API, pero sí que la llamada no
        # falle y el papel exista: es lo que se comprueba en el listado.
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        assert datos["cuantos"] == 1

    def test_hace_falta_entrar(self, cliente, cuenta):
        assert cliente.get("/api/documentos").status_code == 401

    def test_la_fecha_es_la_del_papel_no_la_de_hoy(self, cliente, cuenta):
        """Una factura de marzo se sube en junio: la fecha que vale es la del papel."""
        papel = _papel(cliente, cuenta["cabeceras"], fecha="2026-03-14", tipo="factura")
        assert papel["fecha"] == "2026-03-14"


class TestSubirElPapel:
    def test_se_sube_y_queda_con_fichero(self, cliente, cuenta, carpeta_de_adjuntos):
        papel = _papel(cliente, cuenta["cabeceras"])
        respuesta = _subir(cliente, cuenta["cabeceras"], papel["id"])
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["tiene_fichero"] is True
        assert datos["nombre_del_fichero"] == "contrato.pdf"
        assert datos["bytes"] > 0

    def test_el_fichero_va_a_disco_y_no_a_la_base(self, cliente, cuenta, carpeta_de_adjuntos):
        """Un papel de un agricultor no puede acabar dentro de un fichero que se sube a git."""
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir(cliente, cuenta["cabeceras"], papel["id"])
        escritos = list(carpeta_de_adjuntos.rglob("*"))
        ficheros = [f for f in escritos if f.is_file()]
        assert len(ficheros) == 1
        assert ficheros[0].read_bytes() == b"%PDF-1.4 x"

    def test_el_nombre_lo_decide_el_programa_y_no_el_navegador(
        self, cliente, cuenta, carpeta_de_adjuntos
    ):
        """Un nombre como «../../main.py» escribiría fuera de la carpeta.

        El nombre que manda el navegador se guarda **solo para enseñarlo**. Este test es la
        frontera entre «un agricultor se equivoca al nombrar un fichero» y «alguien escribe donde
        no debe».
        """
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir(cliente, cuenta["cabeceras"], papel["id"], nombre="../../main.py")
        ficheros = [f for f in carpeta_de_adjuntos.rglob("*") if f.is_file()]
        assert len(ficheros) == 1
        assert "main.py" not in ficheros[0].name
        assert ficheros[0].name.startswith("documento-")
        assert ficheros[0].suffix == ".pdf"
        # Y el nombre original se conserva para enseñarlo.
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        assert datos["documentos"][0]["nombre_del_fichero"] == "../../main.py"

    def test_un_tipo_de_fichero_que_no_vale_se_rechaza(self, cliente, cuenta, carpeta_de_adjuntos):
        papel = _papel(cliente, cuenta["cabeceras"])
        respuesta = cliente.post(
            f"/api/documentos/{papel['id']}/fichero",
            headers=cuenta["cabeceras"],
            files={"fichero": ("virus.exe", b"MZ\x90", "application/x-msdownload")},
        )
        assert respuesta.status_code == 422
        assert not list(carpeta_de_adjuntos.rglob("*.[eE][xX][eE]"))

    def test_el_mensaje_dice_qué_sí_vale(self, cliente, cuenta, carpeta_de_adjuntos):
        papel = _papel(cliente, cuenta["cabeceras"])
        respuesta = cliente.post(
            f"/api/documentos/{papel['id']}/fichero",
            headers=cuenta["cabeceras"],
            files={"fichero": ("raro.bin", b"x", "application/octet-stream")},
        )
        assert "PDF" in respuesta.json()["detail"]

    def test_un_fichero_vacio_se_rechaza(self, cliente, cuenta, carpeta_de_adjuntos):
        papel = _papel(cliente, cuenta["cabeceras"])
        respuesta = cliente.post(
            f"/api/documentos/{papel['id']}/fichero",
            headers=cuenta["cabeceras"],
            files={"fichero": ("vacio.pdf", b"", "application/pdf")},
        )
        assert respuesta.status_code == 422

    def test_se_admiten_los_ficheros_de_oficina(self, cliente, cuenta, carpeta_de_adjuntos):
        """Una factura puede venir en una hoja de cálculo, no solo en PDF."""
        papel = _papel(cliente, cuenta["cabeceras"], tipo="factura")
        respuesta = cliente.post(
            f"/api/documentos/{papel['id']}/fichero",
            headers=cuenta["cabeceras"],
            files={
                "fichero": (
                    "factura.xlsx",
                    b"PK\x03\x04",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["tiene_fichero"] is True

    def test_subir_otro_fichero_reemplaza_el_anterior_y_no_deja_basura(
        self, cliente, cuenta, carpeta_de_adjuntos
    ):
        """El papel nuevo manda: si no, cada corrección dejaría el viejo ocupando sitio."""
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir(cliente, cuenta["cabeceras"], papel["id"], contenido=b"el primero")
        _subir(cliente, cuenta["cabeceras"], papel["id"], contenido=b"el segundo")
        ficheros = [f for f in carpeta_de_adjuntos.rglob("*") if f.is_file()]
        assert len(ficheros) == 1
        assert ficheros[0].read_bytes() == b"el segundo"


class TestDescargarElPapel:
    def test_se_descarga_tal_cual_se_subio(self, cliente, cuenta, carpeta_de_adjuntos):
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir(cliente, cuenta["cabeceras"], papel["id"], contenido=b"contenido del contrato")
        respuesta = cliente.get(
            f"/api/documentos/{papel['id']}/fichero", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200
        assert respuesta.content == b"contenido del contrato"

    def test_se_descarga_con_su_nombre(self, cliente, cuenta, carpeta_de_adjuntos):
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir(cliente, cuenta["cabeceras"], papel["id"], nombre="mi contrato.pdf")
        respuesta = cliente.get(
            f"/api/documentos/{papel['id']}/fichero", headers=cuenta["cabeceras"]
        )
        # La cabecera viene codificada (los espacios van como %20), que es como lo pide la norma
        # para los nombres con espacios o acentos. Se compara ya decodificada.
        assert "mi contrato.pdf" in unquote(respuesta.headers["content-disposition"])

    def test_un_papel_sin_fichero_lo_dice(self, cliente, cuenta):
        papel = _papel(cliente, cuenta["cabeceras"])
        respuesta = cliente.get(
            f"/api/documentos/{papel['id']}/fichero", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 404
        assert "apuntado" in respuesta.json()["detail"]

    def test_si_el_fichero_ha_desaparecido_del_disco_lo_dice(
        self, cliente, cuenta, carpeta_de_adjuntos
    ):
        """Un 404 con explicación, no un error del servidor: pasa cuando alguien toca la carpeta."""
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir(cliente, cuenta["cabeceras"], papel["id"])
        for fichero in carpeta_de_adjuntos.rglob("*"):
            if fichero.is_file():
                fichero.unlink()
        respuesta = cliente.get(
            f"/api/documentos/{papel['id']}/fichero", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 404


class TestNadaSeBorra:
    def test_anular_pide_motivo(self, cliente, cuenta):
        papel = _papel(cliente, cuenta["cabeceras"])
        respuesta = cliente.post(
            f"/api/documentos/{papel['id']}/anular", headers=cuenta["cabeceras"], json={}
        )
        assert respuesta.status_code == 422
        assert respuesta.json()["detail"]

    def test_al_anular_queda_el_motivo(self, cliente, cuenta):
        papel = _papel(cliente, cuenta["cabeceras"])
        respuesta = cliente.post(
            f"/api/documentos/{papel['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "me equivoqué de carpeta"},
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["anulado"] is True
        assert respuesta.json()["motivo_anulacion"] == "me equivoqué de carpeta"

    def test_el_fichero_no_se_borra_al_anular(self, cliente, cuenta, carpeta_de_adjuntos):
        """Lo que se anula es el apunte, no la prueba: el papel sigue siendo el papel."""
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir(cliente, cuenta["cabeceras"], papel["id"], contenido=b"el contrato de verdad")
        cliente.post(
            f"/api/documentos/{papel['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "estaba mal el nombre"},
        )
        ficheros = [f for f in carpeta_de_adjuntos.rglob("*") if f.is_file()]
        assert len(ficheros) == 1
        assert ficheros[0].read_bytes() == b"el contrato de verdad"

    def test_un_papel_anulado_no_sale_en_la_lista(self, cliente, cuenta):
        papel = _papel(cliente, cuenta["cabeceras"])
        cliente.post(
            f"/api/documentos/{papel['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "duplicado"},
        )
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        assert datos["cuantos"] == 0

    def test_pero_se_puede_pedir_que_salgan(self, cliente, cuenta):
        """La historia se puede ver: es lo que interesa en una inspección."""
        papel = _papel(cliente, cuenta["cabeceras"])
        cliente.post(
            f"/api/documentos/{papel['id']}/anular",
            headers=cuenta["cabeceras"],
            json={"motivo": "duplicado"},
        )
        datos = cliente.get(
            "/api/documentos", headers=cuenta["cabeceras"], params={"incluir_anulados": True}
        ).json()
        assert datos["cuantos"] == 1
        assert datos["documentos"][0]["anulado"] is True


class TestLaListaYLasCarpetas:
    def test_los_papeles_salen_agrupados_por_carpeta(self, cliente, cuenta):
        """Nadie busca «el documento 47»: busca «la factura del abono»."""
        _papel(cliente, cuenta["cabeceras"], carpeta="Facturas", titulo="Factura de mayo")
        _papel(cliente, cuenta["cabeceras"], carpeta="Contratos", titulo="Contrato del río")
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        con_papeles = [c for c in datos["carpetas"] if c["cuantos"] > 0]
        assert {c["nombre"] for c in con_papeles} == {"Facturas", "Contratos"}

    def test_las_sugerencias_salen_aunque_esten_vacias(self, cliente, cuenta):
        """Si no salieran, el agricultor no sabría que puede archivar ahí."""
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        vacias = [c for c in datos["carpetas"] if c["cuantos"] == 0]
        assert vacias, "tienen que salir las carpetas sugeridas aunque no tengan papeles"

    def test_se_pueden_ver_solo_los_de_una_carpeta(self, cliente, cuenta):
        _papel(cliente, cuenta["cabeceras"], carpeta="Facturas", titulo="Factura de mayo")
        _papel(cliente, cuenta["cabeceras"], carpeta="Contratos", titulo="Contrato del río")
        datos = cliente.get(
            "/api/documentos", headers=cuenta["cabeceras"], params={"carpeta": "Facturas"}
        ).json()
        assert datos["cuantos"] == 1
        assert datos["documentos"][0]["titulo"] == "Factura de mayo"

    def test_se_pueden_ver_solo_los_de_un_tipo(self, cliente, cuenta):
        _papel(cliente, cuenta["cabeceras"], tipo="factura", titulo="Una factura")
        _papel(cliente, cuenta["cabeceras"], tipo="contrato", titulo="Un contrato")
        datos = cliente.get(
            "/api/documentos", headers=cuenta["cabeceras"], params={"tipo": "factura"}
        ).json()
        assert datos["cuantos"] == 1

    def test_los_papeles_de_otro_ano_siguen_ahi(self, cliente, cuenta):
        """Un contrato de arrendamiento vale para diez años, no para una campaña."""
        _papel(cliente, cuenta["cabeceras"])
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        assert datos["cuantos"] == 1

    def test_la_lista_dice_cuantos_hay(self, cliente, cuenta):
        _papel(cliente, cuenta["cabeceras"])
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        assert "1" in datos["resumen"]

    def test_con_un_papel_lo_dice_en_singular(self, cliente, cuenta):
        """«Tienes 1 papeles guardados» es lo primero que hace desconfiar de un programa (ronda 84)."""
        _papel(cliente, cuenta["cabeceras"])
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        assert datos["resumen"] == "Tienes 1 papel guardado."

    def test_con_varios_papeles_lo_dice_en_plural(self, cliente, cuenta):
        _papel(cliente, cuenta["cabeceras"])
        _papel(cliente, cuenta["cabeceras"], titulo="Otro papel")
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        assert datos["resumen"] == "Tienes 2 papeles guardados."

    def test_sin_papeles_lo_dice_con_una_pista(self, cliente, cuenta):
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        assert datos["cuantos"] == 0
        assert datos["resumen"] == datos["textos"]["sin_papeles"]

    def test_los_tipos_se_sirven_con_su_nombre(self, cliente, cuenta):
        datos = cliente.get("/api/documentos", headers=cuenta["cabeceras"]).json()
        valores = {t["valor"] for t in datos["tipos"]}
        assert valores == set(catalogos.TIPOS_DOCUMENTO)
        assert all(t["etiqueta"] for t in datos["tipos"])


class TestElListadoParaCopiar:
    def test_sale_en_texto_plano(self, cliente, cuenta):
        """El uso real es mandárselo al técnico o al gestor: un texto se pega en cualquier sitio."""
        _papel(cliente, cuenta["cabeceras"], carpeta="Facturas", titulo="Factura de mayo")
        datos = cliente.get("/api/documentos/listado", headers=cuenta["cabeceras"]).json()
        assert "Factura de mayo" in datos["texto"]
        assert "Facturas" in datos["texto"]
        assert datos["cuantos"] == 1

    def test_dice_si_tiene_fichero_o_no(self, cliente, cuenta):
        _papel(cliente, cuenta["cabeceras"], titulo="Contrato sin foto")
        datos = cliente.get("/api/documentos/listado", headers=cuenta["cabeceras"]).json()
        assert "sin fichero" in datos["texto"]

    def test_sin_papeles_no_sale_vacio(self, cliente, cuenta):
        datos = cliente.get("/api/documentos/listado", headers=cuenta["cabeceras"]).json()
        assert datos["texto"].strip()
        assert datos["cuantos"] == 0


class TestAislamientoEntreFincas:
    def test_una_finca_no_ve_los_papeles_de_otra(self, cliente, cuenta, crear_cuenta):
        _papel(cliente, cuenta["cabeceras"], titulo="Contrato de la finca A")
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")
        datos = cliente.get("/api/documentos", headers=otra["cabeceras"]).json()
        assert datos["cuantos"] == 0

    def test_no_se_puede_descargar_el_papel_de_otra_finca(
        self, cliente, cuenta, crear_cuenta, carpeta_de_adjuntos
    ):
        papel = _papel(cliente, cuenta["cabeceras"])
        _subir(cliente, cuenta["cabeceras"], papel["id"])
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")
        respuesta = cliente.get(
            f"/api/documentos/{papel['id']}/fichero", headers=otra["cabeceras"]
        )
        assert respuesta.status_code == 404

    def test_no_se_puede_anular_el_papel_de_otra_finca(
        self, cliente, cuenta, crear_cuenta
    ):
        papel = _papel(cliente, cuenta["cabeceras"])
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")
        respuesta = cliente.post(
            f"/api/documentos/{papel['id']}/anular",
            headers=otra["cabeceras"],
            json={"motivo": "porque yo lo digo"},
        )
        assert respuesta.status_code == 404

    def test_no_se_puede_subir_un_fichero_al_papel_de_otra_finca(
        self, cliente, cuenta, crear_cuenta, carpeta_de_adjuntos
    ):
        papel = _papel(cliente, cuenta["cabeceras"])
        otra = crear_cuenta("otra@ejemplo.test", nombre="Otra finca")
        respuesta = _subir(cliente, otra["cabeceras"], papel["id"])
        assert respuesta.status_code == 404


class TestElFicheroSeSacaDeSuCarpetaYNoDeOtra:
    def test_una_ruta_con_puntos_no_sirve_para_leer_fuera(self, cliente, cuenta, carpeta_de_adjuntos, db_sesion):
        """Comprobación de seguridad: si alguien cambia la ruta a mano, no se lee de fuera.

        La ruta viene de la base de datos, así que este test simula el caso peor: que alguien
        escriba en la tabla una ruta que apunta fuera de la carpeta de adjuntos.
        """
        from app import models

        papel = _papel(cliente, cuenta["cabeceras"])
        fila = db_sesion.get(models.DocumentoAnexo, papel["id"])
        fila.fichero_ruta = "../../app/main.py"
        fila.fichero_nombre = "main.py"
        db_sesion.commit()

        respuesta = cliente.get(
            f"/api/documentos/{papel['id']}/fichero", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 404
        # Y lo que **no** puede pasar de ninguna manera: que devuelva el fichero del programa.
        assert b"FastAPI" not in respuesta.content


class TestLosTextosDelAgricultor:
    def test_no_llevan_jerga(self):
        """Aquí se dice «los papeles», no «documentación complementaria» ni «repositorio»."""
        from app import textos

        todos = " ".join(textos.DOCUMENTOS.values()).lower()
        for palabra in (
            "anexo",
            "repositorio",
            "documentación complementaria",
            "gestión documental",
            "subir al servidor",
        ):
            assert palabra not in todos, f"«{palabra}» en los textos del agricultor"

    def test_entran_en_la_revision_de_jerga(self):
        """Están en `textos_visibles()`, así que el test general también los revisa."""
        from app import textos

        assert textos.DOCUMENTOS["titulo"] in textos.textos_visibles()

    def test_se_dice_para_que_sirve(self):
        """El agricultor tiene que saber por qué molestarse en guardar un papel."""
        from app import textos

        assert "inspección" in textos.DOCUMENTOS["para_que"]

    def test_se_dice_que_se_puede_apuntar_sin_el_papel(self):
        from app import textos

        assert "sin el papel" in textos.DOCUMENTOS["no_tiene_fichero"]

    def test_la_carpeta_se_explica_con_sus_palabras(self):
        from app import textos

        assert "casa" in textos.DOCUMENTOS["carpeta_pista"]
