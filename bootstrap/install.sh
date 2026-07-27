#!/usr/bin/env bash
# OpenConcierge guided POSIX installer.
#
# Resolves a local source or release manifest, installs the OpenConcierge
# distribution or skill into a Hermes profile, and ends with passive checks.
# No network calls, no secret logging, no background processes.
#
# Exit codes:
#   0  success
#   2  user cancellation
#   3  command failure
#   4  registration failure

set -euo pipefail

PROFILE="openconcierge"
MODE="interactive"
SOURCE=""
SKILL_SOURCE=""
SOURCE_PROFILE="default"
CHANNEL="desktop"
REPAIR=0
ASSUME_YES=0
NO_DESKTOP=0
HERMES_BIN="${HERMES_BIN:-hermes}"

fail() {
  printf '%s\n' "$1" >&2
  exit "${2:-3}"
}

usage() {
  printf '%s\n' 'Usage: install.sh [--source PATH] [--skill-source URL] [--source-profile NAME] [--profile NAME] [--mode interactive|dedicated|existing] [--channel desktop|telegram] [--repair] [--yes] [--no-desktop]'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --source) SOURCE="$2"; shift 2 ;;
    --skill-source) SKILL_SOURCE="$2"; shift 2 ;;
    --source-profile) SOURCE_PROFILE="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --channel) CHANNEL="$2"; shift 2 ;;
    --repair) REPAIR=1; shift ;;
    --yes) ASSUME_YES=1; shift ;;
    --no-desktop) NO_DESKTOP=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown option: $1" 3 ;;
  esac
done

[ -n "$PROFILE" ] || fail "Profile name cannot be empty." 3
[ -n "$SOURCE_PROFILE" ] || fail "Source profile cannot be empty." 3

case "$MODE" in
  interactive|dedicated|existing) ;;
  *) fail "Invalid mode: $MODE. Use interactive, dedicated, or existing." 3 ;;
esac

case "$CHANNEL" in
  desktop|telegram) ;;
  *) fail "Invalid channel: $CHANNEL. Use desktop or telegram." 3 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

resolve_local_distribution() {
  if [ -n "$SOURCE" ]; then return; fi
  if [ -f "$SCRIPT_DIR/release.json" ]; then
    local value
    value="$(python3 - "$SCRIPT_DIR/release.json" <<'PY' 2>/dev/null || true
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
if not isinstance(data, dict):
    sys.exit(0)
dist = data.get("distribution_source")
if isinstance(dist, str) and dist:
    print(dist)
PY
)"
    if [ -n "$value" ]; then
      SOURCE="$value"
      return
    fi
  fi
  if [ -f "$REPO_ROOT/distribution.yaml" ]; then
    SOURCE="$REPO_ROOT"
  fi
}

resolve_skill_source() {
  if [ -n "$SKILL_SOURCE" ]; then return; fi
  if [ -f "$SCRIPT_DIR/release.json" ]; then
    local value
    value="$(python3 - "$SCRIPT_DIR/release.json" <<'PY' 2>/dev/null || true
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
if not isinstance(data, dict):
    sys.exit(0)
skill = data.get("skill_source")
if isinstance(skill, str) and skill:
    print(skill)
PY
)"
    if [ -n "$value" ]; then
      SKILL_SOURCE="$value"
    fi
  fi
}

resolve_local_distribution
resolve_skill_source

absolutize() {
  case "$1" in
    /*) printf '%s\n' "$1" ;;
    *) (cd "$1" 2>/dev/null && pwd) || printf '%s\n' "$1" ;;
  esac
}

if [ "$MODE" = "dedicated" ]; then
  if [ -z "$SOURCE" ]; then
    fail "No distribution source found. Pass --source PATH to a directory containing distribution.yaml." 3
  fi
  SOURCE="$(absolutize "$SOURCE")"
  [ -f "$SOURCE/distribution.yaml" ] || fail "Distribution source $SOURCE is missing distribution.yaml." 3
  [ -f "$SOURCE/skills/openconcierge/SKILL.md" ] || fail "Distribution source $SOURCE is missing skills/openconcierge/SKILL.md." 3
fi

if [ "$MODE" = "existing" ]; then
  if [ -z "$SKILL_SOURCE" ]; then
    fail "No skill source found. Pass --skill-source URL or a published skill identifier." 3
  fi
fi

if [ "$MODE" = "interactive" ]; then
  if [ "$ASSUME_YES" -eq 1 ] && [ ! -t 0 ]; then
    fail "Interactive mode requires a terminal. Pass --mode dedicated or --mode existing with --yes." 3
  fi
  printf 'Choose an installation mode:\n'
  printf '  1. Dedicated OpenConcierge profile\n'
  printf '  2. Add the OpenConcierge skill to an existing profile\n'
  printf 'Enter 1 or 2: '
  selection=""
  if [ -t 0 ]; then
    read -r selection
  else
    read -r selection || true
  fi
  case "$selection" in
    1) MODE="dedicated" ;;
    2) MODE="existing" ;;
    *) fail "Installation cancelled." 2 ;;
  esac
fi

has_hermes() {
  command -v "$HERMES_BIN" >/dev/null 2>&1
}

check_hermes() {
  "$HERMES_BIN" doctor >/dev/null
}

install_official_hermes() {
  local installer
  installer="$(mktemp)"
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    "https://hermes-agent.nousresearch.com/install.sh" \
    --output "$installer" || fail 'Could not download the official Hermes installer.' 3
  bash "$installer" || fail 'The official Hermes installer did not complete.' 3
  rm -f "$installer"
}

if ! has_hermes; then
  if [ "$ASSUME_YES" -eq 0 ] && [ -t 0 ]; then
    printf 'OpenConcierge needs Hermes to continue. Install Hermes now? [y/N] '
    confirm=""
    read -r confirm || true
    case "$confirm" in
      y|Y|yes|YES) ;;
      *) fail "Cancelled. Install Hermes from https://hermes-agent.nousresearch.com and re-run this installer." 2 ;;
    esac
  fi
  install_official_hermes
fi

if ! check_hermes; then
  fail "Hermes is installed but the local environment is unhealthy. Run 'hermes doctor' for details." 3
fi

registration_failed() {
  fail "Hermes did not register the expected profile or skill. Re-run with --repair --yes to refresh an existing OpenConcierge profile." 4
}

if [ "$MODE" = "dedicated" ]; then
  if "$HERMES_BIN" profile create "$PROFILE" --clone-from "$SOURCE_PROFILE"; then
    "$HERMES_BIN" profile install "$SOURCE" --name "$PROFILE" --alias --force --yes
  else
    create_status=$?
    if [ "$REPAIR" -eq 1 ] && [ "$ASSUME_YES" -eq 1 ]; then
      "$HERMES_BIN" profile update "$PROFILE" --yes
    else
      fail "Profile '$PROFILE' already exists. Re-run with --repair --yes to refresh it, or pick a different --profile name." 2
    fi
  fi
  if ! "$HERMES_BIN" profile show "$PROFILE" >/dev/null; then
    registration_failed
  fi
  skills_output="$("$HERMES_BIN" -p "$PROFILE" skills list --source all --enabled-only || true)"
  case "$skills_output" in
    *openconcierge*) ;;
    *) registration_failed ;;
  esac
elif [ "$MODE" = "existing" ]; then
  "$HERMES_BIN" profile show "$PROFILE" >/dev/null
  "$HERMES_BIN" -p "$PROFILE" skills install "$SKILL_SOURCE" --name openconcierge --yes
  skills_output="$("$HERMES_BIN" -p "$PROFILE" skills list --source all --enabled-only || true)"
  case "$skills_output" in
    *openconcierge*) ;;
    *) registration_failed ;;
  esac
fi

if [ "$CHANNEL" = "telegram" ]; then
  printf 'Telegram setup for the new OpenConcierge profile:\n'
  printf '  1. Open Hermes Desktop and sign in to the new profile.\n'
  printf '  2. Go to Gateway -> Telegram in Hermes Desktop.\n'
  printf '  3. Create a new bot token for this profile. Do not reuse an active token from another profile.\n'
  printf 'The installer does not start a gateway; Hermes handles that step.\n'
  exit 0
fi

tools_output="$("$HERMES_BIN" tools list --platform cli || true)"
search_signal=0
search_signal_text="$(printf '%s' "$tools_output" | tr '[:upper:]' '[:lower:]')"
for keyword in web search mcp exa tavily brave duckduckgo serp firecrawl searx parallel xai; do
  case "$search_signal_text" in
    *"$keyword"*) search_signal=1 ;;
  esac
done
if [ "$search_signal" -eq 0 ]; then
  printf 'No compatible web search tool was detected for this profile. Open Hermes Desktop and configure a search integration (Tools, Skills, or MCP) before asking OpenConcierge to research products.\n' >&2
fi

if [ "$NO_DESKTOP" -eq 0 ]; then
  if ! "$HERMES_BIN" -p "$PROFILE" desktop; then
    fail "Could not launch Hermes Desktop for profile '$PROFILE'. Run 'hermes -p $PROFILE desktop' manually." 3
  fi
fi

exit 0
