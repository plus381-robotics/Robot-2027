// Zajedničke stavke reda komandi (core/toolitems.js): „Taktika“ (#tactic) i „Strana“ Žuta | Plava (nad skrivenim
// #side, koji ostaje izvor istine za app.js). Jedan čvor po stavci; okvir ga premešta u red komandi prostora:
// Taktike -> taktike-alati, Vožnja/Snimci -> za sada stari red (stari-alati), od Zadatka 4.4 voznja-alati.
import { registerToolItem } from '../core/toolitems.js';
import { segmented } from '../shell/segmented.js';

registerToolItem({
  id: 'taktika', title: 'Taktika',
  mount: el => {
    const lab = document.createElement('label');
    lab.className = 'ti-label';
    lab.append('Taktika ', document.getElementById('tactic'));
    el.appendChild(lab);
  },
});

registerToolItem({
  id: 'strana', title: 'Strana',
  mount: el => {
    const side = document.getElementById('side');
    side.hidden = true;
    const lab = document.createElement('span');
    lab.className = 'ti-label';
    lab.textContent = 'Strana';
    el.append(lab, segmented(side, { id: 'sideSeg', cls: 'seg-side', title: 'Strana stola sa koje robot kreće',
      labels: { zuta: 'Žuta', plava: 'Plava' } }), side);
  },
});
