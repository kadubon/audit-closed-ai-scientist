PYTHON ?= python

.PHONY: reproduce quick benchmark figures test security

reproduce:
	$(PYTHON) run_all_experiments.py --profile standard

quick:
	$(PYTHON) run_all_experiments.py --profile quick

benchmark:
	$(PYTHON) scripts/run_benchmark_only.py --runs 320 --seed 2030 --output results/benchmark_only.json

figures:
	$(PYTHON) regenerate_figures.py --input results/experiment_results.json --output-dir figures

test:
	$(PYTHON) -m unittest discover -s tests -p "test_*.py"

security: test
