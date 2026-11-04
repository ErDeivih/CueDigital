# CueDigital — sistema de diseño agrícola

El sistema visual de **CueDigital**, la herramienta digital del agricultor de Castilla y León. No se
construye a partir de la interfaz anterior: David la rechazó y se rehace desde aquí. Este fichero es
la fuente de la verdad para cualquier pantalla nueva.

## Qué manda

1. **El campo primero.** La pantalla se juzga de pie en una parcela, con sol de frente, el móvil en
   una mano y sin cobertura. Todo lo que se pulsa mide **48 px** como mínimo (`touch-target`), el
   texto de campo es **19/28** (`body-field`) y los formularios son cortos.
2. **Alto contraste, sin adornos.** Texto a 4,5:1 como mínimo, medido y anotado (abajo). Sin sombras,
   degradados ni transparencias: al sol no se ven y en un móvil barato cuestan.
3. **El color nunca informa solo.** Todo lo que dice el color lo dice también una palabra o un icono
   (y hay un token de estado para cada caso).
4. **Sin cobertura no se pierde nada.** Los apuntes se guardan en el móvil y se mandan solos; la
   interfaz dice «guardado en el móvil» solo si de verdad se ha guardado.
5. **Nada se inventa.** Un dato que no se sabe queda en blanco («no consta»), nunca un cero ni un
   valor parecido.

## Voz y textos

- Se tutea, en presente y en corto: **qué pasa + qué hago ahora**. «No se ha podido guardar. Prueba
  otra vez» es un mensaje; «Error de validación» no lo es.
- Sin jerga en pantalla. Las palabras prohibidas del proyecto están en `app/textos.py`
  (`PALABRAS_PROHIBIDAS`) y las vigilan tres tests.
- Las cifras en castellano: coma decimal, punto de miles, unidad siempre al lado (`ha`, `kg`, `L`).
- Una pregunta por pantalla en el campo; los datos opcionales se agrupan y se pueden dejar vacíos.
- Nada de relleno: ni «bienvenido a tu plataforma» ni frases que no aporten.

## Color

Dos temas, **Día** y **Noche**. Todo par de texto y fondo que se usa en pantalla está medido; los
números son la ratio de contraste WCAG calculada con la fórmula de luminancia relativa.

| Texto | Sobre | Ratio | AA |
|---|---|---|---|
| `ink` #12211A | `surface-card` #FFFFFF | 16,69:1 | ✅ |
| `ink` #12211A | `surface-page` #F3F0E8 | 14,66:1 | ✅ |
| `ink-muted` #4A5A51 | `surface-card` #FFFFFF | 7,31:1 | ✅ |
| `ink-muted` #4A5A51 | `surface-page` #F3F0E8 | 6,42:1 | ✅ |
| blanco #FFFFFF | `brand` #175C33 | 8,03:1 | ✅ |
| `brand-bright` #1E7A43 | `surface-card` #FFFFFF | 5,36:1 | ✅ |
| blanco #FFFFFF | `info` #1C4F7A | 8,58:1 | ✅ |
| blanco #FFFFFF | `success` #1E6B3A | 6,52:1 | ✅ |
| blanco #FFFFFF | `danger` #9E2B25 | 7,43:1 | ✅ |
| `warning` #7A4A00 | `warning-tint` #FDEBC8 | 6,37:1 | ✅ |
| `danger` #9E2B25 | `danger-tint` #F8DEDB | 5,83:1 | ✅ |
| `accent` #9A5B12 | `surface-card` #FFFFFF | 5,41:1 | ✅ |
| `border-strong` #6E6A5D | `surface-card` #FFFFFF | 5,41:1 | ✅ |
| `focus` #0B63CE | `surface-card` / `surface-page` | 5,69 / 5,00:1 | ✅ |
| `ink` #F1F3EE | `surface-card` noche #17211C | 14,79:1 | ✅ |
| `ink-muted` #B9C4BC | `surface-card` noche #17211C | 9,20:1 | ✅ |
| blanco #FFFFFF | `brand` noche #2E7D4F | 5,05:1 | ✅ |
| `brand-bright` noche #5CC98B | `surface-card` noche #17211C | 8,01:1 | ✅ |
| `warning` noche #E9B949 | `warning-tint` noche #3A2C17 | 7,41:1 | ✅ |
| `danger` noche #F08A82 | `danger-tint` noche #3A1E1C | 6,27:1 | ✅ |
| `border-strong` noche #6B7F74 | `surface-card` noche #17211C | 3,87:1 | ✅ |

Cómo se usa:

- **`brand`** es el verde de la casa: botón principal, pestaña activa, enlace. Sobre él, texto blanco.
- **`brand-tint`** marca selección y campaña; **`accent`/`accent-tint`** son tierra y cosecha, para
  cifras y para avisos que no bloquean.
- **`warning`** = falta algo o hay que revisar; **`danger`** = no se ha podido guardar o se va a
  anular algo. Los dos van siempre con palabra e icono.
- **Colores que hay que distinguir** (estado de una parcela, tipo de apunte) se separan también en
  **luminosidad**, no solo en tono, y llevan etiqueta escrita.
- Prohibido: nombrar colores en el código de una pantalla (`#...` suelto). Todo color sale de un
  token.

## Tipografía

Una sola familia: la del sistema (`system-ui`…), porque **la aplicación tiene que funcionar sin red**
y una fuente descargada es una pantalla en blanco sin cobertura. Escala corta:

| Estilo | Tamaño/interlínea | Peso | Para |
|---|---|---|---|
| `display` | 32/38 | 700 | Título de pantalla y cifra grande |
| `title` | 24/30 | 700 | Título de ficha y de panel |
| `heading` | 20/26 | 600 | Título de bloque |
| `body-field` | 19/28 | 400 | Texto y campos en el móvil, de pie en el campo |
| `body` | 17/26 | 400 | Texto en tableta y PC |
| `label` | 15/20 | 600 | Etiqueta de campo, columna de tabla, estado |
| `caption` | 13/18 | 400 | Fecha, unidad, ayuda secundaria |

El **mínimo** de texto de lectura es 17 px en PC y 19 px en campo; `caption` no se usa para nada que
haya que leer de pie.

## Espaciado y formas

- Escala: 4, 8, 12, 16, 24, 32, 48 px. Nada inventado por pantalla.
- Radios: 6 (etiquetas), 10 (botones y campos), 16 (fichas y hojas), píldora (filtros y estados).
- Rejilla: contenido a **1180 px** como máximo; a partir de ahí solo crecen los márgenes.
- Bordes de 1 px (`border-subtle` para separar, `border-strong` para el borde de un control).
- **Sin sombras ni degradados**: la jerarquía se hace con espacio, tamaño y borde.

## Iconografía

- Iconos de **trazo**, 24 px, grosor 2 px, esquinas redondeadas, dibujados en línea (`<svg>` con
  `stroke="currentColor"`, `fill="none"`). Nunca emoji en la interfaz.
- Todo icono que no sea decorativo lleva su `aria-label`; el decorativo, `aria-hidden="true"`.
- Un icono nunca sustituye a la palabra en una acción importante: va con su texto.

## Los cuatro estados de cada pantalla

| Estado | Qué se ve | Regla |
|---|---|---|
| **Vacío** | Qué falta y **el botón que lo arregla** | Nunca una pantalla en blanco ni un «no hay datos» seco |
| **Cargando** | Un texto que dice qué se está trayendo | Si tarda, se puede seguir; no se bloquea la pantalla entera |
| **Error** | Qué ha pasado + qué hago ahora | Siempre con salida: reintentar, seguir a mano o volver |
| **Sin permiso** | Quién puede hacerlo y dónde se pide | No se oculta la pantalla sin decir por qué |

## Accesibilidad y campo

- Foco visible con `focus` (anillo de 2 px) en todo lo que se puede pulsar; navegable con teclado.
- Etiqueta visible en todos los campos (`<label>`), no solo placeholder.
- Área táctil mínima **48×48**; separación entre dos acciones de 8 px como mínimo.
- Se respeta `prefers-reduced-motion`: sin animación por defecto.
- Los datos importantes se pueden leer a 200 % de zoom sin scroll horizontal.

## Lo que no se hace

- No se reutiliza el aspecto de la interfaz anterior (la rechazó David).
- No se usan sombras, degradados, transparencias ni animaciones decorativas.
- No se informa con color solo.
- No se escriben textos para el agricultor fuera de `app/textos.py`.
- No se tapan los estados vacío/error con un spinner.
