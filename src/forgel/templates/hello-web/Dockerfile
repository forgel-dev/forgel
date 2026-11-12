FROM python:3.12-slim

WORKDIR /app

COPY api ./api
COPY web ./web

EXPOSE 8000

CMD ["python", "api/app.py", "--host", "0.0.0.0"]
