import { Navigate, Outlet, useLocation } from "react-router-dom";
import type { Role } from "../../types";
import { homePathFor } from "../../utils/permissions";
import { useAuth } from "./useSession";

interface Props {
  roles?: Role[];
  needsCourse?: boolean;
}

export default function RequireAuth({ roles, needsCourse = true }: Props) {
  const { session } = useAuth();
  const location = useLocation();

  if (!session) return <Navigate to="/" replace state={{ from: location.pathname }} />;
  if (session.mustChangePassword && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }
  if (needsCourse && !session.courseId) return <Navigate to="/select-course" replace />;
  if (roles && !roles.includes(session.activeRole)) {
    return <Navigate to={homePathFor(session.activeRole)} replace />;
  }
  return <Outlet />;
}
