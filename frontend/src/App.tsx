import { Routes, Route } from 'react-router-dom'

// Placeholder components — replaced by real implementations in later plans
const Todo = ({ name }: { name: string }) => (
  <div style={{ padding: 32, fontFamily: 'monospace' }}>
    <h2>{name}</h2>
    <p>Placeholder — implementation in progress</p>
  </div>
)

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Todo name="LoginPage" />} />
      <Route path="/admin" element={<Todo name="AdminDashboard" />} />
      <Route path="/admin/users" element={<Todo name="UserManagementPage" />} />
      <Route path="/admin/courses" element={<Todo name="CourseManagementPage (admin)" />} />
      <Route path="/admin/security" element={<Todo name="SecurityPage" />} />
      <Route path="/admin/dev-tools" element={<Todo name="DevToolsPage" />} />
      <Route path="/admin/whitelabel" element={<Todo name="WhiteLabelPage" />} />
      <Route path="/creator" element={<Todo name="CreatorDashboard" />} />
      <Route path="/creator/courses" element={<Todo name="CourseManagementPage (creator)" />} />
      <Route path="/creator/learners" element={<Todo name="CreatorLearners" />} />
      <Route path="/courses/:id" element={<Todo name="CourseViewerPage" />} />
      <Route path="/learn" element={<Todo name="LearnerCatalogue" />} />
      <Route path="/learn/:id" element={<Todo name="CourseDetail" />} />
      <Route path="/" element={<Todo name="SmartRedirect" />} />
      <Route path="*" element={<Todo name="SmartRedirect (404)" />} />
    </Routes>
  )
}
