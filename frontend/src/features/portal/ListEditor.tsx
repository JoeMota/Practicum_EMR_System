import AddOutlined from "@mui/icons-material/AddOutlined";
import DeleteOutlineOutlined from "@mui/icons-material/DeleteOutlineOutlined";
import { Box, Button, IconButton, MenuItem, Stack, TextField, Typography } from "@mui/material";

export interface ListEditorField<T extends object> {
  key: keyof T;
  label: string;
  options?: readonly string[];
}

interface ListEditorProps<T extends object> {
  label: string;
  path: string;
  rows: T[];
  fields: ListEditorField<T>[];
  maxRows: number;
  disabled?: boolean;
  createRow: () => T;
  onChange: (rows: T[]) => void;
  errorFor?: (path: string) => string | undefined;
}

export default function ListEditor<T extends object>({
  label, path, rows, fields, maxRows, disabled = false, createRow, onChange, errorFor,
}: ListEditorProps<T>) {
  const setValue = (rowIndex: number, key: keyof T, value: string) => {
    onChange(rows.map((row, index) => index === rowIndex ? { ...row, [key]: value } as T : row));
  };

  const valueOf = (row: T, key: keyof T) => {
    const value = (row as Record<string, unknown>)[String(key)];
    return typeof value === "string" ? value : "";
  };

  return (
    <Stack spacing={1.25}>
      <Typography variant="subtitle2">{label}</Typography>
      {rows.map((row, index) => (
        <Box
          key={`${path}-${index}`}
          sx={{
            display: "grid",
            gap: 1.5,
            alignItems: "start",
            gridTemplateColumns: { xs: "1fr auto", sm: `repeat(${fields.length}, minmax(0, 1fr)) auto` },
          }}
        >
          {fields.map((field) => {
            const error = errorFor?.(`${path}.${index}.${String(field.key)}`);
            return (
              <TextField
                key={String(field.key)}
                select={Boolean(field.options)}
                label={field.label}
                value={valueOf(row, field.key)}
                disabled={disabled}
                error={Boolean(error)}
                helperText={error}
                onChange={(event) => setValue(index, field.key, event.target.value)}
              >
                {field.options?.map((option) => (
                  <MenuItem key={option} value={option}>{option || "Select"}</MenuItem>
                ))}
              </TextField>
            );
          })}
          <IconButton
            aria-label={`Remove ${label.toLowerCase()} ${index + 1}`}
            title={`Remove ${label.toLowerCase()} ${index + 1}`}
            disabled={disabled}
            onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}
            sx={{ minWidth: 44, minHeight: 44 }}
          >
            <DeleteOutlineOutlined />
          </IconButton>
        </Box>
      ))}
      {rows.length < maxRows && (
        <Button
          type="button"
          variant="outlined"
          size="small"
          startIcon={<AddOutlined />}
          disabled={disabled}
          onClick={() => onChange([...rows, createRow()])}
          sx={{ alignSelf: "flex-start" }}
        >
          Add {label.toLowerCase()}
        </Button>
      )}
    </Stack>
  );
}
