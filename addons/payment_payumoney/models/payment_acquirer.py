# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib

from odoo import api, fields, models


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('payumoney', "PayUmoney")], ondelete={'payumoney': 'set default'})
    payumoney_merchant_key = fields.Char(
        string="Merchant Key", help="The key solely used to identify the account with PayU money",
        required_if_provider='payumoney')
    payumoney_merchant_salt = fields.Char(
        string="Merchant Salt", required_if_provider='payumoney', groups='base.group_system')

    @api.model
    def _get_compatible_acquirers(self, *args, currency_id=None, **kwargs):
        """ Override of payment to unlist PayUmoney acquirers when the currency is not INR. """
        acquirers = super()._get_compatible_acquirers(*args, currency_id=currency_id, **kwargs)

        currency = self.env['res.currency'].browse(currency_id).exists()
        if currency and currency.name != 'INR':
            acquirers = acquirers.filtered(lambda a: a.provider != 'payumoney')

        return acquirers

    def _payumoney_generate_sign(self, values, incoming=True):
        """ Generate the shasign for incoming or outgoing communications.

        :param dict values: The values used to generate the signature
        :param bool incoming: Whether the signature must be generated for an incoming (PayUmoney to
                              Odoo) or outgoing (Odoo to PayUMoney) communication.
        :return: The shasign
        :rtype: str
        """
        sign_values = {
            **values,
            'key': self.payumoney_merchant_key,
            'salt': self.payumoney_merchant_salt,
        }
        if incoming:
            keys = 'salt|status||||||udf5|udf4|udf3|udf2|udf1|email|firstname|productinfo|amount|' \
                   'txnid|key'
            sign = '|'.join(f'{sign_values.get(k) or ""}' for k in keys.split('|'))
        else:  # outgoing
            keys = 'key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5||||||salt'
            sign = '|'.join(f'{sign_values.get(k) or ""}' for k in keys.split('|'))
        return hashlib.sha512(sign.encode('utf-8')).hexdigest()

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'payumoney':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_payumoney.payment_method_payumoney').id
