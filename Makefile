PYTHON ?= python3
export PYTHONPATH := src

.PHONY: test lint demo clean

test:
	$(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m compileall -q -x 'templates' src tests

demo:
	$(PYTHON) -m forgel demo --home .forgel-demo

clean:
	rm -rf .forgel-demo .venv
