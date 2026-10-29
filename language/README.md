# language

A Claude Code plugin for text that no reader can misread, in any language. It takes the discipline of ASD-STE100
(Simplified Technical English), the aerospace standard for maintenance manuals, and applies it beyond English: to
tool descriptions, error messages, prompts, inter-agent instructions and status reports that an agent, a translator
or a non-native reader must parse with no author to ask.

## What it gives you

### `language:simple`

- **Universal rules** that hold in every language: one action per sentence, length caps, the actor named, no
  semicolons, at most 3 stacked nouns, clear references, conditions before actions, one term for one thing, verbs
  instead of nominalizations, no officialese, idioms or marketing adjectives.
- **Language profiles** for English, Russian, Spanish and Estonian: sentence-length caps, the traps of each language
  (phrasal verbs, "-ся", "se", the impersonal "-takse", "poolt", false friends and more), modal words with two
  readings and an officialese table with plain replacements.
- **Modality kept**: "may have failed" never becomes "failed", and the rewrite adds no cause, frequency or step the
  source did not state.
- **No translation**: the result is in the language of the input. Code, identifiers, quotes and product names stay
  as they are. A language without a profile gets the universal rules and a note that it has no profile.
- **Two modes**: Strict for instructions, errors, tool descriptions and prompts. Flavored for READMEs, PR descriptions
  and changelogs, where the lexical rules are advice.
- **Text only by default**: the rewritten text, ready to paste. A table of broken rules, original and rewrite on
  request.
- A dependency-free Python linter for the mechanical rules. It detects the language of each paragraph, flags
  semicolons, long sentences, nominalizations, officialese and marketing words as hard findings, and the passive, the
  English present perfect and synonym rotation as advisory ones. It never flags a hedge.

## Not included

The ASD-STE100 dictionary of approved words. ASD does not allow it to be redistributed, so the skill applies the
principle (the plainest common word, used the same way every time) instead of a word list. For real aircraft
documentation, request the standard at [asd-ste100.org](https://www.asd-ste100.org/).

## Install

```
/plugin marketplace add valeriakononenko/claude-plugins
/plugin install language@divergence082-plugins
```

## Use

Ask in your own words: "simplify this error message", "упрости описание инструмента", "simplifica este texto",
"lihtsusta see juhend", or invoke `/language:simple`. Ask for "before/after" to see which rules the rewrite applied.

Run the linter on its own:

```bash
python3 language/skills/simple/scripts/simple_lint.py docs/*.md
echo "Необходимо осуществить проверку; затем перезапустить." | python3 language/skills/simple/scripts/simple_lint.py
python3 language/skills/simple/scripts/simple_lint.py --selftest
```

## Credits

The rule set follows the public description of ASD-STE100 Issue 9 (2025) and builds on the structure of
[asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) by Dustin Yuchen Teng (MIT).
