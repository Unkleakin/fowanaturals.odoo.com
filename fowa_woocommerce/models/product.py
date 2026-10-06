import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    woo_id = fields.Char("WooCommerce ID", copy=False, index=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    woo_id = fields.Char("WooCommerce ID", copy=False, index=True)
    woo_publish_stock = fields.Boolean("Publish Stock to Website", default=True)

    # ---- Woo -> Odoo -------------------------------------------------
    @api.model
    def _cron_woo_pull_products(self):
        Api = self.env['fowa.woo.api']
        for wp in Api.get_all('products', {'status': 'publish'}):
            try:
                with self.env.cr.savepoint():
                    self._woo_upsert_product(wp)
            except Exception:
                _logger.exception("Failed to import Woo product %s", wp.get('id'))

    @api.model
    def _woo_upsert_product(self, wp):
        """Create/update a simple product (variable products are imported as their parent)."""
        sku = wp.get('sku') or False
        woo_id = str(wp['id'])
        tmpl = self.search([('woo_id', '=', woo_id)], limit=1)
        if not tmpl and sku:
            tmpl = self.search([('default_code', '=', sku)], limit=1)
        vals = {
            'name': wp.get('name'),
            'woo_id': woo_id,
            'default_code': sku,
            'list_price': float(wp.get('regular_price') or wp.get('price') or 0),
            'description_sale': wp.get('short_description') or False,
            'sale_ok': True,
            'detailed_type': 'product',
        }
        if tmpl:
            # Odoo owns name/price once the product exists; only link IDs.
            tmpl.write({'woo_id': woo_id, 'default_code': sku or tmpl.default_code})
        else:
            tmpl = self.create(vals)
        tmpl.product_variant_id.woo_id = woo_id
        return tmpl

    # ---- Odoo -> Woo -------------------------------------------------
    @api.model
    def _cron_woo_push_stock(self):
        icp = self.env['ir.config_parameter'].sudo()
        wh_id = int(icp.get_param('fowa_woo.warehouse_id') or 0)
        Api = self.env['fowa.woo.api']
        products = self.search([('woo_id', '!=', False), ('woo_publish_stock', '=', True),
                                ('detailed_type', '=', 'product')])
        for tmpl in products:
            prod = tmpl.product_variant_id.with_context(warehouse=wh_id) if wh_id else tmpl.product_variant_id
            qty = max(int(prod.free_qty), 0)
            try:
                Api.request('PUT', f'products/{tmpl.woo_id}', json={
                    'manage_stock': True, 'stock_quantity': qty})
            except Exception:
                _logger.exception("Failed to push stock for %s", tmpl.display_name)
