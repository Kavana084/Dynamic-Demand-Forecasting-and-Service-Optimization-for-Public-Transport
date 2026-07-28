import React, { useState } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert } from 'react-bootstrap';
import { Zap } from 'lucide-react';

const DynamicDecision = () => {
  const [formData, setFormData] = useState({});
  const [recommendation, setRecommendation] = useState(null);

  const handleGenerate = (e) => {
    e.preventDefault();
    setRecommendation({
      action: "Reallocate 3 buses from Route 12 to Route 45",
      priorityRoutes: ["Route 45", "Route 88"],
      expectedReward: "+14.5% Efficiency"
    });
  };

  return (
    <Container fluid>
      <div className="d-flex align-items-center mb-4">
        <h2 className="mb-0">Dynamic Decision Engine (DRL)</h2>
      </div>

      <Row>
        <Col md={5}>
          <Card className="shadow-sm border-0 mb-4">
            <Card.Header className="bg-white border-bottom">
              <h5 className="mb-0">Current State Inputs</h5>
            </Card.Header>
            <Card.Body>
              <Form onSubmit={handleGenerate}>
                <Form.Group className="mb-3">
                  <Form.Label>Traffic Level</Form.Label>
                  <Form.Select>
                    <option>Low</option>
                    <option>Moderate</option>
                    <option>High</option>
                    <option>Severe</option>
                  </Form.Select>
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Label>Weather Impact</Form.Label>
                  <Form.Select>
                    <option>None</option>
                    <option>Light Rain</option>
                    <option>Heavy Rain</option>
                  </Form.Select>
                </Form.Group>
                <Form.Group className="mb-4">
                  <Form.Label>Current Demand Spike Region</Form.Label>
                  <Form.Control type="text" placeholder="e.g., Downtown" />
                </Form.Group>
                <Button variant="dark" type="submit" className="w-100 d-flex justify-content-center align-items-center">
                  <Zap size={18} className="me-2" /> Generate Recommendation
                </Button>
              </Form>
            </Card.Body>
          </Card>
        </Col>

        <Col md={7}>
          {recommendation ? (
            <Card className="shadow-sm border-0 mb-4 bg-light border-start border-4 border-warning">
              <Card.Body className="p-4">
                <h4 className="text-dark mb-4">AI Recommended Action</h4>
                <Alert variant="warning" className="fs-5 text-center fw-bold border-warning">
                  {recommendation.action}
                </Alert>
                <Row className="mt-4">
                  <Col sm={6}>
                    <p className="text-muted mb-1">Priority Routes</p>
                    <h5 className="mb-0">{recommendation.priorityRoutes.join(', ')}</h5>
                  </Col>
                  <Col sm={6}>
                    <p className="text-muted mb-1">Expected Reward Score</p>
                    <h5 className="mb-0 text-success">{recommendation.expectedReward}</h5>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          ) : (
             <Card className="shadow-sm border-0 h-100 d-flex align-items-center justify-content-center text-muted p-5 text-center">
              Input current state variables to generate dynamic DRL recommendations.
            </Card>
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default DynamicDecision;
