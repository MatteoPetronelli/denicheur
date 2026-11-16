#!/usr/bin/env bash
# Prove a repo works from a fresh clone: clone HEAD into a temp folder, run the gate there, clean up.
#
#   clean_clone_check.sh "cargo test --workspace" "cargo clippy --workspace --all-targets -- -D warnings"
#   clean_clone_check.sh --keep "docker compose -p proof up -d --build" "curl -fsS localhost:3000"
#
# Each argument is one shell command, run from the root of the clone. Stops at the first failure.
# --keep leaves the clone in place (to inspect it, or because containers still use it).
# Only committed work is cloned: uncommitted changes are listed as a warning, not tested.
set -u

keep=0
[ "${1:-}" = "--keep" ] && { keep=1; shift; }
[ $# -ge 1 ] || { echo "usage: $0 [--keep] \"command\" [\"command\" ...]" >&2; exit 2; }

src=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "not inside a git repository" >&2; exit 2; }
cd "$src" || exit 2

dirty=$(git status --porcelain)
[ -n "$dirty" ] && { echo "WARNING: not in the clone (uncommitted):"; echo "$dirty" | sed 's/^/  /'; }

# What only a clone reveals: empty directories are not tracked, and line endings may be converted.
empty=$(find . -type d -empty -not -path './.git/*' -not -path '*/node_modules/*' -not -path '*/target/*' 2>/dev/null | head -20)
[ -n "$empty" ] && { echo "NOTE: empty directories (absent from a clone):"; echo "$empty" | sed 's/^/  /'; }
[ "$(git config core.autocrlf)" = "true" ] && echo "NOTE: core.autocrlf=true, text files are checked out with CRLF here."

dest="${TMPDIR:-${TEMP:-/tmp}}/clean-clone-$(basename "$src")-$$"
git clone -q . "$dest" || { echo "clone failed" >&2; exit 1; }
echo "clone: $dest ($(git -C "$dest" log --format='%h %s' -1))"

status=0
cd "$dest" || exit 1
for cmd in "$@"; do
  echo "--- $cmd"
  if ! bash -c "$cmd"; then
    echo "FAILED: $cmd"
    status=1
    break
  fi
done
cd "$src" || exit 1

if [ $keep -eq 1 ]; then
  echo "kept: $dest"
else
  rm -rf "$dest"
fi
[ $status -eq 0 ] && echo "CLEAN CLONE OK ($# command(s))" || echo "CLEAN CLONE FAILED"
exit $status
