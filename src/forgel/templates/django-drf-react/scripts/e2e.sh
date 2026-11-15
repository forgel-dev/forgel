#!/bin/sh
# Run the isolated-stand e2e QA scenario.
#
# environment.yaml has no working directory of its own, so its `e2e` command is
# this wrapper: it builds the QA stack, brings up api, postgres, object storage
# and web on an internal network (no host port is published), runs the
# headless-browser scenario from qa/ and tears the stand down again. `set -e`
# makes the wrapper exit non-zero as soon as a step fails.
set -e

cd "$(dirname "$0")/.."

compose="docker compose -f docker/docker-compose.qa.yml"

cleanup() {
  $compose --profile qa down --volumes --remove-orphans
}
trap cleanup EXIT INT TERM

$compose build
$compose up --detach --wait api postgres minio web
$compose --profile qa run --rm qa

echo "e2e: the isolated QA stand passed"
