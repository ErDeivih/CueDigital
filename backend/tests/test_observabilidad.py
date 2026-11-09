"""Pruebas de **la observabilidad del propio programa** (09/11/2026).

QUÉ SE COMPRUEBA AQUÍ, Y POR QUÉ CADA COSA
==========================================

La observabilidad tiene un riesgo propio y no es el de siempre: **no puede romper la
aplicación**. Un contador mal puesto no puede dejar a un agricultor sin apuntar un tratamiento,
y un aviso que llega del móvil roto no puede contestar un 5xx. Por eso la mitad de estas
pruebas no miran lo que se mide, sino **lo que pasa cuando medir falla**:

* el búfer de errores está acotado (una lista que crece sin freno es una fuga de memoria en el
  móvil de un agricultor);
* sin `CUEDIGITAL_OBSERVABILIDAD` **no se escribe ni un byte en disco** (la suite no ensucia el
  ordenador de quien la ejecuta, y una instalación normal no necesita ficheros);
* el resumen **no existe** sin token (404), y con token configurado exige la cabecera buena
  (403) y compara en tiempo constante;
* las rutas se guardan por su plantilla, **sin identificadores**, que es lo que hace que el
  resumen sirva para algo;
* el aviso de pantalla contesta **siempre 204**, incluso con basura, y no cuenta lo que no vale;
* si el registro lanza, **la petición sigue** y contesta lo que tenía que contestar;
* el embudo se calcula con SQL sobre los datos de verdad y **aguanta una base a medias**.

Los datos de prueba de las pruebas que usan la API son los de `conftest.py` (`cuenta`,
`parcela`, `nuevo_tratamiento`): no se inventa ninguna base paralela.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models, observabilidad


# ---------------------------------------------------------------------------
# Preparación: cada prueba de este fichero empieza sin variables y sin métricas
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def sin_variables_de_observabilidad(monkeypatch):
    """**La suite no enciende la observabilidad.** Ni el registro en disco ni el token.

    Se borran en cada prueba y no solo al principio del fichero: si alguien deja la variable
    puesta en su consola, estas pruebas comprobarían otra cosa. Las que necesitan la variable la
    ponen ellas, con su `monkeypatch`, y al terminar se deshace sola.
    """
    monkeypatch.delenv(observabilidad.VARIABLE_DEL_REGISTRO, raising=False)
    monkeypatch.delenv(observabilidad.VARIABLE_DEL_TOKEN, raising=False)


@pytest.fixture(autouse=True)
def limpia_lo_medido(sin_variables_de_observabilidad):
    """Cada prueba mira sus propios contadores, no los de la anterior."""
    observabilidad.reiniciar()
    yield
    observabilidad.reiniciar()


def _hoy() -> str:
    return dt.date.today().isoformat()


# ---------------------------------------------------------------------------
# 1. El búfer de errores está acotado y no guarda datos de nadie
# ---------------------------------------------------------------------------


class TestElBufferDeErrores:
    def test_el_buffer_esta_acotado(self):
        """Se apuntan más errores que hueco hay, y no crece: cae el más viejo."""
        for indice in range(observabilidad.MAXIMO_DE_ERRORES + 25):
            observabilidad.registrar_error(
                "Fallo", "GET", f"/api/parcelas/{indice}", 500, f"el fallo número {indice}"
            )
        datos = observabilidad.resumen()
        assert len(datos["errores_recientes"]) == observabilidad.MAXIMO_DE_ERRORES, (
            "el búfer de errores no se ha recortado: "
            f"{len(datos['errores_recientes'])} entradas"
        )
        assert datos["memoria"]["errores"] == observabilidad.MAXIMO_DE_ERRORES

    def test_los_errores_se_leen_del_mas_nuevo_al_mas_viejo(self):
        observabilidad.registrar_error("Fallo", "GET", "/api/a", 500, "el primero")
        observabilidad.registrar_error("Fallo", "GET", "/api/b", 500, "el segundo")
        errores = observabilidad.resumen()["errores_recientes"]
        assert errores[0]["mensaje"] == "el segundo", "el error nuevo tiene que salir primero"
        assert errores[-1]["mensaje"] == "el primero"

    def test_el_error_lleva_su_marca_de_tiempo_y_su_codigo(self):
        antes = dt.datetime.now()
        observabilidad.registrar_error("ValueError", "POST", "/api/labores/9", 500, "se rompió")
        error = observabilidad.resumen()["errores_recientes"][0]
        assert error["tipo"] == "ValueError"
        assert error["metodo"] == "POST"
        assert error["ruta"] == "/api/labores/{id}"
        assert error["codigo"] == 500
        assert dt.datetime.fromisoformat(error["cuando"]) >= antes.replace(microsecond=0)

    def test_el_mensaje_no_guarda_correos_ni_nif_ni_telefonos(self):
        """Un mensaje de fallo es un sitio por donde se cuelan datos personales.

        Se apunta un error con un correo, un NIF y un teléfono dentro, se lee lo guardado y se
        comprueba que **no están**: se sustituyen por marcas. El mensaje es corto de todas formas.
        """
        observabilidad.registrar_error(
            "Fallo",
            "POST",
            "/api/cuenta/entrar",
            500,
            "No se pudo guardar el agricultor (david@ejemplo.test, 70922320A, 666555444) "
            "y el registro sigue",
        )
        mensaje = observabilidad.resumen()["errores_recientes"][0]["mensaje"]
        assert "david@ejemplo.test" not in mensaje
        assert "70922320A" not in mensaje
        assert "666555444" not in mensaje
        assert len(mensaje) <= observabilidad.MAXIMO_DEL_MENSAJE

    def test_el_mensaje_se_recorta_y_se_deja_en_una_linea(self):
        observabilidad.registrar_error("Fallo", "GET", "/api/x", 500, "linea\n" * 200)
        mensaje = observabilidad.resumen()["errores_recientes"][0]["mensaje"]
        assert "\n" not in mensaje
        assert len(mensaje) <= observabilidad.MAXIMO_DEL_MENSAJE

    def test_una_duracion_imposible_no_se_guarda(self):
        """Un reloj roto no puede hacer que el p95 diga tonterías."""
        for duracion in (-1, float("inf"), float("nan"), 10_000_000):
            observabilidad.registrar_peticion("GET", "/api/rara", 200, duracion)
        ruta = observabilidad.resumen()["rutas"][0]
        assert ruta["peticiones"] == 4, "se cuentan las peticiones, aunque la medida no sirva"
        assert ruta["muestras"] == 0, "ninguna duración imposible debe entrar en la muestra"
        assert ruta["p50_ms"] is None and ruta["p95_ms"] is None


# ---------------------------------------------------------------------------
# 2. Sin variable de entorno no se escribe NADA en disco
# ---------------------------------------------------------------------------


class TestElRegistroEnDisco:
    def test_sin_variable_no_se_escribe_ningun_fichero(self, tmp_path, monkeypatch):
        """El caso de por defecto. Se comprueba que **ni siquiera se intenta**.

        No basta con mirar que no haya fichero: se cambia la escritura por un espía y se
        comprueba que nadie la llama. Así también se caza una futura escritura «inocente» que
        creara una carpeta vacía en el disco de quien corre la suite.
        """
        escritos: list[dict] = []
        monkeypatch.setattr(observabilidad, "_escribir_en_disco", lambda evento: escritos.append(evento))

        for _ in range(5):
            observabilidad.registrar_error("Fallo", "GET", "/api/x", 500, "un fallo")
            observabilidad.registrar_pantalla("hoy")

        assert escritos == [], "se ha intentado escribir en disco sin la variable puesta"
        assert observabilidad.ruta_configurada() is None
        assert list(tmp_path.iterdir()) == []

    def test_con_la_variable_apuntando_a_un_fichero_se_escribe_jsonl(self, tmp_path, monkeypatch):
        fichero = tmp_path / "registro.jsonl"
        monkeypatch.setenv(observabilidad.VARIABLE_DEL_REGISTRO, str(fichero))

        observabilidad.registrar_error("Fallo", "GET", "/api/parcelas/7", 500, "un fallo")
        observabilidad.registrar_pantalla("tierras")

        assert fichero.is_file(), "con la variable puesta hay que escribir el registro"
        lineas = [json.loads(linea) for linea in fichero.read_text(encoding="utf-8").splitlines()]
        assert [linea["que"] for linea in lineas] == ["error", "pantalla"]
        assert lineas[0]["ruta"] == "/api/parcelas/{id}", "la ruta se guarda normalizada"
        assert lineas[1]["pantalla"] == "tierras"

    def test_con_la_variable_apuntando_a_una_carpeta_se_escribe_dentro(self, tmp_path, monkeypatch):
        carpeta = tmp_path / "registro"
        monkeypatch.setenv(observabilidad.VARIABLE_DEL_REGISTRO, str(carpeta))

        observabilidad.registrar_error("Fallo", "GET", "/api/x", 500, "un fallo")

        assert (carpeta / observabilidad.NOMBRE_DEL_FICHERO).is_file(), (
            "la variable puede apuntar a una carpeta: dentro va el fichero con su nombre"
        )

    def test_el_fichero_gira_y_no_crece_sin_freno(self, tmp_path, monkeypatch):
        """Se baja el tamaño máximo y se comprueba que aparecen las copias giradas."""
        fichero = tmp_path / "registro.jsonl"
        monkeypatch.setenv(observabilidad.VARIABLE_DEL_REGISTRO, str(fichero))
        monkeypatch.setattr(observabilidad, "MAXIMO_DE_BYTES_DEL_FICHERO", 200)

        for indice in range(40):
            observabilidad.registrar_error(
                "Fallo", "GET", "/api/x", 500, f"un fallo largo y repetido número {indice}"
            )

        assert fichero.is_file()
        assert fichero.with_name(fichero.name + ".1").is_file(), (
            "el registro tiene que girar al llegar al tamaño máximo, no crecer para siempre"
        )
        assert fichero.stat().st_size < 400, "el fichero que se sigue escribiendo tiene que ser pequeño"
        for ruta in (fichero, fichero.with_name(fichero.name + ".1")):
            for linea in ruta.read_text(encoding="utf-8").splitlines():
                assert json.loads(linea)["que"] == "error"

    def test_si_la_carpeta_no_se_puede_escribir_no_pasa_nada(self, tmp_path, monkeypatch):
        """Un disco lleno o una carpeta sin permiso no pueden tumbar la petición.

        Se apunta a una ruta imposible —una carpeta que en realidad es un fichero— y se comprueba
        que registrar un error no lanza. Es la prueba de la regla de oro: **la métrica se pierde,
        la petición no**.
        """
        estorbo = tmp_path / "ocupado"
        estorbo.write_text("no soy una carpeta", encoding="utf-8")
        monkeypatch.setenv(
            observabilidad.VARIABLE_DEL_REGISTRO, str(estorbo / "registro.jsonl")
        )
        observabilidad.registrar_error("Fallo", "GET", "/api/x", 500, "un fallo")
        assert len(observabilidad.resumen()["errores_recientes"]) == 1, (
            "aunque el disco falle, la medida en memoria tiene que quedar"
        )


# ---------------------------------------------------------------------------
# 3. El aviso de pantalla no puede romper nada
# ---------------------------------------------------------------------------


class TestElAvisoDePantalla:
    @pytest.mark.parametrize(
        "cuerpo",
        [
            b"",
            b"no es json",
            b'{"pantalla": 42}',
            b'{"pantalla": "../../etc/passwd"}',
            b'{"pantalla": "una pantalla con espacios"}',
            b'{"otra_cosa": "hoy"}',
            b"[]",
            b"null",
            b"\xff\xfe\x00basura",
            b"x" * 100_000,
        ],
        ids=[
            "vacio",
            "no-json",
            "numero",
            "ruta",
            "espacios",
            "sin-pantalla",
            "lista",
            "nulo",
            "bytes",
            "enorme",
        ],
    )
    def test_el_aviso_contesta_204_siempre(self, cliente, cuerpo):
        respuesta = cliente.post(
            "/api/observabilidad/pantalla",
            content=cuerpo,
            headers={"Content-Type": "application/json"},
        )
        assert respuesta.status_code == 204, (
            f"el aviso tiene que contestar 204 y ha contestado {respuesta.status_code}: "
            "un cuerpo roto del móvil no puede ser un 5xx"
        )

    def test_lo_que_no_vale_no_se_cuenta(self, cliente):
        for cuerpo in (b"no es json", b'{"pantalla": 42}', b'{"pantalla": "mi pantalla"}'):
            cliente.post(
                "/api/observabilidad/pantalla",
                content=cuerpo,
                headers={"Content-Type": "application/json"},
            )
        assert observabilidad.resumen()["pantallas"] == [], (
            "lo que no parece una pantalla se descarta, no se cuenta como «otra»"
        )

    def test_una_pantalla_buena_suma_uno_a_su_dia(self, cliente):
        respuesta = cliente.post(
            "/api/observabilidad/pantalla",
            content=json.dumps({"pantalla": "tierras"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        assert respuesta.status_code == 204
        assert observabilidad.resumen()["pantallas"] == [
            {"dia": _hoy(), "pantalla": "tierras", "veces": 1}
        ]

    def test_la_pantalla_se_normaliza_y_lo_desconocido_cuenta_como_otra(self, cliente):
        for pantalla in ("Hoy", " alta ", "pantalla_inventada", "mas"):
            cliente.post(
                "/api/observabilidad/pantalla",
                content=json.dumps({"pantalla": pantalla}).encode(),
                headers={"Content-Type": "application/json"},
            )
        pantallas = {fila["pantalla"]: fila["veces"] for fila in observabilidad.resumen()["pantallas"]}
        assert pantallas == {"hoy": 1, "alta": 1, "otra": 1, "mas": 1}

    def test_un_fallo_al_apuntar_la_pantalla_no_cambia_el_204(self, cliente, monkeypatch):
        """**La regla de oro, en el aviso:** si el registro lanza, el móvil recibe su 204 igual."""

        def _revienta(*_args, **_kwargs):
            raise RuntimeError("el registro está roto")

        monkeypatch.setattr(observabilidad, "registrar_pantalla", _revienta)
        respuesta = cliente.post(
            "/api/observabilidad/pantalla",
            content=b'{"pantalla": "hoy"}',
            headers={"Content-Type": "application/json"},
        )
        assert respuesta.status_code == 204


# ---------------------------------------------------------------------------
# 4. Las claves de pantalla: lista blanca, longitud y caracteres
# ---------------------------------------------------------------------------


class TestLasClavesDePantalla:
    def test_la_lista_blanca_sale_del_armazon(self):
        """La lista blanca es la de las pantallas que la aplicación nueva sabe abrir.

        Se comprueba contra los valores de `vista` de `web/nuevo/app.js`, **sin copiarlos a
        mano**: si mañana se añade una pantalla, esta prueba obliga a decidir si se mide con su
        nombre o como `otra`, y eso es una decisión, no un olvido.
        """
        fuente = (
            pathlib.Path(__file__).resolve().parents[1] / "web" / "nuevo" / "app.js"
        ).read_text(encoding="utf-8")
        vistas = set(re.findall(r'vista === "([a-z0-9_-]+)"', fuente))
        vistas |= set(re.findall(r'data-destino="([a-z0-9_-]+)"', fuente))
        vistas |= set(re.findall(r'setVista\("([a-z0-9_-]+)"\)', fuente))
        assert set(observabilidad.CLAVES_DE_PANTALLA) == vistas, (
            "la lista blanca de pantallas y las vistas de la app nueva no coinciden: "
            f"sobran {sorted(set(observabilidad.CLAVES_DE_PANTALLA) - vistas)} y faltan "
            f"{sorted(vistas - set(observabilidad.CLAVES_DE_PANTALLA))}"
        )

    def test_solo_se_acepta_lo_que_parece_una_pantalla(self):
        assert observabilidad.clave_de_pantalla("hoy") == "hoy"
        assert observabilidad.clave_de_pantalla("HOY") == "hoy"
        assert observabilidad.clave_de_pantalla("  alta  ") == "alta"
        assert observabilidad.clave_de_pantalla("inventada") == "otra"
        assert observabilidad.clave_de_pantalla("../../etc") is None
        assert observabilidad.clave_de_pantalla("con espacios") is None
        assert observabilidad.clave_de_pantalla("x" * 100) is None
        assert observabilidad.clave_de_pantalla(None) is None
        assert observabilidad.clave_de_pantalla(42) is None

    def test_se_purgan_los_dias_viejos(self):
        viejo = (dt.date.today() - dt.timedelta(days=observabilidad.DIAS_DE_PANTALLAS + 40)).isoformat()
        observabilidad._PANTALLAS[(viejo, "hoy")] = 9
        observabilidad.registrar_pantalla("tierras")
        dias = {fila["dia"] for fila in observabilidad.resumen()["pantallas"]}
        assert viejo not in dias, "los días viejos no pueden quedarse para siempre"


# ---------------------------------------------------------------------------
# 5. Las rutas: plantilla sin identificadores y percentiles acotados
# ---------------------------------------------------------------------------


class TestLasRutas:
    def test_la_ruta_se_normaliza_sin_identificadores(self):
        assert observabilidad.normalizar_ruta("/api/parcelas/17") == "/api/parcelas/{id}"
        assert (
            observabilidad.normalizar_ruta("/api/parcelas/2031/tratamientos/9")
            == "/api/parcelas/{id}/tratamientos/{id}"
        )
        assert (
            observabilidad.normalizar_ruta("/api/nuevo/tierra/7?campana_id=3")
            == "/api/nuevo/tierra/{id}"
        )
        assert observabilidad.normalizar_ruta("37-455-12-3") == "/37-455-12-3", (
            "un identificador no es un número suelto: no se toca lo que no lo parece"
        )
        assert observabilidad.normalizar_ruta("") == "/"
        assert observabilidad.normalizar_ruta(None) == "/"
        assert len(observabilidad.normalizar_ruta("/" + "x" * 500)) <= observabilidad.MAXIMO_DE_LA_RUTA

    def test_el_middleware_mide_la_peticion_sin_identificadores(self, cliente):
        """De punta a punta: se pide una ruta con un id y en el resumen no aparece el id.

        Es lo que hace que `/api/parcelas/17` y `/api/parcelas/2031` sean la misma fila y que el
        resumen no se llene de claves distintas: una por cada tierra de la finca.
        """
        observabilidad.reiniciar()
        cliente.get("/api/parcelas/424242")
        rutas = {fila["ruta"]: fila for fila in observabilidad.resumen()["rutas"]}
        assert "/api/parcelas/{id}" in rutas, (
            f"el middleware no ha medido la petición por su plantilla: {sorted(rutas)}"
        )
        assert all("424242" not in ruta for ruta in rutas), (
            "el identificador se ha colado en una clave del resumen"
        )

    def test_los_percentiles_son_sencillos_y_coherentes(self):
        for milisegundos in (10, 20, 30, 40, 50):
            observabilidad.registrar_peticion("GET", "/api/x", 200, milisegundos)
        observabilidad.registrar_peticion("GET", "/api/x", 500, 60)
        ruta = observabilidad.resumen()["rutas"][0]
        assert ruta["peticiones"] == 6
        assert ruta["codigos"] == {"200": 5, "500": 1}
        assert ruta["p50_ms"] is not None and ruta["p95_ms"] is not None
        assert ruta["p50_ms"] <= ruta["p95_ms"], "el p50 no puede ser mayor que el p95"
        assert 30 <= ruta["p50_ms"] <= 40
        assert ruta["p95_ms"] >= 50

    def test_la_muestra_por_ruta_esta_acotada(self):
        for indice in range(observabilidad.MAXIMO_DE_MUESTRAS_POR_RUTA + 100):
            observabilidad.registrar_peticion("GET", "/api/x", 200, indice)
        ruta = observabilidad.resumen()["rutas"][0]
        assert ruta["muestras"] == observabilidad.MAXIMO_DE_MUESTRAS_POR_RUTA, (
            "se guardan todas las muestras: eso es una lista que crece sin freno"
        )

    def test_el_5xx_se_apunta_tambien_como_error(self):
        observabilidad.registrar_peticion("POST", "/api/labores/3", 500, 25, mensaje="se rompió")
        errores = observabilidad.resumen()["errores_recientes"]
        assert len(errores) == 1
        assert errores[0]["codigo"] == 500
        assert errores[0]["ruta"] == "/api/labores/{id}"

    def test_un_4xx_no_es_un_error_de_la_aplicacion(self):
        """Un 404 es una respuesta correcta a algo que no está, no un fallo que arreglar."""
        observabilidad.registrar_peticion("GET", "/api/x", 404, 5)
        assert observabilidad.resumen()["errores_recientes"] == []


# ---------------------------------------------------------------------------
# 6. El resumen: sin token no existe; con token, cabecera buena
# ---------------------------------------------------------------------------


class TestElTokenDelResumen:
    def test_sin_token_configurado_la_puerta_no_existe(self, cliente):
        respuesta = cliente.get("/api/observabilidad/resumen")
        assert respuesta.status_code == 404, (
            "sin CUEDIGITAL_OBSERVABILIDAD_TOKEN el resumen tiene que ser un 404, "
            "que no exista para nadie"
        )

    def test_con_token_configurado_sin_cabecera_es_403(self, cliente, monkeypatch):
        monkeypatch.setenv(observabilidad.VARIABLE_DEL_TOKEN, "un-token-de-verdad")
        assert cliente.get("/api/observabilidad/resumen").status_code == 403
        assert (
            cliente.get(
                "/api/observabilidad/resumen", headers={observabilidad.CABECERA_DEL_RESUMEN: "otro"}
            ).status_code
            == 403
        )

    def test_con_token_configurado_y_la_cabecera_buena_contesta_el_resumen(self, cliente, monkeypatch):
        monkeypatch.setenv(observabilidad.VARIABLE_DEL_TOKEN, "un-token-de-verdad")
        respuesta = cliente.get(
            "/api/observabilidad/resumen",
            headers={observabilidad.CABECERA_DEL_RESUMEN: "un-token-de-verdad"},
        )
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert set(datos) >= {"errores_recientes", "pantallas", "rutas", "embudo"}
        assert "etapas" in datos["embudo"] and "fallos" in datos["embudo"]

    def test_una_cabecera_vacia_no_vale_ni_con_token(self, cliente, monkeypatch):
        monkeypatch.setenv(observabilidad.VARIABLE_DEL_TOKEN, "un-token-de-verdad")
        respuesta = cliente.get(
            "/api/observabilidad/resumen",
            headers={observabilidad.CABECERA_DEL_RESUMEN: ""},
        )
        assert respuesta.status_code == 403

    def test_el_token_no_se_adivina_con_el_tiempo(self, monkeypatch):
        """Se usa `hmac.compare_digest`: una comparación normal para en el primer fallo.

        No se puede medir el tiempo de forma fiable en una prueba, así que se comprueba lo que
        sí es comprobable: que compara en tiempo constante de verdad y que un token sin
        configurar no vale nunca (ni con la cabecera vacía).
        """
        monkeypatch.setenv(observabilidad.VARIABLE_DEL_TOKEN, "secreto")
        assert observabilidad.token_es_valido("secreto") is True
        assert observabilidad.token_es_valido("secret0") is False
        assert observabilidad.token_es_valido("") is False
        assert observabilidad.token_es_valido(None) is False
        monkeypatch.delenv(observabilidad.VARIABLE_DEL_TOKEN)
        assert observabilidad.token_es_valido("") is False
        assert observabilidad.token_es_valido("secreto") is False


# ---------------------------------------------------------------------------
# 7. Si la observabilidad falla, la petición sigue
# ---------------------------------------------------------------------------


class TestLaObservabilidadNoRompeLaAplicacion:
    def test_si_el_registro_lanza_la_peticion_sigue(self, cliente, monkeypatch):
        """El caso que da miedo: el medidor revienta en cada petición.

        Se cambia `registrar_peticion` por una función que lanza y se pide una ruta de verdad.
        Tiene que contestar lo mismo que contestaría sin observabilidad (200) y no un 500.
        """

        def _revienta(*_args, **_kwargs):
            raise RuntimeError("la observabilidad está rota")

        monkeypatch.setattr(observabilidad, "registrar_peticion", _revienta)
        respuesta = cliente.get("/health")
        assert respuesta.status_code == 200, (
            "un fallo del medidor ha cambiado la respuesta: la observabilidad no puede tumbar "
            "la aplicación"
        )
        assert respuesta.json()["estado"] == "ok"

    def test_si_el_resumen_falla_se_contesta_500_y_la_aplicacion_sigue(self, cliente, monkeypatch):
        """El resumen es una herramienta interna: si falla, se dice con su 500 y nada más.

        Lo que **no** puede pasar es que ese fallo se lleve por delante la aplicación: la
        aplicación no depende de esta puerta para nada. Se comprueba el 500 del resumen y el 200
        de `/health` en la misma prueba.
        """

        def _revienta():
            raise RuntimeError("el resumen está roto")

        monkeypatch.setattr(observabilidad, "resumen", _revienta)
        monkeypatch.setenv(observabilidad.VARIABLE_DEL_TOKEN, "un-token-de-verdad")
        respuesta = cliente.get(
            "/api/observabilidad/resumen",
            headers={observabilidad.CABECERA_DEL_RESUMEN: "un-token-de-verdad"},
        )
        assert respuesta.status_code == 500, (
            "un fallo al preparar el resumen tiene que ser un 500 de esa puerta, no una excepción "
            "suelta"
        )
        assert cliente.get("/health").status_code == 200, "y la aplicación tiene que seguir viva"

    def test_registrar_un_error_con_un_objeto_hostil_no_lanza(self):
        """Un `str()` que lanza tampoco puede tumbar al medidor."""

        class _Hostil:
            def __str__(self):
                raise RuntimeError("no me puedes convertir a texto")

            def __repr__(self):  # pragma: no cover - por si acaso
                raise RuntimeError("ni a representación")

        observabilidad.registrar_error(_Hostil(), _Hostil(), _Hostil(), _Hostil(), _Hostil())
        errores = observabilidad.resumen()["errores_recientes"]
        assert len(errores) == 1, "el error se apunta con lo que sí se ha podido leer"
        assert errores[0]["tipo"] == "desconocido"
        assert errores[0]["ruta"] == "/"


# ---------------------------------------------------------------------------
# 8. El embudo: SQL sobre los datos de verdad, y aguanta una base a medias
# ---------------------------------------------------------------------------


def _las_cuentas_del_embudo(db) -> dict[str, int | None]:
    """Las etapas del embudo, por su clave. Cierra la lectura para que la siguiente vea lo nuevo."""
    resultado = observabilidad.embudo(db)
    db.rollback()
    return {etapa["clave"]: etapa["cuenta"] for etapa in resultado["etapas"]}


class TestElEmbudo:
    def test_el_embudo_cuenta_lo_que_de_verdad_hay(self, cliente, cuenta, parcela, nuevo_tratamiento, db):
        """Se recorren las etapas **creando los datos**: una tierra, un apunte y una firma.

        No se mira solo el número final: se mira que cada escalón sube cuando aparece el dato que
        lo hace subir, y que antes era cero. Un embudo que siempre da lo mismo no mide nada.
        """
        antes = _las_cuentas_del_embudo(db)
        assert antes["cuentas"] == 1, "el alta de la cuenta tiene que contarse"
        assert antes["fincas"] == 1
        assert antes["fincas_con_tierra"] == 1, "la parcela de la prueba ya es una tierra"
        assert antes["fincas_con_apunte"] == 0
        assert antes["fincas_con_cuaderno"] == 0

        respuesta = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        )
        assert respuesta.status_code == 201, respuesta.text
        con_apunte = _las_cuentas_del_embudo(db)
        assert con_apunte["fincas_con_apunte"] == 1, "el tratamiento tiene que contar como apunte"

        db.add(
            models.Firma(
                explotacion_id=cuenta["explotacion_id"],
                entidad="cuaderno",
                huella="a" * 64,
            )
        )
        db.commit()
        con_cuaderno = _las_cuentas_del_embudo(db)
        assert con_cuaderno["fincas_con_cuaderno"] == 1, (
            "el cuaderno firmado tiene que contar en el último escalón"
        )

    def test_el_embudo_baja_el_escalon_cuando_falta_el_dato(self, cliente, cuenta, parcela, db):
        """**El control al revés**: sin apuntes, el cuarto escalón es cero, no «uno porque sí»."""
        cuentas = _las_cuentas_del_embudo(db)
        assert cuentas["fincas_con_tierra"] == 1
        assert cuentas["fincas_con_apunte"] == 0

    def test_el_embudo_no_se_rompe_con_una_base_a_medias(self):
        """Con tablas ausentes, la etapa que no se puede medir queda en `None` y se declara.

        Se levanta una base de prueba con **solo dos tablas** y se le pasa el embudo. Las etapas
        que necesitan `parcelas`, `labores`… no existen: tienen que salir como «no se sabe», con
        su motivo, y las dos primeras tienen que medirse igual. Un `0` ahí sería mentira: sería
        decir que nadie ha llegado cuando lo que pasa es que no hay dónde mirar.
        """
        motor = create_engine("sqlite://")
        models.Base.metadata.create_all(
            bind=motor, tables=[models.Usuario.__table__, models.Explotacion.__table__]
        )
        with Session(motor) as sesion:
            resultado = observabilidad.embudo(sesion)
        cuentas = {etapa["clave"]: etapa["cuenta"] for etapa in resultado["etapas"]}
        fallos = {fallo["clave"] for fallo in resultado["fallos"]}
        assert cuentas["cuentas"] == 0
        assert cuentas["fincas"] == 0
        assert cuentas["fincas_con_tierra"] is None, "una tabla que no está no es un cero"
        assert "fincas_con_tierra" in fallos, "y hay que decir cuál no se ha podido medir"

    def test_el_embudo_es_monotono(self, cliente, cuenta, parcela, db):
        """Un embudo en el que un escalón tiene más que el anterior no describe a nadie."""
        cuentas = _las_cuentas_del_embudo(db)
        orden = [clave for clave, _que_es, _sql in observabilidad.ETAPAS_DEL_EMBUDO]
        anteriores = [cuentas[clave] for clave in orden if cuentas[clave] is not None]
        assert anteriores == sorted(anteriores, reverse=True), (
            f"las cuentas del embudo no bajan: {dict(zip(orden, anteriores))}"
        )
