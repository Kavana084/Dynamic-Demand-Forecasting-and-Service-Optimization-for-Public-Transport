import React, { useEffect, useState } from 'react';
import { Navbar, Container, Badge } from 'react-bootstrap';
import { testConnection } from '../api/api';

const AppNavbar = () => {
  const [status, setStatus] = useState('Checking...');
  const [isOnline, setIsOnline] = useState(false);

  useEffect(() => {
    const checkStatus = async () => {
      try {
        await testConnection();
        setStatus('Online');
        setIsOnline(true);
      } catch (error) {
        setStatus('Offline');
        setIsOnline(false);
      }
    };
    checkStatus();
  }, []);

  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="border-bottom sticky-top">
      <Container fluid>
        <Navbar.Brand href="/">Smart Public Transit Optimization System</Navbar.Brand>
        <Navbar.Toggle />
        <Navbar.Collapse className="justify-content-end">
          <Navbar.Text>
            Backend Status:{' '}
            <Badge bg={isOnline ? 'success' : 'danger'}>
              {isOnline ? '🟢 ' : '🔴 '}
              {status}
            </Badge>
          </Navbar.Text>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default AppNavbar;
