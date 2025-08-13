# Agent-Based Economy Simulation

This project is an agent-based simulation designed to model an economy from the ground up. The primary goal is to achieve realistic emergent behaviors and outcomes by modeling the interactions of individual agents (Households and Firms).

Development follows a strict set of rules emphasizing stability, modularity, realism, and incremental progress.

---

> ### **Current Status: UNSTABLE**
>
> **WARNING:** The simulation is currently in an unstable state. The interactions between the implemented systems lead to unrealistic and unsustainable economic outcomes. This is a priority to resolve in the next development cycle.
>
> *   **Runaway Debt:** Firms continuously take out loans to cover expenses, particularly rising wages, without a corresponding increase in profitability, leading to infinite debt accumulation.
> *   **Inventory Hoarding & Price Collapse:** Firms produce more than they can sell. The resulting high inventory causes prices to trend towards zero, a condition from which they cannot recover.
> *   **Unstable Labor/Wage Dynamics:** Access to unlimited credit creates a runaway feedback loop. Firms raise wages to attract workers, funding the increase with loans, which forces other firms to do the same. This leads to wage hyper-inflation that is disconnected from actual firm revenue.

---

## Core Principles

The simulation is built upon several key principles:

*   **Configuration Separation:** All parameters are strictly separated.
    *   `constants.py`: For static application values (e.g., visualization settings).
    *   `config.json`: For dynamic simulation parameters (e.g., number of agents, economic variables).
*   **Modularity (SOLID):** The codebase is highly modular, with a clean separation of concerns. We adhere to SOLID principles to ensure the code remains maintainable and extensible.
*   **Determinism:** All simulation runs are fully reproducible. All sources of randomness are controlled by a single master seed defined in the configuration.
*   **Incremental & Testable Development:** New features are added incrementally. Each change begins with a testable hypothesis and is validated before moving forward.
*   **Documented Abstractions:** When real-world processes are too complex to model 1-to-1, we use scientifically-grounded abstractions whose limitations are explicitly documented.

---

## Getting Started

### Project Structure

*   `main.py`: The main application entry point; handles the Pygame loop.
*   `simulation.py`: The core simulation engine with all agent logic.
*   `visualization.py`: Handles all real-time and final graph rendering.
*   `constants.py`: Defines static, framework-level constants.
*   `config.json`: Defines parameters for a specific economic experiment.
*   `logging_setup.py`: Configures the application's logging system.
*   `README.md`: This file.

### How to Run

1.  Ensure Python (e.g., version 3.11+) and the required libraries (`pygame`, `numpy`, `matplotlib`) are installed.
2.  Modify `config.json` to set the desired parameters for the simulation run.
3.  Execute the main script from your terminal:
    ```bash
    python main.py
    ```

---

## System Architecture & Abstractions

This section details the current logic implemented in the simulation.

### 1. Market Mechanism
*   **Abstraction:** Households exhibit a two-step shopping behavior. They first identify a small number of the geographically closest firms (`shopping_firms_to_consider`) and then purchase from the one with the lowest price.
*   **Limitation:** All goods are treated as perfect substitutes. The model lacks factors like brand loyalty, quality differences, or advertising.

### 2. Labor Market
*   **Abstraction:** The labor market is fully dynamic. Firms hire when profitable and lay off workers when cash reserves are low. Employed households will actively switch to a different firm if it offers a sufficiently higher wage (`job_switching_wage_threshold`).
*   **Limitation:** The model does not include skills, job search costs, or formal wage negotiation.

### 3. Firm Production & Inventory
*   **Abstraction:** A firm's production output is a direct function of its number of employees (`production_per_worker`). A firm's `target_inventory` is also dynamic, calculated as a multiple of its current production rate.
*   **Limitation:** Raw materials are sourced from an abstract, infinite market at a fixed price. There is no supply chain.

### 4. Price & Wage Mechanisms
*   **Abstraction:**
    *   **Price:** Firms dynamically adjust prices based on inventory levels relative to their target. High inventory leads to lower prices; low inventory leads to higher prices.
    *   **Wages:** Firms increase wages either proactively (when profitable) or reactively (when they lose an employee or fail to hire).
*   **Limitation:** The rate of wage increase is a fixed percentage. This mechanism is a primary driver of the current economic instability.

### 5. Banking and Credit
*   **Abstraction:** A central bank provides interest-bearing loans to firms whose cash balance is projected to be insufficient to cover near-term payroll.
*   **Limitation:** The bank has effectively infinite capital and loan approval is automatic. There is no risk assessment, which allows failing firms to accumulate unsustainable debt and prevents natural market correction (i.e., bankruptcy).