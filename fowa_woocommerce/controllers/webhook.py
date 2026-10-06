import base64
import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WooWebhook(http.Controller):

    @http.route('/fowa_woo/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def webhook(self, **kw):
        body = request.httprequest.get_data()
        secret = request.env['ir.config_parameter'].sudo().get_param('fowa_woo.webhook_secret')
        if not secret:
            return request.make_response('webhook secret not configured', status=503)
        expected = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
        given = request.httprequest.headers.get('X-WC-Webhook-Signature', '')
        if not hmac.compare_digest(expected, given):
            return request.make_response('invalid signature', status=401)

        topic = request.httprequest.headers.get('X-WC-Webhook-Topic', '')
        try:
            payload = json.loads(body or b'{}')
        except ValueError:
            return request.make_response('ok')  # Woo's ping on webhook creation isn't JSON
        env = request.env(su=True)
        try:
            if topic.startswith('order.'):
                env['sale.order']._woo_upsert_order(payload)
            elif topic.startswith('product.'):
                env['product.template']._woo_upsert_product(payload)
        except Exception:
            _logger.exception("Webhook %s failed", topic)
            return request.make_response('error', status=500)  # Woo retries on failure
        return request.make_response('ok')
