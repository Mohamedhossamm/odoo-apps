from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPosArabicSearch(TransactionCase):
    def test_search_files_are_in_the_pos(self):
        bundle = self.env["ir.qweb"]._get_asset_bundle("point_of_sale._assets_pos", js=True, css=False)
        urls = [asset.url for asset in bundle.javascripts]
        for name in ("normalize.js", "search_patches.js"):
            self.assertTrue(any(url.endswith(f"pos_arabic_search/static/src/app/{name}") for url in urls), name)
