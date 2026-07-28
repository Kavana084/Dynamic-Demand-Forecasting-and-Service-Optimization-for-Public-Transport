import React, { useState } from 'react';
import { Container, Card, Form, Button, Row, Col } from 'react-bootstrap';

const Prediction = () => {
  const [formData, setFormData] = useState({
    routeId: '',
    hour: '',
    dayType: 'weekday',
    weatherCondition: 'clear'
  });
  const [result, setResult] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    // Simulate API call
    setResult({
      predictedPassengerCount: Math.floor(Math.random() * 150) + 20,
      confidenceScore: '92%',
      isPeakHour: parseInt(formData.hour) >= 8 && parseInt(formData.hour) <= 10
    });
  };

  return (
    <Container fluid>
      <h2 className="mb-4">Demand Prediction (CatBoost)</h2>
      
      <Row>
        <Col md={6}>
          <Card className="shadow-sm border-0 mb-4">
            <Card.Body>
              <Form onSubmit={handleSubmit}>
                <Form.Group className="mb-3">
                  <Form.Label>Route ID</Form.Label>
                  <Form.Control type="text" placeholder="e.g., 45" required 
                    onChange={e => setFormData({...formData, routeId: e.target.value})} />
                </Form.Group>
                
                <Form.Group className="mb-3">
                  <Form.Label>Hour of Day (0-23)</Form.Label>
                  <Form.Control type="number" min="0" max="23" required
                    onChange={e => setFormData({...formData, hour: e.target.value})} />
                </Form.Group>

                <Form.Group className="mb-3">
                  <Form.Label>Day Type</Form.Label>
                  <Form.Select onChange={e => setFormData({...formData, dayType: e.target.value})}>
                    <option value="weekday">Weekday</option>
                    <option value="weekend">Weekend</option>
                    <option value="holiday">Holiday</option>
                  </Form.Select>
                </Form.Group>

                <Form.Group className="mb-4">
                  <Form.Label>Weather Condition</Form.Label>
                  <Form.Select onChange={e => setFormData({...formData, weatherCondition: e.target.value})}>
                    <option value="clear">Clear</option>
                    <option value="rain">Rain</option>
                    <option value="storm">Storm</option>
                  </Form.Select>
                </Form.Group>

                <Button variant="primary" type="submit" className="w-100">
                  Predict Demand
                </Button>
              </Form>
            </Card.Body>
          </Card>
        </Col>

        <Col md={6}>
          {result ? (
            <Card className="shadow-sm border-0 bg-primary text-white mb-4">
              <Card.Header className="border-0 bg-transparent pt-4 pb-0">
                <h5 className="mb-0">Prediction Result</h5>
              </Card.Header>
              <Card.Body>
                <h1 className="display-4 fw-bold mb-3">{result.predictedPassengerCount} <small className="fs-5 fw-normal">passengers</small></h1>
                <div className="d-flex justify-content-between mb-2">
                  <span>Confidence Score:</span>
                  <strong>{result.confidenceScore}</strong>
                </div>
                <div className="d-flex justify-content-between">
                  <span>Peak Hour Indicator:</span>
                  <strong>{result.isPeakHour ? 'Yes' : 'No'}</strong>
                </div>
              </Card.Body>
            </Card>
          ) : (
            <Card className="shadow-sm border-0 mb-4 h-100 d-flex align-items-center justify-content-center text-muted p-5 text-center">
              Enter details and click Predict to see the CatBoost model output.
            </Card>
          )}
          
          <Card className="shadow-sm border-0 h-100 mt-4" style={{ minHeight: '200px' }}>
             <Card.Body className="d-flex align-items-center justify-content-center text-muted">
                Chart Space Reserved
             </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default Prediction;
