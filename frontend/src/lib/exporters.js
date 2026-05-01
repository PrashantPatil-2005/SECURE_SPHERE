function csvEscape(v) {
  if (v === null || v === undefined) return '';
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function pickColumns(rows, columns) {
  if (columns && columns.length) return columns;
  const set = new Set();
  for (const r of rows.slice(0, 50)) {
    if (r && typeof r === 'object') {
      for (const k of Object.keys(r)) set.add(k);
    }
  }
  return Array.from(set);
}

function downloadBlob(content, filename, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function timestamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

export function exportCsv(rows, { filename = 'export', columns } = {}) {
  if (!Array.isArray(rows) || rows.length === 0) return;
  const cols = pickColumns(rows, columns);
  const head = cols.map(csvEscape).join(',');
  const body = rows
    .map((r) => cols.map((c) => csvEscape(r?.[c])).join(','))
    .join('\n');
  const csv = `${head}\n${body}\n`;
  downloadBlob(csv, `${filename}-${timestamp()}.csv`, 'text/csv;charset=utf-8');
}

export function exportJson(data, { filename = 'export', pretty = true } = {}) {
  const json = JSON.stringify(data, null, pretty ? 2 : 0);
  downloadBlob(json, `${filename}-${timestamp()}.json`, 'application/json');
}
