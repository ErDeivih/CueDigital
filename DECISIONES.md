# DECISIONES — CueDigital

> Decisiones **Nivel 2** del protocolo de autonomía: se deciden sin parar la sesión, se ejecutan,
> y se anotan aquí **con el motivo**. David las revisa cuando quiere.

## 2026-11-04 · D01-R1: los rechazos pasan a un buzón (una clave por rechazo) en las dos orillas

**Decisión**: el vaciado de la cola escribe los rechazos con `cola.rechazos`
(`cuedigital.rechazado.<id_local>`, una clave por rechazo) y la pantalla los lee de ahí; se deja de
usar el array compartido `cuedigital.rechazados.<cuenta>` para escribir, y lo que haya en ese array
**se migra** al buzón al arrancar.

**Motivo**: con el array, dos rechazos simultáneos leen los dos la misma lista, cada uno escribe la
suya, y **uno de los dos desaparece**: no queda pendiente ni rechazado. Es la misma carrera que se
cerró en los pendientes (una clave por intención), viva en el array de rechazos. El buzón ya estaba
escrito y probado (`nucleo.js`, `crearBuzonDeRechazos`); lo que faltaba era **conectar las dos
orillas a la vez**, porque conectar solo la escritura dejaba a la pantalla leyendo el array viejo y
mintiendo (medido: el recorrido de la cola pasó a 9 con 2 fallos; ver commit `d8f64ad`).

**Reversibilidad**: sí. Los datos no se borran: se copian al buzón, se verifica la copia y **solo
entonces** se borra el origen; si la copia falla, el origen se queda. Un JSON corrupto se conserva.
Volver atrás es dejar de leer el buzón.

**Dueño**: cada rechazo lleva su `cuenta`. La pantalla enseña solo los de la cuenta abierta (y los
sin dueño solo cuando no hay sesión), que es exactamente lo que hacía la clave con dueño. Un rechazo
de A no se le enseña a B.

**Lo que NO cambia**: la forma de un pendiente, el turno, la migración de pendientes, la API ni los
textos que ve el agricultor.

**Comprobado (2026-11-04)**
- `node --test "tests_js/*.test.js"`: **1.228 superadas, 0 fallos** (eran 1.221: +7, contadas por el
  guardián de la documentación, que por eso se ha actualizado).
- `scripts/verificar_que_la_cola_no_cruza_cuentas.py` contra servidor y Chromium de verdad:
  **9 comprobaciones, 0 fallos**. La tercera sección es la que vale aquí: un apunte que el servidor
  rechaza **se aparta en su propia clave** y **la pantalla dice el motivo leyéndolo de ahí**.
- `pytest` completo: se anota en `ESTADO-AGENTE.md` con el resultado medido, no con el que había.
