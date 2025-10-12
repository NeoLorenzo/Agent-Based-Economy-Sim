# Agent-Based Economy Simulation

![Status](https://img.shields.io/badge/Status-Stable-brightgreen)![Python Version](https://img.shields.io/badge/Python-3.11+-blue)![Dependencies](https://img.shields.io/badge/Dependencies-Pygame_|_NumPy_|_Matplotlib-green)

An agent-based simulation designed to model a complete, closed-loop economy from the ground up. This project serves as a virtual laboratory to study how complex, macro-scale economic phenomena—such as business cycles, market equilibrium, and wealth distribution—can emerge from the simple, micro-scale, profit-driven decisions of individual agents.

The simulation demonstrates emergent, multi-stage economic behaviors, including periods of expansion, recession, and a final, sustainable equilibrium, all driven by the adaptive intelligence of its firm agents.

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

This simulation models a **closed-loop economy** with a constant money supply. Wealth is never created or destroyed, only transferred between agents. This creates a self-contained "global economy" where all actions have direct and observable consequences. The central thesis is that complex economic behavior can be modeled by programming agents to follow realistic, understandable rules and constraints.

### Agent Intelligence & Decision-Making

The behavior of the economy is driven by the goals and intelligence of its two agent types:

*   **Households:** Serve as the economy's consumers and labor force.
    *   **Goal:** Fulfill consumption needs.
    *   **Behavior:** As consumers, they exhibit **bounded rationality**. They do not have perfect information about all firms in the market. Instead, they identify a small subset of the geographically closest firms and purchase from the one offering the lowest price. As workers, they seek to maximize their income by switching to firms that offer a sufficiently higher wage.

*   **Firms:** The producers, employers, and strategic heart of the simulation.
    *   **Goal:** Maximize long-term profit.
    *   **Behavior:** Firms operate with an adaptive, two-mode AI that uses profit as its primary feedback signal. This AI is the engine of the simulation's emergent behavior.
        *   **Inputs for Decisions:** A firm's strategy is determined by a combination of factors: its profit trend (rising or falling), current inventory levels, smoothed historical sales data, and its available capital.
        *   **Adaptive Strategy:** The firm's decision-making process is a form of reinforcement learning; strategies that lead to increased profit are continued, while strategies that lead to falling profit are abandoned in favor of new, exploratory actions.

### The Economic Cycle (Anatomy of a Single Tick)

Each tick of the simulation proceeds through a series of phases that model the flow of money and goods:

1.  **Production Phase:**
    *   Firms produce goods based on their current number of employees (`Production = Num_Workers * Production_Per_Worker`).
    *   This production incurs a `raw_material_cost`.
    *   **Wealth Preservation:** To maintain the closed-loop system, this cost is not destroyed. The total money spent on raw materials is immediately and equally distributed to all Households as income. This is an abstraction representing household ownership of all primary economic resources (land, natural resources, etc.).

2.  **Shopping Phase:**
    *   Households evaluate a configured number of the nearest firms and choose to purchase from the one with the lowest price.
    *   Money is transferred from the Household's balance to the Firm's `revenue_this_tick` accumulator.

3.  **Payday & Profit Calculation Phase:**
    *   Firms pay wages to their employees. Firms that cannot afford their payroll go bankrupt, firing all employees and liquidating their assets.
    *   The firm's **profit** for the tick is then calculated using the fundamental business equation:
        `Profit = Revenue - (Wages_Paid + Raw_Material_Costs)`
    *   This profit calculation is the single most important metric that drives all subsequent firm behavior.

4.  **Firm Strategy Phase (The "Brain"):**
    *   This is the core of the agent AI. Each firm assesses its performance and decides on its strategy for the next tick. The AI operates in one of two modes:

    *   **A. "Exploitation" Mode (Normal Operations):**
        *   This is the default state when profit is stable or growing.
        *   **Pricing:** The firm makes small, incremental price adjustments. If profit is rising, it continues its last price change (e.g., continues raising prices). If profit is stable, it uses inventory levels relative to historical sales as a tie-breaker to fine-tune its price.
        *   **Production:** The firm sets a `target_num_workers` with the goal of producing enough to meet its smoothed average sales demand while maintaining a small inventory buffer. This target is constrained by a budget; a firm will not target a workforce expansion it cannot afford.

    *   **B. "Exploration" Mode (Crisis Operations):**
        *   If a firm's profit has fallen for a configured number of consecutive ticks, it concludes its current strategy has failed and enters a crisis.
        *   **Pricing:** It makes a large, experimental price cut (e.g., 25%) to break out of its failing strategy and explore new market demand at a lower price point.
        *   **Production:** It aggressively slashes its `target_num_workers` to cut costs and survive the crisis.

    *   **The Unbreakable Law of Profitability:** After all strategic decisions are made, a final rule is enforced: a firm's price is **never allowed to fall below its marginal cost of production** (`raw_material_cost + wage_per_unit`). This prevents firms from intentionally selling goods at a loss and ensures their long-term viability.

5.  **Labor Market Phase:**
    *   Firms execute the hiring and firing strategy decided in the previous phase.
    *   **Strategic Layoffs:** If a firm's new `target_num_workers` is lower than its current workforce, it will immediately lay off the surplus employees.
    *   **Hiring:** If a firm is **profitable** and its target is higher than its current workforce, it will attempt to hire new employees from the pool of unemployed households. The profitability check prevents firms from making reckless hiring decisions while losing money.
    *   **Job Switching:** Employed households will switch jobs if another firm offers a wage that is a certain percentage higher than their current wage, creating a competitive labor market.

---

### Modeling Realism: A Detailed Breakdown

The simulation strives for behavioral and procedural realism. Below are key realistic economic concepts and how they are modeled.

| Realistic Feature | How It's Modeled in the Simulation |
| :--- | :--- |
| **Profit Motive** | The core driver of all firm behavior. Price, production, and employment strategies are adjusted based on profit feedback from the previous tick. |
| **Price Dynamics** | Prices are not fixed; they emerge from the strategic decisions of firms. Firms raise prices when demand is strong (rising profits) and cut them when demand falters (falling profits). |
| **Business Cycles** | The simulation naturally produces cycles of expansion (boom) and contraction (recession) without being explicitly programmed to do so. |
| **Competitive Labor Market** | Households are not passive workers. They actively seek higher wages, forcing firms to compete for labor and influencing the market wage rate. |
| **Capital Constraints** | Firms are limited by their balance. They cannot pay wages they don't have, leading to bankruptcy. Hiring plans are constrained by a budget for expansion. |
| **Inventory Management** | Firms adjust production targets based on maintaining an optimal inventory level relative to a moving average of sales, a common real-world business practice. |
| **Bounded Rationality** | Households make decisions based on limited, local information (nearest firms) rather than having perfect knowledge of the entire market. |
| **Unemployment** | Unemployment is not a fixed parameter but an emergent property of the system, rising during recessions (layoffs) and falling during booms (hiring). |

### Current Abstractions & Unrealistic Elements

To manage complexity and focus on core economic interactions, the simulation makes several simplifying abstractions. These represent areas where the model is currently unrealistic.

| Abstraction / Simplification | Description & Implication |
| :--- | :--- |
| **No Government or Central Bank** | The economy operates without taxes, public spending, regulation, or monetary policy. This creates a pure free-market environment. |
| **Single Homogeneous Good** | All firms produce and sell the exact same product. There is no product differentiation, quality variation, or brand loyalty. Competition is based solely on price. |
| **Simplified Banking** | A bank exists to service debt, but the model for loan issuance is disabled. There is no credit creation, fractional reserve banking, or complex financial instruments. Firms cannot easily acquire capital for expansion beyond their profits. |
| **Instantaneous Processes** | Production, sales, and payments occur instantly within a single tick. There are no time lags for manufacturing, shipping, or clearing payments. |
| **Abstract Geography** | Agents have positions in a 2D space for proximity calculations, but there are no explicit transportation costs, supply chains, or resource locations. |
| **Perfect Resource Distribution** | The "money leak patch" that redistributes raw material costs to households is a significant abstraction. It models household ownership of all resources but does so with perfect, instantaneous, and equal distribution. |
| **Static Population & Skills** | The number of households is fixed. There is no population growth, migration, or variation in worker skill, productivity, or education. |

---

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