#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OceanBase 社区自动签到脚本
适用于青龙面板定时任务
"""

import random
import time
import json
import os
import requests
import pytz
import base64
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5


def bj_time():
    """获取北京时间"""
    return datetime.now(pytz.timezone('Asia/Shanghai'))


def fmt_now():
    """格式化当前时间"""
    return bj_time().strftime("%Y-%m-%d %H:%M:%S")


class OceanBaseClient:
    def __init__(self, user, pwd, pushplus_token=None):
        self.user = user
        self.pwd = pwd
        self.pushplus_token = pushplus_token
        self.user_name = user  # 用于消息推送中显示用户名
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/json"
        })
        self.public_key = None
    
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
    
    def get_public_key(self):
        """获取RSA公钥"""
        try:
            self.log("获取公钥...")
            
            public_key_url = "https://obiamweb.oceanbase.com/webapi/aciamweb/config/publicKey"
            
            headers = {
                'Host': 'obiamweb.oceanbase.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0',
                'Accept': 'application/json',
                'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                'Referer': 'https://www.oceanbase.com/',
                'Content-Type': 'application/json',
                'Origin': 'https://www.oceanbase.com',
                'DNT': '1',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Priority': 'u=4'
            }
            
            response = self.session.get(public_key_url, headers=headers)
            self.log(f"公钥接口响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                # 检查响应格式，公钥在data字段中
                if result.get('data'):
                    self.public_key = result['data']
                    self.log("获取公钥成功")
                    return self.public_key
                elif result.get('result') and result['result'].get('data'):
                    self.public_key = result['result']['data']
                    self.log("获取公钥成功")
                    return self.public_key
                else:
                    self.log(f"公钥响应格式异常: {result}", 'ERROR')
                    return None
            else:
                self.log(f"获取公钥失败，状态码: {response.status_code}", 'ERROR')
                return None
                
        except Exception as e:
            self.log(f"获取公钥异常: {str(e)}", 'ERROR')
            return None
    
    def encrypt_password(self, password, public_key):
        """使用RSA公钥加密密码"""
        try:
            self.log("开始加密密码...")
            
            # 限制密码长度为230字符（参考前端逻辑）
            if len(password) > 230:
                password = password[:230]
            
            # 解析公钥
            if public_key.startswith('-----BEGIN PUBLIC KEY-----'):
                # 如果已经是完整的PEM格式
                key = RSA.import_key(public_key)
            else:
                # 如果只是公钥内容，需要添加PEM头尾
                pem_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
                key = RSA.import_key(pem_key)
            
            # 使用PKCS1_v1_5进行加密
            cipher = PKCS1_v1_5.new(key)
            
            # 重试机制，确保加密结果长度为344（参考前端逻辑）
            for i in range(10):
                encrypted = cipher.encrypt(password.encode('utf-8'))
                encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
                
                self.log(f"第{i+1}次加密，结果长度: {len(encrypted_b64)}")
                
                # 前端期望加密结果长度为344
                if len(encrypted_b64) == 344:
                    self.log("密码加密成功")
                    return encrypted_b64
            
            # 如果10次都没有得到344长度的结果，返回最后一次的结果
            self.log(f"密码加密完成，最终长度: {len(encrypted_b64)}")
            return encrypted_b64
            
        except Exception as e:
            self.log(f"密码加密失败: {str(e)}", 'ERROR')
            return None
    
    def login(self):
        """登录OceanBase论坛"""
        try:
            self.log("开始登录...")
            
            # 第一步：访问登录页面获取初始cookie
            self.session.get("https://www.oceanbase.com/ob/login/password")
            
            # 第二步：获取RSA公钥
            public_key = self.get_public_key()
            if not public_key:
                self.log("获取公钥失败，无法继续登录", 'ERROR')
                return False
            
            # 第三步：使用公钥加密密码
            encrypted_password = self.encrypt_password(self.pwd, public_key)
            if not encrypted_password:
                self.log("密码加密失败，无法继续登录", 'ERROR')
                return False
            
            # 第四步：执行登录
            login_url = "https://obiamweb.oceanbase.com/webapi/aciamweb/login/publicLogin"
            headers = {
                'Host': 'obiamweb.oceanbase.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0',
                'Accept': 'application/json',
                'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                'Referer': 'https://www.oceanbase.com/',
                'Content-Type': 'application/json',
                'Authorization': '',
                'Security-Code': '',
                'X-Aciamweb-Tenant': '',
                'X-Aciamweb-Tenant-Id': '',
                'X-From-Aciamweb': 'true',
                'Origin': 'https://www.oceanbase.com',
                'DNT': '1',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Priority': 'u=4',
                'TE': 'trailers'
            }
            
            # 使用RSA加密后的密码
            login_data = {
                "passAccountName": self.user,
                "password": encrypted_password,  # 使用RSA加密后的密码
                "registerFrom": 0,
                "aliyunMpToken": None,
                "mpToken": None,
                "mpChannel": None
            }
            
            response = self.session.post(login_url, json=login_data, headers=headers)
            
            self.log(f"登录响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                # 检查登录是否成功，从抓包看成功时data字段会有内容
                if result.get('data') and isinstance(result['data'], dict):
                    # 第五步：获取token信息
                    token_url = "https://webapi.oceanbase.com/api/links/token"
                    token_headers = {
                        'Host': 'webapi.oceanbase.com',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0',
                        'Accept': 'application/json',
                        'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                        'Referer': 'https://www.oceanbase.com/',
                        'Content-Type': 'application/json',
                        'Authorization': '',
                        'Security-Code': '',
                        'X-Aciamweb-Tenant': '',
                        'X-Aciamweb-Tenant-Id': '',
                        'X-From-Aciamweb': 'true',
                        'Origin': 'https://www.oceanbase.com',
                        'DNT': '1',
                        'Sec-Fetch-Dest': 'empty',
                        'Sec-Fetch-Mode': 'cors',
                        'Sec-Fetch-Site': 'same-site',
                        'Priority': 'u=4',
                        'TE': 'trailers'
                    }
                    
                    token_response = self.session.post(token_url, json={}, headers=token_headers)
                    self.log(f"Token响应状态码: {token_response.status_code}")
                    
                    if token_response.status_code == 200:
                        token_result = token_response.json()
                        if token_result.get('success'):
                            self.log("登录成功")
                            return True
                    
                    self.log("登录成功但获取token失败")
                    return True
                else:
                    self.log(f"登录失败: {result}", 'ERROR')
                    return False
            else:
                self.log(f"登录请求失败，状态码: {response.status_code}", 'ERROR')
                return False
                
        except Exception as e:
            self.log(f"登录异常: {str(e)}", 'ERROR')
            return False
    
    def checkin(self):
        """执行签到操作"""
        try:
            self.log("开始签到...")

            # 第一步：登录
            try:
                login_success = self.login()
                if not login_success:
                    return {
                        "message": "签到失败",
                        "details": "登录失败"
                    }
            except Exception as e:
                self.log(f"签到时登录异常: {str(e)}", 'ERROR')
                return {
                    "message": "签到失败",
                    "details": "登录异常"
                }

            time.sleep(2)

            # 第二步：执行签到
            checkin_url = "https://openwebapi.oceanbase.com/api/integral/signUp/insertOrUpdateSignUp"
            checkin_headers = {
                'Host': 'openwebapi.oceanbase.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0',
                'Accept': 'application/json',
                'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                'Referer': 'https://open.oceanbase.com/user/coin',
                'Content-Type': 'application/json; charset=utf-8',
                'Origin': 'https://open.oceanbase.com',
                'DNT': '1',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Priority': 'u=0'
            }

            checkin_response = self.session.post(checkin_url, json={}, headers=checkin_headers)
            self.log(f"签到接口响应状态码: {checkin_response.status_code}")

            # 第三步：查询签到状态
            query_url = "https://openwebapi.oceanbase.com/api/integral/signUp/queryUserSignUpDays"
            query_headers = {
                'Host': 'openwebapi.oceanbase.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0',
                'Accept': 'application/json',
                'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
                'Referer': 'https://open.oceanbase.com/user/coin',
                'Content-Type': 'application/json; charset=utf-8',
                'Origin': 'https://open.oceanbase.com',
                'DNT': '1',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'Priority': 'u=0'
            }

            query_response = self.session.post(query_url, json={}, headers=query_headers)
            self.log(f"最终查询接口响应状态码: {query_response.status_code}")
            
            if checkin_response.status_code == 200:
                checkin_result = checkin_response.json()
                if checkin_result.get('code') == 200:
                    if query_response.status_code == 200:
                        final_result = query_response.json()
                        if final_result.get('code') == 200 and final_result.get('data'):
                            data = final_result['data']
                            total_days = data.get('currentTotalDays', 0)
                            sign_flag = data.get('signUpFlag', 0)
                            
                            if sign_flag == 1:
                                return {
                                    "message": "签到成功",
                                    "details": f"OceanBase 签到成功，累计签到 {total_days} 天"
                                }
                            else:
                                return {
                                    "message": "签到失败",
                                    "details": "OceanBase 签到失败，签到状态异常"
                                }
                    
                    return {
                        "message": "签到成功",
                        "details": "OceanBase 签到成功"
                    }
                elif checkin_result.get('code') == 500 and "已签到" in str(checkin_result.get('message', '')):
                    if query_response.status_code == 200:
                        final_result = query_response.json()
                        if final_result.get('code') == 200 and final_result.get('data'):
                            data = final_result['data']
                            total_days = data.get('currentTotalDays', 0)
                            sign_flag = data.get('signUpFlag', 0)
                            
                            if sign_flag == 1:
                                return {
                                    "message": "今日已签到",
                                    "details": f"累计签到 {total_days} 天"
                                }
                            else:
                                return {
                                    "message": "签到失败",
                                    "details": "OceanBase 签到失败，签到状态异常"
                                }
                    return {
                        "message": "签到成功",
                        "details": "今日已签到"
                    }
                else:
                    error_msg = checkin_result.get('message', '签到失败')
                    return {
                        "message": "签到失败",
                        "details": f"OceanBase 签到失败: {error_msg}"
                    }
            else:
                return {
                    "message": "签到失败",
                    "details": f"OceanBase 签到请求失败，状态码: {checkin_response.status_code}"
                }
                
        except Exception as e:
            self.log(f"签到失败: {str(e)}", 'ERROR')
            return {
                "message": "签到失败",
                "details": f"OceanBase 签到异常: {str(e)}"
            }
    
    def run_checkin(self):
        """执行签到任务"""
        self.log("=== 开始 OceanBase 社区签到任务 ===")
        
        try:
            result = self.checkin()
            
            today = bj_time().strftime("%Y-%m-%d")
            title = f"OceanBase 社区签到结果 - {today}"
            
            if isinstance(result, dict):
                message = result.get("message", "未知状态")
                details = result.get("details", "")
                
                if "成功" in message or "已签到" in message:
                    content = f"✅ {message}\n\n📝 详情：{details}"
                    self.log("签到成功")
                else:
                    content = f"❌ {message}\n\n📝 详情：{details}"
                    self.log(f"签到失败: {details}", 'ERROR')
            else:
                content = f"✅ OceanBase 签到成功：{result}"
                self.log("签到成功")
            
        except Exception as e:
            today = bj_time().strftime("%Y-%m-%d")
            title = f"OceanBase 社区签到结果 - {today}"
            content = f"❌ OceanBase 签到失败：{str(e)}"
            self.log(f"签到失败: {str(e)}", 'ERROR')
        
        self.log("=== 任务完成，准备推送结果 ===")
        self.send_notification(title, content)
        
        self.log("OceanBase 签到任务完成")
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
        print(f"✅ 延迟结束，开始执行 OceanBase 签到任务")
    else:
        print(f"🚀 无需延迟，立即开始执行 OceanBase 签到任务")


def main():
    """主函数"""
    try:
        random_delay()
        
        ob_users = os.environ.get("OCEANBASE_USER", "").split("#")
        ob_pwds = os.environ.get("OCEANBASE_PWD", "").split("#")
        pushplus_token = os.environ.get("PUSH_PLUS_TOKEN")
        
        if not ob_users or not ob_users[0]:
            print("❌ 错误：未配置 OCEANBASE_USER 环境变量")
            return
        
        if not ob_pwds or not ob_pwds[0]:
            print("❌ 错误：未配置 OCEANBASE_PWD 环境变量")
            return
        
        # 处理多账号情况
        for ob_user, ob_pwd in zip(ob_users, ob_pwds):
            if not ob_user or not ob_pwd:
                continue
            
            print(f"\n{'='*50}")
            print(f"开始处理账号: {ob_user}")
            print(f"{'='*50}")
            
            client = OceanBaseClient(ob_user, ob_pwd, pushplus_token)
            result = client.run_checkin()
            
            print(f"\n账号 {ob_user} 处理完成")
            print(f"结果: {result}")
    
    except Exception as e:
        print(f"❌ 程序执行异常: {str(e)}")
        if 'pushplus_token' in locals() and pushplus_token:
            try:
                error_title = "OceanBase 签到任务异常"
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