import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './Layout';
import Overview from './pages/Overview';
import Trends from './pages/Trends';
import Statistics from './pages/Statistics';
import Evaluation from './pages/Evaluation';
import Forecast from './pages/Forecast';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="trends" element={<Trends />} />
          <Route path="statistics" element={<Statistics />} />
          <Route path="evaluation" element={<Evaluation />} />
          <Route path="forecast" element={<Forecast />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
