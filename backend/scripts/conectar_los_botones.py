"""Conecta las siete acciones de las dos pantallas nuevas (14/10/2026).

**EL HALLAZGO QUE ESTO ARREGLA**: las dos pantallas pintaban sus botones y **nadie los escuchaba**. Se midió: las siete
acciones aparecían **cero veces** en `app.js`, y la casa atiende los clics con **un solo manejador delegado**
(`document.addEventListener("click", …)`, que lee `elemento.dataset.accion`). Los botones de las tareas **sí** están
conectados (`app.js:19766`), y por eso su recorrido —que pulsa— pasa; el del CRM-04 no los pulsaba, y por eso su
«16 · 0» **no** probaba esta parte.

La forma está **copiada** de los de las tareas: `if (nombre === "…") return …;`, dentro del mismo manejador delegado.
Se inserta **antes** de `if (nombre === "tarea-completar") {`, que es una línea única.
"""

import ast
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[1]

CASOS = '''  // **Las dos pantallas nuevas** (CRM-04 y Entrega 5, 14/10/2026). Sus botones se pintaban y **nadie los
  // escuchaba**: las siete acciones aparecían cero veces en este fichero y el manejador delegado no las conocía, así
  // que pulsarlas no hacía nada. Lo encontró el recorrido de la fusión, que sí pulsa; el del CRM-04 trabajaba contra
  // las puertas de la API y no lo podía ver.
  if (nombre === "fusion-ver") {
    // Lee lo que se ha elegido y **pide la vista previa al servidor**, que es quien cuenta las once tablas y quien
    // sabe qué colisiona.
    const suyo = estadoDeLaFusion();
    suyo.origen_id = (document.getElementById("fusion-origen") || {}).value || "";
    suyo.destino_id = (document.getElementById("fusion-destino") || {}).value || "";
    if (!suyo.origen_id || !suyo.destino_id) {
      // **Y se dice, en vez de no hacer nada**: un botón que no responde parece roto.
      suyo.error = t("fusion.elije_una", "");
      suyo.previa = null;
      return pantallaLaFusion();
    }
    suyo.error = "";
    suyo.resultado = null;
    suyo.cargando = true;
    pantallaLaFusion();
    try {
      suyo.previa = await apiJson(`/api/contactos/${suyo.origen_id}/fusion/${suyo.destino_id}`);
    } catch (fallo) {
      suyo.error = (fallo && fallo.message) || mensaje("no_se_pudo");
      suyo.previa = null;
    }
    suyo.cargando = false;
    return pantallaLaFusion();
  }
  if (nombre === "fusion-hacer") {
    const suyo = estadoDeLaFusion();
    const origen = elemento.dataset.origen || suyo.origen_id;
    const destino = elemento.dataset.destino || suyo.destino_id;
    const resultado = await mandarCambio(`/api/contactos/${origen}/fusion/${destino}`, "POST", {});
    if (resultado.error) {
      // **Lo que diga el servidor se enseña tal cual**: si se niega (por ejemplo porque las dos fichas tienen notas
      // escritas), el agricultor tiene que leer por qué.
      suyo.error = resultado.error;
      return pantallaLaFusion();
    }
    suyo.resultado = { destino_id: destino, aviso: t("fusion.hecho", "") };
    suyo.previa = null;
    suyo.error = "";
    return pantallaLaFusion();
  }
  if (nombre === "fusion-deshacer") {
    const suyo = estadoDeLaFusion();
    const destino = elemento.dataset.destino || suyo.destino_id;
    const resultado = await mandarCambio(`/api/contactos/${destino}/deshacer-la-fusion`, "POST", {});
    if (resultado.error) {
      suyo.error = resultado.error;
      return pantallaLaFusion();
    }
    suyo.resultado = null;
    suyo.aviso = t("fusion.deshacer", "");
    return abrirLaFusion({});
  }
  if (nombre === "trabajos-terceros-proponer") {
    // **Lo que se ha escrito en el alta**, leído campo por campo.
    const elDelCampo = (nombre_del_campo) => {
      const campo = document.getElementById(nombre_del_campo);
      return campo ? campo.value.trim() : "";
    };
    const cuerpo = {
      contacto_id: Number(elDelCampo("trabajo-cliente")) || 0,
      titulo: elDelCampo("trabajo-titulo"),
      ubicacion: elDelCampo("trabajo-ubicacion") || null,
      superficie_ha: elDelCampo("trabajo-superficie") || null,
      de_quien_es_el_insumo: elDelCampo("trabajo-insumo") || "propio",
      tarifa_por_hora: elDelCampo("trabajo-tarifa") || null,
      clave_de_reenvio: claveDeReenvio("trabajo-a-tercero"),
    };
    const resultado = await mandarCambio("/api/trabajos-a-terceros", "POST", cuerpo);
    const suyo = estadoDeLosTrabajosATerceros();
    if (resultado.error) {
      // **Lo escrito no se pierde**: se guarda lo que se llevaba, como hace el resto de la casa.
      suyo.a_medias = cuerpo;
      suyo.error = resultado.error;
      return pantallaLosTrabajosATerceros();
    }
    suyo.a_medias = null;
    suyo.error = "";
    return abrirLosTrabajosATerceros();
  }
  if (nombre === "trabajos-terceros-aceptar" || nombre === "trabajos-terceros-parte" || nombre === "trabajos-terceros-cancelar") {
    const suyo = estadoDeLosTrabajosATerceros();
    const id = Number(elemento.dataset.id);
    const cual = nombre === "trabajos-terceros-aceptar" ? "aceptar" : nombre === "trabajos-terceros-parte" ? "parte" : "cancelar";
    // El parte lleva las horas y el coste **si se han escrito**; vacío es «no consta», no un cero.
    const horas = document.getElementById("trabajo-horas");
    const coste = document.getElementById("trabajo-coste");
    const cuerpo =
      cual === "parte" ? { horas_hechas: (horas && horas.value.trim()) || null, coste_conocido: (coste && coste.value.trim()) || null } : {};
    const resultado = await mandarCambio(`/api/trabajos-a-terceros/${id}/${cual}`, "POST", cuerpo);
    if (resultado.error) {
      suyo.error = resultado.error;
      return pantallaLosTrabajosATerceros();
    }
    suyo.error = "";
    return abrirLosTrabajosATerceros();
  }
'''

p = RAIZ / "web/app.js"
lineas = p.read_bytes().decode("utf-8").split("\n")
ancla = [k for k, l in enumerate(lineas) if l.strip() == 'if (nombre === "tarea-completar") {']
if len(ancla) != 1:
    raise SystemExit(f"ABORTO: el ancla de tarea-completar aparece {len(ancla)} veces")
if any('if (nombre === "fusion-ver")' in l for l in lineas):
    print("las siete acciones ya estaban")
else:
    k = ancla[0]
    s = "\r" if lineas[k].endswith("\r") else ""
    lineas[k:k] = [(x + s) if s else x for x in CASOS.rstrip("\n").split("\n")]
    p.write_bytes("\n".join(lineas).encode("utf-8"))
    print("las siete acciones puestas, antes de la línea", k + 1)
print("comprobado:", sum(1 for l in p.read_bytes().decode("utf-8").split("\n") if 'if (nombre === "fusion-' in l or 'if (nombre === "trabajo-' in l), "casos nuevos")
