# Meridian Academic Intelligence

A local-first student results platform for marks administration, validation, review, reporting, and academic analysis. Student data stays in the workspace's SQLite database; the app makes no external API calls. The included records are clearly labeled **Sample data**.

## Run locally

Requires Python 3.10 or newer. There are no Python package installs or service credentials.

1. Open a terminal in this folder.
2. Run `python server.py` (Windows users can also use `py server.py`).
3. Open [http://localhost:8000](http://localhost:8000).

The server creates `meridian.db` in this folder the first time it runs. This database persists when the server stops or the page reloads. To start with an empty database, stop the server, delete `meridian.db`, and start it again; the sample database will be created automatically. Keep a copy of `meridian.db` to back up local records.

## Included workflows

- **Overview:** current term attainment, pass rates, grade distribution, support flags, and subject result snapshots.
- **Results:** searchable and filterable register, CSV export, mark entry, visible grade rules, and submit / return / approve / publish audit events.
- **Students, subjects, and terms:** add and edit student and subject records; configure subject maxima, pass marks, subject weights, and the A*–D percentage bands; add terms and choose the current term.
- **Import marks:** download a CSV template; upload CSV, map source columns, preview row-level validation, detect duplicate rows, identify existing marks, and import valid rows. Existing marks are updated. Invalid rows are not committed.
- **Report cards:** individual term report, subject results, grading explanation, print dialog (choose Save as PDF).
- **Analytics:** class and subject filters, term comparisons, grade distribution, subject mean/pass-rate comparisons, and students needing support.
- **Student rankings:** overall standings use complete recorded marks and average percentage; subject leaders are calculated per subject. Ties share a place, incomplete students are shown without a rank, and rankings refresh when marks change. Students see only their own position after publication.
- **Notifications and audit trail:** local event history for initialized sample data, record changes, imports, and workflow actions.

## Calculation and workflow notes

Percentage is `score / subject maximum × 100`. A* / A / B / C / D begin at 90 / 80 / 70 / 60 / 50 percent; E is at or above the subject-specific pass threshold and U is below it. The displayed GPA maps each subject percentage linearly to 0–4 across 50–100% and averages using subject weights. It is an indicative estimate, not an institutional GPA standard. Teachers can submit and return a term for correction; administrators can approve submitted results and publish approved results. The role switch is a local workflow demonstration, not an identity or authentication system. This app is intended for a single trusted local environment and is not hardened for multi-user network deployment. The Abhimanyu Zade first-place example is only applied to marks tagged as sample; marks imported or entered by a user are tagged separately and are never overwritten by that sample-data refresh.

## Local data and limitations

All student and assessment records are stored locally in SQLite. The app does not send records to external services. The interface loads DM Sans and Manrope from Google Fonts when internet access is available; system sans-serif fallbacks keep it usable offline. CSV import supports comma-delimited UTF-8 files with a header row. Spreadsheet workbooks should be exported as CSV first.
