import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ProjectListPage from './pages/ProjectListPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import ProjectBoardPage from './pages/ProjectBoardPage'
import InterviewListPage from './pages/InterviewListPage'
import InterviewDetailPage from './pages/InterviewDetailPage'
import UploadPage from './pages/UploadPage'

// Board page has its own full-screen dark layout
function App() {
  return (
    <Routes>
      <Route path="/projects/:id/board" element={<ProjectBoardPage />} />
      <Route path="/*" element={<LayoutRoutes />} />
    </Routes>
  )
}

function LayoutRoutes() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ProjectListPage />} />
        <Route path="/projects/:id" element={<ProjectDetailPage />} />
        <Route path="/interviews" element={<InterviewListPage />} />
        <Route path="/interviews/:id" element={<InterviewDetailPage />} />
        <Route path="/upload" element={<UploadPage />} />
      </Routes>
    </Layout>
  )
}

export default App
