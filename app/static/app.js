const runtimeStatus = document.getElementById('runtimeStatus');
const resultMode = document.getElementById('resultMode');
const resultContainer = document.getElementById('resultContainer');
const errorBox = document.getElementById('errorBox');
const loadingBox = document.getElementById('loadingBox');
const submitText = document.getElementById('submitText');
const submitFile = document.getElementById('submitFile');

async function loadHealth() {
  try {
    const response = await fetch('/health');
    const health = await response.json();
    runtimeStatus.textContent = `LLM: ${health.llm_configured ? '已配置' : '未配置'} | 知识库: ${health.knowledge_base_ready ? '已就绪' : '未就绪'}`;
  } catch (error) {
    runtimeStatus.textContent = '运行状态获取失败，请检查服务是否正常启动。';
  }
}

function setLoading(isLoading, modeLabel) {
  loadingBox.classList.toggle('hidden', !isLoading);
  submitText.disabled = isLoading;
  submitFile.disabled = isLoading;
  if (modeLabel) {
    resultMode.textContent = modeLabel;
  }
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.remove('hidden');
}

function clearError() {
  errorBox.textContent = '';
  errorBox.classList.add('hidden');
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderResult(payload) {
  const summary = payload.summary || {};
  const fields = payload.extracted_fields || {};
  const report = payload.report || {};
  const risks = payload.risks || [];

  const summaryHtml = `
    <div class="summary-grid">
      <article class="metric"><strong>合同类型</strong><span>${escapeHtml(summary.contract_type || '-')}</span></article>
      <article class="metric"><strong>整体风险</strong><span>${escapeHtml(summary.overall_risk || '-')}</span></article>
      <article class="metric"><strong>风险数量</strong><span>${escapeHtml(summary.risk_count ?? 0)}</span></article>
    </div>
  `;

  const fieldsHtml = `
    <div class="fields-grid">
      <article class="field-card"><strong>合同名称</strong><span>${escapeHtml(fields.contract_name || '-')}</span></article>
      <article class="field-card"><strong>甲方</strong><span>${escapeHtml(fields.party_a || '-')}</span></article>
      <article class="field-card"><strong>乙方</strong><span>${escapeHtml(fields.party_b || '-')}</span></article>
      <article class="field-card"><strong>金额</strong><span>${escapeHtml(fields.amount || '-')}</span></article>
      <article class="field-card"><strong>争议条款</strong><span>${escapeHtml(fields.dispute_clause || '-')}</span></article>
      <article class="field-card"><strong>生成时间</strong><span>${escapeHtml(report.generated_at || '-')}</span></article>
    </div>
  `;

  const reportHtml = `
    <article class="report-card">
      <strong>报告摘要</strong>
      <p>${escapeHtml(report.overview || '-')}</p>
      <strong>关键发现</strong>
      <ul class="basis-list">${(report.key_findings || []).map(item => `<li>${escapeHtml(item)}</li>`).join('') || '<li>-</li>'}</ul>
      <strong>建议动作</strong>
      <ul class="basis-list">${(report.next_actions || []).map(item => `<li>${escapeHtml(item)}</li>`).join('') || '<li>-</li>'}</ul>
    </article>
  `;

  const risksHtml = risks.length
    ? `<div class="risk-list">${risks.map((risk) => {
        const basisItems = (risk.basis_sources || []).map((source) => {
          const title = source.article_label ? `${source.source_title} ${source.article_label}` : source.source_title;
          return `<li><strong>${escapeHtml(title)}</strong><br>${escapeHtml(source.snippet)}${source.source_path ? `<br><small>${escapeHtml(source.source_path)}</small>` : ''}</li>`;
        }).join('');

        return `
          <article class="risk-card">
            <div class="risk-meta">
              <span>规则: ${escapeHtml(risk.rule_id)}</span>
              <span>等级: ${escapeHtml(risk.severity)}</span>
              <span>位置: ${escapeHtml(risk.clause_no || risk.section_title || '未定位')}</span>
            </div>
            <h3>${escapeHtml(risk.title)}</h3>
            <p><strong>风险说明：</strong>${escapeHtml(risk.description)}</p>
            <p><strong>命中证据：</strong>${escapeHtml(risk.evidence)}</p>
            <p><strong>LLM解释：</strong>${escapeHtml(risk.ai_explanation || '-')}</p>
            <p><strong>修改建议：</strong>${escapeHtml(risk.suggestion)}</p>
            <strong>依据来源</strong>
            <ul class="basis-list">${basisItems || '<li>-</li>'}</ul>
          </article>
        `;
      }).join('')}</div>`
    : '<p>本次未识别出明确风险。</p>';

  resultContainer.classList.remove('empty');
  resultContainer.innerHTML = `${summaryHtml}${fieldsHtml}${reportHtml}<h3>风险清单</h3>${risksHtml}`;
}

async function submitTextReview() {
  clearError();
  setLoading(true, '文本校审中');
  try {
    const response = await fetch('/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contract_text: document.getElementById('contractText').value,
        contract_type: document.getElementById('textContractType').value || null,
        our_side: document.getElementById('textOurSide').value,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || '文本校审失败');
    }
    renderResult(payload);
  } catch (error) {
    showError(error.message || '文本校审失败');
  } finally {
    setLoading(false, '文本模式');
  }
}

async function submitFileReview() {
  clearError();
  const fileInput = document.getElementById('contractFile');
  if (!fileInput.files.length) {
    showError('请先选择要上传的合同文件。');
    return;
  }

  setLoading(true, '文件校审中');
  try {
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('our_side', document.getElementById('fileOurSide').value);
    if (document.getElementById('fileContractType').value) {
      formData.append('contract_type', document.getElementById('fileContractType').value);
    }

    const response = await fetch('/review/file', {
      method: 'POST',
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || '文件校审失败');
    }
    renderResult(payload);
  } catch (error) {
    showError(error.message || '文件校审失败');
  } finally {
    setLoading(false, '文件模式');
  }
}

submitText.addEventListener('click', submitTextReview);
submitFile.addEventListener('click', submitFileReview);
loadHealth();
