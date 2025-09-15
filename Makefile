.PHONY: setup run install teardown

setup: install run

install:
	poetry install

run:
	poetry run python3 src/app/app.py

teardown:
	@echo "Nothing to teardown. If you opened 'poetry shell' manually, type 'exit'."

web: 
	poetry run streamlit run src/app/app.py

docker:
	docker build -t classics-app .
	docker run classics-app

check:
	poetry run black --check .
	# poetry run isort --check-only .
	# poetry run flake8 .


fix: 
	# Remove unused imports/vars first (optional; comment out if you don't use autoflake)
	# poetry run autoflake --in-place --remove-all-unused-imports --recursive .
	# poetry run isort .
	poetry run black .
	# poetry run flake8 .

test: 
	poetry run pytest -q