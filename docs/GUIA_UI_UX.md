# Cómo tiene que ser la interfaz

> Alcance actualizado a 01/10/2026: esta guía conserva las prioridades del modo de
> campo. El despacho se concreta en [CONTRATO_IMPLEMENTACION_CRM.md](CONTRATO_IMPLEMENTACION_CRM.md),
> con navegación, tablas, mapas y fichas. No aplicar prohibiciones de menús móviles
> a todo el CRM. Mantener nombres oficiales cuando eviten confusión: ITEAF e ITV
> son inspecciones distintas, con una explicación sencilla junto a sus nombres.

**Para quien construye o modifica la pantalla de CUE Digital, sea persona o agente.**
Se lee junto con [`../DESIGN.md`](../DESIGN.md) —que dice **cómo se ve**— y con
[`UI_Y_AGENTES.md`](UI_Y_AGENTES.md) —que dice **qué herramientas se usan y cuáles no**.

Este documento dice **cómo se comporta**.

---

## 0. La única pregunta que decide

Todo lo de aquí sale de una escena. Antes de dar por bueno cualquier cambio, contéstala:

> **¿Puede un agricultor de 65 años, con el móvil en una mano, la otra sucia, el sol de
> frente y sin cobertura, apuntar lo que ha hecho en menos de un minuto sin llamar a
> nadie?**

Si la respuesta es no, el diseño está mal. No hay excepciones y no hay "ya, pero es más
bonito así".

**Quién es.** Lleva el cuaderno en papel desde 2013 y no ha usado nunca un programa de
gestión. Puede que no tenga correo en el móvil. **No es torpe**: es que nadie le ha
diseñado nada pensando en él. Desde el 1 de enero de 2027 el registro tiene que ser
electrónico, y si esto no se entiende, se queda fuera de la ley sin querer.

**Qué tiene que sentir.** Tranquilidad y franqueza. Que le habla alguien que sabe del
tema, como un vecino. Al terminar de apuntar algo, la sensación tiene que ser *"ya está"*,
no *"a ver si lo habré hecho bien"*.

---

## 1. Las ocho reglas

| # | Regla | Por qué | Quién la vigila |
|---|---|---|---|
| 1 | **Nunca se pide un dato que la app pueda deducir** | Si ya sabe la parcela, el cultivo o la máquina, preguntarlo es trabajo regalado | Revisión |
| 2 | **Nunca se enseña un término que no usaría en el bar** | Si no entiende la pregunta, la respuesta será mala o ninguna | `test_sin_jerga.py` |
| 3 | **Ningún aviso deja sin saber qué hacer** | Un bloqueo sin salida es un abandono | `test_los_mensajes_que_bloquean_dicen_que_hacer` |
| 4 | **Nunca se pierde trabajo** | Sin cobertura, con el móvil apagado o cerrando el navegador | `tests_js/nucleo.test.js` |
| 5 | **Siempre se puede deshacer** | Y nada se borra: se anula con un motivo | `test_registro_obligatorio.py` |
| 6 | **Siempre hay salida en papel** | Un botón que imprime, siempre disponible | `test_el_pdf_sale_aunque_falten_datos` |
| 7 | **Lo que no se sabe se queda en blanco y se pregunta** | Un dato inventado es una sanción; un hueco es una pregunta | `test_borradores.py` |
| 8 | **Si le dices que le falta algo, le das el botón que lo arregla** | Ya estuvo mal: decía "añade tu primera parcela" sin dejar hacerlo | `test_..._no_deja_al_agricultor_sin_salida` |

La 8 merece un párrafo. **Este error ya se cometió una vez.** La pantalla decía
*"Todavía no tienes parcelas. Añade la primera y ya podrás apuntar lo que haces"* y no
había **ninguna forma** de añadirla. Seis botones que no llevaban a ninguna parte. Antes
de escribir un aviso, pregunta: **¿y ahora qué hace?**

---

## 2. Cómo se habla

### 2.1. Traducción obligatoria

La app **jamás** muestra la columna izquierda.

| Lo que dice la ley | Lo que dice la app |
|---|---|
| Cuaderno de explotación | **Mi cuaderno** |
| Explotación | **Mi finca** |
| Titular | **Tú** |
| Campaña | **El año** |
| DGC / recinto SIGPAC | **Parcela** / **Trozo de parcela** |
| UHC | **Grupo de parcelas** |
| Tratamiento fitosanitario | **He echado producto** |
| Materia activa | **Lo que lleva dentro** |
| Nº de registro | **Número de la etiqueta** |
| Dosis | **Cuánto por hectárea** |
| Plazo de seguridad | **Días de espera antes de cogerlo** |
| Franja de seguridad | **Metros sin tratar junto al agua** |
| Fertilización | **Abonar** |
| Riqueza N-P-K | **Los tres números del saco** |
| Unidades fertilizantes | **Abono puro** |
| Plan de abonado | **Plan de abono del año** |
| Recomendación de nutrientes | **Qué abono necesita** |
| Postcosecha | **Tratar después de recoger** |
| Semilla tratada | **Semilla que ya venía tratada** |
| Cesta de la compra | **Los productos que he comprado** |
| Analíticas | **Análisis** |
| Material analizado | **Qué has mandado analizar** |
| Boletín de análisis / nº de informe | **El papel del laboratorio** |
| Producto vegetal | **Lo que has vendido** |
| Cosecha comercializada | **Lo que he vendido** |
| Venta directa | **Lo vendí yo al cliente** |
| Trazabilidad | *No se dice.* Se dice **«de dónde salió»** |
| Instalaciones | **Naves y almacenes** |
| Registro de maquinaria | **Mis máquinas** |
| ITEAF | **La ITV de la máquina** |
| ROMA | **El registro de la máquina** |
| ROPO / carné de aplicador | **El carné para echar producto** |
| Asesor GIP | **El técnico que te asesora** |
| Medidas preventivas / GIP | **Lo que hago sin echar producto** |
| Gestión integrada de plagas | *No se dice.* Se dice **«lo que hago sin echar producto»** |
| Material analizado | **Qué has mandado analizar** |
| Umbrales de tratamiento | **Mirar el campo antes de decidir** |
| Fauna auxiliar / infraestructuras ecológicas | **Setos y flores para los bichos que comen plagas** |
| Zona vulnerable a nitratos | **Zona con reglas de abono más estrictas** |
| Ecorrégimen | **Ayuda por hacerlo bien** |
| Otras prácticas culturales | **Otros trabajos del campo** |

La lista viva, con las palabras prohibidas, está en `backend/app/textos.py`. La tabla de
arriba es la referencia para redactar; **si añades un término nuevo, añádelo a los dos
sitios**.

### 2.2. Cómo se escribe un mensaje

Estructura fija: **qué pasa + qué hago ahora**. Siempre las dos partes.

| ❌ Mal | ✅ Bien |
|---|---|
| "Error de validación: dosis excede máximo permitido" | *"Has puesto más producto del que permite la etiqueta. Como mucho son 0,80 L/ha. Bájalo y ya está."* |
| "Campo obligatorio" | *"Falta esto: ¿Cómo llamas tú a esa tierra?"* |
| "No se pudo sincronizar" | *"No hay cobertura. No te preocupes: lo hemos guardado en el móvil y se manda solo."* |
| "Plazo de seguridad incumplido" | *"Todavía no puedes coger esta parcela. El producto que echaste el 01/05/2026 pide 21 días de espera: podrás cogerla a partir del 22/05/2026. Faltan 12 días."* |
| "Sesión expirada" | *"Te hemos desconectado por seguridad. Vuelve a entrar."* |

**Prohibido:** números de error, la palabra "error", tecnicismos, y cualquier mensaje que
no diga qué hacer.

### 2.3. Singular y plural

*"1 apuntes"* es lo primero que hace desconfiar de un programa: si esto está mal escrito,
¿qué más estará mal? Usa `textos.mensaje_con_cuenta("A6", cuantos)`, que elige entre
`A6_uno` y `A6_varios`.

### 2.4. Los números y las fechas

- Decimales con **coma**: `0,80 L/ha`. Nunca `0.80`.
- Millares con **punto**: `1.234 kg`.
- Fechas: `22/05/2026`. Nada de `2026-05-22` en pantalla.
- Se escriben con `legal.formatea_numero()` y `legal.formatea_fecha()`.

**Y ojo con lo que escribe el agricultor**: en un teclado español se teclea `0,8`. La
regla de lectura está en `nucleo.js` (`aNumero`) y tiene una ambigüedad documentada:
`0.8` son 0,8 pero `1.234` son mil doscientos treinta y cuatro. **No la "arregles" sin
leer el comentario**: un cambio ahí es un error de mil veces.

---

## 3. Los patrones de pantalla

### 3.1. La pantalla de inicio

**Seis botones grandes y nada más. El orden no se toca.**

```
        ¿Qué has hecho hoy?

  💧  HE ECHADO PRODUCTO          ← el grande, el 90 % de los usos
  🟤  HE ABONADO        🚜  HE HECHO UN TRABAJO
  📖  MI CUADERNO       🖨️  SACAR EN PAPEL
  ❓  NO SÉ QUÉ PULSAR

  🔁  LO MISMO QUE LA ÚLTIMA VEZ      ← atajos, en secundario
  🎤  DÍMELO CON LA VOZ
  📋  MIS PARCELAS, PRODUCTOS Y MÁQUINAS
```

- **El botón grande es "HE ECHADO PRODUCTO"**, porque es el 90 % de lo que se apunta.
- **Los atajos van debajo, en secundario.** Son atajos, no caminos: no compiten.
- **El botón "NO SÉ QUÉ PULSAR" no es un chiste.** Es la salida de emergencia de quien
  se ha perdido, y lleva a la ayuda en castellano.

**Excepción documentada:** si al agricultor le falta lo imprescindible (no tiene ninguna
parcela), la pantalla abre con un aviso y **un solo botón grande**: el que lo arregla. El
aviso manda, porque sin parcela los seis botones no llevan a nada.

### 3.2. El asistente: una pregunta por pantalla

Cada paso tiene **un** campo, un título que es **la pregunta** y una pista corta.

```
[▬▬▬▬░░░░]  ← los pasos, para saber que esto se acaba

¿Dónde?
Toca la parcela donde has trabajado

  📍 El Prado        2,43 ha · secano
  📍 El Prado Alto   1,10 ha · secano

  [ DEJARLO ]  [ SEGUIR ]
```

- **El paso opcional lleva "DEJARLO".** Y siempre se puede volver atrás.
- **Los pasos del asistente se ven arriba.** Es la duda que más desanima en un formulario
  largo: no saber cuánto queda.
- **Lo que ya se sabe viene puesto.** La fecha de hoy, la superficie de la parcela. El
  agricultor corrige mucho mejor de lo que rellena.

**Excepción documentada a "una pregunta por pantalla":** los campos **opcionales** de las
altas van todos juntos en el último paso, con un botón grande de DEJARLO debajo. El
motivo: la regla existe para no marear con decisiones obligatorias, y cinco pantallas
seguidas de datos que se pueden dejar en blanco marean más que una sola.

**Regla del clic:** en una pantalla con varios campos, elegir **no salta de pantalla**.
En una con uno solo, sí. Si tocas esto, `app.js` lo comprueba con
`paso.campos.length > 1`.

### 3.3. El estado vacío que no deja sin salida

**Nunca un aviso solo.** Siempre aviso **+ el botón que lo arregla**.

```js
if (estado.parcelas.length === 0) {
  return `
    <div class="aviso">${esc(aviso("no_hay_parcelas"))}</div>
    ${boton({ etiqueta: t("maestros.anadir_primera_parcela", ""), icono: "📍",
              accion: "anadir-maestro", datos: { tipo: "parcela" }, clase: "boton-principal" })}`;
}
```

### 3.4. La tarjeta de revisión (*Generative UI*)

**Cuando algo se entiende solo** —un dictado, y mañana una foto de etiqueta—, el
resultado **no es un texto**: es el formulario a medio rellenar.

```
Lo que he entendido
Mira si está bien. Completa lo que falte y apúntalo.

  ¿Dónde?                    El Prado
  ¿Cuándo?                   22/09/2026
  ¿Qué producto has echado?  Ejemplo 25 EC
  ¿Por qué lo has echado?    Vi la plaga o la hierba en el campo
  ¿Cuánto por hectárea?      2,00

Para poder apuntarlo me falta esto:
  · ¿Qué máquina?

  [ ESTÁ BIEN, APUNTARLO ]   [ CORREGIRLO A MANO ]
```

Tres reglas que no se negocian:

1. **Se enseña siempre lo que se ha entendido**, cada dato con la pregunta que le
   corresponde. El agricultor revisa y confirma; nunca se guarda a ciegas.
2. **Lo que no se ha entendido se pregunta**, no se rellena con algo parecido.
3. **Lo que se ha oído pero no se sabe dónde va, se enseña aparte** (`campo: null`), con
   un texto que lo explica: *"Esto lo he oído pero no sé dónde ponerlo. Dímelo tú."* El
   caso típico es *"dos litros"*, que puede ser la dosis o el total.

**El botón "APUNTARLO" no guarda: abre el asistente de siempre con los campos puestos.**
Así el agricultor sigue en el camino que ya conoce, y puede corregir cualquier cosa.

### 3.5. La confirmación y el deshacer

Después de guardar: **"Apuntado"**, un *"DESHACER"* a la vista, y **lo que eso significa
para él**:

> *"Fíjate: con lo que has echado hoy, en esta parcela no podrás coger la cosecha hasta
> el 22/05/2026."*

Ese dato no es decorativo: es la razón por la que existe el cuaderno.

### 3.6. La lista

Elemento de lista: **lo importante arriba a la izquierda, el detalle debajo**.

```
01/05/2026                    Ejemplo 25 EC
Trigo blando · 2,43 ha · 0,80 L/ha
Hasta aquí no puedes coger la cosecha: 22/05/2026
```

### 3.7. La ayuda de cada campo

Va **debajo del campo**, sin tener que pulsar nada, y siempre en el mismo orden:

> **Días de espera**
> **Qué es:** los días que tienen que pasar desde que echas el producto hasta que puedes
> recoger la cosecha.
> **Por qué te lo piden:** para que lo que vendes no lleve restos de producto.
> **Ejemplo:** si pone 21 días y echas el 1 de mayo, no puedes coger hasta el 22 de mayo.
> **Si te falta:** no se puede calcular a partir de qué día puedes cosechar.

Se sirve desde `textos.AYUDA` y se pinta con `ayudaDeCampo("clave")`. Si añades un campo
que pide un dato que el agricultor no tiene por qué saber, **dale su ayuda**.

### 3.8. Los boletines y los papeles que trae el agricultor

Un boletín de laboratorio, una etiqueta, un albarán: cosas que **vienen de fuera** y que el
agricultor no ha decidido. Se pintan así:

1. **Los números, con su nombre y su unidad, uno por línea.** Nunca una tabla con veinte
   columnas casi vacías: un boletín de tierra trae nueve números y uno de agua trae tres.
   Los números se piden al servidor (`parametros_analitica`), no se escriben en la interfaz.
2. **Si algo no viene en el papel, no se pide.** Un boletín que no trae el fósforo no trae un
   cero: no lo trae. Un campo vacío se queda vacío y no se apunta como cero.
3. **El papel entero se puede subir en PDF o en foto**, y se dice que se puede hacer una
   foto con el móvil. Es la forma de que el original quede guardado sin copiar nada a mano.
4. **Se dice de dónde sale cada lista de números** cuando no la fija ninguna norma. El
   agricultor tiene derecho a saber qué está rellenando por obligación y qué no.

```
Análisis de La tierra de El Prado
De dónde salió        El Prado
Muestra cogida el     14/02/2026
Laboratorio           Laboratorio Agrario de Villamuriel
Nº de boletín         2026/0417

Materia orgánica      1,80 %
pH                    7,40
Fósforo asimilable    18,00 ppm
```

### 3.9. El cuestionario: cuando el agricultor ya sabe la respuesta

El asistente pregunta **una cosa por pantalla** porque va descubriendo lo que ha pasado. Pero
hay tres secciones del cuaderno en las que no se descubre nada: son un cuestionario del que
el agricultor ya sabe la respuesta. Las medidas preventivas de la finca son el caso claro.

Ahí la regla se invierte a propósito: **las preguntas van todas juntas en una pantalla**.

```
Marca lo que hagas en tu finca

✅ ¿Cambias de cultivo de un año a otro?
   Lo que quieras añadir:  Trigo-cebada
⬜ ¿Usas variedades que aguantan mejor las plagas?
✅ ¿Limpias la máquina al pasar de una parcela a otra?

        [ GUARDAR ]  [ No hago ninguna de estas cosas ]
```

Las cuatro reglas del cuestionario:

1. **Se enseña el estado de todas las preguntas**, no solo las contestadas. Si solo salieran
   las marcadas, no habría forma de marcar la primera.
2. **Siempre en el mismo orden**, o el agricultor creerá que le preguntan cosas distintas
   cada vez que entra.
3. **Siempre se puede no marcar nada**, con un botón que lo dice claro. Un cuestionario del
   que no se puede salir sin contestar es una trampa.
4. **Se contesta una vez y sirve para todo el año.** Si hay que volver a marcarlo en cada
   apunte, la sección no sirve para nada: lo que se marca se queda para el siguiente.

### 3.10. Cuando el dato tiene que cuadrar con otro

Hay tres sitios donde un apunte solo no dice nada porque **solo tiene sentido comparado con
otro**, y los tres se cuentan igual:

| Lo que se apunta | Con qué se compara |
|---|---|
| Un abono | Con el plan de abono del año |
| Lo que se vende | Con lo que se apuntó que se cogió |
| Un tratamiento | Con las medidas preventivas de la finca |

La forma es siempre la misma, y se ha repetido tres veces porque funciona:

1. **Se apunta primero y se compara después.** Nunca se impide apuntar por no tener la otra
   mitad: el agricultor puede apuntar hoy y rellenar lo otro mañana.
2. **La frase dice los dos números, no solo que algo va mal.**
   > *"Llevas vendidos 42.000 kg de los 45.000 kg que apuntaste que cogiste."*
   > *"Con este abono te pasas de lo que tenías en el plan: el plan dice 100 kg de nitrógeno
   > por hectárea y así llevarías 120,5."*
3. **El aviso explica la causa más probable, que casi nunca es la que parece.**
   > *"Mira a ver si te falta apuntar alguna cosecha."*
4. **Nunca bloquea.** Casi siempre el error es un apunte que falta, no una mentira. Y el
   agricultor puede tener razón: puede estar vendiendo de la cosecha del año pasado.
5. **Si cuadra, se dice.** *"Llevas vendidos 42.000 kg de los 45.000 kg que apuntaste que
   cogiste"* es la frase que hace que alguien siga usando el programa: le confirma que lo
   tiene bien.

### 3.11. Los avisos que ayudan y no agobian
**Sí:** *"Faltan 3 días para poder coger 'El Prado'."* · *"La ITV del pulverizador caduca
en 20 días."* · *"Llevas dos meses sin apuntar nada. ¿Todo bien?"*

**No:** un aviso por cada campo vacío al abrir · contadores rojos que no se pueden
resolver · cualquier aviso que no se quite con un toque.

**Regla:** un aviso al día como máximo en la pantalla principal. El resto, dentro.

### 3.12. Cuando el programa no ha podido comprobar algo

Este patrón salió al comprobar la firma del cuaderno, y vale para todo lo que el programa no
sabe leer: una firma de curva elíptica, un boletín escaneado torcido, un fichero que no se
entiende.

**Las tres respuestas no son dos, y confundirlas es el error grave:**

| Lo que ha pasado | Qué se le dice | Qué se hace con el dato |
|---|---|---|
| **Está bien** | *"La firma está comprobada: es de este cuaderno y tuya."* | Se guarda, marcado |
| **Está mal** | *"Ese fichero de firma no es de este cuaderno. Vuelve a firmarlo."* | **Se rechaza** |
| **No se ha podido comprobar** | *"No se ha podido comprobar la firma, pero se ha guardado igual. No es culpa tuya: tu certificado es de los que este programa todavía no sabe leer."* | **Se guarda**, y se dice |

**Sí:**
- Decir **«no es culpa tuya»** y **qué se ha hecho** («se ha guardado igual»). El agricultor
  tiene que saber si su trabajo está a salvo o no.
- Dar el motivo **en sus palabras**: «tu certificado es de los que este programa todavía no sabe
  leer». Nunca «SHA-256», «curva elíptica», «CMS» ni «criptográfico»: no puede hacer nada con
  eso. La explicación técnica se guarda aparte, para quien mantiene el programa.
- Dar una salida cuando la hay: *"Vuelve a firmarlo"*, *"prueba a hacer la foto otra vez con más
  luz"*.

**No:**
- **Decir «no vale» de algo que no se ha podido comprobar.** Es acusar a alguien de algo que no
  ha hecho, y aquí se trata de un agricultor y su cuaderno.
- **Callarlo.** Si el programa no ha mirado algo, quien lo mire después tiene que saberlo.
- Enseñar el error técnico y esperar que el agricultor lo interprete.

**Regla:** *«no lo sé» no es «no»* y *«no lo sé» no es «sí»*. Las tres se dicen distinto.

---

## 4. Accesibilidad y dispositivo

| Qué | Cómo | Dónde |
|---|---|---|
| Letra base | **18 px**. Por debajo, a partir de los 50 años no se lee | `--letra` |
| Letra grande | Botón **A+** en la cabecera → 21 px y botones de 72 px | `body.letra-grande` |
| Ampliar con los dedos | Permitido. **`user-scalable=no` está prohibido** | `index.html` |
| Alto de lo que se toca | **64 px mínimo.** Un dedo con guante acierta eso | `--toque` |
| Separación entre botones | **8 px mínimo.** Pegados, tocar uno es tocar los dos | `.boton` |
| Contraste | **≥ 4,5:1.** Al sol se pierde la mitad del que mides en la oficina | `test_design_md.py` |
| El color no informa solo | Todo lo que dice el color lo dice también una palabra o icono | `.boton-elegido` |
| Los números | Teclado numérico del móvil: `inputmode="decimal"` | `app.js` |
| Peso de la página | Sin frameworks. Se abre con mala cobertura | — |

---

## 5. Sin cobertura

El campo no tiene cobertura. **Eso no es una excepción, es lo normal.**

- **Todo se guarda primero en el móvil**, siempre, aunque haya cobertura.
- Al recuperar la red **se manda solo**. El agricultor no hace nada.
- **Nunca aparece un error por no tener cobertura.** Como mucho, un aviso tranquilo:
  *"3 cosas apuntadas esperando a que haya cobertura. Se mandan solas."*
- Si el servidor rechaza algo que estaba en la cola, **se aparta y se avisa**. Perder un
  apunte del agricultor en silencio es lo único imperdonable.
- La aplicación se abre sin cobertura (service worker), **pero los datos del agricultor
  nunca se guardan en la caché del navegador**.

---

## 6. Errores de diseño prohibidos

1. Formularios largos con todos los campos a la vez. **Un paso, una pregunta.**
2. Preguntar algo que la app ya sabe.
3. Obligar a elegir de una lista de 500 productos. **Se busca por nombre o por foto.**
4. Esconder la salida en papel detrás de tres menús.
5. Bloquear un apunte por un campo opcional.
6. Mensajes de error técnicos, o un aviso sin el botón que lo arregla.
7. Perder lo escrito al cerrar la pantalla.
8. Pedir la contraseña cada vez.
9. Avisos que no se pueden quitar.
10. Cambiar de sitio los botones entre versiones. **Lo que funciona, no se mueve.**
11. Depender de `hover` o de un clic preciso. En un móvil no hay ratón.
12. Poner un dato que no tienes. **Un hueco es una pregunta; un invento es una sanción.**

---

## 7. Antes de dar una pantalla por buena

- [ ] ¿Se entiende sin saber informática? **Léela en voz alta.** Si suena a
      administración, reescríbela.
- [ ] ¿Hay algún término de la tabla de §2.1 sin traducir?
- [ ] ¿Cada aviso dice qué hacer ahora?
- [ ] ¿Cada estado vacío tiene su botón para salir de él?
- [ ] ¿Cada campo que pide un dato no obvio tiene su ayuda al lado?
- [ ] ¿Todo lo que se toca mide 64 px o más y está separado?
- [ ] ¿Se puede hacer todo con una mano y sin cobertura?
- [ ] ¿Se puede deshacer?
- [ ] ¿Los textos están en `textos.py`, y no escritos en `app.js` o en el HTML?
- [ ] Los tests: `pytest`, `node --test`, y uno nuevo que **pulse el botón** y compruebe
      que llega a donde tiene que llegar.

---

## 8. Lo que de verdad hace falta para saber si esto está bien

**Ninguna de las comprobaciones de arriba sustituye a probarlo con gente.**

Está pendiente y es lo más importante que queda. El plan, del apartado 5.18 del documento
del MVP: **tres agricultores reales**, uno de ellos de más de 60 años y con poca soltura
con el móvil. Sin ayudarles:

| # | Tarea | Éxito | Objetivo |
|---|---|---|---|
| T1 | Apuntar un tratamiento nuevo | Solo, sin ayuda | < 3 min |
| T2 | Apuntar el mismo tratamiento otra vez | Solo, sin ayuda | **< 30 s** |
| T3 | Sacar el cuaderno en papel | Solo | < 1 min |
| T4 | Averiguar cuándo puede cosechar una parcela | Solo y **entiende la respuesta** | < 30 s |
| T5 | Apuntar algo **sin cobertura** | Termina y no se pierde | < 3 min |
| T6 | Leer un mensaje de bloqueo y saber qué hacer | **Lo explica con sus palabras** | — |

**Aprobado:** T2 y T5 sin ninguna ayuda, y en T6 los tres dicen con sus palabras qué
tienen que hacer. **Si algo falla, se cambia el diseño, no se culpa al agricultor.**

**Métrica de uso, para después:** si un agricultor hace **menos de 4 registros al mes**,
la aplicación ha fallado.
