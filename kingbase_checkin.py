#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kingbase 论坛自动回帖脚本
适用于青龙面板定时任务
"""

import random
import time
import json
import os
import requests
import pytz
from datetime import datetime


def bj_time():
    """获取北京时间"""
    return datetime.now(pytz.timezone('Asia/Shanghai'))


def fmt_now():
    """格式化当前时间"""
    return bj_time().strftime("%Y-%m-%d %H:%M:%S")


class KingbaseClient:
    def __init__(self, user, pwd, article_id, pushplus_token=None):
        self.user = user
        self.pwd = pwd
        self.article_id = article_id
        self.token = None
        self.pushplus_token = pushplus_token
        self.user_name = user
    
    def log(self, message, level='INFO'):
        """日志输出"""
        timestamp = fmt_now()
        print(f"[{timestamp}] [{level}] {message}")
    
    def send_notification(self, title, content):
        """PushPlus消息推送"""
        if not self.pushplus_token:
            self.log("⚠️ 未配置PushPlus Token，跳过消息推送")
            return
        
        attempts = 3
        pushplus_url = "http://www.pushplus.plus/send"
        
        # 在标题和内容中加入用户名称
        title_with_user = "[{}] {}".format(self.user_name, title)
        content_with_user = "👤 账号: {}\n\n{}".format(self.user_name, content)
        
        for attempt in range(attempts):
            try:
                response = requests.post(
                    pushplus_url,
                    data=json.dumps({
                        "token": self.pushplus_token,
                        "title": title_with_user,
                        "content": content_with_user
                    }).encode('utf-8'),
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                response.raise_for_status()
                self.log("✅ PushPlus响应: {}".format(response.text))
                break
            except requests.exceptions.RequestException as e:
                self.log("❌ PushPlus推送失败: {}".format(e), 'ERROR')
                if attempt < attempts - 1:
                    sleep_time = random.randint(30, 60)
                    self.log("将在 {} 秒后重试...".format(sleep_time))
                    time.sleep(sleep_time)
    
    def login(self):
        """登录 Kingbase 论坛"""
        try:
            self.log("尝试登录 Kingbase...")
            login_url = "https://bbs.kingbase.com.cn/web-api/web/system/user/loginWeb"
            
            login_data = {
                "username": self.user,
                "password": self.pwd,
                "code": None,
                "loginMethod": "account",
                "phoneNumber": None,
                "email": None
            }
            
            response = requests.post(login_url, json=login_data)
            r = response.json()
            
            if r.get("code") != 200:
                # 重试一次
                response = requests.post(login_url, json=login_data)
                r = response.json()
            
            if r.get("code") != 200:
                raise RuntimeError(f"登录失败: {r.get('msg')}")
            
            self.token = r["data"]
            self.log("Kingbase 登录成功")
            return True
            
        except Exception as e:
            self.log(f"登录异常: {str(e)}", 'ERROR')
            raise
    
    def reply(self):
        """发表回帖"""
        if not self.token:
            self.login()
        
        self.log("登录后等待3秒...")
        time.sleep(3)
        
        try:
            view_url = f"https://bbs.kingbase.com.cn/forumDetail?articleId={self.article_id}"
            view_headers = {
                "Authorization": f"Bearer {self.token}",
                "Web-Token": self.token,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0"
            }
            view_cookies = {
                "Authorization": self.token,
                "Web-Token": self.token
            }
            requests.get(view_url, headers=view_headers, cookies=view_cookies)
            
            self.log("打开帖子后等待5秒...")
            time.sleep(5)
            
            headers = {
                "Content-Type": "application/json;charset=utf-8",
                "Authorization": f"Bearer {self.token}",
                "Web-Token": self.token,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
                "Referer": f"https://bbs.kingbase.com.cn/forumDetail?articleId={self.article_id}",
                "Origin": "https://bbs.kingbase.com.cn"
            }
            
            cookies = {
                "Authorization": self.token,
                "Web-Token": self.token
            }
            
            body = {
                "articleId": self.article_id,
                "commentContent": "<p><img src=\"/UEditorPlus/dialogs/emotion/./custom_emotion/emotion_02.png\"/></p>"
            }
            
            url = "https://bbs.kingbase.com.cn/web-api/web/forum/comment"
            self.log("发送回帖内容...")
            response = requests.post(url, headers=headers, cookies=cookies, json=body)
            r = response.json()
            
            if r.get("code") != 200:
                raise RuntimeError(f"回帖失败: {r.get('msg')}")
            
            return r.get("msg", "success")
            
        except Exception as e:
            self.log(f"回帖失败: {str(e)}", 'ERROR')
            raise
    
    def run_checkin(self, reply_count=5):
        """执行签到任务"""
        self.log("=== 开始 Kingbase 论坛回帖任务 ===")
        
        results = []
        success_count = 0
        
        for idx in range(1, reply_count + 1):
            self.log(f"=== 开始第 {idx}/{reply_count} 次回帖 ===")
            
            try:
                msg = self.reply()
                log_msg = f"第{idx}/{reply_count}次回帖成功：{msg}"
                self.log(f"[成功] {log_msg}")
                results.append(f"✅ {log_msg}")
                success_count += 1
                
            except Exception as e:
                log_msg = f"第{idx}次回帖失败：{str(e)}"
                self.log(f"[失败] {log_msg}", 'ERROR')
                results.append(f"❌ {log_msg}")
            
            if idx < reply_count:
                random_wait = random.randint(10, 60)
                self.log(f"回帖后随机等待 {random_wait} 秒...")
                time.sleep(random_wait)
        
        today = bj_time().strftime("%Y-%m-%d")
        title = f"Kingbase 论坛回帖结果 - {today}"
        
        content_lines = [
            f"📊 回帖统计：成功 {success_count}/{reply_count} 次",
            "",
            "📝 详细结果："
        ]
        content_lines.extend(results)
        
        content = "\n".join(content_lines)
        
        self.log("=== 任务完成，准备推送结果 ===")
        self.send_notification(title, content)
        
        self.log(f"Kingbase 回帖任务完成，成功 {success_count}/{reply_count} 次")
        return {
            "success_count": success_count,
            "total_count": reply_count,
            "results": results
        }


def random_delay():
    delay_minutes = random.randint(0, 60)
    delay_seconds = delay_minutes * 60
    
    if delay_minutes > 0:
        from datetime import timedelta
        current_time = bj_time()
        estimated_start = current_time + timedelta(minutes=delay_minutes)
        
        print(f"🕐 随机延迟 {delay_minutes} 分钟后开始执行任务...")
        print(f"⏰ 预计开始时间: {estimated_start.strftime('%H:%M:%S')}")
        time.sleep(delay_seconds)
        print(f"✅ 延迟结束，开始执行 Kingbase 回帖任务")
    else:
        print(f"🚀 无需延迟，立即开始执行 Kingbase 回帖任务")


def main():
    """主函数"""
    try:
        random_delay()
        
        kb_users = os.environ.get("KINGBASE_USER", "").split("#")
        kb_pwds = os.environ.get("KINGBASE_PWD", "").split("#")
        pushplus_token = os.environ.get("PUSH_PLUS_TOKEN")
        article_id = os.environ.get("KINGBASE_ARTICLE_ID")
        reply_count = int(os.environ.get("KINGBASE_REPLY_CNT", "5"))
        
        if not article_id:
            print("❌ 错误：未配置 KINGBASE_ARTICLE_ID 环境变量")
            return
        
        if not kb_users or not kb_users[0]:
            print("❌ 错误：未配置 KINGBASE_USER 环境变量")
            return
        
        if not kb_pwds or not kb_pwds[0]:
            print("❌ 错误：未配置 KINGBASE_PWD 环境变量")
            return
        
        # 处理多账号情况
        for user, pwd in zip(kb_users, kb_pwds):
            if not user or not pwd:
                continue
            
            print(f"\n{'='*50}")
            print(f"开始处理账号: {user}")
            print(f"{'='*50}")
            
            client = KingbaseClient(user, pwd, article_id, pushplus_token)
            result = client.run_checkin(reply_count)
            
            print(f"\n账号 {user} 处理完成")
            print(f"成功回帖: {result['success_count']}/{result['total_count']} 次")
    
    except Exception as e:
        print(f"❌ 程序执行异常: {str(e)}")
        # 如果有推送token，发送错误通知
        if 'pushplus_token' in locals() and pushplus_token:
            try:
                error_title = "Kingbase 回帖任务异常"
                error_content = f"❌ 程序执行异常: {str(e)}"
                requests.post(
                    "http://www.pushplus.plus/send",
                    data=json.dumps({
                        "token": pushplus_token,
                        "title": error_title,
                        "content": error_content
                    }).encode('utf-8'),
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
            except:
                pass


if __name__ == "__main__":
    main()