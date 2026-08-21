/**
 * Dashboard Page
 */
const DashboardPage = {
  statsInterval: null,

  render() {
    return `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-card-header">
            <span class="stat-label">CPU Usage</span>
            <svg class="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="4" y="4" width="16" height="16" rx="2"/>
              <rect x="9" y="9" width="6" height="6"/>
              <line x1="9" y1="1" x2="9" y2="4"/>
              <line x1="15" y1="1" x2="15" y2="4"/>
            </svg>
          </div>
          <div class="stat-value" id="stat-cpu">0%</div>
          <div class="stat-bar-container">
            <div class="stat-bar-fill" id="stat-cpu-bar" style="width: 0%"></div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-card-header">
            <span class="stat-label">RAM Usage</span>
            <svg class="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M6 19v-3"/>
              <path d="M10 19v-3"/>
              <path d="M14 19v-3"/>
              <path d="M18 19v-3"/>
              <path d="M6 5v3"/>
              <path d="M10 5v3"/>
              <path d="M14 5v3"/>
              <path d="M18 5v3"/>
              <rect x="2" y="8" width="20" height="8" rx="2"/>
            </svg>
          </div>
          <div class="stat-value" id="stat-ram">0 GB</div>
          <div class="stat-bar-container">
            <div class="stat-bar-fill" id="stat-ram-bar" style="width: 0%"></div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-card-header">
            <span class="stat-label">Active Profiles</span>
            <svg class="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
            </svg>
          </div>
          <div class="stat-value" id="stat-profiles">0</div>
          <div class="stat-bar-container">
            <div class="stat-bar-fill" id="stat-profiles-bar" style="width: 25%"></div>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-card-header">
            <span class="stat-label">Active Jobs</span>
            <svg class="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
          </div>
          <div class="stat-value" id="stat-jobs">0</div>
          <div class="stat-bar-container">
            <div class="stat-bar-fill" id="stat-jobs-bar" style="width: 0%"></div>
          </div>
        </div>
      </div>

      <!-- Active Campaigns Table -->
      <div class="card-section">
        <div class="card-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-purple)" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          <span>Active Campaign Jobs</span>
        </div>
        <div class="table-wrapper">
          <table class="custom-table">
            <thead>
              <tr>
                <th>Profile</th>
                <th>Campaign</th>
                <th>Target Video</th>
                <th>Mode</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody id="campaigns-table-body">
              <tr>
                <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">
                  Waiting for active campaign polling...
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Quick Live Console -->
      <div class="terminal-container">
        <div class="terminal-header">
          <div class="terminal-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="4 17 10 11 4 5"/>
              <line x1="12" y1="19" x2="20" y2="19"/>
            </svg>
            <span>Live Output</span>
          </div>
          <button class="btn btn-ghost" style="padding: 4px 10px; font-size: 11px;" onclick="App.navigate('logs')">
            Expand Terminal
          </button>
        </div>
        <div class="terminal-body" id="dashboard-terminal">
          <div class="log-line">
            <span class="log-time">[System]</span>
            <span class="log-level-info">INFO</span>
            <span class="log-msg">YT Booster Desktop Interface Initialized.</span>
          </div>
        </div>
      </div>
    `;
  },

  async init() {
    this.fetchStats();
    this.statsInterval = setInterval(() => this.fetchStats(), 3000);
  },

  destroy() {
    if (this.statsInterval) {
      clearInterval(this.statsInterval);
      this.statsInterval = null;
    }
  },

  async fetchStats() {
    try {
      const res = await fetch(App.apiUrl('/dashboard/api/stats'));
      if (res.ok) {
        if (!App.isEngineRunning) {
          App.updateEngineUI(true);
        }
        this.failCount = 0;

        const json = await res.json();
        const stats = json.data || {};
        
        // CPU
        const cpu = (stats.cpu && stats.cpu.percent !== undefined) ? stats.cpu.percent : (stats.cpu_percent || 0);
        const cpuEl = document.getElementById('stat-cpu');
        const cpuBarEl = document.getElementById('stat-cpu-bar');
        if (cpuEl) cpuEl.innerText = `${Number(cpu).toFixed(1)}%`;
        if (cpuBarEl) cpuBarEl.style.width = `${Math.min(Math.max(cpu, 0), 100)}%`;

        // RAM
        const memUsed = stats.memory?.used_gb ?? ((stats.memory_used || 0) / (1024 ** 3)).toFixed(1);
        const memTotal = stats.memory?.total_gb ?? ((stats.memory_total || 0) / (1024 ** 3)).toFixed(1);
        const memPercent = stats.memory?.percent ?? stats.memory_percent ?? 0;
        
        const ramEl = document.getElementById('stat-ram');
        const ramBarEl = document.getElementById('stat-ram-bar');
        if (ramEl) ramEl.innerText = `${memUsed} / ${memTotal} GB`;
        if (ramBarEl) ramBarEl.style.width = `${Math.min(Math.max(memPercent, 0), 100)}%`;
      } else {
        this.failCount = (this.failCount || 0) + 1;
        if (this.failCount > 2 && App.isEngineRunning) {
          App.updateEngineUI(false);
        }
      }
    } catch (e) {
      this.failCount = (this.failCount || 0) + 1;
      if (this.failCount > 2 && App.isEngineRunning) {
        App.updateEngineUI(false);
      }
    }

    // Profiles & Chrome processes count
    try {
      const profRes = await fetch(App.apiUrl('/dashboard/api/profiles'));
      if (profRes.ok) {
        const profData = await profRes.json();
        const processes = profData.data?.processes || [];
        const profEl = document.getElementById('stat-profiles');
        const profBarEl = document.getElementById('stat-profiles-bar');
        if (profEl) profEl.innerText = `${processes.length}`;
        if (profBarEl) profBarEl.style.width = `${Math.min(processes.length * 15, 100)}%`;
      }
    } catch (e) {}

    // Active campaigns
    try {
      const campRes = await fetch(App.apiUrl('/dashboard/api/campaigns'));
      if (campRes.ok) {
        const campData = await campRes.json();
        const campaignsData = campData.data?.campaigns || {};
        const campaigns = Array.isArray(campaignsData) ? campaignsData : Object.values(campaignsData);

        const jobsEl = document.getElementById('stat-jobs');
        const jobsBarEl = document.getElementById('stat-jobs-bar');
        if (jobsEl) jobsEl.innerText = `${campaigns.length}`;
        if (jobsBarEl) jobsBarEl.style.width = `${Math.min(campaigns.length * 20, 100)}%`;

        const tbody = document.getElementById('campaigns-table-body');
        if (tbody) {
          if (campaigns.length === 0) {
            tbody.innerHTML = `
              <tr>
                <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 20px;">
                  No active jobs currently running. Node is polling Laravel queue.
                </td>
              </tr>
            `;
          } else {
            tbody.innerHTML = campaigns.map(c => `
              <tr>
                <td style="font-weight: 600;">${c.profile_name || 'Profile'}</td>
                <td>${c.title || c.campaign_title || 'Campaign #' + (c.id || c.campaign_id || '')}</td>
                <td style="color: var(--text-secondary); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                  ${c.video_title || c.video_url || c.url || '—'}
                </td>
                <td><span class="badge badge-info">${c.mode || 'SEARCH'}</span></td>
                <td><span class="badge badge-success">${c.status || 'Active'}</span></td>
              </tr>
            `).join('');
          }
        }
      }
    } catch (e) {}
  }
};
