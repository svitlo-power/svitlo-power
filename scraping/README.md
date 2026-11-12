# Local metrics

Start the application services first so the `svitlo-power_web_network` Docker
network and their metrics endpoints exist. Then start Prometheus and Grafana:

```powershell
docker compose -f scraping\docker-compose.yml up -d
```

- Grafana: http://localhost:3000 (default login: `admin` / `admin`)
- Prometheus: http://localhost:9090

Prometheus scrapes `/metrics` from the backend services on the shared Docker
network every 15 seconds. The grid reporter uses port `9099`; the three FastAPI
services use their container HTTP port `5005`. Redis and host/container
exporters are intentionally not included.

The scheduler runs in `svitlo-power-back-end` and publishes
`job_execution_success_total`, `job_execution_failure_total`, and
`job_execution_duration_seconds`. Success and duration series are initialized
for registered jobs at scheduler startup. Failure series start at zero and
increase when a job fails or is missed. Ownership-change and next-run metrics
are not published.

Stop only the monitoring services with:

```powershell
docker compose -f scraping\docker-compose.yml down
```

Prometheus history and Grafana settings persist in named Docker volumes. Add
`-v` to `down` only if you also want to remove those stored data volumes.
