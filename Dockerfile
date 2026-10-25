FROM apache/airflow:2.10.4-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY pyproject.toml /pyproject.toml
RUN python -c "import subprocess, tomllib; deps = tomllib.load(open('/pyproject.toml', 'rb'))['project']['dependencies']; subprocess.run(['pip', 'install', '--no-cache-dir', *deps], check=True)"