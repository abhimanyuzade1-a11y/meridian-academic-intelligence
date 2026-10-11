# Meridian Academic Intelligence

A student results platform for organizing academic records, calculating grades, reviewing results, and understanding student performance.

## Live Demo

[Open Meridian Academic Intelligence](https://meridian-academic-intelligence.onrender.com)

> **Demo only:** The app uses sample records and does not have secure user accounts. Anyone with the public link can switch roles and edit records. Do not enter private or real student information.

## What it can do

- **Academic overview:** See overall attainment, pass rates, grade distribution, and students who may need support.
- **Student records:** Browse, search, and filter students by class.
- **Subjects and terms:** Manage subjects, academic terms, mark limits, pass marks, and grading rules.
- **Record results:** Enter marks or import them from a CSV file. Review validation messages and duplicate records before saving.
- **Calculate grades:** Automatically calculate totals, percentages, grades, pass/fail status, and an indicative GPA.
- **Review and publish:** Teachers can submit results for review. Administrators can approve and publish them. Actions appear in the audit history.
- **Rank students:** View overall rankings and subject leaders. Students with missing marks are not ranked until their results are comparable.
- **View report cards:** Review a student's subject results and grade explanations, then print or save the report as a PDF.
- **Explore analytics:** Compare class and subject performance and view results across terms.
- **Export data:** Download CSV files for use in spreadsheet software.

## Sample subjects

The current sample dataset includes:

- RPA
- Big Data
- Blockchain Technology
- DSA
- C++

The app labels its demonstration records as sample data.

## Roles in the demo

The role selector demonstrates different views:

- **Administrator:** Manage student and subject records, terms, grading rules, approvals, and publication.
- **Teacher:** Enter or import marks and submit results for review.
- **Student:** View published results and individual ranking information.

These roles are **not protected by login accounts**. The selector is for demonstrating the workflow only; it does not verify anyone's identity or prevent visitors from accessing other roles.

## Technology

- **Python** — local web server and application backend
- **SQLite** — database for students, subjects, terms, marks, and audit events
- **HTML, CSS, and JavaScript** — responsive user interface
- **Render** — hosts the public demo

The app uses Python's standard library and does not require external API keys.

## Run locally

You need Python 3.10 or newer.

1. Download or clone this repository.
2. Open a terminal in the project folder.
3. Start the app:

   ```bash
   python server.py
