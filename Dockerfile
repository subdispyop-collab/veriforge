# Reproducible image for VERIFORGE 1.0.0 plus the assurance scripts.
# This image was not built on the authoring host: registry and PyPI egress
# were blocked there. The install step is the intended reproduction path.
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml requirements.lock README.md ./
COPY veriforge ./veriforge
COPY tests ./tests
COPY scripts ./scripts
COPY datasets ./datasets
COPY research ./research
COPY experiments ./experiments
COPY docs ./docs

RUN python -m pip install --upgrade pip \
    && python -m pip install -e ".[dev]"

CMD ["python", "scripts/run_assurance_experiment.py"]
