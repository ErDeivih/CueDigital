---
version: alpha
name: CUE Digital
description: El cuaderno de campo digital. Diseñado para un agricultor de 50 a 70 años, al sol, con una mano y sin cobertura.
colors:
  primary: "#1f4a2c"
  primary-container: "#2f6b40"
  primary-dark: "#0d2b18"
  primary-overlay: "#3a6446"
  primary-overlay-border: "#8fae97"
  on-primary: "#ffffff"
  tertiary: "#8a6a00"
  secondary-container: "#ffe9a8"
  on-secondary-container: "#3d2f00"
  surface: "#ffffff"
  surface-variant: "#f4f6f3"
  on-surface: "#10190f"
  on-surface-variant: "#43503f"
  outline: "#a9b6a8"
  error: "#8c1d18"
  error-dark: "#5c110d"
  error-container: "#fbe3e1"
  on-error-container: "#4a0f0b"
  focus: "#ffd24a"
typography:
  pregunta:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: 1.45rem
    fontWeight: 800
    lineHeight: 1.45
  titulo:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: 1.5rem
    fontWeight: 700
    lineHeight: 1.45
  boton:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: 1.1rem
    fontWeight: 700
  boton-principal:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: 1.35rem
    fontWeight: 700
  campo:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: 1.15rem
    fontWeight: 400
  cuerpo:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.45
  cuerpo-grande:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: 21px
    fontWeight: 400
    lineHeight: 1.45
  pista:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: 0.95rem
    fontWeight: 400
  dato-grande:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: 1.6rem
    fontWeight: 800
rounded:
  sm: 4px
  md: 8px
  lg: 10px
  xl: 14px
spacing:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  xxl: 32px
components:
  boton:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary}"
    typography: "{typography.boton}"
    rounded: "{rounded.xl}"
    height: 64px
    padding: 16px
  boton-principal:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary}"
    typography: "{typography.boton-principal}"
    rounded: "{rounded.xl}"
    height: 104px
    padding: 16px
  boton-claro:
    backgroundColor: "{colors.surface-variant}"
    textColor: "{colors.primary}"
    typography: "{typography.boton}"
    rounded: "{rounded.xl}"
    height: 64px
  boton-secundario:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.primary}"
    typography: "{typography.boton}"
    rounded: "{rounded.xl}"
    height: 64px
  boton-elegido:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.boton}"
    rounded: "{rounded.xl}"
    height: 64px
  boton-peligro:
    backgroundColor: "{colors.error}"
    textColor: "{colors.on-primary}"
    typography: "{typography.boton}"
    rounded: "{rounded.xl}"
    height: 64px
  boton-letra:
    backgroundColor: "{colors.primary-overlay}"
    textColor: "{colors.on-primary}"
    typography: "{typography.boton}"
    rounded: "{rounded.lg}"
    height: 48px
  cabecera:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.titulo}"
    height: 64px
    padding: 12px
  campo:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.campo}"
    rounded: "{rounded.xl}"
    height: 64px
    padding: 12px
  foco:
    backgroundColor: "{colors.focus}"
    size: 4px
  aviso:
    backgroundColor: "{colors.secondary-container}"
    textColor: "{colors.on-secondary-container}"
    typography: "{typography.cuerpo}"
    rounded: "{rounded.xl}"
    padding: 16px
  aviso-error:
    backgroundColor: "{colors.error-container}"
    textColor: "{colors.on-error-container}"
    typography: "{typography.cuerpo}"
    rounded: "{rounded.xl}"
    padding: 16px
  ayuda-campo:
    backgroundColor: "{colors.surface-variant}"
    textColor: "{colors.on-surface}"
    typography: "{typography.pista}"
    rounded: "{rounded.md}"
    padding: 12px
  lista-item:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.cuerpo}"
    rounded: "{rounded.xl}"
    padding: 16px
  paso:
    backgroundColor: "{colors.outline}"
    rounded: "{rounded.sm}"
    height: 8px
  paso-hecho:
    backgroundColor: "{colors.primary-container}"
    rounded: "{rounded.sm}"
    height: 8px
  dato:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.dato-grande}"
  pregunta-pantalla:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.pregunta}"
  borde-boton:
    backgroundColor: "{colors.primary-dark}"
    height: 3px
  borde-boton-secundario:
    backgroundColor: "{colors.primary}"
    height: 3px
  borde-boton-peligro:
    backgroundColor: "{colors.error-dark}"
    height: 3px
  borde-boton-letra:
    backgroundColor: "{colors.primary-overlay-border}"
    size: 2px
  borde-campo:
    backgroundColor: "{colors.outline}"
    height: 3px
  borde-aviso:
    backgroundColor: "{colors.tertiary}"
    size: 2px
  borde-aviso-error:
    backgroundColor: "{colors.error}"
    size: 2px
  borde-ayuda:
    backgroundColor: "{colors.primary-container}"
    size: 6px
  pista:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface-variant}"
    typography: "{typography.pista}"
---

# CUE Digital

> **Nota para quien lea esto, sea persona o agente.** Este documento es para quien
> construye la aplicación, no para el agricultor. Por eso aquí sí aparecen nombradas
> las palabras prohibidas, justamente para prohibirlas. La regla de "cero jerga" se
> aplica a lo que se ve en pantalla, y se comprueba con tests sobre `textos.py` y sobre
> los ficheros de `web/`, no sobre este fichero.

## Overview

**El cuaderno de campo que se lee al sol y se maneja con una mano.**

Esto no es una aplicación de gestión vista en una oficina. Es lo que un agricultor
abre de pie en mitad de una parcela, con el móvil en una mano, la otra ocupada, el sol
dando de lleno en la pantalla y probablemente sin cobertura. Todo lo que sigue sale de
esa escena concreta.

**A quién le habla.** A un agricultor de entre 50 y 70 años que lleva el cuaderno en
papel desde 2013 y no ha usado nunca un programa de gestión. Puede que no tenga
correo electrónico en el móvil. No es torpe: es que nadie le ha diseñado nada pensando
en él. Desde el 1 de enero de 2027 el registro de productos aplicados tiene que ser
electrónico, y si esto no se entiende, ese agricultor se queda fuera de la ley sin
querer.

**Qué tiene que sentir.** Tranquilidad y franqueza. Que el programa le habla como le
hablaría un vecino que sabe del tema: sin jerga, sin abreviaturas y sin dar por hecho
que sabe qué es un recinto SIGPAC. La sensación al terminar de apuntar algo tiene que
ser "ya está", no "a ver si lo habré hecho bien".

**Cómo se traduce eso en el aspecto visual.** Verde de campo, no verde de aplicación
corporativa: un verde oscuro de verdad, con blanco, y el amarillo reservado para
señalar. Superficies planas y limpias, con bordes gruesos que separan sin necesidad de
sombras. Nada de degradados, nada de desenfoques, nada de animaciones: en una pantalla
al sol no se ven, y en un móvil barato cuestan.

**La regla que manda sobre todas las demás.** Si hay que elegir entre que quepa más
información y que se entienda, gana que se entienda. Siempre. Una pantalla con tres
cosas claras vale más que una con quince apretadas.

## Colors

La paleta es corta a propósito: dos verdes, blanco, casi negro, y dos parejas de
colores de aviso que no se usan para nada más. Un color, un significado.

- **Primary (#1f4a2c):** el verde de la marca. Es el color de la cabecera, de lo que
  ya está elegido y del contorno de lo importante. Oscuro a propósito: sobre blanco da
  casi 10:1 de contraste, que es lo que permite leerlo al sol.
- **Primary container (#2f6b40):** el verde de los botones. Un paso más claro que el
  primary para que el blanco de encima siga leyéndose bien (6,2:1). Es el color que
  más superficie ocupa en la aplicación, porque los botones son lo que más se toca.
- **Primary dark (#0d2b18):** el borde de los botones. Existe para que un botón verde
  se distinga del fondo aunque la pantalla esté sucia o el brillo esté bajo. **Este
  sistema no separa con sombras; separa con bordes.**
- **On primary (#ffffff):** todo el texto que va encima de verde.
- **Primary overlay (#3a6446):** el fondo de los botones pequeños de la cabecera. Es un
  verde sólido, **no un blanco con transparencia**: las transparencias no están
  permitidas en este sistema, y al sol un blanco al 18 % sobre verde se ve sucio.
  **Primary overlay border (#8fae97):** el borde de esos mismos botones, un verde claro
  que se distingue del fondo sin competir con el texto.
- **Tertiary (#8a6a00):** el ámbar oscuro de los bordes de aviso. Es el único color
  que dice "mira esto" sin decir "esto está mal".
- **Secondary container (#ffe9a8):** el fondo de los avisos. Ámbar claro, que en una
  pantalla al sol se lee mejor que cualquier color saturado.
- **On secondary container (#3d2f00):** el texto de los avisos. Marrón muy oscuro, no
  negro: sobre ámbar, el negro puro cansa la vista.
- **Surface (#ffffff):** el fondo. Blanco de verdad, sin el gris azulado que se pone
  por costumbre y que al sol se ve sucio.
- **Surface variant (#f4f6f3):** el fondo de lo secundario: botones de "volver", la
  ayuda de cada campo.
- **On surface (#10190f):** el texto normal. Casi negro con una pizca de verde, para
  que no parezca impreso en una fotocopiadora.
- **On surface variant (#43503f):** el texto secundario: las pistas, el pie de página,
  el detalle de cada apunte. **Hay uno solo a propósito.** Llegó a haber tres grises
  casi iguales, y tres grises casi iguales son una inconsistencia esperando a que
  alguien copie el que no era.
- **Outline (#a9b6a8):** los bordes de lo que no está elegido. Gris verdoso, nunca
  negro: un borde negro compite con el texto.
- **Error (#8c1d18)**, **Error dark (#5c110d)** y **Error container (#fbe3e1)** con
  **On error container (#4a0f0b):** el rojo de "esto no se puede guardar", en su versión
  de fondo, de borde y de texto. **Solo se usa para eso.** Un rojo usado para decorar
  deja de significar peligro.
- **Focus (#ffd24a):** el amarillo del foco. Es lo único que marca "estás aquí", y
  funciona igual para quien ve bien y para quien no distingue colores, porque es un
  contorno grueso y no un cambio de tono.

## Typography

Una sola familia: la del propio móvil (`system-ui`). Es una decisión, no una
vagancia. Así no hay que descargar ninguna fuente —lo que importa con mala cobertura—,
el texto se ve exactamente como el agricultor está acostumbrado a ver su móvil, y el
sistema ya la tiene optimizada para su pantalla.

- **Cuerpo (18 px, peso 400):** el tamaño base. **Por debajo de 18 px, a partir de los
  50 años no se lee.** No es una recomendación de estilo: es el mínimo por debajo del
  cual esta aplicación no sirve para quien está hecha.
- **Cuerpo grande (21 px):** con el botón "A+" de la cabecera. Existe porque quien ve
  poco no siempre sabe que puede ampliar con los dedos, y porque ampliar con los dedos
  descoloca la pantalla.
- **Pregunta de pantalla (1,45 rem, peso 800):** la única pregunta de cada pantalla del
  asistente. Va en negrita fuerte para que se entienda de un vistazo qué se está
  pidiendo, sin leer nada más.
- **Título (1,5 rem, peso 700):** los títulos de pantalla.
- **Botón (1,1 rem, peso 700)** y **botón principal (1,35 rem, peso 700):** el texto de
  los botones. En negrita siempre: sobre verde y con prisa, la letra fina se pierde.
- **Campo (1,15 rem, peso 400):** lo que el agricultor escribe. Más grande que el
  cuerpo porque es lo que está mirando mientras teclea con el teclado del móvil.
- **Pista (0,95 rem, peso 400):** el texto de ayuda bajo cada campo. **Es el único
  texto por debajo del tamaño base, y nunca lleva información imprescindible**: si algo
  hay que leerlo sí o sí, va en cuerpo.
- **Dato grande (1,6 rem, peso 800):** las cifras que el agricultor viene a consultar
  —cuántos días faltan, cuántas hectáreas—. Un número que hay que buscar entre texto
  no se encuentra.

## Layout

**Una columna en el móvil, y de verdad que se aprovecha el ancho en el ordenador.** Eso
último se añadió el 30/09/2026, porque hasta entonces la aplicación era **una columna de
44 rem también en un ordenador** y aquello no era una aplicación de gestión: parecía un
móvil en medio de la pantalla.

### En el móvil (hasta 63,99 rem)

- **Ancho máximo 44 rem**, centrado. En una tablet o un ordenador la aplicación no se
  estira: una línea de texto de 60 caracteres se lee; una de 200, no.
- **Escala de espaciado:** 4, 8, 12, 16, 24 y 32 px. Se usa la de 16 px entre campos y
  la de 24 px entre bloques.
- **Márgenes de 12 px** a los lados en móvil, que es lo que deja el pulgar libre.
- **El botón principal mide 104 px de alto y ocupa todo el ancho.** Es el que más se
  toca de toda la aplicación; tiene que ser imposible fallarlo.
- **Ningún elemento tocable baja de 64 px de alto** (72 px con la letra grande). Un
  dedo con guante acierta 64 px. Por debajo de eso se toca el de al lado.
- **Los botones se separan entre sí al menos 8 px.** Si están pegados, tocar uno es
  tocar los dos.
- **La cabecera se queda fija arriba.** Es la única forma de volver al inicio sin
  buscar, y volver al inicio tiene que estar siempre a un toque.

### En el ordenador (desde 64 rem, unos 1024 px)

La misma aplicación, con el marco de un programa de gestión. **El móvil no se toca**: todo
esto vive dentro de su `@media`.

- **Menú lateral fijo de 17 rem** a la izquierda, en verde oscuro, con el nombre de la
  cuenta arriba y **todos los módulos** debajo, uno por renglón (Panel, Mi cuaderno, Mis
  tierras, Qué hay sembrado, El almacén, Los análisis, El plan de abono, Lo que he
  vendido, Los papeles, Mis facturas, Los años del cuaderno, La Junta, Mis datos, Ayuda).
- **El módulo en el que se está, marcado con tres cosas a la vez:** fondo distinto,
  barra amarilla a la izquierda y `aria-current="page"`. El color solo no informa.
- **Barra de arriba, fija, con lo que hay que saber siempre:** la campaña que se está
  llevando y la cuenta («Tu cuenta»). **No dice «Finca»**: en este programa la finca se
  identifica por el nombre del titular, y poner «Finca: David Pérez Velasco» sería decir
  una cosa que no es. Lleva además el botón **APUNTAR**, la letra grande y salir.
- **La pantalla ocupa todo el ancho** que sobra del menú, con 32 px de aire a los lados.
- **Los botones de la barra y de las filas de una tabla miden 2,9 rem** (unos 46 px): con
  ratón no hacen falta 64, pero el agricultor tiene entre 50 y 70 años y aquí no se baja
  de 40. **Los botones de las acciones principales siguen midiendo lo mismo que en el
  móvil.**
- **Las listas se ven en tabla** (tierras, cuaderno, años, facturas y almacén): cabecera por
  columna —y la cabecera es un botón cuando la columna se puede ordenar—, los números
  alineados a la derecha, las acciones en la última columna y **el total al pie**, que es la
  cuenta que se viene a hacer en esa lista. Los mismos datos, en el móvil, van en tarjetas:
  las dos formas están en el mismo HTML y las separa el CSS (`.solo-escritorio` y
  `.solo-movil`), nunca JavaScript.
- **La ficha de la fila elegida, en un panel al lado** (20 rem), sin salir de la página: se
  toca el **nombre** —que es un botón, porque un `<tr>` no se puede enfocar con el
  teclado— y al lado salen sus datos y sus botones. Volver a tocar el mismo nombre cierra el
  panel. La fila entera **no** es un botón.
- **Nada de sombras, degradados ni animaciones**, igual que en el móvil: cambia el
  ancho, no el lenguaje.

## Elevation & Depth

**Este sistema no usa sombras.** Ni una. Es la decisión menos habitual de este
documento y la más deliberada.

Una sombra sirve para separar dos planos, y para eso hace falta que se vea. Al sol, en
una pantalla de móvil con el brillo al máximo, una sombra del 10 % de negro es
literalmente invisible: el agricultor no ve el relieve, solo ve un borde sucio que
parece un defecto de la pantalla. Y en un móvil barato, cada sombra es trabajo de
dibujo en cada fotograma.

**En su lugar, la separación se hace con tres cosas, y las tres se ven siempre:**

1. **Bordes de 3 px** de un color que contrasta con el fondo.
2. **Cambios de color planos** entre superficies: blanco, verde, ámbar, rojo.
3. **Espacio en blanco** entre bloques.

El resultado es una interfaz que parece un formulario de papel bien impreso, y eso es
exactamente lo que es. La única excepción es el foco, que se marca con un contorno
amarillo de 4 px: no es una sombra, es una señal, y tiene que verse aunque el
agricultor esté mirando la pantalla de lado.

## Shapes

- **14 px (xl)** para todo lo que se toca: botones, campos, avisos, elementos de lista.
  Es redondeado de verdad, para que un dedo lo reconozca como algo que se pulsa, pero
  sin llegar a parecer un juguete. Esta aplicación tiene que dar confianza a alguien que
  se juega una sanción.
- **10 px (lg)** para los botones pequeños de la cabecera.
- **8 px (md)** para los bloques de ayuda, que no se tocan: si se tocan, se redondean
  como lo que se toca.
- **4 px (sm)** para las barras de progreso del asistente, que son indicadores y no
  botones.
- **No hay esquinas cuadradas.** Una esquina de 90 grados en una pantalla táctil no
  dice "púlsame"; una redondeada, sí.

## Components

Veintiocho piezas. Si algo no está aquí, no debería existir.

**Convención de los bordes.** El formato de este documento no tiene un sub-token para
el color del borde (solo admite `backgroundColor`, `textColor`, `typography`, `rounded`,
`padding`, `size`, `height` y `width`). Como este diseño **se separa con bordes y no con
sombras**, los bordes se declaran como componentes propios con el prefijo `borde-`: su
`backgroundColor` es el color de la línea y su `height` o `size` es el grosor. Así el
validador queda limpio y, de paso, el grosor viaja junto al color, que es más de lo que
daría un `borderColor`. **Todo lo que lleva borde tiene su `borde-` correspondiente.**

- **Botón (64 px):** verde medio, texto blanco en negrita, borde `borde-boton`, esquinas
  de 14 px. Con icono a la izquierda y, debajo del texto, una pista corta en cuerpo
  pequeño ("bichos, hierbas, hongos"). **El icono y la palabra van siempre juntos:**
  quien no lee bien reconoce el dibujo, y quien no conoce el dibujo lee la palabra.
- **Botón principal (104 px):** igual, más alto y con la letra más grande. **Solo hay
  uno en la pantalla**, y es "HE ECHADO PRODUCTO" o el botón que desbloquea al
  agricultor nuevo. Si hay dos en la misma pantalla, uno de los dos sobra.
  **Excepción documentada:** cuando al agricultor le falta lo imprescindible (no tiene
  ninguna parcela), la pantalla de inicio abre con un aviso y **un solo** botón
  principal, el que lo arregla, y el "HE ECHADO PRODUCTO" baja a normal. En ese momento
  el aviso manda, porque sin parcela los seis botones no llevan a ninguna parte.
- **Botón secundario:** fondo blanco, texto y borde verdes. Para los dos atajos que van
  debajo de los seis grandes: **"LO MISMO QUE LA ÚLTIMA VEZ"** y **"DÍMELO CON LA VOZ"**.
  Van en secundario para que no compitan con lo principal: son atajos, no caminos.
  **La pantalla de inicio tiene seis botones grandes y nada más**, y eso no se toca.
- **Botón claro:** fondo gris verdoso, texto verde y borde `borde-campo`. Para "VOLVER" y
  "DEJARLO", que son salidas y no acciones. Nunca para la acción principal.
- **Botón elegido:** verde oscuro con el contorno `foco`. Es el que ya se ha elegido en
  una lista. **Lleva el contorno además del color** para que se distinga sin depender de
  ver bien los colores.
- **Botón de peligro:** rojo. Solo para "DESHACER", que es la única acción que quita
  algo.
- **Botón de letra (48 px):** en la cabecera, para agrandar la letra y para salir. Es la
  única excepción a los 64 px, porque vive en la cabecera y no es una acción de campo.
- **Cabecera:** verde oscuro, texto blanco, fija arriba. Lleva el nombre de la
  aplicación y los dos botones de letra y salida. **Nada más**: la cabecera no es un
  menú.
- **Campo:** fondo blanco, borde `borde-campo`, letra de 1,15 rem, 64 px de alto. Al
  recibir el foco, contorno `foco` y borde verde. **Los campos de números piden el
  teclado numérico del móvil** (`inputmode="decimal"`): escribir una dosis con el
  teclado de letras es una tortura y una fuente de errores.
- **Aviso:** fondo ámbar, texto marrón oscuro, borde `borde-aviso`. Para lo informativo:
  "podrás coger la cosecha a partir del 22 de mayo".
- **Aviso de error:** fondo rojo claro, texto rojo oscuro, borde `borde-aviso-error`.
  **Solo aparece cuando algo no se ha podido guardar**, y siempre dice qué hacer ahora,
  no qué ha pasado.
- **Ayuda de campo:** fondo gris claro, borde izquierdo `borde-ayuda` de 6 px. Va debajo
  de cada campo y explica, en este orden: qué es, por qué te lo piden, un ejemplo y qué
  pasa si no lo pones.
- **Elemento de lista:** fondo blanco con borde `borde-campo`. Un apunte del cuaderno,
  con la fecha y el producto arriba y el detalle debajo.
- **Dibujo de la parcela:** la forma del trozo que trae el SIGPAC, en un `<svg>` de 96 px
  dentro del elemento de la lista. Fondo verde muy claro, contorno verde oscuro de 2 px y
  sin relleno llamativo: **es un reconocimiento, no un mapa.** No lleva ni calles ni
  nombres ni teselas, porque un mapa de verdad pesa megas y necesita cobertura, y lo único
  que hace falta aquí es que el agricultor reconozca su tierra de un vistazo. **Si la
  parcela no tiene forma** (se apuntó a mano), no se dibuja un cuadro: no se pone nada.
  Un cuadrado inventado sería peor que no dibujar, porque parecería la parcela.
- **Pasos del asistente:** barras de 8 px, grises las que faltan y verdes las hechas.
  Están para que el agricultor sepa que esto se acaba, que es la duda que más
  desanima en un formulario largo.
- **Dato:** la cifra que el agricultor viene a consultar, en 1,6 rem y negrita fuerte.
- **Pregunta de pantalla:** la única pregunta de cada pantalla del asistente.
- **Foco:** contorno amarillo de 4 px. No es una sombra: es una señal.

## Do's and Don'ts

### Texto

- **Sí:** escribe como le hablarías a un vecino. "¿Cuántas hectáreas has tratado?".
- **Sí:** usa siempre el mismo nombre para lo mismo. Si una parcela se llama "parcela"
  en una pantalla, se llama "parcela" en las cuarenta y una restantes.
- **Sí:** ante una duda, di qué hacer ahora. "Corrige la superficie" en vez de
  "superficie no válida".
- **No:** escribas "cuaderno de explotación", "recinto SIGPAC", "unidad homogénea de
  cultivo", "dosis", "postcosecha", "cumplimentar", "trazabilidad" ni ningún código de
  error. El vocabulario completo y las palabras prohibidas están en
  `backend/app/textos.py`, y hay un test que falla si se cuela alguna.
- **No:** escribas un texto para el agricultor en el HTML o en el JavaScript. **Todos
  los textos se piden a `/api/interfaz`.** Si los escribes a mano, el test que garantiza
  que no hay jerga deja de cubrirlos.
- **No:** uses abreviaturas. "ha" solo si va detrás de un número y ya se ha dicho
  "hectáreas" antes en la misma pantalla.

### Interacción

- **Sí:** una pregunta por pantalla. Un paso, un campo.
- **Sí:** ponle por defecto lo que ya sabes. La fecha de hoy, la superficie de la
  parcela, lo del último apunte. El agricultor corrige mucho mejor de lo que rellena.
- **Sí:** ofrece "LO MISMO QUE LA ÚLTIMA VEZ" en cuanto haya algo que repetir. El 80 %
  de los apuntes son el mismo producto con otra fecha.
- **Sí:** comprueba en el móvil lo que se pueda comprobar en el móvil, sin esperar al
  servidor. Con mala cobertura, esa espera es la diferencia entre corregirlo y
  abandonar.
- **Sí:** deja siempre un "DESHACER" a la vista después de guardar.
- **No:** bloquees un apunte por un campo opcional. Si falta un dato que no impide
  guardar, se guarda y se avisa: se llega a la inspección con el cuaderno a medias,
  que es mucho mejor que sin cuaderno.
- **No:** escondas un dato detrás de un "hover". En un móvil no hay ratón.
- **No:** pidas dos veces lo mismo. Si el programa ya sabe la parcela, el cultivo o la
  máquina, no se pregunta.
- **No:** cambies los botones de sitio entre versiones. Lo que funciona, no se mueve.

### Color y forma

- **Sí:** usa el color para reforzar, nunca para informar en solitario. Todo lo que el
  color dice, lo dice también una palabra o un icono.
- **Sí:** mantén el contraste por encima de 4,5:1. Al sol se pierde la mitad del
  contraste que mides en una oficina.
- **No:** añadas sombras, degradados, desenfoques ni transparencias.
- **No:** añadas animaciones. En un móvil barato cuestan, y al sol no se ven.
- **No:** uses el rojo para nada que no sea "esto no se ha podido guardar" ni el ámbar
  para nada que no sea "fíjate en esto".

### Sin cobertura

- **Sí:** guarda todo primero en el móvil, siempre, aunque haya cobertura.
- **Sí:** di cuántas cosas quedan pendientes de mandar, en cristiano y sin alarma.
- **No:** muestres un error por no tener cobertura. No tener cobertura en el campo no
  es un error, es lo normal.
- **No:** borres nunca un apunte porque haya fallado al mandarlo. Se aparta y se avisa;
  perder un dato del agricultor en silencio es lo único imperdonable.

### Antes de dar por bueno un cambio

- **Sí:** pasa `pytest` y `node --test "tests_js/*.test.js"`.
- **Sí:** comprueba que se sirve con el tipo correcto (`text/javascript` para los `.js`):
  un módulo servido como `text/plain` deja la pantalla en blanco sin decir por qué.
- **No:** des por bueno que es fácil porque tú lo entiendes. Eso se comprueba con
  agricultores de verdad, en el campo, y está en el apartado 5.18 del documento del MVP.
