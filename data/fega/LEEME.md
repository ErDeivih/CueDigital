# Los catálogos oficiales del cuaderno

> **Ojo con dos catálogos que se llaman parecido.** La tabla `Unidades` del MAPA (la de esta
> carpeta, del registro de fitosanitarios) **no es** la tabla `UNIDADES_MEDIDA` de SIEX (del
> cuaderno). Una viene del MAPA y la otra del FEGA, y **sus valores no son los mismos**.

Esta carpeta **no se escribe a mano**: la llena `backend/scripts/bajar_catalogos_fega.py`, que
baja los ficheros oficiales tal y como los publica la administración, comprueba que son lo que
dicen ser y apunta de dónde salen, cuándo y con qué huella. Los tests **no salen a internet**:
leen estos ficheros.

**Fecha de la última descarga:** 27/09/2026.

## Lo que hay aquí

| Fichero | Qué es | De dónde sale | Comprobado | SHA-256 |
|---|---|---|---|---|
| `anexo_ix_autorizacion_acceso_rea_cue.docx` | Anexo IX: modelo de autorización de acceso a REA y al cuaderno | <https://www.fega.gob.es/sites/default/files/files/document/2023.11.10-ANEXO%20IX.Modelo_autorizaci%C3%B3n_acceso_REA_CUE_PUBLICADO.docx> | 18,172 bytes | `0258bd0915c3606f6998ea3f63703c5e7894c482619dcf4408aa2b1f0a47aa82` |
| `anexo_v_definicion_de_variables_3.11.xlsx` | Anexo V: definición de las variables de REA y del cuaderno (hojas REA y CUE) | <https://www.fega.gob.es/sites/default/files/files/document/2025.11.20-ANEXO_V_Definicion_de_variables_3.11_CORRECCION_ERRORES_PUBLICACION.xlsx> | 302 filas en «CUE» (2 hojas: REA: 246, CUE: 302) | `0f7391ff59df46d83fd18071cbed8765033dd269497cc7704d60258d84e16e19` |
| `anexo_vi_interfaz_unico_comun_3.11.4.docx` | Anexo VI: el interfaz único común (v3.11.4), con los métodos y las cabeceras | <https://www.fega.gob.es/sites/default/files/files/document/2025.11.19-ANEXO%20VI.Interfaz%20%C3%9Anico%20Com%C3%BAn_V3_11_4.docx> | 2,955,796 bytes | `8acd60aca62e002533ac8c4aa45d2ffb820fa94c849f72d11bff63474f418d5d` |
| `anexo_viii_autorizacion_representacion.docx` | Anexo VIII: modelo de autorización de representación (lo firma el titular) | <https://www.fega.gob.es/sites/default/files/files/document/2023.11.10-ANEXO%20VIII.%20Modelo_autorizacion_representaci%C3%B3n_PUBLICADO.docx> | 17,176 bytes | `9a0428f343b88d62a43e441884f66d5934cd5e7af7da83a58707e8a8b3e48366` |
| `anexo_x_procedimiento_autorizacion_cue.pdf` | Anexo X: procedimiento de autorización y las direcciones del interfaz por comunidad | <https://www.fega.gob.es/sites/default/files/files/document/2024.05.17-ANEXO_X-ProcedimientoAutorizacionCUE_PUBLICADO.pdf> | 313,858 bytes | `68610f0a3a9dc20c93c74299ff7e4916d6df54b0f64045ae43a2ba46063e33e9` |
| `documento_tecnico_siex_3.11.pdf` | Documento Técnico SIEX 3.11 (el diseño del cuaderno y de los catálogos) | <https://www.fega.gob.es/sites/default/files/files/document/2025.11.14-DT%20AGRICOLA_v3.11_CORRECCION%20ERRORES_LIMPIO.pdf> | 1,100,498 bytes | `0fc059a380f34115dccab04e9a7eb5eaced89464e52e49f5486b7ac26cabcf87` |
| `mapa_acciones.xlsx` | Acciones del producto sobre el organismo | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 10 filas en «Acciones» (1 hoja: Acciones: 10) | `723dae38aeaeebe17aeb160ef0d053f6aa22625efcfe3e58f9db9dcfb8e65a14` |
| `mapa_ambitos.xlsx` | Ámbitos de aplicación | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 5 filas en «Ambitos» (1 hoja: Ambitos: 5) | `77200db7b63c2da8e3ea38b0a2edadd4a7f9b2bb52aa7f36bf60598029271a88` |
| `mapa_clasificaciones.xlsx` | Clasificaciones y etiquetado | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 179 filas en «Clasificaciones» (1 hoja: Clasificaciones: 179) | `f483005d823dda667df3960093adc9ce9c727eebe786563b7cd5c2961cffb42d` |
| `mapa_coformulantes.xlsx` | Coformulantes | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 17207 filas en «CoFormulantes» (1 hoja: CoFormulantes: 17207) | `85bf98ceb87a1d6b54d81e85675fdeeb53f7a1df9e14f4881dde45efb2473aa1` |
| `mapa_funciones.xlsx` | Funciones del producto | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 31 filas en «Funciones» (1 hoja: Funciones: 31) | `a5df3948012123aee9ef2aec22e4961f19eb6b89f0a4d8f43ef7d1242a1a48ec` |
| `mapa_jerarquia.xlsx` | Jerarquía de especies vegetales (el nombre oficial de cada cultivo) | <https://www.mapa.gob.es/dam/mapa/contenido/agricultura/temas/sanidad-vegetal/medios-de-defensa-fitosanitaria/registro-productos-fitosanitarios/jerarquia.xlsx> | 816 filas en «Hoja1» (1 hoja: Hoja1: 816) | `86c815c15b867e4dc9125f5f971a23aff78ff071e1c8e4091999909563e1d9b0` |
| `mapa_metodos_aplicacion.xlsx` | Métodos de aplicación | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 20 filas en «MetodosAplicacion» (1 hoja: MetodosAplicacion: 20) | `1ce246bbb406c92672c912a972b3605dff7dfa63d2588c7afb7ac917e09bc07d` |
| `mapa_plagas.xlsx` | Clasificación oficial de plagas | <https://www.mapa.gob.es/dam/mapa/contenido/agricultura/temas/sanidad-vegetal/medios-de-defensa-fitosanitaria/registro-productos-fitosanitarios/plagas.xlsx> | 604 filas en «Enfermedades (grupos 8-11)» (5 hojas: Nota explicativa: 1, Malas hierbas (grupos 1-5): 207, Artrópodos y gasterópodos (6-7): 537, Enfermedades (grupos 8-11): 604, Reguladores y otros (12-19): 59) | `75b1ffbff4d48a155d598db2d89e99d194ffc413086177119eee97843d0e17ab` |
| `mapa_preparados.xlsx` | Tipos de preparado (formulación) | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 88 filas en «Preparados» (1 hoja: Preparados: 88) | `7c47b8f0702b9c5528c877c6512720ac030aef1e3d5c7b84eb4aa17cdb50f225` |
| `mapa_productos_fitosanitarios.xlsx` | Listado completo de productos fitosanitarios registrados (el registro oficial) | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcelFiltroProducto> | 3087 filas en «Productos» (1 hoja: Productos: 3087) | `239e2cacb26207ecbf4b9601ef94051562c8998640a7331ef94707144967e643` |
| `mapa_prudencias.xlsx` | Frases de prudencia (las «P» de las etiquetas) | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 237 filas en «Prudencias» (1 hoja: Prudencias: 237) | `ad4ed579e98e4532dfbfba43b4a7a0e094afed6151c749a4ac246790ad0804f7` |
| `mapa_riesgos.xlsx` | Riesgos (las «H» y las «EUH») | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 240 filas en «Riesgos» (1 hoja: Riesgos: 240) | `93fe25863f5f61f2891394e058570e43783f48bdcb3c8580325b68376c103fbc` |
| `mapa_sistemas_cultivo.xlsx` | Sistemas de cultivo | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 7 filas en «SistemasCultivo» (1 hoja: SistemasCultivo: 7) | `f6bdbc8956379095211e2ad7940aa0d0cdf96980fca9199710f56fab570d7837` |
| `mapa_tipos_sustancia.xlsx` | Tipos de sustancia activa | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 11 filas en «TiposSustancia» (1 hoja: TiposSustancia: 11) | `297df4d0251cac3c4672b1bdce14495944754ec40b1c47944176defaa4ca6cea` |
| `mapa_tipos_usuario.xlsx` | Tipos de usuario | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 5 filas en «TiposUsuarios» (1 hoja: TiposUsuarios: 5) | `8b487235fb5fe1cf3ca9568a1b263fb9b1901406941948fe6313d6b28c5a1075` |
| `mapa_translocaciones.xlsx` | Translocación en la planta | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 15 filas en «Translocaciones» (1 hoja: Translocaciones: 15) | `6b5002efc92aeaa884abefc3397a6ddd50f37f60a0630b4c251c5421395f2ebb` |
| `mapa_unidades.xlsx` | Unidades de medida del registro de fitosanitarios | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 124 filas en «Unidades» (1 hoja: Unidades: 124) | `c8c5e6ecb6bdc0cca80aa0b093fe40938fe1ec6b2f80a295ac22e3383b5e3661` |
| `mapa_utilizaciones.xlsx` | Utilizaciones | <https://servicio.mapa.gob.es/regfiweb/Exportaciones/ExportExcel> | 52 filas en «Utilizaciones» (1 hoja: Utilizaciones: 52) | `f9cdb22249f8cf8b68db58b2d92c1c4fe674b7b491aeb0c01e2a276b17c5de31` |

## Lo que NO está aquí, y por qué

Esto es lo más importante de este documento: **lo que falta se dice, no se rellena**.

| Dirección | Qué es | Por qué no está |
|---|---|---|
| <https://www3.sede.fega.gob.es/bdcsixpor/catalogos> | Los VALORES de los catálogos de SIEX (incluida la tabla UNIDADES_MEDIDA) | está detrás de un captcha de Google (reCAPTCHA). No se pasa: saltarse un captcha es saltarse la norma de una web. Hay que pedirlos (docs/CORREO_LISTO_PARA_ENVIAR.md) |
| <https://www11.fega.es/bdcsix/login/portal> | El acceso identificado al portal de SIEX | exige usuario y contraseña, y este programa no entra en ninguna cuenta |
| <https://www.fega.gob.es/search/site> | El buscador interno del FEGA | su robots.txt lo prohíbe expresamente: no se usa |
| <https://www.mapa.gob.es/dam/…/registro-productos-fitosanitarios/autorizaciones_excepcionales.xls> | Las autorizaciones excepcionales (33 MB) | es un Excel antiguo (.xls) y este proyecto solo sabe leer los modernos (.xlsx). No se guarda un fichero que no se puede ni abrir |

### Los valores de los catálogos de SIEX: pedidos, no saltados

Los **valores** de los catálogos de SIEX (entre ellos la tabla `UNIDADES_MEDIDA`, que es la que
hace falta para el cuaderno) están detrás de un **captcha de Google** en el portal del FEGA.
**No se pasa**: saltarse un captcha es saltarse la norma de una web, y eso este programa no lo
hace. Lo que sí se tiene es la **estructura** de esos catálogos (los nombres y las columnas de
las 287 tablas), que se baja con `scripts/bajar_catalogos_siex.py` en `data/siex_catalogos.json`.

Para pedirlos hay un correo ya redactado en [`docs/CORREO_LISTO_PARA_ENVIAR.md`](../../docs/CORREO_LISTO_PARA_ENVIAR.md).

## Cómo se regenera

```bash
cd backend
../.venv/Scripts/python.exe scripts/bajar_catalogos_fega.py
```

Se va **despacio** (una petición cada dos segundos) y con un cliente que se identifica. Si un
fichero no llega, el guion **se para y lo dice** con su dirección y su código HTTP: nunca deja
un fichero de relleno. Con `--sin-descarga` se rehace este LEEME sin tocar la red.

## Las condiciones de uso de cada fuente

- **FEGA:** su aviso legal autoriza la reproducción *«siempre que se cite su origen y se difunda
  sin alterar su contenido»*, y añade que si el FEGA exige autorización previa esa autorización
  general no vale. Aquí se cita el origen en cada fila de la tabla de arriba.
- **MAPA:** su aviso legal cita la Ley 37/2007 de reutilización de la información del sector
  público, pero **no declara una licencia concreta**. Se apunta tal cual, sin suponer lo que no
  dice, y se ha preguntado por el ritmo y el permiso a `sgmpagri@mapa.es` (ver el correo).
- **`robots.txt`:** se comprobó el de los tres dominios antes de bajar nada, y ninguna de estas
  direcciones está prohibida. El buscador interno del FEGA (`/search/site`) sí lo está, y **no
  se usa**.
