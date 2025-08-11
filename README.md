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
*   `simulation.py`: Contains the core simulation logic, including the `Household` and `Firm` agent classes and the main `Simulation` engine that manages the world state.
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
    *   **Abstraction:** In each tick, households choose which firm to purchase from based on geographic proximity. The simulation calculates the closest firm to each household, and the household shops there exclusively. This introduces a basic, yet realistic, constraint to consumer choice.
    *   **Configuration:** This behavior is controlled by the `enable_proximity_choice` flag in `config.json`. If set to `false`, the simulation reverts to the legacy model where households choose a firm completely at random.
    *   **Limitation:** While more realistic than random choice, this model still lacks more advanced decision-making factors like price comparison, firm reputation, or product differentiation.

2.  **Labor Market:**
    *   **Abstraction:** At the start of the simulation, each household is assigned to a single firm as its permanent employer.
    *   **Limitation:** There is no concept of a labor market. Households cannot be unemployed, switch jobs, or negotiate wages. Firms cannot hire or fire workers based on their needs.

3.  **Firm Production & Inventory:**
    *   **Abstraction:** Firms do not produce goods or manage inventory. They can sell an infinite quantity of their product. Their only economic activities are receiving payments and paying wages.
    *   **Limitation:** This means firms cannot go bankrupt due to a lack of sales, nor can they fail to meet demand. Profitability is not linked to production efficiency or cost management.

4.  **Static Economic Variables:**
    *   **Abstraction:** Key economic variables—specifically the price of goods (`p`) and the proportion of revenue paid as wages (`wage_rate`)—are static values set in `config.json`.
    *   **Limitation:** The model lacks any mechanism for price discovery or wage negotiation. The economy cannot self-regulate in response to supply and demand pressures.