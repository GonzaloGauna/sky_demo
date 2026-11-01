# License AGPL-3.0 or later. Odoo 19 values inventory directly on stock.move.
from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.addons.fix_change_multicompany.models import cross_company_subset


class ResCompany(models.Model):
    _inherit = "res.company"

    waiki_allow_cross_company_stock = fields.Boolean(string="Permitir logistica entre empresas seleccionadas", default=False)

    def write(self, vals):
        if "waiki_allow_cross_company_stock" in vals and not self.env.is_system():
            raise AccessError(_("Only administrators can change the cross-company stock policy."))
        return super().write(vals)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _check_company(self, fnames=None):
        enabled = cross_company_subset(self, fnames, "waiki_allow_cross_company_stock")
        return super(StockMove, self - enabled)._check_company(fnames)


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _check_company(self, fnames=None):
        enabled = cross_company_subset(self, fnames, "waiki_allow_cross_company_stock")
        return super(StockMoveLine, self - enabled)._check_company(fnames)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    waiki_stock_company_ids = fields.Many2many('res.company', compute='_compute_waiki_stock_companies')
    warehouse_id = fields.Many2one(domain="[('company_id', 'in', waiki_stock_company_ids)]")

    @api.depends('company_id', 'company_id.waiki_allow_cross_company_stock')
    @api.depends_context('allowed_company_ids')
    def _compute_waiki_stock_companies(self):
        for order in self:
            company = order.company_id._origin or order.company_id
            order.waiki_stock_company_ids = self.env.companies if company.waiki_allow_cross_company_stock else company

    def _check_company(self, fnames=None):
        enabled = cross_company_subset(self, fnames, "waiki_allow_cross_company_stock")
        return super(SaleOrder, self - enabled)._check_company(fnames)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    waiki_stock_company_ids = fields.Many2many('res.company', compute='_compute_waiki_stock_companies')
    picking_type_id = fields.Many2one(check_company=True, domain="[('code', '=', 'incoming'), '|', ('company_id', '=', False), ('company_id', 'in', waiki_stock_company_ids)]")

    @api.depends('company_id', 'company_id.waiki_allow_cross_company_stock')
    @api.depends_context('allowed_company_ids')
    def _compute_waiki_stock_companies(self):
        for order in self:
            company = order.company_id._origin or order.company_id
            order.waiki_stock_company_ids = self.env.companies if company.waiki_allow_cross_company_stock else company

    def _check_company(self, fnames=None):
        enabled = cross_company_subset(self, fnames, "waiki_allow_cross_company_stock")
        return super(PurchaseOrder, self - enabled)._check_company(fnames)

