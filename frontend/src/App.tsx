import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DisplayPrefsProvider } from "./theme/DisplayPrefsProvider";
import { AuthProvider } from "./features/auth/AuthContext";
import { useAuth } from "./features/auth/useSession";
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
import CaseListPage from "./features/cases/CaseListPage";
import CaseEditorPage from "./features/cases/CaseEditorPage";
import RosterImportPage from "./features/admin/RosterImportPage";
import AuditLogPage from "./features/admin/AuditLogPage";
import CourseAdminPage from "./features/admin/CourseAdminPage";
import AdminHomePage from "./features/admin/AdminHomePage";
import AdminPeoplePage from "./features/admin/AdminPeoplePage";
import ReportsPage from "./features/admin/ReportsPage";
import DashboardPage from "./features/dashboard/DashboardPage";
import PatientPortalPage from "./features/portal/PatientPortalPage";
import TeachingPage from "./features/teaching/TeachingPage";
import LabCheckinPage from "./features/simLab/LabCheckinPage";
import AboutPage from "./features/about/AboutPage";
import NotFoundPage from "./pages/NotFoundPage";
import { homePathFor } from "./utils/permissions";

function LoginRoute() {
  const { session } = useAuth();
  if (!session) return <LoginPage />;
  if (session.mustChangePassword) return <Navigate to="/change-password" replace />;
  if (session.activeRole === "patient") return <Navigate to="/portal" replace />;
  if (session.activeRole === "admin" && !session.courseId) return <Navigate to="/admin" replace />;
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
            <Route path="/portal/preview" element={<PatientPortalPage previewMode />} />

            <Route element={<RequireAuth needsCourse={false} />}>
              <Route path="/change-password" element={<ChangePasswordPage />} />
              <Route path="/select-course" element={<SelectCoursePage />} />
            </Route>

            <Route element={<RequireAuth needsCourse={false} />}>
              <Route element={<AppShell />}>
                <Route path="/about" element={<AboutPage />} />
                <Route element={<RequireAuth roles={["admin"]} needsCourse={false} />}>
                  <Route path="/admin" element={<AdminHomePage />} />
                  <Route path="/admin/courses" element={<CourseAdminPage />} />
                  <Route path="/admin/people" element={<AdminPeoplePage />} />
                  <Route path="/admin/reports" element={<ReportsPage />} />
                  <Route path="/admin/activity" element={<AuditLogPage />} />
                </Route>

                <Route element={<RequireAuth roles={["patient"]} needsCourse={false} />}>
                  <Route path="/portal" element={<PatientPortalPage />} />
                </Route>

                <Route element={<RequireAuth />}>
                  <Route element={<RequireAuth roles={["student", "instructor", "course_coordinator"]} />}>
                    <Route path="/dashboard" element={<DashboardPage />} />
                  </Route>
                  <Route element={<RequireAuth roles={["student", "instructor", "course_coordinator", "front_desk"]} />}>
                    <Route path="/patients" element={<PatientListPage />} />
                    <Route path="/patients/:patientId" element={<PatientChartPage />} />
                  </Route>

                  <Route element={<RequireAuth roles={["student"]} />}>
                    <Route path="/patients/:patientId/notes/:noteId" element={<NoteEditorPage />} />
                    <Route path="/my-activity" element={<AuditLogPage />} />
                  </Route>

                  <Route element={<RequireAuth roles={["instructor", "course_coordinator"]} />}>
                    <Route path="/review" element={<ReviewQueuePage />} />
                    <Route path="/review/:noteId" element={<NoteReviewPage />} />
                  </Route>

                  <Route element={<RequireAuth roles={["instructor", "course_coordinator"]} />}>
                    <Route path="/teaching" element={<TeachingPage />} />
                    <Route path="/audit" element={<AuditLogPage />} />
                  </Route>

                  <Route element={<RequireAuth roles={["course_coordinator", "admin"]} />}>
                    <Route path="/admin/roster" element={<RosterImportPage />} />
                  </Route>

                  <Route element={<RequireAuth roles={["instructor", "course_coordinator"]} />}>
                    <Route path="/cases" element={<CaseListPage />} />
                    <Route path="/cases/new" element={<CaseEditorPage />} />
                    <Route path="/cases/:caseId" element={<CaseEditorPage />} />
                    <Route path="/lab-checkin" element={<LabCheckinPage />} />
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
