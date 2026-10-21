// Diagnóstico del 21/10/2026: ejecuta funciones reales de app.js en un entorno controlado.
// La salida 1 significa que se han reproducido los defectos descritos en el informe.
// No es una suite de aceptación: convertir cada caso en una regresión al corregir D01.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { crearCola, crearAlmacenMemoria, sesionDelToken, loQueSePuedeMandar, decideQueHacer } from '../../backend/web/nucleo.js';

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
    sesionDelToken, loQueSePuedeMandar, decideQueHacer, crearAlmacenMemoria,
    pintarAvisoPendientes:()=>{}, cargarDatos:async()=>{}, mensaje:x=>x,
    avisoDelServidor:x=>x?.detail||'', leer:(k,d)=>JSON.parse(almacen.getItem(k)||JSON.stringify(d)),
  });
  for(const nombre of ['guardar','almacenSeguro','laSesionDeAhora','apuntarSinCobertura','enviarOApuntar','mandarPendientes'])
    vm.runInContext(funcion(nombre),contexto);
  return contexto;
}
const resultado={};
{
  const c=preparar(); let rechazar;
  c.api=()=>new Promise((_,reject)=>{rechazar=reject;});
  const envio=c.enviarOApuntar('/api/parcelas',{alias:'De A'},'parcela');
  c.estado.token=token(2,2); rechazar(new Error('respuesta perdida'));
  await envio;
  const pendiente=c.cola.leer()[0];
  assert.equal(pendiente.cuenta,'2:2');
  resultado.cambio_durante_primer_envio={creador:'1:1',dueno_asignado:pendiente.cuenta};
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
  assert.equal(enviados[0].clave_de_reenvio,undefined);
  assert.ok(enviados[1].clave_de_reenvio);
  resultado.identidad_primer_envio={primero_tiene_clave:false,reintento_tiene_clave:true};
}
{
  const almacen=crearAlmacenMemoria();const reloj=()=> '2026-10-21T00:00:00.000Z';
  const a=crearCola(almacen,{reloj}),b=crearCola(almacen,{reloj});
  const uno=a.apuntar({datos:{nota:'uno'}}),dos=b.apuntar({datos:{nota:'dos'}});
  assert.equal(uno.id_local,dos.id_local);
  a.quitar(uno.id_local);
  assert.equal(a.tamano(),0);
  resultado.identidad_dos_instancias={ids_iguales:true,apuntes_eliminados_al_confirmar_uno:2};
}
{
  const c=preparar();c.window.localStorage={setItem(){throw new Error('bloqueado');}};
  const cola=crearCola(c.almacenSeguro());
  const apunte=cola.apuntar({datos:{nota:'no durable'}});
  assert.equal(apunte.guardado,true);
  resultado.almacen_bloqueado_desde_arranque={fallback:'memoria',dice_guardado:apunte.guardado};
}
{
  const c=preparar();
  c.cola.apuntar({ruta:'/api/trabajos',datos:{nota:'rechazado'},cuenta:'1:1'});
  const set=c.almacen.setItem;c.almacen.setItem=(k,v)=>{if(k==='cuedigital.rechazados')throw new Error('cuota');set(k,v);};
  c.api=async()=>({ok:false,status:422,json:async()=>({detail:'No aceptado'})});
  await c.mandarPendientes();
  assert.equal(c.cola.tamano(),0);
  assert.equal(c.almacen.getItem('cuedigital.rechazados'),null);
  resultado.fallo_al_apartar={pendientes:0,rechazados:0,dato_perdido:true};
}
if(process.env.CUE_AUDIT_REAL){
  const config=JSON.parse(process.env.CUE_AUDIT_REAL);
  const c=preparar();c.estado.token=config.token;
  let primera=true;
  c.api=async(ruta,opciones)=>{
    const r=await fetch(config.direccion+ruta,{...opciones,headers:{'Content-Type':'application/json',Authorization:`Bearer ${config.token}`}});
    if(!r.ok)throw new Error(`La reproduccion necesita alta valida: ${r.status} ${await r.text()}`);
    if(primera){primera=false;await r.json();throw new Error('Respuesta perdida DESPUES del commit real');}
    return r;
  };
  const datos={campana_id:config.campana_id,parcela_id:config.parcela_id,tipo:'laboreo',subtipo:'AUDITORIA_RESPUESTA_PERDIDA',fecha:'2026-10-21'};
  await c.enviarOApuntar('/api/trabajos',datos,'labor');
  await c.mandarPendientes();
  const r=await fetch(config.direccion+'/api/trabajos',{headers:{Authorization:`Bearer ${config.token}`}});
  const body=await r.json(); const filas=Array.isArray(body)?body:body.hechos||body.trabajos||[];
  const mias=filas.filter(x=>x.subtipo===datos.subtipo);
  assert.equal(mias.length,2);
  resultado.servidor_real_respuesta_perdida={filas_creadas:mias.length,ids:mias.map(x=>x.id)};
}
console.log(JSON.stringify(resultado,null,2));

console.error('D01: defectos reproducidos; consultar REVISION_PRODUCTO_2026-10-19.md.');
process.exitCode = 1;
