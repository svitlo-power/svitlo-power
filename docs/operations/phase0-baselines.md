# Phase 0 Baseline Measurement Guide

This document describes how to measure and document baselines for Phase 0 exit criteria.

## Required Baselines (7 Days Production)

Per the migration plan, the following baselines must be measured over 7 days of production traffic:

| Metric | Baseline Target | Measurement Method |
|--------|-----------------|-------------------|
| Dashboard API p99 latency | < 500ms | Prometheus histogram `http_request_duration_seconds` |
| Dashboard API error rate | < 0.1% | Prometheus counter `http_requests_total` with status >= 500 |
| SSE connection count | Baseline recorded | Prometheus gauge `sse_connections_active` |
| Scheduled job success rate | 100% | Prometheus counters `job_execution_success_total` / `job_execution_failure_total` |
| Snapshot freshness (legacy) | < 30s | Custom metric from dashboard service |

## Measurement Procedure

### 1. Enable Metrics Collection

Ensure all services have Prometheus metrics endpoint exposed:

```yaml
# docker-compose.yml additions
services:
  back-end:
    ports:
      - "9090:9090"  # Prometheus metrics
  app-back-end:
    ports:
      - "9091:9091"
  sse-back-end:
    ports:
      - "9092:9092"
  grid-reporter:
    ports:
      - "9093:9093"
```

### 2. Prometheus Configuration

Add scrape configs to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'back-end'
    static_configs:
      - targets: ['back-end:9090']
  - job_name: 'app-back-end'
    static_configs:
      - targets: ['app-back-end:9091']
  - job_name: 'sse-back-end'
    static_configs:
      - targets: ['sse-back-end:9092']
  - job_name: 'grid-reporter'
    static_configs:
      - targets: ['grid-reporter:9093']
```

### 3. Key Queries for Baseline Measurement

#### Dashboard API p99 Latency
```promql
histogram_quantile(0.99, 
  sum(rate(http_request_duration_seconds_bucket{job=~"back-end|app-back-end",handler=~"/api/dashboard/.*"}[5m])) by (le)
)
```

#### Dashboard API Error Rate
```promql
sum(rate(http_requests_total{job=~"back-end|app-back-end",handler=~"/api/dashboard/.*",status=~"5.."}[5m]))
/
sum(rate(http_requests_total{job=~"back-end|app-back-end",handler=~"/api/dashboard/.*"}[5m]))
```

#### SSE Connection Count
```promql
sum(sse_connections_active{job=~"back-end|sse-back-end|app-back-end"})
```

#### Scheduled Job Success Rate
```promql
sum(rate(job_execution_success_total[5m]))
/
(sum(rate(job_execution_success_total[5m])) + sum(rate(job_execution_failure_total[5m])))
```

#### Legacy Snapshot Freshness
```promql
# From back-end dashboard service
time() - dashboard_snapshot_generated_at_timestamp
```

### 4. Data Collection Script

Run this script daily to collect baseline data:

```bash
#!/bin/bash
# collect-baselines.sh

OUTPUT_DIR="baselines/$(date +%Y-%m-%d)"
mkdir -p "$OUTPUT_DIR"

# Dashboard API p99 latency
curl -s "http://prometheus:9090/api/v1/query?query=histogram_quantile(0.99,sum(rate(http_request_duration_seconds_bucket{job=~\"back-end|app-back-end\",handler=~\"/api/dashboard/.*\"}[5m]))by(le))" \
  > "$OUTPUT_DIR/dashboard_p99_latency.json"

# Dashboard API error rate
curl -s "http://prometheus:9090/api/v1/query?query=sum(rate(http_requests_total{job=~\"back-end|app-back-end\",handler=~\"/api/dashboard/.*\",status=~\"5..\"}[5m]))/sum(rate(http_requests_total{job=~\"back-end|app-back-end\",handler=~\"/api/dashboard/.*\"}[5m]))" \
  > "$OUTPUT_DIR/dashboard_error_rate.json"

# SSE connection count
curl -s "http://prometheus:9090/api/v1/query?query=sum(sse_connections_active{job=~\"back-end|sse-back-end|app-back-end\"})" \
  > "$OUTPUT_DIR/sse_connections.json"

# Job success rate
curl -s "http://prometheus:9090/api/v1/query?query=sum(rate(job_execution_success_total[5m]))/(sum(rate(job_execution_success_total[5m]))+sum(rate(job_execution_failure_total[5m])))" \
  > "$OUTPUT_DIR/job_success_rate.json"

# Snapshot freshness
curl -s "http://prometheus:9090/api/v1/query?query=time()-dashboard_snapshot_generated_at_timestamp" \
  > "$OUTPUT_DIR/snapshot_freshness.json"

echo "Baseline data collected to $OUTPUT_DIR"
```

### 5. Baseline Report Template

After 7 days, compile results into a report:

```markdown
# Phase 0 Baseline Report

**Measurement Period**: YYYY-MM-DD to YYYY-MM-DD
**Environment**: Production
**Services**: back-end, app-back-end, sse-back-end, grid-reporter

## Results

| Metric | Target | Measured | Pass/Fail |
|--------|--------|----------|-----------|
| Dashboard API p99 latency | < 500ms | XXXms | PASS/FAIL |
| Dashboard API error rate | < 0.1% | X.XX% | PASS/FAIL |
| SSE connection count | Recorded | XXX | N/A |
| Scheduled job success rate | 100% | XX.X% | PASS/FAIL |
| Snapshot freshness (legacy) | < 30s | XXs | PASS/FAIL |

## Observations

- [ ] All targets met
- [ ] Anomalies observed: (describe)
- [ ] Recommendations for threshold adjustments: (if any)

## Sign-off

- [ ] Platform Engineer: _______________
- [ ] Tech Lead: _______________
- [ ] Date: _______________
```

### 6. Grafana Dashboard

Create a dashboard with these panels:

1. **Dashboard API Latency (p50, p95, p99)** - Time series
2. **Dashboard API Error Rate** - Time series
3. **SSE Connections** - Time series (public vs private)
4. **Scheduled Job Success/Failure** - Time series
5. **Snapshot Freshness** - Time series
6. **Redis Operations** - Time series (latency, errors)
7. **Feature Flag Status** - Table (current state of all flags)

### 7. Alerting Rules

Add these alerts for Phase 0 monitoring:

```yaml
groups:
  - name: phase0-baselines
    rules:
      - alert: DashboardAPIHighLatency
        expr: histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job=~"back-end|app-back-end",handler=~"/api/dashboard/.*"}[5m])) by (le)) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Dashboard API p99 latency > 500ms"
          
      - alert: DashboardAPIHighErrorRate
        expr: sum(rate(http_requests_total{job=~"back-end|app-back-end",handler=~"/api/dashboard/.*",status=~"5.."}[5m])) / sum(rate(http_requests_total{job=~"back-end|app-back-end",handler=~"/api/dashboard/.*"}[5m])) > 0.001
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Dashboard API error rate > 0.1%"
          
      - alert: SSEConnectionDrop
        expr: sse_connections_active{job=~"back-end|sse-back-end|app-back-end"} < 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "SSE connections dropped below threshold"
          
      - alert: ScheduledJobFailures
        expr: rate(job_execution_failure_total[5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Scheduled job failures detected"
```

## Exit Gate Checklist

Before proceeding to Phase 1:

- [ ] 7 days of production data collected
- [ ] All baseline targets met
- [ ] Baseline report completed and signed off
- [ ] Grafana dashboard created and shared
- [ ] Alerting rules deployed
- [ ] Team trained on rollback procedures
- [ ] Feature flag infrastructure tested in staging