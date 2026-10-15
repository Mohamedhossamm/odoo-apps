"""Write money amounts in Arabic words (تفقيط) with correct number-noun agreement.

    >>> amount_to_arabic(1234.50, "EGP")
    'فقط ألف ومائتان وأربعة وثلاثون جنيهاً وخمسون قرشاً لا غير'

Pure Python with no dependencies, so the same file works inside an Odoo module
and on its own.

Agreement rules applied to the counted noun (currency, subunit, or a scale word
such as ألف):
    1          noun + "one"        جنيه واحد / هللة واحدة
    2          dual                جنيهان / هللتان
    3 – 10     plural              ثلاثة جنيهات / ثلاث هللات
    11 – 99    singular accusative أحد عشر جنيهاً
    100, 1000… singular genitive   مائة جنيه / ألف جنيه
The last two digits decide the form, so 103 takes the plural and 150 the
accusative. 3–10 and 13–19 take the opposite gender of the noun.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Tuple, Union

ZERO = "صفر"
DEFAULT_PREFIX = "فقط"
DEFAULT_SUFFIX = "لا غير"

# Number words as used with a masculine noun (ثلاثة جنيهات) and a feminine one (ثلاث هللات).
ONES_WITH_MASCULINE = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة", "عشرة"]
ONES_WITH_FEMININE = ["", "واحدة", "اثنتان", "ثلاث", "أربع", "خمس", "ست", "سبع", "ثماني", "تسع", "عشر"]
TENS = ["", "", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
HUNDREDS = ["", "مائة", "مائتان", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"]
# مائتان drops its nun when a noun follows directly: مائتا جنيه.
TWO_HUNDRED_CONSTRUCT = "مائتا"


@dataclass(frozen=True)
class Noun:
    singular: str
    dual: str
    dual_construct: str  # the dual when a noun follows directly: ألفا جنيه
    plural: str
    accusative: str  # after 11–99: جنيهاً
    feminine: bool = False


@dataclass(frozen=True)
class Currency:
    unit: Noun
    subunit: Noun
    decimals: int


THOUSAND = Noun("ألف", "ألفان", "ألفا", "آلاف", "ألفاً")
MILLION = Noun("مليون", "مليونان", "مليونا", "ملايين", "مليوناً")
BILLION = Noun("مليار", "ملياران", "مليارا", "مليارات", "ملياراً")
SCALES = [(10**9, BILLION), (10**6, MILLION), (10**3, THOUSAND)]

POUND = Noun("جنيه", "جنيهان", "جنيها", "جنيهات", "جنيهاً")
PIASTRE = Noun("قرش", "قرشان", "قرشا", "قروش", "قرشاً")
RIYAL = Noun("ريال", "ريالان", "ريالا", "ريالات", "ريالاً")
HALALA = Noun("هللة", "هللتان", "هللتا", "هللات", "هللة", feminine=True)
DIRHAM = Noun("درهم", "درهمان", "درهما", "دراهم", "درهماً")
FILS = Noun("فلس", "فلسان", "فلسا", "فلوس", "فلساً")
DINAR = Noun("دينار", "ديناران", "دينارا", "دنانير", "ديناراً")
BAISA = Noun("بيسة", "بيستان", "بيستا", "بيسات", "بيسة", feminine=True)
DOLLAR = Noun("دولار", "دولاران", "دولارا", "دولارات", "دولاراً")
CENT = Noun("سنت", "سنتان", "سنتا", "سنتات", "سنتاً")

CURRENCIES: Dict[str, Currency] = {
    "EGP": Currency(POUND, PIASTRE, 2),
    "SAR": Currency(RIYAL, HALALA, 2),
    "AED": Currency(DIRHAM, FILS, 2),
    "QAR": Currency(RIYAL, DIRHAM, 2),
    "KWD": Currency(DINAR, FILS, 3),
    "BHD": Currency(DINAR, FILS, 3),
    "JOD": Currency(DINAR, FILS, 3),
    "OMR": Currency(RIYAL, BAISA, 3),
    "USD": Currency(DOLLAR, CENT, 2),
}


def _below_100(n: int, feminine_noun: bool) -> str:
    ones = ONES_WITH_FEMININE if feminine_noun else ONES_WITH_MASCULINE
    if n <= 10:
        return ones[n]
    if n == 11:
        return "إحدى عشرة" if feminine_noun else "أحد عشر"
    if n == 12:
        return "اثنتا عشرة" if feminine_noun else "اثنا عشر"
    if n < 20:
        return f"{ones[n - 10]} {'عشرة' if feminine_noun else 'عشر'}"
    tens, unit = divmod(n, 10)
    if not unit:
        return TENS[tens]
    unit_word = ("إحدى" if feminine_noun else "واحد") if unit == 1 else ones[unit]
    return f"{unit_word} و{TENS[tens]}"


def _below_1000(n: int, feminine_noun: bool, noun_follows: bool) -> str:
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        word = HUNDREDS[hundreds]
        if hundreds == 2 and not rest and noun_follows:
            word = TWO_HUNDRED_CONSTRUCT
        parts.append(word)
    if rest:
        parts.append(_below_100(rest, feminine_noun))
    return " و".join(parts)


def _counted(n: int, noun: Noun, alone: bool, more_follows: bool = False) -> str:
    """'n noun' for 1 <= n <= 999 with Arabic agreement.

    alone: n is the whole count of this noun (1 and 2 then become the noun itself:
        جنيه واحد, جنيهان). False for the last group of a bigger number, where
        1 and 2 are written out: ألف وواحد جنيه.
    more_follows: only for scale words. More number words come after (أحد عشر ألفاً
        وخمسمائة), as opposed to the currency noun directly (أحد عشر ألف جنيه).
    """
    is_scale = noun in (THOUSAND, MILLION, BILLION)
    if alone and n == 1:
        if is_scale:
            return noun.singular
        return f"{noun.singular} {'واحدة' if noun.feminine else 'واحد'}"
    if alone and n == 2:
        if is_scale and not more_follows:
            return noun.dual_construct
        return noun.dual
    last_two = n % 100
    if 3 <= last_two <= 10:
        form = noun.plural
    elif 11 <= last_two <= 99:
        form = noun.accusative if (more_follows or not is_scale) else noun.singular
    else:
        form = noun.singular
    return f"{_below_1000(n, noun.feminine, noun_follows=last_two == 0)} {form}"


def _integer_words(n: int, unit: Noun) -> str:
    """Words for a positive whole number of `unit`, scales included."""
    if n < 1000:
        return _counted(n, unit, alone=True)

    parts: List[str] = []
    rest = n
    for scale_value, scale_noun in SCALES:
        count, rest = divmod(rest, scale_value)
        if not count:
            continue
        if count >= 1000:
            raise ValueError("Amounts of a trillion or more are not supported")
        parts.append(_counted(count, scale_noun, alone=True, more_follows=rest > 0))

    if rest:
        parts.append(_counted(rest, unit, alone=False))
        return " و".join(parts)
    # Nothing below the last scale word: the currency noun follows it directly, in the genitive.
    return f"{' و'.join(parts)} {unit.singular}"


def split_amount(amount: Union[int, float, str, Decimal], decimals: int) -> Tuple[int, int]:
    """Whole units and subunits, rounded half up to the currency's decimals."""
    quantum = Decimal(1).scaleb(-decimals)
    value = Decimal(str(amount)).quantize(quantum, rounding=ROUND_HALF_UP)
    if value < 0:
        raise ValueError("Negative amounts are not supported")
    whole = int(value)
    fraction = int((value - whole) * (10**decimals))
    return whole, fraction


def amount_to_arabic(
    amount: Union[int, float, str, Decimal],
    currency: Union[str, Currency],
    prefix: str = DEFAULT_PREFIX,
    suffix: str = DEFAULT_SUFFIX,
) -> str:
    """Write `amount` in Arabic words, for example on an invoice or a cheque."""
    if isinstance(currency, str):
        try:
            currency = CURRENCIES[currency.upper()]
        except KeyError:
            raise ValueError(f"No Arabic wording defined for currency {currency!r}") from None

    whole, fraction = split_amount(amount, currency.decimals)
    phrases = []
    if whole:
        phrases.append(_integer_words(whole, currency.unit))
    if fraction:
        phrases.append(_counted(fraction, currency.subunit, alone=True))
    body = " و".join(phrases) if phrases else f"{ZERO} {currency.unit.singular}"
    return " ".join(part for part in (prefix, body, suffix) if part)
