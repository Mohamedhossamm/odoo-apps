/** @odoo-module */

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { patch } from "@web/core/utils/patch";

const REFRESH_MS = 5000;

/** Cashier view: move paid orders from preparing to ready to collected. */
export class OrderStatusPanel extends Component {
    static template = "pos_order_status_board.OrderStatusPanel";
    static components = { Dialog };
    static props = { close: Function };

    setup() {
        this.pos = usePos();
        // The plain ORM service, not pos.data: pos.data treats call results as records to load
        // and drops a plain dictionary like the board data.
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ preparing: [], ready: [], boardUrl: false, loaded: false, busy: false });
        onMounted(() => {
            this.refresh();
            this.timer = setInterval(() => this.refresh(), REFRESH_MS);
        });
        onWillUnmount(() => clearInterval(this.timer));
    }

    async refresh() {
        let data;
        try {
            data = await this.orm.silent.call("pos.config", "get_order_status_board", [[this.pos.config.id]]);
        } catch {
            return; // offline: keep showing the last list instead of emptying it
        }
        Object.assign(this.state, {
            preparing: data.preparing,
            ready: data.ready,
            boardUrl: data.board_url,
            loaded: true,
        });
    }

    async setStatus(order, status) {
        this.state.busy = true;
        try {
            await this.orm.call("pos.order", "set_order_status", [[order.id], status]);
            await this.refresh();
        } catch {
            this.notification.add(_t("Could not update the order. Check the connection."), {
                type: "danger",
            });
        } finally {
            this.state.busy = false;
        }
    }

    openBoard() {
        window.open(this.state.boardUrl, "_blank");
    }
}

patch(Navbar.prototype, {
    openOrderStatusPanel() {
        this.dialog.add(OrderStatusPanel, {});
    },
});
