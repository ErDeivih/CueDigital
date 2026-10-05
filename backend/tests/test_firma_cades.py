"""Comprobar la firma del cuaderno de verdad.

Lo que se prueba aquí, y por qué importa:

**Hasta la ronda 12 el fichero de firma se guardaba sin abrirlo.** Se comprobaba que la huella
que decía el agricultor fuera la del cuaderno, pero nadie miraba dentro del fichero: se podía
subir un fichero de texto, la firma de otro documento o la firma de otro agricultor, y el
programa lo guardaba igual. Estos tests cierran ese hueco.

**Y lo que se prueba no son firmas inventadas por mí.** Los ficheros de `fixtures/firma_cades`
los generó **OpenSSL de verdad**, con la misma estructura que produce AutoFirma (un CAdES es un
CMS con los atributos firmados dentro). Probar un lector binario contra ficheros hechos por el
mismo programa que los lee no probaría nada: se estaría comprobando que soy coherente conmigo
mismo. Ver el `LEEME.md` de esa carpeta.

La distinción que más se comprueba aquí, y la que más importa:

- **`mal`** es «esta firma no es de este cuaderno». Eso se rechaza.
- **`no_comprobada`** es «no sé leer esta firma». Eso **no** se rechaza: se guarda y se dice.
  Confundir las dos cosas sería llamar mentiroso a un agricultor por no saber leer su
  certificado. Hay un test por cada lado de esa frontera.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from app import cades

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "firma_cades"


def fichero(nombre: str) -> bytes:
    return (FIXTURES / nombre).read_bytes()


@pytest.fixture(scope="module")
def contenido() -> bytes:
    return fichero("cuaderno_de_prueba.txt")


@pytest.fixture(scope="module")
def cambiado() -> bytes:
    return fichero("cuaderno_cambiado.txt")


def der_de_un_pem(nombre: str) -> bytes:
    """El certificado en binario, que es como va dentro de la firma."""
    texto = fichero(nombre).decode("utf-8")
    limpio = "".join(linea for linea in texto.splitlines() if not linea.startswith("-----"))
    return base64.b64decode(limpio)


# --------------------------------------------------------------------------
# Leer la estructura
# --------------------------------------------------------------------------


class TestLeerLaEstructura:
    def test_lee_un_trozo_corto(self):
        etiqueta, valor, siguiente = cades.leer_tlv(b"\x02\x03abc", 0)
        assert (etiqueta, valor, siguiente) == (0x02, b"abc", 5)

    def test_lee_un_trozo_largo(self):
        """Los certificados y las firmas pasan de 127 bytes, así que el tamaño va en dos bytes."""
        cuerpo = b"x" * 300
        datos = b"\x30\x82\x01\x2c" + cuerpo
        etiqueta, valor, siguiente = cades.leer_tlv(datos, 0)
        assert etiqueta == 0x30
        assert valor == cuerpo
        assert siguiente == len(datos)

    def test_un_fichero_cortado_se_trata_como_ilegible(self):
        with pytest.raises(cades.NoSeEntiende):
            cades.leer_tlv(b"\x30\x10abc", 0)

    def test_un_tamano_imposible_se_trata_como_ilegible(self):
        """Un tamaño de 8 bytes no cabe en un fichero de firma: es basura, no un caso raro."""
        with pytest.raises(cades.NoSeEntiende):
            cades.leer_tlv(b"\x30\x88" + b"\x01" * 8, 0)

    def test_leer_un_identificador_oficial(self):
        assert cades.leer_oid(bytes.fromhex("550403")) == "2.5.4.3"
        assert cades.leer_oid(bytes.fromhex("2a864886f70d010101")) == "1.2.840.113549.1.1.1"

    def test_reconstruir_el_conjunto_con_tamanos_distintos(self):
        """Esto es lo que se firma de verdad: si el tamaño se arma mal, no cuadra nunca."""
        for largo in (10, 200, 40000):
            cuerpo = b"y" * largo
            montado = cades.reconstruir_conjunto(cuerpo)
            assert montado[0] == 0x31
            _e, valor, _s = cades.leer_tlv(montado, 0)
            assert valor == cuerpo


class TestLosCertificadosDePrueba:
    def test_saca_el_titular_del_certificado(self):
        sujeto = cades.sujeto_del_certificado(der_de_un_pem("certificado.pem"))
        assert sujeto["CN"] == "PEREZ VELASCO DAVID"
        assert sujeto["serialNumber"] == "70922320A"
        assert sujeto["C"] == "ES"

    def test_saca_el_nif_del_certificado(self):
        sujeto = cades.sujeto_del_certificado(der_de_un_pem("certificado.pem"))
        assert cades.nif_del_sujeto(sujeto) == "70922320A"

    def test_otro_certificado_tiene_otro_nif(self):
        sujeto = cades.sujeto_del_certificado(der_de_un_pem("certificado_de_otro.pem"))
        assert cades.nif_del_sujeto(sujeto) == "12345678Z"

    def test_el_nif_tambien_se_busca_en_el_nombre_si_no_esta_en_su_sitio(self):
        """Hay certificados antiguos que ponen el NIF en el nombre y no en el campo oficial."""
        assert cades.nif_del_sujeto({"CN": "PEREZ VELASCO DAVID 70922320A"}) == "70922320A"
        assert cades.nif_del_sujeto({"CN": "EMPRESA AGRICOLA SL B12345678"}) == "B12345678"

    def test_si_no_dice_su_nif_se_devuelve_vacio(self):
        """Vacío es «no lo sé», y eso **no** es «es otro». La diferencia decide si se rechaza."""
        assert cades.nif_del_sujeto({"CN": "UN AGRICULTOR"}) == ""
        assert cades.nif_del_sujeto({}) == ""

    def test_saca_la_validez_del_certificado(self):
        validez = cades.validez_del_certificado(der_de_un_pem("certificado.pem"))
        assert validez is not None
        desde, hasta = validez
        assert desde.startswith("20") and hasta.startswith("20")
        assert desde < hasta

    def test_saca_la_clave_publica(self):
        modulo, exponente = cades.clave_publica_rsa(der_de_un_pem("certificado.pem"))
        assert modulo.bit_length() == 2048
        assert exponente == 65537

    def test_de_un_certificado_de_curva_no_saca_clave_rsa(self):
        """Y eso es lo que hace que una firma de curva se diga «no comprobada» y no «mala»."""
        assert cades.clave_publica_rsa(der_de_un_pem("certificado_curva.pem")) is None

    def test_saca_el_numero_de_serie(self):
        serie = cades.numero_de_serie_del_certificado(der_de_un_pem("certificado.pem"))
        assert len(serie) == 40  # 20 bytes en hexadecimal
        assert serie.upper() == serie


# --------------------------------------------------------------------------
# Una firma de verdad: los tres finales posibles
# --------------------------------------------------------------------------


class TestUnaFirmaDeVerdad:
    def test_una_firma_buena_se_comprueba(self, contenido):
        resultado = cades.verificar(fichero("firma_destacada.p7s"), contenido)
        assert resultado.estado == cades.ESTADO_BIEN
        assert resultado.vale is True
        assert resultado.esta_tocado is False
        assert resultado.resumen_coincide is True
        assert resultado.aritmetica_correcta is True
        assert resultado.algoritmo_de_resumen == "sha256"
        assert resultado.firmado_en and resultado.firmado_en.startswith("20")

    def test_y_dice_de_quien_es(self, contenido):
        resultado = cades.verificar(fichero("firma_destacada.p7s"), contenido)
        assert resultado.firmante_nif == "70922320A"
        assert resultado.firmante_nombre == "PEREZ VELASCO DAVID"

    def test_y_dice_si_el_certificado_estaba_en_vigor(self, contenido):
        resultado = cades.verificar(fichero("firma_destacada.p7s"), contenido)
        assert resultado.vigente_al_firmar is True

    def test_no_lleva_el_cuaderno_dentro(self, contenido):
        """La firma de AutoFirma es «destacada»: el fichero de firma no lleva el cuaderno."""
        resultado = cades.verificar(fichero("firma_destacada.p7s"), contenido)
        assert resultado.lleva_el_contenido_dentro is False

    def test_la_firma_adjunta_si_lo_lleva_y_tambien_vale(self, contenido):
        resultado = cades.verificar(fichero("firma_adjunta.p7s"), contenido)
        assert resultado.estado == cades.ESTADO_BIEN
        assert resultado.lleva_el_contenido_dentro is True
        assert resultado.el_contenido_adjunto_es_el_nuestro is True

    def test_la_adjunta_vale_sin_darle_el_cuaderno(self):
        """Si el cuaderno va dentro, no hace falta que se lo den."""
        resultado = cades.verificar(fichero("firma_adjunta.p7s"))
        assert resultado.estado == cades.ESTADO_BIEN


class TestCuandoLaFirmaNoEsDeEsteCuaderno:
    """El final que se rechaza. Aquí no hay duda: alguien ha tocado algo."""

    def test_una_firma_buena_de_otro_cuaderno_no_vale(self, cambiado):
        resultado = cades.verificar(fichero("firma_destacada.p7s"), cambiado)
        assert resultado.esta_tocado is True
        assert resultado.resumen_coincide is False
        assert "otro cuaderno" in resultado.motivo

    def test_cambiarle_un_byte_a_la_firma_la_tira(self, contenido):
        """Cambiar un solo byte de la firma tiene que notarse. Si no, no estaría comprobando nada."""
        buena = bytearray(fichero("firma_destacada.p7s"))
        buena[-10] ^= 0xFF
        resultado = cades.verificar(bytes(buena), contenido)
        assert resultado.esta_tocado is True
        assert resultado.aritmetica_correcta is False

    def test_una_firma_adjunta_de_otro_cuaderno_no_vale(self, cambiado):
        resultado = cades.verificar(fichero("firma_adjunta.p7s"), cambiado)
        assert resultado.esta_tocado is True
        assert resultado.el_contenido_adjunto_es_el_nuestro is False
        assert "no es el cuaderno que hay ahora" in resultado.motivo

    def test_una_firma_con_sha1_no_se_admite(self, contenido):
        """Se sabe leer, pero SHA-1 está roto: darla por buena sería lo peor que se puede hacer."""
        resultado = cades.verificar(fichero("firma_sha1.p7s"), contenido)
        assert resultado.esta_tocado is True
        assert "SHA-1" in resultado.motivo

    def test_darle_otro_cuaderno_del_mismo_tamano_tambien_se_nota(self, contenido):
        """Dos ficheros del mismo tamaño pero distintos: el resumen los distingue."""
        otro = bytearray(contenido)
        otro[-2] = ord("X") if otro[-2] != ord("X") else ord("Y")
        assert len(bytes(otro)) == len(contenido)
        resultado = cades.verificar(fichero("firma_destacada.p7s"), bytes(otro))
        assert resultado.esta_tocado is True


class TestCuandoNoSePuedeComprobar:
    """El final que **no** se rechaza. Esta frontera es la que más importa de todo el módulo."""

    def test_una_firma_de_curva_no_se_dice_que_este_mal(self, contenido):
        """No saber leer una firma no es lo mismo que saber que está mal.

        Decir «no vale» aquí sería llamar mentiroso a un agricultor por tener un certificado
        que este programa todavía no sabe leer.
        """
        resultado = cades.verificar(fichero("firma_curva.p7s"), contenido)
        assert resultado.estado == cades.ESTADO_NO_COMPROBADA
        assert resultado.esta_tocado is False
        assert resultado.vale is False
        assert "curva elíptica" in resultado.motivo
        assert "No quiere decir que no valga" in resultado.motivo

    def test_sin_el_cuaderno_no_se_puede_comprobar_una_firma_destacada(self):
        resultado = cades.verificar(fichero("firma_destacada.p7s"))
        assert resultado.estado == cades.ESTADO_NO_COMPROBADA
        assert "hace falta darle el cuaderno" in resultado.motivo

    def test_un_fichero_que_no_es_una_firma(self, contenido):
        resultado = cades.verificar(b"esto no es una firma, es texto", contenido)
        assert resultado.estado == cades.ESTADO_NO_COMPROBADA
        assert "no parece un fichero de firma" in resultado.motivo

    def test_sin_fichero(self, contenido):
        resultado = cades.verificar(b"", contenido)
        assert resultado.estado == cades.ESTADO_NO_COMPROBADA
        assert "no hay fichero" in resultado.motivo

    def test_un_base64_que_no_se_puede_leer(self):
        resultado = cades.verificar_base64("esto no es base64!!!", b"lo que sea")
        assert resultado.estado == cades.ESTADO_NO_COMPROBADA

    def test_el_firmante_se_dice_incluso_cuando_no_se_puede_comprobar(self, contenido):
        """Saber quién firma sirve aunque no se pueda comprobar la firma: es un dato útil."""
        resultado = cades.verificar(fichero("firma_curva.p7s"), contenido)
        assert resultado.firmante_nif == "70922320A"


class TestLaFirmaDeOtroCertificado:
    """Una firma perfectamente buena de otro agricultor.

    Esto **se comprueba bien** (la firma es válida y es de ese cuaderno), así que el resultado
    dice `bien`. Lo que hace falta es que diga **de quién es**, para que quien llama pueda
    compararlo con el agricultor que ha entrado. Si no dijera de quién es, no habría forma de
    darse cuenta.
    """

    def test_la_firma_es_valida(self, contenido):
        resultado = cades.verificar(fichero("firma_de_otro.p7s"), contenido)
        assert resultado.estado == cades.ESTADO_BIEN

    def test_pero_dice_que_es_de_otro(self, contenido):
        resultado = cades.verificar(fichero("firma_de_otro.p7s"), contenido)
        assert resultado.firmante_nif == "12345678Z"
        assert resultado.firmante_nombre == "OTRO AGRICULTOR"

    def test_y_el_de_la_buena_es_el_del_agricultor(self, contenido):
        resultado = cades.verificar(fichero("firma_destacada.p7s"), contenido)
        assert resultado.firmante_nif == "70922320A"


# --------------------------------------------------------------------------
# Lo que NO se comprueba, declarado
# --------------------------------------------------------------------------


class TestLoQueNoSeComprueba:
    def test_la_cadena_de_confianza_no_se_comprueba_y_se_dice(self, contenido):
        """Sin la lista de autoridades raíz no se puede saber si el certificado es de fiar.

        Es el dato que más se mira, así que es donde menos se puede improvisar: el campo se
        queda en falso y se explica por qué, en vez de dejarlo en un «sí» optimista.
        """
        resultado = cades.verificar(fichero("firma_destacada.p7s"), contenido)
        assert resultado.cadena_de_confianza_comprobada is False
        assert any("cadena de confianza" in texto for texto in resultado.no_comprobado)

    def test_se_dice_en_los_documentos_del_programa(self):
        """Y no solo en el código: en el texto del módulo, que es lo que lee quien lo mantiene."""
        texto = (Path(cades.__file__)).read_text(encoding="utf-8")
        assert "cadena de confianza" in texto
        assert "No comprueba la cadena de confianza" in texto

    def test_el_resultado_se_puede_convertir_en_diccionario(self, contenido):
        """Es lo que se guarda en la auditoría: tiene que poder guardarse tal cual."""
        datos = cades.verificar(fichero("firma_destacada.p7s"), contenido).como_dict()
        assert datos["vale"] is True
        assert datos["cadena_de_confianza_comprobada"] is False
        assert datos["firmante_nif"] == "70922320A"
        # Y todo tiene que ser guardable en JSON, sin objetos raros.
        import json

        assert json.loads(json.dumps(datos)) == datos


class TestLoQueSeLeCuentaAlAgricultor:
    """Sin tecnicismos, y diciéndole qué puede hacer. Es la regla 3.1 del proyecto."""
    def test_la_firma_buena_se_cuenta_en_cristiano(self, contenido):
        texto = cades.resumen_para_el_agricultor(
            cades.verificar(fichero("firma_destacada.p7s"), contenido)
        )
        assert "comprobada" in texto

    def test_la_firma_que_no_es_del_cuaderno_le_dice_que_vuelva_a_firmar(self, cambiado):
        texto = cades.resumen_para_el_agricultor(
            cades.verificar(fichero("firma_destacada.p7s"), cambiado)
        )
        assert "Vuelve a firmarlo" in texto

    def test_la_que_no_se_pudo_comprobar_le_quita_la_culpa(self, contenido):
        texto = cades.resumen_para_el_agricultor(
            cades.verificar(fichero("firma_curva.p7s"), contenido)
        )
        assert "No es culpa tuya" in texto
        assert "se ha guardado igual" in texto

    @pytest.mark.parametrize(
        "caso",
        [
            ("firma_destacada.p7s", "cuaderno_de_prueba.txt"),
            ("firma_destacada.p7s", "cuaderno_cambiado.txt"),
            ("firma_curva.p7s", "cuaderno_de_prueba.txt"),
            ("firma_sha1.p7s", "cuaderno_de_prueba.txt"),
        ],
    )
    def test_ningun_mensaje_lleva_jerga(self, caso):
        """Un agricultor no puede arreglar un ASN.1, pero sí puede volver a firmar."""
        texto = cades.resumen_para_el_agricultor(
            cades.verificar(fichero(caso[0]), fichero(caso[1]))
        )
        for palabra in (
            "ASN.1",
            "CMS",
            "criptogr",
            "hash",
            "PKCS",
            "SHA-256",
            "SHA-1",
            "certificado digital",
            "algoritmo",
        ):
            assert palabra.lower() not in texto.lower(), f"«{palabra}» en: {texto}"


# --------------------------------------------------------------------------
# La comprobación, dentro del flujo de firmar
#
# Aquí se prueba la fontanería: que el servidor pase el cuaderno de verdad al comprobador, y que
# haga lo correcto con cada uno de los tres finales. El comprobador en sí ya está probado arriba
# contra firmas de verdad, así que aquí se sustituye por uno de mentira: lo que se mira es qué
# hace el servidor con la respuesta.
# --------------------------------------------------------------------------

CABECERAS_CERTIFICADO = {
    "X-SSL-Client-Subject": (
        "CN=PEREZ VELASCO DAVID,SN=PEREZ VELASCO,G=DAVID,SERIALNUMBER=70922320A,C=ES"
    ),
    "X-SSL-Client-Verify": "SUCCESS",
}


@pytest.fixture
def con_certificado(monkeypatch):
    monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")


def _resultado(estado, **extra) -> cades.Resultado:
    """Un resultado del comprobador, hecho a mano para probar la fontanería.

    Se le pone la misma declaración que pone el comprobador de verdad (que la cadena de confianza
    no se comprueba): si el de mentira fuera más optimista que el real, este test daría por
    bueno un resultado que el programa nunca produce.
    """
    base = {
        "estado": estado,
        "motivo": "motivo tecnico",
        "explicacion": "explicación en cristiano",
        "firmante_nif": "70922320A",
        "firmante_nombre": "PEREZ VELASCO DAVID",
        "cadena_de_confianza_comprobada": False,
        "no_comprobado": ["la cadena de confianza"],
    }
    base.update(extra)
    return cades.Resultado(**base)


class TestLaComprobacionEnElFlujoDeFirmar:
    def _preparado(self, cliente, cuenta, con_certificado):
        cabeceras = {**cuenta["cabeceras"], **CABECERAS_CERTIFICADO}
        return cliente.get("/api/firmas/preparar", headers=cabeceras).json(), cabeceras

    def test_un_fichero_que_no_es_una_firma_se_guarda_pero_marcado(self, cliente, cuenta, con_certificado):
        """No comprobar algo no es motivo para dejar a un agricultor sin firmar.

        Ojo con esto, que es una decisión y no un descuido: antes se guardaba cualquier cosa sin
        mirarla. Ahora se mira, y si no se entiende **se dice** en vez de callarlo. Pero no se
        rechaza: rechazar por no saber leer un fichero dejaría al agricultor sin poder firmar.
        """
        preparado, cabeceras = self._preparado(cliente, cuenta, con_certificado)
        respuesta = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
                "contenido": base64.b64encode(b"esto no es una firma").decode(),
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["verificada_criptograficamente"] is False
        assert datos["nota_verificacion"]

    def test_a_la_comprobacion_se_le_pasa_el_cuaderno_de_verdad(self, cliente, cuenta, con_certificado, monkeypatch):
        """Si se le pasara otra cosa, comprobaría el documento equivocado y no serviría de nada."""
        visto = {}

        def comprobar(texto, contenido):
            visto["contenido"] = contenido
            return _resultado(cades.ESTADO_BIEN)

        monkeypatch.setattr(cades, "verificar_base64", comprobar)
        preparado, cabeceras = self._preparado(cliente, cuenta, con_certificado)
        fichero_del_cuaderno = cliente.get("/api/firmas/fichero", headers=cabeceras).text

        cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
                "contenido": base64.b64encode(b"da igual").decode(),
            },
        )
        assert visto["contenido"].decode("utf-8") == fichero_del_cuaderno

    def test_una_firma_buena_queda_como_comprobada(self, cliente, cuenta, con_certificado, monkeypatch):
        monkeypatch.setattr(
            cades, "verificar_base64", lambda texto, contenido: _resultado(cades.ESTADO_BIEN)
        )
        preparado, cabeceras = self._preparado(cliente, cuenta, con_certificado)
        datos = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
                "contenido": base64.b64encode(b"da igual").decode(),
            },
        ).json()
        assert datos["verificada_criptograficamente"] is True

    def test_una_firma_tocada_se_rechaza(self, cliente, cuenta, con_certificado, monkeypatch):
        """Aquí no hay duda: guardar esto sería dejar creer que el cuaderno está respaldado."""
        monkeypatch.setattr(
            cades, "verificar_base64", lambda texto, contenido: _resultado(cades.ESTADO_MAL)
        )
        preparado, cabeceras = self._preparado(cliente, cuenta, con_certificado)
        respuesta = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
                "contenido": base64.b64encode(b"da igual").decode(),
            },
        )
        assert respuesta.status_code == 422
        assert "no es de este cuaderno" in respuesta.json()["detail"]
        # Y se le dice qué puede hacer, no solo que no.
        assert "Vuelve a firmarlo" in respuesta.json()["detail"]
        # Y no ha quedado ninguna firma guardada a medias.
        assert cliente.get(
            "/api/firmas", headers={**cuenta["cabeceras"], **CABECERAS_CERTIFICADO}
        ).json() == []

    def test_una_firma_de_otro_agricultor_se_rechaza(self, cliente, cuenta, con_certificado, monkeypatch):
        """Una firma buena de otro certificado no es la firma de este agricultor."""
        monkeypatch.setattr(
            cades,
            "verificar_base64",
            lambda texto, contenido: _resultado(
                cades.ESTADO_BIEN, firmante_nif="12345678Z", firmante_nombre="OTRO AGRICULTOR"
            ),
        )
        preparado, cabeceras = self._preparado(cliente, cuenta, con_certificado)
        respuesta = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
                "contenido": base64.b64encode(b"da igual").decode(),
            },
        )
        assert respuesta.status_code == 422
        assert "OTRO AGRICULTOR" in respuesta.json()["detail"]
        assert "70922320A" in respuesta.json()["detail"]

    def test_si_la_firma_no_dice_su_nif_no_se_rechaza(self, cliente, cuenta, con_certificado, monkeypatch):
        """No saber de quién es no es lo mismo que saber que es de otro."""
        monkeypatch.setattr(
            cades, "verificar_base64", lambda texto, contenido: _resultado(cades.ESTADO_BIEN, firmante_nif="")
        )
        preparado, cabeceras = self._preparado(cliente, cuenta, con_certificado)
        respuesta = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
                "contenido": base64.b64encode(b"da igual").decode(),
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["verificada_criptograficamente"] is True

    def test_sin_fichero_de_firma_se_guarda_y_se_dice_que_no_habia_nada_que_mirar(
        self, cliente, cuenta, con_certificado
    ):
        """El fichero de firma es opcional: se puede registrar quién firmó y qué se firmó."""
        preparado, cabeceras = self._preparado(cliente, cuenta, con_certificado)
        datos = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
            },
        ).json()
        assert datos["verificada_criptograficamente"] is False
        assert "no se ha mandado" in datos["nota_verificacion"]

    def test_lo_que_no_se_pudo_comprobar_se_cuenta_sin_jerga(self, cliente, cuenta, con_certificado, monkeypatch):
        """La nota llega a la pantalla del agricultor: tiene que poder leerla."""
        monkeypatch.setattr(
            cades,
            "verificar_base64",
            lambda texto, contenido: _resultado(
                cades.ESTADO_NO_COMPROBADA,
                motivo="la firma es de curva elíptica con SHA-256",
                explicacion=cades.EXPLICACION_CURVA,
            ),
        )
        preparado, cabeceras = self._preparado(cliente, cuenta, con_certificado)
        datos = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
                "contenido": base64.b64encode(b"da igual").decode(),
            },
        ).json()
        assert datos["verificada_criptograficamente"] is False
        assert datos["nota_verificacion"] == cades.EXPLICACION_CURVA
        for palabra in ("SHA-256", "curva elíptica", "criptogr"):
            assert palabra not in datos["nota_verificacion"]

    def test_queda_apuntado_que_se_miro_y_que_no(self, cliente, cuenta, con_certificado, monkeypatch, db_sesion):
        """La auditoría guarda la comprobación entera, para poder reconstruirla meses después."""
        from sqlalchemy import select

        from app import models

        monkeypatch.setattr(
            cades, "verificar_base64", lambda texto, contenido: _resultado(cades.ESTADO_BIEN)
        )
        preparado, cabeceras = self._preparado(cliente, cuenta, con_certificado)
        respuesta = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
                "contenido": base64.b64encode(b"da igual").decode(),
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        # Se cierra la lectura que tuviera abierta esta sesión: si no, seguiría viendo la base
        # de datos como estaba antes de la petición y parecería que no se ha apuntado nada.
        db_sesion.rollback()
        apunte = db_sesion.scalars(
            select(models.Auditoria).where(models.Auditoria.accion == "firmar")
        ).first()
        assert apunte is not None
        verificacion = apunte.datos["verificacion"]
        assert verificacion["vale"] is True
        # Y queda escrito lo que NO se comprobó: la cadena de confianza.
        assert verificacion["cadena_de_confianza_comprobada"] is False
        assert verificacion["no_comprobado"]
