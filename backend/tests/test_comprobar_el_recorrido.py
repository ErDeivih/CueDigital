"""El recorrido del encargo: que el guion esté, que recorra **la cadena entera** y que pueda fallar.

**Por qué existe este fichero** (07/10/2026). La revisión funcional del recorrido encontró el hueco de
fondo: **ninguna suite recorría la cadena entera** —Inicio → Tierras → ficha → registrar trabajo →
historial—, así que un defecto que solo se ve andando (como el 422 al corregir un trabajo, o un botón que
no llevaba a ninguna parte) podía estar roto con todas las suites en verde.

Estos tests **no abren ningún navegador** (eso es una comprobación a mano, como el guion del navegador y
`humo.py`). Lo que comprueban es lo que sí se puede comprobar sin navegador:

1. Que el guion está, se puede leer y dice para qué sirve.
2. Que recorre **los pasos del encargo**, uno por uno, y con la explotación de 64 tierras (no con una
   cuenta vacía: es la única forma de que el recorrido se parezca a lo que hace el agricultor).
3. Que **puede fallar**: cuenta las comprobaciones, guarda los fallos con su frase y sale con error.
4. Que las capturas se guardan **fuera** de la aplicación.
"""

from __future__ import annotations

import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[2]
GUION = RAIZ / "backend" / "scripts" / "comprobar_el_recorrido.py"


def _fuente() -> str:
    return GUION.read_text(encoding="utf-8")


class TestElGuionDelRecorrido:
    def test_esta_y_dice_para_que_sirve(self):
        assert GUION.exists(), "no está el guion del recorrido"
        fuente = _fuente()
        assert "Inicio" in fuente and "Tierras" in fuente, "no dice qué recorre"
        assert "add_argument" not in fuente or "sys.argv" in fuente, "no deja pasarle la dirección"

    def test_usa_la_explotacion_de_64_tierras_y_no_una_cuenta_vacia(self):
        """Las capturas de una explotación vacía no dejan revisar tablas, nombres largos ni pagos: el
        encargo lo dijo con estas palabras. El recorrido se hace con las 64 tierras de verdad."""
        fuente = _fuente()
        assert "from datos_representativos import preparar" in fuente, (
            "el recorrido no usa la explotación de 64 tierras: con una cuenta vacía no se revisa nada"
        )
        assert "preparar(DIRECCION)" in fuente, "no prepara el escenario antes de andar"

    def test_recorre_los_pasos_del_encargo(self):
        """Cada paso, con la acción que lo da. Si alguien quita uno, esto lo dice."""
        fuente = _fuente()
        pasos = {
            "abrir las tierras desde Inicio": "#menu-tierras",
            "buscar la tierra en la lista": "buscar_tierra_mis_cosas",
            "abrir su ficha": "elegir-fila",
            "entrar en su historial": "tierra-historia",
            "planificar un trabajo": "trabajo-planificar",
            "volver a la lista de tierras": "mis-cosas",
        }
        faltan = [nombre for nombre, aguja in pasos.items() if aguja not in fuente]
        assert faltan == [], f"el recorrido no da estos pasos: {faltan}"

    def test_puede_fallar_y_lo_dice(self):
        """Una comprobación que no puede fallar no comprueba nada: esto exige el mecanismo."""
        fuente = _fuente()
        assert "def comprobar(" in fuente, "no hay forma de comprobar nada"
        assert "FALLOS.append(" in fuente, "los fallos no se guardan"
        assert "return 1 if FALLOS else 0" in fuente, "el guion no sale con error cuando algo falla"
        assert "Comprobaciones:" in fuente, "no dice cuántas comprobaciones ha hecho"

    def test_las_capturas_no_se_guardan_dentro_de_la_aplicacion(self):
        fuente = _fuente()
        assert "captura(" in fuente, "no guarda capturas de los pasos"
        assert "Temp" in fuente or "TEMP" in fuente, (
            "las capturas se guardan fuera de la aplicación (una captura no es un fichero del programa)"
        )
        assert "web/" not in fuente.split("CARPETA")[0], "la carpeta de capturas apunta dentro de la web"
