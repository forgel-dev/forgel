# django-drf-react template: `docker compose up --build` evidence

The unittest suite never starts Docker (constraint), so the local stand is run
by the coding agent. The `Output` section below is the actual output captured on
the coding host (Docker Compose v5.3.1) while writing this report.

## Command

Run from the repository root:

```sh
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react --env-file src/forgel/templates/django-drf-react/.env.example up --build -d
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react ps
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react logs --no-color api
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react exec -T api python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/healthz'); print(r.status, r.read().decode())"
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react exec -T postgres psql -U app -d app -c 'select 1;'
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react logs --no-color --tail=6 api
docker compose -f src/forgel/templates/django-drf-react/compose.yaml --project-directory src/forgel/templates/django-drf-react down -v
```

## Output

Build log lines are verbatim; `...` marks an elided run of pip download lines.

```text
$ docker compose ... up --build -d
#1 [internal] load local bake definitions
#1 reading from stdin 628B done
#1 DONE 0.0s

#2 [internal] load build definition from Dockerfile
#2 transferring dockerfile: 411B 0.0s done
#2 DONE 0.0s

#3 [internal] load metadata for docker.io/library/python:3.12-slim
#3 DONE 0.0s

#4 [internal] load .dockerignore
#4 transferring context: 91B done
#4 DONE 0.0s

#5 [1/7] FROM docker.io/library/python:3.12-slim
#5 DONE 0.0s

#6 [2/7] WORKDIR /app
#6 CACHED

#7 [internal] load build context
#7 transferring context: 9.23kB done
#7 DONE 0.0s

#8 [3/7] COPY api/requirements.txt /app/requirements.txt
#8 DONE 0.0s

#9 [4/7] RUN pip install --no-cache-dir -r /app/requirements.txt
#9 2.735 Collecting Django==5.2.7 (from -r /app/requirements.txt (line 1))
#9 2.997   Downloading django-5.2.7-py3-none-any.whl.metadata (4.1 kB)
#9 3.198 Collecting djangorestframework==3.16.1 (from -r /app/requirements.txt (line 2))
#9 3.269   Downloading djangorestframework-3.16.1-py3-none-any.whl.metadata (11 kB)
#9 3.351 Collecting psycopg==3.2.10 (from psycopg[binary]==3.2.10->-r /app/requirements.txt (line 3))
#9 3.417   Downloading psycopg-3.2.10-py3-none-any.whl.metadata (4.6 kB)
#9 3.509 Collecting django-storages==1.14.6 (from -r /app/requirements.txt (line 4))
#9 3.574   Downloading django_storages-1.14.6-py3-none-any.whl.metadata (4.7 kB)
#9 4.267 Collecting boto3==1.40.50 (from -r /app/requirements.txt (line 5))
#9 4.348   Downloading boto3-1.40.50-py3-none-any.whl.metadata (6.7 kB)
...
#9 21.18 Successfully installed Django-5.2.7 asgiref-3.13.0 boto3-1.40.50 botocore-1.40.76 django-storages-1.14.6 djangorestframework-3.16.1 jmespath-1.1.0 psycopg-3.2.10 psycopg-binary-3.2.10 python-dateutil-2.9.0.post0 s3transfer-0.14.0 six-1.17.0 sqlparse-0.6.1 typing-extensions-4.16.0 urllib3-2.8.0
#9 21.18 WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager, possibly rendering your system unusable. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv. Use the --root-user-action option if you know what you are doing and want to suppress this warning.
#9 21.51
#9 21.51 [notice] A new release of pip is available: 25.0.1 -> 26.3
#9 21.51 [notice] To update, run: pip install --upgrade pip
#9 DONE 21.9s

#10 [5/7] COPY api/ /app/
#10 DONE 0.0s

#11 [6/7] COPY docker/ /app/docker/
#11 DONE 0.0s

#12 [7/7] RUN chmod +x /app/docker/entrypoint.sh
#12 DONE 0.2s

#13 exporting to image
#13 exporting layers
#13 exporting layers 1.6s done
#13 writing image sha256:c8679448285104b32937462b4bd6d90e663d6d59a064f525f6c3267cff219fc7 done
#13 naming to docker.io/library/django-drf-react-api done
#13 DONE 1.6s

#14 resolving provenance for metadata file
#14 DONE 0.0s
 Image django-drf-react-api Building
 Image django-drf-react-api Built
 Network django-drf-react_default Creating
 Network django-drf-react_default Created
 Volume django-drf-react_postgres-data Creating
 Volume django-drf-react_postgres-data Created
 Volume django-drf-react_minio-data Creating
 Volume django-drf-react_minio-data Created
 Container django-drf-react-postgres-1 Creating
 Container django-drf-react-minio-1 Creating
 Container django-drf-react-postgres-1 Created
 Container django-drf-react-minio-1 Created
 Container django-drf-react-api-1 Creating
 Container django-drf-react-api-1 Created
 Container django-drf-react-postgres-1 Starting
 Container django-drf-react-minio-1 Starting
 Container django-drf-react-minio-1 Started
 Container django-drf-react-postgres-1 Started
 Container django-drf-react-postgres-1 Waiting
 Container django-drf-react-minio-1 Waiting
 Container django-drf-react-minio-1 Healthy
 Container django-drf-react-postgres-1 Healthy
 Container django-drf-react-api-1 Starting
 Container django-drf-react-api-1 Started

$ docker compose ... ps
NAME                          IMAGE                        COMMAND                  SERVICE    CREATED          STATUS                    PORTS
django-drf-react-api-1        django-drf-react-api         "/app/docker/entrypo…"   api        10 seconds ago   Up 4 seconds              0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
django-drf-react-minio-1      bitnamilegacy/minio:latest   "/opt/bitnami/script…"   minio      10 seconds ago   Up 10 seconds (healthy)   0.0.0.0:9000-9001->9000-9001/tcp, [::]:9000-9001->9000-9001/tcp
django-drf-react-postgres-1   postgres:16-alpine           "docker-entrypoint.s…"   postgres   10 seconds ago   Up 10 seconds (healthy)   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp

$ docker compose ... logs --no-color api
api-1  | Operations to perform:
api-1  |   Apply all migrations: auth, contenttypes
api-1  | Running migrations:
api-1  |   Applying contenttypes.0001_initial... OK
api-1  |   Applying contenttypes.0002_remove_content_type_name... OK
api-1  |   Applying auth.0001_initial... OK
api-1  |   Applying auth.0002_alter_permission_name_max_length... OK
api-1  |   Applying auth.0003_alter_user_email_max_length... OK
api-1  |   Applying auth.0004_alter_user_username_opts... OK
api-1  |   Applying auth.0005_alter_user_last_login_null... OK
api-1  |   Applying auth.0006_require_contenttypes_0002... OK
api-1  |   Applying auth.0007_alter_validators_add_error_messages... OK
api-1  |   Applying auth.0008_alter_user_username_max_length... OK
api-1  |   Applying auth.0009_alter_user_last_name_max_length... OK
api-1  |   Applying auth.0010_alter_group_name_max_length... OK
api-1  |   Applying auth.0011_update_proxy_permissions... OK
api-1  |   Applying auth.0012_alter_user_first_name_max_length... OK
api-1  | bucket 'app-media' is ready

$ docker compose ... exec -T api python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/healthz'); print(r.status, r.read().decode())"
200 {"status":"ok"}

$ docker compose ... exec -T postgres psql -U app -d app -c 'select 1;'
 ?column?
----------
        1
(1 row)

$ docker compose ... logs --no-color --tail=6 api
api-1  | Starting development server at http://0.0.0.0:8000/
api-1  | Quit the server with CONTROL-C.
api-1  |
api-1  | WARNING: This is a development server. Do not use it in a production setting. Use a production WSGI or ASGI server instead.
api-1  | For more information on production servers see: https://docs.djangoproject.com/en/5.2/howto/deployment/
api-1  | [15/Nov/2026 09:26:52] "GET /healthz HTTP/1.1" 200 15

$ docker compose ... down -v
 Container django-drf-react-api-1 Stopping
 Container django-drf-react-api-1 Stopped
 Container django-drf-react-api-1 Removing
 Container django-drf-react-api-1 Removed
 Container django-drf-react-minio-1 Stopping
 Container django-drf-react-postgres-1 Stopping
 Container django-drf-react-minio-1 Stopped
 Container django-drf-react-minio-1 Removing
 Container django-drf-react-minio-1 Removed
 Container django-drf-react-postgres-1 Stopped
 Container django-drf-react-postgres-1 Removing
 Container django-drf-react-postgres-1 Removed
 Network django-drf-react_default Removing
 Volume django-drf-react_postgres-data Removing
 Volume django-drf-react_minio-data Removing
 Volume django-drf-react_postgres-data Removed
 Volume django-drf-react_minio-data Removed
 Network django-drf-react_default Removed
```

## What the output shows

- `docker compose ps` lists `api`, `postgres` and `minio`; Postgres and MinIO are
  `(healthy)` and the API publishes `0.0.0.0:8000->8000/tcp`.
- The API log shows `migrate` applying the `contenttypes` and `auth` migrations.
  Those tables only exist in the Postgres service named by `POSTGRES_HOST` /
  `POSTGRES_DB` / `POSTGRES_USER`, so a green migration is the Postgres
  connection in action.
- `bucket 'app-media' is ready` is `api/config/bucket.py` creating the bucket
  named by `S3_BUCKET` in MinIO on startup.
- The in-container request returns `200 {"status":"ok"}` and the API access log
  records `"GET /healthz HTTP/1.1" 200 15`.
- `psql -U app -d app -c 'select 1;'` inside the `postgres` service returns one
  row.

## Object-storage image note

The first attempt used the Docker Hub tag `minio/minio:latest`, which this
registry now rejects (`pull access denied for minio/minio, repository does not
exist or may require 'docker login'`), and `quay.io/minio/minio:latest` answered
`unauthorized`. The compose file therefore takes the server image from
`MINIO_IMAGE` (default `bitnamilegacy/minio:latest`, which serves the same S3
API and still ships `mc` and `curl`); the run above uses that default. Pin or
mirror it through `MINIO_IMAGE` in `.env` for another registry.

Status: **confirmed** - captured on the coding host with Docker Compose v5.3.1;
the block above is that run's output.
