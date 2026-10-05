"""Tests de las naves y almacenes, y de las clases de tratamiento.

Hacen falta por dos motivos, y los dos son obligaciones del cuaderno:

1. **Tratamiento de instalaciones**: cuando se trata una nave, el producto no se echa en
   la tierra. Sin poder apuntar la nave, esa sección del cuaderno oficial no se puede
   cumplimentar de ninguna manera. Es el único hueco que era imposible de tapar sin esto.
2. **Distinguir de qué clase es cada aplicación.** La app oficial tiene cuatro secciones
   separadas (tratamiento, semilla tratada, postcosecha, instalaciones) y aquí son el
   mismo registro con distinto «dónde». Lo que cambia es qué se exige: una parcela o un
   local.
"""

from __future__ import annotations


class TestLasInstalaciones:
    def test_se_da_de_alta_una_nave(self, cliente, cuenta, crear_instalacion):
        nave = crear_instalacion(alias="La nave del grano", tipo="nave")
        assert nave["alias"] == "La nave del grano"
        assert nave["tipo"] == "nave"

    def test_se_listan(self, cliente, cuenta, crear_instalacion):
        crear_instalacion(alias="Uno")
        crear_instalacion(alias="Dos")
        listado = cliente.get("/api/instalaciones", headers=cuenta["cabeceras"]).json()
        assert len(listado) == 2
        assert [i["alias"] for i in listado] == ["Dos", "Uno"]  # ordenadas por nombre

    def test_se_puede_ver_una(self, cliente, cuenta, instalacion):
        respuesta = cliente.get(
            f"/api/instalaciones/{instalacion['id']}", headers=cuenta["cabeceras"]
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["id"] == instalacion["id"]

    def test_un_tipo_que_no_existe_se_rechaza(self, cliente, cuenta):
        respuesta = cliente.post(
            "/api/instalaciones",
            headers=cuenta["cabeceras"],
            json={"alias": "Rara", "tipo": "castillo"},
        )
        assert respuesta.status_code == 422
        assert "almacen" in respuesta.json()["detail"]

    def test_la_referencia_catastral_se_guarda(self, cliente, cuenta, crear_instalacion):
        """Es lo que identifica una nave delante de la administración: no tiene SIGPAC."""
        nave = crear_instalacion(referencia_catastral="37181A012000450000FP")
        assert nave["referencia_catastral"] == "37181A012000450000FP"

    def test_cada_finca_ve_solo_sus_naves(self, cliente, cuenta, crear_instalacion, crear_cuenta):
        crear_instalacion(alias="Mía")
        otro = crear_cuenta("otro@ejemplo.test")
        assert cliente.get("/api/instalaciones", headers=otro["cabeceras"]).json() == []

    def test_no_se_puede_ver_una_nave_de_otra_finca(
        self, cliente, cuenta, instalacion, crear_cuenta
    ):
        otro = crear_cuenta("otro@ejemplo.test")
        respuesta = cliente.get(
            f"/api/instalaciones/{instalacion['id']}", headers=otro["cabeceras"]
        )
        assert respuesta.status_code == 404

    def test_hace_falta_entrar(self, cliente):
        assert cliente.get("/api/instalaciones").status_code == 401


class TestTratamientoDeInstalaciones:
    """La sección que era imposible de cumplimentar sin las naves."""

    def test_se_apunta_un_tratamiento_en_una_nave(
        self, cliente, cuenta, nuevo_tratamiento_en_instalacion, instalacion
    ):
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento_en_instalacion(),
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["tipo"] == "instalaciones"
        assert datos["instalacion_id"] == instalacion["id"]
        assert datos["parcela_id"] is None
        assert datos["plazo_reentrada_dias"] == 3

    def test_una_nave_no_necesita_hectareas(
        self, cliente, cuenta, nuevo_tratamiento_en_instalacion
    ):
        """Una nave no se mide en hectáreas, así que no se piden."""
        carga = nuevo_tratamiento_en_instalacion()
        assert "superficie_tratada_ha" not in carga
        respuesta = cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=carga)
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["superficie_tratada_ha"] == 0

    def test_sin_decir_la_nave_no_se_puede_apuntar(
        self, cliente, cuenta, nuevo_tratamiento_en_instalacion
    ):
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento_en_instalacion(instalacion_id=None),
        )
        assert respuesta.status_code == 422
        codigos = [a["codigo"] for a in respuesta.json()["detail"]["avisos"]]
        assert "V20_sin_instalacion" in codigos

    def test_el_aviso_dice_qué_hacer(
        self, cliente, cuenta, nuevo_tratamiento_en_instalacion
    ):
        respuesta = cliente.post(
            "/api/tratamientos/validar",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento_en_instalacion(instalacion_id=None),
        )
        aviso = next(a for a in respuesta.json()["avisos"] if a["codigo"] == "V20_sin_instalacion")
        assert "nave" in aviso["mensaje"]
        assert "apuntarlo" in aviso["mensaje"], "no dice para qué"

    def test_no_se_puede_apuntar_en_una_nave_de_otra_finca(
        self, cliente, cuenta, crear_cuenta, nuevo_tratamiento_en_instalacion, instalacion
    ):
        otro = crear_cuenta("otro@ejemplo.test")
        campana_ajena = cliente.get("/api/campanas/actual", headers=otro["cabeceras"]).json()
        producto_ajeno = cliente.post(
            "/api/productos",
            headers=otro["cabeceras"],
            json={"nombre_comercial": "Suyo", "numero_registro": "1.111"},
        ).json()
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=otro["cabeceras"],
            json={
                **nuevo_tratamiento_en_instalacion(),
                "campana_id": campana_ajena["id"],
                "producto_id": producto_ajeno["id"],
            },
        )
        assert respuesta.status_code == 404


class TestPostcosecha:
    def test_se_apunta_al_producto_ya_recogido(
        self, cliente, cuenta, nuevo_tratamiento_en_instalacion
    ):
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento_en_instalacion(
                tipo="postcosecha",
                producto_cosechado="Trigo",
                lote_cosecha="L-2026-07",
            ),
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["tipo"] == "postcosecha"
        assert datos["producto_cosechado"] == "Trigo"
        assert datos["lote_cosecha"] == "L-2026-07"


class TestSemillaTratada:
    def test_la_semilla_tratada_va_en_la_parcela_donde_se_siembra(
        self, cliente, cuenta, nuevo_tratamiento
    ):
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(tipo="semilla_tratada"),
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["tipo"] == "semilla_tratada"
        assert datos["parcela_id"] is not None, "la semilla se siembra en una parcela"

    def test_sin_parcela_no_se_puede_apuntar(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(tipo="semilla_tratada", parcela_id=None),
        )
        assert respuesta.status_code == 422
        codigos = [a["codigo"] for a in respuesta.json()["detail"]["avisos"]]
        assert "V18_sin_parcela" in codigos


class TestLoDeSiempreSigueFuncionando:
    """Un tratamiento normal no puede haberse estropeado al añadir todo esto."""

    def test_un_tratamiento_de_parcela_sigue_igual(self, cliente, cuenta, nuevo_tratamiento):
        respuesta = cliente.post(
            "/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento()
        )
        assert respuesta.status_code == 201, respuesta.text
        datos = respuesta.json()
        assert datos["tipo"] == "parcela", "por defecto tiene que ser en la parcela"
        assert datos["parcela_id"] is not None
        assert datos["superficie_tratada_ha"] == 2.43
        assert datos["fecha_fin_plazo_seguridad"] == "2026-05-22"

    def test_sin_hectareas_en_una_parcela_se_pide(
        self, cliente, cuenta, nuevo_tratamiento
    ):
        """En la tierra sí hacen falta: es lo que multiplica la dosis."""
        respuesta = cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento(superficie_tratada_ha=None),
        )
        assert respuesta.status_code == 422
        codigos = [a["codigo"] for a in respuesta.json()["detail"]["avisos"]]
        assert "V22_sin_superficie" in codigos

    def test_los_dos_tipos_se_pueden_listar_juntos(
        self, cliente, cuenta, campana, nuevo_tratamiento, nuevo_tratamiento_en_instalacion
    ):
        cliente.post("/api/tratamientos", headers=cuenta["cabeceras"], json=nuevo_tratamiento())
        cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento_en_instalacion(),
        )
        listado = cliente.get("/api/tratamientos", headers=cuenta["cabeceras"]).json()
        assert len(listado) == 2
        assert {t["tipo"] for t in listado} == {"parcela", "instalaciones"}

    def test_la_firma_del_cuaderno_incluye_las_naves(
        self, cliente, cuenta, nuevo_tratamiento_en_instalacion, monkeypatch
    ):
        """Si la nave no va al fichero que se firma, la firma no cubre todo el cuaderno."""
        monkeypatch.setenv("CUEDIGITAL_CONFIAR_EN_CABECERAS", "1")
        cliente.post(
            "/api/tratamientos",
            headers=cuenta["cabeceras"],
            json=nuevo_tratamiento_en_instalacion(),
        )
        preparado = cliente.get("/api/firmas/preparar", headers=cuenta["cabeceras"]).json()
        assert "Nave o almacén: El almacén grande" in preparado["contenido"]
        assert "Clase de aplicación: instalaciones" in preparado["contenido"]


class TestLaInterfazDeLasInstalaciones:
    def test_la_interfaz_trae_las_preguntas_de_las_naves(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        for clave in (
            "instalacion.alias",
            "instalacion.tipo",
            "instalacion.referencia_catastral",
            "instalacion.uso",
        ):
            assert datos["etiquetas"].get(clave), f"falta la etiqueta {clave}"

    def test_la_interfaz_trae_los_tipos_con_su_nombre(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        tipos = {item["valor"]: item["texto"] for item in datos["tipos_instalacion"]}
        assert tipos["almacen"] == "Almacén"
        assert tipos["nave"] == "Nave"

    def test_la_interfaz_trae_las_clases_de_tratamiento(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        clases = {item["valor"]: item["texto"] for item in datos["tipos_tratamiento"]}
        assert set(clases) == {"parcela", "semilla_tratada", "postcosecha", "instalaciones"}
        assert all(clases.values()), "alguna clase se ha quedado sin nombre"

    def test_la_seccion_de_naves_esta_en_mis_cosas(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        for clave in (
            "seccion_instalacion",
            "pista_instalacion",
            "sin_instalacion",
            "anadir_instalacion",
            "instalacion_se_usa",
        ):
            assert datos["maestros"].get(clave), f"falta maestros.{clave}"
