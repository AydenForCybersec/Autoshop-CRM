# Managing Users and Permissions

This section is for owners and admins only. It explains how to add staff accounts, assign roles, and fine-tune what each person can and cannot do.

## The four roles

When you create a user account, you assign them a **role**. The role determines what they can see and do.

- **Owner** — complete access to everything with no restrictions
- **Admin** — same as Owner. Use this for a trusted manager.
- **Staff** — can handle day-to-day work: add customers, vehicles, and jobs; log parts and labor; print invoices. Cannot see accounting or change settings.
- **Viewer** — read-only access. Can look up customers and jobs but cannot add or change anything. Good for a front desk person who just needs to check on job status.

## Adding a new user

1. Click **Settings** in the top menu
2. Click the **Users** tab
3. Scroll down to the **Add User** form
4. Enter a username (no spaces — use something simple like their first name)
5. Enter a starting password (at least 8 characters)
6. Choose their role
7. Click **Add User**

Give the employee their username and password privately. They can use it to sign in right away.

## Changing a user's role

On the **Users** tab, find the person's name in the **Current Users** list. Change the **Role** dropdown to the new role. Click **Update User**.

## Setting a mechanic's hourly labor rate

Find the mechanic's name in the **Current Users** list. Enter their billing rate (what you charge customers, per hour) in the **Labor Rate ($/hr)** box. Click **Update User**.

Example: if you charge $90 per hour for that mechanic, enter `90.00`.

When anyone logs labor for that mechanic on a job, this rate is used. The rate is saved into the labor entry at the time it is logged — so if you change the rate later, past entries are not affected.

## Resetting a password

If someone forgets their password, go to their card in the **Current Users** list, type a new password in the **Reset Password** field, and click **Set New Password**.

Passwords must be at least 8 characters. There is no "confirm password" step — just type the new one and click the button.

## Deactivating an account

When someone leaves the shop, you do not delete their account — you deactivate it. This keeps all their past work in the system (job history, labor entries, invoices) while preventing them from signing in.

Find their name in **Current Users**, uncheck the **Account active** box, and click **Update User**.

To reactivate them later, check the box again and click **Update User**.

## Fine-tuning permissions (advanced)

If you want a specific person to have access to something their role normally does not include — or block them from something their role normally allows — you can do this on the **Permissions** tab.

1. Click the **Permissions** tab in Settings
2. Find the user's name
3. Check or uncheck individual permissions
4. Click **Save Permissions**

This is useful for situations like: a senior staff member who needs to see the accounting page, or a part-time employee who should not be able to create new customers.

You do not need to use this for most staff. The four roles cover the common cases. Only use the permissions tab when a role is almost right but needs one small adjustment.

## A note on admin accounts

Admin and Owner accounts always have full access — their permissions cannot be restricted through the permissions tab. If you need to limit someone's access, they should be on the Staff or Viewer role instead.

At least one active admin account must exist at all times. The system will not let you deactivate or demote the last admin.
