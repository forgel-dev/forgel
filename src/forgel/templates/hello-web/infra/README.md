# Infrastructure: hello-web (M0)

The M0 skeleton uses a **local provider**. There are no cloud resources yet.

- The generated API binds to `127.0.0.1`.
- The static frontend is served by the API process.
- `staging.json` describes how to start it.

A real provider plugin (`provider-yandex`) arrives in M1. It will implement
`plan`, `apply`, `verify`, `rollback`, `destroy` and `observe`.
