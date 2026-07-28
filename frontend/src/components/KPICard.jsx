import React from 'react';
import { Card } from 'react-bootstrap';

const KPICard = ({ title, value, icon: Icon, color = "primary" }) => {
  return (
    <Card className="shadow-sm border-0 mb-4 h-100">
      <Card.Body className="d-flex align-items-center">
        <div className={`rounded-circle bg-${color} bg-opacity-10 p-3 me-3 text-${color}`}>
          {Icon && <Icon size={24} />}
        </div>
        <div>
          <h6 className="text-muted mb-1">{title}</h6>
          <h3 className="mb-0 fw-bold">{value}</h3>
        </div>
      </Card.Body>
    </Card>
  );
};

export default KPICard;
