/** @odoo-module */

import { PosDB } from "@point_of_sale/app/store/db";
import { patch } from "@web/core/utils/patch";
import { normalizeArabic } from "@mh_pos_arabic_search/app/normalize";

// The POS searches a text built from every product and customer: putting it and the query in one spelling is enough.

patch(PosDB.prototype, {
    _product_search_string(product) {
        return normalizeArabic(super._product_search_string(...arguments));
    },
    _partner_search_string(partner) {
        return normalizeArabic(super._partner_search_string(...arguments));
    },
    search_product_in_category(category_id, query) {
        return super.search_product_in_category(category_id, normalizeArabic(query));
    },
    search_partner(query) {
        return super.search_partner(normalizeArabic(query));
    },
});
