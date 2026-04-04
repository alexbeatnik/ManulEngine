# ============================================================================
# ManulEngine CI/CD Runner — Multi-stage Dockerfile
# Image: ghcr.io/alexbeatnik/manul-engine
# ============================================================================

# ---------------------------------------------------------------------------
# Build args
# ---------------------------------------------------------------------------
ARG PYTHON_VERSION=3.12
ARG MANUL_VERSION=0.0.9.22
ARG BROWSERS=chromium

# ===========================================================================
# Stage 1: builder — install Python packages + Playwright browsers
# ===========================================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

ARG MANUL_VERSION
ARG BROWSERS

ENV PLAYWRIGHT_BROWSERS_PATH=/home/manul/.cache/ms-playwright

# Install ManulEngine (no pip cache to keep layer small)
RUN pip install --no-cache-dir manul-engine==${MANUL_VERSION}

# Install Playwright browser(s) — downloads binaries + system deps
RUN playwright install --with-deps ${BROWSERS}

# ===========================================================================
# Stage 2: runtime — slim final image
# ===========================================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ARG MANUL_VERSION
ARG PYTHON_VERSION

# Runtime system libraries for Playwright Chromium + fonts + PID 1
RUN apt-get update && apt-get install -y --no-install-recommends \
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
        libdrm2 libdbus-1-3 libxkbcommon0 libatspi2.0-0 \
        libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
        libpango-1.0-0 libcairo2 libasound2 libwayland-client0 \
        fonts-liberation fonts-noto-color-emoji \
        dumb-init \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages
COPY --from=builder /usr/local/bin/manul /usr/local/bin/manul
COPY --from=builder /usr/local/bin/playwright /usr/local/bin/playwright

# ---------------------------------------------------------------------------
# Non-root user
# ---------------------------------------------------------------------------
RUN groupadd --gid 1000 manul \
    && useradd --uid 1000 --gid manul --shell /bin/bash --create-home manul

# Copy Playwright browser binaries from builder stage
ENV PLAYWRIGHT_BROWSERS_PATH=/home/manul/.cache/ms-playwright
COPY --from=builder /home/manul/.cache/ms-playwright /home/manul/.cache/ms-playwright
RUN chown -R manul:manul /home/manul/.cache

# ---------------------------------------------------------------------------
# Working directory
# ---------------------------------------------------------------------------
WORKDIR /workspace
RUN mkdir -p /workspace/reports /workspace/cache \
    && chown -R manul:manul /workspace

# ---------------------------------------------------------------------------
# Environment — sensible CI defaults
# ---------------------------------------------------------------------------
ENV MANUL_HEADLESS=true \
    MANUL_BROWSER=chromium \
    MANUL_SCREENSHOT=on-fail \
    MANUL_HTML_REPORT=true \
    MANUL_WORKERS=1 \
    MANUL_BROWSER_ARGS="--no-sandbox --disable-dev-shm-usage" \
    PLAYWRIGHT_BROWSERS_PATH=/home/manul/.cache/ms-playwright \
    TZ=UTC \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1

# ---------------------------------------------------------------------------
# OCI labels
# ---------------------------------------------------------------------------
LABEL org.opencontainers.image.source="https://github.com/alexbeatnik/ManulEngine" \
      org.opencontainers.image.description="ManulEngine — deterministic DSL-first browser automation CI runner" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="0.0.9.22" \
      org.opencontainers.image.vendor="alexbeatnik"

# ---------------------------------------------------------------------------
# Health check (useful for serve / daemon modes)
# ---------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["manul", "--help"]

# Switch to non-root
USER manul

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
ENTRYPOINT ["dumb-init", "--", "manul"]
CMD ["--help"]
