.PHONY: db install seed run reset demo

db:
	docker compose up -d db

install:
	pip install -r requirements.txt

seed:
	python -m app.seed.run

run:
	uvicorn app.main:app --reload --port 8000

reset:
	python -m app.seed.run --drop

demo:
	curl -s -X POST localhost:8000/api/v1/leads/3613790/score | python -m json.tool
