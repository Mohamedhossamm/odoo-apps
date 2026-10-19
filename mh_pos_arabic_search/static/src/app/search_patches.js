/** @odoo-module */

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { ResPartner } from "@point_of_sale/app/models/res_partner";
import { patch } from "@web/core/utils/patch";
import { normalizeArabic } from "@mh_pos_arabic_search/app/normalize";

// Odoo filters with `searchString.includes(searchWord)`: putting both in one spelling is enough.

patch(ProductTemplate.prototype, {
    get searchString() {
        return normalizeArabic(super.searchString);
    },
    get normalizedName() {
        return normalizeArabic(super.normalizedName);
    },
});

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

patch(PosStore.prototype, {
    getProductsBySearchWord(searchWord, products) {
        return super.getProductsBySearchWord(normalizeArabic(searchWord), products);
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
