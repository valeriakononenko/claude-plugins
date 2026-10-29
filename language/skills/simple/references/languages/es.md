# Spanish (`es`)

Spanish drops the subject, uses one particle — "se" — for the passive, the impersonal and the reflexive, and builds
long chains of "de". Administrative Spanish (lenguaje administrativo) adds empty verbs and set phrases on top.

## Sentence length

- Instructions and procedures: at most **20 words**.
- Descriptions: at most **25 words**.

## Traps

### Empty verbs and nominalization

- "Realice la verificación de la configuración." → "Verifique la configuración."
- "Se procedió a la eliminación de los registros." → "El servicio eliminó los registros."
- "Proceda a reiniciar el servidor." → "Reinicie el servidor."

Empty verbs to remove: realizar, efectuar, llevar a cabo, proceder a, hacer entrega de.

### "De" chains

At most 3 nouns joined by "de".

- "la solicitud de modificación de la configuración de red del cliente" → "la solicitud del cliente para cambiar la
  configuración de red"

### "Se": passive, impersonal or reflexive

"Se eliminó el archivo" hides who deleted it. "Se envía la respuesta" can be a description or an instruction.

- "Se eliminan los archivos temporales." → "El agente elimina los archivos temporales."
- "Se recomienda reiniciar." → "Recomendamos reiniciar." / "Reinicie."

Keep "se" in a description when the actor is irrelevant: "El log se rota cada día."

### Periphrastic passive

"Ser + participio" is rarer in Spanish than in English and often a calque.

- "El archivo fue eliminado por el servicio." → "El servicio eliminó el archivo."

### Dropped subject

The verb ending names only the person, not the actor. When two actors are in play, name the subject.

- "El cliente envía el token al servidor. Después lo valida." → "… Después el servidor valida el token."

### "Su" with several owners

"Su" can mean his, her, its, their or your (usted).

- "El agente envía su clave al servidor." → "El agente envía la clave del agente al servidor." / "… su propia clave …"

### Gerund after the main verb

A gerund for a later action (gerundio de posterioridad) is an error and hides the order of events.

- "El servicio falló, reiniciándose a los 5 segundos." → "El servicio falló. Se reinició 5 segundos después."

### False friends in technical text

| Avoid (in this sense)            | Use                                      |
|----------------------------------|------------------------------------------|
| `eventualmente` = "finally"      | `finalmente`, `al final`                 |
| `remover` = "remove"             | `quitar`, `eliminar`                     |
| `aplicar` = "apply (for)"        | `solicitar`                              |
| `librería` = "library" (code)    | `biblioteca`                             |
| `asumir` = "assume"              | `suponer`                                |
| `en base a`                      | `según`, `a partir de`                   |

### Modal words with two readings

| Word        | Readings                     | Fix                                              |
|-------------|------------------------------|--------------------------------------------------|
| `puede`     | es capaz / es posible        | "es capaz de"; "es posible que"; keep and flag   |
| `debe`      | obligación                   | keep                                             |
| `debe de`   | suposición                   | keep — do not merge with `debe`                  |
| `deberá`    | obligación / predicción      | "tiene que"; "probablemente"                     |

### Form of address

Pick "usted" or "tú" for instructions and keep it. Do not mix "Reinicie" and "Reinicia" in one document.

## Officialese and filler

| Avoid                            | Use                       |
|----------------------------------|---------------------------|
| a nivel de                       | en                        |
| de cara a                        | para                      |
| con el fin de, a fin de          | para                      |
| en el caso de que                | si                        |
| debido al hecho de que           | porque                    |
| en la actualidad                 | ahora                     |
| cabe destacar que                | (delete)                  |
| el mismo, la misma (as pronoun)  | él, ella, or the noun     |
| procedemos a                     | (delete)                  |

Marketing words to delete or measure: potente, robusto, innovador, revolucionario, de vanguardia, sin fisuras,
líder, único.

## Linter coverage

Hard: semicolon, long sentence (25 words), nominalization (realizar/efectuar/llevar a cabo + noun in -ción/-miento),
officialese, marketing words. Advisory: passive with "ser + participio", synonym rotation (verificar/comprobar/
confirmar and others). The linter cannot see "se", "su", dropped subjects or the gerund of posteriority.
