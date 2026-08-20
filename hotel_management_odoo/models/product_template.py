# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _description = "Product Template"

    _ROOM_CAPACITY_BY_TYPE = {
        "single": 1,
        "double": 2,
        "dormitory": 4,
    }

    @tools.ormcache()
    def _get_default_uom_id(self):
        """Method for getting the default uom id"""
        return self.env.ref('uom.product_uom_unit')

    is_room = fields.Boolean(string="Room", help="is room")
    status = fields.Selection([("available", "Available"),
                               ("reserved", "Reserved"),
                               ("occupied", "Occupied")],
                              default="available", string="Status",
                              help="Status of The Room",
                              tracking=True)
    is_room_avail = fields.Boolean(default=True, string="Available",
                                   help="Check if the room is available")
    list_price = fields.Float(string='Rent', digits='Product Price',
                              help="The rent of the room.")
    room_amenities_ids = fields.Many2many("hotel.amenity",
                                          string="Room Amenities",
                                          help="List of room amenities.")
    floor_id = fields.Many2one('hotel.floor', string='Floor',
                               help="Automatically selects the Floor",
                               tracking=True)
    user_id = fields.Many2one('res.users', string="User",
                              related='floor_id.user_id',
                              help="Automatically selects the manager",
                              tracking=True)
    room_type = fields.Selection([('single', 'Single'),
                                  ('double', 'Double'),
                                  ('dormitory', 'Dormitory')],
                                 required=True, string="Room Type",
                                 help="Automatically selects the Room Type",
                                 tracking=True,
                                 default="single")
    num_person = fields.Integer(string='Number Of Persons',
                                required=True,
                                help="Automatically chooses the No. of Persons",
                                tracking=True)

    @api.model
    def _normalize_room_create_vals(self, vals):
        """Apply room defaults when records are created outside the form."""
        vals = dict(vals)
        is_room = vals.get('is_room', self.env.context.get('default_is_room'))
        if not is_room:
            return vals
        vals['is_room'] = True
        vals['type'] = 'consu'
        vals['is_storable'] = False
        vals.setdefault('status', 'available')
        vals.setdefault('is_room_avail', vals['status'] == 'available')
        room_type = vals.get('room_type') or 'single'
        vals.setdefault('num_person', self._ROOM_CAPACITY_BY_TYPE.get(room_type, 1))
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        """Keep duplicated/imported room products visible in reservations."""
        vals_list = [
            self._normalize_room_create_vals(vals)
            for vals in vals_list
        ]
        return super().create(vals_list)

    def write(self, vals):
        """Mirror onchange room behavior for imports, mass edits and RPC writes."""
        vals = dict(vals)
        if vals.get('is_room'):
            vals['type'] = 'consu'
            vals['is_storable'] = False
            vals.setdefault('status', 'available')
            vals.setdefault('is_room_avail', vals['status'] == 'available')
        if vals.get('room_type') and 'num_person' not in vals:
            vals['num_person'] = self._ROOM_CAPACITY_BY_TYPE.get(vals['room_type'], 1)
        result = super().write(vals)
        if (
            not self.env.context.get('skip_room_availability_sync')
            and 'status' in vals
            and 'is_room_avail' not in vals
        ):
            self.filtered('is_room').with_context(
                skip_room_availability_sync=True
            ).write({'is_room_avail': vals['status'] == 'available'})
        return result

    def copy(self, default=None):
        """Duplicated rooms must start available and selectable."""
        default = dict(default or {})
        if self.is_room:
            default.update({
                'is_room': True,
                'type': 'consu',
                'is_storable': False,
                'status': 'available',
                'is_room_avail': True,
            })
        return super().copy(default)

    def action_normalize_hotel_rooms(self):
        """Repair selected products so they can be used as hotel rooms."""
        for room in self:
            vals = {
                'is_room': True,
                'type': 'consu',
                'is_storable': False,
            }
            if room.status:
                vals['is_room_avail'] = room.status == 'available'
            else:
                vals.update({
                    'status': 'available',
                    'is_room_avail': True,
                })
            if not room.num_person:
                vals['num_person'] = self._ROOM_CAPACITY_BY_TYPE.get(
                    room.room_type or 'single', 1)
            room.write(vals)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('Selected rooms were normalized.'),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    @api.constrains("num_person")
    def _check_capacity(self):
        """Check capacity function"""
        for room in self:
            if room.num_person <= 0:
                raise ValidationError(_("Room capacity must be more than 0"))

    @api.onchange("room_type")
    def _onchange_room_type(self):
        """Based on selected room type, number of person will be updated.
        ----------------------------------------
        @param self: object pointer"""
        if self.room_type == "single":
            self.num_person = 1
        elif self.room_type == "double":
            self.num_person = 2
        else:
            self.num_person = 4

    @api.onchange('is_room')
    def _onchange_is_room(self):
        """Set product type to consumable if it is a room"""
        if self.is_room:
            self.type = 'consu'
            self.is_storable = False

    @api.constrains('is_room', 'is_storable')
    def _check_room_type(self):
        """Room products cannot be storable"""
        for record in self:
            if record.is_room and record.is_storable:
                raise ValidationError(_("Room products cannot be storable. Please disable 'Track Inventory'."))

