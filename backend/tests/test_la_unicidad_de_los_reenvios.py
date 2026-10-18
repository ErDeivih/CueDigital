"""**Los 24 reenvíos tienen unicidad en la base** -por índice **o** por restricción- (18/10/2026).

### ***Y por que esta prueba existe, con su historia***

*El informe de la sesion decia «24 de 24 indices». **Era cierto por casualidad**: la comprobacion que lo respaldo
miraba `__table__.indexes`, **y tres de los modelos usan `UniqueConstraint`** -`NotaDeUnContacto`, `Tarea` y
`TrabajoParaUnTercero`-. *Al mirarlos con ese criterio incompleto salieron como «sin indice», y **eran un falso
aviso mio**, no un defecto del codigo.*

***Es el mismo error que la revision independiente me señalo***: *una comprobacion con un criterio incompleto que
despues denuncia un defecto. **Esta prueba mira las dos formas**, para que no vuelva a pasar.*

### ***Y lo que comprueba, ademas de que exista***

  · **las dos columnas**: *la unicidad es por **finca y clave**, no por clave sola -dos fincas pueden mandar la
    misma clave sin chocar-*;
  · **que sea unica de verdad** -no un indice normal-;
  · **y el recuento**: *si aparece un modelo 25 con la columna y sin unicidad, **falla y lo nombra**.*
"""

from __future__ import annotations

from sqlalchemy import UniqueConstraint

from app import models

# ***Las tres que usan restriccion en vez de indice***, nombradas para que se vea que se pensaron.
LAS_DE_RESTRICCION = {"NotaDeUnContacto", "Tarea", "TrabajoParaUnTercero"}


def los_modelos_con_clave_de_reenvio() -> list[str]:
    salida = []
    for nombre in sorted(dir(models)):
        clase = getattr(models, nombre)
        if not hasattr(clase, "__table__"):
            continue
        if "clave_de_reenvio" in {c.key for c in clase.__table__.columns}:
            salida.append(nombre)
    return salida


def la_unicidad_de(clase):
    """**Las dos formas**: *un indice unico o una restriccion unica, y en las dos, por finca y clave.*

    *Se devuelve una tupla `(como, columnas)` o `None` si no hay ninguna.*
    """
    for indice in clase.__table__.indexes:
        if indice.unique and "reenvio" in (indice.name or ""):
            return ("indice", [c.name for c in indice.columns])
    for restriccion in clase.__table__.constraints:
        if isinstance(restriccion, UniqueConstraint) and "reenvio" in (restriccion.name or ""):
            return ("restriccion", [c.name for c in restriccion.columns])
    return None


def test_son_veinticuatro_y_ninguno_se_ha_quedado_sin_unicidad():
    """*El recuento y la cobertura: **ninguno con la columna y sin unicidad**.*"""
    los = los_modelos_con_clave_de_reenvio()

    assert len(los) >= 24, f"***tienen que ser al menos 24***: {len(los)}"
    sin_unicidad = [nombre for nombre in los if la_unicidad_de(getattr(models, nombre)) is None]
    assert sin_unicidad == [], (
        f"***estos modelos llevan `clave_de_reenvio` y NO tienen unicidad***: {sin_unicidad}. "
        "Un reintento apuntaria dos filas -y en silencio-."
    )


# ***Y algunas cierran la clave por su PADRE***, que es una decision, no un descuido: *una averia es de **su**
# maquina, y la misma clave en otra maquina es otra accion -el movil manda una clave por formulario, y dos
# maquinas son dos formularios-.* Aqui se nombran para que se sepa quien tiene alcance de padre.
LAS_QUE_CIERRAN_POR_SU_PADRE = {
    # ***Y son TRES, medidos -no adivinados-***: *las tres de la **maquina**. Las demas cierran por finca y
    # clave, aunque el apunte cuelgue de una entrega o de un gasto: *el movil manda **una clave por accion**, y
    # la accion ya dice de que es.*
    "AveriaDeMaquina": "maquina_id",
    "InspeccionDeMaquina": "maquina_id",
    "LecturaDeContador": "maquina_id",
}


def test_la_unicidad_es_por_finca_Y_por_clave():
    """***Dos fincas pueden mandar la misma clave sin chocar.***

    *Si la unicidad fuera por la clave sola, la primera finca que usara una clave impediria a las demas -y el
    contrato dice «alcance de la clave», que es **por explotacion**-.*

    ***Y el orden importa***: *`explotacion_id` **primero** -es el alcance de la finca- y `clave_de_reenvio`
    **ultima** -la clave identifica la accion **dentro** de ese alcance-.*
    """
    for nombre in los_modelos_con_clave_de_reenvio():
        como, columnas = la_unicidad_de(getattr(models, nombre))
        assert columnas[0] == "explotacion_id", (
            f"***{nombre}***: la unicidad es {como} sobre {columnas}, y tiene que **empezar** por "
            "`explotacion_id` -el alcance es la finca-"
        )
        assert columnas[-1] == "clave_de_reenvio", (
            f"***{nombre}***: la unicidad es {como} sobre {columnas}, y tiene que **acabar** en "
            "`clave_de_reenvio` -la clave identifica la accion dentro del alcance-"
        )


def test_y_las_que_cierran_la_clave_por_su_padre_son_las_que_se_saben():
    """***El alcance de la clave, dicho***: *la mayoria son por finca y clave; **nueve** cierran ademas por su
    padre -la maquina, la entrega, el gasto...-, y eso es una decision: la misma clave en otra maquina es otra
    accion.*

    *Y si aparece una mas, **se sabe** en vez de pasar desapercibida.*
    """
    con_padre = {}
    for nombre in los_modelos_con_clave_de_reenvio():
        _como, columnas = la_unicidad_de(getattr(models, nombre))
        if len(columnas) > 2:
            con_padre[nombre] = columnas[1]

    assert con_padre == LAS_QUE_CIERRAN_POR_SU_PADRE, (
        f"***cambio el alcance de alguna clave***: antes {sorted(LAS_QUE_CIERRAN_POR_SU_PADRE)}, "
        f"ahora {sorted(con_padre)}"
    )


def test_y_las_tres_de_restriccion_siguen_siendo_las_tres():
    """*Para que no se cambie una forma por otra sin darse cuenta: **el guardian mira las dos, pero el cambio se
    sabe**.*"""
    de_restriccion = {
        nombre
        for nombre in los_modelos_con_clave_de_reenvio()
        if la_unicidad_de(getattr(models, nombre))[0] == "restriccion"
    }
    assert de_restriccion == LAS_DE_RESTRICCION, (
        f"***cambio la forma de la unicidad***: antes {sorted(LAS_DE_RESTRICCION)}, "
        f"ahora {sorted(de_restriccion)}"
    )
