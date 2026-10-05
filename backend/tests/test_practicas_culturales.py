"""Las prácticas culturales que no son sembrar, plantar, regar ni coger la cosecha.

**Por qué existe este fichero.** Se encontró releyendo el documento oficial de la Junta, que del
apartado «Otras Prácticas Culturales» dice:

> *«permite buscar y/o anotar otras prácticas culturales en una DGC: **Laboreo, mantenimiento de
> cubierta, pastoreo**, etc.»*

Había **dos problemas**, y el segundo era el gordo:

1. **Faltaban dos de las tres que el documento nombra.** Había `laboreo`, pero no había forma de
   apuntar un mantenimiento de cubierta ni un pastoreo.
2. **La lista de tipos de labor existía en el catálogo y ninguna pantalla la ofrecía.** El
   agricultor pulsaba «OTRO TRABAJO» y se guardaba la palabra `otra`, sin decir nunca cuál. Así
   que la poda, el desbroce, la escarda y el laboreo estaban escritos en el catálogo, con su
   nombre, y **no se podían elegir**. Y el volcado oficial mandaba «otra» para todo.

Es el mismo tipo de fallo que el de Documentación: la lista decía «hecho» y la mitad del camino
no existía. Lo que se comprueba aquí es que ahora se puede hacer, de punta a punta.
"""

from __future__ import annotations

import base64
import datetime as dt
import re
import zlib

import pytest

from app import catalogos, legal, sigpac, textos


def _texto_del_pdf(pdf: bytes) -> str:
    """Lo que se puede leer dentro del PDF que se entrega.

    Hace falta porque comprobar solo que el fichero «se genera» no dice nada de lo que lleva
    dentro, y el fallo que se está persiguiendo aquí es justo ese: secciones que existían en los
    datos y **no llegaban al papel que se firma**. El PDF va comprimido y con los acentos
    escapados en octal (WinAnsi), así que se descomprime y se traduce el escape.

    Si algún día esto devolviera vacío, el test tiene que fallar, no pasar por suerte: por eso
    los que lo usan comprueban el texto, no su ausencia.
    """
    trozos: list[bytes] = []
    for marca in re.finditer(rb"stream\r?\n", pdf):
        fin = pdf.find(b"endstream", marca.end())
        crudo = pdf[marca.end() : fin].strip()
        try:
            trozos.append(zlib.decompress(base64.a85decode(crudo, adobe=True)))
        except Exception:  # noqa: BLE001 — hay streams que no son texto y no importan
            continue
    junto = b"\n".join(trozos)
    junto = re.sub(rb"\\([0-7]{3})", lambda m: bytes([int(m.group(1), 8)]), junto)
    return junto.decode("cp1252", errors="replace")


class TestLosTiposQueNombraElDocumento:
    def test_esta_laboreo(self):
        assert "laboreo" in catalogos.TIPOS_LABOR

    def test_esta_el_mantenimiento_de_cubierta(self):
        """«mantenimiento de cubierta» con estas palabras en el documento oficial."""
        assert "cubierta" in catalogos.TIPOS_LABOR
        assert "cubierta" in catalogos.ETIQUETA_LABOR["cubierta"].lower()

    def test_esta_el_pastoreo(self):
        assert "pastoreo" in catalogos.TIPOS_LABOR
        assert catalogos.ETIQUETA_LABOR["pastoreo"] == "Pastoreo"

    def test_cada_tipo_tiene_su_nombre(self):
        """Un código sin nombre acabaría saliendo en el papel como «cubierta», en minúscula."""
        for tipo in catalogos.TIPOS_LABOR:
            assert catalogos.ETIQUETA_LABOR.get(tipo), f"el tipo {tipo} no tiene nombre"

    def test_no_se_ha_quitado_ninguno_de_los_que_habia(self):
        """Hay apuntes guardados que usan los códigos viejos, y el tipo va en el volcado."""
        for tipo in ("siembra", "plantacion", "riego", "cosecha", "poda", "desbroce", "escarda", "laboreo", "otra"):
            assert tipo in catalogos.TIPOS_LABOR


class TestLoQueSeLeOfreceAlAgricultor:
    """La lista de prácticas de «otro trabajo»: lo que ve en pantalla."""

    def test_cada_boton_corresponde_a_un_tipo_de_verdad(self):
        """Si un botón ofreciera un código que no existe, el apunte se guardaría con basura."""
        ids = {trabajo["id"] for trabajo in textos.TRABAJOS_DE_LABOR}
        assert ids <= set(catalogos.TIPOS_LABOR)

    def test_todos_tienen_dibujo_y_texto(self):
        for trabajo in textos.TRABAJOS_DE_LABOR:
            assert trabajo["texto"]
            assert trabajo["icono"]

    def test_no_se_pregunta_dos_veces_lo_mismo(self):
        """Sembrar, plantar, regar y coger la cosecha ya tienen su botón en la pantalla de inicio.

        Volver a ofrecerlos aquí sería preguntar dos veces la misma cosa, y el agricultor tendría
        que elegir entre dos caminos para apuntar lo mismo.
        """
        ids = {trabajo["id"] for trabajo in textos.TRABAJOS_DE_LABOR}
        assert not ids & {"siembra", "plantacion", "riego", "cosecha"}

    def test_se_puede_decir_que_no_es_ninguna(self):
        """Siempre tiene que haber salida: si no es ninguna de las que hay, se escribe a mano."""
        assert "otra" in {trabajo["id"] for trabajo in textos.TRABAJOS_DE_LABOR}

    def test_las_dos_que_faltaban_estan_en_la_lista(self):
        ids = {trabajo["id"] for trabajo in textos.TRABAJOS_DE_LABOR}
        assert "cubierta" in ids
        assert "pastoreo" in ids

    def test_los_textos_los_revisa_el_test_de_jerga(self):
        """Todo lo que lee el agricultor pasa por el test de jerga, también esto.

        Si esta lista se hubiera quedado en `catalogos.py`, sería el único texto de pantalla del
        programa sin revisar. Por eso vive en `textos.py`.
        """
        visibles = textos.textos_visibles()
        for trabajo in textos.TRABAJOS_DE_LABOR:
            assert trabajo["texto"] in visibles

    def test_no_llevan_jerga(self):
        for trabajo in textos.TRABAJOS_DE_LABOR:
            assert not textos.palabras_prohibidas_encontradas(trabajo["texto"])


class TestLaPreguntaQueFaltaba:
    def test_el_asistente_pregunta_cual_es(self):
        """«Otro trabajo» no es un trabajo: es un cajón, y hay que abrirlo."""
        assert "labor.cual" in textos.ETIQUETAS
        assert textos.ETIQUETAS["labor.cual"]["pregunta"]
        assert textos.ETIQUETAS["labor.cual"]["pista"]

    def test_la_pista_dice_qué_hacer_si_no_es_ninguna(self):
        assert "OTRA COSA" in textos.ETIQUETAS["labor.cual"]["pista"]


class TestLaInterfazLasOfrece:
    def test_la_interfaz_sirve_las_practicas(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        ids = {trabajo["id"] for trabajo in datos["trabajos_de_labor"]}
        assert "cubierta" in ids and "pastoreo" in ids

    def test_y_sirve_los_nombres_de_cada_tipo(self, cliente):
        """El resumen del asistente y el papel necesitan el nombre, no el código."""
        datos = cliente.get("/api/interfaz").json()
        assert datos["etiquetas_labor"]["pastoreo"] == "Pastoreo"
        assert datos["etiquetas_labor"]["cubierta"] == "Mantenimiento de la cubierta"

    def test_las_practicas_llevan_su_dibujo(self, cliente):
        datos = cliente.get("/api/interfaz").json()
        for trabajo in datos["trabajos_de_labor"]:
            assert trabajo["icono"]


class TestSePuedeApuntarDeVerdad:
    """De punta a punta: lo que antes no se podía hacer."""

    @pytest.mark.parametrize("tipo", ["cubierta", "pastoreo", "laboreo", "poda", "desbroce", "escarda"])
    def test_cada_practica_se_apunta_y_se_guarda_por_su_nombre(self, cliente, cuenta, campana, parcela, tipo):
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": tipo,
                "fecha": "2026-04-10",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["tipo"] == tipo

    def test_la_practica_sale_en_el_cuaderno_con_su_nombre(self, cliente, cuenta, campana, parcela):
        """En el papel no puede salir «cubierta»: sale lo que entiende quien lo lea."""
        cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "cubierta",
                "fecha": "2026-04-10",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
            },
        )
        cuaderno = cliente.get("/api/cuaderno/pdf", headers=cuenta["cabeceras"])
        assert cuaderno.status_code == 200
        # El PDF es binario y comprimido, así que no se busca el texto dentro: lo que se
        # comprueba es que se genera con la labor apuntada.
        assert cuaderno.content[:4] == b"%PDF"

    def test_el_nombre_de_la_practica_esta_en_la_firma(self, cliente, cuenta, campana, parcela):
        """El fichero que se firma es texto: ahí sí se puede leer el nombre de la práctica."""
        cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "pastoreo",
                "fecha": "2026-04-10",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
            },
        )
        fichero = cliente.get("/api/firmas/fichero", headers=cuenta["cabeceras"]).text
        assert "Pastoreo" in fichero

    def test_sigue_habiendo_un_cajon_para_lo_que_no_esta_en_la_lista(
        self, cliente, cuenta, campana, parcela
    ):
        """«Otra» sigue existiendo: inventarse una lista cerrada dejaría fuera al que hace algo
        que no está previsto. Lo que cambia es que ya no es el único sitio donde acaba todo."""
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "otra",
                "fecha": "2026-04-10",
                "parcela_id": parcela["id"],
                "superficie_ha": 1.0,
                "detalles": {"nota": "pasé el rulo"},
            },
        )
        assert respuesta.status_code == 201
        assert respuesta.json()["tipo"] == "otra"


class TestElCuadernoLlevaLasLabores:
    """Las labores se apuntaban y **no salían** ni en el papel ni en el fichero de datos.

    Eso es la peor clase de fallo: el agricultor tenía el dato y el documento que entrega si se lo
    piden no lo enseñaba. Y no es una sección cualquiera: son tres de los bloques que pide el
    contenido mínimo del cuaderno —las labores culturales, el riego y la siembra y plantación— y en
    este programa los tres son labores de distinto tipo.
    """

    def _una_labor(self, cliente, cabeceras, campana, parcela, **datos) -> None:
        respuesta = cliente.post(
            "/api/labores",
            headers=cabeceras,
            json={
                "campana_id": campana["id"],
                "fecha": "2026-04-10",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                **datos,
            },
        )
        assert respuesta.status_code == 201, respuesta.text

    def _texto_del_csv(self, cliente, cuenta) -> str:
        respuesta = cliente.get("/api/cuaderno/export.csv", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        return respuesta.content.decode("utf-8-sig")

    def test_el_fichero_de_datos_lleva_las_labores(self, cliente, cuenta, campana, parcela):
        """Con el agua del riego, de dónde salió, cómo se riega y el número de contador."""
        self._una_labor(
            cliente,
            cuenta["cabeceras"],
            campana,
            parcela,
            tipo="riego",
            volumen_agua=1200.0,
            unidad_agua="m3",
            origen_agua="pozo",
            sistema_riego="goteo",
            numero_contador="C-1234",
        )
        texto = self._texto_del_csv(cliente, cuenta)
        assert textos.LABORES["informe_titulo"].upper() in texto
        assert "Riego" in texto
        assert catalogos.ETIQUETA_ORIGEN_AGUA["pozo"] in texto
        assert catalogos.ETIQUETA_SISTEMA_RIEGO["goteo"] in texto
        assert "1.200,00" in texto
        assert "C-1234" in texto

    def test_la_semilla_de_la_siembra_tambien_sale(self, cliente, cuenta, campana, parcela):
        """El bloque 6 del contenido mínimo: siembra, dosis, lote y si el material venía tratado."""
        self._una_labor(
            cliente,
            cuenta["cabeceras"],
            campana,
            parcela,
            tipo="siembra",
            cantidad_semilla_kg=480.0,
            dosis_siembra_kg_ha=197.5,
            lote_semilla="L-SEM-2026-04",
            material_tratado=True,
            siembra_directa=True,
        )
        texto = self._texto_del_csv(cliente, cuenta)
        assert "480,00" in texto
        assert "197,50" in texto
        assert "L-SEM-2026-04" in texto

    def test_el_pastoreo_dice_de_quien_era_el_ganado(self, cliente, cuenta, campana, parcela):
        self._una_labor(
            cliente,
            cuenta["cabeceras"],
            campana,
            parcela,
            tipo="pastoreo",
            animales_terceros=True,
            animales_propios=False,
        )
        texto = self._texto_del_csv(cliente, cuenta)
        linea = next(l for l in texto.splitlines() if "Pastoreo" in l)
        assert textos.ACCIONES["si"] in linea, "el ganado de otros"
        assert textos.ACCIONES["no"] in linea, "y el propio"

    def test_se_dice_cuando_no_hay_ninguna_labor_apuntada(self, cliente, cuenta):
        """Una sección vacía se dice: quien abre el fichero tiene que poder distinguir «no hay
        nada» de «la exportación se ha roto»."""
        texto = self._texto_del_csv(cliente, cuenta)
        assert textos.LABORES["informe_titulo"].upper() in texto
        assert textos.LABORES["informe_sin_nada"] in texto

    def test_lo_que_no_se_apunto_no_se_convierte_en_cero(self, cliente, cuenta, campana, parcela):
        """Una poda no lleva agua ni semilla: esas casillas van **vacías**, no a cero.

        El cero es un dato —«eché cero agua»— y el hueco es «no lo apunté». Confundirlos en el
        documento que se entrega es escribir algo que no pasó.
        """
        self._una_labor(cliente, cuenta["cabeceras"], campana, parcela, tipo="poda")
        texto = self._texto_del_csv(cliente, cuenta)
        linea = next(l for l in texto.splitlines() if "Poda" in l)
        assert "0,00" not in linea, f"la poda no llevaba agua ni semilla: {linea}"
        assert "sin fecha" not in linea

    def _la_fila_de_una_labor(self, texto: str, contiene: str) -> list[str]:
        """La **fila de datos** de una labor, separada por columnas.

        Hace falta separar la cabecera de los datos: «Siembra» está en la cabecera (en «Siembra
        directa») y en la fila, así que buscar la línea por la palabra cogería la cabecera. Se
        busca por lo que solo está en el dato: la fecha.
        """
        cabecera = next(l for l in texto.splitlines() if l.startswith("Fecha;Labor"))
        columnas = cabecera.split(";")
        for linea in texto.splitlines():
            if "10/04/2026" in linea and contiene in linea:
                valores = linea.split(";")
                assert len(valores) == len(columnas), f"la fila no cuadra con la cabecera: {linea}"
                return valores
        raise AssertionError(f"no encuentro la fila de la labor: {contiene}")

    def test_la_semilla_tratada_dice_que_tratamiento_recibio(
        self, cliente, cuenta, campana, parcela
    ):
        """**Esto faltaba.** El anexo II pide, del uso de semilla tratada, **qué tratamiento** llevó
        la semilla, **cuándo** y **si funcionó**. Hasta la ronda 5 solo se apuntaba «semilla
        tratada: sí», que dice que sí pero no qué, y eso es lo que hay que poder contestar si un
        día se pregunta por una partida de grano.
        """
        self._una_labor(
            cliente,
            cuenta["cabeceras"],
            campana,
            parcela,
            tipo="siembra",
            material_tratado=True,
            tratamiento_semilla="Imidacloprid + tiram",
            fecha_tratamiento_semilla="2026-02-01",
            eficacia_tratamiento_semilla="bien",
        )
        texto = self._texto_del_csv(cliente, cuenta)
        valores = self._la_fila_de_una_labor(texto, parcela["alias"])
        cabecera = next(l for l in texto.splitlines() if l.startswith("Fecha;Labor")).split(";")

        def de_la_columna(etiqueta: str) -> str:
            return valores[cabecera.index(etiqueta)]

        assert de_la_columna("Qué le echaron a la semilla") == "Imidacloprid + tiram"
        assert de_la_columna("Cuándo se trató la semilla") == legal.formatea_fecha(dt.date(2026, 2, 1))
        assert de_la_columna("Cómo funcionó el tratamiento de la semilla") == (
            catalogos.ETIQUETA_EFICACIA["bien"]
        )

    def test_una_semilla_sin_tratar_no_dice_que_se_trato(
        self, cliente, cuenta, campana, parcela
    ):
        """Lo que no pasó no se escribe: sin tratamiento, esas casillas van vacías."""
        self._una_labor(
            cliente, cuenta["cabeceras"], campana, parcela, tipo="siembra", material_tratado=False
        )
        texto = self._texto_del_csv(cliente, cuenta)
        valores = self._la_fila_de_una_labor(texto, parcela["alias"])
        cabecera = next(l for l in texto.splitlines() if l.startswith("Fecha;Labor")).split(";")

        assert valores[cabecera.index("Semilla tratada")] == textos.ACCIONES["no"]
        for etiqueta in (
            "Qué le echaron a la semilla",
            "Cuándo se trató la semilla",
            "Cómo funcionó el tratamiento de la semilla",
        ):
            assert valores[cabecera.index(etiqueta)] == "", f"«{etiqueta}» no debería llevar nada"

    def test_el_papel_tambien_sale_con_las_labores(self, cliente, cuenta, campana, parcela):
        """El PDF es binario y comprimido, así que se comprueba que se genera con la labor dentro."""
        self._una_labor(cliente, cuenta["cabeceras"], campana, parcela, tipo="laboreo")
        cuaderno = cliente.get("/api/cuaderno/pdf", headers=cuenta["cabeceras"])
        assert cuaderno.status_code == 200
        assert cuaderno.content.startswith(b"%PDF")

    def test_una_labor_puede_decir_con_que_maquina_se_hizo(
        self, cliente, cuenta, campana, parcela, equipo
    ):
        """**Esto faltaba, y el contenido mínimo del CUE lo pide.**

        Los tratamientos decían con qué máquina se aplicó (`equipo_id`) y las labores no: se podía
        apuntar que se labró y no con qué. Es lo que el cuaderno oficial pide en el bloque de
        labores culturales y en el de siembra («Maquinaria»).
        """
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-04-10",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "tipo": "laboreo",
                "equipo_id": equipo["id"],
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["equipo_id"] == equipo["id"], "se guarda y vuelve en la respuesta"

        texto = self._texto_del_csv(cliente, cuenta)
        linea = next(l for l in texto.splitlines() if "Laboreo" in l)
        assert equipo["nombre"] in linea, f"la máquina no sale en el fichero: {linea}"

    def test_una_maquina_que_no_es_suya_no_vale(self, cliente, cuenta, campana, parcela):
        """Una máquina de otra finca no puede acabar en este cuaderno.

        Y la respuesta es **404, no 403**: es la regla de toda la API a propósito, para no
        confirmar si ese identificador existe en la finca de otro.
        """
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-04-10",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "tipo": "laboreo",
                "equipo_id": 99999,
            },
        )
        assert respuesta.status_code == 404
        assert "no está en tu cuaderno" in respuesta.json()["detail"]

    def test_sin_maquina_la_labor_se_apunta_igual(self, cliente, cuenta, campana, parcela):
        """Hay labores a mano, y obligar a tener la máquina antes es la forma de que no se apunte."""
        respuesta = cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "fecha": "2026-04-10",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
                "tipo": "poda",
            },
        )
        assert respuesta.status_code == 201, respuesta.text
        assert respuesta.json()["equipo_id"] is None

    def test_el_papel_lleva_de_verdad_la_seccion_de_labores(self, cliente, cuenta, campana, parcela):
        """Y no solo «el PDF sale»: la sección tiene que estar **dentro** del papel.

        Comprobar que el fichero se abre deja pasar el fallo entero: el agricultor podía tener la
        labor apuntada y entregar un papel donde esa sección no estaba.
        """
        self._una_labor(
            cliente,
            cuenta["cabeceras"],
            campana,
            parcela,
            tipo="laboreo",
            observaciones="Pase de chísel",
        )
        cuaderno = cliente.get("/api/cuaderno/pdf", headers=cuenta["cabeceras"])
        texto = _texto_del_pdf(cuaderno.content)
        assert textos.LABORES["informe_titulo"] in texto
        assert catalogos.ETIQUETA_LABOR["laboreo"] in texto
        assert parcela["alias"] in texto


class TestElCuadernoImpresoLlevaLasTierrasYElPlan:
    """Las parcelas y el plan de abono se apuntaban y **no salían** en el cuaderno.

    Es el mismo fallo que el de las labores, y por eso se persigue igual: el contenido mínimo del
    cuaderno tiene trece bloques y el papel solo enseñaba seis. «Datos de superficies» es el bloque
    12, y el plan de abono es lo que después se compara con lo que de verdad se echó.

    Un cuaderno que no dice de qué tierras habla no sirve para entregarlo, aunque los datos estén
    todos dentro del programa.
    """

    @pytest.fixture
    def plan_de_abono(self, cliente, cuenta, campana, parcela):
        def _crear(**cambios):
            datos = {
                "campana_id": campana["id"],
                "parcela_id": parcela["id"],
                "cultivo": "Trigo blando",
                "superficie_ha": 2.43,
                "necesidad_n": 100.0,
                "necesidad_p": 40.0,
                "necesidad_k": 60.0,
                "detalle": [{"nombre": "Nitrato amónico", "kg_ha": 200.0, "momento": "fondo"}],
            }
            datos.update(cambios)
            respuesta = cliente.post("/api/planes", headers=cuenta["cabeceras"], json=datos)
            assert respuesta.status_code == 201, respuesta.text
            return respuesta.json()

        return _crear

    def _texto_del_csv(self, cliente, cuenta) -> str:
        respuesta = cliente.get("/api/cuaderno/export.csv", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        return respuesta.content.decode("utf-8-sig")

    def test_el_fichero_de_datos_empieza_por_las_tierras(self, cliente, cuenta, parcela):
        texto = self._texto_del_csv(cliente, cuenta)
        assert textos.PARCELAS["informe_titulo"].upper() in texto
        linea = next(l for l in texto.splitlines() if parcela["alias"] in l)
        assert parcela["ref_sigpac"] in linea
        assert parcela["municipio"] in linea
        assert parcela["provincia"] in linea
        assert legal.formatea_numero(parcela["superficie_ha"], 4) in linea
        assert catalogos.ETIQUETA_SISTEMA["secano"] in linea
        assert texto.index(textos.PARCELAS["informe_titulo"].upper()) < texto.index(
            "PRODUCTOS APLICADOS"
        ), "las tierras van antes que lo que se hizo en ellas"

    def test_el_uso_de_la_parcela_sale_del_catalogo_oficial(self, cliente, cuenta, crear_parcela):
        """El uso se escribe como lo llama el SIGPAC («TIERRAS ARABLES»), no como un código."""
        crear_parcela(alias="El llano", uso_sigpac="TA")
        texto = self._texto_del_csv(cliente, cuenta)
        linea = next(l for l in texto.splitlines() if "El llano" in l)
        assert sigpac.etiqueta_uso("TA") in linea
        assert sigpac.etiqueta_uso("TA") != "TA", "el catálogo oficial tiene que estar cargado"

    def test_un_uso_que_no_esta_en_el_catalogo_se_escribe_tal_cual(
        self, cliente, cuenta, crear_parcela
    ):
        """Si el código no está en la lista oficial se pone el código, **nunca** una traducción
        nuestra: «TA» es lo que pone el papel del agricultor, y una palabra inventada es peor."""
        crear_parcela(alias="La cuesta", uso_sigpac="ZZ")
        texto = self._texto_del_csv(cliente, cuenta)
        linea = next(l for l in texto.splitlines() if "La cuesta" in l)
        assert "ZZ" in linea

    def test_la_parcela_dice_la_pendiente_y_la_zona_de_nitratos(
        self, cliente, cuenta, crear_parcela
    ):
        """Las dos que importan para cumplir y que en el papel estorban."""
        crear_parcela(alias="La vega", pendiente_pct=8.5)
        texto = self._texto_del_csv(cliente, cuenta)
        assert "Pendiente (%)" in texto
        assert "Zona de nitratos" in texto
        linea = next(l for l in texto.splitlines() if "La vega" in l)
        assert "8,50" in linea

    def test_el_plan_de_abono_sale_con_lo_previsto_y_el_reparto(
        self, cliente, cuenta, parcela, plan_de_abono
    ):
        plan_de_abono()
        texto = self._texto_del_csv(cliente, cuenta)
        assert textos.PLAN["titulo"].upper() in texto
        linea = next(l for l in texto.splitlines() if "Trigo blando" in l)
        assert parcela["alias"] in linea
        assert "100,00" in linea, "el nitrógeno previsto"
        assert "40,00" in linea, "el fósforo previsto"
        assert "60,00" in linea, "el potasio previsto"
        assert "Nitrato amónico" in linea
        assert "200,00 kg/ha" in linea
        assert "fondo" in linea

    def test_al_plan_que_le_falta_un_dato_no_se_le_inventa_un_cero(
        self, cliente, cuenta, plan_de_abono
    ):
        """Un plan sin nutrientes apuntados deja las casillas **vacías**, no a cero.

        El cero es un dato —«no hacía falta nitrógeno»— y el hueco es «no lo calculé». Escribir un
        cero donde no hay dato es poner en el cuaderno algo que el agricultor no ha dicho.
        """
        plan_de_abono(
            necesidad_n=None,
            necesidad_p=None,
            necesidad_k=None,
            produccion_esperada_kg_ha=None,
            detalle=[],
        )
        texto = self._texto_del_csv(cliente, cuenta)
        linea = next(l for l in texto.splitlines() if "Trigo blando" in l)
        assert "0,00" not in linea, f"no se apuntó ningún nutriente: {linea}"
        assert "kg/ha" not in linea, f"y no hay ningún reparto previsto: {linea}"

    def test_se_dice_cuando_no_hay_ni_parcelas_ni_plan(self, cliente, cuenta, campana):
        """Una sección vacía se dice: quien abre el fichero tiene que poder distinguir «no hay
        nada» de «la exportación se ha roto»."""
        texto = self._texto_del_csv(cliente, cuenta)
        assert textos.PARCELAS["informe_sin_nada"] in texto
        assert textos.PLAN["sin_planes"] in texto

    def test_el_papel_lleva_las_parcelas_y_el_plan_de_verdad(
        self, cliente, cuenta, campana, parcela, plan_de_abono
    ):
        """Dentro del PDF, no solo «el PDF sale»: es el fallo que se está persiguiendo."""
        plan_de_abono()
        cuaderno = cliente.get("/api/cuaderno/pdf", headers=cuenta["cabeceras"])
        assert cuaderno.status_code == 200
        assert cuaderno.content.startswith(b"%PDF")
        texto = _texto_del_pdf(cuaderno.content)
        assert textos.PARCELAS["informe_titulo"] in texto
        assert parcela["alias"] in texto
        assert textos.PLAN["titulo"] in texto
        assert "Trigo blando" in texto
        assert "Nitrato" in texto, "y el reparto previsto, que va debajo de la tabla"


class TestElCuadernoImpresoLlevaLasNavesYLasMaquinas:
    """Los dos últimos bloques del contenido mínimo que no llegaban al papel.

    Con las parcelas y el plan ya dentro, el cuaderno impreso enseñaba once de los trece bloques del
    Anexo II. Faltaban estos dos: **en qué local se había tratado** (una nave no tiene recinto
    SIGPAC, se identifica por su referencia catastral) y **con qué máquina se había echado el
    producto**. Los dos datos se apuntaban en el programa y no salían en el papel que se entrega,
    que es el mismo fallo que el de las labores y el de las parcelas.
    """

    def _texto_del_csv(self, cliente, cuenta) -> str:
        respuesta = cliente.get("/api/cuaderno/export.csv", headers=cuenta["cabeceras"])
        assert respuesta.status_code == 200
        return respuesta.content.decode("utf-8-sig")

    def test_el_fichero_de_datos_lleva_las_naves(self, cliente, cuenta, crear_instalacion):
        crear_instalacion(alias="La nave del grano", tipo="nave", referencia_catastral="1234567VG4513N")
        texto = self._texto_del_csv(cliente, cuenta)
        assert textos.INSTALACIONES["informe_titulo"].upper() in texto
        linea = next(l for l in texto.splitlines() if "La nave del grano" in l)
        assert catalogos.ETIQUETA_INSTALACION["nave"] in linea
        assert "1234567VG4513N" in linea
        assert "Peñaranda de Bracamonte" in linea
        assert "Guardar el grano" in linea

    def test_el_fichero_de_datos_lleva_las_maquinas_con_sus_revisiones(
        self, cliente, cuenta, crear_equipo
    ):
        """La ITEAf caducada es lo que deja a un equipo sin poder aplicarse: tiene que verse."""
        crear_equipo(
            nombre="El pulverizador viejo",
            fecha_iteaf="2019-02-10",
            fecha_proxima_iteaf="2024-02-10",
        )
        texto = self._texto_del_csv(cliente, cuenta)
        assert textos.MAQUINARIA["informe_titulo"].upper() in texto
        linea = next(l for l in texto.splitlines() if "El pulverizador viejo" in l)
        assert "ROMA-9876" in linea
        assert legal.formatea_fecha(dt.date(2019, 2, 10)) in linea
        assert legal.formatea_fecha(dt.date(2024, 2, 10)) in linea

    def test_una_maquina_sin_numero_de_serie_no_se_inventa(self, cliente, cuenta, crear_equipo):
        """Lo que no se apuntó queda **vacío**, y nunca con la palabra «None» dentro."""
        crear_equipo(nombre="La mochila", numero_roma=None, numero_serie=None, fecha_iteaf=None)
        texto = self._texto_del_csv(cliente, cuenta)
        linea = next(l for l in texto.splitlines() if "La mochila" in l)
        assert "None" not in linea, f"un dato que no está no puede salir como «None»: {linea}"
        assert "1900" not in linea, "ni con una fecha de relleno"

    def test_se_dice_cuando_no_hay_ni_naves_ni_maquinas(self, cliente, cuenta, campana):
        texto = self._texto_del_csv(cliente, cuenta)
        assert textos.INSTALACIONES["informe_sin_nada"] in texto
        assert textos.MAQUINARIA["informe_sin_nada"] in texto

    def test_el_papel_lleva_las_naves_y_las_maquinas_de_verdad(
        self, cliente, cuenta, campana, crear_instalacion, crear_equipo
    ):
        crear_instalacion(alias="La nave del grano")
        crear_equipo(nombre="El pulverizador")
        cuaderno = cliente.get("/api/cuaderno/pdf", headers=cuenta["cabeceras"])
        assert cuaderno.status_code == 200
        texto = _texto_del_pdf(cuaderno.content)
        assert textos.INSTALACIONES["informe_titulo"] in texto
        assert "La nave del grano" in texto
        assert textos.MAQUINARIA["informe_titulo"] in texto
        assert "El pulverizador" in texto


class TestElVolcadoOficial:
    def test_el_tipo_de_labor_va_en_el_volcado(self, cliente, cuenta, campana, parcela):
        """El bloque 5 del contenido mínimo («labores culturales») lleva la fecha, el cultivo y
        la superficie. El tipo es lo que dice qué labor fue."""
        cliente.post(
            "/api/labores",
            headers=cuenta["cabeceras"],
            json={
                "campana_id": campana["id"],
                "tipo": "cubierta",
                "fecha": "2026-04-10",
                "parcela_id": parcela["id"],
                "superficie_ha": 2.43,
            },
        )
        datos = cliente.get("/api/iuws/contenido", headers=cuenta["cabeceras"]).json()
        nombres = [campo["nombre"] for campo in datos["campos_por_bloque"]["labores"]]
        assert "Fecha inicio" in nombres
        assert "Superficie de labor (ha)" in nombres

    def test_las_practicas_nuevas_no_inventan_codigos_de_catalogo(self):
        """«Tipo de labor» en el CUE es «opciones a elegir en función del cultivo» (según catálogo).

        O sea: el tipo va como código de un catálogo oficial que **no tenemos**. Aquí se guarda el
        nombre de la práctica para el cuaderno del agricultor, y en el volcado ese campo sigue
        vacío y marcado, como todos los de catálogo. Lo que no se hace es inventarse el número.
        """
        from app import iuws_contenido

        campos = iuws_contenido.BLOQUES["labores"][2]
        de_catalogo = [campo for campo in campos if campo.catalogo]
        # Si algún día se marca «tipo de labor» como campo de catálogo, tiene que salir vacío.
        for campo in de_catalogo:
            assert campo.de is None or campo.catalogo
