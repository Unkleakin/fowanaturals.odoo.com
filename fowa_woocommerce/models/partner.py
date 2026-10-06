from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    woo_id = fields.Char("WooCommerce Customer ID", copy=False, index=True)

    @api.model
    def _woo_get_or_create(self, billing, shipping, woo_customer_id=None):
        """Match by Woo ID, then e-mail; otherwise create. Returns (invoice, delivery)."""
        woo_customer_id = str(woo_customer_id) if woo_customer_id else False
        email = (billing.get('email') or '').strip().lower()
        partner = False
        if woo_customer_id:
            partner = self.search([('woo_id', '=', woo_customer_id)], limit=1)
        if not partner and email:
            partner = self.search([('email', '=ilike', email), ('parent_id', '=', False)], limit=1)
        if not partner:
            partner = self.create(dict(self._woo_address_vals(billing), woo_id=woo_customer_id, email=email or False))
        elif woo_customer_id and not partner.woo_id:
            partner.woo_id = woo_customer_id

        delivery = partner
        if shipping.get('address_1') and shipping.get('address_1') != billing.get('address_1'):
            delivery = self.create(dict(self._woo_address_vals(shipping), parent_id=partner.id, type='delivery'))
        return partner, delivery

    @api.model
    def _woo_address_vals(self, a):
        country = self.env['res.country'].search([('code', '=', a.get('country'))], limit=1)
        state = self.env['res.country.state'].search(
            [('code', '=', a.get('state')), ('country_id', '=', country.id)], limit=1) if country else False
        name = f"{a.get('first_name', '')} {a.get('last_name', '')}".strip() or a.get('company') or a.get('email')
        return {
            'name': name, 'company_name': a.get('company') or False,
            'street': a.get('address_1') or False, 'street2': a.get('address_2') or False,
            'city': a.get('city') or False, 'zip': a.get('postcode') or False,
            'country_id': country.id or False, 'state_id': state.id if state else False,
            'phone': a.get('phone') or False,
        }
