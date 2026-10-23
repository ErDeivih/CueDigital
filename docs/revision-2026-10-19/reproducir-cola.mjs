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
import { crearCola, crearAlmacenMemoria, sesionDelToken, loQueSePuedeMandar, decideQueHacer, unIdDeComando, pedirElTurno, soltarElTurno, laClaveConDueno, esDelMismoContexto, vaciarLaCola } from '../../backend/web/nucleo.js';

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
    estado, navigator:{onLine:true}, cola:crearCola(almacen), almacen, window:{localStorage:almacen},
    ALMACEN:almacen, CLAVE_ULTIMO:'cuedigital.ultimo', CLAVE_RECHAZADOS:'cuedigital.rechazados',
    // *La instalacion, que es de donde sale el dueno cuando el vale no se puede leer.*
    CLAVE_INSTALACION:'cuedigital.instalacion',
    sesionDelToken, loQueSePuedeMandar, decideQueHacer, crearAlmacenMemoria,
    // ***Y el id de comando, que `enviarOApuntar` usa desde el 21/10***: *sin el en el contexto, la funcion
    // revienta y el diagnóstico moria con «rechazar is not a function», que no decia nada de la cola.*
    unIdDeComando,
    // *Y el turno, que `mandarPendientes` pide desde el 21/10 para no vaciar dos pestañas a la vez.*
    pedirElTurno, soltarElTurno, laClaveConDueno, esDelMismoContexto, vaciarLaCola,
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
// CUE_AUDIT_CONCURRENCIA=1 node docs/revision-2026-10-19/reproducir-cola.mjs
// Almacén controlado: intercalar después de la ÚLTIMA lectura, no solo la primera.
if (process.env.CUE_AUDIT_CONCURRENCIA === '1' || process.argv.includes('--concurrencia')) {
const concurrencia={};
for (const modo of ['apuntar','quitar','turno']) {
 const base=crearAlmacenMemoria(); let lecturas=0,interferido=false,segunda;
 const clave=modo==='turno'?'cuedigital.cola.turno':'cuedigital.pendientes';
 const a={esDurable:true,getItem(k){const anterior=base.getItem(k);if(k===clave && ++lecturas===(modo==='apuntar'?2:1)&&!interferido){interferido=true; if(modo==='turno')segunda=pedirElTurno(base,{dueno:'1:1:inst',procesador:'B',ahora:1000});else crearCola(base).apuntar({id_local:'B',datos:{nota:'B'}});}return anterior;},setItem:(k,v)=>base.setItem(k,v),removeItem:k=>base.removeItem(k)};
 if(modo==='turno'){const primera=pedirElTurno(a,{dueno:'1:1:inst',procesador:'A',ahora:1000});concurrencia.turno_simultaneo={A:primera.turno,B:segunda.turno};}
 else{const cola=crearCola(a);if(modo==='apuntar')cola.apuntar({id_local:'A',datos:{nota:'A'}});else{crearCola(base).apuntar({id_local:'confirmado',datos:{}});cola.quitar('confirmado');}concurrencia[modo]={esperados:modo==='apuntar'?['A','B']:['B'],conservados:cola.leer().map(x=>x.id_local)};}
}
console.log(JSON.stringify(concurrencia,null,2));
  // Diagnóstico: exigir conservación/exclusión; 1 significa que siguen los defectos.
  const correcto = concurrencia.apuntar.conservados.length === 2 &&
    concurrencia.quitar.conservados.includes('B') &&
    !(concurrencia.turno_simultaneo.A && concurrencia.turno_simultaneo.B);
  process.exit(correcto ? 0 : 1);
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
  const a=crearCola(almacen,{reloj}),b=crearCola(almacen,{reloj});
  const uno=a.apuntar({datos:{nota:'uno'}}),dos=b.apuntar({datos:{nota:'dos'}});
  assert.notEqual(uno.id_local,dos.id_local, '***dos instancias no pueden generar el mismo id***');
  a.quitar(uno.id_local);
  assert.equal(a.tamano(),1, '***confirmar uno no puede borrar los dos***');
  resultado.identidad_dos_instancias={ids_distintos:true,quedan:1,correcto:true};
}
{
  const c=preparar();c.window.localStorage={setItem(){throw new Error('bloqueado');}};
  const cola=crearCola(c.almacenSeguro());
  const apunte=cola.apuntar({datos:{nota:'no durable'}});
  // *En memoria se «escribe» y se pierde al cerrar: **no se puede prometer guardado**. `durable` es lo que lo dice.*
  assert.equal(apunte.durable,false, '***en modo privado NO se puede decir que quedo guardado***');
  resultado.almacen_bloqueado_desde_arranque={fallback:'memoria',durable:apunte.durable,correcto:true};
}
{
  const c=preparar();
  c.cola.apuntar({ruta:'/api/trabajos',datos:{nota:'rechazado'},cuenta:'1:1',id_local:'p-rechazo'});
  // ***La clave lleva dueno desde el 21/10***: *el rechazo de esta sesion vive en `cuedigital.rechazados.1:1`, no
  // en la clave global. El interceptor mira el prefijo, y la lectura de abajo tambien.*
  const laClaveDeLosRechazos='cuedigital.rechazados.1:1';
  const set=c.almacen.setItem;c.almacen.setItem=(k,v)=>{if(k.startsWith('cuedigital.rechazados'))throw new Error('cuota');set(k,v);};
  c.api=async()=>({ok:false,status:422,json:async()=>({detail:'No aceptado'})});
  await c.mandarPendientes();
  // ***El dato NO se pierde***: *o sigue pendiente, o quedo apartado. Lo que no puede es desaparecer.*
  const pendientes=c.cola.tamano();
  const apartados=JSON.parse(c.almacen.getItem(laClaveDeLosRechazos)||'[]').length;
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
  const base=status===200?'cuedigital.ultimo':'cuedigital.rechazados';
  assert.ok(c.almacen.getItem(base+'.1:1'), 'La respuesta debe persistir bajo A');
  assert.equal(c.almacen.getItem(base+'.2:2'), null, 'La respuesta de A no debe persistir bajo B');
  if(status===200) assert.equal(c.estado.ultimo, undefined, 'No pintar el último de A en B');
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
