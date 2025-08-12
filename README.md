# Agent-Based Economy Simulation

## Overview

This project is an agent-based simulation designed to model an economy from the ground up. The primary goal is to achieve realistic emergent behaviors and outcomes by modeling the interactions of individual agents (Households and Firms).

Development follows a strict set of rules emphasizing stability, modularity, realism, and incremental progress. Every change is deliberate, testable, and aims to move the simulation closer to a scientifically-grounded representation of real-world economic processes.

## Core Principles

The simulation is built upon several key principles:

*   **Configuration Separation:** All parameters are strictly separated.
    *   `constants.py`: For static application values (e.g., visualization settings) that do not change between experiments.
    *   `config.json`: For dynamic simulation parameters (e.g., number of agents, economic variables) that define a specific experimental run.
*   **Modularity (SOLID):** The codebase is highly modular, with a clean separation between simulation logic, visualization, and configuration. We adhere to SOLID principles to ensure the code remains maintainable and extensible.
*   **Determinism:** All simulation runs must be fully reproducible. All sources of randomness are controlled by a single master seed defined in the configuration.
*   **Incremental & Testable Development:** New features are added incrementally. Each change begins with a testable hypothesis and is validated before moving forward, ensuring stability.
*   **Documented Abstractions:** When real-world processes are too complex to model 1-to-1, we use scientifically-grounded abstractions. These simplifications and their limitations are explicitly documented here.

## Project Structure

*   `main.py`: The main application entry point. Handles Pygame initialization, the main visualization loop, and user input.
*   `simulation.py`: Contains the core simulation logic. It uses high-performance NumPy structured arrays to manage agent data (instead of individual agent objects) and a central `Simulation` class to run the tick-based world state updates.
*   `constants.py`: Defines static, framework-level constants (Rule 1.1).
*   `config.json`: Defines the parameters for a specific economic experiment (Rule 1.2).
*   `logging_setup.py`: Configures the application's logging system at startup, creating unique run directories and injecting contextual data into log messages as required by Rule 2.
*   `README.md`: This file, providing an overview and documentation of the project.

## How to Run

1.  Ensure Python (I use version 3.11.9) and the required libraries (`pygame`, `numpy`) are installed.
2.  Modify the `config.json` file to set the desired parameters for the simulation run.
3.  Execute the main script from your terminal:
    ```bash
    python main.py
    ```

## Current State & Known Abstractions (MVP - v0.1)

The current version of the simulation is a minimal viable product (MVP) designed to establish the foundational code structure. The economic model is intentionally simplistic and relies on several major abstractions that will be replaced in future iterations.

1.  **Market Mechanism:**
    *   **Abstraction:** In each tick, households exhibit a realistic, two-step shopping behavior. First, they identify a small number of the geographically closest firms (for convenience). Second, they evaluate the prices at those nearby firms and choose to shop at the one offering the lowest price. This models a consumer's trade-off between convenience and cost.
    *   **Configuration:** This behavior is controlled by the `enable_proximity_choice` flag and the `shopping_firms_to_consider` parameter in `config.json`. If `enable_proximity_choice` is `false`, the simulation reverts to a simpler model where households choose a firm completely at random.
    *   **Limitation:** This model is a significant step up from simple proximity or random choice, but it still lacks factors like brand loyalty, product quality differences, or the influence of advertising. All goods are treated as perfect substitutes.

2.  **Labor Market:**
    *   **Abstraction:** The simulation now features a dynamic labor market with a fixed wage system. All households start as unemployed. Firms can hire workers from the unemployed pool if they have sufficient capital and revenue, and will lay off workers if their capital drops too low. Each employed household receives a fixed, stable wage per tick, defined by the firm's `wage_rate`. This creates a predictable payroll expense for firms and a stable income for households.
    *   **Limitation:** The model does not yet include wage negotiation, skills, or active job-seeking behavior from households (they are hired passively). The wage rate is static and does not yet respond to labor supply and demand dynamics (i.e., a "tight" or "loose" labor market).

3.  **Firm Restocking & Inventory:**
    *   **Abstraction:** Firms act as retailers. They do not produce goods. Instead, they purchase inventory from an abstract, infinite "wholesale market" at a fixed `wholesale_price`. Each firm attempts to maintain a `target_inventory` level. If its current inventory drops below this target, it orders more goods, limited by its available cash balance.
    *   **Limitation:** The wholesale market is a simplification. It has an infinite supply and a fixed price, meaning firms do not compete for wholesale goods. A firm's `target_inventory` is static and does not yet adapt to long-term sales trends. The cost of holding inventory is not modeled.

4.  **Price & Wage Mechanisms:**
    *   **Price:** Firms now dynamically adjust the price of their goods based on inventory levels. If inventory falls below a configured threshold (signaling high demand), the firm raises its price. If inventory exceeds another threshold (signaling a surplus), it lowers the price. This behavior is controlled by `price_adjustment_rate` and inventory threshold factors in `config.json`.
    *   **Wage Abstraction:** The proportion of revenue paid as wages (`wage_rate`) remains a static value set in `config.json`.
    *   **Limitation:** While price is now dynamic, the model still lacks a true wage negotiation mechanism. Wages are a fixed percentage of revenue, and there is no labor market competition driving wages up or down.

5.  **Banking and Credit:**
    *   **Abstraction:** The simulation includes a single, centralized "Bank" agent. This bank acts as a lender of last resort to prevent premature firm bankruptcy. If a firm's cash balance is projected to be insufficient to cover its wage expenses over a configurable number of future ticks (e.g., 10 ticks), the bank automatically issues an emergency loan to that firm. The loan amount is a multiple of the projected expenses.
    *   **Limitation:** This is a highly simplified banking model. The bank has infinite capital, loans are approved automatically without risk assessment, and (for now) the loans are interest-free. The goal of this abstraction is not to model banking in detail, but to provide the necessary liquidity to prevent the economy from seizing up, allowing for more complex, long-term dynamics to emerge.