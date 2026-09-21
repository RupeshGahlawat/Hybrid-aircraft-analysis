# Contributing to AeroHybrid

Thank you for your interest in contributing to AeroHybrid. As an aerospace engineering and research-grade simulation framework, we uphold strict standards regarding physical consistency, mathematical verification, test coverage, and documentation.

---

## 1. Development Principles

1. **Physical First Principles**: Every flight dynamic, thermodynamic, or electrical model must be backed by documented physical equations, certified aircraft specifications (e.g., ATR 72-600 FCOM/EASA TCDS), or peer-reviewed literature (AIAA, SAE, IEEE).
2. **Deterministic & Verifiable**: Any machine learning surrogate or LLM analysis service must include deterministic grounding and assertion checks against physical ground truth. Zero hallucinations are tolerated in safety-critical outputs.
3. **Traceability**: Changes to requirements, simulation logic, or avionics must maintain traceability across [PRD.md](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/PRD.md), [SRS.md](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/SRS.md), [ARCHITECTURE.md](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/ARCHITECTURE.md), and [TESTING.md](file:///c:/Users/Asus/Documents/Hybrid%20aircraft%20simulation/TESTING.md).
4. **Clean Code & Testing**: All new features must include automated test cases in `tests/` and maintain 100% pass rates under `pytest`.

---

## 2. Pull Request Workflow

1. Fork the repository and create a descriptive branch:
   ```bash
   git checkout -b feat/variable-pitch-propeller-model
   ```
2. Set up the development environment:
   ```bash
   python -m pip install -r requirements.txt
   cd frontend && npm install && cd ..
   ```
3. Run the automated test suite before committing:
   ```bash
   python -m pytest tests/test_core.py -v
   ```
4. Commit using Conventional Commits:
   - `feat(...)`: New simulation feature or telemetry component
   - `fix(...)`: Bug fix in physics, calculations, or frontend
   - `docs(...)`: Specification, architecture, or model card updates
   - `test(...)`: Adding or updating test cases
5. Push to your branch and open a Pull Request with complete verification evidence.

---

## 3. Aerospace Palette Guidelines

When modifying or adding frontend components:
- Strictly adhere to the off-white laboratory clean-room aesthetic (`#F8FAFC`, `#FFFFFF`, `#0EA5E9` cyan accents, `#64748B` slate borders).
- Dark themes, high-contrast black backgrounds, and unstructured utility CSS are discouraged. Keep styling modular in pure Vanilla CSS.

---

## 4. Reporting Issues

Open an issue detailing:
- Expected physical behavior vs. observed behavior.
- Relevant flight conditions (altitude, ambient temperature, hybrid split, aircraft weight).
- Steps to reproduce or mathematical derivation of the discrepancy.
