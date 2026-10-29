---
name: coffee
description: >
  Keep the Mac awake with caffeinate. Start it when the user's message is just "coffee" (or "кофе", "café"), optionally
  with a duration such as "coffee 2h" or "coffee 30m"; stop it on "decaf", "coffee off", "no coffee" or "хватит кофе";
  report it on "coffee status". Use whenever the user asks to keep the computer awake, stop it sleeping, or run
  caffeinate.
---

# Coffee

Run macOS `caffeinate` detached, so the Mac stays awake after this session ends. Do the action at once: no questions,
no plan. Reply in one line.

## Start

1. Check `uname`. On anything but `Darwin`, say that `caffeinate` is macOS-only and stop.
2. Read the duration from the message: `30m`, `2h`, `1h30m`, `90` (minutes) or words like "на час". Convert it to
   seconds. No duration means until stopped.
3. Stop a running copy first, so the new duration replaces the old one:

   ```bash
   pkill -x caffeinate
   ```

4. Start it detached. `-d` keeps the display on, `-i` blocks idle sleep, `-m` keeps the disk awake, `-s` blocks
   system sleep on AC power:

   ```bash
   nohup caffeinate -dims >/dev/null 2>&1 &            # until stopped
   nohup caffeinate -dims -t <seconds> >/dev/null 2>&1 &   # for a duration
   ```

5. Confirm with `pgrep -lf caffeinate` and reply: "☕ Mac stays awake until <time or 'you say decaf'>."

## Stop

```bash
pkill -x caffeinate
```

Reply "Decaf: the Mac can sleep again." If nothing was running, say so.

## Status

Run `pgrep -lf caffeinate` and `ps -o etime= -p <pid>`. Report whether it runs, for how long and the `-t` limit if
one is set.
