# Free global hosting options for Astra — checked 2026-10-13

Aly requested current free options while B1 was underway. Recommendations below
are planning choices, not authority to create accounts, accept service terms,
upgrade billing or expose a server. The existing approved baseline is Oracle
Always Free + DuckDNS + Caddy; no provider switch is made by this comparison.

Astra currently uses a standard-library Python server and a local SQLite file.
It needs durable storage across restarts. A single region can serve users
worldwide; this does not mean a multi-region database or guaranteed global
latency. The final region, free capacity, account eligibility and real workload
performance are unverified until Aly's account/provisioning checks.

| Option | Current free offer / cost boundary | Fit for Astra |
| --- | --- | --- |
| Oracle Cloud Always Free | Published A1 allowance is 1,500 OCPU-hours / 9,000 GB-hours monthly, equivalent to 2 OCPUs and 12 GB RAM; 200 GB combined boot/block storage in the home region. Free capacity can be unavailable and idle instances may be reclaimed. | Recommended free pilot: retains Python/SQLite architecture and durable disk. Use only console-confirmed eligible resources; no paid upgrade. |
| Google Compute Engine Free Tier | One eligible e2-micro equivalent in selected US regions and 30 GB standard persistent disk. A standard VM's external IPv4 list price is $0.005/hour: about $3.65 for a 730-hour month, before any applicable credits. | Technically compatible, but a straightforward always-on public IPv4 deployment is not completely free. Avoid presenting its free compute as a $0 complete hosting bill. |
| Render Free | Free web service; idle spin-down after 15 minutes. Local filesystem changes, including SQLite, disappear on spin-down/restart/redeploy. Free services cannot attach persistent disks; free PostgreSQL expires after 30 days. | Suitable for disposable demonstrations; unsuitable for the current durable Astra database. A different database/storage design would be required. |
| AWS Free Plan | New-account plan lasts up to six months or until its credits are exhausted. It includes $100 initial credits and up to $100 earned credits. | Temporary trial, not a permanent free hosting solution for this app. |

The fit assessments are engineering judgments based on Astra's current code and
the published provider limits, not provider guarantees.

## Recommended zero-subscription pilot

One Oracle Always Free VM, Ubuntu, persistent SQLite data, Caddy reverse proxy
and a free DuckDNS hostname. Caddy obtains/renews HTTPS certificates for eligible
public names. Keep Astra listening on loopback; use Caddy access logs for real
client IPs, as Aly selected. Retain encrypted off-VM backups and prove restore
before inviting users.

Use the current published 2-core/12-GB A1 ceiling, not older 4-core/24-GB guides.
Oracle sign-up normally needs a phone and card for verification; its documentation
says the card is not charged unless the account is upgraded. Aly performs all
account/credential/terms steps. Capacity, current console billing labels and
available resources must be checked before creating anything. If free capacity
is unavailable, stop and discuss the fallback rather than selecting a paid shape.

For a global team, select the account's home region deliberately based on users,
data location and available free capacity. A US region may suit the school
project, but no region is selected here. Actual worldwide availability, latency,
security and recoverability remain unverified.

## Primary sources

- [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm): A1 allowance, disk budgets, home-region restriction, unavailable-capacity and idle-reclamation rules.
- [Oracle Free Tier/account rules](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm): account verification, upgrade/billing and trial-vs-Always-Free boundaries.
- [Google Cloud Free Tier](https://docs.cloud.google.com/free/docs/free-cloud-features): VM/disk/region allowances and billing-account requirements.
- [Google VPC pricing](https://cloud.google.com/vpc/pricing): external IPv4 charge; $3.65 example is calculated from the published rate, not a quote for the entire service. A nonessential free-hour clause was omitted because retrieved official-page variants differed during review.
- [Render Free](https://render.com/docs/free): idle sleep, ephemeral filesystem, disk exclusion and database expiry.
- [AWS Free Plan](https://aws.amazon.com/about-aws/whats-new/2025/07/aws-free-tier-credits-month-free-plan/): credit amounts and expiry.
- [DuckDNS](https://www.duckdns.org/): free dynamic DNS service.
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https): certificate management for eligible public names.
