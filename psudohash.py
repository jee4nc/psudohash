#!/bin/python3
#
# Author: Panagiotis Chartas (t3l3machus)
# https://github.com/t3l3machus
#
# Fork: refactored to a generator-based pipeline (no global mutable state)
# with a single source of truth for the output count.

import argparse, os, sys, itertools
from pathlib import Path
from tqdm import tqdm

# Resolve bundled data files relative to this script, not the CWD,
# so the tool works regardless of the directory it's invoked from.
SCRIPT_DIR = Path(__file__).resolve().parent
PADDINGS_FILE = SCRIPT_DIR / 'common_padding_values.txt'

# Colors (zeroed out by main() when color is disabled)
MAIN = '\033[38;5;50m'
LOGO = '\033[38;5;41m'
LOGO2 = '\033[38;5;42m'
GREEN = '\033[38;5;82m'
ORANGE = '\033[0;38;5;214m'
PRPL = '\033[0;38;5;26m'
PRPL2 = '\033[0;38;5;25m'
RED = '\033[1;31m'
END = '\033[0m'
BOLD = '\033[1m'
USE_COLOR = True

# Character -> symbol/number (leet) substitution schema. Edit to taste.
TRANSFORMATIONS = [
    {'a': ['@', '4']},
    {'b': '8'},
    {'e': '3'},
    {'g': ['9', '6']},
    {'i': ['1', '!']},
    {'o': '0'},
    {'s': ['$', '5']},
    {'t': '7'},
]

# Separators inserted between a mutated word and an appended year.
YEAR_SEPARATORS = ['', '_', '-', '@']


# ----------------( Pure generation helpers )---------------- #
def within_length(word, minlen, maxlen):
    """Return True if `word` (without trailing newline) passes the length filters."""
    n = len(word)
    if minlen and n < minlen:
        return False
    if maxlen and n > maxlen:
        return False
    return True


COMPLEXITY_CLASSES = ('lower', 'upper', 'digit', 'special')


def meets_complexity(word, required):
    """
    Return True if `word` contains at least one character of every class named
    in `required` (a set drawn from COMPLEXITY_CLASSES). Empty/None means no
    requirement.
    """
    if not required:
        return True
    if 'lower' in required and not any(c.islower() for c in word):
        return False
    if 'upper' in required and not any(c.isupper() for c in word):
        return False
    if 'digit' in required and not any(c.isdigit() for c in word):
        return False
    if 'special' in required and not any(not c.isalnum() for c in word):
        return False
    return True


def _leet_subs(low, transformations):
    """Return the list of leet substitutions for a lowercase character, or []."""
    for t in transformations:
        if low in t:
            sub = t[low]
            return sub if isinstance(sub, list) else [sub]
    return []


def case_forms(word, mode):
    """
    Yield case variations of `word`.
      - "all":       every per-character upper/lower combination (2**letters).
      - "realistic": only the forms humans actually use — all-lower, ALL-UPPER,
                     Capitalized and Title Case (per-segment capitalization).
    """
    if mode == 'realistic':
        seen = set()
        for form in (word.lower(), word.upper(), word.capitalize(), word.title()):
            if form not in seen:
                seen.add(form)
                yield form
    else:  # "all"
        options = [sorted({ch.upper(), ch.lower()}) for ch in word]
        for combo in itertools.product(*options):
            yield ''.join(combo)


def leet_forms(word, transformations, mode):
    """
    Yield leet (character→symbol) variations of `word`.
      - "none":      no substitution, just the word itself.
      - "all":       every per-character combination of keep/substitute.
      - "realistic": consistent substitution — each substitutable letter is
                     either left alone or replaced in ALL its occurrences by one
                     of its symbols (how humans actually leet-speak).
    """
    if mode == 'none':
        yield word
        return

    if mode == 'realistic':
        # One choice per distinct substitutable letter, applied to every occurrence.
        letters, choices = [], []
        for low in dict.fromkeys(ch.lower() for ch in word):
            subs = _leet_subs(low, transformations)
            if subs:
                letters.append(low)
                choices.append([None, *subs])  # None == keep
        seen = set()
        for combo in itertools.product(*choices) if choices else [()]:
            result = word
            for low, choice in zip(letters, combo):
                if choice is not None:
                    result = result.replace(low, choice).replace(low.upper(), choice)
            if result not in seen:
                seen.add(result)
                yield result
        return

    # "all": independent keep/substitute per character position.
    options = [[ch, *_leet_subs(ch.lower(), transformations)] for ch in word]
    for combo in itertools.product(*options):
        yield ''.join(combo)


def base_variants(word, transformations, case_mode='all', leet_mode='all'):
    """
    Yield every case- and leet-based variant of `word` by composing the chosen
    case mode with the chosen leet mode. Duplicates are removed. The defaults
    (all/all) reproduce the original per-character Cartesian product.
    """
    seen = set()
    for cased in case_forms(word, case_mode):
        for leeted in leet_forms(cased, transformations, leet_mode):
            if leeted not in seen:
                seen.add(leeted)
                yield leeted


def numbering_variants(word, level, count_max):
    """
    Yield numbering suffixes for `word`: for each digit width 1..level and each
    number 1..count_max-1, both "<word><n>" and "<word>_<n>" (zero-padded).
    """
    for width in range(1, level + 1):
        for k in range(1, count_max):
            num = str(k).zfill(width)
            yield f"{word}{num}"
            yield f"{word}_{num}"


def year_variants(word, years, separators):
    """Yield "<word><sep><YYYY>" and "<word><sep><YY>" for each year/separator."""
    for y in years:
        for sep in separators:
            yield f"{word}{sep}{y}"
            yield f"{word}{sep}{y[2:]}"


def paddings_after(word, paddings):
    """Yield "<word><pad>" and (unless pad starts with '_') "<word>_<pad>"."""
    for val in paddings:
        yield f"{word}{val}"
        if not val.startswith('_'):
            yield f"{word}_{val}"


def paddings_before(word, paddings):
    """Yield "<pad><word>" and (unless pad ends with '_') "<pad>_<word>"."""
    for val in paddings:
        yield f"{val}{word}"
        if not val.endswith('_'):
            yield f"{val}_{word}"


def generate_keyword(keyword, cfg):
    """
    Yield every final mutation for a single keyword, applying length filtering
    uniformly to each emitted word. Stages mirror the original tool:

      1. base (case + leet) variants            -> always
      2. numbering suffixes (from base)         -> if -an
      3. year suffixes (from base, fed forward) -> if -y
      4. paddings after / before (from base + year variants) -> if -cpa / -cpb

    Numbering variants are not fed into the padding stage (matching the original
    behaviour); year variants are.
    """
    def ok(w):
        return within_length(w, cfg.minlen, cfg.maxlen) and meets_complexity(w, cfg.require)

    base = list(base_variants(keyword, TRANSFORMATIONS, cfg.case_mode, cfg.leet_mode))

    for w in base:
        if ok(w):
            yield w

    if cfg.numbering_level:
        for w in base:
            for v in numbering_variants(w, cfg.numbering_level, cfg.numbering_max):
                if ok(v):
                    yield v

    # Pool that the padding stages operate on: base words plus year variants.
    pool = base
    if cfg.years:
        pool = list(base)
        for w in base:
            for v in year_variants(w, cfg.years, YEAR_SEPARATORS):
                if ok(v):
                    yield v
                pool.append(v)

    if cfg.pad_after:
        for w in pool:
            for v in paddings_after(w, cfg.paddings):
                if ok(v):
                    yield v

    if cfg.pad_before:
        for w in pool:
            for v in paddings_before(w, cfg.paddings):
                if ok(v):
                    yield v


def deduplicate_file(path):
    """
    Remove duplicate lines from `path` in place, preserving first-seen order.
    Streams line by line through a temp file, holding only a set of seen lines
    in memory. Returns (kept, removed) counts.
    """
    seen = set()
    kept = removed = 0
    tmp_path = f'{path}.dedup.tmp'

    with open(path, 'r') as src, open(tmp_path, 'w') as dst:
        for line in src:
            if line in seen:
                removed += 1
                continue
            seen.add(line)
            dst.write(line)
            kept += 1

    os.replace(tmp_path, path)
    return kept, removed


# ----------------( CLI / configuration )---------------- #
class Config:
    """Resolved run settings derived from parsed CLI arguments."""
    __slots__ = ('minlen', 'maxlen', 'numbering_level', 'numbering_max',
                 'years', 'paddings', 'pad_after', 'pad_before',
                 'case_mode', 'leet_mode', 'require')

    def __init__(self, minlen, maxlen, numbering_level, numbering_max,
                 years, paddings, pad_after, pad_before,
                 case_mode='all', leet_mode='all', require=None):
        self.minlen = minlen
        self.maxlen = maxlen
        self.numbering_level = numbering_level
        self.numbering_max = numbering_max
        self.years = years
        self.paddings = paddings
        self.pad_after = pad_after
        self.pad_before = pad_before
        self.case_mode = case_mode
        self.leet_mode = leet_mode
        self.require = require or set()


def build_parser():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''
Usage examples:

  # 1) No multi-word: treat each keyword separately
      python3 psudohash.py -w foo,bar,baz -cpa
      # → foo, bar, baz

  # 2) In-order joins (-i): up to 2 words by default
      python3 psudohash.py -w foo,bar,baz -i
      # → foo, bar, baz, foobar, foobaz, barbaz

  # 3) All-order combinations (-c): up to 2 words by default
      python3 psudohash.py -w foo,bar,baz -c
      # → foo, bar, baz, foobar, foobaz, barfoo, barbaz, bazfoo, bazbar

  # 4) Change separator between joined words
      python3 psudohash.py -w foo,bar,baz -i --sep "_"
      # → foo, bar, baz, foo_bar, foo_baz, bar_baz, foo_bar_baz

  # 5) Combine up to 3 words (instead of default 2)
      python3 psudohash.py -w foo,bar,baz -i --max-combine 3
      # → foo, bar, baz, foobar, foobaz, barbaz, foobarbaz, ...
'''
        )

    parser.add_argument("-w", "--words", action="store", help="Comma separated keywords to mutate", required=True)
    parser.add_argument("-i", "--inorder", action="store_true", help="Join keywords only in the order given: for each 1≤r≤max_combine, concatenate each r-subset in original sequence.")
    parser.add_argument("-c", "--combinations", action="store_true", help="Generate every ordering of every subset (up to max_combine) of the provided keywords.")
    parser.add_argument("--max-combine", type=int, default=2, help="Maximum number of raw keywords to join into one base string (default: 2). Applies when using -i or -c.")
    parser.add_argument("--minlen", type=int, help="Minimum length (inclusive) of any resulting password. Mutations shorter than this are skipped.")
    parser.add_argument("--maxlen", type=int, help="Maximum length (inclusive) of any resulting password. Mutations longer than this are skipped.")
    parser.add_argument("--sep", type=str, default="", help="Separator to insert between joined keywords (default: no separator).")
    parser.add_argument("--case-mode", choices=['all', 'realistic'], default='all', help="Case variation strategy.\n  all       = every upper/lower combination (default, e.g. aMaZoN).\n  realistic = only forms humans use: lower, UPPER, Capitalized, Title Case.")
    parser.add_argument("--leet-mode", choices=['all', 'realistic', 'none'], default='all', help="Leet (char→symbol) substitution strategy.\n  all       = every per-character keep/substitute combination (default).\n  realistic = consistent: each letter is left alone or replaced everywhere.\n  none      = no leet substitution.")
    parser.add_argument("--require", type=str, metavar='CLASSES', help="Keep only passwords containing at least one of each comma-separated\ncharacter class: lower,upper,digit,special (e.g. --require upper,digit,special).")
    parser.add_argument("-R", "--realistic", action="store_true", help="Preset that enables human-like mutations: --case-mode realistic AND\n--leet-mode realistic. Produces a much smaller, higher-signal wordlist.")
    parser.add_argument("-an", "--append-numbering", action="store", help="Append numbering range at the end of each word mutation (before appending year or common paddings).\nThe LEVEL value represents the minimum number of digits. LEVEL must be >= 1. \nSet to 1 will append range: 1,2,3..100\nSet to 2 will append range: 01,02,03..100 + previous\nSet to 3 will append range: 001,002,003..100 + previous.\n\n", type=int, metavar='LEVEL')
    parser.add_argument("-nl", "--numbering-limit", action="store", help="Change max numbering limit value of option -an. Default is 50. Must be used with -an.", type=int, metavar='LIMIT')
    parser.add_argument("-y", "--years", action="store", help="Single OR comma separated OR range of years to be appended to each word mutation (Example: 2022 OR 1990,2017,2022 OR 1990-2000)")
    parser.add_argument("-ap", "--append-padding", action="store", help="Add comma separated values to common paddings (must be used with -cpb OR -cpa)", metavar='VALUES')
    parser.add_argument("-cpb", "--common-paddings-before", action="store_true", help="Append common paddings before each mutated word")
    parser.add_argument("-cpa", "--common-paddings-after", action="store_true", help="Append common paddings after each mutated word")
    parser.add_argument("-cpo", "--custom-paddings-only", action="store_true", help="Use only user provided paddings for word mutations (must be used with -ap AND (-cpb OR -cpa))")
    parser.add_argument("-o", "--output", action="store", help="Output filename (default: output.txt)", metavar='FILENAME')
    parser.add_argument("-q", "--quiet", action="store_true", help="Do not print the banner on startup")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output (also auto-disabled when stdout is not a TTY or NO_COLOR is set)")
    parser.add_argument("-u", "--unique", action="store_true", help="Remove duplicate lines from the final wordlist (order-preserving). Adds a post-processing pass.")
    return parser


def exit_with_msg(parser, msg):
    parser.print_help()
    print(f'\n[{RED}Debug{END}] {msg}\n')
    sys.exit(1)


def parse_years(parser, raw):
    """Parse the -y argument (single, comma list, or range) into a list of strings."""
    def valid(y):
        return y.isdecimal() and 1000 <= int(y) <= 3200

    err = 'Illegal year(s) input. Acceptable years range: 1000 - 3200.'

    if ',' not in raw and '-' not in raw:
        if valid(raw):
            return [raw]
        exit_with_msg(parser, err)

    if ',' in raw:
        years = []
        for y in raw.split(','):
            y = y.strip()
            if not valid(y):
                exit_with_msg(parser, err)
            years.append(y)
        return years

    if raw.count('-') == 1:
        start, end = raw.split('-')
        if valid(start) and valid(end) and int(start) < int(end):
            return [str(y) for y in range(int(start), int(end) + 1)]
        exit_with_msg(parser, err)

    exit_with_msg(parser, err)


def load_paddings(parser, args):
    """Resolve the list of padding values from the file and/or -ap, per the flags."""
    use_paddings = args.common_paddings_before or args.common_paddings_after

    if (args.custom_paddings_only or args.append_padding) and not use_paddings:
        exit_with_msg(parser, 'Options -ap and -cpo must be used with -cpa or -cpb.')

    paddings = []
    if use_paddings and not args.custom_paddings_only:
        try:
            with open(PADDINGS_FILE, 'r') as f:
                paddings = [val.strip() for val in f.readlines()]
        except FileNotFoundError:
            exit_with_msg(parser, f'File "{PADDINGS_FILE}" not found.')
        except OSError as e:
            exit_with_msg(parser, f'Could not read "{PADDINGS_FILE}": {e}')

    if args.append_padding:
        for val in args.append_padding.split(','):
            if val.strip() != '' and val not in paddings:
                paddings.append(val)

    if use_paddings:
        paddings = list(set(paddings))

    return paddings


def build_keywords(args):
    """Build the list of base keywords from -w, honoring -i/-c/--sep/--max-combine."""
    raw = []
    for w in args.words.split(','):
        w = w.strip()
        if not w:
            continue
        if w.isdecimal():
            return None  # caller reports the error
        raw.append(w)

    limit = min(len(raw), args.max_combine)
    keywords = []

    if args.inorder:
        for r in range(1, limit + 1):
            for combo in itertools.combinations(raw, r):
                keywords.append(args.sep.join(combo))
    elif args.combinations:
        for r in range(1, limit + 1):
            for combo in itertools.combinations(raw, r):
                for perm in itertools.permutations(combo):
                    keywords.append(args.sep.join(perm))
    else:
        keywords = list(raw)

    return keywords


# ----------------( Presentation )---------------- #
def banner():
    padding = '  '

    P = [[' ', '┌', '─', '┐'], [' ', '├', '─', '┘'], [' ', '┴', ' ', ' ']]
    S = [[' ', '┌', '─', '┐'], [' ', '└', '─', '┐'], [' ', '└', '─', '┘']]
    U = [[' ', '┬', ' ', '┬'], [' ', '│', ' ', '│'], [' ', '└', '─', '┘']]
    D = [[' ', '┌', '┬', '┐'], [' ', ' ', '│', '│'], [' ', '─', '┴', '┘']]
    O = [[' ', '┌', '─', '┐'], [' ', '│', ' ', '│'], [' ', '└', '─', '┘']]
    H = [[' ', '┐', ' ', '┌'], [' ', '├', '╫', '┤'], [' ', '┘', ' ', '└']]
    A = [[' ', '┌', '─', '┐'], [' ', '├', '─', '┤'], [' ', '┴', ' ', '┴']]
    S = [[' ', '┌', '─', '┐'], [' ', '└', '─', '┐'], [' ', '└', '─', '┘']]
    H = [[' ', '┬', ' ', '┬'], [' ', '├', '─', '┤'], [' ', '┴', ' ', '┴']]

    chars = [P, S, U, D, O, H, A, S, H]
    final = []
    print('\r')
    init_color = 37
    txt_color = init_color
    cl = 0

    for charset in range(0, 3):
        for pos in range(0, len(chars)):
            for i in range(0, len(chars[pos][charset])):
                clr = f'\033[38;5;{txt_color}m' if USE_COLOR else ''
                final.append(f'{clr}{chars[pos][charset][i]}')
                cl += 1
                txt_color = txt_color + 36 if cl <= 3 else txt_color
            cl = 0
            txt_color = init_color
        init_color += 31
        if charset < 2:
            final.append('\n   ')

    print(f"   {''.join(final)}")
    print(f'{END}{padding}                        by t3l3machus\n')


def human_size(num_bytes):
    if num_bytes > 100000:
        return f'{round(num_bytes / 1000 / 1000, 1)} MB'
    return f'{num_bytes} bytes'


# ----------------( Main )---------------- #
def main():
    global MAIN, LOGO, LOGO2, GREEN, ORANGE, PRPL, PRPL2, RED, END, BOLD, USE_COLOR

    parser = build_parser()
    args = parser.parse_args()

    # Disable ANSI colors on request, when piped/redirected, or per NO_COLOR
    # (https://no-color.org), so escape codes don't leak to files/non-TTYs.
    USE_COLOR = not (args.no_color or os.environ.get('NO_COLOR') is not None or not sys.stdout.isatty())
    if not USE_COLOR:
        MAIN = LOGO = LOGO2 = GREEN = ORANGE = PRPL = PRPL2 = RED = END = BOLD = ''

    if not args.quiet:
        banner()

    # Validate numbering options
    if args.numbering_limit and not args.append_numbering:
        exit_with_msg(parser, 'Option -nl must be used with -an.')
    if args.append_numbering is not None and args.append_numbering <= 0:
        exit_with_msg(parser, 'Numbering level must be > 0.')

    numbering_max = (args.numbering_limit + 1) if args.numbering_limit else 51

    years = parse_years(parser, args.years) if args.years else []
    paddings = load_paddings(parser, args)

    # The --realistic preset is shorthand for realistic case + realistic leet.
    case_mode = 'realistic' if args.realistic else args.case_mode
    leet_mode = 'realistic' if args.realistic else args.leet_mode

    require = set()
    if args.require:
        for cls in args.require.split(','):
            cls = cls.strip().lower()
            if cls == '':
                continue
            if cls not in COMPLEXITY_CLASSES:
                exit_with_msg(parser, f'Unknown character class "{cls}" for --require. '
                                      f'Choose from: {", ".join(COMPLEXITY_CLASSES)}.')
            require.add(cls)

    keywords = build_keywords(args)
    if keywords is None:
        exit_with_msg(parser, 'Unable to mutate digit-only keywords.')

    cfg = Config(
        minlen=args.minlen,
        maxlen=args.maxlen,
        numbering_level=args.append_numbering,
        numbering_max=numbering_max,
        years=years,
        paddings=paddings,
        pad_after=args.common_paddings_after or args.custom_paddings_only,
        pad_before=args.common_paddings_before,
        case_mode=case_mode,
        leet_mode=leet_mode,
        require=require,
    )

    outfile = args.output if args.output else 'output.txt'
    lowered = [kw.lower() for kw in keywords]

    # Count pass: derive the exact word count and byte size from the very same
    # generator that will write the file, so the two can never drift apart.
    print(f'[{MAIN}Info{END}] Calculating output length and size...')
    total_words = 0
    total_bytes = 0
    for kw in lowered:
        for word in generate_keyword(kw, cfg):
            total_words += 1
            total_bytes += len(word) + 1

    prompt = (f'[{ORANGE}Warning{END}] This operation will produce {BOLD}{total_words}{END} words, '
              f'{BOLD}{human_size(total_bytes)}{END}'
              f'{" (before deduplication)" if args.unique else ""}. '
              f'Are you sure you want to proceed? [y/n]: ')

    try:
        consent = input(prompt)
    except KeyboardInterrupt:
        sys.exit('\n')

    if consent.lower() not in ['y', 'yes']:
        sys.exit(f'\n[{RED}X{END}] Aborting.')

    # Write pass.
    with open(outfile, 'w') as wordlist, \
         tqdm(total=total_words, desc=' ├─ Writing mutations', leave=False) as pbar:
        for word, kw in zip(keywords, lowered):
            print(f'[{GREEN}*{END}] Mutating keyword: {GREEN}{word}{END}')
            for mutation in generate_keyword(kw, cfg):
                wordlist.write(mutation + '\n')
                pbar.update(1)

    if args.unique:
        kept, removed = deduplicate_file(outfile)
        print(f'[{MAIN}Info{END}] Removed {removed} duplicate(s); {kept} unique words remain.')

    print(f'\n[{MAIN}Info{END}] Completed! List saved in {outfile}\n')


if __name__ == '__main__':
    main()
