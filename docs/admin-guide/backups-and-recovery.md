# Admin Guide: Backups and Recovery

## Who this is for
Admins responsible for data safety.

## Before you start
- You have DB credentials and secure backup storage.
- You tested backup script access on your host.

## Step-by-step
1. Set DB backup variables required by `scripts/backup_db.sh`.
2. Run backup script on a schedule (daily recommended).
3. Store backups off the app host.
4. Test restore on a non-production environment.
5. Record recovery steps in your team runbook.

## If this fails
- Script errors: verify DB host/user/password and permissions.
- Corrupt dump: repeat backup and validate file size and restore test.
- Missing backups: set alerts for failed backup jobs.

## Done when
- You have recent restorable backups.
- Recovery has been tested at least once.
