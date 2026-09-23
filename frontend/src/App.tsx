import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DisplayPrefsProvider } from "./theme/DisplayPrefsProvider";
import { AuthProvider, useAuth } from "./features/auth/AuthContext";
import RequireAuth from "./features/auth/RequireAuth";
import LoginPage from "./features/auth/LoginPage";
import SelectCoursePage from "./features/auth/SelectCoursePage";
import ChangePasswordPage from "./features/auth/ChangePasswordPage";
import AppShell from "./components/AppShell";
import PatientListPage from "./features/patients/PatientListPage";
import PatientChartPage from "./features/patients/PatientChartPage";
import NoteEditorPage from "./features/encounters/NoteEditorPage";
import ReviewQueuePage from "./features/encounters/ReviewQueuePage";
import NoteReviewPage from "./features/encounters/NoteReviewPage";
import RosterImportPage from "./features/admin/RosterImportPage";
import AuditLogPage from "./features/admin/AuditLogPage";
import NotFoundPage from "./pages/NotFoundPage";
import { homePathFor } from "./utils/permissions";

function LoginRoute() {
  const { session } = useAuth();
  if (!session) return <LoginPage />;
  if (session.user.mustChangePassword) return <Navigate to="/change-password" replace />;
  if (!session.courseId) return <Navigate to="/select-course" replace />;
  return <Navigate to={homePathFor(session.activeRole)} replace />;
}

export default function App() {
  return (
    <DisplayPrefsProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LoginRoute />} />

            <Route element={<RequireAuth needsCourse={false} allowTempPassword />}>
              <Route path="/change-password" element={<ChangePasswordPage />} />
            </Route>

            <Route element={<RequireAuth needsCourse={false} />}>
              <Route path="/select-course" element={<SelectCoursePage />} />
            </Route>

            <Route element={<RequireAuth />}>
              <Route element={<AppShell />}>
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
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </DisplayPrefsProvider>
  );
}
