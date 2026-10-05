"""La autorización del producto: las tres comprobaciones que no podían saltar.

**Por qué existe este fichero.** Es la tercera vez en cuatro rondas que aparece el mismo fallo, y
esta vez eran **tres de golpe**: comprobaciones que existían, estaban escritas con sus mensajes y
sus tests… y **no podían saltar nunca**, porque el dato del que dependen no se podía meter desde
ninguna pantalla.

| Comprobación | De qué depende | Qué pasaba |
|---|---|---|
| `V1_no_autorizado` | `producto.autorizado` | Se quedaba en su valor por defecto («sí, autorizado») sin preguntarlo nunca |
| `V15_no_ecologico` | `producto.permitido_ecologico` | Igual: por defecto «sí, sirve para ecológico» |
| `V1_autorizacion_caducada` | `producto.autorizacion_hasta` | La fecha no se podía escribir en ningún sitio |

Las tres importan de verdad, y no son avisos: **bloquean**. Usar un producto retirado, o uno que
no vale para ecológico en una finca ecológica, o uno cuya autorización excepcional ya caducó, es
una infracción. Y el programa decía «adelante» en los tres casos.

Lo de la autorización excepcional es lo más delicado: es el permiso **temporal** para usar un
producto que no está autorizado con carácter general, y se pide cuando aparece una plaga que no
se puede combatir con lo que hay. Cuando ese permiso se acaba, el producto deja de poder usarse.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import inspect, text

from app import database


def _producto(cliente, cabeceras, **cambios) -> dict:
    cuerpo = {
        "nombre_comercial": "Ejemplo 25 EC",
        "numero_registro": "24.123",
        "dosis_maxima": 2.0,
        "unidad_dosis": "L/ha",
        "plazo_seguridad_dias": 21,
    }
    cuerpo.update(cambios)
    respuesta = cliente.post("/api/productos", headers=cabeceras, json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _tratamiento(cliente, cabeceras, campana, parcela, producto, fecha="2026-05-05"):
    return cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": fecha,
            "parcela_id": parcela["id"],
            "superficie_tratada_ha": 1.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto["id"],
            "dosis": 0.5,
        },
    )


class TestLosCamposQueFaltaban:
    def test_la_autorizacion_se_guarda_y_se_devuelve(self, cliente, cuenta):
        """Guardar un dato y no devolverlo es como no tenerlo: no llega a ninguna pantalla."""
        producto = _producto(
            cliente,
            cuenta["cabeceras"],
            autorizacion_excepcional="AUT-2026-0417",
            autorizacion_hasta="2026-07-31",
        )
        assert producto["autorizacion_excepcional"] == "AUT-2026-0417"
        assert producto["autorizacion_hasta"] == "2026-07-31"

    def test_por_defecto_un_producto_no_queda_autorizado_ni_permitido(self, cliente, cuenta):
        """**Cambio del 02/10/2026, y el porqué.** Antes esta prueba decía lo contrario: «el defecto
        es sí, que es lo que pasa con lo que se compra en una tienda».

        Estaba mal, y era el defecto **A1** de `docs/T02_VALORES_POR_DEFECTO.md`: el bloque de la
        autorización del formulario está plegado y pone «opcional», así que dar de alta un producto
        escribiendo solo el nombre y la dosis bastaba para que el programa diera por bueno que se
        puede usar y que vale para ecológico. Las dos comprobaciones de este fichero —las que
        bloquean, y por las que existe— **no podían saltar nunca**. Un «sí» puesto por el programa
        no es un dato del agricultor: es la ausencia de un dato disfrazada de permiso.

        Ahora hay tres estados: `True`, `False` y `None` («no comprobado»). El tercero avisa y no
        bloquea, porque el cuaderno tiene que poder recoger lo que de verdad se hizo.
        """
        producto = _producto(cliente, cuenta["cabeceras"])
        assert producto["autorizado"] is None
        assert producto["permitido_ecologico"] is None

    def test_si_el_agricultor_contesta_que_si_se_guarda_que_si(self, cliente, cuenta):
        """El «sí» de verdad sigue valiendo: lo que cambia es quién lo dice."""
        producto = _producto(
            cliente, cuenta["cabeceras"], autorizado=True, permitido_ecologico=True
        )
        assert producto["autorizado"] is True
        assert producto["permitido_ecologico"] is True

    def test_se_puede_decir_que_no_esta_autorizado(self, cliente, cuenta):
        producto = _producto(cliente, cuenta["cabeceras"], autorizado=False)
        assert producto["autorizado"] is False

    def test_el_tipo_de_carne_y_el_reganip_del_aplicador(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/aplicadores",
            headers=cuenta["cabeceras"],
            json={
                "nombre": "David Pérez",
                "numero_carne": "C-123456",
                "tipo_carne": "Cualificado",
                "numero_reganip": "REGANIP-2026-12",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        # El carné se guarda con su clave canónica (en minúsculas) y se enseña su nombre. **Cambio del
        # 26/09/2026, y el motivo es el cuaderno**: su hoja 1.2 tiene una columna por tipo de carné y
        # se marca con una cruz, así que «Cualificado», «cualificado» y «nivel 2» no pueden ser tres
        # cosas distintas. Antes esto era texto libre y la cruz no se podía poner.
        from app import catalogos

        assert datos["tipo_carne"] == "cualificado"
        assert catalogos.etiqueta_carne(datos["tipo_carne"]) == "Cualificado"
        assert datos["numero_reganip"] == "REGANIP-2026-12"


class TestLaComprobacionQueNoPodiaSaltar_ProductoRetirado:
    def test_un_producto_no_autorizado_bloquea(self, cliente, cuenta, campana, parcela):
        producto = _producto(cliente, cuenta["cabeceras"], autorizado=False)
        respuesta = _tratamiento(cliente, cuenta["cabeceras"], campana, parcela, producto)
        assert respuesta.status_code == 422
        avisos = respuesta.json()["detail"]["avisos"]
        assert any(aviso["codigo"] == "V1_no_autorizado" for aviso in avisos)

    def test_y_el_mensaje_dice_qué_hacer(self, cliente, cuenta, campana, parcela):
        producto = _producto(cliente, cuenta["cabeceras"], autorizado=False)
        respuesta = _tratamiento(cliente, cuenta["cabeceras"], campana, parcela, producto)
        mensaje = respuesta.json()["detail"]["avisos"][0]["mensaje"]
        assert mensaje
        assert "error" not in mensaje.lower()

    def test_un_producto_autorizado_pasa(self, cliente, cuenta, campana, parcela):
        producto = _producto(cliente, cuenta["cabeceras"])
        assert _tratamiento(cliente, cuenta["cabeceras"], campana, parcela, producto).status_code == 201


class TestLaComprobacionQueNoPodiaSaltar_Ecologico:
    def test_en_una_finca_ecologica_un_producto_que_no_vale_bloquea(
        self, cliente, cuenta, campana, parcela
    ):
        # La finca tiene que ser ecológica para que la comprobación aplique.
        cliente.put(
            "/api/mi-finca",
            headers=cuenta["cabeceras"],
            json={"produccion_ecologica": True},
        )
        producto = _producto(cliente, cuenta["cabeceras"], permitido_ecologico=False)
        respuesta = _tratamiento(cliente, cuenta["cabeceras"], campana, parcela, producto)
        assert respuesta.status_code == 422
        avisos = respuesta.json()["detail"]["avisos"]
        assert any(aviso["codigo"] == "V15_no_ecologico" for aviso in avisos)

    def test_en_una_finca_normal_no_aplica(self, cliente, cuenta, campana, parcela):
        """La regla es para las fincas ecológicas: en las demás, ese dato no pinta nada."""
        producto = _producto(cliente, cuenta["cabeceras"], permitido_ecologico=False)
        assert _tratamiento(cliente, cuenta["cabeceras"], campana, parcela, producto).status_code == 201


class TestLaComprobacionQueNoPodiaSaltar_AutorizacionCaducada:
    def test_una_autorizacion_caducada_bloquea(self, cliente, cuenta, campana, parcela):
        """Es lo más delicado: usar un producto sin autorización vigente es una infracción."""
        producto = _producto(
            cliente,
            cuenta["cabeceras"],
            autorizacion_excepcional="AUT-2025-0001",
            autorizacion_hasta="2026-03-31",
        )
        respuesta = _tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto, fecha="2026-05-05"
        )
        assert respuesta.status_code == 422
        avisos = respuesta.json()["detail"]["avisos"]
        assert any(aviso["codigo"] == "V1_autorizacion_caducada" for aviso in avisos)

    def test_y_el_aviso_dice_la_fecha(self, cliente, cuenta, campana, parcela):
        producto = _producto(
            cliente,
            cuenta["cabeceras"],
            autorizacion_excepcional="AUT-2025-0001",
            autorizacion_hasta="2026-03-31",
        )
        respuesta = _tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto, fecha="2026-05-05"
        )
        aviso = [
            a
            for a in respuesta.json()["detail"]["avisos"]
            if a["codigo"] == "V1_autorizacion_caducada"
        ][0]
        assert "31/03/2026" in aviso["mensaje"]

    def test_dentro_del_plazo_se_puede_usar(self, cliente, cuenta, campana, parcela):
        producto = _producto(
            cliente,
            cuenta["cabeceras"],
            autorizacion_excepcional="AUT-2026-0417",
            autorizacion_hasta="2026-07-31",
        )
        respuesta = _tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto, fecha="2026-05-05"
        )
        assert respuesta.status_code == 201, respuesta.text

    def test_el_ultimo_dia_todavia_se_puede(self, cliente, cuenta, campana, parcela):
        """El día que acaba, todavía vale: la autorización es «hasta» ese día."""
        producto = _producto(
            cliente,
            cuenta["cabeceras"],
            autorizacion_excepcional="AUT-2026-0417",
            autorizacion_hasta="2026-05-05",
        )
        respuesta = _tratamiento(
            cliente, cuenta["cabeceras"], campana, parcela, producto, fecha="2026-05-05"
        )
        assert respuesta.status_code == 201, respuesta.text


class TestElAvisoDeQueSeAcaba:
    def test_avisa_antes_de_que_acabe(self, cliente, cuenta, monkeypatch):
        """Con mes y medio, que es lo que se tarda en pedir otra o en buscar la alternativa."""
        from app import legal

        monkeypatch.setattr(legal, "hoy", lambda: dt.date(2026, 6, 20))
        _producto(
            cliente,
            cuenta["cabeceras"],
            autorizacion_excepcional="AUT-2026-0417",
            autorizacion_hasta="2026-07-10",
        )
        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        assert any(aviso["tipo"] == "autorizacion" for aviso in avisos)

    def test_dice_la_fecha_y_que_hay_que_darse_prisa(self, cliente, cuenta, monkeypatch):
        from app import legal

        monkeypatch.setattr(legal, "hoy", lambda: dt.date(2026, 6, 20))
        _producto(
            cliente,
            cuenta["cabeceras"],
            autorizacion_excepcional="AUT-2026-0417",
            autorizacion_hasta="2026-07-10",
        )
        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        aviso = [a for a in avisos if a["tipo"] == "autorizacion"][0]
        assert "10/07/2026" in aviso["mensaje"]
        assert "aprovecha" in aviso["mensaje"] or "pide otra" in aviso["mensaje"]

    def test_una_que_ya_acabo_se_dice_como_tal(self, cliente, cuenta, monkeypatch):
        from app import legal

        monkeypatch.setattr(legal, "hoy", lambda: dt.date(2026, 6, 20))
        _producto(
            cliente,
            cuenta["cabeceras"],
            autorizacion_excepcional="AUT-2025-0001",
            autorizacion_hasta="2026-03-31",
        )
        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        aviso = [a for a in avisos if a["tipo"] == "autorizacion_caducada"][0]
        assert aviso["urgente"] is True
        assert "Ya no se puede usar" in aviso["mensaje"]

    def test_sin_autorizacion_especial_no_hay_aviso(self, cliente, cuenta):
        """Un producto normal no tiene autorización excepcional, y eso no es un aviso."""
        _producto(cliente, cuenta["cabeceras"])
        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        assert not [a for a in avisos if a["tipo"].startswith("autorizacion")]

    def test_los_avisos_no_llevan_jerga(self, cliente, cuenta, monkeypatch):
        from app import legal, textos

        monkeypatch.setattr(legal, "hoy", lambda: dt.date(2026, 6, 20))
        _producto(
            cliente,
            cuenta["cabeceras"],
            autorizacion_excepcional="AUT-2026-0417",
            autorizacion_hasta="2026-07-10",
        )
        avisos = cliente.get("/api/avisos", headers=cuenta["cabeceras"]).json()["avisos"]
        for aviso in avisos:
            assert not textos.palabras_prohibidas_encontradas(aviso["mensaje"])


class TestElTercerEstado_NoSeSabe:
    """«No lo sé» es una respuesta: no da permiso y no bloquea lo que de verdad ha pasado.

    Es el cierre del defecto **A1** de `docs/T02_VALORES_POR_DEFECTO.md`. Estas pruebas son las que
    impiden que el defecto permissivo vuelva por la puerta de atrás: con `True` por defecto, callar
    era lo mismo que dar permiso.
    """

    def _validar(self, cliente, cabeceras, campana, parcela, producto):
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cabeceras,
            json={
                "campana_id": campana["id"],
                "fecha": "2026-05-05",
                "parcela_id": parcela["id"],
                "superficie_tratada_ha": 1.0,
                "justificacion": "Vi la plaga o la hierba en el campo",
                "producto_id": producto["id"],
                "dosis": 0.5,
            },
        )
        assert respuesta.status_code == 200, respuesta.text
        return {aviso["codigo"]: aviso for aviso in respuesta.json()["avisos"]}

    def test_un_producto_sin_comprobar_no_pasa_por_bueno_en_silencio(
        self, cliente, cuenta, campana, parcela
    ):
        producto = _producto(cliente, cuenta["cabeceras"])
        avisos = self._validar(cliente, cuenta["cabeceras"], campana, parcela, producto)
        assert "V1_autorizacion_sin_comprobar" in avisos
        assert not avisos["V1_autorizacion_sin_comprobar"]["bloquea"], (
            "no saber no puede impedir apuntar lo que de verdad ha pasado en el campo"
        )
        assert "V1_no_autorizado" not in avisos

    def test_el_aviso_dice_qué_hacer_para_que_se_pueda_comprobar(
        self, cliente, cuenta, campana, parcela
    ):
        producto = _producto(cliente, cuenta["cabeceras"])
        avisos = self._validar(cliente, cuenta["cabeceras"], campana, parcela, producto)
        mensaje = avisos["V1_autorizacion_sin_comprobar"]["mensaje"].lower()
        assert "ficha del producto" in mensaje, "tiene que decir dónde se arregla"

    def test_el_apunte_se_puede_guardar_igual(self, cliente, cuenta, campana, parcela):
        """El aviso no bloquea de verdad, no solo de palabra."""
        producto = _producto(cliente, cuenta["cabeceras"])
        respuesta = _tratamiento(cliente, cuenta["cabeceras"], campana, parcela, producto)
        assert respuesta.status_code == 201, respuesta.text

    def test_en_una_finca_ecologica_un_producto_sin_comprobar_tambien_lo_dice(
        self, cliente, cuenta, campana, parcela
    ):
        """Aquí el defecto permissivo hacía el daño más grande: apagaba la comprobación del
        ecológico, que es la que más importa en una finca ecológica."""
        cliente.put(
            "/api/mi-finca", headers=cuenta["cabeceras"], json={"produccion_ecologica": True}
        )
        producto = _producto(cliente, cuenta["cabeceras"])
        avisos = self._validar(cliente, cuenta["cabeceras"], campana, parcela, producto)
        assert "V15_no_se_si_es_ecologico" in avisos
        assert not avisos["V15_no_se_si_es_ecologico"]["bloquea"]

    def test_en_una_finca_que_no_es_ecologica_no_se_habla_del_ecologico(
        self, cliente, cuenta, campana, parcela
    ):
        """Si la finca no es ecológica, el ecológico no viene a cuento: eso sería ruido."""
        producto = _producto(cliente, cuenta["cabeceras"])
        avisos = self._validar(cliente, cuenta["cabeceras"], campana, parcela, producto)
        assert "V15_no_se_si_es_ecologico" not in avisos

    def test_una_correccion_que_no_manda_la_autorizacion_no_la_borra(self, cliente, cuenta):
        """**El cuidado que pide una columna de tres estados.** En `PUT` no se distingue «me lo
        mandan vacío» de «no me lo mandan» salvo mirando `model_fields_set`, y un `None` de más
        borraría lo que el agricultor ya había comprobado: corregir la dosis no puede llevarse por
        delante la autorización."""
        producto = _producto(cliente, cuenta["cabeceras"], autorizado=True)
        corregido = cliente.put(
            f"/api/productos/{producto['id']}",
            headers=cuenta["cabeceras"],
            json={"nombre_comercial": "Ejemplo 25 EC", "numero_registro": "24.123", "dosis_maxima": 1.5},
        )
        assert corregido.status_code == 200, corregido.text
        assert corregido.json()["autorizado"] is True

    def test_y_si_la_corrección_dice_no_lo_sé_se_guarda_no_lo_sé(self, cliente, cuenta):
        producto = _producto(cliente, cuenta["cabeceras"], autorizado=True)
        corregido = cliente.put(
            f"/api/productos/{producto['id']}",
            headers=cuenta["cabeceras"],
            json={
                "nombre_comercial": "Ejemplo 25 EC",
                "numero_registro": "24.123",
                "autorizado": None,
            },
        ).json()
        assert corregido["autorizado"] is None


class TestLosTextosDeLasPreguntas:
    """Las preguntas viven en `ETIQUETAS_MAESTRO`, que es donde están las de las fichas que se dan
    de alta una vez («Mis cosas»), no en `ETIQUETAS`, que es el asistente de los apuntes. Las dos
    se sirven juntas a la pantalla y las dos entran en la revisión de jerga: aquí se busca en las
    dos, porque lo que importa es que la pregunta exista y se revise, no en qué cajón está.
    """

    CLAVES = (
        "producto.autorizado",
        "producto.permitido_ecologico",
        "producto.autorizacion_excepcional",
        "producto.autorizacion_hasta",
        "aplicador.tipo_carne",
        "aplicador.numero_reganip",
    )

    def _etiqueta(self, clave: str) -> dict:
        from app import textos

        return textos.ETIQUETAS.get(clave) or textos.ETIQUETAS_MAESTRO.get(clave) or {}

    def test_las_preguntas_nuevas_existen(self):
        for clave in self.CLAVES:
            etiqueta = self._etiqueta(clave)
            assert etiqueta, clave
            assert etiqueta["pregunta"]
            assert etiqueta["pista"]

    def test_se_sirven_a_la_pantalla(self, cliente):
        """Y llegan al navegador: una pregunta que existe en el servidor y no se sirve no se ve."""
        datos = cliente.get("/api/interfaz").json()
        etiquetas = datos["etiquetas"]
        for clave in self.CLAVES:
            assert clave in etiquetas, clave

    def test_no_llevan_jerga(self):
        from app import textos

        for clave in self.CLAVES:
            for valor in self._etiqueta(clave).values():
                assert not textos.palabras_prohibidas_encontradas(valor), (clave, valor)

    def test_entran_en_la_revision_de_jerga(self):
        from app import textos

        visibles = textos.textos_visibles()
        for clave in self.CLAVES:
            assert self._etiqueta(clave)["pregunta"] in visibles, clave

    def test_se_explica_qué_es_una_autorización_excepcional_sin_decir_el_nombre(self):
        """«Autorización excepcional» es el nombre del BOE; el agricultor dice «un permiso»."""
        pregunta = self._etiqueta("producto.autorizacion_excepcional")["pregunta"].lower()
        assert "permiso" in pregunta
        assert "excepcional" not in pregunta


# --------------------------------------------------------------------------
# La migración: las dos columnas del catálogo tienen que admitir el tercer estado
# --------------------------------------------------------------------------


def _motor_con_las_dos_columnas_obligatorias(tmp_path):
    """Una base como la de verdad: la tabla del catálogo, con sus dos columnas obligatorias.

    El `CREATE TABLE` no se escribe a mano: se coge el que genera el modelo y se le devuelve el
    `NOT NULL` a esas dos columnas, que es exactamente lo que tenían las bases creadas antes del
    02/10/2026. Así la prueba sigue valiendo aunque la tabla gane columnas.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.schema import CreateTable

    from app import models

    motor = create_engine(f"sqlite:///{(tmp_path / 'catalogo.db').as_posix()}")
    tabla = models.Base.metadata.tables["productos_fitosanitarios"]
    ddl = str(CreateTable(tabla).compile(dialect=motor.dialect))
    for columna in ("autorizado", "permitido_ecologico"):
        ddl = ddl.replace(f"{columna} BOOLEAN,", f"{columna} BOOLEAN NOT NULL,")
    assert "autorizado BOOLEAN NOT NULL," in ddl, "la prueba necesita las columnas obligatorias"
    # Con la conexión cruda y las claves foráneas apagadas: en esta base de prueba solo existe esta
    # tabla, así que la explotación de la ficha no está. Es a propósito (ver la prueba de las filas
    # huérfanas de `test_zona_de_nitratos_no_comprobado.py`).
    cruda = motor.raw_connection()
    try:
        cursor = cruda.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute(ddl)
        cursor.execute(
            "INSERT INTO productos_fitosanitarios (id, explotacion_id, nombre_comercial, "
            "unidad_dosis, unidad_compra, autorizado, permitido_ecologico) "
            "VALUES (1, 1, 'Karate Zeon', 'L/ha', 'L', 1, 1)"
        )
        cruda.commit()
        cursor.close()
    finally:
        cruda.close()
    return motor


class TestLaMigracionDelCatalogo:
    """La columna tiene que poder guardar el tercer estado, y la tabla no puede perder nada."""

    def test_las_dos_columnas_pasan_a_admitir_el_tercer_estado(self, tmp_path):
        motor = _motor_con_las_dos_columnas_obligatorias(tmp_path)
        hechas = database.reconstruir_para_poder_decir_no_se(motor)
        assert sorted(hechas) == [
            "productos_fitosanitarios.autorizado",
            "productos_fitosanitarios.permitido_ecologico",
        ]
        columnas = {c["name"]: c for c in inspect(motor).get_columns("productos_fitosanitarios")}
        assert columnas["autorizado"]["nullable"] is True
        assert columnas["permitido_ecologico"]["nullable"] is True

    def test_la_tabla_se_reconstruye_una_sola_vez(self, tmp_path):
        """Dos columnas en la misma tabla son **una** reconstrucción, no dos.

        Se mira cuántas veces se ha **hecho la copia**, y no cuántos ficheros hay: una reconstrucción deja
        dos ficheros a propósito (la copia coherente y la idéntica byte a byte) y eso no es hacer el trabajo
        dos veces. Lo que no puede pasar es que la tabla se reconstruya dos veces: sería pasar dos veces por
        la ventana de riesgo sin ganar nada.
        """
        motor = _motor_con_las_dos_columnas_obligatorias(tmp_path)
        database.reconstruir_para_poder_decir_no_se(motor)
        coherentes = [
            copia
            for copia in tmp_path.glob("catalogo.db.antes-de-migrar-*")
            if not copia.name.endswith("-byte-a-byte")
        ]
        assert len(coherentes) == 1, f"una copia por reconstrucción, no una por columna: {coherentes}"
        identicas = list(tmp_path.glob("catalogo.db.antes-de-migrar-*-byte-a-byte"))
        assert len(identicas) == 1, f"y la copia idéntica, una: {identicas}"

    def test_el_catalogo_no_pierde_ningun_producto_ni_cambia_sus_datos(self, tmp_path):
        motor = _motor_con_las_dos_columnas_obligatorias(tmp_path)
        with motor.begin() as conexion:
            antes = conexion.execute(
                text("SELECT * FROM productos_fitosanitarios ORDER BY id")
            ).fetchall()

        database.reconstruir_para_poder_decir_no_se(motor)

        with motor.begin() as conexion:
            despues = conexion.execute(
                text("SELECT * FROM productos_fitosanitarios ORDER BY id")
            ).fetchall()
            # Y ahora la ficha sí puede decir «no comprobado», que es lo que hacía falta.
            conexion.execute(
                text("UPDATE productos_fitosanitarios SET autorizado = NULL WHERE id = 1")
            )
            valor = conexion.execute(
                text("SELECT autorizado FROM productos_fitosanitarios WHERE id = 1")
            ).scalar_one()
        assert despues == antes, "la reconstrucción no puede cambiar ni un dato"
        assert valor is None

    def test_hacerlo_dos_veces_no_cambia_nada(self, tmp_path):
        motor = _motor_con_las_dos_columnas_obligatorias(tmp_path)
        assert database.reconstruir_para_poder_decir_no_se(motor)
        assert database.reconstruir_para_poder_decir_no_se(motor) == []

    def test_los_productos_que_ya_estaban_no_se_reescriben_solos(self, tmp_path):
        """**Decisión, no olvido.** En una ficha vieja no hay forma de saber si el «sí está
        autorizado» lo escribió el agricultor o lo puso el programa: el alta de un producto no deja
        rastro en la auditoría. Cambiarlo a «no comprobado» borraría un dato que sí era un dato, así
        que no se toca y se arregla desde la pantalla, ficha a ficha. Lo que se migra es el
        **esquema**, no el contenido.
        """
        motor = _motor_con_las_dos_columnas_obligatorias(tmp_path)
        database.reconstruir_para_poder_decir_no_se(motor)
        with motor.begin() as conexion:
            fila = conexion.execute(
                text("SELECT autorizado, permitido_ecologico FROM productos_fitosanitarios")
            ).one()
        assert tuple(fila) == (1, 1), "ningún producto se reescribe solo"


class TestLaRevisionAManoDelCatalogo:
    """El guion de migración no cambia esas fichas: **las lista**, para que se puedan revisar.

    Es la otra mitad de la decisión de arriba. Si no se reescriben solas, tiene que haber una forma
    de saber cuáles mirar; si no, quedan «pendientes» para siempre y nadie se acuerda de ellas.
    """

    def _el_guion(self):
        import importlib.util
        import pathlib as _pathlib

        ruta = _pathlib.Path(__file__).resolve().parents[1] / "scripts" / "migrar_zona_de_nitratos.py"
        especificacion = importlib.util.spec_from_file_location("migrar_zonas", ruta)
        modulo = importlib.util.module_from_spec(especificacion)
        especificacion.loader.exec_module(modulo)
        return modulo

    def _base_con_productos(self, tmp_path, filas: list[tuple]):
        """Una base con la tabla del catálogo y los productos que diga cada prueba.

        Se crea con las columnas ya anulables (el estado de después del arranque) porque lo que se
        prueba aquí es el **informe**, no la reconstrucción, que tiene sus propias pruebas.
        """
        from sqlalchemy import create_engine
        from sqlalchemy.schema import CreateTable

        from app import models

        motor = create_engine(f"sqlite:///{(tmp_path / 'catalogo_para_revisar.db').as_posix()}")
        tabla = models.Base.metadata.tables["productos_fitosanitarios"]
        ddl = str(CreateTable(tabla).compile(dialect=motor.dialect))
        cruda = motor.raw_connection()
        try:
            cursor = cruda.cursor()
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.execute(ddl)
            for identificador, nombre, autorizado, ecologico in filas:
                cursor.execute(
                    "INSERT INTO productos_fitosanitarios (id, explotacion_id, nombre_comercial, "
                    "unidad_dosis, unidad_compra, autorizado, permitido_ecologico) "
                    "VALUES (?, 1, ?, 'L/ha', 'L', ?, ?)",
                    (identificador, nombre, autorizado, ecologico),
                )
            cruda.commit()
            cursor.close()
        finally:
            cruda.close()
        return motor

    def test_lista_los_productos_con_su_respuesta_y_dice_cuales_mirar(self, tmp_path, capsys):
        """El agricultor tiene que poder ver **qué ficha** mirar y qué dice hoy, no un «hay 1»."""
        import sqlite3

        motor = self._base_con_productos(
            tmp_path,
            [
                (1, "Glifosato 36 SL", 1, 1),
                (2, "Cobre 50", None, None),
            ],
        )
        with sqlite3.connect(motor.url.database) as conexion:
            self._el_guion()._revision_de_los_productos(conexion)

        salida = capsys.readouterr().out
        assert "Glifosato 36 SL" in salida, "no dice qué producto hay que revisar"
        assert "autorizado: sí" in salida
        assert "no comprobado" in salida, "no distingue el que ya está sin comprobar"
        assert "2 productos en total" in salida
        assert "NO se puede saber" in salida, "no dice que eso no se puede deducir"

    def test_solo_el_que_esta_sin_comprobar_cuenta_como_revisado(self, tmp_path, capsys):
        import sqlite3

        motor = self._base_con_productos(tmp_path, [(1, "Cobre 50", None, None)])
        with sqlite3.connect(motor.url.database) as conexion:
            self._el_guion()._revision_de_los_productos(conexion)
        salida = capsys.readouterr().out
        assert "1 producto en total" in salida, "el singular se lee mal si dice «1 productos»"
        assert "1 ya dicen" in salida

    def test_el_informe_no_cambia_ni_una_ficha(self, tmp_path):
        """**Lo que no puede pasar**: que el informe se lleve por delante lo que venía a enseñar."""
        import sqlite3

        motor = self._base_con_productos(tmp_path, [(1, "Glifosato 36 SL", 1, 0)])
        with sqlite3.connect(motor.url.database) as conexion:
            antes = conexion.execute(
                "SELECT autorizado, permitido_ecologico FROM productos_fitosanitarios"
            ).fetchall()
            self._el_guion()._revision_de_los_productos(conexion)
            despues = conexion.execute(
                "SELECT autorizado, permitido_ecologico FROM productos_fitosanitarios"
            ).fetchall()
        assert despues == antes, "el informe ha tocado una ficha que solo venía a enseñar"

    def test_con_el_catalogo_vacio_lo_dice_y_no_revienta(self, tmp_path, capsys):
        import sqlite3

        motor = self._base_con_productos(tmp_path, [])
        with sqlite3.connect(motor.url.database) as conexion:
            self._el_guion()._revision_de_los_productos(conexion)
        assert "no hay ningún producto" in capsys.readouterr().out
