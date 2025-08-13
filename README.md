# Agent-Based Economy Simulation

![Status](https://img.shields.io/badge/Status-Unstable-red)
![Python Version](https://img.shields.io/badge/Python-3.11+-blue)
![Dependencies](https://img.shields.io/badge/Dependencies-Pygame_|_NumPy_|_Matplotlib-green)

An agent-based simulation designed to model emergent economic behaviors from the ground up, following a strict, incremental, and testable development methodology.

---

> ### **WARNING: CURRENTLY UNSTABLE**
>
> The simulation is in a state of economic collapse due to unbalanced feedback loops. This is the top priority to resolve.
>
> *   **Runaway Debt & Wages:** Firms use unlimited, risk-free loans to fund hyper-inflationary wage competition.
> *   **Inventory Hoarding:** Production, funded by debt, outpaces sales, leading to ever-growing inventory.
> *   **Price Collapse:** The massive inventory surplus creates constant downward pressure, causing prices to trend towards zero.

---

## Getting Started

### Installation & Execution

1.  **Prerequisites:** Ensure you have Python 3.11+ installed.
2.  **Dependencies:** Install the required libraries.
    ```bash
    pip install pygame numpy matplotlib
    ```
3.  **Configuration:** Modify `config.json` to define the parameters for your economic experiment.
4.  **Run Simulation:**
    ```bash
    python main.py
    ```

<details>
<summary><strong>Project File Structure</strong></summary>

| File                | Description                                                              |
| ------------------- | ------------------------------------------------------------------------ |
| `main.py`           | Main application entry point; handles the Pygame loop and visualization. |
| `simulation.py`     | The core simulation engine containing all agent and economic logic.      |
| `visualization.py`  | Handles all real-time (Pygame) and final (Matplotlib) graph rendering.    |
| `constants.py`      | Defines static, framework-level constants (e.g., colors, screen size).   |
| `config.json`       | Defines the parameters for a specific economic experiment.               |
| `logging_setup.py`  | Configures the application's logging system at startup.                  |
| `README.md`         | This file.                                                               |

</details>

---

## System Architecture & Known Limitations

The table below outlines the primary systems, their current implementation (the abstraction), and the known limitations that contribute to the simulation's instability.

| System                      | Abstraction                                                                                                                                                           | Limitation (Source of Instability)                                                                                                                            |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Market & Shopping**       | Households identify the closest firms and buy from the cheapest among them.                                                                                           | All goods are perfect substitutes. Lacks brand loyalty or quality differentiation.                                                                            |
| **Labor Market**            | A fully dynamic market. Firms hire/fire based on profitability. Employees actively switch jobs for higher pay.                                                          | Does not model skills or job search costs. The wage competition is a primary driver of the economic collapse.                                                 |
| **Production & Inventory**  | Production output is a direct function of the number of workers. Firms dynamically adjust their target inventory based on their production rate.                        | Raw materials are sourced from an infinite, fixed-price market. No supply chain constraints exist.                                                            |
| **Price & Wage Setting**    | **Prices** are set based on inventory levels (high inventory -> lower price). **Wages** are increased proactively by profitable firms or reactively when losing employees. | The wage-setting mechanism is a fixed percentage increase, which is unrealistic and fuels hyper-inflation when combined with the banking system.              |
| **Banking & Credit**        | A central bank automatically issues interest-bearing loans to any firm projected to have a payroll shortfall.                                                          | **CRITICAL:** The bank has infinite capital and performs no risk assessment. This prevents firm bankruptcy and enables unsustainable debt-fueled wage growth. |

<br>

<details>
<summary><strong>Core Development Philosophy</strong></summary>

*   **Configuration Separation:** Static app constants (`constants.py`) are kept separate from dynamic experiment parameters (`config.json`).
*   **Modularity (SOLID):** The codebase is highly modular with a clean separation of concerns to ensure maintainability.
*   **Determinism:** All simulation runs are fully reproducible from a single master seed.
*   **Incremental & Testable Development:** New features are added incrementally, each beginning with a testable hypothesis.
*   **Documented Abstractions:** When real-world processes are simplified, the assumptions and limitations are explicitly documented.

</details>