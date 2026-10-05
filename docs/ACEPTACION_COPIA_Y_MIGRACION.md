# Aceptación de la copia previa a la migración: qué se sostiene y qué no

Fecha de este documento: **02/10/2026**. Revisión independiente de la entrega del coordinador del
mismo día: la **copia que se hace antes de reconstruir tablas** (`_copia_de_seguridad_del_fichero` y
sus ayudantes), su uso en `reconstruir_para_poder_decir_no_se` y en el guion de migración.

**Qué es este documento.** El resultado de **intentar romper** la entrega, no de confirmarla. Cada
afirmación de aquí lleva su prueba: el nombre de la prueba que la mide o el `fichero:línea` donde se
lee. Cuando algo no se ha podido comprobar, se dice **y se dice por qué**, en vez de darlo por bueno.

**Qué NO es.** No es una auditoría de los datos del agricultor ni una revisión del cuaderno: solo de
la copia y de la migración de esquema. No se ha arrancado ningún servidor, no se ha llamado a
`127.0.0.1:8000` y **no se ha leído ni tocado `backend/cuedigital.db`**: todo lo de aquí se ha medido
con ficheros temporales de `pytest`.

**Cómo se ha hecho.** Leyendo el código entero (no los comentarios de resumen) y **midiendo** el
comportamiento por mi cuenta, con guiones de exploración fuera del repositorio y luego con pruebas de
aceptación. Nada de lo que dice el autor se ha dado por bueno por estar escrito.

**Contra qué revisión se ha medido** (las dos se han quedado quietas durante la revisión):

| Fichero | Líneas | SHA-256 (primeros 12) | Última modificación |
|---|---|---|---|
| `backend/app/database.py` | 511 | `D38C5ACFEC86` | 02/10/2026 12:08:51 |
| `backend/scripts/migrar_zona_de_nitratos.py` | 312 | `C7C41E4410B4` | 02/10/2026 11:03:46 |

**Lo que se ha escrito.** Un fichero, y solo uno, de pruebas de aceptación:
`backend/tests/test_aceptacion_copia_y_migracion.py` — **25 pruebas, 25 pasan, 2,5 s** (leído del
`--junit-xml`). No se ha tocado ningún fichero de la aplicación ni ninguna prueba ajena.

---

## 1. Lo que se afirma, y lo que se ha medido
| Lo que afirma la entrega | ¿Se sostiene? | Dónde está la prueba |
|---|---|---|
| 1. La copia incluye los cambios confirmados que siguen en el `-wal`, y por eso no se copia el fichero sin más | **Sí, con un matiz importante** (§2.1) | `test_la_copia_lleva_las_filas_confirmadas_que_siguen_en_el_wal` |
| 2. La copia se comprueba entera (`quick_check`) **y** con los mismos datos (mismas tablas, mismas filas) | **Sí.** Las dos hacen falta: la de entereza sola **no** caza el caso del WAL | `test_la_copia_lleva_las_filas...` (pasos 2 y 3), `test_una_tabla_que_falta_se_nota` |
| 3. Si falla cualquiera de las dos, no se reconstruye ninguna tabla y el guion sale con 1 | **Sí para las dos comprobaciones**; **no** para una copia que no se puede ni crear (§3.7) | `test_si_la_copia_no_esta_entera...`, `test_si_la_copia_no_tiene_los_mismos_datos...`, `test_el_guion_avisa_en_cristiano...` |
| 4. Sin nada pendiente en el WAL se guarda además una copia byte a byte; con algo pendiente **no** se deja una incompleta | **Sí.** Sin WAL: identidad byte a byte y `sha256` iguales. Con WAL: no queda ningún `-byte-a-byte` | `test_sin_nada_en_el_wal_la_copia_es_byte_a_byte...`, `test_la_copia_lleva_las_filas...` |
| 5. «Volver atrás» deja el fichero exactamente como estaba | **No, tal y como está contado**: si hay un `-wal` al lado, la vuelta atrás **no vuelve** (§3.1) | `test_volver_atras_solo_copiando_la_copia_no_deshace_lo_escrito_despues` |

---

## 2. Lo que se sostiene, con la prueba delante

### 2.1. La copia lleva lo confirmado en el `-wal`… mientras haya otra conexión abierta

Con una conexión escribiendo y **sin cerrar** (que es lo que hace que lo confirmado siga en el
`-wal`), medido con la base realista de 26 tablas:

* El fichero principal, copiado a mano, trae **1** tratamiento y la base **2**: el apunte del WAL no
  está en el principal. La prueba lo comprueba **antes** de creerse lo demás, porque si el principal
  ya tuviera el apunte, la prueba no probaría nada.
* Esa copia a mano **pasa `quick_check`** (`_la_copia_esta_entera` → `True`) y **falla** la
  comprobación de los datos (`_copia_tiene_lo_mismo` → `False`). Es decir: **la comprobación de
  entereza por sí sola no habría cazado nada**, y las dos hacen falta.
* La copia que hace el programa trae las **2** filas, se puede abrir después y su contenido (**todas
  las filas de las 26 tablas**) es igual al de la base.

**El matiz, y es de fondo.** El motivo escrito en el código («los cambios confirmados pueden seguir en
el `-wal` y no estar en el principal; por eso no se copia el fichero sin más») **solo es cierto
mientras haya otra conexión abierta**. Medido en el caso contrario (base quieta, con el `-wal` que
dejó un cierre a lo bruto): el simple hecho de copiar **vacía el WAL**, porque la propia conexión que
abre `_copiar_con_sqlite` (`database.py:332-348`) lo vuelca al principal y lo trunca —

```
tamaño del principal antes:   8192   wal: 4152
copia ofrecida:  ...-byte-a-byte
tamaño del principal después: 8192   wal: 0
```

— y entonces la copia que se devuelve es la **byte a byte**, completa y exacta. O sea: con la base
quieta, copiar el fichero principal sin más **habría bastado**, y es el propio programa el que lo ha
puesto al día antes de copiarlo. Está fijado en
`test_una_base_que_quedo_con_el_wal_de_una_caida_se_copia_entera_y_exacta`. No es un defecto (el
resultado es bueno), pero sí una diferencia entre el motivo que dice el código y lo que pasa de
verdad, y conviene saberlo antes de «simplificar» esto.

**Un `-wal` que existe y está vacío** (0 bytes, lo que deja un `wal_checkpoint(TRUNCATE)` o la propia
copia) se trata como «no hay nada pendiente» y la copia byte a byte que se devuelve **es correcta
porque no había nada que volcar**: comprobado fila a fila en
`test_un_wal_que_existe_y_esta_vacio_se_trata_como_que_no_hay_nada`.

### 2.2. Las dos comprobaciones, y que hacen falta las dos

* `PRAGMA quick_check` sobre la copia: pasa con la copia incompleta del WAL (§2.1).
* «Los mismos datos»: cuenta **las tablas y las filas de cada tabla** de la copia y de la base, y
  exige el mapa entero igual (`database.py:362-395`). Detecta una copia **con menos** filas
  (`test_no_da_por_buena_una_copia_con_menos_filas_que_la_base`), **con más**
  (`test_detecta_una_copia_a_la_que_le_sobra_una_fila`) y a la que le **falta una tabla**
  (`test_una_tabla_que_falta_se_nota`).

Lo que esta comprobación **no** demuestra, medido: compara **números de filas, no valores**. Dos bases
con las mismas filas y los datos cambiados la pasan
(`test_dos_bases_con_las_mismas_filas_y_datos_distintos_pasan_la_comprobacion`). No es un fallo —la
copia la hace la API de copia de SQLite, no se escribe a mano— pero es su límite, y está escrito para
no pedirle más de lo que da.

Y una consecuencia de compararla **con la base viva**: si alguien apunta algo entre la copia y la
comprobación, los números no cuadran y la migración se **rechaza**. Es el lado seguro, pero el mensaje
que sale («no tiene los mismos datos que la base») **culpa a la copia cuando la que se ha movido es la
base** (`test_la_copia_se_compara_con_la_base_viva_y_una_escritura_posterior_la_invalida`).

### 2.3. Si la copia no se puede comprobar, no se reconstruye ninguna tabla

Provocado **de verdad**, sin parchear nada: se le ocupa el nombre a la copia con una carpeta, así que
SQLite no puede escribirla. Resultado: `sqlite3.OperationalError`, la columna `en_zona_vulnerable`
sigue siendo obligatoria y el contenido de todas las tablas es idéntico
(`test_si_la_copia_no_se_puede_ni_crear_la_tabla_no_se_reconstruye`). Y por el camino de verdad del
arranque, `crear_tablas` (`database.py:496-511`), con las dos comprobaciones parcheadas —**se dice que
van parcheadas**, porque hacer fallar de verdad un `quick_check` sobre una copia recién hecha por
SQLite no está al alcance de una prueba—: el error se levanta y no se toca ninguna tabla
(`test_si_la_copia_no_esta_entera_no_se_reconstruye_ninguna_tabla`,
`test_si_la_copia_no_tiene_los_mismos_datos_no_se_reconstruye_ninguna_tabla`).

### 2.4. La copia byte a byte, y la vuelta atrás sin `-wal`

Sin nada pendiente en el `-wal`, la copia que se devuelve es
`…antes-de-migrar-<marca>-byte-a-byte` y es **idéntica** al original: `read_bytes()` igual y el mismo
`sha256` (`test_sin_nada_en_el_wal_la_copia_es_byte_a_byte_y_el_fichero_queda_igual`). Después de
reconstruir las cuatro columnas de `COLUMNAS_QUE_DEJARON_DE_SER_OBLIGATORIAS` con la base realista,
**no cambia ni una fila** (se compara el contenido de todas las filas de las 26 tablas, no los
recuentos) y poner la copia encima devuelve la base **como estaba, esquema incluido**: la columna
vuelve a ser obligatoria y las filas son las mismas
(`test_la_reconstruccion_no_cambia_ni_una_fila`,
`test_la_vuelta_atras_devuelve_la_base_como_estaba_antes_de_migrar`).

Y cuando **sí** hay algo pendiente en el WAL, la copia byte a byte incompleta **no se deja**: en la
carpeta no queda ningún fichero `*-byte-a-byte*` (el `_borrar_copia` de `database.py:316-329` cumple
lo que promete, con sus `-wal`/`-shm`).

---

## 3. Lo que NO se sostiene o queda flojo

### 3.1. La vuelta atrás no vuelve si hay un `-wal` al lado (el defecto más serio)

El guion de migración imprime, literalmente (`migrar_zona_de_nitratos.py:305`):

> `Para volver atrás: copia {copia} encima de {ruta}`

y el docstring de `_copia_de_seguridad_del_fichero` dice lo mismo («se copia esa copia encima del
original»). Eso es un `shutil.copy2` del fichero principal **dejando el `-wal` y el `-shm` donde
están**. Y el `-wal` de la base que se está restaurando puede contener lo que se apuntó **después** de
la copia: SQLite lo vuelve a aplicar encima. Medido, con la base realista y la copia coherente
(la del caso del WAL, que es justo para la que se escribió todo esto):

```
la copia tiene 2 tratamientos
la base tiene 3 (se apuntó uno más después de copiar)
[se copia la copia encima]
la base sigue teniendo 3   ← el apunte de después ha vuelto del -wal
```

Está en `test_volver_atras_solo_copiando_la_copia_no_deshace_lo_escrito_despues`. Y la prueba de que
la causa es el `-wal` de al lado, y no otra cosa, es la de al lado:
`test_volver_atras_quitando_tambien_el_wal_si_deshace_lo_de_despues` — quitando `-wal` y `-shm` antes
de copiar, la base vuelve a los 2 tratamientos de la copia.

**Por qué es serio.** No es un caso raro: es el escenario para el que existe la copia coherente
(alguien tiene la base abierta en modo WAL). El guion **no pide que el programa esté parado**, así que
es normal que el programa siga escribiendo mientras se hace la copia. Y quien sigue la instrucción
cree que ha vuelto atrás cuando en realidad tiene una base mezclada: parte de la copia y parte de lo
de después. El código **ya sabe** que hay que quitar los ficheros de al lado (para eso está
`_borrar_copia`), pero solo lo aplica a sus propias copias, no a la hora de restaurar.

**Lo que está bien y no hay que tocar:** las dos pruebas de arriba están escritas a propósito como
descripción de lo que hace hoy el programa. El día que se arregle (que el aviso diga que hay que
quitar el `-wal` y el `-shm` de la base antes de poner la copia, o que el programa lo haga), la
primera prueba **tiene que fallar**, y eso será la buena noticia.

### 3.2. El guion de migración nunca cambia ni una fila (y deja el trabajo a medias)

El informe del guion cuenta los apuntes que dicen «no está en zona» sin que nadie lo haya comprobado,
y la lista de los que va a cambiar está **siempre vacía**. Medido con una base donde hay exactamente
ese caso (un tratamiento con `en_zona_vulnerable = 0`, su tierra con `zona_vulnerable_nitratos` a
«no lo sé» y ninguna firma):

```
tratamientos: filas=1  sin_saberlo=1  y_firmadas=0
ids que cambiaría: []          ← y el propio informe dice que hay 1
```

La causa está en cómo se arma la consulta (`migrar_zona_de_nitratos.py:113` y `:145-152`):
`_condiciones` devuelve las tres condiciones y la tercera es `"(<sin_saberlo>) AND <firmado>"`, que
**empieza por un paréntesis que cierra antes del `AND`**. Al pegar
`... WHERE {sin_saberlo} AND NOT {firmadas}`, el `NOT` se aplica solo a la primera mitad y la consulta
queda `A AND NOT (A) AND B`: **no puede devolver nada**. Para que dijera lo que se pretendía haría
falta `AND NOT ({firmadas})`.

Consecuencia medida al ejecutar el guion entero (`--migrar`): sale con **1** diciendo «Quedan apuntes
que dicen «no» sin saberlo y sin firma: revisa el informe»… **después de haber reconstruido ya las
columnas**. Es decir, el esquema se queda migrado y el dato sin tocar: la operación se queda a medias,
y el agricultor no ha pasado a «no se ha podido comprobar» ni uno solo de sus apuntes. Lo detecta su
propia comprobación final (`migrar_zona_de_nitratos.py:298-303`), que es lo único que impide que
salga un «todo bien» falso. Está en
`test_el_guion_dice_que_hay_apuntes_que_cambiar_y_luego_no_cambia_ninguno`.

> Ojo: el arreglo **no es mío**, y no lo he hecho. Lo que sí digo es que, mientras esto esté así, la
> migración de datos del apartado A2 **no se ha hecho** aunque el guion se ejecute.

### 3.3. Una sola ejecución del guion deja **cuatro** copias de la base del agricultor

Medido (`test_el_guion_deja_la_columna_admitiendo_no_se_y_no_cambia_ninguna_fila`): el guion hace su
copia a mano (`migrar_zona_de_nitratos.py:265`) y después llama a
`reconstruir_para_poder_decir_no_se` (`:273`), que **hace otra copia por su cuenta**
(`database.py:228`). Y cada una de las dos deja **dos** ficheros (la coherente y la byte a byte). En
una base de 352.256 bytes:

```
realista.db                                             405.504 bytes (después de migrar)
realista.db.antes-de-migrar-<marca>                     352.256
realista.db.antes-de-migrar-<marca>-byte-a-byte         352.256
realista.db.antes-de-migrar-<marca>-<pid>               352.256
realista.db.antes-de-migrar-<marca>-<pid>-byte-a-byte   352.256
```

**Nadie borra ninguna nunca**, y todas se quedan en la misma carpeta que la base. Con esto se entiende
una prueba del coordinador que está en rojo desde antes de que yo empezara:
`backend/tests/test_autorizacion_del_producto.py:499-517` (`test_la_tabla_se_reconstruye_una_sola_vez`)
espera `len(copias) == 1` buscando `catalogo.db.antes-de-migrar-*`, y encuentra **2** (la coherente y
la byte a byte). Su intención —una reconstrucción por tabla, no una por columna— **se cumple**: la
cuenta falla porque cada llamada deja dos ficheros. Esa prueba es del coordinador y **no la he
tocado**; lo apunto aquí porque el síntoma es exactamente este.

### 3.4. Se deja basura (`-shm`, `-wal`) al lado de la base y de la copia

Medido (`test_lo_que_el_programa_deja_al_lado_de_la_base`). Con la base en modo WAL, después de la
copia quedan, junto a la base: `base`, `base-wal`, `base-shm`, la copia, `copia-shm` (**32.768
bytes**) y `copia-wal` (**0 bytes**). Los dos últimos los crean las propias **comprobaciones** al
abrir la copia, y `_borrar_copia` **no** los limpia: solo limpia los de la copia byte a byte. Cuando
la aplicación se cierra, quedan la copia y sus dos ficheros. No es peligroso, pero es basura en la
carpeta del agricultor, y una carpeta con un `-shm` al lado parece una base viva.

### 3.5. «La base se queda intacta» no es literalmente cierto

Las dos comprobaciones y la copia **tocan el fichero del agricultor**, aunque no su esquema ni sus
datos: la conexión que abre `_copiar_con_sqlite` vuelca el `-wal` al principal y lo trunca (medido:
principal 4.096 → 8.192 bytes, `-wal` 12.392 → 0). No se pierde nada y es lo que haría SQLite de
todos modos al abrir la base, pero conviene saber que «no se ha cambiado la estructura de la base de
datos» quiere decir exactamente eso (estructura), no «no se ha tocado el fichero».

### 3.6. Caminos en los que se reconstruye una tabla **sin ninguna copia válida**

Sí, existen, y los dos son reales:

| Camino | Qué pasa | Prueba |
|---|---|---|
| Base **en memoria** (`sqlite://`), que es lo que usan las pruebas con `StaticPool` | `_ruta_del_fichero` devuelve `None` (`database.py:243-253`), no se copia nada y **la tabla se reconstruye igual**, tirándola abajo sin red | `test_en_memoria_no_se_hace_ninguna_copia_y_la_tabla_se_reconstruye_igual` |
| **PostgreSQL**, el de producción | Lo mismo: `_ruta_del_fichero` devuelve `None` y `_copia_de_seguridad_del_fichero` **no copia nada** | `test_con_postgresql_no_se_hace_copia_ninguna` |

En memoria no hay nada que perder, y está claro por qué se acepta. Con PostgreSQL es más delicado:
además de no haber copia, la reconstrucción (`database.py:427-493`) lanza SQL de SQLite
(`PRAGMA foreign_keys=OFF`, `ALTER TABLE … RENAME TO`), que en PostgreSQL no significa lo mismo.
**No he podido probarlo** (no hay servidor de PostgreSQL en esta máquina): lo que está medido es solo
la puerta, que no copia. Queda como lo más flojo de todo lo que no se ha podido comprobar.

Un tercer camino, de la misma familia: si el fichero de la base **no existe**, `_copia_de_seguridad_del_fichero`
devuelve `None` sin decir nada (`database.py:285-286`). En el arranque no pasa (antes se crea el
fichero), pero es la misma puerta.

### 3.7. El mensaje de error no dice qué hacer, y hay fallos que no pasan por él

Los dos mensajes son:

> `La copia previa a la migración no se puede comprobar: <ruta de la copia>. No se ha cambiado la
> estructura de la base de datos.`
> `La copia previa a la migración no tiene los mismos datos que la base: <ruta de la copia>. No se ha
> cambiado la estructura de la base de datos.`

Dicen **qué ha pasado**, **dónde está la copia** y **qué no se ha hecho** — que es más de lo que
suelen decir los mensajes de este programa y sirve para no asustar. Lo que **no** dicen es qué hacer
a continuación (no dicen si el programa arranca o no, ni a quién avisar, ni que hay que mirar el disco
o el espacio libre). Y hay tres caminos en los que el guion **no** llega a ese mensaje, porque solo
recoge `RuntimeError` (`migrar_zona_de_nitratos.py:266`):

1. **La copia no se puede ni crear** (el nombre está ocupado, no hay permiso, o —esto no se ha podido
   probar— el disco está lleno): sale un `sqlite3.OperationalError` y el guion **no** lo cuenta en
   cristiano (`test_el_guion_no_avisa_en_cristiano_cuando_la_copia_no_se_puede_ni_crear`).
2. Lo mismo con **un fichero que no es una base de datos**: traza de Python y código 1 (medido con el
   guion lanzado como proceso).
3. En el **arranque del programa**, `crear_tablas()` se llama sin recoger nada (`app/main.py:75`), así
   que el fallo sale como traza de Python y el programa no arranca. (Esto se ha leído, no se ha
   ejecutado: no se levanta servidor en esta revisión.)

En los tres casos el proceso acaba con código 1 y **la base se queda intacta**, que es lo que importa;
lo que falla es el aviso.

### 3.8. Las copias no las cubre el `.gitignore`

`.gitignore:9` ignora `*.db`, y el patrón **no** cubre `cuedigital.db.antes-de-migrar-<marca>` ni
`…-byte-a-byte` ni `cuedigital.db-wal`. Medido en un repositorio de usar y tirar con el mismo
`.gitignore`:

```
cuedigital.db                                    → ignorado (.gitignore:9:*.db)
cuedigital.db.antes-de-migrar-20261002-120000    → NO IGNORADO (se subiría al repositorio)
cuedigital.db.antes-de-migrar-…-byte-a-byte      → NO IGNORADO
cuedigital.db-wal                                → NO IGNORADO
```

Como la copia se deja **al lado de la base** y es una copia entera de los datos del agricultor (con su
NIF y sus tierras), un `git add -A` en esa carpeta subiría la base entera al repositorio. Aquí no se
ha podido ver el efecto final porque **este directorio de trabajo no es un repositorio de git**
(`git check-ignore` contesta «not a git repository»), así que queda como riesgo latente, medido solo
en cuanto al patrón. **No he tocado el `.gitignore`** (es convenio del proyecto, no un fichero de la
aplicación, pero cambiarlo es una decisión de quien lo mantiene). No hay prueba automática de esto a
propósito: haría falta `git` instalado y un repositorio, y una prueba que dependa de eso es una
lotería.

---

## 4. Las preguntas concretas del encargo, en corto

| Pregunta | Respuesta medida |
|---|---|
| ¿Y si el `-wal` existe pero está vacío? | Se trata como «no hay nada pendiente» y la copia byte a byte es correcta (§2.1, con prueba) |
| ¿Y si la base está abierta por otra conexión mientras se copia? | La copia coherente **sí** lleva lo del WAL (§2.1). Si alguien escribe **después** de copiar, la comprobación lo rechaza: no se migra, pero el mensaje culpa a la copia (§2.2) |
| ¿Y si la copia queda en un disco lleno? | **No comprobado** (§5). Lo más parecido que sí se ha probado: si la copia no se puede crear, no se reconstruye nada (bien) **pero el guion escupe una traza** (§3.7) |
| ¿Se deja basura (`-wal`, `-shm`) al lado de la base? | Sí: `-shm` de 32.768 bytes y `-wal` de 0 bytes junto a la copia, y los de la base mientras está abierta (§3.4) |
| ¿El mensaje de error dice qué hacer? | Dice qué pasa, dónde está la copia y qué **no** se ha hecho. No dice qué hacer después, y tres caminos ni siquiera llegan a él (§3.7) |
| ¿Hay algún camino en el que se reconstruya una tabla sin copia válida? | Sí: base en memoria y PostgreSQL, y «fichero que no existe» (§3.6) |
| ¿Qué pasa con una base en memoria o con PostgreSQL? | En memoria: sin copia y se reconstruye igual (asumible). PostgreSQL: **no copia nada**; lo que haría la reconstrucción allí no se ha podido probar (§3.6) |

---

## 5. Lo que NO se ha podido comprobar, y por qué

1. **Un disco lleno.** No hay forma de llenar el disco de esta máquina sin poner en riesgo el trabajo
   de los demás (hay otro agente trabajando en el repositorio). Lo más cerca que se ha estado es
   hacer que la copia **no se pueda crear**, que es el mismo camino de error y que sí está medido
   (§3.7). Que un disco lleno se comporte igual es una **inferencia**, no una medida.
2. **Una carpeta en la que no se pueda escribir.** En Windows el atributo de «solo lectura» de una
   carpeta **no** impide crear ficheros dentro, y cambiar los permisos (ACL) de carpetas temporales de
   la máquina queda fuera de lo que puede hacer una prueba de este proyecto.
3. **PostgreSQL de verdad.** No hay servidor, ni ganas de montarlo para esto. Está medido que la
   puerta no copia nada (con una dirección de PostgreSQL, `_ruta_del_fichero` → `None`); lo que haría
   la reconstrucción con SQL de SQLite contra PostgreSQL **no** está comprobado.
4. **Dos procesos escribiendo a la vez *durante* la copia.** Se ha medido el caso que se puede
   provocar de forma determinista (una escritura **después** de la copia, que hace que la
   comprobación la rechace). Que la copia salga a medias en mitad de una escritura concurrente no se
   ha podido forzar desde una prueba.
5. **El arranque del programa con la copia rota.** Se ha leído que `crear_tablas()` se llama sin
   recoger el error (`app/main.py:75`) y se ha probado el error en la función; **no** se ha levantado
   el servidor para verlo con los ojos (no se arrancan servidores en esta revisión).
6. **El efecto real del `.gitignore` en este repositorio**, porque este directorio no es un
   repositorio de git (§3.8).

---

## 6. El estado de la suite mientras se hacía esta revisión

Se ha ejecutado la suite entera tres veces, y los números se movieron **por el trabajo de otro
agente** que estaba tocando `backend/app/` (los apartados A4–A7) al mismo tiempo. Ninguno de los
fallos es de esta revisión:

| Momento | Comando | Resultado leído del `--junit-xml` |
|---|---|---|
| Antes de escribir nada (12:2x) | `pytest tests -q -p no:randomly` | **2.990 pruebas, 4 fallos, 0 errores, 1 omitida** |
| A media revisión (12:4x) | el mismo | **3.017 pruebas, 13 fallos, 0 errores, 1 omitida** |
| Al terminar (12:5x) | el mismo | **no arranca**: `tests/test_lo_que_hoy_hace_por_defecto.py` no se puede importar (`ImportError: cannot import name 'modelos_de_prueba' from 'app'`), un módulo del otro agente a medio escribir |
| Al terminar (12:5x), ignorando ese módulo | `pytest tests -q -p no:randomly --ignore=tests/test_lo_que_hoy_hace_por_defecto.py` | **3.013 pruebas, 3 fallos, 0 errores, 1 omitida, 152 s**. Las 25 de este encargo, en verde |

Los tres fallos de la última vuelta son:

* `tests/test_autorizacion_del_producto.py:499` (`test_la_tabla_se_reconstruye_una_sola_vez`) —
  **ya fallaba antes de empezar** y es de la entrega que se revisa aquí: cuenta copias (§3.3).
* `tests/test_lista_de_la_junta.py:215` — **ya fallaba antes de empezar** (los números de tests de la
  documentación).
* `tests/test_que_no_falte_ningun_texto.py` — apareció **durante** la revisión, en el trabajo del otro
  agente.

No he tocado ninguno de esos ficheros: son del coordinador o de otro agente.

---

## 7. Resumen para quien tenga que decidir

* La copia **hace lo que dice**: lleva el WAL, se comprueba entera y con los mismos datos, se puede
  abrir después, es byte a byte cuando no hay nada pendiente, y no deja copias incompletas que
  parezcan buenas. Cuando la comprobación falla, no se reconstruye nada.
* Lo que **hay que arreglar** (por orden de gravedad): **(1)** la vuelta atrás con un `-wal` al lado,
  que hoy no vuelve y está contada así en el propio aviso del guion (§3.1); **(2)** el `NOT` mal
  parentizado del guion, que impide que la migración de datos cambie nada y deja el esquema migrado y
  los datos sin tocar (§3.2); **(3)** las cuatro copias por ejecución y la basura `-wal`/`-shm`, que
  nadie borra (§3.3, §3.4); **(4)** que el guion recoja también los fallos que no son `RuntimeError`,
  para que un disco lleno no acabe en una traza (§3.7); **(5)** cubrir las copias en el `.gitignore`
  (§3.8).
* **Nada de esto lo he arreglado yo**, y el fichero de pruebas de aceptación está escrito para que
  estos defectos se vean: cuando se arreglen, las pruebas que los describen fallarán y habrá que
  actualizarlas — eso es lo que tiene que pasar.
