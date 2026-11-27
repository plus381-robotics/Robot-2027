// Test dela: mesto dok ne stigne Faza 5.
import { registerPanel } from '../core/panels.js';

registerPanel({
  id: 'test-dela', title: 'Test dela', workspaces: ['test'], region: 'main', priority: 1, open: true,
  mount: el => { el.innerHTML = '<div class="ws-empty"><h2>Test dela</h2><p>Test dela dolazi u Fazi 5</p></div>'; },
});
