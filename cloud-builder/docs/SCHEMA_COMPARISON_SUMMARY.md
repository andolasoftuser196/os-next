# MySQL to PostgreSQL Schema Comparison Summary

**Generated:** December 3, 2025  
**Source:** MySQL 8.0 @ orangescrumlive_schema (v2)  
**Target:** PostgreSQL 16.4 @ orangescrum-mt-test-1 (v4)

## Quick Stats

| Metric | Count |
|--------|-------|
| **Common Tables (to migrate)** | 198 |
| **Deprecated MySQL-only Tables** | 32 |
| **New PostgreSQL V4 Tables** | 98 |
| **Total MySQL Tables** | 230 |
| **Total PostgreSQL Tables** | 296 |

## Migration Strategy

### ✅ Tables to Migrate (198)
All tables that exist in both schemas will be migrated. These represent the core application data that is compatible between v2 and v4.

### ❌ Deprecated Tables (32 - MySQL only)
These tables exist in MySQL v2 but were removed in PostgreSQL v4. They will **NOT** be migrated:

- `account_deleted_emails` - Old email tracking
- `api_tokens` - Replaced by new auth system
- `audit_trails` - Replaced by enhanced logging
- `cart_dismissals` - Legacy feature
- `daily_traffics` - Old analytics
- `defect_labels` - Deprecated defect system
- `discount_coupons` - Old billing system
- `easycases_tmp` - Temporary migration table
- `selfhosted_*` - Self-hosted specific tables
- `user_*` (discounts, mapping, refcodes, referals) - Old user system
- Various utility tables (date_d, days, numbers, etc.)

### ➕ New PostgreSQL V4 Features (98 new tables)

#### Test Management System (46 tables)
- `test_cases`, `test_steps`, `test_runs`, `test_results`
- `test_plans`, `test_suites`, `test_scenarios`
- `test_defects`, `test_defect_*` (priorities, severities, statuses)
- `test_case_*` (comments, dependencies, resources, approvals)
- `test_execution_histories`, `test_management_*`

#### GitSync Integration (6 tables)
- `gitsync_provider_tokens`
- `gitsync_synchronizations`
- `gitsync_synchronization_entities`
- `gitsync_synchronization_histories`
- `gitsync_tasks`
- `gitsync_phinxlog`

#### Wiki Management (8 tables)
- `wiki_instances`, `wiki_spaces_books`, `wiki_pages`
- `wiki_api_keys`, `wiki_audit_logs`
- `wiki_project_links`
- `project_wiki_mapping`, `task_wiki_mapping`

#### Superset Reporting (7 tables)
- `superset_instances`, `superset_dashboards`
- `superset_embed_configs`, `superset_tokens`
- `superset_users`, `superset_dashboard_*`

#### Project Templates Enhancement (7 tables)
- `project_template_metas`
- `project_template_labels`
- `project_template_cases_labels`
- `project_template_task_types`
- `project_template_users`
- `project_template_workflows`
- `project_template_workflow_details`

#### Teams & SLA (4 tables)
- `teams`, `team_users`
- `slas`, `sla_types`

#### Other New Features
- `company_types`, `company_apis`
- `critical_path_snapshots`
- `ldap_informations`
- `ganttcharts`
- `email_settings`
- `inspection_zip_details`

## Notable Schema Changes in Common Tables

### companies
**Removed columns (deprecated):**
- `account_type`, `team_size`, `team_type` - Old org structure
- `billing_detail` - Moved to separate system
- `is_drip_extended`, `is_stripe_payment` - Old billing flags

**New columns:**
- `company_type_id` - New company classification
- `parent_company_id` - Multi-org hierarchy support
- `api_access_code` - API authentication

### easycases
**Removed columns:**
- `source` - Old import tracking
- `task_import_id` - Legacy import system

**New columns:**
- `approval_status`, `approved_by`, `approver_id`, `dt_approved`, `is_approved` - Approval workflow
- `feature_id` - Feature linking
- `team_id` - Team assignment
- `dependency_type` - Enhanced dependencies

### projects
**Removed columns:**
- `project_import_id`, `source` - Old import system

**New columns:**
- `organization_id` - Multi-org support
- `parent_id` - Project hierarchy (programs/portfolios)
- `purpose_type` - Project categorization

### types
**Changed:**
- `global` (varchar) → `is_global` (integer) - Datatype normalization

### Data Type Conversions
- `tinyint(1)` → `boolean` (for flags)
- `tinyint` → `smallint` (for small numbers)
- `datetime` → `timestamp without time zone`
- `float` → `double precision`
- Column names: Lowercase in PostgreSQL (e.g., `Time_zone_id` → `time_zone_id`)

## Execution Plan

### 1. Review Generated Files
```bash
cd durango-builder/migration_artifacts/run_20251203_142402/
cat MIGRATION_REPORT.txt
cat schema_differences.txt
cat pgloader.load
```

### 2. Test Migration (Dry Run)
Before migrating to production, test on a clone:
```bash
# Create test database
docker run --rm -e PGPASSWORD=postgres postgres:16.2 \
  psql -h 192.168.2.132 -p 5432 -U postgres -d postgres \
  -c "CREATE DATABASE migration_test_1;"

# Update pgloader.load to point to test database
# Then run migration
./compare_and_migrate.sh --execute-migration
```

### 3. Execute Production Migration
```bash
# After verifying test migration
./compare_and_migrate.sh --execute-migration
```

### 4. Post-Migration Verification
- Verify row counts match between MySQL and PostgreSQL
- Test application functionality
- Check for any data type conversion issues
- Validate foreign key relationships
- Run CakePHP migrations to add new V4 columns

## Important Notes

⚠️ **Data Only Migration**: pgloader migrates data only. The PostgreSQL schema must already exist with all tables and columns created by CakePHP migrations.

⚠️ **Triggers Disabled**: Migration temporarily disables triggers on key tables (companies, easycases, projects, users) for performance.

⚠️ **Sequence Reset**: After migration, sequences are reset to prevent ID conflicts.

⚠️ **NULL Handling**: Zero dates (`0000-00-00`) are converted to NULL in PostgreSQL.

⚠️ **Case Sensitivity**: PostgreSQL column names are lowercase. Some columns have been renamed (e.g., `Time_zone_id` → `time_zone_id`).

## Files Generated

- `pgloader.load` - pgloader configuration file
- `common_tables.txt` - List of tables to migrate
- `mysql_only_tables.txt` - Deprecated tables (excluded)
- `postgres_only_tables.txt` - New V4 feature tables
- `schema_differences.txt` - Detailed column differences
- `table_schemas/` - Individual table schemas for comparison
- `MIGRATION_REPORT.txt` - Full detailed report

## Next Steps

1. ✅ Schema comparison complete
2. ⏳ Review schema differences
3. ⏳ Test migration on clone database
4. ⏳ Execute production migration
5. ⏳ Run post-migration verification
6. ⏳ Run CakePHP migrations for V4 schema updates
