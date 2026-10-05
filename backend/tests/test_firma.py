"""Tests de la firma del cuaderno.

Lo que se comprueba aquí, por orden de importancia:

1. **Que la huella sea estable.** Si el mismo cuaderno diera dos huellas distintas, la
   firma no valdría para nada: parecería manipulado sin que nadie lo hubiera tocado.
2. **Que se note cuando algo cambia después de firmar.** Es lo único que de verdad
   protege el cuaderno, y lo que mira una inspección.
3. **Que no se pueda firmar sin certificado.** Una firma que no dice de quién es no es
   una firma.
4. Que la orden de AutoFirma sea la del manual oficial, no una inventada.
"""

from __future__ import annotations

import base64
import datetime as dt

import pytest

from app import firma as firma_util

CABECERAS_CERTIFICADO = {
    # El mismo NIF con el que se da de alta la finca en las pruebas.
    "X-SSL-Client-Subject": (
        "CN=PEREZ VELASCO DAVID,SN=PEREZ VELASCO,G=DAVID,SERIALNUMBER=70922320A,C=ES"
    ),
    "X-SSL-Client-Verify": "SUCCESS",
}


@pytest.fixture
def con_certificado(monkeypatch):
    monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")


class FirmaFalsa:
    """Una firma con una huella concreta, para probar los tres estados."""

    def __init__(self, huella: str):
        self.huella = huella


# --------------------------------------------------------------------------
# Escribir los datos siempre igual
# --------------------------------------------------------------------------


class TestValoresEstables:
    def test_lo_que_no_hay_es_vacio(self):
        assert firma_util.valor_para_firmar(None) == ""

    def test_si_y_no_en_castellano(self):
        assert firma_util.valor_para_firmar(True) == "si"
        assert firma_util.valor_para_firmar(False) == "no"

    def test_la_fecha_en_ordenador_pero_sin_hora(self):
        assert firma_util.valor_para_firmar(dt.date(2026, 5, 22)) == "2026-05-22"

    def test_los_numeros_sin_ceros_de_adorno(self):
        """Si el mismo número saliera un día como "0.8000000001", la huella cambiaría."""
        assert firma_util.valor_para_firmar(0.8) == "0.8"
        assert firma_util.valor_para_firmar(2.430000) == "2.43"
        assert firma_util.valor_para_firmar(2) == "2"
        assert firma_util.valor_para_firmar(0.0) == "0"

    def test_una_lista_se_une(self):
        assert firma_util.valor_para_firmar(["rotacion", "trampeo"]) == "rotacion, trampeo"

    def test_el_texto_se_limpia(self):
        assert firma_util.valor_para_firmar("  El Prado  ") == "El Prado"


class TestBloque:
    def test_los_campos_van_ordenados(self):
        """El orden en que se escriban en el código no puede cambiar el fichero."""
        uno = firma_util.bloque("X", {"b": 2, "a": 1})
        otro = firma_util.bloque("X", {"a": 1, "b": 2})
        assert uno == otro
        assert uno.index("a: 1") < uno.index("b: 2")

    def test_los_campos_vacios_salen_pero_vacios(self):
        texto = firma_util.bloque("X", {"a": None})
        assert "a: " in texto


class TestHuella:
    def test_el_mismo_texto_da_la_misma_huella(self):
        assert firma_util.huella("hola") == firma_util.huella("hola")

    def test_un_caracter_distinto_cambia_la_huella(self):
        assert firma_util.huella("hola") != firma_util.huella("hola ")

    def test_la_huella_tiene_la_forma_esperada(self):
        resultado = firma_util.huella("hola")
        assert len(resultado) == 64
        assert all(caracter in "0123456789abcdef" for caracter in resultado)

    def test_el_mismo_cuaderno_da_siempre_la_misma_huella(self):
        """ESTE ES EL TEST QUE SOSTIENE TODO LO DEMÁS."""
        argumentos = dict(
            explotacion={"Nombre": "David", "NIF": "70922320A"},
            campana={"Año": 2026},
            tratamientos=[{"Fecha": dt.date(2026, 5, 1), "Dosis": 0.8}],
        )
        primera = firma_util.huella(firma_util.texto_del_cuaderno(**argumentos))
        segunda = firma_util.huella(firma_util.texto_del_cuaderno(**argumentos))
        assert primera == segunda

    def test_cambiar_un_dato_cambia_la_huella(self):
        base = dict(explotacion={"Nombre": "David"}, campana={"Año": 2026})
        una = firma_util.huella(
            firma_util.texto_del_cuaderno(**base, tratamientos=[{"Dosis": 0.8}])
        )
        otra = firma_util.huella(
            firma_util.texto_del_cuaderno(**base, tratamientos=[{"Dosis": 0.9}])
        )
        assert una != otra

    def test_anadir_un_apunte_cambia_la_huella(self):
        base = dict(explotacion={"Nombre": "David"}, campana={"Año": 2026})
        una = firma_util.huella(firma_util.texto_del_cuaderno(**base, tratamientos=[]))
        otra = firma_util.huella(
            firma_util.texto_del_cuaderno(**base, tratamientos=[{"Dosis": 0.8}])
        )
        assert una != otra


class TestElFicheroDelCuaderno:
    def test_lleva_su_cabecera_y_su_version(self):
        texto = firma_util.texto_del_cuaderno(
            explotacion={"Nombre": "David"}, campana={"Año": 2026}
        )
        assert "CUADERNO DE CAMPO" in texto
        assert f"version: {firma_util.VERSION_CANONICA}" in texto

    def test_dice_cuantos_apuntes_hay_de_cada_cosa(self):
        texto = firma_util.texto_del_cuaderno(
            explotacion={"Nombre": "David"},
            campana={"Año": 2026},
            tratamientos=[{"Dosis": 0.8}, {"Dosis": 0.9}],
            fertilizaciones=[{"Kilos": 300}],
            labores=[],
        )
        assert "PRODUCTOS APLICADOS (2)" in texto
        assert "ABONOS (1)" in texto
        assert "LABORES (0)" in texto

    def test_cada_apunte_va_numerado(self):
        """Si se reordena el cuaderno, el fichero cambia: y eso también es un cambio."""
        texto = firma_util.texto_del_cuaderno(
            explotacion={"Nombre": "David"},
            campana={"Año": 2026},
            tratamientos=[{"Producto": "Uno"}, {"Producto": "Dos"}],
        )
        assert "PRODUCTO APLICADO 1" in texto
        assert "PRODUCTO APLICADO 2" in texto

    def test_se_lee_a_simple_vista(self):
        """El fichero lo puede abrir una persona: las claves van en castellano."""
        texto = firma_util.texto_del_cuaderno(
            explotacion={"Nombre": "David", "NIF": "70922320A"},
            campana={"Año": 2026},
        )
        assert "Nombre: David" in texto
        assert "NIF: 70922320A" in texto

    def test_un_solo_apunte_tambien_se_puede_firmar(self):
        texto = firma_util.texto_de_un_registro("PRODUCTO APLICADO", {"Dosis": 0.8})
        assert "CUADERNO DE CAMPO" in texto
        assert "== PRODUCTO APLICADO" in texto
        assert "Dosis: 0.8" in texto


class TestElComandoDeAutoFirma:
    """Sacado de la sección 6 del manual oficial, no inventado."""

    def test_en_windows(self):
        comando = firma_util.comando_autofirma("cuaderno_2026.txt", "windows")
        assert "AutoFirmaCommandLine" in comando
        assert "sign" in comando
        assert '-i "cuaderno_2026.txt"' in comando
        assert '-o "cuaderno_2026.txt.csig"' in comando

    def test_en_linux(self):
        comando = firma_util.comando_autofirma("cuaderno_2026.txt", "linux")
        assert "/usr/bin/AutoFirma" in comando

    def test_en_mac(self):
        comando = firma_util.comando_autofirma("cuaderno_2026.txt", "mac")
        assert "AutoFirma.app" in comando

    def test_el_formato_y_el_algoritmo(self):
        comando = firma_util.comando_autofirma("x.txt")
        assert "-format cades" in comando
        assert f"-algorithm {firma_util.ALGORITMO}" in comando

    def test_un_sistema_desconocido_no_revienta(self):
        assert "AutoFirmaCommandLine" in firma_util.comando_autofirma("x.txt", "plan9")


class TestLosTresEstados:
    def test_sin_firmar(self):
        assert firma_util.estado_de_la_firma(None, "abc") == firma_util.ESTADO_SIN_FIRMAR

    def test_firmado_y_sin_cambios(self):
        firma = FirmaFalsa("abc")
        assert firma_util.estado_de_la_firma(firma, "abc") == firma_util.ESTADO_FIRMADO

    def test_cambiado_despues_de_firmar(self):
        """Se firmó "abc" y ahora el cuaderno produce "abd": alguien lo ha tocado."""
        firma = FirmaFalsa("abc")
        assert firma_util.estado_de_la_firma(firma, "abd") == firma_util.ESTADO_CAMBIADO


# --------------------------------------------------------------------------
# La firma por la API
# --------------------------------------------------------------------------


class TestFirmarPorLaApi:
    def test_hace_falta_entrar(self, cliente, cuenta):
        assert cliente.get("/api/firmas/estado").status_code == 401

    def test_el_estado_sin_firmar(self, cliente, cuenta):
        respuesta = cliente.get("/api/firmas/estado", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["estado"] == "sin_firmar"
        assert datos["firma"] is None
        assert len(datos["huella"]) == 64
        assert datos["mensaje"]
        assert datos["explicacion"]

    def test_sin_certificado_no_se_puede_firmar(self, cliente, cuenta, con_certificado):
        datos = cliente.get("/api/firmas/estado", headers=cuenta["cabeceras"]).json()
        assert datos["puede_firmar"] is False

    def test_con_el_certificado_de_la_finca_si_se_puede(
        self, cliente, cuenta, con_certificado
    ):
        datos = cliente.get(
            "/api/firmas/estado", headers={**cuenta["cabeceras"], **CABECERAS_CERTIFICADO}
        ).json()
        assert datos["puede_firmar"] is True

    def test_el_fichero_se_descarga_con_su_nombre(self, cliente, cuenta):
        respuesta = cliente.get("/api/firmas/fichero", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        assert "cuaderno_" in respuesta.headers["content-disposition"]
        assert "CUADERNO DE CAMPO" in respuesta.text

    def test_preparar_da_el_fichero_la_huella_y_la_orden(self, cliente, cuenta):
        datos = cliente.get("/api/firmas/preparar", headers=cuenta["cabeceras"]).json()
        assert len(datos["huella"]) == 64
        assert datos["nombre_del_fichero"].endswith(".txt")
        assert "AutoFirmaCommandLine" in datos["comando"]
        assert datos["contenido"].startswith("CUADERNO DE CAMPO")
        assert datos["formato"] == "CAdES"

    def test_la_huella_es_la_misma_que_la_del_fichero(self, cliente, cuenta):
        fichero = cliente.get("/api/firmas/fichero", headers=cuenta["cabeceras"]).text
        preparado = cliente.get("/api/firmas/preparar", headers=cuenta["cabeceras"]).json()
        assert firma_util.huella(fichero) == preparado["huella"]

    def test_firmar_sin_certificado_no_se_puede(self, cliente, cuenta, con_certificado):
        preparado = cliente.get("/api/firmas/preparar", headers=cuenta["cabeceras"]).json()
        respuesta = cliente.post(
            "/api/firmas",
            headers=cuenta["cabeceras"],
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
            },
        )
        assert respuesta.status_code == 403
        assert "certificado" in respuesta.json()["detail"].lower()

    def test_firmar_con_el_certificado(self, cliente, cuenta, con_certificado):
        cabeceras = {**cuenta["cabeceras"], **CABECERAS_CERTIFICADO}
        preparado = cliente.get("/api/firmas/preparar", headers=cabeceras).json()
        respuesta = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
                "nombre_del_fichero": preparado["nombre_del_fichero"],
                "contenido": base64.b64encode(b"firma-de-mentira").decode(),
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["firmante_nif"] == "70922320A"
        assert datos["firmante_nombre"] == "PEREZ VELASCO DAVID"
        assert datos["huella"] == preparado["huella"]
        # Honestidad: no se pone a True sin comprobarlo.
        assert datos["verificada_criptograficamente"] is False

    def test_despues_de_firmar_el_estado_dice_que_esta_firmado(
        self, cliente, cuenta, con_certificado
    ):
        cabeceras = {**cuenta["cabeceras"], **CABECERAS_CERTIFICADO}
        preparado = cliente.get("/api/firmas/preparar", headers=cabeceras).json()
        cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
            },
        )
        datos = cliente.get("/api/firmas/estado", headers=cabeceras).json()
        assert datos["estado"] == "firmado"
        assert datos["firma"] is not None
        assert "PEREZ VELASCO DAVID" in datos["mensaje"]

    def test_firmar_una_version_vieja_se_rechaza(self, cliente, cuenta, con_certificado):
        """Firmar algo que ya no es lo que hay sería dejar creer que está respaldado."""
        cabeceras = {**cuenta["cabeceras"], **CABECERAS_CERTIFICADO}
        preparado = cliente.get("/api/firmas/preparar", headers=cabeceras).json()
        respuesta = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": "0" * 64,
            },
        )
        assert respuesta.status_code == 409
        assert "vuelve a descargarlo" in respuesta.json()["detail"].lower()

    def test_algo_que_no_es_una_firma_se_rechaza(self, cliente, cuenta, con_certificado):
        cabeceras = {**cuenta["cabeceras"], **CABECERAS_CERTIFICADO}
        preparado = cliente.get("/api/firmas/preparar", headers=cabeceras).json()
        respuesta = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
                "contenido": "esto no es base64 válido!!!",
            },
        )
        assert respuesta.status_code == 422

    def test_no_se_puede_firmar_cualquier_cosa(self, cliente, cuenta, con_certificado):
        respuesta = cliente.get(
            "/api/firmas/preparar", headers=cuenta["cabeceras"], params={"entidad": "inventado"}
        )
        assert respuesta.status_code == 422


class TestLoQueDeVerdadProtegeAlCuaderno:
    def test_si_se_apunta_algo_despues_de_firmar_el_estado_lo_avisa(
        self, cliente, cuenta, con_certificado, parcela, producto, nuevo_tratamiento
    ):
        """ESTE ES EL TEST QUE JUSTIFICA TODA LA FIRMA.

        Se firma el cuaderno, y después se apunta un producto. La firma ya no vale para
        lo que hay ahora, y el programa tiene que decirlo bien claro. Una firma que ya
        no cuadra es peor que no tener firma, porque parece que el cuaderno está
        respaldado y no lo está.
        """
        cabeceras = {**cuenta["cabeceras"], **CABECERAS_CERTIFICADO}
        preparado = cliente.get("/api/firmas/preparar", headers=cabeceras).json()
        cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
            },
        )
        assert cliente.get("/api/firmas/estado", headers=cabeceras).json()["estado"] == "firmado"

        # Ahora se apunta algo nuevo.
        tratamiento = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        )
        assert tratamiento.status_code == 201, tratamiento.text

        datos = cliente.get("/api/firmas/estado", headers=cabeceras).json()
        assert datos["estado"] == "cambiado_despues_de_firmar", datos["mensaje"]
        assert "vuelve a firmarlo" in datos["mensaje"].lower()

    def test_la_historia_de_las_firmas_se_guarda_entera(
        self, cliente, cuenta, con_certificado
    ):
        """Una firma no se borra: si el cuaderno cambia, quedan las dos."""
        cabeceras = {**cuenta["cabeceras"], **CABECERAS_CERTIFICADO}
        for _ in range(2):
            preparado = cliente.get("/api/firmas/preparar", headers=cabeceras).json()
            cliente.post(
                "/api/firmas",
                headers=cabeceras,
                json={
                    "entidad": "cuaderno",
                    "campana_id": preparado["campana_id"],
                    "huella": preparado["huella"],
                },
            )
        firmas = cliente.get("/api/firmas", headers=cuenta["cabeceras"]).json()
        assert len(firmas) == 2

    def test_un_apunte_suelto_tambien_se_puede_firmar(
        self, cliente, cuenta, con_certificado, nuevo_tratamiento
    ):
        cabeceras = {**cuenta["cabeceras"], **CABECERAS_CERTIFICADO}
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()

        preparado = cliente.get(
            "/api/firmas/preparar",
            headers=cabeceras,
            params={"entidad": "tratamiento", "entidad_id": creado["id"]},
        ).json()
        assert preparado["contenido"].startswith("CUADERNO DE CAMPO")
        assert "PRODUCTO APLICADO" in preparado["contenido"]

        respuesta = cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "tratamiento",
                "entidad_id": creado["id"],
                "huella": preparado["huella"],
            },
        )
        assert respuesta.status_code == 201, respuesta.text

        datos = cliente.get(
            "/api/firmas/estado",
            headers=cabeceras,
            params={"entidad": "tratamiento", "entidad_id": creado["id"]},
        ).json()
        assert datos["estado"] == "firmado"


class TestAislamientoDeLasFirmas:
    def test_no_se_puede_firmar_un_apunte_de_otra_finca(
        self, cliente, cuenta, crear_cuenta, con_certificado, nuevo_tratamiento
    ):
        creado = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        ).json()
        otro = crear_cuenta("otro@ejemplo.test")
        respuesta = cliente.get(
            "/api/firmas/preparar",
            headers=otro["cabeceras"],
            params={"entidad": "tratamiento", "entidad_id": creado["id"]},
        )
        assert respuesta.status_code == 404

    def test_cada_finca_ve_solo_sus_firmas(
        self, cliente, cuenta, crear_cuenta, con_certificado
    ):
        cabeceras = {**cuenta["cabeceras"], **CABECERAS_CERTIFICADO}
        preparado = cliente.get("/api/firmas/preparar", headers=cabeceras).json()
        cliente.post(
            "/api/firmas",
            headers=cabeceras,
            json={
                "entidad": "cuaderno",
                "campana_id": preparado["campana_id"],
                "huella": preparado["huella"],
            },
        )
        otro = crear_cuenta("otro@ejemplo.test")
        assert cliente.get("/api/firmas", headers=otro["cabeceras"]).json() == []
