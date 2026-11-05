#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

failed=()

for dir in tests/test_*/; do
  [ -d "$dir" ] || continue
  name=$(basename "$dir")
  compose="$dir/docker-compose.yaml"
  log="$dir/output/run.log"

  printf '[ %-14s ] running... ' "$name"
  rm -rf "${dir}output" && mkdir -p "${dir}output"
  : > "$log"

  # Build + up detached
  if ! docker compose -f "$compose" up --build --remove-orphans --detach client_1 >>"$log" 2>&1; then
    echo "FAIL (docker compose up)"
    failed+=("$name"); echo "     log: $log"
    docker compose -f "$compose" down --remove-orphans -v >>"$log" 2>&1 || true
    continue
  fi

  # ID del contenedor del cliente
  client_id=$(docker compose -f "$compose" ps -q --all client_1)
  if [ -z "$client_id" ]; then
    echo "FAIL (client_1 no arrancó)"
    failed+=("$name"); echo "     log: $log"
    docker compose -f "$compose" down --remove-orphans -v >>"$log" 2>&1 || true
    continue
  fi

  # Esperar su salida y guardar exit code + logs del cliente
  rc=$(docker wait "$client_id" 2>>"$log")
  docker logs "$client_id" >>"$log" 2>&1 || true

  # Bajar todo antes de verificar
  docker compose -f "$compose" down --remove-orphans -v >>"$log" 2>&1 || true

  if [ "$rc" -ne 0 ]; then
    echo "FAIL (client exit=$rc)"
    failed+=("$name"); echo "     log: $log"
    continue
  fi

  # Verificar contra expected 
  verify_out=$(python3 "$dir/verify.py" 2>&1)
  vrc=$?
  echo "$verify_out" >>"$log"

  if [ "$vrc" -ne 0 ]; then
    echo "FAIL (verify)"
    echo "$verify_out" | sed 's/^/       /'
    failed+=("$name"); echo "     log: $log"
  else
    echo "OK"
  fi
done

echo ""
if [ ${#failed[@]} -gt 0 ]; then
  echo "FAILED (${#failed[@]}): ${failed[*]}"
  exit 1
fi
echo "All tests passed."