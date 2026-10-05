<#
    probar_iuws_con_certificado.ps1 — Llamar al interfaz de la Junta (IUWS) **con el certificado del
    agricultor**, desde el propio Windows donde está guardado.

    POR QUÉ EXISTE ESTO, Y POR QUÉ ESTÁ EN POWERSHELL Y NO EN PYTHON

    El certificado de David está en el almacén de Windows (`Cert:\CurrentUser\My`) y su clave privada
    está marcada como **no exportable**: no se puede sacar de ahí, y por eso no se puede usar desde
    `httpx` ni desde ningún programa que necesite la clave en un fichero. Lo que sí se puede hacer es
    **usarla donde vive**: Windows firma el saludo TLS por dentro y el programa nunca ve la clave.

    Eso es lo que hace este script, y es la única forma de comprobar de verdad qué contesta el
    interfaz sin pedirle a David que exporte su clave (que es justo lo que no se debe hacer: una
    clave privada exportada es una clave privada que se puede copiar).

    QUÉ HACE Y QUÉ NO HACE

      · Hace **llamadas de lectura** (`GET`): la versión del descriptor y la llamada de comunicación
        (`comunicacion/PRUEBA`), que es la que el propio interfaz pone para comprobar credenciales.
      · **No manda ningún dato del agricultor** y **no crea ni presenta nada**: no llama a `crear` ni
        a `exportar`. Presentar de verdad es otra cosa y solo se hace cuando el interfaz lo permita.
      · **No escribe la clave en ningún sitio** y **no exporta el certificado**: no llama a
        `Export-PfxCertificate` ni a `Export-Certificate`, y no deja ningún fichero.
      · Lo único que imprime son datos públicos del certificado (su asunto, su huella y sus fechas)
        y **lo que contesta el interfaz, tal cual**.

    CÓMO SE LANZA

    ```powershell
    # El certificado se busca por el NIF (o por la huella) que se le pase.
    powershell -File backend\scripts\probar_iuws_con_certificado.ps1 `
        -Asunto 70922320A `
        -Direccion https://servicios.ayg.jcyl.es `
        -Rutas /IUWS/api/version,/IUWS/api/comunicacion/PRUEBA
    ```

    **El identificador del certificado se pasa por parámetro o por variable de entorno**
    (`CUEDIGITAL_CERTIFICADO`), nunca se escribe en el repositorio: el repositorio no lleva datos
    personales de nadie.
#>
[CmdletBinding()]
param(
    # Por dónde se busca el certificado: el NIF del titular o su huella. Si no se pasa, se lee de
    # `CUEDIGITAL_CERTIFICADO`.
    [string]$Asunto = $env:CUEDIGITAL_CERTIFICADO,

    # La dirección del interfaz. Por defecto, la del entorno de integración (que es el que se puede
    # usar para ensayar). La de la comunidad se pasa a mano: `https://servicios.ayg.jcyl.es`.
    [string]$Direccion = "https://sga.entornointegracion.es",

    # Las rutas que se llaman, separadas por comas. Las de por defecto son las dos de lectura.
    [string[]]$Rutas = @("/IUWS/api/version", "/IUWS/api/comunicacion/PRUEBA"),

    [int]$SegundosDeEspera = 30
)

$ErrorActionPreference = "Stop"

if (-not $Asunto) {
    Write-Output "Falta el certificado: pásalo con -Asunto (el NIF o la huella) o en la variable CUEDIGITAL_CERTIFICADO."
    exit 2
}

# TLS 1.2: sin esto, Windows PowerShell 5.1 puede intentar negociar versiones que el servidor ya no
# admite, y el fallo que sale es de protocolo, no del certificado.
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$certificado = Get-ChildItem Cert:\CurrentUser\My |
    Where-Object { ($_.Subject -like "*$Asunto*" -or $_.Thumbprint -eq $Asunto) -and $_.HasPrivateKey } |
    Select-Object -First 1

if (-not $certificado) {
    Write-Output "No hay ningún certificado con «$Asunto» y clave privada en el almacén de Windows."
    Write-Output "Míralo con:  Get-ChildItem Cert:\CurrentUser\My | Select-Object Subject, Thumbprint, HasPrivateKey"
    exit 2
}

Write-Output "Certificado: $($certificado.Subject)"
Write-Output "Valido hasta: $($certificado.NotAfter) | huella: $($certificado.Thumbprint)"
Write-Output "Clave privada utilizable desde Windows: $($certificado.HasPrivateKey)"
Write-Output "Direccion: $Direccion"
Write-Output ""

foreach ($ruta in $Rutas) {
    $url = "$Direccion$ruta"
    try {
        $peticion = [System.Net.HttpWebRequest]::Create($url)
        $peticion.Method = "GET"
        $peticion.Timeout = $SegundosDeEspera * 1000
        $peticion.AllowAutoRedirect = $false
        $peticion.UserAgent = "CueDigital/comprobacion"
        # Aquí es donde entra la clave privada: la usa Windows, dentro del saludo TLS.
        $peticion.ClientCertificates.Add($certificado) | Out-Null
        $respuesta = $peticion.GetResponse()
        $codigo = [int]$respuesta.StatusCode
        $estado = $respuesta.StatusCode
        $lector = New-Object System.IO.StreamReader($respuesta.GetResponseStream())
        $cuerpo = $lector.ReadToEnd()
        $lector.Close()
        $respuesta.Close()
        if ($cuerpo.Length -gt 800) { $cuerpo = $cuerpo.Substring(0, 800) + "..." }
        Write-Output "$url"
        Write-Output "  -> $codigo $estado"
        Write-Output "  $cuerpo"
    } catch [System.Net.WebException] {
        $respuesta = $_.Exception.Response
        if ($respuesta -ne $null) {
            $codigo = [int]$respuesta.StatusCode
            $estado = $respuesta.StatusCode
            $lector = New-Object System.IO.StreamReader($respuesta.GetResponseStream())
            $cuerpo = $lector.ReadToEnd()
            $lector.Close()
            if ($cuerpo.Length -gt 800) { $cuerpo = $cuerpo.Substring(0, 800) + "..." }
            Write-Output "$url"
            Write-Output "  -> $codigo $estado"
            Write-Output "  $cuerpo"
        } else {
            $error = $_.Exception
            while ($error.InnerException) { $error = $error.InnerException }
            Write-Output "$url"
            Write-Output "  -> SIN RESPUESTA: $($error.GetType().Name): $($error.Message)"
        }
    }
    Write-Output ""
}
