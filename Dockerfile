# Diké en un contenedor: el motor de verificación de citas, su corpus y el demo.
# No necesita nada de la máquina de quien lo construye, y una vez construido
# corre sin red:
#
#     docker build -t dike .
#     docker run --rm --network none dike                        # el demo
#     docker run --rm --network none dike python -m pytest -q    # los tests
FROM python:3.12-slim

# jq y OpenSSL: el segundo camino de verificación de docs/hackathon/KEYS.md no usa Python.
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends jq openssl >/dev/null \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home dike

WORKDIR /dike
COPY packages packages
COPY pyproject.toml README.md ./
COPY lexo_cli lexo_cli
COPY shared shared
RUN pip install --no-cache-dir -q ./packages/dike-id/python \
 && pip install --no-cache-dir -q -e ".[test]"

# El corpus: se comprueba su suma, se instala con el propio `dike starter`
# (que valida el paquete entero) y se borra la copia de trabajo.
COPY --chown=dike:dike corpus /home/dike/corpus
USER dike
ENV PYTHONDONTWRITEBYTECODE=1
RUN cd /home/dike/corpus \
 && sha256sum -c SHA256SUMS \
 && tar -xzf chile-base-*.tar.gz \
 && mkdir -p /home/dike/.lexo \
 && printf 'starter:\n  user: demo\n' > /home/dike/.lexo/config.yaml \
 && dike starter --user demo install chile-base --name chile-base --json > /home/dike/corpus-instalado.json \
 && rm -rf /home/dike/corpus

COPY --chown=dike:dike docs docs
COPY --chown=dike:dike scripts scripts
COPY --chown=dike:dike conftest.py ./

CMD ["python", "docs/hackathon/demo_bli_e2e.py"]
