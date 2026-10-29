#!/usr/bin/env python3
"""Mechanical linter for the simple-language rules in English, Russian, Spanish and Estonian.

Finds candidates, never decides: ambiguous references, genitive chains, word order and meaning stay with the writer.
It never flags a hedge or a modal word, because the skill treats confidence as content.

Usage:
    simple_lint.py FILE [FILE ...]
    echo "text" | simple_lint.py --lang ru --json
    simple_lint.py --baseline 5 --disable passive FILE
    simple_lint.py --selftest

Exit 0 when hard findings do not exceed --baseline (default 0), 1 when they do, 2 on a usage error. Advisory findings
never fail the run.
"""
import argparse
import bisect
import json
import re
import sys

sys.dont_write_bytecode = True

LANGS = ("en", "ru", "es", "et")
HARD = "hard"
ADVISORY = "advisory"
MIN_WORDS_TO_DETECT = 6
CYRILLIC_SHARE_FOR_RU = 0.3

SENTENCE_CAP = {"en": 25, "ru": 22, "es": 25, "et": 20}

STOPWORDS = {
    "en": {"the", "and", "of", "to", "is", "that", "it", "for", "with", "this", "are", "be", "not", "if", "you"},
    "es": {"el", "la", "de", "que", "y", "los", "las", "en", "se", "por", "un", "una", "es", "para", "con", "del",
           "si", "no"},
    "et": {"ja", "ei", "see", "kui", "mis", "ning", "või", "ka", "et", "siis", "seda", "selle", "ole", "olla",
           "peab", "pärast", "enne"},
}
LETTER_HINTS = {"es": "ñ¿¡áéíóú", "et": "õäöü"}

WORD_FLAGS = re.I | re.U


def _rx(pattern):
    return re.compile(pattern, WORD_FLAGS)


NOMINALIZATION = {
    "en": _rx(r"\b(?:perform(?:s|ed|ing)?|conduct(?:s|ed|ing)?|carr(?:y|ies|ied|ying)\s+out)\s+(?:a|an|the)\s+"
              r"\w+(?:tion|sion|ment|ance|ence|ysis)\b"),
    "ru": _rx(r"\b(?:осуществ|производ|произвед|произвест|провод|провед|провест|выполн|обеспеч)"
              r"(?!\w*(?:ост|ств|ник|тел))(?!\w*(?:ни[еяюи]|нием)\b)\w*\s+(?:\w+\s+)?"
              r"\w+(?:ние|ния|нию|нием|нии|ция|цию|ции|цией|ка|ку|ки|кой)\b"),
    "es": _rx(r"\b(?:realiz\w*|realic\w*|efectu\w*|efectú\w*|llev\w*\s+a\s+cabo|proced\w*\s+a)\s+"
              r"(?:(?:la|el|una|un|los|las)\s+)?\w+(?:ción|ciones|sión|siones|miento|mientos)\b"),
    "et": _rx(r"\b(?:teosta\w*|toimu\w*|soorita\w*|vii\w*\s+läbi|läbi\s*vii\w*)\s+(?:\w+\s+)?"
              r"\w+(?:mine|mise|misi|mist|misel|misega|miseks)\b"
              r"|\b\w+(?:mine|mise)\s+(?:toimu\w*|teostatakse|viiakse\s+läbi)\b"),
}

OFFICIALESE = {
    "en": _rx(r"\b(?:in\s+order\s+to|utiliz\w*|utilis\w*|leverag(?:e|es|ed|ing)|at\s+this\s+point\s+in\s+time|"
              r"due\s+to\s+the\s+fact\s+that|in\s+the\s+event\s+that|it\s+is\s+important\s+to\s+note|prior\s+to|"
              r"facilitat\w*)\b"),
    "ru": _rx(r"\b(?:данн(?:ый|ая|ое|ого|ой|ому|ую|ом)|явля(?:ется|ются|лся|лась|лось|лись)|в\s+целях|с\s+целью|"
              r"в\s+рамках|в\s+случае,?\s+если|в\s+связи\s+с\s+тем,?\s+что|на\s+сегодняшний\s+день|"
              r"вышеуказанн\w*|нижеследующ\w*|име(?:ет|ло|ют|ли)\s+место|следует\s+отметить)\b"),
    "es": _rx(r"\b(?:a\s+nivel\s+de|de\s+cara\s+a|con\s+el\s+fin\s+de|a\s+fin\s+de|en\s+el\s+caso\s+de\s+que|"
              r"debido\s+al\s+hecho\s+de\s+que|en\s+la\s+actualidad|cabe\s+destacar|procedemos\s+a|en\s+base\s+a)\b"
              r"|\b(?:el|la|los|las)\s+mism[oa]s?\b(?=\s*(?:[.,;:)]|$))"),
    "et": _rx(r"(?<!\bon )(?<!\boli )(?<!\bolid )(?<!\bsai )\bantud\b|\bpoolt\b|\beesmärgiga\b|\bjuhul,?\s+kui\b|"
              r"\btulenevalt\s+asjaolust\b|\bhetkel\b|\btuleb\s+märkida\b|\bom(?:ab|avad|ama)\b"),
}

MARKETING = {
    "en": _rx(r"\b(?:seamless(?:ly)?|robust(?:ly)?|powerful|cutting-edge|effortless(?:ly)?|blazing[- ]fast|"
              r"world-class|state-of-the-art|game-chang(?:ing|er))\b"),
    "ru": _rx(r"\b(?:бесшовн\w*|мощн\w*|передов\w*|инновационн\w*|уникальн\w*|революционн\w*)\b"),
    "es": _rx(r"\b(?:potentes?|robust[oa]s?|innovador\w*|revolucionari[oa]s?|de\s+vanguardia|sin\s+fisuras)\b"),
    "et": _rx(r"\b(?:võimsa?\w*|uuenduslik\w*|innovaatilis?\w*|revolutsiooniline\w*|tipptasemel|sujuva?\w*)\b"),
}

PHRASAL_VERB = {
    "en": _rx(r"\b(?:spin(?:s|ning)?\s+up|spun\s+up|reach(?:es|ed|ing)?\s+out|div(?:e|es|ed|ing)\s+into|dove\s+into|"
              r"kick(?:s|ed|ing)?\s+off|circl(?:e|es|ed|ing)\s+back|touch(?:es|ed|ing)?\s+base|"
              r"look(?:s|ed|ing)?\s+into)\b"),
}

EN_PARTICIPLES = ("given|taken|made|done|found|seen|known|shown|written|built|sent|set|run|read|kept|held|left|put|"
                  "begun|gone|lost|paid|said|told|brought|chosen|broken|frozen|hidden|forgotten|understood")

PASSIVE = {
    "en": _rx(r"\b(?:is|are|was|were|been|being)\s+(?:\w+ed|" + EN_PARTICIPLES + r")\b(?!\s+(?:to|for|by)\s+\w+ing)"),
    "ru": _rx(r"\b(?:был|была|было|были|будет|будут)\s+\w+(?:ан|ян|ен|ён|ыт|ит|ут|ат)(?:а|о|ы)?\b"),
    "es": _rx(r"\b(?:es|son|fue|fueron|será|serán|sido|ser|era|eran)\s+(?!(?:nada|cada|vida|salida|entrada)\b)"
              r"\w+(?:ado|ada|ados|adas|ido|ida|idos|idas)\b"),
}

PRESENT_PERFECT = {
    "en": _rx(r"(?<!\bmay )(?<!\bmight )(?<!\bcould )(?<!\bshould )(?<!\bwould )(?<!\bmust )\b(?:has|have|had)\s+"
              r"(?:been\s+)?(?:\w+ed|" + EN_PARTICIPLES + r")\b"),
}

SYNONYM_GROUPS = {
    "en": [("check", "verify", "confirm", "validate"), ("delete", "remove", "erase"),
           ("start", "launch", "initiate"), ("stop", "halt", "terminate"), ("use", "utilize", "employ"),
           ("get", "retrieve", "fetch", "obtain"), ("change", "modify", "alter"), ("user", "customer", "client")],
    "ru": [("провер", "убед", "удостовер"), ("удал", "стер"), ("запуст", "запуск", "стартова"),
           ("пользовател", "клиент", "абонент"), ("получ", "извлеч", "извлек"), ("измен", "модифицир")],
    "es": [("verific", "comprob", "comprueb", "confirm", "valid"), ("elimin", "borr", "quit", "suprim"),
           ("usuari", "client"), ("obten", "obtien", "recuper"), ("cambi", "modific")],
    "et": [("kontroll", "veendu", "kinnita"), ("kustut", "eemalda"), ("kasutaja", "klient"),
           ("muut", "modifitseeri")],
}

SYNONYM_ALIASES = {("es", "comprueb"): "comprob", ("es", "obtien"): "obten", ("ru", "запуск"): "запуст",
                   ("ru", "извлек"): "извлеч"}

MESSAGES = {
    "semicolon": "Semicolon. Write separate sentences.",
    "long-sentence": "Sentence has {n} words (cap {cap} for {lang}). Split it.",
    "nominalization": "Action frozen into a noun with an empty verb. Use the verb.",
    "officialese": "Officialese or filler. Use the plain form from the language profile, or delete.",
    "marketing": "Claim without a measurement. Delete it, or replace it with the measurement.",
    "phrasal-verb": "Phrasal verb. Use the single plain verb.",
    "passive": "Possible passive. Name the actor, unless it is unknown or irrelevant.",
    "present-perfect": "Compound tense. Use the simple form, unless current relevance is the point.",
    "synonym-rotation": "'{word}' and '{other}' (line {line}) may name the same thing. Pick one term.",
}

RULE_LEVELS = {"semicolon": HARD, "long-sentence": HARD, "nominalization": HARD, "officialese": HARD,
               "marketing": HARD, "phrasal-verb": HARD, "passive": ADVISORY, "present-perfect": ADVISORY,
               "synonym-rotation": ADVISORY}

PATTERN_RULES = (("nominalization", NOMINALIZATION), ("officialese", OFFICIALESE), ("marketing", MARKETING),
                 ("phrasal-verb", PHRASAL_VERB), ("passive", PASSIVE), ("present-perfect", PRESENT_PERFECT))

CODE_FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`\n]+`")
LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
LIST_ITEM = re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+)")
BLOCKQUOTE = re.compile(r"^(\s*(?:>\s?)+)")
STANDALONE = re.compile(r"^\s*(?:#|<|\||(?:[-*_=]\s*){3,}$)")
WORD = re.compile(r"\w", re.U)
SENTENCE_END = re.compile(r"[.!?…][\"'”’»)\]*_]*$")
SENTENCE_OPENER = re.compile(r"^[\"'“‘«(\[*_¿¡]*[\w]")
ABBREVIATIONS = {"e.g.", "i.e.", "vs.", "cf.", "etc.", "no.", "fig.", "nt.", "vt.", "jne.", "jt.", "sr.", "sra.",
                 "dr.", "pág.", "т.", "см.", "г.", "др.", "т.е.", "т.д.", "т.п."}

SELFTEST_CASES = [
    ("en", "The request may have failed.", set()),
    ("ru", "Возможно, запрос не прошёл.", set()),
    ("es", "Puede que la solicitud haya fallado.", set()),
    ("et", "Päring võis ebaõnnestuda.", set()),
    ("en", "Open the file; read line 3.", {"semicolon"}),
    ("en", "Perform an analysis of the log.", {"nominalization"}),
    ("en", "Spin up the worker in order to start.", {"phrasal-verb", "officialese"}),
    ("en", "We have received the report.", {"present-perfect"}),
    ("en", "The file is deleted after upload.", {"passive"}),
    ("en", "This seamless tool is fast.", {"marketing"}),
    ("ru", "Необходимо осуществить проверку конфига.", {"nominalization"}),
    ("ru", "Данный модуль является частью сервиса.", {"officialese"}),
    ("ru", "Дождитесь завершения выполнения задачи сборки.", set()),
    ("ru", "Данные сохраняются в базе.", set()),
    ("ru", "Файл был удалён сервисом.", {"passive"}),
    ("ru", "Это бесшовная интеграция.", {"marketing"}),
    ("es", "Realice la verificación de la configuración.", {"nominalization"}),
    ("es", "Revise los datos a nivel de red.", {"officialese"}),
    ("es", "Revise el archivo y guarde el mismo.", {"officialese"}),
    ("es", "Use el mismo archivo.", set()),
    ("es", "El archivo fue eliminado por el servicio.", {"passive"}),
    ("et", "Teostage konfiguratsiooni kontrollimine.", {"nominalization"}),
    ("et", "Fail kustutati teenuse poolt.", {"officialese"}),
    ("et", "Antud fail on vigane.", {"officialese"}),
    ("et", "Luba on antud kasutajale.", set()),
    ("en", "Use `a; b` in the shell.", set()),
]


def _mask(text):
    text = INLINE_CODE.sub(lambda m: "CODE" + " " * (len(m.group(0)) - 4) if len(m.group(0)) >= 4 else "CODE", text)
    return LINK.sub(lambda m: m.group(1) + " " * (len(m.group(0)) - len(m.group(1))), text)


def _blocks(text):
    """Split Markdown into prose blocks: lists of (line number, column, text) pieces, one block per paragraph."""
    blocks, current, in_fence, in_front_matter = [], [], False, False
    lines = text.splitlines()
    for lineno, raw in enumerate(lines, 1):
        if lineno == 1 and raw.strip() == "---":
            in_front_matter = True
            continue
        if in_front_matter:
            in_front_matter = raw.strip() != "---"
            continue
        if CODE_FENCE.match(raw):
            in_fence = not in_fence
            if current:
                blocks.append(current)
                current = []
            continue
        if in_fence:
            continue
        line, column = raw, 0
        quote = BLOCKQUOTE.match(line)
        if quote:
            column = len(quote.group(1))
            line = line[column:]
        if not line.strip() or STANDALONE.match(line):
            if current:
                blocks.append(current)
                current = []
            continue
        item = LIST_ITEM.match(line)
        if item:
            if current:
                blocks.append(current)
                current = []
            column += len(item.group(1))
            line = line[len(item.group(1)):]
        current.append((lineno, column, _mask(line)))
    if current:
        blocks.append(current)
    return blocks


def _words(text):
    return [w for w in text.split() if WORD.search(w)]


def detect_language(text, fallback="en"):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return fallback
    cyrillic = sum(1 for c in letters if "Ѐ" <= c <= "ӿ")
    if cyrillic / len(letters) > CYRILLIC_SHARE_FOR_RU:
        return "ru"
    tokens = [w.strip(".,;:!?¿¡()\"'«»").lower() for w in text.split()]
    scores = {lang: sum(1 for t in tokens if t in words) for lang, words in STOPWORDS.items()}
    lowered = text.lower()
    for lang, hints in LETTER_HINTS.items():
        scores[lang] += sum(lowered.count(c) for c in hints)
    scores["et"] += 2 * lowered.count("õ")
    best = max(scores, key=scores.get)
    return best if scores[best] else fallback


def _sentences(joined):
    tokens = list(re.finditer(r"\S+", joined))
    if not tokens:
        return []
    starts = [tokens[0].start()]
    for token, following in zip(tokens, tokens[1:]):
        word = token.group()
        if not SENTENCE_END.search(word) or word.lower().lstrip("(\"'«") in ABBREVIATIONS:
            continue
        nxt = following.group()
        if SENTENCE_OPENER.match(nxt) and (nxt.lstrip("\"'“‘«([*_¿¡")[:1].isupper()
                                           or nxt.lstrip("\"'“‘«([*_¿¡")[:1].isdigit()):
            starts.append(following.start())
    return list(zip(starts, starts[1:] + [len(joined)]))


def _locate(pieces, offsets, position):
    index = bisect.bisect_right(offsets, position) - 1
    lineno, column, _ = pieces[index]
    return lineno, column + position - offsets[index] + 1


def _finding(filename, line, col, rule, lang, match, message):
    return {"file": filename, "line": line, "col": col, "rule": rule, "level": RULE_LEVELS[rule], "lang": lang,
            "match": match, "message": message}


def lint_text(text, filename="<stdin>", lang=None, disabled=frozenset()):
    blocks = _blocks(text)
    file_lang = lang or detect_language(" ".join(p[2] for b in blocks for p in b))
    findings, seen_synonyms = [], {}
    for pieces in blocks:
        offsets, position = [], 0
        for _, _, piece in pieces:
            offsets.append(position)
            position += len(piece) + 1
        joined = " ".join(piece for _, _, piece in pieces)
        block_lang = lang or (detect_language(joined, file_lang) if len(_words(joined)) >= MIN_WORDS_TO_DETECT
                              else file_lang)
        where = lambda pos: _locate(pieces, offsets, pos)

        for match in re.finditer(";", joined):
            findings.append(_finding(filename, *where(match.start()), "semicolon", block_lang, ";",
                                     MESSAGES["semicolon"]))
        cap = SENTENCE_CAP[block_lang]
        for start, end in _sentences(joined):
            count = len(_words(joined[start:end]))
            if count > cap:
                findings.append(_finding(filename, *where(start), "long-sentence", block_lang, f"{count} words",
                                         MESSAGES["long-sentence"].format(n=count, cap=cap, lang=block_lang)))
        for rule, patterns in PATTERN_RULES:
            pattern = patterns.get(block_lang)
            if pattern is None:
                continue
            for match in pattern.finditer(joined):
                findings.append(_finding(filename, *where(match.start()), rule, block_lang, match.group(0),
                                         MESSAGES[rule]))
        for group in SYNONYM_GROUPS[block_lang]:
            key = (block_lang, group)
            stems = "|".join(sorted(group, key=len, reverse=True))
            for match in re.finditer(r"\b(?:" + stems + r")\w*", joined, WORD_FLAGS):
                word = match.group(0)
                stem = next(s for s in sorted(group, key=len, reverse=True) if word.lower().startswith(s))
                stem = SYNONYM_ALIASES.get((block_lang, stem), stem)
                first = seen_synonyms.setdefault(key, {})
                line, col = where(match.start())
                if stem in first:
                    continue
                if first:
                    other_word, other_line = next(iter(first.values()))
                    findings.append(_finding(filename, line, col, "synonym-rotation", block_lang, word,
                                             MESSAGES["synonym-rotation"].format(word=word, other=other_word,
                                                                                 line=other_line)))
                first[stem] = (word, line)
    findings = [f for f in findings if f["rule"] not in disabled]
    return sorted(findings, key=lambda f: (f["file"], f["line"], f["col"], f["rule"]))


def _selftest():
    failures = 0
    for lang, text, expected in SELFTEST_CASES:
        got = {f["rule"] for f in lint_text(text, lang=lang)}
        if got != expected:
            failures += 1
            print(f"FAIL [{lang}] {text!r}: expected {sorted(expected)}, got {sorted(got)}")
    for text, expected in [("The service deletes the file after the upload ends.", "en"),
                           ("Сервис удаляет файл после загрузки.", "ru"),
                           ("El servicio elimina el archivo después de la carga.", "es"),
                           ("Teenus kustutab faili pärast üleslaadimist ja logib selle.", "et")]:
        got = detect_language(text)
        if got != expected:
            failures += 1
            print(f"FAIL detect {text!r}: expected {expected}, got {got}")
    long_ru = " ".join(["слово"] * 23) + "."
    if {f["rule"] for f in lint_text(long_ru, lang="ru")} != {"long-sentence"}:
        failures += 1
        print("FAIL long sentence in ru")
    rotation = lint_text("Check the token.\n\nThen verify the file.", lang="en")
    if [f["rule"] for f in rotation] != ["synonym-rotation"] or rotation[0]["line"] != 3:
        failures += 1
        print(f"FAIL synonym rotation: {rotation}")
    fenced = lint_text("```\nrm a; rm b\n```\n", lang="en")
    if fenced:
        failures += 1
        print(f"FAIL fenced code: {fenced}")
    print("selftest: ok" if not failures else f"selftest: {failures} failed")
    return 1 if failures else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", help="files to lint; stdin when none")
    parser.add_argument("--lang", choices=LANGS, help="force the language instead of detecting it per paragraph")
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    parser.add_argument("--baseline", type=int, default=0, help="hard findings tolerated before exit 1")
    parser.add_argument("--disable", default="", help="comma-separated rules to silence")
    parser.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    args = parser.parse_args(argv)

    if args.selftest:
        return _selftest()
    disabled = {r.strip() for r in args.disable.split(",") if r.strip()}
    unknown = disabled - set(RULE_LEVELS)
    if unknown:
        parser.error(f"unknown rule(s): {', '.join(sorted(unknown))}. Known: {', '.join(RULE_LEVELS)}")
    if args.baseline < 0:
        parser.error("--baseline must be 0 or more")

    findings = []
    sources = args.files or ["-"]
    for name in sources:
        try:
            text = sys.stdin.read() if name == "-" else open(name, encoding="utf-8").read()
        except OSError as error:
            parser.error(f"cannot read {name}: {error.strerror}")
        findings += lint_text(text, "<stdin>" if name == "-" else name, args.lang, frozenset(disabled))

    hard = sum(1 for f in findings if f["level"] == HARD)
    if args.json:
        print(json.dumps({"findings": findings, "hard": hard, "advisory": len(findings) - hard,
                          "baseline": args.baseline}, ensure_ascii=False, indent=2))
    else:
        for f in findings:
            print(f"{f['file']}:{f['line']}:{f['col']}: {f['rule']} [{f['level']}, {f['lang']}] "
                  f"{f['match']!r} — {f['message']}")
        print(f"{hard} hard, {len(findings) - hard} advisory (baseline {args.baseline})")
    return 1 if hard > args.baseline else 0


if __name__ == "__main__":
    sys.exit(main())
