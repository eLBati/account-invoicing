from odoo.addons.account.tests.account_test_users import AccountTestUsers


class TestInvoiceComputation(AccountTestUsers):

    def setUp(self):
        super(TestInvoiceComputation, self).setUp()
        self.invoice_model = self.env['account.invoice']
        self.partner3 = self.env.ref('base.res_partner_3')
        self.sales_journal = self.env['account.journal'].search(
            [('type', '=', 'sale')])[0]
        account_user_type = self.env.ref(
            'account.data_account_type_receivable')
        self.a_recv = self.account_model.sudo(self.account_manager.id).create(
            dict(
                code="cust_acc",
                name="customer account",
                user_type_id=account_user_type.id,
                reconcile=True,
            ))
        self.user_demo = self.env.ref('base.user_demo')
        self.a_sale = self.env['account.account'].search([
            (
                'user_type_id', '=',
                self.env.ref('account.data_account_type_revenue').id)
        ], limit=1)
        self.product_product_10 = self.env.ref('product.product_product_10')
        self.product_order_01 = self.env.ref('product.product_order_01')
        self.product_uom_unit = self.env.ref('uom.product_uom_unit')
        self.tax_22_inc = self.env["account.tax"].create({
            "name": "22% INC",
            "description": "22INC",
            "amount": 22,
            "type_tax_use": "sale",
            "price_include": True,
        })

    def test_computation(self):
        invoice = self.invoice_model.create({
            'partner_id': self.partner3.id,
            'journal_id': self.sales_journal.id,
            'account_id': self.a_recv.id,
            'user_id': self.user_demo.id,
            'type': 'out_invoice',
            'invoice_line_ids': [
                (0, 0, {
                    'account_id': self.a_sale.id,
                    'product_id': self.product_product_10.id,
                    'name': 'product_product_10',
                    'quantity': 10,
                    'uom_id': self.product_uom_unit.id,
                    'price_unit': 11,
                    'invoice_line_tax_ids': [(6, 0, {
                        self.tax_22_inc.id})]
                }),
                (0, 0, {
                    'account_id': self.a_sale.id,
                    'product_id': self.product_product_10.id,
                    'name': 'product_product_10',
                    'quantity': 10,
                    'uom_id': self.product_uom_unit.id,
                    'price_unit': 11,
                    'invoice_line_tax_ids': [(6, 0, {
                        self.tax_22_inc.id})]
                }),
                (0, 0, {
                    'account_id': self.a_sale.id,
                    'product_id': self.product_product_10.id,
                    'name': 'product_product_10',
                    'quantity': 10,
                    'uom_id': self.product_uom_unit.id,
                    'price_unit': 11,
                    'invoice_line_tax_ids': [(6, 0, {
                        self.tax_22_inc.id})]
                }),
                (0, 0, {
                    'account_id': self.a_sale.id,
                    'product_id': self.product_product_10.id,
                    'name': 'product_product_10',
                    'quantity': 10,
                    'uom_id': self.product_uom_unit.id,
                    'price_unit': 11,
                    'invoice_line_tax_ids': [(6, 0, {
                        self.tax_22_inc.id})]
                }),
                (0, 0, {
                    'account_id': self.a_sale.id,
                    'product_id': self.product_product_10.id,
                    'name': 'product_product_10',
                    'quantity': 10,
                    'uom_id': self.product_uom_unit.id,
                    'price_unit': 11,
                    'invoice_line_tax_ids': [(6, 0, {
                        self.tax_22_inc.id})]
                }),
                (0, 0, {
                    'account_id': self.a_sale.id,
                    'product_id': self.product_order_01.id,
                    'name': 'product_order_01',
                    'quantity': 1,
                    'uom_id': self.product_uom_unit.id,
                    'price_unit': 420,
                    'invoice_line_tax_ids': [(6, 0, {
                        self.tax_22_inc.id})]
                }),
                (0, 0, {
                    'account_id': self.a_sale.id,
                    'name': 'discount',
                    'quantity': 1,
                    'uom_id': self.product_uom_unit.id,
                    'price_unit': -242.5,
                    'invoice_line_tax_ids': [(6, 0, {
                        self.tax_22_inc.id})]
                }),
            ],
        })
        invoice.action_invoice_open()

        # TODO verificare round global e modificare o commentare takobi_saas_pos/models/pos_order
        #  completare i test per account.invoice.tax, totali fattura, journal entry
        #  aggiungere i test per i vari casi particolari, righe con aliquote diverse,
        #  righe con conti diversi, eventualmente con account_analytic_id e analytic_tag_ids,
        #  per grouping_applicable
