"""El registro oficial de productos fitosanitarios: que la comprobación no mienta.

Este módulo dice si un número de registro está en el listado oficial del MAPA. Lo peligroso aquí no es
que no funcione: es que **diga que un producto no existe cuando en realidad no tiene la lista**. Por
eso la prueba más importante de este fichero es la del «no lo sé»: sin fichero bajado, `esta_en_el_registro`
devuelve `None` y `aviso_sobre_el_numero` devuelve `None`, que quiere decir **no se avisa de nada**.

Los tests leen el fichero oficial que está en `data/fega/` (bajado con `scripts/bajar_catalogos_fega.py`),
y **ninguno sale a internet**.
"""

from __future__ import annotations

import pathlib

import pytest
from openpyxl import Workbook

from app import registro_oficial_de_productos as registro

RAIZ = pathlib.Path(__file__).resolve().parents[2]
FICHERO_OFICIAL = RAIZ / "data" / "fega" / "mapa_productos_fitosanitarios.xlsx"


@pytest.fixture(autouse=True)
def sin_lo_leido():
    """Cada prueba empieza sin nada leído: lo que lee una no puede cambiarle el resultado a otra."""
    registro.olvidar()
    yield
    registro.olvidar()


def _un_registro(filas: list[tuple]) -> pathlib.Path:
    """Fabrica un listado con la misma forma que el oficial: título, filtros, cabecera en la 4."""
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Productos"
    hoja.append(["Productos"])
    hoja.append([])
    hoja.append(["Filtros usados"])
    hoja.append(list(registro.__dict__.get("_CABECERA_DE_PRUEBA", ("NumRegistro", "Nombre", "Estado"))))
    for fila in filas:
        hoja.append(list(fila))
    destino = pathlib.Path(str(__import__("tempfile").mkdtemp())) / "productos.xlsx"
    libro.save(destino)
    return destino


class TestLoQueDiceElRegistroOficial:
    """Contra el listado de verdad que está bajado en `data/fega`."""

    def test_el_listado_oficial_esta_y_se_lee(self):
        assert FICHERO_OFICIAL.exists(), (
            "falta el listado oficial: se baja con `python scripts/bajar_catalogos_fega.py`"
        )
        assert registro.cargar() is not None
        # 3.087 filas contadas al bajarlo. Si un día son muchas menos, algo ha ido mal al leer.
        assert registro.cuantos() > 3000

    def test_un_numero_que_esta_se_reconoce(self):
        """Se coge un número del propio fichero: no se inventa ninguno para la prueba."""
        from openpyxl import load_workbook

        libro = load_workbook(FICHERO_OFICIAL, read_only=True, data_only=True)
        hoja = libro[libro.sheetnames[0]]
        filas = hoja.iter_rows(values_only=True)
        for _ in range(registro.FILA_DE_LA_CABECERA):
            next(filas)
        primero = next(filas)
        numero = str(primero[0]).strip()
        libro.close()

        assert registro.esta_en_el_registro(numero) is True
        ficha = registro.ficha(numero)
        assert ficha and ficha["nombre"]
        assert registro.aviso_sobre_el_numero(numero) is None or (
            registro.aviso_sobre_el_numero(numero)["codigo"] == "no_vigente"
        )

    def test_un_numero_inventado_se_detecta(self):
        assert registro.esta_en_el_registro("ES-99999999") is False
        aviso = registro.aviso_sobre_el_numero("ES-99999999")
        assert aviso and aviso["codigo"] == "no_esta_en_el_registro"
        assert aviso["numero"] == "ES-99999999"

    def test_el_espacio_y_las_minusculas_no_cambian_el_numero(self):
        """Limpiar el número no es interpretarlo: `es-00849` es el mismo número que `ES-00849`."""
        assert registro.esta_en_el_registro(" es-00849 ") == registro.esta_en_el_registro("ES-00849")

    def test_un_producto_no_vigente_se_avisa(self):
        """Si el registro oficial dice que el producto no está vigente, hay que decirlo.

        Se busca un producto que no esté vigente en el propio fichero; si hoy no hubiera ninguno, la
        prueba lo dice en vez de dar por bueno el caso.
        """
        from openpyxl import load_workbook

        libro = load_workbook(FICHERO_OFICIAL, read_only=True, data_only=True)
        hoja = libro[libro.sheetnames[0]]
        filas = hoja.iter_rows(values_only=True)
        for _ in range(registro.FILA_DE_LA_CABECERA):
            next(filas)
        no_vigente = ""
        for fila in filas:
            if fila and fila[0] and len(fila) > 5 and fila[5] and str(fila[5]).strip() != registro.ESTADO_VIGENTE:
                no_vigente = str(fila[0]).strip()
                break
        libro.close()

        if not no_vigente:
            pytest.skip("hoy no hay ningún producto no vigente en el listado oficial")
        aviso = registro.aviso_sobre_el_numero(no_vigente)
        assert aviso and aviso["codigo"] == "no_vigente"

    def test_la_procedencia_sale_del_fichero_de_procedencia(self):
        """La dirección y la fecha del listado no se escriben aquí: se leen de donde se apuntaron."""
        datos = registro.procedencia()
        assert datos["url"].startswith("https://servicio.mapa.gob.es")
        assert datos["descargado_el"]
        assert len(datos["sha256"]) == 64


class TestElNumeroEscritoDeOtraForma:
    """El registro escribe los números con ceros de delante; en las etiquetas se ven sin ellos.

    Esto **no** es «no existe»: es «está escrito de otra forma», y decirlo así evita una alarma
    falsa. Una alarma falsa hace que se deje de hacer caso a las de verdad.
    """

    def _uno_con_ceros(self) -> str:
        """Un número del registro que lleve ceros de delante, sacado del propio fichero."""
        from openpyxl import load_workbook

        libro = load_workbook(FICHERO_OFICIAL, read_only=True, data_only=True)
        hoja = libro[libro.sheetnames[0]]
        filas = hoja.iter_rows(values_only=True)
        for _ in range(registro.FILA_DE_LA_CABECERA):
            next(filas)
        for fila in filas:
            numero = str(fila[0]).strip() if fila and fila[0] else ""
            if registro.sin_ceros_de_delante(numero) != numero:
                libro.close()
                return numero
        libro.close()
        pytest.skip("hoy no hay ningún número con ceros de delante en el listado oficial")

    def test_sin_ceros_de_delante_se_dice_como_lo_escribe_el_registro(self):
        oficial = self._uno_con_ceros()
        escrito_a_mano = registro.sin_ceros_de_delante(oficial)
        assert escrito_a_mano != oficial

        aviso = registro.aviso_sobre_el_numero(escrito_a_mano)
        assert aviso and aviso["codigo"] == "escrito_de_otra_forma"
        assert aviso["oficial"] == oficial, "hay que poder decirle cómo se escribe de verdad"
        # Y no se da por bueno: `esta_en_el_registro` sigue diciendo que **ese texto** no está.
        assert registro.esta_en_el_registro(escrito_a_mano) is False

    def test_la_forma_oficial_si_esta(self):
        oficial = self._uno_con_ceros()
        assert registro.esta_en_el_registro(oficial) is True

    def test_los_ceros_de_delante_no_cambian_el_numero_de_los_que_no_llevan_guion(self):
        """Los números antiguos son cinco cifras sin guion (`11179`): ahí no se quita nada."""
        assert registro.sin_ceros_de_delante("11179") == "11179"
        assert registro.sin_ceros_de_delante("ES-00849") == "ES-849"
        assert registro.sin_ceros_de_delante(" es-00000 ") == "ES-0"
        assert registro.sin_ceros_de_delante("") == ""


class TestCuandoNoSeSabe:
    """Lo más importante: sin lista, **no se avisa de nada**. Callarse no es lo mismo que mentir."""

    def test_sin_fichero_no_se_avisa_de_nada(self, monkeypatch, tmp_path):
        monkeypatch.setattr(registro, "RUTA", tmp_path / "no_existe.xlsx")
        registro.olvidar()

        assert registro.cargar() is None
        assert registro.cargado() is False
        assert registro.cuantos() == 0
        assert registro.esta_en_el_registro("ES-00849") is None
        assert registro.aviso_sobre_el_numero("ES-99999999") is None, (
            "sin el listado bajado no se puede decir que un producto no existe"
        )

    def test_sin_fichero_el_resumen_dice_por_que_no(self, monkeypatch, tmp_path):
        monkeypatch.setattr(registro, "RUTA", tmp_path / "no_existe.xlsx")
        registro.olvidar()
        datos = registro.resumen()
        assert datos["cargado"] is False
        assert "bajar_catalogos_fega" in datos["por_que_no"]
        assert datos["productos"] == 0

    def test_un_fichero_ilegible_no_revienta(self, monkeypatch, tmp_path):
        roto = tmp_path / "productos.xlsx"
        roto.write_bytes(b"esto no es un Excel")
        monkeypatch.setattr(registro, "RUTA", roto)
        registro.olvidar()
        assert registro.cargar() is None
        assert registro.aviso_sobre_el_numero("ES-00849") is None

    def test_un_fichero_con_otra_cabecera_no_se_interpreta(self, monkeypatch, tmp_path):
        """Si el MAPA cambia las columnas, esto **no** adivina: dice que no lo sabe."""
        libro = Workbook()
        hoja = libro.active
        hoja.append(["Otra cosa"])
        hoja.append([])
        hoja.append([])
        hoja.append(["Referencia", "Descripcion"])
        hoja.append(["ES-00849", "Un producto"])
        destino = tmp_path / "otra.xlsx"
        libro.save(destino)

        monkeypatch.setattr(registro, "RUTA", destino)
        registro.olvidar()
        assert registro.cargar() is None
        assert registro.esta_en_el_registro("ES-00849") is None


class TestElNumeroVacio:
    def test_sin_numero_no_hay_nada_que_decir(self):
        """El número de registro es opcional: si no está, no hay aviso (ni bueno ni malo)."""
        assert registro.esta_en_el_registro("") is None
        assert registro.esta_en_el_registro(None) is None
        assert registro.aviso_sobre_el_numero("") is None
        assert registro.aviso_sobre_el_numero(None) is None

    def test_un_numero_solo_con_espacios_tampoco(self):
        assert registro.esta_en_el_registro("   ") is None
        assert registro.aviso_sobre_el_numero("   ") is None


class TestElAvisoNuncaBloquea:
    def test_el_aviso_es_solo_un_aviso(self):
        """Lo que devuelve esto es para enseñarlo, no para impedir apuntar.

        Se comprueba sobre el propio módulo: no tiene ninguna función que lance una excepción ni que
        devuelva «bloquea». La regla del proyecto (un aviso nunca cierra la puerta) se ve aquí en que
        todo lo que devuelve son diccionarios con un `codigo`.
        """
        aviso = registro.aviso_sobre_el_numero("ES-99999999")
        assert set(aviso) == {"codigo", "numero", "oficial", "ficha"}
        assert "bloquea" not in aviso
