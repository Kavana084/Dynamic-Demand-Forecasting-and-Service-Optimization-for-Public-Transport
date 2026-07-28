import React from 'react';
import { Outlet } from 'react-router-dom';
import AppNavbar from './Navbar';
import Sidebar from './Sidebar';
import { Container, Row, Col } from 'react-bootstrap';

import FloatingAssistant from './FloatingAssistant';

const Layout = () => {
  return (
    <div className="d-flex flex-column" style={{ minHeight: '100vh' }}>
      <AppNavbar />
      <div className="d-flex flex-grow-1 overflow-hidden">
        <Sidebar />
        <main className="flex-grow-1 bg-light p-4 overflow-auto" style={{ height: 'calc(100vh - 56px)' }}>
          <Outlet />
        </main>
      </div>
      <FloatingAssistant />
    </div>
  );
};

export default Layout;
