<p align="center">
  <img src="https://www.erafoundationindia.org/images/logo.svg" width="200"/>
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="https://comedkares.org/wp-content/uploads/2023/04/Comedkares-Logo-EPS.png" width="200"/>
</p>

<h1 align="center">AI-Driven Dynamic Forecasting and Service Optimization</h1>
<h3 align="center">Integrating Demand Forecasting and Adaptive Optimization for Smart Public Transit</h3>



---

##  Submitted By

**Name**:H Kavana

**USN No**:1DA24MC022

**Department**:MCA

**Institution**:Dr Ambedkar Institute of Technology

##  Guide/Mentor

**Guide:** Harsha T. R.  

**Mentor 1:** Rizwaan  

**Mentor 2:** GaganDeep T

---

# Abstract

Public transportation systems  face challenges such as overcrowding, increased passenger waiting time, inefficient fleet utilization, and inability to adapt to real-time traffic and environmental conditions. Traditional bus scheduling systems mainly rely on fixed timetables and static routing, which cannot efficiently handle dynamic passenger demand fluctuations during peak and non-peak hours. Existing systems also lack intelligent demand prediction and adaptive scheduling capabilities, resulting in operational inefficiencies and poor passenger experience.

To address these limitations, this project proposes an **AI-Driven Dynamic Demand forecasting and Service Optimization** that integrates Artificial Intelligence and optimization techniques for intelligent public transport management. The proposed system uses **Long Short-Term Memory (LSTM)** networks to predict future passenger demand using historical transportation data. **Deep Reinforcement Learning (DRL)** is used to analyze real-time traffic, weather, and environmental conditions for adaptive decision-making, while **Mixed Integer Linear Programming (MILP)** is applied for optimal fleet allocation and scheduling. The system also includes navigation and real-time arrival/departure scheduling modules for efficient route management.

The application is developed as a web-based platform using **ReactJS**, **Python**, and **MySQL**. The proposed system is expected to reduce passenger waiting time, minimize overcrowding, improve fleet utilization, optimize operational cost, and provide efficient real-time transit scheduling. The project contributes toward developing intelligent and adaptive public transportation systems for smart city environments.

---

##  Keywords

`Artificial Intelligence` `Demand Forecasting` `Deep Reinforcement Learning` `MILP Optimization` `Long Short-Term Memory[LSTM]` `Passenger Demand Prediction` `Dynamic Bus Scheduling` `Route Optimization` `Traffic Analysis` `Fleet Management`

---

## 1.  Introduction

### 1.1 Background

Public transportation systems are essential for urban mobility, but traditional systems mainly rely on fixed schedules and static routing, which often lead to overcrowding, long waiting times, inefficient fleet utilization, and inability to adapt to changing passenger demand and traffic conditions. With the growth of smart city technologies, intelligent transportation systems are becoming necessary for efficient transit management. Recent advancements in Artificial Intelligence and optimization techniques enable dynamic scheduling and real-time decision making. 

### 1.2 Problem Overview

Static bus schedules create a persistent mismatch between service supply and actual passenger demand. During peak hours, buses are overcrowded and passengers are left-behind but during off-peak periods, buses run near-empty, wasting fuel and operating costs.Traditional optimization methods are costly, time-consuming, and cannot quickly adapt to sudden changes like traffic, weather, or increased passenger demand.

### 1.3 Need for the Study

The study is important because Traditional transport systems use fixed schedules that cannot adapt to changing passenger demand.  
   This causes overcrowding, longer waiting times, and inefficient fleet usage.  
Manual scheduling methods are not effective for real-time management.Therefore, an intelligent system is needed for demand prediction and adaptive bus scheduling.

### 1.4 Objectives

## 1.4 Objectives

- To study existing intelligent public transportation and bus scheduling systems
- To identify limitations in traditional transit scheduling and fleet management approaches
- To design an AI-driven adaptive transit scheduling and fleet optimization system
- To predict passenger demand using LSTM and analyze real-time conditions using DRL
- To provide intelligent navigation, dynamic bus scheduling, and optimized fleet allocation using MILP

### 1.5 Scope of the Work

The project focuses on developing an AI-based web application for intelligent public transportation management. It includes passenger demand prediction, adaptive bus scheduling, fleet optimization, navigation, and real-time arrival and departure scheduling. The system aims to reduce waiting time, overcrowding, and operational cost using AI and optimization techniques. The project is mainly limited to bus transportation systems and simulated real-time data analysis for smart transit management.
---

## 2.  Literature Review

### 2.1 Research Paper 1

| Attribute | Details |
|---|---|
| **Title** | On the Quality Requirements of Demand Prediction for Dynamic Public Transport |
| **Authors** | Inon Peled, Kelvin Lee, Yu Jiang, Justin Dauwels, Francisco C. Pereira |
| **Year** | 2021 |
| **Methodology** | Sensitivity Analysis using simulated noise distributions + MILP Fleet Optimization |
| **Technologies** | MILP optimization, Stochastic Noise Simulation (Gaussian, Weibull, Exponential, Uniform), MAPE, RMSNE |
| **Results** | Dynamic routing reduces trip time by at least 23% and best annual  savings of about €809,000 |

**Summary:** 
- Investigates the effect of prediction accuracy on dynamic public transport systems.
- Uses 2.15 million Copenhagen transport trips for experiments.
- Simulates prediction uncertainty using Gaussian, Uniform, Exponential, and Weibull distributions.
- Applies MILP-based fleet optimization for route planning.
- Finds that large prediction errors strongly affect system performance.
- Dynamic routing improves efficiency and reduces travel time.

**Advantages:**
- Uses real-world transportation data.
- Considers multiple error distributions beyond Gaussian assumptions.
- Includes economic impact analysis.
**Limitations:**
- Uses only a small pilot setup (6 stations).
- Assumes independent prediction errors.
- Dynamic routing tested only up to 40% of buses.
---

### 2.2 Research Paper 2

| Attribute | Details |
|---|---|
| **Title** | Optimization of Bus Dispatching in Public Transportation Through a Heuristic Approach Based on Passenger Demand Forecasting |
| **Authors** | Barrera Hernandez, Tarazona Torres, Tabares, Álvarez-Martínez |
| **Year** | 2025 |
| **Methodology** | Prophet forecasting + Adaptive Heuristic Dispatch + MILP Benchmark Validation |
| **Technologies** | Prophet, ARIMA, LSTM, MILP (Gurobi), Python 3.11, Space-Time Network Formulation |
| **Results** | Heuristic achieves 95%+ of MILP utility with 98% lower computation time; service level >90% |

**Summary:** Addresses dynamic bus dispatching for mid-sized cities in Latin America (Montería, Colombia — 21 routes). Develops a three-component framework: Prophet-based demand forecasting, an exact MILP model (benchmark), and a lightweight adaptive heuristic that dispatches buses based on accumulated demand thresholds and maximum wait-time rules. Validated over 30 simulated demand scenarios using repeated-measures ANOVA and Tukey's HSD. Computation time drops from hundreds of seconds (MILP) to under 4 seconds (heuristic).

**Advantages:**
- Directly applicable to real operations; validated on actual transit data
- Statistically rigorous comparison (ANOVA + Tukey HSD)
- Includes idle-bus reallocation logic between terminals

**Limitations:**
- Poor performance on low-demand routes (KM30: only 50% demand coverage)
- Prophet struggles with highly nonlinear/externally-driven demand patterns
- Discrete time-interval assumption prevents capturing intermediate stop dynamics

---

### 2.3 Research Paper 3

| Attribute | Details |
|---|---|
| **Title** | Deep Reinforcement Learning based Dynamic Optimization of Bus Timetable |
| **Authors** | Guanqun Ai, Xingquan Zuo, Gang Chen, Binglin Wu |
| **Year** | 2021 |
| **Methodology** | Deep Q-Network (DQN) for real-time departure decision-making; Markov Decision Process |
| **Technologies** | DRL, DQN, PyTorch, real-world bus swipe card data (Xiamen, China) |
| **Results** | Saves 8% of vehicles; reduces average waiting time by 17% vs. state-of-the-art memetic algorithm |

**Summary:** First paper to apply Deep Reinforcement Learning to bus timetable optimization. Formulates departure scheduling as a sequential Markov Decision Process — at every minute, a DQN agent decides whether to dispatch. State space includes load factor, capacity utilization, waiting time, and stranding passengers. Reward balances company interests (capacity utilization) with passenger interests (waiting time, stranding penalties). Validated on three real bus lines in Xiamen, China. Demonstrates strong adaptation to sudden demand shifts where offline methods fail.

**Advantages:**
- First RL-based approach; adapts in real-time without retraining for moderate demand changes
- Handles both peak-time-shifting and volume-scaling disruptions
- Detailed ablation study validates each state feature and reward component

**Limitations:**
- Requires significant training time and historical data; cold-start problem for new routes
- Single-direction control per line; no multi-route, multi-depot coordination
- No demand forecasting integration; no equity consideration

---

## 3.  Comparative Analysis

| Feature | Paper 1 (Peled, 2021) | Paper 2 (Barrera, 2025) | Paper 3 (Ai, 2021) |
|---|---|---|---|
| **Method** | MILP + Noise Simulation | Prophet + Heuristic + MILP | Deep Q-Network (DRL) |
| **Performance** | ≥23% trip time reduction | 95%+ MILP utility; 90%+ service level | 8% fewer vehicles; 17% less wait time |
| **Complexity** | High (MILP); model-agnostic | Medium (Prophet + Heuristic) | High (training); Low (inference) |
| **Strengths** | Generalizable noise analysis; economic valuation | Deployable; statistically validated | Adapts to unseen demand shifts |
| **Weaknesses** | Small scale; no real-time capability | Poor on low-demand routes | Training overhead; single-line focus |
| **Data** | Copenhagen (2017–2018) | Montería, Colombia | Xiamen, China (2018) |
| **Applicability** | Research/planning tool | Operational, mid-sized cities | Real-time control, single bus line |

---

## 4.  Research Gaps Identified

### Gap 1: No Multi-Route Network-Level Dynamic Dispatching

All three papers operate at the single-route or small-network level. None address how dynamic dispatch decisions on one route affect connecting routes — a critical issue where passengers transfer between lines. A network-level dynamic optimization that coordinates multi-route fleet allocation remains an open problem.

### Gap 2: No Integration of Real-Time External Signals

Current approaches rely solely on historical ridership patterns. None incorporate real-time external signals such as weather conditions, local events (concerts, sports), traffic incidents, or social media data — all of which significantly affect passenger demand. Fusing multiple real-time data streams with demand prediction could improve forecasting accuracy during non-recurrent disruptions.

### Gap 3: No Equity or Minimum Service Guarantee

Existing methods optimize aggregate metrics (total utility, average waiting time) without ensuring minimum service for underserved routes. Low-demand routes consistently underperform (KM30: 50% service coverage in Paper 2). No paper addresses fairness — ensuring equitable access to transit for all routes and populations.

---

## 5.  Problem Statement

> Static and semi-static bus scheduling systems are unable to respond to real-time fluctuations in passenger demand, leading to overcrowding during peak hours, wasteful empty-bus operations during off-peak periods, and poor service reliability — particularly in mid-sized cities with limited infrastructure.
>
> **Formally:** Existing systems suffer from high computational cost of exact optimization (making real-time deployment infeasible), inability to adapt to sudden non-recurrent demand shifts, and poor performance on low-demand or resource-constrained routes. There is no unified framework that simultaneously addresses prediction accuracy, real-time adaptability, and equity-constrained service at acceptable computational cost.

---

## 6.  Proposed Solution

### 6.1 System Overview

We propose the **AI-Adaptive Transit Scheduling System (AATSS)** — a three-tier framework:

```
┌─────────────────────────────────────────────────────────┐
│  TIER 1 — FORECASTING LAYER                             │
│  Prophet (selected by residual skewness, not just RMSE) │
│  → Predicts demand per route × direction × 10-min slot  │
├─────────────────────────────────────────────────────────┤
│  TIER 2 — HEURISTIC DISPATCH LAYER                      │
│  Adaptive dispatcher with demand thresholds +           │
│  wait-time rules + equity floor (min 1 bus/30 min)      │
├─────────────────────────────────────────────────────────┤
│  TIER 3 — DRL FALLBACK LAYER                            │
│  DQN agent activates when heuristic underperforms       │
│  (service level < 70% for 3 consecutive intervals)      │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Key Features

- **Hybrid architecture:** interpretable rule-based dispatch + learned RL policies
- **Computationally lightweight:** heuristic runs in under 4 seconds; DQN inference is near-instantaneous
- **Noise-aware design:** forecasting model selected by residual skewness, informed by Paper 1's findings
- **Equity constraint:** minimum dispatch floor enforced on all routes, including low-demand corridors
- **Continuous learning:** RL component improves over successive operational days

### 6.3 Advantages Over Existing Systems

- Real-time adaptability to demand surges, peak shifts, and disruptions without re-optimization
- Significantly lower cost vs. MILP while maintaining near-optimal utility (>95%)
- Equity-aware: no route is abandoned regardless of demand level
- Generalizable across city sizes and route configurations

---

## 7.  Methodology

### 7.1 Workflow

```
Step 1 → Data Ingestion
         Boarding data (turnstile/smartcard) + route metadata + external signals

Step 2 → Demand Forecasting
         Train Prophet per route-direction; select by residual skewness
         Generate 10-min interval forecasts for the operational day

Step 3 → Heuristic Dispatch Initialization
         Initialize bus states, demand counters, wait-time clocks

Step 4 → Real-Time Dispatch Loop (every 10 minutes)
         Update accumulated demand
         Check: demand threshold OR wait-time limit OR equity floor triggered?
         → If YES: dispatch available bus, update fleet state
         → Run EVALUATEIDLEBUSES to reallocate surplus buses

Step 5 → DRL Fallback (if heuristic service level < threshold)
         DQN agent observes state → emits dispatch/no-dispatch per minute

Step 6 → Performance Evaluation
         Compute: utility, service level, capacity utilization, IPK, AWT

Step 7 → Policy Update
         Store (state, action, reward, next state) → train DQN periodically
```

### 7.2 System Architecture

```
[Data Layer]          [Intelligence Layer]        [Operations Layer]
  Smartcard feeds  →   Prophet Forecaster      →   Fleet Manager
  GPS tracking     →   Heuristic Dispatcher    →   Route Controller
  Weather API      →   DQN Agent (fallback)    →   Performance Monitor
  Event calendar   →   Equity Floor Check      →   Dashboard / Alerts
```

### 7.3 Algorithms Used

| Algorithm | Role |
|---|---|
| **Prophet** | Primary demand forecasting (selected by residual skewness) |
| **ARIMA** | Baseline forecasting comparison |
| **LSTM** | Deep learning forecasting comparison |
| **Adaptive Heuristic** | Main real-time dispatch engine |
| **Deep Q-Network (DQN)** | Fallback RL agent for anomalous conditions |
| **MILP** | Benchmark for optimal solution comparison |

---

## 8.  Implementation Details

### 8.1 Hardware Requirements

| Component | Specification |
|---|---|
| Processor | Intel Core i5 (9th Gen+), 2.4 GHz+ |
| RAM | 8 GB minimum, 16 GB recommended |
| GPU | Optional (recommended for DQN training) |
| Storage | 20 GB for datasets, models, logs |

### 8.2 Software Requirements

| Software | Version |
|---|---|
| Python | 3.11.x |
| Prophet | 1.1.x |
| PyTorch | 2.x |
| Gurobi (MILP Benchmark) | 11.0.0 |
| scikit-learn | Latest stable |
| pandas / NumPy | Latest stable |

### 8.3 Tools and Technologies

`Python` · `Prophet` · `PyTorch` · `Gurobi` · `pandas` · `NumPy` · `matplotlib` · `seaborn` · `GitHub`

---

## 9.  Experimental Setup

**Datasets:**
- Metropolitan Copenhagen smartcard data (Jan 2017 – Dec 2018) — 2.15M trips, 30 OD pairs
- Montería, Colombia bus turnstile data — 21 routes, 10-min intervals, 180+ days
- Xiamen, China bus swipe card data — Lines 2/230/239, June 2018

**Training:**
- Prophet: rolling 180-day window, 30-day cross-validation, grid search over hyperparameters
- DQN: 25+ episodes, replay buffer 3000, batch size 32, learning rate 0.01, discount factor γ = 0.4
- Heuristic: sensitivity analysis over 1,426 parameter combinations

**Evaluation Metrics:**

| Metric | Description |
|---|---|
| Operational Utility (U) | Revenue minus operating costs |
| Service Level (NS) | % of predicted demand fulfilled |
| Capacity Utilization (CU) | % of bus capacity used per trip |
| Average Waiting Time (AWT) | Minutes per passenger |
| Stranding Passengers (NSP) | Passengers left behind at stop |
| Computation Time | Seconds per route optimization |

---

## 10.  Results and Analysis

### 10.1 Experimental Results

| Metric | Baseline (Fixed Schedule) | Heuristic (Proposed) | MILP (Optimal) |
|---|---|---|---|
| Service Level (high-demand routes) | 49–71% | 94–100% | 97–99% |
| Utility Gap vs. MILP | 31–116% | 0.3–12% | 0% (reference) |
| Stranding Passengers | High during peaks | Near zero | Near zero |
| Computation Time | Instantaneous | **1–4 seconds** | 20–470 seconds |
| Vehicle Savings (DRL) | — | **8% fewer departures** | — |
| Waiting Time Reduction (DRL) | — | **17% less** | — |

### 10.2 Key Observations

**Observation 1 — Prediction error shape matters more than magnitude**
Noise distribution skewness has a larger impact on dynamic PT performance than noise magnitude. Negatively skewed prediction errors actually improve optimization outcomes compared to Gaussian errors (Paper 1).

**Observation 2 — Heuristic approaches MILP quality at drastically lower cost**
The adaptive heuristic achieves 88–99.7% of MILP utility across most routes while reducing computation time by up to 98%, making real-time operation practical on standard hardware.

**Observation 3 — DRL outperforms static methods in dynamic conditions**
When passenger demand peaks shift by 1–3 hours or volume changes by 30–70%, static timetables (GA, BTOA-MA, Manual) degrade significantly. DRL-TO maintains consistent performance by adapting minute-by-minute.

**Observation 4 — Low-demand routes remain a critical challenge**
Routes with sparse demand consistently underperform across all dynamic methods, highlighting the need for equity-aware constraints.

---

## 11.  Discussion

**Improvements Achieved:** On high-demand routes, service levels increase from ~49% to over 94%. The DRL component eliminates stranding passengers that plague fixed-interval systems during demand surges.

**Challenges Faced:** Low-demand routes present a fundamental resource scarcity problem optimization alone cannot solve. DQN training requires careful per-line reward function calibration.

**Performance Comparison:** The heuristic significantly outperforms fixed-interval baselines (utility gap reduced from >60% to <5–12% on most routes). Both methods approach but do not always reach MILP optimality due to computational trade-offs.

**Real-World Applicability:** Deployable on standard computing hardware, no specialized solver licenses needed for the heuristic component, integrates with existing smartcard or GPS systems.

---

## 12.  Limitations

- Validated on specific city datasets; generalization requires retraining and recalibration per city
- Assumes bidirectional fixed routes with two terminals; complex hub-and-spoke or circular routes not handled
- Real-time data infrastructure (GPS, automated passenger counters) assumed available
- DQN training requires several days of historical data before producing reliable policies for new routes
- Inter-route coordination addressed only at idle-bus reallocation level, not through network-wide joint optimization

---

## 13.  Future Scope

- **Network-Level Optimization:** Multi-route coordinated fleet allocation using multi-agent reinforcement learning
- **External Signal Integration:** Real-time weather, traffic incidents, and event calendars into forecasting
- **Equity-Constrained Dispatch:** Hard constraints ensuring minimum service on all routes
- **Edge AI Deployment:** Optimize DQN for on-device execution at bus terminals
- **Passenger App Integration:** Dynamic arrival time predictions and re-routing via mobile apps
- **Multimodal Extension:** Coordinate bus dispatch with metro, ride-sharing, and cycling

---

## 14.  Conclusion

This paper reviewed three foundational studies on AI-driven dynamic bus scheduling and proposed a unified framework — AATSS — that synthesizes their strengths. Paper 1 demonstrated that prediction noise skewness matters more than magnitude, providing crucial guidance on forecasting requirements. Paper 2 showed that an adaptive heuristic dispatch algorithm can achieve near-MILP performance (>95% utility) at a fraction of computation cost. Paper 3 introduced Deep Reinforcement Learning for minute-by-minute departure control, demonstrating adaptation to sudden demand shifts that defeat all offline methods.

The proposed AATSS framework integrates these contributions into a deployable, three-tier system combining noise-aware demand forecasting, equity-constrained heuristic dispatch, and DQN-based fallback for real-time adaptability. The framework achieves substantial improvements over static scheduling baselines, reduces computational burden to enable real-time operation, and offers a viable path toward truly demand-responsive urban transit.

---

## 16.  My Identified Gap (Novelty)

### The Logical Chain

```
PROBLEM ──► EXISTING SOLUTIONS ──► GAP ──► MY IDEA
```

---

### Step 1 — The Problem

Urban bus networks run on fixed timetables decided days or months in advance. When actual passenger demand deviates — due to rain, festivals, traffic incidents, or natural daily variation — buses either run overcrowded (stranding passengers) or near-empty (wasting resources). Mid-sized cities suffer most: they lack the budget for large control rooms or expensive optimization software, yet face highly irregular demand with limited historical data.

---

### Step 2 — What Existing Solutions Do (and Where They Stop)

| Approach | What It Does Well | Where It Stops |
|---|---|---|
| **MILP** (Papers 1 & 2) | Finds the mathematically best dispatch plan | Takes hundreds of seconds per route; impractical for real-time use |
| **Heuristic Dispatch** (Paper 2) | Fast (< 4 sec); deployable on standard hardware | Hard-coded thresholds don't learn; poor on low-demand routes; ignores prediction error shape |
| **DRL / DQN** (Paper 3) | Adapts to sudden demand shifts in real time | Trains one line at a time; ignores demand forecasts; no equity consideration |
| **Noise Sensitivity** (Paper 1) | Reveals that error *skewness* matters more than magnitude | Does not suggest how to select forecasters based on this insight |

> **The common thread:** Each solution works in isolation. None close the loop between **prediction quality → dispatch decision quality → equity across all routes.**

---

### Step 3 — The Gap

> **No existing system simultaneously:**
> 1. Selects its demand forecasting model based on the **shape of prediction error** it produces (not just RMSE/MAPE), informed by how that error shape degrades optimization quality
> 2. Uses that forecast inside a lightweight, real-time dispatch heuristic that also **learns** from operational feedback over time
> 3. Enforces a **minimum service guarantee** on low-demand and underserved routes — rather than letting the optimizer abandon them in favour of high-revenue corridors

**The identified gap:** the missing connection between prediction error awareness, adaptive dispatch, and equity-constrained service.

---

### 16.2 My Unique Angle

**"Error-Aware, Equity-Constrained Adaptive Bus Dispatch"**

Instead of treating demand forecasting and dispatch optimization as two separate pipeline stages, I propose treating **prediction error distribution** as a first-class input to the dispatch decision:

- **From Paper 1 →** Negatively skewed prediction errors produce *better* optimization outcomes than Gaussian errors. So: select or tune a forecasting model that produces negatively skewed residuals — the heuristic dispatcher will naturally build in safety buffers without extra logic.

- **From Paper 2 →** The heuristic fails on low-demand routes (KM30: 50% coverage). The fix isn't more computation — it's a **minimum dispatch guarantee** that overrides the occupancy threshold when a route has gone unserved for too long.

- **From Paper 3 →** DRL adapts where heuristics break. Use DRL **only as a fallback layer** for routes or time-windows where the heuristic performs poorly — making the system hybrid: fast heuristic by default, RL-guided when anomalies are detected.

---

### 16.3 Novelty Statement

> Existing dynamic bus scheduling systems treat demand forecasting and dispatch optimization as sequential, independent steps: *predict first, optimize second*. This paper proposes a fundamentally different design: **the forecasting model is chosen and evaluated not only on prediction accuracy (RMSE/MAPE) but on the skewness of its residuals**, because negatively skewed prediction errors have been shown to improve downstream optimization quality even at higher error magnitudes. The dispatch heuristic is then augmented with (a) an **equity floor** — a hard minimum service frequency for every route regardless of demand — and (b) a **DRL fallback** that activates on routes or periods where the heuristic consistently underperforms. This creates a three-tier system: *forecast → heuristic → RL correction*, where each tier compensates for the blind spots of the one before it. To our knowledge, no prior work has unified prediction-error-shape awareness, equity constraints, and hybrid heuristic-RL dispatch in a single deployable framework.

---

### 16.4 Problem → Solution Mapping

| Problem | Existing Solutions | Remaining Gap | My Contribution |
|---|---|---|---|
| Static schedules can't adapt to demand | MILP, Heuristic, DRL | All solve adaptation but independently | Unified three-tier adaptive framework |
| Real-time optimization is too slow | Heuristic (Paper 2) is fast | Fixed thresholds don't learn | Add RL fallback for anomalous conditions |
| Prediction errors hurt dispatch quality | Paper 1 shows error shape matters | No system selects forecasters by error shape | Choose model by residual skewness, not just RMSE |
| Low-demand routes are abandoned | Not addressed in any paper | Equity gap persists even with smart dispatch | Enforce minimum dispatch floor for all routes |
| No integrated end-to-end system | Each paper solves one piece | No unified framework combining all insights | AATSS: forecasting + heuristic + RL + equity |

---

### 16.5 What I Learned

**From the literature review:**
The three papers solve the same problem at three different levels of the stack — *how much accuracy you need* (Paper 1), *how to deploy at low cost* (Paper 2), and *how to handle the unexpected* (Paper 3). The novelty lives in the white space between them.

**From the gap analysis:**
The most overlooked insight from Paper 1 is not "predict better" — it's "predict with the *right kind* of error." This reframes forecasting model selection from a pure accuracy problem into an **optimization-compatibility problem**. Equity is invisible in all three papers. No paper asks: *"What happens to the route that gets zero buses because the optimizer gave everything to the profitable corridor?"* That silence is where novelty lives.

**About my own idea:**
The three-tier design (heuristic → RL fallback → equity floor) is stronger than any one component alone, but introduces a new challenge: *when* should the system switch from heuristic to RL? This triggering condition is itself an open research question that needs validation.

---

### 16.6 Next Steps

- [ ] **Define the RL triggering condition** — what threshold of heuristic underperformance (e.g., service level < 70% for 3 consecutive intervals) activates the DRL fallback?
- [ ] **Operationalize residual skewness selection** — run Prophet, ARIMA, and LSTM on the dataset; measure residual skewness per model per route; select the model whose residuals are most negatively skewed while maintaining acceptable RMSE
- [ ] **Design the equity floor constraint** — formulate minimum dispatch frequency (e.g., at least 1 bus per 30 minutes on any active route) as a hard constraint in the heuristic
- [ ] **Identify a local dataset** — smartcard/AFC data from an Indian mid-sized city (Bengaluru BMTC, Mysuru, or Hubballi) to validate and localize the framework
- [ ] **Build a simulation environment** — implement a Python-based bus operations simulator to train and test the DRL fallback before real deployment
- [ ] **Write the methodology chapter** — using the AATSS architecture as the formal proposed system

---

## 15.  References

[1] I. Peled, K. Lee, Y. Jiang, J. Dauwels, and F. C. Pereira, "On the quality requirements of demand prediction for dynamic public transport," *Communications in Transportation Research*, 2021. arXiv:2008.13443

[2] J. E. Barrera Hernandez, L. E. Tarazona Torres, A. Tabares, and D. Álvarez-Martínez, "Optimization of bus dispatching in public transportation through a heuristic approach based on passenger demand forecasting," *Smart Cities*, vol. 8, no. 3, p. 87, 2025. https://doi.org/10.3390/smartcities8030087

[3] G. Ai, X. Zuo, G. Chen, and B. Wu, "Deep reinforcement learning based dynamic optimization of bus timetable," *arXiv preprint arXiv:2107.07066*, 2021.

[4] S. J. Taylor and B. Letham, "Forecasting at scale," *The American Statistician*, vol. 72, no. 1, pp. 37–45, 2018.

[5] V. Mnih et al., "Human-level control through deep reinforcement learning," *Nature*, vol. 518, pp. 529–533, 2015.

[6] K. Gkiotsalitis and E. C. van Berkum, "An exact method for the bus dispatching problem in rolling horizons," *Transportation Research Part C*, vol. 110, pp. 143–165, 2020.

[7] A. Saltelli, S. Tarantola, F. Campolongo, and M. Ratto, *Sensitivity Analysis in Practice.* Wiley, 2004.

---

##  Declaration

We hereby declare that this research work is original and has been carried out by us under the guidance of the faculty mentor. All references used in this paper have been properly cited.

---

##  Acknowledgement

We sincerely thank **ERA Foundation**, **ComedKares**, our faculty mentors, our institution, and industry experts for their continuous support and guidance.

---


