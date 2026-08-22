/**
 * Settings Page (.env Editor)
 * All button handlers use addEventListener (no inline onclick) for CSP compatibility.
 */
const SettingsPage = {
  currentEnv: {},

  render() {
    return `
      <div class="settings-grid">
        <!-- Section 1: Server Connection -->
        <div class="card-section">
          <div class="card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-purple)" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="2" y1="12" x2="22" y2="12"/>
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
            <span>Laravel Server Connection</span>
          </div>

          <div class="form-group">
            <label class="form-label">Laravel API URL</label>
            <input type="text" class="form-input" id="setting-laravel-url" placeholder="https://your-domain.com/api">
          </div>

          <div class="form-group">
            <label class="form-label">API Token (Optional)</label>
            <div class="input-wrapper">
              <input type="password" class="form-input" id="setting-laravel-token" placeholder="Bearer Token">
              <button class="input-btn" id="btn-toggle-laravel-token">👁</button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">SaaS Device Key</label>
            <input type="text" class="form-input" id="setting-device-key" placeholder="dev_key_...">
          </div>

          <button class="btn btn-ghost" style="width: 100%; justify-content: center;" id="btn-test-connection">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <span>Test Laravel Connection</span>
          </button>
        </div>

        <!-- Section 2: Engine Config -->
        <div class="card-section">
          <div class="card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-amber)" stroke-width="2">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
              <line x1="6" y1="6" x2="6.01" y2="6"/>
              <line x1="6" y1="18" x2="6.01" y2="18"/>
            </svg>
            <span>Engine & Hardware Settings</span>
          </div>

          <div class="form-group">
            <label class="form-label">Local Port</label>
            <input type="number" class="form-input" id="setting-port" value="8000">
          </div>

          <div class="toggle-wrapper">
            <div>
              <div style="font-weight: 600; font-size: 13px;">Debug Mode</div>
              <div style="font-size: 11px; color: var(--text-muted);">Enable detailed verbose logging</div>
            </div>
            <label class="switch">
              <input type="checkbox" id="setting-debug">
              <span class="slider"></span>
            </label>
          </div>

          <div class="toggle-wrapper">
            <div>
              <div style="font-weight: 600; font-size: 13px;">Auto-Start on Boot</div>
              <div style="font-size: 11px; color: var(--text-muted);">Launch silently when PC turns on</div>
            </div>
            <label class="switch">
              <input type="checkbox" id="setting-autostart">
              <span class="slider"></span>
            </label>
          </div>
        </div>
      </div>

      <!-- Action Bar -->
      <div style="display: flex; justify-content: flex-end; gap: 14px; margin-top: 10px;">
        <button class="btn btn-ghost" id="btn-reset-defaults">
          <span>Reset Defaults</span>
        </button>
        <button class="btn btn-primary" id="btn-save-settings">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          <span>Save & Apply Settings</span>
        </button>
      </div>
    `;
  },

  async init() {
    // Wire up ALL button handlers via addEventListener (CSP-safe)
    const bind = (id, handler) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('click', handler);
    };

    bind('btn-toggle-laravel-token', () => this.togglePassword('setting-laravel-token'));
    bind('btn-test-connection', () => this.testConnection());
    bind('btn-reset-defaults', () => this.resetDefaults());
    bind('btn-save-settings', () => this.saveSettings());

    await this.loadEnv();
  },

  destroy() {},

  togglePassword(id) {
    const input = document.getElementById(id);
    if (input) {
      input.type = input.type === 'password' ? 'text' : 'password';
    }
  },

  async loadEnv() {
    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        this.currentEnv = (await window.__TAURI__.core.invoke('read_env')) || {};
      } else {
        // Fallback for browser preview
        this.currentEnv = this.currentEnv && Object.keys(this.currentEnv).length > 0 ? this.currentEnv : {
          LARAVEL_API_URL: 'http://youtube.test/api',
          LARAVEL_API_TOKEN: '',
          SAAS_DEVICE_KEY: '',
          PORT: '8008',
          DEBUG: 'True'
        };
      }

      console.log('[SettingsPage] Loaded env:', this.currentEnv);

      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val || '';
      };

      setVal('setting-laravel-url', this.currentEnv.LARAVEL_API_URL);
      setVal('setting-laravel-token', this.currentEnv.LARAVEL_API_TOKEN);
      setVal('setting-device-key', this.currentEnv.SAAS_DEVICE_KEY);
      setVal('setting-port', this.currentEnv.PORT || '8008');

      const debugEl = document.getElementById('setting-debug');
      if (debugEl) {
        debugEl.checked = (this.currentEnv.DEBUG || '').toLowerCase() === 'true';
      }
    } catch (e) {
      console.error('[SettingsPage] Failed to load .env:', e);
      Toast.error(`Failed to load .env settings: ${e}`);
    }
  },

  async saveSettings() {
    const btn = document.getElementById('btn-save-settings');
    const originalBtnHTML = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <svg class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>Saving...</span>
      `;
    }

    try {
      const laravelUrl = document.getElementById('setting-laravel-url')?.value.trim() || '';
      const laravelToken = document.getElementById('setting-laravel-token')?.value.trim() || '';
      const deviceKey = document.getElementById('setting-device-key')?.value.trim() || '';
      const port = document.getElementById('setting-port')?.value.trim() || '8008';
      const debug = document.getElementById('setting-debug')?.checked ? 'True' : 'False';

      const updated = {
        ...(this.currentEnv || {}),
        LARAVEL_API_URL: laravelUrl,
        LARAVEL_API_TOKEN: laravelToken,
        SAAS_DEVICE_KEY: deviceKey,
        PORT: port,
        DEBUG: debug,
      };

      console.log('[SettingsPage] Saving settings:', updated);

      if (window.__TAURI__ && window.__TAURI__.core) {
        await window.__TAURI__.core.invoke('write_env', { settings: updated });
        App.port = parseInt(updated.PORT, 10) || 8008;
        this.currentEnv = updated;
        Toast.success('Settings saved successfully!');
      } else {
        this.currentEnv = updated;
        Toast.success('Settings saved (Preview Mode)');
      }
    } catch (e) {
      console.error('[SettingsPage] Save failed:', e);
      Toast.error(`Failed to save settings: ${e}`);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalBtnHTML;
      }
    }
  },

  async testConnection() {
    const btn = document.getElementById('btn-test-connection');
    const originalHTML = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <svg class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>Testing...</span>
      `;
    }

    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        const res = await window.__TAURI__.core.invoke('test_connection');
        if (res.success) {
          Toast.success(res.message || 'Connection successful!');
        } else {
          Toast.error(`Connection failed: ${res.error || 'HTTP ' + res.status_code}`);
        }
      } else {
        Toast.success('Laravel API reachability verified (Preview)!');
      }
    } catch (e) {
      Toast.error(`Connection test failed: ${e}`);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
      }
    }
  },

  resetDefaults() {
    document.getElementById('setting-laravel-url').value = 'http://youtube.test/api';
    document.getElementById('setting-port').value = '8000';
    document.getElementById('setting-debug').checked = true;
    Toast.info('Reset form to default values.');
  }
};
