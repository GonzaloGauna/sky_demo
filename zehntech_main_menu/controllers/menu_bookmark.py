# from odoo import http
# from odoo.http import request, route


# class MenuBookmark(http.Controller):

#     @route('/web/menu_bookmark/data', methods=['POST'], type='jsonrpc', auth='user')
#     def menu_bookmark_data(self, **kwargs):
#         return request.env['menu.bookmark'].search_read([('user_id', '=', request.session.uid)], [])

#     @route('/web/menu_bookmark/add', methods=['POST'], type='jsonrpc', auth='user')
#     def menu_bookmark_add(self, **kwargs):
#         new_bookmark = {
#             'name': kwargs.get('name'),
#             'url': kwargs.get('url'),
#             'user_id': request.session.uid,
#         }
#         return request.env['menu.bookmark'].create(new_bookmark).id


from odoo import http
from odoo.http import request, route

class MenuBookmark(http.Controller):

    @route('/web/menu_bookmark/data', methods=['POST'], type='jsonrpc', auth='user')
    def menu_bookmark_data(self, **kwargs):
        return request.env['menu.bookmark'].search_read([('user_id', '=', request.session.uid)], [])

    @route('/web/menu_bookmark/add', methods=['POST'], type='jsonrpc', auth='user')
    def menu_bookmark_add(self, **kwargs):
        name = kwargs.get('name')
        url = kwargs.get('url')
        user_id = request.session.uid

        # Check for existing bookmark for this user and url
        existing = request.env['menu.bookmark'].sudo().search([
            ('user_id', '=', user_id),
            ('url', '=', url)
        ], limit=1)
        if existing:
            return {'error': f'"{name}" is already bookmarked.'}

        new_bookmark = {
            'name': name,
            'url': url,
            'user_id': user_id,
        }
        bookmark = request.env['menu.bookmark'].sudo().create(new_bookmark)
        return {'success': True, 'id': bookmark.id}