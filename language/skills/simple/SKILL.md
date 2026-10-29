---
name: simple
description: >
  Rewrite text in English, Russian, Spanish or Estonian so a reader cannot misread it: one action per sentence, short
  sentences, the actor named, one term for one thing, verbs instead of nominalizations, no officialese, and every
  hedge kept at its original strength. A language-independent take on ASD-STE100 (Simplified Technical English), with
  a trap profile per language. Use when text must be parsed without a human to resolve ambiguity — tool descriptions,
  error messages, inter-agent instructions, system prompts, status reports, procedures — or when text reads as dense,
  hedged, bureaucratic or easy to misparse. Triggers: simplify, disambiguate, plain language, STE / STE100 rewrite,
  controlled language, rewrite so an agent cannot misread this, упрости текст, убери канцелярит, простой язык,
  simplifica el texto, lenguaje claro, lihtsusta teksti, selge keel. Not for creative or marketing copy.
---

# Simple language

ASD-STE100 (Simplified Technical English) is the aerospace standard that stops maintenance technicians from misreading
English instructions. It removes the two biggest sources of misreading: words with more than one meaning, and
sentences with more than one possible structure.

This skill applies the same discipline to **any language** and to a different reader. That reader is an AI agent, a
downstream system, a translator or a non-native reader with no author to ask. The skill has two layers:

- **Universal rules** — sentence shape, actors, terms, modality. They hold in every language and are listed below.
- **Language profiles** — the traps of one language, with before/after examples: `references/languages/<code>.md`.

Supported languages: English (`en`), Russian (`ru`), Spanish (`es`), Estonian (`et`).

## When to use

- Text will be read by another agent, a translation pipeline or a non-native reader, and a wrong reading has a cost.
- A prompt, system message, tool description or error message must say exactly one thing.
- Text reads as dense, hedged, bureaucratic (канцелярит, kantseliit, lenguaje administrativo) or easy to misparse.
- The user wants a before/after table that names the broken rule. The default output is the rewritten text alone.

Not for creative, marketing or persuasive copy, where voice and nuance are the point.

## Language

1. Detect the language of the input. Write the result **in the same language. Never translate.**
2. Read the profile for that language in `references/languages/` before rewriting. It sets the sentence-length caps
   and lists the traps the universal rules do not catch.
3. Mixed text: apply the profile of the prose language. Russian prose with English terms gets the Russian profile.
   Leave code, identifiers, commands, paths, URLs, quotes and product names exactly as they are.
4. A language without a profile: apply the universal rules only. Add one line after the text:
   `No profile for <language>: universal rules only.` Do not invent language-specific rules you cannot back.

## Two modes

Pick the mode from the text type. Keep the choice internal unless the user asks for the rule table.

**Strict** — procedures, error messages, tool and function descriptions, inter-agent instructions, prompts, safety
text: anywhere a wrong reading has a cost. Apply every rule, including the length caps and one term per meaning.

**Flavored** — READMEs, PR descriptions, changelogs, explanatory prose. Apply the structural rules in full. Treat the
lexical rules as advisory: prose needs some range, and a strict rewrite of prose reads as a personality transplant.

## Universal rules

### Structural — apply in every language

- **One action per sentence.** Split "open the file and check line 3, then …" into one step each.
- **Sentence length.** Stay under the caps in the language profile: one cap for instructions, one for descriptions.
- **Actor named.** Say who acts. Use a passive or impersonal form only when the actor is unknown or irrelevant.
- **No semicolons.** Write separate sentences. Other punctuation is allowed.
- **Short noun chains.** At most 3 nouns stacked as one phrase. This covers every form a language stacks nouns in:
  English noun clusters, Russian and Estonian genitive chains, Spanish "de … de … de", Estonian compounds.
- **Clear references.** When "it", "он", "este" or "see" can point at two nouns, repeat the noun.
- **No ellipsis.** Keep the subject, the verb and the condition, even if the sentence gets longer.
- **Lists for sequences.** Use a numbered or bulleted list for 3 or more steps or conditions.
- **Paragraphs.** One topic per paragraph, at most 6 sentences.
- **Conditions first.** Put a condition or a warning before the action it limits: "If X, do Y", not "Do Y if X".
- **Explicit numbers.** Write numbers, units, ranges and limits in full: "from 1 to 10 inclusive", not "1–10ish".

### Lexical — enforce in Strict, advise in Flavored

- **One term, one meaning.** Pick one word for one thing or action and use it every time. Do not rotate synonyms
  ("user / customer / client", "пользователь / клиент / абонент", "usuario / cliente", "kasutaja / klient").
- **Verb, not noun.** Use the verb for an action: "check the log", not "perform a check of the log".
- **Plain words.** Prefer the common word over the formal or rare one. Remove officialese and filler.
- **No idioms or metaphors.** They do not survive translation, and a model reads them literally.
- **No marketing adjectives.** Delete seamless, robust, powerful or the measurement-free equivalent in the language,
  or replace it with the measurement that earns the claim.
- **One form of address.** Pick one form for instructions (imperative, infinitive, "you", "вы", "usted", "teie") and
  keep it through the document.
- **Domain terms.** Keep a necessary technical term. Define it once if a common reader does not know it.

### Modality — never change it

A hedge carries the author's confidence, and confidence is content. "May have failed" stays "may have failed",
"возможно, упал" stays "возможно, упал", "puede que haya fallado" and "võis ebaõnnestuda" stay as they are.

- Never turn a hedge into a fact or a fact into a hedge, even when a shorter sentence tempts you.
- Never add a cause, a frequency, a mechanism or a step the source did not state. If an added sentence makes the
  text better, it is new content: drop it, or list it on its own line as a suggestion.
- When a modal word has two readings (ability or possibility: "can", "может", "puede", "võib"), choose one reading
  only when the context decides it. Otherwise keep the word and flag it.
- When the tense or length rules conflict with modality, modality wins.

## Scan checklist

Scan the whole text for these before rewriting. Each one points at an exact word or mark.

1. **Synonym rotation** — one thing under several names.
2. **Hedge stacking** — qualifiers pile up until the sentence asserts nothing ("it is important to note that this may
   potentially help"). State the claim with its one real hedge, or delete it.
3. **Nominalization** — an action frozen into a noun with an empty verb ("perform an analysis", "осуществить
   проверку", "realizar la verificación", "teostada kontrolli").
4. **Officialese and filler** — bureaucratic words that add length and no meaning. Each profile lists them.
5. **Run-on sentences** — several ideas joined by commas, semicolons, dashes or relative clauses.
6. **Language traps** — the profile's own list: phrasal verbs, "-ся", "se", the impersonal "-takse", and the rest.

## Process

1. Detect the language and read its profile. Pick the mode.
2. Read the text once for meaning. Know what it must still say after the rewrite.
3. For a mechanical first pass, run the linter (see below) on the text. It finds candidates. It does not decide.
4. Walk the text sentence by sentence. Flag every universal rule, scan item and profile trap it breaks. In Flavored
   mode, flag the lexical rules but do not enforce them.
5. Rewrite each flagged sentence. Keep every fact, condition, scope qualifier, number and hedge.
   - If a rewrite would drop required precision (a safety condition, an exception, a number), keep the longer
     phrasing and report it.
   - Stop when the sentence has one reading, not when it is shortest. Past that point, compression costs the reader.
6. Output the result (see Output). If the text already complies, say so and change nothing.

## Linter

`scripts/simple_lint.py` is a stdlib-only Python linter for the mechanical part of the rules. It detects the language
of each paragraph (en, ru, es, et), or takes `--lang`.

```bash
python3 scripts/simple_lint.py FILE [FILE ...]
echo "text" | python3 scripts/simple_lint.py --lang ru --json
python3 scripts/simple_lint.py --baseline 5 --disable passive FILE
python3 scripts/simple_lint.py --selftest
```

Hard checks: semicolons, sentence length against the profile caps, nominalization with an empty verb, officialese,
marketing words and English phrasal verbs. Advisory checks: the passive, the English present perfect and synonym
rotation inside one file. The linter skips code blocks, inline code and tables. A paragraph full of quotes in another
language can be detected as that language: pass `--lang` for such text. **It never flags a hedge.** It cannot see
ambiguous references, genitive chains, word order or meaning: those stay your job. Exit code 1 means hard findings
exceed `--baseline` (default 0). Advisory findings never fail the run.

## Output

**Default: the rewritten text, and nothing else.** No preamble, no mode announcement, no count of changes, no closing
offer. The caller wants text to paste into a tool description, an error string or a prompt.

Two lines may follow the text, each only when it has content:

- `Kept as-is: <phrase> — <precision a shorter form would lose>.`
- `No profile for <language>: universal rules only.`

**On request: the rule table.** The user may ask for the reasoning: "show the diff", "which rules", "before/after",
"почему так", "explica los cambios". Then output this table instead. Keep the original and simplified text in the
input language, and write the rule names in the language of the conversation:

```markdown
| Rule                | Original                                   | Simplified                            |
|---------------------|--------------------------------------------|---------------------------------------|
| Nominalization      | "Необходимо осуществить проверку конфига." | "Проверьте конфиг."                   |
| Actor named ("-ся") | "Файл удаляется после загрузки."           | "Сервис удаляет файл после загрузки." |

Mode: Strict. Language: ru. 2 findings.
```

After the table, add one line on anything you deliberately did not simplify, and why.

## Boundaries

**Will:**

- Rewrite text in its own language into short, single-reading, actor-first sentences.
- Keep every fact, condition, scope qualifier, number and hedge.
- Suggest a one-line glossary entry for a domain term that must stay.

**Will not:**

- Translate the text, or "fix" code, identifiers, quotes or product names inside it.
- Reproduce the ASD-STE100 dictionary or claim compliance with it. This is a clarity tool inspired by STE, not a
  certified STE authoring tool. For real aircraft documentation, get the standard from
  [asd-ste100.org](https://www.asd-ste100.org/).
- Simplify creative, marketing or persuasive copy.
- Drop a safety condition, exception or qualifier to shorten a sentence. It reports the trade-off instead.
- Change "may have failed" into "failed", or "could be caused by X" into "X is the cause".
- Make weak content useful. A hollow paragraph rewritten under these rules is a short, clean hollow paragraph. If the
  text says nothing, say so instead of polishing it.

## Files

- `references/languages/en.md`, `ru.md`, `es.md`, `et.md` — length caps, traps, officialese lists and examples.
- `examples/before-after.md` — worked rewrites of agent output in all four languages, with the calls made.
- `scripts/simple_lint.py` — the linter.
