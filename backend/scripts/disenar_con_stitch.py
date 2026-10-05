"""Diseñar las pantallas con Stitch (la herramienta de diseño con IA de Google).

## Qué hace

Habla con el servidor MCP de Stitch (`https://stitch.googleapis.com/mcp`) y le pide **las pantallas de
esta aplicación**: primero le sube nuestro `DESIGN.md` (el contrato de diseño del proyecto: colores,
tipos, medidas) para que diseñe **dentro de nuestras reglas** y no con las suyas, y después le pide cada
pantalla con un texto que describe qué tiene que hacer el agricultor en ella.

Las respuestas crudas se guardan en `docs/stitch/`, y las capturas del rediseño en
`docs/stitch/rediseno/`, para poder mirarlas después y para que el trabajo de diseño quede documentado
(qué se pidió, qué se obtuvo y cuándo).

## Cómo se usa

```bash
cd backend
$env:STITCH_API_KEY="<tu clave>"      # NUNCA se escribe en un fichero del repositorio
../.venv/Scripts/python.exe scripts/disenar_con_stitch.py --listar
../.venv/Scripts/python.exe scripts/disenar_con_stitch.py --proyecto NUEVO
../.venv/Scripts/python.exe scripts/disenar_con_stitch.py --sistema ID_DEL_PROYECTO
../.venv/Scripts/python.exe scripts/disenar_con_stitch.py --todas ID_DEL_PROYECTO
```

## Cuatro cosas que se aprendieron llamando de verdad (ronda 76)

1. **El `projectId` va SIN el prefijo `projects/`.** Con el nombre completo, Stitch contesta
   `Request contains an invalid argument`, que no dice nada de dónde está el fallo.
2. **Después de subir el `DESIGN.md` hay que crear el sistema de diseño** con
   `create_design_system_from_design_md` (es el segundo paso y no se hace solo). Lo que devuelve
   `upload_design_md` es la **instancia de pantalla** con la que se crea.
3. **Cada pantalla se pide con `designSystem`**: si no se pasa, Stitch usa un sistema suyo y las
   pantallas salen **con otro estilo**. El id del sistema es `assets/…`.
4. **Tarda minutos y no se reintenta.** Si la llamada se corta, lo que hay que hacer es preguntar por la
   pantalla con `get_screen` (cada 30 s, hasta 10 veces), no volver a pedirla: se duplicaría.

## Lo que hay que saber de la clave

- La cabecera que funciona es **`X-Goog-Api-Key`** (con `Authorization: Bearer` contesta 401: «esperaba
  un token de OAuth»). Eso se descubrió probando, y queda aquí escrito para no volver a tropezar.
- **La clave no entra en el repositorio**: se pasa por variable de entorno. Es la misma regla que con
  la clave del certificado.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import sys

import httpx

URL = "https://stitch.googleapis.com/mcp"
RAIZ = pathlib.Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "docs" / "stitch"
DISENO = RAIZ / "DESIGN.md"

# El sistema de diseño del proyecto de CueDigital, creado a partir de nuestro `DESIGN.md` con
# `create_design_system_from_design_md`. Se pasa en **cada** pantalla: si no, Stitch usa el suyo y las
# pantallas salen con otro estilo.
SISTEMA_DE_DISENO = "assets/87c81708ca75482bb84bcecc667cd7d9"

# Lo que se le pide a Stitch de cada pantalla. El texto va en castellano porque es como habla el
# agricultor, y cada uno lleva lo que la pantalla tiene que resolver, no cómo tiene que ser: el cómo lo
# decide el diseño. Los textos de los botones son los de verdad (`backend/app/textos.py`): no se inventan
# frases para el agricultor.
COMUN = (
    "Aplicación web para móvil, para un agricultor de 50 a 70 años de Castilla y León. Se usa DE PIE EN "
    "EL CAMPO, con una mano, con sol y a veces sin cobertura. El usuario no sabe de informática: tiene "
    "que entender la pantalla sin que nadie se la explique. Reglas: letra de 18 px o más; botones de "
    "64 px de alto o más; nada de menús escondidos ni de pestañas; un solo color de acción; sin sombras, "
    "sin degradados, sin animaciones; **iconos dibujados (SVG) y no emoji**; todo lo que se pide se "
    "explica al lado con una frase. "
)

PANTALLAS = {
    "inicio": (
        COMUN
        + " Es la pantalla que abre el agricultor todos los días. Arriba, el saludo: «Hola · 2026». "
        "Debajo, la pregunta, en grande: «¿Qué has hecho hoy?». Después, SEIS acciones, y aquí está lo "
        "importante: **«HE ECHO PRODUCTO» tiene que verse claramente como la acción principal** (la que "
        "más se usa), y las otras cinco como secundarias: «HE ABONADO» (abono para la tierra), «HE HECHO "
        "UN TRABAJO» (sembrar, regar, coger), «MI CUADERNO» (ver lo que tengo apuntado), «SACAR EN PAPEL» "
        "(para imprimir), «NO SÉ QUÉ PULSAR» (te lo explico). Cada una con su pista de una línea debajo. "
        "Más abajo y separadas, dos atajos: «LO MISMO QUE LA ÚLTIMA VEZ» y «Dímelo con la voz» "
        "(cuéntamelo con tus palabras), y al final «MIS PARCELAS, PRODUCTOS Y MÁQUINAS». Abajo del todo, "
        "una frase pequeña: «Si algo no lo entiendes, déjalo en blanco y pregunta». Quiero que se vea de "
        "un vistazo qué es lo principal y qué lo secundario, sin que nada parezca un formulario. NO "
        "pongas barra de pestañas abajo ni menús: todo lo que hace falta está en esta pantalla."
    ),
    "asistente": (
        COMUN
        + " Es UN PASO del asistente para apuntar que se ha echado un producto. Arriba, una barra de "
        "progreso y la pregunta en grande: «¿Dónde lo has echado?». Debajo, la explicación pequeña: «Casi "
        "siempre es en una parcela. Elige lo que corresponda». Después, la lista de tierras como tarjetas "
        "grandes donde se toca: cada una con su nombre puesto por el agricultor («El Prado»), su "
        "superficie («4,90 ha»), su pueblo, el dibujo de la forma de la parcela y, si la tiene, su "
        "declaración de pastos o barbecho. Al final de la lista, una tarjeta aparte y más clara: «¿No es "
        "en una parcela?» (para naves, almacenes y producto ya recogido). Abajo del todo, un botón claro "
        "para dejarlo y otro para seguir. Lo que se toca tiene que verse que se toca (no es un "
        "formulario: se elige con el dedo). NO pongas barra de pestañas abajo ni menús."
    ),
    "mi_cuaderno": (
        COMUN
        + " Es «Mi cuaderno»: el resumen del año del agricultor. Arriba, cuántos apuntes tiene: «3 "
        "apuntes de producto», con la lista de los apuntes (fecha, producto, en qué tierra y cuántas "
        "hectáreas). Después, un bloque que dice «Lo que falta por completar» con lo que le queda por "
        "apuntar y, en cada línea, un botón para arreglarlo («A El Prado le falta decir qué cultivo tiene "
        "este año» + botón «QUÉ HAY SEMBRADO»). Más abajo, bloques del mismo estilo: «Lo que he vendido», "
        "«Lo que hago sin echar producto», «Los análisis», «El plan de abono del año», «Firmar el "
        "cuaderno», y uno destacado: «Sacar mi cuaderno para la Junta» con un botón grande. Al final, "
        "tres botones: «SACAR EN PAPEL», «GUARDAR LOS DATOS EN UN FICHERO» y «VOLVER». Es una pantalla "
        "LARGA de leer: quiero que se distingan bien los bloques unos de otros y que cada bloque se vea "
        "cerrado. NO pongas barra de pestañas abajo ni menús."
    ),
    "mis_tierras": (
        COMUN
        + " Es la lista de las tierras del agricultor («Mis parcelas, productos y máquinas»). Arriba el "
        "título y el botón «AÑADIR». Cada tierra es una tarjeta con: su nombre puesto por él («El "
        "Prado»), la referencia del SIGPAC (37-70-0-0-503-51-1), sus hectáreas («4,90 ha»), su pueblo, el "
        "dibujo sencillo de la forma del trozo, y una línea con lo que tiene sembrado este año. Si a una "
        "tierra le falta decir qué tiene sembrado, se dice con un aviso claro y su botón («LE FALTA DECIR "
        "QUÉ TIENE SEMBRADO» + «DECIR QUÉ HAY SEMBRADO»). Las tierras son muchas (más de cincuenta): la "
        "tarjeta tiene que dejar claro de un vistazo cuál es cuál. NO pongas barra de pestañas abajo ni "
        "menús."
    ),
    # --- Ronda 90: las veinticuatro pantallas que no tenían diseño propio ---------------------------
    #
    # Las cuatro de arriba son las del rediseño de la ronda 76. De estas, **ninguna tenía diseño**: se
    # habían ido mejorando con las ideas que Stitch dio para aquellas cuatro (iconos dibujados, la tarjeta
    # de una tierra, cada dato con su nombre…), pero a cada una no se le había pedido el suyo. El encargo
    # de cada una cita los textos de verdad de `textos.py` y las reglas del campo.
    "mis_datos": (
        COMUN
        + " Es «Mis datos», la primera hoja del cuaderno: quién eres y cómo se llama tu finca. Once "
        "renglones que se rellenan en el mismo orden en que se leen en el papel, de arriba abajo, y un "
        "solo botón al final: «GUARDAR MIS DATOS». Cada renglón lleva su pregunta en grande encima y, "
        "debajo, una frase pequeña que dice qué poner: «¿Cómo te llamas?» con «Como viene en el cuaderno "
        "de la Junta», «Tu NIF» con «Con la letra. Es lo que se compara con tu certificado al entrar», "
        "«Un teléfono» con «Por si hay que avisarte de algo del cuaderno» y «Tu correo». Cuando una "
        "respuesta no hace falta, se dice ahí mismo: «Nº de registro nacional (si lo tienes)» con «Si no "
        "lo sabes, déjalo en blanco». Lo que ya está guardado tiene que verse escrito en su renglón al "
        "abrir la pantalla, sin que el agricultor tenga que acordarse de nada. Al guardar, un aviso "
        "claro y en su sitio: «Tus datos están guardados. La portada del cuaderno ya los lleva.». Debajo "
        "de todo, y separado de los renglones, el botón «Quién entra en mi finca» y «VOLVER». Que se "
        "vea que esto se rellena una vez y vale para siempre: no es algo que haya que mandar cada día. "
        "NO pongas barra de pestañas abajo ni menús."
    ),
    "quien_entra": (
        COMUN
        + " Es «Quién entra en mi finca»: la lista de las cuentas que apuntan en el mismo cuaderno, y en "
        "qué finca está trabajando cada una. Arriba se lee «Estás en» con el nombre de la finca, y en "
        "cada persona de la lista su nombre en grande, su correo debajo y su papel: «Tú (titular)» o "
        "«Ayuda en la finca». El papel de cada uno tiene que leerse de un vistazo, porque es lo que dice "
        "quién manda aquí. Si el agricultor es el titular se le dice «Eres el titular de esta finca: "
        "puedes añadir y quitar cuentas.»; si no lo es, «En esta finca decide el titular quién entra. Si "
        "quieres que entre otra persona, pídeselo al titular.». Cuando no hay nadie más, se dice: «De "
        "momento solo entras tú.». Para añadir a alguien, un renglón con «¿Con qué correo entra?», su "
        "explicación «El correo con el que se dio de alta esa persona», la frase «La otra persona tiene "
        "que tener ya su cuenta hecha con ese correo: tú no puedes ponerle la clave.» y el botón «AÑADIR "
        "UNA CUENTA». A cada persona se le puede quitar el acceso con «QUITARLE EL ACCESO», y eso tiene "
        "que verse como lo que menos se toca de la pantalla. Lo que se acaba de hacer se dice con un "
        "aviso claro: «Ya puede entrar en tu finca.» o «Ya no entra en tu finca.». Solo cuando la cuenta "
        "entra en más de una finca sale al final el bloque «En qué finca estás trabajando», con el botón "
        "«PONME EN ESTA FINCA» en las demás y sin botón en la que ya está. Al final del todo, «VOLVER». "
        "NO pongas barra de pestañas abajo ni menús."
    ),
    "medidas": (
        COMUN
        + " Es «Lo que hago sin echar producto»: las diez cosas que el agricultor hace para no tener que "
        "tratar, que se apuntan una vez al año. Se lee entero de un vistazo: diez casillas grandes, una "
        "debajo de otra, cada una con su pregunta en grande («¿Cambias de cultivo de un año a otro?», "
        "«¿Limpias la máquina al pasar de una parcela a otra?», «¿Quitas los restos del cultivo "
        "anterior?», «¿Apuntas lo que pasa cada año para aprender?»). El agricultor tiene que distinguir "
        "al momento lo que ya está marcado de lo que no: lo marcado se ve lleno y con su señal de visto, "
        "y lo que no, vacío, y nunca solo por el color. Debajo del título va la explicación en una frase "
        "corta: «Antes de echar producto, la ley pide haber probado otras cosas. Marca las que hagas en "
        "tu finca: se apuntan una vez y valen para todo el año.». Encima de las casillas, el rótulo "
        "«Marca lo que hagas en tu finca» con «Toca las que hagas. Si te equivocas, vuelve a tocarla y "
        "se desmarca.», porque aquí no se escribe: se toca. Solo la casilla marcada abre su renglón de "
        "nota, con «Lo que quieras añadir» y dentro la pista «Tus palabras». Al final, un aviso pequeño "
        "que cuenta que estas diez preguntas son las que pide la ley y que lo que se imprime es el "
        "nombre de cada una, no un número. Abajo, tres botones separados: «GUARDAR», «No hago ninguna de "
        "estas cosas» y «VOLVER». El de «No hago ninguna de estas cosas» no puede parecer el de guardar: "
        "es otra cosa y tiene que verse distinto. NO pongas barra de pestañas abajo ni menús."
    ),
    "ventas": (
        COMUN
        + " Es «Lo que he vendido»: las ventas de la cosecha, una detrás de otra, para poder responder "
        "de dónde salió cada partida. Arriba, el título y «Aquí se apunta lo que sale de la finca: a "
        "quién, cuánto y de qué parcelas salió. Es lo que cierra el cuaderno por arriba.». Cada venta es "
        "una ficha con la fecha y el producto arriba, en grande, que es lo que se busca de un vistazo. "
        "Debajo, cada dato en su propia fila y con su nombre delante, nunca una línea corrida de números "
        "y palabras que haya que adivinar: «Cuánto», «Cómo lo vendiste», «A quién», «Partida», "
        "«Albarán» y «De dónde». Con muchas ventas, la lista tiene que dejar claro dónde empieza y dónde "
        "acaba cada una. Si todavía no hay ninguna: «Todavía no has apuntado ninguna venta este año.». "
        "Antes de los botones, en letra pequeña, se dice que aquí no se apunta el precio ni lo que te "
        "han pagado: «Lo que pide la ley de esta sección es qué, cuánto y cuándo; las cuentas van "
        "aparte.». Abajo, «APUNTAR UNA VENTA» como botón principal bien grande y «VOLVER» como "
        "secundario. Nada de sumas ni de gráficos: sumar es cosa de otro sitio, aquí se apunta y se "
        "mira. NO pongas barra de pestañas abajo ni menús."
    ),
    "grupos": (
        COMUN
        + " Es «Parcelas que se llevan igual»: las tierras que se labran igual, juntadas en grupos, para "
        "apuntar de una vez un tratamiento para las seis en vez de seis apuntes. Arriba, el título y "
        "«Cuando varias parcelas tienen lo mismo y se labran igual, se pueden apuntar de una vez: un "
        "tratamiento para las seis, en vez de seis apuntes.». Cada grupo es una tarjeta con su nombre en "
        "grande, debajo cuántas parcelas son y cuántas hectáreas suman con su cultivo, y después la "
        "lista de los nombres de esas tierras, uno detrás de otro. Si el grupo lo juntó el programa y no "
        "el agricultor, se dice con una frase pequeña: «Lo juntó el programa.». Si todavía no hay "
        "ninguno: «Todavía no has juntado ninguna parcela. Al apuntar un tratamiento, después de la "
        "lista de parcelas te saldrán los grupos que tengas.». Cuando hay tierras de las que no se sabe "
        "qué tienen sembrado, el aviso va arriba y bien visible: «Para juntarlas hace falta saber qué "
        "hay sembrado en cada una. Hay parcelas sin decirlo.», con el botón «Qué hay sembrado» justo "
        "debajo para arreglarlo. Ese aviso es lo más importante de la pantalla cuando sale, porque sin "
        "eso no se pueden juntar. Antes de los botones, un bloque aparte explica para qué sirve: «El "
        "cuaderno sigue diciendo qué se hizo en cada parcela, porque el grupo las lleva dentro. Lo que "
        "se ahorra es escribirlo seis veces.». Abajo, «JUNTARLAS TÚ SOLO» como botón principal, y «Mis "
        "parcelas, productos y máquinas» y «VOLVER» como secundarios. NO pongas barra de pestañas abajo "
        "ni menús."
    ),
    "entrar": (
        COMUN
        + " Es la puerta de la aplicación: la primera pantalla que ve el agricultor, y en ella solo hay "
        "que resolver una cosa: si ya tiene cuaderno o si es la primera vez. Arriba, el título «Mi "
        "cuaderno» y una frase que explica para qué le sirve tenerlo aquí: «Puedes llevarlo en papel "
        "hasta el 31 de diciembre de 2026. A partir del 1 de enero de 2027 tiene que ser electrónico. Si "
        "lo llevas aquí, no se te pierde, te calcula solo los días de espera y te avisa de lo que "
        "falta». Los dos caminos tienen que verse como DOS caminos y no como un formulario largo: el de "
        "quien ya tiene cuenta, con «Tu correo», «Tu clave» y el botón «ENTRAR»; y el de quien llega "
        "nuevo, con «¿Cómo te llamas?», «Tu NIF», «¿En qué pueblo está tu finca?», «¿En qué provincia?», "
        "«Tu correo», «Tu clave» y el botón «CREAR MI CUADERNO». La provincia se elige de una lista: no "
        "se escribe. Abajo del todo, un botón claro para pasar al otro camino («Es mi primera vez» "
        "cuando está en el de entrar, «Ya tengo cuenta» cuando está en el de crear), y al pulsarlo los "
        "campos cambian: nada de campos escondidos ni de pestañas. Debajo de la clave, y solo si esta "
        "instalación lo tiene puesto, un botón aparte y más claro: «ENTRAR CON MI CERTIFICADO» con su "
        "pista «Sin teclear nada: usa el certificado que ya tienes», que nunca puede tapar el de correo y "
        "clave (si el certificado falla, tiene que poder entrar igual). Junto al NIF, una ayuda pequeña "
        "que diga qué es y dónde se mira, porque es el único dato que no viene en un papel que él tenga a "
        "mano. Lo que se pide se explica al lado con una frase, y nada que parezca un trámite. NO pongas "
        "barra de pestañas abajo ni menús."
    ),
    "mapa": (
        COMUN
        + " Es la pantalla con la que el agricultor apunta una tierra sin teclear ningún número: mueve "
        "el mapa con el dedo hasta poner su tierra en la cruz del centro y pulsa «ESTA ES MI TIERRA». "
        "Arriba, «Buscar mi tierra en el mapa» y la frase que enseña a usarla: «Mueve el mapa con el dedo "
        "hasta poner tu tierra en la cruz del centro, y pulsa ESTA ES MI TIERRA. También puedes tocar "
        "directamente tu trozo». El mapa tiene que ser lo más grande de la pantalla y **la cruz del "
        "centro tiene que verse siempre**, también con sol; debajo, tres botones iguales de altos: "
        "«ACERCAR», «ALEJAR» y «ESTOY AQUÍ», y luego el botón principal «ESTA ES MI TIERRA», que es el "
        "único con el color de acción. Cuando el SIGPAC contesta, aparece un bloque con el título «Esta "
        "es la parcela que hay ahí», la pregunta «¿Es tuya esta tierra?» y los datos **cada uno con su "
        "nombre al lado**: «La referencia de tu trozo», «Superficie», «Qué es», «Pueblo», «Referencia "
        "catastral» y «Zona de nitratos», que contesta «Sí: tu tierra está en zona de nitratos», «No está "
        "en zona de nitratos», «Solo una parte: el 40 % de tu tierra está en zona de nitratos» o «No se "
        "ha podido comprobar si está en zona de nitratos. Puedes apuntarla igual y mirarlo más tarde». "
        "Dentro de ese bloque van también el sistema de la tierra («¿Es de secano o de regadío?») y el "
        "nombre que le pone él («¿Cómo llamas tú a esa tierra?»), y al final dos botones: el principal "
        "«SÍ, APUNTARLA» y el claro «NO ES ESA», porque nadie puede apuntar una tierra que no es suya por "
        "ir deprisa. Los avisos se dicen en su sitio y con lo que hay que hacer: «El mapa necesita "
        "conexión. Si no tienes, puedes apuntar la parcela con su referencia», y mientras busca, "
        "«Mirando en el SIGPAC…». Si no se sabe por dónde empezar, no se pinta un mapa de otro sitio: se "
        "dice y se ofrece «ESTOY AQUÍ» como botón principal. NO pongas barra de pestañas abajo ni menús."
    ),
    "decir_cultivo": (
        COMUN
        + " Es la pantalla donde el agricultor dice qué tiene sembrado, y se llega a ella desde el aviso "
        "de la tierra a la que le falta decirlo. Lo primero, y muy claro, **de qué tierra se está "
        "hablando**: su nombre y sus hectáreas, tal y como él la llama («El Prado · 4,90 ha»), debajo del "
        "título «¿Qué hay sembrado?», que es la misma pregunta que va a contestar. Si esa tierra ya tenía "
        "algo declarado, lo que estaba puesto tiene que salir escrito: quien repite un dato no lo vuelve "
        "a teclear, y lo que se ha tecleado no se pierde si hay que volver a mirarlo. Los campos, en "
        "este orden y cada uno con su frase al lado: «¿Qué hay sembrado?» con «Por ejemplo: trigo blando, "
        "cebada, girasol, alfalfa, viña»; «¿De qué variedad?» con «Si lo sabes. Por ejemplo: Craklin»; "
        "«¿Es de secano o de regadío?», que viene ya elegido porque casi siempre es lo mismo que la "
        "tierra; «¿Desde cuándo está?» con «Si no lo sabes, déjalo en blanco»; y «¿Hasta cuándo?». Las "
        "dos fechas se eligen en un calendario, no se escriben, y ningún campo es obligatorio: el único "
        "que hace falta de verdad es el primero. Abajo, el botón principal «GUARDAR» y el claro "
        "«VOLVER», y si el programa contesta algo, el aviso sale arriba, con una frase que diga qué pasa "
        "y qué hacer. NO pongas barra de pestañas abajo ni menús."
    ),
    "cuaderno_de_la_junta": (
        COMUN
        + " Es la pantalla que más trabajo ahorra de todas: el agricultor descarga de la aplicación de "
        "la Junta el fichero con sus tierras y aquí lo abre para traérselas de una vez, sin teclearlas; "
        "con más de cincuenta tierras, eso es la diferencia entre empezar y dejarlo. Arriba, «Traer mis "
        "tierras del cuaderno de la Junta» y la explicación: «Si ya llevas el cuaderno en la aplicación "
        "de la Junta, no hace falta que escribas tus tierras otra vez: sube aquí el cuaderno que "
        "descargas y el programa las apunta por ti». **Son tres pantallas en una y hay que notar en cuál "
        "se está**, sin pestañas y sin perder de vista el botón de volver. Primero se elige el fichero, "
        "con los pasos contados al lado («Entra en la aplicación de la Junta con tu certificado, "
        "descarga el cuaderno de la campaña y guarda el fichero en el ordenador o en el móvil. Después "
        "súbelo aquí») y el botón «TRAER MIS TIERRAS», que mientras abre el fichero dice «Abriendo el "
        "cuaderno…» y no se puede volver a pulsar. Después, el resumen, con el título «Esto es lo que "
        "trae tu cuaderno»: «Campaña», «Titular», «Tierras apuntadas en el papel», «Tierras distintas», "
        "«Hectáreas que declaras», «Pueblos», «Lo que tienes sembrado» y «Tierras en zona de nitratos», "
        "y debajo «Las tierras que va a apuntar», la lista de lo que va a entrar. **Leer el fichero no "
        "apunta nada**, y por eso el resumen termina con «SÍ, SON MIS TIERRAS» (principal) y «NO, "
        "VOLVER» (claro): lo que entra en el cuaderno lo decide él después de verlo. Por último, el "
        "resultado, «Tus tierras ya están apuntadas», con cada cuenta en su renglón («Tierras nuevas: "
        "51», «Tierras que ya tenías y les he puesto lo que siembras: 3», «Tierras que ya estaban "
        "apuntadas: 2»), lo que se ha rellenado solo («De tus datos de titular he rellenado: nombre y "
        "NIF») y, con su título, «Cosas que conviene que mires»; las cuentas que están a cero no se "
        "enseñan, porque un cero invita a pensar que se ha mirado algo que no se ha mirado. Cierra con "
        "«Puedes subir el cuaderno las veces que quieras: la misma tierra no se apunta dos veces» y con "
        "los botones «VER MIS TIERRAS» y «VOLVER». NO pongas barra de pestañas abajo ni menús."
    ),
    "traer_del_sigpac": (
        COMUN
        + " Es un guion para no teclear ocho datos por cada tierra: pegando la referencia del trozo, el "
        "programa trae solo la superficie, el pueblo y el uso del suelo. Empieza con la explicación «Si "
        "tienes la referencia del trozo (la del papel del SIGPAC), el programa trae solo la superficie, "
        "la pendiente, el uso y el dibujo. Así no hay que copiar ocho números por parcela». El camino "
        "bueno, y el que tiene que verse como el principal, es **pegar la referencia**: la casilla «La "
        "referencia de tu trozo» va con su pista al lado («Pega lo que tengas: la del visor del SIGPAC "
        "(37:70:0:0:503:51), los siete números del papel (37-70-0-0-503-51-1) o la referencia catastral "
        "(37070A50300051000AQ)») y con el ejemplo puesto dentro («37-22-0-0-501-427-1»), porque es lo "
        "que él tiene delante y lo que le evita todo lo demás. Más abajo, y como camino segundo, el que "
        "prefiere ir por partes: «¿En qué provincia está esta parcela?» (con «Todas las provincias» para "
        "no elegir ninguna), «¿En qué pueblo está?» con «Escribe las primeras letras y elígelo de la "
        "lista» y el botón «BUSCAR EL PUEBLO», «El polígono» y «El número de la parcela»; siguen el "
        "nombre que le pone él a la tierra («¿Cómo llamas tú a esa tierra?») y «¿Es de secano o de "
        "regadío?», y cierra el botón principal «BUSCAR MIS TROZOS». Cuando el SIGPAC contesta sale el "
        "título «Los trozos que hay en esa parcela» con «El SIGPAC ha encontrado estos trozos. Marca los "
        "que sean tuyos y los traigo con su superficie, su uso y su dibujo»: cada trozo es «Trozo 1», "
        "con su referencia debajo, y se marca con el dedo; el que está marcado tiene que verse muy "
        "claro, porque de ahí sale lo que se trae. Al final, «TRAERME LOS MARCADOS», que no se puede "
        "pulsar sin haber marcado ninguno y que entonces dice «Marca al menos un trozo para poder "
        "traerlo.»; y si en esa parcela no hay ningún trozo, se dice con «En esa parcela el SIGPAC no "
        "tiene ningún trozo…». NO pongas barra de pestañas abajo ni menús."
    ),
    "hecho": (
        COMUN
        + " Es la pantalla que sale JUSTO DESPUÉS de apuntar algo, y es de las que más veces ve el "
        "agricultor en un día. Lo primero, en grande, la confirmación: «Apuntado. Si te has "
        "equivocado, pulsa DESHACER.». Debajo, el resumen de lo que se acaba de apuntar —qué se ha "
        "echado, en qué tierra, cuánto y qué día—, para que lo repase de un vistazo y vea que se ha "
        "entendido bien. Si el apunte se ha quedado en el móvil porque no hay cobertura, sale su "
        "aviso: «No hay cobertura. No te preocupes: lo hemos guardado en el móvil y se manda solo "
        "cuando llegues a casa.»; si hay cobertura, ese aviso no se enseña. Si el producto tiene un "
        "plazo de espera, va su frase aparte, que es lo que evita coger la cosecha antes de tiempo: "
        "«Fíjate: con lo que has echado hoy, en esta parcela no podrás coger la cosecha hasta el "
        "{fin}.». Los avisos que acompañan al apunte se enseñan tal y como los manda el servidor, "
        "pero los que impiden guardar no salen nunca: si algo impide guardar, esta pantalla no se "
        "abre. Abajo, dos botones grandes y separados: «DESHACER», para cuando alguien se equivoca, "
        "y «VOLVER», para volver al inicio. Quiero que se vea sin buscarlo si el apunte quedó "
        "guardado o quedó esperando a que haya cobertura, y que el de deshacer esté a la vista pero "
        "sin parecer una amenaza. NO pongas barra de pestañas abajo ni menús."
    ),
    "documentos": (
        COMUN
        + " Es «Los papeles»: donde se guardan los papeles que acompañan al cuaderno (contratos, "
        "facturas, resguardos de envases, boletines). Arriba, el título «Los papeles» y, debajo, la "
        "explicación de qué se guarda aquí: «Aquí guardas los papeles que acompañan al cuaderno: el "
        "contrato de la tierra, las facturas de lo que compras, los resguardos de los envases. El "
        "cuaderno dice lo que hiciste; estos papeles son los que lo demuestran.». Lo que hay "
        "guardado va agrupado por carpetas, cada una con su nombre en grande («Contratos», "
        "«Facturas», «Envases», «Licencias y permisos», «Ayudas y subvenciones», «Otros») y dentro "
        "cada papel con su título, su detalle en una línea (qué clase de papel es, la fecha, de "
        "quién es y si tiene el papel subido o solo apuntado) y su botón: «VER EL PAPEL» si ya está "
        "subido, o «SUBIR EL PAPEL» si todavía no, con la frase que lo explica: «Este papel está "
        "apuntado pero no has subido el fichero. Apúntalo igual: así no se te olvida que existe.». "
        "Los papeles que no caen en ninguna carpeta no se esconden: se enseñan igual, bajo «Sin "
        "carpeta». Si todavía no hay ninguno: «Todavía no has guardado ningún papel. No hace falta "
        "que lo tengas todo: empieza por el contrato de la tierra, que es el que más se pide.». Al "
        "final va la frase que hace que el agricultor se tome la molestia de guardarlos: «Si un día "
        "viene una inspección, esto es lo que te van a pedir junto con el cuaderno. Y si se te "
        "pierde el papel de verdad, aquí queda al menos apuntado.». Abajo, «GUARDAR UN PAPEL» como "
        "acción principal y, más discretos, «LISTA DE PAPELES, PARA COPIAR» y «VOLVER». Lo que "
        "tiene que quedar claro de un vistazo es qué se guarda aquí y para qué, y en qué carpeta "
        "está cada cosa. NO pongas barra de pestañas abajo ni menús."
    ),
    "cesta": (
        COMUN
        + " Es «Lo que tengo en el almacén»: el libro de movimientos de cada producto. Arriba, el "
        "título y la explicación: «Aquí ves cuánto producto compraste, cuánto llevas echado y "
        "cuánto te queda. Sirve para dos cosas: saber si te llega para tratar la parcela, y tener "
        "el libro de entradas y salidas que se mira en una inspección.». Después, cuántos productos "
        "hay, con su palabra: «Tienes 1 producto apuntado.» cuando hay uno y «Tienes 3 productos "
        "apuntados.» cuando hay varios. Cada producto es una tarjeta con su nombre, su materia "
        "activa y sus cuentas, una debajo de otra y cada una con su nombre delante: «Compraste» "
        "(con su unidad), «Llevas echado» (con «En 2 apuntes») y «Te queda». **«Te queda» es lo que "
        "el agricultor viene a ver**: tiene que ser el número que más se lea de la tarjeta, para "
        "que se vea de un vistazo si le queda producto o no. Cuando un dato no se sabe se enseña un "
        "guion (—), nunca un cero, y al lado se dice por qué no hay número: «No has apuntado cuánto "
        "compraste, así que no se puede saber cuánto te queda. Apúntalo en la ficha del producto y "
        "aquí saldrán las cuentas.», o «Lo compraste en {comprado} y lo echas en {gastado}. Son "
        "cosas distintas y no se pueden restar: un litro y un kilo no son lo mismo.», o el aviso de "
        "que ha echado más de lo que apuntó que compró. Si no hay ningún producto: «Todavía no has "
        "apuntado ningún producto. Cuando apuntes uno, aquí verás lo que te queda.». Al final, la "
        "frase que da sentido a todo esto, con las palabras del agricultor: «Si un día te preguntan "
        "cuánto producto has comprado y cuánto has echado, esto es la respuesta. Y si te queda "
        "poco, lo ves antes de quedarte sin él en mitad del tratamiento.», y los botones «MIS "
        "PRODUCTOS» y «VOLVER». NO pongas barra de pestañas abajo ni menús."
    ),
    "cultivos": (
        COMUN
        + " Es «Qué hay sembrado»: qué hay este año en cada tierra. Arriba, el título y la "
        "explicación: «Dinos qué hay este año en cada parcela. Con eso, cuando apuntes un "
        "tratamiento o una labor ya no tienes que escribir el cultivo: el programa ya lo sabe.». "
        "Debajo, el aviso que dice cómo va el asunto: «A 1 parcela le falta decir qué tiene este "
        "año.» cuando falta una y «A 3 parcelas les falta decir qué tienen este año.» cuando faltan "
        "varias, o «Ya está dicho qué hay en todas tus parcelas.» si ya está todo dicho. Cada "
        "tierra es una tarjeta con su nombre («El Prado»), su detalle (las hectáreas y si es «Sin "
        "riego» o «Con riego») y lo que tiene sembrado, fila a fila y cada fila con su nombre "
        "delante: «Este año hay» (la especie y la variedad), «Desde» y «Hasta». Al lado de cada "
        "tierra va su botón: «CAMBIARLO» si ya está dicho, o «DECIR QUÉ HAY SEMBRADO» si todavía "
        "no. A las tierras que no lo tienen dicho se les dice en su propia tarjeta: «Todavía no has "
        "dicho qué hay aquí este año.», y a las que repiten lo mismo que el año pasado se les "
        "avisa, porque sembrar lo mismo gasta la tierra: «Aquí has puesto lo mismo que el año "
        "pasado. Si vas a repetir, apúntalo en las medidas preventivas: la rotación de cultivos es "
        "una de las que se piden.». Los años anteriores de esa tierra van en una línea corta y en "
        "pequeño, con «Otros años» delante. Si todavía no hay tierras: «Todavía no tienes parcelas. "
        "Añade la primera y después me dices qué hay sembrado.». Lo que tiene que verse de un "
        "vistazo es qué tierras todavía no tienen dicho qué hay, para decirlo sin tener que "
        "buscarlas. NO pongas barra de pestañas abajo ni menús."
    ),
    "analiticas": (
        COMUN
        + " Es «Los análisis»: los boletines del laboratorio. Arriba, el título y la explicación de "
        "para qué se guardan: «Aquí se guardan los análisis que has mandado hacer: de la tierra, "
        "del agua, de la planta o de la cosecha. Con los números de la tierra se abona mejor, y el "
        "papel del laboratorio no se pierde.». Después, cuántos hay y de cuándo son: la cuenta con "
        "su palabra («1 análisis guardado» o «3 análisis guardados») y, en cada boletín, sus fechas "
        "y «Hace 2 años» cuando el boletín no es de este año. Cada análisis lleva su título con lo "
        "que es y de dónde salió («Análisis de La tierra de El Prado») y su ficha: «De dónde "
        "salió», «Muestra cogida el {fecha}», «Resultado el {fecha}», «Laboratorio» y «Nº de "
        "boletín». Debajo van los números del boletín, cada uno con su nombre y su unidad, que es "
        "lo que de verdad se mira. Si el boletín está guardado pero sin los números copiados, se "
        "dice: «Sin números apuntados: solo está guardado el boletín.». Con el papel, lo mismo: si "
        "está subido, «Ya tienes el boletín guardado.» con el nombre del fichero y el botón "
        "«DESCARGAR EL BOLETÍN»; si no está, «De este análisis no tienes el papel guardado. Si lo "
        "tienes en el móvil o en papel, hazle una foto y súbela.» con el botón «SUBIR EL PAPEL DEL "
        "LABORATORIO». Si no hay ninguno: «Todavía no has apuntado ningún análisis.». Siempre, en "
        "pequeño, la línea que dice qué números se guardan de cada clase: «Los números que se "
        "guardan de cada clase de análisis son los que trae el boletín. De la tierra son los nueve "
        "que pide la administración; de lo demás, todavía no hay listado oficial.». Abajo, «APUNTAR "
        "UN ANÁLISIS» como acción principal y «VOLVER». Lo que hay que ver de un vistazo es cuántos "
        "análisis hay y de cuándo son, porque un boletín viejo no vale igual que uno de este año. "
        "NO pongas barra de pestañas abajo ni menús."
    ),
    "facturas": (
        COMUN
        + " Es «Mis facturas»: la lista de las facturas de compra que el agricultor ha subido, con el "
        "botón de añadir una nueva. La primera frase de la pantalla es la que dice qué es esto: «Aquí "
        "guardas las facturas de lo que compras». Justo debajo tiene que quedar claro PARA QUÉ sirven, "
        "porque de ahí sale la razón de subir el papel: «Sirven para tres cosas: saber cuánto producto "
        "tienes comprado, rellenar el cuaderno cuando te pida la empresa que te lo vendió y el número "
        "de factura, y tener el papel a mano si te lo piden». Cada factura de la lista es una fila "
        "ancha que se lee de un tirón: de quién es (el nombre de la empresa que se lo vendió, o «Sin "
        "decir quién» cuando no se sabe), de qué día es, qué número tiene y cuántas cosas se compraron, "
        "con los dos números con su nombre delante, «Total de la factura» y «Lo que has comprado». Un "
        "total que no se sabe se enseña como una raya y nunca como un cero: es un dato que falta, no un "
        "dato que valga cero. Si todavía no ha subido ninguna, se dice tal cual, «Todavía no has subido "
        "ninguna factura.», y debajo en pequeño «Cuando subas la primera, aquí verás lo que has "
        "comprado y de quién.». Si el ordenador no sabe leer las fotos, se avisa en su bloque, bajo "
        "«Mira esto antes de guardar», explicando que la factura se puede subir igual. Abajo, dos "
        "botones bien separados: «AÑADIR UNA FACTURA», que es el único de color de acción, y «VOLVER». "
        "Cuando se acaba de guardar una, esta misma pantalla dice «Factura guardada.» y ofrece «VER LO "
        "QUE TENGO EN EL ALMACÉN». NO pongas barra de pestañas abajo ni menús."
    ),
    "nueva_factura": (
        COMUN
        + " Es «Añadir una factura»: la puerta para meter el papel en el cuaderno. El título es el "
        "mismo botón con el que se llega, «AÑADIR UNA FACTURA», y debajo va la misma frase de antes, "
        "«Aquí guardas las facturas de lo que compras», porque quien entra aquí viene de la lista. Lo "
        "principal, lo que tiene que verse de un vistazo, es DÓNDE SE ELIGE EL PAPEL: el rótulo «La "
        "factura: una foto o el fichero del proveedor», grande y con su hueco ancho para elegir la foto "
        "del móvil o el fichero que manda el proveedor, y tiene que verse que ahí se toca y que caben "
        "las dos cosas. Al lado, en pequeño, la pista de cómo se hace: «Hazle la foto al papel entero, "
        "con luz y sin torcerlo. Si tienes el fichero, súbelo: se lee mejor y no hay que adivinar "
        "nada.». Después, tres caminos y ninguno esconde a los otros: «LEER LA FACTURA», que es el de "
        "color de acción y mientras trabaja dice «Leyendo la factura…» sin poder pulsarse otra vez, "
        "«ESCRIBIRLA A MANO» y «VOLVER». Hay que dejar claro que el programa solo lo intenta y que no "
        "se guarda nada hasta que él lo mire: si no la puede leer se dice sin palabras raras, «No se ha "
        "podido leer la factura. Prueba otra vez o escríbela a mano.», y si no hay cobertura también, "
        "«Para leer la factura hace falta conexión. El fichero lo tienes en tu móvil: prueba cuando "
        "tengas cobertura.», quedando siempre el camino de escribirla a mano a la vista. NO pongas "
        "barra de pestañas abajo ni menús."
    ),
    "interpretacion_factura": (
        COMUN
        + " Es «Esto es lo que he leído»: lo que el programa ha entendido de la factura, puesto para "
        "que el agricultor lo mire, lo corrija y lo dé por bueno. Tiene que quedar claro desde la "
        "primera línea que esto es una propuesta suya y que lo que se guarda es lo que diga él: «Míralo "
        "y corrige lo que esté mal. Lo que se guarda es lo que tú digas, no lo que yo haya entendido.». "
        "Arriba, en pequeño, de dónde sale la lectura, con el rótulo «Leída de» y, según el caso, «Una "
        "foto (repasa las palabras con tilde)», «El fichero que traía el texto», «Un papel escaneado "
        "(repasa las palabras con tilde)» o «Escrita a mano por ti»: es lo que explica por qué una "
        "palabra puede venir cambiada. Antes de los datos, el bloque «Mira esto antes de guardar» con "
        "los avisos que haya, y el primero y más importante es el de la factura repetida: «Esta misma "
        "factura ya la has subido (nº {numero}). Si la guardas otra vez, la contarás dos veces.». "
        "Después, los datos uno por uno, cada uno con su nombre delante y su número dentro de un hueco "
        "grande que se toca y se corrige con el dedo, todos del mismo tamaño y bien separados: «¿Quién "
        "te lo ha vendido?» con su pista «El nombre de la empresa, como viene en la factura», «Su "
        "NIF», «¿Qué número tiene la factura?», «¿De qué día es?», «Base imponible», «Cuota de IVA», "
        "«Tipo de IVA (%)» y «Total de la factura». Debajo, el bloque «Lo que has comprado» con su "
        "pista, y cada cosa comprada en su ficha con: «Qué es», «Cuánto», «En qué se mide», «A cómo», "
        "«Cuánto suma» y «¿Es uno de tus productos?», con las salidas «No es de la cesta (una "
        "reparación, unas botas…)» y «No lo tengo apuntado: créalo con estos datos». Lo que no cuadra "
        "se dice en la ficha de esa misma cosa comprada, con la frase «La cuenta no cuadra: mira la "
        "cantidad, el precio y el importe», y no solo con un color. Abajo, «SÍ, GUARDAR ESTA FACTURA» "
        "como único botón de acción, que mientras guarda dice «Guardando la factura…» y no se puede "
        "volver a pulsar, y «VOLVER». NO pongas barra de pestañas abajo ni menús."
    ),
    "dictado": (
        COMUN
        + " Es «Dímelo con la voz»: el agricultor cuenta con sus palabras lo que ha hecho en el campo "
        "y el programa lo apunta. La introducción explica el trato: «Cuéntame lo que has hecho con tus "
        "palabras» y «lo que no entienda se queda en blanco», porque nada se apunta sin que él lo vea. "
        "Lo grande y lo que tiene que verse de un vistazo es EL BOTÓN DE HABLAR: dice «HABLAR», lleva "
        "el micrófono dibujado (dibujo y no emoji) y su pista debajo, «cuéntamelo con tus palabras»; el "
        "mismo botón tiene que poder decir que está escuchando, con «Te escucho… di lo que has hecho y "
        "pulsa PARAR» y el botón convertido en «PARAR». Lo que ha dicho tiene que quedar escrito, "
        "entero y a la vista, en su hueco con el rótulo «Escribe lo que has hecho», para poder leerlo, "
        "arreglarlo con el dedo o completarlo con el teclado. Al lado, en pequeño, el ejemplo: "
        "«Por ejemplo:» y la frase de muestra «hoy he echado dos litros en el prado, había pulgón». "
        "Hablar es un atajo y nunca un requisito: donde el móvil no sepa escuchar se dice en ese mismo "
        "sitio, «Este navegador no sabe escuchar. Escribe lo que has hecho y lo entiendo igual.», y el "
        "hueco de escribir se queda igual de grande y de claro. Si no ha oído nada también se dice, "
        "«No he oído nada. Prueba otra vez, o escríbelo.». Abajo, «ENTENDERLO» como botón de acción y "
        "«VOLVER». NO pongas barra de pestañas abajo ni menús."
    ),
    "borrador": (
        COMUN
        + " Es «Lo que he entendido»: lo que el programa ha sacado del dictado, para que el agricultor "
        "lo repase antes de apuntarlo. La introducción pide justo eso: «Mira si está bien. Completa lo "
        "que falte y apúntalo.». Lo entendido va en fichas de dos partes, la pregunta y lo que ha "
        "entendido, y las preguntas son las de siempre, las mismas que vería rellenándolo a mano: «¿Qué "
        "has hecho?», «¿Dónde?», «¿Cuándo?», «¿Qué producto has echado?», «¿Cuánto por hectárea?». Se "
        "tiene que leer de un vistazo qué ha hecho, dónde y cuándo, sin que parezca un montón de texto "
        "seguido. Lo que ha oído pero no sabe dónde ponerlo no se esconde ni se tira: va aparte, bajo "
        "«Esto lo he oído pero no sé dónde ponerlo». Lo que le falta por decir se pide después, bajo "
        "«Para poder apuntarlo me falta esto:», en una lista corta de preguntas. Si no ha entendido "
        "nada, se dice con «No he entendido nada de lo que has dicho. Prueba a decírmelo de otra forma, "
        "o rellénalo a mano: se tarda un minuto.», en vez de enseñar una ficha vacía. Abajo, dos "
        "botones: «ESTÁ BIEN, APUNTARLO» como botón de acción y «CORREGIRLO A MANO» más claro, porque "
        "corregir es tan normal como dar el visto bueno. NO pongas barra de pestañas abajo ni menús."
    ),
    "nuevo_documento": (
        COMUN
        + " Es la pantalla donde el agricultor guarda un papel: el contrato de la tierra, la factura del "
        "abono, el resguardo de los envases. Arriba, el título «GUARDAR UN PAPEL» y la frase que dice "
        "para qué sirve: «Si un día viene una inspección, esto es lo que te van a pedir junto con el "
        "cuaderno. Y si se te pierde el papel de verdad, aquí queda al menos apuntado.» Debajo, lo "
        "primero y más grande: «¿Qué es?», que es el nombre del papel, con su ejemplo al lado (Por "
        "ejemplo: «Contrato de la finca del río» o «Factura del abono de mayo»). **Ese nombre manda: sin "
        "título no se guarda nada**, y cuando falta se dice «Ponle un nombre al papel, para poder "
        "encontrarlo luego.», con el nombre ahí mismo para escribirlo. Después, las demás preguntas, "
        "cada una con su explicación al lado: «¿De qué es?», «¿En qué carpeta lo guardas?» («Como las "
        "tienes tú en casa. Si escribes una nueva, se crea.»), las carpetas que ya tiene como "
        "sugerencia («Las que suele haber»), «¿De qué fecha es?» («La del papel, no la de hoy. Si no lo "
        "sabes, déjalo en blanco.»), «¿De quién es o quién te lo dio?» («El proveedor, el dueño de la "
        "tierra, la cooperativa») y «¿Quieres apuntar algo más?». **Tiene que verse claro qué se está "
        "guardando**: el nombre del papel y su carpeta a la vista mientras se contesta lo demás, como se "
        "lee el lomo de un archivador. Al final, el papel en sí, con su nombre tal cual («El papel en sí "
        "(una foto o el PDF)») y el botón «SUBIR EL PAPEL», porque una foto hecha con el móvil vale "
        "igual que el papel de verdad. Abajo, «GUARDAR» y «VOLVER», y dicho se puede guardar aunque el "
        "papel no lo tenga a mano: «Este papel está apuntado pero no has subido el fichero. Apúntalo "
        "igual: así no se te olvida que existe.» NO pongas barra de pestañas abajo ni menús."
    ),
    "firmar": (
        COMUN
        + " Es «Firmar el cuaderno»: la pantalla donde el agricultor firma el cuaderno del año. Arriba, "
        "en dos pasos que se lean uno detrás del otro: primero qué es firmar —«Firmar es lo que hace que "
        "el cuaderno valga delante de la administración: queda claro quién lo ha hecho y que nadie lo ha "
        "cambiado después.»— y después para qué le sirve, que es para poder enseñarlo delante de quien "
        "se lo pida. Debajo, cómo está hoy: «Todavía no has firmado el cuaderno de este año.» con "
        "«Puedes firmarlo ahora.» **y el botón grande «FIRMAR EL CUADERNO»**, que es lo principal de la "
        "pantalla y lo único que se puede pulsar ahí. Después, los tres pasos con su número y su nombre "
        "—«1. Descarga este fichero», «2. Fírmalo con AutoFirma» y «3. Sube aquí la firma»—, cada uno "
        "con su explicación al lado y su botón: «DESCARGAR EL FICHERO» y «SUBIR LA FIRMA». Al lado del "
        "paso 2 va dicho, sin rodeos, qué es AutoFirma: «AutoFirma es el programa que usa la "
        "administración para firmar. Si no lo tienes, se descarga gratis de la web del Gobierno.» Tiene "
        "que verse de un vistazo en qué punto va: «Ya tienes el fichero. Ábrelo con AutoFirma y firma.» "
        "cuando ya lo ha descargado, y «Firmado el {fecha} por {nombre}. Nadie lo ha cambiado desde "
        "entonces.» cuando ya está firmado. **Si esta instalación no puede firmar, el botón no se "
        "enseña**: en su sitio se dice qué falta y qué hacer, «Para firmar hace falta que entres con tu "
        "certificado. Es lo que dice quién firma: sin él no se puede saber.», en vez de dejar un botón "
        "que no funciona. Y si después de firmar se ha cambiado algo, se avisa en su bloque: «Ojo: este "
        "cuaderno se firmó el {fecha}, pero después se ha cambiado algo. La firma ya no vale para lo que "
        "hay ahora. Vuelve a firmarlo.» Cuando no hay nada apuntado, se dice «Todavía no hay nada "
        "apuntado este año, así que no hay nada que firmar.». Abajo, «VOLVER». NO pongas barra de "
        "pestañas abajo ni menús."
    ),
    "planes": (
        COMUN
        + " Es «El plan de abono del año»: lo que el agricultor va a echarle a cada cultivo y lo que ha "
        "echado de verdad. Arriba, el título y la frase que lo explica: «El plan dice qué abono vas a "
        "echar, cuánto y en qué momento. Después el programa compara lo que apuntas con lo que tenías "
        "previsto, para que no te pases sin darte cuenta.» Debajo, **el aviso de la ley en su bloque y "
        "sin esconderlo**: «El plan de abono es obligatorio desde el 1 de septiembre de 2026. En regadío "
        "lo es desde el 1 de enero de 2026, si el cultivo se sembró o se plantó entre marzo y junio.» "
        "Cada plan va en su bloque, con su nombre delante —«Plan de {cultivo}»— y debajo, en una línea, "
        "la tierra, sus hectáreas y «kilos por hectárea»; después, «El año anterior había (cultivo)» y "
        "«Lo hice con una herramienta: Sí», para que se vea de dónde salen los números. **Lo principal "
        "es la tabla, y tiene que leerse de un vistazo**: su cabecera dice «Tenías previsto · Llevas · "
        "Te queda», y cada fila es un nutriente (N, P y K) con sus tres números en ese mismo orden. "
        "Cuando alguien se ha pasado, en el tercer sitio no va un número sino la palabra «Pasado», la "
        "fila se distingue de las demás y encima sale el aviso en su franja: «Ojo: llevas más de lo que "
        "tenías previsto. Míralo antes de seguir abonando.» Si de un nutriente no hay dato, esa fila no "
        "se enseña: antes que un hueco con un rótulo, nada. Se dice también en qué se apoya el plan, con "
        "«Este plan se apoya en un análisis:» y sus números, o «Este plan no se apoya en ningún "
        "análisis. Si tienes uno de la tierra, se puede enganchar y queda todo junto.»; y cuántos abonos "
        "van contra él: «Un abono apuntado contra este plan.» o «Todavía no has apuntado ningún abono "
        "contra este plan.» Cuando no hay ningún plan todavía, la pantalla no se queda en blanco: se "
        "dice «Todavía no tienes ningún plan de abono apuntado este año.» y queda el botón «HACER EL "
        "PLAN DE ABONO»; cuando ya hay plan, los dos botones son «VER EL PLAN DE ABONO» y «HACER EL "
        "PLAN DE ABONO». Abajo, «VOLVER». NO pongas barra de pestañas abajo ni menús."
    ),
    "ayuda": (
        COMUN
        + " Es «Ayuda»: la pantalla a la que va el agricultor cuando no entiende algo, y tiene que "
        "poder leerse por partes, encontrando lo que busca sin leerlo todo. Arriba, el título y la "
        "promesa: «Aquí está explicado todo lo que te pide el programa, en palabras normales. Si algo no "
        "lo entiendes, no lo apuntes mal: déjalo en blanco y pregúntame.» **Lo primero que se lee es lo "
        "que la ley obliga y lo que no**, bajo el título «Qué te obliga la ley, y qué no», y cada punto "
        "con su nombre en su propia caja: «Llevar el cuaderno al día» («Llevar el cuaderno al día y "
        "poder enseñarlo si te lo piden: eso sí es obligatorio.»), «Mandar los datos a la Junta» "
        "(«Mandar los datos a la Junta por internet es voluntario. Lo dice el artículo 10.2 del Real "
        "Decreto 1054/2022: la ley te obliga a tener el registro, no a enviarlo. Si no lo mandas, no "
        "estás incumpliendo nada.»), «Con un programa tuyo», «Las fechas que importan», «Cuándo será "
        "obligatorio del todo» y «Lo que todavía no está aclarado». Ese primer bloque es el que se tiene "
        "que ver de un vistazo, porque contesta a la primera pregunta de quien empieza: si esto hay que "
        "mandarlo o no. Después, «Para qué sirve esto», con cada explicación con su título delante y una "
        "detrás de otra, para ir derecho a la que interesa: «Para qué sirve el cuaderno», «En papel o en "
        "el móvil», «Qué pasa si no lo llevo», «Por qué te pido tantos datos», «Por qué hay días de "
        "espera», «Por qué te aviso de los nitratos», «Para qué sirve un análisis», «Por qué te pido las "
        "medidas preventivas», «Para qué sirve apuntar lo que vendo» y «Cuánto tiempo hay que guardar "
        "los papeles». Y al final, «Qué significa cada cosa», que es la ayuda de cada casilla que se "
        "rellena: su nombre, qué es, por qué se pide, un ejemplo y qué pasa si falta. Debajo quedan los "
        "cuatro bloques que son tablas largas —«Las reglas de abono de las zonas de nitratos», «Cuánto "
        "nitrógeno permite la tabla para cada cultivo», «Cuándo no se puede abonar» y «Lo que el "
        "programa todavía no puede comprobar»—, y esos se abren al pulsarlos, para que no tapen lo que "
        "se busca. Es una pantalla larga: quiero que se vea dónde acaba un bloque y empieza el "
        "siguiente, y que nada se lea como un muro. Abajo, «VOLVER». NO pongas barra de pestañas abajo "
        "ni menús."
    ),
    "piezas": (
        COMUN
        + " No es una pantalla de verdad: es **una lámina para revisar de una vez los trozos que se "
        "repiten en todas las pantallas**. Dibújalos todos juntos, sobre el mismo fondo, cada uno con su "
        "nombre debajo bien legible, y separados lo suficiente para verse sueltos y no confundirse unos "
        "con otros. **La tarjeta de una tierra**: el nombre que le pone el agricultor («El Prado»), su "
        "superficie con su palabra («4,90 ha»), su pueblo, el dibujo en línea de la forma del trozo a la "
        "izquierda y, dentro de la tarjeta y en una franja que se vea, sus avisos: «Está en zona de "
        "nitratos» y «Tiene una masa de agua cerca»; dibuja una segunda tarjeta igual con la palabra "
        "«ELEGIDA» y su círculo marcado, porque el color solo no informa. **La lista de botones para "
        "elegir**, que es la que usa el asistente para preguntar «¿cuál?»: botones grandes, uno detrás "
        "de otro, cada uno con su dibujo a la izquierda y su explicación de una línea al lado. **Un "
        "campo con su pregunta y su ayuda**: el rótulo grande, el hueco para escribir y, debajo, la "
        "explicación de la casilla con sus cuatro rótulos («Qué es:», «Por qué te lo piden:», "
        "«Ejemplo:» y «Si te falta:»). **Los avisos, los tres juntos**: el normal (una cosa que hay que "
        "saber), el de algo que no se ha podido hacer («No se ha podido mandar. No te preocupes: sigue "
        "guardado en el móvil.» con su botón «VOLVER») y el de lo que está esperando a mandarse («1 "
        "apunte esperando a que haya cobertura. Se manda solo.»). **El bloque de apuntado**: la "
        "confirmación corta con lo que se acaba de apuntar —«Apuntado. Si te has equivocado, pulsa "
        "DESHACER.»— y sus dos botones, «DESHACER» y «VOLVER». **La barra de botones de abajo del "
        "asistente**, pegada al borde de la pantalla y con sitio de sobra debajo, con sus tres botones "
        "en fila —«VOLVER», «DEJARLO» y «SEGUIR»— para que el pulgar llegue sin mover la mano. Y **el "
        "estado vacío**: una lista sin nada dentro, dicha con su frase («Todavía no has apuntado nada "
        "este año.») y el botón que lo arregla al lado, como «HACER EL PLAN DE ABONO» o «AÑADIR», nunca "
        "un hueco en blanco. NO pongas barra de pestañas abajo ni menús."
    ),
    # --- Ronda 91: corregir y borrar lo que uno ha introducido ----------------------------------------
    #
    # David lo pidió así: «recuerda también dejar borrar las cosas que introduzca porque puede que me
    # equivoque, o modificar también». Son dos estados nuevos de la aplicación y ninguna pantalla los
    # tenía diseñados: la ficha de un apunte con sus dos botones, el asistente abierto **en modo
    # corrección** y la pantalla que pregunta si de verdad se quiere borrar. Se piden como dos láminas
    # (no son pantallas sueltas: son trozos) y con los textos de verdad de `textos.py`.
    "corregir_un_apunte": (
        COMUN
        + " No es una pantalla de verdad: es una **lámina con los tres momentos de corregir un apunte "
        "que ya está guardado**, uno debajo de otro, cada uno con su nombre bien legible. **1) La ficha "
        "del apunte dentro de la lista del cuaderno**: arriba a la izquierda, en pequeño, «Apunte 1», y "
        "a la derecha la fecha y de qué clase es («12/05/2026 · Producto»); el nombre del producto en "
        "grande («Glifosato 36 SL»); y debajo, cada dato con su nombre delante, uno por renglón: «Tierra "
        "y parcela: El Prado», «Hectáreas tratadas: 4,90 ha», «Cuánto por hectárea: 2,00 L/ha», "
        "«Cultivo: Trigo blando», «Hasta aquí no puedes coger la cosecha: 26/05/2026». Debajo de la "
        "ficha, **dos botones del mismo ancho, uno al lado del otro**: «CORREGIR» (el primero, con el "
        "color de acción de la aplicación) y «BORRAR» (el segundo, en el color de peligro). Tienen que "
        "verse claramente como dos acciones de esa ficha y a la vez como algo que no es la ficha (no se "
        "toca la tarjeta: se tocan los botones). **2) El asistente abierto en modo corrección**: arriba "
        "la barra de progreso y, en grande, «Corregir lo que apuntaste»; debajo, la explicación: «Está "
        "puesto lo que apuntaste. Cambia lo que esté mal y guárdalo: queda escrito que lo has "
        "cambiado.»; después un campo de ejemplo con lo que ya había puesto («4,90»); y abajo, pegados "
        "al borde, dos botones: «VOLVER» y «GUARDAR LOS CAMBIOS». **3) El final**: una pantalla corta "
        "que dice «Corregido» en grande y debajo «Ya está cambiado. Lo que había antes queda guardado "
        "en el historial del cuaderno.». En los tres sitios, lo que es un aviso se ve como un aviso y "
        "lo que es un dato se lee como un dato. NO pongas barra de pestañas abajo ni menús."
    ),
    "borrar_un_apunte": (
        COMUN
        + " No es una pantalla de verdad: es una **lámina con los dos casos de borrar un apunte**, uno "
        "debajo de otro, cada uno con su nombre bien legible. **1) La pregunta, cuando el apunte se "
        "puede borrar**: en grande, como una pregunta y no como un aviso, «¿Seguro que quieres "
        "borrarlo?»; debajo, en pequeño, «De tu cuaderno desaparece del todo.»; después, **lo que va a "
        "desaparecer**, con los mismos datos de la ficha que el agricultor acaba de tocar: «Producto: "
        "Glifosato 36 SL», «Tierra y parcela: El Prado», «Hectáreas tratadas: 4,90 ha»; luego, dos "
        "avisos: «Si solo te has equivocado al escribirlo, mejor CORREGIRLO: así el apunte queda bien "
        "en vez de desaparecer.» y «El programa guarda por dentro qué había apuntado y qué día lo "
        "borraste, por si algún día hay que explicarlo.»; y abajo **tres botones**: «SÍ, BORRARLO» (en "
        "el color de peligro), «MEJOR CORREGIRLO» y «VOLVER». Los dos últimos tienen que verse más "
        "tranquilos que el primero: el botón que quita algo del cuaderno no puede ser el que más "
        "apetezca pulsar. **2) El caso de un apunte firmado**: el mismo tipo de pantalla, pero la "
        "pregunta dice «Este apunte está firmado, así que no se puede borrar. Se puede ANULAR: queda "
        "tachado, con el motivo, y la firma sigue cuadrando.» y **no hay ningún botón de borrar**: los "
        "botones son «ANULARLO» y «VOLVER». Deja claro, sin palabras raras, que aquí lo que se puede "
        "hacer es tachar el apunte y no hacerlo desaparecer. NO pongas barra de pestañas abajo ni "
        "menús."
    ),
    "campanas": (
        COMUN
        + " Es «Los años de mi cuaderno»: la lista de los años que tiene el agricultor y en cuál está "
        "apuntando ahora. Arriba, el título y una frase corta que explique que el cuaderno se lleva por "
        "años: «Tu cuaderno se lleva por años: lo que apuntas va al año en el que estás.» Debajo, la "
        "lista de años, del más nuevo al más viejo, y cada año en su tarjeta: el año **en muy grande** "
        "(«2026»); debajo, sus fechas en un renglón («Empieza: 01/09/2025» y «Termina: 31/08/2026»); y "
        "una etiqueta de estado que diga «ESTÁS APUNTANDO EN ESTE» en el año que se está llevando y "
        "«Año cerrado» en el que el agricultor ya ha dado por terminado. Cada tarjeta tiene que decir "
        "también **cuánto hay dentro** —«Tiene 42 apuntes dentro»— porque eso es lo que explica por qué "
        "un año no se puede quitar; si no tiene nada, «No tiene nada apuntado». Debajo de los datos de "
        "cada año, **dos botones del mismo ancho, uno al lado del otro**: «CORREGIR» (el primero, con el "
        "color de acción de la aplicación) y «BORRAR» (el segundo, en el color de peligro). Al final de "
        "la lista, separado y como lo que menos se toca, el botón «EMPEZAR UN AÑO NUEVO», con su "
        "explicación debajo: «Cuando empiece el año que viene, hazlo aquí: lo que apuntes irá a ese "
        "año.» Y el botón «VOLVER» al final del todo. Cuando un año tiene cosas dentro, su tarjeta lo "
        "dice para que no extrañe que no se pueda quitar: «Aquí dentro hay cosas apuntadas: primero "
        "quítalas y después podrás quitar el año.» NO pongas barra de pestañas abajo ni menús."
    ),
}


# ──────────────────────────────────────────────────────────────────────────────
# LA VERSIÓN DE ESCRITORIO (30/09/2026, la pidió David)
# ──────────────────────────────────────────────────────────────────────────────
#
# POR QUÉ HAY DOS FAMILIAS DE ENCARGOS. Todo lo de arriba está pedido para **móvil** («se usa de pie en el
# campo, con una mano»), y ese es el uso principal. Pero David lo dijo claro: *«debe ser responsive para
# usarse en pc y móvil, no solo móvil… hacer una versión para pc que parezca una aplicación de gestión»*.
# Un agricultor que lleva 64 tierras no las mira de una en una en el móvil: se sienta en el despacho, abre
# el ordenador y quiere **una tabla con filtros, columnas y totales**, como en cualquier programa de
# gestión. Son dos usos de verdad y una sola aplicación.
#
# Así que estos encargos son de **escritorio** (`deviceType: DESKTOP`, 1440×900) y describen lo que un
# programa de gestión tiene que tener: menú lateral con los módulos, barra de arriba con la finca, la
# campaña y el usuario, tablas con columnas que se ordenan, filtros, acciones por fila y un panel de datos
# al lado. **El mismo programa, la misma información**: en el móvil eso se ve en una columna con tarjetas
# (lo que ya está hecho), y en el ordenador, en tablas.
#
# Se guardan en `docs/stitch/escritorio/` y **no se pisan con los del móvil**: son familias distintas y se
# aplican por separado.
CARPETA_ESCRITORIO = DESTINO / "escritorio"

COMUN_ESCRITORIO = (
    "Aplicación web de GESTIÓN para el ORDENADOR (pantalla de 1440x900), para una explotación agrícola de "
    "Castilla y León. La usa el mismo agricultor que usa la versión de móvil, pero aquí está SENTADO EN EL "
    "DESPACHO, con ratón y teclado, y quiere hacer en diez minutos lo que en el campo hace en dos horas: "
    "ver de un vistazo el estado de todo, filtrar, ordenar, comparar, cuadrar números y sacar documentos. "
    "El ejemplo a seguir es un **programa de gestión empresarial**: menú lateral con los módulos, barra de "
    "arriba con la finca y el año, y el contenido en **tablas y paneles**, no en tarjetas grandes de móvil. "
    "Reglas: nada de sombras, nada de degradados, nada de animaciones; **iconos dibujados (SVG), no emoji**; "
    "los colores y la tipografía son los del contrato de diseño del proyecto (verde oscuro, fondo claro, "
    "tinta oscura); los botones de la barra de herramientas y de las filas son **compactos** (32-40 px de "
    "alto, no 64: aquí se usa el ratón), y los del formulario principal, cómodos. Cada columna lleva su "
    "nombre arriba y se puede ordenar. Cada fila lleva sus acciones a la derecha («Editar», «Borrar») y la "
    "fila entera no es un botón. Los números van alineados a la derecha y con su unidad. Todo lo que se "
    "enseña tiene que poder leerse sin que nadie lo explique, y **no se enseña ningún dato inventado**: lo "
    "que no se sabe se deja en blanco o se dice «—». NO pongas barra de pestañas abajo. "
)

PANTALLAS_ESCRITORIO: dict[str, str] = {
    # 1. El armazón: es el encargo más importante de todos, porque define el marco de lo demás.
    "estructura": (
        COMUN_ESCRITORIO
        + " Es **el armazón de la aplicación con la lista de tierras dentro**, y es la pantalla que define "
        "cómo son las demás. **1) Menú lateral, a la izquierda, fijo, de unos 240 px**, con el nombre de la "
        "finca arriba y los módulos debajo, uno por renglón con su icono dibujado y su nombre: «Panel», "
        "«Cuaderno», «Tierras», «Almacén», «Análisis», «Ventas», «Plan de abono», «Documentos», «Facturas», "
        "«Productos y máquinas», «Años del cuaderno», «Mis datos». El módulo en el que se está tiene que "
        "verse claramente marcado (fondo distinto y una barra a la izquierda), y los demás no. **2) Barra "
        "de arriba**, a lo ancho: a la izquierda el nombre de la pantalla («Tierras») y debajo su "
        "explicación en una frase; a la derecha, un selector de campaña («2026»), el nombre del usuario "
        "(«David Pérez Velasco») y el botón principal «APUNTAR» (verde sólido, es lo que más se usa). "
        "**3) El contenido, en una franja de herramientas y una tabla.** La franja lleva: un campo de "
        "búsqueda («Buscar entre tus tierras»), un desplegable de filtro por pueblo y otro por cultivo, la "
        "casilla «Sólo las que les falta decir qué tienen», y arriba a la derecha los botones «AÑADIR UNA "
        "TIERRA», «SACAR EN EXCEL» y «IMPRIMIR». Debajo, **la tabla**: 64 filas de tierras, con las columnas "
        "«Nº», «Nombre», «Referencia SIGPAC», «Pueblo», «Hectáreas», «Qué tiene este año», «Sistema» y "
        "«Acciones». Las hectáreas alineadas a la derecha con dos decimales y su «ha». En «Qué tiene este "
        "año» sale el cultivo, y cuando falta se ve un aviso en ámbar con el botón «DECIRLO» al lado; cuando "
        "está, se ve el cultivo y su variedad. En «Acciones», dos botones pequeños por fila: «Editar» y "
        "«Borrar» (el de borrar en el color de peligro, más discreto). La cabecera de la tabla se queda fija "
        "al bajar. Al pie de la tabla: «64 tierras · 187,42 ha en total» y los botones de página. "
        "**4) A la derecha, un panel lateral de detalle** (unos 320 px) que enseña la tierra elegida: su "
        "nombre, su referencia oficial, sus hectáreas, el dibujo de su forma, qué tiene sembrado este año y "
        "sus tres últimos apuntes, con el botón «VER LA TIERRA ENTERA». Si no hay ninguna elegida, el panel "
        "dice «Toca una tierra de la lista para verla aquí». NO pongas barra de pestañas abajo."
    ),
    # 2. El panel de mando: lo que se mira al sentarse.
    "panel": (
        COMUN_ESCRITORIO
        + " Es **el panel de mando**: lo que el agricultor mira al sentarse, para saber cómo va el año sin "
        "abrir nada. Arriba, el armazón de siempre (menú lateral con «Panel» marcado, barra de arriba con la "
        "finca, la campaña y el usuario). Debajo, en una sola fila, **cuatro tarjetas de números**, cada una "
        "con su rótulo pequeño, el número grande y una frase de contexto debajo: «Apuntes este año» con «24 "
        "apuntes de producto», «Hectáreas tratadas» con «62,40 ha», «Lo que he vendido» con «42.000 kg de "
        "trigo», y «Gasto en fitosanitarios» con «1.240,50 €» y «12 facturas». Después, dos columnas: a la "
        "izquierda y más ancha, **«Lo que falta por completar»**, con cada cosa que le falta al cuaderno en "
        "su renglón, el aviso en ámbar a la izquierda y su botón a la derecha («A 10 tierras les falta decir "
        "qué tienen este año» + «DECIRLO»; «El plan de abono de este año no está» + «HACERLO»; «Tienes 3 "
        "facturas sin el papel guardado» + «SUBIRLAS»). Si no falta nada, «Todo apuntado: tu cuaderno está "
        "al día.» A la derecha, **«Los últimos apuntes»**, cinco renglones con la fecha, el producto o el "
        "trabajo, la tierra y las hectáreas, y al final un enlace «Verlos todos». Abajo del todo, una franja "
        "con los botones «SACAR EL CUADERNO EN PAPEL», «GUARDAR LOS DATOS EN UN FICHERO» y «FIRMAR EL "
        "CUADERNO». NO pongas barra de pestañas abajo."
    ),
    # 3. El cuaderno: la tabla de apuntes, que es el corazón del programa.
    "cuaderno": (
        COMUN_ESCRITORIO
        + " Es **«El cuaderno»: la tabla de todo lo que se ha apuntado este año**, que es el corazón del "
        "programa. Arriba, el armazón de siempre con «Cuaderno» marcado en el menú. Debajo, la franja de "
        "herramientas: un campo de búsqueda («Buscar en el cuaderno»), un desplegable «De qué clase» "
        "(Producto, Abono, Trabajo, Cosecha, Todo), dos campos de fecha («Desde» y «Hasta»), un desplegable "
        "de tierras y la casilla «Sólo los que están firmados». A la derecha, «APUNTAR» (verde sólido) y "
        "«SACAR EN PAPEL». Después, **la tabla de apuntes**, con las columnas: «Fecha», «Clase» (una "
        "etiqueta pequeña: Producto / Abono / Trabajo), «Qué» (el producto o el trabajo, en negrita), "
        "«Tierra», «Hectáreas», «Cultivo», «Firmado» y «Acciones» («VER», «Editar», «Borrar»). Las filas "
        "agrupadas por mes, con el mes escrito en una franja fina encima de sus apuntes («Octubre de 2026 · "
        "8 apuntes»). Las filas de los apuntes firmados llevan su marca de firmado y **el botón de borrar "
        "apagado**, porque un apunte firmado no se puede borrar: en su lugar se ofrece «ANULARLO». Al pie de "
        "la tabla, «24 apuntes · 62,40 ha tratadas» y la paginación. A la derecha, **un panel de detalle** "
        "con el apunte elegido: la fecha y la clase arriba, el producto en grande, y debajo cada dato con su "
        "nombre («Tierra y parcela», «Hectáreas tratadas», «Cuánto por hectárea», «Cultivo», «Hasta aquí no "
        "puedes coger la cosecha»), más el botón «CORREGIR» y el de volver a su sitio. NO pongas barra de "
        "pestañas abajo."
    ),
    # 4. Un formulario de alta/corrección en escritorio: es donde se teclea.
    "formulario": (
        COMUN_ESCRITORIO
        + " Es **el formulario de un apunte en el ordenador** (aquí, echar producto): la pantalla donde se "
        "teclea. Arriba, el armazón de siempre con «Cuaderno» marcado. Debajo, una cabecera de pantalla con "
        "el título «Apuntar lo que he echado» y, a la derecha, los botones «CANCELAR» y «APUNTARLO» (verde "
        "sólido). El formulario va **en dos columnas dentro de un panel blanco con borde**, no en una "
        "columna estrecha de móvil: a la izquierda los datos del apunte y a la derecha los que dependen de "
        "ellos. Cada campo lleva su pregunta encima en negrita, su explicación pequeña debajo y su hueco; los "
        "obligatorios llevan una marca. A la izquierda: «¿Dónde lo has echado?» (una lista de tierras con su "
        "buscador arriba, y el elegido marcado), «¿Qué has echado?» (desplegable de productos de tu cesta, "
        "con su número de registro debajo), «¿Cuánto por hectárea?» con su unidad («L/ha»), y «¿Cuándo?» con "
        "su fecha y los atajos «HOY» y «AYER». A la derecha: «¿Cuántas hectáreas has tratado?» (que se "
        "rellena solo al elegir la tierra y se puede corregir), «¿Por qué lo has echado?» (plaga o motivo), "
        "«¿Quién lo aplica?» y «¿Con qué máquina?», y «¿Qué hiciste antes para no tener que echarlo?» con las "
        "medidas que ya declaró marcadas. **A la derecha del formulario, un panel de resumen** que se lee de "
        "un vistazo y va diciendo lo que se lleva puesto: la tierra, el producto, las hectáreas, la dosis, la "
        "fecha y —esto es lo que importa— **«Hasta aquí no puedes coger la cosecha: 26/05/2026»** calculado "
        "con los días de espera del producto. Si falta algo obligatorio, el aviso va en rojo en ese renglón "
        "del resumen y el botón de apuntar se queda apagado. NO pongas barra de pestañas abajo."
    ),
    # 5. El almacén: números, compras, gastos y existencias.
    "almacen": (
        COMUN_ESCRITORIO
        + " Es **«El almacén»: los números de lo que se ha comprado, lo que se ha echado y lo que queda**. "
        "Arriba, el armazón de siempre con «Almacén» marcado. Debajo, cuatro tarjetas de números: «Producto "
        "comprado» («1.240,00 L»), «Producto echado» («860,50 L»), «Te queda» («379,50 L») y «Gasto del año» "
        "(«2.410,80 €»). Después, **la tabla de productos**, con las columnas: «Producto», «Nº de registro», "
        "«Comprado», «Echado», «Te queda», «Gasto», «Estado» y «Acciones». En «Te queda», si el número es "
        "negativo (se ha echado más de lo comprado) tiene que verse claramente como un aviso en rojo con su "
        "explicación («Has echado más de lo que has comprado»); si no se puede comparar, se dice «No se puede "
        "comparar» en vez de un cero, que sería mentira. «Estado» lleva una etiqueta: «Las cuentas cuadran» o "
        "«Míralo». Cada fila tiene «Ver sus apuntes» y «Editar». A la derecha, un panel con el producto "
        "elegido: su ficha, el número de la etiqueta, su plazo de seguridad y sus últimos movimientos "
        "(compra y tratamientos, uno por renglón con su fecha y su cantidad). Y abajo, la tabla de **facturas "
        "del año**: «Fecha», «Proveedor», «Nº», «Base», «IVA», «Total», «Papel guardado» (sí o no) y "
        "«Acciones». NO pongas barra de pestañas abajo."
    ),
    # ── Los encargos de la segunda tanda (30/09/2026, los pidió David) ────────────────────────────────
    #
    # POR QUÉ ESTOS Y NO OTROS. La primera tanda (los cinco de arriba) se pidió **antes** de construir la
    # versión de escritorio, y con ella se hicieron el armazón, el panel de mando, la tabla del cuaderno y el
    # almacén. Pero luego salieron más pantallas de escritorio **sin diseño propio** —la tabla de «qué hay
    # sembrado», la de las facturas y la de los años del cuaderno se construyeron copiando la forma de las
    # otras, que es justo lo que no se quiere— y quedan módulos enteros por hacer.
    #
    # David lo pidió así: *«estás usando Stitch para ayudarte en la implementación de las nuevas páginas/uis?
    # hazlo si no es así»*. Y su instrucción de la ronda 90 sigue en pie: *«no pares hasta tener toda la app
    # cubierta»*. Así que van los seis que faltan para tener **todo lo que ya existe** con su diseño, y los
    # que hacen falta para las listas que vienen después.
    "cultivos": (
        COMUN_ESCRITORIO
        + " Es **«Qué hay sembrado»: la tabla de lo que tiene cada tierra este año**. Es la lista más larga "
        "del programa después de las tierras (una fila por tierra; el agricultor tiene 64). Arriba, el armazón "
        "de siempre con «Qué hay sembrado» marcado en el menú. Debajo, el título («Qué hay sembrado»), su "
        "explicación en una frase («Dinos qué hay este año en cada parcela. Con eso, cuando apuntes un "
        "tratamiento o una labor ya no tienes que escribir el cultivo: el programa ya lo sabe.») y **un aviso "
        "en ámbar que dice cuántas faltan** («A 10 parcelas les falta decir qué tienen este año»). Después, "
        "**la tabla**, con las columnas: «Tierra», «Hectáreas» (a la derecha, con dos decimales y su «ha»), "
        "«Este año hay» (el cultivo y su variedad), «Otros años» (los dos o tres últimos, en pequeño y con su "
        "año delante: «2025: CEBADA · 2024: TRIGO BLANDO»), «Estado» y «Acciones». En «Estado», una etiqueta: "
        "«Al día» (verde) en las que ya está dicho, «Falta rellenar» (ámbar) en las que no. En «Acciones», un "
        "botón por fila: «CAMBIARLO» en las que ya está dicho y «DECIRLO» en las que falta. Cuando el cultivo "
        "de este año es el mismo que el del año pasado, tiene que verse un aviso pequeño y claro en la misma "
        "fila («Repite lo del año pasado»), porque sembrar lo mismo dos años seguidos gasta la tierra. La "
        "cabecera de la tabla se queda fija al bajar. Al pie: «64 tierras · 54 con su cultivo dicho». Y un "
        "bloque de explicación abajo («Sirve para tres cosas: el cuaderno de cada año dice qué había en la "
        "tierra, puedes ver qué sembraste los años anteriores —que es lo que ayuda a decidir la rotación— y el "
        "aviso de «en esa fecha no había cultivo» funciona.»). NO pongas barra de pestañas abajo."
    ),
    "facturas": (
        COMUN_ESCRITORIO
        + " Es **«Mis facturas»: la tabla de las facturas de compra del año**. Arriba, el armazón de siempre "
        "con «Mis facturas» marcado. Debajo, el título con su explicación y la cuenta («1 factura guardada»). "
        "Después, **la tabla**, con las columnas: «Fecha», «Quién te lo vendió», «Nº de factura», «Base», "
        "«IVA», «Total» (los tres importes a la derecha, con su «€» y dos decimales), «El papel» y "
        "«Acciones». En «El papel»: si la factura tiene guardada la foto o el PDF se dice («Con el papel "
        "subido»); si no, se ve **una etiqueta en ámbar que dice «Falta el papel»**, porque es lo primero que "
        "se pide en una inspección y lo que hay que arreglar. Un importe que no se sabe **no es un cero**: se "
        "deja en blanco. En «Acciones», por fila: «Subir el papel» (o «Ver el papel» si ya está), «Editar» y "
        "«Borrar» (este último en el color de peligro, más discreto). La cabecera se queda fija al bajar. Al "
        "pie, el total del año («1 factura · 800,00 €»). Arriba a la derecha, el botón principal «AÑADIR UNA "
        "FACTURA». Y debajo de la tabla, el aviso del lector («El lector de fotos está funcionando con el "
        "idioma español: todo lo que lea te lo enseño para que lo confirmes.»). NO pongas barra de pestañas "
        "abajo."
    ),
    "campanas": (
        COMUN_ESCRITORIO
        + " Es **«Los años de mi cuaderno»: la tabla de los años (campañas) que tiene el agricultor**. Es una "
        "lista corta (tres o cuatro filas) pero de la que cuelga el año entero, así que tiene que leerse muy "
        "claro. Arriba, el armazón de siempre con «Los años de mi cuaderno» marcado. Debajo, el título y su "
        "explicación («Tu cuaderno se lleva por años: lo que apuntas va al año en el que estás. Aquí ves los "
        "años que tienes y puedes arreglar o quitar el que esté mal.»). Después, **la tabla**, con las "
        "columnas: «Año», «Empieza», «Termina», «Qué tiene dentro», «Estado» y «Acciones». En «Año», el año en "
        "grande y, al lado, la etiqueta «Estás apuntando en este» (ámbar) en el que se está llevando. En «Qué "
        "tiene dentro» va, en su renglón principal, **cuántos apuntes tiene** («0 apuntes», «38 apuntes») y, "
        "debajo y en pequeño, lo que hay dentro que no son apuntes («54 tierras con su cultivo dicho»), con una "
        "etiqueta en ámbar que dice «Hay cosas dentro» cuando el año no se puede quitar. En «Estado»: «Año "
        "abierto» o «Año cerrado». En «Acciones»: «CORREGIR» y «BORRAR», y **el BORRAR apagado con la frase que "
        "lo explica** cuando el año tiene cosas dentro (no se puede quitar un año con datos). Al pie: «3 años "
        "en tu cuaderno». Debajo de la tabla, el botón «EMPEZAR UN AÑO NUEVO» con su explicación. NO pongas "
        "barra de pestañas abajo."
    ),
    "ventas": (
        COMUN_ESCRITORIO
        + " Es **«Lo que he vendido»: la tabla de la cosecha comercializada del año**. Arriba, el armazón de "
        "siempre con «Lo que he vendido» marcado. Debajo, el título, su explicación y la cuenta del año («2 "
        "ventas apuntadas · 44.000 kg»). Después, **la tabla**, con las columnas: «Fecha», «Qué», «Cuánto», «A "
        "quién», «Partida», «Albarán», «De dónde» y «Acciones». «Cuánto» va a la derecha, con su unidad y sin "
        "inventarse nada: si no se sabe, en blanco. En «Acciones», «Editar» y «Borrar». La cabecera se queda "
        "fija. Al pie, el total vendido del año. Y un aviso claro cuando lo vendido **no cuadra con lo "
        "cosechado** («Has vendido más de lo que has apuntado cosechado: lo normal es que se te haya olvidado "
        "apuntar la cosecha»), porque ese descuadre es justo lo que mira una inspección. Arriba a la derecha, "
        "el botón principal «APUNTAR UNA VENTA». NO pongas barra de pestañas abajo."
    ),
    "analisis": (
        COMUN_ESCRITORIO
        + " Es **«Los análisis»: la tabla de los boletines del laboratorio** (de tierra, de agua, de planta, "
        "de cosecha y de residuos). Arriba, el armazón de siempre con «Los análisis» marcado. Debajo, el "
        "título, su explicación y la cuenta («1 análisis guardado»). Después, **la tabla**, con las columnas: "
        "«Fecha», «De qué es» (tierra, agua, planta, cosecha, residuos), «De dónde» (la tierra o la nave), "
        "«Laboratorio», «Nº de informe», «Edad» y «Acciones». En «Edad», una etiqueta con lo que se viene a "
        "mirar («De este año», «Hace 2 años» en ámbar cuando ya es viejo). En «Acciones»: «Ver el boletín», "
        "«Subir el informe» (si falta), «Editar» y «Borrar». Al pie, cuántos hay. Y a la derecha, un panel con "
        "**el boletín elegido**: sus números, cada uno con su nombre y su unidad («Materia orgánica 1,80 %», "
        "«pH 7,4»), y el enlace al papel. Arriba a la derecha, el botón principal «APUNTAR UN ANÁLISIS». NO "
        "pongas barra de pestañas abajo."
    ),
    "maestros": (
        COMUN_ESCRITORIO
        + " Es **«Productos y máquinas»: las fichas de lo que se usa en la finca** (los productos "
        "fitosanitarios, los abonos, quién aplica, quién asesora, las máquinas y las naves). Arriba, el "
        "armazón de siempre con «Productos y máquinas» marcado. La pantalla está **organizada por pestañas o "
        "por bloques con su título**, uno por cada clase de ficha («Productos», «Abonos», «Quién aplica», "
        "«Quién asesora», «Máquinas», «Naves»), y cada bloque con su botón «AÑADIR» a la derecha. Dentro de "
        "cada bloque, **una tabla compacta** con lo que hace falta para reconocer cada ficha, que es distinto "
        "en cada una: los productos con «Producto», «Nº de registro», «Materia activa», «Dosis máxima» y "
        "«Días de espera»; los abonos con «Abono», «Riqueza N», «Riqueza P» y «Riqueza K»; quien aplica con "
        "«Nombre», «NIF» y «Carné»; las máquinas con «Máquina», «Tipo» y «Nº de serie»; las naves con «Nave», "
        "«Tipo» y «Superficie». Cada fila con «Editar» y «Borrar» a la derecha. **Lo que no se sabe se deja en "
        "blanco, nunca un cero ni un guion de relleno.** La cabecera de cada tabla se queda fija al bajar. NO "
        "pongas barra de pestañas abajo."
    ),
}

# ──────────────────────────────────────────────────────────────────────────────────────────────────
# LOS TRES PROTOTIPOS DEL CRM (T03 / E1, 01/10/2026)
# ──────────────────────────────────────────────────────────────────────────────────────────────────
#
# POR QUÉ ESTOS TRES Y CON ESTE TEXTO. El contrato de implementación
# (`docs/CONTRATO_IMPLEMENTACION_CRM.md`, apartados 4 y 8) fija el primer encargo a Stitch: **S01 Inicio de
# gestión, S02 Tierras y mapa y S03 Ficha de tierra**, con la navegación persistente, jerarquía clara,
# tablas compactas, y tres criterios que se incumplen fácil: **a 1024 px no se esconden las Acciones**, el
# panel lateral pasa debajo cuando no cabe, y **mapa y tabla comparten la selección**.
#
# Dos cosas que NO se le mandan a Stitch, y están escritas aquí para que no se cuelen:
#  1. **Ningún dato real ni personal**: el encargo lleva un juego de datos **ficticio y explícito** (64
#     tierras, nombres largos, 10 sin cultivo, 3 sin forma, importes desconocidos, un pago parcial y una
#     inspección vencida). La base de datos real no sale del ordenador del agricultor.
#  2. **Ninguna cifra inventada**: se le dice expresamente que no invente salud, ingresos ni cumplimiento.
#     Lo que no se sabe se enseña como desconocido o pendiente, no como verde.
COMUN_CRM = (
    "CRM agrícola español de escritorio (1440x900) para una explotación de Castilla y León. Lo usa el "
        "mismo agricultor en dos momentos: **en el despacho**, con ratón y teclado, para ver el estado de "
        "todo, filtrar, ordenar, cuadrar cuentas y sacar documentos; y **en el campo**, desde el móvil. Esta "
        "pantalla es la del despacho. Datos de ejemplo FICTICIOS (no son de nadie): 64 tierras con nombres "
        "largos («501/10015-1 VEZA VELLOSA», «Las Suertes de Arriba (parcela 12)»), 10 de ellas sin cultivo "
        "declarado, 3 sin geometría, varias campañas (2024, 2025, 2026), importes que a veces se desconocen, "
        "un pago parcial y una inspección de maquinaria vencida. "
        "Reglas que no se pueden romper: **nada de sombras, degradados ni animaciones**; iconos dibujados "
        "(SVG), no emoji; los colores y la tipografía son los del contrato de diseño del proyecto (verde "
        "oscuro, fondo claro, tinta oscura); **los botones de la barra y de las filas, compactos** (32-40 px, "
        "aquí se usa el ratón) y los de la acción principal, cómodos; cada columna lleva su nombre arriba y se "
        "puede ordenar; cada fila lleva sus acciones a la derecha y **la fila entera no es un botón**; los "
        "números van alineados a la derecha con su unidad y **los importes con dos decimales y su €**. "
        "**A 1024 px de ancho no se puede esconder la columna de Acciones**: si la tabla y el panel no caben "
        "juntos, el panel pasa debajo. **No se enseña ningún dato inventado**: lo que no se sabe se deja en "
        "blanco o se dice «—» o «pendiente», nunca un cero. **Prohibido inventar** salud de cultivos, "
        "ingresos, rendimientos o porcentajes de cumplimiento: si no hay dato, se dice que falta. Los estados "
        "que hay que dibujar, además del cargado: vacío (recién empezado), sin resultados por filtro, "
        "cargando, error de servicio y conflicto. NO pongas barra de pestañas abajo."
    )
PANTALLAS_ESCRITORIO["crm_inicio"] = (
    COMUN_CRM
    + " Es **el Inicio de gestión**: lo primero que se ve al entrar en el despacho, para saber qué hay "
        "que hacer hoy sin abrir nada. La navegación lateral (menú de despacho, fijo, con el módulo activo "
        "marcado y una barra de resalte) y la barra de arriba (explotación, **selector de campaña visible "
        "(2026)**, campaña, búsqueda global que encuentra tierra, referencia SIGPAC, contacto, producto, "
        "factura y máquina, un botón «Añadir» y los pendientes personales) son persistentes en todas las "
        "pantallas: aquí se ven por primera vez y hay que dibujarlas con detalle. El contenido tiene TRES "
        "zonas: (1) **Pendientes que requieren acción**, en tarjetas o renglones, cada una con su cifra y su "
        "botón: «Tierras sin cultivo declarado: 10» + «VERLAS», «Trabajos previstos esta semana: 4» + «VER LA "
        "AGENDA», «Documentos por revisar: 3» + «REVISAR», «Cobros vencidos: 2 · 1.240,00 €» + «VER COBROS», "
        "«Pagos vencidos: 1 · 380,50 €» + «VER PAGOS», «Inspección de maquinaria vencida: 1» + «VER LA "
        "MÁQUINA». **Cada cifra se puede pulsar y lleva a su lista ya filtrada**: eso hay que verlo en el "
        "diseño (número grande, etiqueta pequeña y una flecha o un enlace claro). (2) **Resumen de la "
        "campaña**: superficie gestionada y cultivada, área trabajada, facturado registrado, cobrado y "
        "pendiente, y **cuántos registros tienen datos sin completar**. Aquí van las advertencias: si no "
        "están todos los importes, la tarjeta tiene que decir **«con los importes registrados»**, nunca "
        "«beneficio». Cada tarjeta dice **su fecha de corte** y a qué campaña se refiere. (3) **Agenda**: los "
        "próximos trabajos previstos, con fecha, tierra o cliente, tipo y estado, y una lista corta de "
        "«documentos por revisar» con su tipo. Abajo, una franja con las acciones documentales del año. Y en "
        "una esquina, discreto, un aviso de que hay datos pendientes de completar, con enlace a la lista. NO "
        "pongas publicidad, consejos ni gráficos decorativos que parezcan datos."
    )
PANTALLAS_ESCRITORIO["crm_tierras"] = (
    COMUN_CRM
    + " Es **Tierras y mapa**: la pantalla donde se trabaja con las 64 tierras, y la más usada del "
        "despacho. Arriba, la navegación y la barra de siempre (con el módulo «Tierras y mapa» activo). "
        "Debajo, una **franja de filtros visibles** (no escondidos en un botón): un buscador («Buscar por "
        "nombre, referencia SIGPAC o municipio») y varios desplegables: cultivo, municipio, secano/regadío, "
        "titularidad, campaña, y dos casillas destacadas: «Solo las que no tienen cultivo declarado» y «Solo "
        "las que no tienen forma». **Cada filtro puesto se ve como una etiqueta que se puede quitar** (una "
        "«x» al lado), y hay un botón «QUITAR TODOS LOS FILTROS». A la derecha de la franja, «AÑADIR UNA "
        "TIERRA» y «EXPORTAR» (que dice si exporta lo seleccionado, lo filtrado o todo). Después, **la tabla y "
        "el mapa, juntos y sincronizados**: la tabla a la izquierda con las columnas «Nombre», «Municipio», "
        "«Área gestionada» (a la derecha, dos decimales y «ha»), «Cultivo actual», «Último trabajo», "
        "«Pendientes» (una etiqueta cuando le falta algo) y «Estado de la forma» («Con forma», «Sin forma»), "
        "más una casilla de selección por fila y las acciones a la derecha («Abrir», «Planificar trabajo», "
        "«Registrar trabajo»). El mapa ocupa la derecha: ortofoto de fondo, los polígonos de las tierras "
        "gestionadas encima, la tierra seleccionada resaltada, y **la misma selección que la tabla** (al tocar "
        "una fila se resalta su polígono, y al revés). Encima del mapa, un conmutador «Tabla / Mapa / Los "
        "dos» y las capas que se pueden encender (recintos oficiales, cultivo, trabajos, avisos, lluvia, "
        "satélite) con su leyenda, su fecha y su fuente. **Las tierras sin geometría no desaparecen**: en una "
        "lista aparte, debajo o al lado, con un aviso de que se pueden dibujar. Al pie de la tabla: «64 "
        "tierras · 187,42 ha gestionadas · mostrando 10 de 64» con los botones de página. NO dibujes ningún "
        "mapa inventado con datos que parezcan reales: el mapa puede ser un esquema de parcelas con la "
        "ortofoto indicada, y los polígonos claramente de ejemplo."
    )
PANTALLAS_ESCRITORIO["crm_ficha_tierra"] = (
    COMUN_CRM
    + " Es **la ficha de una tierra**: la pantalla de «esta tierra, entera», a la que se llega desde la "
        "tabla, desde el mapa, desde un trabajo, desde una factura o desde el cuaderno, y **siempre es la "
        "misma ficha**. Arriba, la navegación y la barra de siempre (con «Tierras y mapa» activo) y, debajo, "
        "una miga de pan que diga de dónde se viene («Tierras y mapa / El Prado») con una flecha de vuelta "
        "que **conserva los filtros** de la lista. Después, un **resumen fijo** (siempre visible al bajar): el "
        "nombre de la tierra, su municipio y referencia SIGPAC, **la campaña y el cultivo de este año**, la "
        "superficie (área gestionada y declarada, con su diferencia cuando no coinciden), el dibujo de su "
        "forma y el **próximo trabajo previsto**. A la derecha del resumen, las acciones principales: "
        "«REGISTRAR TRABAJO» (verde sólido), «PLANIFICAR», «EDITAR LA TIERRA» y «VER EN EL MAPA». Debajo, la "
        "ficha se organiza **en secciones con pestañas o con bloques apilados**, y cada sección tiene su "
        "título y su cuenta: «Historia» (la línea de tiempo de todo lo que se ha hecho: fecha, trabajo, "
        "superficie, máquina o persona, insumos y si está revisado), «Cultivos» (los tres últimos años y el "
        "actual, con especie, variedad y fechas), «Productos y abono» (lo echado y lo aportado, con el "
        "nutriente cuando se sepa), «Cosecha y cuentas» (lo cosechado, lo vendido y los costes conocidos, "
        "**diciendo cuánto queda sin asignar**), «Documentos» (los papeles vinculados con su tipo y fecha) y "
        "«PAC» (los compromisos y prácticas que afectan a esta tierra, con su estado). **Cada fila de la "
        "historia se puede abrir** (no es solo texto) y hay un botón «AÑADIR ALGO A ESTA TIERRA». Reglas de "
        "esta pantalla que hay que ver en el dibujo: **una labor no es un cultivo** (un rodillo no cambia «lo "
        "que hay sembrado»), **un trabajo previsto no es un trabajo hecho** (se distinguen), y lo que no se "
        "sabe se enseña como «sin dato» o «pendiente», nunca como cero ni como verde."
    )


def _clave() -> str:
    clave = (os.environ.get("STITCH_API_KEY") or "").strip()
    if not clave:
        # Salida para trabajar desde una sesión de agente sin variables de entorno: un fichero temporal
        # FUERA del repositorio. Sigue sin haber ninguna clave escrita en el proyecto.
        temporal = pathlib.Path(os.environ.get("TEMP", "/tmp"), "stitch_key.txt")
        if temporal.is_file():
            clave = temporal.read_text(encoding="utf-8-sig").strip()
    if not clave:
        print("Falta la clave de Stitch. Ponla en la variable STITCH_API_KEY (no la escribas en el")
        print("repositorio). Se saca de https://stitch.withgoogle.com con tu cuenta.")
        raise SystemExit(2)
    return clave


def _proyecto_id(valor: str) -> str:
    """El id del proyecto **sin** el prefijo `projects/`: Stitch lo pide así (si no, error)."""
    return valor.split("/")[-1]


def _llamar(metodo: str, argumentos: dict, espera: float = 600.0) -> dict:
    """Llama a una herramienta del servidor MCP de Stitch y devuelve su respuesta."""
    respuesta = httpx.post(
        URL,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": metodo, "arguments": argumentos},
        },
        headers={"X-Goog-Api-Key": _clave(), "Content-Type": "application/json"},
        timeout=espera,
    )
    datos = respuesta.json()
    resultado = datos.get("result", {})
    if resultado.get("isError"):
        texto = " ".join(bloque.get("text", "") for bloque in resultado.get("content", []))
        raise RuntimeError(f"Stitch ha contestado con un error: {texto[:300]}")
    # Las respuestas vienen como texto con un JSON dentro: se devuelve ya interpretado.
    trozos = [bloque.get("text", "") for bloque in resultado.get("content", [])]
    junto = "\n".join(trozos).strip()
    try:
        return json.loads(junto)
    except json.JSONDecodeError:
        return {"texto": junto}


def _guardar(nombre: str, datos: dict, destino: pathlib.Path | None = None) -> pathlib.Path:
    carpeta = destino or DESTINO
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre}.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def _bajar_capturas_en(carpeta: pathlib.Path, nombre: str, datos: dict) -> None:
    """Baja la captura (y el HTML) de las pantallas que vienen en una respuesta de generación."""
    for componente in datos.get("outputComponents", []):
        for pantalla in (componente.get("design") or {}).get("screens", []):
            captura = pantalla.get("screenshot") or {}
            if captura.get("downloadUrl"):
                carpeta.mkdir(parents=True, exist_ok=True)
                # `=s1600` pide la captura grande: la que trae Stitch es de 141 px de ancho y no se lee.
                for sufijo in ("", "_grande"):
                    url = captura["downloadUrl"] + ("" if sufijo == "" else "=s1600")
                    imagen = httpx.get(url, timeout=180, follow_redirects=True)
                    (carpeta / f"{nombre}{sufijo}.png").write_bytes(imagen.content)
                print(f"  captura: {carpeta.relative_to(RAIZ).as_posix()}/{nombre}.png")
            html = pantalla.get("htmlCode") or {}
            if html.get("downloadUrl"):
                codigo = httpx.get(html["downloadUrl"], timeout=180, follow_redirects=True)
                (carpeta / f"{nombre}.html").write_bytes(codigo.content)
        if componente.get("text"):
            carpeta.mkdir(parents=True, exist_ok=True)
            (carpeta / f"{nombre}_explicacion.md").write_text(componente["text"], encoding="utf-8")


def _bajar_capturas(nombre: str, datos: dict) -> None:
    _bajar_capturas_en(DESTINO / "rediseno", nombre, datos)


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--listar", action="store_true", help="enseña los proyectos que hay")
    analizador.add_argument("--proyecto", metavar="TITULO", help="crea un proyecto nuevo")
    analizador.add_argument("--diseno", metavar="ID", help="sube DESIGN.md a ese proyecto")
    analizador.add_argument(
        "--sistema", metavar="ID", help="crea el sistema de diseño a partir del DESIGN.md subido"
    )
    analizador.add_argument(
        "--pantalla", metavar="CLAVE", choices=sorted(PANTALLAS), help="genera una pantalla"
    )
    analizador.add_argument("--todas", metavar="ID", help="genera todas las pantallas de ese proyecto")
    analizador.add_argument(
        "--nuevas",
        metavar="ID",
        help=(
            "genera solo las pantallas que **todavía no tienen diseño pedido** (las que no tienen su "
            "`docs/stitch/pantalla_<clave>.json`), que es lo que hace falta para ir cubriendo la "
            "aplicación entera sin volver a pedir lo que ya está"
        ),
    )
    analizador.add_argument(
        "--escritorio",
        metavar="ID",
        help=(
            "genera los diseños de **la versión de escritorio** (aplicación de gestión, 1440x900) que "
            "todavía no se hayan pedido, en `docs/stitch/escritorio/`. Es una familia aparte de la de "
            "móvil: no se pisan"
        ),
    )
    argumentos = analizador.parse_args()

    if argumentos.listar:
        datos = _llamar("list_projects", {})
        for proyecto in datos.get("projects", []):
            print(f"  {proyecto.get('name')}  ·  {proyecto.get('title')}")
        return 0

    if argumentos.proyecto:
        datos = _llamar("create_project", {"title": argumentos.proyecto})
        print(f"Proyecto creado: {json.dumps(datos, ensure_ascii=False)[:300]}")
        _guardar("proyecto", datos)
        return 0

    if argumentos.diseno:
        # El contrato de diseño del proyecto, tal cual: así Stitch diseña con nuestros colores, tipos
        # y medidas, y no con los suyos.
        contenido = base64.b64encode(DISENO.read_bytes()).decode("ascii")
        datos = _llamar(
            "upload_design_md",
            {"projectId": _proyecto_id(argumentos.diseno), "designMdBase64": contenido},
        )
        print(f"Diseño subido: {json.dumps(datos, ensure_ascii=False)[:300]}")
        _guardar("diseno", datos)
        return 0

    if argumentos.sistema:
        subido = json.loads((DESTINO / "diseno.json").read_text(encoding="utf-8"))
        datos = _llamar(
            "create_design_system_from_design_md",
            {
                "projectId": _proyecto_id(argumentos.sistema),
                "deviceType": "MOBILE",
                "selectedScreenInstance": {
                    "id": subido["id"],
                    "sourceScreen": subido["sourceScreen"],
                },
            },
        )
        print(f"Sistema de diseño creado: {json.dumps(datos, ensure_ascii=False)[:300]}")
        _guardar("sistema_de_diseno", datos)
        return 0

    def generar(clave: str, proyecto: str) -> None:
        datos = _llamar(
            "generate_screen_from_text",
            {
                "projectId": _proyecto_id(proyecto),
                "prompt": PANTALLAS[clave],
                "deviceType": "MOBILE",
                "designSystem": SISTEMA_DE_DISENO,
            },
        )
        _guardar(f"pantalla_{clave}", datos)
        print(f"Pantalla «{clave}»: {json.dumps(datos, ensure_ascii=False)[:200]}")
        _bajar_capturas(clave, datos)

    if argumentos.pantalla and argumentos.todas:
        generar(argumentos.pantalla, argumentos.todas)
        return 0

    if argumentos.todas:
        for clave in sorted(PANTALLAS):
            print(f"--- {clave} ---")
            try:
                generar(clave, argumentos.todas)
            except Exception as problema:  # noqa: BLE001 - una pantalla que falla no para el resto
                print(f"  {problema}")
        return 0

    if argumentos.escritorio:
        # **`deviceType: "DESKTOP"`**, que es lo que hace que Stitch diseñe una pantalla ancha de ordenador
        # y no un móvil. La primera vez que se pidió esto se probó con `MOBILE` y las capturas salían como
        # un móvil estirado: no vale.
        def generar_escritorio(clave: str, proyecto: str) -> None:
            datos = _llamar(
                "generate_screen_from_text",
                {
                    "projectId": _proyecto_id(proyecto),
                    "prompt": PANTALLAS_ESCRITORIO[clave],
                    "deviceType": "DESKTOP",
                    "designSystem": SISTEMA_DE_DISENO,
                },
            )
            _guardar(f"pantalla_{clave}", datos, destino=CARPETA_ESCRITORIO)
            print(f"Pantalla de escritorio «{clave}»: {json.dumps(datos, ensure_ascii=False)[:200]}")
            _bajar_capturas_en(CARPETA_ESCRITORIO, clave, datos)

        pendientes = [
            clave
            for clave in sorted(PANTALLAS_ESCRITORIO)
            if not (CARPETA_ESCRITORIO / f"pantalla_{clave}.json").is_file()
        ]
        print(f"Pantallas de escritorio sin diseño pedido: {len(pendientes)} de {len(PANTALLAS_ESCRITORIO)}")
        for clave in pendientes:
            print(f"--- {clave} ---")
            # Una pantalla que falle no puede llevarse por delante a las demás (misma lección que arriba):
            # el fichero de la respuesta es lo que marca lo que ya está pedido, así que volver a lanzarlo
            # retoma donde se quedó y no duplica nada.
            try:
                generar_escritorio(clave, argumentos.escritorio)
            except Exception as problema:  # noqa: BLE001
                print(f"  {problema}")
        return 0

    if argumentos.nuevas:
        # Solo lo que no tiene diseño pedido: el fichero de la respuesta es lo que dice que ya se pidió.
        pendientes = [
            clave for clave in sorted(PANTALLAS) if not (DESTINO / f"pantalla_{clave}.json").is_file()
        ]
        print(f"Pantallas sin diseño pedido: {len(pendientes)} de {len(PANTALLAS)}")
        for clave in pendientes:
            print(f"--- {clave} ---")
            # **`Exception` y no `RuntimeError`**, y aquí está el motivo: en la primera tanda de la ronda
            # 90, la pantalla «la ayuda» se cortó a mitad (un fallo de red contra el servidor de Stitch) y
            # el guion **se paró entero**, dejando veintiuna pantallas sin pedir. Una pantalla que falla
            # no puede llevarse por delante a las demás: se dice qué ha pasado y se sigue. El fichero de
            # la respuesta es lo que marca lo que ya está pedido, así que volver a lanzarlo retoma donde
            # se quedó y **no duplica** nada.
            try:
                generar(clave, argumentos.nuevas)
            except Exception as problema:  # noqa: BLE001
                print(f"  {problema}")
        return 0

    analizador.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
