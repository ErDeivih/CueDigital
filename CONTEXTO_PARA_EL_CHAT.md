# CUE Digital — traspaso para el chat en la nube

Preparado el 18/10/2026 para David. Es contexto de continuidad, no certificación de que
todo el producto esté terminado. Léelo entero antes de proponer trabajo.

## 1. Qué quiere David de este nuevo chat

«Este chat estará en la nube para poder trabajar también desde el móvil. Quiero que
entiendas el repositorio, el producto, sus especificaciones, los cambios y los problemas
para poder seguir desarrollándolo sin empezar desde cero.»

David prefiere usar este chat para arquitectura, revisión, normativa, decisiones de UX y
encargos detallados. DeepSeek implementa el trabajo largo por coste. No gastar rondas en
reconocer una y otra vez lo ya documentado. Darle bloques suficientes para continuar,
con entregas y criterios verificables, y revisar sus resultados con independencia.

ATENCIÓN AL ACCESO: las rutas Windows de este documento son referencias del ordenador
de David. Un chat en la nube no puede leerlas por conocer su nombre. Si no tienes una
copia adjunta o conexión al repositorio, pide los documentos o fuentes necesarios y
declara el límite. No digas que has inspeccionado archivos o ejecutado pruebas sin hacerlo.
No solicites ni difundas certificados privados, claves, bases reales o documentos personales.

## 2. Qué es el producto

CUE Digital empezó como cuaderno de campo y ha evolucionado hacia un CRM/ERP agrario
autohospedado. El cuaderno debe generarse desde la actividad real registrada, no ser
otro formulario que obligue a escribir lo mismo dos veces.

David gestiona unas 64–65 tierras, con distintas campañas y ayuda de otras personas.
Ese número es contexto histórico, no una constante del programa. Debe servir a otras
explotaciones, superficies y cultivos, no solo al conjunto de prueba.

Dos usos igual de importantes:
- Despacho: aplicación de gestión profesional con tablas, filtros, mapas, fichas,
  documentos, cuentas, planificación y varios paneles. David rechazó el aspecto de
  «móvil estirado», controles gigantes y funcionalidades dispersas.
- Campo: móvil legible, acciones claras y poco esfuerzo para registrar trabajos,
  cantidades y documentos, incluso con problemas de cobertura.

Objetivo de experiencia: navegar por explotación y campaña, abrir una ficha desde
cualquier contexto, entender cada cifra y llegar a los registros que la explican.
No trasladar complejidad de implementación al agricultor ni ocultar información faltante.

## 3. Alcance funcional deseado

1. Tierras: SIGPAC, geometría real, mapa con selección coherente con tabla/filtros,
   cultivos e historial por año. Agujeros, multipolígonos y solapes sin inventar superficie.
2. Trabajos: planificar, ejecutar, corregir y anular. Rodillo, cultivador o siembra deben
   quedar en la historia; planificar no equivale a haberlo hecho ni cambia el cultivo real.
3. Insumos: compra, lote/envase, existencias y consumo por tierra. Ejemplo: comprar 5 L,
   aplicar 2 y 3 en dos tierras, saldo correcto; anular devuelve lo que corresponde.
4. Fitosanitarios: marca/producto, autorización, etiqueta, dosis, fechas, cantidad y
   unidad, plazos y evidencias. Lo firmado conserva los datos históricos de aquel día.
5. Abonos: composición y fuente, cantidad, unidad, superficie tratada, kg/ha y nutrientes.
   Distinguir porcentaje en masa de g/L; sin densidad no convertir litros y % m/m en kg N.
   No confundir P con P2O5 ni K con K2O.
6. Semillas: especie, variedad, procedencia, categoría y evidencia; desconocido no se
   convierte automáticamente en «no certificada». Categorías dependen de especie/ámbito.
7. Economía: compras, facturas, gastos, ventas, entregas, cobros/pagos parciales,
   anticipos, pendientes, inversiones y costes. No duplicar factura y gasto enlazados.
8. Bancos: importación y conciliación de extractos, reenvíos, asignaciones y deshacer.
   Conexión bancaria directa es una aspiración futura, no acreditada como disponible.
9. Contactos: cliente/proveedor/taller y otros papeles, canales y direcciones múltiples,
   notas con autor, tareas, saldos separados y fusión con auditoría.
10. Trabajos para terceros: cliente, tierras externas, maquinaria, insumos y facturación;
    las hectáreas de un cliente no se suman a la superficie propia ni a su PAC.
11. Maquinaria: disponibilidad, ITV/ITEAF y otras obligaciones según clasificación y
    aplicabilidad acreditada, documentos, averías, taller, costes, contadores y reservas.
12. PAC: preparación por recinto y campaña, historial de cultivos, ecorrégimen elegido,
    compromisos y evidencias, escenarios futuros y paquete para asesor. No envío directo
    ni afirmación automática de elegibilidad sin reglas aplicables y datos suficientes.
13. Paneles: explotación, tierras, economía, agenda y maquinaria; cifras con unidad,
    periodo, fuente, cobertura y enlace al detalle; personalización y filtros coherentes.
14. Futuro: lluvia observada/estimada/pronosticada, satélite y observaciones de campo.
    Una inferencia de estado del cultivo no debe presentarse como hecho comprobado.
15. OCR: fotos y papeles, propuestas revisables y vínculo al original. No asumir precisión
    demostrada: necesita evaluación con corpus autorizado y casos representativos.

## 4. Ubicación y arquitectura

Repositorio activo: F:\EspacioCodigo\CueDigital.
F:\CuadernoCampo es otra carpeta con materiales/fuentes; no confundirla con el destino activo.

- Backend Python: FastAPI, Pydantic y SQLAlchemy, dependencias en backend/requirements.txt.
- SQLite local por defecto: backend/cuedigital.db. Es la base real, NO un resto de pruebas.
  La URL depende de CUEDIGITAL_DATABASE_URL y del directorio de arranque.
- PostgreSQL es un destino previsto; no declarar equivalencia completa sin pruebas en ese motor.
- Geometría: texto WKT en Parcela.geometria. No asumir que ya existe una columna PostGIS.
- Frontend: JavaScript con módulos ES y React/HTM servidos directamente, sin compilación npm.
  backend/package.json marca type=module. Hay vendor local.
- app.js orquesta estado, navegación, peticiones y presentación; componentes en
  backend/web/react/, pantallas en react/pantallas/, piezas en react/piezas/.
- Navegación por hash, con campañas y explotación en el contexto. Recarga, Atrás y
  Adelante son comportamientos que hay que comprobar.
- Service worker/PWA y caché versionada. No atribuir cualquier fallo de pantalla a caché.
- app/models.py: persistencia; app/schemas.py: contratos; app/routers/: rutas;
  app/servicios.py: reglas compartidas; app/textos.py: textos de la interfaz.
- Módulos de dominio nuevos: maquinaria.py, reservas.py, nutrientes.py, superficies.py,
  reenvios.py, paneles.py, pac.py, accesos.py, entre otros.
- Pruebas: backend/tests/ y backend/tests_js/. Los guiones de scripts/ hacen recorridos
  contra servidores y navegadores reales, con escenarios aislados.

Arranque local habitual, desde backend:
..\.venv\Scripts\python.exe -m uvicorn app.main:app
No arrancarlo contra la base real para pruebas o migraciones experimentales.

## 5. Documentos que deben gobernar la continuidad

En el repositorio:
- AGENTS.md: convenio de trabajo. Leer antes de editar.
- DESIGN.md: diseño, tokens, legibilidad y componentes.
- docs/PLAN_CRM_AGRARIO_2026.md
- docs/ESPECIFICACION_DETALLADA_CRM_2026.md
- docs/CONTRATO_IMPLEMENTACION_CRM.md
- docs/MATRIZ_NORMATIVA_CRM.md
- docs/SEGUIMIENTO_IMPLEMENTACION_CRM.md
- docs/ESTADO_DEL_REDISENO.md
- docs/T04_CONTRATO_NAVEGACION.md
- docs/REACT.md
- docs/LO_QUE_OBLIGA_LA_LEY.md y docs/LO_QUE_PIDE_LA_JUNTA.md
- docs/FUENTES_OFICIALES_PENDIENTES.md y documentación de IUWS.

Perfil de coordinación fuera del repositorio:
F:\EspacioCodigo\ProyectoServidor\rea-sandbox\estudiar-apps\perfiles\cuedigital\

Leer LEER-PRIMERO.md, COLA.md, ESTADO.md y CONTINUAR-AQUI.md, pero priorizar
el código y las revisiones recientes cuando haya contradicciones históricas.
CONTINUAR-AQUI ha crecido mucho; no asumir que su primer estado antiguo es el actual.

Revisiones independientes más recientes en ese perfil:
- REVISION_2026-10-14.md: semillas, superficies/unidades y cola detallada.
- RESCATE_2026-10-15.md, con añadido del 16: cuenta-horas y errores de diagnóstico.
- REVISION_PERMISOS_2026-10-18.md: permisos y alcance de verificaciones.
- REVISION_PAC_2026-10-18.md: defectos de fotos PAC y falta de recorrido completo.

COLA.md organiza CRM-00 a CRM-12. No crear otro plan contradictorio; actualizar el
contrato existente y mantener separados hecho, parcial, pendiente y bloqueo externo.

## 6. Estado de Git EN EL MOMENTO DE ESTE TRASPASO

Rama: estabilizacion-2026-10-18.
Último commit observado: eec9e55, independencia entre campañas.
La rama principal seguía en 949c595 según las entregas; no se ha fusionado ni publicado
en esta conversación. Comprobar el estado al retomar.

IMPORTANTE: el árbol YA NO ESTÁ LIMPIO. Se observaron 14 ficheros modificados y un nuevo
backend/scripts/andar_el_recorrido_de_la_pac.py, posteriores a la última revisión.
Son trabajo PAC en curso de otro agente. No resetear, sobrescribir ni dar por verificado.

Los documentos actuales anuncian 5528 pruebas Python y 1143 JavaScript; son recuentos
del trabajo en curso, NO suites ejecutadas por este revisor ahora.
La entrega anterior del agente anunciaba 5524/1143 con salida 0.
Los números cambian con nuevos ficheros: no convertirlos en constantes del encargo.

## 7. Últimos cambios y verificaciones independientes

### Semillas
El alta guardaba categoría/procedencia, pero la corrección las borraba y el formulario
no las enviaba. Se corrigió backend y ambos borradores de frontend. Ausencia pasó a
«No consta». Hubo recorrido con recarga y auditoría. No reabrir ese reconocimiento.

### Maquinaria y rescate del cuenta-horas
El agente persiguió una supuesta caché durante nueve rondas. La causa real: lecturas y
contador estaban dentro del map de averías y no en la ficha exterior. Se reprodujo
ejecutando la función real. Se corrigieron colocación, retrocesos intermedios, huecos,
unidades incompatibles y presentación de cobertura. Se completaron lecturas/reservas
según la entrega posterior, con pruebas y recorridos declarados.

### Incidente de modelos
Un git checkout eliminó trabajo no commiteado de models.py. Se reconstruyeron clases
de lecturas/reservas y columnas de fertilizantes. Se acumulaban más de cien ficheros.
El agente consolidó el trabajo por capas en la rama de estabilización.
No afirmar reconstrucción exacta o migración integral de todos los modelos por suite verde.
Los ensayos revisados sí cubren columnas de fertilizantes e índice de lecturas sobre copia.

### Permisos
El panel exponía 123.45 EUR con permiso económico desactivado, mientras el saldo daba 403.
Se corrigió en servidor conservando el panel agronómico.
El clasificador por sufijos omitía fusion-hacer y contacto-borrar-si, que sí escriben.
Se sustituyó por web/react/acciones.js y filtrado de componentes/DOM; MutationObserver
cubre renderizados React posteriores.

Roles: titular modifica y ve dinero; ayudante modifica sin ver dinero; consulta no hace
ninguna de las dos cosas. Ocultar botones NO autoriza; servidor siempre comprueba.
Consulta se preparó solo en base temporal porque no había puerta para conceder ese rol.

Verificación independiente más reciente: ejecutado verificar_los_permisos_por_rol.py
contra su servidor temporal en HEAD eec9e55: 53 comprobaciones, 0 fallos, salida 0.
Incluye pantallas reales, controles positivos del titular, consulta, ayudante y cambio de
cuenta/explotación. Acredita ese recorrido, no cada permiso de todas las rutas.

### Reenvíos
Se añadieron unicidad, conflicto y comparación de relaciones hijas. El índice solo no
basta. Hubo defectos de comparación de relaciones como columnas y reservas que chocaban
consigo mismas al reintentar. Se corrigieron con pruebas de comportamiento.
No confundir unicidad con idempotencia completa ni comparar una petición original solo
contra una fila ya editada sin definir ese contrato.

### PAC: backend nuevo y revisión ABIERTA
Commits a92bd62 (escenarios), 05282d6 (fotos), eec9e55 (campañas).
Funciones puras y API para comparar escenarios sin alterar cultivos reales. Foto con
contenido, año, versión, fecha y huella; exportación CSV desde contenido guardado.

Sobre eec9e55 este revisor ejecutó 14 pruebas de escenario, fotos e independencia entre
campañas: pasan. Aun así reprodujo dos errores en API con base temporal:
1. Guardar 2027 versión 1 y 2028 versión 1: GET /api/pac/foto/1 devuelve 2027. La identidad
   se numera por año, pero el enlace omite el año. Usar ID único o año + versión.
2. Evaluar, cambiar alias de parcela y guardar: guarda el alias nuevo. POST /foto
   recalcula desde la finca actual en vez de conservar la evaluación mostrada.
   Necesita identidad/huella de evaluación y conflicto si cambió el origen.

En esa revisión la pantalla solo pedía /api/pac/paquete: no había interfaz para escenarios,
comparación, fotos ni exportación. NO podía declararse CRM-09 terminado para el usuario.
Ahora hay cambios sin commit precisamente en PAC: comprobar su implementación y pruebas
antes de afirmar que esos fallos siguen presentes o que ya están reparados.

## 8. Próximo trabajo, sin reiniciar el proyecto

1. Leer el diff PAC pendiente y REVISION_PAC_2026-10-18.md; coordinarse con el agente
   escritor. No volver al diagnóstico de caché ni rehacer la estabilización completa.
2. Cerrar identidad de foto, consistencia con evaluación mostrada, entrada validada,
   concurrencia/reintentos y aislamiento.
3. Recorrido de agricultor: campaña objetivo → cultivos hipotéticos → comparar → datos
   faltantes → guardar versión → historial → exportar la versión exacta.
4. Pruebas de dos años con versión 1, cambios entre vista/guardado, historial inmutable
   y permisos. Hipótesis no es declaración ni trabajo realizado.
5. Terminar verificación y revisión visual de superficies/mapa: filtros 10/64,
   agujeros/multipolígonos, solapes, selección, trabajo vs plan y cambio de campaña.
6. Continuar paneles, fiabilidad, personalización y tareas listas según la cola.
7. OCR, meteo/satélite y banca directa requieren pruebas, fuentes/proveedores y permisos
   adecuados; no anunciar esas capacidades como terminadas sin evidencia.

## 9. Normativa e integración oficial

Usar fuentes BOE, FEGA, MAPA y Junta de Castilla y León, por campaña, ámbito y supuesto.
No repetir fechas de un resumen antiguo como si se hubieran verificado hoy.
Un test que reproduce el contrato no demuestra que el contrato sea jurídicamente correcto.
No afirmar cumplimiento PAC ni elegibilidad por disponer de una exportación.

IUWS es integración separada del uso del cuaderno. El README actual dice que se localizó
descriptor CUE v3.11.4/esquema y se inventarió mapeo de 18 bloques. Exportación oficial
sigue pendiente de catálogos, decisiones de mapeo y prueba autenticada. El viejo relato
de «solo falta BdcSix v2.6.0» es anterior y no debe usarse como estado vigente.
No enviar correos, solicitudes ni datos oficiales sin autorización de David.

## 10. Reglas de trabajo y errores que no deben repetirse

- Unknown no es cero, falso, autorizado, ecológico o certificado.
- Cada registro pertenece a una explotación; permisos económicos y de modificación separados.
- Dinero, existencias, cantidades y superficies tienen unidades y conceptos distintos.
- Historial firmado no cambia cuando se corrige un producto hoy.
- Interfaz: textos centralizados, tokens de diseño y accesibilidad según DESIGN; no copiar
  tamaños de otro CRM sin evaluar el uso de campo y escritorio.
- Leer tests/contratos y cumplir AGENTS al implementar: pruebas, humo y recorrido cuando
  corresponda. Solo afirmar lo ejecutado y explicar omisiones.
- Una prueba de componente aislado no comprueba app.js, su cargador ni la API.
- Buscar una cadena o contar nombres encuentra candidatos; no demuestra comportamiento.
- Una suite verde no equivale a producto completo ni una lista de acciones a autorización universal.
- No insertar por número de línea o una llave ambigua. Leer el bloque real y aplicar parche acotado.
- Hay CRLF y LF mezclados. Preservarlos; evitar diffs completos por formato.
- Nunca git checkout/reset/clean para arreglar un fichero con trabajo no guardado.
- Copia recuperable incluye ficheros nuevos; no sobrescribir una copia completa con una parcial.
- No probar con la base real ni subirla al chat. Huella de referencia observada:
  CC65753395EF33B3E15679BB74EA77A706DD8557615486CEB709F73F12334B12.
- No matar Chrome por nombre: solo procesos/perfiles de pruebas propios identificados.
- Subagentes con ficheros delimitados y un escritor por fichero compartido.
- Tras dos intentos sin evidencia nueva, reproducción mínima y revisión; no inventar otra
  causa ni gastar nueve rondas repitiendo conclusiones.
- Dar a DeepSeek una cola suficiente y pedir que continúe después de cada entrega;
  no confundir autonomía con trabajo indefinido sin criterios de cierre.

## 11. Herramientas externas y referencias

REA: laboratorio F:\EspacioCodigo\ProyectoServidor\rea-sandbox para estudiar aplicaciones
empaquetadas con evidencia. No usar ingeniería inversa para entender nuestras fuentes.
Skills locales rea-windows-local y reverse-engineer-anything gobiernan ese uso.
Las colas de RadioPV/facylf del laboratorio NO son la cola de CUE Digital.

Referencias documentales utilizadas: ERPNext, Odoo, farmOS y AGRIVI. No se ha acreditado
un análisis completo de competidores ni de sus binarios. Copiar decisiones útiles con
código propio, no funcionalidades ajenas sin una necesidad del agricultor.

Stitch ayudó con diseños en docs/stitch/. v0 se planteó para dirección visual con pocos
tokens. No asumir que un chat nuevo tenga esas herramientas o credenciales. Nunca
copiar claves de mensajes antiguos al repositorio o a un traspaso.

## 12. Instrucción de arranque para el chat nuevo

Primero confirma qué archivos puedes consultar realmente. Lee los documentos rectores
y el diff/estado reciente si están disponibles. Resume lo comprobado, los pendientes y
la próxima entrega concreta. No prometas conocer todo el repositorio basándote solo en
este documento. Prioriza terminar el flujo PAC que está en curso y después la cola.
No crear otro plan gigante contradictorio ni pedir de nuevo decisiones ya especificadas.
