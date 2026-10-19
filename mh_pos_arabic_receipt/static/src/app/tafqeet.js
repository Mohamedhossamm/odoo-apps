/** @odoo-module */
// Money amounts in Arabic words (تفقيط), computed in the browser so receipts print offline.
// Same rules and output as arabic_amount_in_words/tools/tafqeet.py; keep the two in step.

export const DEFAULT_PREFIX = "فقط";
export const DEFAULT_SUFFIX = "لا غير";
const ZERO = "صفر";

// Number words as used with a masculine noun (ثلاثة جنيهات) and a feminine one (ثلاث هللات).
const ONES_WITH_MASCULINE = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة", "عشرة"];
const ONES_WITH_FEMININE = ["", "واحدة", "اثنتان", "ثلاث", "أربع", "خمس", "ست", "سبع", "ثماني", "تسع", "عشر"];
const TENS = ["", "", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"];
const HUNDREDS = ["", "مائة", "مائتان", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"];
// مائتان drops its nun when a noun follows directly: مائتا جنيه.
const TWO_HUNDRED_CONSTRUCT = "مائتا";

function noun(singular, dual, dualConstruct, plural, accusative, feminine = false, isScale = false) {
    return { singular, dual, dualConstruct, plural, accusative, feminine, isScale };
}

const THOUSAND = noun("ألف", "ألفان", "ألفا", "آلاف", "ألفاً", false, true);
const MILLION = noun("مليون", "مليونان", "مليونا", "ملايين", "مليوناً", false, true);
const BILLION = noun("مليار", "ملياران", "مليارا", "مليارات", "ملياراً", false, true);
const SCALES = [
    [1e9, BILLION],
    [1e6, MILLION],
    [1e3, THOUSAND],
];

const POUND = noun("جنيه", "جنيهان", "جنيها", "جنيهات", "جنيهاً");
const PIASTRE = noun("قرش", "قرشان", "قرشا", "قروش", "قرشاً");
const RIYAL = noun("ريال", "ريالان", "ريالا", "ريالات", "ريالاً");
const HALALA = noun("هللة", "هللتان", "هللتا", "هللات", "هللة", true);
const DIRHAM = noun("درهم", "درهمان", "درهما", "دراهم", "درهماً");
const FILS = noun("فلس", "فلسان", "فلسا", "فلوس", "فلساً");
const DINAR = noun("دينار", "ديناران", "دينارا", "دنانير", "ديناراً");
const BAISA = noun("بيسة", "بيستان", "بيستا", "بيسات", "بيسة", true);
const DOLLAR = noun("دولار", "دولاران", "دولارا", "دولارات", "دولاراً");
const CENT = noun("سنت", "سنتان", "سنتا", "سنتات", "سنتاً");

export const CURRENCIES = {
    EGP: { unit: POUND, subunit: PIASTRE, decimals: 2 },
    SAR: { unit: RIYAL, subunit: HALALA, decimals: 2 },
    AED: { unit: DIRHAM, subunit: FILS, decimals: 2 },
    QAR: { unit: RIYAL, subunit: DIRHAM, decimals: 2 },
    KWD: { unit: DINAR, subunit: FILS, decimals: 3 },
    BHD: { unit: DINAR, subunit: FILS, decimals: 3 },
    JOD: { unit: DINAR, subunit: FILS, decimals: 3 },
    OMR: { unit: RIYAL, subunit: BAISA, decimals: 3 },
    USD: { unit: DOLLAR, subunit: CENT, decimals: 2 },
};

function below100(n, feminineNoun) {
    const ones = feminineNoun ? ONES_WITH_FEMININE : ONES_WITH_MASCULINE;
    if (n <= 10) {
        return ones[n];
    }
    if (n === 11) {
        return feminineNoun ? "إحدى عشرة" : "أحد عشر";
    }
    if (n === 12) {
        return feminineNoun ? "اثنتا عشرة" : "اثنا عشر";
    }
    if (n < 20) {
        return `${ones[n - 10]} ${feminineNoun ? "عشرة" : "عشر"}`;
    }
    const tens = Math.floor(n / 10);
    const unit = n % 10;
    if (!unit) {
        return TENS[tens];
    }
    const unitWord = unit === 1 ? (feminineNoun ? "إحدى" : "واحد") : ones[unit];
    return `${unitWord} و${TENS[tens]}`;
}

function below1000(n, feminineNoun, nounFollows) {
    const hundreds = Math.floor(n / 100);
    const rest = n % 100;
    const parts = [];
    if (hundreds) {
        parts.push(hundreds === 2 && !rest && nounFollows ? TWO_HUNDRED_CONSTRUCT : HUNDREDS[hundreds]);
    }
    if (rest) {
        parts.push(below100(rest, feminineNoun));
    }
    return parts.join(" و");
}

/** "n noun" for 1 <= n <= 999 with Arabic agreement. See tafqeet.py for the rules. */
function counted(n, theNoun, alone, moreFollows = false) {
    if (alone && n === 1) {
        return theNoun.isScale ? theNoun.singular : `${theNoun.singular} ${theNoun.feminine ? "واحدة" : "واحد"}`;
    }
    if (alone && n === 2) {
        return theNoun.isScale && !moreFollows ? theNoun.dualConstruct : theNoun.dual;
    }
    const lastTwo = n % 100;
    let form;
    if (lastTwo >= 3 && lastTwo <= 10) {
        form = theNoun.plural;
    } else if (lastTwo >= 11 && lastTwo <= 99) {
        form = moreFollows || !theNoun.isScale ? theNoun.accusative : theNoun.singular;
    } else {
        form = theNoun.singular;
    }
    return `${below1000(n, theNoun.feminine, lastTwo === 0)} ${form}`;
}

function integerWords(n, unit) {
    if (n < 1000) {
        return counted(n, unit, true);
    }
    const parts = [];
    let rest = n;
    for (const [scaleValue, scaleNoun] of SCALES) {
        const count = Math.floor(rest / scaleValue);
        rest = rest % scaleValue;
        if (!count) {
            continue;
        }
        if (count >= 1000) {
            throw new Error("Amounts of a trillion or more are not supported");
        }
        parts.push(counted(count, scaleNoun, true, rest > 0));
    }
    if (rest) {
        parts.push(counted(rest, unit, false));
        return parts.join(" و");
    }
    // Nothing below the last scale word: the currency noun follows it directly, in the genitive.
    return `${parts.join(" و")} ${unit.singular}`;
}

/** Whole units and subunits, rounded half up to the currency's decimals. */
export function splitAmount(amount, decimals) {
    const factor = 10 ** decimals;
    // Round on the decimal string, not the float, so 10.005 rounds up like in Python's Decimal.
    const [whole, fraction = ""] = Number(amount).toFixed(decimals + 3).split(".");
    let units = Number(whole) * factor + Number((fraction + "000").slice(0, decimals) || 0);
    if (Number(fraction.charAt(decimals) || 0) >= 5) {
        units += 1;
    }
    if (units < 0) {
        throw new Error("Negative amounts are not supported");
    }
    return [Math.floor(units / factor), units % factor];
}

/** Write `amount` in Arabic words, or return "" when the currency has no Arabic wording. */
export function amountToArabic(amount, currencyCode, { prefix = DEFAULT_PREFIX, suffix = DEFAULT_SUFFIX } = {}) {
    const currency = CURRENCIES[String(currencyCode || "").toUpperCase()];
    if (!currency || !(amount >= 0)) {
        return "";
    }
    const [whole, fraction] = splitAmount(amount, currency.decimals);
    const phrases = [];
    if (whole) {
        phrases.push(integerWords(whole, currency.unit));
    }
    if (fraction) {
        phrases.push(counted(fraction, currency.subunit, true));
    }
    const body = phrases.length ? phrases.join(" و") : `${ZERO} ${currency.unit.singular}`;
    return [prefix, body, suffix].filter(Boolean).join(" ");
}
