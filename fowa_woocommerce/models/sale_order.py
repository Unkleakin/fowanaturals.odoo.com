import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

PAID_STATUSES = ('processing', 'completed')
CANCELLED_STATUSES = ('cancelled', 'refunded', 'failed')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    woo_id = fields.Char("WooCommerce Order ID", copy=False, index=True)
    woo_number = fields.Char("Website Order #", copy=False)
    woo_status = fields.Char("Website Status", copy=False)

    _sql_constraints = [('woo_id_uniq', 'unique(woo_id)', "This WooCommerce order is already imported.")]

    @api.model
    def _cron_woo_pull_orders(self):
        icp = self.env['ir.config_parameter'].sudo()
        since = icp.get_param('fowa_woo.orders_since')
        params = {'orderby': 'date', 'order': 'asc'}
        if since:
            params['modified_after'] = since
        newest = since
        for wo in self.env['fowa.woo.api'].get_all('orders', params):
            try:
                with self.env.cr.savepoint():
                    self._woo_upsert_order(wo)
                newest = max(newest or '', wo.get('date_modified_gmt') or '') or newest
            except Exception:
                _logger.exception("Failed to import Woo order %s", wo.get('id'))
        if newest:
            icp.set_param('fowa_woo.orders_since', newest if newest.endswith('Z') else newest + 'Z')

    @api.model
    def _woo_upsert_order(self, wo):
        woo_id = str(wo['id'])
        status = wo.get('status')
        order = self.search([('woo_id', '=', woo_id)], limit=1)
        if order:
            return self._woo_update_status(order, status)
        if status in CANCELLED_STATUSES or status in ('pending', 'checkout-draft'):
            return self.browse()  # wait until the order is actually placed/paid

        partner, delivery = self.env['res.partner']._woo_get_or_create(
            wo.get('billing') or {}, wo.get('shipping') or {}, wo.get('customer_id'))
        lines = [(0, 0, self._woo_line_vals(li)) for li in wo.get('line_items', [])]
        for ship in wo.get('shipping_lines', []):
            if float(ship.get('total') or 0):
                lines.append((0, 0, {'name': ship.get('method_title') or 'Shipping',
                                     'product_uom_qty': 1, 'price_unit': float(ship['total'])}))
        order = self.create({
            'partner_id': partner.id,
            'partner_shipping_id': delivery.id,
            'woo_id': woo_id,
            'woo_number': wo.get('number'),
            'woo_status': status,
            'client_order_ref': f"WEB-{wo.get('number')}",
            'date_order': (wo.get('date_created_gmt') or '').replace('T', ' ') or fields.Datetime.now(),
            'note': wo.get('customer_note') or False,
            'order_line': lines,
        })
        return self._woo_update_status(order, status)

    @api.model
    def _woo_line_vals(self, li):
        Product = self.env['product.product']
        product = Product.search([('woo_id', '=', str(li.get('variation_id') or li.get('product_id')))], limit=1)
        if not product and li.get('sku'):
            product = Product.search([('default_code', '=', li['sku'])], limit=1)
        qty = li.get('quantity') or 1
        vals = {'product_uom_qty': qty, 'price_unit': float(li.get('subtotal') or 0) / qty}
        if product:
            vals['product_id'] = product.id
        else:
            vals['name'] = li.get('name') or 'Website item'
        # Discounts: coupon difference between subtotal and total
        subtotal, total = float(li.get('subtotal') or 0), float(li.get('total') or 0)
        if subtotal > 0 and total < subtotal:
            vals['discount'] = round((subtotal - total) / subtotal * 100, 2)
        return vals

    def _woo_update_status(self, order, status):
        order.woo_status = status
        icp = self.env['ir.config_parameter'].sudo()
        if status in PAID_STATUSES and order.state in ('draft', 'sent') \
                and icp.get_param('fowa_woo.auto_confirm', 'True') == 'True':
            order.action_confirm()
        elif status in CANCELLED_STATUSES and order.state != 'cancel' and not order.invoice_ids.filtered(
                lambda i: i.state == 'posted'):
            order._action_cancel()
        return order
