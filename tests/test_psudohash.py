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


# ----------------( char_variants )---------------- #
def test_char_variants_letter_with_leet():
    assert ph.char_variants("a", T) == sorted({"A", "a", "@", "4"})


def test_char_variants_letter_without_leet():
    assert ph.char_variants("m", T) == sorted({"M", "m"})


def test_char_variants_non_alpha_is_singleton():
    assert ph.char_variants("_", T) == ["_"]
    assert ph.char_variants("5", T) == ["5"]


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
