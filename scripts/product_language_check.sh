#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASCII_TERM="inter""view"
UNICODE_TERM=$'\u9762\u8bd5'

cd "$ROOT_DIR"

content_matches="$(git grep -n -i -e "$ASCII_TERM" -e "$UNICODE_TERM" -- . || true)"
if [[ -n "$content_matches" ]]; then
  printf '%s\n' "[product-language-check] disallowed product framing found in tracked content"
  printf '%s\n' "$content_matches"
  exit 1
fi

message_matches="$(git log --all --format='%H%x09%s%n%b' | grep -inE "${ASCII_TERM}|${UNICODE_TERM}" || true)"
if [[ -n "$message_matches" ]]; then
  printf '%s\n' "[product-language-check] disallowed product framing found in commit messages"
  printf '%s\n' "$message_matches"
  exit 1
fi

printf '%s\n' "[product-language-check] tracked content and commit messages are clean"
