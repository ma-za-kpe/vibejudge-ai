# CloudWatch Logs Insights Queries

This document contains ready-to-use CloudWatch Logs Insights queries for analyzing ECS container logs from the VibeJudge AI Streamlit dashboard deployment.

## Prerequisites

- Log Group: `/ecs/vibejudge-dashboard`
- Region: `us-east-1`
- Retention: 7 days

## How to Use These Queries

1. Open AWS Console → CloudWatch → Logs → Insights
2. Select log group: `/ecs/vibejudge-dashboard`
3. Copy and paste a query from below
4. Adjust time range as needed (default: last 1 hour)
5. Click "Run query"

---

## 1. Find Errors and Exceptions

**Purpose**: Identify application errors, exceptions, and failures for troubleshooting.

**Query**:
```sql
fields @timestamp, @message, @logStream
| filter @message like /(?i)(error|exception|failed|failure|critical)/
| sort @timestamp desc
| limit 100
```

**Use Cases**:
- Investigate application crashes
- Debug failed API calls
- Identify Python exceptions
- Track deployment failures

**Sample Output**:
```
@timestamp              @message                                    @logStream
2025-01-15 10:23:45    ERROR: Failed to connect to API             ecs/streamlit-dashboard/task-abc123
2025-01-15 10:22:30    Exception: KeyError in session state        ecs/streamlit-dashboard/task-def456
```

---

## 2. Track Response Times

**Purpose**: Monitor application performance and identify slow requests.

**Query**:
```sql
fields @timestamp, @message
| filter @message like /response_time|duration|elapsed/
| parse @message /response_time[=:]?\s*(?<response_time>\d+\.?\d*)/
| stats avg(response_time) as avg_response_ms,
        max(response_time) as max_response_ms,
        min(response_time) as min_response_ms,
        count() as request_count
  by bin(5m)
| sort bin(5m) desc
```

**Use Cases**:
- Identify performance degradation
- Correlate response times with scaling events
- Validate <2s page load requirement
- Detect slow API calls

**Sample Output**:
```
bin(5m)              avg_response_ms  max_response_ms  min_response_ms  request_count
2025-01-15 10:20:00  1250.5          3200.0           450.0            42
2025-01-15 10:15:00  980.2           1800.0           520.0            38
```

**Alternative Query** (for Streamlit-specific timing):
```sql
fields @timestamp, @message
| filter @message like /GET|POST/
| parse @message /(?<method>GET|POST)\s+(?<path>\/[^\s]*)\s+.*\s+(?<status>\d{3})\s+(?<duration>\d+)ms/
| stats avg(duration) as avg_ms,
        max(duration) as max_ms,
        pct(duration, 95) as p95_ms,
        pct(duration, 99) as p99_ms
  by path
| sort avg_ms desc
```

---

## 3. Monitor Health Checks

**Purpose**: Track health check requests and identify unhealthy tasks.

**Query**:
```sql
fields @timestamp, @message, @logStream
| filter @message like /_stcore\/health/
| parse @message /(?<method>GET|POST)\s+\/_stcore\/health\s+.*\s+(?<status>\d{3})/
| stats count() as health_check_count,
        sum(status = 200) as success_count,
        sum(status != 200) as failure_count
  by bin(1m), @logStream
| sort bin(1m) desc
```

**Use Cases**:
- Verify health check frequency (should be every 30s per task)
- Identify tasks failing health checks
- Correlate health check failures with task restarts
- Debug ALB target group issues

**Sample Output**:
```
bin(1m)              @logStream                          health_check_count  success_count  failure_count
2025-01-15 10:23:00  ecs/streamlit-dashboard/task-abc123  2                  2              0
2025-01-15 10:23:00  ecs/streamlit-dashboard/task-def456  2                  1              1
```

**Alternative Query** (health check failures only):
```sql
fields @timestamp, @message, @logStream
| filter @message like /_stcore\/health/
| parse @message /(?<status>\d{3})/
| filter status != "200"
| sort @timestamp desc
| limit 50
```

---

## 4. Analyze Scaling Events

**Purpose**: Track ECS service scaling actions and correlate with CPU utilization.

**Query**:
```sql
fields @timestamp, @message, @logStream
| filter @message like /(?i)(scaling|task started|task stopped|desired count|running count)/
| parse @message /desired[:\s]+(?<desired>\d+)/
| parse @message /running[:\s]+(?<running>\d+)/
| sort @timestamp desc
| limit 100
```

**Use Cases**:
- Verify auto-scaling triggers correctly
- Identify scaling thrashing (rapid scale up/down)
- Correlate scaling with traffic patterns
- Debug scaling policy configuration

**Sample Output**:
```
@timestamp              @message                                    desired  running
2025-01-15 10:25:00    Scaling out: desired count changed to 4     4        2
2025-01-15 10:26:30    Task started: new task launched             4        3
2025-01-15 10:27:00    Task started: new task launched             4        4
```

**Alternative Query** (task lifecycle events):
```sql
fields @timestamp, @message
| filter @message like /(?i)(task started|task stopped|task failed|task running)/
| stats count() as event_count by @message
| sort event_count desc
```

---

## 5. Monitor API Calls to Backend

**Purpose**: Track API calls from Streamlit to the backend API and identify failures.

**Query**:
```sql
fields @timestamp, @message
| filter @message like /(?i)(api|request|http)/
| parse @message /(?<method>GET|POST|PUT|DELETE)\s+(?<url>https?:\/\/[^\s]+)\s+.*\s+(?<status>\d{3})/
| stats count() as request_count,
        sum(status >= 200 and status < 300) as success_count,
        sum(status >= 400 and status < 500) as client_error_count,
        sum(status >= 500) as server_error_count
  by url
| sort request_count desc
```

**Use Cases**:
- Identify failing API endpoints
- Track API usage patterns
- Debug authentication issues (401/403 errors)
- Monitor backend API availability

---

## 6. Analyze Container Startup Time

**Purpose**: Measure how long containers take to start and become healthy.

**Query**:
```sql
fields @timestamp, @message, @logStream
| filter @message like /(?i)(starting|started|ready|listening)/
| sort @timestamp asc
| stats earliest(@timestamp) as start_time,
        latest(@timestamp) as ready_time
  by @logStream
| fields @logStream, start_time, ready_time,
         (ready_time - start_time) / 1000 as startup_seconds
| sort startup_seconds desc
```

**Use Cases**:
- Optimize container startup time
- Identify slow deployments
- Debug health check grace period issues
- Validate deployment performance

---

## 7. Find Memory and Resource Issues

**Purpose**: Identify out-of-memory errors and resource exhaustion.

**Query**:
```sql
fields @timestamp, @message, @logStream
| filter @message like /(?i)(memory|oom|out of memory|resource|cpu|killed)/
| sort @timestamp desc
| limit 50
```

**Use Cases**:
- Detect OOM kills (task memory > 1GB)
- Identify memory leaks
- Debug task crashes
- Determine if memory increase is needed

---

## 8. Track User Sessions and Activity

**Purpose**: Monitor user activity and session patterns.

**Query**:
```sql
fields @timestamp, @message
| filter @message like /(?i)(session|user|login|logout|page|navigation)/
| parse @message /session[_\s]?id[=:]?\s*(?<session_id>[a-zA-Z0-9-]+)/
| stats count() as activity_count by session_id
| sort activity_count desc
| limit 20
```

**Use Cases**:
- Track concurrent users
- Identify high-activity sessions
- Debug session state issues
- Analyze usage patterns

---

## 9. Monitor Deployment Events

**Purpose**: Track deployments, rollbacks, and task replacements.

**Query**:
```sql
fields @timestamp, @message, @logStream
| filter @message like /(?i)(deployment|rollback|task definition|version|image)/
| sort @timestamp desc
| limit 50
```

**Use Cases**:
- Verify successful deployments
- Track deployment frequency
- Identify rollback events
- Correlate issues with deployments

---

## 10. Generate Error Rate Dashboard

**Purpose**: Calculate error rate over time for monitoring.

**Query**:
```sql
fields @timestamp, @message
| filter @message like /(?i)(error|exception|failed|success|completed)/
| stats count() as total_events,
        sum(@message like /(?i)(error|exception|failed)/) as error_count,
        sum(@message like /(?i)(success|completed)/) as success_count
  by bin(5m)
| fields bin(5m),
         total_events,
         error_count,
         success_count,
         (error_count * 100.0 / total_events) as error_rate_percent
| sort bin(5m) desc
```

**Use Cases**:
- Monitor application health
- Set up CloudWatch alarms based on error rate
- Identify degradation trends
- Validate SLA compliance

---

## Advanced Queries

### Query 11: Correlate Errors with Task Restarts

```sql
fields @timestamp, @message, @logStream
| filter @message like /(?i)(error|exception|task stopped|task started)/
| sort @timestamp asc
| limit 200
```

### Query 12: Find Slow Database/API Queries

```sql
fields @timestamp, @message
| filter @message like /query|database|api/
| parse @message /duration[=:]?\s*(?<duration>\d+)/
| filter duration > 1000
| sort duration desc
| limit 50
```

### Query 13: Monitor Cache Hit Rate

```sql
fields @timestamp, @message
| filter @message like /cache/
| parse @message /cache\s+(?<result>hit|miss)/
| stats count() as total,
        sum(result = "hit") as hits,
        sum(result = "miss") as misses
  by bin(5m)
| fields bin(5m),
         total,
         hits,
         misses,
         (hits * 100.0 / total) as hit_rate_percent
| sort bin(5m) desc
```

---

## Tips for Effective Log Analysis

1. **Use Time Ranges Wisely**: Start with 1 hour, expand if needed
2. **Combine Filters**: Use multiple `filter` statements for precision
3. **Parse Structured Logs**: Use `parse` to extract specific fields
4. **Aggregate with Stats**: Use `stats` for metrics and trends
5. **Sort Appropriately**: Use `desc` for recent events, `asc` for chronological
6. **Limit Results**: Always use `limit` to avoid overwhelming output
7. **Save Frequent Queries**: Save commonly used queries in CloudWatch console
8. **Create Dashboards**: Convert queries to CloudWatch dashboard widgets
9. **Set Up Alarms**: Use query results to trigger CloudWatch alarms
10. **Correlate with Metrics**: Cross-reference logs with CloudWatch metrics

---

## Troubleshooting Common Issues

### No Results Returned

- Verify log group name: `/ecs/vibejudge-dashboard`
- Check time range (logs retained for 7 days only)
- Ensure ECS tasks are running and generating logs
- Verify IAM permissions for CloudWatch Logs access

### Query Timeout

- Reduce time range (try 1 hour instead of 7 days)
- Add more specific filters to reduce data volume
- Use `limit` to cap result size
- Consider using CloudWatch Logs Insights saved queries

### Unexpected Results

- Check log format (Streamlit may change output format)
- Verify `parse` regex patterns match actual log format
- Test filters incrementally (add one at a time)
- Use `display @message` to see raw log format

---

## Related Resources

- [CloudWatch Logs Insights Query Syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [ECS Container Logs](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_cloudwatch_logs.html)
- [RUNBOOK.md](./RUNBOOK.md) - Operational procedures
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide

---

**Last Updated**: 2025-01-15  
**Maintained By**: VibeJudge DevOps Team
