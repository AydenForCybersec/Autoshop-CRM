# Reference: Permission Matrix

## Who this is for
Admins assigning feature access.

## Before you start
- Understand each role in your shop.

## Step-by-step
1. Use default roles as a baseline.
2. Apply per-user overrides only when needed.

| Permission | Admin | Owner | Mechanic | Accountant | Service Writer |
|---|---|---|---|---|---|
| view_dashboard | Yes | Yes | Yes | Yes | Yes |
| view_customers | Yes | Yes | Yes | No | Yes |
| manage_customers | Yes | Yes | No | No | Yes |
| view_vehicles | Yes | Yes | Yes | No | Yes |
| manage_vehicles | Yes | Yes | No | No | Yes |
| view_jobs | Yes | Yes | Yes | No | Yes |
| manage_jobs | Yes | Yes | Yes | No | Yes |
| view_accounting | Yes | Yes | No | Yes | No |
| export_accounting | Yes | Yes | No | Yes | No |
| manage_settings | Yes | Yes | No | No | No |
| manage_users | Yes | Yes | No | No | No |
| manage_permissions | Yes | Yes | No | No | No |
| manage_theme | Yes | Yes | No | No | No |
| manage_updates | Yes | Yes | No | No | No |

## If this fails
- Users blocked unexpectedly: check custom overrides.
- Too much access: reduce to least privilege and retest.

## Done when
- Access matches job responsibilities.
