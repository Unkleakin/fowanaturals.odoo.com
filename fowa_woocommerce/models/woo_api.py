import logging

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 30
PER_PAGE = 100


class WooApi(models.AbstractModel):
    _name = 'fowa.woo.api'
    _description = 'WooCommerce REST API client'

    @api.model
    def _credentials(self):
        icp = self.env['ir.config_parameter'].sudo()
        url = (icp.get_param('fowa_woo.url') or '').rstrip('/')
        key = icp.get_param('fowa_woo.consumer_key')
        secret = icp.get_param('fowa_woo.consumer_secret')
        if not (url and key and secret):
            raise UserError(_("WooCommerce is not configured. Go to Settings > WooCommerce."))
        return url, key, secret

    @api.model
    def request(self, method, endpoint, params=None, json=None):
        url, key, secret = self._credentials()
        resp = requests.request(
            method, f"{url}/wp-json/wc/v3/{endpoint.lstrip('/')}",
            auth=(key, secret), params=params, json=json, timeout=TIMEOUT,
        )
        if not resp.ok:
            _logger.error("WooCommerce %s %s failed: %s %s", method, endpoint, resp.status_code, resp.text[:500])
            raise UserError(_("WooCommerce error %s on %s: %s", resp.status_code, endpoint, resp.text[:300]))
        return resp

    @api.model
    def get_all(self, endpoint, params=None):
        """Yield every record of a paginated collection."""
        params = dict(params or {}, per_page=PER_PAGE, page=1)
        while True:
            resp = self.request('GET', endpoint, params=params)
            data = resp.json()
            yield from data
            if params['page'] >= int(resp.headers.get('X-WP-TotalPages', 1)):
                break
            params['page'] += 1

    @api.model
    def test_connection(self):
        resp = self.request('GET', 'system_status')
        return resp.json().get('environment', {}).get('site_url')
