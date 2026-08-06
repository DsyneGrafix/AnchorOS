#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-.}"

if [[ ! -d "$TARGET/anchorinsight_pipeline" ]]; then
  echo "ERROR: target does not contain anchorinsight_pipeline/"
  echo "Install AIN-201.1 first."
  exit 1
fi

cp -r anchorinsight_pipeline/. "$TARGET/anchorinsight_pipeline/"
cp tests/test_ain302_evidence_lifecycle.py "$TARGET/tests/"
cp examples/run_ain302_evidence_proof.py "$TARGET/examples/"

echo "AIN-302 patch installed into: $TARGET"
echo "Verify with:"
echo "  cd \"$TARGET\""
echo "  python -m unittest tests.test_ain302_evidence_lifecycle -v"
echo "  python -m examples.run_ain302_evidence_proof"
