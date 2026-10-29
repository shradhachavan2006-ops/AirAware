import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { DatasetProvider } from './context/DatasetContext';
import Layout from './Layout';
import Overview from './pages/Overview';
import Trends from './pages/Trends';
import Statistics from './pages/Statistics';
import Evaluation from './pages/Evaluation';
import Forecast from './pages/Forecast';
import DatasetManager from './pages/DatasetManager';
import DataQuality from './pages/DataQuality';
import StatAnalysis from './pages/StatAnalysis';
import Regression from './pages/Regression';
import Methodology from './pages/Methodology';

export default function App() {
  return (
    <DatasetProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            {/* Default → Overview */}
            <Route index element={<Navigate to="/overview" replace />} />

            {/* Existing pages */}
            <Route path="overview"    element={<Overview />}    />
            <Route path="trends"      element={<Trends />}      />
            <Route path="statistics"  element={<Statistics />}  />
            <Route path="evaluation"  element={<Evaluation />}  />
            <Route path="forecast"    element={<Forecast />}    />

            {/* V2 new pages */}
            <Route path="datasets"      element={<DatasetManager />} />
            <Route path="quality"       element={<DataQuality />}    />
            <Route path="stat-analysis" element={<StatAnalysis />}   />
            <Route path="regression"    element={<Regression />}     />
            <Route path="methodology"   element={<Methodology />}    />

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/overview" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </DatasetProvider>
  );
}
