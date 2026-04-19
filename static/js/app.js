const MODULE_NAMES = {
    overall_evaluation: "整体评价",
    job_analysis: "岗位分析",
    high_freq_categories: "高频考点分类解析",
    high_freq_list: "高频考点清单",
    project_deep_dive: "项目深挖",
    behavioral_prep: "行为面试准备",
    on_site_strategies: "临场应对策略",
    recommended_resources: "推荐复习资料",
};

let currentReportId = null;
let resumeFilePath = null;
let jdFilePath = null;

document.addEventListener("DOMContentLoaded", () => {
    initJDTypeSwitch();
    initFileUploads();
    initFormSubmit();
    initNavigation();
    loadHistory();
});

function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            }
        });
    });

    const sections = document.querySelectorAll('section[id]');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const id = entry.target.getAttribute('id');
                navLinks.forEach(link => {
                    link.classList.toggle('active', link.getAttribute('href') === `#${id}`);
                });
            }
        });
    }, { threshold: 0.3 });

    sections.forEach(section => observer.observe(section));
}

function initJDTypeSwitch() {
    const radios = document.querySelectorAll('input[name="jd-type"]');
    const textContainer = document.getElementById("jd-text-container");
    const imageContainer = document.getElementById("jd-image-container");

    radios.forEach((radio) => {
        radio.addEventListener("change", () => {
            textContainer.classList.toggle("hidden", radio.value !== "text");
            imageContainer.classList.toggle("hidden", radio.value !== "image");
        });
    });
}

function initFileUploads() {
    const jdArea = document.getElementById("jd-upload-area");
    const jdInput = document.getElementById("jd-file");
    const resumeArea = document.getElementById("resume-upload-area");
    const resumeInput = document.getElementById("resume-input");

    jdArea.addEventListener("click", () => jdInput.click());
    jdInput.addEventListener("change", (e) => handleFileUpload(e, "jd"));

    resumeArea.addEventListener("click", () => resumeInput.click());
    resumeInput.addEventListener("change", (e) => handleFileUpload(e, "resume"));

    jdArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        jdArea.style.borderColor = "var(--primary)";
    });
    jdArea.addEventListener("dragleave", () => {
        jdArea.style.borderColor = "";
    });
    jdArea.addEventListener("drop", (e) => {
        e.preventDefault();
        jdArea.style.borderColor = "";
        handleFileDrop(e.dataTransfer.files, "jd");
    });

    resumeArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        resumeArea.style.borderColor = "var(--primary)";
    });
    resumeArea.addEventListener("dragleave", () => {
        resumeArea.style.borderColor = "";
    });
    resumeArea.addEventListener("drop", (e) => {
        e.preventDefault();
        resumeArea.style.borderColor = "";
        handleFileDrop(e.dataTransfer.files, "resume");
    });

    document.getElementById("remove-jd").addEventListener("click", (e) => {
        e.stopPropagation();
        resetUpload("jd");
    });
    document.getElementById("remove-resume").addEventListener("click", (e) => {
        e.stopPropagation();
        resetUpload("resume");
    });
}

function handleFileUpload(e, type) {
    const file = e.target.files[0];
    if (file) uploadFile(file, type);
}

function handleFileDrop(files, type) {
    const file = files[0];
    if (file) uploadFile(file, type);
}

async function uploadFile(file, type) {
    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.error, "error");
            return;
        }

        const data = await response.json();

        if (type === "jd") {
            jdFilePath = data.filepath;
            const preview = document.getElementById("jd-preview");
            preview.src = URL.createObjectURL(file);
            showPreview("jd", file.name);
        } else {
            resumeFilePath = data.filepath;
            document.getElementById("resume-filename").textContent = file.name;
            showPreview("resume", file.name);
        }

        showToast("文件上传成功", "success");
    } catch (error) {
        showToast("上传失败: " + error.message, "error");
    }
}

function showPreview(type, filename) {
    const area = document.getElementById(`${type}-upload-area`);
    area.querySelector(".upload-placeholder").classList.add("hidden");
    area.querySelector(".upload-preview").classList.remove("hidden");
}

function resetUpload(type) {
    const area = document.getElementById(`${type}-upload-area`);
    area.querySelector(".upload-placeholder").classList.remove("hidden");
    area.querySelector(".upload-preview").classList.add("hidden");

    if (type === "jd") {
        jdFilePath = null;
        document.getElementById("jd-file").value = "";
    } else {
        resumeFilePath = null;
        document.getElementById("resume-input").value = "";
    }
}

function initFormSubmit() {
    document.getElementById("generate-form").addEventListener("submit", async (e) => {
        e.preventDefault();

        const positionName = document.getElementById("position-name").value.trim();
        if (!positionName) {
            showToast("请输入岗位名称", "warning");
            return;
        }

        if (!resumeFilePath) {
            showToast("请上传简历PDF", "warning");
            return;
        }

        const jdType = document.querySelector('input[name="jd-type"]:checked').value;
        let jdContent = "";

        if (jdType === "text") {
            jdContent = document.getElementById("jd-text").value.trim();
        } else if (jdType === "image") {
            jdContent = jdFilePath;
        }

        const count = parseInt(document.getElementById("crawl-count").value) || 10;

        startGeneration(positionName, jdType, jdContent, count);
    });
}

async function startGeneration(positionName, jdType, jdContent, count) {
    const btn = document.getElementById("generate-btn");
    btn.disabled = true;
    btn.innerHTML = "生成中...";

    document.getElementById("progress-section").classList.remove("hidden");
    document.getElementById("report-section").classList.add("hidden");
    updateProgress(0, "准备开始...");

    try {
        const response = await fetch("/api/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                position_name: positionName,
                jd_type: jdType,
                jd_content: jdContent,
                resume_path: resumeFilePath,
                count: count,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.error, "error");
            resetButton();
            return;
        }

        const data = await response.json();
        pollTaskStatus(data.task_id);
    } catch (error) {
        showToast("请求失败: " + error.message, "error");
        resetButton();
    }
}

function pollTaskStatus(taskId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`/api/task/${taskId}`);
            const data = await response.json();

            updateProgressByStep(data.step);

            if (data.status === "completed") {
                clearInterval(interval);
                currentReportId = data.report_id;
                loadReport(data.report_id);
                showToast("报告生成成功！", "success");
                resetButton();
            } else if (data.status === "failed") {
                clearInterval(interval);
                showToast("生成失败: " + data.error, "error");
                resetButton();
            }
        } catch (error) {
            console.error("Poll error:", error);
        }
    }, 2000);
}

function updateProgress(percent, text) {
    document.getElementById("progress-fill").style.width = `${percent}%`;
    document.getElementById("progress-text").textContent = text;
}

function updateProgressByStep(stepText) {
    const steps = document.querySelectorAll(".step");
    const stepMap = {
        "解析输入信息": 1,
        "抓取面经数据": 2,
        "生成报告模块": 3,
        "保存报告": 4,
        "完成": 4,
    };

    const currentStep = stepMap[stepText] || 0;
    const percent = Math.min((currentStep / 4) * 100, 100);

    steps.forEach((step, index) => {
        const stepNum = index + 1;
        step.classList.remove("active", "completed");
        if (stepNum < currentStep) {
            step.classList.add("completed");
        } else if (stepNum === currentStep) {
            step.classList.add("active");
        }
    });

    updateProgress(percent, stepText || "处理中...");
}

function resetButton() {
    const btn = document.getElementById("generate-btn");
    btn.disabled = false;
    btn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
        </svg>
        <span>开始生成报告</span>
    `;
}

async function loadReport(reportId) {
    try {
        const response = await fetch(`/api/report/${reportId}`);
        const report = await response.json();

        document.getElementById("report-section").classList.remove("hidden");
        renderTabs();
        renderModule("all", report);

        document.getElementById("report-section").scrollIntoView({ behavior: "smooth" });
        loadHistory();
    } catch (error) {
        showToast("加载报告失败: " + error.message, "error");
    }
}

function renderTabs() {
    const tabsContainer = document.getElementById("module-tabs");
    tabsContainer.innerHTML = '<button class="tab-btn active" data-module="all">全部</button>';

    Object.entries(MODULE_NAMES).forEach(([key, name]) => {
        const btn = document.createElement("button");
        btn.className = "tab-btn";
        btn.dataset.module = key;
        btn.textContent = name;
        tabsContainer.appendChild(btn);
    });

    tabsContainer.querySelectorAll(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            tabsContainer.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            loadModuleContent(btn.dataset.module);
        });
    });
}

async function loadModuleContent(moduleKey) {
    if (!currentReportId) return;

    try {
        const response = await fetch(`/api/report/${currentReportId}`);
        const report = await response.json();
        renderModule(moduleKey, report);
    } catch (error) {
        showToast("加载模块失败", "error");
    }
}

function renderModule(moduleKey, report) {
    const container = document.getElementById("module-content");
    const modules = report.modules || {};

    if (moduleKey === "all") {
        let html = '<div class="report-modules">';
        Object.entries(MODULE_NAMES).forEach(([key, name]) => {
            if (modules[key]) {
                html += renderModuleCard(key, name, modules[key]);
            }
        });
        html += '</div>';
        container.innerHTML = html;
        initModuleCollapse();
    } else if (modules[moduleKey]) {
        container.innerHTML = renderModuleCard(moduleKey, MODULE_NAMES[moduleKey], modules[moduleKey], true);
        initModuleCollapse();
    } else {
        container.innerHTML = '<p class="empty-text">该模块暂无内容</p>';
    }
}

function initModuleCollapse() {
    document.querySelectorAll('.module-card-header').forEach(header => {
        header.addEventListener('click', () => {
            const card = header.closest('.module-card');
            card.classList.toggle('collapsed');
        });
    });
}

function renderModuleCard(key, name, data, isSingle = false) {
    const icons = {
        overall_evaluation: "📊",
        job_analysis: "💼",
        high_freq_categories: "📚",
        high_freq_list: "📝",
        project_deep_dive: "🔍",
        behavioral_prep: "🤝",
        on_site_strategies: "⚡",
        recommended_resources: "📖",
    };

    const icon = icons[key] || "📄";

    return `
        <div class="module-card ${isSingle ? 'single' : ''}" data-module="${key}">
            <div class="module-card-header">
                <span class="module-icon">${icon}</span>
                <h3>${name}</h3>
            </div>
            <div class="module-card-body">
                ${renderModuleContent(data)}
            </div>
        </div>
    `;
}

function renderModuleContent(data, depth = 0) {
    if (typeof data === "string") {
        return `<p class="content-text">${data}</p>`;
    }

    if (Array.isArray(data)) {
        if (data.length === 0) return '<p class="empty-text">暂无内容</p>';

        const firstItem = data[0];
        if (typeof firstItem === "object" && firstItem !== null) {
            let html = '<div class="item-list">';
            data.forEach((item, index) => {
                html += `<div class="item-card">`;
                const ordered = {};
                const priorityKeys = ["question", "project_name", "tech", "category", "scenario"];
                priorityKeys.forEach(pk => {
                    if (item[pk] !== undefined) ordered[pk] = item[pk];
                });
                Object.entries(item).forEach(([k, v]) => {
                    if (!ordered.hasOwnProperty(k)) ordered[k] = v;
                });
                Object.entries(ordered).forEach(([key, value]) => {
                    const label = formatLabel(key);
                    if (key === "question" || key === "project_name") {
                        html += `<div class="item-field item-field-title"><span class="field-label">${index + 1}. ${label}</span><span class="field-value">${value}</span></div>`;
                    } else if (typeof value === "string") {
                        html += `<div class="item-field"><span class="field-label">${label}</span><span class="field-value">${value}</span></div>`;
                    } else if (Array.isArray(value)) {
                        if (value.length > 0 && typeof value[0] === "object") {
                            html += `<div class="item-field"><span class="field-label">${label}</span><div class="field-value">${renderModuleContent(value, depth + 1)}</div></div>`;
                        } else {
                            html += `<div class="item-field"><span class="field-label">${label}</span><div class="field-value">${value.map(v => `<span class="tag">${v}</span>`).join('')}</div></div>`;
                        }
                    } else if (typeof value === "object" && value !== null) {
                        html += `<div class="item-field"><span class="field-label">${label}</span><div class="field-value">${renderModuleContent(value, depth + 1)}</div></div>`;
                    } else if (value !== undefined && value !== null) {
                        html += `<div class="item-field"><span class="field-label">${label}</span><span class="field-value">${value}</span></div>`;
                    }
                });
                html += `</div>`;
            });
            html += '</div>';
            return html;
        } else {
            return `<ul class="simple-list">${data.map((item, index) => `<li>${index + 1}. ${item}</li>`).join("")}</ul>`;
        }
    }

    if (typeof data === "object" && data !== null) {
        let html = '<div class="content-sections">';
        const sortedEntries = Object.entries(data).sort((a, b) => {
            const priorityKeys = ["question", "questions", "predicted_questions", "possible_questions"];
            const aIdx = priorityKeys.indexOf(a[0]);
            const bIdx = priorityKeys.indexOf(b[0]);
            if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx;
            if (aIdx !== -1) return -1;
            if (bIdx !== -1) return 1;
            return 0;
        });
        sortedEntries.forEach(([key, value]) => {
            if (key === "title") return;

            const label = formatLabel(key);

            if (typeof value === "string") {
                html += `<div class="content-block"><h4>${label}</h4><p>${value}</p></div>`;
            } else if (Array.isArray(value)) {
                if (value.length > 0 && typeof value[0] === "object") {
                    html += `<div class="content-block"><h4>${label}</h4>${renderModuleContent(value, depth + 1)}</div>`;
                } else {
                    html += `<div class="content-block"><h4>${label}</h4><ul class="simple-list">${value.map((item, index) => `<li>${index + 1}. ${item}</li>`).join("")}</ul></div>`;
                }
            } else if (typeof value === "object" && value !== null) {
                html += `<div class="content-block"><h4>${label}</h4>${renderModuleContent(value, depth + 1)}</div>`;
            } else if (value !== undefined && value !== null) {
                html += `<div class="content-block"><h4>${label}</h4><p>${value}</p></div>`;
            }
        });
        html += '</div>';
        return html;
    }

    return `<p class="content-text">${data}</p>`;
}

function formatLabel(key) {
    const labelMap = {
        title: "标题",
        summary: "总结",
        suggestions: "建议",
        skills: "技能要求",
        questions: "问题",
        project_name: "项目名称",
        tech_deep_dive: "技术深挖",
        predicted_questions: "预测问题",
        question: "问题",
        depth: "深度",
        preparation_tips: "准备建议",
        tech: "技术点",
        possible_questions: "可能的问题",
        books: "推荐书籍",
        courses: "推荐课程",
        websites: "推荐网站",
        interview_exps: "面经链接",
        match_score: "匹配度",
        strengths: "优势",
        weaknesses: "不足",
        core_requirements: "核心要求",
        tech_stack: "技术栈",
        soft_skills: "软技能",
        categories: "分类",
        category: "类别",
        description: "描述",
        strategy: "策略",
        key_points: "要点",
        answer_points: "答题要点",
        example_answer: "示例回答",
        pitfalls: "常见陷阱",
        overall_evaluation: "整体评价",
        job_analysis: "岗位分析",
        high_freq_categories: "高频考点分类",
        high_freq_list: "高频考点清单",
        project_deep_dive: "项目深挖",
        behavioral_prep: "行为面试准备",
        on_site_strategies: "临场应对策略",
        recommended_resources: "推荐复习资料",
        match_level: "匹配等级",
        advice: "建议",
        resume_suggestions: "简历修改建议",
        overview: "概述",
        key_skills: "关键技能",
        experience_requirements: "经验要求",
        education_requirements: "学历要求",
        responsibilities: "岗位职责",
        qualifications: "任职要求",
        dimension: "维度",
        frequency: "频率",
        importance: "重要性",
        answer_framework: "回答框架",
        star_method: "STAR方法",
        scenario: "场景",
        task: "任务",
        action: "行动",
        result: "结果",
        pressure_questions: "压力问题",
        coping_techniques: "应对技巧",
    };

    if (labelMap[key]) return labelMap[key];

    return key
        .replace(/_([a-z])/g, (match, letter) => " " + letter.toUpperCase())
        .replace(/^./, (match) => match.toUpperCase());
}

document.getElementById("export-btn").addEventListener("click", async () => {
    if (!currentReportId) {
        showToast("没有可导出的报告", "warning");
        return;
    }

    try {
        window.open(`/api/report/${currentReportId}/export`, "_blank");
        showToast("导出成功", "success");
    } catch (error) {
        showToast("导出失败", "error");
    }
});

async function loadHistory() {
    try {
        const response = await fetch("/api/reports");
        const reports = await response.json();

        const container = document.getElementById("history-list");

        if (reports.length === 0) {
            container.innerHTML = '<p class="empty-text">暂无历史报告</p>';
            return;
        }

        container.innerHTML = reports
            .map(
                (report) => `
            <div class="history-item" data-report-id="${report.report_id}">
                <div class="history-info">
                    <h4>${report.position_name}</h4>
                    <p>${report.created_at} · ${report.modules_count}个模块</p>
                </div>
                <div class="history-actions">
                    <button class="view-btn">查看</button>
                    <button class="export-btn">导出</button>
                </div>
            </div>
        `
            )
            .join("");

        container.querySelectorAll(".history-item").forEach((item) => {
            item.querySelector(".view-btn").addEventListener("click", (e) => {
                e.stopPropagation();
                viewHistoryReport(item.dataset.reportId);
            });
            item.querySelector(".export-btn").addEventListener("click", (e) => {
                e.stopPropagation();
                window.open(`/api/report/${item.dataset.reportId}/export`, "_blank");
            });
        });
    } catch (error) {
        console.error("Load history error:", error);
    }
}

async function viewHistoryReport(reportId) {
    currentReportId = reportId;
    document.getElementById("report-section").classList.remove("hidden");

    try {
        const response = await fetch(`/api/report/${reportId}`);
        const report = await response.json();

        renderTabs();
        renderModule("all", report);

        document.getElementById("report-section").scrollIntoView({ behavior: "smooth" });
    } catch (error) {
        showToast("加载报告失败", "error");
    }
}

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}
