#!/usr/bin/env bash
# Verify all AI FrontDesk infrastructure services are responding.
# Run from the project root after `docker compose up -d`.

set -uo pipefail

# ── Load .env so password variables are available ─────────────────────────────
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local name="$1"
    local cmd="$2"
    if eval "$cmd" &>/dev/null; then
        echo -e "${GREEN}  [OK]${NC}  $name"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}  [FAIL]${NC} $name"
        FAIL=$((FAIL + 1))
    fi
}

echo ""
echo "AI FrontDesk — Infrastructure Health Check"
echo "============================================"

# PostgreSQL — checked via docker exec (bypasses host port remap)
check "PostgreSQL" \
    "docker compose exec -T postgres pg_isready -U argent -d argent"

# Redis — checked via docker exec (bypasses host port remap)
check "Redis" \
    "docker compose exec -T redis redis-cli -a \"${REDIS_PASSWORD:-changeme}\" ping | grep -q PONG"

# ChromaDB — host port 8002
check "ChromaDB" \
    "curl -sf --max-time 5 http://localhost:8002/api/v1/heartbeat"

# Neo4j HTTP — host port 7475
check "Neo4j HTTP" \
    "curl -sf --max-time 10 http://localhost:7475"

# Neo4j Bolt — checked via docker exec (bypasses host port remap)
check "Neo4j Bolt" \
    "docker compose exec -T neo4j \
        cypher-shell -u neo4j -p \"${NEO4J_PASSWORD:-changeme}\" 'RETURN 1 AS ok' \
        2>/dev/null | grep -q 1"

# LiveKit — check port is open (returns non-2xx but connection succeeds)
check "LiveKit" \
    "curl -s --max-time 5 http://localhost:7880 > /dev/null"

# Ollama
check "Ollama" \
    "curl -sf --max-time 5 http://localhost:11434"

# Ollama — model present
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:4b}"
check "Ollama model: ${OLLAMA_MODEL}" \
    "curl -sf --max-time 5 http://localhost:11434/api/tags | grep -q '${OLLAMA_MODEL%%:*}'"

# Piper model files (downloaded by scripts/pull_models.sh)
check "Piper model files" \
    "test -f piper-models/en_US-lessac-medium.onnx \
     && test -f piper-models/en_US-lessac-medium.onnx.json"

echo ""
echo "============================================"
echo -e "  Passed: ${GREEN}${PASS}${NC}  |  Failed: ${RED}${FAIL}${NC}"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo -e "${YELLOW}  Tip: run \`docker compose logs <service>\` to debug a failure.${NC}"
    echo -e "${YELLOW}  Ollama model + Piper files need \`bash scripts/pull_models.sh\` first.${NC}"
    exit 1
else
    echo -e "${GREEN}  All services healthy. Ready to start the backend.${NC}"
fi
echo ""
