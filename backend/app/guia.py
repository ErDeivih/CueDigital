"""**El cuaderno guiado**: qué toca hacer en una tierra y a partir de cuándo (10/11/2026).

## Para qué existe

David lo pidió como «(7) un cuaderno guiado que diga qué falta». La app ya decía qué falta para
cumplir con la Junta (`que-falta`), pero no **qué toca hacer en una tierra concreta y con qué fecha**.
Eso es lo que hace falta de pie en la parcela: «de esta tierra no puedes cosechar hasta el 20 de
noviembre» o «no vuelvas a entrar hasta el día 12».

## Lo que NO hace

- **No inventa plazos.** Solo usa lo que está apuntado: la fecha del tratamiento y los días de
  plazo de seguridad y de reentrada que trae la etiqueta del producto (o los que escribió el
  agricultor). Si el dato no está, no se calcula nada: se dice que no se sabe.
- **No es un consejo agronómico.** No dice «fumiga ahora» ni elige producto: dice cuándo termina
  un plazo que ya está apuntado. Lo que no está apuntado, no se lo inventa.

## Cómo se usa

`lo_que_toca()` es una función **pura** (sin base de datos, sin servidor), igual que `legal.py`: se
puede probar con fechas fijas y no depende de qué día se ejecute. Devuelve una lista de avisos con
su **código** y su **estado**; el texto lo pone `textos.py` y la pantalla lo compone, para que no
haya dos vocabularios.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# Un plazo que termina dentro de estos días se enseña como **aviso**: es el momento de mirarlo
# antes de organizar la cosecha o de volver a la parcela.
DIAS_DE_AVISO = 3

# Los tres estados posibles de un plazo, y ninguno más. «No lo sé» no es «no hay plazo».
VENCIDO = "vencido"
HOY = "hoy"
PROXIMO = "proximo"
ABIERTO = "abierto"
SIN_FECHA = "sin-fecha"


@dataclass(frozen=True)
class Tarea:
    """Un aviso del cuaderno guiado: qué es, desde/para cuándo y cómo de cerca está."""

    codigo: str
    fecha: date | None
    estado: str
    dias: int | None = None

    def como_diccionario(self) -> dict:
        return {
            "codigo": self.codigo,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "estado": self.estado,
            "dias": self.dias,
        }


def _estado_de_un_plazo(fecha_limite: date, hoy: date) -> tuple[str, int]:
    """Cuántos días quedan y en qué estado está el plazo.

    **Tres días o menos es aviso**: el agricultor tiene que enterarse antes de organizar el día.
    """
    dias = (fecha_limite - hoy).days
    if dias < 0:
        return VENCIDO, dias
    if dias == 0:
        return HOY, dias
    if dias <= DIAS_DE_AVISO:
        return PROXIMO, dias
    return ABIERTO, dias


def lo_que_toca(
    *,
    hoy: date,
    tratamientos: list[dict],
    tiene_cultivo: bool,
    campana_anio: int | None = None,
) -> list[dict]:
    """Los avisos de una tierra, ordenados por lo que corre más prisa.

    `tratamientos` son los apuntes de la tierra **del más nuevo al más viejo**, cada uno con
    `fecha` (date), `plazo_seguridad_dias` y `plazo_reentrada_dias` (enteros o `None`).

    - **Cosecha**: desde la fecha del último tratamiento con plazo de seguridad no se puede
      cosechar. Ese es el plazo que más se nota: si se cosecha antes, el producto va al mercado
      con residuos.
    - **Volver a entrar**: lo mismo con el plazo de reentrada, que es para las personas.
    - **Cultivo sin declarar**: si la tierra no tiene cultivo en la campaña, se dice, pero **sin
      fecha inventada**: no hay norma que ponga un día para eso.
    """
    tareas: list[Tarea] = []

    def el_ultimo(campo: str) -> dict | None:
        for tratamiento in tratamientos:
            if tratamiento.get(campo) is not None and tratamiento.get("fecha") is not None:
                return tratamiento
        return None

    for campo, codigo in (
        ("plazo_seguridad_dias", "cosecha"),
        ("plazo_reentrada_dias", "reentrada"),
    ):
        ultimo = el_ultimo(campo)
        if ultimo is None:
            continue
        limite = ultimo["fecha"] + timedelta(days=int(ultimo[campo]))
        estado, dias = _estado_de_un_plazo(limite, hoy)
        tareas.append(Tarea(codigo=codigo, fecha=limite, estado=estado, dias=dias))

    if not tiene_cultivo:
        tareas.append(Tarea(codigo="cultivo", fecha=None, estado=SIN_FECHA, dias=None))

    # Lo que corre más prisa primero: vencido (ya se puede, hay que saberlo) y hoy, después lo
    # próximo, y al final lo que está abierto o sin fecha.
    orden = {VENCIDO: 0, HOY: 1, PROXIMO: 2, ABIERTO: 3, SIN_FECHA: 4}
    tareas.sort(key=lambda tarea: orden.get(tarea.estado, 9))
    return [tarea.como_diccionario() for tarea in tareas]


def resumen_de_la_tierra(tareas: list[dict]) -> str:
    """Una frase para la cabecera: cuántos avisos hay y cuántos corren prisa.

    «Nada que mirar», «3 avisos, 1 corre prisa». Sirve para decir en la lista de tierras qué
    tierra hay que mirar sin abrirla.
    """
    if not tareas:
        return "nada"
    # Un plazo **vencido** no corre prisa: ya se puede hacer. La prisa es que el plazo termine hoy
    # o dentro de los próximos días; avisar de lo que ya pasó sería ruido.
    prisa = sum(1 for tarea in tareas if tarea["estado"] in (HOY, PROXIMO))
    if prisa == 0:
        return "tranquila"
    if prisa == 1:
        return "una-prisa"
    return "varias-prisas"
