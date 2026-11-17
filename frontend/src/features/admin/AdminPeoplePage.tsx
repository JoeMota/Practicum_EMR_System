import { useState } from "react";
import { Box, Card, CardActionArea, CardContent, LinearProgress, Stack, Typography } from "@mui/material";
import { listCoursesForUser } from "../../api/courses";
import { useSession } from "../auth/useSession";
import { useAsync } from "../../utils/useAsync";
import { usePageHeading } from "../../components/usePageHeading";
import PageError from "../../components/PageError";
import RosterImportPage from "./RosterImportPage";

export default function AdminPeoplePage() {
  usePageHeading("People");
  const { user } = useSession();
  const courses = useAsync(() => listCoursesForUser(), [user.id]);
  const [courseId, setCourseId] = useState<string>();

  if (courses.error) return <PageError error={courses.error} />;
  if (!courses.data) return <LinearProgress aria-label="Loading classes" />;

  const selected = courses.data.find((course) => course.id === courseId);

  return (
    <Stack spacing={2.5}>
      <Box>
        <Typography variant="body2" color="text.secondary">
          Pick a class, then enroll someone who already has an account or create one for that class.
        </Typography>
      </Box>
      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
        {courses.data.map((course) => (
          <Card key={course.id} sx={{ minWidth: 180, borderWidth: course.id === courseId ? 2 : 1, borderColor: course.id === courseId ? "primary.main" : "divider" }}>
            <CardActionArea onClick={() => setCourseId(course.id)}>
              <CardContent>
                <Typography variant="subtitle2">{course.code}</Typography>
                <Typography variant="caption" color="text.secondary">{course.term}</Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        ))}
        {courses.data.length === 0 && (
          <Typography variant="body2" color="text.secondary">Create a class before adding people.</Typography>
        )}
      </Box>
      {selected && <RosterImportPage courseId={selected.id} />}
    </Stack>
  );
}
