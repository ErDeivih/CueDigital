"""Corregir y borrar las tierras: la parcela, su cultivo declarado y los grupos (ronda 92).

LO QUE SE PRUEBA AQUÍ, Y POR QUÉ

David lo pidió con estas palabras: «recuerda también dejar borrar las cosas que introduzca porque
puede que me equivoque, o modificar también». La ronda 91 lo hizo para los apuntes del cuaderno
(tratamientos, abonos, labores y cosechas) y **las tierras se quedaron fuera**, que es justo donde
se equivoca uno primero y más veces: la referencia copiada a medias, las hectáreas que no son, la
tierra que ya no se lleva y sigue en la lista, el cultivo declarado en la parcela de al lado.

Estas pruebas defienden las cinco cosas que hacen que corregir y borrar una tierra sea de fiar y no
un agujero por el que se cuela un cuaderno que dice lo que no es:

  1. **Corregir cambia esa tierra, no da de alta otra.** El identificador sigue siendo el mismo: de
     él cuelgan todos los apuntes que se hicieron en ella. Dos tierras donde había una es un
     cuaderno que dice que se trabajó en dos sitios.
  2. **Lo que había no se pierde**: queda en la auditoría, campo por campo (`correcciones`).
  3. **Las reglas son las mismas que al dar de alta la tierra**, porque es la misma función. Una
     corrección rechazada no deja la tierra a medias.
  4. **Una tierra con apuntes encima NO se borra**: se contesta 409 diciendo cuántos son y qué
     hacer. Borrarla destruiría en silencio el cuaderno de campo, que es lo único que este programa
     no puede hacer.
  5. **El cultivo declarado se puede cambiar y se puede quitar**, y los grupos se pueden corregir y
     deshacer —salvo los que ya se han usado para apuntar, porque esos apuntes se quedarían sin
     decir dónde se hizo el trabajo—.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app import catalogos, models, textos
from app.schemas import GrupoEntrada, GrupoSalida, ParcelaEntrada, ParcelaSalida

# La respuesta de verdad del SIGPAC que está guardada en el repositorio. Los tests **no salen a
# internet** (ver `test_sigpac.py`): un test que depende de que el FEGA conteste es una lotería.
RUTA_DATOS = Path(__file__).resolve().parents[2] / "data" / "sigpac"


def _auditoria(db, entidad: str, entidad_id: int, accion: str):
    """El rastro que ha dejado una corrección o un borrado."""
    return list(
        db.scalars(
            select(models.Auditoria).where(
                models.Auditoria.entidad == entidad,
                models.Auditoria.entidad_id == entidad_id,
                models.Auditoria.accion == accion,
            )
        )
    )


def _una_tierra(**cambios) -> dict:
    """Una tierra completa y correcta, a la que se le cambia lo que pruebe cada test.

    Son los mismos datos que manda el alta (`tests.conftest.crear_parcela`), escritos aquí porque
    la corrección necesita **el cuerpo entero**: `PUT /api/parcelas/{id}` acepta exactamente el
    mismo esquema que el alta, y esa es la gracia.
    """
    datos = {
        "alias": "El Prado",
        "ref_sigpac": "37-455-12-3",
        "superficie_ha": 2.43,
        "superficie_oficial": True,
        "sistema": "secano",
        "uso_sigpac": "Labor secano",
        "municipio": "Peñaranda de Bracamonte",
        "provincia": "Salamanca",
    }
    datos.update(cambios)
    return datos


def _las_tierras(cliente, cabeceras) -> list[dict]:
    return cliente.get("/api/parcelas", headers=cabeceras).json()


def _la_ficha_de_la_tierra(cliente, cabeceras, parcela_id) -> dict:
    """La fila de esa tierra en «Qué hay sembrado» (`GET /api/cultivos`)."""
    listado = cliente.get("/api/cultivos", headers=cabeceras).json()
    return [fila for fila in listado["parcelas"] if fila["parcela_id"] == parcela_id][0]


@pytest.fixture
def servidor_sigpac(monkeypatch):
    """Un SIGPAC de mentiras que devuelve la respuesta de verdad guardada en el repositorio.

    Es el mismo montaje que usa `test_sigpac.py`, y aquí hace falta por un motivo concreto: la
    superficie del recinto entero (`superficie_sigpac_ha`) **solo la trae el conector**, y hay que
    comprobar que corregir esa tierra no se la lleva por delante.
    """
    import httpx

    crudo = json.loads((RUTA_DATOS / "recinto_de_ejemplo.json").read_text(encoding="utf-8"))

    class RespuestaFalsa:
        status_code = 200
        text = json.dumps(crudo)

        def raise_for_status(self):
            return None

    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: RespuestaFalsa())


@pytest.fixture
def dos_tierras(crear_parcela):
    """Dos tierras de la misma finca, que es lo mínimo para poder juntarlas en un grupo."""
    return [
        crear_parcela(alias="El Prado"),
        crear_parcela(alias="La Vega", ref_sigpac="37-455-12-4", superficie_ha=3.0),
    ]


def _juntar(cliente, cabeceras, parcelas, nombre="La cebada", **cambios) -> dict:
    respuesta = cliente.post(
        "/api/grupos",
        headers=cabeceras,
        json={
            "nombre": nombre,
            "parcela_ids": [parcela["id"] for parcela in parcelas],
            **cambios,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _los_grupos(cliente, cabeceras) -> list[dict]:
    return cliente.get("/api/grupos", headers=cabeceras).json()


def _la_forma_de_un_recinto_de_verdad() -> str:
    """El WKT de un recinto real del SIGPAC (el que está descargado con los catálogos).

    Se lee del fichero y no se escribe a mano, por lo mismo que en `test_dibujo_de_la_parcela.py`:
    una forma inventada no dice si el dibujo es el de verdad.
    """
    datos = json.loads((RUTA_DATOS / "recinto_de_ejemplo.json").read_text(encoding="utf-8"))
    return datos[0]["wkt"]


def _enganches_guardados(db) -> int:
    """Cuántas filas quedan en la tabla que engancha cada grupo con sus tierras.

    Se mira la tabla de verdad y no lo que devuelve la API a propósito: una fila suelta que apunte a
    una tierra que ya no existe no se ve en ninguna lista (la consulta la descarta) y, en cambio,
    deja basura dentro del cuaderno.
    """
    return db.scalar(select(func.count()).select_from(models.grupo_parcela))


class TestCorregirUnaTierra:
    def test_los_datos_cambiados_son_los_que_se_guardan(self, cliente, cuenta, parcela):
        respuesta = cliente.put(
            f"/api/parcelas/{parcela['id']}",
            headers=cuenta["cabeceras"],
            json=_una_tierra(alias="El Prado de arriba", superficie_ha=3.1),
        )

        assert respuesta.status_code == 200, respuesta.text
        corregida = respuesta.json()
        assert corregida["id"] == parcela["id"]
        assert corregida["alias"] == "El Prado de arriba"
        assert corregida["superficie_ha"] == 3.1

    def test_corregir_no_da_de_alta_otra_tierra(self, cliente, cuenta, parcela):
        """El identificador es el mismo y en la lista sigue habiendo una tierra, no dos.

        No es un detalle de estilo: de esa tierra cuelgan los tratamientos, los abonos y las labores
        que se hicieron en ella, y su identificador es el mismo que se manda a la Junta. Si corregir
        diera de alta otra, la tierra con los apuntes se quedaría con los datos malos.
        """
        cliente.put(
            f"/api/parcelas/{parcela['id']}",
            headers=cuenta["cabeceras"],
            json=_una_tierra(superficie_ha=3.1),
        )

        tierras = _las_tierras(cliente, cuenta["cabeceras"])
        assert [tierra["id"] for tierra in tierras] == [parcela["id"]]
        assert tierras[0]["superficie_ha"] == 3.1

    def test_lo_que_habia_queda_en_el_rastro(self, cliente, cuenta, db_sesion, parcela):
        """El cuaderno enseña lo nuevo y el programa sí sabe qué decía antes."""
        cliente.put(
            f"/api/parcelas/{parcela['id']}",
            headers=cuenta["cabeceras"],
            json=_una_tierra(alias="El Prado de arriba"),
        )

        rastro = _auditoria(db_sesion, "parcela", parcela["id"], "corregir")
        assert len(rastro) == 1
        assert rastro[0].datos["alias"] == ["El Prado", "El Prado de arriba"]
        assert rastro[0].fecha is not None

    def test_lo_que_el_alta_calcula_sola_se_vuelve_a_calcular(
        self, cliente, cuenta, db_sesion, crear_parcela, monkeypatch
    ):
        """La zona de nitratos la deduce el listado oficial, y al corregir se vuelve a mirar.

        Se carga el listado de verdad —el de IDECyL, que ya está en el repositorio— y se corrige el
        pueblo a uno que no está en zona. Si la corrección copiara el valor que ya había, la tierra
        se quedaría marcada como zona de nitratos para siempre, y el agricultor tendría reglas de
        abono que no le tocan.
        """
        from scripts import bajar_zonas_vulnerables_cyl as fuente

        monkeypatch.setattr(catalogos, "_RUTA_ZV_POR_DEFECTO", fuente.CSV)
        try:
            catalogos.cargar_zonas_vulnerables()
            parcela = crear_parcela(
                municipio="Peñaranda de Bracamonte",
                provincia="Salamanca",
                zona_vulnerable_nitratos=None,
            )
            assert parcela["zona_vulnerable_nitratos"] is True, "el listado dice que ahí sí"

            corregida = cliente.put(
                f"/api/parcelas/{parcela['id']}",
                headers=cuenta["cabeceras"],
                json=_una_tierra(provincia="Burgos"),
            ).json()

            assert corregida["zona_vulnerable_nitratos"] is False, "ahí el listado dice que no"
        finally:
            catalogos.olvidar_zonas_vulnerables()

        # Y en el rastro se ve que la cuenta se ha vuelto a hacer.
        rastro = _auditoria(db_sesion, "parcela", parcela["id"], "corregir")
        assert rastro[0].datos["zona_vulnerable_nitratos"] == [True, False]

    def test_una_tierra_traida_del_sigpac_no_pierde_su_superficie_oficial(
        self, cliente, cuenta, servidor_sigpac
    ):
        """Hay un dato que el formulario no pregunta y que no se puede perder al corregir.

        La superficie del recinto entero (`superficie_sigpac_ha`) la trae el conector del SIGPAC y
        la pide por su nombre la hoja 2.1 del cuaderno de la Junta. Como no viaja en el formulario,
        guardar «lo que llega sin más» al corregir la borraría sin decir nada: es el mismo cuidado
        que ya se tuvo con el ecorregimen al corregir el cultivo declarado.
        """
        parcela = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cuenta["cabeceras"],
            json={"ref_sigpac": "37-22-0-0-501-427-1", "alias": "El Prado", "sistema": "secano"},
        ).json()
        assert parcela["superficie_sigpac_ha"] > 0

        corregida = cliente.put(
            f"/api/parcelas/{parcela['id']}",
            headers=cuenta["cabeceras"],
            json=_una_tierra(alias="El Prado de arriba"),
        ).json()

        assert corregida["alias"] == "El Prado de arriba"
        assert corregida["superficie_sigpac_ha"] == parcela["superficie_sigpac_ha"]

    def test_una_correccion_que_no_cumple_las_reglas_se_rechaza(self, cliente, cuenta, parcela):
        """Corregir no puede ser la puerta de atrás para meter lo que el alta no deja."""
        respuesta = cliente.put(
            f"/api/parcelas/{parcela['id']}",
            headers=cuenta["cabeceras"],
            json=_una_tierra(sistema="invernadero", alias="Lo que sea", superficie_ha=99.0),
        )

        assert respuesta.status_code == 422
        assert respuesta.json()["detail"] == textos.mensaje("V23_sistema_desconocido")
        # Y la tierra sigue como estaba: una corrección rechazada no la deja a medias.
        guardada = cliente.get(
            f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert guardada["sistema"] == "secano"
        assert guardada["alias"] == "El Prado"
        assert guardada["superficie_ha"] == 2.43

    def test_una_tierra_sin_nombre_no_se_queda_asi(self, cliente, cuenta, parcela):
        """El nombre es lo único que hace falta de verdad: sin él no se reconoce la tierra."""
        respuesta = cliente.put(
            f"/api/parcelas/{parcela['id']}",
            headers=cuenta["cabeceras"],
            json=_una_tierra(alias=""),
        )

        assert respuesta.status_code == 422
        assert cliente.get(
            f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"]
        ).json()["alias"] == "El Prado"

    def test_una_tierra_con_forma_no_pierde_el_dibujo_al_corregirla(
        self, cliente, cuenta, db_sesion, crear_parcela
    ):
        """La forma del trozo no viaja en la respuesta, así que el formulario no puede devolverla.

        `ParcelaSalida` manda la línea que se pinta (`dibujo`) y el centro, **no el WKT entero**, y
        eso es a propósito: el WKT son cientos de caracteres por tierra y al móvil no le hacen falta.
        Pero significa que el formulario de corregir **no tiene la forma**, así que si la corrección
        copiara lo que llega sin más, ponerle el nombre bueno a una tierra le borraría el dibujo y el
        mapa se quedaría sin el trozo. Es el mismo fallo que se arregló con la máquina de la cosecha
        en la ronda 91 (el navegador lo mandaba, el esquema lo tiraba y se perdía sin decir nada), y
        no puede volver a pasar con las tierras.
        """
        parcela = crear_parcela(alias="El Prado", geometria=_la_forma_de_un_recinto_de_verdad())
        assert parcela["dibujo"], "el alta guarda la forma y la devuelve dibujada"
        assert parcela["centro"], "y el centro, que es donde se abre el mapa"

        corregida = cliente.put(
            f"/api/parcelas/{parcela['id']}",
            headers=cuenta["cabeceras"],
            json=_una_tierra(alias="El Prado de arriba"),
        ).json()

        assert corregida["alias"] == "El Prado de arriba"
        assert corregida["dibujo"] == parcela["dibujo"], "el mapa se ha quedado sin el trozo"
        assert corregida["centro"] == parcela["centro"]
        # Y el rastro no puede decir que la forma ha cambiado, porque no ha cambiado.
        rastro = _auditoria(db_sesion, "parcela", parcela["id"], "corregir")
        assert "geometria" not in rastro[0].datos

    def test_una_tierra_sin_forma_sigue_sin_forma(self, cliente, cuenta, crear_parcela):
        """Y al revés: corregir no puede inventarle una forma a una tierra apuntada a mano.

        Un cuadro inventado parecería su parcela, que es peor que no tener dibujo.
        """
        parcela = crear_parcela(alias="Sin forma")
        assert parcela["dibujo"] is None

        corregida = cliente.put(
            f"/api/parcelas/{parcela['id']}",
            headers=cuenta["cabeceras"],
            json=_una_tierra(alias="Sin forma, pero con el nombre bueno"),
        ).json()

        assert corregida["dibujo"] is None
        assert corregida["centro"] is None

    def test_la_fecha_en_que_se_apunto_la_tierra_no_cambia(
        self, cliente, cuenta, db_sesion, parcela
    ):
        """«Cuándo se apuntó» no es un dato que se corrija, y hay que cuidarlo a mano.

        `correcciones` protege las columnas que no se corrigen nunca, y en su lista está
        `creado_en`; la de la parcela se llama `creada_en` —en femenino, como «la parcela»—, así que
        se le escapa. Sin copiarla, corregir el nombre de una tierra le pondría la fecha de alta en
        blanco y la base de datos no lo admitiría: la corrección fallaría con un fallo del programa
        en vez de decir nada.
        """
        antes = db_sesion.scalar(
            select(models.Parcela).where(models.Parcela.id == parcela["id"])
        ).creada_en
        assert antes is not None

        respuesta = cliente.put(
            f"/api/parcelas/{parcela['id']}",
            headers=cuenta["cabeceras"],
            json=_una_tierra(alias="El Prado de arriba"),
        )
        assert respuesta.status_code == 200, respuesta.text

        db_sesion.expire_all()
        despues = db_sesion.scalar(
            select(models.Parcela).where(models.Parcela.id == parcela["id"])
        ).creada_en
        assert despues == antes

    def test_la_tierra_de_otra_finca_no_se_toca(self, cliente, cuenta, crear_cuenta, parcela):
        """Corregir la tierra de otro agricultor contesta lo mismo que si no existiera."""
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.put(
            f"/api/parcelas/{parcela['id']}",
            headers=otro["cabeceras"],
            json=_una_tierra(alias="Mía"),
        )

        assert respuesta.status_code == 404
        assert _las_tierras(cliente, cuenta["cabeceras"])[0]["alias"] == "El Prado"

    def test_sin_entrar_no_se_corrige_nada(self, cliente, cuenta, parcela):
        respuesta = cliente.put(f"/api/parcelas/{parcela['id']}", json=_una_tierra())
        assert respuesta.status_code == 401


class TestBorrarUnaTierra:
    def test_se_borra_cuando_no_depende_nada_de_ella(self, cliente, cuenta, parcela):
        respuesta = cliente.delete(
            f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 200, respuesta.text
        assert _las_tierras(cliente, cuenta["cabeceras"]) == []
        assert (
            cliente.get(
                f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 404
        )

    def test_lo_borrado_queda_escrito_en_el_rastro(self, cliente, cuenta, db_sesion, parcela):
        """El cuaderno no la enseña, y el programa sí sabe qué había y qué día se borró."""
        cliente.delete(f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"])

        rastro = _auditoria(db_sesion, "parcela", parcela["id"], "borrar")
        assert len(rastro) == 1
        assert rastro[0].datos["alias"] == "El Prado"
        assert rastro[0].datos["superficie_ha"] == 2.43
        assert rastro[0].fecha is not None

    def test_borrar_dos_veces_no_rompe_nada(self, cliente, cuenta, parcela):
        assert (
            cliente.delete(
                f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 200
        )
        assert (
            cliente.delete(
                f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 404
        )

    def test_una_tierra_con_apuntes_encima_no_se_borra(
        self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        """Borrar la tierra donde se hizo un tratamiento destruiría el cuaderno en silencio."""
        cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        )

        respuesta = cliente.delete(
            f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == textos.mensaje_con_cuenta("B2_tierra_con_apuntes", 1)
        # Y sigue ahí, con su apunte dentro.
        assert (
            cliente.get(
                f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 200
        )
        assert len(cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()) == 1

    def test_el_mensaje_dice_cuantas_cosas_dependen_y_que_hacer(
        self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento
    ):
        """El «no» con el número delante y con las dos salidas: sin eso deja al agricultor parado.

        Se apuntan tres cosas de tres tablas distintas (un tratamiento, una labor y el cultivo
        declarado) para comprobar que la cuenta **las suma todas** y no solo una.
        """
        cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        )
        cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "labrar",
                "fecha": "2026-03-15",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
            },
        )
        cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={"campana_id": campana["id"], "especie": "Cebada", "sistema": "secano"},
        )

        respuesta = cliente.delete(
            f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 409
        detalle = respuesta.json()["detail"]
        assert "3 apuntes" in detalle, detalle
        assert "Bórralos o corrígelos antes" in detalle, detalle
        assert "corrige la tierra" in detalle, detalle

    def test_lo_que_depende_de_ella_sigue_ahi(self, cliente, cuenta, campana, parcela, producto, nuevo_tratamiento):
        """Un 409 no puede dejar el cuaderno a medias: la tierra y su apunte siguen donde estaban."""
        cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        )

        cliente.delete(f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"])

        apuntes = cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()
        assert len(apuntes) == 1
        assert apuntes[0]["parcela_id"] == parcela["id"]

    def test_el_cultivo_declarado_tambien_cuenta(self, cliente, cuenta, campana, parcela):
        """Una tierra con el cultivo declarado tampoco se borra sin más.

        Es una dependencia de verdad, no un detalle: esa fila se iría con la tierra y el cuaderno de
        la Junta se quedaría sin decir qué había sembrado ese año.
        """
        cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos",
            headers=cuenta["cabeceras"],
            json={"campana_id": campana["id"], "especie": "Cebada", "sistema": "secano"},
        )

        respuesta = cliente.delete(
            f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"]
        )

        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == textos.mensaje_con_cuenta("B2_tierra_con_apuntes", 1)

    def test_la_tierra_de_otra_finca_no_se_borra(self, cliente, cuenta, crear_cuenta, parcela):
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.delete(
            f"/api/parcelas/{parcela['id']}", headers=otro["cabeceras"]
        )

        assert respuesta.status_code == 404
        assert len(_las_tierras(cliente, cuenta["cabeceras"])) == 1

    def test_sin_entrar_no_se_borra_nada(self, cliente, cuenta, parcela):
        assert cliente.delete(f"/api/parcelas/{parcela['id']}").status_code == 401

    def test_una_tierra_de_un_grupo_se_puede_borrar_y_el_grupo_se_queda_sin_ella(
        self, cliente, cuenta, db_sesion, dos_tierras
    ):
        """El grupo **no es el cuaderno**: lo que se va es la tierra, no la agrupación.

        Se prueba a propósito, porque es una decisión y no un descuido: la fila que engancha el
        grupo con esa tierra desaparece con ella (la base de datos la borra en cascada,
        `ondelete="CASCADE"` en `models`), y el grupo se queda con las tierras que le quedan.
        """
        grupo = _juntar(cliente, cuenta["cabeceras"], dos_tierras)

        assert (
            cliente.delete(
                f"/api/parcelas/{dos_tierras[0]['id']}", headers=cuenta["cabeceras"]
            ).status_code
            == 200
        )

        assert _los_grupos(cliente, cuenta["cabeceras"])[0]["parcela_ids"] == [
            dos_tierras[1]["id"]
        ]
        assert grupo["parcela_ids"] == [tierra["id"] for tierra in dos_tierras], (
            "el grupo sí las tenía las dos cuando se juntó"
        )
        assert _enganches_guardados(db_sesion) == 1, "no queda la fila de la tierra que se fue"


class TestLoQueSeCuentaAntesDeBorrar:
    """La cuenta de lo que depende de una tierra se saca de la base de datos, y esto la mantiene honesta."""

    def test_las_tablas_que_apuntan_a_una_tierra_se_cuentan_todas(self):
        """Las ocho que hay hoy, por su nombre.

        Si mañana se añade un apunte nuevo que se hace en una tierra —como se añadieron las ventas y
        los análisis—, esta prueba falla y obliga a decidir: o cuenta como dependencia, o hay que
        escribir por qué no. Sin ella, la cuenta se quedaría corta en silencio y borrar una tierra
        reventaría al guardar (la base de datos no deja un apunte sin su tierra) o, peor, se llevaría
        el apunte por delante.

        **La octava es la versión del recinto** (T05, 02/10/2026), y sí cuenta como dependencia: es
        la ficha de qué era esa tierra en una campaña y de dónde se supo, así que una tierra que
        desaparece se lleva por delante la historia de su recinto. La consecuencia, dicha entera: a
        una tierra con versiones importadas **no se le puede dar al botón de borrar**; lo que se
        hace es corregirla, que es lo que de verdad quiere quien se ha equivocado al escribirla, y
        el mensaje que sale (`B2_tierra_con_apuntes`) es el mismo que para cualquier otro apunte.

        **Y la novena es la siembra de una semilla** (T10, 03/10/2026), que entra por el motivo que
        este mismo docstring pide: una siembra es un apunte que se hace **en una tierra** («en esta
        tierra sembré esta semilla»), así que cuenta como dependencia. Una tierra con siembras
        apuntadas no se puede borrar —se corrige— y el mensaje que sale es el mismo que para
        cualquier otro apunte (`B2_tierra_con_apuntes`). Lo que **no** se ha hecho es copiar la
        superficie de la tierra a la siembra ni al revés: son dos números distintos.

        **Y las tres de las cuentas** (T13, E7, 05/10/2026), que entran por lo mismo: `gastos` cuando
        el gasto ya dice de qué tierra es (el gasóleo de esa parcela), `inversiones_de_la_finca`
        cuando la compra se imputa a una tierra (una nave, un pozo) y `repartos_de_coste` cuando un
        trozo de un gasto o de una inversión se ha llevado **a esa tierra**. Las tres son
        dependencias de verdad: sin la tierra, esas filas se quedarían sin decir a qué se referían (y
        la base de datos no las admitiría). Así que una tierra con cuentas apuntadas **se corrige,
        no se borra**, con el mismo mensaje que las demás.

        **Y las dos del trabajo planificado** (T15, E9, 05/10/2026): `trabajos_previstos` (un plan se
        piensa para una tierra) y `lineas_de_trabajo_previsto` (cada línea del plan dice de qué tierra
        es el insumo). Las dos son dependencias de verdad por el mismo motivo que las demás.
        """
        from app.routers import parcelas

        assert [modelo.__tablename__ for modelo in parcelas._tablas_que_apuntan_a("parcela_id")] == [
            "analiticas",
            "fertilizaciones",
            "gastos",
            "inversiones_de_la_finca",
            "labores",
            "lineas_de_trabajo_previsto",
            "parcela_cultivos",
            "planes_abonado",
            "repartos_de_coste",
            "siembras",
            "trabajos_previstos",
            "tratamientos",
            "ventas_de_cosecha",
            "versiones_de_recinto",
        ]

    def test_las_tablas_que_apuntan_a_un_grupo_se_cuentan_todas(self):
        """Y las seis que apuntan a un grupo: los apuntes que se hicieron sobre él.

        **La sexta es el trabajo planificado** (T15, E9, 05/10/2026): un plan también se piensa para un
        grupo de tierras que se llevan igual («rodar las seis del trigo»). Es una dependencia de verdad
        por el mismo motivo que las otras cinco: sin el grupo, el plan se queda sin decir sobre qué
        tierras era.
        """
        from app.routers import parcelas

        assert [modelo.__tablename__ for modelo in parcelas._tablas_que_apuntan_a("grupo_id")] == [
            "fertilizaciones",
            "labores",
            "planes_abonado",
            "trabajos_previstos",
            "tratamientos",
            "ventas_de_cosecha",
        ]

    def test_solo_se_corrige_lo_que_el_formulario_puede_mandar_de_vuelta(self):
        """La regla de la corrección, escrita y con nombre, para la tierra **y** para el grupo.

        **Solo se cambia lo que la API acepta al dar de alta y devuelve al leer**, porque el
        formulario de corregir se rellena con lo que devuelve la API: una columna que no sale en la
        salida es un dato que el agricultor no puede mandar de vuelta, y copiarlo del registro
        preparado lo borraría sin que nadie se entere. Esta prueba es la que obliga a decidir el día
        que se añada una columna nueva: o se devuelve para que se pueda corregir, o se queda en esta
        lista y no se toca.
        """
        from app.routers import parcelas

        assert sorted(
            parcelas._columnas_que_una_correccion_no_toca(
                models.Parcela, ParcelaEntrada, ParcelaSalida
            )
        ) == ["creada_en", "geometria", "superficie_sigpac_ha"]
        assert parcelas._columnas_que_una_correccion_no_toca(
            models.GrupoParcelas, GrupoEntrada, GrupoSalida
        ) == ["creado_automaticamente"]

        # Y se quedan fuera por el motivo que dice la regla, no por casualidad.
        assert "geometria" in ParcelaEntrada.model_fields, "la forma sí se manda al dar de alta"
        assert "geometria" not in ParcelaSalida.model_fields, "pero no se devuelve, así que no vuelve"
        assert "superficie_sigpac_ha" not in ParcelaEntrada.model_fields
        assert "superficie_sigpac_ha" in ParcelaSalida.model_fields
        assert "creado_automaticamente" not in GrupoEntrada.model_fields
        assert "creado_automaticamente" in GrupoSalida.model_fields

    def test_un_grupo_que_junto_el_programa_sigue_siendo_suyo(self, cliente, cuenta, campana, dos_tierras):
        """Renombrar un grupo que juntó el programa no puede convertirlo en «juntado por ti».

        Ese dato no se pregunta en el formulario (solo se pregunta el nombre) y es el que dice de
        quién es el grupo: si la corrección lo copiara del registro preparado, cambiaría solo.
        """
        for tierra in dos_tierras:
            cliente.post(
                f"/api/parcelas/{tierra['id']}/cultivos",
                headers=cuenta["cabeceras"],
                json={"campana_id": campana["id"], "especie": "Cebada", "sistema": "secano"},
            )
        cliente.post(
            "/api/grupos/calcular", headers=cuenta["cabeceras"], params={"campana_id": campana["id"]}
        )
        grupo = _los_grupos(cliente, cuenta["cabeceras"])[0]
        assert grupo["creado_automaticamente"] is True

        corregido = cliente.put(
            f"/api/grupos/{grupo['id']}",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "La cebada de mi hermano",
                "parcela_ids": grupo["parcela_ids"],
            },
        ).json()

        assert corregido["nombre"] == "La cebada de mi hermano"
        assert corregido["creado_automaticamente"] is True


class TestElCultivoDeclarado:
    """Cambiarlo y **quitarlo**: son dos cosas distintas y hacen falta las dos."""

    def _declarar(self, cliente, cabeceras, campana, parcela, especie="Cebada", **cambios) -> dict:
        cuerpo = {"campana_id": campana["id"], "especie": especie, "sistema": "secano"}
        cuerpo.update(cambios)
        respuesta = cliente.post(
            f"/api/parcelas/{parcela['id']}/cultivos", headers=cabeceras, json=cuerpo
        )
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    def test_se_puede_cambiar_el_de_una_campana(self, cliente, cuenta, campana, parcela):
        """Equivocarse de tierra al decir qué hay sembrado es lo primero que pasa."""
        self._declarar(cliente, cuenta["cabeceras"], campana, parcela, especie="Cebada")

        segunda = self._declarar(cliente, cuenta["cabeceras"], campana, parcela, especie="Trigo blando")

        assert segunda["corregido"] is True
        cultivos = cliente.get(
            f"/api/parcelas/{parcela['id']}/cultivos", headers=cuenta["cabeceras"]
        ).json()
        assert [cultivo["especie"] for cultivo in cultivos] == ["Trigo blando"], "no quedan dos"
        assert _la_ficha_de_la_tierra(cliente, cuenta["cabeceras"], parcela["id"])["actual"][
            "especie"
        ] == "Trigo blando"

    def test_se_puede_quitar_y_la_tierra_vuelve_a_salir_a_medias(
        self, cliente, cuenta, campana, parcela
    ):
        """Quitar no es cambiar: la tierra se queda **sin decir** qué tiene, y se vuelve a pedir.

        Es lo que hacía falta para no dejar un dato falso: si estaba en barbecho, la única salida
        que había era escribir otro cultivo. Y al quitarlo tiene que volver a salir en la lista de
        las que les falta decirlo, con su botón para volver a decirlo.
        """
        self._declarar(cliente, cuenta["cabeceras"], campana, parcela, especie="Cebada")
        assert (
            _la_ficha_de_la_tierra(cliente, cuenta["cabeceras"], parcela["id"])["falta_decirlo"]
            is False
        )

        respuesta = cliente.delete(
            f"/api/parcelas/{parcela['id']}/cultivos/{campana['id']}",
            headers=cuenta["cabeceras"],
        )

        assert respuesta.status_code == 200, respuesta.text
        assert (
            cliente.get(
                f"/api/parcelas/{parcela['id']}/cultivos", headers=cuenta["cabeceras"]
            ).json()
            == []
        )
        ficha = _la_ficha_de_la_tierra(cliente, cuenta["cabeceras"], parcela["id"])
        assert ficha["actual"] is None
        assert ficha["falta_decirlo"] is True
        listado = cliente.get("/api/cultivos", headers=cuenta["cabeceras"]).json()
        assert listado["cuantos"] == 1
        assert listado["faltan"] == 1, "vuelve a estar a medias, que es la verdad"

    def test_lo_que_estaba_declarado_queda_en_el_rastro(
        self, cliente, cuenta, db_sesion, campana, parcela
    ):
        """Se quita de la lista y el programa sí sabe qué se había declarado."""
        cultivo = self._declarar(cliente, cuenta["cabeceras"], campana, parcela, especie="Cebada")

        cliente.delete(
            f"/api/parcelas/{parcela['id']}/cultivos/{campana['id']}",
            headers=cuenta["cabeceras"],
        )

        rastro = _auditoria(db_sesion, "parcela_cultivo", cultivo["id"], "borrar")
        assert len(rastro) == 1
        assert rastro[0].datos["especie"] == "Cebada"
        assert rastro[0].fecha is not None

    def test_quitar_el_que_no_esta_dicho_lo_dice_claro(self, cliente, cuenta, campana, parcela):
        respuesta = cliente.delete(
            f"/api/parcelas/{parcela['id']}/cultivos/{campana['id']}",
            headers=cuenta["cabeceras"],
        )

        assert respuesta.status_code == 404
        assert respuesta.json()["detail"] == textos.mensaje("B4_no_hay_cultivo_que_quitar")

    def test_quitar_dos_veces_no_rompe_nada(self, cliente, cuenta, campana, parcela):
        self._declarar(cliente, cuenta["cabeceras"], campana, parcela)
        assert (
            cliente.delete(
                f"/api/parcelas/{parcela['id']}/cultivos/{campana['id']}",
                headers=cuenta["cabeceras"],
            ).status_code
            == 200
        )
        assert (
            cliente.delete(
                f"/api/parcelas/{parcela['id']}/cultivos/{campana['id']}",
                headers=cuenta["cabeceras"],
            ).status_code
            == 404
        )

    def test_el_cultivo_de_otra_finca_no_se_toca(
        self, cliente, cuenta, crear_cuenta, campana, parcela
    ):
        self._declarar(cliente, cuenta["cabeceras"], campana, parcela)
        otro = crear_cuenta("otro@ejemplo.test")

        respuesta = cliente.delete(
            f"/api/parcelas/{parcela['id']}/cultivos/{campana['id']}",
            headers=otro["cabeceras"],
        )

        assert respuesta.status_code == 404
        assert (
            len(
                cliente.get(
                    f"/api/parcelas/{parcela['id']}/cultivos", headers=cuenta["cabeceras"]
                ).json()
            )
            == 1
        )

    def test_sin_entrar_no_se_quita(self, cliente, cuenta, campana, parcela):
        assert (
            cliente.delete(f"/api/parcelas/{parcela['id']}/cultivos/{campana['id']}").status_code
            == 401
        )


class TestLosGrupos:
    def test_se_corrige_el_nombre(self, cliente, cuenta, db_sesion, dos_tierras):
        """Lo que más se corrige de un grupo es el nombre: «La cebada» cuando era trigo."""
        grupo = _juntar(cliente, cuenta["cabeceras"], dos_tierras)

        respuesta = cliente.put(
            f"/api/grupos/{grupo['id']}",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "El trigo",
                "parcela_ids": [tierra["id"] for tierra in dos_tierras],
            },
        )

        assert respuesta.status_code == 200, respuesta.text
        corregido = respuesta.json()
        assert corregido["id"] == grupo["id"], "es el mismo grupo, no otro"
        assert corregido["nombre"] == "El trigo"
        assert corregido["parcela_ids"] == grupo["parcela_ids"]
        assert _los_grupos(cliente, cuenta["cabeceras"])[0]["nombre"] == "El trigo"

        rastro = _auditoria(db_sesion, "grupo", grupo["id"], "corregir")
        assert rastro[0].datos["nombre"] == ["La cebada", "El trigo"]

    def test_se_le_pueden_cambiar_las_tierras_y_queda_escrito(
        self, cliente, cuenta, db_sesion, crear_parcela, dos_tierras
    ):
        """Los apuntes guardan **el grupo**, no cada tierra: hay que poder saber quién estaba dentro.

        El día que se apuntó un tratamiento sobre este grupo, el grupo llevaba unas tierras
        concretas. Si después se le cambian, esa información no puede perderse: por eso el cambio se
        apunta aparte, con las de antes y las de ahora.
        """
        tercera = crear_parcela(alias="El Alto", ref_sigpac="37-455-12-5")
        grupo = _juntar(cliente, cuenta["cabeceras"], dos_tierras)

        respuesta = cliente.put(
            f"/api/grupos/{grupo['id']}",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "La cebada",
                "parcela_ids": [dos_tierras[0]["id"], tercera["id"]],
            },
        )

        assert respuesta.status_code == 200, respuesta.text
        assert respuesta.json()["parcela_ids"] == [dos_tierras[0]["id"], tercera["id"]]

        rastro = _auditoria(db_sesion, "grupo", grupo["id"], "corregir_tierras")
        assert rastro[0].datos["tierras_antes"] == [tierra["id"] for tierra in dos_tierras]
        assert rastro[0].datos["tierras_ahora"] == [dos_tierras[0]["id"], tercera["id"]]

    def test_un_grupo_de_una_sola_tierra_no_se_puede_corregir_asi(
        self, cliente, cuenta, dos_tierras
    ):
        """Las mismas reglas que al juntarlas: un grupo de una sola tierra no ahorra nada."""
        grupo = _juntar(cliente, cuenta["cabeceras"], dos_tierras)

        respuesta = cliente.put(
            f"/api/grupos/{grupo['id']}",
            headers=cuenta["cabeceras"],
            json={"nombre": grupo["nombre"], "parcela_ids": [dos_tierras[0]["id"]]},
        )

        assert respuesta.status_code == 422
        assert respuesta.json()["detail"] == textos.mensaje("V24_grupo_de_una_sola_tierra")
        assert len(_los_grupos(cliente, cuenta["cabeceras"])[0]["parcela_ids"]) == 2

    def test_no_se_puede_corregir_con_una_tierra_de_otra_finca(
        self, cliente, cuenta, crear_cuenta, dos_tierras
    ):
        """Un grupo no puede mezclar tierras de dos fincas: eso sería juntar cuadernos."""
        grupo = _juntar(cliente, cuenta["cabeceras"], dos_tierras)
        otro = crear_cuenta("otro@ejemplo.test")
        ajena = cliente.post(
            "/api/parcelas", headers=otro["cabeceras"], json=_una_tierra(alias="La suya")
        ).json()

        respuesta = cliente.put(
            f"/api/grupos/{grupo['id']}",
            headers=cuenta["cabeceras"],
            json={"nombre": "Mezcla", "parcela_ids": [dos_tierras[0]["id"], ajena["id"]]},
        )

        assert respuesta.status_code == 404
        assert _los_grupos(cliente, cuenta["cabeceras"])[0]["nombre"] == "La cebada"

    def test_se_borra_el_que_no_se_ha_usado(self, cliente, cuenta, db_sesion, dos_tierras):
        """Un grupo sin apuntes es solo una forma de escribir de una vez: se deshace sin más."""
        grupo = _juntar(cliente, cuenta["cabeceras"], dos_tierras)

        respuesta = cliente.delete(f"/api/grupos/{grupo['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 200, respuesta.text
        assert _los_grupos(cliente, cuenta["cabeceras"]) == []
        assert _auditoria(db_sesion, "grupo", grupo["id"], "borrar")[0].datos["nombre"] == "La cebada"
        assert _enganches_guardados(db_sesion) == 0, "el grupo se lleva sus enganches consigo"
        # Y las tierras no se tocan: lo que se ha ido es la agrupación.
        assert len(_las_tierras(cliente, cuenta["cabeceras"])) == 2

    def test_borrar_dos_veces_no_rompe_nada(self, cliente, cuenta, dos_tierras):
        grupo = _juntar(cliente, cuenta["cabeceras"], dos_tierras)
        assert (
            cliente.delete(f"/api/grupos/{grupo['id']}", headers=cuenta["cabeceras"]).status_code
            == 200
        )
        assert (
            cliente.delete(f"/api/grupos/{grupo['id']}", headers=cuenta["cabeceras"]).status_code
            == 404
        )

    def test_el_que_se_ha_usado_para_apuntar_no_se_borra(
        self, cliente, cuenta, campana, dos_tierras, producto
    ):
        """Los apuntes guardan el grupo, no cada tierra: sin él dejarían de decir dónde se hizo."""
        grupo = _juntar(cliente, cuenta["cabeceras"], dos_tierras)
        apunte = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "grupo_id": grupo["id"],
                "superficie_tratada_ha": 5.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert apunte.status_code == 201, apunte.text

        respuesta = cliente.delete(f"/api/grupos/{grupo['id']}", headers=cuenta["cabeceras"])

        assert respuesta.status_code == 409
        assert respuesta.json()["detail"] == textos.mensaje_con_cuenta("B3_grupo_con_apuntes", 1)
        assert len(_los_grupos(cliente, cuenta["cabeceras"])) == 1
        # Y el apunte sigue diciendo dónde se hizo.
        guardado = cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()[0]
        assert guardado["grupo_id"] == grupo["id"]

    def test_el_grupo_de_otra_finca_no_se_toca(self, cliente, cuenta, crear_cuenta, dos_tierras):
        grupo = _juntar(cliente, cuenta["cabeceras"], dos_tierras)
        otro = crear_cuenta("otro@ejemplo.test")

        corregir = cliente.put(
            f"/api/grupos/{grupo['id']}",
            headers=otro["cabeceras"],
            json={"nombre": "Mío", "parcela_ids": [tierra["id"] for tierra in dos_tierras]},
        )
        borrar = cliente.delete(f"/api/grupos/{grupo['id']}", headers=otro["cabeceras"])

        assert corregir.status_code == 404
        assert borrar.status_code == 404
        assert _los_grupos(cliente, cuenta["cabeceras"])[0]["nombre"] == "La cebada"

    def test_sin_entrar_no_se_toca_ningun_grupo(self, cliente, cuenta, dos_tierras):
        grupo = _juntar(cliente, cuenta["cabeceras"], dos_tierras)

        assert (
            cliente.put(
                f"/api/grupos/{grupo['id']}",
                json={"nombre": "Mío", "parcela_ids": [tierra["id"] for tierra in dos_tierras]},
            ).status_code
            == 401
        )
        assert cliente.delete(f"/api/grupos/{grupo['id']}").status_code == 401


class TestLaListaDeRutasNoSeHaRoto:
    """Corregir y borrar **se añaden**: nada de lo que ya había puede desaparecer por el camino."""

    def test_las_rutas_de_siempre_siguen_ahi(self):
        """Se mira la lista de rutas que publica la aplicación, no una respuesta.

        Así esta prueba caza una ruta que se pierda aunque su pantalla no se use en ninguna otra
        prueba del fichero. Se lee del esquema que la aplicación publica (`/openapi.json`) y no de
        `app.routes` porque los routers se incluyen en diferido y ahí solo se ven los envoltorios,
        no las rutas de dentro.
        """
        from app.main import app

        esquema = app.openapi()["paths"]
        publicadas = {
            (metodo.upper(), ruta)
            for ruta, metodos in esquema.items()
            for metodo in metodos
        }
        de_siempre = {
            ("GET", "/api/parcelas"),
            ("POST", "/api/parcelas"),
            ("GET", "/api/parcelas/{parcela_id}"),
            ("GET", "/api/parcelas/{parcela_id}/cultivos"),
            ("POST", "/api/parcelas/{parcela_id}/cultivos"),
            ("POST", "/api/parcelas/desde-sigpac"),
            ("POST", "/api/parcelas/desde-sigpac/varias"),
            ("GET", "/api/cultivos"),
            ("GET", "/api/grupos"),
            ("POST", "/api/grupos"),
            ("POST", "/api/grupos/calcular"),
            ("GET", "/api/municipios"),
            ("GET", "/api/sigpac/estado"),
        }
        assert de_siempre <= publicadas, f"faltan rutas de antes: {sorted(de_siempre - publicadas)}"

        assert {
            ("PUT", "/api/parcelas/{parcela_id}"),
            ("DELETE", "/api/parcelas/{parcela_id}"),
            ("DELETE", "/api/parcelas/{parcela_id}/cultivos/{campana_id}"),
            ("PUT", "/api/grupos/{grupo_id}"),
            ("DELETE", "/api/grupos/{grupo_id}"),
        } <= publicadas, "faltan las rutas nuevas"

    def test_el_alta_y_el_listado_contestan_lo_mismo_que_antes(self, cliente, cuenta, crear_parcela):
        """Lo que ya hacían sigue haciéndolo igual: esto es añadir, no cambiar."""
        parcela = crear_parcela()

        assert parcela["alias"] == "El Prado"
        assert parcela["ref_sigpac"] == "37-455-12-3"
        assert parcela["superficie_ha"] == 2.43
        assert parcela["superficie_oficial"] is True
        assert parcela["sistema"] == "secano"
        assert parcela["municipio"] == "Peñaranda de Bracamonte"
        assert parcela["provincia"] == "Salamanca"
        assert parcela["uso_sigpac"] == "Labor secano"

        listado = _las_tierras(cliente, cuenta["cabeceras"])
        assert [tierra["id"] for tierra in listado] == [parcela["id"]]
        assert listado[0]["alias"] == "El Prado"

        ficha = cliente.get(
            f"/api/parcelas/{parcela['id']}", headers=cuenta["cabeceras"]
        ).json()
        assert ficha == parcela
