# Contributing to Symboisis — LLM-Powered Automated FMEA Generator

Thank you for your interest in contributing to FMEA_SupplyChain as part of the
GDG CHARUSAT Open Source Contri Sprintathon! 🎉

---

## 🚨 Contribution Rules (Strict Enforcement)

Read this section carefully before doing anything. Violations will result
in your PR being closed without review.

❌ Do NOT open PRs for issues unless you are officially assigned  
❌ PRs without a linked issue (or team number) will be closed immediately  
❌ PRs for unassigned issues will be closed without merging  
❌ Do NOT self-assign issues  
✅ Contributors may create new issues for bugs, enhancements, or documentation improvements, following the Issue Guidelines below  
✅ One issue per contributor at a time - finish and submit before picking another  
✅ Only maintainers can assign, review, and merge PRs - do not ask others to merge your PR  
✅ Every PR must include your Team Number in the description  
✅ General improvement PRs (bug fixes or enhancements outside existing issues) are allowed but reviewed strictly - you must still include your team number and clearly explain the change  

---

## 📌 Issue Policy

Contributors may create new issues for:

- Bugs
- UI/UX inconsistencies in the Streamlit dashboard
- Documentation improvements
- Feature suggestions

Before creating a new issue, check that a similar issue does not already exist.  
Use clear, descriptive titles and provide proper details.  
To work on an issue, comment on it requesting assignment (e.g., "I'd like to work on this, Team XX").  
Wait for a maintainer to officially assign you before writing any code.  
Once assigned, you must submit your PR within 3-5 days or the issue will be reassigned.  
If you're stuck or unavailable, comment on the issue so maintainers can help or reassign.  

---

## 🚀 Reporting Bugs or Proposing Improvements

If you identify:

- A functional bug in FMEA generation, risk scoring, or CLI
- A UI/UX inconsistency in the Streamlit dashboard (`app.py`)
- A documentation error across any `.md` file
- A minor or major enhancement to the pipeline
- A refactor that improves code quality or maintainability

You must create a new issue and wait for it to be approved.

---

## 📌 Important Guidelines

✅ Open a new issue describing the problem clearly and wait for maintainer acknowledgment before submitting a Pull Request.  
✅ Submit a Pull Request with a clear and structured description.  
✅ Include your Team Number in the PR description.  
✅ Clearly explain the problem and the rationale behind your proposed change.  
✅ Attach screenshots if the change affects the Streamlit dashboard UI.  

Maintainers reserve the right to close any PR that is:

- Trivial or low-effort
- Outside the intended scope
- Poorly documented
- Not aligned with repository standards

Please ensure that your contribution is meaningful, well-tested, and professionally presented.

---

## 🔐 Environment Variables & Secrets

Some issues may require environment variables (API keys, model credentials, HuggingFace tokens, etc.).

🚨 Do NOT ask for environment variables in issues or pull requests.  
🚨 Do NOT commit secrets or API keys to the repository.  
🚨 Do NOT commit your `.env` file — use `.env.example` as the template only.  

If you need environment variables to work on an assigned issue, please contact the organizers privately:

📱 WhatsApp: +91-8320699419 || +91-8347036131 || +91-9227448882  
📧 Email: charmidodiya2005@gmail.com || jadejakrishnapal04@gmail.com || aaleya2604@gmail.com  

Environment details will be shared only after the issue is officially assigned to you.

---

## 🛠 Tech Stack

This project uses:

- **Language:** Python 3.9+
- **Dashboard:** Streamlit
- **LLM Framework:** HuggingFace Transformers (Mistral / LLaMA)
- **NLP:** NLTK, spaCy
- **Data Processing:** Pandas, NumPy
- **Risk Scoring:** Custom rule-based engine in `src/risk_scoring.py`
- **Config:** YAML-based configuration via `config/config.yaml`
- **Testing:** pytest
- **Export Formats:** Excel (openpyxl), CSV, JSON

---

## ✅ Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.9 or higher
- pip (comes with Python)
- Git
- A code editor (VS Code recommended)
- 8GB RAM minimum (16GB recommended if running the LLM locally)
- GPU optional — all features work in `--no-model` rule-based mode without one

---

## 🚀 Getting Started

### Step 1: Fork the Repository

Navigate to [https://github.com/gdg-charusat/FMEA_SupplyChain](https://github.com/gdg-charusat/FMEA_SupplyChain)  
Click the **Fork** button in the top-right corner.  
This creates a copy of the repository in your GitHub account.

### Step 2: Clone Your Fork

Clone the forked repository to your local machine:
```bash
git clone https://github.com/YOUR-USERNAME/FMEA_SupplyChain.git
cd FMEA_SupplyChain
```

Replace `YOUR-USERNAME` with your GitHub username.

### Step 3: Add Upstream Remote

Add the original repository as an upstream remote to keep your fork synced:
```bash
git remote add upstream https://github.com/gdg-charusat/FMEA_SupplyChain.git
```

Verify the remotes:
```bash
git remote -v
```

You should see:

- `origin` - your fork ([https://github.com/YOUR-USERNAME/FMEA_SupplyChain.git](https://github.com/YOUR-USERNAME/FMEA_SupplyChain.git))
- `upstream` - the original repository ([https://github.com/gdg-charusat/FMEA_SupplyChain.git](https://github.com/gdg-charusat/FMEA_SupplyChain.git))

### Step 4: Create a Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 5: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 6: Download Required NLTK Data
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger')"
```

### Step 7: Set Up Environment File

Copy the example environment file and fill in your settings:

**Windows:**
```bash
copy .env.example .env
```

**Linux/Mac:**
```bash
cp .env.example .env
```

Most fields in `.env` are optional. The system works without any API keys using rule-based mode.

### Step 8: Run the App to Verify Setup
```bash
streamlit run app.py
```

Navigate to [http://localhost:8501](http://localhost:8501) in your browser. If the dashboard loads, your setup is complete.

Alternatively, test with the CLI:
```bash
python cli.py --structured FMEA.csv --output output/test.xlsx --no-model
```

### Step 9: Create a New Branch

> **IMPORTANT:** Always create a new branch for your work. Never work directly on the `main` branch.
```bash
git fetch upstream
git checkout main
git merge upstream/main
git checkout -b feature/your-feature-name
```

**Branch Naming Convention:**

- `feature/` — for new features (e.g., `feature/voice-input`)
- `fix/` — for bug fixes (e.g., `fix/rpn-calculation-error`)
- `docs/` — for documentation (e.g., `docs/update-setup-guide`)
- `style/` — for styling changes (e.g., `style/dashboard-theme`)
- `refactor/` — for code refactoring (e.g., `refactor/preprocessing-module`)
- `test/` — for adding tests (e.g., `test/risk-scoring-unit-tests`)

---

## 💻 Development Workflow

### 1. Pick an Issue

Browse the Issues page at [https://github.com/gdg-charusat/FMEA_SupplyChain/issues](https://github.com/gdg-charusat/FMEA_SupplyChain/issues)

Look for issues labelled:
- `good first issue` or `level: beginner` — for beginners
- `level: intermediate` — for intermediate contributors
- `level: advanced` — for advanced contributors

Comment on the issue with your request and team number, e.g.:
> "Hi, I'd like to work on this issue. - Team 07"

Wait to be officially assigned — do not start writing any code until a maintainer assigns you.  
Do not work on an issue already assigned to someone else.

### 2. Understand the Project Structure

Understand which module your issue touches:

- `src/preprocessing.py` — text cleaning, sentiment analysis
- `src/llm_extractor.py` — LLM-based field extraction
- `src/risk_scoring.py` — Severity, Occurrence, Detection, RPN calculation
- `src/fmea_generator.py` — main orchestration class
- `src/utils.py` — shared helper functions
- `app.py` — Streamlit dashboard
- `cli.py` — command line interface
- `mitigation_module/` — mitigation plan generation
- `config/config.yaml` — all configurable parameters

### 3. Make Your Changes

- Write clean, readable Python code
- Follow PEP 8 style guidelines
- Add docstrings to any new function you create
- Do not change unrelated files — keep your PR focused on one issue only
- Test your changes by running the app and CLI before submitting

### 4. Test Your Changes

Run the dashboard:
```bash
streamlit run app.py
```

Run the CLI with sample data:
```bash
python cli.py --structured FMEA.csv --output output/test.xlsx --no-model
```

Run the examples:
```bash
python examples.py
```

Run pytest if your issue involves `src/` modules:
```bash
python -m pytest tests/ -v
```

If your issue adds new logic, add at least one test in the `tests/` folder.

### 5. Commit Your Changes

Write clear, descriptive commit messages:
```bash
git add .
git commit -m "feat: add voice input processor to app.py"
```

**Commit Message Format:**

- `feat:` — new feature (e.g., `feat: add dark mode toggle`)
- `fix:` — bug fix (e.g., `fix: resolve RPN calculation error`)
- `docs:` — documentation changes (e.g., `docs: update setup guide`)
- `style:` — formatting or CSS changes (e.g., `style: improve dashboard theme`)
- `refactor:` — code restructuring (e.g., `refactor: simplify preprocessing logic`)
- `test:` — adding or updating tests (e.g., `test: add unit tests for risk scoring`)
- `chore:` — maintenance tasks (e.g., `chore: update requirements.txt`)

### 6. Push to Your Fork
```bash
git push origin feature/your-feature-name
```

### 7. Create a Pull Request

Go to your fork on GitHub: `https://github.com/YOUR-USERNAME/Symboisis`  
Click **"Compare & pull request"** button.  
Fill out the PR template completely:

- **Title:** Clear, descriptive title (e.g., `Add OCR document upload to dashboard`)
- **Team Number:** You must state your team number (e.g., Team 07) — PRs without this will be closed
- **Issue Reference:** Link the assigned issue (e.g., `Closes #12`) — PRs without a linked issue will be closed
- **Description:** Explain what changes you made and why
- **Screenshots:** Add before/after screenshots if dashboard UI changes are involved

Click **"Create pull request"**

---

## 📌 Issue Guidelines

### Finding Issues

Issues are categorized by difficulty level. Contributors may also create well-documented issues for valid improvements.

**🟢 Beginner Level (Good First Issues)**

- Adding docstrings to existing functions
- Fixing typos or errors in documentation
- Adding comments to config files
- Creating helper scripts like `check_requirements.py`
- Minor CLI improvements like `--version` or `--help` examples

Labels: `good first issue`, `level: beginner`

**🟡 Intermediate Level**

- Adding new input modes to `app.py` (voice, OCR, etc.)
- Building new `src/` modules with proper class structure
- Integrating existing standalone scripts into the dashboard
- Adding PDF or JSON export functionality
- Building CLI interactive modes

Labels: `level: intermediate`

**🔴 Advanced Level**

- Building dynamic supply chain simulation engines
- Fine-tuning LLM prompts with evaluation pipelines
- Architectural changes to the FMEA generation pipeline
- Multi-module integrations involving dataset analysis

Labels: `level: advanced`

---

### How to Request an Issue

Find an unassigned issue you want to work on.  
Comment on the issue with this format:

> "I'd like to work on this. - Team [your team number]"

Wait for a maintainer to assign it to you — this is mandatory.  
Once assigned, start working and submit your PR within 3–5 days.  
If you can't complete it in time, comment to let maintainers know.

⚠️ Before opening a new issue, ensure:

- The issue does not already exist
- It is clearly documented
- It aligns with the project scope (FMEA generation, supply chain risk, NLP, dashboard, CLI)

---

### Creating a New Issue

When creating a new issue:

- Use a clear and descriptive title
- Add a detailed description:
  - What is the problem or feature?
  - Which file or module does it affect?
  - Steps to reproduce (if a bug)
  - Expected vs actual behaviour
  - Screenshots (if UI-related)
- Wait for maintainer review before starting work

---

## 🔄 Pull Request Process

### PR Requirements — Non-Negotiable

PRs that don't meet **ALL** of the following will be closed without review:

- [ ] Team number stated in the PR description (e.g., Team XX)
- [ ] Linked to your assigned issue via `Closes #issue-number`
- [ ] You are the assigned contributor for that issue
- [ ] PR is raised after assignment, not before

### Before Submitting

- [ ] `streamlit run app.py` runs without errors
- [ ] `python cli.py --structured FMEA.csv --output output/test.xlsx --no-model` works
- [ ] `python -m pytest tests/` passes (or you have documented why a test was skipped)
- [ ] No new `print()` statements added to `src/` modules — use logging instead
- [ ] No secrets, API keys, or `.env` files committed
- [ ] Commit messages follow the conventional format above
- [ ] If dashboard UI was changed, before/after screenshots are in the PR

### PR Review Process

A maintainer will review your PR within 24–48 hours.  
You may be asked to make changes — respond promptly.  
Make requested changes and push to the same branch (PR auto-updates).  
Only maintainers can approve and merge — do not request peers to merge.

### Addressing Review Comments

Make the requested changes, then:
```bash
git add .
git commit -m "fix: address review comments on voice input validation"
git push origin feature/your-feature-name
```

---

## 🆘 Need Help?

- **Issue Discussion:** Comment on the issue you are working on
- **WhatsApp:** +91-8320699419 || +91-8347036131 || +91-9227448882
- **Email:** charmidodiya2005@gmail.com || jadejakrishnapal04@gmail.com || aaleya2604@gmail.com
- **Troubleshooting:** Check the FAQ section in `README.md` first

---

## 🎯 Tips for Success

**Start Small:** Begin with a beginner issue to understand how the pipeline works before touching `src/` modules.

**Run Everything First:** Before changing anything, run `streamlit run app.py` and `python examples.py` to see what the project actually does. You will understand the code far better after seeing it in action.

**Read the Guides:** This repo has detailed documentation for every major feature. `START_HERE.md`, `QUICK_REFERENCE.md`, and `YOUR_DATA_GUIDE.md` will save you hours.

**Use --no-model:** If you don't have a powerful machine, add `--no-model` to all CLI commands. The rule-based mode is fast and works for most issues without needing a GPU or large model download.

**Ask Questions:** It is better to ask than to waste time going in the wrong direction. Comment on your assigned issue and maintainers will help.

**Be Patient:** Code review takes time — be responsive to feedback when it comes.

**Have Fun:** This is about learning NLP, LLMs, supply chain analysis, and open source collaboration all at once. Enjoy it!

---

## 📜 Code of Conduct

Please be respectful and professional in all interactions. We are here to learn and help each other grow. Discrimination, harassment, or disrespectful behaviour of any kind will not be tolerated.

Happy Coding! 🚀

If you have any questions or need clarification, feel free to reach out to the maintainers or ask in the issue comments.
