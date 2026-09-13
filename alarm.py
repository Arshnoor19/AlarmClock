#!/usr/bin/env python3
import click
import curses
import json
import os
import sys
import time
import threading
from datetime import datetime, timedelta

ALARM_DIR = os.path.expanduser("~/.alarm_clock")
ALARM_FILE = os.path.join(ALARM_DIR, "alarms.json")
CONFIG_FILE = os.path.join(ALARM_DIR, "config.json")
DEFAULT_SNOOZE_MINUTES = 5

ASCII_DIGITS = {
    "0": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "3": [" ### ", "#   #", "    #", "  ## ", "    #", "#   #", " ### "],
    "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    "6": [" ### ", "#    ", "#### ", "#   #", "#   #", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "],
    "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    "9": [" ### ", "#   #", "#   #", " ####", "    #", "#   #", " ### "],
    ":": ["     ", "  #  ", "     ", "     ", "     ", "  #  ", "     "],
}


def ensure_storage():
    os.makedirs(ALARM_DIR, exist_ok=True)
    if not os.path.exists(ALARM_FILE):
        with open(ALARM_FILE, "w") as f:
            json.dump({"alarms": []}, f, indent=2)


def load_alarms():
    ensure_storage()
    try:
        with open(ALARM_FILE, "r") as f:
            data = json.load(f)
            return data.get("alarms", [])
    except (json.JSONDecodeError, OSError):
        return []


def save_alarms(alarms):
    ensure_storage()
    with open(ALARM_FILE, "w") as f:
        json.dump({"alarms": alarms}, f, indent=2)


def load_config():
    ensure_storage()
    if not os.path.exists(CONFIG_FILE):
        return {"snooze_minutes": DEFAULT_SNOOZE_MINUTES}
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            config.setdefault("snooze_minutes", DEFAULT_SNOOZE_MINUTES)
            return config
    except (json.JSONDecodeError, OSError):
        return {"snooze_minutes": DEFAULT_SNOOZE_MINUTES}


def save_config(config):
    ensure_storage()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def next_id(alarms):
    if not alarms:
        return 1
    return max(a["id"] for a in alarms) + 1


def render_ascii_time(time_str):
    lines = [""] * 7
    for ch in time_str:
        glyph = ASCII_DIGITS.get(ch, ["     "] * 7)
        for i in range(7):
            lines[i] += glyph[i] + "  "
    return "\n".join(lines)


def beep():
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass
    if sys.platform == "darwin":
        os.system("afplay /System/Library/Sounds/Glass.aiff > /dev/null 2>&1 &")
    else:
        os.system("printf '\\a'")


# ---------- curses time picker ----------

def pick_format(stdscr):
    curses.curs_set(0)
    options = ["24-hour format", "12-hour format"]
    idx = 0
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Choose time format (UP/DOWN + ENTER):")
        for i, opt in enumerate(options):
            prefix = "> " if i == idx else "  "
            attr = curses.A_REVERSE if i == idx else curses.A_NORMAL
            stdscr.addstr(i + 2, 0, prefix + opt, attr)
        stdscr.refresh()
        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')):
            idx = (idx - 1) % len(options)
        elif key in (curses.KEY_DOWN, ord('j')):
            idx = (idx + 1) % len(options)
        elif key in (curses.KEY_ENTER, 10, 13):
            return "24hr" if idx == 0 else "12hr"
        elif key == 27:
            return None


def pick_time(stdscr, fmt):
    curses.curs_set(0)
    hour = 7
    minute = 30
    meridiem = 0  # 0 = AM, 1 = PM
    field = 0  # 0=hour, 1=minute, 2=meridiem(12hr only)
    fields = 3 if fmt == "12hr" else 2

    max_hour = 12 if fmt == "12hr" else 23
    min_hour = 1 if fmt == "12hr" else 0

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Set the time (LEFT/RIGHT to switch, UP/DOWN to change, ENTER to confirm):")

        hstr = f"{hour:02d}"
        mstr = f"{minute:02d}"
        merstr = "AM" if meridiem == 0 else "PM"

        def attr(i):
            return curses.A_REVERSE if field == i else curses.A_NORMAL

        y = 2
        x = 0
        stdscr.addstr(y, x, "[ ")
        x += 2
        stdscr.addstr(y, x, hstr, attr(0))
        x += len(hstr)
        stdscr.addstr(y, x, " ] : [ ")
        x += 7
        stdscr.addstr(y, x, mstr, attr(1))
        x += len(mstr)
        stdscr.addstr(y, x, " ]")
        x += 2
        if fmt == "12hr":
            stdscr.addstr(y, x, " [ ")
            x += 3
            stdscr.addstr(y, x, merstr, attr(2))
            x += len(merstr)
            stdscr.addstr(y, x, " ]")

        stdscr.refresh()
        key = stdscr.getch()

        if key in (curses.KEY_RIGHT, ord('l')):
            field = (field + 1) % fields
        elif key in (curses.KEY_LEFT, ord('h')):
            field = (field - 1) % fields
        elif key in (curses.KEY_UP, ord('k')):
            if field == 0:
                hour = min_hour if hour >= max_hour else hour + 1
            elif field == 1:
                minute = 0 if minute >= 59 else minute + 1
            elif field == 2:
                meridiem = 1 - meridiem
        elif key in (curses.KEY_DOWN, ord('j')):
            if field == 0:
                hour = max_hour if hour <= min_hour else hour - 1
            elif field == 1:
                minute = 59 if minute <= 0 else minute - 1
            elif field == 2:
                meridiem = 1 - meridiem
        elif key in (curses.KEY_ENTER, 10, 13):
            if fmt == "12hr":
                h24 = hour % 12
                if meridiem == 1:
                    h24 += 12
                return f"{h24:02d}:{minute:02d}"
            else:
                return f"{hour:02d}:{minute:02d}"
        elif key == 27:
            return None


def interactive_set():
    fmt = curses.wrapper(pick_format)
    if fmt is None:
        click.echo("Cancelled.")
        return
    time_str = curses.wrapper(pick_time, fmt)
    if time_str is None:
        click.echo("Cancelled.")
        return

    label = click.prompt("Label (optional)", default="", show_default=False)
    message = click.prompt("Message (optional)", default="", show_default=False)

    alarms = load_alarms()
    alarm = {
        "id": next_id(alarms),
        "time": time_str,
        "format": fmt,
        "label": label,
        "message": message,
        "active": True,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    alarms.append(alarm)
    save_alarms(alarms)
    click.echo(f"Alarm set for {time_str} (id={alarm['id']}).")


# ---------- CLI ----------

@click.group()
def cli():
    """Simple CLI alarm clock."""
    pass


@cli.command(name="set")
def set_alarm():
    """Interactively set a new alarm."""
    try:
        interactive_set()
    except Exception as e:
        click.echo(f"Error setting alarm: {e}", err=True)
        sys.exit(1)


@cli.command(name="list")
def list_alarms():
    """List all alarms."""
    alarms = load_alarms()
    if not alarms:
        click.echo("No alarms set.")
        return

    click.echo(f"{'ID':<4}{'TIME':<8}{'LABEL':<15}{'STATUS':<8}")
    for a in sorted(alarms, key=lambda x: x["id"]):
        status = "active" if a.get("active", True) else "inactive"
        label = a.get("label") or "-"
        click.echo(f"{a['id']:<4}{a['time']:<8}{label:<15}{status:<8}")


@cli.command()
def delete():
    """Delete an alarm by choosing from a list."""
    alarms = load_alarms()
    if not alarms:
        click.echo("No alarms to delete.")
        return

    alarms_sorted = sorted(alarms, key=lambda x: x["id"])
    click.echo("Select an alarm to delete:")
    for a in alarms_sorted:
        label = a.get("label") or "-"
        click.echo(f"  {a['id']}) {a['time']}  {label}")

    choice = click.prompt("Enter alarm ID to delete", type=int)
    remaining = [a for a in alarms if a["id"] != choice]
    if len(remaining) == len(alarms):
        click.echo(f"No alarm found with id {choice}.", err=True)
        sys.exit(1)

    save_alarms(remaining)
    click.echo(f"Deleted alarm {choice}.")


@cli.command(name="snooze-time")
@click.argument("minutes", type=int)
def snooze_time(minutes):
    """Set the default snooze duration in minutes."""
    if minutes <= 0:
        click.echo("Snooze duration must be a positive number of minutes.", err=True)
        sys.exit(1)

    config = load_config()
    config["snooze_minutes"] = minutes
    save_config(config)
    click.echo(f"Snooze duration set to {minutes} minute(s).")


def fire_alarm(alarm):
    stop_beep = threading.Event()

    def beep_loop():
        while not stop_beep.is_set():
            beep()
            time.sleep(1)

    snooze_minutes = load_config().get("snooze_minutes", DEFAULT_SNOOZE_MINUTES)

    os.system("clear" if os.name != "nt" else "cls")
    art = render_ascii_time(alarm["time"])
    click.echo("\n" + art + "\n")
    if alarm.get("label"):
        click.echo(f"Label: {alarm['label']}")
    if alarm.get("message"):
        click.echo(f"Message: {alarm['message']}")
    click.echo(f"\n[ENTER] Snooze ({snooze_minutes} min)    [D] Dismiss")

    beep_thread = threading.Thread(target=beep_loop, daemon=True)
    beep_thread.start()
    action = "dismiss"
    try:
        choice = input().strip().lower()
        action = "dismiss" if choice == "d" else "snooze"
    except (EOFError, KeyboardInterrupt):
        action = "dismiss"
    stop_beep.set()

    if action == "snooze":
        click.echo(f"Alarm snoozed for {snooze_minutes} minute(s).")
    else:
        click.echo("Alarm dismissed.")

    return action


def watch_alarms(stop_event):
    fired_today = set()
    last_date = datetime.now().date()

    while not stop_event.is_set():
        now = datetime.now()
        if now.date() != last_date:
            fired_today.clear()
            last_date = now.date()

        current_time = now.strftime("%H:%M")
        alarms = load_alarms()
        for a in alarms:
            if not a.get("active", True):
                continue
            key = (a["id"], current_time)
            if a["time"] == current_time and key not in fired_today:
                fired_today.add(key)
                action = fire_alarm(a)
                if action == "snooze":
                    snooze_minutes = load_config().get("snooze_minutes", DEFAULT_SNOOZE_MINUTES)
                    new_time = (now + timedelta(minutes=snooze_minutes)).strftime("%H:%M")
                    all_alarms = load_alarms()
                    for existing in all_alarms:
                        if existing["id"] == a["id"]:
                            existing["time"] = new_time
                            break
                    save_alarms(all_alarms)
                    fired_today.discard((a["id"], new_time))

        stop_event.wait(5)


@cli.command()
def start():
    """Start the background alarm watcher daemon."""
    ensure_storage()
    click.echo("Alarm watcher started. Press Ctrl+C to stop.")
    stop_event = threading.Event()
    watcher = threading.Thread(target=watch_alarms, args=(stop_event,), daemon=True)
    watcher.start()
    try:
        while watcher.is_alive():
            watcher.join(timeout=1)
    except KeyboardInterrupt:
        stop_event.set()
        click.echo("\nAlarm watcher stopped.")


if __name__ == "__main__":
    cli()
