/** @odoo-module */

import { toRaw, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ListRenderer } from "@web/views/list/list_renderer";
import {
    X2ManySearchBar,
    recordMatches,
    searchableColumns,
} from "@mh_x2many_search/js/x2many_search_bar";

// The search of each x2many list, read by its ListRenderer to hide the rows that do not match.
const searchByList = new WeakMap();

// Odoo 16 patches take a name and reach the original through this._super.
patch(X2ManyField.prototype, "mh_x2many_search", {
    setup() {
        this._super(...arguments);
        this.x2mSearch = useState({ facets: [] });
        const archInfo = (this.viewMode && this.activeField.views?.[this.viewMode]) || {};
        this.x2mSearchColumns =
            this.viewMode === "list" ? searchableColumns(archInfo, this.list.fields) : [];
        // The page size to come back to once the search is cleared.
        this.x2mSearchPageLimit = null;
    },

    // Used through t-component: subclasses (invoice lines, ...) copied X2ManyField.components before this patch.
    get x2mSearchBar() {
        return X2ManySearchBar;
    },

    get showX2mSearch() {
        return (
            this.x2mSearchColumns.length > 0 &&
            !this.activeField.options?.no_search &&
            (this.list.count > 0 || this.x2mSearch.facets.length > 0)
        );
    },

    get x2mSearchMatchCount() {
        const facets = this.x2mSearch.facets;
        return this.list.records.filter((r) => recordMatches(r, facets, this.x2mSearchColumns)).length;
    },

    async onX2mSearchChange(facets) {
        const list = this.list;
        if (list.editedRecord && !(await list.unselectRecord(true))) {
            return;
        }
        this.x2mSearch.facets = facets;
        // The search covers every line, not only the current page.
        if (facets.length && list.count > list.limit) {
            this.x2mSearchPageLimit = list.limit;
            await list.load({ limit: list.count, offset: 0 });
        } else if (!facets.length && this.x2mSearchPageLimit) {
            const limit = this.x2mSearchPageLimit;
            this.x2mSearchPageLimit = null;
            await list.load({ limit, offset: 0 });
        }
        this.render();
    },

    get rendererProps() {
        const facets = this.x2mSearch.facets;
        searchByList.set(toRaw(this.list), facets.length ? { facets, columns: this.x2mSearchColumns } : null);
        return this._super();
    },
});

patch(ListRenderer.prototype, "mh_x2many_search", {
    getRowClass(record) {
        const classNames = this._super(...arguments);
        const search = this.props.list && searchByList.get(toRaw(this.props.list));
        // A line being added or edited stays visible even if it does not match yet.
        if (
            search &&
            !record.isNew &&
            !record.isInEdition &&
            !recordMatches(record, search.facets, search.columns)
        ) {
            return `${classNames} d-none`;
        }
        return classNames;
    },
});
