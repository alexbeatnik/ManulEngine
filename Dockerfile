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
# Stage 1: deps — install Python packages + Playwright browsers
# ===========================================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS deps

ARG MANUL_VERSION
ARG BROWSERS

# System packages required by Playwright Chromium + fonts for screenshots
RUN apt-get update && apt-get install -y --no-install-recommends \
        # Playwright Chromium runtime deps
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
        libdrm2 libdbus-1-3 libxkbcommon0 libatspi2.0-0 \
        libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
        libpango-1.0-0 libcairo2 libasound2 libwayland-client0 \
        # Fonts for correct text rendering in screenshots
        fonts-liberation fonts-noto-color-emoji \
        # PID 1 init
        dumb-init \
    && rm -rf /var/lib/apt/lists/*

# Install ManulEngine (no pip cache to keep layer small)
RUN pip install --no-cache-dir manul-engine==${MANUL_VERSION}

# Install Playwright browser(s)
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
RUN playwright install --with-deps ${BROWSERS}

# ===========================================================================
# Stage 2: runtime — slim final image
# ===========================================================================
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ARG MANUL_VERSION
ARG BROWSERS

# Re-install only the minimal runtime system libraries (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
        libdrm2 libdbus-1-3 libxkbcommon0 libatspi2.0-0 \
        libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
        libpango-1.0-0 libcairo2 libasound2 libwayland-client0 \
        fonts-liberation fonts-noto-color-emoji \
        dumb-init \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from deps stage
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin/manul /usr/local/bin/manul
COPY --from=deps /usr/local/bin/playwright /usr/local/bin/playwright

# Copy Playwright browser binaries from deps stage
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers
COPY --from=deps /opt/playwright-browsers /opt/playwright-browsers

# ---------------------------------------------------------------------------
# Non-root user
# ---------------------------------------------------------------------------
RUN groupadd --gid 1000 manul \
    && useradd --uid 1000 --gid manul --shell /bin/bash --create-home manul

# ---------------------------------------------------------------------------
# Working directory
# ---------------------------------------------------------------------------
WORKDIR /workspace
RUN chown manul:manul /workspace

# ---------------------------------------------------------------------------
# Environment — sensible CI defaults
# ---------------------------------------------------------------------------
ENV MANUL_HEADLESS=true \
    MANUL_BROWSER=chromium \
    MANUL_SCREENSHOT=on-fail \
    MANUL_HTML_REPORT=true \
    MANUL_WORKERS=1 \
    MANUL_BROWSER_ARGS="--no-sandbox --disable-dev-shm-usage" \
    TZ=UTC \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1

# ---------------------------------------------------------------------------
# OCI labels
# ---------------------------------------------------------------------------
LABEL org.opencontainers.image.source="https://github.com/alexbeatnik/ManulEngine" \
      org.opencontainers.image.description="ManulEngine — deterministic DSL-first browser automation CI runner" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${MANUL_VERSION}"

# ---------------------------------------------------------------------------
# Health check (useful for serve / daemon modes)
# ---------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["manul", "--help"]

# Switch to non-root
USER manul

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
ENTRYPOINT ["dumb-init", "--", "manul"]
CMD ["--help"]
