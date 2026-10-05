"""Tests del certificado digital: leerlo y entrar con él.

Dos cosas se comprueban aquí, y la segunda importa más que la primera:

1. Que se sepa leer un certificado: sacar el NIF, sacar el nombre, y saber si el NIF
   tiene sentido.
2. Que **no se pueda falsificar**. Si el programa se creyera la cabecera que trae el
   nombre del certificado sin más, cualquiera podría mandar
   `X-SSL-Client-Subject: CN=..., SERIALNUMBER=70922320A` y entrar en la finca de otro.
   Es el fallo clásico de confiar en una cabecera que pone el cliente.
"""

from __future__ import annotations

import pytest

from app import certificados

# --------------------------------------------------------------------------
# NIF: DNI, NIE y CIF
# --------------------------------------------------------------------------


class TestNif:
    def test_los_dni_buenos_se_aceptan(self):
        # Letras calculadas con el algoritmo oficial (módulo 23).
        for nif in ("12345678Z", "00000000T", "99999999R", "70922320A"):
            assert certificados.nif_valido(nif), f"{nif} debería valer"

    def test_un_dni_con_la_letra_cambiada_no_cuela(self):
        assert not certificados.nif_valido("12345678A")
        assert not certificados.nif_valido("70922320B")

    def test_los_nie_se_aceptan(self):
        assert certificados.nif_valido("X0000000T")
        assert certificados.nif_valido("Y0000000Z")
        assert certificados.nif_valido("Z0000000M")

    def test_un_nie_con_la_letra_mal_no_cuela(self):
        assert not certificados.nif_valido("X0000000A")

    def test_los_cif_se_aceptan(self):
        # A1234567 -> dígito de control 4. Calculado a mano: se doblan las posiciones
        # impares (1,3,5,7), se suman las pares y el control es lo que falta hasta 10.
        assert certificados.nif_valido("A12345674")
        assert certificados.nif_valido("B12345674")

    def test_un_cif_con_el_digito_mal_no_cuela(self):
        assert not certificados.nif_valido("A12345673")

    def test_una_sociedad_limitada_lleva_digito_no_letra(self):
        """El tipo de organización decide si el control va en cifra o en letra.

        Aceptar las dos formas en todos los casos dejaría pasar NIF mal escritos.
        """
        assert not certificados.nif_valido("A1234567E")

    def test_un_organismo_publico_lleva_letra_no_digito(self):
        # La Q es de organismo público: su control es letra.
        assert not certificados.nif_valido("Q12345674")

    def test_lo_que_no_tiene_forma_de_nif_se_rechaza(self):
        for basura in ("", "hola", "123", "123456789012345", "ABCDEFGHI"):
            assert not certificados.nif_valido(basura), f"{basura!r} no debería valer"

    def test_se_normaliza_al_comparar(self):
        """El NIF del certificado y el que teclea el agricultor tienen que coincidir."""
        assert certificados.normaliza_nif(" 70922320-a ") == "70922320A"
        assert certificados.normaliza_nif("es70922320a") == "70922320A"
        assert certificados.normaliza_nif("VATES-B12345674") == "B12345674"
        assert certificados.nif_valido(" 70922320-a ")

    def test_el_tipo_se_reconoce(self):
        assert certificados.tipo_de_nif("12345678Z") == "dni"
        assert certificados.tipo_de_nif("X0000000T") == "nie"
        assert certificados.tipo_de_nif("A12345674") == "cif"
        assert certificados.tipo_de_nif("nada") is None


# --------------------------------------------------------------------------
# Leer el nombre distinguido
# --------------------------------------------------------------------------


DN_PERSONA_FISICA = (
    "CN=PEREZ VELASCO DAVID,SN=PEREZ VELASCO,G=DAVID,"
    "SERIALNUMBER=70922320A,C=ES"
)
DN_PERSONA_JURIDICA = "CN=EXPLOTACIONES EJEMPLO SL,O=EXPLOTACIONES EJEMPLO SL,SERIALNUMBER=B12345674,C=ES"


class TestNombreDistinguido:
    def test_se_saca_el_nif(self):
        certificado = certificados.certificado_de_dn(DN_PERSONA_FISICA)
        assert certificado is not None
        assert certificado.nif == "70922320A"

    def test_se_saca_el_nombre(self):
        certificado = certificados.certificado_de_dn(DN_PERSONA_FISICA)
        assert certificado.nombre == "PEREZ VELASCO DAVID"

    def test_una_empresa_se_reconoce_como_empresa(self):
        certificado = certificados.certificado_de_dn(DN_PERSONA_JURIDICA)
        assert certificado.nif == "B12345674"
        assert certificado.es_empresa is True
        assert certificado.organizacion == "EXPLOTACIONES EJEMPLO SL"

    def test_una_persona_no_es_empresa(self):
        certificado = certificados.certificado_de_dn(DN_PERSONA_FISICA)
        assert certificado.es_empresa is False

    def test_sin_cn_se_compone_con_el_nombre_y_los_apellidos(self):
        certificado = certificados.certificado_de_dn(
            "G=DAVID,SN=PEREZ VELASCO,SERIALNUMBER=70922320A"
        )
        assert certificado.nombre == "DAVID PEREZ VELASCO"

    def test_se_entienden_las_claves_con_oid(self):
        """Algunos servidores web escriben OID.2.5.4.5 en vez de SERIALNUMBER."""
        certificado = certificados.certificado_de_dn(
            "OID.2.5.4.3=PEREZ VELASCO DAVID,OID.2.5.4.5=70922320A"
        )
        assert certificado.nif == "70922320A"
        assert certificado.nombre == "PEREZ VELASCO DAVID"

    def test_se_entiende_un_apellido_con_coma_dentro(self):
        """ "PEREZ VELASCO, DAVID" va escapado, y partir por todas las comas lo rompe."""
        certificado = certificados.certificado_de_dn(
            "CN=PEREZ VELASCO\\, DAVID,SERIALNUMBER=70922320A"
        )
        assert certificado.nombre == "PEREZ VELASCO, DAVID"
        assert certificado.nif == "70922320A"

    def test_se_entiende_un_valor_entrecomillado(self):
        certificado = certificados.certificado_de_dn(
            'CN="PEREZ VELASCO DAVID",SERIALNUMBER=70922320A'
        )
        assert certificado.nombre == "PEREZ VELASCO DAVID"

    def test_sin_nif_no_se_inventa_ninguno(self):
        """Un certificado sin NIF no vale para entrar, y no se rellena con nada."""
        certificado = certificados.certificado_de_dn("CN=ALGUIEN,C=ES")
        assert certificado is not None
        assert certificado.nif == ""
        assert certificado.nif_valido is False

    def test_un_nif_que_no_es_nif_se_ignora(self):
        certificado = certificados.certificado_de_dn("CN=ALGUIEN,SERIALNUMBER=NOESUNNIF")
        assert certificado.nif == ""

    def test_un_dn_vacio_no_da_certificado(self):
        assert certificados.certificado_de_dn(None) is None
        assert certificados.certificado_de_dn("") is None

    def test_lo_que_sale_es_lo_que_se_enseña(self):
        certificado = certificados.certificado_de_dn(DN_PERSONA_FISICA)
        datos = certificado.como_dict()
        assert datos["nif"] == "70922320A"
        assert datos["nif_valido"] is True
        assert datos["es_empresa"] is False


# --------------------------------------------------------------------------
# De la petición al certificado, y el problema de la cabecera falsificada
# --------------------------------------------------------------------------


class PeticionFalsa:
    """Lo mínimo que `certificado_de_peticion` necesita de una petición."""

    def __init__(self, cabeceras: dict[str, str]):
        self.headers = cabeceras


@pytest.fixture
def sin_confiar(monkeypatch):
    monkeypatch.delenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", raising=False)


@pytest.fixture
def confiando(monkeypatch):
    monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
    monkeypatch.delenv("CUEDIGITAL_CABECERA_CERTIFICADO", raising=False)
    monkeypatch.delenv("CUEDIGITAL_CABECERA_VERIFICACION", raising=False)


class TestLaCabeceraNoSeCreePorDefecto:
    def test_por_defecto_no_se_esta_configurado(self, sin_confiar):
        assert certificados.esta_configurado() is False

    def test_por_defecto_una_cabecera_con_certificado_no_sirve_para_nada(
        self, sin_confiar
    ):
        """ESTE ES EL TEST IMPORTANTE.

        Si el programa se creyera la cabecera sin más, cualquiera que llegara a él
        directamente podría mandar el NIF de otro agricultor y entrar en su finca.
        """
        peticion = PeticionFalsa(
            {
                "X-SSL-Client-Subject": DN_PERSONA_FISICA,
                "X-SSL-Client-Verify": "SUCCESS",
            }
        )
        assert certificados.certificado_de_peticion(peticion) is None

    def test_configurado_si_se_lee(self, confiando):
        peticion = PeticionFalsa(
            {
                "X-SSL-Client-Subject": DN_PERSONA_FISICA,
                "X-SSL-Client-Verify": "SUCCESS",
            }
        )
        certificado = certificados.certificado_de_peticion(peticion)
        assert certificado is not None
        assert certificado.nif == "70922320A"

    def test_si_el_servidor_web_dice_que_el_certificado_no_vale_no_se_entra(
        self, confiando
    ):
        """El nombre puede venir, pero si la validación falló, no se entra."""
        peticion = PeticionFalsa(
            {
                "X-SSL-Client-Subject": DN_PERSONA_FISICA,
                "X-SSL-Client-Verify": "FAILED:unable to verify the first certificate",
            }
        )
        assert certificados.certificado_de_peticion(peticion) is None

    def test_sin_cabecera_no_hay_certificado(self, confiando):
        assert certificados.certificado_de_peticion(PeticionFalsa({})) is None

    def test_los_nombres_de_las_cabeceras_se_pueden_cambiar(self, monkeypatch):
        """Cada servidor web las llama de una forma."""
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        monkeypatch.setenv("CUEDIGITAL_CABECERA_CERTIFICADO", "X-Client-Cert-DN")
        monkeypatch.delenv("CUEDIGITAL_CABECERA_VERIFICACION", raising=False)
        peticion = PeticionFalsa({"X-Client-Cert-DN": DN_PERSONA_FISICA})
        certificado = certificados.certificado_de_peticion(peticion)
        assert certificado is not None
        assert certificado.nif == "70922320A"


# --------------------------------------------------------------------------
# Entrar con el certificado, por la API
# --------------------------------------------------------------------------

CABECERAS_CERTIFICADO = {
    "X-SSL-Client-Subject": DN_PERSONA_FISICA,
    "X-SSL-Client-Verify": "SUCCESS",
}


def cabeceras_con_dn(dn: str, verificacion: str = "SUCCESS") -> dict[str, str]:
    return {"X-SSL-Client-Subject": dn, "X-SSL-Client-Verify": verificacion}


class TestEntrarConCertificadoPorLaApi:
    """La cuenta de prueba se da de alta con el NIF 70922320A."""

    def test_sin_configurar_el_programa_no_deja_entrar(self, cliente, monkeypatch):
        monkeypatch.delenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", raising=False)
        respuesta = cliente.post(
            "/api/cuenta/entrar-con-certificado", headers=CABECERAS_CERTIFICADO
        )
        assert respuesta.status_code == 401
        assert "correo y tu clave" in respuesta.json()["detail"]

    def test_configurado_y_con_el_nif_de_la_finca_se_entra(
        self, cliente, cuenta, monkeypatch
    ):
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        respuesta = cliente.post(
            "/api/cuenta/entrar-con-certificado", headers=CABECERAS_CERTIFICADO
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["token"]
        assert datos["explotacion_id"] == cuenta["explotacion_id"]

    def test_configurado_sin_certificado_no_se_entra(self, cliente, cuenta, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        respuesta = cliente.post("/api/cuenta/entrar-con-certificado")
        assert respuesta.status_code == 401

    def test_un_nif_que_no_esta_dado_de_alta_lo_dice_con_salida(
        self, cliente, cuenta, monkeypatch
    ):
        """No basta con decir que no: hay que decir qué hacer."""
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        otro = "CN=OTRO AGRICULTOR,SERIALNUMBER=12345678Z"
        respuesta = cliente.post(
            "/api/cuenta/entrar-con-certificado", headers=cabeceras_con_dn(otro)
        )
        assert respuesta.status_code == 403
        mensaje = respuesta.json()["detail"]
        assert "12345678Z" in mensaje
        assert "correo y tu clave" in mensaje, "no le dice qué hacer"

    def test_un_certificado_con_el_nif_mal_escrito_no_entra(
        self, cliente, cuenta, monkeypatch
    ):
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        malo = "CN=ALGUIEN,SERIALNUMBER=70922320B"
        respuesta = cliente.post(
            "/api/cuenta/entrar-con-certificado", headers=cabeceras_con_dn(malo)
        )
        assert respuesta.status_code == 401
        assert "70922320B" in respuesta.json()["detail"]

    def test_un_certificado_sin_nif_no_entra(self, cliente, cuenta, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        respuesta = cliente.post(
            "/api/cuenta/entrar-con-certificado",
            headers=cabeceras_con_dn("CN=ALGUIEN,C=ES"),
        )
        assert respuesta.status_code == 401

    def test_con_el_certificado_no_validado_por_el_servidor_web_no_se_entra(
        self, cliente, cuenta, monkeypatch
    ):
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        respuesta = cliente.post(
            "/api/cuenta/entrar-con-certificado",
            headers=cabeceras_con_dn(DN_PERSONA_FISICA, verificacion="NONE"),
        )
        assert respuesta.status_code == 401

    def test_queda_apuntado_quien_entro(self, cliente, cuenta, monkeypatch):
        """En el cuaderno tiene que quedar el rastro de por dónde se ha entrado."""
        from sqlalchemy import select

        from app import models
        from app.database import SessionLocal

        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        cliente.post("/api/cuenta/entrar-con-certificado", headers=CABECERAS_CERTIFICADO)

        with SessionLocal() as db:
            apuntes = list(
                db.scalars(
                    select(models.Auditoria).where(
                        models.Auditoria.accion == "entrar_con_certificado"
                    )
                )
            )
        assert apuntes
        assert apuntes[0].datos["nif"] == "70922320A"


class TestEstadoDelCertificado:
    def test_sin_configurar_lo_dice_para_que_no_salga_el_boton(self, cliente, monkeypatch):
        monkeypatch.delenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", raising=False)
        datos = cliente.get("/api/cuenta/certificado/estado").json()
        assert datos["configurado"] is False
        assert datos["hay_certificado"] is False
        assert datos["si_no_se_puede"]

    def test_configurado_y_con_certificado_dice_de_quien_es(self, cliente, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        datos = cliente.get(
            "/api/cuenta/certificado/estado", headers=CABECERAS_CERTIFICADO
        ).json()
        assert datos["configurado"] is True
        assert datos["hay_certificado"] is True
        assert datos["certificado"]["nif"] == "70922320A"
        assert datos["certificado"]["nombre"] == "PEREZ VELASCO DAVID"


class TestVincularCertificado:
    def test_si_el_nif_coincide_se_vincula(self, cliente, cuenta, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        respuesta = cliente.post(
            "/api/cuenta/vincular-certificado",
            headers={**cuenta["cabeceras"], **CABECERAS_CERTIFICADO},
        )
        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["vinculado"] is True
        assert respuesta.json()["mensaje"]

    def test_si_el_nif_no_coincide_no_se_vincula(self, cliente, cuenta, monkeypatch):
        """Vincular el certificado de otro NIF sería dejarle entrar en otra finca."""
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        otro = "CN=OTRO,SERIALNUMBER=12345678Z"
        respuesta = cliente.post(
            "/api/cuenta/vincular-certificado",
            headers={**cuenta["cabeceras"], **cabeceras_con_dn(otro)},
        )
        assert respuesta.status_code == 409
        mensaje = respuesta.json()["detail"]
        assert "12345678Z" in mensaje
        assert "70922320A" in mensaje, "no dice cuál es el de su finca"

    def test_hace_falta_estar_dentro(self, cliente, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        respuesta = cliente.post(
            "/api/cuenta/vincular-certificado", headers=CABECERAS_CERTIFICADO
        )
        assert respuesta.status_code == 401

    def test_sin_certificado_no_hay_nada_que_vincular(self, cliente, cuenta, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        respuesta = cliente.post(
            "/api/cuenta/vincular-certificado", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 401


class TestElNifSeGuardaSiempreIgual:
    """Si el NIF se guardara tal y como se teclea, el certificado no encontraría la finca."""

    def test_un_nif_escrito_con_espacios_y_minusculas_sirve_igual(
        self, cliente, monkeypatch
    ):
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        alta = cliente.post(
            "/api/cuenta/registro",
            json={
                "explotacion": {
                    "nombre": "Otra Finca",
                    "nif": " 12345678-z ",
                    "municipio": "Salamanca",
                    "provincia": "Salamanca",
                },
                "nombre": "Otro",
                "correo": "otro@ejemplo.test",
                "clave": "una-clave-larga",
            },
        )
        assert alta.status_code == 201, alta.text

        # El certificado trae el NIF en mayúsculas y sin espacios: tiene que encontrar
        # la finca igual.
        respuesta = cliente.post(
            "/api/cuenta/entrar-con-certificado",
            headers=cabeceras_con_dn("CN=OTRO,SERIALNUMBER=12345678Z"),
        )
        assert respuesta.status_code == 200, respuesta.text
