# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import float_is_zero
from .common import TestSaleCommon
from odoo.tests import Form, tagged
from odoo import Command, fields


@tagged('-at_install', 'post_install')
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

        # Context
        cls.context = {
            'active_model': 'sale.order',
            'active_ids': [cls.sale_order.id],
            'active_id': cls.sale_order.id,
            'default_journal_id': cls.company_data['default_journal_sale'].id,
        }

    def _check_order_search(self, orders, domain, expected_result):
        domain += [('id', 'in', orders.ids)]
        result = self.env['sale.order'].search(domain)
        self.assertEqual(result, expected_result, "Unexpected result on search orders")

    def test_search_invoice_ids(self):
        """Test searching on computed fields invoice_ids"""

        # Make qty zero to have a line without invoices
        self.sol_prod_order.product_uom_qty = 0
        self.sale_order.action_confirm()

        # Tests before creating an invoice
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.sale_order)
        self._check_order_search(self.sale_order, [('invoice_ids', '!=', False)], self.env['sale.order'])

        # Create invoice
        moves = self.sale_order._create_invoices()

        # Tests after creating the invoice
        self._check_order_search(self.sale_order, [('invoice_ids', 'in', moves.ids)], self.sale_order)
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.env['sale.order'])
        self._check_order_search(self.sale_order, [('invoice_ids', '!=', False)], self.sale_order)

    def test_downpayment(self):
        """ Test invoice with a way of downpayment and check downpayment's SO line is created
            and also check a total amount of invoice is equal to a respective sale order's total amount
        """
        # Confirm the SO
        self.sale_order.action_confirm()
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.sale_order)
        # Let's do an invoice for a deposit of 100
        downpayment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
            'deposit_account_id': self.company_data['default_account_revenue'].id
        })
        downpayment.create_invoices()
        downpayment2 = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
            'deposit_account_id': self.company_data['default_account_revenue'].id
        })
        downpayment2.create_invoices()
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.env['sale.order'])

        self.assertEqual(len(self.sale_order.invoice_ids), 2, 'Invoice should be created for the SO')
        downpayment_line = self.sale_order.order_line.filtered(lambda l: l.is_downpayment)
        self.assertEqual(len(downpayment_line), 2, 'SO line downpayment should be created on SO')

        # Update delivered quantity of SO lines
        self.sol_serv_deliver.write({'qty_delivered': 4.0})
        self.sol_prod_deliver.write({'qty_delivered': 2.0})

        # Let's do an invoice with refunds
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'deposit_account_id': self.company_data['default_account_revenue'].id
        })
        payment.create_invoices()

        self.assertEqual(len(self.sale_order.invoice_ids), 3, 'Invoice should be created for the SO')

        invoice = max(self.sale_order.invoice_ids)
        self.assertEqual(len(invoice.invoice_line_ids.filtered(lambda l: not (l.display_type == 'line_section' and l.name == "Down Payments"))), len(self.sale_order.order_line), 'All lines should be invoiced')
        self.assertEqual(len(invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'line_section' and l.name == "Down Payments")), 1, 'A single section for downpayments should be present')
        self.assertEqual(invoice.amount_total, self.sale_order.amount_total - sum(downpayment_line.mapped('price_unit')), 'Downpayment should be applied')

    def test_downpayment_line_remains_on_SO(self):
        """ Test downpayment's SO line is created and remains unchanged even if everything is invoiced
        """
        # Create the SO with one line
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
        })
        sale_order_line = self.env['sale.order.line'].with_context(tracking_disable=True).create({
            'name': self.company_data['product_order_no'].name,
            'product_id': self.company_data['product_order_no'].id,
            'product_uom_qty': 5,
            'product_uom': self.company_data['product_order_no'].uom_id.id,
            'price_unit': self.company_data['product_order_no'].list_price,
            'order_id': sale_order.id,
            'tax_id': False,
        })
        # Confirm the SO
        sale_order.action_confirm()
        # Update delivered quantity of SO line
        sale_order_line.write({'qty_delivered': 5.0})
        context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        # Let's do an invoice for a down payment of 50
        downpayment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
            'deposit_account_id': self.company_data['default_account_revenue'].id
        })
        downpayment.create_invoices()
        # Let's do the invoice for the remaining amount
        payment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'deposit_account_id': self.company_data['default_account_revenue'].id
        })
        payment.create_invoices()
        # Confirm all invoices
        downpayment_line = sale_order.order_line.filtered(lambda l: l.is_downpayment)
        self.assertEqual(downpayment_line[0].price_unit, 50, 'The down payment unit price should not change on SO')
        sale_order.invoice_ids.action_post()
        self.assertEqual(downpayment_line[0].price_unit, 50, 'The down payment unit price should not change on SO')

    def test_downpayment_percentage_tax_icl(self):
        """ Test invoice with a percentage downpayment and an included tax
            Check the total amount of invoice is correct and equal to a respective sale order's total amount
        """
        # Confirm the SO
        self.sale_order.action_confirm()
        tax_downpayment = self.company_data['default_tax_sale'].copy({'price_include': True})
        # Let's do an invoice for a deposit of 100
        product_id = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')
        product_id = self.env['product.product'].browse(int(product_id)).exists()
        product_id.taxes_id = tax_downpayment.ids
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'percentage',
            'amount': 50,
            'deposit_account_id': self.company_data['default_account_revenue'].id,
        })
        payment.create_invoices()

        self.assertEqual(len(self.sale_order.invoice_ids), 1, 'Invoice should be created for the SO')
        downpayment_line = self.sale_order.order_line.filtered(lambda l: l.is_downpayment)
        self.assertEqual(len(downpayment_line), 1, 'SO line downpayment should be created on SO')
        self.assertEqual(downpayment_line.price_unit, self.sale_order.amount_total/2, 'downpayment should have the correct amount')

        invoice = self.sale_order.invoice_ids[0]
        downpayment_aml = invoice.line_ids.filtered(lambda l: not (l.display_type == 'line_section' and l.name == "Down Payments"))[0]
        self.assertEqual(downpayment_aml.price_total, self.sale_order.amount_total/2, 'downpayment should have the correct amount')
        self.assertEqual(downpayment_aml.price_unit, self.sale_order.amount_total/2, 'downpayment should have the correct amount')
        invoice.action_post()
        self.assertEqual(downpayment_line.price_unit, self.sale_order.amount_total/2, 'downpayment should have the correct amount')

    def test_downpayment_invoice_and_partial_credit_note(self):
        """This test check that the downpayment line amount on the sale order remains consistent"""
        self.sale_order.action_confirm()

        # Create an invoice for a Down payment of 100
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 100,
            'deposit_account_id': self.company_data['default_account_revenue'].id,
        })
        payment.create_invoices()

        # Ensure the downpayment line on the sale order is correctly set to 100
        downpayment_line = self.sale_order.order_line.filtered(lambda l: l.is_downpayment)
        self.assertEqual(downpayment_line.price_unit, 100)

        # post the downpayment invoice and ensure the downpayment_line amount is still 100
        downpayment_invoice = downpayment_line.order_id.order_line.invoice_lines.move_id
        downpayment_invoice.action_post()
        self.assertEqual(downpayment_line.price_unit, 100)

        # Create a credit note for a part of the downpayment invoice and post it
        move_reversal = self.env['account.move.reversal'].with_context(
            active_model="account.move",
            active_ids=downpayment_invoice.ids,
        ).create({
            'date': '2020-02-01',
            'reason': 'no reason',
            'refund_method': 'refund',
            'journal_id': downpayment_invoice.journal_id.id,
        })
        reversal_action = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal_action['res_id'])
        with Form(reverse_move) as form_reverse:
            with form_reverse.invoice_line_ids.edit(0) as line_form:
                line_form.price_unit = 20.0
        reverse_move.action_post()

        self.assertEqual(downpayment_line.price_unit, 80,
                         "The downpayment line amount should be equal to the sum of the invoice and credit note amount")

    def test_invoice_with_discount(self):
        """ Test invoice with a discount and check discount applied on both SO lines and an invoice lines """
        # Update discount and delivered quantity on SO lines
        self.sol_prod_order.write({'discount': 20.0})
        self.sol_serv_deliver.write({'discount': 20.0, 'qty_delivered': 4.0})
        self.sol_serv_order.write({'discount': -10.0})
        self.sol_prod_deliver.write({'qty_delivered': 2.0})

        for line in self.sale_order.order_line.filtered(lambda l: l.discount):
            product_price = line.price_unit * line.product_uom_qty
            self.assertEqual(line.discount, (product_price - line.price_subtotal) / product_price * 100, 'Discount should be applied on order line')

        # lines are in draft
        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_to_invoice, precision_digits=2), "The amount to invoice should be zero, as the line is in draf state")
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        self.sale_order.action_confirm()

        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        self.assertEqual(self.sol_serv_order.untaxed_amount_to_invoice, 297, "The untaxed amount to invoice is wrong")
        self.assertEqual(self.sol_serv_deliver.untaxed_amount_to_invoice, self.sol_serv_deliver.qty_delivered * self.sol_serv_deliver.price_reduce, "The untaxed amount to invoice should be qty deli * price reduce, so 4 * (180 - 36)")
        # 'untaxed_amount_to_invoice' is invalid when 'sale_stock' is installed.
        # self.assertEqual(self.sol_prod_deliver.untaxed_amount_to_invoice, 140, "The untaxed amount to invoice should be qty deli * price reduce, so 4 * (180 - 36)")

        # Let's do an invoice with invoiceable lines
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.sale_order)
        payment.create_invoices()
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.env['sale.order'])
        invoice = self.sale_order.invoice_ids[0]
        invoice.action_post()

        # Check discount appeared on both SO lines and invoice lines
        for line, inv_line in zip(self.sale_order.order_line, invoice.invoice_line_ids):
            self.assertEqual(line.discount, inv_line.discount, 'Discount on lines of order and invoice should be same')

    def test_invoice(self):
        """ Test create and invoice from the SO, and check qty invoice/to invoice, and the related amounts """
        # lines are in draft
        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_to_invoice, precision_digits=2), "The amount to invoice should be zero, as the line is in draf state")
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        # Confirm the SO
        self.sale_order.action_confirm()

        # Check ordered quantity, quantity to invoice and invoiced quantity of SO lines
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, 'Quantity to invoice should be same as ordered quantity')
                self.assertEqual(line.qty_invoiced, 0.0, 'Invoiced quantity should be zero as no any invoice created for SO')
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
            else:
                self.assertEqual(line.qty_to_invoice, line.product_uom_qty, 'Quantity to invoice should be same as ordered quantity')
                self.assertEqual(line.qty_invoiced, 0.0, 'Invoiced quantity should be zero as no any invoice created for SO')
                self.assertEqual(line.untaxed_amount_to_invoice, line.product_uom_qty * line.price_unit, "The amount to invoice should the total of the line, as the line is confirmed")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line is confirmed")

        # Let's do an invoice with invoiceable lines
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()

        invoice = self.sale_order.invoice_ids[0]

        # Update quantity of an invoice lines
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 3.0
        with move_form.invoice_line_ids.edit(1) as line_form:
            line_form.quantity = 2.0
        invoice = move_form.save()

        # amount to invoice / invoiced should not have changed (amounts take only confirmed invoice into account)
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be zero")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as delivered lines are not delivered yet")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity (no confirmed invoice)")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as no invoice are validated for now")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(self.sol_prod_order.qty_to_invoice, 2.0, "Changing the quantity on draft invoice update the qty to invoice on SO lines")
                    self.assertEqual(self.sol_prod_order.qty_invoiced, 3.0, "Changing the quantity on draft invoice update the invoiced qty on SO lines")
                else:
                    self.assertEqual(self.sol_serv_order.qty_to_invoice, 1.0, "Changing the quantity on draft invoice update the qty to invoice on SO lines")
                    self.assertEqual(self.sol_serv_order.qty_invoiced, 2.0, "Changing the quantity on draft invoice update the invoiced qty on SO lines")
                self.assertEqual(line.untaxed_amount_to_invoice, line.product_uom_qty * line.price_unit, "The amount to invoice should the total of the line, as the line is confirmed (no confirmed invoice)")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as no invoice are validated for now")

        invoice.action_post()

        # Check quantity to invoice on SO lines
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(line.qty_to_invoice, 2.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEqual(line.qty_invoiced, 3.0, "The ordered (prod) sale line are totally invoiced (qty invoiced come from the invoice lines)")
                else:
                    self.assertEqual(line.qty_to_invoice, 1.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEqual(line.qty_invoiced, 2.0, "The ordered (serv) sale line are totally invoiced (qty invoiced = the invoice lines)")
                self.assertEqual(line.untaxed_amount_to_invoice, line.price_unit * line.qty_to_invoice, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, for ordered products")
                self.assertEqual(line.untaxed_amount_invoiced, line.price_unit * line.qty_invoiced, "Amount invoiced is now set as qty invoiced * unit price since no price change on invoice, for ordered products")

    def test_multiple_sale_orders_on_same_invoice(self):
        """ The model allows the association of multiple SO lines linked to the same invoice line.
            Check that the operations behave well, if a custom module creates such a situation.
        """
        self.sale_order.action_confirm()
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()

        # create a second SO whose lines are linked to the same invoice lines
        # this is a way to create a situation where sale_line_ids has multiple items
        sale_order_data = self.sale_order.copy_data()[0]
        sale_order_data['order_line'] = [
            (0, 0, line.copy_data({
                'invoice_lines': [(6, 0, line.invoice_lines.ids)],
            })[0])
            for line in self.sale_order.order_line
        ]
        self.sale_order.create(sale_order_data)

        # we should now have at least one move line linked to several order lines
        invoice = self.sale_order.invoice_ids[0]
        self.assertTrue(any(len(move_line.sale_line_ids) > 1
                            for move_line in invoice.line_ids))

        # however these actions should not raise
        invoice.action_post()
        invoice.button_draft()
        invoice.button_cancel()

    def test_invoice_with_sections(self):
        """ Test create and invoice with sections from the SO, and check qty invoice/to invoice, and the related amounts """

        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
        })

        SaleOrderLine = self.env['sale.order.line'].with_context(tracking_disable=True)
        SaleOrderLine.create({
            'name': 'Section',
            'display_type': 'line_section',
            'order_id': sale_order.id,
        })
        sol_prod_deliver = SaleOrderLine.create({
            'name': self.company_data['product_order_no'].name,
            'product_id': self.company_data['product_order_no'].id,
            'product_uom_qty': 5,
            'product_uom': self.company_data['product_order_no'].uom_id.id,
            'price_unit': self.company_data['product_order_no'].list_price,
            'order_id': sale_order.id,
            'tax_id': False,
        })

        # Confirm the SO
        sale_order.action_confirm()

        sol_prod_deliver.write({'qty_delivered': 5.0})

        # Context
        self.context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        # Let's do an invoice with invoiceable lines
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()

        invoice = sale_order.invoice_ids[0]

        self.assertEqual(invoice.line_ids[0].display_type, 'line_section')

    def test_qty_invoiced(self):
        """Verify uom rounding is correctly considered during qty_invoiced compute"""
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
        })

        SaleOrderLine = self.env['sale.order.line'].with_context(tracking_disable=True)
        sol_prod_deliver = SaleOrderLine.create({
            'name': self.company_data['product_order_no'].name,
            'product_id': self.company_data['product_order_no'].id,
            'product_uom_qty': 5,
            'product_uom': self.company_data['product_order_no'].uom_id.id,
            'price_unit': self.company_data['product_order_no'].list_price,
            'order_id': sale_order.id,
            'tax_id': False,
        })

        # Confirm the SO
        sale_order.action_confirm()

        sol_prod_deliver.write({'qty_delivered': 5.0})
        # Context
        self.context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        # Let's do an invoice with invoiceable lines
        invoicing_wizard = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        invoicing_wizard.create_invoices()

        self.assertEqual(sol_prod_deliver.qty_invoiced, 5.0)
        # We would have to change the digits of the field to
        # test a greater decimal precision.
        quantity = 5.13
        move_form = Form(sale_order.invoice_ids)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = quantity
        move_form.save()

        # Default uom rounding to 0.01
        qty_invoiced_field = sol_prod_deliver._fields.get('qty_invoiced')
        sol_prod_deliver.env.add_to_compute(qty_invoiced_field, sol_prod_deliver)
        self.assertEqual(sol_prod_deliver.qty_invoiced, quantity)

        # Rounding to 0.1, should be rounded with UP (ceil) rounding_method
        # Not floor or half up rounding.
        sol_prod_deliver.product_uom.rounding *= 10
        sol_prod_deliver.product_uom.flush(['rounding'])
        expected_qty = 5.2
        qty_invoiced_field = sol_prod_deliver._fields.get('qty_invoiced')
        sol_prod_deliver.env.add_to_compute(qty_invoiced_field, sol_prod_deliver)
        self.assertEqual(sol_prod_deliver.qty_invoiced, expected_qty)

    def test_invoice_analytic_account_default(self):
        """ Tests whether, when an analytic account rule is set and the so has no analytic account,
        the default analytic acount is correctly computed in the invoice.
        """
        analytic_account_default = self.env['account.analytic.account'].create({'name': 'default'})

        self.env['account.analytic.default'].create({
            'analytic_id': analytic_account_default.id,
            'product_id': self.product_a.id,
        })

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a

        with so_form.order_line.new() as sol:
            sol.product_id = self.product_a
            sol.product_uom_qty = 1

        so = so_form.save()
        so.action_confirm()
        so._force_lines_to_invoice_policy_order()

        so_context = {
            'active_model': 'sale.order',
            'active_ids': [so.id],
            'active_id': so.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        down_payment = self.env['sale.advance.payment.inv'].with_context(so_context).create({})
        down_payment.create_invoices()

        aml = self.env['account.move.line'].search([('move_id', 'in', so.invoice_ids.ids)])[0]
        self.assertRecordValues(aml, [{'analytic_account_id': analytic_account_default.id}])

    def test_invoice_analytic_account_so_not_default(self):
        """ Tests whether, when an analytic account rule is set and the so has an analytic account,
        the default analytic acount doesn't replace the one from the so in the invoice.
        """
        analytic_account_default = self.env['account.analytic.account'].create({'name': 'default'})
        analytic_account_so = self.env['account.analytic.account'].create({'name': 'so'})

        self.env['account.analytic.default'].create({
            'analytic_id': analytic_account_default.id,
            'product_id': self.product_a.id,
        })

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        so_form.analytic_account_id = analytic_account_so

        with so_form.order_line.new() as sol:
            sol.product_id = self.product_a
            sol.product_uom_qty = 1

        so = so_form.save()
        so.action_confirm()
        so._force_lines_to_invoice_policy_order()

        so_context = {
            'active_model': 'sale.order',
            'active_ids': [so.id],
            'active_id': so.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        down_payment = self.env['sale.advance.payment.inv'].with_context(so_context).create({})
        down_payment.create_invoices()

        aml = self.env['account.move.line'].search([('move_id', 'in', so.invoice_ids.ids)])[0]
        self.assertRecordValues(aml, [{'analytic_account_id': analytic_account_so.id}])

    def test_invoice_analytic_tag_so_not_default(self):
        """
        Tests whether, when an analytic tag rule is set and
        the so has an analytic tag different from default,
        the default analytic tag doesn't get overriden in invoice.
        """
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_tags')
        analytic_account_default = self.env['account.analytic.account'].create({'name': 'default'})
        analytic_tag_default = self.env['account.analytic.tag'].create({'name': 'default'})
        analytic_tag_super = self.env['account.analytic.tag'].create({'name': 'Super Tag'})

        self.env['account.analytic.default'].create({
            'analytic_id': analytic_account_default.id,
            'analytic_tag_ids': [(6, 0, analytic_tag_default.ids)],
            'product_id': self.product_a.id,
        })

        so = self.env['sale.order'].create({'partner_id': self.partner_a.id})
        self.env['sale.order.line'].create({
            'order_id': so.id,
            'name': "test",
            'product_id': self.product_a.id
        })
        so.order_line.analytic_tag_ids = [(6, 0, analytic_tag_super.ids)]
        so.action_confirm()
        so.order_line.qty_delivered = 1
        aml = so._create_invoices().invoice_line_ids
        self.assertRecordValues(aml, [{'analytic_tag_ids': analytic_tag_super.ids}])

    def test_invoice_analytic_tag_set_manually(self):
        """
        Tests whether, when there is no analytic tag rule set,
        the manually set analytic tag is passed from the so to the invoice.
        """
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_tags')
        analytic_tag_super = self.env['account.analytic.tag'].create({'name': 'Super Tag'})

        so = self.env['sale.order'].create({'partner_id': self.partner_a.id})
        self.env['sale.order.line'].create({
            'order_id': so.id,
            'name': "test",
            'product_id': self.product_a.id
        })
        so.order_line.analytic_tag_ids = [(6, 0, analytic_tag_super.ids)]
        so.action_confirm()
        so.order_line.qty_delivered = 1
        aml = so._create_invoices().invoice_line_ids
        self.assertRecordValues(aml, [{'analytic_tag_ids': analytic_tag_super.ids}])

    def test_invoice_analytic_tag_default_account_id(self):
        """
        Test whether, when an analytic tag rule with the condition `account_id` set,
        the default tag is correctly set during the conversion from so to invoice
        """
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_tags')
        analytic_account_default = self.env['account.analytic.account'].create({'name': 'default'})
        analytic_tag_default = self.env['account.analytic.tag'].create({'name': 'Super Tag'})

        self.env['account.analytic.default'].create({
            'analytic_id': analytic_account_default.id,
            'analytic_tag_ids': [(6, 0, analytic_tag_default.ids)],
            'product_id': self.product_a.id,
            'account_id': self.company_data['default_account_revenue'].id,
        })

        so = self.env['sale.order'].create({'partner_id': self.partner_a.id})
        self.env['sale.order.line'].create({
            'order_id': so.id,
            'name': "test",
            'product_id': self.product_a.id
        })
        self.assertFalse(so.order_line.analytic_tag_ids, "There should be no tag set.")
        so.action_confirm()
        so.order_line.qty_delivered = 1
        aml = so._create_invoices().invoice_line_ids
        self.assertRecordValues(aml, [{'analytic_tag_ids': analytic_tag_default.ids}])

    def test_partial_invoicing_interaction_with_invoicing_switch_threshold(self):
        """ Let's say you partially invoice a SO, let's call the resuling invoice 'A'. Now if you change the
            'Invoicing Switch Threshold' such that the invoice date of 'A' is before the new threshold,
            the SO should still take invoice 'A' into account.
        """
        if not self.env['ir.module.module'].search([('name', '=', 'account_accountant'), ('state', '=', 'installed')]):
            self.skipTest("This test requires the installation of the account_account module")

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_delivery_no'].id,
                    'product_uom_qty': 20,
                }),
            ],
        })
        line = sale_order.order_line[0]

        sale_order.action_confirm()

        line.qty_delivered = 10

        invoice = sale_order._create_invoices()
        invoice.action_post()

        self.assertEqual(line.qty_invoiced, 10)

        self.env['res.config.settings'].create({
            'invoicing_switch_threshold': fields.Date.add(invoice.invoice_date, days=30),
        }).execute()

        invoice.invalidate_cache(fnames=['payment_state'])

        self.assertEqual(line.qty_invoiced, 10)
        line.qty_delivered = 15
        self.assertEqual(line.qty_invoiced, 10)
