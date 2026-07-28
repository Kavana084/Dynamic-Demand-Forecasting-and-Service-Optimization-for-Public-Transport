import React from 'react';
import { Container, Row, Col } from 'react-bootstrap';
import ChatWidget from '../components/ChatWidget';

const Chatbot = () => {
  return (
    <Container fluid className="h-100 d-flex flex-column">
      <h2 className="mb-4">AI Transit Assistant</h2>
      <Row className="flex-grow-1">
        <Col md={8} lg={6} className="mx-auto h-100 pb-4">
          <ChatWidget />
        </Col>
      </Row>
    </Container>
  );
};

export default Chatbot;
