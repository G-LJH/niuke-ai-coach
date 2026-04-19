# -*- coding: utf-8 -*-
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.tools.resume import parse_resume_pdf
from src.tools.jd import analyze_jd_screenshot
from src.tools.niuke import search_interview_exps, fetch_interview_content

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SAMPLE_RESUME = os.path.join(TEST_DATA_DIR, "sample_resume.pdf")
SAMPLE_JD = os.path.join(TEST_DATA_DIR, "sample_jd.jpg")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "test_output.txt")


def write(f, text=""):
    f.write(text + "\n")


def separator(f, title):
    write(f)
    write(f, "=" * 60)
    write(f, f"  {title}")
    write(f, "=" * 60)
    write(f)


def test_resume(f):
    separator(f, "简历解析测试")
    
    if not os.path.exists(SAMPLE_RESUME):
        write(f, f"跳过：未找到简历文件 {SAMPLE_RESUME}")
        return False
    
    write(f, f"解析文件：{SAMPLE_RESUME}")
    result = parse_resume_pdf(SAMPLE_RESUME)
    
    if "error" in result:
        write(f, f"失败：{result['error']}")
        return False
    
    write(f, "\n提取结果：")
    write(f, f"  姓名：{result.get('name', '未提取')}")
    write(f, f"  电话：{result.get('phone', '未提取')}")
    write(f, f"  邮箱：{result.get('email', '未提取')}")
    write(f, f"  原始文本长度：{len(result.get('raw_text', ''))} 字符")
    write(f, "\n原始文本预览（前500字符）：")
    write(f, f"  {result.get('raw_text', '')[:500]}...")
    return True


def test_jd(f):
    separator(f, "JD OCR识别测试")
    
    if not os.path.exists(SAMPLE_JD):
        write(f, f"跳过：未找到JD图片 {SAMPLE_JD}")
        return False
    
    write(f, f"解析图片：{SAMPLE_JD}")
    result = analyze_jd_screenshot(SAMPLE_JD)
    
    if "error" in result:
        write(f, f"失败：{result['error']}")
        return False
    
    write(f, "\n提取结果：")
    write(f, f"  公司：{result.get('company', '未提取')}")
    write(f, f"  职位：{result.get('position', '未提取')}")
    write(f, f"  任职要求：{len(result.get('requirements', []))} 条")
    for i, req in enumerate(result.get('requirements', [])[:5], 1):
        write(f, f"    {i}. {req}")
    write(f, f"  优先技能：{len(result.get('preferred_skills', []))} 条")
    for i, skill in enumerate(result.get('preferred_skills', [])[:5], 1):
        write(f, f"    {i}. {skill}")
    return True


def test_niuke(f):
    separator(f, "牛客网面经爬取测试")
    
    write(f, "搜索职位：Java，数量：3")
    results = search_interview_exps(position="Java", count=3)
    
    write(f, f"\n找到 {len(results)} 条面经：")
    for i, r in enumerate(results, 1):
        write(f, f"\n  {i}. {r.get('title', '无标题')}")
        write(f, f"     链接：{r.get('url', '无链接')}")
    
    if results:
        write(f, "\n获取第一条面经内容...")
        first_url = results[0]["url"]
        content = fetch_interview_content(first_url)
        
        if "error" in content:
            write(f, f"  失败：{content['error']}")
        else:
            write(f, f"\n  标题：{content.get('title', '无')}")
            write(f, f"  作者：{content.get('author', '无')}")
            write(f, f"  日期：{content.get('date', '无')}")
            write(f, f"  内容长度：{len(content.get('content', ''))} 字符")
            write(f, f"  提取问题数：{len(content.get('questions', []))}")
            write(f, "\n" + "-" * 40)
            write(f, "面经完整内容：")
            write(f, "-" * 40)
            write(f, content.get('content', ''))
            
            if content.get('questions'):
                write(f, "\n" + "-" * 40)
                write(f, "提取的面试问题：")
                write(f, "-" * 40)
                for i, q in enumerate(content['questions'], 1):
                    write(f, f"{i}. {q}")
    return True


if __name__ == "__main__":
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        write(f, "=" * 60)
        write(f, "  测试报告")
        write(f, f"  运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        write(f, "=" * 60)
        
        test_resume(f)
        test_jd(f)
        test_niuke(f)
        
        separator(f, "测试完成")
    
    print(f"测试完成！结果已保存到：{OUTPUT_FILE}")
    print("请用文本编辑器（如VS Code、记事本）打开查看完整结果。")
