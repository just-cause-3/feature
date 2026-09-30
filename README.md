# 🎯 CAT PYQ Practice Hub (2017 - 2025)

An interactive, responsive practice and mock exam platform for official Common Admission Test (CAT) Previous Year Questions (PYQs) covering **VARC**, **DILR**, and **QA / Quant** from **2017 to 2025** (1,830+ questions).

Live on GitHub Pages: `https://<your-username>.github.io/<repo-name>/`

---

## ✨ Features

- **Complete Official PYQs (2017 - 2025)**: All slots and sections (QA, DILR, VARC).
- **Embedded Diagrams & Charts**: High-resolution diagrams, tables, and case figures with click-to-zoom support.
- **LaTeX Math Support**: Mathematical equations rendered with MathJax.
- **Interactive Practice Mode**: Immediate answer validation, score metrics (+3 / -1 / 0), and step-by-step explanatory notes.
- **2IIM Video Solutions**: Embedded YouTube solutions starting at the exact timestamp for each question.
- **40-Minute Mock Test Mode**: Authentic CAT exam simulation with countdown timer, official question palette (5 color states), and detailed scorecard.
- **Comprehensive Filters**: Filter by Section, Year, Slot, Question Type (MCQ vs TITA), and Status (Unattempted, Correct, Incorrect, Bookmarked).
- **Offline Ready**: Works directly by opening `index.html` in any browser or hosted on static hosts like GitHub Pages.

---

## 📁 Repository Structure

```text
├── index.html          # Main application page (entry point for GitHub Pages)
├── css/
│   └── app.css         # Modern design system & styles
├── js/
│   └── app.js          # Interactive application logic & state engine
├── data/
│   ├── cat_data.js     # Bundled dataset for zero-CORS offline & web loading
│   └── cat_pyqs.json   # JSON dataset of all 1,830 questions
└── images/             # All 68 diagrams, charts, and figures
```

---

## 🚀 Running Locally

You can simply open `index.html` in any modern web browser or start a local server:

```bash
# Python 3
python -m http.server 8080
```

Then visit `http://localhost:8080/index.html`.
