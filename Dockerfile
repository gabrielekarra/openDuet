# syntax=docker/dockerfile:1
FROM python:3.12-slim
ARG OPENDUET_BROWSER=false
ARG OPENDUET_VOICE=false
ARG OPENDUET_KEV=false
ARG OPENDUET_OFFICE=false
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
WORKDIR /app
COPY pyproject.toml README.md LICENSE uv.lock ./
COPY openduet ./openduet
RUN --mount=type=secret,id=build_ca,target=/tmp/build-ca.pem \
    if [ -s /tmp/build-ca.pem ]; then \
      export SSL_CERT_FILE=/tmp/build-ca.pem PIP_CERT=/tmp/build-ca.pem UV_SYSTEM_CERTS=true NODE_EXTRA_CA_CERTS=/tmp/build-ca.pem; \
    fi; \
    pip install --no-cache-dir uv && \
    set -- && \
    if [ "$OPENDUET_BROWSER" = true ]; then set -- "$@" --extra browser; fi && \
    if [ "$OPENDUET_VOICE" = true ]; then set -- "$@" --extra voice; fi && \
    if [ "$OPENDUET_KEV" = true ]; then set -- "$@" --extra kev; fi && \
    uv sync --frozen --no-dev --no-editable "$@" && \
    if [ "$OPENDUET_BROWSER" = true ]; then .venv/bin/playwright install --with-deps chromium; fi && \
    if [ "$OPENDUET_OFFICE" = true ]; then apt-get update -qq && apt-get install -y --no-install-recommends libreoffice-calc libreoffice-impress poppler-utils > /dev/null && rm -rf /var/lib/apt/lists/*; fi && \
    chmod -R a+rX /app/openduet && useradd -m -u 10001 openduet && mkdir -p /data/prototypes /prototypes /computer /models && chown -R openduet /data /prototypes /computer /models
USER openduet
EXPOSE 8765
CMD ["/app/.venv/bin/openduet", "--config", "/app/openduet.toml"]
