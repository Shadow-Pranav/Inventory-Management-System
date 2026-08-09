up:        ; docker compose up --build
down:      ; docker compose down
reset:     ; docker compose down -v && docker compose up --build
sh:        ; docker compose exec web bash
mm:        ; docker compose exec web python manage.py makemigrations
migrate:   ; docker compose exec web python manage.py migrate
test:      ; docker compose exec web pytest -q
lint:      ; docker compose exec web ruff check . --fix && docker compose exec web ruff format .
seed:      ; docker compose exec web python manage.py seed_demo
async:     ; docker compose --profile async up -d worker beat
psql:      ; docker compose exec db psql -U sits -d sits
