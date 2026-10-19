/** @odoo-module */

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { amountToArabic } from "@pos_arabic_receipt/app/tafqeet";

patch(PosOrderline.prototype, {
    get arabicReceiptName() {
        const arabicName = this.product_id?.pos_arabic_name;
        // Skip it when the line already shows the Arabic name, for an Arabic-speaking cashier.
        if (this.config.ar_receipt_product_names && arabicName && arabicName !== this.full_product_name) {
            return arabicName;
        }
        return "";
    },
});

patch(OrderReceipt.prototype, {
    get arabicLabels() {
        // A POS in Arabic already prints the Arabic labels.
        return this.order.config.ar_receipt_labels && !user.lang?.startsWith("ar");
    },

    get arabicAmount() {
        const order = this.order;
        if (!order.config.ar_receipt_amount_words) {
            return "";
        }
        const toPay = order.appliedRounding ? order.roundedPriceIncl : order.priceIncl;
        // Refunds are negative and are not written in words.
        return toPay > 0 ? amountToArabic(toPay, order.currency?.name) : "";
    },
});
