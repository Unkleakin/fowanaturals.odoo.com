# fowanaturals.odoo.com

Odoo.sh repository (assumes Odoo 17.0). Contains `fowa_woocommerce`, a connector to the WooCommerce store at https://fowanaturals.com.

## What it does
| Flow | Direction | Trigger |
|---|---|---|
| Orders -> sale orders (auto-confirmed when Processing/Completed; cancelled on cancel/refund/fail) | Woo -> Odoo | webhook + 15-min cron |
| Customers (matched by Woo ID, then e-mail) | Woo -> Odoo | with orders |
| Products (matched by Woo ID, then SKU) | Woo -> Odoo | webhook + daily cron |
| Stock (`free_qty`) | Odoo -> Woo | 15-min cron |

Odoo is the source of truth for stock and, after first import, product names/prices. Variable products are imported as their parent only (v1).

## Setup
1. Push to the Odoo.sh branch, install **Fowa Naturals WooCommerce Connector**.
2. WooCommerce > Settings > Advanced > REST API: create a **Read/Write** key.
3. Odoo > Settings > WooCommerce: enter the store URL, key and secret, then **Test connection**.
4. WooCommerce > Settings > Advanced > Webhooks: add `Order created`, `Order updated`, `Product updated` pointing to
   `https://<your-odoo-sh-domain>/fowa_woo/webhook` with a secret; paste the same secret in Odoo.
5. Run **Import products now** first (so order lines link to products), then **Sync orders now**.
6. Enable the three crons under Settings > Technical > Scheduled Actions (shipped inactive).

Test on a staging branch before production. Secrets are stored in `ir.config_parameter`, never in git.
