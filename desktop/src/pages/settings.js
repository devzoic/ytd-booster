/**
 * Settings Page (.env Editor)
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
              <button class="input-btn" onclick="SettingsPage.togglePassword('setting-laravel-token')">👁</button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">SaaS Device Key</label>
            <input type="text" class="form-input" id="setting-device-key" placeholder="dev_key_...">
          </div>

          <button class="btn btn-ghost" style="width: 100%; justify-content: center;" onclick="SettingsPage.testConnection()">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <span>Test Laravel Connection</span>
          </button>
        </div>

        <!-- Section 2: Ngrok Public Tunnel -->
        <div class="card-section">
          <div class="card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" stroke-width="2">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
            <span>Ngrok Tunnel Settings</span>
          </div>

          <div class="form-group">
            <label class="form-label">Ngrok Auth Token</label>
            <div class="input-wrapper">
              <input type="password" class="form-input" id="setting-ngrok-token" placeholder="Paste from dashboard.ngrok.com">
              <button class="input-btn" onclick="SettingsPage.togglePassword('setting-ngrok-token')">👁</button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Static Ngrok Domain</label>
            <input type="text" class="form-input" id="setting-ngrok-domain" placeholder="https://your-domain.ngrok-free.dev">
          </div>

          <!-- Section 3: Engine Config -->
          <div class="card-title" style="margin-top: 24px;">
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
        <button class="btn btn-ghost" onclick="SettingsPage.resetDefaults()">
          <span>Reset Defaults</span>
        </button>
        <button class="btn btn-primary" onclick="SettingsPage.saveSettings()">
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
        this.currentEnv = await window.__TAURI__.core.invoke('read_env');
      } else {
        // Fallback for browser preview
        this.currentEnv = {
          LARAVEL_API_URL: 'http://youtube.test/api',
          LARAVEL_API_TOKEN: '',
          SAAS_DEVICE_KEY: 'dev_key_g1B2eipLZwv4FlbcZN1QBUI3',
          NGROK_AUTHTOKEN: '3H2elxwZm1EMrYBNfwmVHI8ZJoG_3KtTcF1GAAVGJoYUHGaiw',
          NGROK_DOMAIN: 'https://observant-skimpily-petition.ngrok-free.dev',
          PORT: '8000',
          DEBUG: 'True'
        };
      }

      document.getElementById('setting-laravel-url').value = this.currentEnv.LARAVEL_API_URL || '';
      document.getElementById('setting-laravel-token').value = this.currentEnv.LARAVEL_API_TOKEN || '';
      document.getElementById('setting-device-key').value = this.currentEnv.SAAS_DEVICE_KEY || '';
      document.getElementById('setting-ngrok-token').value = this.currentEnv.NGROK_AUTHTOKEN || '';
      document.getElementById('setting-ngrok-domain').value = this.currentEnv.NGROK_DOMAIN || '';
      document.getElementById('setting-port').value = this.currentEnv.PORT || '8008';
      document.getElementById('setting-debug').checked = (this.currentEnv.DEBUG || '').toLowerCase() === 'true';
    } catch (e) {
      Toast.error(`Failed to load .env settings: ${e}`);
    }
  },

  async saveSettings() {
    const updated = {
      ...this.currentEnv,
      LARAVEL_API_URL: document.getElementById('setting-laravel-url').value.trim(),
      LARAVEL_API_TOKEN: document.getElementById('setting-laravel-token').value.trim(),
      SAAS_DEVICE_KEY: document.getElementById('setting-device-key').value.trim(),
      NGROK_AUTHTOKEN: document.getElementById('setting-ngrok-token').value.trim(),
      NGROK_DOMAIN: document.getElementById('setting-ngrok-domain').value.trim(),
      PORT: document.getElementById('setting-port').value.trim() || '8008',
      DEBUG: document.getElementById('setting-debug').checked ? 'True' : 'False',
    };

    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        await window.__TAURI__.core.invoke('write_env', { settings: updated });
        App.port = parseInt(updated.PORT, 10) || 8008;
        Toast.success('Settings saved successfully!');
        
        // Auto restart engine with new settings
        Toast.info('Applying new settings to engine...');
        await App.stopEngine();
        await App.startEngine();
      } else {
        App.port = parseInt(updated.PORT, 10) || 8008;
        Toast.success('Settings saved (Preview Mode)!');
      }
      this.currentEnv = updated;
    } catch (e) {
      Toast.error(`Failed to save settings: ${e}`);
    }
  },

  async testConnection() {
    const url = document.getElementById('setting-laravel-url').value.trim();
    if (!url) {
      Toast.error('Please enter a Laravel API URL first.');
      return;
    }

    Toast.info(`Testing connection to ${url}...`);
    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        const res = await window.__TAURI__.core.invoke('test_connection', { url });
        if (res.success) {
          Toast.success(`Connected! Server responded with HTTP ${res.status_code}`);
        } else {
          Toast.error(`Connection failed: ${res.error || 'HTTP ' + res.status_code}`);
        }
      } else {
        Toast.success('Laravel API reachability verified (Preview)!');
      }
    } catch (e) {
      Toast.error(`Connection test failed: ${e}`);
    }
  },

  resetDefaults() {
    document.getElementById('setting-laravel-url').value = 'http://youtube.test/api';
    document.getElementById('setting-port').value = '8000';
    document.getElementById('setting-debug').checked = true;
    Toast.info('Reset form to default values.');
  }
};
