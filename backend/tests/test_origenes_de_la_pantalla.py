"""**Qué orígenes pueden llamar a la API desde fuera** (09/11/2026).

EL CASO QUE CIERRA ESTE TEST
============================

La pantalla puede servirse desde otro sitio que la API: el front estático en GitHub Pages
(`https://erdeivih.github.io`) llamando al servidor propio. El navegador manda entonces una
petición **con origen distinto** y la API tiene que autorizarlo, o la pantalla se queda sin
datos aunque el servidor esté bien.

Hasta hoy el CORS estaba clavado a `http://localhost:5173` (el servidor de desarrollo). Eso
significa que **una pantalla publicada en otro sitio no puede leer la API**, y no hay forma de
arreglarlo sin tocar el código. Ahora los orígenes extra se piden por
`CUEDIGITAL_CORS_ORIGENES`, separados por comas, y los de desarrollo siguen valiendo.

Se comprueba sin levantar el servidor: la función que decide la lista.
"""

from __future__ import annotations

from app import main


def test_sin_variable_solo_valen_los_origenes_de_desarrollo(monkeypatch):
    """Por defecto, lo de siempre: nada de abrir la API a cualquiera."""
    monkeypatch.delenv("CUEDIGITAL_CORS_ORIGENES", raising=False)
    origenes = main.origenes_permitidos()
    assert "http://localhost:5173" in origenes
    assert "http://127.0.0.1:5173" in origenes
    assert all("github.io" not in origen for origen in origenes)


def test_una_pantalla_publicada_fuera_se_autoriza_por_variable(monkeypatch):
    """El front de Pages entra en la lista cuando se le dice, y solo entonces."""
    monkeypatch.setenv(
        "CUEDIGITAL_CORS_ORIGENES", "https://erdeivih.github.io, https://otro.example"
    )
    origenes = main.origenes_permitidos()
    assert "https://erdeivih.github.io" in origenes
    assert "https://otro.example" in origenes
    # Los de desarrollo no se pierden: el mismo programa sirve para los dos.
    assert "http://localhost:5173" in origenes


def test_los_huecos_y_las_comas_de_mas_no_rompen_la_lista(monkeypatch):
    """Escribir la variable con espacios o comas de más no puede dejar un origen negro."""
    monkeypatch.setenv("CUEDIGITAL_CORS_ORIGENES", " https://a.example ,, https://b.example , ")
    origenes = main.origenes_permitidos()
    assert "https://a.example" in origenes
    assert "https://b.example" in origenes
    assert "" not in origenes
    assert all(origen == origen.strip() for origen in origenes)


def test_la_estrella_no_abre_la_api_a_todo_el_mundo(monkeypatch):
    """`*` se ignora a propósito: es una API con datos de agricultores, no un servicio público.

    Con `*` y credenciales, cualquier página podría leer los vales de una cuenta abierta. Si
    alguien pone `*` por comodidad, el programa no lo obedece y sigue pidiendo orígenes escritos.
    """
    monkeypatch.setenv("CUEDIGITAL_CORS_ORIGENES", "*, https://c.example")
    origenes = main.origenes_permitidos()
    assert "*" not in origenes
    assert "https://c.example" in origenes
