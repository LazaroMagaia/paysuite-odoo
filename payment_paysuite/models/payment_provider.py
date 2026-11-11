from odoo import fields, models
from odoo.tools import urls

from odoo.addons.payment_paysuite import const

API_BASE_URL = 'https://paysuite.tech/api/v1/'


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('paysuite', "PaySuite")],
        ondelete={'paysuite': 'set default'},
    )
    paysuite_api_token = fields.Char(
        string="API Token",
        help="Token em Settings > API Access no painel do PaySuite (conta de empresa).",
        required_if_provider='paysuite',
        copy=False,
        groups='base.group_system',
    )
    paysuite_sync_contacts = fields.Boolean(
        string="Sync Customers as PaySuite Contacts",
        help="When enabled, the customer's name, email and phone number are sent to "
             "PaySuite to find or create a contact linked to each payment. "
             "Disabled by default: no personal data is sent unless you enable it.",
        default=False,
    )
    paysuite_webhook_secret = fields.Char(
        string="Webhook Secret",
        help="Segredo usado para validar a assinatura X-Signature dos webhooks.",
        required_if_provider='paysuite',
        copy=False,
        groups='base.group_system',
    )

    # === BUSINESS METHODS === #

    def _get_supported_currencies(self):
        supported_currencies = super()._get_supported_currencies()
        if self.code != 'paysuite':
            return supported_currencies
        return supported_currencies.filtered(
            lambda c: c.name in const.SUPPORTED_CURRENCIES
        )

    def _get_default_payment_method_codes(self):
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'paysuite':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # === REQUEST HELPERS === #

    def _build_request_url(self, endpoint, **kwargs):
        if self.code != 'paysuite':
            return super()._build_request_url(endpoint, **kwargs)
        return urls.urljoin(API_BASE_URL, endpoint.lstrip('/'))

    def _build_request_headers(self, method, endpoint, payload, **kwargs):
        if self.code != 'paysuite':
            return super()._build_request_headers(method, endpoint, payload, **kwargs)
        return {
            'Authorization': f'Bearer {self.paysuite_api_token}',
            'Accept': 'application/json',
        }

    def _parse_response_error(self, response):
        if self.code != 'paysuite':
            return super()._parse_response_error(response)
        try:
            return response.json().get('message', '')
        except ValueError:
            return response.text