# PRELIMINARY PAGES

## Title Page
**Project Title**: Transit AI System
**Submitted by**: [Student Name]
**In partial fulfillment for the award of the degree of**: [Degree Name]
**Institution**: [College Name]
**Year**: [Year]

## Certificate from the Organization/Company
This is to certify that the project entitled "Transit AI System" is a bona fide record of work carried out by [Student Name] under our supervision and guidance during the period [Start Date] to [End Date] at [Company Name].

## Certificate from the College
This is to certify that the project report entitled "Transit AI System" submitted by [Student Name] in partial fulfillment of the requirements for the award of [Degree Name] is a record of original work done under my supervision and guidance.
- **Internal Guide**: [Guide Name]
- **HOD**: [HOD Name]

## Declaration by the Student
I hereby declare that the project report entitled "Transit AI System" submitted to [College Name] is a record of an original work done by me under the guidance of [Guide Name], and this project has not formed the basis for the award of any degree or diploma elsewhere.

## Acknowledgements
I would like to express my sincere gratitude to my guide, the Head of the Department, and all those who have directly or indirectly helped me in the successful completion of this project.

## Abstract / Synopsis
The Transit AI System is an advanced, AI-powered public transportation management platform designed to optimize transit operations and enhance the commuter experience. Traditional transit systems often suffer from static scheduling, poor route optimization, and unpredictable demand. This project leverages Artificial Intelligence, particularly Machine Learning (CatBoost for demand prediction) and Operations Research (PuLP for fleet optimization), to dynamically manage routes, schedules, and fleet distribution. Additionally, it offers an intuitive trip-planning interface for users and an administrative dashboard for real-time monitoring and decision-making. 

## Table of Contents
1. Chapter 1: Introduction
2. Chapter 2: Literature Survey
3. Chapter 3: System Requirements Specification (SRS)
4. Chapter 4: System Design
5. Chapter 5: Implementation Details
6. Chapter 6: Software Testing
7. Chapter 7: Screenshots and Outputs
8. Chapter 8: Conclusion and Future Scope
9. Chapter 9: References
10. Chapter 10: Appendix

## List of Figures
- Figure 4.1: System Architecture Diagram
- Figure 4.2: Data Flow Diagram (Level 0 and 1)
- Figure 4.3: Use Case Diagram
- Figure 4.4: Sequence Diagram
- Figure 7.1: User Login Screen
- Figure 7.2: Trip Planner Interface
- Figure 7.3: Admin Dashboard with Demand Prediction

## List of Tables
- Table 3.1: Hardware Requirements
- Table 3.2: Software Requirements
- Table 4.1: Database Schema description
- Table 6.1: Test Cases for User Authentication
- Table 6.2: Test Cases for Trip Planning Algorithm

---

# CHAPTER 1: INTRODUCTION

## 1.1 Introduction
Urban transportation networks face continuous challenges in managing growing commuter demand while maintaining operational efficiency. The Transit AI System aims to bridge this gap by integrating modern AI and optimization techniques into transit management. By predicting passenger demand and optimizing fleet allocation, the system provides a smarter, more responsive public transport infrastructure.

## 1.2 Problem Statement
Existing transit systems largely operate on fixed schedules and predetermined routes that do not adapt to real-time fluctuations in passenger demand. This leads to inefficiencies such as overcrowded vehicles during peak hours, empty trips during off-peak hours, and suboptimal resource utilization. Commuters also lack intelligent trip-planning tools that consider real-time factors and multimodality.

## 1.3 Objectives
- To develop an intelligent trip planner for commuters.
- To implement machine learning models (CatBoost) for accurate passenger demand prediction.
- To utilize linear programming (PuLP) for optimizing fleet allocation and scheduling.
- To provide a comprehensive administrative dashboard for real-time monitoring.

## 1.4 Scope of the Project
The scope of this project encompasses the development of a full-stack web application with a robust backend to handle complex AI and routing algorithms. It serves two primary user roles:
1. **Commuters**: Planning trips, viewing transit options, and getting real-time routing.
2. **Administrators**: Monitoring fleet metrics, viewing demand forecasts, and adjusting operations.

## 1.5 Organization Overview
*(Include a brief overview of the organization or department where the project was conducted, detailing their focus on transportation, AI, or software development).*

---

# CHAPTER 2: LITERATURE SURVEY

## 2.1 Existing Systems
Current public transit systems often rely on historical, aggregated data to set semi-permanent schedules. Software solutions exist for ticketing and basic routing (like standard shortest-path algorithms), but they often lack predictive capabilities. Fleet allocation is mostly done manually by dispatchers based on intuition rather than algorithmic optimization.

## 2.2 Proposed System
The proposed Transit AI System integrates predictive analytics and prescriptive optimization. It uses historical ridership data to forecast future demand and automatically generates optimized fleet allocation schedules. It also includes an advanced routing engine using NetworkX for calculating optimal multimodal paths for users. 

## 2.3 Identified Research Gaps
- Lack of integration between predictive models and fleet optimization in standard open-source tools.
- Insufficient dynamic routing capabilities that account for real-time demand variations.
- Poor user interfaces for transit administrators to visualize complex AI-driven metrics.

---

# CHAPTER 3: SYSTEM REQUIREMENTS SPECIFICATION (SRS)

## 3.1 Hardware Requirements
- **Processor**: Intel Core i5 / AMD Ryzen 5 or higher
- **RAM**: 8 GB minimum (16 GB recommended for ML training)
- **Storage**: 256 GB SSD
- **Network**: Broadband Internet connection

## 3.2 Software Requirements
- **Operating System**: Windows 10/11, Linux, or macOS
- **Backend**: Python 3.9+, FastAPI, Uvicorn
- **Frontend**: Node.js, React 18, Vite, TailwindCSS
- **Database**: PostgreSQL (or SQLite for development)
- **Machine Learning**: CatBoost, Scikit-learn, Pandas
- **Optimization**: PuLP
- **Network Analysis**: NetworkX

## 3.3 Functional Requirements
- **User Authentication**: Secure registration and login for both commuters and admins (JWT based).
- **Trip Planning**: Users can input source and destination to receive optimal transit routes.
- **Demand Prediction**: System automatically predicts passenger load for various routes based on historical data.
- **Fleet Optimization**: System recommends optimal vehicle assignment based on predicted demand.
- **Admin Dashboard**: Visual representation of system health, demand forecasts, and fleet status.

## 3.4 Non-Functional Requirements
- **Performance**: The routing algorithm must return results within 2 seconds.
- **Scalability**: The backend must handle concurrent requests using FastAPI's asynchronous capabilities.
- **Security**: Passwords must be hashed using bcrypt; API endpoints must be protected via JWT authorization.
- **Usability**: The frontend must be responsive and accessible on mobile devices.

---

# CHAPTER 4: SYSTEM DESIGN

## 4.1 System Architecture
The system follows a modern client-server architecture:
- **Frontend (Client)**: Built with React and Vite, communicating via RESTful APIs.
- **Backend (Server)**: Built with FastAPI, handling business logic, ML inference, and routing algorithms.
- **Database Layer**: PostgreSQL via SQLAlchemy ORM for relational data storage.

## 4.2 Data Flow Diagrams (DFD)
- **Level 0 (Context Diagram)**: Shows the User and Admin interacting with the Transit AI System.
- **Level 1**: Details the processes: Authentication, Trip Planning Engine, Machine Learning Predictor, and Fleet Optimizer.

## 4.3 Use Case Diagrams
- **User**: Register, Login, Search Route, View Trip Details.
- **Admin**: Login, View Dashboard, Run Optimization, View Demand Predictions, Manage Fleet.

## 4.4 Sequence Diagrams
- **Trip Planning Flow**: User -> Frontend -> API Gateway -> Routing Engine (NetworkX) -> Database -> Return Route -> Display on UI.
- **Demand Prediction Flow**: Admin -> Dashboard -> API Request -> ML Model (CatBoost) -> Return Forecast -> Display Charts (Recharts).

## 4.5 Database Design / Schema
- **Users Table**: `id`, `username`, `password_hash`, `role`
- **Stops Table**: `id`, `name`, `latitude`, `longitude`
- **Routes Table**: `id`, `route_name`, `base_frequency`
- **Fleet Table**: `id`, `vehicle_type`, `capacity`, `status`
- **Demand_History Table**: `id`, `route_id`, `timestamp`, `passenger_count`

---

# CHAPTER 5: IMPLEMENTATION DETAILS

## 5.1 Technologies Used / Programming Languages
- **Python**: Core backend language.
- **JavaScript/TypeScript**: Frontend development.
- **FastAPI**: High-performance API framework.
- **React.js & TailwindCSS**: UI component library and styling.
- **SQLAlchemy**: Database Object Relational Mapping (ORM).

## 5.2 Modules Description
- **API Gateway Module**: Handles HTTP routing and JWT validation.
- **Routing Engine**: Utilizes NetworkX to calculate the shortest/fastest path between transit nodes.
- **ML Pipeline**: Uses CatBoost for regression tasks to predict hourly passenger volumes.
- **Optimization Engine**: Uses PuLP to solve mixed-integer linear programming problems to assign buses to routes optimally.

## 5.3 Implementation Steps
1. **Environment Setup**: Setting up virtual environments, Node.js, and installing dependencies via `requirements.txt` and `package.json`.
2. **Database Migration**: Creating schemas using SQLAlchemy and populating seed data.
3. **Backend API Development**: Implementing endpoints for user management and routing.
4. **AI Integration**: Training the CatBoost model on historical transit data and saving the model weights.
5. **Frontend UI**: Building responsive React components and connecting them to backend APIs using Axios.

---

# CHAPTER 6: SOFTWARE TESTING

## 6.1 Testing Strategies
The system utilized both manual and automated testing approaches to ensure reliability and accuracy, especially for the routing and AI components.

## 6.2 Unit Testing
- Tested individual Python functions (e.g., distance calculations, shortest path algorithms).
- Framework: `pytest`.

## 6.3 Integration Testing
- Verified communication between the React frontend and FastAPI backend.
- Verified database transaction integrity.

## 6.4 System Testing
- End-to-end testing of the complete user flow from login to generating a trip plan.
- Verifying the ML model's inference latency under load.

## 6.5 Test Cases
- **TC01**: Valid User Login - Expected: Success & JWT returned.
- **TC02**: Invalid Login - Expected: 401 Unauthorized error.
- **TC03**: Route Search (Valid Stops) - Expected: Returns list of transit legs and total time.
- **TC04**: Route Search (Invalid Stops) - Expected: 404 Not Found or appropriate error message.
- **TC05**: Demand Prediction - Expected: Returns positive integer forecasts for future timestamps.

---

# CHAPTER 7: SCREENSHOTS AND OUTPUTS

## 7.1 Input Screens
*(Note: In the actual document, insert screenshots here)*
- User Login / Registration Screen
- Search Form for Trip Planning (Source, Destination, Time)
- Admin Login Screen

## 7.2 Output / Report Screens
*(Note: In the actual document, insert screenshots here)*
- Interactive Map View showing the planned route (using Leaflet).
- Admin Dashboard charts displaying passenger demand trends (using Recharts).
- Fleet Optimization Output Table.

---

# CHAPTER 8: CONCLUSION AND FUTURE SCOPE

## 8.1 Conclusion
The Transit AI System successfully demonstrates the application of modern software architecture and Artificial Intelligence in public transportation. By integrating a React frontend with a FastAPI backend powered by Machine Learning and Operations Research models, the system provides a robust solution for both commuters seeking efficient routes and administrators aiming to optimize fleet resources.

## 8.2 Limitations of the Project
- The current predictive model accuracy heavily relies on the quality of historical data.
- Real-time GPS tracking of vehicles is simulated and not connected to physical hardware in this phase.
- Weather and traffic anomalies are currently handled with basic heuristics rather than real-time API integrations.

## 8.3 Future Enhancements
- Integration with live GTFS (General Transit Feed Specification) real-time data.
- Mobile application deployment using React Native for better accessibility.
- Incorporating reinforcement learning for dynamic route adjustments in real-time.

---

# CHAPTER 9: REFERENCES

1. A. P. V. et al., "Machine Learning for Public Transport Demand Forecasting," *IEEE Transactions on Intelligent Transportation Systems*, vol. 22, no. 5, pp. 2800-2810, May 2021.
2. S. B. and M. N., "Optimization of Bus Fleet Allocation Using Linear Programming," *IEEE Access*, vol. 8, pp. 10234-10245, 2020.
3. FastAPI Documentation, available at: https://fastapi.tiangolo.com/
4. React Documentation, available at: https://reactjs.org/docs/getting-started.html
5. CatBoost Documentation, available at: https://catboost.ai/

---

# CHAPTER 10: APPENDIX

## Glossary
- **API**: Application Programming Interface
- **JWT**: JSON Web Token
- **ML**: Machine Learning
- **ORM**: Object Relational Mapping

## Sample Code Snippets
**Trip Routing Endpoint (FastAPI)**
```python
@app.get("/api/v1/route")
async def get_route(source: int, destination: int):
    # Logic to calculate shortest path using NetworkX
    path = calculate_shortest_path(source, destination)
    return {"status": "success", "route": path}
```
**Demand Prediction (CatBoost)**
```python
def predict_demand(route_id, hour):
    # Load pre-trained model and predict
    model = CatBoostRegressor().load_model("demand_model.cbm")
    features = [route_id, hour]
    prediction = model.predict(features)
    return max(0, int(prediction))
```
