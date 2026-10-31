"""Los límites de intentos: cuántas veces se puede llamar a una puerta desde un sitio.

## Por qué vive en su propio fichero

`security.py` sabe firmar vales y guardar claves, pero **no sabe de quién viene la
petición**: eso lo trae la petición de HTTP (`request.client.host`), no el vale. Por eso
el límite está aquí y no dentro de `security.py`, que tiene que poder probarse sin red.

## Qué se limita y por qué

- **Entrar con correo y clave**: los fallos, no los aciertos. Quien acierta no se ve
  afectado aunque esté detrás de una conexión compartida; quien prueba claves, sí.
- **Darse de alta**: cada alta que pide el mismo sitio, acierte o no, porque crear
  cuentas en serie es lo que se quiere evitar.
- **Entrar con el certificado**: cada llamada desde el mismo sitio. Es barato de
  llamar y no tiene clave que adivinar, así que lo que se limita es el ritmo.

Se cuenta **por dos claves a la vez** en la entrada: por la dirección de quien llama y
por el correo que se está probando. Así no vale ni cambiar de correo desde la misma
dirección ni cambiar de dirección contra el mismo correo.

## Lo que este límite NO es

Es un contador **en memoria**, por proceso. Sirve para una instalación (que es como se
despliega: un servidor por agricultor o por cliente), y no pretende ser un cortafuegos
distribuido. Si algún día hay varios procesos detrás de un equilibrador, el contador
tiene que ir a algo compartido (la base de datos o un servicio de memoria); el sitio
para cambiarlo es este fichero y este comentario.

## La dirección de quien llama

Se usa `request.client.host`, que es la dirección real de la conexión. **No se lee
`X-Forwarded-For`**: esa cabecera la puede escribir cualquiera, y creérsela convertiría
el límite en un adorno que se salta con una línea. Si algún día el programa se pone
detrás de un proxy, el proxy tiene que ser quien corte, o hay que configurar el servidor
para que reescriba la dirección real; eso se hace en la instalación, no aquí.
"""

from __future__ import annotations

import logging
import threading
import time

registro = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Los números. Se pueden cambiar aquí y solo aquí.
# --------------------------------------------------------------------------

# Entrar con clave: diez fallos en un cuarto de hora. Un agricultor que se equivoca
# tres veces seguidas no llega ni de lejos; una lista de claves, sí.
MAXIMO_FALLOS_DE_ENTRADA = 10
VENTANA_DE_ENTRADA_SEGUNDOS = 15 * 60

# Darse de alta: diez llamadas por hora desde el mismo sitio. Se cuentan todas, no solo
# las que acaban en cuenta: cada llamada gasta una huella de clave, y eso también es
# trabajo que no se le regala a quien va a probar en serie.
MAXIMO_ALTAS = 10
VENTANA_DE_ALTAS_SEGUNDOS = 60 * 60

# Entrar con certificado: treinta llamadas por hora desde el mismo sitio.
MAXIMO_CERTIFICADOS = 30
VENTANA_DE_CERTIFICADO_SEGUNDOS = 60 * 60


class Limitador:
    """Cuenta marcas de tiempo por clave y dice si se ha pasado.

    Es deliberadamente pequeño: una lista de instantes por clave, y se tiran los que
    ya han salido de la ventana. No guarda nada en disco ni sobrevive a un reinicio,
    que es lo que se quiere: al reiniciar, el agricultor vuelve a poder entrar.
    """

    def __init__(self, maximo: int, ventana_segundos: int) -> None:
        self.maximo = maximo
        self.ventana = ventana_segundos
        self._marcas: dict[str, list[float]] = {}
        self._cerrojo = threading.Lock()

    def _vigentes(self, clave: str, ahora: float) -> list[float]:
        marcas = [instante for instante in self._marcas.get(clave, ()) if ahora - instante < self.ventana]
        if marcas:
            self._marcas[clave] = marcas
        else:
            self._marcas.pop(clave, None)
        return marcas

    def puede(self, clave: str) -> bool:
        """¿Queda sitio para otra llamada? No apunta nada: solo mira."""
        ahora = time.monotonic()
        with self._cerrojo:
            return len(self._vigentes(clave, ahora)) < self.maximo

    def apunta(self, clave: str) -> int:
        """Apunta una llamada y devuelve cuántas hay ahora en la ventana."""
        ahora = time.monotonic()
        with self._cerrojo:
            marcas = self._vigentes(clave, ahora)
            marcas.append(ahora)
            self._marcas[clave] = marcas
            return len(marcas)

    def olvida(self, clave: str) -> None:
        """Borra lo apuntado de una clave: se usa cuando la entrada ha ido bien."""
        with self._cerrojo:
            self._marcas.pop(clave, None)

    def limpiar(self) -> None:
        with self._cerrojo:
            self._marcas.clear()


# Una instancia por puerta. Los nombres se usan en los tests y en los mensajes de
# registro, así que no se renombran a la ligera.
ENTRADAS_POR_DIRECCION = Limitador(MAXIMO_FALLOS_DE_ENTRADA, VENTANA_DE_ENTRADA_SEGUNDOS)
ENTRADAS_POR_CUENTA = Limitador(MAXIMO_FALLOS_DE_ENTRADA, VENTANA_DE_ENTRADA_SEGUNDOS)
ALTAS_POR_DIRECCION = Limitador(MAXIMO_ALTAS, VENTANA_DE_ALTAS_SEGUNDOS)
CERTIFICADOS_POR_DIRECCION = Limitador(MAXIMO_CERTIFICADOS, VENTANA_DE_CERTIFICADO_SEGUNDOS)

_LOS_DE_ESTE_MODULO = (
    ENTRADAS_POR_DIRECCION,
    ENTRADAS_POR_CUENTA,
    ALTAS_POR_DIRECCION,
    CERTIFICADOS_POR_DIRECCION,
)


def direccion_de(request) -> str:
    """La dirección desde la que llega la petición, o «desconocida» si no la trae."""
    cliente = getattr(request, "client", None)
    return getattr(cliente, "host", None) or "desconocida"


def clave_de_entrada_por_direccion(request) -> str:
    return f"entrar:desde:{direccion_de(request)}"


def clave_de_entrada_por_cuenta(correo: str) -> str:
    return f"entrar:cuenta:{(correo or '').strip().lower()}"


def clave_de_alta(request) -> str:
    return f"alta:desde:{direccion_de(request)}"


def clave_de_certificado(request) -> str:
    return f"certificado:desde:{direccion_de(request)}"


def demasiadas_entradas(request, correo: str) -> bool:
    """Mira las dos cuentas de la entrada (dirección y correo), sin apuntar nada."""
    return not (
        ENTRADAS_POR_DIRECCION.puede(clave_de_entrada_por_direccion(request))
        and ENTRADAS_POR_CUENTA.puede(clave_de_entrada_por_cuenta(correo))
    )


def apuntar_fallo_de_entrada(request, correo: str) -> None:
    """Apunta un fallo en las dos claves y lo deja en el registro del programa.

    En el registro va **solo la dirección**, no el correo: un intento fallido no debe
    dejar en un fichero de texto la lista de correos que alguien estaba probando.
    """
    desde = clave_de_entrada_por_direccion(request)
    cuenta = clave_de_entrada_por_cuenta(correo)
    cuantas_desde = ENTRADAS_POR_DIRECCION.apunta(desde)
    cuantas_de_la_cuenta = ENTRADAS_POR_CUENTA.apunta(cuenta)
    registro.warning(
        "entrada fallida desde %s (%s fallos en la ventana, %s contra ese correo)",
        direccion_de(request),
        cuantas_desde,
        cuantas_de_la_cuenta,
    )


def olvidar_fallos_de_entrada(request, correo: str) -> None:
    """La entrada ha ido bien: se borran los fallos **de esa cuenta**.

    Los de la dirección **no se borran**: si se borraran, quien tiene una cuenta buena
    podría ir probando claves de otras y limpiar el contador entrando en la suya cada
    pocos intentos. El precio es que los fallos de un sitio se acumulan durante la
    ventana aunque alguno acabe bien, y es el precio correcto.
    """
    ENTRADAS_POR_CUENTA.olvida(clave_de_entrada_por_cuenta(correo))


def limpiar_todo() -> None:
    """Para los tests: dejar los contadores como recién arrancados."""
    for limitador in _LOS_DE_ESTE_MODULO:
        limitador.limpiar()
