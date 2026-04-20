#!/usr/bin/env bash
# Installs Cuebert's Git LFS attribute template into a downstream game repository.
# Platform: macOS, Linux, WSL (bash 4+). Hub path is derived from this script location.
#
# Usage: scripts/install-game-lfs.sh [--dry-run] [--no-lfs-install] [--force] <project-path>
# Exit: 0 success, 1 user/input error, 2 environment/tooling error
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HUB_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
TEMPLATE="${HUB_ROOT}/docs/projects/_templates/game-project-gitattributes.template"

DRY_RUN=0
NO_LFS_INSTALL=0
FORCE=0
PROJECT_PATH=""

usage() {
  sed -n '1,80p' <<'EOF'
Usage: scripts/install-game-lfs.sh [--dry-run] [--no-lfs-install] [--force] <project-path>

Installs cuebert's LFS template into <project-path>.

Options:
  --dry-run          Show what would be changed without writing.
  --no-lfs-install   Skip 'git lfs install' (assume already done).
  --force            Replace an existing Cuebert LFS block (markers), or refresh install.
  -h, --help         Show this help.

Exits 0 on success, 1 on user error, 2 on environmental error.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --no-lfs-install) NO_LFS_INSTALL=1 ;;
    --force) FORCE=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      if [[ -n "${PROJECT_PATH}" ]]; then
        echo "Unexpected extra argument: $1" >&2
        exit 1
      fi
      PROJECT_PATH="$1"
      ;;
  esac
  shift
done

if [[ -z "${PROJECT_PATH}" ]]; then
  echo "Error: <project-path> is required." >&2
  usage >&2
  exit 1
fi

if [[ "${PROJECT_PATH}" == *".."* ]]; then
  echo "Error: project path must not contain '..'." >&2
  exit 1
fi

if [[ ! -d "${TEMPLATE%/*}" ]] || [[ ! -f "${TEMPLATE}" ]]; then
  echo "Error: template missing at ${TEMPLATE}" >&2
  exit 2
fi

if ! command -v git >/dev/null 2>&1; then
  echo "Error: git is not installed or not on PATH." >&2
  exit 2
fi

normalize_repo_path() {
  local p="$1"
  (cd "${p}" && pwd -P) || return 1
}

if ! NORM="$(normalize_repo_path "${PROJECT_PATH}")"; then
  echo "Error: not a directory or unreadable path: ${PROJECT_PATH}" >&2
  exit 1
fi

case "${NORM}" in
  /etc/*|/var/*)
    echo "Error: refusing to operate under /etc or /var: ${NORM}" >&2
    exit 1
    ;;
esac

if ! git -C "${NORM}" rev-parse --git-dir >/dev/null 2>&1; then
  echo "Error: ${NORM} is not a git repository." >&2
  exit 1
fi

if ! git lfs version >/dev/null 2>&1; then
  echo "Error: Git LFS is not installed. Install from https://git-lfs.com and retry." >&2
  exit 2
fi

warn_engine="unknown"
if compgen -G "${NORM}/*.uproject" >/dev/null 2>&1; then
  warn_engine="unreal"
elif [[ -f "${NORM}/ProjectSettings/ProjectVersion.txt" ]]; then
  warn_engine="unity"
elif [[ -f "${NORM}/project.godot" ]]; then
  warn_engine="godot"
else
  echo "Warning: no Unreal (*.uproject), Unity (ProjectSettings/ProjectVersion.txt), or Godot (project.godot) marker at repo root; proceeding anyway." >&2
fi
if [[ "${warn_engine}" != "unknown" ]]; then
  echo "Detected engine hint: ${warn_engine}" >&2
fi

extract_cuebert_block() {
  awk '/^# <<<BEGIN_CUEBERT_GAME_LFS_V1>>>$/,/^# <<<END_CUEBERT_GAME_LFS_V1>>>$/' "${TEMPLATE}"
}

ATTR_OUT="${NORM}/.gitattributes"
BEGIN_MARK='# <<<BEGIN_CUEBERT_GAME_LFS_V1>>>'
END_MARK='# <<<END_CUEBERT_GAME_LFS_V1>>>'

strip_old_block() {
  local f="$1"
  awk -v begin="${BEGIN_MARK}" -v end="${END_MARK}" '
    $0==begin {skip=1; next}
    $0==end {skip=0; next}
    skip==0 {print}
  ' "${f}"
}

has_cuebert_block() {
  [[ -f "$1" ]] && grep -qF "${BEGIN_MARK}" "$1"
}

append_block() {
  cat <<'BANNER'

# ==============================================================================
# Cuebert game LFS block (v1) — appended by scripts/install-game-lfs.sh
# ==============================================================================
BANNER
  extract_cuebert_block
}

if [[ -f "${ATTR_OUT}" ]] && grep -q 'filter=lfs' "${ATTR_OUT}"; then
  echo "Warning: ${ATTR_OUT} already contains filter=lfs rules; review for duplicates after install." >&2
fi

ALREADY_INSTALLED=0

if [[ ! -f "${ATTR_OUT}" ]]; then
  echo "Installing full template -> ${ATTR_OUT}"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] would copy ${TEMPLATE} to ${ATTR_OUT}"
  else
    cp "${TEMPLATE}" "${ATTR_OUT}"
  fi
elif has_cuebert_block "${ATTR_OUT}" && [[ "${FORCE}" -eq 0 ]]; then
  echo "${ATTR_OUT} already contains a Cuebert LFS block. Pass --force to replace it." >&2
  ALREADY_INSTALLED=1
elif has_cuebert_block "${ATTR_OUT}" && [[ "${FORCE}" -eq 1 ]]; then
  echo "Replacing existing Cuebert LFS block in ${ATTR_OUT} (--force)."
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] would strip old block and append fresh Cuebert block"
  else
    tmp="${ATTR_OUT}.tmp.$$"
    strip_old_block "${ATTR_OUT}" >"${tmp}"
    {
      cat "${tmp}"
      append_block
    } >"${ATTR_OUT}.new.$$"
    mv "${ATTR_OUT}.new.$$" "${ATTR_OUT}"
    rm -f "${tmp}"
  fi
else
  echo "Appending Cuebert LFS block to ${ATTR_OUT}"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] would append delimited Cuebert block"
  else
    {
      cat "${ATTR_OUT}"
      append_block
    } >"${ATTR_OUT}.new.$$"
    mv "${ATTR_OUT}.new.$$" "${ATTR_OUT}"
  fi
fi

if [[ "${ALREADY_INSTALLED}" -eq 1 ]]; then
  if [[ "${NO_LFS_INSTALL}" -eq 0 ]]; then
    if [[ "${DRY_RUN}" -eq 1 ]]; then
      echo "[dry-run] would run: git -C \"${NORM}\" lfs install"
    else
      git -C "${NORM}" lfs install
    fi
  fi
  echo ""
  echo "No .gitattributes changes needed."
  exit 0
fi

if [[ "${NO_LFS_INSTALL}" -eq 0 ]]; then
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[dry-run] would run: git -C \"${NORM}\" lfs install"
  else
    git -C "${NORM}" lfs install
  fi
else
  echo "Skipping git lfs install (--no-lfs-install)."
fi

echo ""
echo "Next steps (in ${NORM}):"
echo "  git add .gitattributes"
echo "  git commit -m \"chore: enable Git LFS for game assets (Cuebert template)\""
echo "  For files already tracked as normal blobs, see docs/_ai_system/standards/game-project-lfs.md (history rewrite section)."
echo ""
echo "Reference: ${HUB_ROOT}/docs/_ai_system/standards/game-project-lfs.md"

exit 0
