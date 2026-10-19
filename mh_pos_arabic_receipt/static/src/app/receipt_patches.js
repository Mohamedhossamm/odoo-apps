/** @odoo-module */

import { Order, Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { amountToArabic } from "@mh_pos_arabic_receipt/app/tafqeet";

patch(Orderline.prototype, {
    getDisplayData() {
        const data = super.getDisplayData(...arguments);
        const arabicName = this.product.pos_arabic_name;
        // Skip it when the POS already shows the Arabic name, for an Arabic-speaking cashier.
        if (this.pos.config.ar_receipt_product_names && arabicName && arabicName !== data.productName) {
            data.arabicName = arabicName;
        }
        return data;
    },
});

patch(Order.prototype, {
    export_for_printing() {
        const data = super.export_for_printing(...arguments);
        const config = this.pos.config;

        // A POS in Arabic already prints the Arabic labels.
        data.arabicLabels = config.ar_receipt_labels && !session.user_context?.lang?.startsWith("ar");

        if (config.ar_receipt_amount_words) {
            const toPay = data.amount_total + (data.rounding_applied || 0);
            // Refunds are negative and are not written in words.
            data.arabicAmount = toPay > 0 ? amountToArabic(toPay, this.pos.currency?.name) : "";
        }

        const partner = this.get_partner();
        if (config.ar_receipt_customer && partner) {
            data.arabicCustomer = {
                name: partner.name,
                phone: partner.mobile || partner.phone || "",
            };
        }
        return data;
    },
});
