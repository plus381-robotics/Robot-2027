// Segmentirano dugme (npr. Žuta | Plava, meč | test) nad postojećim <select>-om: select ostaje izvor istine (skriven;
// app.js ga čita i sluša kao do sada). Klik na deo postavi select.value i pošalje 'change' (isti slušaoci kao ranije);
// promena selecta spolja: 'change', ili 'seg-sync' kad kod postavi .value bez događaja.
//   segmented(select, {id, cls, labels: {value: tekst}, titles: {value: opis}, title}) -> span.seg

export function segmented(select, { id, cls, labels = {}, titles = {}, title } = {}) {
  const box = document.createElement('span');
  box.className = 'seg' + (cls ? ' ' + cls : '');
  if (id) box.id = id;
  box.setAttribute('role', 'group');
  if (title) box.title = title;
  for (const o of select.options) {
    const b = document.createElement('button');
    b.type = 'button';
    b.dataset.v = o.value;
    b.textContent = labels[o.value] || o.textContent;
    if (titles[o.value]) b.title = titles[o.value];
    b.onclick = () => {
      if (select.value === o.value || select.disabled) return;
      select.value = o.value;
      select.dispatchEvent(new Event('change', { bubbles: true }));
    };
    box.appendChild(b);
  }
  const sync = () => {
    for (const b of box.children) {
      const on = b.dataset.v === select.value;
      b.classList.toggle('on', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    }
  };
  select.addEventListener('change', sync);
  select.addEventListener('seg-sync', sync);
  sync();
  return box;
}
