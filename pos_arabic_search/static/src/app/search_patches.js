/** @odoo-module */

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ResPartner } from "@point_of_sale/app/models/res_partner";
import { patch } from "@web/core/utils/patch";
import { normalizeArabic } from "@pos_arabic_search/app/normalize";

// Odoo filters with `searchString.includes(searchWord)`: putting both in one spelling is enough.

patch(ProductProduct.prototype, {
    get searchString() {
        return normalizeArabic(super.searchString);
    },
});

patch(ResPartner.prototype, {
    get searchString() {
        return normalizeArabic(super.searchString);
    },
});

patch(ProductScreen.prototype, {
    get searchWord() {
        return normalizeArabic(super.searchWord);
    },
});

patch(PartnerList.prototype, {
    getPartners() {
        const query = this.state.query;
        const normalized = normalizeArabic(query);
        if (normalized === query) {
            return super.getPartners(...arguments);
        }
        // Search with the normalized query without writing it into the search box the cashier types in.
        const view = Object.create(this, { state: { value: { ...this.state, query: normalized } } });
        return super.getPartners.call(view, ...arguments);
    },
});
