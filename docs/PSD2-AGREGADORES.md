# PSD2 solo lectura: agregadores, licencia, límites y dos opciones medidas

> **Fecha de consulta de todas las fuentes: 2026-11-05.** Cada afirmación lleva su URL y su
> estado (VERIFICADO / PENDIENTE). Lo que no está publicado se escribe **«no publicado»**; no se
> estima. Este documento **no es asesoramiento jurídico**: las obligaciones se confirman con el
> proveedor y, si hace falta, con un abogado.
>
> **Revisión del 2026-11-08** (para la decisión de David): se han vuelto a abrir las páginas de
> precios y límites, se añade un candidato de bajo coste con precio publicado y se pone en números
> **por qué no se hace la licencia propia**. Las filas nuevas llevan su fecha; las del 05/11 se
> mantienen porque no han cambiado. **No se ha contratado nada ni se ha escrito código de PSD2.**

**Qué se busca:** conectar las cuentas del agricultor para **leer saldos y movimientos** y
conciliarlos con los gastos y cobros que la aplicación ya tiene. **Nunca** operar: no se inicia
ningún pago, no se ordena ninguna transferencia y no se guardan credenciales del banco.

---

## 1. Marco legal y técnico, en corto

| Afirmación | Fuente (consultada 2026-11-05) | Estado |
|---|---|---|
| El **AISP** (proveedor de servicios de información sobre cuentas) presta un servicio **en línea** que facilita **información agregada** de una o varias cuentas de pago del usuario en uno o varios proveedores | Banco de España, registro de prestadores de AIS: <https://sedeelectronica.bde.es/sede/es/tramites/registro-prestadores-informacion-cuentas-p222.html> | VERIFICADO |
| El **PISP** inicia pagos en nombre del usuario. **Para solo lectura no se necesita licencia de iniciación de pagos** | Directiva (UE) 2015/2366 (PSD2), anexo I servicios 7 y 8: <https://eur-lex.europa.eu/eli/dir/2015/2366/oj> · transposición: Real Decreto-ley 19/2018, <https://www.boe.es/buscar/act.php?id=BOE-A-2018-16036> | La definición de **AIS** está VERIFICADA en el Banco de España (fila anterior) y la transposición española se ha abierto en el BOE; **el texto literal de la Directiva no se ha abierto hoy** (EUR-Lex no sirvió el contenido): PENDIENTE de leer el anexo I. La conclusión «solo lectura no exige PIS» se apoya en la definición de AIS, no en una cita literal |
| En España, el Banco de España **inscribe** a las entidades que prestan el servicio de información sobre cuentas (art. 15 del RDL 19/2018 y art. 3 del RD 736/2019); hay un procedimiento de **presolicitud** y una guía para solicitantes | Banco de España (misma URL del registro) | VERIFICADO |
| **Consentimiento**: el usuario debe autorizar expresamente el acceso; sin consentimiento no hay acceso. El acceso se limita al **saldo** y a las **operaciones de los últimos 90 días** | RTS sobre autenticación reforzada, Reglamento Delegado (UE) 2018/389, art. 10: <https://www.legislation.gov.uk/eur/2018/389/chapter/III/adopted> (texto del reglamento) | VERIFICADO |
| **Reautenticación**: hace falta autenticación reforzada la primera vez y **cuando han pasado más de 90 días** desde el último acceso a la información | RTS 2018/389, art. 10.2 (misma URL) | VERIFICADO |
| **Frecuencia**: si el usuario **no está pidiendo** la información activamente, el AISP no puede acceder **más de 4 veces en 24 horas**, salvo acuerdo de mayor frecuencia con el banco y consentimiento del usuario | EBA, Q&A 2018_4210 (interpreta el art. 36.5.b del RTS): <https://www.eba.europa.eu/single-rule-book-qa/qna/view/publicId/2018_4210> | VERIFICADO |
| El usuario puede **revocar** el consentimiento; el proveedor debe ofrecer una vía para revisarlo y terminarlo | Enable Banking, FAQ (gestión de consentimientos): <https://enablebanking.com/docs/faq/> | VERIFICADO en el proveedor; el derecho de revocación es de la norma (PSD2) |

**Lo que esto significa para nosotros:** si se contrata a un **AISP ya autorizado**, la aplicación
**no necesita ser AISP ni pedir autorización al Banco de España** para leer cuentas: el proveedor
actúa como entidad regulada y nosotros somos su cliente. Lo confirman dos proveedores en su
documentación: Enable Banking («when your application relies on Enable Banking accessing ASPSPs as
a regulated entity») y Tink («aggreghiamo i dati con la nostra licenza», FAQ de precios). Ese es el
camino barato; **la alternativa —ser AISP propio— exige autorización, capital y equipo** y no es
viable para este producto hoy.

---

## 2. Agregadores candidatos (solo lectura, AIS)

Criterio: que ofrezcan **API de información de cuentas (AIS)**, que operen en España y que tengan
**sandbox** o entorno de pruebas documentado. Coste: **«no publicado»** significa que no hay precio
público y hay que pedir presupuesto.

| Proveedor | Licencia y autoridad | API AIS y sandbox | Coste | Cobertura / límites | Contratación | Fuente (2026-11-05) |
|---|---|---|---|---|---|---|
| **Arcopay** (antes Afterbanks) | «Fintech española regulada por el Banco de España como Entidad de Pago y pasaportada para el resto de Europa»; licencias PSD2 de **AIS y PIS** en Europa y Reino Unido | API PSD2 de información de cuentas + **usuarios mock y bancos sandbox**; documentación SwaggerHub y widget | **No publicado** (contacto comercial) | España, Portugal, Italia, Grecia, Rumanía (+ México, Argentina, Colombia, Chile); AIS sobre cuentas corrientes | Contrato con el proveedor; sandbox con el alta | <https://www.arcopay.io/compania/> · <https://www.arcopay.io/desarrolladores/> |
| **Powens** (incluye **Unnax**) | Powens SAS: institución de pago autorizada y supervisada por la **ACPR** (Francia), CIB 16948. Unnax Regulatory Services EDE, S.L.U.: entidad de dinero electrónico inscrita en el **Banco de España**, código 6719 | API de agregación financiera, transacciones, y **sandbox** (registro gratuito en su consola) | **No publicado** (contacto) | **1.800+ bancos** en Europa; datos de transacciones actualizados a diario; presencia en Francia, España y México | Contrato + alta de la aplicación | <https://www.powens.com/> (pie de página legal) · <https://www.powens.com/coverage/> |
| **Tink** (grupo Visa) | Licencia de Tink emitida por la **FSA sueca** (Finansinspektionen) y válida en la UE: así lo dice su FAQ de precios (quien no tiene licencia propia usa la de Tink; quien la tiene, sube su eIDAS) | API de agregación de cuentas; sandbox con registro en consola; 3.000+ conexiones, 19 mercados europeos | **No publicado como cifra**: plan «Standard: precio base por usuario y mes» sin importe, y «Enterprise: precio personalizado» | 19 mercados; cobertura por mercado en su documentación | Cuenta + contrato; verificación de dominio y due diligence | <https://tink.com/de/preisgestaltung/> · <https://tink.com/about-us/> · <https://console.tink.com/signup> |
| **Enable Banking** | Actúa como entidad regulada (licencia propia); **autoridad no verificada hoy**. Ofrece modo «TPP con licencia propia» (infraestructura dedicada) para quien ya es AISP | API AIS (cuentas, saldos, movimientos) + **sandbox**; se puede probar antes de firmar contrato (producción restringida enlazando cuentas propias) | **No publicado como cifra**: precio por volumen (nº de cuentas y pagos/mes), con **factura mínima mensual**; presupuesto por correo | Consentimiento máximo típico **180 días**; historial de 90 días (límite de las cuentas); revocación desde su portal de consentimientos | Contrato + KYB de la empresa | <https://enablebanking.com/docs/faq/> · <https://enablebanking.com/> |
| **Salt Edge** | Ofrece soluciones AIS/PSD2; **autoridad que concede su licencia: PENDIENTE de verificar** (no se ha localizado una página de precios: `/pricing` devuelve 404) | API de información de cuentas y sandbox para clientes | **No publicado** | Cobertura europea amplia; cifras concretas de España **PENDIENTE** | Contrato | <https://www.saltedge.com/> |
| **GoCardless (Bank Account Data, ex-Nordigen)** | Proveedor de acceso a datos bancarios; **autoridad y continuidad del producto: PENDIENTE** (la página de precios de GoCardless no menciona el producto de datos; hay referencias de terceros al fin del plan gratuito que **no se usan aquí**) | API AIS documentada históricamente; sandbox | **No publicado** (no verificado) | **PENDIENTE** | Contrato | <https://gocardless.com/> |

**Conclusión de la tabla:** hay al menos **ocho candidatos reales** con AIS y sandbox y dos con
autoridad española verificada (Arcopay y Unnax/Powens). **Ninguno de los grandes publica precio**:
remiten a contacto comercial. La excepción es **openbanking.io**, que publica **3 €/mes** pero cuya
licencia y cobertura no están verificadas (ver **2 ter**). Cualquier cifra que se escriba sin
presupuesto o sin leer la letra pequeña sería inventada.

---

## 2 bis. El coste, en claro (comprobado el 2026-11-05)

> **Regla:** primero el coste. Si no hay cifra publicada se escribe **«no publicado»** y se pide
> presupuesto; **no se estima**. David **no ha aprobado ningún gasto**.

### 2 bis.1 Lo que publica cada proveedor

| Proveedor | Qué publica | Cifra | Unidad | URL (consultada 2026-11-05) |
|---|---|---|---|---|
| **Enable Banking** | Precio **por volumen** (nº de cuentas y pagos al mes) y **factura mínima mensual**; presupuesto por correo | **no publicado** | — | <https://enablebanking.com/docs/faq/> (pregunta «How much does it cost…») |
| **Powens / Unnax** | **No hay página de precios** (`/pricing/` devuelve 404). Sandbox con registro gratuito; presupuesto por formulario de contacto | **no publicado** | — | <https://www.powens.com/pricing/> (404) · <https://www.powens.com/contact-us/> |
| **Arcopay** (ex-Afterbanks) | **No hay página de precios**; presupuesto por correo (`info@arcopay.io`, en su web) | **no publicado** | — | <https://www.arcopay.io/desarrolladores/> · <https://www.arcopay.io/compania/> |
| **Tink** | Plan **Standard**: «precio base **por usuario y mes**», **sin importe** en la página; plan Enterprise: «precio personalizado». Sandbox con registro | **no publicado** | usuario/mes (unidad publicada, sin cifra) | <https://tink.com/de/preisgestaltung/> |
| **Salt Edge** | **No hay página de precios**: `/pricing`, `/plans` y `/pricing_plans` devuelven 404 | **no publicado** | — | <https://www.saltedge.com/pricing> (404) · <https://www.saltedge.com/plans> (404) |
| **GoCardless Bank Account Data** (ex-Nordigen) | Unidad de facturación publicada: **«requisición activa al mes»** (una autorización del usuario = una requisición; dura como máximo 90 o 180 días; el sandbox no cuenta). **Precio por requisición: no publicado** | **no publicado** | requisición activa/mes (unidad publicada) | <https://bankaccountdata.zendesk.com/hc/en-gb/articles/11528933493916-Bank-Account-Data-API-Usage-how-is-your-usage-number-calculated> |
| **BBVA API Market** | **Sandbox y área privada gratis** con registro; el coste de producción «depende de los servicios que se consuman y el uso que tengan, que habría que estudiar» | **0 € (sandbox)** · producción **no publicado** | registro / uso | <https://www.bbvaapimarket.com/es/> (FAQ de la portada) |
| **Santander, CaixaBank** | No se ha localizado página de precios oficial | **no publicado** | — | — (PENDIENTE) |

**Resumen:** de los siete proveedores, **ninguno publica el precio de producción**. Lo único con cifra
es el **sandbox de BBVA API Market (0 €)**; los sandbox de los agregadores se prueban al registrarse,
sin precio publicado. Las **unidades** de facturación sí están publicadas en dos casos: Tink
(usuario/mes) y GoCardless (requisición activa/mes).

### 2 bis.2 Los escenarios, con cantidades ciertas (no con precios inventados)

Escenario de la app: **1 explotación, 2 cuentas, 1 consulta al día (≈30/mes), 12 meses, solo lectura,
sin PIS**.

| Concepto | Cantidad anual (aritmética) | Coste con cifras publicadas |
|---|---|---|
| Cuentas conectadas | 2 cuentas × 12 meses = **24 cuentas-mes** | **No calculable**: nadie publica €/cuenta/mes |
| Consultas | 30/mes × 12 = **360 consultas/año** | **No calculable**: nadie publica €/consulta |
| Requisiciones (GoCardless) | **12/año** si las dos cuentas son del mismo banco; **24/año** si son de dos bancos | **No calculable**: no publica €/requisición activa |
| Sandbox / pruebas | 1 entorno | **0 € en BBVA API Market**; en los agregadores, prueba al registrarse (sin precio publicado) |
| Alta, contrato y DPA | 1 | **No publicado** (va en el contrato) |
| **Total anual** | — | **NO PUBLICADO. No se puede dar una cifra sin presupuesto escrito.** |

> **Lo que no se hace:** no se pone un «desde X €» ni un rango orientativo. Un escenario con precios
> supuestos sería una cifra inventada, y David todavía no ha aprobado gasto.

### 2 bis.3 La pregunta exacta (dos presupuestos escritos)

Se piden **dos** presupuestos, a las dos opciones de la sección 4, con este mismo escenario. Texto para
enviar (vale para los dos, cambiando el destinatario):

> Asunto: **Presupuesto AIS (solo lectura) — 2 cuentas, 30 consultas/mes**
>
> Hola: estamos valorando conectar cuentas bancarias **solo para leer saldos y movimientos** (sin
> iniciación de pagos) en una aplicación de gestión agrícola en España. Escenario para el presupuesto:
> **1 empresa, 2 cuentas bancarias en España, 1 consulta al día (≈30 al mes), 12 meses, sandbox
> incluido, sin PIS**. Necesitamos, por escrito y con IVA desglosado: (1) qué incluye la **factura
> mínima mensual** y cuál es su importe; (2) precio **por cuenta/mes** y **por consulta** (o por
> requisición activa al mes, si es su unidad); (3) **coste de alta** e integración; (4) **DPA**
> (encargado de tratamiento) y condiciones RGPD; (5) **cobertura de bancos españoles** (BBVA,
> Santander, CaixaBank, Bankinter, cajas rurales y cooperativas); (6) **límites** de peticiones y
> frecuencia de actualización; (7) plazo de contratación y condiciones de **revocación** del
> consentimiento. Gracias.

Destinatarios:
- **Enable Banking:** `info@enablebanking.com` (publicado en su FAQ).
- **Powens / Unnax:** formulario <https://www.powens.com/contact-us/> (no hay correo comercial
  publicado).
- Si se quiere una tercera referencia: **Arcopay**, `info@arcopay.io`.

### 2 bis.4 Decisión y criterio de parada

1. **Sin coste publicado no se propone contratar.** No hay propuesta económica que llevar a David.
2. **Dos presupuestos escritos** (Enable Banking y Powens/Unnax) y **decide David**. Este documento
   no aprueba gasto.
3. **Criterio de parada:** si el coste anual supera el de **seguir con la importación de extracto por
   fichero** —que ya existe y cuesta **0 €**—, **no se contrata**. La conexión PSD2 ahorra teclear,
   no aporta un dato que hoy falte.
4. **Nada de código de PSD2** hasta que haya contrato firmado y aprobación de David.

---

## 2 ter. Revisión del 2026-11-08: lo que se puede decidir hoy

> **Para David, en una frase:** hoy **no hay ningún precio de producción publicado** por los
> agregadores grandes; hay **sandbox gratis** para probar y **un candidato pequeño que publica
> 3 €/mes por cuenta** pero cuya licencia y cobertura española **no están verificadas**. La licencia
> propia (ser AISP) exige **50.000 € de capital inicial** y certificados: está descartada. La
> decisión de gastar sigue siendo de David y **no se contrata nada en este documento**.

### 2 ter.1 Precio publicado, precio desconocido y prueba gratis

| Proveedor | Qué se puede leer hoy | Cifra publicada | Qué falta para decidir | Fuente (2026-11-08) |
|---|---|---|---|---|
| **Enable Banking** | Precio **por volumen** (cuentas y pagos/mes) y **factura mínima mensual**; se puede crear cuenta, usar sandbox y **enlazar cuentas propias en producción antes de firmar** (aplicación restringida) | **No publicado** (presupuesto a `info@enablebanking.com`) | Cuánto es el mínimo mensual y el €/cuenta; cobertura de bancos españoles por banco | <https://enablebanking.com/docs/faq/> (preguntas «How much does it cost…» y «Can I test… before signing…», abiertas 2026-11-08) |
| **Powens / Unnax** | Sin página de precios (`/pricing/` sigue devolviendo **404**); consola con registro gratuito; entidades ACPR (CIB 16948) y Banco de España (código 6719) en el pie legal | **No publicado** | Presupuesto y DPA | <https://www.powens.com/pricing/> (404, 2026-11-08) · <https://www.powens.com/> (pie legal, 2026-11-08) |
| **Tink** (Visa) | Plan **Standard**: «precio base **por usuario y mes**», sin importe; Enterprise: «personalizado». Licencia de la FSA sueca (la propia o la del cliente) | **No publicado** | €/usuario/mes del plan Standard | <https://tink.com/de/preisgestaltung/> (abierta 2026-11-08) |
| **GoCardless Bank Account Data** (ex-Nordigen) | Unidad de facturación publicada: **requisición activa/mes** (una autorización = una requisición; 90 o 180 días; sandbox no cuenta) | **No publicado** | Precio por requisición y si aceptan altas nuevas | <https://bankaccountdata.zendesk.com/hc/en-gb/articles/11528933493916-Bank-Account-Data-API-Usage-how-is-your-usage-number-calculated> (2026-11-08) |
| **openbanking.io** (candidato nuevo, pequeño) | Precio **público**: **3 €/mes con 1 cuenta incluida**, **+1 €/mes por cuenta adicional**; sin tarjeta para empezar; dice **350+ bancos PSD2 / 2.611 bancos** y España en la lista; clave privada en el dispositivo, el servidor solo guarda cifrado | **3 €/mes (1 cuenta) · 1 €/mes por cuenta adicional** | **Licencia**: no publica si actúa con licencia propia o como técnico de un AISP; **cobertura real de los bancos de los agricultores**; DPA; y si su API sirve para una aplicación de terceros (no solo para su app) | <https://open-banking.io/en> · <https://open-banking.io/en/banks> · <https://open-banking.io/en/security> (2026-11-08) |
| **BBVA API Market** | Sandbox y área privada gratis con registro; producción según uso | **0 € (sandbox)** · producción **no publicado** | Qué API de AIS ofrece a terceros y a qué precio | <https://www.bbvaapimarket.com/es/> (2026-11-05) |
| **TrueLayer** | No hay página de precios (`/pricing/` devuelve **404**) | **No publicado** | Presupuesto | <https://truelayer.com/pricing/> (404, 2026-11-08) |
| **Salt Edge** | Sin página de precios (`/pricing`, `/plans` → 404) | **No publicado** | Presupuesto | <https://www.saltedge.com/pricing> (404, 2026-11-05) |

**Aritmética del único precio publicado, como referencia y no como oferta:** con openbanking.io,
**2 cuentas = 3 € + 1 € = 4 €/mes = 48 €/año**, y **3 cuentas = 60 €/año**, antes de IVA y de
cualquier alta. Es **el único ancla pública** que existe hoy; **no es una oferta para nuestro caso**
porque su licencia y su cobertura española no están verificadas, y un precio bajo no compensa un
proveedor que no pueda leer los bancos de los agricultores o que no tenga DPA.

**Lo que sigue sin poder calcularse:** coste de los grandes (Enable Banking, Powens, Tink,
Arcopay, TrueLayer, Salt Edge, GoCardless) y coste de alta/integración. Sin presupuesto escrito no
hay cifra; no se estima.

### 2 ter.2 Por qué no se hace la licencia propia (ser AISP), en números

| Concepto | Cifra | Fuente (2026-11-08) |
|---|---|---|
| **Capital inicial** para un AISP (servicio del anexo I, punto 7) | **50.000 €** | Directiva (UE) 2015/2366, art. 7.1.b: <https://paymentslaw.eu/psd-2/art-7/> (texto del artículo abierto 2026-11-08) |
| Certificados **eIDAS QWAC + QSealC** | **2.000–10.000 €/año**, según el prestador — **estimación de un tercero, no tarifa oficial** | Guía de terceros: <https://dev.to/johnfrandsen/migrating-off-nordigen-a-field-guide-for-indie-builders-2026-4o3j> (2026-11-08; se usa **solo** como orden de magnitud, marcado como no oficial) |
| Autorización, auditoría, seguro de responsabilidad, DORA, pruebas de penetración, equipo | **No publicado** | Banco de España, registro y guía de AIS: <https://sedeelectronica.bde.es/sede/es/tramites/registro-prestadores-informacion-cuentas-p222.html> |
| **Conclusión** | **Descartado**: 50.000 € de capital más certificados, auditoría y meses de tramitación para leer dos cuentas. La vía es **un AISP ya autorizado** | — |

### 2 ter.3 Límites que no cambian con el proveedor

| Límite | Qué significa para la pantalla | Fuente |
|---|---|---|
| **4 accesos/24 h** si el agricultor no está pidiendo la información activamente | Con **una consulta al día** no se llega al límite; si se sincroniza al abrir la pantalla, se cuenta | EBA Q&A 2018_4210: <https://www.eba.europa.eu/single-rule-book-qa/qna/view/publicId/2018_4210> |
| **Saldo y movimientos de los últimos 90 días** | La primera conexión **no trae años de historial**; lo anterior sigue viniendo del extracto por fichero | RTS 2018/389, art. 10: <https://www.legislation.gov.uk/eur/2018/389/chapter/III/adopted> |
| **Reautenticación a los 90 días**; consentimiento máximo típico **180 días** | Hay que avisar antes de que caduque y pedir reconexión; si no, la pantalla se queda sin datos | RTS art. 10.2 · Enable Banking FAQ (validez máxima 180 días, 2026-11-08) |
| **Solo lectura** | Sin PIS, sin transferencias, sin cambiar nada en el banco; sin guardar credenciales | PSD2 anexo I y RDL 19/2018 |
| **Revocación** | El agricultor puede cortar el acceso; el histórico ya importado **no se borra** | Enable Banking FAQ (portal de consentimientos) |

### 2 ter.4 La decisión, con tres caminos y un criterio de parada

| Camino | Coste | Qué se gana | Qué se arriesga | Cuándo elegirlo |
|---|---|---|---|---|
| **A. Seguir como hoy**: extracto por fichero | **0 €** | Ya funciona; el agricultor sube el extracto y se concilia | Teclado manual y menos fresco | **Por defecto**, hasta que haya presupuesto y aprobación |
| **B. Agregador AISP** (Enable Banking, Powens/Unnax; opcional openbanking.io si verifica licencia) | **Desconocido** en los grandes; **48 €/año** de ancla en openbanking.io (2 cuentas, sin IVA) | Saldos y movimientos solos, sin teclear | Coste recurrente + dependencia + DPA + cobertura | Solo si el presupuesto anual es **menor que el coste de seguir a mano** y David lo aprueba |
| **C. Licencia propia (AISP)** | **50.000 € de capital** + certificados + auditoría | Control total | Inviable para este producto | **Descartado** |

**Recomendación honesta:** pedir **dos presupuestos escritos** (Enable Banking y Powens/Unnax) con el
texto de **2 bis.3**; y, **solo si se quiere una tercera referencia barata**, pedir a **openbanking.io**
por escrito: licencia con la que opera, cobertura de los bancos españoles que usan los agricultores,
DPA, y si su API admite aplicaciones de terceros con las claves del cliente. **No se contrata nada**
hasta que David vea las cifras y lo apruebe. Si el anual supera lo que cuesta seguir subiendo el
extracto (0 €), **no se contrata**.

---

## 3. Bancos españoles con API propia

| Banco | Qué hay verificado | Estado |
|---|---|---|
| **BBVA** (BBVA API Market) | Portal oficial con **APIs normativas PSD2** y de conciliación (`Reconciliation`); **sandbox y área privada gratis con registro** (no hace falta ser cliente); el coste de producción «depende de los servicios que se consuman y el uso», y hay que estudiarlo. Qué API concreta de **AIS** ofrece a terceros: **PENDIENTE** | Portal y condiciones: **VERIFICADO** · AIS concreta: **PENDIENTE** · precio de producción: **no publicado** |
| **Santander**, **CaixaBank** y resto | Tienen iniciativas de *open banking* para terceros, pero **no se ha verificado en fuente oficial** qué API de AIS ofrecen, con qué licencia ni con qué límites. Solo fuentes de terceros, que no se usan | **PENDIENTE** |

**Lo importante, y esto sí está verificado:** conectar **directamente** con cada banco exige ser
**TPP con licencia propia y certificados eIDAS** (el RTS y los proveedores lo describen: Enable
Banking, FAQ, modo «TPP con licencia propia», y el Banco de España exige inscripción como AISP). Para
este producto, **la vía directa con cada banco no es viable**: multiplica contratos, certificados y
mantenimiento. La vía es **un agregador AISP**.

---

## 4. Las dos opciones medidas y la decisión

### Opción A — **Enable Banking** (AIS con licencia del proveedor)

- **Qué es:** API de información de cuentas; nosotros consumimos su API, el usuario autoriza en su
  banco y el proveedor actúa como entidad regulada.
- **Licencia:** proveedor con licencia propia; nosotros **no** necesitamos ser AISP ni PISP
  (VERIFICADO en su FAQ: modo de entidad regulada y modo «TPP con licencia propia»).
- **Límite de uso:** consentimiento máximo típico **180 días**; acceso a saldo y movimientos de los
  **últimos 90 días**; el RTS impone **4 accesos/24 h** si el usuario no pide activamente la
  información; la API tiene límites de peticiones (respuesta 429) — cifras concretas **PENDIENTE**
  (están en su documentación de referencia, no en la FAQ).
- **Coste:** **no publicado**. Precio por volumen con **factura mínima mensual**; presupuesto por
  `info@enablebanking.com`.
- **Contratación:** cuenta + sandbox → contrato + KYB → producción. Se puede probar antes de firmar.
- **Encaje:** el más rápido de integrar y el único de los cinco que **publica cómo probar sin
  contrato**.

### Opción B — **Powens / Unnax** (AIS con entidad en España)

- **Qué es:** agregación financiera (1.800+ bancos europeos) con entidad española (Unnax) y matriz
  francesa (Powens).
- **Licencia:** **ACPR** (Francia, CIB 16948) y **Banco de España** (Unnax Regulatory Services EDE,
  código 6719) — VERIFICADO en su pie legal.
- **Límite de uso:** límites de peticiones y cuentas **PENDIENTE** (van en contrato/documentación);
  datos actualizados a diario; cobertura española amplia.
- **Coste:** **no publicado** (contacto).
- **Contratación:** contrato + alta de la aplicación + sandbox (registro gratuito).
- **Encaje:** el que tiene **entidad española regulada** y cobertura contrastada; más orientado a
  contratos de volumen.

### La decisión, con la regla de David

| Dimensión | Opción A (Enable Banking) | Opción B (Powens/Unnax) |
|---|---|---|
| Coste | **No publicado** (por volumen + mínimo mensual) | **No publicado** |
| Licencia | Proveedor regulado; no hace falta ser AISP | ACPR + Banco de España (Unnax) |
| Límite | 180 días de consentimiento; 90 días de historial; 4 accesos/24 h; rate limits PENDIENTE | PENDIENTE en cifras |
| Sandbox | Sí, autoservicio antes de contrato | Sí, registro |
| Cobertura España | PENDIENTE de confirmar por banco | 1.800+ bancos UE |

**No se puede elegir «la más barata que cumpla» porque ninguna de las dos publica precio** (comprobado
otra vez el 2026-11-05 en la sección **2 bis**). Las dos implican contrato y factura mínima, así que el
coste es **relevante y desconocido**. Por la regla acordada, esto es **nivel 3: paro y pregunto**.

**La pregunta concreta (para llevar a los dos):** precio anual para este escenario marcado como
supuesto: **1 explotación, 2 cuentas bancarias, 1 consulta al día (≈30 al mes), 12 meses**, sin
iniciación de pagos, con sandbox incluido y DPA firmado. Pedir: alta, mínimo mensual, precio por
cuenta y por consulta, límites de peticiones, cobertura de los bancos españoles que usan los
agricultores (BBVA, Santander, CaixaBank, Bankinter, cooperativas y cajas rurales), plazo de
contratación y condiciones de revocación. **Con esos dos presupuestos se elige el más barato que
cumpla** (AIS España + sandbox + consentimiento + DPA + sin PIS).

**Criterio de parada adicional:** si el precio anual supera lo que cuesta seguir con la importación
de extractos por fichero (que ya existe y es gratis), **no se contrata**: no se paga por comodidad
lo que el agricultor puede hacer subiendo un fichero.

---

## 5. Cómo se engancharía a lo que ya existe

La aplicación **ya tiene** el circuito de extractos y conciliación, y está construido para que la
fuente sea intercambiable:

- `CuentaBancaria` guarda nombre, banco y **solo los cuatro últimos dígitos**, y dice en su
  docstring que **no se pide ningún dato de la banca**: ni claves ni acceso
  (`backend/app/models.py:1949-1984`). Eso no cambia con PSD2: se sigue sin guardar credenciales.
- `ImportacionDeExtracto` registra cada lote (qué se leyó, de quién, huella) y **no guarda el
  fichero** (`models.py:2030-2076`).
- `MovimientoDeExtracto` es el hecho del banco (fecha, concepto, importe, saldo, referencia) y
  **no crea ningún ingreso ni gasto**; la conciliación con `Cobro`, `Gasto` y `PagoDeGasto` vive en
  `ConciliacionDeMovimiento` (`models.py:1717, 2078-2155, 2158, 4100, 4303`).
- Las reglas de duplicado y de traspaso propio ya están resueltas (`clave_de_duplicado`,
  `pareja_de_traspaso_id`), así que PSD2 **no necesita un modelo de dinero nuevo**.

**Diseño propuesto (fase 2, si se contrata):**

1. Nueva fuente de movimientos: `origen = "psd2"` en `MovimientoDeExtracto` (o una
   `ImportacionDeExtracto` sintética con `huella` del lote), reutilizando `clave_de_duplicado` para
   que **volver a sincronizar no duplique** nada.
2. Saldos: guardar el saldo que devuelve el banco por cuenta y fecha de consulta (nunca calcularlo
   desde los movimientos y llamarlo «saldo del banco»).
3. Pantalla: «conectar cuenta» → consentimiento en el banco → elegir cuentas → sincronizar; y
   «desconectar» que revoca el consentimiento. Todo el texto, en `textos.py`.
4. La conciliación **no cambia**: los movimientos entran y se concilian como hoy.
5. Nada de ingresos/gastos automáticos: un movimiento no es un apunte del cuaderno.

---

## 6. Qué NO se hará (límite duro)

- **No operar:** sin iniciación de pagos, sin transferencias, sin domiciliaciones, sin cambiar nada
  en el banco. Solo lectura.
- **No guardar credenciales** del banco: ni usuario, ni contraseña, ni claves, ni coordenadas.
- **No hacer *scraping*** de la banca electrónica ni pedir la clave al agricultor.
- **No guardar datos de tarjeta** ni datos de pago sensibles.
- **No conectar con licencia propia** (ser AISP): no es viable ni necesario si se contrata a un AISP.
- **No dar por hecho que hay cobertura**: si un banco no está en el agregador, se dice y se sigue
  con la importación de extracto por fichero.

Coherente con lo ya escrito en `docs/CONTRATO_IMPLEMENTACION_CRM.md:251` («nada de PSD2 ni
credenciales») y con `WALL.md:48-49`: **mientras no haya contrato con un proveedor autorizado y
aprobación de David, PSD2 no entra en el código**.

---

## 7. Seguridad, consentimiento y datos

- **El consentimiento se da en el banco**, no en nuestra aplicación: el flujo redirige al usuario a
  su entidad y allí se autentica. Nuestra aplicación **nunca ve la clave** (así lo describen los
  proveedores: Enable Banking, FAQ).
- **Qué se guarda:** identificador de sesión/consentimiento del proveedor, `identification_hash`
  de la cuenta (identificador estable que da Enable Banking para emparejar la misma cuenta entre
  sesiones), saldos y movimientos, y la fecha de la última consulta. **Nunca credenciales.**
- **Caducidad:** el consentimiento caduca (máximo típico 180 días en Enable Banking; la norma exige
  reautenticación a los 90 días del último acceso). La aplicación debe **avisar antes de que
  caduque** y pedir reconexión.
- **Revocación:** el usuario puede revocar en el proveedor (Enable Banking ofrece su portal de
  consentimientos) y desde nuestra aplicación (botón «desconectar»). Al revocar se deja de
  sincronizar y **no se borra el histórico ya importado** (se conserva como cualquier extracto).
- **RGPD:** base jurídica = **consentimiento** del usuario; minimización (solo saldo y movimientos);
  hay que firmar **DPA** con el agregador y verificar dónde trata los datos; informar en la política
  de privacidad de quién es el proveedor y de cómo revocar. **PENDIENTE** revisar el DPA concreto
  del proveedor elegido (no es asesoría jurídica).

---

## 8. Qué hay que contratar o pedir

| # | Qué | De quién | Estado |
|---|---|---|---|
| 1 | **Dos presupuestos escritos** con el escenario de uso (2 cuentas, ≈30 consultas/mes, 12 meses; texto listo en **2 bis.3**) | Enable Banking y Powens/Unnax | **PENDIENTE (nivel 3)** |
| 1 bis | **Tercera referencia barata**: presupuesto, licencia y cobertura de openbanking.io (3 €/mes por cuenta publicados, sin verificar licencia ni bancos) | openbanking.io | **PENDIENTE (nivel 3); no se usa sin verificar licencia y DPA** |
| 2 | Contrato de servicios AIS y **DPA** | Proveedor elegido | PENDIENTE |
| 3 | Alta de la aplicación (KYB, verificación de dominio) | Proveedor | PENDIENTE |
| 4 | Confirmar cobertura de los bancos que usan los agricultores | Proveedor | PENDIENTE |
| 5 | Aprobación de David del gasto y del alcance (solo lectura) | David | PENDIENTE |
| 6 | Si se quisiera licencia propia (descartado): autorización como AISP | Banco de España | No se hace |

---

## 9. Verificación (resumen)

| Afirmación | URL | Fecha | Estado |
|---|---|---|---|
| AISP = información agregada de cuentas; inscripción en el Banco de España | <https://sedeelectronica.bde.es/sede/es/tramites/registro-prestadores-informacion-cuentas-p222.html> | 2026-11-05 | VERIFICADO |
| Consentimiento: saldo y operaciones de los últimos 90 días; reautenticación a los 90 días | <https://www.legislation.gov.uk/eur/2018/389/chapter/III/adopted> | 2026-11-05 | VERIFICADO |
| 4 accesos/24 h si el usuario no pide activamente la información | <https://www.eba.europa.eu/single-rule-book-qa/qna/view/publicId/2018_4210> | 2026-11-05 | VERIFICADO |
| Arcopay: entidad de pago española (Banco de España), licencias AIS/PIS, sandbox | <https://www.arcopay.io/compania/> | 2026-11-05 | VERIFICADO |
| Powens/Unnax: ACPR CIB 16948 y Banco de España código 6719 | <https://www.powens.com/> | 2026-11-05 | VERIFICADO |
| Tink: licencia emitida por la **FSA sueca**; plan «por usuario y mes» sin cifra | <https://tink.com/de/preisgestaltung/> | 2026-11-05 | VERIFICADO lo publicado; cifra **NO PUBLICADA** |
| Enable Banking: sandbox antes de contrato; precio por volumen con mínimo mensual; consentimiento máximo típico 180 días | <https://enablebanking.com/docs/faq/> | 2026-11-05 | VERIFICADO; precio **NO PUBLICADO** |
| Powens/Unnax: sin página de precios (`/pricing/` devuelve 404); sandbox con registro | <https://www.powens.com/pricing/> | 2026-11-05 | **NO PUBLICADO** |
| Salt Edge: sin página de precios (`/pricing`, `/plans`, `/pricing_plans` → 404) | <https://www.saltedge.com/pricing> | 2026-11-05 | **NO PUBLICADO** |
| GoCardless Bank Account Data: unidad de facturación «requisición activa al mes»; GoCardless Ltd autorizada por la **FCA** (PSR 2017, nº 597190) | <https://bankaccountdata.zendesk.com/hc/en-gb/articles/11528933493916-Bank-Account-Data-API-Usage-how-is-your-usage-number-calculated> · <https://bankaccountdata.zendesk.com/hc/en-gb/categories/17222350058268-FAQ> | 2026-11-05 | Unidad y licencia VERIFICADAS; precio **NO PUBLICADO** |
| BBVA API Market: sandbox y área privada gratis con registro; producción según uso | <https://www.bbvaapimarket.com/es/> | 2026-11-05 | VERIFICADO (sandbox 0 €); producción **NO PUBLICADO** |
| Enable Banking: volumen + factura mínima; sandbox y cuentas propias antes de firmar; consentimiento máximo típico 180 días | <https://enablebanking.com/docs/faq/> | 2026-11-08 | VERIFICADO; precio **NO PUBLICADO** |
| Tink: plan Standard «por usuario y mes» sin importe; Enterprise personalizado; licencia FSA sueca | <https://tink.com/de/preisgestaltung/> | 2026-11-08 | VERIFICADO lo publicado; cifra **NO PUBLICADA** |
| Powens: `/pricing/` sigue devolviendo 404 | <https://www.powens.com/pricing/> | 2026-11-08 | **NO PUBLICADO** |
| TrueLayer: `/pricing/` devuelve 404 | <https://truelayer.com/pricing/> | 2026-11-08 | **NO PUBLICADO** |
| GoCardless: requisición activa/mes como unidad; sandbox no cuenta | <https://bankaccountdata.zendesk.com/hc/en-gb/articles/11528933493916-Bank-Account-Data-API-Usage-how-is-your-usage-number-calculated> | 2026-11-08 | Unidad VERIFICADA; precio **NO PUBLICADO** |
| openbanking.io: 3 €/mes con 1 cuenta y 1 €/mes por adicional; dice 350+ bancos PSD2 y España en la lista; cifra el dato en el dispositivo | <https://open-banking.io/en> · <https://open-banking.io/en/banks> · <https://open-banking.io/en/security> | 2026-11-08 | Precio y lista VERIFICADOS en su web; **licencia y DPA NO VERIFICADOS** |
| Capital inicial de un AISP: **50.000 €** | <https://paymentslaw.eu/psd-2/art-7/> (art. 7.1.b) | 2026-11-08 | VERIFICADO |
| eIDAS QWAC+QSealC: 2.000–10.000 €/año | <https://dev.to/johnfrandsen/migrating-off-nordigen-a-field-guide-for-indie-builders-2026-4o3j> | 2026-11-08 | **ESTIMACIÓN DE UN TERCERO**, no tarifa oficial |
| APIs propias de Santander/CaixaBank para AIS | — | 2026-11-05 | **PENDIENTE** |

**No verificado (no se rellena):** **ningún precio de producción** de los agregadores grandes;
cobertura exacta de bancos españoles de Tink, Salt Edge y Enable Banking; **licencia con la que
opera openbanking.io** (no dice si es AISP propio o técnico de uno) y su DPA; límites numéricos de
peticiones; condiciones de las APIs propias de Santander y CaixaBank; autoridad supervisora de Salt
Edge y Enable Banking; qué API concreta de AIS ofrece BBVA a terceros. **Lo que sí queda cerrado:**
quien concede la licencia a Arcopay (Banco de España), Powens/Unnax (ACPR y Banco de España), Tink
(FSA sueca) y GoCardless (FCA); la unidad de facturación de Tink y de GoCardless; que el sandbox de
BBVA API Market es gratis; el precio publicado de openbanking.io (3 €/mes + 1 €/cuenta); y que un
AISP propio exige **50.000 € de capital inicial**.
