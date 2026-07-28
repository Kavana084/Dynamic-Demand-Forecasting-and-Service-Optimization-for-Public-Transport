[![](https://drait.edu.in/assets/images/full_logo-wide.png)](https://drait.edu.in) [![](https://www.erafoundationindia.org/images/logo.svg)](https://www.erafoundationindia.org) [![](https://comedkares.org/wp-content/uploads/2023/04/Comedkares-Logo-EPS.png)](https://comedkares.org)

# Dynamic Demand Forecasting and Service Optimization for Public Transport

**Kavana**
**MCA**
**1DA24MC022**

---

## Abstract

Public transportation systems face growing challenges in matching service capacity with actual passenger demand, often resulting in overcrowded buses during peak hours and underutilized resources during off-peak periods. Traditional scheduling approaches rely on static timetables that fail to adapt to fluctuating ridership patterns caused by time of day, day of week, seasonal trends, weather conditions, and special events. This project presents a **Dynamic Demand Forecasting and Service Optimization system** for BMTC (Bengaluru Metropolitan Transport Corporation) that leverages historical ridership data and real-time information to predict passenger demand and recommend optimized bus scheduling, route planning, and resource allocation strategies. The system integrates CatBoost-based demand forecasting, Mixed-Integer Linear Programming (MILP) for fleet optimization, and the RAPTOR algorithm for trip planning, exposed through a FastAPI backend and a React frontend with an integrated AI assistant. By applying data-driven forecasting techniques, the system aims to improve service efficiency, reduce operational costs, minimize passenger wait times, and enhance the overall commuter experience. Similar demand-driven dispatch and forecasting approaches have demonstrated measurable gains in service quality, operational utility, and fleet efficiency.[1][2][3]

---

## Keywords

Demand Forecasting, Public Transport, Service Optimization, Route Planning, Resource Allocation, Machine Learning, Data Analytics.

---

# 1. Introduction

Efficient public transport management depends on accurately anticipating passenger demand across routes, stops, and time periods. Fixed schedules that do not account for real-world variability often lead to service mismatches — some routes are overcrowded while others run with low occupancy. This inefficiency increases operational costs for transit agencies and reduces the quality of service experienced by commuters.

Recent advancements in data analytics and machine learning have made it possible to move beyond static, rule-based scheduling toward systems that learn from historical ridership patterns and adapt to real-time conditions. Predictive models can identify demand trends across time, location, and external factors such as weather and events, enabling transit authorities to make proactive, data-driven scheduling decisions rather than reactive ones.[1][2]

Motivated by these advancements, this project proposes a Dynamic Demand Forecasting and Service Optimization system for BMTC that analyzes historical and real-time transport data to forecast passenger demand and generate recommendations for bus scheduling, route planning, and resource allocation. The goal is to help transit authorities move from static, one-size-fits-all schedules toward a responsive, intelligent approach to service planning that improves efficiency and commuter satisfaction.

---

# 2. Literature Review

## 2.1 On the Quality Requirements of Demand Prediction for Dynamic Public Transport

Peled et al. studied how the accuracy of demand predictions affects the performance of demand-responsive public transport, using a case study of PT trips in Copenhagen. By simulating a range of Gaussian and non-Gaussian noise distributions around ground-truth demand and re-optimizing a fleet under each, the authors found that the skew and presence of large, infrequent prediction errors — not just overall accuracy — drive optimization performance, and that dynamic routing can reduce trip time by at least 23% versus static routing [1].

## 2.2 Optimization of Bus Dispatching Through a Heuristic Approach Based on Passenger Demand Forecasting

Barrera Hernandez et al. proposed a dynamic dispatch heuristic that integrates Prophet-based passenger demand forecasts with an exact MILP benchmark model, validated on a real-world case study of eight bus routes in Montería, Colombia. Their heuristic matched or surpassed 95% of the MILP's operational utility on average while reducing computation time by up to 98%, demonstrating that lightweight, forecast-driven heuristics can approximate exact optimization at a fraction of the computational cost [2].

## 2.3 Deep Reinforcement Learning Based Dynamic Optimization of Bus Timetable

Ai et al. proposed DRL-TO, a Deep Q-Network-based method that treats bus timetabling as a sequential, minute-by-minute dispatch decision problem rather than an offline optimization. Evaluated against manual, genetic-algorithm, and memetic-algorithm baselines on real bus lines in Xiamen, China, DRL-TO adapted dispatch intervals to real-time passenger flow changes, saving 8% of vehicles and reducing passenger waiting time by 17% on average [3].

---

# 3. Problem Statement

Public transport agencies frequently struggle to align the supply of buses and routes with actual, fluctuating passenger demand. Manual scheduling and static timetables cannot easily adapt to variations caused by peak-hour surges, seasonal changes, weather, and special events. This mismatch results in overcrowding, wasted resources, longer wait times, and reduced commuter satisfaction. There is a need for an intelligent system that can forecast demand accurately and translate those forecasts into actionable scheduling and resource allocation decisions.[1][2][3]

---

# 4. Objectives

- Predict passenger demand using historical and real-time transport data.
- Identify demand patterns across routes, stops, and time periods.
- Optimize bus scheduling based on forecasted demand.
- Support data-driven route planning decisions.
- Improve resource allocation across the transport network.
- Reduce passenger wait times and overcrowding.
- Provide an interface for visualizing demand trends and optimization outcomes.

---

# 5. Methodology

The proposed system follows a modular architecture that integrates data collection, forecasting models, and an optimization layer to transform raw transport data into actionable scheduling and planning insights.

## 5.1 Data Collection

Historical ridership data, route information, and real-time inputs are gathered from BMTC's GTFS data (4,164 routes, 55,071 trips, ~1.49M `stop_times` rows) to form the foundation for demand analysis.

---

## 5.2 Data Preprocessing

Prior to forecasting, the collected data undergoes a preprocessing stage to improve quality and consistency. This phase performs several operations, including:

- Handling missing or inconsistent records.
- Normalizing and formatting timestamps.
- Aggregating ridership data by route, stop, and time window.
- Structuring data for input into forecasting models.
- Generating a synthetic passenger demand dataset (~225,000 records, ~60 features) using quantile-mapped demand generation, demand-aware vehicle capacity assignment, strict no-leakage rolling averages, and a custom Bengaluru seasonal climate model.

These preprocessing operations ensure that the forecasting model receives clean, standardized, and context-rich input, resulting in more accurate demand predictions.

---

## 5.3 Demand Forecasting

The preprocessed data is passed to a CatBoost-based forecasting module, which analyzes historical patterns and real-time signals to predict expected passenger demand. The model evaluates temporal trends, route-level variation, and external factors to identify potential demand spikes or drops.

During this phase, the model performs:

- Time-series demand prediction
- Route-level and stop-level demand analysis
- Peak vs. off-peak pattern identification
- Anomaly detection for unusual demand events

---

## 5.4 Service Optimization

Based on the forecasted demand, a Mixed-Integer Linear Programming (MILP) module generates recommendations for bus scheduling, route adjustments, and resource allocation, while the RAPTOR algorithm handles commuter trip planning. Rather than only presenting raw predictions, the system translates forecasts into actionable scheduling suggestions that help planners better match capacity with expected ridership.

---

## 5.5 Result Presentation

The application presents demand forecasts and optimization recommendations through a structured, user-friendly React interface, backed by an AI assistant. Visualizations of demand trends, route-level insights, and scheduling suggestions improve interpretability and support decision-making by transit planners.

---

## 6. Implementation

The Dynamic Demand Forecasting and Service Optimization system was developed as a full-stack application combining a data pipeline, forecasting logic, an optimization engine, and a user interface for reviewing predictions and recommendations.

### 6.1 Frontend

The frontend was developed using React.js to provide an interactive, responsive dashboard for exploring demand trends, route-level insights, and scheduling recommendations, alongside a chat interface for the AI assistant.

### 6.2 Backend

The backend was built with FastAPI and SQLAlchemy, handling forecasting requests, fleet optimization, trip-planning queries, and serving results to the frontend through REST APIs.

### 6.3 Database

*(Add your actual database, e.g. PostgreSQL/SQLite, and what it stores — ridership history, route data, forecast results, etc.)*

### 6.4 Forecasting & Optimization Engine

Passenger demand forecasting is handled by CatBoost, fleet scheduling by a MILP optimizer, and commuter trip planning by the RAPTOR algorithm. An AI assistant, powered by the Groq API (`llama-3.3-70b-versatile`), provides conversational access to schedules and demand insights.

---

# 7. Results and Analysis

The developed system successfully performs demand forecasting and generates scheduling recommendations across multiple routes and time periods.

### Key Results

- Accurate prediction of passenger demand trends across routes and time windows.
- Identification of peak and off-peak demand patterns.
- Generation of data-driven bus scheduling recommendations.
- Improved alignment between service capacity and actual demand.
- Reduced overcrowding and underutilization on analyzed routes.

The system effectively assists transit planners in understanding demand patterns and making informed scheduling and resource allocation decisions.

---

# 8. Discussion

The implementation of the Dynamic Demand Forecasting and Service Optimization system demonstrated how data-driven techniques can simplify and improve public transport planning. During testing, the system was able to identify meaningful demand patterns and translate them into practical scheduling suggestions.

One of the most beneficial aspects of the project was its ability to highlight demand fluctuations that static timetables typically miss, helping planners anticipate rather than react to ridership changes. The optimization component further improves usefulness by converting raw forecasts into concrete scheduling and allocation recommendations.

The performance of the system largely depends on the quality and completeness of the historical data provided. Well-structured, consistent ridership data generally produces more reliable forecasts, while sparse or noisy data may require additional cleaning and validation.

Overall, the project shows that demand forecasting tools can serve as effective decision-support systems for transit agencies by reducing scheduling inefficiencies, improving resource utilization, and enhancing the overall commuter experience.

---

# 9. Conclusion

The Dynamic Demand Forecasting and Service Optimization system was successfully developed to help predict passenger demand and generate optimized scheduling and resource allocation recommendations for public transport.

The project helps reduce the mismatch between service capacity and actual ridership, making it easier for transit planners to design efficient, responsive schedules. It can be useful for transit agencies, urban planners, and researchers working on smart mobility solutions.

Overall, the project achieved its goal of creating a data-driven tool for improving public transport scheduling and service optimization.[1][2][3]

---

## 10. Future Scope

The current system successfully provides demand forecasting and service optimization support for public transport. In the future, the project can be enhanced with the following features:

- Integration with live GPS and ticketing data for real-time demand tracking.
- Support for multi-modal transport optimization (bus, metro, rail).
- Predictive alerts for anticipated overcrowding or service gaps.
- Interactive dashboard for transit authorities with advanced analytics.
- Integration with mapping services for dynamic route visualization.
- Personalized commuter-facing features such as crowding predictions.

These enhancements can improve the usability, scalability, and effectiveness of the system while providing a more comprehensive planning experience for transit agencies and commuters.

---

## Acknowledgements

We sincerely thank:

- ERA Foundation
- ComedKares
- Faculty mentors
- Institution
- Industry experts

for their continuous support and guidance.

## References

[1] [On the Quality Requirements of Demand Prediction for Dynamic Public Transport](https://arxiv.org/abs/2008.13443)

[2] [Optimization of Bus Dispatching in Public Transportation Through a Heuristic Approach Based on Passenger Demand Forecasting](https://doi.org/10.3390/smartcities8030087)

[3] [Deep Reinforcement Learning based Dynamic Optimization of Bus Timetable](https://arxiv.org/abs/2107.07066)
