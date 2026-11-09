"""Las pruebas del guion de carga: que las cuentas no se inventen, sin red y sin levantar nada.

El guion `scripts/prueba_de_carga.py` es el que decide cuántos agricultores aguanta el
programa. Si sus cuentas están mal —un percentil que se coge del extremo, un veredicto que
dice «aguanta» cuando había errores, una carpeta que no se borra— el documento de capacidad
diría una cosa y la máquina otra. Por eso lo que se prueba aquí es **la lógica**: percentiles
con listas conocidas, la rodilla, el veredicto y su código de salida, la tabla, el entorno
temporal y la salida cuando no hay servidor.

Lo que **no** se prueba aquí es la medición en sí: eso es la prueba de verdad, y se hace
contra un uvicorn de verdad (se lanza a mano y se apunta en `docs/PRUEBAS_DE_CARGA.md`).
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile

import httpx
import pytest

RUTA_GUION = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "prueba_de_carga.py"

_spec = importlib.util.spec_from_file_location("prueba_de_carga", RUTA_GUION)
assert _spec is not None and _spec.loader is not None
guion = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guion)


# --------------------------------------------------------------------------
# Percentiles
# --------------------------------------------------------------------------


def test_los_percentiles_de_una_lista_conocida():
    """Con 1..100, el p50 es 50,5 y el p95 es 95,05: se puede comprobar a mano."""
    valores = list(range(1, 101))
    assert guion.percentil(valores, 50) == pytest.approx(50.5)
    assert guion.percentil(valores, 95) == pytest.approx(95.05)
    assert guion.percentil(valores, 99) == pytest.approx(99.01)
    assert guion.percentil(valores, 0) == pytest.approx(1.0)
    assert guion.percentil(valores, 100) == pytest.approx(100.0)


def test_el_percentil_de_una_sola_medida_es_esa_medida():
    assert guion.percentiles([7.0]) == {"p50": 7.0, "p95": 7.0, "p99": 7.0}


def test_la_tabla_de_percentiles_lleva_los_tres_que_se_ensenan():
    medidas = guion.percentiles([10.0, 20.0, 30.0, 40.0])
    assert set(medidas) == {"p50", "p95", "p99"}
    assert medidas["p50"] == pytest.approx(25.0)
    assert medidas["p95"] == pytest.approx(38.5, abs=0.1)
    assert medidas["p99"] == pytest.approx(39.7, abs=0.1)


def test_sin_medidas_no_se_inventa_un_percentil():
    with pytest.raises(ValueError, match="No hay medidas"):
        guion.percentil([], 95)


def test_un_percentil_fuera_de_rango_se_rechaza():
    with pytest.raises(ValueError, match="entre 0 y 100"):
        guion.percentil([1.0, 2.0], 101)


# --------------------------------------------------------------------------
# Los escalones de concurrencia
# --------------------------------------------------------------------------


def test_los_escalones_se_leen_de_menos_a_mas():
    assert guion.leer_los_escalones("1,5,10,25,50") == (1, 5, 10, 25, 50)
    assert guion.leer_los_escalones(" 1 , 5 ") == (1, 5)


@pytest.mark.parametrize(
    "texto",
    ["", "   ", "1,5,5", "5,1", "0,5", "uno,cinco"],
)
def test_unos_escalones_que_no_valen_se_rechazan(texto):
    with pytest.raises(ValueError):
        guion.leer_los_escalones(texto)


def test_la_direccion_se_normaliza_sin_perder_el_servidor():
    assert guion.normalizar_direccion("127.0.0.1:8010/") == "http://127.0.0.1:8010"
    assert guion.normalizar_direccion("http://127.0.0.1:8010/") == "http://127.0.0.1:8010"
    with pytest.raises(ValueError):
        guion.normalizar_direccion("   ")


# --------------------------------------------------------------------------
# La rodilla y el veredicto
# --------------------------------------------------------------------------


def _medicion(usuarios: int, p95: float, errores: int = 0) -> dict:
    return {
        "usuarios": usuarios,
        "peticiones": usuarios * 5,
        "errores": errores,
        "p50_ms": p95 / 2,
        "p95_ms": p95,
        "p99_ms": p95 * 1.1,
        "peticiones_por_segundo": 100.0,
    }


def test_sin_errores_ni_disparos_no_hay_rodilla():
    mediciones = [_medicion(1, 20), _medicion(5, 30), _medicion(10, 45)]
    assert guion.encontrar_la_rodilla(mediciones) is None
    veredicto = guion.resumir_el_veredicto(mediciones, (1, 5, 10))
    assert veredicto["aguanta"] is True
    assert veredicto["codigo"] == guion.CODIGO_AGUANTA
    assert veredicto["rodilla_usuarios"] is None


def test_la_rodilla_aparece_en_cuanto_hay_errores():
    mediciones = [_medicion(1, 20), _medicion(5, 30, errores=3)]
    assert guion.encontrar_la_rodilla(mediciones) == 1
    veredicto = guion.resumir_el_veredicto(mediciones, (1, 5, 10))
    assert veredicto["aguanta"] is False
    assert veredicto["codigo"] == guion.CODIGO_NO_AGUANTA
    assert veredicto["rodilla_usuarios"] == 5
    assert "3 peticiones con error" in veredicto["motivo"]


def test_la_rodilla_aparece_cuando_el_p95_pasa_del_umbral():
    mediciones = [_medicion(1, 20), _medicion(50, guion.UMBRAL_P95_MS + 1)]
    assert guion.encontrar_la_rodilla(mediciones) == 1
    assert "pasa del umbral" in guion.resumir_el_veredicto(mediciones, (1, 50))["motivo"]


def test_mas_de_un_segundo_de_p95_ya_es_rodilla_aunque_haya_crecido_poco():
    """De 800 a 1.100 ms es un 38 % más, pero un segundo de espera ya no es aguantar.

    Es el caso medido el 09/11/2026 con 50 usuarios a la vez: el p95 llegó a 1.337 ms
    creciendo «solo» un 75 % respecto de los 25 usuarios. Un agricultor de pie en una
    parcela con mala cobertura no puede esperar eso, así que el umbral absoluto manda
    aunque la subida relativa no llegue al factor de la rodilla.
    """
    mediciones = [_medicion(10, 800), _medicion(50, 1100)]
    assert guion.encontrar_la_rodilla(mediciones) == 1


def test_la_rodilla_aparece_cuando_el_p95_se_multiplica():
    """De 200 a 900 ms es un p95 que se dispara aunque no llegue al umbral absoluto."""
    mediciones = [_medicion(1, 200), _medicion(25, 900)]
    assert guion.encontrar_la_rodilla(mediciones) == 1
    assert "se multiplica" in guion.resumir_el_veredicto(mediciones, (1, 25))["motivo"]


def test_un_pico_pequeno_no_es_una_rodilla():
    """De 50 a 120 ms es ruido de la máquina, no una rodilla: no se puede gritar por eso."""
    mediciones = [_medicion(1, 50), _medicion(5, 120)]
    assert guion.encontrar_la_rodilla(mediciones) is None


def test_si_faltan_escalones_no_se_puede_decir_que_aguanta():
    mediciones = [_medicion(1, 20), _medicion(5, 30)]
    veredicto = guion.resumir_el_veredicto(mediciones, (1, 5, 10))
    assert veredicto["aguanta"] is False
    assert veredicto["codigo"] == guion.CODIGO_NO_AGUANTA
    assert veredicto["escalones_que_faltan"] == [10]


# --------------------------------------------------------------------------
# La tabla que se enseña
# --------------------------------------------------------------------------


def test_la_tabla_sale_en_castellano_y_marca_la_rodilla():
    mediciones = [_medicion(1, 20), _medicion(5, 30), _medicion(10, 2000)]
    veredicto = guion.resumir_el_veredicto(mediciones, (1, 5, 10))
    tabla = guion.formatear_la_tabla(mediciones, veredicto)
    for palabra in ("Usuarios", "Peticiones", "Errores", "p50", "p95", "p99", "Peticiones/s"):
        assert palabra in tabla
    assert "<-- rodilla" in tabla
    assert "Rodilla: a partir de 10 usuarios" in tabla
    assert "Veredicto: NO aguanta" in tabla
    # Una fila por escalón, además de las dos cabeceras.
    assert len(tabla.splitlines()) == 2 + len(mediciones) + 3


def test_la_tabla_dice_que_aguanta_cuando_no_hay_rodilla():
    mediciones = [_medicion(1, 20), _medicion(5, 30)]
    veredicto = guion.resumir_el_veredicto(mediciones, (1, 5))
    tabla = guion.formatear_la_tabla(mediciones, veredicto)
    assert "Rodilla: no ha aparecido" in tabla
    assert "Veredicto: AGUANTA" in tabla
    assert "<-- rodilla" not in tabla


# --------------------------------------------------------------------------
# El recorrido, con respuestas de mentira (sin red)
# --------------------------------------------------------------------------

USUARIO_DE_PRUEBA = {
    "correo": "carga@ejemplo.test",
    "clave": "carga-2026-segura",
    "campana_id": 1,
    "producto_id": 2,
    "tierras": [7],
    "fecha": "2026-11-09",
}


def _andar_con(manejador) -> list[dict]:
    """Anda el recorrido contra un transporte falso de httpx: **no se abre ningún socket**."""

    async def _andar() -> list[dict]:
        transporte = httpx.MockTransport(manejador)
        async with httpx.AsyncClient(
            transport=transporte, base_url="http://prueba.test"
        ) as cliente:
            medidas: list[dict] = []
            await guion.andar_el_recorrido(cliente, USUARIO_DE_PRUEBA, medidas)
            return medidas

    return asyncio.run(_andar())


def test_el_recorrido_bueno_son_las_cinco_peticiones_del_agricultor():
    def manejador(peticion: httpx.Request) -> httpx.Response:
        if peticion.url.path == "/api/cuenta/entrar":
            return httpx.Response(200, json={"token": "un-token"})
        if peticion.url.path == "/api/tratamientos":
            return httpx.Response(201, json={"id": 1})
        return httpx.Response(200, json={})

    medidas = _andar_con(manejador)
    assert [medida["ruta"] for medida in medidas] == [
        "/api/cuenta/entrar",
        "/api/parcelas/vista",
        "/api/parcelas/7",
        "/api/tratamientos",
        "/api/cuaderno/resumen",
    ]
    assert all(200 <= medida["estado"] < 300 for medida in medidas)


def test_si_no_puede_entrar_el_recorrido_se_corta_y_se_apunta_el_fallo():
    """Sin clave no se puede seguir: una petición apuntada, con su 401, y nada más."""

    def manejador(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "El correo o la clave no son correctos."})

    medidas = _andar_con(manejador)
    assert len(medidas) == 1
    assert medidas[0]["ruta"] == "/api/cuenta/entrar"
    assert medidas[0]["estado"] == 401


def test_una_respuesta_de_entrar_que_no_trae_token_no_se_cuenta_dos_veces():
    """Un 200 con el cuerpo roto es UN fallo, no uno y medio."""

    def manejador(peticion: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="esto no es JSON")

    medidas = _andar_con(manejador)
    assert len(medidas) == 1
    assert medidas[0]["ruta"] == "/api/cuenta/entrar"


def test_el_tratamiento_que_rechazan_cuenta_como_error_pero_el_recorrido_sigue():
    def manejador(peticion: httpx.Request) -> httpx.Response:
        if peticion.url.path == "/api/cuenta/entrar":
            return httpx.Response(200, json={"token": "un-token"})
        if peticion.url.path == "/api/tratamientos":
            return httpx.Response(422, json={"detail": "falta algo"})
        return httpx.Response(200, json={})

    medidas = _andar_con(manejador)
    assert len(medidas) == 5
    errores = [medida for medida in medidas if medida["estado"] == 422]
    assert len(errores) == 1


# --------------------------------------------------------------------------
# La base de datos y los adjuntos: todo dentro de una carpeta temporal
# --------------------------------------------------------------------------


def test_el_servidor_de_pruebas_escribe_solo_en_la_carpeta_temporal(tmp_path):
    carpeta = tmp_path / "carga"
    entorno = guion.entorno_del_servidor_temporal(carpeta)
    base = entorno["CUEDIGITAL_DATABASE_URL"]
    assert base.startswith("sqlite:///")
    assert pathlib.Path(base.removeprefix("sqlite:///")).parent == carpeta
    assert pathlib.Path(entorno["CUEDIGITAL_ADJUNTOS"]) == carpeta / "adjuntos"
    # Las dos condiciones que hacen falta para poder bajar las iteraciones sin dejar
    # la contraseña floja en un servidor de verdad.
    assert entorno["CUEDIGITAL_ENTORNO"] == "pruebas"
    assert entorno["CUEDIGITAL_ITERACIONES_PBKDF2"] == "100000"
    assert entorno["CUEDIGITAL_SECRETO"]


def test_el_servidor_de_pruebas_no_hereda_la_base_de_la_suite(tmp_path, monkeypatch):
    monkeypatch.setenv("CUEDIGITAL_DATABASE_URL", "sqlite:///./backend/cuedigital.db")
    monkeypatch.setenv("CUEDIGITAL_SUITE_SOBRE", "postgresql://no/debe/pasar")
    entorno = guion.entorno_del_servidor_temporal(tmp_path / "carga")
    assert "cuedigital.db" not in entorno["CUEDIGITAL_DATABASE_URL"]
    assert "CUEDIGITAL_SUITE_SOBRE" not in entorno


def test_la_carpeta_temporal_de_la_carga_se_borra_al_terminar():
    with guion.carpeta_temporal_de_la_carga() as carpeta:
        assert carpeta.exists()
        assert str(carpeta).startswith(tempfile.gettempdir())
        (carpeta / "algo.txt").write_text("hola", encoding="utf-8")
    assert not carpeta.exists()


# --------------------------------------------------------------------------
# Que el servidor de pruebas se apaga de verdad
# --------------------------------------------------------------------------


def test_saber_si_queda_algo_escuchando_en_el_puerto():
    """El aviso de «sigue escuchando» solo puede salir si de verdad sigue escuchando."""
    import socket

    with socket.socket() as escucha:
        escucha.bind(("127.0.0.1", 0))
        # Con poco «backlog» y sin nadie aceptando, la segunda conexión se rechaza y la
        # función creería que el puerto se ha cerrado. El servidor de verdad acepta.
        escucha.listen(128)
        puerto = escucha.getsockname()[1]
        assert guion.el_puerto_esta_abierto(puerto, espera=0.2, intervalo=0.05) is True
    assert guion.el_puerto_esta_abierto(puerto, espera=0.5, intervalo=0.05) is False


def test_el_puerto_que_se_cierra_mientras_se_mira_deja_de_estar_abierto():
    """Un socket tarda un instante en soltarse: se espera a que cierre, no se avisa a la primera."""
    import socket
    import threading
    import time

    escucha = socket.socket()
    escucha.bind(("127.0.0.1", 0))
    escucha.listen(128)
    puerto = escucha.getsockname()[1]

    def cerrar() -> None:
        time.sleep(0.4)
        escucha.close()

    hilo = threading.Thread(target=cerrar, daemon=True)
    hilo.start()
    try:
        assert guion.el_puerto_esta_abierto(puerto, espera=3.0, intervalo=0.1) is False
    finally:
        hilo.join(timeout=5)


# --------------------------------------------------------------------------
# Cuando no hay servidor: se dice y se sale con 2, sin romper
# --------------------------------------------------------------------------


def test_el_mensaje_sin_servidor_dice_que_no_hay_y_como_arrancarlo():
    mensaje = guion.mensaje_sin_servidor("http://127.0.0.1:1234", "conexión rechazada")
    assert "No hay ningún servidor" in mensaje
    assert "http://127.0.0.1:1234" in mensaje
    assert "uvicorn" in mensaje
    assert "conexión rechazada" in mensaje


def test_el_guion_sale_con_codigo_2_cuando_no_hay_servidor():
    """Se lanza de verdad el guion contra un puerto cerrado: no debe romper, debe decir que no hay."""
    entorno = dict(os.environ)
    entorno["PYTHONIOENCODING"] = "utf-8"
    proceso = subprocess.run(
        [
            sys.executable,
            str(RUTA_GUION),
            "--base",
            "http://127.0.0.1:1",
            "--sin-servidor",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=entorno,
        timeout=120,
        check=False,
    )
    assert proceso.returncode == guion.CODIGO_SIN_SERVIDOR == 2, proceso.stderr
    salida = f"{proceso.stdout}\n{proceso.stderr}"
    assert "No hay ningún servidor" in salida
    assert "Traceback" not in salida


def test_la_prueba_puede_medir_con_las_iteraciones_de_produccion():
    """`--iteraciones-pbkdf2 240000` mide el coste real de entrar en producción.

    Sin esa opción la prueba siempre mide con 100.000 (el registro tarda menos), y el
    número que sale es **optimista**: en producción la clave se deriva 240.000 veces. La
    opción tiene que existir y llegar hasta el servidor temporal, no solo al texto de ayuda.
    """
    codigo = guion.main(
        [
            "--base",
            "http://127.0.0.1:1",
            "--sin-servidor",
            "--iteraciones-pbkdf2",
            "240000",
        ]
    )
    assert codigo == guion.CODIGO_SIN_SERVIDOR
    entorno = guion.entorno_del_servidor_temporal(
        pathlib.Path(tempfile.gettempdir()) / "carga", iteraciones=240000
    )
    assert entorno["CUEDIGITAL_ITERACIONES_PBKDF2"] == "240000"


def test_la_maquina_se_puede_describir_sin_inventar():
    datos = guion.informacion_de_la_maquina()
    assert datos["sistema"]
    assert datos["nucleos_logicos"] is None or datos["nucleos_logicos"] >= 1
    assert datos["ram_gb"] is None or datos["ram_gb"] > 0
