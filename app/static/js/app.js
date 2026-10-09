/**
 * HandWrite Me — Application Controller & UI State Manager
 */
document.addEventListener('DOMContentLoaded', () => {
  const app = new HandWriteApp();
  app.init();
});

class HandWriteApp {
  constructor() {
    this.currentView = 'dashboard';
    this.profiles = [];
    this.documents = [];
    this.activeProfileId = null;
    this.selectedSampleFile = null;
    this.selectedDocFile = null;
    this.activeCharFilter = 'ALL';
    this.confirmCallback = null;
  }

  async init() {
    this.bindNavigation();
    this.bindModals();
    this.bindDropzones();
    this.bindForms();
    this.bindFilters();

    await this.checkApiConnection();
    await this.loadInitialData();
  }

  // Toast Notification Helper
  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // Confirmation Modal Helper
  showConfirm(title, message, okText, onConfirm) {
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    const okBtn = document.getElementById('confirm-ok-btn');
    okBtn.textContent = okText || 'Confirm';
    
    this.confirmCallback = onConfirm;
    document.getElementById('confirm-modal').classList.remove('hidden');
  }

  closeConfirm() {
    document.getElementById('confirm-modal').classList.add('hidden');
    this.confirmCallback = null;
  }

  // API Connection Checker
  async checkApiConnection() {
    const badge = document.getElementById('api-status-badge');
    const text = document.getElementById('api-status-text');
    try {
      await window.api.listProfiles(0, 1);
      badge.className = 'status-indicator online';
      text.textContent = 'API Connected';
    } catch (e) {
      badge.className = 'status-indicator offline';
      text.textContent = 'API Offline';
    }
  }

  // Navigation Logic
  bindNavigation() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        const view = e.currentTarget.dataset.view;
        this.switchView(view);
      });
    });

    document.getElementById('dash-refresh-btn').addEventListener('click', () => {
      this.loadInitialData();
      this.showToast('Dashboard data refreshed', 'success');
    });

    document.getElementById('dash-view-all-docs').addEventListener('click', () => {
      this.switchView('documents');
    });

    // Quick Launch Buttons
    document.getElementById('dash-action-create-profile').addEventListener('click', () => {
      this.openProfileModal();
    });

    document.getElementById('dash-action-upload-sample').addEventListener('click', () => {
      this.switchView('samples');
    });

    document.getElementById('dash-action-upload-doc').addEventListener('click', () => {
      this.switchView('documents');
    });
  }

  switchView(viewName) {
    this.currentView = viewName;
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.classList.toggle('active', tab.dataset.view === viewName);
    });

    document.querySelectorAll('.view-panel').forEach(panel => {
      panel.classList.toggle('active', panel.id === `view-${viewName}`);
    });

    if (viewName === 'dashboard') {
      this.renderDashboard();
    } else if (viewName === 'profiles') {
      this.renderProfilesGrid();
    } else if (viewName === 'samples') {
      this.updateSampleProfileSelect();
      if (this.activeProfileId) {
        this.loadProfileSamples(this.activeProfileId);
      }
    } else if (viewName === 'documents') {
      this.updateDocProfileSelects();
      this.loadDocuments();
    }
  }

  // Initial Data Fetching
  async loadInitialData() {
    try {
      this.profiles = await window.api.listProfiles(0, 100);
      this.documents = await window.api.listDocuments({ limit: 100 });
      this.renderDashboard();
      this.updateSampleProfileSelect();
      this.updateDocProfileSelects();
      if (this.currentView === 'profiles') this.renderProfilesGrid();
      if (this.currentView === 'documents') this.renderDocsTable();
    } catch (e) {
      this.showToast(e.message, 'error');
      this.renderInitialDataError(e.message);
    }
  }

  renderInitialDataError(errorMsg) {
    document.getElementById('stat-profiles-count').textContent = '—';
    document.getElementById('stat-samples-count').textContent = '—';
    document.getElementById('stat-docs-count').textContent = '—';
    document.getElementById('stat-pages-count').textContent = '—';

    const recentList = document.getElementById('dash-recent-docs-list');
    if (recentList) {
      recentList.innerHTML = `<div class="empty-placeholder" style="color: var(--danger-color, #ef4444);">Failed to load recent documents: ${this.escapeHtml(errorMsg)}</div>`;
    }

    const profilesGrid = document.getElementById('profiles-grid');
    if (profilesGrid) {
      profilesGrid.innerHTML = `<div class="empty-placeholder" style="color: var(--danger-color, #ef4444);">Failed to load profiles: ${this.escapeHtml(errorMsg)}</div>`;
    }

    const docsBody = document.getElementById('docs-table-body');
    if (docsBody) {
      docsBody.innerHTML = `<tr><td colspan="6" class="text-center" style="color: var(--danger-color, #ef4444);">Failed to load documents: ${this.escapeHtml(errorMsg)}</td></tr>`;
    }
  }

  // --- DASHBOARD VIEW ---
  async renderDashboard() {
    document.getElementById('stat-profiles-count').textContent = this.profiles.length;
    document.getElementById('stat-docs-count').textContent = this.documents.length;

    let totalPages = 0;
    this.documents.forEach(d => totalPages += (d.page_count || 0));
    document.getElementById('stat-pages-count').textContent = totalPages;

    // Calculate total character samples count across profiles
    let totalSamples = 0;
    try {
      for (const p of this.profiles) {
        const samples = await window.api.listSamples(p.id);
        totalSamples += samples.length;
      }
    } catch (e) {}
    document.getElementById('stat-samples-count').textContent = totalSamples;

    // Render Recent Documents List
    const recentList = document.getElementById('dash-recent-docs-list');
    if (this.documents.length === 0) {
      recentList.innerHTML = '<div class="empty-placeholder">No documents uploaded yet.</div>';
      return;
    }

    const recentDocs = [...this.documents].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5);
    recentList.innerHTML = recentDocs.map(doc => `
      <div class="action-tile" style="margin-bottom: 0.5rem; cursor: default;">
        <div class="tile-icon icon-emerald"><svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></div>
        <div class="tile-info" style="flex:1;">
          <span class="tile-title">${this.escapeHtml(doc.filename)}</span>
          <span class="tile-desc">${doc.page_count} page(s) &bull; ${(doc.file_size / 1024).toFixed(1)} KB</span>
        </div>
        <span class="badge ${doc.status === 'completed' ? 'badge-success' : 'badge-warning'}">${doc.status}</span>
      </div>
    `).join('');
  }

  // --- PROFILES VIEW ---
  renderProfilesGrid() {
    const grid = document.getElementById('profiles-grid');
    if (this.profiles.length === 0) {
      grid.innerHTML = `
        <div class="card glass-card" style="grid-column: 1 / -1; text-align: center; padding: 3rem;">
          <h3 style="margin-bottom: 0.5rem;">No Handwriting Profiles Found</h3>
          <p class="panel-subtitle" style="margin-bottom: 1.5rem;">Create a profile to begin collecting handwriting character samples.</p>
          <button class="btn btn-primary" onclick="document.getElementById('open-create-profile-btn').click()">Create Profile</button>
        </div>
      `;
      return;
    }

    grid.innerHTML = this.profiles.map(p => `
      <div class="profile-card">
        <div>
          <div class="profile-card-header">
            <h3 class="profile-name">${this.escapeHtml(p.profile_name)}</h3>
            <p class="profile-desc">${this.escapeHtml(p.description || 'No description provided.')}</p>
          </div>
          <div class="profile-meta">
            <span>ID: #${p.id}</span>
            <span>Created: ${new Date(p.created_at).toLocaleDateString()}</span>
          </div>
        </div>
        <div class="profile-actions">
          <button class="btn btn-secondary btn-sm" onclick="window.app.openProfileModal(${p.id})">Edit</button>
          <button class="btn btn-primary btn-sm" onclick="window.app.viewProfileSamples(${p.id})">Character Studio</button>
          <button class="btn btn-danger btn-sm" onclick="window.app.confirmDeleteProfile(${p.id})">Delete</button>
        </div>
      </div>
    `).join('');
  }

  openProfileModal(profileId = null) {
    const title = document.getElementById('profile-modal-title');
    const idInput = document.getElementById('profile-form-id');
    const nameInput = document.getElementById('profile-form-name');
    const descInput = document.getElementById('profile-form-desc');

    if (profileId) {
      const p = this.profiles.find(item => item.id === profileId);
      if (p) {
        title.textContent = 'Edit Handwriting Profile';
        idInput.value = p.id;
        nameInput.value = p.profile_name;
        descInput.value = p.description || '';
      }
    } else {
      title.textContent = 'Create Handwriting Profile';
      idInput.value = '';
      nameInput.value = '';
      descInput.value = '';
    }

    document.getElementById('profile-modal').classList.remove('hidden');
  }

  closeProfileModal() {
    document.getElementById('profile-modal').classList.add('hidden');
  }

  async saveProfile(e) {
    e.preventDefault();
    const id = document.getElementById('profile-form-id').value;
    const name = document.getElementById('profile-form-name').value.trim();
    const desc = document.getElementById('profile-form-desc').value.trim();

    if (!name) {
      this.showToast('Profile name is required', 'error');
      return;
    }

    const btn = document.getElementById('profile-form-submit');
    const spinner = btn.querySelector('.spinner');
    btn.disabled = true;
    spinner.classList.remove('hidden');

    try {
      if (id) {
        await window.api.updateProfile(id, { profile_name: name, description: desc });
        this.showToast('Profile updated successfully', 'success');
      } else {
        await window.api.createProfile({ profile_name: name, description: desc });
        this.showToast('Profile created successfully', 'success');
      }
      this.closeProfileModal();
      await this.loadInitialData();
    } catch (err) {
      this.showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      spinner.classList.add('hidden');
    }
  }

  confirmDeleteProfile(profileId) {
    const p = this.profiles.find(item => item.id === profileId);
    const name = p ? p.profile_name : `Profile #${profileId}`;
    this.showConfirm(
      'Delete Profile',
      `Are you sure you want to delete profile "${name}"? All associated character sample files will be deleted from disk.`,
      'Delete Profile',
      async () => {
        try {
          await window.api.deleteProfile(profileId);
          this.showToast(`Profile "${name}" deleted`, 'success');
          await this.loadInitialData();
        } catch (err) {
          this.showToast(err.message, 'error');
        }
      }
    );
  }

  viewProfileSamples(profileId) {
    this.activeProfileId = profileId;
    this.switchView('samples');
  }

  // --- CHARACTER SAMPLE STUDIO ---
  updateSampleProfileSelect() {
    const select = document.getElementById('sample-active-profile-select');
    select.innerHTML = '<option value="">-- Select Profile --</option>' + 
      this.profiles.map(p => `<option value="${p.id}" ${p.id === this.activeProfileId ? 'selected' : ''}>${this.escapeHtml(p.profile_name)} (ID: #${p.id})</option>`).join('');
  }

  async loadProfileSamples(profileId) {
    const gallery = document.getElementById('samples-gallery-grid');
    if (!profileId) {
      gallery.innerHTML = '<div class="empty-placeholder">Select a profile to view character samples.</div>';
      return;
    }

    gallery.innerHTML = '<div class="empty-placeholder">Loading character samples...</div>';
    try {
      const samples = await window.api.listSamples(profileId);
      this.renderSampleGallery(samples);
    } catch (err) {
      this.showToast(err.message, 'error');
      gallery.innerHTML = '<div class="empty-placeholder">Failed to load samples.</div>';
    }
  }

  renderSampleGallery(samples) {
    const gallery = document.getElementById('samples-gallery-grid');
    const tagsContainer = document.getElementById('sample-filter-tags');

    if (samples.length === 0) {
      gallery.innerHTML = '<div class="empty-placeholder" style="grid-column: 1 / -1;">No character samples uploaded for this profile yet.</div>';
      tagsContainer.innerHTML = '<button class="filter-tag active" data-char="ALL">ALL</button>';
      return;
    }

    // Populate Filter Tags
    const uniqueChars = Array.from(new Set(samples.map(s => s.character))).sort();
    tagsContainer.innerHTML = '<button class="filter-tag ' + (this.activeCharFilter === 'ALL' ? 'active' : '') + '" data-char="ALL">ALL</button>' +
      uniqueChars.map(c => `<button class="filter-tag ${this.activeCharFilter === c ? 'active' : ''}" data-char="${this.escapeHtml(c)}">${this.escapeHtml(c)}</button>`).join('');

    // Filter samples
    const filtered = this.activeCharFilter === 'ALL' 
      ? samples 
      : samples.filter(s => s.character === this.activeCharFilter);

    gallery.innerHTML = filtered.map(s => {
      const imgUrl = this.resolveMediaUrl(s.image_url || s.file_path);
      return `
        <div class="sample-thumb-card">
          <button class="sample-delete-btn" title="Delete Sample" onclick="window.app.confirmDeleteSample(${s.profile_id}, ${s.id})">&times;</button>
          <div class="sample-img-box">
            <img src="${imgUrl}" alt="${this.escapeHtml(s.character)}" class="sample-img" onerror="this.onerror=null; this.src='data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'50\' height=\'50\'><text x=\'50%\' y=\'50%\' dominant-baseline=\'middle\' text-anchor=\'middle\' fill=\'%2364748b\'>IMG</text></svg>';">
          </div>
          <span class="sample-char-badge">${this.escapeHtml(s.character)}</span>
        </div>
      `;
    }).join('');

    // Re-bind tag clicks
    tagsContainer.querySelectorAll('.filter-tag').forEach(tag => {
      tag.addEventListener('click', (e) => {
        this.activeCharFilter = e.currentTarget.dataset.char;
        this.renderSampleGallery(samples);
      });
    });
  }

  async handleSampleUpload(e) {
    e.preventDefault();
    if (!this.activeProfileId) {
      this.showToast('Please select an active profile first', 'error');
      return;
    }

    const charInput = document.getElementById('sample-char-input').value.trim();
    if (!charInput) {
      this.showToast('Character label is required', 'error');
      return;
    }

    if (!this.selectedSampleFile) {
      this.showToast('Please select a sample image file', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('character', charInput);
    formData.append('sample_type', document.getElementById('sample-type-input').value);
    formData.append('file', this.selectedSampleFile);

    const btn = document.getElementById('sample-upload-submit');
    const spinner = btn.querySelector('.spinner');
    btn.disabled = true;
    spinner.classList.remove('hidden');

    try {
      await window.api.uploadSample(this.activeProfileId, formData);
      this.showToast(`Sample for '${charInput}' uploaded successfully`, 'success');
      
      // Reset form
      document.getElementById('sample-char-input').value = '';
      this.clearSampleFile();
      await this.loadProfileSamples(this.activeProfileId);
    } catch (err) {
      this.showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      spinner.classList.add('hidden');
    }
  }

  confirmDeleteSample(profileId, sampleId) {
    this.showConfirm(
      'Delete Sample',
      'Are you sure you want to delete this character sample image?',
      'Delete Sample',
      async () => {
        try {
          await window.api.deleteSample(profileId, sampleId);
          this.showToast('Character sample deleted', 'success');
          await this.loadProfileSamples(profileId);
        } catch (err) {
          this.showToast(err.message, 'error');
        }
      }
    );
  }

  // --- PDF DOCUMENTS VIEW ---
  updateDocProfileSelects() {
    const assocSelect = document.getElementById('doc-assoc-profile-select');
    const filterSelect = document.getElementById('doc-filter-profile');

    const opts = this.profiles.map(p => `<option value="${p.id}">${this.escapeHtml(p.profile_name)} (ID: #${p.id})</option>`).join('');
    assocSelect.innerHTML = '<option value="">-- None (Standalone Document) --</option>' + opts;
    filterSelect.innerHTML = '<option value="">All Profiles</option>' + opts;
  }

  async loadDocuments() {
    const profileFilter = document.getElementById('doc-filter-profile').value;
    const statusFilter = document.getElementById('doc-filter-status').value;

    const params = { limit: 100 };
    if (profileFilter) params.profile_id = profileFilter;
    if (statusFilter) params.status = statusFilter;

    try {
      this.documents = await window.api.listDocuments(params);
      this.renderDocsTable();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  }

  renderDocsTable() {
    const tbody = document.getElementById('docs-table-body');
    if (this.documents.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center">No PDF documents match the selected filter.</td></tr>';
      return;
    }

    tbody.innerHTML = this.documents.map(d => {
      const statusBadge = d.status === 'completed'
        ? '<span class="badge badge-success">Completed</span>'
        : '<span class="badge badge-warning">No Text</span>';
      
      const profileName = d.profile_id 
        ? (this.profiles.find(p => p.id === d.profile_id)?.profile_name || `#${d.profile_id}`)
        : '<span style="color:var(--text-dim)">Standalone</span>';

      return `
        <tr>
          <td>#${d.id}</td>
          <td><strong>${this.escapeHtml(d.filename)}</strong></td>
          <td>${(d.file_size / 1024).toFixed(1)} KB</td>
          <td>${d.page_count}</td>
          <td>${statusBadge}</td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick="window.app.viewDocumentText(${d.id})">View Text</button>
            <button class="btn btn-danger btn-sm" onclick="window.app.confirmDeleteDoc(${d.id})">Delete</button>
          </td>
        </tr>
      `;
    }).join('');
  }

  async handleDocUpload(e) {
    e.preventDefault();
    if (!this.selectedDocFile) {
      this.showToast('Please select a PDF document file', 'error');
      return;
    }

    const formData = new FormData();
    formData.append('file', this.selectedDocFile);
    const assocProfile = document.getElementById('doc-assoc-profile-select').value;
    if (assocProfile) {
      formData.append('profile_id', assocProfile);
    }

    const btn = document.getElementById('doc-upload-submit');
    const spinner = btn.querySelector('.spinner');
    btn.disabled = true;
    spinner.classList.remove('hidden');

    try {
      const doc = await window.api.uploadDocument(formData);
      this.showToast(`PDF "${doc.filename}" uploaded successfully (${doc.page_count} page(s))`, 'success');
      this.clearDocFile();
      await this.loadInitialData();
    } catch (err) {
      this.showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      spinner.classList.add('hidden');
    }
  }

  async viewDocumentText(docId) {
    try {
      const detail = await window.api.getDocument(docId);
      document.getElementById('doc-modal-title').textContent = detail.filename;
      document.getElementById('doc-meta-status').textContent = `Status: ${detail.status}`;
      document.getElementById('doc-meta-pages').textContent = `${detail.page_count} Page(s)`;
      document.getElementById('doc-meta-size').textContent = `${(detail.file_size / 1024).toFixed(1)} KB`;
      
      const contentBox = document.getElementById('doc-text-content');
      contentBox.textContent = detail.extracted_text || '(No text content extracted from this document.)';
      
      document.getElementById('document-text-modal').classList.remove('hidden');
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  }

  confirmDeleteDoc(docId) {
    const doc = this.documents.find(d => d.id === docId);
    const name = doc ? doc.filename : `Document #${docId}`;
    this.showConfirm(
      'Delete Document',
      `Are you sure you want to delete "${name}"? The stored file will be removed from disk.`,
      'Delete Document',
      async () => {
        try {
          await window.api.deleteDocument(docId);
          this.showToast(`Document "${name}" deleted`, 'success');
          await this.loadInitialData();
        } catch (err) {
          this.showToast(err.message, 'error');
        }
      }
    );
  }

  // Dropzones & File Selectors Binding
  bindDropzones() {
    // Sample Dropzone
    const sampleDz = document.getElementById('sample-dropzone');
    const sampleInput = document.getElementById('sample-file-input');

    sampleDz.addEventListener('click', () => sampleInput.click());
    sampleDz.addEventListener('dragover', (e) => { e.preventDefault(); sampleDz.classList.add('dragover'); });
    sampleDz.addEventListener('dragleave', () => sampleDz.classList.remove('dragover'));
    sampleDz.addEventListener('drop', (e) => {
      e.preventDefault();
      sampleDz.classList.remove('dragover');
      if (e.dataTransfer.files.length) this.setSampleFile(e.dataTransfer.files[0]);
    });
    sampleInput.addEventListener('change', (e) => {
      if (e.target.files.length) this.setSampleFile(e.target.files[0]);
    });
    document.getElementById('sample-remove-file-btn').addEventListener('click', () => this.clearSampleFile());

    // Document Dropzone
    const docDz = document.getElementById('doc-dropzone');
    const docInput = document.getElementById('doc-file-input');

    docDz.addEventListener('click', () => docInput.click());
    docDz.addEventListener('dragover', (e) => { e.preventDefault(); docDz.classList.add('dragover'); });
    docDz.addEventListener('dragleave', () => docDz.classList.remove('dragover'));
    docDz.addEventListener('drop', (e) => {
      e.preventDefault();
      docDz.classList.remove('dragover');
      if (e.dataTransfer.files.length) this.setDocFile(e.dataTransfer.files[0]);
    });
    docInput.addEventListener('change', (e) => {
      if (e.target.files.length) this.setDocFile(e.target.files[0]);
    });
    document.getElementById('doc-remove-file-btn').addEventListener('click', () => this.clearDocFile());
  }

  setSampleFile(file) {
    if (!file.type.startsWith('image/')) {
      this.showToast('Only image files (PNG, JPEG, WEBP, GIF) are allowed', 'error');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      this.showToast('File size exceeds maximum allowed limit of 5MB', 'error');
      return;
    }

    this.selectedSampleFile = file;
    document.getElementById('sample-file-name').textContent = file.name;
    document.getElementById('sample-file-size').textContent = `${(file.size / 1024).toFixed(1)} KB`;
    
    const reader = new FileReader();
    reader.onload = (e) => {
      document.getElementById('sample-preview-img').src = e.target.result;
      document.getElementById('sample-dropzone').classList.add('hidden');
      document.getElementById('sample-file-preview').classList.remove('hidden');
      document.getElementById('sample-upload-submit').disabled = false;
    };
    reader.readAsDataURL(file);
  }

  clearSampleFile() {
    this.selectedSampleFile = null;
    document.getElementById('sample-file-input').value = '';
    document.getElementById('sample-dropzone').classList.remove('hidden');
    document.getElementById('sample-file-preview').classList.add('hidden');
    document.getElementById('sample-upload-submit').disabled = true;
  }

  setDocFile(file) {
    if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
      this.showToast('Only PDF documents (.pdf) are allowed', 'error');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      this.showToast('File size exceeds maximum allowed limit of 10MB', 'error');
      return;
    }

    this.selectedDocFile = file;
    document.getElementById('doc-file-name').textContent = file.name;
    document.getElementById('doc-file-size').textContent = `${(file.size / 1024).toFixed(1)} KB`;
    
    document.getElementById('doc-dropzone').classList.add('hidden');
    document.getElementById('doc-file-preview').classList.remove('hidden');
    document.getElementById('doc-upload-submit').disabled = false;
  }

  clearDocFile() {
    this.selectedDocFile = null;
    document.getElementById('doc-file-input').value = '';
    document.getElementById('doc-dropzone').classList.remove('hidden');
    document.getElementById('doc-file-preview').classList.add('hidden');
    document.getElementById('doc-upload-submit').disabled = true;
  }

  bindForms() {
    document.getElementById('open-create-profile-btn').addEventListener('click', () => this.openProfileModal());
    document.getElementById('profile-modal-close').addEventListener('click', () => this.closeProfileModal());
    document.getElementById('profile-modal-cancel').addEventListener('click', () => this.closeProfileModal());
    document.getElementById('profile-form').addEventListener('submit', (e) => this.saveProfile(e));

    document.getElementById('sample-upload-form').addEventListener('submit', (e) => this.handleSampleUpload(e));
    document.getElementById('doc-upload-form').addEventListener('submit', (e) => this.handleDocUpload(e));
  }

  bindModals() {
    document.getElementById('confirm-cancel-btn').addEventListener('click', () => this.closeConfirm());
    document.getElementById('confirm-ok-btn').addEventListener('click', () => {
      if (this.confirmCallback) this.confirmCallback();
      this.closeConfirm();
    });

    document.getElementById('doc-modal-close').addEventListener('click', () => {
      document.getElementById('document-text-modal').classList.add('hidden');
    });
    document.getElementById('doc-modal-close-btn').addEventListener('click', () => {
      document.getElementById('document-text-modal').classList.add('hidden');
    });

    document.getElementById('copy-text-btn').addEventListener('click', () => {
      const txt = document.getElementById('doc-text-content').textContent;
      navigator.clipboard.writeText(txt);
      this.showToast('Extracted text copied to clipboard', 'success');
    });
  }

  bindFilters() {
    document.getElementById('sample-active-profile-select').addEventListener('change', (e) => {
      this.activeProfileId = e.target.value ? parseInt(e.target.value, 10) : null;
      this.activeCharFilter = 'ALL';
      this.loadProfileSamples(this.activeProfileId);
    });

    document.getElementById('doc-filter-profile').addEventListener('change', () => this.loadDocuments());
    document.getElementById('doc-filter-status').addEventListener('change', () => this.loadDocuments());
  }

  // Media URL Helper
  resolveMediaUrl(path) {
    if (!path) return '';
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    if (path.startsWith('/')) return `${window.api.baseUrl.replace(/\/api\/v1$/, '')}${path}`;
    return `${window.api.baseUrl.replace(/\/api\/v1$/, '')}/${path}`;
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&to;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

window.app = new HandWriteApp();
