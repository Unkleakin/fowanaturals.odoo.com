from odoo import _, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fowa_woo_url = fields.Char("Store URL", config_parameter='fowa_woo.url', default='https://fowanaturals.com')
    fowa_woo_consumer_key = fields.Char("Consumer Key", config_parameter='fowa_woo.consumer_key')
    fowa_woo_consumer_secret = fields.Char("Consumer Secret", config_parameter='fowa_woo.consumer_secret')
    fowa_woo_webhook_secret = fields.Char("Webhook Secret", config_parameter='fowa_woo.webhook_secret')
    fowa_woo_warehouse_id = fields.Many2one(
        'stock.warehouse', "Stock Warehouse", config_parameter='fowa_woo.warehouse_id',
        help="Warehouse whose available quantity is published to the website. Empty = all warehouses.")
    fowa_woo_auto_confirm = fields.Boolean(
        "Auto-confirm Paid Orders", config_parameter='fowa_woo.auto_confirm', default=True)

    def action_fowa_woo_test(self):
        self.set_values()
        site = self.env['fowa.woo.api'].test_connection()
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
            'title': _("WooCommerce"), 'message': _("Connected to %s", site), 'type': 'success'}}

    def action_fowa_woo_sync_products(self):
        self.env['product.template']._cron_woo_pull_products()

    def action_fowa_woo_sync_orders(self):
        self.env['sale.order']._cron_woo_pull_orders()
