"""TODO el texto que ve el agricultor, en un solo sitio.

Decisión de arquitectura: los mensajes y las ayudas NO están repartidos por los
servicios. Están aquí, juntos. Hay dos motivos:

1. Se pueden revisar de una tirada. La regla "cero jerga" solo se mantiene si el
   texto está en un fichero que se lee entero.
2. El test `test_sin_jerga` recorre este módulo y falla si aparece una palabra
   prohibida. Sin esta separación, ese test no se puede escribir.

Las palabras prohibidas no son un capricho: son las que un agricultor no diría en
voz alta. Si aparecen en pantalla, el agricultor deja de entender lo que le
pedimos, y entonces el cuaderno se queda a medias.
"""

from __future__ import annotations

# --------------------------------------------------------------------------
# Los "porqués": lo que la app explica cuando alguien pregunta para qué sirve esto
# --------------------------------------------------------------------------

PORQUE = {
    "para_que_sirve": (
        "Desde 2013, si echas productos para las plagas en tu finca, la ley te obliga "
        "a apuntarlo. Es el cuaderno donde queda escrito todo lo que haces en el campo. "
        "Sirve para tres cosas:\n"
        "1. Cumplir la ley. Si viene una inspección, es lo que te van a pedir.\n"
        "2. Saber qué hiciste. Si un cliente pregunta por una partida, lo tienes apuntado.\n"
        "3. Poder vender. Sin cuaderno no puedes demostrar qué echaste ni cuándo."
    ),
    "papel_o_digital": (
        "Puedes llevarlo en papel hasta el 31 de diciembre de 2026. A partir del "
        "1 de enero de 2027 tiene que ser electrónico. Si lo llevas aquí, no se te "
        "pierde, te calcula solo los días de espera y te avisa de lo que falta."
    ),
    "que_pasa_si_no_lo_llevo": (
        "Es una obligación. En una inspección te pueden sancionar y, además, te "
        "costará justificar lo que has hecho para las ayudas o para vender a la "
        "cooperativa."
    ),
    "por_que_tantos_datos": (
        "Casi todo lo que te pedimos viene ya en la etiqueta del producto o lo sabe "
        "el programa. Lo único que tienes que poner tú es dónde, cuándo y qué has hecho. "
        "Si algo no lo sabes, déjalo en blanco: se puede completar después."
    ),
    "por_que_dias_de_espera": (
        "Los días de espera son el tiempo que tiene que pasar desde que echas un "
        "producto hasta que puedes coger la cosecha. Están para que lo que vendes no "
        "lleve restos. El programa calcula solo el día a partir del cual puedes cogerla."
    ),
    "por_que_zona_nitratos": (
        "En algunos pueblos hay reglas más estrictas para abonar, porque el agua de "
        "la zona tiene demasiado nitrato. Si tu parcela está en una de esas zonas, "
        "el programa te lo dice y te avisa, con las reglas concretas que hay cargadas."
    ),
    "por_que_analisis": (
        "Un análisis de la tierra dice lo que ya tiene tu finca. Con eso se abona lo "
        "justo: ni de más, que se tira el dinero y contamina, ni de menos, que se pierde "
        "cosecha. El papel del laboratorio se pierde en un cajón; aquí lo tienes para "
        "siempre y el plan de abono lo aprovecha."
    ),
    "por_que_medidas": (
        "Antes de echar producto, la ley pide que hayas probado otras cosas: cambiar de "
        "cultivo, mirar el campo antes de decidir, limpiar la máquina… Se llaman medidas "
        "preventivas. Las marcas una vez y quedan apuntadas para todo el año. Sirve para "
        "dos cosas: en una inspección demuestras que no echas producto por echar, y de "
        "paso te ahorras tratamientos que no hacían falta."
    ),
    "por_que_vender": (
        "Apuntar lo que vendes es lo que cierra el cuaderno: con eso se puede responder a "
        "«¿de dónde salió esta partida?» cuando lo pregunta un cliente o una inspección. "
        "Si algún día hay un problema con un lote, el que tiene el papel es el que se libra."
    ),
    # Este porqué se añadió en la ronda 35 al comprobar el plazo de conservación, que estaba en la
    # lista de lo que faltaba por confirmar. La respuesta está en el propio reglamento (ver
    # `docs/LO_QUE_OBLIGA_LA_LEY.md`), así que se dice con su número de artículo en vez de dejarlo en
    # «consulta a un asesor»: es lo que necesita saber quien se pregunta si puede tirar los papeles.
    "cuanto_tiempo_guardar": (
        "Desde que apuntas algo hasta que puedes tirarlo pasan 3 años: la ley dice que los "
        "registros y los papeles que los justifican (las facturas, los certificados de la máquina, "
        "el asesoramiento) se conservan «al menos durante los 3 años siguientes a su fecha de "
        "emisión». Es el artículo 16.3 del Real Decreto 1311/2012, y está escrito entero en el "
        "documento de lo que obliga la ley. Aquí no se borra nada solo: si algo se anula, se queda "
        "con su motivo."
    ),
}

# El título corto de cada porqué, para la pantalla de ayuda (rediseño de la ronda 83).
#
# **Por qué hacía falta.** Los porqués son párrafos largos y en la pantalla salían **seguidos y sin
# nombre**, así que no se sabía dónde acababa uno y empezaba el siguiente: se leían como un muro. Con su
# título delante, cada uno es una cosa con su nombre y se puede ir a la que interesa.
#
# Va en un diccionario aparte —y no dentro del texto— porque el mismo porqué se enseña en otras pantallas
# (el de vender, en «lo que he vendido»; el de las medidas, en las medidas) donde el título no pinta nada.
PORQUE_TITULOS: dict[str, str] = {
    "para_que_sirve": "Para qué sirve el cuaderno",
    "papel_o_digital": "En papel o en el móvil",
    "que_pasa_si_no_lo_llevo": "Qué pasa si no lo llevo",
    "por_que_tantos_datos": "Por qué te pido tantos datos",
    "por_que_dias_de_espera": "Por qué hay días de espera",
    "por_que_zona_nitratos": "Por qué te aviso de los nitratos",
    "por_que_analisis": "Para qué sirve un análisis",
    "por_que_medidas": "Por qué te pido las medidas preventivas",
    "por_que_vender": "Para qué sirve apuntar lo que vendo",
    "cuanto_tiempo_guardar": "Cuánto tiempo hay que guardar los papeles",
}

# --------------------------------------------------------------------------
# Ayuda de cada campo: qué es, por qué se pide, ejemplo y qué pasa si falta
# --------------------------------------------------------------------------

# Los cuatro rótulos con los que se presenta la ayuda de un campo. **Estaban escritos dentro del
# JavaScript** (`ayudaDeCampo()` en `app.js`), que es justo donde no pueden estar: no pasaban por la
# prueba que vigila que no hay jerga y nadie podía revisarlos ni cambiarlos desde aquí. Se vieron al
# pasar a React la pantalla de entrar, que es una de las que los enseñan.
ROTULOS_DE_LA_AYUDA_DE_UN_CAMPO: dict[str, str] = {
    "que_es": "Qué es:",
    "por_que": "Por qué te lo piden:",
    "ejemplo": "Ejemplo:",
    "si_falta": "Si te falta:",
}

AYUDA: dict[str, dict[str, str]] = {
    "explotacion.nif": {
        "titulo": "Tu NIF",
        "que_es": "El número que te identifica en tus papeles.",
        "por_que": "Con él se sabe de qué finca son los apuntes.",
        "ejemplo": "70922320A",
        "si_falta": "Sin NIF no se puede identificar la finca en el cuaderno.",
    },
    "explotacion.codigo_siex": {
        "titulo": "El número de tu finca",
        "que_es": "El número que le dio la Junta a tu finca, como una matrícula.",
        "por_que": "Es el número que usa la administración para reconocer tu finca.",
        "ejemplo": "ES13...",
        "si_falta": "Si no lo sabes, déjalo en blanco: se puede poner después.",
    },
    "parcela.ref_sigpac": {
        "titulo": "El número del trozo de tierra",
        "que_es": "El número oficial de ese trozo: provincia, polígono, parcela y recinto.",
        "por_que": "SIGPAC es el catastro del campo. Con ese número traemos la superficie sola.",
        "ejemplo": "37-455-12-3",
        "si_falta": "Sin él tendrás que medir la superficie tú o dibujar el trozo en el mapa.",
    },
    "parcela.superficie_ha": {
        "titulo": "Cuántas hectáreas tiene",
        "que_es": "La superficie del trozo.",
        "por_que": "De aquí salen las cantidades de producto y de abono.",
        "ejemplo": "2,4317",
        "si_falta": "No se pueden calcular las dosis ni las cantidades totales.",
    },
    "parcela.alias": {
        "titulo": "Cómo llamas tú a esa tierra",
        "que_es": "El nombre de la finca, el que usas tú.",
        "por_que": "Para reconocerla de un vistazo cuando tengas muchas.",
        "ejemplo": "El Prado",
        "si_falta": "Tendrás que buscar la parcela por su número, que es más incómodo.",
    },
    "parcela.zona_vulnerable_nitratos": {
        "titulo": "Zona de nitratos",
        "que_es": "Si esa tierra está en un pueblo con reglas especiales para abonar.",
        "por_que": "En esas zonas el abono se mira más, porque el agua tiene demasiado nitrato.",
        "ejemplo": "Sí",
        "si_falta": "El programa no sabrá si tiene que avisarte de las reglas de abono.",
    },
    "parcela.masa_agua_cerca": {
        "titulo": "Si hay agua cerca",
        "que_es": "Si en esa tierra o al lado hay río, arroyo o balsa.",
        "por_que": "Junto al agua hay que dejar una orilla sin tratar, para no contaminarla.",
        "ejemplo": "Sí",
        "si_falta": "No se te avisará de la orilla que hay que dejar sin tratar.",
    },
    "producto.numero_registro": {
        "titulo": "El número de la etiqueta",
        "que_es": "El número que viene en el envase del producto, junto al nombre.",
        "por_que": "Es lo que dice que el producto está autorizado y qué lleva dentro.",
        "ejemplo": "24.123",
        "si_falta": "No se puede saber qué lleva ni cuántos días hay que esperar.",
    },
    "producto.materia_activa": {
        "titulo": "Lo que lleva dentro",
        "que_es": "La sustancia que de verdad hace el efecto.",
        "por_que": "Dos marcas distintas pueden llevar lo mismo; esto lo aclara.",
        "ejemplo": "Tebuconazol",
        "si_falta": "Se rellena solo con el número de la etiqueta, así que normalmente no falta.",
    },
    "producto.dosis_maxima": {
        "titulo": "Cuánto se puede echar como mucho",
        "que_es": "La cantidad máxima por hectárea que permite la etiqueta.",
        "por_que": "Echar más de lo permitido no es legal y no sirve de nada.",
        "ejemplo": "0,8 L/ha",
        "si_falta": "El programa no podrá avisarte si te pasas de la dosis.",
    },
    "producto.plazo_seguridad_dias": {
        "titulo": "Días de espera",
        "que_es": "Los días que tienen que pasar desde que echas el producto hasta que puedes coger la cosecha.",
        "por_que": "Para que lo que vendes no lleve restos del producto.",
        "ejemplo": "21",
        "si_falta": "No se puede calcular a partir de qué día puedes cosechar.",
    },
    "tratamiento.fecha": {
        "titulo": "El día que lo echaste",
        "que_es": "El día real de la aplicación, no el día que lo apuntas.",
        "por_que": "De aquí salen los días de espera para poder coger la cosecha.",
        "ejemplo": "12/05/2026",
        "si_falta": "No se puede saber cuándo podrás cosechar esa parcela.",
    },
    "tratamiento.parcela_id": {
        "titulo": "Dónde lo echaste",
        "que_es": "La parcela o el grupo de parcelas donde has trabajado.",
        "por_que": "El cuaderno se apunta por trozo de tierra.",
        "ejemplo": "El Prado",
        "si_falta": "Sin saber dónde, el apunte no sirve para nada.",
    },
    "tratamiento.superficie_tratada_ha": {
        "titulo": "Cuántas hectáreas has tratado",
        "que_es": "La superficie que de verdad has tratado.",
        "por_que": "Se usa para calcular cuánto producto has gastado en total.",
        "ejemplo": "2,43",
        "si_falta": "No se puede calcular la cantidad total de producto.",
    },
    "tratamiento.justificacion": {
        "titulo": "Por qué lo has echado",
        "que_es": "El motivo por el que decidiste tratar.",
        "por_que": "La ley pide el motivo: demuestra que hacía falta y que no echas por echar.",
        "ejemplo": "Vi pulgón en las hojas",
        "si_falta": "El apunte queda incompleto y en una inspección no se justifica.",
    },
    "tratamiento.dosis": {
        "titulo": "Cuánto producto por hectárea",
        "que_es": "La cantidad de producto que has puesto en cada hectárea.",
        "por_que": "Tiene que ser la de la etiqueta. Ni más ni menos.",
        "ejemplo": "0,8 L/ha",
        "si_falta": "No se puede comprobar si has respetado lo que permite la etiqueta.",
    },
    "fertilizacion.kg_ha_producto": {
        "titulo": "Cuántos kilos por hectárea",
        "que_es": "Los kilos de abono que has echado en cada hectárea.",
        "por_que": "Con esto y los tres números del saco se calcula el abono puro que has aportado.",
        "ejemplo": "300",
        "si_falta": "No se puede calcular el abono puro, que es lo que mira la administración.",
    },
    "fertilizacion.riqueza": {
        "titulo": "Los tres números del saco",
        "que_es": "El nitrógeno, el fósforo y el potasio que lleva el abono, en tanto por ciento.",
        "por_que": "Un saco al 33,5 % y otro al 20 % no aportan lo mismo aunque pesen igual.",
        "ejemplo": "33,5 - 0 - 0",
        "si_falta": "No se puede saber cuánto abono de verdad has aportado.",
    },
    "labor.tipo": {
        "titulo": "Qué has hecho",
        "que_es": "El trabajo que has hecho en el campo.",
        "por_que": "Completa la historia de la parcela, que es lo que se mira en una inspección.",
        "ejemplo": "Sembrar",
        "si_falta": "Queda un hueco en la historia de esa tierra.",
    },
    "labor.superficie_ha": {
        "titulo": "Cuántas hectáreas",
        "que_es": "La superficie en la que has hecho el trabajo.",
        "por_que": "Sirve para cuadrar los kilos de semilla, el agua o la cosecha.",
        "ejemplo": "2,43",
        "si_falta": "No se pueden cuadrar las cantidades.",
    },
    "analitica.tipo": {
        "titulo": "Qué has mandado analizar",
        "que_es": "Si el análisis es de la tierra, del agua, de la planta, de lo que has recogido o de si lleva restos.",
        "por_que": "Cada cosa se mira de una manera distinta, y el boletín trae números distintos.",
        "ejemplo": "La tierra",
        "si_falta": "Sin saber qué se ha analizado, los números del boletín no dicen nada.",
    },
    "analitica.fecha_toma_muestra": {
        "titulo": "El día que cogiste la muestra",
        "que_es": "El día que se cogió la tierra, el agua o la planta. No el día que fuiste al laboratorio.",
        "por_que": "Es la fecha del dato. Un análisis de hace tres años no vale para decidir el abono de este año.",
        "ejemplo": "14/02/2026",
        "si_falta": "No se puede saber si el análisis es de este año o de hace diez.",
    },
    "analitica.fecha_resultado": {
        "titulo": "El día que te dieron el resultado",
        "que_es": "El día que salió el boletín del laboratorio.",
        "por_que": "Sirve para saber si el papel es reciente o lleva meses en un cajón.",
        "ejemplo": "28/02/2026",
        "si_falta": "Si no lo sabes, déjalo en blanco.",
    },
    "analitica.parcela_id": {
        "titulo": "De dónde salió",
        "que_es": "La parcela de la que se cogió la muestra.",
        "por_que": "Un análisis de tierra solo vale para la parcela de la que salió.",
        "ejemplo": "El Prado",
        "si_falta": "El análisis queda guardado, pero no se puede usar para el plan de abono de ninguna parcela.",
    },
    "analitica.laboratorio": {
        "titulo": "Quién ha hecho el análisis",
        "que_es": "El nombre del laboratorio que firma el boletín.",
        "por_que": "Es lo que dice que el análisis lo ha hecho alguien que sabe, y no un papel cualquiera.",
        "ejemplo": "Laboratorio Agrario de Villamuriel",
        "si_falta": "El análisis vale menos: no se sabe quién lo ha hecho.",
    },
    "analitica.numero_informe": {
        "titulo": "El número del boletín",
        "que_es": "El número que viene en el papel del laboratorio.",
        "por_que": "Con ese número, el laboratorio encuentra tu análisis si hay que preguntarle algo.",
        "ejemplo": "2026/0417",
        "si_falta": "Si no lo encuentras, déjalo en blanco.",
    },
    "analitica.parametros": {
        "titulo": "Los números del boletín",
        "que_es": "Los valores que te ha dado el laboratorio.",
        "por_que": "Es lo que de verdad se aprovecha: el plan de abono los lee solos.",
        "ejemplo": "Fósforo: 18",
        "si_falta": "Un análisis sin números es solo un papel, pero puedes subir el boletín y rellenarlo después.",
    },
    "analitica.fichero": {
        "titulo": "El papel del laboratorio",
        "que_es": "El boletín en PDF o una foto hecha con el móvil.",
        "por_que": "Así no hay que copiar los números a mano y queda el original guardado.",
        "ejemplo": "boletin.pdf",
        "si_falta": "Se puede seguir apuntando a mano lo que diga el papel.",
    },
    "asesor.numero_ropo": {
        "titulo": "El número de asesor",
        "que_es": "El número con el que tu técnico está inscrito como asesor (el ROPO).",
        "por_que": "La Junta comprueba ese número en su registro. Si no está, no acepta el tratamiento.",
        "ejemplo": "ROPO-ASESOR-778",
        "si_falta": "Pídeselo a tu técnico: sin ese número el tratamiento no se puede entregar a la Junta.",
    },
}


# --------------------------------------------------------------------------
# Mensajes. Todos siguen la misma estructura: qué pasa + qué hago ahora.
# --------------------------------------------------------------------------

MENSAJES: dict[str, str] = {
    # --- tratamientos ---
    "V1_sin_registro": (
        "Ese número de etiqueta no nos suena. Míralo otra vez en el envase del producto."
    ),
    "V1_no_autorizado": (
        "Ese producto ya no se puede usar. Mira la etiqueta o pregunta en la tienda "
        "dónde lo compraste."
    ),
    # El tercer estado: no sabemos si el producto sigue autorizado. Avisa y no bloquea, porque el
    # cuaderno tiene que poder recoger lo que de verdad se hizo, pero **no se calla**: callar aquí
    # es lo que hacía que un producto retirado pasara por bueno.
    "V1_autorizacion_sin_comprobar": (
        "De este producto no sabemos si sigue autorizado, porque en su ficha no lo has dicho. "
        "Mira el envase o pregúntalo en la tienda y márcalo en la ficha del producto. "
        "El apunte se puede guardar."
    ),
    "V1_autorizacion_caducada": (
        "El permiso especial para usar ese producto terminó el {fecha}. Ahora mismo no "
        "se puede echar."
    ),
    "V2_no_esta_en_la_cesta": (
        "Este producto no lo tienes apuntado como comprado. ¿Lo añadimos a la lista?"
    ),
    "V3_dosis_excedida": (
        "Has puesto más de lo que permite la etiqueta. Como mucho son {maximo} {unidad}. "
        "Bájalo y ya está."
    ),
    "V4_superficie_excedida": (
        "La parcela tiene {parcela} hectáreas y has puesto {usada}. Corrige la superficie."
    ),
    "V5_fecha_fuera_de_cultivo": (
        "En esa fecha no había cultivo en esta parcela. ¿Seguro que fue ese día?"
    ),
    "V6_carne_caducado": (
        "El carné de {nombre} caducó el {fecha}. Renueva el carné o cambia quién aplica."
    ),
    "V6_sin_carne": (
        "A {nombre} le falta el número de carné para echar producto. Ponlo antes de seguir."
    ),
    "V7_iteaf_caducada": (
        "La ITV de {equipo} está caducada. No se puede echar producto con esa máquina: "
        "pásala antes o usa otra."
    ),
    "V7_sin_iteaf": (
        "A {equipo} le falta la fecha de la ITV. Ponla antes de seguir."
    ),
    "V8_dias_de_espera": (
        "Fíjate: con lo que has echado hoy, en esta parcela no podrás coger la cosecha "
        "hasta el {fin}."
    ),
    # Cuántos días faltan para poder coger la cosecha. **Estaba escrito dentro del JavaScript**
    # (en el resumen del asistente, «Faltan N días.»), que es justo donde no puede estar: no pasaba
    # por la prueba que vigila que no hay jerga.
    "V8_cuantos_dias_faltan": "Faltan {dias} días.",
    "V9_no_puedes_cosechar": (
        "Todavía no puedes coger esta parcela. El producto que echaste el {fecha} pide "
        "{dias} días de espera: podrás cogerla a partir del {fin}. Faltan {restantes} días."
    ),
    # --- el plazo de seguridad que no se sabe (A5 de T02) ---
    #
    # **Este mensaje es el tercer final, y faltaba.** Cuando el producto no traía el plazo de
    # seguridad —es opcional en su ficha y nadie lo pide—, el programa saltaba ese tratamiento y
    # **no decía nada**: se podía cosechar al día siguiente de tratar y el cuaderno no decía ni una
    # palabra. Un hueco ahí no es un dato que falta, es una cosecha con residuos. Ahora se dice, y
    # no bloquea: no se puede dejar al agricultor sin apuntar la cosecha que ha hecho, pero tampoco
    # se le puede dejar creyendo que está comprobado. Se dice **qué hacer para poder comprobarlo**.
    #
    # Singular y plural con `mensaje_con_cuenta`: «de 1 tratamiento(s)» es lo primero que hace
    # desconfiar de un programa.
    "V27_plazo_de_seguridad_sin_comprobar_uno": (
        "De 1 tratamiento de esta tierra no consta el plazo de seguridad, así que no hemos podido "
        "comprobar si ya puedes coger la cosecha. Mira la etiqueta del producto, apunta los días "
        "de espera en la ficha del producto (Mis cosas) y lo miraremos. La cosecha se puede "
        "apuntar."
    ),
    "V27_plazo_de_seguridad_sin_comprobar_varios": (
        "De {cuantos} tratamientos de esta tierra no consta el plazo de seguridad, así que no "
        "hemos podido comprobar si ya puedes coger la cosecha. Mira la etiqueta de esos productos, "
        "apunta los días de espera en su ficha (Mis cosas) y lo miraremos. La cosecha se puede "
        "apuntar."
    ),
    "V10_sin_justificacion": (
        "Pon por qué lo has echado. Por ejemplo: «vi pulgón», «aviso de la Junta» o "
        "«me lo dijo mi técnico»."
    ),
    "V11_franja_seguridad": (
        "Esta parcela tiene {agua} al lado. Hay que dejar sin tratar los metros de la "
        "orilla. ¿Los has dejado?"
    ),
    # **A12 (05/10/2026): cuando no se sabe si hay agua, se dice.** Antes, los dos campos nacían en `False`
    # y una tierra sin contestar se leía como «aquí no hay agua»: la franja de seguridad no se comprobaba y
    # el programa se callaba. Avisa y no bloquea: el apunte se puede guardar, pero el agricultor se entera
    # de que **esa comprobación no se ha hecho**, que es distinto de que no haya nada que respetar.
    "V11_no_se_si_hay_agua": (
        "En esta tierra no consta si hay un río, un arroyo o una toma de agua al lado, así que no se ha "
        "podido comprobar si hay que dejar sin tratar la orilla. Dilo en la ficha de la tierra y el "
        "programa lo comprobará solo."
    ),
    "V15_no_ecologico": (
        "Estás en ecológico y este producto no vale para ecológico. Tienes que usar otro."
    ),
    # **A13 (05/10/2026): la finca, en tres estados.** Este campo nacía en `False`, y ese «no» que nadie
    # había dicho **apagaba la comprobación ecológica entera**: si la finca es ecológica y la casilla no
    # está marcada, el programa dejaba de avisar de que un producto no vale para ecológico. Ahora, cuando
    # no consta, se dice que no se ha podido comprobar. Avisa y no bloquea.
    "V15_no_se_si_la_finca_es_ecologica": (
        "No consta si tu finca es de producción ecológica, así que no se ha podido comprobar si este "
        "producto se puede usar. Dilo en los datos de la finca y el programa lo comprobará solo."
    ),
    # El tercer estado en una finca ecológica. Antes esto no se decía nunca: el producto nacía con
    # «sí se puede en ecológico» puesto por defecto, así que la comprobación que más importa en una
    # finca ecológica estaba apagada. Avisa y no bloquea, por lo mismo que el de la autorización.
    "V15_no_se_si_es_ecologico": (
        "Tu finca es ecológica y en la ficha de este producto no pone si se puede usar en "
        "ecológico. Míralo en la etiqueta o pregúntalo en la tienda, y márcalo en la ficha. "
        "El apunte se puede guardar."
    ),
    "V16_producto_caducado": (
        "Ese bote caducó el {fecha}. Mira si te queda otro en buen estado."
    ),
    "V18_sin_parcela": (
        "Dinos en qué parcela lo has hecho, para poder apuntarlo."
    ),
    "V20_sin_instalacion": (
        "Dinos en qué nave o almacén lo has hecho, para poder apuntarlo."
    ),
    "V22_sin_superficie": (
        "Pon cuántas hectáreas has tratado. Si no lo sabes a ciencia cierta, pon las "
        "que tiene la parcela."
    ),
    # El sistema de la tierra (secano o regadío). **Estaba escrito dentro del router**, que es
    # justo donde no puede estar un texto que lee el agricultor: no pasaba por la prueba que
    # vigila que no hay jerga y no se podía revisar desde aquí. Se encontró al sacar a una función
    # común el alta y la corrección de una tierra (ronda 92).
    "V23_sistema_desconocido": "El sistema tiene que ser secano o regadío.",
    # Un grupo de una sola tierra. Lo mismo: estaba dentro del router. Va aquí desde la ronda 92,
    # cuando el alta y la corrección de un grupo pasaron a compartir las mismas comprobaciones.
    "V24_grupo_de_una_sola_tierra": (
        "Un grupo tiene que tener al menos dos parcelas. Si es una sola, no hace falta grupo."
    ),
    "F6_sin_cultivo_en_el_plan": "Pon qué cultivo vas a abonar.",
    "F7_sin_superficie_en_el_plan": "Pon cuántas hectáreas vas a abonar.",
    # --- lo que no se ha podido contar del abono (A4 y A6 de T02) ---
    #
    # Los tres mensajes de aquí abajo dicen lo mismo de tres formas distintas: **este cálculo se ha
    # quedado a medias, y por qué**. Son el tercer final que pide `AGENTS.md` —«hay tres finales, no
    # dos: bien, mal, y no lo he podido comprobar»— y ninguno bloquea, porque el abono ya se ha
    # echado y el cuaderno tiene que recogerlo. Lo que no puede es callarse y dar a entender que el
    # tope de nitrógeno está mirado.
    #
    # 1) Un abono apuntado en varias tierras a la vez del que no se puede saber qué tierra lo
    #    recibió. Antes estos apuntes **no contaban para ninguna tierra**, así que el tope de los
    #    170 kg no saltaba aunque se pasara de verdad.
    "F8_aporte_por_grupo_sin_comprobar_uno": (
        "En esta tierra hay 1 abono apuntado en varias tierras a la vez, y de ese apunte no se "
        "puede saber qué parte le tocó a esta, así que el nitrógeno del año está sin comprobar del "
        "todo. Si quieres que se mire bien, apunta el abono tierra por tierra. El apunte se puede "
        "guardar."
    ),
    "F8_aporte_por_grupo_sin_comprobar_varios": (
        "En esta tierra hay {cuantos} abonos apuntados en varias tierras a la vez, y de esos "
        "apuntes no se puede saber qué parte le tocó a esta, así que el nitrógeno del año está sin "
        "comprobar del todo. Si quieres que se mire bien, apúntalos tierra por tierra. El apunte se "
        "puede guardar."
    ),
    # 2) El abono que se está apuntando no dice lo que lleva. Sin composición no se puede calcular
    #    lo que aporta, y antes se guardaba como «cero nutrientes» **también en el documento que se
    #    firma**.
    "F9_composicion_sin_comprobar": (
        "De este abono no consta la composición (cuánto nitrógeno, fósforo y potasio lleva), así "
        "que no hemos podido calcular lo que aporta ni comprobar el tope de nitrógeno. Rellena la "
        "composición en la ficha del abono (Mis cosas) y lo miraremos. El apunte se puede guardar."
    ),
    # 3) Y lo mismo con lo que ya estaba apuntado en esa tierra: el nitrógeno del año es una parte
    #    de lo que se ha echado, y quien lo mire tiene que saberlo.
    "F10_lo_ya_apuntado_sin_composicion_uno": (
        "En esta tierra hay 1 abono apuntado del que no consta la composición, así que el nitrógeno "
        "del año es una parte de lo que se ha echado y el tope está sin comprobar del todo. Rellena "
        "su composición en Mis cosas y lo miraremos. El apunte se puede guardar."
    ),
    "F10_lo_ya_apuntado_sin_composicion_varios": (
        "En esta tierra hay {cuantos} abonos apuntados de los que no consta la composición, así que "
        "el nitrógeno del año es una parte de lo que se ha echado y el tope está sin comprobar del "
        "todo. Rellena su composición en Mis cosas y lo miraremos. El apunte se puede guardar."
    ),
    # 4) Y el tope mirado **tierra por tierra** cuando el abono va sobre un grupo entero: el tope es
    #    por tierra y por año, así que se comprueba cada una con su propia historia, y se nombra la
    #    que más llevaba. Sin esto, quien abona siempre por grupo no vería nunca el aviso.
    "F11_tope_estiercol_en_una_tierra_del_grupo": (
        "Ojo: {tierra} es una de las tierras de este grupo y ya lleva {ya} kilos de nitrógeno por "
        "hectárea al año en forma de estiércol o purín. Con este abono serían {total}, y no se "
        "pueden pasar de {tope}. Se puede apuntar, pero míralo antes de echar más."
    ),
    "V21_instalacion_de_otra_finca": (
        "Esa nave no está en tu cuaderno. Añádela primero en Mis cosas."
    ),
    # --- la superficie de la tierra cuando no se sabe (A7 de T02) ---
    #
    # **Estos dos mensajes existen porque un dato que no se sabía se estaba guardando como un cero**,
    # y ese cero no era un número feo en una lista: la tierra pasaba a no poder tratarse ni abonarse,
    # porque cualquier superficie la superaba. El agricultor veía «se pasa de la superficie de la
    # parcela» en una tierra que nunca había medido, sin saber que el cero lo había puesto el
    # programa. Ahora no se bloquea —el cuaderno tiene que recoger lo que se ha hecho en el campo— y
    # se dice **qué falta y dónde se arregla**, que es la regla de la casa: no se deja al agricultor
    # sin salida.
    #
    # Van en singular y en plural con `mensaje_con_cuenta`, y `{donde}` es «esta tierra» o «alguna
    # tierra de este grupo»: el mismo texto vale para el tratamiento y para el abono, como
    # `V18_sin_parcela`.
    "V25_tierra_sin_superficie": (
        "De {donde} no sabemos cuántas hectáreas tiene, así que no hemos podido comprobar que no "
        "te pases de su superficie. Apunta las hectáreas en Mis cosas (Tus tierras, corregir la "
        "tierra) y lo miraremos. El apunte se puede guardar."
    ),
    # Y cuando el recinto del SIGPAC sí tiene su superficie guardada, se le dice cuál es **para que
    # él decida**: proponer no es escribir. La del recinto es la del trozo entero, no la cultivada,
    # así que copiarla sola sería inventarse un dato (`models.Parcela.superficie_sigpac_ha`).
    "V26_tierra_sin_superficie_con_la_del_sigpac": (
        "De {donde} no sabemos cuántas hectáreas tiene, así que no hemos podido comprobar que no te "
        "pases de su superficie. El recinto del SIGPAC mide {sigpac} ha: míralo y, si es lo que "
        "cultivas, apunta esas hectáreas en Mis cosas (Tus tierras, corregir la tierra). El apunte "
        "se puede guardar."
    ),
    "V19_incompleto": (
        "Falta algo por poner, pero puedes guardarlo ahora y completarlo cuando quieras. "
        "Queda apuntado en la lista de lo que falta."
    ),
# --- abonos ---
    "F1_sin_cantidad": (
        "Pon cuántos kilos de abono has echado por hectárea."
    ),
    "F2_superficie_excedida": (
        "La parcela tiene {parcela} hectáreas y has puesto {usada}. Corrige la superficie."
    ),
    "F3_zona_nitratos": (
        "Esta parcela está en zona de nitratos. Ahí el abono tiene reglas más estrictas: como "
        "mucho {tope} kilos de nitrógeno por hectárea al año en forma de estiércol o purín, y "
        "no se puede abonar con el suelo inundado, helado o con nieve."
    ),
    "F4_sin_plan_regadio": (
        "Esta parcela es de regadío y le falta el plan de abono del año. Desde 2026 hay "
        "que tenerlo. ¿Lo hacemos?"
    ),
    "F5_plan_excedido": (
        "Con este abono te pasas de lo que tenías en el plan: el plan dice {plan} kilos de "
        "nitrógeno por hectárea y así llevarías {total}. Se puede apuntar, pero míralo."
    ),
    # --- las reglas de la zona de nitratos (Orden MAV/398/2022) ---
    "N1_estiercol_pasa_tope": (
        "Ojo: en zona de nitratos no se pueden echar más de {tope} kilos de nitrógeno por "
        "hectárea al año en forma de estiércol o purín, y así llevarías {total} "
        "({ya} que tenías apuntados y {nuevo} de este). Se puede apuntar, pero míralo antes "
        "de echar más."
    ),
    "N2_pendiente_organico": (
        "Esta parcela tiene un {pendiente} % de pendiente, y con más del {maximo} % solo se "
        "pueden echar abonos orgánicos SÓLIDOS. Si el que vas a echar es purín, que es "
        "líquido, aquí no se puede."
    ),
    "N3_tabla_cultivo": (
        "La tabla oficial para {cultivo} {sistema} da {referencia} kilos de nitrógeno por "
        "hectárea. Con los abonos que has apuntado este año y este llevarías {total}. "
        "La cifra puede ajustarse según la cosecha esperada: revísala antes de echar más. "
        "El apunte se puede guardar."
    ),
    # Este aviso es distinto de los tres de arriba: no dice que te hayas pasado de nada, dice
    # que **no se ha podido mirar**. Existe porque antes, cuando no sabíamos si la tierra estaba
    # en zona de nitratos, el programa callaba y parecía que lo había comprobado todo.
    "N4_no_se_si_es_zona_de_nitratos": (
        "De esta tierra no sabemos si está en zona de nitratos, así que no hemos podido mirar "
        "las reglas de abonado que se aplican ahí. Apunta el municipio de la tierra y lo "
        "comprobamos en el listado oficial. El apunte se puede guardar."
    ),
    # --- analíticas ---
    "N1_sin_material": (        "Dinos qué has mandado analizar: la tierra, el agua, la planta, lo que has "
        "recogido o si lleva restos."
    ),
    "N2_sin_fecha_de_muestra": (
        "Pon el día que cogiste la muestra. Es lo que dice si el análisis es de este año "
        "o de hace diez."
    ),
    "N3_sin_sitio": (
        "Dinos de qué parcela salió la muestra, para poder usar el análisis en el plan de "
        "abono."
    ),
    "N4_fechas_cruzadas": (
        "El resultado no puede ser de antes de coger la muestra. Mira las dos fechas."
    ),
    "N5_sin_numeros": (
        "Este análisis no tiene ningún número apuntado. Puedes guardarlo así y rellenarlo "
        "cuando tengas el boletín delante."
    ),
    "N6_residuos_sin_sustancia": (
        "En un análisis de restos hay que decir qué sustancia han encontrado. Míralo en "
        "el boletín."
    ),
    "N7_agua_con_nitrato": (
        "El agua con la que riegas trae {valor} mg/L de nitrato. Eso ya es abono que "
        "recibe el cultivo: cuéntalo en los aportes del plan para no echar de más."
    ),
    "N8_analisis_viejo": (
        "Este análisis es de hace {anios} años. Sirve de referencia, pero para decidir el "
        "abono de este año conviene uno más nuevo."
    ),
    "N9_sin_laboratorio": (
        "A este análisis le falta el laboratorio que lo ha hecho. Sin eso, en una "
        "inspección no se sabe de dónde sale el número."
    ),
    # --- medidas preventivas ---
    "P1_sin_ninguna": (
        "No has marcado ninguna medida preventiva. Si de verdad no haces ninguna, se "
        "puede dejar así; pero si haces alguna, márcala: sin eso no se puede demostrar "
        "que miraste otras cosas antes de echar producto."
    ),
    "P2_tratamiento_sin_medidas": (
        "Antes de echar producto, la ley pide haber probado otras cosas. Todavía no has "
        "dicho cuáles haces: se marcan una vez en «Lo que hago sin echar producto» y "
        "quedan apuntadas para todo el año."
    ),
    # --- lo que se vende ---
    "C1_sin_producto": (
        "Pon qué has vendido. Es lo que ponga en el albarán: trigo, cebada, remolacha…"
    ),
    "C2_sin_cantidad": "Pon cuánto has vendido.",
    "C3_sin_fecha": "Pon el día que salió.",
    "C4_fechas_cruzadas": (
        "El último día de la venta no puede ser antes del primero. Mira las dos fechas."
    ),
    "C5_sin_comprador": (
        "No has dicho a quién se lo has vendido. Si lo sabes, ponlo: es lo que te van a "
        "preguntar si hay un problema con la partida."
    ),
    "C6_venta_sin_cosecha": (
        "Llevas {vendido} kg vendidos y no has apuntado que cogieras la cosecha. Míralo, "
        "que es cosa de un minuto."
    ),
    "C7_mas_de_lo_cosechado": (
        "Llevas vendidos {vendido} kg y apuntaste que cogiste {cosechado} kg. Se puede "
        "apuntar, pero mira a ver si te falta apuntar alguna cosecha."
    ),
    # --- el asesor ---
    "S1_sin_ropo_asesor": (
        "A {nombre} le falta el número de inscripción de asesor. Sin ese número, la Junta no "
        "acepta el tratamiento: pídeselo y apúntalo en Mis cosas."
    ),
    "S2_asesor_sin_fecha": (
        "No has dicho qué día te asesoró. Si no te acuerdas, déjalo así; si lo sabes, "
        "apúntalo, que es lo que se mira."
    ),
    "S3_asesor_sin_validar": (
        "No has dicho si el técnico dio el tratamiento por bueno. Es una casilla de dos: "
        "favorable o desfavorable."
    ),
    # --- generales ---
    "guardado_ok": "Apuntado. Si te has equivocado, tienes unos segundos para deshacer.",
    "sin_cobertura": (
        "No hay cobertura. No te preocupes: lo hemos guardado en el móvil y se manda "
        "solo cuando llegues a casa."
    ),
    "pregunta_falta_algo": (
        "¿La semilla venía ya tratada? Si venía tratada cuenta como si hubieras echado "
        "producto, y hay que apuntar con qué."
    ),
    # --- avisos que ayudan (no agobian: uno al día como mucho) ---
    "A1_carne_caduca_pronto": (
        "El carné de {nombre} caduca el {fecha}. Ve pidiendo cita para renovarlo."
    ),
    "A2_iteaf_caduca_pronto": (
        "La ITV de {equipo} caduca el {fecha}. Pide cita con tiempo, que luego se junta todo."
    ),
    "A3_parcela_sin_cultivo": (
        "A {parcela} le falta decir qué cultivo tiene este año. Sin eso el cuaderno queda a medias."
    ),
    "A4_producto_caduca_pronto": "El bote de {producto} caduca el {fecha}. Míralo antes de usarlo.",
    # La autorización excepcional: es el permiso temporal para usar un producto que no está
    # autorizado con carácter general. Cuando se acaba, usarlo es una infracción.
    #
    # Que estos dos avisos no existieran no se notaba: el programa **ya tenía** la comprobación
    # que bloquea un tratamiento con la autorización caducada, pero la fecha no se podía meter
    # desde ninguna pantalla, así que la comprobación no podía saltar nunca.
    "A24_autorizacion_caduca_pronto": (
        "La autorización para usar {producto} acaba el {fecha}. Después de ese día ya no se "
        "puede usar, así que aprovecha o pide otra."
    ),
    "A25_autorizacion_caducada": (
        "La autorización para usar {producto} acabó el {fecha}. Ya no se puede usar: el programa "
        "no te dejará apuntarlo."
    ),
    # --- el número de registro, contra el listado oficial del MAPA ---
    #
    # Esto se puede comprobar desde la ronda 30 porque el **listado oficial de productos
    # fitosanitarios** está bajado en `data/fega/` (3.087 productos, con su número de registro y su
    # estado). Son **avisos, nunca bloqueos**: el agricultor decide. Y si el listado no está, el
    # programa **no dice nada** —«no lo sé» no es «no existe»—, que es lo que impide que este aviso
    # se convierta en una mentira el día que falte el fichero.
    "A26_numero_de_registro_desconocido": (
        "El número de registro de {producto} ({numero}) no aparece en el listado oficial de "
        "productos del MAPA. Míralo en la etiqueta del envase y corrígelo si hace falta: en una "
        "inspección es el número que se comprueba."
    ),
    "A27_producto_no_vigente": (
        "{producto} tiene el número de registro {numero}, y en el listado oficial del MAPA figura "
        "como «{estado}», no como autorizado. Antes de usarlo, confírmalo con quien te lo vendió."
    ),
    # El registro oficial escribe los números con ceros de delante (`ES-00849`) y en la etiqueta del
    # envase o en la factura se ven sin ellos. Esto **no** es «no existe»: es «está escrito de otra
    # forma», y decir la diferencia es lo que evita que el agricultor se pase una tarde buscando un
    # problema que no tiene.
    "A28_numero_de_registro_de_otra_forma": (
        "El número de registro de {producto} está apuntado como {numero}, y en el listado oficial "
        "del MAPA ese producto figura como {oficial}. Corrígelo para que cuadre con el registro."
    ),
    "A6_uno": (
        "Un apunte no dice por qué se echó el producto. Se puede completar cuando quieras."
    ),
    "A6_varios": (
        "{cuantos} apuntes no dicen por qué se echó el producto. Se pueden completar "
        "cuando quieras."
    ),
    "A7_uno": "Un apunte no dice cuánto producto se echó. Complétalo si puedes.",
    "A7_varios": "{cuantos} apuntes no dicen cuánto producto se echó. Complétalos si puedes.",
    "A8_todo_en_orden": "Lo tienes todo apuntado y sin nada pendiente. Así da gusto.",
    # **Un cuaderno sin empezar no está al día** (01/10/2026, T02). Con el año vacío, las comprobaciones no
    # tienen nada que mirar y la pantalla decía «No te falta nada por apuntar»: el silencio se leía como un
    # visto bueno. Este texto dice lo que pasa de verdad y, además, dice qué hacer.
    "A8_sin_nada_que_revisar": (
        "Todavía no hay nada apuntado este año, así que no hay nada que revisar. Empieza apuntando "
        "lo que hagas en el campo y aquí te iremos diciendo si falta algún dato."
    ),
    # Cuando se traen varias parcelas del SIGPAC de una vez. El plural importa: «1 parcelas» es lo
    # primero que hace desconfiar de un programa.
    "parcelas_traidas_uno": "Ya está: una parcela traída del SIGPAC.",
    "parcelas_traidas_varios": "Ya están: {cuantos} parcelas traídas del SIGPAC.",
    "A9_uno": (
        "Un apunte no dice quién echó el producto o con qué máquina. Se puede completar "
        "cuando quieras."
    ),
    "A9_varios": (
        "{cuantos} apuntes no dicen quién echó el producto o con qué máquina. "
        "Se pueden completar cuando quieras."
    ),
    "V8_faltan_dias": "Faltan {cuantos} días.",
    # La superficie de un grupo de parcelas. Va aparte del aviso de una sola parcela porque el
    # número que se enseña es otro: ahí la superficie de esa parcela, aquí la suma de las del
    # grupo. Decir «la parcela tiene 2,43 ha» cuando son cinco parcelas sería confundir.
    "V4_superficie_excedida_grupo": (
        "Entre todas las parcelas del grupo suman {parcela} hectáreas y has puesto {usada}. "
        "Corrige la superficie."
    ),
    "F2_superficie_excedida_grupo": (
        "Entre todas las parcelas del grupo suman {parcela} hectáreas y has puesto {usada}. "
        "Corrige la superficie."
    ),
    # El libro de movimientos del producto: cuánto entró y cuánto ha salido.
    #
    # Estos tres no son avisos de que algo esté mal: son las tres razones por las que **no se
    # puede hacer la resta**. La diferencia importa: decir «te quedan -3 kg» sería inventarse un
    # dato, y callarse que no se puede saber es lo contrario de lo que hace este programa.
    "A20_sin_cantidad_comprada": (
        "No has apuntado cuánto compraste, así que no se puede saber cuánto te queda. "
        "Apúntalo en la ficha del producto y aquí saldrán las cuentas."
    ),
    "A21_unidades_distintas": (
        "Lo compraste en {comprado} y lo echas en {gastado}. Son cosas distintas y no se pueden "
        "restar: un litro y un kilo no son lo mismo."
    ),
    "A22_gastado_mas_que_comprado": (
        "Has echado más de lo que apuntaste que compraste. Suele pasar cuando el producto venía "
        "de otro año o cuando falta apuntar una compra."
    ),
    "A23_de_otra_campana": (
        "Y en años anteriores has echado más todavía, así que lo más probable es que sea de una "
        "compra vieja."
    ),
    # --- generales ---
    # Lo que se dice cuando falla algo que no tiene un mensaje propio: descargar el cuaderno en
    # papel o en fichero, subir el papel de un documento, bajar el boletín de un análisis, subir el
    # cuaderno firmado…
    #
    # **Faltaba, y se notaba en pantalla:** diez sitios del programa lo pedían y el aviso salía
    # **en blanco**, que es peor que no avisar: el agricultor pulsa, no pasa nada y no sabe por qué.
    # Lo encontró la prueba que exige que todo texto que use la interfaz exista (ronda 32).
    "no_se_pudo": (
        "No se ha podido. Prueba otra vez; si sigue igual, avisa a quien te instaló el programa."
    ),
    # --- Borrar y corregir (ronda 91) ---
    #
    # Lo único que NO se puede borrar: un apunte firmado. La firma es la prueba de lo que había, y
    # `models.Firma` dice, con razón, que una firma no se borra nunca. El mensaje no se queda en el
    # «no»: dice qué hacer, que es la regla de todos los mensajes que bloquean algo.
    "B1_firmado_no_se_borra": (
        "Ese apunte está firmado, y una firma es la prueba de lo que había apuntado: no se puede "
        "borrar. Anúlalo: queda tachado, con su motivo, y la firma sigue cuadrando."
    ),
    # --- Borrar las tierras: la parcela, su cultivo y los grupos (ronda 92) ---
    #
    # Estas frases existen por el mismo motivo que la de arriba, y son **la única cosa que este
    # programa no puede hacer**: borrar una tierra que tiene apuntes encima. Los tratamientos, los
    # abonos, las labores, las cosechas, los análisis y las ventas apuntan a esa tierra por su
    # identificador; si desapareciera, esos apuntes dejarían de decir dónde se hizo el trabajo, que
    # es justo lo que se mira en una inspección. Por eso el mensaje **no se queda en el «no»**: dice
    # cuántas cosas dependen de ella y da las dos salidas que hay (borrarlas o corregirlas antes, o
    # corregir la tierra en vez de borrarla, que es lo que quiere de verdad quien se equivocó al
    # escribirla).
    #
    # Van en singular y en plural porque el número va delante: «Esa tierra tiene 1 apuntes» es lo
    # primero que hace desconfiar de un programa (ver `mensaje_con_cuenta`).
    "B2_tierra_con_apuntes_uno": (
        "Esa tierra tiene 1 apunte en el cuaderno. Bórralo o corrígelo antes, o corrige la tierra "
        "en vez de borrarla."
    ),
    "B2_tierra_con_apuntes_varios": (
        "Esa tierra tiene {cuantos} apuntes en el cuaderno. Bórralos o corrígelos antes, o corrige "
        "la tierra en vez de borrarla."
    ),
    # Un grupo es una agrupación para apuntar de una vez, no un dato del cuaderno. Pero los apuntes
    # que se hicieron con él guardan **el identificador del grupo** y no el de cada tierra: sin el
    # grupo, esos apuntes se quedarían sin decir dónde se hizo el trabajo. Se dice la cuenta y lo
    # que hay que hacer, como en el caso de la tierra.
    "B3_grupo_con_apuntes_uno": (
        "Ese grupo se ha usado en 1 apunte del cuaderno, y ese apunte dejaría de decir dónde se "
        "hizo. Bórralo o corrígelo antes de borrar el grupo."
    ),
    "B3_grupo_con_apuntes_varios": (
        "Ese grupo se ha usado en {cuantos} apuntes del cuaderno, y esos apuntes dejarían de decir "
        "dónde se hizo. Bórralos o corrígelos antes de borrar el grupo."
    ),
    # Quitar el cultivo declarado de una tierra (dejarla sin decir qué tiene sembrado). No se dice
    # «error» ni «no encontrado»: se dice lo que pasa, que es que no hay nada que quitar.
    "B4_no_hay_cultivo_que_quitar": (
        "Esa tierra no tiene dicho qué hay sembrado ese año, así que no hay nada que quitar."
    ),
    # --- Lo que se da de alta y no se puede borrar porque está en uso (ronda 93) ---
    #
    # El mismo problema que el de las tierras (B2) y los grupos (B3), pero para **todo lo demás que el
    # agricultor da de alta**: un producto que está dentro de un tratamiento, una máquina que se usó en
    # una labor, un abono que se echó, una nave donde se trató, un asesor que firmó un apunte, una
    # campaña con el año lleno, un plan que sostiene unos abonos.
    #
    # Se dicen **dos cosas y en este orden**, que es lo que hace que el mensaje sirva de algo: qué
    # pasaría si se borrara (el apunte se quedaría diciendo algo que ya no se sabe) y qué se puede
    # hacer ahora (corregir en vez de borrar, o vaciar lo que depende de ello). Y van en singular y en
    # plural porque el número va delante.
    #
    # **No nombran la cosa** («ese producto», «esa máquina»): el mismo mensaje lo usan seis fichas
    # distintas, y el agricultor ya sabe qué acaba de pulsar —lo tiene en la pantalla, encima del
    # aviso—. Escribir seis mensajes casi iguales sería seis sitios donde equivocarse al escribirlos.
    "B5_en_uso_uno": (
        "Esto lo usa 1 apunte del cuaderno, y ese apunte se quedaría sin decir lo que dice. "
        "Cámbialo en el apunte o bórralo antes, o corrige esto en vez de borrarlo."
    ),
    "B5_en_uso_varios": (
        "Esto lo usan {cuantos} apuntes del cuaderno, y esos apuntes se quedarían sin decir lo que "
        "dicen. Cámbialos o bórralos antes, o corrige esto en vez de borrarlo."
    ),
    # Y el mismo caso cuando lo que hay dentro no son apuntes sueltos sino **el año entero**: una
    # campaña con sus tratamientos, sus abonos y sus trabajos. Borrarla se llevaría por delante el
    # cuaderno de ese año.
    "B6_tiene_dentro_uno": (
        "Aquí dentro hay 1 cosa apuntada, y se borraría con esto. Bórrala o cámbiala de sitio antes, "
        "o corrige esto en vez de borrarlo."
    ),
    "B6_tiene_dentro_varios": (
        "Aquí dentro hay {cuantos} cosas apuntadas, y se borrarían con esto. Bórralas o cámbialas de "
        "sitio antes, o corrige esto en vez de borrarlo."
    ),
    # --- El libro del almacén (T09, 03/10/2026) ---
    #
    # Todos siguen la estructura de siempre —qué pasa y qué hago ahora— y los que bloquean lo dicen
    # con las palabras del agricultor: «anúlalo», «escríbelo», «míralo en el envase».
    #
    # **Lo que estos mensajes NO dicen nunca:** que un dato que falta sea un cero. Un albarán sin la
    # cantidad no es un albarán de cero litros, y por eso el programa lo apunta y dice que no sabe
    # cuánto, en vez de hacerle la cuenta con un cero que saldría mal para siempre.
    "AL1_una_recepcion_sin_lineas": (
        "Un albarán sin decir qué venía no apunta nada. Escribe al menos una cosa: qué producto, "
        "cuánto y de qué lote."
    ),
    "AL2_la_linea_no_dice_que_es": (
        "En esa línea no dices qué ha llegado. Elige el producto o el abono de tu lista, o escribe "
        "su nombre tal y como sale en el albarán."
    ),
    "AL3_la_unidad_no_cuadra": (
        "Este artículo lo llevas en {unidad} y esta línea viene en {otra}. Se ha apuntado lo que dice "
        "el albarán, pero no se ha podido sumar a lo que ya había: mira a ver si es el mismo producto."
    ),
    "AL4_la_caducidad_no_cuadra": (
        "De este lote ya tenías apuntado que caduca el {antes} y ahora dices el {ahora}. Se ha dejado "
        "lo que había: mira la fecha en el envase y corrige la que esté mal."
    ),
    "AL5_no_se_pudo_comprobar_si_ya_estaba": (
        "Como este albarán no lleva número (o no dice de quién es), no se ha podido comprobar si ya "
        "estaba apuntado. Míralo en la lista y anula el que sobre."
    ),
    "AL6_ese_albaran_ya_estaba": (
        "Ese albarán ya lo tenías apuntado{fecha}. No se ha vuelto a apuntar, así que no se ha contado "
        "dos veces. Si el que había estaba mal, anúlalo y apunta este."
    ),
    "AL7_esa_factura_ya_esta_en_otro_albaran": (
        "Esa factura ya está enganchada a otro albarán. Si es que te has equivocado de factura, elige "
        "la buena; si de verdad son dos albaranes de la misma factura, apunta el segundo con su "
        "número y engancha la factura al que la trajo."
    ),
    "AL8_tipo_de_movimiento_desconocido": (
        "Eso no es una cosa que pase en el almacén. Se puede apuntar que entró, que salió, que se "
        "perdió o que al contar había otra cantidad."
    ),
    "AL9_una_salida_necesita_su_apunte": (
        "Para sacar producto del almacén hay que decir de qué trabajo sale. Apúntalo desde el "
        "tratamiento o el abono, que ya saben cuánto se gastó."
    ),
    "AL10_falta_el_motivo": (
        "Aquí no hay ningún papel que explique esto, así que lo tiene que explicar quien lo apunta. "
        "Escribe en dos palabras qué ha pasado: se rompió, se contó distinto, me lo trajo un vecino…"
    ),
    "AL11_un_ajuste_necesita_la_diferencia": (
        "Un conteo distinto se apunta con lo que sobra o lo que falta. Di cuánto: si hay de más, en "
        "positivo, y si hay de menos, en negativo. Si sale cero, es que cuadra y no hay nada que "
        "apuntar."
    ),
    "AL12_una_merma_necesita_la_cantidad": (
        "Para apuntar lo que se ha perdido hace falta saber cuánto. Escribe la cantidad y en qué se "
        "mide."
    ),
    "AL13_falta_la_unidad": (
        "Falta decir en qué se mide esa cantidad. Sin eso no se puede restar de lo que hay en el "
        "almacén: pon litros, kilos o unidades."
    ),
    "AL14_ese_lote_no_es_de_ese_articulo": (
        "Ese lote es de otro producto. Elige uno de los lotes de este artículo, o apunta el lote "
        "nuevo con su número."
    ),
    "AL15_eso_no_gasta_del_almacen": (
        "Lo que gasta del almacén es un tratamiento o un abono. Eso que dices no saca producto, así "
        "que no se puede restar."
    ),
    "AL16_el_apunte_esta_anulado": (
        "Ese apunte está anulado, así que no gastó nada. Quita la anulación y vuelve a intentarlo."
    ),
    "AL17_el_apunte_no_dice_el_total": (
        "Ese apunte solo tiene la dosis por hectárea, y eso no es lo que se gastó: la dosis es lo que "
        "se echa en cada hectárea. Escribe cuánto has sacado del lote en total, o completa el apunte "
        "con la cantidad total."
    ),
    "AL18_el_lote_se_queda_en_negativo": (
        "De este lote quedan {queda} {unidad} y vas a sacar {sacas}. Puedes corregir la cantidad, "
        "apuntar la entrada que falta, o marcar que la diferencia es de verdad y seguir: lo que no se "
        "hace es apuntarlo a escondidas."
    ),
    "AL19_la_salida_ya_estaba_con_otra_cantidad": (
        "De este lote ya habías apuntado que se sacaron {antes} {unidad} para este trabajo, y ahora "
        "dices {ahora}. Se ha dejado lo que había. Si la cantidad buena es la de ahora, anula ese "
        "movimiento y vuelve a apuntarlo."
    ),
    "AL20_ya_estaba_anulado": (
        "Eso ya estaba anulado, con su motivo escrito. Si te has equivocado de motivo, corrígelo "
        "donde lo apuntaste."
    ),
    "AL21_la_factura_no_esta_dicha": (
        "Dices que esto viene de una factura, pero no dices de cuál. Elige la factura en tu lista de "
        "compras."
    ),
    "AL22_eso_tiene_su_puerta": (
        "Lo que sale de un albarán o de un trabajo se apunta desde ahí, no a mano: así queda escrito "
        "de dónde viene. Apúntalo en su pantalla y el almacén se ajusta solo."
    ),
    "AL23_esa_linea_no_es_de_esa_factura": (
        "Esa línea no es de la factura que has dicho. Míralo otra vez en el papel: elige la factura "
        "buena o la línea buena."
    ),
    "AL24_eso_se_anula_en_su_albaran": (
        "Esto entró con un albarán, así que se deshace anulando el albarán: lo que vino en un papel "
        "se corrige en ese papel. Anula el albarán y apunta el bueno, y el almacén se ajusta solo."
    ),
    # **El reenvío de una factura** (09/10/2026). El contrato §2 dice que reenviar el mismo comando
    # devuelve su resultado y no crea otro movimiento, y que el duplicado puede ser exacto (la misma
    # petición) o **posible** (el mismo emisor, número, fecha y total). Son dos cosas distintas y el
    # agricultor tiene que poder distinguirlas, así que se dicen con dos mensajes distintos.
    "AL25_esa_factura_ya_estaba": (
        "Esa factura ya la tenías apuntada{fecha}. No se ha vuelto a apuntar, así que no se ha "
        "contado dos veces. Si la que había estaba mal, corrígela; y si no vale, anúlala."
    ),
    "AL26_la_misma_clave_con_otros_datos": (
        "Esa petición ya se atendió, pero con otros datos: una misma petición no puede traer dos "
        "facturas distintas. Mira cuál de las dos es la buena y vuelve a mandarla como una petición "
        "nueva."
    ),
    "AL27_no_se_pudo_comprobar_si_ya_estaba_la_factura": (
        "Como esta factura no dice el número (o no dice de quién es), no se ha podido comprobar si ya "
        "estaba apuntada. Míralo en la lista y anula la que sobre."
    ),
    "AL28_ese_numero_ya_esta_con_otros_importes": (
        "De ese proveedor ya tienes una factura con ese número y ese año, y **no dice lo mismo**: "
        "una de las dos tiene los importes mal. Se ha dejado la que había. Si te has equivocado al "
        "apuntar, corrígela; y si de verdad son dos facturas, apunta la segunda con su número."
    ),    # **La ficha de la compra** (S11, 09/10/2026): lo que se ha facturado, lo que ha entrado de verdad, lo
    # que se ha pagado y lo que queda. Estas dos dicen lo que **no se puede saber**, que es tan importante
    # como las cifras: sin ellas, un hueco parecería un cero.
    "AL29_no_se_puede_saber_lo_recibido_por_linea": (
        "De esta factura, {cuantas} línea(s) no están enganchadas a ningún albarán línea a línea, así "
        "que no se puede saber cuánto ha entrado de cada una. Abajo están los albaranes que sí traen "
        "esta factura: míralos para saber qué falta por llegar."
    ),
    "AL40_esta_factura_no_ha_metido_nada_en_el_almacen": (
        "De esta factura no ha entrado nada al almacén todavía: la mercancía la mete el albarán, no la "
        "factura. Si ya la tienes en casa, apunta el albarán y engánchalo aquí."
    ),
    # Los dos avisos que pidió el revisor (09/10/2026): la ficha sumaba gastos anulados y callaba lo que
    # no sabía, así que dos pantallas daban dos cifras del mismo dinero y un cero parecía un dato.
    "AL41_los_gastos_no_cuadran_con_la_factura": (
        "La factura dice {facturado} y los gastos apuntados a ella suman {gastado}. Lo pendiente que "
        "enseña arriba es lo de los gastos, no lo de la factura: mira cuál de los dos está mal antes de "
        "darlo por bueno."
    ),
    "AL42_hay_gastos_sin_importe": (
        "De esta compra hay {cuantos} gasto(s) sin el importe apuntado, así que **no se puede saber lo "
        "que queda por pagar**: por eso arriba pone «—» y no una cifra. Apunta cuánto costó."
    ),
    "AL43_hay_gastos_anulados": (
        "De esta compra hay {cuantos} gasto(s) anulados. No cuentan en lo que se ha pagado ni en lo que "
        "queda —lo que se anuló no es una deuda—, pero siguen a la vista en Gastos por si hay que "
        "mirarlos."
    ),
    # **La corrección que quiere quitar una línea que un albarán está apuntando** (09/10/2026). Antes
    # contestaba 500 por la clave foránea; ahora lo dice y dice qué hacer.
    "AL44_no_se_puede_quitar_una_linea_con_albaran": (
        "No se puede quitar esa línea: un albarán dice que le corresponde, así que su mercancía se "
        "quedaría sin saber de qué compra es. Si la línea sobra, anula antes el albarán; y si lo que "
        "quieres es cambiar lo que dice, cambia sus números en vez de quitarla."
    ),
    # **El reintento de un móvil después de corregir la factura** (09/10/2026). No es un conflicto: el
    # comando se atendió, y su resultado cambió porque el agricultor lo cambió él.
    "AL45_esa_factura_se_corrigio_despues": (
        "Esa petición ya se atendió, y la factura {numero} se corrigió después, así que lo que dice ahora "
        "no es lo que traía esta petición. Se devuelve como está hoy: mírala antes de volver a mandarla."
    ),
    # Lo mismo para el dinero (09/10/2026): la misma clave con otro importe no es un reenvío.
    "G41_la_misma_clave_con_otros_datos": (
        "Esa petición ya se atendió, pero con otro dinero: una misma petición no puede traer dos pagos "
        "distintos. Mira cuál es el bueno y apunta el otro como una petición nueva."
    ),
    # **El mismo número y el mismo año, pero otro dinero** (CRM-00, 11/10/2026). No se bloquea —son dos
    # documentos, según el contrato §S10—, pero **no se calla**: el caso que llega de verdad es un número
    # tecleado mal, y el agricultor tiene que poder verlo sin buscarlo.
    "AL48_ese_numero_ya_esta_con_otro_total": (
        "Se ha apuntado. Ojo: ya tienes otra factura de ese proveedor con el número {numero}, del "
        "{fecha}, por {total}, y esta trae otro importe. Si es la misma y te has equivocado al teclear, "
        "corrige la que sobra; y si son dos documentos distintos, no hay nada que hacer."
    ),
    # **La que hay no dice el importe y esta sí** (CRM-00, 11/10/2026): no se apunta otra vez —el papel es el
    # mismo—, pero el importe que acaba de escribir no se tira sin decirlo.
    "AL49_la_que_hay_no_dice_el_importe": (
        "La factura {numero} ya estaba apuntada, pero **sin el importe**. No se ha apuntado otra vez; si "
        "quieres guardar estas cifras, corrige esa factura y ponle el importe ahí."
    ),
    # **El reenvío de un comando cuya factura se anuló** (09/10/2026, a petición de David). La clave no se
    # recicla: se contesta con el estado, y se dice cómo darla de alta otra vez.
    "AL46_esa_factura_esta_anulada_y_no_se_reapunta": (
        "Esa petición ya se atendió, y su factura está anulada{motivo}. No se ha apuntado nada: una "
        "petición ya usada no vale para dar de alta otra factura. Si la quieres otra vez, mándala como "
        "una petición nueva."
    ),
    # **El posible duplicado comercial que dice otra cosa** (09/10/2026): antes se contestaba «ya estaba»
    # y lo que llegaba se perdía en silencio. Ahora se para y se explica, para que decida el agricultor.
    "AL47_ese_numero_ya_esta_y_dice_otra_cosa": (
        "Ya tienes una factura de ese proveedor con el número {numero}, del {fecha}, por {total}, y "
        "**dice otra cosa** que esta. No se ha apuntado nada para no dejar dos versiones del mismo "
        "papel. Míralas: si la que había está mal, corrígela; y si de verdad son dos facturas distintas, "
        "apunta esta con su número."
    ),
    # Estas tres no son avisos de que algo esté mal: son las tres razones por las que **no se puede
    # hacer la resta**. Es la misma decisión que en la cesta (A20–A23): decir «te quedan 0 litros»
    # cuando no se sabe sería peor que decir que no se sabe.
    "AL30_falta_la_cantidad_uno": (
        "De este lote hay 1 movimiento sin la cantidad apuntada, así que no se puede saber lo que "
        "queda. Apunta cuánto era."
    ),
    "AL30_falta_la_cantidad_varios": (
        "De este lote hay {cuantos} movimientos sin la cantidad apuntada, así que no se puede saber "
        "lo que queda. Apunta cuánto era."
    ),
    "AL31_unidades_que_no_cuadran": (
        "En este lote hay cosas apuntadas en {unidades} y la cuenta se lleva en {cuenta}. Un litro y "
        "un kilo no son lo mismo, así que no se pueden sumar: míralo a ver si es el mismo producto."
    ),
    "AL32_falta_la_unidad_uno": (
        "De este lote hay 1 movimiento sin decir en qué se mide, así que no se puede hacer la cuenta. "
        "Apúntalo en litros, kilos o unidades."
    ),
    "AL32_falta_la_unidad_varios": (
        "De este lote hay {cuantos} movimientos sin decir en qué se miden, así que no se puede hacer "
        "la cuenta. Apúntalos en litros, kilos o unidades."
    ),
    "AL33_saldo_negativo": (
        "Sale más de lo que entró: falta apuntar una entrada o hay una salida de más. Míralo y "
        "apunta lo que falte."
    ),
    "AL34_el_albaran_esta_anulado": "El albarán del que salió esto está anulado, así que no metió nada.",
    "AL35_el_apunte_esta_anulado": "El apunte del que sale esto está anulado, así que no gastó nada.",
    "AL36_la_factura_esta_anulada": "La factura de la que salió esto está anulada.",
    "AL37_el_documento_ya_no_esta": (
        "El documento del que salió esto ya no está, así que no se puede comprobar y no se cuenta."
    ),
    "AL38_el_movimiento_esta_anulado": "Este movimiento está anulado.",
    # ----------------------------------------------------------------------
    # La identidad y las versiones del recinto (T05, 02/10/2026). Son los mensajes de la
    # importación de un lote de recintos y de su comparación entre campañas. Ninguno bloquea el
    # trabajo del agricultor: el que no se puede importar se explica, y lo demás se guarda.
    # ----------------------------------------------------------------------
    "R1_lote_sin_ano": (
        "No se sabe de qué año es este lote de recintos. Dinos el año y se puede guardar."
    ),
    "R2_ano_que_no_es_tuyo": (
        "Ese año no está en tu cuaderno. Elige uno de los años que tienes."
    ),
    "R3_ano_sin_crear": (
        "El año {anio} no está creado todavía en tu cuaderno. Créalo primero y vuelve a importar "
        "el lote."
    ),
    "R4_fuente_desconocida": (
        "El lote dice que viene de «{fuente}», y esa no es una de las fuentes que se guardan "
        "({fuentes}). Dinos de dónde viene."
    ),
    "R5_recinto_sin_datos": (
        "El recinto número {cuantos} del lote no trae ni su referencia ni su forma, así que no se "
        "sabe cuál es. Míralo en el papel y vuelve a importar el lote."
    ),
    "R6_recinto_repetido": (
        "El lote trae dos recintos distintos para la misma tierra ({clave}). Se ha tenido en cuenta "
        "el primero: mira el segundo en el papel."
    ),
    "R14_dos_recintos_de_la_misma_tierra": (
        "El lote trae dos recintos distintos para la misma tierra ({clave}) y no se sabe cuál de los "
        "dos vale, así que **no se ha dado de alta ninguno de los dos**. Míralos en el papel y vuelve "
        "a importar el que sea el bueno."
    ),
    "R7_tierra_ajena": (
        "Una de las tierras de este lote no está en tu cuaderno. Elige una de tus tierras."
    ),
    "R8_referencia_a_medias": (
        "El recinto {clave} viene sin el número de recinto, así que no se sabe de qué tierra es. "
        "Completa la referencia o dile al lote a qué tierra pertenece."
    ),
    "R9_tierra_ambigua": (
        "Hay {cuantas} tierras que podrían ser la de este recinto ({clave}) y no se sabe cuál. "
        "Dile al lote a qué tierra pertenece."
    ),
    "R10_sin_dos_superficies": (
        "De este recinto solo se conoce una superficie, así que no hay nada que comparar."
    ),
    "R11_superficies_que_no_cuadran": (
        "Las superficies de este recinto no cuadran entre sí: se llevan {diferencia} ha "
        "({porcentaje} %). Míralo antes de declararlo."
    ),
    "R12_superficies_que_cuadran": (
        "Las superficies que se conocen de este recinto cuadran: se llevan {diferencia} ha."
    ),
    "R13_resumen_de_la_comparacion": (
        "Comparadas las dos campañas: {iguales} igual, {cambiados} cambiados, {desaparecidos} "
        "desaparecidos y {nuevos} nuevos."
    ),
}


def mensaje_con_cuenta(base: str, cuantos: int) -> str:
    """Elige entre el singular y el plural.

    Parece un detalle tonto, pero "1 apuntes" es lo primero que hace desconfiar de un
    programa: si esto está mal escrito, ¿qué más estará mal? Y el agricultor que lee
    "1 apunte" sabe que el programa le habla a él, no a una máquina.
    """
    return mensaje(f"{base}_uno" if cuantos == 1 else f"{base}_varios", cuantos=cuantos)


# --------------------------------------------------------------------------
# La pantalla de inicio y los textos de la interfaz
#
# Decisión: el vocabulario de la interfaz vive AQUÍ, en el backend, y la interfaz lo
# pide a `/api/interfaz`. Podría estar escrito directamente en el HTML, pero entonces
# el test que garantiza que no hay jerga no lo cubriría, y en tres meses alguien
# volvería a escribir "cuaderno de explotación" en un botón.
# --------------------------------------------------------------------------

PANTALLA_INICIO: dict = {
    "saludo": "Hola",
    "pregunta": "¿Qué has hecho hoy?",
    "botones": [
        {
            "id": "echar_producto",
            "icono": "💧",
            "texto": "HE ECHADO PRODUCTO",
            "pista": "bichos, hierbas, hongos",
            "principal": True,
        },
        {
            "id": "abonar",
            "icono": "🟤",
            "texto": "HE ABONADO",
            "pista": "abono para la tierra",
            "principal": False,
        },
        {
            "id": "trabajo",
            "icono": "🚜",
            "texto": "HE HECHO UN TRABAJO",
            "pista": "sembrar, regar, coger",
            "principal": False,
        },
        {
            "id": "mi_cuaderno",
            "icono": "📖",
            "texto": "MI CUADERNO",
            "pista": "ver lo que tengo apuntado",
            "principal": False,
        },
        {
            "id": "papel",
            "icono": "🖨️",
            "texto": "SACAR EN PAPEL",
            "pista": "para imprimir",
            "principal": False,
        },
        {
            "id": "ayuda",
            "icono": "❓",
            "texto": "NO SÉ QUÉ PULSAR",
            "pista": "te lo explico",
            "principal": False,
        },
    ],
    "repetir": {
        "texto": "LO MISMO QUE LA ÚLTIMA VEZ",
        # Cuando la finca no tiene **ningún** apunte del año. Es un hecho comprobado contra los
        # números del cuaderno (`/api/cuaderno/resumen`), no una suposición del móvil: antes se
        # decía esto mismo mirando solo lo que el navegador recordaba, y quien había apuntado
        # desde otro aparato leía que su cuaderno estaba vacío.
        "vacio": (
            "Todavía no has apuntado nada. Empieza por el botón grande de arriba "
            "y en dos preguntas lo tienes."
        ),
        # Y esto se dice cuando sí hay apuntes, pero ninguno se puede repetir con dos toques:
        # solo se repite un tratamiento, y este año todavía no hay ninguno apuntado.
        "sin_poder_repetir": (
            "Este año ya has apuntado cosas, pero ningún tratamiento: el atajo de repetir sale "
            "con el primero que apuntes."
        ),
    },
}

# --------------------------------------------------------------------------
# React sin compilar: lo que se dice cuando no se puede dibujar la pantalla
#
# La pantalla de inicio se pinta con React (`backend/web/react/`), y React se carga con tres
# ficheros de `web/vendor/`. Si esos ficheros no llegan —un móvil sin cobertura con la caché
# a medias después de un despliegue—, la pantalla se quedaría en blanco, que es justo lo que
# no puede pasar delante de un agricultor. En su lugar se le dice esto y se le da el botón
# para volver a abrirla.
#
# **Estos textos viven aquí y no en el JavaScript**, como todos los demás: si el agricultor
# los puede leer, los revisa el test de la jerga.
# --------------------------------------------------------------------------

REACT: dict = {
    "sin_react": (
        "Esta pantalla no se ha podido abrir. Vuelve a abrir la aplicación; si sigue igual, "
        "dile a quien te la instaló que falta un fichero del programa."
    ),
    "recargar": "VOLVER A ABRIRLA",
}

TRABAJOS: tuple[dict, ...] = (
    {"id": "siembra", "icono": "🌱", "texto": "HE SEMBRADO"},
    {"id": "plantacion", "icono": "🌿", "texto": "HE PLANTADO"},
    {"id": "riego", "icono": "💦", "texto": "HE REGADO"},
    {"id": "cosecha", "icono": "🌾", "texto": "HE COGIDO LA COSECHA"},
    {"id": "otra", "icono": "🔧", "texto": "OTRO TRABAJO"},
)

# Y cuando dice «otro trabajo», ¿cuál? Estas son las prácticas que no tienen botón propio en la
# pantalla de inicio. **Dos de ellas las nombra el documento oficial de la Junta** para el
# apartado «Otras Prácticas Culturales»: el mantenimiento de la cubierta y el pastoreo. Antes no
# había forma de apuntarlas: todo lo que no fuera sembrar, plantar, regar o coger la cosecha
# acababa en el cajón de «otra», sin nombre.
#
# Los cuatro que ya tienen su botón en la pantalla de inicio NO están aquí: preguntarlos otra vez
# sería preguntar dos veces lo mismo.
#
# El orden no es alfabético a propósito: primero lo que más se hace en el campo.
TRABAJOS_DE_LABOR: tuple[dict, ...] = (
    {"id": "laboreo", "icono": "🚜", "texto": "HE LABRADO LA TIERRA"},
    {"id": "cubierta", "icono": "🌾", "texto": "HE MANTENIDO LA CUBIERTA"},
    {"id": "poda", "icono": "✂️", "texto": "HE PODADO"},
    {"id": "desbroce", "icono": "🌿", "texto": "HE DESBROZADO"},
    {"id": "escarda", "icono": "🧹", "texto": "HE ESCARDADO"},
    {"id": "pastoreo", "icono": "🐑", "texto": "HA PASTADO EL GANADO"},
    {"id": "otra", "icono": "🔧", "texto": "OTRA COSA"},
)

ACCIONES: dict[str, str] = {
    "apuntar": "APUNTARLO",
    "deshacer": "DESHACER",
    "dejarlo": "DEJARLO",
    "seguir": "SEGUIR",
    "volver": "VOLVER",
    # **Esta faltaba, y se notaba en pantalla.** `accion("guardar")` en `app.js` cae a su propio
    # nombre cuando la clave no está aquí: el botón de guardar salía escrito «guardar», en
    # minúscula y distinto de todos los demás. La pantalla de guardar un papel la llamaba desde el
    # principio. Se añade aquí —y hay una prueba que exige que toda clave que usa `app.js` esté en
    # esta tabla—, para que no vuelva a pasar con la siguiente.
    "guardar": "GUARDAR",
    "atras": "Atrás",
    "elegir_otra": "Elegir otra",
    "hoy": "Hoy",
    "ayer": "Ayer",
    "si": "Sí",
    "no": "No",
    "no_se": "No lo sé",
    "ver_las_cuentas": "MIS CUENTAS",
}

PANTALLA_CUADERNO: dict = {
    "titulo": "Mi cuaderno",
    "sin_nada": "Todavía no has apuntado nada este año.",
    "ver_papel": "SACAR EN PAPEL",
    # El fichero de datos: el registro en un formato que se puede guardar, abrir con Excel y
    # entregar si algún día lo piden. Es lo que la ley pide de verdad —llevar el registro y poder
    # enseñarlo—, sin depender de que la Junta tenga la ventanilla abierta: mandarlo es voluntario
    # (artículo 10.2 del Real Decreto 1054/2022).
    "sacar_datos": "GUARDAR LOS DATOS EN UN FICHERO",
    # Y aquí, lo mismo: **se dice de qué año es el fichero** (06/10/2026). Antes el servidor sacaba el año
    # más nuevo de la finca mientras el fichero se llamaba como el año que se estaba viendo; ahora sale el
    # que se está viendo, y la pista lo dice.
    "datos_pista": (
        "Se abre con Excel. Es tu cuaderno del año que estás viendo. Guárdalo: por si te lo piden"
    ),
    # Lo que de verdad obliga la ley, dicho donde el agricultor lo va a leer: al lado del botón con
    # el que se guarda el cuaderno. Mucha gente cree que está obligada a mandar los datos a la
    # Junta por internet, y **no lo está**: lo que es obligatorio es llevar el registro y poder
    # enseñarlo (artículo 10.2 del Real Decreto 1054/2022). Callarlo para «empujar» a usar la
    # ventanilla de la Junta sería engañar al que menos puede defenderse.
    "ley_pista": (
        "Llevar el cuaderno es obligatorio; mandarlo a la Junta por internet, no: es voluntario "
        "(artículo 10.2 del Real Decreto 1054/2022)."
    ),
    "falta_titulo": "Lo que falta por completar",
    "falta_vacio": "Lo tienes todo apuntado.",
    # **Y con el cuaderno sin empezar, esta sección no puede decir que está todo** (07/10/2026).
    #
    # Lo encontró David mirando la pantalla, no una suite: con el año recién creado, arriba se leía
    # «Todavía no has apuntado nada este año» (la frase del servidor, que ya se corrigió el 01/10) y **justo
    # debajo, en esta sección, «Lo tienes todo apuntado»**. Las dos frases se contradecían, y la de abajo
    # decía lo mismo que el silencio que la de arriba venía a evitar: un cuaderno sin empezar **no está al
    # día**. Cuando el servidor no ha podido mirar nada (`esta_completo: null`) esta sección dice esto.
    "falta_sin_empezar": "Aquí saldrá lo que te falte cuando apuntes algo.",
    # ── La frase de un vistazo, debajo del título (rediseño de la ronda 80)
    #
    # Es lo primero que se lee al abrir el cuaderno y contesta a la única pregunta que el agricultor se
    # hace antes de mirar nada más: «¿tengo el cuaderno al día?». Se dice **solo si el servidor ha
    # contestado** lo que falta: decir «no te falta nada» cuando la lista no ha llegado sería afirmar lo
    # que no se sabe, que es lo que este programa no hace.
    "pendiente_uno": "Te falta 1 cosa por apuntar",
    "pendientes_varios": "Te faltan {cuantas} cosas por apuntar",
    "pendientes_ninguno": "No te falta nada por apuntar",
    # ── Cada apunte, con cada dato dicho (rediseño de la ronda 79; los cuatro tipos desde la 91)
    #
    # Antes un apunte era una sola línea: «TRIGO BLANDO · 4,90 ha · 0,80 L/ha». Tres datos seguidos y sin
    # decir cuál es cuál, y **la tierra donde se echó no salía en ninguna parte** —que es justo lo que se
    # pregunta cuando llega una inspección—. Ahora cada apunte es una ficha con su número, su fecha y sus
    # datos con el nombre delante: estas palabras son los rótulos de esos datos.
    "apunte_numero": "Apunte {numero}",
    # El título de la lista, con el número delante y en singular o plural («1 apuntes» se lee fatal). Son
    # los cuatro tipos de apunte: lo que se echa, lo que se abona, lo que se trabaja y lo que se cosecha.
    "apuntes_titulo_uno": "1 apunte en el cuaderno",
    "apuntes_titulo_varios": "{cuantas} apuntes en el cuaderno",
    "tierra_y_parcela": "Tierra y parcela",
    "hectareas_tratadas": "Hectáreas tratadas",
    # El mismo nombre que en la etiqueta del campo («Cuánto producto por hectárea», ver `ETIQUETAS`),
    # acortado: dentro de la ficha el valor ya lleva su unidad («0,80 L/ha»).
    "cuanto_por_hectarea": "Cuánto por hectárea",
    "el_cultivo": "Cultivo",
    # El botón para apuntar otro tratamiento, dentro del bloque de los apuntes. Sin él, apuntar uno nuevo
    # desde aquí obliga a volver al inicio y buscarlo: en la pantalla que más se mira, eso son dos pasos
    # de más. Dos frases y no una porque con la lista vacía «otro» no tiene sentido.
    "apuntar_otro": "APUNTAR OTRO TRATAMIENTO",
    "apuntar_uno": "APUNTAR UN TRATAMIENTO",
}

# Las fincas de una cuenta: en cuál se está trabajando, y quién más entra en ella (ronda 89).
#
# Es lo que pidió David: «quiero que una explotación puedan acceder varias cuentas, no solo 1». Estas son
# las palabras que lee el agricultor, tanto en los avisos de la pantalla como en los del servidor: **aquí
# no se escribe una frase para el agricultor en ningún otro sitio**.
FINCAS: dict[str, str] = {
    "titulo": "Quién entra en mi finca",
    "explica": (
        "En tu finca puede entrar más de una cuenta: la tuya y la de quien te ayude (tu mujer, tu hijo, "
        "el técnico). Todos ven lo mismo y apuntan en el mismo cuaderno. Tú decides quién entra."
    ),
    "cambiar_titulo": "En qué finca estás trabajando",
    "cambiar_explica": (
        "Si puedes entrar en más de una finca, aquí eliges en cuál estás apuntando. Lo que apuntes va a "
        "la finca que elijas."
    ),
    "estas_en": "Estás en",
    "entrar_en": "PONME EN ESTA FINCA",
    "la_tuya": "Tuya",
    "papel_ayudante": "Ayudas en ella",
    # El botón y las palabras de la pantalla (los avisos del servidor van abajo).
    "anadir": "AÑADIR UNA CUENTA",
    "que_correo": "¿Con qué correo entra?",
    "que_correo_pista": "El correo con el que se dio de alta esa persona",
    "anadir_pista": (
        "La otra persona tiene que tener ya su cuenta hecha con ese correo: tú no puedes ponerle la clave."
    ),
    "quitar": "QUITARLE EL ACCESO",
    "titular": "Tú (titular)",
    "ayudante": "Ayuda en la finca",
    "tu_cuenta": "Tu cuenta",
    "eres_el_titular": "Eres el titular de esta finca: puedes añadir y quitar cuentas.",
    "no_eres_el_titular": (
        "En esta finca decide el titular quién entra. Si quieres que entre otra persona, pídeselo al "
        "titular."
    ),
    "solo_una": "De momento solo entras tú.",
    # Lo que puede hacer quien ayuda (ronda 90, del diseño de Stitch de esta pantalla): sin decirlo, el
    # titular no sabe qué le está dando a la otra persona, y la otra persona no sabe qué puede hacer. Es
    # **lo que hace de verdad el servidor**: el ayudante apunta lo que se haga en la finca con su cuenta,
    # y no puede decidir quién entra (eso es del titular, y la puerta contesta 403).
    "que_puede_ayudante": (
        "Puede apuntar lo que se haga en la finca con su propio móvil. No puede decidir quién entra ni "
        "quitar cuentas."
    ),
    # La etiqueta de la finca en la que se está trabajando, dentro de la lista (ronda 90): las demás llevan
    # su botón y esta no, así que se dice con palabras.
    "estas_aqui": "Estás trabajando aquí ahora",
    # La explicación del botón que lleva a esta pantalla desde «mis datos» (ronda 90, del diseño de Stitch
    # de esa pantalla). Sin ella, el botón se lee pero no se sabe qué hay dentro.
    "pista_boton": "Añadir otra cuenta que apunte en tu finca",
    # Cómo se llama el papel de cada uno en la lista. Hacen falta **los cuatro** y no dos: al titular de
    # la finca se le puede mirar desde dos sitios (eres tú, o eres el ayudante y el titular es otro) y lo
    # mismo pasa con el ayudante. «Tú (titular)» no vale para el titular cuando quien mira es el ayudante:
    # ahí hay que decir de quién es la finca, no quién eres tú. Y «Tu cuenta» es para que el ayudante se
    # reconozca en la lista sin tener que buscar su correo.
    "papel_titular": "El titular de la finca",
    # Los dos avisos de que la lista ha cambiado. Sin ellos, al añadir una cuenta lo único que cambia es
    # una línea más en la lista, y el agricultor no sabe si se ha hecho o no.
    "anadida": "Ya puede entrar en tu finca.",
    "quitada": "Ya no entra en tu finca.",
    # Quitar el acceso es lo único de esta pantalla que no se deshace con otro toque (habría que volver a
    # añadir el correo), así que se pregunta antes. Es el mismo `window.confirm` que usa el botón de salir.
    "confirmar_quitar": "¿Quitarle el acceso a esta cuenta? Podrás volver a añadirla cuando quieras.",
    # Los avisos del servidor (los lee el agricultor tal cual).
    "no_existe": "Esa finca no está.",
    "no_es_tuya": "Esa finca no es tuya o ya no tienes acceso a ella.",
    "solo_el_titular": "Solo el titular de la finca puede decidir quién más entra.",
    "cuenta_que_no_existe": (
        "No hay ninguna cuenta con ese correo. Que se dé de alta primero (con su correo y su clave) y "
        "vuelve a añadirla."
    ),
    "cuenta_no_activa": "Esa cuenta está desactivada.",
    "ya_eres_tu": "Esa cuenta es la tuya: ya entras en esta finca.",
    "ya_estaba": "Esa cuenta ya puede entrar en esta finca.",
    "no_entra": "Esa cuenta no entra en esta finca.",
    "el_titular_no_se_quita": (
        "El titular de la finca no se puede quitar: una finca sin titular se queda sin quien la gestiona."
    ),
    "no_se_pudo_quitar": "No se ha podido quitar el acceso.",
}

PANTALLA_ENTRAR: dict = {    "titulo": "Mi cuaderno",
    "crear": "CREAR MI CUADERNO",
    "entrar": "ENTRAR",
    "ya_tengo_cuenta": "Ya tengo cuenta",
    "primera_vez": "Es mi primera vez",
    "como_te_llamas": "¿Cómo te llamas?",
    "tu_nif": "Tu NIF",
    "tu_pueblo": "¿En qué pueblo está tu finca?",
    "tu_provincia": "¿En qué provincia?",
    "tu_correo": "Tu correo",
    "tu_clave": "Tu clave",
}

PANTALLA_AYUDA: dict = {
    "titulo": "Ayuda",
    "intro": (
        "Aquí está explicado todo lo que te pide el programa, en palabras normales. "
        "Si algo no lo entiendes, no lo apuntes mal: déjalo en blanco y pregúntame."
    ),
    "porques_titulo": "Para qué sirve esto",
    # Lo que la ley obliga y lo que no. Va en la ayuda porque es la primera pregunta de quien
    # empieza —«¿yo esto tengo que mandarlo?»— y porque la respuesta no es la que la gente cree:
    # llevar el registro es obligatorio, **mandarlo no**. Con el artículo delante, para que quien
    # lo lea pueda comprobarlo en el BOE y no tenga que fiarse de esta pantalla.
    "ley_titulo": "Qué te obliga la ley, y qué no",
    # Las dos etiquetas de sí o no de ese bloque (ronda 90, del diseño de Stitch de la ayuda): la primera
    # pregunta de quien empieza es «¿yo esto tengo que mandarlo?», y la respuesta se lee en la etiqueta sin
    # leer el párrafo. Solo las llevan dos de los seis puntos: los otros cuatro son explicaciones.
    "obligatorio": "Sí es obligatorio",
    "voluntario": "Es voluntario",
    # El título corto de cada punto de la ley, para que en la pantalla salga **cada uno con su nombre**
    # (rediseño de la ronda 83). Eran seis párrafos largos seguidos bajo un solo rótulo, y se leían como un
    # muro: no se sabía dónde acababa uno y empezaba el siguiente.
    "ley_llevar_titulo": "Llevar el cuaderno al día",
    "ley_mandar_titulo": "Mandar los datos a la Junta",
    "ley_programa_titulo": "Con un programa tuyo",
    "ley_fechas_titulo": "Las fechas que importan",
    "ley_cuando_obligatorio_titulo": "Cuándo será obligatorio del todo",
    "ley_sin_confirmar_titulo": "Lo que todavía no está aclarado",
    "ley_llevar": (
        "Llevar el cuaderno al día y poder enseñarlo si te lo piden: eso sí es obligatorio."
    ),
    "ley_mandar": (
        "Mandar los datos a la Junta por internet es voluntario. Lo dice el artículo 10.2 del "
        "Real Decreto 1054/2022: la ley te obliga a tener el registro, no a enviarlo. Si no lo "
        "mandas, no estás incumpliendo nada."
    ),
    "ley_programa": (
        "Puedes llevar el cuaderno con un programa tuyo, no hace falta usar el de la Junta: lo "
        "permite el artículo 10.3 del mismo real decreto, siempre que ese programa tenga todo lo "
        "que pide su anexo II. Este recoge los trece apartados que pide, y más abajo está apuntado "
        "lo que todavía no recoge por dentro, para que no te fíes de más."
    ),
    "ley_fechas": (
        "Las fechas que importan: los abonos se registran desde el 1 de enero de 2026, y el "
        "registro de los tratamientos puede ir en papel hasta el 31 de diciembre de 2026: a "
        "partir del 1 de enero de 2027 tiene que ser electrónico. El plan de abono es "
        "obligatorio desde el 1 de septiembre de 2026."
    ),
    "ley_cuando_obligatorio": (
        "Y una cosa que se dice poco: el cuaderno electrónico solo será obligatorio en el "
        "siguiente periodo de la PAC, el que viene después de 2027, y solo para las fincas de más "
        "de 30 hectáreas de cultivo —tierras de labor y cultivos permanentes, sin contar los pastos "
        "temporales—, las de más de 5 hectáreas de regadío o las que tengan invernaderos de más de "
        "0,1 hectáreas. Para las demás será voluntario, como ahora."
    ),
    "ley_sin_confirmar": (
        "Hay una cosa que todavía no está aclarada: si llevando el registro en tu programa hay que "
        "ir mandando los datos a la Junta cada cierto tiempo. Está preguntado por escrito y aquí se "
        "dirá lo que contesten."
    ),
    "campos_titulo": "Qué significa cada cosa",
    "repetir_no_se": (
        "Si no sabes qué pulsar, empieza por el botón grande. "
        "¿Has echado algo para los bichos o las hierbas? Ese es."
    ),
    # Las reglas de abono de la zona de nitratos. Se enseñan con su número y de dónde salen,
    # porque son las que pueden costar una sanción y el agricultor tiene derecho a leerlas.
    "reglas_titulo": "Las reglas de abono de las zonas de nitratos",
    "reglas_intro": (
        "Estas son las reglas del programa de actuación de Castilla y León. Solo se aplican si "
        "tu parcela está en una zona declarada con problemas de nitratos."
    ),
    "regla_con_numero": "El número que importa:",
    "regla_sin_numero": "Así funciona:",
    "lo_que_falta_titulo": "Lo que el programa todavía no puede comprobar",
    "lo_que_falta_intro": (
        "Esto no lo tenemos y por eso no te avisamos de ello. No es un olvido: se dice para "
        "que lo sepas y lo mires tú o tu técnico."
    ),
    "la_app_avisa": "El programa te avisa",
    "la_app_no_puede": "El programa no lo puede comprobar",
    "la_app_consulta": "La tabla está aquí para consultarla; el programa aún no comprueba tu caso",
    "aportes_titulo": "Cuánto nitrógeno permite la tabla para cada cultivo",
    "aportes_pista": (
        "Estas cifras son para parcelas en zona de nitratos. La tabla permite ajustar la dosis "
        "según la cosecha esperada. Si tu cultivo o forma de riego no aparece, no adivines el límite."
    ),
    "periodos_titulo": "Cuándo no se puede abonar",
    "periodos_pista": (
        "La fecha depende del cultivo y del abono. Algunas reglas cuentan desde la siembra o "
        "hasta la cosecha; consulta el caso concreto antes de echarlo."
    ),
    "secano": "Sin riego",
    "regadio": "Con riego",
    "organicos": "Abonos orgánicos",
    "minerales": "Abonos minerales",
    "sin_cifra": "La tabla no da una cifra para este caso",
    "unidad_nitrogeno": "kg N/ha",
}

# Las preguntas del asistente, en las palabras del agricultor.
# La clave es el nombre del dato; el valor, lo que se le pregunta.
ETIQUETAS: dict[str, dict[str, str]] = {
    # ── El grupo de tierras (ronda 92) ──────────────────────────────────────────────────────────────
    #
    # Un grupo lo junta el programa (las tierras que se llevan igual), así que la única pregunta que
    # tiene es **cómo lo llama el agricultor**: «Cebada (3 parcelas)» es como lo llama el programa, y
    # él lo llamará «el de mi hermano». Es el formulario entero de corregir un grupo.
    #
    # **Los otros cuatro campos no se preguntan y están aquí igual**, porque hay una prueba que exige
    # que todo campo del mapa de `app.js` (`CAMPOS`) tenga su pregunta y su pista en el servidor: sin
    # ellas, el día que alguien pinte ese campo saldría en blanco. Los suyos dicen lo que son, que es
    # lo único honesto que se puede decir de un campo que no se pregunta.
    "grupo.nombre": {
        "pregunta": "¿Cómo llamas tú a este grupo?",
        "pista": "El nombre que usas tú para estas tierras juntas",
    },
    "grupo.parcela_ids": {
        "pregunta": "¿Qué tierras van en este grupo?",
        "pista": "Las junta el programa: las que se llevan igual",
    },
    "grupo.campana_id": {
        "pregunta": "¿De qué año es el grupo?",
        "pista": "El año que estás llevando",
    },
    "grupo.cultivo": {
        "pregunta": "¿Qué se lleva en estas tierras?",
        "pista": "El cultivo que tienen en común",
    },
    "grupo.sistema": {
        "pregunta": "¿Secano o regadío?",
        "pista": "Lo que tienen en común esas tierras",
    },
    # El año del cuaderno (la campaña). Tres preguntas y las tres se contestan solas la primera vez: el
    # año nuevo sale con las fechas del año natural puestas, y el agricultor solo las cambia si su
    # cosecha empieza en septiembre.
    "campana.anio": {
        "pregunta": "¿De qué año es?",
        "pista": "El año del cuaderno: 2026, 2027…",
    },
    "campana.fecha_inicio": {
        "pregunta": "¿Cuándo empieza ese año?",
        "pista": "Muchas cosechas empiezan en septiembre, no en enero",
    },
    "campana.fecha_fin": {
        "pregunta": "¿Cuándo termina?",
        "pista": "El día en que se acaba ese año del cuaderno",
    },
    "campana.cerrada": {
        "pregunta": "¿Has terminado ese año?",
        "pista": "Márcalo cuando no vayas a apuntar nada más de ese año. Se puede desmarcar",
    },
    # Las dos fechas van en una sola pantalla: son una sola idea («cuándo empieza y cuándo termina ese
    # año»), y separarlas obligaría a pasar dos pantallas para decir una cosa.
    "campana.fechas": {
        "pregunta": "¿Cuándo empieza y cuándo termina ese año?",
        "pista": "Muchas cosechas empiezan en septiembre, no en enero",
    },
    "comun.parcela_id": {
        "pregunta": "¿Dónde?",
        "pista": "Toca la parcela donde has trabajado",
    },
    "tratamiento.tipo": {
        "pregunta": "¿Dónde has echado el producto?",
        "pista": "Casi siempre es en una parcela. Elige lo que corresponda",
    },
    "tratamiento.no_es_parcela": {
        "pregunta": "¿No es en una parcela?",
        "pista": "Si has tratado una nave o el producto ya recogido, dilo aquí",
    },
    "tratamiento.instalacion_id": {
        "pregunta": "¿En qué nave o almacén?",
        "pista": "Tiene que estar antes en Mis cosas",
    },
    "tratamiento.producto_cosechado": {
        "pregunta": "¿A qué producto se lo has echado?",
        "pista": "Al grano, a la fruta… lo que tenías guardado",
    },
    "tratamiento.lote_cosecha": {
        "pregunta": "¿De qué partida era?",
        "pista": "Si no lo sabes, déjalo en blanco",
    },
    "tratamiento.plazo_reentrada_dias": {
        "pregunta": "¿Cuántos días hay que esperar para entrar sin protección?",
        "pista": "Viene en la etiqueta. Es para que nadie entre antes de tiempo",
    },
    "comun.fecha": {
        "pregunta": "¿Cuándo?",
        "pista": "Si ha sido hoy, déjalo como está",
    },
    "comun.superficie_ha": {
        "pregunta": "¿Cuántas hectáreas?",
        "pista": "Si has hecho toda la parcela, déjalo como está",
    },
    "tratamiento.plaga": {
        "pregunta": "¿Qué problema tenías?",
        "pista": "Bichos, hierba, una enfermedad del cultivo",
    },
    "tratamiento.justificacion": {
        "pregunta": "¿Por qué lo has echado?",
        "pista": "Es lo que te van a preguntar en una inspección",
    },
    "tratamiento.producto_id": {
        "pregunta": "¿Qué producto has echado?",
        "pista": "Tiene que estar antes en los productos que has comprado",
    },
    "tratamiento.dosis": {
        "pregunta": "¿Cuánto por hectárea?",
        "pista": "Lo que pone en la etiqueta. Si te pasas, no te dejo apuntarlo",
    },
    "tratamiento.aplicador_id": {
        "pregunta": "¿Quién lo ha echado?",
        "pista": "Si has sido tú, elígete a ti",
    },
    "tratamiento.equipo_id": {
        "pregunta": "¿Con qué máquina?",
        "pista": "Tiene que tener la ITV en regla",
    },
    # La máquina de la labor. El contenido mínimo del CUE la pide en los bloques de labores y de
    # siembra, y solo la preguntaban los tratamientos: se podía apuntar que se labró y no con qué.
    "labor.equipo_id": {
        "pregunta": "¿Con qué máquina lo has hecho?",
        "pista": "Si lo has hecho a mano, deja el botón DEJARLO y sigue",
        "sin_maquinas": (
            "Si quieres apuntar con qué máquina, añádela primero en Mis cosas, apartado Máquinas "
            "de echar producto. Sin eso, el trabajo se apunta igual."
        ),
    },
    "tratamiento.franja_seguridad_respetada": {
        "pregunta": "¿Has dejado la orilla sin tratar?",
        "pista": "Los metros junto al río o a una toma de agua",
    },
    # Estas dos faltaban y se notó al mapear el cuaderno al formato de la Junta: el interfaz las
    # pide como campos obligatorios y el cuaderno no los preguntaba en ninguna pantalla. Se piden
    # aquí, con las palabras del campo y no las del manual.
    "tratamiento.aplicado_a_mano": {
        "pregunta": "¿Lo has echado a mano?",
        "pista": "Con mochila o con un apero de mano. Si has usado una máquina, contesta que no",
    },
    "tratamiento.eficacia": {
        "pregunta": "¿Cómo ha funcionado?",
        "pista": "Si todavía no lo sabes, déjalo en blanco y contéstalo otro día",
    },
    # Las condiciones de la aplicación. Van todas juntas en una pantalla opcional, y se saltan
    # con un toque: el agricultor que tiene prisa apunta el tratamiento y sigue.
    #
    # Que hagan falta se supo mirando qué campos del registro **no llegaban a ninguna pantalla**:
    # había once escritos en la base de datos y ninguno se podía rellenar. Y dos de ellos los pide
    # el contenido mínimo del CUE por su número: la hora de tratamiento (campo 3) y el estado de
    # la planta (campo 8).
    "tratamiento.como_fue": {
        "pregunta": "¿Quieres apuntar cómo fue?",
        "pista": "Es opcional. Si tienes prisa, dale a SEGUIR y ya está",
    },
    "tratamiento.hora_inicio": {
        "pregunta": "¿A qué hora lo echaste?",
        "pista": "Por ejemplo: 07:30. Lo pide el cuaderno de la Junta",
    },
    "tratamiento.hora_fin": {
        "pregunta": "¿Y a qué hora acabaste?",
        "pista": "Si no lo sabes, déjalo en blanco",
    },
    "tratamiento.estado_cultivo": {
        "pregunta": "¿Cómo estaba la planta?",
        "pista": "Naciendo, echando hoja, espigando, granando… Lo pide el cuaderno",
    },
    "tratamiento.como_estaba_el_dia": {
        "pregunta": "¿Cómo estaba el día?",
        "pista": "El viento es lo que más se pregunta cuando hay una queja de un vecino",
    },
    "tratamiento.temperatura_c": {
        "pregunta": "¿Qué temperatura hacía?",
        "pista": "En grados. Si no lo sabes, déjalo en blanco",
    },
    "tratamiento.humedad_pct": {
        "pregunta": "¿Había humedad?",
        "pista": "En tanto por ciento, si lo sabes",
    },
    "tratamiento.viento_kmh": {
        "pregunta": "¿Cuánto viento hacía?",
        "pista": "En kilómetros por hora. Con mucho viento el producto se va a donde no debe",
    },
    "tratamiento.viento_direccion": {
        "pregunta": "¿De dónde venía el viento?",
        "pista": "Norte, sur, levante, poniente…",
    },
    "tratamiento.volumen_caldo_l_ha": {
        "pregunta": "¿Cuánta mezcla has gastado por hectárea?",
        "pista": "En litros por hectárea, si lo sabes",
    },
    "tratamiento.operadores_expuestos": {
        "pregunta": "¿Cuántos estabais trabajando?",
        "pista": "Contando a ti. Es lo que se mira si alguien se pone malo",
    },
    "tratamiento.incidencias": {
        "pregunta": "¿Pasó algo raro?",
        "pista": "Si se atascó la boquilla, si sopló una racha, si te quedaste sin producto…",
    },
    "tratamiento.medidas": {
        "pregunta": "¿Qué hiciste antes para no tener que echarlo?",
        "pista": "Marca lo que hayas hecho. Puedes marcar varias",
    },
    "tratamiento.observaciones": {
        "pregunta": "¿Quieres apuntar algo más?",
        "pista": "Esto es opcional, puedes dejarlo en blanco",
    },
    "fertilizacion.fertilizante_id": {
        "pregunta": "¿Qué abono has echado?",
        "pista": "El nombre que viene en el saco",
    },
    "fertilizacion.kg_ha_producto": {
        "pregunta": "¿Cuántos kilos por hectárea?",
        "pista": "Los kilos de abono que has echado en cada hectárea",
    },
    "tratamiento.quien_maquina": {
        "pregunta": "¿Quién lo ha echado y con qué máquina?",
        "pista": "Si no lo sabes ahora, puedes dejarlo y completarlo otro día",
    },
    "tratamiento.resumen": {
        "pregunta": "Mira si está bien",
        "pista": "Si algo no cuadra, pulsa VOLVER y lo cambias",
    },
    "tratamiento.superficie": {
        "pregunta": "¿Cuántas hectáreas has tratado?",
        "pista": "Viene puesto lo que tiene la parcela. Cámbialo si has tratado menos",
    },
    "fertilizacion.resumen": {
        "pregunta": "Mira si está bien",
        "pista": "Si algo no cuadra, pulsa VOLVER y lo cambias",
    },
    "labor.que_has_hecho": {
        "pregunta": "¿Qué has hecho?",
        "pista": "Elige lo que más se parezca",
    },
    # «Otro trabajo» no dice nada: hay un apartado del cuaderno para las otras prácticas
    # culturales —labrar, mantener la cubierta, pastar— y hay que saber cuál es.
    "labor.cual": {
        "pregunta": "¿Cuál de estos?",
        "pista": "Si no es ninguno, elige OTRA COSA y lo escribes luego",
    },
    "labor.cosecha_cantidad": {
        "pregunta": "¿Cuánto has recogido?",
        "pista": "En kilos, si lo sabes. Si no, déjalo en blanco",
    },
    "labor.destino_cosecha": {
        "pregunta": "¿Qué salió de esta cosecha y qué quedó en el suelo?",
        "pista": "Contesta solo lo que sepas; sin respuesta no se supone que sea no",
    },
    "labor.cubierta_detalle": {
        "pregunta": "¿Cuándo estableciste la cubierta y cómo es?",
        "pista": "La fecha de establecimiento puede ser distinta del día en que la mantuviste",
    },
    "labor.restos_detalle": {
        "pregunta": "¿Dejaste los restos en el suelo?",
        "pista": "Se pregunta por separado para la poda y el desbroce",
    },
    "labor.datos_propios": {
        "pregunta": "¿Algún dato propio de este trabajo?",
        "pista": "Las preguntas cambian según el trabajo que elegiste",
        "sin_preguntas": "Este trabajo no necesita más datos.",
    },
    "cuaderno.repetir": {
        "pregunta": "¿Lo apuntamos otra vez?",
        "pista": "Puedes cambiar el día antes de apuntarlo",
    },
    "labor.detalles": {
        "pregunta": "¿Algo más que apuntar?",
        "pista": "Por ejemplo, cuántos kilos has recogido o de dónde salió el agua",
    },
}

# --------------------------------------------------------------------------
# Mis cosas: dar de alta parcelas, productos, abonos, aplicadores y máquinas
#
# Estas pantallas son las que hacen que la aplicación se pueda usar de verdad. Sin
# ellas, al agricultor nuevo se le dice "añade tu primera parcela" y no hay forma de
# hacerlo: se queda mirando una pantalla que le pide algo imposible.
# --------------------------------------------------------------------------

MAESTROS: dict[str, str] = {
    "titulo": "Mis parcelas, productos y máquinas",
    "intro": (
        "Aquí se da de alta lo que usas: la tierra, los productos, los abonos, quién "
        "aplica y las máquinas. Solo hay que hacerlo una vez, y luego apuntar es mucho "
        "más rápido."
    ),
    "mis_cosas": "MIS PARCELAS, PRODUCTOS Y MÁQUINAS",
    "anadir": "AÑADIR",
    "antes_de_empezar": "Antes de empezar",
    "falta_parcela": (
        "Para poder apuntar cualquier cosa hace falta tener al menos una parcela. "
        "Se tarda un minuto."
    ),
    "anadir_primera_parcela": "AÑADIR MI PRIMERA PARCELA",
    "seccion_parcela": "Parcelas",
    "seccion_producto": "Productos que he comprado",
    "seccion_abono": "Abonos",
    "seccion_aplicador": "Quién aplica el producto",
    "seccion_asesor": "Quién me asesora",
    "seccion_equipo": "Máquinas de echar producto",
    "seccion_instalacion": "Naves, almacenes e invernaderos",
    "pista_parcela": "Los trozos de tierra donde trabajas",
    "pista_producto": "Lo que has comprado para las plagas, las hierbas o los hongos",
    "pista_abono": "Los abonos que usas, con sus tres números",
    "pista_aplicador": "Tú, un trabajador o una empresa",
    "pista_asesor": (
        "El técnico que te dice qué hacer. Es distinto de quien echa el producto, aunque a "
        "veces sea la misma persona"
    ),
    "pista_equipo": "El pulverizador, el atomizador…",
    "pista_instalacion": (
        "Donde guardas el grano, la maquinaria o el producto. Sirve para apuntar los "
        "tratamientos de las naves"
    ),
    "sin_parcela": "Todavía no tienes parcelas.",
    "sin_producto": "Todavía no has apuntado ningún producto comprado.",
    "sin_abono": "Todavía no has apuntado ningún abono.",
    "sin_aplicador": "Todavía no has apuntado quién aplica.",
    "sin_equipo": "Todavía no has apuntado ninguna máquina.",
    "guardado": "Apuntado. Ya lo tienes disponible para cuando lo necesites.",
    "donde_se_usa": "Dónde se usa:",
    "parcela_se_usa": "Cuando dices dónde has echado el producto o has hecho un trabajo.",
    "producto_se_usa": "Cuando apuntas un producto que has echado.",
    "abono_se_usa": "Cuando apuntas que has abonado.",
    "aplicador_se_usa": "Cuando dices quién ha echado el producto.",
    "equipo_se_usa": "Cuando dices con qué máquina lo has echado.",
    "instalacion_se_usa": (
        "Cuando tratas una nave o un almacén, y cuando dices dónde has guardado la "
        "cosecha."
    ),
    "sin_asesor": "Todavía no has apuntado a ningún asesor.",
    "anadir_asesor": "AÑADIR QUIÉN ME ASESORA",
    "asesor_se_usa": (
        "Cuando apuntas un tratamiento y dices que te lo ha asesorado un técnico."
    ),
    "sin_instalacion": "Todavía no has apuntado ninguna nave ni almacén.",
    # ── El buscador de tierras (rediseño de la ronda 82)
    #
    # Con 51 tierras, apuntar dónde se ha echado el producto era recorrer la lista entera con el pulgar. El
    # buscador es lo que hace que se pueda escribir «prado» o el pueblo. Estas son sus palabras: la
    # etiqueta, el ejemplo que sale dentro de la casilla (para que se vea qué se puede escribir), la pista
    # de debajo, el botón y lo que se dice cuando no encuentra nada (con su salida, que es «verlas todas»).
    "buscar_tierra": "Buscar entre tus tierras",
    # El ejemplo que sale dentro de la casilla: unos números del SIGPAC, que es lo que menos se le ocurre
    # escribir y lo que más cuesta encontrar a mano. **No lleva el nombre de ninguna tierra de verdad**:
    # un ejemplo con un nombre real hace que la comprobación en el navegador crea que esa tierra sigue en
    # la lista después de buscar otra cosa.
    "buscar_tierra_ejemplo": "Por ejemplo: 503 51",
    "buscar_tierra_pista": "Escribe unas letras del nombre, del pueblo o del número del SIGPAC",
    "buscar_boton": "BUSCAR",
    "verlas_todas": "VERLAS TODAS",
    "buscar_sin_nada": "Con esas letras no encuentro ninguna tierra.",
    "buscar_sin_nada_pista": (
        "Prueba con menos letras, o míralo en la lista entera."
    ),
    # ── La tarjeta de una tierra en «Mis parcelas, productos y máquinas» (rediseño de la ronda 78)
    #
    # En esta pantalla la lista de tierras era un muro de filas de texto iguales: con 51 tierras, no se
    # distingue una de otra. Ahora cada tierra sale con la forma que tiene en el SIGPAC, su pueblo y sus
    # datos puestos **con su nombre delante** (una referencia del SIGPAC sin decir qué es no se entiende),
    # y con lo que hay sembrado este año. Estas palabras son las de esos rótulos.
    "tierra_numero": "Tierra n.º {numero}",
    "tierra_sigpac": "Referencia oficial SIGPAC",
    "tierra_cultivo": "Cultivo de este año",
    # El pie de la tarjeta: qué pasa si se toca. La tarjeta **abre** lo que hay sembrado en esa tierra,
    # que es lo único que se puede hacer con ella desde esta pantalla.
    "tierra_ver_cultivo": "VER O CAMBIAR LO QUE HAY SEMBRADO",
    # Lo que se dice cuando la tierra no tiene cultivo declarado este año. Va en ámbar y con el botón que
    # lo arregla dentro de la misma tarjeta, que es donde el agricultor está mirando.
    "tierra_sin_cultivo": "Le falta decir qué tiene sembrado este año",
    # Cuántas tierras hay dadas de alta. Dos frases y no una con paréntesis: «tienes 1 tierras apuntadas»
    # es exactamente el tipo de frase que hace que alguien deje de leer lo que pone la pantalla.
    "cuantas_tierras": "Tienes {cuantas} tierras apuntadas",
    "cuantas_tierras_una": "Tienes 1 tierra apuntada",
    # El dibujo del trozo que trae el SIGPAC. Va como etiqueta accesible (`aria-label`), porque
    # quien no ve el dibujo tiene que saber qué es.
    "dibujo_de_la_parcela": "La forma de la parcela según el SIGPAC",
    "anadir_instalacion": "AÑADIR UNA NAVE O UN ALMACÉN",
    "anadir_parcela": "AÑADIR UNA PARCELA",
    "anadir_producto": "AÑADIR UN PRODUCTO COMPRADO",
    "anadir_abono": "AÑADIR UN ABONO",
    "anadir_aplicador": "AÑADIR QUIÉN APLICA",
    "anadir_equipo": "AÑADIR UNA MÁQUINA",
    "grupo_opcional": "¿Quieres afinar más?",
    "grupo_opcional_pista": (
        "Esto es opcional. Si no lo sabes, pulsa DEJARLO y sigues: se puede rellenar "
        "otro día."
    ),
    "sin_sitio_titulo": "Esto lo he oído pero no sé dónde ponerlo",
    "falta_este_dato": "Falta esto: {pregunta}",
    "producto.unidad_dosis_etiqueta": "Cómo se mide la dosis",
}

# El dictado: decir en voz alta lo que se ha hecho y que se rellene solo.
DICTADO: dict[str, str] = {
    "titulo": "Dímelo con la voz",
    "intro": (
        "Cuéntame lo que has hecho con tus palabras y yo relleno el formulario. "
        "Tú lo miras antes de apuntarlo: lo que no entienda se queda en blanco."
    ),
    "boton": "HABLAR",
    "pista_boton": "cuéntamelo con tus palabras",
    "escuchando": "Te escucho… di lo que has hecho y pulsa PARAR",
    "parar": "PARAR",
    "no_se_puede": (
        "Este navegador no sabe escuchar. Escribe lo que has hecho y lo entiendo igual."
    ),
    "escribe": "Escribe lo que has hecho",
    # Debajo del recuadro, y por qué (ronda 90, del diseño de Stitch de esta pantalla): lo que se dicta
    # aparece ahí escrito, y el agricultor tiene que saber que **puede corregirlo con el dedo**. Sin
    # decirlo, una palabra mal oída parecía un fallo del programa del que no se podía hacer nada.
    "escribe_pista": (
        "Lo que digas queda escrito aquí. Si alguna palabra sale cambiada, corrígela con el dedo: lo que "
        "se apunta es lo que ponga aquí."
    ),
    "ejemplo": "Por ejemplo: «hoy he echado dos litros en el prado, había pulgón»",
    "entender": "ENTENDERLO",
    "no_he_oido": "No he oído nada. Prueba otra vez, o escríbelo.",
    "corregir": "CORREGIRLO A MANO",
    "apuntarlo": "ESTÁ BIEN, APUNTARLO",
    "he_entendido": "He entendido esto:",
    # Lo que el agricultor ha dicho, tal cual, en la pantalla de la revisión (ronda 90, del diseño de
    # Stitch de esa pantalla). Sin esto, lo único que ve son los datos ya colocados: si el programa ha
    # oído mal una palabra, no tiene con qué compararlo. Lleva los dos puntos porque los lleva el rótulo,
    # como los de la ayuda de un campo («Qué es:»).
    "has_dicho": "Has dicho:",
    "no_entiendo_esto": "Esto no lo he sabido colocar:",
}

# Las preguntas de cada campo de las pantallas de alta.
ETIQUETAS_MAESTRO: dict[str, dict[str, str]] = {
    # --- parcela ---
    "parcela.alias": {
        "pregunta": "¿Cómo llamas tú a esa tierra?",
        "pista": "El nombre que usas tú, para reconocerla de un vistazo",
    },
    "parcela.superficie_ha": {
        "pregunta": "¿Cuántas hectáreas tiene?",
        "pista": "Si lo sabes por el SIGPAC, ponlo tal cual",
    },
    "parcela.sistema": {
        "pregunta": "¿Es de secano o de regadío?",
        "pista": "Importa: el regadío tiene más obligaciones",
    },
    "parcela.ref_sigpac": {
        "pregunta": "¿Tiene número del SIGPAC?",
        "pista": "Si no lo sabes, déjalo en blanco: se puede poner después",
    },
    "parcela.municipio": {
        "pregunta": "¿En qué pueblo está?",
        "pista": "Junto con la provincia permite consultar la zona de nitratos",
    },
    "parcela.provincia": {
        "pregunta": "¿En qué provincia está?",
        "pista": "Pon la provincia de esta parcela, que puede ser distinta de la explotación",
    },
    # El uso del suelo. Se pregunta con la lista oficial del SIGPAC delante (TA - TIERRAS
    # ARABLES y así), que es exactamente como lo enseña el visor que usa el agricultor.
    "parcela.uso_sigpac": {
        "pregunta": "¿Qué es esa tierra?",
        "pista": "Como lo llama el SIGPAC. Si no lo sabes, déjalo en blanco",
    },
    "parcela.masa_agua_cerca": {
        "pregunta": "¿Hay río, arroyo o balsa dentro o al lado?",
        "pista": "Se pregunta para no contaminar el agua",
    },
    "parcela.captacion_consumo_humano": {
        "pregunta": "¿Hay una toma de agua para beber cerca?",
        "pista": "Si la hay, las reglas son más duras. Es importante decirlo bien",
    },
    "parcela.zona_vulnerable_nitratos": {
        "pregunta": "¿Está en zona de nitratos?",
        "pista": "Si no lo sabes, elige NO LO SÉ y no pasa nada",
    },
    # --- producto comprado ---
    "producto.nombre_comercial": {
        "pregunta": "¿Cómo se llama el producto?",
        "pista": "Tal y como viene en el envase",
    },
    "producto.numero_registro": {
        "pregunta": "¿Qué número trae la etiqueta?",
        "pista": "Es el número que va junto al nombre. Con él sabré qué lleva y cuánto esperar",
    },
    "producto.materia_activa": {
        "pregunta": "¿Sabes lo que lleva dentro?",
        "pista": "Si no lo sabes, déjalo en blanco: se rellena con el número de la etiqueta",
    },
    "producto.tipo_producto": {
        "pregunta": "¿Qué tipo de producto es?",
        "pista": "Escríbelo como aparece en la etiqueta. El código oficial sigue pendiente",
    },
    "producto.dosis_maxima": {
        "pregunta": "¿Cuánto se puede echar como mucho por hectárea?",
        "pista": "Lo que pone la etiqueta. Con esto te aviso si te pasas",
    },
    "producto.unidad_dosis": {
        "pregunta": "¿En qué se mide esa dosis?",
        "pista": "Viene en la etiqueta: por hectárea o por cada 100 litros",
    },
    "producto.plazo_seguridad_dias": {
        "pregunta": "¿Cuántos días de espera trae?",
        "pista": "Los días que hay que esperar antes de poder coger la cosecha",
    },
    "producto.lote": {
        "pregunta": "¿Qué número de lote trae?",
        "pista": "Viene en el envase. Sirve si hay un problema con esa partida",
    },
    "producto.fecha_caducidad": {
        "pregunta": "¿Cuándo caduca?",
        "pista": "Viene en el envase. Te aviso antes de que se pase",
    },
    # La autorización del producto. Existe una cosa que se llama «autorización excepcional»: es
    # un permiso temporal para usar un producto que no está autorizado con carácter general. Se
    # pide cuando aparece una plaga que no se puede combatir con lo que hay. Cuando se acaba, usar
    # ese producto es una infracción, así que el programa no deja apuntarlo.
    "producto.autorizado": {
        "pregunta": "¿Está autorizado este producto?",
        "pista": "Míralo en la etiqueta o pregunta en la tienda. Si no lo sabes, contesta NO LO SÉ",
    },
    "producto.permitido_ecologico": {
        "pregunta": "¿Se puede usar en ecológico?",
        "pista": "Solo importa si tu finca es ecológica. Si no lo sabes, contesta NO LO SÉ",
    },
    "producto.autorizacion_excepcional": {
        "pregunta": "¿Tiene un permiso especial?",
        "pista": "El número del permiso, si te lo han dado para una plaga concreta",
    },
    "producto.autorizacion_hasta": {
        "pregunta": "¿Hasta cuándo vale ese permiso?",
        "pista": "Después de esa fecha el programa no te dejará apuntarlo",
    },
    "producto.proveedor": {
        "pregunta": "¿Dónde lo has comprado?",
        "pista": "La tienda o la cooperativa",
    },
    # --- abono ---
    "abono.nombre": {
        "pregunta": "¿Cómo se llama el abono?",
        "pista": "Tal y como viene en el saco",
    },
    "abono.riqueza": {
        "pregunta": "¿Qué tres números trae el saco?",
        "pista": "Nitrógeno, fósforo y potasio. Por ejemplo: 33,5 - 0 - 0",
    },
    "abono.riqueza_n": {
        "pregunta": "Nitrógeno (el primer número)",
        "pista": "Si el saco no lo trae, pon 0",
    },
    "abono.riqueza_p": {
        "pregunta": "Fósforo (el segundo número)",
        "pista": "Si el saco no lo trae, pon 0",
    },
    "abono.riqueza_k": {
        "pregunta": "Potasio (el tercer número)",
        "pista": "Si el saco no lo trae, pon 0",
    },
    "abono.tipo": {
        "pregunta": "¿Es mineral o ecológico?",
        "pista": "Si no lo sabes, déjalo como está",
    },
    # --- aplicador ---
    "aplicador.nombre": {
        "pregunta": "¿Quién echa el producto?",
        "pista": "Escribe tu nombre si lo echas tú",
    },
    "aplicador.es_empresa": {
        "pregunta": "¿Es una empresa o una persona?",
        "pista": "Si es una empresa, se apunta su número de registro",
    },
    "aplicador.numero_carne": {
        "pregunta": "¿Qué número de carné tiene?",
        "pista": "El carné de echar productos. Sin él no se puede aplicar",
    },
    "aplicador.fecha_caducidad_carne": {
        "pregunta": "¿Cuándo caduca el carné?",
        "pista": "Te aviso un mes antes para que lo renueves",
    },
    "aplicador.numero_ropo": {
        "pregunta": "¿Tiene número de registro?",
        "pista": "Si no lo sabes, déjalo en blanco",
    },
    "aplicador.tipo_carne": {
        "pregunta": "¿Qué carné tiene?",
        "pista": "Lo pone en su carné: básico, cualificado, fumigador o piloto",
    },
    "aplicador.numero_reganip": {
        "pregunta": "¿Y número del registro de equipos?",
        "pista": "Solo si aplica productos con equipo aéreo o de otro tipo. Si no, déjalo",
    },
    # --- equipo ---
    # El cuaderno de la Junta pide la **descripción del equipo con su tipo, marca y modelo** y las
    # tres pestañas de su aplicación distinguen la maquinaria propia, la ajena y los equipos que no
    # van en el ROMA. Por eso se pregunta todo eso, y «de quién es» se pregunta en palabras llanas.
    "equipo.nombre": {
        "pregunta": "¿Cómo llamas tú a la máquina?",
        "pista": "Por ejemplo: el pulverizador, el atomizador grande",
    },
    "equipo.tipo": {
        "pregunta": "¿Qué máquina es?",
        "pista": "Un pulverizador, un atomizador, una mochila…",
    },
    "equipo.marca": {"pregunta": "¿De qué marca es?", "pista": "Si no lo sabes, déjalo"},
    "equipo.modelo": {"pregunta": "¿Y el modelo?", "pista": "Viene en la chapa de la máquina"},
    "equipo.titularidad": {
        "pregunta": "¿De quién es?",
        "pista": "Si la máquina no va inscrita en el ROMA, dilo aquí",
    },
    "equipo.fecha_adquisicion": {
        "pregunta": "¿Cuándo la compraste?",
        "pista": "Si no te acuerdas del día, pon el año",
    },
    "equipo.fecha_iteaf": {
        "pregunta": "¿Cuándo pasó la última inspección?",
        "pista": "La fecha del papel de la ITV",
    },
    "equipo.numero_roma": {
        "pregunta": "¿Qué número de registro tiene la máquina?",
        "pista": "Si no lo sabes, déjalo en blanco",
    },
    "equipo.fecha_proxima_iteaf": {
        "pregunta": "¿Cuándo le toca la ITV?",
        "pista": "Con la ITV caducada no se puede echar producto. Te aviso antes",
    },
    # --- instalación: naves, almacenes e invernaderos ---
    "instalacion.alias": {
        "pregunta": "¿Cómo llamas tú a esa nave?",
        "pista": "El nombre que usas tú: el almacén grande, la nave del grano…",
    },
    "instalacion.tipo": {
        "pregunta": "¿Qué es?",
        "pista": "Elige lo que más se parezca",
    },
    "instalacion.referencia_catastral": {
        "pregunta": "¿Tiene número del Catastro?",
        "pista": "Sale en el recibo del IBI. Si no lo sabes, déjalo en blanco",
    },
    "instalacion.municipio": {
        "pregunta": "¿En qué pueblo está?",
        "pista": "Si no lo sabes, déjalo en blanco",
    },
    "instalacion.uso": {
        "pregunta": "¿Para qué la usas?",
        "pista": "Por ejemplo: guardar el grano, guardar la maquinaria",
    },
    "instalacion.superficie_m2": {
        "pregunta": "¿Cuántos metros cuadrados tiene?",
        "pista": "Si no lo sabes, déjalo en blanco",
    },
    # --- el plan de abono del año ---
    "plan.cultivo": {
        "pregunta": "¿Qué vas a abonar?",
        "pista": "El cultivo que hay o que vas a sembrar",
    },
    "plan.necesidades": {
        "pregunta": "¿Qué necesita el cultivo?",
        "pista": "Kilos de cada cosa por hectárea. Si no lo sabes, déjalo en blanco",
    },
    "plan.necesidad_n": {
        "pregunta": "Nitrógeno (N)",
        "pista": "Lo que se va a llevar el cultivo. Si no lo sabes, pon 0",
    },
    "plan.necesidad_p": {
        "pregunta": "Fósforo (P)",
        "pista": "Si no lo sabes, pon 0",
    },
    "plan.necesidad_k": {
        "pregunta": "Potasio (K)",
        "pista": "Si no lo sabes, pon 0",
    },
    "plan.produccion_esperada_kg_ha": {
        "pregunta": "¿Cuánto esperas sacar?",
        "pista": "En kilos por hectárea. De ahí sale lo que la planta necesita",
    },
    "plan.aportes_suelo_agua": {
        "pregunta": "¿Qué le aporta ya la tierra o el agua?",
        "pista": "Lo que ya hay no hace falta echarlo. Si no lo sabes, déjalo en blanco",
    },
    "plan.notas": {
        "pregunta": "¿Quieres apuntar algo más?",
        "pista": "Esto es opcional",
    },
    # Si se usó una herramienta para hacer el plan. El anexo II lo pide con un sí o un no (el campo
    # «Herramienta» es booleano), así que se pregunta igual: sin inventarse listas ni equivalencias.
    "plan.herramienta": {
        "pregunta": "¿Has usado un programa o una herramienta para hacerlo?",
        "pista": "Si lo has calculado tú de cabeza, contesta que no",
    },

    # --- los análisis de laboratorio ---
    #
    # Lo que se le pregunta en cada paso del asistente. El nombre de cada número del
    # boletín no está aquí: sale del catálogo (`catalogos.PARAMETROS_ANALITICA`), porque
    # hay cinco clases de análisis y cada una trae números distintos.
    "analitica.tipo": {
        "pregunta": "¿Qué has mandado analizar?",
        "pista": "Elige lo que ponga el boletín. Casi siempre es la tierra",
    },
    "analitica.fecha_toma_muestra": {
        "pregunta": "¿Cuándo cogiste la muestra?",
        "pista": "El día que la cogiste, no el día que fuiste al laboratorio",
    },
    "analitica.sitio": {
        "pregunta": "¿De dónde salió?",
        "pista": "Toca la parcela de la que cogiste la muestra",
    },
    "analitica.no_es_parcela": {
        "pregunta": "¿No es de una parcela?",
        "pista": "El agua de una balsa o un lote de grano ya mezclado, por ejemplo",
    },
    "analitica.instalacion_id": {
        "pregunta": "¿De qué nave o balsa?",
        "pista": "Tiene que estar antes en Mis cosas",
    },
    "analitica.parametros": {
        "pregunta": "Copia los números del boletín",
        "pista": "Rellena solo los que vengan. Lo que dejes en blanco se queda en blanco",
    },
    "analitica.laboratorio": {
        "pregunta": "¿Quién ha hecho el análisis?",
        "pista": "El laboratorio que firma el boletín",
    },
    "analitica.informe": {
        "pregunta": "¿Qué número tiene el boletín?",
        "pista": "Viene arriba del papel. Si no lo ves, déjalo en blanco",
    },
    "analitica.fecha_resultado": {
        "pregunta": "¿Cuándo te dieron el resultado?",
        "pista": "El día que salió el boletín. Si no lo sabes, déjalo en blanco",
    },
    "analitica.lote": {
        "pregunta": "¿De qué lote o partida?",
        "pista": "Si la muestra era de un lote concreto, ponlo aquí",
    },
    "analitica.sustancia_detectada": {
        "pregunta": "¿Qué sustancia han encontrado?",
        "pista": "Lo que diga el boletín, tal cual",
    },
    "analitica.observaciones": {
        "pregunta": "¿Quieres apuntar algo más?",
        "pista": "Esto es opcional, puedes dejarlo en blanco",
    },
    "analitica.elegir_para_el_plan": {
        "pregunta": "¿De qué análisis sale este plan?",
        "pista": "De esta parcela. Si no tienes análisis, pulsa DEJARLO y sigue",
    },
    "medidas.marcar": {
        "pregunta": "¿Qué haces sin echar producto?",
        "pista": "Marca todo lo que hagas. Puedes marcar varias, y se puede cambiar cuando quieras",
    },
    "medidas.codigo": {
        "pregunta": "¿Y algo más que hagas tú?",
        "pista": "Escríbelo con tus palabras. Esto es opcional",
    },

    # --- el asesor: los campos de la pantalla de alta ---
    "asesor.nombre": {
        "pregunta": "¿Cómo se llama tu técnico?",
        "pista": "El asesor que te dice qué hacer en el campo",
    },
    "asesor.numero_ropo": {
        "pregunta": "¿Qué número de asesor tiene?",
        "pista": "Es su número del registro de asesores. Pídeselo, que sin él la Junta no acepta el tratamiento",
    },
    "asesor.ambito": {
        "pregunta": "¿De qué te asesora?",
        "pista": "De plagas, de producción integrada o de ecológico",
    },
    "asesor.entidad_certificacion": {
        "pregunta": "¿Qué entidad lo certifica?",
        "pista": "Si no lo sabes, déjalo en blanco",
    },
    "asesor.telefono": {
        "pregunta": "¿Su teléfono?",
        "pista": "Para poder llamarle. Opcional",
    },

    # --- el asesoramiento de un tratamiento ---
    "tratamiento.asesor_id": {
        "pregunta": "¿Te lo ha asesorado un técnico?",
        "pista": "Si lo has decidido tú solo, pulsa DEJARLO y sigue",
    },
    "tratamiento.asesor_fecha": {
        "pregunta": "¿Cuándo te lo dijo?",
        "pista": "El día que hablaste con él",
    },
    "tratamiento.asesoramiento_validado": {
        "pregunta": "¿Te dio el visto bueno?",
        "pista": "Si el técnico estuvo de acuerdo con el tratamiento",
    },

    # --- lo que se siembra ---
    "labor.semilla": {
        "pregunta": "¿Cuánta semilla has echado?",
        "pista": "En kilos. Si no lo sabes, déjalo en blanco",
    },
    "labor.semilla_detalle": {
        "pregunta": "¿De qué saco era la semilla?",
        "pista": "El número de lote. Sirve si hay un problema con esa partida",
    },
    "labor.siembra_directa": {
        "pregunta": "¿Ha sido siembra directa?",
        "pista": "Sin labrar antes, sobre el rastrojo del año pasado",
    },
    "labor.plantacion_detalle": {
        "pregunta": "¿Cómo has plantado?",
        "pista": "Cuántas plantas por hectárea y a qué marco. Si no lo sabes, déjalo",
    },
    # Estas tres **faltaban**: los campos salían en la pantalla de la siembra con la etiqueta
    # vacía, porque `pintaCamposMaestro` saca la pregunta de aquí y no había entrada. Se descubrió
    # buscando otra cosa, al comprobar que el mapeo oficial pide datos que el cuaderno no recoge.
    # Ahora hay un test que impide que vuelva a pasar con ningún campo de ninguna pantalla.
    "labor.material_tratado": {
        "pregunta": "¿La semilla venía tratada?",
        "pista": "Lo suele poner el saco o el albarán de la casa",
    },
    "labor.material_adquirido": {
        "pregunta": "¿La compraste?",
        "pista": "Si la semilla o la planta es de tu cosecha anterior, contesta que no",
    },
    "labor.fecha_adquisicion": {
        "pregunta": "¿Cuándo la compraste?",
        "pista": "El día del albarán",
    },

    # --- el pastoreo ---
    "labor.animales": {
        "pregunta": "¿De quién era el ganado?",
        "pista": "Si te han traído animales a pastar, o si son tuyos. Pueden ser las dos cosas",
    },
    "labor.animales_terceros": {
        "pregunta": "¿Los animales eran de otra persona?",
        "pista": "Si te han traído ganado a pastar, contesta que sí",
    },
    "labor.animales_propios": {
        "pregunta": "¿Y eran tuyos?",
        "pista": "Si el ganado es de tu explotación. Pueden ser las dos cosas",
    },
    "labor.semillas_siembra": {"pregunta": "¿Sacaste semilla para sembrar?", "pista": "De esta cosecha"},
    "labor.plantas_cosechadas": {"pregunta": "¿Recogiste plantas o partes de ellas?", "pista": "De esta cosecha"},
    "labor.sin_cosechar_ambiental": {"pregunta": "¿Dejaste algo sin cosechar por motivos ambientales?", "pista": "Por ejemplo, para proteger fauna"},
    "labor.restos_cosecha_depositados": {"pregunta": "¿Dejaste los restos de la cosecha en el suelo?", "pista": "Los restos segados o recogidos"},
    "labor.fecha_establecimiento_cubierta": {"pregunta": "¿Cuándo estableciste la cubierta?", "pista": "No es necesariamente la fecha de esta labor de mantenimiento"},
    "labor.tipo_cobertura": {"pregunta": "¿Qué tipo de cubierta es?", "pista": "Descríbela con tus palabras; falta el catálogo de códigos oficiales"},
    "labor.anchura_cubierta_m": {"pregunta": "¿Qué anchura tiene la cubierta?", "pista": "En metros"},
    "labor.anchura_libre_proyeccion_m": {"pregunta": "¿Qué anchura queda libre bajo la copa?", "pista": "En metros"},
    "labor.restos_desbroce_depositados": {"pregunta": "¿Dejaste los restos del desbroce en el suelo?", "pista": "Responde solo si lo sabes"},
    "labor.restos_poda_depositados": {"pregunta": "¿Dejaste los restos de la poda en el suelo?", "pista": "Responde solo si lo sabes"},
    "tratamiento.unidad_cantidad_aplicada": {"pregunta": "¿En qué unidad se mide la cantidad aplicada?", "pista": "Como aparece en la etiqueta o el albarán; falta el código oficial"},

    # --- las que faltaban ---
    #
    # Estas catorce se pintaban en pantalla **sin pregunta**: el campo estaba en el mapa de
    # `app.js` y se dibujaba, pero `pintaCamposMaestro` no encontraba el texto y salía un hueco en
    # blanco al lado de la casilla. Se descubrió con un test que recorre **todas** las claves del
    # mapa y exige que cada una tenga su pregunta (ver `test_interfaz.py`).
    #
    # Están agrupadas aquí, y no repartidas por su sección, porque juntas se entienden: son las
    # que se quedaron sin texto.
    "labor.cantidad_semilla_kg": {
        "pregunta": "Semilla que has echado",
        "pista": "En kilos. Si no lo sabes, déjalo en blanco",
    },
    "labor.dosis_siembra_kg_ha": {
        "pregunta": "Kilos por hectárea",
        "pista": "Si lo sabes. Si no, déjalo",
    },
    "labor.lote_semilla": {
        "pregunta": "El número de lote",
        "pista": "Viene en el saco. Sirve si hay un problema con esa partida",
    },
    # El tratamiento que recibió la semilla. Se pregunta **solo** cuando el agricultor ha dicho que
    # la semilla venía tratada: es lo que el anexo II pide además del «sí», y preguntarlo de una
    # semilla sin tratar sería preguntar por algo que no existe.
    "labor.tratamiento_semilla": {
        "pregunta": "¿Qué le habían echado a la semilla?",
        "pista": "Lo que ponga en la etiqueta del saco. Si no lo sabes, déjalo en blanco",
    },
    "labor.fecha_tratamiento_semilla": {
        "pregunta": "¿Cuándo se trató la semilla?",
        "pista": "Si no lo sabes, déjalo en blanco",
    },
    "labor.eficacia_tratamiento_semilla": {
        "pregunta": "¿Cómo ha funcionado?",
        "pista": "Lo mismo que se pregunta de un tratamiento del campo",
    },
    "labor.densidad_plantacion": {
        "pregunta": "Plantas por hectárea",
        "pista": "Si lo sabes",
    },
    "labor.marco_plantacion": {
        "pregunta": "A qué marco",
        "pista": "La distancia entre plantas y entre filas, por ejemplo 3 por 1,5 metros",
    },
    "labor.volumen_agua": {
        "pregunta": "Cuánta agua",
        "pista": "Lo que marque el contador, o lo que calcules",
    },
    "labor.unidad_agua": {
        "pregunta": "En qué la mides",
        "pista": "Metros cúbicos, metros cúbicos por hectárea o milímetros",
    },
    "labor.sistema_riego": {
        "pregunta": "Cómo riegas",
        "pista": "Aspersión, goteo, a manta…",
    },
    "labor.numero_contador": {
        "pregunta": "El número del contador",
        "pista": "El que viene en el recibo o en el aparato",
    },
    "labor.nitratos_agua": {
        "pregunta": "Los nitratos del agua",
        "pista": "Si tienes el análisis del agua. En miligramos por litro",
    },
    "producto.cantidad_comprada": {
        "pregunta": "Cuánto compraste",
        "pista": "Lo que ponga en la factura",
    },
    "producto.fecha_compra": {
        "pregunta": "Cuándo lo compraste",
        "pista": "El día de la factura",
    },
    "producto.unidad_compra": {
        "pregunta": "En qué lo compras",
        "pista": "Litros, kilos, unidades…",
    },
    "analitica.numero_informe": {
        "pregunta": "El número del informe",
        "pista": "Viene en el papel del laboratorio",
    },

    # --- el agua del riego ---
    "labor.agua": {
        "pregunta": "¿Cuánta agua has echado?",
        "pista": "Lo que marque el contador, o lo que calcules",
    },
    "labor.origen_agua": {
        "pregunta": "¿De dónde ha salido el agua?",
        "pista": "Del pozo, del canal, de la balsa…",
    },
    "labor.agua_detalle": {
        "pregunta": "¿Y los nitratos del agua?",
        "pista": "Si tienes el análisis del agua. El nitrato también abona, así que cuenta",
    },

    # --- lo que se vende ---
    "venta.tipo": {
        "pregunta": "¿Cómo lo has vendido?",
        "pista": "Si fue a un comprador o a la cooperativa, o si lo vendiste tú al cliente",
    },
    "venta.producto": {
        "pregunta": "¿Qué has vendido?",
        "pista": "Lo que ponga en el albarán: trigo, cebada, remolacha…",
    },
    "venta.variedad": {
        "pregunta": "¿De qué variedad?",
        "pista": "Si lo sabes. Si no, déjalo en blanco",
    },
    "venta.cantidad": {
        "pregunta": "¿Cuánto has vendido?",
        "pista": "El número que sale en el albarán",
    },
    "venta.unidad": {
        "pregunta": "¿En qué lo mides?",
        "pista": "El grano se vende en kilos o en toneladas",
    },
    "venta.fecha": {
        "pregunta": "¿Cuándo salió?",
        "pista": "El primer día, si salió en varios viajes",
    },
    "venta.fecha_fin": {
        "pregunta": "¿Y el último día?",
        "pista": "Si salió todo el mismo día, déjalo en blanco",
    },
    "venta.lote": {
        "pregunta": "¿De qué partida era?",
        "pista": "El número de lote. Sirve para saber de dónde salió",
    },
    "venta.comprador": {
        "pregunta": "¿A quién se lo has vendido?",
        "pista": "La cooperativa, el almacén o el cliente",
    },
    "venta.numero_albaran": {
        "pregunta": "¿Qué número tiene el albarán?",
        "pista": "El papel de la venta. Si no lo tienes a mano, déjalo en blanco",
    },
    "venta.de_donde": {
        "pregunta": "¿De qué parcela salió?",
        "pista": "Si salió de varias, elige una o déjalo en blanco",
    },
    "venta.observaciones": {
        "pregunta": "¿Quieres apuntar algo más?",
        "pista": "Esto es opcional, puedes dejarlo en blanco",
    },
    # **El dinero de una entrega NO tiene preguntas de asistente, y es una decisión** (T12, 03/10/2026). El
    # asistente de la venta es el recorrido del campo; el importe, el precio y el vencimiento se apuntan
    # después, en su propia pantalla. Se probó a meterlos aquí (tres preguntas más) y se quitó: el caso A08
    # del contrato es justamente **una entrega sin precio**, y alargar el asistente para un dato que casi
    # nunca se tiene en la parcela hace que el agricultor pase dos pantallas saltando. Sus textos viven en
    # `VENTA` (`importe`, `precio_unitario`, `vencimiento`, `de_que_cosecha`), que es donde los lee la
    # pantalla que sí los pregunta.
}

# Textos del plan de abono del año. La app oficial lo llama «recomendación de
# nutrientes»; aquí se llama plan de abono, que es como lo llama el agricultor.
PLAN: dict[str, str] = {
    "titulo": "El plan de abono del año",
    # El cultivo del año anterior en esa parcela. Lo calcula el programa desde el historial de
    # campañas: el anexo II lo pide en el plan de abono y el agricultor no tiene por qué acordarse.
    "precedente": "El año anterior había",
    # El rótulo de si el plan se hizo con una herramienta. Antes decía «Lo hice», y con el «Sí» detrás se
    # leía «Lo hice: Sí», que no dice el qué (ronda 85): la pregunta del asistente es «¿Has usado un programa
    # o una herramienta para hacerlo?», así que el rótulo dice lo mismo en corto.
    "herramienta_pregunta": "Lo hice con una herramienta",
    "explica": (
        "El plan dice qué abono vas a echar, cuánto y en qué momento. Después el "
        "programa compara lo que apuntas con lo que tenías previsto, para que no te "
        "pases sin darte cuenta."
    ),
    "sin_planes": "Todavía no tienes ningún plan de abono apuntado este año.",
    "hacer": "HACER EL PLAN DE ABONO",
    "guardado": "Plan guardado. Cuando apuntes un abono, podrás decir que va con él.",
    "se_usa": "Cuando apuntas que has abonado, puedes decir a qué plan responde.",
    "previsto": "Tenías previsto",
    "aplicado": "Llevas echado",
    "queda": "Te queda",
    "pasado": "Ojo: llevas más de lo que tenías previsto. Míralo antes de seguir abonando.",
    "sin_necesidades": (
        "A este plan le faltan las necesidades del cultivo, así que todavía no se puede "
        "comparar con lo que llevas echado."
    ),
    "apuntes_uno": "Un abono apuntado contra este plan.",
    "apuntes_varios": "{cuantos} abonos apuntados contra este plan.",
    "sin_apuntes": "Todavía no has apuntado ningún abono contra este plan.",
    # Desde el 1 de septiembre de 2026 el plan de abono es obligatorio en **todas** las unidades de
    # producción, no solo en regadío (artículo 4.2 del Real Decreto 1051/2022). Antes este texto
    # hablaba solo del regadío, y desde esa fecha se quedaba corto: un agricultor de secano lo leía
    # y creía que no iba con él.
    "obligatorio": (
        "El plan de abono es obligatorio desde el 1 de septiembre de 2026. En regadío lo es desde "
        "el 1 de enero de 2026, si el cultivo se sembró o se plantó entre marzo y junio."
    ),
    "kilos_por_hectarea": "kilos por hectárea",
    # El veredicto de un plan, en su etiqueta (ronda 90, del diseño de Stitch de esta pantalla): es la
    # primera pregunta al abrirla —«¿voy bien?»— y antes había que leerse la tabla entera para contestarla.
    "en_regla": "En regla",
    "alerta_exceso": "Alerta: exceso",
    "ver": "VER EL PLAN DE ABONO",
    "plan_de": "Plan de {cultivo}",
    "tabla_nutriente": "Qué",
    "tabla_previsto": "Tenías previsto",
    "tabla_aplicado": "Llevas",
    "tabla_queda": "Te queda",
    "tabla_pasado": "Pasado",
    "guardado_titulo": "Plan guardado",
    "apunta_abonos": (
        "Cuando apuntes un abono, podrás decir que va con este plan, y el programa irá "
        "llevando la cuenta por ti."
    ),
    "se_basa_en": "Este plan se apoya en un análisis:",
    "sin_analisis": (
        "Este plan no se apoya en ningún análisis. Si tienes uno de la tierra, se puede "
        "enganchar y queda todo junto."
    ),
}

# Textos de los análisis de laboratorio. La app oficial los llama «Analíticas»; aquí se
# llaman análisis, que es como se dice en el pueblo.
ANALITICA: dict[str, str] = {
    "titulo": "Los análisis",
    "explica": (
        "Aquí se guardan los análisis que has mandado hacer: de la tierra, del agua, de "
        "la planta o de la cosecha. Con los números de la tierra se abona mejor, y el "
        "papel del laboratorio no se pierde."
    ),
    "sin_analisis": "Todavía no has apuntado ningún análisis.",
    "anadir": "APUNTAR UN ANÁLISIS",
    "ver": "VER MIS ANÁLISIS",
    "guardado": "Análisis apuntado. Guárdalo bien: sirve para varios años.",
    "guardado_titulo": "Análisis apuntado",
    "se_usa": "Dónde se aprovecha esto:",
    "aprovecha": (
        "Cuando hagas el plan de abono de una parcela, podrás decir que se apoya en este "
        "análisis. Así, dentro de dos años, se sabe de dónde salía cada número."
    ),
    # El número, delante y con su palabra (rediseño de la ronda 81): es lo que hace que el bloque se lea
    # de un vistazo, sin contar los renglones de la lista. El singular y el plural, porque «1 análisis
    # guardados» es lo primero que hace desconfiar de un programa.
    "cuantos_uno": "1 análisis guardado",
    "cuantos": "{cuantos} análisis guardados",
    "sin_numeros": "Sin números apuntados: solo está guardado el boletín.",
    "subir_informe": "SUBIR EL PAPEL DEL LABORATORIO",
    "informe_subido": "Boletín guardado. Ya se puede descargar cuando lo necesites.",
    "informe_ya_esta": "Ya tienes el boletín guardado.",
    "descargar_informe": "DESCARGAR EL BOLETÍN",
    "sin_informe": (
        "De este análisis no tienes el papel guardado. Si lo tienes en el móvil o en "
        "papel, hazle una foto y súbela."
    ),
    "el_informe": "El papel del laboratorio",
    "de": "Análisis de {que}",
    "de_la_parcela": "de {parcela}",
    "cogida": "Muestra cogida el {fecha}",
    "resultado": "Resultado el {fecha}",
    "hace_anios": "Hace {anios} años",
    # La edad del boletín, en la etiqueta de la ficha (ronda 90, del diseño de «los análisis»): un
    # análisis de hace tres años no vale lo mismo que uno de este año, y eso hay que verlo de un vistazo
    # sin leer la fecha. El año se pega detrás, entre paréntesis, en `app.js`.
    "de_este_anio": "De este año",
    # El rótulo del bloque de números del boletín. Sin él, los números salen sueltos debajo de la ficha y
    # no se sabe si son del boletín o de otro sitio.
    "numeros_titulo": "Los números del boletín",
    "quien": "Laboratorio",
    "informe_numero": "Nº de boletín",
    "informe_titulo": "Informe de análisis",
    "informe_sin_nada": "Todavía no hay ningún análisis apuntado este año.",
    "usar_en_el_plan": "USAR ESTE ANÁLISIS EN EL PLAN",
    "apunta_primero": (
        "Primero apunta el análisis. Después, al hacer el plan de abono, podrás decir "
        "que se apoya en él."
    ),
    "sin_analisis_de_la_parcela": (
        "Esta parcela no tiene ningún análisis apuntado. Se puede hacer el plan igual."
    ),
    "parcela_vacia": "Sin parcela asignada",
    "sin_oficial": (
        "Los números que se guardan de cada clase de análisis son los que trae el boletín. "
        "De la tierra son los nueve que pide la administración; de lo demás, todavía no "
        "hay listado oficial."
    ),
    "subir_ahora": "¿Quieres subir el papel del laboratorio?",
    "subir_ahora_pista": (
        "Puedes hacerle una foto con el móvil. Así queda el original guardado."
    ),
    "saltar_informe": "AHORA NO, LO DEJO ASÍ",
    "sitio": "De dónde salió",
}

# Textos de las medidas preventivas de la explotación. La app oficial las tiene en
# «Explotación: Medidas Preventivas», y son la parte de la gestión integrada de plagas que
# se declara una vez y vale para todo el año.
MEDIDAS: dict[str, str] = {
    "titulo": "Lo que hago sin echar producto",
    "explica": (
        "Antes de echar producto, la ley pide haber probado otras cosas. Marca las que "
        "hagas en tu finca: se apuntan una vez y valen para todo el año."
    ),
    "sin_declarar": "Todavía no has dicho qué haces sin echar producto.",
    "declarada_una": "Tienes marcada {cuantas} medida. Se puede cambiar cuando quieras.",
    "declarada_varias": "Tienes marcadas {cuantas} medidas. Se pueden cambiar cuando quieras.",
    "declarada_ninguna": (
        "Has dicho que no haces ninguna de estas cosas. Si haces alguna, márcala: sin eso "
        "no se puede demostrar que miraste otras opciones antes de tratar."
    ),
    "hacer": "MARCAR LO QUE HAGO",
    "ver": "VER LO QUE HAGO SIN PRODUCTO",
    "guardado": "Apuntado. Cuando apuntes un producto, ya saldrá marcado lo que hagas aquí.",
    "guardado_titulo": "Medidas apuntadas",
    "se_usa": "Dónde se aprovecha esto:",
    "aprovecha": (
        "Al apuntar un producto, lo que hagas aquí ya sale marcado. Así el cuaderno "
        "demuestra que miraste otras cosas antes de tratarlo."
    ),
    "marcar_titulo": "Marca lo que hagas en tu finca",
    "marcar_pista": (
        "Toca las que hagas. Si te equivocas, vuelve a tocarla y se desmarca."
    ),
    "guardar": "GUARDAR",
    "no_hago_ninguna": "No hago ninguna de estas cosas",
    # ── Quitar la declaración entera (ronda 93) ──
    #
    # **No es lo mismo que «no hago ninguna»**, y la diferencia es la mitad de este texto: «no hago
    # ninguna» es una respuesta (el agricultor ha mirado las diez preguntas y ha contestado que ninguna) y
    # quitar la declaración es **volver a dejarlo sin contestar**. Por eso el botón se llama «borrar lo que
    # he dicho» y no «no hago ninguna», y por eso la explicación dice que el programa volverá a preguntar.
    "quitar": "BORRAR LO QUE HE DICHO DE ESTAS MEDIDAS",
    "quitar_pista": (
        "Esto no es decir que no haces ninguna: es dejar la finca sin contestar, como si no lo hubieras "
        "mirado nunca. El programa volverá a preguntártelo, y lo que has apuntado en cada tratamiento no "
        "se toca."
    ),
    "quitar_explica": (
        "Sirve para volver a empezar: si te equivocaste al contestar, o si quieres mirarlo otra vez con "
        "calma. Si lo que pasa es que no haces ninguna, mejor marca esa respuesta: así queda dicho."
    ),
    "quitado_titulo": "Borrado",
    "quitado": (
        "Tu finca vuelve a estar sin contestar estas preguntas. Cuando quieras, vuelve a mirarlas: no se "
        "ha perdido nada de lo que apuntaste en cada tratamiento."
    ),
    # La etiqueta de una medida ya marcada (ronda 90, del diseño de Stitch de esta pantalla). El visto del
    # cuadro y el color ya lo dicen; esto lo dice **con palabras**, que es la regla del proyecto.
    "hecho_en_mi_finca": "Hecho en mi finca",
    "informe_titulo": "Medidas preventivas (gestión integrada de plagas)",
    "informe_sin_nada": "Todavía no hay ninguna medida preventiva apuntada.",
    "observaciones": "Lo que quieras añadir",
    "observaciones_pista": (
        "Las diez preguntas no cubren todo. Si haces algo más, escríbelo aquí"
    ),
    "tus_palabras": "Tus palabras",
    "sin_observaciones": "Sin nada más apuntado",
    "de_la_finca": "En toda la finca",
    "en_el_apunte": "Lo que hiciste antes de echarlo",
    "del_ano": "Las de este año",
    "catalogo_aviso": (
        "Las diez preguntas son las medidas de la gestión integrada de plagas. El listado "
        "oficial de la Junta se publica «según catálogo» y no trae los códigos: los de "
        "aquí son internos, y lo que se imprime es el nombre de cada medida."
    ),
    "pregunta_en_el_tratamiento": "¿Qué hiciste antes para no tener que echarlo?",
    "pista_en_el_tratamiento": (
        "Ya viene marcado lo que dijiste que haces en tu finca. Quita lo que esta vez no "
        "hicieras"
    ),
}

# Textos de lo que se vende. La app oficial lo llama «Otras Actividades: Cosecha
# Comercializada»; aquí se llama «lo que he vendido», que es como lo dice el agricultor.
VENTA: dict[str, str] = {
    "titulo": "Lo que he vendido",
    "explica": (
        "Aquí se apunta lo que sale de la finca: a quién, cuánto y de qué parcelas salió. "
        "Es lo que cierra el cuaderno por arriba."
    ),
    "sin_nada": "Todavía no has apuntado ninguna venta este año.",
    "anadir": "APUNTAR UNA VENTA",
    "ver": "VER LO QUE HE VENDIDO",
    "guardado": "Venta apuntada. Ya se puede responder de dónde salió cada partida.",
    "guardado_titulo": "Venta apuntada",
    "se_usa": "Para qué sirve esto:",
    # El número de ventas, delante y con su palabra (rediseño de la ronda 81): lo que hace que el bloque
    # se lea de un vistazo. Se dice «ventas apuntadas» y no «entregas» porque es como llama a esto el
    # resto de la aplicación («APUNTAR UNA VENTA», «Venta apuntada»).
    "cuantas_una": "1 venta apuntada",
    "cuantas": "{cuantas} ventas apuntadas",
    "aprovecha": (
        "Con el lote y las parcelas de origen se puede responder «¿de dónde salió esta "
        "partida?» si algún día pregunta un cliente o una inspección."
    ),
    "de_que": "Venta de {producto}",
    "informe_titulo": "Cosecha comercializada",
    "informe_sin_nada": "Todavía no hay ninguna venta apuntada este año.",
    "cuadra": "Llevas vendidos {vendido} kg de los {cosechado} kg que apuntaste que cogiste.",
    "no_cuadra": (
        "Ojo: llevas vendidos {vendido} kg y apuntaste que cogiste {cosechado} kg. Mira a "
        "ver si te falta apuntar alguna cosecha."
    ),
    "sin_cosecha": (
        "Llevas vendidos {vendido} kg y no has apuntado ninguna cosecha. Si la cogiste, "
        "apúntala: así el cuaderno cuadra."
    ),
    "nada_cosechado": "Todavía no has apuntado ninguna cosecha este año.",
    "con_unidades": (
        "Hay ventas apuntadas en unidades, que no se pueden sumar con los kilos. Salen en "
        "el informe una a una."
    ),
    "tipo": "Cómo lo vendiste",
    "cuando": "¿Cuándo salió?",
    "hasta_cuando": "¿Y hasta cuándo?",
    "que": "¿Qué has vendido?",
    "variedad": "¿De qué variedad?",
    "cuanto": "¿Cuánto has vendido?",
    "unidad": "¿En qué lo mides?",
    "lote": "¿De qué partida?",
    "comprador": "¿A quién se lo has vendido?",
    "albaran": "¿Qué número tiene el albarán?",
    "de_donde": "¿De qué parcelas salió?",
    "observaciones": "¿Quieres apuntar algo más?",
    "tabla_dia": "Día",
    "tabla_que": "Qué",
    "tabla_cuanto": "Cuánto",
    "tabla_quien": "A quién",
    "tabla_lote": "Partida",
    "tabla_donde": "De dónde",
    "tabla_albaran": "Albarán",
    "vendido": "Lo que llevas vendido",
    "cosecha_apuntada": "Lo que apuntaste que cogiste",
    "queda_por_vender": "Te queda por vender",
    "un_viaje": "Un solo día",
    "varios_dias": "Salieron en varios días",
    "sin_comprador": "No lo has dicho",
    "sin_lote": "Sin partida",
    "sin_donde": "Sin decir de dónde",
    "varias_parcelas": "varias parcelas",
    # ── El dinero (T12, E6, 03/10/2026) ──────────────────────────────────────────────────────────
    #
    # **Esto decía lo contrario y se cambia aquí, con el motivo escrito.** El texto era: «Aquí no se
    # apunta el precio ni lo que te han pagado. Lo que pide la ley de esta sección es qué, cuánto y
    # cuándo; las cuentas van aparte». Era verdad mientras el programa no guardaba importes, y desde
    # el T12 es mentira: ahora se apunta el importe, el vencimiento y los cobros. Dejar el texto
    # viejo sería decirle al agricultor que no puede hacer algo que sí puede, que es peor que no
    # tenerlo. La segunda mitad del texto nuevo es la que no se puede quitar nunca: **lo que se hace
    # aquí es una cuenta de gestión y no un documento con validez oficial**, y eso lo dice el
    # contrato por escrito (la emisión fiscal completa «requiere especificación normativa propia
    # antes de activarse como tal»).
    "dinero_fuera": (
        "Aquí se apunta lo que te han de pagar y lo que te han pagado. La factura que se hace desde "
        "esta pantalla es tu cuenta de lo que has vendido: no es un documento con validez oficial."
    ),
    # Las cuatro cosas que el contrato manda separar, dichas como las dice el agricultor. Es el
    # párrafo que se lee al abrir la pantalla, y va aquí y no en el componente.
    "lo_que_se_separa": (
        "Una cosa es lo que coges de la tierra, otra lo que sacas de la finca, otra la factura que "
        "haces y otra el dinero que entra. Se apuntan por separado porque pasan en días distintos."
    ),
    # --- Las columnas de la tabla (las ocho del contrato, §4 S12)
    "tabla_cliente": "Cliente",
    "tabla_producto": "Producto",
    "tabla_fecha": "Fecha",
    "tabla_cantidad": "Cantidad",
    "tabla_importe": "Importe",
    "tabla_vencimiento": "Vencimiento",
    "tabla_cobrado": "Cobrado",
    "tabla_pendiente": "Pendiente",
    "tabla_estado": "Estado",
    "tabla_acciones": "Acciones",
    # --- La búsqueda y los filtros
    "buscar": "Buscar entre lo que has vendido",
    "buscar_pista": "Escribe el nombre del cliente, el producto o el número del albarán.",
    "buscar_boton": "BUSCAR",
    "buscar_limpiar": "VERLO TODO",
    "solo_pendientes": "SOLO LO QUE FALTA POR COBRAR",
    "solo_sin_importe": "SOLO LO QUE NO TIENE IMPORTE",
    "vacio_filtro": "Ninguna entrega contesta a esos filtros. Prueba a quitarlos.",
    # --- El pie: los números del conjunto filtrado, con lo que no se sabe dicho aparte
    "pie_una": "1 entrega · {importe} · pendiente {pendiente}",
    "pie_varias": "{entregas} entregas · {importe} · pendiente {pendiente}",
    # **Y el pie de cuando no se sabe ningún importe** (revisión del T12). El pie de arriba pone
    # `dinero.formatea(None)`, que es «0,00 €»: con un año de entregas sin precio, el número más grande
    # de la pantalla decía que se había vendido por cero euros, que es justo lo que prohíbe el A08 («no
    # lo sé» y «cero» no son lo mismo). Estas dos frases dicen lo que pasa sin dar ningún número.
    "pie_una_sin_importe": "1 entrega · importe sin apuntar · pendiente sin apuntar",
    "pie_varias_sin_importe": "{entregas} entregas · importe sin apuntar · pendiente sin apuntar",
    # **Aquí está la mitad honesta del pie.** Un total que suma lo que hay y calla que le faltan
    # importes parece que cuadra, y no cuadra: es el A08 del contrato dicho en el pie de una tabla.
    "faltan_importes_una": "A 1 entrega le falta el importe, así que no entra en estas cuentas.",
    "faltan_importes": "A {cuantas} entregas les falta el importe, así que no entran en estas cuentas.",
    # --- Los estados de una entrega, uno por uno (ver `app/ventas.py`)
    "estado_sin_importe": "Falta el importe",
    "estado_sin_facturar": "Sin facturar",
    "estado_sin_cobrar": "Sin cobrar",
    "estado_cobrada_en_parte": "Cobrada en parte",
    "estado_cobrada": "Cobrada",
    "estado_vencida": "Vencida",
    "estado_vencida_pista": "Pasó el día acordado y sigue sin pagarse.",
    # El estado de una factura que se ha quitado (revisión del T12). Sin esta palabra, una factura
    # anulada se leía como una factura de cero euros: lo que se enseña sigue siendo lo que decía, con su
    # estado dicho.
    "estado_anulada": "Quitada",
    # --- El aviso del A08, que es el que impide contar un cero
    "sin_importe_aviso": (
        "De esta entrega se sabe lo que salió y no por cuánto. No se cuenta como si valiera cero: "
        "queda con el importe pendiente hasta que pongas el precio o el importe del papel."
    ),
    "poner_importe": "PONER EL IMPORTE",
    "importe_titulo": "¿Por cuánto ha sido?",
    "importe_explica": (
        "Escribe el importe que te han dicho, o el precio y el programa lo calcula. Lo que no sepas "
        "se queda en blanco: un cero no es lo mismo que no saberlo."
    ),
    "importe": "El importe",
    "importe_pista": "Lo que pone el papel del comprador, en euros. Por ejemplo: 1.205,40",
    "precio_unitario": "El precio de cada kilo o unidad",
    "precio_unitario_pista": (
        "Lo que te pagan por kilo. Si escribes el importe, este dato se queda solo como apunte de lo "
        "que pactaste."
    ),
    "vencimiento": "¿Cuándo te lo tienen que pagar?",
    "vencimiento_pista": "Si no lo habéis dicho, déjalo en blanco.",
    "de_que_cosecha": "¿De qué cosecha salió?",
    "de_que_cosecha_pista": (
        "La cosecha que apuntaste de esa tierra. Sirve para saber de dónde salió la partida."
    ),
    "sin_cosecha_apuntada": "Sin decir de qué cosecha",
    "cliente_ficha": "¿Es uno de tus contactos?",
    "cliente_ficha_pista": "Si lo eliges, sus datos ya no hay que volver a escribirlos.",
    "sin_contacto": "Sin enlazar con ninguna ficha",
    "importe_guardado": "Importe apuntado.",
    "importe_calculado": "Se calcula del precio por la cantidad, y sale {importe}.",
    # --- Los ajustes y las devoluciones
    "ajuste_poner": "APUNTAR UNA DEVOLUCIÓN O UN AJUSTE",
    "ajuste_titulo": "¿Qué ha pasado con esta entrega?",
    "ajuste_explica": (
        "Aquí se apunta lo que cambia el importe o los kilos después de haber entregado: lo que te "
        "devuelven, y lo que se ajusta por peso, por humedad o por calidad. Cada uno dice de dónde "
        "sale, para que dentro de un año se sepa."
    ),
    "ajuste_tipo": "¿Qué ha pasado?",
    "ajuste_cantidad": "¿Cuántos kilos cambian?",
    "ajuste_cantidad_pista": (
        "Con el signo: lo que te devuelven va en negativo. Por ejemplo: -3.000"
    ),
    "ajuste_importe": "¿Cuántos euros cambian?",
    "ajuste_importe_pista": (
        "Con el signo: lo que te devuelven o lo que te descuentan va en negativo. Por ejemplo: -40,50"
    ),
    "ajuste_origen": "¿Quién lo dice?",
    "ajuste_origen_pista": (
        "De dónde sale el número. Sin esto, un ajuste es un número suelto y no se puede defender."
    ),
    "ajuste_motivo": "¿Por qué?",
    "ajuste_motivo_pista": "Con tus palabras. Por ejemplo: «el trigo venía con mucha humedad».",
    "ajuste_evidencia": "¿Qué papel lo demuestra?",
    "ajuste_evidencia_pista": (
        "El número del boletín o lo que dijo el básculero. Si tienes el papel, se puede subir después."
    ),
    "ajuste_sin_papel": "Sin papel adjunto",
    "ajuste_guardado": "Apunte añadido. El importe de la entrega ya lo tiene en cuenta.",
    "ajuste_anular": "QUITAR ESTE AJUSTE",
    "ajuste_quitar_pista": (
        "El importe de la entrega vuelve a ser el de antes. El papel que lo demostraba se queda "
        "guardado, por si hay que enseñarlo."
    ),
    # El motivo con el que se apunta una anulación desde la pantalla que pregunta. Es el mismo que usa
    # el resto de la aplicación para lo mismo, y va aquí y no escrito en el JavaScript: **el agricultor
    # lee lo que la pantalla le dice**, pero lo que se guarda en el historial también es suyo.
    "ajuste_motivo_al_quitar": "Me he equivocado al apuntarlo",
    "ajuste_anulado": "Apunte quitado del importe.",
    "ajuste_sin_nada": (
        "Ese apunte no cambia ni los kilos ni los euros, así que no he apuntado nada. Escribe "
        "cuánto cambia, o cuéntalo en las observaciones de la entrega."
    ),
    "ajustes_de_esta_entrega": "Lo que ha cambiado después de entregar",
    "tipos_de_ajuste": {
        "devolucion": "Me han devuelto mercancía",
        "peso": "El peso no era el apuntado",
        "humedad": "Ajuste por humedad",
        "calidad": "Ajuste por calidad",
    },
    "origenes_de_un_ajuste": {
        "cliente": "Me lo ha dicho el cliente",
        "bascula": "Lo dice la báscula",
        "laboratorio": "Lo dice un análisis",
        "acuerdo": "Lo hemos acordado",
        "otro": "Otra cosa",
    },
    # --- Las puertas a las otras tres pantallas de esta sección
    "facturas_abrir": "MIS FACTURAS DE LO VENDIDO",
    "cobros_abrir": "LO QUE ME HAN PAGADO",
    "facturar_esto": "FACTURAR ESTA ENTREGA",
    "cobrar_esto": "APUNTAR UN COBRO",
}

# --------------------------------------------------------------------------
# La factura emitida (T12, E6, 03/10/2026)
#
# **Lo que este vocabulario NO dice, y es lo más importante de este bloque.** En ninguna de estas
# frases aparece un impuesto, un número de serie oficial ni la palabra «legal»: esto es la **cuenta
# de gestión** del agricultor. El contrato lo pide así (§4, S12): «La emisión fiscal completa
# requiere especificación normativa propia antes de activarse como tal». Una pantalla que llamara
# «factura oficial» a esto le estaría diciendo al agricultor que puede presentarlo donde no puede, y
# ese es el peor fallo que puede tener esta entrega.
# --------------------------------------------------------------------------
FACTURA_EMITIDA: dict[str, str] = {
    "titulo": "Mis facturas de lo vendido",
    "explica": (
        "Aquí juntas una o varias entregas y ves de un vistazo lo que te deben. Es tu cuenta de "
        "gestión: no es un documento con validez oficial."
    ),
    "aviso_no_oficial": (
        "Esto no es un documento con validez oficial: es tu cuenta para saber qué has vendido y qué te "
        "deben. El papel que se presenta donde haga falta lo tienes que hacer aparte."
    ),
    "sin_nada": "Todavía no has hecho ninguna factura de lo que has vendido.",
    "nueva": "FACTURAR LO ENTREGADO",
    "nueva_titulo": "¿Qué entregas van en esta factura?",
    "nueva_explica": (
        "Marca las entregas que quieras juntar en la misma factura. Al juntarlas no se cuenta el "
        "dinero dos veces: cada entrega está en una sola factura."
    ),
    "elegir_una": "Marca al menos una entrega para facturar.",
    "seleccionar": "Marcar esta entrega",
    "numero": "¿Qué número le pones?",
    "numero_pista": "El tuyo, el que uses tú. Si lo dejas en blanco, se llama por su fecha.",
    "fecha": "¿De qué día es la factura?",
    "vencimiento": "¿Cuándo te la tienen que pagar?",
    "cliente": "¿A quién le facturas?",
    "cliente_ficha": "¿Es uno de tus contactos?",
    "cliente_ficha_pista": (
        "Si lo eliges, la factura queda enlazada con su ficha y sabes cuánto te debe esa casa."
    ),
    "sin_contacto": "Sin enlazar con ninguna ficha",
    "notas": "¿Quieres apuntar algo más?",
    "con_estas": "Estas entregas van dentro de esta factura:",
    "total": "Total de la factura",
    "cobrado": "Cobrado",
    "pendiente": "Pendiente",
    "sin_importe_aun": (
        "Estas entregas todavía no se pueden facturar porque no se sabe por cuánto. Ponles el importe "
        "y vuelve aquí: sin importe no hay nada que reclamar."
    ),
    "ya_facturada": (
        "La entrega del {fecha} de {producto} ya está dentro de la factura {numero}. Para cambiarla, "
        "quita primero esa factura."
    ),
    "ya_facturada_sin_numero": (
        "La entrega del {fecha} de {producto} ya está dentro de otra factura tuya. Para cambiarla, "
        "quita primero esa factura."
    ),
    "guardada_titulo": "Factura hecha",
    "guardada": "Ya está la factura. Ahora se puede apuntar lo que te vayan pagando.",
    "ya_estaba": (
        "Esa factura ya la habías hecho, así que no se ha hecho dos veces. Está en tu lista."
    ),
    "volver": "VOLVER A MIS FACTURAS",
    "ver_ficha": "VER ESTA FACTURA",
    # Cuántas facturas hay y cuántas están pendientes. Con las dos formas: «1 facturas» es lo primero que
    # hace desconfiar de un programa.
    "cuantas_pendientes": "Tienes {cuantas} facturas con algo por cobrar.",
    "cuantas_pendientes_una": "Tienes 1 factura con algo por cobrar.",
    "cuantas_cobradas": "Están todas cobradas.",
    # El motivo que se guarda al quitar una factura desde la pantalla que pregunta (ver `VENTA`).
    "motivo_al_quitar": "Me he equivocado al hacerla",
    # Cómo se llama una factura en una lista: «Factura F-2026-1 · Cooperativa Agrícola». Se compone en
    # el servidor y no en la pantalla (una frase compuesta dentro de un componente es una frase escrita
    # a mano). El número puede faltar y entonces queda la fecha: **no se le inventa un número**.
    "nombre": "Factura {numero}",
    "nombre_sin_numero": "Factura del {fecha}",
    "nombre_con_cliente": "Factura {numero} · {cliente}",
    "lineas": "Lo que va dentro",
    "linea_sin_entrega": "Una entrega que ya no está",
    "pagos": "Lo que te han pagado",
    "sin_pagos": "De esta factura todavía no te han pagado nada.",
    "apuntar_cobro": "APUNTAR UN COBRO",
    "cobrada_entera": "Esta factura está cobrada entera.",
    "diferencia": (
        "El importe de esta entrega ha cambiado desde que se facturó. La factura se queda como se "
        "hizo, y la diferencia está aquí dicha."
    ),
    "diferencia_de": "Ahora la entrega vale {ahora} y se facturó por {antes}.",
    "anular": "QUITAR ESTA FACTURA",
    "anular_titulo": "¿Seguro que quieres quitarla?",
    "anular_explica": (
        "La factura desaparece de tu lista y sus entregas quedan libres para volver a facturarlas. "
        "Lo que has cobrado no se toca: los cobros se quedan apuntados sin factura, a la espera."
    ),
    "anular_motivo": "Dinos por qué, para que quede apuntado.",
    "anulada": "Factura quitada. Sus entregas vuelven a estar sin facturar.",
    # **Y lo que enseña la ficha de una factura quitada** (revisión del T12): antes salía con `0,00 €` y
    # «0 entregas», porque solo se miraban sus líneas vivas. Lo que se emitió fue 121,00 € con una entrega
    # dentro, y sus líneas siguen en la base con su motivo: lo que hay que ver es lo que decía.
    "anulada_lo_que_decia": (
        "Esta factura está quitada, así que no cuenta en lo que te deben. Lo que ves debajo es lo que "
        "decía el día que se hizo."
    ),
    "no_esta": "Esa factura no está.",
}

# --------------------------------------------------------------------------
# Los cobros (T12, E6, 03/10/2026)
#
# El caso A06 del contrato vive en estas frases: «Factura 121 EUR, pago 40 EUR → pendiente 81; un
# segundo importe conciliado no crea una segunda factura». Por eso hay un texto para «de este cobro
# van 40 a la factura y quedan 81 por cobrar», y **ninguno** para «se ha creado una factura»: apuntar
# un cobro no crea ninguna factura, nunca.
# --------------------------------------------------------------------------
COBRO: dict[str, str] = {
    "titulo": "Lo que me han pagado",
    "explica": (
        "El dinero que ha entrado, aunque sea una parte de lo que te deben. Un pago puede ir contra "
        "una factura tuya o quedarse sin asignar hasta que sepas de cuál es."
    ),
    "sin_nada": "Todavía no has apuntado ningún cobro.",
    # Cuántos cobros hay. El singular importa: «1 cobros» se lee fatal.
    "cuantos": "{cuantas} cobros apuntados.",
    "cuantos_uno": "1 cobro apuntado.",
    # El motivo que se guarda al quitar un cobro desde la pantalla que pregunta (ver `VENTA`).
    "motivo_al_quitar": "Me he equivocado al apuntarlo",
    "nuevo": "APUNTAR UN COBRO",
    "nuevo_titulo": "¿Cuánto te han pagado?",
    "fecha": "¿Cuándo te lo han pagado?",
    "importe": "¿Cuánto ha entrado?",
    "importe_pista": "En euros. Si es una parte de lo que te deben, pon solo esa parte.",
    "cliente": "¿Quién te lo ha pagado?",
    "cliente_ficha": "¿Es uno de tus contactos?",
    "cliente_ficha_pista": (
        "Si lo eliges, el cobro queda enlazado con su ficha y sabes cuánto ha pagado esa casa."
    ),
    "sin_contacto": "Sin enlazar con ninguna ficha",
    "factura": "¿De qué factura es?",
    "sin_factura": "Todavía no sé de qué factura es",
    "sin_factura_pista": (
        "Si no lo sabes, se apunta igual y queda sin asignar. Cuando lo sepas, se dice desde su ficha."
    ),
    "forma": "¿Cómo ha entrado?",
    "referencia": "¿Qué referencia trae?",
    "referencia_pista": "La que sale en el banco, tal cual. Sirve para encontrarlo después.",
    "notas": "¿Quieres apuntar algo más?",
    "formas": {
        "transferencia": "Transferencia",
        "efectivo": "En efectivo",
        "cheque": "Con un cheque",
        "confirming": "Confirming",
        "otro": "Otra forma",
    },
    "guardado_titulo": "Cobro apuntado",
    "guardado": "Ya está apuntado lo que te han pagado.",
    # El reenvío del móvil: no se apunta dos veces y se dice con palabras.
    "ya_estaba": "Ese cobro ya lo habías apuntado, así que no se ha apuntado dos veces.",
    # Y la cuenta exacta de lo que pasa después de apuntarlo. Es el A06 en una frase.
    "va_a_la_factura": "De este cobro van {imputado} a la factura {numero}.",
    "queda_pendiente": "Le quedan {pendiente} por cobrar.",
    "queda_cobrada": "Con esto la factura {numero} queda cobrada entera.",
    "sobra_sin_asignar": (
        "Y sobran {sobrante}, que se quedan sin asignar hasta que sepas a qué van."
    ),
    "imputado": "Va a la factura",
    # **Los dos rótulos de la tabla del ordenador** (11/10/2026). Los demás ya estaban —`fecha`, `cuanto`,
    # `imputado`, `cliente`, `forma`—, así que la tabla **no inventa vocabulario**: dice lo mismo que la ficha.
    # Y `tabla_repartido` es el que se escribe cuando un cobro va a varias facturas y no se pueden listar sus
    # números: mejor «Varias facturas» que el texto de «no sé de qué factura es», que sería mentira.
    "tabla_acciones": "Acciones",
    "tabla_repartido": "Varias facturas",
    # **Un cobro que salda varias deudas** (CRM-01, 11/10/2026). Hace falta un rótulo propio porque el de
    # arriba dice «Va a **la** factura», en singular, y un ingreso repartido va a varias: sin esto, la ficha
    # enseñaba el nombre de una sola —o decía «sin factura», que es lo contrario de lo que ha hecho el
    # agricultor—.
    "repartido_entre": "Repartido entre estas facturas",
    # **Y el reparto, mientras se apunta** (CRM-01, 11/10/2026): un ingreso puede saldar varias deudas de
    # una vez (350 que saldan una factura de 100 y otra de 250). Se marcan las que salda y, si no se escribe
    # el importe, a cada una se le aplica lo que le queda por cobrar.
    "reparto_pista": (
        "Si este dinero salda varias facturas, márcalas aquí. Si no escribes el importe, a cada una se "
        "le aplica lo que le queda por cobrar."
    ),
    "reparto_lo_que_le_queda": "lo que le queda",
    "sin_asignar": "Sin asignar",
    "sin_asignar_titulo": "Cobros que todavía no sé de qué factura son",
    "sin_asignar_explica": (
        "Este dinero ha entrado y todavía no se sabe qué factura salda. No se pierde: cuando lo "
        "sepas, se le dice de cuál es."
    ),
    "conciliar": "DECIR DE QUÉ FACTURA ES",
    "conciliar_titulo": "¿Qué factura salda este cobro?",
    "conciliar_elegir": "Elige la factura",
    "conciliado": "Ya se sabe de qué factura es.",
    "deshacer": "QUITAR LA ASIGNACIÓN",
    "deshecho": "El cobro se queda otra vez sin asignar. El dinero sigue apuntado.",
    "anular": "QUITAR ESTE COBRO",
    "anular_titulo": "¿Seguro que quieres quitarlo?",
    "anular_explica": (
        "El cobro desaparece de tu lista y la factura vuelve a deber lo que debía. Si te has "
        "equivocado en la cantidad, es mejor corregirlo."
    ),
    "anular_motivo": "Dinos por qué, para que quede apuntado.",
    "anulado": "Cobro quitado. La factura vuelve a deber lo que debía.",
    "no_esta": "Ese cobro no está.",
    "no_hay_facturas": (
        "Todavía no tienes ninguna factura de lo que has vendido, así que este cobro se queda sin "
        "asignar. Para que vaya contra una factura, hazla primero desde «lo que he vendido»."
    ),
}

# Textos del volcado oficial a la Junta (IUWS).
#
# ATENCIÓN, Y ESTO ES UNA EXCEPCIÓN A PROPÓSITO: estos textos **NO entran en
# `textos_visibles()`, así que el test `test_sin_jerga` no los revisa**. El motivo es que no
# los lee un agricultor: los lee quien hace la integración con la Junta, una vez, y con el
# manual de FEGA delante. Ahí «interfaz», «credenciales», «descriptor» y «volcado» son los
# nombres oficiales, y cambiarlos por paráfrasis haría imposible seguir el manual. Traducir
# «descriptor v2.6.0» a «el papelito de los campos» no ayuda a nadie: confunde.
#
# La regla del cero jerga sigue valiendo para todo lo demás, y hay un test que comprueba
# justamente que estos textos están fuera de la lista y que se han quedado fuera queriendo.
IUWS: dict[str, str] = {
    "titulo": "Volcado oficial a la Junta (IUWS)",
    "explica": (
        "El Interfaz Único de Web Services es el canal oficial para volcar el cuaderno al "
        "CUE de la Junta. Está definido en el Anexo VI del documento técnico de SIEX."
    ),
    "para_quien": (
        "Esta pantalla no es para el agricultor: es para quien monta la integración. Por eso "
        "habla con los nombres del manual."
    ),
    "resumen_sin_conectar": (
        "Todavía no está conectado. Abajo está la lista de lo que falta, con quién tiene que "
        "darlo y a qué correo se pide."
    ),
    "resumen_conectado": (
        "Está todo lo que hace falta para conectar. Se puede probar el método de versión."
    ),
    "que_hay": "Lo que ya está hecho",
    "que_falta": "Lo que falta, y de quién depende",
    "nadie_bloqueado": "No falta nada de tu parte.",
    "endpoints": "Las direcciones de cada método",
    "formulario": "El formulario de solicitud de acceso de Castilla y León",
    "formulario_pista": (
        "Todos los campos son obligatorios. Se firma electrónicamente y se manda a los dos "
        "correos."
    ),
    "contactos": "A quién se le pide",
    "descargar_paquete": "DESCARGAR EL PAQUETE",
    "probar_conexion": "PROBAR LA CONEXIÓN",
    "ver_contenido": "VER QUÉ CAMPOS SE VUELCAN",
    "ver_mensajes": "VER LOS MENSAJES DEL INTERFAZ",
    "fuente_del_contenido": (
        "Documento técnico SIEX v3.11, Anexo II. El número de cada campo es el del documento."
    ),
    "no_configurado_para_probar": (
        "Esta instalación no está configurada para hablar con el interfaz, así que no se ha "
        "llamado. Abajo está lo que falta."
    ),
    "version_se_puede_probar_sin_nada": (
        "Esta prueba se puede hacer ya, sin tener nada configurado: el método de versión es el "
        "único que el interfaz deja abierto, sin certificado. Si contesta, hay camino hasta la "
        "Junta; lo demás seguirá haciendo falta, pero al menos se sabe que la red y la "
        "dirección están bien."
    ),
    "version_ok": "El interfaz ha contestado y dice con qué versión trabaja.",
    "version_no_contesta": (
        "El interfaz no ha contestado. Con esto ya se sabe algo útil: el problema está antes "
        "de las credenciales —la red, el cortafuegos o la dirección—, así que no tiene sentido "
        "buscar el fallo en el certificado."
    ),
    "conexion_en_la_configurada": (
        "Hay camino hasta la Junta: la dirección que tienes puesta contesta y trabaja con la "
        "versión {version}."
    ),
    "conexion_en_otra_direccion": (
        "Hay camino hasta la Junta, pero no por la dirección que tienes puesta: la que contesta "
        "es {base}, y trabaja con la versión {version}. Esa es la del Anexo X para esa "
        "comunidad; se puede poner en la configuración para no volver a probarlo."
    ),
    "conexion_404": (
        "La dirección ha contestado, pero ahí no está el método de versión (404). NO es un "
        "problema de credenciales. Comprueba "
        "que la dirección termina en /IUWS/api/version; la ruta anterior, sin /api/, ya no "
        "corresponde al Anexo VI vigente."
    ),
    "conexion_sin_respuesta": (
        "No se ha podido llegar a ninguna de las direcciones conocidas. Esto sí apunta a la red "
        "o al cortafuegos, y no a las credenciales ni al certificado."
    ),
    "entorno_de_integracion_no_publica": (
        "El entorno de integración del FEGA contesta en /IUWS/api/version. Si ves un 404, "
        "revisa si se está usando la ruta antigua sin /api/."
    ),
    "direcciones_conocidas": "Las direcciones del interfaz, por comunidad (Anexo X)",
    "probadas": "Direcciones probadas, y qué ha contestado cada una",
    "no_se_pudo_conectar": (
        "No se ha podido llegar al interfaz. Puede ser la red, el cortafuegos o que el "
        "servidor no esté disponible."
    ),
    "conexion_ok": "El interfaz ha contestado. Hay camino hasta él.",
    "conexion_rara": "El interfaz ha contestado, pero no con un OK. Mira la respuesta.",
    "comprobado_de_verdad": (
        "Se ha comprobado la ruta de versión 3.11.4 en producción y en el entorno de "
        "integración. Las llamadas autenticadas de esta versión siguen pendientes de probar "
        "con el alta y el certificado reales."
    ),
    "version_observada": "Versión que contestó el interfaz cuando se comprobó",
    "fecha_de_la_comprobacion": "Cuándo se comprobó",
    "falta_la_respuesta": "Pega lo que ha contestado el interfaz y te lo traduzco.",
    "el_paquete_no_es_el_volcado": (
        "Ojo con esto: este paquete NO es el fichero que se manda a la Junta. Es el sobre "
        "oficial con el contenido del cuaderno dentro, en el orden de campos del contenido "
        "mínimo. El descriptor oficial BdcSix-DS-DiseñoCUE.xlsx v3.11.4 y su esquema JSON "
        "ya están disponibles, pero "
        "todavía falta completar y verificar el mapeo campo por campo antes de poder enviarlo."
    ),
    "los_catalogos": (
        "Los campos marcados como «según catálogo» van vacíos a propósito: su valor es un "
        "código oficial (producto, unidad, justificación…) que se saca del servicio de "
        "catálogos de SIEX. Poner un número inventado sería peor que dejarlo vacío."
    ),
    "identificador_ajeno": (
        "Cada actividad lleva un identificador propio (IdAjena). Es lo que permite corregir "
        "una actividad ya cargada en vez de duplicarla, y no puede cambiar nunca."
    ),
    "sin_datos": "Todavía no hay nada que volcar este año.",
    "que_se_vuelca": "Qué se vuelca, bloque por bloque",
    "bloque": "Bloque",
    "campos": "Campos",
    "de_catalogo": "De catálogo",
    "obligatorios": "Obligatorios",
    "traducir_respuesta": "Traducir una respuesta del interfaz",
    "pegar_respuesta": "Pega aquí lo que ha contestado",
    "traducir": "TRADUCIRLO",
    "respuesta_pegada_vacia": "No has pegado nada.",
}

# Textos del conector con el SIGPAC. El SIGPAC es el catastro del campo: darle la referencia de
# un recinto y que la aplicación traiga sola la superficie, la pendiente, el uso y el dibujo.
SIGPAC: dict[str, str] = {
    "titulo": "Traer la parcela del SIGPAC",
    "explica": (
        "Si tienes la referencia del trozo (la del papel del SIGPAC), el programa trae solo la "
        "superficie, la pendiente, el uso y el dibujo. Así no hay que copiar ocho números por "
        "parcela."
    ),
    "referencia": "La referencia del trozo",
    "referencia_pista": "Siete números: provincia, municipio, agregado, zona, polígono, parcela y recinto",
    "referencia_ejemplo": "37-22-0-0-501-427-1",
    # La casilla de la referencia admite las tres formas que el agricultor tiene delante: lo
    # que copia del visor del SIGPAC (seis números), lo que copia del papel (siete) y la
    # referencia catastral del Catastro. Antes solo valía la de siete, y quien traía la del
    # visor se quedaba mirando un error sin saber qué le faltaba.
    "referencia_como_sea": "La referencia de tu trozo",
    "referencia_como_sea_pista": (
        "Pega lo que tengas: la del visor del SIGPAC (37:70:0:0:503:51), los siete números del "
        "papel (37-70-0-0-503-51-1) o la referencia catastral (37070A50300051000AQ)"
    ),
    "referencia_vacia": (
        "No has escrito nada. Copia la referencia de tu trozo: está en el papel del SIGPAC o en "
        "la web del Catastro, en «Consulta descriptiva y gráfica»."
    ),
    "referencia_no_entendida": (
        "Eso no lo entiendo. Sirve la referencia del visor del SIGPAC (37:70:0:0:503:51), los "
        "siete números con el recinto (37-70-0-0-503-51-1) o la referencia catastral del "
        "Catastro (37070A50300051000AQ). Has escrito {cuantos} números."
    ),
    "referencia_catastral": "La referencia catastral",
    "referencia_catastral_pista": (
        "Es la que empieza por los números de tu provincia y tu pueblo y tiene 20 letras y "
        "números. Trae dentro el polígono y la parcela, así que con ella ya se puede buscar."
    ),
    # Buscar los trozos (los recintos) de una parcela y dejárselos marcar: es lo que hacen las
    # aplicaciones oficiales del FEGA, y evita que el agricultor tenga que saberse el recinto.
    "buscar": "BUSCAR MIS TROZOS",
    "buscando": "Preguntando al SIGPAC…",
    "buscar_titulo": "Los trozos que hay en esa parcela",
    "buscar_explica": (
        "El SIGPAC ha encontrado estos trozos. Marca los que sean tuyos y los traigo con su "
        "superficie, su uso y su dibujo."
    ),
    "sin_recintos": (
        "En esa parcela el SIGPAC no tiene ningún trozo. Mira que el polígono y la parcela "
        "estén bien copiados; si tu trozo está en otra zona o en otro agregado, hay que "
        "ponerlo también."
    ),
    "recinto_numero": "Trozo {numero}",
    "traer_los_marcados": "TRAERME LOS MARCADOS",
    "marca_alguno": "Marca al menos un trozo para poder traerlo.",
    # La parcela se busca por sus dos números, que son los que el agricultor tiene en el papel y
    # los que enseña el visor. El recinto no se pregunta: sale de la lista que devuelve el SIGPAC.
    "poligono": "El polígono",
    "parcela": "El número de la parcela",
    "o_pega_la_referencia": (
        "Y si tienes la referencia a mano, pégala aquí y no hace falta rellenar nada más:"
    ),
    # Los dos caminos de esta pantalla, cada uno con su nombre (ronda 90, del diseño de Stitch): pegar la
    # referencia ahorra teclear seis datos, y estaba **abajo del todo**, después de los seis campos que
    # ahorra. Ahora va primero y se ve que es el camino corto.
    "camino_rapido": "El camino rápido",
    "o_por_partes": "O si lo prefieres: buscar por partes",
    "busca_antes": (
        "Pulsa BUSCAR MIS TROZOS y marca los que sean tuyos: todavía no has traído ninguno."
    ),
    # Sin el número de recinto no se puede pedir el trozo al SIGPAC: hay que buscar la parcela y
    # elegir de la lista. Se dice así, con lo que tiene que hacer, y no «faltan datos».
    "falta_el_recinto": (
        "A esa referencia le falta el número del trozo. Escribe la parcela sin el trozo y el "
        "programa te enseña los que hay para que elijas el tuyo."
    ),
    "busqueda_incompleta": (
        "Para buscar tus trozos hacen falta el pueblo y los números del polígono y de la "
        "parcela. Copia la referencia entera del SIGPAC, o elige tu pueblo y escribe los dos "
        "números."
    ),
    "traer": "TRAERME LOS DATOS",
    "comprobar": "COMPROBAR LA REFERENCIA",
    "alias": "¿Cómo llamas tú a esa tierra?",
    "sistema": "¿Es de secano o de regadío?",
    "municipio_parcela": "¿En qué pueblo está esta parcela?",
    "provincia_parcela": "¿En qué provincia está esta parcela?",
    "ubicacion_pista": (
        "Escribe los dos si los sabes. Así podemos avisarte si esta parcela está en una zona "
        "con límites de abono especiales. Los números del SIGPAC no bastan para saberlo."
    ),
    "trayendo": "Preguntando al SIGPAC…",
    "traido_titulo": "Parcela traída del SIGPAC",
    "traido": "Ya está. La superficie es la oficial, así que las cuentas del cuaderno salen bien.",
    "que_ha_venido": "Lo que ha venido solo:",
    "no_encontrado": (
        "El SIGPAC no tiene ningún recinto con esa referencia. Mira que los siete números estén "
        "bien copiados."
    ),
    "sin_permiso_red": (
        "No se ha podido preguntar al SIGPAC. Puede ser la cobertura o que el servicio no esté "
        "disponible: apunta la parcela a mano y tráela otro día."
    ),
    "a_mano": "APUNTARLA A MANO",
    "estas_no": "Estas no se han podido traer",
    "y_el_dibujo": "Y el dibujo del trozo, que sirve para el mapa",
    "superficie_oficial": "Superficie oficial",
    "uso": "Qué es",
    "pendiente": "Pendiente",
    "altitud": "Altitud",
    "los_nombres_no_vienen": (
        "El SIGPAC no trae los nombres del pueblo y la provincia. Si no los has indicado, "
        "todavía no sabemos si esta parcela está en una zona con límites de abono especiales."
    ),
    "que_hay_descargado": "Los datos oficiales del SIGPAC",
    "productos": "Productos del catálogo oficial",
    "usos": "Usos del suelo",
    "licencia": "De dónde salen estos datos",
    "actualizar": "Cómo actualizarlos",
    "sin_datos": (
        "Todavía no están descargados los datos oficiales del SIGPAC. La aplicación funciona "
        "igual: solo se pierden los nombres de los usos y el catálogo de productos."
    ),
}

# Textos del certificado digital. La idea es que el agricultor no teclee nada: ya tiene
# el certificado, se lo dio la FNMT, y es lo que usa para hablar con la administración.
CERTIFICADO: dict[str, str] = {
    "boton": "ENTRAR CON MI CERTIFICADO",
    "pista": "Sin teclear nada: usa el certificado que ya tienes",
    "no_configurado": (
        "En esta instalación todavía no se puede entrar con certificado. Entra con tu "
        "correo y tu clave."
    ),
    "no_dado_de_alta": (
        "Tu certificado es de {nif}, y en este cuaderno no hay ninguna finca con ese "
        "NIF. Entra con tu correo y tu clave, y luego vincula el certificado."
    ),
    "sin_nif": (
        "Tu certificado no trae un NIF que se entienda. Prueba con otro certificado."
    ),
    "no_valido": (
        "El NIF de tu certificado ({nif}) no tiene la letra bien. Comprueba que sea el "
        "certificado correcto."
    ),
    "vinculado": (
        "Certificado vinculado. La próxima vez puedes entrar solo con él, sin teclear nada."
    ),
    "vincular_titulo": "Vincular mi certificado",
    "vincular_explica": (
        "Si vinculas tu certificado, la próxima vez entras sin escribir el correo ni la "
        "clave."
    ),
    "no_coincide": (
        "El NIF de tu certificado es {nif} y el de esta finca es {de_la_finca}. Para "
        "vincularlo tienen que ser el mismo."
    ),
    "vinculado_ya": "Ya tienes el certificado vinculado: {nif}",
    "en_uso": "Con este certificado entras como {nombre}.",
}

# Textos de la firma del cuaderno. Nada de "criptográfico", "hash" ni "CAdES": el
# agricultor solo necesita saber quién lo firmó, cuándo, y si alguien lo ha tocado
# después.
FIRMA: dict[str, str] = {
    "titulo": "Firmar el cuaderno",
    "explica": (
        "Firmar es lo que hace que el cuaderno valga delante de la administración: "
        "queda claro quién lo ha hecho y que nadie lo ha cambiado después."
    ),
    "sin_firmar": "Todavía no has firmado el cuaderno de este año.",
    "firmado": "Firmado el {fecha} por {nombre}. Nadie lo ha cambiado desde entonces.",
    "cambiado": (
        "Ojo: este cuaderno se firmó el {fecha}, pero después se ha cambiado algo. "
        "La firma ya no vale para lo que hay ahora. Vuelve a firmarlo."
    ),
    "puede_firmar": "Puedes firmarlo ahora.",
    "no_puede_firmar": (
        "Para firmar hace falta que entres con tu certificado. Es lo que dice quién "
        "firma: sin él no se puede saber."
    ),
    "boton": "FIRMAR EL CUADERNO",
    "paso_1": "1. Descarga este fichero",
    "paso_2": "2. Fírmalo con AutoFirma",
    "paso_3": "3. Sube aquí la firma",
    "descargar": "DESCARGAR EL FICHERO",
    "subir": "SUBIR LA FIRMA",
    "fichero_listo": "Ya tienes el fichero. Ábrelo con AutoFirma y firma.",
    "firmado_ok": "Firmado. Ya puedes comprobar que el cuaderno no se ha cambiado.",
    "huella_no_cuadra": (
        "Ese fichero de firma no corresponde a lo que hay ahora en el cuaderno. Vuelve "
        "a descargarlo y fírmalo otra vez."
    ),
    "ya_firmado_igual": "Este cuaderno ya estaba firmado y no ha cambiado nada.",
    "instrucciones": (
        "AutoFirma es el programa que usa la administración para firmar. Si no lo "
        "tienes, se descarga gratis de la web del Gobierno."
    ),
    "un_apunte": "Firmar este apunte",
    "el_cuaderno": "Firmar el cuaderno del año",
    "sin_nada_que_firmar": "Todavía no hay nada apuntado este año, así que no hay nada que firmar.",
    "firma_guardada": "Firma guardada.",
    # Cuando el fichero de firma no es de este cuaderno. Se le dice qué hacer, no qué ha fallado
    # por dentro: el agricultor no puede arreglar un ASN.1, pero sí puede volver a firmar.
    "firma_no_es_de_este_cuaderno": (
        "Ese fichero de firma no es de este cuaderno: {motivo}. Vuelve a firmarlo."
    ),
    "firma_de_otro_agricultor": (
        "Ese fichero de firma lo ha firmado {firmante}, que no eres tú. Cada uno firma con su "
        "certificado: vuelve a firmarlo con el tuyo, el de {nif}."
    ),
    # Y cuando no se ha podido comprobar, que es distinto de que esté mal. Se guarda igual y se
    # dice, porque dejar sin firmar a alguien por no saber leer su certificado sería peor.
    "firma_sin_comprobar": (
        "La firma se ha guardado, pero no se ha podido comprobar que sea tuya. No es culpa tuya "
        "y el cuaderno vale igual: {motivo}."
    ),
    "firma_comprobada": "La firma está comprobada: es de este cuaderno y tuya.",
}

# --------------------------------------------------------------------------
# Corregir y borrar lo que uno ha introducido (ronda 91, y las tierras en la 92)
# --------------------------------------------------------------------------
#
# POR QUÉ ESTOS TEXTOS EXISTEN Y NO ESTABAN
#
# Hasta la ronda 90, un apunte mal metido solo se podía **anular** (y solo justo después de
# guardarlo, con el botón DESHACER): si el agricultor se daba cuenta tres días después, o si lo
# que estaba mal era una tierra o una máquina, no había forma de arreglarlo. David lo pidió así:
# «recuerda también dejar borrar las cosas que introduzca porque puede que me equivoque, o
# modificar también».
#
# Y estos textos son la mitad de la función: el agricultor tiene que saber **qué pasa** cuando
# pulsa CORREGIR y cuando pulsa BORRAR, porque no son lo mismo y las dos cosas tocan su cuaderno.
# Se dice en las tres pantallas donde se decide: en la ficha de cada apunte (los dos botones), en
# el resumen del asistente cuando se está corrigiendo, y en la pantalla que pregunta si de verdad
# se quiere borrar.
CORREGIR: dict[str, str] = {
    # ── Los dos botones, en cada apunte y en cada ficha ──
    "boton": "CORREGIR",
    "borrar": "BORRAR",
    # ── Mientras se corrige (el asistente, con lo que había ya puesto) ──
    #
    # El título y la pista son los del atajo de repetir: el asistente se abre con los datos del
    # apunte que se está corrigiendo, y sin decir esto parecería que se va a apuntar otra vez lo
    # mismo en vez de arreglar lo que ya está.
    "pregunta": "Corregir lo que apuntaste",
    "pista": (
        "Está puesto lo que apuntaste. Cambia lo que esté mal y guárdalo: queda escrito que lo "
        "has cambiado."
    ),
    "boton_guardar": "GUARDAR LOS CAMBIOS",
    # La etiqueta que sale en la barra del asistente **en cada paso** mientras se está corrigiendo
    # (diseño de Stitch de la ronda 92). El título de arriba dice que se está corrigiendo, pero en el
    # paso 6 de 9 ya no se lee: esta etiqueta va pegada a la barra de progreso, que es lo que se mira
    # para saber por dónde vas. Sin ella, el agricultor a mitad del formulario no sabe si está
    # arreglando lo que ya había o apuntando algo nuevo.
    "modificando": "CORRIGIENDO LO APUNTADO",
    # El botón de volver, mientras se corrige. Se dice **sin guardar** porque es lo único que el
    # agricultor no puede deducir: aquí volver atrás deja el apunte como estaba, y con la pantalla
    # llena de datos puestos es fácil creer que ya se ha guardado algo.
    "volver_sin_guardar": "VOLVER SIN GUARDAR",
    # Los dos finales posibles de una corrección.
    "hecho_titulo": "Corregido",
    "hecho": "Ya está cambiado. Lo que había antes queda guardado en el historial del cuaderno.",
    # ── La pantalla que pregunta si de verdad se quiere borrar ──
    #
    # Es una pregunta en grande (`.pregunta`), no un título: lo que viene después de pulsar BORRAR
    # no se puede deshacer, así que la pantalla tiene que leerse como una pregunta y no como un
    # aviso más.
    "pregunta_borrar": "¿Seguro que quieres borrarlo?",
    "borrar_pista": "De tu cuaderno desaparece del todo.",
    # El rótulo de la caja que enseña lo que se va a borrar (diseño de Stitch de la ronda 92): una
    # caja de datos sin título es una caja de datos, y el agricultor tiene que saber de un vistazo
    # que lo que está leyendo es **lo que va a desaparecer**, no lo que hay apuntado.
    "lo_que_desaparece": "Lo que va a desaparecer de tu cuaderno",
    # Lo que de verdad hay que decir, y por qué: borrar y corregir se parecen y no son lo mismo.
    # Un apunte que se borra por haberse equivocado al escribirlo deja el cuaderno con un hueco;
    # corregirlo lo deja bien. El agricultor es el único que sabe cuál de las dos cosas le pasa.
    "borrar_mejor_corregir": (
        "Si solo te has equivocado al escribirlo, mejor CORREGIRLO: así el apunte queda bien en "
        "vez de desaparecer."
    ),
    # Y lo mismo, cuando lo que se borra **no es un apunte** sino una tierra o un grupo: aquí no hay
    # nada que «quede bien», así que se dice lo que de verdad pasa al borrarlo.
    "borrar_tierra_pista": (
        "Si te has equivocado al darla de alta, mejor CORREGIRLA: así no pierdes los apuntes que "
        "ya tenga."
    ),
    "borrar_grupo_pista": (
        "Un grupo es solo una forma de apuntar de una vez: sus tierras no se tocan y siguen en tu "
        "cuaderno."
    ),
    # Lo que queda por dentro cuando se borra. Se dice porque es la verdad y porque es lo que
    # distingue esto de «borrar sin más»: el programa no se olvida de lo que había.
    "borrar_queda_rastro": (
        "El programa guarda por dentro qué había apuntado y qué día lo borraste, por si algún día "
        "hay que explicarlo."
    ),
    # El rótulo del bloque que explica lo de arriba. Es propio y no el genérico («Dónde se aprovecha
    # esto:») porque aquí no se está aprovechando nada: se está diciendo qué queda guardado.
    "rastro_titulo": "Qué queda guardado",
    # ── El año del cuaderno (la campaña), en la pantalla que los enseña ──
    #
    # Al agricultor **no se le habla de «campañas»**: eso es la palabra del programa. Él dice «el año».
    # Y el rótulo de la ficha es «Año del cuaderno» porque es exactamente lo que es: el año al que va
    # todo lo que apunta.
    "que_es_campana": "Año del cuaderno",
    # ── Firmado: se dice y se da la salida ──
    #
    # Un apunte firmado no se puede borrar (la firma es la prueba de lo que había). El aviso lleva
    # su botón, como todos los avisos de este programa: un aviso sin salida deja al agricultor
    # mirando una frase.
    "esta_firmado": (
        "Este apunte está firmado, así que no se puede borrar. Se puede ANULAR: queda tachado, "
        "con el motivo, y la firma sigue cuadrando."
    ),
    "anular_este": "ANULARLO",
    # Y qué significa anular, que no es lo mismo que borrar y no lo sabe todo el mundo (diseño de Stitch
    # de la ronda 92). Va en la misma pantalla, debajo del aviso de que está firmado: el agricultor tiene
    # que entender qué va a quedar en su cuaderno **antes** de pulsar.
    "que_es_anular": (
        "Anular no borra el apunte: se queda tachado, con el día y el motivo. Así, si viene una "
        "inspección, se ve que no escondes nada."
    ),
    "anulado_ok": "Anulado. Queda tachado en el cuaderno, con el motivo escrito.",
    # Los dos botones de la pantalla que pregunta si de verdad se quiere borrar. **El de borrar no es
    # el único**: al lado está el que arregla el cuaderno sin dejar hueco, y va con su palabra
    # («MEJOR…») porque es lo que de verdad quiere hacer la mayoría de las veces que alguien se
    # equivoca: cambiar el dato, no borrar el apunte.
    "boton_borrar_si": "SÍ, BORRARLO",
    "boton_mejor_corregirlo": "MEJOR CORREGIRLO",
    # Lo que se dice después de borrar. El «por dentro» del texto de abajo no es un adorno: es lo que
    # distingue esto de un borrado sin más, y el agricultor tiene derecho a saberlo antes de pulsar.
    # Se deja claro que **lo que había desaparece de su cuaderno**: eso es lo que ha pedido.
    "borrado_titulo": "Borrado",
    "borrado_ok": "Ese apunte ya no está en tu cuaderno.",
    "volver_al_cuaderno": "VOLVER AL CUADERNO",
    # ── Los rótulos de la lista de lo apuntado ──
    #
    # «Lo que tengo apuntado este año» son cuatro clases de apunte (producto, abono, trabajo y
    # cosecha) en la misma lista, y cada tarjeta tiene que decir de qué clase es: si no, un abono y
    # una labor se leen igual.
    "que_es_producto": "Producto",
    "que_es_abono": "Abono",
    "que_es_trabajo": "Trabajo",
    "que_es_cosecha": "Cosecha",
    # ── Y lo que no es un apunte del cuaderno (ronda 92: las tierras y los grupos) ──
    #
    # Las mismas palabras y los mismos botones, para lo que el agricultor dio de alta él. Cada cosa
    # dice **cómo se llama** (sale como primer renglón de la ficha que se va a borrar), a dónde se
    # vuelve al terminar y qué se dice cuando ya no está.
    "que_es_tierra": "Tierra",
    "que_es_grupo": "Grupo de tierras",
    # Y las demás cosas, cada una con su nombre (ronda 93). Es el primer renglón de la ficha que se
    # enseña al corregir o al borrar: sin él, la caja de datos empieza por un dato y no se sabe de qué.
    "que_es_analisis": "Análisis",
    "que_es_venta": "Venta",
    "que_es_plan": "Plan de abono",
    "que_es_aplicador": "Quién aplica",
    "que_es_asesor": "Asesor",
    "que_es_equipo": "Máquina",
    "que_es_instalacion": "Nave o almacén",
    "que_es_documento": "Papel",
    "que_es_factura": "Factura",
    "volver_a_las_tierras": "VOLVER A MIS TIERRAS",
    "volver_a_los_grupos": "VOLVER A LOS GRUPOS",
    # Y a los años del cuaderno (ronda 93). El botón de volver de un año corregido o borrado dice adónde
    # va: «VOLVER» a secas, en una pantalla a la que se llega desde «mis datos», no dice nada.
    "volver_a_los_anos": "VOLVER A LOS AÑOS",
    "borrado_ok_tierra": "Esa tierra ya no está en tu cuaderno.",
    "borrado_ok_grupo": "Ese grupo ya no está: sus tierras siguen en tu cuaderno.",
    # El que se usa para todo lo demás que se da de alta (un producto, una máquina, un análisis, una
    # venta, un papel…). Es genérico **a propósito**: son cosas distintas y una frase que valga para
    # todas tiene que decir lo único que comparten, que es que ya no están. Decir «ese producto» en un
    # mensaje que también sale al borrar una máquina sería mentir.
    "borrado_ok_cosa": "Ya no está en tu cuaderno.",
}

# Textos de estado de la interfaz
INTERFAZ: dict[str, str] = {
    "apuntado_ok": "Apuntado. Si te has equivocado, pulsa DESHACER.",
    # La explicación del botón de deshacer (ronda 90, del diseño de Stitch de la pantalla de
    # confirmación). Sin ella, el único botón que puede borrar un apunte es también el que menos se sabe
    # para qué está: con esto se dice que es para cuando alguien se ha confundido, y de qué.
    "deshacer_pista": "Por si te has confundido de tierra, producto o dosis.",
    "pendientes": (
        "{cuantos} cosas apuntadas esperando a que haya cobertura. Se mandan solas."
    ),
    # Con un solo apunte sin mandar, «1 cosas apuntadas» se lee fatal (ronda 84). Y este aviso sale en la
    # cabecera justo cuando el agricultor está en el campo sin cobertura, que es cuando más lo mira.
    "pendientes_uno": (
        "1 apunte esperando a que haya cobertura. Se manda solo."
    ),
    "mandando": "Mandando lo que tenías apuntado…",
    "sin_permiso": "Este navegador no deja guardar en el móvil. Apunta con cobertura.",
    "no_hay_productos": (
        "Todavía no has apuntado ningún producto comprado. Añádelo primero y luego "
        "podrás decir dónde lo has echado."
    ),
    "no_hay_parcelas": (
        "Todavía no tienes parcelas. Añade la primera y ya podrás apuntar lo que haces."
    ),
    "no_hay_abonos": (
        "Todavía no has apuntado ningún abono. Añádelo primero y luego podrás decir "
        "cuánto has echado."
    ),
    "no_hay_instalaciones": (
        "Todavía no tienes ninguna nave ni almacén apuntado. Añádelo primero y ya "
        "podrás decir dónde lo has echado."
    ),
    "cargando": "Un momento…",
    "no_se_pudo": (
        "No se ha podido mandar. No te preocupes: sigue guardado en el móvil."
    ),
    "pie": (
        "Si algo no lo entiendes, déjalo en blanco y pregunta. Un cuaderno a medias se "
        "arregla; uno con datos inventados, no."
    ),
    "confirmar_salida": "¿Seguro que quieres salir?",
}

# Textos de la pantalla que enseña lo que se ha entendido de un dictado.
# Es la idea de "Generative UI": la respuesta no es una frase de chat, es una tarjeta
# con el formulario a medio rellenar y el botón de apuntarlo.
BORRADOR: dict[str, str] = {
    "titulo": "Lo que he entendido",
    "intro": "Mira si está bien. Completa lo que falte y apúntalo.",
    "falta_intro": "Para poder apuntarlo me falta esto:",
    "sin_sitio": "Esto lo he oído pero no sé dónde ponerlo. Dímelo tú:",
    "nada_entendido": (
        "No he entendido nada de lo que has dicho. Prueba a decírmelo de otra forma, "
        "o rellénalo a mano: se tarda un minuto."
    ),
    "fuente_reglas": "Lo he entendido yo solo, sin ayuda de nadie.",
    "fuente_modelo": "Lo ha entendido el ayudante.",
}

# Rótulos cortos que aparecen en las listas y en el resumen
ROTULOS: dict[str, str] = {
    "unidad_hectareas": "hectáreas",
    "unidad_kilos_ha": "kilos por hectárea",
    "unidad_kilos": "Kilos",
    "etiqueta_numero": "etiqueta",
    "dias_espera_corto": "días de espera",
    "itv_hasta": "ITV hasta",
    "hectareas_corto": "ha",
    # La composición de un abono, cuando no consta (A6, 03/10/2026). Se dice con palabras porque el hueco no
    # es un cero: «0-0-0» afirmaría que ese abono no lleva nitrógeno, fósforo ni potasio, y eso solo lo sabe
    # quien lea la etiqueta. Es el mismo criterio que la raya del almacén («—»), pero aquí se puede explicar.
    "composicion_no_se": "no consta la composición",
    # La unidad corta de peso, para las líneas donde el número va delante («2 ventas apuntadas · 44.000
    # kg»). La larga («Kilos») es un rótulo de campo, y con mayúscula en medio de una frase no se lee.
    "kilos_corto": "kg",
    "parcelas_corto": "parcelas",
    # ── Las tarjetas del asistente (rediseño de la ronda 77) ────────────────────────────────
    # «ELEGIDA» va en la tarjeta de la tierra que el agricultor acaba de tocar. Se dice con una
    # palabra además del color y del círculo marcado: la regla del proyecto es que el color no
    # informe solo, y quien no distinga el verde tiene que poder leer que esa es la elegida.
    "elegida": "ELEGIDA",
    # El paso por el que va el asistente, en palabras. Los tramos de la barra ya lo enseñan, pero
    # un número escrito no se puede confundir con una barra a medias.
    "paso": "Paso {numero} de {total}",
    # Los dos avisos que puede llevar una tierra en su tarjeta. Son datos que ya se saben (vienen
    # del SIGPAC y del catálogo oficial), no suposiciones: por eso se pueden enseñar.
    "tierra_en_nitratos": "Está en zona de nitratos",
    "tierra_masa_agua": "Tiene una masa de agua cerca",
    "producto": "Producto",
    "abono": "Abono",
    "hectareas": "Hectáreas",
    "kilos_por_hectarea": "Kilos por hectárea",
    "por_hectarea": "Por hectárea",
    "por_que": "Por qué",
    "recogido": "Recogido",
    "trabajo": "El trabajo",
    "apuntes_de_producto": "apuntes de producto",
    # El singular y el plural, porque «1 apuntes» es lo primero que hace desconfiar de un programa (la
    # misma regla que la prueba `TestSingularYPlural`). El título del bloque de «mi cuaderno» lleva el
    # número delante, así que con un solo apunte tiene que decir «1 apunte de producto».
    "apunte_de_producto": "apunte de producto",
    "ya_cosechado": "Hasta aquí no puedes coger la cosecha:",
    # De los análisis
    "analisis": "Análisis",
    "sin_unidad": "sin unidad",
    "informe": "Boletín",
    "material": "Qué se analizó",
    "muestra": "Muestra",
    "laboratorio": "Laboratorio",
    "resultado": "Resultado",
    "numeros": "Números del boletín",
    # Del asesor
    "ropo_corto": "Nº de asesor",
}



PALABRAS_PROHIBIDAS: tuple[str, ...] = (
    "error",
    "validación",
    "validacion",
    "cumplimentar",
    "epígrafe",
    "epigrafe",
    "dosificación",
    "dosificacion",
    "trazabilidad",
    "interfaz",
    "sincronizar",
    "sesión",
    "sesion",
    "campo obligatorio",
    "operación cultural",
    "operacion cultural",
    "fitosanitario",
    "fitosanitarios",
    "dgc",
    "uhc",
)


def _recoger(valor) -> list[str]:
    """Saca todos los textos de una estructura anidada, sean diccionarios o listas."""
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, dict):
        resultado: list[str] = []
        for contenido in valor.values():
            resultado.extend(_recoger(contenido))
        return resultado
    if isinstance(valor, (list, tuple, set)):
        resultado = []
        for contenido in valor:
            resultado.extend(_recoger(contenido))
        return resultado
    return []


# Textos de la documentación anexa: los papeles que acompañan al cuaderno.
#
# El documento de la Junta habla de «documentación complementaria al Cuaderno». Aquí se dice «los
# papeles», que es como lo llama un agricultor: el contrato, la factura, el resguardo de los
# envases. La regla 3.1 vale igual que en todo lo demás: nada de «anexo», «repositorio» ni
# «documentación complementaria» en lo que él lee.
DOCUMENTOS: dict[str, str] = {
    "titulo": "Los papeles",
    # **La puerta de la bandeja** (T08, S10, 06/10/2026): el botón que entra desde «los papeles» a lo
    # que llega y hay que revisar. Se llama como la pantalla a la que lleva, que es la regla de la
    # casa con los botones que abren un sitio.
    "bandeja": "LA BANDEJA: LO QUE HAY QUE REVISAR",
    "explica": (
        "Aquí guardas los papeles que acompañan al cuaderno: el contrato de la tierra, las "
        "facturas de lo que compras, los resguardos de los envases. El cuaderno dice lo que "
        "hiciste; estos papeles son los que lo demuestran."
    ),
    "para_que": (
        "Si un día viene una inspección, esto es lo que te van a pedir junto con el cuaderno. "
        "Y si se te pierde el papel de verdad, aquí queda al menos apuntado."
    ),
    "cuantos": "Tienes {cuantos} papeles guardados.",
    # Con un solo papel, «Tienes 1 papeles guardados» (ronda 84).
    "cuantos_uno": "Tienes 1 papel guardado.",
    "sin_papeles": (
        "Todavía no has guardado ningún papel. No hace falta que lo tengas todo: empieza por el "
        "contrato de la tierra, que es el que más se pide."
    ),
    "nuevo": "GUARDAR UN PAPEL",
    "carpeta": "¿En qué carpeta lo guardas?",
    "carpeta_pista": "Como las tienes tú en casa. Si escribes una nueva, se crea.",
    "carpeta_sugerida": "Las que suele haber",
    "titulo_del_papel": "¿Qué es?",
    "titulo_pista": "Por ejemplo: «Contrato de la finca del río» o «Factura del abono de mayo»",
    "que_es": "¿De qué es?",
    "fecha_del_papel": "¿De qué fecha es?",
    "fecha_pista": "La del papel, no la de hoy. Si no lo sabes, déjalo en blanco.",
    "quien": "¿De quién es o quién te lo dio?",
    "quien_pista": "El proveedor, el dueño de la tierra, la cooperativa",
    "notas": "¿Quieres apuntar algo más?",
    "el_fichero": "El papel en sí (una foto o el PDF)",
    # Lo que hay que hacer en esta pantalla (ronda 90, del diseño de Stitch de «guardar un papel»): el nombre
    # es lo único que hace falta de verdad, y las carpetas que ya tiene se tocan en vez de escribirlas (en el
    # móvil, escribir con guantes es lo que más cuesta).
    "hace_falta": "Hace falta",
    "toca_una": "Toca una de las que ya tienes, o escribe una nueva:",
    "fichero_pista": (
        "Si tienes el papel a mano, hazle una foto o elige el fichero: queda guardado con él. Si no lo "
        "tienes, apúntalo igual y súbelo cuando llegues a casa."
    ),
    "subir_fichero": "SUBIR EL PAPEL",
    "fichero_subido": "Papel guardado.",
    "descargar": "VER EL PAPEL",
    "sin_fichero": (
        "Este papel está apuntado pero no has subido el fichero. Apúntalo igual: así no se te "
        "olvida que existe."
    ),
    "tiene_fichero": "Con el papel subido",
    "no_tiene_fichero": "Solo apuntado, sin el papel",
    "anular": "QUITARLO DE LA LISTA",
    "motivo_anulacion": "¿Por qué lo quitas?",
    "anulado": "Quitado de la lista el {fecha}: {motivo}",
    "falta_el_motivo": "Dime por qué lo quitas, para que quede apuntado.",
    "el_titulo": "Ponle un nombre al papel, para poder encontrarlo luego.",
    "carpetas": "Tus carpetas",
    "sin_carpeta": "Sin carpeta",
    "listado": "LISTA DE PAPELES, PARA COPIAR",
    "listado_pista": "Sale en texto, para pegarlo en un correo o imprimirlo.",
    "sin_archivar": (
        "Estos papeles no has dicho de qué son. Míralos cuando puedas: un papel que no se sabe "
        "qué es, no sirve de nada en una inspección."
    ),
}


# La cesta de la compra: el libro de movimientos de los productos fitosanitarios.
#
# El nombre lo pone el agricultor: «el almacén». La app de la Junta lo llama «Cesta de la compra»
# y «Situación Cesta»; aquí se dice «lo que tengo en el almacén» porque es donde está de verdad.
CESTA: dict[str, str] = {
    "titulo": "Lo que tengo en el almacén",
    "explica": (
        "Aquí ves cuánto producto compraste, cuánto llevas echado y cuánto te queda. Sirve para "
        "dos cosas: saber si te llega para tratar la parcela, y tener el libro de entradas y "
        "salidas que se mira en una inspección."
    ),
    "vacia": (
        "Todavía no has apuntado ningún producto. Cuando apuntes uno, aquí verás lo que te queda."
    ),
    "cuantos": "Tienes {cuantos} productos apuntados.",
    # Con uno solo, «Tienes 1 productos apuntados» (ronda 84).
    "cuantos_uno": "Tienes 1 producto apuntado.",
    "comprado": "Compraste",
    "gastado": "Llevas echado",
    "queda": "Te queda",
    # ── Los dos números, cada uno con su nombre (T21, 06/10/2026) ─────────────
    #
    # **Por qué hay dos filas y no una.** Hasta hoy esta pantalla contestaba «te queda» con *lo comprado
    # por factura menos lo echado*, y el libro del almacén contestaba lo mismo con *lo que ha entrado por
    # albarán menos lo que ha salido*: dos números distintos del mismo producto, en dos pantallas, y el
    # agricultor sin saber cuál creerse. Desde el T21 manda **el del almacén** (que es lo que hay de
    # verdad dentro), y la cuenta de los papeles se sigue enseñando **al lado y con su nombre**, porque
    # no es lo mismo: lo comprado no está dentro hasta que llega el albarán.
    #
    # **No se suman ni se mezclan**: son dos hechos distintos y cada uno va con su etiqueta.
    "queda_en_el_almacen": "Te queda (lo que hay en el almacén)",
    "queda_en_el_almacen_pista": (
        "Es lo que hay de verdad: lo que ha entrado por albarán menos lo que ha salido del almacén."
    ),
    "queda_segun_los_papeles": "Según los papeles (lo comprado menos lo echado)",
    "no_se_sabe_lo_que_hay": "Lo que hay en el almacén todavía no se puede decir",
    "apuntes": "En {cuantos} apuntes",
    "sin_cantidad": "Sin saber cuánto compraste",
    "no_se_puede_comparar": "No se puede comparar",
    # El estado de cada producto, en una etiqueta corta (ronda 90, del diseño de «el almacén»). Son tres
    # estados y tres frases: las cuentas están bien, hay algo que mirar, o falta el dato de la compra (esa
    # tercera ya existía: `sin_cantidad`). El chip dice **si hay algo que mirar**; el porqué lo dice el
    # motivo, justo debajo. Sin el chip, para saber si un producto está bien había que leer los tres
    # números de cada tarjeta y hacer la cuenta mentalmente.
    "cuadra": "Las cuentas cuadran",
    "mirar": "Míralo",
    "de_que_es": "De qué es",
    "cuando": "Cuándo",
    "donde_lo_compraste": "Dónde lo compraste",
    # **De dónde sale el número de lo comprado** (30/09/2026). El servidor lo manda desde siempre
    # (`comprado_de_donde`: «facturas» o «ficha»), pero ninguna pantalla lo enseñaba, así que el agricultor
    # veía un número sin poder comprobarlo. Ahora va en el panel de al lado de la tabla.
    "de_las_facturas": "Sale de tus facturas",
    "de_la_ficha": "Lo escribiste en la ficha del producto",
    "para_que_sirve": (
        "Si un día te preguntan cuánto producto has comprado y cuánto has echado, esto es la "
        "respuesta. Y si te queda poco, lo ves antes de quedarte sin él en mitad del tratamiento."
    ),
    "como_apuntarlo": (
        "Cuánto compraste se apunta en la ficha del producto. Sin ese dato, aquí no salen las "
        "cuentas: no se inventan."
    ),
    "ir_a_productos": "MIS PRODUCTOS",
}


# El libro del almacén (T09, 03/10/2026): lo que entró por albarán, en qué lote, y de qué lote salió
# lo que se ha echado.
#
# **Por qué hay dos pantallas de almacén y no una.** «Lo que tengo en el almacén» (los textos de
# arriba, `CESTA`) contesta a «¿me queda producto?» con lo comprado y lo echado, y lleva ahí desde
# el principio: **no se ha tocado**, porque es la que el agricultor usa todos los días. Este libro
# contesta a otra cosa, que es lo que pide una inspección: de qué lote salió cada cosa y qué llegó
# de verdad con el albarán. Se dicen las dos, y la pantalla del libro avisa de que una factura sin
# albarán no mete mercancía, para que un almacén vacío no parezca producto perdido.
ALMACEN: dict[str, str] = {
    "titulo": "El libro del almacén",
    "explica": (
        "Aquí se apunta lo que entra y lo que sale, envase por envase: el día que llegó el albarán, "
        "de qué lote era y hasta cuándo vale, y de qué lote salió lo que has echado. Sirve para lo "
        "que no se puede saber de otra forma: si un día el fabricante avisa de un lote, aquí se ve "
        "dónde se fue."
    ),
    "para_que": (
        "En una inspección, el cuaderno dice lo que hiciste y el lote dice con qué. Y para ti sirve "
        "para no comprar de más: cada envase lleva su cuenta, así que sabes lo que te queda antes de "
        "bajar al pueblo."
    ),
    "como_funciona": (
        "Lo que mete mercancía en el almacén es el albarán, no la factura. La factura dice cuánto "
        "costó y de quién era; la mercancía entra el día que llega el camión. Por eso, si apuntas "
        "una factura y todavía no has apuntado su albarán, aquí no sale existencia: no es que se "
        "haya perdido, es que aún no ha entrado."
    ),
    # --- las cuatro clases de cosa que se guarda (las pestañas del almacén) ---
    # Los nombres son los del contrato (§4: «productos de tratamiento, abonos, semillas y otros
    # insumos») y no los de la ficha de dentro: al agricultor no se le dice «fitosanitario», que es
    # una palabra de mostrador y la primera de la lista de las prohibidas.
    "categoria_fitosanitario": "Productos de tratamiento",
    "categoria_abono": "Abonos",
    "categoria_semilla": "Semillas",
    "categoria_otros": "Otras cosas",
    # --- las cuatro cosas que pueden pasar ---
    "entrada": "Entró",
    "salida": "Salió",
    "merma": "Se perdió",
    "ajuste": "Conteo distinto",
    "entradas": "Entró",
    "salidas": "Salió",
    "mermas": "Se perdió",
    "ajustes": "Diferencia del conteo",
    "queda": "Queda",
    "no_se_sabe_lo_que_queda": "No se puede saber lo que queda",
    "saldo_negativo": (
        "Sale más de lo que había apuntado. Míralo: falta apuntar una entrada o hay una salida de más."
    ),
    # --- el lote ---
    "lote": "Lote",
    "sin_numero_de_lote": "Sin número de lote",
    "sin_numero_de_lote_pista": (
        "El envase no lo trae o no lo has mirado. Apúntalo cuando lo mires: es lo que permite "
        "seguirle la pista si el fabricante avisa."
    ),
    "caducidad": "Caduca",
    "sin_caducidad": "No se sabe cuándo caduca",
    "sin_caducidad_pista": "No es que no caduque: es que no lo has mirado. Míralo en el envase.",
    "caducado": "Caducado",
    "caducado_pista": (
        "Este envase está pasado de fecha. Míralo antes de usarlo: no se puede dar por bueno solo "
        "porque esté en el almacén."
    ),
    "en_plazo": "En fecha",
    "envase": "Envase",
    "donde_esta": "Dónde está",
    # --- el albarán ---
    "recepciones": "Lo que ha llegado",
    "recepciones_vacio": (
        "Todavía no has apuntado ningún albarán. Cuando llegue el próximo pedido, apúntalo aquí: es "
        "lo que mete la mercancía en el almacén."
    ),
    "sin_articulos": (
        "Todavía no hay nada apuntado en el almacén. Cuando apuntes el primer albarán, aquí verás lo "
        "que queda de cada envase."
    ),
    "cuantos_articulos": "En el almacén llevas {cuantos} cosas apuntadas.",
    "cuantos_articulos_uno": "En el almacén llevas 1 cosa apuntada.",
    "cuantos_albaranes": "Tienes {cuantos} albaranes apuntados.",
    "cuantos_albaranes_uno": "Tienes 1 albarán apuntado.",
    "nuevo_albaran": "APUNTAR UN ALBARÁN",
    "numero_albaran": "¿Qué número tiene el albarán?",
    "numero_albaran_pista": "Lo que ponga en el papel. Si no lleva número, déjalo en blanco y dilo.",
    "proveedor": "¿De quién es?",
    "fecha_albaran": "¿De qué día es?",
    "lineas": "Lo que venía",
    "ya_estaba": "Ese albarán ya estaba apuntado",
    "ya_estaba_explica": (
        "No se ha vuelto a apuntar, así que no se ha contado dos veces. Si el que había estaba mal, "
        "anúlalo y apunta este."
    ),
    "no_se_pudo_comprobar": (
        "Como este albarán no lleva número (o no dice de quién es), no se ha podido comprobar si ya "
        "estaba apuntado. Míralo en la lista y anula el que sobre."
    ),
    "la_factura_llego_despues": "La factura llegó después",
    "enganchar_factura": "DECIR DE QUÉ FACTURA ES",
    "factura_enganchada": (
        "Esta factura ya está enganchada a su albarán. La mercancía no se cuenta otra vez: entró una "
        "vez, el día que llegó."
    ),
    "sin_factura": "Sin factura apuntada",
    "compras_sin_albaran": (
        "De esto tienes compras apuntadas en facturas pero no ha entrado nada al almacén: apunta el "
        "albarán cuando llegue y aquí saldrá la existencia."
    ),
    "compras_sin_albaran_una": (
        "De esto tienes 1 compra apuntada en una factura pero no ha entrado nada al almacén: apunta "
        "el albarán cuando llegue y aquí saldrá la existencia."
    ),
    # --- los botones ---
    "nueva_entrada": "APUNTAR QUE HA ENTRADO",
    "nueva_merma": "APUNTAR QUE SE HA PERDIDO",
    "nuevo_ajuste": "APUNTAR LO QUE HE CONTADO",
    "nueva_salida": "SACAR DE UN LOTE",
    "anular": "ANULAR",
    "motivo": "¿Por qué?",
    "motivo_pista": "En dos palabras: se rompió, se contó distinto, llegó sin cantidad…",
    "cantidad": "¿Cuánto?",
    "cantidad_pista": "El total, no la dosis por hectárea. Y en qué se mide: litros, kilos, unidades.",
    "de_que_apunte_sale": "¿De qué apunte sale?",
}


# ---------------------------------------------------------------------------
# El libro del almacén EN LA PANTALLA (T09, 03/10/2026)
# ---------------------------------------------------------------------------
#
# El servidor del almacén ya estaba hecho cuando se escribió esto —el albarán, los lotes y el libro
# de movimientos, en `routers/almacen_api.py`— y sus palabras viven en `ALMACEN`, aquí arriba: los
# mensajes que el servidor contesta cuando algo no cuadra y las etiquetas que vienen dentro de sus
# respuestas. Lo que faltaba era **la pantalla**, y estos son los textos que lee el agricultor en
# ella. Los que ya existían **no se copian**: se apunta a ellos (`ALMACEN["lote"]` y compañía), para
# que un día no digan dos cosas distintas.
#
# **Por qué van dentro de `CESTA` y no en un bloque propio**, que es lo que pediría el sentido común:
# porque `/api/interfaz` sirve los bloques **por su nombre, uno a uno**, y `textos.ALMACEN` no está
# en esa lista (sirve `cesta`, no `almacen`). Un bloque nuevo aquí **no llegaría a la pantalla**: el
# componente pediría `t("almacen.…")`, el texto saldría en blanco y el test
# `test_que_no_falte_ningun_texto` lo diría —que es justo lo bueno que tiene ese test—. Así que las
# palabras de las dos pantallas del almacén viven en el bloque del almacén, que es el que se sirve y
# el que el móvil se guarda para funcionar sin cobertura. **El arreglo limpio es una línea en
# `routers/interfaz.py`** (`"almacen": textos.ALMACEN`), y está apuntado, con lo que se ha hecho en su
# lugar, en `docs/T09_PANTALLA_DEL_ALMACEN.md`: este trabajo no podía tocar los routers.
#
# Lo que estas palabras **no** dicen nunca, y es la regla de la casa: que un dato que falta sea un
# cero. Un lote del que no consta la cantidad no está a cero; **no se sabe lo que queda**, y eso se
# dice con esas palabras, con el motivo al lado.
LIBRO_DEL_ALMACEN: dict[str, str] = {
    # --- el nombre de la pantalla y para qué sirve (los mismos que el servidor manda) ---
    "libro_titulo": ALMACEN["titulo"],
    "libro_explica": ALMACEN["explica"],
    "libro_para_que": ALMACEN["para_que"],
    "libro_como_funciona": ALMACEN["como_funciona"],
    "libro_cargando": "Buscando lo que hay en el almacén…",
    # --- las cuatro cosas que pueden pasar, con su nombre delante ---
    "libro_entrada": ALMACEN["entrada"],
    "libro_salida": ALMACEN["salida"],
    "libro_merma": ALMACEN["merma"],
    "libro_ajuste": ALMACEN["ajuste"],
    "libro_entradas": ALMACEN["entradas"],
    "libro_salidas": ALMACEN["salidas"],
    "libro_mermas": ALMACEN["mermas"],
    "libro_ajustes": ALMACEN["ajustes"],
    "libro_queda": ALMACEN["queda"],
    "libro_no_se_sabe_lo_que_queda": ALMACEN["no_se_sabe_lo_que_queda"],
    # --- el lote y el envase ---
    "libro_lote": ALMACEN["lote"],
    "libro_sin_numero_de_lote": ALMACEN["sin_numero_de_lote"],
    "libro_sin_numero_de_lote_pista": ALMACEN["sin_numero_de_lote_pista"],
    "libro_caducidad": ALMACEN["caducidad"],
    "libro_sin_caducidad": ALMACEN["sin_caducidad"],
    "libro_sin_caducidad_pista": ALMACEN["sin_caducidad_pista"],
    "libro_caducado": ALMACEN["caducado"],
    "libro_caducado_pista": ALMACEN["caducado_pista"],
    "libro_en_plazo": ALMACEN["en_plazo"],
    "libro_envase": ALMACEN["envase"],
    "libro_donde_esta": ALMACEN["donde_esta"],
    "libro_categoria_fitosanitario": ALMACEN["categoria_fitosanitario"],
    "libro_categoria_abono": ALMACEN["categoria_abono"],
    "libro_categoria_semilla": ALMACEN["categoria_semilla"],
    "libro_categoria_otros": ALMACEN["categoria_otros"],
    # --- 1. lo que ha llegado: los albaranes ---
    "libro_recepciones": ALMACEN["recepciones"],
    "libro_recepciones_vacio": ALMACEN["recepciones_vacio"],
    "libro_cuantos_albaranes": ALMACEN["cuantos_albaranes"],
    "libro_cuantos_albaranes_uno": ALMACEN["cuantos_albaranes_uno"],
    "libro_nuevo_albaran": ALMACEN["nuevo_albaran"],
    "libro_nuevo_albaran_pista": "Lo que llegó el día que vino el camión",
    "libro_abrir_albaran": "ABRIR ESTE ALBARÁN",
    # El nombre de un albarán en una lista. Lleva el número dentro, así que lo monta `app.js`: aquí no
    # se escribe ni una frase de pantalla.
    "libro_albaran_numero": "Albarán {numero}",
    "libro_albaran_sin_numero": "Un albarán sin número",
    "libro_albaran_pista": "Sin número no se puede comprobar si ya estaba apuntado",
    "libro_fecha_albaran": ALMACEN["fecha_albaran"],
    "libro_proveedor": ALMACEN["proveedor"],
    "libro_numero_albaran": ALMACEN["numero_albaran"],
    "libro_numero_albaran_pista": ALMACEN["numero_albaran_pista"],
    # El número, como rótulo de una fila (en la ficha del albarán): la pregunta de arriba es para el
    # formulario de apuntarlo, y aquí no se pregunta nada, se enseña.
    "libro_numero_de_albaran": "Número del albarán",
    "libro_notas_albaran": "¿Quieres apuntar algo más?",
    "libro_lineas": ALMACEN["lineas"],
    # Las dos cuentas del albarán, en singular y en plural: son las frases que dicen si aquello metió
    # mercancía en el almacén o no, y con uno solo se leerían «1 líneas».
    "libro_cuantas_lineas_uno": "1 línea",
    "libro_cuantas_lineas": "{cuantas} líneas",
    "libro_cuantas_entradas_uno": "1 entrada en el almacén",
    "libro_cuantas_entradas": "{cuantas} entradas en el almacén",
    # --- 2. apuntar un albarán, línea a línea ---
    "libro_albaran_titulo": "Apuntar un albarán",
    "libro_albaran_explica": (
        "Copia lo que pone el papel: quién lo trajo, qué venía y de qué lote. Lo que no ponga el "
        "papel se deja en blanco, y el programa dirá que no lo sabe en vez de suponerlo."
    ),
    "libro_albaran_guardar": "SÍ, GUARDAR EL ALBARÁN",
    "libro_albaran_guardando": "Guardando el albarán…",
    "libro_albaran_anadir_linea": "AÑADIR OTRA LÍNEA",
    "libro_albaran_quitar_linea": "QUITAR ESTA LÍNEA",
    "libro_linea_titulo": "Línea {numero}",
    "libro_linea_que_es": "¿Qué ha llegado?",
    "libro_linea_que_es_pista": (
        "Elige el producto o el abono de tu lista —así el almacén habla de lo mismo que tu "
        "cuaderno— o escribe el nombre tal y como sale en el papel."
    ),
    "libro_linea_libre": "No está en mi lista: lo que pone el papel",
    "libro_linea_nombre": "El nombre que pone el albarán",
    "libro_linea_cantidad": ALMACEN["cantidad"],
    "libro_linea_cantidad_pista": "Lo que trae el papel, sin la dosis por hectárea",
    "libro_linea_unidad": "¿En qué se mide?",
    "libro_linea_unidad_pista": "Lo que ponga el papel. Si no lo pone, déjalo sin decir.",
    "libro_linea_sin_unidad": "El papel no lo dice",
    "libro_linea_numero_lote": "¿Qué número de lote trae?",
    "libro_linea_numero_lote_pista": (
        "El número impreso en el envase. Si no lo trae o no lo has mirado, déjalo en blanco: se "
        "apunta igual y se dice que no se sabe."
    ),
    "libro_linea_caducidad": "¿Hasta cuándo vale?",
    "libro_linea_caducidad_pista": (
        "La fecha del envase. Si no la has mirado, déjalo en blanco: no es que no caduque, es que no "
        "lo sabes todavía."
    ),
    "libro_linea_envase": "¿Cómo viene el envase?",
    "libro_linea_envase_pista": "Una garrafa de 5 litros, un saco de 25 kilos…",
    "libro_linea_contenido": "¿Cuánto trae cada envase?",
    "libro_linea_donde": "¿Dónde lo vas a guardar?",
    "libro_linea_donde_pista": "La nave, el almacén, el rincón donde lo pongas",
    # --- 3. la ficha de un albarán ---
    "libro_de_quien": "De quién es",
    "libro_de_que_dia": "De qué día es",
    # Un movimiento (o un albarán) sin fecha **no es el más antiguo**: es uno del que no se sabe cuándo
    # fue, y eso se dice con estas dos palabras en vez de dejar el hueco en blanco.
    "libro_sin_fecha": "Sin fecha",
    "libro_cuanto_metio": "Lo que metió en el almacén",
    "libro_sin_entradas": (
        "Este albarán no ha metido nada en el almacén: sus entradas no cuentan, pero lo que decía el "
        "papel sigue aquí."
    ),
    "libro_anulado": "Anulado",
    "libro_anulado_con_motivo": "Anulado: {motivo}",
    "libro_anulado_ok": (
        "Anulado. Sus entradas ya no cuentan en el almacén, pero el albarán sigue aquí con lo que "
        "dijo el papel."
    ),
    "libro_anular": ALMACEN["anular"],
    "libro_anular_pregunta": "¿Por qué anulas este albarán?",
    "libro_anular_pista": "En dos palabras: me equivoqué de papel, venía otra cosa, ya estaba…",
    "libro_anular_si": "SÍ, ANULARLO",
    "libro_anular_no": "MEJOR NO",
    "libro_volver_al_libro": "VOLVER AL LIBRO DEL ALMACÉN",
    "libro_volver_al_albaran": "VOLVER AL ALBARÁN",
    # Lo que se dice al guardar un albarán, y lo que se dice cuando se ha quedado en el móvil: las dos
    # frases dicen **qué pasa** con la mercancía, que es lo que el agricultor necesita saber.
    "libro_guardado": "El albarán está apuntado.",
    "libro_guardado_pista": (
        "La mercancía ya está en el almacén: lo que has apuntado es lo que ha entrado. Si algo no "
        "cuadra, anula el albarán y lo apuntas otra vez."
    ),
    "libro_encolado": "El albarán se ha quedado apuntado en el móvil.",
    "libro_ya_estaba": ALMACEN["ya_estaba"],
    "libro_ya_estaba_explica": ALMACEN["ya_estaba_explica"],
    "libro_no_se_pudo_comprobar": ALMACEN["no_se_pudo_comprobar"],
    # --- 4. lo que queda, envase por envase ---
    "libro_existencias_titulo": "Lo que queda en el almacén",
    "libro_existencias_pista": (
        "Cada envase lleva su cuenta por separado: lo que queda de un lote es de ese lote, no del "
        "total del producto."
    ),
    "libro_sin_articulos": ALMACEN["sin_articulos"],
    "libro_cuantos_articulos": ALMACEN["cuantos_articulos"],
    "libro_cuantos_articulos_uno": ALMACEN["cuantos_articulos_uno"],
    "libro_sin_movimientos": "De este envase no se ha apuntado todavía nada.",
    # El nombre de un envase en una lista: «Lote 4471-A». Lo monta `app.js` con el número dentro.
    "libro_lote_numero": "Lote {numero}",
    "libro_lotes_de": "Los envases de este producto",
    "libro_sin_lotes": "De este producto no hay ningún envase apuntado todavía.",
    # --- 5. lo comprado que todavía no ha entrado ---
    "libro_compras_sin_albaran": ALMACEN["compras_sin_albaran"],
    "libro_compras_sin_albaran_una": ALMACEN["compras_sin_albaran_una"],
    # --- 6. el libro, movimiento a movimiento ---
    "libro_movimientos_titulo": "Lo que ha pasado en el almacén",
    "libro_movimientos_pista": "Todo lo que entró, salió, se perdió y se contó distinto, lo último primero.",
    "libro_sin_movimientos_ninguno": (
        "Todavía no se ha movido nada en el almacén. Cuando apuntes un albarán, aquí verás lo que "
        "entró y lo que ha salido después."
    ),
    "libro_no_cuenta": "No cuenta",
    "libro_de_un_albaran": "Entró con un albarán",
    "libro_de_un_apunte": "Sale de un apunte de tu cuaderno",
    "libro_de_una_factura": "Sale de una factura",
    "libro_a_mano": "Se apuntó a mano",
    # --- 7. apuntar una merma, un ajuste o una entrada sin papel ---
    "libro_merma_titulo": "Apuntar que se ha perdido",
    "libro_merma_pista": (
        "Un envase roto, algo que se ha estropeado. No es que lo hayas echado en la tierra: por eso "
        "se apunta aparte y no cuenta como producto gastado."
    ),
    "libro_ajuste_titulo": "Apuntar lo que he contado",
    "libro_ajuste_pista": (
        "Al contar había otra cantidad de la que dice el libro. Si había de más, ponlo en positivo; "
        "si había de menos, con un menos delante."
    ),
    "libro_entrada_titulo": "Apuntar que ha entrado",
    "libro_entrada_pista": (
        "Para lo que ya estaba en el almacén antes de usar el programa. Si lo que ha llegado trae "
        "albarán, apúntalo como albarán: así queda el papel detrás."
    ),
    "libro_movimiento_articulo": "¿De qué es?",
    "libro_movimiento_articulo_pista": "Lo que hay dado de alta en el almacén",
    "libro_movimiento_lote": "¿De qué envase?",
    "libro_movimiento_lote_pista": "Si no sabes el número, se apunta sin él.",
    "libro_movimiento_cantidad": ALMACEN["cantidad"],
    "libro_movimiento_cantidad_pista": ALMACEN["cantidad_pista"],
    "libro_movimiento_unidad": "¿En qué se mide?",
    # El hueco de un envase del que no se dice en qué se mide: aquí **no hay ningún papel** que lo
    # explique (una merma, un conteo, una entrada sin albarán), así que el rótulo no puede hablar del
    # papel como el del albarán. Se vio en la captura de «apuntar que se ha perdido».
    "libro_movimiento_sin_unidad": "Sin decir en qué se mide",
    "libro_movimiento_fecha": "¿De qué día es?",
    "libro_movimiento_motivo": ALMACEN["motivo"],
    "libro_movimiento_motivo_pista": ALMACEN["motivo_pista"],
    "libro_movimiento_guardar": "SÍ, APUNTARLO",
    "libro_movimiento_guardando": "Apuntándolo…",
    "libro_movimiento_guardado": "Apuntado en el libro del almacén.",
    "libro_movimiento_guardado_pista": (
        "Con esto el envase ya lleva su cuenta. Si te has equivocado, anula el movimiento y "
        "apúntalo otra vez."
    ),
    # --- 8. sacar de un lote desde un apunte ---
    "libro_salida_titulo": "Sacar del almacén lo que has echado",
    # El apunte del que sale: no siempre tiene nombre de producto (un abono se apunta por su nombre, un
    # tratamiento por el producto), así que el rótulo es el mismo para los dos y debajo va el detalle.
    "libro_salida_apunte": "El apunte del que sale",
    "libro_salida_explica": (
        "Esto sale de un apunte de tu cuaderno, y la cantidad la dice el apunte: aquí solo dices de "
        "qué envase salió. Así, si un día el fabricante avisa de un lote, se sabe dónde se fue."
    ),
    "libro_salida_de_que_lote": "¿De qué envase ha salido?",
    "libro_salida_lote": "SACAR DE ESTE ENVASE",
    "libro_salida_guardada": "Apuntado: eso es lo que ha salido del envase.",
    "libro_salida_total": "Lo que se ha sacado del envase",
    "libro_salida_por_hectarea": "Cuánto por hectárea",
    "libro_salida_hectareas": "Hectáreas del apunte",
    "libro_salida_total_pista": "El total que se gastó, no lo que se echa en cada hectárea",
    "libro_salida_cantidad": "¿Cuánto has sacado en total?",
    "libro_salida_cantidad_pista": (
        "El apunte solo tiene lo que se echa en cada hectárea, y eso no es lo que se gastó. Escribe "
        "el total, o completa el apunte con la cantidad total."
    ),
    "libro_salida_descuadre_si": "SÍ, LA DIFERENCIA ES DE VERDAD",
    "libro_salida_corregir": "CORREGIR LA CANTIDAD",
    "libro_sin_articulos_de_eso": (
        "De esto no hay nada apuntado todavía en el almacén. Apunta el albarán cuando llegue y "
        "entonces podrás decir de qué envase salió."
    ),
    "libro_ver_el_libro": "VER EL LIBRO DEL ALMACÉN",
    "libro_ver_la_cesta": "VER LO QUE TENGO EN EL ALMACÉN",
    # --- los botones de las cuatro cosas que se pueden apuntar ---
    # Son los mismos rótulos que el servidor manda en las respuestas del almacén (`ALMACEN`), para que
    # el botón y lo que contesta el programa digan lo mismo.
    "libro_nueva_entrada": ALMACEN["nueva_entrada"],
    "libro_nueva_merma": ALMACEN["nueva_merma"],
    "libro_nuevo_ajuste": ALMACEN["nuevo_ajuste"],
    "libro_nueva_salida": ALMACEN["nueva_salida"],
    # --- 9. enganchar la factura que llega después ---
    "libro_factura_enganchada": ALMACEN["factura_enganchada"],
    "libro_factura_sin": ALMACEN["sin_factura"],
    "libro_factura_de": "La factura de este albarán",
    "libro_engancharla": ALMACEN["enganchar_factura"],
    "libro_factura_titulo": "Decir de qué factura es este albarán",
    "libro_factura_explica": (
        "La mercancía ya entró el día del albarán: la factura solo dice de quién era y cuánto costó. "
        "Por eso engancharla no cambia ni un litro de lo que hay en el almacén."
    ),
    "libro_factura_elige": "¿Cuál de tus facturas es?",
    "libro_factura_nada_apuntado": (
        "Elegir una de esta lista no apunta nada: el programa solo mira si puede ser la de este "
        "albarán y te lo dice."
    ),
    "libro_factura_nada": (
        "No tienes ninguna factura apuntada. Sube la factura y vuelve aquí: entonces podrás decir "
        "cuál es la de este albarán."
    ),
    "libro_factura_es_esta": "ES ESTA",
    "libro_factura_propuesta": (
        "El programa cree que esta factura es la de este albarán. Míralo y dilo tú: todavía no está "
        "apuntado nada."
    ),
    "libro_factura_no_propuesta": (
        "Esta factura no parece la de este albarán. Míralas otra vez: el proveedor o el número no "
        "coinciden. Si de todas formas estás seguro, puedes decir que sí."
    ),
    "libro_factura_como": "Por qué se propone",
    "libro_factura_lineas": "Lo que parece el mismo producto",
    "libro_factura_si": "SÍ, ES ESTA",
    "libro_factura_si_igual": "SÍ, ES ESTA AUNQUE NO CUADRE",
    "libro_factura_otra": "ELEGIR OTRA FACTURA",
    "libro_factura_comprobando": "MIRANDO SI ES ESA…",
    "libro_factura_enganchada_ok": (
        "Enganchada. La mercancía no se cuenta otra vez: entró una vez, el día que llegó el albarán."
    ),
    "libro_factura_sin_comprobar": (
        "No se ha podido preguntar si esta factura es la de este albarán. Prueba otra vez cuando "
        "tengas cobertura: hasta que lo digas tú, no se apunta nada."
    ),
}

# Los textos del libro del almacén se sirven **dentro del bloque del almacén** (`cesta`), que es el
# que `/api/interfaz` manda al móvil. El porqué, con su alternativa, está escrito más arriba.
CESTA.update(LIBRO_DEL_ALMACEN)



# El cultivo de cada parcela: la pestaña «Características DGC» e «Historial Cultivos» de la app
# oficial. Se le dice «qué hay sembrado», que es como lo pregunta un agricultor.
CULTIVOS: dict[str, str] = {
    "titulo": "Qué hay sembrado",
    "explica": (
        "Dinos qué hay este año en cada parcela. Con eso, cuando apuntes un tratamiento o una "
        "labor ya no tienes que escribir el cultivo: el programa ya lo sabe."
    ),
    "para_que": (
        "Sirve para tres cosas: el cuaderno de cada año dice qué había en la tierra, puedes ver "
        "qué sembraste los años anteriores —que es lo que ayuda a decidir la rotación— y el "
        "aviso de «en esa fecha no había cultivo» funciona."
    ),
    "sin_parcelas": (
        "Todavía no tienes parcelas. Añade la primera y después me dices qué hay sembrado."
    ),
    "faltan": "A {cuantos} parcelas les falta decir qué tienen este año.",
    # Con una sola tierra sin decir, «A 1 parcelas les falta decir qué tienen» se lee fatal (ronda 84).
    "faltan_uno": "A 1 parcela le falta decir qué tiene este año.",
    "todo_dicho": "Ya está dicho qué hay en todas tus parcelas.",
    "decir": "DECIR QUÉ HAY SEMBRADO",
    "cambiar": "CAMBIARLO",
    "falta_decirlo": "Todavía no has dicho qué hay aquí este año.",
    "tiene": "Este año hay",
    "cuando": "Desde",
    "hasta": "Hasta",
    # Las dos etiquetas de estado de cada tierra (ronda 90, del diseño de Stitch de esta pantalla): con más
    # de cincuenta tierras, lo que se viene a buscar aquí es **a cuáles les falta decir qué tienen**, y eso
    # hay que verlo sin leer la ficha de cada una.
    "al_dia": "Al día",
    "falta_rellenar": "Falta rellenar",
    # **El filtro de las que faltan** (30/09/2026). Lo trae el diseño de escritorio de esta pantalla
    # (`docs/stitch/escritorio/cultivos.png`), y con 64 tierras es lo que convierte el aviso en algo que se
    # puede arreglar: el aviso dice cuántas faltan y el botón enseña esas y solo esas, para ir diciéndolas una
    # detrás de otra sin buscarlas en la lista. Y siempre hay salida: «VERLAS TODAS» (un filtro del que no se
    # puede salir es una lista de tierras que ha desaparecido).
    "ver_las_que_faltan": "VER SOLO LAS QUE FALTAN",
    "verlas_todas": "VERLAS TODAS",
    "otros_anos": "Otros años",
    "repite": (
        "Aquí has puesto lo mismo que el año pasado. Si vas a repetir, apúntalo en las medidas "
        "preventivas: la rotación de cultivos es una de las que se piden."
    ),
    "la_especie": "¿Qué hay sembrado?",
    "la_especie_pista": "Por ejemplo: trigo blando, cebada, girasol, alfalfa, viña",
    "variedad": "¿De qué variedad?",
    "variedad_pista": "Si lo sabes. Por ejemplo: Craklin",
    "sistema": "¿Es de secano o de regadío?",
    "desde_cuando": "¿Desde cuándo está?",
    "hasta_cuando": "¿Hasta cuándo?",
    "fechas_pista": "Si no lo sabes, déjalo en blanco",
    "guardado": "Apuntado. Ya no tendrás que escribir el cultivo en cada apunte.",
    # Cambiar lo que ya dijiste, y quitarlo (ronda 93). Las dos cosas se pueden hacer desde la ronda
    # anterior **por la API** (`PUT`/`POST` sobre el mismo cultivo y `DELETE`), pero ninguna pantalla las
    # pedía: al agricultor que se equivocaba de tierra al decir el cultivo solo le quedaba escribir otro
    # encima, que es dejar un dato falso en el cuaderno.
    "corrigiendo": "ESTÁS CAMBIANDO LO QUE DIJISTE",
    "quitar": "QUITAR EL CULTIVO DE ESTE AÑO",
    # Por qué se ofrece quitarlo, con el caso de verdad: es lo que le pasa al que se equivoca de tierra, y
    # lo que hay que hacer si la tierra está en barbecho — que no es lo mismo que «no lo sé».
    "quitar_pista": (
        "Si esta tierra este año está en barbecho, o el cultivo que dijiste era de otra tierra, quítalo: "
        "volverá a salir como una a la que le falta decir qué tiene."
    ),
    # El final del quitado. Se dice **qué pasa ahora**, que es lo que tranquiliza: no se queda un hueco ni
    # un dato falso, sino la pregunta por contestar.
    "quitado_titulo": "Quitado",
    "quitado": (
        "Esa tierra vuelve a salir como una a la que le falta decir qué tiene este año. Lo que estaba "
        "dicho queda guardado en el historial del cuaderno."
    ),
    # Lo que hay que hacer en esta pantalla y la tranquilidad de que nada es obligatorio salvo el cultivo
    # (ronda 90, del diseño de Stitch de «decir qué hay sembrado»). Sin esto, cinco casillas parecen un
    # examen, y quien no sabe la variedad o la fecha exacta se queda mirándolo.
    "rellenar_aviso": (
        "Rellena lo que sepas y pulsa GUARDAR. Lo único que hace falta de verdad es el cultivo: lo demás, "
        "si no estás seguro, déjalo en blanco."
    ),
    # La etiqueta del campo que sí hace falta (diseño de Stitch): dice cuál es sin que haya que adivinarlo.
    "imprescindible": "Hace falta",
    "cual_parcela": "¿En qué parcela?",
}


# Las unidades homogéneas de cultivo. La app oficial las llama «UHC» y aquí se dice «parcelas
# que se llevan igual», que es lo que son y lo que el agricultor entiende. Sirven para lo mismo
# que allí: apuntar una vez lo que se hace en seis parcelas.
GRUPOS: dict[str, str] = {
    "titulo": "Parcelas que se llevan igual",
    "explica": (
        "Cuando varias parcelas tienen lo mismo y se labran igual, se pueden apuntar de una vez: "
        "un tratamiento para las seis, en vez de seis apuntes."
    ),
    "para_que": (
        "El cuaderno sigue diciendo qué se hizo en cada parcela, porque el grupo las lleva "
        "dentro. Lo que se ahorra es escribirlo seis veces."
    ),
    "sin_grupos": (
        "Todavía no has juntado ninguna parcela. Al apuntar un tratamiento, después de la lista "
        "de parcelas te saldrán los grupos que tengas."
    ),
    "calcular": "JUNTARLAS TÚ SOLO",
    "automatico": "Lo juntó el programa.",
    # Cuando el grupo lo hizo el agricultor a mano (ronda 90, del diseño de Stitch de esta pantalla): la
    # etiqueta dice de quién es el grupo, que es lo que dice si puede cambiarlo.
    "juntado_por_ti": "Juntado por ti.",
    # El rótulo de la lista de tierras del grupo. Con las hectáreas de cada una, que es lo que faltaba: los
    # nombres separados por puntos no decían cuánto tenía cada tierra.
    "tierras_del_grupo": "Tierras que van juntas en este grupo:",
    "creados": "Ya están juntas: {cuantos} grupos nuevos.",
    "no_hay_nada_que_juntar": (
        "No hay parcelas que se puedan juntar. Para juntarlas hace falta que tengan el mismo "
        "cultivo y el mismo sistema, y que estén cerca."
    ),
    "por_sin_cultivo": (
        "Hay parcelas de las que no sabemos qué tienen sembrado, así que no se pueden juntar. "
        "Dilo primero en «Qué hay sembrado»."
    ),
    "por_sin_forma": (
        "Hay parcelas que no tienen su forma puesta en el mapa, así que no se puede saber si "
        "están cerca de otras. Se traen del SIGPAC desde «Mis parcelas»."
    ),
    "faltan_cultivos": (
        "Para juntarlas hace falta saber qué hay sembrado en cada una. Hay parcelas sin decirlo."
    ),
    "en_varias": "En varias parcelas a la vez",
    "en_varias_pista": "Un apunte para todas las del grupo",
    "cuantas": "{cuantas} parcelas",
    "sin_grupos_al_apuntar": (
        "Si tienes varias parcelas con lo mismo, junta las para no apuntarlo seis veces."
    ),
}


# El informe de las labores: lo que se hizo en el campo (sembrar, regar, podar, pastorear, coger
# la cosecha…). Va al cuaderno en papel y al fichero de datos, y es una de las secciones que pide
# el contenido mínimo del cuaderno (bloque 5, «Labores culturales»), junto con el riego (bloque 9)
# y la siembra y plantación (bloque 6), que en este programa son labores de otro tipo.
LABORES: dict[str, str] = {
    "informe_titulo": "Labores y trabajos",
    "informe_sin_nada": "Todavía no hay ninguna labor apuntada este año.",
}

# Las parcelas del agricultor: sus tierras, con su referencia del SIGPAC y su superficie. Es el
# bloque 12 del contenido mínimo («Datos de superficies»), y en el papel tiene que estar: es lo
# primero que mira quien revisa un cuaderno.
PARCELAS: dict[str, str] = {
    "informe_titulo": "Mis parcelas",
    "informe_sin_nada": "Todavía no has apuntado ninguna parcela.",
}

# Las naves y los almacenes (bloque de «edificaciones» del contenido mínimo) y las máquinas de
# echar producto (bloque de «maquinaria»). El nombre es el mismo que ya se ve en *Mis cosas*: si en
# la pantalla se llama «Naves, almacenes e invernaderos», en el papel tiene que llamarse igual.
#
# Se dice «máquinas de echar producto» y no «maquinaria» porque es lo que de verdad se apunta aquí:
# el pulverizador o el atomizador que hizo la aplicación, que es lo que el cuaderno tiene que poder
# demostrar. Un tractor no aplica nada.
INSTALACIONES: dict[str, str] = {
    "informe_titulo": "Naves, almacenes e invernaderos",
    "informe_sin_nada": "Todavía no has apuntado ninguna nave ni almacén.",
}

MAQUINARIA: dict[str, str] = {
    "informe_titulo": "Máquinas de echar producto",
    "informe_sin_nada": "Todavía no has apuntado ninguna máquina.",
}

# Elegir el pueblo. La lista es la oficial del INE (los 2.248 municipios de Castilla y León), y
# está para que el agricultor **no tenga que saberse ningún código**: escribe las primeras letras
# de su pueblo, lo elige, y el programa rellena el municipio, la provincia y el código.
MUNICIPIOS: dict[str, str] = {
    "elegir": "¿En qué pueblo está?",
    "pista": "Escribe las primeras letras y elígelo de la lista",
    "buscar": "BUSCAR EL PUEBLO",
    "cualquiera": "Todas las provincias",
    "codigo_pista": "Código {codigo}",
    "no_esta_en_la_lista": (
        "Ese pueblo no está en la lista de Castilla y León. Prueba a escribir las primeras "
        "letras y elígelo; si tu pueblo es de otra provincia, escríbelo a mano."
    ),
    "sin_lista": (
        "No se ha podido cargar la lista de pueblos. Escribe el nombre a mano: se puede "
        "apuntar la parcela igual."
    ),
    "cuantos": "{cuantos} pueblos",
}

# El mapa: elegir la tierra tocándola, que es lo que sabe hacer todo el mundo.
#
# Las palabras están elegidas para que no haga falta saber nada de mapas: «acercar» y «alejar» en
# vez de «zoom», «la foto del campo» en vez de «ortofoto», y «los linderos» en vez de «recintos
# SIGPAC». Y se dice claro lo que hace falta (conexión) y lo que se puede hacer sin ella.
MAPA: dict[str, str] = {
    "titulo": "Buscar mi tierra en el mapa",
    "explica": (
        "Muévete por el mapa y toca tu trozo de tierra. El programa mira en el SIGPAC qué parcela "
        "es y te la enseña antes de apuntarla."
    ),
    "necesita_conexion": (
        "El mapa necesita conexión. Si no tienes, puedes apuntar la parcela con su referencia."
    ),
    "sin_conexion": (
        "No se puede cargar el mapa ahora mismo: para el mapa hace falta conexión. Puede ser la "
        "cobertura o que el servicio no esté disponible. Apunta la parcela con su referencia y "
        "lo miras en el mapa otro día."
    ),
    "acercar": "ACERCAR",
    "alejar": "ALEJAR",
    "estoy_aqui": "ESTOY AQUÍ",
    "dame_este_punto": "ESTA ES MI TIERRA",
    "buscando": "Mirando en el SIGPAC…",
    "donde_estoy": "Dónde estoy",
    "sin_ubicacion": (
        "No se ha podido saber dónde estás. Mira que el móvil tenga la ubicación encendida y "
        "que hayas dejado que el navegador la use."
    ),
    "encontrado_titulo": "Esta es la parcela que hay ahí",
    # La confirmación de que el SIGPAC ha contestado, con su recordatorio (ronda 90, del diseño de Stitch de
    # esta pantalla): lo que garantiza que se apunta la tierra que es, es que él compare los datos con su papel.
    "comprobado": (
        "Comprobado en el SIGPAC: hay una parcela bajo la cruz. Mira abajo si los datos coinciden con tu papel."
    ),
    "pregunta": "¿Es tuya esta tierra?",
    "no_hay_nada": (
        "Ahí no hay ninguna parcela del SIGPAC. Prueba a tocar un poco más adentro de tu tierra, "
        "o busca por tu pueblo y el número de la parcela."
    ),
    "cuantos_trozos": (
        "En esa parcela hay {cuantos} trozos. Los verás en la lista para marcar los tuyos."
    ),
    "la_foto": "La foto del campo",
    "los_linderos": "Los linderos",
    "el_cultivo": "Lo que se declaró",
    "guardando": "Apuntando la parcela…",
    "apuntada": "Ya está apuntada. Puedes verla en Mis parcelas.",
    "apuntarla": "SÍ, APUNTARLA",
    "no_es_mia": "NO ES ESA",
    # El funcionamiento de la pantalla, explicado como se lo contaría alguien a un vecino.
    "elegir_en_el_mapa": "VER EL MAPA Y ELEGIRLA AHÍ",
    "pista_mover": (
        "Mueve el mapa con el dedo hasta poner tu tierra en la cruz del centro, y pulsa ESTA ES MI "
        "TIERRA. También puedes tocar directamente tu trozo."
    ),
    "cargando": "Cargando el mapa…",
    "poner_en_el_centro": "ESTA ES MI TIERRA",
    "superficie": "Superficie",
    "pueblo": "Pueblo",
    "referencia_catastral": "Referencia catastral",
    "sin_centro": (
        "No se puede saber por dónde empezar el mapa. Pulsa ESTOY AQUÍ, o apunta primero una "
        "parcela por su referencia y el mapa se abrirá en tu tierra."
    ),
    # La zona de nitratos, con sus tres respuestas posibles y la de «solo una parte». Son cuatro
    # mensajes porque son cuatro cosas distintas, y de ellas dependen las reglas de abono.
    "zona_nitratos": "Zona de nitratos",
    "zona_nitratos_si": "Sí: tu tierra está en zona de nitratos",
    "zona_nitratos_parte": (
        "Solo una parte: el {porcentaje} % de tu tierra está en zona de nitratos"
    ),
    "zona_nitratos_no": "No está en zona de nitratos",
    "zona_nitratos_no_se": (
        "No se ha podido comprobar si está en zona de nitratos. Puedes apuntarla igual y mirarlo "
        "más tarde."
    ),
    "no_se_pudo_apuntar": "No se ha podido apuntar la parcela. Prueba otra vez.",
}

# Traer las tierras del cuaderno de la Junta.
#
# El agricultor de Castilla y León que lleva su cuaderno en la aplicación de la Junta (el Cuecyl)
# tiene ahí, ya escritas, todas sus parcelas: las que declaró en la Solicitud Única, con su
# polígono, su parcela, su recinto, su cultivo y sus hectáreas. Volver a teclearlas sería una
# tontería y, sobre todo, una fuente de errores: un número cambiado y la tierra del cuaderno ya no
# es la suya.
#
# Las palabras están puestas para que se entienda sin saber nada de informática: «el cuaderno de
# la Junta», «subir el fichero», «tus tierras». Nada de «importar», «sincronizar» ni nombres de
# formatos de fichero.
CUADERNO_CYL: dict[str, str] = {
    "titulo": "Traer mis tierras del cuaderno de la Junta",
    "explica": (
        "Si ya llevas el cuaderno en la aplicación de la Junta, no hace falta que escribas tus "
        "tierras otra vez: sube aquí el cuaderno que descargas y el programa las apunta por ti."
    ),
    "como_se_hace": (
        "Entra en la aplicación de la Junta con tu certificado, descarga el cuaderno de la "
        "campaña y guarda el fichero en el ordenador o en el móvil. Después súbelo aquí."
    ),
    "traer": "TRAER MIS TIERRAS",
    "eligiendo": "Abriendo el cuaderno…",
    # El aviso de antes de subir nada (ronda 90, del diseño de Stitch de esta pantalla). Es la duda que
    # tiene el agricultor con el dedo encima del botón —«¿y esto no me va a pisar lo que ya tengo?»— y la
    # respuesta es la regla de esta pantalla: leer el fichero no apunta nada hasta que él lo confirme.
    "no_apunta_nada": (
        "Leer el fichero no apunta nada todavía: primero verás en pantalla todo lo que trae y tú decides "
        "si se guarda."
    ),
    "que_fichero": "El fichero del cuaderno (el que se llama CuadernoExplotacion…)",
    "resumen_titulo": "Esto es lo que trae tu cuaderno",
    "resumen_campana": "Campaña",
    "resumen_lineas": "Tierras apuntadas en el papel",
    "resumen_tierras": "Tierras distintas",
    "resumen_hectareas": "Hectáreas que declaras",
    "resumen_pueblos": "Pueblos",
    "resumen_cultivos": "Lo que tienes sembrado",
    "resumen_nitratos": "Tierras en zona de nitratos",
    "resumen_partidas": "Tierras que el papel parte en trozos",
    "resumen_titular": "Titular",
    "lineas_titulo": "Las tierras que va a apuntar",
    "confirmar": "SÍ, SON MIS TIERRAS",
    "volver": "NO, VOLVER",
    "importando": "Apuntando tus tierras…",
    "hecho_titulo": "Tus tierras ya están apuntadas",
    "creadas": "Tierras nuevas: {cuantas}",
    "con_cultivo": "Tierras que ya tenías y les he puesto lo que siembras: {cuantas}",
    "ya_estaban": "Tierras que ya estaban apuntadas: {cuantas}",
    "no_vinieron": "Líneas que no se han podido apuntar: {cuantas}",
    "titular_rellenado": "De tus datos de titular he rellenado: {cuales}",
    "titular_ya_estaba": "Tus datos de titular ya estaban puestos: no he tocado nada.",
    "avisos_titulo": "Cosas que conviene que mires",
    "otra_vez": (
        "Puedes subir el cuaderno las veces que quieras: la misma tierra no se apunta dos veces."
    ),
    "ver_tierras": "VER MIS TIERRAS",
    # El cuaderno no se puede subir sin conexión, y no se puede dejar «en cola» como un apunte:
    # un fichero o va entero o no va. Se dice claro en vez de fingir que se ha guardado.
    "sin_conexion": (
        "Para subir el cuaderno hace falta conexión. El fichero lo tienes en tu móvil: "
        "prueba cuando tengas cobertura."
    ),
    "no_se_pudo": (
        "No se ha podido abrir el cuaderno. Mira que sea el fichero que descargas de la "
        "aplicación de la Junta."
    ),
    # Sacar el cuaderno relleno y decir lo que falta. Es la respuesta a «¿qué datos me piden?»: no
    # una lista escrita a mano, sino lo que sale de comparar las 25 hojas del cuaderno oficial con
    # lo que el agricultor tiene apuntado.
    "sacar_titulo": "Sacar mi cuaderno para la Junta",
    # **Se dice de qué año es el fichero** (06/10/2026). La ruta sacaba el año en curso aunque el
    # agricultor estuviera mirando otro; ahora saca el que se está mirando, y aquí se dice con esas
    # palabras para que se sepa **qué se lleva** antes de pulsar (aceptación 3 del encargo: el alcance
    # de una descarga se dice; «todos», «los filtrados» o, aquí, «el del año que estás viendo»).
    "sacar_explica": (
        "El programa escribe tu cuaderno **del año que estás viendo** con las 25 hojas de la Junta y "
        "todo lo que tienes apuntado: tus tierras, tus tratamientos, tus abonos, tus análisis y lo que "
        "has vendido. Lo que falte sale en blanco, nunca con un dato inventado."
    ),
    "sacar": "SACAR MI CUADERNO",
    "hojas_datos": "{cuantas} hojas de 25 llevan datos tuyos",
    # Con una sola hoja, «1 hojas de 25 llevan datos tuyos» (ronda 84). Es la pista que va dentro del bloque
    # verde de la inspección, la que se mira con el inspector delante.
    "hojas_datos_uno": "1 hoja de 25 lleva datos tuyos",
    "que_falta_titulo": "Lo que te falta para tenerlo completo",
    "que_falta_pista": "Cada cosa dice dónde se apunta, para que la puedas arreglar.",
    "donde": "Dónde se apunta",
    "hoja": "Hoja",
    "a_mano_en_el_fichero": "Se rellena a mano en el fichero",
    "todo_completo": "No le falta nada de lo que pide el cuaderno.",
}

# Las facturas de compra.
#
# El agricultor hace una foto al papel (o sube el PDF que le manda el proveedor), el programa lo
# lee y **le enseña lo que ha entendido** para que lo confirme o lo corrija. Eso último es lo que
# hace que se pueda leer una foto con el móvil sin jugarse un dato.
#
# Y no es un adorno para llevar las cuentas: el cuaderno de la Junta pide, en la hoja de la
# fertilización, la «empresa suministradora» y el «nº de factura», y en la del abonado el «nº de
# albarán». Sin facturas, esas casillas se quedan vacías.
# ── Los años del cuaderno (la campaña) ──
#
# POR QUÉ EXISTE ESTA PANTALLA (ronda 93). Hasta ahora la campaña **la creaba el programa** al darse de
# alta la cuenta, y no había ninguna pantalla que la enseñara: `GET/POST/PUT/DELETE /api/campanas`
# estaban en el servidor y no los pedía nadie. O sea que si el año salía mal escrito (2027 donde iba
# 2026), o si el agricultor quería empezar el año siguiente, **no había forma** de hacerlo desde la
# aplicación; y de la campaña cuelga el año entero del cuaderno.
#
# Cómo se le habla: **«el año»**, nunca «la campaña». Es la palabra del programa, y el agricultor dice
# «el año del cuaderno» o «la cosecha». El rótulo de arriba de cada ficha lo dice entero.

# ── Las tablas del ordenador (30/09/2026) ──
#
# POR QUÉ ESTÁN AQUÍ LOS NOMBRES DE LAS COLUMNAS. Porque son **frases que lee el agricultor** («Qué tiene
# este año», «Referencia SIGPAC») y en este proyecto eso vive en `textos.py`, no dentro de un componente.
# La tabla de tierras es la primera: es la que pidió David (64 tierras que en el móvil se miran de una en
# una y en el ordenador se miran de arriba abajo).
TABLA: dict[str, str] = {
    # El nombre de la tabla, para quien no ve la pantalla (lector de pantalla).
    "tierras_etiqueta": "Tus tierras, en una tabla",
    "numero": "Nº",
    "nombre": "Nombre",
    "sigpac": "Referencia SIGPAC",
    "pueblo": "Pueblo",
    "hectareas": "Hectáreas",
    "cultivo": "Qué tiene este año",
    "acciones": "Acciones",
    # **Las etiquetas cortas de los botones de una fila.** En una tarjeta del móvil cabe «VER O CAMBIAR LO QUE
    # HAY SEMBRADO», pero en una tabla esa frase ensancha la última columna hasta sacar la tabla de la
    # pantalla (se vio en la captura de la versión de ordenador: con el panel abierto, los botones de la
    # última columna quedaban tapados). Aquí va lo mismo en una palabra, y la frase entera sigue estando
    # donde se lee: en la ficha del móvil y en el panel de al lado.
    "decirlo": "DECIRLO",
    "ver_cultivo": "VER",
    # El título del botón de una cabecera que ordena («Ordenar por Nombre»). Va en el `title` y no se ve:
    # el que se ve es el nombre de la columna, que es lo que se pulsa.
    "ordenar_por": "Ordenar por: {columna}",
    # El pie de la tabla. Lleva número, así que tiene singular y plural (`con_cuenta`).
    #
    # **OJO CON EL NOMBRE DE LA CLAVE**: el ayudante busca `<base>_uno` para el singular y `<base>_varios`
    # (o `<base>`) para el plural. Aquí estaban escritas como `_una` —porque «tierra» y «factura» son
    # femeninas— y con una sola tierra la tabla decía «1 tierras» y con una sola factura, «1 facturas». Lo
    # cazó la captura de la versión de ordenador, no una prueba: por eso ahora estas claves están también en
    # `TestSingularYPlural` (`tests/test_sin_jerga.py`), que es la prueba que existe para esto.
    "resumen_tierras_uno": "1 tierra · {hectareas} ha",
    "resumen_tierras": "{cuantas} tierras · {hectareas} ha",
    "resumen_filtrado": "{cuantas} de {total} tierras · {hectareas} ha",
    # ── La tabla del cuaderno (los apuntes del año) ──
    #
    # Es la tabla que pidió David para el ordenador: lo que en el móvil se mira apunte a apunte, aquí de
    # arriba abajo y con el total de hectáreas del año al pie.
    "apuntes_etiqueta": "Lo que has apuntado este año, en una tabla",
    "fecha": "Fecha",
    "clase": "Clase",
    "que": "Qué",
    "tierra": "Tierra",
    "firmado": "Firmado",
    "resumen_apuntes_uno": "1 apunte · {hectareas} ha tratadas",
    "resumen_apuntes": "{cuantas} apuntes · {hectareas} ha tratadas",
    # Al pie del cuaderno, cuántos están firmados. Lo pide el diseño de escritorio de esa pantalla, y solo
    # sale si hay alguno (un «0 firmados» no le importa a nadie). Sin número delante no hay singular y plural
    # que valgan: la frase es la misma con uno y con veinte.
    "firmados": "{cuantos} firmados",
    "firmados_uno": "1 firmado",
    # ── **Lo que falta por saber, cuando el pie de una tabla suma** (A14 de `docs/T02_VALORES_POR_DEFECTO.md`,
    #    05/10/2026) ──
    #
    # Por qué existen. Los pies de las tablas y las dos tarjetas del panel de mando sumaban con
    # `Number(...) || 0`: un apunte sin hectáreas, una tierra sin superficie dicha o una venta sin kilos
    # **sumaban cero en silencio**, y el total se leía como si estuviera completo. Ahora se suma lo que se
    # sabe y **se dice cuánto falta**, con la cuenta delante.
    #
    # Están en `TABLA` y no en los textos del panel de mando porque **`app.js` lee los dos sitios** y
    # `TABLA` se sirve en `/api/interfaz` (los del panel también, pero el mismo dato dicho en dos
    # diccionarios acaba diciéndose de dos maneras). Y con sus dos formas: «1 tierra sin decir sus
    # hectáreas» es lo primero que hace desconfiar de un programa; hay una prueba que exige las dos.
    "tierras_sin_hectareas": "{cuantas} tierras sin decir sus hectáreas",
    "tierras_sin_hectareas_uno": "1 tierra sin decir sus hectáreas",
    "apuntes_sin_hectareas": "{cuantas} apuntes sin decir sus hectáreas",
    "apuntes_sin_hectareas_uno": "1 apunte sin decir sus hectáreas",
    "ventas_sin_kilos": "{cuantas} ventas sin decir sus kilos",
    "ventas_sin_kilos_uno": "1 venta sin decir sus kilos",
    # ── La tabla de los años del cuaderno ──
    "anos_etiqueta": "Los años de tu cuaderno, en una tabla",
    "ano": "Año",
    "empieza": "Empieza",
    "termina": "Termina",
    "dentro": "Qué tiene dentro",
    "estado": "Estado",
    "resumen_anos_uno": "1 año en tu cuaderno",
    "resumen_anos": "{cuantas} años en tu cuaderno",
    # ── La tabla de las facturas ──
    "facturas_etiqueta": "Tus facturas, en una tabla",
    "proveedor": "Quién te lo vendió",
    "numero_factura": "Nº de factura",
    "base": "Base",
    "iva": "IVA",
    "total": "Total",
    "papel": "El papel",
    "resumen_facturas_uno": "1 factura · {total} €",
    "resumen_facturas": "{cuantas} facturas · {total} €",
    "resumen_facturas_sin_total_uno": "1 factura · falta decir el total",
    "resumen_facturas_sin_total": "{cuantas} facturas · falta el total de alguna",
    # ── La tabla de lo que tengo en el almacén (30/09/2026) ──
    #
    # Es la tabla del diseño de escritorio que pidió Stitch para esta pantalla
    # (`docs/stitch/escritorio/almacen.png`): el libro de entradas y salidas de cada producto, de arriba
    # abajo. Los nombres de las columnas son **los del diseño y los del cuaderno** («Comprado», «Echado»,
    # «Te queda»), en una palabra, porque un nombre de columna largo se come el ancho de la tabla.
    #
    # **Lo que el diseño enseñaba y aquí NO está: el gasto en euros por producto.** Ese número no existe en
    # el programa —las líneas de factura traen un importe, pero no está sumado por producto para la
    # campaña—, y ponerlo de adorno sería inventarse un dato. Cuando exista, tiene su columna.
    "cesta_etiqueta": "Lo que tienes en el almacén, en una tabla",
    "producto": "Producto",
    "registro": "Nº de registro",
    "comprado": "Comprado",
    "echado": "Echado",
    "te_queda": "Te queda",
    # **La etiqueta corta de la tierra a la que le falta decir qué tiene** (30/09/2026). En la tarjeta del
    # móvil la frase entera («Todavía no has dicho qué hay aquí este año.») se lee bien; en una celda de la
    # tabla ocupaba tres renglones y dejaba la columna estrecha y alta. Aquí va lo mismo en tres palabras, y
    # la frase entera sigue estando donde se lee: en la tarjeta y en el panel de al lado.
    "sin_decir": "Falta decirlo",
    # El pie de la tabla del almacén: cuántos productos hay y, si los hay, cuántos hay que mirar (que es la
    # cuenta que se viene a hacer aquí, como las hectáreas en la de tierras).
    "resumen_cesta_uno": "1 producto en el almacén",
    "resumen_cesta": "{cuantas} productos en el almacén",
    "resumen_cesta_mirar_uno": "1 hay que mirarlo",
    "resumen_cesta_mirar": "{cuantas} hay que mirarlos",
    # **Las etiquetas cortas del estado de un producto** (30/09/2026). En la tarjeta del móvil la frase
    # entera se lee bien («Las cuentas cuadran», «No se puede comparar»); en una celda de la tabla ocupaba
    # cuatro renglones y ponía la fila altísima —se vio en la captura de la versión de ordenador, que es
    # justo para lo que está—. Aquí va lo mismo en dos palabras, y **dice lo mismo con palabras**: el color
    # solo no informa (regla de la casa). La frase entera sigue en la tarjeta y en el panel de al lado.
    "estado_cuadra": "Cuadra",
    "estado_mirar": "Míralo",
    "estado_sin_dato": "Falta el dato",
    "estado_no_se_compara": "No se compara",
    # ── La tabla de lo que hay sembrado (30/09/2026) ──
    #
    # POR QUÉ HIZO FALTA. Esta pantalla se quedó fuera de la lista de tablas por hacer, y es —después de las
    # tierras— **la lista más larga del programa**: una fila por tierra, con 64 tierras. En el ordenador se
    # veían tres tarjetas enormes por pantalla; en la revisión de la interfaz del 30/09/2026 se vio con los
    # datos de verdad. La tarjeta se queda para el móvil, que es donde se lee de una en una.
    "cultivos_etiqueta": "Qué hay sembrado este año, en una tabla",
    "este_ano": "Este año hay",
    "otros_anos": "Otros años",
    # La columna del aviso de rotación (30/09/2026): **en su propia columna**, que es como lo pone el diseño de
    # escritorio de esta pantalla (`docs/stitch/escritorio/cultivos.png`). Antes iba como letra pequeña debajo
    # del cultivo, y ahí no se ve al recorrer la lista de arriba abajo, que es lo que se hace con 64 tierras.
    "rotacion": "Rotación",
    # La etiqueta corta del botón de la fila. La de la tarjeta («CAMBIARLO») ya cabe, pero va aquí para que
    # las tablas tengan sus rótulos en el mismo sitio.
    "cambiarlo": "CAMBIARLO",
    # El aviso de que este año se repite el cultivo del año pasado, en corto: la frase entera (que explica
    # por qué importa) se queda en la tarjeta.
    "repite_el_ano_pasado": "Repite lo del año pasado",
    # El pie: cuántas tierras hay y cuántas tienen dicho su cultivo, que es la cuenta que se viene a hacer
    # en esta pantalla («¿a cuáles les falta?»).
    "resumen_cultivos_uno": "1 tierra",
    "resumen_cultivos": "{cuantas} tierras",
    "resumen_cultivos_dichas_uno": "1 con su cultivo dicho",
    "resumen_cultivos_dichas": "{cuantas} con su cultivo dicho",
    # El pie cuando está puesto el filtro de las que faltan: un filtro sin decir qué está filtrando deja al
    # agricultor creyendo que ha perdido tierras (lo mismo que hace la tabla de tierras con su buscador).
    "resumen_cultivos_filtrado": "{cuantas} de {total} tierras",
    # ── La tabla de la maquinaria (T14, 03/10/2026) ──
    #
    # Los nombres de las columnas son **los del contrato, en una palabra** (§4, S16): máquina, tipo,
    # matrícula o serie, propiedad o alquiler, horas, próxima revisión, documentación y disponibilidad. Un
    # nombre de columna largo se come el ancho de la tabla, y con ocho columnas eso se nota enseguida.
    #
    # **La columna de la próxima revisión puede estar vacía y eso es lo que tiene que pasar**: si el programa
    # no tiene la fecha en ningún papel, escribe «falta el dato» y no una fecha calculada. Es la trampa del
    # ticket, y se ve en la tabla antes que en ningún sitio.
    "maquinaria_etiqueta": "Tu maquinaria, en una tabla",
    "maquina": "Máquina",
    "tipo_maquina": "Tipo",
    "matricula_o_serie": "Matrícula o serie",
    "propiedad": "Tuya o alquilada",
    "horas": "Horas",
    "proxima_revision": "Próxima revisión",
    "documentacion": "Papeles",
    "disponibilidad": "Disponibilidad",
    "resumen_maquinaria_uno": "1 máquina",
    "resumen_maquinaria": "{cuantas} máquinas",
    "resumen_maquinaria_filtrado": "{cuantas} de {total} máquinas",
    "resumen_maquinaria_avisos_uno": "1 con algo que mirar",
    "cuentas_concepto": "Qué fue",
    "cuentas_coste": "Lo que costó",
    "cuentas_va_a": "Va a",
    "cuentas_pagado": "Pagado",
    "cuentas_pendiente": "Falta por pagar",
    "cuentas_estado": "Cómo está",
    "cuentas_acciones": "Acciones",
    "cuentas_tierra": "Una tierra",
    "cuentas_cultivo": "Un cultivo",
    "resumen_cuentas": "{cuantas} gastos · {total} de coste conocido",
    "resumen_cuentas_uno": "1 gasto · {total} de coste conocido",
    "resumen_cuentas_filtrado": "{cuantas} de {total} gastos",
    # --- La tabla de los movimientos del banco (T20, 06/10/2026) ---
    "bancos_etiqueta": "Los movimientos del banco, en una tabla",
    "bancos_fecha": "El día",
    "bancos_concepto": "Qué fue",
    "bancos_cuenta": "La cuenta",
    "bancos_importe": "El importe",
    "bancos_estado": "Cómo está",
    "bancos_por_conciliar": "Le queda por cuadrar",
    "bancos_abrir": "¿CONTRA QUÉ PAPEL VA?",
    # El pie de la lista, con singular y plural (`conCuenta` busca `<base>_uno` y `<base>`, y rellena
    # `{cuantos}`): «Tienes 1 movimientos» es lo primero que hace desconfiar de un programa.
    "bancos_resumen_uno": "Tienes 1 movimiento",
    "bancos_resumen": "Tienes {cuantos} movimientos",
}

# ── El panel de detalle, al lado de la tabla (fase 3, 30/09/2026) ──
#
# POR QUÉ EXISTE. En el ordenador, la lista y su ficha van juntas: se toca el nombre de una tierra y se ve
# al lado, sin cambiar de pantalla. Es la mitad de lo que hace que una tabla sirva (lo pidió David: «una
# aplicación de gestión»), y aquí están sus tres frases.
PANEL: dict[str, str] = {
    "etiqueta": "La ficha de lo que has elegido",
    "tierra": "La tierra que has elegido",
    "tierra_pueblo": "Pueblo",
    # Lo que se lee cuando no hay nada elegido: **dice qué hacer**, no se queda en blanco.
    "vacio": "Toca el nombre de una tierra de la lista y la verás aquí, con sus datos.",
    # La ficha de un producto del almacén, en el mismo panel (30/09/2026): la misma pieza, otra lista.
    "producto": "El producto que has elegido",
    "producto_vacio": "Toca el nombre de un producto de la lista y lo verás aquí, con sus cuentas.",
    # El rótulo de la fila que dice **de dónde sale** el número de lo comprado. Va en el panel porque un
    # número sin su origen no se puede comprobar, y esto ya lo decía el servidor (`comprado_de_donde`) sin
    # que ninguna pantalla lo enseñara.
    "producto_origen": "De dónde sale",
    # Lo que se enseña en el panel de una tierra, debajo de sus datos: **sus últimos apuntes del año**. Lo pide
    # el diseño de escritorio de esta pantalla (`docs/stitch/escritorio/estructura.png`) y es la pregunta que
    # se hace al mirar una tierra en el despacho.
    "tierra_ultimos": "Lo último que le has hecho",
    # **El botón que abre su historia** (T15, 05/10/2026): lo que ha pasado en esa tierra —sus trabajos
    # hechos, lo que queda previsto y lo que consta que ha costado—. Se llama **igual que el título de la
    # pantalla a la que lleva** (`AGENDA.historia_titulo`), que es la regla de la casa con los botones que
    # abren un sitio: el mismo nombre en el renglón y en la pantalla. Se pinta en mayúsculas porque es un
    # botón, no una frase.
    "tierra_historia": "LO QUE HA PASADO EN ESTA TIERRA",
}


# ── El armazón de la aplicación en el ordenador (30/09/2026) ──
#
# POR QUÉ EXISTE. Hasta hoy la aplicación era **una columna de móvil** también en el ordenador: sin menú,
# sin barra con la finca y el año, y para llegar a las 64 tierras había que saber que estaban detrás de un
# botón de la pantalla de inicio. David lo dijo claro: «no es una app usable de gestión». Estas son las
# palabras del armazón nuevo (el menú lateral y la barra de arriba), y son las del agricultor: se habla de
# «la finca» y «el año», y el menú se llama «menú» porque es lo que dice cualquiera.
MENU: dict[str, str] = {
    "titulo": "Menú",
    "etiqueta": "El menú de la aplicación",
    # El primer módulo: en el ordenador es lo que se ve al entrar (en el móvil, «Mi cuaderno»).
    "panel": "Panel",
    # **No hay «Finca» en la barra, y es una decisión** (30/09/2026). En este programa la finca se
    # identifica por **el nombre del titular**: `Explotacion.nombre` es el campo «¿Cómo te llamas?» de
    # «Mis datos» y no hay un nombre de finca aparte (comprobado: la cuenta de David devuelve «David Pérez
    # Velasco»). Poner «Finca: David Pérez Velasco» sería decir una cosa que no es. El día que una finca
    # tenga nombre propio —o cuando una cuenta entre en varias, que ya se puede—, ese dato vuelve a la
    # barra: el hueco está hecho y solo falta el dato.
    "cuenta": "Tu cuenta",
    "sin_cuenta": "Tu cuenta",
    # En la barra se dice «Campaña», que es lo que pone el cuaderno de la Junta; en la pantalla de los
    # años se le llama «el año», que es como lo dice el agricultor.
    "campana": "Campaña",
    "sin_campana": "Sin año",
    "apuntar": "APUNTAR",
    "letra": "A+",
    "letra_etiqueta": "Poner la letra más grande",
    "salir": "Salir",
    "salir_etiqueta": "Salir de la cuenta",
    # ── Los grupos del menú (07/10/2026, del encargo del rediseño) ──
    #
    # El menú tiene 21 renglones: seguidos, no se encuentra nada. Se agrupan por donde el agricultor los
    # busca, **sin pantallas de por medio** (el encargo lo dice así: «la agrupación es visual, no introduce
    # pantallas intermedias obligatorias»).
    #
    # **Y no hay grupo «Normativa»**, que el encargo nombra: no existe esa pantalla (la biblioteca de
    # obligaciones con su fuente y su vigencia está por hacer). Un renglón que no lleva a ninguna parte es
    # peor que no tenerlo.
    "grupo_inicio": "Inicio",
    "grupo_campo": "El campo",
    "grupo_gestion": "La gestión",
    "grupo_cuaderno": "El cuaderno",
    "grupo_ajustes": "Ajustes",
    # El botón que abre el menú cuando no cabe a la izquierda (el móvil y las ventanas estrechas).
    "abrir": "Menú",
    "abrir_etiqueta": "Abrir el menú de la aplicación",
    "cerrar": "Cerrar el menú",
    "cerrar_etiqueta": "Cerrar el menú",
}


# ── La barra de arriba, con el contexto (T04, 03/10/2026) ──
#
# **Por qué ahora sí hay «Finca» en la barra.** El comentario de `MENU` (arriba) decía que no la había a
# propósito, porque la finca se identificaba por el nombre del titular y poner «Finca: David Pérez Velasco»
# sería decir una cosa que no es. Aquello era verdad con **una** finca; desde la ronda 89 una cuenta puede
# entrar en **varias**, y entonces «en cuál estoy apuntando» es lo primero que hay que saber para no apuntar
# en la que no es. El dato sale de `Explotacion.nombre` (el mismo que ya se enseñaba como cuenta), así que el
# rótulo honesto es «Finca» cuando hay más de una, y el nombre de la finca cuando hay una sola.
#
# Los botones de cambiar de finca y de campaña son los mismos que los de la pantalla «quién entra»: la barra
# no inventa un camino nuevo, usa el que ya existe. **Y el de campaña no cambia nada**: el servidor no tiene
# forma de decir «trabaja en el año 2023» (`/api/campanas/actual` devuelve siempre la más nueva), así que la
# barra ofrece la campaña como dato y no ofrece elegirla (ver `pintarMarco` en `app.js`).
# ── La búsqueda global (07/10/2026, del encargo del rediseño) ──
#
# La caja de la cabecera y la pantalla que enseña lo que encuentra. **La puerta del servidor ya está**
# (`GET /api/buscar`: tierras, gastos, personas, máquinas y papeles, cada grupo con su prueba), así que
# estas son las palabras que le faltan a la pantalla.
#
# Dos cosas que se dicen aquí y no en la pantalla, porque son decisiones: **cuánto hay que escribir para
# que busque** (dos letras: con una saldría casi todo, y una lista con casi todo no ayuda a encontrar) y
# **cómo se llama cada grupo**, que es el nombre que el agricultor le da a esas cosas.
BUSCAR: dict[str, str] = {
    "titulo": "Buscar",
    "caja": "Buscar en tu cuaderno",
    "pista": "Escribe al menos dos letras. Busca en tus tierras, tus gastos, tus papeles, tus personas y tus máquinas.",
    "boton": "BUSCAR",
    # Lo que se dice cuando no se ha buscado nada todavía: no es un error, es que no se ha pedido nada.
    "sin_buscar": "Escribe lo que buscas y pulsa BUSCAR.",
    # Y cuando se ha buscado y no hay nada. **En positivo y sin culpar a nadie**: no hay nada, y ya está.
    "sin_resultados": "No hay nada que se llame así.",
    # Los nombres de los grupos, que son los que el agricultor usa para esas cosas.
    "grupo_tierras": "Tierras",
    "grupo_gastos": "Gastos",
    "grupo_personas": "Personas y empresas",
    "grupo_maquinas": "Máquinas",
    "grupo_papeles": "Papeles",
    # Y lo que se dice cuando un grupo se ha cortado: un buscador que enseña diez de cuarenta y no avisa
    # hace creer que solo hay diez.
    "cortado": "Hay más de los que caben aquí: afina lo que buscas.",
    # Lo que hace el botón de cada resultado: un resultado que no lleva a ninguna parte no es un
    # resultado, es un cartel.
    "ver": "VER",
    "cuantos_uno": "1 resultado",
    "cuantos": "{cuantos} resultados",
}


MARCO: dict[str, str] = {    "finca": "Finca",
    "sin_finca": "Sin finca",
    "cambiar_campana": "Cambiar de campaña",
    "cambiar_finca": "Cambiar de finca",
    # ── Lo que falta por apuntar, en la barra (07/10/2026) ──
    #
    # El encargo del rediseño pide que el contexto lleve «lo pendiente» a la vista: el agricultor tiene que
    # poder saber **desde cualquier pantalla** si le falta algo por apuntar, y llegar a ello de un toque.
    # La frase va entera (singular o plural) porque quien la monta es `app.js`, que es quien tiene la
    # cuenta; aquí solo están las dos formas, como en el resto de la aplicación.
    "pendiente_uno": "Te falta 1 cosa por apuntar",
    "pendientes": "Te faltan {cuantas} cosas por apuntar",
    "pendientes_etiqueta": "Ver lo que falta por apuntar",
}


# ── La dirección que no lleva a ninguna parte (T04, 03/10/2026) ──
#
# Existe porque una aplicación con direcciones tiene tres casos que **no son el mismo** y que hasta ahora no
# se podían ni decir: una dirección que no es de ninguna pantalla (`#/lo-que-sea`), una ficha que no está en
# el cuaderno de este agricultor (el servidor contesta 404 y **no** dice si existe en otra finca: eso es a
# propósito) y una dirección que no se ha podido comprobar **por falta de cobertura**. Confundir el tercero
# con el segundo sería decirle a alguien que su tierra no existe cuando lo que pasa es que no hay red.
DIRECCION: dict[str, str] = {
    "titulo": "Esa dirección no lleva a ninguna parte",
    "explica": (
        "El enlace que has abierto no es de ninguna pantalla del cuaderno, o la ficha que pide no está en "
        "tu cuaderno. Comprueba la dirección o vuelve al principio."
    ),
    "sin_cobertura_titulo": "Esto no lo he podido comprobar",
    "reintentar": "VOLVER A INTENTARLO",
    "volver": "VOLVER AL PRINCIPIO",
}


# ── El panel de mando del ordenador (fase 4, 30/09/2026) ──
#
# POR QUÉ EXISTE. Es la pantalla que se abre al entrar desde un ordenador, y hasta hoy era **la pantalla de
# inicio del móvil estirada**: ocho botones de ancho completo, uno debajo de otro, en un monitor de 1440 px.
# David lo pidió así desde el principio («una versión para pc que parezca una aplicación de gestión») y es la
# fase que más se nota: lo que hace un programa de gestión al abrirse es enseñar **el estado** de todo —cuatro
# números del año, lo que falta por completar con su botón— y no una lista de botones que hay que pulsar para
# enterarse.
#
# El diseño del que sale está en `docs/stitch/escritorio/panel.png` (pedido a Stitch con nuestro `DESIGN.md`).
# Y **una cosa del diseño NO se ha copiado, a propósito**: la tarjeta del «gasto en fitosanitarios» en euros,
# porque ese número no existe en el programa (las líneas de factura traen importe, pero no hay un gasto por
# producto sumado para el año). En su lugar va la tarjeta de las tierras, que es un dato que sí hay y que
# dice lo que hay que hacer («10 sin decir qué tienen este año»).
PANEL_DE_MANDO: dict[str, str] = {
    "titulo": "Panel de mando",
    "explica": (
        "Cómo va el cuaderno de este año, de un vistazo: lo que llevas apuntado, lo que falta por "
        "completar y lo último que has hecho."
    ),
    # ── Las cuatro tarjetas de números ──
    "apuntes": "Apuntes este año",
    "hectareas": "Hectáreas tratadas",
    "hectareas_detalle": "de {hectareas} ha de tus tierras",
    "vendido": "Lo que has vendido",
    "tierras": "Tus tierras",
    # El detalle de la tarjeta de las tierras: lo que hay que arreglar, en una línea. Con su singular, que
    # «1 sin decir qué tienen» es lo primero que hace desconfiar de un programa.
    "tierras_sin_decir_uno": "1 sin decir qué tiene este año",
    "tierras_sin_decir": "{cuantas} sin decir qué tienen este año",
    "tierras_al_dia": "Todas con su cultivo dicho",
    # ── Lo que falta por completar ──
    "falta_titulo": "Lo que falta por completar",
    # Lo mismo que dice el cuaderno del móvil, contado aquí para la esquina del bloque. **Ojo con el
    # nombre de las claves**: el ayudante `conCuenta` busca `<base>_uno` para el singular y `<base>` para
    # el plural (aquí ya se tropezó una vez con `_una`/`_varias`).
    "falta_uno": "1 cosa por completar",
    "falta": "{cuantas} cosas por completar",
    "falta_vacio": "No te falta nada: el cuaderno está al día.",
    # ── Los últimos apuntes ──
    "ultimos_titulo": "Los últimos apuntes",
    "ultimos_vacio": "Todavía no has apuntado nada este año.",
    "ver_todos_uno": "Ver el apunte del año",
    "ver_todos": "Ver los {cuantas} apuntes del año",
    # ── Apuntar algo de hoy ──
    "apuntar_titulo": "Apuntar algo de hoy",
    # ── El cierre ──
    "cierre_titulo": "Cierre y trámites",
    "cierre_explica": (
        "Lo que se saca del programa: el cuaderno en papel para imprimir, los datos en un fichero y la "
        "firma del año."
    ),
}


CAMPANAS: dict[str, str] = {
    "titulo": "Los años de mi cuaderno",
    "explica": (
        "Tu cuaderno se lleva por años: lo que apuntas va al año en el que estás. Aquí ves los años "
        "que tienes y puedes arreglar o quitar el que esté mal."
    ),
    # El rótulo pequeño de cada ficha, encima del año (diseño de Stitch de esta pantalla).
    "rotulo": "Año del cuaderno",
    "el_que_llevo": "Estás apuntando en este",
    "cerrado": "Año cerrado",
    "abierto": "Año abierto",
    "empieza": "Empieza",
    "termina": "Termina",
    # **Un año no se puede quitar si tiene cosas dentro.** Se dice antes de que lo intente, y con el
    # número delante, que es lo que explica por qué: es el año entero del cuaderno.
    "dentro_uno": "Tiene 1 cosa apuntada dentro",
    "dentro_varios": "Tiene {cuantos} cosas apuntadas dentro",
    "vacio": "No tiene nada apuntado",
    "no_se_puede_quitar": (
        "Aquí dentro hay cosas apuntadas: primero quítalas y después podrás quitar el año."
    ),
    # ── Qué tiene dentro, dicho por lo que es (30/09/2026) ──
    #
    # POR QUÉ HIZO FALTA. La tabla de los años decía «Tiene 54 cosas apuntadas dentro» y «mi cuaderno» del
    # mismo año decía «0 apuntes en el cuaderno». Las dos cosas eran verdad (las 54 eran las tierras con su
    # cultivo dicho) y el agricultor no podía entenderlo: se vio en la revisión de la interfaz del
    # 30/09/2026, mirando la aplicación con sus 64 tierras de verdad.
    #
    # Ahora el año dice **los apuntes** (tratamientos, abonos y labores, que es lo que cuenta el cuaderno) y,
    # debajo y en pequeño, lo que hay dentro que no son apuntes: las tierras con su cultivo dicho y las demás
    # cosas. Los cuatro textos llevan número, así que tienen singular y plural.
    "apuntes_uno": "1 apunte",
    "apuntes": "{cuantos} apuntes",
    "cultivo_dicho_uno": "1 tierra con su cultivo dicho",
    "cultivo_dicho": "{cuantas} tierras con su cultivo dicho",
    "otras_cosas_uno": "1 cosa más dentro",
    "otras_cosas": "{cuantas} cosas más dentro",
    # La etiqueta **corta** de «no se puede quitar», para la celda de la tabla: la frase entera ocupaba dos
    # renglones y ponía la fila alta (el mismo fallo que «Falta decirlo» en las tierras y «Cuadra» en el
    # almacén). La frase larga se sigue leyendo en la ficha del año y en la pantalla que pregunta.
    "no_se_puede_quitar_corto": "Hay cosas dentro",
    # Empezar el año siguiente. Faltaba entero: sin esto, cuando llegaba el año nuevo el cuaderno se
    # quedaba en el año viejo y no había ninguna forma de empezar el de verdad.
    "anadir": "EMPEZAR UN AÑO NUEVO",
    "anadir_pista": "Cuando empiece el año que viene, hazlo aquí: lo que apuntes irá a ese año.",
    "guardado": "Año guardado. Ya puedes apuntar en él.",
    "sin_campanas": "Todavía no hay ningún año en tu cuaderno.",
    "abrir": "LOS AÑOS DE MI CUADERNO",
    "pista_anadir": (
        "Un año en tu cuaderno no tiene por qué empezar en enero: muchas cosechas empiezan en "
        "septiembre. Pon el día en que tú empiezas a apuntar ese año."
    ),
}

# **La ficha de una compra** (S11, 09/10/2026). Es la pantalla que junta las cuatro cifras que hasta
# ahora vivían en tres sitios: lo que dice la factura, lo que ha entrado de verdad, lo que se ha pagado
# y lo que queda. Las etiquetas se llaman como se llama cada cosa en el campo —«facturado», «recibido»,
# «pagado», «pendiente»— porque son las palabras con las que el agricultor hace la pregunta.
COMPRA: dict[str, str] = {
    "titulo": "La compra",
    "buscando": "Buscando la compra…",
    "anulada": "Esta factura está anulada: no cuenta.",
    "anulada_con_motivo": "Esta factura está anulada: {motivo}",
    "no_se_sabe": "No se puede saber",
    "nada_todavia": "Nada todavía",
    "un_albaran_sin_numero": "Un albarán sin número",
    "ese_albaran_esta_anulado": "Ese albarán está anulado, así que no metió nada.",
    "las_lineas": "Lo que trae la factura",
    # **Los rótulos de la tabla de líneas** (09/10/2026). La tabla tiene cuatro columnas —qué es, lo
    # facturado, lo que ha entrado y lo que falta— y los encabezados los sirve el servidor como todo lo
    # demás: la pantalla elige el dibujo, no las palabras.
    "col_producto": "Producto",
    "col_facturado": "Facturado",
    "col_ha_entrado": "Ha entrado",
    "col_falta": "Falta",
    "de_ese_pago_va_aqui": "De ese pago, a esta compra: {importe}",
    "facturado": "Facturado",
    "facturado_pista": "Lo que dice la factura del proveedor.",
    "recibido": "Recibido",
    "recibido_pista": "Lo que ha entrado de verdad en el almacén. Lo mete el albarán, no la factura.",
    "pagado": "Pagado",
    "pagado_pista": "El dinero que ya ha salido para esta compra.",
    "pendiente": "Pendiente",
    "pendiente_pista": "Lo que queda por pagar de esta compra.",
    "recibido_de": "Lo que ha llegado",
    "sin_albaran": "De esta compra no ha entrado nada todavía.",
    "los_albaranes": "Los albaranes de esta compra",
    "falta_por_llegar": "Falta por llegar",
    "de_la_linea": "De esta línea han entrado {recibido} de {facturado} {unidad}.",
    "linea_completa": "De esta línea ha entrado todo.",
    "no_se_sabe_la_linea": "De esta línea no se puede saber cuánto ha entrado.",
    "pero_ha_llegado": "Lo que sí ha llegado viene en otra unidad: {cuanto}.",
    "el_dinero": "El dinero de esta compra",
    "sin_gasto": (
        "De esta factura todavía no hay ningún gasto apuntado, así que no se puede decir cuánto se ha "
        "pagado. Apunta el gasto en «Gastos» y enlázalo con esta factura."
    ),
    "los_gastos": "Los gastos",
    "los_pagos": "Los pagos",
    "ver_el_albaran": "VER EL ALBARÁN",
    "ver_el_gasto": "VER EL GASTO",
    "ver_la_compra": "VER LA COMPRA",
    "volver_a_las_facturas": "VOLVER A MIS FACTURAS",
    "sin_lineas": "Esta factura no trae líneas apuntadas.",
}

FACTURAS: dict[str, str] = {
    "titulo": "Mis facturas",
    "resumen_cifras": "Los números de tus facturas",
    "numero_de_facturas": "Facturas",
    "sin_papel_numero": "Sin el papel",
    "explica": (
        "Aquí guardas las facturas de lo que compras. Hazle una foto al papel o sube el fichero "
        "que te manda el proveedor: el programa lee lo que pone y te lo enseña para que lo "
        "confirmes."
    ),
    "para_que_sirven": (
        "Sirven para tres cosas: saber cuánto producto tienes comprado, rellenar el cuaderno "
        "cuando te pida la empresa que te lo vendió y el número de factura, y tener el papel a "
        "mano si te lo piden."
    ),
    "anadir": "AÑADIR UNA FACTURA",
    "que_fichero": "La factura: una foto o el fichero del proveedor",
    "como_se_hace": (
        "Hazle la foto al papel entero, con luz y sin torcerlo. Si tienes el fichero, súbelo: se "
        "lee mejor y no hay que adivinar nada."
    ),
    "leyendo": "Leyendo la factura…",
    "leer": "LEER LA FACTURA",
    "a_mano": "ESCRIBIRLA A MANO",
    "sin_conexion": (
        "Para leer la factura hace falta conexión. El fichero lo tienes en tu móvil: prueba "
        "cuando tengas cobertura."
    ),
    "no_se_pudo": "No se ha podido leer la factura. Prueba otra vez o escríbela a mano.",
    # El trato claro (ronda 90, del diseño de Stitch de «añadir una factura»): es la duda que tiene con el
    # papel en la mano —«¿esto me lo va a apuntar sin preguntarme?»—, y la respuesta es que no. El programa
    # solo intenta leerlo; lo que se guarda es lo que él confirme en la pantalla siguiente.
    "trato_claro": (
        "El programa solo intenta leer el papel. Nada se guarda en el cuaderno hasta que tú lo mires en "
        "pantalla y digas que está bien."
    ),
    "sin_proveedor": "Sin decir quién",
    "guardando": "Guardando la factura…",
    "interpretacion_titulo": "Esto es lo que he leído",
    "interpretacion_pista": (
        "Míralo y corrige lo que esté mal. Lo que se guarda es lo que tú digas, no lo que yo haya "
        "entendido."
    ),
    # Corregir una factura que ya está guardada (ronda 93). Es la misma pantalla que la de arriba —los
    # mismos campos, las mismas líneas— y por eso los textos son hermanos de aquellos: lo que cambia es
    # que aquí **no se ha leído nada**, se está arreglando lo que ya está en el cuaderno. El título no
    # puede decir «esto es lo que he leído» (sería mentira: nadie ha leído nada), y la pista dice lo que
    # de verdad le importa al agricultor antes de tocar nada: **lo de antes no desaparece**.
    "corregir_titulo": "Esto es lo que tienes guardado",
    "corregir_pista": (
        "Cambia lo que esté mal y guarda. Lo que había antes se queda apuntado en el cuaderno."
    ),
    "corregir_confirmar": "SÍ, GUARDAR LOS CAMBIOS",
    # Volver, desde una corrección, es volver **a la lista de facturas** (de donde se salió al pulsar
    # CORREGIR), no a «añadir una factura». El botón lo dice para que no haya duda de adónde lleva.
    "corregir_volver": "VOLVER A MIS FACTURAS",
    "avisos_titulo": "Mira esto antes de guardar",
    "de_donde_sale_la_lectura": "Leída de",
    "leida_pdf": "El fichero que traía el texto",
    "leida_foto": "Una foto (repasa las palabras con tilde)",
    "leida_escaneo": "Un papel escaneado (repasa las palabras con tilde)",
    "leida_mano": "Escrita a mano por ti",
    "campo_proveedor": "¿Quién te lo ha vendido?",
    "campo_proveedor_pista": "El nombre de la empresa, como viene en la factura",
    "campo_nif": "Su NIF",
    "campo_numero": "¿Qué número tiene la factura?",
    "campo_numero_pista": "Lo pide el cuaderno, así que no lo dejes en blanco",
    "campo_fecha": "¿De qué día es?",
    "campo_base": "Base imponible",
    "campo_base_pista": "Lo que suman los productos, sin el IVA",
    "campo_iva": "Cuota de IVA",
    "campo_tipo_iva": "Tipo de IVA (%)",
    "campo_total": "Total de la factura",
    "campo_notas": "¿Quieres apuntar algo más?",
    "lineas_titulo": "Lo que has comprado",
    "lineas_pista": (
        "Cada línea es un producto. Si alguna no te cuadra, corrígela o bórrala antes de guardar."
    ),
    "linea_descripcion": "Qué es",
    "linea_cantidad": "Cuánto",
    "linea_unidad": "En qué se mide",
    "linea_precio": "A cómo",
    "linea_importe": "Cuánto suma",
    "linea_producto": "¿Es uno de tus productos?",
    "linea_crear_producto": "No lo tengo apuntado: créalo con estos datos",
    "linea_registro": "Número de registro que viene en la factura",
    "linea_sin_producto": "No es de la cesta (una reparación, unas botas…)",
    "linea_sugerida": "Es este: {producto}, {como}",
    "linea_cuadra": "La cuenta cuadra",
    "linea_no_cuadra": "La cuenta no cuadra: mira la cantidad, el precio y el importe",
    # La etiqueta de la línea que hay que revisar (ronda 90, del diseño de Stitch de esta pantalla): el aviso
    # va dentro de la línea, y con tres o cuatro líneas se acaba leyendo la pantalla entera para saber cuál es.
    "revisar_numeros": "Revisar números",
    "linea_anadir": "AÑADIR OTRA LÍNEA",
    "linea_quitar": "QUITAR ESTA LÍNEA",
    "confirmar": "SÍ, GUARDAR ESTA FACTURA",
    "volver": "VOLVER",
    "guardada": "Factura guardada.",
    "guardada_pista": (
        "Ya cuenta para saber cuánto producto tienes comprado. La verás en «lo que tengo en el "
        "almacén»."
    ),
    "ya_estaba": (
        "Esta misma factura ya la has subido (nº {numero}). Si la guardas otra vez, la contarás dos "
        "veces."
    ),
    "sin_facturas": "Todavía no has subido ninguna factura.",
    "sin_facturas_pista": (
        "Cuando subas la primera, aquí verás lo que has comprado y de quién."
    ),
    "ver_almacen": "VER LO QUE TENGO EN EL ALMACÉN",
    "anular": "ANULAR ESTA FACTURA",
    "anular_pregunta": "¿Por qué la anulas?",
    # Lo que hace ANULAR (ronda 93): desde esta ronda la factura **también se puede borrar**, así que
    # decir «la factura no se borra» ya no es verdad. Lo que sí dice este texto, y es lo que importa
    # aquí, es qué queda al anular: la factura sigue en la lista, con su motivo, y deja de contar.
    "anular_pista": "La factura se queda en la lista, con su motivo, y deja de contar.",
    "anulada": "Anulada: {motivo}",
    "falta_motivo": "Escribe por qué la anulas.",
    "sin_fichero": "Esta factura no tiene ni la foto ni el fichero.",
    # La foto del papel, por factura (ronda 90, del diseño de Stitch de esta pantalla). El programa sabe
    # desde siempre si el papel está guardado (`tiene_fichero`) y **no lo decía en ninguna parte**: para
    # una inspección, el papel es justo lo que se pide. Y el botón de verlo y el de subirlo tampoco
    # existían, aunque los dos caminos están en el servidor desde la ronda 40: `VER LA FACTURA` y
    # `SUBIR LA FOTO DEL PAPEL` estaban escritos y sin puerta.
    "papel_guardado": "Foto del papel guardada",
    # La etiqueta corta de la tabla: en la ficha del móvil cabe la frase entera —«Esta factura no tiene ni
    # la foto ni el fichero.»—, pero en una celda de la tabla esa frase ocupa cinco renglones y se come la
    # columna. La frase larga **no se tira**: sigue en su ficha, y aquí se dice lo mismo en tres palabras.
    "papel_falta": "Falta el papel",
    "subir_el_papel": "SUBIR LA FOTO DEL PAPEL",
    # Cuántas hay, como en «mis cosas» y en el almacén (ronda 84): va en singular y en plural.
    "cuantas_uno": "1 factura guardada",
    "cuantas": "{cuantas} facturas guardadas",
    "ver_fichero": "VER LA FACTURA",
    "cuadre_titulo": "Lo comprado y lo echado",
    "cuadre_pista": (
        "Con esto se ve si cuadra lo que has comprado con lo que has echado. No siempre se puede "
        "restar: si compras en botes y echas en litros, hacen falta más cuentas."
    ),
    "cuadre_comprado": "Comprado",
    "cuadre_gastado": "Echado",
    "cuadre_queda": "Te queda",
    "de_las_facturas": "Según tus facturas",
    "de_la_ficha": "Según lo que apuntaste en el producto",
    "cuantas_compras": "{cuantas} compra(s)",
}


# Los datos del titular y de la finca: la **portada del cuaderno de la Junta** (su hoja 1.1). Son
# cuatro datos que se ponen una vez y valen para todos los años, y sin ellos esa hoja sale con
# huecos. Se llaman «Mis datos» y no «Datos de la explotación» porque es lo que son: los suyos.
MIS_DATOS: dict[str, str] = {
    "titulo": "Mis datos",
    "explica": (
        "Estos son los datos que van en la primera hoja del cuaderno: quién eres y cómo se llama tu "
        "explotación. Se piden una vez y valen para todos los años."
    ),
    "nombre": "¿Cómo te llamas?",
    "nombre_pista": "Como viene en el cuaderno de la Junta",
    "nif": "Tu NIF",
    "nif_pista": "Con la letra. Es lo que se compara con tu certificado al entrar",
    "registro_autonomico": "Nº de registro de tu explotación",
    "registro_autonomico_pista": (
        "Lo trae tu cuaderno de la Junta, arriba del todo. Es el que se pone en la portada"
    ),
    "registro_nacional": "Nº de registro nacional (si lo tienes)",
    "registro_nacional_pista": "Si no lo sabes, déjalo en blanco",
    "direccion": "Tu dirección",
    "direccion_pista": "La calle y el número, como en el cuaderno",
    "localidad": "Tu pueblo o ciudad",
    "codigo_postal": "Código postal",
    "provincia": "Provincia",
    "municipio": "Pueblo donde tienes las tierras",
    # **A13 (05/10/2026): la pregunta que no existía.** Este campo estaba en el modelo desde el primer día,
    # **salía en el documento que se firma** y **apagaba la comprobación ecológica**… y no había forma de
    # contestarlo en ninguna pantalla: nacía en `False`, o sea «no soy ecológico», sin que nadie lo hubiera
    # dicho. Ahora se pregunta, con sus tres respuestas, y «no lo sé» es una de ellas.
    "produccion_ecologica": "¿Tu finca es de producción ecológica?",
    "produccion_ecologica_pista": (
        "Si no lo sabes, déjalo en «no lo sé»: mientras no conste, el programa te avisará de que no ha "
        "podido comprobar si un producto vale para ecológico"
    ),
    "municipio_pista": "Si tienes tierras en varios, pon el principal",
    "telefono": "Un teléfono",
    "telefono_pista": "Por si hay que avisarte de algo del cuaderno",
    "correo": "Tu correo",
    "guardar": "GUARDAR MIS DATOS",
    "guardado": "Tus datos están guardados. La portada del cuaderno ya los lleva.",
    "lo_que_falta": "Lo que le falta a la portada: {cuales}",
}


# El registro electrónico: qué es, dónde se apunta y los enlaces oficiales para lo que hay que
# traer de fuera.
#
# David preguntó literalmente «¿a qué se refiere con registro electrónico? ¿dónde debo registrar los
# apuntes?». Esto es la respuesta, dentro de la aplicación y en cristiano, con la dirección de cada
# sitio por si hay que ir.
#
# Las fechas salen de la ley y están comprobadas con su cita en `docs/LO_QUE_OBLIGA_LA_LEY.md`.
REGISTRO_ELECTRONICO: dict[str, object] = {
    "titulo": "Dónde apunto lo que hago",
    "que_es": (
        "El registro electrónico es lo mismo que apuntas ahora en el papel, pero guardado en un "
        "programa. En vez de escribir en el cuaderno con el bolígrafo, lo apuntas aquí."
    ),
    "donde": (
        "Lo apuntas aquí, en esta aplicación, o en la aplicación de la Junta (el Cuecyl). Las dos "
        "valen: la ley permite llevar el cuaderno con un programa tuyo si tiene todo lo que pide."
    ),
    "desde_cuando": (
        "Hasta el 31 de diciembre de 2026 puedes seguir apuntando en papel. Desde el 1 de enero de "
        "2027 tiene que ser electrónico: o sea, apuntado en un programa como este."
    ),
    "es_voluntario": (
        "Una cosa es apuntarlo y otra mandarlo. Apuntarlo es obligatorio. Mandarlo a la Junta por "
        "internet es voluntario: si no lo mandas, no pasa nada, pero tienes que poder enseñarlo."
    ),
    "enlaces_titulo": "Los sitios oficiales, para lo que hay que traer de fuera",
    "enlaces": [
        {
            "texto": "Descargar tu cuaderno de la Junta (Cuecyl)",
            "url": "https://particulares.ayg.jcyl.es",
        },
        {
            "texto": "Actualizar tus parcelas y tus cultivos (Reacyl)",
            "url": (
                "https://agriculturaganaderia.jcyl.es/web/es/"
                "registro-explotaciones-agrarias-castilla.html"
            ),
        },
        {
            "texto": "La Solicitud Única de las ayudas (PAC)",
            "url": "https://www.jcyl.es/web/es/temas/agricultura-ganaderia/pac.html",
        },
        {
            "texto": "Tu maquinaria y su inscripción en el ROMA",
            "url": "https://www.mapa.gob.es/es/agricultura/temas/medios-de-produccion/maquinaria-agricola/",
        },
        {
            "texto": "Productos autorizados y su número de registro (MAPA)",
            "url": (
                "https://www.mapa.gob.es/es/agricultura/temas/sanidad-vegetal/"
                "productos-fitosanitarios/registro-productos/"
            ),
        },
        {
            "texto": "Las fechas y las obligaciones, en el BOE",
            "url": "https://www.boe.es/buscar/act.php?id=BOE-A-2012-11605",
        },
        {
            "texto": "Las tablas oficiales del cuaderno digital (FEGA)",
            "url": "https://www.fega.gob.es/es/siex/documentacion-tecnica-agricola-siex",
        },
    ],
}


def con_cuenta(diccionario: dict, base: str, cuantos: int) -> str:
    """El texto de una cuenta, en singular o en plural (rediseño de la ronda 84).

    **Por qué existe.** Muchos textos llevan el número delante —«Tienes {cuantos} papeles guardados»,
    «A {cuantos} parcelas les falta decir qué tienen este año»— y con uno se leían fatal: «Tienes 1 papeles
    guardados». El proyecto ya tiene esa regla escrita desde la primera ronda («1 apuntes es lo primero que
    hace desconfiar de un programa»), pero solo se cumplía en los mensajes que pasan por
    `mensaje_con_cuenta`; los demás textos se quedaban con el plural.

    El singular se escribe al lado del plural, con la terminación `_uno`; el plural es el de siempre (o su
    terminación `_varios`, si el texto se llama de otra manera). Si falta el singular, se usa el de siempre
    con el número delante: es lo que hacía antes y así no se rompe nada en pantalla —pero la prueba
    `TestSingularYPlural` exige que esté, para que no vuelva a pasar—.
    """
    clave = f"{base}_uno" if cuantos == 1 else f"{base}_varios"
    plantilla = diccionario.get(clave) or diccionario.get(base) or ""
    return plantilla.format(cuantos=cuantos)


def textos_visibles() -> list[str]:
    """Todos los textos que puede llegar a leer un agricultor.

    Lo usa `test_sin_jerga` para comprobar de una vez que no se ha colado ninguna
    palabra rara. Es la única forma de que la regla aguante con el tiempo: revisar
    a ojo una pantalla cada vez no funciona.

    Incluye el vocabulario de la interfaz (`PANTALLA_INICIO`, `ETIQUETAS`, `TRABAJOS`,
    `ACCIONES`, `INTERFAZ`), que es lo que se sirve por `/api/interfaz`. Si alguien
    añade un texto nuevo y no lo mete aquí, el test deja de cubrirlo: por eso las
    estructuras se recorren enteras en vez de listarlas a mano.
    """
    textos: list[str] = []
    textos.extend(PORQUE.values())
    # Los títulos cortos de cada porqué y de cada punto de la ley (ronda 83) los lee el agricultor igual que
    # los textos, así que pasan por el mismo test de jerga.
    textos.extend(PORQUE_TITULOS.values())
    textos.extend(MENSAJES.values())
    for ayuda in AYUDA.values():
        textos.extend(ayuda.values())
    textos.extend(_recoger(PANTALLA_INICIO))
    textos.extend(_recoger(PANTALLA_ENTRAR))
    textos.extend(_recoger(PANTALLA_CUADERNO))
    textos.extend(_recoger(PANTALLA_AYUDA))
    textos.extend(_recoger(TRABAJOS))
    # Las prácticas de «otro trabajo» también las lee el agricultor, así que también pasan por el
    # test de jerga. Si se quedaran fuera, serían el único texto de pantalla sin revisar.
    textos.extend(_recoger(TRABAJOS_DE_LABOR))
    textos.extend(_recoger(ETIQUETAS))
    textos.extend(ACCIONES.values())
    textos.extend(INTERFAZ.values())
    textos.extend(ROTULOS.values())
    textos.extend(BORRADOR.values())
    textos.extend(MAESTROS.values())
    textos.extend(DICTADO.values())
    textos.extend(CERTIFICADO.values())
    textos.extend(FIRMA.values())
    textos.extend(PLAN.values())
    textos.extend(ANALITICA.values())
    textos.extend(MEDIDAS.values())
    # Lo que se vende: la app oficial lo llama «cosecha comercializada». Se recoge entero con
    # `_recoger` desde el T12 y no con `.values()`: dentro lleva las dos listas cerradas de los
    # tipos de ajuste y de los orígenes de un ajuste (diccionarios), y con `.values()` esos textos
    # llegarían al test de jerga como diccionarios en vez de como frases.
    textos.extend(_recoger(VENTA))
    textos.extend(SIGPAC.values())
    textos.extend(DOCUMENTOS.values())
    textos.extend(CESTA.values())
    # El libro del almacén (T09, 03/10/2026): las palabras de los albaranes, los lotes y los
    # movimientos. Se revisan como todas las demás, y aquí hace falta más cuidado que en ningún
    # sitio: «lote», «caducidad» y «existencia» son palabras que se pueden escribir de diez maneras
    # de mostrador y solo una que entienda un agricultor.
    textos.extend(ALMACEN.values())
    textos.extend(CULTIVOS.values())
    textos.extend(GRUPOS.values())
    # Los títulos y los «todavía no hay nada» de las secciones del cuaderno también los lee el
    # agricultor, así que también pasan por el test de jerga. Si se quedaran fuera, serían los
    # únicos textos que llegan a sus ojos sin revisar.
    textos.extend(LABORES.values())
    textos.extend(PARCELAS.values())
    textos.extend(INSTALACIONES.values())
    textos.extend(MAQUINARIA.values())
    textos.extend(MUNICIPIOS.values())
    textos.extend(MAPA.values())
    textos.extend(CUADERNO_CYL.values())
    textos.extend(FACTURAS.values())
    textos.extend(MIS_DATOS.values())
    # Las palabras de las fincas de una cuenta (ronda 89): también las lee el agricultor.
    textos.extend(FINCAS.values())
    # Corregir y borrar lo que uno ha introducido (ronda 91): son los botones y las preguntas de
    # las pantallas donde se arregla un apunte, así que los lee el agricultor como cualquier otro
    # texto de pantalla.
    textos.extend(CORREGIR.values())
    # Lo que se dice cuando no se ha podido dibujar la pantalla (React no ha llegado a
    # cargarse). Son las palabras que vería un agricultor en el peor momento posible, así que
    # tienen que pasar por el mismo test de jerga que las demás.
    textos.extend(REACT.values())
    # Las versiones del recinto (T05, 02/10/2026): los nombres de las fuentes, los cuatro estados
    # de la comparación y las frases que dicen cómo está un recinto. Las lee el agricultor igual que
    # todo lo demás, así que pasan por el mismo test de jerga.
    textos.extend(VERSIONES_DE_RECINTO.values())
    # Las tierras en el mapa y en la tabla, y las versiones de una tierra (T06, 03/10/2026): las
    # palabras de la pantalla que enlaza la lista con el mapa y de la ficha que compara dos años. Se
    # revisan como todas las demás; si se quedaran fuera, serían los únicos textos sin pasar por el
    # test de jerga.
    textos.extend(TIERRA_Y_MAPA.values())
    textos.extend(VERSIONES_EN_PANTALLA.values())
    # Las semillas y las siembras (T10, 03/10/2026): lo que pone una etiqueta, las dos cifras de una
    # siembra y lo que se dice cuando una de las dos no se sabe. Pasan por el test de jerga como
    # todas las demás: aquí hay palabras de mostrador («poder germinativo», «pureza», «dosis») que
    # hay que decir de manera que se entiendan.
    textos.extend(SEMILLAS.values())
    textos.extend(MENSAJES_DE_LAS_SEMILLAS.values())
    # Los contactos (T11, 03/10/2026): los papeles que puede hacer una persona o una empresa, lo que
    # se dice al proponerle una ficha desde los nombres que ya tiene escritos y lo que se dice cuando
    # dos nombres no se pueden juntar. `_recoger` y no `.values()` porque dentro hay el diccionario de
    # los papeles, y un diccionario dentro de la lista dejaría esos textos sin revisar.
    textos.extend(_recoger(CONTACTOS))
    textos.extend(MENSAJES_DE_LOS_CONTACTOS.values())
    # La factura emitida y el cobro (T12, E6, 03/10/2026): las palabras de las tres pantallas del
    # dinero —la factura nuestra, lo cobrado y los ajustes de una entrega—. `_recoger` y no
    # `.values()` en los dos que llevan dentro sus listas cerradas (los tipos de ajuste y las formas
    # de cobro): con `.values()` esas listas se quedarían sin revisar y son justo las que más
    # importan, porque son las que el agricultor elige con el dedo.
    textos.extend(_recoger(FACTURA_EMITIDA))
    textos.extend(_recoger(COBRO))
    textos.extend(MENSAJES_DE_LAS_VENTAS.values())
    textos.extend(_recoger(REGISTRO_ELECTRONICO))
    textos.extend(_recoger(ETIQUETAS_MAESTRO))
    # **Las columnas de las tablas y la maquinaria** (T14, 03/10/2026).
    #
    # `TABLA` **no estaba aquí**, y era el único diccionario de textos de pantalla que se había quedado
    # fuera del test de jerga: los nombres de las columnas se leen como cualquier otra frase (y «documentación»
    # o «Aplicaciones» son justo las palabras que se cuelan sin que nadie mire). Se añade con la maquinaria,
    # que trae ocho columnas nuevas, y se revisa entero de paso.
    textos.extend(TABLA.values())
    textos.extend(MAQUINARIA_DE_LA_FINCA.values())
    textos.extend(MENSAJES_DE_LA_MAQUINARIA.values())
    # Las cuentas de la explotación (T13, E7, 05/10/2026): lo que ha costado, a qué va, cuánto se ha
    # pagado y qué falta por saber. Se recogen enteros, y con `_recoger` y no con `.values()` porque
    # dentro llevan cuatro diccionarios (las categorías, los métodos de reparto, las formas de pago y
    # los estados de una ayuda): con `.values()` esos textos llegarían al test de jerga como
    # diccionarios en vez de como frases, y son justo los que más se leen.
    textos.extend(_recoger(GASTOS))
    # **La agenda de los trabajos (T15, 05/10/2026).** Igual que los del T13: se recogen enteros para
    # que el test de jerga los mire, que es lo que le pasó a `TABLA` en el T14.
    textos.extend(AGENDA.values())
    # **El extracto del banco y la conciliación (T20, E11, 06/10/2026).** Se recoge entero —con `_recoger`
    # y no con `.values()`— por el mismo motivo que los del T13 y el T15: dentro lleva las cuatro familias
    # de claves compuestas, y `_recoger` las recorre todas. Un texto de pantalla que no pase por aquí es un
    # texto que se lee sin que el test de jerga lo mire.
    textos.extend(_recoger(BANCOS))
    # **La bandeja de los papeles (T08, S10, 06/10/2026).** Se recoge entera, con `_recoger` y no con
    # `.values()`, por el mismo motivo que los del T13, el T15 y el T20: dentro lleva las familias
    # compuestas (`estado_…`, `clase_…`, `que_hacer_…`) y `_recoger` las recorre todas. Un texto de
    # pantalla que no pase por aquí es un texto que se lee sin que el test de jerga lo mire.
    textos.extend(_recoger(BANDEJA))
    return textos


def es_una_direccion(texto: str) -> bool:
    """¿Ese texto es una dirección de internet?

    Hace falta para la revisión de jerga, y no es un atajo: **una dirección no es un texto que lea
    el agricultor**, es la dirección del sitio oficial, y sus palabras las pone la administración
    (por ejemplo, la página del registro de productos del MAPA lleva «productos-fitosanitarios» en
    su propia dirección, y no se puede ni se debe cambiar). Lo que se revisa es lo que se lee en la
    pantalla: el texto del enlace («Productos autorizados y su número de registro»), que sí está
    revisado.
    """
    limpio = (texto or "").strip().lower()
    return limpio.startswith(("http://", "https://"))


def palabras_prohibidas_encontradas(texto: str) -> list[str]:
    """Devuelve qué palabras de la lista negra aparecen en un texto."""
    if es_una_direccion(texto):
        return []
    bajo = texto.lower()
    return [palabra for palabra in PALABRAS_PROHIBIDAS if palabra in bajo]


def ayuda(campo: str) -> dict[str, str] | None:
    return AYUDA.get(campo)


def mensaje(codigo: str, **datos) -> str:
    """Devuelve el mensaje ya rellenado. Falla fuerte si el código no existe.

    Preferimos que reviente en los tests a que salga en pantalla un texto vacío
    delante de un agricultor.
    """
    plantilla = MENSAJES[codigo]
    return plantilla.format(**datos) if datos else plantilla


ZONAS_VULNERABLES_ESTADO = {
    "cargado": (
        "Listado municipal de zonas vulnerables cargado desde el conjunto oficial "
        "de IDECyL basado en el Decreto 5/2020. Confirma la situación de tu parcela "
        "si hay cambios normativos posteriores o dudas sobre sus límites."
    ),
    "sin_datos": (
        "No está cargado el listado de zonas vulnerables. No podemos determinar "
        "si una parcela pertenece a una zona; compruébalo con la Junta."
    ),
}


# --------------------------------------------------------------------------
# La identidad y las versiones del recinto (T05, 02/10/2026)
# --------------------------------------------------------------------------
#
# **Qué es esto.** Una tierra no es siempre la misma cosa: su recinto cambia de forma, de uso y de
# superficie entre campañas, y lo que dice el SIGPAC no es lo que declara el agricultor. Lo cuenta
# entero `app/versiones_de_recinto.py` y la tabla `versiones_de_recinto`.
#
# **De dónde salen las palabras de este bloque.** De aquí y de ningún otro sitio: los nombres de las
# fuentes, los cuatro estados de la comparación (`igual`, `cambiado`, `desaparecido`, `nuevo`, que
# son los del contrato §2.1), lo que se llama cada dato que puede cambiar, y las frases que dicen
# cómo está un recinto. El servicio no escribe ni una frase: pide la clave.
VERSIONES_DE_RECINTO = {
    "titulo": "Las versiones del recinto",
    "explica": (
        "Una tierra puede cambiar de forma, de uso y de superficie de un año a otro, y lo que dice "
        "el SIGPAC no es lo mismo que lo que tú declaras. Aquí se guarda cada versión con su año y "
        "con quién lo dijo, para poder comparar dos años sin perder lo de antes."
    ),
    # Las cuatro fuentes que se pueden guardar, con el nombre con el que las lee el agricultor.
    "fuente_sigpac": "SIGPAC",
    "fuente_cuaderno_de_la_junta": "Cuaderno de la Junta",
    "fuente_agricultor": "Lo que dijiste tú",
    "fuente_medicion_en_campo": "Medido en el campo",
    "sin_fuente": "sin decir de dónde",
    # Los cuatro estados de la comparación.
    "estado_igual": "Igual",
    "estado_cambiado": "Cambiado",
    "estado_desaparecido": "Desaparecido",
    "estado_nuevo": "Nuevo",
    # El estado de revisión de una versión.
    "revision_sin_revisar": "Sin revisar",
    "revision_revisado": "Revisado",
    "revision_con_dudas": "Con dudas",
    # Qué es cada cosa que puede cambiar entre dos versiones. Se usan para decir **por qué** un
    # recinto está cambiado, y son las mismas palabras que salen en la pantalla.
    "campo_referencia": "la referencia",
    "campo_referencia_completa": "que la referencia esté completa",
    "campo_geometria": "la forma del trozo",
    "campo_area_geometria": "el área de la forma",
    "campo_area_sigpac": "la superficie del SIGPAC",
    "campo_area_declarada": "las hectáreas que declaras",
    "campo_uso": "el uso",
    # Cómo está una versión, en una frase. La primera es la que hace visible el grupo «sin forma»
    # del contrato: un recinto sin polígono no se esconde ni se le dibuja nada.
    "como_esta_sin_forma": "Sin forma: no ha venido el polígono",
    "como_esta_referencia_a_medias": "La referencia está a medias: falta el número de recinto",
    # Los solapes. Son tres respuestas y no dos, y el motivo está en `geo.se_solapan`: no es lo
    # mismo «se pisan» que «puede que sí», y ninguna de las dos es «no se sabe».
    "solape_si": "Se pisan: hay parte de uno dentro del otro",
    "solape_puede": "Pueden pisarse: míralos en el mapa",
    "solape_no": "No se pisan",
    "solape_no_se": "No se puede saber: a alguno le falta la forma",
}


# --------------------------------------------------------------------------
# Las tierras de la finca, en el mapa y en la tabla (T06, 03/10/2026)
# --------------------------------------------------------------------------
#
# **Qué es esto.** La pantalla que pide el contrato en su apartado 2.1: las 64 tierras a la vez, en
# una tabla con buscador, filtros, agrupación y selección, y el mapa de la finca al lado, con las dos
# cosas enlazadas (se toca una fila y se enfoca su trozo; se toca un trozo y se enfoca su fila).
#
# **De dónde salen estas palabras.** De aquí y de ningún otro sitio. El componente que las pinta no
# escribe ni una frase: las recibe por propiedades desde `/api/parcelas/vista`, que es el endpoint que
# las sirve junto con los datos. Se revisan con el test de jerga como todas las demás porque están en
# `textos_visibles()`.
#
# **Lo que este bloque NO hace, y se dice:** no hay ni un texto que afirme que una tierra «cumple» ni
# que esté «declarada», ni un porcentaje ni una media. Todo lo que se lee aquí es un recuento de lo
# que hay o el nombre de un dato. La regla de la casa: un dato que no se sabe se queda en blanco.
TIERRA_Y_MAPA: dict[str, str] = {
    "titulo": "Mis tierras, en el mapa y en la tabla",
    "explica": (
        "Aquí están todas tus tierras a la vez. En la lista ves sus hectáreas, su pueblo y lo que "
        "tienen sembrado este año; en el mapa, su forma. Toca el nombre de una tierra y se te enseña "
        "su trozo en el mapa; toca un trozo del mapa y se te enseña su renglón."
    ),
    # --- Buscar y filtrar
    "buscar": "Buscar por su nombre o por su referencia del SIGPAC",
    "buscar_boton": "BUSCAR",
    "filtros_titulo": "Filtros",
    "filtro_cultivo": "Qué tienen sembrado",
    "filtro_municipio": "El pueblo",
    "filtro_revision": "Si lo has revisado",
    "filtro_pac": "Lo que puedes declarar",
    "filtro_todas": "TODAS",
    # Las cuatro opciones del filtro de la PAC. **Ninguna dice «cumple» ni «autorizado»**: son
    # hechos que se pueden comprobar fila a fila (tiene los tres números de la referencia, o tiene
    # hectáreas dichas, o no). La regla del proyecto es que un programa no marca una casilla que
    # nadie ha comprobado.
    "pac_con_referencia": "Con los tres números de la referencia",
    "pac_sin_referencia": "Con la referencia a medias",
    "pac_con_hectareas": "Con hectáreas dichas",
    "pac_sin_hectareas": "Sin hectáreas dichas",
    "quitar_filtros": "QUITAR LOS FILTROS",
    "sin_filtros_titulo": "Con esos filtros no hay ninguna tierra",
    "sin_filtros_pista": (
        "Prueba a quitar alguno. Las tierras no se han ido a ningún sitio: están todas, solo que "
        "ahora mismo no se ven."
    ),
    # --- Agrupar
    "agrupar_titulo": "Agrupar la lista",
    "agrupar_no": "Sin agrupar",
    "agrupar_cultivo": "Por lo que tienen sembrado",
    "agrupar_municipio": "Por pueblo",
    "agrupar_forma": "Por si se les ha medido la forma",
    "grupo_con_forma": "Con su forma medida",
    # **El grupo «sin forma» del contrato.** Una tierra a la que no le ha llegado el polígono no
    # desaparece de la lista ni se le dibuja un cuadro: sale aquí, con estas palabras.
    "grupo_sin_forma": "Sin forma",
    "sin_forma": "SIN FORMA",
    # Y lo que se lee en esa misma columna cuando **sí** se le ha medido: una palabra, porque el color
    # solo no informa (regla de la casa) y un hueco tampoco.
    "con_forma": "Medida",
    "sin_forma_explica": (
        "De esta tierra no ha llegado el polígono, así que no se puede dibujar. Sigue en la lista "
        "con sus datos: lo único que no se sabe es su forma."
    ),
    "sin_cultivo": "Sin decir qué tiene",
    "sin_hectareas": "Sin hectáreas dichas",
    "sin_pueblo": "Sin pueblo dicho",
    # Una tierra sin ninguna versión de este año no está «sin revisar»: está **sin versión**, que es
    # otra cosa. Decir «sin revisar» de ella afirmaría que alguien miró algo.
    "revision_sin_version": "Sin ninguna versión de este año",
    "col_marcar": "Marcar",
    # **Dos cosas que se descubrieron midiendo los datos de verdad del agricultor** (03/10/2026), y
    # que no son precauciones teóricas:
    #
    #  · 65 tierras y solo **60 nombres distintos**: hay dos filas que se llaman
    #    «507/24-1 TRIGO BLANDO (0.46 ha)» y tienen hasta la misma superficie. El programa **no le
    #    cambia el nombre a sus tierras** (el nombre es suyo), pero le dice que está repetido, que es
    #    lo que le hace mirar el número y la referencia para saber cuál está eligiendo.
    #  · 65 tierras y solo **52 referencias distintas**: el cuaderno de la Junta parte un mismo
    #    recinto en varias líneas de cultivo, así que varias filas **son el mismo trozo de tierra** y
    #    comparten su forma. Al tocar el trozo no se elige una fila al azar: se encienden todas y se
    #    dice cuántas son.
    "nombre_repetido": (
        "Hay {cuantas} tierras con este mismo nombre. Míralas por su número y su referencia para "
        "saber cuál es esta."
    ),
    "recinto_compartido": (
        "Esta forma la comparten {cuantas} tierras: el SIGPAC parte un mismo trozo en varias líneas "
        "de cultivo, así que estas {cuantas} están encendidas a la vez."
    ),
    # **Cuando la finca entera no cabe en una imagen del mapa.** El servicio oficial no da una caja de
    # más de medio grado (unos 55 km), y una finca repartida en más que eso no se puede enseñar de
    # una vez. Se dice, en vez de dejar que el agricultor lea «puede ser la cobertura» delante de un
    # fallo que no tiene nada que ver con la cobertura (revisión de T06, D7).
    "hectareas_declaradas_pista": "Las que declaras este año: {hectareas}",
    "no_caben_todas": (
        "Tus tierras están repartidas en más de lo que cabe en una imagen del mapa, así que se ve "
        "una parte. Toca el nombre de una tierra en la lista y el mapa se pone en ella."
    ),
    # --- Seleccionar
    "marcar_todas": "MARCAR LAS QUE SE VEN",
    "desmarcar_todas": "QUITAR LA SELECCIÓN",
    "marcadas_uno": "Has marcado 1 tierra",
    "marcadas_varios": "Has marcado {cuantas} tierras",
    "ninguna_marcada": "No has marcado ninguna tierra.",
    "marcar_esta": "Marcar esta tierra",
    # --- La tabla
    "col_numero": "N.º",
    "col_nombre": "Nombre",
    "col_referencia": "Referencia SIGPAC",
    "col_hectareas": "Hectáreas",
    "col_cultivo": "Qué tiene este año",
    "col_pueblo": "Pueblo",
    "col_revision": "Revisión",
    "col_forma": "Forma",
    "col_acciones": "Acciones",
    "tabla_etiqueta": "Tus tierras",
    "ver_versiones": "VER LO QUE HA SIDO",
    "abrir_en_el_mapa": "VERLA EN EL MAPA",
    # El pie. **Solo recuentos**, ninguno calculado aquí: los da el servidor con todas las tierras de
    # la finca, y por eso dicen de qué va cada número aunque el agricultor tenga un filtro puesto.
    "pie_filtrado": "Ves {cuantas} de {total} tierras",
    "pie_todas": "{cuantas} tierras",
    "pie_sin_forma": "Sin forma: {cuantas}",
    "pie_sin_cultivo": "Sin decir qué tienen este año: {cuantas}",
    "pie_sin_hectareas": "Sin hectáreas dichas: {cuantas}",
    # --- El mapa
    "mapa_titulo": "El mapa de la finca",
    "mapa_explica": (
        "Debajo están tus trozos, con la forma que tienen apuntada. Si una tierra no tiene forma, "
        "no se dibuja: no se le inventa un cuadro."
    ),
    "encajar": "ENCAJAR TODA LA FINCA",
    "acercar": "ACERCAR",
    "alejar": "ALEJAR",
    "ver_mis_tierras": "QUITAR LOS LINDEROS DE MIS TIERRAS",
    "ocultar_mis_tierras": "VER LOS LINDEROS DE MIS TIERRAS",
    "cambiar_capa": "Qué se ve debajo",
    "leyenda": "Leyenda",
    "lo_da": "Lo da: {servicio}",
    # Qué enseña cada capa, para que la leyenda diga algo de verdad. Son las tres que hay: el
    # contrato nombra también una capa de «avisos», y **no existe ningún servicio que la dé** (ver
    # `mapa.estado_del_mapa`): por eso se dice que no está, en vez de prometerla.
    "leyenda_foto": "La foto del campo vista desde el aire. Es la ortofoto del IGN (PNOA).",
    "leyenda_linderos": "Las rayas que separan los trozos de tierra, tal y como los tiene el SIGPAC.",
    "leyenda_cultivo": "Lo que se declaró que hay sembrado en cada trozo, según el SIGPAC.",
    "leyenda_mis_tierras": (
        "Las rayas gruesas son tus tierras, con la forma que tienen apuntada en el programa."
    ),
    "capa_avisos_no_esta": (
        "La capa de avisos no está puesta porque el SIGPAC no publica ningún servicio que la dé. "
        "No se ofrece un botón que no enseñaría nada."
    ),
    # La fecha de la imagen. **No se pone la de hoy**: eso afirmaría que la foto es de hoy, y la foto
    # puede ser de hace ocho años. El servicio que la da no dice de qué día es, así que se dice eso.
    # El hueco `{cuando}` lo rellena `app.js`, que es quien tiene la frase del servidor y el dato.
    "fecha_de_la_imagen": "De cuándo es la imagen: {cuando}",
    "fecha_sin_saber": "No se sabe: el servicio que da la imagen no dice de qué día es.",
    "sin_forma_que_ensenar": (
        "No hay ninguna tierra con su forma medida, así que no hay nada que dibujar en el mapa. "
        "Se le puede decir la forma a una tierra desde su ficha, y entonces saldrá aquí."
    ),
    # Lo que pasa cuando una imagen no llega. Es una frase entera y a propósito: el agricultor tiene
    # que saber que **no ha perdido nada** y que puede seguir trabajando con la tabla.
    "imagen_no_llega": (
        "No se ha podido traer la imagen del mapa. Puede ser la cobertura o que el servicio no "
        "conteste ahora mismo. Tus linderos siguen dibujados y la lista funciona igual: puedes "
        "seguir mirando y trabajando. Prueba otra vez dentro de un rato."
    ),
}

# Las versiones de una tierra, en su pantalla (T06, 03/10/2026).
#
# **Qué es esto.** La ficha que T05 dejó pedida y sin hacer: sus versiones por año y por quién lo
# dijo, con las tres áreas separadas, si el polígono vale y cómo está. Y encima, las dos cosas que se
# hacen con ellas: **comparar dos años** y **ensayar una importación** antes de apuntarla.
#
# **Lo que se dice de cada número, y por qué así.** Las tres áreas van cada una con su nombre y
# **ninguna se calcula de otra**: la que mide la forma, la que dice el SIGPAC y la que declara el
# agricultor son tres magnitudes distintas, y cuando una no se sabe se escribe «No se sabe» —nunca un
# cero, que afirmaría que mide cero hectáreas—.
VERSIONES_EN_PANTALLA: dict[str, str] = {
    "titulo": "Lo que ha sido esta tierra",
    "explica": (
        "Una tierra no es siempre la misma: su forma, su uso y sus hectáreas cambian de un año a "
        "otro, y lo que dice el SIGPAC no es lo mismo que lo que declaras tú. Aquí está cada versión "
        "con su año y con quién lo dijo, y aquí puedes comparar dos años sin tocar nada."
    ),
    "sin_versiones": (
        "De esta tierra todavía no hay ninguna versión guardada. Lo que se sabe de ella es lo que "
        "está en su ficha, y se puede traer lo de un año para empezar a tener historia."
    ),
    "de_que_ano": "El año",
    "de_quien": "Quién lo dijo",
    "cuando_se_miro": "Cuándo se miró",
    "sin_fecha_de_consulta": "No se apuntó cuándo se miró.",
    "referencia": "La referencia",
    "sin_referencia_numeros": "No vinieron los números de la referencia.",
    "esta_completa": "Está completa",
    "le_falta_el_recinto": "Le falta el número de recinto",
    "como_esta": "Cómo está",
    # Las tres áreas, cada una con su nombre. **No se suman ni se comparan solas**: se enseñan.
    "el_area_de_la_forma": "Lo que mide la forma que vino",
    "el_area_del_sigpac": "Lo que dice el SIGPAC",
    "el_area_declarada": "Las hectáreas que declaras",
    "no_se_sabe": "No se sabe",
    "el_uso": "El uso",
    "la_pendiente": "La pendiente",
    # --- Comparar dos años
    "comparar_titulo": "Comparar dos años",
    "comparar_explica": (
        "Elige un año y otro, y el programa te dice qué recintos están igual, cuáles han cambiado, "
        "cuáles ya no vienen y cuáles son nuevos. Comparar no toca nada: ni una hectárea ni un punto."
    ),
    "comparar_antes": "El año de antes",
    "comparar_despues": "El año de ahora",
    "comparar_boton": "COMPARAR",
    "comparar_falta": "Elige los dos años y vuelve a pulsar.",
    "comparar_sin_datos": (
        "Todavía no hay versiones de dos años distintos, así que no hay nada que comparar."
    ),
    "que_cambio": "Qué cambió",
    "no_cambio_nada": "No cambió nada",
    "cuenta_iguales": "Iguales",
    "cuenta_cambiados": "Cambiados",
    "cuenta_desaparecidos": "Desaparecidos",
    "cuenta_nuevos": "Nuevos",
    # --- Traer lo de otro año, ensayando antes
    "traer_titulo": "Traer lo de otro año",
    "traer_explica": (
        "Puedes mirar qué pasaría si a esta tierra se le apuntara lo mismo que tenía otro año. "
        "Primero se enseña lo que cambiaría y no se apunta nada; solo se apunta si tú lo dices."
    ),
    "ensayar": "ENSAYARLO SIN APUNTAR NADA",
    # El hueco `{anio}` y el `{fuente}` los rellena `app.js`: la frase es del servidor y los datos son
    # del servidor, pero unirlos es trabajo de `app.js` (`docs/REACT.md`, las frases compuestas).
    "traer_de_anio": "Lo que esta tierra tenía en {anio}, según {fuente}",
    "ensayando": "Mirando qué cambiaría…",
    "recintos_que_trae": "Recintos que trae",
    "tierras_nuevas": "Tierras que se darían de alta",
    # **El recuento de los recintos a los que no les ha llegado el polígono, con su nombre.** Aquí
    # ponía la etiqueta de «No se sabe», y la revisión de T06 lo cazó: eso **no** es un dato que no se
    # sepa, es un recuento de recintos sin forma —una cosa de la que se sabe todo—, y además se leía
    # fatal («No se sabe: 3»).
    "recintos_sin_forma": "Recintos sin su forma medida",
    "no_se_ha_apuntado": (
        "Esto es solo un ensayo: no se ha apuntado nada de nada. Si te cuadra, pulsa el botón de "
        "abajo; si no, no pasa nada."
    ),
    "apuntarlo": "SÍ, APUNTARLO",
    "apuntando_el_lote": "Apuntándolo…",
    "apuntado_el_lote": (
        "Ya está apuntado: {creadas} versiones nuevas y {actualizadas} puestas al día, con "
        "«igual» en {iguales}."
    ),
    "lo_que_no_se_pudo": "Lo que no se ha podido tener en cuenta",
    "trozos_que_se_pisan": "Trozos que se pisan",
    "superficies_que_no_cuadran": "Superficies que no cuadran",
    "ninguno": "Ninguno.",
    "volver_a_las_tierras": "VOLVER A MIS TIERRAS",
}


# --------------------------------------------------------------------------
# Las semillas y las siembras (T10, 03/10/2026)
#
# **Se añade al final y no se toca ni un texto de los de arriba.** Lo que hay aquí son las palabras
# de dos pantallas nuevas: la ficha de una semilla —con lo que pone su etiqueta— y la siembra, que
# es «en esta tierra sembré esta semilla».
#
# Tres decisiones que están en las frases y conviene entender:
#
#  1. **La dosis por hectárea y la cantidad total se piden con nombres distintos y no se parecen.**
#     «Cuánto se siembra en cada hectárea» y «Cuánto se ha gastado en total» son dos preguntas, y en
#     la pantalla van en dos sitios distintos con su unidad cada una. Confundirlas es un error de
#     diez veces (el caso A02 del contrato), y la manera de no confundirlas es no llamarlas igual.
#  2. **El poder germinativo y la pureza se dicen con su hueco**: «La etiqueta no lo dice» es una
#     respuesta, y es distinta de un cero. Estas dos cifras no vienen en todas las etiquetas.
#  3. **Cuando algo se ha calculado, se dice.** `{calculado}` es la frase que acompaña a un número
#     que ha sacado el programa (dosis × hectáreas): el agricultor tiene que poder revisarlo.
SEMILLAS: dict[str, str] = {
    "titulo": "Mis semillas",
    "explica": (
        "Aquí tienes las semillas que usas, con lo que pone su etiqueta y lo que te queda de cada "
        "una. La semilla es una cosa más del almacén: entra con el albarán y sale cuando la siembras."
    ),
    "vacia": (
        "Todavía no has dado de alta ninguna semilla. Cuando apuntes una, aquí verás su etiqueta y "
        "lo que te queda."
    ),
    # El singular y el plural, porque «Tienes 1 semillas» es lo primero que hace desconfiar de un
    # programa (ronda 84).
    "cuantas": "Tienes {cuantas} semillas dadas de alta.",
    "cuantas_una": "Tienes 1 semilla dada de alta.",
    "anadir": "AÑADIR UNA SEMILLA",
    "leer_etiqueta": "HACERLE UNA FOTO A LA ETIQUETA",
    "leer_lo_que_pone": "LEER LO QUE PONE (NO SE GUARDA NADA)",
    "leer_etiqueta_pista": (
        "Hazle una foto a la etiqueta del envase. Si se puede leer, te enseño lo que he entendido "
        "para que lo mires antes de guardarlo."
    ),
    "que_se_puede_hacer": "¿Qué quieres hacer?",
    "volver_a_las_semillas": "VOLVER A MIS SEMILLAS",
    # --- La ficha de una semilla (el alta y la corrección son el mismo formulario)
    "ficha_titulo": "Una semilla nueva",
    "ficha_titulo_corregir": "Corregir esta semilla",
    "ficha_explica": (
        "Escribe lo que pone la etiqueta. Lo que no venga en el papel, déjalo en blanco: se queda "
        "vacío y ya está, no se pone un cero."
    ),
    "ficha_explica_propuesta": (
        "Esto es lo que he leído de la foto. Míralo y corrígelo: hasta que no pulses el botón de "
        "abajo, no se ha guardado nada. Lo que no he podido leer está en blanco."
    ),
    "nombre_del_articulo": "Cómo la llamas tú",
    "nombre_del_articulo_pista": (
        "El nombre con el que la reconoces en el almacén. Es el que verás en la lista y en el libro."
    ),
    "especie": "Qué semilla es",
    "especie_pista": "La especie, como viene en la etiqueta: veza común, trigo blando, cebada…",
    "variedad": "La variedad",
    "variedad_pista": "El nombre de la variedad, si el papel lo dice.",
    "casa_comercial": "La casa que la vende",
    "casa_comercial_pista": "Quien la produce o la envasa: lo que pone arriba del todo en la etiqueta.",
    "proveedor": "A quién se la compraste",
    "proveedor_pista": "El proveedor o la cooperativa, si quieres apuntarlo.",
    "numero_lote_proveedor": "El número de lote del envase",
    "numero_lote_proveedor_pista": (
        "El número que va impreso en el saco. Es con el que te avisan si hay un problema con esa "
        "partida."
    ),
    "dosis_recomendada": "Cuánto recomienda sembrar por hectárea",
    "dosis_recomendada_pista": (
        "Lo que dice la etiqueta, no lo que tú siembras. Puedes sembrar otra cosa: eso se apunta en "
        "cada siembra."
    ),
    "unidad_de_la_dosis": "En qué se mide",
    "fecha_envasado": "Cuándo se envasó",
    "fecha_caducidad": "Hasta cuándo vale",
    "fecha_caducidad_pista": (
        "Si el papel no lo dice, déjalo en blanco: «no lo he mirado» no es «no caduca»."
    ),
    "poder_germinativo": "Poder germinativo",
    "poder_germinativo_pista": "El porcentaje del papel. No viene en todas las etiquetas.",
    "pureza": "Pureza",
    "pureza_pista": "El porcentaje del papel. Tampoco viene en todas.",
    "no_lo_dice": "La etiqueta no lo dice",
    "tratada": "¿Viene tratada?",
    "tratada_pista": (
        "Si el envase dice que la semilla viene tratada con algo, márcalo aquí. Es un dato que "
        "importa al manejarla."
    ),
    "tratada_si": "Sí viene tratada",
    "tratada_no": "No viene tratada",
    "tratada_no_se": "No lo sé",
    "guardar": "GUARDAR LA SEMILLA",
    "guardando": "Guardando…",
    "guardada": "Semilla guardada",
    "guardada_explica": (
        "Ya está en tu almacén. Cuando la siembres, se apunta en la tierra y sale de aquí: así el "
        "libro cuadra."
    ),
    "no_confirmada": (
        "Esto es solo lo que he leído. Hasta que no pulses GUARDAR LA SEMILLA, no hay ninguna "
        "semilla apuntada."
    ),
    # --- Lo que leyó el programa de la foto
    "leido_de_foto": "Leído de la foto de la etiqueta",
    "leido_de_pdf": "Leído del PDF de la etiqueta",
    "leido_de_escaneo": "Leído del escaneo de la etiqueta",
    "leido_de_texto": "Leído de lo que has pegado",
    "leido_a_mano": "Lo has escrito tú",
    "idioma_de_la_lectura": "Leído con el idioma {idioma}",
    "campos_leidos": "He podido leer {cuantos} datos de la etiqueta.",
    "campos_leidos_uno": "He podido leer 1 dato de la etiqueta.",
    "no_he_leido_nada": (
        "De esta foto no he podido sacar ningún dato. Escribe tú lo que pone la etiqueta: la foto "
        "se guarda igual, como el papel que es."
    ),
    "escribirlo_a_mano": "ESCRIBIRLO A MANO",
    "lo_que_dice_el_papel": "Lo que dice el papel y no he podido apuntar",
    "lo_que_dice_el_papel_explica": (
        "Esto lo he leído, pero tal y como está escrito no se puede apuntar. Míralo y ponlo donde "
        "toque."
    ),
    "la_foto_se_guarda": (
        "La foto se guarda con la semilla, así que dentro de un año puedes volver a mirarla."
    ),
    "subir_la_foto": "SUBIR LA FOTO",
    "foto_guardada": "La foto de la etiqueta ya está guardada con esta semilla.",
    "sin_foto": "Esta semilla no tiene la foto de la etiqueta guardada.",
    "ver_la_foto": "VER LA FOTO DE LA ETIQUETA",
    "no_hay_lector": (
        "En este ordenador no está puesto el programa que lee las fotos, así que de la foto no "
        "puedo sacar los datos. Puedes escribir tú lo que pone la etiqueta."
    ),
    # --- Lo que queda en el almacén
    "lo_que_queda": "Lo que te queda",
    "sin_saber_lo_que_queda": "No se puede saber lo que queda",
    "lotes_disponibles": "Envases en el almacén",
    "no_esta_en_el_almacen": (
        "Esta semilla todavía no está dada de entrada en el almacén, así que no se puede descontar "
        "nada de ella. Apunta el albarán o una entrada y vuelve aquí."
    ),
    "apuntar_una_entrada": "APUNTAR LO QUE YA TENÍA",
    "ver_el_libro": "VER EL LIBRO DEL ALMACÉN",
    # --- Las siembras
    "siembras_titulo": "Lo que he sembrado",
    "siembras_explica": (
        "Cada siembra dice en qué tierra, de qué semilla y cuánto. Lo que siembras sale del almacén "
        "en el mismo momento, así que la semilla que te queda es la de verdad."
    ),
    "siembras_vacia": (
        "Todavía no has apuntado ninguna siembra. Cuando siembres, aquí lo tendrás y la semilla "
        "saldrá del almacén."
    ),
    "cuantas_siembras": "Tienes {cuantas} siembras apuntadas.",
    "cuantas_siembras_una": "Tienes 1 siembra apuntada.",
    "sembrar_esta": "SEMBRAR ESTA SEMILLA",
    "sembrar_esta_pista": "Apunta en qué tierra la has sembrado y sale del almacén",
    "siembra_titulo": "Sembrar una semilla",
    "siembra_titulo_corregir": "Corregir esta siembra",
    "siembra_explica": (
        "Dime en qué tierra la has sembrado y cuánto. Si me das una de las dos cifras y las "
        "hectáreas, la otra la saco yo y te lo digo."
    ),
    "siembra_semilla": "¿Qué semilla?",
    "siembra_tierra": "¿En qué tierra?",
    "siembra_fecha": "¿Cuándo?",
    "siembra_superficie": "¿Cuántas hectáreas has sembrado?",
    "siembra_dosis": "Cuánto se siembra en cada hectárea",
    "siembra_cantidad_total": "Cuánto se ha gastado en total",
    "siembra_unidad_total": "En qué se mide el total",
    "siembra_envase": "De qué envase sale",
    "siembra_envase_pista": (
        "De qué saco sale la semilla. Sin esto no se puede descontar del almacén, porque no se sabe "
        "de dónde quitar."
    ),
    "siembra_notas": "Lo que quieras apuntar",
    "guardar_siembra": "GUARDAR LA SIEMBRA",
    "guardando_siembra": "Guardando…",
    "siembra_guardada": "Siembra apuntada",
    "siembra_guardada_explica": (
        "La semilla ha salido del almacén. Si te has equivocado, puedes corregirla o anularla: si la "
        "anulas, lo que salió vuelve a contar y no queda nada descontado dos veces."
    ),
    "calculado": "Lo ha calculado el programa",
    "calculado_pista": (
        "Este número no lo has escrito tú: sale de la dosis por las hectáreas. Míralo, y si no es "
        "así, cámbialo."
    ),
    "siembra_anular": "ANULAR ESTA SIEMBRA",
    "siembra_motivo_anulacion": "Por qué la anulas",
    "siembra_motivo_anulacion_pista": (
        "Una siembra no se borra: se anula y queda dicho por qué. Así el cuaderno se puede explicar."
    ),
    "siembra_anulada": "Siembra anulada. Lo que había salido del almacén vuelve a contar.",
    "siembra_ya_anulada": "Esta siembra está anulada.",
    "siembra_no_descuenta": "Esta siembra no ha descontado nada del almacén",
    "siembra_no_descuenta_pista": (
        "Falta saber cuánto se sembró o de qué envase sale. Mientras no se sepa, no se resta nada: "
        "antes un hueco que un número inventado. Corrígela cuando lo sepas."
    ),
    "corregir_siembra": "CORREGIRLA",
    "volver_a_las_siembras": "VOLVER A LO QUE HE SEMBRADO",
    "siembras_de_esta_semilla": "Dónde la has sembrado",
    "donde_se_sembro": "Dónde se sembró",
    "cuantas_hectareas": "Hectáreas",
    # --- Lo que piden las dos pantallas y estaba sin escribir
    # (claves que usan `semillas.js` y `siembras.js`: se añaden aquí para que ninguna pregunta salga
    # en blanco, que es justo el fallo que este proyecto persigue con su prueba de textos)
    "buscando": "Buscando…",
    "volver_al_inicio": "VOLVER AL INICIO",
    "ver_las_siembras": "VER LO QUE HE SEMBRADO",
    "anadir_pista": "Escribe lo que pone la etiqueta del envase",
    "articulo_del_almacen": "¿Es algo que ya tienes en el almacén?",
    "articulo_del_almacen_pista": (
        "Si la semilla ya entró con un albarán, elígela aquí: se le cuelga la etiqueta a lo que ya "
        "hay, en vez de apuntar dos veces la misma semilla."
    ),
    "articulo_nuevo": "No, es nueva: la apunto ahora",
    "sin_decir": "Sin decir",
    "sin_semillas": (
        "Todavía no tienes ninguna semilla dada de alta, así que no hay de dónde descontar lo que "
        "siembres. Apunta una y vuelve aquí."
    ),
    "siembra_elige_la_tierra": "Elige la tierra",
    "siembra_superficie_pista": (
        "Las hectáreas que has sembrado. Con esto y una de las dos cifras de abajo, la otra la saco yo."
    ),
    "siembra_dosis_pista": (
        "Lo que siembras en cada hectárea. No es lo que has gastado en total: son cosas distintas."
    ),
    "siembra_cantidad_total_pista": (
        "Lo que has gastado en la tierra entera. Es lo que sale del almacén."
    ),
    "siembra_sin_envase": "No sé de qué envase sale",
    # Un dato que no se sabe, dicho con dos palabras: es lo que se enseña en la ficha de una siembra
    # cuando la dosis o el total no constan. **Nunca se pone un cero ahí.**
    "no_se_sabe": "No se sabe",
    # Un envase sin número de lote es una cosa de verdad (la etiqueta no lo traía), no un hueco.
    "envase_sin_numero": "El envase sin número",
}


# Y los mensajes, con su código. Van aparte y se añaden a `MENSAJES` al final (como el bloque del
# libro del almacén) para no tocar ni un mensaje de los que ya estaban.
MENSAJES_DE_LAS_SEMILLAS: dict[str, str] = {
    # --- Leer la etiqueta
    "SM1_etiqueta_ilegible": (
        "De esa foto no he podido sacar ni una letra. Prueba otra vez con más luz y la etiqueta "
        "derecha, o escribe tú lo que pone."
    ),
    "SM2_dosis_sin_decir_por_hectarea": (
        "La etiqueta dice «{dice}» y no dice si es por hectárea. No lo he apuntado como dosis: mira "
        "el envase y ponlo tú donde toque."
    ),
    "SM3_fecha_sin_dia": (
        "De {que} la etiqueta solo dice {dice} (mes y año), así que no la he apuntado: mira el "
        "envase y escribe el día."
    ),
    "SM4_el_envasado": "el envasado",
    "SM5_la_caducidad": "la caducidad",
    "SM6_la_etiqueta_no_dice_la_caducidad": (
        "Esta etiqueta no dice hasta cuándo vale la semilla. Se queda en blanco: «no lo dice» no es "
        "«no caduca»."
    ),
    # --- La dosis y la cantidad total
    "SM7_una_dosis_negativa": (
        "Una cantidad no puede ser negativa. La he dejado en blanco: escríbela otra vez."
    ),
    "SM8_la_cantidad_la_he_calculado": (
        "La cantidad total la he calculado yo: {dosis} {unidad_dosis} por {superficie} hectáreas son "
        "{total} {unidad}. Míralo, y si no es así, cámbialo."
    ),
    "SM9_sin_unidad": "sin unidad",
    "SM10_la_dosis_la_he_calculado": (
        "La dosis por hectárea la he calculado yo: {total} {unidad} entre {superficie} hectáreas son "
        "{dosis} {unidad_dosis}. Míralo, y si no es así, cámbialo."
    ),
    "SM11_las_dos_cifras_no_cuadran": (
        "Las dos cifras no cuadran: {dosis} {unidad_dosis} por {superficie} hectáreas son "
        "{esperado}, y tú has puesto {total} {unidad}. Puede estar bien (a lo mejor sembraste a "
        "mano una parte), pero míralo antes de guardar."
    ),
    "SM12_las_unidades_no_se_pueden_comparar": (
        "Una cifra está en {una} y la otra en {otra}, y esas dos no se pueden comparar: para pasar "
        "de una a otra haría falta la densidad, que no sabemos. Déjalas como están o ponlas en la "
        "misma unidad."
    ),
    # --- Dar de alta la semilla
    "SM13_falta_el_nombre": (
        "Falta cómo llamas a esta semilla. Escribe el nombre con el que la reconoces en el almacén."
    ),
    "SM14_falta_la_unidad_de_la_dosis": (
        "Has puesto cuánto se siembra por hectárea, pero no en qué se mide. Elige kilos, gramos o "
        "unidades: sin eso el número no dice nada."
    ),
    "SM15_el_porcentaje_no_vale": (
        "Un porcentaje va entre 0 y 100, y el que has puesto no lo es. Corrígelo o déjalo en blanco: "
        "un poder germinativo inventado es peor que un hueco."
    ),
    # --- Sacar la semilla del almacén y apuntar la siembra
    "SM16_no_se_puede_sacar_sin_cantidad": (
        "No se ha sacado nada del almacén porque no se sabe cuánto se sembró. Dime la cantidad total "
        "o la dosis por hectárea con las hectáreas, y la siembra descuenta."
    ),
    "SM17_no_se_puede_sacar_sin_envase": (
        "No se ha sacado nada del almacén porque no se sabe de qué envase sale. Elige el saco del "
        "que has sembrado."
    ),
    "SM18_la_semilla_no_esta_en_el_almacen": (
        "Esta semilla todavía no está dada de entrada en el almacén, así que no hay de dónde "
        "quitarla. Apunta el albarán con el que llegó, o una entrada de lo que ya tenías."
    ),
    "SM19_el_envase_no_es_de_esta_semilla": (
        "Ese envase no es de esta semilla. Elige uno de los suyos."
    ),
    "SM20_la_siembra_ya_estaba": (
        "Esta siembra ya estaba apuntada: no se ha descontado otra vez. Si querías cambiarla, pulsa "
        "CORREGIRLA."
    ),
    "SM21_no_se_pudo_comprobar_si_ya_estaba": (
        "Esta siembra se ha apuntado, pero no he podido comprobar si ya estaba: no ha venido con la "
        "marca de la petición. Si la ves dos veces, anula una."
    ),
    "SM22_falta_la_tierra": (
        "Falta decir en qué tierra la has sembrado. Toca la tierra y vuelve a guardar."
    ),
    "SM23_la_siembra_esta_anulada": (
        "Esta siembra está anulada, así que no ha gastado nada. Apunta una nueva si te has "
        "equivocado al anularla."
    ),
    "SM24_falta_el_motivo_para_anular": (
        "Para anular una siembra hace falta decir por qué. Escríbelo y vuelve a pulsar."
    ),
    "SM25_lo_que_salio_cambio": (
        "Lo que salió del almacén ha cambiado: {antes} {unidad} antes y {ahora} {unidad} ahora. La "
        "salida vieja queda anulada y la nueva es la que cuenta, así no hay dos descuentos."
    ),
    "SM26_el_lote_no_se_puede_sacar": (
        "No se ha podido sacar del envase: {motivo} Corrige la siembra o apunta lo que falta en el "
        "almacén."
    ),
    "SM27_la_semilla_no_existe": (
        "Esta semilla no está en tu lista. Vuelve a tus semillas y elige una."
    ),
    "SM28_nada_que_corregir": (
        "No hay nada que corregir: esa siembra no está en tu cuaderno."
    ),
    # Este lo usa el libro del almacén (`servicios.estado_de_los_origenes`): dice por qué una salida
    # de semilla ya no cuenta. Es la mitad de «anular una siembra devuelve lo que salió».
    "SM29_la_siembra_esta_anulada": (
        "La siembra está anulada, así que esta salida no cuenta."
    ),
    "SM30_la_salida_se_corrigio": (
        "Se corrigió la siembra: esta salida es la de antes y ya no cuenta."
    ),
    "SM31_ahora_si_descuenta": (
        "Ahora sí se ha sacado del almacén: {cantidad} {unidad}. Antes no se pudo porque faltaba un "
        "dato."
    ),
    "SM32_lo_que_salio_vuelve_a_contar": (
        "Lo que había salido del almacén vuelve a contar. La salida sigue en el libro, tachada, y la "
        "semilla está otra vez donde estaba."
    ),
    "SM33_esa_semilla_ya_tiene_su_etiqueta": (
        "Ese producto del almacén ya tiene su etiqueta de semilla apuntada. Corrígela en su ficha en "
        "vez de darla de alta otra vez."
    ),
    # Los dos que salieron de la revisión del T10 (03/10/2026).
    "SM34_la_semilla_no_se_cambia": (
        "La semilla de una siembra apuntada no se cambia: lo que salió del almacén salió de esa "
        "semilla. Si te has equivocado, anula esta siembra y apunta la buena con la semilla que sea."
    ),
    "SM35_no_ha_entrado_para_saber_lo_que_queda": (
        "De esta semilla no ha entrado nada en el almacén todavía, así que no se puede saber lo que "
        "queda. Apunta el albarán con el que llegó y aquí saldrá lo que tienes."
    ),
}

MENSAJES.update(MENSAJES_DE_LAS_SEMILLAS)


# --------------------------------------------------------------------------
# Los contactos (T11, 03/10/2026)
#
# **Se añade al final y no se toca ni un texto de los de arriba.** Lo que hay aquí son las palabras de
# una sección nueva: la ficha de una persona o de una empresa que trata con la finca (el proveedor, el
# comprador, el técnico), los papeles que puede hacer y la pantalla donde se le enseñan al agricultor
# los nombres que ya tiene escritos para que decida cuáles son la misma persona.
#
# Cuatro decisiones que están en las frases y conviene entender:
#
#  1. **Un papel se dice como lo diría él, no como lo dice el registro.** «Quien te vende el producto» y
#     no «proveedor de productos fitosanitarios»: la palabra «fitosanitario» está prohibida en pantalla
#     desde el primer día. Los papeles son lo que alguien HACE con esta finca, y así se escriben.
#  2. **Cuando el programa no junta dos nombres, dice por qué y no lo llama error.** «Se parecen, pero
#     no son iguales» es una decisión del programa para no equivocarse, no una falta del agricultor.
#  3. **La migración propone y él confirma, y eso se dice con esas palabras.** Una pantalla que
#     apuntara doce fichas por su cuenta daría miedo, y haría bien en darlo.
#  4. **Ningún texto lleva marcas de ningún tipo** (ni asteriscos ni almohadillas): lo que se lee en
#     pantalla es exactamente lo que hay escrito aquí, letra a letra.
CONTACTOS: dict[str, object] = {
    # **Los canales** (Entrega 2, 13/10/2026): varios teléfonos, correos y direcciones con su etiqueta y
    # su principal. Se dice cuál es el principal porque, si hay dos teléfonos, hay que saber cuál se marca.
    "canales_titulo": "Sus teléfonos, correos y direcciones",
    "canales_pista": (
        "Los de siempre y los demás: el del almacén, el móvil de quien atiende, la dirección de entrega. El principal es el que se usa si no se dice otra cosa."
    ),
    "canales_principal": "El principal",
    "canales_sin_etiqueta": "Sin nombre",
    "canales_sin_nada_mas": "No hay ninguno más apuntado.",
    "canales_apuntar": "Apuntar otro",
    "canales_hacer_principal": "Usar este",
    "canales_quitar": "Quitar",
    "canales_cual": "¿Qué es?",
    "canales_el_dato": "El teléfono, el correo o la dirección",
    "canales_como_se_llama": "Cómo lo llamas tú (el almacén, el móvil de Ana…)",
    # **Las próximas acciones** (Entrega 3, 13/10/2026): lo que queda por hacer con este contacto.
    "tareas_titulo": "Lo que hay que hacer",
    "tareas_pista": (
        "Lo próximo con este contacto. Si una se pasa de fecha se queda vencida: el programa no la cancela por su cuenta, porque eso lo decides tú."
    ),
    "tareas_apuntar": "Apuntar",
    "tareas_que_hacer": "¿Qué hay que hacer?",
    "tareas_cuando": "¿Para cuándo? Si no lo sabes, déjalo en blanco",
    "tareas_quien": "¿Quién lo hace?",
    "tareas_completar": "Hecha",
    "tareas_cancelar": "Cancelar",
    "tareas_vencida": "Vencida",
    "tareas_sin_nada": "No hay nada apuntado con este contacto.",
    "tareas_hecha_por": "Hecha por",
    "tareas_cancelada_por": "Cancelada por",
    # **El saldo del contacto** (Entrega 1, 13/10/2026). Se dicen los dos sentidos por separado y con
    # sus palabras, porque la pantalla es donde se entiende que no se restan.
    "saldo_titulo": "Lo que hay con este contacto",
    "saldo_explica": (
        "Lo que nos debe y lo que le debemos, cada cosa por su lado. No se restan: que a la misma persona se le venda y se le compre es lo normal, y juntarlo escondería las dos."
    ),
    "saldo_nos_debe": "Nos debe",
    "saldo_le_debemos": "Le debemos",
    "saldo_nada": "Nada",
    "saldo_importe": "Importe",
    "saldo_cobrado": "Cobrado",
    "saldo_pagado": "Pagado",
    "saldo_pendiente": "Queda",
    "saldo_sin_importe": "No se sabe cuánto",
    "saldo_sin_documentos": "No hay ningún documento apuntado a este contacto.",
    "saldo_sin_asignar": "Dinero sin asignar",
    "saldo_sin_asignar_pista": (
        "Está apuntado y no se sabe de qué es, así que no rebaja ninguna deuda. No es un anticipo."
    ),
    "saldo_para_revisar": "Para revisar",
    "saldo_para_revisar_pista": (
        "Se ha cobrado o pagado más de lo que valía el documento. Puede ser un tecleo, un pago de otra cosa o una devolución pendiente."
    ),
    "saldo_cobertura": "Hasta dónde llega",
    "saldo_cobertura_pista": (
        "Solo cuenta lo que está apuntado a este contacto. Las facturas de compra no llevan contacto, así que no se adjudican por el nombre."
    ),
    "saldo_en_euros": "En euros",
    "saldo_no_se_adjudica_por_nombre": "No se adjudica nada por el nombre.",
    "saldo_abrir": "Ver los documentos",
    # **Las notas con autor** (CRM-03, criterio (f), 11/10/2026). El rótulo de la lista, el del campo
    # donde se escribe y el de la fecha. El autor de cada nota lo pone el servidor; aquí solo se dice
    # cómo se lee («la escribió …»).
    "notas_titulo": "Lo que se sabe de esta ficha",
    "notas_pista": "Lo que se va apuntando, con quién lo apuntó y cuándo. No se corrige: si algo cambia, se apunta otra nota.",
    "sin_notas": "Todavía no hay ninguna nota.",
    "nota_nueva": "Apuntar una nota",
    "nota_nueva_pista": "Lo que quieras acordarte de esta ficha.",
    "apuntar_la_nota": "APUNTAR LA NOTA",
    "nota_la_escribio": "La escribió",
    "nota_lo_escribio_el_programa": "Lo apuntó el programa",
    # **Y el autor que ya no se puede nombrar** (13/10/2026, revision): la escribio una persona, pero su
    # nombre no esta. Se dice eso, que es lo que se sabe, en vez de culpar al programa.
    "nota_autor_sin_nombre": "alguien cuyo nombre ya no está",
    "titulo": "Las personas y las empresas",
    "explica": (
        "Aquí apuntas una vez a quien te vende, a quien te compra, a quien te asesora o a quien te "
        "lleva la mercancía. Después, en cada factura y en cada venta, solo tienes que decir cuál de "
        "ellos es: su nombre ya no hay que volver a escribirlo."
    ),
    "vacia": (
        "Todavía no tienes ninguna ficha apuntada. Puedes empezar por los nombres que ya has escrito "
        "en tus facturas y en tus ventas: el programa te los enseña y tú dices cuáles son la misma "
        "persona."
    ),
    "cuantas": "Tienes {cuantas} fichas apuntadas.",
    "cuantas_una": "Tienes 1 ficha apuntada.",
    # Cuántos papeles llevan escrito su nombre. Es el número que enseña la tarjeta de la lista, y con
    # uno se leería «Su nombre está escrito en 1 papeles», que es lo primero que hace desconfiar.
    "cuantos_escritos": "Su nombre está escrito en {cuantas} papeles.",
    "cuantos_escritos_uno": "Su nombre está escrito en 1 papel.",
    # **El estado, a la vista** (CRM-03, criterio (e), 11/10/2026). Va en el rótulo de la ficha y en
    # su «qué es», que es lo que se lee de un vistazo en la lista y en la tabla: un contacto de baja
    # **no se esconde**, porque su pasado sigue apuntándole; lo que hace es decirlo.
    "de_baja": "DE BAJA",
    "dejarlo_de_usar": "DEJAR DE USARLO",
    "volver_a_usarlo": "VOLVER A USARLO",
    "dejarlo_de_usar_pista": (
        "Deja de ofrecerse sin borrar nada: sus facturas y sus ventas siguen apuntándole."
    ),
    "de_baja_pista": "Ya no se trabaja con esta ficha. Sigue aquí porque sus papeles la necesitan.",
    # **Los rótulos de la tabla del ordenador** (11/10/2026). Van aquí, con los demás textos del servidor, y no
    # escritos a mano en el HTML, porque el contrato de la tabla lo pide así (`web/react/piezas/tabla.js`: «los
    # textos de las columnas y del resumen vienen del servidor»). La última columna es siempre la de las
    # acciones: el componente pinta ahí sus botones y por eso una fila escribe **una celda menos** que columnas
    # hay (hay una prueba que lo impide).
    "tabla_nombre": "Nombre",
    "tabla_que_es": "Qué es",
    "tabla_nif": "NIF",
    "tabla_telefono": "Teléfono",
    "tabla_localidad": "Localidad",
    "tabla_acciones": "Acciones",
    "tabla_abrir": "ABRIR LA FICHA",
    # Lo que se escribe en la celda cuando un dato no está puesto. Un hueco en blanco no dice si falta el dato
    # o si la pantalla se ha equivocado; una raya, sí.
    "tabla_sin_dato": "—",
    "tabla_que_es_sin_papel": "Sin papel apuntado",
    "buscando": "Buscando…",
    "buscar": "Buscar por el nombre",
    "buscar_pista": "Escribe unas letras del nombre. No hacen falta las tildes.",
    "buscar_boton": "BUSCAR",
    "buscar_limpiar": "VERLAS TODAS",
    "que_se_puede_hacer": "¿Qué quieres hacer?",
    "anadir": "AÑADIR UNA FICHA",
    "anadir_pista": "Una persona o una empresa que trate con tu finca",
    "traer_los_nombres": "TRAER LOS NOMBRES QUE YA TENGO ESCRITOS",
    "traer_los_nombres_pista": (
        "El programa mira los nombres que ya están escritos en tus facturas, tus ventas y tus "
        "análisis, y te propone una ficha por cada uno. Tú decides cuáles se apuntan."
    ),
    "volver_al_inicio": "VOLVER AL INICIO",
    # --- La ficha de un contacto
    "ficha_titulo": "Una ficha nueva",
    "ficha_titulo_corregir": "Corregir esta ficha",
    "ficha_explica": (
        "Escribe lo que sepas. Lo que no sepas, déjalo en blanco: se queda vacío y no pasa nada."
    ),
    "nombre": "Cómo se llama",
    "nombre_pista": "El nombre tal y como lo escribes tú. Es el que verás en la lista.",
    "es_persona_o_empresa": "¿Es una persona o una empresa?",
    "es_empresa_si": "Es una empresa",
    "es_empresa_no": "Es una persona",
    "es_empresa_no_se": "No lo sé",
    "nif": "Su NIF o su CIF",
    "nif_pista": (
        "El número que viene en sus facturas. Si dos nombres distintos lo comparten, el programa sabe "
        "que son la misma empresa."
    ),
    "telefono": "Su teléfono",
    "correo": "Su correo",
    "direccion": "Su dirección",
    "localidad": "Su pueblo",
    "notas": "Lo que quieras apuntar de él",
    "notas_pista": "Por ejemplo: el del pienso, o que pasa los martes.",
    "los_papeles": "¿Qué hace contigo?",
    "los_papeles_pista": (
        "Puedes marcar más de uno: la misma cooperativa te vende la semilla y te compra el trigo."
    ),
    "papeles_que_dicen_sus_papeles": "Según lo que tienes apuntado, también sería:",
    # Lo que haría esa ficha según los papeles en los que aparece su nombre. Es distinto de la pregunta
    # de la ficha («¿Qué hace contigo?», que se contesta marcando): aquí el programa **cuenta lo que ha
    # visto** al proponer, y por eso se dice con otras palabras.
    "papeles_que_tendria": "Haría contigo:",
    "guardar": "GUARDAR LA FICHA",
    "guardando": "Guardando…",
    "guardada": "Ficha guardada.",
    "volver_a_los_contactos": "VOLVER A LAS FICHAS",
    "borrar": "BORRAR ESTA FICHA",
    "borrar_pista": (
        "Se borra la ficha, pero no se borra ningún nombre de tus facturas ni de tus ventas: siguen "
        "diciendo lo mismo."
    ),
    "borrar_confirmar": "¿Seguro que quieres borrar esta ficha?",
    "borrar_si": "SÍ, BORRARLA",
    "borrar_no": "MEJOR NO",
    "borrada": "Ficha borrada. Los nombres de tus facturas y de tus ventas siguen donde estaban.",
    # --- Dónde aparece su nombre
    "donde_aparece": "Dónde está escrito su nombre",
    "donde_aparece_explica": (
        "Estos son los papeles en los que aparece. El nombre que escribiste tú no se ha tocado: si "
        "quieres, puedes quitar el enlace y el papel se queda como estaba."
    ),
    "sin_enlaces": (
        "Su nombre todavía no está enlazado con ningún papel. Puedes buscarlo entre los nombres que "
        "ya tienes escritos y decir que es él."
    ),
    "enlazar": "ENLAZAR UN NOMBRE QUE YA TENGO ESCRITO",
    "quitar_enlace": "QUITAR EL ENLACE",
    "enlace_quitado": "Enlace quitado. El nombre sigue escrito en el papel, tal y como lo escribiste.",
    "el_texto_ha_cambiado": (
        "Ojo: en ese papel ahora pone lo siguiente: {ahora}. Cuando lo enlazaste ponía: {entonces}. Si "
        "ya no es él, quita el enlace."
    ),
    "esta_anulada": "anulada",
    "de_la_migracion": "Apuntada desde los nombres que ya tenías escritos",
    "de_la_migracion_pista": (
        "Esta ficha la propuso el programa a partir de tus papeles. Si la corriges, se queda como "
        "tuya y ya no se deshace con las demás."
    ),
    # --- Buscar un nombre ya escrito para enlazarlo
    "escritos_titulo": "Los nombres que ya tienes escritos",
    "escritos_explica": (
        "Estos nombres están escritos en tus papeles y todavía no los has enlazado con ninguna ficha. "
        "Toca el que sea esta persona y quedará enlazado. No se cambia ni una letra de tu papel."
    ),
    "escritos_vacio": (
        "No hay ningún nombre escrito sin enlazar. Todo lo que tienes apuntado ya tiene su ficha."
    ),
    "escritos_cuantos": "Hay {cuantos} nombres escritos esperando a que les digas de quién son.",
    "escritos_cuantos_uno": "Hay 1 nombre escrito esperando a que le digas de quién es.",
    "escritos_buscar": "Buscar entre los nombres escritos",
    "escritos_buscar_pista": "Escribe unas letras del nombre que buscas.",
    "escritos_buscar_boton": "BUSCAR",
    "escritos_ver_todos": "VERLOS TODOS",
    "enlazar_este": "ESTE ES",
    "enlazado": "Enlazado. Ese nombre ya es de esta ficha.",
    # --- La revisión de los nombres (la migración)
    "revision_titulo": "Los nombres que ya tienes escritos",
    "revision_explica": (
        "He mirado los nombres que están escritos a mano en tus facturas, tus albaranes, tus ventas y "
        "tus análisis, y te propongo una ficha por cada uno. No he apuntado nada todavía: mira la "
        "lista y apunta solo las que quieras."
    ),
    "revision_nada": "No hay ningún nombre escrito sin dueño. Todo lo que tienes apuntado ya tiene su ficha.",
    "revision_cuantas": "Se te proponen {cuantas} fichas, con {nombres} nombres escritos.",
    "revision_cuantas_una": "Se te propone 1 ficha, con 1 nombre escrito.",
    # **Los dos nombres que se parecen, con nombre y apellidos.** Enseñar solo el grupo entero haría
    # creer que todos los nombres de la lista se parecen entre sí, y no es lo mismo.
    "revision_se_parecen_estos": (
        "«{uno}» y «{otro}» se parecen, pero no son iguales. El programa no los junta: míralos y "
        "decide tú."
    ),
    # Los NIF, cuando el nombre es el mismo y el número no: son **dos personas distintas**, y por eso se
    # enseñan los dos números, que es lo único que lo demuestra.
    "revision_nifs_dos": "Los NIF de esos papeles son {nifs}.",
    "revision_apuntadas": (
        "Apuntadas {cuantas} fichas, con {nombres} nombres enlazados. Ni una letra de tus papeles se "
        "ha tocado."
    ),
    "revision_apuntadas_uno": (
        "Apuntada 1 ficha, con 1 nombre enlazado. Ni una letra de tus papeles se ha tocado."
    ),
    "revision_que_se_hace": "Qué hace el programa con esto",
    "revision_que_se_hace_explica": (
        "Lo que apuntes no cambia ni una letra de tus papeles: los nombres siguen escritos donde "
        "estaban. Lo único que hace es apuntar de quién son, para que no tengas que volver a "
        "escribirlos."
    ),
    "revision_seguras": "Se pueden apuntar",
    "revision_seguras_pista": (
        "Estos nombres están escritos igual en todas partes, así que son la misma persona o la misma "
        "empresa."
    ),
    "revision_mirar": "Estos los tienes que mirar tú",
    "revision_mirar_pista": (
        "El programa no los junta solo, y no es un fallo: son nombres que se parecen, y juntar a dos "
        "que no son el mismo no se puede deshacer."
    ),
    "revision_apuntar": "APUNTAR ESTA FICHA",
    "revision_apuntar_todas": "APUNTARLAS TODAS",
    "revision_deshacer": "DESHACER ESTO",
    "revision_deshacer_pista": (
        "Quita las fichas que apuntó el programa. Las que hayas corregido tú se quedan."
    ),
    "revision_deshecho": (
        "Deshecho: {fichas} fichas quitadas y {enlaces} enlaces deshechos. Tus papeles siguen igual."
    ),
    "revision_cuantos_ya": "Ya tenías {cuantos} nombres enlazados, y esos no salen aquí.",
    "revision_motivo_el_mismo_nombre": "Está escrito igual en todas partes",
    "revision_motivo_mismo_nif": "Tienen el mismo NIF, así que son la misma empresa",
    "revision_motivo_se_parecen": (
        "Se parecen, pero no son iguales. El programa no los junta: míralos y decide tú."
    ),
    "revision_motivo_el_mismo_nombre_dos_nif": (
        "El nombre es el mismo, pero el NIF no. Pueden ser dos personas distintas, así que el programa "
        "no las junta."
    ),
    # **El caso simétrico, y el defecto más grave que ha tenido este ticket.** El NIF se usaba como
    # prueba él solo, así que un NIF tecleado mal fundía a dos personas distintas en una ficha, la
    # marcaba como «segura» y el guion la apuntaba sin avisar. Ahora, si el NIF coincide y los nombres
    # no tienen nada que ver, se enseña y decide el agricultor.
    "revision_motivo_mismo_nif_nombres_distintos": (
        "El NIF es el mismo, pero los nombres no se parecen en nada. Uno de los dos papeles está mal "
        "escrito, así que el programa no los junta: míralos y decide tú."
    ),
    "revision_nif_compartido": "Los dos papeles llevan el mismo NIF: {nifs}.",
    "revision_nombres_escritos": "Así está escrito en tus papeles:",
    "revision_volver": "VOLVER A LAS FICHAS",
    # --- Los nombres de los papeles. **Ni uno lleva la palabra «fitosanitario»**: está prohibida.
    "papeles": {
        "proveedor": "Quien te vende el producto",
        "proveedor_semilla": "Quien te vende la semilla",
        "proveedor_abono": "Quien te vende el abono",
        "comprador": "Quien te compra la cosecha",
        "asesor": "El técnico que te asesora",
        "aplicador": "Quien echa el producto",
        "transportista": "Quien te lleva la mercancía",
        "taller": "El taller donde arreglas las máquinas",
        "laboratorio": "El laboratorio donde mandas las muestras",
        "veterinario": "El veterinario",
        "arrendador": "Quien te alquila la tierra",
        "otro": "Otra cosa",
    },
    # --- De dónde sale cada nombre escrito: lo dice la tabla donde está, no una frase suelta.
    #
    # **Hay una clave por cada puerta de `contactos.ENLACES`, y ni una más.** Aquí había una de más
    # (`tabla_almacen`, de la puerta `articulos.proveedor`) que se quedó cuando se quitó esa puerta al
    # descubrir que esa columna no existe: texto muerto que nadie pide. Lo encontró el propio informe
    # del ticket y lo quitó esta ronda. Hay una prueba que ata esta lista a las puertas de verdad.
    "tabla_facturas": "Una factura",
    "tabla_albaranes": "Un albarán",
    "tabla_ventas": "Una venta",
    "tabla_analisis": "Un análisis",
    "tabla_productos": "Un producto de los que compras",
    "tabla_aplicadores": "Quien echa el producto",
    "tabla_asesores": "Un asesor",
}

MENSAJES_DE_LOS_CONTACTOS: dict[str, str] = {
    # Las dos cosas que sí se exigen a un canal (Entrega 2, 13/10/2026).
    "C7_esa_clase_de_canal_no_existe": "Eso no es un teléfono, un correo ni una dirección.",
    "C7_un_canal_necesita_algo_escrito": "Escribe el teléfono, el correo o la dirección.",
    # Lo único que se le exige a una próxima acción (Entrega 3, 13/10/2026): que se sepa qué hay que hacer.
    "C7_una_tarea_necesita_titulo": "Escribe qué hay que hacer.",
    # **El 404 de este módulo** (13/10/2026). Faltaba: se usaba en tres sitios y **no existía en ningún
    # diccionario**, así que en vez de contestar 404 el programa **reventaba con un KeyError** —un 500
    # donde tiene que haber un 404—. Lo encontró una prueba de aislamiento, no una lectura. Y las palabras
    # no confirman que exista: lo mismo que en el resto de la casa, no se contesta «no es tuyo».
    "C7_no_existe": "Eso no está en tu cuaderno.",
    # La accion ya se guardo, pero con otro texto o en otro contacto (13/10/2026, revision). Se dice
    # lo que pasa y que NO se ha cambiado nada, para que el agricultor no crea que su texto nuevo esta
    # guardado: lo que escribio sigue en la pantalla, y volver a pulsar lo apunta como nota nueva.
    "C7_la_accion_ya_se_guardo_de_otra_manera": (
        "Esta acción ya se había guardado, pero con otro texto. No se ha cambiado nada: lo que has escrito sigue aquí, y si vuelves a pulsar se apunta como nota nueva."
    ),
    # Una nota vacía no es una nota (CRM-03, criterio (f), 11/10/2026).
    "C7_una_nota_necesita_texto": "Una nota tiene que decir algo. Escribe lo que quieras apuntar.",
    # --- Lo que se le dice cuando algo no se puede hacer, siempre con la salida
    "C2_eso_no_se_puede_enlazar": (
        "Ese nombre no se puede enlazar desde aquí. Vuelve a las fichas y busca el nombre entre los "
        "que ya tienes escritos."
    ),
    "C3_eso_no_se_puede_juntar_solo": (
        "Esos nombres se parecen, pero el programa no puede asegurar que sean la misma persona, así "
        "que no los junta. Apunta una ficha y enlaza con ella los nombres que tú sepas que son suyos. "
        "Si de verdad son el mismo, el camino es ese: uno por uno."
    ),
    "C4_la_propuesta_ha_cambiado": (
        "La lista de nombres ha cambiado desde que la miraste, así que no he apuntado nada. Vuelve a "
        "mirarla y apunta lo que quieras: así lo que se apunte es lo que has visto."
    ),
    "C5_ahi_no_hay_nombre": (
        "En ese papel no hay ningún nombre escrito, así que no hay nada que enlazar. Escribe primero "
        "el nombre en el papel y vuelve aquí."
    ),
    "C6_ese_papel_no_existe": (
        "Ese papel no es de los que se pueden marcar ({papeles}). Marca uno de los de la lista."
    ),
    "C7_un_contacto_necesita_nombre": (
        "Falta el nombre. Sin nombre no se sabe de quién es la ficha: escríbelo y guárdala."
    ),
    "C8_no_has_elegido_ninguna": (
        "No has elegido ninguna ficha, así que no he apuntado nada. Marca las que quieras y vuelve a "
        "pulsar el botón."
    ),
    "C9_esta_ficha_es_tuya": (
        "{nombre} no se ha quitado: la has corregido o le has enlazado algo tú, así que es tuya."
    ),
    "C10_ese_nombre_ya_tiene_dueno": (
        "Ese nombre ya está enlazado con la ficha {nombre}. Si no es la misma persona, quítalo de "
        "allí primero."
    ),
    # El reenvío de la misma confirmación (el doble toque con guantes, el móvil lento). Antes salía
    # «la lista ha cambiado», que era mentira: lo que había pasado es que el propio programa ya la
    # había apuntado. El contrato pide que reenviar devuelva su resultado, y eso es lo que hace.
    "C11_ya_estaba_apuntada": (
        "Esa ficha ya estaba apuntada de antes, así que no se ha apuntado dos veces. Mírala en tu "
        "lista: está con el nombre {nombre}."
    ),
}

MENSAJES.update(MENSAJES_DE_LOS_CONTACTOS)

# --------------------------------------------------------------------------
# Lo que se le dice al agricultor sobre el dinero (T12, E6, 03/10/2026)
#
# Todos llevan **qué pasa y qué hago ahora**, que es la estructura obligatoria de este programa, y
# los que bloquean lo dicen con todas las letras. Los cuatro que importan:
#
#   · `D1` — el A08 del contrato: cantidad conocida e **importe pendiente**. No es un error: es un
#     dato que aún no se sabe, y el mensaje dice cómo se arregla (poniendo el precio).
#   · `D3` — el A06: un cobro parcial deja un pendiente, y se dice el número exacto.
#   · `D5` — una entrega sin importe no se puede facturar. Se dice por qué y qué hacer.
#   · `D6` — dos entregas, una factura: lo que impide contar el dinero dos veces. Se dice cuál es la
#     factura donde ya está, para que el agricultor no tenga que buscarla.
# --------------------------------------------------------------------------
MENSAJES_DE_LAS_VENTAS: dict[str, str] = {
    "D1_importe_pendiente_de_saber": (
        "De esta entrega se sabe lo que salió y no por cuánto, así que no se cuenta como ingreso. "
        "Cuando sepas el precio o el importe, ponlo y la cuenta se hace sola."
    ),
    "D2_importe_negativo": (
        "Un importe no puede ser negativo. Si lo que pasó es que te devolvieron mercancía o te "
        "descontaron algo, apúntalo como devolución o como ajuste de esa entrega."
    ),
    "D3_falta_por_cobrar": (
        "De esta factura llevas cobrado {cobrado} de {total}: quedan {pendiente} por cobrar."
    ),
    "D4_cobro_mas_que_lo_que_se_debe": (
        "Has apuntado {importe} y de esa factura solo faltaban {pendiente} por cobrar. A la factura "
        "van {imputado} y los {sobrante} que sobran se quedan sin asignar, hasta que sepas a qué van."
    ),
    "D5_sin_importe_no_se_puede_facturar": (
        "Esa entrega no se puede facturar todavía porque no se sabe por cuánto. Ponle el importe o el "
        "precio, y vuelve a facturarla."
    ),
    "D6_esa_entrega_ya_esta_facturada": (
        "Esa entrega ya está dentro de la factura {numero}. Una entrega no puede estar en dos "
        "facturas: si te has equivocado, quita la factura y vuelve a hacerla con las que quieras."
    ),
    "D7_el_ajuste_necesita_origen": (
        "Un ajuste que cambia el importe tiene que decir de dónde sale. Elige quién lo dice y "
        "escríbelo: si no, dentro de un año nadie sabe por qué ese número es ese."
    ),
    "D8_el_cobro_tiene_que_ser_mayor_que_cero": (
        "Un cobro de cero euros no es un cobro. Escribe lo que de verdad ha entrado."
    ),
    "D9_esa_factura_no_se_puede_quitar": (
        "Esa factura tiene cobros apuntados, así que no se quita: primero quita los cobros y después "
        "la factura. Así el dinero que ha entrado no desaparece de tus cuentas."
    ),
    "D10_no_hay_nada_que_facturar": (
        "No has marcado ninguna entrega, así que no he hecho ninguna factura. Marca las que quieras "
        "juntar y vuelve a pulsar el botón."
    ),
    # Una cosecha de la que sale una entrega no se puede borrar (T12): la entrega se quedaría diciendo que
    # salió de algo que ya no existe. Las dos formas, singular y plural, que es como se cuenta todo aquí.
    "D11_esa_cosecha_la_usa_una_entrega_uno": (
        "Esa cosecha la usa 1 entrega: dice que la partida salió de ahí. Corrige primero la entrega —o "
        "quítale esa cosecha— y después podrás borrarla."
    ),
    "D11_esa_cosecha_la_usa_una_entrega_varios": (
        "Esa cosecha la usan {cuantos} entregas: dicen que la partida salió de ahí. Corrige primero las "
        "entregas —o quítales esa cosecha— y después podrás borrarla."
    ),
    # ----------------------------------------------------------------------
    # Los tres mensajes de la revisión del T12 (03/10/2026): cada uno cierra un defecto medido.
    # ----------------------------------------------------------------------
    #
    # D12 — un importe que no cabe donde se guarda. La columna del dinero admite 24 cifras y un importe de
    # veintidós cifras enteras salía como un texto de 27: **en SQLite entraba y en PostgreSQL tumbaba la
    # operación entera**. El tope no es el de la columna sino el de una venta que puede ser de verdad.
    "D12_ese_importe_es_demasiado_grande": (
        "Ese importe es demasiado grande: como mucho se pueden apuntar {maximo} en un sitio. Mira si te "
        "sobra alguna cifra."
    ),
    # D13 — un texto más largo de lo que cabe en su columna. Es el mismo defecto del rastro, pero con el
    # nombre del agricultor: en PostgreSQL la fila no entra y se pierde el apunte entero.
    "D13_algo_es_mas_largo_de_lo_que_cabe": (
        "Uno de los textos que has escrito es más largo de lo que cabe en su sitio, así que no lo he "
        "guardado. Acórtalo y vuelve a apuntarlo."
    ),
    # D14 — la misma entrega dos veces en la misma petición de facturar. Antes salía el aviso de «ya está
    # dentro de la factura .» —con el hueco en blanco— y decía algo que no era: esa entrega no estaba en
    # ninguna factura, lo que pasaba es que venía repetida.
    "D14_esa_entrega_viene_repetida": (
        "Esa entrega está dos veces en la misma factura, así que no he hecho ninguna: quita la que sobra "
        "y vuelve a hacerla."
    ),
}

MENSAJES.update(MENSAJES_DE_LAS_VENTAS)


# --------------------------------------------------------------------------
# La maquinaria de la finca (T14, E8, 03/10/2026)
# --------------------------------------------------------------------------
#
# LAS PALABRAS DE ESTA SECCIÓN TIENEN UN TRABAJO DIFÍCIL, y conviene saber cuál antes de tocarlas:
#
#  1. **Separar cinco cosas que se parecen.** ITV, ITEAF, mantenimiento, seguro y ROMA no son lo mismo,
#     y el documento de la casa avisa de la confusión más común: «No llamar a ITEAF "ITV" en las
#     etiquetas» (`docs/MATRIZ_NORMATIVA_CRM.md`, N09). Por eso cada una lleva su nombre y **una frase
#     que dice qué es**, en palabras que se entiendan sin haber leído un real decreto.
#  2. **Decir lo que no se sabe sin que suene a fallo del programa.** Cuando una obligación aplica y no
#     hay ni una inspección apuntada, la pantalla no puede enseñar una fecha ni quedarse en blanco:
#     dice que no lo sabe y **qué hay que mirar** (la clasificación técnica, que está en el papel).
#     Ese es el «lo dice y lo pregunta» que pide el contrato, y sus frases están aquí.
#  3. **No prometer lo que el programa no hace.** Ningún texto de esta sección dice que una máquina
#     «está en regla» por su nombre ni por su clase: eso lo decide el papel, y el programa solo lo copia.
MAQUINARIA_DE_LA_FINCA: dict[str, str] = {
    # ── La pantalla de la lista ──
    "titulo": "Mi maquinaria",
    "explica": (
        "Aquí están tus máquinas: el tractor, el remolque, los aperos y los equipos con los que echas "
        "el producto. De cada una se apunta qué le toca pasar y cuándo, con el papel que lo demuestra."
    ),
    "cuantas": "Tienes {cuantos} máquinas apuntadas.",
    "cuantas_uno": "Tienes 1 máquina apuntada.",
    "sin_maquinas": (
        "Todavía no has apuntado ninguna máquina. Empieza por la que más uses: el tractor. Apúntala y "
        "después le dices qué le toca pasar."
    ),
    "nueva": "APUNTAR UNA MÁQUINA",
    # Lo que se dice al traer a la lista un equipo del cuaderno: se dice **qué se ha traído**, porque
    # también se ha traído su última inspección y su número de ROMA.
    "equipo_traido": (
        "Ya está en la lista, con lo que ya tenías apuntado del cuaderno. Mírale la clasificación técnica "
        "y contesta lo que le toca."
    ),
    "buscar": "BUSCAR",
    "buscar_pista": "Escribe las primeras letras de su nombre",
    "ver_todas": "VER TODAS",
    # Un hueco se enseña diciendo que está vacío, nunca en blanco: un renglón sin nada al lado parece un
    # fallo del programa, y en una ficha de máquina los huecos son normales (no todo se sabe).
    "sin_decir": "Falta decirlo",
    "sin_resultados": (
        "Ninguna de tus máquinas se llama así. Prueba con otras letras o pulsa VER TODAS para verlas "
        "todas otra vez."
    ),
    "abrir": "VER ESTA MÁQUINA",
    "situacion": "Cómo está:",
    # Lo de anular, que **no es borrar**: lo anulado se queda en el cuaderno, tachado, y deja de contar.
    "anular": "ANULAR",
    "motivo_anulacion": "¿Por qué lo anulas?",
    "anular_confirmar": "ANULARLO CON ESTE MOTIVO",
    "anular_inspeccion": "Anular esta inspección",
    "anular_averia": "Anular esta avería",
    "anular_pista": (
        "Lo que anulas se queda en tu cuaderno, tachado y con el motivo escrito, pero deja de contar: no "
        "se mira para saber cuándo le toca la próxima. Si lo que quieres es quitarlo del todo, se borra."
    ),
    "anular_necesita_motivo": (
        "Para anularlo hace falta el motivo: dentro de un año, ese motivo es lo único que explicará por "
        "qué está tachado. Escríbelo y vuelve a pulsar el botón."
    ),
    "anulada": "Ya está anulado, con su motivo.",
    # El bloque de los equipos que ya estaban en el cuaderno: ver `EquipoSinFichaSalida`.
    "equipos_sin_ficha": "Equipos de echar producto que todavía no están en esta lista",
    "equipos_explica": (
        "Estos equipos los apuntaste para el cuaderno de la Junta. Aquí no están todavía porque esta "
        "lista es más nueva y sirve para todo, no solo para los equipos de echar producto. Si son los "
        "mismos, tráelos: no se pierde nada de lo que ya estaba escrito."
    ),
    "traer_equipo": "TRAERLO A LA LISTA",
    # Lo que el programa no sabe calcular, dicho en la pantalla y no solo en un comentario.
    "que_falta_titulo": "Lo que este programa todavía no calcula",
    "que_falta_explica": (
        "Se dice para que no te fíes de una fecha que no está: cuando el programa no tiene la fuente "
        "de un plazo, no se la inventa. Las fechas que ves son las que traen tus papeles."
    ),
    "que_falta_para_que": "Para qué haría falta",
    "que_falta_depende": "De quién depende",
    # ── Lo que se escribe en la tabla y en la tarjeta, ya compuesto ──
    #
    # Estas frases llevan huecos y las rellena `app.js` con lo que traiga el servidor: es la misma regla
    # que en las demás tablas (el nombre del dato es del servidor, el valor sale del cuaderno).
    "horas_corto": "h",
    "proxima_revision_texto": "{obligacion} el {fecha}",
    "sin_fecha_corto": "Falta el dato",
    # Los avisos de la tabla, con singular y plural: «1 cosas que mirar» es lo primero que hace
    # desconfiar de un programa.
    "faltan_por_saber_uno": "1 más sin fecha",
    "faltan_por_saber_varios": "{cuantas} más sin fecha",
    "papeles_uno": "1 papel",
    "papeles_varios": "{cuantas} papeles",
    "sin_papel_apuntado_uno": "1 sin papel",
    "sin_papel_apuntado_varios": "{cuantas} sin papel",
    "sin_inspecciones_corto": "Sin inspecciones",
    "avisos_uno": "1 cosa que mirar",
    "avisos_varios": "{cuantas} cosas que mirar",
    # **Las mismas dos frases en corto, para la celda de la tabla.** Con nueve columnas, «4 cosas que
    # mirar» ensancha la última hasta sacar de la pantalla los botones de la fila; en una celda, «4 avisos»
    # dice lo mismo y cabe. La frase entera sigue estando en la tarjeta del móvil y en la ficha.
    "avisos_corto_uno": "1 aviso",
    "avisos_corto_varios": "{cuantas} avisos",
    # La etiqueta del botón de una fila de la tabla, en corto: la frase entera («VER ESTA MÁQUINA») es la
    # de la tarjeta del móvil, donde hay sitio.
    "ver_corto": "VER",
    "vencida_corto": "Vencida",
    "al_caer_corto": "Caduca pronto",
    "no_favorable_corto": "Desfavorable",
    "ultima_inspeccion_texto": "La última: {fecha}",
    "averia_de_texto": "Avería del {fecha}",
    "arreglada_texto": "Arreglada el {fecha}",
    "sigue_sin_arreglar": "Sigue sin arreglar",
    "no_se_si_arreglada": "No sé si está arreglada",
    # ── Los tres formularios: la máquina, una inspección y una avería ──
    "form_nueva_titulo": "Apuntar una máquina",
    "form_nueva_pista": (
        "Con el nombre y las tres preguntas de abajo ya queda apuntada. Lo demás se puede dejar en "
        "blanco y ponerse otro día: en un hueco no se escribe nada."
    ),
    "form_corregir_titulo": "Corregir esta máquina",
    "form_corregir_pista": (
        "Está puesto lo que apuntaste. Cambia lo que esté mal: lo que había antes queda guardado en el "
        "historial del cuaderno."
    ),
    "form_inspeccion_titulo": "Apuntar una inspección",
    "form_inspeccion_pista": (
        "Copia las fechas del papel. El programa no las calcula: si el papel no trae la de la próxima, "
        "se deja en blanco y la ficha dirá que no se sabe cuándo toca."
    ),
    "form_averia_titulo": "Apuntar una avería",
    "form_averia_pista": (
        "Qué pasó, cuándo y si ya está arreglada. Si la máquina no está para trabajar, se cambia aparte, "
        "en sus datos: son dos cosas distintas."
    ),
    "form_guardando": "Guardando…",
    "campo_tipo_inspeccion": "¿Qué le han pasado?",
    "campo_fecha": "¿Cuándo fue?",
    "campo_fecha_pista": "La fecha que trae el papel",
    "campo_proxima_fecha": "¿Cuándo toca la próxima?",
    "campo_proxima_fecha_pista": (
        "Si el papel la trae, cópiala. Si no, déjala en blanco: el programa no la calcula."
    ),
    "campo_documento": "¿Con qué papel?",
    "campo_documento_pista": (
        "Si lo tienes guardado en «los papeles», elígelo. Sin papel también se puede apuntar, y la ficha "
        "dirá que no lo trae."
    ),
    "sin_papeles_guardados": (
        "No tienes ningún papel guardado. Puedes apuntar la inspección igual y guardar el papel después "
        "en «los papeles»."
    ),
    "campo_notas": "Notas",
    "campo_fecha_averia": "¿Cuándo pasó?",
    "campo_que_paso": "¿Qué pasó?",
    # ── Los datos de una máquina, en su ficha ──
    "seccion_datos": "Los datos de la máquina",
    # **Las clases de máquina son NUESTRAS**, y se dice en la pantalla: la tabla oficial de
    # clasificaciones técnicas por máquina no está transcrita (L07), así que esto solo sirve para leer la
    # lista de un vistazo y **no decide qué inspecciones le tocan**. Eso lo dice el papel, y se pide aparte.
    "clase_tractor": "Tractor",
    "clase_remolque": "Remolque",
    "clase_apero": "Apero",
    "clase_cosechadora": "Cosechadora",
    "clase_equipo_de_aplicacion": "Equipo de echar producto",
    "clase_otro": "Otra cosa",
    "clase": "¿Qué es?",
    "clase_pista": (
        "Para leer tu lista de un vistazo. No decide qué inspecciones le tocan: eso depende de la "
        "clasificación técnica, que se pregunta más abajo."
    ),
    "nombre": "¿Cómo la llamas?",
    "nombre_pista": "Como la llamas tú: «el Landini», «el remolque grande»",
    "marca": "Marca",
    "modelo": "Modelo",
    "anio": "Año",
    "matricula": "Matrícula",
    "matricula_pista": "Si la tiene: los tractores, los remolques y las cosechadoras",
    "numero_serie": "Número de serie",
    "numero_serie_pista": "Lo traen los aperos que no llevan matrícula",
    "numero_roma": "Número del ROMA",
    "numero_roma_pista": (
        "El número de inscripción en el registro de maquinaria, si lo tiene. No lo pongas si no lo sabes: "
        "un número inventado es peor que un hueco."
    ),
    # **La clasificación técnica: el campo que impide la trampa del ticket.** Se pide tal cual lo dice el
    # papel, sin lista cerrada (la tabla oficial de clasificaciones no está transcrita: L07) y sin adivinar.
    "clasificacion": "¿Cómo clasifica el papel a esta máquina?",
    "clasificacion_pista": (
        "Lo pone en la ficha del ROMA o en el papel de la última inspección, con sus palabras: por "
        "ejemplo, «pulverizador arrastrado». No lo deduzcas por el nombre: de esto depende qué "
        "inspecciones le tocan. Si no lo sabes, déjalo en blanco."
    ),
    "sin_clasificacion": "Sin decir la clasificación",
    "clasificacion_falta": (
        "Falta la clasificación técnica de esta máquina, que es lo que dice qué inspecciones le tocan. "
        "Mírala en la ficha del ROMA o en el papel de la última inspección y escríbela aquí."
    ),
    "horas": "Horas del cuenta-horas",
    "horas_pista": "Si la máquina lo tiene y lo has mirado. Déjalo en blanco si no lo sabes",
    "notas": "Notas",
    "notas_pista": "Lo que quieras apuntar: dónde duerme, quién la lleva…",
    # Propiedad: las tres respuestas.
    "propiedad": "¿Es tuya o alquilada?",
    "propiedad_propia": "Es mía",
    "propiedad_alquilada": "Es alquilada",
    "propiedad_no_se": "No lo sé",
    # Disponibilidad: las tres respuestas, y «no lo sé» es una de verdad.
    "disponibilidad": "¿Puedes contar con ella para trabajar?",
    "disponibilidad_disponible": "Sí puedo",
    "disponibilidad_no_disponible": "No puedo",
    "disponibilidad_no_se": "No lo he mirado",
    "disponibilidad_pista": (
        "No se adivina por las averías ni por las fechas: una máquina con una avería apuntada puede "
        "estar trabajando igual, y quien lo sabe eres tú."
    ),
    # ── Las cinco obligaciones ──
    "seccion_obligaciones": "Lo que tiene que pasar esta máquina",
    "seccion_obligaciones_explica": (
        "Se pregunta una por una porque no son lo mismo. Y de algunas no se puede saber por el nombre "
        "de la máquina: depende de su clasificación técnica, que es la que está en el papel."
    ),
    "obligacion_itv": "ITV",
    "obligacion_iteaf": "ITEAF",
    "obligacion_mantenimiento": "Mantenimiento",
    "obligacion_seguro": "Seguro",
    "obligacion_roma": "ROMA",
    "que_es_itv": "La inspección técnica del vehículo, como la del coche.",
    "que_es_iteaf": "La inspección de las máquinas con las que se echa el producto. No es la ITV.",
    "que_es_mantenimiento": "El repaso que le das tú: el aceite, los filtros, las cuchillas.",
    "que_es_seguro": "La póliza de la máquina. La del coche y la de la cosecha no son la misma.",
    "que_es_roma": "Su número en el registro de maquinaria, que es lo que pide el cuaderno.",
    "aplicabilidad": "¿Le toca?",
    "aplicabilidad_si": "Sí le toca",
    "aplicabilidad_no": "No le toca",
    "aplicabilidad_no_se": "No lo sé",
    "de_donde_sale": "¿De dónde sale eso?",
    "de_donde_sale_pista": (
        "Es lo que te van a preguntar: no es lo mismo que lo diga un papel que que lo digas tú."
    ),
    "origen_documento": "Lo dice el papel",
    "origen_el_agricultor": "Lo digo yo",
    "origen_no_se": "No lo sé",
    "lo_que_dice_la_norma": "De dónde sale esta obligación",
    "guarda_el_papel": (
        "Los papeles de las inspecciones hay que poder enseñarlos tres años. Si los guardas en «los "
        "papeles», deja aquí apuntado cuál es."
    ),
    # ── El estado de cada obligación, con sus palabras ──
    #
    # **Cada estado dice lo mismo con palabras y no solo con un color** (regla de la casa): «Vencida el
    # 12/05/2026» se lee igual en un móvil al sol que en una captura en blanco y negro.
    "situacion_no_se_si_toca": "No se sabe si le toca",
    "situacion_no_aplica": "No le toca",
    "situacion_sin_inspeccion": "No hay ninguna apuntada",
    # Hay una fecha escrita y no hay ninguna inspección de la que salga: se sabe cuándo toca y no cuándo
    # fue la última. Es el caso del equipo del cuaderno que traía la fecha de la próxima ITEAF sin la de
    # la última, y decirlo así es lo único honesto.
    "situacion_sin_la_ultima": "Toca el {fecha}, pero no se sabe cuándo fue la última",
    "situacion_no_favorable": "La última salió desfavorable",
    "situacion_sin_fecha": "No se sabe cuándo toca la próxima",
    "situacion_vencida": "Vencida el {fecha}",
    "situacion_proxima": "Caduca el {fecha}",
    "situacion_vigente": "Hasta el {fecha}",
    "sin_fecha_apuntada": "Falta la fecha",
    "resultado": "¿Cómo salió?",
    "resultado_favorable": "Favorable",
    "resultado_desfavorable": "Desfavorable",
    "resultado_no_consta": "No lo pone el papel",
    "proxima_fecha": "¿Cuándo toca la próxima?",
    "ultima_inspeccion": "La última fue el {fecha}",
    "documento": "¿Con qué papel lo apuntas?",
    "con_papel": "Con su papel",
    "sin_papel": "Sin papel apuntado",
    # **El papel, con su nombre y su botón para abrirlo.** La ficha decía solo «Con su papel»: no decía
    # **cuál** era ni dejaba verlo, y el papel es justo lo que se enseña en una inspección (lo encontró la
    # revisión del ticket). Con esto, el agricultor lee el nombre del papel que demuestra la inspección y
    # lo abre de un toque.
    "ver_papel": "VER EL PAPEL",
    "papel_sin_nombre": "El papel que tienes guardado",
    "sin_papel_pista": (
        "De esta inspección no has apuntado ningún papel. Cuando lo tengas, guárdalo en «los papeles» y "
        "dilo aquí: en una inspección es lo que te van a pedir."
    ),
    # ── Las inspecciones y las averías ──
    "seccion_inspecciones": "Lo que le han pasado, con su fecha",
    "sin_inspecciones": (
        "De esta máquina no hay ninguna inspección apuntada. Lo que le toque lo dice su clasificación "
        "técnica: mírala en el papel y apunta la última que le hayan pasado."
    ),
    "apuntar_inspeccion": "APUNTAR UNA INSPECCIÓN",
    "inspeccion_de": "Inspección de {obligacion}",
    "seccion_averias": "Averías",
    "sin_averias": "No has apuntado ninguna avería.",
    "apuntar_averia": "APUNTAR UNA AVERÍA",
    "que_paso": "¿Qué pasó?",
    "que_paso_pista": "En dos palabras: «se rompió el eje del ventilador»",
    "resuelta": "¿Ya está arreglada?",
    "resuelta_si": "Ya está arreglada",
    "resuelta_no": "Sigue sin arreglar",
    "resuelta_no_se": "No lo sé",
    # **El rótulo de los papeles y su aviso de los tres años.** `guarda_el_papel` es el único texto del
    # proyecto que dice que los papeles de las inspecciones hay que poder enseñarlos **tres años**
    # (artículo 16.3 del RD 1311/2012, en `LO_QUE_OBLIGA_LA_LEY.md`), y estaba escrito y sin enseñar en
    # ningún sitio: la revisión del ticket lo cazó. Ahora se lee en la ficha, debajo de las inspecciones.
    "papeles_titulo": "Los papeles de las inspecciones",
    "guarda_el_papel": (
        "Los papeles de las inspecciones hay que poder enseñarlos tres años. Si los guardas en «los "
        "papeles», deja aquí apuntado cuál es."
    ),
    "fecha_resuelta": "¿Cuándo se arregló?",
    "horas_de_la_averia": "Horas del cuenta-horas cuando pasó",
    # ── La calculadora de «¿puedo cogerla hoy?», que es el aviso al planificar un trabajo ──
    "avisos_titulo": "Antes de contar con ella",
    "sin_avisos": "De esta máquina no hay nada que mirar ahora mismo.",
    "urgente": "Míralo antes de usarla",
    "mirar_cuando_puedas": "Míralo cuando puedas",
    # ── El alta y la corrección ──
    "guardar": "GUARDAR LA MÁQUINA",
    "guardado": "Ya está guardada.",
    "corregida": "Ya está corregido. Lo que había antes queda guardado en el historial.",
    "que_es_equipo": "Una máquina",
    "es_el_equipo_del_cuaderno": "¿Es uno de los equipos que apuntaste para el cuaderno?",
    "es_el_equipo_del_cuaderno_pista": (
        "Si esta máquina es la misma que ya tenías apuntada como equipo para echar producto, elígela "
        "aquí: así no se escribe dos veces."
    ),
    "ningun_equipo": "No es ninguno de esos",
    "el_equipo_que_ya_estaba": "El equipo que ya estaba enlazado",
}

# Los mensajes de la maquinaria. Los siete primeros (M1 a M10) son **avisos de verdad**, y por eso
# llevan la marca de urgencia y salen en la lista y en la ficha; los demás son los que se dicen cuando
# algo no se puede hacer, y **todos dicen qué hacer ahora** (la regla de la casa).
MENSAJES_DE_LA_MAQUINARIA: dict[str, str] = {
    "M1_la_maquina_no_esta_disponible": (
        "«{maquina}» está apuntada como que no puedes contar con ella. Si ya está para trabajar, "
        "cámbialo en su ficha y podrás usarla."
    ),
    "M2_no_se_si_esta_disponible": (
        "De «{maquina}» no has dicho si puedes contar con ella. Dilo en su ficha: así no te llevas la "
        "sorpresa el día que la necesites."
    ),
    "M3_tiene_una_averia_sin_arreglar": (
        "«{maquina}» tiene una avería apuntada el {fecha} que sigue sin arreglar: {que}. Si ya está "
        "arreglada, márcala en su ficha."
    ),
    "M4_una_inspeccion_esta_vencida": (
        "La {obligacion} de «{maquina}» venció el {fecha}. Pide cita antes de usarla y, cuando la "
        "pases, apunta la fecha que traiga el papel."
    ),
    "M5_una_inspeccion_caduca_pronto": (
        "La {obligacion} de «{maquina}» caduca el {fecha}: quedan {dias} días. Pide cita con tiempo."
    ),
    "M6_la_ultima_inspeccion_no_fue_favorable": (
        "La última {obligacion} de «{maquina}» salió desfavorable. Hasta que la vuelvas a pasar, esa "
        "máquina no está en regla: pide cita y apunta lo que diga el papel nuevo."
    ),
    "M7_no_hay_ninguna_inspeccion_apuntada": (
        "De «{maquina}» no hay ninguna {obligacion} apuntada, así que no se sabe cuándo le toca. Mira "
        "el papel de la última y apúntala en su ficha."
    ),
    "M8_la_inspeccion_no_trae_la_proxima_fecha": (
        "La última {obligacion} de «{maquina}» no trae la fecha de la próxima, así que el programa no "
        "puede avisarte. Si el papel la pone, cópiala en su ficha."
    ),
    "M9_no_se_si_esa_inspeccion_le_toca": (
        "No has dicho si a «{maquina}» le toca la {obligacion}. Eso depende de su clasificación "
        "técnica: mírala en el papel y contéstalo en su ficha."
    ),
    # M20 — hay una fecha de la próxima escrita y no hay ninguna inspección de la que salga (el equipo del
    # cuaderno que traía la próxima ITEAF sin la última). Se dice la fecha —que es del agricultor— y qué
    # falta por apuntar.
    "M20_esta_la_proxima_pero_no_la_ultima": (
        "De «{maquina}» está apuntado que la próxima {obligacion} toca el {fecha}, pero no cuándo fue la "
        "última. Mira el papel y apunta su fecha en la ficha."
    ),
    "M10_dice_que_no_aplica_sin_decir_de_donde_sale": (
        "De «{maquina}» está apuntado que la {obligacion} no le toca, pero no de dónde sale eso. Di si "
        "lo dice un papel o lo dices tú: es lo primero que te van a preguntar."
    ),
    "M11_esa_maquina_necesita_nombre": (
        "Una máquina sin nombre no se puede apuntar: dentro de un año no sabrías cuál es. Escríbele "
        "cómo la llamas y vuelve a guardarla."
    ),
    "M12_eso_no_es_una_clase_de_maquina": (
        "«{valor}» no es una de las clases de máquina que se pueden elegir, así que no lo he guardado. "
        "Elige una de la lista."
    ),
    "M13_eso_no_es_una_de_las_respuestas": (
        "«{valor}» no es una de las respuestas que se pueden elegir, así que no lo he guardado. Elige "
        "una de la lista."
    ),
    "M14_esa_maquina_no_se_puede_quitar": (
        "Esa máquina la usan {cuantas} apuntes del cuaderno, así que no se quita: se quedarían sin "
        "decir con qué se trabajó. Si ya no la tienes, cámbiale el nombre para que se vea —por ejemplo "
        "«vendido»— y quítale la disponibilidad."
    ),
    "M15_ese_equipo_ya_esta_en_la_lista": (
        "Ese equipo del cuaderno ya es «{maquina}»: un equipo es una máquina, no dos, así que no lo he "
        "traído otra vez. Abre «{maquina}» y cámbialo ahí si le falta algo."
    ),
    "M17_eso_no_es_una_de_las_cinco_cosas": (
        "«{valor}» no es una de las cinco cosas que hay que pasarle a una máquina, así que no lo he "
        "guardado. Elige una de las cinco."
    ),
    # M19 — quitar una máquina con inspecciones o averías dentro. Se dice **cuántas cosas** hay y qué
    # hacer, y con singular y plural porque con una sola se leía «1 inspecciones».
    "M19_esa_maquina_tiene_cosas_apuntadas_uno": (
        "Esa máquina tiene 1 inspección o avería apuntada, y si la quito se pierde lo que le pasaron. "
        "Bórrala o anúlala primero y después podrás quitar la máquina."
    ),
    "M19_esa_maquina_tiene_cosas_apuntadas_varios": (
        "Esa máquina tiene {cuantas} inspecciones o averías apuntadas, y si la quito se pierde lo que "
        "le pasaron. Bórralas o anúlalas primero y después podrás quitar la máquina."
    ),
}

MENSAJES.update(MENSAJES_DE_LA_MAQUINARIA)


# --------------------------------------------------------------------------
# Las cuentas de la explotación (T13, E7, 05/10/2026)
# --------------------------------------------------------------------------
#
# POR QUÉ ESTE VOCABULARIO ES TAN LARGO, Y POR QUÉ ESO ES LO CORRECTO AQUÍ. Esta pantalla es la
# primera del programa donde hay que decir **«no lo sé»** muchas veces y de muchas maneras: falta el
# importe de un gasto, falta la superficie de una tierra, falta saber a qué va un coste, falta saber
# si una ayuda se ha cobrado. Cada una de esas cosas se dice con su frase y **dice qué hacer**, que es
# la regla de la casa: describir el problema y callarse no vale.
#
# Y las listas cerradas (las categorías, los métodos de reparto, las formas de pago) llevan **su
# orden y su nombre**, y el orden no se saca de las claves del diccionario: unos botones que cambian
# de sitio se pulsan mal.

# ---------------------------------------------------------------------------
# **Lo que hay que hacer** (Entrega 3, 13/10/2026): la lista de próximas acciones, cruzando fichas.
# ---------------------------------------------------------------------------
TAREAS: dict = {
    "titulo": "Lo que hay que hacer",
    "pista": (
        "Lo próximo, de todos tus contactos. Lo vencido se queda vencido: el programa no lo cancela por su cuenta."
    ),
    "todas": "Todas",
    "de_hoy": "Para hoy",
    "vencidas": "Vencidas",
    "sin_fecha": "Sin fecha",
    "cargando": "Mirando lo que tienes…",
    "que": "Qué hay que hacer",
    "cuando": "Para cuándo",
    "quien": "Quién",
    "con_quien": "Con quién",
    "vencida": "Vencida",
    "ver_la_ficha": "Ver la ficha",
    "hecha": "Hecha",
    "cancelar": "Cancelar",
    "ya_hecha": "Ya hecha",
    "ya_cancelada": "Cancelada",
    "no_hay_ninguna": "No hay nada apuntado. Cuando apuntes algo, sale aquí.",
}

GASTOS: dict = {
    # **El camino de vuelta a la ficha del proveedor** (Entrega 1, 13/10/2026).
    "ficha_del_proveedor": "Ver la ficha de su proveedor",
    "titulo": "Mis cuentas",
    "explica": (
        "Aquí está lo que te ha costado, a qué va y cuánto te queda por pagar. Lo que no sepas se "
        "queda en blanco y el programa te lo dice: un hueco no es un cero."
    ),
    "cuantas": "Tienes {cuantos} gastos apuntados.",
    "cuantas_uno": "Tienes 1 gasto apuntado.",
    "sin_gastos": (
        "Todavía no has apuntado ningún gasto. Empieza por el que tengas el papel a mano: el abono, "
        "el gasóleo o la reparación. Si no sabes lo que costó, apúntalo igual y se queda en blanco."
    ),
    "sin_resultados": (
        "Ningún gasto coincide con lo que buscas. Prueba con otras letras o pulsa VER TODAS para "
        "verlos todos otra vez."
    ),
    "nuevo": "APUNTAR UN GASTO",
    "nuevo_pago": "APUNTAR UN PAGO",
    "nueva_inversion": "APUNTAR UNA INVERSIÓN",
    "nueva_ayuda": "APUNTAR UNA AYUDA",
    "buscar": "BUSCAR",
    "buscar_pista": "Escribe las primeras letras del concepto o del proveedor",
    "ver_todas": "VER TODAS",
    "abrir": "VER ESTE GASTO",
    "corregir": "CORREGIR",
    "anular": "ANULAR",
    "anular_motivo": "¿Por qué lo anulas?",
    "rellenar": "RELLENAR EL IMPORTE",
    "importe": "Lo que costó",
    "pagado": "Pagado",
    "pendiente": "Falta por pagar",
    "como_esta": "Cómo está",
    "proveedor": "Proveedor:",
    "su_tierra": "Va a",
    "su_cuenta": "La cuenta de este gasto",
    "no_se_sabe": "No lo sé",
    "sin_asignar_corto": "Sin asignar",
    "sin_asignar_explica": (
        "Lo que está sin asignar es un coste que ya sabes que existe pero todavía no está en ninguna "
        "tierra. Sigue contando en tus cuentas: lo único que falta es decir a dónde va."
    ),
    "estado_sin_importe": "Falta saber lo que costó",
    "estado_sin_pagar": "Sin pagar",
    "estado_pagado_en_parte": "Pagado a medias",
    "estado_pagado": "Pagado",
    "estado_vencido": "Vencido",
    "estado_anulado": "Anulado",
    "esta_anulado": "Esto está anulado, con su motivo. Sigue aquí para que sepas que estuvo.",
    "esta_anulada": "Esta compra está anulada.",
    "cuadre_titulo": "Las cuentas de este gasto",
    "cuadre_entero": "Lo que costó",
    "cuadre_repartido": "En tierras, cultivos o máquinas",
    "cuadre_sin_asignar": "Sin asignar",
    "cuadre_no_cierra": (
        "Estas cuentas no cierran: hay una parte del gasto que no está ni en un sitio ni en el otro. "
        "Míralo y repártelo otra vez."
    ),
    "todavia_sin_reparto": (
        "Todavía no has dicho a qué tierra o cultivo va este gasto. Sigue contando en tus cuentas, "
        "pero está sin asignar."
    ),
    "reparto_metodo": "Se repartió",
    "reparto_quitar": "QUITARLO DE AQUÍ",
    "repartir": "REPARTIRLO",
    "dejarlo_sin_asignar": "DEJARLO SIN ASIGNAR",
    "metodo_area": "por hectáreas",
    "metodo_horas": "por horas",
    "metodo_consumo": "por lo que se gastó en cada sitio",
    "metodo_manual": "a mano",
    "coste_titulo": "Lo que te ha costado",
    "coste_explica": (
        "Lo directo es lo que dice el papel de un gasto de esa tierra. Lo repartido lo has repartido "
        "tú. Y lo sin asignar es un coste que existe y todavía no va a ningún sitio."
    ),
    "coste_directo": "Directo",
    "coste_repartido": "Repartido",
    "coste_sin_asignar": "Sin asignar",
    "coste_total_conocido": "Total conocido",
    "cuantos_sin_importe": "Gastos de los que no sabes el importe",
    "sin_importe_explica": "De esos no se puede hacer la cuenta hasta que apuntes lo que costaron",
    "caja_titulo": "La caja",
    "caja_explica": (
        "Esto es el dinero que ha entrado y salido de verdad. No es lo mismo que el margen: puedes "
        "haber vendido mucho y no haber cobrado nada todavía."
    ),
    "caja_entrado": "Ha entrado",
    "caja_salido": "Ha salido",
    "caja_saldo": "Queda",
    "caja_por_pagar": "Falta por pagar",
    "ayudas_cobradas": "Ayudas cobradas",
    "ayudas_previstas": "Ayudas pedidas o concedidas, sin cobrar",
    "prevision_no_es_ingreso": "Esto no se suma a lo que ha entrado: todavía no es dinero tuyo",
    "margen_titulo": "El margen de cada cultivo",
    "margen_explica": (
        "Lo que has ingresado menos lo que te ha costado. Si falta el importe de un gasto, el margen "
        "no se puede calcular y aquí se dice por qué, en vez de enseñar una cifra que no es."
    ),
    "ingresos": "Has ingresado",
    "coste_conocido": "Te ha costado",
    "margen": "Margen",
    "margen_incompleto": (
        "De este cultivo no se puede calcular el margen: falta el importe de algún gasto o de algún "
        "ingreso. Apunta lo que falta y vuelve a mirarlo."
    ),
    "inversiones_titulo": "Las inversiones",
    "inversiones_explica": (
        "Un tractor o una nave no son un gasto del año: duran años. Lo que de ellos le toca a esta "
        "campaña lo dices tú, y lo que no digas se queda sin asignar y se ve aquí."
    ),
    "inversion_en_la_campana": "De esto le toca a esta campaña",
    "una_inversion_no_es_un_gasto": (
        "Una inversión no entra entera en el año en que se compra: lo que le toca a cada campaña lo "
        "dices con un reparto."
    ),
    "ayudas_titulo": "Las ayudas",
    "ayudas_explica": (
        "Lo que has pedido, lo que te han concedido y lo que has cobrado son tres cosas distintas, y "
        "aquí van separadas. Lo que todavía no has cobrado no es dinero que tengas."
    ),
    "ayuda_prevista": "Pedido",
    "ayuda_concedida": "Concedido",
    "ayuda_cobrada": "Cobrado",
    "ayuda_estado_prevista": "Pedida, sin resolver",
    "ayuda_estado_concedida": "Concedida, sin cobrar",
    "ayuda_estado_cobrada": "Cobrada",
    "pagos_titulo": "Los pagos",
    "pagos_explica": "El dinero que ha salido, y a qué gastos va.",
    "sin_pagos": "Todavía no has apuntado ningún pago.",
    "pago_aplicado": "Va a gastos por",
    "pago_sin_conciliar": "Sin saber a qué va",
    "pago_conciliar": "DECIR A QUÉ VA",
    "pago_deshacer": "DESHACER ESTO",
    "sin_conciliar_titulo": "Dinero que salió y todavía no sabes a qué va",
    "sin_conciliar_explica": (
        "Ese dinero está apuntado y no se ha perdido: lo único que falta es decir contra qué gasto "
        "va. Cuando lo digas, se descuenta de lo que debes."
    ),
    "sus_pagos": "Los pagos de este gasto",
    "que_falta_titulo": "Lo que este programa todavía no calcula",
    "que_falta_explica": (
        "Se dice para que no te fíes de una cifra que no está: cuando el programa no tiene el dato, "
        "no se lo inventa."
    ),
    "que_falta_para_que": "Para qué haría falta",
    "que_falta_depende": "De quién depende",
    "el_traspaso_no_se_guarda": (
        "Un traspaso de una cuenta tuya a otra no es un ingreso ni un gasto, así que no se apunta ni "
        "en los ingresos ni en los gastos. Guardarlo junto al extracto del banco es el trabajo "
        "siguiente: hoy el programa solo te dice cómo quedan los dos movimientos."
    ),
    "form_nuevo_titulo": "Apuntar un gasto",
    "form_nuevo_pista": (
        "Con el concepto y lo que costó ya queda apuntado. Lo que no sepas se deja en blanco: un "
        "hueco se queda en blanco y no se escribe un cero."
    ),
    "form_corregir_titulo": "Corregir este gasto",
    "form_corregir_pista": (
        "Está puesto lo que apuntaste. Cambia lo que esté mal: lo que había antes queda guardado en "
        "el historial del cuaderno."
    ),
    "form_repartir_titulo": "Repartir este gasto",
    "form_repartir_pista": (
        "Elige cómo lo repartes. Si no sabes a qué va, déjalo sin asignar: se queda dicho y sigue "
        "contando en tus cuentas."
    ),
    "form_pago_titulo": "Apuntar un pago",
    "form_pago_pista": (
        "Lo que ha salido de tu cuenta y, si lo sabes, contra qué gasto va. Si no lo sabes, apúntalo "
        "igual: se queda esperando a que lo digas."
    ),
    "form_inversion_titulo": "Apuntar una inversión",
    "form_inversion_pista": (
        "Lo que has comprado para que dure. Su precio no entra entero en este año: después le dices "
        "qué parte le toca a cada campaña."
    ),
    "form_ayuda_titulo": "Apuntar una ayuda",
    "form_ayuda_pista": (
        "Lo que has pedido, lo que te han concedido y lo que has cobrado. Rellena solo lo que sepas: "
        "lo demás se queda en blanco."
    ),
    "form_anular_titulo": "Anular",
    "guardar": "GUARDAR",
    "cancelar": "VOLVER SIN GUARDAR",
    "guardando": "Guardando…",
    "anular_confirmar": "ANULARLO CON ESTE MOTIVO",
    "campo_concepto": "¿Qué fue?",
    "campo_concepto_pista": "«Gasóleo», «abono del trigo», «reparación del remolque»",
    "campo_categoria": "¿De qué es?",
    "campo_categoria_pista": "Para agrupar tus gastos. Si no lo tienes claro, «otro»",
    "campo_importe": "¿Cuánto costó?",
    "campo_importe_pista": "Si no lo sabes, déjalo en blanco: el programa no escribe un cero",
    "campo_base": "Lo que cuesta sin el IVA",
    "campo_cuota": "El IVA",
    "campo_fecha": "¿Cuándo fue?",
    "campo_vencimiento": "¿Cuándo hay que pagarlo?",
    "campo_vencimiento_pista": "Si lo tienes pactado. Si no, déjalo en blanco",
    "campo_proveedor": "¿A quién se lo compraste?",
    "campo_metodo": "¿Cómo lo reparto?",
    "campo_destino": "¿A qué se reparte?",
    # **Qué es cada destino, y qué se puede marcar en cada uno** (ronda 9). El formulario ofrecía
    # repartir entre tierras, cultivos o máquinas, pero lo que se marcaba era siempre la lista de
    # tierras: eligiendo «máquina» se guardaba un reparto que decía máquina y apuntaba a una tierra.
    # Ahora cada destino trae sus cosas, y estas tres frases son las que preguntan cuáles.
    "campo_destino_pista": (
        "Las tierras se reparten por hectáreas, por horas, por lo que se gastó o a mano. Los cultivos y las "
        "máquinas, por horas, por lo que se gastó o a mano: no tienen hectáreas propias."
    ),
    "campo_cultivos": "¿Entre qué cultivos?",
    "campo_maquinas": "¿Entre qué máquinas?",
    "campo_pesos": "¿Cuánto en cada sitio?",
    "campo_horas": "Horas",
    "campo_litros": "Litros o kilos",
    # **Entre qué tierras se reparte** (06/10/2026). Los cuatro métodos necesitan saber a qué tierras
    # va el gasto —por hectáreas se reparte entre las que se marquen, y por horas, por consumo o a mano
    # hay que decir cuánto en cada una—, y la pantalla no lo preguntaba: el reparto entero se quedaba en
    # «sin asignar» por no poder decir las tierras. Estas cuatro frases son esa pregunta.
    "campo_tierras": "¿Entre qué tierras?",
    "campo_tierras_pista": (
        "Marca las tierras a las que va este gasto. Se reparte entre las que marques, y de cada una se "
        "dice lo que le toca."
    ),
    "marcar_todas": "TODAS MIS TIERRAS",
    "campo_euros_del_trozo": "Lo que le toca (€)",
    "campo_motivo": "¿Por qué lo anulas?",
    "categorias_de_gasto": {
        "abono": "Abono",
        "fitosanitario": "Producto para las plagas y las hierbas",
        "semilla": "Semilla",
        "gasoleo": "Gasóleo",
        "reparacion": "Reparación",
        "servicio": "Trabajo de otro",
        "alquiler": "Alquiler",
        "seguro": "Seguro",
        "impuesto": "Impuesto",
        "cuota": "Cuota",
        "otro": "Otra cosa",
    },
    "categorias_de_inversion": {
        "maquinaria": "Máquina",
        "apero": "Apero",
        "instalacion": "Nave o instalación",
        "vehiculo": "Vehículo",
        "terreno": "Tierra",
        "otro": "Otra cosa",
    },
    "metodos_de_reparto": {
        "area": "Por hectáreas",
        "horas": "Por horas",
        "consumo": "Por lo que se gastó en cada sitio",
        "manual": "A mano",
    },
    # **La misma lista que la del cobro** (`ventas.FORMAS_DE_COBRO`): no puede haber dos verdades
    # sobre cómo se mueve el dinero.
    "formas_de_pago": {
        "transferencia": "Transferencia",
        "efectivo": "Efectivo",
        "cheque": "Cheque",
        "confirming": "Confirming",
        "otro": "Otra forma",
    },
    "estados_de_una_subvencion": {
        "prevista": "Pedida, sin resolver",
        "concedida": "Concedida, sin cobrar",
        "cobrada": "Cobrada",
    },
    "los_bancos": "EL BANCO Y LOS PAPELES",
}


# Y los mensajes. **Los que bloquean llevan «qué pasa + qué hago ahora»**, que es la estructura
# obligatoria de este programa: decir el problema y callarse no vale.
MENSAJES.update(
    {
        "G1_el_gasto_de_cero_euros_no_es_un_gasto": (
            "Un gasto de cero euros no es un gasto. Si lo que pasa es que no sabes lo que costó, deja "
            "el importe en blanco y el programa lo apuntará como que falta por saber."
        ),
        "G2_esa_categoria_no_es_ninguna_de_las_que_hay": (
            "«{valor}» no es ninguna de las categorías que hay ({lista}). Elige una de la lista o "
            "apúntalo como «Otra cosa» y escribe en el concepto lo que fue."
        ),
        "G3_el_pago_tiene_que_ser_mayor_que_cero": (
            "Un pago tiene que ser mayor que cero. Escribe lo que de verdad ha salido de tu cuenta."
        ),
        "G4_un_pago_no_puede_aplicarse_mas_de_lo_que_se_debe": (
            "A «{concepto}» le faltan {pendiente} por pagar y has puesto {quiere}. Baja el importe "
            "hasta lo que se debe, o apunta primero lo que falte del gasto."
        ),
        "G5_ese_metodo_de_reparto_no_es_ninguno_de_los_cuatro": (
            "«{valor}» no es ninguna de las formas de repartir ({lista}). Elige una de la lista."
        ),
        "G6_no_se_puede_repartir_porque_falta_la_superficie": (
            "No se ha podido repartir porque a una de las tierras le falta la superficie, y sin ella "
            "no se sabe qué parte le toca. El gasto se ha quedado sin asignar: mira la superficie de "
            "la tierra y vuelve a repartirlo."
        ),
        "G7_el_reparto_a_mano_suma_mas_que_el_gasto": (
            "Lo que has repartido suma más de lo que costó el gasto. Repasa los importes: la suma no "
            "puede pasar de lo que costó."
        ),
        "G8_ese_pago_ya_no_tiene_dinero_libre": (
            "De ese pago ya está todo dicho a qué va. Si quieres cambiar a qué va, deshaz primero lo "
            "que tiene puesto."
        ),
        "G9_el_gasto_no_tiene_importe_y_no_se_puede_repartir": (
            "Este gasto no tiene importe, así que no se puede repartir: no se sabe cuánto llevar a "
            "cada sitio. Apunta lo que costó y vuelve a repartirlo."
        ),
        "G10_esa_forma_de_pago_no_es_ninguna_de_las_que_hay": (
            "«{valor}» no es ninguna de las formas de pago ({lista}). Elige una de la lista."
        ),
        "G11_ese_importe_no_cabe": (
            "Ese importe («{importe}») no cabe donde se guarda: parece un número de más al teclearlo. "
            "Míralo y vuelve a escribirlo."
        ),
        "G12_la_inversion_de_cero_euros_no_es_una_inversion": (
            "Una inversión de cero euros no es una inversión. Si no sabes lo que costó, deja el "
            "importe en blanco: se queda como que falta por saber."
        ),
        "G15_eso_no_es_un_importe": (
            "«{importe}» no es un importe. Escríbelo con números, por ejemplo 121,50."
        ),
        "G16_el_gasto_necesita_saber_que_es": (
            "Un gasto tiene que decir qué fue. Escribe dos o tres palabras —«gasóleo», «abono del "
            "trigo»— y guárdalo otra vez."
        ),
        "G17_el_gasto_se_ha_guardado_sin_importe": (
            "Se ha guardado, pero sin el importe: hasta que no sepas lo que costó, esta cuenta no "
            "entra en el margen. Apúntalo cuando tengas el papel."
        ),
        "G18_no_se_pueden_comprobar_las_cuentas": (
            "No se han podido comprobar las cuentas del papel porque falta {faltan}. Si lo tienes "
            "delante, apúntalo: el programa no lo supone."
        ),
        "G19_las_cuentas_del_gasto_no_cuadran": (
            "Las cuentas de este gasto no cuadran: la base más el IVA no da el total, se llevan "
            "{diferencia}. El programa guarda lo que has escrito, pero míralo en el papel."
        ),
        "G20_el_gasto_todavia_no_esta_en_ninguna_tierra": (
            "El gasto está apuntado y todavía no está en ninguna tierra: sigue contando en tus "
            "cuentas, pero aparece como sin asignar. Dile a qué va cuando puedas."
        ),
        "G21_eso_esta_anulado_y_no_se_corrige": (
            "Esto está anulado, así que no se puede corregir. Si te has equivocado al anularlo, "
            "apunta el gasto otra vez."
        ),
        "G22_para_anular_hace_falta_el_motivo": (
            "Para anularlo hace falta el motivo: dentro de un año, ese motivo es lo único que "
            "explicará por qué está tachado. Escríbelo y vuelve a pulsar el botón."
        ),
        "G23_su_gasto_se_anulo": "Su gasto se anuló",
        "G24_gasto_anulado": (
            "Anulado, con su motivo («{motivo}»). Sigue en tu cuaderno, tachado, y deja de contar en "
            "las cuentas."
        ),
        "G25_el_dinero_ha_vuelto_a_estar_sin_conciliar": (
            "El dinero que estaba puesto en este gasto ha vuelto a quedar sin decir a qué va ({cuantos} "
            "apuntes). Dilo cuando sepas a qué gasto va."
        ),
        "G26_eso_no_es_un_sitio_donde_repartir": (
            "«{valor}» no es un sitio donde se pueda repartir un gasto ({lista}). Elige uno de la "
            "lista."
        ),
        "G27_queda_parte_sin_asignar": (
            "Queda {importe} sin asignar: está apuntado y sigue contando en tus cuentas, pero "
            "todavía no va a ninguna tierra."
        ),
        "G28_el_reparto_no_cuadra": (
            "Este reparto no cuadra: hay {falta} del gasto que no están ni repartidos ni sin asignar. "
            "Repártelo otra vez para que la suma sea la del gasto."
        ),
        "G29_el_gasto_se_queda_sin_asignar_diciendolo": (
            "El gasto se queda sin asignar, y así se dice. Sigue contando en tus cuentas: solo falta "
            "decir a dónde va."
        ),
        "G30_la_inversion_necesita_saber_que_es": (
            "Una inversión tiene que decir qué es. Escribe dos o tres palabras —«tractor», «nave del "
            "grano»— y guárdala otra vez."
        ),
        "G31_esa_categoria_de_inversion_no_existe": (
            "«{valor}» no es ninguna de las categorías de inversión que hay ({lista}). Elige una de "
            "la lista."
        ),
        "G32_una_inversion_no_es_un_gasto_del_ano": (
            "Apuntada. Ojo con una cosa: su precio no entra entero en el año en que se compró. Dile "
            "qué parte le toca a cada campaña y lo que no digas se queda sin asignar."
        ),
        "G33_la_inversion_se_ha_guardado_sin_importe": (
            "Se ha guardado sin el importe. Mientras no sepas lo que costó, no se puede decir qué "
            "parte le toca a cada campaña."
        ),
        "G34_inversion_anulada": (
            "Anulada, con su motivo («{motivo}»). Sus repartos dejan de contar."
        ),
        "G35_hay_gastos_sin_importe_y_no_se_les_aplica_el_dinero": (
            "Hay {cuantos} gastos de los que no sabes el importe, así que este dinero no se les ha "
            "podido aplicar: no se sabe cuánto deben. Apunta lo que costaron y vuelve a decir a qué "
            "va este pago."
        ),
        "G36_una_parte_del_pago_queda_sin_conciliar": (
            "Se ha aplicado lo que se debía y quedan {importe} sin decir a qué van: están apuntados y "
            "esperando. Dilo cuando sepas contra qué gasto van."
        ),
        "G37_a_este_gasto_no_se_le_puede_aplicar_dinero_sin_saber_lo_que_costo": (
            "A «{concepto}» no se le puede aplicar dinero porque no se sabe lo que costó. Apunta "
            "primero su importe y después dile a qué va el pago."
        ),
        "G38_ese_pago_no_tiene_tanto_dinero_libre": (
            "De este pago solo quedan {libre} sin decir a qué van y has puesto {quiere}. Baja el "
            "importe o deshaz antes lo que tenga puesto."
        ),
        "G39_ese_pago_esta_anulado": (
            "Ese pago está anulado, así que no se le puede decir a qué va. Si te has equivocado al "
            "anularlo, apúntalo otra vez."
        ),
        "G40_el_pago_sigue_apuntado_y_sin_conciliar": (
            "Deshecho. El pago sigue apuntado con todo su importe y otra vez sin decir a qué va: el "
            "dinero no se ha borrado."
        ),
        "G41_pago_anulado": (
            "Pago anulado, con su motivo («{motivo}»). Los gastos que saldaba vuelven a estar "
            "pendientes."
        ),
        "G42_la_ayuda_necesita_saber_de_que_es": (
            "Una ayuda tiene que decir de qué es. Escribe dos o tres palabras —«ayuda a la cosecha de "
            "cereal»— y guárdala otra vez."
        ),
        "G43_una_ayuda_prevista_no_es_un_ingreso": (
            "Apuntada. Recuerda que una ayuda pedida o concedida **no es dinero que hayas cobrado**: "
            "no se suma a lo que ha entrado hasta que te la ingresen."
        ),
        "G44_ayuda_anulada": (
            "Anulada, con su motivo («{motivo}»). Deja de contar como ingreso."
        ),
        "G45_un_traspaso_a_la_misma_cuenta_no_es_un_traspaso": (
            "Ese traspaso sale y entra en la misma cuenta, así que no es un traspaso. Mira de qué "
            "cuenta sale y a cuál entra."
        ),
        "G46_faltan_importes_por_saber_uno": "Falta 1 importe por saber",
        "G46_faltan_importes_por_saber_varios": "Faltan {cuantos} importes por saber",
        "G47_gastos_sin_saber_a_donde_van_uno": "1 gasto sin saber a dónde va",
        "G47_gastos_sin_saber_a_donde_van_varios": "{cuantos} gastos sin saber a dónde van",
        # --- a qué clase de sitio se reparte (ronda 9) ---
        "G48_las_hectareas_son_de_una_tierra": (
            "Repartir por hectáreas solo se puede hacer entre tierras: las hectáreas son de una tierra, y un "
            "cultivo o una máquina no tienen superficie propia. Elige otro método para repartirlo."
        ),
        "G49_un_destino_sin_nombre": (
            "Hay un sitio al que repartir sin decir cuál es. Míralo y vuelve a repartirlo."
        ),
        "G50_esa_tierra_no_esta_en_tu_cuaderno": (
            "Una de las tierras a las que repartes no está en tu cuaderno. Míralas y vuelve a repartirlo."
        ),
        "G51_eso_es_una_tierra_y_no_un_cultivo": (
            "Estás repartiendo entre cultivos, pero lo que has dicho que es un cultivo es el número de una tierra. "
            "Elige el cultivo por su nombre, o reparte entre tierras."
        ),
        "G52_esa_maquina_no_esta_en_tu_cuaderno": (
            "Una de las máquinas a las que repartes no está en tu cuaderno. Míralas y vuelve a repartirlo."
        ),
    }
)

MENSAJES.update({
    "TJ1_el_previsto_no_gasta": (
        "Este trabajo está previsto y todavía no se ha hecho: no ha gastado nada del almacén."
    ),
    "TJ2_no_consta_si_se_hizo": (
        "De este trabajo no consta si se llegó a hacer, así que no cuenta como trabajo hecho. "
        "Dilo y queda apuntado."
    ),
    "TJ3_el_apunte_esta_anulado": (
        "Este apunte está anulado: lo que había salido del almacén vuelve a contar."
    ),
    "TJ4_lo_que_salio_cambio": (
        "Se corrigió el trabajo: la salida de antes ya no cuenta y se ha apuntado la nueva."
    ),
    "TJ5_falta_el_motivo_para_anular": (
        "Para anular un trabajo hace falta decir por qué. Escríbelo y vuelve a pulsar."
    ),
    "TJ6_el_trabajo_ya_estaba_anulado": (
        "Este trabajo ya estaba anulado, así que no ha cambiado nada."
    ),
    "TJ7_de_la_lluvia_no_sale_la_nascencia": (
        "Que haya llovido no quiere decir que la planta haya nacido: eso se mira en el campo y se "
        "apunta como una observación."
    ),
    "TJ8_un_rodillo_no_cambia_lo_sembrado": (
        "Pasar el rodillo no cambia lo que tienes sembrado: la siembra sigue apuntada."
    ),
    "TJ9_no_se_reprograma_lo_ya_hecho": (
        "Este trabajo ya se hizo, así que su fecha es la del día en que se hizo. Si hiciste otro, "
        "apúntalo."
    ),
    "TJ10_lo_firmado_no_se_borra": (
        "Este apunte está firmado y no se puede borrar: se anula, con su motivo, y queda el rastro."
    ),
    "TJ11_el_trabajo_ya_estaba": (
        "Este trabajo ya estaba apuntado: no se ha vuelto a descontar del almacén."
    ),
    "TJ12_no_se_pudo_comprobar_si_ya_estaba": (
        "Esta petición no trae la clave para saber si ya se había apuntado, así que no he podido "
        "comprobarlo."
    ),
    "TJ13_faltan_las_hectareas": (
        "Hay trabajos de este año que no dicen cuántas hectáreas se trabajaron, así que las que se "
        "ven son solo las que constan."
    ),
    "TJ14_faltan_las_horas": (
        "Hay trabajos de este año que no dicen cuántas horas se estuvo, así que las que se ven son "
        "solo las que constan."
    ),
    "TJ15_la_tierra_quedo_o_no": (
        "Se cogió la cosecha, pero no consta si la tierra quedó con algo o vacía: eso se mira en el "
        "campo y se apunta como una observación."
    ),
    "TJ16_sin_maquina": "Hay trabajos apuntados sin decir con qué máquina se hicieron.",
    "TJ17_un_plan_no_es_un_trabajo": (
        "Esto está planificado y todavía no es un trabajo hecho: cuando lo hagas, apunta lo que de "
        "verdad pasó, con su día y lo que gastaste."
    ),
    "TJ18_sin_tierra": (
        "Hay trabajos que no dicen de qué tierra eran, así que no salen en el historial de ninguna."
    ),
    "TJ19_la_revision_de_lo_firmado": (
        "Lo firmado no se cambia: queda la revisión nueva, y la firma de antes sigue valiendo para lo "
        "que se firmó."
    ),
    "TJ20_no_se_pueden_sumar_unidades": (
        "Hay cantidades en unidades distintas, así que no se pueden juntar en una sola cifra."
    ),
    "TJ21_falta_la_cantidad": (
        "Hay un consumo apuntado sin cantidad, así que no se puede saber lo que queda."
    ),
    "TJ22_falta_la_unidad": (
        "Hay un consumo apuntado sin decir en qué se mide, así que no se puede hacer la cuenta."
    ),
    "TJ23_faltan_las_hectareas_de_la_tierra": (
        "Esta tierra no dice cuántas hectáreas tiene, así que no se puede comparar con lo trabajado."
    ),
    "TJ24_no_hay_fecha_de_hoy": (
        "No sé qué día es hoy, así que no te puedo decir cuánto falta ni cuánto se ha pasado."
    ),
    "TJ25_la_fecha_prevista_no_se_sabe": (
        "Este trabajo está planificado sin día, así que no se puede decir cuándo toca."
    ),
    "TJ26_el_apunte_del_consumo_no_esta": (
        "Hay una salida del almacén que dice venir de un trabajo que no encuentro, así que no la he "
        "podido comprobar."
    ),
    "TJ27_no_se_sabe_si_nacio": (
        "No consta si la planta ha nacido: eso se mira en el campo y se apunta como una observación."
    ),
    "TJ28_no_se_sabe_que_se_sembro": (
        "La siembra está apuntada, pero no dice qué se sembró. Apúntalo y el estado de la tierra "
        "quedará completo."
    ),
})

# --------------------------------------------------------------------------
# Los mensajes de la bandeja documental (T08, S10, 06/10/2026)
# --------------------------------------------------------------------------
#
# Lo que el servidor dice cuando algo no se puede hacer, con el prefijo `T08_` de este ticket (los del
# banco son `T20_`, y así se sabe de qué pantalla es cada uno). Todos dicen **qué pasa y qué hacer**, que
# es la regla de la casa: un aviso que no dice qué hacer deja al agricultor parado delante de la pantalla.
MENSAJES_DE_LA_BANDEJA: dict[str, str] = {
    # --- el papel y su ficha ---
    "T08_ese_papel_no_esta_en_tu_bandeja": "Ese papel no está en tu bandeja. Míralo en LOS PAPELES y vuelve a intentarlo.",
    "T08_eso_no_esta_en_tu_cuaderno": "Eso no está en tu cuaderno. Elige algo que ya tengas apuntado.",
    "T08_sin_fichero_no_se_puede_leer": "Este papel está apuntado sin su fichero, así que no hay nada que leer. Súbelo desde LOS PAPELES y vuelve a intentarlo.",
    "T08_este_papel_no_lo_se_leer": "De este tipo de papel todavía no sé leer nada. Escribe los datos a mano: quedan guardados igual.",
    "T08_el_fichero_ha_cambiado": "El fichero que tengo guardado no es el que subiste, así que no lo he leído. Vuelve a subir el papel bueno.",
    # --- clasificar y revisar ---
    "T08_ese_tipo_no_existe": "Ese tipo de papel no lo conozco. Los que hay: {tipos}.",
    "T08_ese_estado_no_existe": "Ese estado no lo conozco. Los que hay: {estados}.",
    "T08_no_has_aceptado_nada": "No has dicho qué queda de este papel. Escribe lo que ponga el papel y vuelve a intentarlo.",
    "T08_ese_importe_no_se_entiende": "Ese importe no lo entiendo. Escríbelo como en el papel, por ejemplo 1.234,56.",
    "T08_esa_fecha_no_se_entiende": "Esa fecha no la entiendo. Escríbela como 31/12/2026.",
    "T08_esa_fecha_no_existe": "Esa fecha no existe. Mírala y vuelve a escribirla.",
    "T08_no_hay_lectura_que_descartar": "De este papel no hay ninguna lectura que descartar. Léelo primero.",
    "T08_dime_por_que_no_sirve": "Dime por qué no te sirve la lectura, para que quede apuntado.",
    "T08_revisado_sin_confirmar": "Guardado lo que queda de este papel. Está sin confirmar: confírmalo cuando lo tengas claro.",
    "T08_lectura_descartada": "Descartada esa lectura: queda guardada con tu motivo, y el papel sigue esperando.",
    # --- confirmar ---
    "T08_hay_que_revisar_antes": "Antes de confirmar hay que revisar el papel y decir qué queda: ábrelo, mira lo que dice (o escríbelo a mano) y guárdalo.",
    "T08_papel_confirmado": "Papel confirmado. Ya está en LOS PAPELES, con su fichero tal y como llegó.",
    # --- el duplicado ---
    "T08_el_mismo_papel_ya_estaba": "Este mismo papel ya lo tienes: «{titulo}», subido el {cuando}. No se ha apuntado otra vez.",
    "T08_el_mismo_papel_esta_en_una_factura": "Este mismo fichero ya lo subiste como la factura de compra «{quien}» (nº {numero}). No se ha apuntado otra vez.",
    "T08_papel_en_la_bandeja": "Papel guardado tal y como llegó. Está en la bandeja, sin revisar: nada ha entrado en tu cuaderno todavía.",
    # --- enlazar ---
    "T08_esa_clase_no_existe": "Con eso no se puede enlazar un papel. Se puede con: {clases}.",
    "T08_dime_con_que_lo_enlazo": "Dime con qué quieres enlazar este papel.",
    "T08_no_hay_nada_que_enlazar": "No hay nada de eso en tu cuaderno. Apúntalo primero en su pantalla y vuelve a intentarlo.",
    "T08_ya_estaba_enlazado": "Este papel ya está enlazado con eso.",
    "T08_esa_inspeccion_ya_tiene_papel": "Esa inspección ya tiene su papel. Quítaselo a la otra antes de ponérselo a esta.",
    "T08_papel_enlazado": "Enlazado. No se ha creado nada: el papel solo dice con qué va.",
    "T08_dime_que_enlace_quito": "Dime qué enlace quieres quitar.",
    "T08_ese_enlace_no_esta": "Este papel no está enlazado con eso, así que no hay nada que quitar.",
    "T08_papel_desenlazado": "Quitado ese enlace. Lo que había apuntado sigue en tu cuaderno igual que estaba.",
    # --- rectificar ---
    "T08_dime_a_que_papel_rectifica": "Dime a qué papel corrige este. Elige uno de la lista.",
    "T08_un_papel_no_se_rectifica_a_si_mismo": "Un papel no puede corregirse a sí mismo. Elige el papel al que corrige.",
    "T08_esto_haria_un_circulo": "Así los papeles se corregirían unos a otros en círculo. Mira a qué corrige cada uno y elige el bueno.",
    "T08_rectifica_a_otro": "Apuntado: este papel corrige a ese. Los dos siguen ahí, y el corregido queda marcado.",
}
MENSAJES.update(MENSAJES_DE_LA_BANDEJA)


AGENDA: dict[str, str] = {
    "titulo": "Los trabajos",
    # **La superficie de la tierra, en su ficha** (07/10/2026, E7 de la revisión del recorrido): el dato se
    # mandaba desde el primer día y la ficha no lo enseñaba. Es lo primero que se mira de una tierra y con
    # lo que se comprueban las hectáreas de cada trabajo.
    "superficie": "Superficie",
    "hectareas_corto": "ha",
    # **La referencia oficial del SIGPAC, en la ficha** (07/10/2026): es lo único que el panel de la fila
    # enseñaba y la ficha no. Se dice con el mismo nombre que en el panel (`MAESTROS.tierra_sigpac`), para
    # que el agricultor lea lo mismo en los dos sitios mientras los dos existan.
    "referencia": "Referencia oficial SIGPAC",
    "explica": "Aquí tienes lo que tienes pensado hacer y lo que ya has hecho, en dos listas separadas. Lo que está pensado no ha gastado nada del almacén: lo que se gasta se apunta cuando el trabajo se hace.",
    "buscando": "Buscando…",
    "ver_el_cuaderno": "VER MI CUADERNO",
    "volver_a_los_trabajos": "VOLVER A LOS TRABAJOS",
    "previstos_titulo": "Lo que tengo pensado hacer",
    # **El botón de las versiones de una tierra, en su ficha** (07/10/2026). Se llama como esa pantalla
    # (`VERSIONES_EN_PANTALLA.titulo`): un botón que lleva a una pantalla se llama como esa pantalla. Está
    # aquí, y no solo allí, porque el armazón de la ficha lee **este** bloque, y las dos copias tienen que
    # tener las mismas claves (lo comprueban dos pruebas).
    "lo_que_ha_sido": "Lo que ha sido esta tierra",
    # **Y el de decir o cambiar el cultivo, desde la ficha** (07/10/2026): la ficha ya enseña lo que hay
    # sembrado; con esto puede además decirlo o corregirlo **sin salir de la tierra** que se está mirando,
    # que es lo que pide la ficha única. Se dice con el nombre de esa pantalla (`CULTIVOS.titulo`).
    "decir_el_cultivo": "Qué hay sembrado",
    # **El botón de volver a la lista de tierras desde la ficha de una** (07/10/2026, E4 de la revisión del
    # recorrido). Se dice con el nombre de esa pantalla —el mismo que el del menú—, que es como el
    # agricultor la conoce; aquí no se inventa ninguna palabra nueva.
    "mis_tierras": "Mis parcelas, productos y máquinas",
    "previstos_explica": "Lo que está pensado no es un trabajo hecho y no ha gastado nada.",
    "previstos_vacio": "No tienes nada planificado. Cuando sepas lo que vas a hacer, apúntalo aquí.",
    "planificar": "PLANIFICAR UN TRABAJO",
    "planificar_titulo": "Planificar un trabajo",
    "planificar_explica": "Apunta lo que piensas hacer. No gasta nada del almacén: eso se apunta el día que lo hagas, con lo que de verdad gastes.",
    "guardar_previsto": "GUARDAR LO QUE PIENSO HACER",
    "ya_lo_he_hecho": "YA LO HE HECHO",
    # Un plan ya cumplido se sigue enseñando en «lo que tengo pensado hacer» —el plan es lo que se pensó, y
    # eso no se borra—, pero **no puede ofrecer el botón de apuntarlo otra vez**: el servidor contesta 409
    # («este trabajo ya estaba apuntado») y el agricultor se queda mirando un botón que no hace nada. Se
    # dice cuándo se hizo, y el hecho está en la otra lista con su corregir y su anular.
    "ya_esta_hecho": "Ya lo apuntaste como hecho:",
    "cambiarlo_de_dia": "CAMBIARLO DE DÍA",
    "cancelarlo": "CANCELARLO",
    "reprogramar_titulo": "Cambiar de día este trabajo",
    "reprogramar_explica": "Elige el día nuevo. El día que tenía queda apuntado, para que se pueda explicar el cambio.",
    "cambiar_el_dia": "CAMBIARLO DE DÍA",
    "hechos_titulo": "Lo que he hecho",
    "hechos_explica": "Cada trabajo con su día, su tierra, su máquina y lo que se gastó. Lo anulado sale también, con su motivo.",
    "hechos_vacio": "Todavía no has apuntado ningún trabajo hecho.",
    "hecho_titulo": "Lo que he hecho de verdad",
    "hecho_explica": "Apunta lo que de verdad has hecho: el día, las hectáreas y las horas de verdad, y lo que gastaste. No tiene que ser igual que lo que habías pensado.",
    "lo_que_estaba_previsto": "Lo que tenías pensado",
    "lo_previsto_no_gasta": "Lo pensado no ha gastado nada del almacén.",
    "guardar_trabajo": "APUNTAR LO QUE HE HECHO",
    "corregir_titulo": "Corregir este trabajo",
    "corregirlo": "CORREGIRLO",
    "guardar_correccion": "GUARDAR LA CORRECCIÓN",
    "anular_titulo": "Anular este trabajo",
    "anularlo": "ANULARLO",
    "anular_explica": "Un trabajo no se borra: se anula y queda dicho por qué. Lo que había salido del almacén vuelve a contar.",
    "anular_confirmar": "ANULARLO",
    "motivo_anulacion": "Por qué lo anulas",
    "motivo_anulacion_pista": "Escríbelo pensando en que lo vas a leer dentro de dos años.",
    "guardando": "Guardando…",
    "tipo": "Qué trabajo",
    "tipo_pista": "Rodillo, cultivador, siembra, riego…",
    "elige_el_trabajo": "Elige el trabajo",
    "subtipo": "Con qué apero",
    "subtipo_pista": "Solo para las labores de suelo: rodillo, cultivador, arado…",
    "sin_decir": "Sin decir",
    "tierra": "En qué tierra",
    "elige_la_tierra": "Elige la tierra",
    "dia": "Qué día lo hiciste",
    "dia_pista": "El día de verdad, que es el que va al cuaderno.",
    "dia_previsto": "Para qué día lo tienes pensado",
    "dia_previsto_pista": "Si todavía no lo sabes, déjalo en blanco: se queda sin día.",
    "hectareas": "Cuántas hectáreas has trabajado",
    "hectareas_previstas": "Cuántas hectáreas piensas trabajar",
    "hectareas_pista": "Si no lo sabes, déjalo en blanco. No se pone un cero.",
    "horas": "Cuántas horas has estado",
    "horas_previstas": "Cuántas horas piensas estar",
    "horas_pista": "Si no lo sabes, déjalo en blanco.",
    "maquina": "Con qué máquina",
    "maquina_pista": "La máquina con la que lo hiciste. Si fue a mano, déjalo sin decir.",
    "sin_maquina": "Sin máquina dicha",
    "insumo": "Qué gastaste del almacén",
    "insumo_pista": "De qué envase sale lo que gastaste. Si no gastaste nada, déjalo sin decir.",
    "insumo_previsto_pista": "Lo que crees que vas a gastar. No se descuenta hasta que lo hagas.",
    "sin_insumo": "No gasté nada",
    "cantidad": "Cuánto",
    "cantidad_pista": "El total gastado, no lo de cada hectárea.",
    "unidad": "En qué se mide",
    "observaciones": "Lo que quieras apuntar",
    "repaso": "Antes de guardar, mira esto",
    "historia_titulo": "Lo que ha pasado en esta tierra",
    "que_hay_hoy": "Qué hay hoy",
    "lo_que_esta_sembrado": "Lo que hay sembrado",
    "variedad": "Variedad",
    "desde_cuando": "Desde",
    "sin_cultivo_declarado": "De esta tierra no consta que haya nada sembrado.",
    "ultima_labor": "La última labor",
    "historial_titulo": "Todo lo que ha pasado",
    # **La sección de Cultivos de la ficha de una tierra** (encargo del rediseño, 07/10/2026): lo sembrado y
    # lo plantado, sacado de la historia a su propia sección —lo que cambió el cultivo de verdad, sin contar
    # lo anulado—, porque dentro de la historia había que leerla línea a línea para saber qué se sembró.
    "cultivos": "Cultivos",
    "sin_cultivos": "No hay ninguna siembra ni plantación apuntada en esta tierra.",
    "historial_explica": "Sale todo, también lo anulado, con el motivo por el que se anuló. Nada se borra.",
    "historial_vacio": "En esta tierra no hay ningún trabajo apuntado.",
    "revisado": "Corregido después",
    "firmado": "Está firmado: no se puede borrar, solo anular",
    "observaciones_de_campo": "Lo que he visto en el campo",
    "no_consta": "Lo que no consta",
    "sin_tierras": "Para planificar un trabajo hace falta tener una tierra dada de alta.",
    "anadir_tierra": "VER MIS TIERRAS",
    # ── Lo que ha costado una tierra (T13 + T15, 05/10/2026) ──────────────────
    #
    # La mitad que le faltaba al recorrido de abrir una tierra: qué cultivo tiene, qué trabajos se han
    # hecho, qué queda previsto **y qué costes conocidos tiene**. Las cifras las calcula el servidor
    # (`GET /api/gastos/de-una-tierra/<id>`); aquí solo están las palabras.
    #
    # **Dos cifras y no una suma**, y se dice por qué: un coste directo es lo que pone el papel y uno
    # repartido es una estimación que acordó el agricultor. Y `costes_sin_importe` existe porque un
    # total que calla que le faltan datos miente: dice cuántos gastos de esa tierra no traen el importe.
    "costes_titulo": "Lo que ha costado esta tierra",
    "costes_explica": (
        "Lo que consta de esta tierra. Está separado en dos: lo que pone el papel y lo que se repartió "
        "desde las cuentas, que es una estimación. Lo que no se sabe se dice, no se cuenta como cero."
    ),
    "costes_directos": "Lo que pone el papel",
    "costes_repartidos": "Lo repartido desde las cuentas",
    "costes_total": "Lo que se sabe que ha costado",
    "costes_sin_importe": (
        "Hay {cuantos} gastos de esta tierra que no dicen lo que costó, así que el total se queda corto."
    ),
    # **Y en singular, cuando es uno** (07/10/2026): la frase decía «Hay 1 gasto» y «Hay 2 gasto» con la
    # misma forma, y el agricultor lo lee. Es la misma regla que en el resto de la aplicación: el número
    # con su palabra, en singular o en plural.
    "costes_sin_importe_uno": (
        "Hay 1 gasto de esta tierra que no dice lo que costó, así que el total se queda corto."
    ),
    "costes_vacio": "De esta tierra no hay ningún gasto apuntado.",
    "costes_directo_es": "Es un gasto que dice esta tierra.",
    "costes_repartido_es": "Es un trozo que se repartió a esta tierra desde las cuentas.",
    "ver_el_gasto": "VER EL GASTO",
}

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
    # **La moneda que no es el euro** (CRM-02, 11/10/2026): no se apunta como si fueran euros. Y se dice por
    # qué no se convierte: porque este programa **no convierte monedas** —no tiene ninguna fuente de cambio
    # acreditada— y un cambio inventado sería un número falso en las cuentas de la campaña.
    "T20_moneda_distinta": "Una línea del extracto está en otra moneda y no se ha apuntado: este programa no convierte monedas, porque no tiene de dónde sacar el cambio. Descarga el extracto en euros o convierte esa línea en tu banco.",
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
    "T20_este_movimiento_ya_esta_apuntado": "Este movimiento ya está apuntado entero a sus papeles, así que no queda nada que repartir. Si te has equivocado, deshaz lo apuntado y vuelve a repartirlo.",
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

# --------------------------------------------------------------------------
# Las existencias que cuadran (T21, 06/10/2026)
# --------------------------------------------------------------------------
#
# **Estas cinco frases son las del módulo `app/existencias.py`** (`existencias.MENSAJES`), y hay una
# prueba que compara los dos sitios leyendo el informe del ticket (`docs/T21_EXISTENCIAS.md`): si una
# cambia en un lado y no en el otro, se pone roja.
#
# El problema que resuelven, dicho corto: en la finca había **dos libros** —lo comprado contra lo echado
# (la cesta, de las facturas y los tratamientos) y las existencias físicas del almacén (por envases y
# lotes)— y cada uno decía una cosa. A partir del T21, **donde las dos vistas hablan del mismo artículo
# usan el mismo saldo físico**, y cuando no se puede (no hay enlace, o las unidades no son las mismas) se
# dice con una de estas frases, **nunca con un cero**.
MENSAJES.update(
    {
        "A24_el_producto_no_tiene_articulo": (
            "Este producto no está enlazado con nada del almacén, así que de lo que te queda no se "
            "puede decir nada aquí. Enlázalo con un artículo del almacén y las dos pantallas dirán lo "
            "mismo."
        ),
        "A25_los_dos_libros_dicen_lo_mismo": (
            "Este consumo está apuntado en el cuaderno y en el almacén: es el mismo, y contarlo dos "
            "veces diría que has echado el doble. Cuenta una vez."
        ),
        "A26_el_libro_viejo_no_tiene_saldo_fisico": (
            "De este producto el cuaderno sabe lo que compraste y lo que llevas echado, pero en el "
            "almacén no hay ninguna entrada suya: lo comprado no está dentro hasta que llegue el "
            "albarán. Apunta la entrada cuando llegue y aquí saldrá lo que te queda de verdad."
        ),
        "A27_unidades_que_no_se_pueden_restar": (
            "Esto se lleva en {unidad} y lo que hay apuntado está en {otra}. No se pueden restar: un "
            "litro y un kilo no son lo mismo, y hace falta la densidad del producto."
        ),
        "A28_no_hay_articulo_del_que_sacar_el_saldo": (
            "Ni el cuaderno ni el almacén tienen una ficha de la que sacar lo que te queda. "
            "Apunta de qué producto se trata y volverá a salir la cuenta."
        ),
    }
)

# --------------------------------------------------------------------------
# El extracto del banco y la conciliación (T20, E11, 06/10/2026)
# --------------------------------------------------------------------------
#
# **Las palabras de S14**: subir el extracto, mirarlo sin apuntar nada, cuadrarlo con las facturas y los
# cobros, deshacerlo y mirar lo que queda. Y las cuatro familias de claves que se leen **compuestas**,
# dichas aquí para que nadie las busque en balde:
#
#   · `estado_<estado>` — cómo está un movimiento (`sin_conciliar`, `conciliado_en_parte`, `conciliado`,
#     `no_se_puede_conciliar`). El servidor manda la clave en `MovimientoSalida.estado`, no la frase.
#   · `falta_<lo_que_falta>` — qué no consta de una línea (`importe_no_consta`, `saldo_no_consta`,
#     `referencia_no_consta`, `concepto_no_consta`, `importe_ilegible_en_la_fila`, `saldo_ilegible`).
#   · `por_que_no_<clave>` — por qué un movimiento no se puede cuadrar (`no_consta_el_importe`,
#     `es_un_traspaso_entre_cuentas_tuyas`).
#   · `propuesta_<tipo>` — cómo cuadra una propuesta (`exacta`, `agrupada`, `parcial`).
#
# Las claves de las cuatro familias salen de `app/extractos.py` (sus constantes), y hay una prueba que las
# recorre enteras: **la que falte sale en blanco en la pantalla sin que salte nada**, y un renglón en
# blanco en medio de una pantalla de dinero es lo peor que puede pasar aquí. **Y ojo con `no_se_puede_conciliar`:
# no es «sin cuadrar»** — uno dice «se puede y no lo has hecho» y el otro «no se puede, y aquí está por qué».
BANCOS: dict[str, str] = {
    # --- la pantalla ---
    "titulo": "El banco y los papeles",
    "explica": (
        "Aquí subes el extracto que has descargado de tu banca y lo cuadras con las facturas y los cobros. "
        "El programa no se conecta a ningún banco: solo lee el fichero que le das tú."
    ),
    "buscando": "Buscando…",
    "volver_a_los_movimientos": "VOLVER A LOS MOVIMIENTOS",
    # --- subir el fichero (leer NO guarda nada) ---
    "subir_titulo": "Subir el extracto",
    "subir_explica": (
        "Elige el fichero que has descargado de tu banca. El programa lo lee y te enseña lo que ha "
        "entendido, sin apuntar nada todavía."
    ),
    "nada_se_apunta": "Leer no apunta nada: primero lo miras y después decides.",
    "fichero": "El fichero del extracto",
    "fichero_pista": "Es el fichero que te has descargado de tu banca.",
    "fichero_elegido": "El fichero que has elegido es",
    "cuenta": "De qué cuenta es",
    "cuenta_pista": "La cuenta de la que has descargado el extracto.",
    "elige_la_cuenta": "Elige la cuenta",
    "perfil": "Cómo escribe tu banco",
    "perfil_pista": "Si ya nos dijiste cómo escribe las fechas y los importes, elígelo aquí.",
    "sin_perfil": "Todavía no lo he dicho",
    "leer_el_extracto": "LEER EL EXTRACTO",
    "leyendo": "Leyendo el extracto…",
    "anadir_una_cuenta": "AÑADIR UNA CUENTA",
    "anadir_un_perfil": "DECIR CÓMO ESCRIBE MI BANCO",
    "sin_cuentas": "Para subir un extracto hace falta decir antes de qué cuenta es.",
    # --- la vista previa: lo que se va a apuntar, y lo que no ---
    "vista_titulo": "Lo que he entendido del fichero",
    "vista_nada_apuntado": "Esto todavía no está apuntado. Míralo y, si está bien, apúntalo.",
    "ya_estaba_el_fichero": "Este mismo fichero ya lo subiste antes.",
    "cuenta_detectada": "En el fichero pone que es la cuenta",
    "cuenta_no_detectada": "En el fichero no se lee de qué cuenta es.",
    "lineas_leidas": "Líneas leídas",
    "movimientos_leidos": "Movimientos entendidos",
    "se_apuntaran": "Se van a apuntar",
    "ya_estaban": "Ya estaban apuntados",
    "ya_estaban_explica": "Estos no se apuntan otra vez: ya los tenías.",
    "rechazadas_cuantas": "Líneas que no se han entendido",
    "entradas": "Dinero que entra",
    "salidas": "Dinero que sale",
    "sin_importe": "Líneas sin importe",
    "sin_importe_explica": (
        "De esas no se sabe cuánto, y no cuentan en los totales. Escribe el importe a mano."
    ),
    "formato_de_fecha": "Las fechas del fichero",
    "formato_no_dicho": "No nos has dicho cómo son",
    "saldo_final": "El saldo que queda",
    "no_consta": "No consta",
    "no_se_sabe": "No lo sé",
    "avisos_titulo": "Lo que hay que mirar de esta lectura",
    "rechazadas_titulo": "Líneas que no se han podido leer",
    "rechazadas_explica": "Estas líneas no se van a apuntar. Cada una dice qué le pasa y en qué línea está.",
    "linea_numero": "Línea",
    "se_van_a_apuntar": "Lo que se va a apuntar",
    "no_hay_ninguno_nuevo": "De este fichero no hay ningún movimiento nuevo que apuntar.",
    "ya_estaba_esta_linea": "Esta línea ya estaba apuntada.",
    "apuntar_los_movimientos": "APUNTAR ESTOS MOVIMIENTOS",
    "importando": "Apuntando…",
    "descartar": "NO APUNTAR NADA",
    "apuntado_titulo": "Lo que se ha apuntado",
    "apuntados": "Movimientos apuntados",
    "repetidos": "Que ya estaban",
    "repetidos_explica": "No se han repetido: ya los tenías apuntados.",
    # --- los traspasos entre cuentas propias (A07) ---
    "traspasos_titulo": "Dinero que ha cambiado de cuenta",
    "traspasos_explica": "Parece el mismo dinero pasado de una cuenta tuya a otra.",
    "traspaso_sale_de": "Sale de",
    "traspaso_entra_en": "Entra en",
    "traspaso_dias": "Días de diferencia",
    "traspaso_donde": "Márcalo abriendo uno de los dos movimientos y diciendo cuál es el otro.",
    # --- la lista de movimientos ---
    "movimientos_titulo": "Los movimientos del banco",
    "movimientos_explica": "Cada línea del extracto, con lo que le queda por cuadrar.",
    "movimientos_vacio": (
        "Todavía no has apuntado ningún movimiento. Sube el extracto de tu banca para empezar."
    ),
    "sin_resultados": (
        "Ningún movimiento coincide con lo que buscas. Prueba con otras letras o pulsa VER TODO."
    ),
    "buscar": "Buscar en los movimientos",
    "buscar_pista": "Escribe parte del concepto o de la referencia.",
    "buscar_boton": "BUSCAR",
    "ver_todo": "VER TODO",
    "exportar": "DESCARGAR EL EXTRACTO",
    # **Se dice qué se lleva el fichero** (06/10/2026), y no es un adorno: hasta hoy el botón bajaba
    # **todo el extracto de la cuenta** aunque el agricultor tuviera la lista filtrada, y como no lo decía,
    # parecía que se llevaba lo que estaba viendo. Ahora se lleva lo que se ve (los filtros van con la
    # descarga) y la pista lo dice con esas palabras, que es lo que el encargo pide: «verifica el alcance
    # anunciado: seleccionados, filtrados o todos; si solo permite uno, debe decir cuál».
    "exportar_pista": (
        "Se descarga en un fichero lo que estás viendo: con el filtro y la cuenta que tengas puestos. "
        "Donde el importe no consta, la casilla va en blanco."
    ),
    "estado": "Cuáles ver",
    "todos_los_estados": "Todos",
    "fecha": "El día",
    "referencia": "La referencia",
    "importe": "El importe",
    "saldo": "El saldo que quedó",
    "su_cuenta": "La cuenta",
    "como_esta": "Cómo está",
    "imputado": "Ya apuntado a papeles",
    "por_conciliar": "Le queda por cuadrar",
    "abrir": "¿CONTRA QUÉ PAPEL VA?",
    "es_traspaso": "Es un traspaso entre cuentas tuyas: ese dinero solo ha cambiado de sitio.",
    "corregido_a_mano": "Este importe lo escribiste tú.",
    "sin_importe_aviso": (
        "De este movimiento no consta el importe, así que no se puede cuadrar con ningún papel. "
        "Escríbelo a mano."
    ),
    # --- lo que queda por cuadrar, de los dos lados ---
    "pendientes_titulo": "Lo que queda por cuadrar",
    "pendientes_explica": (
        "De un lado, el dinero del banco que todavía no está apuntado a ningún papel. Del otro, las "
        "facturas y los cobros a los que les falta dinero."
    ),
    "dinero_sin_papel": "Dinero del banco sin papel",
    "sin_conciliar_cuantos": "Movimientos sin cuadrar",
    "papeles_sin_dinero": "Papeles sin dinero",
    "de_quien": "Quién",
    "le_falta": "Le falta",
    "sin_pendientes": "No queda nada por cuadrar: todo el dinero apuntado está en su papel.",
    "como_se_cuadra": "Para cuadrar algo, abre el movimiento del banco y dile contra qué papel va.",
    # --- la ficha de un movimiento ---
    "ficha_titulo": "Este movimiento del banco",
    "propuestas_titulo": "Contra qué papel va",
    "propuestas_explica": (
        "Estas son las cuentas que cuadran con este movimiento, y por qué. Elige una y el dinero queda "
        "apuntado a ese papel."
    ),
    "propuestas_vacio": (
        "Con este movimiento no cuadra ninguna factura ni ningún cobro. Puedes apuntarlo a mano."
    ),
    "porque_titulo": "Por qué te lo propongo",
    "a_que_papeles": "A estos papeles",
    "se_apuntaria": "Se apuntarían",
    "quedaria_sin_apuntar": "Quedaría sin apuntar",
    "apuntar_esta": "APUNTAR ESTA",
    "papel_desconocido": "De este papel no se sabe cómo se llama. Míralo antes de apuntar nada aquí.",
    "a_mano_titulo": "Apuntarlo a mano",
    "a_mano_explica": (
        "Elige el papel y, si solo le vas a apuntar una parte, escribe cuánto. Si lo dejas en blanco, se "
        "apunta lo que quepa, del papel más antiguo al más nuevo."
    ),
    "papel": "A qué papel",
    "elige_el_papel": "Elige el papel",
    "cantidad": "Cuánto de este movimiento",
    "cantidad_pista": "Déjalo en blanco para apuntar todo lo que quepa.",
    "apuntar": "APUNTAR ESTE DINERO",
    "sin_papeles": (
        "No tienes ninguna factura ni ningún cobro al que apuntar este dinero. Apúntalo antes."
    ),
    "lo_conciliado_titulo": "Lo que ha quedado apuntado",
    "lo_devuelto_titulo": "Lo que ha vuelto a quedar pendiente",
    "deshacer_titulo": "Deshacer lo apuntado",
    "deshacer_explica": (
        "Deshacer no borra el movimiento del banco: el banco ya movió ese dinero. Lo que se deshace es a "
        "qué papeles estaba apuntado, y queda dicho quién lo deshizo y cuándo."
    ),
    "deshacer": "DESHACERLO",
    "nada_que_deshacer": "De este movimiento no hay nada apuntado a ningún papel.",
    "traspaso_titulo": "Es un traspaso entre cuentas tuyas",
    "traspaso_explica": (
        "Si este dinero solo ha cambiado de cuenta, dilo: así no cuenta como ingreso ni como gasto."
    ),
    "traspaso_ya_esta": "Este movimiento está atado a otro: ese dinero solo ha cambiado de cuenta.",
    "traspaso_el_otro": "La otra parte del traspaso",
    "traspaso_pista": "Tiene que ser de otra cuenta tuya, del mismo importe y al revés.",
    "traspaso_elige": "Elige el otro movimiento",
    "traspaso_atar": "ATAR EL TRASPASO",
    "traspaso_quitar": "QUITAR EL TRASPASO",
    "sin_parejas": "No hay ningún movimiento de otra cuenta tuya al que atarlo.",
    "corregir": "CORREGIR EL IMPORTE A MANO",
    # --- los botones de los formularios (los lee `app.js`, no la pantalla) ---
    "guardar": "GUARDAR",
    "cancelar": "DEJARLO",
    "guardando": "Guardando…",
    # --- el alta de una cuenta (sin ningún dato de banca) ---
    "form_cuenta_titulo": "Añadir una cuenta",
    "form_cuenta_pista": (
        "Aquí no se pide ninguna clave ni el número entero de la cuenta: el programa no se conecta a tu "
        "banco, solo lee el fichero que le des."
    ),
    "cuenta_nombre": "Cómo llamas a esta cuenta",
    "cuenta_nombre_pista": "Un nombre que reconozcas: «La del día a día», «La del gasóleo».",
    "cuenta_banco": "Qué banco es",
    "cuenta_banco_pista": "Si no quieres apuntarlo, déjalo en blanco.",
    "cuenta_ultimos": "Los cuatro últimos números",
    "cuenta_ultimos_pista": (
        "Solo los cuatro últimos. El número entero no hace falta para nada y no se guarda."
    ),
    "cuenta_propia": "Es una cuenta tuya",
    "cuenta_propia_pista": "Lo que se mueve entre tus cuentas no es un ingreso ni un gasto.",
    # --- cómo escribe el banco (el perfil de formato) ---
    "form_perfil_titulo": "Cómo escribe tu banco",
    "form_perfil_pista": (
        "Si tu banco escribe las fechas o los importes de una manera que el programa no puede adivinar, "
        "díselo aquí una vez y se acuerda la próxima vez."
    ),
    "perfil_nombre": "Cómo llamas a esta forma de escribir",
    "perfil_nombre_pista": "Por ejemplo: «El extracto de la cuenta del gasóleo».",
    "perfil_cuenta": "De qué cuenta es",
    "perfil_cuenta_pista": "Si vale para todas tus cuentas, déjalo sin decir.",
    "perfil_decimal": "Cómo escribe los decimales",
    "perfil_fecha": "Cómo escribe las fechas",
    "perfil_sin_signo": "Cuando un importe no trae signo, ¿qué quiere decir?",
    "decimal_coma": "Con coma (1.234,56)",
    "decimal_punto": "Con punto (1,234.56)",
    "fecha_dmy": "Día/mes/año (31/12/2026)",
    "fecha_mdy": "Mes/día/año (12/31/2026)",
    "sin_signo_entra": "Que el dinero entra",
    "sin_signo_sale": "Que el dinero sale",
    # --- la corrección del importe que no consta ---
    "form_correccion_titulo": "Corregir este movimiento",
    "form_correccion_pista": (
        "Sirve para escribir el importe que no consta en el fichero del banco. Si ya has apuntado este "
        "dinero a un papel, deshaz primero la conciliación."
    ),
    "correccion_importe": "El importe",
    "correccion_importe_pista": "Como lo escribe tu banco: 1.234,56",
    "correccion_signo": "Si el dinero entra o sale",
    "signo_entra": "Entra",
    "signo_sale": "Sale",
    "correccion_concepto": "Qué fue",
    "correccion_motivo": "Por qué lo corriges",
    "correccion_motivo_pista": "Escríbelo pensando en que lo vas a leer dentro de dos años.",
    # --- cómo está un movimiento (el servidor manda la clave, no la frase) ---
    "estado_sin_conciliar": "Sin cuadrar",
    "estado_conciliado_en_parte": "A medias",
    "estado_conciliado": "Cuadrado",
    "estado_no_se_puede_conciliar": "No consta el importe",
    # --- lo que no consta de una línea ---
    "falta_importe_no_consta": "No consta el importe",
    "falta_saldo_no_consta": "No consta el saldo",
    "falta_referencia_no_consta": "No trae referencia",
    "falta_concepto_no_consta": "No trae concepto",
    "falta_importe_ilegible_en_la_fila": "El importe no se ha podido leer",
    "falta_saldo_ilegible": "El saldo no se ha podido leer",
    # --- por qué no se puede cuadrar ---
    "por_que_no_no_consta_el_importe": (
        "En este movimiento no consta el importe, así que no se sabe cuánto se puede apuntar a un papel. "
        "Escríbelo y vuelve a intentarlo."
    ),
    "por_que_no_es_un_traspaso_entre_cuentas_tuyas": (
        "Este movimiento es un traspaso entre cuentas tuyas: ese dinero solo ha cambiado de sitio y no "
        "salda ninguna factura."
    ),
    # --- cómo cuadra una propuesta ---
    "propuesta_exacta": "Cuadra exacto con este papel",
    "propuesta_agrupada": "Cuadra con varios papeles a la vez",
    "propuesta_parcial": "Es una parte de lo que le falta",
}


# --------------------------------------------------------------------------
# La bandeja de los papeles (T08, S10, 06/10/2026)
# --------------------------------------------------------------------------
#
# **Lo que llega y hay que revisar**, que no es lo mismo que «los papeles» (lo que ya está archivado):
# la bandeja es la mesa de la entrada y «los papeles» es el armario. Las palabras son las del agricultor,
# y las tres que más importan se dicen aquí para que nadie las busque: **el original** (el fichero tal y
# como llegó, que no se toca), **la propuesta** (lo que el programa ha leído, que no es un dato) y **lo
# que has aceptado** (que es lo que queda, y todavía sin confirmar).
#
# Dos familias de claves se leen **compuestas**, y las dos las resuelve el servidor y llegan ya escritas:
#
#   · `estado_<estado>` — cómo está un papel (`recien_subido`, `clasificado`, `propuesta_revisada`,
#     `confirmado`) más `estado_desconocido`, que es lo que se dice si el estado no es ninguno de esos.
#     El servidor manda la palabra en `etiqueta_estado`.
#   · `clase_<clase>` — con qué va un papel (`compra`, `gasto`, `venta`, `maquina`, `trabajo`,
#     `inspeccion`) más `clase_desconocida`. El servidor manda la palabra en `etiqueta_clase`.
#
# Y `que_hacer_<estado>`: qué hacer con un papel que está así. **No hay `que_hacer_confirmado`** a
# propósito: de un papel confirmado no hay nada que hacer, y por eso su frase no existe (la pantalla no la
# busca).
BANDEJA: dict = {
    "titulo": "La bandeja de los papeles",
    "explica": (
        "Aquí llega lo que todavía no has mirado: la foto de una factura, el ticket del gasóleo, el "
        "certificado de una máquina. El papel se guarda tal y como llega, y nada entra en tu cuaderno "
        "hasta que tú lo confirmes."
    ),
    "cuantos": "Tienes {cuantos} papeles en la bandeja.",
    # Con uno solo, «Tienes 1 papeles en la bandeja» (ronda 84).
    "cuantos_uno": "Tienes 1 papel en la bandeja.",
    "sin_papeles": (
        "La bandeja está vacía: no tienes ningún papel esperando. Sube uno con el botón de aquí arriba "
        "cuando te llegue."
    ),
    "sin_resultados": "Ningún papel coincide con lo que buscas. Prueba con otras letras o pulsa VER TODO.",
    "faltan_por_decir_de_que_son": (
        "Hay papeles a los que todavía no has dicho de qué son. Ábrelos y dilo: un papel que no se sabe "
        "qué es no sirve de nada en una inspección."
    ),
    "no_consta": "No consta",
    "si": "Sí",
    "no": "No",
    "buscando": "Buscando…",
    # Lo que se dice de algo enlazado que ya no está en el cuaderno: se dice, en vez de enseñar su número.
    "eso_ya_no_esta": "eso ya no está en tu cuaderno",
    # --- subir: el original entra tal y como llega ---
    "subir_titulo": "Subir un papel",
    "subir_explica": (
        "Elige el fichero (una foto o un PDF) y di de qué es. El papel se guarda tal y como llegó."
    ),
    "nada_se_apunta": (
        "Subir no apunta nada al cuaderno: solo guarda el papel. Lo que se lea de él es una propuesta, "
        "y la confirmas tú."
    ),
    "fichero": "El papel, en una foto o en un PDF",
    "fichero_pista": "Hazle una foto al papel o elige el fichero que ya tienes.",
    "fichero_elegido": "El fichero que has elegido es",
    "de_que_es": "¿De qué es?",
    "de_que_es_pista": "Si todavía no lo sabes, déjalo en «no lo sé» y díselo luego desde la bandeja.",
    "no_lo_se_todavia": "Todavía no lo sé",
    "decir_de_que_es": "DECIR DE QUÉ ES",
    "comprobar_el_fichero": "COMPROBAR EL FICHERO",
    "comprobando": "Comprobando…",
    "subir_el_papel": "SUBIR EL PAPEL",
    "subiendo": "Subiendo…",
    "olvidar_el_fichero": "ELEGIR OTRO FICHERO",
    "lo_que_se_ha_comprobado": "Lo que he visto del fichero",
    "la_huella": "Su huella",
    "la_huella_pista": (
        "Es la huella del fichero tal y como llegó. Sirve para saber que este papel es este y no otro, y "
        "no cambia nunca."
    ),
    "tamano": "Cuánto ocupa",
    "ya_estaba": "Este mismo papel ya lo tienes",
    "ya_estaba_explica": (
        "No se ha guardado otra vez: el mismo papel no puede estar dos veces. Es este:"
    ),
    "del_que_ya_estaba_subido": "Lo subiste el",
    "abrir_el_que_ya_estaba": "VER EL PAPEL QUE YA TENÍA",
    "no_estaba": "Este papel no lo tenías: puedes subirlo.",
    # --- la lista ---
    "lista_titulo": "Lo que hay que revisar",
    "lista_explica": (
        "Cada papel, con cómo está y qué le falta. Los que confirmes salen de aquí y se ven en LOS PAPELES."
    ),
    "buscar": "Buscar en la bandeja",
    "buscar_pista": "Escribe parte del nombre o de quién te lo dio.",
    "buscar_boton": "BUSCAR",
    "ver_todo": "VER TODO",
    "cuales_ver": "Cuáles ver",
    "todos_los_estados": "Todos",
    "sin_revisar": "Sin revisar",
    "todos_los_tipos": "De todo",
    "lo_que_es": "Qué es",
    "el_dia_del_papel": "El día del papel",
    "de_quien": "De quién",
    "el_fichero": "El fichero",
    "sin_fichero": "Sin fichero",
    "su_lectura": "Su lectura",
    "tiene_propuesta": "Leído, sin revisar",
    "sin_propuesta": "Todavía no se ha leído",
    "enlazado_con": "Va con",
    "sin_enlazar": "Sin enlazar con nada",
    "abrir": "MIRAR ESTE PAPEL",
    "los_papeles": "VER TODOS LOS PAPELES",
    # --- la ficha: el original, siempre a la vista ---
    "ficha_titulo": "Este papel",
    "el_original": "El papel, tal y como llegó",
    "el_original_explica": (
        "Este es el fichero que subiste. El programa no lo cambia nunca: lo que se lee de él va aparte."
    ),
    "ver_el_original": "VER EL ORIGINAL",
    "sin_fichero_aviso": (
        "Este papel está apuntado sin su fichero. Súbelo desde LOS PAPELES para poder leerlo."
    ),
    # --- la propuesta: lo que se ha leído, y que no es un dato ---
    "la_propuesta": "Lo que el programa ha leído",
    "la_propuesta_explica": "Esto es una propuesta, no un dato: nada de esto ha entrado en tu cuaderno.",
    # **La frase que sostiene la mitad del ticket.** No hay corpus (T07) para medir la lectura, así que no
    # se puede decir que esté bien: se dice que no se puede medir, y se pide al agricultor que la mire.
    "no_se_mide_la_lectura": (
        "El programa no dice si esta lectura está bien: para eso habría que compararla con muchísimas "
        "facturas de verdad, y esa colección todavía no existe. Mírala tú, campo por campo."
    ),
    "leer_el_papel": "LEER EL PAPEL",
    "leyendo": "Leyendo el papel…",
    "no_hay_propuesta": "De este papel no hay ninguna lectura. Puedes escribir los datos a mano.",
    "este_papel_no_lo_se_leer": (
        "De este tipo de papel todavía no sé leer nada. Escribe los datos a mano y quedan guardados igual."
    ),
    "avisos_titulo": "Lo que hay que mirar de esta lectura",
    "las_lineas": "Las líneas que he leído",
    "sin_lineas": "No he reconocido ninguna línea. Puede ser una factura de servicios.",
    "lineas_leidas": "Líneas leídas",
    "lineas_que_cuadran": "Con la cuenta bien",
    # Lo único que se puede afirmar de una línea sin corpus: si su cuenta cuadra, que es aritmética.
    "la_cuenta_cuadra": "La cuenta cuadra",
    "la_cuenta_no_cuadra": "La cuenta no cuadra: mírala antes de guardar",
    "cuadra_el_total": "La base más el IVA da el total",
    "suman_las_lineas": "Las líneas suman la base",
    "cantidad": "Cuánto",
    "precio": "El precio",
    "importe": "El importe",
    "proveedor": "El proveedor",
    "nif_del_proveedor": "Su NIF",
    "numero_de_factura": "El número de factura",
    "fecha": "La fecha",
    "base_imponible": "La base",
    "cuota_de_iva": "El IVA",
    "tipo_de_iva": "El tipo de IVA",
    "total": "El total",
    "descartada": "Esta lectura la descartaste: no te servía.",
    # --- revisar y confirmar: dos actos distintos ---
    "lo_aceptado": "Lo que has aceptado",
    "lo_aceptado_explica": "Esto es lo que queda de este papel. Todavía no está confirmado.",
    "revisar": "REVISAR Y DECIR QUÉ QUEDA",
    "revisar_titulo": "Decide qué queda",
    "revisar_pista": (
        "Corrige lo que haga falta y guarda: lo que guardes es lo que quedará. Después lo confirmas."
    ),
    "guardar": "GUARDAR LO QUE QUEDA",
    "guardando": "Guardando…",
    "cancelar": "DEJARLO",
    "sin_aceptar_nada": "Todavía no has dicho qué queda de este papel.",
    "hay_que_revisar_antes": (
        "Antes de confirmar hay que decir qué queda: revisa la lectura o escribe los datos a mano."
    ),
    "confirmar": "CONFIRMAR ESTE PAPEL",
    "confirmando": "Confirmando…",
    "confirmar_explica": (
        "Al confirmarlo, lo que has aceptado pasa al papel con tu nombre y la fecha. El fichero no se toca."
    ),
    "ya_esta_en_los_papeles": "Este papel ya está confirmado y se ve en LOS PAPELES.",
    "confirmado_por": "Lo confirmaste tú",
    "confirmado_en": "Cuándo",
    "motivo": "¿Por qué no te sirve?",
    "descartar_pista": "Dímelo, para que quede apuntado por qué este papel se escribió a mano.",
    "descartar_la_propuesta": "ESTA LECTURA NO ME SIRVE",
    # --- enlazar: con lo que ya existe, y sin crear nada ---
    "enlazar_titulo": "Con qué va este papel",
    "enlazar_explica": (
        "Un papel puede ir con una compra, un gasto, una venta, una máquina, un trabajo o una inspección."
    ),
    "no_crea_nada": (
        "Enlazar no crea nada: ni un gasto, ni una factura, ni una venta. Solo dice con qué va este papel."
    ),
    "de_que_clase": "¿Con qué quieres enlazarlo?",
    "buscar_candidato": "Buscar lo que ya tienes",
    "buscar_candidato_pista": "Escribe parte del nombre si no lo encuentras en la lista.",
    "buscar_candidatos": "BUSCAR",
    "cual_de_ellos": "¿Cuál de ellos?",
    "elige_uno": "Elige uno",
    "enlazar": "ENLAZARLO",
    "enlazando": "Enlazando…",
    "enlazado_titulo": "Con esto va",
    "desenlazar": "QUITARLO DE AHÍ",
    "sin_candidatos": "No hay nada de eso en tu cuaderno. Apúntalo primero en su pantalla y vuelve.",
    # --- rectificar: las dos quedan ---
    "rectificar_titulo": "Este papel corrige a otro",
    "rectificar_explica": (
        "Si es la factura corregida que sustituye a la anterior, dilo aquí. Las dos quedan: la corregida "
        "sigue ahí, marcada, y no se borra."
    ),
    "a_que_papel": "¿A qué papel corrige?",
    "elige_el_papel": "Elige el papel",
    "rectificar": "DECIR QUE CORRIGE A ESE",
    "rectifica_a": "Corrige a",
    "rectificada_por": "Este papel está corregido por",
    "nadie_lo_ha_corregido": "Este papel no corrige a ninguno ni lo ha corregido nadie.",
    "volver_a_la_bandeja": "VOLVER A LA BANDEJA",
    # --- cómo está un papel (`estado_<estado>`) ---
    "estado_recien_subido": "Recién subido",
    "estado_clasificado": "Sin leer",
    "estado_propuesta_revisada": "Revisado, sin confirmar",
    "estado_confirmado": "Confirmado",
    "estado_desconocido": "No se sabe cómo está",
    # --- y qué hacer con él, según cómo esté (`que_hacer_<estado>`) ---
    "que_hacer_recien_subido": (
        "Falta decir de qué es: elige su tipo y el papel sale de «recién subido»."
    ),
    "que_hacer_clasificado": "Falta mirarlo: léelo (o escríbelo a mano) y di qué queda.",
    "que_hacer_propuesta_revisada": "Ya has dicho qué queda: confírmalo cuando quieras.",
    # --- con qué se puede enlazar (`clase_<clase>`): el servidor manda la clave, la pantalla la palabra ---
    "clase_compra": "Una factura de lo que has comprado",
    "clase_gasto": "Un gasto",
    "clase_venta": "Una venta de tu cosecha",
    "clase_maquina": "Una máquina",
    "clase_trabajo": "Un trabajo hecho",
    "clase_inspeccion": "Una inspección de una máquina",
    "clase_desconocida": "Algo de tu cuaderno",
}

# ── La normativa (07/10/2026) ────────────────────────────────────────────────────────────────
# Las frases de la pantalla que ensena las reglas de la normativa. **Nada de jerga**: lo que se ve habla de
# obligaciones, de fuentes oficiales y de lo que no se sabe, no de ficheros ni de programas.
NORMATIVA: dict[str, str] = {
    "titulo": "La normativa",
    "pista": "Lo que hay que cumplir en el cuaderno, con su fuente oficial para poder comprobarlo.",
    "fuente": "Fuente oficial",
    "fuentes": "Fuentes oficiales",
    "sin_clasificar": "Sin clasificar",
    # **Por que se dice «sin clasificar» en vez de callarse** (07/10/2026): una obligacion y una recomendacion no
    # se leen igual, y decir cual es cada una sin saberlo seria enganar al agricultor. Se dice lo que se sabe y
    # se calla lo que no, pero **diciendo que no se sabe**.
    "sin_tipo": "Todavia no se ha clasificado esta regla: puede ser una obligacion o una recomendacion.",
    "sin_estado": "Todavia no se ha revisado si esta regla esta en vigor.",
    "como_se_lee": "Es un resumen para el cuaderno. Lo que dice la norma, entero, esta en su fuente oficial.",
    "sin_normativa": "No hay ninguna regla cargada.",
}

# ── La ayuda de la normativa (07/10/2026) ─────────────────────────────────────────────────────
# Lo que se le enseña al agricultor en la pantalla de normativa, regla por regla. **Aquí y no en el módulo de
# datos**: son textos visibles, y en esta casa los textos visibles viven aquí, para poder revisarlos juntos y
# para que la prueba de la jerga los mire. Cada uno dice **qué tiene que tener apuntado** y **qué no debe dar
# por hecho**, con las palabras de la fuente y sin inventarse ninguna obligación.
AYUDA_DE_LA_NORMATIVA: dict[str, str] = {
    'N01': 'Ten apuntado qué práctica de condicionalidad has elegido y con qué límites: el historial de esa tierra, sus superficies y clasificaciones, la alternativa que aplicas y las excepciones, si las tienes.',
    'N02': 'El ecorregimen que has pedido: qué parcelas entran, qué superficie cuenta, los cultivos principales y secundarios, y por qué has dejado fuera lo que hayas dejado. Un plan de un año no comprueba el año siguiente: eso es solo una simulación.',
    'N03': 'Los compromisos que has adquirido: expediente, régimen, solicitud, resolución, fechas de inicio y fin, superficie o unidades comprometidas y sus condiciones. Si cambias, cedes o renuncias, se conserva la resolución.',
    'N04': 'Las excepciones que se aplican en tu zona: municipio o comarca, la labor afectada y hasta cuándo vale. Una excepción de otra campaña o de otra comunidad no te desbloquea la labor.',
    'N05': 'La ficha del producto y la autorización de uso no son lo mismo, y la marca no basta para saber qué formulación ni qué uso está permitido. Guarda la etiqueta y la consulta que hiciste. Una dosis máxima general no autoriza cualquier cultivo ni cualquier plaga.',
    'N06': 'Lo que pide el plan de abonado: cultivo y rendimiento previsto, análisis, agua y otros aportes, la composición del abono con sus unidades, la superficie que has abonado de verdad, la fecha y la técnica. El nitrógeno total no es lo mismo que sus fracciones, ni el fósforo que el P2O5. Y el programa no sustituye al asesor que la norma exige.',
    'N07': 'Guarda la etiqueta, la factura, la procedencia y los papeles de autorización si los hay. Una semilla comprada sin etiqueta no queda certificada por eso, y la tuya propia se puede documentar sin darla por ilegal.',
    'N08': 'La condición ecológica de la explotación, del producto y del lote, cada una con su prueba. Si hace falta una autorización individual, guarda el período, la especie o variedad y la cantidad. Que algo no esté en un catálogo no es un permiso.',
    'N09': 'La ITEAF y la ITV son dos obligaciones distintas, y no vencen a la vez para el tractor, el remolque y el equipo de aplicación. Manda la fecha del documento de inspección.',
    'N10': 'Llevar los registros, el formato exigido y la comunicación a la Administración son tres cosas separadas. Que el cuaderno sea voluntario no te exime de lo que pida tu sector.',
}
