# sg-urban-spine view server (OGC API Features over Silver + published Gold). Read-only on the lake.
#   docker build -t localhost/sg-urban-spine-serve:0.1.0 .
#   local checkout instead of GitHub: --build-context spine=/path/to/sg-urban-spine --build-arg SPINE_PIP=/src
ARG BASE=python:3.11-slim
FROM scratch AS spine
FROM ${BASE}
ARG SPINE_PIP="git+https://github.com/tetratorus/sg-urban-spine@main"
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN --mount=type=bind,from=spine,target=/src,rw pip install --no-cache-dir "${SPINE_PIP}"
EXPOSE 8090
CMD ["spine", "--lake", "/lake", "serve", "--host", "0.0.0.0", "--port", "8090"]
