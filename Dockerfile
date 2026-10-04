# syntax=docker/dockerfile:1
#
# The agent-incidents MCP server (plugins/agent-security/mcp/incidents-server) as an image. Build from the
# repository root, because the image also carries the plugin's dataset snapshot:
#   docker build -t agent-incidents-mcp .
# and run it on stdio (no port is opened, no network request is made):
#   docker run --rm -i agent-incidents-mcp
#
# The base image is pinned by digest (node:22-alpine, multi-arch index).
ARG NODE_IMAGE=node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402
ARG SERVER_DIR=plugins/agent-security/mcp/incidents-server

# Build on the runner's own platform: the output is plain JavaScript and the dependencies have no native code.
FROM --platform=$BUILDPLATFORM ${NODE_IMAGE} AS build
ARG SERVER_DIR
WORKDIR /src
COPY ${SERVER_DIR}/package.json ${SERVER_DIR}/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY ${SERVER_DIR}/tsconfig.json ./
COPY ${SERVER_DIR}/src/ src/
RUN npm run build
# Production tree: runtime dependencies from the committed lockfile, dist/, README and the dataset snapshot.
WORKDIR /out
COPY ${SERVER_DIR}/package.json ${SERVER_DIR}/package-lock.json ${SERVER_DIR}/README.md ${SERVER_DIR}/server.json ./
COPY plugins/agent-security/data/incidents.json data/incidents.json
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund \
 && cp -R /src/dist ./ \
 && rm -rf /root/.npm

FROM ${NODE_IMAGE}
ARG VERSION=0.0.0-dev
LABEL org.opencontainers.image.title="agent-incidents-mcp" \
      org.opencontainers.image.description="Read-only MCP server (stdio) over the AI agent incident dataset" \
      org.opencontainers.image.source="https://github.com/basitalisandhu/agent-security-skills" \
      org.opencontainers.image.url="https://github.com/basitalisandhu/agent-security-skills/tree/main/plugins/agent-security/mcp/incidents-server" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${VERSION}" \
      io.modelcontextprotocol.server.name="io.github.basitalisandhu/agent-incidents"
ENV NODE_ENV=production
COPY --from=build /out/ /app/
WORKDIR /app
USER node
# The bundled snapshot is /app/data/incidents.json. To serve another copy, mount it and set AGENT_INCIDENTS_DATA.
ENTRYPOINT ["node", "dist/index.js"]
