# Estado del rediseño, y lo que queda por decidir

> **Para qué es este fichero.** El encargo del rediseño está en
> [`REDISENO_V0_STITCH_20261007.md`](REDISENO_V0_STITCH_20261007.md) y su material en
> `docs/stitch/crm_20261007/`. Esto es lo que **ya está hecho y medido**, y —lo que más importa— **la
> decisión que falta tomar** antes de seguir. Se escribe el 07/10/2026, al cerrar una sesión larga, para
> que la siguiente no tenga que reconstruir el estado leyendo diffs.

---

## 1. Lo que está entregado, y con qué se comprueba

| Qué | Cómo se comprueba (comando) |
|---|---|
| **El recorrido del encargo**: Inicio → Tierras → buscar entre 64 → ficha → planificar → historial → volver a la lista | `pytest tests/test_el_recorrido_se_anda.py` — **levanta el servidor en una base temporal y anda el recorrido con Chrome sin ventana**. 15 comprobaciones, 0 fallos. Capturas por paso en `%TEMP%\cd-ui\recorrido-*.png` |
| **Menú agrupado** (Inicio · El campo · La gestión · El cuaderno · Ajustes) y **navegación completa a 390/712 px** | `python scripts/comprobar_el_armazon.py <dir>` (61 comprobaciones) y `node --test tests_js/armazon.test.js` |
| **Contexto**: finca, campaña y **lo que falta por apuntar**, en la barra, desde cualquier pantalla | Dentro del recorrido: «la barra dice lo que falta por apuntar» |
| **Las cuatro pantallas se identifican** (ruta, elemento propio, sin formulario de entrar y con datos del servidor), con **casos negativos** | `python scripts/mirar_pantallas.py <dir>` — 16 capturas del escenario de 64 tierras, y el escenario vacío aparte (`--vacio`) |
| **Filtros conservados al volver** | `tests_js/interfaz.test.js` (memoria de vista) y `scripts/comprobar_en_un_navegador.py` |
| **La misma tierra se dice igual en el panel y en su ficha** | `tests_js/interfaz.test.js` → «la misma tierra se dice igual en el panel y en su ficha» |
| **El móvil abre la ficha** (y no otra pantalla distinta que el ordenador) | `python scripts/comprobar_la_ficha_en_el_movil.py <dir>` — 4 comprobaciones a 390 px |

**Números al cerrar esta sesión**: 4.583 pruebas de Python (0 rojos, 1 omitida), 1.065 de JavaScript
(0 rojos). Los tres documentos con los recuentos (`README.md`, `AGENTS.md`,
`LO_QUE_PIDE_LA_JUNTA.md`) los compara `test_lista_de_la_junta.py`.

**Los cuatro defectos de la revisión del 07/10** están cerrados, cada uno con su comprobación: el cuaderno
vacío no se contradice, los importes no se parten a ningún ancho, las capturas son de la explotación de 64
tierras, y la comprobación de pantalla mira la identidad y no una palabra suelta.

---

## 2. Lo que queda, y **la decisión que hay que tomar**

### 2.1 «Fichas únicas» — es una decisión, no un arreglo

Hoy **la misma tierra se puede mirar en cuatro pantallas**:

| Pantalla | Dónde se entra | Qué enseña |
|---|---|---|
| **El panel** de la fila | `elegir-fila`, en la lista de tierras (ordenador) | nombre, referencia, hectáreas y un botón a su historia |
| **Su historia** (`#/tierras/<id>/historial`) | el botón del panel, o la tarjeta en el móvil | qué hay hoy, los trabajos hechos, lo previsto, los costes |
| **Su cultivo** | `cultivo-decir` / «VER EL CULTIVO» | lo sembrado, para decir o corregir el cultivo |
| **Sus versiones** (`#/tierras/<id>/versiones`) | su dirección | la comparación entre campañas (contrato, §137-144) |

**Lo que ya se ha hecho** para que no se contradigan: el móvil abre la ficha (no el cultivo) y hay una
prueba que exige que el panel y la ficha digan **el mismo nombre y la misma superficie**.

**La decisión que falta**: **cuál de esas cuatro es *la* ficha de una tierra** y qué entra dentro. Las
opciones honestas son dos:

- **(a) La historia es la ficha** y las otras tres se convierten en **secciones suyas** (el panel desaparece
  como pantalla propia: al elegir una fila se abre la ficha; «decir el cultivo» y «versiones» pasan a ser
  bloques dentro). Es lo que pide el encargo y lo que menos pantallas deja.
- **(b) El panel es la ficha** y la historia es una sección suya. Deja la lista más rápida de usar (se ve
  la tierra sin salir de la lista) pero obliga a que la historia quepa en un panel lateral.

Lo que **no** se puede seguir es lo de ahora: cuatro sitios que enseñan trozos distintos del mismo bicho.
Y antes de tocar nada: **hay que decidir si las «versiones» (la comparación anual) se construyen** — el
contrato las pide y no existen (`versiones_api.py` no tiene variedad, siembra, cosecha, rendimiento ni
coste por campaña).

### 2.2 La búsqueda global — es una función nueva, no un cableado

La cabecera del encargo la pide. **No hay ninguna puerta en el servidor para eso**: comprobado, lo único
que existe es la búsqueda del SIGPAC (`parcelas.py:933`). Hace falta un endpoint que busque en tierras,
gastos, papeles, personas y máquinas a la vez, con su forma de decir «no hay nada» y su permiso por
explotación. Un buscador de mentira sería peor que no tenerlo.

### 2.3 Lo que **no** hay que rehacer

- El armazón (menú, contexto, navegación) está hecho y medido a los cuatro anchos.
- El recorrido está atado a la suite: **no se puede romper sin que salga en rojo**.
- Las medidas del despacho del encargo (menú 240 px, cuerpo 16 px, títulos 24/20, cifras 26, controles 44)
  **siguen sin aplicarse a propósito**: el encargo dice que hay que acordarlas y actualizar `DESIGN.md` y
  sus pruebas antes de tocarlas, y el campo se queda a 18 px.

---

## 3. Cómo se comprueba todo (los comandos, en orden)

```powershell
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests -q          # 4.583 (incluye el recorrido, con servidor y Chrome)
node --test "tests_js/*.test.js"                        # 1.065

# Y las comprobaciones de navegador, contra un servidor de pruebas (nunca el 8000):
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\cd-prueba.db"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8029   # en otra ventana
..\.venv\Scripts\python.exe scripts\comprobar_el_recorrido.py http://127.0.0.1:8029
..\.venv\Scripts\python.exe scripts\comprobar_el_armazon.py   http://127.0.0.1:8029
..\.venv\Scripts\python.exe scripts\mirar_pantallas.py        http://127.0.0.1:8029
..\.venv\Scripts\python.exe scripts\comprobar_la_ficha_en_el_movil.py http://127.0.0.1:8029
```

**Nunca** contra `backend/cuedigital.db` (la base del agricultor) ni contra el puerto 8000.
