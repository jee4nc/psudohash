# psudohash
[![Python 3.x](https://img.shields.io/badge/python-3.x-yellow.svg)](https://www.python.org/) [![License](https://img.shields.io/badge/license-MIT-red.svg)](https://github.com/t3l3machus/psudohash/blob/main/LICENSE) 
<img src="https://img.shields.io/badge/Maintained%3F-Yes-23a82c">
<img src="https://img.shields.io/badge/Developed%20on-kali%20linux-blueviolet">  

## Cool New Features of v1.1.0
Special thanks to [DavidAngelos](https://github.com/DavidAngelos):  
▶️ Added a progress bar in every step to track execution.  
▶️ Added options:
- **In-order joins** (`-i` / `--inorder`): join keywords only in the original order (e.g. `foo,bar,baz` → `foo, bar, baz, foobar, foobaz, barbaz, foobarbaz`).
- **All-order combinations** (`-c` / `--combinations`): generate every ordering of each subset (e.g. `foo,bar,baz` → `foo, bar, baz, foobar, foobaz, barfoo, …, bazbarfoo`).
- **Custom separator** (`--sep <string>`): when joining words, insert this string between tokens (defaults to no separator).
- **Max combine size** (`--max-combine <N>`): limit how many raw keywords get joined together (default: 2).
- **Min/Max length filtering of final words** (`--minlen/--maxlen <N>`): filter the final wordlist only with word with the desired length.

## Purpose
Psudohash is a password list generator for orchestrating brute force attacks and cracking hashes. It imitates certain password creation patterns commonly used by humans, like substituting a word's letters with symbols or numbers (leet), using char-case variations, adding a common padding before or after the main passphrase and more. It is keyword-based and highly customizable. 🎥 -> [Video Presentation](https://www.youtube.com/watch?v=oj3zjApOOGc)

## Pentesting Corporate Environments
System administrators and other employees often use a mutated version of the Company's name to set passwords (e.g. Am@z0n_2022). This is commonly the case for network devices (Wi-Fi access points, switches, routers, etc), application or even domain accounts. With the most basic options, psudohash can generate a wordlist with all possible mutations of one or multiple keywords, based on common character substitution patterns (customizable), case variations, strings commonly used as padding and more. Take a look at the following example:  

![image](https://github.com/t3l3machus/psudohash/assets/75489922/4a25ef08-8b21-4798-8b1a-97bdbd2dc2e3)


## Customization
### Leet Character Substitution
The script implements the following character substitution schema. You can add/modify character substitution mappings by editing the `TRANSFORMATIONS` list in `psudohash.py` and following the data structure presented below (default):
```
TRANSFORMATIONS = [
	{'a' : ['@', '4']},
	{'b' : '8'},
	{'e' : '3'},
	{'g' : ['9', '6']},
	{'i' : ['1', '!']},
	{'o' : '0'},
	{'s' : ['$', '5']},
	{'t' : '7'}
]
```  
### Common Padding Values
When setting passwords, I believe it's pretty standard to add a sequence of characters before and/or after the main passphrase to make it "stronger". For example, one may set a password "dragon" and add a value like "!!!" or "!@#" at the end, resulting in "dragon!!!", "dragon!@#", etc. Psudohash reads such values from `common_padding_values.txt` and uses them to mutate the provided keywords by appending them before (`-cpb`) or after (`-cpa`) each generated keyword variation. You can modify it as you see fit.

### Year Values
When appending a year value to a mutated keyword, psudohash will do so by utilizing various separators. By default, it will use the following separators which you can modify by editing the `YEAR_SEPARATORS` list:  
```
YEAR_SEPARATORS = ['', '_', '-', '@']
```
For example, if the given keyword is "amazon" and option `-y 2023` was used, the output will include "amazon2023", "amazon_2023", "amazon-2023", "amazon@2023", "amazon23", "amazon_23", "amazon-23", "amazon@23".

### Season & Month Tokens
A very common corporate pattern, driven by password‐expiry policies, is `Season + Year` or `Month + Year` (e.g. `Spring2024`, `Jan2025`). With `--seasons` and/or `--months`, psudohash appends these tokens to each mutation, reusing the years given with `-y` and joining them with the same `YEAR_SEPARATORS`. Both the full year and the 2‐digit year are produced (`Spring2024`, `Spring24`), and `--months` also includes 3‐letter abbreviations (`January2024`, `Jan2024`).

Names are available in English and Spanish, selected with `--lang` (default `en`):
```
SEASONS = {
    'en': ['Spring', 'Summer', 'Fall', 'Autumn', 'Winter'],
    'es': ['Primavera', 'Verano', 'Otoño', 'Otono', 'Invierno'],
}
```
The Spanish set ships both the accented form (`Otoño`) and an ASCII fallback (`Otono`), since targets type either. Edit the `SEASONS`, `MONTHS` and `MONTH_ABBR` dictionaries in `psudohash.py` to taste.

## Installation
This fork uses [uv](https://docs.astral.sh/uv/) for dependency management.
```bash
git clone https://github.com/jee4nc/psudohash.git
cd ./psudohash
uv sync
```
Then run it with:
```bash
uv run python psudohash.py -w example -cpa
```

<details>
<summary>Without uv (plain pip)</summary>

```bash
pip3 install tqdm
chmod +x psudohash.py
./psudohash.py -w example -cpa
```
</details>

### Running the tests
```bash
uv run pytest
```

## Usage
```
./psudohash.py [-h] -w WORDS [-i] [-c] [--sep SEP] [--max-combine N] [--minlen N] [--maxlen N] [--case-mode {all,realistic}] [--leet-mode {all,realistic,none}] [--require CLASSES] [-R] [-an LEVEL] [-nl LIMIT] [-y YEARS] [-d YEARS] [--date-formats FORMATS] [--seasons] [--months] [--lang LANGS] [--reverse] [-ap VALUES] [-cpb] [-cpa] [-cpo] [-o FILENAME] [-q] [--yes] [--no-color] [-u]
```
The help dialog [ -h, --help ] includes usage details and examples.

## Options

- **`-w, --words <kw1,kw2,…>`**  
  Comma‐separated raw keywords (required).

- **`-i, --inorder`**  
  Join up to `--max-combine` keywords in the given order (e.g. `foo,bar,baz` → `foo, bar, baz, foobar, foobaz, barbaz, foobarbaz`).

- **`-c, --combinations`**  
  Generate every permutation of each subset (up to `--max-combine`) (e.g. `foo,bar,baz` → `foo, bar, baz, foobar, foobaz, barfoo, …`).

- **`--max-combine <N>`** (default: 2)  
  Maximum number of raw keywords to join into one base string.

- **`--sep <string>`**  
  When joining words (`-i` or `-c`), place this string between tokens. Defaults to an empty string.

- **`--minlen <N>`**  
  Discard any final password shorter than N characters.

- **`--maxlen <N>`**  
  Discard any final password longer than N characters.

- **`--case-mode {all,realistic}`** (default: `all`)  
  Case variation strategy. `all` produces every upper/lower combination (e.g. `aMaZoN`); `realistic` produces only the forms humans actually use: all-lower, ALL-UPPER, Capitalized and Title Case.

- **`--leet-mode {all,realistic,none}`** (default: `all`)  
  Leet substitution strategy. `all` is every per-character keep/substitute combination; `realistic` is consistent (each letter is left alone or replaced in *all* its occurrences); `none` disables leet.

- **`--require <classes>`**  
  Keep only passwords containing at least one of each comma-separated character class: `lower,upper,digit,special`. Useful to match a target's password policy and avoid wasting guesses (e.g. `--require upper,digit,special`).

- **`-R, --realistic`**  
  Preset enabling human-like mutations (`--case-mode realistic` **and** `--leet-mode realistic`). Produces a far smaller, higher-signal wordlist. For `amazon` this drops the base mutations from 384 to 14.

- **`-an, --append-numbering <LEVEL>`**  
  Append numbered suffixes (zero‐padded to `<LEVEL>` digits) to each word mutation.

- **`-nl, --numbering-limit <LIMIT>`**  
  Maximum number to count up to when appending numbers (default: 50).

- **`-y, --years <years>`**  
  Append one or more years to each mutation (e.g. `1990-2000`, or `2022,2023`).

- **`-d, --dates <years>`**  
  Append common date patterns (birthdays, etc.) for a year, comma list or range of years (e.g. `1998` or `1990-2000`). Each pattern is joined to the keyword with the same separators as `-y`, so `pedro` + `01/1998` produces `pedro011998`, `pedro_011998`, … Impossible dates (e.g. `31/02`) are skipped. The set of formats is controlled by `--date-formats`.

- **`--date-formats <formats>`** (default: `ddmmyyyy,ddmmyy,mmyyyy,ddmm,yyyy,yy`)  
  Comma‐separated date formats for `-d`. Available tokens: `ddmmyyyy, ddmmyy, mmddyyyy, mmddyy, yyyymmdd, mmyyyy, mmyy, ddmm, mmdd, yyyy, yy`.

- **`--seasons`**  
  Append season+year tokens to each mutation (e.g. `amazonSpring2024`), the common password‐expiry pattern. Requires `-y` for the year(s); both full and 2‐digit years are produced.

- **`--months`**  
  Append month+year tokens, full and abbreviated (e.g. `amazonJanuary2024`, `amazonJan2024`). Requires `-y`.

- **`--lang <langs>`** (default: `en`)  
  Comma‐separated languages for `--seasons`/`--months`. Available: `en, es` (e.g. `--lang en,es`).

- **`--reverse`**  
  Also mutate the reverse of each keyword (e.g. `amazon` → `nozama`); the reversed form receives the full set of mutations.

- **`-ap, --append-padding <vals>`**  
  Append custom padding values (comma‐separated). Must be used with `-cpb` or `-cpa`.

- **`-cpb, --common-paddings-before`**  
  Prepend values from `common_padding_values.txt` before each mutation.

- **`-cpa, --common-paddings-after`**  
  Append values from `common_padding_values.txt` after each mutation.

- **`-cpo, --custom-paddings-only`**  
  Use only user‐provided paddings (no defaults). Must be used with `-ap`.

- **`-o, --output <file>`**  
  Write the results to `<file>` (default: `output.txt`). If the file already exists, psudohash warns before overwriting it.

- **`-q, --quiet`**  
  Suppress the ASCII art banner on startup.

- **`--yes`**  
  Skip the confirmation prompt (assume yes). Useful for scripts and non‐interactive runs.

- **`--no-color`**  
  Disable colored output. Colors are also auto-disabled when stdout is not a TTY (e.g. piped/redirected) or when the `NO_COLOR` environment variable is set.

- **`-u, --unique`**  
  Remove duplicate lines from the final wordlist (order-preserving). Deduplication runs inline while writing, so the file is produced in a single pass.


### Usage Examples

1. **No multi‐word (singletons only)**  
   ```bash
   ./psudohash.py -w foo,bar,baz -cpa
   # → foo, bar, baz
   ```

2. **In‐order joins (-i, up to 2 words by default)**  
   ```bash
   ./psudohash.py -w foo,bar,baz -i
   # → foo, bar, baz, foobar, foobaz, barbaz
   ```

3. **All‐order combinations (-c, up to 2 words by default)**  
   ```bash
   ./psudohash.py -w foo,bar,baz -c
   # → foo, bar, baz, foobar, foobaz, barfoo, barbaz, bazfoo, bazbar
   ```

4. **Change separator between joined words**  
   ```bash
   ./psudohash.py -w foo,bar,baz -i --sep "_"
   # → foo, bar, baz, foo_bar, foo_baz, bar_baz
   ```

5. **Length Filtering (`--minlen`/`--maxlen`)**  
   ```bash
	./psudohash.py -w apple,banana -i --minlen 10
	# Example final outputs might include “applebanana” (11 chars), “bananaapple” (11 chars).
   ```

6. **Combine up to 3 words (instead of default 2)**  
   ```bash
   ./psudohash.py -w foo,bar,baz -i --max-combine 3
   # → foo, bar, baz, foobar, foobaz, barbaz, foobarbaz
   ```

7. **Deduplicated output**  
   ```bash
   ./psudohash.py -w amazon -y 2022 -an 1 --unique
   # Removes any duplicate mutations from output.txt
   ```

8. **Realistic, human-like mutations (smaller, higher-signal list)**  
   ```bash
   ./psudohash.py -w amazon --realistic
   # → amazon, Amazon, AMAZON, @m@zon, amaz0n, 4m4z0n, ...  (14 vs 384)
   ```

9. **Match a target password policy**  
   ```bash
   ./psudohash.py -w amazon -R -y 2024 --require upper,digit --minlen 8
   # Only candidates with an uppercase letter AND a digit, length >= 8
   ```

10. **Birthday / date patterns (e.g. `pedro011998`)**  
    ```bash
    ./psudohash.py -w pedro -d 1998 -R
    # → pedro011998, pedro01011998, pedro0101, pedro1998, ... for every plausible date
    # Narrow the formats if you know the shape:
    ./psudohash.py -w pedro -d 1998 --date-formats mmyyyy -R
    # → pedro011998, pedro021998, ... pedro121998
    ```

11. **Season / month + year (password‐expiry pattern)**  
    ```bash
    ./psudohash.py -w amazon --seasons -y 2024 -R
    # → amazonSpring2024, amazon_Spring2024, amazonWinter24, ...
    # English + Spanish names, with months too:
    ./psudohash.py -w amazon --seasons --months -y 2024 --lang en,es -R
    # → ...amazonPrimavera2024, amazonEnero2024, amazonEne2024, ...
    ```

12. **Reverse the keyword**  
    ```bash
    ./psudohash.py -w amazon --reverse -R
    # mutates both "amazon" and "nozama"
    ```

13. **Non‐interactive run (skip the prompt)**  
    ```bash
    ./psudohash.py -w amazon -R --yes -o creds.txt
    # generates without asking for confirmation
    ```

## Usage Tips
1. Combining options `--years` and `--append-numbering` with a `--numbering-limit` ≥ last two digits of any year input, will most likely produce duplicate words because of the mutation patterns implemented by the tool. 
2. If you add custom padding values and/or modify the predefined common padding values in the source code, in combination with multiple optional parameters, there is a small chance of duplicate words occurring. Use `-u`/`--unique` to remove any duplicates from the final wordlist.
3. The reported word count and size are exact, even when `--minlen`/`--maxlen` filtering is active, because they are derived from the same generator that writes the file (counted with a no-write pass first).

## Individuals
When it comes to people, i think we all have (more or less) set passwords using a mutation of one or more words that mean something to us e.g., our name or wife/kid/pet/band names, sticking the year we were born at the end or maybe a super secure padding like "!@#". Well, guess what?

![usage_example_png](https://raw.github.com/t3l3machus/psudohash/master/Screenshots/multiple-words.png)


## Future 
I'm gathering information regarding commonly used password creation patterns to enhance the tool's capabilities.
