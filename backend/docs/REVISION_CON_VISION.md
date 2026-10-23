# La revisión con visión

> ## ***22/10/2026 — las capturas son NUEVAS y la revisión anterior ya no vale***
>
> *Las quince capturas de `docs/capturas-de-anchuras/` **se han regenerado después de aplicar los tres cambios que
> pidió la revisión** —la acción duplicada de Inicio (A1), los filtros que tapaban las tierras (C2) y la cabecera a 1024
> (C1)—. **Las que revisó Codex son de antes de esos cambios**: lo que se ve en ellas ya no es lo que hace el programa.*
>
> ***Lo comprobado de las nuevas, que se puede comprobar sin ojos***:
>
> | | |
> |---|---|
> | **cuántas** | **15** *(tres pantallas × cinco anchuras)* |
> | **su tamaño** | ***todas miden lo que anuncian*** *(comprobado leyendo la cabecera del PNG: 320x700, 390x844, 712x900, 1024x768 y 1440x900)* |
> | **la identidad de la pantalla** | *el capturador la comprueba con una **señal** por pantalla (`LAS_SENALES`): que esté el botón «MI CUADERNO» en Inicio, el buscador en Tierras, el de «ECHAR PRODUCTO» en el Cuaderno* |
>
> ***Lo que NO se puede comprobar desde aquí***: *si la pantalla **se entiende**, si la jerarquía es la correcta y si
> sigue pareciendo CUE Digital. **Eso necesita ojos, y esta sesión no los tiene.***
>
> ***Así que la revisión con visión se rehace sobre estas quince.*** *La tabla de abajo sigue siendo el sitio para
> rellenarla.*

---

# Revisión visual independiente — 22/10/2026

**Revisor: Codex, con lectura de imágenes. Resultado D05: CAMBIOS_SOLICITADOS.**
Se han visto las quince capturas originales y las quince corregidas; no se aprueba todavía D05.
Esto revisa las primeras vistas de tres pantallas con datos ficticios, no todas las funciones,
una prueba de usabilidad con agricultores ni una auditoría de accesibilidad completa.

## Evidencia corregida

Las cinco imágenes originales llamadas `inicio` mostraban «Esa dirección no lleva a ninguna parte»:
el capturador abría `#/inicio`, que no es la dirección de inicio. Además, sus tamaños reales eran:

| Etiqueta original | PNG real |
|---|---|
| 320×700 | 500×605 |
| 390×844 | 500×749 |
| 712×900 | 696×805 |
| 1024×768 | 1008×673 |
| 1440×900 | 1424×805 |

Constructor de ventana no equivale a viewport. El capturador ahora usa `nav.medir`, abre `#/`,
exige un elemento propio de cada pantalla y comprueba `innerWidth/innerHeight` antes de guardar.
Se sustituyeron las quince imágenes por capturas de esas rutas, con dimensiones PNG exactas,
y se revisaron visualmente después. Ubicación real desde la raíz: `backend/docs/capturas-de-anchuras/`.

## Resultado por captura

**C:** cambios necesarios. **A:** anotación de jerarquía. **V:** conforme para el estado mostrado,
con las limitaciones de esta revisión. Firma de todas las celdas: Codex, 22/10/2026.

| Pantalla | 320×700 | 390×844 | 712×900 | 1024×768 | 1440×900 |
|---|---|---|---|---|---|
| Inicio | A1 | A1 | A1 | C1, A1 | A1 |
| Tierras | C2 | C2 | C2 | C1, C2 | C2 |
| Cuaderno | V | V | V | C1 | V |

Cada celda corresponde a `<pantalla>-<ancho>x<alto>.png` en la carpeta enlazada:
[inicio](capturas-de-anchuras/inicio-390x844.png),
[tierras](capturas-de-anchuras/tierras-1440x900.png),
[cuaderno](capturas-de-anchuras/cuaderno-320x700.png).

### C1 — Cabecera de escritorio a 1024

Los textos de finca/campaña se superponen y el contexto de cuenta se recorta. La cabecera no
conserva una jerarquía legible al entrar en el breakpoint de escritorio. La captura exacta a
1024 sí activa el marco; la antigua de 1008 no lo hacía.

**Aceptación:** a 1024, 1100 y 1440 no hay intersecciones de texto ni controles tapados; cuenta,
finca y campaña se identifican, con nombres largos. Reorganizar o abreviar con etiqueta accesible,
sin reducir el suelo tipográfico ni el área de los controles. Repetir con zoom de escritorio real.

### C2 — Tierras: los resultados llegan demasiado tarde

En las cinco primeras vistas se ven sobre todo explicación y filtros. Ni a 1440×900 aparece
una tierra: búsqueda, cuatro grupos de opciones y agrupación empujan tabla/tarjetas y mapa hacia
abajo. Tener tarjetas más abajo no cumple por sí solo la experiencia de despacho ni la de campo.

**Aceptación:** búsqueda y contexto visibles; filtros avanzados plegables; filtros activos y
acción de quitarlos reconocibles; primeras tierras visibles sin atravesar todas las opciones.
En escritorio tabla/mapa coordinados; en móvil tarjetas legibles. Mantener orden, selección,
exportación y restauración de contexto. Probar tres y 64 tierras, filtros activos, vacío y fallo.
No resolverlo reduciendo letra o botones. Ver el contrato D04 existente.

### A1 — Inicio: acción duplicada

«HE HECHO UN TRABAJO» aparece antes de la pregunta y otra vez entre las seis acciones. En móvil
consume altura y compite con la acción principal. En escritorio se repite también entre los
atajos del panel. Resolver la duplicación conservando las seis acciones y su orden contractual;
si se mantiene un acceso adicional, justificar una tarea distinta y comprobar comprensión.

## Marca y lectura

Sí se reconoce CUE Digital: símbolo, verde propio, tipografía consistente y contraste visual
claro. En móvil de 320/390 el nombre ocupa dos líneas, pero no se ve cortado. Las tarjetas del
cuaderno vacío distinguen tarea pendiente y acción; no se han visto capturas de un cuaderno
poblado en esta serie. El menú de escritorio sigue largo y mezcla nombres con frases: necesita
la revisión de arquitectura de información ya especificada, no otra plantilla visual.

Esta lectura no certifica las medidas antiguas de contraste, tacto o zoom. Hay instrumentos que
usan `#/inicio` o no fijan viewport; repetir sus medidas con identidad de pantalla, dimensiones
reales y controles positivos. Pellizco (`visualViewport.scale`) no sustituye reflujo con zoom
de escritorio. No afirmar cumplimiento WCAG completo ni usabilidad real por estas capturas.
