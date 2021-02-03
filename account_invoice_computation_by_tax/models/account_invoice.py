from odoo import models, api, fields, _
from odoo.tools import float_round


class Invoice(models.Model):
    _inherit = "account.invoice"

    def grouping_applicable(self):
        if self.type not in ["out_invoice", "out_refund"]:
            return False
        for line in self.invoice_line_ids:
            if len(line.invoice_line_tax_ids) != 1:
                return False
        if not self.invoice_line_ids._all_included_in_price():
            return False
        grouped_lines = self.invoice_line_ids._get_grouped_lines()
        if not self._check_groupable_lines(grouped_lines):
            return False
        return True

    @api.multi
    def get_taxes_values(self):
        tax_grouped = super(Invoice, self).get_taxes_values()
        if not self.grouping_applicable():
            return tax_grouped
        self._compute_lines_by_tax(tax_grouped)
        return tax_grouped

    @staticmethod
    def _check_groupable_lines(grouped_lines):
        for key in grouped_lines:
            lines = grouped_lines[key]
            if len(lines.mapped("account_id")) > 1:
                # can't recompute grouped lines with different accounts:
                # related move lines can't be grouped
                return False
        return True

    def _compute_lines_by_tax(self, tax_grouped):
        grouped_lines = self.invoice_line_ids._get_grouped_lines()
        for key in grouped_lines:
            # See account.tax.get_grouping_key
            tax = self.env["account.tax"].browse(int(key.split("-")[0]))
            lines = grouped_lines[key]
            untaxed_amount, tax_amount = lines._compute_grouped_totals(tax)
            tax_grouped[key]["amount"] = tax_amount
            tax_grouped[key]["base"] = untaxed_amount

    @api.multi
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount',
                 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type', 'date')
    def _compute_amount(self):
        super(Invoice, self)._compute_amount()
        for inv in self:
            if not inv.grouping_applicable():
                continue
            inv.amount_untaxed = sum(
                line.base for line in inv.tax_line_ids)
            amount_untaxed_signed = inv.amount_untaxed
            if (
                inv.currency_id and inv.company_id and
                inv.currency_id != inv.company_id.currency_id
            ):
                currency_id = inv.currency_id
                rate_date = inv._get_currency_rate_date() or fields.Date.today()
                amount_untaxed_signed = currency_id._convert(
                    inv.amount_untaxed, inv.company_id.currency_id, inv.company_id,
                    rate_date)
        sign = inv.type in ['in_refund', 'out_refund'] and -1 or 1
        inv.amount_untaxed_signed = amount_untaxed_signed * sign

    def invoice_line_move_line_get(self):
        res = super(Invoice, self).invoice_line_move_line_get()
        if not self.grouping_applicable():
            return res
        grouped_lines = self.invoice_line_ids._get_grouped_lines()
        new_res = []
        for key in grouped_lines:
            tax = self.env["account.tax"].browse(int(key.split("-")[0]))
            lines = grouped_lines[key]
            # taking the first: they must be all the same
            account_id = lines[0].account_id
            if not account_id:
                continue
            tax_ids = [(4, tax.id, None)]
            analytic_tag_ids = lines[0].analytic_tag_ids
            analytic_tag_ids = [
                (4, analytic_tag.id, None) for analytic_tag in analytic_tag_ids]
            untaxed_amount, tax_amount = lines._compute_grouped_totals(tax)
            move_line_dict = {
                'invl_id': lines[0].id,
                'type': 'src',
                'name': _("%s: untaxed amount") % tax.name,
                'price_unit': untaxed_amount,
                'quantity': 1,
                'price': untaxed_amount,
                'account_id': account_id.id,
                'product_id': None,
                'uom_id': None,
                'account_analytic_id': lines[0].account_analytic_id.id,
                'analytic_tag_ids': analytic_tag_ids,
                'tax_ids': tax_ids,
                'invoice_id': self.id,
            }
            new_res.append(move_line_dict)
        return new_res


class InvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def _all_included_in_price(self):
        if all(self.mapped("invoice_line_tax_ids.price_include")):
            return True
        return False

    def _get_grouped_lines(self):
        grouped_lines = {}
        for line in self:
            tax = line.invoice_line_tax_ids[0]
            key = tax.get_grouping_key({
                'tax_id': tax.id,
                'account_id': tax.account_id.id,
                'account_analytic_id': line.account_analytic_id.id,
                'analytic_tag_ids': line.analytic_tag_ids.ids or False,
            })
            if key not in grouped_lines:
                grouped_lines[key] = line
            else:
                grouped_lines[key] |= line
        return grouped_lines

    def _compute_grouped_totals(self, tax):
        total = 0
        for line in self:
            precision = line.company_id.currency_id.decimal_places
            total += line.price_unit * (1 - (line.discount or 0.0) / 100.0) * \
                     line.quantity
        untaxed_amount = float_round(
            total / (1 + (tax.amount / 100)), precision_digits=precision)
        tax_amount = total - untaxed_amount
        return untaxed_amount, tax_amount
