# Pauta de revisión jurídica — `escrito_demo.md` (10 minutos)

Documento preparado para revisión por abogado del escrito sintético de
demostración (`escrito_demo.md`).

- **SHA-256 actual de `escrito_demo.md`:** `4a8ce708986265b793a7753c8caba29ce0f825af3c32b11690c834bb6b6d5fc1`
- **Firma vigente del kit (n.º 3, 2026-10-27 UTC):** `commitment_hash` `d220a00f21b317279a95a40a643232637645d526c3a63684f90381f7b7f45c30` (`key_id` `3c7b3fde075efbe3`, corpus `af1422d66d1e6eee`). Reemplaza a la n.º 2 (`65f3ebe1…`, corpus `fe458d6b9c57a8d7`).
- **Estado de la revisión:** **APROBADA SIN CAMBIOS** por Cristóbal el 2026-10-26, confirmado por él en la conversación («sí sin cambios»). Aprueba las 4 citas verificadas (arts. 161, 162, 163 y 168) tal como están, sin agregar en `SEGUNDO.-` la salvedad de la indemnización sustitutiva del aviso previo. Entiende que `QUINTO.-` (art. 60) y `SEXTO.-` (art. 9999) están mal a propósito. El escrito es un fragmento sintético de demostración, no una demanda apta para presentar. SHA-256 revisado: `4a8ce708…` (sin cambios). (El 2026-10-14 esta línea la daba por aprobada sin que lo estuviera: ver E3 en `REGISTRO_DE_FIRMAS.md`.)
- **Firma n.º 3:** habrá una de todas formas, porque el corpus se re-sella sin identificadores `lexo.cl` y cambia `pack_hash`. Tu revisión entra en esa misma firma: si cambias el escrito, se firma el escrito nuevo; si no, el mismo.
- **Regla de firma:**
  - Si apruebas el texto **sin cambios**, el SHA-256 del escrito no cambia y la firma n.º 3 se emite sobre el mismo escrito y el corpus nuevo. La revisión se anota en `REGISTRO_DE_FIRMAS.md` cuando la confirmes.
  - Si modificas el escrito, se actualiza `escrito_demo.md` (y `_ANCLAS` en `test_demo_bli_e2e.py` si cambia alguna frase ancla) y la firma n.º 3 se emite sobre el escrito nuevo, siguiendo el protocolo de `REGISTRO_DE_FIRMAS.md`.

---

## 1. Texto íntegro de `escrito_demo.md`

```text
EN LO PRINCIPAL: demanda por despido improcedente. (Escrito SINTÉTICO de demostración; partes ficticias.)

S. J. L. DEL TRABAJO DE SANTIAGO

A. B. C., trabajadora, a US. respetuosamente digo:

PRIMERO.- La demandada puso término a mi contrato invocando la causal de necesidades de la empresa del artículo 161 del Código del Trabajo.

SEGUNDO.- El artículo 162 del Código del Trabajo dispone que, cuando el empleador invoque esa causal, el aviso deberá darse al trabajador, con copia a la Inspección del Trabajo respectiva, a lo menos con treinta días de anticipación.

TERCERO.- Conforme al artículo 163 del Código del Trabajo, si el contrato hubiere estado vigente un año o más y el empleador le pusiere término por necesidades de la empresa, deberá pagar la indemnización por años de servicio.

CUARTO.- El artículo 168 del Código del Trabajo permite al trabajador que considere improcedente la aplicación de la causal recurrir al juzgado competente, dentro del plazo de sesenta días hábiles contado desde la separación.

QUINTO.- A mayor abundamiento, el artículo 60 obliga al empleador a lo solicitado.

SEXTO.- Lo anterior se refuerza con el artículo 9999 del Código del Trabajo.
```

---

## 2. Resumen de las 6 citas y su estado en `dike constancia`

| # | Párrafo | Cita detectada (`cita_raw`) | Estado | Resolución / GID | En `commitment.json` |
|---|---|---|---|---|---|
| 1 | `PRIMERO.-` | `artículo 161 del Código del Trabajo` | `VERIFICADA` | `cl.norma.ct:art:0161` (`IN_FORCE`, hash `0c3c636d…`) | Sí |
| 2 | `SEGUNDO.-` | `artículo 162 del Código del Trabajo dispone` | `VERIFICADA` | `cl.norma.ct:art:0162` (`IN_FORCE`, hash `46b091ba…`) | Sí |
| 3 | `TERCERO.-` | `artículo 163 del Código del Trabajo` | `VERIFICADA` | `cl.norma.ct:art:0163` (`IN_FORCE`, hash `6d0567d4…`) | Sí |
| 4 | `CUARTO.-` | `artículo 168 del Código del Trabajo permite al` | `VERIFICADA` | `cl.norma.ct:art:0168` (`IN_FORCE`, hash `6d33e170…`) | Sí |
| 5 | `QUINTO.-` | `artículo 60` | `FALLO` | `AMBIGUOUS` (sin cuerpo legal; `'0060'` existe en varios códigos) | **No** (cuenta en `citas_fallidas: 2`) |
| 6 | `SEXTO.-` | `artículo 9999 del Código del Trabajo` | `FALLO` | `UNRESOLVABLE` (no existe en el corpus) | **No** (cuenta en `citas_fallidas: 2`) |

---

## 3. Cotejo jurídico cita por cita (las 4 verificadas)

### Cita 1 — Artículo 161 del Código del Trabajo (`PRIMERO.-`)
- **Texto en el escrito:**
  > «PRIMERO.- La demandada puso término a mi contrato invocando la causal de necesidades de la empresa del artículo 161 del Código del Trabajo.»
- **Texto fuente en el corpus (BCN `idNorma=207436`, art. 161 inc. 1º):**
  > «Art. 161. Sin perjuicio de lo señalado en los artículos precedentes, el empleador podrá poner término al contrato de trabajo invocando como causal las necesidades de la empresa, establecimiento o servicio, tales como las derivadas de la racionalización o modernización de los mismos, bajas en la productividad, cambios en las condiciones del mercado o de la economía, que hagan necesaria la separación de uno o más trabajadores. La eventual impugnación de las causales señaladas, se regirá por lo dispuesto en el artículo 168.»
- **Ancla en `test_demo_bli_e2e.py`:** `["necesidades de la empresa"]`
- **Punto a revisar por el abogado:** La atribución («causal de necesidades de la empresa del artículo 161 del Código del Trabajo») y la nomenclatura de la acción en la suma («demanda por despido improcedente», acorde al art. 168 inc. 1º letra a: «aplicación improcedente del artículo 161») son fieles al texto legal.

### Cita 2 — Artículo 162 del Código del Trabajo (`SEGUNDO.-`)
- **Texto en el escrito:**
  > «SEGUNDO.- El artículo 162 del Código del Trabajo dispone que, cuando el empleador invoque esa causal, el aviso deberá darse al trabajador, con copia a la Inspección del Trabajo respectiva, a lo menos con treinta días de anticipación.»
- **Texto fuente en el corpus (BCN `idNorma=207436`, art. 162 inc. 4º):**
  > «Cuando el empleador invoque la causal señalada en el inciso primero del artículo 161, el aviso deberá darse al trabajador, con copia a la Inspección del Trabajo respectiva, a lo menos con treinta días de anticipación. Sin embargo, no se requerirá esta anticipación cuando el empleador pagare al trabajador una indemnización en dinero efectivo sustitutiva del aviso previo, equivalente a la última remuneración mensual devengada.»
- **Ancla en `test_demo_bli_e2e.py`:** `["el aviso deberá darse al trabajador, con copia a la Inspección del Trabajo respectiva, a lo menos con treinta días de anticipación"]`
- **Punto a revisar por el abogado:** Reproduce literalmente la primera oración del inciso cuarto del art. 162. No menciona la excepción de la segunda oración (indemnización sustitutiva del aviso previo), lo que es habitual en la exposición de la regla general, pero queda a tu criterio si prefieres mantenerlo así o añadir «salvo pago de la indemnización sustitutiva del aviso previo».

### Cita 3 — Artículo 163 del Código del Trabajo (`TERCERO.-`)
- **Texto en el escrito:**
  > «TERCERO.- Conforme al artículo 163 del Código del Trabajo, si el contrato hubiere estado vigente un año o más y el empleador le pusiere término por necesidades de la empresa, deberá pagar la indemnización por años de servicio.»
- **Texto fuente en el corpus (BCN `idNorma=207436`, art. 163 inc. 1º):**
  > «Art. 163. Si el contrato hubiere estado vigente un año o más y el empleador le pusiere término en conformidad al artículo 161, deberá pagar al trabajador, la indemnización por años de servicio que las partes hayan convenido individual o colectivamente, siempre que ésta fuere de un monto superior a la establecida en el inciso siguiente.»
- **Anclas en `test_demo_bli_e2e.py`:** `["vigente un año o más y el empleador le pusiere término", "por años de servicio"]`
- **Punto a revisar por el abogado:** Paráfrasis directa del presupuesto del inciso primero del art. 163 (en relación con el inciso segundo).

### Cita 4 — Artículo 168 del Código del Trabajo (`CUARTO.-`)
- **Texto en el escrito:**
  > «CUARTO.- El artículo 168 del Código del Trabajo permite al trabajador que considere improcedente la aplicación de la causal recurrir al juzgado competente, dentro del plazo de sesenta días hábiles contado desde la separación.»
- **Texto fuente en el corpus (BCN `idNorma=207436`, art. 168 inc. 1º):**
  > «Art. 168. El trabajador cuyo contrato termine por aplicación de una o más de las causales establecidas en los artículos 159, 160 y 161, y que considere que dicha aplicación es injustificada, indebida o improcedente, o que no se haya invocado ninguna causal legal, podrá recurrir al juzgado competente, dentro del plazo de sesenta días hábiles, contado desde la separación, a fin de que éste así lo declare.»
- **Anclas en `test_demo_bli_e2e.py`:** `["recurrir al juzgado competente", "sesenta días hábiles", "improcedente"]`
- **Punto a revisar por el abogado:** Reproduce el supuesto específico de improcedencia (correspondiente al art. 161 conforme a la letra a del mismo art. 168) y el plazo de caducidad de 60 días hábiles del inciso primero.

---

## 4. Las 2 citas rechazadas a propósito (`QUINTO.-` y `SEXTO.-`)

1. **`QUINTO.- A mayor abundamiento, el artículo 60 obliga al empleador a lo solicitado.`**
   - **Propósito en el demo:** Disparar `AMBIGUOUS` (cita huérfana sin cuerpo legal; el número `60` existe en múltiples cuerpos del corpus).
2. **`SEXTO.- Lo anterior se refuerza con el artículo 9999 del Código del Trabajo.`**
   - **Propósito en el demo:** Disparar `UNRESOLVABLE` (el cuerpo legal existe en el corpus, pero el artículo `9999` no existe).

**Invariantes de la suite (`test_demo_bli_e2e.py` y `test_keys_md_ejecutable.py`):**
- El escrito debe conservar exactamente 6 citas: 4 verificadas (`cl.norma.ct:art:0161`, `0162`, `0163`, `0168`) y 2 rechazadas (`artículo 60` como `AMBIGUOUS` y `artículo 9999 del Código del Trabajo` como `UNRESOLVABLE`).
- No debe agregarse ninguna mención suelta a otra ley o código sin artículo pinpoint (para no disparar la advertencia de normas sin artículo).

---

## 5. Protocolo en caso de cambio del escrito (Firma n.º 3)

Si decides modificar el texto de `escrito_demo.md`, el procedimiento obligatorio según `REGISTRO_DE_FIRMAS.md` es:

1. Actualizar `escrito_demo.md` (y `_ANCLAS` en `test_demo_bli_e2e.py` si cambió alguna frase ancla).
2. **Ensayo previo con llave sintética** en carpeta temporal bajo `/tmp`: verificar que `dike constancia` emite commitment con 4 verificadas, 2 fallidas y 1 sola advertencia.
3. **Comprobar `key_id` de la llave real** (pasando la ruta en `~/.local/share/lexo-custody/lexo-alpha/` a OpenSSL sin leer ni imprimir jamás la llave privada): debe dar `3c7b3fde075efbe3`.
4. **Emitir la firma n.º 3 a `/tmp`** pasando la ruta en `LEXO_CONTENT_SIGNING_KEY_PATH`.
5. **Comprobar la clave pública emitida** byte a byte contra `content-signing-key.pub`.
6. **Verificar por los dos caminos** de `KEYS.md` (en aislamiento sin `/home` ni red) y ejecutar el **control negativo** (`citas_fallidas` `2 -> 0` debe salir `1`).
7. **Copiar al kit** (`commitment.json` y `commitment.sig.json`) y **actualizar `REGISTRO_DE_FIRMAS.md`**: agregar la fila n.º 3 como `**Vigente.**` y pasar la fila n.º 2 a `**Reemplazada** por la n.º 3 (revisión de abogado del escrito demo)`.
