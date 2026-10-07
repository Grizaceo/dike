#!/usr/bin/env python3
"""Verificación de un commitment de Diké por un TERCERO.

Este script es deliberadamente autónomo:

* NO importa nada de Diké. Si usara el mismo código que produce la firma, no
  probaría nada: solo confirmaría que el código es consistente consigo mismo.
* Solo usa la biblioteca estándar y `cryptography`.
* Hace lo mismo que la receta de `jq` + OpenSSL de KEYS.md, paso por paso.

Uso:
    python3 verificar_tercero.py <commitment.json> <commitment.sig.json> <pubkey.pem>

Código de salida:
    0  VERIFICADO.
    1  NO VERIFICADO. Los archivos se leyeron, pero algo no cuadra: el sobre no
       declara el contrato esperado, el hash no coincide, la firma no es de
       esta llave o no es válida.
    2  NO SE PUDO EVALUAR. Uso incorrecto, archivo ilegible, JSON inválido o
       con claves duplicadas, sobre incompleto o con un campo de más, un número
       que no es un entero simple de hasta 15 dígitos (2.0, 2e0, -0), una clave
       pública que no está en su forma canónica.

Qué se firma (contrato V2): los 64 caracteres hexadecimales de
    sha256("role:algorithm:schema_version:commitment_hash")
donde commitment_hash es el SHA-256 del commitment en JSON canónico (claves
ordenadas, sin espacios, UTF-8 sin escapar).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA = "dike-content-signature-v2"
ROL = "content-integrity"
ALGORITMO = "ed25519"
CAMPOS_SOBRE = ("schema_version", "role", "algorithm", "key_id", "commitment_hash", "signature")

VERIFICADO, NO_VERIFICADO, NO_EVALUABLE = 0, 1, 2


class EntradaInvalida(Exception):
    """La entrada no se puede evaluar (salida 2)."""


def _sin_duplicados(pares):
    """Una clave repetida es una trampa: `json.loads` se queda con la última
    aparición, y quien lee el archivo ve primero la otra."""
    vistas = {}
    for clave, _valor in pares:
        vistas[clave] = vistas.get(clave, 0) + 1
    repetidas = [k for k, n in vistas.items() if n > 1]
    if repetidas:
        raise EntradaInvalida(f"claves JSON duplicadas: {repetidas}")
    return dict(pares)


def _constante_no_json(nombre):
    raise EntradaInvalida(f"{nombre} no es un valor JSON")


def _numero_no_entero(literal):
    raise EntradaInvalida(f"número no admitido ({literal}): un commitment solo lleva enteros simples")


def _entero_canonico(literal):
    # Un entero admite varias escrituras (2, 2e0, 2.0; 0 y -0) y cada
    # herramienta las normaliza distinto. Aquí vale una sola: el entero simple.
    if literal == "-0":
        raise EntradaInvalida("número no admitido (-0): un commitment solo lleva enteros simples")
    # Y de hasta 15 dígitos: un lector de doble precisión (jq antes de 1.7)
    # redondea los más largos, y el hash canónico saldría distinto.
    if len(literal.lstrip("-")) > 15:
        raise EntradaInvalida("número no admitido: un commitment solo lleva enteros de hasta 15 dígitos")
    return int(literal)


def cargar_objeto(ruta: str) -> dict:
    """Lee un archivo JSON cuya raíz es un objeto, sin claves duplicadas."""
    nombre = Path(ruta).name
    try:
        texto = Path(ruta).read_text(encoding="utf-8-sig")  # tolera un BOM inicial
    except (OSError, UnicodeDecodeError) as exc:
        raise EntradaInvalida(f"no se pudo leer {nombre} ({type(exc).__name__})") from exc
    try:
        datos = json.loads(
            texto,
            object_pairs_hook=_sin_duplicados,
            parse_constant=_constante_no_json,
            parse_float=_numero_no_entero,
            parse_int=_entero_canonico,
        )
    except EntradaInvalida as exc:
        raise EntradaInvalida(f"{nombre}: {exc}") from exc
    except ValueError as exc:
        raise EntradaInvalida(f"{nombre} no es JSON válido") from exc
    if not isinstance(datos, dict):
        raise EntradaInvalida(f"{nombre}: la raíz no es un objeto JSON")
    return datos


def hash_canonico(commitment: dict) -> str:
    """SHA-256 del JSON canónico. Reimplementado aquí, no importado."""
    raw = json.dumps(
        commitment, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _no_verificado(motivo: str, *detalle: str) -> int:
    print(motivo)
    for linea in detalle:
        print(linea)
    print("RESULTADO: NO VERIFICADO")
    return NO_VERIFICADO


def main(commitment_path: str, sig_path: str, pubkey_path: str) -> int:
    # ── 0. Leer. Nada de lo que sigue se evalúa si la entrada no es legible ──
    try:
        commitment = cargar_objeto(commitment_path)
        sobre = cargar_objeto(sig_path)
        faltan = [k for k in CAMPOS_SOBRE if not isinstance(sobre.get(k), str)]
        if faltan:
            raise EntradaInvalida(f"sobre incompleto, faltan o no son cadenas: {faltan}")
        # El sobre es cerrado: un campo de más no está firmado, y quien lo lee
        # junto a una firma válida podría darlo por acreditado.
        sobran = sorted(set(sobre) - set(CAMPOS_SOBRE))
        if sobran:
            raise EntradaInvalida(f"el sobre trae campos que la firma no cubre: {sobran}")
        firma_hex = sobre["signature"]
        # Exactamente 64 bytes en hex y en minúsculas, que es como se emite:
        # `bytes.fromhex` a secas ignora espacios y acepta mayúsculas.
        if len(firma_hex) != 128 or not set(firma_hex) <= set("0123456789abcdef"):
            raise EntradaInvalida("la firma del sobre no son 64 bytes en hexadecimal (minúsculas)")
        firma = bytes.fromhex(firma_hex)
        try:
            c_hash = hash_canonico(commitment)
        except UnicodeEncodeError as exc:
            raise EntradaInvalida("el commitment trae texto que no es Unicode válido") from exc
        try:
            pem = Path(pubkey_path).read_bytes()
            pubkey = serialization.load_pem_public_key(pem)
        except OSError as exc:
            raise EntradaInvalida(
                f"no se pudo leer {Path(pubkey_path).name} ({type(exc).__name__})"
            ) from exc
        except (ValueError, TypeError) as exc:
            raise EntradaInvalida(
                f"{Path(pubkey_path).name} no es una clave pública PEM"
            ) from exc
        # Una sola escritura del archivo de la clave: la canónica. Esta
        # biblioteca ignora caracteres sueltos dentro del PEM y OpenSSL no; sin
        # este control el mismo archivo verificaba aquí y no con la receta.
        # Se admiten el salto de línea de Windows y que falte el salto final.
        pem = pem.replace(b"\r", b"")
        if not pem.endswith(b"\n"):
            pem += b"\n"
        if pem != pubkey.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ):
            raise EntradaInvalida(
                f"{Path(pubkey_path).name} no es una clave pública PEM en su forma canónica"
            )
    except EntradaInvalida as exc:
        print(f"FALLA: {exc}")
        print("RESULTADO: NO SE PUDO EVALUAR")
        return NO_EVALUABLE

    print("== Verificación de commitment Diké (tercero, sin acceso al proyecto) ==")
    print(f"  commitment : {Path(commitment_path).name}")
    print(f"  firma      : {Path(sig_path).name}")
    print(f"  pubkey     : {Path(pubkey_path).name}")
    print()

    if not isinstance(pubkey, Ed25519PublicKey):
        return _no_verificado("FALLA: la pubkey no es Ed25519")

    # ── 1. El sobre declara exactamente el contrato V2 ──
    # Los tres campos se comparan con valores fijos: como van separados por
    # «:» dentro de lo firmado, un campo libre permitiría correr el reparto.
    print("1. Contrato declarado por el sobre")
    print(f"   schema_version: {sobre['schema_version']}")
    print(f"   role          : {sobre['role']}")
    print(f"   algorithm     : {sobre['algorithm']}")
    if sobre["schema_version"] != SCHEMA:
        return _no_verificado(
            f"FALLA: schema_version={sobre['schema_version']!r} (se esperaba {SCHEMA})",
            "       Las firmas V1 no ligaban el rol; este verificador no las acepta.",
        )
    if sobre["role"] != ROL:
        return _no_verificado(f"FALLA: role={sobre['role']!r} (se esperaba {ROL})")
    if sobre["algorithm"] != ALGORITMO:
        return _no_verificado(
            f"FALLA: algorithm={sobre['algorithm']!r} (se esperaba {ALGORITMO})"
        )
    print("   => OK")
    print()

    # ── 2. El commitment es el que se firmó ──
    print("2. Hash canónico del commitment")
    print(f"   calculado : {c_hash}")
    print(f"   firmado   : {sobre['commitment_hash']}")
    if c_hash != sobre["commitment_hash"]:
        return _no_verificado(
            "   => NO COINCIDE: el commitment cambió después de firmarse",
            "      (o la firma no es de este commitment)",
        )
    print("   => OK")
    print()

    # ── 3. La pubkey presentada es la que dice el sobre ──
    print("3. Identidad de la llave (key_id = 16 hex del SHA-256 de la pubkey en bruto)")
    raw_pub = pubkey.public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    key_id_calc = hashlib.sha256(raw_pub).hexdigest()[:16]
    print(f"   calculado  : {key_id_calc}")
    print(f"   en el sobre: {sobre['key_id']}")
    if key_id_calc != sobre["key_id"]:
        return _no_verificado("   => NO COINCIDE: la firma no fue hecha con esta llave")
    print("   => OK")
    print()

    # ── 4. La firma ──
    print("4. Firma Ed25519 sobre sha256(role:algorithm:schema_version:hash), en hex")
    firmado = hashlib.sha256(
        f"{ROL}:{ALGORITMO}:{SCHEMA}:{c_hash}".encode("utf-8")
    ).hexdigest().encode("utf-8")
    try:
        pubkey.verify(firma, firmado)
    except InvalidSignature:
        return _no_verificado("   => INVÁLIDA")
    print("   => VÁLIDA")

    print()
    print("RESULTADO: VERIFICADO")
    print()
    print("Lo que esto demuestra:")
    print("  · el commitment no fue alterado después de firmarse")
    print(f"  · la firma fue hecha con la llave cuyo key_id es {key_id_calc}.")
    print("    Compara ese key_id con el publicado en KEYS.md: una pubkey que")
    print("    llega junto al commitment no prueba nada por sí sola.")
    print("  · la firma se emitió para el rol content-integrity y no otro")
    print()
    print("Lo que NO demuestra (y es importante decirlo):")
    print("  · que la fecha tenga valor legal en Chile. La Ley 19.799 art. 5º")
    print("    Nº 2 exige un fechado electrónico de PRESTADOR ACREDITADO;")
    print("    esto no lo es y no pretende serlo.")
    print("  · quién es el titular de la llave: la firma prueba QUE se firmó,")
    print("    no QUIÉN firmó.")
    print("  · que las normas citadas fundamenten lo que el escrito afirma.")
    print("    Diké NO verifica eso: solo que cada norma existe en su corpus")
    print("    local, que su texto es citable y que está vigente a la fecha")
    print("    consultada. La corrección sustantiva es juicio del abogado.")
    return VERIFICADO


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python3 verificar_tercero.py <commitment.json> <commitment.sig.json> <pubkey.pem>")
        print()
        print((__doc__ or "").strip())
        sys.exit(NO_EVALUABLE)
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
