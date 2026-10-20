import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DisplayPrefsProvider } from "./theme/DisplayPrefsProvider";
import { AuthProvider, useAuth } from "./features/auth/AuthContext";
import RequireAuth from "./features/auth/RequireAuth";
import LoginPage from "./features/auth/LoginPage";
import ChangePasswordPage from "./features/auth/ChangePasswordPage";
import SelectCoursePage from "./features/auth/SelectCoursePage";
import AppShell from "./components/AppShell";
import PatientListPage from "./features/patients/PatientListPage";
import PatientChartPage from "./features/patients/PatientChartPage";
import NoteEditorPage from "./features/encounters/NoteEditorPage";
import ReviewQueuePage from "./features/encounters/ReviewQueuePage";
import NoteReviewPage from "./features/encounters/NoteReviewPage";
import RosterImportPage from "./features/admin/RosterImportPage";
import AuditLogPage from "./features/admin/AuditLogPage";
import CourseAdminPage from "./features/admin/CourseAdminPage";
import ReportsPage from "./features/admin/ReportsPage";
import DashboardPage from "./features/dashboard/DashboardPage";
import NotFoundPage from "./pages/NotFoundPage";
import { homePathFor } from "./utils/permissions";

function LoginRoute() {
  const { session } = useAuth();
  if (!session) return <LoginPage />;
  if (session.mustChangePassword) return <Navigate to="/change-password" replace />;
  if (session.activeRole === "admin" && !session.courseId) return <Navigate to="/admin/courses" replace />;
  if (session.courseId) return <Navigate to={homePathFor(session.activeRole)} replace />;
  return <Navigate to="/select-course" replace />;
}

export default function App() {
  return (
    <DisplayPrefsProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LoginRoute />} />

            <Route element={<RequireAuth needsCourse={false} />}>
              <Route path="/change-password" element={<ChangePasswordPage />} />
              <Route path="/select-course" element={<SelectCoursePage />} />
            </Route>

            <Route element={<RequireAuth needsCourse={false} />}>
              <Route element={<AppShell />}>
                <Route element={<RequireAuth roles={["admin"]} needsCourse={false} />}>
                  <Route path="/admin/courses" element={<CourseAdminPage />} />
                  <Route path="/admin/reports" element={<ReportsPage />} />
                </Route>

                <Route element={<RequireAuth />}>
                  <Route element={<RequireAuth roles={["student", "instructor"]} />}>
                    <Route path="/dashboard" element={<DashboardPage />} />
                  </Route>
                  <Route path="/patients" element={<PatientListPage />} />
                  <Route path="/patients/:patientId" element={<PatientChartPage />} />

                  <Route element={<RequireAuth roles={["student"]} />}>
                    <Route path="/patients/:patientId/notes/:noteId" element={<NoteEditorPage />} />
                  </Route>

                  <Route element={<RequireAuth roles={["instructor"]} />}>
                    <Route path="/review" element={<ReviewQueuePage />} />
                    <Route path="/review/:noteId" element={<NoteReviewPage />} />
                  </Route>

                  <Route element={<RequireAuth roles={["instructor", "admin"]} />}>
                    <Route path="/admin/roster" element={<RosterImportPage />} />
                    <Route path="/audit" element={<AuditLogPage />} />
                  </Route>

                  <Route path="*" element={<NotFoundPage />} />
                </Route>
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </DisplayPrefsProvider>
  );
}
