# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestSaleCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestSaleToInvoice(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Create the SO with four order lines
        cls.sale_order = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
        })
        SaleOrderLine = cls.env['sale.order.line'].with_context(tracking_disable=True)
        cls.sol_prod_order = SaleOrderLine.create({
            'name': cls.company_data['product_order_no'].name,
            'product_id': cls.company_data['product_order_no'].id,
            'product_uom_qty': 5,
            'product_uom': cls.company_data['product_order_no'].uom_id.id,
            'price_unit': cls.company_data['product_order_no'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_deliver = SaleOrderLine.create({
            'name': cls.company_data['product_service_delivery'].name,
            'product_id': cls.company_data['product_service_delivery'].id,
            'product_uom_qty': 4,
            'product_uom': cls.company_data['product_service_delivery'].uom_id.id,
            'price_unit': cls.company_data['product_service_delivery'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_order = SaleOrderLine.create({
            'name': cls.company_data['product_service_order'].name,
            'product_id': cls.company_data['product_service_order'].id,
            'product_uom_qty': 3,
            'product_uom': cls.company_data['product_service_order'].uom_id.id,
            'price_unit': cls.company_data['product_service_order'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_prod_deliver = SaleOrderLine.create({
            'name': cls.company_data['product_delivery_no'].name,
            'product_id': cls.company_data['product_delivery_no'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_delivery_no'].uom_id.id,
            'price_unit': cls.company_data['product_delivery_no'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })

        # Confirm the SO
        cls.sale_order.action_confirm()

        # Create an invoice with invoiceable lines only
        payment = cls.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': [cls.sale_order.id],
            'active_id': cls.sale_order.id,
            'default_journal_id': cls.company_data['default_journal_sale'].id,
        }).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()

        cls.invoice = cls.sale_order.invoice_ids[0]

    def test_refund_create(self):
        # Validate invoice
        self.invoice.action_post()

        # Check quantity to invoice on SO lines
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
                self.assertFalse(line.invoice_lines, "The line based on delivered qty are not invoiced, so they should not be linked to invoice line")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(line.qty_to_invoice, 0.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEqual(line.qty_invoiced, 5.0, "The ordered (prod) sale line are totally invoiced (qty invoiced come from the invoice lines)")
                else:
                    self.assertEqual(line.qty_to_invoice, 0.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEqual(line.qty_invoiced, 3.0, "The ordered (serv) sale line are totally invoiced (qty invoiced = the invoice lines)")
                self.assertEqual(line.untaxed_amount_to_invoice, line.price_unit * line.qty_to_invoice, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, for ordered products")
                self.assertEqual(line.untaxed_amount_invoiced, line.price_unit * line.qty_invoiced, "Amount invoiced is now set as qty invoiced * unit price since no price change on invoice, for ordered products")
                self.assertEqual(len(line.invoice_lines), 1, "The lines 'ordered' qty are invoiced, so it should be linked to 1 invoice lines")

        # Make a credit note
        credit_note_wizard = self.env['account.move.reversal'].with_context({'active_ids': [self.invoice.id], 'active_id': self.invoice.id, 'active_model': 'account.move'}).create({
            'refund_method': 'refund',  # this is the only mode for which the SO line is linked to the refund (https://github.com/odoo/odoo/commit/e680f29560ac20133c7af0c6364c6ef494662eac)
            'reason': 'reason test create',
            'journal_id': self.invoice.journal_id.id,
        })
        credit_note_wizard.reverse_moves()
        invoice_refund = self.sale_order.invoice_ids.sorted(key=lambda inv: inv.id, reverse=False)[-1]  # the first invoice, its refund, and the new invoice

        # Check invoice's type and number
        self.assertEqual(invoice_refund.move_type, 'out_refund', 'The last created invoiced should be a refund')
        self.assertEqual(invoice_refund.state, 'draft', 'Last Customer invoices should be in draft')
        self.assertEqual(self.sale_order.invoice_count, 2, "The SO should have 2 related invoices: the original, the new refund")
        self.assertEqual(len(self.sale_order.invoice_ids.filtered(lambda inv: inv.move_type == 'out_refund')), 1, "The SO should be linked to only one refund")
        self.assertEqual(len(self.sale_order.invoice_ids.filtered(lambda inv: inv.move_type == 'out_invoice')), 1, "The SO should be linked to only one customer invoices")

        # At this time, the invoice 1 is opend (validated) and its refund is in draft, so the amounts invoiced are not zero for
        # invoiced sale line. The amounts only take validated invoice/refund into account.
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO line based on delivered qty")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
                self.assertFalse(line.invoice_lines, "The line based on delivered are not invoiced, so they should not be linked to invoice line")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(line.qty_to_invoice, 5.0, "As the refund is created, the invoiced quantity cancel each other (consu ordered)")
                    self.assertEqual(line.qty_invoiced, 0.0, "The qty to invoice should have decreased as the refund is created for ordered consu SO line")
                    self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "Amount to invoice is zero as the refund is not validated")
                    self.assertEqual(line.untaxed_amount_invoiced, line.price_unit * 5, "Amount invoiced is now set as unit price * ordered qty - refund qty) even if the ")
                    self.assertEqual(len(line.invoice_lines), 2, "The line 'ordered consumable' is invoiced, so it should be linked to 2 invoice lines (invoice and refund)")
                else:
                    self.assertEqual(line.qty_to_invoice, 3.0, "As the refund is created, the invoiced quantity cancel each other (consu ordered)")
                    self.assertEqual(line.qty_invoiced, 0.0, "The qty to invoice should have decreased as the refund is created for ordered service SO line")
                    self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "Amount to invoice is zero as the refund is not validated")
                    self.assertEqual(line.untaxed_amount_invoiced, line.price_unit * 3, "Amount invoiced is now set as unit price * ordered qty - refund qty) even if the ")
                    self.assertEqual(len(line.invoice_lines), 2, "The line 'ordered service' is invoiced, so it should be linked to 2 invoice lines (invoice and refund)")

        # Validate the refund
        invoice_refund.action_post()

        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
                self.assertFalse(line.invoice_lines, "The line based on delivered are not invoiced, so they should not be linked to invoice line")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(line.qty_to_invoice, 5.0, "As the refund still exists, the quantity to invoice is the ordered quantity")
                    self.assertEqual(line.qty_invoiced, 0.0, "The qty to invoice should be zero as, with the refund, the quantities cancel each other")
                    self.assertEqual(line.untaxed_amount_to_invoice, line.price_unit * 5, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, as refund is validated")
                    self.assertEqual(line.untaxed_amount_invoiced, 0.0, "Amount invoiced decreased as the refund is now confirmed")
                    self.assertEqual(len(line.invoice_lines), 2, "The line 'ordered consumable' is invoiced, so it should be linked to 2 invoice lines (invoice and refund)")
                else:
                    self.assertEqual(line.qty_to_invoice, 3.0, "As the refund still exists, the quantity to invoice is the ordered quantity")
                    self.assertEqual(line.qty_invoiced, 0.0, "The qty to invoice should be zero as, with the refund, the quantities cancel each other")
                    self.assertEqual(line.untaxed_amount_to_invoice, line.price_unit * 3, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, as refund is validated")
                    self.assertEqual(line.untaxed_amount_invoiced, 0.0, "Amount invoiced decreased as the refund is now confirmed")
                    self.assertEqual(len(line.invoice_lines), 2, "The line 'ordered service' is invoiced, so it should be linked to 2 invoice lines (invoice and refund)")

    def test_refund_cancel(self):
        """ Test invoice with a refund in 'cancel' mode, meaning a refund will be created and auto confirm to completely cancel the first
            customer invoice. The SO will have 2 invoice (customer + refund) in a paid state at the end. """
        # Increase quantity of an invoice lines
        with Form(self.invoice) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.quantity = 6
            with invoice_form.invoice_line_ids.edit(1) as line_form:
                line_form.quantity = 4

        # Validate invoice
        self.invoice.action_post()

        # Check quantity to invoice on SO lines
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
                self.assertFalse(line.invoice_lines, "The line based on delivered qty are not invoiced, so they should not be linked to invoice line")
            else:
                self.assertEqual(line.untaxed_amount_to_invoice, line.price_unit * line.qty_to_invoice, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, for ordered products")
                self.assertEqual(line.untaxed_amount_invoiced, line.price_unit * line.qty_invoiced, "Amount invoiced is now set as qty invoiced * unit price since no price change on invoice, for ordered products")
                self.assertEqual(len(line.invoice_lines), 1, "The lines 'ordered' qty are invoiced, so it should be linked to 1 invoice lines")

                self.assertEqual(line.qty_invoiced, line.product_uom_qty + 1, "The quantity invoiced is +1 unit from the one of the sale line, as we modified invoice lines (%s)" % (line.name,))
                self.assertEqual(line.qty_to_invoice, -1, "The quantity to invoice is negative as we invoice more than ordered")

        # Make a credit note
        credit_note_wizard = self.env['account.move.reversal'].with_context({'active_ids': self.invoice.ids, 'active_id': self.invoice.id, 'active_model': 'account.move'}).create({
            'refund_method': 'cancel',
            'reason': 'reason test cancel',
            'journal_id': self.invoice.journal_id.id,
        })
        invoice_refund = self.env['account.move'].browse(credit_note_wizard.reverse_moves()['res_id'])

        # Check invoice's type and number
        self.assertEqual(invoice_refund.move_type, 'out_refund', 'The last created invoiced should be a customer invoice')
        self.assertEqual(invoice_refund.payment_state, 'paid', 'Last Customer creadit note should be in paid state')
        self.assertEqual(self.sale_order.invoice_count, 2, "The SO should have 3 related invoices: the original, the refund, and the new one")
        self.assertEqual(len(self.sale_order.invoice_ids.filtered(lambda inv: inv.move_type == 'out_refund')), 1, "The SO should be linked to only one refund")
        self.assertEqual(len(self.sale_order.invoice_ids.filtered(lambda inv: inv.move_type == 'out_invoice')), 1, "The SO should be linked to only one customer invoices")

        # At this time, the invoice 1 is opened (validated) and its refund validated too, so the amounts invoiced are zero for
        # all sale line. All invoiceable Sale lines have
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO line based on delivered qty")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
                self.assertFalse(line.invoice_lines, "The line based on delivered are not invoiced, so they should not be linked to invoice line")
            else:
                self.assertEqual(line.qty_to_invoice, line.product_uom_qty, "The quantity to invoice should be the ordered quantity")
                self.assertEqual(line.qty_invoiced, 0, "The quantity invoiced is zero as the refund (paid) completely cancel the first invoice")

                self.assertEqual(line.untaxed_amount_to_invoice, line.price_unit * line.qty_to_invoice, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, for ordered products")
                self.assertEqual(line.untaxed_amount_invoiced, line.price_unit * line.qty_invoiced, "Amount invoiced is now set as qty invoiced * unit price since no price change on invoice, for ordered products")
                self.assertEqual(len(line.invoice_lines), 2, "The lines 'ordered' qty are invoiced, so it should be linked to 1 invoice lines")

    def test_refund_modify(self):
        """ Test invoice with a refund in 'modify' mode, and check customer invoices credit note is created from respective invoice """
        # Decrease quantity of an invoice lines
        with Form(self.invoice) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.quantity = 3
            with invoice_form.invoice_line_ids.edit(1) as line_form:
                line_form.quantity = 2

        # Validate invoice
        self.invoice.action_post()

        # Check quantity to invoice on SO lines
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
                self.assertFalse(line.invoice_lines, "The line based on delivered qty are not invoiced, so they should not be linked to invoice line")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(line.qty_to_invoice, 2.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEqual(line.qty_invoiced, 3.0, "The ordered (prod) sale line are totally invoiced (qty invoiced come from the invoice lines)")
                else:
                    self.assertEqual(line.qty_to_invoice, 1.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEqual(line.qty_invoiced, 2.0, "The ordered (serv) sale line are totally invoiced (qty invoiced = the invoice lines)")
                self.assertEqual(line.untaxed_amount_to_invoice, line.price_unit * line.qty_to_invoice, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, for ordered products")
                self.assertEqual(line.untaxed_amount_invoiced, line.price_unit * line.qty_invoiced, "Amount invoiced is now set as qty invoiced * unit price since no price change on invoice, for ordered products")
                self.assertEqual(len(line.invoice_lines), 1, "The lines 'ordered' qty are invoiced, so it should be linked to 1 invoice lines")

        # Make a credit note
        credit_note_wizard = self.env['account.move.reversal'].with_context({'active_ids': [self.invoice.id], 'active_id': self.invoice.id, 'active_model': 'account.move'}).create({
            'refund_method': 'modify',  # this is the only mode for which the SO line is linked to the refund (https://github.com/odoo/odoo/commit/e680f29560ac20133c7af0c6364c6ef494662eac)
            'reason': 'reason test modify',
            'journal_id': self.invoice.journal_id.id,
        })
        invoice_refund = self.env['account.move'].browse(credit_note_wizard.reverse_moves()['res_id'])

        # Check invoice's type and number
        self.assertEqual(invoice_refund.move_type, 'out_invoice', 'The last created invoiced should be a customer invoice')
        self.assertEqual(invoice_refund.state, 'draft', 'Last Customer invoices should be in draft')
        self.assertEqual(self.sale_order.invoice_count, 3, "The SO should have 3 related invoices: the original, the refund, and the new one")
        self.assertEqual(len(self.sale_order.invoice_ids.filtered(lambda inv: inv.move_type == 'out_refund')), 1, "The SO should be linked to only one refund")
        self.assertEqual(len(self.sale_order.invoice_ids.filtered(lambda inv: inv.move_type == 'out_invoice')), 2, "The SO should be linked to two customer invoices")

        # At this time, the invoice 1 and its refund are confirmed, so the amounts invoiced are zero. The third invoice
        # (2nd customer inv) is in draft state.
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
                self.assertFalse(line.invoice_lines, "The line based on delivered are not invoiced, so they should not be linked to invoice line")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(line.qty_to_invoice, 2.0, "The qty to invoice does not change when confirming the new invoice (2)")
                    self.assertEqual(line.qty_invoiced, 3.0, "The ordered (prod) sale line does not change on invoice 2 confirmation")
                    self.assertEqual(line.untaxed_amount_to_invoice, line.price_unit * 5, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, for ordered products")
                    self.assertEqual(line.untaxed_amount_invoiced, 0.0, "Amount invoiced is zero as the invoice 1 and its refund are reconcilied")
                    self.assertEqual(len(line.invoice_lines), 3, "The line 'ordered consumable' is invoiced, so it should be linked to 3 invoice lines (invoice and refund)")
                else:
                    self.assertEqual(line.qty_to_invoice, 1.0, "The qty to invoice does not change when confirming the new invoice (2)")
                    self.assertEqual(line.qty_invoiced, 2.0, "The ordered (serv) sale line does not change on invoice 2 confirmation")
                    self.assertEqual(line.untaxed_amount_to_invoice, line.price_unit * 3, "Amount to invoice is now set as unit price * ordered qty - refund qty) even if the ")
                    self.assertEqual(line.untaxed_amount_invoiced, 0.0, "Amount invoiced is zero as the invoice 1 and its refund are reconcilied")
                    self.assertEqual(len(line.invoice_lines), 3, "The line 'ordered service' is invoiced, so it should be linked to 3 invoice lines (invoice and refund)")

        # Change unit of ordered product on refund lines
        move_form = Form(invoice_refund)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 100
        with move_form.invoice_line_ids.edit(1) as line_form:
            line_form.price_unit = 50
        invoice_refund = move_form.save()

        # Validate the refund
        invoice_refund.action_post()

        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
                self.assertFalse(line.invoice_lines, "The line based on delivered are not invoiced, so they should not be linked to invoice line, even after validation")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(line.qty_to_invoice, 2.0, "The qty to invoice does not change when confirming the new invoice (3)")
                    self.assertEqual(line.qty_invoiced, 3.0, "The ordered sale line are totally invoiced (qty invoiced = ordered qty)")
                    self.assertEqual(line.untaxed_amount_to_invoice, 1100.0, "")
                    self.assertEqual(line.untaxed_amount_invoiced, 300.0, "")
                    self.assertEqual(len(line.invoice_lines), 3, "The line 'ordered consumable' is invoiced, so it should be linked to 2 invoice lines (invoice and refund), even after validation")
                else:
                    self.assertEqual(line.qty_to_invoice, 1.0, "The qty to invoice does not change when confirming the new invoice (3)")
                    self.assertEqual(line.qty_invoiced, 2.0, "The ordered sale line are totally invoiced (qty invoiced = ordered qty)")
                    self.assertEqual(line.untaxed_amount_to_invoice, 170.0, "")
                    self.assertEqual(line.untaxed_amount_invoiced, 100.0, "")
                    self.assertEqual(len(line.invoice_lines), 3, "The line 'ordered service' is invoiced, so it should be linked to 2 invoice lines (invoice and refund), even after validation")

    def test_refund_invoice_with_downpayment(self):
        sale_order_refund = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
        })
        sol_product = self.env['sale.order.line'].create({
            'name': self.company_data['product_order_no'].name,
            'product_id': self.company_data['product_order_no'].id,
            'product_uom_qty': 5,
            'product_uom': self.company_data['product_order_no'].uom_id.id,
            'price_unit': self.company_data['product_order_no'].list_price,
            'order_id': sale_order_refund.id,
            'tax_id': False,
        })

        sale_order_refund.action_confirm()
        so_context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order_refund.id],
            'active_id': sale_order_refund.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create({
            'advance_payment_method': 'percentage',
            'amount': 50,
            'deposit_account_id': self.company_data['default_account_revenue'].id
        })
        downpayment.create_invoices()
        sale_order_refund.invoice_ids[0].action_post()
        sol_downpayment = sale_order_refund.order_line[1]

        payment = self.env['sale.advance.payment.inv'].with_context(so_context).create({
            'deposit_account_id': self.company_data['default_account_revenue'].id
        })
        payment.create_invoices()

        so_invoice = max(sale_order_refund.invoice_ids)
        self.assertEqual(len(so_invoice.invoice_line_ids.filtered(lambda l: not (l.display_type == 'line_section' and l.name == "Down Payments"))), len(sale_order_refund.order_line), 'All lines should be invoiced')
        self.assertEqual(len(so_invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'line_section' and l.name == "Down Payments")), 1, 'A single section for downpayments should be present')
        self.assertEqual(so_invoice.amount_total, sale_order_refund.amount_total - sol_downpayment.price_unit, 'Downpayment should be applied')
        so_invoice.action_post()

        credit_note_wizard = self.env['account.move.reversal'].with_context({'active_ids': [so_invoice.id], 'active_id': so_invoice.id, 'active_model': 'account.move'}).create({
            'refund_method': 'refund',
            'reason': 'reason test refund with downpayment',
            'journal_id': so_invoice.journal_id.id,
        })
        credit_note_wizard.reverse_moves()
        invoice_refund = sale_order_refund.invoice_ids.sorted(key=lambda inv: inv.id, reverse=False)[-1]
        invoice_refund.action_post()

        self.assertEqual(sol_product.qty_to_invoice, 5.0, "As the refund still exists, the quantity to invoice is the ordered quantity")
        self.assertEqual(sol_product.qty_invoiced, 0.0, "The qty invoiced should be zero as, with the refund, the quantities cancel each other")
        self.assertEqual(sol_product.untaxed_amount_to_invoice, sol_product.price_unit * 5, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, as refund is validated")
        self.assertEqual(sol_product.untaxed_amount_invoiced, 0.0, "Amount invoiced decreased as the refund is now confirmed")
        self.assertEqual(len(sol_product.invoice_lines), 2, "The product line is invoiced, so it should be linked to 2 invoice lines (invoice and refund)")

        self.assertEqual(sol_downpayment.qty_to_invoice, -1.0, "As the downpayment was invoiced separately, it will still have to be deducted from the total invoice (hence -1.0), after the refund.")
        self.assertEqual(sol_downpayment.qty_invoiced, 1.0, "The qty to invoice should be 1 as, with the refund, the products are not invoiced anymore, but the downpayment still is")
        self.assertEqual(sol_downpayment.untaxed_amount_to_invoice, -(sol_product.price_unit * 5)/2, "Amount to invoice decreased as the refund is now confirmed")
        self.assertEqual(sol_downpayment.untaxed_amount_invoiced, (sol_product.price_unit * 5)/2, "Amount invoiced is now set as half of all products' total amount to invoice, as refund is validated")
        self.assertEqual(len(sol_downpayment.invoice_lines), 3, "The product line is invoiced, so it should be linked to 3 invoice lines (downpayment invoice, partial invoice and refund)")
