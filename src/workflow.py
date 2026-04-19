import os
import json
import time
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.logger import get_logger, log_workflow_step
from src.state_manager import (
    create_workflow,
    update_workflow_status,
    get_workflow,
)
from src.tools import (
    search_interview_exps,
    fetch_interview_content,
    parse_resume_pdf,
    analyze_jd_screenshot,
    call_llm,
)

logger = get_logger("workflow")

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

WORKFLOW_TIMEOUT_MINUTES = 60
STEP_TIMEOUTS = {
    1: 5 * 60,
    2: 30 * 60,
    3: 20 * 60,
    4: 1 * 60,
}

MODULE_NAMES = [
    "overall_evaluation",
    "job_analysis",
    "high_freq_categories",
    "high_freq_list",
    "project_deep_dive",
    "behavioral_prep",
    "on_site_strategies",
    "recommended_resources",
]

MODULE_PROMPTS = {
    "overall_evaluation": "基于简历与岗位匹配度，生成整体评价和简历修改建议。返回JSON格式：{\"title\": \"整体评价\", \"summary\": \"评价文字\", \"match_score\": 85, \"resume_suggestions\": [\"建议1\"]}",
    "job_analysis": "分析岗位核心要求、技术栈、软技能要求、发展方向。返回JSON格式：{\"title\": \"岗位分析\", \"core_requirements\": [\"要求1\"], \"tech_stack\": [\"技术A\"], \"soft_skills\": [\"沟通\"], \"career_path\": \"发展方向\"}",
    "high_freq_categories": "按面试维度分类高频考点。返回JSON格式：{\"title\": \"高频考点分类解析\", \"categories\": [{\"category\": \"基础知识\", \"description\": \"说明\", \"questions\": [{\"question\": \"问题\", \"frequency\": 5, \"difficulty\": \"medium\", \"strategy\": \"策略\", \"key_points\": [\"要点1\"]}]}]}",
    "high_freq_list": "列出高频考点清单及应对策略。返回JSON格式：{\"title\": \"高频考点清单及应对策略\", \"questions\": [{\"question\": \"问题\", \"frequency\": 8, \"answer_points\": [\"要点1\"], \"example_answer\": \"示例\", \"pitfalls\": [\"错误1\"]}]}",
    "project_deep_dive": "针对简历项目生成追问预测。返回JSON格式：{\"title\": \"项目深挖\", \"projects\": [{\"project_name\": \"项目\", \"predicted_questions\": [{\"question\": \"追问\", \"depth\": \"deep\", \"preparation_tips\": \"建议\"}], \"tech_deep_dive\": [{\"tech\": \"技术\", \"possible_questions\": [\"问题1\"]}]}], \"general_tips\": \"通用建议\"}",
    "behavioral_prep": "生成HR终面常见问题及STAR回答框架。返回JSON格式：{\"title\": \"行为面试准备\", \"questions\": [{\"question\": \"问题\", \"framework\": \"STAR框架\", \"example\": \"示例\"}], \"tips\": \"技巧\"}",
    "on_site_strategies": "生成临场应对策略。返回JSON格式：{\"title\": \"临场应对策略\", \"pressure_handling\": [\"技巧1\"], \"unknown_questions\": [\"技巧1\"], \"communication_tips\": [\"技巧1\"]}",
    "recommended_resources": "推荐复习资料。返回JSON格式：{\"title\": \"推荐复习资料\", \"books\": [\"书名1\"], \"websites\": [\"网站1\"], \"courses\": [\"课程1\"], \"interview_exps\": [\"链接1\"]}",
}


def generate_workflow_id(position_name: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    pos_hash = hashlib.md5(position_name.encode()).hexdigest()[:8]
    return f"report_{timestamp}_{pos_hash}"


def generate_interview_report(
    position_name: str,
    jd_input: Optional[Dict[str, str]] = None,
    crawl_count: int = 10,
    resume_pdf_path: str = None,
    workflow_id: str = None,
    resume: bool = False,
    progress_callback=None,
) -> Dict[str, Any]:
    if not workflow_id:
        workflow_id = generate_workflow_id(position_name)

    if resume:
        return _resume_workflow(workflow_id)

    create_workflow(workflow_id)
    start_time = time.time()

    try:
        jd_text = None

        update_workflow_status(workflow_id, 1, "parse_input", "running")
        log_workflow_step(logger, workflow_id, 1, "parse_input", "running")
        if progress_callback:
            progress_callback("解析输入信息")

        if jd_input:
            if jd_input.get("type") == "image":
                result = analyze_jd_screenshot(jd_input.get("content"))
                if "error" in result:
                    raise Exception(f"JD截图解析失败: {result['error']}")
                jd_text = result.get("raw_text", "")
            elif jd_input.get("type") == "text":
                jd_text = jd_input.get("content", "")

        resume_result = parse_resume_pdf(resume_pdf_path)
        if "error" in resume_result:
            raise Exception(f"简历解析失败: {resume_result['error']}")

        parsed_context = {
            "jd_text": jd_text,
            "resume_raw_text": resume_result.get("raw_text", ""),
        }

        update_workflow_status(
            workflow_id,
            1,
            "parse_input",
            "running",
            data={"parsed_context": parsed_context},
        )

        if time.time() - start_time > STEP_TIMEOUTS[1]:
            raise Exception("步骤1超时")

        update_workflow_status(workflow_id, 2, "fetch_interview_exps", "running")
        log_workflow_step(logger, workflow_id, 2, "fetch_interview_exps", "running")
        if progress_callback:
            progress_callback("抓取面经数据")

        exp_urls = search_interview_exps(position=position_name, count=crawl_count)
        urls_found = [u["url"] for u in exp_urls]

        exps = []
        urls_success = []
        urls_failed = []

        for url_info in exp_urls:
            url = url_info["url"]
            retry = 0
            max_retries = 3
            success = False

            while retry < max_retries and not success:
                result = fetch_interview_content(url)
                if "error" not in result:
                    exps.append(result)
                    urls_success.append(url)
                    success = True
                else:
                    retry += 1
                    if retry < max_retries:
                        time.sleep(60)

            if not success:
                urls_failed.append({"url": url, "error": result.get("error", "unknown")})

        success_rate = len(urls_success) / len(urls_found) if urls_found else 0
        if success_rate == 0:
            raise Exception("面经抓取成功率为0，终止流程")

        if success_rate < 0.5:
            logger.warning(f"面经抓取成功率较低: {success_rate:.2%}")

        interview_exps_data = {
            "urls_found": urls_found,
            "urls_success": urls_success,
            "urls_failed": urls_failed,
            "exps": exps,
            "total_count": len(urls_found),
            "success_count": len(urls_success),
            "fail_count": len(urls_failed),
        }

        update_workflow_status(
            workflow_id,
            2,
            "fetch_interview_exps",
            "running",
            data={"interview_exps": interview_exps_data},
        )

        if time.time() - start_time > STEP_TIMEOUTS[2]:
            raise Exception("步骤2超时")

        update_workflow_status(workflow_id, 3, "generate_report_modules", "running")
        log_workflow_step(logger, workflow_id, 3, "generate_report_modules", "running")
        if progress_callback:
            progress_callback("生成报告模块")

        modules_generated = []
        modules_failed = []
        modules_data = {}
        total_input_tokens = 0
        total_output_tokens = 0

        system_prompt = f"""你是专业的面试辅导专家。
岗位名称：{position_name}
{f'岗位描述：{jd_text}' if jd_text else ''}
候选人简历原文：{parsed_context['resume_raw_text'][:5000]}
面经数据：{json.dumps(exps, ensure_ascii=False)[:5000]}

请根据以上信息生成面试分析报告模块。只返回JSON格式，不要其他文字。"""

        for module_name in MODULE_NAMES:
            try:
                logger.info(f"生成模块: {module_name}")
                prompt = MODULE_PROMPTS[module_name]
                result = call_llm(prompt, system_prompt=system_prompt)

                if "error" in result:
                    logger.error(f"模块 {module_name} 生成失败: {result['error']}")
                    modules_failed.append(module_name)
                    continue

                module_content = json.loads(result["content"])
                modules_data[module_name] = module_content
                modules_generated.append(module_name)
                logger.info(f"模块 {module_name} 生成成功")

                total_input_tokens += result["usage"]["input_tokens"]
                total_output_tokens += result["usage"]["output_tokens"]

                update_workflow_status(
                    workflow_id,
                    3,
                    "generate_report_modules",
                    "running",
                    data={
                        "modules_generated": modules_generated,
                        "modules_failed": modules_failed,
                    },
                )

            except Exception as e:
                logger.error(f"模块 {module_name} 生成失败: {e}")
                modules_failed.append(module_name)

        if time.time() - start_time > STEP_TIMEOUTS[3]:
            raise Exception("步骤3超时")

        update_workflow_status(workflow_id, 4, "save_report", "running")
        log_workflow_step(logger, workflow_id, 4, "save_report", "running")
        if progress_callback:
            progress_callback("保存报告")

        report_id = workflow_id
        report = {
            "report_id": report_id,
            "position_name": position_name,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "modules": modules_data,
        }

        file_path = os.path.join(REPORTS_DIR, f"{report_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        update_workflow_status(
            workflow_id,
            4,
            "save_report",
            "completed",
            data={
                "report_id": report_id,
                "file_path": file_path,
            },
        )

        log_workflow_step(logger, workflow_id, 4, "save_report", "completed")

        return {
            "success": True,
            "report_id": report_id,
            "file_path": file_path,
            "modules_count": len(modules_generated),
            "created_at": report["created_at"],
        }

    except Exception as e:
        update_workflow_status(
            workflow_id,
            get_workflow(workflow_id)["step"],
            get_workflow(workflow_id)["step_name"],
            "failed",
            error={
                "code": "WORKFLOW_ERROR",
                "message": str(e),
                "detail": {},
            },
        )
        return {
            "success": False,
            "error": {
                "code": "WORKFLOW_ERROR",
                "message": str(e),
                "step": get_workflow(workflow_id)["step"],
                "step_name": get_workflow(workflow_id)["step_name"],
            },
        }


def _resume_workflow(workflow_id: str) -> Dict[str, Any]:
    workflow = get_workflow(workflow_id)
    if not workflow:
        return {"success": False, "error": {"message": f"Workflow {workflow_id} not found"}}

    if workflow["status"] == "completed":
        return {
            "success": True,
            "report_id": workflow["data"].get("report_id"),
            "file_path": workflow["data"].get("file_path"),
        }

    if workflow["status"] not in ("running", "failed"):
        return {"success": False, "error": {"message": "Workflow cannot be resumed"}}

    return generate_interview_report(
        position_name="",
        workflow_id=workflow_id,
        resume=True,
    )
