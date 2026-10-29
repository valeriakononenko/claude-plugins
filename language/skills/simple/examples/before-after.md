#
Before / after

Worked rewrites of agent output, one or two per language. Each lists what was flagged, what was deliberately not
flagged, and any call the rewrite made. The examples are illustrations, not quotes from a real system.

## English — tool description (Strict)

**Before:**

> This tool will attempt to synchronize state across the various backends that have been configured, and if a
> conflict is detected it may resolve it automatically depending on the strategy that has been set, or otherwise it
> will surface the conflict for manual review.

**Flagged:** two actions in one sentence, present perfect in the relative clauses, passive "is detected", 44 words.

**Not flagged:** "will attempt to" and "may resolve". They are hedges: the tool is not promised to succeed.

**After:**

> The tool tries to synchronize state across the configured backends. If it finds a conflict, it reads the configured
> strategy. If the strategy allows automatic resolution, the tool may resolve the conflict. If the tool does not
> resolve the conflict, it reports the conflict for manual review.

## English — error message (Strict)

**Before:**

> An error may have occurred while processing your request due to a possible mismatch in the expected data format,
> which could be caused by an outdated client version.

**After:**

> Your request may have failed. The cause may be a data format that does not match what the server expects. An
> outdated client can cause this mismatch. Check your client version.

**The modality call.** A tempting rewrite is "The request failed. The most common cause is an outdated client." It
reads better and is wrong twice: it asserts a failure the system only suspects, and it invents a frequency. "May have
failed" keeps a compound tense because the modality rule wins over the tense rule.

## Russian — inter-agent instruction (Strict)

**Before:**

> После того как будет осуществлено завершение выполнения задачи сборки и при условии отсутствия ошибок, агенту
> следует произвести загрузку артефакта, однако необходимо учитывать, что в случае таймаута данный артефакт может
> оказаться неполным.

**Flagged:** genitive chain "завершение выполнения задачи сборки", empty verbs "осуществлено", "произвести",
officialese "в случае", "данный", "необходимо учитывать", three facts in one sentence, 31 words.

**Not flagged:** "может оказаться неполным". It is a hedge: a timeout does not always cut the artifact.

**After:**

> Дождитесь, когда задача сборки завершится без ошибок. Затем загрузите артефакт. Внимание: при таймауте артефакт
> может оказаться неполным.

**The call.** "Следует произвести загрузку" became the imperative "загрузите": in an instruction to the executing
agent, a recommendation is a command. Do not make the same move in a description. A sentence like "Проверьте, что
артефакт полный" would make the warning actionable, but the source did not say it. If you add it, list it as a
suggestion after the text.

## Russian — README prose (Flavored)

**Before:**

> Данный модуль является высокопроизводительным решением для осуществления кеширования ответов; он обеспечивает
> бесшовную интеграцию с существующей инфраструктурой.

**After:**

> Модуль кеширует ответы сервиса. Он работает с вашей инфраструктурой без изменений в ней.

**Calls.** "Высокопроизводительный" and "бесшовный" are claims without a measurement: they are gone. If the author
has a number ("отвечает за 2 мс"), put the number back.

## Spanish — error message (Strict)

**Before:**

> Se ha producido un error a nivel de la validación de los datos de configuración del usuario, debiéndose proceder a
> la revisión de los mismos con el fin de que el proceso pueda ser completado.

**Flagged:** "se ha producido" hides the actor, "de" chain of four nouns, officialese "a nivel de", "proceder a", "los
mismos", "con el fin de que", gerund "debiéndose", passive "pueda ser completado", 35 words.

**After:**

> La validación falló: la configuración del usuario tiene datos incorrectos. Revise la configuración y vuelva a
> ejecutar el proceso.

**The call.** "Vuelva a ejecutar el proceso" spells out what "para que el proceso pueda ser completado" implied. It
adds no new fact: the source already said the process must complete after the fix.

## Spanish — status report (Strict)

**Before:**

> Eventualmente el servicio se reinició, pudiendo haberse perdido algunos mensajes de la cola.

**After:**

> Al final el servicio se reinició. Es posible que se perdieran algunos mensajes de la cola.

**Calls.** "Eventualmente" here means "finally", a false friend: replaced with "al final". The hedge "pudiendo
haberse perdido" stays a hedge: "es posible que se perdieran", not "se perdieron".

## Estonian — instruction (Strict)

**Before:**

> Enne andmebaasi uuendamise protsessi läbiviimist tuleb antud serveri poolt teostada varukoopia tegemine, kuna
> vastasel juhul võivad andmed kaduma minna.

**Flagged:** genitive chain "andmebaasi uuendamise protsessi", empty verbs "läbiviimist", "teostada", "-mine" noun
"tegemine", "poolt", "antud", 19 words.

**Not flagged:** "võivad … kaduma minna". It is a hedge.

**After:**

> Enne andmebaasi uuendamist peab see server tegema varukoopia. Ilma varukoopiata võivad andmed kaduma minna.

**The call.** The source names the server as the actor, so the rewrite keeps the server as the actor. An imperative
("Tee varukoopia") would move the duty to the reader.

## Estonian — description (Flavored)

**Before:**

> Fail kustutatakse automaatselt pärast seda, kui selle töötlemine on teenuse poolt lõpetatud.

**After:**

> Kui teenus lõpetab faili töötlemise, kustutab teenus faili automaatselt.

**The call.** The impersonal "kustutatakse" alone would be fine in a description. Here the "poolt" clause names the
actor anyway, so the active sentence is both shorter and clearer.
