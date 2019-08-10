#!/usr/bin/env bash
export SPELLING=1
if poetry run sphinx-build -E -b spelling docs build/docs 2>/dev/null | sed 's/^/docs\//' | grep '\.rst:[0-9]'; then
  exit 1
fi
exit 0
