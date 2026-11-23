#!/usr/bin/env bash
# assess.sh — read-only inventory of a codebase to plan a Rust migration.
#
# Usage:   scripts/assess.sh [path]      (defaults to the current directory)
#
# Prints: language breakdown by lines of code, build/dependency manifests found,
# dependency counts, likely entry points, and a rough size signal. Makes no changes.
# Works with just coreutils; uses `cloc`, `tokei`, or `git` if present for better data.

set -euo pipefail

ROOT="${1:-.}"
if [[ ! -d "$ROOT" ]]; then
  echo "error: '$ROOT' is not a directory" >&2
  exit 1
fi
ROOT="$(cd "$ROOT" && pwd)"

# Directories that are noise for a source inventory.
PRUNE=( .git node_modules target dist build .venv venv __pycache__ vendor .next .gradle .idea .cache )
prune_expr=()
for d in "${PRUNE[@]}"; do prune_expr+=( -name "$d" -o ); done
# drop trailing -o
unset 'prune_expr[${#prune_expr[@]}-1]'

hr() { printf '%s\n' "------------------------------------------------------------"; }
section() { hr; printf '  %s\n' "$1"; hr; }

section "Codebase assessment: $ROOT"

# ---------------------------------------------------------------------------
# 1. Language breakdown. Prefer tokei/cloc; otherwise count by extension.
# ---------------------------------------------------------------------------
section "Language breakdown (lines of code)"
if command -v tokei >/dev/null 2>&1; then
  tokei "$ROOT"
elif command -v cloc >/dev/null 2>&1; then
  cloc --quiet "$ROOT"
else
  echo "(install 'tokei' or 'cloc' for richer output; falling back to extension counts)"
  echo
  # shellcheck disable=SC2016
  find "$ROOT" \( "${prune_expr[@]}" \) -prune -o -type f -name '*.*' -print 2>/dev/null \
    | sed -n 's/.*\.\([A-Za-z0-9_]*\)$/\1/p' \
    | tr '[:upper:]' '[:lower:]' \
    | grep -E '^(py|js|jsx|ts|tsx|go|c|h|cc|cpp|cxx|hpp|java|kt|rb|cs|rs|php|scala|swift|m|mm)$' \
    | sort | uniq -c | sort -rn \
    | awk '{printf "  %-8s %s files\n", $2, $1}'
fi

# ---------------------------------------------------------------------------
# 2. Build systems / dependency manifests found (tells you the ecosystem).
# ---------------------------------------------------------------------------
section "Build & dependency manifests"
manifests=(
  "package.json:Node/JS"      "requirements.txt:Python"   "pyproject.toml:Python"
  "Pipfile:Python"            "go.mod:Go"                 "pom.xml:Java/Maven"
  "build.gradle:Java/Gradle"  "build.gradle.kts:Java/Gradle" "Gemfile:Ruby"
  "*.csproj:C#/.NET"          "CMakeLists.txt:C/C++/CMake" "Makefile:C/C++/Make"
  "Cargo.toml:Rust (existing!)" "composer.json:PHP"
)
found_any=0
for entry in "${manifests[@]}"; do
  file="${entry%%:*}"; label="${entry##*:}"
  while IFS= read -r hit; do
    [[ -z "$hit" ]] && continue
    found_any=1
    printf "  %-22s %s\n" "$label" "${hit#"$ROOT"/}"
  done < <(find "$ROOT" \( "${prune_expr[@]}" \) -prune -o -type f -name "$file" -print 2>/dev/null | head -20)
done
[[ "$found_any" -eq 0 ]] && echo "  (none detected)"

# ---------------------------------------------------------------------------
# 3. Rough dependency counts for the common ecosystems.
# ---------------------------------------------------------------------------
section "Dependency counts (rough)"
count_deps() { # file, pattern description
  local f="$1"
  [[ -f "$f" ]] || return 0
  case "$f" in
    *package.json)   n=$(grep -cE '":\s*"' "$f" 2>/dev/null || echo "?"); echo "  package.json:      ~$n dependency lines" ;;
    *requirements.txt) n=$(grep -cvE '^\s*(#|$)' "$f" 2>/dev/null || echo "?"); echo "  requirements.txt:  $n packages" ;;
    *go.mod)         n=$(grep -cE '^\s+[^ ]+ v' "$f" 2>/dev/null || echo "?"); echo "  go.mod:            ~$n modules" ;;
    *Gemfile)        n=$(grep -cE '^\s*gem ' "$f" 2>/dev/null || echo "?"); echo "  Gemfile:           $n gems" ;;
  esac
}
while IFS= read -r f; do count_deps "$f"; done < <(
  find "$ROOT" \( "${prune_expr[@]}" \) -prune -o -type f \
    \( -name package.json -o -name requirements.txt -o -name go.mod -o -name Gemfile \) -print 2>/dev/null | head -20
)

# ---------------------------------------------------------------------------
# 4. Likely entry points — where execution starts (good seam candidates).
# ---------------------------------------------------------------------------
section "Likely entry points"
grep -rlEs --exclude-dir={.git,node_modules,target,dist,build,.venv,venv,__pycache__,vendor} \
  '(^|[^A-Za-z_])(func main|def main|public static void main|if __name__ == .__main__.|fn main)' \
  "$ROOT" 2>/dev/null | head -20 | sed "s#^$ROOT/#  #" || echo "  (none obvious)"

# ---------------------------------------------------------------------------
# 5. Size signal (informs full-rewrite vs incremental).
# ---------------------------------------------------------------------------
section "Size signal"
total_files=$(find "$ROOT" \( "${prune_expr[@]}" \) -prune -o -type f -print 2>/dev/null | wc -l | tr -d ' ')
echo "  Source files (excluding vendor dirs): $total_files"
if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse >/dev/null 2>&1; then
  echo "  Git contributors:  $(git -C "$ROOT" shortlog -sne HEAD 2>/dev/null | wc -l | tr -d ' ')"
  echo "  Last commit:       $(git -C "$ROOT" log -1 --format=%cd --date=short 2>/dev/null || echo '?')"
fi

hr
cat <<'EOF'
Next steps:
  - Read references/strategy.md to choose incremental-FFI vs strangler-service vs rewrite.
  - Identify seams around the entry points and the hottest module above.
  - Then set up the Rust workspace (references/production.md) and the parity harness
    (references/verification.md + scripts/parity_check.py) BEFORE porting logic.
EOF
