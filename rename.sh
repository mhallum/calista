# rename_frontend_to_entrypoints.sh
set -euo pipefail

test -d src/calista || { echo "run from repo root (src/calista missing)"; exit 1; }

# Use git mv if available
if [ -d .git ]; then MV="git mv -k"; else MV="mv"; fi

# 1) Move the package
if [ -d src/calista/frontend ]; then
  if [ -d src/calista/entrypoints ]; then
    echo "Moving contents: src/calista/frontend/* -> src/calista/entrypoints/"
    mkdir -p src/calista/entrypoints
    find src/calista/frontend -mindepth 1 -maxdepth 1 -exec $MV {} src/calista/entrypoints/ \;
    rmdir src/calista/frontend || true
  else
    echo "Renaming: src/calista/frontend -> src/calista/entrypoints"
    $MV src/calista/frontend src/calista/entrypoints
  fi
else
  echo "No src/calista/frontend directory found (nothing to move)"
fi

# 2) Update imports in src/ and tests/ (macOS/BSD sed; see GNU sed below)
if command -v rg >/dev/null 2>&1; then
  echo "Rewriting imports: calista.frontend -> calista.entrypoints (BSD sed)"
  rg -0 -l 'calista\.frontend(\.|$)' src tests | xargs -0 sed -i '' \
    -e 's|calista\.frontend\.|calista.entrypoints.|g' \
    -e 's|\bcalista\.frontend\b|calista.entrypoints|g'
else
  echo "ripgrep (rg) not found; install it or ask me for a Python-based replacer."
fi

# 3) Update console script target in pyproject.toml
#   handles both old forms just in case
sed -i '' \
  -e 's|"calista\.cli\.main:calista"|"calista.entrypoints.cli.main:calista"|g' \
  -e 's|"calista\.frontend\.cli\.main:calista"|"calista.entrypoints.cli.main:calista"|g' \
  pyproject.toml

echo "Done. Verify with: rg -n 'calista\.frontend(\.|$)' src tests || true"
echo "Then run: pytest -q"
