IMAGE ?= heart-api:1.0.0

.PHONY: setup data eda train test lint serve mlflow-ui docker-build docker-run smoke k8s-deploy monitor-up

setup:        ## create venv and install everything
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt

data:         ## download + clean dataset
	python -m heart.download

eda:          ## generate EDA figures into reports/figures
	python -m heart.eda

train:        ## train, track in MLflow, export best model
	python -m heart.train

test:
	pytest -v --cov=heart --cov=app

lint:
	ruff check . && ruff format --check .

serve:
	uvicorn app.main:app --reload --port 8000

mlflow-ui:
	mlflow ui --backend-store-uri ./mlruns --port 5000

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run --rm -p 8000:8000 --name heart-api $(IMAGE)

smoke:        ## hit the running API with the sample payload
	curl -s -X POST localhost:8000/predict -H 'Content-Type: application/json' -d @sample_request.json

k8s-deploy:   ## minikube: load image + apply manifests
	minikube image load $(IMAGE)
	kubectl apply -f k8s/
	kubectl -n heart-mlops rollout status deploy/heart-api

monitor-up:   ## API + Prometheus + Grafana via docker compose
	docker compose -f monitoring/docker-compose.yml up --build -d
