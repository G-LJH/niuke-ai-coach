import os
import sys
import json
import time
import threading
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(__file__))

from src.workflow import generate_interview_report
from src.state_manager import get_workflow

app = Flask(__name__, static_folder="static", template_folder="templates")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "data", "uploads")
REPORTS_FOLDER = os.path.join(os.path.dirname(__file__), "data", "reports")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORTS_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024

TASKS = {}

MODULE_NAMES = {
    "overall_evaluation": "整体评价",
    "job_analysis": "岗位分析",
    "high_freq_categories": "高频考点分类解析",
    "high_freq_list": "高频考点清单",
    "project_deep_dive": "项目深挖",
    "behavioral_prep": "行为面试准备",
    "on_site_strategies": "临场应对策略",
    "recommended_resources": "推荐复习资料",
}

MODULE_ICONS = {
    "overall_evaluation": "📊",
    "job_analysis": "💼",
    "high_freq_categories": "📚",
    "high_freq_list": "📝",
    "project_deep_dive": "🔍",
    "behavioral_prep": "🤝",
    "on_site_strategies": "⚡",
    "recommended_resources": "📖",
}

LABEL_MAP = {
    "title": "标题",
    "summary": "总结",
    "suggestions": "建议",
    "skills": "技能要求",
    "questions": "问题",
    "project_name": "项目名称",
    "tech_deep_dive": "技术深挖",
    "predicted_questions": "预测问题",
    "question": "问题",
    "depth": "深度",
    "preparation_tips": "准备建议",
    "tech": "技术点",
    "possible_questions": "可能的问题",
    "books": "推荐书籍",
    "courses": "推荐课程",
    "websites": "推荐网站",
    "interview_exps": "面经链接",
    "match_score": "匹配度",
    "strengths": "优势",
    "weaknesses": "不足",
    "core_requirements": "核心要求",
    "tech_stack": "技术栈",
    "soft_skills": "软技能",
    "categories": "分类",
    "category": "类别",
    "description": "描述",
    "strategy": "策略",
    "key_points": "要点",
    "answer_points": "答题要点",
    "example_answer": "示例回答",
    "pitfalls": "常见陷阱",
    "match_level": "匹配等级",
    "advice": "建议",
    "resume_suggestions": "简历修改建议",
    "overview": "概述",
    "key_skills": "关键技能",
    "experience_requirements": "经验要求",
    "education_requirements": "学历要求",
    "responsibilities": "岗位职责",
    "qualifications": "任职要求",
    "dimension": "维度",
    "frequency": "频率",
    "importance": "重要性",
    "answer_framework": "回答框架",
    "scenario": "场景",
    "task": "任务",
    "action": "行动",
    "result": "结果",
    "pressure_questions": "压力问题",
    "coping_techniques": "应对技巧",
}

LIST_KEYS = {"resume_suggestions", "core_requirements", "tech_stack", "soft_skills"}
QUESTION_KEYS = {"questions", "predicted_questions", "possible_questions"}
RESOURCE_KEYS = {"books", "courses", "websites", "interview_exps"}
SCALAR_KEYS = {"summary", "match_score", "match_level"}


def format_label(key):
    return LABEL_MAP.get(key, key)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _format_list_items(items, indent=0):
    prefix = "  " * indent
    lines = []
    for item in items:
        if isinstance(item, dict):
            for k, v in item.items():
                if isinstance(v, list):
                    lines.append(f"{prefix}- **{format_label(k)}**:")
                    lines.extend(f"{prefix}  - {sub}" for sub in v)
                else:
                    lines.append(f"{prefix}- **{format_label(k)}**: {v}")
        else:
            lines.append(f"{prefix}- {item}")
    return lines


def _format_question_item(item, index):
    lines = []
    if isinstance(item, dict):
        question = item.get("question", "")
        lines.append(f"**{index}. {question}**\n")
        for k, v in item.items():
            if k == "question":
                continue
            if k in ("frequency", "difficulty", "depth", "match_score"):
                lines.append(f"- **{format_label(k)}**: {v}")
            elif isinstance(v, list):
                lines.append(f"- **{format_label(k)}**:")
                lines.extend(f"  - {sub}" for sub in v)
            elif isinstance(v, str):
                lines.append(f"- **{format_label(k)}**: {v}")
    else:
        lines.append(f"{index}. {item}")
    return lines


def _format_module_to_markdown(module_key, module_data):
    lines = []
    if not isinstance(module_data, dict):
        return lines

    for key, value in sorted(module_data.items(), key=lambda x: (
        0 if x[0] in QUESTION_KEYS | SCALAR_KEYS else 1
    )):
        label = format_label(key)

        if key in SCALAR_KEYS:
            lines.append(f"### {label}\n")
            lines.append(f"**{value}**\n" if isinstance(value, (int, float)) else f"{value}\n")

        elif key in LIST_KEYS:
            lines.append(f"### {label}\n")
            if isinstance(value, list):
                lines.extend(f"- {item}" for item in value)
            lines.append("")

        elif key in QUESTION_KEYS:
            lines.append(f"### {label}\n")
            if isinstance(value, list):
                for i, item in enumerate(value, 1):
                    lines.extend(_format_question_item(item, i))
                    lines.append("")

        elif key == "categories":
            lines.append(f"### {label}\n")
            if isinstance(value, list):
                lines.append("| 维度 | 考察重点 | 准备建议 |")
                lines.append("|------|----------|----------|")
                for cat in value:
                    if isinstance(cat, dict):
                        category = cat.get("category", "")
                        desc = cat.get("description", "")
                        questions = cat.get("questions", [])
                        question_text = ", ".join(q.get("question", "") for q in questions[:3]) if questions else ""
                        lines.append(f"| {category} | {desc} | {question_text} |")
                lines.append("")

                for cat in value:
                    if isinstance(cat, dict):
                        category = cat.get("category", "")
                        lines.append(f"#### {category}\n")
                        questions = cat.get("questions", [])
                        if questions:
                            for i, q in enumerate(questions, 1):
                                if isinstance(q, dict):
                                    lines.append(f"**{i}. {q.get('question', '')}**\n")
                                    for k, v in q.items():
                                        if k == "question":
                                            continue
                                        if isinstance(v, list):
                                            lines.append(f"- **{format_label(k)}**:")
                                            lines.extend(f"  - {sub}" for sub in v)
                                        elif isinstance(v, str):
                                            lines.append(f"- **{format_label(k)}**: {v}")
                                    lines.append("")

        elif key == "projects":
            lines.append(f"### {label}\n")
            if isinstance(value, list):
                for i, proj in enumerate(value, 1):
                    if isinstance(proj, dict):
                        proj_name = proj.get("project_name", "")
                        lines.append(f"**{i}. {proj_name}**\n")
                        for k, v in proj.items():
                            if k == "project_name":
                                continue
                            if k in ("predicted_questions", "tech_deep_dive"):
                                lines.append(f"- **{format_label(k)}**:")
                                if isinstance(v, list):
                                    for item in v:
                                        question = item.get("question", "") or item.get("tech", "") if isinstance(item, dict) else item
                                        lines.append(f"  - {question}")
                            elif isinstance(v, str):
                                lines.append(f"- **{format_label(k)}**: {v}")
                        lines.append("")

        elif key in RESOURCE_KEYS:
            lines.append(f"### {label}\n")
            if isinstance(value, list):
                lines.extend(f"- {item}" for item in value)
                lines.append("")

        elif isinstance(value, str):
            lines.append(f"### {label}\n")
            lines.append(f"{value}\n")

        elif isinstance(value, list):
            lines.append(f"### {label}\n")
            lines.extend(_format_list_items(value))
            lines.append("")

    return lines


def run_task(task_id, position_name, jd_type, jd_content, resume_path, count):
    try:
        jd_input = None
        if jd_type == "text" and jd_content:
            jd_input = {"type": "text", "content": jd_content}
        elif jd_type == "image" and jd_content:
            jd_input = {"type": "image", "content": jd_content}

        TASKS[task_id]["status"] = "running"
        TASKS[task_id]["step"] = "解析输入信息"

        result = generate_interview_report(
            position_name=position_name,
            jd_input=jd_input,
            crawl_count=count,
            resume_pdf_path=resume_path,
            progress_callback=lambda step: TASKS[task_id].update({"step": step}),
        )

        if result.get("success"):
            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["report_id"] = result["report_id"]
            TASKS[task_id]["file_path"] = result["file_path"]
            TASKS[task_id]["step"] = "完成"
        else:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["error"] = result.get("error", {}).get("message", "未知错误")
            TASKS[task_id]["step"] = "完成"
    except Exception as e:
        TASKS[task_id]["status"] = "failed"
        TASKS[task_id]["error"] = str(e)
        TASKS[task_id]["step"] = "完成"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "没有文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "没有选择文件"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": f"不支持的文件格式，仅支持: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_name = f"{timestamp}_{uuid.uuid4().hex[:8]}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_name)
    file.save(filepath)

    return jsonify({"filepath": filepath, "filename": filename})


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.json
    position_name = data.get("position_name", "").strip()
    if not position_name:
        return jsonify({"error": "岗位名称不能为空"}), 400

    jd_type = data.get("jd_type", "none")
    jd_content = data.get("jd_content", "")
    resume_path = data.get("resume_path", "")
    count = data.get("count", 10)

    if not resume_path:
        return jsonify({"error": "请上传简历"}), 400

    if not os.path.exists(resume_path):
        return jsonify({"error": "简历文件不存在"}), 400

    task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
    TASKS[task_id] = {
        "status": "pending",
        "step": "等待开始",
        "position_name": position_name,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    thread = threading.Thread(
        target=run_task,
        args=(task_id, position_name, jd_type, jd_content, resume_path, count),
    )
    thread.daemon = True
    thread.start()

    return jsonify({"task_id": task_id, "status": "pending"})


@app.route("/api/task/<task_id>")
def get_task_status(task_id):
    if task_id not in TASKS:
        return jsonify({"error": "任务不存在"}), 404

    task = TASKS[task_id]
    return jsonify({
        "task_id": task_id,
        "status": task["status"],
        "step": task.get("step", ""),
        "position_name": task.get("position_name", ""),
        "report_id": task.get("report_id", ""),
        "error": task.get("error", ""),
    })


@app.route("/api/report/<report_id>")
def get_report(report_id):
    report_path = os.path.join(REPORTS_FOLDER, f"{report_id}.json")
    if not os.path.exists(report_path):
        return jsonify({"error": "报告不存在"}), 404

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    return jsonify(report)


@app.route("/api/report/<report_id>/export")
def export_report(report_id):
    report_path = os.path.join(REPORTS_FOLDER, f"{report_id}.json")
    if not os.path.exists(report_path):
        return jsonify({"error": "报告不存在"}), 404

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    position_name = report.get('position_name', '未知岗位')
    created_at = report.get('created_at', '')
    modules = report.get('modules', {})

    md_lines = [f"# 🎯 {position_name} - 面试分析报告\n", f"**生成时间**: {created_at}\n", "---\n"]

    for module_key, module_name in MODULE_NAMES.items():
        module_data = modules.get(module_key, {})
        if not module_data:
            continue

        icon = MODULE_ICONS.get(module_key, "📄")
        md_lines.append(f"## {icon} {module_name}\n")
        md_lines.extend(_format_module_to_markdown(module_key, module_data))
        md_lines.append("---\n")

    export_path = os.path.join(REPORTS_FOLDER, f"{report_id}.md")
    with open(export_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return send_file(export_path, as_attachment=True, download_name=f"{report_id}.md")


@app.route("/api/reports")
def list_reports():
    reports = []
    if os.path.exists(REPORTS_FOLDER):
        for filename in sorted(os.listdir(REPORTS_FOLDER), reverse=True):
            if filename.endswith(".json"):
                filepath = os.path.join(REPORTS_FOLDER, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    report = json.load(f)
                reports.append({
                    "report_id": report.get("report_id", filename.replace(".json", "")),
                    "position_name": report.get("position_name", ""),
                    "created_at": report.get("created_at", ""),
                    "modules_count": len(report.get("modules", {})),
                })
    return jsonify(reports)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
