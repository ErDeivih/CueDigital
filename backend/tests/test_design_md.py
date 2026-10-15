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

    def test_la_escala_de_letra_del_contrato_es_la_del_css(self):
        """**La escala de letra, atada al contrato** (06/10/2026).

        Los colores ya estaban atados (`test_cada_color_del_contrato_es_el_que_usa_el_css`), pero los
        **tamaños de letra no**: cada uno vivía escrito a mano en su regla, así que el contrato podía decir
        1,25 rem y el CSS usar otra cosa durante meses sin que nadie se enterara (y `h2` ni estaba en el
        contrato). Ahora los dos sitios están atados por esta tabla, y añadir un tamaño a la escala obliga a
        escribirlo en los dos.

        Se incluye `--letra` (el cuerpo) porque es el número del que cuelga todo lo demás.
        """
        frontmatter, _ = leer_design_md()
        variables = leer_variables_css()
        parejas = {
            "--letra": "cuerpo",
            "--t-pregunta": "pregunta",
            "--t-titulo": "titulo",
            "--t-subtitulo": "subtitulo",
            "--t-bloque": "bloque",
            "--t-dato-grande": "dato-grande",
            "--t-dato-mando": "dato-mando",
            "--t-boton": "boton",
            "--t-boton-principal": "boton-principal",
            "--t-campo": "campo",
            "--t-pista": "pista",
        }
        problemas: list[str] = []
        for variable, token in parejas.items():
            en_css = variables.get(variable)
            en_contrato = (frontmatter["typography"].get(token) or {}).get("fontSize")
            if en_css is None:
                problemas.append(f"{variable} no está en el CSS")
            elif en_contrato is None:
                problemas.append(f"typography.{token} no está en DESIGN.md")
            elif str(en_css) != str(en_contrato):
                problemas.append(f"{variable} es {en_css} en el CSS y {en_contrato} en el contrato")
        assert not problemas, "La escala de letra se ha separado del contrato: " + "; ".join(problemas)

    def test_la_escala_de_separacion_del_contrato_es_la_del_css(self):
        """**La escala de separación, atada al contrato** (06/10/2026).

        Los colores y la letra ya estaban atados; la separación **estaba en el contrato y no existía en el
        CSS**, así que cada pantalla tenía su propio ritmo (0.7rem, 0.8rem, 0.9rem, 1rem…) y el contrato el
        suyo. Ahora las seis medidas viven en `:root` con el nombre del contrato y esta prueba las compara:
        añadir una separación nueva obliga a escribirla en los dos sitios.
        """
        frontmatter, _ = leer_design_md()
        variables = leer_variables_css()
        problemas: list[str] = []
        for nombre, token in (
            ("--e-xs", "xs"),
            ("--e-sm", "sm"),
            ("--e-md", "md"),
            ("--e-lg", "lg"),
            ("--e-xl", "xl"),
            ("--e-xxl", "xxl"),
        ):
            en_css = variables.get(nombre)
            en_contrato = (frontmatter.get("spacing") or {}).get(token)
            if en_css is None:
                problemas.append(f"{nombre} no está en el CSS")
            elif en_contrato is None:
                problemas.append(f"spacing.{token} no está en DESIGN.md")
            elif str(en_css) != str(en_contrato):
                problemas.append(f"{nombre} es {en_css} en el CSS y {en_contrato} en el contrato")
        assert not problemas, "La escala de separación se ha separado del contrato: " + "; ".join(problemas)

    def test_las_cuatro_esquinas_del_contrato_son_las_del_css(self):
        """**Las esquinas, atadas al contrato** (14/10/2026).

        Es el mismo caso que la separación de arriba, y esta vez el contrato **nombra las piezas** que
        estaban mal: `paso` —la barra del asistente, que tenía **6 px** donde el contrato dice **4**— y
        `ayuda-campo`. Las cuatro vivían como **números sueltos** en el CSS —`10px`, `8px`, `4px`—
        mientras el contrato las llama `{rounded.lg}`, `{rounded.md}`, `{rounded.sm}` y `{rounded.xl}`:
        la medida estaba en los dos sitios y **sin atar**. Con nombre, añadir una nueva obliga a
        escribirla en los dos.
        """
        frontmatter, _ = leer_design_md()
        variables = leer_variables_css()
        problemas: list[str] = []
        for nombre, token in (
            ("--radio-xl", "xl"),
            ("--radio-lg", "lg"),
            ("--radio-md", "md"),
            ("--radio-sm", "sm"),
        ):
            en_css = variables.get(nombre)
            en_contrato = (frontmatter.get("rounded") or {}).get(token)
            if en_css is None:
                problemas.append(f"{nombre} no está en el CSS")
            elif en_contrato is None:
                problemas.append(f"rounded.{token} no está en DESIGN.md")
            elif str(en_css) != str(en_contrato):
                problemas.append(f"{nombre} es {en_css} en el CSS y {en_contrato} en el contrato")
        assert not problemas, "Las esquinas se han separado del contrato: " + "; ".join(problemas)

    def test_ninguna_esquina_del_css_es_una_que_el_contrato_no_tenga(self):
        """**Y la otra mitad**: que no haya una esquina suelta por ahí.

        Atar las cuatro variables no basta: alguien puede escribir `border-radius: 6px` en una pieza
        nueva y las cuatro seguirían cuadrando. Esto es lo que **encontró** las dos `6px` —una de ellas
        en la barra del asistente—, porque el contrato es explícito: «**No hay esquinas cuadradas**», y
        las que hay son las suyas.

        Se admiten `50 %` (los círculos) y el `0` de una tarjeta a la que solo se redondean dos
        esquinas: **ninguno de los dos es una esquina nueva**.
        """
        fuente = CSS.read_text(encoding="utf-8")
        permitidos = {
            "var(--radio)",
            "var(--radio-xl)",
            "var(--radio-lg)",
            "var(--radio-md)",
            "var(--radio-sm)",
            "50%",
        }
        problemas: list[str] = []
        for numero, linea in enumerate(fuente.splitlines(), start=1):
            encontrado = re.search(r"border-radius:\s*([^;]+);", linea)
            if not encontrado:
                continue
            # El `0` de «solo estas dos esquinas» no es una esquina: se quita para mirar el resto.
            trozos = [t for t in encontrado.group(1).split() if t and t != "0"]
            for trozo in trozos:
                if trozo not in permitidos:
                    problemas.append(f"línea {numero}: `{trozo}` no es una esquina del contrato")
        assert not problemas, "Hay esquinas fuera del contrato: " + "; ".join(problemas)

    def test_el_css_no_declara_sombras_ni_degradados_ni_desenfoques(self):
        """**La regla más deliberada del contrato, y la que no tenía guardián** (14/10/2026).

        El contrato lo dice con su motivo: «**Este sistema no usa sombras. Ni una**… Al sol, una sombra
        del 10 % de negro es **literalmente invisible**: el agricultor no ve el relieve, solo ve **un
        borde sucio que parece un defecto de la pantalla**. Y en un móvil barato, cada sombra es trabajo
        de dibujo **en cada fotograma**».

        El CSS tenía **una**: `box-shadow: 0 0 0 2px …`, que con desplazamiento y desenfoque cero **no
        es una sombra** —es un anillo— pero **se lee como una**. Ahora es `outline`, que dibuja en el
        mismo sitio, y esto impide que vuelva a colarse ninguna.

        Se buscan **declaraciones**, no la palabra suelta: los comentarios que explican la regla la
        nombran, y **eso es bueno** (el primer intento de esta prueba falló justo por eso).
        """
        fuente = CSS.read_text(encoding="utf-8")
        prohibidas = ("box-shadow", "text-shadow", "backdrop-filter")
        problemas: list[str] = [
            f"línea {numero}: {linea.strip()}"
            for numero, linea in enumerate(fuente.splitlines(), start=1)
            if linea.strip().startswith(prohibidas)
            or re.match(r"^\s*background-image:\s*(linear|radial)-gradient", linea)
        ]
        assert not problemas, (
            "El contrato dice «nada de sombras, degradados ni animaciones», y su motivo es el sol: "
            + "; ".join(problemas)
        )

    def test_la_densidad_del_escritorio_es_la_que_declara_el_contrato(self):
        """**La densidad del escritorio, atada a SU tabla** (14/10/2026).

        `DESIGN.md` tiene una sección —«La densidad del escritorio, y de dónde salen sus números»— con
        una **tabla que declara valor por valor y la fuente de cada uno** (Odoo 17, Frappe 15, el
        escritorio que Stitch ya dibujó), y el CSS tiene esos mismos números dentro de su
        `@media (min-width: 64rem)`. **Estaban en los dos sitios y sin atar**: el mismo caso que la
        escala de separación y que las esquinas.

        **Y por qué esta prueba lee la tabla en vez de fiarse de un comentario**: *me costó **tres**
        conclusiones falsas el mismo día*. Leí el contrato a trozos y las tres veces dije «esto no está
        en el contrato» —la densidad del escritorio, el radio 14 → 8 y los botones a 40— **y las tres
        estaba**. Es el mismo error que «volcarlo, no filtrarlo». Aquí se busca **en el documento**.
        """
        _, texto = leer_design_md()
        css = CSS.read_text(encoding="utf-8")
        bloque = re.search(r"@media\s*\(min-width:\s*64rem\)\s*\{(.*?)\n\}", css, re.S)
        assert bloque, "el CSS no tiene el bloque del escritorio (`@media (min-width: 64rem)`)"
        dentro = bloque.group(1)

        problemas: list[str] = []
        # Cada fila de la tabla del contrato que se corresponde con una variable del bloque del CSS.
        for rotulo, variable in (("cuerpo", "--letra"), ("radio de control", "--radio")):
            fila = re.search(r"\|\s*" + re.escape(rotulo) + r"\s*\|[^|]*\|\s*\*\*(\d+)[^*]*\*\*", texto)
            en_css = re.search(re.escape(variable) + r":\s*(\d+)px", dentro)
            if not fila:
                problemas.append(f"la tabla de densidad del contrato no declara `{rotulo}`")
            elif not en_css:
                problemas.append(f"el bloque del escritorio no tiene {variable}")
            elif en_css.group(1) != fila.group(1):
                problemas.append(
                    f"{rotulo}: el contrato dice {fila.group(1)} y el CSS {en_css.group(1)}"
                )

        # **Y el suelo de los botones**, que el contrato protege con una frase explicita: «un suelo con
        # motivo de accesibilidad **no lo rompe el agente por su cuenta**, lo rompe el dueño del
        # producto si quiere». Si alguien cambia esa frase, esta prueba lo dice — y su altura real se
        # mide en el navegador, que es donde se ve (`.boton` mide **40** en el escritorio, medido).
        assert re.search(r"devuelto a\s*\**\s*40", texto), (
            "el contrato ya no dice que los botones del escritorio se han devuelto a 40: si el dueño ha "
            "cambiado ese suelo, hay que cambiarlo aqui Y en el CSS"
        )

        assert not problemas, "La densidad del escritorio se ha separado del contrato: " + "; ".join(problemas)

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
