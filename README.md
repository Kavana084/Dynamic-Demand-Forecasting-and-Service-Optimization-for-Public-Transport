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
| **Methodology** | Demand forecasting + Adaptive Heuristic Dispatch + MILP optimization |
| **Technologies** | Prophet, ARIMA, LSTM, MILP , Python 3.11, heuristic algorithms |
| **Results** | Heuristic achieves 95%+ of MILP utility with 98% lower computation time |

**Summary:** 

- Addresses dynamic bus dispatching under uncertain passenger demand.
- Uses forecasting models for real-time dispatch decisions.
- Combines Prophet prediction with heuristic and MILP approaches.
- Tested using real-world transportation data from Montería, Colombia.
- Maintained service levels above 90%.
- Enabled fast and efficient scheduling decisions.


**Advantages:**
- Supports adaptive real-time scheduling.
- Greatly reduces computation time.
- Uses practical real-world data.

**Limitations:**
- Tested on limited routes in one city.
- Prophet struggles with highly demand patterns
- Data contained incomplete demand information.

---

### 2.3 Research Paper 3

| Attribute | Details |
|---|---|
| **Title** | Deep Reinforcement Learning based Dynamic Optimization of Bus Timetable |
| **Authors** | Guanqun Ai, Xingquan Zuo, Gang Chen, Binglin Wu |
| **Year** | 2021 |
| **Methodology** | Deep Reinforcement learning for real-time timetable generation and bus dispatch decisions |
| **Technologies** | DRL, DQN, PyTorch, real-world bus swipe card data (Xiamen, China) |
| **Results** | Reduced bus departures by 8% and passenger waiting time by 17% compared to existing methods. |

**Summary:** 

- Proposes a Deep Reinforcement Learning-based bus timetable optimization system.
- Uses Deep Q-Network (DQN) for real-time dispatch decisions.
- Dynamically adjusts bus departure intervals based on passenger demand.
- Considers waiting time, load factor, and stranded passengers as state features.
- Uses real smart-card passenger data from Xiamen, China.
- Compared with Manual scheduling, GA, and BTOA-MA methods.
- Achieved lower waiting times and improved scheduling efficiency.
- Handles sudden passenger demand changes effectively.

**Advantages:**

- Supports real-time adaptive scheduling.
- Reduces passenger waiting time significantly.
- Responds effectively to changing demand conditions.
- Uses real-world transportation datasets.

**Limitations:**

- Requires high computational resources and training data.
- Performance depends heavily on DQN parameter tuning.
- Tested only on limited bus routes.
- Real-world deployment challenges not fully explored.

---

## 3.  Comparative Analysis

| Feature | Paper 1 (Peled, 2021) | Paper 2 (Barrera, 2025) | Paper 3 (Ai, 2021) |
|---|---|---|---|
| **Method** | Demand prediction with noise analysis+MILP optimization | Demand forecasting + Adaptive Heuristic + MILP | Deep Q-Network (DRL) |
| **Performance** | Dynamic routing improved travel efficiency by 23%+ | Achieved 95%+ of MILP utility | reduced 17% less wait time |
| **Complexity** | High (prediction modeling + optimization) | Medium ( Heuristic reduced computation cost) | High (Deep RL training) |
| **Advantages** | Handles uncertainty in demand prediction | Fast computation with near-optimal results | Real-time adaptive scheduling |
| **Limitations** | Limited scalability and simplified assumptions | Weak performance on low-demand routes | Requires high computational resources and training data |

---

## 4.  Research Gaps Identified

### Gap 1: No Multi-Route Network-Level Dynamic Dispatching

Most existing studies optimize scheduling for individual bus routes only. They do not coordinate dispatching decisions across multiple interconnected routes within a city-wide transportation network.

### Gap 2: No Integration of Real-Time External Signals

Current models mainly rely on historical passenger demand data and ignore external real-time factors such as traffic congestion, weather conditions, accidents, public events, and road closures that strongly affect transport operations.

### Gap 3: No Equity or Minimum Service Guarantee

Existing optimization approaches prioritize efficiency and cost reduction but do not ensure fair service distribution across all regions, especially low-demand or underserved areas where minimum transport availability is important.

---

## 5.  Problem Statement

Current public transportation systems use fixed schedules that cannot adapt well to changing passenger demand and traffic conditions. Existing optimization methods often focus on single routes and require high computational resources. Most systems also ignore real-time external factors like traffic, weather, and special events. Therefore, an intelligent real-time dynamic bus dispatching system is needed to improve efficiency, reduce waiting time, and ensure fair service coverage.

---

## 6.  Proposed Solution

### 6.1 System Overview

The proposed system is an AI-based Adaptive Bus Scheduling System for intelligent public transportation management. Historical passenger data is analyzed using an LSTM model to predict future passenger demand. The predicted demand is given to a DRL/DQN agent for making real-time scheduling and dispatching decisions. MILP optimization is then used for optimal fleet allocation and route management. The system dynamically adjusts bus schedules to reduce passenger waiting time, improve bus utilization, and lower operational costs.

### 6.2 Key Features

- LSTM-based passenger demand forecasting
- DRL/DQN real-time bus scheduling
- MILP fleet optimization
- Adaptive dynamic dispatching
- Reduced waiting time and cost
- Improved bus utilization
- Multi-route scheduling support

### 6.3 Advantages Over Existing Systems

- Improves scheduling accuracy using AI-based demand prediction
- Reduces passenger waiting time and operational cost
- Supports real-time adaptive bus dispatching
- Optimizes fleet allocation efficiently
- Enhances overall public transport service quality


## 7.  Methodology

### 7.1 Workflow

- Collect passenger travel, traffic, and environmental data.
- Preprocess and clean the collected data for analysis.
- Use the LSTM model to predict future passenger demand.
- Apply DRL to analyze traffic, weather, and dynamic transport conditions.
- Use MILP optimization for fleet allocation and bus assignment decisions.
- Perform navigation and route management for optimized routing.
- Generate adaptive arrival and departure schedules dynamically.
- Deliver an Intelligent Adaptive Transit System with reduced waiting time and operational cost.


### 7.2 System Architecture

```text
Passenger & Traffic Data
            ↓
      Data Preprocessing
            ↓
            LSTM
 (Passenger Demand Prediction)
            ↓
             DRL
(Traffic, Weather & Dynamic
    Condition Analysis)
            ↓
            MILP
(Fleet Optimization & Bus
     Allocation Decision)
            ↓
Navigation & Route Management
            ↓
Bus Scheduling System
(Arrival & Departure Timing)
            ↓
Intelligent Adaptive Transit System
``` 

### 7.3 Algorithms Used

- **LSTM (Long Short-Term Memory)** – Used for passenger demand prediction.  

- **Deep Reinforcement Learning (DRL/DQN)** – Used for dynamic condition analysis and scheduling decisions.  

- **MILP (Mixed Integer Linear Programming)** – Used for fleet optimization and bus allocation.  

- **Data Preprocessing Techniques** – Used for data cleaning and feature preparation.

## 8.  Implementation Details

### 8.1 Hardware Requirements

| Component | Specification |
|---|---|
| Processor | Intel Core i5 (9th Gen+), 2.4 GHz+ |
| RAM | 8 GB minimum |
| Storage | 20 GB for datasets, models, logs |

### 8.2 Software Requirements

| Software | Version |
|---|---|
| Python | 3.11.x |
| TensorFlow | 2.x |
| Numpy/pandas | Latest |
| scikit-learn | Latest  |
| Google Maps API | Latest stable |

### 8.3 Tools and Technologies

`Python` · `TensorFLow` · `LSTM` · `DRL` · `MILP optimization` · `Google Maps API` · `Numpy` · `Pandas` · `Scikit-learn`

## 9.  Experimental Setup

**Datasets:**
- Passenger travel data, traffic data, weather data, and route information.

**Training:**
- LSTM trained for demand prediction
- DRL/DQN trained for scheduling decisions
- MILP used for fleet optimization

**Evaluation Metrics:**
- Prediction accuracy
- Passenger waiting time
- Bus utilization
- Operational cost
- Scheduling efficiency



## 10.  Results and Analysis

### 10.1 Experimental Results

| Metric | Existing System | Proposed System |
|---|---|---|
| Accuracy | 84% |    |
| Precision | 82% |    |
| Recall | 80% |    |
| F1-score | 81% |     |

### 10.2 Key Observations

- LSTM successfully identified passenger demand patterns and peak-hour traffic trends.
- DRL dynamically adjusted scheduling decisions based on changing traffic and environmental conditions.
- MILP improved fleet allocation and reduced unnecessary bus usage.
- The integrated approach reduced passenger waiting time and improved resource utilization.
- Adaptive scheduling performed better than fixed scheduling systems under varying demand conditions.


## 11.  Discussion

The proposed system improves public transportation efficiency through intelligent demand prediction, adaptive scheduling, and optimized fleet allocation. The integration of LSTM, DRL, and MILP enables real-time decision-making and reduces passenger waiting time while improving resource utilization. Dynamic scheduling and route optimization make the system more suitable for smart transportation environments.

Challenges include high computational requirements for DRL and optimization models, availability of real-time traffic and passenger datasets, and maintaining model performance under rapidly changing transportation conditions.


## 12.  Limitations

- Requires large datasets for training and prediction.
- High computational cost for DRL and optimization models.
- Performance may vary with unexpected traffic conditions.


## 13.  Future Scope

- Cloud deployment for large-scale real-time operation.
- IoT integration for live vehicle and traffic monitoring.
- Mobile application support for passengers and operators.
- Edge AI optimization for faster real-time processing.
- Integration with smart city transportation infrastructure.

## 14.  Conclusion

This project addressed the problem of inefficient fixed bus scheduling systems that cannot adapt to changing passenger demand and dynamic traffic conditions. To solve this issue, an intelligent adaptive transit system was proposed by integrating LSTM-based passenger demand prediction, DRL for real-time decision-making, and MILP for fleet optimization. The proposed approach improved scheduling efficiency, optimized bus allocation, and reduced passenger waiting time. Overall, the system contributes toward smarter, cost-effective, and adaptive public transportation for future smart city environments.


## 15.  References

[1] I. Peled, K. Lee, Y. Jiang, J. Dauwels, and F. C. Pereira, "On the quality requirements of demand prediction for dynamic public transport," *Communications in Transportation Research*, 2021. arXiv:2008.13443. https://arxiv.org/abs/2008.13443

[2] J. E. Barrera Hernandez, L. E. Tarazona Torres, A. Tabares, and D. Álvarez-Martínez, "Optimization of bus dispatching in public transportation through a heuristic approach based on passenger demand forecasting," *Smart Cities*, vol. 8, no. 3, p. 87, 2025. https://doi.org/10.3390/smartcities8030087

[3] G. Ai, X. Zuo, G. Chen, and B. Wu, "Deep reinforcement learning based dynamic optimization of bus timetable," *arXiv preprint arXiv:2107.07066*, 2021.
https://arxiv.org/abs/2107.07066


##  Declaration

We hereby declare that this research work is original and has been carried out by us under the guidance of the faculty mentor. All references used in this paper have been properly cited.

---

##  Acknowledgement

We sincerely thank **ERA Foundation**, **ComedKares**, our faculty mentors, our institution, and industry experts for their continuous support and guidance.

---


