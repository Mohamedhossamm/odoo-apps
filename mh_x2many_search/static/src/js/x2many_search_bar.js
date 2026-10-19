/** @odoo-module */

import { Component, useRef, useState } from "@odoo/owl";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { formatFloat } from "@web/core/utils/numbers";
import { unaccent } from "@web/core/utils/strings";
import { normalizeArabic } from "@mh_x2many_search/js/normalize";

const UNSEARCHABLE_TYPES = ["binary", "boolean", "image", "properties", "json"];

/** The form both the typed text and the cell values are compared in. */
export function normalizeSearchText(text) {
    return normalizeArabic(unaccent(String(text ?? ""), false));
}

/** What a record shows for a field, as plain text. */
function fieldText(record, column) {
    const value = record.data[column.name];
    if (value === false || value === null || value === undefined) {
        return "";
    }
    switch (column.fieldType) {
        case "many2one":
            return Array.isArray(value) ? value[1] || "" : value.display_name || "";
        case "many2many":
        case "one2many":
            return (value.records || []).map((r) => r.data.display_name || "").join(" ");
        case "selection": {
            const option = (record.fields[column.name].selection || []).find(([key]) => key === value);
            return option ? option[1] : String(value);
        }
        case "date":
            return formatDate(value);
        case "datetime":
            return formatDateTime(value);
        case "integer":
        case "float":
        case "monetary": {
            // Both the stored number (2) and what the list shows (2.00, 1,250.00) are found.
            const digits = record.fields[column.name].digits;
            return `${value} ${formatFloat(value, { digits: digits || [16, 2] })}`;
        }
        default:
            return String(value);
    }
}

/**
 * Searchable columns of a list arch: the visible fields a user can read.
 * Columns hidden with a condition stay searchable, the condition depends on the parent record.
 */
export function searchableColumns(archInfo, fields) {
    const seen = new Set();
    return (archInfo.columns || [])
        .filter((column) => column.type === "field" && fields[column.name])
        .map((column) => ({
            name: column.name,
            label: column.label || fields[column.name].string,
            fieldType: fields[column.name].type,
            isHandle: column.isHandle,
            column_invisible: column.column_invisible,
        }))
        .filter((column) => {
            const searchable =
                !column.isHandle &&
                !UNSEARCHABLE_TYPES.includes(column.fieldType) &&
                !["True", "1", "true"].includes(column.column_invisible) &&
                !seen.has(column.name);
            seen.add(column.name);
            return searchable;
        });
}

/** Whether a record passes every facet: each facet needs one of its values in its columns (or any column). */
export function recordMatches(record, facets, columns) {
    return facets.every((facet) => {
        const facetColumns = facet.names ? columns.filter((c) => facet.names.includes(c.name)) : columns;
        const text = normalizeSearchText(facetColumns.map((c) => fieldText(record, c)).join(" | "));
        return facet.values.some((value) => text.includes(normalizeSearchText(value)));
    });
}

export class X2ManySearchBar extends Component {
    static template = "mh_x2many_search.X2ManySearchBar";
    static props = {
        columns: Array,
        facets: Array,
        onChange: Function,
    };

    setup() {
        this.state = useState({ query: "", focusedIndex: 0, open: false });
        this.inputRef = useRef("input");
    }

    get items() {
        const query = this.state.query.trim();
        if (!query || !this.state.open) {
            return [];
        }
        // The first suggestion searches every column, like typing in Odoo's search view.
        // Columns with the same label (Amount with and without tax) are one suggestion.
        const byLabel = new Map();
        for (const column of this.props.columns) {
            const label = column.label || column.name;
            byLabel.set(label, [...(byLabel.get(label) || []), column.name]);
        }
        return [
            { names: false, label: "" },
            ...[...byLabel].map(([label, names]) => ({ names, label })),
        ].map((item, index) => ({ ...item, id: index, query }));
    }

    select(item) {
        const facets = this.props.facets.map((f) => ({ ...f, values: [...f.values] }));
        const existing = facets.find((f) => f.label === (item.label || _t("All")));
        if (existing) {
            existing.values.push(item.query);
        } else {
            facets.push({ names: item.names, label: item.label || _t("All"), values: [item.query] });
        }
        this.state.query = "";
        this.state.focusedIndex = 0;
        // Owl may skip writing "" back if the box was never rendered with the typed text.
        if (this.inputRef.el) {
            this.inputRef.el.value = "";
        }
        this.props.onChange(facets);
        this.inputRef.el?.focus();
    }

    removeFacet(facet) {
        this.props.onChange(this.props.facets.filter((f) => f !== facet));
        this.inputRef.el?.focus();
    }

    onInput() {
        // t-model keeps state.query in step with the box.
        this.state.focusedIndex = 0;
        this.state.open = true;
    }

    onKeydown(ev) {
        const items = this.items;
        switch (ev.key) {
            case "ArrowDown":
                if (items.length) {
                    ev.preventDefault();
                    this.state.focusedIndex = (this.state.focusedIndex + 1) % items.length;
                }
                break;
            case "ArrowUp":
                if (items.length) {
                    ev.preventDefault();
                    this.state.focusedIndex = (this.state.focusedIndex - 1 + items.length) % items.length;
                }
                break;
            case "Enter":
                // Never let Enter reach the form: it would save or open a line.
                ev.preventDefault();
                ev.stopPropagation();
                if (items.length) {
                    this.select(items[this.state.focusedIndex]);
                }
                break;
            case "Escape":
                if (items.length) {
                    ev.stopPropagation();
                    this.state.open = false;
                }
                break;
            case "Backspace":
                if (!this.state.query && this.props.facets.length) {
                    this.removeFacet(this.props.facets.at(-1));
                }
                break;
        }
    }

    onFocus() {
        this.state.open = true;
    }

    onBlur() {
        // Let a click on a suggestion land before the suggestions close.
        setTimeout(() => {
            if (this.inputRef.el && document.activeElement !== this.inputRef.el) {
                this.state.open = false;
            }
        }, 200);
    }
}
