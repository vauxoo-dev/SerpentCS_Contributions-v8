import werkzeug
from openerp import http
from openerp.http import request
import openerp.addons.website_sale.controllers.main
from openerp import SUPERUSER_ID
from openerp.addons.website.models.website import slug
from openerp.addons.website_sale.controllers.main import table_compute, QueryURL  # noqa
PPG = 20
PPR = 4


class table_compute(object):  # flake8: noqa

    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey):
        res = True
        for axisy in range(sizey):
            for axisx in range(sizex):
                if posx + axisx >= PPR:
                    res = False
                    break
                row = self.table.setdefault(posy + axisy, {})
                if row.setdefault(posx + axisx) is not None:
                    res = False
                    break

            for axisx in range(PPR):
                self.table[posy + axisy].setdefault(axisx, None)

        return res

    def process(self, products):
        minpos = 0
        index = 0
        maxy = 0
        for prod in products:
            axisx = min(max(prod.website_size_x, 1), PPR)
            axisy = min(max(prod.website_size_y, 1), PPR)
            if index > PPG:
                axisx = axisy = 1
            pos = minpos
            while not self._check_place(pos % PPR, pos / PPR, axisx, axisy):
                pos += 1

            if index > PPG and pos / PPR > maxy:
                break
            if axisx == 1 and axisy == 1:
                minpos = pos / PPR
            for y2 in range(axisy):
                for x2 in range(axisx):
                    self.table[pos / PPR + y2][pos % PPR + x2] = False

            self.table[
                pos /
                PPR][
                pos %
                PPR] = {
                'product': prod,
                'x': axisx,
                'y': axisy,
                'class': ' '.join(
                    map(  # pylint: disable=W0141,W0110
                        lambda axisx: axisx.html_class or '',
                        prod.website_style_ids))}
            if index <= PPG:
                maxy = max(maxy, axisy + pos / PPR)
            index += 1

        rows = sorted(self.table.items())
        rows = map(lambda axisx: axisx[1], rows)  # pylint: disable=W0141,W0110
        for col in range(len(rows)):
            cols = sorted(rows[col].items())
            axisx += len(cols)
            rows[col] = [
                c for c in
                map(lambda axisx: axisx[1],  # pylint: disable=W0141,W0110
                    cols) if c]

        return rows


class QueryURL(object):   # flake8: noqa

    def __init__(self, path='', **args):
        self.path = path
        self.args = args

    def __call__(self, path=None, **kw):
        if not path:
            path = self.path
        for k, v in self.args.items():
            kw.setdefault(k, v)

        lst = []
        for k, v in kw.items():
            if v:
                if isinstance(v, list) or isinstance(v, set):
                    lst.append(werkzeug.url_encode([(k, i) for i in v]))
                else:
                    lst.append(werkzeug.url_encode([(k, v)]))

        if lst:
            path += '?' + '&'.join(lst)
        return path


class website_sale(openerp.addons.website_sale.controllers.main.website_sale):

    @http.route(['/shop', '/shop/page/<int:page>', '/shop/category/<model("product.public.category"):category>',  # noqa
                 '/shop/category/<model("product.public.category"):category>\
                 /page/<int:page>', '/shop/brands'], type='http', auth='public', website=True)  # noqa
    def shop(self, page=0, category=None, search='', brand=None, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry  # noqa
        values = {}
        domain = request.website.sale_product_domain()
        if search:
            domain += ['|', '|', '|',
                       ('name', 'ilike', search),
                       ('description', 'ilike', search),
                       ('description_sale', 'ilike', search),
                       ('product_variant_ids.default_code', 'ilike', search)]
        if category:
            domain += [('public_categ_ids', 'child_of', int(category))]
        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [
            map(int, v.split('-'))  # pylint: disable=W0141,W0110
            for v in attrib_list if v]
        attrib_set = set([v[1] for v in attrib_values])
        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domain += [('attribute_line_ids.value_ids', 'in', ids)]
                    attrib = value[0]
                    ids = [value[1]]

            if attrib:
                domain += [('attribute_line_ids.value_ids', 'in', ids)]
        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list)  # noqa
        if not context.get('pricelist'):
            pricelist = self.get_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = pool.get('product.pricelist').browse(cr, uid, context['pricelist'], context)  # noqa
        product_obj = pool.get('product.template')

        # Brand's product search
        if brand:
            values.update({'brand': brand})
            product_designer_obj = pool.get('product.brand')
            brand_ids = product_designer_obj.search(cr, SUPERUSER_ID, [('id', '=', int(brand))])  # noqa
            domain += [('product_brand_id', 'in', brand_ids)]
        url = '/shop'
        product_count = product_obj.search_count(cr, uid, domain, context=context)  # noqa
        if search:
            post['search'] = search
        if category:
            category = pool['product.public.category'].browse(cr, uid, int(category), context=context)  # noqa
            url = '/shop/category/%s' % slug(category)
        pager = request.website.pager(url=url, total=product_count, page=page, step=PPG, scope=7, url_args=post)  # noqa
        product_ids = product_obj.search(cr, uid, domain, limit=PPG, offset=pager['offset'], order='website_published desc, website_sequence desc', context=context)  # noqa
        products = product_obj.browse(cr, uid, product_ids, context=context)
        style_obj = pool['product.style']
        style_ids = style_obj.search(cr, uid, [], context=context)
        styles = style_obj.browse(cr, uid, style_ids, context=context)
        category_obj = pool['product.public.category']
        category_ids = category_obj.search(cr, uid, [], context=context)
        categories = category_obj.browse(
            cr,
            uid,
            category_ids,
            context=context)
        categs = filter(  # pylint: disable=W0141,W0110
            lambda x: not x.parent_id,
            categories)
        if category:
            selected_id = int(category)
            child_prod_ids = category_obj.search(cr, uid, [('parent_id', '=', selected_id)], context=context)  # noqa
            children_ids = category_obj.browse(cr, uid, child_prod_ids)
            values.update({'child_list': children_ids})
        attributes_obj = request.registry['product.attribute']
        attributes_ids = attributes_obj.search(cr, uid, [], context=context)
        attributes = attributes_obj.browse(cr, uid, attributes_ids,
                                           context=context)
        from_currency = pool.get('product.price.type')._get_field_currency(
            cr, uid, 'list_price', context)
        to_currency = pricelist.currency_id
        compute_currency = lambda price: pool['res.currency']._compute(
            cr, uid, from_currency, to_currency, price, context=context)
        brand_obj = pool.get('product.brand')
        brand_ids = brand_obj.search(cr, uid, [], context=context)
        brands = brand_obj.browse(cr, uid, brand_ids, context=context)
        values.update({'search': search,
                       'category': category,
                       'attrib_values': attrib_values,
                       'attrib_set': attrib_set,
                       'pager': pager,
                       'pricelist': pricelist,
                       'products': products,
                       'bins': table_compute().process(products),
                       'rows': PPR,
                       'styles': styles,
                       'categories': categs,
                       'attributes': attributes,
                       'compute_currency': compute_currency,
                       'keep': keep,
                       'style_in_product': lambda style, product: style.id in [s.id for s in product.website_style_ids],  # noqa
                       'attrib_encode': lambda attribs: werkzeug.url_encode([('attrib', i) for i in attribs]),  # noqa
                       'brands': brands,
                       })
        return request.website.render('website_sale.products', values)

    # Method to get the brands.
    @http.route(['/page/product_brands'], type='http', auth='public',
                website=True)
    def product_brands(self, **post):
        cr, context, pool = (request.cr, request.context, request.registry)
        brand_values = []
        brand_obj = pool['product.brand']
        domain = []
        if post.get('search'):
            domain += [('name', 'ilike', post.get('search'))]
        brand_ids = brand_obj.search(cr, SUPERUSER_ID, domain)
        for brand_rec in brand_obj.browse(cr, SUPERUSER_ID, brand_ids, context=context):  # noqa
            brand_values.append(brand_rec)

        keep = QueryURL('/page/product_brands', brand_id=[])
        values = {'brand_rec': brand_values, 'keep': keep}
        if post.get('search'):
            values.update({'search': post.get('search')})
        return request.website.render('website_product_brand.product_brands', values)  # noqa

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
