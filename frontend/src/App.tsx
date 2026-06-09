import { Routes, Route } from 'react-router-dom';
import { Layout } from '@/components/layout/Layout';
import { Dashboard } from '@/pages/Dashboard';
import { UploadPage } from '@/pages/Upload';
import { ContractDetail } from '@/pages/ContractDetail';
import { SearchPage } from '@/pages/Search';
import { ReviewPage } from '@/pages/Review';
import { ReviewHistoryPage } from '@/pages/ReviewHistory';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/contracts/:id" element={<ContractDetail />} />
        <Route path="/contracts/:id/review" element={<ReviewPage />} />
        <Route path="/contracts/:id/reviews" element={<ReviewHistoryPage />} />
        <Route path="/search" element={<SearchPage />} />
      </Route>
    </Routes>
  );
}
