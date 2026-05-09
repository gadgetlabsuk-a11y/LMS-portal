import { useEffect } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import { setNavigate } from '@/services/api'

// Layouts
import { AdminLayout } from '@/components/layout/AdminLayout'
import { LearnerLayout } from '@/components/layout/LearnerLayout'
import { CreatorLayout } from '@/components/layout/CreatorLayout'

// Auth
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { SmartRedirect } from '@/components/auth/SmartRedirect'

// Pages
import { LoginPage } from '@/pages/LoginPage'
import { AdminDashboard } from '@/pages/admin/AdminDashboard'
import { UserManagementPage } from '@/pages/admin/UserManagementPage'
import { CourseManagementPage } from '@/pages/admin/CourseManagementPage'
import { SecurityPage } from '@/pages/admin/SecurityPage'
import { DevToolsPage } from '@/pages/admin/DevToolsPage'
import { WhiteLabelPage } from '@/pages/admin/WhiteLabelPage'
import { CreatorDashboard } from '@/pages/creator/CreatorDashboard'
import { CreatorCourseListPage } from '@/pages/creator/CreatorCourseListPage'
import { CourseBuilderPage } from '@/pages/creator/CourseBuilderPage'
import { ModuleDetailPage } from '@/pages/creator/ModuleDetailPage'
import { SlideBuilderPage } from '@/pages/creator/SlideBuilderPage'
import { SlideEditorPage } from '@/pages/creator/SlideEditorPage'
import { CreatorLearners } from '@/pages/creator/CreatorLearners'
import { LearnerCatalogue } from '@/pages/learn/LearnerCatalogue'
import { CourseDetail } from '@/pages/learn/CourseDetail'
import { CourseViewerPage } from '@/pages/CourseViewerPage'

export default function App() {
  const navigate = useNavigate()

  // Wire the api service's 401 handler to React Router's navigate.
  // This replaces the monolith's window.history.pushState + PopStateEvent pattern.
  useEffect(() => {
    setNavigate(navigate)
  }, [navigate])

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Admin routes */}
      <Route
        path="/admin"
        element={
          <AdminLayout>
            <ProtectedRoute adminOnly>
              <AdminDashboard />
            </ProtectedRoute>
          </AdminLayout>
        }
      />
      <Route
        path="/admin/users"
        element={
          <AdminLayout>
            <ProtectedRoute adminOnly>
              <UserManagementPage />
            </ProtectedRoute>
          </AdminLayout>
        }
      />
      <Route
        path="/admin/courses"
        element={
          <AdminLayout>
            <ProtectedRoute adminOnly>
              <CourseManagementPage />
            </ProtectedRoute>
          </AdminLayout>
        }
      />
      <Route
        path="/admin/security"
        element={
          <AdminLayout>
            <ProtectedRoute adminOnly>
              <SecurityPage />
            </ProtectedRoute>
          </AdminLayout>
        }
      />
      <Route
        path="/admin/dev-tools"
        element={
          <AdminLayout>
            <ProtectedRoute adminOnly>
              <DevToolsPage />
            </ProtectedRoute>
          </AdminLayout>
        }
      />
      <Route
        path="/admin/whitelabel"
        element={
          <AdminLayout>
            <ProtectedRoute adminOnly>
              <WhiteLabelPage />
            </ProtectedRoute>
          </AdminLayout>
        }
      />

      {/* Creator routes */}
      <Route
        path="/creator"
        element={
          <CreatorLayout>
            <ProtectedRoute creatorRoute>
              <CreatorDashboard />
            </ProtectedRoute>
          </CreatorLayout>
        }
      />
      <Route
        path="/creator/courses"
        element={
          <CreatorLayout>
            <ProtectedRoute creatorRoute>
              <CreatorCourseListPage />
            </ProtectedRoute>
          </CreatorLayout>
        }
      />
      <Route
        path="/creator/courses/:id/builder"
        element={
          <CreatorLayout>
            <ProtectedRoute creatorRoute>
              <CourseBuilderPage />
            </ProtectedRoute>
          </CreatorLayout>
        }
      />
      <Route
        path="/creator/courses/:id/modules/:moduleId"
        element={
          <CreatorLayout>
            <ProtectedRoute creatorRoute>
              <ModuleDetailPage />
            </ProtectedRoute>
          </CreatorLayout>
        }
      />
      <Route
        path="/creator/courses/:id/videos/:videoId/slides"
        element={
          <CreatorLayout>
            <ProtectedRoute creatorRoute>
              <SlideBuilderPage />
            </ProtectedRoute>
          </CreatorLayout>
        }
      />
      <Route
        path="/creator/courses/:id/videos/:videoId/slides/:slideId/editor"
        element={
          <CreatorLayout>
            <ProtectedRoute creatorRoute>
              <SlideEditorPage />
            </ProtectedRoute>
          </CreatorLayout>
        }
      />
      <Route
        path="/creator/learners"
        element={
          <CreatorLayout>
            <ProtectedRoute creatorRoute>
              <CreatorLearners />
            </ProtectedRoute>
          </CreatorLayout>
        }
      />

      {/* Course viewer (no layout wrapper — full-screen) */}
      <Route
        path="/courses/:id"
        element={
          <ProtectedRoute>
            <CourseViewerPage />
          </ProtectedRoute>
        }
      />

      {/* Learner routes */}
      <Route
        path="/learn"
        element={
          <LearnerLayout>
            <ProtectedRoute>
              <LearnerCatalogue />
            </ProtectedRoute>
          </LearnerLayout>
        }
      />
      <Route
        path="/learn/:id"
        element={
          <LearnerLayout>
            <ProtectedRoute>
              <CourseDetail />
            </ProtectedRoute>
          </LearnerLayout>
        }
      />

      {/* Catch-all */}
      <Route path="/" element={<SmartRedirect />} />
      <Route path="*" element={<SmartRedirect />} />
    </Routes>
  )
}
