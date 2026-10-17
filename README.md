# PanzerPlanner
A student planner program made for IMB Z Datathon 2026

# Student Planner

A desktop student planner built with Python and tkinter. It pulls your class timetable from a university timetable service over a URL, lets you add classmates' calendars, tracks your assignments, and finds times when your study group is free.

- **Single file:** `student_planner.py`
- **No dependencies:** Python standard library only
- **Python:** 3.9 or newer

---

## Features

| Area | What it does |
| --- | --- |
| **Timetable** | Four views, switched with the buttons at the top right: **List** (grouped by day), **Week** (hour-by-hour grid with a red "now" line), **Day** (one column per calendar, so you can compare classmates side by side) and **Month** (click a day to open it). Everything is colour-coded by calendar, overlapping classes sit side by side, and tasks due in the period are shown. Click a class for details. |
| **Tasks & Assignments** | Add, edit, delete and complete tasks with course, due date and priority. Overdue tasks show red, tasks due within 2 days show amber. |
| **Timetable Sources** | Add multiple iCal / webcal URLs: yours plus classmates'. Each has an owner, a colour and a show/hide switch. |
| **Study Group Planner** | Pick several calendars and list the times when everyone is free. Copy slots to the clipboard or add one as a study task. |
| **Next up banner** | Shows your next class and the time until it starts (your own calendars only). |
| **Offline cache** | The last downloaded timetable is stored locally and shown even without a connection. |
| **Background sync** | Calendars download in a background thread so the window never freezes. Optional sync on startup. |

---

## Installation and running

1. Install Python 3.9+.
2. Make sure tkinter is available:
   - **Windows / macOS:** included with the python.org installer.
   - **Debian / Ubuntu:** `sudo apt install python3-tk`
   - **Fedora:** `sudo dnf install python3-tkinter`
3. Run the app:

```bash
python student_planner.py
```

> **Windows note:** if your timetable uses named time zones (e.g. `Australia/Melbourne`) and times look wrong, run `pip install tzdata` so Python can read the time zone database.

---

## Connecting your university timetable

The app reads the standard **iCalendar (`.ics`)** format, which most timetable and calendar systems can publish as a personal subscription link.

1. Find your university's **Subscribe**, **Export** or **Calendar feed** option and copy the link.
2. In the app, open the **Timetable Sources** tab and click **Add source**.
3. Fill in the form:
   - **Name:** any label, e.g. `My Timetable`. Names must be unique.
   - **URL:** an `https://` or `webcal://` link. `webcal://` is converted to `https://` automatically.
   - **Whose calendar:** `Me` or `Classmate`.
   - **Colour:** used for timetable rows and the calendar list.
   - **Extra header (optional):** `Header-Name: value`, for services that need a token header.
4. The calendar downloads straight away. Use **Sync timetables** (top right) to refresh all calendars at any time.

### If it says the URL did not return a calendar

The link probably points at a login page instead of a feed. Look for the subscription or export link inside your timetable service. The feed URL normally contains a secret token, so no login is needed. If your service only works behind a login, a plain URL fetch can't reach it.

---

## Adding classmates' calendars

Ask each classmate to share the iCal link for their calendar:

- **Google Calendar:** Settings → pick the calendar → *Secret address in iCal format*
- **Outlook:** Calendar → *Publish calendar* → copy the ICS link
- **University timetable:** the same Subscribe / Export link you used for your own

Add each one as a source with **Whose calendar** set to `Classmate`. Use **Show / hide** to switch a calendar off in the timetable without deleting it.

> **Privacy:** these links usually act like passwords. They are saved as plain text in `~/.student_planner.json`. Only add calendars people have agreed to share, and don't post the links publicly.

---

## Study Group Planner

1. Open the **Study Group Planner** tab.
2. Select two or more calendars in the list (Ctrl/Shift-click).
3. Set the options:

   | Option | Default | Notes |
   | --- | --- | --- |
   | Start date | today | `YYYY-MM-DD` |
   | Number of days | 7 | 1–60 |
   | Day starts / ends | 09:00 / 18:00 | `HH:MM`, end must be after start |
   | Min length | 60 | minutes, at least 5 |
   | Include weekends | off | |

4. Click **Find common free time**.
5. Switch to the **Heatmap** tab for a day × 30-minute grid shaded from red (nobody free) to green (everyone free). Each cell shows how many people are free, for example `3/4`. Click a cell to see who is free or busy. If everyone is free, you can add it as a study task straight away.
6. On the **Free slots** tab, select one or more results, then either:
   - **Copy selected to clipboard** for a ready-to-paste group chat message, or
   - **Add selected as study task** to add the first selected slot to your Tasks tab.

Notes:

- All-day events (e.g. public holidays) are ignored when finding free time.
- If a selected calendar hasn't been synced yet, the app asks you to sync first. An empty calendar would otherwise look completely free.
- Hidden calendars can still be used in the finder.

---

## Tasks & Assignments

- **Add / Edit:** title, course, due date (`YYYY-MM-DD HH:MM`, or just `YYYY-MM-DD` which becomes 23:59), and priority (Low / Medium / High).
- **Toggle done:** marks a task complete. Use **Show completed** to see finished tasks.
- Tasks are sorted by completion, then due date, then priority.

---

## Data and storage

Everything is saved to a single JSON file:

~/.student_planner.json

It contains your sources, tasks, cached events, last-sync times and settings. To reset the app, close it and delete that file. To back up, copy it.

---

## What the calendar parser supports

| Supported | Not supported |
| --- | --- |
| One-off and all-day events | Edits to single occurrences of a repeating event (`RECURRENCE-ID`) |
| Repeating events: `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY` | Complex rules such as "second Tuesday of the month" (`BYSETPOS`, `BYDAY` on monthly rules) |
| `INTERVAL`, `COUNT`, `UNTIL`, `EXDATE`, and `BYDAY` on weekly rules | Events that need a login to download |
| UTC times and named time zones converted to your local time | Alarms, attendees and attachments (ignored) |
| Times without a zone are treated as local time | |

Repeating events are expanded for a window of **60 days back to 400 days forward** from the day you sync. Network requests time out after 20 seconds.

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `No module named 'tkinter'` | Install tkinter (see Installation). |
| "The URL did not return an iCalendar feed" | Use the subscribe/export link, not the web page. |
| `HTTP 401` / `403` | The feed needs authentication. Check the token in the URL, or add a header under **Edit**. |
| `Connection problem` | Check your internet connection and the URL. |
| Class times are off by hours | Run `pip install tzdata` (Windows) and re-sync. |
| Timetable is empty | Check the week shown, that the calendar is **shown** (✔) in Sources, and that it synced (Events count > 0). |
| A classmate's classes don't appear in "Next up" | By design: it only counts calendars marked `Me`. |

---

## Project structure

`student_planner.py` is organised into these sections:

| Section | Purpose |
| --- | --- |
| iCalendar parsing | `parse_ics`, recurrence expansion, time zone handling |
| `Store` | Loads and saves the JSON data file; combines events from visible calendars |
| Network | `fetch_timetable` downloads and validates a feed |
| Free-time finder | `free_slots` computes gaps when none of the chosen events are happening |
| GUI | `FormDialog` and `PlannerApp` with the four tabs |

---

## Ideas for future improvements

- Add manual events (for study sessions you plan yourself).
- Export the shared free-time list as an `.ics` invite.
- Month view and daily reminders.
- Support for feeds behind a login.
