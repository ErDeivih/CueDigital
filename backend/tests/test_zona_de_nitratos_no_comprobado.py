"""La zona de nitratos de un apunte: «no se ha podido comprobar» es una respuesta, y no es «no».

Estas pruebas son el cierre del apartado **A2** de `docs/T02_VALORES_POR_DEFECTO.md` (««no lo
sé» se guarda como «no», y entra en el documento que se firma»).

**Qué estaba mal.** `servicios.py` guardaba `bool(parcela.zona_vulnerable_nitratos) if parcela
else False`. La tierra guarda a propósito tres estados (`models.py`, `zona_vulnerable_nitratos`:
`True`, `False` y `None`, «no lo sabemos»), y ese `bool(...)` convertía el tercero en un **no**.
El sitio donde acababa ese `False` no era una pantalla: era el **documento que se firma**
(`firma.py`), y una vez firmado ya no se puede corregir sin volver a firmar. Además, con la
tierra en «no lo sé», ni el aviso de los 170 kg ni las reglas de la Orden MAV/398/2022 se
ejecutaban, así que parecía que el programa lo había mirado todo.

**Qué se hace ahora.** `None` se guarda como `None` (tercer estado), en el documento firmado se
escribe «no se sabe», y al apuntar un abono el programa dice que no ha podido comprobarlo, en vez
de callar. Ningún `True` ni `False` cambia de significado, y por eso los cuadernos ya firmados
siguen cuadrando con su huella: hasta ahora estas columnas no admitían «no se sabe», así que
ningún apunte firmado puede tenerlo.
"""

from __future__ import annotations

import pathlib

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import CreateTable

from app import database, firma, models


def _cuerpo_de_abono(campana, parcela, fertilizante, **cambios):
    """Un abono correcto al que cada prueba le cambia lo suyo."""
    datos = {
        "campana_id": campana["id"],
        "fecha": "2026-02-20",
        "parcela_id": parcela["id"],
        "superficie_ha": parcela["superficie_ha"],
        "fertilizante_id": fertilizante["id"],
        "kg_ha_producto": 100.0,
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def sin_zona_comprobada(crear_parcela):
    """Una tierra de la que **no se sabe** si está en zona vulnerable a nitratos.

    Es el caso normal: la tierra está en un municipio del que no consta el código INE, o el
    listado oficial de zonas vulnerables no está cargado. La suite arranca sin ese listado a
    propósito (ver `conftest.py`, `CUEDIGITAL_ZV_CYL_RUTA`).
    """
    tierra = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=None)
    assert tierra["zona_vulnerable_nitratos"] is None, "la prueba necesita el tercer estado"
    return tierra


# --------------------------------------------------------------------------
# Lo que se guarda
# --------------------------------------------------------------------------


class TestLoQueSeGuarda:
    def test_un_abono_en_una_tierra_sin_comprobar_no_afirma_que_este_fuera(
        self, cliente, cuenta, campana, fertilizante, sin_zona_comprobada
    ):
        """El defecto de A2, con el caso de un abono: antes se guardaba `False`."""
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_abono(campana, sin_zona_comprobada, fertilizante),
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["en_zona_vulnerable"] is None, (
            "un «no lo sé» no puede guardarse como «no está en zona»"
        )

    def test_un_tratamiento_en_una_tierra_sin_comprobar_tampoco(
        self, cliente, cuenta, nuevo_tratamiento, sin_zona_comprobada
    ):
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(parcela_id=sin_zona_comprobada["id"]),
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["en_zona_vulnerable"] is None

    def test_el_tercer_estado_llega_a_la_respuesta_de_la_api_no_solo_a_la_base(
        self, cliente, cuenta, campana, fertilizante, sin_zona_comprobada
    ):
        """Si la respuesta no lo distingue, ninguna pantalla puede contarlo bien."""
        cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_abono(campana, sin_zona_comprobada, fertilizante),
        )
        listado = cliente.get("/api/fertilizaciones", headers=cuenta["cabeceras"]).json()
        assert len(listado) == 1
        assert "en_zona_vulnerable" in listado[0]
        assert listado[0]["en_zona_vulnerable"] is None

    def test_una_tierra_que_si_esta_en_zona_se_sigue_guardando_como_que_si(
        self, cliente, cuenta, campana, fertilizante, crear_parcela
    ):
        """El arreglo no puede cambiar lo que ya estaba bien."""
        en_zona = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True)
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_abono(campana, en_zona, fertilizante),
        )
        assert respuesta.json()["en_zona_vulnerable"] is True

    def test_una_tierra_que_no_esta_en_zona_se_sigue_guardando_como_que_no(
        self, cliente, cuenta, campana, fertilizante, crear_parcela
    ):
        fuera = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=False)
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_abono(campana, fuera, fertilizante),
        )
        assert respuesta.json()["en_zona_vulnerable"] is False

    def test_un_abono_de_varias_tierras_tampoco_puede_decir_que_no(
        self, cliente, cuenta, campana, fertilizante, crear_parcela
    ):
        """Un grupo puede tener tierras dentro y tierras fuera: no hay una respuesta buena."""
        primera = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True)
        segunda = crear_parcela(alias="El Prado", zona_vulnerable_nitratos=False)
        grupo = cliente.post(
            "/api/grupos",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "Las dos de arriba",
                "campana_id": campana["id"],
                "parcela_ids": [primera["id"], segunda["id"]],
            },
        )
        assert grupo.status_code == 201, grupo.text
        respuesta = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_abono(
                campana, primera, fertilizante, parcela_id=None, grupo_id=grupo.json()["id"]
            ),
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["en_zona_vulnerable"] is None, (
            "una tierra del grupo está en zona y la otra no: el apunte no puede decir «no»"
        )


# --------------------------------------------------------------------------
# El documento que se firma
# --------------------------------------------------------------------------


class TestElDocumentoQueSeFirma:
    def test_el_abono_dice_en_el_documento_que_no_se_sabe(
        self, cliente, cuenta, campana, fertilizante, sin_zona_comprobada
    ):
        creado = cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_abono(campana, sin_zona_comprobada, fertilizante),
        ).json()
        fichero = cliente.get(
            "/api/firmas/preparar",
            headers=cuenta["cabeceras"],
            params={"entidad": "fertilizacion", "entidad_id": creado["id"]},
        ).json()
        assert "En zona de nitratos: no se sabe" in fichero["contenido"], (
            "el documento firmado tiene que decir que no se ha podido comprobar"
        )
        assert "En zona de nitratos: no\n" not in fichero["contenido"], (
            "no puede decir «no», porque eso es afirmar que se hizo fuera de zona"
        )

    def test_el_tratamiento_dice_en_el_documento_que_no_se_sabe(
        self, cliente, cuenta, nuevo_tratamiento, sin_zona_comprobada
    ):
        creado = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(parcela_id=sin_zona_comprobada["id"]),
        ).json()
        fichero = cliente.get(
            "/api/firmas/preparar",
            headers=cuenta["cabeceras"],
            params={"entidad": "tratamiento", "entidad_id": creado["id"]},
        ).json()
        assert "En zona de nitratos: no se sabe" in fichero["contenido"]

    def test_el_cuaderno_entero_de_la_campana_tambien_lo_dice(
        self, cliente, cuenta, campana, fertilizante, sin_zona_comprobada
    ):
        """El cuaderno entero es el que se firma de verdad: si ahí no se dice, no se dice."""
        cliente.post(
            "/api/fertilizaciones",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_abono(campana, sin_zona_comprobada, fertilizante),
        )
        fichero = cliente.get(
            "/api/firmas/preparar",
            headers=cuenta["cabeceras"],
            params={"entidad": "cuaderno", "campana_id": campana["id"]},
        ).json()
        assert "En zona de nitratos: no se sabe" in fichero["contenido"]

    def test_un_si_y_un_no_se_siguen_escribiendo_como_siempre(self):
        """**Esto es lo que impide que las firmas viejas dejen de cuadrar.**

        Los cuadernos ya firmados tienen «si» o «no» en esa línea, y su huella se calculó con
        ese texto. Si ahora esos dos valores se escribieran de otra forma, todos los cuadernos
        firmados hasta hoy aparecerían como manipulados, que es justo lo contrario de lo que
        hace falta. El tercer estado es nuevo, así que no puede estar en ninguna firma vieja.
        """
        assert firma.valor_para_firmar(firma.si_no_o_no_se(True)) == "si"
        assert firma.valor_para_firmar(firma.si_no_o_no_se(False)) == "no"
        assert firma.valor_para_firmar(firma.si_no_o_no_se(None)) == "no se sabe"

    def test_la_version_de_la_forma_canonica_no_ha_cambiado(self):
        """Si hubiera que subirla, es que se ha cambiado el texto de los cuadernos firmados."""
        assert firma.VERSION_CANONICA == 1


# --------------------------------------------------------------------------
# Lo que se avisa al apuntar
# --------------------------------------------------------------------------


class TestLoQueSeAvisa:
    def _avisos(self, cliente, cuenta, campana, parcela, fertilizante, **cambios):
        respuesta = cliente.post(
            "/api/fertilizaciones/validar",
            headers=cuenta["cabeceras"],
            json=_cuerpo_de_abono(campana, parcela, fertilizante, **cambios),
        )
        assert respuesta.status_code == 200, respuesta.text
        return {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}

    def test_si_no_se_sabe_el_programa_lo_dice_en_vez_de_callar(
        self, cliente, cuenta, campana, fertilizante, sin_zona_comprobada
    ):
        avisos = self._avisos(cliente, cuenta, campana, sin_zona_comprobada, fertilizante)
        assert "N4_no_se_si_es_zona_de_nitratos" in avisos, (
            "callar aquí deja creyendo que las reglas de nitratos se han mirado"
        )
        assert not avisos["N4_no_se_si_es_zona_de_nitratos"]["bloquea"], (
            "no saber no puede impedir apuntar lo que de verdad ha pasado en el campo"
        )

    def test_el_aviso_dice_qué_hacer_para_que_se_pueda_comprobar(
        self, cliente, cuenta, campana, fertilizante, sin_zona_comprobada
    ):
        avisos = self._avisos(cliente, cuenta, campana, sin_zona_comprobada, fertilizante)
        mensaje = avisos["N4_no_se_si_es_zona_de_nitratos"]["mensaje"]
        assert "municipio" in mensaje.lower(), "tiene que decir qué falta para poder mirarlo"

    def test_fuera_de_la_zona_se_sigue_sin_avisar_de_nada_de_nitratos(
        self, cliente, cuenta, campana, fertilizante, crear_parcela
    ):
        """Fuera de zona el Código de Buenas Prácticas es voluntario: no se avisa."""
        fuera = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=False)
        avisos = self._avisos(cliente, cuenta, campana, fuera, fertilizante)
        assert "N4_no_se_si_es_zona_de_nitratos" not in avisos
        assert not [codigo for codigo in avisos if codigo.startswith("N")]

    def test_en_zona_se_siguen_comprobando_las_reglas_de_verdad(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """Y donde sí se sabe, se mira de verdad: el tope de los 170 kg sigue saltando."""
        en_zona = crear_parcela(alias="La Vega", zona_vulnerable_nitratos=True)
        purin = cliente.post(
            "/api/fertilizantes",
            headers=cuenta["cabeceras"],
            json={"nombre": "Purín de cerdo", "tipo": "organico", "riqueza_n": 4.0},
        ).json()
        avisos = self._avisos(
            cliente, cuenta, campana, en_zona, purin, kg_ha_producto=5000.0
        )
        assert "N1_estiercol_pasa_tope" in avisos, "5.000 kg/ha de purín al 4 % son 200 kg N/ha"
        assert "N4_no_se_si_es_zona_de_nitratos" not in avisos


# --------------------------------------------------------------------------
# La migración: la columna tiene que poder guardar el tercer estado
# --------------------------------------------------------------------------


def _motor_con_la_columna_obligatoria(tmp_path, nombre: str = "vieja.db"):
    """Una base como la de verdad: las tablas del modelo, pero con la columna obligatoria.

    No se escribe el `CREATE TABLE` a mano: se coge el que genera el modelo y se le devuelve el
    `NOT NULL` a esa columna. Así la prueba sigue valiendo aunque la tabla gane columnas, y lo
    que comprueba es exactamente la diferencia que hay entre una instalación vieja y una nueva.
    """
    motor = create_engine(f"sqlite:///{(tmp_path / nombre).as_posix()}")
    dialecto = motor.dialect
    for nombre_tabla in ("tratamientos", "fertilizaciones"):
        tabla = models.Base.metadata.tables[nombre_tabla]
        ddl = str(CreateTable(tabla).compile(dialect=dialecto))
        ddl = ddl.replace(
            "en_zona_vulnerable BOOLEAN,", "en_zona_vulnerable BOOLEAN NOT NULL,"
        )
        assert "en_zona_vulnerable BOOLEAN NOT NULL," in ddl, (
            "la prueba necesita una tabla con la columna obligatoria"
        )
        with motor.begin() as conexion:
            conexion.execute(text(ddl))
    return motor


def _meter_dos_apuntes(motor) -> None:
    """Un tratamiento que dice «no» y un abono que dice «si», con sus filas de apoyo."""
    with motor.begin() as conexion:
        conexion.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conexion.execute(
            text(
                "INSERT INTO tratamientos (id, explotacion_id, campana_id, fecha, tipo, "
                "superficie_tratada_ha, unidad_dosis, en_zona_vulnerable, anulado) "
                "VALUES (1, 1, 1, '2026-05-01', 'parcela', 2.43, 'L/ha', 0, 0)"
            )
        )
        conexion.execute(
            text(
                "INSERT INTO fertilizaciones (id, explotacion_id, campana_id, fecha, "
                "superficie_ha, tipo, riqueza_n, riqueza_p, riqueza_k, kg_ha_producto, "
                "cantidad_total_kg, uf_n_ha, uf_p_ha, uf_k_ha, uf_n_total, uf_p_total, "
                "uf_k_total, en_zona_vulnerable, anulado) "
                "VALUES (1, 1, 1, '2026-02-20', 2.43, 'organico', 4.0, 0.0, 0.0, 1000.0, "
                "2430.0, 40.0, 0.0, 0.0, 972.0, 0.0, 0.0, 1, 0)"
            )
        )


class TestLaMigracion:
    def test_una_base_vieja_no_deja_guardar_el_tercer_estado(self, tmp_path):
        """El punto de partida: así se comporta hoy una instalación que viene de antes."""
        motor = _motor_con_la_columna_obligatoria(tmp_path)
        columnas = {c["name"]: c for c in inspect(motor).get_columns("fertilizaciones")}
        assert columnas["en_zona_vulnerable"]["nullable"] is False

    def test_la_reconstruccion_deja_la_columna_admitiendo_no_se(self, tmp_path):
        motor = _motor_con_la_columna_obligatoria(tmp_path)
        _meter_dos_apuntes(motor)

        hechas = database.reconstruir_para_poder_decir_no_se(motor)

        assert sorted(hechas) == [
            "fertilizaciones.en_zona_vulnerable",
            "tratamientos.en_zona_vulnerable",
        ]
        for tabla in ("tratamientos", "fertilizaciones"):
            columnas = {c["name"]: c for c in inspect(motor).get_columns(tabla)}
            assert columnas["en_zona_vulnerable"]["nullable"] is True, tabla

    def test_la_reconstruccion_no_cambia_ni_un_dato(self, tmp_path):
        """Copiar las filas es copiarlas, no arreglarlas: eso es otra decisión y va aparte."""
        motor = _motor_con_la_columna_obligatoria(tmp_path)
        _meter_dos_apuntes(motor)

        database.reconstruir_para_poder_decir_no_se(motor)

        with motor.begin() as conexion:
            assert conexion.execute(
                text("SELECT COUNT(*) FROM tratamientos")
            ).scalar_one() == 1
            assert conexion.execute(
                text("SELECT COUNT(*) FROM fertilizaciones")
            ).scalar_one() == 1
            # Los valores siguen siendo los que había, incluido el «no» que se inventó en su día.
            assert conexion.execute(
                text("SELECT en_zona_vulnerable FROM tratamientos WHERE id = 1")
            ).scalar_one() == 0
            assert conexion.execute(
                text("SELECT en_zona_vulnerable FROM fertilizaciones WHERE id = 1")
            ).scalar_one() == 1
            # Y ahora sí se puede guardar el tercer estado.
            conexion.execute(
                text("UPDATE tratamientos SET en_zona_vulnerable = NULL WHERE id = 1")
            )
            assert conexion.execute(
                text("SELECT en_zona_vulnerable FROM tratamientos WHERE id = 1")
            ).scalar_one() is None

    def test_los_indices_vuelven_a_estar(self, tmp_path):
        """Tirar la tabla vieja se lleva sus índices por delante: hay que volver a crearlos."""
        motor = _motor_con_la_columna_obligatoria(tmp_path)
        database.reconstruir_para_poder_decir_no_se(motor)

        with motor.begin() as conexion:
            indices = {
                fila[0]
                for fila in conexion.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type = 'index' "
                        "AND tbl_name IN ('tratamientos', 'fertilizaciones')"
                    )
                )
            }
        # Los del modelo tienen que estar todos.
        for tabla in ("tratamientos", "fertilizaciones"):
            for indice in models.Base.metadata.tables[tabla].indexes:
                assert indice.name in indices, indice.name

    def test_hacerlo_dos_veces_no_cambia_nada(self, tmp_path):
        motor = _motor_con_la_columna_obligatoria(tmp_path)
        _meter_dos_apuntes(motor)
        primera = database.reconstruir_para_poder_decir_no_se(motor)
        segunda = database.reconstruir_para_poder_decir_no_se(motor)
        assert primera, "la primera vez tenía que hacer algo"
        assert segunda == [], "la segunda vez no hay nada que hacer"
        with motor.begin() as conexion:
            assert conexion.execute(text("SELECT COUNT(*) FROM tratamientos")).scalar_one() == 1

    def test_deja_una_copia_de_la_base_antes_de_tocarla(self, tmp_path):
        """Una reconstrucción sin vuelta atrás no se hace."""
        motor = _motor_con_la_columna_obligatoria(tmp_path)
        database.reconstruir_para_poder_decir_no_se(motor)
        copias = list(tmp_path.glob("vieja.db.antes-de-migrar-*"))
        assert copias, "tiene que haber quedado una copia al lado de la base"

    def test_si_la_copia_no_es_valida_no_reconstruye_la_base(self, tmp_path, monkeypatch):
        """El arranque debe detenerse antes de tocar tablas si no hay vuelta atrás válida."""
        motor = _motor_con_la_columna_obligatoria(tmp_path)
        _meter_dos_apuntes(motor)
        monkeypatch.setattr(database, "_la_copia_esta_entera", lambda _ruta: False)

        with pytest.raises(RuntimeError, match="copia previa a la migración"):
            database.reconstruir_para_poder_decir_no_se(motor)

        columnas = {c["name"]: c for c in inspect(motor).get_columns("tratamientos")}
        assert columnas["en_zona_vulnerable"]["nullable"] is False
        with motor.begin() as conexion:
            assert conexion.execute(text("SELECT COUNT(*) FROM tratamientos")).scalar_one() == 1

    def test_una_base_que_no_tiene_la_tabla_se_ignora(self, tmp_path):
        """En una instalación a la que le falta una tabla, la otra se arregla igual."""
        motor = create_engine(f"sqlite:///{(tmp_path / 'solo_una.db').as_posix()}")
        tabla = models.Base.metadata.tables["fertilizaciones"]
        ddl = str(CreateTable(tabla).compile(dialect=motor.dialect)).replace(
            "en_zona_vulnerable BOOLEAN,", "en_zona_vulnerable BOOLEAN NOT NULL,"
        )
        with motor.begin() as conexion:
            conexion.execute(text(ddl))

        hechas = database.reconstruir_para_poder_decir_no_se(motor)

        assert hechas == ["fertilizaciones.en_zona_vulnerable"]

    def test_si_algo_falla_a_mitad_se_deshace_todo(self, tmp_path):
        """La red de seguridad: si una parte de la reconstrucción falla, la base se queda igual.

        Se prepara el fallo de verdad, sin trampa: se ocupa por adelantado el nombre de uno de los
        índices de la tabla, así que al volver a crearlos SQLite dice que ya existe y la
        reconstrucción se queda a medias. Lo que se comprueba es que **no se queda a medias**: la
        columna sigue siendo obligatoria, la fila sigue ahí y no queda ninguna tabla suelta.
        """
        motor = _motor_con_la_columna_obligatoria(tmp_path)
        _meter_dos_apuntes(motor)
        with motor.begin() as conexion:
            conexion.execute(text("CREATE TABLE estorbo (x INTEGER)"))
            conexion.execute(text("CREATE INDEX ix_tratamientos_fecha ON estorbo (x)"))

        with pytest.raises(Exception) as fallo:
            database.reconstruir_para_poder_decir_no_se(motor)

        assert "already exists" in str(fallo.value)

        # Y la base sigue exactamente como estaba: con la columna obligatoria y con su fila.
        columnas = {c["name"]: c for c in inspect(motor).get_columns("tratamientos")}
        assert columnas["en_zona_vulnerable"]["nullable"] is False
        with motor.begin() as conexion:
            assert conexion.execute(
                text("SELECT COUNT(*) FROM tratamientos")
            ).scalar_one() == 1
            sobrantes = conexion.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type = 'table' "
                    "AND name LIKE '%reconstruida%'"
                )
            ).fetchall()
        assert sobrantes == [], "no puede quedar la tabla a medio hacer"

    def test_una_fila_que_ya_apuntaba_a_nada_no_impide_el_cambio(self, tmp_path):
        """Una base que ya venía con una fila huérfana no puede quedarse sin poner al día.

        Pasa de verdad: una tierra borrada a mano, un traspaso a medias. Bloquear el cambio por un
        problema que ya estaba sería dejar al agricultor sin poder apuntar por culpa de algo que no
        ha hecho él. Lo que no se admite es que la reconstrucción **añada** huérfanas.
        """
        motor = _motor_con_la_columna_obligatoria(tmp_path)
        # Las filas de `_meter_dos_apuntes` apuntan a una explotación y una campaña que no existen
        # en esta base de prueba: ya eran huérfanas antes de empezar.
        _meter_dos_apuntes(motor)

        hechas = database.reconstruir_para_poder_decir_no_se(motor)

        assert hechas, "tenía que hacer el cambio"
        columnas = {c["name"]: c for c in inspect(motor).get_columns("tratamientos")}
        assert columnas["en_zona_vulnerable"]["nullable"] is True
        with motor.begin() as conexion:
            assert conexion.execute(
                text("SELECT COUNT(*) FROM tratamientos")
            ).scalar_one() == 1


# --------------------------------------------------------------------------
# La copia que se hace antes de tocar nada
# --------------------------------------------------------------------------
#
# **Por qué esta sección existe.** La copia es la vuelta atrás del agricultor: si no sirve, la
# reconstrucción de tablas es un salto sin red. Y hay una forma de que una copia parezca buena sin
# serlo: los cambios **confirmados** que todavía viven en el fichero `-wal`. Un fichero principal
# copiado a mano en ese momento **pasa `quick_check`** (está entero) y **le faltan filas**.


def _base_simple(tmp_path, nombre: str = "normal.db"):
    """Una base pequeña con una tabla y una fila, hecha a mano (sin depender del modelo)."""
    import sqlite3

    ruta = tmp_path / nombre
    conexion = sqlite3.connect(str(ruta))
    try:
        conexion.execute("CREATE TABLE cosas (id INTEGER PRIMARY KEY, nombre TEXT)")
        conexion.execute("INSERT INTO cosas (nombre) VALUES ('La Vega')")
        conexion.commit()
    finally:
        conexion.close()
    return ruta


class TestLaCopiaDeAntesDeMigrar:
    def test_una_copia_normal_se_puede_volver_a_poner_byte_a_byte(self, tmp_path):
        """El caso de siempre: sin nada pendiente, volver atrás deja el fichero **igual**.

        Se devuelve la copia byte a byte justo por esto: `VACUUM INTO` y la API de copia de SQLite
        sacan copias coherentes, pero reorganizadas, y devolver una de esas al sitio no deja el
        fichero como estaba.
        """
        ruta = _base_simple(tmp_path)
        motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")

        copia = database._copia_de_seguridad_del_fichero(motor)

        assert copia and copia.endswith("-byte-a-byte"), f"se esperaba la copia byte a byte: {copia}"
        assert pathlib.Path(copia).read_bytes() == ruta.read_bytes()

    def test_con_cambios_confirmados_en_el_wal_la_copia_lleva_los_datos(self, tmp_path):
        """**El caso que no caza `quick_check`.** Cambios confirmados todavía en el WAL.

        Se deja la conexión que escribió **abierta** a propósito: así el WAL no se vacía al cerrar y
        lo confirmado sigue sin bajar al fichero principal, que es como se encuentra una base que
        alguien ha abierto con un visor de SQLite. Después:

        1. Se comprueba **que el problema es real**: una copia del fichero principal, tal cual,
           **no lleva** la fila confirmada. Sin esto, la prueba no demostraría nada.
        2. Se comprueba que la copia que hace el programa **sí la lleva**, y que lo dice.
        """
        import shutil
        import sqlite3

        ruta = _base_simple(tmp_path, "con_wal.db")
        escritor = sqlite3.connect(str(ruta))
        try:
            assert escritor.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() == "wal"
            escritor.execute("INSERT INTO cosas (nombre) VALUES ('El Prado')")
            escritor.commit()
            assert pathlib.Path(f"{ruta}-wal").stat().st_size > 0, (
                "la prueba necesita cambios confirmados viviendo en el WAL"
            )

            # 1. El problema, demostrado: copiar el principal a mano pierde la fila.
            a_mano = tmp_path / "a-mano.db"
            shutil.copy2(ruta, a_mano)
            mirando = sqlite3.connect(f"file:{a_mano.as_posix()}?mode=ro", uri=True)
            try:
                cuantas = mirando.execute("SELECT COUNT(*) FROM cosas").fetchone()[0]
            finally:
                mirando.close()
            assert cuantas == 1, (
                "si el fichero principal ya tuviera las dos filas, esta prueba no probaría nada"
            )

            # 2. Y la copia del programa sí las lleva.
            motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
            copia = database._copia_de_seguridad_del_fichero(motor)
        finally:
            escritor.close()

        assert copia
        conexion = sqlite3.connect(f"file:{pathlib.Path(copia).as_posix()}?mode=ro", uri=True)
        try:
            nombres = [fila[0] for fila in conexion.execute("SELECT nombre FROM cosas ORDER BY id")]
        finally:
            conexion.close()
        assert nombres == ["La Vega", "El Prado"], (
            f"la copia tiene que llevar lo que estaba en el WAL: {nombres}"
        )

    def test_con_el_wal_cargado_no_se_deja_una_copia_byte_a_byte_incompleta(self, tmp_path):
        """No se guarda una copia que **parece** la vuelta atrás y pierde datos.

        Es peor que no tenerla: el agricultor la restauraría creyendo que vuelve a lo de antes.
        """
        import sqlite3

        ruta = _base_simple(tmp_path, "con_wal2.db")
        escritor = sqlite3.connect(str(ruta))
        try:
            escritor.execute("PRAGMA journal_mode=WAL")
            escritor.execute("INSERT INTO cosas (nombre) VALUES ('El Prado')")
            escritor.commit()
            motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
            copia = database._copia_de_seguridad_del_fichero(motor)
        finally:
            escritor.close()

        assert copia and not copia.endswith("-byte-a-byte"), (
            "con datos pendientes en el WAL solo vale la copia coherente"
        )
        sobrantes = [f.name for f in tmp_path.glob("*byte-a-byte*")]
        assert sobrantes == [], f"ha quedado una copia incompleta: {sobrantes}"

    def test_si_a_la_copia_le_faltan_datos_no_se_reconstruye_nada(self, tmp_path, monkeypatch):
        """Segunda red: puede estar entera y aun así no tener lo mismo. Entonces, se para.

        **Con dos intentos** (revisión independiente, 02/10/2026). La comprobación se hace contra la base
        viva, así que si otro proceso escribe justo entre la copia y la comprobación, lo que falla es el
        momento y no la copia. Se vuelve a copiar una vez y, si tampoco cuadra, se para **diciendo qué
        hacer** (cerrar el otro programa), en vez de culpar a una copia que estaba bien.
        """
        motor = _motor_con_la_columna_obligatoria(tmp_path)
        _meter_dos_apuntes(motor)
        monkeypatch.setattr(database, "_copia_tiene_lo_mismo", lambda _ruta, _copia: False)

        with pytest.raises(RuntimeError, match="otro programa escribiendo"):
            database.reconstruir_para_poder_decir_no_se(motor)

        columnas = {c["name"]: c for c in inspect(motor).get_columns("tratamientos")}
        assert columnas["en_zona_vulnerable"]["nullable"] is False
        with motor.begin() as conexion:
            assert conexion.execute(
                text("SELECT COUNT(*) FROM tratamientos")
            ).scalar_one() == 1
        sobrantes = [f.name for f in tmp_path.glob("vieja.db.antes-de-migrar-*")]
        assert sobrantes == [], f"ha quedado una copia que no vale: {sobrantes}"

    def test_la_comprobacion_de_los_datos_caza_lo_que_quick_check_no(self, tmp_path):
        """Y la comprobación sirve: dos bases enteras y distintas se distinguen."""
        import shutil
        import sqlite3

        una = _base_simple(tmp_path, "una.db")
        otra = tmp_path / "otra.db"
        shutil.copy2(una, otra)
        assert database._copia_tiene_lo_mismo(una, otra) is True
        with sqlite3.connect(str(otra)) as conexion:
            conexion.execute("INSERT INTO cosas (nombre) VALUES ('Otra')")
        assert database._la_copia_esta_entera(otra) is True, "las dos están enteras"
        assert database._copia_tiene_lo_mismo(una, otra) is False, (
            "una copia con menos filas tiene que detectarse"
        )


class TestDeshacerLaMigracion:
    """Volver atrás **de verdad**: no basta con poner la copia encima si hay un WAL al lado.

    Lo encontró la revisión independiente del 02/10/2026, y es de los que se ven tarde: si junto a la base
    hay un `-wal` (cambios confirmados que no han bajado al fichero principal), copiar la copia encima **no
    deshace nada** —SQLite reaplica el `-wal` en cuanto abre—, así que el agricultor creería haber vuelto
    atrás y no habría vuelto. La vuelta atrás son tres cosas: el fichero, el `-wal` y el `-shm`. Eso es lo
    que hace `backend/scripts/deshacer_la_migracion.py`, y esto es lo que lo comprueba.
    """

    def _el_guion(self):
        import importlib.util
        import pathlib as _pathlib

        ruta = (
            _pathlib.Path(__file__).resolve().parents[1] / "scripts" / "deshacer_la_migracion.py"
        )
        especificacion = importlib.util.spec_from_file_location("deshacer", ruta)
        modulo = importlib.util.module_from_spec(especificacion)
        especificacion.loader.exec_module(modulo)
        return modulo

    def _nombres(self, ruta) -> list[str]:
        import sqlite3

        conexion = sqlite3.connect(f"file:{ruta.as_posix()}?mode=ro", uri=True)
        try:
            return [fila[0] for fila in conexion.execute("SELECT nombre FROM cosas ORDER BY id")]
        finally:
            conexion.close()

    def _escribir_y_morir(self, ruta, nombre: str) -> None:
        """Deja una fila confirmada **en el WAL** y mata el proceso sin cerrar nada.

        Es la forma de reproducir de verdad lo que pasa cuando el programa se cae (o lo matan) con cambios
        confirmados que todavía no han bajado al fichero principal: el `-wal` se queda con ellos y **nadie
        lo tiene abierto**. Sin esto no se puede probar la vuelta atrás en Windows: un `-wal` abierto por
        otro proceso no se puede ni borrar.
        """
        import subprocess
        import sys

        programa = (
            "import os, sqlite3, sys\n"
            "conexion = sqlite3.connect(sys.argv[1])\n"
            "conexion.execute('PRAGMA journal_mode=WAL')\n"
            "conexion.execute('INSERT INTO cosas (nombre) VALUES (?)', (sys.argv[2],))\n"
            "conexion.commit()\n"
            # `os._exit` NO cierra la conexión ni hace punto de control: el WAL se queda con lo confirmado.
            "os._exit(0)\n"
        )
        subprocess.run([sys.executable, "-c", programa, str(ruta), nombre], check=True)

    def test_copiar_la_copia_con_un_wal_al_lado_no_deshace_lo_de_despues(self, tmp_path):
        """**El problema, medido**: con un `-wal` al lado, poner la copia encima no vuelve atrás.

        SQLite reaplica el `-wal` en cuanto abre la base, así que lo escrito **después** de la copia vuelve
        a estar ahí. Por eso «para volver atrás, copia la copia encima» estaba incompleto.
        """
        import shutil

        ruta = tmp_path / "con_wal3.db"
        import sqlite3

        conexion = sqlite3.connect(str(ruta))
        conexion.execute("CREATE TABLE cosas (id INTEGER PRIMARY KEY, nombre TEXT)")
        conexion.execute("INSERT INTO cosas (nombre) VALUES ('La Vega')")
        conexion.execute("INSERT INTO cosas (nombre) VALUES ('El Prado')")
        conexion.commit()
        conexion.close()
        # La copia, **antes** de lo que hay que deshacer (que es como se hace de verdad: la copia es de
        # antes de tocar nada).
        motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
        copia = database._copia_de_seguridad_del_fichero(motor)
        assert self._nombres(pathlib.Path(copia)) == ["La Vega", "El Prado"]

        # Y ahora sí: alguien escribe **después de la copia** y el proceso se muere sin bajar el WAL.
        self._escribir_y_morir(ruta, "Después de la copia")
        assert pathlib.Path(f"{ruta}-wal").exists(), "la prueba necesita el WAL en el disco"
        assert self._nombres(ruta) == ["La Vega", "El Prado", "Después de la copia"]

        shutil.copy2(copia, ruta)

        assert self._nombres(ruta) == ["La Vega", "El Prado", "Después de la copia"], (
            "si copiar la copia encima ya volviera atrás, esta prueba no demostraría nada"
        )

    def test_el_guion_deshace_de_verdad_quitando_tambien_el_wal(self, tmp_path):
        """Y **la solución**: el guion pone la copia **y** quita el `-wal` y el `-shm`."""
        import sys

        ruta = tmp_path / "con_wal4.db"
        import sqlite3

        conexion = sqlite3.connect(str(ruta))
        conexion.execute("CREATE TABLE cosas (id INTEGER PRIMARY KEY, nombre TEXT)")
        conexion.execute("INSERT INTO cosas (nombre) VALUES ('La Vega')")
        conexion.execute("INSERT INTO cosas (nombre) VALUES ('El Prado')")
        conexion.commit()
        conexion.close()
        motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
        copia = database._copia_de_seguridad_del_fichero(motor)
        # Lo escrito después de la copia, que es lo que hay que deshacer.
        self._escribir_y_morir(ruta, "Después de la copia")

        guion = self._el_guion()
        sys.argv = ["deshacer", "--base", str(ruta), "--copia", copia]
        codigo = guion.main()

        assert codigo == 0, "el guion tiene que terminar bien"
        assert self._nombres(ruta) == ["La Vega", "El Prado"], (
            "el guion no ha deshecho de verdad: sigue estando lo escrito después de la copia"
        )
        assert not pathlib.Path(f"{ruta}-wal").exists(), "el WAL tiene que quedar fuera"

    def test_el_guion_no_da_por_deshecho_lo_que_no_ha_podido_terminar(self, tmp_path, capsys):
        """Si no puede quitar el WAL (otro programa lo tiene abierto), **no dice que está hecho**.

        En Windows un `-wal` abierto por otro proceso no se puede borrar, y sin borrarlo la vuelta atrás no
        está hecha: el WAL reaplicaría lo de después. El guion para, lo explica y sale con 1.
        """
        import sqlite3
        import sys

        ruta = tmp_path / "con_wal5.db"
        conexion = sqlite3.connect(str(ruta))
        conexion.execute("CREATE TABLE cosas (id INTEGER PRIMARY KEY, nombre TEXT)")
        conexion.execute("INSERT INTO cosas (nombre) VALUES ('La Vega')")
        conexion.commit()
        conexion.execute("PRAGMA journal_mode=WAL")
        conexion.execute("INSERT INTO cosas (nombre) VALUES ('El Prado')")
        conexion.commit()
        motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
        copia = database._copia_de_seguridad_del_fichero(motor)
        try:
            guion = self._el_guion()
            sys.argv = ["deshacer", "--base", str(ruta), "--copia", copia]
            codigo = guion.main()
            salida = capsys.readouterr().out
        finally:
            conexion.close()

        assert codigo == 1, "no puede decir que ha terminado si no ha podido quitar el WAL"
        assert "No se ha podido terminar" in salida
        assert "no está hecha" in salida
        assert "antes-de-deshacer" in salida, "tiene que decir cómo dejarlo como estaba"

    def test_guarda_el_estado_de_ahora_antes_de_pisarlo(self, tmp_path):
        """Deshacer un deshacer también tiene que ser posible: si te equivocas de copia, no la pierdes."""
        import pathlib as _pathlib
        import shutil
        import sys

        ruta = _base_simple(tmp_path, "con_wal4.db")
        motor = database.crear_engine(f"sqlite:///{ruta.as_posix()}")
        copia = database._copia_de_seguridad_del_fichero(motor)

        guion = self._el_guion()
        sys.argv = ["deshacer", "--base", str(ruta), "--copia", copia]
        assert guion.main() == 0

        guardadas = list(_pathlib.Path(tmp_path).glob("con_wal4.db.antes-de-deshacer-*"))
        assert guardadas, "no ha guardado el estado de ahora antes de pisarlo"
        # Y esa copia sirve para volver: se pone y la base queda utilizable con sus datos.
        shutil.copy2(guardadas[0], ruta)
        assert self._nombres(ruta) == ["La Vega"]

    def test_si_la_copia_no_sirve_no_toca_nada(self, tmp_path, capsys):
        """Una copia que no se puede abrir no puede pisar la base: se dice y no se toca."""
        import sys

        ruta = _base_simple(tmp_path, "con_wal5.db")
        mala = tmp_path / "mala.db"
        mala.write_bytes(b"esto no es una base de datos")
        antes = ruta.read_bytes()

        guion = self._el_guion()
        sys.argv = ["deshacer", "--base", str(ruta), "--copia", str(mala)]
        codigo = guion.main()

        assert codigo == 1
        assert "no se puede abrir o no está entera" in capsys.readouterr().out
        assert ruta.read_bytes() == antes, "ha pisado la base con una copia que no vale"
