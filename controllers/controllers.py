# -*- coding: utf-8 -*-
# from odoo import http


# class IwAccounting(http.Controller):
#     @http.route('/iw_accounting/iw_accounting/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/iw_accounting/iw_accounting/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('iw_accounting.listing', {
#             'root': '/iw_accounting/iw_accounting',
#             'objects': http.request.env['iw_accounting.iw_accounting'].search([]),
#         })

#     @http.route('/iw_accounting/iw_accounting/objects/<model("iw_accounting.iw_accounting"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('iw_accounting.object', {
#             'object': obj
#         })
