# Dynamic Demand Forecasting and Service Optimization for Public Transport

> An AI-powered system combining demand prediction, deep reinforcement learning, and fleet optimization to improve public transport efficiency, reduce travel time, and enhance passenger experience in real time.

---

## Table of Contents

* [Abstract](#abstract)
* [Problem Statement](#problem-statement)
* [Introduction](#introduction)
* [Literature Review](#literature-review)
* [Proposed System](#proposed-system)
* [Methodology](#methodology)
* [Features](#features)
* [System Architecture](#system-architecture)
* [Comparative Analysis](#comparative-analysis)
* [Limitations](#limitations)
* [Future Scope](#future-scope)
* [Conclusion](#conclusion)
* [References](#references)

---

## Abstract

Public Transport (PT) has traditionally relied on static itineraries and fixed timetables that remain unchanged for months, making them unable to respond to real-time changes in passenger demand. As autonomous mobility advances and Smart Cities take shape, PT systems must become dynamic and demand-responsive. This project addresses two critical and interconnected challenges: how accurate demand predictions must be for effective dynamic PT operation, and how bus timetables can be dynamically optimized in real time using deep reinforcement learning to respond to sudden changes in passenger flow. By synthesizing findings from both research papers, this project proposes a unified system for **Dynamic Demand Forecasting and Service Optimization** that combines stochastic demand prediction with noise-aware optimization, Deep Reinforcement Learning (DRL) for real-time timetable generation, Mixed-Integer Linear Programming (MILP) for fleet routing, and Value of Travel Time Savings (VTTS) economic evaluation.

---

## Problem Statement

Public transport systems worldwide face two compounding problems: demand-responsive PT depends on accurate demand forecasts, but prediction errors are unavoidable and current systems do not account for the shape of prediction error distributions, while existing bus timetable optimization methods operate offline — fixed in advance — and cannot adjust when actual passenger flow changes suddenly, leading to overcrowding and stranded passengers during demand surges, empty buses wasting resources during low-demand periods, and an inability to shift departure frequency in real time. There is therefore a need for a system that understands how prediction error quality affects routing decisions and dynamically adjusts dispatch decisions every minute based on real-time passenger flow, regardless of prediction model accuracy.

---

## Introduction

Public Transport has traditionally used static itineraries unchanged for months. However, as autonomous mobility advances, predictive models of transport demand are increasingly used for traffic management, and dynamic, demand-responsive routing is emerging as the next standard. More accurate demand predictions yield better utilization of PT resources — fewer vehicles used while travel times are shorter. Conversely, errors in predicted demand lead to sub-optimal routing, wasted energy, longer waiting times, and financial loss. In practice, sudden changes in passenger flow occur frequently, and a timetable fixed by any offline algorithm cannot adapt quickly enough to peak hours shifting due to events or weather, sudden surges or drops in passengers, or non-recurrent disruptions like road blocks or service cancellations. Key findings from the literature show that dynamic routing can reduce trip time by at least **23% vs. static routing**, worth an estimated **€809,000/year** in VTTS, while a Deep Reinforcement Learning-based dispatcher can save **8% of vehicles** and reduce passenger waiting time by **17%** on average compared to state-of-the-art offline methods.

---

## Literature Review

Early PT optimization depended entirely on manual survey-based demand estimates and static offline methods — genetic algorithms, mathematical programming, and heuristics — that divide a day into fixed time periods and compute timetables in advance. While these improved scheduling efficiency, they could not adapt when actual passenger flow deviated from historical patterns. Peled et al. (2021) advanced this field through a model-agnostic sensitivity analysis on 2.15 million Copenhagen PT trips, showing that prediction error *shape* — not just magnitude — determines routing quality, and that RMSNE better captures routing-critical accuracy than MAPE because it is dominated by infrequent large errors. Ai et al. (2021) took a complementary direction by formulating bus timetabling as a per-minute Markov Decision Process and training a Deep Q-Network to dispatch buses in real time, demonstrating that DRL adapts to sudden demand shifts where all offline methods fail. Together, these works reveal that the path to optimal PT lies in combining noise-aware demand forecasting with real-time reinforcement learning dispatch.

---

## Proposed System

The proposed **Dynamic Demand Forecasting and Service Optimization (DDFSO)** system integrates findings from both papers into a unified pipeline. It uses demand forecasting with awareness of noise distribution shape to inform fleet routing via MILP optimization, and uses a Deep Q-Network to decide per-minute dispatch at each control point based on real-time passenger observations. Generated routes and timetables are validated against historical worst-case demand scenarios, and performance is evaluated in both relative trip-time savings and economic VTTS terms.

---

## Methodology

Raw PT trip data from electronic travel cards is aggregated into hourly Origin-Destination (OD) trip counts, with 100 sampled hours used as Ground Truth. Stochastic noise from six distributions — Gaussian, Uniform, Exponential, Negated Exponential, Weibull, and Negated Weibull — is applied to simulate demand prediction errors, evaluated using MAPE and RMSNE.

These noisy predictions feed into a MILP formulation that minimizes fleet size, in-vehicle travel time, and waiting time under capacity and worst-case feasibility constraints. In parallel, a Deep Q-Network (DQN) agent makes per-minute depart or wait decisions at each control point, trained via experience replay with a reward function that balances capacity efficiency against passenger waiting time and stranding penalties.

---

## Features

- **Noise-Aware Demand Forecasting** — evaluates prediction quality across six noise distributions to understand how error shape affects routing quality.
- **MILP Fleet Optimization** — minimizes fleet size and total trip time across all OD pairs with capacity and historical worst-case safety constraints.
- **Real-Time DQN Dispatch** — makes per-minute departure decisions based on live passenger flow, adapting dynamically to demand shifts.
- **RMSNE-Guided Error Weighting** — prioritizes RMSNE over MAPE as the accuracy metric, since infrequent large errors disproportionately degrade routing.
- **Stranded Passenger Control** — applies a sharp DQN reward penalty whenever passengers are left behind, maintaining service quality during surges.
- **Economic Impact Quantification** — converts time savings into €/year using VTTS, providing operators with a concrete financial justification for dynamic routing.

---

## System Architecture

1. Data Input Layer
2. Demand Forecasting Module
3. MILP Fleet Optimization
4. DRL Dispatch Engine
5. Route and Timetable Output
6. Evaluation and Analytics Module

---

## Comparative Analysis

| Feature | Manual / GA / BTOA-MA | **DDFSO (Proposed)** |
|---------|----------------------|----------------------|
| Timetable Generation | Offline, fixed in advance | Real-time, per-minute DQN dispatch |
| Adaptation to Flow Changes | Cannot adapt | Adapts to peak shifts and surges |
| Demand Forecasting | Historical averages | Noise-aware with 6 distribution types |
| Stranded Passenger Control | Not modeled | Strong reward penalty |
| Economic Evaluation (VTTS) | Not measured | €/year quantification |
| Trip Time Reduction | Baseline | ≥23% vs. static routing |

---

## Limitations

- AI-generated routing decisions may degrade under highly biased or out-of-distribution demand inputs
- MILP scales poorly beyond pilot-size networks due to NP-hard complexity
- DQN performance depends on historical data quality and may underperform on new or sparse routes
- Independent noise per OD pair does not capture correlated city-wide disruptions
- Passenger route choice and mode-switching behaviour are not modeled
- Electronic card data covers only approximately one-third of all PT trips, limiting demand observability

---

## Future Scope

- [ ] Correlated OD noise modeling for city-wide disruption scenarios
- [ ] Scaling to full metropolitan PT networks beyond pilot stations
- [ ] Robust optimization with chance constraints for service failure bounding
- [ ] Bi-level formulation incorporating traveler mode-switching and bounded rationality
- [ ] Transfer learning to reduce cold-start on routes with limited history
- [ ] Cross-modal integration with metro, tram, and bike-sharing systems
- [ ] Real-time operator dashboard with stranding risk alerts

---

## Conclusion

The proposed DDFSO system addresses the full PT optimization pipeline — from noisy demand signals through noise-aware fleet routing to real-time DRL dispatch. Prediction error shape matters more than average accuracy, RMSNE is the correct metric for routing-critical evaluation, and negatively-skewed noise distributions outperform Gaussian assumptions. Dynamic routing with 40% dynamic buses achieves at least **23% trip-time reduction** and **€809,000/year** in economic savings, while real-time DRL dispatch saves **8% of vehicles** and reduces waiting time by **17%**, with near-zero stranded passengers. Together, these results establish a robust, adaptive, and economically justified framework for smart city PT deployment.

---

## References

1. On the quality requirements of demand prediction for dynamic public transport
2. Deep Reinforcement Learning based Dynamic Optimization of Bus Timetable

---

*Project: Dynamic Demand Forecasting and Service Optimization for Public Transport*
*Based on: Peled et al. (2021) · Ai et al. (2021)*
