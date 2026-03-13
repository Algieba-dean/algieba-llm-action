import os
import requests
import feedparser
import logging
import sys
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服务器
current_dir = os.path.dirname(os.path.abspath(__file__)) # 这里锁死脚本所在路径，避免到时候在外层通过client运行mcp的时候，读不到.env
env_path = os.path.join(current_dir, '.env')
load_dotenv(env_path)
mcp = FastMCP("Blog_Monitor_Notifier")

# 配置日志
log_file_path = os.path.join(current_dir, 'mcp_server.log')

# 1. 获取专属的 logger 实例并设置捕获级别
logger = logging.getLogger("blog_monitor")
logger.setLevel(logging.INFO)

# 2. 核心避坑：清空可能被框架提前注入的默认 handler
if logger.hasHandlers():
    logger.handlers.clear()

# 3. 创建格式化器
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s')

# 4. 配置文件 Handler
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 5. 配置标准错误流 Handler (给 OpenCode 这种客户端看的)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(formatter)
logger.addHandler(stderr_handler)

# 6. 核心避坑：切断向 root logger 的传播
# 防止我们的日志被 FastMCP 底层拦截或吞噬
logger.propagate = False

# 测试一下日志是否正常工作
logger.info("=== 日志系统初始化成功，MCP Server 启动中 ===")

@mcp.tool()
def get_latest_blog_post(rss_url: str) -> str:
    """
    请求并解析目标博客的 RSS feed，获取最新的一篇博客文章的标题和链接。
    当你需要检查博客是否有更新时，调用此工具。
    """
    logger.info(f"开始检查 RSS 源: {rss_url}")
    try:
        feed = feedparser.parse(rss_url)
        if feed.entries:
            latest_entry = feed.entries[0]
            logger.info(f"成功获取到最新文章: {latest_entry.title}")
            return f"Title: {latest_entry.title}\nLink: {latest_entry.link}"
        
        logger.warning(f"RSS 源 {rss_url} 解析成功，但没有找到文章条目。")
        return f"在 RSS 源 {rss_url} 中未找到任何文章。"
    except Exception as e:
        logger.error(f"解析 RSS 失败: {str(e)}", exc_info=True)
        return f"获取博客失败: {str(e)}"

@mcp.tool()
def send_email_notification(post_title: str, post_link: str) -> str:
    """
    当发现博客有更新时，调用此工具发送邮件通知。
    必须提供新博客的标题 (post_title) 和链接 (post_link)。
    """
    logger.info(f"准备发送邮件通知，目标文章: {post_title}")
    
    target_email = os.environ.get("TARGET_EMAIL")
    email_api_key = os.environ.get("EMAIL_API_KEY")

    # 打印脱敏后的鉴权信息，用于排查环境注入问题
    masked_email = target_email if target_email else "未配置"
    masked_key = f"{email_api_key[:5]}...{email_api_key[-3:]}" if email_api_key else "未配置"
    logger.info(f"读取到的配置 -> 目标邮箱: {masked_email}, API_KEY: {masked_key}")

    if not target_email or not email_api_key:
        logger.error("邮件发送终止：核心环境变量缺失。")
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
        logger.info("正在向 Resend API 发起 POST 请求...")
        response = requests.post("https://api.resend.com/emails", headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info("邮件 API 调用成功，邮件已发送。")
            return "邮件通知发送成功"
        
        logger.error(f"邮件 API 返回错误状态码: {response.status_code}, 详情: {response.text}")
        return f"邮件发送失败，API 返回: {response.text}"
    except Exception as e:
        logger.error(f"请求 Resend API 时发生异常: {str(e)}", exc_info=True)
        return f"发送邮件时发生网络异常: {str(e)}"

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