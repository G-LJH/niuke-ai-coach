import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.workflow import generate_interview_report
from src.state_manager import get_workflow


def main():
    parser = argparse.ArgumentParser(description="牛客AI面试教练 - 生成面试分析报告")
    parser.add_argument("--position", type=str, required=True, help="岗位名称")
    parser.add_argument("--jd-text", type=str, help="岗位描述文字")
    parser.add_argument("--jd-image", type=str, help="JD截图路径")
    parser.add_argument("--resume", type=str, required=True, help="简历PDF路径")
    parser.add_argument("--count", type=int, default=10, help="抓取面经数量 (1-50)")
    parser.add_argument("--workflow-id", type=str, help="工作流ID（用于断点续传）")
    parser.add_argument("--resume-workflow", action="store_true", help="从断点续传恢复工作流")

    args = parser.parse_args()

    jd_input = None
    if args.jd_text:
        jd_input = {"type": "text", "content": args.jd_text}
    elif args.jd_image:
        jd_input = {"type": "image", "content": args.jd_image}

    result = generate_interview_report(
        position_name=args.position,
        jd_input=jd_input,
        crawl_count=args.count,
        resume_pdf_path=args.resume,
        workflow_id=args.workflow_id,
        resume=args.resume_workflow,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("success"):
        print(f"\n报告生成成功！")
        print(f"报告ID: {result['report_id']}")
        print(f"文件路径: {result['file_path']}")
    else:
        print(f"\n报告生成失败: {result.get('error', {}).get('message', '未知错误')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
