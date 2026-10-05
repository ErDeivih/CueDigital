"""Los ficheros de React que usa la interfaz: que estén, que sean los revisados y que no se toquen.

Este test existe porque la interfaz pasa a React **sin compilar**: lo que hay en
`backend/web/vendor/` no es una dependencia que se instala, es JavaScript que se ejecuta tal cual en
el navegador del agricultor. Si alguien cambia uno de esos ficheros —a mano, o porque una descarga
trajo otra cosa— la aplicación ejecutaría código que nadie ha revisado, y no habría forma de notarlo.

Por eso se comprueba aquí:

1. Que los tres ficheros están y su **SHA-256** es el que está apuntado en el guion.
2. Que las direcciones de descarga están **clavadas a una versión** (`@18.3.1`), no a «la última»:
   una dependencia que cambia sola es una aplicación que un día deja de funcionar sin que nadie haya
   tocado nada.
3. Que el guion **no toca la red** cuando ya está todo descargado (se sustituye la descarga por una
   que falla a propósito: si intentara descargar, el test se pondría rojo).
4. Que si un fichero no cuadra, el guion **se para** en vez de seguir con lo que haya.
5. Que el LEEME de la carpeta cuenta lo mismo que el guion, con las huellas y las licencias.

Ninguno de estos tests toca la red.
"""

from __future__ import annotations

import hashlib
import re

import pytest

from scripts import bajar_react

CARPETA = bajar_react.DESTINO
LEEME = CARPETA / "LEEME.md"


class TestLosFicherosEstan:
    def test_estan_los_tres_y_con_la_huella_esperada(self):
        """Los tres ficheros oficiales, descargados y sin tocar."""
        faltan = [nombre for nombre in bajar_react.FICHEROS if not (CARPETA / nombre).exists()]
        assert not faltan, (
            f"faltan ficheros de React en {CARPETA}: {faltan}. "
            "Se descargan con `python scripts/bajar_react.py`."
        )
        for nombre, (_url, huella_esperada) in bajar_react.FICHEROS.items():
            actual = hashlib.sha256((CARPETA / nombre).read_bytes()).hexdigest()
            assert actual == huella_esperada, (
                f"{nombre} no es el fichero que se revisó.\n"
                f"  esperada: {huella_esperada}\n  la que hay: {actual}\n"
                "No se edita a mano: se cambia la versión en `scripts/bajar_react.py` y se vuelve a lanzar."
            )
        assert bajar_react.esta_descargado() is True

    def test_estan_las_licencias(self):
        """MIT (React) y Apache 2.0 (`htm`) permiten copiarlos, y sus textos van con ellos."""
        for nombre in ("LICENSE-React.txt", "LICENSE-htm.txt"):
            fichero = CARPETA / nombre
            assert fichero.exists(), f"falta {nombre} en {CARPETA}"
            assert fichero.read_text(encoding="utf-8").strip(), f"{nombre} está vacío"

        assert "MIT License" in (CARPETA / "LICENSE-React.txt").read_text(encoding="utf-8")
        assert "Apache License" in (CARPETA / "LICENSE-htm.txt").read_text(encoding="utf-8")


class TestLasDirecciones:
    def test_las_direcciones_clavan_la_version(self):
        """`@18.3.1` y no `@latest`: una dependencia que cambia sola rompe sin avisar."""
        for nombre, (url, huella) in bajar_react.FICHEROS.items():
            assert url.startswith("https://"), f"{nombre} no se descarga por https: {url}"
            assert "unpkg.com" in url, f"{nombre} no sale del espejo oficial del registro: {url}"
            assert re.search(r"@\d+\.\d+\.\d+/", url), (
                f"{nombre} no lleva la versión clavada en la dirección: {url}"
            )
            assert "latest" not in url, f"{nombre} apunta a «la última», que cambia sola: {url}"
            assert re.fullmatch(r"[0-9a-f]{64}", huella), f"{nombre} no tiene una huella SHA-256"

    def test_react_no_pasa_de_la_18(self):
        """React 19 ya no publica ficheros para `<script>`: si alguien sube de versión, que lo diga.

        Esto no es una preferencia: es el motivo por el que la interfaz se puede cargar sin
        compilar. Cuando salga una versión con ficheros UMD, este test es el sitio donde hay que
        explicar el cambio.
        """
        versiones = {
            re.search(r"@(\d+)\.", url).group(1)
            for url, _huella in ((url, h) for url, h in bajar_react.FICHEROS.values())
            if "react" in url
        }
        assert versiones == {"18"}, (
            f"React va por la versión {versiones} y esto se escribió para la 18, que es la última "
            "que publica ficheros UMD (los que se cargan con una etiqueta <script> sin compilar)"
        )


class TestElGuion:
    def test_no_toca_la_red_si_ya_esta_todo(self, monkeypatch, capsys):
        """Si los ficheros están y coinciden, el guion no descarga nada."""

        def no_llames_a_la_red(*_args, **_kwargs):
            raise AssertionError("el guion ha intentado descargar teniendo los ficheros ya puestos")

        monkeypatch.setattr(bajar_react.httpx, "get", no_llames_a_la_red)
        assert bajar_react.main() == 0
        assert "Ya está y coincide" in capsys.readouterr().out

    def test_se_para_si_un_fichero_no_cuadra(self, monkeypatch, tmp_path, capsys):
        """Un fichero cambiado no se da por bueno: se avisa y se para."""
        # Los otros dos se ponen buenos para que lo único malo sea el que se está probando: si no,
        # el guion intentaría descargarlos y el test dejaría de comprobar lo que quiere comprobar.
        for nombre, (_url, _huella) in bajar_react.FICHEROS.items():
            if nombre != "react.production.min.js":
                (tmp_path / nombre).write_bytes((CARPETA / nombre).read_bytes())
        (tmp_path / "react.production.min.js").write_text("esto no es React", encoding="utf-8")

        def no_llames_a_la_red(*_args, **_kwargs):
            raise AssertionError("no debe descargar nada cuando lo que hay no cuadra")

        monkeypatch.setattr(bajar_react, "DESTINO", tmp_path)
        monkeypatch.setattr(bajar_react.httpx, "get", no_llames_a_la_red)

        assert bajar_react.main() == 1
        salida = capsys.readouterr().out
        assert "NO coincide" in salida
        assert "No se da nada por bueno" in salida


class TestElLeeme:
    def test_el_leeme_cuenta_lo_mismo_que_el_guion(self):
        """El LEEME lleva las huellas y las direcciones: si se cambia una versión, hay que tocarlo."""
        texto = LEEME.read_text(encoding="utf-8")

        for nombre, (url, huella) in bajar_react.FICHEROS.items():
            assert nombre in texto, f"el LEEME no nombra {nombre}"
            assert url in texto, f"el LEEME no dice de dónde sale {nombre}"
            assert huella in texto, f"el LEEME no lleva la huella de {nombre}"

    def test_el_leeme_explica_por_que_no_se_compila_y_las_licencias(self):
        """Los dos motivos por los que esto está aquí, y no en un proyecto con npm."""
        texto = LEEME.read_text(encoding="utf-8")

        assert "sin cobertura" in texto, "el LEEME no explica que tiene que funcionar sin cobertura"
        assert "no hay Node" in texto, "el LEEME no explica que donde corre esto no hay Node"
        assert "React 19" in texto, "el LEEME no explica por qué la versión 18 y no la última"
        assert "MIT" in texto and "Apache 2.0" in texto, "el LEEME no dice las licencias"
        assert "bajar_react.py" in texto, "el LEEME no dice cómo se regenera"


class TestLaVersionDeHtmTambienEstaClavada:
    def test_htm_va_con_su_version_y_su_huella(self):
        url, huella = bajar_react.FICHEROS["htm.umd.js"]
        assert "@3.1.1/" in url, f"htm no lleva la versión clavada: {url}"
        assert re.fullmatch(r"[0-9a-f]{64}", huella)

    def test_htm_es_lo_que_permite_escribir_la_pantalla_sin_compilar(self, tmp_path):
        """`htm` tiene que dejar `window.htm` al cargarse: si no, no hay forma de pintar sin JSX."""
        contenido = (CARPETA / "htm.umd.js").read_text(encoding="utf-8")
        assert "htm" in contenido
        # El fichero UMD se asigna a window/globalThis cuando no hay sistema de módulos.
        assert re.search(r"(window|globalThis|self)\.htm|exports\.htm|module\.exports", contenido), (
            "el fichero de htm no parece un UMD: no se podría cargar con <script>"
        )


@pytest.mark.parametrize("nombre", [n for n in sorted(bajar_react.FICHEROS) if "react" in n])
def test_ningun_fichero_vendido_como_nuestro(nombre: str):
    """Los ficheros de vendor no se editan: llevan la cabecera de su fabricante.

    Los de React empiezan con un comentario de licencia. Si uno se hubiera reescrito a mano, ese
    comentario no estaría.

    `htm.umd.js` **no** entra aquí porque su fichero compilado se publica sin cabecera (está
    minificado a pelo). Su licencia viaja aparte, en `LICENSE-htm.txt`, y es Apache 2.0.
    """
    texto = (CARPETA / nombre).read_text(encoding="utf-8", errors="replace")[:2000]
    assert "license" in texto.lower() or "copyright" in texto.lower(), (
        f"{nombre} no lleva la cabecera de licencia: parece editado a mano"
    )
