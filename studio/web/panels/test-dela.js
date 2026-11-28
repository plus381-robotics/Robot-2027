// Test dela (Zadatak 5.2): podkartice Lidar · Pogon · Mehanizmi · IR na početku reda komandi. Radi samo Lidar
// (panels/lidar.js: red komandi, sto + radar, kartica Lidar); ostale su sive dok ne stigne Faza 6 (ESP).
import { registerPanel } from '../core/panels.js';

export const TEST_TABS = [
  { id: 'lidar', label: 'Lidar', title: 'Lidar: sirovo → u stolu / van stola → grupe (računa laptop)' },
  { id: 'pogon', label: 'Pogon', off: 'dolazi sa Fazom 6 (ESP)' },
  { id: 'mehanizmi', label: 'Mehanizmi', off: 'dolazi sa Fazom 6 (ESP)' },
  { id: 'ir', label: 'IR', off: 'dolazi sa Fazom 6 (ESP)' },
];

registerPanel({
  id: 'test-dela', title: 'Test dela', workspaces: ['test'], region: 'tool', priority: 1, open: true,
  mount: el => {
    el.className += ' tool-row';
    el.innerHTML = `<span class="seg td-tabs" id="tdTabs" role="tablist" title="Deo robota koji se testira">${TEST_TABS.map(t =>
      `<button type="button" role="tab" data-v="${t.id}"${t.off ? ' disabled' : ' class="on" aria-selected="true"'} title="${t.off ? `${t.label}: ${t.off}` : t.title}">${t.label}</button>`).join('')}</span>`;
  },
});
