"""Pruebas de la revisión móvil y de tableta (`task-8`).

## Para qué existen

El 09/11/2026 se revisó la app nueva (`/nuevo/`) y se midió, en un navegador de verdad, que:
el **38 % del texto** iba a 13 px (y el calendario a 10), la **opción elegida** se quedaba en
**2,48:1** de contraste en modo oscuro, las **celdas del calendario** medían 42,9 px de ancho
a 390 (menos que un dedo), el **menú lateral** separaba sus renglones 4 px, el **mapa de
«Mis tierras»** no se podía tocar (los anillos tienen 2 px de trazo), la **lista de 64
tierras de «Apuntar»** vivía en una caja con scroll propio, y la **referencia del SIGPAC**
se escribía con el teclado de letras.

Estas pruebas son el guardián de los arreglos: leen el CSS y el JavaScript y comprueban los
números, no las intenciones. La comprobación de verdad (capturas y medidas en el DOM a 360,
390, 768 y 1024 px) la hace `backend/scripts/capturar_la_revision_movil.py` y su resultado
queda en `docs/capturas-revision/mediciones-despues.json`; la última prueba de este fichero
lee ese resultado y exige **0 desbordes y 0 controles por debajo de 44 px**.

Se escribieron **antes** de tocar la pantalla, y la primera vez que se ejecutaron se pusieron
en rojo: eso es lo que demuestra que miran algo que de verdad estaba mal.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
NUEVO = RAIZ / "backend" / "web" / "nuevo"
CSS = NUEVO / "estilos.css"
APP = NUEVO / "app.js"
MEDICION = RAIZ / "docs" / "capturas-revision" / "mediciones-despues.json"

# El suelo del dedo y el de la letra, los dos del contrato (`DESIGN.md`).
TOQUE_MINIMO = 44
TOQUE_PRINCIPAL = 48
PISTA_PX = 15.2


def leer(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def bloque_css(selector: str) -> str:
    """El cuerpo de la primera regla de ese selector exacto (sin `@media` de por medio)."""
    encontrado = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", leer(CSS))
    assert encontrado, f"el CSS no tiene la regla `{selector}`"
    return encontrado.group(1)


def a_px(valor: str) -> float | None:
    """`13px` → 13; `0.95rem` → 15,2; lo que no sea una medida, `None`."""
    medida = re.fullmatch(r"\s*([\d.]+)(px|rem)\s*", valor)
    if not medida:
        return None
    numero = float(medida.group(1))
    return numero * 16 if medida.group(2) == "rem" else numero


def a_rgb(color: str) -> tuple[int, int, int]:
    valor = color.strip().lstrip("#")
    if len(valor) == 3:
        valor = "".join(letra * 2 for letra in valor)
    return tuple(int(valor[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def luminancia(color: str) -> float:
    def canal(valor: int) -> float:
        proporcion = valor / 255
        return proporcion / 12.92 if proporcion <= 0.03928 else ((proporcion + 0.055) / 1.055) ** 2.4

    rojo, verde, azul = a_rgb(color)
    return 0.2126 * canal(rojo) + 0.7152 * canal(verde) + 0.0722 * canal(azul)


def contraste(uno: str, otro: str) -> float:
    claro, oscuro = sorted((luminancia(uno), luminancia(otro)), reverse=True)
    return round((claro + 0.05) / (oscuro + 0.05), 2)


def la_paleta(*, oscuro: bool) -> dict[str, str]:
    """Los tokens de `:root` y, encima, los del bloque de noche si se piden."""
    css = leer(CSS)
    luz = re.search(r":root\s*\{(.*?)\}", css, re.DOTALL)
    assert luz, "el CSS nuevo no tiene `:root`"
    valores = {
        nombre: valor.strip() for nombre, valor in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", luz.group(1))
    }
    if oscuro:
        noche = re.search(
            r"@media \(prefers-color-scheme: dark\)\s*\{\s*:root\s*\{(.*?)\}\s*\}",
            css,
            re.DOTALL,
        )
        assert noche, "el CSS nuevo no tiene la paleta de noche"
        valores.update(
            {
                nombre: valor.strip()
                for nombre, valor in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", noche.group(1))
            }
        )
    return valores


def etiquetas_de_input() -> list[str]:
    return re.findall(r"<input\b[^>]*>", leer(APP), re.DOTALL)


def el_input_con(enganche: str) -> str:
    for etiqueta in etiquetas_de_input():
        if enganche in etiqueta:
            return etiqueta
    pytest.fail(f"no hay ningún `<input>` con el enganche `{enganche}` en app.js")


# ---------------------------------------------------------------------------
# Lo que se toca
# ---------------------------------------------------------------------------


class TestLoQueSeToca:
    def test_la_rejilla_del_calendario_da_celdas_de_dedo_a_360(self):
        """A 360 px no se puede tener a la vez 8 px de hueco y 44 px de celda con los
        márgenes de 16: la tarjeta del calendario se sale a sangre en el móvil. Esto
        comprueba los dos números que lo hacen posible, en vez de fiarse del comentario.
        """
        css = leer(CSS)
        hueco = re.search(r"--calendario-hueco:\s*(\d+)px", css)
        assert hueco, "falta el hueco declarado de la rejilla del calendario"
        assert int(hueco.group(1)) >= 8, "las celdas del calendario se tocan entre sí"
        a_sangre = re.search(
            r"\.pantalla-calendario \.tarjeta--calendario\s*\{[^}]*margin-left:\s*calc\(-1 \* var\(--space-4\)\)",
            css,
            re.DOTALL,
        )
        assert a_sangre, "la tarjeta del calendario no se sale a sangre en el móvil"
        # El ancho útil de una celda: (360 − 2 de borde − 6 huecos) / 7.
        ancho = (360 - 2 - 6 * int(hueco.group(1))) / 7
        assert ancho >= TOQUE_MINIMO, f"las celdas del calendario miden {ancho:.1f} px de ancho"

    def test_los_renglones_del_menu_se_separan(self):
        assert "gap: var(--space-2)" in bloque_css(".nav"), (
            "los renglones del menú lateral se separan menos de 8 px"
        )

    def test_las_celdas_del_calendario_se_separan(self):
        css = leer(CSS)
        regla = re.search(r"\.calendario__semana,\s*\.calendario__rejilla\s*\{([^}]*)\}", css)
        assert regla, "falta la regla de la rejilla del calendario"
        assert "gap: var(--calendario-hueco)" in regla.group(1), "las celdas del calendario se tocan"

    def test_la_accion_principal_llega_a_48(self):
        assert "min-height: 56px" in bloque_css(".boton--grande"), "la acción principal mide menos de 48 px"
        assert "min-height: var(--toque)" in bloque_css(".boton")


# ---------------------------------------------------------------------------
# La letra
# ---------------------------------------------------------------------------


class TestLaLetra:
    def test_ninguna_letra_baja_del_tamano_de_la_pista(self):
        """El único texto por debajo del cuerpo es la pista (0,95 rem = 15,2 px).

        Medido el 09/11/2026: había **25 reglas a 13 px**, tres a 10 px, una a 14 y trece a
        15. Con el sol de frente eso no se lee. Esto las cuenta una a una.
        """
        problemas: list[str] = []
        for numero, linea in enumerate(leer(CSS).splitlines(), start=1):
            medida = re.search(r"font-size:\s*([^;]+);", linea)
            if not medida:
                continue
            valor = medida.group(1).strip()
            if valor in ("inherit", "0"):
                continue
            px = a_px(valor)
            if px is None:
                problemas.append(f"línea {numero}: `font-size: {valor}` no es una medida conocida")
            elif round(px, 2) < PISTA_PX:
                problemas.append(f"línea {numero}: `font-size: {valor}` ({px} px)")
        assert not problemas, "hay texto por debajo de 15,2 px: " + "; ".join(problemas)

    def test_la_marca_de_hoy_no_se_pinta_diminuta(self):
        assert "font-size: 10px" not in leer(CSS), "la marca «Hoy» y la cuenta del día siguen a 10 px"


# ---------------------------------------------------------------------------
# El elegido, en los dos modos
# ---------------------------------------------------------------------------


class TestElElegido:
    def test_la_opcion_elegida_se_lee_en_los_dos_modos(self):
        """En claro el elegido medía 6,51:1; en oscuro, **2,48:1** (el texto de marca sobre
        su propio tinte). Se pinta como manda el contrato: fondo de marca y texto blanco.
        """
        for oscuro in (False, True):
            paleta = la_paleta(oscuro=oscuro)
            ratio = contraste(paleta["--brand"], paleta["--on-brand"])
            assert ratio >= 4.5, f"el elegido se queda en {ratio}:1 en {'oscuro' if oscuro else 'claro'}"
        regla = bloque_css(".pastilla--activa")
        assert "background: var(--brand)" in regla, "la pastilla elegida no usa el fondo de marca"
        assert "color: var(--on-brand)" in regla, "la pastilla elegida no usa el texto sobre marca"
        nav = bloque_css(".nav__enlace--activo")
        assert "background: var(--brand)" in nav and "color: var(--on-brand)" in nav

    def test_la_marca_hoy_se_lee_en_los_dos_modos(self):
        """`--brand` sobre el fondo de la tarjeta da 3,29:1 en oscuro: se usa el verde claro."""
        paleta = la_paleta(oscuro=False)
        assert contraste(paleta["--brand"], paleta["--surface-card"]) >= 4.5
        noche = la_paleta(oscuro=True)
        assert contraste(noche["--brand-bright"], noche["--surface-card"]) >= 4.5
        css = leer(CSS)
        regla = re.search(r"\.calendario__hoy\s*\{([^}]*)\}", css)
        assert regla and "color: var(--brand)" in regla.group(1)
        # Y la de noche se cambia al verde claro, en su bloque.
        de_noche = css.split("@media (prefers-color-scheme: dark)")[-1]
        assert ".calendario__hoy" in de_noche, "la marca «Hoy» no se corrige en modo oscuro"
        assert "--brand-bright" in de_noche


# ---------------------------------------------------------------------------
# El mapa
# ---------------------------------------------------------------------------


class TestElMapa:
    def test_los_anillos_del_mapa_llevan_su_zona_de_toque(self):
        """Un trazo de 2 px no se acierta con el dedo. Detrás va el mismo camino con 60 px
        de trazo invisible, como ya hace la ventana del SIGPAC."""
        app = leer(APP)
        assert "data-mapa-toque" in app, "el mapa de «Mis tierras» no tiene zonas de toque"
        assert "mapa__anillo--toque" in app
        css = leer(CSS)
        assert "stroke-width: 60" in bloque_css(".mapa__anillo--toque")
        assert "pointer-events: stroke" in bloque_css(".mapa__anillo--toque")

    def test_el_mapa_del_sigpac_elige_el_recinto_que_se_toca(self):
        app = leer(APP)
        assert "data-sigpac-dibujo-recinto" in app
        assert "aria-pressed" in app
        assert "onKeyDown" in app


# ---------------------------------------------------------------------------
# El teclado del móvil
# ---------------------------------------------------------------------------


CAMPOS_NUMERICOS = (
    "data-apuntar-hectareas",
    "data-apuntar-dosis",
    "data-editar-superficie",
    "data-sigpac-agregado",
    "data-sigpac-zona",
    "data-sigpac-poligono",
    "data-sigpac-parcela",
    "data-sigpac-buscar-referencia",
)

BUSCADORES = (
    "data-buscador",
    "data-producto-buscar",
    "data-sigpac-buscar-municipio",
)


class TestElTeclado:
    @pytest.mark.parametrize("enganche", CAMPOS_NUMERICOS)
    def test_cada_campo_numerico_pide_el_teclado_del_movil(self, enganche):
        etiqueta = el_input_con(enganche)
        tiene = (
            'type="number"' in etiqueta
            or 'type="tel"' in etiqueta
            or "inputMode=" in etiqueta
            or "inputmode=" in etiqueta
        )
        assert tiene, f"`{enganche}` se escribe con el teclado de letras"

    def test_la_referencia_del_sigpac_lleva_teclado_de_numeros(self):
        """La referencia son siete números con separadores. `type="tel"` pide el teclado de
        números y `inputMode="decimal"` elige el que **trae separador** (coma o punto): sin
        él, en un iPhone no se puede escribir `37.70.0.0.503.51`."""
        etiqueta = el_input_con("data-sigpac-buscar-referencia")
        assert 'type="tel"' in etiqueta, "la referencia del SIGPAC no pide el teclado de números"
        assert "inputMode=\"decimal\"" in etiqueta, "el teclado de la referencia no trae separador"

    def test_las_cantidades_piden_teclado_de_numeros_con_coma(self):
        etiqueta = el_input_con("data-apuntar-dosis")
        assert 'type="tel"' in etiqueta and "inputMode=\"decimal\"" in etiqueta

    @pytest.mark.parametrize("enganche", BUSCADORES)
    def test_los_buscadores_dicen_que_la_tecla_busca(self, enganche):
        etiqueta = el_input_con(enganche)
        assert "enterKeyHint=" in etiqueta or "enterkeyhint=" in etiqueta, (
            f"`{enganche}` no dice qué hace la tecla de enviar"
        )


# ---------------------------------------------------------------------------
# Tablas, listas y la tierra sin forma
# ---------------------------------------------------------------------------


class TestTablasYListas:
    def test_la_tabla_de_otros_anios_se_desplaza_dentro_de_su_caja(self):
        """Una tabla de cuatro columnas a 360 no cabe: se desplaza dentro de su caja y la
        primera columna (el año) se queda a la vista, sin mover la página."""
        app = leer(APP)
        assert re.search(
            r'<div className="tabla-envoltura">\s*<table className="panel__tabla"', app
        ), "la tabla de «otros años» no tiene su caja que desplaza"
        css = leer(CSS)
        assert ".panel__tabla th:first-child" in css, "la primera columna de la tabla no se queda fija"

    def test_la_lista_de_tierras_de_apuntar_no_anida_scroll(self):
        """En el móvil se desplaza la página, no una caja dentro de la página (P5)."""
        css = leer(CSS)
        movil = css.split("@media (max-width: 700px)")
        assert len(movil) > 1
        assert re.search(
            r"\.pantalla-apuntar \.lista-tierras\s*\{[^}]*max-height:\s*none", css, re.DOTALL
        ), "la lista de tierras de «Apuntar» sigue con scroll propio en el móvil"

    def test_la_tierra_sin_forma_no_pinta_un_cuadro(self):
        """`DESIGN.md`: si la parcela no tiene forma, **no se dibuja un cuadro**. Y la misma
        idea no se repite dos veces por fila (P7)."""
        app = leer(APP)
        assert "miniatura--sin-mapa" not in app, "sigue habiendo un cuadro inventado para la tierra sin forma"
        assert "tierra--sin-miniatura" in app
        assert ".tierra--sin-miniatura" in leer(CSS)


# ---------------------------------------------------------------------------
# La prueba de la verdad: los números del navegador
# ---------------------------------------------------------------------------


class TestLoMedidoEnElNavegador:
    """Lee el resultado del guion de capturas y medidas (`mediciones-despues.json`).

    No lanza un navegador (eso lo hace el guion a mano): comprueba el resultado guardado,
    que es la evidencia que cita `docs/revision-interfaz.md`.
    """

    def test_el_guion_de_capturas_existe(self):
        assert (RAIZ / "backend" / "scripts" / "capturar_la_revision_movil.py").is_file()

    def test_estan_las_capturas_de_los_cuatro_anchos(self):
        capturas = RAIZ / "docs" / "capturas-revision"
        for ancho in (360, 390, 768, 1024):
            for pantalla in ("tierras", "tierra", "alta", "sigpac", "cuaderno", "trabajos"):
                fichero = capturas / f"despues-{pantalla}-{ancho}.png"
                assert fichero.is_file(), f"falta la captura {fichero.name}"

    def test_cero_desbordes_y_cero_controles_pequenos(self):
        assert MEDICION.is_file(), "falta `mediciones-despues.json`: no hay prueba del después"
        datos = json.loads(MEDICION.read_text(encoding="utf-8"))
        resumen = datos.get("resumen") or {}
        assert set(resumen) == {"360", "390", "768", "1024"}, (
            f"faltan anchos en la medición: {sorted(resumen)}"
        )
        problemas: list[str] = []
        for ancho, numeros in resumen.items():
            if numeros["pantallas_con_desborde"]:
                problemas.append(f"{ancho} px: desborde en {numeros['desbordes']}")
            if numeros["controles_pequenos"]:
                problemas.append(
                    f"{ancho} px: {numeros['controles_pequenos']} controles < 44 px"
                    f" ({numeros['detalle_pequenos']})"
                )
            if numeros["principales_pequenos"]:
                problemas.append(f"{ancho} px: {numeros['principales_pequenos']} acciones principales < 48 px")
            if numeros["modales_que_no_caben"]:
                problemas.append(f"{ancho} px: {numeros['modales_que_no_caben']} ventanas que no caben")
        assert not problemas, "La medición del después no está limpia: " + "; ".join(problemas)
