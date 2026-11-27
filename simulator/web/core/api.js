// Poziv servera (eurosim/server.py): bez tela GET, sa telom POST JSON. Greška servera ({error}) ili HTTP greška ->
// Error sa .data (odgovor) i .status. esc: tekst sa servera (ili iz fajla) bezbedno u HTML.
export async function api(path, body) {
  const r = await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const d = await r.json();
  if (!r.ok || d.error) { const e = new Error(d.error || r.statusText); e.data = d; e.status = r.status; throw e; }
  return d;
}

export const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
