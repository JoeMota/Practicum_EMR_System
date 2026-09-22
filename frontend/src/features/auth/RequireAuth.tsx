import { Navigate, Outlet, useLocation } from "react-router-dom";
import type { Role } from "../../types";
import { homePathFor } from "../../utils/permissions";
import { useAuth } from "./AuthContext";

interface Props {
  roles?: Role[];
  /** Most screens are scoped to a course; the course picker itself is not. */
  needsCourse?: boolean;
  /** Allow the change-password screen even when mustChangePassword is true. */
  allowTempPassword?: boolean;
}

export default function RequireAuth({ roles, needsCourse = true, allowTempPassword = false }: Props) {
  const { session } = useAuth();
  const location = useLocation();

  if (!session) return <Navigate to="/" replace state={{ from: location.pathname }} />;
  if (session.user.mustChangePassword && !allowTempPassword) {
    return <Navigate to="/change-password" replace />;
  }
  if (needsCourse && !session.courseId) return <Navigate to="/select-course" replace />;
  if (roles && !roles.includes(session.activeRole)) {
    return <Navigate to={homePathFor(session.activeRole)} replace />;
  }
  return <Outlet />;
}
