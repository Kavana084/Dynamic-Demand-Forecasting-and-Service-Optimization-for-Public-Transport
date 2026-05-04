# Dynamic Demand Forecasting & Service Optimization for Public Transport

> A smart system to predict passenger demand and optimize bus allocation and scheduling in real time.

---

##  Project Overview

Public transport systems fail because service supply is decided by fixed schedules, not by actual passenger demand. This leads to overcrowded buses at peak hours, near-empty buses off-peak, and slow responses to disruptions.

This project builds a data-driven system that forecasts demand and adjusts services dynamically.

---

##  Problem Statement

Buses are overcrowded during peak hours, underutilized off-peak, and unable to respond to sudden demand spikes — all because passenger demand is never accurately predicted in advance.

**Root Cause:**
> The absence of an intelligent, real-time, data-driven forecasting and optimization system capable of predicting passenger demand and adjusting services dynamically.

---

##  Root Cause Analysis (5 Whys)

- Buses are overcrowded and delayed because allocation doesn't match actual demand
- Allocation doesn't match demand because no accurate forecasting method exists
- Demand isn't predicted accurately because historical and real-time data aren't analyzed effectively
- Data isn't analyzed effectively because no ML or predictive analytics are in use
- Advanced tech isn't adopted because systems still rely on outdated static scheduling

---

##  Research on Existing Solutions

**Google Maps Transit** helps passengers plan journeys using real-time traffic data and multi-modal routing. It is widely used but focused entirely on navigation, not on how the transport network is managed.

**Moovit** provides live arrival updates and delay alerts using crowd-sourced passenger data. It improves the passenger experience but has no connection to how authorities plan or deploy buses.

**Citymapper** compares all available transport modes in urban areas and offers personalized route suggestions with real-time disruption alerts. It is strong in cities where it operates but limited in coverage.

**Traditional Fixed Scheduling** uses predefined timetables set by transport authorities, updated annually or seasonally. It is simple to manage but cannot respond to changing demand.

**Intelligent Transport Systems (ITS)** use GPS sensors and data platforms to give authorities real-time visibility into fleet positions and traffic. It improves monitoring but lacks any predictive capability.

---

## Observations

All existing apps are built for passengers seeking information, not for operators managing the network. Every solution is reactive — it responds after a problem occurs, never before. Data exists across these systems (GPS signals, crowd reports, telemetry) but it never crosses into operational decisions. Even where digital tools are in place, fixed scheduling remains the actual foundation of how services are planned.

---

## Limitations

None of the solutions predict how many passengers will travel on a specific route at a specific time, so bus frequency cannot be adjusted proactively. Real-time updates reach passengers through apps but don't trigger any operational response — problems are communicated, not corrected. Passenger apps and authority systems work in silos, so crowd data never reaches planning systems. Static schedules break down whenever demand deviates from the historical average they were built on. And when sudden demand spikes occur — festivals, accidents, emergencies — no solution can automatically redeploy buses to respond.

---

##  Identified Gap

No existing solution combines demand forecasting, real-time data, and automatic service adjustment into one tool for transport authorities. The ability to predict passenger volume before service decisions are made, convert demand signals into fleet actions automatically, and connect passenger behavior with scheduling systems — none of this exists today.

---

##  Proposed Approach

Build a system using historical data, GPS, and real-time inputs to forecast demand by route and time, recommend dynamic bus allocation and schedule changes, alert authorities to demand spikes before service degrades, and give passengers live crowd and delay updates.

**Core technologies:** Machine learning for time-series demand forecasting, real-time data integration, and a dynamic scheduling engine.

---

##  Next Steps

-  Identify data sources — GTFS feeds, GPS telemetry, ticketing data, weather APIs
-  Prototype the demand forecasting model starting with time-series regression
-  Design an authority dashboard for actionable service decisions
-  Validate assumptions with transport authority stakeholders
-  Define success metrics — load factor, empty-run rate, spike response time

---

*Day 1–3 Research | Dynamic Demand Forecasting Project*
