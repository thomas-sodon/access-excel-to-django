# Access and ownership: Northwind

The rule for every engagement: the client owns the code repository, the host, the database and the sign-in app registration; we hold only the access the care plan needs after acceptance, and no credential of the client's that we do not need. This page is written from the engagement: target repository `thomas-sodon/access-excel-to-django` (folder `northwind/`), hosting provider `none` managed by us, sign-in `local`, no secret references set, no care plan, no Windows + Access machine.

**Demo status.** This is our own public demo, so we are the owner of everything below; there is no client to transfer to. The sections still say what a client transfer covers.

## Accounts and owners

| Account or resource | Owner | Administered by | State at acceptance (demo) |
|---|---|---|---|
| GitHub repository `thomas-sodon/access-excel-to-django` (code, CI, pull requests) | us (demo); the client for a client engagement | us | private until the S6 gate, then public |
| GitHub Actions (CI on synthetic data, no secrets) | follows the repository | us | runs from the private period deleted before the repository is made public |
| Hosting (provider `none`: a Linux host) | the client | the client or their MSP, or us under a care plan | none set up |
| Production database | the client | the client's DBA | none |
| Database backups and their storage | the client | the client's DBA or MSP | none |
| Microsoft Entra app registration (only with Microsoft sign-in) | the client's tenant | the client's Entra administrator | not used (sign-in `local`) |
| SMTP / e-mail sending | the client | the client | not used |
| Domain name and TLS certificate | the client | the client or their MSP | none |
| Windows + Access machine (relink rehearsal) | the client | the client | none (`environment.windows_box.available` false) |
| Pipeline repository and engagement records (`modernization-pipeline`) | us | us | ours; they hold names, counts and hashes, no data values |

## Credentials we hold

| Secret reference | Opens | Stored | Revoked or rotated |
|---|---|---|---|
| `secrets.github_push.ref` | pushes and pull requests on the client's target repository | not set (demo: the operator's own GitHub login pushes) | revoked at acceptance unless the care plan needs it |
| `secrets.stage1_target_url_ref` | the Stage 1 database | not set (no Stage 1) | |
| `secrets.staging_db_url_ref` | the staging database | not set (no staging host) | |
| `secrets.production_db_url_ref` | the production database (go-live load) | not set (no go-live) | rotated by the client's DBA after go-live |
| `secrets.entra.client_secret_ref` | the Entra app registration | not set (sign-in `local`) | rotated before `secrets.entra.secret_expires` |
| `secrets.accdb_password_ref` | a password-protected source file | not set (the source has no password) | |

Besides these, we hold only our own logins: the operator's GitHub account (a file-stored gh token used for the demo repositories) and the passwords of the local database roles on the operator's host (in the operator's private settings file, never in a repository). None of them opens a client system.

## Transfer steps

For a client engagement, at the S6 gate (who does each step in brackets):

1. **Repository** (client, us): the client confirms they own the repository, or we transfer it to their GitHub organisation; they set branch protection; we remove our access unless the care plan needs it. The demo repository stays in our account.
2. **Hosting** (client or MSP): the host account and its billing are in the client's name; production settings are entered from the names in the runbook; we keep no host login unless the care plan needs one.
3. **Database** (client's DBA): the DBA rotates the login whose URL was in `secrets.production_db_url_ref` and keeps the admin login.
4. **Sign-in** (client's Entra administrator, only with Microsoft sign-in): the app registration lives in the client's tenant; they rotate the client secret and update the host setting.
5. **App** (client): change `DJANGO_SECRET_KEY` after the handover if we ever saw the host's settings; disable our administrator accounts in the app.
6. **Push token** (us): revoke the token in `secrets.github_push` and delete its line from our secret store, unless the care plan needs it.
7. **Windows + Access machine** (client): delete the copies listed in `environment.windows_box.copies` (none for the demo) and note the date beside the destruction record ([data-retention.md](data-retention.md)).
8. **Record** (us): set `care_plan.access_after_acceptance` in the engagement and correct the section below if it differs.

## After acceptance

The engagement has no care plan (`care_plan` is null), so after acceptance we keep no access to any client system and hold no client credential. For the demo, we keep owning the public repository and the engagement records; the private data we hold is public sample data and its deletion follows [data-retention.md](data-retention.md). If a care plan is purchased later, this section is updated from `care_plan.access_after_acceptance` in a follow-up pull request.
