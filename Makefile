.PHONY: setup run install teardown

setup: install run

install:
	poetry install

run:
	poetry run python3 src/app/app.py

teardown:
	@echo "Nothing to teardown. If you opened 'poetry shell' manually, type 'exit'."
