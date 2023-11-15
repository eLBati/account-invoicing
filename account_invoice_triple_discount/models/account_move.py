# Copyright 2017 Tecnativa - David Vidal
# Copyright 2017 Tecnativa - Pedro M. Baeza
# Copyright 2023 Simone Rubino - Aion Tech
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMove(models.Model):

    _inherit = "account.move"

    def _recompute_tax_lines(self, **kwargs):
        """
        As the taxes are recalculated based on a single discount, we need to
        simulate a multiple discount by changing the unit price. Values are
        restored after the original process is done
        """
        old_values_by_line_id = {}
        digits = self.invoice_line_ids._fields["price_unit"]._digits
        self.invoice_line_ids._fields["price_unit"]._digits = (16, 16)
        for line in self.invoice_line_ids:
            aggregated_discount = line._compute_aggregated_discount(line.discount)
            old_values_by_line_id[line.id] = {
                "price_unit": line.price_unit,
                "discount": line.discount,
            }
            price_unit = line.price_unit * (1 - aggregated_discount / 100)
            line.update({"price_unit": price_unit, "discount": 0})
        self.invoice_line_ids._fields["price_unit"]._digits = digits
        res = super(AccountMove, self)._recompute_tax_lines(**kwargs)
        for line in self.invoice_line_ids:
            if line.id not in old_values_by_line_id:
                continue
            line.with_context(
                restoring_triple_discount=True,
            ).update(old_values_by_line_id[line.id])
        return res

    def _has_discount(self):
        self.ensure_one()
        return any(
            [
                line._compute_aggregated_discount(line.discount) > 0
                for line in self.invoice_line_ids
            ]
        )

    @api.model
    def _field_will_change(self, record, vals, field_name):
        result = super()._field_will_change(record, vals, field_name)
        is_discount_field = (
            record._name == self.line_ids._name and field_name == "discount"
        )
        if (
            not result
            and self.env.context.get("restoring_triple_discount")
            and is_discount_field
        ):
            # Discount value in the cache has many digits (e.g. 100.00000000000009),
            # but we have just restored the original digits (e.g. 2) in the field
            # and want to write the correct value (e.g. 100.00).
            # The method in super compares:
            # - the cache value rounded with the field's digits: 100.00
            # - the value we want to write: 100.00
            # and concludes that the value won't change,
            # thus leaving the cache value (100.00000000000009)
            # instead of updating the cache with the value we actually want (100.00)
            result = True
        return result
