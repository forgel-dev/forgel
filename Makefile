PYTHON ?= python3
CLI_PIP ?= $(HOME)/.forgel-cli/bin/pip
export PYTHONPATH := src

.PHONY: test lint demo chat clean e2e-blog install-cli

test:
	$(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m compileall -q -x 'templates' src tests

demo:
	$(PYTHON) -m forgel demo --home .forgel-demo

# Local console: the same commands as Telegram, no bot token and no server.
chat:
	$(PYTHON) -m forgel chat --home .forgel-demo

# Manual, free harness check. The bridge/API modes are documented in
# tests/e2e/README.md and are run only on explicit instruction.
e2e-blog:
	$(PYTHON) tests/e2e/run_blog_e2e.py --mode script --strict

clean:
	rm -rf .forgel-demo .venv

# The self-hosting CLI runs from its own non-editable copy: the coding agent
# edits src/forgel while the daemon works, so a live import would load
# half-edited modules and break the running console. Build from the committed
# tree, never install with -e.
install-cli:
	@tmp=$$(mktemp -d); \
	trap 'rm -rf "$$tmp"' EXIT; \
	git archive HEAD | tar -x -C "$$tmp"; \
	$(CLI_PIP) uninstall -y forgel >/dev/null 2>&1 || true; \
	$(CLI_PIP) install --no-build-isolation "$$tmp[github,tokens]"
