import React from 'react';
import { Alert } from 'react-bootstrap';

const ErrorAlert = ({ message, onClose }) => {
  if (!message) return null;
  
  return (
    <Alert variant="danger" onClose={onClose} dismissible={!!onClose}>
      <Alert.Heading>Error</Alert.Heading>
      <p className="mb-0">{message}</p>
    </Alert>
  );
};

export default ErrorAlert;
