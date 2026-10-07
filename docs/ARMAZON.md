# El armazón nuevo: el menú agrupado y la navegación completa

> **Qué es este documento.** El informe de las comprobaciones del encargo del rediseño
> (`docs/REDISENO_V0_STITCH_20261007.md`, apartado 3) sobre el menú agrupado y la navegación completa:
> **qué comprueba cada cosa, qué salió (con números), qué falló y qué no se ha podido comprobar**.
>
> Escrito el **07/10/2026**, midiendo contra un servidor de pruebas propio (`uvicorn` en el puerto **8027**,
> base SQLite temporal). El puerto 8000 (el de David) no se ha tocado.

## 1. Los tres ficheros de esta comprobación

| Fichero | Qué hace |
|---|---|
| [`backend/tests_js/armazon.test.js`](../backend/tests_js/armazon.test.js) | **16 pruebas** de `node --test`, sin navegador: el componente `Marco` (con `grupos` y sin `grupos`), la tabla `MODULOS`/`GRUPOS_DEL_MENU` de `app.js` y que las acciones de abrir y cerrar el menú estén escritas **literales** |
| [`backend/scripts/comprobar_el_armazon.py`](../backend/scripts/comprobar_el_armazon.py) | **La comprobación en un navegador de verdad** (`navegador_cdp.py`): Chrome sin ventana, pilas de anchos, clics y teclas de verdad. Imprime **comprobaciones y fallos** |
| este documento | El informe |

Se ha trabajado **solo** sobre estos tres ficheros. No se ha tocado `app.js`, `estilos.css`,
`react/piezas/marco.js`, `index.html`, `textos.py` ni ningún test que ya existía.

## 2. Cómo se corre

```powershell
cd F:\EspacioCodigo\CueDigital\backend
$env:CUEDIGITAL_DATABASE_URL="sqlite:///$env:TEMP\cd-armazon-sub.db"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8027      # en otra terminal
node --test "tests_js/armazon.test.js"
..\.venv\Scripts\python.exe scripts\comprobar_el_armazon.py http://127.0.0.1:8027
```

## 3. Los números que salieron (07/10/2026)

| Qué | Resultado |
|---|---|
| `node --test "tests_js/armazon.test.js"` | **16 pruebas, 16 en verde, 0 rojas** (399 ms) |
| `comprobar_el_armazon.py` (390, 712, 1024, 1440 px + la pantalla de entrar) | **61 comprobaciones, 0 fallos** (49 s) |
| `node --test "tests_js/react.test.js"` (las pruebas que ya existían del armazón) | **332 en verde** |
| `node --test "tests_js/interfaz.test.js"` (el cableado de `app.js`) | **338 en verde** |
| `pytest tests/test_el_armazon_del_ordenador.py tests/test_los_botones_hacen_algo.py` | **17 en verde** |

> **Sobre qué versión del programa se midió.** El armazón se estaba escribiendo **a la vez** que estas
> comprobaciones. La pasada buena del navegador es de las **17:55** del 07/10/2026, y en ese momento las
> fechas de los ficheros del armazón eran: `marco.js` 17:39, `index.html` 17:40, `estilos.css` 17:44 y
> `app.js` **17:51** (todas anteriores). Si alguien toca el armazón después de esa hora, esta foto se queda
> atrás: se vuelve a correr el guion, que tarda **49 segundos**.

### El menú, a cada ancho

| | 390 px | 712 px | 1024 px | 1440 px |
|---|---|---|---|---|
| Renglones en el documento | 21 | 21 | 21 | 21 |
| Con el menú **cerrado** (lo que se ve al cargar) | 0 de 21 | 0 de 21 | *no aplica: el menú lateral sale solo* | *no aplica* |
| Pulsando el botón de abrir | 21 de 21 | 21 de 21 | — | — |
| Con Escape | 0 de 21 | 0 de 21 | — | — |
| Grupos con su nombre | 5 de 5 | 5 de 5 | 5 de 5 | 5 de 5 |
| Renglones dentro de su grupo | 21 de 21 | 21 de 21 | 21 de 21 | 21 de 21 |
| Pulsaciones hasta **Cuentas** tabulando | **12** (Mayús+Tab) | **12** | **13** (Tab) | **13** |
| Pulsaciones hasta pasar por los **21** renglones | 27 | 27 | 24 | 24 |
| Enter en el renglón de Cuentas | abre «Mis cuentas» | abre «Mis cuentas» | abre «Mis cuentas» | abre «Mis cuentas» |

Los nombres de los grupos son **los del servidor** (`/api/interfaz` → `textos.MENU`):
`Inicio`, `El campo`, `La gestión`, `El cuaderno`, `Ajustes`. El servidor manda los cinco; ninguno sale en
blanco.

**Y el renglón de «Normativa» no existe**, que es lo que hay que comprobar: a ningún ancho hay un renglón
`menu-*` que no esté en la tabla `app.js`, ni un grupo de más, ni el texto «Normativa» dentro del armazón.
El motivo está escrito en `app.js`: no hay ninguna pantalla que sea eso, y un renglón que no lleva a ninguna
parte es peor que no tenerlo.

### Antes de que estuviera implementado

Cuando llegué, `marco.js` todavía no aceptaba `grupos` ni existían `menu-abrir`/`menu-cerrar`. Las pruebas
se escribieron igualmente contra el contrato y **salieron en rojo diciendo exactamente qué faltaba** (el
armazón pintaba la lista plana y los dos botones no existían). La implementación llegó mientras medía, y la
pasada completa en verde es la de la tabla de arriba (390, 712, 1024 y 1440 px).

## 4. Qué comprueba cada cosa, una por una

### 4.1. `armazon.test.js` (sin navegador)

Mismo arnés que `react.test.js`: los ficheros de `web/vendor` se cargan con `vm.runInThisContext` y el
componente se convierte en HTML con `renderToStaticMarkup`. **Sin dependencias nuevas.** La tabla
`MODULOS`/`GRUPOS_DEL_MENU` se lee de `app.js` con un lector propio que **se salta comentarios y cadenas**
(una tabla de este proyecto lleva corchetes dentro de los comentarios) y la convierte a dato de este mundo
(`JSON`), porque lo que devuelve `vm` es de otro *realm* y `assert.deepEqual` lo rechaza aunque el contenido
sea el mismo — costó una vuelta: la prueba decía «actual: [] expected: []»).

| Prueba | Qué comprueba |
|---|---|
| la tabla de grupos es la del contrato | Los cinco (`inicio`, `campo`, `gestion`, `cuaderno`, `ajustes`), en su orden, y **ninguno inventado** |
| cada renglón lleva su grupo | Los 21 tienen `grupo`, y es uno de los cinco |
| son 21, sin repeticiones, y ningún grupo vacío | El número del contrato, claves únicas y ningún grupo que saldría con su nombre y sin renglones |
| el nombre de cada grupo está en el servidor | Su texto es `menu.grupo_<clave>`: la frase no se escribe en `app.js` |
| la agrupación es visual | **Ningún grupo lleva acción propia** (sería una pantalla de más) y **cada renglón lleva la suya** |
| cada grupo sale con su nombre y sus renglones dentro | Con etiquetas únicas: cada nombre una vez, cada renglón entre el suyo y el siguiente grupo, en el orden que venga |
| el orden no se toca | Con los grupos y los renglones al revés, salen al revés |
| no se cuelan ni se pierden renglones | Los tres que se le pasan, y ni uno más |
| con `grupos` no se pinta además la lista plana | No saldrían renglones repetidos |
| sin `grupos`, la lista plana | La de siempre, sin ningún nombre de grupo y con sus acciones |
| cada renglón conserva todo | `id="menu-<clave>"`, `data-accion`, sus `data-*`, la clase del menú y `aria-current` solo en el activo (y **uno solo**) |
| con los 21 de verdad, agrupados salen los mismos | Ata el componente con la tabla de `app.js`: los mismos `id` y cada uno en su grupo |
| los botones de abrir y cerrar, literales | `data-accion="menu-abrir"` y `"menu-cerrar"` escritos **literalmente** en lo que se sirve, y atendidos por el manejador de clics (`nombre === "menu-abrir"`) |
| guardianes del lector | Que el lector encuentra los 21 renglones y los 5 grupos, y que el buscador de acciones **no se cree** una acción puesta por variable (`accion=${...}`) |

Los dos últimos son los guardianes que pide `AGENTS.md`: **un test que lee ficheros y los interpreta necesita
su propia prueba**, porque uno que se come el fichero es peor que no tenerlo.

### 4.2. `comprobar_el_armazon.py` (el navegador)

61 comprobaciones. Por cada ancho: los renglones están y no hay ninguno de más · no hay nada de «Normativa» ·
el estado inicial no está a medias (0 o 21, nunca 17) · el botón de abrir está y se ve · se abre con el ratón
y salen los 21 · se cierra con su botón y no queda ninguno · se llega al botón **tabulando** y **Enter** lo
abre · **Escape** lo cierra · los cinco nombres del servidor salen y **se ven** · cada renglón está dentro de
su grupo (medido **por anidamiento** y, si fallara, **por posición**) · tabulando se pasa por los 21 ·
tabulando se llega a Cuentas y Enter abre «Mis cuentas» · al abrir una pantalla el panel no se queda encima
(hallazgo). Sin sesión: la pantalla de entrar se abre, **no se ve ni un renglón** de menú (ni hay ninguno en
el documento: el armazón no se pinta) y `#/cuentas` **no abre una ficha**.

Dos cosas que merecen decirse del método, porque son las que hacen que la medida valga:

- **El grupo de cada renglón se lee de `app.js` por un lado y del DOM por otro, y se comparan.** El DOM
  decide qué se ve; `app.js` dice qué debería verse. Si el programa agrupara mal, se vería aquí.
- **El paseo con el teclado va hacia atrás en el móvil y hacia adelante en el ordenador, y se dice por qué.**
  El armazón (`#marco`) está **antes** que la cabecera en el documento: en el ordenador el menú sale al
  cargar y el `Tab` entra en él de frente; en el móvil se abre con un botón que está **después**, así que el
  `Mayús+Tab` entra por el final del armazón sin dar la vuelta a la página. El resumen de cada paseo dice en
  qué dirección va, dónde empieza y cuántas pulsaciones cuesta: «12 pulsaciones» sin decir desde dónde no
  diría nada.

## 5. Lo que falló

**En mis comprobaciones: nada.** Las 61 en verde y las 16 pruebas de JavaScript en verde.

**Y se ha comprobado que las comprobaciones pueden fallar** (`--romper`, sin tocar ningún fichero del
programa). Cada rotura produce **exactamente un fallo**, y el suyo:

| Rotura | Qué sale |
|---|---|
| `--romper selector` (el selector del botón de abrir, por uno que no existe) | `[FALLO] 390 px: el botón de abrir el menú se puede pulsar ([data-accion="menu-abrir-NO-EXISTE"])` — 11 comprobaciones, 1 fallo |
| `--romper renglon` (se pide el renglón «Normativa», que no existe) | `[FALLO] 390 px: los 22 renglones del menú están en el documento (faltan: ['menu-normativa'])` — 22 y 1 |
| `--romper grupo` (se pide el grupo «Normativa», que no existe) | `[FALLO] 390 px: los 6 grupos salen con su nombre (los del servidor) — sin nombre: ['Normativa']` — 22 y 1 |

**En el árbol, y no es mío** (lo cuento para que se arregle donde toca):

1. **`react.test.js` tenía un rojo cuando empecé a medir** — `la barra dice el año y la cuenta, y lleva el
   botón de apuntar` compara la lista **exacta** de acciones del armazón y el botón nuevo de cerrar el menú
   (`menu-cerrar`, que el componente pinta siempre y esconde el CSS en el ordenador) no estaba en la lista:
   `actual: ['menu-cerrar', 'ir-inicio', …]`, `expected: ['ir-inicio', …]`. **El coordinador lo ha arreglado
   mientras medía**: la última pasada de `react.test.js` está en **332 verdes, 0 rojos**.
2. **`tests/test_lista_de_la_junta.py` dice que la documentación miente con el número de pruebas de
   JavaScript**, y tiene razón **por mi fichero nuevo**: dice 1048 y hay **1064** (los 1048 de antes más las
   16 de `armazon.test.js`). El test es
   `TestElResumenCuadraConLaTabla::test_los_numeros_de_test_de_la_documentacion_no_se_quedan_viejos`
   (`pytest tests/test_lista_de_la_junta.py -k numeros_de_test`). **No lo he arreglado porque esos tres
   ficheros no son míos**; hay que poner **1064** en los tres sitios:
   - `README.md:1381` — `node --test "tests_js/*.test.js"   # 1048 tests`
   - `AGENTS.md:52` — `# JavaScript (1048 tests): …`
   - `docs/LO_QUE_PIDE_LA_JUNTA.md:22` — «… y 1048 de JavaScript.»

## 6. Lo que **no** se ha podido comprobar (y por qué)

1. **«Con el menú cerrado, ningún renglón visible» a 1024 y 1440 px.** A partir de 64 rem (1024 px) el menú
   es el lateral del ordenador y **sale solo al cargar**: no hay estado «cerrado» que medir. Se comprueba lo
   que sí es exigible —que los 21 estén a la vista y se tabule por ellos **sin pulsar nada**— y se dice como
   hallazgo. Lo mismo con el botón de cerrar y Escape: por encima de 64 rem no tienen sentido (el CSS esconde
   el botón), y ahí no se comprueban.
2. **«Que el menú ofrezca Normativa».** El encargo lo pide en su lista, y el contrato del coordinador dice a
   propósito que **no existe** (no hay pantalla que sea eso). Se comprueba la parte que sí se puede: que el
   renglón de **Cuentas** se alcanza tabulando a todos los anchos, y que **no** hay ningún renglón ni grupo
   inventado para llenar ese hueco. Lo que no se puede comprobar es una pantalla que no existe.
3. **La pantalla de entrar, a 390, 712 y 1024 px.** Se comprueba a **1440 px** (donde el armazón del
   ordenador es lo que más se ve) y el caso de la dirección de dentro. A los otros tres anchos el armazón ni
   se pinta, así que la comprobación no cambiaría; no se ha repetido por tiempo, no por imposibilidad.
4. **Que la agrupación sea *visual* también para un lector de pantalla.** Se mide que el renglón esté
   **dentro** del grupo (anidamiento) y que el grupo tenga su nombre; el componente añade `aria-labelledby` a
   la lista de cada grupo, pero **eso no se ha comprobado con un lector de pantalla de verdad**.
5. **La pinta del panel** (contraste, tamaños, que nada se salga de la pantalla al 200 %). Eso es de
   `DESIGN.md` y de `comprobar_teclado_y_zoom.py`, que no son de este encargo; aquí solo se mide lo que se ve
   (`checkVisibility`) y por dónde va el foco.
6. **`comprobar_en_un_navegador.py`/`humo.py` y la suite entera.** No se han corrido: el coordinador estaba
   editando `app.js`, `estilos.css`, `index.html` y `marco.js` a la vez y la consigna era correr **lo mío**.
   Lo que sí se ha corrido son los tres ficheros de JavaScript que tocan el armazón y los dos guardianes de
   Python, y están verdes (arriba).

## 7. Los hallazgos (medidos, no fallos)

Se imprimen con las comprobaciones y no cuentan como fallo porque el contrato no los pide. Son tres cosas
que se ven midiendo y conviene decidir:

1. **Al abrir el menú con `Enter`, el foco se queda en el botón de la cabecera**, que el panel tapa: para
   entrar en el menú hay que dar la vuelta a la página con el tabulador (o ir hacia atrás, que es lo que hace
   el paseo). Pasa igual a 390 y a 712 px. Mover el foco al primer renglón (o al panel) al abrirlo lo
   arreglaría.
2. **Al abrir una pantalla desde el panel, el panel se queda abierto encima.** Medido a 390 y 712: tras
   pulsar `Enter` en Cuentas, «Mis cuentas» se abre **detrás** del panel, y el agricultor no ve lo que acaba
   de abrir hasta que lo cierra. Cerrar el panel al navegar (como hace el resto de la aplicación) lo
   arreglaría.
3. **A 1024 y 1440 px el menú sale solo** (no hay botón que pulsar): es la decisión de diseño del armazón de
   escritorio, y se apunta para que quede escrito que la comprobación de «cerrado» solo aplica por debajo de
   64 rem.

## 8. Lo que este encargo deja atado

- El menú tiene **5 grupos y 21 renglones**, los del contrato, y **ninguno inventado**.
- **La agrupación es visual**: ningún grupo lleva acción, cada renglón sigue llevando a su pantalla, y al
  pulsar `Enter` en un renglón se abre la pantalla (no un grupo) — comprobado **tabulando**, no escribiendo
  la dirección.
- **Por debajo de 64 rem el menú se abre** con su botón (y con `Enter`), se cierra con el suyo y con
  `Escape`, y **estando cerrado no se ve ni un renglón** (no queda nada tabulable fuera de la vista).
- **Sin sesión no hay menú de negocio**: ni un renglón en el documento, y una dirección de dentro no abre una
  ficha.
- Y si mañana alguien quita un grupo, mete un renglón que no lleva a ninguna parte, deja el menú a medias o
  rompe el tabulado, **hay 16 pruebas y 61 comprobaciones que lo dicen**.
