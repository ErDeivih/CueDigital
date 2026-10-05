"""Prueba de humo: el recorrido completo contra el servidor de verdad.

No es un test (para eso está pytest, que no levanta servidor). Esto comprueba lo que
los tests no pueden: que uvicorn arranca, que la API responde por HTTP y que **el PDF
que descarga el agricultor es un PDF de verdad y se puede abrir**.

Se ejecuta con el servidor levantado **y con la base de datos limpia**:

    python scripts/humo.py http://127.0.0.1:8010

El servidor tiene que arrancarse con estas variables, o la prueba falla por el entorno y no
por el programa. **Ojo con el nombre de la última**, que lleva «CONFIAR» y no «CONFIER»:

    CUEDIGITAL_DATABASE_URL=sqlite:///./humo.db   (una base nueva, borrada antes de arrancar)
    CUEDIGITAL_SECRETO=lo-que-sea                  (no es un secreto de verdad)
    CUEDIGITAL_ADJUNTOS=<carpeta temporal>         (para no dejar adjuntos de prueba)
    CUEDIGITAL_CONFIAR_EN_CABECERAS=1              (para el apartado del certificado digital)

Sin `CUEDIGITAL_CONFIAR_EN_CABECERAS=1` el apartado 11 falla entero: el programa no se cree las
cabeceras del certificado, y hace bien, porque por defecto no debe creérselas.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import unicodedata
from decimal import Decimal
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"
# La raíz del proyecto. Hace falta para llegar a los ficheros de firma de ejemplo, que son los
# únicos que permiten comprobar aquí que una firma **de verdad** que no es de este cuaderno se
# rechaza. Sin ellos solo se podría probar con basura, y la basura no demuestra nada.
RAIZ = Path(__file__).resolve().parents[2]

# Una fecha propia para el apartado del cultivo de la parcela. Sirve para encontrar **esa** fila
# del volcado por su fecha, en vez de dar por bueno el último tratamiento del cuaderno.
FECHA_DEL_CULTIVO = "2026-05-20"

FALLOS: list[str] = []


def comprobar(condicion: bool, descripcion: str) -> None:
    marca = "OK  " if condicion else "FALLO"
    print(f"  [{marca}] {descripcion}")
    if not condicion:
        FALLOS.append(descripcion)


def _para_comparar(texto: str) -> str:
    """Un texto listo para cotejar dos formas de escribirlo: sin tildes, en minúsculas y sin espacios de más.

    **Se escribe aquí a propósito, y no se importa del programa.** Lo que hay que comprobar es que el
    número que enseña un filtro salga de contar las filas; si se usara la misma función que usa el
    servidor, la comprobación estaría de acuerdo consigo misma y no comprobaría nada. Es la misma lección
    de la revisión de T06: su prueba del vínculo fila↔polígono reimplementó la función del JavaScript en
    vez de llamarla.

    Hace falta porque los nombres los escribe una persona: el cuaderno de la Junta escribe `MACHACON` y
    la lista oficial del INE dice `Machacón`, y hay tierras con dos espacios de dentro del nombre.
    """
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(letra for letra in sin_tildes if not unicodedata.combining(letra))
    return " ".join(sin_tildes.lower().split())


def _euros(valor: object) -> str:
    """Un importe que viene del servidor, escrito siempre igual, para poder compararlo.

    **No se sabe de antemano si el dinero llega como texto o como número**: el programa lo guarda como
    texto decimal canónico (`«121.00»`) y lo devuelve así, pero un cambio de esquema podría mandarlo como
    número. Aquí se aceptan los dos y se devuelve siempre con dos decimales.

    Si no se puede leer, se devuelve `«?»`, que **no coincide con ningún importe esperado**: así una
    comprobación no puede pasar por accidente cuando el servidor manda algo que no es un importe.
    """
    if valor is None:
        return "?"
    try:
        return f"{Decimal(str(valor)):.2f}"
    except Exception:  # noqa: BLE001 — lo que no sea un importe se dice con «?»
        return "?"


def _abrir_el_cuaderno(contenido: bytes):
    """Abre el cuaderno que se acaba de descargar, para comprobar que **es un Excel de verdad**.

    Sin esto, un fichero corrupto pasaría la prueba por el simple hecho de llegar con el tipo
    correcto: lo que hay que comprobar es que se puede abrir y que dentro está lo que tiene que
    estar.
    """
    import io

    from openpyxl import load_workbook

    return load_workbook(io.BytesIO(contenido))


def _factura_de_ejemplo() -> bytes:
    """Fabrica una factura de proveedor, con datos inventados, para poder leerla de verdad.

    Se hace con `reportlab` (que ya es una dependencia del proyecto) y no se guarda en el
    repositorio: una factura de verdad lleva el NIF y los precios de una persona, y esto es un
    ejemplo con una cooperativa que no existe.
    """
    import io

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    lineas = [
        "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
        "C/ Mayor 12 - 37300 Peñaranda de Bracamonte (Salamanca)",
        "N.I.F.: F37012345",
        "",
        "FACTURA Nº 2026/00123",
        "Fecha: 15/03/2026",
        "",
        "Cliente: DAVID PEREZ VELASCO",
        "N.I.F.: 70922320A",
        "",
        "Codigo   Descripcion                          Cant.  Ud    Precio     Importe",
        "00123    GLIFOSATO 36% SL 20 L                  2    UD     85,00      170,00",
        "00456    NITRATO AMONICO 33,5%               1000    KG      0,45      450,00",
        "",
        "                                              Base imponible:           620,00",
        "                                              IVA 21%:                  130,20",
        "                                              TOTAL FACTURA:            750,20",
    ]
    buffer = io.BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=A4)
    alto = 800
    for linea in lineas:
        lienzo.drawString(50, alto, linea)
        alto -= 16
    lienzo.save()
    return buffer.getvalue()


def main() -> int:
    print(f"Prueba de humo contra {BASE}\n")
    cliente = httpx.Client(base_url=BASE, timeout=30.0)

    print("1. El servidor está en pie")
    salud = cliente.get("/health")
    comprobar(salud.status_code == 200, "GET /health responde 200")
    comprobar(salud.json()["estado"] == "ok", "el estado es ok")
    comprobar(
        salud.json()["zonas_vulnerables_cargadas"] is True,
        "carga el listado municipal oficial de zonas vulnerables",
    )

    print("\n1b. La pantalla del agricultor")
    portada = cliente.get("/")
    comprobar(portada.status_code == 200, "la portada se sirve")
    comprobar(
        "text/html" in portada.headers.get("content-type", ""),
        "la portada es HTML",
    )
    # El tipo de fichero importa de verdad: un .js servido como text/plain hace que
    # el navegador rechace el módulo y la pantalla se quede en blanco sin decir nada.
    for fichero, tipo in (
        ("app.js", "javascript"),
        ("nucleo.js", "javascript"),
        ("estilos.css", "text/css"),
        ("manifest.webmanifest", "manifest+json"),
    ):
        respuesta = cliente.get(f"/{fichero}")
        comprobar(
            respuesta.status_code == 200 and tipo in respuesta.headers.get("content-type", ""),
            f"{fichero} se sirve como {tipo}",
        )

    interfaz = cliente.get("/api/interfaz")
    comprobar(interfaz.status_code == 200, "el vocabulario de la pantalla se sirve")
    vocabulario = interfaz.json()
    botones = [boton["texto"] for boton in vocabulario["pantalla_inicio"]["botones"]]
    comprobar(len(botones) == 6, f"la pantalla de inicio tiene seis botones: {', '.join(botones)}")
    comprobar("NO SÉ QUÉ PULSAR" in botones, "está el botón de quien no sabe qué pulsar")
    comprobar(
        vocabulario["pantalla_inicio"]["repetir"]["texto"] == "LO MISMO QUE LA ÚLTIMA VEZ",
        "está el botón de repetir lo de la última vez",
    )

    print("\n2. Alta de la cuenta")
    alta = cliente.post(
        "/api/cuenta/registro",
        json={
            "explotacion": {
                "nombre": "David Pérez Velasco",
                "nif": "70922320A",
                "provincia": "Salamanca",
                "municipio": "Peñaranda de Bracamonte",
            },
            "nombre": "David",
            "correo": "humo@ejemplo.test",
            "clave": "una-clave-larga-de-verdad",
        },
    )
    if alta.status_code == 409:
        alta = cliente.post(
            "/api/cuenta/entrar",
            json={"correo": "humo@ejemplo.test", "clave": "una-clave-larga-de-verdad"},
        )
    comprobar(alta.status_code in (200, 201), "la cuenta se crea y devuelve token")
    cabeceras = {"Authorization": f"Bearer {alta.json()['token']}"}

    campana = cliente.get("/api/campanas/actual", headers=cabeceras).json()
    comprobar(campana["anio"] >= 2026, f"la campaña del año se crea sola ({campana['anio']})")

    print("\n3. La parcela y el producto")
    parcela = cliente.post(
        "/api/parcelas",
        headers=cabeceras,
        json={
            "alias": "El Prado",
            "ref_sigpac": "37-455-12-3",
            "superficie_ha": 2.43,
            "superficie_oficial": True,
            "sistema": "secano",
            # El municipio **y** la provincia: el listado oficial se coteja por los dos, porque hay
            # municipios que se llaman igual en provincias distintas. Con el municipio solo, la
            # aplicación dice «no lo sé» —que es lo correcto— y esta comprobación no tendría
            # sentido. Se quedó sin actualizar al corregir esa regla: pedía la zona con el
            # municipio solo y salía en rojo.
            "municipio": "Peñaranda de Bracamonte",
            "provincia": "Salamanca",
        },
    )
    comprobar(parcela.status_code == 201, "se crea la parcela")
    comprobar(
        parcela.json()["zona_vulnerable_nitratos"] is True,
        "la zona de nitratos se reconoce por municipio y provincia oficiales",
    )
    # Y con el municipio solo tiene que decir «no lo sé», no «no»: es un municipio que existe en
    # más de una provincia, así que sin la provincia no se puede afirmar nada. Es la misma regla
    # que la hace fiable, comprobada también contra el servidor de verdad.
    sin_provincia = cliente.post(
        "/api/parcelas",
        headers=cabeceras,
        json={
            "alias": "El Prado sin provincia",
            "superficie_ha": 1.0,
            "sistema": "secano",
            "municipio": "Peñaranda de Bracamonte",
        },
    )
    comprobar(
        sin_provincia.json()["zona_vulnerable_nitratos"] is None,
        "y con el municipio solo dice «no lo sé», no «no»",
    )

    producto = cliente.post(
        "/api/productos",
        headers=cabeceras,
        json={
            "nombre_comercial": "Ejemplo 25 EC",
            "numero_registro": "24.123",
            "materia_activa": "Tebuconazol",
            "dosis_maxima": 0.8,
            "plazo_seguridad_dias": 21,
        },
    )
    comprobar(producto.status_code == 201, "se da de alta el producto comprado")

    print("\n3b. El dictado: una frase dicha en voz alta")
    dictado = cliente.post(
        "/api/borradores/desde-texto",
        headers=cabeceras,
        json={
            "texto": (
                "hoy he echado ejemplo 25 ec en el prado, dos litros por hectarea, "
                "habia pulgon"
            )
        },
    )
    comprobar(dictado.status_code == 200, "el dictado responde")
    borrador = dictado.json()
    comprobar(borrador["tipo"] == "tratamiento", "ha entendido que es un producto")
    comprobar(
        borrador["datos"].get("parcela_id") == parcela.json()["id"],
        "ha reconocido la parcela por su nombre",
    )
    comprobar(
        borrador["datos"].get("producto_id") == producto.json()["id"],
        "ha reconocido el producto aunque no dijera la formulación",
    )
    comprobar(borrador["datos"].get("dosis") == 2, "ha entendido la dosis")
    comprobar(borrador["falta"] == [], "no le falta nada")
    comprobar(borrador["fuente"] == "reglas", "lo ha entendido sin ningún modelo")
    print("     Lo que vería el agricultor:")
    print(f"       {borrador['titulo']}: {borrador['intro']}")
    for entrada in borrador["entendido"]:
        print(f"       · {entrada['pregunta']} {entrada['valor']}")

    incomprensible = cliente.post(
        "/api/borradores/desde-texto", headers=cabeceras, json={"texto": "bla bla bla"}
    )
    comprobar(
        incomprensible.json()["datos"] == {}, "una frase incomprensible no inventa datos"
    )
    comprobar(
        incomprensible.json()["nada_entendido"] is not None, "y lo dice claramente"
    )
    comprobar(
        cliente.get("/api/tratamientos", headers=cabeceras).json() == [],
        "el dictado NO ha guardado nada: solo propone",
    )

    print("\n3c. Dar de alta lo que se usa (las pantallas de 'mis cosas')")
    vocabulario = cliente.get("/api/interfaz").json()
    comprobar(
        all(f"seccion_{t}" in vocabulario["maestros"] for t in ("parcela", "producto", "abono", "aplicador", "equipo")),
        "el vocabulario trae las cinco secciones",
    )
    comprobar(
        all(f"anadir_{t}" in vocabulario["maestros"] for t in ("parcela", "producto", "abono", "aplicador", "equipo")),
        "cada sección trae su botón de añadir",
    )
    comprobar(
        "antes_de_empezar" in vocabulario["maestros"]
        and "anadir_primera_parcela" in vocabulario["maestros"],
        "está el aviso que desbloquea al agricultor nuevo",
    )
    comprobar(
        "parcela.alias" in vocabulario["etiquetas"],
        "las preguntas de las pantallas de alta llegan a la interfaz",
    )
    comprobar(vocabulario["dictado"].get("titulo") is not None, "el dictado trae su texto")

    # Los cinco endpoints que llaman los asistentes de alta de la interfaz.
    altas = [
        ("/api/fertilizantes", {"nombre": "Urea 46%", "riqueza_n": 46.0}),
        ("/api/aplicadores", {"nombre": "David Pérez", "numero_carne": "C-123456"}),
        ("/api/equipos", {"nombre": "Pulverizador grande", "fecha_proxima_iteaf": "2029-03-01"}),
    ]
    for ruta, cuerpo in altas:
        respuesta = cliente.post(ruta, headers=cabeceras, json=cuerpo)
        comprobar(respuesta.status_code == 201, f"se puede dar de alta en {ruta}")

    print("\n4. Se intenta apuntar un tratamiento mal hecho")
    malo = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-01",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 9.0,
            "justificacion": None,
            "producto_id": producto.json()["id"],
            "dosis": 1.5,
        },
    )
    comprobar(malo.status_code == 422, "se rechaza (422)")
    codigos = [a["codigo"] for a in malo.json()["detail"]["avisos"]]
    comprobar("V3_dosis_excedida" in codigos, "detecta que se pasa de la dosis de la etiqueta")
    comprobar("V4_superficie_excedida" in codigos, "detecta que trata más hectáreas que la parcela")
    comprobar("V10_sin_justificacion" in codigos, "detecta que falta decir por qué se trató")
    print("     Lo que leería el agricultor:")
    for aviso in malo.json()["detail"]["avisos"]:
        print(f"       · {aviso['mensaje']}")

    print("\n5. Se apunta bien")
    bueno = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-01",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 2.43,
            "cultivo": "Trigo blando",
            "plaga": "Roya amarilla",
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.8,
        },
    )
    comprobar(bueno.status_code == 201, "el tratamiento se guarda")
    datos = bueno.json()
    comprobar(datos["fecha_fin_plazo_seguridad"] == "2026-05-22", "calcula el fin de los días de espera")
    comprobar(abs(datos["cantidad_total"] - 1.944) < 1e-6, "calcula la cantidad total de producto")

    print("\n6. Se intenta cosechar antes de tiempo")
    antes = cliente.post(
        "/api/cosecha",
        headers=cabeceras,
        json={"campana_id": campana["id"], "fecha": "2026-05-10", "parcela_id": parcela.json()["id"]},
    )
    comprobar(antes.status_code == 422, "no deja cosechar antes del plazo")
    print(f"     Lo que leería el agricultor: {antes.json()['detail']['avisos'][0]['mensaje']}")

    despues = cliente.post(
        "/api/cosecha",
        headers=cabeceras,
        json={"campana_id": campana["id"], "fecha": "2026-05-25", "parcela_id": parcela.json()["id"]},
    )
    comprobar(despues.status_code == 201, "sí deja cosechar pasados los días de espera")

    print("\n7. El abono")
    abono = cliente.post(
        "/api/fertilizantes",
        headers=cabeceras,
        json={"nombre": "Nitrato amónico 33,5%", "riqueza_n": 33.5},
    )
    comprobar(abono.status_code == 201, "se da de alta el abono con sus tres números")
    abonado = cliente.post(
        "/api/fertilizaciones",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-02-20",
            "parcela_id": parcela.json()["id"],
            "superficie_ha": 2.43,
            "fertilizante_id": abono.json()["id"],
            "kg_ha_producto": 300.0,
        },
    )
    comprobar(abonado.status_code == 201, "el abono se guarda")
    comprobar(
        abs(abonado.json()["uf_n_ha"] - 100.5) < 1e-6,
        "calcula el abono puro: 300 kg al 33,5 % = 100,5 kg de nitrógeno",
    )

    print("\n8. El cuaderno en papel")
    pdf = cliente.get(f"/api/cuaderno/pdf?campana_id={campana['id']}", headers=cabeceras)
    comprobar(pdf.status_code == 200, "el PDF se descarga")
    comprobar(pdf.content.startswith(b"%PDF"), "lo descargado es un PDF de verdad")
    comprobar(len(pdf.content) > 1500, f"el PDF tiene contenido ({len(pdf.content)} bytes)")
    ruta_pdf = "cuaderno_de_humo.pdf"
    with open(ruta_pdf, "wb") as fichero:
        fichero.write(pdf.content)
    print(f"     Guardado en {ruta_pdf} para poder abrirlo y mirarlo")

    csv = cliente.get(f"/api/cuaderno/export.csv?campana_id={campana['id']}", headers=cabeceras)
    comprobar(csv.status_code == 200, "la exportación se descarga")
    texto = csv.content.decode("utf-8")
    comprobar("El Prado" in texto, "la exportación lleva la parcela")
    comprobar(texto.startswith("\ufeff"), "la exportación lleva BOM, así Excel no rompe las tildes")

    print("\n9. Qué falta por completar")
    falta = cliente.get(f"/api/cuaderno/falta?campana_id={campana['id']}", headers=cabeceras)
    comprobar(falta.status_code == 200, "se puede preguntar qué falta")
    for pendiente in falta.json()["pendientes"]:
        print(f"     · {pendiente['mensaje']}")

    print("\n10. La ayuda")
    ayuda = cliente.get("/api/ayuda").json()
    comprobar("para_que_sirve" in ayuda["porques"], "la ayuda trae los porqués")
    comprobar(
        ayuda["plazos_legales"]["productos_electronico_desde"] == "01/01/2027",
        "dice la fecha en que el registro pasa a ser electrónico",
    )

    # Los pueblos, para poder dar de alta una parcela sin saberse ningún código. Esta lista es
    # local (no hace falta internet), así que se puede comprobar aquí siempre.
    print("\n10 bis. Elegir el pueblo en vez de teclearlo")
    municipios = cliente.get("/api/municipios", params={"buscar": "calvarrasa"}).json()
    comprobar(municipios["total"] == 2248, f"están los 2.248 municipios ({municipios['total']})")
    nombres = [m["nombre"] for m in municipios["municipios"]]
    comprobar(
        "Calvarrasa de Arriba" in nombres,
        "se encuentra un pueblo escribiendo las primeras letras, sin tildes ni códigos",
    )
    comprobar(
        any(m["codigo_ine"] == "37070" for m in municipios["municipios"]),
        "y viene con su código oficial, que es el que usa el SIGPAC",
    )

    # El mapa: la puerta que permite elegir la tierra tocándola. Aquí se comprueba lo que se puede
    # comprobar sin internet (si el servicio contesta o no es cosa del día), que es que la puerta
    # existe, dice de dónde saca las imágenes y rechaza una zona imposible.
    print("\n10 ter. El mapa para elegir la tierra tocándola")
    mapa = cliente.get("/api/mapa/estado")
    comprobar(mapa.status_code == 200, "se puede preguntar qué hay detrás del mapa")
    datos_mapa = mapa.json()
    comprobar(
        {"foto", "linderos", "cultivo"} <= set(datos_mapa["capas"]),
        "están las tres capas: la foto, los linderos y el cultivo declarado",
    )
    comprobar(
        "conexión" in datos_mapa["mensaje_sin_conexion"],
        "y se dice claro que el mapa necesita conexión",
    )
    al_reves = cliente.get(
        "/api/mapa/imagen",
        params={"capa": "foto", "oeste": -5.55, "sur": 40.91, "este": -5.56, "norte": 40.90},
    )
    comprobar(
        al_reves.status_code == 422,
        "una zona al revés se rechaza en vez de enseñar otro sitio",
    )

    print("\n11. El certificado digital")
    estado_certificado = cliente.get("/api/cuenta/certificado/estado")
    comprobar(estado_certificado.status_code == 200, "se puede preguntar por el certificado")
    comprobar(
        estado_certificado.json()["configurado"] is True,
        "la instalación está configurada para leer el certificado",
    )

    # El certificado de la finca dada de alta en el paso 2 (NIF 70922320A).
    dn_propio = "CN=PEREZ VELASCO DAVID,SN=PEREZ VELASCO,G=DAVID,SERIALNUMBER=70922320A,C=ES"
    con_certificado = cliente.post(
        "/api/cuenta/entrar-con-certificado",
        headers={"X-SSL-Client-Subject": dn_propio, "X-SSL-Client-Verify": "SUCCESS"},
    )
    comprobar(
        con_certificado.status_code == 200,
        "se entra con el certificado, sin teclear correo ni clave",
    )
    comprobar(bool(con_certificado.json().get("token")), "devuelve token")

    dn_ajeno = "CN=OTRO AGRICULTOR,SERIALNUMBER=12345678Z"
    ajeno = cliente.post(
        "/api/cuenta/entrar-con-certificado",
        headers={"X-SSL-Client-Subject": dn_ajeno, "X-SSL-Client-Verify": "SUCCESS"},
    )
    comprobar(ajeno.status_code == 403, "un certificado de otro NIF NO entra")
    comprobar(
        "correo y tu clave" in ajeno.json()["detail"],
        "y el mensaje le dice qué hacer, no solo que no",
    )

    no_validado = cliente.post(
        "/api/cuenta/entrar-con-certificado",
        headers={"X-SSL-Client-Subject": dn_propio, "X-SSL-Client-Verify": "FAILED"},
    )
    comprobar(
        no_validado.status_code == 401,
        "si el servidor web dice que el certificado no vale, no se entra",
    )

    print("\n12. La firma del cuaderno")
    cabeceras_firma = {
        **cabeceras,
        "X-SSL-Client-Subject": dn_propio,
        "X-SSL-Client-Verify": "SUCCESS",
    }

    estado_firma = cliente.get("/api/firmas/estado", headers=cabeceras_firma).json()
    comprobar(estado_firma["estado"] == "sin_firmar", "todavía no está firmado")
    comprobar(estado_firma["puede_firmar"] is True, "con el certificado se puede firmar")

    preparado = cliente.get("/api/firmas/preparar", headers=cabeceras_firma).json()
    comprobar(len(preparado["huella"]) == 64, "el fichero a firmar tiene su huella")
    comprobar(
        "AutoFirmaCommandLine" in preparado["comando"],
        "la orden es la de AutoFirma, sacada del manual",
    )
    comprobar(
        preparado["contenido"].startswith("CUADERNO DE CAMPO"),
        "el fichero se puede abrir y leer",
    )

    fichero = cliente.get("/api/firmas/fichero", headers=cabeceras_firma).text
    comprobar(
        hashlib.sha256(fichero.encode("utf-8")).hexdigest() == preparado["huella"],
        "la huella es la del fichero que se descarga",
    )

    firmado = cliente.post(
        "/api/firmas",
        headers=cabeceras_firma,
        json={
            "entidad": "cuaderno",
            "campana_id": preparado["campana_id"],
            "huella": preparado["huella"],
            "nombre_del_fichero": preparado["nombre_del_fichero"],
        },
    )
    comprobar(firmado.status_code == 201, "se guarda la firma")
    comprobar(firmado.json()["firmante_nif"] == "70922320A", "queda apuntado quién firmó")
    comprobar(
        firmado.json()["nota_verificacion"] and "no se ha mandado" in firmado.json()["nota_verificacion"],
        "y se apunta que no había fichero de firma que comprobar, en vez de dar por hecho que sí",
    )

    # Y ahora la comprobación de verdad. Aquí no se puede firmar de verdad (haría falta
    # AutoFirma y el certificado del agricultor), pero sí se puede comprobar **lo que NO se
    # puede aceptar**: que un fichero que no es una firma quede registrado como comprobado.
    #
    # Antes de la ronda 12 esto no se miraba: se subía cualquier cosa y se guardaba igual. Ahora
    # se lee el fichero de firma. Un fichero que no lo es se guarda pero **marcado como no
    # comprobado**, y eso es lo que se comprueba aquí: que el programa no diga «comprobada» de
    # algo que no ha podido mirar.
    no_es_una_firma = cliente.post(
        "/api/firmas",
        headers=cabeceras_firma,
        json={
            "entidad": "cuaderno",
            "campana_id": preparado["campana_id"],
            "huella": preparado["huella"],
            "contenido": base64.b64encode(b"esto no es una firma").decode(),
        },
    )
    comprobar(
        no_es_una_firma.status_code == 201,
        "un fichero que no es una firma se guarda igual (no se deja al agricultor sin firmar)",
    )
    comprobar(
        no_es_una_firma.json()["verificada_criptograficamente"] is False,
        "pero NO se dice que esté comprobada: eso sería mentir en el único sitio donde no se puede",
    )
    comprobar(
        "no es un fichero de firma" in (no_es_una_firma.json()["nota_verificacion"] or ""),
        "y se explica en palabras que el agricultor entiende, sin jerga",
    )

    # Y una firma de verdad: la de ejemplo, hecha con OpenSSL, que **no** es de este cuaderno.
    # Tiene que rechazarse. Es la prueba de que la comprobación no es de adorno.
    firma_de_ejemplo = (
        RAIZ / "backend" / "tests" / "fixtures" / "firma_cades" / "firma_destacada.p7s"
    ).read_bytes()
    ajena = cliente.post(
        "/api/firmas",
        headers=cabeceras_firma,
        json={
            "entidad": "cuaderno",
            "campana_id": preparado["campana_id"],
            "huella": preparado["huella"],
            "contenido": base64.b64encode(firma_de_ejemplo).decode(),
        },
    )
    comprobar(
        ajena.status_code == 422,
        "una firma DE VERDAD de otro cuaderno se rechaza: no basta con que sea una firma",
    )
    comprobar(
        "no es de este cuaderno" in ajena.json()["detail"],
        "y el mensaje dice qué ha pasado, no un código de error",
    )

    despues_de_firmar = cliente.get("/api/firmas/estado", headers=cabeceras_firma).json()
    comprobar(despues_de_firmar["estado"] == "firmado", "el cuaderno queda firmado")
    comprobar(
        "Nadie lo ha cambiado" in despues_de_firmar["mensaje"],
        "y lo dice con esas palabras",
    )

    # Ahora se apunta algo más, y la firma tiene que dejar de valer.
    labor = cliente.post(
        "/api/labores",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "tipo": "poda",
            "fecha": "2026-06-01",
            "parcela_id": parcela.json()["id"],
            "superficie_ha": 1.0,
        },
    )
    comprobar(labor.status_code == 201, "se apunta una labor más")

    cambiado = cliente.get("/api/firmas/estado", headers=cabeceras_firma).json()
    comprobar(
        cambiado["estado"] == "cambiado_despues_de_firmar",
        "al cambiar el cuaderno, la firma deja de valer y se avisa",
    )
    comprobar(
        "Vuelve a firmarlo" in cambiado["mensaje"],
        "y el aviso dice qué hacer, no solo que algo va mal",
    )

    print("\n13. Naves, almacenes y clases de tratamiento")
    almacen = cliente.post(
        "/api/instalaciones",
        headers=cabeceras,
        json={"alias": "El almacén grande", "tipo": "almacen", "uso": "Guardar el grano"},
    )
    comprobar(almacen.status_code == 201, "se da de alta una nave o un almacén")
    comprobar(almacen.json()["tipo"] == "almacen", "con su tipo")

    en_nave = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-06-10",
            "tipo": "instalaciones",
            "instalacion_id": almacen.json()["id"],
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.5,
            "plazo_reentrada_dias": 3,
        },
    )
    comprobar(en_nave.status_code == 201, "se apunta un tratamiento de una nave")
    comprobar(en_nave.json()["parcela_id"] is None, "sin parcela: fue en una nave")
    comprobar(en_nave.json()["tipo"] == "instalaciones", "queda claro de qué clase fue")

    sin_nave = cliente.post(
        "/api/tratamientos/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-06-10",
            "tipo": "instalaciones",
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.5,
        },
    )
    avisos_sin_nave = [a["codigo"] for a in sin_nave.json()["avisos"]]
    comprobar(
        "V20_sin_instalacion" in avisos_sin_nave,
        "sin decir la nave no deja apuntarlo",
    )

    postcosecha = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-01",
            "tipo": "postcosecha",
            "instalacion_id": almacen.json()["id"],
            "producto_cosechado": "Trigo",
            "lote_cosecha": "L-2026-07",
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.3,
        },
    )
    comprobar(postcosecha.status_code == 201, "se apunta un tratamiento al producto recogido")
    comprobar(
        postcosecha.json()["producto_cosechado"] == "Trigo",
        "con el producto y su partida",
    )

    # Y lo de siempre tiene que seguir funcionando igual.
    normal = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-02",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 2.43,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.8,
        },
    )
    comprobar(normal.status_code == 201, "un tratamiento de parcela sigue apuntándose igual")
    comprobar(normal.json()["tipo"] == "parcela", "y por defecto es en la parcela")

    print("\n14. El plan de abono del año")
    plan = cliente.post(
        "/api/planes",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "parcela_id": parcela.json()["id"],
            "cultivo": "Trigo blando",
            "superficie_ha": 2.43,
            "necesidad_n": 100.0,
            "necesidad_p": 40.0,
            "necesidad_k": 60.0,
        },
    )
    comprobar(plan.status_code == 201, "se hace el plan de abono del año")
    plan_id = plan.json()["id"]

    resumen = cliente.get(f"/api/planes/{plan_id}/resumen", headers=cabeceras).json()
    comprobar(
        abs(resumen["filas"][0]["aplicado"] - 100.5) < 1e-6,
        "el plan cuenta el abono que YA se había echado en esa parcela",
    )
    comprobar(
        resumen["filas"][0]["previsto"] == 100.0,
        "el plan dice lo que el cultivo se va a llevar",
    )

    contra_el_plan = cliente.post(
        "/api/fertilizaciones",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-03-01",
            "parcela_id": parcela.json()["id"],
            "superficie_ha": 2.43,
            "fertilizante_id": abono.json()["id"],
            "kg_ha_producto": 300.0,
            "plan_id": plan_id,
        },
    )
    comprobar(contra_el_plan.status_code == 201, "se apunta un abono contra el plan")

    con_lo_echado = cliente.get(f"/api/planes/{plan_id}", headers=cabeceras).json()
    comprobar(
        abs(con_lo_echado["aplicado_n"] - 201.0) < 1e-6,
        "el plan va contando todo lo que se echa: 100,5 de antes + 100,5 de ahora",
    )
    comprobar(
        con_lo_echado["se_ha_pasado"] is True,
        "y avisa al pasarse: 100,5 kg contra un plan de 100",
    )
    comprobar(
        "más de lo que tenías previsto" in con_lo_echado["mensaje"],
        "el aviso dice qué pasa",
    )

    # El aviso tiene que salir EN EL MOMENTO de apuntar, no después.
    aviso_previo = cliente.post(
        "/api/fertilizaciones/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-03-02",
            "parcela_id": parcela.json()["id"],
            "superficie_ha": 2.43,
            "fertilizante_id": abono.json()["id"],
            "kg_ha_producto": 100.0,
        },
    )
    codigos_aviso = [a["codigo"] for a in aviso_previo.json()["avisos"]]
    comprobar(
        "F5_plan_excedido" in codigos_aviso,
        "al apuntar otro abono avisa de que se pasa del plan, sin tener que enlazarlo",
    )

    # Las dos cosas que pide el anexo II del CUE y no se preguntaban (ronda 24).
    #
    # El cultivo del año anterior no se pregunta: se saca de la campaña anterior, que es un dato
    # que el cuaderno ya tiene. Para poder comprobarlo hace falta una campaña anterior de verdad,
    # así que se crea aquí con su cultivo declarado.
    anterior = cliente.post(
        "/api/campanas",
        headers=cabeceras,
        json={
            "anio": campana["anio"] - 1,
            "fecha_inicio": f"{campana['anio'] - 1}-09-01",
            "fecha_fin": f"{campana['anio']}-08-31",
        },
    )
    comprobar(anterior.status_code == 201, "se puede crear la campaña anterior")
    comprobar(
        cliente.post(
            f"/api/parcelas/{parcela.json()['id']}/cultivos",
            headers=cabeceras,
            json={"campana_id": anterior.json()["id"], "especie": "Cebada"},
        ).status_code
        == 201,
        "y se puede decir qué había sembrado el año anterior",
    )

    con_herramienta = cliente.post(
        "/api/planes",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "parcela_id": parcela.json()["id"],
            "cultivo": "Trigo blando",
            "superficie_ha": 2.43,
            "herramienta": True,
        },
    )
    comprobar(con_herramienta.status_code == 201, "el plan se puede guardar diciendo con qué se hizo")
    comprobar(
        con_herramienta.json()["herramienta"] is True,
        "y el cuaderno lo devuelve: antes se guardaba y no se preguntaba",
    )

    sin_herramienta = cliente.post(
        "/api/planes",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "parcela_id": parcela.json()["id"],
            "cultivo": "Trigo blando",
            "superficie_ha": 2.43,
        },
    )
    comprobar(
        sin_herramienta.json()["herramienta"] is None,
        "y sin contestarlo se queda vacío, no en «no»: un «no» de relleno sería un dato falso",
    )

    los_planes = cliente.get("/api/planes", headers=cabeceras).json()
    el_que_lleva_herramienta = next(p for p in los_planes if p["id"] == con_herramienta.json()["id"])
    comprobar(
        el_que_lleva_herramienta["cultivo_precedente"] == "Cebada",
        "el plan dice el cultivo del año anterior sin preguntárselo al agricultor",
    )

    print("\n15. Los análisis de laboratorio")
    vocabulario_analisis = cliente.get("/api/interfaz").json()
    comprobar(
        len(vocabulario_analisis["tipos_analitica"]) == 5,
        "el vocabulario trae las cinco clases de análisis",
    )
    comprobar(
        len(vocabulario_analisis["parametros_analitica"]["suelo"]) == 9,
        "y los nueve números del boletín de tierra, que son los que pide la norma",
    )

    # Un boletín de tierra con un número inventado al lado: el inventado no puede entrar.
    analisis = cliente.post(
        "/api/analiticas",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "tipo": "suelo",
            "fecha_toma_muestra": "2026-02-14",
            "fecha_resultado": "2026-02-28",
            "parcela_id": parcela.json()["id"],
            "laboratorio": "Laboratorio Agrario de Villamuriel",
            "numero_informe": "2026/0417",
            "parametros": [
                {"clave": "materia_organica", "valor": 1.8},
                {"clave": "ph", "valor": "7,4"},
                {"clave": "fosforo_asimilable", "valor": 18.0},
                {"clave": "color_de_la_tierra", "valor": 3},
            ],
        },
    )
    comprobar(analisis.status_code == 201, "se apunta un análisis de suelo")
    guardado = analisis.json()
    claves = [p["clave"] for p in guardado["parametros"]]
    comprobar(
        "color_de_la_tierra" not in claves,
        "un número que no existe en el catálogo no se cuela",
    )
    comprobar(guardado["parametros"][1]["valor"] == 7.4, "la coma del móvil se entiende")
    comprobar(guardado["donde"] == "El Prado", "dice de qué parcela salió la muestra")

    # El boletín, subido como lo subiría el agricultor: un PDF de verdad.
    subida = cliente.post(
        f"/api/analiticas/{guardado['id']}/informe",
        headers=cabeceras,
        files={"fichero": ("boletin.pdf", b"%PDF-1.4 boletin de prueba", "application/pdf")},
    )
    comprobar(subida.status_code == 200, "se sube el boletín del laboratorio")
    bajado = cliente.get(f"/api/analiticas/{guardado['id']}/informe", headers=cabeceras)
    comprobar(
        bajado.content == b"%PDF-1.4 boletin de prueba",
        "y se vuelve a descargar igual que se subió",
    )

    sin_sitio = cliente.post(
        "/api/analiticas/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "tipo": "suelo",
            "fecha_toma_muestra": "2026-02-14",
            "parametros": [{"clave": "ph", "valor": 7.4}],
        },
    )
    codigos_analisis = [a["codigo"] for a in sin_sitio.json()["avisos"]]
    comprobar(
        "N3_sin_sitio" in codigos_analisis,
        "un análisis de tierra sin parcela no se puede guardar",
    )

    agua = cliente.post(
        "/api/analiticas",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "tipo": "agua_riego",
            "fecha_toma_muestra": "2026-03-05",
            "parcela_id": parcela.json()["id"],
            "laboratorio": "Laboratorio Agrario de Villamuriel",
            "parametros": [{"clave": "nitratos", "valor": 42.0}],
        },
    )
    comprobar(agua.status_code == 201, "se apunta un análisis del agua de riego")
    comprobar(
        [p["clave"] for p in agua.json()["parametros"]] == ["nitratos"],
        "del agua se guarda el nitrato, y no los parámetros de la tierra",
    )

    informe = cliente.get(
        f"/api/analiticas/informe?campana_id={campana['id']}", headers=cabeceras
    ).json()
    comprobar(informe["cuantos"] == 2, "el informe de análisis lleva los dos análisis")

    # Y el plan de abono se puede apoyar en él.
    plan_con_analisis = cliente.put(
        f"/api/planes/{plan_id}",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "parcela_id": parcela.json()["id"],
            "cultivo": "Trigo blando",
            "superficie_ha": 2.43,
            "necesidad_n": 100.0,
            "necesidad_p": 40.0,
            "necesidad_k": 60.0,
            "analitica_id": guardado["id"],
        },
    )
    comprobar(plan_con_analisis.status_code == 200, "el plan se puede apoyar en el análisis")
    con_analisis = cliente.get(f"/api/planes/{plan_id}", headers=cabeceras).json()
    comprobar(
        con_analisis["analisis"]["id"] == guardado["id"],
        "y el plan devuelve el análisis entero, sin una segunda llamada",
    )
    comprobar(
        con_analisis["analisis"]["parametros_con_nombre"][1]["texto"] == "7,40",
        "con cada número ya escrito como se lee en castellano",
    )

    # El «Informe Analíticas» tiene que salir en el cuaderno que se lleva al papel: en la
    # app oficial está en Utilidades > Ver listados, y aquí sale junto al cuaderno.
    csv_con_analisis = cliente.get(
        f"/api/cuaderno/export.csv?campana_id={campana['id']}", headers=cabeceras
    ).content.decode("utf-8-sig")
    comprobar(
        "INFORME DE ANÁLISIS" in csv_con_analisis,
        "la exportación lleva el informe de análisis",
    )
    comprobar(
        "Fósforo asimilable: 18,00 ppm" in csv_con_analisis,
        "y lleva los números del boletín con su nombre y su unidad",
    )
    pdf_con_analisis = cliente.get(
        f"/api/cuaderno/pdf?campana_id={campana['id']}", headers=cabeceras
    )
    comprobar(
        pdf_con_analisis.content.startswith(b"%PDF")
        and len(pdf_con_analisis.content) > 1500,
        "y el PDF sigue saliendo entero con el análisis dentro",
    )

    print("\n16. Las medidas preventivas de la finca")
    vocabulario_medidas = cliente.get("/api/interfaz").json()
    comprobar(
        len(vocabulario_medidas["medidas_preventivas"]) == 10,
        "el vocabulario trae las diez medidas",
    )
    comprobar(
        all(m["pregunta"].startswith("¿") for m in vocabulario_medidas["medidas_preventivas"]),
        "y cada una se pregunta en cristiano, no con su nombre oficial",
    )

    sin_declarar = cliente.get("/api/medidas", headers=cabeceras).json()
    comprobar(sin_declarar["declarada"] is False, "al principio no hay nada declarado")
    comprobar(
        len(sin_declarar["medidas"]) == 10,
        "pero salen las diez preguntas: si no, no se podría marcar la primera",
    )

    # Sin medidas declaradas, al apuntar un producto el cuaderno avisa de que falta esa
    # sección. Es la gestión integrada de plagas: hay que poder demostrar que se miraron
    # otras cosas antes de tratar.
    aviso_gip = cliente.post(
        "/api/tratamientos/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-03",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 2.43,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.8,
        },
    )
    codigos_gip = [a["codigo"] for a in aviso_gip.json()["avisos"]]
    comprobar(
        "P2_tratamiento_sin_medidas" in codigos_gip,
        "sin medidas declaradas, el apunte avisa de que falta esa sección",
    )
    comprobar(
        aviso_gip.json()["puede_guardarse"] is True,
        "y no impide apuntar: el agricultor puede declararlas después",
    )

    declaradas = cliente.put(
        "/api/medidas",
        headers=cabeceras,
        json={
            "aplicadas": ["rotacion", "muestreo", "higiene", "una_medida_inventada"],
            "observaciones": {"muestreo": "Miro el campo antes de decidir"},
        },
    )
    comprobar(
        declaradas.status_code == 200 and declaradas.json()["cuantas"] == 3,
        "se declaran las medidas que se hacen",
    )
    comprobar(
        declaradas.json()["descartadas"] == ["una_medida_inventada"],
        "una medida que no está en el catálogo se descarta y se dice, sin perder las demás",
    )

    con_medidas = cliente.post(
        "/api/tratamientos/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-03",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 2.43,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.8,
        },
    )
    codigos_con_medidas = [a["codigo"] for a in con_medidas.json()["avisos"]]
    comprobar(
        "P2_tratamiento_sin_medidas" not in codigos_con_medidas,
        "una vez declaradas, el apunte ya no avisa",
    )

    # Y el apunte guarda lo que de verdad se hizo esa vez, que es otra cosa distinta.
    apunte_con_medidas = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-04",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 2.43,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.8,
            "medidas": ["muestreo", "higiene"],
        },
    )
    comprobar(
        apunte_con_medidas.status_code == 201
        and apunte_con_medidas.json()["medidas"] == ["muestreo", "higiene"],
        "el apunte guarda lo que se hizo esa vez, que es distinto de lo que se hace siempre",
    )

    informe_medidas = cliente.get("/api/medidas/informe", headers=cabeceras).json()
    comprobar(
        informe_medidas["cuantas"] == 3
        and "Rotación de cultivos" in [f["medida"] for f in informe_medidas["filas"]],
        "el informe lleva las medidas con su nombre oficial, no con el código",
    )
    comprobar(
        informe_medidas["filas"][1]["observaciones"] == "Miro el campo antes de decidir",
        "y lleva lo que el agricultor escribió con sus palabras",
    )

    csv_medidas = cliente.get(
        f"/api/cuaderno/export.csv?campana_id={campana['id']}", headers=cabeceras
    ).content.decode("utf-8-sig")
    comprobar(
        "MEDIDAS PREVENTIVAS" in csv_medidas and "Rotación de cultivos" in csv_medidas,
        "el cuaderno que se lleva al papel lleva las medidas preventivas",
    )

    print("\n17. Lo que se vende")
    vocabulario_venta = cliente.get("/api/interfaz").json()
    comprobar(
        {v["valor"] for v in vocabulario_venta["tipos_venta"]}
        == {"comercializada", "venta_directa"},
        "el vocabulario trae las dos clases de venta que separa la norma",
    )
    comprobar(
        vocabulario_venta["venta"]["titulo"] == "Lo que he vendido",
        "y la pantalla se llama como lo llama el agricultor, no como la norma",
    )

    # Vender sin haber apuntado la cosecha: el cuaderno avisa de que no cuadra.
    sin_cosecha = cliente.post(
        "/api/ventas/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-10",
            "producto": "Trigo blando",
            "cantidad": 42000.0,
            "unidad": "kg",
            "comprador": "Cooperativa Agrícola de Peñaranda",
        },
    )
    codigos_venta = [a["codigo"] for a in sin_cosecha.json()["avisos"]]
    comprobar(
        "C6_venta_sin_cosecha" in codigos_venta,
        "vender sin haber apuntado la cosecha avisa",
    )
    comprobar(
        sin_cosecha.json()["puede_guardarse"] is True,
        "y no impide apuntar la venta: puede estar vendiendo de otro año",
    )

    # Se apunta que se cogió la cosecha, y ahora sí cuadra.
    cosechado_humo = cliente.post(
        "/api/cosecha",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-01",
            "parcela_id": parcela.json()["id"],
            "cantidad_kg": 45000,
        },
    )
    comprobar(cosechado_humo.status_code == 201, "se apunta que se cogió la cosecha")

    venta = cliente.post(
        "/api/ventas",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "tipo": "comercializada",
            "fecha": "2026-07-10",
            "fecha_fin": "2026-07-12",
            "producto": "Trigo blando",
            "variedad": "Craklin",
            "cantidad": 42.0,
            "unidad": "t",
            "lote": "L-2026-07",
            "comprador": "Cooperativa Agrícola de Peñaranda",
            "numero_albaran": "ALB-2026-118",
            "parcela_id": parcela.json()["id"],
        },
    )
    comprobar(venta.status_code == 201, "se apunta la venta")
    comprobar(
        venta.json()["kilos"] == 42000.0,
        "42 toneladas se guardan como 42 y se leen como 42.000 kg",
    )
    comprobar(
        venta.json()["texto_cantidad"] == "42,00 t",
        "y la cantidad se enseña como se lee en castellano",
    )

    # 42.000 kg vendidos de 45.000 kg cogidos: 2.000 más todavía caben.
    con_cosecha = cliente.post(
        "/api/ventas/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-14",
            "producto": "Trigo blando",
            "cantidad": 2000.0,
            "unidad": "kg",
            "comprador": "Cooperativa Agrícola de Peñaranda",
        },
    )
    codigos_con_cosecha = [a["codigo"] for a in con_cosecha.json()["avisos"]]
    comprobar(
        "C6_venta_sin_cosecha" not in codigos_con_cosecha
        and "C7_mas_de_lo_cosechado" not in codigos_con_cosecha,
        "con la cosecha apuntada y sin pasarse, ya no avisa",
    )

    pasada = cliente.post(
        "/api/ventas/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-15",
            "producto": "Trigo blando",
            "cantidad": 20000.0,
            "unidad": "kg",
            "comprador": "Cooperativa Agrícola de Peñaranda",
        },
    )
    codigos_pasada = [a["codigo"] for a in pasada.json()["avisos"]]
    comprobar(
        "C7_mas_de_lo_cosechado" in codigos_pasada,
        "42.000 kg vendidos + 20.000 más pasa de los 45.000 kg apuntados",
    )

    informe_ventas = cliente.get("/api/ventas/informe", headers=cabeceras).json()
    comprobar(informe_ventas["cuantas"] == 1, "el informe de ventas lleva la venta")
    comprobar(
        informe_ventas["filas"][0]["cantidad"] == "42,00 t",
        "con su cantidad y su unidad",
    )
    comprobar(
        informe_ventas["filas"][0]["comprador"] == "Cooperativa Agrícola de Peñaranda",
        "y con a quién se vendió",
    )

    resumen_ventas = cliente.get("/api/ventas/resumen", headers=cabeceras).json()
    comprobar(
        resumen_ventas["filas"][2]["kilos"] == 3000.0,
        "el resumen dice lo que queda por vender: 45.000 cogidos menos 42.000 vendidos",
    )
    comprobar(resumen_ventas["cuadra"] is True, "y que cuadra")

    csv_ventas = cliente.get(
        f"/api/cuaderno/export.csv?campana_id={campana['id']}", headers=cabeceras
    ).content.decode("utf-8-sig")
    comprobar(
        "COSECHA COMERCIALIZADA" in csv_ventas and "ALB-2026-118" in csv_ventas,
        "el cuaderno que se lleva al papel lleva lo que se ha vendido",
    )

    print("\n18. El volcado oficial a la Junta (IUWS)")
    estado_iuws = cliente.get("/api/iuws/estado", headers=cabeceras).json()
    comprobar(
        estado_iuws["conectado"] is False,
        "el volcado no está conectado, y lo dice en vez de intentarlo",
    )
    comprobar(
        estado_iuws["descriptor_cargado"] is False,
        "y avisa de que el mapeo del descriptor v3.11.4 aún no está completo",
    )
    claves_que_faltan = {f["clave"] for f in estado_iuws["faltan"]}
    for clave in ("descriptor", "catalogos", "nombre_comercial", "dominio", "certificado"):
        comprobar(clave in claves_que_faltan, f"falta por resolver: {clave}")
    comprobar(
        all(f["quien"] for f in estado_iuws["faltan"]),
        "cada cosa que falta dice de quién depende",
    )
    comprobar(
        estado_iuws["url_version"] == "https://sga.entornointegracion.es/IUWS/api/version",
        "apunta al entorno de integración: es lo que se puede usar sin autorización",
    )
    comprobar(
        estado_iuws["contactos"]["castilla_y_leon"] == "comercialcuecyl@jcyl.es",
        "y trae los dos correos a los que se pide el acceso",
    )
    comprobar(
        len(estado_iuws["campos_del_formulario"]) == 8,
        "con los ocho campos del formulario de la Junta",
    )

    contenido_iuws = cliente.get("/api/iuws/contenido", headers=cabeceras).json()
    comprobar(
        len(contenido_iuws["bloques"]) >= 10,
        "declara los bloques del contenido mínimo que se vuelcan",
    )
    comprobar(
        "SIEX v3.11" in contenido_iuws["fuente"] and "Anexo II" in contenido_iuws["fuente"],
        "y de dónde sale cada número de campo",
    )
    nombres_de_campo = [
        campo["nombre"] for campo in contenido_iuws["campos_por_bloque"]["tratamientos"]
    ]
    comprobar(
        "Superficie tratada (ha)" in nombres_de_campo,
        "los campos llevan el nombre del documento, no uno inventado",
    )
    comprobar(
        contenido_iuws["campos_de_catalogo"],
        "y se listan aparte los campos que son código de catálogo",
    )

    paquete_iuws = cliente.get("/api/iuws/paquete", headers=cabeceras).json()
    comprobar(
        paquete_iuws["formato"] == "sobre-documentado-con-contenido-minimo-siex",
        "el paquete dice qué formato tiene",
    )
    comprobar(
        "NO en el formato del descriptor" in paquete_iuws["aviso"],
        "y avisa de que NO es el fichero que se manda a la Junta",
    )
    sobre_iuws = paquete_iuws["CUADERNO"][0]
    comprobar(sobre_iuws["IdTitular"] == "70922320A", "el sobre lleva el NIF del titular")
    comprobar(sobre_iuws["CAExplotacion"] == "13", "y el código de Castilla y León, que es 13")
    actividades = sobre_iuws["ActividadesExplotacion"]
    comprobar(
        len(actividades["tratamientos"]) >= 1,
        "y lleva dentro los tratamientos que hay apuntados",
    )
    fila_iuws = actividades["tratamientos"][0]
    comprobar(
        fila_iuws["IdAjena"].startswith("CD-70922320A-T-"),
        "cada actividad lleva su identificador ajeno, que es lo que evita duplicarla",
    )
    comprobar(
        fila_iuws["c24"] is not None,
        "con el número de registro del producto dentro",
    )
    # Ojo con este cambio: hasta la ronda 10 el cultivo salía vacío porque no teníamos los
    # códigos oficiales. Ahora sí (catálogo de productos del SIGPAC), así que sale el código y
    # sale marcado que es de catálogo. Los que NO tenemos siguen vacíos.
    comprobar(
        fila_iuws["c6"] is not None and fila_iuws["c6_catalogo"] is True,
        "y el cultivo con el CÓDIGO oficial del catálogo de productos del FEGA",
    )
    comprobar(
        fila_iuws["c54"] is None and fila_iuws["c54_catalogo"] is True,
        "mientras los catálogos que no tenemos siguen vacíos y marcados, no inventados",
    )

    descarga_iuws = cliente.get("/api/iuws/paquete.json", headers=cabeceras)
    comprobar(
        descarga_iuws.status_code == 200
        and "attachment" in descarga_iuws.headers["content-disposition"],
        "el paquete se puede descargar para pasárselo a quien integre",
    )

    # La prueba de conexión con la Junta. **Aquí sí se sale a internet**, y es lo único que
    # demuestra de verdad que hay camino hasta el interfaz: los tests comprueban el flujo con un
    # transporte de mentira, y esto llama a la Junta.
    #
    # El método de versión es el único que el interfaz deja abierto —sin certificado, sin nombre
    # comercial y sin estar dado de alta—, así que esta prueba **funciona hoy**, aunque no haya
    # nada configurado. Eso es lo que la hace útil: separa «no hay camino hasta la Junta» de «la
    # Junta no me reconoce», que son dos problemas que se confunden todo el tiempo.
    sin_pedirlo = cliente.get("/api/iuws/version", headers=cabeceras).json()
    comprobar(
        sin_pedirlo["probado"] is False,
        "la prueba de conexión no llama al interfaz si no se le pide",
    )
    comprobar(
        sin_pedirlo["se_puede_probar_ya"] is True,
        "pero dice que ya se puede probar, sin tener nada configurado",
    )

    prueba = cliente.get("/api/iuws/version?llamar=1", headers=cabeceras).json()
    if prueba.get("codigo") == 200:
        comprobar(prueba["conectado"] is True, "y se llama de verdad al interfaz de la Junta")
        comprobar(
            prueba["donde_contesta"] == "https://sga.entornointegracion.es",
            f"y contesta el entorno de integración del FEGA: {prueba['donde_contesta']}",
        )
        comprobar(
            "3.11" in prueba["respuesta"],
            f"con la versión que dice el interfaz: {prueba['respuesta']}",
        )
        comprobar(
            "versión" in prueba["mensaje"],
            "y se cuenta en castellano, no con un volcado del JSON",
        )
        comprobar(len(prueba["probadas"]) == 1, "la dirección de integración responde a la primera")
    else:
        print(
            "     (el interfaz de la Junta no ha contestado desde aquí: se sigue, que para eso "
            "está el aviso y no bloquea nada)"
        )

    comprobado = cliente.get("/api/iuws/comprobar-de-verdad", headers=cabeceras).json()
    # Desde el 27/09/2026 hay **dos** métodos comprobados con llamadas de verdad: la versión (que
    # contesta 200) y la llamada del token sin certificado (que es la que dice dónde se corta). Lo
    # que importa comprobar no es cuántos son, sino que **el de la versión esté y con la ruta
    # vigente**: la ruta antigua sin `/api/` era la que daba 404.
    comprobar(
        any(m["metodo"] == "/IUWS/api/version" for m in comprobado["metodos"]),
        "está apuntado el método de versión comprobado con la ruta vigente",
    )
    comprobar(
        all("404" not in m["que_contesto"] for m in comprobado["metodos"]),
        "y en la dirección de la comunidad ninguno contestó que no existe",
    )
    comprobar(
        len(comprobado["en_el_entorno_de_integracion"]) == 2,
        "y consta que la ruta antigua sin /api/ era la que daba 404",
    )
    comprobar(
        "certificado" in comprobado["por_que_no_se_prueba_lo_demas"].lower(),
        "y está dicho por qué no se prueban los demás: el servidor pide el certificado antes",
    )

    traduccion = cliente.post(
        "/api/iuws/leer-respuesta",
        headers=cabeceras,
        json={
            "respuesta": {
                "resultado": {
                    "codigoResultado": "PARCIAL",
                    "detalleImportacion": [
                        {"codigo": 3, "descripcion": "ok"},
                        {"codigo": 6, "descripcion": "mal"},
                    ],
                }
            }
        },
    ).json()
    comprobar(traduccion["es_parcial"] is True, "traduce una respuesta a medias del interfaz")
    comprobar(
        len(traduccion["actividades_fallidas"]) == 1
        and "ROMA" in traduccion["actividades_fallidas"][0]["explicacion"],
        "y dice qué actividad ha fallado y por qué, no «error 6»",
    )

    mensajes_iuws = cliente.get("/api/iuws/mensajes", headers=cabeceras).json()
    comprobar(
        len(mensajes_iuws["mensajes"]) == 19,
        "el catálogo de mensajes del interfaz está entero: los 19 códigos del anexo",
    )

    print("\n19. El asesor, la semilla y el agua")
    vocabulario_asesor = cliente.get("/api/interfaz").json()
    comprobar(
        vocabulario_asesor["maestros"]["seccion_asesor"] == "Quién me asesora",
        "el vocabulario trae la sección del asesor",
    )
    comprobar(
        {a["valor"] for a in vocabulario_asesor["ambitos_asesor"]} == {"gip", "produccion_integrada", "ecologico", "otros"},
        "y los ámbitos del registro de asesores",
    )
    comprobar(
        {o["valor"] for o in vocabulario_asesor["origenes_agua"]} == {
            "pozo", "canal", "balsa", "manantial", "rio", "comunidad_regantes", "red", "otro"
        },
        "y de dónde puede salir el agua de riego",
    )

    asesor = cliente.post(
        "/api/asesores",
        headers=cabeceras,
        json={
            "nombre": "Ana García Ruiz",
            "nif": "12345678Z",
            "numero_ropo": "ROPO-ASESOR-778",
            "ambito": "gip",
            "entidad_certificacion": "Producción Integrada de Castilla y León",
        },
    )
    comprobar(asesor.status_code == 201, "se da de alta el asesor con su número de ROPO")

    # Un asesor sin número de ROPO: la Junta no lo encontraría en su registro (error 7), así
    # que el apunte no se deja guardar.
    sin_ropo = cliente.post(
        "/api/asesores",
        headers=cabeceras,
        json={"nombre": "Sin papeles", "numero_ropo": ""},
    )
    aviso_asesor = cliente.post(
        "/api/tratamientos/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-05",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 2.43,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.8,
            "asesor_id": sin_ropo.json()["id"],
        },
    )
    codigos_asesor = [a["codigo"] for a in aviso_asesor.json()["avisos"]]
    comprobar(
        "S1_sin_ropo_asesor" in codigos_asesor,
        "un asesor sin número de ROPO no deja guardar el tratamiento",
    )

    con_asesor = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-06",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 2.43,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.8,
            "asesor_id": asesor.json()["id"],
            "asesor_fecha": "2026-05-04",
            "asesoramiento_validado": True,
            "asesoramiento_contrato": False,
        },
    )
    comprobar(con_asesor.status_code == 201, "se apunta un tratamiento asesorado")
    comprobar(
        con_asesor.json()["asesor_fecha"] == "2026-05-04",
        "con el día en que lo dijo el técnico",
    )

    # La semilla, con su dosis y su lote.
    siembra = cliente.post(
        "/api/labores",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "tipo": "siembra",
            "fecha": "2026-03-01",
            "parcela_id": parcela.json()["id"],
            "superficie_ha": 2.43,
            "cultivo": "Trigo blando",
            "cantidad_semilla_kg": 480.0,
            "dosis_siembra_kg_ha": 197.5,
            "lote_semilla": "L-SEM-2026-04",
            "material_adquirido": True,
            "siembra_directa": True,
        },
    )
    comprobar(siembra.status_code == 201, "se apunta la siembra con la semilla y su lote")
    comprobar(
        siembra.json()["lote_semilla"] == "L-SEM-2026-04",
        "y queda el número de lote, que es lo que salva una partida",
    )

    # El agua del riego, que también es un dato de abono.
    riego = cliente.post(
        "/api/labores",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "tipo": "riego",
            "fecha": "2026-06-01",
            "parcela_id": parcela.json()["id"],
            "superficie_ha": 2.43,
            "volumen_agua": 1200.0,
            "unidad_agua": "m3",
            "origen_agua": "pozo",
            "sistema_riego": "aspersion",
            "numero_contador": "CNT-4471",
            "nitratos_agua": 38.0,
        },
    )
    comprobar(riego.status_code == 201, "se apunta un riego con de dónde sale el agua")
    comprobar(
        riego.json()["nitratos_agua"] == 38.0,
        "y con los nitratos del agua, que son abono que ya recibe el cultivo",
    )

    paquete_final = cliente.get("/api/iuws/paquete", headers=cabeceras).json()
    actividades_final = paquete_final["CUADERNO"][0]["ActividadesExplotacion"]
    fila_asesorada = [
        f for f in actividades_final["tratamientos"] if f["c50"] == "ROPO-ASESOR-778"
    ]
    comprobar(
        fila_asesorada and fila_asesorada[0]["c44"] == "2026-05-04",
        "el volcado lleva el asesoramiento con su nº de ROPO y su fecha",
    )
    comprobar(
        actividades_final["siembra_plantacion"][0]["c10"] == "L-SEM-2026-04",
        "y lleva el lote de la semilla en el campo 10 del bloque de siembra",
    )
    comprobar(
        actividades_final["riego"][0]["c41"] == 38.0,
        "y los nitratos del agua en el campo 41, el del subbloque de fertirrigación",
    )

    # Las prácticas culturales que no son sembrar, plantar, regar ni coger la cosecha.
    #
    # Esto se añadió en la ronda 14, leyendo el documento oficial, que para el apartado «Otras
    # Prácticas Culturales» nombra «Laboreo, mantenimiento de cubierta, pastoreo». Faltaban dos
    # de las tres, y además la lista de tipos existía en el catálogo y **ninguna pantalla la
    # ofrecía**: todo lo que no fueran las cuatro de siempre se guardaba como «otra».
    catalogo_labores = cliente.get("/api/interfaz").json()
    comprobar(
        {"laboreo", "cubierta", "pastoreo"}
        <= {trabajo["id"] for trabajo in catalogo_labores["trabajos_de_labor"]},
        "las tres prácticas del documento oficial se pueden elegir: laboreo, cubierta y pastoreo",
    )
    comprobar(
        not (
            {"siembra", "plantacion", "riego", "cosecha"}
            & {trabajo["id"] for trabajo in catalogo_labores["trabajos_de_labor"]}
        ),
        "y no se vuelve a preguntar lo que ya tiene su botón en la pantalla de inicio",
    )

    cubierta = cliente.post(
        "/api/labores",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "tipo": "cubierta",
            "fecha": "2026-04-15",
            "parcela_id": parcela.json()["id"],
            "superficie_ha": 2.43,
        },
    )
    comprobar(
        cubierta.status_code == 201 and cubierta.json()["tipo"] == "cubierta",
        "se apunta un mantenimiento de la cubierta, que antes no se podía ni decir",
    )
    fichero_firmado = cliente.get("/api/firmas/fichero", headers=cabeceras).text
    comprobar(
        "Mantenimiento de la cubierta" in fichero_firmado,
        "y en el cuaderno sale con su nombre, no con el código en minúsculas",
    )

    print("\n20. El conector con el SIGPAC")
    estado_sigpac = cliente.get("/api/sigpac/estado").json()
    comprobar(
        estado_sigpac["cargados"] is True,
        "los datos oficiales del SIGPAC están descargados",
    )
    comprobar(
        estado_sigpac["productos"] == 933,
        f"y trae los 933 productos del catálogo del FEGA ({estado_sigpac['productos']})",
    )
    comprobar(
        "Creative Commons" in estado_sigpac["licencia"],
        "con su licencia, que se puede redistribuir diciendo de dónde sale",
    )

    # El conector de verdad: se le da una referencia y trae la parcela. **Aquí sí se sale a
    # internet**, que es lo que distingue la prueba de humo de los tests: los tests prueban el
    # parser contra una respuesta guardada, y esto prueba que el servicio del FEGA sigue
    # contestando como dice su documento.
    referencia = "37-22-0-0-501-427-1"
    consulta = cliente.post(
        "/api/sigpac/consultar", headers=cabeceras, json={"ref_sigpac": referencia}
    )
    comprobar(consulta.status_code == 200, "se puede preguntar al SIGPAC por un recinto")
    if consulta.status_code == 200 and consulta.json()["encontrado"]:
        datos_recinto = consulta.json()
        comprobar(
            datos_recinto["superficie_ha"] > 0,
            f"y devuelve la superficie ({datos_recinto['superficie_ha']} ha)",
        )
        comprobar(datos_recinto["uso"] == "TIERRAS ARABLES", "y el uso con su nombre oficial")
        comprobar(datos_recinto["tiene_dibujo"] is True, "y el dibujo del trozo")

        traida = cliente.post(
            "/api/parcelas/desde-sigpac",
            headers=cabeceras,
            json={"ref_sigpac": referencia, "alias": "La traída del SIGPAC"},
        )
        comprobar(traida.status_code == 201, "se da de alta la parcela desde el SIGPAC")
        parcela_traida = traida.json()
        comprobar(
            parcela_traida["superficie_oficial"] is True,
            "con la superficie oficial, no una medida a ojo",
        )
        comprobar(
            parcela_traida["pendiente_pct"] is not None,
            "y con la pendiente, que es un dato que antes había que buscar",
        )
        comprobar(
            parcela_traida["ref_sigpac"] == referencia,
            "y con su referencia, para poder volver a consultarla",
        )
        # Y la forma del trozo, que es lo que hasta la ronda 20 no se veía en ninguna parte:
        # el SIGPAC la devolvía, se guardaba en la base de datos y ahí se quedaba.
        comprobar(
            bool(parcela_traida["dibujo"]) and parcela_traida["dibujo"].startswith("M "),
            "y con el dibujo de su forma, que es lo que le deja reconocerla de un vistazo",
        )
        comprobar(
            parcela_traida["poligono"] is not None
            and parcela_traida["numero_parcela"] is not None
            and parcela_traida["numero_recinto"] is not None,
            "y con las tres partes de la referencia por separado, como en el papel del SIGPAC",
        )
        comprobar(
            "geometria" not in parcela_traida,
            "y sin mandar el polígono entero al móvil: lo que viaja es la línea que se pinta",
        )
        # El dibujo no puede mentir sobre la forma: se corrige por la latitud, porque un grado de
        # longitud no mide lo mismo que uno de latitud.
        numeros_dibujo = [
            float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", parcela_traida["dibujo"])
        ]
        anchos = numeros_dibujo[0::2]
        altos = numeros_dibujo[1::2]
        comprobar(
            all(0 <= valor <= 100 for valor in numeros_dibujo),
            "y todo el dibujo cae dentro del cuadro, sin recortes",
        )
        comprobar(
            max(anchos) - min(anchos) > 0 and max(altos) - min(altos) > 0,
            "y el dibujo tiene forma de verdad, no un punto",
        )
    else:
        print("     (el SIGPAC no ha contestado: se sigue, que para eso está el aviso)")

    # Y el catálogo oficial de productos ya rellena el volcado, que es lo que faltaba.
    venta_traida = cliente.post(
        "/api/ventas",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-20",
            "producto": "Trigo blando",
            "cantidad": 1000.0,
            "unidad": "kg",
            "comprador": "La cooperativa",
        },
    )
    comprobar(venta_traida.status_code == 201, "se apunta una venta con el nombre del producto")
    paquete_productos = cliente.get("/api/iuws/paquete", headers=cabeceras).json()
    filas_venta = paquete_productos["CUADERNO"][0]["ActividadesExplotacion"]["cosecha_comercializada"]
    fila_con_trigo = [f for f in filas_venta if f.get("c2") == 1]
    comprobar(
        bool(fila_con_trigo),
        "y en el volcado sale el código oficial del producto (1 = TRIGO BLANDO), no el texto",
    )
    comprobar(
        paquete_productos["catalogos_que_faltan"],
        "aunque los catálogos que NO tenemos siguen vacíos y listados aparte",
    )

    print("\n21. Las reglas de abono de la zona de nitratos")
    ayuda_nitratos = cliente.get("/api/ayuda").json()
    reglas = {r["clave"]: r for r in ayuda_nitratos["reglas_nitratos"]}
    comprobar(
        reglas["estiercol_170"]["texto_valor"] == "170 kg N/ha al año",
        "la regla del estiércol dice su número: 170 kg N/ha al año",
    )
    comprobar(
        reglas["pendiente_15"]["texto_valor"] == "15 % de pendiente",
        "y la de la pendiente, el suyo: 15 %",
    )
    comprobar(
        all("MAV/398/2022" in r["fuente"] for r in ayuda_nitratos["reglas_nitratos"]),
        "y cada regla dice de qué Orden sale",
    )
    comprobar(
        ayuda_nitratos["limites_que_faltan"] == []
        and len(ayuda_nitratos["aportes_maximos_n"]) == 22
        and len(ayuda_nitratos["periodos_prohibidos_n"]) == 6
        and reglas["aportes_por_cultivo"]["que_hace_la_app"] == "avisa"
        and reglas["periodos_prohibidos"]["que_hace_la_app"] == "consulta",
        "el Anexo III avisa con datos exactos y el V conserva los periodos como consulta",
    )

    # Una parcela en zona de nitratos, con un purín que se pasa del tope.
    en_zona = cliente.post(
        "/api/parcelas",
        headers=cabeceras,
        json={
            "alias": "La de nitratos",
            "superficie_ha": 2.0,
            "sistema": "secano",
            "municipio": "Peñaranda de Bracamonte",
            "provincia": "Salamanca",
            "zona_vulnerable_nitratos": True,
            "pendiente_pct": 22.0,
        },
    )
    comprobar(en_zona.status_code == 201, "se da de alta una parcela en zona de nitratos")

    cebada = cliente.post(
        f"/api/parcelas/{en_zona.json()['id']}/cultivos",
        headers=cabeceras,
        json={"campana_id": campana["id"], "especie": "Cebada", "sistema": "secano"},
    )
    comprobar(cebada.status_code == 201, "se declara cebada de secano, fila exacta del Anexo III")

    purin = cliente.post(
        "/api/fertilizantes",
        headers=cabeceras,
        json={"nombre": "Purín de cerdo", "tipo": "organico", "riqueza_n": 4.0},
    )
    comprobar(purin.status_code == 201, "y un purín orgánico al 4 % de nitrógeno")

    aviso_nitratos = cliente.post(
        "/api/fertilizaciones/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-02-25",
            "parcela_id": en_zona.json()["id"],
            "superficie_ha": 2.0,
            "fertilizante_id": purin.json()["id"],
            "kg_ha_producto": 5000.0,
        },
    )
    codigos_nitratos = {a["codigo"]: a for a in aviso_nitratos.json()["avisos"]}
    comprobar(
        "N1_estiercol_pasa_tope" in codigos_nitratos,
        "5.000 kg/ha de purín son 200 kg N/ha: pasa de los 170 y avisa",
    )
    comprobar(
        "170" in codigos_nitratos["N1_estiercol_pasa_tope"]["mensaje"]
        and "200" in codigos_nitratos["N1_estiercol_pasa_tope"]["mensaje"],
        "y el aviso dice el tope y lo que llevaría, no solo que algo va mal",
    )
    comprobar(
        codigos_nitratos["N1_estiercol_pasa_tope"]["bloquea"] is False,
        "y no bloquea: el cuaderno tiene que recoger lo que de verdad ha pasado",
    )
    comprobar(
        "N2_pendiente_organico" in codigos_nitratos,
        "y con el 22 % de pendiente avisa de que solo valen los orgánicos sólidos",
    )
    comprobar(
        "F3_zona_nitratos" in codigos_nitratos
        and "170" in codigos_nitratos["F3_zona_nitratos"]["mensaje"],
        "y el aviso de zona de nitratos ya trae el número, no solo «hay reglas más estrictas»",
    )
    comprobar(
        "N3_tabla_cultivo" in codigos_nitratos
        and "105,0" in codigos_nitratos["N3_tabla_cultivo"]["mensaje"]
        and "200,0" in codigos_nitratos["N3_tabla_cultivo"]["mensaje"]
        and codigos_nitratos["N3_tabla_cultivo"]["bloquea"] is False,
        "el Anexo III avisa sin bloquear: cebada secano 105 kg N/ha frente a 200",
    )

    # 22. Los papeles que acompañan al cuaderno.
    #
    # Este apartado se encontró releyendo las instrucciones oficiales: la app de la Junta tiene
    # una sección «Documentación» para «contratos, facturas, albaranes de entrega de envases a
    # Sigfito, etc.», y aquí no existía. Sección nueva, así que se prueba entera.
    print("\n22. Los papeles que acompañan al cuaderno")
    carpeta_humo = Path(os.environ.get("CUEDIGITAL_ADJUNTOS") or (RAIZ / "backend" / "datos" / "adjuntos"))

    papel = cliente.post(
        "/api/documentos",
        headers=cabeceras,
        json={
            "titulo": "Contrato de la finca del río",
            "tipo": "contrato",
            "carpeta": "Contratos",
            "quien": "Los herederos de la finca del río",
            "notas": "Vale hasta 2031",
        },
    )
    comprobar(papel.status_code == 201, "se apunta un papel: el contrato de la finca")
    comprobar(
        papel.json()["tiene_fichero"] is False,
        "y se apunta SIN subir el fichero, que es lo que hace falta para el que no sabe hacer fotos",
    )
    comprobar(
        papel.json()["etiqueta_tipo"] == "Un contrato",
        "y el tipo sale con su nombre en palabras, resuelto en el servidor",
    )

    factura = cliente.post(
        "/api/documentos",
        headers=cabeceras,
        json={
            "titulo": "Factura del abono de mayo",
            "tipo": "factura",
            "carpeta": "Facturas",
            "fecha": "2026-05-20",
        },
    )
    comprobar(factura.status_code == 201, "se apunta una factura, con la fecha del papel")

    subida = cliente.post(
        f"/api/documentos/{papel.json()['id']}/fichero",
        headers=cabeceras,
        files={"fichero": ("contrato.pdf", b"%PDF-1.4 el contrato de verdad", "application/pdf")},
    )
    comprobar(subida.status_code == 200, "se sube el papel en PDF")
    comprobar(
        subida.json()["tiene_fichero"] is True and subida.json()["bytes"] > 0,
        "y queda guardado con su fichero y su tamaño",
    )

    # Las dos cosas que no se pueden permitir: que un fichero raro entre, y que un nombre con
    # «..» escriba fuera de la carpeta.
    raro = cliente.post(
        f"/api/documentos/{papel.json()['id']}/fichero",
        headers=cabeceras,
        files={"fichero": ("virus.exe", b"MZ", "application/x-msdownload")},
    )
    comprobar(raro.status_code == 422, "un fichero ejecutable se rechaza")
    comprobar("PDF" in raro.json()["detail"], "y el mensaje dice qué sí vale, no solo que no")

    escape = cliente.post(
        f"/api/documentos/{factura.json()['id']}/fichero",
        headers=cabeceras,
        files={"fichero": ("../../main.py", b"%PDF-1.4 no soy el programa", "application/pdf")},
    )
    comprobar(escape.status_code == 200, "se admite un nombre raro sin protestar por el nombre")
    escritos = sorted(f.name for f in carpeta_humo.rglob("*") if f.is_file())
    comprobar(
        all(nombre.startswith("documento-") or nombre.startswith("analitica-") for nombre in escritos),
        "pero el nombre del fichero en disco lo decide el programa, no el navegador",
    )
    comprobar(
        not any("main.py" in nombre for nombre in escritos),
        "y un nombre con «..» no ha escrito nada fuera de su carpeta",
    )

    bajado = cliente.get(
        f"/api/documentos/{papel.json()['id']}/fichero", headers=cabeceras
    )
    comprobar(
        bajado.status_code == 200 and bajado.content == b"%PDF-1.4 el contrato de verdad",
        "el papel se descarga igual que se subió",
    )

    listado_papeles = cliente.get("/api/documentos", headers=cabeceras).json()
    comprobar(listado_papeles["cuantos"] == 2, "los dos papeles salen en la lista")
    con_papeles = {c["nombre"] for c in listado_papeles["carpetas"] if c["cuantos"] > 0}
    comprobar(
        con_papeles == {"Contratos", "Facturas"},
        f"agrupados por sus carpetas ({', '.join(sorted(con_papeles))})",
    )
    comprobar(
        any(c["cuantos"] == 0 for c in listado_papeles["carpetas"]),
        "y salen las carpetas sugeridas aunque estén vacías, para saber que se puede archivar ahí",
    )

    texto_papeles = cliente.get("/api/documentos/listado", headers=cabeceras).json()
    comprobar(
        "Contrato de la finca del río" in texto_papeles["texto"]
        and "sin fichero" not in texto_papeles["texto"].split("Contrato de la finca del río")[1][:40],
        "el listado en texto dice qué papeles hay y cuáles tienen fichero",
    )

    anulado = cliente.post(
        f"/api/documentos/{factura.json()['id']}/anular",
        headers=cabeceras,
        json={"motivo": "era un duplicado"},
    )
    comprobar(anulado.status_code == 200, "un papel se puede anular con su motivo")
    comprobar(
        anulado.json()["motivo_anulacion"] == "era un duplicado",
        "y el motivo queda escrito, no se pierde",
    )
    comprobar(
        cliente.get("/api/documentos", headers=cabeceras).json()["cuantos"] == 1,
        "el anulado sale de la lista",
    )
    comprobar(
        cliente.get(
            "/api/documentos", headers=cabeceras, params={"incluir_anulados": True}
        ).json()["cuantos"]
        == 2,
        "pero se puede pedir que salga: la historia no se borra",
    )

    # 23. Lo que tengo en el almacén: el libro de entradas y salidas del producto.
    #
    # Esto se añadió en la ronda 15, leyendo el apartado «Cesta de la compra» de la app oficial,
    # que tiene un botón «Situación Cesta» con «las cantidades adquiridas y gastadas». Aquí los
    # campos de la compra estaban en la base de datos y **no los leía ninguna pantalla**.
    print("\n23. Lo que tengo en el almacén")
    la_grande = cliente.post(
        "/api/parcelas",
        headers=cabeceras,
        json={
            "alias": "La Grande",
            "superficie_ha": 10.0,
            "sistema": "secano",
            "municipio": "Peñaranda de Bracamonte",
            "provincia": "Salamanca",
        },
    )
    comprobar(la_grande.status_code == 201, "se da de alta una parcela de 10 hectáreas")

    con_compra = cliente.post(
        "/api/productos",
        headers=cabeceras,
        json={
            "nombre_comercial": "Cipermetrina 10 %",
            "numero_registro": "24.500",
            "materia_activa": "Cipermetrina",
            "dosis_maxima": 2.0,
            "unidad_dosis": "L/ha",
            "plazo_seguridad_dias": 14,
            "cantidad_comprada": 20.0,
            "unidad_compra": "L",
            "fecha_compra": "2026-03-10",
            "proveedor": "Cooperativa de Peñaranda",
        },
    )
    comprobar(con_compra.status_code == 201, "se apunta un producto CON cuánto se compró")
    comprobar(
        con_compra.json()["cantidad_comprada"] == 20.0,
        "y la cantidad se devuelve: antes se guardaba y no salía en la respuesta",
    )

    echado = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-05",
            "parcela_id": la_grande.json()["id"],
            "superficie_tratada_ha": 10.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": con_compra.json()["id"],
            "dosis": 1.5,
        },
    )
    comprobar(echado.status_code == 201, "se apunta un tratamiento de 1,5 L/ha en 10 ha")

    almacen = cliente.get("/api/productos/cesta/situacion", headers=cabeceras).json()
    comprobar(almacen["cuantos"] >= 1, "la situación del almacén responde")
    fila_almacen = [
        fila for fila in almacen["productos"] if fila["producto_id"] == con_compra.json()["id"]
    ][0]
    comprobar(fila_almacen["comprado"] == 20.0, "dice cuánto se compró (20 L)")
    comprobar(
        fila_almacen["gastado"] == 15.0,
        f"y cuánto se ha echado: 1,5 L/ha por 10 ha son 15 L ({fila_almacen['gastado']})",
    )
    comprobar(
        fila_almacen["queda"] == 5.0,
        f"y lo que queda, que es la pregunta de verdad ({fila_almacen['queda']} L)",
    )
    comprobar(
        fila_almacen["fecha_compra"] == "2026-03-10"
        and fila_almacen["proveedor"] == "Cooperativa de Peñaranda",
        "con la fecha y el proveedor, que son los datos del libro de movimientos",
    )

    # Y lo que el programa NO hace: restar un litro de un kilo. Un producto comprado en kilos
    # pero echado con dosis en litros no se puede comparar sin la densidad.
    en_kilos = cliente.post(
        "/api/productos",
        headers=cabeceras,
        json={
            "nombre_comercial": "Azufre mojable",
            "numero_registro": "24.501",
            "dosis_maxima": 3.0,
            "unidad_dosis": "L/ha",
            "plazo_seguridad_dias": 10,
            "cantidad_comprada": 25.0,
            "unidad_compra": "kg",
        },
    )
    cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-06",
            "parcela_id": la_grande.json()["id"],
            "superficie_tratada_ha": 10.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": en_kilos.json()["id"],
            "dosis": 1.0,
        },
    )
    almacen2 = cliente.get("/api/productos/cesta/situacion", headers=cabeceras).json()
    fila_kilos = [
        fila for fila in almacen2["productos"] if fila["producto_id"] == en_kilos.json()["id"]
    ][0]
    comprobar(
        fila_kilos["se_puede_comparar"] is False and fila_kilos["queda"] is None,
        "un producto comprado en kilos y echado en litros NO da una resta inventada",
    )
    comprobar(
        "kg" in fila_kilos["motivo"] and "L" in fila_kilos["motivo"],
        "y dice por qué no se puede, con las dos unidades delante",
    )
    comprobar(
        almacen2["sin_poder_comparar"] >= 1,
        "y se puede saber cuántos productos están así, para poder apuntar el dato que falta",
    )

    # 24. Qué hay sembrado en cada parcela.
    #
    # El fallo más raro de todos los que han salido: el cuaderno **ya le decía al agricultor**
    # «a El Prado le falta decir qué cultivo tiene este año» y no había ninguna forma de
    # contestarle. La tabla estaba en la base de datos, con su endpoint, y no la usaba ninguna
    # pantalla. Y de paso: el «Cultivo» de todos los tratamientos salía vacío, y el aviso de
    # «en esa fecha no había cultivo» no podía saltar nunca.
    print("\n24. Qué hay sembrado en cada parcela")
    falta_antes = cliente.get("/api/cuaderno/falta", headers=cabeceras).json()
    comprobar(
        any(p["tipo"] == "parcela_sin_cultivo" for p in falta_antes["pendientes"]),
        "el cuaderno avisa de que hay parcelas sin decir qué cultivo tienen",
    )
    cultivos_finca = cliente.get("/api/cultivos", headers=cabeceras).json()
    comprobar(
        cultivos_finca["faltan"] >= 1,
        f"y la pantalla de cultivos dice a cuántas les falta ({cultivos_finca['faltan']})",
    )

    dicho = cliente.post(
        f"/api/parcelas/{parcela.json()['id']}/cultivos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            # Ojo con esto, que es una lección: el catálogo oficial del SIGPAC tiene **una sola**
            # entrada de cebada, «CEBADA» (código 5). «Cebada de dos carreras» es una variedad,
            # no un producto, así que va en `variedad` y no en `especie`. Poniéndolo en la
            # especie, el volcado no encuentra código y lo deja vacío —que es lo correcto—, pero
            # el cuaderno queda peor.
            "especie": "Cebada",
            "variedad": "Dos carreras",
            "sistema": "secano",
            "fecha_inicio": "2025-11-01",
        },
    )
    comprobar(dicho.status_code == 201, "se puede decir qué hay sembrado, que antes no se podía")

    falta_despues = cliente.get("/api/cuaderno/falta", headers=cabeceras).json()
    comprobar(
        not any(
            p["tipo"] == "parcela_sin_cultivo" and p.get("parcela_id") == parcela.json()["id"]
            for p in falta_despues["pendientes"]
        ),
        "y el aviso de «le falta el cultivo» desaparece al decirlo",
    )

    con_cultivo = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": FECHA_DEL_CULTIVO,
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 2.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.5,
        },
    )
    comprobar(
        con_cultivo.status_code == 201 and con_cultivo.json()["cultivo"] == "Cebada",
        "un tratamiento nuevo ya trae el cultivo solo, sin preguntarlo otra vez",
    )

    paquete_cultivo = cliente.get("/api/iuws/paquete", headers=cabeceras).json()
    # La fila se busca **por su fecha**, no por ser la última: así se comprueba la que se acaba
    # de crear y no otra cualquiera del cuaderno.
    filas_del_dia = [
        fila
        for fila in paquete_cultivo["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"]
        if str(fila["c1"]) == FECHA_DEL_CULTIVO
    ]
    comprobar(
        bool(filas_del_dia) and filas_del_dia[-1]["c6"] == 5,
        "y el volcado lleva el CÓDIGO oficial del cultivo (5 = CEBADA), no el texto",
    )
    comprobar(
        bool(filas_del_dia) and filas_del_dia[-1]["c6_catalogo"] is True,
        "marcado como que viene del catálogo de productos del FEGA",
    )

    # Y el aviso que no podía saltar nunca, porque dependía de este dato.
    fuera_de_fecha = cliente.post(
        "/api/tratamientos/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": FECHA_DEL_CULTIVO,
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 2.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.5,
        },
    ).json()
    comprobar(
        "V5_fecha_fuera_de_cultivo" not in {a["codigo"] for a in fuera_de_fecha["avisos"]},
        "dentro del periodo declarado del cultivo, el aviso de la fecha no salta",
    )

    # 25. Las parcelas que se llevan igual: apuntar una vez lo que se hace en seis.
    #
    # Tercera vez que aparece el mismo fallo, y por eso se prueba entero: `GrupoParcelas` estaba
    # en la base de datos con tres endpoints y **ninguna pantalla los llamaba** (`grupo_id` no
    # aparecía ni una vez en el JavaScript). Y de paso se cerró un agujero de verdad: la
    # comprobación de la superficie **no se hacía** cuando el apunte era de un grupo.
    print("\n25. Las parcelas que se llevan igual")
    # Se declara el mismo cultivo en la parcela del cultivo y en la de nitratos, para que se
    # puedan juntar: hace falta mismo cultivo, mismo sistema y estar cerca.
    for otra in (parcela.json()["id"], en_zona.json()["id"]):
        cliente.post(
            f"/api/parcelas/{otra}/cultivos",
            headers=cabeceras,
            json={
                "campana_id": campana["id"],
                "especie": "Cebada",
                "sistema": "secano",
            },
        )

    calculado = cliente.post("/api/grupos/calcular", headers=cabeceras).json()
    comprobar(
        calculado["grupos_creados"] >= 1,
        f"el botón de juntarlas solo junta las que se llevan igual ({calculado['grupos_creados']})",
    )
    comprobar(
        calculado["campana_id"] == campana["id"],
        "y se coge la campaña del año en curso si no se le dice otra cosa",
    )

    grupos = cliente.get("/api/grupos", headers=cabeceras).json()
    comprobar(bool(grupos), "los grupos salen en la lista")
    grupo = grupos[0]
    comprobar(
        len(grupo["parcela_ids"]) >= 2 and grupo["superficie_total_ha"] > 0,
        f"con sus parcelas y la superficie sumada ({grupo['superficie_total_ha']} ha)",
    )

    en_grupo = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-25",
            "grupo_id": grupo["id"],
            "superficie_tratada_ha": grupo["superficie_total_ha"],
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.5,
        },
    )
    comprobar(
        en_grupo.status_code == 201,
        "se apunta un tratamiento para TODAS las parcelas del grupo de una vez",
    )
    comprobar(
        en_grupo.json()["grupo_id"] == grupo["id"] and en_grupo.json()["parcela_id"] is None,
        "y queda apuntado el grupo, no una parcela suelta",
    )

    # El agujero: antes esto pasaba sin que nadie dijera nada.
    se_pasa = cliente.post(
        "/api/tratamientos/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-25",
            "grupo_id": grupo["id"],
            "superficie_tratada_ha": grupo["superficie_total_ha"] + 50,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.5,
        },
    ).json()
    comprobar(
        "V4_superficie_excedida_grupo" in {a["codigo"] for a in se_pasa["avisos"]},
        "y tratar más hectáreas que tiene el grupo SÍ se comprueba (antes no se miraba)",
    )

    # 26. Cómo se echó el producto.
    #
    # Once campos del registro de tratamientos no llegaban a ninguna pantalla: se guardaban y ahí
    # se quedaban. Dos los pide el contenido mínimo por su número (la hora, campo 3, y el estado
    # de la planta, campo 8), y el aviso de «¿has dejado la orilla sin tratar?» **saltaba
    # siempre** porque la pregunta no existía.
    print("\n26. Cómo se echó el producto")
    del_dia = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-28",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 1.5,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.5,
            "hora_inicio": "07:30",
            "hora_fin": "10:15",
            "estado_cultivo": "Espigando",
            "temperatura_c": 18.5,
            "humedad_pct": 65.0,
            "viento_kmh": 12.0,
            "viento_direccion": "Norte",
            "volumen_caldo_l_ha": 250.0,
            "operadores_expuestos": 2,
            "incidencias": "Se atascó una boquilla",
        },
    )
    comprobar(del_dia.status_code == 201, "se apunta cómo se echó: hora, planta y día")
    comprobar(
        del_dia.json()["hora_inicio"] == "07:30" and del_dia.json()["viento_kmh"] == 12.0,
        "y los datos vuelven en la respuesta, que antes se guardaban y no salían",
    )

    paquete_del_dia = cliente.get("/api/iuws/paquete", headers=cabeceras).json()
    filas_del_dia = [
        fila
        for fila in paquete_del_dia["CUADERNO"][0]["ActividadesExplotacion"]["tratamientos"]
        if str(fila["c1"]) == "2026-05-28"
    ]
    comprobar(
        bool(filas_del_dia) and filas_del_dia[-1]["c3"] == "07:30",
        "y la hora llega al volcado en el campo 3, que estaba declarado y nunca se podía llenar",
    )
    comprobar(
        bool(filas_del_dia) and filas_del_dia[-1]["c8"] is None and filas_del_dia[-1]["c8_catalogo"] is True,
        "y el estado de la planta (campo 8) ya está declarado: vacío y marcado, que es de catálogo",
    )

    # El aviso que saltaba siempre: con agua al lado, la pregunta no existía en ninguna pantalla.
    del_rio = cliente.post(
        "/api/parcelas",
        headers=cabeceras,
        json={
            "alias": "La del río",
            "superficie_ha": 1.0,
            "sistema": "secano",
            "masa_agua_cerca": True,
        },
    )
    comprobar(del_rio.status_code == 201, "se da de alta una parcela con agua al lado")

    def _avisos_de_la_orilla(contestar):
        cuerpo = {
            "campana_id": campana["id"],
            "fecha": "2026-05-28",
            "parcela_id": del_rio.json()["id"],
            "superficie_tratada_ha": 1.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.5,
        }
        if contestar is not None:
            cuerpo["franja_seguridad_respetada"] = contestar
        respuesta = cliente.post("/api/tratamientos/validar", headers=cabeceras, json=cuerpo)
        return {a["codigo"] for a in respuesta.json()["avisos"]}

    comprobar(
        "V11_franja_seguridad" in _avisos_de_la_orilla(None),
        "sin contestar, avisa de la orilla junto al agua",
    )
    comprobar(
        "V11_franja_seguridad" not in _avisos_de_la_orilla(True),
        "y al contestar que sí se dejó, el aviso desaparece: antes no había forma de quitarlo",
    )

    # 26 bis. Dos campos que se añadieron al mapear el cuaderno al formato de la Junta.
    #
    # El interfaz los exige como **obligatorios** (`AplicacionManual` y `Eficacia`) y el cuaderno
    # no los preguntaba en ninguna pantalla: otra vez el mismo fallo de siempre, el dato escrito y
    # sin puerta. Aquí se comprueba que se guardan, que se devuelven y que llegan al documento que
    # se firma, que es donde tienen que estar.
    con_lo_nuevo = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-05-29",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 1.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": producto.json()["id"],
            "dosis": 0.5,
            "aplicado_a_mano": True,
            "eficacia": "regular",
        },
    )
    comprobar(con_lo_nuevo.status_code == 201, "se apunta si se echó a mano y cómo funcionó")
    comprobar(
        con_lo_nuevo.json().get("aplicado_a_mano") is True,
        "y el cuaderno lo devuelve en vez de perderlo",
    )
    comprobar(con_lo_nuevo.json().get("eficacia") == "regular", "y lo mismo con la eficacia")
    texto_firmado = cliente.get("/api/firmas/fichero", headers=cabeceras_firma).text
    comprobar(
        "Se aplicó a mano" in texto_firmado,
        "y las dos cosas salen en el documento que se firma",
    )

    # 27. La autorización del producto: tres comprobaciones que no podían saltar.
    #
    # Tercera vez en cuatro rondas que aparece el mismo fallo, y esta vez eran tres de golpe. El
    # programa ya tenía escrito y probado que un producto retirado no se puede usar, que uno que
    # no vale para ecológico no se puede echar en una finca ecológica, y que una autorización
    # excepcional caducada bloquea. Las tres dependían de datos que **no se podían meter desde
    # ninguna pantalla**, así que decían «adelante» en los tres casos.
    print("\n27. La autorización del producto")
    retirado = cliente.post(
        "/api/productos",
        headers=cabeceras,
        json={
            "nombre_comercial": "Producto retirado",
            "numero_registro": "24.900",
            "dosis_maxima": 2.0,
            "unidad_dosis": "L/ha",
            "plazo_seguridad_dias": 14,
            "autorizado": False,
        },
    )
    comprobar(
        retirado.status_code == 201 and retirado.json()["autorizado"] is False,
        "se puede decir que un producto ya no está autorizado",
    )
    intento_retirado = cliente.post(
        "/api/tratamientos",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-06-01",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 1.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": retirado.json()["id"],
            "dosis": 0.5,
        },
    )
    comprobar(
        intento_retirado.status_code == 422
        and any(
            a["codigo"] == "V1_no_autorizado"
            for a in intento_retirado.json()["detail"]["avisos"]
        ),
        "y usarlo BLOQUEA, que es lo que decía el código y no podía pasar nunca",
    )

    con_permiso = cliente.post(
        "/api/productos",
        headers=cabeceras,
        json={
            "nombre_comercial": "Con permiso especial",
            "numero_registro": "24.901",
            "dosis_maxima": 2.0,
            "unidad_dosis": "L/ha",
            "plazo_seguridad_dias": 14,
            "autorizacion_excepcional": "AUT-2026-0417",
            "autorizacion_hasta": "2026-06-15",
        },
    )
    comprobar(
        con_permiso.status_code == 201
        and con_permiso.json()["autorizacion_hasta"] == "2026-06-15",
        "se puede apuntar un permiso especial y hasta cuándo vale",
    )

    dentro = cliente.post(
        "/api/tratamientos/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-06-01",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 1.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": con_permiso.json()["id"],
            "dosis": 0.5,
        },
    ).json()
    comprobar(
        "V1_autorizacion_caducada" not in {a["codigo"] for a in dentro["avisos"]},
        "dentro del plazo del permiso, el tratamiento se puede apuntar",
    )

    fuera = cliente.post(
        "/api/tratamientos/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-07-01",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 1.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": con_permiso.json()["id"],
            "dosis": 0.5,
        },
    ).json()
    aviso_caducado = [a for a in fuera["avisos"] if a["codigo"] == "V1_autorizacion_caducada"]
    comprobar(
        bool(aviso_caducado) and "15/06/2026" in aviso_caducado[0]["mensaje"],
        "y pasado el plazo BLOQUEA diciendo la fecha, que antes no se podía ni saber",
    )

    # Y en ecológico: un producto que no vale, en una finca ecológica.
    cliente.put("/api/mi-finca", headers=cabeceras, json={"produccion_ecologica": True})
    no_ecologico = cliente.post(
        "/api/productos",
        headers=cabeceras,
        json={
            "nombre_comercial": "No vale para ecológico",
            "numero_registro": "24.902",
            "dosis_maxima": 2.0,
            "unidad_dosis": "L/ha",
            "plazo_seguridad_dias": 14,
            "permitido_ecologico": False,
        },
    )
    intento_eco = cliente.post(
        "/api/tratamientos/validar",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "fecha": "2026-06-01",
            "parcela_id": parcela.json()["id"],
            "superficie_tratada_ha": 1.0,
            "justificacion": "Vi la plaga o la hierba en el campo",
            "producto_id": no_ecologico.json()["id"],
            "dosis": 0.5,
        },
    ).json()
    comprobar(
        "V15_no_ecologico" in {a["codigo"] for a in intento_eco["avisos"]},
        "y en una finca ecológica, un producto que no vale BLOQUEA (tampoco podía pasar antes)",
    )
    cliente.put("/api/mi-finca", headers=cabeceras, json={"produccion_ecologica": False})

    # El tipo de carné es una **lista cerrada**: en la hoja 1.2 del cuaderno de la Junta esa casilla
    # se marca con una cruz en una de las cuatro columnas (básico, cualificado, fumigador y piloto),
    # así que un texto libre no se podría pasar al papel. Se guarda la clave en minúscula y se
    # rechaza lo que no esté en la lista, con la lista delante para que se sepa qué poner.
    tipo_carne = cliente.post(
        "/api/aplicadores",
        headers=cabeceras,
        json={
            "nombre": "Aplicador con carné",
            "numero_carne": "C-999111",
            "tipo_carne": "cualificado",
            "numero_reganip": "REGANIP-2026-12",
        },
    )
    comprobar(
        tipo_carne.status_code == 201
        and tipo_carne.json()["tipo_carne"] == "cualificado"
        and tipo_carne.json()["numero_reganip"] == "REGANIP-2026-12",
        "y el aplicador puede decir el tipo de carné y su número de registro de equipos",
    )

    carne_inventado = cliente.post(
        "/api/aplicadores",
        headers=cabeceras,
        json={"nombre": "Aplicador sin carné de verdad", "tipo_carne": "nivel 2 de la vieja"},
    )
    comprobar(
        carne_inventado.status_code == 422
        and "cualificado" in carne_inventado.text.lower()
        and "fumigador" in carne_inventado.text.lower(),
        "y un tipo de carné que no existe se rechaza diciendo cuáles hay (la hoja 1.2 cruza una de las cuatro)",
    )

    print("\n28. Traer las tierras del cuaderno de la Junta (el Cuecyl)")
    # El cuaderno se fabrica aquí con datos inventados (el mismo ejemplo que usan los tests): los
    # cuadernos de verdad llevan el nombre, el NIF y las tierras de una persona, y eso no entra en
    # el repositorio ni en una prueba.
    from hacer_cuaderno_de_ejemplo import construye  # noqa: E402  (está en esta misma carpeta)

    cuaderno_de_ejemplo = construye()

    estado_cuaderno = cliente.get("/api/cuaderno-cyl/estado")
    comprobar(
        estado_cuaderno.status_code == 200
        and "particulares.ayg.jcyl.es" in estado_cuaderno.json()["de_donde"],
        "se dice de dónde se descarga el cuaderno (la aplicación de la Junta)",
    )

    leido = cliente.post(
        "/api/cuaderno-cyl/leer",
        headers=cabeceras,
        files={"fichero": ("CuadernoExplotacion_070922320A.xlsx", cuaderno_de_ejemplo)},
    )
    comprobar(leido.status_code == 200, f"el cuaderno se lee ({leido.status_code})")
    resumen = leido.json()["resumen"]
    comprobar(resumen["anio"] == 2026, f"se lee la campaña del cuaderno ({resumen['anio']})")
    comprobar(resumen["lineas"] == 8, f"se cuentan las líneas del papel ({resumen['lineas']})")
    comprobar(resumen["lineas_ilegibles"] == 1, "y se cuenta la línea que no se puede apuntar")
    comprobar(resumen["tierras"] == 5, f"y las tierras distintas ({resumen['tierras']})")
    comprobar(
        resumen["tierras_partidas"] == 1,
        "se ve que una tierra está partida en trozos en el papel",
    )
    comprobar(
        resumen["hectareas_declaradas"] == 14.52,
        f"se suman las hectáreas declaradas ({resumen['hectareas_declaradas']})",
    )
    comprobar(
        leido.json()["titular"] == "EXPLOTACIÓN DE EJEMPLO",
        "se leen los datos del titular de la portada",
    )

    cuantas_antes = len(cliente.get("/api/parcelas", headers=cabeceras).json())
    traido = cliente.post(
        "/api/cuaderno-cyl/importar",
        headers=cabeceras,
        files={"fichero": ("CuadernoExplotacion_070922320A.xlsx", cuaderno_de_ejemplo)},
    )
    comprobar(traido.status_code == 200, f"las tierras se traen ({traido.status_code})")
    datos = traido.json()
    comprobar(datos["creadas"] == 7, f"se apuntan las tierras del cuaderno ({datos['creadas']})")
    comprobar(datos["sin_apuntar"] == 1, "y se dice la línea que no se ha podido apuntar")
    despues = cliente.get("/api/parcelas", headers=cabeceras).json()
    comprobar(len(despues) == cuantas_antes + 7, "y aparecen en la lista de parcelas")

    la_del_cuaderno = next(p for p in despues if p["ref_sigpac"] == "99-99-0-0-1-1-1")
    comprobar(
        la_del_cuaderno["municipio"] == "PUEBLO DE EJEMPLO" and la_del_cuaderno["uso_sigpac"] == "TA",
        "cada tierra trae su pueblo y su uso del papel",
    )
    comprobar(
        la_del_cuaderno["zona_vulnerable_nitratos"] is True,
        "y la casilla de zona de nitratos, que en el papel venía marcada",
    )
    cultivo = cliente.get(
        f"/api/parcelas/{la_del_cuaderno['id']}/cultivos", headers=cabeceras
    ).json()
    comprobar(
        len(cultivo) == 1
        and cultivo[0]["especie"] == "CEBADA"
        and cultivo[0]["ecorregimen"] == "P3",
        "y su cultivo con el ecorregimen del cuaderno",
    )
    trozos = [p for p in despues if p["ref_sigpac"] == "99-99-0-0-1-5-1"]
    comprobar(len(trozos) == 3, "la tierra partida en el papel se apunta en sus tres trozos")
    comprobar(
        sorted(p["superficie_ha"] for p in trozos) == [0.13, 0.46, 4.44]
        and {p["superficie_sigpac_ha"] for p in trozos} == {5.07},
        "cada trozo con lo que se cultiva, y la superficie del recinto guardada aparte",
    )

    repetido = cliente.post(
        "/api/cuaderno-cyl/importar",
        headers=cabeceras,
        files={"fichero": ("CuadernoExplotacion_070922320A.xlsx", cuaderno_de_ejemplo)},
    ).json()
    comprobar(
        repetido["creadas"] == 0 and repetido["ya_estaban"] == 7,
        "subirlo otra vez no duplica ni una tierra",
    )
    comprobar(
        len(cliente.get("/api/parcelas", headers=cabeceras).json()) == len(despues),
        "y la lista de parcelas sigue teniendo las mismas",
    )

    finca = cliente.get("/api/mi-finca", headers=cabeceras).json()
    comprobar(
        finca["registro_autonomico"] == "9999999999"
        and finca["direccion"] == "CALLE DEL EJEMPLO, 1",
        "los datos del titular del cuaderno se rellenan donde estaban vacíos",
    )

    print("\n29. Las facturas: subirlas, que el programa las lea y confirmarlas")
    factura = _factura_de_ejemplo()

    estado_facturas = cliente.get("/api/facturas/estado", headers=cabeceras)
    comprobar(estado_facturas.status_code == 200, "se puede preguntar si se leen las fotos")
    comprobar(
        "hay_lector" in estado_facturas.json()["lector"],
        "y se dice si hay lector de fotos y con qué idioma",
    )

    producto = cliente.post(
        "/api/productos",
        headers=cabeceras,
        json={
            "nombre_comercial": "Glifosato 36 SL",
            "numero_registro": "24.123",
            "dosis_maxima": 4,
            "unidad_dosis": "L/ha",
            "unidad_compra": "L",
        },
    ).json()

    leida = cliente.post(
        "/api/facturas/leer",
        headers=cabeceras,
        files={"fichero": ("factura.pdf", factura, "application/pdf")},
    )
    comprobar(leida.status_code == 200, f"la factura se lee ({leida.status_code})")
    datos = leida.json()
    comprobar(
        datos["proveedor"].startswith("COOPERATIVA"),
        f"se lee quién la manda ({datos['proveedor'][:30]})",
    )
    comprobar(datos["proveedor_nif"] == "F37012345", "y su NIF, que no es el del agricultor")
    comprobar(
        datos["numero_factura"] == "2026/00123" and datos["fecha"] == "2026-03-15",
        "y el número y la fecha",
    )
    comprobar(
        datos["base_imponible"] == 620.0 and datos["cuota_iva"] == 130.2 and datos["total"] == 750.2,
        "y la base, el IVA y el total",
    )
    comprobar(
        datos["resumen"]["lineas"] == 2 and datos["resumen"]["lineas_que_cuadran"] == 2,
        "y las líneas, con la cuenta de cada una comprobada (cantidad × precio = importe)",
    )
    comprobar(
        datos["lineas"][0]["producto_sugerido"] == "Glifosato 36 SL",
        "y se reconoce el producto de su cesta en la primera línea",
    )

    guardada = cliente.post(
        "/api/facturas",
        headers=cabeceras,
        data={
            "datos": json.dumps(
                {
                    "fecha": "2026-03-15",
                    "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
                    "proveedor_nif": "F37012345",
                    "numero_factura": "2026/00123",
                    "base_imponible": 620.0,
                    "cuota_iva": 130.2,
                    "tipo_iva_pct": 21.0,
                    "total": 750.2,
                    "leida_por": "pdf",
                    "lineas": [
                        {
                            "descripcion": "GLIFOSATO 36% SL 20 L",
                            "cantidad": 40,
                            "unidad": "L",
                            "precio_unitario": 4.25,
                            "importe": 170.0,
                            "producto_id": producto["id"],
                        },
                        {
                            "descripcion": "NITRATO AMONICO 33,5%",
                            "cantidad": 1000,
                            "unidad": "kg",
                            "precio_unitario": 0.45,
                            "importe": 450.0,
                        },
                    ],
                }
            )
        },
        files={"fichero": ("factura.pdf", factura, "application/pdf")},
    )
    comprobar(guardada.status_code == 201, f"la factura se guarda ({guardada.status_code})")
    comprobar(
        guardada.json()["tiene_fichero"] is True,
        "y se queda la foto o el PDF como justificante",
    )
    descargada = cliente.get(f"/api/facturas/{guardada.json()['id']}/fichero", headers=cabeceras)
    comprobar(
        descargada.status_code == 200 and descargada.content[:4] == b"%PDF",
        "y el justificante se puede volver a ver",
    )

    cesta = cliente.get("/api/productos/cesta/situacion", headers=cabeceras).json()
    fila = next(p for p in cesta["productos"] if p["producto_id"] == producto["id"])
    comprobar(
        fila["comprado"] == 40.0 and fila["comprado_de_donde"] == "facturas",
        "lo comprado sale de la factura, no de lo que se escribió a mano",
    )
    comprobar(
        fila["compras"][0]["numero_factura"] == "2026/00123",
        "y se dice de qué factura sale cada compra",
    )

    otra_vez = cliente.post(
        "/api/facturas/leer",
        headers=cabeceras,
        files={"fichero": ("factura.pdf", factura, "application/pdf")},
    ).json()
    comprobar(
        otra_vez["ya_estaba"] == guardada.json()["id"],
        "subir la misma factura otra vez se avisa, para no contarla dos veces",
    )

    anulada = cliente.post(
        f"/api/facturas/{guardada.json()['id']}/anular",
        headers=cabeceras,
        json={"motivo": "Era un albarán"},
    )
    comprobar(
        anulada.status_code == 200 and anulada.json()["anulada"] is True,
        "una factura se puede anular con su motivo",
    )
    cesta = cliente.get("/api/productos/cesta/situacion", headers=cabeceras).json()
    fila = next(p for p in cesta["productos"] if p["producto_id"] == producto["id"])
    comprobar(
        fila["comprado"] is None,
        "y una factura anulada deja de contar en el almacén",
    )

    print("\n30. El cuaderno de la Junta relleno, y lo que le falta")
    hojas = cliente.get("/api/cuaderno-cyl/hojas", headers=cabeceras)
    comprobar(
        hojas.status_code == 200 and len(hojas.json()["hojas"]) == 25,
        "el cuaderno tiene las 25 hojas del cuaderno oficial",
    )
    comprobar(
        any(hoja["titulo"] == "Las parcelas" for hoja in hojas.json()["hojas"]),
        "y cada hoja dice qué es",
    )

    exportado = cliente.get("/api/cuaderno-cyl/exportar", headers=cabeceras)
    comprobar(
        exportado.status_code == 200 and exportado.content[:2] == b"PK",
        f"el cuaderno se saca relleno ({exportado.status_code})",
    )
    comprobar(
        "CuadernoExplotacion_70922320A" in exportado.headers.get("content-disposition", ""),
        "con el nombre que le pone la Junta",
    )
    libro = _abrir_el_cuaderno(exportado.content)
    comprobar(len(libro.sheetnames) == 25, "y con sus 25 hojas")
    comprobar(
        libro["1.1. INF. GRAL"]["G7"].value == "David Pérez Velasco",
        "la portada lleva el titular",
    )
    comprobar(
        libro["2.1. DATOS PARCELAS"]["Q2"].value == 2026,
        "la hoja de parcelas dice de qué año es",
    )
    comprobar(
        libro["6. REG. FERTILIZ"]["G11"].value == "A-2026-88"
        or libro["6. REG. FERTILIZ"]["G11"].value in (None, ""),
        "y el abonado sale con el nº de albarán si se ha apuntado",
    )

    falta = cliente.get("/api/cuaderno-cyl/que-falta", headers=cabeceras).json()
    comprobar(
        falta["hojas"] == 25 and "hojas_con_datos" in falta,
        "se dice cuántas hojas llevan datos",
    )
    comprobar(
        isinstance(falta["faltan"], list) and all(f["donde_se_pone"] for f in falta["faltan"]),
        "y cada cosa que falta dice dónde se apunta",
    )
    # Las hojas que el programa todavía no escribe solas tienen que salir en el informe **con la
    # dirección oficial** donde se terminan a mano: si no, el agricultor entrega un cuaderno con
    # quince hojas en blanco y no sabe ni dónde ni cómo completarlas.
    comprobar(
        any(
            f["hoja"] == "3.2. REG. USO SEMILLA TRAT." and "particulares.ayg.jcyl.es" in f["donde_se_pone"]
            for f in falta["faltan"]
        ),
        "y las hojas que no se escriben solas dicen dónde se terminan (con la dirección de la Junta)",
    )
    comprobar(
        any("máquina" in f["que_falta"] for f in falta["faltan"]),
        "y avisa de las máquinas que faltan por apuntar",
    )

    print("\n31. Corregir y borrar lo que uno ha introducido")
    # Ronda 91. Lo que se comprueba es lo que de verdad pidió el dueño del proyecto («dejar borrar las
    # cosas que introduzca porque puede que me equivoque, o modificar también») y, sobre todo, que las
    # dos cosas **dejen rastro**: el cuaderno no enseña lo borrado y el programa sí sabe que estuvo.
    #
    # **Y se manda de vuelta lo que devuelve la API**, que es exactamente lo que hace el formulario al
    # corregir (se rellena con el apunte guardado). Eso vale de dos cosas: comprueba la corrección y
    # comprueba que un apunte se puede volver a mandar tal cual —lo que se rompe en cuanto la salida y
    # la entrada de la API se separan—.
    apuntes = [a for a in cliente.get("/api/tratamientos", headers=cabeceras).json() if a["parcela_id"]]
    if not apuntes:
        comprobar(False, "no hay ningún tratamiento de una tierra con el que probar la corrección")
    else:
        apunte = apuntes[0]
        ident = apunte["id"]
        carga = {
            "campana_id": apunte["campana_id"],
            "fecha": apunte["fecha"],
            "tipo": apunte["tipo"],
            "parcela_id": apunte["parcela_id"],
            "superficie_tratada_ha": apunte["superficie_tratada_ha"],
            "justificacion": "Me había equivocado de dosis",
            "producto_id": apunte["producto_id"],
            "dosis": 0.5,
            "unidad_dosis": apunte["unidad_dosis"],
        }
        corregido = cliente.put(f"/api/tratamientos/{ident}", headers=cabeceras, json=carga)
        comprobar(
            corregido.status_code == 200,
            f"un apunte se puede corregir ({corregido.status_code}: {corregido.text[:120]})",
        )
        if corregido.status_code == 200:
            comprobar(corregido.json()["id"] == ident, "y sigue siendo el mismo apunte, no otro")
            comprobar(
                abs(corregido.json()["cantidad_total"] - 0.5 * float(carga["superficie_tratada_ha"]))
                < 0.01,
                "y los números que calcula el programa se vuelven a calcular",
            )
            comprobar(
                corregido.json()["justificacion"] == "Me había equivocado de dosis",
                "y lo que había antes queda en el historial del cuaderno",
            )

        # Y ahora uno de prueba que se borra, para no dejar la finca de la prueba sin apuntes.
        de_prueba = cliente.post(
            "/api/tratamientos",
            headers=cabeceras,
            json={**carga, "justificacion": "Esto lo apunté por error"},
        )
        comprobar(
            de_prueba.status_code == 201,
            f"se puede apuntar uno de prueba para borrarlo ({de_prueba.status_code})",
        )
        ident_de_prueba = de_prueba.json()["id"] if de_prueba.status_code == 201 else None
        if ident_de_prueba:
            cuantos_antes = len(cliente.get("/api/tratamientos", headers=cabeceras).json())
            borrado = cliente.delete(f"/api/tratamientos/{ident_de_prueba}", headers=cabeceras)
            comprobar(borrado.status_code == 200, f"un apunte se puede borrar ({borrado.status_code})")
            comprobar(
                len(cliente.get("/api/tratamientos", headers=cabeceras).json()) == cuantos_antes - 1,
                "y desaparece de la lista del cuaderno",
            )
            comprobar(
                cliente.get(f"/api/tratamientos/{ident_de_prueba}", headers=cabeceras).status_code
                == 404,
                "y ya no se puede ni mirar",
            )
            comprobar(
                cliente.delete(f"/api/tratamientos/{ident_de_prueba}", headers=cabeceras).status_code
                == 404,
                "y borrarlo otra vez no rompe nada",
            )

        # Los cuatro tipos de apunte se anulan por su ruta. Las labores **no tenían ninguna** hasta la
        # ronda 91, y el aviso de «este apunte está firmado» manda a anular: sin esta ruta, el mensaje
        # dejaba al agricultor sin salida.
        labor = cliente.post(
            "/api/labores",
            headers=cabeceras,
            json={
                "campana_id": apunte["campana_id"],
                "tipo": "laboreo",
                "fecha": apunte["fecha"],
                "parcela_id": apunte["parcela_id"],
                "superficie_ha": apunte["superficie_tratada_ha"],
            },
        )
        comprobar(labor.status_code == 201, f"se puede apuntar un trabajo ({labor.status_code})")
        if labor.status_code == 201:
            anulada = cliente.post(
                f"/api/labores/{labor.json()['id']}/anular",
                headers=cabeceras,
                json={"motivo": "Me he equivocado"},
            )
            comprobar(anulada.status_code == 200, "y un trabajo también se puede anular")

    print("\n32. Corregir y borrar las tierras y los grupos")
    # Ronda 92: lo mismo que el apartado 31, pero con lo que el agricultor dio de alta él. Y con dos
    # comprobaciones que solo se pueden hacer aquí, contra el servidor de verdad:
    #   · que **corregir una tierra no le quita los cultivos que tenga declarados** ni la referencia;
    #   · que **una tierra con apuntes no se deja borrar** y el motivo dice qué hacer (borrar una tierra
    #     con el cuaderno lleno de apuntes destruiría el registro en silencio).
    tierras = cliente.get("/api/parcelas", headers=cabeceras).json()
    if not tierras:
        comprobar(False, "no hay ninguna tierra con la que probar la corrección")
    else:
        tierra = tierras[0]
        corregida = cliente.put(
            f"/api/parcelas/{tierra['id']}",
            headers=cabeceras,
            json={
                "alias": "El Prado de arriba",
                "ref_sigpac": tierra["ref_sigpac"],
                "superficie_ha": tierra["superficie_ha"],
                "sistema": tierra["sistema"],
                "municipio": tierra["municipio"],
                "provincia": tierra["provincia"],
                "uso_sigpac": tierra["uso_sigpac"],
            },
        )
        comprobar(
            corregida.status_code == 200,
            f"una tierra se puede corregir ({corregida.status_code}: {corregida.text[:120]})",
        )
        if corregida.status_code == 200:
            comprobar(corregida.json()["id"] == tierra["id"], "y sigue siendo la misma tierra")
            comprobar(
                corregida.json()["alias"] == "El Prado de arriba",
                "y el nombre nuevo es el que queda",
            )
            comprobar(
                corregida.json()["ref_sigpac"] == tierra["ref_sigpac"],
                "y no se ha perdido la referencia del SIGPAC",
            )
            # La forma del trozo, que es lo que dibuja el mapa: el formulario no la manda (no se
            # devuelve en el listado), así que la corrección **no puede tocarla**.
            if tierra.get("dibujo"):
                comprobar(
                    bool(corregida.json().get("dibujo")),
                    "y la tierra sigue teniendo su forma (el mapa no se queda sin el trozo)",
                )
            # Y se deja como estaba, para no ensuciar el resto de la prueba de humo.
            cliente.put(
                f"/api/parcelas/{tierra['id']}",
                headers=cabeceras,
                json={
                    "alias": tierra["alias"],
                    "ref_sigpac": tierra["ref_sigpac"],
                    "superficie_ha": tierra["superficie_ha"],
                    "sistema": tierra["sistema"],
                    "municipio": tierra["municipio"],
                    "provincia": tierra["provincia"],
                    "uso_sigpac": tierra["uso_sigpac"],
                },
            )

        # Una tierra con apuntes **no se borra**: se dice cuántas cosas dependen de ella y qué hacer.
        if labor.status_code == 201 or apuntes:
            con_apuntes = cliente.delete(f"/api/parcelas/{tierra['id']}", headers=cabeceras)
            comprobar(
                con_apuntes.status_code == 409,
                f"una tierra con apuntes no se borra ({con_apuntes.status_code})",
            )
            comprobar(
                "apunte" in con_apuntes.text and "corrige" in con_apuntes.text.lower(),
                "y el motivo dice cuántas cosas dependen de ella y qué hacer",
            )

        # Y una tierra de prueba, sin nada colgando, se borra.
        de_prueba = cliente.post(
            "/api/parcelas",
            headers=cabeceras,
            json={
                "alias": "Tierra de prueba (se borra)",
                "superficie_ha": 0.5,
                "sistema": "secano",
                "municipio": "Calvarrasa de Arriba",
                "provincia": "Salamanca",
            },
        )
        comprobar(
            de_prueba.status_code == 201,
            f"se puede apuntar una tierra de prueba ({de_prueba.status_code})",
        )
        if de_prueba.status_code == 201:
            borrada = cliente.delete(
                f"/api/parcelas/{de_prueba.json()['id']}", headers=cabeceras
            )
            comprobar(borrada.status_code == 200, f"y una tierra se puede borrar ({borrada.status_code})")
            comprobar(
                cliente.delete(
                    f"/api/parcelas/{de_prueba.json()['id']}", headers=cabeceras
                ).status_code
                == 404,
                "y borrarla otra vez no rompe nada",
            )

        # Los grupos: se corrige el nombre y se borra uno que no se ha usado.
        grupo = cliente.post(
            "/api/grupos",
            headers=cabeceras,
            json={
                "nombre": "Grupo de prueba",
                "campana_id": apunte["campana_id"] if apuntes else None,
                "parcela_ids": [t["id"] for t in tierras[:2]],
            },
        )
        if grupo.status_code in (201, 200):
            ident_grupo = grupo.json()["id"]
            renombrado = cliente.put(
                f"/api/grupos/{ident_grupo}",
                headers=cabeceras,
                json={
                    "nombre": "El de mi hermano",
                    "parcela_ids": grupo.json()["parcela_ids"],
                },
            )
            comprobar(
                renombrado.status_code == 200,
                f"un grupo se puede corregir ({renombrado.status_code}: {renombrado.text[:120]})",
            )
            if renombrado.status_code == 200:
                comprobar(renombrado.json()["nombre"] == "El de mi hermano", "y con el nombre nuevo")
                comprobar(
                    renombrado.json()["parcela_ids"] == grupo.json()["parcela_ids"],
                    "y sin perder sus tierras",
                )
            borrado_grupo = cliente.delete(f"/api/grupos/{ident_grupo}", headers=cabeceras)
            comprobar(
                borrado_grupo.status_code == 200,
                f"y un grupo sin apuntes se puede borrar ({borrado_grupo.status_code})",
            )

    # 33. Las versiones del recinto (T05). Es el recorrido que pidió el ticket y que no se puede
    # comprobar en una prueba de unidad: **previsualizar un lote, aplicarlo dos veces y mirar que la
    # segunda no cree nada**. La segunda aplicación es el reenvío del móvil (un lote que se manda sin
    # cobertura y se vuelve a mandar al recuperarla), y si creara una versión nueva cada vez, el
    # historial de un recinto tendría una fila por cada intento de envío.
    print("\n33. Las versiones del recinto (T05): previsualizar, aplicar dos veces y comparar")

    # Un cuadrado de unos 100 m de lado, en la provincia 37 (la misma parcela que usa el SIGPAC de
    # verdad que hay guardado en `data/sigpac/`). Los números no son inventados: son los de la
    # respuesta de ejemplo.
    CUADRADO = "POLYGON((-5.0 41.0,-4.999 41.0,-4.999 41.001,-5.0 41.001,-5.0 41.0))"

    def _un_recinto(numero: int, **cambios) -> dict:
        """Un recinto del lote, como lo mandaría el SIGPAC."""
        datos = {
            "provincia": "37",
            "municipio": "70",
            "agregado": 0,
            "zona": 0,
            "poligono": 503,
            "numero_parcela": 51,
            "numero_recinto": numero,
            "geometria": CUADRADO if numero == 1 else None,
            "area_sigpac_ha": 0.93,
            "uso_sigpac": "TA",
        }
        datos.update(cambios)
        return datos

    identificador_de_campana = campana.get("id") if isinstance(campana, dict) else None
    comprobar(
        identificador_de_campana is not None,
        "hay una campaña con la que probar las versiones del recinto",
    )
    if identificador_de_campana is not None:
        # Tres recintos: uno con forma, uno sin forma y uno sin superficie. Los tres son «lo que
        # trae la fuente», y ninguno se rellena solo.
        el_lote = {
            "campana_id": identificador_de_campana,
            "fuente": "sigpac",
            "fecha_consulta": "2026-10-03",
            "recintos": [
                _un_recinto(1),
                _un_recinto(2, geometria=None),
                _un_recinto(3, geometria=None, area_sigpac_ha=None),
            ],
        }

        plan = cliente.post(
            "/api/versiones/previsualizar", headers=cabeceras, json=el_lote
        )
        comprobar(
            plan.status_code == 200,
            f"un lote de recintos se puede previsualizar ({plan.status_code}: {plan.text[:160]})",
        )
        if plan.status_code == 200:
            antes = plan.json()
            comprobar(
                antes["aplicada"] is False,
                "previsualizar dice que NO ha aplicado nada",
            )
            comprobar(
                antes["recintos_en_el_lote"] == 3,
                f"el lote lleva sus tres recintos ({antes['recintos_en_el_lote']})",
            )
            comprobar(
                antes["nuevos"] == 3,
                f"y los tres son nuevos, porque no había ninguno ({antes['nuevos']})",
            )
            comprobar(
                antes["sin_forma"] == 2,
                f"y dos no traen polígono ({antes['sin_forma']})",
            )
            comprobar(
                antes["nuevos"] + antes["cambiados"] + antes["iguales"] == 3,
                "los tres números suman los recintos del lote, ni uno más",
            )

            # **Previsualizar no escribe**, y eso se comprueba mirando, no preguntando: se listan las
            # versiones de esa campaña y tienen que estar vacías.
            guardadas_antes = cliente.get(
                "/api/versiones",
                headers=cabeceras,
                params={"campana_id": identificador_de_campana},
            )
            if guardadas_antes.status_code == 200:
                comprobar(
                    guardadas_antes.json() == [],
                    f"y no ha guardado ninguna versión ({len(guardadas_antes.json())})",
                )
            else:
                comprobar(
                    False,
                    f"no se han podido listar las versiones ({guardadas_antes.status_code})",
                )

            aplicado = cliente.post("/api/versiones/aplicar", headers=cabeceras, json=el_lote)
            comprobar(
                aplicado.status_code == 200,
                f"el lote se puede aplicar ({aplicado.status_code}: {aplicado.text[:160]})",
            )
            if aplicado.status_code == 200:
                despues = aplicado.json()
                comprobar(despues["aplicada"] is True, "aplicar dice que sí ha aplicado")
                comprobar(
                    despues["versiones_creadas"] == 3,
                    f"y ha creado tres versiones ({despues['versiones_creadas']})",
                )

                guardadas = cliente.get(
                    "/api/versiones",
                    headers=cabeceras,
                    params={"campana_id": identificador_de_campana},
                )
                if guardadas.status_code == 200:
                    filas = guardadas.json()
                    comprobar(len(filas) == 3, f"y las tres están guardadas ({len(filas)})")
                    # **El recinto sin forma sale en la lista**, con su frase. No se le dibuja una
                    # forma que nadie ha medido, y tampoco desaparece de la tabla.
                    sin_forma = [fila for fila in filas if fila.get("tiene_forma") is False]
                    comprobar(
                        len(sin_forma) == 2,
                        f"y los dos sin forma salen en la lista, diciéndolo ({len(sin_forma)})",
                    )
                    if sin_forma:
                        comprobar(
                            "forma" in sin_forma[0].get("como_esta", "").lower(),
                            f"y con la frase que dice que no hay forma "
                            f"({sin_forma[0].get('como_esta')!r})",
                        )

                    # **Las tres áreas son tres cosas distintas y ninguna se deduce de otra.** La de
                    # la forma la mide el programa; la del SIGPAC y la declarada las dice la fuente.
                    # Y la que no se sabe **se queda sin saber: vacía, nunca 0**.
                    por_recinto = {
                        fila["numero_recinto"]: fila
                        for fila in filas
                        if fila.get("numero_recinto") is not None
                    }
                    el_primero = por_recinto.get(1)
                    if el_primero is None:
                        comprobar(False, "no ha vuelto el recinto 1 en la lista de versiones")
                    else:
                        comprobar(
                            el_primero["area_sigpac_ha"] == 0.93,
                            f"la superficie que dijo el SIGPAC se guarda tal cual "
                            f"({el_primero['area_sigpac_ha']})",
                        )
                        comprobar(
                            el_primero["area_geometria_ha"] is not None,
                            "y la de la forma la mide el programa, no se copia de la del SIGPAC",
                        )
                        comprobar(
                            el_primero["area_declarada_ha"] is None,
                            f"y la que no dijo nadie se queda sin saber, no en cero "
                            f"({el_primero['area_declarada_ha']!r})",
                        )
                    el_tercero = por_recinto.get(3)
                    if el_tercero is None:
                        comprobar(False, "no ha vuelto el recinto 3 en la lista de versiones")
                    else:
                        comprobar(
                            el_tercero["area_sigpac_ha"] is None,
                            f"un recinto sin superficie no sale con cero hectáreas "
                            f"({el_tercero['area_sigpac_ha']!r})",
                        )
                        comprobar(
                            el_tercero["tiene_forma"] is False,
                            "y sigue sin forma, sin inventársela",
                        )

                # **La segunda vez no crea nada.** Es el reenvío desde la cola del móvil.
                otra_vez = cliente.post("/api/versiones/aplicar", headers=cabeceras, json=el_lote)
                comprobar(
                    otra_vez.status_code == 200,
                    f"el mismo lote se puede volver a aplicar, como un reenvío "
                    f"({otra_vez.status_code}: {otra_vez.text[:160]})",
                )
                if otra_vez.status_code == 200:
                    repetido = otra_vez.json()
                    comprobar(
                        repetido["versiones_creadas"] == 0,
                        f"y la segunda vez NO crea ninguna versión "
                        f"({repetido['versiones_creadas']})",
                    )
                    comprobar(
                        repetido["iguales"] == 3,
                        f"y los tres salen como iguales ({repetido['iguales']})",
                    )
                    comprobar(
                        repetido["tierras_creadas"] == [],
                        f"y no da de alta ninguna tierra de nuevo "
                        f"({repetido['tierras_creadas']})",
                    )
                    if guardadas.status_code == 200:
                        otra_lista = cliente.get(
                            "/api/versiones",
                            headers=cabeceras,
                            params={"campana_id": identificador_de_campana},
                        )
                        if otra_lista.status_code == 200:
                            comprobar(
                                len(otra_lista.json()) == 3,
                                f"y siguen siendo tres versiones, no seis "
                                f"({len(otra_lista.json())})",
                            )

    # 34. La vista de las tierras (T06). Lo que pidió el ticket, medido contra el servidor de verdad:
    # que una tierra **sin forma siga en la lista diciéndolo** (no desaparece), que no traiga anillos
    # que dibujar (no se le inventa una forma), y sobre todo que **los recuentos cuadren con las
    # filas**: si el pie dice 7 y salen 6, o si «sin forma» dice 0 y hay una fila sin forma, el
    # agricultor deja de fiarse de todo lo demás. Es el contrato más importante de esta pantalla.
    print("\n34. La vista de las tierras (T06): la tabla, el grupo «sin forma» y el mapa")
    vista = cliente.get("/api/parcelas/vista", headers=cabeceras)
    comprobar(
        vista.status_code == 200,
        f"la vista de las tierras se sirve ({vista.status_code}: {vista.text[:160]})",
    )
    if vista.status_code == 200:
        datos = vista.json()
        tierras = datos["tierras"]
        totales = datos["totales"]
        comprobar(
            len(tierras) == totales["tierras"],
            f"el recuento de tierras cuadra con las filas "
            f"({len(tierras)} filas contra {totales['tierras']} en el pie)",
        )
        sin_forma = [tierra for tierra in tierras if not tierra["tiene_forma"]]
        con_forma = [tierra for tierra in tierras if tierra["tiene_forma"]]
        comprobar(
            len(sin_forma) == totales["sin_forma"],
            f"el grupo «sin forma» cuadra ({len(sin_forma)} contra {totales['sin_forma']})",
        )
        comprobar(
            len(con_forma) == totales["con_forma"],
            f"las que tienen forma cuadran ({len(con_forma)} contra {totales['con_forma']})",
        )
        comprobar(
            all(tierra["anillos"] == [] for tierra in sin_forma),
            "una tierra sin forma sigue en la lista y no trae anillos que dibujar",
        )
        comprobar(
            all(tierra["forma"] is None for tierra in sin_forma),
            "y no se le inventa un dibujo",
        )
        comprobar(
            all(tierra["anillos"] for tierra in con_forma),
            "una tierra con forma sí trae sus anillos",
        )
        comprobar(
            [tierra["numero"] for tierra in tierras] == list(range(1, len(tierras) + 1)),
            "cada tierra trae su número, seguido y sin repetir",
        )
        el_mapa = datos["mapa"]
        comprobar(
            el_mapa["hay_forma"] == bool(con_forma),
            f"el mapa dice si hay algo que dibujar ({el_mapa['hay_forma']})",
        )
        if con_forma:
            caja = el_mapa.get("caja")
            comprobar(caja is not None, "con formas, el mapa trae su caja")
            if caja:
                comprobar(
                    all(
                        caja["oeste"] <= punto[0] <= caja["este"]
                        and caja["sur"] <= punto[1] <= caja["norte"]
                        for tierra in con_forma
                        for anillo in tierra["anillos"]
                        for punto in anillo
                    ),
                    "y la caja contiene todos los vértices: el mapa no deja ninguna fuera",
                )
        else:
            comprobar(
                el_mapa.get("caja") is None,
                "sin formas no hay caja: el mapa no se inventa un centro ni salta de provincia",
            )

        # **Las tres comprobaciones que pide el subagente de T06, y que son las que habrían cazado
        # los tres defectos que de verdad aparecieron en esa pantalla** (03/10/2026). No son teóricas:
        # las tres cosas pasaron.

        # 1. El mismo número dicho dos veces tiene que ser el mismo número. `totales.con_forma` y
        # `mapa.tierras_con_forma` llegaron a decir **2 y 1 en la misma respuesta**, porque uno miraba
        # la forma escrita y el otro los anillos que se pueden dibujar.
        comprobar(
            totales["con_forma"] == el_mapa["tierras_con_forma"],
            "el mismo recuento no se dice de dos formas distintas "
            f"({totales['con_forma']} contra {el_mapa['tierras_con_forma']})",
        )

        # 2. **La caja que da la vista la tiene que aceptar el propio programa.** Con una finca de más
        # de medio grado, `/api/mapa/imagen` contestaba 422 y la pantalla decía «puede ser la
        # cobertura», mandando a mirar donde no era. Aquí se comprueba con los límites que el propio
        # programa publica en `/api/mapa/estado`, y que la envolvente sin recortar contenga la caja.
        estado_del_mapa = cliente.get("/api/mapa/estado")
        if estado_del_mapa.status_code != 200 or not el_mapa.get("caja"):
            comprobar(
                estado_del_mapa.status_code == 200,
                f"el estado del mapa se sirve ({estado_del_mapa.status_code})",
            )
        else:
            limites = estado_del_mapa.json()["limites"]
            la_caja = el_mapa["caja"]
            lado = max(
                la_caja["norte"] - la_caja["sur"], la_caja["este"] - la_caja["oeste"]
            )
            comprobar(
                limites["lado_minimo_grados"] <= lado <= limites["lado_maximo_grados"],
                f"la caja que da la vista está dentro de lo que el programa acepta "
                f"({lado:.4f} grados, y los topes son "
                f"{limites['lado_minimo_grados']}–{limites['lado_maximo_grados']})",
            )
            envolvente = el_mapa.get("extension")
            if envolvente:
                comprobar(
                    envolvente["oeste"] <= la_caja["oeste"]
                    and envolvente["sur"] <= la_caja["sur"]
                    and envolvente["este"] >= la_caja["este"]
                    and envolvente["norte"] >= la_caja["norte"],
                    "y la envolvente sin recortar contiene a la caja que se pide",
                )
                dentro_de_la_caja = (
                    abs(envolvente["oeste"] - la_caja["oeste"]) < 1e-9
                    and abs(envolvente["este"] - la_caja["este"]) < 1e-9
                    and abs(envolvente["sur"] - la_caja["sur"]) < 1e-9
                    and abs(envolvente["norte"] - la_caja["norte"]) < 1e-9
                )
                comprobar(
                    bool(el_mapa.get("se_puede_ensenar_entera")) == dentro_de_la_caja,
                    "y dice si cabe entera justo cuando cabe "
                    f"(dice {el_mapa.get('se_puede_ensenar_entera')})",
                )
            else:
                comprobar(
                    False, "la vista no trae la envolvente de las formas (`extension`)"
                )

        # 3. **Cada opción de un filtro dice un número, y ese número tiene que salir de contar las
        # filas.** Aquí es donde más se rompió esta pantalla: el filtro del pueblo llegó a decir 3 y
        # enseñar 4, dos veces y por dos motivos distintos (mayúsculas por un lado, tildes y espacios
        # por otro). Se cuenta **con una normalización escrita aquí**, no con la del servidor: si se
        # usara la suya, la prueba estaría de acuerdo consigo misma y no comprobaría nada.
        filtros = datos.get("filtros") or {}
        for nombre_del_filtro, campo_de_la_tierra in (
            ("municipios", "municipio"),
            ("pueblos", "municipio"),
            ("cultivos", "cultivo_clave"),
        ):
            opciones = filtros.get(nombre_del_filtro)
            if not opciones:
                continue
            malas = []
            for opcion in opciones:
                valor = opcion.get("valor") or ""
                if valor.startswith("sin_"):
                    # **Las opciones de «nada dicho» no llevan el texto de nadie**: llevan una clave
                    # propia (`sin_pueblo`, `sin_cultivo`), así que lo que cuentan son las tierras que
                    # no lo dicen. Comprobarlo aquí es lo que impide que esa opción diga un número y
                    # enseñe otro, que es justo el fallo que tuvo esta pantalla.
                    contadas = sum(
                        1
                        for tierra in tierras
                        if not _para_comparar(tierra.get(campo_de_la_tierra) or "")
                    )
                else:
                    contadas = sum(
                        1
                        for tierra in tierras
                        if _para_comparar(tierra.get(campo_de_la_tierra) or "")
                        == _para_comparar(valor)
                    )
                if contadas != opcion.get("cuantas"):
                    malas.append(
                        f"{opcion.get('texto')!r} dice {opcion.get('cuantas')} y salen {contadas}"
                    )
            comprobar(
                malas == [],
                f"cada opción de «{nombre_del_filtro}» cuenta lo que sale al aplicarla "
                f"({'; '.join(malas) if malas else f'{len(opciones)} opciones cuadran'})",
            )

    # 35. **Del papel al almacén y al cuaderno (T09).** Esta sección faltaba y es la que más falta
    # hacía: el recorrido no llamaba ni una vez a `/api/almacen`, así que la compra, la recepción y
    # las existencias —el primer tramo del recorrido de negocio— **no pasaban nunca por la puerta de
    # fuera**. Un defecto entre dos rutas (una siembra anulada que se reenvía y no descuenta) se coló
    # por ahí en T10 y lo encontró el revisor a mano. Esto lo ve solo.
    print("\n35. Del papel al almacén: entra un albarán, sale producto y se anula")
    albaran = cliente.post(
        "/api/almacen/recepciones",
        headers=cabeceras,
        json={
            "fecha": "2026-03-15",
            "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
            "numero_albaran": "A-2026-118",
            "lineas": [
                {
                    "nombre": "Glifosato 36 SL",
                    "categoria": "fitosanitario",
                    "unidad": "L",
                    "cantidad": 5.0,
                    "unidad_de_la_cantidad": "L",
                    "numero_lote": "4471-A",
                    "fecha_caducidad": "2028-06-30",
                    "presentacion": "garrafa de 5 L",
                }
            ],
        },
    )
    comprobar(
        albaran.status_code in (200, 201),
        f"un albarán con su línea entra al almacén ({albaran.status_code}: {albaran.text[:160]})",
    )
    if albaran.status_code in (200, 201):
        cuerpo = albaran.json()
        identificador = (cuerpo.get("recepcion") or cuerpo).get("id")
        articulo_id = (cuerpo.get("recepcion") or cuerpo).get("lineas", [{}])[0].get(
            "articulo_id"
        )

        def el_saldo(articulo: int | None):
            """Lo que queda del artículo, tal y como lo cuenta el propio programa.

            El campo se llama `saldo` y **puede ser `None`**, que es «no se puede saber» (por ejemplo
            si en el mismo envase entraron litros y kilos): por eso las comprobaciones de abajo no
            comparan contra un cero cuando no hay dato.
            """
            existencias = cliente.get("/api/almacen/existencias", headers=cabeceras)
            if existencias.status_code != 200:
                return None
            for fila in existencias.json().get("articulos", []):
                if fila.get("articulo_id") == articulo:
                    return fila.get("saldo")
            return None

        comprobar(
            articulo_id is not None,
            f"y la línea dice de qué artículo es ({articulo_id})",
        )
        comprobar(
            el_saldo(articulo_id) == 5.0,
            f"y lo que queda son los cinco litros que entraron ({el_saldo(articulo_id)!r})",
        )
        # Reenviar el mismo albarán no puede meter el producto dos veces: es lo que hace la cola del
        # móvil cuando no hay cobertura.
        otra_vez = cliente.post(
            "/api/almacen/recepciones",
            headers=cabeceras,
            json={
                "fecha": "2026-03-15",
                "proveedor": "COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L.",
                "numero_albaran": "A-2026-118",
                "lineas": [
                    {
                        "nombre": "Glifosato 36 SL",
                        "categoria": "fitosanitario",
                        "unidad": "L",
                        "cantidad": 5.0,
                        "unidad_de_la_cantidad": "L",
                        "numero_lote": "4471-A",
                    }
                ],
                "clave_de_reenvio": "humo-albaran-118",
            },
        )
        comprobar(
            otra_vez.status_code in (200, 201, 409),
            f"y volver a mandar el mismo albarán se contesta, no revienta ({otra_vez.status_code})",
        )
        # Y anular el albarán tiene que devolver el almacén a cero **sin borrar nada**.
        anulado = cliente.post(
            f"/api/almacen/recepciones/{identificador}/anular",
            headers=cabeceras,
            json={"motivo": "Me equivoqué de albarán"},
        )
        comprobar(
            anulado.status_code == 200,
            f"y un albarán se puede anular con su motivo ({anulado.status_code}: {anulado.text[:120]})",
        )
        if anulado.status_code == 200:
            comprobar(
                el_saldo(articulo_id) in (0, 0.0),
                f"y anulado, el almacén deja de contar lo que entró ({el_saldo(articulo_id)!r})",
            )
            apuntes = cliente.get(
                f"/api/almacen/recepciones/{identificador}", headers=cabeceras
            )
            comprobar(
                apuntes.status_code == 200 and apuntes.json().get("anulada") is True,
                "y el albarán sigue ahí, marcado como anulado: no se borra nada",
            )

    # 36. **La semilla, del almacén a la tierra (T10).** La otra mitad del agujero del apartado 35: el
    # recorrido tampoco llamaba a `/api/semillas`. Aquí se comprueba lo que el encargo pone como
    # riesgo número uno —**la dosis por hectárea no es la cantidad total**— y lo que rompió de verdad
    # en este ticket según su revisión independiente: que la cuenta la haga el servidor **y se sepa**,
    # que un dato que no se puede calcular **no se invente un cero**, y que la semilla salga del
    # almacén **una sola vez** aunque se reenvíe desde la cola.
    print("\n36. La semilla: de la compra a la tierra, con la dosis y el total cada uno en su sitio")
    el_albaran = cliente.post(
        "/api/almacen/recepciones",
        headers=cabeceras,
        json={
            "fecha": "2026-02-20",
            "proveedor": "SEMILLAS DEL DUERO S.L.",
            "numero_albaran": "S-2026-44",
            "lineas": [
                {
                    "nombre": "Veza comun Villalobos",
                    "categoria": "semilla",
                    "unidad": "kg",
                    "cantidad": 1000.0,
                    "unidad_de_la_cantidad": "kg",
                    "numero_lote": "4471-A",
                    "fecha_caducidad": "2028-01-12",
                }
            ],
        },
    )
    comprobar(
        el_albaran.status_code in (200, 201),
        f"la semilla comprada entra al almacén ({el_albaran.status_code}: {el_albaran.text[:140]})",
    )
    if el_albaran.status_code in (200, 201):
        cuerpo_del_albaran = el_albaran.json()
        la_recepcion = cuerpo_del_albaran.get("recepcion") or cuerpo_del_albaran
        articulo_de_la_semilla = la_recepcion.get("lineas", [{}])[0].get("articulo_id")
        comprobar(
            articulo_de_la_semilla is not None,
            f"y la línea dice de qué artículo es ({articulo_de_la_semilla})",
        )

        la_semilla = cliente.post(
            "/api/semillas",
            headers=cabeceras,
            json={
                "articulo_id": articulo_de_la_semilla,
                "unidad": "kg",
                "especie": "Veza comun",
                "variedad": "Villalobos",
                "casa_comercial": "Semillas del Duero",
                "numero_lote_proveedor": "4471-A",
                "dosis_recomendada_por_ha": 120.0,
                "unidad_dosis": "kg/ha",
                "fecha_caducidad": "2028-01-12",
                "poder_germinativo_pct": 92.0,
                "pureza_pct": 99.2,
                "tratada": False,
            },
        )
        comprobar(
            la_semilla.status_code in (200, 201),
            f"y la semilla se da de alta sobre ese artículo "
            f"({la_semilla.status_code}: {la_semilla.text[:140]})",
        )
        if la_semilla.status_code in (200, 201):
            semilla_id = la_semilla.json().get("id")
            tierras = cliente.get("/api/parcelas", headers=cabeceras).json()
            if not tierras:
                comprobar(False, "no hay ninguna tierra donde sembrar")
            else:
                parcela_id = tierras[0]["id"]

                # **La dosis por hectárea y la cantidad total, cada una con su nombre.** Aquí se dan
                # las dos a propósito: es el caso en el que el programa no tiene que calcular nada.
                # **La siembra tiene que decir de qué envase sale la semilla.** Sin envase no se puede
                # descontar del almacén (y el programa lo dice en vez de inventarse un cero), así que
                # se busca el lote que acaba de entrar con el albarán.
                def el_primer_lote(articulo: int | None):
                    existencias = cliente.get("/api/almacen/existencias", headers=cabeceras)
                    if existencias.status_code != 200:
                        return None
                    for fila in existencias.json().get("articulos", []):
                        if fila.get("articulo_id") == articulo:
                            lotes = fila.get("lotes") or []
                            return lotes[0].get("lote_id") if lotes else None
                    return None

                el_lote_de_la_semilla = el_primer_lote(articulo_de_la_semilla)
                comprobar(
                    el_lote_de_la_semilla is not None,
                    f"y el albarán ha dejado un envase del que sacarla ({el_lote_de_la_semilla})",
                )

                el_cuerpo_de_la_siembra = {
                    "semilla_id": semilla_id,
                    "parcela_id": parcela_id,
                    "lote_id": el_lote_de_la_semilla,
                    "fecha": "2026-03-01",
                    "superficie_ha": 2.0,
                    "dosis_por_ha": 120.0,
                    "unidad_dosis": "kg/ha",
                    "cantidad_total": 240.0,
                    "unidad_cantidad": "kg",
                    "clave_de_reenvio": "humo-siembra-1",
                }
                sembrada = cliente.post(
                    "/api/siembras", headers=cabeceras, json=el_cuerpo_de_la_siembra
                )
                comprobar(
                    sembrada.status_code in (200, 201),
                    f"una siembra se apunta diciendo la dosis y el total "
                    f"({sembrada.status_code}: {sembrada.text[:140]})",
                )
                if sembrada.status_code in (200, 201):
                    la_siembra = sembrada.json().get("siembra") or sembrada.json()
                    comprobar(
                        la_siembra.get("dosis_por_ha") == 120.0
                        and (la_siembra.get("cantidad_total") == 240.0),
                        f"y salen las dos, cada una con su número "
                        f"(dosis {la_siembra.get('dosis_por_ha')!r}, "
                        f"total {la_siembra.get('cantidad_total')!r})",
                    )
                    comprobar(
                        (la_siembra.get("unidad_dosis"), la_siembra.get("unidad_cantidad"))
                        == ("kg/ha", "kg"),
                        f"y cada una con su unidad "
                        f"({la_siembra.get('unidad_dosis')!r}, "
                        f"{la_siembra.get('unidad_cantidad')!r})",
                    )

                # **Y cuando solo dan la dosis, el total lo calcula el programa y LO DICE.** Un
                # número que sale de una cuenta y no se distingue de uno que le han dado es un número
                # que el agricultor no puede comprobar.
                calculada = cliente.post(
                    "/api/siembras",
                    headers=cabeceras,
                    json={
                        "semilla_id": semilla_id,
                        "parcela_id": parcela_id,
                        "fecha": "2026-03-02",
                        "superficie_ha": 1.0,
                        "dosis_por_ha": 120.0,
                        "unidad_dosis": "kg/ha",
                        "unidad_cantidad": "kg",
                        "clave_de_reenvio": "humo-siembra-2",
                    },
                )
                if calculada.status_code in (200, 201):
                    la_calculada = calculada.json().get("siembra") or calculada.json()
                    comprobar(
                        la_calculada.get("cantidad_total") == 120.0,
                        f"con la dosis y la superficie, el total sale solo "
                        f"({la_calculada.get('cantidad_total')!r})",
                    )
                    comprobar(
                        la_calculada.get("cantidad_total_calculada") is True,
                        f"y dice que lo ha calculado, no lo da por sabido "
                        f"({la_calculada.get('cantidad_total_calculada')!r})",
                    )
                else:
                    comprobar(
                        False,
                        f"no se ha podido apuntar la siembra con solo la dosis "
                        f"({calculada.status_code}: {calculada.text[:140]})",
                    )

                # **Y sin superficie no se puede calcular: se queda vacío, nunca cero.** Es la regla
                # de la casa —un dato que no se sabe no es un cero— aplicada al caso donde es más
                # fácil equivocarse.
                sin_superficie = cliente.post(
                    "/api/siembras",
                    headers=cabeceras,
                    json={
                        "semilla_id": semilla_id,
                        "parcela_id": parcela_id,
                        "fecha": "2026-03-03",
                        "dosis_por_ha": 120.0,
                        "unidad_dosis": "kg/ha",
                        "unidad_cantidad": "kg",
                        "clave_de_reenvio": "humo-siembra-3",
                    },
                )
                if sin_superficie.status_code in (200, 201):
                    la_sin_superficie = (
                        sin_superficie.json().get("siembra") or sin_superficie.json()
                    )
                    comprobar(
                        la_sin_superficie.get("cantidad_total") in (None, ""),
                        f"sin superficie, el total se queda sin saber, no en cero "
                        f"({la_sin_superficie.get('cantidad_total')!r})",
                    )
                else:
                    comprobar(
                        False,
                        f"no se ha podido apuntar la siembra sin superficie "
                        f"({sin_superficie.status_code}: {sin_superficie.text[:140]})",
                    )

                # **Y el defecto de gravedad alta que encontró la revisión de T10**: anular una
                # siembra y **volver a mandar la misma petición** —que es lo que hace la cola del
                # móvil: reenviar con la misma clave— tiene que **volver a descontar del almacén**.
                # Antes no lo hacía: la salida vieja se encontraba por su clave `«…:salida»` y se daba
                # por buena aunque su siembra estuviera anulada, así que el agricultor veía el apunte
                # hecho **y la semilla seguía en la nave** —y el aviso le decía que no se descontaba
                # «porque no se sabe de qué envase sale», con el envase en la misma respuesta—.
                #
                # Lo cazó una revisión independiente entera. **Esta comprobación lo habría cazado
                # sola**, y por eso está aquí: era el agujero del apartado 18.4 de este documento.
                def lo_que_queda(articulo: int | None):
                    existencias = cliente.get("/api/almacen/existencias", headers=cabeceras)
                    if existencias.status_code != 200:
                        return None
                    for fila in existencias.json().get("articulos", []):
                        if fila.get("articulo_id") == articulo:
                            return fila.get("saldo")
                    return None

                if sembrada.status_code in (200, 201):
                    identificador_siembra = la_siembra.get("id")
                    comprobar(
                        lo_que_queda(articulo_de_la_semilla) == 760.0,
                        f"y la semilla ha salido del almacén una vez "
                        f"({lo_que_queda(articulo_de_la_semilla)!r} de 1000)",
                    )
                    anulada = cliente.post(
                        f"/api/siembras/{identificador_siembra}/anular",
                        headers=cabeceras,
                        json={"motivo": "Me equivoqué de tierra"},
                    )
                    comprobar(
                        anulada.status_code == 200,
                        f"una siembra se puede anular con su motivo "
                        f"({anulada.status_code}: {anulada.text[:120]})",
                    )
                    if anulada.status_code == 200:
                        comprobar(
                            lo_que_queda(articulo_de_la_semilla) == 1000.0,
                            f"y anulada, la semilla vuelve al almacén "
                            f"({lo_que_queda(articulo_de_la_semilla)!r})",
                        )
                        # **El reenvío de la cola, que es donde estaba el defecto.**
                        el_reenvio = cliente.post(
                            "/api/siembras", headers=cabeceras, json=el_cuerpo_de_la_siembra
                        )
                        comprobar(
                            el_reenvio.status_code in (200, 201),
                            f"y volver a mandar la misma siembra se contesta, no revienta "
                            f"({el_reenvio.status_code}: {el_reenvio.text[:120]})",
                        )
                        comprobar(
                            lo_que_queda(articulo_de_la_semilla) == 760.0,
                            f"y la semilla vuelve a salir del almacén: "
                            f"{lo_que_queda(articulo_de_la_semilla)!r} "
                            "(el defecto era que se quedaba en 1000 y el apunte parecía hecho)",
                        )

    print("\n37. Las personas y las empresas (T11): los nombres escritos y la fusión que NO se hace sola")
    # **Por qué existe esta sección.** El módulo de contactos entró con 55 pruebas de Python y 32 de
    # JavaScript, y una revisión independiente le encontró cuatro defectos. El más grave: el programa
    # juntaba dos nombres distintos **solo porque llevaban el mismo NIF**, lo marcaba como «seguro» y el
    # guion de migración lo apuntaba **sin preguntar**. Y este recorrido no tocaba ni una vez
    # `/api/contactos`: lo que se arregló allí no lo vigilaba nadie aquí. Esto es ese vigilante.
    escritos = cliente.get("/api/contactos/escritos", headers=cabeceras)
    comprobar(
        escritos.status_code == 200,
        f"el programa sabe qué nombres hay escritos a mano en los papeles ({escritos.status_code})",
    )
    textos_escritos = [fila["texto"] for fila in escritos.json()] if escritos.status_code == 200 else []
    comprobar(
        any("duero" in _para_comparar(texto) for texto in textos_escritos),
        f"y entre ellos está el proveedor del albarán, tal y como se escribió ({textos_escritos[:3]})",
    )

    # Una ficha a mano, que es lo que hace el agricultor cuando alguien no está en ningún papel.
    la_ficha = cliente.post(
        "/api/contactos",
        headers=cabeceras,
        json={
            "nombre": "Talleres Aguirre",
            "es_empresa": True,
            "nif": "B99999999",
            "papeles": ["proveedor"],
        },
    )
    comprobar(
        la_ficha.status_code in (200, 201),
        f"una ficha se da de alta a mano ({la_ficha.status_code}: {la_ficha.text[:120]})",
    )
    if la_ficha.status_code in (200, 201):
        el_identificador = la_ficha.json().get("id")
        leida = cliente.get(f"/api/contactos/{el_identificador}", headers=cabeceras)
        comprobar(
            leida.status_code == 200
            and _para_comparar(leida.json().get("nombre", "")) == "talleres aguirre",
            f"y se vuelve a leer con su nombre ({leida.status_code}: {leida.text[:120]})",
        )

    # **El caso del defecto, montado a propósito**: dos albaranes de dos proveedores distintos con
    # **el mismo NIF** (un NIF mal tecleado de una letra). El programa **no** puede juntarlos solo.
    for indice, nombre_del_proveedor in enumerate(("Juan Garcia Lopez", "Pedro Lopez Ruiz"), start=1):
        el_albaran_del_nif = cliente.post(
            "/api/almacen/recepciones",
            headers=cabeceras,
            json={
                "fecha": "2026-03-02",
                "proveedor": nombre_del_proveedor,
                "proveedor_nif": "B12345678",
                "numero_albaran": f"NIF-{indice}",
                "lineas": [
                    {
                        "nombre": f"Producto del NIF {indice}",
                        "categoria": "fitosanitario",
                        "unidad": "l",
                        "cantidad": 5.0,
                        "unidad_de_la_cantidad": "l",
                    }
                ],
            },
        )
        comprobar(
            el_albaran_del_nif.status_code in (200, 201),
            f"se apunta el albarán de «{nombre_del_proveedor}» con el NIF B12345678 "
            f"({el_albaran_del_nif.status_code}: {el_albaran_del_nif.text[:110]})",
        )

    fichas_antes = cliente.get("/api/contactos", headers=cabeceras)
    cuantas_antes = len(fichas_antes.json()) if fichas_antes.status_code == 200 else None
    revision = cliente.get("/api/contactos/migracion", headers=cabeceras)
    comprobar(
        revision.status_code == 200,
        f"la revisión de los nombres se puede mirar ({revision.status_code}: {revision.text[:120]})",
    )
    if revision.status_code == 200:
        la_revision = revision.json()
        resumen = la_revision.get("resumen", {})
        comprobar(
            resumen.get("nif_con_nombres_distintos", 0) >= 1,
            "y los dos nombres del mismo NIF salen como «no se juntan» "
            f"({resumen.get('nif_con_nombres_distintos')} caso(s); el defecto era que se juntaban "
            "y se apuntaban solos)",
        )

        def los_dos_en_la_misma_ficha(propuesta: dict) -> bool:
            suyos = {_para_comparar(nombre) for nombre in propuesta.get("nombres", [])}
            return {"juan garcia lopez", "pedro lopez ruiz"} <= suyos

        juntas = [
            propuesta
            for propuesta in la_revision.get("propuestas", [])
            if propuesta.get("segura") and los_dos_en_la_misma_ficha(propuesta)
        ]
        comprobar(
            not juntas,
            f"y ninguna propuesta **segura** mete los dos nombres en la misma ficha ({juntas})",
        )
        cuantas_despues = len(cliente.get("/api/contactos", headers=cabeceras).json())
        comprobar(
            cuantas_antes == cuantas_despues,
            f"y mirar la revisión no apunta ninguna ficha "
            f"({cuantas_antes} antes, {cuantas_despues} después)",
        )

    print("\n38. El dinero de las ventas (T12): lo que no tiene precio, la factura y el cobro parcial")
    # **Por qué existe esta sección.** El dinero entró con sus pruebas, y su revisión independiente
    # encontró doce defectos —tres de ellos de producción—. El recorrido oficial no lo tocaba, así que se
    # añade aquí lo que el contrato pide con nombre y apellidos: **A08** (una entrega sin precio no es un
    # ingreso de cero) y **A06** (una factura de 121 con un pago de 40 deja 81 pendientes, y un segundo
    # importe no crea una segunda factura).

    # ── A08: 8.000 kg sin precio ───────────────────────────────────────────────
    sin_precio = cliente.post(
        "/api/ventas",
        headers=cabeceras,
        json={
            "campana_id": campana["id"],
            "tipo": "comercializada",
            "fecha": "2026-07-15",
            "producto": "Cebada",
            "cantidad": 8.0,
            "unidad": "t",
            "comprador": "Cooperativa Agrícola de Peñaranda",
        },
    )
    comprobar(
        sin_precio.status_code == 201,
        f"una entrega se apunta aunque no se sepa el precio ({sin_precio.status_code})",
    )
    if sin_precio.status_code == 201:
        suya = sin_precio.json()
        comprobar(suya.get("kilos") == 8000.0, f"y los kilos se saben ({suya.get('kilos')!r})")
        comprobar(
            suya.get("importe") is None,
            f"y el importe queda PENDIENTE, no en cero ({suya.get('importe')!r})",
        )
        comprobar(
            suya.get("estado") == "sin_importe",
            f"y la entrega dice que le falta el importe ({suya.get('estado')!r})",
        )

        # Y no se puede facturar: el A08 no puede colarse por la puerta de atrás de la factura.
        factura_sin_precio = cliente.post(
            "/api/facturas-emitidas",
            headers=cabeceras,
            json={"fecha": "2026-07-16", "entregas": [suya["id"]]},
        )
        comprobar(
            factura_sin_precio.status_code == 422,
            f"y una entrega sin precio NO se puede facturar "
            f"({factura_sin_precio.status_code}: {factura_sin_precio.text[:110]})",
        )

        # ── A06: factura de 121, pago de 40, pendiente 81 ─────────────────────
        con_importe = cliente.put(
            f"/api/ventas/{suya['id']}",
            headers=cabeceras,
            json={
                "campana_id": campana["id"],
                "tipo": "comercializada",
                "fecha": "2026-07-15",
                "producto": "Cebada",
                "cantidad": 8.0,
                "unidad": "t",
                "comprador": "Cooperativa Agrícola de Peñaranda",
                "importe": "121.00",
                "vencimiento": "2026-08-15",
            },
        )
        comprobar(
            con_importe.status_code == 200,
            f"a la entrega se le puede poner su importe ({con_importe.status_code})",
        )
        if con_importe.status_code == 200:
            comprobar(
                _euros(con_importe.json().get("importe")) == "121.00",
                f"y el importe se guarda con sus céntimos "
                f"({_euros(con_importe.json().get('importe'))})",
            )

            cuantas_antes = len(
                cliente.get("/api/facturas-emitidas", headers=cabeceras).json()
            )
            la_factura = cliente.post(
                "/api/facturas-emitidas",
                headers=cabeceras,
                json={"fecha": "2026-07-16", "entregas": [suya["id"]]},
            )
            comprobar(
                la_factura.status_code == 201,
                f"la entrega se factura ({la_factura.status_code}: {la_factura.text[:110]})",
            )
            if la_factura.status_code == 201:
                la_factura_cuerpo = la_factura.json()
                identificador_de_la_factura = la_factura_cuerpo["id"]
                comprobar(
                    _euros(la_factura_cuerpo.get("importe_total")) == "121.00",
                    f"y la factura suma sus líneas, no se lo inventa "
                    f"({_euros(la_factura_cuerpo.get('importe_total'))})",
                )

                el_cobro = cliente.post(
                    "/api/cobros",
                    headers=cabeceras,
                    json={
                        "fecha": "2026-07-20",
                        "importe": "40.00",
                        "factura_emitida_id": identificador_de_la_factura,
                        "clave_de_reenvio": "cobro-parcial-40",
                    },
                )
                comprobar(
                    el_cobro.status_code == 201,
                    f"se apunta un cobro parcial de 40 ({el_cobro.status_code}: {el_cobro.text[:110]})",
                )

                la_factura_leida = cliente.get(
                    f"/api/facturas-emitidas/{identificador_de_la_factura}", headers=cabeceras
                ).json()
                comprobar(
                    _euros(la_factura_leida.get("pendiente")) == "81.00",
                    f"y de 121 pagados 40 quedan 81 ({_euros(la_factura_leida.get('pendiente'))})",
                )
                comprobar(
                    _euros(la_factura_leida.get("cobrado")) == "40.00",
                    f"y lo cobrado es lo que entró, ni un céntimo más "
                    f"({_euros(la_factura_leida.get('cobrado'))})",
                )

                # **El reenvío del móvil**: el mismo cobro, otra vez, con la misma clave.
                repetido = cliente.post(
                    "/api/cobros",
                    headers=cabeceras,
                    json={
                        "fecha": "2026-07-20",
                        "importe": "40.00",
                        "factura_emitida_id": identificador_de_la_factura,
                        "clave_de_reenvio": "cobro-parcial-40",
                    },
                )
                comprobar(
                    repetido.status_code in (200, 201),
                    f"y volver a mandar el mismo cobro se contesta, no revienta "
                    f"({repetido.status_code}: {repetido.text[:110]})",
                )
                la_factura_repetida = cliente.get(
                    f"/api/facturas-emitidas/{identificador_de_la_factura}", headers=cabeceras
                ).json()
                comprobar(
                    _euros(la_factura_repetida.get("cobrado")) == "40.00",
                    f"y no se ha cobrado dos veces ({_euros(la_factura_repetida.get('cobrado'))})",
                )
                cuantas_despues = len(
                    cliente.get("/api/facturas-emitidas", headers=cabeceras).json()
                )
                comprobar(
                    cuantas_despues == cuantas_antes + 1,
                    f"y cobrar no ha creado ninguna factura de más "
                    f"({cuantas_antes} → {cuantas_despues}; se esperaba una sola nueva)",
                )

    # ── La tabla del dinero: el pie tiene que hablar del mismo conjunto que las filas ──
    la_tabla = cliente.get("/api/ventas/tabla", headers=cabeceras)
    comprobar(
        la_tabla.status_code == 200,
        f"la tabla de las ventas y su dinero se puede mirar ({la_tabla.status_code})",
    )
    if la_tabla.status_code == 200:
        tabla_del_dinero = la_tabla.json()
        comprobar(
            bool(tabla_del_dinero.get("pie")),
            f"y trae su pie con el conjunto filtrado ({str(tabla_del_dinero.get('pie'))[:70]!r})",
        )
        comprobar(
            tabla_del_dinero.get("filtradas") == tabla_del_dinero.get("total"),
            "y sin filtros puestos, lo filtrado es todo "
            f"({tabla_del_dinero.get('filtradas')} de {tabla_del_dinero.get('total')})",
        )
        comprobar(
            len(tabla_del_dinero.get("filas", [])) == tabla_del_dinero.get("filtradas"),
            "y el pie cuenta las mismas filas que se enseñan "
            f"({len(tabla_del_dinero.get('filas', []))} filas, "
            f"{tabla_del_dinero.get('filtradas')} filtradas)",
        )

    cliente.close()
    print()
    if FALLOS:
        print(f"RESULTADO: {len(FALLOS)} comprobaciones han fallado")
        for fallo in FALLOS:
            print(f"  - {fallo}")
        return 1
    print("RESULTADO: todo correcto")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
