# Inventario T01 — parte servidor

**Qué es este documento.** El inventario real del servidor de CUE Digital, hecho leyendo el
código, no la especificación. Todo lo que dice aquí lleva fichero y número de línea. Lo que no
se ha podido comprobar se dice como «no comprobado».

**Fecha del inventario:** lectura del código en su estado actual del repositorio
(`backend/app/**`, `backend/web/**`).

**Cómo se ha hecho.** Lectura directa de `models.py`, `schemas.py`, los 19 ficheros de
`routers/`, `deps.py`, `main.py`, `servicios.py`, `validaciones.py`, `legal.py` y `catalogos.py`;
y una extracción automática de las rutas con el árbol sintáctico de Python (decoradores
`@router.*` + firma de la función) y de todas las apariciones de `/api/` en
`backend/web/**/*.js`.

**Lo que NO se ha comprobado (y conviene que se sepa):**

- **No se ha abierto la base de datos real** (`backend/cuedigital.db`). Todo lo que se dice de
  los datos es lo que el código *puede* guardar, no lo que hay guardado. No se ha contado
  ninguna fila.
- **No se ha arrancado el servidor**, ni se ha ejecutado `scripts/humo.py` ni la comprobación
  de navegador. Los códigos HTTP y los mensajes salen de leer el código, no de llamarlo.
- **No se ha comprobado qué esquema tiene la base de datos de verdad** (`crear_tablas()` añade
  columnas al arrancar). Si la base de producción va por detrás del modelo, este inventario
  describe el modelo, no la tabla tal y como está hoy en disco.
- Las rutas del cuaderno de la Junta, del IUWS y del mapa se han inventariado por su
  declaración; **no se ha verificado respuesta a respuesta** lo que devuelven.

---

## 1. Modelos (`backend/app/models.py`, 1.235 líneas)

### 1.1. Resumen

**26 objetos de tabla**: 25 clases con `__tablename__` más una tabla de enlace
(`grupo_parcela`, `models.py:281`).

| Tabla | Clase | Línea | `explotacion_id` | Anulación | Autor | Versión |
|---|---|---|---|---|---|---|
| `explotaciones` | `Explotacion` | 55 | — (es la raíz) | no | no | no |
| `usuarios` | `Usuario` | 89 | sí (FK) | no | no | no |
| `accesos_a_fincas` | `AccesoAFinca` | 107 | sí (FK) | no | no | no |
| `campanas` | `Campana` | 150 | sí (FK) | no | no | no |
| `parcelas` | `Parcela` | 163 | sí (FK) | no | no | no |
| `parcela_cultivos` | `ParcelaCultivo` | 252 | sí (FK) | no | no | no |
| `grupo_parcela` | (tabla `Table`) | 281 | **NO** | — | — | — |
| `grupos_parcelas` | `GrupoParcelas` | 289 | sí (FK) | no | no | no |
| `instalaciones` | `Instalacion` | 312 | sí (FK) | no | no | no |
| `productos_fitosanitarios` | `ProductoFitosanitario` | 347 | sí (FK) | no | no | no |
| `fertilizantes` | `Fertilizante` | 382 | sí (FK) | no | no | no |
| `aplicadores` | `Aplicador` | 395 | sí (FK) | no | no | no |
| `asesores` | `Asesor` | 414 | sí (FK) | no | no | no |
| `equipos_aplicacion` | `EquipoAplicacion` | 460 | sí (FK) | no | no | no |
| `tratamientos` | `TratamientoFitosanitario` | 506 | sí (FK) | **sí** | no | no |
| `planes_abonado` | `PlanAbonado` | 624 | sí (FK) | no | no | no |
| `medidas_preventivas` | `MedidaPreventivaDeclarada` | 670 | sí (FK) | no | no | no |
| `analiticas` | `Analitica` | 711 | sí (FK) | **sí** | no | no |
| `ventas_de_cosecha` | `VentaDeCosecha` | 786 | sí (FK) | **sí** | no | no |
| `fertilizaciones` | `RegistroFertilizacion` | 855 | sí (FK) | **sí** | no | no |
| `labores` | `Labor` | 917 | sí (FK) | **sí** | no | no |
| `auditoria` | `Auditoria` | 1001 | sí (FK) | — | **`usuario_id`** | no |
| `firmas` | `Firma` | 1020 | sí (FK) | no (nunca se anula) | no (firmante) | **sí** (`version_canonica`) |
| `documentos_anexos` | `DocumentoAnexo` | 1071 | sí (FK) | **sí** | no | no |
| `facturas` | `Factura` | 1138 | sí (FK) | **sí** (`anulada`) | no | no |
| `lineas_de_factura` | `LineaDeFactura` | 1203 | sí (FK) | no | no | no |

**Tres cosas que hay que decir de este cuadro, porque son contratos del §2 del
`CONTRATO_IMPLEMENTACION_CRM.md` y hoy no se cumplen:**

1. **Ninguna tabla de negocio tiene columna de autor.** La única traza de quién hizo algo está
   en `auditoria.usuario_id` (`models.py:1012`), y **es anulable**: hay caminos del código que
   escriben auditoría sin usuario (`registros.py:227-235` y `443-457`, por ejemplo, crean
   auditoría al apuntar un tratamiento o un abono **sin poner `usuario_id`**).
2. **Ninguna tabla de negocio tiene columna de versión.** Lo único que se parece a una versión
   es `firmas.version_canonica` (`models.py:1053`, `default=1`). No hay control de versión
   esperada en ninguna escritura: reenviar el mismo comando crea otro movimiento.
3. **La anulación no está en todas partes y no es uniforme.** Tienen `anulado` +
   `motivo_anulacion`: `tratamientos` (604), `analiticas` (778), `ventas_de_cosecha` (847),
   `fertilizaciones` (903), `labores` (996), `documentos_anexos` (1128). `facturas` la llama
   `anulada` (1194). Las demás (parcelas, cultivos, grupos, maestros, planes, medidas,
   campañas) **no se anulan: se borran**, con el rastro en `auditoria` (`correcciones.borrar`).

### 1.2. Tabla por tabla

Convenio: **NN** = no admite vacío (`Mapped[tipo]` sin `| None`); **N** = admite vacío
(`Mapped[tipo | None]`). El «valor por defecto» es el de Python (`default=`) o el de la base
(`server_default=`). **No hay ni una sola columna con `nullable=` escrito a mano**: la
nulabilidad sale del tipo, así que un `| None` es la única marca de «puede faltar».

#### `explotaciones` — `Explotacion`, `models.py:55-86`

| Columna | Tipo | Vacío | Defecto |
|---|---|---|---|
| `id` | int PK | no | autoincremental |
| `nombre` | String(200) | NN | — |
| `nif` | String(20), index | NN | — |
| `codigo_siex` | String(40) | N | — |
| `ccaa` | String(60) | NN | `"Castilla y León"` (62) |
| `provincia` | String(60) | NN | `""` (63) |
| `municipio` | String(120) | NN | `""` (64) |
| `produccion_ecologica` | Boolean | NN | **`False`** (65) |
| `registro_nacional` | String(40) | N | — |
| `registro_autonomico` | String(40) | N | — |
| `direccion` | String(200) | N | — |
| `localidad` | String(120) | N | — |
| `codigo_postal` | String(10) | N | — |
| `telefono` | String(40) | N | — |
| `correo` | String(200) | N | — |
| `creada_en` | DateTime | NN | `server_default=func.now()` |

Claves ajenas: ninguna. Relación: `parcelas` (`models.py:86`).
Ojo: `produccion_ecologica` con `default=False` es la puerta de la comprobación
`V15_no_ecologico` (`validaciones.py:218-220`): si nadie marca la casilla, la finca **no** es
ecológica y la comprobación **no salta nunca**.

#### `usuarios` — `Usuario`, `models.py:89-104`

`id` PK; `explotacion_id` FK→`explotaciones.id`, NN, index (96); `nombre` String(120) NN;
`correo` String(200) NN, `unique=True`, index; `clave_hash` String(200) NN;
`es_titular` Boolean NN **default `True`** (100); `activo` Boolean NN **default `True`** (101);
`creado_en` DateTime NN `server_default=func.now()`.

`explotacion_id` aquí **no es aislamiento, es «en qué finca estoy trabajando»**
(`models.py:93-95`). El aislamiento real se comprueba en `deps.usuario_actual`
(`deps.py:45-57`) contra el vale y contra `accesos.puede_entrar`.

#### `accesos_a_fincas` — `AccesoAFinca`, `models.py:107-142`

`id` PK; `usuario_id` FK→`usuarios.id` NN index; `explotacion_id` FK→`explotaciones.id` NN
index; `papel` String(20) NN **default `"ayudante"`** (138); `creado_en` NN `server_default`.
Restricción: `UniqueConstraint("usuario_id","explotacion_id")` = `uq_acceso_usuario_finca` (131).

#### `campanas` — `Campana`, `models.py:150-160`

`id` PK; `explotacion_id` FK NN index; `anio` Integer NN; `fecha_inicio` Date NN;
`fecha_fin` Date NN; `cerrada` Boolean NN **default `False`** (159); `creada_en` NN
`server_default`.
Restricción: `UniqueConstraint("explotacion_id","anio")` = `uq_campana_anio` (152).

#### `parcelas` — `Parcela`, `models.py:163-249`

| Columna | Tipo | Vacío | Defecto |
|---|---|---|---|
| `id` | int PK | no | — |
| `explotacion_id` | FK→`explotaciones.id`, index | NN | — |
| `alias` | String(120) | NN | — |
| `ref_sigpac` | String(60), index | N | — |
| `provincia` | String(60) | NN | `""` (176) |
| `municipio` | String(120) | NN | `""` (177) |
| `codigo_ine` | String(10) | N | — |
| `poligono` | Integer | N | — |
| `numero_parcela` | Integer | N | — |
| `numero_recinto` | Integer | N | — |
| `agregado` | Integer | NN | **`0`** (186) |
| `zona` | Integer | NN | **`0`** (187) |
| `referencia_catastral` | String(30) | N | — |
| `superficie_ha` | Float | NN | **`0.0`** (193) |
| `superficie_oficial` | Boolean | NN | **`False`** (194) |
| `superficie_sigpac_ha` | Float | N | — (200, «vacío = no lo sé, nunca 0») |
| `uso_sigpac` | String(80) | N | — |
| `sistema` | String(20) | NN | **`"secano"`** (203) |
| `pendiente_pct` | Float | N | — |
| `masa_agua_cerca` | Boolean | NN | **`False`** (205) |
| `captacion_consumo_humano` | Boolean | NN | **`False`** (206) |
| `zona_vulnerable_nitratos` | Boolean | N | **`None`** (208) — el único «booleano de tres estados» bien puesto |
| `geometria` | Text (WKT) | N | — |
| `creada_en` | DateTime | NN | `server_default=func.now()` |

Propiedades calculadas (no columnas): `centro` (218) y `dibujo` (234).

#### `parcela_cultivos` — `ParcelaCultivo`, `models.py:252-278`

`id` PK; `explotacion_id` FK NN index; `parcela_id` FK→`parcelas.id` NN index;
`campana_id` FK→`campanas.id` NN index; `especie` String(120) NN; `variedad` String(120) N;
`sistema` String(20) NN **default `"secano"`** (263); `fecha_inicio` Date N; `fecha_fin` Date N;
`ecorregimen` String(40) N (271, sin catálogo oficial); `superficie_cultivada_ha` Float N (276,
«vacío = no lo sé, nunca 0»). Relación `parcela` (278).

#### `grupo_parcela` — tabla de enlace, `models.py:281-286`

`grupo_id` FK→`grupos_parcelas.id` `ondelete=CASCADE` PK; `parcela_id` FK→`parcelas.id`
`ondelete=CASCADE` PK. **Sin `explotacion_id`**: es la única tabla que no lo lleva, y es
intencionado (los dos lados ya lo llevan). El aislamiento del grupo se comprueba al cargarlo
con `obtener_de_la_explotacion` (`parcelas.py:1064`, por ejemplo).

#### `grupos_parcelas` — `GrupoParcelas`, `models.py:289-309`

`id` PK; `explotacion_id` FK NN index; `nombre` String(120) NN; `campana_id` FK→`campanas.id` N
(sin index); `cultivo` String(120) N; `sistema` String(20) NN **default `"secano"`** (305);
`creado_automaticamente` Boolean NN **default `False`** (306); `creado_en` NN `server_default`.
Relación `parcelas` por `grupo_parcela` (309).

#### `instalaciones` — `Instalacion`, `models.py:312-339`

`id` PK; `explotacion_id` FK NN index; `alias` String(120) NN; `tipo` String(30) NN
**default `"almacen"`** (333); `referencia_catastral` String(40) N; `municipio` String(120) NN
**default `""`** (335); `uso` String(200) N; `superficie_m2` Float N; `observaciones` Text N;
`creada_en` NN `server_default`.

#### `productos_fitosanitarios` — `ProductoFitosanitario`, `models.py:347-379`

| Columna | Tipo | Vacío | Defecto |
|---|---|---|---|
| `id` | int PK | no | — |
| `explotacion_id` | FK NN index | — | — |
| `nombre_comercial` | String(200) | NN | — |
| `numero_registro` | String(40), index | N | — |
| `materia_activa` | String(300) | N | — |
| `tipo_producto` | String(120) | N | — |
| `dosis_maxima` | Float | N | — |
| `unidad_dosis` | String(10) | NN | **`"L/ha"`** (365) |
| `plazo_seguridad_dias` | Integer | N | — |
| `lote` | String(60) | N | — |
| `fecha_caducidad` | Date | N | — |
| `cantidad_comprada` | Float | N | — |
| `unidad_compra` | String(10) | NN | **`"L"`** (370) |
| `fecha_compra` | Date | N | — |
| `proveedor` | String(200) | N | — |
| `autorizado` | Boolean | NN | **`True`** (373) |
| `permitido_ecologico` | Boolean | NN | **`True`** (374) |
| `autorizacion_excepcional` | String(120) | N | — |
| `autorizacion_hasta` | Date | N | — |
| `foto_etiqueta` | String(400) | N | — |
| `creado_en` | DateTime | NN | `server_default` |

#### `fertilizantes` — `Fertilizante`, `models.py:382-392`

`id` PK; `explotacion_id` FK NN index; `nombre` String(200) NN; `tipo` String(30) NN
**default `"mineral"`** (388); `riqueza_n` Float **NN default `0.0`** (389);
`riqueza_p` Float **NN default `0.0`** (390); `riqueza_k` Float **NN default `0.0`** (391);
`creado_en` NN `server_default`.

#### `aplicadores` — `Aplicador`, `models.py:395-411`

`id` PK; `explotacion_id` FK NN index; `nombre` String(200) NN; `nif` String(20) N;
`es_empresa` Boolean NN **default `False`** (404); `numero_ropo` String(60) N;
`numero_carne` String(60) N; `tipo_carne` String(60) N; `fecha_caducidad_carne` Date N;
`numero_reganip` String(60) N; `creado_en` NN `server_default`.

#### `asesores` — `Asesor`, `models.py:414-457`

`id` PK; `explotacion_id` FK NN index; `nombre` String(200) NN; `nif` String(20) N;
`es_empresa` Boolean NN **default `False`** (445); `numero_ropo` String(60) N;
`ambito` String(40) N; `entidad_certificacion` String(200) N; `telefono` String(40) N;
`correo` String(200) N; `creado_en` NN `server_default`.

#### `equipos_aplicacion` — `EquipoAplicacion`, `models.py:460-499`

`id` PK; `explotacion_id` FK NN index; `nombre` String(120) NN; `tipo` String(80) N;
`titularidad` String(20) NN **default `"propia"`** (491); `marca` String(80) N;
`modelo` String(80) N; `numero_roma` String(60) N; `numero_serie` String(80) N;
`fecha_adquisicion` Date N; `fecha_iteaf` Date N; `fecha_proxima_iteaf` Date N;
`creado_en` NN `server_default`.

#### `tratamientos` — `TratamientoFitosanitario`, `models.py:506-616`

| Columna | Tipo | Vacío | Defecto |
|---|---|---|---|
| `id` | int PK | no | — |
| `explotacion_id` | FK NN index | — | — |
| `campana_id` | FK→`campanas.id` NN index | — | — |
| `fecha` | Date, index | NN | — |
| `hora_inicio` / `hora_fin` | String(5) | N | — |
| `parcela_id` | FK→`parcelas.id`, index | N | — |
| `grupo_id` | FK→`grupos_parcelas.id` | N | — |
| `tipo` | String(30), index | NN | **`"parcela"`** (535) |
| `instalacion_id` | FK→`instalaciones.id`, index | N | — |
| `producto_cosechado` | String(200) | N | — |
| `lote_cosecha` | String(60) | N | — |
| `superficie_tratada_ha` | Float | **NN** | *sin defecto* (544) |
| `cultivo` / `variedad` | String(120) | N | — |
| `plaga` | String(200) | N | — |
| `justificacion` | Text | N | — |
| `estado_cultivo` | String(120) | N | — |
| `producto_id` | FK→`productos_fitosanitarios.id` | N | — |
| `producto_nombre` | String(200) | N | — |
| `numero_registro` | String(40) | N | — |
| `materia_activa` | String(300) | N | — |
| `lote_producto` | String(60) | N | — |
| `dosis` | Float | N | — |
| `unidad_dosis` | String(10) | NN | **`"L/ha"`** (559) |
| `dosis_maxima_etiqueta` | Float | N | — |
| `cantidad_total` | Float | N | — |
| `unidad_cantidad_aplicada` | String(20) | N | — |
| `volumen_caldo_l_ha` | Float | N | — |
| `plazo_seguridad_dias` | Integer | N | — |
| `fecha_fin_plazo_seguridad` | Date | N | — |
| `plazo_reentrada_dias` | Integer | N | — |
| `aplicador_id` | FK→`aplicadores.id` | N | — |
| `equipo_id` | FK→`equipos_aplicacion.id` | N | — |
| `asesor_id` | FK→`asesores.id` | N | — |
| `asesor_fecha` | Date | N | — |
| `asesoramiento_validado` | Boolean | N | — (580: «`None` es “no lo he dicho”») |
| `asesoramiento_contrato` | Boolean | N | — |
| `temperatura_c` / `humedad_pct` / `viento_kmh` | Float | N | — |
| `viento_direccion` | String(20) | N | — |
| `franja_seguridad_respetada` | Boolean | N | — |
| `aplicado_a_mano` | Boolean | N | — (594: «vacío es “no lo sé”, no “no”») |
| `eficacia` | String(20) | N | — |
| `en_zona_vulnerable` | Boolean | **NN** | **`False`** (598) |
| `operadores_expuestos` | Integer | N | — |
| `incidencias` / `observaciones` | Text | N | — |
| `anulado` | Boolean | NN | **`False`** (604) |
| `motivo_anulacion` | Text | N | — |
| `creado_en` | DateTime | NN | `server_default` |
| `actualizado_en` | DateTime | NN | `server_default` + `onupdate` (608) |
| `medidas` | JSON | N | **`list`** (616) |

**Copia deliberada de la etiqueta**: `dosis_maxima_etiqueta`, `plazo_seguridad_dias` y los datos
del producto se copian al apunte (documentado en `models.py:509-512`).

#### `planes_abonado` — `PlanAbonado`, `models.py:624-667`

`id` PK; `explotacion_id` FK NN index; `campana_id` FK NN index; `parcela_id` FK→`parcelas.id`
N; `grupo_id` FK→`grupos_parcelas.id` N; `cultivo` String(120) NN; `superficie_ha` Float NN;
`produccion_esperada_kg_ha` Float N; `necesidad_n` / `necesidad_p` / `necesidad_k` Float N;
`aportes_suelo_agua` Float N; `herramienta` Boolean N; `detalle` JSON **default `list`** (655);
`analitica_id` **Integer, NO ForeignKey** (662, decisión explicada: SQLite no añade FK a una
columna existente); `notas` Text N; `creado_en` / `actualizado_en` (con `onupdate`).

#### `medidas_preventivas` — `MedidaPreventivaDeclarada`, `models.py:670-708`

`id` PK; `explotacion_id` FK NN index; `medida` String(40) NN index (código del catálogo, sin
FK a propósito, 696-698); `aplicada` Boolean NN **default `True`** (700); `observaciones` Text N;
`declarada_en` y `actualizada_en` (con `onupdate`).
Restricción: `UniqueConstraint("explotacion_id","medida")` = `uq_medida_por_finca` (692).

#### `analiticas` — `Analitica`, `models.py:711-783`

`id` PK; `explotacion_id` FK NN index; `campana_id` FK NN index; `tipo` String(30) NN index;
`fecha_toma_muestra` Date NN index; `fecha_resultado` Date N; `parcela_id` FK index N;
`instalacion_id` FK N; `lote` String(80) N; `laboratorio` String(200) N;
`nif_laboratorio` String(20) N; `numero_informe` String(80) N; `tipo_analisis` String(120) N;
`sustancia_detectada` String(200) N; `parametros` JSON **default `list`** (768);
`fichero_nombre` String(200) N; `fichero_ruta` String(300) N; `fichero_tipo` String(100) N;
`fichero_bytes` Integer N; `observaciones` Text N; `anulado` Boolean NN **default `False`** (778);
`motivo_anulacion` Text N; `creado_en` / `actualizado_en`.

#### `ventas_de_cosecha` — `VentaDeCosecha`, `models.py:786-852`

`id` PK; `explotacion_id` FK NN index; `campana_id` FK NN index; `tipo` String(30) NN index
**default `"comercializada"`** (821); `fecha` Date NN index; `fecha_fin` Date N; `producto`
String(200) NN; `variedad` String(120) N; `cantidad` Float NN; `unidad` String(10) NN
**default `"kg"`** (836); `lote` String(80) N; `comprador` String(200) N;
`numero_albaran` String(80) N; `parcela_id` FK index N; `grupo_id` FK N; `observaciones` Text N;
`anulado` Boolean NN **default `False`** (847); `motivo_anulacion` Text N; `creado_en` /
`actualizado_en`.

**No hay precio, ni importe, ni estado de cobro** (documentado a propósito, 808-811). Tampoco
hay columnas de fichero: la ruta `POST /api/ventas/{id}/fichero` **no existe** (dicho en
`ventas_api.py:351-380`).

#### `fertilizaciones` — `RegistroFertilizacion`, `models.py:855-909`

`id` PK; `explotacion_id` FK NN index; `campana_id` FK NN index; `fecha` Date NN index;
`parcela_id` FK index N; `grupo_id` FK N; `superficie_ha` Float NN;
`fertilizante_id` FK→`fertilizantes.id` N; `fertilizante_nombre` String(200) N; `tipo`
String(30) NN **default `"mineral"`** (871); `riqueza_n`, `riqueza_p`, `riqueza_k` Float
**NN default `0.0`** (874-876); `kg_ha_producto` Float NN; `cantidad_total_kg` Float NN;
`uf_n_ha`, `uf_p_ha`, `uf_k_ha`, `uf_n_total`, `uf_p_total`, `uf_k_total` Float
**NN default `0.0`** (880-885); `modo_aplicacion` String(60) N; `momento` String(30) N;
`plan_id` FK→`planes_abonado.id` N; `numero_albaran` String(80) N; `tipo_fertilizacion`
String(20) N; `factura_id` FK→`facturas.id` N; `en_zona_vulnerable` Boolean **NN default
`False`** (899); `nitratos_agua_riego` Float N; `observaciones` Text N; `anulado` Boolean NN
**default `False`** (903); `motivo_anulacion` Text N; `creado_en` / `actualizado_en`.

#### `labores` — `Labor`, `models.py:917-998`

`id` PK; `explotacion_id` FK NN index; `campana_id` FK NN index; `tipo` String(30) NN index;
`fecha` Date NN index; `parcela_id` FK index N; `grupo_id` FK N; `superficie_ha` Float N;
`cultivo` / `variedad` String(120) N; `cantidad_semilla_kg` Float N; `dosis_siembra_kg_ha`
Float N; `material_tratado` Boolean N; `material_adquirido` Boolean N; `fecha_adquisicion` Date
N; `tratamiento_semilla` String(200) N; `fecha_tratamiento_semilla` Date N;
`eficacia_tratamiento_semilla` String(20) N; `lote_semilla` String(80) N; `siembra_directa`
Boolean N; `densidad_plantacion` Float N; `marco_plantacion` String(60) N; `animales_terceros` /
`animales_propios` Boolean N; `equipo_id` FK→`equipos_aplicacion.id` N; `semillas_siembra`,
`plantas_cosechadas`, `sin_cosechar_ambiental`, `restos_cosecha_depositados` Boolean N;
`fecha_establecimiento_cubierta` Date N; `tipo_cobertura` String(120) N; `anchura_cubierta_m`,
`anchura_libre_proyeccion_m` Float N; `restos_desbroce_depositados`, `restos_poda_depositados`
Boolean N; `volumen_agua` Float N; `unidad_agua` String(10) N; `origen_agua` String(40) N;
`sistema_riego` String(40) N; `numero_contador` String(60) N; `nitratos_agua` Float N;
`detalles` JSON N (sin defecto); `observaciones` Text N; `anulado` Boolean NN **default `False`**
(996); `motivo_anulacion` Text N; `creado_en`.

**Ojo con la cosecha**: una cosecha **es una labor** con `tipo="cosecha"` y sus datos dentro de
`detalles` (`registros.py:711-723`: `detalles={"producto":…, "cantidad_kg":…}`). El producto y
los kilos de la cosecha **no tienen columna propia**.

#### `auditoria` — `Auditoria`, `models.py:1001-1017`

`id` PK; `explotacion_id` FK NN index; `usuario_id` FK→`usuarios.id` **N**; `entidad`
String(60) NN; `entidad_id` Integer N; `accion` String(30) NN; `datos` JSON N; `fecha`
DateTime NN `server_default`.

No hay columnas `creado_por`, `creado_en` ni `version` en las tablas de negocio: **este es el
único sitio donde se sabe quién hizo algo**, y es opcional.

#### `firmas` — `Firma`, `models.py:1020-1068`

`id` PK; `explotacion_id` FK NN index; `entidad` String(40) NN index; `entidad_id` Integer N;
`campana_id` FK→`campanas.id` N; `huella` String(64) NN index; `version_canonica` Integer NN
**default `1`** (1053); `algoritmo` String(40) NN **default `"SHA256withRSA"`** (1054);
`formato` String(20) NN **default `"CAdES"`** (1055); `firmante_nif` String(20) NN
**default `""`** (1057); `firmante_nombre` String(200) NN **default `""`** (1058);
`contenido` Text N; `nombre_del_fichero` String(200) N; `firmado_en` NN `server_default`;
`verificada_criptograficamente` Boolean NN **default `False`** (1065); `nota_verificacion` Text N.

**Nunca se anula ni se borra** (1023): firmar otra vez deja las dos filas.

#### `documentos_anexos` — `DocumentoAnexo`, `models.py:1071-1130`

`id` PK; `explotacion_id` FK NN index; `campana_id` FK N; `carpeta` String(80) NN
**default `""`** (1111); `titulo` String(200) NN **default `""`** (1113); `tipo` String(40) NN
**default `"otros"`** (1115); `fecha` Date N; `quien` String(200) N; `notas` Text N;
`fichero_nombre` String(200) N; `fichero_ruta` String(300) N; `fichero_tipo` String(120) N;
`fichero_bytes` Integer N; `anulado` Boolean NN **default `False`** (1128); `motivo_anulacion`
Text N; `creado_en`.

#### `facturas` — `Factura`, `models.py:1138-1200`

`id` PK; `explotacion_id` FK NN index; `campana_id` FK index **N**; `fecha` Date N index;
`proveedor` String(200) N; `proveedor_nif` String(20) N; `numero_factura` String(80) N index;
`base_imponible` Float N; `cuota_iva` Float N; `tipo_iva_pct` Float N; `total` Float N;
`notas` Text N; `leida_por` String(20) N; `huella` String(64) N index; `fichero_nombre`
String(200) N; `fichero_ruta` String(300) N; `fichero_tipo` String(120) N; `fichero_bytes`
Integer N; `anulada` Boolean NN **default `False`** (1194); `motivo_anulacion` Text N;
`creada_en`. Relación `lineas` con `cascade="all, delete-orphan"` (1198).

**Ninguna cifra es obligatoria ni tiene defecto**: sin `default=`, así que un hueco se queda en
`None` (nulo de verdad).

#### `lineas_de_factura` — `LineaDeFactura`, `models.py:1203-1235`

`id` PK; `explotacion_id` FK NN index; `factura_id` FK→`facturas.id` NN index;
`descripcion` String(200) NN; `cantidad` Float N; `unidad` String(20) N; `precio_unitario`
Float N; `importe` Float N; `numero_registro` String(40) N; `lote` String(60) N;
`producto_id` FK→`productos_fitosanitarios.id` N; `fertilizante_id` FK→`fertilizantes.id` N.

---

## 2. API (`backend/app/routers/*.py`)

### 2.1. Cómo está montado

Los **19 routers** (19 ficheros con `APIRouter` en `backend/app/routers/`, más el `__init__.py`
vacío) se registran en `main.py:109-131`, en este orden: `cuenta`, `fincas_api`,
`explotacion`, `parcelas`, `mapa`, `cuaderno_cyl_api`, `facturas_api`, `maestros`, `registros`,
`cuaderno`, `interfaz`, `borradores_api`, `firmas_api`, `planes_api`, `analiticas_api`,
`medidas_api`, `ventas_api`, `documentos_api`, `iuws_api`. Al final, un montaje de ficheros
estáticos en `/` (`main.py:155-156`) que **se come cualquier ruta declarada después**.

Prefijos (`APIRouter(prefix=…)`):

| Router | Prefijo | Línea |
|---|---|---|
| `cuenta` | `/api/cuenta` | cuenta.py:20 |
| `fincas_api` | `/api/fincas` | fincas_api.py:37 |
| `explotacion` | `/api` | explotacion.py:12 |
| `parcelas` | `/api` | parcelas.py:32 |
| `mapa` | `/api/mapa` | mapa.py:30 |
| `cuaderno_cyl_api` | `/api/cuaderno-cyl` | cuaderno_cyl_api.py:56 |
| `facturas_api` | `/api/facturas` | facturas_api.py:53 |
| `maestros` | `/api` | maestros.py:51 |
| `registros` | `/api` | registros.py:35 |
| `cuaderno` | `/api` | cuaderno.py:31 |
| `interfaz` | `/api` | interfaz.py:14 |
| `borradores_api` | `/api` | borradores_api.py:24 |
| `firmas_api` | `/api` | firmas_api.py:37 |
| `planes_api` | `/api` | planes_api.py:26 |
| `analiticas_api` | `/api` | analiticas_api.py:45 |
| `medidas_api` | `/api` | medidas_api.py:48 |
| `ventas_api` | `/api` | ventas_api.py:41 |
| `documentos_api` | `/api` | documentos_api.py:47 |
| `iuws_api` | `/api/iuws` | iuws_api.py:49 |
| — (`main.py`) | `/health`, `/api` | main.py:134, 142 |

**Ningún router declara `dependencies=[...]`**: la sesión se pide router a router, función a
función. Eso significa que **la puerta de la sesión se puede olvidar sin que nada avise**, y de
hecho hay tres sitios donde se ha olvidado (ver 2.3).

**Aviso de orden de declaración** (no es un detalle de estilo): en varios sitios una ruta
literal va declarada **antes** que la de identificador a propósito, porque FastAPI resuelve por
orden. Está explicado en `ventas_api.py:150-155` (`/ventas/informe` antes de `/ventas/{venta_id}`)
y en `ventas_api.py:238-243`. **Cualquier reorganización de esas rutas rompe la llamada sin dar
un error claro.**

### 2.2. Inventario completo (método + camino → router → salida → sesión → filtro por finca)

Convenio de las columnas:

- **Sesión**: «sí» = la firma pide `UsuarioActual`, o pide `ExplotacionActual`, que **depende de
  `usuario_actual`** (`deps.py:64-68`), así que también exige sesión. «NO» = se puede llamar sin
  identificarse.
- **Filtro**: «sí» = la consulta filtra por `explotacion_id` o pasa por
  `obtener_de_la_explotacion` (`deps.py:74-85`, que devuelve **404** y no 403). «n/a» = la ruta no
  toca datos de nadie (catálogo, texto, servicio oficial).

#### Cuenta y fincas

| Método y camino | Fichero:línea | Salida | Sesión | Filtro |
|---|---|---|---|---|
| `POST /api/cuenta/registro` | cuenta.py:35 | `TokenSalida` (201) | **NO** | n/a |
| `POST /api/cuenta/entrar` | cuenta.py:103 | `TokenSalida` | **NO** | n/a |
| `GET /api/cuenta/yo` | cuenta.py:125 | dict | sí | propio usuario |
| `GET /api/cuenta/certificado/estado` | cuenta.py:167 | dict | **NO** | n/a |
| `POST /api/cuenta/entrar-con-certificado` | cuenta.py:184 | `TokenSalida` | **NO** | n/a |
| `POST /api/cuenta/vincular-certificado` | cuenta.py:238 | dict | sí | propio usuario |
| `GET /api/fincas` | fincas_api.py:79 | `list[FincaSalida]` | sí | por cuenta (sus accesos) |
| `POST /api/fincas/cambiar` | fincas_api.py:88 | `TokenSalida` | sí | por cuenta |
| `GET /api/fincas/quien-entra` | fincas_api.py:120 | `QuienEntraSalida` | sí | sí |
| `POST /api/fincas/quien-entra` | fincas_api.py:161 | `QuienEntraSalida` (201) | sí | sí + titular |
| `DELETE /api/fincas/quien-entra/{usuario_id}` | fincas_api.py:201 | `QuienEntraSalida` | sí | sí + titular |

#### Finca, campañas, tierras y grupos

| Método y camino | Fichero:línea | Salida | Sesión | Filtro |
|---|---|---|---|---|
| `GET /api/mi-finca` | explotacion.py:15 | `ExplotacionSalida` | sí | sí |
| `PUT /api/mi-finca` | explotacion.py:20 | `ExplotacionSalida` | sí | sí (lista blanca de campos, 24-43) |
| `GET /api/campanas` | explotacion.py:67 | `list[CampanaSalida]` | sí | sí |
| `POST /api/campanas` | explotacion.py:133 | `CampanaSalida` (201) | sí | sí |
| `GET /api/campanas/actual` | explotacion.py:145 | `CampanaSalida` | sí | sí |
| `PUT /api/campanas/{campana_id}` | explotacion.py:158 | `CampanaSalida` | sí | sí |
| `DELETE /api/campanas/{campana_id}` | explotacion.py:300 | dict | sí | sí (409 si tiene cosas dentro) |
| `GET /api/parcelas` | parcelas.py:230 | `list[ParcelaSalida]` | sí | sí |
| `POST /api/parcelas` | parcelas.py:339 | `ParcelaSalida` (201) | sí | sí |
| `GET /api/parcelas/{parcela_id}` | parcelas.py:699 | `ParcelaSalida` | sí | sí |
| `PUT /api/parcelas/{parcela_id}` | parcelas.py:704 | `ParcelaSalida` | sí | sí |
| `DELETE /api/parcelas/{parcela_id}` | parcelas.py:771 | dict | sí | sí |
| `POST /api/parcelas/desde-sigpac` | parcelas.py:357 | `ParcelaSalida` (201) | sí | sí |
| `POST /api/parcelas/desde-sigpac/varias` | parcelas.py:519 | dict | sí | sí |
| `GET /api/parcelas/{parcela_id}/cultivos` | parcelas.py:813 | dict | sí | sí |
| `POST /api/parcelas/{parcela_id}/cultivos` | parcelas.py:841 | dict (201) | sí | sí |
| `DELETE /api/parcelas/{parcela_id}/cultivos/{campana_id}` | parcelas.py:908 | dict | sí | sí |
| `GET /api/cultivos` | parcelas.py:647 | dict | sí | sí |
| `GET /api/grupos` | parcelas.py:962 | dict | sí | sí |
| `POST /api/grupos` | parcelas.py:1038 | `GrupoSalida` (201) | sí | sí |
| `PUT /api/grupos/{grupo_id}` | parcelas.py:1048 | `GrupoSalida` | sí | sí |
| `DELETE /api/grupos/{grupo_id}` | parcelas.py:1094 | dict | sí | sí |
| `POST /api/grupos/calcular` | parcelas.py:1130 | dict | sí | sí |
| `GET /api/municipios` | parcelas.py:427 | dict | **NO** | n/a (lista INE oficial) |
| `POST /api/sigpac/buscar` | parcelas.py:460 | dict | **NO** | n/a (servicio oficial) |
| `GET /api/sigpac/estado` | parcelas.py:591 | dict | **NO** | n/a |
| `POST /api/sigpac/consultar` | parcelas.py:604 | dict | **NO** | n/a |
| `GET /api/zonas-vulnerables/estado` | parcelas.py:1168 | dict | **NO** | n/a (pero ver 2.4) |
| `GET /api/mapa/estado` | mapa.py:44 | dict | **NO** | n/a |
| `GET /api/mapa/imagen` | mapa.py:79 | imagen (proxy IGN/SIGPAC) | **NO** | n/a |
| `POST /api/mapa/punto` | mapa.py:133 | dict | **NO** | n/a (consulta por coordenada) |

#### Maestros

Todos filtran por explotación. Los `GET` de lista y los `POST` **no piden `UsuarioActual`**,
pero sí `ExplotacionActual`, así que **sí exigen sesión**; las correcciones y los borrados piden
además `UsuarioActual` porque escriben en la auditoría con el usuario.

| Método y camino | Fichero:línea | Salida | Sesión | Filtro |
|---|---|---|---|---|
| `GET /api/productos` | maestros.py:147 | `list[ProductoSalida]` | sí | sí |
| `POST /api/productos` | maestros.py:182 | `ProductoSalida` (201) | sí | sí |
| `GET /api/productos/{producto_id}` | maestros.py:271 | `ProductoSalida` | sí | sí |
| `PUT /api/productos/{producto_id}` | maestros.py:192 | `ProductoSalida` | sí | sí |
| `DELETE /api/productos/{producto_id}` | maestros.py:231 | dict | sí | sí |
| `GET /api/productos/cesta/situacion` | maestros.py:280 | dict | sí | sí |
| `GET/POST/PUT/DELETE /api/fertilizantes…` | maestros.py:339, 373, 383, 444 | `FertilizanteSalida` | sí | sí |
| `GET/POST/PUT/DELETE /api/aplicadores…` | maestros.py:486, 536, 546, 580 | `AplicadorSalida` | sí | sí |
| `GET/POST/PUT/DELETE /api/asesores…` | maestros.py:621, 658, 676, 712 | `AsesorSalida` | sí | sí |
| `GET/POST/PUT/DELETE /api/equipos…` | maestros.py:748, 782, 792, 828 | `EquipoSalida` | sí | sí |
| `GET/POST/PUT/DELETE /api/instalaciones…` | maestros.py:867, 914, 941, 978 | `InstalacionSalida` | sí | sí |
| `GET /api/instalaciones/{instalacion_id}` | maestros.py:934 | `InstalacionSalida` | sí | sí |
| `GET /api/avisos` | maestros.py:1019 | dict | sí | sí |

#### Registro obligatorio (tratamientos, abonos, labores, cosecha)

| Método y camino | Fichero:línea | Salida | Sesión | Filtro |
|---|---|---|---|---|
| `POST /api/tratamientos/validar` | registros.py:180 | `ResultadoValidacion` | sí | sí (vía `_contexto_tratamiento` → `_cargar`) |
| `POST /api/tratamientos` | registros.py:220 | `TratamientoSalida` (201) | sí | sí |
| `GET /api/tratamientos` | registros.py:240 | `list[TratamientoSalida]` | sí | sí |
| `GET /api/tratamientos/{tratamiento_id}` | registros.py:260 | `TratamientoSalida` | sí | sí |
| `POST /api/tratamientos/{tratamiento_id}/anular` | registros.py:269 | dict | sí | sí |
| `PUT /api/tratamientos/{tratamiento_id}` | registros.py:283 | `TratamientoSalida` | sí | sí |
| `DELETE /api/tratamientos/{tratamiento_id}` | registros.py:315 | dict | sí | sí (409 si firmado) |
| `POST /api/fertilizaciones/validar` | registros.py:400 | `ResultadoValidacion` | sí | sí |
| `POST /api/fertilizaciones` | registros.py:442 | `FertilizacionSalida` (201) | sí | sí |
| `GET /api/fertilizaciones` | registros.py:462 | `list[FertilizacionSalida]` | sí | sí |
| `POST /api/fertilizaciones/{registro_id}/anular` | registros.py:480 | dict | sí | sí |
| `PUT /api/fertilizaciones/{registro_id}` | registros.py:491 | `FertilizacionSalida` | sí | sí |
| `DELETE /api/fertilizaciones/{registro_id}` | registros.py:521 | dict | sí | sí (409 si firmado) |
| `POST /api/labores` | registros.py:580 | `LaborSalida` (201) | sí | sí |
| `PUT /api/labores/{labor_id}` | registros.py:590 | `LaborSalida` | sí | sí |
| `DELETE /api/labores/{labor_id}` | registros.py:612 | dict | sí | sí (409 si firmado) |
| `POST /api/labores/{labor_id}/anular` | registros.py:632 | dict | sí | sí |
| `GET /api/labores` | registros.py:647 | `list[LaborSalida]` | sí | sí |
| `POST /api/cosecha/validar` | registros.py:664 | `ResultadoValidacion` | sí | sí |
| `POST /api/cosecha` | registros.py:727 | dict (201) | sí | sí |
| `PUT /api/cosecha/{labor_id}` | registros.py:737 | dict | sí | sí |
| `DELETE /api/cosecha/{labor_id}` | registros.py:759 | dict | sí | sí |

**No hay `GET /api/cosecha`**: la cosecha se lee por `/api/labores` y se filtra por `tipo` en el
cliente (no comprobado en el navegador).

#### Plan de abono, análisis, medidas, ventas

| Método y camino | Fichero:línea | Salida | Sesión | Filtro |
|---|---|---|---|---|
| `GET /api/planes` | planes_api.py:146 | `list[PlanConLoAplicado]` | sí | sí |
| `POST /api/planes/validar` | planes_api.py:159 | dict | **NO** | **n/a — sin filtro** |
| `POST /api/planes` | planes_api.py:168 | `PlanAbonadoSalida` (201) | sí | sí |
| `GET /api/planes/{plan_id}` | planes_api.py:196 | `PlanConLoAplicado` | sí | sí |
| `PUT /api/planes/{plan_id}` | planes_api.py:202 | `PlanAbonadoSalida` | sí | sí |
| `GET /api/planes/{plan_id}/resumen` | planes_api.py:230 | dict | sí | sí |
| `DELETE /api/planes/{plan_id}` | planes_api.py:261 | dict | sí | sí |
| `GET /api/analiticas` | analiticas_api.py:187 | `list[AnaliticaConSitio]` | sí | sí |
| `GET /api/analiticas/informe` | analiticas_api.py:217 | `InformeDeAnalisis` | sí | sí |
| `POST /api/analiticas/validar` | analiticas_api.py:286 | dict | **NO** | **n/a — sin filtro** |
| `POST /api/analiticas` | analiticas_api.py:296 | `AnaliticaConSitio` (201) | sí | sí |
| `GET /api/analiticas/{analitica_id}` | analiticas_api.py:328 | `AnaliticaConSitio` | sí | sí |
| `PUT /api/analiticas/{analitica_id}` | analiticas_api.py:336 | `AnaliticaConSitio` | sí | sí |
| `POST /api/analiticas/{analitica_id}/anular` | analiticas_api.py:373 | `AnaliticaSalida` | sí | sí |
| `POST /api/analiticas/{analitica_id}/informe` | analiticas_api.py:411 | `AnaliticaConSitio` | sí | sí |
| `GET /api/analiticas/{analitica_id}/informe` | analiticas_api.py:439 | fichero PDF | sí | sí |
| `GET /api/analiticas/{analitica_id}/parametros` | analiticas_api.py:454 | dict | sí | sí |
| `DELETE /api/analiticas/{analitica_id}` | analiticas_api.py:485 | dict | sí | sí |
| `GET /api/medidas` | medidas_api.py:92 | `DeclaracionDeMedidas` | sí | sí |
| `POST /api/medidas/validar` | medidas_api.py:98 | dict | **NO** | **n/a — sin filtro** |
| `PUT /api/medidas` | medidas_api.py:107 | `DeclaracionDeMedidas` | sí | sí |
| `DELETE /api/medidas` | medidas_api.py:136 | `DeclaracionDeMedidas` | sí | sí |
| `GET /api/medidas/informe` | medidas_api.py:186 | dict | sí | sí |
| `GET /api/ventas` | ventas_api.py:129 | `list[VentaConNombres]` | sí | sí |
| `GET /api/ventas/informe` | ventas_api.py:148 | `InformeDeVentas` | sí | sí |
| `GET /api/ventas/resumen` | ventas_api.py:235 | dict | sí | sí |
| `POST /api/ventas/validar` | ventas_api.py:260 | dict | sí | sí |
| `POST /api/ventas` | ventas_api.py:269 | `VentaConNombres` (201) | sí | sí |
| `GET /api/ventas/{venta_id}` | ventas_api.py:294 | `VentaConNombres` | sí | sí |
| `PUT /api/ventas/{venta_id}` | ventas_api.py:300 | `VentaConNombres` | sí | sí |
| `POST /api/ventas/{venta_id}/anular` | ventas_api.py:324 | `VentaSalida` | sí | sí |
| `DELETE /api/ventas/{venta_id}` | ventas_api.py:350 | dict | sí | sí |

#### Documentos, facturas, firmas, cuaderno

| Método y camino | Fichero:línea | Salida | Sesión | Filtro |
|---|---|---|---|---|
| `GET /api/documentos` | documentos_api.py:97 | dict | sí | sí |
| `POST /api/documentos` | documentos_api.py:221 | `DocumentoSalida` (201) | sí | sí |
| `PUT /api/documentos/{documento_id}` | documentos_api.py:248 | `DocumentoSalida` | sí | sí |
| `DELETE /api/documentos/{documento_id}` | documentos_api.py:286 | dict | sí | sí |
| `POST /api/documentos/{documento_id}/fichero` | documentos_api.py:342 | `DocumentoSalida` | sí | sí |
| `GET /api/documentos/{documento_id}/fichero` | documentos_api.py:389 | fichero | sí | sí |
| `POST /api/documentos/{documento_id}/anular` | documentos_api.py:407 | `DocumentoSalida` | sí | sí |
| `GET /api/documentos/listado` | documentos_api.py:444 | dict | sí | sí |
| `POST /api/facturas/leer` | facturas_api.py:107 | `FacturaLeidaSalida` | sí | sí |
| `POST /api/facturas` | facturas_api.py:246 | `FacturaSalida` (201) | sí | sí |
| `GET /api/facturas` | facturas_api.py:522 | `list[FacturaSalida]` | sí | sí |
| `GET /api/facturas/estado` | facturas_api.py:535 | dict | sí | sí |
| `GET /api/facturas/resumen` | facturas_api.py:546 | `list[dict]` | sí | sí |
| `GET /api/facturas/{factura_id}` | facturas_api.py:559 | `FacturaSalida` | sí | sí |
| `POST /api/facturas/{factura_id}/fichero` | facturas_api.py:565 | `FacturaSalida` | sí | sí |
| `GET /api/facturas/{factura_id}/fichero` | facturas_api.py:597 | fichero | sí | sí |
| `POST /api/facturas/{factura_id}/anular` | facturas_api.py:612 | `FacturaSalida` | sí | sí |
| `PUT /api/facturas/{factura_id}` | facturas_api.py:777 | `FacturaSalida` | sí | sí |
| `DELETE /api/facturas/{factura_id}` | facturas_api.py:860 | dict | sí | sí |
| `GET /api/firmas/estado` | firmas_api.py:256 | `EstadoFirma` | sí | sí |
| `GET /api/firmas/fichero` | firmas_api.py:295 | texto plano | sí | sí |
| `GET /api/firmas/preparar` | firmas_api.py:314 | dict | sí | sí |
| `POST /api/firmas` | firmas_api.py:342 | `FirmaSalida` (201) | sí | sí |
| `GET /api/firmas` | firmas_api.py:456 | `list[FirmaSalida]` | sí | sí |
| `GET /api/cuaderno/resumen` | cuaderno.py:617 | dict | sí | sí |
| `GET /api/cuaderno/falta` | cuaderno.py:658 | dict | sí | sí |
| `GET /api/cuaderno/export.csv` | cuaderno.py:737 | CSV | sí | sí |
| `GET /api/cuaderno/pdf` | cuaderno.py:939 | PDF | sí | sí |
| `POST /api/borradores/desde-texto` | borradores_api.py:52 | `BorradorSalida` | sí | sí |
| `GET /api/interfaz` | interfaz.py:17 | dict (textos) | **NO** | n/a |
| `GET /api/ayuda` | cuaderno.py:1248 | dict | **NO** | n/a |
| `GET /api/ayuda/{campo}` | cuaderno.py:1294 | dict | **NO** | n/a |

#### Cuaderno de la Junta y volcado oficial

| Método y camino | Fichero:línea | Salida | Sesión | Filtro |
|---|---|---|---|---|
| `POST /api/cuaderno-cyl/leer` | cuaderno_cyl_api.py:122 | `CuadernoLeidoSalida` | sí | sí (no escribe) |
| `POST /api/cuaderno-cyl/importar` | cuaderno_cyl_api.py:337 | `ImportacionDelCuadernoSalida` | sí | sí |
| `GET /api/cuaderno-cyl/estado` | cuaderno_cyl_api.py:456 | dict | **NO** | n/a |
| `GET /api/cuaderno-cyl/hojas` | cuaderno_cyl_api.py:470 | dict | **NO** | n/a |
| `GET /api/cuaderno-cyl/que-falta` | cuaderno_cyl_api.py:485 | dict | sí | sí |
| `GET /api/cuaderno-cyl/exportar` | cuaderno_cyl_api.py:498 | XLSX | sí | sí |
| `GET /api/iuws/estado` | iuws_api.py:66 | dict | sí | sí |
| `GET /api/iuws/contenido` | iuws_api.py:140 | dict | sí | n/a (no lleva datos) |
| `GET /api/iuws/paquete` | iuws_api.py:173 | JSON | sí | sí |
| `GET /api/iuws/paquete.json` | iuws_api.py:186 | JSON | sí | sí |
| `GET /api/iuws/version` | iuws_api.py:206 | dict | **NO** | n/a |
| `GET /api/iuws/comprobar-de-verdad` | iuws_api.py:272 | dict | **NO** | n/a (devuelve comprobaciones históricas guardadas; no sale a internet) |
| `POST /api/iuws/leer-respuesta` | iuws_api.py:318 | dict | **NO** | n/a |
| `GET /api/iuws/mensajes` | iuws_api.py:347 | dict | **NO** | n/a |

#### Sistema (`main.py`)

| Método y camino | Fichero:línea | Salida | Sesión | Filtro |
|---|---|---|---|---|
| `GET /health` | main.py:134 | dict | **NO** | n/a (dice si hay zonas vulnerables cargadas) |
| `GET /api` | main.py:142 | dict | **NO** | n/a |

### 2.3. Rutas que NO exigen sesión

**24 rutas sin `UsuarioActual` ni `ExplotacionActual`** (de las **170** declaradas en
`backend/app/routers/*.py`), más `/health` y `/api`, que están en `main.py:134` y `main.py:142` y
tampoco piden sesión: **26 en total**. Se agrupan por lo que significan: 4 + 17 + 3 = 24 en los
routers.

1. **Alta y entrada** (tiene sentido): `POST /api/cuenta/registro`, `POST /api/cuenta/entrar`,
   `GET /api/cuenta/certificado/estado`, `POST /api/cuenta/entrar-con-certificado`.
2. **Catálogos y textos oficiales** (no llevan datos de nadie, y está dicho en el propio código:
   `parcelas.py:594-597`): `GET /api/municipios`, `GET /api/sigpac/buscar`,
   `GET /api/sigpac/estado`, `POST /api/sigpac/consultar`, `GET /api/zonas-vulnerables/estado`,
   `GET /api/mapa/estado`, `GET /api/mapa/imagen`, `POST /api/mapa/punto`,
   `GET /api/interfaz`, `GET /api/ayuda`, `GET /api/ayuda/{campo}`,
   `GET /api/iuws/version`, `GET /api/iuws/comprobar-de-verdad`,
   `POST /api/iuws/leer-respuesta`, `GET /api/iuws/mensajes`,
   `GET /api/cuaderno-cyl/estado`, `GET /api/cuaderno-cyl/hojas` → **17 rutas**.
   (Y, aparte de los routers, `GET /health` (`main.py:134`) y `GET /api` (`main.py:142`), que
   tampoco piden sesión: `/health` dice si hay zonas vulnerables cargadas y `/api` es la portada
   de la documentación.)
3. **Las tres que conviene mirar aunque hoy no filtren nada** (ver 2.4): `POST /api/planes/validar`
   (`planes_api.py:159-165`), `POST /api/analiticas/validar` (`analiticas_api.py:286-293`) y
   `POST /api/medidas/validar` (`medidas_api.py:98-104`) **no piden nada**: ni sesión, ni finca.
   Son **puras**: no leen ni escriben base de datos, así que **hoy no filtran nada de nadie**. El
   riesgo no es la fuga de hoy, es que son la excepción que permite que mañana alguien añada una
   consulta ahí dentro sin que nada lo pare.
   **Y el contraste, que es lo que hay que copiar**: `POST /api/tratamientos/validar`
   (`registros.py:180-185`) hace lo mismo —validar sin guardar— y **sí** pide `ExplotacionActual`,
   porque por dentro carga la parcela, el producto, el aplicador, la máquina, el local y el asesor
   con `obtener_de_la_explotacion` (`registros.py:43-46` y `130-139`). Las otras tres no lo hacen
   porque hoy no cargan nada; el día que lo hagan tendrán que pedir la finca igual.
   Las tres firmas, literales:
   - `planes_api.py:159-160` → `def validar_plan_endpoint(datos: PlanAbonadoEntrada) -> dict:`
   - `analiticas_api.py:286-287` → `def validar_analitica_endpoint(datos: AnaliticaEntrada) -> dict:`
   - `medidas_api.py:98-99` → `def validar_medidas_endpoint(datos: MedidasEntrada) -> dict:`

### 2.4. Filtros dudosos o ausentes (lo que hay que mirar)

Estas son las que **no filtran por explotación** o donde el filtro depende de una llamada
indirecta que conviene vigilar:

| Ruta | Fichero:línea | Qué pasa |
|---|---|---|
| `POST /api/mapa/punto` | mapa.py:133 (cuerpo 134-170) | **Sin sesión y sin finca.** Pregunta al SIGPAC por una coordenada. No devuelve datos del agricultor, pero es una consulta abierta a un servicio externo con parámetros del que llama. El contrato (§4, S02) ya avisa de que «una consulta por coordenada no acredita propiedad»: ni la acredita ni la comprueba. |
| `GET /api/mapa/imagen` | mapa.py:79 | **Sin sesión.** Es un proxy a IGN/SIGPAC: cualquiera puede usarlo como proxy de imágenes. No devuelve datos del agricultor. |
| `GET /api/zonas-vulnerables/estado` | parcelas.py:1168 | **Sin sesión.** Dice qué listado oficial hay cargado. No lleva datos de nadie, pero **sí revela el estado del servidor** y no está documentado como público (los otros dos —`/sigpac/estado` y `/mapa/estado`— sí lo están, parcelas.py:594-597 y mapa.py:46). |
| `GET /api/iuws/comprobar-de-verdad` | iuws_api.py:272 | **Sin sesión, pero no sale a internet.** Devuelve constantes con el resultado de comprobaciones anteriores. La ruta de llamada saliente es `GET /api/iuws/version?llamar=1` (`iuws_api.py:206-249`), también pública: conviene limitar quién puede activarla o su frecuencia antes de exponer el servidor. |
| `GET /api/iuws/paquete`, `GET /api/iuws/paquete.json` | iuws_api.py:173, 186 | Sí piden `ExplotacionActual`, así que **sí filtran**… pero el filtro real no se ha leído línea a línea en este inventario: **no comprobado** que todo lo que arma el paquete pase por `obtener_de_la_explotacion`. |
| `GET /api/cuaderno/export.csv`, `GET /api/cuaderno/pdf` | cuaderno.py:737, 939 | La firma **sí** pide `ExplotacionActual`, y de ahí sale `explotacion.id`, pero **la consulta se arma en funciones auxiliares** (`_tratamientos`, `_fertilizaciones`, `_labores`) que hay que leer una a una: **no comprobado** que las tres filtren por finca. Es el punto que más conviene verificar antes de tocar el cuaderno. |
| `GET /api/firmas/estado`, `/fichero`, `/preparar`, `POST /api/firmas` | firmas_api.py:256, 295, 314, 342 | El filtro pasa por `_texto_y_huella(db, explotacion, …)`. Se ha visto que la función recibe `explotacion` (266-268, 304-306, 325-327) pero **no se ha leído su cuerpo entero**: **no comprobado** que `entidad_id` de otra finca dé 404 en todos los casos. |
| `POST /api/tratamientos/validar`, `/fertilizaciones/validar`, `/cosecha/validar` | registros.py:180, 400, 664 | Sí filtran: pasan por `_contexto_*` → `_cargar` → `obtener_de_la_explotacion` (registros.py:43-46, 130-139, 346-359). **Comprobado.** |
| `GET /api/parcelas`, `/productos`, … (listados) | varios | Filtran con `.where(Modelo.explotacion_id == explotacion.id)`. Comprobado en `registros.py:248-250`, `planes_api.py:150-152`, `facturas_api.py:526`, `ventas_api.py:130-140`, `maestros.py:1031-1033`. |

**Una nota sobre el aislamiento que sí está bien hecho y conviene no romper**: `deps.py:74-85`
devuelve **404** donde lo natural sería 403, para no revelar si un identificador existe en otra
finca. Y `planes_api.py:43-52` extiende esa regla a un campo que **no es clave foránea**
(`analitica_id`), con el motivo escrito.

---

## 3. De la API a la pantalla

**Método**: se han buscado todas las apariciones de `/api/` en `backend/web/**/*.js` (excluyendo
`vendor/`), incluidas las rutas construidas con plantilla (`/api/tratamientos/${id}`). Fichero
principal de llamadas: `backend/web/app.js` (11.351 líneas), con la capa `api()` / `apiJson()`
en `app.js:315-339`. Las pantallas de React (`web/react/pantallas/*.js`) **no llaman a la API**:
son puras y reciben los datos ya resueltos (dicho en `montar.js:7` y en la cabecera de cada
pantalla). Todo pasa por `app.js`.

### 3.1. Rutas con puerta (alguien las llama)

| Ruta | Quién la llama |
|---|---|
| `/api/interfaz` | `app.js:3580` (y desde 27 ficheros más solo por comentario) |
| `/api/cuenta/registro` | `app.js:3732` |
| `/api/cuenta/entrar` | `app.js:3734` |
| `/api/cuenta/certificado/estado` | `app.js:906` |
| `/api/cuenta/entrar-con-certificado` | `app.js:917` |
| `/api/fincas` | `app.js:1861` |
| `/api/fincas/quien-entra` | `app.js:1862`, `app.js:1884` |
| `/api/fincas/quien-entra/{id}` (DELETE) | `app.js:1908` |
| `/api/fincas/cambiar` | `app.js:1931` |
| `/api/mi-finca` (GET y PUT) | `app.js:1780`, `app.js:3649` |
| `/api/campanas` (GET, POST) | `app.js:3629`, `app.js:3820` |
| `/api/campanas/actual` | `app.js:3625` |
| `/api/campanas/{id}` (PUT/DELETE) | `app.js:4697` |
| `/api/parcelas` (GET, POST) | `app.js:3629`, `app.js:6138` |
| `/api/parcelas/{id}` (PUT/DELETE) | `app.js:4574` |
| `/api/parcelas/desde-sigpac` | `app.js:5769` |
| `/api/parcelas/desde-sigpac/varias` | `app.js:6015` |
| `/api/parcelas/{id}/cultivos` (GET, POST) | `app.js:8812` |
| `/api/parcelas/{id}/cultivos/{campana}` (DELETE) | `app.js:8916` |
| `/api/cultivos` | `app.js:3642` |
| `/api/grupos` (GET, POST) | `app.js:3643`, `app.js:6142` |
| `/api/grupos/{id}` (PUT/DELETE) | `app.js:4592` |
| `/api/grupos/calcular` | `app.js:9006` |
| `/api/municipios` | `app.js:5933` |
| `/api/sigpac/buscar` | `app.js:5967` |
| `/api/mapa/imagen` | `app.js:5558` |
| `/api/mapa/punto` | `app.js:5739` |
| `/api/productos` (GET, POST) | `app.js:3630`, `app.js:6149` |
| `/api/productos/cesta/situacion` | `app.js:3641` |
| `/api/fertilizantes` (GET, POST) | `app.js:3631`, `app.js:6152` |
| `/api/aplicadores` (GET, POST) | `app.js:3632`, `app.js:6153` |
| `/api/asesores` (GET, POST) | `app.js:3633`, `app.js:6154` |
| `/api/equipos` (GET, POST) | `app.js:3634`, `app.js:6155` |
| `/api/instalaciones` (GET, POST) | `app.js:3635`, `app.js:6156` |
| `/api/tratamientos` (GET, POST) | `app.js:3655`, `app.js:3951` |
| `/api/tratamientos/{id}` (PUT/DELETE) | `app.js:4510` |
| `/api/tratamientos/{id}/anular` | `app.js:4543` |
| `/api/fertilizaciones` (GET, POST) | `app.js:3656`, `app.js:3956` |
| `/api/fertilizaciones/{id}` (PUT/DELETE) | `app.js:4511` |
| `/api/fertilizaciones/{id}/anular` | `app.js:4544` |
| `/api/labores` (GET, POST) | `app.js:3657`, `app.js:3962` |
| `/api/labores/{id}` (PUT/DELETE) | `app.js:4513` |
| `/api/labores/{id}/anular` | `app.js:4546` |
| `/api/cosecha` (POST) | `app.js:3959` |
| `/api/cosecha/{id}` (PUT/DELETE) | `app.js:4512` |
| `/api/planes` (GET, POST) | `app.js:3636`, `app.js:3846` |
| `/api/planes/{id}` (PUT/DELETE) | `app.js:4638` |
| `/api/analiticas` (GET, POST) | `app.js:3637`, `app.js:3897` |
| `/api/analiticas/{id}` (PUT/DELETE) | `app.js:4620` |
| `/api/analiticas/{id}/informe` (GET, POST) | `app.js:10910`, `app.js:10928` |
| `/api/medidas` (GET, PUT, DELETE) | `app.js:3638`, `app.js:10273`, `app.js:10346` |
| `/api/ventas` (GET, POST) | `app.js:3639`, `app.js:3871` |
| `/api/ventas/{id}` (PUT/DELETE) | `app.js:4629` |
| `/api/documentos` (GET, POST) | `app.js:3640`, `app.js:7460` |
| `/api/documentos/{id}` (PUT/DELETE) | `app.js:4653`, `app.js:7456` |
| `/api/documentos/{id}/fichero` (POST, GET) | `app.js:7480`, `app.js:7521`, `app.js:7541` |
| `/api/documentos/listado` | `app.js:7562` |
| `/api/facturas` (GET, POST) | `app.js:3646`, `app.js:8475` |
| `/api/facturas/estado` | `app.js:3647` |
| `/api/facturas/leer` | `app.js:8329` |
| `/api/facturas/{id}` (PUT, DELETE) | `app.js:4668`, `app.js:8465` |
| `/api/facturas/{id}/fichero` (POST, GET) | `app.js:8090`, `app.js:8109` |
| `/api/firmas` (GET, POST) | `app.js:3658`, `app.js:9585` |
| `/api/firmas/estado` | `app.js:3645` |
| `/api/firmas/fichero` | `app.js:9526` |
| `/api/cuaderno/resumen` | `app.js:3659` |
| `/api/cuaderno/falta` | `app.js:3644` |
| `/api/cuaderno/export.csv` | `app.js:5120` |
| `/api/cuaderno/pdf` | `app.js:5095` |
| `/api/cuaderno-cyl/leer` | `app.js:5408` |
| `/api/cuaderno-cyl/importar` | `app.js:5442` |
| `/api/cuaderno-cyl/que-falta` | `app.js:1794`, `app.js:3648` |
| `/api/cuaderno-cyl/exportar` | `app.js:1955` |
| `/api/borradores/desde-texto` | `app.js:9419` |

### 3.2. Rutas que **no llama nadie** (puertas que no existen)

Estas rutas existen en el servidor y **ningún fichero de `backend/web/` las llama**. Se han
comprobado una a una buscando el camino literal en todo el JavaScript de la web.

**Datos que se pueden escribir pero no se ven, o que existen sin puerta:**

| Ruta | Fichero:línea | Qué es |
|---|---|---|
| `GET /api/analiticas/informe` | analiticas_api.py:217 | El «Informe Analíticas» (todas las de la campaña). **Se arma entero y nadie lo pide.** |
| `GET /api/analiticas/{id}/parametros` | analiticas_api.py:454 | Los números del boletín, sueltos. |
| `POST /api/analiticas/{id}/anular` | analiticas_api.py:373 | Anular un análisis. En la pantalla **solo se puede corregir o borrar** (`app.js:4620`). |
| `GET /api/ventas/informe` | ventas_api.py:148 | El «Informe Cosechas Comercializadas». **Nadie lo enseña.** |
| `GET /api/ventas/resumen` | ventas_api.py:235 | Lo vendido contra lo cosechado. |
| `POST /api/ventas/validar` | ventas_api.py:260 | Validación previa. La pantalla manda directo a `POST /api/ventas` (3871). |
| `POST /api/ventas/{id}/anular` | ventas_api.py:324 | Anular una venta. La pantalla solo corrige o borra (`app.js:4629`). |
| `POST /api/facturas/{id}/anular` | facturas_api.py:612 | Anular una factura. Igual: la pantalla solo corrige o borra (`app.js:4668`). |
| `GET /api/facturas/resumen` | facturas_api.py:546 | Lo comprado por producto, con su factura. Existe y **nadie lo pide**. |
| `GET /api/planes/{id}/resumen` | planes_api.py:230 | El plan con lo aplicado, resumido. El listado general (146) sí se usa. |
| `POST /api/planes/validar` | planes_api.py:159 | Validación previa del plan. |
| `POST /api/analiticas/validar` | analiticas_api.py:286 | Validación previa del análisis. |
| `POST /api/medidas/validar` | medidas_api.py:98 | Validación previa de las medidas. |
| `POST /api/tratamientos/validar` | registros.py:180 | **Validación previa del tratamiento.** Existe, está probada y **la pantalla no la llama** (no aparece `/validar` en ningún fichero de `web/`). Las comprobaciones que ve el agricultor son las de `nucleo.js` (obligatorios y superficie, `nucleo.js:334-373`) y las del guardado. |
| `POST /api/fertilizaciones/validar` | registros.py:400 | Igual. |
| `POST /api/cosecha/validar` | registros.py:664 | Igual (esto es lo que hace que el aviso de los días de espera se vea **solo al guardar**). |
| `GET /api/medidas/informe` | medidas_api.py:186 | El informe de medidas preventivas. |
| `GET /api/avisos` | maestros.py:1019 | **La lista de lo que caduca y lo que falta.** Con toda su lógica de ITV, carne, caducidades y número de registro oficial: existe y **ninguna pantalla la enseña**. Se puede comprobar que no aparece ni «avisos» ni «todo_bien» en `backend/web/`. |
| `GET /api/firmas/preparar` | firmas_api.py:314 | La orden de AutoFirma ya montada. La pantalla usa `/firmas/fichero` (9526) y compone la orden de otra manera. |
| `GET /api/cuenta/yo` | cuenta.py:125 | Nunca se llama. |
| `POST /api/cuenta/vincular-certificado` | cuenta.py:238 | **No se puede vincular un certificado desde la pantalla.** La ruta existe. |
| `GET /api/cuaderno-cyl/estado` | cuaderno_cyl_api.py:456 | Qué cuaderno de la Junta hay cargado. |
| `GET /api/cuaderno-cyl/hojas` | cuaderno_cyl_api.py:470 | Las 25 hojas, por nombre. |
| `GET /api/sigpac/estado` | parcelas.py:591 | Qué datos del SIGPAC hay bajados. |
| `POST /api/sigpac/consultar` | parcelas.py:604 | «Comprueba esta referencia antes de apuntarla». Existe para eso y **no hay botón**. |
| `GET /api/zonas-vulnerables/estado` | parcelas.py:1168 | Qué listado de zonas hay. |
| `GET /api/mapa/estado` | mapa.py:44 | Las capas y sus límites. |
| `GET /api/ayuda`, `GET /api/ayuda/{campo}` | cuaderno.py:1248, 1294 | La ayuda por campo. La pantalla de ayuda se sirve por `/api/interfaz` (`ayuda.js:96`). |
| **Las 8 rutas de `/api/iuws/*`** | iuws_api.py:66, 140, 173, 186, 206, 272, 318, 347 | **El volcado oficial entero no tiene ninguna pantalla.** No aparece «iuws» en ningún fichero de `backend/web/`. |
| `GET /api/productos/{producto_id}` | maestros.py:271 | La ficha de un producto, suelta. Del producto solo se usa la lista y `/cesta/situacion`. |
| `GET /api/instalaciones/{instalacion_id}` | maestros.py:934 | La ficha de una nave, suelta. Solo se usa la lista. |
| `GET /health`, `GET /api` | main.py:134, 142 | No los llama la pantalla (el `service-worker.js:298` menciona `/health` solo para **no** guardarlo en caché). |
| `GET /api/parcelas/{parcela_id}`, `GET /api/tratamientos/{id}`, `GET /api/facturas/{id}` (GET suelto) | parcelas.py:699, registros.py:260, facturas_api.py:559 | **Dudoso**: el camino literal existe en `app.js` (4574, 4510, 4668), pero se usa para las operaciones de corregir y borrar. **No comprobado** que la pantalla pida alguna vez la ficha suelta con `GET`. |

### 3.3. Un campo que existe y no tiene puerta

De la lectura de `models.py` contra `schemas.py` y contra la web:

- **`Parcela.superficie_sigpac_ha`** (`models.py:200`) sale en `ParcelaSalida`
  (`schemas.py:229`) pero **no está en `ParcelaEntrada`** (`schemas.py:120-140`) ni en
  `ParcelaDesdeSigpac` (153-168). Y en la web, `superficie_sigpac_ha` **no aparece ni una vez**
  (búsqueda en todo `backend/web/**/*.js`: 0 resultados). Es decir: la columna existe, se
  devuelve, y **no hay ninguna forma de que el agricultor la meta a mano** — solo se rellena al
  traer del SIGPAC (`parcelas.py:202`) o al importar el cuaderno de la Junta
  (`cuaderno_cyl_api.py:291`).
- **`Labor.detalles`** es JSON y ahí viven el producto y los kilos de la cosecha
  (`registros.py:718`). El contrato (§2, «Guardar un dato del cuaderno») dice que un dato con
  nombre y número va en su propia columna: **estos dos no la tienen**.

---

## 4. Estados que existen de verdad

Esta sección describe **lo que hay**, no lo que el contrato pide. Cuando el contrato (§3, «Estados
obligatorios») nombra nueve estados, aquí se dice cuáles existen y cuáles no.

### 4.1. El error

**Códigos HTTP que el servidor usa de verdad** (contados sobre `backend/app/*.py` y
`backend/app/routers/*.py`):

| Código | Cuándo | Ejemplos |
|---|---|---|
| **401** | No hay sesión, el vale no vale, la cuenta no está activa, no hay acceso a esa finca | `deps.py:26-57` (cuatro casos distintos, con cuatro mensajes distintos) |
| **403** | La cuenta no está activa; no se puede firmar con ese certificado | `cuenta.py:115`, `cuenta.py:215`, `firmas_api.py:242`, `firmas_api.py:246` |
| **404** | «Eso no está en tu cuaderno» (el aislamiento), y «todavía no hay ningún año creado» | `deps.py:83`; y el vacío disfrazado de 404 en **7 sitios**: `analiticas_api.py:87`, `cuaderno.py:256`, `explotacion.py:154`, `firmas_api.py:57`, `iuws_api.py:62`, `planes_api.py:39`, `ventas_api.py:54` |
| **409** | Un apunte **firmado** no se borra; una campaña con cosas dentro no se borra | `registros.py:119-122`, `explotacion.py` (borrado de campaña) |
| **413** | El fichero que se sube pesa más de lo admitido | `adjuntos.py:102`, `adjuntos.py:140` |
| **422** | Hay algo que **bloquea** el guardado | 28 usos. La forma más común es `{"puede_guardarse": False, "avisos": [...]}` con los avisos **ya redactados** (`registros.py:73-83`) |
| **503** | El servicio de fuera (SIGPAC, mapa) no contesta | `parcelas.py:395, 483, 576, 623`, `mapa.py:120, 170` |

**Cómo viaja el mensaje.** Dos formas, y son distintas:

1. **Texto plano en `detail`.** En su mayoría **no** sale de `textos.py`, sino escrito a mano en
   el router. Contado sobre `backend/app/routers/*.py`: hay **95 líneas con `detail=`**, de las
   cuales solo **38** pasan por `textos.mensaje(...)`/`textos.*`; **26 están escritas a mano**
   (22 con `detail="…"` y 4 con `detail=f"…"`), y el resto son diccionarios de avisos o
   `detail=str(error)`. Ejemplos literales: `"Todavía no hay ningún año creado."`,
   `"Ese año no está en tu cuaderno."`, `"Dinos por qué lo anulas, para que quede apuntado."`,
   `"No se han podido leer los datos de la factura."`, `"Eso no parece un fichero de firma."`,
   `f"No se pueden cambiar estos datos: …"` (`explotacion.py:48`),
   `f"«{datos.tipo_fertilizacion}» no es un tipo de abonado. …"` (`registros.py:420-423`).
   Esto contradice el §3.1 de `AGENTS.md` («todo el texto que ve el agricultor vive en
   `textos.py`») y hay que decirlo: **en los routers hay 26 mensajes escritos a mano**. Solo
   **8 códigos distintos** se piden con `textos.mensaje("...")` desde los routers — aunque esas
   8 llamadas aparezcan en 38 líneas.
2. **Estructura con avisos** `{"puede_guardarse": bool, "avisos": [{codigo, mensaje, bloquea,
   campo}]}` (`schemas.py:1090-1099`), donde `mensaje` **sí** viene de `textos.py` vía
   `validaciones.Aviso`.

**Cómo lo enseña el cliente.** `apiJson` (`app.js:326-339`) convierte cualquier respuesta no-`ok`
en un `Error` con el texto del servidor, o con el genérico `mensaje("no_se_pudo")`. Un **401**
dispara `salir(false)` y tira al agricultor fuera (`app.js:319-322`).

### 4.2. El vacío

**No hay un estado «vacío» en el servidor.** Un listado sin datos es **200 con `[]`**
(por ejemplo `registros.py:257`). El vacío se representa de tres maneras distintas y ninguna es
un estado explícito:

1. **Lista vacía** (lo normal): `GET /api/tratamientos`, `/parcelas`, `/ventas`…
2. **404 con mensaje de vacío**: «Todavía no hay ningún año creado.» en **7 ficheros**
   (los de 4.1). Es un **vacío disfrazado de error**: el cliente no puede distinguir «no hay
   nada todavía» de «no es tuyo», porque los dos son 404.
3. **Campos `null` calculados a propósito** para no mentir: `CampanaSalida.cuantas_cosas`,
   `apuntes`, `tierras_con_cultivo`, `otras_cosas` (`schemas.py:101-112`) son `None` cuando no se
   han contado, con el motivo escrito: «un cero sería mentira».

En el cliente, cada listado lleva su propio texto de vacío (`app.js:1094`, `1513`, `1519`…), y
hay un detalle fino que **sí está bien resuelto**: cuando `/api/cuaderno/falta` no ha llegado, la
pantalla **no dice «no te falta nada»** (`app.js:1520-1525`). Es el único sitio donde se ha visto
esa distinción.

### 4.3. La carga

**No existe en el servidor.** No hay ningún endpoint que devuelva «estoy trabajando». El estado de
carga es **solo del cliente**:

- Texto `aviso.cargando` en la cabecera (`app.js:3774`).
- El mapa tiene su propio `cargando` (`app.js:5496`, `5678`; `react/pantallas/mapa.js:35, 51`).
- **No hay barra de progreso, ni «pendiente de enviar», ni «conflicto»** en ninguna parte que se
  haya podido leer.

### 4.4. El «dato incompleto» — el estado que **sí** está trabajado

Aquí es donde el programa tiene más hecho, y conviene distinguir tres mecanismos distintos:

1. **Lo que falta del cuaderno propio** — `GET /api/cuaderno/falta` (`cuaderno.py:658-729`).
   Comprueba **cuatro** cosas: tierra sin cultivo declarado (681), tratamiento sin justificación
   (691), tratamiento sin dosis (700), tratamiento sin aplicador o sin máquina (714). Devuelve
   `esta_completo`, `pendientes` y `mensaje`. **Ojo con `esta_completo`**: es `not pendientes`
   (726) y el `mensaje` es `A8_todo_en_orden` (728) — ver el hallazgo de T02.
2. **Lo que falta del cuaderno de la Junta** — `GET /api/cuaderno-cyl/que-falta`
   (`cuaderno_cyl_api.py:485-495`). No es una lista escrita a mano: sale de **escribir el
   cuaderno entero y mirar lo que quedó en blanco**; lo que no está puesto **sale vacío y no con
   un cero** (dicho en `cuaderno_cyl_api.py:503-504`).
3. **Lo que falta del volcado oficial** — `GET /api/iuws/estado` (`iuws_api.py:66-137`).
   Devuelve `faltan` con `{clave, que, por_que, quien, bloquea}` (125-134) y `cuantas_faltan`;
   cada pieza que falta dice **de quién depende** (`iuws.lo_que_falta`, iuws_api.py:79). Es el
   único sitio del programa que dice «esto no lo puedo hacer yo». **No tiene pantalla** (§3.2).

Y dos mecanismos de aviso que **no bloquean**:

- Los avisos del §`/validar` y del guardado: `Aviso(codigo, mensaje, bloquea, campo)`
  (`schemas.py:1090-1095`), con `bloquea=False` para todo lo que es un aviso y no un impedimento.
  El criterio está escrito en `validaciones.py:346-351`: las reglas de nitratos **avisan y no
  bloquean** «porque el cuaderno tiene que recoger lo que de verdad ha pasado».
- La cola sin cobertura (`web/nucleo.js:140-206`): el apunte se guarda en el móvil
  (`localStorage`, clave `cuedigital.pendientes`) y `decideQueHacer` (201-206) devuelve
  `{accion: "nada" | "esperar" | "mandar", cuantos}`. **No hay estado «pendiente de enviar»
  con nombre propio en la API**: el apunte encolado existe solo en el navegador, y el servidor
  no sabe nada de él. **No comprobado**: qué se enseña al agricultor sobre la cola (el texto
  existe, pero no se ha mirado la pantalla en un navegador).

### 4.5. Estados del contrato que **no existen**

Comparando con el §3 del contrato («Estados obligatorios»):

| Estado que pide el contrato | ¿Existe? |
|---|---|
| cargando | Solo en el cliente (texto y mapa). No en el servidor. |
| vacío nuevo | No como estado: es `[]` o un 404 de vacío. |
| sin resultados por filtro | **No existe**: no hay filtros en el servidor ni paginación. Los listados devuelven todo y el cliente filtra. |
| acceso restringido | Sí, pero **404 y no 403** a propósito (`deps.py:74-85`). 403 solo para cuenta inactiva y para firmar. |
| servicio no disponible | Sí: **503** para SIGPAC y mapa. |
| copia local antigua | Solo en el cliente (`app.js:3582-3587`: si `/api/interfaz` falla, se usa lo guardado). |
| pendiente de enviar | Solo en el cliente (la cola). |
| conflicto | **No existe.** No hay versión esperada ni detección de edición simultánea. |
| guardado | Sí: **201** al crear (hay `status_code=status.HTTP_201_CREATED` en 25 rutas). |
| dato incompleto | Sí, y por tres caminos (4.4). |

### 4.6. Una cosa que el cliente borra: el fallo se convierte en vacío

En `cargarDatos` (`app.js:3590-3660`), **las 25 llamadas que alimentan la pantalla llevan
`.catch(() => null)` o `.catch(() => [])`**:

```
app.js:3625  apiJson("/api/campanas/actual").catch(() => null),
app.js:3629  apiJson("/api/campanas").catch(() => []),    apiJson("/api/parcelas").catch(() => []),
app.js:3630  apiJson("/api/productos").catch(() => []),
…                                  (igual hasta app.js:3659)
```

Es decir: **si el servidor contesta 500, o no contesta, el estado en memoria queda igual que si
la finca estuviera vacía**, salvo en el caso de `faltantes`, que sí se distingue (1520-1525). El
contrato lo dice expresamente al revés («No presentar una tabla vacía cuando falló la consulta»):
**hoy, para 24 de las 25 piezas, se presenta la tabla vacía.** Esto no es una opinión sobre el
diseño: es lo que hace el código, y es el hallazgo más repetido de este inventario.

---

## 5. Esquemas (`backend/app/schemas.py`, 1.533 líneas)

Dos bases: `EntradaBase` (`schemas.py:16-17`, con `str_strip_whitespace=True`) y `SalidaBase`
(20-21, con `from_attributes=True`). Ninguna entrada hereda de la de salida.

**La decisión que gobierna todo el fichero** (escrita en `schemas.py:3-7`): los campos que el
agricultor no tiene por qué saber (dosis máxima, plazo de espera, abono puro) se aceptan
opcionales y **se rellenan solos desde el producto o el abono**.

### 5.1. Entidades de negocio principales

#### Explotación

- **`ExplotacionEntrada`** (29-44): `nombre` (obligatorio, 1-200), `nif` (obligatorio, 1-20),
  `codigo_siex=None`, **`ccaa="Castilla y León"`**, **`provincia=""`**, **`municipio=""`**,
  **`produccion_ecologica=False`**, y `None` para registro nacional/autonómico, dirección,
  localidad, código postal, teléfono y correo.
- **`ExplotacionSalida`** (47-62): todos los campos del modelo, con los mismos nombres.

#### Campaña

- **`CampanaEntrada`** (65-68): `anio` (2000-2100), `fecha_inicio`, `fecha_fin`. **No pregunta
  `cerrada`**: nace abierta.
- **`CampanaCorreccion`** (71-86): lo de arriba **más `cerrada: bool` obligatorio**, y el motivo
  está escrito (80-83): si se pudiera omitir, corregir el año **volvería a abrir una campaña
  cerrada sin que nadie lo pidiera**.
- **`CampanaSalida`** (89-112): `cuantas_cosas`, `apuntes`, `tierras_con_cultivo`, `otras_cosas`
  → **`int | None = None`**, a propósito: «un cero sería mentira» (97-100).

#### Parcela

- **`ParcelaEntrada`** (120-140): `alias` (1-120, obligatorio), `ref_sigpac=None`,
  **`provincia=""`**, **`municipio=""`**, `codigo_ine=None`, polígono/parcela/recinto `None`,
  **`agregado=0`**, **`zona=0`**, `referencia_catastral=None`, **`superficie_ha: float = Field(ge=0)`
  (obligatoria, pero admite 0)**, **`superficie_oficial=False`**, `uso_sigpac=None`,
  **`sistema="secano"`**, `pendiente_pct=None`, **`masa_agua_cerca=False`**,
  **`captacion_consumo_humano=False`**, `zona_vulnerable_nitratos=None` (bien: tres estados),
  `geometria=None`.
  **Falta `superficie_sigpac_ha`** (está en el modelo y en la salida, no en la entrada).
- **`ParcelaSalida`** (214-254): añade `codigo_ine`, `superficie_sigpac_ha`, `agregado=0`,
  `zona=0`, `referencia_catastral`, y las dos calculadas `centro` (250) y `dibujo` (254).
- **`ParcelaDesdeSigpac`** (153-168): `ref_sigpac` (5-60), `alias=None`, **`sistema="secano"`**,
  `provincia=None`, `municipio=None`, `referencia_catastral=None`. No hereda municipio de la
  explotación a propósito (162).
- **`VariasParcelasDesdeSigpac`** (195-211): `referencias` (1-200), **`sistema="secano"`**, resto
  `None`.

#### Grupo de parcelas

- **`GrupoEntrada`** (277-282): `nombre` (1-120), `campana_id=None`, `cultivo=None`,
  **`sistema="secano"`**, `parcela_ids=[]` (factoría).
- **`GrupoSalida`** (285-292): igual más `id` y `creado_automaticamente`.

#### Producto fitosanitario (la más delicada de todas)

- **`ProductoEntrada`** (300-318): `nombre_comercial` (1-200), `tipo_producto=None`,
  `numero_registro=None`, `materia_activa=None`, **`dosis_maxima=None`** (`gt=0`),
  **`unidad_dosis="L/ha"`**, **`plazo_seguridad_dias=None`** (`ge=0`), `lote=None`,
  `fecha_caducidad=None`, `cantidad_comprada=None`, **`unidad_compra="L"`**, `fecha_compra=None`,
  `proveedor=None`, **`autorizado=True`**, **`permitido_ecologico=True`**,
  `autorizacion_excepcional=None`, `autorizacion_hasta=None`, `foto_etiqueta=None`.
- **`ProductoSalida`** (321-347): todo lo de arriba con los mismos defectos, más las compras y la
  autorización, que «faltaban en la salida» y por eso **las tres comprobaciones que dependen de
  ellas no podían saltar nunca** (341-346).

#### Fertilizante — el «cero nutrientes»

- **`FertilizanteEntrada`** (350-355): `nombre` (1-200), **`tipo="mineral"`**,
  **`riqueza_n=0.0`**, **`riqueza_p=0.0`**, **`riqueza_k=0.0`** (los tres con `ge=0, le=100`).
- **`FertilizanteSalida`** (358-364): los mismos tres sin defecto (los devuelve el modelo).

#### Tratamiento fitosanitario

- **`TratamientoEntrada`** (466-513): `campana_id` y `fecha` obligatorios; **`tipo="parcela"`**;
  `parcela_id`, `grupo_id`, `instalacion_id`, `producto_cosechado`, `lote_cosecha` → `None`;
  `superficie_tratada_ha=None` (`gt=0`); `cultivo`, `variedad`, `plaga`, `justificacion`,
  `estado_cultivo` → `None`; `producto_id=None`, `lote_producto=None`; `dosis=None` (`gt=0`);
  **`unidad_dosis="L/ha"`**; `volumen_caldo_l_ha=None`; `unidad_cantidad_aplicada=None`;
  aplicador, equipo, asesor y sus fechas → `None`; los tres booleanos del asesoramiento y las
  condiciones → `None` (aquí **sí** distinguen «no lo sé» de «no», 505-507);
  `aplicado_a_mano=None`, `eficacia=None`, `plazo_reentrada_dias=None`, `operadores_expuestos=None`;
  **`medidas=[]`**; `incidencias=None`, `observaciones=None`.
  **No acepta `en_zona_vulnerable`**: eso lo decide el servidor (ver T02).
- **`TratamientoSalida`** (516-578): sin defectos peligrosos; **`unidad_dosis: str`** y
  **`en_zona_vulnerable: bool`** son obligatorios (es decir, siempre hay un valor, y por eso el
  `False` que pone `servicios.py:102` **siempre viaja**).

#### Fertilización (abono)

- **`FertilizacionEntrada`** (586-606): `campana_id`, `fecha`, **`superficie_ha` (`gt=0`)**,
  **`kg_ha_producto` (`gt=0`)** obligatorios; `parcela_id`, `grupo_id`, `fertilizante_id`,
  `modo_aplicacion`, `momento`, `plan_id`, `numero_albaran`, `tipo_fertilizacion`, `factura_id` →
  `None`; `nitratos_agua_riego=None`; `observaciones=None`.
  **No acepta riqueza ni unidades fertilizantes ni `en_zona_vulnerable`**: todo eso lo calcula
  `servicios.preparar_fertilizacion` (111-161).
- **`FertilizacionSalida`** (609-638): los seis `uf_*` y las tres riquezas **sin defecto**, y
  `en_zona_vulnerable: bool` obligatorio.

#### Plan de abono

- **`AbonoPrevisto`** (646-652): `fertilizante_id=None`, `nombre=None`, `kg_ha=None`, `momento=None`.
- **`PlanAbonadoEntrada`** (655-675): `campana_id` obligatorio; **`cultivo: str = ""`** y
  **`superficie_ha: float = Field(default=0.0, ge=0)`** — **a propósito sin `min_length` ni
  `gt=0`** (659-661), para que el hueco llegue a `validaciones.py` y el agricultor reciba el
  aviso escrito (`F6_sin_cultivo_en_el_plan`, `F7_sin_superficie_en_el_plan`,
  `validaciones.py:539-543`); `necesidad_n/p/k`, `aportes_suelo_agua`, `produccion_esperada` →
  `None`; **`detalle=[]`**; `herramienta=None`; `notas=None`; `analitica_id=None`.
- **`PlanAbonadoSalida`** (678-693) y **`PlanConLoAplicado`** (696-723): este último añade
  `cultivo_precedente`, `aplicado_n/p/k` (sin defecto), `queda_n/p/k` (nullable), `se_ha_pasado`,
  `apuntes`, `mensaje` y el `analisis` resuelto.

#### Venta de cosecha

- **`VentaEntrada`** (735-754): `campana_id`, `fecha` obligatorios; **`tipo="comercializada"`**;
  `fecha_fin=None`; **`producto: str = ""`** y **`cantidad: float | None = None`** — otra vez a
  propósito sin mínimo, para que el aviso salga escrito (`validaciones.py:611-618`);
  **`unidad="kg"`**; `lote`, `comprador`, `numero_albaran`, `parcela_id`, `grupo_id`,
  `observaciones` → `None`.
- **`VentaSalida`** (757-777): `cantidad: float` obligatoria (la del modelo), `anulado: bool`, y
  **`kilos: float | None = None`** calculado al vuelo (774-776).
- **`InformeDeVentas`** (789-801): `vendido_kg`, `cosechado_kg`, `queda_kg`, `hay_unidades`, etc.

#### Labor (y cosecha)

- **`LaborEntrada`** (960-1008): `campana_id`, `tipo`, `fecha` obligatorios; **todo lo demás es
  `None`**: `superficie_ha`, cultivo, variedad, `detalles`, observaciones, y los ~25 campos de
  siembra, pastoreo, cubierta y riego (con `ge=0` donde es una cantidad).
- **`LaborSalida`** (1011-1065): los mismos, todos `= None` menos los obligatorios.
- **`CosechaEntrada`** (1072-1087): `campana_id`, `fecha`, **`parcela_id: int`** obligatorios;
  `producto=None`, `cantidad_kg=None`, los cuatro booleanos `None`, `equipo_id=None`.

#### Análisis, medidas, documentos, facturas, firmas

- **`AnaliticaEntrada`** (889-903): `campana_id`, `tipo`, `fecha_toma_muestra` obligatorios;
  `parametros=[]`; resto `None`. `ParametroEntrada` (871-887) acepta `valor: float | str | None`
  **a propósito** (el «7,4» con coma).
- **`AnaliticaSalida`** (906-930): `etiqueta_tipo=""`, `parametros=[]`, `anios=None`.
- **`MedidasEntrada`** (821-831): **`aplicadas=[]`**, **`observaciones={}`**. **`MedidaEntrada`**
  (813-818): `codigo` obligatorio y **`aplicada=True`**.
- **`DocumentoEntrada`** (1298-1312): `titulo` (1-200) obligatorio, **`tipo="otros"`**,
  **`carpeta=""`** (luego el router la cambia por «Otros»: `documentos_api.py:206`), `fecha=None`,
  `quien=None`, `notas=None`, `campana_id=None`.
- **`LineaDeFacturaEntrada`** (1409-1433): `descripcion` obligatoria; `cantidad`, `unidad`,
  `precio_unitario`, `importe` → `None`; `numero_registro=None`, `lote=None`; `producto_id=None`;
  `fertilizante_id=None`; **`crear_producto=False`**.
- **`FacturaEntrada`** (1436-1448): **todo `None`** (fecha, proveedor, NIF, número, base, cuota,
  tipo de IVA, total, notas, `leida_por`) y **`lineas=[]`**. **No hay ni un defecto numérico**:
  una factura a medias se guarda con huecos de verdad, no con ceros. Esto está bien.
- **`FirmaEntrada`** (1236-1246): `entidad` (1-40) y **`huella` exactamente de 64 caracteres**
  obligatorios; `entidad_id=None`, `campana_id=None`, `nombre_del_fichero=None`,
  `contenido=None` (opcional a propósito, 1244-1245).
- **`BorradorSalida`** (1219-1228): **es el contrato para un modelo de lengua** (dicho en
  1186-1199). `datos: dict` libre **a propósito**, porque un borrador está incompleto por
  definición y obligarle a tener la forma completa «animaría a rellenar los huecos con inventos».

### 5.2. Esquemas de salida que devuelven más de lo que el modelo tiene

- `ParcelaSalida.centro` y `.dibujo` (250, 254) — calculados con `geo`.
- `AnaliticaConSitio.donde` y `.parametros_con_nombre` (941-942) — resueltos en el servidor a
  propósito (935-939).
- `VentaConNombres.etiqueta_tipo`, `.donde`, `.etiqueta_unidad`, `.texto_cantidad` (783-786).
- `LineaDeFacturaSalida.producto`, `.fertilizante`, `.cuadra` (1464-1468) — `cuadra` se calcula
  al devolver, no se guarda.
- `DocumentoSalida.tiene_fichero` (1332) — «un papel apuntado sin fichero es un recordatorio».
- `PlanConLoAplicado` entero.

**Un detalle que rompe el patrón y conviene saber**: `PlanConLoAplicado` referencia
`AnaliticaConSitio`, que está declarada **más abajo**, y por eso el módulo termina con
`PlanConLoAplicado.model_rebuild()` (`schemas.py:1342`). Sin esa línea, pedir un plan falla con
«AnaliticaSalida is not defined». Cualquier reordenación del fichero que mueva esa llamada lo
rompe.

---

## 6. Resumen de lo que este inventario deja señalado

1. **Ninguna tabla de negocio tiene autor, y ninguna tiene versión.** La única traza está en
   `auditoria.usuario_id`, que es opcional y que algunos caminos no rellenan.
2. **La anulación no es uniforme**: 7 tablas la tienen (una con otro nombre) y el resto se borra.
3. **Tres rutas de validación no exigen sesión** (`planes_api.py:159`, `analiticas_api.py:286`,
   `medidas_api.py:98`) y **el mapa y el SIGPAC son abiertos** (coherente con que no lleven datos
   de nadie). La ruta pública `GET /api/iuws/version?llamar=1` sí provoca tráfico saliente;
   `GET /api/iuws/comprobar-de-verdad` solo muestra resultados históricos guardados.
4. **Hay 39 rutas sin ninguna pantalla** (más `/health` y `/api`, que no son funciones del
   agricultor), incluidas las 8 del volcado oficial y los tres `/validar` del registro obligatorio.
   El caso más llamativo es `GET /api/avisos` (`maestros.py:1019`): toda la lógica de caducidades
   y del registro oficial de productos, funcionando y sin puerta. El desglose está en §3.2.
5. **El vacío se representa como 404** en 7 sitios, con el mismo texto duplicado, y el cliente
   **no puede distinguirlo de «eso no es tuyo»**.
6. **El cliente convierte 24 de sus 25 fallos de carga en «vacío»** (`app.js:3625-3659`).
7. **El «dato incompleto» sí está trabajado por tres caminos**, y el del IUWS es el único que
   dice de quién depende cada hueco. Ninguno de los tres tiene pantalla salvo el del cuaderno de
   la Junta.
8. **En `schemas.py` los huecos que bloquean se dejan a propósito sin mínimo** (`cultivo: str = ""`,
   `superficie_ha = 0.0`, `producto: str = ""`) para que el aviso salga escrito y no como un error
   técnico. Es una decisión consciente y está documentada en el propio fichero.
9. **Y la contraria**: `ProductoEntrada.autorizado=True`, `permitido_ecologico=True`,
   `FertilizanteEntrada.riqueza_*=0.0`, `ParcelaEntrada.sistema="secano"`. Esos cuatro defectos
   **no** son huecos que se dejan pasar: son afirmaciones que el programa hace sin preguntar. Es
   el objeto del informe T02.
