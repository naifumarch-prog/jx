import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import HomePage from './pages/HomePage';
import DashboardPage from './pages/DashboardPage';
import CreateLinkPage from './pages/CreateLinkPage';
import LinkDetailsPage from './pages/LinkDetailsPage';
import PricingPage from './pages/PricingPage';
import AdminPage from './pages/AdminPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import { checkAuthStatus } from './services/api';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const verifyAuth = async () => {
      try {
        const userData = await checkAuthStatus();
        setIsAuthenticated(true);
        setUser(userData);
      } catch (error) {
        setIsAuthenticated(false);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    verifyAuth();
  }, []);

  if (loading) {
    return <div className="min-h-screen bg-gray-50 flex items-center justify-center">Memuat...</div>;
  }

  return (
    <Router>
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Toaster position="top-right" />
        <Navbar isAuthenticated={isAuthenticated} user={user} />
        
        <main className="flex-grow">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            
            {/* Protected Routes */}
            <Route 
              path="/dashboard" 
              element={isAuthenticated ? <DashboardPage user={user} /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/create-link" 
              element={isAuthenticated ? <CreateLinkPage user={user} /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/link/:linkId" 
              element={isAuthenticated ? <LinkDetailsPage user={user} /> : <Navigate to="/login" />} 
            />
            <Route 
              path="/pricing" 
              element={isAuthenticated ? <PricingPage user={user} /> : <Navigate to="/login" />} 
            />
            
            {/* Admin Route */}
            <Route 
              path="/admin" 
              element={user?.role === 'admin' ? <AdminPage user={user} /> : <Navigate to="/dashboard" />} 
            />
            
            {/* Catch all */}
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </main>
        
        <Footer />
      </div>
    </Router>
  );
}

export default App;