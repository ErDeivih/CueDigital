titulo: CueDigital — documentacion de control
estado: en-curso
tarea: D01-R1 cerrado; D08 con regla de decisión (dos opciones, la más barata que cumpla)
nivel: 2
siguiente: propuesta de corpus y proveedor para D08
bloqueado: 
fecha: 2026-11-04

## Lo que se ha hecho en esta sesion

1. **D01-R1, cerrado**: dos rechazos que llegan a la vez ya no se pisan. El vaciado escribe en el buzon
   (`cuedigital.rechazado.<id>`, una clave por rechazo) y la pantalla lee de ahi; lo que quedara en las
   listas viejas se migra al arrancar, comprobando antes de borrar y conservando lo que no se puede leer.
   Motivo y reversibilidad en `DECISIONES.md`. Prueba del enchufe en `tests_js/interfaz.test.js`.
2. **El instrumento de D01, reparado**: `docs/revision-2026-10-19/reproducir-cola.mjs` abortaba con
   `ReferenceError: duenoDelTurno is not defined` y su modo `--concurrencia` medía la cola de array, que
   la aplicacion ya no usa. Ahora corre y mide el camino real. Salida en `reproducciones.txt`.
3. **Un fallo de andamio, arreglado**: la prueba de la migracion de nitratos dependia de la pagina de
   codigos de la consola; ahora el subproceso va en UTF-8 y, si falla, ensena la salida del guion.

## La ultima pasada, sobre este mismo HEAD

    Python       ***5647 superadas, 2 omitidas, 0 fallos***  (5649 recogidas)
    JavaScript   ***1228 superadas, 0 fallos***
    recorrido de la cola (Chromium + servidor de verdad)   ***9/9***
    humo         ***«RESULTADO: todo correcto»***
    `reproducir-cola.mjs`  siete casos en verde · `--concurrencia`: el camino real conserva las dos

## Lo que sigue abierto

- **D01 no esta cerrado**: le falta la aceptacion de **dos pestanas reales** (`navegador_cdp.py` maneja un
  solo destino). Es la tarea 3 del `BACKLOG.md` y la siguiente.
- **D07** (ciclo de vida de las raices de React) y la **intermitencia de la suite de Python**, en el
  `BACKLOG.md` con su criterio de aceptacion.
- **D08** espera decision de nivel 3 (corpus autorizado y proveedor); no se inventan metricas.
