---
name: Fix Dev Stack Connectivity
description: "Diagnose and fix Docker Compose + Traefik + browser-container connectivity/TLS/DNS issues in this workspace"
argument-hint: "Paste the exact error/symptom (e.g., ERR_CONNECTION_REFUSED, DNS_PROBE_STARTED, SQLSTATE auth error)"
agent: agent
---
You are working in the `os-next` workspace.

Task: Diagnose and fix ONE connectivity/runtime issue for the local dev stack based on the user-provided symptom.

Input symptom:
`$ARGUMENTS`

## Scope
Focus on these components when relevant:
- `docker-compose.yml`, `docker-compose.override.yml`
- `traefik/dynamic.yml`
- `os-v4/.env`
- `certs/*`
- browser service (`lscr.io/linuxserver/chromium`)

## Required workflow
1. Reproduce and verify current state.
- Run targeted checks (`docker compose ps`, service logs, container exec probes, HTTP status checks).
- Confirm whether the issue is DNS, TLS/cert, routing, port publish, auth, or DB credentials.

2. Apply the smallest safe fix.
- Edit only files needed for this issue.
- Prefer minimal, reversible changes.
- Keep templates in sync when editing generated files:
  - `templates/docker-compose.yml.j2`
  - `templates/docker-compose.override.yml.j2`
  - `templates/traefik-dynamic.yml.j2`

3. Recreate only affected services.
- Use `docker compose up -d --force-recreate <service>` when possible.
- Avoid full stack restart unless required.

4. Verify end-to-end.
- Re-run checks proving the symptom is resolved.
- Include at least one inside-browser-container verification when browser networking is involved.

## Guardrails
- Do not run destructive commands (`git reset --hard`, deleting volumes/data) unless explicitly asked.
- Preserve user changes in unrelated files.
- If a cert warning remains due to self-signed cert trust, implement trust wiring rather than bypassing blindly.

## Response format
Return a concise report with:
1. Root cause
2. Files changed
3. Commands run for verification
4. Final status codes/results
5. Any remaining risk or follow-up
