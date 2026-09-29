FROM python:3.14-slim

RUN useradd --system --uid 10001 skp
WORKDIR /app
COPY pyproject.toml ./
COPY skp_companion ./skp_companion
RUN pip install --no-cache-dir . && mkdir -p /data && chown skp /data

USER skp
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import json,urllib.request as u; exit(0 if json.load(u.urlopen('http://127.0.0.1:8000/health'))['ok'] else 1)"
CMD ["skp-companion"]
