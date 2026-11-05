# PSD2 solo lectura: agregadores, licencia, límites y dos opciones medidas

> **Fecha de consulta de todas las fuentes: 2026-11-05.** Cada afirmación lleva su URL y su
> estado (VERIFICADO / PENDIENTE). Lo que no está publicado se escribe **«no publicado»**; no se
> estima. Este documento **no es asesoramiento jurídico**: las obligaciones se confirman con el
> proveedor y, si hace falta, con un abogado.

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
| **Tink** (grupo Visa) | Declara licencia PSD2 propia y agregar «con nuestra licencia»; **autoridad no verificada hoy** | API de agregación de cuentas; sandbox con registro en consola; 3.000+ conexiones, 19 mercados europeos | **No publicado como cifra**: la página de precios muestra plan «Standard: precio base por usuario y mes» sin importe, y «Enterprise: precio personalizado» | 19 mercados; cobertura por mercado en su documentación | Cuenta + contrato; verificación de dominio y due diligence | <https://tink.com/it/prezzi/> · <https://tink.com/about-us/> · <https://console.tink.com/signup> |
| **Enable Banking** | Actúa como entidad regulada (licencia propia); **autoridad no verificada hoy**. Ofrece modo «TPP con licencia propia» (infraestructura dedicada) para quien ya es AISP | API AIS (cuentas, saldos, movimientos) + **sandbox**; se puede probar antes de firmar contrato (producción restringida enlazando cuentas propias) | **No publicado como cifra**: precio por volumen (nº de cuentas y pagos/mes), con **factura mínima mensual**; presupuesto por correo | Consentimiento máximo típico **180 días**; historial de 90 días (límite de las cuentas); revocación desde su portal de consentimientos | Contrato + KYB de la empresa | <https://enablebanking.com/docs/faq/> · <https://enablebanking.com/> |
| **Salt Edge** | Ofrece soluciones AIS/PSD2; **autoridad que concede su licencia: PENDIENTE de verificar** (no se ha localizado una página de precios: `/pricing` devuelve 404) | API de información de cuentas y sandbox para clientes | **No publicado** | Cobertura europea amplia; cifras concretas de España **PENDIENTE** | Contrato | <https://www.saltedge.com/> |
| **GoCardless (Bank Account Data, ex-Nordigen)** | Proveedor de acceso a datos bancarios; **autoridad y continuidad del producto: PENDIENTE** (la página de precios de GoCardless no menciona el producto de datos; hay referencias de terceros al fin del plan gratuito que **no se usan aquí**) | API AIS documentada históricamente; sandbox | **No publicado** (no verificado) | **PENDIENTE** | Contrato | <https://gocardless.com/> |

**Conclusión de la tabla:** hay al menos **cinco candidatos reales** con AIS y sandbox y dos con
autoridad española verificada (Arcopay y Unnax/Powens). **Ninguno publica precio**: los cinco
remiten a contacto comercial. Cualquier cifra que se escriba sin presupuesto sería inventada.

---

## 3. Bancos españoles con API propia

| Banco | Qué hay verificado | Estado |
|---|---|---|
| **BBVA** (BBVA API Market) | Existe un portal oficial de APIs para empresas: <https://ei.bbva.es/eu/empresas/bbva-api.html>. **No se ha podido leer su catálogo** (página servida en euskera/redirecciones) ni confirmar qué API de AIS ofrece ni sus condiciones | **PENDIENTE** |
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

**No se puede elegir «la más barata que cumpla» porque ninguna de las dos publica precio.** Las dos
implican contrato y factura mínima, así que el coste es **relevante y desconocido**. Por la regla
acordada, esto es **nivel 3: paro y pregunto**.

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
| 1 | Presupuesto con el escenario de uso (2 cuentas, 30 consultas/mes) | Enable Banking y Powens/Unnax | **PENDIENTE (nivel 3)** |
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
| Tink: licencia propia declarada; plan «por usuario y mes» sin cifra | <https://tink.com/it/prezzi/> | 2026-11-05 | VERIFICADO lo publicado; cifra **NO PUBLICADA** |
| Enable Banking: sandbox antes de contrato; precio por volumen con mínimo mensual; consentimiento máximo típico 180 días | <https://enablebanking.com/docs/faq/> | 2026-11-05 | VERIFICADO |
| Salt Edge / GoCardless: AIS y precios | — | 2026-11-05 | **PENDIENTE** |
| APIs propias de BBVA/Santander/CaixaBank para AIS | <https://ei.bbva.es/eu/empresas/bbva-api.html> | 2026-11-05 | **PENDIENTE** |

**No verificado (no se rellena):** precios de cualquier proveedor; cobertura exacta de bancos
españoles de Tink, Salt Edge y Enable Banking; límites numéricos de peticiones; condiciones de las
APIs propias de los bancos; autoridad supervisora de Tink, Salt Edge y Enable Banking.
