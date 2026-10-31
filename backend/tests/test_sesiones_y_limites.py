"""Que una sesión se pueda cerrar de verdad, y que las puertas de entrada tengan tope.

Tres cosas que el piloto no puede dejar sin probar (D06 del encargo del 19/10/2026):

1. **Un vale se puede revocar.** Antes el vale era un texto firmado que valía hasta que
   caducaba, y no había forma de cerrarlo: ni al cambiar la clave, ni al desactivar la
   cuenta. Si a alguien le robaban el móvil, el ladrón seguía dentro un mes.
2. **Las puertas de entrada tienen tope.** Sin tope, un programa puede probar claves en
   serie toda la noche. Se limitan los fallos al entrar, las altas y el ritmo del
   certificado.
3. **El secreto que firma se puede cambiar sin echar a nadie.** Se firma con el nuevo y se
   comprueba también con el anterior, y en producción no se arranca sin secreto largo.

Lo que aquí se prueba es el comportamiento de verdad: se piden vales, se cambian claves y
se llenan los contadores hasta que la puerta contesta «espera».
"""

from __future__ import annotations

import copy
import json
import os
import time
import types

import pytest
from sqlalchemy import select

from app import limites, models, security, textos
from scripts import cambiar_la_clave


def _peticion(host: str):
    """Lo mínimo que `limites` mira de una petición: de dónde viene."""
    return types.SimpleNamespace(client=types.SimpleNamespace(host=host))


def _usuario(db, correo: str) -> models.Usuario:
    usuario = db.scalar(select(models.Usuario).where(models.Usuario.correo == correo))
    assert usuario is not None, f"no está dado de alta {correo}"
    return usuario


def _entrar(cliente, correo: str = "david@ejemplo.test", clave: str = "una-clave-mala"):
    return cliente.post("/api/cuenta/entrar", json={"correo": correo, "clave": clave})


class TestLosValesSeRevocan:
    """Un vale emitido deja de valer en cuanto la cuenta sube su versión."""

    def test_el_vale_vale_y_deja_de_valer_al_subir_la_version(
        self, cliente, cuenta, db_sesion
    ):
        assert cliente.get("/api/mi-finca", headers=cuenta["cabeceras"]).status_code == 200

        usuario = _usuario(db_sesion, "david@ejemplo.test")
        usuario.token_version = (usuario.token_version or 0) + 1
        db_sesion.commit()

        respuesta = cliente.get("/api/mi-finca", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 401, respuesta.text

    def test_al_volver_a_entrar_se_entrega_un_vale_nuevo(self, cliente, cuenta, db_sesion):
        usuario = _usuario(db_sesion, "david@ejemplo.test")
        usuario.token_version = 7
        db_sesion.commit()

        assert cliente.get("/api/mi-finca", headers=cuenta["cabeceras"]).status_code == 401

        respuesta = _entrar(cliente, clave="una-clave-larga-de-verdad")
        assert respuesta.status_code == 200, respuesta.text
        nuevas = {"Authorization": f"Bearer {respuesta.json()['token']}"}
        assert cliente.get("/api/mi-finca", headers=nuevas).status_code == 200

    def test_cambiar_la_clave_cierra_los_vales_que_estaban_abiertos(
        self, cliente, cuenta, monkeypatch
    ):
        assert cliente.get("/api/mi-finca", headers=cuenta["cabeceras"]).status_code == 200

        monkeypatch.setattr(
            "sys.argv",
            [
                "cambiar_la_clave.py",
                "--correo",
                "david@ejemplo.test",
                "--clave",
                "una-clave-nueva-y-larga",
            ],
        )
        assert cambiar_la_clave.main() == 0

        respuesta = cliente.get("/api/mi-finca", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 401, respuesta.text

        # Y con la clave nueva se vuelve a entrar sin problema.
        entrar = _entrar(cliente, clave="una-clave-nueva-y-larga")
        assert entrar.status_code == 200, entrar.text

    def test_un_vale_antiguo_sin_version_cuenta_como_la_cero(self, cliente, cuenta, db_sesion):
        """Los vales emitidos antes de este cambio no llevan `tv`, y valen como la versión 0.

        Si no fuese así, actualizar el programa echaría a todo el mundo de golpe. Y en cuanto
        la cuenta sube a la 1, ese vale viejo deja de valer como cualquier otro.
        """
        usuario = _usuario(db_sesion, "david@ejemplo.test")
        # Se fabrica a mano un vale con el mismo formato de antes de D06: firmado igual,
        # pero **sin** el campo `tv`. Si se usara `crear_token`, ya llevaría `tv: 0` y el
        # test no probaría lo que dice su nombre.
        cuerpo = {
            "uid": usuario.id,
            "eid": usuario.explotacion_id,
            "exp": int(time.time()) + 60,
        }
        carga = security._b64(json.dumps(cuerpo, separators=(",", ":")).encode("utf-8"))
        antiguo = f"{carga}.{security._firmar(carga, security._SECRETOS_EN_MEMORIA[0])}"
        cabeceras = {"Authorization": f"Bearer {antiguo}"}

        assert cliente.get("/api/mi-finca", headers=cabeceras).status_code == 200

        usuario.token_version = 1
        db_sesion.commit()
        assert cliente.get("/api/mi-finca", headers=cabeceras).status_code == 401


class TestLimitesDeEntrada:
    """Al entrar se cuentan los fallos, no los aciertos, y se cuenta por sitio y por cuenta."""

    def test_tras_diez_fallos_se_pide_esperar(self, cliente, cuenta):
        for _ in range(limites.MAXIMO_FALLOS_DE_ENTRADA):
            assert _entrar(cliente).status_code == 401

        respuesta = _entrar(cliente)
        assert respuesta.status_code == 429, respuesta.text
        assert respuesta.headers["Retry-After"] == str(limites.VENTANA_DE_ENTRADA_SEGUNDOS)
        assert respuesta.json()["detail"] == textos.mensaje("demasiados_intentos")

    def test_entrar_bien_no_gasta_el_tope(self, cliente, cuenta):
        for _ in range(limites.MAXIMO_FALLOS_DE_ENTRADA * 2):
            respuesta = _entrar(cliente, clave="una-clave-larga-de-verdad")
            assert respuesta.status_code == 200, respuesta.text

    def test_un_acierto_perdona_la_cuenta_pero_no_la_direccion(self, cliente, cuenta):
        """Nueve fallos, un acierto y un fallo más: la dirección ya está al límite.

        Es la decisión tomada a propósito: quien acierta deja de arrastrar los fallos de
        **su cuenta**, pero la dirección sigue sumando, porque ahí lo que se frena es la
        prueba en serie de claves.
        """
        for _ in range(limites.MAXIMO_FALLOS_DE_ENTRADA - 1):
            assert _entrar(cliente).status_code == 401

        assert _entrar(cliente, clave="una-clave-larga-de-verdad").status_code == 200
        assert _entrar(cliente).status_code == 401
        assert _entrar(cliente).status_code == 429

    def test_una_cuenta_se_corta_aunque_cambie_la_direccion(self):
        for numero in range(limites.MAXIMO_FALLOS_DE_ENTRADA):
            limites.apuntar_fallo_de_entrada(
                _peticion(f"10.0.1.{numero}"), "david@ejemplo.test"
            )

        # Desde otra dirección, la cuenta está igual de bloqueada.
        assert limites.demasiadas_entradas(_peticion("10.0.2.1"), "david@ejemplo.test") is True
        # Y otra cuenta desde otra dirección no paga el pato.
        assert limites.demasiadas_entradas(_peticion("10.0.2.1"), "otra@ejemplo.test") is False

    def test_una_direccion_se_corta_aunque_cambie_la_cuenta(self):
        for numero in range(limites.MAXIMO_FALLOS_DE_ENTRADA):
            limites.apuntar_fallo_de_entrada(
                _peticion("10.0.3.1"), f"cuenta{numero}@ejemplo.test"
            )

        assert limites.demasiadas_entradas(_peticion("10.0.3.1"), "nueva@ejemplo.test") is True
        assert limites.demasiadas_entradas(_peticion("10.0.3.2"), "nueva@ejemplo.test") is False

    def test_un_acierto_limpia_solo_lo_de_su_cuenta(self):
        for numero in range(limites.MAXIMO_FALLOS_DE_ENTRADA):
            limites.apuntar_fallo_de_entrada(
                _peticion(f"10.0.4.{numero}"), "david@ejemplo.test"
            )
        # Un acierto desde una dirección nueva: perdona la cuenta, no la dirección.
        limites.olvidar_fallos_de_entrada(_peticion("10.0.4.1"), "david@ejemplo.test")

        assert limites.demasiadas_entradas(_peticion("10.0.5.1"), "david@ejemplo.test") is False
        for numero in range(limites.MAXIMO_FALLOS_DE_ENTRADA):
            limites.apuntar_fallo_de_entrada(
                _peticion("10.0.6.1"), f"otra{numero}@ejemplo.test"
            )
        limites.olvidar_fallos_de_entrada(_peticion("10.0.6.1"), "otra0@ejemplo.test")
        # La dirección sigue llena aunque la cuenta se haya perdonado.
        assert limites.demasiadas_entradas(_peticion("10.0.6.1"), "libre@ejemplo.test") is True


class TestLimitesDeAlta:
    """Las altas también se cuentan, y se cuentan todas las llamadas, no solo las que acaban en cuenta."""

    def test_tras_diez_altas_se_pide_esperar(self, cliente):
        for numero in range(limites.MAXIMO_ALTAS):
            respuesta = cliente.post(
                "/api/cuenta/registro",
                json={
                    **copy.deepcopy(_DATOS_DE_ALTA),
                    "correo": f"cuenta{numero}@ejemplo.test",
                },
            )
            assert respuesta.status_code == 201, respuesta.text

        respuesta = cliente.post(
            "/api/cuenta/registro",
            json={**copy.deepcopy(_DATOS_DE_ALTA), "correo": "otra@ejemplo.test"},
        )
        assert respuesta.status_code == 429, respuesta.text
        assert respuesta.headers["Retry-After"] == str(limites.VENTANA_DE_ALTAS_SEGUNDOS)
        assert respuesta.json()["detail"] == textos.mensaje("demasiados_intentos")

    def test_una_alta_que_falla_tambien_gasta_el_tope(self, cliente):
        """El correo repetido no crea cuenta, pero la llamada ya se ha apuntado.

        Si no fuese así, el tope se esquivaría con un correo que ya existe.
        """
        primera = cliente.post("/api/cuenta/registro", json=copy.deepcopy(_DATOS_DE_ALTA))
        assert primera.status_code == 201, primera.text

        for _ in range(limites.MAXIMO_ALTAS - 1):
            repetida = cliente.post("/api/cuenta/registro", json=copy.deepcopy(_DATOS_DE_ALTA))
            assert repetida.status_code == 409, repetida.text

        respuesta = cliente.post("/api/cuenta/registro", json=copy.deepcopy(_DATOS_DE_ALTA))
        assert respuesta.status_code == 429, respuesta.text


class TestLimitesDelCertificado:
    """El certificado se limita por ritmo, aunque no haya certificado que mirar."""

    def test_se_corta_despues_de_treinta_llamadas(self, cliente):
        for _ in range(limites.MAXIMO_CERTIFICADOS):
            respuesta = cliente.post("/api/cuenta/entrar-con-certificado")
            assert respuesta.status_code == 401, respuesta.text

        respuesta = cliente.post("/api/cuenta/entrar-con-certificado")
        assert respuesta.status_code == 429, respuesta.text
        assert respuesta.headers["Retry-After"] == str(limites.VENTANA_DE_CERTIFICADO_SEGUNDOS)
        assert respuesta.json()["detail"] == textos.mensaje("demasiados_intentos")

    def test_otra_direccion_no_hereda_el_bloqueo(self):
        for _ in range(limites.MAXIMO_CERTIFICADOS):
            limites.CERTIFICADOS_POR_DIRECCION.apunta(
                limites.clave_de_certificado(_peticion("10.0.7.1"))
            )

        assert (
            limites.CERTIFICADOS_POR_DIRECCION.puede(
                limites.clave_de_certificado(_peticion("10.0.7.1"))
            )
            is False
        )
        assert (
            limites.CERTIFICADOS_POR_DIRECCION.puede(
                limites.clave_de_certificado(_peticion("10.0.7.2"))
            )
            is True
        )


class TestLaRotacionDelSecreto:
    """Se firma con el nuevo y se comprueba también con el anterior, para no echar a nadie."""

    def test_un_vale_firmado_con_el_anterior_sigue_valiendo(
        self, secretos_reversibles
    ):
        viejo = security._SECRETOS_EN_MEMORIA[0]
        vale = security.crear_token(11, 22)
        assert security.leer_token(vale)["uid"] == 11

        os.environ["CUEDIGITAL_SECRETO"] = "el-secreto-nuevo-de-verdad-" + "x" * 40
        os.environ["CUEDIGITAL_SECRETO_ANTERIOR"] = viejo
        security._recargar_secretos_para_pruebas()

        assert security._SECRETOS_EN_MEMORIA[0] != viejo
        leido = security.leer_token(vale)
        assert leido is not None and leido["uid"] == 11

    def test_al_quitar_el_anterior_los_vales_viejos_dejan_de_valer(
        self, secretos_reversibles
    ):
        viejo = security._SECRETOS_EN_MEMORIA[0]
        vale = security.crear_token(11, 22)

        os.environ["CUEDIGITAL_SECRETO"] = "el-secreto-nuevo-de-verdad-" + "x" * 40
        os.environ["CUEDIGITAL_SECRETO_ANTERIOR"] = viejo
        security._recargar_secretos_para_pruebas()
        assert security.leer_token(vale) is not None

        os.environ.pop("CUEDIGITAL_SECRETO_ANTERIOR", None)
        security._recargar_secretos_para_pruebas()
        assert security.leer_token(vale) is None

    def test_el_vale_nuevo_se_firma_con_el_nuevo(self, secretos_reversibles):
        os.environ["CUEDIGITAL_SECRETO"] = "el-secreto-nuevo-de-verdad-" + "x" * 40
        security._recargar_secretos_para_pruebas()

        nuevo = security.crear_token(11, 22)
        assert security.leer_token(nuevo) is not None

        os.environ.pop("CUEDIGITAL_SECRETO_ANTERIOR", None)
        security._recargar_secretos_para_pruebas()
        assert security.leer_token(nuevo) is not None


class TestEnProduccionNoSeArrancaConUnSecretoFlojo:
    """En una instalación de verdad, un secreto corto o ausente para el arranque."""

    def test_sin_secreto_no_arranca(self, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_ENTORNO", "produccion")
        monkeypatch.delenv("CUEDIGITAL_SECRETO", raising=False)
        monkeypatch.delenv("CUEDIGITAL_SECRETO_ANTERIOR", raising=False)

        with pytest.raises(RuntimeError, match="CUEDIGITAL_SECRETO"):
            security.secretos_de_firma()

    def test_un_secreto_corto_no_vale(self, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_ENTORNO", "produccion")
        monkeypatch.setenv("CUEDIGITAL_SECRETO", "corto")
        monkeypatch.delenv("CUEDIGITAL_SECRETO_ANTERIOR", raising=False)

        with pytest.raises(RuntimeError, match="caracteres"):
            security.secretos_de_firma()

    def test_un_anterior_corto_tampoco_vale(self, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_ENTORNO", "produccion")
        monkeypatch.setenv("CUEDIGITAL_SECRETO", "un-secreto-largo-de-verdad-" + "x" * 40)
        monkeypatch.setenv("CUEDIGITAL_SECRETO_ANTERIOR", "corto")

        with pytest.raises(RuntimeError, match="ANTERIOR"):
            security.secretos_de_firma()

    def test_en_la_suite_se_puede_funcionar_sin_secreto(self, monkeypatch):
        monkeypatch.setenv("CUEDIGITAL_ENTORNO", "pruebas")
        monkeypatch.delenv("CUEDIGITAL_SECRETO", raising=False)
        monkeypatch.delenv("CUEDIGITAL_SECRETO_ANTERIOR", raising=False)

        secretos = security.secretos_de_firma()
        assert len(secretos) == 1 and len(secretos[0]) >= security.LONGITUD_MINIMA_DEL_SECRETO


@pytest.fixture
def secretos_reversibles():
    """Deja el entorno y la memoria de secretos como estaban, aunque el test falle.

    **No se usa `monkeypatch` a propósito para esto.** `monkeypatch` deshace las variables de
    entorno al terminar, pero la lista de secretos vive en memoria y ya se habría recargado
    con el secreto del test: el entorno volvería al de siempre y la memoria se quedaría con
    otro, y a partir de ahí cualquier vale emitido en la suite sería ilegible. Se guardan las
    dos cosas y se restauran las dos, en el mismo sitio y en el mismo orden.
    """
    nombres = ("CUEDIGITAL_SECRETO", "CUEDIGITAL_SECRETO_ANTERIOR", "CUEDIGITAL_ENTORNO")
    antes = {nombre: os.environ.get(nombre) for nombre in nombres}
    en_memoria = security._SECRETOS_EN_MEMORIA
    yield
    for nombre, valor in antes.items():
        if valor is None:
            os.environ.pop(nombre, None)
        else:
            os.environ[nombre] = valor
    security._SECRETOS_EN_MEMORIA = en_memoria


_DATOS_DE_ALTA = {
    "explotacion": {
        "nombre": "Finca de prueba",
        "nif": "70922320A",
        "provincia": "Salamanca",
        "municipio": "Peñaranda de Bracamonte",
    },
    "nombre": "Alguien",
    "correo": "alguien@ejemplo.test",
    "clave": "una-clave-larga-de-verdad",
}
