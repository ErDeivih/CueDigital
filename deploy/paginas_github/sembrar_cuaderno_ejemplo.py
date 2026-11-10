"""Siembra el **cuaderno** de la finca de ejemplo contra la app publicada (10/11/2026).

QUÉ HACE
========

Deja la finca de ejemplo con contenido realista, **contra la app que ya está publicada** (no contra
una base de datos local). En este orden:

1. **Completa las cinco tierras con los datos REALES del SIGPAC.** Busca el recinto por su
   referencia (`POST /api/sigpac/buscar`) y actualiza la tierra (`PUT /api/parcelas/{id}`) con la
   **superficie**, el **uso** y la **pendiente** que devuelve el SIGPAC. La **geometría no se toca**:
   se comprueba, antes y después, que el dibujo de la tierra es exactamente el mismo.
2. **Da de alta los apuntes del cuaderno** con fechas de los últimos 60 días (hoy es 10/11/2026):
   tres tratamientos (en tres tierras distintas, con plazo de seguridad y de reentrada), dos
   abonos, dos labores (una preparación y una siembra) y una cosecha.
3. **Comprueba por la API** que todo está: la ficha de cada tierra, el resumen, el calendario y la
   foto de las cinco tierras (`GET /api/mapa/tierra/{id}.png`).
4. **Imprime el resumen** con los identificadores y las fechas, y sale con 1 si algo ha fallado.

ES IDEMPOTENTE: ejecutarlo dos veces no duplica nada. Las tierras que ya están completas no se
vuelven a tocar, y los apuntes se reconocen por su marca (`MARCADOR`) o por su terna
(tierra, fecha, tipo), así que la segunda pasada solo comprueba.

DE DÓNDE SALE CADA DATO (la regla de la casa: nada se inventa)
==============================================================

· **Las referencias de las tierras** son las del cliente de Salamanca, las mismas que usa
  `backend/scripts/pintar_las_parcelas_del_cliente.py`, sacadas del GeoPackage real del SIGPAC.
· **La superficie, el uso y la pendiente** los dice el SIGPAC en la respuesta de la búsqueda. No se
  escriben a mano.
· **Los productos fitosanitarios** son entradas REALES del listado oficial de FEGA
  (`data/fega/mapa_productos_fitosanitarios.xlsx`): su nombre comercial, su número de registro, su
  composición y su estado «Vigente» están copiados de ahí. El **plazo de seguridad de 15 días** y el
  **plazo de reentrada de 2 días** son los del encargo para esta demo (pidió «15 y 2» para que el
  cuaderno guiado tenga algo que avisar); no son un dato de la etiqueta y por eso van aquí, a la
  vista, y no dentro del catálogo de productos.
· **Los abonos** son denominaciones corrientes de abono mineral («Complejo NPK 8-15-15», «Nitrato
  amónico 33,5 %»), no una marca comercial: lo que se sabe es la riqueza, y la riqueza se declara.
· **La cosecha** se apunta **sin kilos**: no hay un dato del que salgan, y un número inventado en el
  cuaderno es peor que un hueco. (`cantidad_kg` es opcional en `CosechaEntrada`.)
· **Nada de datos personales**: ni nombres, ni NIF, ni teléfonos, ni correos de personas. Los apuntes
  son de la finca.

DÓNDE SE HA MIRADO EL CONTRATO
==============================

· `backend/app/schemas.py`: `ParcelaEntrada`, `ProductoEntrada`, `FertilizanteEntrada`,
  `TratamientoEntrada`, `FertilizacionEntrada`, `LaborEntrada` y `CosechaEntrada`.
· `backend/app/routers/parcelas.py`: el `PUT` y `_columnas_que_una_correccion_no_toca` (que es lo
  que deja quieta la geometría).
· `backend/web/nuevo/modelo.js`: `cuerpoDelTratamiento`, `cuerpoDelAbono` y `cuerpoDelApunte`, que
  es cómo manda estos mismos apuntes la pantalla.

USO
===

    python deploy/paginas_github/sembrar_cuaderno_ejemplo.py
    python deploy/paginas_github/sembrar_cuaderno_ejemplo.py https://servidor.tail4263a0.ts.net:8443

Por defecto va a `https://servidor.tail4263a0.ts.net:8443`. La dirección usa el certificado de
Tailscale, que no lo firma una autoridad pública, así que la verificación del certificado va
apagada **a propósito** (es el mismo servidor de casa, por la red privada de Tailscale).
"""

from __future__ import annotations

import datetime as dt
import re
import sys
import time

import httpx

# La app publicada de la finca de ejemplo. Es la del encargo del 10/11/2026.
URL_POR_DEFECTO = "https://servidor.tail4263a0.ts.net:8443"

# La cuenta de ejemplo que ya está dada de alta en ese servidor.
CORREO = "demo@cuedigital.local"
CLAVE = "cuaderno-demo-2026"

# Hoy es 10/11/2026 (el día del encargo). Se guarda fijo para que la comprobación del calendario y
# las fechas de los apuntes no dependan de qué día se ejecute el guion: es una demo con fecha.
HOY_DE_LA_DEMO = dt.date(2026, 11, 10)
DIAS_DE_HISTORIA = 60

# La marca que llevan los apuntes de este guion en `observaciones`. Es lo que permite ejecutarlo dos
# veces sin duplicar: si ya existe un apunte con esta marca, no se vuelve a crear.
MARCADOR = "Apunte de ejemplo de la finca demo (contenido de demostración)"

# Las cinco tierras del cliente de Salamanca. Las referencias NO se inventan: son las del GeoPackage
# real del SIGPAC, las mismas que usa `backend/scripts/pintar_las_parcelas_del_cliente.py`.
# «El Visor» va con la referencia del visor (seis números, sin recinto), como la copiaría el
# agricultor del visor del SIGPAC; el recinto se saca de la búsqueda.
PARCELAS = (
    ("El Prado", "37-70-0-0-503-51-1"),
    ("El Alto", "37-70-0-0-501-84-1"),
    ("La Vega", "37-70-0-0-501-82-2"),
    ("Las Eras", "37-70-0-0-501-80-1"),
    ("El Visor", "37-70-0-0-501-80"),
)

# Los plazos del cuaderno guiado. **Son los que pidió el encargo para la demo** (15 y 2 días), no un
# dato leído de la etiqueta: van en el producto (el plazo de seguridad se copia del producto al
# apunte, así lo hace `servicios.preparar_tratamiento`) y en cada apunte (la reentrada).
PLAZO_SEGURIDAD_DIAS = 15
PLAZO_REENTRADA_DIAS = 2

# Los tres productos fitosanitarios, con los datos REALES del listado oficial de FEGA
# (`data/fega/mapa_productos_fitosanitarios.xlsx`, comprobado el 10/11/2026):
#
#   · «CLINIC TF»    · ES-01098 · GLIFOSATO 36% (SAL ISOPROPILAMINA) [SL] P/V · Vigente
#   · «BUNAZOL 250»  · 24112    · TEBUCONAZOL 25% [EW] P/V                    · Vigente
#   · «ATRAPA»       · 25637    · LAMBDA CIHALOTRIN 10% [CS] P/V              · Vigente
#
# La dosis es la que se apunta en la demo (una aplicación normal); la dosis máxima de etiqueta NO se
# rellena porque el listado oficial no la trae y un tope inventado cerraría la puerta o dejaría pasar
# una barbaridad. Donde no consta, queda vacío (regla de la casa).
PRODUCTOS = (
    {
        "clave": "ES-01098",
        "nombre_comercial": "CLINIC TF",
        "numero_registro": "ES-01098",
        "materia_activa": "Glifosato (sal isopropilamina)",
        "tipo_producto": "herbicida",
        "dosis": 2.0,
        "unidad_dosis": "L/ha",
    },
    {
        "clave": "24112",
        "nombre_comercial": "BUNAZOL 250",
        "numero_registro": "24112",
        "materia_activa": "Tebuconazol",
        "tipo_producto": "fungicida",
        "dosis": 0.5,
        "unidad_dosis": "L/ha",
    },
    {
        "clave": "25637",
        "nombre_comercial": "ATRAPA",
        "numero_registro": "25637",
        "materia_activa": "Lambda cihalotrin",
        "tipo_producto": "insecticida",
        "dosis": 0.15,
        "unidad_dosis": "L/ha",
    },
)

# Los dos abonos (denominaciones corrientes, con su riqueza; no son una marca).
ABONOS = (
    {
        "nombre": "Complejo NPK 8-15-15",
        "tipo": "mineral",
        "riqueza_n": 8,
        "riqueza_p": 15,
        "riqueza_k": 15,
        "aplicaciones": (
            {
                "parcela": "El Prado",
                "fecha": "2026-09-22",
                "dosis_kg_ha": 350,
                "tipo_fertilizacion": "fondo",
                # OJO: `fertilizaciones.momento` es una columna de 30 caracteres y el
                # esquema rechaza lo que no cabe (en PostgreSQL perdería la operación). Los dos
                # textos de aquí caben; si se alargan, el alta contesta 422.
                "momento": "Fondo antes de sembrar",
            },
        ),
    },
    {
        "nombre": "Nitrato amónico 33,5 %",
        "tipo": "mineral",
        "riqueza_n": 33.5,
        "riqueza_p": None,
        "riqueza_k": None,
        "aplicaciones": (
            {
                "parcela": "El Alto",
                "fecha": "2026-10-20",
                "dosis_kg_ha": 250,
                "tipo_fertilizacion": "cobertera",
                "momento": "Cobertera del cereal",
            },
        ),
    },
)

# Tres tratamientos en tres tierras distintas, con fechas de hace 2, 3 y 4 días. La justificación es
# lo que se ve en el campo (no lleva nombres de personas ni datos de nadie).
TRATAMIENTOS = (
    {
        "parcela": "El Prado",
        "fecha": "2026-11-06",
        "producto": "ES-01098",
        "plaga": "Hierba",
        "justificacion": "Hierba en el rastrojo; se trata antes de sembrar",
    },
    {
        "parcela": "El Alto",
        "fecha": "2026-11-07",
        "producto": "24112",
        "plaga": "Enfermedad de la hoja",
        "justificacion": "Manchas en la hoja; se trata la parcela",
    },
    {
        "parcela": "La Vega",
        "fecha": "2026-11-08",
        "producto": "25637",
        "plaga": "Pulgón",
        "justificacion": "Pulgón en el pasto; se trata el brote",
    },
)

# Dos labores: una preparación del terreno y una siembra (en la misma tierra, que es como se hace).
LABORES = (
    {
        "parcela": "El Visor",
        "tipo": "laboreo",
        "subtipo": "cultivador",
        "fecha": "2026-09-28",
        "observaciones": "Preparación del terreno antes de sembrar",
    },
    {
        "parcela": "El Visor",
        "tipo": "siembra",
        "subtipo": None,
        "fecha": "2026-10-03",
        "cultivo": "Trigo blando",
        "dosis_siembra_kg_ha": 180,
        "observaciones": "Siembra de trigo blando",
    },
)

# La cosecha. Se apunta sin kilos: `cantidad_kg` es opcional y no hay un dato del que salga, así que
# se queda vacío en vez de inventarlo. La tierra no lleva tratamientos, así que no hay plazo de
# seguridad que incumplir.
COSECHA = {"parcela": "Las Eras", "fecha": "2026-10-09", "producto": "Maíz"}

CABECERAS_PNG = b"\x89PNG\r\n\x1a\n"


# --------------------------------------------------------------------------
# La puerta: login, reintentos y lectura de respuestas
# --------------------------------------------------------------------------


def _pantalla(texto: str = "") -> None:
    print(texto)


def _fallo(resultado: dict, mensaje: str) -> None:
    resultado["fallos"].append(mensaje)
    _pantalla(f"  FALLO: {mensaje}")


def _numero(valor) -> float | None:
    return None if valor is None else float(valor)


def _areas_iguales(uno, otro) -> bool:
    """Compara dos números de la API sin pelearse por el último decimal del JSON."""
    if uno is None or otro is None:
        return uno is otro
    return abs(float(uno) - float(otro)) < 1e-6


class Cliente:
    """HTTP contra la app, con reintentos para cuando el servidor se está reiniciando.

    **Los reintentos de escritura son prudentes a propósito**: si un `POST` se queda esperando y no
    se sabe si llegó a guardarse, NO se reintenta (reintentarlo podría duplicar). Se dice lo que ha
    pasado y se puede volver a ejecutar el guion, que es idempotente.
    """

    def __init__(self, url: str) -> None:
        self.cliente = httpx.Client(
            base_url=url.rstrip("/"),
            timeout=300.0,
            verify=False,  # el certificado es de Tailscale, no de una autoridad pública
            follow_redirects=True,
        )
        self.cabeceras: dict[str, str] = {}

    def pide(self, metodo: str, ruta: str, *, escribir: bool = False, **kwargs):
        intentos = 4 if escribir else 5
        for intento in range(1, intentos + 1):
            try:
                respuesta = self.cliente.request(metodo, ruta, headers=self.cabeceras, **kwargs)
            except httpx.ConnectError as error:
                if intento == intentos:
                    raise
                _pantalla(f"  (el servidor no contesta: {error}; reintento {intento}/{intentos})")
                time.sleep(2 * intento)
                continue
            except httpx.TimeoutException as error:
                if escribir:
                    raise RuntimeError(
                        f"{metodo} {ruta}: se ha quedado esperando y no se sabe si se guardó "
                        f"({error}). Vuelve a ejecutar el guion: no duplicará nada."
                    ) from error
                if intento == intentos:
                    raise
                _pantalla(f"  (tarda demasiado: {error}; reintento {intento}/{intentos})")
                time.sleep(2 * intento)
                continue
            # 502/503/504 es el proxy diciendo que la app no está levantada: es lo que se ve cuando
            # el servidor se está actualizando. En una escritura, un 502 no ha llegado a la app.
            temporales = (502, 504) if escribir else (502, 503, 504)
            if respuesta.status_code in temporales and intento < intentos:
                _pantalla(
                    f"  ({metodo} {ruta}: {respuesta.status_code}; el servidor está arrancando. "
                    f"reintento {intento}/{intentos})"
                )
                time.sleep(2 * intento)
                continue
            return respuesta
        raise RuntimeError(f"{metodo} {ruta}: no ha contestado después de {intentos} intentos")

    def leer(self, ruta: str, **kwargs):
        respuesta = self.pide("GET", ruta, **kwargs)
        if respuesta.status_code != 200:
            raise RuntimeError(f"GET {ruta}: {respuesta.status_code} {respuesta.text[:400]}")
        return respuesta

    def escribir(self, metodo: str, ruta: str, cuerpo: dict, *, vale: tuple[int, ...] = (200, 201)):
        respuesta = self.pide(metodo, ruta, escribir=True, json=cuerpo)
        if respuesta.status_code not in vale:
            raise RuntimeError(
                f"{metodo} {ruta}: {respuesta.status_code} {respuesta.text[:600]}"
            )
        return respuesta


def entrar(cliente: Cliente) -> None:
    respuesta = cliente.pide(
        "POST", "/api/cuenta/entrar", json={"correo": CORREO, "clave": CLAVE}
    )
    if respuesta.status_code != 200:
        raise RuntimeError(
            f"No se puede entrar con la cuenta de ejemplo: {respuesta.status_code} "
            f"{respuesta.text[:300]}"
        )
    cliente.cabeceras = {"Authorization": f"Bearer {respuesta.json()['token']}"}
    _pantalla("cuenta: dentro con la cuenta de ejemplo")


def campana_de_2026(cliente: Cliente) -> dict:
    """La campaña de 2026, que es la de los apuntes. Si no está, se dice y no se inventa."""
    campanas = cliente.leer("/api/campanas").json()
    for campana in campanas:
        if campana.get("anio") == 2026:
            return campana
    raise RuntimeError(
        "No está la campaña de 2026 en el servidor, y los apuntes de este guion son de 2026. "
        "No se inventa una campaña."
    )


def parcelas_por_alias(cliente: Cliente) -> dict:
    return {parcela["alias"]: parcela for parcela in cliente.leer("/api/parcelas").json()}


# --------------------------------------------------------------------------
# 1. Las tierras: los datos del SIGPAC sin tocar la geometría
# --------------------------------------------------------------------------


def _recinto_de_la_referencia(referencia: str, recintos: list[dict]) -> dict | None:
    """Elige el recinto al que apunta la referencia, y **nunca adivina**.

    La búsqueda por una parcela devuelve **todos** los trozos de esa parcela (La Vega, por ejemplo,
    tiene cuatro). Si la referencia trae el número de recinto (siete números), se elige ese. Si no
    lo trae (la del visor, seis números) solo vale que haya uno; con varios, se para y se dice.
    """
    numeros = [int(numero) for numero in re.findall(r"\d+", referencia)]
    if len(numeros) >= 7:
        pedido = numeros[6]
        for recinto in recintos:
            if recinto.get("recinto") == pedido:
                return recinto
        return None
    if len(recintos) == 1:
        return recintos[0]
    return None


def _cuerpo_del_put(parcela: dict, recinto: dict) -> dict:
    """El cuerpo del `PUT`, con lo que manda el SIGPAC y lo que ya tenía la tierra.

    Los campos que no se mandan no se tocan: la geometría, el centro y la superficie del recinto
    (`superficie_sigpac_ha`) **no están en `ParcelaEntrada`**, así que `_columnas_que_una_correccion_no_toca`
    los deja como estaban. Eso es justo lo que pide el encargo: completar sin pisar la forma.
    """
    return {
        "alias": parcela["alias"],
        "ref_sigpac": recinto["referencia"],
        # Lo que ya sabía la tierra se devuelve tal cual (si estaba vacío, el PUT lo completa solo a
        # partir de la referencia: el código INE, el polígono, la parcela y el recinto).
        "provincia": parcela.get("provincia") or "",
        "municipio": parcela.get("municipio") or "",
        "codigo_ine": parcela.get("codigo_ine"),
        "poligono": parcela.get("poligono"),
        "numero_parcela": parcela.get("numero_parcela"),
        "numero_recinto": parcela.get("numero_recinto"),
        "agregado": parcela.get("agregado") or 0,
        "zona": parcela.get("zona") or 0,
        "referencia_catastral": parcela.get("referencia_catastral"),
        "sistema": parcela.get("sistema"),
        "masa_agua_cerca": parcela.get("masa_agua_cerca"),
        "captacion_consumo_humano": parcela.get("captacion_consumo_humano"),
        # La zona de nitratos **no se copia**: se manda `None` («no lo sé») a propósito para que la
        # puerta la vuelva a resolver con el listado oficial (ahora que el PUT completa el código INE
        # con la referencia). Si se mandara el valor que hubiera, un `False` viejo taparía al listado.
        "zona_vulnerable_nitratos": None,
        # Y lo nuevo, que es lo que manda el SIGPAC.
        "superficie_ha": recinto["superficie_ha"],
        "superficie_oficial": True,
        "uso_sigpac": recinto["uso_sigpac"],
        "pendiente_pct": recinto["pendiente_pct"],
    }


def completar_las_tierras(cliente: Cliente, resultado: dict) -> dict:
    """Completa las cinco tierras con la superficie, el uso y la pendiente del SIGPAC."""
    parcelas = parcelas_por_alias(cliente)
    completas: dict[str, dict] = {}

    for alias, referencia in PARCELAS:
        parcela = parcelas.get(alias)
        if parcela is None:
            _fallo(
                resultado,
                f"la tierra «{alias}» no está en la finca. Este guion completa las cinco tierras "
                "que ya existen; no da de alta tierras nuevas.",
            )
            continue

        ya_completa = all(
            parcela.get(campo) is not None
            for campo in ("ref_sigpac", "superficie_ha", "uso_sigpac", "pendiente_pct")
        )
        if ya_completa:
            completas[alias] = parcela
            _pantalla(
                f"tierra «{alias}»: ya tenía los datos del SIGPAC "
                f"({parcela['superficie_ha']} ha, uso {parcela['uso_sigpac']}, "
                f"pendiente {parcela['pendiente_pct']} %) · no se toca"
            )
            resultado["parcelas"].append(
                {
                    "alias": alias,
                    "id": parcela["id"],
                    "superficie_ha": parcela["superficie_ha"],
                    "uso_sigpac": parcela["uso_sigpac"],
                    "pendiente_pct": parcela["pendiente_pct"],
                    "accion": "ya estaba",
                }
            )
            continue

        try:
            busqueda = cliente.escribir(
                "POST",
                "/api/sigpac/buscar",
                {"referencia": referencia},
                vale=(200,),
            ).json()
        except RuntimeError as error:
            _fallo(resultado, f"tierra «{alias}»: no se ha podido preguntar al SIGPAC ({error})")
            continue

        recintos = busqueda.get("recintos") or []
        recinto = _recinto_de_la_referencia(referencia, recintos)
        if recinto is None:
            _fallo(
                resultado,
                f"tierra «{alias}»: la búsqueda por {referencia} devuelve {len(recintos)} trozos y "
                "no se puede decir cuál es el suyo. No se elige a ciegas.",
            )
            continue

        dibujo_antes = parcela.get("dibujo")
        try:
            respuesta = cliente.escribir(
                "PUT", f"/api/parcelas/{parcela['id']}", _cuerpo_del_put(parcela, recinto)
            )
        except RuntimeError as error:
            _fallo(resultado, f"tierra «{alias}»: no se ha podido actualizar ({error})")
            continue

        guardada = respuesta.json()
        problemas = []
        for campo, esperado in (
            ("ref_sigpac", recinto["referencia"]),
            ("superficie_ha", recinto["superficie_ha"]),
            ("uso_sigpac", recinto["uso_sigpac"]),
            ("pendiente_pct", recinto["pendiente_pct"]),
        ):
            obtenido = guardada.get(campo)
            if campo in ("superficie_ha", "pendiente_pct"):
                if not _areas_iguales(obtenido, esperado):
                    problemas.append(f"{campo}={obtenido} (el SIGPAC dijo {esperado})")
            elif obtenido != esperado:
                problemas.append(f"{campo}={obtenido} (el SIGPAC dijo {esperado})")
        # La prueba de que la forma no se ha pisado: el dibujo se calcula de la geometría, así que si
        # cambia, ha cambiado la geometría.
        if dibujo_antes and guardada.get("dibujo") != dibujo_antes:
            problemas.append("el dibujo de la tierra ha cambiado: la geometría NO se ha respetado")
        if not guardada.get("dibujo"):
            problemas.append("la tierra se ha quedado sin dibujo")

        if problemas:
            _fallo(resultado, f"tierra «{alias}»: " + "; ".join(problemas))
            continue

        completas[alias] = guardada
        resultado["parcelas"].append(
            {
                "alias": alias,
                "id": guardada["id"],
                "referencia": guardada["ref_sigpac"],
                "superficie_ha": guardada["superficie_ha"],
                "uso_sigpac": guardada["uso_sigpac"],
                "pendiente_pct": guardada["pendiente_pct"],
                "accion": "completada",
            }
        )
        _pantalla(
            f"tierra «{alias}»: {guardada['superficie_ha']} ha · uso {guardada['uso_sigpac']} · "
            f"pendiente {guardada['pendiente_pct']} % · forma intacta"
        )

    return completas


# --------------------------------------------------------------------------
# 2. El catálogo que hace falta para poder apuntar (productos y abonos)
# --------------------------------------------------------------------------


def _normaliza_registro(numero: str | None) -> str:
    return "".join((numero or "").split()).upper()


def _producto_guardable(producto: dict) -> dict:
    """El cuerpo del producto, con los plazos de la demo y el estado del registro oficial."""
    return {
        "nombre_comercial": producto["nombre_comercial"],
        "numero_registro": producto["numero_registro"],
        "materia_activa": producto["materia_activa"],
        "tipo_producto": producto["tipo_producto"],
        "unidad_dosis": producto["unidad_dosis"],
        "plazo_seguridad_dias": PLAZO_SEGURIDAD_DIAS,
        # «Vigente» en el listado oficial de FEGA. `True` es lo que dice ese listado, no una
        # suposición: sin esto, el alta avisaría de que la autorización no está comprobada.
        "autorizado": True,
    }


def asegurar_productos(cliente: Cliente, resultado: dict) -> dict:
    """Deja los tres productos en el catálogo de la finca y los devuelve por su número de registro."""
    existentes = cliente.leer("/api/productos").json()
    por_registro = {
        _normaliza_registro(producto.get("numero_registro")): producto
        for producto in existentes
        if producto.get("numero_registro")
    }
    productos: dict[str, dict] = {}

    for producto in PRODUCTOS:
        guardado = por_registro.get(_normaliza_registro(producto["numero_registro"]))
        if guardado is None:
            try:
                respuesta = cliente.escribir("POST", "/api/productos", _producto_guardable(producto))
            except RuntimeError as error:
                _fallo(resultado, f"producto «{producto['nombre_comercial']}»: {error}")
                continue
            guardado = respuesta.json()
            _pantalla(
                f"producto «{guardado['nombre_comercial']}»: alta · id={guardado['id']} · "
                f"registro {guardado['numero_registro']} · plazo {guardado['plazo_seguridad_dias']} días"
            )
            resultado["productos"].append(
                {"id": guardado["id"], "nombre": guardado["nombre_comercial"], "accion": "creado"}
            )
        else:
            # Si ya existía pero sin el plazo (porque lo creó otro camino), se le pone el del
            # encargo. Se hace con un PUT con lo que devolvió la API, para no borrar nada.
            if guardado.get("plazo_seguridad_dias") != PLAZO_SEGURIDAD_DIAS:
                cuerpo = {
                    campo: guardado.get(campo)
                    for campo in (
                        "nombre_comercial",
                        "tipo_producto",
                        "numero_registro",
                        "materia_activa",
                        "dosis_maxima",
                        "unidad_dosis",
                        "plazo_seguridad_dias",
                        "lote",
                        "fecha_caducidad",
                        "cantidad_comprada",
                        "unidad_compra",
                        "fecha_compra",
                        "proveedor",
                        "autorizado",
                        "permitido_ecologico",
                        "autorizacion_excepcional",
                        "autorizacion_hasta",
                        "foto_etiqueta",
                    )
                }
                cuerpo["plazo_seguridad_dias"] = PLAZO_SEGURIDAD_DIAS
                try:
                    guardado = cliente.escribir(
                        "PUT", f"/api/productos/{guardado['id']}", cuerpo
                    ).json()
                except RuntimeError as error:
                    _fallo(resultado, f"producto «{producto['nombre_comercial']}»: {error}")
                    continue
                _pantalla(
                    f"producto «{guardado['nombre_comercial']}»: se le ha puesto el plazo de "
                    f"{PLAZO_SEGURIDAD_DIAS} días (id={guardado['id']})"
                )
                resultado["productos"].append(
                    {"id": guardado["id"], "nombre": guardado["nombre_comercial"], "accion": "corregido"}
                )
            else:
                _pantalla(
                    f"producto «{guardado['nombre_comercial']}»: ya estaba · id={guardado['id']}"
                )
                resultado["productos"].append(
                    {"id": guardado["id"], "nombre": guardado["nombre_comercial"], "accion": "ya estaba"}
                )
        productos[producto["clave"]] = guardado

    return productos


def asegurar_abonos(cliente: Cliente, resultado: dict) -> dict:
    """Deja los dos abonos en el catálogo de la finca y los devuelve por su nombre."""
    existentes = {abono.get("nombre"): abono for abono in cliente.leer("/api/fertilizantes").json()}
    abonos: dict[str, dict] = {}

    for abono in ABONOS:
        guardado = existentes.get(abono["nombre"])
        if guardado is None:
            cuerpo = {
                "nombre": abono["nombre"],
                "tipo": abono["tipo"],
                "riqueza_n": abono["riqueza_n"],
                "riqueza_p": abono["riqueza_p"],
                "riqueza_k": abono["riqueza_k"],
            }
            try:
                guardado = cliente.escribir("POST", "/api/fertilizantes", cuerpo).json()
            except RuntimeError as error:
                _fallo(resultado, f"abono «{abono['nombre']}»: {error}")
                continue
            _pantalla(
                f"abono «{guardado['nombre']}»: alta · id={guardado['id']} · "
                f"riqueza N {guardado.get('riqueza_n')} · P {guardado.get('riqueza_p')} · "
                f"K {guardado.get('riqueza_k')}"
            )
            resultado["abonos"].append({"id": guardado["id"], "nombre": guardado["nombre"], "accion": "creado"})
        else:
            _pantalla(f"abono «{guardado['nombre']}»: ya estaba · id={guardado['id']}")
            resultado["abonos"].append({"id": guardado["id"], "nombre": guardado["nombre"], "accion": "ya estaba"})
        abonos[abono["nombre"]] = guardado

    return abonos


# --------------------------------------------------------------------------
# 3. Los apuntes del cuaderno
# --------------------------------------------------------------------------


def _fecha(cadena: str) -> dt.date:
    return dt.date.fromisoformat(cadena)


def _superficie_para_apuntar(parcela: dict) -> float:
    """La superficie del apunte, sin pasarse de la de la tierra (la API lo bloquea si se pasa)."""
    return round(float(parcela["superficie_ha"]), 2)


def crear_tratamientos(cliente: Cliente, campana: dict, parcelas: dict, productos: dict, resultado: dict) -> None:
    existentes = cliente.leer("/api/tratamientos", params={"campana_id": campana["id"]}).json()
    # La dosis y la unidad son de la definición del guion (el catálogo las guarda en el producto, pero
    # la respuesta no devuelve la dosis de la aplicación: eso es de cada apunte).
    definiciones = {producto["clave"]: producto for producto in PRODUCTOS}

    for plan in TRATAMIENTOS:
        parcela = parcelas.get(plan["parcela"])
        producto = productos.get(plan["producto"])
        definicion = definiciones.get(plan["producto"])
        if parcela is None or producto is None or definicion is None:
            _fallo(resultado, f"tratamiento en «{plan['parcela']}»: falta la tierra o el producto")
            continue

        ya = any(
            apunte.get("parcela_id") == parcela["id"]
            and apunte.get("fecha") == plan["fecha"]
            and MARCADOR in (apunte.get("observaciones") or "")
            for apunte in existentes
        )
        if ya:
            _pantalla(f"tratamiento «{plan['parcela']}» {plan['fecha']}: ya estaba · no se duplica")
            resultado["tratamientos"].append(
                {
                    "parcela": plan["parcela"],
                    "fecha": plan["fecha"],
                    "accion": "ya estaba",
                }
            )
            continue

        cuerpo = {
            "campana_id": campana["id"],
            "tipo": "parcela",
            "fecha": plan["fecha"],
            "parcela_id": parcela["id"],
            "superficie_tratada_ha": _superficie_para_apuntar(parcela),
            "producto_id": producto["id"],
            "dosis": definicion["dosis"],
            "unidad_dosis": definicion["unidad_dosis"],
            "plaga": plan["plaga"],
            "justificacion": plan["justificacion"],
            "plazo_reentrada_dias": PLAZO_REENTRADA_DIAS,
            "observaciones": MARCADOR,
        }
        try:
            guardado = cliente.escribir("POST", "/api/tratamientos", cuerpo).json()
        except RuntimeError as error:
            _fallo(resultado, f"tratamiento «{plan['parcela']}» {plan['fecha']}: {error}")
            continue

        problemas = []
        if guardado.get("plazo_seguridad_dias") != PLAZO_SEGURIDAD_DIAS:
            problemas.append(
                f"plazo de seguridad {guardado.get('plazo_seguridad_dias')} "
                f"(se esperaba {PLAZO_SEGURIDAD_DIAS})"
            )
        if guardado.get("plazo_reentrada_dias") != PLAZO_REENTRADA_DIAS:
            problemas.append(
                f"plazo de reentrada {guardado.get('plazo_reentrada_dias')} "
                f"(se esperaba {PLAZO_REENTRADA_DIAS})"
            )
        fin_esperado = (_fecha(plan["fecha"]) + dt.timedelta(days=PLAZO_SEGURIDAD_DIAS)).isoformat()
        if guardado.get("fecha_fin_plazo_seguridad") != fin_esperado:
            problemas.append(
                f"fin de plazo {guardado.get('fecha_fin_plazo_seguridad')} (se esperaba {fin_esperado})"
            )
        if problemas:
            _fallo(resultado, f"tratamiento «{plan['parcela']}»: " + "; ".join(problemas))
            continue

        resultado["tratamientos"].append(
            {
                "id": guardado["id"],
                "parcela": plan["parcela"],
                "fecha": plan["fecha"],
                "producto": guardado.get("producto_nombre"),
                "plazo_seguridad_dias": guardado.get("plazo_seguridad_dias"),
                "fecha_fin_plazo_seguridad": guardado.get("fecha_fin_plazo_seguridad"),
                "plazo_reentrada_dias": guardado.get("plazo_reentrada_dias"),
                "accion": "creado",
            }
        )
        _pantalla(
            f"tratamiento «{plan['parcela']}» {plan['fecha']}: id={guardado['id']} · "
            f"{guardado.get('producto_nombre')} · plazo de seguridad hasta "
            f"{guardado.get('fecha_fin_plazo_seguridad')} · reentrada {PLAZO_REENTRADA_DIAS} días"
        )


def crear_fertilizaciones(cliente: Cliente, campana: dict, parcelas: dict, abonos: dict, resultado: dict) -> None:
    existentes = cliente.leer("/api/fertilizaciones", params={"campana_id": campana["id"]}).json()

    for abono in ABONOS:
        guardado_abono = abonos.get(abono["nombre"])
        if guardado_abono is None:
            continue
        for aplicacion in abono["aplicaciones"]:
            parcela = parcelas.get(aplicacion["parcela"])
            if parcela is None:
                _fallo(resultado, f"abono en «{aplicacion['parcela']}»: falta la tierra")
                continue

            # La respuesta de un abono **no devuelve `fertilizante_id`** (`FertilizacionSalida`
            # trae el nombre y no el identificador), así que el abono se reconoce por su terna
            # (tierra, fecha y nombre del abono), que es lo que lo identifica de verdad. Con el
            # identificador la comparación sería siempre con `None` y se duplicaría el apunte.
            ya = any(
                apunte.get("parcela_id") == parcela["id"]
                and apunte.get("fecha") == aplicacion["fecha"]
                and apunte.get("fertilizante_nombre") == guardado_abono["nombre"]
                for apunte in existentes
            )
            if ya:
                _pantalla(
                    f"abono «{aplicacion['parcela']}» {aplicacion['fecha']}: ya estaba · no se duplica"
                )
                resultado["fertilizaciones"].append(
                    {"parcela": aplicacion["parcela"], "fecha": aplicacion["fecha"], "accion": "ya estaba"}
                )
                continue

            superficie = _superficie_para_apuntar(parcela)
            cantidad_total = round(superficie * aplicacion["dosis_kg_ha"], 3)
            cuerpo = {
                "campana_id": campana["id"],
                "fecha": aplicacion["fecha"],
                "parcela_id": parcela["id"],
                "superficie_ha": superficie,
                "fertilizante_id": guardado_abono["id"],
                "kg_ha_producto": aplicacion["dosis_kg_ha"],
                "cantidad_total_kg": cantidad_total,
                "unidad_del_producto": "kg",
                "tipo_fertilizacion": aplicacion["tipo_fertilizacion"],
                "momento": aplicacion["momento"],
                "observaciones": MARCADOR,
            }
            try:
                guardado = cliente.escribir("POST", "/api/fertilizaciones", cuerpo).json()
            except RuntimeError as error:
                _fallo(resultado, f"abono «{aplicacion['parcela']}» {aplicacion['fecha']}: {error}")
                continue

            resultado["fertilizaciones"].append(
                {
                    "id": guardado["id"],
                    "parcela": aplicacion["parcela"],
                    "fecha": aplicacion["fecha"],
                    "abono": guardado.get("fertilizante_nombre"),
                    "kg_ha": guardado.get("kg_ha_producto"),
                    "accion": "creado",
                }
            )
            _pantalla(
                f"abono «{aplicacion['parcela']}» {aplicacion['fecha']}: id={guardado['id']} · "
                f"{guardado.get('fertilizante_nombre')} · {guardado.get('kg_ha_producto')} kg/ha · "
                f"{guardado.get('cantidad_total_kg')} kg"
            )


def crear_labores(cliente: Cliente, campana: dict, parcelas: dict, resultado: dict) -> None:
    existentes = cliente.leer("/api/labores", params={"campana_id": campana["id"]}).json()

    for plan in LABORES:
        parcela = parcelas.get(plan["parcela"])
        if parcela is None:
            _fallo(resultado, f"labor en «{plan['parcela']}»: falta la tierra")
            continue

        ya = any(
            apunte.get("parcela_id") == parcela["id"]
            and apunte.get("fecha") == plan["fecha"]
            and apunte.get("tipo") == plan["tipo"]
            and MARCADOR in (apunte.get("observaciones") or "")
            for apunte in existentes
        )
        if ya:
            _pantalla(f"labor «{plan['tipo']}» en «{plan['parcela']}» {plan['fecha']}: ya estaba")
            resultado["labores"].append(
                {"parcela": plan["parcela"], "tipo": plan["tipo"], "fecha": plan["fecha"], "accion": "ya estaba"}
            )
            continue

        superficie = _superficie_para_apuntar(parcela)
        cuerpo = {
            "campana_id": campana["id"],
            "tipo": plan["tipo"],
            "fecha": plan["fecha"],
            "parcela_id": parcela["id"],
            "superficie_ha": superficie,
            "observaciones": f"{plan['observaciones']}. {MARCADOR}",
        }
        if plan["tipo"] == "laboreo":
            if plan.get("subtipo"):
                cuerpo["subtipo"] = plan["subtipo"]
        else:
            cuerpo["cultivo"] = plan.get("cultivo")
            cuerpo["dosis_siembra_kg_ha"] = plan.get("dosis_siembra_kg_ha")
            if plan.get("dosis_siembra_kg_ha") is not None:
                cuerpo["cantidad_semilla_kg"] = round(
                    superficie * plan["dosis_siembra_kg_ha"], 1
                )

        try:
            guardado = cliente.escribir("POST", "/api/labores", cuerpo).json()
        except RuntimeError as error:
            _fallo(resultado, f"labor «{plan['tipo']}» en «{plan['parcela']}»: {error}")
            continue

        resultado["labores"].append(
            {
                "id": guardado["id"],
                "parcela": plan["parcela"],
                "tipo": guardado.get("tipo"),
                "subtipo": guardado.get("subtipo"),
                "fecha": plan["fecha"],
                "accion": "creado",
            }
        )
        etiqueta = guardado.get("tipo")
        if guardado.get("subtipo"):
            etiqueta += f" ({guardado['subtipo']})"
        _pantalla(f"labor «{etiqueta}» en «{plan['parcela']}» {plan['fecha']}: id={guardado['id']}")


def crear_cosecha(cliente: Cliente, campana: dict, parcelas: dict, resultado: dict) -> None:
    parcela = parcelas.get(COSECHA["parcela"])
    if parcela is None:
        _fallo(resultado, f"cosecha en «{COSECHA['parcela']}»: falta la tierra")
        return

    existentes = cliente.leer("/api/labores", params={"campana_id": campana["id"]}).json()
    ya = any(
        apunte.get("parcela_id") == parcela["id"]
        and apunte.get("fecha") == COSECHA["fecha"]
        and apunte.get("tipo") == "cosecha"
        for apunte in existentes
    )
    if ya:
        _pantalla(f"cosecha en «{COSECHA['parcela']}» {COSECHA['fecha']}: ya estaba · no se duplica")
        resultado["cosechas"].append(
            {"parcela": COSECHA["parcela"], "fecha": COSECHA["fecha"], "accion": "ya estaba"}
        )
        return

    cuerpo = {
        "campana_id": campana["id"],
        "fecha": COSECHA["fecha"],
        "parcela_id": parcela["id"],
        "producto": COSECHA["producto"],
        # Sin `cantidad_kg` a propósito: no hay un dato del que salga y no se inventa.
    }
    try:
        respuesta = cliente.escribir("POST", "/api/cosecha", cuerpo)
    except RuntimeError as error:
        _fallo(resultado, f"cosecha en «{COSECHA['parcela']}» {COSECHA['fecha']}: {error}")
        return

    guardado = respuesta.json()
    if not guardado.get("guardado"):
        _fallo(resultado, f"cosecha: la respuesta no dice que se haya guardado ({guardado})")
        return
    resultado["cosechas"].append(
        {
            "id": guardado.get("id"),
            "parcela": COSECHA["parcela"],
            "fecha": COSECHA["fecha"],
            "producto": COSECHA["producto"],
            "accion": "creado",
            "avisos": guardado.get("avisos") or [],
        }
    )
    _pantalla(
        f"cosecha «{COSECHA['producto']}» en «{COSECHA['parcela']}» {COSECHA['fecha']}: "
        f"id={guardado.get('id')} · sin kilos (no se inventan)"
    )


# --------------------------------------------------------------------------
# 4. La comprobación por la API
# --------------------------------------------------------------------------


def _comprobar(resultado: dict, condicion: bool, mensaje: str) -> None:
    resultado["comprobaciones"].append({"correcta": bool(condicion), "mensaje": mensaje})
    _pantalla(f"  {'OK    ' if condicion else 'FALLA '} {mensaje}")
    if not condicion:
        resultado["fallos"].append(mensaje)


def _es_png(datos: bytes) -> bool:
    return datos.startswith(CABECERAS_PNG) and len(datos) > 1000


def comprobar(cliente: Cliente, campana: dict, resultado: dict) -> None:
    _pantalla("\nComprobaciones por la API:")

    # --- Las cinco tierras, con su superficie y su forma ---
    tierras = cliente.leer("/api/nuevo/tierras").json().get("tierras") or []
    _comprobar(resultado, len(tierras) == 5, f"la finca tiene las 5 tierras ({len(tierras)})")
    con_superficie = [tierra for tierra in tierras if tierra.get("superficie_ha") is not None]
    _comprobar(
        resultado,
        len(con_superficie) == len(tierras) and bool(tierras),
        f"las tierras tienen superficie del SIGPAC ({len(con_superficie)}/{len(tierras)})",
    )
    con_forma = [tierra for tierra in tierras if tierra.get("anillo")]
    _comprobar(
        resultado,
        len(con_forma) == len(tierras) and bool(tierras),
        f"las tierras siguen con su contorno ({len(con_forma)}/{len(tierras)})",
    )
    totales = cliente.leer("/api/nuevo/tierras").json().get("totales") or {}
    _comprobar(
        resultado,
        totales.get("ha") is not None,
        f"la finca sabe sus hectáreas ({totales.get('ha')} ha)",
    )

    # --- La foto de cada tierra ---
    fotos_ok = 0
    for tierra in tierras:
        foto = cliente.leer(f"/api/mapa/tierra/{tierra['id']}.png")
        if _es_png(foto.content):
            fotos_ok += 1
    _comprobar(
        resultado,
        fotos_ok == len(tierras) and bool(tierras),
        f"la foto de cada tierra es un PNG ({fotos_ok}/{len(tierras)})",
    )

    # --- La ficha de las tierras tratadas: sus apuntes y el cuaderno guiado ---
    for plan in TRATAMIENTOS:
        tierra = next((t for t in tierras if t.get("alias") == plan["parcela"]), None)
        if tierra is None:
            _comprobar(resultado, False, f"la ficha de «{plan['parcela']}»: no está la tierra")
            continue
        ficha = cliente.leer(f"/api/nuevo/tierra/{tierra['id']}").json()
        resumen_tierra = ficha.get("resumen") or {}
        _comprobar(
            resultado,
            (resumen_tierra.get("n_apuntes") or 0) >= 1,
            f"la ficha de «{plan['parcela']}» tiene sus apuntes "
            f"({resumen_tierra.get('n_apuntes')})",
        )
        _comprobar(
            resultado,
            bool(ficha.get("historial")),
            f"la ficha de «{plan['parcela']}» tiene historial",
        )
        guia = {tarea.get("codigo"): tarea for tarea in (ficha.get("guia") or [])}
        cosecha = guia.get("cosecha") or {}
        reentrada = guia.get("reentrada") or {}
        _comprobar(
            resultado,
            cosecha.get("estado") not in (None, "sin-fecha"),
            f"el cuaderno guiado de «{plan['parcela']}» avisa de la cosecha "
            f"({cosecha.get('estado')}, {cosecha.get('fecha')})",
        )
        _comprobar(
            resultado,
            reentrada.get("estado") not in (None, "sin-fecha"),
            f"el cuaderno guiado de «{plan['parcela']}» avisa de la reentrada "
            f"({reentrada.get('estado')}, {reentrada.get('fecha')})",
        )

    # --- El calendario de los últimos 60 días ---
    desde = (HOY_DE_LA_DEMO - dt.timedelta(days=DIAS_DE_HISTORIA)).isoformat()
    hasta = HOY_DE_LA_DEMO.isoformat()
    calendario = cliente.leer("/api/nuevo/calendario", params={"desde": desde, "hasta": hasta}).json()
    totales_cal = calendario.get("totales") or {}
    por_tipo = totales_cal.get("por_tipo") or {}
    apuntes_esperados = len(TRATAMIENTOS) + sum(
        len(abono["aplicaciones"]) for abono in ABONOS
    ) + len(LABORES) + 1
    _comprobar(
        resultado,
        (totales_cal.get("n") or 0) >= apuntes_esperados,
        f"el calendario del {desde} al {hasta} tiene los apuntes ({totales_cal.get('n')})",
    )
    _comprobar(
        resultado,
        # La cosecha va como su propio tipo en el calendario (`cosecha`), no dentro de `labor`: es
        # una labor en la tabla, pero la agenda la cuenta aparte.
        por_tipo.get("tratamiento", 0) >= len(TRATAMIENTOS)
        and por_tipo.get("abono", 0) >= sum(len(abono["aplicaciones"]) for abono in ABONOS)
        and por_tipo.get("labor", 0) >= len(LABORES)
        and por_tipo.get("cosecha", 0) >= 1,
        f"el calendario los cuenta por tipo ({por_tipo})",
    )

    # --- El resumen de la finca (y lo que le falta del cuaderno) ---
    resumen = cliente.leer("/api/nuevo/resumen").json()
    cuaderno = resumen.get("cuaderno") or {}
    _comprobar(
        resultado,
        "faltan" in cuaderno,
        f"el resumen de la finca responde (le faltan {cuaderno.get('faltan')} datos del cuaderno)",
    )

    # --- Y las listas del cuaderno: cada apunte, UNA sola vez ---
    #
    # Esto es lo que vigila la idempotencia de verdad. No basta con «que haya al menos»: un apunte
    # duplicado es un defecto del cuaderno, porque cuenta dos veces el mismo trabajo. La primera
    # versión buscaba los abonos por `fertilizante_id`, que **la respuesta no devuelve**
    # (`FertilizacionSalida` trae `fertilizante_nombre`), así que la segunda pasada los duplicó.
    # Estas cuentas exactas son las que lo cazan; por eso están aquí.
    parcelas_por_nombre = {parcela["alias"]: parcela for parcela in cliente.leer("/api/parcelas").json()}
    tratamientos = cliente.leer("/api/tratamientos", params={"campana_id": campana["id"]}).json()
    fertilizaciones = cliente.leer("/api/fertilizaciones", params={"campana_id": campana["id"]}).json()
    labores = cliente.leer("/api/labores", params={"campana_id": campana["id"]}).json()

    for plan in TRATAMIENTOS:
        tierra = parcelas_por_nombre.get(plan["parcela"])
        cuantos = sum(
            1
            for apunte in tratamientos
            if tierra
            and apunte.get("parcela_id") == tierra["id"]
            and apunte.get("fecha") == plan["fecha"]
            and MARCADOR in (apunte.get("observaciones") or "")
        )
        _comprobar(
            resultado,
            cuantos == 1,
            f"el tratamiento de «{plan['parcela']}» {plan['fecha']} está una sola vez ({cuantos})",
        )

    for abono in ABONOS:
        for aplicacion in abono["aplicaciones"]:
            tierra = parcelas_por_nombre.get(aplicacion["parcela"])
            cuantos = sum(
                1
                for apunte in fertilizaciones
                if tierra
                and apunte.get("parcela_id") == tierra["id"]
                and apunte.get("fecha") == aplicacion["fecha"]
                and apunte.get("fertilizante_nombre") == abono["nombre"]
            )
            _comprobar(
                resultado,
                cuantos == 1,
                f"el abono de «{aplicacion['parcela']}» {aplicacion['fecha']} está una sola vez "
                f"({cuantos})",
            )

    for plan in LABORES:
        tierra = parcelas_por_nombre.get(plan["parcela"])
        cuantos = sum(
            1
            for apunte in labores
            if tierra
            and apunte.get("parcela_id") == tierra["id"]
            and apunte.get("fecha") == plan["fecha"]
            and apunte.get("tipo") == plan["tipo"]
            and MARCADOR in (apunte.get("observaciones") or "")
        )
        _comprobar(
            resultado,
            cuantos == 1,
            f"la labor «{plan['tipo']}» de «{plan['parcela']}» {plan['fecha']} está una sola vez "
            f"({cuantos})",
        )

    tierra_de_la_cosecha = parcelas_por_nombre.get(COSECHA["parcela"])
    cuantas_cosechas = sum(
        1
        for apunte in labores
        if tierra_de_la_cosecha
        and apunte.get("parcela_id") == tierra_de_la_cosecha["id"]
        and apunte.get("fecha") == COSECHA["fecha"]
        and apunte.get("tipo") == "cosecha"
    )
    _comprobar(
        resultado,
        cuantas_cosechas == 1,
        f"la cosecha de «{COSECHA['parcela']}» {COSECHA['fecha']} está una sola vez "
        f"({cuantas_cosechas})",
    )

    # Y el mínimo de cada lista (por si la finca tiene además otros apuntes que no son del guion).
    for lista, minimo, nombre in (
        (tratamientos, len(TRATAMIENTOS), "tratamientos"),
        (fertilizaciones, sum(len(abono["aplicaciones"]) for abono in ABONOS), "abonos"),
        (labores, len(LABORES) + 1, "labores y cosecha"),
    ):
        _comprobar(
            resultado,
            len(lista) >= minimo,
            f"la lista de {nombre} tiene lo apuntado ({len(lista)}, mínimo {minimo})",
        )


def resumen_final(resultado: dict, campana: dict) -> None:
    _pantalla("\nRESUMEN")
    _pantalla("=======")
    _pantalla(f"Campaña: {campana.get('anio')} (id={campana.get('id')})")

    _pantalla("\nTierras del SIGPAC:")
    for parcela in resultado["parcelas"]:
        _pantalla(
            f"  · {parcela['alias']} (id={parcela['id']}): {parcela['superficie_ha']} ha · "
            f"uso {parcela['uso_sigpac']} · pendiente {parcela['pendiente_pct']} % · {parcela['accion']}"
        )

    _pantalla("\nProductos del catálogo:")
    for producto in resultado["productos"]:
        _pantalla(f"  · {producto['nombre']} (id={producto['id']}): {producto['accion']}")

    _pantalla("\nAbonos del catálogo:")
    for abono in resultado["abonos"]:
        _pantalla(f"  · {abono['nombre']} (id={abono['id']}): {abono['accion']}")

    _pantalla("\nApuntes del cuaderno:")
    for tratamiento in resultado["tratamientos"]:
        if tratamiento.get("id") is not None:
            _pantalla(
                f"  · tratamiento {tratamiento['fecha']} en {tratamiento['parcela']}: "
                f"id={tratamiento['id']} · {tratamiento['producto']} · plazo de seguridad hasta "
                f"{tratamiento['fecha_fin_plazo_seguridad']} · reentrada "
                f"{tratamiento['plazo_reentrada_dias']} días"
            )
        else:
            _pantalla(f"  · tratamiento {tratamiento['fecha']} en {tratamiento['parcela']}: ya estaba")
    for abono in resultado["fertilizaciones"]:
        if abono.get("id") is not None:
            _pantalla(
                f"  · abono {abono['fecha']} en {abono['parcela']}: id={abono['id']} · "
                f"{abono['abono']} · {abono['kg_ha']} kg/ha"
            )
        else:
            _pantalla(f"  · abono {abono['fecha']} en {abono['parcela']}: ya estaba")
    for labor in resultado["labores"]:
        if labor.get("id") is not None:
            _pantalla(
                f"  · labor {labor['tipo']} {labor['fecha']} en {labor['parcela']}: id={labor['id']}"
            )
        else:
            _pantalla(f"  · labor {labor['tipo']} {labor['fecha']} en {labor['parcela']}: ya estaba")
    for cosecha in resultado["cosechas"]:
        if cosecha.get("id") is not None:
            _pantalla(
                f"  · cosecha {cosecha['fecha']} en {cosecha['parcela']}: id={cosecha['id']} · "
                f"{cosecha['producto']} (sin kilos: no se inventan)"
            )
        else:
            _pantalla(f"  · cosecha {cosecha['fecha']} en {cosecha['parcela']}: ya estaba")

    correctas = sum(1 for comprobacion in resultado["comprobaciones"] if comprobacion["correcta"])
    _pantalla(
        f"\nComprobaciones: {correctas}/{len(resultado['comprobaciones'])} correctas · "
        f"fallos: {len(resultado['fallos'])}"
    )
    if resultado["fallos"]:
        _pantalla("\nLO QUE HA FALLADO:")
        for fallo in resultado["fallos"]:
            _pantalla(f"  · {fallo}")
        _pantalla("\nEl guion NO ha dejado la finca como se pedía. Se puede volver a ejecutar: es idempotente.")
    else:
        _pantalla("\nTodo ha ido bien: la finca de ejemplo tiene sus tierras completas y su cuaderno.")


# --------------------------------------------------------------------------
# El programa
# --------------------------------------------------------------------------


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    url = (sys.argv[1] if len(sys.argv) > 1 else URL_POR_DEFECTO).rstrip("/")
    _pantalla(f"Servidor: {url}")
    _pantalla(f"Cuenta: {CORREO}")

    resultado: dict = {
        "parcelas": [],
        "productos": [],
        "abonos": [],
        "tratamientos": [],
        "fertilizaciones": [],
        "labores": [],
        "cosechas": [],
        "comprobaciones": [],
        "fallos": [],
    }

    cliente = Cliente(url)
    try:
        try:
            entrar(cliente)
            campana = campana_de_2026(cliente)
            _pantalla(f"campaña: {campana.get('anio')} (id={campana.get('id')})")
        except RuntimeError as error:
            _fallo(resultado, str(error))
            return 1

        _pantalla("\n1. Las tierras: los datos reales del SIGPAC (sin tocar la forma)")
        parcelas = completar_las_tierras(cliente, resultado)
        if len(parcelas) != len(PARCELAS):
            _pantalla(
                "\nNo están completas las cinco tierras: no se sigue con los apuntes, porque un "
                "apunte sin superficie no se puede comprobar."
            )
            resumen_final(resultado, campana)
            return 1

        _pantalla("\n2. El catálogo que hace falta para apuntar")
        productos = asegurar_productos(cliente, resultado)
        abonos = asegurar_abonos(cliente, resultado)
        if len(productos) != len(PRODUCTOS) or len(abonos) != len(ABONOS):
            _pantalla("\nNo está el catálogo completo: no se siguen creando apuntes.")
            resumen_final(resultado, campana)
            return 1

        _pantalla("\n3. Los apuntes del cuaderno")
        crear_tratamientos(cliente, campana, parcelas, productos, resultado)
        crear_fertilizaciones(cliente, campana, parcelas, abonos, resultado)
        crear_labores(cliente, campana, parcelas, resultado)
        crear_cosecha(cliente, campana, parcelas, resultado)

        _pantalla("\n4. Las comprobaciones")
        try:
            comprobar(cliente, campana, resultado)
        except RuntimeError as error:
            _fallo(resultado, f"no se ha podido comprobar todo: {error}")

        resumen_final(resultado, campana)
        return 0 if not resultado["fallos"] else 1
    finally:
        cliente.cliente.close()


if __name__ == "__main__":
    sys.exit(main())
