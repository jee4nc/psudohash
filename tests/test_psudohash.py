"""Unit tests for the pure generation helpers in psudohash."""
import itertools

import psudohash as ph

T = ph.TRANSFORMATIONS


# ----------------( within_length )---------------- #
def test_within_length_no_filters():
    assert ph.within_length("abc", None, None) is True


def test_within_length_inclusive_bounds():
    # minlen/maxlen are inclusive; a word exactly at the bound passes.
    assert ph.within_length("abcde", 5, 5) is True
    assert ph.within_length("abcd", 5, 5) is False   # too short
    assert ph.within_length("abcdef", 5, 5) is False  # too long


# ----------------( case_forms )---------------- #
def test_case_forms_all_count():
    assert len(list(ph.case_forms("foo", "all"))) == 2 ** 3


def test_case_forms_realistic_single_word():
    assert set(ph.case_forms("foo", "realistic")) == {"foo", "FOO", "Foo"}


def test_case_forms_realistic_titlecases_segments():
    # Title Case capitalizes each segment; Capitalize only the first letter.
    out = set(ph.case_forms("foo_bar", "realistic"))
    assert "Foo_Bar" in out   # title
    assert "Foo_bar" in out   # capitalize


# ----------------( leet_forms )---------------- #
def test_leet_forms_none():
    assert list(ph.leet_forms("amazon", T, "none")) == ["amazon"]


def test_leet_forms_all_count():
    # "aa": each position independently in [a, @, 4] -> 9 combos
    assert len(list(ph.leet_forms("aa", T, "all"))) == 9


def test_leet_forms_realistic_is_consistent():
    # Both a's substituted together or not at all: aa, @@, 44 (no mixed "a@").
    assert set(ph.leet_forms("aa", T, "realistic")) == {"aa", "@@", "44"}


def test_leet_forms_realistic_replaces_all_cases():
    assert "@m@zon" in set(ph.leet_forms("amazon", T, "realistic"))


# ----------------( meets_complexity )---------------- #
def test_meets_complexity_empty_passes():
    assert ph.meets_complexity("abc", set()) is True


def test_meets_complexity_all_classes():
    assert ph.meets_complexity("Abc1!", {"lower", "upper", "digit", "special"}) is True
    assert ph.meets_complexity("abc1!", {"upper"}) is False
    assert ph.meets_complexity("Abcde", {"digit"}) is False
    assert ph.meets_complexity("Abcd1", {"special"}) is False


# ----------------( base_variants )---------------- #
def test_base_variants_count_amazon():
    # a:4  m:2  a:4  z:2  o:3  n:2  = 384
    assert len(list(ph.base_variants("amazon", T))) == 384


def test_base_variants_count_foo():
    # f:2  o:3  o:3 = 18
    assert len(list(ph.base_variants("foo", T))) == 18


def test_base_variants_are_unique():
    out = list(ph.base_variants("amazon", T))
    assert len(out) == len(set(out))


def test_base_variants_contains_identity_and_full_leet():
    out = set(ph.base_variants("foo", T))
    assert "foo" in out
    assert "f00" in out
    assert "FOO" in out


def test_base_variants_realistic_is_smaller_and_a_subset():
    full = set(ph.base_variants("amazon", T, "all", "all"))
    realistic = set(ph.base_variants("amazon", T, "realistic", "realistic"))
    assert 0 < len(realistic) < len(full)
    assert realistic <= full  # realistic forms are a subset of the exhaustive set


# ----------------( numbering_variants )---------------- #
def test_numbering_variants_level1():
    out = list(ph.numbering_variants("foo", level=1, count_max=4))  # k = 1..3
    assert out == ["foo1", "foo_1", "foo2", "foo_2", "foo3", "foo_3"]


def test_numbering_variants_zero_padding():
    out = list(ph.numbering_variants("x", level=2, count_max=2))  # k = 1
    # width 1 then width 2
    assert out == ["x1", "x_1", "x01", "x_01"]


# ----------------( year_variants )---------------- #
def test_year_variants_full_and_short():
    out = list(ph.year_variants("amazon", ["2020"], ["", "_"]))
    assert out == ["amazon2020", "amazon20", "amazon_2020", "amazon_20"]


# ----------------( build_dates )---------------- #
def test_build_dates_mmyyyy():
    out = ph.build_dates(["1998"], ["mmyyyy"])
    assert out[0] == "011998"
    assert "121998" in out
    assert len(out) == 12


def test_build_dates_year_tokens():
    assert ph.build_dates(["1998"], ["yyyy", "yy"]) == ["1998", "98"]


def test_build_dates_skips_impossible_dates():
    # 1999 is not a leap year -> no 29 Feb; 2000 is -> 29 Feb present.
    assert "29021999" not in ph.build_dates(["1999"], ["ddmmyyyy"])
    assert "29022000" in ph.build_dates(["2000"], ["ddmmyyyy"])
    # 31 Feb / 31 Apr never exist.
    ddmm = ph.build_dates(["2000"], ["ddmm"])
    assert "3102" not in ddmm and "3104" not in ddmm
    assert "0101" in ddmm and "3112" in ddmm


def test_build_dates_dedup_and_order():
    out = ph.build_dates(["1998", "1998"], ["yyyy"])  # duplicate year
    assert out == ["1998"]


# ----------------( paddings )---------------- #
def test_paddings_after_underscore_rule():
    # "!" -> word!, word_!  ; "_x" -> word_x only (already starts with '_')
    assert list(ph.paddings_after("dragon", ["!"])) == ["dragon!", "dragon_!"]
    assert list(ph.paddings_after("dragon", ["_x"])) == ["dragon_x"]


def test_paddings_before_underscore_rule():
    # "!" -> !word, !_word ; "x_" -> x_word only (already ends with '_')
    assert list(ph.paddings_before("dragon", ["!"])) == ["!dragon", "!_dragon"]
    assert list(ph.paddings_before("dragon", ["x_"])) == ["x_dragon"]


# ----------------( generate_keyword integration )---------------- #
def _cfg(**kw):
    defaults = dict(minlen=None, maxlen=None, numbering_level=None,
                    numbering_max=51, years=[], paddings=[],
                    pad_after=False, pad_before=False)
    defaults.update(kw)
    return ph.Config(**defaults)


def test_generate_keyword_base_only():
    out = list(ph.generate_keyword("amazon", _cfg()))
    assert len(out) == 384
    assert set(out) == set(ph.base_variants("amazon", T))


def test_generate_keyword_maxlen_filters_uniformly():
    # With maxlen, every emitted word must satisfy the bound.
    cfg = _cfg(maxlen=7, years=["2020"])
    out = list(ph.generate_keyword("amazon", cfg))
    assert out, "expected some output"
    assert all(len(w) <= 7 for w in out)


def test_generate_keyword_dates_appended_with_separators():
    cfg = _cfg(dates=["011998"])
    out = set(ph.generate_keyword("pedro", cfg))
    assert "pedro011998" in out
    assert "pedro_011998" in out   # one of the YEAR_SEPARATORS variants


def test_generate_keyword_dates_feed_padding_pool():
    cfg = _cfg(dates=["011998"], paddings=["!"], pad_after=True)
    out = set(ph.generate_keyword("pedro", cfg))
    assert "pedro011998!" in out   # padding applied to a date variant


def test_generate_keyword_require_filters_emitted_but_not_pool():
    # require=digit drops the bare base word but keeps year variants that
    # gained a digit -> the pool must not be pruned by the complexity filter.
    cfg = _cfg(years=["2020"], require={"digit"})
    out = set(ph.generate_keyword("amazon", cfg))
    assert "amazon" not in out       # no digit -> filtered
    assert "amazon2020" in out       # base fed the year stage despite being filtered


def test_generate_keyword_years_feed_paddings_not_numbering():
    # Year variants must be available as padding bases; numbering must not.
    cfg = _cfg(years=["2020"], paddings=["!"], pad_after=True, numbering_level=1, numbering_max=3)
    out = set(ph.generate_keyword("foo", cfg))
    assert "foo2020!" in out          # padding applied to a year variant
    assert "foo1" in out              # numbering emitted
    assert "foo1!" not in out         # padding NOT applied to a numbering variant


# ----------------( deduplicate_file )---------------- #
def test_deduplicate_file(tmp_path):
    p = tmp_path / "wl.txt"
    p.write_text("a\nb\na\nc\nb\na\n")
    kept, removed = ph.deduplicate_file(str(p))
    assert kept == 3
    assert removed == 3
    assert p.read_text() == "a\nb\nc\n"  # first-seen order preserved
