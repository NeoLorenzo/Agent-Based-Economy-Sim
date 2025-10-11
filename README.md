# Agent-Based Economy Simulation

![Status](https://img.shields.io/badge/Status-Stable-brightgreen)![Python Version](https://img.shields.io/badge/Python-3.11+-blue)![Dependencies](https://img.shields.io/badge/Dependencies-Pygame_|_NumPy_|_Matplotlib-green)

An agent-based simulation designed to model a complete, closed-loop economy from the ground up. The simulation demonstrates emergent, multi-stage economic behaviors, including periods of expansion, recession, and a final, sustainable equilibrium, all driven by the profit-seeking intelligence of its firm agents.

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

## System Architecture & Economic Model

This simulation models a **closed-loop economy** with a constant money supply. Wealth is never created or destroyed, only transferred between agents. This creates a self-contained "global economy" where all actions have direct and observable consequences.

### Agent Types

*   **Households:** The consumers and labor force of the economy. Households own all primary resources and receive income from two sources: wages from firms and dividends from the sale of raw materials. Their goal is to purchase goods to meet their needs.
*   **Firms:** The producers and employers. Firms are complex agents driven by a single, overriding goal: **to maximize long-term profit.** They make strategic decisions about pricing, production, and employment to achieve this goal.

### The Economic Cycle (Anatomy of a Single Tick)

Each tick of the simulation proceeds through a series of phases that model the flow of money and goods:

1.  **Production Phase:**
    *   Firms produce goods based on their current number of employees.
    *   This production incurs a `raw_material_cost`.
    *   **Wealth Preservation:** To maintain the closed-loop system, this cost is not destroyed. The total money spent on raw materials is immediately and equally distributed to all Households as income, representing their ownership of all natural resources.

2.  **Shopping Phase:**
    *   Households evaluate a subset of the nearest firms and choose to purchase from the one with the lowest price.
    *   Money is transferred from the Household's balance to the Firm's `revenue_this_tick` accumulator.

3.  **Payday & Profit Calculation Phase:**
    *   Firms pay wages to their employees.
    *   The firm's **profit** for the tick is now calculated using the fundamental business equation:
        `Profit = Revenue - (Wages Paid + Raw Material Costs)`
    *   This profit calculation is the single most important metric that drives all subsequent firm behavior.

4.  **Firm Strategy Phase (The "Brain"):**
    *   This is the core of the agent AI. Each firm assesses its performance and decides on its strategy for the next tick. The AI operates in one of two modes:

    *   **A. "Exploitation" Mode (Normal Operations):**
        *   This is the default state when profit is stable or growing.
        *   **Pricing:** The firm makes small, incremental price adjustments. If profit is rising, it continues its last price change (e.g., continues raising prices). If profit is stable, it uses inventory levels as a tie-breaker to fine-tune its price.
        *   **Production:** The firm sets a `target_num_workers` with the goal of producing slightly more than its recent sales volume, maintaining a small, healthy inventory buffer.

    *   **B. "Exploration" Mode (Crisis Operations):**
        *   If a firm's profit has fallen for a configured number of consecutive ticks (e.g., 5), it concludes its current strategy has failed and enters a crisis.
        *   **Pricing:** It makes a large, experimental price cut (e.g., 25%) to break out of its failing strategy and explore new market demand at a lower price point.
        *   **Production:** It aggressively slashes its `target_num_workers` to cut costs and survive the crisis.

    *   **The Unbreakable Law of Profitability:** After all strategic decisions are made, a final rule is enforced: a firm's price is **never allowed to fall below its marginal cost of production.** This prevents firms from intentionally selling goods at a loss and ensures their long-term viability.

5.  **Labor Market Phase:**
    *   Firms execute the strategy decided in the previous phase.
    *   **Strategic Layoffs:** If a firm's new `target_num_workers` is lower than its current workforce, it will immediately lay off the surplus employees.
    *   **Hiring:** If a firm is **profitable** and its target is higher than its current workforce, it will attempt to hire new employees. The profitability check prevents firms from making reckless hiring decisions while losing money.

### Emergent Economic Behaviors

The interaction of these systems produces a robust, multi-stage economic narrative:

1.  **The Initial Boom:** The simulation begins with an economic expansion. Firms hire aggressively to meet untapped demand, creating a virtuous cycle of wage growth and consumption that drives up capital and prices.

2.  **Market Saturation & Recession:** The economy inevitably reaches a peak. High prices stifle demand, and firms find their profits begin to fall. This triggers a market-wide correction. The firms' AI correctly identifies the downturn and enters a recessionary strategy: they lay off workers en masse to cut costs and slash prices to regain customers.

3.  **The Stable Equilibrium:** The recession does not lead to a total collapse. The "Law of Profitability" provides a natural floor for the price crash. At this point, firms can no longer compete on price and must instead compete on efficiency. The simulation settles into a dynamic, sustainable equilibrium where firms actively manage their smaller workforces to meet the now-stable consumer demand, ensuring their long-term profitability and survival.

<br>

<details>
<summary><strong>Core Development Philosophy</strong></summary>

*   **Configuration Separation:** Static app constants (`constants.py`) are kept separate from dynamic experiment parameters (`config.json`).
*   **Modularity (SOLID):** The codebase is highly modular with a clean separation of concerns to ensure maintainability.
*   **Determinism:** All simulation runs are fully reproducible from a single master seed.
*   **Incremental & Testable Development:** New features are added incrementally, each beginning with a testable hypothesis.
*   **Documented Abstractions:** When real-world processes are simplified, the assumptions and limitations are explicitly documented.

</details>