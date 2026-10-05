"""La tabla de campos del descriptor oficial del cuaderno, para no mapear a ojo.

## Por qué existe esto

El descriptor oficial (`BdcSix-DS-DisenoCUE_3.11.4.xlsx`, en `data/iuws_fuentes/`) dice, campo
por campo, si es obligatorio, de qué tipo es y **contra qué catálogo valida**. Eso es
exactamente lo que hace falta para armar el JSON que se manda a la Junta, y es lo que durante
muchas rondas se creyó perdido.

El descriptor es un Excel, y el programa no lleva librería de Excel (a propósito: es un fichero
oficial que se lee una vez, no algo del día a día). Así que la tabla se extrae una vez con
`backend/scripts/sacar_campos_del_descriptor.py` a un JSON **derivado** y aquí se lee ese JSON.

Decisión que conviene entender: **el identificador del catálogo se guarda tal y como lo escribe
el descriptor**, en prosa («Catálogo de Eficacia del tratamiento»), y **no se traduce al
identificador de la tabla de SIEX**. Se comprobó que el descriptor no usa esos identificadores
—solo aparecen cuatro nombres de registros externos—, así que emparejarlos por parecido de
nombre sería adivinar. Lo que se puede afirmar es qué catálogo pide el descriptor, y eso es lo
que se dice.

## Lo que este módulo NO hace

No dice que un campo esté bien relleno. Para eso está el esquema JSON oficial, que se comprueba
con `iuws_cliente.errores_del_esquema`. Esto dice **qué pide el descriptor**, que es otra cosa:
el esquema te dice que falta un número, y esto te dice de qué catálogo tiene que salir.

## El descriptor y el esquema: coinciden más de lo que parecía

El esquema JSON es **el contrato** (es lo que se valida antes de mandar) y agrupa las actividades
en bloques con nombres como `TratamFito`, `Fertilizacion` o `Riego`. El descriptor usa **los
mismos nombres**: los 20 bloques del esquema tienen su bloque en el descriptor. El descriptor
trae uno de más, `ActividadAgraria`, que el esquema no tiene.

Aun así, **la estructura se saca del esquema y el tipo y el catálogo de cada campo, del
descriptor**: el esquema dice qué es obligatorio y de qué tipo, y el descriptor dice contra qué
catálogo valida cada cosa. Los dos se cotejan campo a campo, y hay tests que lo hacen.

### La trampa que costó un rato: el descriptor omite la llave `{`

Una tabla que se saque del descriptor mirando solo la llave `{` de las cabeceras de bloque
**está mal**: el documento oficial **omite esa llave en 14 cabeceras**, entre ellas `TratamFito`,
`SiembraPlantacion`, `HuertaVivero` y las listas de plagas, enfermedades, malas hierbas y
reguladores. Esos 14 bloques se cuentan como campos y sus campos cuelgan del bloque de arriba.

Se descubrió **cruzando la tabla con el esquema**, y llegó a estar escrito en la documentación que
«el descriptor no tiene `TratamFito`», que era falso. La marca que sí es fiable es la **columna de
ocurrencia** (`0..n`, `1..n`, `0..1`), que solo tienen los bloques. Y hay un test que exige que
**cada bloque del esquema aparezca en la tabla**, que es lo que habría cazado el fallo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# El mismo criterio que `iuws.py` para llegar a `data/`: desde `backend/app/`.
RAIZ = Path(__file__).resolve().parents[2]
RUTA_TABLA = RAIZ / "data" / "iuws_campos_del_cuaderno.json"

_tabla: dict | None = None
_leida = False


@dataclass(frozen=True)
class CampoDelDescriptor:
    """Un campo del descriptor, con lo que el descriptor dice de él."""

    ruta: str
    campo: str
    obligatorio: bool
    tipo_de_dato: str
    catalogo: str | None
    # Lo que el descriptor escribe sobre el campo. Aquí es donde están las convenciones que no
    # son un catálogo: «1 Siembra 0 Plantación», por ejemplo. Sin este texto habría que
    # suponerlas.
    descripcion: str = ""

    @property
    def bloque(self) -> str:
        """El bloque al que pertenece, que es el trozo de ruta de delante del campo."""
        return self.ruta.rsplit(".", 1)[0] if "." in self.ruta else ""


def cargar(ruta: Path | str | None = None) -> dict | None:
    """Lee la tabla derivada. Devuelve `None` si no está, y entonces todo se dice vacío.

    Mismo criterio que el resto de listas oficiales del proyecto: **si el fichero no está, el
    programa sigue funcionando y dice que no lo tiene**, en vez de suponer.
    """
    global _tabla, _leida
    destino = Path(ruta) if ruta else RUTA_TABLA
    _leida = True
    if not destino.exists():
        _tabla = None
        return None
    try:
        datos = json.loads(destino.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        _tabla = None
        return None
    if not isinstance(datos, dict) or not datos.get("registros"):
        _tabla = None
        return None
    _tabla = datos
    return _tabla


def tabla() -> dict | None:
    if not _leida:
        cargar()
    return _tabla


def olvidar() -> None:
    """Vacía la tabla leída. Existe para los tests: uno que carga la suya no puede dejarla
    puesta para el siguiente, o el orden de ejecución cambiaría los resultados."""
    global _tabla, _leida
    _tabla = None
    _leida = False


def cargada() -> bool:
    return bool(tabla())


def campos() -> tuple[CampoDelDescriptor, ...]:
    """Todos los campos del descriptor, en el orden del documento."""
    datos = tabla() or {}
    return tuple(
        CampoDelDescriptor(
            ruta=r.get("ruta", ""),
            campo=r.get("campo", ""),
            obligatorio=bool(r.get("obligatorio")),
            tipo_de_dato=r.get("tipo_de_dato", ""),
            catalogo=r.get("catalogo") or None,
            descripcion=r.get("descripcion", ""),
        )
        for r in datos.get("registros", ())
        if r.get("tipo") == "campo"
    )


def bloques() -> tuple[str, ...]:
    """Las rutas de los bloques, tal y como las numera el descriptor."""
    datos = tabla() or {}
    return tuple(
        r.get("ruta", "") for r in datos.get("registros", ()) if r.get("tipo") == "bloque"
    )


def campos_del_bloque(bloque: str) -> tuple[CampoDelDescriptor, ...]:
    """Los campos de ese bloque, comparando por la ruta entera **o por el último trozo**.

    Se admiten las dos formas a propósito: la ruta entera
    (`CUADERNO.ActividadesExplotacion.DGCs`) no deja dudas, y el último trozo (`DGCs`) es lo
    que escribirá quien llame. Y se compara sin distinguir mayúsculas, porque un fallo por una
    mayúscula se convierte en «no encuentro nada» sin decir por qué.

    **Ojo:** un nombre corto puede coincidir con varios bloques anidados. `DGCs`, sin ir más
    lejos, aparece dentro de `EnergiaUtilizada`, `Cosecha`, `Fertilizacion`, `PlanAbonado`,
    `ComercializacionVD`, `Analitica`, `Pastoreo`, `LaboresCulturales` y `Riego`. En ese caso
    **se devuelven los de todos**, y para distinguirlos está `CampoDelDescriptor.ruta`. No se
    elige uno «el más probable»: eso sería adivinar. Si hace falta uno solo, se pasa la ruta
    entera.
    """
    buscado = bloque.strip().lower()
    return tuple(
        c
        for c in campos()
        if c.bloque.lower() == buscado or c.bloque.rsplit(".", 1)[-1].lower() == buscado
    )


def bloques_que_coinciden(nombre: str) -> tuple[str, ...]:
    """Las rutas de bloque que acaban en ese nombre. Sirve para ver si un nombre corto es ambiguo."""
    buscado = nombre.strip().lower()
    return tuple(
        b for b in bloques() if b.lower() == buscado or b.rsplit(".", 1)[-1].lower() == buscado
    )


def obligatorios_del_bloque(bloque: str) -> tuple[CampoDelDescriptor, ...]:
    return tuple(c for c in campos_del_bloque(bloque) if c.obligatorio)


def catalogo_de(campo: str, *, bloque: str | None = None) -> str | None:
    """Qué catálogo pide el descriptor para ese campo, o `None` si no pide ninguno.

    Si hay varios campos con ese nombre en bloques distintos, se puede acotar con `bloque`.
    """
    buscado = campo.strip().lower()
    candidatos = [
        c
        for c in campos()
        if c.campo.lower() == buscado
        and (bloque is None or c.bloque.lower() == bloque.strip().lower())
    ]
    for candidato in candidatos:
        if candidato.catalogo:
            return candidato.catalogo
    return None


def bloques_con_catalogo() -> tuple[tuple[str, str], ...]:
    """Las **listas** del descriptor que traen su catálogo en la cabecera.

    Pasa con las listas de enfermedades, plagas, malas hierbas y reguladores: el catálogo está en
    la cabecera de la lista, no en cada elemento. Se devuelve tal cual, sin repartirlo a los
    campos de dentro: repartirlo sería decidir que el catálogo de la lista es el de cada elemento,
    y eso el documento no lo dice.
    """
    datos = tabla() or {}
    return tuple(
        (r.get("ruta", ""), r["catalogo"])
        for r in datos.get("registros", ())
        if r.get("tipo") == "bloque" and r.get("catalogo")
    )


def catalogos_que_pide() -> tuple[tuple[str, int], ...]:
    """Los catálogos que pide el descriptor, con cuántos sitios dependen de cada uno.

    Se cuentan los campos **y las listas**: una lista de enfermedades depende del catálogo de
    enfermedades igual que un campo suelto, y dejarla fuera haría que la lista de lo que hay que
    pedir a FEGA estuviera incompleta.

    Se devuelve el nombre **tal y como lo escribe el descriptor**, con su mayúscula y su acento.
    No se juntan los que solo se diferencian en eso: juntarlos sería decidir que son el mismo
    catálogo, y eso no lo dice el documento.
    """
    cuenta: dict[str, int] = {}
    for c in campos():
        if c.catalogo:
            cuenta[c.catalogo] = cuenta.get(c.catalogo, 0) + 1
    for _ruta, catalogo in bloques_con_catalogo():
        cuenta[catalogo] = cuenta.get(catalogo, 0) + 1
    return tuple(sorted(cuenta.items(), key=lambda par: (-par[1], par[0])))


def resumen() -> dict:
    """Lo que se puede decir de la tabla, para la pantalla de estado y para la ayuda.

    Si la tabla no está, se dice que no está y se devuelve todo vacío: nunca se inventa.
    """
    datos = tabla()
    if not datos:
        return {
            "cargada": False,
            "por_que_no": (
                "No está la tabla de campos del descriptor. Se rehace con "
                "scripts/sacar_campos_del_descriptor.py a partir del descriptor oficial."
            ),
            "fuente": None,
            "bloques": 0,
            "campos": 0,
            "obligatorios": 0,
            "catalogos": [],
        }
    return {
        "cargada": True,
        "fuente": datos.get("fuente"),
        "hoja": datos.get("hoja"),
        "bloques": datos.get("bloques", 0),
        "campos": datos.get("campos", 0),
        "obligatorios": datos.get("obligatorios", 0),
        "catalogos": [
            {"nombre": nombre, "campos": cuantos} for nombre, cuantos in catalogos_que_pide()
        ],
    }
