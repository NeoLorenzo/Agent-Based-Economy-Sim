# 📈 Agent-Based Economy Simulation

![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-unstable-red.svg)

This project is an agent-based simulation designed to model an economy from the ground up. The primary goal is to achieve realistic emergent behaviors and outcomes by modeling the interactions of individual agents (Households and Firms).

---

## 🏛️ Core Principles

Development follows a strict set of rules emphasizing stability, modularity, and realism.

| Principle                       | Description                                                                                                                            |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Configuration Separation**    | Static app constants (`constants.py`) are kept separate from dynamic experiment parameters (`config.json`).                            |
| **Modularity (SOLID)**          | The codebase is highly modular, adhering to SOLID principles to ensure maintainability and extensibility.                               |
| **Determinism**                 | All simulation runs are fully reproducible, controlled by a single master seed from the configuration file.                            |
| **Incremental Development**     | New features are added incrementally, each beginning with a testable hypothesis and validation protocol to ensure stability.           |
| **Documented Abstractions**     | When real-world processes are simplified, the assumptions and limitations are explicitly documented.                                     |

---

## 📂 Project Structure

*   🐍 `main.py`: Main application entry point and visualization loop.
*   ⚙️ `simulation.py`: The core simulation engine with all agent logic.
*   🎨 `visualization.py`: Handles all Pygame and Matplotlib drawing.
*   🔩 `constants.py`: Defines static, framework-level constants.
*   📝 `config.json`: Defines parameters for a specific economic experiment.
*   📜 `logging_setup.py`: Configures the application's logging system.
*   📖 `README.md`: Project overview and documentation (this file).

---

## 🚀 How to Run

1️⃣ Ensure Python (3.11+) and the required libraries (`pygame`, `numpy`, `matplotlib`) are installed.

2️⃣ Modify the `config.json` file to set the desired parameters for the simulation run.

3️⃣ Execute the main script from your terminal:

python main.py


---

## ⚠️ Current Status & Known Issues

> **WARNING: The simulation is currently in an unstable state.** The interactions between the implemented systems lead to unrealistic and unsustainable economic outcomes. This is a priority to resolve in the next development cycle.

*   🛑 **Runaway Debt:** Firms continuously take out loans to cover rising wages without a corresponding increase in profitability, leading to infinite debt.
*   🛑 **Inventory Hoarding:** The price adjustment logic is insufficient to clear inventory. Firms continue producing while funded by loans, leading to ever-growing stockpiles.
*   🛑 **Price Collapse:** Constant downward pressure from high inventory causes prices to trend towards zero, a condition from which firms cannot recover.
*   🛑 **Unstable Labor/Wage Dynamics:** A runaway feedback loop of competitive wage increases, funded by credit, causes wage hyper-inflation that is disconnected from firm revenue.

---

## 🔬 Implemented Abstractions & Logic

This section details the current logic, including the systems contributing to the instability.

### 🛒 1. Market Mechanism
*   **Abstraction:** Households shop by first identifying a few of the closest firms, then purchasing from the cheapest among them.
*   **Limitation:** All goods are perfect substitutes. Lacks brand loyalty, quality differences, or advertising.

### 👨‍💼 2. Labor Market
*   **Abstraction:** A fully dynamic market. Firms hire/fire based on profitability and payroll needs. Employees actively switch jobs for higher wages.
*   **Limitation:** No skills, job search costs, or formal wage negotiation. Firm hiring targets are simplistic.

### 🏭 3. Firm Production & Inventory
*   **Abstraction:** Production output is a direct function of the number of employees. The `target_inventory` is now dynamic, based on the firm's current production rate.
*   **Limitation:** Raw materials are sourced from an infinite market at a fixed price. No supply chain is modeled.

### 💰 4. Price & Wage Mechanisms
*   **Price:** Firms dynamically adjust prices based on inventory levels relative to a dynamic target.
*   **Wages:** Firms increase wages proactively (if profitable) or reactively (if they lose an employee or fail to hire).
*   **Limitation:** The wage increase rate is a fixed percentage and is a primary driver of the current economic instability.

### 🏦 5. Banking and Credit
*   **Abstraction:** A central bank issues interest-bearing loans to firms that cannot cover their near-term payroll.
*   **Limitation:** The bank has infinite capital and loan approval is automatic. This prevents natural market correction (bankruptcy) and enables firms to accumulate unsustainable debt.