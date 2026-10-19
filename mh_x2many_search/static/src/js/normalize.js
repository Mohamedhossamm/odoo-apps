/** @odoo-module */
// Arabic is typed many ways for the same word. Searching compares both sides in one spelling.
// Same rules as mh_pos_arabic_search/static/src/app/normalize.js; keep the two in step.

const LETTERS = {
    // Alef with hamza or madda, and alef wasla: أحمد = احمد
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ٱ": "ا",
    // Taa marbuta written as haa: قهوة = قهوه
    "ة": "ه",
    // Alef maqsura and yaa with hamza written as yaa: مستشفى = مستشفي
    "ى": "ي",
    "ئ": "ي",
    // Waw with hamza: مؤسسة = موسسة
    "ؤ": "و",
    // Persian keyboard letters that look the same
    "ک": "ك",
    "ی": "ي",
    "ہ": "ه",
};

// Tashkeel (fathatan to sukun, superscript alef) and tatweel: مُحَمَّد = محمد, مـحـمـد = محمد
const IGNORED = /[ً-ْٰـ]/g;
const ARABIC_INDIC_DIGITS = /[٠-٩]/g;
const PERSIAN_DIGITS = /[۰-۹]/g;
const TO_REPLACE = new RegExp(`[${Object.keys(LETTERS).join("")}]`, "g");

/** The spelling both the search word and the searched text are compared in. */
export function normalizeArabic(text) {
    if (!text) {
        return text;
    }
    return text
        .replace(IGNORED, "")
        .replace(TO_REPLACE, (letter) => LETTERS[letter])
        .replace(ARABIC_INDIC_DIGITS, (digit) => String(digit.charCodeAt(0) - 0x0660))
        .replace(PERSIAN_DIGITS, (digit) => String(digit.charCodeAt(0) - 0x06f0));
}
