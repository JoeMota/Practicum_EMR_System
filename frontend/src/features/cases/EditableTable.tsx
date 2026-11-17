import { Button, IconButton, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";
import DeleteOutlined from "@mui/icons-material/DeleteOutlined";

export interface Column {
  key: string;
  label: string;
  type?: "text" | "date" | "select";
  options?: string[];
}

interface Props {
  label: string;
  addLabel: string;
  columns: Column[];
  rows: Record<string, string>[];
  blank: Record<string, string>;
  onChange: (rows: Record<string, string>[]) => void;
}

export default function EditableTable({ label, addLabel, columns, rows, blank, onChange }: Props) {
  const update = (index: number, key: string, value: string) => {
    onChange(rows.map((row, i) => (i === index ? { ...row, [key]: value } : row)));
  };

  return (
    <>
      <Typography component="h3" variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>{label}</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            {columns.map((column) => <TableCell key={column.key}>{column.label}</TableCell>)}
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, index) => (
            <TableRow key={row.id}>
              {columns.map((column) => (
                <TableCell key={column.key} sx={{ minWidth: column.type === "date" ? 150 : 120 }}>
                  {column.type === "select" ? (
                    <TextField
                      select size="small" fullWidth value={row[column.key] ?? ""}
                      onChange={(e) => update(index, column.key, e.target.value)}
                      slotProps={{ select: { native: true } }}
                      aria-label={`${label} ${column.label}`}
                    >
                      <option value="" />
                      {column.options?.map((option) => <option key={option} value={option}>{option}</option>)}
                    </TextField>
                  ) : (
                    <TextField
                      size="small" fullWidth type={column.type === "date" ? "date" : "text"}
                      value={row[column.key] ?? ""}
                      onChange={(e) => update(index, column.key, e.target.value)}
                      aria-label={`${label} ${column.label}`}
                    />
                  )}
                </TableCell>
              ))}
              <TableCell>
                <IconButton
                  aria-label={`Remove ${label} row`}
                  onClick={() => onChange(rows.filter((_, i) => i !== index))}
                >
                  <DeleteOutlined fontSize="small" />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Button
        size="small" sx={{ mt: 1 }}
        onClick={() => onChange([...rows, { ...blank, id: crypto.randomUUID() }])}
      >
        Add {addLabel}
      </Button>
    </>
  );
}
