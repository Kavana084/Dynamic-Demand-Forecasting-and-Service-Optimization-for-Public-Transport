<div align="center">
<img src="https://www.erafoundationindia.org/images/logo.svg" height="80" style="background:white; padding:8px; margin:0 16px;" />
<img src="https://comedkares.org/wp-content/uploads/2023/04/Comedkares-Logo-EPS.png" height="80" style="background:white; padding:8px; margin:0 16px;" />

# AI- Driven Dynamic Demand Forecasting and Service Optimization for Public Transport


*H.Kavana*  
*MCA*  
*1DA24MC022*

</div>

# Abstract

Public transportation systems  face challenges such as overcrowding, increased passenger waiting time, inefficient fleet utilization, and inability to adapt to real-time traffic and environmental conditions. Traditional bus scheduling systems mainly rely on fixed timetables and static routing, which cannot efficiently handle dynamic passenger demand fluctuations during peak and non-peak hours. Existing systems also lack intelligent demand prediction and adaptive scheduling capabilities, resulting in operational inefficiencies and poor passenger experience.

To address these limitations, this project proposes an **AI-Driven Dynamic Demand forecasting and Service Optimization** that integrates Artificial Intelligence and optimization techniques for intelligent public transport management. The proposed system uses **CatBoost**  to predict future passenger demand using historical transportation data[2]. **Deep Reinforcement Learning (DRL)** is used to analyze real-time traffic, weather, and environmental conditions for adaptive decision-making[3], while **Mixed Integer Linear Programming (MILP)** is applied for optimal fleet allocation and scheduling[1][2]. The system also includes navigation and real-time arrival/departure scheduling modules for efficient route management.

The application is developed as a web-based platform using **ReactJS**, **Python**, and **Supabase**. The proposed system is expected to reduce passenger waiting time, minimize overcrowding, improve fleet utilization, optimize operational cost, and provide efficient real-time transit scheduling. The project contributes toward developing intelligent and adaptive public transportation systems for smart city environments.

---

##  Keywords

`Artificial Intelligence` `Demand Forecasting` `Deep Reinforcement Learning` `MILP Optimization` `CatBoost` `Passenger Demand Prediction` `Dynamic Bus Scheduling` `Route Optimization` `Traffic Analysis` `Fleet Management`

---

# 1.  Introduction

Public transportation systems are essential for urban mobility, but traditional systems mainly rely on fixed schedules[3] and static routing, which often lead to overcrowding, long waiting times[2][3], inefficient fleet utilization, and inability to adapt to changing passenger demand and traffic conditions. With the growth of smart city technologies, intelligent transportation systems are becoming necessary for efficient transit management. Recent advancements in Artificial Intelligence and optimization techniques enable dynamic scheduling and real-time decision making. 
Static bus schedules create a persistent mismatch between service supply and actual passenger demand[3]. During peak hours, buses are overcrowded and passengers are left-behind[2][3] but during off-peak periods, buses run near-empty, wasting fuel and operating costs.Traditional optimization methods are costly, time-consuming, and cannot quickly adapt to sudden changes like traffic, weather, or increased passenger demand.

---

# 2. Literature Review

## 2.1 Research Paper 1

Peled et al. (2021) studied the impact of demand prediction accuracy on dynamic public transport systems using 2.15 million transportation trips from Copenhagen. The research combined demand forecasting uncertainty analysis with MILP-based fleet optimization. Results showed that dynamic routing reduced travel time by at least 23% and generated annual savings of approximately €809,000. The study highlighted that accurate demand prediction is essential for achieving efficient transport operations and resource utilization.

## 2.2 Research Paper 2

Barrera Hernandez et al. (2025) proposed a demand-driven bus dispatching framework that integrates forecasting models with heuristic and MILP optimization techniques. The study used real transportation data from Montería, Colombia, to support real-time dispatch decisions. The heuristic approach achieved over 95% of the MILP solution quality while reducing computation time by 98%. The research demonstrated the practicality of combining demand forecasting with fast optimization methods for public transport management.

## 2.3 Research Paper 3

Ai et al. (2021) developed a Deep Reinforcement Learning-based system for dynamic bus timetable optimization using Deep Q-Networks (DQN). The model adjusted bus departure intervals in real time according to passenger demand and operational conditions. Experiments conducted on smart-card data from Xiamen, China, reduced passenger waiting time by 17% and bus departures by 8%. The study proved that AI-based adaptive scheduling can significantly improve public transport efficiency and service quality.

---

# 3 Problem Statement

 Current public transportation systems use fixed schedules that cannot adapt well to changing passenger demand and traffic conditions. Existing optimization methods often focus on single routes and require high computational resources. Most systems also ignore real-time external factors like traffic, weather, and special events. Therefore, an intelligent real-time dynamic bus dispatching system is needed to improve efficiency, reduce waiting time, and ensure fair service coverage.

# 4 Objectives

- To study existing intelligent public transportation and bus scheduling systems
- To identify limitations in traditional transit scheduling and fleet management approaches
- To design an AI-driven adaptive transit scheduling and fleet optimization system
- To predict passenger demand using CatBoost and analyze real-time conditions using DRL
- To provide intelligent navigation, dynamic bus scheduling, and optimized fleet allocation using MILP.

---

# 5. Methodology

## 7.1 Demand Forecasting

Historical passenger travel data, traffic conditions, weather information, and route details are collected and preprocessed to create a high-quality dataset. The CatBoost machine learning model is trained using these features to predict future passenger demand across different routes and time intervals. The forecasting model identifies travel patterns, peak-hour congestion, and seasonal variations to support intelligent scheduling decisions.

## 5.2 Dynamic Scheduling and Fleet Optimization

The predicted passenger demand is provided to a Deep Reinforcement Learning (DRL/DQN) agent that continuously analyzes real-time traffic conditions, weather changes, and operational constraints. Based on the current environment, the DRL model generates adaptive scheduling decisions. MILP (Mixed Integer Linear Programming) optimization is then applied to allocate buses efficiently and determine the optimal fleet size required to meet demand while minimizing operational costs.

## 5.3 Adaptive Transit Management

The optimized scheduling and fleet allocation outputs are integrated with route management and navigation modules. The system dynamically updates bus arrival and departure schedules according to changing passenger demand and traffic conditions. This adaptive approach reduces waiting time, improves bus utilization, and enhances overall public transport efficiency.

---

# 6. Implementation

## 6.1 Data Collection and Preprocessing

Passenger travel records, GTFS route data, traffic information, and weather data are collected from various sources. Data preprocessing techniques such as cleaning, normalization, feature engineering, and missing-value handling are performed to prepare the dataset for machine learning and optimization tasks.

## 6.2 Model Development

The CatBoost model is implemented for passenger demand prediction using historical and real-time transportation data. The trained model generates demand forecasts that serve as inputs for the scheduling system. A DRL/DQN model is developed to make intelligent dispatching decisions under dynamic transportation conditions.

## 6.3 Fleet Optimization and Scheduling

MILP optimization is integrated with the scheduling framework to determine efficient fleet allocation and route assignments. The optimization engine balances passenger demand, bus availability, route coverage, and operational costs. The final scheduling module generates adaptive arrival and departure timings for buses.

---

# 7. Results and Analysis

## 7.1 Experimental Results

The proposed AI-based Adaptive Bus Scheduling System was evaluated using passenger travel data, traffic information, weather conditions, and route datasets. The integration of CatBoost demand forecasting, DRL-based scheduling, and MILP optimization produced significant improvements compared to conventional fixed scheduling systems.

## 7.2 Performance Analysis

The CatBoost model accurately predicted passenger demand and identified peak-hour travel patterns, enabling better resource planning and service scheduling. The DRL scheduling agent dynamically adjusted dispatching decisions based on real-time traffic and environmental conditions, improving operational flexibility.

MILP optimization enhanced fleet utilization by assigning buses more efficiently across routes and reducing unnecessary vehicle deployment. This resulted in lower operational costs and improved service reliability. The combined AI framework demonstrated superior performance compared to traditional scheduling approaches.

## 7.3 Key Findings

- CatBoost improved demand forecasting accuracy and peak-demand detection.
- DRL enabled real-time adaptive scheduling and dispatching.
- MILP optimized fleet allocation and resource utilization.
- Passenger waiting time was significantly reduced.
- Bus utilization and service reliability improved.
- The integrated system outperformed conventional fixed scheduling methods.

## 8.  Discussion

The proposed system improves public transportation efficiency through intelligent demand prediction, adaptive scheduling, and optimized fleet allocation. The integration of CatBoost, DRL, and MILP enables real-time decision-making and reduces passenger waiting time while improving resource utilization. Dynamic scheduling and route optimization make the system more suitable for smart transportation environments.

Challenges include high computational requirements for DRL and optimization models, availability of real-time traffic and passenger datasets, and maintaining model performance under rapidly changing transportation conditions.


## 9.  Future Scope

- Cloud deployment for large-scale real-time operation.
- IoT integration for live vehicle and traffic monitoring.
- Mobile application support for passengers and operators.
- Edge AI optimization for faster real-time processing.
- Integration with smart city transportation infrastructure.

## 10.  Conclusion

This project addressed the problem of inefficient fixed bus scheduling systems that cannot adapt to changing passenger demand and dynamic traffic conditions. To solve this issue, an intelligent adaptive transit system was proposed by integrating CatBoost-based passenger demand prediction, DRL for real-time decision-making, and MILP for fleet optimization. The proposed approach improved scheduling efficiency, optimized bus allocation, and reduced passenger waiting time. Overall, the system contributes toward smarter, cost-effective, and adaptive public transportation for future smart city environments.


## 11.  References

[1] I. Peled, K. Lee, Y. Jiang, J. Dauwels, and F. C. Pereira, "On the quality requirements of demand prediction for dynamic public transport," *Communications in Transportation Research*, 2021. arXiv:2008.13443. https://arxiv.org/abs/2008.13443

[2] J. E. Barrera Hernandez, L. E. Tarazona Torres, A. Tabares, and D. Álvarez-Martínez, "Optimization of bus dispatching in public transportation through a heuristic approach based on passenger demand forecasting," *Smart Cities*, vol. 8, no. 3, p. 87, 2025. https://doi.org/10.3390/smartcities8030087

[3] G. Ai, X. Zuo, G. Chen, and B. Wu, "Deep reinforcement learning based dynamic optimization of bus timetable," *arXiv preprint arXiv:2107.07066*, 2021.
https://arxiv.org/abs/2107.07066

---

##  Acknowledgement

We sincerely thank **ERA Foundation**, **ComedKares**, our faculty mentors, our institution, and industry experts for their continuous support and guidance.

---


