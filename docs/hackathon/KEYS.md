# Claves de verificación — Diké

## English Summary (for Jury & Third-Party Verifiers)

This folder lets anyone verify — offline and without Diké's code — that a
signed Diké *commitment* has not been altered after signing. It contains only a
**public** key (`content-signing-key.pub`, `key_id` `3c7b3fde075efbe3`) and no
private keys. All CLI output, JSON field names, and the detailed specification
below are in Spanish.

- **What a commitment is:** `dike constancia` checks every statutory citation
  in a brief against a local, hash-identified snapshot of Chilean law derived
  from the Biblioteca del Congreso Nacional (BCN). In the included example
  (`escrito_demo.md`, 6 citations), Diké verifies 4 citations (`citas_verificadas: 4`)
  and refuses to certify 2 (`citas_fallidas: 2`: one ambiguous citation without
  a statute name, one non-existent article). Only the 4 verified provisions
  enter `commitment.json`; refused citations and brief prose stay out.
- **What this signature proves:**
  1. `commitment.json` was not modified after signing (canonical JSON SHA-256
     equals `commitment_hash`).
  2. The signature was produced with the Ed25519 key whose public key is
     published here (`key_id` `3c7b3fde075efbe3`).
  3. The signature is bound to the `content-integrity` role and contract
     `dike-content-signature-v2` (signing the 64 ASCII hex characters of
     `sha256("content-integrity:ed25519:dike-content-signature-v2:" + commitment_hash)`).
- **What this signature does NOT prove:**
  - *No accredited legal timestamp in Chile:* Under Chilean Law 19.799 (Art. 5
    No. 2), a date has legal faith only when issued by an accredited timestamp
    provider (*prestador acreditado*). This signature is not an advanced
    electronic signature or accredited timestamp, and a blockchain anchor is
    not one either; dates reflect the signing machine's clock.
  - *No certified signer identity:* It proves *which key* signed, not *who*
    holds it (no certificate from an accredited certification provider under
    Law 19.799 Art. 2(b) and Art. 11).
  - *No substantive legal validation:* Diké checks that each cited article
    exists in the local corpus snapshot (`pack_hash` `af1422d66d1e6eee`), has
    citable text, and is recorded as in force on the reference date. It does
    **not** verify that the norm substantively supports the brief's argument.
  - *Not live official law:* The corpus is a dated local BCN snapshot named by
    `pack_hash`.
- **Two independent verification paths (run the executable blocks in
  *Verificar en dos minutos* below from this folder):**
  - **Path 1 (*Camino 1: Python*):** runs `verificar_tercero.py` (uses only
    Python stdlib + `cryptography`; imports nothing from Diké). Outputs
    `RESULTADO: VERIFICADO` (exit `0`).
  - **Path 2 (*Camino 2: sin Python, con jq, coreutils y OpenSSL*):** pure
    Linux shell recipe using `jq`, GNU coreutils (`sha256sum`, `basenc`), and
    OpenSSL 3 (`openssl pkeyutl -verify`). Outputs
    `Signature Verified Successfully` (exit `0`).
  - In both paths, compare the printed `key_id` against `3c7b3fde075efbe3` in
    the *Clave de contenido* table below.

---

Esta carpeta permite comprobar, sin nuestro código y sin red, que un
*commitment* de Diké no fue alterado después de firmarse. Publica una clave
**pública**. No contiene ninguna clave privada.

| Archivo | Qué es |
|---|---|
| `KEYS.md` | Este documento |
| `content-signing-key.pub` | La clave pública de contenido, la misma que se imprime más abajo |
| `verificar_tercero.py` | Verificador independiente. No importa nada de Diké |
| `commitment.json`, `commitment.sig.json` | Un commitment de ejemplo y su firma, emitidos sobre un escrito sintético de seis citas: cuatro verificadas y dos que Diké se negó a certificar |

## Verificar en dos minutos

Desde esta carpeta, por cualquiera de los dos caminos. Comprueban lo mismo y,
en cada entrada con que se los ha probado, dan el mismo veredicto: verifica o
no verifica (ver *Los dos caminos, comparados*).

### Camino 1: Python

Requiere Python 3 con el paquete `cryptography`. Probado con Python 3.10 a 3.14.

```bash
python3 verificar_tercero.py commitment.json commitment.sig.json content-signing-key.pub
```

Termina con `RESULTADO: VERIFICADO` y código de salida 0. Sale 1 si algo no
cuadra (el contrato del sobre, el hash, la llave o la firma) y 2 si no pudo
evaluar la entrada (JSON inválido o con claves duplicadas, sobre incompleto o
con un campo de más, un número que no es un entero simple de hasta 15 dígitos,
una clave pública que no está escrita en su forma canónica).

### Camino 2: sin Python, con jq, coreutils y OpenSSL

Requiere bash, `jq` 1.6 o posterior, GNU coreutils 8.31 o posterior
(`sha256sum`, `basenc`), GNU `sed` y `grep`, y OpenSSL 3. Está probado solo en
Linux: Debian 12, Ubuntu 22.04 y 24.04 y Arch, con `jq` 1.6 a 1.8 y OpenSSL 3.0
a 3.6. En macOS y Windows esas herramientas no vienen de serie: usa el camino 1.

```bash
(
set -euo pipefail
C=commitment.json; S=commitment.sig.json; K=content-signing-key.pub
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

# 0. Cada archivo es un solo objeto JSON, sin bytes nulos, y no repite ninguna clave:
#    quien lee el archivo vería la primera aparición y jq usa la última
for f in "$C" "$S"; do
  [ "$(tr -d '\000' < "$f" | wc -c)" -eq "$(wc -c < "$f")" ] || { echo "FALLA: $f trae bytes nulos"; exit 2; }
  jq -es 'length==1 and (.[0]|type=="object")' "$f" >/dev/null \
    || { echo "FALLA: $f no es un único objeto JSON"; exit 2; }
  [ "$(jq -c --stream 'select(length==2)' "$f" | sort)" = "$(jq -c 'tostream|select(length==2)' "$f" | sort)" ] \
    || { echo "FALLA: claves duplicadas en $f"; exit 2; }
done
#    Y los números, enteros simples de hasta 15 dígitos: jq leería 2e0, 04 o +4 como
#    un entero y Python no, y un jq anterior a 1.7 redondea los enteros más largos
N=$(sed -E 's/"([^"\\]|\\.)*"//g' "$C" | grep -aoE '[-+.0-9A-Za-z]+' | grep -avcE '^(0|-?[1-9][0-9]{0,14}|true|false|null)$' || true)
[ "$N" = 0 ] || { echo "FALLA: el commitment trae un número que no es un entero simple"; exit 2; }

# 1. El sobre trae exactamente seis campos, con su forma exacta, y declara este contrato.
#    Se compara dentro de jq: el shell quita los saltos de línea finales y los bytes nulos
jq -e '(keys == ["algorithm","commitment_hash","key_id","role","schema_version","signature"])
  and (.key_id|test("\\A[0-9a-f]{16}\\z")) and (.commitment_hash|test("\\A[0-9a-f]{64}\\z"))
  and (.signature|test("\\A[0-9a-f]{128}\\z"))' "$S" >/dev/null \
  || { echo "FALLA: el sobre no tiene exactamente los seis campos con su formato"; exit 2; }
jq -e '.schema_version=="dike-content-signature-v2" and .role=="content-integrity" and .algorithm=="ed25519"' "$S" >/dev/null \
  || { echo "FALLA: schema_version, role o algorithm inesperados"; exit 1; }

# 2. Hash canónico del commitment, igual al que dice el sobre
H=$(jq -cSj . "$C" | sha256sum | cut -d' ' -f1)
jq -e --arg h "$H" '.commitment_hash==$h' "$S" >/dev/null || { echo "FALLA: el hash NO coincide"; exit 1; }

# 3. La clave pública es una sola clave PEM, escrita en su forma canónica (se admite el
#    salto de línea de Windows), y es la del sobre: key_id = 16 hex del SHA-256 de la
#    clave en bruto
tr -d '\r' < "$K" | sed '$a\' > "$T/clave.pem"
openssl pkey -pubin -in "$K" -out "$T/canonica.pem" 2>/dev/null \
  && [ "$(sha256sum < "$T/clave.pem")" = "$(sha256sum < "$T/canonica.pem")" ] \
  || { echo "FALLA: $K no es una clave pública PEM en su forma canónica"; exit 2; }
KID=$(openssl pkey -pubin -in "$K" -outform DER | tail -c 32 | sha256sum | cut -c1-16)
jq -e --arg k "$KID" '.key_id==$k' "$S" >/dev/null || { echo "FALLA: la firma no es de esta clave"; exit 1; }
echo "key_id: $KID"

# 4. Bytes firmados: los 64 caracteres hex de sha256("role:algorithm:schema_version:hash")
printf '%s' "content-integrity:ed25519:dike-content-signature-v2:$H" \
  | sha256sum | cut -d' ' -f1 | tr -d '\n' > "$T/firmado.txt"

# 5. La firma, de hex a binario
jq -rj '.signature|ascii_upcase' "$S" | basenc -d --base16 > "$T/firma.bin"

# 6. Verificación Ed25519 (con archivos: -rawin no acepta tuberías)
openssl pkeyutl -verify -pubin -inkey "$K" -rawin -in "$T/firmado.txt" -sigfile "$T/firma.bin"
)
```

Termina con `Signature Verified Successfully`. Cualquier otro final es un
rechazo, y el bloque sale con un código distinto de 0. Va entre paréntesis para
que un fallo no cierre tu terminal.

En los dos caminos, **compara el `key_id` impreso con el de la sección *Clave de
contenido***. Una clave pública que llega junto al commitment no prueba nada
por sí sola: cualquiera puede firmar con su propia llave y adjuntarla.

### Los dos caminos, comparados

Los dos caminos y la biblioteca de Diké se prueban juntos sobre una batería de
entradas con una sola variable alterada: campos cambiados, agregados o
quitados; números, firmas e identificadores escritos de otra forma; saltos de
línea y bytes nulos pegados a un valor; archivos con más de un documento; la
clave pública con caracteres de más. En todas dan el mismo veredicto, y una
búsqueda con alteraciones al azar tampoco encuentra una en que discrepen.

Eso es una batería, no una demostración. Son dos lectores de JSON y dos
bibliotecas criptográficas distintas, y no hay prueba de que coincidan ante
*toda* entrada mal formada. Las diferencias que se han encontrado hasta ahora
eran siempre del mismo tipo: un camino rechazaba un archivo mal escrito que el
otro leía, con el mismo contenido firmado. Si encuentras una entrada que un
camino acepte y el otro rechace, es un defecto de este kit.

El veredicto es el mismo; el código de salida puede no serlo. Ante una entrada
mal formada un camino puede salir 1 y el otro 2.

## Qué se firma, exactamente

1. **El hash canónico.** `commitment_hash` es el SHA-256 de `commitment.json`
   serializado con las claves ordenadas, sin espacios y en UTF-8 sin escapar.
   Reordenar o reindentar el archivo no lo cambia. Cambiar, agregar o quitar
   un campo o un valor sí, y la firma deja de verificar.
2. **La firma.** Ed25519 sobre los 64 caracteres hexadecimales de
   `sha256("content-integrity:ed25519:dike-content-signature-v2:" + commitment_hash)`.
   El rol va dentro de lo firmado: una firma hecha para otro rol no verifica
   como commitment.
3. **El sobre.** `commitment.sig.json` lleva exactamente seis campos, todos
   cadenas: `schema_version`, `role`, `algorithm`, `key_id`, `commitment_hash`
   y `signature`, que son 128 hexadecimales en minúsculas. Un campo de más no
   lo cubriría la firma, y por eso los dos caminos lo rechazan en vez de
   ignorarlo. Igual que en el commitment, reordenar o reindentar el archivo no
   cambia nada; cambiar, agregar o quitar un campo o un valor, sí.
4. **La clave pública.** `content-signing-key.pub` es una sola clave en PEM,
   tal como la escriben OpenSSL y Python. Se admite el salto de línea de
   Windows; con texto antes, con otra clave detrás o con cualquier carácter de
   más, los dos caminos la rechazan.

El paso 1, a mano. Calcula el hash y lo compara con el que declara el sobre:

```bash
python3 -c "
import hashlib, json, sys
def sin_duplicados(pares):
    claves = [k for k, _ in pares]
    assert len(claves) == len(set(claves)), 'claves duplicadas'
    return dict(pares)
c = json.load(open('commitment.json', encoding='utf-8'), object_pairs_hook=sin_duplicados)
raw = json.dumps(c, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
h = hashlib.sha256(raw.encode('utf-8')).hexdigest()
firmado = json.load(open('commitment.sig.json', encoding='utf-8'))['commitment_hash']
print('calculado:', h)
print('firmado  :', firmado)
sys.exit(0 if h == firmado else 1)"
```

Que los dos hashes coincidan no prueba nada por sí solo: quien altera el
commitment puede recalcular el hash y escribirlo en el sobre. Lo que ata es la
firma, y por eso los dos caminos de arriba la verifican.

`jq -cSj` y Python dan el mismo hash canónico para lo que lleva un commitment:
cadenas, enteros, nulos, listas y objetos. Difieren en dos cosas, y por eso
ninguna entra a un commitment. Una son los números que no están escritos como
un entero simple de hasta 15 dígitos (`2.0`, `2e0`, `-0`, `02`, `+2`, o un
entero más largo, que un `jq` anterior a 1.7 redondea): el firmador no los
firma y los dos caminos los rechazan. La otra es el carácter de control DEL,
que el firmador tampoco firma.

**Firmas anteriores (V1).** Hubo un contrato anterior que firmaba solo el
hash, sin ligar el rol. Nunca se publicó ninguna firma V1, y
`verificar_tercero.py` las rechaza.

## Clave de contenido

| | |
|---|---|
| **Rol** | Integridad de commitments (`content-integrity`) |
| Algoritmo | Ed25519 |
| `key_id` | `3c7b3fde075efbe3` |
| Formato | `key_id` = primeros 16 hex del SHA-256 de la clave pública en bruto |

```
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEArt9zSTIMkR8jf2XdsPPDjHLjQ1J3km4xlFeCkxxH230=
-----END PUBLIC KEY-----
```

## Qué es un commitment

`dike constancia` revisa cada cita normativa de un escrito contra el corpus
local de Diké, que son textos derivados de la Biblioteca del Congreso Nacional
(BCN) e identificados por un `pack_hash`. Dice cuáles pudo verificar y cuáles
no. Con `--emit-commitment DIR --sign` escribe además, en `DIR`, el commitment
firmado, con los mismos nombres de archivo que usa este documento.

| | Qué contiene | Dónde queda |
|---|---|---|
| La constancia completa | La cita tal como aparece en el escrito, la ruta del archivo, el origen que anotó el abogado | En la máquina del abogado. No se publica |
| `commitment.json` | Solo las normas que sí se verificaron (identificador, vigencia, hash del texto fuente, URL de BCN), el `pack_hash`, la fecha y los conteos | Se firma y se puede mostrar |

**Lo que revela.** Un commitment no contiene texto del escrito, rutas ni
nombres, y tampoco la huella (SHA-256) del escrito. Sí revela qué normas se
citaron y se verificaron, cuántas citas había, cuántas no se pudieron
verificar, y la fecha y hora de la constancia. Quien publica un commitment
publica eso.

**Lo que queda fuera.** Las citas que Diké no pudo verificar no entran al
commitment: solo viaja su número (`citas_fallidas`). Si ninguna cita queda
verificada, Diké no emite commitment. Tampoco lo emite si no puede decir contra
qué corpus verificó: sin un `pack_hash` de 16 hexadecimales, o con más de un
corpus en uso a la vez, que un solo `pack_hash` no puede nombrar.

## Qué acredita esta firma, y qué no

**Sí acredita:**

- Que el commitment no fue alterado después de firmado.
- Que se firmó con la llave cuya clave pública se presenta.
- Que la firma se emitió para el rol `content-integrity`.

Verificable sin red, sin credenciales y sin acceso a nuestros sistemas.

**No acredita:**

- **Que la fecha tenga valor legal en Chile.** Según la Ley 19.799, art. 5º
  Nº 2, ni siquiera un instrumento privado suscrito con firma electrónica
  avanzada hace fe de su fecha «a menos que ésta conste a través de un fechado
  electrónico otorgado por un prestador acreditado». Esta firma no es firma
  electrónica avanzada ni un fechado de prestador acreditado, y un anclaje en
  blockchain tampoco lo es. La fecha del commitment es la del reloj de la
  máquina que lo emitió. La ley llama Entidad Acreditadora a «la Subsecretaría
  de Economía, Fomento y Reconstrucción» (art. 2º, letra e).
- **Quién firmó.** La firma prueba *que* se firmó con esta llave, no *quién* es
  su titular. Lo que la misma ley prevé para dar fe de ese vínculo es el
  certificado de firma electrónica, la «certificación electrónica que da fe del
  vínculo entre el firmante o titular del certificado y los datos de creación
  de la firma electrónica» (art. 2º, letra b), que otorga un prestador de
  servicios de certificación (art. 11). Esta llave no tiene certificado. Sin
  él, quién es su titular habría que probarlo por otros medios: para lo
  suscrito con una firma electrónica que no es avanzada, la ley se remite a
  «las reglas generales» (art. 5º, inciso final).
- **Que las citas sean sustantivamente correctas.** Diké verifica que cada
  norma existe en su corpus local, que su texto es citable y que está vigente a
  la fecha consultada. **No** verifica que la norma diga lo que el escrito le
  atribuye: eso es juicio del abogado.
- **Que el corpus sea el texto oficial de hoy.** El corpus es una copia local
  de BCN, tomada en una fecha. El `pack_hash` identifica esa copia.

El propio commitment lleva su alcance en el campo `alcance` y las advertencias
del sistema en `advertencias`.

## Separación de roles

Diké usa dos llaves, y la regla es no usar nunca la misma para las dos cosas:

| Llave | Rol | Para qué |
|---|---|---|
| `signing-key.pem` | Autorización | Firmar escrituras aprobadas por una persona |
| `content-signing-key.pem` | Integridad | Firmar commitments |

Qué hace cumplir el código:

- La llave de contenido se configura aparte y nunca cae a la de autorización.
- La firma liga el rol: re-etiquetar un sobre con otro rol lo invalida.
- El firmador de commitments solo firma el rol `content-integrity`: pedirle
  otro rol es un error.
- Diké se niega a firmar un commitment si las dos rutas configuradas apuntan
  al mismo archivo, también a través de un enlace simbólico.

Qué no hace: no detecta una copia de la misma llave guardada en otro archivo.

## Límites conocidos

- **`pack_hash` sin registro público.** Un tercero ve un identificador de 16
  hexadecimales. Todavía no hay un registro público que diga a qué versión del
  corpus corresponde.
- **Sin revocación.** `key_id` permite distinguir llaves, pero no hay mecanismo
  para revocar una. Si esta llave se comprometiera, lo único posible sería
  anunciarlo aquí; y como la firma no lleva una fecha con valor legal, no se
  podría distinguir una firma anterior al compromiso de una posterior.
- **El control de datos personales es por patrones.** Detecta RUT, correo y
  teléfono móvil con formato habitual. No detecta nombres, direcciones,
  teléfonos fijos ni un RUT escrito con espacios. Lo que protege al commitment
  no es ese control sino que su esquema es cerrado: no tiene ningún campo de
  texto libre que venga del escrito.
- **Camino 2 solo en Linux.** No hay receta sin Python para macOS ni Windows.
  El camino 1 no se ha probado fuera de Linux.
- **Fuera de este kit.** La firma de autorización de Diké y el sello "virtual"
  de la aplicación de custodia `lexo-case-writer` son otros mecanismos, con
  sus propios límites. Ese sello virtual no es un sello de tiempo. Nada de lo
  que afirma este documento se apoya en ellos.

## Afirmaciones y pruebas

Lo que este documento afirma sobre cómo se comporta el sistema tiene una
prueba automática, y esta tabla dice cuál. Las pruebas viven en el repositorio
de Diké, que no es público; la última columna dice qué puedes comprobar tú
mismo con esta carpeta. Los límites de la sección anterior son ausencias: no
hay registro del `pack_hash` ni revocación, y eso no se prueba, se declara.

| Afirmación | Prueba | ¿Comprobable con este kit? |
|---|---|---|
| Los comandos de este documento funcionan tal como están escritos | `test_keys_md_ejecutable.py::test_cada_bloque_se_ejecuta_literal` | Sí: ejecútalos |
| Cambiar, agregar o quitar un campo o un valor, en el commitment o en el sobre, hace fallar los dos caminos | `test_keys_md_ejecutable.py::test_un_cambio_hace_fallar_los_dos_caminos` | Sí: cambia un valor y repite |
| El sobre lleva seis campos y ninguno más | `test_content_signing.py::test_from_dict_rechaza_campos_de_mas`, `test_verificar_tercero.py::test_sobre_con_un_campo_de_mas` | Sí: agrega un campo al sobre |
| La firma tiene una sola escritura: en mayúsculas no verifica | `test_content_signing.py::test_firma_en_mayusculas_no_verifica`, `test_verificar_tercero.py::test_firma_en_mayusculas` | Sí |
| La clave pública tiene una sola escritura, salvo el salto de línea de Windows | `test_content_signing.py::test_leer_clave_publica_rechaza_lo_que_openssl_no_leeria_igual`, `::test_leer_clave_publica_acepta_la_forma_canonica_y_el_salto_de_windows` | Sí: agrega una línea antes de la clave |
| Los dos caminos dan el mismo veredicto en cada entrada de la batería | `test_keys_md_ejecutable.py::test_los_tres_verificadores_coinciden` | Sí |
| Una búsqueda con alteraciones al azar no encuentra una entrada en que discrepen | `test_keys_md_ejecutable.py::test_una_busqueda_al_azar_no_encuentra_discrepancias` | No |
| Reordenar, reindentar o cambiar los saltos de línea de un archivo no hace fallar ningún camino | `test_keys_md_ejecutable.py::test_un_cambio_de_forma_no_hace_fallar_ningun_camino` | Sí |
| Se verifica sin red y sin acceso a nuestros sistemas | `test_keys_md_ejecutable.py::test_los_dos_caminos_funcionan_sin_home_ni_red` | Sí: desconecta la red |
| La receta firma el rol y no solo el hash | `test_keys_md_ejecutable.py::test_si_la_receta_verificara_solo_el_hash_se_nota` | Sí: lee el paso 4 |
| Comparar hashes no basta: un sobre con el rol cambiado pasa esa comparación | `test_keys_md_ejecutable.py::test_el_bloque_del_hash_no_ve_un_sobre_reetiquetado` | Sí |
| `jq` y Python dan el mismo hash canónico | `test_keys_md_ejecutable.py::test_jq_y_python_dan_el_mismo_hash` | Sí |
| El firmador no firma números decimales, enteros de más de 15 dígitos ni el carácter DEL | `test_commitment_constancia.py::test_validar_rechaza_tipos_inesperados`, `::test_validar_rechaza_conteos_de_mas_de_15_digitos`, `::test_validar_rechaza_el_caracter_del` | No |
| Los dos caminos rechazan un número que no es un entero simple de hasta 15 dígitos | `test_keys_md_ejecutable.py::test_los_tres_verificadores_coinciden`, `::test_la_receta_rechaza_enteros_que_jq_normaliza` | Sí: escribe `2e0` o `02` donde dice `2` |
| La clave impresa es la del archivo y su `key_id` es el publicado | `test_keys_md_ejecutable.py::test_la_clave_impresa_es_la_del_archivo` | Sí: paso 3 del camino 2 |
| El ejemplo verifica con la clave publicada, y trae cuatro citas verificadas y dos fuera | `test_keys_md_ejecutable.py::test_el_ejemplo_del_kit_verifica_con_la_clave_publicada` | Sí |
| Esta carpeta no contiene claves privadas | `test_keys_md_ejecutable.py::test_la_carpeta_no_trae_claves_privadas` | Sí: `grep -r PRIVATE .` |
| `verificar_tercero.py` no importa nada de Diké | `test_verificar_tercero.py::test_no_importa_nada_de_lexo_cli` | Sí: lee sus `import` |
| Sale 0, 1 o 2 según el caso | `test_verificar_tercero.py::test_positivo_verifica_e_imprime_el_key_id`, `::test_commitment_alterado`, `::test_sobre_sin_un_campo` | Sí |
| Rechaza claves JSON duplicadas | `test_verificar_tercero.py::test_duplicado_primer_nivel_falso_primero` | Sí |
| Reordenar o reindentar no cambia el hash | `test_verificar_tercero.py::test_positivo_el_formato_del_archivo_no_importa` | Sí |
| Rechaza firmas V1 | `test_verificar_tercero.py::test_v1_legitima_se_rechaza` | Sí: cambia `schema_version` |
| El rol va dentro de lo firmado | `test_content_signing.py::test_rol_ligado_a_la_firma_en_ambas_direcciones` | Sí: cambia `role` en el sobre |
| Los bytes firmados son los que dice este documento | `test_content_signing.py::test_contrato_v2_bytes_firmados_fijos` | Sí |
| `dike constancia --emit-commitment --sign` escribe archivos que pasan el verificador | `test_constancia_emit_commitment.py::test_emite_firma_y_el_tercero_verifica` | No |
| Un commitment lleva estos campos y ninguno más | `test_constancia_emit_commitment.py::test_el_commitment_lleva_estos_campos_y_ninguno_mas` | Sí: lee `commitment.json` |
| El commitment no lleva texto, rutas, origen ni huella del escrito | `test_constancia_emit_commitment.py::test_el_commitment_no_lleva_ruta_origen_prosa_ni_huella` | En parte: lee `commitment.json` |
| El esquema es cerrado: un campo de más no se publica ni se firma | `test_commitment_constancia.py::test_compromiso_publico_rechaza_campos_fuera_del_esquema` | No |
| Lo que se publica pasa por el control de datos personales | `test_commitment_constancia.py::test_pii_en_un_campo_publicado_bloquea` | No |
| Las citas no verificadas no entran al commitment | `test_constancia_emit_commitment.py::test_lo_no_verificado_no_entra_al_commitment` | No |
| Sin ninguna cita verificada no hay commitment | `test_constancia_emit_commitment.py::test_ninguna_cita_verificada_no_emite` | No |
| El `pack_hash` son 16 hexadecimales | `test_commitment_constancia.py::test_validar_exige_pack_hash_de_16_hexadecimales`, `test_constancia_emit_commitment.py::test_el_pack_hash_de_un_solo_corpus_son_sus_16_primeros_hex` | Sí: lee `commitment.json` |
| Sin un único corpus que nombrar no hay commitment | `test_constancia_emit_commitment.py::test_sin_un_pack_hash_de_verdad_no_emite` | No |
| Un commitment no se firma si le falta un campo, un conteo es negativo o los conteos no cuadran | `test_commitment_constancia.py::test_validar_exige_cada_campo_obligatorio`, `::test_validar_rechaza_conteos_negativos`, `::test_validar_rechaza_un_total_que_no_cuadra` | No |
| La llave de contenido nunca cae a la de autorización | `test_content_signing.py::test_no_firma_sin_llave_configurada` | No |
| No se firma con el archivo de la llave de autorización | `test_content_signing.py::test_firmar_rechaza_la_llave_de_autorizacion` | No |
| El firmador de commitments solo firma el rol `content-integrity` | `test_content_signing.py::test_firmar_no_emite_el_rol_de_autorizacion` | No |
| Una copia de la misma llave en otro archivo no se detecta | `test_content_signing.py::test_una_copia_de_la_llave_en_otro_archivo_no_se_detecta` | No |
| Las citas de la Ley 19.799 son literales | `test_keys_md_ejecutable.py::test_las_citas_de_la_ley_19799_son_literales` | Sí: BCN, idNorma 196640 |
| El control de datos personales no ve nombres ni RUT con espacios | `test_keys_md_ejecutable.py::test_los_limites_declarados_del_control_de_pii_son_reales` | No |
