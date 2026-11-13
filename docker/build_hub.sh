#!/bin/bash
set -ex

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE_NAME="scheduler-mgr-hub"
IMAGE_TAG="latest"

while getopts "n:t:" opt; do
  case $opt in
    n) IMAGE_NAME="$OPTARG" ;;
    t) IMAGE_TAG="$OPTARG" ;;
    *) echo "Usage: $0 [-n image_name] [-t image_tag]" && exit 1 ;;
  esac
done

docker build \
  -f "$SCRIPT_DIR/hub.Dockerfile" \
  -t "$IMAGE_NAME:$IMAGE_TAG" \
  "$PROJECT_ROOT"
