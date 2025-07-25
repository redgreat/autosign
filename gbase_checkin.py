#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gbase 论坛自动签到脚本
适用于青龙面板定时任务
"""

import random
import time
import json
import os
import requests
import pytz
from datetime import datetime
from urllib.parse import urlencode


def bj_time():
    """获取北京时间"""
    return datetime.now(pytz.timezone('Asia/Shanghai'))


def fmt_now():
    """格式化当前时间"""
    return bj_time().strftime("%Y-%m-%d %H:%M:%S")


class GbaseClient:
    def __init__(self, username, password, pushplus_token=None):
        self.username = username
        self.password = password
        self.pushplus_token = pushplus_token
        self.session = requests.Session()
        self.csrf_token = None
        self.gbase_satoken = None
        
        # 设置通用请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': '1',
            'Connection': 'keep-alive',
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
        
        # 在标题和内容中加入用户名称
        title_with_user = "[{}] {}".format(self.username, title)
        content_with_user = "👤 账号: {}\n\n{}".format(self.username, content)
        
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
    
    def get_csrf_token(self):
        """获取CSRF Token"""
        try:
            self.log("获取CSRF Token...")
            url = "https://www.gbase.cn/user-center/api/auth/csrf"
            
            headers = {
                'Referer': 'https://www.gbase.cn/user-center/login',
                'Content-Type': 'application/json',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Priority': 'u=4'
            }
            
            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            self.csrf_token = data.get('csrfToken')
            
            if not self.csrf_token:
                raise RuntimeError("获取CSRF Token失败")
            
            self.log(f"✅ 获取CSRF Token成功: {self.csrf_token[:20]}...")
            return True
            
        except Exception as e:
            self.log(f"获取CSRF Token失败: {str(e)}", 'ERROR')
            raise
    
    def login(self):
        """登录 Gbase 论坛"""
        try:
            self.log("尝试登录 Gbase...")
            
            # 先获取CSRF Token
            self.get_csrf_token()
            
            # 登录请求
            login_url = "https://www.gbase.cn/user-center/api/auth/callback/credentials"
            
            headers = {
                'Referer': 'https://www.gbase.cn/user-center/login',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://www.gbase.cn',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Priority': 'u=4'
            }
            
            # 构造登录数据
            login_data = {
                'type': 'undefined',
                'username': self.username,
                'password': self.password,
                'verifyEmail': '',
                'redirect': 'true',
                'callbackUrl': '/user-center',
                'csrfToken': self.csrf_token,
                'json': 'true'
            }
            
            # 发送登录请求
            response = self.session.post(
                login_url, 
                data=urlencode(login_data),
                headers=headers,
                allow_redirects=False
            )
            
            # 检查登录响应状态
            if response.status_code not in [200, 302]:
                raise RuntimeError(f"登录请求失败，状态码: {response.status_code}")
            
            # 检查登录是否成功 - 通过检查cookies中的session token
            session_token = None
            for cookie in self.session.cookies:
                if 'session-token' in cookie.name:
                    session_token = cookie.value
                    break
                elif 'gbase-satoken' in cookie.name:
                    self.gbase_satoken = cookie.value
            
            if not session_token and not self.gbase_satoken:
                # 尝试从响应中获取token信息
                if response.status_code in [302, 200]:
                    self.log("登录请求已发送，检查认证状态...")
                    # 可能需要额外的验证步骤
                else:
                    raise RuntimeError(f"登录失败，状态码: {response.status_code}")
            
            # 从cookies中提取gbase-satoken
            for cookie in self.session.cookies:
                if cookie.name == 'gbase-satoken':
                    self.gbase_satoken = cookie.value
                    break
            
            if self.gbase_satoken:
                self.log("✅ Gbase 登录成功")
                return True
            else:
                # 尝试通过session API获取accessToken
                self.log("尝试通过session API获取accessToken...")
                time.sleep(2)
                
                # 调用session API获取accessToken
                session_api_url = "https://www.gbase.cn/user-center/api/auth/session"
                headers = {
                    'Referer': 'https://www.gbase.cn/user-center/membership/points',
                    'Content-Type': 'application/json',
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                    'Priority': 'u=4'
                }
                
                response = self.session.get(session_api_url, headers=headers)
                
                # 检查session API响应
                if response.status_code != 200:
                    self.log(f"Session API请求失败，状态码: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        session_data = response.json()
                        access_token = session_data.get('accessToken')
                        if access_token:
                            self.gbase_satoken = access_token
                            self.log(f"✅ 通过Session API获取到accessToken: {access_token[:20]}...")
                            self.log("✅ Gbase 登录成功")
                            return True
                        else:
                            self.log("Session API响应中未找到accessToken")
                    except Exception as e:
                        self.log(f"解析Session API响应失败: {str(e)}")
                
                raise RuntimeError("登录失败：未获取到有效的认证token")
            
        except Exception as e:
            self.log(f"登录异常: {str(e)}", 'ERROR')
            raise
    
    def get_user_info(self):
        """获取用户信息"""
        try:
            self.log("获取用户信息...")
            
            # 用户信息请求
            user_info_url = "https://www.gbase.cn/gbase-gateway/gbase-community-service/account/me"
            
            headers = {
                'Referer': 'https://www.gbase.cn/user-center/membership/points',
                'Content-Type': 'application/json; charset=utf-8',
                'gbase-satoken': f'Bearer {self.gbase_satoken}',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Priority': 'u=4'
            }
            
            response = self.session.get(user_info_url, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 200:
                data = result.get('data', {})
                user_info = {
                    'account': data.get('account', ''),
                    'charmPoints': data.get('charmPoints', 0),
                    'checkInContinuousDays': data.get('checkInContinuousDays', 0),
                    'checkInCumulativeDays': data.get('checkInCumulativeDays', 0),
                    'checkInLastTime': data.get('checkInLastTime', ''),
                    'userLevelName': data.get('userLevelName', '')
                }
                self.log(f"✅ 获取用户信息成功: 吉币{user_info['charmPoints']}，连续签到{user_info['checkInContinuousDays']}天")
                return user_info
            else:
                self.log(f"获取用户信息失败: {result.get('msg', '未知错误')}")
                return None
                
        except Exception as e:
            self.log(f"获取用户信息异常: {str(e)}", 'ERROR')
            return None
    
    def checkin(self):
        """执行签到"""
        if not self.gbase_satoken:
            self.login()
        
        try:
            self.log("开始执行签到...")
            
            # 签到请求
            checkin_url = "https://www.gbase.cn/gbase-gateway/gbase-community-service/check-in/add"
            
            headers = {
                'Referer': 'https://www.gbase.cn/user-center/membership/check-in',
                'Content-Type': 'application/json; charset=utf-8',
                'gbase-satoken': f'Bearer {self.gbase_satoken}',
                'Origin': 'https://www.gbase.cn',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Priority': 'u=4'
            }
            
            # 发送签到请求
            response = self.session.post(
                checkin_url,
                json={},
                headers=headers
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 200:
                msg = result.get('msg', '签到成功')
                self.log(f"✅ 签到成功: {msg}")
                return msg
            else:
                error_msg = result.get('msg', '签到失败')
                if '已签到' in error_msg or '重复' in error_msg:
                    self.log(f"ℹ️ {error_msg}")
                    return error_msg
                else:
                    raise RuntimeError(f"签到失败: {error_msg}")
            
        except Exception as e:
            self.log(f"签到失败: {str(e)}", 'ERROR')
            raise
    
    def run_checkin(self):
        """执行签到任务"""
        self.log("=== 开始 Gbase 论坛签到任务 ===")
        
        try:
            result = self.checkin()
            
            # 获取用户信息
            user_info = self.get_user_info()
            
            today = bj_time().strftime("%Y-%m-%d")
            title = f"Gbase 论坛签到结果 - {today}"
            
            # 构建推送内容
            if user_info:
                content = f"✅ 签到成功: {result}\n\n" + \
                         f"📊 账号信息:\n" + \
                         f"• 账号: {user_info['account']}\n" + \
                         f"• 总吉币: {user_info['charmPoints']}\n" + \
                         f"• 连续签到: {user_info['checkInContinuousDays']} 天\n" + \
                         f"• 累计签到: {user_info['checkInCumulativeDays']} 天\n" + \
                         f"• 等级: {user_info['userLevelName']}\n" + \
                         f"• 最后签到: {user_info['checkInLastTime']}"
            else:
                content = f"✅ 签到成功: {result}"
            
            self.log("=== 任务完成，准备推送结果 ===")
            self.send_notification(title, content)
            
            self.log("Gbase 签到任务完成")
            return {
                "success": True,
                "message": result,
                "user_info": user_info
            }
            
        except Exception as e:
            error_msg = str(e)
            self.log(f"签到任务失败: {error_msg}", 'ERROR')
            
            today = bj_time().strftime("%Y-%m-%d")
            title = f"Gbase 论坛签到失败 - {today}"
            content = f"❌ 签到失败: {error_msg}"
            
            self.send_notification(title, content)
            
            return {
                "success": False,
                "message": error_msg
            }


def random_delay():
    """随机延迟"""
    delay_minutes = random.randint(0, 60)
    delay_seconds = delay_minutes * 60
    
    if delay_minutes > 0:
        from datetime import timedelta
        current_time = bj_time()
        estimated_start = current_time + timedelta(minutes=delay_minutes)
        
        print(f"🕐 随机延迟 {delay_minutes} 分钟后开始执行任务...")
        print(f"⏰ 预计开始时间: {estimated_start.strftime('%H:%M:%S')}")
        time.sleep(delay_seconds)
        print(f"✅ 延迟结束，开始执行 Gbase 签到任务")
    else:
        print(f"🚀 无需延迟，立即开始执行 Gbase 签到任务")


def main():
    """主函数"""
    try:
        # random_delay()
        
        # 获取环境变量
        gbase_users = os.environ.get("GBASE_USER", "").split("#")
        gbase_pwds = os.environ.get("GBASE_PWD", "").split("#")
        pushplus_token = os.environ.get("PUSH_PLUS_TOKEN")
        
        if not gbase_users or not gbase_users[0]:
            print("❌ 错误：未配置 GBASE_USER 环境变量")
            return
        
        if not gbase_pwds or not gbase_pwds[0]:
            print("❌ 错误：未配置 GBASE_PWD 环境变量")
            return
        
        # 处理多账号情况
        for user, pwd in zip(gbase_users, gbase_pwds):
            if not user or not pwd:
                continue
            
            print(f"\n{'='*50}")
            print(f"开始处理账号: {user}")
            print(f"{'='*50}")
            
            client = GbaseClient(user, pwd, pushplus_token)
            result = client.run_checkin()
            
            print(f"\n账号 {user} 处理完成")
            if result['success']:
                print(f"✅ 签到成功: {result['message']}")
            else:
                print(f"❌ 签到失败: {result['message']}")
            
            # 多账号间随机等待
            if len(gbase_users) > 1:
                wait_time = random.randint(30, 120)
                print(f"账号间等待 {wait_time} 秒...")
                time.sleep(wait_time)
    
    except Exception as e:
        print(f"❌ 程序执行异常: {str(e)}")
        # 如果有推送token，发送错误通知
        if 'pushplus_token' in locals() and pushplus_token:
            try:
                error_title = "Gbase 签到任务异常"
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