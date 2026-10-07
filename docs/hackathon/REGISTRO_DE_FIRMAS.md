# Registro de firmas de la llave de contenido

Llave: `content-integrity`, Ed25519, `key_id` `3c7b3fde075efbe3` (la publicada en `KEYS.md`).

## Reglas

1. **Toda firma hecha con la llave real se anota aquí cuando se hace**, también
   las que salgan mal. Una firma que no está en este registro no debería existir.
2. **Una firma no se borra ni se corrige.** Si un commitment firmado resulta
   incorrecto, se firma uno nuevo y la fila del anterior pasa a «Reemplazada»,
   con el motivo y el número de la que la reemplaza. La fila vieja se queda.
3. **Los errores del proceso se anotan en la sección «Errores»**, hayan llegado
   o no a producir una firma: una firma que no debió hacerse, una que hubo que
   repetir, un control que falló, un descuido que pudo haber firmado algo.
4. Antes de firmar: ensayo con una llave sintética (mismo comando, mismo
   escrito) y comprobación de que el `key_id` de la llave real es el publicado.
   Después: verificación por los dos caminos de `KEYS.md` con la clave
   publicada, sin `/home` ni red, y un control negativo.
5. La firma se emite a una carpeta temporal y solo se copia al kit cuando pasó
   todo lo anterior.

Un test (`test_la_firma_del_kit_esta_en_el_registro`) falla si el ejemplo del
kit lleva una firma que no figura aquí como vigente.

## Firmas (contrato V2)

| N.º | Fecha (UTC) | `commitment_hash` | Qué se firmó | Estado |
|---|---|---|---|---|
| 1 | 2026-10-06T06:16:52Z | `a981036de88ffc2dfec95ecf33421fa08adbda334975cf04477ff5ef450b1b8f` | Commitment del escrito sintético `escrito_demo.md`: 6 citas, 4 verificadas y 2 que Diké no pudo verificar. Corpus `ea28fa1c0f9af6c1` | **Vigente.** Es el ejemplo del kit |

### Detalle de la firma n.º 1

- **Quién la ejecutó.** Una sesión de Claude Code, por instrucción de Cristóbal
  en la conversación del 2026-10-06. El plan de remediación 2 (D4) preveía que
  firmara él a mano y que ningún agente tocara la custodia; Cristóbal decidió
  delegarla. La sesión pasó al CLI la ruta de la llave y nunca leyó ni imprimió
  su contenido.
- **Comando.** `dike constancia docs/hackathon/escrito_demo.md --json --emit-commitment DIR --sign`,
  con `LEXO_CONTENT_SIGNING_KEY_PATH` apuntando a la llave real y `DIR` una
  carpeta temporal. Salió 1, que es lo esperado: hay dos citas sin verificar.
- **Código.** Commit `0bdcf6be` de la rama `bli/remediacion2-commitment`.
- **Escrito.** SHA-256 `4a8ce708986265b793a7753c8caba29ce0f825af3c32b11690c834bb6b6d5fc1`. Se anota aquí porque
  el escrito es sintético y está en el repositorio; el commitment público no
  lleva la huella del escrito.
- **Comprobaciones.** `key_id` de la llave real igual al publicado, antes de
  firmar. La clave pública emitida, idéntica byte a byte a
  `content-signing-key.pub`. Los dos caminos de `KEYS.md` con salida 0, también
  en un entorno sin `/home` ni red. Con el commitment alterado, salida 1 por
  los dos caminos.
- **Lo que se sabía sin resolver al firmar.** El escrito aún no había sido
  revisado por un abogado. Cristóbal decidió firmar igual: si la revisión cambia
  el escrito, se firma de nuevo y esta fila pasa a «Reemplazada».

- **Reverificada el 2026-10-06, después de endurecer los verificadores.** Los
  arreglos de la reauditoría 2 hicieron más estrictos los dos caminos: el
  sobre lleva seis campos y ninguno más, la firma se acepta solo en
  minúsculas, la clave pública solo en su forma canónica y los enteros solo
  hasta 15 dígitos. La firma n.º 1 no se tocó y sigue verificando por los dos
  caminos, también con las herramientas de Debian 12, Ubuntu 22.04 y Ubuntu
  24.04 (`jq` 1.6 y 1.7, OpenSSL 3.0).

Evidencia: `docs/reviews/evidencia/remediacion2_20261006/f6_firma_real.txt` y,
para la reverificación, `docs/reviews/evidencia/remediacion3_20261006/`.

## Firmas anteriores a este registro (contrato V1)

El 2026-10-05, durante el desarrollo y antes de que existiera el contrato V2,
se emitieron con esta misma llave firmas V1, que cubrían solo el hash y no
ligaban el rol. La reauditoría de ese día encontró cinco sobres, todos en
carpetas de trabajo fuera de git (`cache/scratch/`). Ninguno se publicó, y
`verificar_tercero.py` los rechaza. No se anotaron cuando se hicieron: por eso
existe este registro.

Evidencia: `docs/reviews/evidencia/reauditoria_opus55_20261005/q9b_clave_publicada_y_git.txt`.

## Errores

### E1 — 2026-10-06, al escribir este mismo registro (después de la firma n.º 1)

- **Qué pasó.** La primera versión de este archivo se generó con un guion de
  shell cuyo bloque de texto no estaba entre comillas. El shell interpretó cada
  fragmento entre acentos graves del Markdown como un comando a ejecutar. Uno de
  esos fragmentos era el propio comando de firma.
- **Qué efecto tuvo.** Ninguna firma. El comando de firma no llegó a
  ejecutarse (el shell falló antes, al leer `<tmp>` como una redirección) y,
  de haberse ejecutado, no había ninguna llave configurada en ese entorno: el
  CLI habría salido con `SIGNATURE_UNAVAILABLE`. El archivo quedó escrito con
  los datos en blanco y el test del registro falló, que es como se notó.
- **Cómo se comprobó que no hubo daño.** Todas las copias del sobre firmado con
  la llave real tienen el mismo SHA-256, es decir, existe una sola firma; la
  carpeta de custodia conserva sus fechas de modificación; no apareció ningún
  archivo nuevo en el perfil.
- **Qué se cambió.** El archivo se regeneró sin pasar texto con acentos graves
  por el shell. Regla: el texto de un documento nunca va en un bloque que el
  shell expande; las variables se pasan por el entorno.
- **Por qué importa aunque no pasó nada.** El descuido estuvo a una
  redirección fallida y una variable de entorno de ejecutar el comando de firma
  sin que nadie lo pidiera. La regla 5 (firmar a una carpeta temporal) y que la
  llave no esté configurada por defecto son lo que habría contenido el daño.

### E2 — 2026-10-06, hallado por la reauditoría 2 (después de la firma n.º 1)

- **Qué pasó.** El commitment de la firma n.º 1 lleva en `advertencias` la
  frase «El texto menciona normas sin artículo pinpoint que el gate no
  verificó…». En `escrito_demo.md` las cinco menciones del Código del Trabajo
  llevan su artículo: la advertencia no corresponde a ese escrito. La dispara
  un defecto del producto anterior a esta rama: la función que busca normas
  sin artículo mira si el artículo viene después del nombre de la norma, y en
  un escrito chileno va antes («artículo 161 del Código del Trabajo»).
  Hallazgo H6 de `docs/reviews/REAUDITORIA2_COMMITMENT_HACKATHON_20261006.md`.
- **Qué efecto tuvo.** La firma n.º 1 es válida y verifica. Lo firmado advierte
  de más, no certifica de más: ninguna cita quedó acreditada sin estarlo. Pero
  el ejemplo del kit declara un punto ciego que no existe, y quien lo lea
  puede preguntar cuáles son esas normas sin artículo. Ninguna.
- **Qué se hizo.** Sobre la firma, nada: no se parcha ni se borra (regla 2). El
  arreglo del código quedó preparado y medido, **sin aplicar**, en
  `docs/reviews/evidencia/remediacion3_20261006/h6_propuesta/`. Con él, el
  mismo escrito da un commitment que difiere del firmado solo en
  `advertencias` (una en vez de dos) y en `fecha_constancia`.
- **Qué falta, y lo decide Cristóbal.** Aplicar el arreglo y firmar de nuevo
  (firma n.º 2), en lo posible junto con su revisión del escrito como abogado,
  para firmar una sola vez más. Hasta entonces la firma n.º 1 sigue vigente y
  este error queda anotado aquí.
