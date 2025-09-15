.PHONY: setup run install teardown

setup: install run

install:
	poetry install

run:
	poetry run python3 src/app/app.py

teardown:
	@echo "Nothing to teardown. If you opened 'poetry shell' manually, type 'exit'."

web: install
	poetry run streamlit run src/app/app.py --server.port 8501 --server.address 0.0.0.0


docker:
	docker build -t classics-app .
	docker run classics-app
