from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestX2manySearch(TransactionCase):
    def test_search_files_are_in_the_backend(self):
        paths = [path for path, *_ in self.env["ir.asset"]._get_asset_paths("web.assets_backend", js=True)]
        for name in ("normalize.js", "x2many_search_bar.js", "x2many_field_patch.js"):
            self.assertTrue(any(p.endswith(f"mh_x2many_search/static/src/js/{name}") for p in paths), name)
