# Dynamic Demand Forecasting & Service Optimization for Public Transport

> A smart system that predicts passenger demand by route and time, then automatically adjusts bus allocation and scheduling — before problems occur, not after.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Problem Statement](#problem-statement)
- [Root Cause Analysis](#root-cause-analysis)
- [Research on Existing Solutions](#research-on-existing-solutions)
- [Comparative Analysis](#comparative-analysis)
- [Pattern Identification](#pattern-identification)
- [Limitations of Existing Solutions](#limitations-of-existing-solutions)
- [Identified Gap](#identified-gap)
- [Proposed Approach](#proposed-approach)
- [Target Users](#target-users)
- [Next Steps](#next-steps)

---

## Project Overview

Public transport systems consistently fail in the same way: service supply is decided by fixed schedules built on historical averages, while actual passenger demand shifts constantly — by time of day, weather, events, and disruptions. The result is overcrowded buses at peak hours, near-empty buses off-peak, and no ability to respond to sudden demand spikes before passengers experience the consequences.

This project addresses that failure by building a data-driven system that forecasts passenger demand by route and time, and converts those forecasts into automated service recommendations for transport authorities — closing the loop between prediction and action that no existing solution provides.

---

## Problem Statement

> Buses are overcrowded during peak hours, underutilized off-peak, and unable to respond to sudden demand spikes — because passenger demand is never accurately predicted in advance.

Public transport operators currently make deployment decisions using timetables that were set months or years ago. When demand deviates from the historical average those timetables assumed — which happens daily — the system has no mechanism to adapt. Passengers experience the outcome as overcrowding, long waits, and unreliable service. Operators experience it as high operational costs and low efficiency.

The core problem is not a lack of data. GPS signals, crowd-sourced passenger reports, ticketing transactions, and real-time traffic data all exist across various platforms. The problem is that this data is fragmented across systems that were never designed to connect — and even where data is available, no system converts it into automated operational decisions.

**Sub-problems this project addresses:**

- **Demand forecasting** — predicting passenger volume by route, time, and day using historical patterns and real-time signals
- **Service optimization** — adjusting bus frequency, allocation, and scheduling dynamically in response to forecast demand
- **Real-time monitoring** — detecting and responding to sudden demand shifts caused by events, weather, or disruptions
- **Data integration** — bridging passenger-facing data streams with authority-facing planning systems
- **Operator experience** — giving transport authorities actionable recommendations, not just dashboards to monitor

---

## Root Cause Analysis

### 5 Whys

Starting from the most visible symptom — buses are overcrowded and delayed:

1. **Why are buses overcrowded and delayed?**
   Bus allocation does not match actual passenger demand, especially during peak hours.

2. **Why does allocation not match demand?**
   The transport system lacks accurate methods to forecast passenger volume by route and time period.

3. **Why is demand not forecast accurately?**
   Historical data, travel behavior patterns, seasonal trends, and live conditions are not analyzed together or in real time.

4. **Why is this data not analyzed effectively?**
   No system uses machine learning, predictive analytics, or integrated data pipelines for this purpose.

5. **Why are these approaches not in use?**
   Public transport systems still depend on static scheduling methods rather than intelligent, demand-driven optimization.

### Root Cause Statement

> The fundamental cause of overcrowding, delays, and inefficient resource use in public transport is the absence of a system that predicts passenger demand accurately and adjusts services dynamically in response — before passengers experience the failure.

### Cause and Effect Chain

```
Static scheduling & no predictive analytics
        ↓
Passenger demand is not forecast
        ↓
Buses are allocated to fixed timetables, not actual need
        ↓
Overcrowding on high-demand routes, underuse on low-demand routes
        ↓
Delays, passenger dissatisfaction, high operational costs
        ↓
Reduced public trust in transport, increased private vehicle use
```

---

## Research on Existing Solutions

Five solutions were researched and documented across Days 1–3. Each is summarized on a standard set of axes to enable structured comparison.

| Solution | Purpose | Key Features | Target Users | Core Approach |
|---|---|---|---|---|
| **Google Maps Transit** | Journey planning and navigation | Real-time traffic, multi-modal routing, live arrival times | Passengers | Passenger-side data aggregation; no operator interface |
| **Moovit** | Live transit information via crowd-sourcing | Crowd-sourced delay alerts, arrival predictions, multi-city coverage | Passengers | Community data collection; no predictive modelling |
| **Citymapper** | Urban multi-modal route comparison | Door-to-door planning, disruption alerts, mode comparison | Urban commuters | API-based aggregation and disruption messaging |
| **Traditional Fixed Scheduling** | Define service timetables in advance | Annual or seasonal updates, predefined routes and frequency | Transport authorities | Historical average demand baked into static timetables |
| **ITS (Intelligent Transport Systems)** | Fleet tracking and operational visibility | GPS monitoring, traffic signal integration, AVL systems | Transport authorities | Sensor networks and dashboards; monitoring only |

One structural split is immediately visible: Google Maps, Moovit, and Citymapper all serve passengers, while Traditional Scheduling and ITS serve transport authorities. No solution operates across both. This split is not incidental — it is central to understanding why the core problem persists.

---

## Comparative Analysis

Listing what solutions do differently is not analysis. The goal of comparison is to understand *why* solutions differ, what those differences mean for the problem, and — most importantly — where all solutions converge on the same blind spot despite their differences.

### What all five solutions share

Despite serving different users and using different technologies, all five solutions share four structural properties:

**They are all passive in relation to demand.** Every solution treats passenger demand as something to be observed and reported after it has manifested — never anticipated before it does. Google Maps reports delays in progress. ITS shows congestion building. Traditional Scheduling assumes demand will match the historical average. No solution asks what demand will look like in an hour or tomorrow morning.

**They all require a human decision to act.** Passenger apps tell passengers what is happening; ITS tells operators what is happening. In both cases, a human must interpret the information and respond. No solution closes the loop automatically. The action layer is always separated from the data layer by a human step.

**They all treat scheduling as fixed infrastructure.** Even ITS — the most technically sophisticated authority tool in the comparison — monitors bus positions relative to fixed timetables. Its core metric is schedule adherence: whether buses arrive on time relative to a predetermined plan. The plan itself is never questioned.

**They are data-rich but action-poor.** Each solution collects or uses meaningful data — GPS signals, crowd reports, live traffic. That data never crosses into operational decisions. Three separate data pipelines (consumer apps, ITS, ticketing systems) exist in parallel, each capturing a fraction of what demand forecasting would need.

### Where solutions differ — and why the differences have limited significance

**Consumer apps vs authority tools.** Google Maps, Moovit, and Citymapper solve the passenger information problem: *Which bus should I take?* ITS and Traditional Scheduling solve the operational planning problem: *How many buses should run?* These are genuinely different problems. The significant observation is that no solution attempts to bridge them. Moovit's crowd-sourced load data has direct relevance to scheduling decisions — yet it never reaches any planning system.

**Real-time vs static.** Moovit and Google Maps provide real-time updates; Traditional Scheduling is static by definition. This appears to be a major difference. Its practical significance is limited: real-time updates change what passengers *know*, not what operators *do*. A passenger who sees a 15-minute delay is better informed but no better served. The operational layer remains static regardless of how much real-time information flows through the passenger layer. The real-time capability exists on the wrong side of the system.

**ITS as the closest approximation.** ITS is the only solution that gives authorities genuine real-time operational visibility — knowing where every bus is and how traffic is behaving. This is more useful than static scheduling alone. But ITS generates no predictions and triggers no actions. A transport manager using ITS still decides manually whether to redeploy buses, and still has no way to anticipate demand before it arrives at a stop.

### Effectiveness ranking

Ranked by contribution to the core problem — accurate demand forecasting and dynamic service adjustment:

1. **ITS** — most useful for authorities, but limited to reactive monitoring
2. **Google Maps Transit** — richest data pipeline, but no operational outlet
3. **Moovit** — crowd data is genuinely valuable, but siloed in the passenger layer
4. **Citymapper** — strong user experience, but narrower city coverage and no operational component
5. **Traditional Scheduling** — foundational but entirely static; encodes the problem rather than solving it

---

## Pattern Identification

Patterns emerge from examining not what individual solutions do, but what all solutions share — including the assumptions they make without questioning them.

| # | Pattern | Evidence | Significance |
|---|---|---|---|
| P1 | **Passenger-only orientation** | All three consumer apps target passengers exclusively | Operators are entirely absent from the design space of consumer transit technology |
| P2 | **Reactive by design** | Every solution responds after demand manifests — none anticipates it | Problems are communicated or tracked, never prevented |
| P3 | **Data siloing** | Each solution owns its own data pipeline with no cross-system sharing | Operational systems and passenger apps exist in separate, incompatible technical stacks |
| P4 | **Static scheduling as the foundation** | Even ITS builds on top of fixed timetables rather than replacing them | Modern monitoring tools are layered onto outdated planning logic |
| P5 | **Monitoring without action** | ITS provides real-time visibility but generates no automated response | Knowing where buses are does not improve where they go next |

### The dominant assumption: demand is a given, not a variable

The most important pattern is not any individual design choice — it is a shared assumption that runs through all five solutions: **passenger demand is something to be observed, not predicted**. Every solution treats demand as an input to the system, not as a variable the system should model.

This assumption explains why the two halves of the system were never connected. Passenger apps collect demand signals but have no mechanism to act on them. Authority tools can act but have no demand signals to act on. The gap between these two layers is not an oversight. It is the structural consequence of every solution accepting the same assumption: that demand management is not the system's job.

### Why static scheduling persists

Traditional scheduling persists not because it works well but because it is simple, auditable, and contractually embedded in how transport authorities operate. Even ITS — explicitly designed to modernize transport operations — layered itself on top of static scheduling rather than replacing it. This reveals that the limitation is partly technical (no predictive tools exist) and partly institutional (static schedules are the governance and procurement structure). Any solution in this space must engage with both dimensions.

---

## Limitations of Existing Solutions

Each limitation below is derived directly from the comparative analysis and pattern identification. Every limitation is evidenced by specific observations from the comparison — not asserted generically.

---

### Limitation 1: No solution predicts future demand — all solutions are structurally reactive

**Observation:** Across all five solutions, not one performs demand forecasting. Google Maps and Moovit provide real-time status. ITS tracks fleet positions. Traditional Scheduling uses historical averages encoded in timetables. The word *predict* does not describe what any of these systems do.

This is not a missing feature — it is a missing design intent. These systems were not built to ask *How many passengers will arrive at Route 12B at 8:45 AM tomorrow?* because they were designed to inform, not to optimize. Google Maps knows real-time traffic but has no model of passenger volume. Moovit collects crowd reports to generate arrival estimates, not to recommend service changes. ITS has GPS data on every bus but no model of how many people will board at the next stop.

**Why this matters:** Without demand prediction, deployment decisions are always made after demand has already appeared. A transport authority can see that Route 12 was overcrowded at 8:45 AM today, but it cannot pre-position extra buses for 8:45 AM tomorrow. The result is a permanent lag between service supply and passenger need — and this lag is the core experience failure that passengers report as overcrowding and delay.

**Evidence:** Traditional Scheduling uses historical averages as a proxy for prediction, but averages collapse when demand deviates from the norm — during weather events, disruptions, or occasions not captured in the historical baseline. ITS offers real-time positioning data but explicitly no predictive function. No consumer app models future demand in any form.

---

### Limitation 2: The passenger data layer and the planning layer are architecturally disconnected

**Observation:** Moovit crowd-sources delay reports from millions of commuters. Google Maps aggregates real-time traffic and transit data at scale. Both systems carry live signals of where demand pressure exists across urban networks. None of this data crosses into ITS dashboards or scheduling systems.

This disconnection is structural, not incidental. Consumer apps are built as passenger-facing products — their architecture was never intended to interface with government planning systems. ITS platforms are built on procurement standards (AVL, SCADA) that predate modern consumer data pipelines. The result is two parallel systems — one with rich passenger-side demand signals, one with operational authority — with no bridge between them.

**Why this matters:** The data required to predict demand already exists. It is being collected every day by passenger apps, ticketing systems, and GPS sensors. The problem is not data scarcity — it is data fragmentation. A planning system that could ingest crowd-sourced load signals, ticketing transaction patterns, and GPS headway data would have meaningful inputs for demand forecasting. No current solution creates this integration. The three data pipelines each solve a fraction of the problem in isolation.

**Evidence:** Moovit's entire value proposition is crowd-sourced data, yet its platform has no operator-facing component. Google Maps integrates GTFS feeds but does not expose demand signals to authorities. ITS operates on sensor and AVL data without any integration to passenger-facing streams. Three parallel pipelines exist, none connected to each other.

---

### Limitation 3: No solution converts demand signals into automated operational actions

**Observation:** ITS is the only solution that gives transport authorities real-time operational data. Yet ITS requires a human operator to interpret that data and manually decide whether to act — redeploy a bus, adjust a route, increase frequency. The system monitors; it does not optimize.

This limitation is sharpest during demand spikes. An ITS operator sees congestion building on Route 7 at 7:55 AM. The decision to act, the identification of which bus to move, and the communication of the schedule change to passengers all require manual steps. The response time is limited not by data availability but by human processing speed.

**Why this matters:** The value of real-time data diminishes when action is delayed by manual decision cycles. A spike in demand at 7:55 AM is actionable only if a redeployment can reach passengers before 8:10 AM. If approval and communication take 10–15 minutes, the window has already closed. Dynamic optimization requires closed-loop automation — the data, decision, and action need to be in the same system.

**Evidence:** ITS dashboards are built around visibility tools — maps, headway displays, delay indicators. They include no recommendation engines, no automated redeployment triggers, no dynamic scheduling outputs. Traditional Scheduling has no feedback mechanism at all — changes require a full planning cycle. Consumer apps have no operational authority. Across all five solutions, zero examples of automated operational response to demand signals exist.

---

### Limitation 4: Static scheduling persists as the implicit baseline even in modern tools

**Observation:** ITS was designed to modernize public transport. Yet its primary metric is schedule adherence — whether buses arrive on time relative to a predetermined timetable. The timetable itself is never questioned. ITS makes static scheduling more visible and more trackable. It does not make scheduling dynamic.

**Why this matters:** Static schedules are built on historical averages — average Monday demand, average summer ridership. They perform adequately when demand is stable and predictable. They fail structurally when demand deviates: during events, disruptions, or shifts in commuter behavior. Modern cities — with hybrid working patterns, event-driven demand, and changing demographics — generate demand profiles that historical averages do not represent accurately. Every novel demand pattern becomes an edge case the system was not designed for.

**Evidence:** All five solutions accept static scheduling as the foundation. Google Maps and Moovit present static timetable data overlaid with real-time updates. ITS measures performance against static schedules. Only during severe disruptions do authorities temporarily break from the timetable — and this is treated as an exceptional response, not a normal operational mode.

---

### Limitation 5: Unplanned demand events are universally unaddressed

**Observation:** None of the five solutions has a mechanism for anticipating or responding to unplanned demand spikes. A major sporting event, a service disruption on a parallel line, or sudden severe weather can multiply demand on specific routes within minutes. Every existing solution treats these scenarios as outside its scope.

This limitation compounds Limitations 1 and 3. Because no solution forecasts demand, spikes arrive without warning. Because no solution automates response, any reaction is slow and manual. The scenarios with the highest service impact are precisely those in which all five solutions perform worst.

**Why this matters:** Unplanned demand spikes are not rare edge cases — they are a regular feature of urban transport. Major events occur weekly in large cities; weather disruptions are monthly. These are predictable categories of events, even when the specific event is not. A system that integrates event calendars, weather APIs, and historical surge patterns could model and pre-position for these scenarios. No existing solution attempts this.

**Evidence:** Traditional Scheduling does not account for events by design. ITS provides awareness but no automated response. Passenger apps alert users to disruptions but do not affect service delivery. The absence of event-driven response is consistent across all five solutions — it is a shared gap, not an individual failure.

---

## Identified Gap

The five limitations above converge on a single structural gap:

> **No existing solution integrates demand prediction with operational action.**

Each solution reviewed is well-designed for its stated purpose. The pattern across all of them is that the stated purpose excludes the forecasting-and-optimization loop that the problem actually requires. Consumer apps were designed to serve passengers, not to optimize services. Authority tools were designed to monitor execution, not to forecast demand. The gap is not an oversight within any individual solution — it is the consequence of the field never having attempted a solution that bridges the passenger-authority divide and combines prediction with automated response.

Three specific capabilities are absent across all five solutions:

1. **Demand forecasting** — modelling future passenger volume by route and time using historical data, real-time signals, and external inputs such as weather and events
2. **Data integration** — connecting passenger-facing data streams (crowd reports, boarding patterns, ticketing) with authority-facing planning systems
3. **Closed-loop optimization** — converting demand forecasts automatically into service recommendations or redeployment actions, without requiring manual human interpretation at each step

---

## Proposed Approach

Build a system that treats passenger demand as a predictable, modelable variable — and uses that prediction to drive automated service decisions before problems occur.

### Core capabilities

**Demand forecasting engine**
Uses time-series machine learning trained on historical ridership data, supplemented with real-time GPS headway data, weather conditions, event calendars, and ticketing signals. Outputs predicted passenger volume by route and 30-minute time window.

**Dynamic scheduling and allocation**
Converts demand forecasts into service recommendations — adjusted frequency, bus redeployment, route modifications — delivered to transport authority operators as actionable suggestions with supporting data.

**Spike detection and pre-positioning**
Monitors incoming signals (event data, weather alerts, disruption reports) to identify demand spikes before they arrive, enabling pre-emptive deployment rather than reactive response.

**Operator dashboard**
Gives transport authorities a single interface for forecast visibility, recommended actions, fleet status, and historical performance — designed for decision support, not just monitoring.

**Passenger-facing updates**
Provides passengers with live crowd levels, adjusted arrival times based on dynamic scheduling, and disruption notifications that reflect actual operational decisions — not static timetable data.

### Core technologies

- Machine learning for time-series demand forecasting (LSTM, gradient boosting, or ensemble models)
- GTFS and GTFS-RT feeds for static and real-time transit data
- GPS and AVL integration for fleet positioning
- Weather and event calendar APIs for external demand signals
- Automated scheduling engine for converting forecasts to service adjustments

---

## Target Users

**Transport authorities and operators** — the primary user. This system is built for the people who decide how many buses run and where. It gives them demand forecasts before they make deployment decisions, and automated recommendations when demand shifts.

**Transport planners** — use historical demand analysis and pattern reports to improve route design, frequency planning, and investment decisions over longer time horizons.

**Passengers** — benefit indirectly through improved service reliability, reduced overcrowding, and live updates that reflect actual operational decisions rather than static timetables.

---

## Next Steps

- [ ] Identify and access data sources — GTFS feeds, GPS telemetry, ticketing transaction data, weather APIs, event calendars
- [ ] Prototype the demand forecasting model using time-series regression as a baseline
- [ ] Design the operator dashboard with a focus on actionable recommendations, not just data display
- [ ] Validate core assumptions with transport authority stakeholders
- [ ] Define success metrics — load factor improvement, empty-run rate reduction, spike response time, schedule adherence delta

---

*Research conducted across Days 1–4 | Dynamic Demand Forecasting & Service Optimization for Public Transport*
