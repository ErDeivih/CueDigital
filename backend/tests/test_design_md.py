"""Tests del contrato de diseño (`DESIGN.md`).

Un `DESIGN.md` que nadie comprueba es un documento decorativo: en tres meses dice una
cosa y la pantalla hace otra. Estos tests son lo que convierte el contrato en algo que
se cumple de verdad.

Qué se comprueba:

1. Que el fichero sigue el formato oficial: frontmatter YAML, secciones y su orden.
2. Que cada color del contrato es **exactamente** el que usa el CSS, y en los dos
   sentidos: ni el contrato inventa colores que la pantalla no tiene, ni la pantalla
   tiene colores que el contrato no declara.
3. Que no queda ningún color suelto fuera de `:root`.
4. Que ningún par de fondo y texto baja de 4,5:1. Es la regla `contrast-ratio` del
   validador oficial, implementada aquí para no depender de Node ni de internet.
5. Que las reglas duras están escritas en "Do's and Don'ts", que es lo que lee un
   agente antes de tocar la interfaz.

El validador oficial (`npx -p @google/design.md designmd lint DESIGN.md`) da **0 errores
y 0 advertencias** sobre este fichero. Está apuntado en el README para poder pasarlo a
mano, pero **no se llama desde aquí a propósito**: un test que necesita Node, npm y
conexión no es un test, es una lotería.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[2]
DESIGN = RAIZ / "DESIGN.md"
CSS = RAIZ / "backend" / "web" / "estilos.css"

# El orden que fija la especificación. No es una preferencia: el validador oficial
# avisa si las secciones aparecen en otro orden.
SECCIONES_OFICIALES = [
    "Overview",
    "Colors",
    "Typography",
    "Layout",
    "Elevation & Depth",
    "Shapes",
    "Components",
    "Do's and Don'ts",
]

CONTRASTE_MINIMO = 4.5

# Qué variable del CSS corresponde a cada token del contrato. Si se añade un color a
# uno de los dos lados, el test obliga a añadirlo también al otro.
MAPA_DE_COLORES = {
    "--verde": "primary",
    "--verde-medio": "primary-container",
    "--verde-oscuro": "primary-dark",
    "--sobre-verde": "on-primary",
    "--sobre-verde-tenue": "primary-overlay",
    "--sobre-verde-borde": "primary-overlay-border",
    "--tinta": "on-surface",
    "--tinta-suave": "on-surface-variant",
    "--fondo": "surface",
    "--fondo-suave": "surface-variant",
    "--borde": "outline",
    "--aviso-fondo": "secondary-container",
    "--aviso-borde": "tertiary",
    "--aviso-tinta": "on-secondary-container",
    "--error-fondo": "error-container",
    "--error-borde": "error",
    "--error-oscuro": "error-dark",
    "--error-tinta": "on-error-container",
    "--foco": "focus",
}


# --------------------------------------------------------------------------
# Lectura de los dos ficheros
# --------------------------------------------------------------------------


def leer_design_md() -> tuple[dict, str]:
    """Separa el frontmatter YAML del cuerpo en Markdown."""
    texto = DESIGN.read_text(encoding="utf-8")
    assert texto.startswith("---\n"), "DESIGN.md tiene que empezar con una línea con ---"
    resto = texto[4:]
    cierre = resto.index("\n---\n")
    return yaml.safe_load(resto[:cierre]), resto[cierre + 5 :]


def quita_comentarios_css(texto: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", texto, flags=re.DOTALL)


def leer_variables_css() -> dict[str, str]:
    """Saca las variables de `:root`. Son los únicos colores del CSS."""
    sin_comentarios = quita_comentarios_css(CSS.read_text(encoding="utf-8"))
    bloque = re.search(r":root\s*\{(.*?)\}", sin_comentarios, flags=re.DOTALL)
    assert bloque, "estilos.css no tiene un bloque :root"
    return {
        nombre: valor.strip()
        for nombre, valor in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", bloque.group(1))
    }


def secciones_del_cuerpo(cuerpo: str) -> list[str]:
    return [coincidencia.strip() for coincidencia in re.findall(r"(?m)^##\s+(.+?)\s*$", cuerpo)]


# --------------------------------------------------------------------------
# Contraste, según la fórmula del W3C
# --------------------------------------------------------------------------


def a_rgb(color: str) -> tuple[int, int, int]:
    valor = color.strip().lstrip("#")
    if len(valor) == 3:
        valor = "".join(letra * 2 for letra in valor)
    assert len(valor) == 6, f"color no reconocido: {color}"
    return tuple(int(valor[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def luminancia(color: str) -> float:
    def canal(valor: int) -> float:
        proporcion = valor / 255
        return proporcion / 12.92 if proporcion <= 0.03928 else ((proporcion + 0.055) / 1.055) ** 2.4

    rojo, verde, azul = a_rgb(color)
    return 0.2126 * canal(rojo) + 0.7152 * canal(verde) + 0.0722 * canal(azul)


def contraste(uno: str, otro: str) -> float:
    claro, oscuro = sorted((luminancia(uno), luminancia(otro)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


def resuelve_referencia(valor, frontmatter: dict):
    """Convierte `{colors.primary}` en su valor. Deja lo demás igual."""
    if not isinstance(valor, str):
        return valor
    coincidencia = re.fullmatch(r"\{([\w.-]+)\}", valor.strip())
    if not coincidencia:
        return valor
    actual = frontmatter
    for parte in coincidencia.group(1).split("."):
        actual = actual[parte]
    return actual


# --------------------------------------------------------------------------
# El formato oficial
# --------------------------------------------------------------------------


class TestFormato:
    def test_el_fichero_existe(self):
        assert DESIGN.is_file(), "falta DESIGN.md en la raíz del proyecto"

    def test_el_frontmatter_es_yaml_valido(self):
        frontmatter, _ = leer_design_md()
        assert isinstance(frontmatter, dict)
        assert frontmatter["name"] == "CUE Digital"
        assert frontmatter["version"] == "alpha"

    def test_estan_las_ocho_secciones_oficiales(self):
        _, cuerpo = leer_design_md()
        assert secciones_del_cuerpo(cuerpo) == SECCIONES_OFICIALES

    def test_no_hay_secciones_repetidas(self):
        """Una sección repetida es un error para el validador oficial."""
        _, cuerpo = leer_design_md()
        encontradas = secciones_del_cuerpo(cuerpo)
        assert len(encontradas) == len(set(encontradas))

    def test_los_grupos_de_tokens_estan(self):
        frontmatter, _ = leer_design_md()
        for grupo in ("colors", "typography", "rounded", "spacing", "components"):
            assert frontmatter.get(grupo), f"falta el grupo {grupo}"

    def test_todas_las_referencias_apuntan_a_algo_que_existe(self):
        """Una referencia rota es el único error que da el validador oficial."""
        frontmatter, _ = leer_design_md()
        for nombre, componente in frontmatter["components"].items():
            for propiedad, valor in componente.items():
                if not (isinstance(valor, str) and valor.strip().startswith("{")):
                    continue
                try:
                    resuelve_referencia(valor, frontmatter)
                except (KeyError, TypeError):
                    pytest.fail(f"components.{nombre}.{propiedad} apunta a {valor}, que no existe")


# --------------------------------------------------------------------------
# El contrato y el código dicen lo mismo
# --------------------------------------------------------------------------


class TestContratoYCodigo:
    def test_cada_color_del_contrato_es_el_que_usa_el_css(self):
        frontmatter, _ = leer_design_md()
        variables = leer_variables_css()
        problemas: list[str] = []
        for variable, token in MAPA_DE_COLORES.items():
            en_css = variables.get(variable)
            en_contrato = frontmatter["colors"].get(token)
            if en_css is None:
                problemas.append(f"{variable} ya no está en el CSS")
            elif en_contrato is None:
                problemas.append(f"colors.{token} se ha quitado de DESIGN.md")
            elif en_css.lower() != str(en_contrato).lower():
                problemas.append(f"{variable} es {en_css} en el CSS y {en_contrato} en el contrato")
        assert not problemas, "El contrato y el CSS se han separado: " + "; ".join(problemas)

    def test_el_contrato_no_declara_colores_que_la_pantalla_no_use(self):
        frontmatter, _ = leer_design_md()
        declarados = set(frontmatter["colors"])
        mapeados = set(MAPA_DE_COLORES.values())
        sobran = declarados - mapeados
        assert not sobran, f"DESIGN.md declara colores que no existen en el CSS: {sorted(sobran)}"

    def test_el_css_no_declara_colores_que_el_contrato_no_conozca(self):
        variables = leer_variables_css()
        de_color = {n for n in variables if "color" in n or n in MAPA_DE_COLORES}
        sobran = de_color - set(MAPA_DE_COLORES)
        assert not sobran, f"El CSS tiene colores sin declarar en DESIGN.md: {sorted(sobran)}"

    def test_no_queda_ningun_color_suelto_fuera_de_root(self):
        """Todos los colores viven en `:root`. Si no, el contrato deja de ser cierto."""
        texto = quita_comentarios_css(CSS.read_text(encoding="utf-8"))
        bloque = re.search(r":root\s*\{.*?\}", texto, flags=re.DOTALL)
        assert bloque
        fuera = texto[: bloque.start()] + texto[bloque.end() :]
        sueltos = re.findall(r"#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)", fuera)
        assert not sueltos, f"Hay colores escritos a mano fuera de :root: {sueltos}"

    def test_las_medidas_duras_coinciden(self):
        """Los tres números que sostienen la usabilidad, en los dos ficheros."""
        frontmatter, _ = leer_design_md()
        variables = leer_variables_css()
        assert frontmatter["components"]["boton"]["height"] == variables["--toque"]
        assert frontmatter["typography"]["cuerpo"]["fontSize"] == variables["--letra"]
        assert frontmatter["rounded"]["xl"] == variables["--radio"]

    def test_la_letra_base_no_baja_de_18_pixeles(self):
        frontmatter, _ = leer_design_md()
        assert int(str(frontmatter["typography"]["cuerpo"]["fontSize"]).replace("px", "")) >= 18

    def test_ningun_boton_baja_de_64_pixeles_de_alto(self):
        frontmatter, _ = leer_design_md()
        # Los bordes no son botones: son líneas, y miden 2 o 3 px a propósito. El
        # resto de excepciones están justificadas en el propio contrato.
        no_son_botones = {"boton-letra", "paso", "paso-hecho", "foco"}
        for nombre, componente in frontmatter["components"].items():
            if nombre.startswith("borde-") or nombre in no_son_botones:
                continue
            alto = componente.get("height")
            if alto is None:
                continue
            assert int(str(alto).replace("px", "")) >= 48, f"{nombre} mide {alto} de alto"


# --------------------------------------------------------------------------
# Contraste: la regla que hace que se lea al sol
# --------------------------------------------------------------------------


class TestContraste:
    def test_ningun_par_de_fondo_y_texto_baja_del_minimo(self):
        frontmatter, _ = leer_design_md()
        problemas: list[str] = []
        for nombre, componente in frontmatter["components"].items():
            fondo = resuelve_referencia(componente.get("backgroundColor"), frontmatter)
            texto = resuelve_referencia(componente.get("textColor"), frontmatter)
            if not (isinstance(fondo, str) and isinstance(texto, str)):
                continue
            if not fondo.startswith("#") or not texto.startswith("#"):
                continue
            ratio = contraste(fondo, texto)
            if ratio < CONTRASTE_MINIMO:
                problemas.append(f"{nombre}: {ratio:.2f}:1 ({texto} sobre {fondo})")
        assert not problemas, "Por debajo de 4,5:1 no se lee al sol: " + "; ".join(problemas)

    def test_la_cabecera_se_lee_con_facilidad(self):
        """Es lo primero que se ve y no puede quedarse en el mínimo raspado."""
        frontmatter, _ = leer_design_md()
        cabecera = frontmatter["components"]["cabecera"]
        ratio = contraste(
            resuelve_referencia(cabecera["backgroundColor"], frontmatter),
            resuelve_referencia(cabecera["textColor"], frontmatter),
        )
        assert ratio >= 7.0, f"la cabecera se queda en {ratio:.2f}:1"


# --------------------------------------------------------------------------
# Las reglas que un agente tiene que leer
# --------------------------------------------------------------------------


class TestReglasDuras:
    def _texto(self) -> str:
        _, cuerpo = leer_design_md()
        return cuerpo

    def test_estan_escritas_las_medidas_minimas(self):
        texto = self._texto()
        assert "64 px" in texto, "no se dice en ninguna parte el alto mínimo de un botón"
        assert "18 px" in texto, "no se dice el tamaño mínimo de letra"

    def test_se_dice_que_no_hay_sombras(self):
        texto = self._texto()
        assert "no usa sombras" in texto.lower()
        assert "no:" in texto.lower()

    def test_estan_las_reglas_de_interaccion(self):
        texto = self._texto()
        for regla in (
            "una pregunta por pantalla",
            "LO MISMO QUE LA ÚLTIMA VEZ",
            "DESHACER",
            "inputmode",
        ):
            assert regla in texto, f"falta la regla: {regla}"

    def test_se_prohibe_escribir_textos_fuera_de_textos_py(self):
        texto = self._texto()
        assert "/api/interfaz" in texto
        assert "textos.py" in texto

    def test_estan_las_reglas_de_sin_cobertura(self):
        texto = self._texto()
        assert "sin cobertura" in texto.lower()
        assert "no tener cobertura en el campo no" in texto.lower()

    def test_se_dice_que_hay_que_pasar_los_tests(self):
        texto = self._texto()
        assert "pytest" in texto
        assert "node --test" in texto

    def test_el_documento_avisa_de_que_puede_nombrar_la_jerga(self):
        """Aquí SÍ aparecen las palabras prohibidas: para prohibirlas.

        Sin este aviso, alguien podría "arreglar" el documento borrándolas, y con
        ellas la lista de lo que no se puede decir.
        """
        texto = self._texto()
        assert "palabras prohibidas" in texto
        assert "no para el agricultor" in texto
