let pollingInterval = null;

// Preset sample datasets
const PRESETS = {
  standard: [
    { name: "Sophia Taylor", email: "sophia.t@example.com", custom_attributes: { grade: "Distinction", track: "Backend Systems" } },
    { name: "Liam Anderson", email: "liam.a@example.com", custom_attributes: { grade: "Merit", track: "Full Stack" } },
    { name: "Emma Watson", email: "emma.w@example.com", custom_attributes: { grade: "Honors", track: "Cloud Architecture" } },
    { name: "Noah Miller", email: "noah.m@example.com", custom_attributes: { grade: "A+", track: "Distributed Systems" } },
    { name: "Olivia Davis", email: "olivia.d@example.com", custom_attributes: { grade: "Distinction", track: "DevOps" } }
  ],
  large: Array.from({ length: 15 }, (_, i) => ({
    name: `Participant ${i + 1}`,
    email: `student${i + 1}@university.edu`,
    custom_attributes: { batch: "Cohort-2026", score: `${85 + (i % 15)}%` }
  })),
  fault: [
    { name: "Valid Recipient One", email: "valid1@example.com", custom_attributes: { status: "Honors" } },
    { name: "Valid Recipient Two", email: "valid2@example.com", custom_attributes: { status: "Pass" } },
    { name: "Faulty Recipient (Simulated Error)", email: "fail.user@example.com", custom_attributes: { _fail_generate: true, note: "Will fail generation gracefully" } },
    { name: "Valid Recipient Three", email: "valid3@example.com", custom_attributes: { status: "Distinction" } }
  ]
};

document.addEventListener("DOMContentLoaded", () => {
  // Set default issue date to today
  document.getElementById("issue_date").valueAsDate = new Date();
  loadSamplePreset("standard");
  loadJobs();

  // Poll for updates every 2.5 seconds
  pollingInterval = setInterval(loadJobs, 2500);
});

function loadSamplePreset(type) {
  const data = PRESETS[type];
  if (!data) return;

  if (!document.getElementById("title").value) {
    document.getElementById("title").value = "Advanced Python Engineering Masterclass";
  }
  if (!document.getElementById("issuer_name").value) {
    document.getElementById("issuer_name").value = "Global Academy of Technology";
  }

  document.getElementById("recipients_json").value = JSON.stringify(data, null, 2);
}

function resetForm() {
  document.getElementById("job-form").reset();
  document.getElementById("issue_date").valueAsDate = new Date();
  document.getElementById("recipients_json").value = "";
}

function showAlert(msg, isError = false) {
  const alertBox = document.getElementById("alert-box");
  alertBox.innerHTML = `
    <div class="alert ${isError ? "alert-danger" : "alert-success"}">
      <span>${msg}</span>
      <button style="background:none;border:none;cursor:pointer;" onclick="this.parentElement.remove()">&times;</button>
    </div>
  `;
}

async function handleJobSubmit(e) {
  e.preventDefault();
  const submitBtn = document.getElementById("submit-btn");
  submitBtn.disabled = true;
  submitBtn.innerText = "⏳ Processing Job...";

  try {
    const title = document.getElementById("title").value.trim();
    const issuer_name = document.getElementById("issuer_name").value.trim();
    const issue_date = document.getElementById("issue_date").value;
    const description = document.getElementById("description").value.trim() || undefined;
    const mode = document.getElementById("processing_mode").value;

    let recipients;
    try {
      recipients = JSON.parse(document.getElementById("recipients_json").value);
      if (!Array.isArray(recipients) || recipients.length === 0) {
        throw new Error("Recipients must be a non-empty array of objects.");
      }
    } catch (parseErr) {
      throw new Error("Invalid JSON in recipients array: " + parseErr.message);
    }

    const payload = {
      title,
      issuer_name,
      issue_date: issue_date || undefined,
      description,
      recipients
    };

    const isSync = mode === "sync";
    const res = await fetch(`/api/v1/jobs?sync=${isSync}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();

    if (!res.ok) {
      const errDetail = Array.isArray(data.detail)
        ? data.detail.map(d => `${d.loc?.join(".")}: ${d.msg}`).join(", ")
        : (data.detail || "Submission failed");
      throw new Error(errDetail);
    }

    showAlert(`Success! Job "${data.job_id.slice(0, 8)}..." queued with ${data.total_count} recipients.`);
    loadJobs();
  } catch (err) {
    showAlert(err.message, true);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerText = "🚀 Submit Bulk Generation Job";
  }
}

async function loadJobs() {
  try {
    const res = await fetch("/api/v1/jobs");
    if (!res.ok) return;
    const jobs = await res.json();

    updateSummaryStats(jobs);

    const tbody = document.getElementById("jobs-table-body");
    if (jobs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No generation jobs submitted yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = jobs.map(j => {
      const isRunning = j.status === "processing" || j.status === "pending";
      const badgeClass = `badge-${j.status}`;
      const createdDate = j.created_at ? new Date(j.created_at).toLocaleTimeString() : "-";

      return `
        <tr>
          <td>
            <strong>${escapeHtml(j.title)}</strong><br>
            <span style="font-family: monospace; font-size: 0.75rem; color: var(--text-muted);">${j.id.slice(0, 8)}...</span>
          </td>
          <td>${escapeHtml(j.issuer_name)}</td>
          <td>
            <span class="badge ${badgeClass} ${isRunning ? "pulse" : ""}">
              ${escapeHtml(j.status.replace("_", " "))}
            </span>
          </td>
          <td style="min-width: 130px;">
            <div style="font-size: 0.75rem; display: flex; justify-content: space-between; margin-bottom: 2px;">
              <span>${j.progress_percent}%</span>
              <span>${j.success_count}/${j.total_count}</span>
            </div>
            <div class="progress-container">
              <div class="progress-bar" style="width: ${j.progress_percent}%"></div>
            </div>
          </td>
          <td>
            <span style="color: var(--success); font-weight:600;">✓ ${j.success_count}</span>
            ${j.failed_count > 0 ? `<span style="color: var(--danger); font-weight:600; margin-left: 6px;">✕ ${j.failed_count}</span>` : ""}
          </td>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${createdDate}</td>
          <td>
            <div style="display: flex; gap: 0.4rem;">
              <button class="btn-secondary" style="padding: 0.35rem 0.65rem;" onclick="viewJobDetails('${j.id}')">View</button>
              ${j.success_count > 0 ? `
                <a href="/api/v1/jobs/${j.id}/download" class="btn-success" title="Download all as ZIP">
                  📦 ZIP
                </a>
              ` : ""}
            </div>
          </td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    console.error("Error loading jobs:", err);
  }
}

function updateSummaryStats(jobs) {
  document.getElementById("stat-total-jobs").innerText = jobs.length;
  const totalCerts = jobs.reduce((sum, j) => sum + (j.success_count + j.failed_count), 0);
  const successCerts = jobs.reduce((sum, j) => sum + j.success_count, 0);

  document.getElementById("stat-total-certs").innerText = totalCerts;
  if (totalCerts > 0) {
    const rate = Math.round((successCerts / totalCerts) * 100);
    document.getElementById("stat-success-rate").innerText = `${rate}%`;
  } else {
    document.getElementById("stat-success-rate").innerText = "100%";
  }
}

async function viewJobDetails(jobId) {
  try {
    const res = await fetch(`/api/v1/jobs/${jobId}`);
    if (!res.ok) {
      alert("Failed to load job details.");
      return;
    }
    const job = await res.json();

    document.getElementById("modal-title").innerText = `Job: ${job.title}`;
    document.getElementById("modal-meta").innerHTML = `
      <div style="background: #f8fafc; padding: 0.85rem; border-radius: 8px; font-size: 0.85rem; display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem;">
        <div><strong>Status:</strong> <span class="badge badge-${job.status}">${job.status}</span></div>
        <div><strong>Issuer:</strong> ${escapeHtml(job.issuer_name)}</div>
        <div><strong>Date:</strong> ${escapeHtml(job.issue_date)}</div>
        <div><strong>Total / Success / Failed:</strong> ${job.total_count} / ${job.success_count} / ${job.failed_count}</div>
      </div>
    `;

    const zipLink = document.getElementById("modal-zip-link");
    if (job.success_count > 0) {
      zipLink.style.display = "inline-flex";
      zipLink.href = `/api/v1/jobs/${job.id}/download`;
    } else {
      zipLink.style.display = "none";
    }

    const tbody = document.getElementById("modal-cert-table-body");
    tbody.innerHTML = (job.certificates || []).map(c => `
      <tr>
        <td><strong>${escapeHtml(c.recipient_name)}</strong></td>
        <td>${escapeHtml(c.recipient_email)}</td>
        <td><span class="badge badge-${c.status}">${c.status}</span></td>
        <td><code>${escapeHtml(c.certificate_code)}</code></td>
        <td style="font-size: 0.8rem; color: ${c.status === 'failed' ? 'var(--danger)' : 'var(--text-muted)'};">
          ${c.error_message ? escapeHtml(c.error_message) : formatAttributes(c.custom_attributes)}
        </td>
        <td>
          ${c.download_url ? `
            <a href="${c.download_url}" target="_blank" class="btn-success" style="font-size: 0.75rem;">
              📄 PDF
            </a>
          ` : `<span style="color: var(--text-muted); font-size: 0.75rem;">N/A</span>`}
        </td>
      </tr>
    `).join("");

    document.getElementById("detail-modal").classList.add("active");
  } catch (err) {
    alert("Error fetching job details: " + err.message);
  }
}

function formatAttributes(attrs) {
  if (!attrs || Object.keys(attrs).length === 0) return "-";
  return Object.entries(attrs)
    .filter(([k]) => !k.startsWith("_"))
    .map(([k, v]) => `${k}: ${v}`)
    .join(", ");
}

function closeModal(id) {
  document.getElementById(id).classList.remove("active");
}

function openVerifyModal() {
  document.getElementById("verify-code-input").value = "";
  document.getElementById("verify-result").innerHTML = "";
  document.getElementById("verify-modal").classList.add("active");
}

async function performVerification() {
  const code = document.getElementById("verify-code-input").value.trim();
  const resultDiv = document.getElementById("verify-result");
  if (!code) {
    resultDiv.innerHTML = `<div class="alert alert-danger">Please enter a certificate code.</div>`;
    return;
  }

  resultDiv.innerHTML = `<div style="text-align: center;">Verifying code...</div>`;

  try {
    const res = await fetch(`/api/v1/certificates/verify/${encodeURIComponent(code)}`);
    const data = await res.json();

    if (data.valid) {
      resultDiv.innerHTML = `
        <div class="alert alert-success" style="flex-direction: column; align-items: flex-start; gap: 0.5rem;">
          <div style="font-weight: 700; font-size: 1rem;">✓ Authentic Certificate Verified</div>
          <div style="font-size: 0.85rem; line-height: 1.6;">
            <strong>Recipient:</strong> ${escapeHtml(data.recipient_name)}<br>
            <strong>Program:</strong> ${escapeHtml(data.title)}<br>
            <strong>Issuer:</strong> ${escapeHtml(data.issuer_name)}<br>
            <strong>Issue Date:</strong> ${escapeHtml(data.issue_date)}<br>
            <strong>Verification Code:</strong> <code>${escapeHtml(data.certificate_code)}</code>
          </div>
        </div>
      `;
    } else {
      resultDiv.innerHTML = `
        <div class="alert alert-danger" style="flex-direction: column; align-items: flex-start; gap: 0.5rem;">
          <div style="font-weight: 700;">✕ Verification Failed</div>
          <div style="font-size: 0.85rem;">${escapeHtml(data.message)}</div>
        </div>
      `;
    }
  } catch (err) {
    resultDiv.innerHTML = `<div class="alert alert-danger">Network error verifying credential: ${err.message}</div>`;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
