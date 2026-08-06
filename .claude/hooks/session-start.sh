#!/bin/bash
# SessionStart hook: install the ui-ux-pro-max skill into the user skills dir.
#
# Claude Code on the web resets the container's home directory between
# sessions, so a `~/.claude/skills` install does not survive. This hook
# reinstalls the skill on every session start so it is always available.
#
# The upstream repo stores the skill's data/ and scripts/ as symlinks into
# src/ui-ux-pro-max/, so the copy dereferences them (cp -rL) to leave a
# self-contained skill directory behind.
#
# Never fails the session: every failure path exits 0.
set -uo pipefail

SKILL_NAME="ui-ux-pro-max"
UPSTREAM="https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git"
DEST="${HOME}/.claude/skills/${SKILL_NAME}"

# Only needed in the ephemeral web container; local installs persist already.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Idempotent: skip when a previous run already installed it.
if [ -f "${DEST}/SKILL.md" ] && [ -d "${DEST}/data" ] && [ -d "${DEST}/scripts" ]; then
  echo "${SKILL_NAME}: already installed"
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

if ! git clone --depth 1 --quiet "${UPSTREAM}" "${TMP}/src" 2>/dev/null; then
  echo "${SKILL_NAME}: clone failed, skipping install" >&2
  exit 0
fi

SRC="${TMP}/src/.claude/skills/${SKILL_NAME}"
if [ ! -f "${SRC}/SKILL.md" ]; then
  echo "${SKILL_NAME}: unexpected upstream layout, skipping install" >&2
  exit 0
fi

mkdir -p "${HOME}/.claude/skills" || exit 0
rm -rf "${DEST}"
if cp -rL "${SRC}" "${DEST}" 2>/dev/null; then
  echo "${SKILL_NAME}: installed to ${DEST}"
else
  echo "${SKILL_NAME}: copy failed, skipping install" >&2
fi

exit 0
