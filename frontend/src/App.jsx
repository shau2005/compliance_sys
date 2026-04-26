import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';

function AppContent() {
  const [analysisData, setAnalysisData] = useState(null);
  const navigate = useNavigate();

  const handleAnalysisComplete = (data) => {
    setAnalysisData(data);
    navigate('/dashboard');
  };

  const handleReset = () => {
    setAnalysisData(null);
    navigate('/');
  };

  return (
    <AnimatePresence mode="wait">
      <Routes>
        <Route 
          path="/" 
          element={<Onboarding onComplete={handleAnalysisComplete} />} 
        />
        <Route 
          path="/dashboard" 
          element={
            analysisData ? (
              <Dashboard data={analysisData} onReset={handleReset} />
            ) : (
              <div className="flex h-screen items-center justify-center text-secondary">
                <div className="text-center">
                  <p className="mb-4">No analysis data found.</p>
                  <button 
                    onClick={handleReset}
                    className="px-4 py-2 bg-elevated border-subtle rounded-md hover:bg-surface"
                  >
                    Go Back
                  </button>
                </div>
              </div>
            )
          } 
        />
      </Routes>
    </AnimatePresence>
  );
}

export default function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}
