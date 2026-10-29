# Estonian (`et`)

Estonian has 14 cases, joins nouns into long compounds, has no grammatical gender and no future tense, and expresses
the passive through the impersonal (umbisikuline tegumood). Its officialese (kantseliit) leans on empty verbs,
"-mine" nouns and the "poolt" construction.

## Sentence length

- Instructions and procedures: at most **15 words**.
- Descriptions: at most **20 words**.

Case endings and compounds pack more content into a word than English does. The caps are lower to match.

## Traps

### Empty verbs and "-mine" nouns

- "Teostage konfiguratsiooni kontrollimine." → "Kontrollige konfiguratsiooni."
- "Toimub andmete töötlemine." → "Teenus töötleb andmeid."
- "Viige läbi failide kustutamine." → "Kustutage failid."

Empty verbs to remove: teostama, läbi viima, toimuma, sooritama, omama, osutuma.

### Genitive chains and compounds

At most 3 nouns in a genitive chain, and at most 3 parts in a compound you write yourself. Keep an established term
("andmebaasiserver") as it is.

- "kasutaja konto seadete muutmise taotlus" → "kasutaja taotlus muuta konto seadeid"
- "võrguühendusetõrketeade" → "võrguühenduse tõrke teade" → "teade, et võrguühendus katkes"

### The impersonal hides the actor

"Fail kustutatakse" and "fail kustutati" say nothing about who deletes the file. In an instruction, name the actor or
use the imperative.

- "Pärast üleslaadimist fail kustutatakse." → "Pärast üleslaadimist kustutab teenus faili."

Keep the impersonal in a description when the actor is irrelevant: "Logi roteeritakse iga päev."

### "Poolt"

"X-i poolt" for the agent is a calque from Russian and German and counts as kantseliit.

- "Fail kustutati teenuse poolt." → "Teenus kustutas faili."

### Particle verbs

A particle verb (ühendverb) splits in a main clause, and the particle can land far from the verb: "Lülita pärast
varukoopia tegemist ja kontrollimist teenus välja." Keep the verb and its particle close, or use a single verb.

- "Viige läbi kontroll." → "Kontrollige."
- "Lülita pärast varukoopia tegemist teenus välja." → "Tee varukoopia. Seejärel lülita teenus välja."

### No future tense

Estonian uses the present tense for the future. When the time matters, name it.

- "Teenus taaskäivitub." — now or later? → "Teenus taaskäivitub 5 minuti pärast."

Do not build a future with "saama" ("fail saab kustutatud"): it is a calque.

### "Antud" as "this"

"Antud juhul", "antud fail" is a calque. Use "see".

- "Antud fail on vigane." → "See fail on vigane."

### Modal words with two readings

| Word       | Readings                     | Fix                                                |
|------------|------------------------------|----------------------------------------------------|
| `võib`     | tohib / võimalik             | "tohib"; "võimalik, et"; keep and flag if unclear  |
| `peab`     | kohustus / eeldus            | "on kohustatud"; "eeldatavasti"                    |
| `saab`     | suudab / tohib               | "suudab"; "tohib"                                  |

### Form of address

Pick the plural imperative ("Avage fail") or the singular one ("Ava fail") and keep it. Interfaces often use the
singular. Formal documents use the plural.

## Officialese and filler

| Avoid                        | Use                       |
|------------------------------|---------------------------|
| antud (in the sense "this")  | see                       |
| X-i poolt                    | active sentence           |
| teostama, läbi viima         | the verb of the action    |
| toimub X-mine                | the verb of X             |
| omama                        | olema (X-il on …)         |
| eesmärgiga                   | et                        |
| juhul, kui                   | kui                       |
| tulenevalt asjaolust, et     | sest                      |
| hetkel                       | praegu                    |
| tuleb märkida, et            | (delete)                  |

Marketing words to delete or measure: võimas, töökindel (without a measurement), uuenduslik, innovaatiline,
revolutsiooniline, tipptasemel, sujuv.

## Linter coverage

Hard: semicolon, long sentence (20 words), nominalization (teostama/läbi viima/toimuma + noun in -mine/-mise),
officialese ("antud", "poolt" and the rest), marketing words. Advisory: synonym rotation (kontrollima/veenduma/
kinnitama and others). The linter does not flag the impersonal: Estonian uses it in good plain text. It cannot see
compounds, genitive chains or particle verbs.
