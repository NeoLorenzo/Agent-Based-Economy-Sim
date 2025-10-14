# Agent-Based Economy Simulation

![Status](https://img.shields.io/badge/Status-Stable-brightgreen)![Python Version](https://img.shields.io/badge/Python-3.11+-blue)![Dependencies](https://img.shields.io/badge/Dependencies-Pygame_|_NumPy_|_Matplotlib-green)

An agent-based simulation designed to model a complete, closed-loop economy from the ground up. This project serves as a virtual laboratory to study how complex, macro-scale economic phenomena—such as business cycles, market equilibrium, and wealth distribution—can emerge from the simple, micro-scale, profit-driven decisions of individual agents.

The simulation now successfully models a sustainable, competitive equilibrium, avoiding the failure modes of liquidity traps and market collapse through realistic labor and market friction mechanics.

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
    *   **Behavior:** As consumers, they exhibit **bounded rationality** and **market inertia**. They do not have perfect information, instead identifying a small subset of the geographically closest firms and purchasing from the one offering the lowest price. However, they also have a configurable chance to remain **loyal** to the firm they purchased from in the previous tick, creating a more stable and realistic market. As workers, they seek to maximize their income by switching to firms that offer a sufficiently higher wage.

*   **Firms:** The producers, employers, and strategic heart of the simulation.
    *   **Goal:** Maximize long-term profit.
    *   **Behavior:** Firms operate with an adaptive AI that uses a blend of health metrics—inventory levels, sales trends, profit trends, and capital reserves—as its primary feedback signal. This AI is the engine of the simulation's emergent behavior.
        *   **Inputs for Decisions:** A firm's strategy is determined by a combination of factors: its profit trend (rising or falling), current inventory levels, smoothed historical sales data, and its available capital.
        *   **Adaptive Strategy:** The firm's decision-making process is a form of reinforcement learning; strategies that lead to increased profit are continued, while strategies that lead to falling profit are abandoned in favor of new, exploratory actions.

### The Economic Cycle (Anatomy of a Single Tick)

Each tick of the simulation proceeds through a series of phases that model the flow of money and goods:

1.  **Production Phase:**
    *   Firms produce goods based on their current number of employees (`Production = Num_Workers * Production_Per_Worker`).
    *   This production incurs a `raw_material_cost`.
    *   **Wealth Preservation:** To maintain the closed-loop system, this cost is not destroyed. The total money spent on raw materials is immediately and equally distributed to all Households as income. This is an abstraction representing household ownership of all primary economic resources (land, natural resources, etc.).

2.  **Shopping Phase:**
    *   Households first decide if they will remain loyal to their previous firm. If not, they evaluate a configured number of the nearest firms and choose to purchase from the one with the lowest price.
    *   Money is transferred from the Household's balance to the Firm's `revenue_this_tick` accumulator.

3.  **Payday & Profit Calculation Phase:**
    *   Firms pay wages to their employees. Firms that cannot afford their payroll go bankrupt, firing all employees and liquidating their assets.
    *   The firm's **profit** for the tick is then calculated using the fundamental business equation:
        `Profit = Revenue - (Wages_Paid + Raw_Material_Costs)`
    *   This profit calculation is the single most important metric that drives all subsequent firm behavior.

4.  **Firm Strategy Phase (The "Brain"):**
    *   This is the core of the agent AI. Each firm assesses its performance and decides on its strategy for the next tick. The AI synthesizes its health scores for inventory, sales, profit, and capital into strategic impulses for price and production.

    *   **The Unbreakable Law of Profitability:** After all strategic decisions are made, a final, robust rule is enforced: a firm's price is **never allowed to fall below its marginal cost of production**. This cost is calculated from the previous tick's performance (`total_costs / units_sold`). To prevent a single bad sales day from causing a catastrophic "price explosion," the system uses a stable, production-based cost as a fallback if the calculated unit cost is determined to be an unrealistic outlier.

5.  **Labor Market Phase:**
    *   Firms execute the hiring and firing strategy decided in the previous phase.
    *   **Strategic Layoffs:** If a firm's new `target_num_workers` is lower than its current workforce, it will lay off the surplus employees.
    *   **Hiring (with Friction):** If a firm is profitable and its target is higher than its current workforce, it will attempt to hire new employees. However, hiring is subject to **labor market friction**. A firm cannot instantly hire the entire unemployed population; instead, it can only recruit from a limited, randomly sampled subset of available workers each tick, modeling the real-world costs and time involved in recruitment.
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
| **Labor Market Friction** | Hiring is not instantaneous. Firms can only recruit a limited percentage of the unemployed pool each tick, modeling search costs and preventing volatile mass-hiring events. |
| **Customer Loyalty / Inertia** | Households have a chance to remain loyal to their previous firm, even if it's not the absolute cheapest. This softens perfect price competition and allows for more stable profit margins. |
| **Capital Constraints** | Firms are limited by their balance. They cannot pay wages they don't have, leading to bankruptcy. Hiring plans are constrained by a budget for expansion. |
| **Inventory Management** | Firms adjust production targets based on maintaining an optimal inventory level relative to a moving average of sales, a common real-world business practice. |
| **Bounded Rationality** | Households make decisions based on limited, local information (nearest firms) rather than having perfect knowledge of the entire market. |
| **Unemployment** | Unemployment is not a fixed parameter but an emergent property of the system, rising during recessions (layoffs) and falling during booms (hiring). |

### Current Abstractions & Unrealistic Elements

To manage complexity and focus on core economic interactions, the simulation makes several simplifying abstractions.

| Abstraction / Simplification | Description & Implication |
| :--- | :--- |
| **No Government or Central Bank** | The economy operates without taxes, public spending, regulation, or monetary policy. This creates a pure free-market environment. |
| **Single Homogeneous Good** | All firms produce and sell the exact same product. There is no product differentiation, quality variation, or brand loyalty. Competition is based primarily on price. |
| **Simplified Banking** | A bank exists to service debt, but the model for loan issuance is disabled. There is no credit creation, fractional reserve banking, or complex financial instruments. Firms cannot easily acquire capital for expansion beyond their profits. |
| **Instantaneous Processes** | While the labor market now has friction, other processes like production, sales, and payments occur instantly within a single tick. There are no time lags for manufacturing or shipping. |
| **Abstract Geography** | Agents have positions in a 2D space for proximity calculations, but there are no explicit transportation costs, supply chains, or resource locations. |
| **Perfect Resource Distribution** | The "money leak patch" that redistributes raw material costs to households is a significant abstraction. It models household ownership of all resources but does so with perfect, instantaneous, and equal distribution. |
| **Static Population & Skills** | The number of households is fixed. There is no population growth, migration, or variation in worker skill, productivity, or education. |

---

### Emergent Economic Behaviors

The interaction of these systems produces a robust, multi-stage economic narrative:

1.  **The Initial Boom:** The simulation begins with an economic expansion. Firms hire to meet untapped demand, creating a virtuous cycle of wage growth and consumption that drives up capital.

2.  **Market Saturation & Competition:** The economy reaches a peak where supply meets demand. The firms' AI correctly identifies the shift and transitions from an expansionary strategy to a competitive one.

3.  **The Stable Equilibrium:** The simulation now successfully avoids a total collapse. The combination of labor market friction and customer loyalty prevents a single firm from monopolizing the market or triggering a death spiral. The economy settles into a dynamic, sustainable equilibrium where firms actively compete for market share and labor, leading to stable prices, low unemployment, and a continuous circulation of wealth between the household and firm sectors.

<br>

<details>
<summary><strong>Core Development Philosophy</strong></summary>

*   **Configuration Separation:** Static app constants (`constants.py`) are kept separate from dynamic experiment parameters (`config.json`).
*   **Modularity (SOLID):** The codebase is highly modular with a clean separation of concerns to ensure maintainability.
*   **Determinism:** All simulation runs are fully reproducible from a single master seed.
*   **Incremental & Testable Development:** New features are added incrementally, each beginning with a testable hypothesis.
*   **Documented Abstractions:** When real-world processes are simplified, the assumptions and limitations are explicitly documented.

</details>

## Roadmap & Future Work

The simulation's previous primary challenge, a systemic collapse into a **liquidity trap**, has been solved. The introduction of realistic market frictions has created a stable, circulating economy. However, this stability has revealed a new, more nuanced emergent behavior: the economy settles into a state of **perfect competition**, where firms are locked in a "race-to-the-bottom" price war, selling goods at or near their marginal cost of production. This limits profitability and prevents long-term growth and capital accumulation.

The central aim of future development is to introduce mechanisms that allow firms to **escape perfect competition** and develop more complex strategies. This will be achieved through two complementary strategies:

1.  **Developing a Realistic Supply Chain:** The raw material abstraction will be replaced with an ecosystem of specialized firms. The hypothesis is that creating a robust business-to-business (B2B) economy will force firms to differentiate themselves not just on price, but on the quality and cost of their inputs. This will create opportunities for vertical integration and strategic sourcing, breaking the price war.

2.  **Introducing Product Differentiation & a Luxury Sector:** To combat both the price war and wealth stagnation, new classes of goods will be introduced. This allows firms to target different market segments. A firm could choose to produce a low-cost "mass market" good or a high-cost, high-margin "luxury" good. This creates a "wealth sink" for the richest agents and allows firms to develop brand strategies beyond simple price adjustments, leading to a more diverse and realistic market structure.

Potential new firm types to be implemented include:

*   **Primary Producers:** Firms that extract raw materials (e.g., **Mines, Farms, Lumber Mills**), forming the base of the supply chain.
*   **Intermediate Goods Producers:** Firms that process raw materials into components (e.g., **Smelters, Refineries, Weavers**), selling exclusively to other businesses.
*   **Capital Goods Producers:** Firms that build the "machinery" other firms need to operate (e.g., **Tool & Die Shops, Factory Constructors**), introducing capital investment and depreciation.
*   **Energy Producers:** A utility firm that sells a necessary input (energy) to all other firms and households, creating a constant B2B and B2C cost.
*   **Luxury Sector Firms:** Businesses that cater exclusively to high-wealth households, such as **Artisan Workshops** (producing high-cost goods) or **High-End Service Providers** (entertainment, bespoke services).