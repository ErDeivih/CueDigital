"""T06 — Las tierras de la finca, en el mapa y en la tabla (03/10/2026).

**Qué comprueba este fichero.** Lo que el contrato pide para T06 en su parte de servidor, que es la
mitad del ticket que no se ve en una captura:

  · que una tierra **sin forma** sigue en la lista, con `tiene_forma` en falso y **sin anillos** (no
    se le dibuja un cuadro que nadie ha medido);
  · que los recuentos del pie son los de la finca entera, y que **no hay ningún total de hectáreas**
    calculado en el servidor (un total que sumara las superficies que no se saben sería una cifra
    inventada);
  · que el mapa de la finca **no tiene caja** cuando ninguna tierra tiene forma, y que cuando la
    tiene, la caja envuelve las formas de verdad y **siempre agrandada hasta el mínimo que acepta el
    servicio de mapas** (sin cambiar de sitio);
  · que los filtros salen de las tierras que hay, con su recuento, y **con el mismo criterio con el
    que filtra la pantalla**;
  · que una tierra de **otra finca** no aparece por ningún lado;
  · que la versión de la campaña es la que da el estado de revisión y las hectáreas declaradas;
  · que una geometría multiparte sale en **anillos separados**, no en una lista plana de puntos (que
    dibujaría una raya de un trozo al otro);
  · y que `/api/mapa/estado` dice qué enseña cada capa, que la fecha de la imagen **no se sabe** (y
    lo dice), y que las capas se pueden ocultar.

**Nada de esto toca la base del agricultor**: la suite fija `CUEDIGITAL_DATABASE_URL` a una carpeta
temporal antes de importar nada de `app` (`tests/conftest.py`).
"""

from __future__ import annotations

from app import textos

# Una forma de verdad, en coordenadas de Salamanca, del tamaño de una parcela.
UN_WKT = "POLYGON((-5.5600 40.9000, -5.5500 40.9000, -5.5500 40.9100, -5.5600 40.9100, -5.5600 40.9000))"
OTRO_WKT = "POLYGON((-5.5000 40.9500, -5.4900 40.9500, -5.4900 40.9600, -5.5000 40.9600, -5.5000 40.9500))"
# Dos trozos separados: es el caso que una lista plana de puntos dibujaría mal.
MULTIPARTE = (
    "MULTIPOLYGON(((-5.56 40.90, -5.55 40.90, -5.55 40.91, -5.56 40.91, -5.56 40.90)),"
    "((-5.50 40.95, -5.49 40.95, -5.49 40.96, -5.50 40.96, -5.50 40.95)))"
)


def _la_vista(cliente, cuenta, **parametros):
    respuesta = cliente.get("/api/parcelas/vista", headers=cuenta["cabeceras"], params=parametros)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _una_tierra(datos: list[dict], alias: str) -> dict:
    encontrada = next((tierra for tierra in datos if tierra["alias"] == alias), None)
    assert encontrada is not None, f"no está «{alias}»: {[t['alias'] for t in datos]}"
    return encontrada


class TestUnaTierraSinFormaNoDesaparece:
    def test_la_tierra_sin_forma_sigue_en_la_lista_y_no_se_le_dibuja_nada(self, cliente, cuenta, crear_parcela):
        """El contrato §2.1: «Una fila sin polígono sigue en la tabla y en un grupo «sin forma»».

        Aquí se comprueba la mitad del servidor: la tierra **está** en la respuesta, con
        `tiene_forma` en falso y **sin ningún anillo**. Lo que no se hace es dibujarle un cuadro:
        eso sería una forma que nadie ha medido.
        """
        crear_parcela(alias="Sin forma", geometria=None)
        crear_parcela(alias="Con forma", geometria=UN_WKT)

        datos = _la_vista(cliente, cuenta)["tierras"]
        sin_forma = _una_tierra(datos, "Sin forma")

        assert sin_forma["tiene_forma"] is False
        assert sin_forma["anillos"] == []
        assert sin_forma["forma"] is None
        assert _una_tierra(datos, "Con forma")["tiene_forma"] is True

    def test_un_multipoligono_sale_en_anillos_separados(self, cliente, cuenta, crear_parcela):
        """Dos trozos son **dos anillos**, no una lista de puntos con una raya en medio."""
        crear_parcela(alias="Partida en dos", geometria=MULTIPARTE)

        tierra = _una_tierra(_la_vista(cliente, cuenta)["tierras"], "Partida en dos")

        assert tierra["tiene_forma"] is True
        assert len(tierra["anillos"]) == 2, tierra["anillos"]
        # Y cada anillo es un trozo cerrado de la misma forma: cuatro esquinas.
        assert all(len(anillo) == 4 for anillo in tierra["anillos"])

    def test_la_tierra_sin_hectareas_las_tiene_en_blanco_y_no_en_cero(self, cliente, cuenta, crear_parcela):
        """`None` es «no lo sé» y **no** es cero (`docs/T02_VALORES_POR_DEFECTO.md`)."""
        crear_parcela(alias="Sin hectáreas", superficie_ha=None)

        tierra = _una_tierra(_la_vista(cliente, cuenta)["tierras"], "Sin hectáreas")

        assert tierra["superficie_ha"] is None
        assert tierra["tiene_hectareas_dichas"] is False


class TestLosRecuentosDelPie:
    def test_los_recuentos_son_los_de_la_finca_entera(self, cliente, cuenta, crear_parcela):
        """El pie dice «ves 10 de 64» con esos dos números, y los dos salen de aquí."""
        crear_parcela(alias="A", geometria=UN_WKT)
        crear_parcela(alias="B", geometria=None, superficie_ha=None)
        crear_parcela(alias="C", geometria=OTRO_WKT)

        datos = _la_vista(cliente, cuenta)

        assert datos["totales"]["tierras"] == 3
        assert datos["totales"]["con_forma"] == 2
        assert datos["totales"]["sin_forma"] == 1
        assert datos["totales"]["sin_hectareas"] == 1
        # Y las tres están sin decir qué tienen: no se ha declarado ningún cultivo.
        assert datos["totales"]["sin_cultivo"] == 3

    def test_no_se_ofrece_ningun_total_de_hectareas(self, cliente, cuenta, crear_parcela):
        """**Ni una cifra que el servidor no haya calculado, y ninguna que sume huecos.**

        La mitad de las tierras de un agricultor pueden tener la superficie en blanco. Un total que
        las sumara como cero sería falso, y uno que solo sumara las conocidas diría menos de lo que
        parece. Por eso no hay ningún total de superficie en esta respuesta, y esta prueba lo fija
        para que nadie lo añada «porque queda bien en el pie».
        """
        crear_parcela(alias="Con hectáreas", superficie_ha=2.43)
        crear_parcela(alias="Sin hectáreas", superficie_ha=None)

        datos = _la_vista(cliente, cuenta)

        # La lista de lo que puede llevar el pie, escrita entera: si mañana alguien añade una
        # superficie sumada, esta prueba se pone roja y le obliga a justificarla.
        assert set(datos["totales"]) == {
            "tierras",
            "con_forma",
            "sin_forma",
            "sin_cultivo",
            "sin_hectareas",
            "sin_revision",
        }
        # Y lo mismo con lo que devuelve la llamada entera: si aparece una cifra nueva, hay que
        # justificarla aquí.
        assert set(datos) == {
            "textos",
            "textos_de_las_versiones",
            "campana_id",
            "campana_anio",
            "tierras",
            "totales",
            "mapa",
            "filtros",
        }


class TestElMapaDeLaFinca:
    def test_sin_ninguna_forma_no_hay_caja_y_el_mapa_no_se_inventa_un_centro(
        self, cliente, cuenta, crear_parcela
    ):
        """**El mapa no salta a otra provincia ni inventa un centro.**

        Sin ninguna forma medida no hay nada que enseñar: `hay_forma` en falso y la caja vacía. La
        pantalla lo dice y ofrece la tabla, que funciona igual.
        """
        crear_parcela(alias="Sin forma 1", geometria=None)
        crear_parcela(alias="Sin forma 2", geometria=None)

        mapa = _la_vista(cliente, cuenta)["mapa"]

        assert mapa["hay_forma"] is False
        assert mapa["caja"] is None
        assert mapa["tierras_con_forma"] == 0

    def test_la_caja_envuelve_las_formas_que_de_verdad_hay(self, cliente, cuenta, crear_parcela):
        crear_parcela(alias="Una", geometria=UN_WKT)
        crear_parcela(alias="Otra", geometria=OTRO_WKT)

        mapa = _la_vista(cliente, cuenta)["mapa"]

        assert mapa["hay_forma"] is True
        assert mapa["tierras_con_forma"] == 2
        caja = mapa["caja"]
        # La primera forma va de -5,56 a -5,55 y la segunda de -5,50 a -5,49.
        assert caja["oeste"] == -5.56
        assert caja["este"] == -5.49
        assert caja["sur"] == 40.90
        assert caja["norte"] == 40.96

    def test_una_forma_minuscula_se_agranda_al_minimo_sin_cambiar_de_sitio(
        self, cliente, cuenta, crear_parcela
    ):
        """Un trozo de 40 metros mide menos de lo que acepta el servicio de mapas.

        Lo que se hace es **agrandar la caja alrededor de su propio centro**, que es enseñar la misma
        tierra más de cerca. Lo que no se hace es abrir el mapa en otro sitio.
        """
        diminuta = "POLYGON((-5.56000 40.90000, -5.55960 40.90000, -5.55960 40.90040, -5.56000 40.90040, -5.56000 40.90000))"
        crear_parcela(alias="Diminuta", geometria=diminuta)

        caja = _la_vista(cliente, cuenta)["mapa"]["caja"]

        lado = max(caja["este"] - caja["oeste"], caja["norte"] - caja["sur"])
        assert lado >= 0.0008, f"la caja se queda por debajo del mínimo: {lado}"
        # Y sigue conteniendo la tierra: el centro no se ha movido.
        assert caja["oeste"] < -5.5599 < caja["este"]
        assert caja["sur"] < 40.9001 < caja["norte"]


class TestLosFiltros:
    def test_los_filtros_salen_de_las_tierras_que_hay_con_su_recuento(self, cliente, cuenta, crear_parcela):
        """Ni una lista escrita a mano: un pueblo que no está en ninguna tierra no se ofrece."""
        crear_parcela(alias="A", municipio="Peñaranda de Bracamonte", geometria=UN_WKT)
        crear_parcela(alias="B", municipio="Peñaranda de Bracamonte", geometria=None)
        crear_parcela(alias="C", municipio="Macotera", geometria=None)

        filtros = _la_vista(cliente, cuenta)["filtros"]

        pueblos = {opcion["valor"]: opcion["cuantas"] for opcion in filtros["municipios"]}
        assert pueblos["Peñaranda de Bracamonte"] == 2
        assert pueblos["Macotera"] == 1
        assert "Salamanca" not in pueblos, "se ofrece un pueblo que no tiene ninguna tierra"

    def test_el_filtro_de_la_pac_cuenta_los_mismos_hechos_que_la_pantalla(self, cliente, cuenta, crear_parcela):
        """Las opciones del filtro de la PAC son **hechos**, y ninguno dice «cumple»."""
        # Completa: los tres números del recinto.
        crear_parcela(alias="Completa", poligono=503, numero_parcela=51, numero_recinto=1, superficie_ha=2.4)
        # A medias: le falta el número de recinto, que es el que hace que la referencia lo sea.
        crear_parcela(alias="A medias", poligono=503, numero_parcela=52, numero_recinto=None, superficie_ha=None)

        filtros = _la_vista(cliente, cuenta)["filtros"]
        por_valor = {opcion["valor"]: opcion["cuantas"] for opcion in filtros["pac"]}

        assert por_valor["con_referencia"] == 1
        assert por_valor["sin_referencia"] == 1
        assert por_valor["con_hectareas"] == 1
        assert por_valor["sin_hectareas"] == 1
        # Y ninguna opción promete algo que este programa no sabe comprobar.
        for opcion in filtros["pac"]:
            assert "cumple" not in opcion["texto"].lower()
            assert "autoriz" not in opcion["texto"].lower()

    def test_una_tierra_sin_ninguna_version_se_ofrece_como_tal_y_no_como_sin_revisar(
        self, cliente, cuenta, crear_parcela
    ):
        """«Sin revisar» y «sin ninguna versión» no son lo mismo: lo segundo no lo ha mirado nadie."""
        crear_parcela(alias="Sin versiones")

        filtros = _la_vista(cliente, cuenta)["filtros"]
        valores = [opcion["valor"] for opcion in filtros["revisiones"]]

        assert "sin_version" in valores
        assert "sin_revisar" not in valores, "se ofrece «sin revisar» de una tierra que no tiene versión"


class TestLaVersionDeLaCampana:
    def test_la_version_da_el_estado_de_revision_y_las_hectareas_declaradas(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """El estado de revisión y lo declarado **no están en la tierra**: están en su versión."""
        parcela = crear_parcela(alias="El Prado", geometria=UN_WKT)
        lote = {
            "campana_id": campana["id"],
            "fuente": "sigpac",
            "recintos": [
                {
                    "parcela_id": parcela["id"],
                    "poligono": 503,
                    "numero_parcela": 51,
                    "numero_recinto": 1,
                    "geometria": UN_WKT,
                    "area_sigpac_ha": 2.7923,
                    "area_declarada_ha": 2.5,
                    "estado_revision": "revisado",
                }
            ],
        }
        aplicado = cliente.post("/api/versiones/aplicar", headers=cuenta["cabeceras"], json=lote)
        assert aplicado.status_code == 200, aplicado.text

        tierra = _una_tierra(_la_vista(cliente, cuenta)["tierras"], "El Prado")

        assert tierra["estado_revision"] == "revisado"
        assert tierra["estado_revision_texto"] == textos.VERSIONES_DE_RECINTO["revision_revisado"]
        assert tierra["area_declarada_ha"] == 2.5
        assert tierra["fuente_texto"] == textos.VERSIONES_DE_RECINTO["fuente_sigpac"]
        assert tierra["anio_de_la_version"] == campana["anio"]

    def test_la_vista_no_escribe_nada(self, cliente, cuenta, crear_parcela):
        """Pedir la vista dos veces deja la finca exactamente como estaba."""
        crear_parcela(alias="El Prado", geometria=UN_WKT)

        primera = _la_vista(cliente, cuenta)
        segunda = _la_vista(cliente, cuenta)

        assert primera == segunda
        assert cliente.get("/api/versiones", headers=cuenta["cabeceras"]).json() == []


class TestElAislamientoEntreFincas:
    def test_no_se_ven_las_tierras_de_otra_finca(self, cliente, cuenta, crear_cuenta, crear_parcela):
        """`explotacion_id` va por delante en todas las consultas."""
        crear_parcela(alias="Mía", geometria=UN_WKT)
        otro = crear_cuenta(correo="otro@ejemplo.test", nombre="Otro", nif="12345678Z")
        respuesta = cliente.post(
            "/api/parcelas",
            headers=otro["cabeceras"],
            json={"alias": "Del otro", "geometria": OTRO_WKT, "superficie_ha": 9.9},
        )
        assert respuesta.status_code == 201, respuesta.text

        datos = _la_vista(cliente, cuenta)

        assert [tierra["alias"] for tierra in datos["tierras"]] == ["Mía"]
        assert datos["totales"]["tierras"] == 1

    def test_una_campana_de_otra_finca_contesta_404_y_no_403(self, cliente, cuenta, crear_cuenta):
        """No se dice si ese identificador existe en el cuaderno de otro (`deps.py`)."""
        otro = crear_cuenta(correo="otro@ejemplo.test", nombre="Otro", nif="12345678Z")
        suya = cliente.get("/api/campanas/actual", headers=otro["cabeceras"]).json()

        respuesta = cliente.get(
            "/api/parcelas/vista",
            headers=cuenta["cabeceras"],
            params={"campana_id": suya["id"]},
        )

        assert respuesta.status_code == 404, respuesta.text


class TestLoQueDijeronLosDatosDeVerdad:
    """Lo que se aprendió mirando los datos reales del agricultor (03/10/2026).

    No son precauciones teóricas: salen de mirar una **copia** de su base de datos y contar. Están aquí
    para que no se «arreglen» volviendo a lo de antes.

    **Y una advertencia de método, que costó un dato falso en la documentación:** cuando aquí se diga
    «medido», tiene que decir **sobre qué finca** se midió. Una base puede tener varias explotaciones, y
    un recuento de toda la base **no es** un recuento de la finca del agricultor.
    """

    def test_el_mismo_pueblo_escrito_de_dos_formas_es_una_sola_opcion(
        self, cliente, cuenta, crear_parcela
    ):
        """El mismo pueblo escrito de dos maneras tiene que ser **una sola opción** en el filtro.

        **Por qué esta prueba hace falta, con el caso de verdad:** su cuaderno escribe `MACHACON`
        (como lo escribe la Junta, sin tilde) y la lista oficial del INE escribe `Machacón` (con
        tilde), que es de donde el formulario coge el pueblo cuando se elige del listado: **el mismo
        pueblo escrito de dos maneras según quién lo escriba**. Y a eso se suman los nombres con dos
        espacios de dentro, de teclearlos a mano. El día que apunte una tierra más eligiendo su pueblo
        de la lista tendrá las dos formas en la misma finca.

        Si el filtro cotejara el texto tal cual (o juntara solo por mayúsculas), en la lista de
        pueblos saldrían dos entradas para el mismo pueblo, y además **el número de la opción y las
        filas que salen al elegirla no cuadrarían**: diría 3 y enseñaría 4. Las opciones se juntan con
        la misma normalización que usa la pantalla y **el recuento se suma**.

        Los datos de esta prueba **los monta la prueba** (tres formas del mismo pueblo y otro
        distinto): no lee la base del agricultor, que es la regla de toda la suite.
        """
        crear_parcela(alias="Una", municipio="CALVARRASA DE ARRIBA")
        crear_parcela(alias="Otra", municipio="Calvarrasa de Arriba")
        crear_parcela(alias="Tercera", municipio="calvarrasa de arriba")
        crear_parcela(alias="De otro pueblo", municipio="MACHACON")

        filtros = _la_vista(cliente, cuenta)["filtros"]
        pueblos = {opcion["valor"]: opcion["cuantas"] for opcion in filtros["municipios"]}

        assert len(pueblos) == 2, f"el mismo pueblo sale más de una vez: {pueblos}"
        assert pueblos["CALVARRASA DE ARRIBA"] == 3, "el recuento no suma las tres formas de escribirlo"
        assert pueblos["MACHACON"] == 1
        # Y el rótulo de la opción es **una de las formas escritas de verdad**, no una inventada.
        assert "CALVARRASA DE ARRIBA" in [
            opcion["texto"] for opcion in filtros["municipios"]
        ]

    def test_el_nombre_del_pueblo_no_se_le_cambia_a_la_tierra(self, cliente, cuenta, crear_parcela):
        """**El dato guardado y el que se enseña no se tocan.** El nombre es del agricultor."""
        crear_parcela(alias="Una", municipio="Calvarrasa de Arriba")
        crear_parcela(alias="Otra", municipio="CALVARRASA DE ARRIBA")

        tierras = _la_vista(cliente, cuenta)["tierras"]

        assert sorted(tierra["municipio"] for tierra in tierras) == [
            "CALVARRASA DE ARRIBA",
            "Calvarrasa de Arriba",
        ], "el programa le ha cambiado el nombre al pueblo de sus tierras"

    def test_dos_tierras_con_el_mismo_nombre_se_cuentan(self, cliente, cuenta, crear_parcela):
        """**Medido en su finca** (filtrando por su explotación, que es lo que hay que hacer siempre):
        **64 tierras y solo 59 nombres distintos**, y hay parejas con el mismo nombre.

        (En toda la base hay 65 tierras y 60 nombres, porque tiene una tierra más en otra explotación;
        el recuento de la base **no es** el de su finca, y por eso aquí se dice cuál es cuál.)

        El programa **no renombra nada**, pero dice que el nombre está repetido: es lo que hace que el
        agricultor mire el número de la tierra y la referencia para saber cuál está eligiendo.
        """
        crear_parcela(alias="507/24-1 TRIGO BLANDO (0.46 ha)")
        crear_parcela(alias="507/24-1 TRIGO BLANDO (0.46 ha)")
        crear_parcela(alias="507/24-1 TRIGO BLANDO (0.46 ha)")
        crear_parcela(alias="507/91-3 AVENA (1 ha)")

        tierras = {tierra["alias"]: tierra for tierra in _la_vista(cliente, cuenta)["tierras"]}

        assert tierras["507/24-1 TRIGO BLANDO (0.46 ha)"]["cuantas_con_el_mismo_nombre"] == 3
        assert tierras["507/91-3 AVENA (1 ha)"]["cuantas_con_el_mismo_nombre"] == 1
        # Y el nombre se queda tal cual: no se le añade un número ni un sufijo.
        assert "507/24-1 TRIGO BLANDO (0.46 ha)" in tierras

    def test_las_tierras_que_comparten_recinto_lo_dicen(self, cliente, cuenta, crear_parcela):
        """**Medido en su finca**: **64 tierras y solo 51 referencias distintas**, porque el cuaderno de
        la Junta parte un mismo recinto en varias líneas de cultivo (una la comparten 9 tierras y otra
        6).

        (En toda la base son 65 tierras y 52 referencias: la que falta está en otra explotación. Se
        dice cuál es cuál a propósito, porque un recuento de la base **no es** un recuento de su finca.)

        Dos tierras con la misma referencia **son el mismo trozo de tierra**, así que comparten
        polígono. El servidor lo dice con una clave, para que la pantalla encienda las dos en vez de
        elegir una al azar.
        """
        comun = "37-70-0-0-507-24-1"
        crear_parcela(alias="Línea 1", ref_sigpac=comun)
        crear_parcela(alias="Línea 2", ref_sigpac=comun)
        # Y la misma referencia escrita con espacios de más y en minúsculas es **la misma**.
        crear_parcela(alias="Línea 3", ref_sigpac=" 37-70-0-0-507-24-1 ")
        crear_parcela(alias="Otra tierra", ref_sigpac="37-70-0-0-507-91-3")

        tierras = {tierra["alias"]: tierra for tierra in _la_vista(cliente, cuenta)["tierras"]}
        claves = {tierra["clave_recinto"] for tierra in tierras.values()}

        assert len(claves) == 2, f"las tres líneas del mismo recinto no comparten clave: {claves}"
        assert len({tierras[n]["clave_recinto"] for n in ("Línea 1", "Línea 2", "Línea 3")}) == 1
        assert tierras["Otra tierra"]["clave_recinto"] != tierras["Línea 1"]["clave_recinto"]

    def test_una_tierra_sin_referencia_ni_forma_no_comparte_recinto_con_nadie(
        self, cliente, cuenta, crear_parcela
    ):
        """De una tierra sin referencia y sin forma **no se puede decir** que comparta nada.

        Decir que sí sería inventarse un recinto: es la regla de la casa (lo que no se sabe no se
        afirma) aplicada a la clave que decide qué tierras se encienden juntas.
        """
        crear_parcela(alias="Sin nada 1", ref_sigpac=None)
        crear_parcela(alias="Sin nada 2", ref_sigpac=None)

        tierras = _la_vista(cliente, cuenta)["tierras"]
        claves = {tierra["clave_recinto"] for tierra in tierras}

        assert len(claves) == 2, "dos tierras sin referencia ni forma no pueden compartir recinto"
        assert all(clave.startswith("tierra:") for clave in claves)

    def test_dos_tierras_con_la_misma_forma_y_sin_referencia_son_el_mismo_recinto(
        self, cliente, cuenta, crear_parcela
    ):
        """Sin referencia, la clave es la huella de la forma (la misma idea que en T05)."""
        crear_parcela(alias="Copia 1", ref_sigpac=None, geometria=UN_WKT)
        crear_parcela(alias="Copia 2", ref_sigpac=None, geometria=UN_WKT)
        crear_parcela(alias="Distinta", ref_sigpac=None, geometria=OTRO_WKT)

        tierras = {tierra["alias"]: tierra for tierra in _la_vista(cliente, cuenta)["tierras"]}

        assert tierras["Copia 1"]["clave_recinto"] == tierras["Copia 2"]["clave_recinto"]
        assert tierras["Copia 1"]["clave_recinto"] != tierras["Distinta"]["clave_recinto"]
        assert tierras["Copia 1"]["clave_recinto"].startswith("forma:")


    def test_el_mismo_pueblo_con_tilde_y_sin_tilde_es_una_sola_opcion(
        self, cliente, cuenta, crear_parcela
    ):
        """La revisión de T06 (D3) encontró que el servidor juntaba las formas de escribirlo **solo
        por mayúsculas**, y la pantalla coteja quitando también **tildes y espacios de dentro**
        (`nucleo.sinTildes`). Con dos normalizaciones distintas, el número de la opción y las filas
        que salen al elegirla no cuadran: el agricultor lee «3 tierras» y le salen cuatro.

        Los dos casos están a un paso de sus datos: `MACHACON` es como lo escribe el cuaderno de la
        Junta (sin tilde) y `Machacón` como lo escribe la lista oficial del INE, de donde el
        formulario lo coge al elegirlo.
        """
        crear_parcela(alias="Del cuaderno", municipio="MACHACON")
        crear_parcela(alias="Del cuaderno 2", municipio="MACHACON")
        crear_parcela(alias="De la lista oficial", municipio="Machacón")
        crear_parcela(alias="Con dos espacios", municipio="Calvarrasa  de Arriba")
        crear_parcela(alias="Con uno", municipio="Calvarrasa de Arriba")

        filtros = _la_vista(cliente, cuenta)["filtros"]
        pueblos = {opcion["valor"]: opcion["cuantas"] for opcion in filtros["municipios"]}

        assert len(pueblos) == 2, f"el mismo pueblo sale partido: {pueblos}"
        assert pueblos["MACHACON"] == 3, "la tilde parte el recuento del mismo pueblo"
        assert pueblos["Calvarrasa  de Arriba"] == 2, "los espacios de dentro parten el recuento"

    def test_la_columna_de_las_hectareas_y_el_pie_cuentan_lo_mismo(
        self, cliente, cuenta, campana, crear_parcela
    ):
        """«Hectáreas dichas» es **la superficie de la tierra**, y esa es la regla que usan a la vez la
        fila, el pie y el filtro (revisión de T06, D1).

        Antes el pie contaba también el área declarada de la versión, así que una tierra traída del
        cuaderno de la Junta **sin superficie** pero con hectáreas declaradas salía en la tabla
        diciendo «Sin hectáreas dichas» mientras el pie decía que no había ninguna así. Dos cosas que
        no pueden ser verdad a la vez. Lo que el agricultor declara sigue teniendo su sitio, con su
        nombre, en la ficha de la tierra.
        """
        parcela = crear_parcela(alias="De la Junta, sin superficie", superficie_ha=None, geometria=None)
        lote = {
            "campana_id": campana["id"],
            "fuente": "agricultor",
            "recintos": [
                {
                    "parcela_id": parcela["id"],
                    "poligono": 507,
                    "numero_parcela": 24,
                    "numero_recinto": 1,
                    "area_declarada_ha": 2.5,
                }
            ],
        }
        aplicado = cliente.post("/api/versiones/aplicar", headers=cuenta["cabeceras"], json=lote)
        assert aplicado.status_code == 200, aplicado.text

        vista = _la_vista(cliente, cuenta)
        tierra = _una_tierra(vista["tierras"], "De la Junta, sin superficie")

        assert tierra["superficie_ha"] is None
        assert tierra["area_declarada_ha"] == 2.5, "lo declarado tiene que seguir leyéndose"
        assert tierra["tiene_hectareas_dichas"] is False, "la tierra no tiene dicha su superficie"
        # Y el pie cuenta exactamente esa misma regla: una tierra, la de la fila que lo dice.
        assert vista["totales"]["sin_hectareas"] == 1
        valores = [opcion["valor"] for opcion in vista["filtros"]["pac"]]
        assert "sin_hectareas" in valores, "el filtro no ofrece el estado que enseña una fila"

    def test_la_caja_que_da_la_vista_la_acepta_el_propio_programa(
        self, cliente, cuenta, crear_parcela
    ):
        """**Una finca repartida en más de medio grado** (dos pueblos lejanos, o una coordenada mal
        apuntada) daba una caja que el propio `/api/mapa/imagen` rechazaba con 422, y el agricultor
        leía «puede ser la cobertura» delante de un fallo que no tiene nada que ver con la cobertura
        (revisión de T06, D7).

        Ahora la caja que se da **es siempre una que este programa acepta**, y `se_puede_ensenar_entera`
        dice que no se ve toda la finca. **Y no se pierde dónde están las tierras de fuera**: eso lo
        dice `extension`, que es la envolvente sin recortar.
        """
        from app.routers import mapa as router_del_mapa

        crear_parcela(alias="En Salamanca", geometria=UN_WKT, superficie_ha=2.4)
        # A un grado largo de la primera: es la misma explotación, pero no cabe en una imagen.
        crear_parcela(
            alias="Lejos",
            geometria="POLYGON((-4.5600 40.9000, -4.5500 40.9000, -4.5500 40.9100, -4.5600 40.9100, -4.5600 40.9000))",
            superficie_ha=1.0,
        )

        mapa = _la_vista(cliente, cuenta)["mapa"]
        caja = mapa["caja"]
        lado = max(caja["este"] - caja["oeste"], caja["norte"] - caja["sur"])

        assert mapa["se_puede_ensenar_entera"] is False
        assert lado <= router_del_mapa.LADO_MAXIMO_GRADOS, "la caja que se da la rechaza el programa"
        assert lado >= router_del_mapa.LADO_MINIMO_GRADOS
        # Y la envolvente de verdad sigue estando, con las dos tierras dentro.
        extension = mapa["extension"]
        assert extension["oeste"] <= -5.56 and extension["este"] >= -4.55
        assert extension["sur"] <= 40.9 and extension["norte"] >= 40.91


class TestLoQueDiceElMapaDeSusCapas:

    def test_cada_capa_dice_que_ensena_y_que_se_puede_ocultar(self, cliente):
        datos = cliente.get("/api/mapa/estado").json()

        assert set(datos["capas"]) == {"foto", "linderos", "cultivo"}
        for nombre, capa in datos["capas"].items():
            assert capa["leyenda"].strip(), f"la capa «{nombre}» no dice qué enseña"
            assert capa["se_puede_ocultar"] is True

    def test_la_fecha_de_la_imagen_no_se_sabe_y_lo_dice(self, cliente):
        """**La fecha no se inventa.**

        Los dos WMS que dan las imágenes no publican de qué día son (se comprobó con su
        `GetCapabilities`): no hay ninguna dimensión de tiempo. Poner la fecha de hoy afirmaría que
        la foto es de hoy, y la ortofoto puede ser de hace años. Lo que se hace es decir que no se
        sabe, en la pantalla.
        """
        datos = cliente.get("/api/mapa/estado").json()

        for capa in datos["capas"].values():
            assert capa["fecha"] is None
            assert capa["fecha_texto"] == textos.TIERRA_Y_MAPA["fecha_sin_saber"]

    def test_dice_que_pasa_cuando_una_imagen_no_llega(self, cliente):
        """No se borran los linderos ni se deja una foto vieja sin fecha: se avisa y se sigue."""
        datos = cliente.get("/api/mapa/estado").json()

        assert datos["si_no_llega_una_imagen"] == textos.TIERRA_Y_MAPA["imagen_no_llega"]
        assert "linderos" in datos["si_no_llega_una_imagen"]
        assert "lista" in datos["si_no_llega_una_imagen"]

    def test_la_capa_de_avisos_no_se_promete(self, cliente):
        """El contrato nombra una capa de «avisos» que **ningún servicio publica**.

        Se dice en la pantalla en vez de ofrecer un botón que no enseñaría nada. Esta prueba es la
        que impide que alguien la «arregle» añadiendo una capa vacía.
        """
        datos = cliente.get("/api/mapa/estado").json()

        assert "avisos" not in datos["capas"]
        assert datos["capa_avisos_no_esta"] == textos.TIERRA_Y_MAPA["capa_avisos_no_esta"]
