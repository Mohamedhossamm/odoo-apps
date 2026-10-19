from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestX2manySearch(TransactionCase):
    def test_search_files_are_in_the_backend(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("web.assets_backend", js=True, css=False)
        urls = [asset.url for asset in bundle.javascripts]
        for name in ("normalize.js", "x2many_search_bar.js", "x2many_field_patch.js"):
            self.assertTrue(any(url.endswith(f"mh_x2many_search/static/src/js/{name}") for url in urls), name)
