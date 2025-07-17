#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TiDB 社区自动签到脚本
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


class TiDBClient:
    def __init__(self, user, pwd, pushplus_token=None):
        self.user = user
        self.pwd = pwd
        self.pushplus_token = pushplus_token
        self.user_name = user
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-hans",
            "Origin": "https://accounts.pingcap.cn",
            "Referer": "https://accounts.pingcap.cn/login?redirect_to=https%3A%2F%2Ftidb.net%2Fmember",
            "DNT": "1"
        })
    
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
        """登录 TiDB 社区"""
        try:
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-hans",
                "Origin": "https://accounts.pingcap.cn",
                "Referer": "https://accounts.pingcap.cn/login?redirect_to=https%3A%2F%2Ftidb.net%2Fmember",
                "DNT": "1"
            })
            
            self.log("开始登录 TiDB...")
            
            login_page_url = "https://accounts.pingcap.cn/login?redirect_to=https%3A%2F%2Ftidb.net%2Fmember"
            login_page = self.session.get(login_page_url)
            
            csrf_token = self.session.cookies.get("csrftoken")
            if not csrf_token:
                raise RuntimeError("CSRF 令牌获取失败")
            
            csrf_cookies = [c for c in self.session.cookies if c.name == "csrftoken"]
            if len(csrf_cookies) > 1:
                newest_csrf = sorted(csrf_cookies, key=lambda c: c.expires if c.expires else 0, reverse=True)[0]
                for c in csrf_cookies:
                    if c != newest_csrf:
                        self.session.cookies.clear(c.domain, c.path, c.name)
            
            login_url = "https://accounts.pingcap.cn/api/login/password"
            login_data = {
                "identifier": self.user,
                "password": self.pwd,
                "redirect_to": "https://tidb.net/member"
            }
            
            self.session.headers.update({
                "Content-Type": "application/json",
                "X-CSRFTOKEN": csrf_token,
                "Accept": "application/json, text/plain, */*",
                "Upgrade-Insecure-Requests": "1"
            })
            
            login_response = self.session.post(login_url, json=login_data)
            
            if login_response.status_code != 200:
                raise RuntimeError(f"登录失败，状态码: {login_response.status_code}")
            
            login_json = login_response.json()
            if login_json.get("detail") != "成功":
                raise RuntimeError(f"登录失败: {login_json}")
            
            redirect_url = "https://accounts.pingcap.cn" + login_json["data"]["redirect_to"]
            self.session.headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1"
            })
            
            redirect_response = self.session.get(redirect_url, allow_redirects=False)
            if redirect_response.status_code in (301, 302, 303, 307, 308):
                next_url = redirect_response.headers.get('Location')
                if next_url and 'tidb.net' in next_url:
                    self.session.get(next_url, allow_redirects=True)
            
            member_url = "https://tidb.net/member"
            member_response = self.session.get(member_url)
            if "登录" in member_response.text and "注册" in member_response.text:
                raise RuntimeError("登录失败，会员页面仍显示登录/注册选项")
            
            self.log("TiDB 登录成功")
            return True
            
        except Exception as e:
            self.log(f"TiDB 登录失败: {str(e)}", 'ERROR')
            raise
    
    def checkin(self):
        """执行签到"""
        try:
            self.login()
            time.sleep(2)
            
            self.log("开始签到...")
            
            checkin_url = "https://tidb.net/api/points/daily-checkin"
            
            csrf_cookies = [c for c in self.session.cookies if c.name == "csrftoken"]
            if len(csrf_cookies) > 1:
                newest_csrf = sorted(csrf_cookies, key=lambda c: c.expires if c.expires else 0, reverse=True)[0]
                for c in csrf_cookies:
                    if c != newest_csrf:
                        self.session.cookies.clear(c.domain, c.path, c.name)
                csrf_token = newest_csrf.value
            else:
                csrf_token = self.session.cookies.get("csrftoken")
            
            self.session.headers.update({
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://tidb.net/member",
                "Origin": "https://tidb.net",
                "X-CSRFTOKEN": csrf_token if csrf_token else ""
            })
            
            checkin_response = self.session.post(checkin_url)
            
            try:
                checkin_json = checkin_response.json()
            except Exception as e:
                return {
                    "message": "签到成功",
                    "note": "签到响应解析失败，但可能已成功"
                }
            
            if checkin_response.status_code == 409:
                return {
                    "message": "签到成功",
                    "continues_checkin_count": "未知",
                    "points": "未知",
                    "tomorrow_points": "未知",
                    "note": "今天已经签到过了"
                }
            elif checkin_response.status_code != 200:
                raise RuntimeError(f"签到请求失败，状态码: {checkin_response.status_code}")
            
            if checkin_json.get("detail") == "成功":
                data = checkin_json.get("data", {})
                continues_days = data.get("continues_checkin_count", 0)
                points = data.get("points", 0)
                tomorrow_points = data.get("tomorrow_points", 0)
                
                return {
                    "message": "签到成功",
                    "continues_checkin_count": continues_days,
                    "points": points,
                    "tomorrow_points": tomorrow_points
                }
            elif "already" in str(checkin_json).lower():
                return {
                    "message": "签到成功",
                    "continues_checkin_count": "未知",
                    "points": "未知",
                    "tomorrow_points": "未知",
                    "note": "今天已经签到过了"
                }
            else:
                raise RuntimeError(checkin_json.get("detail", "未知错误"))
        
        except Exception as e:
            self.log(f"TiDB 签到失败: {str(e)}", 'ERROR')
            raise
    
    def checkin_with_retry(self):
        """带重试机制的签到"""
        try:
            result = self.checkin()
            return result
        except Exception as e:
            self.log(f"第一次签到失败: {str(e)}", 'ERROR')
            
            try:
                self.log("尝试使用备用方法签到...")
                self.session.headers.update({
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                })
                result = self.checkin()
                return result
            except Exception as e2:
                self.log(f"备用方法也失败: {str(e2)}", 'ERROR')
                raise e2
    
    def run_checkin(self):
        """执行签到任务"""
        self.log("=== 开始 TiDB 社区签到任务 ===")
        
        try:
            result = self.checkin_with_retry()

            today = bj_time().strftime("%Y-%m-%d")
            title = f"TiDB 社区签到结果 - {today}"
            
            if isinstance(result, dict):
                if "message" in result and result["message"] == "签到成功":
                    if "continues_checkin_count" in result and result["continues_checkin_count"] != "未知":
                        continues_days = result.get("continues_checkin_count", 0)
                        points = result.get("points", 0)
                        tomorrow_points = result.get("tomorrow_points", 0)
                        content = f"✅ TiDB 签到成功！\n\n📊 签到统计：\n• 连续签到：{continues_days} 天\n• 今日积分：+{points} 点\n• 明日积分：+{tomorrow_points} 点"
                    else:
                        note = result.get("note", "")
                        content = f"✅ TiDB 签到成功！\n\n📝 备注：{note}"
                else:
                    content = f"✅ TiDB 签到成功：{result}"
            else:
                content = f"✅ TiDB 签到成功：{result}"
            
            self.log("签到成功")
            
        except Exception as e:
            today = bj_time().strftime("%Y-%m-%d")
            title = f"TiDB 社区签到结果 - {today}"
            content = f"❌ TiDB 签到失败：{str(e)}"
            self.log(f"签到失败: {str(e)}", 'ERROR')
        
        self.log("=== 任务完成，准备推送结果 ===")
        self.send_notification(title, content)
        
        self.log("TiDB 签到任务完成")
        return content


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
        print(f"✅ 延迟结束，开始执行 TiDB 签到任务")
    else:
        print(f"🚀 无需延迟，立即开始执行 TiDB 签到任务")


def main():
    """主函数"""
    try:
        random_delay()
        
        tidb_users = os.environ.get("TIDB_USER", "").split("#")
        tidb_pwds = os.environ.get("TIDB_PWD", "").split("#")
        pushplus_token = os.environ.get("PUSH_PLUS_TOKEN")
        
        if not tidb_users or not tidb_users[0]:
            print("❌ 错误：未配置 TIDB_USER 环境变量")
            return
        
        if not tidb_pwds or not tidb_pwds[0]:
            print("❌ 错误：未配置 TIDB_PWD 环境变量")
            return
        
        for tidb_user, tidb_pwd in zip(tidb_users, tidb_pwds):
            if not tidb_user or not tidb_pwd:
                continue
            
            print(f"\n{'='*50}")
            print(f"开始处理账号: {tidb_user}")
            print(f"{'='*50}")
            
            client = TiDBClient(tidb_user, tidb_pwd, pushplus_token)
            result = client.run_checkin()
            
            print(f"\n账号 {tidb_user} 处理完成")
            print(f"结果: {result}")
    
    except Exception as e:
        print(f"❌ 程序执行异常: {str(e)}")
        if 'pushplus_token' in locals() and pushplus_token:
            try:
                error_title = "TiDB 签到任务异常"
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