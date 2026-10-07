#!/usr/bin/env python3
"""Batería de mutación del commitment firmado. No toca el árbol real.

Por qué existe: el 2026-10-05 la suite focal estaba en verde (29 passed) y
9 de 14 mutantes sobrevivían. Los tests pasaban, pero no fallaban si se rompía
lo que decían proteger. Esta batería rompe cada garantía, una a la vez, sobre
una COPIA de `lexo_cli/` y `docs/hackathon/`, y exige que algún test lo note.

    python scripts/hackathon/mutar_commitment.py            # todo
    python scripts/hackathon/mutar_commitment.py --solo M01 T05

Sale 0 si no sobrevive ninguno; 1 si sobrevive alguno; 2 si el arnés está mal
(la copia sin mutar no pasa, o un ancla ya no aparece exactamente una vez).

M01–M14 son las catorce propiedades de la reauditoría
(`docs/reviews/evidencia/reauditoria_opus55_20261005/mutar.py`), con las anclas
puestas al día. M15 en adelante cubren el endurecimiento de la remediación 2.
T01–T09 mutan el verificador de tercero, que antes no tenía ningún test.

R01 en adelante son de la reauditoría 2 (2026-10-06): los diez huecos de test
que encontró (H5) y cada control que se agregó por sus hallazgos H1 a H4 y
H11. K01–K10 mutan la receta de `jq` + OpenSSL de KEYS.md, que la batería
anterior no tocaba.

Dos cambios respecto de la batería anterior, para que nadie compare cifras sin
saberlo. M14 rompía «firmar respeta el rol pedido» y M16, «firmar solo acepta
roles de la lista». Desde H11 `firmar_commitment` firma un solo rol y lo dice
una sola guardia: M14 pasó a romperla y M16 se retiró, porque era la misma
mutación. Y lo que NO está: el control de bytes nulos de la
receta y su `grep -a` solo cambian el resultado con un `jq` anterior a 1.8
(con el de esta máquina son mutantes equivalentes; se probaron a mano con
jq 1.5, 1.6 y 1.7.1), y el exportador, que en la copia de trabajo es un enlace.
"""
from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Importar al módulo hermano sin dejar `scripts/hackathon/__pycache__/` en el perfil.
_escribia_pyc, sys.dont_write_bytecode = sys.dont_write_bytecode, True
try:
    import copia_de_trabajo  # noqa: E402
finally:
    sys.dont_write_bytecode = _escribia_pyc

REPO = copia_de_trabajo.REPO
CS = "lexo_cli/content_signing.py"
CM = "lexo_cli/commitment.py"
CC = "lexo_cli/commands/constancia.py"
VT = "docs/hackathon/verificar_tercero.py"
KEYS = "docs/hackathon/KEYS.md"

TESTS = [
    "lexo_cli/tests/test_content_signing.py",
    "lexo_cli/tests/test_commitment_constancia.py",
    "lexo_cli/tests/test_verificar_tercero.py",
    "lexo_cli/tests/test_keys_md_ejecutable.py",
    "lexo_cli/tests/test_constancia_emit_commitment.py",
]

_BYTES = 'sobre.role + ":" + sobre.algorithm + ":" + sobre.schema_version + ":" + sobre.commitment_hash'

# (id, archivo, texto original, texto mutado, qué propiedad rompe)
MUTANTES: list[tuple[str, str, str, str, str]] = [
    # ── Las catorce de la reauditoría ──
    ("M01", CS, _BYTES,
     'sobre.algorithm + ":" + sobre.schema_version + ":" + sobre.commitment_hash',
     "el ROL deja de estar firmado (queda solo la validación de campo)"),
    ("M02", CS,
     '    if sobre.role != role_esperado:\n'
     '        raise ContentSigningError(f"role incompatible: {sobre.role!r} != {role_esperado!r}")\n',
     '',
     "se quita la validación de campo del rol (queda solo la criptografía)"),
    ("M03", CS, _BYTES,
     'sobre.role + ":" + sobre.algorithm + ":" + sobre.commitment_hash',
     "schema_version deja de estar firmado"),
    ("M04", CS, _BYTES,
     'sobre.role + ":" + sobre.schema_version + ":" + sobre.commitment_hash',
     "algorithm deja de estar firmado"),
    ("M05", CS,
     '    if dups:\n        raise DuplicateKeyError(f"claves JSON duplicadas: {dups}")\n',
     '',
     "reject_duplicate_keys no rechaza nada"),
    ("M06", CS,
     'fd = os.open(str(p), flags, 0o600)',
     'fd = os.open(str(p), flags, 0o644)',
     "la llave se CREA 0644 y recién después se corrige a 0600"),
    ("M07", CS,
     '        # V1 firmaba solo el hash crudo: data = bytes.fromhex(c_hash)\n'
     '        public_key.verify(bytes.fromhex(sobre.signature_hex), bytes.fromhex(c_hash))\n',
     '        pass\n',
     "la vía legacy no verifica ninguna firma (devuelve True siempre)"),
    ("M08", CS,
     '    if sobre.schema_version != _SCHEMA_V1:\n'
     '        raise ContentSigningError(\n'
     '            f"no es firma V1 legacy: {sobre.schema_version!r}"\n'
     '        )\n',
     '',
     "la vía legacy acepta sobres de cualquier esquema"),
    ("M09", CM,
     '    for clave in _CLAVES_HUELLA:\n        publico.pop(clave, None)\n',
     '',
     "compromiso_publico() no omite la huella del documento"),
    ("M10", CM,
     '    if publico:\n        payload = compromiso_publico(commitment)\n',
     '    if False:\n        payload = compromiso_publico(commitment)\n',
     "escribir_commitment ignora publico=True"),
    ("M11", CS,
     'flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)',
     'flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC',
     "generar_content_key sobrescribe llaves existentes"),
    ("M12", CS,
     '    except InvalidSignature:\n        return False\n    return True\n\n\ndef verificar_archivos',
     '    except Exception:\n        return False\n    return True\n\n\ndef verificar_archivos',
     "verificar_commitment traga excepciones anchas"),
    ("M13", CS,
     '    if sobre.commitment_hash != c_hash:\n'
     '        raise CommitmentAlteradoError(\n'
     '            f"el commitment cambió tras la firma: firmado {sobre.commitment_hash[:16]}…, "\n'
     '            f"ahora {c_hash[:16]}…"\n'
     '        )\n'
     '    if sobre.key_id != derive_key_id(public_key):',
     '    if sobre.key_id != derive_key_id(public_key):',
     "V2 no compara el hash del commitment con el del sobre"),
    ("M14", CS,
     '    if role != _ROL:\n        # Reauditoría 2 (H11)',
     '    if False:\n        # Reauditoría 2 (H11)',
     "firmar_commitment firma con el rol que le pidan: «authorization» o uno inventado"),

    # ── Endurecimiento de la remediación 2 ──
    ("M15", CS,
     '    if sobre.algorithm != _ALGORITMO:\n'
     '        raise ContentSigningError(\n'
     '            f"algorithm inesperado: {sobre.algorithm!r} (esperado {_ALGORITMO!r})"\n'
     '        )\n',
     '',
     "verificar_commitment no valida algorithm (ambigüedad del «:»)"),
    ("M17", CS,
     '        faltan = [k for k in _CAMPOS_SOBRE if not isinstance(d.get(k), str)]',
     '        d = {"schema_version": CONTENT_SIGNATURE_SCHEMA_VERSION, "role": _ROL, "algorithm": _ALGORITMO, **d}\n'
     '        faltan = [k for k in _CAMPOS_SOBRE if not isinstance(d.get(k), str)]',
     "from_dict vuelve a rellenar schema_version, role y algorithm"),
    ("M18", CS,
     ' | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)',
     ' | os.O_EXCL',
     "la creación de la llave pierde O_NOFOLLOW"),
    ("M19", CS,
     '        os.chmod(nuevo, 0o700)',
     '        os.chmod(nuevo, 0o755)',
     "los directorios de la llave se crean 0755"),
    ("M20", CM,
     'destino: str | Path, *, publico: bool = True) -> str:',
     'destino: str | Path, *, publico: bool = False) -> str:',
     "escribir_commitment vuelve a publicar la huella por defecto"),
    ("M21", CM,
     '    bloqueantes = _pii_bloqueante(auditar_pii(_cadenas(commitment, "commitment")))\n    if bloqueantes:',
     '    bloqueantes = {}\n    if bloqueantes:',
     "lo que se publica deja de auditarse por PII"),
    ("M22", CM,
     '        if k not in permitidas:\n            raise CommitmentPIIError(\n'
     '                f"El commitment contiene un campo fuera del esquema',
     '        if False:\n            raise CommitmentPIIError(\n'
     '                f"El commitment contiene un campo fuera del esquema',
     "la lista blanca de claves se desactiva (queda la lista negra)"),
    ("M23", CM,
     '    if verificadas != len(normas):',
     '    if False:',
     "citas_verificadas ya no tiene que cuadrar con las normas"),
    ("M24", CS,
     '    validar_publicable(commitment, permitir_huella=permitir_huella)\n    if tiene_huella',
     '    if tiene_huella',
     "firmar_commitment firma sin validar que sea publicable"),
    ("M25", CS,
     '    if misma:\n        raise ContentSigningError(\n            "ROLE_KEY_REUSE',
     '    if False:\n        raise ContentSigningError(\n            "ROLE_KEY_REUSE',
     "se puede firmar commitments con el archivo de la llave de autorización"),
    ("M26", CS,
     '    if sobre.key_id != derive_key_id(public_key):\n        return False\n',
     '',
     "verificar_commitment no compara el key_id con la pubkey"),
    ("M27", CS,
     '    data = _loads_estricto(text)\n    if not isinstance(data, dict):',
     '    data = json.loads(text)\n    if not isinstance(data, dict):',
     "el lector estricto de archivos acepta claves duplicadas"),
    ("M28", CM,
     '        if declarado is not None and declarado != valor:',
     '        if False:',
     "el constructor acepta conteos que no cuadran con los detalles"),
    ("M29", CM,
     '        if norma.get("estado") != "VERIFICADA":',
     '        if False:',
     "una norma no verificada puede ir en el commitment"),
    ("M30", CM,
     '    con_huella = sorted(k for k in commitment if k in _CLAVES_HUELLA)\n'
     '    if con_huella and not permitir_huella:',
     '    con_huella = sorted(k for k in commitment if k in _CLAVES_HUELLA)\n'
     '    permitidas = permitidas | _CLAVES_HUELLA\n'
     '    if False:',
     "la huella del escrito se publica y se firma sin opt-in"),

    # ── Paridad entre verificadores (entradas raras) ──
    ("M31", CS,
     '            parse_float=_numero_no_entero,\n            parse_int=_entero_canonico,\n',
     '',
     "el lector estricto acepta 2e0, 2.0 y -0 (jq y Python los normalizan distinto)"),
    ("M32", CM,
     '        if "\\x7f" in cadena:',
     '        if False:',
     "se firma un commitment con el carácter DEL (la receta sin Python no lo verificaría)"),
    ("M33", CS,
     '    if len(firma_hex) != 128 or not set(firma_hex) <= _HEX:',
     '    if False:',
     "una firma con espacios o de otro largo verifica en la API"),
    ("M34", CS,
     '        text = Path(path).read_text(encoding="utf-8-sig")',
     '        text = Path(path).read_text(encoding="utf-8")',
     "la API rechaza un archivo con BOM que los otros verificadores aceptan"),

    # ── `dike constancia --emit-commitment` ──
    ("C01", CC,
     '    if not publico["normas_verificadas"]:\n        output_error(',
     '    if False:\n        output_error(',
     "el CLI emite un commitment aunque ninguna cita quedó verificada"),
    ("C02", CC,
     '    ya = [p.name for p in _archivos_commitment(directorio, firmar=True) if p.exists() or p.is_symlink()]',
     '    ya = [p.name for p in _archivos_commitment(directorio, firmar=firmar) if p.exists() or p.is_symlink()]',
     "el CLI deja un commitment nuevo junto a una firma vieja"),
    ("C03", CC,
     '        for ruta_archivo in escritos:\n            ruta_archivo.unlink(missing_ok=True)\n',
     '',
     "el CLI deja archivos a medias cuando falla la emisión"),
    ("C04", CC,
     '    if directorio is not None and not _emitir_commitment(result, cfg, directorio, firmar=firmar):\n'
     '        return EXIT_COMMITMENT_NO_EMITIDO\n',
     '    if directorio is not None:\n'
     '        _emitir_commitment(result, cfg, directorio, firmar=firmar)\n',
     "el CLI sale como si hubiera emitido cuando no emitió"),
    ("C05", CC,
     '            if cs.verificar_archivos(directorio / COMMITMENT_FILE, directorio / SIGNATURE_FILE, pubkey) is not True:',
     '            if False:',
     "el CLI no verifica lo que dejó en disco"),
    ("C06", CC,
     '        publico = compromiso_publico(commitment_de_constancia(result))',
     '        publico = commitment_de_constancia(result, documento=__file__)',
     "el CLI calcula y publica la huella de un archivo"),

    # ── El verificador de tercero ──
    ("T01", VT,
     '    if repetidas:\n        raise EntradaInvalida(f"claves JSON duplicadas: {repetidas}")\n',
     '',
     "el verificador de tercero acepta claves duplicadas"),
    ("T02", VT, '    if sobre["role"] != ROL:', '    if False:',
     "el verificador de tercero no mira el rol"),
    ("T03", VT, '    if sobre["algorithm"] != ALGORITMO:', '    if False:',
     "el verificador de tercero no mira algorithm"),
    ("T04", VT, '    if sobre["schema_version"] != SCHEMA:', '    if False:',
     "el verificador de tercero acepta cualquier schema_version"),
    ("T05", VT, '    if c_hash != sobre["commitment_hash"]:', '    if False:',
     "el verificador de tercero no compara el hash"),
    ("T06", VT, '    if key_id_calc != sobre["key_id"]:', '    if False:',
     "el verificador de tercero no compara el key_id"),
    ("T07", VT, '        pubkey.verify(firma, firmado)\n', '        pass\n',
     "el verificador de tercero no verifica la firma"),
    ("T08", VT,
     'f"{ROL}:{ALGORITMO}:{SCHEMA}:{c_hash}".encode("utf-8")',
     'f"{ALGORITMO}:{SCHEMA}:{c_hash}".encode("utf-8")',
     "el verificador de tercero deja el rol fuera de los bytes firmados"),
    ("T10", VT,
     '            parse_float=_numero_no_entero,\n            parse_int=_entero_canonico,\n',
     '',
     "el verificador de tercero acepta 2e0, 2.0 y -0"),
    ("T11", VT,
     '        if len(firma_hex) != 128 or not set(firma_hex) <= set("0123456789abcdef"):',
     '        if False:',
     "el verificador de tercero acepta una firma con espacios"),
    ("T12", VT,
     'read_text(encoding="utf-8-sig")  # tolera un BOM inicial',
     'read_text(encoding="utf-8")',
     "el verificador de tercero rechaza un BOM que la receta acepta"),
    ("T09", VT,
     '        if faltan:\n            raise EntradaInvalida(f"sobre incompleto, faltan o no son cadenas: {faltan}")\n',
     '',
     "el verificador de tercero no exige el sobre completo"),

    # ═══ Reauditoría 2 (2026-10-06) ═══

    # ── H2: el sobre es cerrado y la firma tiene una sola escritura ──
    ("R01", CS,
     '        if sobran:\n            raise ContentSigningError(\n                f"el sobre trae campos que la firma no cubre: {sobran}"\n            )\n',
     '',
     "la biblioteca acepta un sobre con campos que nadie firmó"),
    ("R02", CS, '_HEX = frozenset("0123456789abcdef")', '_HEX = frozenset("0123456789abcdefABCDEF")',
     "la biblioteca acepta la firma en mayúsculas"),
    ("R03", VT,
     '        if sobran:\n            raise EntradaInvalida(f"el sobre trae campos que la firma no cubre: {sobran}")\n',
     '',
     "el verificador de tercero acepta un sobre con campos que nadie firmó"),
    ("R04", VT,
     'if len(firma_hex) != 128 or not set(firma_hex) <= set("0123456789abcdef"):',
     'if len(firma_hex) != 128 or not set(firma_hex) <= set("0123456789abcdefABCDEF"):',
     "el verificador de tercero acepta la firma en mayúsculas"),

    # ── Paridad: enteros de más de 15 dígitos y el archivo de la clave ──
    ("R05", CS,
     '    if len(literal.lstrip("-")) > 15:\n        raise ContentSigningError("número no admitido: un commitment solo lleva enteros de hasta 15 dígitos")\n',
     '',
     "la biblioteca lee enteros que un jq anterior a 1.7 redondea"),
    ("R06", VT,
     '    if len(literal.lstrip("-")) > 15:\n        raise EntradaInvalida("número no admitido: un commitment solo lleva enteros de hasta 15 dígitos")\n',
     '',
     "el verificador de tercero lee enteros que un jq anterior a 1.7 redondea"),
    ("R07", CS,
     '    if pem != key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo):',
     '    if False:',
     "la biblioteca lee una clave pública que no está en su forma canónica"),
    ("R08", CS,
     '    if not isinstance(key, Ed25519PublicKey):\n        raise ContentSigningError(f"se esperaba una clave pública Ed25519, hay {type(key).__name__}")\n',
     '',
     "leer_clave_publica devuelve una clave que no es Ed25519"),
    ("R09", VT,
     '        if pem != pubkey.public_bytes(\n            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo\n        ):',
     '        if False:',
     "el verificador de tercero lee una clave pública que no está en su forma canónica"),

    # ── H4: la puerta exige ──
    ("R10", CM,
     '    for campo in _OBLIGATORIOS:\n        if commitment.get(campo) in (None, ""):',
     '    for campo in ():\n        if commitment.get(campo) in (None, ""):',
     "se firma un commitment al que le falta un campo obligatorio"),
    ("R11", CM, '    if commitment["schema_version"] != COMMITMENT_SCHEMA_VERSION:', '    if False:',
     "se firma un commitment con un schema_version ajeno"),
    ("R12", CM, '    if not _PACK_HASH.fullmatch(commitment["pack_hash"]):', '    if False:',
     "se firma un commitment cuyo pack_hash dice «sin-corpus»"),
    ("R13", CM, '_PACK_HASH = re.compile(r"[0-9a-f]{16}")', '_PACK_HASH = re.compile(r"[0-9a-fA-F]{16}")',
     "el pack_hash admite mayúsculas"),
    ("R14", CM, '    if not _PACK_HASH.fullmatch(commitment["pack_hash"]):', '    if not _PACK_HASH.match(commitment["pack_hash"]):',
     "el pack_hash admite cualquier cosa después de 16 hexadecimales"),
    ("R15", CM, '    if not _FECHA.fullmatch(commitment["as_of"]):', '    if False:',
     "as_of admite cualquier texto"),
    ("R16", CM, '    if not _FECHA_HORA_UTC.fullmatch(commitment["fecha_constancia"]):', '    if False:',
     "fecha_constancia admite cualquier texto"),
    ("R17", CM,
     '        if commitment[campo] < 0:\n            raise CommitmentIncoherenteError(f"{campo} no puede ser negativo")\n',
     '',
     "se firma un commitment con un conteo negativo"),
    ("R18", CM,
     '        if commitment[campo] > _CONTEO_MAXIMO:\n            raise CommitmentIncoherenteError(f"{campo} no cabe en 15 dígitos")\n',
     '',
     "se firma un conteo que la receta sin Python no podría verificar con un jq antiguo"),
    ("R19", CM, '    if not advertencias or not all(advertencias):', '    if False:',
     "se firma un commitment sin advertencias"),
    ("R20", CM,
     '        for campo in _OBLIGATORIOS_NORMA:\n            if norma.get(campo) in (None, ""):',
     '        for campo in ():\n            if norma.get(campo) in (None, ""):',
     "una norma puede ir sin gid, sin hash del texto o sin fuente"),
    ("R21", CM, '        if not _TEXTO_HASH.fullmatch(norma["texto_hash"]):', '        if False:',
     "el texto_hash de una norma admite cualquier cadena"),
    ("R22", CM, '    if total != verificadas + fallidas:', '    if False:',
     "total_citas ya no tiene que ser verificadas + fallidas (X06)"),
    ("R23", CM,
     '            if valor is not None and not isinstance(valor, str):\n                raise CommitmentIncoherenteError(\n                    f"normas_verificadas[{i}].{campo} debe ser una cadena"\n                )\n',
     '            pass\n',
     "los campos de una norma admiten cualquier tipo (X05)"),
    ("R24", CM,
     '        validar_publicable(commitment, permitir_huella=True)\n        payload = commitment',
     '        payload = commitment',
     "escribir_commitment(publico=False) no valida (X14)"),

    # ── H5: huecos de test en la llave y los roles ──
    ("R25", CS,
     '    except BaseException:\n        p.unlink(missing_ok=True)\n        raise\n',
     '    except BaseException:\n        raise\n',
     "una llave a medio escribir no se borra (Y04)"),
    ("R26", CS,
     '    if not isinstance(key, Ed25519PrivateKey):\n        raise ContentSigningError(f"se esperaba Ed25519, hay {type(key).__name__}")\n',
     '',
     "no se comprueba que la llave privada sea Ed25519 (Y06)"),
    ("R27", CS,
     '    if role_esperado not in ROLES_VALIDOS:\n        raise ContentSigningError(f"rol esperado no admitido: {role_esperado!r}")\n',
     '',
     "verificar acepta cualquier rol esperado (Y10)"),
    ("R28", CS, '            os.mkdir(nuevo, 0o700)', '            os.mkdir(nuevo)',
     "el directorio de la llave nace 0755 y se corrige después (Y02)"),

    # ── H3 y H5: la emisión del CLI ──
    ("R29", CC,
     '                escritos.append(ruta_archivo)\n                f.write(datos)\n',
     '                f.write(datos)\n            escritos.append(ruta_archivo)\n',
     "si la escritura se corta, el archivo que quedó a medias no se borra (H3)"),
    ("R30", CC,
     '    except BaseException as exc:\n        # BaseException: un Ctrl-C',
     '    except (OSError, ValueError, cs.ContentSigningError) as exc:\n        # BaseException: un Ctrl-C',
     "un Ctrl-C a mitad de la escritura deja archivos (H3)"),
    ("R31", CC, 'if p.exists() or p.is_symlink()]', 'if p.exists()]',
     "la comprobación previa no ve un enlace simbólico colgante (Z02)"),
    ("R32", CC, '            with open(ruta_archivo, "xb") as f:', '            with open(ruta_archivo, "wb") as f:',
     "el CLI sobrescribe y sigue enlaces al escribir (Z03)"),
    ("R33", CC,
     '        if creado and directorio.is_dir() and not any(directorio.iterdir()):\n            directorio.rmdir()\n',
     '',
     "tras un fallo queda la carpeta vacía que el CLI creó (Z07)"),
    ("R34", CC, '    if len(corpora) > 1:', '    if False:',
     "con dos corpus el commitment nombra solo el primero"),
    ("R35", CC,
     '    except Exception:\n        return "sin-corpus"\n    if not corpora:',
     '    except Exception:\n        return "0" * 16\n    if not corpora:',
     "si el manifest no se puede leer, el CLI inventa un pack_hash"),
    ("R36", CC,
     '            pubkey = cs.leer_clave_publica(directorio / PUBKEY_FILE)\n            if cs.verificar_archivos(directorio / COMMITMENT_FILE, directorio / SIGNATURE_FILE, pubkey) is not True:\n                raise cs.ContentSigningError("lo escrito no verifica contra su propia firma")\n',
     '            pass\n',
     "el CLI no lee ni verifica lo que dejó en disco"),

    # ── H5: el verificador de tercero ante lo que no es JSON ──
    ("R37", VT, '            parse_constant=_constante_no_json,\n', '',
     "el verificador de tercero deja de tratar NaN como entrada inválida (W03)"),
    ("R38", VT,
     '        try:\n            c_hash = hash_canonico(commitment)\n        except UnicodeEncodeError as exc:\n            raise EntradaInvalida("el commitment trae texto que no es Unicode válido") from exc\n',
     '        c_hash = hash_canonico(commitment)\n',
     "un surrogate suelto hace caer al verificador de tercero con un traceback (W05)"),

    # ── La receta de KEYS.md ──
    ("K01", KEYS,
     'jq -e --arg k "$KID" \'.key_id==$k\' "$S" >/dev/null || { echo "FALLA: la firma no es de esta clave"; exit 1; }\n',
     '',
     "la receta no compara el key_id"),
    ("K02", KEYS,
     '[ "$N" = 0 ] || { echo "FALLA: el commitment trae un número que no es un entero simple"; exit 2; }\n',
     '',
     "la receta no rechaza 2e0, 2.0, -0, 02 ni +2"),
    ("K03", KEYS,
     'jq -e \'.schema_version=="dike-content-signature-v2" and .role=="content-integrity" and .algorithm=="ed25519"\' "$S" >/dev/null \\\n'
     '  || { echo "FALLA: schema_version, role o algorithm inesperados"; exit 1; }\n',
     '',
     "la receta no mira el contrato que declara el sobre"),
    ("K04", KEYS,
     '    || { echo "FALLA: claves duplicadas en $f"; exit 2; }\n',
     '    || true\n',
     "la receta no rechaza claves duplicadas"),
    ("K05", KEYS,
     '  || { echo "FALLA: el sobre no tiene exactamente los seis campos con su formato"; exit 2; }\n',
     '  || true\n',
     "la receta no exige los seis campos del sobre ni su forma"),
    ("K06", KEYS,
     '    || { echo "FALLA: $f no es un único objeto JSON"; exit 2; }\n',
     '    || true\n',
     "la receta acepta un archivo con dos documentos"),
    ("K07", KEYS,
     '  || { echo "FALLA: $K no es una clave pública PEM en su forma canónica"; exit 2; }\n',
     '  || true\n',
     "la receta acepta una clave pública con texto antes o con otra clave detrás"),
    ("K08", KEYS, "-?[1-9][0-9]{0,14}|true|false|null", "-?[1-9][0-9]*|true|false|null",
     "la receta acepta enteros de más de 15 dígitos"),
    ("K09", KEYS,
     'jq -e --arg h "$H" \'.commitment_hash==$h\' "$S" >/dev/null || { echo "FALLA: el hash NO coincide"; exit 1; }\n',
     '',
     "la receta no compara el hash del commitment con el del sobre"),
    ("K10", KEYS,
     'openssl pkeyutl -verify -pubin -inkey "$K" -rawin -in "$T/firmado.txt" -sigfile "$T/firma.bin"\n',
     'echo "Signature Verified Successfully"\n',
     "la receta no verifica ninguna firma"),
]


def _correr(raiz: Path, tmp: Path, tests: list[str]) -> tuple[int, str, str]:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", f"--basetemp={tmp / 'bt'}",
         "-q", "-x", "--no-header", *tests],
        cwd=raiz, capture_output=True, text=True, env=copia_de_trabajo.entorno(raiz, tmp),
    )
    resumen = [l for l in r.stdout.splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    primero = [l for l in r.stdout.splitlines() if l.startswith(("FAILED", "ERROR"))]
    return (
        r.returncode,
        resumen[-1].strip() if resumen else (r.stdout + r.stderr)[-300:].strip(),
        primero[0].split(" - ")[0] if primero else "",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--solo", nargs="*", default=None, help="ids a correr (por defecto, todos)")
    ap.add_argument("--tmp", default=None, help="carpeta de trabajo (por defecto, una temporal)")
    ap.add_argument("--anclas", action="store_true",
                    help="solo comprueba que cada ancla aparece una vez en el árbol real; no corre nada")
    args = ap.parse_args()
    sys.dont_write_bytecode = True  # ni un .pyc nuevo en el perfil por correr este guion

    if args.anclas:
        veces = [(m[0], (REPO / m[1]).read_text(encoding="utf-8").count(m[2])) for m in MUTANTES]
        malas = [(mid, n) for mid, n in veces if n != 1]
        ids = [m[0] for m in MUTANTES]
        repetidos = sorted({i for i in ids if ids.count(i) > 1})
        print(f"{len(MUTANTES)} mutantes; anclas que no aparecen exactamente una vez: {malas}; ids repetidos: {repetidos}")
        return 2 if malas or repetidos else 0

    tmp = Path(args.tmp) if args.tmp else Path(tempfile.mkdtemp(prefix="mutar-commitment-"))
    raiz = tmp / "root"
    if raiz.exists():
        shutil.rmtree(raiz)
    copia_de_trabajo.crear(raiz)
    tests = [t for t in TESTS if (REPO / t).is_file()]
    archivos = sorted({m[1] for m in MUTANTES})

    def restaurar() -> None:
        for f in archivos:
            shutil.copyfile(REPO / f, raiz / f)

    restaurar()
    rc, res, _ = _correr(raiz, tmp, tests)
    print(f"BASE (copia sin mutar)  exit={rc}  {res}")
    print(f"     tests: {', '.join(Path(t).name for t in tests)}")
    if rc != 0:
        print("la copia sin mutar no pasa: el arnés está mal")
        return 2

    elegidos = [m for m in MUTANTES if args.solo is None or m[0] in args.solo]
    vivos: list[str] = []
    for mid, f, viejo, nuevo, desc in elegidos:
        restaurar()
        src = (raiz / f).read_text(encoding="utf-8")
        if src.count(viejo) != 1:
            print(f"{mid}: el ancla aparece {src.count(viejo)} veces en {f}; la batería está desfasada")
            return 2
        mutado = src.replace(viejo, nuevo)
        if f.endswith(".py"):  # KEYS.md no es Python
            try:
                ast.parse(mutado)
            except SyntaxError as exc:
                print(f"{mid}: la mutación no compila ({exc})")
                return 2
        (raiz / f).write_text(mutado, encoding="utf-8")
        rc, res, primero = _correr(raiz, tmp, tests)
        if rc == 0:
            vivos.append(mid)
        estado = "SOBREVIVE (ningún test lo nota)" if rc == 0 else "muere"
        print(f"{mid} {estado:<32} | {desc}")
        print(f"      -> exit={rc} {res} {('| ' + primero) if primero else ''}")
    restaurar()

    originales = [m[0] for m in elegidos if m[0] <= "M14" and m[0].startswith("M")]
    vivos_originales = [v for v in vivos if v in originales]
    print()
    print(f"MUTANTES VIVOS: {len(vivos)}/{len(elegidos)} -> {vivos}")
    print(f"  de los 14 de la reauditoría (M01–M14): {len(vivos_originales)}/{len(originales)} -> {vivos_originales}")
    intacto = all((raiz / f).read_bytes() == (REPO / f).read_bytes() for f in archivos)
    print(f"copia restaurada idéntica al repo: {intacto}")
    return 1 if vivos else 0


if __name__ == "__main__":
    sys.exit(main())
