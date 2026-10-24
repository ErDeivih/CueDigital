"""***La cola en IndexedDB, probada en el navegador de verdad*** (23/10/2026, D01 — P0).

*Las pruebas de `tests_js` corren en Node, donde **no hay IndexedDB**: lo que se demostró allí es la **lógica** del turno
sobre una base que serializa. Esto lo prueba **contra el IndexedDB de Chromium**, que es el que usa el agricultor.*

***Y prueba las tres cosas que la revisión pide***:

  · ***dos adquisiciones del turno a la vez***: *tiene que ganar **una**;*
  · ***dos apuntes a la vez***: *tienen que quedar **los dos**;*
  · ***la migración***: *lo que había en `localStorage` pasa a IndexedDB **con sus campos**, y **el origen se borra solo
    si están todos**.*

Uso:  python scripts/verificar_la_cola_en_indexeddb.py
"""

from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, "scripts")

from andar_el_recorrido_de_la_pac import el_servidor_temporal  # noqa: E402
from navegador_cdp import NavegadorDeVerdad  # noqa: E402
from verificar_los_permisos_por_rol import _poner_la_sesion, _una_cuenta_nueva  # noqa: E402

# ***Lo que se ejecuta dentro de la página***: *todo en una función asíncrona, y el resultado se deja en `window` para
# poder leerlo -la orden de CDP no espera promesas-.*
LA_PRUEBA = """
(async () => {
  const m = await import('/cola_en_indexeddb.js');
  const n = await import('/nucleo.js');
  const salida = {};

  // ---- 1 · el turno: dos a la vez, gana UNA ----
  const base = await m.abrirLaBase();
  const laBaseDelTurno = m.baseDelTurno(base);
  const [laDeA, laDeB] = await Promise.all([
    n.pedirElTurnoTransaccional(laBaseDelTurno, { clave: 'prueba.turno', dueno: '1:1', procesador: 'A', ahora: 1000 }),
    n.pedirElTurnoTransaccional(laBaseDelTurno, { clave: 'prueba.turno', dueno: '1:1', procesador: 'B', ahora: 1000 }),
  ]);
  salida.turno = { A: laDeA.turno, B: laDeB.turno };

  // ---- 2 · dos apuntes a la vez: quedan LOS DOS ----
  const laCola = m.colaEnIndexedDb(base, { nuevoId: () => 'x' + Math.random().toString(36).slice(2) });
  await Promise.all([
    laCola.apuntar({ id_local: 'A', datos: { nota: 'A' } }),
    laCola.apuntar({ id_local: 'B', datos: { nota: 'B' } }),
  ]);
  const losIds = (await laCola.leer()).map((uno) => uno.id_local).sort();
  salida.apuntar = losIds;

  // ---- 3 · la migración, con sus campos ----
  localStorage.setItem(
    'cuedigital.pendientes',
    JSON.stringify([
      { id_local: 'viejo-1', cuenta: '1:1', ruta: '/api/trabajos', datos: { nota: 'una', clave_de_reenvio: 'r-1' } },
    ]),
  );
  const laOtra = m.colaEnIndexedDb(base, { nuevoId: () => 'y' });
  const elParte = await laOtra.migrarDesde(localStorage);
  const losMigrados = (await laOtra.leer()).filter((uno) => uno.id_local === 'viejo-1');
  salida.migracion = {
    ...elParte,
    esta: losMigrados.length === 1,
    cuenta: losMigrados[0] ? losMigrados[0].cuenta : null,
    clave: losMigrados[0] && losMigrados[0].datos ? losMigrados[0].datos.clave_de_reenvio : null,
    origen: localStorage.getItem('cuedigital.pendientes'),
  };

  window.__resultado = salida;
})();
1
"""


def comprobar(bien: bool, que: str, encontre: str = "") -> bool:
    print(f"  [{'OK   ' if bien else 'FALLO'}] ***{que}***")
    if not bien and encontre:
        print(f"          encontre: {encontre[:400]!r}")
    return bien


def main() -> int:
    fallos = 0
    with el_servidor_temporal() as direccion:
        cuenta = _una_cuenta_nueva(direccion, "idb@prueba.local", "una-clave-larga-y-facil", "Id")
        with NavegadorDeVerdad(ancho=1200, alto=800) as nav:
            _poner_la_sesion(nav, direccion, cuenta["token"])
            nav.abrir(f"{direccion}/#/", esperar=3.0)
            time.sleep(2.0)
            print("== La cola en IndexedDB, en Chromium ==")
            nav.evaluar(LA_PRUEBA)
            el_resultado = None
            for _ in range(40):
                el_crudo = nav.evaluar("window.__resultado ? JSON.stringify(window.__resultado) : null")
                if el_crudo and el_crudo not in ("null", "undefined"):
                    el_resultado = json.loads(el_crudo)
                    break
                time.sleep(0.25)
            if el_resultado is None:
                print("  ***la prueba no devolvió nada***")
                return 1

            el_turno = el_resultado.get("turno") or {}
            print(f"  (el turno: A={el_turno.get('A')} · B={el_turno.get('B')})")
            fallos += not comprobar(
                [bool(el_turno.get("A")), bool(el_turno.get("B"))].count(True) == 1,
                "***dos adquisiciones a la vez: gana UNA***",
                str(el_turno),
            )

            los_ids = el_resultado.get("apuntar") or []
            print(f"  (los apuntes que quedan: {los_ids})")
            fallos += not comprobar(
                los_ids == ["A", "B"],
                "***dos apuntes a la vez: quedan LOS DOS***",
                str(los_ids),
            )

            la_migracion = el_resultado.get("migracion") or {}
            print(f"  (la migración: {la_migracion})")
            fallos += not comprobar(
                la_migracion.get("esta") is True and la_migracion.get("cuenta") == "1:1",
                "***lo viejo pasa con su dueño***",
                str(la_migracion),
            )
            fallos += not comprobar(
                la_migracion.get("clave") == "r-1",
                "***y con su clave de reenvío: el servidor no puede contar dos veces la misma intención***",
                str(la_migracion),
            )
            fallos += not comprobar(
                la_migracion.get("borrado") is True and la_migracion.get("origen") is None,
                "***y el origen se borra SOLO porque estaban todos***",
                str(la_migracion),
            )

    print(f"\nComprobaciones: 5   Fallos: {fallos}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
