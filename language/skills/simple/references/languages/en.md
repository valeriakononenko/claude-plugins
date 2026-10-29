# English (`en`)

English is the language ASD-STE100 was built for, so this profile follows the standard most closely. It keeps the
rule categories of STE Issue 9 (2025) but not its approved dictionary, which ASD does not allow to be redistributed.

## Sentence length

- Instructions and procedures: at most **20 words**.
- Descriptions: at most **25 words**.

Count whitespace-separated words. Code spans count as one word.

## Traps

### Phrasal verbs

A verb plus a particle has meanings its parts do not predict, and translators and models mishandle it.

- "Take off the panel." → "Remove the panel." ("take off" also means depart and deduct)
- "Spin up the job." → "Start the job."
- "Reach out to the owner." → "Contact the owner."
- "Look into the failure." → "Examine the failure."
- "Set up the database." → "Configure the database." (or "Create", when that is what happens)

Keep a phrasal verb only when it is the domain term and has no single-verb equivalent ("log in" in a UI label).

### Compound tenses

STE allows the simple tenses, the imperative, the infinitive and the past participle as an adjective.

- "We have received the report." → "We received the report."
- "The job had been started before the lock was taken." → "The job started before the service took the lock."

**Exception:** keep the compound form when it carries information the simple form cannot. "The job has completed"
says its output is available now. "May have failed" is a hedge. Keep both and flag the departure.

### Passive voice

- "The file is deleted after upload." → "The service deletes the file after upload."

A passive is fine in a description when the actor is unknown or irrelevant: "The log is rotated every day."

### "-ing" forms

Use "-ing" only inside a technical noun ("routing table"). As a verb form it hides the actor or the order of events.

- "Using the token, the request is sent." → "The client sends the request with the token."

### Noun clusters

At most 3 nouns stacked.

- "the agent task queue priority handler" → "the handler that sets the priority of the task queue"

### Words with two readings

| Word     | Readings                      | Fix                                                    |
|----------|-------------------------------|--------------------------------------------------------|
| `may`    | permission / possibility      | "can" for permission, keep "may" for possibility       |
| `can`    | ability / possibility         | "is able to" or "sometimes"; keep and flag if unclear  |
| `should` | recommendation / expectation  | "must" or "we recommend"; "is expected to"             |
| `once`   | after / one time              | "after", "one time"                                    |
| `since`  | because / from a time         | "because", "from"                                      |
| `as`     | because / while / like        | "because", "while", "like"                             |
| `follow` | obey / come after             | "obey", "after"                                        |
| `left`   | remaining / opposite of right | "remaining"                                            |

## Officialese and filler

| Avoid                       | Use               |
|-----------------------------|-------------------|
| in order to                 | to                |
| utilize, leverage           | use               |
| perform / conduct a(n) X    | the verb of X     |
| is able to                  | can               |
| at this point in time       | now               |
| due to the fact that        | because           |
| in the event that           | if                |
| it is important to note     | (delete)          |
| prior to                    | before            |
| facilitate                  | help, make easier |

Marketing words to delete or measure: seamless, robust, powerful, cutting-edge, effortless, blazing-fast,
world-class, state-of-the-art, game-changing.

## Linter coverage

Hard: semicolon, long sentence (25 words), nominalization (perform/conduct/carry out + noun), officialese, marketing
words, soft phrasal verbs. Advisory: passive voice, present perfect, synonym rotation (check/verify/confirm/validate
and others). A modal before the perfect ("may have failed") is never flagged.
