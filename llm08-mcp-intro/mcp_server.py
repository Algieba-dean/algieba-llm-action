import os
import requests
import feedparser
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服务器
load_dotenv()
mcp = FastMCP("Blog_Monitor_Notifier")

@mcp.tool()
def get_latest_blog_post(rss_url: str) -> str:
    """
    请求并解析目标博客的 RSS feed，获取最新的一篇博客文章的标题和链接。
    当你需要检查博客是否有更新时，调用此工具。
    """
    try:
        feed = feedparser.parse(rss_url)
        if feed.entries:
            latest_entry = feed.entries[0]
            return f"Title: {latest_entry.title}\nLink: {latest_entry.link}"
        return f"在 RSS 源 {rss_url} 中未找到任何文章。"
    except Exception as e:
        return f"获取博客失败: {str(e)}"

@mcp.tool()
def send_email_notification(post_title: str, post_link: str) -> str:
    """
    当发现博客有更新时，调用此工具发送邮件通知。
    必须提供新博客的标题 (post_title) 和链接 (post_link)。
    """
    target_email = os.environ.get("TARGET_EMAIL")
    email_api_key = os.environ.get("EMAIL_API_KEY")
    
    if not target_email or not email_api_key:
        return "邮件发送失败：未配置 TARGET_EMAIL 或 EMAIL_API_KEY 环境变量。"

    headers = {
        "Authorization": f"Bearer {email_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from" : "onboarding@resend.dev",
        "to": target_email,
        "subject": f"阿尔的代码屋更新咯：{post_title}",
        "text": f"检测到 阿尔的代码屋 更新了一篇新博客 \n\n标题：{post_title}\n链接: {post_link}"
    }

    try:
        response = requests.post("https://api.resend.com/emails", headers=headers, json=payload)
        if response.status_code == 200:
            return "邮件通知发送成功"
        return f"邮件发送失败: {response.text}"
    except Exception as e:
        return f"发送邮件时发生异常: {str(e)}"

@mcp.tool()
def send_wechat_notification(post_title: str, post_link: str) -> str:
    """
    当发现博客有更新时，调用此工具发送微信通知。
    必须提供新博客的标题 (post_title) 和链接 (post_link)。
    """
    wechat_api_key = os.environ.get("WECHAT_API_KEY")
    
    if not wechat_api_key:
        return "微信通知发送失败：未配置 WECHAT_API_KEY 环境变量。"
        
    url = f"https://sctapi.ftqq.com/{wechat_api_key}.send"
    data = {
        "title": f"阿尔的代码屋更新咯：{post_title}",
        "desp": f"检测到 阿尔的代码屋 更新了一篇新博客 \n\n标题：{post_title}\n链接: {post_link}"
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            return f"微信消息发送失败: {response.text}"
        
        result = response.json()
        if result.get("code") != 0:
            return f"API 拒绝请求: {result.get('message')}"
            
        return "微信通知发送成功"
    except Exception as e:
        return f"发送微信通知时发生异常: {str(e)}"

if __name__ == "__main__":
    # 启动 MCP 服务器，默认监听 stdio
    mcp.run()