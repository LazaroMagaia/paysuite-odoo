import re

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_paysuite.controllers.main import PaysuiteController

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        """Override of payment to return PaySuite-specific rendering values."""
        if self.provider_code != "paysuite":
            return super()._get_specific_rendering_values(processing_values)

        payload = self._paysuite_prepare_payment_request_payload()
        try:
            response = self._send_api_request("POST", "/payments", json=payload)
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        payment_data = response.get("data", {})
        # Needed to fetch the payment status after the redirection and in the webhook.
        self.provider_reference = payment_data.get("id")

        checkout_url = payment_data["checkout_url"]
        return {
            "api_url": checkout_url,
            "http_method": "get",
            "url_params": payment_utils.extract_url_params(checkout_url),
        }

    def _paysuite_prepare_payment_request_payload(self):
        base_url = self.provider_id.get_base_url()
        return_url = urls.urljoin(base_url, PaysuiteController._return_url)
        webhook_url = urls.urljoin(base_url, PaysuiteController._webhook_url)

        # PaySuite only accepts ASCII letters and digits (max 50 chars) in the reference.
        clean_ref = re.sub(r"[^A-Za-z0-9]", "", self.reference)[:35]
        paysuite_reference = f"{clean_ref}T{self.id}"

        payload = {
            "amount": f"{self.amount:.2f}",
            "reference": paysuite_reference,
            "description": (self.reference or "")[:125],
            # PaySuite does not send our reference back on redirection, so we include it.
            "return_url": f"{return_url}?ref={self.reference}",
            "webhook_url": f"{webhook_url}?ref={self.reference}",
        }

        contact_id = self._paysuite_get_or_create_contact_id()
        if contact_id:
            payload["contact_id"] = contact_id
        return payload

    def _paysuite_get_or_create_contact_id(self):
        """Find the PaySuite contact by email, or create it if it does not exist.

        Only runs when the provider has "Sync Customers as PaySuite Contacts" enabled.
        Never blocks the payment: on failure, the payment proceeds without contact_id.
        """
        self.ensure_one()
        # Opt-in: no personal data is sent to PaySuite unless the provider enables it.
        if not self.provider_id.paysuite_sync_contacts:
            return None

        email = (self.partner_email or "").strip().lower()[:100]
        phone = self._paysuite_normalize_phone(self.partner_phone)
        name = (self.partner_name or "").strip()[:100] or email.split("@")[0]

        if not email and not phone:
            return None

        try:
            # 1. Look up by email
            if email:
                response = self._send_api_request(
                    "GET", "/contacts", params={"email": email, "limit": 100}
                )
                for contact in response.get("data", []):
                    if (contact.get("email") or "").strip().lower() == email:
                        return contact["id"]

            # 2. Not found: create it
            contact_payload = {"name": name}
            if email:
                contact_payload["email"] = email
            if phone:
                contact_payload["phone"] = phone
            response = self._send_api_request("POST", "/contacts", json=contact_payload)
            return response.get("data", {}).get("id")
        except ValidationError as error:
            _logger.warning(
                "PaySuite contact lookup/creation failed for %s: %s", self.reference, error
            )
            return None

    @staticmethod
    def _paysuite_normalize_phone(phone):
        """Convert to E.164, assuming Mozambique (+258) when there is no prefix."""
        value = re.sub(r"[^\d+]", "", phone or "")
        if not value:
            return ""
        if value.startswith("00"):
            value = "+" + value[2:]
        elif not value.startswith("+"):
            if value.startswith("258") and len(value) == 12:
                value = "+" + value
            else:
                value = "+258" + value.lstrip("0")
        return value[:20]

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        if provider_code != "paysuite":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("ref")

    def _extract_amount_data(self, payment_data):
        if self.provider_code != "paysuite":
            return super()._extract_amount_data(payment_data)
        # PaySuite only supports MZN and does not return the currency.
        return {"amount": float(payment_data["amount"]), "currency_code": "MZN"}

    def _apply_updates(self, payment_data):
        """Update the transaction from the data of GET /payments/{id}."""
        if self.provider_code != "paysuite":
            super()._apply_updates(payment_data)
            return

        self.provider_reference = payment_data["id"]

        status = payment_data.get("status")
        if status == "pending":
            self._set_pending()
        elif status == "completed":
            self._set_done()
        elif status in ("failed", "cancelled", "expired"):
            self._set_canceled(self.env._("Payment with status: %s", status))
        else:
            _logger.info(
                "Received invalid payment status (%s) for transaction %s.",
                status, self.reference,
            )
            self._set_error(self.env._("Received invalid payment status: %s.", status))