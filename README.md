# CUE Digital — el cuaderno de campo

> **Integración IUWS, 23/09/2026:** ya están localizados el descriptor oficial CUE
> v3.11.4 y su esquema JSON, y se han corregido las rutas con `/api/`. El mapeo de los
> 18 bloques está inventariado; la exportación oficial sigue pendiente de catálogos,
> decisiones de mapeo y prueba autenticada. Véanse [la actualización comprobada](docs/ACTUALIZACION_IUWS_2026-09-22.md)
> y [las fuentes oficiales aún pendientes](docs/FUENTES_OFICIALES_PENDIENTES.md).

> **Nuevo alcance, 01/10/2026:** David ha pedido convertir el cuaderno en una aplicación de
> gestión integral de la explotación (tierras, trabajo, economía, maquinaria, contactos y
> preparación de la PAC). El estado comprobado, las funciones aún inexistentes y las entregas
> para otros agentes están en [el plan de CRM agrario](docs/PLAN_CRM_AGRARIO_2026.md).

Cuaderno de campo digital centrado en **lo que la ley obliga a registrar**:

| Obligación | Desde | Lo dice |
|---|---|---|
| Registro de **abonos** | 01/01/2026 | RD 1051/2022, art. 5 y disposición final única |
| **Plan de abonado** | 01/09/2026 | RD 1051/2022, art. 4.2 |
| Registro **electrónico** de productos aplicados | 01/01/2027 | RD 1311/2012, art. 16.1 + Reglamento (UE) 2023/564 |
| El registro de tratamientos **en papel deja de valer** | 31/12/2026 | RD 1311/2012, art. 16.1 (RD 1039/2025) |

**Y lo que la ley NO obliga**, que es lo que más se confunde y por eso está escrito en la pantalla:

- **Mandar el cuaderno a la Junta es voluntario.** Artículo 10.2 del Real Decreto 1054/2022:
  *«Los titulares de explotaciones agrarias decidirán de forma voluntaria poner a disposición de la
  administración, a través de los REA correspondientes, la información que hayan cumplimentado en el
  CUE.»* Lo obligatorio es **tener** el registro y poder enseñarlo; enviarlo, no.
- **Puedes usar un programa propio.** Artículo 10.3: *«podrá utilizar cualquier otro sistema
  informático de su elección, siempre que cumpla con los requisitos técnicos que se establezcan y con
  el contenido mínimo establecidos en el anexo II»*. Sin ese artículo este programa no sería un
  cuaderno válido.
- **El cuaderno electrónico obligatorio empieza después de 2027**, con el siguiente periodo de la
  PAC, y solo para las fincas de más de 30 ha de cultivo, más de 5 ha de regadío o invernaderos de
  más de 0,1 ha; para las demás es voluntario (RD 1054/2022, disposición final única, apartado 2).

Todo esto está comprobado artículo por artículo, con las comillas literales y los enlaces al BOE, en
[`docs/LO_QUE_OBLIGA_LA_LEY.md`](docs/LO_QUE_OBLIGA_LA_LEY.md) — y hay un test que compara las
fechas del programa con ese documento, para que no se queden viejas.

El programa está pensado para que lo use **un agricultor que no sabe de informática**.
Eso no es una intención: es una regla que se comprueba con tests que fallan si en
cualquier texto que se ve en pantalla aparece una palabra que un agricultor no diría
en voz alta.

---

## Arrancar

```bash
cd backend
python -m venv ../.venv
../.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source ../.venv/bin/activate && pip install -r requirements.txt  # Linux
../.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

- **La aplicación:** <http://127.0.0.1:8000>
- Documentación de la API: <http://127.0.0.1:8000/docs>
- Comprobación de vida: <http://127.0.0.1:8000/health>

Por defecto usa SQLite (`cuedigital.db`), así que **no hace falta levantar nada más**.
Para producción: `CUEDIGITAL_DATABASE_URL=postgresql+psycopg://...`, **y hay que instalar además el
driver**, que **no viene en `requirements.txt`** porque en local no hace falta:

```bash
pip install "psycopg[binary]"
```

Sin él, la aplicación no arranca con una dirección de PostgreSQL (dirá que no encuentra el módulo).
Y para comprobar que arranca de verdad contra PostgreSQL hay un guion que levanta un servidor
desechable y lo mide: `scripts/sonda_postgresql.py` (no toca `cuedigital.db`).

### Entrar con el certificado digital

El programa **no valida el certificado**: eso lo hace el servidor web que tiene delante.
Aquí solo se lee lo que el servidor web ya ha validado. Por eso hay que encenderlo a
mano, y **solo cuando haya un nginx delante**:

```bash
CUEDIGITAL_CONFIAR_EN_CABECERAS=1
CUEDIGITAL_SECRETO=<una clave larga>
```

En nginx:

```nginx
ssl_verify_client on;
proxy_set_header X-SSL-Client-Subject $ssl_client_s_dn;
proxy_set_header X-SSL-Client-Verify  $ssl_client_verify;
```

> **Por qué está apagado por defecto, y por qué esto importa.** Si el programa se creyera
> esas cabeceras sin más, cualquiera que llegara a él directamente podría mandar
> `X-SSL-Client-Subject: CN=lo que sea, SERIALNUMBER=70922320A` y entrar en la finca de
> otro agricultor. Es el fallo clásico de confiar en una cabecera que pone el cliente, y
> hay un test que comprueba que con esto apagado **no se entra**.

Con el certificado, el agricultor entra **sin teclear nada**: el NIF de su certificado
tiene que coincidir con el NIF de su finca. Si no coincide, se le dice cuál es el de su
finca y qué hacer. El correo y la clave **siguen funcionando siempre**: el certificado es
una comodidad, nunca la única puerta.

Los nombres de las cabeceras se pueden cambiar con `CUEDIGITAL_CABECERA_CERTIFICADO` y
`CUEDIGITAL_CABECERA_VERIFICACION`, porque cada servidor web las llama de una forma.

### Si se te olvida la clave

**Este programa no manda correos** (vive en el ordenador del agricultor, no hay ningún servicio de
correo detrás), así que un «he olvidado mi contraseña» con enlace por correo no existe. Si no hubiera
otra salida, el agricultor se quedaría **fuera de su propio cuaderno**, que es justo lo que no puede
pasar. La salida es cambiarla desde el propio ordenador donde está el programa:

```bash
cd backend
# Ver qué cuentas hay (correo y nombre; nunca la clave ni su huella)
../.venv/Scripts/python.exe scripts/cambiar_la_clave.py --listar

# Cambiar la clave (la pide por teclado, sin dejarla en el historial)
../.venv/Scripts/python.exe scripts/cambiar_la_clave.py --correo <el-correo-de-la-cuenta>
```

Guarda la clave con **la misma función que el programa** (`security.hash_clave`, PBKDF2), no puede
bajar de 8 caracteres (la misma regla que el alta) y **no toca nada más**: ni las parcelas, ni los
apuntes, ni el correo. Si el correo no existe o las dos claves tecleadas no coinciden, lo dice y **no
cambia nada**.

### Firmar el cuaderno

Un cuaderno sin firmar es un documento que cualquiera puede haber cambiado. Firmado,
queda claro **quién** lo hizo y que nadie lo ha tocado después. Eso es lo que mira una
inspección.

El agricultor firma con **AutoFirma**, el programa que ya usa para todo lo demás de la
administración. El servidor no firma nada: prepara el fichero, lo entrega, recibe la
firma y guarda de qué fichero era. **Para firmar hay que haber entrado con el
certificado**: es la única forma honesta de saber quién firma.

Tres pasos, en la pantalla **Mi cuaderno**:

1. **Descargar** el fichero del cuaderno (texto plano, se puede abrir y leer).
2. **Firmarlo** con AutoFirma. La orden es la del manual oficial:
   ```
   "AutoFirmaCommandLine" sign -i "cuaderno_2026.txt" -o "cuaderno_2026.txt.csig" -format cades -algorithm SHA256withRSA
   ```
3. **Subir** la firma.

Y lo que de verdad protege el cuaderno: **cada vez que se mira, se vuelve a calcular la
huella del fichero**. Si alguien apunta algo después de firmar, el programa lo dice bien
claro — *"este cuaderno se firmó, pero después se ha cambiado algo. Vuelve a firmarlo"*.
Una firma que ya no cuadra es peor que no tener firma, porque parece que el cuaderno
está respaldado y no lo está.

#### Y lo que llega firmado se comprueba

Desde la ronda 12, cuando el agricultor sube el fichero de firma **se abre y se mira**
(`app/cades.py`). Antes se guardaba sin abrirlo: se podía subir un fichero de texto, la firma de
otro documento o la firma de otro agricultor, y el programa lo guardaba igual.

Se comprueban tres cosas:

1. **Que el resumen que lleva dentro la firma sea el del cuaderno.** Es la que de verdad protege
   el cuaderno.
2. **Que la cuenta de la firma cuadre con el certificado.** Si cuadra, solo pudo firmarlo quien
   tiene la clave privada de ese certificado.
3. **De quién es ese certificado**: se lee su titular y se compara con el agricultor que ha
   entrado. **Una firma perfectamente buena de otro agricultor no vale.**

Y hay **tres finales posibles**, no dos, y la diferencia entre los dos últimos es la que importa:

| Final | Qué se hace | Por qué |
|---|---|---|
| **Se comprueba y es de este cuaderno y tuya** | Se guarda, marcada como comprobada | Es lo que se quiere |
| **No se ha podido comprobar** (por ejemplo, una firma de curva elíptica) | **Se guarda igual**, diciendo por qué | No comprobar algo no es motivo para dejar a un agricultor sin firmar su cuaderno. Decir «no vale» aquí sería llamar mentiroso a alguien por tener un certificado que el programa no sabe leer |
| **Se comprueba y NO es de este cuaderno, o es de otro** | **Se rechaza** | Aquí no hay duda: guardarlo sería dejar creer que el cuaderno está respaldado cuando no lo está |

> **Lo que sigue sin comprobarse, y se dice en voz alta:** la **cadena de confianza**. O sea, que
> el certificado lo haya emitido una autoridad de certificación de fiar. Eso necesita la lista de
> autoridades raíz, que hay que instalar y mantener, y no se puede deducir del fichero.
> `cadena_de_confianza_comprobada` está en `false` y se queda en `false`.
>
> En la práctica pesa poco: el agricultor **entra con su certificado** y lo valida el servidor
> web, así que la cadena ya se comprobó al entrar, con la lista de autoridades del sistema. Lo
> que faltaba es lo de arriba, y eso ya está.
>
> Y **sin añadir ninguna librería de criptografía**, a propósito: la cuenta de una firma RSA es
> una potencia modular, y `pow(base, exponente, modulo)` la hace Python de serie. Lo que sí hace
> falta es saber leer la estructura binaria, y eso es lo que hay escrito a mano en `cades.py`.

Los ficheros con los que se prueba esto (`backend/tests/fixtures/firma_cades/`) son firmas
**de verdad**, hechas con OpenSSL. Probar el lector contra ficheros hechos por él mismo no
probaría nada: sería comprobar que soy coherente conmigo mismo. Ahí está también el caso de la
firma de curva elíptica y el de la firma de otro agricultor.

> ⚠️ **Antes de la primera firma de un agricultor de verdad:** la forma canónica del
> fichero tiene que estar congelada. Añadir un campo o cambiar cómo se escriben los
> números **invalida todas las firmas anteriores**. Lleva un número de versión
> (`VERSION_CANONICA`) justo para eso.

---

## El plan de abono del año

En regadío, desde el **1 de enero de 2026** hay que tener el plan de abono del año. Aquí
se llama así, y no «recomendación de nutrientes», porque es como lo llama el agricultor.

El plan dice **qué se va a echar y cuánto**: las necesidades de N-P-K del cultivo, la
producción esperada y lo que ya le aportan la tierra y el agua.

Y lo que de verdad sirve de un plan **no es el plan**: es saber si se está cumpliendo.
La pantalla enseña, para cada nutriente, lo previsto, lo que llevas y lo que te queda:

```
Plan de Trigo blando
El Prado · 2,43 ha · kilos por hectárea

Ojo: llevas más de lo que tenías previsto. Míralo antes de seguir abonando.

              Tenías previsto · Llevas
  N           100,0 · 120,5 ⚠️
  P            40,0 · 0,0 · 40,0
  K            60,0 · 0,0 · 60,0
```

**El plan cuenta todo lo que se echa en su parcela, esté enlazado o no.** Esa decisión
importa: nadie va a acordarse de enlazar cada abono con el plan a mano, así que si solo
contaran los enlazados el aviso de pasarse no saltaría casi nunca y el plan sería un papel
guardado en un cajón. Los apuntes anulados no cuentan: lo que se anuló no se echó.

**Avisa, no bloquea.** El plan es una recomendación, no un límite legal. Los anexos III y V
del programa de actuación de la zona están disponibles para consulta, pero su aplicación
depende del cultivo, la zona y las excepciones. Bloquear por pasarse del *plan* sería
inventarse una norma.

**Un plan se puede corregir.** No es un apunte, es una previsión: si a mitad de campaña
cambia el tiempo o el precio del abono, el plan se ajusta. Lo que no se toca nunca son
los apuntes de abono, que esos sí son registro obligatorio.

**El plan puede apoyarse en un análisis.** Al hacerlo, después de elegir la parcela, se
ofrecen los análisis de tierra o de planta que tenga esa parcela. Si no tiene ninguno, se
dice y se sigue: el plan se puede hacer igual. Y si más adelante se anula el análisis, el
plan se queda sin apoyo en vez de seguir diciendo que se basa en algo que ya no vale.

**Las dos cosas que pide el anexo II y no se preguntaban** (se cerraron el 24/09/2026):

- **El cultivo que había el año anterior.** No se pregunta: se rellena solo con lo que el
  agricultor ya declaró en la campaña anterior, y sale escrito en la pantalla del plan
  («El año anterior había: Cebada»). Si no hay campaña anterior apuntada, no se enseña nada;
  nunca un dato inventado.
- **Si se usó un programa o una herramienta para hacer el plan.** Se pregunta con un **sí o un
  no**, que es exactamente lo que pide el anexo II (el campo `Herramienta` del bloque
  `PlanAbonado` es booleano, no una lista de programas: poner una lista de cuatro opciones
  habría sido inventarse el catálogo). Se puede dejar sin contestar.

---

## Los análisis de laboratorio

La app oficial los tiene en «Otras Actividades: Analíticas», y son el bloque 13 del
contenido mínimo del CUE. Aquí se llaman análisis, que es como se dice en el pueblo.

Hay dos motivos para que estén, y los dos importan:

1. **Guardar el papel.** El boletín del laboratorio se sube en PDF o en foto. Un boletín
   en un cajón no sirve para nada.
2. **Aprovecharlo.** Un análisis de suelo es el papel más reutilizable que tiene un
   agricultor: sus números valen para el plan de abono de este año y de los tres
   siguientes. Por eso los valores se guardan **por clave** y no como texto libre: si el
   agricultor escribe «fósforo» en un cuadro de texto, el programa no puede usar ese
   número para nada.

Cinco clases: **la tierra, el agua con la que riego, la planta, lo que he recogido y si
lleva restos** de lo que eché.

### Los números, y de dónde sale cada lista

Esto está separado a propósito, porque no es lo mismo:

| Clase | Parámetros | ¿De una norma? |
|---|---|---|
| **La tierra** | materia orgánica, arena, limo, arcilla, pH, fósforo asimilable, potasio asimilable, nitrógeno total y conductividad a 25 ºC | **Sí.** Son los nueve del bloque 13 del contenido mínimo del CUE (documento técnico SIEX v3.11) |
| El agua con la que riego | nitratos, conductividad, pH | **No.** Los que trae un boletín de agua |
| La planta | nitrógeno, fósforo, potasio, materia seca | **No** |
| Lo que he recogido | humedad, proteína, peso por hectolitro, gluten | **No** |
| Si lleva restos | residuo (mg/kg) y la sustancia que hayan encontrado | **No** |

Los tres últimos bloques van marcados en el catálogo con `oficial=False`, y la pantalla lo
dice: **de la tierra los parámetros los fija la administración; de lo demás, no.** El
listado oficial, cuando llegue, se carga como los demás catálogos. Escribir aquí una lista
inventada y presentarla como oficial sería justo lo que este proyecto no hace.

### Lo que no se inventa

- **Un parámetro que no esté en el catálogo se descarta**, no se guarda. Guardarlo daría un
  cuaderno con un número que después nadie sabe interpretar.
- **Un valor en blanco no se guarda como cero.** Un boletín que no trae el fósforo no trae
  un cero: no lo trae. Apuntar un cero sería apuntar un dato falso, y el plan de abono lo
  leería.
- **La unidad la pone el catálogo, no el navegador.** Es lo que hace comparables dos
  análisis de años distintos: si un año se guardara en ppm y otro en mg/kg, la comparación
  sería falsa sin que nadie se diera cuenta.
- **No se compara el nitrato del agua con ningún límite legal.** Se dice el número y que se
  cuente en los aportes del plan. Los anexos III y V de la Orden MAV/398/2022 son tablas
  de consulta; no fijan por sí solos un límite del nitrato del agua para esa parcela.

### El boletín, en disco y no en la base de datos

Un boletín con fotos son varios megas. Meterlo en una columna haría que la copia de
seguridad del agricultor dejara de poderse manejar, así que el fichero va al disco y en la
base de datos queda solo la referencia. Dos decisiones que conviene no deshacer:

- **El nombre del fichero que manda el navegador nunca se usa como ruta.** La ruta la pone
  el programa: carpeta por finca y nombre por identificador. Un nombre como
  `../../app/main.py` escribiría fuera de su carpeta, y hay un test que lo comprueba
  mirando el disco.
- **La carpeta está en el `.gitignore`.** Son papeles del agricultor, con su NIF y los datos
  de su finca. Se puede cambiar de sitio con `CUEDIGITAL_ADJUNTOS`.

### El informe

El «Informe Analíticas» de la app oficial está en *Utilidades > Ver listados*. Aquí sale en
dos sitios: en `GET /api/analiticas/informe`, y **dentro del cuaderno en papel y del CSV**,
con el nombre de cada número y su unidad:

```
INFORME DE ANÁLISIS
Muestra;Resultado;Qué se analizó;De dónde;Laboratorio;Nº boletín;Números del boletín
14/02/2026;28/02/2026;La tierra;El Prado;Laboratorio Agrario de Villamuriel;2026/0417;Materia orgánica: 1,80 % · pH: 7,40 · Fósforo asimilable: 18,00 ppm
```

---

## Lo que hago sin echar producto

La app oficial lo tiene en «Explotación: Medidas Preventivas», y es la parte no química de
la gestión integrada de plagas: *«El apartado Medidas Preventivas permite anotar las medidas
utilizadas en la explotación para la gestión integrada de plagas. Para cumplimentarlo:
marcar las medidas preventivas, y Guardar. Es posible marcar varias medidas.»*

El contenido mínimo del CUE las sitúa **a nivel de Explotación**, así que se declaran una vez
y valen para todo el año. Son diez, y cada una se lee como una pregunta y no como su nombre
oficial:

```
¿Cambias de cultivo de un año a otro?               →  Rotación de cultivos
¿Miras el campo antes de decidir echar algo?        →  Muestreo y umbrales de tratamiento
¿Limpias la máquina al pasar de una parcela a otra? →  Higiene y limpieza de equipos
```

### Son dos cosas distintas, y las dos hacen falta

Aquí está la decisión que importa de esta sección:

| | Qué dice | Dónde vive |
|---|---|---|
| **El registro de la finca** | «Esto es lo que hago **siempre**» | `medidas_preventivas` |
| **Cada tratamiento** | «Esto es lo que hice **esa vez** antes de decidir echar el producto» | `TratamientoFitosanitario.medidas` |

Y lo que las une: **al apuntar un tratamiento, lo declarado en la finca ya sale marcado**, y
el agricultor solo quita lo que esa vez no hiciera. Eso es lo que hace que la sección sirva
de algo en vez de ser un formulario que se rellena una vez y no se vuelve a mirar.

> **Un agujero que había, y ya no.** El campo `medidas` del tratamiento **existía en la base
> de datos desde el principio y la pantalla no lo preguntaba nunca**, así que siempre estaba
> vacío. La gestión integrada de plagas exige poder demostrar que se priorizó lo no químico
> antes de tratar, y eso no se podía cumplir de ninguna manera: no era un campo que faltara,
> era una pregunta que no se hacía.

### Lo que se avisa, y lo que no se bloquea

- **Declarar cero medidas se puede.** Hay fincas que de verdad no hacen ninguna de las diez,
  y bloquear ahí dejaría al agricultor sin poder cerrar su cuaderno por una pregunta que es
  suya. Se avisa y ya está.
- **Al apuntar un tratamiento sin haber declarado nada, se avisa** (y no se bloquea: puede
  apuntar hoy y declararlas mañana). El aviso dice dónde se arregla.
- **Una vez contestado no se vuelve a preguntar**, aunque la respuesta sea «ninguna». Lo que
  persigue el aviso es que la sección esté rellenada, no que la respuesta sea «sí».
- **En una nave o en el grano ya recogido no se pregunta**: tratar un almacén no tiene nada
  que ver con la gestión integrada del cultivo.

### Nada se borra

Desmarcar una medida **no la quita**: se queda con `aplicada=False`. Así, cuando alguien
pregunte «¿esto lo hacías en 2024?», la respuesta está en vez de haber desaparecido. Lo que
sí se descarta es un código que no esté en el catálogo, y se dice cuál (`descartadas`) sin
perder las demás.

### Los códigos son internos, y se dice

El catálogo oficial de medidas se publica «según catálogo» y **no trae los códigos** en la
documentación que tenemos. Los de aquí son internos y estables (están guardados en la base
de datos de cada agricultor, así que no se cambian nunca); **lo que se imprime y se entrega
es el nombre de cada medida**, y la pantalla lo dice en vez de callárselo.

---

## Lo que he vendido

La app oficial lo tiene en «Otras Actividades: Cosecha Comercializada», y el contenido mínimo
del CUE la llama «Cosecha comercializada y/o venta directa». Es la sección que cierra el
cuaderno por arriba: **no es lo que recoges, es lo que sale de la finca.**

> **Por qué se llama «venta» y no «cosecha comercializada».** La tabla, el modelo y la ruta se
> llaman venta. El motivo es que ya existe un `/api/cosecha` para «he cogido la cosecha», y dos
> cosas distintas llamadas «cosecha» en el mismo programa es una trampa para quien lo lea
> dentro de un año. Y «lo que he vendido» es, además, como lo dice el agricultor.

### Lo que pide la norma, y lo que añadimos

| Contenido mínimo del CUE | Aquí |
|---|---|
| 1. Fecha (intervalo de tiempo)* | `fecha` + `fecha_fin` |
| 2. Producto vegetal (según catálogo)* | `producto` + `variedad` |
| 3. Cantidad de producto vegetal (kg o ud)* | `cantidad` + `unidad` |

Y separa **dos clases de venta**, que es lo que distingue `tipo`:

```
Lo vendí a un comprador o a la cooperativa   →  comercializada
Lo vendí yo directamente al cliente          →  venta_directa
```

Lo que añadimos nosotros es todo opcional y por un motivo: el **lote**, el **comprador**, el
**nº de albarán** y las **parcelas de origen** son lo que hace falta para responder «¿de dónde
salió esta partida?» cuando pregunta un cliente. Sin eso, la trazabilidad se queda en la puerta.

> **No hay precio ni importe, y no es un olvido.** Lo que la norma pide de esta sección es qué,
> cuánto y cuándo. La facturación está en otra parte (Verifactu, factura electrónica), que
> todavía no toca, y meter un precio a medias sería empezar por el final. La pantalla lo dice.

### Lo que de verdad sirve: que el cuaderno cuadre

El apunte, solo, es un papel más. Lo que hace útil a esta sección es comparar **lo vendido con
lo cosechado**:

```
Llevas vendidos 42.000 kg de los 45.000 kg que apuntaste que cogiste.
```

Y si no cuadra:

```
Ojo: llevas vendidos 62.000 kg y apuntaste que cogiste 45.000 kg.
Mira a ver si te falta apuntar alguna cosecha.
```

**Avisa, y no bloquea.** Lo normal cuando alguien vende más de lo que ha apuntado es que se
haya olvidado de apuntar la cosecha, no que venda lo que no tiene. Y puede tener razón: puede
estar vendiendo de la cosecha del año pasado.

### Los kilos, las toneladas y las unidades

El grano se vende en kilos o en toneladas, y la fruta y la verdura en unidades. La conversión de
toneladas a kilos es una cuenta, pero **una unidad de lechugas no pesa lo que dice el número**,
así que no se convierte: se queda fuera del total de kilos.

Es mejor un total que significa algo que uno que mezcla peras con manzanas. Las ventas en
unidades siguen saliendo en el informe, una a una, y el informe dice que las hay.

---

## Las reglas de abono de la zona de nitratos

Hasta la ronda 11 la aplicación decía «en tu zona hay reglas más estrictas» y **no decía cuáles**.
El motivo era bueno —no inventarse una norma— pero el resultado no servía: un aviso que no dice
qué hay que hacer no ayuda a nadie.

Los números que hay ahora **no están inventados**: los recoge la propia Junta en la presentación
«Zonas Vulnerables a la contaminación por nitratos en Castilla y León» (Consejería de Medio
Ambiente, Vivienda y Ordenación del Territorio, abril de 2026), que es la que resume el programa de
actuación de la **Orden MAV/398/2022**. Cada regla lleva escrita su fuente.

| Regla | Número | Qué hace la aplicación |
|---|---|---|
| Nitrógeno en forma de estiércoles y purines | **170 kg N/ha al año** | Avisa con la cifra |
| Pendiente: solo abonos orgánicos sólidos | **más del 15 %** | Avisa con la cifra |
| No abonar en zona de máxima crecida | **ni a 5 m** | Avisa |
| Suelo no cultivado, riesgo de escorrentía, terreno forestal | — | Avisa |
| Aportes máximos por cultivo (Anexo III de la Orden) | 22 cultivos, secano y regadío | Avisa sin bloquear con zona, cultivo y sistema exactos; las excepciones requieren revisión |
| Períodos de prohibición por cultivo (Anexo V) | 6 grupos de cultivos | Tabla consultable; no comprueba automáticamente el caso |

Las dos tablas se extraen del [PDF oficial del BOCyL](https://bocyl.jcyl.es/boletines/2022/05/05/pdf/BOCYL-D-05052022-1.pdf) mediante `backend/scripts/bajar_nitratos_cyl.py`. El fichero derivado y su procedencia están en [`data/nitratos_cyl/LEEME.md`](data/nitratos_cyl/LEEME.md). El [listado municipal de IDECyL](data/zv_cyl_fuentes/LEEME.md) ayuda a identificar la zona; las notas, excepciones, cosecha esperada y dudas de delimitación exigen revisar el caso.

**Avisa, y no bloquea**, y el motivo importa: el cuaderno tiene que recoger **lo que de verdad ha
pasado**. Si el programa impidiera apuntar un abono porque se pasa, el cuaderno acabaría diciendo
que ese abono no se echó, que es peor que el error que se quiere evitar. Además nuestros datos
pueden estar incompletos: puede haber estiércol de una cuadrilla que no se apuntó.

**El aviso dice los dos números, no solo que algo va mal:**

```
Ojo: en zona de nitratos no se pueden echar más de 170 kilos de nitrógeno por hectárea al año en
forma de estiércol o purín, y así llevarías 200,0 (160,0 que tenías apuntados y 40,0 de este).
Se puede apuntar, pero míralo antes de echar más.
```

Y las dos reglas que **no** se pueden comprobar se dicen en la pantalla de ayuda, con su motivo:
*«Esto no lo tenemos y por eso no te avisamos de ello. No es un olvido: se dice para que lo sepas
y lo mires tú o tu técnico.»*

---

## Las parcelas vienen del SIGPAC

El SIGPAC es el catastro del campo: el registro oficial de los recintos. Hasta la ronda 10 el
agricultor tenía que escribir a mano la referencia, la superficie, la pendiente, el uso y el
dibujo de cada trozo —ocho datos por cuarenta parcelas—, y ahí es donde más gente abandona una
aplicación nueva.

Ahora se le da **la referencia del recinto** (la del papel del SIGPAC o la que dice el técnico) y
el resto viene solo:

```
La referencia del trozo:  37-22-0-0-501-427-1
                          ↓
Superficie oficial:  2,7923 ha      Pendiente: 4,7 %      Uso: TIERRAS ARABLES
Y el dibujo del trozo, que sirve para el mapa
```

**De dónde sale esto, y por qué no está inventado.** Los servicios del SIGPAC son **públicos y
sin autenticación**, y están documentados en el documento del FEGA «Publicación de nuevos
servicios SIGPAC de consulta y divulgación de datos del SIGC»:

| Servicio | Dirección |
|---|---|
| Consulta de un recinto | `https://sigpac-hubcloud.es/servicioconsultassigpac/query/recinfo/{prov}/{mun}/{agr}/{zona}/{pol}/{parc}/{rec}.json` |
| Listas de códigos oficiales | `https://sigpac-hubcloud.es/codigossigpac/cod_producto.json` |
| OGC API Features | `https://sigpac-hubcloud.es/ogcapi` |

La dirección y **el orden de los siete números** salen del ejemplo que da el propio documento. Y
lo que devuelve el servicio es **exactamente lo que guarda nuestra tabla de parcelas**: los siete
códigos, la superficie en hectáreas, la pendiente media, el uso SIGPAC y **el dibujo en WKT**,
que es el mismo formato que usamos nosotros.

Los datos oficiales están descargados en `data/sigpac/`, con su `LEEME.md` diciendo de dónde sale
cada fichero:

| Fichero | Qué trae |
|---|---|
| `cod_producto.json` | **933 productos** con su código oficial |
| `cod_uso_sigpac.json` | 34 usos del suelo (TA = tierras arables) |
| `cod_aprovechamiento.json`, `cod_incidencia.json`, `cod_region_2023.json` | Los demás listados |
| `recinto_de_ejemplo.json` | Un recinto **de verdad**, para que los tests no necesiten internet |
| `recintos_de_ejemplo.json` | **Todos los trozos de una parcela de verdad** (la del visor `37:70:0:0:503:51`), que es lo que prueba la búsqueda |
| `recinto_de_ejemplo_503_51.json` | El trozo concreto de esa misma parcela |

Se actualizan con `python scripts/bajar_sigpac.py`. Son datos del FEGA publicados bajo licencia
Creative Commons BY 4.0.

### Ya no hay que saberse ningún código

Lo de arriba seguía pidiendo **los siete números de memoria**, y eso no lo sabe nadie. Lo que el
agricultor tiene delante es una de estas tres cosas, y las tres valen:

| Lo que tiene | Cómo se escribe |
|---|---|
| El **visor del SIGPAC** | `37:70:0:0:503:51` — seis números, y el recinto en otra columna |
| El **papel del SIGPAC** | `37-70-0-0-503-51-1` — los siete, con el recinto |
| La **Sede del Catastro** | `37070A50300051000AQ` — la referencia catastral, que trae dentro el polígono y la parcela |

Y se puede hacer **como lo hacen las aplicaciones oficiales del FEGA** (SgaRex en Cantabria,
SgaCap en Galicia): *«Se presentan como posibles campos de búsqueda [Cód. Provincia], [Cód.
Municipio], [Agregado], [Zona], [Cód. Polígono] y [Cód. Parcela]. Son obligatorios […] [Cód.
Provincia], [Cód. Municipio], [Cód. Polígono] y [Cód. Parcela]»*, se pulsa **BUSCAR** y *«se
marcan las casillas de los recintos y se incorporan»*. Aquí es igual, con dos mejoras:

- **El pueblo se elige de la lista oficial**, no se teclean códigos. Son los **2.248 municipios de
  Castilla y León** del diccionario del INE (`data/municipios_cyl.csv`, con su procedencia y su
  huella en `data/municipios_ine_fuentes/`). Al elegirlo se rellenan solos el municipio, la
  provincia y el **código INE**, que es con el que se comprueba la zona de nitratos.
- **Se pueden traer varios trozos de una vez** (`POST /api/parcelas/desde-sigpac/varias`): se pega
  una lista de referencias y se dan de alta todas, diciendo cuáles han entrado y cuáles no y por
  qué. Cuarenta parcelas de una sentada, y si tres están mal copiadas, las otras treinta y siete
  se quedan dentro.

Lo que **no** se hace es adivinar: si a la referencia le falta el recinto, se dice y se manda a la
búsqueda (que es lo que el agricultor quiere hacer de todas formas); si la parcela no tiene ningún
trozo, se dice; y si el SIGPAC no contesta, se dice y se puede apuntar a mano.

### Y ahora, la tierra se elige tocándola en el mapa

Mucha gente no se sabe ni el polígono ni la parcela, pero **reconoce su tierra en una foto aérea de
un vistazo**. Para eso está el mapa, y detrás tiene servicios oficiales, no una caja negra:

| Qué se ve | De dónde sale |
|---|---|
| **La foto del campo** | Ortofoto del **IGN** (PNOA), por su servicio de mapas |
| **Los linderos de los recintos** | Servicio de mapas del **SIGPAC** (FEGA) |
| **Lo que se declaró como cultivo** | El mismo servicio del SIGPAC |

El agricultor mueve el mapa, **toca su trozo** y el programa le dice qué parcela es: referencia,
superficie, uso, pendiente, su pueblo, **su referencia catastral** y si esa tierra está en zona
vulnerable a nitratos. Lo confirma y queda apuntada. También puede **tocar directamente el trozo**
(atajo para quien apunta bien) y hay un botón de **ESTOY AQUÍ**, para quien esté de pie en medio del
campo: pone el mapa donde está y le dice qué parcela pisa.

**La cruz del centro no es un adorno.** Acertar con el dedo en un trozo pequeño, en un móvil y con
guantes, no se hace; mover el mapa y pulsar un botón grande, sí. Y lo que se pregunta es lo que
queda debajo de la cruz, así que el agricultor ve exactamente por dónde va.

Tres cosas que conviene saber de cómo está hecho:

1. **El navegador no habla con el IGN ni con el SIGPAC: le pide las imágenes a su propio
   programa** (`GET /api/mapa/imagen`). Así las direcciones oficiales están en un solo sitio, y si
   el servicio se cae el agricultor lee un mensaje en castellano en vez de ver una imagen rota.
2. **El mapa necesita conexión, y se dice.** Sin cobertura no se puede ver, pero se sigue pudiendo
   apuntar la parcela por su referencia o eligiendo el pueblo. El mapa es una ayuda, no un
   requisito.
3. **Cuando el punto cae en una linde, el SIGPAC devuelve el recinto que lo contiene, que puede ser
   el de al lado** (está comprobado con un punto de verdad y hay un test que lo deja escrito). Por
   eso la pantalla enseña **qué trozo ha encontrado y cuántas hectáreas tiene** antes de apuntarlo:
   un dedo al lado equivocado es otra parcela, y quien lo sabe es el agricultor.

Las direcciones exactas de los servicios, las once consultas del SIGPAC y lo que devuelve cada una
están en [`docs/SERVICIOS_DEL_SIGPAC.md`](docs/SERVICIOS_DEL_SIGPAC.md).

**Tres decisiones que conviene no deshacer:**

1. **Los códigos se guardan en el repositorio, no se piden en cada arranque.** Los recintos
   cambian cada campaña y los códigos casi nunca; y si el servicio del FEGA se cae un domingo, el
   agricultor tiene que poder seguir apuntando. Lo único que se le pide a la red es traer una
   parcela nueva.
2. **El municipio y la provincia del recinto se piden aparte, y ahora se eligen de una lista.** El
   SIGPAC público devuelve códigos numéricos, no nombres, así que los nombres los pone el
   agricultor —eligiéndolos de la lista oficial del INE— y con ellos se calcula la zona de
   nitratos. **El código de municipio del SIGPAC es el mismo del INE**, y eso ya no es una
   suposición: la parcela del visor `37:70:0:0:503:51` es Calvarrasa de Arriba (INE **37070**,
   municipio **070**), su referencia catastral empieza por `37070`, y los 387 municipios del
   listado de IDECyL están todos en el diccionario del INE con el mismo código (lo comprueba
   `tests/test_parcelas_por_codigos.py`). Lo que sigue sin comprobarse es que exista un listado
   **de municipios del SIGPAC**: por eso la lista que se le enseña al agricultor es la del INE,
   que está completa. Si un código no valiera para el SIGPAC, la búsqueda no devolvería trozos
   (no devolvería trozos equivocados), que es el fallo seguro. La misma regla se aplica a las
   parcelas apuntadas a mano: se pueden indicar municipio y provincia, pero **nunca se toman de la
   explotación**.
3. **Sin cobertura se dice, y se apunta a mano.** El conector es un atajo, no un requisito.

**Y lo que de verdad desbloqueó esto**: el **catálogo oficial de productos**. El volcado a la
Junta pide «producto vegetal **según catálogo**», y hasta ahora ese campo salía vacío porque no
teníamos los códigos. Ahora «trigo blando» se manda como el **código 1**, que es lo que publica el
FEGA. Y lo que no está en la lista sigue saliendo vacío: un código mal puesto no da error al
mandarlo, guarda el producto equivocado.

---

## Traer las tierras del cuaderno de la Junta

En Castilla y León, quien lleva su cuaderno en la aplicación de la Junta (el **Cuecyl**) ya tiene
ahí escritas todas sus parcelas: las que declaró en la Solicitud Única, con su polígono, su
parcela, su recinto, su uso, su cultivo, su ecorregimen y sus hectáreas. En un cuaderno de verdad
—los tres que se han mirado son de las campañas 2024, 2025 y 2026— eso son **decenas de líneas**:
el de 2026 tiene 54 líneas y 51 tierras distintas.

Pedirle que las teclee otra vez sería una tontería y, peor, una fuente de errores: un número
cambiado y la tierra deja de ser la suya. Así que hay un botón, **TRAER MIS TIERRAS**, en la
pantalla de añadir una parcela: se sube el fichero que se descarga de la Junta y el programa apunta
las tierras.

**Va en dos pasos, y eso es lo importante.** Primero **se lee y se enseña** («tu cuaderno trae 54
líneas, 51 tierras, 128,28 hectáreas, 7 pueblos, 2 tierras en zona de nitratos») y solo después se
apunta. Dar de alta 51 parcelas sin avisar no es una función, es una sorpresa. Y el segundo paso se
puede repetir las veces que haga falta: **la misma tierra no se apunta dos veces**.

Las decisiones que hay detrás, contadas enteras en [`docs/CUADERNO_DE_LA_JUNTA.md`](docs/CUADERNO_DE_LA_JUNTA.md):

- **Una tierra que el papel parte en trozos se apunta en trozos.** El cuaderno escribe una línea
  por cultivo y superficie declarada: el recinto 1 de la parcela 24 del polígono 507 sale tres
  veces (barbecho 4,44 ha, avena 0,46 ha y 0,13 ha). Si se juntara en una parcela de 5,07 ha, el
  programa dejaría echar producto para 5 hectáreas de avena cuando hay 0,13.
- **La superficie que se cultiva manda para las dosis; la del recinto se guarda aparte.** La hoja
  2.1 del cuaderno pide las dos por separado y no son lo mismo.
- **Una casilla en blanco se queda en blanco.** «Parcela ubicada en zona nitratos» está marcada con
  «Sí» en las que lo están y en blanco en las demás: en blanco es «no lo han declarado», **no** «no
  está».
- **El nombre y el NIF no se copian del cuaderno**: el NIF es lo que se compara con el certificado
  digital al entrar, y la Junta lo escribe con el formato de su registro («0-70922320-A», con un
  cero delante que un DNI no lleva).

**Y el cuaderno se saca relleno.** Desde «mi cuaderno» hay un botón que descarga el libro con las
**25 hojas de la Junta**, sus cabeceras y sus columnas, con lo que el agricultor tiene apuntado: sus
tierras, sus tratamientos, sus abonos (con el nº de albarán y el tipo de abonado), sus análisis, lo
que ha vendido, sus labores, su plan de abonado y sus papeles. Lo que no está puesto **sale en
blanco**, nunca con un cero.

Y con él, **la lista de lo que falta**: cada dato que pide el cuaderno y no está apuntado, con
**dónde se apunta** («las máquinas con las que echas el producto, con su nº de ROMA → Mis cosas →
máquinas de echar producto»). Esa lista no está escrita a mano: sale de comparar las 25 hojas
oficiales con lo que él tiene. **Es la respuesta a «¿qué datos me piden?».**

Lo que más vale de esto es cómo se prueba: el fichero que escribe el programa **se vuelve a leer con
el mismo lector que lee los cuadernos de la Junta**, y el test comprueba que saca las mismas tierras
con la misma referencia. Si no se pudiera leer, es que no sería el cuaderno.

---

## Las facturas: hacerle una foto y que el programa la lea

El cuaderno de la Junta pide la **«empresa suministradora»** y el **«nº de factura»** en su hoja de
fertilización, el **«nº de albarán»** en la del abonado, y guardar «las facturas u otros documentos
que justifiquen la adquisición» **durante tres años**. O sea: la factura no es para llevar las
cuentas de casa, es un dato que el cuaderno pide.

Así que el agricultor **hace una foto al papel** (o sube el PDF que le manda el proveedor) y el
programa **lee lo que pone**: el proveedor, su NIF, el número, la fecha, la base, el IVA, el total y
cada línea con su producto, su cantidad y su precio. Y después **se lo enseña para que lo confirme**,
que es lo que hace que esto se pueda usar con una foto hecha con el móvil:

```
Esto es lo que he leído
Leída de: Una foto (repasa las palabras con tilde)

Mira esto antes de guardar
  En 1 línea(s) la cuenta de cantidad × precio no da el importe. Míralas antes de guardar.

¿Quién te lo ha vendido?   [ COOPERATIVA AGRICOLA DE PEÑARANDA S.C.L. ]
Su NIF [ F37012345 ]   ¿Qué número tiene la factura? [ 2026/00123 ]
Base imponible [ 620,00 ]   Cuota de IVA [ 130,20 ]   Total [ 750,20 ]

Lo que has comprado
  GLIFOSATO 36% SL 20 L    2 ud    85,00   170,00   ¿Es uno de tus productos? [ Glifosato 36 SL ]
  NITRATO AMONICO 33,5%    1000 kg  0,45   450,00   ¿Es uno de tus productos? [ No es de la cesta ]

              [ SÍ, GUARDAR ESTA FACTURA ]      [ VOLVER ]
```

Lo que hace que esto sea de fiar **no es el lector de letras: son las cuentas**. En cada línea,
cantidad × precio tiene que dar el importe; la suma de las líneas tiene que dar la base; base + IVA
tiene que dar el total. Cuando algo no cuadra, se dice en la pantalla. Y el NIF del agricultor ya se
sabe, así que el proveedor es *el otro* NIF de la factura.

Con lo que se guarda:

- **Lo comprado de cada producto**, en «lo que tengo en el almacén», con la factura de la que sale
  cada compra.
- **El cuadre**: comprado contra echado, y **sin restar cuando las unidades no se pueden comparar**
  (comprado en botes, echado en litros: se dice por qué en vez de inventarse un número).
- **El producto, si no lo tenía apuntado**: la línea ofrece crearlo con los datos de la factura. Lo
  que no se inventa es la dosis máxima ni el plazo de seguridad, que están en la etiqueta del bote.
- **El justificante**: el PDF o la foto se guardan y se pueden volver a ver.

Se lee el PDF del proveedor (con su texto dentro, perfecto), un PDF escaneado, una foto o un texto
pegado. Para las fotos hace falta un lector de letras (Tesseract): si no está instalado, **se dice y
no se inventa nada** —la factura se guarda como justificante y los datos se escriben a mano—. El
idioma español del lector se trae con `scripts/bajar_idioma_ocr.py` a `data/ocr/` y se usa **sin
tocar la instalación del ordenador**. Todo el detalle está en [`docs/FACTURAS.md`](docs/FACTURAS.md).

---

## Los sitios oficiales, y dónde se apunta cada cosa

La aplicación contesta dentro de sí misma a «¿qué es el registro electrónico y dónde apunto?»
(pantalla **mi cuaderno**): el registro electrónico es lo mismo que el cuaderno de papel, pero
guardado en un programa; se puede llevar **con esta aplicación o con la de la Junta** (art. 10.3 del
RD 1054/2022); el papel vale **hasta el 31/12/2026** y desde el **1/1/2027** tiene que ser
electrónico; y **mandarlo a la Junta es voluntario** (art. 10.2).

Y cuando hay que traer un dato de fuera, el enlace va ahí mismo, no en un papel aparte:

| Para qué | Dónde |
|---|---|
| Descargar tu cuaderno de la Junta (Cuecyl) | <https://particulares.ayg.jcyl.es> |
| Actualizar tus parcelas y cultivos (Reacyl) | <https://agriculturaganaderia.jcyl.es/web/es/registro-explotaciones-agrarias-castilla.html> |
| La Solicitud Única de las ayudas (PAC) | <https://www.jcyl.es/web/es/temas/agricultura-ganaderia/pac.html> |
| Tu maquinaria y su inscripción en el ROMA | <https://www.mapa.gob.es/es/agricultura/temas/medios-de-produccion/maquinaria-agricola/> |
| Productos autorizados y su nº de registro (MAPA) | <https://www.mapa.gob.es/es/agricultura/temas/sanidad-vegetal/productos-fitosanitarios/registro-productos/> |
| Las fechas y las obligaciones, en el BOE | <https://www.boe.es/buscar/act.php?id=BOE-A-2012-11605> |
| Las tablas oficiales del cuaderno digital (FEGA) | <https://www.fega.gob.es/es/siex/documentacion-tecnica-agricola-siex> |

---

## El volcado oficial a la Junta

El **Interfaz Único de Web Services** (IUWS) es el canal oficial por el que un cuaderno
comercial entrega los datos al CUE de la comunidad. Está definido en el **Anexo VI del
documento técnico de SIEX** (v3.3.0) y en Castilla y León vive en
`https://servicios.ayg.jcyl.es/IUWS/`.

**La guía completa está en [`docs/INTEGRACION_IUWS.md`](docs/INTEGRACION_IUWS.md).** Aquí va
el resumen y, sobre todo, la parte honesta.

### Lo que está hecho y funciona

| Qué | Dónde |
|---|---|
| Las seis direcciones, con los ejemplos del anexo | `GET /api/iuws/estado` |
| Los 19 mensajes del interfaz, traducidos | `GET /api/iuws/mensajes` |
| Traducir una respuesta que te han dado | `POST /api/iuws/leer-respuesta` |
| El contenido mínimo del CUE, campo por campo y numerado | `GET /api/iuws/contenido` |
| El sobre oficial con los datos de la finca dentro | `GET /api/iuws/paquete.json` |
| **Llamar al interfaz de verdad** (versión, token, estado de una carga) | `app/iuws_cliente.py` |
| La prueba de conexión, que **se puede hacer ya** | `GET /api/iuws/version?llamar=1` |
| Qué se ha comprobado contra el interfaz de verdad | `GET /api/iuws/comprobar-de-verdad` |

Con un detalle que importa: **cada actividad lleva su identificador propio** (`IdAjena`). Es
lo que permite corregir una actividad ya cargada en vez de duplicarla, y va calculado —no
guardado en una columna— para que sea único y estable sin migrar nada. **No puede cambiar
nunca**: si cambiara, la Junta dejaría de reconocer lo ya cargado.

### Lo que se ha comprobado llamando al interfaz, no leyéndolo

Se llamó al interfaz de la Junta y esto es lo que contestó, guardado en el programa para que no
se olvide:

- En la dirección de Castilla y León **los siete métodos existen**: el de versión contesta `200`
  con `3.11.4` y los demás contestan «no me has dicho quién eres». Ninguno contesta que la
  dirección no existe.
- **El certificado lo exige el servidor**, no el programa: la llamada de comunicación ni
  siquiera negocia la conexión sin él.
- **El entorno de integración de FEGA, que es la dirección que viene por defecto, no publica
  ninguno de los siete métodos.** Contesta en `/IUWS/` pero los métodos dan 404. Es una trampa
  que hace perder una tarde buscando el fallo en el certificado, así que la prueba de conexión
  prueba también la dirección de la comunidad y dice cuál contesta.
- Y una que se encontró con un test: **el interfaz contesta `200` aunque el resultado sea un
  error**. El código bueno va en el cuerpo. Mirar solo el estado HTTP es lo que hace decir
  «comunicación establecida» cuando ha contestado `ERROR_VALIDAR_CREDENCIALES`.

**El descriptor ya está.** Era lo que bloqueaba todo, y se consiguió el 22/09/2026: el Anexo VI
oficial del FEGA (v3.11.4) lleva **incrustados** el descriptor `BdcSix-DS-DiseñoCUE.xlsx` y su
esquema JSON. Están guardados sin tocar en `data/iuws_fuentes/`, con su huella SHA-256 al lado
para poder demostrar que son los oficiales, y sus huellas coinciden con las de dentro del Word.
A partir de ahí, lo que falta para mandar un cuaderno no es programa:

- **Los valores de los catálogos.** El portal público de SIEX publica la estructura de sus 287
  catálogos (141 visibles), y eso ya se puede consultar sin certificado, pero **los datos de
  cada tabla están detrás de un captcha**. Los códigos no se inventan.
- **El certificado con su alta** en el entorno de integración, el **nombre comercial**, la
  **autorización del titular** a la entidad habilitada y el **código SIEX** de cada finca.

La firma del parámetro `data-signed` **ya se hace con el certificado de verdad** y sin exportar
ninguna clave: se firma **donde la clave vive** (el almacén de Windows), con
`scripts/firmar_con_el_certificado.ps1`, y el programa solo recibe la firma. Se comprobó el
27/09/2026 con el certificado del titular, y **se volvió a comprobar el 28/09/2026**: la firma sale y
**se verifica** con su clave pública. Sigue sin haber ninguna librería de criptografía añadida a
Python, y sigue sin hacer falta. Y si no puede firmar, dice que no pudo — **nunca devuelve una firma
inventada**.

Y el 28/09/2026 se volvió a preguntar al interfaz con el certificado puesto, por si el alta había
llegado: **contesta lo mismo** (`Dominio del certificado no registrado en el sistema`). O sea: sigue
sin faltar nada del programa y sigue faltando el alta. **No se ha presentado nada.**

### Lo que NO está hecho, y por qué no se ha inventado

**El JSON de importación todavía no se manda.** Ahora el formato ya no es el problema: se
comprueba contra el esquema JSON oficial (borrador 7, con `jsonschema`) **antes** de llamar al
servidor, y la marca local `formato` no viaja nunca en el cuerpo. Lo que lo impide son **los
códigos**, y esto tiene un motivo medido, no supuesto:

- El esquema oficial declara **528 tipos y ninguno admite vacío**: no hay un solo `null` en todo
  el esquema. Un campo obligatorio de catálogo que no tengamos **no se puede dejar en blanco**.
- El descriptor marca **175 campos obligatorios**, y dice **contra qué catálogo** valida cada
  uno. Sin ese catálogo, ese bloque no se puede armar de forma que valide.

Así que en su lugar se hace lo que sí se puede hacer:

1. Se vuelca el cuaderno **en el orden de campos del contenido mínimo**, con el número y el
   nombre oficial de cada uno, para poder cotejarlo con el documento técnico línea a línea.
2. Los campos cuyo valor es un **código de catálogo salen vacíos y marcados**, no con un
   número inventado. Un código mal puesto no da error al mandarlo: guarda el producto
   equivocado.
3. **El paquete dice de sí mismo que no es el fichero que se manda a la Junta.** Eso está en
   el propio JSON (`formato`, `aviso`) y hay un test que lo comprueba, para que nadie lo
   mande creyendo que vale.

Y ojo con los ejemplos del Anexo VI, que siguen avisando de esto:

> *«Los ejemplos incluidos en los siguientes apartados pueden no corresponderse con la v2.6
> del descriptor, por lo que deben tomarse como tales ejemplos, ya que aún no se pueden
> generar con dicha estructura.»*

Ese aviso **sigue estando en la versión 3.11.4** y se refiere a los ejemplos del anexo, no al
descriptor. Es justo la razón de no copiar los ejemplos y usar el descriptor.

### Lo que falta, y de quién depende

`GET /api/iuws/estado` lo dice cada vez, calculado y no escrito a mano, para que en cuanto se
resuelva una pieza deje de aparecer:

- **De David**: el nombre comercial, el dominio y el servidor, el certificado de dominio (sello
  de entidad con autenticación de cliente), el alta en el entorno de integración y el código
  SIEX de cada finca.
- **De FEGA**: los **valores** de los catálogos oficiales. El descriptor dice **40 catálogos** y
  de qué campo sale cada uno; SIEX publica sus **287** tablas y, cruzando los nombres, **15 de
  esos 40 ya tienen tabla localizada** (con su identificador, y las 15 son públicas). Lo que
  falta son **los datos** de cada tabla, que están detrás de un captcha. Los 25 que no coinciden
  **no se emparejan por parecido**: se preguntan. Todo esto se ve en `GET /api/iuws/estado`.
  Para los **campos obligatorios** de los 18 bloques hacen falta **19 catálogos**, y de esos **7
  ya tienen tabla localizada**; el mapa entero, bloque por bloque, está en el mismo sitio
  (`mapa_del_cuaderno`).
- **De nosotros**: lo que el cuaderno **no pregunta**. El mapeo del bloque de tratamientos
  (`GET /api/iuws/estado`, apartado `mapeo_del_tratamiento`) separa las dos cosas: de sus 11
  campos oficiales, **6 se pueden mandar ya**, **3 esperan un catálogo de FEGA** y **2 dependen de
  la aplicación** (el tipo y la unidad del producto, y en qué parcela concreta se trató). Eso no
  se arregla escribiendo a nadie. En la ronda 23 se cerraron dos de esas lagunas añadiendo las
  dos preguntas que faltaban —**si se aplicó a mano y cómo de bien funcionó**—, que son dos campos
  que el interfaz de la Junta exige como obligatorios.
- **De cada agricultor**: la autorización del titular a la entidad habilitada.

Y **mientras falte cualquier pieza, el sistema no llama al interfaz**. Hacer una llamada sin
el certificado que el interfaz exige solo sirve para que alguien vea un error que no puede
arreglar.

---

## Si vienes de una versión anterior

Al arrancar, el programa **pone al día la base de datos** que ya existe: añade las
columnas que le falten a las tablas que ya están.

Hace falta de verdad, y es un fallo que ya apareció una vez: `create_all` crea las tablas
que no existen, pero **no toca las que ya existen**. Sin esto, al añadir un campo el
programa arranca bien y después revienta con un «no such column» al abrir el cuaderno, y
el agricultor se queda sin poder entrar.

Las columnas nuevas que son obligatorias se añaden con el mismo valor por defecto que
habría puesto Python, así las filas que ya estaban quedan como si siempre hubieran tenido
ese campo. Está en `app/database.py` y tiene tests propios.

---

## Documentación

| Fichero | Para quién | Qué dice |
|---|---|---|
| [`AGENTS.md`](AGENTS.md) | Quien vaya a tocar el código | El convenio de trabajo, las reglas que no se doblan y las recetas |
| [`DESIGN.md`](DESIGN.md) | Quien toque la interfaz | El contrato visual: colores, tipos y componentes |
| [`docs/PLAN_CRM_AGRARIO_2026.md`](docs/PLAN_CRM_AGRARIO_2026.md) | Agentes que amplíen la aplicación de gestión | Especificación del CRM agrario completo, lo verificado, las fuentes oficiales y catorce entregas con criterios de aceptación |
| [`docs/ESPECIFICACION_DETALLADA_CRM_2026.md`](docs/ESPECIFICACION_DETALLADA_CRM_2026.md) | Agentes que ejecuten una entrega E0–E13 | Campos, cálculos, pantallas, ejemplos y pruebas de aceptación de cada fase, incluida la nueva UI con Stitch |
| [`docs/GUIA_UI_UX.md`](docs/GUIA_UI_UX.md) | Quien diseñe una pantalla | Cómo tiene que comportarse la interfaz |
| [`docs/UI_Y_AGENTES.md`](docs/UI_Y_AGENTES.md) | Quien quiera meter IA | Generative UI, agentes y qué se descarta, con motivos |
| [`docs/LO_QUE_PIDE_LA_JUNTA.md`](docs/LO_QUE_PIDE_LA_JUNTA.md) | Quien planifique | Lista verificada de lo que falta para cumplir |
| [`docs/LO_QUE_OBLIGA_LA_LEY.md`](docs/LO_QUE_OBLIGA_LA_LEY.md) | Quien toque una fecha o un texto legal | Qué obliga la ley y qué no, con las comillas literales y los enlaces al BOE |
| [`docs/SERVICIOS_DEL_SIGPAC.md`](docs/SERVICIOS_DEL_SIGPAC.md) | Quien toque el mapa o los datos del SIGPAC | Los mapas y las **once consultas oficiales** del SIGPAC, con su dirección y qué devuelve cada una |
| [`docs/CUADERNO_DE_LA_JUNTA.md`](docs/CUADERNO_DE_LA_JUNTA.md) | Quien toque el cuaderno digital de Castilla y León | El **Cuecyl**: sus instrucciones oficiales, sus 25 hojas hoja por hoja, y cómo se traen las tierras de ahí sin teclearlas |
| [`docs/FACTURAS.md`](docs/FACTURAS.md) | Quien toque las facturas o el lector de documentos | Por qué el cuaderno necesita las facturas, cómo se leen (PDF, escaneo o foto) y qué se hace con lo que se lee |
| [`docs/MEJORAR_LA_INTERFAZ_CON_STITCH.md`](docs/MEJORAR_LA_INTERFAZ_CON_STITCH.md) | Quien quiera rediseñar una pantalla | Qué se puede hacer con Stitch desde este proyecto, qué no, y **el encargo escrito** para pedírselo |
| [`docs/LO_QUE_SE_APUNTA_POR_TIERRA.md`](docs/LO_QUE_SE_APUNTA_POR_TIERRA.md) | Quien pregunte «¿está completo el registro?» | Campo por campo, **qué se apunta de cada tierra**, y lo que falta con sus tres motivos |
| [`docs/FUENTES_OFICIALES_PENDIENTES.md`](docs/FUENTES_OFICIALES_PENDIENTES.md) | Quien integre IUWS | Fuentes comprobadas, lagunas y consultas exactas a FEGA y Castilla y León |
| [`docs/CATALOGOS_OFICIALES.md`](docs/CATALOGOS_OFICIALES.md) | Quien necesite un código oficial | **Qué catálogos oficiales se bajan** (FEGA y MAPA), con su dirección y su huella, **qué no se puede bajar y por qué** (el captcha de SIEX), y las dos tablas que se llaman parecido y no son lo mismo |
| [`docs/REACT.md`](docs/REACT.md) | Quien toque la interfaz a partir de ahora | **La migración a React**: por qué sin compilar, qué pantallas están migradas, cómo se añade una y qué queda por resolver |
| [`docs/QUIEN_ENTRA_EN_LA_FINCA.md`](docs/QUIEN_ENTRA_EN_LA_FINCA.md) | Quien toque las cuentas o las fincas | **Varias cuentas en la misma finca**: quién manda, en qué finca estás trabajando y por qué cambiar de finca cambia el vale |
| [`docs/TRASPASO_A_OTRO_AGENTE.md`](docs/TRASPASO_A_OTRO_AGENTE.md) | Quien llegue de fuera | Qué es esto, en qué estado está y qué falta para integrarse |
| [`docs/CORREO_LISTO_PARA_ENVIAR.md`](docs/CORREO_LISTO_PARA_ENVIAR.md) | **Quien tenga que pedir el alta** | **El correo para copiar y mandar**: el alta y las cinco consultas al FEGA |

---

## La pantalla: seis botones y nada más

La aplicación abre en **Modo Sencillo**. No hay menús: hay lo que el agricultor ha
hecho hoy.

```
        ¿Qué has hecho hoy?

  💧  HE ECHADO PRODUCTO          ← el grande, el 90 % de los usos
      bichos, hierbas, hongos

  🟤  HE ABONADO        🚜  HE HECHO UN TRABAJO
  📖  MI CUADERNO       🖨️  SACAR EN PAPEL
  ❓  NO SÉ QUÉ PULSAR

  🔁  LO MISMO QUE LA ÚLTIMA VEZ      ← atajos, en secundario
  🎤  DÍMELO CON LA VOZ
  📋  MIS PARCELAS, PRODUCTOS Y MÁQUINAS
```

**Y si al agricultor le falta lo imprescindible**, el inicio abre con un aviso y un solo
botón grande: *"AÑADIR MI PRIMERA PARCELA"*. Antes de esto, la aplicación decía "añade
tu primera parcela" y **no había ninguna forma de hacerlo**: el agricultor nuevo se
quedaba mirando seis botones que no llevaban a ninguna parte.

**Lo que hace que esto sea usable de verdad:**

- **Sin jerga.** Todo el vocabulario vive en `app/textos.py`, no en el HTML. Un test
  recorre todos los textos que se sirven y falla si aparece una palabra prohibida.
- **Una pregunta por pantalla.** Cada paso del asistente pregunta una cosa sola. La
  única excepción son los campos opcionales de las altas, que van juntos en el último
  paso con un botón grande de DEJARLO: cinco pantallas seguidas de datos que se pueden
  dejar en blanco marean más que una sola.
- **Vuelve a poner lo de la última vez.** El 80 % de los tratamientos son el mismo
  producto y otra fecha: dos toques.
- **Se lo puedes decir hablando.** El botón 🎤 usa el reconocimiento de voz del propio
  móvil: sin claves, sin coste y sin mandar la voz a ningún sitio nuevo. Donde no esté
  disponible, **se escribe igual** — el dictado es un atajo, nunca un requisito.
  Devuelve una **tarjeta con el formulario a medio rellenar**, no un texto que haya que
  creerse, y lo que no entiende lo pregunta en vez de inventárselo.
- **Sin cobertura funciona.** Lo que se apunta se guarda primero en el móvil y se
  manda solo al recuperar la red. Nunca se pierde nada, ni se muestra un error por
  no tener cobertura.
- **Avisa antes de dejarte equivocarte.** Los números se comprueban en el móvil, sin
  esperar al servidor: con mala cobertura, esa espera es la diferencia entre
  corregirlo y abandonar.
- **Se puede deshacer.** Y nada se borra: se anula con un motivo y queda el rastro.
- **En cada campo, su explicación** al lado: qué es, por qué te lo piden, un ejemplo
  y qué pasa si no lo pones.
- **Letra grande y botones grandes.** 18 px de base (21 px con el botón A+), 64 px de
  alto mínimo, contraste alto para el sol, y se puede ampliar con los dedos.
- **Se abre sin cobertura** gracias al service worker, que guarda la aplicación pero
  **nunca** los datos del agricultor.

---

## Mis cosas: dar de alta lo que se usa

Una pantalla con siete secciones. Se da de alta una vez y luego apuntar es mucho más
rápido, porque el asistente ya sabe de dónde elegir.

| Sección | Qué se guarda | Para qué sirve después |
|---|---|---|
| **Parcelas** | Nombre, hectáreas, secano o regadío, y si hay agua cerca | Cuando dices dónde has echado el producto |
| **Productos que he comprado** | Nombre, número de la etiqueta, dosis máxima y días de espera | Cuando apuntas qué has echado |
| **Abonos** | Nombre y los tres números del saco | Cuando apuntas que has abonado |
| **Quién aplica el producto** | Nombre y número de carné | Cuando dices quién lo ha echado |
| **Quién me asesora** | Nombre y número de inscripción en el registro (ROPO) | Cuando un tratamiento lo dijo un técnico |
| **Máquinas de echar producto** | Nombre y la fecha de la ITV | Cuando dices con qué lo has echado |
| **Naves, almacenes e invernaderos** | Nombre, tipo, uso y referencia catastral | Cuando tratas una nave o guardas la cosecha |

### Las prácticas culturales

Cuando el agricultor dice **OTRO TRABAJO**, el programa pregunta **cuál**: labrar, mantener la
cubierta, podar, desbrozar, escardar, pastar u otra cosa.

Esto se corrigió en la ronda 14 leyendo el documento oficial de la Junta, que de ese apartado
dice: *«permite buscar y/o anotar otras prácticas culturales en una DGC: Laboreo, mantenimiento
de cubierta, pastoreo, etc.»*. Pasaban dos cosas, y la segunda era la grave:

1. **Faltaban dos de las tres que el documento nombra.** No había forma de apuntar un
   mantenimiento de cubierta ni un pastoreo.
2. **La lista de tipos existía en el programa y no la ofrecía ninguna pantalla.** Pulsar «OTRO
   TRABAJO» guardaba la palabra `otra` sin decir nunca cuál, así que la poda, el desbroce, la
   escarda y el laboreo estaban escritos en el código, con su nombre, y **no se podían elegir**.
   El cuaderno los apuntaba todos igual, y el volcado oficial mandaba «otra» para todo.

Ahora se guarda la práctica de verdad, sale con su nombre en el cuaderno —«Mantenimiento de la
cubierta», no `cubierta`— y sigue habiendo **OTRA COSA** para lo que no esté en la lista: una
lista cerrada dejaría fuera al que hace algo que no está previsto.

> **Y una cosa que se encontró al revisar el Anexo II campo por campo:** hay tres bloques del
> contenido mínimo del CUE que este programa no recoge —energía utilizada, cubierta del suelo y
> «evaluación del tratamiento»— y **la app oficial de Castilla y León tampoco los pide**. Está
> explicado uno por uno en [`docs/LO_QUE_PIDE_LA_JUNTA.md`](docs/LO_QUE_PIDE_LA_JUNTA.md),
> apartado 2 bis, con el motivo de cada uno.

### La forma de la parcela

El SIGPAC devuelve el polígono de cada recinto **desde la ronda 10**, y hasta la ronda 20 **no se
veía en ninguna parte**: se guardaba en la base de datos y ahí se quedaba. La auditoría de campos
lo puso en la lista —un dato que entra y no sale— y es la última pieza de esa lista.

Ahora, en *Mis cosas*, cada parcela lleva **el dibujo de su forma**, y las tres partes de su
referencia por separado (polígono, parcela y recinto, como vienen en el papel del SIGPAC).

Tres decisiones que importan:

- **Se dibuja en SVG, sin ninguna librería de mapas.** Un mapa de verdad (con sus teselas, sus
  calles y sus servidores) pesa megas y necesita cobertura. Lo que hace falta aquí es que el
  agricultor **reconozca su tierra de un vistazo**, y eso lo da la forma del trozo.
- **Se corrige por la latitud.** Un grado de longitud no mide lo mismo que uno de latitud: en
  Salamanca, 1° de longitud son unos 84 km y 1° de latitud unos 111. Sin la corrección, el
  recinto de ejemplo saldría **un tercio más ancho** de lo que es. Hay un test que lo comprueba
  contra el polígono de verdad, y otro que comprueba que el norte queda arriba (en la pantalla la
  Y crece hacia abajo, así que hay que darle la vuelta).
- **Si no hay forma, no se dibuja nada.** Una parcela apuntada a mano no tiene geometría, y un
  cuadro inventado **parecería su parcela**. El programa no dibuja lo que no sabe.

Y el polígono entero **no viaja al móvil**: lo que se manda es la línea que se pinta, unos cientos
de caracteres en vez de un texto largo.

### La autorización del producto

Cuarta vez que aparece el mismo fallo en cinco rondas, y esta vez eran **tres comprobaciones de
golpe que no podían saltar nunca**. El programa ya tenía escrito, con sus mensajes y sus tests:

| Comprobación | De qué depende | Qué pasaba |
|---|---|---|
| «Producto no autorizado» | `autorizado` | Se quedaba en su valor por defecto («sí») sin preguntarlo nunca |
| «No vale para ecológico» | `permitido_ecologico` | Igual: por defecto «sí, sirve» |
| «La autorización caducó» | `autorizacion_hasta` | La fecha no se podía escribir en ningún sitio |

**Y las tres bloquean, no avisan.** Usar un producto retirado, o uno que no vale para ecológico en
una finca ecológica, o uno cuya autorización ya caducó, es una infracción. El programa decía
«adelante» en los tres casos.

La tercera es la más delicada y por eso se explica: una **autorización excepcional** es el permiso
**temporal** para usar un producto que no está autorizado con carácter general, y se pide cuando
aparece una plaga que no se puede combatir con lo que hay. Cuando ese permiso se acaba, el
producto deja de poder usarse. Por eso el programa ahora:

- pregunta si el producto está autorizado, si vale para ecológico, y el número y la fecha del
  permiso especial;
- **avisa con mes y medio** de que el permiso se acaba, que es lo que se tarda en pedir otro o en
  buscar la alternativa;
- y si ya acabó, lo dice claro: *«la autorización para usar este producto acabó el 15/06/2026. Ya
  no se puede usar: el programa no te dejará apuntarlo»*.

De paso, la ficha del aplicador pregunta ahora **el tipo de carné** y el número del registro de
equipos de aplicación, que también estaban en la tabla sin llegar a ninguna pantalla.

### Cómo se echó el producto

Se encontró **mirando qué campos de cada tabla no llegaban a ninguna pantalla**, en vez de ir
pantalla por pantalla: se comparó cada columna con las respuestas de la API y con el JavaScript.
Salieron **once** en el registro de tratamientos, y todas con lo mismo: se guardaban y ahí se
quedaban.

De esas once, dos las pide el contenido mínimo del CUE **por su número**:

- **campo 3, «Hora de tratamiento»**: el volcado lo declaraba como campo suyo y no había forma de
  rellenarlo, así que iba siempre vacío. Un campo declarado que nunca se puede llenar es una
  promesa que no se cumple.
- **campo 8, «Estado Fenológico»**: **ni siquiera estaba declarado** en el bloque de
  tratamientos. El dato existía en la tabla y el volcado no lo nombraba, así que quien leyera el
  paquete no podía saber que faltaba.

El resto son las condiciones de la aplicación: temperatura, humedad, **viento y de dónde venía**
(es lo que se pregunta cuando un vecino se queja de que el producto se le fue encima), la mezcla
por hectárea, cuántos estaban trabajando y si pasó algo raro.

Todo va en **una sola pantalla opcional** que se salta con un toque. Lo natural sería hacer tres
preguntas, pero el asistente del tratamiento es el que más se usa: tres pantallas más que saltar
cada vez es un precio que no vale la pena. El que tiene prisa apunta el tratamiento y sigue.

> **Y de paso se arregló un aviso que saltaba siempre.** El cuaderno avisaba «¿has dejado la
> orilla sin tratar?» en todas las parcelas con agua cerca — **y la pregunta no existía en
> ninguna pantalla**. Su etiqueta estaba escrita desde el principio y nunca se había puesto en
> ningún sitio, así que el aviso era imposible de quitar. Ahora se pregunta y, al contestarla,
> desaparece. Es la misma regla que la del cultivo de la parcela: *un aviso que no se puede
> quitar es un aviso que sobra*.

### Las parcelas que se llevan igual

Es la «unidad homogénea de cultivo» de la app oficial, y aquí faltaba **de la misma manera que lo
anterior**: `GrupoParcelas` estaba en la base de datos con tres endpoints —listar, crear a mano y
«calcular» automático— y **ninguna pantalla los llamaba**. `grupo_id` no aparecía ni una vez en
todo el JavaScript.

Y lo que ahorra es exactamente lo que dice el documento oficial: *«tienen como fin facilitar la
cumplimentación del Cuaderno»*. Si tienes seis parcelas de cebada del mismo sistema y cerca unas
de otras, **un tratamiento es un apunte, no seis**. Ahora:

- Hay pantalla propia, con sus parcelas y la superficie sumada.
- Un botón las junta solo: mismo cultivo, mismo sistema y a menos de 8 km, que es el radio que
  fija la aplicación oficial.
- Al apuntar un tratamiento, un abono o una labor, **los grupos salen en la lista** después de las
  parcelas, y al elegir uno la superficie que se pone es la de todas juntas.

**Y al mirarlo apareció un agujero de verdad, no solo una pantalla que faltaba:** la comprobación
de que no se trata más superficie de la que hay **solo se hacía cuando el apunte era de una
parcela**. En un grupo no se comprobaba nada: se podían apuntar 100 hectáreas sobre un grupo de 5
y el programa no decía ni una palabra. Ahora se mira contra la suma de las parcelas del grupo, y
el aviso dice ese número, no el de una parcela suelta.

> **Dos cosas más que se arreglaron al probarlo.** El botón de juntarlas solo cogía la campaña
> que le pasaran, así que sin decirle ninguna **no hacía nada y no decía por qué**; ahora coge la
> del año en curso y, si no puede juntar algo, **dice qué le falta** (parcelas sin cultivo
> declarado, o sin forma en el mapa). Y `centroide_wkt` exigía tres vértices, así que una parcela
> con solo un punto en el mapa se quedaba fuera de la agrupación **en silencio**: un punto es su
> propio centro.

### Qué hay sembrado

Lo que la app oficial tiene como las pestañas **«Características DGC»** (el cultivo de la parcela)
e **«Historial Cultivos»** (los de las campañas anteriores), y aquí **no existía**. Fue el fallo
más raro de todos los que han salido en estas rondas, porque no faltaba un dato: **estaba todo y
no se podía usar**.

- La tabla `ParcelaCultivo` estaba desde las primeras rondas, con su endpoint de alta.
- **Ninguna pantalla la usaba.**
- Y el cuaderno **ya le decía al agricultor** *«a El Prado le falta decir qué cultivo tiene este
  año. Sin eso el cuaderno queda a medias»*… sin darle ninguna forma de contestar. Eso es
  exactamente lo que prohíbe la regla de este proyecto: **si le dices al agricultor que le falta
  algo, le das el botón que lo arregla**.

Tres consecuencias, y las tres arregladas:

1. **Ya se puede decir qué hay sembrado**, cambiarlo si te equivocas, y ver qué pusiste los años
   anteriores. Si repites el mismo cultivo que el año pasado, se avisa y se te manda a las
   medidas preventivas: la rotación es una de las que se piden.
2. **El «Cultivo» de cada tratamiento y cada labor se rellena solo**, con el de la parcela. Es lo
   que la app oficial llama un *campo calculado*: ya lo has dicho una vez, no hay que repetirlo en
   cada apunte. Sin esto, el «Cultivo» de **todas** las actuaciones iba vacío y el volcado
   oficial lo mandaba en blanco.
3. **El aviso «en esa fecha no había cultivo en esta parcela» puede saltar.** Existía, tenía
   tests… y **no podía saltar nunca**, porque dependía de este dato y no había manera de meterlo.
   Un aviso que no puede saltar es un aviso que no existe.

> **Una lección que salió al probarlo:** el catálogo oficial del SIGPAC tiene **una sola** entrada
> de cebada, «CEBADA» (código 5). «Cebada de dos carreras» es una **variedad**, no un producto, así
> que va en su campo aparte. Si se escribe en la especie, el volcado no encuentra código y lo deja
> vacío —que es lo correcto, porque inventarse el código sería peor—, pero el cuaderno queda peor.

### Los papeles

Y la séptima, que llegó la última porque **no sabíamos que faltaba**: la app oficial tiene un
apartado **Documentación** para guardar «contratos, facturas, albaranes de entrega de envases a
Sigfito, etc.», y aquí no existía. Se descubrió releyendo el documento de instrucciones de la
Junta, no un resumen: su frase de resumen dice *«seis secciones con veinte apartados…, además de
un repositorio de documentación»*. La lista de comprobación tenía 21 filas, pero una era
«Utilidades», que es el menú de los informes y no un apartado. El que faltaba era este.

No es un adorno: el cuaderno dice lo que se hizo, y **los papeles son los que lo demuestran**
cuando llega una inspección. El contrato de arrendamiento de la tierra, la factura del producto,
el resguardo de Sigfito de los envases vacíos.

Cómo funciona, y por qué así:

- **Se puede apuntar un papel sin subir el fichero.** «El contrato está en el cajón de arriba» ya
  sirve. Obligar a subir el fichero dejaría fuera justo al agricultor que no sabe hacerle una
  foto, que es el que más lo necesita.
- **Se agrupa en carpetas, y las carpetas las pone el agricultor.** La Junta dice que «puede
  organizarse en distintas carpetas» y no impone ninguna; el programa sugiere unas cuantas
  (Contratos, Facturas, Envases…) y acepta la que él escriba. Un catálogo cerrado sería inventarse
  una obligación que no existe.
- **Los ficheros van a disco, nunca a la base de datos ni al repositorio** (`app/adjuntos.py`), y
  el nombre del fichero en disco **lo decide el programa**: un nombre como `../../main.py`
  escribiría fuera de su carpeta. El nombre que manda el navegador se guarda solo para enseñarlo.
- **Nada se borra.** Un papel se anula con su motivo y **el fichero sigue ahí**: lo que se anula es
  el apunte, no la prueba.
- **Se admiten PDF, fotos y ficheros de oficina** (Word, Excel, OpenDocument), porque lo que pide
  una inspección no tiene un formato fijo.

### Lo que tengo en el almacén

Es el botón **«Situación Cesta»** de la app de la Junta, y aquí **no existía**: los cuatro campos
de la compra del producto (`cantidad_comprada`, `unidad_compra`, `fecha_compra`, `proveedor`)
estaban en la tabla desde el primer día y **no los leía nadie**. Ninguna pantalla los pedía, la
respuesta de la API ni siquiera los devolvía, y no había ninguna cuenta. O sea que la Cesta
estaba a medias: se apuntaba **qué** producto tienes, y no **cuánto**.

Eso deja sin respuesta la pregunta que se hace de verdad en el campo: **«¿me llega producto para
tratar esta parcela, o tengo que ir a comprar?»**. Ahora la ficha del producto pregunta cuánto
compraste, en qué unidad y cuándo, y esta pantalla enseña las tres cifras: comprado, echado y lo
que queda. Son además el libro de entradas y salidas que se mira en una inspección.

**Y lo que no hace es tan importante como lo que hace.** Un producto se compra en una unidad
(litros, kilos) y se echa con una dosis que se mide en otra («kg/ha»). Restar un litro de un kilo
necesita la densidad, que no sabemos y que cambia de un producto a otro. Cuando eso pasa, el
programa **no hace la cuenta**: dice *«lo compraste en kg y lo echas en L: son cosas distintas y
no se pueden restar»*. Un número inventado ahí sería peor que no poner ninguno, porque el
agricultor compraría o dejaría de comprar con ese número delante.

Lo que sí sabe convertir es lo exacto: 1 L son 1000 mL, 1 kg son 1000 g, y `cc` y `mL` son la
misma cantidad con dos nombres. Está en `legal.py`, con sus tests.



Cada pregunta lleva su explicación al lado, y cada apartado dice **dónde se usa después**,
para que el agricultor entienda por qué se lo están preguntando.

---

## Las cuatro clases de aplicación

La app oficial tiene **cuatro secciones separadas para lo mismo**: echar producto. Aquí es
**un solo registro que dice dónde**, porque los datos son los mismos y lo que cambia es qué
se exige.

| Clase | Dónde | Qué se pide |
|---|---|---|
| **En una parcela** | En la tierra | La parcela y las hectáreas. Es el 90 % de los casos |
| **La semilla ya venía tratada** | En la tierra | La parcela y las hectáreas, igual: la semilla se siembra en algún sitio |
| **Al producto ya recogido** | Un almacén | La nave, el producto tratado y su partida |
| **En una nave o un almacén** | Un almacén | La nave y los días para poder volver a entrar sin protección |

**Y no se le pregunta a todo el mundo.** La elección aparece **al final de la lista de
parcelas**, como una salida para quien la necesita:

```
¿Dónde?
  📍 El Prado        2,43 ha · secano
  📍 La Vega         5,00 ha · secado

¿No es en una parcela?
Si has tratado una nave o el producto ya recogido, dilo aquí
  [ En una nave o un almacén ]   [ Al producto ya recogido ]
```

Nueve de cada diez veces el producto se echa en la tierra, y hacer pasar a todo el mundo
por una pregunta que casi nunca aplica es justo lo que la guía de interfaz prohíbe. Quien
trata una nave, lo ve ahí abajo.

Y hay un detalle de modelado que importa: **una nave no se mide en hectáreas**. La
superficie se pide solo cuando la aplicación va sobre la tierra; en una nave se apunta el
local. Antes se exigía siempre, y eso habría obligado a inventarse un número.

---

## Corregir y borrar lo que uno se ha equivocado

Un cuaderno que no se puede arreglar acaba con datos falsos dentro. Desde la ronda 91, **cada apunte
que sale en «mi cuaderno» se puede corregir y borrar** desde su propia ficha, y eso incluye los abonos,
los trabajos y las cosechas, que hasta entonces **no salían en ninguna pantalla** una vez guardados.

```
1 apunte en el cuaderno

Apunte 1                                      12/05/2026 · Producto
Glifosato 36 SL
  Tierra y parcela                         El Prado
  Hectáreas tratadas                        4,90 ha
  Cuánto por hectárea                     2,00 L/ha
  Hasta aquí no puedes coger la cosecha:  26/05/2026
  [ CORREGIR ]                            [ BORRAR ]
```

- **CORREGIR abre el mismo asistente**, con lo que ya estaba puesto: se cambia el dato malo y el apunte
  sigue siendo el mismo (mismo identificador, que es el que viaja a la Junta). Al final el botón dice
  **GUARDAR LOS CAMBIOS**, y el apunte corregido pasa por **las mismas comprobaciones** que uno nuevo.
- **BORRAR pregunta antes**, enseñando lo que va a desaparecer, y ofrece la otra salida («MEJOR
  CORREGIRLO»): el que se ha equivocado al escribirlo casi siempre quiere arreglarlo, no perderlo.
- Lo que se borra **desaparece del cuaderno** —de la lista, del cuaderno de la Junta y de los números—
  y **queda escrito en la auditoría** lo que había, con la fecha y quién lo borró.
- **Lo único que no se puede borrar es un apunte firmado**: la firma es la prueba de lo que había. Ahí
  se dice y se ofrece **anularlo**, que lo deja tachado con su motivo.

La decisión entera, con lo que cambia de la regla de siempre y por qué, está en
[`docs/CORREGIR_Y_BORRAR.md`](docs/CORREGIR_Y_BORRAR.md).

**Y lo mismo con lo que das de alta tú** (ronda 92): en «Mis parcelas, productos y máquinas» cada
**tierra** lleva sus dos botones debajo de su tarjeta, y en «Parcelas que se llevan igual» los lleva cada
**grupo**. Corregir una tierra abre el mismo formulario del alta con lo que ya estaba puesto —así que se
puede arreglar el nombre, las hectáreas o la referencia del SIGPAC que se copió mal— y borrarla se
pregunta antes, con lo que va a desaparecer delante. **Una tierra que tiene apuntes no se deja borrar**:
se dice cuántas cosas dependen de ella y qué hacer, porque borrarla destruiría el cuaderno en silencio.
Un grupo sí se borra (es solo una forma de apuntar de una vez y sus tierras no se tocan), y de un grupo lo
único que se cambia es **cómo lo llamas tú**.

**Y desde la ronda 93, con todo lo demás**: los **productos**, los **abonos**, **quién aplica**, los
**asesores**, las **máquinas** y las **naves** (cada renglón de «mis cosas» tiene sus dos botones), los
**análisis** —con sus números del boletín, que se pueden corregir uno a uno—, lo que has **vendido** y el
**plan de abono**. Corregir cualquiera de ellos abre **el mismo formulario con el que se dan de alta**,
con lo que ya estaba puesto; y borrar solo se deja cuando no lo usa nada del cuaderno (un producto que
está dentro de un tratamiento no se borra: ese tratamiento se quedaría sin decir qué se echó).

---

## Lo que hace el backend

**Registro obligatorio**

- Tratamientos: producto, dosis, superficie, plaga, justificación, aplicador, máquina
  y las condiciones del tiempo.
- Abonos: riqueza N-P-K, kilos por hectárea y **cálculo del abono puro** (unidades
  fertilizantes), que es lo que de verdad mira la administración.
- Labores, riego y cosecha.
- Deja anotar **por grupos de parcelas** (lo que la aplicación oficial llama unidades
  homogéneas de cultivo) y los calcula solos: agrupa las parcelas que se llevan igual
  y están a menos de 8 km.

**Lo que impide hacer mal**

No deja guardar y explica en castellano qué hacer:

| Comprobación | Mensaje |
|---|---|
| Producto sin número de etiqueta o retirado | *"Ese número de etiqueta no nos suena. Míralo otra vez en el envase."* |
| Dosis por encima de la etiqueta | *"Has puesto más de lo que permite la etiqueta. Como mucho son 0,80 L/ha."* |
| Más hectáreas que la parcela | *"La parcela tiene 2,43 hectáreas y has puesto 9,00. Corrige la superficie."* |
| Carné de aplicador caducado | *"El carné de Juan caducó el 03/03/2026. Renueva el carné o cambia quién aplica."* |
| ITV de la máquina caducada | *"La ITV de Pulverizador grande está caducada."* |
| Cosechar sin respetar los días de espera | *"…podrás cogerla a partir del 22/05/2026. Faltan 12 días."* |
| Falta decir por qué se trató | *"Pon por qué lo has echado. Por ejemplo: «vi pulgón»."* |
| Producto no permitido en ecológico | *"Estás en ecológico y este producto no vale para ecológico."* |

**Y avisa de lo que caduca** antes de que sea tarde: el carné, la ITV y los botes.

**El cuaderno en papel** se genera en PDF y **sale aunque falten datos**: si falta
algo, lleva una hoja al final diciendo qué falta. Hay también exportación a CSV con
BOM, para que Excel no destroce las tildes.

---

## Tests

```bash
cd backend

# Python: cálculos, registro obligatorio, textos, interfaz, contrato de diseño y dictado
../.venv/Scripts/python.exe -m pytest          # 4646 tests

# JavaScript: la lógica del móvil y la interfaz, pulsando botones de verdad
node --test "tests_js/*.test.js"               # 1077 tests

# Recorrido completo contra un servidor de verdad (hace falta tenerlo levantado)
../.venv/Scripts/python.exe scripts/humo.py http://127.0.0.1:8000
```

| Fichero | Qué comprueba |
|---|---|
| `tests/test_legal.py` | Los cálculos: días de espera, abono puro, dosis, vigencias |
| `tests/test_geo.py` | Centro de la parcela y distancia entre parcelas |
| `tests/test_sin_jerga.py` | Que ningún texto lleve jerga y que los avisos digan qué hacer |
| `tests/test_registro_obligatorio.py` | Los casos de aceptación, de punta a punta |
| `tests/test_interfaz.py` | Que la pantalla se sirva, con su tipo, sin jerga, y **que ninguna pregunta se quede en blanco** (ni en la aplicación ni en la copia que usan los tests del móvil) |
| `tests/test_design_md.py` | Que el contrato de diseño y el CSS digan lo mismo |
| `tests/test_borradores.py` | El dictado: que entienda y, sobre todo, que no invente |
| `tests/test_certificado.py` | El certificado: leerlo bien y **no creerse una cabecera falsificada** |
| `tests/test_firma.py` | La firma: que la huella sea estable y que se note si algo cambia después |
| `tests/test_firma_cades.py` | Que la firma **se compruebe de verdad**: con firmas hechas con OpenSSL, no inventadas. Y que «no vale» y «no lo he podido comprobar» no se confundan |
| `tests/test_instalaciones.py` | Las naves y las clases de tratamiento (parcela, semilla, postcosecha, nave) |
| `tests/test_plan_abonado.py` | El plan de abono, su comparación, y **que actualizar no reviente** |
| `tests/test_analiticas.py` | Los análisis: el catálogo como puerta, el boletín subido sin salirse de su carpeta, y el enganche con el plan |
| `tests/test_medidas_preventivas.py` | Las medidas de la finca: que lo declarado alimente el apunte, y que desmarcar no borre |
| `tests/test_lista_de_la_junta.py` | Que la lista de lo que falta **sume 21** y que los números de la documentación no se queden viejos |
| `tests/test_cosecha_comercializada.py` | Lo que se vende: que cuadre con lo cosechado, y que una unidad de lechugas no se sume con kilos |
| `tests/test_iuws.py` | El IUWS: las direcciones del anexo, los 19 mensajes, y **que lo que no se sabe no se inventa** |
| `tests/test_iuws_cliente.py` | El cliente del interfaz: las cabeceras del certificado, el token, seguir una carga, y que **nunca se invente una firma** (con un transporte de mentira, sin salir a internet) |
| `tests/test_asesor_semilla_y_agua.py` | El asesor, la semilla y el agua de riego: las tres últimas secciones que estaban a medias |
| `tests/test_seguridad_de_las_claves.py` | Que el atajo de la suite (bajar las iteraciones de la clave) **no se pueda colar en producción** |
| `tests/test_sigpac.py` | El conector: el parser contra una respuesta **de verdad** del SIGPAC, los 933 productos oficiales, y que sin cobertura se diga || `tests/test_nitratos.py` | Las reglas de la zona de nitratos: el tope de 170 kg, la pendiente del 15 %, y que lo que no se sabe se diga |
| `tests/test_documentos.py` | Los papeles: que se puedan apuntar **sin** subir el fichero, que el fichero vaya a disco y no a la base, que un nombre con `..` no escriba fuera, y que nada se borre |
| `tests/test_practicas_culturales.py` | Las prácticas de «otro trabajo»: que estén las que nombra el documento oficial, que se puedan apuntar de verdad, y que no se pregunte dos veces lo mismo |
| `tests/test_cesta_del_almacen.py` | Lo que tengo en el almacén: que la resta se haga cuando se puede, que **no se haga cuando no** (un litro y un kilo), y que los cuatro campos de la compra se pidan y se devuelvan |
| `tests/test_cultivo_de_la_parcela.py` | Qué hay sembrado: que se pueda decir (que era justo lo que faltaba), el historial de otros años, que el cultivo se rellene solo en los apuntes, y que **el aviso que no podía saltar ahora salte** |
| `tests/test_grupos_de_parcelas.py` | Las parcelas que se llevan igual: juntarlas a mano y solas, apuntar en un grupo, y **que la superficie del grupo sí se compruebe** (que era el agujero) |
| `tests/test_como_se_echo.py` | Cómo se echó el producto: que los once campos que se guardaban y no salían ahora salgan, que la hora llegue al volcado en su campo 3, que el estado de la planta esté declarado, y que **el aviso que saltaba siempre se pueda quitar** |
| `tests/test_autorizacion_del_producto.py` | La autorización del producto: que un producto retirado, uno que no vale para ecológico y uno con el permiso caducado **bloqueen de verdad** (las tres comprobaciones existían y no podían saltar) |
| `tests/test_cuaderno_cyl.py` | El cuaderno de la Junta: que se lea lo que pone el papel (la tierra partida en trozos, la casilla de nitratos en blanco, la variedad detrás del punto, la nota al pie), que **subirlo dos veces no duplique ninguna tierra**, y que no se pise lo que el agricultor ya había escrito |
| `tests/test_facturas.py` | Las facturas: que se lean un PDF y una foto, que las cuentas cuadren (cantidad × precio = importe) o se avise, que el NIF del agricultor no se tome por el del proveedor, que nada se borre, y que **lo comprado salga de las facturas** |
| `tests/test_dibujo_de_la_parcela.py` | El dibujo del trozo: que salga la forma de verdad, que **no salga estirada** (la corrección por la latitud, con el polígono real), que el norte quede arriba, y que sin forma **no se dibuje nada** |
| `tests_js/nucleo.test.js` | Números en castellano, cola sin cobertura, repetir, comprobaciones |
| `tests_js/interfaz.test.js` | Que `app.js` arranca y que **los botones llevan a algún sitio**, pulsándolos. Desde que la pantalla de inicio está en React, aquí se comprueba además que **esa pantalla se le pide a React** con los datos de la aplicación |
| `tests_js/react.test.js` | La pantalla de inicio escrita en React, sin navegador: los seis botones y su orden, el botón grande, el saludo con el nombre y el año, el aviso de que falta la primera parcela, que **ninguna frase esté escrita a mano** en el componente, y la salida de emergencia cuando React no ha llegado |

> **Lo que ningún test sustituye:** probarlo con **tres agricultores reales**. Eso
> está en el apartado 5.18 del documento del MVP y sigue pendiente.

### El contrato de diseño

`DESIGN.md` describe el sistema de diseño para que lo lea un agente (o una persona) antes
de tocar la interfaz. Sigue la especificación oficial de
[google-labs-code/design.md](https://github.com/google-labs-code/design.md) y se puede
validar con su herramienta:

```bash
npx --yes -p "@google/design.md" designmd lint DESIGN.md
```

Da **0 errores y 0 advertencias**. En Windows hay que usar el alias `designmd` y no
`design.md`, porque el sufijo `.md` choca con la asociación de ficheros del sistema.

**Los tests no llaman a ese comando a propósito**: un test que necesita Node, npm y
conexión no es un test, es una lotería. En su lugar, `tests/test_design_md.py` comprueba
lo mismo en Python, incluido el contraste de cada par de fondo y texto.

Si cambias un color o una medida: **cambia los dos lados** (`DESIGN.md` y `estilos.css`).
Si no, el test se pone rojo, que es justo lo que tiene que pasar.

Para el resto de las ideas —*Generative UI*, salida estructurada para modelos pequeños y
qué se descarta y por qué— está `docs/UI_Y_AGENTES.md`.

---

## Estructura

```
backend/
├── app/
│   ├── main.py            Arranque, routers y ficheros de la pantalla
│   ├── database.py        Motor de base de datos (SQLite / PostgreSQL)
│   ├── models.py          Tablas
│   ├── schemas.py         Entrada y salida de la API
│   ├── legal.py           LOS CÁLCULOS LEGALES (días de espera, abono puro)
│   ├── validaciones.py    Las reglas que impiden guardar algo ilegal
│   ├── textos.py          TODO el texto que ve el agricultor, en un solo sitio
│   ├── catalogos.py       Medidas preventivas, provincias, zonas vulnerables
│   ├── borradores.py      El dictado: de una frase a un apunte (lógica pura)
│   ├── servicios.py       Lógica de negocio
│   ├── geo.py             Centroides y distancias
│   ├── security.py        Claves y tokens
│   ├── cades.py           Comprueba la firma del cuaderno, sin librerías de criptografía
│   ├── adjuntos.py        Dónde van los ficheros que sube el agricultor, y qué se admite
│   ├── iuws.py            El interfaz de la Junta: direcciones, mensajes y sobre oficial
│   ├── iuws_cliente.py    Hablar con el interfaz de verdad (versión, token, cargas)
│   â””â”€â”€ routers/           cuenta, finca, parcelas, maestros, registro, cuaderno,
│                          interfaz, borradores, firmas, planes, análisis, medidas,
│                          ventas, documentos, iuws
├── web/
│   ├── index.html         La pantalla (sin compilación)
│   ├── estilos.css        Letra grande, botones grandes, contraste alto
│   ├── app.js             La interfaz: pantallas, asistente, cola sin cobertura
│   ├── nucleo.js          La lógica que se prueba con Node
│   ├── vendor/            React, ReactDOM y htm, tal y como los publica su fabricante.
│   │                      No se editan a mano: se bajan con `scripts/bajar_react.py`
│   ├── react/             Las pantallas ya escritas en React. Van ocho: inicio, confirmación, «mis
│   │                      cosas», «los papeles», el almacén, «qué hay sembrado», la ayuda y
│   │                      «mis datos» (ver `docs/REACT.md`)
│   ├── service-worker.js  Para que se abra sin cobertura
│   â””â”€â”€ manifest.webmanifest
├── tests/                 Tests de Python
│   â””â”€â”€ fixtures/          Firmas y recintos DE VERDAD, para no probar contra inventos
├── tests_js/              Tests de JavaScript
├── package.json           Solo para que Node lea los .js como módulos. No hay npm.
└── scripts/humo.py        Recorrido completo contra un servidor de verdad
DESIGN.md                  El contrato de diseño (lo lee un agente antes de tocar la UI)
docs/
├── REACT.md               La migración de la interfaz a React: qué está hecho, cómo se añade
│                          una pantalla y qué queda por resolver
└── UI_Y_AGENTES.md        Generative UI, agentes y qué se descarta, con motivos
data/
└── zv_cyl.csv             Municipios en zona vulnerable a nitratos
```

---

## Decisiones que conviene no deshacer

1. **Los cálculos legales están en `legal.py`, aislados y con tests propios.** Si uno
   está mal, el cuaderno no vale nada y el agricultor puede perder una cosecha.

2. **Todo el texto para el agricultor está en `textos.py`.** No en los routers ni en el
   HTML. Es lo único que permite que `test_sin_jerga.py` y `test_interfaz.py`
   comprueben de una vez que no se ha colado jerga. **Si escribes un texto en
   `app.js`, el test `test_el_javascript_no_lleva_jerga_en_sus_textos` lo caza.**

3. **La pantalla no se compila.** Son ficheros sueltos servidos por el propio
   programa. No es pereza: el servidor no tiene por qué tener Node, y en un móvil con
   mala cobertura una página ligera se abre. **La migración a React respeta eso**: los
   ficheros oficiales de React viajan en `web/vendor` y se cargan con `<script>`, y las
   plantillas se escriben con `htm`, que es JavaScript normal. El porqué y lo que queda
   por hacer están en [`docs/REACT.md`](docs/REACT.md).

4. **Los tipos MIME se declaran a mano en `main.py`.** En Windows, Python los saca del
   registro y un `.js` puede salir como `text/plain`; el navegador entonces rechaza el
   módulo y la pantalla se queda en blanco sin decir por qué.

5. **`explotacion_id` va en todas las tablas de negocio.** Es lo que aísla a un
   agricultor de otro. Si añades una tabla y se te olvida, se rompe el aislamiento.

6. **Nada se borra.** Los apuntes se anulan con un motivo y queda el rastro en
   `auditoria`. Un cuaderno editable sin huella no sirve en una inspección.

7. **Los datos de la etiqueta se copian al apunte.** Si mañana se corrige la ficha de
   un producto, el apunte histórico no puede cambiar con él.

8. **La geometría se guarda como texto WKT**, no como `Geometry`. Así el mismo código
   funciona en SQLite y en PostgreSQL. Al pasar a PostGIS se cambia esa columna.

9. **Zona de nitratos:** el listado municipal oficial derivado de IDECyL está cargado en
   `data/zv_cyl.csv`. Se coteja código INE o municipio y provincia; con datos insuficientes
   el valor es `None` ("no lo sé"), nunca una negativa inventada. La pertenencia concreta
   y la vigencia de la delimitación deben confirmarse cuando haya dudas.

10. **Los números se leen como los escribe un agricultor.** `"0,8"` son 0,8 y `"1.234"`
    son mil doscientos treinta y cuatro. La regla está documentada en `nucleo.js`,
    porque la ambigüedad del punto es real y hay que entenderla antes de tocarla.

11. **`DESIGN.md` es el contrato, y el CSS tiene que cumplirlo.** Todos los colores viven
    en `:root` de `estilos.css` y **en ningún otro sitio**: hay un test que cuenta los
    colores sueltos que quedan fuera. Si cambias un token, cámbialo en los dos ficheros.

12. **Los bordes se declaran como componentes `borde-` en `DESIGN.md`.** El formato no
    tiene sub-token para el color del borde y este diseño **se separa con bordes, no con
    sombras**. Se resolvió así en vez de borrar los bordes del contrato: la alternativa
    era perder información para callar al validador.

13. **El dictado no adivina.** "Dos litros" puede ser la dosis por hectárea o el total, y
    confundirlos es un error de diez veces en el dato que la ley mira. Si no está claro,
    se apunta lo oído con `campo: null` y se pregunta. Está en `borradores.py` y tiene su
    propio test.

14. **Un borrador nunca escribe en el cuaderno.** `POST /api/borradores/desde-texto`
    devuelve una propuesta; el agricultor la confirma. Un modelo de lenguaje, hoy o
    mañana, no apunta nada por su cuenta: aquí un error es una sanción.

---

## Lo que falta

- **Prueba con tres agricultores reales** (apartado 5.18 del MVP): tiempos, si lo hacen
  solos y si entienden los avisos. Ningún test automático sustituye esto.
- **Confirmar la vigencia jurídica y los límites de cada parcela** frente al listado
  municipal del Decreto 5/2020, reproducido desde el Excel oficial de IDECyL en
  [`data/zv_cyl_fuentes`](data/zv_cyl_fuentes/LEEME.md): 24 zonas y 387 municipios.
- **La comprobación contextual de los límites de nitrógeno de CyL**: el Anexo III ya
  avisa con cifra cuando zona, cultivo y sistema coinciden exactamente. Quedan los ajustes
  por cosecha esperada, excepciones y las fechas relativas del Anexo V para revisión humana.
- El **asesor GIP**, que es lo único que le queda a la sección de personas.
- El volcado oficial por la **Interfaz Único de Web Services** de FEGA.
- **La comprobación criptográfica de la firma** (leer el fichero CAdES de AutoFirma y
  validar la cadena de confianza). El mecanismo de firma está hecho; esto necesita
  librerías de ASN.1/CMS que hoy no están.
- **La foto de la etiqueta.** Mismo patrón que el dictado —una imagen entra, un borrador
  sale—, y es donde un modelo de visión tendría sentido. Ver `docs/UI_Y_AGENTES.md`.
- **Borrar lo que se dio de alta por error.** Hoy una parcela o un producto mal dados de
  alta se pueden corregir pero no quitar. Hay que decidirlo con cuidado: en cuanto un
  producto aparece en un apunte, borrarlo dejaría el cuaderno hablando de algo que ya no
  existe.
- **El dictado con modelo**, si los dictados reales que fallen lo justifican. Se enchufa
  detrás de `redacta_borrador` sin cambiar la firma ni el esquema.

> **La lista completa, sección por sección y con el plan por rondas, está en
> [`docs/LO_QUE_PIDE_LA_JUNTA.md`](docs/LO_QUE_PIDE_LA_JUNTA.md).** Ahí se ve qué hay
> hecho, qué está a medias y qué no existe, comparado con la app oficial CUECyL.

---

⚠️ Documento técnico-informativo, **no asesoramiento jurídico**. Las obligaciones deben
confirmarse con la oficina agraria de la zona o con un asesor.


