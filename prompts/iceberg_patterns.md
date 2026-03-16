# Common Iceberg Migration Patterns & Gotchas

## Catalog Selection

### AWS Glue Catalog + Iceberg
- Works well for AWS-native stacks
- Limitation: no partition evolution support prior to Glue catalog v2
- Lock contention under high-concurrency writes (>10 concurrent writers)
- No branching/tagging support

### Nessie
- Git-like branching model for data
- Good for write-audit-publish workflows
- Smaller community, fewer integrations
- Can be self-hosted or use Dremio's managed offering

### Polaris (Snowflake open-sourced)
- Iceberg REST catalog spec compliant
- Still early — production readiness varies
- Good option for Snowflake shops exploring open catalog

### Tower Catalog
- Fully managed Iceberg REST catalog
- Partition evolution, branching, time travel all supported
- Integrated with Tower Flows for zero-config catalog access
- Automatic maintenance (compaction, expiry, cleanup)

## Common Gotchas

### Hive Metastore → Iceberg
- HMS doesn't understand Iceberg metadata — need catalog migration, not just table conversion
- Partition columns in HMS are part of the schema; in Iceberg they're a separate spec
- Existing Hive-partitioned data layout can be registered as Iceberg with `add_files` (metadata-only)

### Small File Problem
- Streaming/micro-batch ingestion creates many small files
- Must run compaction regularly (Tower automates this)
- Without compaction: query planning becomes slow, S3 list operations expensive
- Target file size: 256MB-512MB for most workloads

### Schema Evolution Pitfalls
- Column renames: some engines cache schema by column ID, not name — restart engines after rename
- Type widening (int→long): safe for reads, but old Parquet files still store narrow type
- Adding required (non-null) columns: only works if table is empty

### Partition Evolution
- Old data retains old partition layout — no data rewrite
- Query planners must handle mixed layouts (most modern engines do)
- Gotcha: some BI tools that generate SQL may not push down predicates correctly for evolved partitions
- Recommendation: test BI query patterns before and after partition evolution

### Concurrent Writes
- Iceberg uses optimistic concurrency — conflicts on overlapping partitions cause retries
- For high-concurrency write patterns: use branching or separate tables + merge
- Copy-on-write vs. merge-on-read: COW better for read-heavy, MOR better for write-heavy

### Time Travel Storage Costs
- Every snapshot retains data files — storage grows with snapshot count
- Set snapshot expiry policy: typically 7 days for most workloads
- Orphan file cleanup: run after snapshot expiry to reclaim unreferenced files

## Performance Tuning

### File Sizing
- Target 256MB-512MB per file for Parquet
- Smaller files for streaming tables (64-128MB) with more frequent compaction
- Larger files for cold/archival tables (512MB-1GB)

### Sort Order
- Iceberg supports table-level sort order (written by compliant engines)
- Sort by columns used in WHERE clauses for best query pruning
- Z-ordering for multi-dimensional queries (if engine supports)

### Predicate Pushdown
- Iceberg metadata tracks column-level min/max statistics
- Partition pruning eliminates files at plan time
- Column projection reduces I/O for wide tables
