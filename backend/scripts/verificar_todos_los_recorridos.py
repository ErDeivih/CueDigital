"""***Todos los recorridos, de una vez*** (22/10/2026).

*Cada corte tiene su instrumento, y **pasan uno a uno**. Lo que falta es pasarlos **todos juntos**, que es lo que el
encargo pide: «suites completas, humo y recorridos reales sobre la misma entrega integrada».*

*Esto los anda todos, **cada uno con su servidor temporal y su base temporal** -no se tocan los datos de nadie-, y
dice al final cuales pasan y cuales no.*

Uso:  python scripts/verificar_todos_los_recorridos.py
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import time

sys.path.insert(0, "scripts")

from verificar_los_permisos_por_rol import PYTHON  # noqa: E402

# *Los recorridos, en el orden en que se fueron construyendo.*
LOS_RECORRIDOS = [
    # ***La PAC se anda con su andador, no con su comprobador*** (22/10/2026): *`verificar_el_recorrido_de_la_pac`
    # **no levanta servidor**: espera uno. El que lo levanta es `andar_el_recorrido_de_la_pac`, y es el que hay que
    # llamar. Se vio porque el andador lo llamo a el y fallo con un error de conexion en tres segundos.*
    ("la PAC", "andar_el_recorrido_de_la_pac.py"),
    ("la cola sin conexion", "verificar_que_la_cola_no_cruza_cuentas.py"),
    ("los permisos por rol", "verificar_los_permisos_por_rol.py"),
    ("los estados de fallo", "verificar_los_estados_de_fallo.py"),
    ("los enlaces de las tierras", "verificar_los_enlaces_de_las_tierras.py"),
    ("las tres anchuras", "verificar_las_anchuras_de_las_tierras.py"),
    ("volver de la ficha", "medir_la_vuelta_de_la_ficha.py"),
    ("el tacto y el foco", "medir_el_tacto_y_el_foco.py"),
    ("el contraste", "medir_el_contraste.py"),
    ("el zoom y lo que se anuncia", "medir_el_zoom_y_lo_que_se_anuncia.py"),
    ("el escape y el foco de regreso", "verificar_el_escape_y_el_foco.py"),
    ("el recorrido de la tierra", "verificar_el_recorrido_de_la_tierra.py"),
    ("el recorrido del dinero", "verificar_el_recorrido_del_dinero.py"),
    ("el recorrido del papel", "verificar_el_recorrido_del_papel.py"),
    ("el recorrido de la compra", "verificar_el_recorrido_de_la_compra.py"),
]


def main() -> int:
    los_que_fallan = []
    print(f"== Los {len(LOS_RECORRIDOS)} recorridos, de una vez ==")
    for nombre, guion in LOS_RECORRIDOS:
        el_camino = pathlib.Path("scripts") / guion
        print(f"\n--- {nombre} ({guion}) ---")
        sys.stdout.flush()
        el_principio = time.time()
        la_pasada = subprocess.run(  # noqa: S603
            [str(PYTHON), str(el_camino)],
            cwd=".",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        lo_que_tardo = time.time() - el_principio
        la_ultima = ""
        for linea in (la_pasada.stdout or "").splitlines():
            if "Comprobaciones:" in linea or "RESULTADO:" in linea:
                la_ultima = linea.strip()
        print(f"  codigo {la_pasada.returncode} · {lo_que_tardo:.0f}s · {la_ultima[:110]}")
        if la_pasada.returncode != 0:
            los_que_fallan.append(nombre)
            # *Y se enseñan las lineas de fallo, que es lo que hace falta para arreglarlo.*
            for linea in (la_pasada.stdout or "").splitlines():
                if "[FALLO]" in linea:
                    print(f"    {linea.strip()[:160]}")
            if la_pasada.stderr:
                print(f"    stderr: {la_pasada.stderr.strip()[:300]}")
    print("\n== Resumen ==")
    if not los_que_fallan:
        print(f"  ***los {len(LOS_RECORRIDOS)} recorridos pasan***")
        return 0
    print(f"  ***fallan {len(los_que_fallan)}: {', '.join(los_que_fallan)}***")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
