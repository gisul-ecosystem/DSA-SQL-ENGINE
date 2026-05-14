# Observability

This directory contains the lightweight Prometheus/Grafana setup for the execution engine.

## Services

- Grafana: `http://localhost:8001`

Grafana defaults to `admin/admin` unless `GRAFANA_ADMIN_USER` and
`GRAFANA_ADMIN_PASSWORD` are set.

## Metrics Targets

- API: `api:8000/metrics`
- Worker: `worker:9101/metrics`

## Traces

Tracing is disabled by default in the lightweight deployment with
`OTEL_SDK_DISABLED=true`. Re-enable Tempo only after the API/worker path is
stable.

## Logs

The API and worker write JSON logs to stdout. View them with
`docker compose logs api worker`. Logs include operational fields such as
`service`, `language`, `mode`, `verdict`, and `job_id` where available. Source
code, stdin, stdout, stderr, and full request payloads are intentionally not
logged.

## Dashboards And Alerts

Grafana provisions the `Execution Engine Overview` dashboard from
`grafana/dashboards/execution-engine-overview.json`.

Prometheus loads alert rules from `alerts.yml` for high API error rates, high
queue depth, high queue wait, worker stalls, Redis availability, low warm-pool
hit rate, and elevated runtime errors.
