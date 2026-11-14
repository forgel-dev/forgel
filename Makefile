PYTHON ?= python3
export PYTHONPATH := src

.PHONY: test lint demo clean e2e-blog

test:
	$(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m compileall -q -x 'templates' src tests

demo:
	$(PYTHON) -m forgel demo --home .forgel-demo

# Manual, free harness check. The bridge/API modes are documented in
# tests/e2e/README.md and are run only on explicit instruction.
e2e-blog:
	$(PYTHON) tests/e2e/run_blog_e2e.py --mode script --strict

clean:
	rm -rf .forgel-demo .venv
