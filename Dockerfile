# ============================================================================
# ManulEngine CI/CD Runner — Multi-stage Dockerfile
# Image: ghcr.io/alexbeatnik/manul-engine
# ============================================================================

# ---------------------------------------------------------------------------
# Build args
# ---------------------------------------------------------------------------
ARG PYTHON_VERSION=3.12
ARG MANUL_VERSION=0.0.9.28
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
ARG BROWSERS

# Copy installed Python packages from builder stage.
# Use a staging copy so the path is robust regardless of whether
# PYTHON_VERSION is major.minor (3.12) or a patch version (3.12.3).
COPY --from=builder /usr/local/lib/ /tmp/builder-lib/
COPY --from=builder /usr/local/bin/manul /usr/local/bin/manul
COPY --from=builder /usr/local/bin/playwright /usr/local/bin/playwright
RUN PY_SITELIB="/usr/local/lib/python$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')/site-packages" \
    && BUILDER_SITELIB=$(ls -d /tmp/builder-lib/python*/site-packages | head -1) \
    && cp -a "${BUILDER_SITELIB}/." "${PY_SITELIB}/" \
    && rm -rf /tmp/builder-lib

# Install runtime system deps for Playwright browsers + fonts + PID 1
# Using playwright install-deps ensures the dep list stays in sync with
# the Playwright version rather than a hand-maintained apt list.
RUN apt-get update && apt-get install -y --no-install-recommends \
        dumb-init fonts-liberation fonts-noto-color-emoji \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Non-root user
# ---------------------------------------------------------------------------
RUN groupadd --gid 1000 manul \
    && useradd --uid 1000 --gid manul --shell /bin/bash --create-home manul

# Copy Playwright browser binaries from builder stage
ENV PLAYWRIGHT_BROWSERS_PATH=/home/manul/.cache/ms-playwright
COPY --from=builder /home/manul/.cache/ms-playwright /home/manul/.cache/ms-playwright
RUN chown -R manul:manul /home/manul/.cache

# Install OS-level deps required by copied browsers (must run as root, before USER)
RUN playwright install-deps ${BROWSERS}

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
      org.opencontainers.image.version="${MANUL_VERSION}" \
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
