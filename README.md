# ⏰ Alarm Clock CLI

A terminal-based alarm clock built in Python. Set alarms, run a stopwatch, and countdown timers — all from your terminal, no GUI needed.

---

## Installation

**Requirements:** Python 3.8+

```bash
# Clone the repo
git clone https://github.com/yourusername/AlarmClock.git
cd AlarmClock

# Install dependency
pip install click
```

---

## Commands

### Set an alarm
```bash
python3 alarm.py set
```
- Choose 24-hour or 12-hour format
- Interactive time picker — arrow keys to change, LEFT/RIGHT to switch fields, ENTER to confirm
- Optionally add a label and message

### List all alarms
```bash
python3 alarm.py list
```
```
ID  TIME    LABEL          STATUS
1   07:30   Wake up        active
2   14:00   Lunch          active
```

### Delete an alarm
```bash
python3 alarm.py delete
```
Shows a list of alarms to pick from — no need to remember IDs.

### Start the alarm watcher
```bash
python3 alarm.py start
```
Runs in the foreground and fires alarms at the right time. Keep this running in a separate terminal. Press `Ctrl+C` to stop.

### Configure snooze duration
```bash
python3 alarm.py snooze-time 10
```
Sets snooze to 10 minutes. Default is 5 minutes.

### Stopwatch
```bash
python3 alarm.py stopwatch
```
```
⏱  00:04:32.12  [running]

Splits:
  #1  00:01:20.44
  #2  00:03:21.44
  #3  00:05:32.12

Controls: ENTER start/stop | SPACE split | R reset | Q quit
```

### Countdown Timer
```bash
python3 alarm.py timer 25
```
```
⏳  24:32  [running]

Started: 25:00

Controls: ENTER start/pause | R reset | Q quit
```
Fires the alarm sound when it hits 00:00. Press ENTER to snooze, D to dismiss.

---

## When an alarm fires

```
 ###    ###        ###    ###
#   #  #   #  #  #   #  #   #
...

Label: Wake up
Message: Don't snooze this time

[ENTER] Snooze (5 min)    [D] Dismiss
```

---

## Data storage

All data is stored locally in `~/.alarm_clock/`:

```
~/.alarm_clock/
  alarms.json    # saved alarms
  config.json    # snooze duration and settings
```

No database, no internet connection needed.

---

## Key decisions

| Decision | Reason |
|---|---|
| `click` for CLI | Clean subcommand structure like git/npm |
| `curses` for time picker | Raw keyboard input, no enter-to-confirm UX |
| JSON for storage | No setup needed, human readable, portable |
| `threading.Event` for watcher | Clean shutdown on Ctrl+C without killing mid-fire |
| System beep fallback | No external audio dependencies — uses `afplay` on macOS, `\a` elsewhere |

---


