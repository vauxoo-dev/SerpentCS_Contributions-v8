import openerp
from openerp import http
from openerp.http import request
from openerp import SUPERUSER_ID
from openerp.addons.website_sale.controllers.main import QueryURL
from openerp.addons.website_sale.controllers.main import website_sale


class WebsiteSale(website_sale):

    @http.route(['/shop',
                 '/shop/page/<int:page>',
                 '/shop/category/<model("product.public.category"):category>',
                 """/shop/category/<model("product.public.category"):category>
                 /page/<int:page>""",
                 '/shop/brands'],
                type='http',
                auth='public',
                website=True)
    def shop(self, page=0, category=None, brand=None, search='', **post):
        cr, context, pool = (request.cr,
                             request.context,
                             request.registry)
        if brand:
            request.context.setdefault('brand_id', int(brand))
        result = super(WebsiteSale, self).shop(page=page, category=category,
                                               brand=brand, search=search,
                                               **post)
        brand_obj = pool.get('product.brand')
        product_obj = pool.get('product.template')
        brand_ids = brand_obj.search(cr, SUPERUSER_ID, [], context=context)
        brands = brand_obj.browse(cr, SUPERUSER_ID, brand_ids, context=context)
        category_obj = pool['product.public.category']
        public_categs = []
        published_product_ids = product_obj.search(
            cr, SUPERUSER_ID, [('website_published', '=', True)])
        published_products = product_obj.browse(cr, SUPERUSER_ID,
                                                published_product_ids,
                                                context=context)
        for pp in published_products:
            for pc in pp.public_categ_ids:
                if pc.id not in public_categs:
                    public_categs.append(pc.id)
        categories = category_obj.browse(
            cr,
            SUPERUSER_ID,
            public_categs,
            context=context)
        result.qcontext['categories'] = categories
        result.qcontext['brand'] = brand
        result.qcontext['brands'] = brands
        return result

    # Method to get the brands.
    @http.route(
        ['/page/product_brands'],
        type='http',
        auth='public',
        website=True)
    def product_brands(self, **post):
        cr, context, pool = (request.cr,
                             request.context,
                             request.registry)
        b_obj = pool['product.brand']
        domain = []
        if post.get('search'):
            domain += [('name', 'ilike', post.get('search'))]
        brand_ids = b_obj.search(cr, SUPERUSER_ID, domain)
        brand_rec = b_obj.browse(cr, SUPERUSER_ID, brand_ids, context=context)

        keep = QueryURL('/page/product_brands', brand_id=[])
        values = {'brand_rec': brand_rec,
                  'keep': keep}
        if post.get('search'):
            values.update({'search': post.get('search')})
        return request.website.render(
            'website_product_brand.product_brands',
            values)

openerp.addons.website_sale.controllers.main.website_sale = WebsiteSale
