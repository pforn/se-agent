# Tower — Product Knowledge Base

## What Tower Is

Tower is a **Python-native, serverless data platform built on Apache Iceberg**. It provides a fully managed lakehouse experience where customers bring their own cloud storage (S3, GCS, ADLS) and Tower handles compute, catalog, scheduling, and table maintenance.

**Core value proposition:** Open data formats (Iceberg) + serverless simplicity + Python-native workflows. No vendor lock-in, no infrastructure management, multi-engine interoperability.

## Core Components

### Tower Flows
- **Serverless ETL/ELT execution engine**
- Write pipelines in pure Python — no Spark clusters to manage
- Auto-scaling: scales to zero when idle, scales up based on data volume
- Native DataFrame API optimized for Iceberg reads/writes
- Built-in connectors for common sources (PostgreSQL, MySQL, Kafka, S3, REST APIs)
- Supports both batch and micro-batch (near-real-time) patterns
- dbt-core integration: run dbt models directly on Tower-managed Iceberg tables

### Tower Catalog
- **Iceberg REST Catalog implementation**
- Full Iceberg spec compliance: schema evolution, partition evolution, time travel, branching
- Multi-engine access: Spark, Trino, Athena, Flink, DuckDB — any engine that speaks Iceberg REST
- Fine-grained access control at table/column level
- Automatic table maintenance: compaction, snapshot expiry, orphan file cleanup
- Namespace management for organizing tables

### Tower Schedules
- **Managed orchestration for Tower Flows**
- Cron-based and event-driven scheduling
- Dependency chains between flows
- Monitoring, alerting, retry policies
- Integration with external orchestrators (Airflow, Dagster) via REST API

### dbt Integration
- Run dbt-core models on Tower-managed Iceberg tables
- dbt adapter for Tower (`dbt-tower`)
- Supports dbt 1.7+ (1.8 compatibility in progress)
- Incremental models, snapshots, and tests all supported
- Performance: columnar pushdown, predicate pruning on Iceberg metadata

## Iceberg Capabilities via Tower

### Schema Evolution
- Add, drop, rename, reorder columns without rewriting data
- Type promotion (int → long, float → double)
- Backward-compatible by default

### Partition Evolution
- Change partition strategy without rewriting historical data
- Example: switch from `daily(event_date)` to `daily(event_date), bucket(16, region)` — old data keeps old layout, new data uses new layout
- Queries automatically handle mixed partition layouts

### Time Travel & Branching
- Query any historical snapshot by ID or timestamp
- Create branches for isolated testing (write-audit-publish pattern)
- Rollback to any previous snapshot

### Table Maintenance
- **Compaction:** Merge small files into optimal-size files (configurable target)
- **Snapshot expiry:** Remove old snapshots to reclaim metadata
- **Orphan file cleanup:** Remove unreferenced data files
- Tower automates all maintenance — no manual `OPTIMIZE` commands

## Deployment Model

- **SaaS control plane** — Tower manages catalog, scheduling, monitoring
- **Customer's cloud account for data** — Data stays in customer's S3/GCS/ADLS
- **Compute in Tower's cloud** — Serverless, no VMs to manage
- VPC peering available for private connectivity to customer data sources
- SOC2 Type II certified
- IAM role assumption for cross-account S3 access (AWS)

## Common Migration Patterns

### Snowflake → Tower
1. Export Snowflake tables to Parquet on S3
2. Register as Iceberg tables in Tower Catalog (metadata-only operation for Parquet)
3. Migrate dbt project to use `dbt-tower` adapter
4. Point BI tools at Tower via Trino or direct Iceberg REST
5. Dual-run period: validate query results match
6. Cutover: deprecate Snowflake

**Key selling points vs. Snowflake:**
- Open format (no lock-in)
- Multi-engine access (Spark + Trino + BI from same tables)
- Cost savings on storage (S3 vs. Snowflake managed storage)
- No per-query pricing surprises

### Databricks → Tower
1. Convert Delta tables to Iceberg (or use Delta UniForm for transition period)
2. Register in Tower Catalog
3. Migrate notebooks/jobs to Tower Flows (Python-native, so usually straightforward)
4. Replace Unity Catalog with Tower Catalog

**Key selling points vs. Databricks:**
- No Databricks Runtime licensing costs
- True multi-engine (not locked to Spark)
- Simpler operational model (serverless, no cluster management)
- Native Iceberg (not Delta-with-Iceberg-compatibility)

### Greenfield
1. Connect Tower to customer's cloud storage
2. Define tables in Tower Catalog
3. Build ingestion flows in Tower Flows
4. Add dbt transformations
5. Connect BI/ML tools via Trino or Iceberg REST

## Pricing Model (Approximate)
- Pay-per-use compute (Flow execution time)
- Catalog management fee (per-table/month)
- Storage: customer's own cloud costs
- No egress fees within same cloud/region
- Typically 40-60% lower TCO than Snowflake for comparable workloads

## Known Limitations (Be Transparent)
- **Streaming:** Near-real-time (micro-batch ~1-5 min latency), not true sub-second streaming. For sub-second, recommend Kafka + Flink writing to Tower-managed Iceberg tables.
- **dbt compatibility:** dbt-core 1.8 adapter in beta. Some advanced dbt features (exposures, semantic layer) not yet supported.
- **Governance:** Table/column-level access control. Row-level security on roadmap.
- **Geographic availability:** US and EU regions. APAC in progress.
- **Ecosystem:** Smaller connector library than Snowflake/Databricks. Custom connectors via Python SDK.
- **Community:** Smaller community/ecosystem than Snowflake or Databricks. Offset by direct FDE support.
