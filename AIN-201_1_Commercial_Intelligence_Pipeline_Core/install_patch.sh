#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-.}"

if [[ ! -d "$TARGET/anchorinsight_registry" ]]; then
  echo "ERROR: target does not contain anchorinsight_registry/"
  echo "Usage: ./install_patch.sh /path/to/AnchorOS"
  exit 1
fi

mkdir -p "$TARGET/anchorinsight_pipeline" "$TARGET/tests" "$TARGET/examples"
cp -r anchorinsight_pipeline/. "$TARGET/anchorinsight_pipeline/"
cp tests/test_ain201_pipeline_core.py "$TARGET/tests/"
cp examples/run_ain201_pipeline.py "$TARGET/examples/"

echo "AIN-201.1 patch installed into: $TARGET"
echo "Verify with:"
echo "  cd \"$TARGET\""
echo "  python -m unittest tests.test_ain201_pipeline_core -v"
echo "  python -m examples.run_ain201_pipeline"
