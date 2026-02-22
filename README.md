## Before start ##

1. register deye account at [developer.deyecloud.com](https://developer.deyecloud.com/) 
2. register deye application
3. create a telegram bot using `@botfather`
4. execute `cp .env.sample .env`
5. fill in the `.env` file with the deye account, application id and secret
6. in `.env` file, fill in the `TG_HOOK_BASE_URL` setting with the url accessible from the internet

## To start locally ##
1. execute `cd front-end`, `pip install -r requirements.txt` and `python run.py`
2. execute `cd back-end`, `npm i` and `npm run dev`
3. open `http://localhost:5127` in your web-browser

## To deploy in docker ##
0. if there is no `db.sqlite3` file in `back-end` folder, create an empty file
1. in `.env` file, set `DEBUG` to `False`
2. execute `sudo docker compose up -d`

## Docker cheatsheet ##

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs (all / specific service)
docker compose logs -f
docker compose logs -f svitlo-power-back-end

# Restart a service
docker compose restart svitlo-power-back-end

# Rebuild and restart a service
docker compose up -d --build svitlo-power-back-end

# Run a single service standalone (with dependencies)
docker compose up -d svitlo-power-back-end

# Run a single service without dependencies
docker compose up -d --no-deps svitlo-power-grid-reporter

# Shell into a running container
docker compose exec svitlo-power-back-end bash

# Check service status
docker compose ps
```

**Services:** `svitlo-power-back-end`, `svitlo-power-sse-back-end`, `svitlo-power-front-end`, `svitlo-power-grid-reporter`, `svitlo-power-mongo`, `svitlo-power-rds`

### Development

## Database

When the database changes are required to be made, always create a migration using the following command: `beanie.exe new-migration -n <migration_name> -p migrations`

Then, execute the migration using command
`beanie.exe migrate -uri <db_uri> -db <db_name> -p migrations/ --no-use-transaction`