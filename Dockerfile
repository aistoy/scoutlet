# Dockerfile for scoutlet webui — targets Hugging Face Spaces by default
# (port 7860, non-root user, no browser), but works on any container host
# (Render, Fly.io, Cloud Run, etc.) by overriding the SCOUTLET_UI_* env vars.
#
# Installs from the repo source (not PyPI) so the image always picks up the
# latest webui.py changes — PyPI releases lag behind main, and the webui
# env-var support required for container hosting is read at import time.
#
# Build locally:
#   docker build -t scoutlet-ui .
#   docker run -p 7860:7860 scoutlet-ui
#
# Deploy on HF Spaces: push this Dockerfile + the repo to a Space, set
# SDK to "docker" in the Space's README.md frontmatter (see project README).

FROM python:3.11-slim

# HF Spaces runs containers as a non-root user (UID 1000) — set that up
# first so the runtime user exists before we install anything.
RUN useradd -m -u 1000 user

WORKDIR /app

# Copy repo (`.dockerignore` filters out .git, .venv, dist, tests, etc.)
# and install from source so webui.py always matches the repo HEAD.
COPY --chown=user:user . /app
RUN pip install --no-cache-dir .

ENV HOME=/home/user \
    PYTHONUNBUFFERED=1 \
    SCOUTLET_UI_HOST=0.0.0.0 \
    SCOUTLET_UI_PORT=7860 \
    SCOUTLET_UI_OPEN_BROWSER=0 \
    SCOUTLET_UI_AUTO_PORT=0

USER user
EXPOSE 7860

# webui.run_server() reads SCOUTLET_UI_* env vars for host/port/browser/auto_port,
# so no launcher script is needed.
CMD ["python", "-c", "from scoutlet.webui import run_server; run_server()"]
