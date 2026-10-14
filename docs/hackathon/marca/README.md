# Diké — logo

The mark is a balance whose stand is a Δ, the initial of ΔΙΚΗ. The left pan is
full and carries a check: what Diké verified. The right pan is empty: what it
refused to certify. *Verify less, prove it.*

| File | Use |
|---|---|
| `dike-icono.svg`, `dike-icono-512.png`, `dike-icono-1024.png` | Square icon (BUIDL logo, avatar, favicon) |
| `dike-logotipo-oscuro.svg` / `.png` | Horizontal logo on a dark background |
| `dike-logotipo-claro.svg` / `.png` | Horizontal logo on a light background |
| `dike-marca-oro.svg`, `dike-marca-tinta.svg` | The mark alone, transparent background |
| `dike-portada.svg` / `.png` | 1920×1080 cover (BUIDL cover, first frame of the video) |

Colors: ink `#0E1A2B`, gold `#D4A84B`, ivory `#F3EDE2`.

The word and the motto are outlined (no font needed to display the SVGs). They
were set in Cormorant Garamond SemiBold and Inter SemiBold, both under the SIL
Open Font License.

Regenerate (from the profile that holds `scripts/hackathon/marca/`):

```bash
python scripts/hackathon/marca/generar_logo.py docs/hackathon/marca <fonts-dir>
cd docs/hackathon/marca
rsvg-convert -w 512 dike-icono.svg -o dike-icono-512.png
rsvg-convert -w 1024 dike-icono.svg -o dike-icono-1024.png
rsvg-convert -h 600 dike-logotipo-oscuro.svg -o dike-logotipo-oscuro.png
rsvg-convert -h 600 dike-logotipo-claro.svg -o dike-logotipo-claro.png
rsvg-convert -w 1920 dike-portada.svg -o dike-portada.png
```
