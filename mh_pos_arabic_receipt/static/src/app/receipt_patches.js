/** @odoo-module */

import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { amountToArabic } from "@mh_pos_arabic_receipt/app/tafqeet";

// Orderline validates the shape of its line in debug mode and rejects unknown keys.
Orderline.props.line.shape.arabicName = { type: String, optional: true };

const ARABIC_LETTERS = /[\u0600-\u06FF]/;

const ARABIC_LABELS = {
    label_total: "الإجمالي",
    label_change: "الباقي",
    label_discounts: "الخصومات",
    label_rounding: "التقريب",
};

patch(PosOrderline.prototype, {
    getDisplayData() {
        const data = super.getDisplayData(...arguments);
        const arabicName = this.product_id?.pos_arabic_name;
        // Skip it when the POS already shows the Arabic name, for an Arabic-speaking cashier.
        if (this.config.ar_receipt_product_names && arabicName && arabicName !== data.productName) {
            data.arabicName = arabicName;
        }
        return data;
    },
});

patch(PosOrder.prototype, {
    export_for_printing() {
        const data = super.export_for_printing(...arguments);
        const config = this.config;

        if (config.ar_receipt_labels) {
            for (const [key, arabic] of Object.entries(ARABIC_LABELS)) {
                // A POS in Arabic already prints the Arabic label.
                if (data[key] && !ARABIC_LETTERS.test(data[key])) {
                    data[key] = `${data[key]} / ${arabic}`;
                }
            }
        }

        if (config.ar_receipt_amount_words) {
            const totals = data.taxTotals;
            const toPay = totals ? totals.order_sign * (totals.order_total + (totals.order_rounding || 0)) : data.amount_total;
            // Refunds are negative and are not written in words.
            data.arabicAmount = toPay > 0 ? amountToArabic(toPay, this.currency?.name) : "";
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
