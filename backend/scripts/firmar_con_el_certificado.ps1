<#
    firmar_con_el_certificado.ps1 — Firmar un texto con la clave privada del certificado que está en
    el almacén de Windows, **sin sacarla de ahí**.

    POR QUÉ EXISTE, Y POR QUÉ EN POWERSHELL

    Para presentar el cuaderno por el interfaz de la Junta hay que mandar el parámetro `data-signed`:
    el NIF del titular **firmado con la clave privada** de su certificado de dominio. El programa está
    en Python, y su clave privada **no es exportable**: no se puede leer en un fichero ni pasar a
    OpenSSL. La salida no es exportarla (una clave exportada es una clave que se puede copiar), sino
    **firmar donde vive**: Windows firma por dentro y el programa solo recibe la firma.

    Esto es lo que hace este script. Lo llamó `iuws_cliente.datos_firmados()` cuando el programa
    necesita firmar de verdad, y también se puede lanzar a mano.

    QUÉ FIRMA Y CÓMO

      · RSA con relleno PKCS#1 v1.5 y SHA-256, que es exactamente lo que espera el interfaz y lo
        mismo que haría la librería `cryptography` si la clave se pudiera leer.
      · La firma sale en **base64**, que es como se manda en la cabecera.

    QUÉ NO HACE

      · **No exporta** la clave ni el certificado: no hay ningún `Export-*` en este fichero.
      · **No toca la red**: firma en local, no llama a la Junta.
      · **No escribe ficheros**: la firma sale por la salida estándar.
      · No imprime la clave privada por ningún lado (no se puede: no sale del almacén).

    CÓMO SE LANZA

    ```powershell
    # Firmar un texto y sacar la firma en base64
    powershell -File backend\scripts\firmar_con_el_certificado.ps1 -Texto "12345678Z"

    # Y comprobar que la firma es buena, que es la prueba de que esto funciona
    powershell -File backend\scripts\firmar_con_el_certificado.ps1 -Texto "12345678Z" -Comprobar
    ```

    El certificado se busca por el NIF o la huella que se pase en `-Asunto` o en la variable
    `CUEDIGITAL_CERTIFICADO`. **En el repositorio no hay ningún dato personal de nadie.**
#>
[CmdletBinding()]
param(
    # Lo que se firma: el NIF o CIF del titular, tal y como lo pide el Anexo VI.
    [Parameter(Mandatory = $true)]
    [string]$Texto,

    # Por dónde se busca el certificado: el NIF del titular o su huella. Si no se pasa, se lee de
    # `CUEDIGITAL_CERTIFICADO`.
    [string]$Asunto = $env:CUEDIGITAL_CERTIFICADO,

    # Con esto, además de firmar, comprueba la firma con la clave pública. Es la prueba de que el
    # mecanismo funciona, y no toca la red.
    [switch]$Comprobar
)

$ErrorActionPreference = "Stop"

if (-not $Asunto) {
    Write-Error "Falta el certificado: pásalo con -Asunto (el NIF o la huella) o en la variable CUEDIGITAL_CERTIFICADO."
    exit 2
}

$certificado = Get-ChildItem Cert:\CurrentUser\My |
    Where-Object { ($_.Subject -like "*$Asunto*" -or $_.Thumbprint -eq $Asunto) -and $_.HasPrivateKey } |
    Select-Object -First 1

if (-not $certificado) {
    Write-Error "No hay ningún certificado con «$Asunto» y clave privada en el almacén de Windows."
    exit 2
}

# La clave privada se pide al almacén y se usa desde ahí: no se puede leer ni copiar, pero sí firmar.
$clavePrivada = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($certificado)
if ($null -eq $clavePrivada) {
    Write-Error "El certificado no tiene clave privada utilizable desde Windows."
    exit 3
}

$datos = [System.Text.Encoding]::UTF8.GetBytes($Texto)

try {
    $firma = $clavePrivada.SignData(
        $datos,
        [System.Security.Cryptography.HashAlgorithmName]::SHA256,
        [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
    )
} finally {
    $clavePrivada.Dispose()
}

$firmaEnBase64 = [System.Convert]::ToBase64String($firma)

if ($Comprobar) {
    $clavePublica = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPublicKey($certificado)
    $buena = $clavePublica.VerifyData(
        $datos,
        $firma,
        [System.Security.Cryptography.HashAlgorithmName]::SHA256,
        [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
    )
    $clavePublica.Dispose()
    Write-Output "Certificado: $($certificado.Subject)"
    Write-Output "Texto firmado: $Texto"
    Write-Output "Firma (base64): $firmaEnBase64"
    Write-Output "La firma se comprueba con la clave publica del certificado: $buena"
    if (-not $buena) { exit 4 }
} else {
    # Solo la firma, para que el programa en Python la pueda leer sin tener que buscar nada.
    Write-Output $firmaEnBase64
}
