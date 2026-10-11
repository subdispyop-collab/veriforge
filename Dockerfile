# Reproducible image for VERIFORGE 1.0.0 plus the assurance scripts.
# Setuptools 78.1.1 and its Debian dependencies are vendored from
# https://dpvctowv9b08b.cloudfront.net/debian/ (trixie). See vendor/debian/SOURCES.txt.
# This build does not contact PyPI.
FROM python:3.12-slim

WORKDIR /app
COPY vendor/debian /vendor/debian
RUN mkdir -p /opt/vendor \
    && for deb in /vendor/debian/*.deb; do dpkg-deb -x "$deb" /opt/vendor; done \
    && cp -a /opt/vendor/usr/lib/python3/dist-packages/. /usr/local/lib/python3.12/site-packages/ \
    && python -c "import setuptools; print(setuptools.__version__)"

COPY pyproject.toml requirements.lock README.md ./
COPY veriforge ./veriforge
COPY tests ./tests
COPY scripts ./scripts
COPY datasets ./datasets
COPY research ./research
COPY experiments ./experiments
COPY docs ./docs

ENV PIP_NO_INDEX=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m pip install --no-build-isolation --no-index --no-deps -e .

CMD ["python", "scripts/run_assurance_experiment.py"]
