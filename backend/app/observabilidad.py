"""**La observabilidad del propio programa** (09/11/2026).

QUÉ ES ESTO Y QUÉ NO ES
=======================

Saber qué falla, qué pantallas se usan y dónde se cae la gente **sin añadir nada que
instalar** y **sin que la observabilidad pueda romper la aplicación**. En un programa que
corre en el móvil de un agricultor de 50 a 70 años, en una parcela y sin cobertura, eso
significa tres cosas:

1. **Todo vive en memoria**, en el propio proceso. No hay ningún servicio de fuera, ni una
   base de datos nueva, ni una dependencia nueva. Es el mismo criterio de siempre: el
   servidor donde se instale esto no tiene por qué tener nada más que Python.
2. **No se guarda nada de nadie.** Se cuentan cosas (una ruta, un código, una pantalla),
   nunca se copian cuerpos de petición, ni NIF, ni correos, ni tokens, ni nombres. El
   cuaderno de un agricultor son datos suyos y de nadie más; una herramienta de medida no
   es una excusa para sacarlos de la explotación. Está contado en `docs/OBSERVABILIDAD.md`.
3. **Ninguna función de este módulo puede lanzar hacia fuera.** Si una métrica falla, se
   pierde la métrica y la petición sigue su camino: un contador roto no puede dejar al
   agricultor sin apuntar un tratamiento. Por eso cada función pública va envuelta y, en el
   peor caso, devuelve una estructura vacía.

Es un módulo **puro**: no importa FastAPI ni SQLAlchemy. La puerta web está en
`routers/observabilidad_api.py`, el medidor de cada petición en `main.py` y el aviso desde la
pantalla en `web/nuevo/app.js`. Así se puede probar sin levantar el servidor, que es lo que
hace `tests/test_observabilidad.py`.

LO QUE SE MIDE
==============

* **Errores**: marca de tiempo, tipo, método, ruta **normalizada** (sin identificadores),
  código y un mensaje corto saneado. En un búfer circular acotado: cuando se llena, el más
  viejo se va solo. Un error es un 5xx, o una excepción que no ha llegado a contestar.
* **Uso por pantalla y día**: `(día, clave)` → cuántas veces se ha abierto. La clave se
  normaliza a `[a-z0-9_-]`, con una lista blanca sacada de la pantalla nueva
  (`web/nuevo/app.js`); lo que no está en la lista se cuenta como `otra`. Los días viejos se
  purgan y hay un tope de claves.
* **Duración por plantilla de ruta**: peticiones, cuenta por código de estado y p50/p95
  **calculados sobre una muestra acotada** (no se guardan todas las medidas: una lista que
  crece sin freno es una fuga de memoria en el móvil de un agricultor).
* **El embudo**, que **no se inventa**: se calcula con SQL sobre las tablas que ya existen
  (cuentas → fincas → fincas con tierra → con algún apunte → con cuaderno firmado o
  exportado). Si una tabla no está, esa etapa se queda en «no se sabe» y se dice por qué,
  nunca se rellena con un cero que parezca un dato.

LO QUE NO SE MIDE, Y POR QUÉ
============================

* **Cuerpos de petición o de respuesta**: pueden llevar el NIF, el correo, el nombre, una
  foto del cuaderno o la clave de un agricultor. No hace falta para saber qué falla.
* **Quién**: ni la cuenta, ni la IP, ni el vale. Para arreglar una pantalla basta con saber
  que falla y dónde; para señalar a una persona haría falta otro motivo y otro permiso.
* **Los datos del cuaderno** (tierras, tratamientos, importes): no son métricas. El resumen
  del embudo cuenta **fincas distintas por etapa**, no qué finca.
* **Texto de pantalla nuevo**: aquí no hay ni una palabra visible para el agricultor. Todo
  lo que lee sigue viviendo en `app/textos.py`.

CÓMO SE ENCIENDE
================

Por defecto **no escribe nada en disco** (la suite no debe ensuciar el ordenador de quien la
ejecuta, y una instalación normal no necesita ficheros). Si se pone la variable de entorno
`CUEDIGITAL_OBSERVABILIDAD` con una carpeta o con un fichero, cada error y cada cambio de
pantalla se añade a un JSONL que gira al llegar a un tamaño máximo. El resumen se lee con
`GET /api/observabilidad/resumen` y la cabecera `X-Observabilidad`, que se compara con
`CUEDIGITAL_OBSERVABILIDAD_TOKEN` en tiempo constante. Sin token configurado esa ruta
**no existe** (404): la herramienta no está abierta «para que la cierren luego».
"""

from __future__ import annotations

import datetime as dt
import hmac
import json
import math
import os
import pathlib
import re
import threading
from collections import deque
from typing import Any

# ---------------------------------------------------------------------------
# Nombres de las variables de entorno y de la cabecera
# ---------------------------------------------------------------------------

VARIABLE_DEL_REGISTRO = "CUEDIGITAL_OBSERVABILIDAD"
VARIABLE_DEL_TOKEN = "CUEDIGITAL_OBSERVABILIDAD_TOKEN"
CABECERA_DEL_RESUMEN = "X-Observabilidad"

# ---------------------------------------------------------------------------
# Topes. Todos son deliberadamente pequeños: esto entra en el móvil de un agricultor.
# ---------------------------------------------------------------------------

#: Cuántos errores se guardan en memoria (los más recientes).
MAXIMO_DE_ERRORES = 40
#: Cuántas plantillas de ruta distintas se miden.
MAXIMO_DE_RUTAS = 200
#: Cuántas claves `(día, pantalla)` se guardan como mucho.
MAXIMO_DE_CLAVES_DE_PANTALLA = 500
#: Cuántos días de uso por pantalla se conservan.
DIAS_DE_PANTALLAS = 14
#: Cuántas duraciones se guardan por ruta para los percentiles (una estructura acotada).
MAXIMO_DE_MUESTRAS_POR_RUTA = 64
#: Cuántos bytes puede llegar a tener el JSONL antes de girar.
MAXIMO_DE_BYTES_DEL_FICHERO = 2 * 1024 * 1024
#: Cuántas copias giradas se conservan (`observabilidad.jsonl.1`, `.2`…).
COPIAS_DEL_FICHERO = 2
#: Cómo se llama el fichero cuando la variable apunta a una carpeta.
NOMBRE_DEL_FICHERO = "observabilidad.jsonl"
#: Longitudes de lo que sí se guarda. Cortas a propósito.
MAXIMO_DEL_MENSAJE = 160
MAXIMO_DEL_TIPO = 60
MAXIMO_DE_LA_RUTA = 120
MAXIMO_DE_LA_CLAVE_DE_PANTALLA = 40
#: Hasta dónde se lee el cuerpo del aviso de pantalla. Más que esto no es un aviso.
MAXIMO_DEL_CUERPO_DEL_AVISO = 2048

#: Las pantallas que la aplicación nueva puede abrir. **Sale de `web/nuevo/app.js`**: son los
#: valores de `vista` y de `data-destino` de su armazón (y no una lista inventada aquí). Lo que
#: no esté en esta lista se cuenta como `otra`: así una pantalla nueva empieza a medirse en
#: cuanto se añade a esta lista, y mientras tanto no ensucia el resumen con claves libres.
CLAVES_DE_PANTALLA = frozenset(
    {
        "hoy",
        "tierras",
        "alta",
        "tierra",
        "apuntar",
        "cuaderno",
        "productos",
        "calendario",
        "trabajos",
        "facturas",
        "mas",
    }
)

#: La clave a la que van a parar las pantallas que no están en la lista blanca.
PANTALLA_DESCONOCIDA = "otra"

#: La plantilla a la que van a parar las rutas cuando ya hay demasiadas medidas. Es una
#: constante propia y no una ruta cualquiera para que no se confunda con una de verdad.
RUTA_DE_DESBORDE = "/(otras)"

# ---------------------------------------------------------------------------
# Expresiones y patrones, todos con un motivo
# ---------------------------------------------------------------------------

_RE_ESPACIOS = re.compile(r"\s+")
#: Un correo no es una métrica: se tapa antes de guardar el mensaje de un fallo.
_RE_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
#: Un NIF o un NIE tampoco: se tapa igual. Es el dato que más se repite en este programa.
_RE_NIF = re.compile(r"\b(?:\d{8}[A-Za-z]|[XYZxyz]\d{7}[A-Za-z])\b")
#: Un número de teléfono español, por si el mensaje lo lleva dentro.
_RE_TELEFONO = re.compile(r"\b(?:\+34)?[6789]\d{8}\b")

_RE_DIGITOS = re.compile(r"^\d+$")
_RE_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_RE_HEX_LARGO = re.compile(r"^[0-9a-fA-F]{8,}$")
_RE_CLAVE_DE_PANTALLA = re.compile(r"^[a-z0-9_-]{1,%d}$" % MAXIMO_DE_LA_CLAVE_DE_PANTALLA)

# ---------------------------------------------------------------------------
# El estado: todo en memoria, todo protegido por un solo cerrojo
# ---------------------------------------------------------------------------
#
# Un cerrojo (y no uno por estructura) porque lo que se hace dentro es muy corto —añadir a una
# cola, sumar uno a un contador— y tener tres cerrojos solo añade la posibilidad de tomarlos en
# orden distinto. El único sitio donde se hace algo más largo es la escritura en disco, que va
# **fuera** de este cerrojo y con el suyo propio.

_CERRADO = threading.RLock()
_CERRADO_DEL_FICHERO = threading.Lock()

#: Errores recientes. `deque` con `maxlen` es el búfer circular: al llenarse, el más viejo cae
#: solo y nadie tiene que acordarse de recortarlo.
_ERRORES: deque[dict[str, Any]] = deque(maxlen=MAXIMO_DE_ERRORES)

#: `(día ISO, clave de pantalla)` → cuántas veces. Es todo lo que se guarda del uso.
_PANTALLAS: dict[tuple[str, str], int] = {}

#: Plantilla de ruta → {peticiones, códigos, muestras de milisegundos}.
_RUTAS: dict[str, dict[str, Any]] = {}

#: Cuándo arrancó este proceso. Sirve para no confundir «no hay errores» con «no se ha mirado».
_ARRANQUE = dt.datetime.now()


# ---------------------------------------------------------------------------
# Utilidades pequeñas (todas sin lanzar)
# ---------------------------------------------------------------------------


def _texto_corto(valor: Any, maximo: int, por_defecto: str = "") -> str:
    """Un texto de una línea, sin datos personales y recortado.

    Se tapan correos, NIF/NIE y teléfonos **antes** de recortar: si se recortara primero, un
    correo partido por la mitad no lo reconocería la expresión y se colaría en el registro.

    No lanza nunca: si el valor no se puede convertir a texto, devuelve el valor por defecto.
    """
    try:
        if valor is None:
            return por_defecto
        texto = _RE_ESPACIOS.sub(" ", str(valor)).strip()
        texto = _RE_CORREO.sub("[correo]", texto)
        texto = _RE_NIF.sub("[nif]", texto)
        texto = _RE_TELEFONO.sub("[telefono]", texto)
        return texto[:maximo]
    except Exception:  # noqa: BLE001 — la observabilidad no puede tumbar la petición
        return por_defecto


def _entero(valor: Any) -> int:
    """Un entero, o 0. Nunca lanza."""
    try:
        return int(valor)
    except Exception:  # noqa: BLE001
        return 0


def _milisegundos(valor: Any) -> float | None:
    """Una duración razonable en milisegundos, o `None` si no lo es.

    Una duración negativa o infinita no es una medida: se descarta. Y una de más de diez
    minutos tampoco es una petición normal (sería un cero mal puesto o un reloj roto).
    """
    try:
        numero = float(valor)
    except Exception:  # noqa: BLE001
        return None
    if not math.isfinite(numero) or numero < 0 or numero > 600_000:
        return None
    return round(numero, 2)


def normalizar_ruta(ruta: Any) -> str:
    """La **plantilla** de una ruta: sin consulta, sin identificadores y acotada.

    Es lo que permite que `/api/parcelas/17` y `/api/parcelas/2031` sean la misma fila del
    resumen. Se sustituye por `{id}` lo que es un identificador y no un nombre: un número
    entero, un UUID, una cadena hexadecimal larga o un segmento desproporcionado. Se corta en
    diez segmentos y en `MAXIMO_DE_LA_RUTA` caracteres para que una ruta inventada por
    cualquiera no se convierta en una clave de memoria sin fin.

    Nunca lanza: ante cualquier cosa rara devuelve `/`.
    """
    try:
        texto = str(ruta or "").split("?", 1)[0].split("#", 1)[0].strip()
        if not texto.startswith("/"):
            texto = "/" + texto
        partes: list[str] = []
        for parte in [tramo for tramo in texto.split("/") if tramo][:10]:
            if (
                _RE_DIGITOS.match(parte)
                or _RE_UUID.match(parte)
                or _RE_HEX_LARGO.match(parte)
                or len(parte) > 48
            ):
                partes.append("{id}")
            else:
                partes.append(parte)
        normal = "/" + "/".join(partes)
        return normal[:MAXIMO_DE_LA_RUTA] or "/"
    except Exception:  # noqa: BLE001
        return "/"


def clave_de_pantalla(valor: Any) -> str | None:
    """La clave con la que se cuenta una pantalla, o `None` si el aviso no vale.

    La regla es la del contrato: solo `[a-z0-9_-]`, en minúsculas y con una longitud máxima.
    Lo que no está en la lista blanca se cuenta como `otra` (una pantalla nueva se mide desde
    el primer día, sin tocar el servidor); lo que **no parece una pantalla** —una ruta, unos
    puntos suspensivos, un espacio— se descarta y no se cuenta.
    """
    try:
        if not isinstance(valor, str):
            return None
        limpio = valor.strip().lower()
        if not _RE_CLAVE_DE_PANTALLA.match(limpio):
            return None
        return limpio if limpio in CLAVES_DE_PANTALLA else PANTALLA_DESCONOCIDA
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# El registro en memoria
# ---------------------------------------------------------------------------


def registrar_error(
    tipo: Any,
    metodo: Any,
    ruta: Any,
    codigo: Any,
    mensaje: Any = None,
) -> None:
    """Apunta un error en el búfer circular y, si está configurado, en el JSONL.

    Lo que se guarda es **lo mínimo** para poder arreglarlo: cuándo, qué tipo de fallo, con
    qué método y en qué plantilla de ruta, el código y un mensaje corto ya saneado. No se
    guarda el cuerpo, ni el vale, ni a quién le pasó.

    No lanza: si algo falla, se pierde el error y la petición sigue.
    """
    try:
        ahora = dt.datetime.now()
        entrada = {
            "cuando": ahora.isoformat(timespec="seconds"),
            "tipo": _texto_corto(tipo, MAXIMO_DEL_TIPO, "desconocido") or "desconocido",
            "metodo": _texto_corto(metodo, 10).upper(),
            "ruta": normalizar_ruta(ruta),
            "codigo": _entero(codigo),
            "mensaje": _texto_corto(mensaje, MAXIMO_DEL_MENSAJE),
        }
        with _CERRADO:
            _ERRORES.append(entrada)
        if ruta_configurada() is not None:
            _escribir_en_disco({"que": "error", **entrada})
    except Exception:  # noqa: BLE001 — una métrica rota no puede tumbar la petición
        return


def registrar_peticion(
    metodo: Any,
    ruta: Any,
    codigo: Any,
    milisegundos: Any,
    tipo: Any = None,
    mensaje: Any = None,
) -> None:
    """Mide una petición: cuenta por código, suma duración y guarda el 5xx como error.

    `tipo` y `mensaje` solo se usan cuando la petición ha fallado con una excepción; si el
    fallo ha sido un 5xx contestado, `tipo` puede ser `None` y se apunta «Respuesta5xx».

    No lanza nunca.
    """
    try:
        plantilla = normalizar_ruta(ruta)
        duracion = _milisegundos(milisegundos)
        codigo_numero = _entero(codigo)
        with _CERRADO:
            datos = _RUTAS.get(plantilla)
            if datos is None:
                if len(_RUTAS) >= MAXIMO_DE_RUTAS:
                    # El tope no puede convertir la lista de rutas en una fuga: lo que sobre
                    # se cuenta en una sola plantilla, y se dice que es eso.
                    plantilla = RUTA_DE_DESBORDE
                    datos = _RUTAS.get(plantilla)
                if datos is None:
                    datos = {
                        "peticiones": 0,
                        "codigos": {},
                        "muestras": deque(maxlen=MAXIMO_DE_MUESTRAS_POR_RUTA),
                    }
                    _RUTAS[plantilla] = datos
            datos["peticiones"] += 1
            clave_del_codigo = str(codigo_numero)
            datos["codigos"][clave_del_codigo] = datos["codigos"].get(clave_del_codigo, 0) + 1
            if duracion is not None:
                datos["muestras"].append(duracion)
        if codigo_numero >= 500:
            registrar_error(
                tipo if tipo is not None else "Respuesta5xx",
                metodo,
                plantilla,
                codigo_numero,
                mensaje,
            )
    except Exception:  # noqa: BLE001
        return


def registrar_pantalla(valor: Any) -> None:
    """Suma uno al uso de una pantalla, en el día de hoy.

    La clave se normaliza (ver `clave_de_pantalla`). Si el día tiene claves de más, la métrica
    se pierde **en silencio**: es preferible eso a que un contador sin tope se coma la memoria
    del móvil. Y si el aviso no vale, no se cuenta nada.

    No lanza nunca.
    """
    try:
        clave = clave_de_pantalla(valor)
        if clave is None:
            return
        hoy = dt.date.today()
        with _CERRADO:
            _purgar_los_dias_viejos(hoy)
            pareja = (hoy.isoformat(), clave)
            if pareja not in _PANTALLAS and len(_PANTALLAS) >= MAXIMO_DE_CLAVES_DE_PANTALLA:
                return
            _PANTALLAS[pareja] = _PANTALLAS.get(pareja, 0) + 1
        if ruta_configurada() is None:
            return
        _escribir_en_disco(
            {
                "que": "pantalla",
                "cuando": dt.datetime.now().isoformat(timespec="seconds"),
                "dia": hoy.isoformat(),
                "pantalla": clave,
            }
        )
    except Exception:  # noqa: BLE001
        return


def _purgar_los_dias_viejos(hoy: dt.date) -> None:
    """Tira los días que ya no interesan. Se llama antes de apuntar y antes de resumir.

    Se hace **bajo el cerrojo**: recorre un diccionario acotado, y así nunca se purga mientras
    otra hebra está escribiendo en él.
    """
    try:
        limite = (hoy - dt.timedelta(days=DIAS_DE_PANTALLAS)).isoformat()
        viejos = [pareja for pareja in _PANTALLAS if pareja[0] < limite]
        for pareja in viejos:
            del _PANTALLAS[pareja]
    except Exception:  # noqa: BLE001
        return


def _percentil(muestras: list[float], porcentaje: float) -> float | None:
    """Un p50/p95 sencillo por interpolación lineal. Sin numpy y sin guardar todo.

    Es un percentil de andar por casa y se dice así: sirve para ver si una ruta se ha vuelto
    lenta, no para publicar una latencia con dos decimales de fe.
    """
    try:
        if not muestras:
            return None
        ordenadas = sorted(muestras)
        if len(ordenadas) == 1:
            return round(float(ordenadas[0]), 2)
        posicion = (len(ordenadas) - 1) * (porcentaje / 100.0)
        abajo = int(posicion)
        arriba = min(abajo + 1, len(ordenadas) - 1)
        peso = posicion - abajo
        return round(ordenadas[abajo] * (1.0 - peso) + ordenadas[arriba] * peso, 2)
    except Exception:  # noqa: BLE001
        return None


def resumen() -> dict[str, Any]:
    """Lo que se ha medido en este proceso, en una estructura que se pueda leer.

    Es memoria pura: **no toca la base de datos**. El embudo va aparte (`embudo(db)`) porque
    ese sí necesita SQL, y así esta función se puede probar sin base ni servidor.

    Los errores van de más nuevo a más viejo; las pantallas de día más reciente a más viejo; y
    las rutas de más petadas a menos, que es el orden en el que se busca el problema.

    No lanza: si algo fallara, devuelve un resumen vacío. Un resumen vacío se lee como «no hay
    nada», y por eso el resumen lleva `desde_el_arranque`: para no confundirlo con «no se ha
    mirado».
    """
    try:
        hoy = dt.date.today()
        with _CERRADO:
            _purgar_los_dias_viejos(hoy)
            errores = list(_ERRORES)[::-1]
            pantallas = [
                {"dia": dia, "pantalla": clave, "veces": veces}
                for (dia, clave), veces in _PANTALLAS.items()
            ]
            rutas = []
            for plantilla, datos in _RUTAS.items():
                muestras = list(datos["muestras"])
                rutas.append(
                    {
                        "ruta": plantilla,
                        "peticiones": datos["peticiones"],
                        "codigos": dict(datos["codigos"]),
                        "muestras": len(muestras),
                        "p50_ms": _percentil(muestras, 50),
                        "p95_ms": _percentil(muestras, 95),
                    }
                )
            memoria = {
                "errores": len(_ERRORES),
                "rutas": len(_RUTAS),
                "pantallas": len(_PANTALLAS),
            }
        pantallas.sort(key=lambda fila: (fila["dia"], fila["veces"]), reverse=True)
        rutas.sort(key=lambda fila: fila["peticiones"], reverse=True)
        return {
            "generado_en": dt.datetime.now().isoformat(timespec="seconds"),
            "desde_el_arranque": _ARRANQUE.isoformat(timespec="seconds"),
            "errores_recientes": errores,
            "pantallas": pantallas,
            "rutas": rutas,
            "memoria": memoria,
        }
    except Exception:  # noqa: BLE001
        return {
            "generado_en": dt.datetime.now().isoformat(timespec="seconds"),
            "desde_el_arranque": _ARRANQUE.isoformat(timespec="seconds"),
            "errores_recientes": [],
            "pantallas": [],
            "rutas": [],
            "memoria": {"errores": 0, "rutas": 0, "pantallas": 0},
        }


def reiniciar() -> None:
    """Vacía lo medido y pone el arranque a ahora. **Solo para las pruebas.**

    Existe para que un test pueda mirar un contador exacto sin depender de lo que midieron los
    tests anteriores. En el programa no se llama desde ningún sitio: si algún día hiciera falta
    «borrar las métricas» en caliente, sería otra decisión y tendría su motivo escrito.
    """
    global _ARRANQUE
    try:
        with _CERRADO:
            _ERRORES.clear()
            _PANTALLAS.clear()
            _RUTAS.clear()
            _ARRANQUE = dt.datetime.now()
    except Exception:  # noqa: BLE001
        return


# ---------------------------------------------------------------------------
# El embudo, con SQL sobre lo que ya existe
# ---------------------------------------------------------------------------

#: Las etapas del embudo, en orden. **Cada una cuenta fincas distintas**, excepto la primera,
#: que cuenta cuentas dadas de alta. El SQL es el mismo válido en SQLite y en PostgreSQL
#: (`COUNT(DISTINCT …)` y subconsultas con `UNION`), porque en este programa lo local y lo de
#: producción tienen que decir lo mismo.
#:
#: El último escalón es «cuaderno firmado o exportado»: se apoya en la tabla `firmas` (una
#: firma de tipo «cuaderno») y en el rastro de `auditoria`, donde la descarga del cuaderno de
#: la Junta escribe `sacar_el_cuaderno_de_la_junta` (`routers/cuaderno_cyl_api.py`). No se
#: instrumenta nada nuevo: se lee lo que el programa ya apunta.
ETAPAS_DEL_EMBUDO: tuple[tuple[str, str, str], ...] = (
    (
        "cuentas",
        "Cuentas dadas de alta",
        "SELECT COUNT(DISTINCT id) FROM usuarios",
    ),
    (
        "fincas",
        "Fincas dadas de alta",
        "SELECT COUNT(DISTINCT id) FROM explotaciones",
    ),
    (
        "fincas_con_tierra",
        "Fincas con al menos una tierra",
        "SELECT COUNT(DISTINCT explotacion_id) FROM parcelas",
    ),
    (
        "fincas_con_apunte",
        "Fincas con al menos un apunte (labor, tratamiento, fertilización o siembra)",
        "SELECT COUNT(DISTINCT explotacion_id) FROM ("
        " SELECT explotacion_id FROM labores"
        " UNION SELECT explotacion_id FROM tratamientos"
        " UNION SELECT explotacion_id FROM fertilizaciones"
        " UNION SELECT explotacion_id FROM siembras"
        ") AS apuntes",
    ),
    (
        "fincas_con_cuaderno",
        "Fincas con el cuaderno firmado o exportado",
        "SELECT COUNT(DISTINCT explotacion_id) FROM ("
        " SELECT explotacion_id FROM firmas WHERE entidad = 'cuaderno'"
        " UNION SELECT explotacion_id FROM auditoria"
        " WHERE accion = 'sacar_el_cuaderno_de_la_junta'"
        ") AS cuadernos",
    ),
)


def embudo(db: Any) -> dict[str, Any]:
    """El embudo de uso, calculado **con SQL sobre los datos que ya existen**.

    Devuelve una entrada por etapa con su cuenta, y una lista de fallos con las etapas que no
    se han podido medir. **Una etapa que falla se queda en `None`, no en `0`**: un cero
    significa «nadie ha llegado» y un `None` significa «no se sabe», y en este programa no son
    lo mismo. El caso típico es una base a la que todavía le falta una tabla.

    Para que un fallo en una etapa **no tumbe las siguientes**, cada consulta va dentro de un
    punto de guardado (`SAVEPOINT`): en PostgreSQL un error deja la transacción abortada, y sin
    el punto de guardado todas las etapas de después fallarían en cadena por un fallo que solo
    era de la primera. No se escribe nada: son cinco `COUNT`.

    No lanza nunca.
    """
    etapas: list[dict[str, Any]] = []
    fallos: list[dict[str, str]] = []
    for clave, que_es, consulta in ETAPAS_DEL_EMBUDO:
        try:
            # `exec_driver_sql` manda la consulta tal cual al motor. Se usa eso y no
            # `sqlalchemy.text` para que este módulo **no tenga que importar SQLAlchemy**: la
            # sesión se la pasa quien llama y aquí solo se le pide un número.
            with db.begin_nested():
                cuenta = db.connection().exec_driver_sql(consulta).scalar()
            etapas.append(
                {
                    "clave": clave,
                    "que_es": que_es,
                    "cuenta": _entero(cuenta),
                }
            )
        except Exception as fallo:  # noqa: BLE001 — una tabla que falta no revienta el resumen
            etapas.append({"clave": clave, "que_es": que_es, "cuenta": None})
            fallos.append(
                {
                    "clave": clave,
                    "motivo": _texto_corto(fallo, 140, "no se ha podido medir"),
                }
            )
    return {"etapas": etapas, "fallos": fallos}


# ---------------------------------------------------------------------------
# El token del resumen
# ---------------------------------------------------------------------------


def token_configurado() -> str | None:
    """El token de la cabecera, si está configurado. `None` significa «esta puerta no existe»."""
    try:
        token = os.environ.get(VARIABLE_DEL_TOKEN, "").strip()
        return token or None
    except Exception:  # noqa: BLE001
        return None


def token_es_valido(cabecera: Any) -> bool:
    """Si la cabecera trae el token configurado, comparando **en tiempo constante**.

    Se usa `hmac.compare_digest`, que tarda lo mismo aunque el primer carácter sea distinto.
    Una comparación normal (`==`) va parando en el primer fallo, y eso deja adivinar el token
    letra a letra midiendo lo que tarda. El token no protege datos de nadie (el resumen no
    lleva datos de ninguna finca), pero una cabecera se compara bien desde el primer día.

    Un token sin configurar **nunca** vale, ni siquiera si la cabecera viene vacía: el «no hay
    nada configurado» no se puede colar como «ha coincidido».
    """
    try:
        esperado = token_configurado()
        if esperado is None:
            return False
        recibido = "" if cabecera is None else str(cabecera)
        return hmac.compare_digest(recibido.encode("utf-8"), esperado.encode("utf-8"))
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# La escritura opcional en disco (JSONL giratorio). Por defecto, NADA.
# ---------------------------------------------------------------------------


def ruta_configurada() -> pathlib.Path | None:
    """La ruta del registro, si `CUEDIGITAL_OBSERVABILIDAD` está puesta. Si no, `None`.

    Se lee la variable **en cada llamada** y no al importar el módulo, por dos motivos: así se
    puede probar el caso «sin variable» sin reiniciar el intérprete, y así se puede apagar la
    escritura sin tocar el código.

    La variable puede apuntar a una **carpeta** (se escribe `observabilidad.jsonl` dentro) o a
    un **fichero**. Un nombre con extensión se trata como fichero; una carpeta que ya existe,
    como carpeta; y un nombre sin extensión que no existe se crea como carpeta, que es lo que
    espera quien pone `CUEDIGITAL_OBSERVABILIDAD=/var/log/cuedigital`.
    """
    try:
        bruto = os.environ.get(VARIABLE_DEL_REGISTRO, "").strip()
        if not bruto:
            return None
        ruta = pathlib.Path(bruto).expanduser()
        if ruta.exists() and ruta.is_dir():
            return ruta / NOMBRE_DEL_FICHERO
        if ruta.exists():
            return ruta
        if ruta.suffix:
            return ruta
        return ruta / NOMBRE_DEL_FICHERO
    except Exception:  # noqa: BLE001
        return None


def _preparar_la_carpeta(fichero: pathlib.Path) -> None:
    """Crea la carpeta del registro si hace falta. Solo se llama con la variable puesta."""
    try:
        fichero.parent.mkdir(parents=True, exist_ok=True)
    except Exception:  # noqa: BLE001
        return


def _rotar_si_hace_falta(fichero: pathlib.Path) -> None:
    """Gira el JSONL cuando llega al tamaño máximo, conservando `COPIAS_DEL_FICHERO` copias.

    El motivo de girar es el de siempre: un fichero que solo crece acaba llenando el disco de
    la instalación. Se usa `os.replace`, que en el mismo volumen es atómico: no queda un
    momento en el que el fichero no esté en ningún sitio.
    """
    try:
        if not fichero.exists() or fichero.stat().st_size < MAXIMO_DE_BYTES_DEL_FICHERO:
            return
        for indice in range(COPIAS_DEL_FICHERO - 1, 0, -1):
            origen = pathlib.Path(f"{fichero}.{indice}")
            destino = pathlib.Path(f"{fichero}.{indice + 1}")
            if origen.exists():
                os.replace(origen, destino)
        os.replace(fichero, pathlib.Path(f"{fichero}.1"))
    except Exception:  # noqa: BLE001
        return


def _escribir_en_disco(evento: dict[str, Any]) -> None:
    """Añade una línea al JSONL, **solo si hay variable de entorno**. Si no, vuelve sin más.

    Nunca lanza: un disco lleno, una carpeta sin permiso o un JSON que no se puede convertir
    se tragan aquí. La métrica se pierde y el programa sigue, que es exactamente lo que se
    pide de una herramienta de medida.
    """
    try:
        fichero = ruta_configurada()
        if fichero is None:
            return
        linea = json.dumps(evento, ensure_ascii=False, separators=(",", ":"), default=str) + "\n"
        with _CERRADO_DEL_FICHERO:
            _preparar_la_carpeta(fichero)
            _rotar_si_hace_falta(fichero)
            with open(fichero, "a", encoding="utf-8", newline="\n") as salida:
                salida.write(linea)
    except Exception:  # noqa: BLE001
        return
