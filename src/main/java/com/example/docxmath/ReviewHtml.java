package com.example.docxmath;

final class ReviewHtml {
    private ReviewHtml() {
    }

    private static String escapeHtml(String value) {
        return HtmlUtil.escape(value);
    }

    private static String escapeJsString(String value) {
        if (value == null || value.isEmpty()) {
            return "";
        }
        return value.replace("\\", "\\\\").replace("'", "\\'");
    }

    static String operatorDashboardPage() {
        return shell("Bang dieu khien van hanh", """
                <div class="hero">
                  <div>
                    <h1>Bang dieu khien van hanh</h1>
                    <p class="muted">Man hinh van hanh toi gian cho upload de, xem trang thai import, va kich hoat xuat DOCX. Toan bo luong xu ly ben duoi duoc giu nguyen.</p>
                  </div>
                  <div class="hero-actions">
                    <a class="btn btn-secondary" href="/review/bundles">Danh sach de review</a>
                    <button class="btn btn-secondary" id="refreshBtn" type="button">Tai lai</button>
                  </div>
                </div>

                <div class="panel stack">
                  <div class="summary-grid" id="operatorSummary"></div>
                  <div class="controls">
                    <label>File DOCX nguon
                      <input id="sourceFile" type="file" accept=".docx" />
                    </label>
                    <label>Nhan upload
                      <input id="uploadLabel" placeholder="Nhan tuy chon" />
                    </label>
                    <div class="batch-actions">
                      <button class="btn btn-primary" id="uploadBtn" type="button">Upload va xu ly</button>
                      <span id="uploadStatus" class="muted small">Dang cho</span>
                    </div>
                  </div>
                </div>

                <div class="panel stack">
                  <h2>Job van hanh</h2>
                  <div id="jobsStatus" class="statusline muted">Dang tai job...</div>
                  <div id="jobsTable">Dang tai...</div>
                </div>

                <div class="panel stack">
                  <h2>Bundle san sang import</h2>
                  <div id="bundleStatus" class="statusline muted">Dang tai bundle...</div>
                  <div id="bundleTable">Dang tai...</div>
                </div>

                <div class="panel stack">
                  <h2>Xuat DOCX tu assembly</h2>
                  <p class="muted small">Xuat tu assembly record da luu bang <code>assembly_id</code>.</p>
                  <div class="controls">
                    <label>Assembly ID
                      <input id="assemblyId" placeholder="assembly_..." />
                    </label>
                    <label>Che do
                      <select id="assemblyMode">
                        <option value="student">hoc sinh</option>
                        <option value="teacher" selected>giao vien</option>
                      </select>
                    </label>
                    <label>Nhan export
                      <input id="exportLabel" placeholder="Nhan tuy chon" />
                    </label>
                    <div class="batch-actions">
                      <button class="btn btn-primary" id="exportBtn" type="button">Xuat DOCX</button>
                      <span id="exportStatus" class="muted small">Dang cho</span>
                    </div>
                  </div>
                  <div id="exportResult" class="panel hidden"></div>
                </div>

                <div class="panel stack">
                  <h2>Ghi chu van hanh</h2>
                  <ul class="muted small">
                    <li>Trang thai hien thi o day la trang thai van hanh, khong thay doi semantics cua parser.</li>
                    <li>DOCX upload se di qua dung pipeline batch hien co.</li>
                    <li>Import va export van giu nguyen boundary approved-artifact va assembly.</li>
                  </ul>
                </div>
                """, """
                const operatorApiGet = typeof apiGet === 'function'
                  ? apiGet
                  : async function(path) {
                      const response = await fetch(path, { headers: { 'Accept': 'application/json' } });
                      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
                      return response.json();
                    };

                const operatorApiPost = typeof apiPost === 'function'
                  ? apiPost
                  : async function(path, payload) {
                      const response = await fetch(path, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                        body: JSON.stringify(payload || {})
                      });
                      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
                      return response.json();
                    };

                const state = { jobs: [], bundles: [], uploadInFlight: false };

                async function loadAll() {
                  const [jobs, bundles] = await Promise.all([
                    operatorApiGet('/api/operator/jobs'),
                    operatorApiGet('/api/operator/bundles')
                  ]);
                  state.jobs = jobs.jobs || [];
                  state.bundles = bundles.bundles || [];
                  render();
                }

                function render() {
                  renderSummary();
                  renderJobs();
                  renderBundles();
                }

                function renderSummary() {
                  const root = document.getElementById('operatorSummary');
                  const uploaded = state.jobs.filter(job => String(job.status || '') === 'uploaded').length;
                  const processing = state.jobs.filter(job => String(job.status || '') === 'processing').length;
                  const ready = state.bundles.filter(bundle => String(bundle.operator_state || '') === 'import_ready').length;
                  const blocked = state.bundles.filter(bundle => String(bundle.operator_state || '') === 'import_blocked').length;
                  root.innerHTML = `
                    <div class="summary-card"><div class="label">Tong job</div><div class="value">${state.jobs.length}</div></div>
                    <div class="summary-card"><div class="label">Da upload</div><div class="value">${uploaded}</div></div>
                    <div class="summary-card"><div class="label">Dang xu ly</div><div class="value">${processing}</div></div>
                    <div class="summary-card"><div class="label">Import duoc ngay</div><div class="value">${ready}</div></div>
                    <div class="summary-card"><div class="label">Dang bi chan import</div><div class="value">${blocked}</div></div>
                  `;
                }

                function renderJobs() {
                  const status = document.getElementById('jobsStatus');
                  status.textContent = `Tim thay ${state.jobs.length} job van hanh`;
                  const root = document.getElementById('jobsTable');
                  if (!state.jobs.length) {
                    root.innerHTML = '<p class="muted">Chua co job nao.</p>';
                    return;
                  }
                  root.innerHTML = `
                    <table class="review-table">
                      <thead>
                        <tr>
                          <th>Job</th>
                          <th>Loai</th>
                          <th>Trang thai</th>
                          <th>File nguon</th>
                          <th>Bundle</th>
                          <th>Thao tac</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${state.jobs.map(job => `
                          <tr>
                            <td>
                              <div class="cell-title">${escapeHtml(job.job_id || '')}</div>
                              <div class="muted small">${escapeHtml(job.created_at || '')}</div>
                            </td>
                            <td>${escapeHtml(job.job_type || '')}</td>
                            <td><span class="badge ${statusClass(job.status)}">${escapeHtml(job.status || '')}</span></td>
                            <td>${escapeHtml(job.source_filename || '')}</td>
                            <td>${escapeHtml(job.bundle_id || '')}</td>
                            <td class="actions">
                              ${job.review_link ? `<a class="btn btn-secondary" href="${escapeHtml(job.review_link)}">Mo bundle review</a>` : ''}
                            </td>
                          </tr>
                        `).join('')}
                      </tbody>
                    </table>`;
                }

                function renderBundles() {
                  const status = document.getElementById('bundleStatus');
                  status.textContent = `Tim thay ${state.bundles.length} bundle de kiem tra`;
                  const root = document.getElementById('bundleTable');
                  if (!state.bundles.length) {
                    root.innerHTML = '<p class="muted">Chua co bundle nao trong operator review root.</p>';
                    return;
                  }
                  root.innerHTML = `
                    <table class="review-table">
                      <thead>
                        <tr>
                          <th>Bundle</th>
                          <th>Mon</th>
                          <th>So cau</th>
                          <th>Trang thai</th>
                          <th>Van hanh</th>
                          <th>Readiness import</th>
                          <th>Ly do</th>
                          <th>Da finalize</th>
                          <th>Thao tac</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${state.bundles.map(bundle => `
                          <tr>
                            <td>
                              <div class="cell-title">${escapeHtml(bundle.display_title || bundle.bundle_id || '')}</div>
                              <div class="muted small">${escapeHtml(bundle.bundle_id || '')}</div>
                            </td>
                            <td>${escapeHtml(bundle.subject || '')}</td>
                            <td>${bundle.question_count ?? 0}</td>
                            <td><span class="badge ${statusClass(bundle.status_summary || '')}">${escapeHtml(bundle.status_summary || '')}</span></td>
                            <td><span class="badge ${statusClass(bundle.operator_state || '')}">${escapeHtml(bundle.operator_state || '')}</span></td>
                            <td><span class="badge ${statusClass(bundle.import_readiness_state || '')}">${escapeHtml(bundle.import_readiness_state || '')}</span></td>
                            <td class="muted small">${escapeHtml(bundle.import_readiness_reason || '')}</td>
                            <td>${bundle.finalized ? '<span class="badge badge-good">roi</span>' : '<span class="badge badge-muted">chua</span>'}</td>
                            <td class="actions">
                              <a class="btn btn-secondary" href="${escapeHtml(bundle.review_bundle_link || '')}">Mo review</a>
                              <a class="btn btn-secondary" href="${escapeHtml(bundle.review_bundle_full_link || '')}">Mo 2 cot</a>
                              ${bundle.import_readiness_state === 'approved_importable'
                                  ? `<button class="btn btn-primary" type="button" onclick="triggerImport('${escapeJsString(bundle.bundle_id || '')}')">Import</button>`
                                  : `<button class="btn btn-secondary" type="button" disabled title="${escapeHtml(bundle.import_readiness_reason || '')}">Dang bi chan</button>`
                              }
                            </td>
                          </tr>
                        `).join('')}
                      </tbody>
                    </table>`;
                }

                async function triggerImport(bundleId) {
                  const status = document.getElementById('bundleStatus');
                  status.textContent = `Dang import ${bundleId}...`;
                  try {
                    const data = await operatorApiPost(`/api/operator/import/${encodeURIComponent(bundleId)}`, { bundle_id: bundleId });
                    status.textContent = `Da xep/hoan tat import cho ${bundleId}`;
                    document.getElementById('jobsStatus').textContent = 'Dang tai lai job...';
                    await loadAll();
                    document.getElementById('jobsStatus').textContent = `Da hoan tat lenh import cho ${bundleId}`;
                    console.log(data);
                  } catch (err) {
                    status.textContent = `Import that bai: ${err.message}`;
                  }
                }

                async function uploadDocx() {
                  if (state.uploadInFlight) {
                    return;
                  }
                  const fileInput = document.getElementById('sourceFile');
                  const uploadBtn = document.getElementById('uploadBtn');
                  const file = fileInput.files && fileInput.files[0];
                  if (!file) {
                    document.getElementById('uploadStatus').textContent = 'Hay chon file .docx truoc';
                    return;
                  }
                  state.uploadInFlight = true;
                  uploadBtn.disabled = true;
                  document.getElementById('uploadStatus').textContent = `Dang upload ${file.name}...`;
                  try {
                    const content = await fileToBase64(file);
                    const payload = {
                      filename: file.name,
                      upload_label: document.getElementById('uploadLabel').value || '',
                      content_base64: content
                    };
                    const response = await operatorApiPost('/api/operator/upload', payload);
                    document.getElementById('uploadStatus').textContent = `Da upload thanh ${response.job_id}; da bat dau xu ly`;
                    await loadAll();
                  } catch (err) {
                    document.getElementById('uploadStatus').textContent = `Upload that bai: ${err.message}`;
                  } finally {
                    state.uploadInFlight = false;
                    uploadBtn.disabled = false;
                  }
                }

                async function triggerExport() {
                  const assemblyId = document.getElementById('assemblyId').value.trim();
                  const mode = document.getElementById('assemblyMode').value;
                  if (!assemblyId) {
                    document.getElementById('exportStatus').textContent = 'Hay nhap assembly_id truoc';
                    return;
                  }
                  document.getElementById('exportStatus').textContent = `Dang xuat ${assemblyId} (${mode})...`;
                  try {
                    const data = await operatorApiPost(`/api/operator/export/${encodeURIComponent(assemblyId)}`, {
                      assembly_id: assemblyId,
                      mode,
                      export_label: document.getElementById('exportLabel').value || ''
                    });
                    const root = document.getElementById('exportResult');
                    root.classList.remove('hidden');
                    root.innerHTML = `
                      <div class="summary-grid">
                        <div class="summary-card"><div class="label">Job</div><div class="value">${escapeHtml(data.job_id || '')}</div></div>
                        <div class="summary-card"><div class="label">Trang thai</div><div class="value">${escapeHtml(data.status || '')}</div></div>
                        <div class="summary-card"><div class="label">Verdict</div><div class="value">${escapeHtml(data.verdict || '')}</div></div>
                        <div class="summary-card"><div class="label">Che do</div><div class="value">${escapeHtml(data.export_mode || '')}</div></div>
                      </div>
                      <div class="stack">
                        <div><strong>DOCX:</strong> ${escapeHtml(data.docx_path || '')}</div>
                        <div><strong>Bao cao export:</strong> ${escapeHtml(data.export_report_path || '')}</div>
                        <div><strong>Acceptance:</strong> ${escapeHtml(data.acceptance_json_path || '')}</div>
                      </div>`;
                    document.getElementById('exportStatus').textContent = `Da xuat xong ${assemblyId}`;
                    await loadAll();
                  } catch (err) {
                    document.getElementById('exportStatus').textContent = `Xuat that bai: ${err.message}`;
                  }
                }

                function fileToBase64(file) {
                  return new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => {
                      const result = String(reader.result || '');
                      const comma = result.indexOf(',');
                      resolve(comma >= 0 ? result.slice(comma + 1) : result);
                    };
                    reader.onerror = () => reject(reader.error || new Error('khong doc duoc file'));
                    reader.readAsDataURL(file);
                  });
                }

                document.getElementById('refreshBtn').addEventListener('click', () => loadAll().catch(err => {
                  document.getElementById('jobsStatus').textContent = `Tai lai that bai: ${err.message}`;
                }));
                document.getElementById('uploadBtn').addEventListener('click', () => uploadDocx().catch(err => {
                  document.getElementById('uploadStatus').textContent = `Upload that bai: ${err.message}`;
                }));
                document.getElementById('exportBtn').addEventListener('click', () => triggerExport().catch(err => {
                  document.getElementById('exportStatus').textContent = `Xuat that bai: ${err.message}`;
                }));

                loadAll().catch(err => {
                  document.getElementById('jobsStatus').textContent = `Tai man hinh van hanh that bai: ${err.message}`;
                });
                """);
    }

    static String bundleListPage() {
        return shell("Danh sach de review", """
                <div class="hero">
                  <div>
                    <h1>Danh sach de review</h1>
                    <p class="muted">Chon mot de de xem HTML nguon, cac cau da tach, va sua du lieu parser o mot noi.</p>
                  </div>
                  <div class="hero-actions">
                    <a class="btn btn-secondary" href="/operator/dashboard">Bang dieu khien van hanh</a>
                    <a class="btn btn-secondary" href="/review/bundles">Tai lai</a>
                  </div>
                </div>
                <div id="pageStatus" class="statusline muted">Dang tai danh sach de...</div>
                <div id="bundleTable" class="panel">Dang tai...</div>
                """, """
                const state = { bundles: [] };

                async function load() {
                  const data = await apiGet('/api/review/bundles');
                  state.bundles = data.bundles || [];
                  render();
                }

                function render() {
                  const status = document.getElementById('pageStatus');
                  status.textContent = `Co ${state.bundles.length} de trong workspace`;
                  const root = document.getElementById('bundleTable');
                  if (!state.bundles.length) {
                    root.innerHTML = '<p class="muted">Chua co de nao trong review root.</p>';
                    return;
                  }
                  root.innerHTML = `
                    <table class="review-table">
                      <thead>
                        <tr>
                          <th>Ten file</th>
                          <th>Mon</th>
                          <th>So cau da tach</th>
                          <th>Trang thai</th>
                          <th>Thao tac</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${state.bundles.map(renderBundleRow).join('')}
                      </tbody>
                    </table>`;
                }

                function renderBundleRow(bundle) {
                  const status = bundle.status_summary || 'ready_to_review';
                  return `
                    <tr>
                      <td>
                        <div class="cell-title">${escapeHtml(bundle.display_title || bundle.bundle_id || '')}</div>
                        <div class="muted small">${escapeHtml(bundle.bundle_id || '')}</div>
                      </td>
                      <td>${escapeHtml(bundle.subject || '')}</td>
                      <td>${bundle.question_count ?? 0}</td>
                      <td><span class="badge ${statusClass(status)}">${escapeHtml(vnStatus(status))}</span></td>
                      <td class="actions">
                        <a class="btn btn-primary" href="/review/bundle/${encodeURIComponent(bundle.bundle_id)}">Mo review</a>
                      </td>
                    </tr>`;
                }

                function vnStatus(value) {
                  const status = String(value || '');
                  if (status === 'finalized') return 'da finalize';
                  if (status === 'ready_to_finalize') return 'san sang finalize';
                  if (status === 'needs_review') return 'can review';
                  if (status === 'blocked') return 'bi chan';
                  if (status === 'ready_to_review') return 'san sang review';
                  return status || 'khong ro';
                }

                load().catch(err => {
                  document.getElementById('pageStatus').textContent = `Tai danh sach that bai: ${err.message}`;
                });
                """);
    }

    static String queuePage(String bundleId) {
        return queuePage(bundleId, false);
    }

    static String fullBundlePage(String bundleId) {
        return queuePage(bundleId, true);
    }

    private static String queuePage(String bundleId, boolean fullMode) {
        String title = "Review de thi";
        return shell(title, """
                <script src="https://unpkg.com/mathlive/dist/mathlive.min.js"></script>
                <div class="hero">
                  <div>
                    <h1>Review de thi</h1>
                    <p class="muted">Bundle: <code>%s</code>%s</p>
                    <p class="muted small">Cot trai la HTML nguon. Cot phai la cac cau parser da tach va panel sua.</p>
                  </div>
                  <div class="hero-actions">
                    <a class="btn btn-secondary" href="/review/bundles">Ve danh sach</a>
                    <button class="btn btn-secondary" id="refreshBtn" type="button">Tai lai</button>
                    <button class="btn btn-primary" id="finalizeBtn" type="button">Finalize bundle</button>
                  </div>
                </div>

                <div id="bundleSummary" class="summary-grid"></div>
                <div id="bundleStatus" class="statusline muted">Dang tai bundle...</div>

                <div class="review-workspace">
                  <section class="panel source-pane">
                    <div class="panel-header">
                      <h2>HTML nguon cua de</h2>
                      <span id="sourceHint" class="muted small">Dang tai HTML nguon...</span>
                    </div>
                    <div class="muted small">Day la noi dung de goc de doi chieu. Khong sua truc tiep tai cot nay.</div>
                    <div class="chip-row">
                      <button type="button" class="btn btn-secondary source-tab-btn active" data-source-tab="original">De goc</button>
                      <button type="button" class="btn btn-secondary source-tab-btn" data-source-tab="readable">Ban doc de nhin</button>
                    </div>
                    <div id="sourceArtifactMeta" class="muted small"></div>
                    <div class="source-view-stack">
                      <iframe id="sourceFrame" class="source-frame" title="Source exam HTML"></iframe>
                      <iframe id="readableSourceFrame" class="source-frame hidden" title="Readable source exam HTML"></iframe>
                    </div>
                  </section>

                  <section class="panel parsed-pane stack">
                    <div class="panel-header">
                      <h2>Cau hoi da tach</h2>
                      <input id="questionSearch" placeholder="Tim theo cau, noi dung..." />
                    </div>
                    <div class="muted small">Day la cac doi tuong cau hoi ma parser da tach duoc. Chon mot cau de xem chi tiet va sua.</div>
                    <div id="questionList" class="question-list">Dang tai danh sach cau hoi...</div>

                    <section class="panel panel-nested">
                      <h3>Thong tin tach cau va readiness import</h3>
                      <div id="parsedMeta" class="stack"></div>
                    </section>

                    <section class="panel panel-nested">
                      <h3>Panel sua cau hoi</h3>
                      <div id="editorStatus" class="muted small">Chon mot cau hoi ben tren de sua.</div>
                      <form id="reviewForm" class="stack"></form>
                    </section>

                    <section class="panel panel-nested">
                      <h3>Finalize</h3>
                      <div class="controls">
                        <label>Finalize boi
                          <input id="finalizedBy" placeholder="Nguoi finalize" />
                        </label>
                        <label>Ghi chu finalize
                          <input id="finalizeNote" placeholder="Ghi chu" />
                        </label>
                      </div>
                      <div id="finalizeResult" class="stack"></div>
                    </section>
                  </section>
                </div>
                """.formatted(
                escapeHtml(bundleId),
                fullMode ? " <span class=\"badge badge-info\">xem toan bo bundle</span>" : ""
        ), """
                const bundleId = '%s';
                const fullMode = %s;
                let bundleData = null;
                let sourceData = null;
                let operatorBundle = null;
                let currentDetail = null;
                let selectedQuestionId = '';
                let sourceFrameReady = false;
                let readableFrameReady = false;
                let activeSourceTab = 'original';

                document.getElementById('refreshBtn').addEventListener('click', () => loadBundle().catch(showLoadError));
                document.getElementById('finalizeBtn').addEventListener('click', finalizeBundle);
                document.getElementById('questionSearch').addEventListener('input', debounce(renderQuestionList, 120));
                document.querySelectorAll('.source-tab-btn').forEach(node => {
                  node.addEventListener('click', () => {
                    setSourceTab(node.dataset.sourceTab || 'original');
                  });
                });

                async function loadBundle() {
                  document.getElementById('bundleStatus').textContent = 'Dang tai du lieu bundle...';
                  const [queue, sourceHtml, operatorBundles] = await Promise.all([
                    apiGet(`/api/review/session/${encodeURIComponent(bundleId)}/queue?includeAll=true&includeSecondary=true&includeReviewed=true`),
                    apiGet(`/api/review/session/${encodeURIComponent(bundleId)}/source-html`),
                    apiGet('/api/operator/bundles').catch(() => ({ bundles: [] }))
                  ]);
                  bundleData = queue;
                  sourceData = sourceHtml;
                  operatorBundle = (operatorBundles.bundles || []).find(item => String(item.bundle_id || '') === bundleId) || null;
                  renderBundleSummary();
                  renderSourceHtml();
                  renderQuestionList();
                  const items = Array.isArray(bundleData.items) ? bundleData.items : [];
                  if (items.length) {
                    const nextId = items.some(item => String(item.question_id || '') === selectedQuestionId)
                      ? selectedQuestionId
                      : String(items[0].question_id || '');
                    if (nextId) {
                      await selectQuestion(nextId);
                    }
                  } else {
                    selectedQuestionId = '';
                    currentDetail = null;
                    renderParsedMeta(null);
                    document.getElementById('reviewForm').innerHTML = '<p class="muted">Khong co cau hoi nao de sua.</p>';
                  }
                  document.getElementById('bundleStatus').textContent = buildBundleStatusText();
                }

                function buildBundleStatusText() {
                  const total = bundleData?.total_item_count ?? 0;
                  if (!total) {
                    return 'Khong tach duoc cau hoi nao tu HTML nguon. Kiem tra lai parser, heading va segmentation.';
                  }
                  return `Da tach ${total} cau hoi. Chon mot cau ben phai de xem va sua.`;
                }

                function renderBundleSummary() {
                  const root = document.getElementById('bundleSummary');
                  const items = Array.isArray(bundleData?.items) ? bundleData.items : [];
                  const total = bundleData?.total_item_count ?? items.length;
                  const needsReview = items.filter(item => String(item.review_status || '') === 'needs_review').length;
                  const blocked = items.filter(item => isBlockedItem(item)).length;
                  const ready = items.filter(item => isReadyItem(item)).length;
                  const readiness = operatorBundle?.import_readiness_state || 'chua ro';
                  root.innerHTML = `
                    <div class="summary-card"><div class="label">Tong so cau da tach</div><div class="value">${total}</div></div>
                    <div class="summary-card"><div class="label">Can review</div><div class="value">${needsReview}</div></div>
                    <div class="summary-card"><div class="label">Dang bi chan</div><div class="value">${blocked}</div></div>
                    <div class="summary-card"><div class="label">San sang</div><div class="value">${ready}</div></div>
                    <div class="summary-card"><div class="label">Readiness import</div><div class="value">${escapeHtml(vnReadiness(readiness))}</div></div>
                  `;
                  if (!document.getElementById('finalizedBy').value) {
                    document.getElementById('finalizedBy').value = bundleData?.finalized_by || bundleData?.primary_reviewer || '';
                  }
                  if (!document.getElementById('finalizeNote').value && bundleData?.finalize_note) {
                    document.getElementById('finalizeNote').value = bundleData.finalize_note || '';
                  }
                }

                function renderSourceHtml() {
                  const frame = document.getElementById('sourceFrame');
                  const readableFrame = document.getElementById('readableSourceFrame');
                  const sourceHint = document.getElementById('sourceHint');
                  const sourceMeta = document.getElementById('sourceArtifactMeta');
                  const rawHtml = String(sourceData?.html_content || '');
                  const safeHtml = injectSourceChrome(stripScripts(rawHtml));
                  const readableHtml = buildReadableHtml(rawHtml);
                  sourceFrameReady = false;
                  readableFrameReady = false;
                  frame.onload = () => {
                    sourceFrameReady = true;
                    if (currentDetail) {
                      highlightSourceForDetail(currentDetail);
                    }
                  };
                  readableFrame.onload = () => {
                    readableFrameReady = true;
                    if (currentDetail) {
                      highlightSourceForDetail(currentDetail);
                    }
                  };
                  frame.srcdoc = safeHtml;
                  readableFrame.srcdoc = readableHtml;
                  sourceMeta.innerHTML = `
                    <div><strong>HTML:</strong> <span class="muted">${escapeHtml(sourceData?.source_html_path || '')}</span></div>
                    <div><strong>DOCX:</strong> <span class="muted">${escapeHtml(sourceData?.source_docx_path || '')}</span></div>`;
                  sourceHint.textContent = sourceData?.html_available
                    ? `Dang xem: ${sourceData.source_html_path || ''}`
                    : 'Khong tim thay file HTML nguon';
                  setSourceTab(activeSourceTab);
                }

                function setSourceTab(tabName) {
                  activeSourceTab = tabName === 'readable' ? 'readable' : 'original';
                  const original = document.getElementById('sourceFrame');
                  const readable = document.getElementById('readableSourceFrame');
                  original.classList.toggle('hidden', activeSourceTab !== 'original');
                  readable.classList.toggle('hidden', activeSourceTab !== 'readable');
                  document.querySelectorAll('.source-tab-btn').forEach(node => {
                    const isActive = (node.dataset.sourceTab || 'original') === activeSourceTab;
                    node.classList.toggle('active', isActive);
                    node.classList.toggle('btn-primary', isActive);
                    node.classList.toggle('btn-secondary', !isActive);
                  });
                  if (currentDetail) {
                    highlightSourceForDetail(currentDetail);
                  }
                }

                function renderQuestionList() {
                  const root = document.getElementById('questionList');
                  const items = Array.isArray(bundleData?.items) ? bundleData.items : [];
                  const search = String(document.getElementById('questionSearch').value || '').trim().toLowerCase();
                  const filtered = items.filter(item => {
                    if (!search) return true;
                    const haystack = `${item.display_label || ''} ${item.question_type || ''} ${item.prompt_preview || ''}`.toLowerCase();
                    return haystack.includes(search);
                  });
                  if (!filtered.length) {
                    root.innerHTML = '<p class="muted">Khong co cau hoi nao khop bo loc hien tai.</p>';
                    return;
                  }
                  root.innerHTML = filtered.map(renderQuestionCard).join('');
                  document.querySelectorAll('.question-card').forEach(node => {
                    node.addEventListener('click', () => {
                      selectQuestion(node.dataset.questionId).catch(err => {
                        document.getElementById('editorStatus').textContent = `Tai chi tiet cau hoi that bai: ${err.message}`;
                      });
                    });
                  });
                }

                function renderQuestionCard(item) {
                  const qid = String(item.question_id || '');
                  const selected = qid === selectedQuestionId ? ' selected' : '';
                  const reviewStatus = vnReviewStatus(item.review_status || 'needs_review');
                  const parserStatus = vnParserStatus(item.parser_status || 'unknown');
                  const issueCodes = Array.isArray(item.issue_codes) ? item.issue_codes : [];
                  const itemState = isBlockedItem(item) ? 'badge-bad' : (isReadyItem(item) ? 'badge-good' : statusClass(item.review_status || ''));
                  return `
                    <button type="button" class="question-card${selected}" data-question-id="${escapeHtml(qid)}">
                      <div class="question-card-top">
                        <strong>${escapeHtml(item.display_label || qid)}</strong>
                        <span class="badge ${itemState}">${escapeHtml(reviewStatus)}</span>
                      </div>
                      <div class="muted small">${escapeHtml(item.question_type || '')} · ${escapeHtml(item.document_family || '')}</div>
                      <div class="muted small">${escapeHtml(item.prompt_preview || '').slice(0, 160)}</div>
                      <div class="tag-row">
                        <span class="badge badge-muted">${escapeHtml(parserStatus)}</span>
                        ${item.has_math ? '<span class="badge badge-info">co toan</span>' : ''}
                        ${item.has_image ? '<span class="badge badge-info">co hinh</span>' : ''}
                        ${issueCodes.slice(0, 2).map(code => `<span class="badge badge-warn">${escapeHtml(code)}</span>`).join('')}
                      </div>
                    </button>`;
                }

                async function selectQuestion(questionId) {
                  selectedQuestionId = String(questionId || '');
                  renderQuestionList();
                  document.getElementById('editorStatus').textContent = 'Dang tai chi tiet cau hoi...';
                  const detail = await apiGet(`/api/review/session/${encodeURIComponent(bundleId)}/question/${encodeURIComponent(selectedQuestionId)}`);
                  currentDetail = detail;
                  renderParsedMeta(detail);
                  renderEditor(detail);
                  highlightSourceForDetail(detail);
                  document.getElementById('editorStatus').textContent = `Dang sua ${detail.display_label || detail.question_id}`;
                }

                function renderParsedMeta(detail) {
                  const root = document.getElementById('parsedMeta');
                  if (!detail) {
                    root.innerHTML = `<div class="muted">Chua co cau hoi nao duoc chon.</div>`;
                    return;
                  }
                  const issueCodes = Array.isArray(detail.issue_codes) ? detail.issue_codes : [];
                  root.innerHTML = `
                      <div class="summary-grid">
                      <div class="summary-card"><div class="label">Loai doi tuong cau hoi</div><div class="value">${escapeHtml(detail.question_type || 'unknown')}</div></div>
                      <div class="summary-card"><div class="label">Trang thai parser</div><div class="value">${escapeHtml(vnParserStatus(detail.parser_status || 'unknown'))}</div></div>
                      <div class="summary-card"><div class="label">Nguon dap an dang duoc chon</div><div class="value">${escapeHtml(detail.reconciliation?.chosen_source || 'khong ro')}</div></div>
                      <div class="summary-card"><div class="label">Readiness import cua bundle</div><div class="value">${escapeHtml(vnReadiness(operatorBundle?.import_readiness_state || 'blocked_import'))}</div></div>
                    </div>
                    <div class="stack tight">
                      <div><strong>HTML nguon:</strong> <span class="muted">${escapeHtml(sourceData?.source_html_path || '')}</span></div>
                      <div><strong>Question object id:</strong> <code>${escapeHtml(detail.question_id || '')}</code></div>
                      <div><strong>Readiness import:</strong> <span class="badge ${statusClass(operatorBundle?.import_readiness_state || '')}">${escapeHtml(vnReadiness(operatorBundle?.import_readiness_state || 'blocked_import'))}</span> <span class="muted small">${escapeHtml(operatorBundle?.import_readiness_reason || '')}</span></div>
                      <div><strong>Ly do can sua:</strong> ${issueCodes.length ? issueCodes.map(code => `<span class="badge badge-warn">${escapeHtml(code)}</span>`).join(' ') : '<span class="badge badge-good">khong co</span>'}</div>
                      <details>
                        <summary>Doi tuong parser question</summary>
                        <pre class="excerpt mono">${escapeHtml(JSON.stringify(detail.parser_question || {}, null, 2))}</pre>
                      </details>
                      <details>
                        <summary>Doi tuong question da tach</summary>
                        <pre class="excerpt mono">${escapeHtml(JSON.stringify(detail.question_item || {}, null, 2))}</pre>
                      </details>
                    </div>`;
                }

                function renderEditor(detail) {
                  const form = document.getElementById('reviewForm');
                  form.innerHTML = '';

                  const statusSelect = document.createElement('select');
                  statusSelect.id = 'reviewStatus';
                  ['needs_review', 'reviewed_fixed', 'reviewed_confirmed', 'skipped', 'rejected_from_import', 'auto_accepted']
                    .forEach(value => {
                    const option = document.createElement('option');
                      option.value = value;
                      option.textContent = vnReviewStatus(value);
                      option.selected = value === (detail.review_status || 'needs_review');
                      statusSelect.appendChild(option);
                    });
                  const reviewer = el('input', { id: 'reviewer', value: detail.reviewer || detail.primary_reviewer || 'user', placeholder: 'Nguoi review' });
                  const note = el('textarea', { id: 'reviewNote', placeholder: 'Ghi chu review' }, detail.review_note || '');

                  form.appendChild(field('Trang thai review', statusSelect));
                  form.appendChild(field('Nguoi review', reviewer));
                  form.appendChild(field('Ghi chu', note));

                  const editorWrap = el('div', { class: 'editor-kind stack' });
                  editorWrap.appendChild(el('div', { class: 'muted small' }, 'Sua answer/rubric o day. HTML nguon o cot trai chi de doi chieu, khong sua truc tiep.'));
                  const kind = editorKind(detail);
                  if (kind === 'single_choice') {
                    editorWrap.appendChild(renderSingleChoiceEditor(detail));
                  } else if (kind === 'boolean_group') {
                    editorWrap.appendChild(renderBooleanEditor(detail));
                  } else if (kind === 'short_answer') {
                    editorWrap.appendChild(renderShortAnswerEditor(detail));
                  } else if (kind === 'rubric') {
                    editorWrap.appendChild(renderRubricEditor(detail));
                  } else {
                    editorWrap.appendChild(el('p', { class: 'muted' }, 'Loai cau hoi nay chua co control sua dac thu. Van co the sua trang thai review va ghi chu.'));
                  }
                  form.appendChild(editorWrap);

                  const saveActions = el('div', { class: 'actions' }, [
                    el('button', { type: 'button', id: 'saveBtnInline', class: 'btn btn-primary' }, 'Luu cau hoi'),
                    el('a', { href: `/review/bundle/${encodeURIComponent(bundleId)}/question/${encodeURIComponent(detail.question_id)}`, class: 'btn btn-secondary' }, 'Mo trang chi tiet cu')
                  ]);
                  form.appendChild(saveActions);
                  document.getElementById('saveBtnInline').addEventListener('click', () => saveReview().catch(err => {
                    document.getElementById('editorStatus').textContent = `Luu that bai: ${err.message}`;
                  }));
                  wireMathEditors();
                }

                function renderSingleChoiceEditor(detail) {
                  const current = detail.question_item?.answer_key?.value || '';
                  const box = el('div', { class: 'stack' });
                  const group = document.createElement('div');
                  group.className = 'choice-group';
                  for (const choice of ['A', 'B', 'C', 'D']) {
                    const label = document.createElement('label');
                    label.className = 'choice-chip';
                    label.innerHTML = `<input type="radio" name="answerChoice" value="${choice}" ${current === choice ? 'checked' : ''} /> <span>${choice}</span>`;
                    group.appendChild(label);
                  }
                  const clearBtn = el('button', { type: 'button', class: 'btn btn-secondary' }, 'Xoa dap an');
                  clearBtn.addEventListener('click', () => {
                    group.querySelectorAll('input[type=radio]').forEach(r => r.checked = false);
                  });
                  box.appendChild(group);
                  box.appendChild(clearBtn);
                  return box;
                }

                function renderBooleanEditor(detail) {
                  const current = detail.question_item?.answer_key?.subanswers || {};
                  const wrap = el('div', { class: 'stack' });
                  const table = el('table', { class: 'review-table compact' });
                  table.innerHTML = `
                    <thead><tr><th>Nhan</th><th>Gia tri</th></tr></thead>
                    <tbody>
                      ${['a','b','c','d'].map(label => `
                        <tr>
                          <td><strong>${label}</strong></td>
                          <td>
                            <select data-boolean-label="${label}">
                              <option value="">xoa</option>
                              <option value="true" ${current[String(label)] === true ? 'selected' : ''}>dung</option>
                              <option value="false" ${current[String(label)] === false ? 'selected' : ''}>sai</option>
                            </select>
                          </td>
                        </tr>`).join('')}
                    </tbody>`;
                  wrap.appendChild(table);
                  return wrap;
                }

                function renderShortAnswerEditor(detail) {
                  const accepted = detail.question_item?.answer_key?.accepted_answers || [];
                  const wrap = el('div', { class: 'stack' });
                  const list = el('div', { id: 'shortAnswerRows', class: 'stack' });
                  if (!accepted.length) {
                    list.appendChild(shortAnswerRow({ raw: '', normalized: '' }));
                  } else {
                    accepted.forEach(answer => list.appendChild(shortAnswerRow(answer)));
                  }
                  const addBtn = el('button', { type: 'button', class: 'btn btn-secondary' }, 'Them dap an chap nhan');
                  addBtn.addEventListener('click', () => list.appendChild(shortAnswerRow({ raw: '', normalized: '' })));
                  wrap.appendChild(list);
                  wrap.appendChild(addBtn);
                  return wrap;
                }

                function renderRubricEditor(detail) {
                  const rubric = detail.question_item?.rubric || {};
                  const wrap = el('div', { class: 'stack' });
                  wrap.appendChild(field('Rubric text', editableMathText('rubricText', rubric.rubric_text || rubric.text || '', 'Noi dung rubric')));
                  wrap.appendChild(field('Rubric JSON', el('textarea', { id: 'rubricJson', class: 'mono', placeholder: 'Rubric JSON' }, JSON.stringify(rubric.blocks || [], null, 2))));
                  return wrap;
                }

                function shortAnswerRow(answer) {
                  const row = el('div', { class: 'short-answer-row' });
                  row.innerHTML = `
                    <div class="math-editor">
                      <math-field class="math-field" data-role="raw">${escapeHtml(answer.raw_input_latex || answer.raw || '')}</math-field>
                      <textarea class="plain-text" data-role="raw-text" placeholder="Dap an goc">${escapeHtml(answer.raw || '')}</textarea>
                    </div>
                    <input class="normalized-input" data-role="normalized" placeholder="Dap an chuan hoa" value="${escapeHtml(answer.normalized || '')}" />
                    <button type="button" class="btn btn-secondary" data-role="remove">Xoa</button>`;
                  row.querySelector('[data-role="remove"]').addEventListener('click', () => row.remove());
                  return row;
                }

                function editableMathText(id, value, placeholder) {
                  const wrap = el('div', { class: 'math-editor' });
                  wrap.appendChild(el('math-field', { id, class: 'math-field' }, value || ''));
                  wrap.appendChild(el('textarea', { id: `${id}Text`, class: 'plain-text', placeholder }, value || ''));
                  return wrap;
                }

                function editorKind(detail) {
                  const mode = detail.question_item?.answer_key?.mode || 'none';
                  const qType = detail.question_type || '';
                  if (mode === 'single_choice' || qType === 'single_choice') return 'single_choice';
                  if (mode === 'boolean_group' || qType === 'true_false') return 'boolean_group';
                  if (mode === 'short_answer' || qType === 'short_answer') return 'short_answer';
                  if (mode === 'rubric' || qType === 'essay') return 'rubric';
                  return 'none';
                }

                function wireMathEditors() {
                  document.querySelectorAll('.math-editor').forEach(container => {
                    const mathField = container.querySelector('math-field');
                    const textarea = container.querySelector('textarea');
                    if (!mathField || !textarea) return;
                    mathField.addEventListener('input', () => {
                      textarea.value = mathField.value || '';
                    });
                    textarea.addEventListener('input', () => {
                      mathField.value = textarea.value || '';
                    });
                  });
                }

                function collectEditPayload(detail) {
                  const kind = editorKind(detail);
                  const edits = {};
                  if (kind === 'single_choice') {
                    const selected = document.querySelector('input[name="answerChoice"]:checked');
                    edits.answer_key = selected ? { mode: 'single_choice', value: selected.value } : { mode: 'none' };
                  } else if (kind === 'boolean_group') {
                    const subanswers = {};
                    document.querySelectorAll('[data-boolean-label]').forEach(sel => {
                      const label = sel.getAttribute('data-boolean-label');
                      if (sel.value === 'true') subanswers[label] = true;
                      if (sel.value === 'false') subanswers[label] = false;
                    });
                    edits.boolean_subanswers = subanswers;
                    if (!Object.keys(subanswers).length) {
                      edits.answer_key = { mode: 'none' };
                    }
                  } else if (kind === 'short_answer') {
                    const answers = [];
                    document.querySelectorAll('#shortAnswerRows .short-answer-row').forEach(row => {
                      const rawField = row.querySelector('[data-role="raw"]');
                      const rawText = row.querySelector('[data-role="raw-text"]');
                      const normalized = row.querySelector('[data-role="normalized"]');
                      const raw = (rawField && rawField.value ? rawField.value : (rawText && rawText.value ? rawText.value : '')).trim();
                      const norm = (normalized && normalized.value ? normalized.value : raw).trim();
                      if (raw || norm) answers.push({ raw, normalized: norm });
                    });
                    if (answers.length) {
                      edits.accepted_answers = answers;
                    } else {
                      edits.answer_key = { mode: 'none' };
                    }
                  } else if (kind === 'rubric') {
                    const rubricText = (document.getElementById('rubricTextText')?.value || document.getElementById('rubricText')?.value || '').trim();
                    const rubricJsonRaw = (document.getElementById('rubricJson')?.value || '[]').trim();
                    let blocks = [];
                    try { blocks = rubricJsonRaw ? JSON.parse(rubricJsonRaw) : []; } catch (err) { blocks = []; }
                    edits.rubric = { mode: 'rubric', rubric_text: rubricText, blocks };
                  }
                  return edits;
                }

                async function saveReview() {
                  if (!currentDetail || !selectedQuestionId) return;
                  const body = {
                    review_status: document.getElementById('reviewStatus').value,
                    review_note: document.getElementById('reviewNote').value,
                    reviewer: document.getElementById('reviewer').value,
                    edits: collectEditPayload(currentDetail)
                  };
                  await apiPost(`/api/review/session/${encodeURIComponent(bundleId)}/question/${encodeURIComponent(selectedQuestionId)}/save`, body);
                  document.getElementById('editorStatus').textContent = `Da luu ${currentDetail.display_label || currentDetail.question_id}`;
                  await loadBundle();
                  if (selectedQuestionId) {
                    await selectQuestion(selectedQuestionId);
                  }
                }

                async function finalizeBundle() {
                  const result = await apiPost(`/api/review/session/${encodeURIComponent(bundleId)}/finalize`, {
                    finalized_by: document.getElementById('finalizedBy').value,
                    finalize_note: document.getElementById('finalizeNote').value
                  });
                  renderFinalizeResult(result);
                  await loadBundle();
                }

                function renderFinalizeResult(data) {
                  const root = document.getElementById('finalizeResult');
                  const blockers = Array.isArray(data.blockers) ? data.blockers : [];
                  root.innerHTML = `
                    <div class="summary-grid">
                      <div class="summary-card"><div class="label">Trang thai finalize</div><div class="value">${escapeHtml(data.status || 'unknown')}</div></div>
                      <div class="summary-card"><div class="label">Finalized boi</div><div class="value">${escapeHtml(data.finalized_by || '—')}</div></div>
                    </div>
                    ${blockers.length ? `<div class="muted small">${blockers.map(item => escapeHtml(item.code || item.question_id || 'blocker')).join(', ')}</div>` : '<div class="badge badge-good">Khong co blocker finalize.</div>'}`;
                }

                function stripScripts(html) {
                  return String(html || '').replace(/<script\\b[^>]*>[\\s\\S]*?<\\/script>/gi, '');
                }

                function injectSourceChrome(html) {
                  const extra = `<style>
                    body { margin: 0; padding: 18px; font: 15px/1.55 system-ui, sans-serif; }
                    .qb-selected-fragment { background: #fff3b0 !important; outline: 2px solid #d97706 !important; }
                  </style>`;
                  if (/<\\/head>/i.test(html)) {
                    return html.replace(/<\\/head>/i, `${extra}</head>`);
                  }
                  return `<!doctype html><html><head><meta charset="utf-8">${extra}</head><body>${html}</body></html>`;
                }

                function buildReadableHtml(rawHtml) {
                  const source = stripScripts(rawHtml);
                  const parser = new DOMParser();
                  const sourceDoc = parser.parseFromString(source || '<html><body></body></html>', 'text/html');
                  const blocks = [];
                  const blockNodes = Array.from(sourceDoc.body?.querySelectorAll('h1,h2,h3,h4,p,div,li,table,img') || []);
                  let optionBuffer = [];

                  function flushOptions() {
                    if (!optionBuffer.length) return;
                    blocks.push(`<div class="readable-options">${optionBuffer.join('')}</div>`);
                    optionBuffer = [];
                  }

                  for (const node of blockNodes) {
                    if (node.closest('table') && node.tagName.toLowerCase() !== 'table') {
                      continue;
                    }
                    const text = normalizeTextForReadable(node.textContent || '');
                    if (!text && node.tagName.toLowerCase() !== 'img' && node.tagName.toLowerCase() !== 'table') {
                      continue;
                    }
                    const originalText = String(node.textContent || '').replace(/\\s+/g, ' ').trim();
                    if (node.tagName.toLowerCase() === 'table') {
                      flushOptions();
                      blocks.push(`<div class="readable-table-wrap">${sanitizeTableHtml(node.outerHTML)}</div>`);
                      continue;
                    }
                    if (node.tagName.toLowerCase() === 'img') {
                      const src = node.getAttribute('src') || '';
                      if (!src) continue;
                      flushOptions();
                      blocks.push(`<figure class="readable-image"><img src="${escapeHtml(src)}" alt="Anh trong de" /></figure>`);
                      continue;
                    }
                    if (isSectionHeading(text)) {
                      flushOptions();
                      blocks.push(`<h2 data-search-text="${escapeHtml(text)}">${escapeHtml(originalText)}</h2>`);
                      continue;
                    }
                    if (isQuestionHeading(text)) {
                      flushOptions();
                      blocks.push(`<h3 data-search-text="${escapeHtml(text)}">${escapeHtml(originalText)}</h3>`);
                      continue;
                    }
                    if (isChoiceLine(text)) {
                      optionBuffer.push(`<div class="readable-option" data-search-text="${escapeHtml(text)}">${escapeHtml(originalText)}</div>`);
                      continue;
                    }
                    flushOptions();
                    blocks.push(`<p data-search-text="${escapeHtml(text)}">${escapeHtml(originalText)}</p>`);
                  }
                  flushOptions();
                  const readableBody = blocks.length
                    ? blocks.join('')
                    : '<p>Khong the tao ban doc de nhin tu HTML nguon nay.</p>';
                  return `<!doctype html><html><head><meta charset="utf-8"><style>
                    body { margin: 0; padding: 22px; font: 16px/1.65 Georgia, \"Times New Roman\", serif; color: #142033; background: #fff; }
                    h1,h2,h3,h4 { margin: 18px 0 8px; line-height: 1.35; }
                    h2 { font-size: 22px; border-bottom: 1px solid #d5ddea; padding-bottom: 6px; }
                    h3 { font-size: 19px; color: #15396b; }
                    p { margin: 10px 0; }
                    .readable-options { display: grid; gap: 8px; margin: 10px 0 16px; }
                    .readable-option { padding: 8px 10px; border: 1px solid #d5ddea; border-radius: 10px; background: #f8fbff; }
                    .readable-table-wrap { overflow-x: auto; margin: 12px 0; }
                    table { width: 100%; border-collapse: collapse; font-size: 14px; }
                    th, td { border: 1px solid #d5ddea; padding: 8px 10px; vertical-align: top; }
                    th { background: #f2f5f9; }
                    img { max-width: 100%; height: auto; border: 1px solid #d5ddea; border-radius: 8px; }
                    .qb-selected-fragment { background: #fff3b0 !important; outline: 2px solid #d97706 !important; }
                  </style></head><body>${readableBody}</body></html>`;
                }

                function sanitizeTableHtml(tableHtml) {
                  return String(tableHtml || '')
                    .replace(/\\s(class|style|width|height|border|cellpadding|cellspacing)=\"[^\"]*\"/gi, '')
                    .replace(/\\s(class|style|width|height|border|cellpadding|cellspacing)='[^']*'/gi, '');
                }

                function normalizeTextForReadable(value) {
                  return String(value || '').replace(/\\s+/g, ' ').trim();
                }

                function isSectionHeading(text) {
                  return /^(phan|part|section|muc)\\b/i.test(String(text || ''));
                }

                function isQuestionHeading(text) {
                  return /^(cau|question)\\s+\\d+\\b/i.test(String(text || ''));
                }

                function isChoiceLine(text) {
                  return /^[A-D][\\.|\\)|:]\\s+/.test(String(text || ''));
                }

                function highlightSourceForDetail(detail) {
                  const originalFrame = document.getElementById('sourceFrame');
                  const readableFrame = document.getElementById('readableSourceFrame');
                  let highlighted = false;
                  if (sourceFrameReady && originalFrame.contentDocument) {
                    highlighted = highlightInsideFrame(originalFrame.contentDocument, detail) || highlighted;
                  }
                  if (readableFrameReady && readableFrame.contentDocument) {
                    highlighted = highlightInsideFrame(readableFrame.contentDocument, detail) || highlighted;
                  }
                  if (!highlighted) {
                    document.getElementById('sourceHint').textContent = `Khong tim thay vi tri noi bat cho ${detail.display_label || detail.question_id}`;
                    return;
                  }
                  const viewName = activeSourceTab === 'readable' ? 'ban doc de nhin' : 'HTML nguon';
                  document.getElementById('sourceHint').textContent = `Dang doi chieu ${detail.display_label || detail.question_id} trong ${viewName}`;
                }

                function highlightInsideFrame(doc, detail) {
                  clearSourceHighlight(doc);
                  const target = findSourceElement(doc, detail);
                  if (!target) return false;
                  target.classList.add('qb-selected-fragment');
                  try {
                    target.scrollIntoView({ block: 'center', behavior: 'smooth' });
                  } catch (err) {
                    target.scrollIntoView();
                  }
                  return true;
                }

                function clearSourceHighlight(doc) {
                  doc.querySelectorAll('.qb-selected-fragment').forEach(node => node.classList.remove('qb-selected-fragment'));
                }

                function findSourceElement(doc, detail) {
                  const candidates = [];
                  const prompt = normalizeText(detail.prompt_preview || '');
                  if (prompt) candidates.push(prompt.slice(0, 80));
                  if (detail.question_number) candidates.push(`cau ${detail.question_number}`);
                  if (detail.display_label) candidates.push(normalizeText(detail.display_label));
                  const nodes = Array.from(doc.body?.querySelectorAll('p,li,div,td,th,span,h1,h2,h3,h4') || []);
                  for (const candidate of candidates) {
                    if (!candidate) continue;
                    const found = nodes.find(node => normalizeText(node.textContent || '').includes(candidate));
                    if (found) return found;
                  }
                  return null;
                }

                function normalizeText(value) {
                  return String(value || '').toLowerCase().replace(/\\s+/g, ' ').trim();
                }

                function isBlockedItem(item) {
                  const reviewStatus = String(item?.review_status || '');
                  const parserStatus = String(item?.parser_status || '');
                  return reviewStatus === 'rejected_from_import'
                    || parserStatus === 'conflict'
                    || parserStatus === 'blocked'
                    || Boolean(item?.conflict);
                }

                function isReadyItem(item) {
                  const reviewStatus = String(item?.review_status || '');
                  return reviewStatus === 'reviewed_fixed'
                    || reviewStatus === 'reviewed_confirmed'
                    || reviewStatus === 'auto_accepted';
                }

                function vnReadiness(value) {
                  const state = String(value || '');
                  if (state === 'approved_importable') return 'duoc import';
                  if (state === 'draft_importable') return 'chi o muc draft';
                  if (state === 'blocked_import') return 'bi chan import';
                  return state || 'khong ro';
                }

                function vnParserStatus(value) {
                  const status = String(value || '');
                  if (status === 'resolved') return 'da giai quyet';
                  if (status === 'needs_review') return 'can review';
                  if (status === 'conflict') return 'xung dot';
                  if (status === 'blocked') return 'bi chan';
                  return status || 'khong ro';
                }

                function vnReviewStatus(value) {
                  const status = String(value || '');
                  if (status === 'needs_review') return 'can review';
                  if (status === 'reviewed_fixed') return 'da sua';
                  if (status === 'reviewed_confirmed') return 'da xac nhan';
                  if (status === 'auto_accepted') return 'duoc chap nhan';
                  if (status === 'skipped') return 'bo qua';
                  if (status === 'rejected_from_import') return 'loai khoi import';
                  return status || 'khong ro';
                }

                function showLoadError(err) {
                  document.getElementById('bundleStatus').textContent = `Tai bundle that bai: ${err.message}`;
                }

                loadBundle().catch(showLoadError);
                """.formatted(escapeJsString(bundleId), String.valueOf(fullMode)));
    }

    static String questionDetailPage(String bundleId, String questionId) {
        return shell("Review question", """
                <script src="https://unpkg.com/mathlive/dist/mathlive.min.js"></script>
                <div class="hero">
                  <div>
                    <h1>Question detail</h1>
                    <p class="muted">Bundle: <code>%s</code> · Question: <code>%s</code></p>
                  </div>
                  <div class="hero-actions">
                    <a class="btn btn-secondary" id="backQueue" href="/review/bundle/%s">Back to queue</a>
                    <button class="btn btn-secondary" id="prevBtn" type="button">Previous</button>
                    <button class="btn btn-secondary" id="nextBtn" type="button">Next</button>
                    <button class="btn btn-primary" id="saveBtn" type="button">Save review</button>
                    <button class="btn btn-primary" id="saveNextBtn" type="button">Save & next</button>
                  </div>
                </div>

                <div id="detailStatus" class="statusline muted">Loading question...</div>

                <div class="detail-grid">
                  <section class="panel">
                    <h2>Original content</h2>
                    <div id="questionMeta"></div>
                    <div id="questionPreview" class="question-preview"></div>
                    <h3>Source excerpt</h3>
                    <pre id="sourceExcerpt" class="excerpt"></pre>
                    <h3>Answer excerpt</h3>
                    <pre id="answerExcerpt" class="excerpt"></pre>
                    <h3>Rubric excerpt</h3>
                    <pre id="rubricExcerpt" class="excerpt"></pre>
                  </section>

                  <div class="stack">
                    <section class="panel">
                      <h2>Parser evidence</h2>
                      <div id="evidence"></div>
                    </section>
                    <section class="panel">
                      <h2>Review editor</h2>
                      <form id="reviewForm" class="stack"></form>
                    </section>
                  </div>
                </div>

                <div id="saveStatus" class="panel hidden"></div>
                """.formatted(escapeHtml(bundleId), escapeHtml(questionId), escapeHtml(bundleId)), """
                const bundleId = '%s';
                const questionId = '%s';
                let currentDetail = null;

                document.getElementById('saveBtn').addEventListener('click', () => saveReview(false));
                document.getElementById('saveNextBtn').addEventListener('click', () => saveReview(true));
                document.getElementById('prevBtn').addEventListener('click', () => navigateSibling('prev_question_id'));
                document.getElementById('nextBtn').addEventListener('click', () => navigateSibling('next_question_id'));
                document.addEventListener('keydown', (event) => {
                  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
                    event.preventDefault();
                    saveReview(false).catch(() => {});
                  }
                  if (event.altKey && event.key === 'ArrowRight') {
                    event.preventDefault();
                    navigateSibling('next_question_id');
                  }
                  if (event.altKey && event.key === 'ArrowLeft') {
                    event.preventDefault();
                    navigateSibling('prev_question_id');
                  }
                });

                async function load() {
                  const data = await apiGet(`/api/review/session/${encodeURIComponent(bundleId)}/question/${encodeURIComponent(questionId)}`);
                  currentDetail = data;
                  render(data);
                }

                function render(detail) {
                  const reconciliation = detail.reconciliation || {};
                  const issueCodes = Array.isArray(detail.issue_codes) ? detail.issue_codes : [];
                  const qaFlags = Array.isArray(detail.qa_flags) ? detail.qa_flags : [];
                  const assetRoles = Array.isArray(detail.asset_roles) ? detail.asset_roles : [];
                  document.getElementById('detailStatus').textContent = `${detail.display_label || detail.question_id} · ${detail.question_type || 'unknown'} · ${detail.document_family || 'unknown'}`;
                  document.getElementById('backQueue').href = `/review/bundle/${encodeURIComponent(bundleId)}`;

                  document.getElementById('questionMeta').innerHTML = `
                    <div class="summary-grid">
                      <div class="summary-card"><div class="label">Confidence</div><div class="value">${formatConfidence(detail.parse_confidence)}</div></div>
                      <div class="summary-card"><div class="label">Math fragments</div><div class="value">${detail.math_fragment_count ?? 0}</div></div>
                      <div class="summary-card"><div class="label">Assets</div><div class="value">${detail.asset_count ?? 0}</div></div>
                      <div class="summary-card"><div class="label">Review status</div><div class="value">${escapeHtml(detail.review_status || 'needs_review')}</div></div>
                      <div class="summary-card"><div class="label">Reviewed by</div><div class="value">${escapeHtml(formatNameList(detail.reviewed_by_all, detail.reviewed_by_count))}</div></div>
                      <div class="summary-card"><div class="label">Finalized by</div><div class="value">${escapeHtml(detail.finalized_by || '—')}</div></div>
                    </div>
                    <div class="tag-row">
                      ${statusBadge('Parser', detail.parser_status || 'unknown')}
                      ${statusBadge('Review', detail.review_status || 'needs_review')}
                      ${statusBadge('Reconciliation', reconciliation.status || 'unknown')}
                      ${statusBadge('Chosen source', reconciliation.chosen_source || 'none', reconciliation.chosen_source ? 'badge-info' : 'badge-muted')}
                    </div>
                    <div class="tag-row">
                      ${chipList('Assets', assetRoles)}
                      ${chipList('QA flags', qaFlags)}
                      ${chipList('Issues', issueCodes)}
                    </div>`;

                  document.getElementById('questionPreview').innerHTML = `
                    <div class="panel-subtitle">Prompt preview</div>
                    <div class="question-preview-box">${escapeHtml(detail.prompt_preview || '')}</div>
                    <div class="panel-subtitle">Asset roles</div>
                    <div class="tag-row">${chipList('', assetRoles, true)}</div>
                    <div class="panel-subtitle">Answer source</div>
                    <div class="muted small">${escapeHtml((detail.answer_detection && detail.answer_detection.source) || '')}</div>`;

                  document.getElementById('sourceExcerpt').textContent = detail.source_html_excerpt || '';
                  document.getElementById('answerExcerpt').textContent = detail.answer_html_excerpt || '';
                  document.getElementById('rubricExcerpt').textContent = detail.rubric_html_excerpt || '';
                  renderEvidence(detail);
                  renderEditor(detail);
                }

                function renderEvidence(detail) {
                  const root = document.getElementById('evidence');
                  root.innerHTML = `
                    <div class="stack">
                      ${summaryLine('Chosen source', detail.reconciliation?.chosen_source || 'none')}
                      ${summaryLine('Reconciliation status', detail.reconciliation?.status || 'unknown')}
                      ${summaryLine('Answer key mode', detail.question_item?.answer_key?.mode || 'none')}
                      ${summaryLine('Reviewed by', formatNameList(detail.reviewed_by_all, detail.reviewed_by_count))}
                      ${summaryLine('Finalized by', detail.finalized_by || 'none')}
                      ${summaryLine('Finalize note', detail.finalize_note || 'none')}
                      ${panelJson('Answer summary entry', detail.answer_summary_entry)}
                      ${panelJson('Answer sources', detail.answer_sources)}
                      ${panelJson('Reconciliation', detail.reconciliation)}
                      ${panelJson('Answer detection', detail.answer_detection)}
                      ${panelJson('Rubric detection', detail.rubric_detection)}
                      ${panelJson('QA flags', detail.qa_flags)}
                      ${panelJson('Issue codes', detail.issue_codes)}
                      ${panelJson('Parser question', detail.parser_question)}
                      ${panelJson('Question item', detail.question_item)}
                      ${panelJson('Current override entry', detail.override_entry)}
                    </div>`;
                }

                function renderEditor(detail) {
                  const form = document.getElementById('reviewForm');
                  form.innerHTML = '';

                  const statusSelect = el('select', { id: 'reviewStatus' },
                    ['needs_review', 'reviewed_fixed', 'reviewed_confirmed', 'skipped', 'rejected_from_import', 'auto_accepted']
                      .map(v => `<option value="${v}" ${v === (detail.review_status || 'needs_review') ? 'selected' : ''}>${v}</option>`).join('')
                  );
                  const note = el('textarea', { id: 'reviewNote', placeholder: 'Review note / reason' }, detail.review_note || '');
                  const reviewer = el('input', { id: 'reviewer', value: detail.reviewer || 'user', placeholder: 'Reviewer' });

                  form.appendChild(field('Review status', statusSelect));
                  form.appendChild(field('Reviewed by', reviewer));
                  form.appendChild(field('Note', note));

                  const kind = editorKind(detail);
                  const answerPanel = el('div', { class: 'editor-kind' });
                  answerPanel.appendChild(el('h3', {}, `Answer editor: ${kind}`));
                  answerPanel.appendChild(el('p', { class: 'muted small' }, 'Clear answer leaves the item unresolved and blocks finalize.'));

                  if (kind === 'single_choice') {
                    answerPanel.appendChild(renderSingleChoiceEditor(detail));
                  } else if (kind === 'boolean_group') {
                    answerPanel.appendChild(renderBooleanEditor(detail));
                  } else if (kind === 'short_answer') {
                    answerPanel.appendChild(renderShortAnswerEditor(detail));
                  } else if (kind === 'rubric') {
                    answerPanel.appendChild(renderRubricEditor(detail));
                  } else {
                    answerPanel.appendChild(el('p', { class: 'muted' }, 'No supported answer/rubric edit controls for this question type.'));
                  }

                  form.appendChild(answerPanel);
                  wireMathEditors();
                }

                function renderSingleChoiceEditor(detail) {
                  const current = detail.question_item?.answer_key?.value || '';
                  const box = el('div', { class: 'stack' });
                  const group = document.createElement('div');
                  group.className = 'choice-group';
                  for (const choice of ['A','B','C','D']) {
                    const id = `choice-${choice}`;
                    const label = document.createElement('label');
                    label.className = 'choice-chip';
                    label.innerHTML = `<input type="radio" name="answerChoice" value="${choice}" ${current === choice ? 'checked' : ''} /> <span>${choice}</span>`;
                    group.appendChild(label);
                  }
                  const clearBtn = el('button', { type: 'button', class: 'btn btn-secondary' }, 'Clear answer');
                  clearBtn.addEventListener('click', () => {
                    group.querySelectorAll('input[type=radio]').forEach(r => r.checked = false);
                  });
                  box.appendChild(group);
                  box.appendChild(clearBtn);
                  return box;
                }

                function renderBooleanEditor(detail) {
                  const current = detail.question_item?.answer_key?.subanswers || {};
                  const wrap = el('div', { class: 'stack' });
                  const table = el('table', { class: 'review-table compact' });
                  table.innerHTML = `
                    <thead><tr><th>Label</th><th>Value</th></tr></thead>
                    <tbody>
                      ${['a','b','c','d'].map(label => `
                        <tr>
                          <td><strong>${label}</strong></td>
                          <td>
                            <select data-boolean-label="${label}">
                              <option value="">clear</option>
                              <option value="true" ${current[String(label)] === true ? 'selected' : ''}>true</option>
                              <option value="false" ${current[String(label)] === false ? 'selected' : ''}>false</option>
                            </select>
                          </td>
                        </tr>`).join('')}
                    </tbody>`;
                  wrap.appendChild(table);
                  return wrap;
                }

                function renderShortAnswerEditor(detail) {
                  const accepted = detail.question_item?.answer_key?.accepted_answers || [];
                  const wrap = el('div', { class: 'stack' });
                  const list = el('div', { id: 'shortAnswerRows', class: 'stack' });
                  if (!accepted.length) {
                    list.appendChild(shortAnswerRow({ raw: '', normalized: '' }));
                  } else {
                    accepted.forEach(answer => list.appendChild(shortAnswerRow(answer)));
                  }
                  const addBtn = el('button', { type: 'button', class: 'btn btn-secondary' }, 'Add accepted answer');
                  addBtn.addEventListener('click', () => list.appendChild(shortAnswerRow({ raw: '', normalized: '' })));
                  const clearBtn = el('button', { type: 'button', class: 'btn btn-secondary' }, 'Clear answers');
                  clearBtn.addEventListener('click', () => {
                    list.innerHTML = '';
                    list.appendChild(shortAnswerRow({ raw: '', normalized: '' }));
                  });
                  wrap.appendChild(list);
                  wrap.appendChild(el('div', { class: 'actions' }, [addBtn, clearBtn]));
                  return wrap;
                }

                function renderRubricEditor(detail) {
                  const rubric = detail.question_item?.rubric || {};
                  const wrap = el('div', { class: 'stack' });
                  const fieldset = el('div', { class: 'stack' });
                  fieldset.appendChild(field('Rubric text', editableMathText('rubricText', rubric.rubric_text || rubric.text || '', 'Rubric text (plain text or MathLive-friendly)')));
                  fieldset.appendChild(field('Rubric JSON', el('textarea', { id: 'rubricJson', class: 'mono', placeholder: 'Optional rubric JSON' }, JSON.stringify(rubric.blocks || [], null, 2))));
                  wrap.appendChild(fieldset);
                  return wrap;
                }

                function shortAnswerRow(answer) {
                  const row = el('div', { class: 'short-answer-row' });
                  row.innerHTML = `
                    <div class="math-editor">
                      <math-field class="math-field" data-role="raw" aria-label="Raw answer latex">${escapeHtml(answer.raw_input_latex || answer.raw || '')}</math-field>
                      <textarea class="plain-text" data-role="raw-text" placeholder="Raw answer">${escapeHtml(answer.raw || '')}</textarea>
                    </div>
                    <input class="normalized-input" data-role="normalized" placeholder="Normalized answer" value="${escapeHtml(answer.normalized || '')}" />
                    <button type="button" class="btn btn-secondary" data-role="remove">Remove</button>`;
                  row.querySelector('[data-role="remove"]').addEventListener('click', () => row.remove());
                  return row;
                }

                function editableMathText(id, value, placeholder) {
                  const wrap = el('div', { class: 'math-editor' });
                  const field = el('math-field', { id, class: 'math-field' }, value || '');
                  const plain = el('textarea', { id: `${id}Text`, class: 'plain-text', placeholder }, value || '');
                  wrap.appendChild(field);
                  wrap.appendChild(plain);
                  return wrap;
                }

                function editorKind(detail) {
                  const mode = detail.question_item?.answer_key?.mode || 'none';
                  const qType = detail.question_type || '';
                  if (mode === 'single_choice' || qType === 'single_choice') return 'single_choice';
                  if (mode === 'boolean_group' || qType === 'true_false') return 'boolean_group';
                  if (mode === 'short_answer' || qType === 'short_answer') return 'short_answer';
                  if (mode === 'rubric' || qType === 'essay') return 'rubric';
                  return 'none';
                }

                function wireMathEditors() {
                  document.querySelectorAll('.math-editor').forEach(container => {
                    const mathField = container.querySelector('math-field');
                    const textarea = container.querySelector('textarea');
                    if (!mathField || !textarea) return;
                    mathField.addEventListener('input', () => {
                      textarea.value = mathField.value || '';
                    });
                    textarea.addEventListener('input', () => {
                      mathField.value = textarea.value || '';
                    });
                  });
                }

                function collectEditPayload(detail) {
                  const kind = editorKind(detail);
                  const edits = {};
                  if (kind === 'single_choice') {
                    const selected = document.querySelector('input[name="answerChoice"]:checked');
                    edits.answer_key = selected ? { mode: 'single_choice', value: selected.value } : { mode: 'none' };
                  } else if (kind === 'boolean_group') {
                    const subanswers = {};
                    document.querySelectorAll('[data-boolean-label]').forEach(sel => {
                      const label = sel.getAttribute('data-boolean-label');
                      if (sel.value === 'true') subanswers[label] = true;
                      if (sel.value === 'false') subanswers[label] = false;
                    });
                    edits.boolean_subanswers = subanswers;
                    if (!Object.keys(subanswers).length) {
                      edits.answer_key = { mode: 'none' };
                    }
                  } else if (kind === 'short_answer') {
                    const answers = [];
                    document.querySelectorAll('#shortAnswerRows .short-answer-row').forEach(row => {
                      const rawField = row.querySelector('[data-role="raw"]');
                      const rawText = row.querySelector('[data-role="raw-text"]');
                      const normalized = row.querySelector('[data-role="normalized"]');
                      const raw = (rawField && rawField.value ? rawField.value : (rawText && rawText.value ? rawText.value : '')).trim();
                      const norm = (normalized && normalized.value ? normalized.value : raw).trim();
                      if (raw || norm) {
                        answers.push({ raw: raw, normalized: norm });
                      }
                    });
                    if (answers.length) {
                      edits.accepted_answers = answers;
                    } else {
                      edits.answer_key = { mode: 'none' };
                    }
                  } else if (kind === 'rubric') {
                    const rubricText = (document.getElementById('rubricTextText')?.value || document.getElementById('rubricText')?.value || '').trim();
                    const rubricJsonRaw = (document.getElementById('rubricJson')?.value || '[]').trim();
                    let blocks = [];
                    try {
                      blocks = rubricJsonRaw ? JSON.parse(rubricJsonRaw) : [];
                    } catch (err) {
                      blocks = [];
                    }
                    edits.rubric = { mode: 'rubric', rubric_text: rubricText, blocks };
                  }
                  return edits;
                }

                async function saveReview(goNext) {
                  if (!currentDetail) return;
                  const body = {
                    review_status: document.getElementById('reviewStatus').value,
                    review_note: document.getElementById('reviewNote').value,
                    reviewer: document.getElementById('reviewer').value,
                    edits: collectEditPayload(currentDetail)
                  };
                  const result = await apiPost(`/api/review/session/${encodeURIComponent(bundleId)}/question/${encodeURIComponent(questionId)}/save`, body);
                  const root = document.getElementById('saveStatus');
                  root.classList.remove('hidden');
                  root.innerHTML = `<pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
                  await load();
                  if (goNext && currentDetail && currentDetail.next_question_id) {
                    navigateSibling('next_question_id');
                  }
                }

                function navigateSibling(field) {
                  const target = currentDetail && currentDetail[field];
                  if (target) {
                    location.href = `/review/bundle/${encodeURIComponent(bundleId)}/question/${encodeURIComponent(target)}`;
                  }
                }

                function statusBadge(label, value, extraClass) {
                  const cls = extraClass || statusClass(value);
                  return `<span class="badge ${cls}">${escapeHtml(label)}: ${escapeHtml(value || 'none')}</span>`;
                }

                function summaryLine(label, value) {
                  return `<div class="summary-line"><span class="muted">${escapeHtml(label)}:</span> <strong>${escapeHtml(value || 'none')}</strong></div>`;
                }

                function chipList(label, values, inlineOnly) {
                  const items = Array.isArray(values) ? values.filter(Boolean) : [];
                  const chips = items.length
                    ? items.map(value => `<span class="badge badge-muted pill">${escapeHtml(String(value))}</span>`).join(' ')
                    : '<span class="muted">none</span>';
                  if (inlineOnly) {
                    return chips;
                  }
                  return `
                    <div class="chip-block">
                      ${label ? `<div class="panel-subtitle">${escapeHtml(label)}</div>` : ''}
                    <div class="chip-row">${chips}</div>
                  </div>`;
                }

                function formatNameList(values, count) {
                  const names = Array.isArray(values) ? values.filter(Boolean) : [];
                  if (!names.length) {
                    return count ? `${count} reviewer(s)` : 'unassigned';
                  }
                  if (names.length <= 2) {
                    return names.join(', ');
                  }
                  return `${names.slice(0, 2).join(', ')} +${names.length - 2}`;
                }

                load().catch(err => {
                  document.getElementById('detailStatus').textContent = `Failed to load question: ${err.message}`;
                });
                """.formatted(escapeJsString(bundleId), escapeJsString(questionId)));
    }

    private static String shell(String title, String body, String script) {
        return """
                <!doctype html>
                <html lang="vi">
                <head>
                  <meta charset="utf-8" />
                  <meta name="viewport" content="width=device-width, initial-scale=1" />
                  <title>%s</title>
                  <style>
                    :root {
                      color-scheme: light;
                      --bg: #f6f7fb;
                      --panel: #ffffff;
                      --panel-alt: #f1f4f8;
                      --text: #162033;
                      --muted: #5b677a;
                      --border: #d5ddea;
                      --accent: #2f6fed;
                      --accent-2: #0f9d58;
                      --danger: #c0392b;
                      --shadow: 0 10px 24px rgba(28, 39, 72, 0.08);
                    }
                    * { box-sizing: border-box; }
                    body {
                      margin: 0;
                      background: linear-gradient(180deg, #f6f7fb 0%%, #eef2f8 100%%);
                      color: var(--text);
                      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                    }
                    a { color: var(--accent); text-decoration: none; }
                    a:hover { text-decoration: underline; }
                    .page { max-width: 1600px; margin: 0 auto; padding: 24px; }
                    .hero {
                      display: flex;
                      justify-content: space-between;
                      align-items: flex-start;
                      gap: 16px;
                      margin-bottom: 16px;
                    }
                    .hero h1, h2, h3 { margin: 0 0 10px; }
                    .hero-actions, .actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
                    .panel {
                      background: var(--panel);
                      border: 1px solid var(--border);
                      border-radius: 14px;
                      box-shadow: var(--shadow);
                      padding: 16px;
                      margin-bottom: 16px;
                    }
                    .stack { display: grid; gap: 12px; }
                    .muted { color: var(--muted); }
                    .small { font-size: 12px; }
                    .statusline { margin: 8px 0 14px; }
                    .btn {
                      display: inline-flex;
                      align-items: center;
                      justify-content: center;
                      border: 1px solid var(--border);
                      background: #fff;
                      color: var(--text);
                      border-radius: 10px;
                      padding: 8px 12px;
                      font: inherit;
                      cursor: pointer;
                    }
                    .btn:hover { border-color: #b7c5df; text-decoration: none; }
                    .btn-primary { background: var(--accent); color: white; border-color: var(--accent); }
                    .btn-secondary { background: #fff; }
                    .badge {
                      display: inline-flex;
                      border-radius: 999px;
                      padding: 2px 8px;
                      border: 1px solid var(--border);
                      font-size: 12px;
                      white-space: nowrap;
                    }
                    .badge-good { background: #e8f7ef; border-color: #b9e7ca; color: #186b38; }
                    .badge-muted { background: #f3f5f7; }
                    .badge-warn { background: #fff4db; border-color: #f5d08a; color: #915f0e; }
                    .badge-bad { background: #fde8e7; border-color: #f0b6b1; color: #9c2a23; }
                    .badge-info { background: #e7f0ff; border-color: #b6ccff; color: #1d4ed8; }
                    .pill { border-radius: 999px; }
                    .review-table {
                      width: 100%%;
                      border-collapse: collapse;
                      font-size: 13px;
                    }
                    .review-table th, .review-table td {
                      border-top: 1px solid var(--border);
                      padding: 10px 8px;
                      text-align: left;
                      vertical-align: top;
                    }
                    .review-table thead th {
                      border-top: 0;
                      background: var(--panel-alt);
                      position: sticky;
                      top: 0;
                      z-index: 1;
                    }
                    .review-table tbody tr.row-problem { background: #fff7f6; }
                    .review-table tbody tr.row-secondary { background: #f7fbff; }
                    .review-table tbody tr.row-reviewed { background: #f7fcf8; }
                    .review-table tbody tr.row-selected { outline: 2px solid rgba(47, 111, 237, 0.35); background: #eef4ff; }
                    .selection-col {
                      width: 36px;
                      text-align: center;
                    }
                    .batch-actions {
                      display: flex;
                      flex-wrap: wrap;
                      gap: 8px;
                      align-items: center;
                    }
                    .review-table.compact th, .review-table.compact td { padding: 6px 8px; }
                    .cell-title { font-weight: 600; }
                    .summary-grid {
                      display: grid;
                      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                      gap: 12px;
                    }
                    .summary-card {
                      background: var(--panel-alt);
                      border-radius: 12px;
                      padding: 12px;
                      border: 1px solid var(--border);
                    }
                    .summary-card .label { color: var(--muted); font-size: 12px; }
                    .summary-card .value { font-size: 22px; font-weight: 700; margin-top: 4px; }
                    .summary-line { display: flex; gap: 8px; flex-wrap: wrap; align-items: baseline; }
                    .controls {
                      display: grid;
                      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                      gap: 12px;
                      align-items: end;
                    }
                    .controls label, .field label {
                      display: grid;
                      gap: 4px;
                      font-weight: 600;
                    }
                    .panel-header {
                      display: flex;
                      justify-content: space-between;
                      align-items: center;
                      gap: 12px;
                      margin-bottom: 10px;
                    }
                    input, select, textarea, math-field {
                      font: inherit;
                      border: 1px solid var(--border);
                      border-radius: 10px;
                      padding: 8px 10px;
                      background: #fff;
                      width: 100%%;
                    }
                    textarea { min-height: 88px; resize: vertical; }
                    .checkbox { display: flex !important; align-items: center; gap: 8px; }
                    .detail-grid {
                      display: grid;
                      grid-template-columns: minmax(0, 1.2fr) minmax(360px, 0.8fr);
                      gap: 16px;
                      align-items: start;
                    }
                    .review-workspace {
                      display: grid;
                      grid-template-columns: minmax(0, 1.15fr) minmax(420px, 0.85fr);
                      gap: 16px;
                      align-items: start;
                    }
                    .source-pane, .parsed-pane { min-width: 0; }
                    .source-frame {
                      width: 100%%;
                      min-height: 76vh;
                      border: 1px solid var(--border);
                      border-radius: 12px;
                      background: #fff;
                    }
                    .source-view-stack { display: grid; gap: 10px; }
                    .source-tab-btn.active { font-weight: 700; }
                    .question-list {
                      display: grid;
                      gap: 10px;
                      max-height: 36vh;
                      overflow: auto;
                      padding-right: 4px;
                    }
                    .question-card {
                      width: 100%%;
                      text-align: left;
                      border: 1px solid var(--border);
                      border-radius: 12px;
                      padding: 12px;
                      background: #fff;
                      cursor: pointer;
                    }
                    .question-card:hover {
                      border-color: #9fb8ea;
                      box-shadow: 0 6px 16px rgba(28, 39, 72, 0.06);
                    }
                    .question-card.selected {
                      border-color: var(--accent);
                      background: #eef4ff;
                    }
                    .question-card-top {
                      display: flex;
                      justify-content: space-between;
                      align-items: flex-start;
                      gap: 10px;
                      margin-bottom: 6px;
                    }
                    .panel-nested {
                      background: #fbfcfe;
                      border-style: dashed;
                      box-shadow: none;
                      margin-bottom: 0;
                    }
                    @media (max-width: 1100px) {
                      .detail-grid { grid-template-columns: 1fr; }
                      .review-workspace { grid-template-columns: 1fr; }
                      .source-frame { min-height: 46vh; }
                    }
                    .question-preview-box, .excerpt {
                      background: #fcfdff;
                      border: 1px solid var(--border);
                      border-radius: 12px;
                      padding: 12px;
                      white-space: pre-wrap;
                      word-break: break-word;
                    }
                    .question-preview { display: grid; gap: 10px; }
                    .excerpt { min-height: 96px; }
                    .panel-subtitle { margin: 12px 0 6px; font-weight: 600; color: var(--muted); }
                    .field { display: grid; gap: 4px; }
                    .editor-kind { padding-top: 6px; border-top: 1px dashed var(--border); }
                    .choice-group { display: flex; gap: 8px; flex-wrap: wrap; }
                    .choice-chip {
                      display: inline-flex;
                      align-items: center;
                      gap: 8px;
                      border: 1px solid var(--border);
                      border-radius: 12px;
                      padding: 8px 10px;
                      background: #fff;
                    }
                    .short-answer-row {
                      display: grid;
                      grid-template-columns: minmax(0, 1fr) 220px auto;
                      gap: 10px;
                      align-items: start;
                    }
                    .tag-row, .chip-row {
                      display: flex;
                      flex-wrap: wrap;
                      gap: 8px;
                      align-items: center;
                    }
                    .stack.tight { gap: 4px; }
                    .math-editor { display: grid; gap: 8px; }
                    .plain-text { min-height: 78px; }
                    .hidden { display: none !important; }
                    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
                  </style>
                </head>
                <body>
                  <div class="page">
                    %s
                  </div>
                  <script>
                    async function apiGet(path) {
                      const response = await fetch(path, { headers: { 'Accept': 'application/json' } });
                      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
                      return response.json();
                    }
                    async function apiPost(path, payload) {
                      const response = await fetch(path, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                        body: JSON.stringify(payload || {})
                      });
                      if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
                      return response.json();
                    }
                    function escapeHtml(value) {
                      return String(value ?? '')
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;')
                        .replace(/"/g, '&quot;')
                        .replace(/'/g, '&#39;');
                    }
                    function escapeJsString(value) {
                      return String(value ?? '').replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'");
                    }
                    function formatConfidence(value) {
                      const num = Number(value || 0);
                      if (!Number.isFinite(num)) return '0.00';
                      return num.toFixed(2);
                    }
                    function statusClass(status) {
                      const value = String(status || '').toLowerCase();
                      if (value.includes('fix') || value === 'resolved' || value === 'reviewed_confirmed' || value === 'reviewed_fixed' || value === 'auto_accepted') return 'badge-good';
                      if (value.includes('conflict') || value.includes('block') || value === 'rejected_from_import') return 'badge-bad';
                      if (value.includes('review') || value.includes('pending') || value === 'needs_review' || value === 'skipped') return 'badge-warn';
                      return 'badge-muted';
                    }
                    function panelJson(title, value) {
                      return `
                        <details>
                          <summary>${escapeHtml(title)}</summary>
                          <pre class="excerpt mono">${escapeHtml(JSON.stringify(value ?? {}, null, 2))}</pre>
                        </details>`;
                    }
                    function field(label, control) {
                      const wrap = document.createElement('div');
                      wrap.className = 'field';
                      const lab = document.createElement('label');
                      lab.textContent = label;
                      wrap.appendChild(lab);
                      wrap.appendChild(control);
                      return wrap;
                    }
                    function el(tag, attrs, textOrChildren) {
                      const node = document.createElement(tag);
                      if (attrs) {
                        for (const [key, value] of Object.entries(attrs)) {
                          if (value == null) continue;
                          if (key === 'class') {
                            node.className = value;
                          } else if (key === 'id') {
                            node.id = value;
                          } else if (key === 'type') {
                            node.type = value;
                          } else if (key === 'placeholder') {
                            node.placeholder = value;
                          } else if (key === 'value') {
                            node.value = value;
                          } else {
                            node.setAttribute(key, value);
                          }
                        }
                      }
                      if (Array.isArray(textOrChildren)) {
                        textOrChildren.forEach(child => node.appendChild(child));
                      } else if (typeof textOrChildren === 'string') {
                        node.textContent = textOrChildren;
                      } else if (textOrChildren instanceof Node) {
                        node.appendChild(textOrChildren);
                      } else if (textOrChildren != null) {
                        node.textContent = String(textOrChildren);
                      }
                      return node;
                    }
                    function debounce(fn, delay) {
                      let handle;
                      return (...args) => {
                        clearTimeout(handle);
                        handle = setTimeout(() => fn(...args), delay);
                      };
                    }
                  </script>
                  <script>%s</script>
                </body>
                </html>
                """.formatted(escapeHtml(title), body, script);
    }
}
