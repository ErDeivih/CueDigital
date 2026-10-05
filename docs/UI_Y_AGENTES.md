# Interfaz, agentes y salida estructurada

> **Aviso del 26/09/2026: la parte de React de este documento ya no manda.** David ha decidido que
> **la interfaz se rehace en React**, con estas palabras: «rehaz toda la ui con react aunque haya que
> rehacer pruebas». Lo que sigue escrito aquí sobre **por qué se descartó** se queda tal cual, porque
> los motivos siguen siendo ciertos y son los que hay que respetar al hacer el cambio (que la
> aplicación funcione **sin cobertura**, que los textos vivan en `textos.py` y que el contrato de
> diseño siga mandando). Las condiciones del cambio están en [`AGENTS.md`](../AGENTS.md), apartado 5.

Qué se ha hecho con las ideas que trajo David (el `design.md` para agentes, la
*Generative UI* que esconde el chat, y forzar la salida de modelos pequeños), qué se
ha descartado y por qué.

**Resumen en una frase:** de las tres ideas, **una está aplicada y verificada**
(`DESIGN.md` como contrato), **una encaja perfectamente y ya estaba medio hecha**
(la interfaz enseña lo que ha entendido en vez de hablar: es *Generative UI*), y **una
está preparada con el punto de enchufe marcado** (salida estructurada, con un extractor
por reglas que ya funciona hoy y sin contratar ningún modelo).

---

## 1. `DESIGN.md`: aplicado y verificado

### Qué es

`DESIGN.md` es un formato abierto para describir un sistema de diseño a **agentes de
código**. Junta dos capas:

- **Frontmatter YAML**: los tokens, que son los valores normativos (colores, tipografía,
  radios, espaciado, componentes).
- **Cuerpo en Markdown**: el porqué, en secciones fijas y en este orden: *Overview,
  Colors, Typography, Layout, Elevation & Depth, Shapes, Components, Do's and Don'ts*.

La idea de fondo: un agente que lee ese fichero genera una interfaz coherente con la
marca sin que nadie se lo explique otra vez. Los tokens dan los valores exactos; la
prosa explica **por qué** valen eso, que es lo que impide que un agente los "mejore".

- Especificación oficial: <https://github.com/google-labs-code/design.md>
- Generador (convierte una web en un `DESIGN.md`): <https://github.com/context-dot-dev/designmd-supply>
- Ejemplos reales: <https://styles.refero.design/ai-agents/design-md-examples>
- Prompts de maquetación: <https://vibeui.online/>

### Qué se ha hecho

1. **`DESIGN.md` en la raíz del proyecto**, escrito a mano siguiendo la especificación.
   Los valores no son inventados: salen de `backend/web/estilos.css`. Contiene 19
   colores, 9 escalas de tipografía, 4 radios, 6 medidas de espaciado y 25 componentes.

2. **Validado con el validador oficial**, que da **0 errores y 0 advertencias**:

   ```bash
   npx --yes -p "@google/design.md" designmd lint DESIGN.md
   ```

   En Windows hay que usar el alias `designmd` y no `design.md`: el sufijo `.md` choca
   con la asociación de ficheros Markdown del sistema. Está explicado en el README de la
   herramienta.

3. **Atado al código con 22 tests** (`backend/tests/test_design_md.py`), para que no se
   convierta en un documento decorativo. Lo que comprueban:

   | Test | Qué impide |
   |---|---|
   | Las ocho secciones en orden | Que alguien reordene o duplique secciones |
   | Referencias `{colors.x}` resueltas | Una referencia rota (el único *error* del validador) |
   | Contrato ⇄ CSS, en los dos sentidos | Que un color cambie en un lado y no en el otro |
   | Ningún color fuera de `:root` | Colores escritos a mano por las esquinas |
   | Contraste ≥ 4,5:1 en cada par fondo/texto | Que algo deje de leerse al sol |
   | 64 px y 18 px en los dos ficheros | Que alguien encoja un botón "para que quepa" |
   | Las reglas duras en "Do's and Don'ts" | Que se borren las reglas al refactorizar |

   El contraste se calcula aquí, en Python, y no llamando al validador: **un test que
   necesita Node, npm y conexión no es un test, es una lotería.**

### Lo que el ejercicio destapó en el código

Escribir el contrato obligó a mirar el CSS con otros ojos, y aparecieron cuatro cosas
reales que se han arreglado:

1. **`--verde-claro` estaba declarado y no se usaba en ningún sitio.** Código muerto.
2. **El amarillo del foco estaba escrito a mano en dos reglas distintas** (`#ffd24a` dos
   veces). Ahora es un token.
3. **La cabecera usaba `rgba(255,255,255,.18)`**, una transparencia... en un sistema
   cuyo propio "Do's and Don'ts" prohíbe las transparencias. Sustituido por un verde
   sólido (`#3a6446`), que además se lee mejor al sol.
4. **Había tres grises de texto casi iguales** (`#43503f`, `#3c4739`, `#55604f`),
   copiados sin criterio. Consolidados en uno. Tres grises casi iguales son una
   inconsistencia esperando a que alguien copie el que no era.

Después de eso, **los 19 colores viven en `:root` y en ningún otro sitio**, y hay un
test que lo comprueba.

### Una limitación del formato, y cómo se resolvió

El formato no tiene sub-token para el color del borde: solo admite `backgroundColor`,
`textColor`, `typography`, `rounded`, `padding`, `size`, `height` y `width`. Y **este
diseño se separa con bordes, no con sombras**, así que los bordes son la mitad del
sistema.

La salida fácil era borrar los bordes del contrato para callar al validador. Eso habría
dejado 9 advertencias a cambio de 4 tokens huérfanos y de perder justo la información
que un agente necesita. Se resolvió declarando los bordes como **componentes propios con
prefijo `borde-`**: su `backgroundColor` es el color de la línea y su `height` o `size`
es el grosor. El validador queda limpio **y** el grosor viaja junto al color, que es más
de lo que daría un `borderColor`.

### Cómo se usa a partir de ahora

- **Antes de tocar la interfaz**, pásale `DESIGN.md` al agente. Ese es el contrato.
- Si cambias un color, un tamaño o una regla: **cambia los dos lados**. Si no, el test
  se pone rojo, que es exactamente lo que tiene que pasar.
- Antes de dar por bueno un cambio de diseño, `pytest` y `node --test "tests_js/*.test.js"`.

---

## 2. *Generative UI*: ya era el diseño, ahora tiene nombre

La idea: no enseñar un chat, sino hacer que la IA devuelva **componentes visuales**. En
vez de que el modelo explique lo que ha entendido en un párrafo, que devuelva la pantalla
ya montada.

**Esto ya estaba en el diseño de CUE Digital, y por el mismo motivo.** El apartado 5.8
del documento del MVP dice, desde antes de esta conversación:

> *"Siempre muestra lo que ha entendido y pide confirmación. Nunca guarda a ciegas."*

Y el endpoint que se ha construido en esta ronda lo cumple literalmente: no devuelve
una frase, devuelve una **tarjeta con el formulario a medio rellenar**, cada dato con la
pregunta que le corresponde, las palabras que lo delataron y la lista de lo que falta.
La interfaz no compone ni una frase: todo el texto viene escrito del servidor.

```
POST /api/borradores/desde-texto
   { "texto": "hoy he echado ejemplo 25 en el prado, dos litros por hectarea, habia pulgon" }

   {
     "tipo": "tratamiento",
     "datos": { "parcela_id": 1, "producto_id": 7, "fecha": "2026-09-21",
                "dosis": 2, "plaga": "Pulgon", "justificacion": "Vi la plaga..." },
     "entendido": [
       { "pregunta": "¿Dónde?", "valor": "El Prado", "campo": "parcela_id",
         "bruto": "prado" }
     ],
     "falta": [],
     "titulo": "Lo que he entendido",
     "intro": "Mira si está bien. Completa lo que falte y apúntalo."
   }
```

### Lo que se descarta, y por qué

| Herramienta | Veredicto | Motivo |
|---|---|---|
| **Vercel AI SDK** | **No** | Es para React y Next.js. Esta interfaz **no se compila a propósito**: son ficheros sueltos que sirve el propio programa, porque el servidor donde se instale no tiene por qué tener Node y porque en un móvil con mala cobertura una página ligera se abre. Meter un framework de React aquí sería cambiar un requisito real (que funcione en el campo) por una moda. |
| **Lobe Chat** | **No** | Es una interfaz de chat, y esconder el chat es justo lo que se busca. Enseñarle a un agricultor de 65 años una caja de texto donde "hablar con la IA" es la forma más rápida de que no la use. |
| **Dify** | **Todavía no** | Es un orquestador para flujos con varios agentes y herramientas. Aquí hay **cero agentes**: hay un extractor. Añadir Dify sería añadir un servicio que mantener para no hacer nada. Tendría sentido si algún día entra "lee mi cuaderno de papel en fotos y cárgamelo", que sí es un flujo largo con pasos. |

**Lo que sí se queda de esta idea**, y es lo importante: la regla de que **la salida de
la IA es una pantalla, no un texto**. Un texto se lee y se cree; una pantalla con los
campos rellenos se revisa y se corrige.

---

## 3. Salida estructurada: el punto de enchufe está puesto

Para que un modelo pequeño no alucine ni rompa la interfaz, hay que **forzarle la
estructura**. De las herramientas que trajo David:

| Herramienta | Para qué serviría aquí |
|---|---|
| **Outlines** | Forzar que el modelo emita exactamente el JSON de `BorradorSalida`. Es la que mejor encaja: impide que conteste "Aquí tienes tu JSON:" o que se invente un campo. |
| **Guidance** | Intercalar reglas: por ejemplo, que el producto solo pueda ser uno de los que ya tiene la explotación. |
| **DSPy** | Optimizar los prompts automáticamente. Útil solo si algún día hay muchos ejemplos de dictados reales que ajustar. |
| **Semantic Kernel** | Estandarizar "habilidades" del agente. Sobredimensionado aquí. |

### La decisión de arquitectura

**El esquema es el contrato, y ya existe.** `backend/app/schemas.py` define
`BorradorSalida`. Cualquier modelo tendría que devolver exactamente eso:

```python
class BorradorSalida(BaseModel):
    tipo: str
    datos: dict               # solo los campos que se han entendido
    entendido: list[EntendidoSalida]
    falta: list[FaltaSalida]
    fuente: str               # "reglas" hoy, "modelo" cuando se enchufe
```

`datos` es un diccionario **libre** a propósito, y no un `TratamientoEntrada`. El motivo
importa: un borrador está **incompleto por definición**. Obligarle a tener la forma
completa animaría a rellenar los huecos con inventos, que es justo lo que no puede pasar
en un cuaderno de campo.

### Y lo más importante: hoy funciona SIN modelo

No se ha dejado la función esperando a un modelo. `backend/app/borradores.py` entiende
hoy, con reglas y con los catálogos de la propia explotación:

- **Fechas dichas de mil maneras**: "hoy", "ayer", "anteayer", "el 3 de mayo", "03/05",
  "03/05/2025". Con una decisión documentada: si la fecha cae más de seis meses en el
  futuro, se entiende del año pasado — es lo que pasa cuando en enero alguien dice "lo
  eché en diciembre".
- **Números en cifra y en palabra**: "2 litros" y "dos litros" y "medio litro" y
  "una tonelada" (que se convierte a 1.000 kg).
- **Sus parcelas, productos y abonos**, por nombre y con tolerancia: reconoce "ejemplo
  25" aunque el producto se llame "Ejemplo 25 EC", y "nitrato amonico" aunque el abono
  sea "Nitrato amónico 33,5%". Exige que aparezcan **todas** las palabras significativas
  del nombre, para que "Total" no salte cada vez que alguien dice "en total".
- **La intención**: tratamiento, abono, cosecha, siembra, riego, poda.
- **El motivo**: "aviso de la Junta", "me lo dijo mi técnico", "había pulgón".

**Sin conexión a ningún modelo, sin claves y sin coste.** El modelo, cuando entre, será
una mejora para las frases raras, no un requisito para las normales.

### Las tres reglas que un modelo NO va a poder saltarse

1. **Un dato que no se sabe se queda en blanco, y se pregunta.** Nunca se rellena "algo
   parecido". Un número de etiqueta inventado es una sanción; un hueco es una pregunta.
2. **Nada se guarda sin que el agricultor lo confirme.** El endpoint no escribe en el
   cuaderno: devuelve un borrador. Hay un test que lo comprueba.
3. **Solo se le pasan los catálogos de su finca.** El borrador no puede proponer la
   parcela ni el producto de otro agricultor. También hay un test.

### La trampa que se ha documentado en el código

"Dos litros" puede ser la **dosis por hectárea** o el **total empleado**, y confundirlos
es un error de diez veces en el dato que la ley mira para decidir si una aplicación fue
legal. Así que **no se adivina**:

- si dice "por hectárea" → es la dosis;
- si además ha dicho la superficie → se reparte y se enseña la cuenta;
- si no → se apunta lo que se ha oído **sin colocarlo** (`campo: null`) y se le pregunta.

El test más importante de `test_borradores.py` es precisamente ese.

---

## 4. Qué haría yo después, por orden

| # | Qué | Por qué en este orden |
|---|---|---|
| 1 | **Prueba con tres agricultores reales** (§5.18 del MVP) | Ninguna de estas ideas sustituye a comprobar que se entiende en el campo. Y podría invalidar decisiones de diseño que ahora parecen obvias. |
| 2 | **Poner el dictado en la interfaz** | El backend está hecho y probado. Falta el botón 🎤 y la pantalla de revisión, que ya está especificada en la respuesta del endpoint. |
| 3 | **Confirmar vigencia y límites de zonas vulnerables** | Los 387 municipios ya se derivan del Excel oficial de IDECyL; ante datos incompletos o dudas de delimitación se pregunta. |
| 4 | **Comprobar el caso concreto de nitrógeno** | Los anexos III y V están cargados para consulta; queda interpretar sus excepciones, el cultivo y la zona vulnerable antes de automatizar avisos. |
| 5 | **Foto de la etiqueta** | Mismo patrón que el dictado: una imagen entra, un `BorradorSalida` sale. Aquí sí haría falta un modelo de visión, y es donde Outlines tiene sentido. |
| 6 | **Dictado con modelo**, si los datos dicen que hace falta | Solo cuando haya dictados reales que fallen. Se enchufa detrás de `redacta_borrador` sin cambiar la firma ni el esquema. |
| 7 | **Dify**, si algún día hay un flujo de verdad | "Cárgame el cuaderno de papel a partir de fotos" es un flujo largo con pasos. Entonces sí. |

---

## 5. Resumen de las herramientas

| Idea | Estado | Dónde está |
|---|---|---|
| `DESIGN.md` como contrato para agentes | **Aplicado y verificado** | `DESIGN.md`, `backend/tests/test_design_md.py` |
| Validador oficial de `DESIGN.md` | **Pasado, 0 errores y 0 avisos** | Comando en el `README.md` |
| *Generative UI*: la IA devuelve pantallas, no texto | **Aplicado** | `/api/borradores/desde-texto`, campos `entendido` y `falta` |
| Ocultar el aspecto de chat | **Ya era el diseño** | Modo Sencillo de seis botones, sección 5.5 del MVP |
| Salida estructurada (contrato de esquema) | **Preparado y en uso** | `BorradorSalida` en `schemas.py` |
| Extractor que funciona sin modelo | **Hecho y probado** | `backend/app/borradores.py`, 68 tests |
| Punto de enchufe del modelo | **Marcado y documentado** | `redacta_borrador`, campo `fuente` |
| Vercel AI SDK / Lobe Chat | **Descartado** | Motivos arriba |
| Dify | **Aplazado** | Motivos arriba |
| Outlines / Guidance / DSPy / Semantic Kernel | **Documentado, sin instalar** | Hacen falta solo cuando entre el modelo |

**Ninguna de estas herramientas está instalada.** No se ha añadido ni una dependencia
por esta vía: lo único que se ha instalado es `pyyaml`, y solo para que los tests puedan
leer el `DESIGN.md`.
