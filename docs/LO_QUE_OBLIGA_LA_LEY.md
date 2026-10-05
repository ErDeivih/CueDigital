# Qué obliga la ley, y qué no

> **Comprobado el 24/09/2026**, leyendo los textos **consolidados** del BOE (los que están en vigor
> hoy), no resúmenes ni notas de prensa. Cada afirmación lleva su artículo y su enlace, y entre
> comillas va el texto **literal** de la norma.
>
> Este documento existe porque el programa le dice al agricultor qué le obliga la ley, y eso no se
> puede escribir de memoria. Si alguien cambia una fecha en el programa, tiene que cambiarla aquí
> también: hay un test que lo comprueba (`backend/tests/test_lo_que_obliga_la_ley.py`).

---

## 1. Tener cuaderno de explotación: obligatorio cuando lo pide la normativa de tu sector

**Real Decreto 1054/2022, artículo 9.1** (redacción del Real Decreto 34/2025, de 21 de enero,
en vigor desde el 23/01/2025) — [BOE-A-2022-23054](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23054):

> «Los titulares de explotaciones agrarias con unidades de producción agrícolas deberán contar con un
> cuaderno de explotación cuando así lo determine la normativa sectorial correspondiente, en
> particular, en materia de nutrición sostenible de los suelos agrarios, productos fitosanitarios e
> intervenciones PAC.»

Y el mismo artículo, sobre papel o electrónico:

> «La cumplimentación por medios electrónicos del Cuaderno Digital de Explotación Agrícola será
> voluntaria siempre y cuando no exista disposición normativa sectorial por la que se determine un
> obligado registro electrónico de los datos de determinadas actividades agrarias, tal como prevé el
> Real Decreto 1311/2012, de 14 de septiembre.»
>
> «En los restantes supuestos, la llevanza del cuaderno podrá realizarse en papel.»

**Traducido:** el cuaderno hay que tenerlo cuando lo pide la normativa de tu sector (abonos,
productos para las plagas, ayudas de la PAC). Llevarlo en papel o en un programa **lo eliges tú**,
salvo donde una norma sectorial exija registro electrónico. Hoy la que lo exige es la de
tratamientos (punto 4).

## 2. Mandar los datos a la Junta: **voluntario**

**Artículo 10.2 del Real Decreto 1054/2022** (redacción del Real Decreto 34/2025):

> «Los titulares de explotaciones agrarias decidirán de forma voluntaria poner a disposición de la
> administración, a través de los REA correspondientes, la información que hayan cumplimentado en el
> CUE.»

**Traducido:** la ley obliga a **tener** el registro y a poder enseñarlo; **enviarlo no es
obligatorio**. Es la frase que más se malinterpreta y por eso está escrita en la pantalla de *Mi
cuaderno* y en la ayuda.

## 3. Usar un programa propio: permitido

**Artículo 10.3 del Real Decreto 1054/2022**:

> «El titular de explotación agraria podrá utilizar los sistemas informáticos desarrollados por la
> Administración de acuerdo con el apartado 1, o podrá utilizar cualquier otro sistema informático de
> su elección, siempre que cumpla con los requisitos técnicos que se establezcan y con el contenido
> mínimo establecidos en el anexo II.»

**Traducido:** este programa es legal como cuaderno, siempre que tenga el contenido mínimo del anexo
II. Lo que todavía no recoge está declarado en
[`LO_QUE_PIDE_LA_JUNTA.md`](LO_QUE_PIDE_LA_JUNTA.md), sin adornos.

## 4. El registro de tratamientos: papel hasta el 31/12/2026, electrónico desde el 01/01/2027

**Real Decreto 1311/2012, artículo 16.1**, último párrafo (añadido por el Real Decreto 34/2025 y
modificado después por la **disposición final primera del Real Decreto 1039/2025, de 19 de
noviembre** — Ref. BOE-A-2025-23421, en vigor desde el 23/11/2025) —
[BOE-A-2012-11605](https://www.boe.es/buscar/act.php?id=BOE-A-2012-11605):

> «[…] los operadores profesionales, definidos conforme al artículo 3.1 de la Directiva 2009/128/CE
> […], en ámbitos agrarios podrán mantener la información obrante en el registro de tratamientos
> fitosanitarios en soporte papel **hasta el 31 de diciembre de 2026**.»

Es decir: **hasta el 31/12/2026 el registro de tratamientos puede estar en papel; desde el
01/01/2027 tiene que ser electrónico** (Reglamento de Ejecución (UE) 2023/564).

> **Cuidado con la cita:** el Real Decreto 34/2025 decía «hasta el 31 de diciembre de **2025**». El
> Real Decreto 1039/2025 lo cambió a **2026**. Quien lea solo el RD 34/2025 se equivoca de año por
> uno. Lo que vale es el texto consolidado de la norma que lo regula, el RD 1311/2012.

### Comprobado otra vez el 26/09/2026, en fuentes de las comunidades

Se ha vuelto a mirar, porque esta fecha decide si el agricultor puede seguir con el cuaderno de papel
o no, y las comunidades lo explican con más detalle que el BOE. La página de la PAC 2026 del
[Gobierno de Aragón](https://www.aragon.es/pac-2026/cuaderno-digital-cue) (última actualización
21/05/2026) dice, con estas palabras:

> «Las personas usuarias y operadores profesionales podrán mantener el registro de tratamientos
> fitosanitarios en soporte papel **hasta el 31 de diciembre de 2026**.»
>
> «La obligatoriedad de realizar dichas anotaciones por medios electrónicos mediante el CUE digital
> entrará en vigor el **1 de enero de 2027**.»
>
> «Esta ampliación del plazo deriva del **Reglamento de Ejecución (UE) 2025/2203** de la Comisión, de
> 31 de octubre de 2025, y ha sido incorporada al ordenamiento jurídico español mediante el **Real
> Decreto 1039/2025**, de 19 de noviembre.»
>
> «Hasta que la explotación agrícola no tenga la obligatoriedad de usar el cuaderno digital, **es
> obligatorio el modelo de cuaderno de explotación en papel** que integra la información mínima que
> se debe cumplimentar hasta la plena entrada en vigor del CUE digital.»

Eso último es lo que explica **por qué David tiene ese cuaderno de 25 hojas**: hasta que llegue la
obligación del CUE digital, lo que hay que llevar es el modelo de cuaderno de su comunidad (en
Castilla y León, el que descarga del Cuecyl), y **eso es lo que este programa rellena** (ver
[`CUADERNO_DE_LA_JUNTA.md`](CUADERNO_DE_LA_JUNTA.md)).

Lo que **no** cambia: el registro de tratamientos en papel vale hasta el 31/12/2026, y a partir del
01/01/2027 tiene que ser electrónico. Con un cuaderno electrónico propio (art. 10.3) eso está
cubierto; con el papel, no.

## 4 bis. Cuánto tiempo hay que guardar el cuaderno y los papeles: 3 años

**Real Decreto 1311/2012, artículo 16.3**, texto consolidado del BOE —
[BOE-A-2012-11605](https://www.boe.es/buscar/act.php?id=BOE-A-2012-11605). Comprobado el **27/09/2026**
en el PDF consolidado del BOE (`https://www.boe.es/buscar/pdf/2012/BOE-A-2012-11605-consolidado.pdf`):

> «3. Se conservarán, junto con el registro referido en el apartado 1, la documentación relativa al
> asesoramiento prevista en el artículo 11.2, los certificados de inspección de los equipos de
> tratamiento, los contratos especificados en el artículo 41.2.c) de la Ley 43/2002, de 20 de
> noviembre, las facturas y los demás documentos justificativos de los asientos realizados en el
> referido cuaderno, y, en su caso, los resultados de los análisis de residuos de productos
> fitosanitarios que hayan sido realizados sobre sus cultivos y producciones. **Los registros y
> documentos se conservarán al menos durante los 3 años siguientes a su fecha de emisión.**»

**Traducido:** desde que se apunta algo (o se emite el papel que lo justifica) hay que poder
enseñarlo **3 años**. Y no solo el cuaderno: también **las facturas**, los **certificados de
inspección de la máquina**, la **documentación del asesoramiento** y los **análisis de residuos**.
Eso explica por qué este programa guarda los papeles y las facturas y **no borra nada**: lo que se
anula se queda con su motivo.

**Y el plazo de volcado, del mismo artículo 16.1:** cuando el registro sea electrónico obligatorio,
la información «deberá registrarse de manera electrónica en la aplicación que se habilite al efecto
por la autoridad competente, **con un plazo de volcado de esta información de un mes desde la fecha
de realización de los tratamientos**». Es decir: **un mes** para volcar cada tratamiento, contado
desde el día en que se hizo. Es un dato que importa el día que se presente por el interfaz de la
Junta, y por eso queda escrito aquí.

> **De dónde sale esto y qué se ha hecho con ello.** Estaba en la lista de lo que faltaba por
> confirmar (`LO_QUE_PIDE_LA_JUNTA.md`, apartado 2, fila 25) desde hacía rondas: «falta confirmar el
> mínimo legal exigible». Ya no falta: está en el artículo, y se dice **también dentro de la
> aplicación**, en la pantalla de ayuda, con el número del artículo delante para que cualquiera pueda
> comprobarlo. Lo que **no** se hace es borrar nada automáticamente al cumplirse los 3 años: la ley
> dice el mínimo que hay que conservar, no que a los 3 años se pueda tirar sin mirar, y quien decide
> eso es el agricultor.

## 5. Los abonos: registro desde el 01/01/2026 y plan de abonado desde el 01/09/2026

**Real Decreto 1051/2022, de 27 de diciembre** (última actualización publicada el 03/11/2025, en
vigor desde el 01/01/2026 por la Orden APA/1226/2025) —
[BOE-A-2022-23052](https://www.boe.es/buscar/act.php?id=BOE-A-2022-23052):

- **Disposición final única:** «El presente real decreto entrará en vigor el 1 de enero de 2023, si
  bien surtirá efectos a partir de 1 de enero de 2024, salvo el apartado 1 del artículo 4, el
  artículo 5 y el artículo 18, que surtirán efectos **el 1 de enero de 2026**.» → el registro de las
  operaciones de fertilización en el cuaderno es obligatorio **desde el 01/01/2026**.
- **Artículo 4.2:** «[…] será responsable de la elaboración y aplicación de un plan de abonado en
  cada unidad de producción integrante de la explotación de la que es titular, **a partir del 1 de
  septiembre de 2026**. Para las unidades de producción en regadío en las que el cultivo se siembre
  o se plante entre el 1 de marzo y el 30 de junio de 2026 esta obligación será efectiva a partir
  del 1 de enero de 2026.» → el **plan de abonado** es obligatorio **desde el 01/09/2026** (y desde
  el 01/01/2026 en el caso del regadío citado). **Ya está en vigor.**
- **Artículo 5.2:** la información «se consignará, **en papel o en digital** de acuerdo con lo
  previsto en» el Real Decreto 1054/2022 → papel o programa, a elección del titular.

## 6. Cuándo será obligatorio el cuaderno electrónico

**Real Decreto 1054/2022, disposición final única, apartado 2** (redacción del Real Decreto
34/2025):

> «No obstante, el Cuaderno Digital de Explotación Agrícola del artículo 9 será de obligado
> cumplimiento **para el siguiente periodo de programación de la PAC**, para aquellas explotaciones
> agrícolas que cumplan alguna de las siguientes condiciones:
> a) Que tengan una superficie superior a 30 hectáreas, sumando las correspondientes a cultivos
> permanentes y tierras de cultivo, excluidos los pastos temporales;
> b) que tengan más 5 hectáreas de regadío sobre el total de su superficie de cultivos permanentes y
> tierras de cultivos, excluidos los pastos temporales;
> c) que dispongan de invernaderos con superficie total bajo cubierta superior a 0,1 ha., que en el
> caso de que no cumplan ninguna de las condiciones establecidas en los apartados a) y b), sólo la
> parte de la superficie agraria con invernadero deberá estar sujeta al cumplimiento del cuaderno
> digital.»
>
> «Para el resto de las explotaciones, las administraciones públicas deberán poner a disposición de
> todas las explotaciones los sistemas informáticos del Cuaderno Digital de Explotación para su
> utilización **voluntaria**.»

**Traducido:** el cuaderno electrónico obligatorio empieza con el periodo de la PAC siguiente
(después de 2027), y solo para las fincas grandes o con regadío/invernadero por encima de esos
umbrales. Para las demás, es voluntario.

## 7. Lo que todavía NO está aclarado (y por eso se dice en la ayuda)

El artículo 16.1, apartado 5, del Real Decreto 1311/2012 dice que los datos «se consignarán de
manera electrónica» y que «deberán ser proporcionados, **al menos, con carácter mensual**». Leyendo
solo eso, parecería que **un programa propio** tendría que volcar a la Junta cada mes.

No es lo que dicen los artículos 10.2 y 10.3 del Real Decreto 1054/2022, que permiten cualquier
sistema propio y dejan el envío a la voluntad del titular. **Esa contradicción aparente es lo que
está preguntado por escrito a la Junta** (ver
[`CORREO_LISTO_PARA_ENVIAR.md`](CORREO_LISTO_PARA_ENVIAR.md)), y hasta que contesten el programa
**no promete nada**: lo dice tal cual en la ayuda.

---

## Lo que el programa dice de todo esto, y dónde

| Qué dice | Dónde se lee |
|---|---|
| Llevar el cuaderno es obligatorio; mandarlo, no — artículo 10.2 del RD 1054/2022 | Pantalla *Mi cuaderno*, debajo de los botones: `cuaderno.ley_pista` |
| Los cinco puntos de la ley, con sus artículos (10.2, 10.3, fechas y umbrales) | *Ayuda* → «Qué te obliga la ley, y qué no»: `ayuda.pantalla.ley_*` |
| Papel hasta el 31/12/2026 y electrónico desde el 01/01/2027 | *Ayuda* → «Para qué sirve esto»: `PORQUE["papel_o_digital"]` |
| Los plazos que sirve la API | `GET /api/interfaz` → `plazos_legales` |

Todas esas frases salen de `backend/app/textos.py` (nada de textos escritos en el HTML o en el
JavaScript) y pasan por el test de jerga, que es el que impide que una palabra rara llegue a la
pantalla.
