#!/usr/bin/env bash
set -euo pipefail

api_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
anchorintel_dir="$(dirname -- "$api_dir")"
engine_dir="$anchorintel_dir/spatial-opportunity-engine"

if [[ ! -d "$engine_dir/spatial_engine" ]]; then
  echo "AnchorIntel could not find the S.P.A.T.I.A.L. engine at:" >&2
  echo "  $engine_dir" >&2
  echo "Keep api and spatial-opportunity-engine together under apps/anchorintel." >&2
  exit 1
fi

export PYTHONPATH="$engine_dir:$api_dir${PYTHONPATH:+:$PYTHONPATH}"

exec python3 -m anchorintel_api \
  --database "$api_dir/data/anchorintel.db" \
  --seed-reference \
  "$@"
