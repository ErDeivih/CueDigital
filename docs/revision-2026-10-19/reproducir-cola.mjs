// Regresión de D01 (convertida del diagnóstico del 21/10/2026).
//
// ANTES este fichero REPRODUCÍA los defectos y salía con 1. Ahora **verifica que están corregidos** y sale
// con 0: cada caso reproduce la misma situación y afirma el comportamiento correcto.
//
// Lo que comprueba, en el orden del encargo:
//   1. el dueño se captura ANTES de esperar, no después;
//   2. la clave de reenvío se sella ANTES del primer envío y es la misma en el reintento;
//   3. dos instancias no generan el mismo id, y confirmar uno no borra los dos;
//   4. si el almacenamiento no es durable, la cola NO dice «guardado»;
//   5. si falla el guardado del rechazo, el original NO se pierde.
//
// No es un recorrido de UI: ejecuta las funciones reales de app.js en un entorno controlado. Con
// `CUE_AUDIT_REAL` (dirección, token, campaña y parcela) además comprueba contra servidor real que una
// respuesta perdida **no duplica**.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { crearCola, crearAlmacenMemoria, sesionDelToken, loQueSePuedeMandar, decideQueHacer, unIdDeComando, pedirElTurno, soltarElTurno, laClaveConDueno, esDelMismoContexto, vaciarLaCola, crearColaPorIntenciones, duenoDelTurno, identidadDeEjecucion, identidadPersistente } from '../../backend/web/nucleo.js';

const source = fs.readFileSync(new URL('../../backend/web/app.js', import.meta.url), 'utf8').replaceAll('\r\n', '\n');
function funcion(nombre) {
  const m = source.match(new RegExp(`^(?:async )?function ${nombre}\\([^]*?^}`, 'm'));
  assert.ok(m, nombre);
  return m[0];
}
const token = (uid, eid) => `${Buffer.from(JSON.stringify({uid,eid})).toString('base64url')}.firma`;
function preparar() {
  const almacen = crearAlmacenMemoria();
  const estado = {token: token(1,1),yo:null};
  const contexto = vm.createContext({
    estado, navigator:{onLine:true},
    // ***La cola de VERDAD*** (04/11/2026): *la aplicación guarda una clave por intención desde el 23/10
    // (`app.js:447`), y este diagnóstico seguía ejercitando la cola de array. **Medir el camino que la aplicación ya
    // no usa no dice nada del producto**; se mide el que usa.*
    cola:crearColaPorIntenciones(almacen), almacen, window:{localStorage:almacen},
    ALMACEN:almacen, CLAVE_ULTIMO:'cuedigital.ultimo', CLAVE_RECHAZADOS:'cuedigital.rechazados',
    // *La instalacion, que es de donde sale el dueno cuando el vale no se puede leer.*
    CLAVE_INSTALACION:'cuedigital.instalacion',
    sesionDelToken, loQueSePuedeMandar, decideQueHacer, crearAlmacenMemoria,
    // ***Y el id de comando, que `enviarOApuntar` usa desde el 21/10***: *sin el en el contexto, la funcion
    // revienta y el diagnóstico moria con «rechazar is not a function», que no decia nada de la cola.*
    unIdDeComando,
    // *Y el turno, que `mandarPendientes` pide desde el 21/10 para no vaciar dos pestañas a la vez.*
    pedirElTurno, soltarElTurno, laClaveConDueno, esDelMismoContexto, vaciarLaCola,
    // ***Y las piezas con las que se decide QUIÉN es el dueño del turno*** (25/10/2026): *`mandarPendientes` llama a
    // `duenoDelTurno` con las dos identidades —la de ejecución, que no se copia al abrir una ventana, y la
    // persistente—; sin ellas en el contexto la extracción revienta por el andamio y no por el código.*
    duenoDelTurno, identidadDeEjecucion, identidadPersistente,
    // ***Sin IndexedDB, que es el caso de este diagnóstico***: *la transacción se prueba de verdad en Chromium con
    // `scripts/verificar_la_cola_en_indexeddb.py`; aquí se mide el camino de respaldo, que **sí existe** en la app.*
    hayIndexedDb:()=>false,
    sessionStorage:crearAlmacenMemoria(), CLAVE_PROCESADOR:"cuedigital.procesador", elProcesadorDeEstaPestana:null,
    pintarAvisoPendientes:()=>{}, cargarDatos:async()=>{}, mensaje:x=>x,
    avisoDelServidor:x=>x?.detail||'', leer:(k,d)=>JSON.parse(almacen.getItem(k)||JSON.stringify(d)),
  });
  // ***Y las dos que dan dueno a las claves locales*** (21/10/2026): *`mandarPendientes` usa `laClaveDe` para los
  // rechazados, y sin ellas en el contexto la regresion revienta por el andamio y no por el codigo.*
  for(const nombre of ['guardar','almacenSeguro','laSesionDeAhora','laInstalacion','elProcesador','laClaveDe','apuntarSinCobertura','enviarOApuntar','mandarPendientes'])
    vm.runInContext(funcion(nombre),contexto);
  return contexto;
}
/**
 * ***Los rechazos, se guarden donde se guarden*** (04/11/2026, D01-R1).
 *
 * *La forma vieja era **una lista por cuenta** (`cuedigital.rechazados.<cuenta>`); la nueva es **una clave por
 * rechazo** (`cuedigital.rechazado.<id_local>`). Leer solo una de las dos formas da «no se apartó» cuando sí se
 * apartó —el fallo del instrumento, no de la app—, así que se leen las dos.*
 */
function losRechazosDe(almacen) {
  const los = [];
  const cuantas = Number(almacen.length) || 0;
  for (let i = 0; i < cuantas; i += 1) {
    const clave = almacen.key(i);
    if (typeof clave !== 'string') continue;
    if (clave.startsWith('cuedigital.rechazados.')) {
      try { const v = JSON.parse(almacen.getItem(clave)); if (Array.isArray(v)) los.push(...v); } catch (e) {}
    } else if (clave.startsWith('cuedigital.rechazado.')) {
      try { const v = JSON.parse(almacen.getItem(clave)); if (v && typeof v === 'object') los.push(v); } catch (e) {}
    }
  }
  return los;
}
// CUE_AUDIT_CONCURRENCIA=1 node docs/revision-2026-10-19/reproducir-cola.mjs
// Almacén controlado: intercalar después de la ÚLTIMA lectura, no solo la primera.
//
// ***Lo que se mide aquí, y lo que NO*** (04/11/2026):
//
//   · el **camino real** de la aplicación es `crearColaPorIntenciones` —**una clave por intención**—: apuntar y
//     quitar **no leen**, escriben su propia clave (`app.js:447`);
//   · la **cola de array** (`crearCola`) ya **no guarda intenciones**: `app.js` la importa y **no la usa**, y lo que
//     haya del formato viejo lo trae `migrarDesde` al arrancar. Su carrera de leer-modificar-escribir se conserva
//     medida aquí como **historia**, no como veredicto: exigirle que pase sería pedirle a código muerto que apruebe.
//   · **sin IndexedDB** el turno es el de `localStorage`, y **no se promete exclusión** (está declarado: la app no
//     dice que vacíe una sola pestaña). Se mide y se informa, pero el veredicto es del camino real.
if (process.env.CUE_AUDIT_CONCURRENCIA === '1' || process.argv.includes('--concurrencia')) {
const concurrencia={};
// ---------------------------------------------------------------- historia: la cola de array
for (const modo of ['apuntar','quitar','turno']) {
 const base=crearAlmacenMemoria(); let lecturas=0,interferido=false,segunda;
 const clave=modo==='turno'?'cuedigital.cola.turno':'cuedigital.pendientes';
 const a={esDurable:true,getItem(k){const anterior=base.getItem(k);if(k===clave && ++lecturas===(modo==='apuntar'?2:1)&&!interferido){interferido=true; if(modo==='turno')segunda=pedirElTurno(base,{dueno:'1:1:inst',procesador:'B',ahora:1000});else crearCola(base).apuntar({id_local:'B',datos:{nota:'B'}});}return anterior;},setItem:(k,v)=>base.setItem(k,v),removeItem:k=>base.removeItem(k)};
 if(modo==='turno'){const primera=pedirElTurno(a,{dueno:'1:1:inst',procesador:'A',ahora:1000});concurrencia['historico_turno_simultaneo']={A:primera.turno,B:segunda.turno};}
 else{const cola=crearCola(a);if(modo==='apuntar')cola.apuntar({id_local:'A',datos:{nota:'A'}});else{crearCola(base).apuntar({id_local:'confirmado',datos:{}});cola.quitar('confirmado');}concurrencia['historico_'+modo]={esperados:modo==='apuntar'?['A','B']:['B'],conservados:cola.leer().map(x=>x.id_local)};}
}
// ---------------------------------------------------------------- el camino real: una clave por intención
/**
 * *El otro escribe **justo antes** de mi escritura.* Es la carrera de verdad: en el camino real no hay lectura que
 * intercalar —apuntar y quitar no leen—, así que lo que hay que demostrar es que **mi escritura no se lleva por
 * delante la suya**, que es lo que hacía el leer-modificar-escribir.
 */
function conElOtroEscribiendoAntes(base, queHaceElOtro) {
  let yaLoHizo = false;
  return {
    esDurable: true,
    getItem: (k) => base.getItem(k),
    setItem(k, v) { if (!yaLoHizo) { yaLoHizo = true; queHaceElOtro(); } base.setItem(k, v); },
    removeItem(k) { if (!yaLoHizo) { yaLoHizo = true; queHaceElOtro(); } base.removeItem(k); },
    get length() { return base.length; },
    key: (i) => base.key(i),
  };
}
{
  // ***apuntar y apuntar, con el otro escribiendo antes de mi escritura.***
  const base = crearAlmacenMemoria();
  const laMia = crearColaPorIntenciones(conElOtroEscribiendoAntes(base, () => crearColaPorIntenciones(base).apuntar({ id_local: 'B', datos: { nota: 'B' } })));
  laMia.apuntar({ id_local: 'A', datos: { nota: 'A' } });
  concurrencia.apuntar_del_camino_real = {
    esperados: ['A', 'B'],
    conservados: laMia.leer().map((x) => x.id_local).sort(),
  };
}
{
  // ***apuntar y quitar: quitar lo mío no puede llevarse lo que el otro acaba de añadir.***
  const base = crearAlmacenMemoria();
  crearColaPorIntenciones(base).apuntar({ id_local: 'confirmado', datos: {} });
  const laMia = crearColaPorIntenciones(conElOtroEscribiendoAntes(base, () => crearColaPorIntenciones(base).apuntar({ id_local: 'B', datos: { nota: 'B' } })));
  laMia.quitar('confirmado');
  concurrencia.quitar_del_camino_real = {
    esperados: ['B'],
    conservados: laMia.leer().map((x) => x.id_local),
  };
}
console.log(JSON.stringify(concurrencia,null,2));
  // ***El veredicto es del camino real***: conservación de las dos intenciones y de lo que el otro añade.
  const elVeredicto =
    concurrencia.apuntar_del_camino_real.conservados.length === 2 &&
    concurrencia.quitar_del_camino_real.conservados.includes('B');
  // *Y se dice lo que queda abierto, para que nadie lo lea como verde general.*
  const elViejoSiguePerdiendo =
    concurrencia.historico_apuntar.conservados.length !== 2 ||
    !concurrencia.historico_quitar.conservados.includes('B');
  console.error(
    `camino real: ${elVeredicto ? 'conserva las dos intenciones' : 'PIERDE INTENCIONES'}` +
    ` · cola de array (ya no enchufada): ${elViejoSiguePerdiendo ? 'sigue perdiendo' : 'no reproduce'}` +
    ` · turno sin IndexedDB: ${concurrencia.historico_turno_simultaneo.A && concurrencia.historico_turno_simultaneo.B ? 'sin exclusión (declarado)' : 'exclusivo'}`,
  );
  process.exit(elVeredicto ? 0 : 1);
}
const resultado={};
{
  const c=preparar(); let rechazar;
  c.api=()=>new Promise((_,reject)=>{rechazar=reject;});
  const envio=c.enviarOApuntar('/api/parcelas',{alias:'De A'},'parcela');
  // *Cambia la cuenta **mientras la peticion esta en vuelo** y despues se pierde la respuesta.*
  c.estado.token=token(2,2); rechazar(new Error('respuesta perdida'));
  await envio;
  const pendiente=c.cola.leer()[0];
  assert.equal(pendiente.cuenta,'1:1', '***el dueno tiene que ser QUIEN LO EMPEZO, no quien este ahora***');
  resultado.cambio_durante_primer_envio={creador:'1:1',dueno_asignado:pendiente.cuenta,correcto:true};
}
{
  const c=preparar(); let primera=true; const enviados=[];
  c.api=async(_ruta,opciones)=>{
    enviados.push(JSON.parse(opciones.body));
    if(primera){primera=false;throw new Error('servidor guardo; respuesta perdida');}
    return {ok:true,status:201,json:async()=>({id:2})};
  };
  await c.enviarOApuntar('/api/trabajos',{tipo:'laboreo'},'labor');
  await c.mandarPendientes();
  assert.equal(enviados.length,2);
  // ***La clave va YA en el primer envio***: *si no, el reintento lleva una nueva y el servidor crea dos.*
  assert.ok(enviados[0].clave_de_reenvio, '***el primer envio tiene que llevar su clave***');
  assert.equal(
    enviados[1].clave_de_reenvio,
    enviados[0].clave_de_reenvio,
    '***y el reintento la MISMA: es la misma intencion***',
  );
  resultado.identidad_primer_envio={primero_tiene_clave:true,misma_clave_en_reintento:true,correcto:true};
}
{
  const almacen=crearAlmacenMemoria();const reloj=()=> '2026-10-21T00:00:00.000Z';
  // ***La cola de la aplicación, no la de array*** (04/11/2026): *es donde de verdad se apunta desde el 23/10.*
  const a=crearColaPorIntenciones(almacen,{reloj}),b=crearColaPorIntenciones(almacen,{reloj});
  const uno=a.apuntar({datos:{nota:'uno'}}),dos=b.apuntar({datos:{nota:'dos'}});
  assert.notEqual(uno.id_local,dos.id_local, '***dos instancias no pueden generar el mismo id***');
  a.quitar(uno.id_local);
  assert.equal(a.tamano(),1, '***confirmar uno no puede borrar los dos***');
  resultado.identidad_dos_instancias={ids_distintos:true,quedan:1,correcto:true};
}
{
  const c=preparar();c.window.localStorage={setItem(){throw new Error('bloqueado');}};
  const cola=crearColaPorIntenciones(c.almacenSeguro());
  const apunte=cola.apuntar({datos:{nota:'no durable'}});
  // *En memoria se «escribe» y se pierde al cerrar: **no se puede prometer guardado**. `durable` es lo que lo dice.*
  assert.equal(apunte.durable,false, '***en modo privado NO se puede decir que quedo guardado***');
  resultado.almacen_bloqueado_desde_arranque={fallback:'memoria',durable:apunte.durable,correcto:true};
}
{
  const c=preparar();
  c.cola.apuntar({ruta:'/api/trabajos',datos:{nota:'rechazado'},cuenta:'1:1',id_local:'p-rechazo'});
  // ***El rechazo se guarda en UNA CLAVE SUYA desde el 04/11/2026*** (D01-R1): *la lista compartida ya no se escribe.
  // El interceptor falla en las **dos** formas —la vieja y la nueva— para que este caso siga midiendo lo que dice
  // medir: **si no se puede apartar, el apunte no puede desaparecer**. Si solo fallara la vieja, el rechazo se
  // guardaría en el buzón y la prueba pasaría sin haber probado nada.*
  const set=c.almacen.setItem;
  c.almacen.setItem=(k,v)=>{if(String(k).startsWith('cuedigital.rechazado'))throw new Error('cuota');set(k,v);};
  c.api=async()=>({ok:false,status:422,json:async()=>({detail:'No aceptado'})});
  await c.mandarPendientes();
  // ***El dato NO se pierde***: *o sigue pendiente, o quedo apartado. Lo que no puede es desaparecer.*
  const pendientes=c.cola.tamano();
  const apartados=losRechazosDe(c.almacen).length;
  assert.ok(
    pendientes + apartados >= 1,
    '***si no se puede apartar, el apunte se queda; no se borra***',
  );
  resultado.fallo_al_apartar={pendientes,rechazados:apartados,dato_perdido:false,correcto:true};
}
for (const status of [200, 422]) {
  const c=preparar(); let resolver;
  c.api=()=>new Promise(resolve=>{resolver=resolve;});
  let envio;
  if(status===200) envio=c.enviarOApuntar('/api/trabajos',{nota:'De A'},'labor');
  else {
    c.cola.apuntar({id_local:'rechazo-A',ruta:'/api/trabajos',datos:{nota:'De A'},cuenta:'1:1'});
    envio=c.mandarPendientes();
  }
  c.estado.token=token(2,2);
  resolver({ok:status===200,status,json:async()=>({detail:'No aceptado'})});
  await envio;
  if(status===200){
    assert.ok(c.almacen.getItem('cuedigital.ultimo.1:1'), 'La respuesta debe persistir bajo A');
    assert.equal(c.almacen.getItem('cuedigital.ultimo.2:2'), null, 'La respuesta de A no debe persistir bajo B');
    assert.equal(c.estado.ultimo, undefined, 'No pintar el último de A en B');
  } else {
    // ***El 422 vive en una clave por rechazo*** (04/11/2026, D01-R1), *con su dueño dentro. Se comprueba lo mismo de
    // siempre: la respuesta de A se guarda **bajo A**, y no bajo B.*
    const los=losRechazosDe(c.almacen);
    const elDeA=los.filter((uno)=>uno && uno.id_local==='rechazo-A');
    assert.equal(elDeA.length,1, 'La respuesta de A debe persistir bajo A');
    assert.equal(elDeA[0].cuenta,'1:1', '***y con el dueño de A, no con el de la sesión de ahora***');
    assert.equal(
      los.filter((uno)=>uno && uno.cuenta==='2:2').length,
      0,
      'La respuesta de A no debe persistir bajo B',
    );
  }
  resultado['respuesta_tardia_'+status]={persistencia:'origen A',cuenta_B_intacta:true,correcto:true};
}
if(process.env.CUE_AUDIT_REAL){
  const config=JSON.parse(process.env.CUE_AUDIT_REAL);
  const c=preparar();c.estado.token=config.token;
  let primera=true;
  c.api=async(ruta,opciones)=>{
    const r=await fetch(config.direccion+ruta,{...opciones,headers:{'Content-Type':'application/json',Authorization:`Bearer ${config.token}`}});
    if(!r.ok)throw new Error(`La comprobacion necesita alta valida: ${r.status} ${await r.text()}`);
    if(primera){primera=false;await r.json();throw new Error('Respuesta perdida DESPUES del commit real');}
    return r;
  };
  const datos={campana_id:config.campana_id,parcela_id:config.parcela_id,tipo:'laboreo',subtipo:'AUDITORIA_RESPUESTA_PERDIDA',fecha:'2026-10-21'};
  await c.enviarOApuntar('/api/trabajos',datos,'labor');
  await c.mandarPendientes();
  const r=await fetch(config.direccion+'/api/trabajos',{headers:{Authorization:`Bearer ${config.token}`}});
  const body=await r.json(); const filas=Array.isArray(body)?body:body.hechos||body.trabajos||[];
  const mias=filas.filter(x=>x.subtipo===datos.subtipo);
  assert.equal(mias.length,1, '***una intencion, UNA fila: la respuesta perdida no puede duplicar***');
  resultado.servidor_real_respuesta_perdida={filas_creadas:mias.length,ids:mias.map(x=>x.id),correcto:true};
}
console.log(JSON.stringify(resultado,null,2));
console.error('D01: cinco casos anteriores y dos respuestas tardías pasan; concurrencia se diagnostica por separado.');
