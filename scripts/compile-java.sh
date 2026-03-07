#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$REPO_ROOT/python/resources/out"
INCLUDE_TESTS=1
CLEAN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --main-only)
      INCLUDE_TESTS=0
      shift
      ;;
    --clean)
      CLEAN=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--out-dir PATH] [--main-only] [--clean]" >&2
      exit 2
      ;;
  esac
done

if ! command -v javac >/dev/null 2>&1; then
  echo "Could not find 'javac' on PATH. Install a JDK and ensure javac is available." >&2
  exit 1
fi

sources=()
for f in "$REPO_ROOT"/java/main/*.java; do
  [[ -f "$f" ]] && sources+=("$f")
done

if [[ "$INCLUDE_TESTS" -eq 1 ]]; then
  for f in "$REPO_ROOT"/java/tests/*.java; do
    [[ -f "$f" ]] && sources+=("$f")
  done
fi

if [[ ${#sources[@]} -eq 0 ]]; then
  echo "No Java source files were found under java/main or java/tests." >&2
  exit 1
fi

if [[ "$CLEAN" -eq 1 && -d "$OUT_DIR" ]]; then
  rm -rf "$OUT_DIR"
fi
mkdir -p "$OUT_DIR"

echo "Compiling ${#sources[@]} Java file(s) to $OUT_DIR"
javac -d "$OUT_DIR" "${sources[@]}"
echo "Java compilation complete."
