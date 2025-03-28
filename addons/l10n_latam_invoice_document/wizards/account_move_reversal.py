# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    l10n_latam_use_documents = fields.Boolean(compute='_compute_document_type')
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', 'Document Type', ondelete='cascade', domain="[('id', 'in', l10n_latam_available_document_type_ids)]", compute='_compute_document_type', readonly=False, inverse='_inverse_document_type')
    l10n_latam_available_document_type_ids = fields.Many2many('l10n_latam.document.type', compute='_compute_document_type')
    l10n_latam_document_number = fields.Char(string='Document Number')
    l10n_latam_manual_document_number = fields.Boolean(compute='_compute_l10n_latam_manual_document_number', string='Manual Number')

    def _inverse_document_type(self):
        self._clean_pipe()
        self.l10n_latam_document_number = '%s|%s' % (self.l10n_latam_document_type_id.id or '', self.l10n_latam_document_number or '')

    @api.depends('l10n_latam_document_type_id')
    def _compute_l10n_latam_manual_document_number(self):
        self.l10n_latam_manual_document_number = False
        for rec in self.filtered('move_ids'):
            move = rec.move_ids[0]
            if move.journal_id and move.journal_id.l10n_latam_use_documents:
                rec.l10n_latam_manual_document_number = move._is_manual_document_number()

    @api.model
    def _reverse_type_map(self, move_type):
        match = {
            'entry': 'entry',
            'out_invoice': 'out_refund',
            'in_invoice': 'in_refund',
            'in_refund': 'in_invoice',
            'out_receipt': 'in_receipt',
            'in_receipt': 'out_receipt'}
        return match.get(move_type)

    @api.depends('move_ids')
    def _compute_document_type(self):
        self.l10n_latam_available_document_type_ids = False
        self.l10n_latam_document_type_id = False
        self.l10n_latam_use_documents = False
        for record in self:
            if len(record.move_ids) > 1:
                move_ids_use_document = record.move_ids._origin.filtered(lambda move: move.l10n_latam_use_documents)
                if move_ids_use_document:
                    raise UserError(_('You can only reverse documents with legal invoicing documents from Latin America one at a time.\nProblematic documents: %s') % ", ".join(move_ids_use_document.mapped('name')))
            else:
                record.l10n_latam_use_documents = record.move_ids.journal_id.l10n_latam_use_documents

            if record.l10n_latam_use_documents:
                refund = record.env['account.move'].new({
                    'move_type': record._reverse_type_map(record.move_ids.move_type),
                    'journal_id': record.move_ids.journal_id.id,
                    'partner_id': record.move_ids.partner_id.id,
                    'company_id': record.move_ids.company_id.id,
                })
                record.l10n_latam_document_type_id = refund.l10n_latam_document_type_id
                record.l10n_latam_available_document_type_ids = refund.l10n_latam_available_document_type_ids

    def _prepare_default_reversal(self, move):
        """ Set the default document type and number in the new revsersal move taking into account the ones selected in
        the wizard """
        res = super()._prepare_default_reversal(move)
        # self.l10n_latam_document_number will have a ',' only if l10n_latam_document_type_id is changed and inverse methods is called
        if self.l10n_latam_document_number and '|' in self.l10n_latam_document_number:
            l10n_latam_document_type_id, l10n_latam_document_number = self.l10n_latam_document_number.split('|')
            res.update({
                'l10n_latam_document_type_id': int(l10n_latam_document_type_id) if l10n_latam_document_type_id else False,
                'l10n_latam_document_number': l10n_latam_document_number or False,
            })
        else:
            res.update({
                'l10n_latam_document_type_id': self.l10n_latam_document_type_id.id,
                'l10n_latam_document_number': self.l10n_latam_document_number,
            })
        return res

    def _clean_pipe(self):
        """ Clean pipe in case the user confirm but he gets a raise, the l10n_latam_document_number is stored now
        with the doc type id, we should remove to append new one or to format properly"""
        latam_document = self.l10n_latam_document_number or ''
        if '|' in latam_document:
            latam_document = latam_document[latam_document.index('|')+1:]
        self.l10n_latam_document_number = latam_document

    @api.onchange('l10n_latam_document_number', 'l10n_latam_document_type_id')
    def _onchange_l10n_latam_document_number(self):
        if self.l10n_latam_document_type_id:
            self._clean_pipe()
            l10n_latam_document_number = self.l10n_latam_document_type_id._format_document_number(
                self.l10n_latam_document_number)
            if self.l10n_latam_document_number != l10n_latam_document_number:
                self.l10n_latam_document_number = l10n_latam_document_number
