import hashlib
import hmac
import pprint

from werkzeug.exceptions import Forbidden, ServiceUnavailable

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment.logging import get_payment_logger

_logger = get_payment_logger(__name__)


class PaysuiteController(http.Controller):
    _return_url = '/payment/paysuite/return'
    _webhook_url = '/payment/paysuite/webhook'

    @http.route(
        _return_url,
        type='http',
        auth='public',
        methods=['GET', 'POST'],
        csrf=False,
        save_session=False,
    )
    def paysuite_return_from_checkout(self, **data):
        """Cliente de volta do checkout: consulta o estado real e mostra o resultado.

        :param dict data: apenas a referência da transação (`ref`) embutida no return_url.
        """
        _logger.info("handling redirection from PaySuite with data:\n%s", pprint.pformat(data))
        try:
            self._verify_and_process(data)
        except ValidationError:
            _logger.error("Unable to process the payment data")
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def paysuite_webhook(self, **data):
        """Recebe o webhook, valida a assinatura X-Signature e sincroniza com a API."""
        _logger.info("notification received from PaySuite with data:\n%s", pprint.pformat(data))

        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
            'paysuite', data
        )
        if not tx_sudo:
            return ""

        self._verify_signature(tx_sudo)

        try:
            self._verify_and_process(data)
        except ValidationError as error:
            _logger.error("Unable to process the payment data")
            raise ServiceUnavailable from error
        return ""  # Acknowledge the notification

    @staticmethod
    def _verify_signature(tx_sudo):
        """Valida o HMAC-SHA256 do corpo bruto com o webhook secret do provider."""
        raw_body = request.httprequest.get_data()
        received = request.httprequest.headers.get('X-Signature', '')
        secret = tx_sudo.provider_id.paysuite_webhook_secret or ''
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        if not secret or not hmac.compare_digest(expected, received):
            _logger.warning("PaySuite webhook with invalid signature (tx %s)", tx_sudo.reference)
            raise Forbidden()

    @staticmethod
    def _verify_and_process(data):
        """Consulta GET /payments/{id} e regista o estado na transação."""
        tx_sudo = request.env['payment.transaction'].sudo()._search_by_reference(
            'paysuite', data
        )
        if not tx_sudo or not tx_sudo.provider_reference:
            return

        response = tx_sudo._send_api_request(
            'GET', f'/payments/{tx_sudo.provider_reference}'
        )
        tx_sudo._record(response['data'])