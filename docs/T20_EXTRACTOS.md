# T20 — Extractos de banco y conciliación reversible

**Ticket:** `T20 / E11 | T12 | Extractos y conciliación reversible; A07 y duplicados`
**Pantalla del contrato:** S14 · `/cuentas/bancos` (§4) · **Casos de aceptación:** A07 y los duplicados
**Fecha:** 05/10/2026 (ronda 40)
**Ficheros de este ticket:** `backend/app/extractos.py`, `backend/app/routers/extractos_api.py`,
`backend/tests/test_extractos.py`, `backend/tests/datos/extracto_de_ejemplo_*.csv` (4 ficheros
inventados) y este informe.

> **Lo que este ticket NO hace, y el encargo lo prohíbe expresamente: no hay ninguna conexión
> bancaria.** Ni real ni simulada. No hay cliente de HTTP, ni direcciones de banco, ni claves, ni
> consentimiento, ni un proveedor. Lo único que entra es **un fichero que el agricultor ha descargado
> de su banca y ha subido él**. Hay una prueba que lee el código de este ticket y lo comprueba
> (`TestNoHayNingunaConexionBancaria`), porque una promesa que no se comprueba es una promesa que se
> rompe el día que alguien añade «una conexión de solo lectura, que no hace daño». La conexión
> bancaria es el ticket T24.

---

## 1. Qué funciona hoy

### 1.1. La lectura de un extracto (`app/extractos.py`, todo funciones puras)

| Qué hace | Cómo |
|---|---|
| **Lee CSV** con el separador que sea (`;`, `,`, tabulador, `\|`), en UTF-8 o en Windows-1252 | se prueba UTF-8 primero (quita la marca de orden de bytes) y si falla se pasa a cp1252 |
| **Busca las columnas por su etiqueta**, nunca por su letra | «Fecha valor» antes que «Fecha», «Importe (EUR)» vale como «Importe», «Concepto ampliado» como «Concepto»: es la receta del cuaderno de la Junta, y la prueba cambia dos columnas de sitio y comprueba que la lectura es la misma |
| **Encuentra la cabecera dentro del fichero** | un extracto de verdad empieza por el banco, la cuenta y el periodo: la cabecera es la fila que reconoce más columnas (no «la fila 5») |
| **Saca de qué cuenta habla**, **solo con los cuatro últimos dígitos** | hay una prueba que comprueba que el IBAN completo no aparece en nada de lo que devuelve el módulo |
| **Normaliza importes** con la regla del programa (`dinero.de_texto`, la misma que lee una factura) y con el separador que declare el perfil | admite el signo detrás («40,00-») y el separador de miles |
| **Normaliza fechas** | y si el fichero se puede leer de dos maneras y nadie ha dicho el orden, **rechaza la fila** (ver §1.2) |
| **Dice si el dinero entra o sale** | con el signo del importe, con columnas de Debe/Haber, o con una columna de signo («A/CARGO/ABONO») |
| **Rechaza las filas que no entiende, con su motivo y su número de línea** | 10 motivos distintos (`extractos.MOTIVOS_DE_RECHAZO`), y se guarda el texto de la fila para que el agricultor la reconozca |
| **Comprueba la aritmética del saldo** (`saldo de antes + importe = saldo de ahora`) | probando los dos órdenes (hay bancas que exportan de la más nueva a la más vieja) y sin acusar a una fila cuando el saldo del fichero no es el de cada movimiento |
| **Detecta los duplicados** | clave de duplicado por referencia del banco, o por día + importe + signo + concepto + saldo (ver §2) |
| **Propone los traspasos entre cuentas propias** | A07 (ver §3) |
| **Propone las conciliaciones** exactas, agrupadas y parciales, con el porqué de cada una | (ver §4) |
| **Reparte, revisa y deshace** una conciliación | (ver §4 y §5) |
| **Exporta a CSV** con el importe en blanco cuando no consta | (ver §6) |

### 1.2. Lo que **no** se adivina, y lo que sí se lee del propio fichero

Esta es la parte del ticket que más cuidado tiene, porque un extracto mal leído mueve un apunte de mes
o cambia el sentido del dinero. La regla es: **lo que el fichero demuestra, se lee; lo que hay que
elegir, se pregunta**.

| Caso | Qué se hace |
|---|---|
| `03/04/2026` sin haber dicho el orden | **se rechaza la fila** (`fecha_ambigua`) y la pantalla pide el formato. Elegir sería mover un apunte de mes |
| El fichero trae un día del 13 en adelante | **el propio fichero demuestra** que es día/mes/año, y se lee el fichero entero así (`AVISO_FORMATO_DE_FECHA_DEDUCIDO`: «las fechas se han leído como d/m/Y porque las líneas 6, 7, 8 lo demuestran») |
| Un importe sin signo (`40,00`) | **se rechaza** (`sin_signo`)… salvo que **el saldo del fichero lo demuestre**: `1.000,00 + 25,00 = 1.025,00` dice que ese dinero entró (`AVISO_SIGNO_DEDUCIDO`) |
| Una columna con `C` o `D` | **se rechaza** (`signo_desconocido`): «C» es crédito en un banco y cargo en otro, y una letra que significa dos contrarios no se puede leer. Quien tenga ese fichero lo añade a su perfil una vez |
| Número en Debe **y** en Haber en la misma fila | **se rechaza** (`debe_y_haber`): el fichero no dice cuál manda |
| Más casillas que cabeceras | **se rechaza** (`columnas_de_mas`): un concepto con un punto y coma suelto desplaza todo lo de detrás y daría un importe que no es el de esa línea |
| Fichero sin cabeceras | **no se lee nada** y se dice (`sin_cabeceras`): leer por posición es justo lo que este programa no hace |
| Un movimiento de `0,00` | **se rechaza** (`importe_cero`): un movimiento de cero euros no es un movimiento. **Y no es lo mismo que un importe que no consta** |
| Casilla del importe **vacía** | **el movimiento se guarda** con el importe en «no lo sé» (ver §6) |

### 1.3. La API (`app/routers/extractos_api.py`), 16 rutas

```
GET    /api/bancos/cuentas                        las cuentas de la casa
POST   /api/bancos/cuentas                        dar de alta una cuenta (sin ningún dato de banca)
PUT    /api/bancos/cuentas/{id}
GET    /api/bancos/perfiles                       los perfiles de formato guardados (S14)
POST   /api/bancos/perfiles
PUT    /api/bancos/perfiles/{id}
POST   /api/bancos/extractos/vista-previa         LEER SIN GUARDAR: es la lectura previa de S14
POST   /api/bancos/extractos/importar             apuntar los movimientos (los que ya estaban, no)
GET    /api/bancos/movimientos                    con filtros, estado y agregados
GET    /api/bancos/movimientos.csv                el extracto exportado
PUT    /api/bancos/movimientos/{id}               corregir a mano (el importe que no consta)
GET    /api/bancos/movimientos/{id}/propuestas     qué papeles cuadran, y por qué
POST   /api/bancos/movimientos/{id}/conciliar      apuntar (uno a uno, parcial o agrupado)
POST   /api/bancos/movimientos/{id}/desconciliar   deshacer, sin borrar el movimiento
POST   /api/bancos/movimientos/{id}/traspaso       atar o desatar un traspaso propio
GET    /api/bancos/pendientes                      lo que queda por cuadrar
```

---

## 2. Importar dos veces el mismo extracto no duplica movimientos (y si se intenta, se dice)

La clave de duplicado (`extractos.clave_de_duplicado`) se compone de lo que **sí** identifica una línea
de un extracto de verdad:

- si el fichero trae **referencia**, manda la referencia (más la cuenta, más el día);
- si no la trae: **cuenta + día + importe + signo + concepto + saldo**. El saldo es lo que distingue
  dos compras idénticas del mismo día;
- y **el número de veces que esa misma línea aparece dentro del fichero** (`#1`, `#2`…).

Ese último detalle es la trampa del ticket y está en los dos sentidos:

- un extracto con **dos compras idénticas del mismo día** (mismo importe, mismo concepto, sin
  referencia ni saldo) son **dos movimientos**, y sin el contador el segundo se tomaría por repetido
  y **desaparecería un movimiento del banco**;
- y el mismo fichero subido otra vez casa la primera con la primera y la segunda con la segunda: **no
  se cuela ninguna**.

Y lo que ya estaba **se dice**: `separa_lo_que_ya_estaba()` devuelve las dos listas, y la API contesta
`creados`, `repetidos`, `el_fichero_ya_estaba` (por la huella SHA-256 del fichero) y un aviso
(«Este mismo fichero ya lo subiste antes…»). Además, la subida lleva **clave de reenvío**: reenviar la
misma petición devuelve lo que pasó la primera vez y no apunta nada, como en el resto del programa.

---

## 3. A07: un traspaso entre cuentas propias no crea ni un ingreso ni un gasto

`extractos.detectar_traspasos()` propone las parejas que cumplen las cuatro condiciones (cuentas
propias, cuentas distintas, un lado sale y el otro entra por **el mismo importe exacto**, y tres días
como mucho de diferencia). Y es **una propuesta**: el contrato pide que «duplicados y traspasos
propios» sean revisables, así que el agricultor los marca (`POST /movimientos/{id}/traspaso`) y hasta
entonces no cambia ninguna cuenta.

Con las dos patas atadas, `resumen_de_lo_que_ha_entrado_y_salido()` **no las suma**: el A07, con
números medidos sobre los ficheros de ejemplo (dos cuentas, 500 € de una a otra):

| | Sin atar | Atado |
|---|---|---|
| Entradas | **1.708,65 €** | **1.208,65 €** |
| Salidas | **1.126,15 €** | **626,15 €** |
| Traspasos | 0 | **1 (500,00 €)** |

Es decir: 500 € de más por cada lado por haber movido dinero de sitio, que es lo que el vínculo evita.
Y un traspaso **no se propone para conciliar**: el dinero que solo ha cambiado de sitio no salda
ninguna factura.

**Un traspaso con comisión no se detecta solo, y se dice**: las dos patas tienen que ser el mismo
importe exacto (lo pide el contrato: «las comisiones como línea aparte»), así que la comisión se queda
como su propio movimiento, que es la verdad.

---

## 4. La conciliación: muchos a muchos, con parciales y agrupados

`extractos.proponer_conciliaciones()` propone tres casos, y **solo propone lo que cuadra**:

| Tipo | Cuándo | Qué evita |
|---|---|---|
| **Exacta** | un papel al que le falta justo lo que dice el movimiento | — |
| **Agrupada** | un ingreso que salda varios papeles cuya suma **cuadra exacta** | los céntimos que faltarían serían un invento |
| **Parcial** | el movimiento lleva menos que lo que le falta al papel (A06: 40 € de una factura de 121 €) | — |

Cada propuesta lleva **su porqué** (`la referencia está en el concepto`, `el nombre está en la otra
parte`, `el importe cuadra exacto`, `la fecha está cerca`), porque una propuesta sin motivo no se puede
revisar. Y no se propone:

- **una suma que no cuadra**;
- **un papel cuyo pendiente no se sabe** (suponer que le falta todo es inventarse un número);
- **un papel de la otra finca** (se comprueba en la lógica y en la consulta, y da 404, no 403);
- **un ingreso contra una factura que se debe pagar** (el lado del dinero tiene que ser el mismo);
- **un movimiento sin importe**, que se dice con su clave (`no_consta_el_importe`).

Al conciliar, `extractos.revisa_una_conciliacion()` comprueba las siete reglas (importe que no consta,
importe que no vale, pendiente desconocido, más que el pendiente, más que el movimiento, el mismo papel
dos veces, clase equivocada, otra finca) y devuelve los problemas **en palabras**, uno por uno.

Y si no se dice cuánto va a cada papel, `extractos.reparte_lo_que_queda()` lo llena **por orden, del
papel más antiguo al más nuevo**, hasta agotar el dinero: no hay ningún reparto a ojo, que es donde
aparecerían los céntimos perdidos.

---

## 5. Conciliar no crea nada, y deshacer deja todo como estaba (con rastro)

**Conciliar escribe una fila de vínculo y una fila de auditoría, y nada más.** No hay ninguna ruta ni
ninguna función de este ticket que cree una factura, un gasto, un cobro o un movimiento a partir de un
pago. Se comprueba de dos maneras:

- **en la lógica pura**: las imputaciones devueltas apuntan a **los mismos objetos** que se le pasaron
  (identidad, no copia), y su importe no cambia;
- **contando las filas de la base de datos** antes y después de conciliar y deshacer
  (`Factura`, `Cobro`, `FacturaEmitida`): el mismo número (probado en la comprobación de §8).

**Deshacer no borra el movimiento del banco.** El banco ya movió ese dinero y eso no se puede deshacer;
lo que se deshace es a qué papeles se había apuntado. Por eso las conciliaciones **no se borran**: se
marcan como deshechas con `anulada`, `deshecha_en`, `deshecha_por_usuario_id` y `motivo_del_deshacer`,
y el importe vuelve a quedar pendiente en cada papel. Lo que queda escrito:

- **en la auditoría**, dos filas con su acción (`conciliar_movimiento`, `desconciliar_movimiento`), el
  usuario, la fecha y los importes;
- **en el vínculo**, quién deshizo, cuándo y con qué motivo. Se conserva el importe que se había
  imputado: dentro de un año se sabe exactamente qué se deshizo.

Y el deshacer es **exacto**: la prueba hace la cuenta entera (una factura de 121 € con un pago de 40 €
deja 81 € pendientes; al deshacer vuelve a deber **121**, no 81) y comprueba que el mapa de pendientes
queda **igual que antes** de conciliar.

---

## 6. Un importe que no consta NO es cero, de punta a punta

La cadena entera, con la prueba que la cubre en cada salto:

| Salto | Qué pasa | Prueba |
|---|---|---|
| **Fichero** | la casilla del importe vacía deja `importe = None` y `signo = None`, con `importe_no_consta` en `falta`. La fila **se guarda**: la línea del banco existe | `test_en_el_fichero_una_casilla_vacia_es_no_lo_se_y_no_cero` |
| **API** | viaja como `null` en el JSON, y la lista dice `se_puede_conciliar: false` y por qué | `test_un_movimiento_sin_importe_no_se_puede_conciliar_y_se_dice_por_que` |
| **Modelo** | la columna `importe` es `Dinero` y admite nulo; el `signo` va nulo con él (invariante probada sobre todo lo leído: **los dos o ninguno**) | `test_un_movimiento_que_sale_tiene_su_importe_y_su_signo_o_ninguno_de_los_dos` |
| **Cálculo** | no se suma como cero: se **cuenta** (`sin_importe`) y se dice aparte. `lo_que_falta_por_conciliar` devuelve `None`, no `0,00` | `test_no_se_suma_como_si_fuera_cero` |
| **Pantalla** | el estado del movimiento es `no_se_puede_conciliar`, y no `sin_conciliar` (que querría decir «se puede, pero no lo has hecho») | `test_el_estado_de_un_movimiento_dice_a_medias_o_conciliado` |
| **Exportación** | el CSV escribe la casilla **en blanco** y una columna que dice qué falta; **nunca `0,00`** | `test_en_el_csv_que_se_exporta_sale_en_blanco_y_nunca_como_cero` |

Y como el programa dice «en esta línea no consta el importe», **hay una puerta para escribirlo**:
`PUT /api/bancos/movimientos/{id}`. Con dos reglas: no se puede corregir un movimiento que ya tiene
dinero apuntado (se dice que hay que deshacer la conciliación primero, con la instrucción) y un importe
**sin decir si entra o sale** se rechaza, porque un movimiento así no se puede sumar.

---

## 7. Aislamiento entre fincas

`explotacion_id` va en las cinco tablas, todas las consultas filtran por él y todo lo que llega por la
URL pasa por `obtener_de_la_explotacion()` (**404, no 403**). Se comprueba en los tres sitios:

- **la lógica pura**: un movimiento de la finca 1 no propone nada de la finca 2, y conciliar a mano con
  un papel de otra finca se rechaza con su problema;
- **la lectura**: cada fila leída lleva su `explotacion_id` desde el fichero;
- **la API** (cuando esté integrada): la cuenta de otra finca da 404, la lista de movimientos sale
  vacía, y ni conciliar ni deshacer ni ver propuestas de un movimiento ajeno responden otra cosa que
  404.

---

## 8. Qué he comprobado y cómo (comandos y números)

### 8.1. Las pruebas del ticket

```bash
cd F:\EspacioCodigo\CueDigital\backend
..\.venv\Scripts\python.exe -m pytest tests/test_extractos.py -q
```

**89 pruebas: 78 en verde, 11 saltadas, 0 rojos.** 2,3 segundos.

Las 11 saltadas **dicen qué falta**, una por una, y no se quedan en verde sin comprobar nada:

- **9** de la parte que guarda: `faltan por integrar: tabla cuentas_bancarias, tabla
  perfiles_de_extracto, tabla movimientos_de_extracto, tabla conciliaciones_de_movimiento, tabla
  importaciones_de_extracto`;
- **1** de los textos: lista **las 59 claves** que pide el router y que todavía no están en
  `textos.py`;
- **1** del `.gitignore` (ver §9.5).

### 8.2. El recorrido entero, con las tablas propuestas, en una base temporal

Como las tablas todavía no están en `models.py`, la API **no se podía probar** con la suite. Para no
entregar un router escrito a ciegas, se comprobó antes de entregarlo con un guion fuera del repositorio
(en el temporal de la máquina, no es un fichero del proyecto) que:

1. apunta la base a un SQLite temporal;
2. **define las cinco tablas propuestas tal y como están escritas en §9.1** (lo comprobado es
   exactamente lo propuesto);
3. mete el router en la aplicación de verdad y recorre el camino completo.

Resultado: **48 comprobaciones, todas en verde**, con esto dentro:

```
OK  la vista previa lee los 7 movimientos          OK  el alta de una cuenta
OK  la vista previa no guarda nada                 OK  se apuntan 7 movimientos al importar
OK  subir el mismo fichero no añade ninguno        OK  y dice cuántos ya estaban (7)
OK  y dice que ese fichero ya estaba               OK  reenviar la misma subida no apunta nada
OK  las dos cuentas dan 9 movimientos              OK  se marca el traspaso y quedan los dos lados atados
OK  la propuesta es exacta y dice por qué          OK  se apunta medio pago (500 de 1.205,40)
OK  el movimiento queda conciliado a medias        OK  y le queda por apuntar el resto (705,40)
OK  conciliar y deshacer NO crean ningún documento OK  el movimiento sigue apuntado después de deshacer
OK  el dinero vuelve a estar pendiente (0,00)      OK  el rastro guarda quién concilió y quién deshizo
OK  la conciliación deshecha queda con su fecha, su autor y su motivo
OK  un movimiento salda dos papeles a la vez       OK  la suma de lo apuntado es la dicha (705,40)
OK  el resto se reparte solo hasta agotar el movimiento
OK  conciliar lo ya conciliado se dice (422)       OK  el importe que no consta sale en blanco en el CSV
OK  corregir un importe sin decir el signo se rechaza (422)
OK  se corrige el importe que no constaba          OK  y el movimiento queda utilizable
OK  la cuenta de una finca no se puede tocar desde otra (404)
OK  los movimientos de una finca no se ven desde otra (0)
OK  un movimiento de otra finca no se puede tocar (404)
```

### 8.3. Las pruebas **muerden**: cuatro roturas a propósito

No basta con que una prueba esté en verde: hay que ver que se pone roja cuando la regla se rompe. Se
rompió el código a propósito cuatro veces, se miró el rojo y **se dejó como estaba**:

| Rotura a propósito | Qué se puso rojo |
|---|---|
| Quitar el contador de apariciones de la clave de duplicado | `test_dos_lineas_identicas_del_mismo_dia_son_dos_movimientos` |
| Que el resumen no mire la marca del traspaso en los movimientos guardados | `test_lo_marcado_en_los_movimientos_basta_para_no_contarlo` |
| Convertir en cero el importe que no consta | 5 pruebas de `TestUnImporteQueNoConstaNoEsCero` (y la del traspaso) |
| Proponer también las sumas que **no** cuadran | `test_una_suma_que_no_cuadra_no_se_propone` y la agrupada |
| Quitar la comprobación de finca al conciliar a mano | `test_conciliar_a_mano_con_un_papel_de_otra_finca_se_rechaza` |

Dos de esas roturas **enseñaron algo** y están arregladas en las pruebas:

- la del traspaso no mordía al principio, porque todas las pruebas le pasaban también la lista de
  traspasos y el resumen la mira; se añadió la prueba que solo usa **las filas ya marcadas**, que es el
  caso real de la pantalla (cuando el traspaso ya está guardado, la lista ya no existe);
- la del `.gitignore` (§9.5) salió de mirar si los ficheros de ejemplo viajaban con el código.

### 8.4. Lo que he mirado a mano, además

- El guardián del rastro (`tests/test_las_etiquetas_del_rastro_caben.py`) lee **mis** etiquetas de
  auditoría al recorrer `app/**/*.py`: son textos fijos (`crear_cuenta_bancaria`,
  `guardar_perfil_de_extracto`, `importar_extracto`, `corregir_movimiento`, `conciliar_movimiento`,
  `desconciliar_movimiento`, `marcar_traspaso_propio`, `quitar_traspaso_propio`), todas de menos de 80
  caracteres y sin tildes. Hay una prueba propia que lo vuelve a comprobar.
- `test_ficheros_de_texto.py` recorre los `.csv` de `backend/tests/datos/`: los cuatro extractos de
  ejemplo son UTF-8 sin marca de orden de bytes (comprobado).

---

## 9. Cambios que hay que integrar (bloques literales)

Todo lo de este apartado es **del coordinador**: son ficheros compartidos que este ticket no escribe.
Están escritos para copiarse tal cual.

### 9.1. `backend/app/models.py` — las cinco tablas

Van juntas y en este orden (las importaciones → las cuentas → los perfiles → los movimientos → las
conciliaciones). Se propone colocarlas **al final del bloque del dinero** (después de `Cobro` y
`AjusteDeEntrega`), porque es donde vive lo que ya está hecho sobre facturas y cobros.

```python
class CuentaBancaria(Base):
    """Una cuenta de la casa. **No se pide ningún dato de la banca**: ni claves, ni acceso.

    Lo único que se guarda para reconocerla es su nombre, el banco (si se quiere apuntar) y **los
    cuatro últimos dígitos del número**. El número completo no hace falta para cuadrar nada y sí es un
    dato que no queremos tener guardado: por eso el esquema de entrada lo recorta antes de guardarlo
    (`CuentaBancariaEntrada._solo_los_cuatro_ultimos`) y hay una prueba que comprueba que el IBAN
    completo no aparece en nada de lo que devuelve el lector.
    """

    __tablename__ = "cuentas_bancarias"
    __table_args__ = (
        # Reenviar la misma alta (el móvil sin cobertura) devuelve la cuenta que ya había, no otra.
        Index(
            "uq_cuenta_bancaria_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("clave_de_reenvio IS NOT NULL"),
            postgresql_where=text("clave_de_reenvio IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    banco: Mapped[str | None] = mapped_column(String(80))
    # Los cuatro últimos dígitos, y solo esos: es lo que se lee en un extracto.
    ultimos_digitos: Mapped[str | None] = mapped_column(String(4))
    # Si es una cuenta de la casa. **Es lo que hace que un traspaso propio no cuente como ingreso ni
    # como gasto** (A07): un pago a un proveedor y un cobro del mismo importe no son un traspaso.
    propia: Mapped[bool] = mapped_column(Boolean, default=True)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    notas: Mapped[str | None] = mapped_column(Text)
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class PerfilDeExtracto(Base):
    """Cómo está escrito el extracto de este banco (S14: «perfiles de formato guardables»).

    **Los tres campos que pueden cambiarle el sentido a un número van en su propia columna y admiten
    nulo**: el separador decimal, el formato de la fecha y qué quiere decir un importe sin signo.
    Nulo es «no me lo has dicho», y con eso el programa lee lo que el propio fichero demuestra y
    **rechaza** lo que no, en vez de elegir por su cuenta.

    Y las columnas también van en columnas y no en un JSON, por la regla de siempre en este programa:
    **un dato con nombre va en su sitio**, no dentro de un texto libre. Aquí, además, tiene una
    consecuencia práctica: el perfil se puede corregir desde el formulario campo por campo.
    """

    __tablename__ = "perfiles_de_extracto"

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    cuenta_id: Mapped[int | None] = mapped_column(ForeignKey("cuentas_bancarias.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    delimitador: Mapped[str] = mapped_column(String(4), default=";")
    decimal: Mapped[str | None] = mapped_column(String(1))
    formato_de_fecha: Mapped[str | None] = mapped_column(String(20))
    # en_el_importe | debe_haber | en_su_columna (ver `extractos.SIGNOS`/`ESTILOS_DE_SIGNO`)
    estilo_del_signo: Mapped[str] = mapped_column(String(30), default="en_el_importe")
    # entra | sale | nulo (nulo es «no me lo has dicho»)
    sin_signo_quiere_decir: Mapped[str | None] = mapped_column(String(10))
    # Lo que escribe el fichero cuando el dinero entra y cuando sale, con `|` de separador
    # («A|ABONO|HABER»), para el estilo que trae el signo en su propia columna.
    dicen_que_entra: Mapped[str | None] = mapped_column(String(200))
    dicen_que_sale: Mapped[str | None] = mapped_column(String(200))
    # El nombre de cada dato **en este fichero** («Fecha», «F. Valor», «Concepto ampliado»…).
    columna_fecha: Mapped[str | None] = mapped_column(String(80))
    columna_fecha_valor: Mapped[str | None] = mapped_column(String(80))
    columna_concepto: Mapped[str | None] = mapped_column(String(80))
    columna_importe: Mapped[str | None] = mapped_column(String(80))
    columna_saldo: Mapped[str | None] = mapped_column(String(80))
    columna_referencia: Mapped[str | None] = mapped_column(String(80))
    columna_debe: Mapped[str | None] = mapped_column(String(80))
    columna_haber: Mapped[str | None] = mapped_column(String(80))
    columna_signo: Mapped[str | None] = mapped_column(String(80))
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class ImportacionDeExtracto(Base):
    """Una subida de un fichero de extracto: qué se leyó, qué se apuntó y de quién era el fichero.

    Es el «original, extracción, campos corregidos, autor y fecha» del contrato (§2), con **una
    decisión que se dice**: el fichero **no se guarda**. Un extracto lleva el número de cuenta
    completo y los nombres de terceros, y los movimientos guardados son ya todo lo que hace falta
    (fecha, concepto, importe, referencia y saldo). Lo que sí se guarda es **su huella**, para poder
    decir «este mismo fichero ya lo importaste», que es lo que pide el ticket.

    Los tres campos que el agricultor haya corregido del perfil se copian aquí: así, dentro de un año,
    se sabe **con qué lectura** se apuntó cada movimiento, aunque después se cambie el perfil.
    """

    __tablename__ = "importaciones_de_extracto"
    __table_args__ = (
        Index(
            "uq_importacion_de_extracto_reenvio",
            "explotacion_id",
            "clave_de_reenvio",
            unique=True,
            sqlite_where=text("clave_de_reenvio IS NOT NULL"),
            postgresql_where=text("clave_de_reenvio IS NOT NULL"),
        ),
        # La huella se busca en cada subida: es lo que dice «este fichero ya estaba».
        Index("ix_importacion_de_extracto_huella", "explotacion_id", "huella"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas_bancarias.id"), index=True)
    perfil_id: Mapped[int | None] = mapped_column(ForeignKey("perfiles_de_extracto.id"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    # El nombre del fichero **solo para enseñarlo**: el programa no guarda su contenido ni lo usa
    # como ruta (la regla de siempre, ver `adjuntos.py`).
    fichero_nombre: Mapped[str | None] = mapped_column(String(200))
    huella: Mapped[str | None] = mapped_column(String(64))
    lineas_leidas: Mapped[int] = mapped_column(Integer, default=0)
    movimientos_creados: Mapped[int] = mapped_column(Integer, default=0)
    movimientos_repetidos: Mapped[int] = mapped_column(Integer, default=0)
    movimientos_sin_importe: Mapped[int] = mapped_column(Integer, default=0)
    filas_rechazadas: Mapped[int] = mapped_column(Integer, default=0)
    decimal: Mapped[str | None] = mapped_column(String(1))
    formato_de_fecha: Mapped[str | None] = mapped_column(String(20))
    sin_signo_quiere_decir: Mapped[str | None] = mapped_column(String(10))
    clave_de_reenvio: Mapped[str | None] = mapped_column(String(120))
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class MovimientoDeExtracto(Base):
    """Una línea del extracto, ya apuntada. **Importar no crea ningún ingreso ni ningún gasto.**

    Es el hecho del banco, tal cual: su día, su concepto, su importe, su referencia y el saldo que
    quedó después. No es un ingreso ni un gasto de la explotación —eso lo dice el signo, y lo dice el
    banco, no el programa— y **no es un apunte del cuaderno**: mover dinero de una cuenta a otra no
    puede aparecer en el margen de un cultivo.

    ## Las dos columnas que pueden quedar nulas, y por qué

    - **`importe`**: nulo es «no consta». Es la regla del ticket de punta a punta, y se apoya en que la
      columna es `Dinero` (texto decimal exacto, ver `dinero.ImporteExacto`), que admite nulo sin
      convertir nada en cero.
    - **`signo`**: nulo **solo** cuando el importe no consta. Los dos van juntos o no va ninguno: un
      movimiento con importe y sin signo sería un movimiento del que no se sabe si suma o resta, y ese
      movimiento no se puede sumar, ni conciliar, ni cuadrar. Hay una prueba que recorre todo lo leído
      y comprueba que esa pareja nunca se rompe.

    ## Y las dos que hacen que no se cuente dos veces

    - **`clave_de_duplicado`**, con índice único por finca y cuenta: subir el mismo extracto dos veces
      no puede apuntar la misma línea dos veces, y no depende de que alguien se acuerde de mirarlo.
    - **`pareja_de_traspaso_id`**: las dos patas de un traspaso propio se apuntan la una a la otra. Es
      lo que hace que el resumen las deje fuera del ingreso y del gasto (A07), y también se cumple
      cuando se lee lo guardado, sin necesitar la lista de traspasos.
    """

    __tablename__ = "movimientos_de_extracto"
    __table_args__ = (
        # **El índice que impide apuntar dos veces la misma línea del banco.** Es parcial a propósito:
        # si algún día una línea se anula, su clave tiene que quedar libre.
        Index(
            "uq_movimiento_de_extracto",
            "explotacion_id",
            "cuenta_id",
            "clave_de_duplicado",
            unique=True,
        ),
        Index("ix_movimiento_de_extracto_fecha", "explotacion_id", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuentas_bancarias.id"), index=True)
    importacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("importaciones_de_extracto.id"), index=True
    )
    fecha: Mapped[dt.date | None] = mapped_column(Date, index=True)
    fecha_valor: Mapped[dt.date | None] = mapped_column(Date)
    concepto: Mapped[str | None] = mapped_column(Text)
    referencia: Mapped[str | None] = mapped_column(String(120))
    # Nulo es «no consta el importe». **Nunca un cero de relleno.**
    importe: Mapped[Decimal | None] = mapped_column(Dinero)
    # entra | sale. Nulo **solo** cuando el importe no consta.
    signo: Mapped[str | None] = mapped_column(String(6))
    saldo: Mapped[Decimal | None] = mapped_column(Dinero)
    # Lo que identifica la línea dentro del fichero del banco (ver `extractos.clave_de_duplicado`).
    clave_de_duplicado: Mapped[str] = mapped_column(String(300))
    # La otra pata de un traspaso entre dos cuentas propias (A07), y la marca que lo saca del resumen.
    pareja_de_traspaso_id: Mapped[int | None] = mapped_column(
        ForeignKey("movimientos_de_extracto.id"), index=True
    )
    # Lo que se escribió a mano y por qué: un importe que no consta se puede corregir, y tiene que
    # quedar dicho que ese número no lo trajo el banco.
    corregido: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_de_la_correccion: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())


class ConciliacionDeMovimiento(Base):
    """Cuánto de un movimiento del banco va contra un papel. **Muchos a muchos.**

    Una fila por pareja (movimiento, papel) y con su importe. Con eso salen los tres casos que el
    contrato pide, sin ninguna tabla más:

    - **pago parcial**: una fila con un importe menor que lo que le falta al papel (A06: 40 € de 121);
    - **pago agrupado**: varias filas del mismo movimiento apuntando a varios papeles;
    - **varios pagos a un papel**: varias filas de movimientos distintos apuntando al mismo papel.

    ## Lo que NO hace, y es la regla del ticket

    **Conciliar no crea ningún documento.** Esta tabla apunta a papeles que ya existen (`clase` +
    `documento_id`): ni una factura, ni un gasto, ni un cobro, ni un movimiento. `clase` es una lista
    cerrada (`cobro`, `factura_emitida`, `factura_de_compra`; lo que falte —un gasto sin factura, una
    inversión, una nómina— es del T13 y está declarado en `extractos.CLASES_QUE_FALTAN`).

    ## Y deshacer no borra

    La fila **no se borra al deshacer**: se marca `anulada` y se queda con **quién** la deshizo
    (`deshecha_por_usuario_id`), **cuándo** (`deshecha_en`) y **con qué motivo**
    (`motivo_del_deshacer`), además de conservar el importe que se había imputado. El índice único es
    parcial (`anulada = 0`), así que deshacer deja la pareja libre para volver a conciliarla. El
    movimiento del banco no se toca: el banco ya movió ese dinero.
    """

    __tablename__ = "conciliaciones_de_movimiento"
    __table_args__ = (
        Index(
            "uq_conciliacion_de_movimiento",
            "explotacion_id",
            "movimiento_id",
            "clase",
            "documento_id",
            unique=True,
            sqlite_where=text("anulada = 0"),
            postgresql_where=text("anulada = false"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    explotacion_id: Mapped[int] = mapped_column(ForeignKey("explotaciones.id"), index=True)
    movimiento_id: Mapped[int] = mapped_column(
        ForeignKey("movimientos_de_extracto.id"), index=True
    )
    # cobro | factura_emitida | factura_de_compra (y lo que traiga el T13)
    clase: Mapped[str] = mapped_column(String(30))
    documento_id: Mapped[int] = mapped_column(Integer, index=True)
    # Lo que de este movimiento se apunta a ese papel. Obligatorio: una conciliación sin importe no
    # dice nada, y el programa reparte por orden cuando el agricultor no dice cuánto.
    importe: Mapped[Decimal] = mapped_column(Dinero, nullable=False)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    anulada: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo_de_anulacion: Mapped[str | None] = mapped_column(Text)
    deshecha_en: Mapped[dt.datetime | None] = mapped_column(DateTime)
    deshecha_por_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    motivo_del_deshacer: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[dt.datetime] = mapped_column(DateTime, server_default=func.now())
```

**Comprobado contra PostgreSQL**: no (el motor de Docker sigue bloqueado, como en la ronda anterior).
Lo que sí se ha cuidado es lo que rompe en PostgreSQL y no en SQLite: **ningún texto de longitud libre
en una columna con tope** (de ahí los `String(n)` de arriba, y el guardián de las etiquetas del
rastro), y las columnas de dinero con el tipo `Dinero` del programa.

### 9.2. `backend/app/schemas.py` — los esquemas de la API

**Están escritos dentro de `app/routers/extractos_api.py`**, y es a propósito: `schemas.py` es un
fichero compartido y sin sus esquemas el router no se podría ni ejecutar (ni comprobar). Se mueven
**tal cual** cuando se integren: son las clases `CuentaBancariaEntrada/Salida`,
`PerfilDeExtractoEntrada/Salida`, `TextoDeUnaFila`, `AvisoDeLaLectura`, `MovimientoLeido`,
`TraspasoPropuesto`, `VistaPreviaDelExtracto`, `ResultadoDeLaImportacion`, `MovimientoSalida`,
`ListaDeMovimientos`, `DocumentoPendiente`, `ImputacionEntrada`, `ConciliacionEntrada`,
`ConciliacionHecha`, `ResultadoDeLaConciliacion`, `CorreccionDeUnMovimiento` y `TraspasoEntrada`
(están en el fichero, en el bloque «Los esquemas de esta API», con este mismo aviso escrito).

Si se prefiere dejarlos donde están, **también vale**: el router funciona igual, y así lo comprobado es
lo entregado. Lo que no se puede es tenerlos en los dos sitios.

### 9.3. `backend/app/main.py` — registrar el router, **y dónde**

```python
# Los extractos de banco y la conciliación (T20, 05/10/2026): subir un fichero que el agricultor ha
# descargado de su banca, verlo antes de apuntarlo y cuadrarlo con las facturas y los cobros. Va detrás
# de ventas_api porque concilia contra sus facturas emitidas y sus cobros. **No se conecta ningún
# banco**: solo se lee el fichero que se sube.
app.include_router(extractos_api.router)
```

y el `import` correspondiente arriba, con los demás:

```python
from .routers import extractos_api
```

> **Cuidado con la línea, y esto se descubrió comprobándolo**: el montaje de la pantalla
> (`app.mount("/", StaticFiles(...))`) está **al final** de `main.py` y **se come cualquier ruta que se
> registre después**. Registrando el router después de esa línea, **las 16 rutas contestan 405 sin dar
> ningún error** (lo dice el propio comentario de `main.py`, y aquí se ha visto en la comprobación).
> El `include_router` va con los demás, **antes** del montaje.

### 9.4. `backend/app/textos.py` — los textos

Van en `textos.py` y **no en el router** (la regla de siempre), con la misma forma que los de la
maquinaria y las semillas: un diccionario propio y su `update` al final. Ninguna lleva jerga, y las que
bloquean dicen qué hacer.

```python
# --------------------------------------------------------------------------
# Los extractos de banco y la conciliación (T20, 05/10/2026)
# --------------------------------------------------------------------------
#
# **Ninguna de estas frases es una explicación técnica**: son las que el agricultor lee cuando una
# línea de su extracto no se ha podido leer (y tiene que poder arreglarla) o cuando el programa le
# propone a qué factura va un dinero. Las claves las pide `app/routers/extractos_api.py`, y hay una
# prueba que las lee de allí y avisa de las que falten.
MENSAJES_DE_LOS_EXTRACTOS: dict[str, str] = {
    # --- una fila que no se entiende (cada motivo dice qué mirar) ---
    "T20_sin_fecha": "Una línea del extracto no trae fecha, así que no se ha apuntado. Mira esa línea en el fichero de tu banco.",
    "T20_fecha_dudosa": "La fecha de una línea se puede leer de dos maneras (día/mes o mes/día) y no se ha adivinado. Dinos cómo escribe las fechas tu banco y vuelve a subir el extracto.",
    "T20_fecha_ilegible": "La fecha de una línea no se ha podido leer. Mira esa línea en el fichero de tu banco.",
    "T20_sin_signo": "En una línea, el importe no dice si el dinero entra o sale, y no se ha adivinado. Dinos cómo lo escribe tu banco y vuelve a subir el extracto.",
    "T20_debe_y_haber": "Una línea trae número en la columna de debe y en la de haber a la vez, así que no se sabe qué hizo ese dinero. Mira esa línea en el fichero de tu banco.",
    "T20_signo_desconocido": "Una línea trae una señal de cargo o abono que este programa no conoce. Dinos qué quiere decir y vuelve a subir el extracto.",
    "T20_importe_cero": "Una línea del extracto trae 0,00 € y no se ha apuntado: un movimiento de cero euros no es un movimiento.",
    "T20_importe_ilegible": "El importe de una línea no se ha podido leer. Mira esa línea en el fichero de tu banco y escríbelo a mano.",
    "T20_columnas_de_mas": "Una línea trae más columnas que la cabecera, así que no se sabe qué número es cada cosa. Mira esa línea en el fichero de tu banco.",
    "T20_sin_cabeceras": "En este fichero no se encuentran las cabeceras de las columnas, así que no se sabe qué es cada número. Descarga el extracto otra vez desde tu banca.",
    "T20_esa_linea_no_se_ha_entendido": "Hay una línea del extracto que no se ha podido entender y no se ha apuntado. Mira la vista previa para ver cuál es.",
    # --- los avisos de la lectura ---
    "T20_no_se_sabe_de_que_cuenta_es": "En el fichero no se lee de qué cuenta es. Elige la cuenta tú antes de apuntarlo.",
    "T20_hay_importes_que_no_constan": "En las líneas {lineas} no consta el importe: se apuntan sin él y no cuentan en los totales. Escribe el importe a mano en cada una cuando lo sepas.",
    "T20_hay_filas_que_no_se_entienden": "Hay líneas del extracto que no se han entendido (las {lineas}) y no se han apuntado. Mira la vista previa para ver qué pasa en cada una.",
    "T20_el_saldo_no_cuadra": "El saldo de las líneas {lineas} no cuadra con el movimiento anterior. Revisa esas líneas: puede haberse leído mal una columna.",
    "T20_el_orden_de_las_filas_es_dudoso": "Los saldos de este fichero no cuadran ni de arriba abajo ni de abajo arriba. Comprueba que no te hayas bajado otro extracto.",
    "T20_el_formato_de_la_fecha_no_esta_declarado": "No nos has dicho cómo escribe las fechas tu banco y en este fichero no se puede saber. Dínoslo y vuelve a subir el extracto.",
    "T20_el_formato_de_la_fecha_se_ha_deducido": "Las fechas se han leído como {formato} porque las líneas {lineas} lo demuestran.",
    "T20_el_signo_se_ha_deducido_del_saldo": "En las líneas {lineas} el importe no trae signo, y se ha leído por el saldo del fichero. Revísalo antes de dar por bueno el extracto.",
    "T20_hay_filas_sin_signo": "En las líneas {lineas} el importe no dice si el dinero entra o sale. Dinos cómo lo escribe tu banco y vuelve a subir el extracto.",
    # --- al conciliar ---
    "T20_el_movimiento_no_dice_cuanto": "En este movimiento no consta el importe, así que no se sabe cuánto se puede apuntar a un papel. Escribe el importe y vuelve a intentarlo.",
    "T20_esa_cantidad_no_vale": "Esa cantidad no vale para apuntarla a un papel. Escribe un importe mayor que cero.",
    "T20_no_se_sabe_cuanto_le_falta": "De ese papel no se sabe cuánto le falta por pagar o por cobrar, así que no se puede decir qué parte le toca. Escribe su importe primero.",
    "T20_mas_de_lo_que_le_falta": "Estás apuntando más dinero del que le falta a ese papel. Apunta lo que le falta y deja el resto sin apuntar.",
    "T20_mas_de_lo_que_dice_el_movimiento": "Estás apuntando más dinero del que dice este movimiento del banco. Quita papeles o apunta menos cantidad en cada uno.",
    "T20_el_mismo_papel_dos_veces": "Ese papel aparece dos veces en la misma conciliación. Deja una sola vez.",
    "T20_ese_papel_no_va_por_ese_lado": "Ese papel no se paga con este movimiento: lo que entra salda lo que te deben y lo que sale paga lo que debes. Mira de qué papel se trata.",
    "T20_eso_no_esta_en_tu_cuaderno": "Eso no está en tu cuaderno. Elige un papel de tu finca.",
    "T20_no_se_ha_podido_apuntar_eso": "No se ha podido apuntar eso a ningún papel. Míralo y vuelve a intentarlo.",
    "T20_no_hay_nada_que_apuntar": "No hay ningún papel al que apuntar este dinero. Apunta antes la factura o el cobro.",
    "T20_no_hay_nada_que_deshacer": "Este movimiento no tiene nada apuntado que deshacer.",
    "T20_no_se_puede_corregir_conciliado": "Este movimiento ya tiene dinero apuntado a un papel, así que no se puede cambiar. Deshaz primero la conciliación y vuelve a intentarlo.",
    "T20_dinos_si_entra_o_sale": "Dinos también si ese dinero entró o salió, porque un importe sin eso no se puede sumar.",
    "T20_correccion_a_mano": "Corregido a mano",
    "T20_deshacer_a_mano": "Se deshizo a mano",
    # --- qué es cada papel, y por qué se propone ---
    "T20_que_es_una_factura_nuestra": "Una factura tuya, de lo que has vendido",
    "T20_que_es_un_cobro_sin_factura": "Un dinero que entró y todavía no sabes de qué factura es",
    "T20_que_es_una_factura_de_compra": "Una factura de lo que has comprado",
    "T20_porque_la_referencia_esta_en_el_concepto": "la referencia está en el concepto del movimiento",
    "T20_porque_el_nombre_esta_en_el_concepto": "el nombre de la otra parte está en el concepto",
    "T20_porque_el_importe_cuadra": "el importe cuadra exacto",
    "T20_porque_la_suma_cuadra": "la suma de los papeles cuadra exacto",
    "T20_porque_la_fecha_esta_cerca": "la fecha está cerca",
    "T20_porque_la_fecha_esta_lejos": "la fecha no está tan cerca",
    "T20_porque_no_se_sabe": "no se sabe por qué",
    # --- el traspaso propio (A07) ---
    "T20_parece_un_traspaso_tuyo": "Estos dos movimientos parecen el mismo dinero pasado de una cuenta tuya a otra. Si es así, dilos como traspaso para que no cuenten como ingreso ni como gasto.",
    "T20_el_traspaso_necesita_dos_movimientos": "Un traspaso son dos movimientos: elige el otro. Si te has equivocado, quita el traspaso.",
    "T20_un_traspaso_va_entre_dos_cuentas": "Un traspaso va entre dos cuentas distintas. Elige un movimiento de otra cuenta tuya.",
    "T20_eso_no_parece_un_traspaso": "Estos dos movimientos no son el mismo dinero: para ser un traspaso tienen que ser del mismo importe y uno tiene que entrar y el otro salir. Míralos otra vez.",
    "T20_esos_movimientos_ya_estan_atados": "Uno de esos dos movimientos ya está atado a otro traspaso. Quita ese traspaso primero.",
    "T20_traspaso_atado": "Atados: este dinero ya no cuenta como ingreso ni como gasto, solo ha cambiado de cuenta.",
    "T20_ese_movimiento_no_es_un_traspaso": "Este movimiento no está atado a ningún traspaso, así que no hay nada que quitar.",
    "T20_traspaso_quitado": "Quitado el traspaso: estos dos movimientos vuelven a contar cada uno por su lado.",
    # --- lo que se apuntó, dicho con su número ---
    "T20_apuntado_contra_un_papel": "Apuntados {importe} de este movimiento a {cuantos} papel(es).",
    "T20_todavia_queda_dinero_sin_apuntar": "Todavía quedan {sobrante} de este movimiento sin apuntar a ningún papel.",
    "T20_deshecho_el_movimiento_sigue_apuntado": "Deshecho: {importe} vuelven a estar pendientes. El movimiento del banco sigue apuntado igual.",
    # --- la subida ---
    "T20_el_mismo_fichero_ya_estaba": "Este mismo fichero ya lo subiste antes: no se ha apuntado nada nuevo. Si tu banco ha añadido movimientos, vuelve a descargar el extracto y súbelo otra vez.",
    "T20_los_movimientos_que_ya_estaban": "De este extracto, {cuantos} movimientos ya estaban apuntados y no se han repetido.",
    "T20_esa_importacion_ya_estaba_hecha": "Esa subida ya se había hecho antes: no se ha apuntado nada nuevo.",
}
MENSAJES.update(MENSAJES_DE_LOS_EXTRACTOS)
```

**Son 59 claves**, y se ha comprobado que **están las 59 que pide el router y ninguna de más** (leyendo
las claves del router con una expresión regular y comparándolas con este bloque). Hay una prueba
(`test_los_textos_que_pide_el_router_estan_en_textos_py`) que hace esa misma comparación y hoy se salta
listando las que faltan; en cuanto estén en `textos.py`, comprueba además que ninguna está vacía. Y
`textos_visibles()` las revisa sola (van dentro de `MENSAJES`), así que pasan por el test de jerga: se
ha comprobado que **ninguna de las 59 lleva una palabra prohibida**.

### 9.5. `.gitignore` — que los extractos de ejemplo viajen

```gitignore
# Los extractos de ejemplo de las pruebas del T20: son ficheros que el programa LEE (como los de
# `data/`), no ficheros que escribe. Sin esta línea, la suite del T20 falla en cualquier copia recién
# hecha y aquí no se nota.
!backend/tests/datos/
```

Es la excepción que el propio `.gitignore` ya tiene para `data/zv_cyl.csv` y `data/municipios_cyl.csv`,
aplicada a los cuatro ficheros que este ticket añade en `backend/tests/datos/`. El fichero de ejemplo
del cuaderno de la Junta (`.xlsx`) no está afectado porque la regla es `*.csv`.

### 9.6. La pantalla (S14, `/cuentas/bancos`): **no está hecha**, y se dice

El mapa del ticket deja la pantalla «dentro de la de gastos o en `web/react/pantallas/extractos.js`, a
decidir con T13», y `web/react/**` no es fichero de este ticket. Lo que hay es **todo lo que la
pantalla necesita**: la vista previa enseña las líneas entendidas con lo que falta en cada una, las
que no se entienden **con su motivo y su número de fila**, los avisos con sus números de línea, el
formato de fecha y el signo que se han deducido, los traspasos propuestos, y las cuentas de entradas,
salidas e importes que no constan. Y cada movimiento sale con su estado, lo que le queda por cuadrar y
por qué no se puede conciliar.

Lo que falta para que el agricultor lo vea: la pantalla, sus dos o tres líneas de menú y enrutador en
`app.js`, su fila en la caché de `service-worker.js`, y las pruebas de JavaScript que **pulsen los
botones** (el patrón de `tests_js/interfaz.test.js`). No se ha escrito nada de eso para no invadir los
ficheros compartidos.

---

## 10. Lo que no se ha podido comprobar, y con quién queda

| Qué | Por qué | De quién depende |
|---|---|---|
| **Las 11 pruebas saltadas** | las cinco tablas no están en `models.py` (9), faltan los textos (1) y falta la línea del `.gitignore` (1) | del coordinador (§9.1, §9.4 y §9.5) |
| **Que la API funcione dentro de la suite** | lo mismo. Se ha comprobado **fuera** de la suite, con el guion de §8.2, contra las tablas propuestas | del coordinador |
| **Que los textos salgan en pantalla** | faltan las 60 claves en `textos.py` y no hay pantalla | del coordinador (§9.4 y §9.6) |
| **PostgreSQL** | el motor de Docker sigue sin responder (ronda anterior). No se ha tocado ningún volumen | del entorno |
| **La suite de Python entera** | tardaba ~6 minutos y el encargo prohíbe correrla | del coordinador |
| **OFX, QFX, CAMT.053 y la Norma 43** | **no se han escrito, y a propósito**: hace falta un fichero de ejemplo de verdad para escribirlos y probarlos, y no se copia el de ningún agricultor. Están enumerados con su motivo en `extractos.FORMATOS_QUE_FALTAN`, y mientras no estén el programa **dice que no entiende el fichero** en vez de leer la mitad | de un fichero de ejemplo autorizado |
| **Los ficheros de extracto de una banca concreta** | los cuatro de `tests/datos/` son **inventados**. Un extracto real lleva el nombre, el IBAN y los terceros de una persona: no entra en el repositorio | de nadie: se prueba con los de cada agricultor, en su instalación |
| **La base de datos del agricultor** | **no se ha abierto ni leído**, como pide el encargo | — |
| **El panel de tesorería (T19)** | el contrato pide que los dos lados de un traspaso no se sumen en las entradas y salidas operativas: **la cuenta está hecha y probada aquí** (`resumen_de_lo_que_ha_entrado_y_salido`), pero el panel es del T19 | del T19 |

---

## 11. Decisiones que conviene no deshacer

1. **El fichero del extracto no se guarda.** Lleva el IBAN completo y terceros; los movimientos
   guardados son ya todo lo que hace falta, y lo que se guarda es su huella. Si alguien quiere el
   original, el sitio es `datos/adjuntos` (§3.10 de `AGENTS.md`) y habrá que decidirlo a sabiendas.
2. **El número de cuenta completo no entra en el programa.** Solo los cuatro últimos dígitos, y hay una
   prueba que lo comprueba **en el resultado**, no en el código.
3. **Un importe sin signo no se lee con una convención por defecto.** Se deduce del saldo del fichero
   cuando el fichero lo demuestra, y si no, **se pregunta**. La única alternativa sería elegir «positivo
   es ingreso» para todo el mundo, y hay bancas en las que eso cambia el sentido del extracto entero.
4. **Las letras sueltas `C` y `D` no se leen.** Significan cosas contrarias según el banco.
5. **La clave de duplicado lleva el número de aparición de la línea dentro del fichero.** Sin él, un
   extracto con dos compras idénticas del mismo día **pierde un movimiento**.
6. **El importe de un traspaso se cuenta una vez** (lo que salió de la cuenta), no dos: las dos patas
   son el mismo dinero.
7. **Deshacer no borra: marca.** La conciliación deshecha conserva importe, autor, fecha y motivo, y el
   movimiento del banco se queda como estaba.
8. **Un movimiento sin importe es «no lo sé», y no es cero.** Es la única forma de que la exportación
   de un extracto no diga que un movimiento fue de cero euros.
