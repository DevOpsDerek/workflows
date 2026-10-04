#!/usr/bin/env bash
set -euo pipefail

workspace="$(cd -- "$WORKSPACE_ROOT" && pwd -P)"
case "$PATH_KIND" in
  file|directory) ;;
  *)
    echo "::error::Path kind must be 'file' or 'directory'."
    exit 1
    ;;
esac
case "$REPOSITORY_PATH" in
  ""|/*|*$'\n'*)
    echo "::error::$PATH_NAME must be a non-empty repository-relative path."
    exit 1
    ;;
esac
case "/$REPOSITORY_PATH/" in
  *"/../"*)
    echo "::error::$PATH_NAME must not contain parent-directory components."
    exit 1
    ;;
esac
if ! resolved="$(realpath "$workspace/$REPOSITORY_PATH")"; then
  echo "::error::$PATH_NAME does not exist."
  exit 1
fi
case "$resolved/" in
  "$workspace/"*) ;;
  *)
    echo "::error::$PATH_NAME must resolve inside the checked-out repository."
    exit 1
    ;;
esac
if [[ "$PATH_KIND" == file && ! -f "$resolved" ]]; then
  echo "::error::$PATH_NAME must be a file."
  exit 1
elif [[ "$PATH_KIND" == directory && ! -d "$resolved" ]]; then
  echo "::error::$PATH_NAME must be a directory."
  exit 1
fi
printf 'absolute-path=%s\n' "$resolved" >> "$GITHUB_OUTPUT"
