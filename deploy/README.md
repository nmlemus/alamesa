# Deploy

## First-deploy checklist

1. **Provision the server** — ensure Python 3.11+, PostgreSQL, and a process manager (systemd or Docker) are available.
2. **Clone the repository** on the server.
3. **Create the env file**:
   ```bash
   cp deploy/.env.example deploy/.env
   ```
4. **Fill in all secrets** in `deploy/.env` (see comments in the file for format details).
5. **Install dependencies**:
   ```bash
   pip install -e ".[prod]"
   ```
6. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```
7. **Start the application**:
   ```bash
   mesadigital
   ```
8. **Verify the health endpoint** returns `{"status": "ok"}`:
   ```bash
   curl http://localhost:8000/health
   ```
9. **Change the first admin password** immediately after logging in for the first time.

---

## Secrets rotation procedure

Follow this procedure whenever a secret must be rotated (compromise, scheduled rotation, team member offboarding):

1. Generate the new secret value (see comments in `.env.example` for generation commands).
2. Update `deploy/.env` on the server with the new value.
3. Restart the application so it picks up the new value:
   ```bash
   systemctl restart mesadigital   # or: docker compose restart api
   ```
4. Verify the health endpoint is still responding after restart.
5. If rotating `SECRET_KEY`, all existing signed tokens and sessions are immediately invalidated — inform users that they will need to log in again.
6. If rotating `DATABASE_URL`, update connection credentials in the database server first, then update the env file, then restart.
7. Remove the old secret from any location where it was stored (password manager, CI variables, etc.).

---

## Backup

Run the following command to take a snapshot of the database:

```bash
pg_dump "$DATABASE_URL" | gzip > "backup-$(date +%Y%m%d-%H%M%S).sql.gz"
```

Store the resulting file in an off-site location (e.g. S3, encrypted external drive). Restore with:

```bash
gunzip -c backup-YYYYMMDD-HHMMSS.sql.gz | psql "$DATABASE_URL"
```

Schedule automated backups via cron or your cloud provider's managed backup feature. Retain at least 7 daily and 4 weekly snapshots.
