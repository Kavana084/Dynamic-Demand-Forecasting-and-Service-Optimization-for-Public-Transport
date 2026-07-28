import React, { useState } from 'react';
import { Container, Row, Col, Card, Form, Button, Table, Badge } from 'react-bootstrap';

const FleetOptimization = () => {
  const [formData, setFormData] = useState({
    buses: '',
    capacity: '40',
    budget: ''
  });
  const [result, setResult] = useState(null);

  const handleOptimize = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/optimize_fleet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (response.ok) {
        const data = await response.json();
        setResult(data);
      } else {
        setResult({ pending: true });
      }
    } catch (error) {
      console.error("Fleet optimization API error", error);
      setResult({ pending: true });
    }
  };

  return (
    <Container fluid>
      <h2 className="mb-4">Fleet Optimization (MILP)</h2>
      
      <Row>
        <Col lg={4}>
          <Card className="shadow-sm border-0 mb-4">
            <Card.Header className="bg-white border-bottom">
              <h5 className="mb-0">Parameters</h5>
            </Card.Header>
            <Card.Body>
              <Form onSubmit={handleOptimize}>
                <Form.Group className="mb-3">
                  <Form.Label>Total Available Buses</Form.Label>
                  <Form.Control type="number" required placeholder="e.g., 50" 
                    onChange={e => setFormData({...formData, buses: e.target.value})} />
                </Form.Group>
                
                <Form.Group className="mb-3">
                  <Form.Label>Standard Bus Capacity</Form.Label>
                  <Form.Control type="number" defaultValue="40" required 
                    onChange={e => setFormData({...formData, capacity: e.target.value})} />
                </Form.Group>

                <Form.Group className="mb-4">
                  <Form.Label>Budget Constraint ($)</Form.Label>
                  <Form.Control type="number" placeholder="Optional" 
                    onChange={e => setFormData({...formData, budget: e.target.value})} />
                </Form.Group>

                <Button variant="primary" type="submit" className="w-100">
                  Run Optimization
                </Button>
              </Form>
            </Card.Body>
          </Card>
        </Col>

        <Col lg={8}>
          {result?.pending ? (
            <Card className="shadow-sm border-0 mb-4 h-100 d-flex align-items-center justify-content-center text-muted p-5 text-center">
              Backend integration pending for Fleet Optimization. Please ensure the endpoint /api/optimize_fleet is fully supported.
            </Card>
          ) : result ? (
            <Card className="shadow-sm border-0 mb-4">
              <Card.Header className="bg-white border-bottom d-flex justify-content-between align-items-center">
                <h5 className="mb-0">Recommended Fleet Allocation</h5>
                <Badge bg="success">Utilization: {result.utilization || result.overall_utilization || 'N/A'}</Badge>
              </Card.Header>
              <Card.Body className="p-0">
                <Table responsive hover className="mb-0">
                  <thead className="bg-light">
                    <tr>
                      <th className="px-4 py-3">Route</th>
                      <th className="py-3">Predicted Demand</th>
                      <th className="py-3">Buses Allocated</th>
                      <th className="px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(result.distribution || result.routes || []).map((item, idx) => (
                      <tr key={idx}>
                        <td className="px-4 py-3 fw-bold">{item.route_name || item.route}</td>
                        <td className="py-3">{item.demand || item.predicted_demand}</td>
                        <td className="py-3 fw-bold text-primary">{item.allocated || item.allocated_buses}</td>
                        <td className="px-4 py-3">
                          <Badge bg={(item.status || item.allocation_status) === 'Optimal' ? 'success' : 'warning'}>
                            {item.status || item.allocation_status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </Card.Body>
            </Card>
          ) : (
            <Card className="shadow-sm border-0 mb-4 h-100 d-flex align-items-center justify-content-center text-muted p-5 text-center">
              Run the optimizer to view route-wise bus distribution recommendations.
            </Card>
          )}
        </Col>
      </Row>
    </Container>
  );
};

export default FleetOptimization;
