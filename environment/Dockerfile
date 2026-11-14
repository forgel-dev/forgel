FROM python:3.12-slim

# The test suite creates and inspects real git repositories. Nothing else is
# installed: the core and its tests use the Python standard library only.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
