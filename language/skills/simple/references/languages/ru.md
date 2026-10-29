# Russian (`ru`)

Russian has free word order, six cases, two aspects and a reflexive suffix that also builds the passive. Each one
gives a sentence a second reading. The main source of dense Russian text is канцелярит: chains of verbal nouns in
the genitive, held together by empty verbs.

## Sentence length

- Instructions and procedures: at most **18 words**.
- Descriptions: at most **22 words**.

Russian has no articles, so the same content takes fewer words than in English. The caps are lower to match.

## Traps

### Verbal nouns and genitive chains (канцелярит)

An action turned into a noun needs an empty verb to carry it, and every next noun goes into the genitive.

- "Необходимо осуществить проверку корректности заполнения полей." → "Проверьте, что поля заполнены правильно."
- "Производится обработка запроса." → "Сервис обрабатывает запрос."
- "для обеспечения возможности проведения анализа" → "чтобы можно было проанализировать"

At most 3 nouns in a row. Empty verbs to remove: осуществлять, производить, проводить, выполнять, обеспечивать,
являться, иметь место.

### "-ся": reflexive or passive

"Файл удаляется" can mean "the file deletes itself" or "someone deletes the file". In an instruction it hides who
must act.

- "Файл удаляется после загрузки." → "Сервис удаляет файл после загрузки."
- "Настройки сохраняются автоматически." — fine in a description, where the actor is irrelevant.

### Subject and object in the same form

When the subject and the object have the same form in the nominative and the accusative, word order alone decides,
and free word order lets both readings stand.

- "Сервис обновляет агент." — who updates whom? → "Сервис обновляет агента." / "Агент обновляет сервис."
- "Ошибку вызывает таймаут." — readable, but "Таймаут вызывает ошибку." is safer: subject first, then verb, then
  object.

Prefer the order subject → verb → object.

### "Который" with two candidates

"Который" agrees with its noun in gender and number. When two nouns match, the reading is open.

- "Лог сервиса, который упал." — the log or the service? → "Лог упавшего сервиса." / "Сервис упал. Вот его лог."

### Participle and gerund phrases

A long participle phrase is a sentence inside a sentence. A gerund (деепричастие) must have the same subject as the
main verb.

- "Запустив скрипт, появилась ошибка." → "Когда я запустил скрипт, появилась ошибка."
- "Сервис, получивший от клиента запрос с устаревшим токеном, возвращает 401." → "Если токен в запросе устарел,
  сервис возвращает 401."

### Aspect carries meaning

"Проверьте" means once, "проверяйте" means every time. Do not swap the aspect to shorten or smooth a sentence.

### Modal words with two readings

| Word       | Readings                   | Fix                                                |
|------------|----------------------------|----------------------------------------------------|
| `может`    | способен / возможно        | "умеет"; "возможно, …"; keep and flag if unclear   |
| `должен`   | обязан / ожидается         | "обязан"; "скорее всего"                           |
| `нужно`    | требование / рекомендация  | "обязательно"; "рекомендуем"                       |
| `пока`     | до тех пор, пока / сейчас  | "до тех пор, пока"; "сейчас"                       |
| `сразу`    | немедленно / одновременно  | "немедленно"; "одновременно"                       |

### Form of address

Pick one form for instructions and keep it: the imperative with "вы" ("Откройте файл") or the infinitive ("Открыть
файл"). Do not mix "ты" and "вы".

## Officialese and filler

| Avoid                                 | Use                              |
|---------------------------------------|----------------------------------|
| данный                                | этот                             |
| является                              | — (dash) or rebuild the sentence |
| осуществлять / производить X-ние      | the verb of X                    |
| в целях, с целью                      | чтобы                            |
| в рамках                              | в, во время, для                 |
| в случае если                         | если                             |
| в связи с тем, что                    | потому что                       |
| на сегодняшний день                   | сейчас                           |
| вышеуказанный, нижеследующий          | этот, следующий                  |
| имеет место                           | есть, происходит                 |
| следует отметить, что                 | (delete)                         |

Marketing words to delete or measure: бесшовный, мощный, передовой, инновационный, уникальный, революционный,
надёжный (without a measurement).

## Linter coverage

Hard: semicolon, long sentence (22 words), nominalization (осуществлять/производить/проводить + noun in -ние/-ция),
officialese, marketing words. Advisory: passive with "был/будет + short participle", synonym rotation (проверить/
убедиться/удостовериться and others). The linter cannot see "-ся", word order, "который" or genitive chains.
