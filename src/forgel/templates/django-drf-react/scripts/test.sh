#!/bin/sh
# Run the Django test suite of the API project.
#
# environment.yaml has no working directory of its own, so its `test` command
# is this wrapper: enter api/ and run `python manage.py test`. The suite needs
# neither a Postgres server nor object storage (settings fall back to SQLite).
set -e
cd "$(dirname "$0")/../api"
exec python manage.py test "$@"
