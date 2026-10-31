// Puerta: la vista previa arranca de verdad y se puede parar.
//
//   node tests_js/_probar-vista-previa.mjs
//
// Arranca `scripts/vista_previa.py` en un puerto libre y con una carpeta de datos
// temporal (nunca la de la explotación), espera a que `/` conteste 200 con la
// pantalla de CUE Digital, comprueba que el servidor sigue vivo un momento
// después y lo para. En Windows, matar el proceso no permite una parada
// ordenada; allí solo se exige que el proceso termine.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { get } from "node:http";

const aqui = dirname(fileURLToPath(import.meta.url));
const backend = join(aqui, "..");
const raiz = join(backend, "..");
const enWindows = process.platform === "win32";

function elPython() {
  const delVenV = enWindows
    ? join(raiz, ".venv", "Scripts", "python.exe")
    : join(raiz, ".venv", "bin", "python");
  if (existsSync(delVenV)) return delVenV;
  return enWindows ? "python" : "python3";
}

function unPuertoLibre() {
  return new Promise((resolver, rechazar) => {
    const servidor = createServer();
    servidor.unref();
    servidor.on("error", rechazar);
    servidor.listen(0, "127.0.0.1", () => {
      const { port } = servidor.address();
      servidor.close(() => resolver(port));
    });
  });
}

function pedirLaPantalla(puerto) {
  return new Promise((resolver) => {
    const peticion = get(
      { host: "127.0.0.1", port: puerto, path: "/", timeout: 2000 },
      (respuesta) => {
        let cuerpo = "";
        respuesta.setEncoding("utf8");
        respuesta.on("data", (trozo) => {
          cuerpo += trozo;
        });
        respuesta.on("end", () => {
          resolver({
            estado: respuesta.statusCode,
            tipo: respuesta.headers["content-type"] ?? "",
            cuerpo,
          });
        });
      },
    );
    peticion.on("timeout", () => peticion.destroy());
    peticion.on("error", () => resolver(null));
  });
}

function dormir(milisegundos) {
  return new Promise((resolver) => setTimeout(resolver, milisegundos));
}

async function main() {
  const python = elPython();
  const puerto = await unPuertoLibre();
  const datos = mkdtempSync(join(tmpdir(), `cuedigital-vista-previa-`));
  let salida = "";
  let servidor;

  try {
    servidor = spawn(
      python,
      ["scripts/vista_previa.py", "--puerto", String(puerto), "--datos", datos],
      {
        cwd: backend,
        env: { ...process.env, PORT: String(puerto) },
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    const recoger = (trozo) => {
      salida = (salida + trozo.toString("utf8")).slice(-8000);
    };
    servidor.stdout.on("data", recoger);
    servidor.stderr.on("data", recoger);

    let terminado = false;
    servidor.on("exit", () => {
      terminado = true;
    });

    const limite = Date.now() + 120_000;
    let pantalla = null;
    while (Date.now() < limite) {
      if (terminado) {
        throw new Error(
          `la vista previa terminó antes de contestar (código ${servidor.exitCode}).\n${salida}`,
        );
      }
      pantalla = await pedirLaPantalla(puerto);
      if (pantalla && pantalla.estado === 200) break;
      await dormir(250);
    }

    if (!pantalla || pantalla.estado !== 200) {
      throw new Error(`«/» no contestó 200 en 120 s.\n${salida}`);
    }
    if (!pantalla.tipo.includes("text/html")) {
      throw new Error(`«/» no contestó como página («${pantalla.tipo}»).\n${salida}`);
    }
    if (!pantalla.cuerpo.includes("CUE Digital")) {
      throw new Error(`«/» no trae la pantalla de CUE Digital.\n${salida}`);
    }

    // Que no se caiga solo justo después de contestar: lo que se prueba no es
    // que llegue a arrancar, es que se quede en pie.
    await dormir(1200);
    if (terminado) {
      throw new Error(
        `la vista previa se cayó después de contestar (código ${servidor.exitCode}).\n${salida}`,
      );
    }

    servidor.kill(enWindows ? undefined : "SIGTERM");
    const codigo = await new Promise((resolver) => {
      if (terminado) return resolver(servidor.exitCode);
      servidor.once("exit", (valor) => resolver(valor));
      setTimeout(() => {
        servidor.kill("SIGKILL");
        resolver(servidor.exitCode);
      }, 10_000).unref();
    });

    if (!enWindows && codigo !== 0) {
      throw new Error(`al pararla terminó con código ${codigo}.\n${salida}`);
    }
    if (!enWindows && !salida.includes("vista previa parada")) {
      throw new Error(`no dijo que la paraba.\n${salida}`);
    }
  } finally {
    if (servidor && servidor.exitCode === null) servidor.kill("SIGKILL");
    rmSync(datos, { recursive: true, force: true });
  }
}

main()
  .then(() => {
    console.log("vista previa: arranca, contesta / y se para");
  })
  .catch((fallo) => {
    console.error(`vista previa: FALLA — ${fallo.message}`);
    process.exit(1);
  });
