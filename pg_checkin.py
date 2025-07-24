#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PGFans 论坛自动签到脚本
适用于青龙面板定时任务
"""

import hashlib
import json
import os
import random
import requests
import time
from datetime import datetime


def bj_time():
    """获取北京时间"""
    import pytz
    return datetime.now(pytz.timezone('Asia/Shanghai'))


def fmt_now():
    """格式化当前时间"""
    return bj_time().strftime("%Y-%m-%d %H:%M:%S")


def push_plus(token, title, content):
    """PushPlus 消息推送"""
    if not token:
        return
    
    try:
        url = "http://www.pushplus.plus/send"
        data = {
            "token": token,
            "title": title,
            "content": content,
            "template": "html"
        }
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 200:
                print(f"[推送] 消息推送成功")
            else:
                print(f"[推送] 消息推送失败: {result.get('msg')}")
        else:
            print(f"[推送] 推送请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"[推送] 推送异常: {str(e)}")


class PGFansClient:
    def __init__(self, mobile, password, pushplus_token=None):
        """初始化 PGFans 客户端"""
        self.mobile = mobile
        self.password = password
        self.pushplus_token = pushplus_token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': 'https://www.pgfans.cn',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': 'https://www.pgfans.cn/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Priority': 'u=0'
        })
        self.user_id = None
        self.sessionid = None
    
    def log(self, message):
        """记录日志"""
        print(f"[{fmt_now()}] {message}")
    
    def generate_signature(self, timestamp, action="login", **kwargs):
        """生成签名"""
        # 根据 JavaScript 代码分析得出的签名算法
        # Md5.hashStr('CYYbQyB7FdIS8xuBEwVwbBDMQKOZPMXK|' + timestamp + '|' + action)
        secret_key = "CYYbQyB7FdIS8xuBEwVwbBDMQKOZPMXK"
        
        # 时间戳需要是10位秒级时间戳
        if len(timestamp) > 10:
            timestamp = timestamp[:10]
        
        # 构造签名字符串
        sign_string = f"{secret_key}|{timestamp}|{action}"
        
        # 生成 MD5 签名
        return hashlib.md5(sign_string.encode()).hexdigest()
    
    def login(self):
        """登录 PGFans 论坛"""
        try:
            self.log("开始登录 PGFans 论坛...")
            
            # 生成时间戳（10位秒级）
            timestamp = str(int(time.time()))
            
            # 生成签名
            signature = self.generate_signature(timestamp, "login")
            
            # 登录请求数据
            login_data = {
                "timestamp": timestamp,
                "signature": signature,
                "mobile": self.mobile,
                "user_pass": self.password
            }
            
            # 发送登录请求
            login_url = "https://admin.pgfans.cn/user/User/login"
            response = self.session.post(login_url, json=login_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == "200":
                    data = result.get("data", {})
                    self.user_id = data.get("id")
                    self.sessionid = data.get("sessionid")
                    
                    self.log(f"登录成功，用户ID: {self.user_id}")
                    
                    # 执行登录验证
                    return self.check_login()
                else:
                    error_msg = result.get("message", "登录失败")
                    self.log(f"登录失败: {error_msg}")
                    return False
            else:
                self.log(f"登录请求失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"登录异常: {str(e)}")
            return False
    
    def check_login(self):
        """验证登录状态"""
        try:
            if not self.user_id or not self.sessionid:
                self.log("缺少用户ID或会话ID，无法验证登录")
                return False
            
            # 生成时间戳和签名
            timestamp = str(int(time.time()))
            signature = self.generate_signature(timestamp, "checklogin")
            
            # 验证请求数据
            check_data = {
                "timestamp": timestamp,
                "signature": signature,
                "user_id": self.user_id,
                "sessionid": self.sessionid
            }
            
            # 发送验证请求
            check_url = "https://admin.pgfans.cn/user/user/checkLogin"
            response = self.session.post(check_url, json=check_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == "200":
                    data = result.get("data", {})
                    login_status = data.get("login_status")
                    if login_status == 1:
                        self.log("登录验证成功")
                        return True
                    else:
                        self.log("登录验证失败，状态异常")
                        return False
                else:
                    error_msg = result.get("message", "验证失败")
                    self.log(f"登录验证失败: {error_msg}")
                    return False
            else:
                self.log(f"验证请求失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"登录验证异常: {str(e)}")
            return False
    
    def get_user_info(self):
        """获取用户信息，包括P豆数量"""
        try:
            if not self.user_id or not self.sessionid:
                self.log("缺少用户ID或会话ID，无法获取用户信息")
                return None
            
            # 生成时间戳和签名
            timestamp = str(int(time.time()))
            signature = self.generate_signature(timestamp, "getnewinfo")
            
            # 用户信息请求数据
            info_data = {
                "timestamp": timestamp,
                "signature": signature,
                "user_id": self.user_id,
                "sessionid": self.sessionid
            }
            
            # 发送用户信息请求
            info_url = "https://admin.pgfans.cn/user/user/getNewInfo"
            response = self.session.post(info_url, json=info_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == "200":
                    data = result.get("data", {})
                    pgdou = data.get("pgdou", 0)
                    self.log(f"当前P豆数量: {pgdou}")
                    return pgdou
                else:
                    error_msg = result.get("message", "获取用户信息失败")
                    self.log(f"获取用户信息失败: {error_msg}")
                    return None
            else:
                self.log(f"用户信息请求失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"获取用户信息异常: {str(e)}")
            return None
    
    def checkin(self):
        """执行签到"""
        try:
            # 先确保已登录
            if not self.login():
                raise RuntimeError("登录失败")
            
            self.log("开始执行签到...")
            
            # 生成时间戳和签名
            timestamp = str(int(time.time()))
            signature = self.generate_signature(timestamp, "signin")
            
            # 签到请求数据
            checkin_data = {
                "timestamp": timestamp,
                "signature": signature,
                "user_id": self.user_id
            }
            
            # 发送签到请求
            checkin_url = "https://admin.pgfans.cn/user/pgdou/signIn"
            response = self.session.post(checkin_url, json=checkin_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == "200":
                    data = result.get("data", {})
                    earned_pgdou = data.get("pgdou", 0)
                    
                    # 获取当前总P豆数量
                    total_pgdou = self.get_user_info()
                    
                    details = f"获得 {earned_pgdou} 个 PG豆"
                    if total_pgdou is not None:
                        details += f"，当前总计: {total_pgdou} 个 PG豆"
                    
                    return {
                        "message": "签到成功",
                        "details": details
                    }
                else:
                    error_msg = result.get("message", "签到失败")
                    # 检查是否已经签到
                    if "已签到" in error_msg or "重复" in error_msg:
                        # 即使已签到，也获取当前P豆数量
                        total_pgdou = self.get_user_info()
                        details = "今天已经签到过了"
                        if total_pgdou is not None:
                            details += f"，当前总计: {total_pgdou} 个 PG豆"
                        
                        return {
                            "message": "今日已签到",
                            "details": details
                        }
                    else:
                        return {
                            "message": "签到失败",
                            "details": error_msg
                        }
            else:
                return {
                    "message": "签到失败",
                    "details": f"请求失败，状态码: {response.status_code}"
                }
                
        except Exception as e:
            self.log(f"签到失败: {str(e)}")
            return {
                "message": "签到失败",
                "details": f"签到异常: {str(e)}"
            }
    
    def run_checkin(self):
        """执行签到任务"""
        self.log("=== 开始 PGFans 论坛签到任务 ===")
        
        try:
            result = self.checkin()
            
            today = bj_time().strftime("%Y-%m-%d")
            title = f"PGFans 论坛签到结果 - {today}"
            
            if isinstance(result, dict):
                message = result.get("message", "未知状态")
                details = result.get("details", "")
                
                if "成功" in message:
                    content = f"✅ {message}\n\n📝 详情：{details}"
                    self.log("签到成功")
                elif "已签到" in message:
                    content = f"ℹ️ {message}\n\n📝 详情：{details}"
                    self.log("今日已签到")
                else:
                    content = f"❌ {message}\n\n📝 详情：{details}"
                    self.log("签到失败")
            else:
                content = f"✅ 签到成功：{result}"
                self.log("签到成功")
            
            # 推送结果
            if self.pushplus_token:
                push_plus(self.pushplus_token, title, content)
            
            return result
            
        except Exception as e:
            error_msg = f"签到任务执行失败: {str(e)}"
            self.log(error_msg)
            
            today = bj_time().strftime("%Y-%m-%d")
            title = f"PGFans 论坛签到结果 - {today}"
            content = f"❌ 签到失败\n\n📝 错误信息：{error_msg}"
            
            if self.pushplus_token:
                push_plus(self.pushplus_token, title, content)
            
            return {
                "message": "签到失败",
                "details": error_msg
            }


def random_delay():
    """随机延迟"""
    delay = random.randint(1, 30)
    print(f"[延迟] 随机等待 {delay} 秒...")
    time.sleep(delay)


def main():
    """主函数"""
    try:
        # random_delay()

        pgfans_users = os.environ.get("PGFANS_USER", "").split("#")
        pgfans_pwds = os.environ.get("PGFANS_PWD", "").split("#")
        pushplus_token = os.environ.get("PUSH_PLUS_TOKEN")
        
        if not pgfans_users or not pgfans_users[0]:
            print("❌ 错误：未配置 PGFANS_USER 环境变量")
            return
        
        if not pgfans_pwds or not pgfans_pwds[0]:
            print("❌ 错误：未配置 PGFANS_PWD 环境变量")
            return
        
        # 确保用户名和密码数量匹配
        if len(pgfans_users) != len(pgfans_pwds):
            print("❌ 错误：用户名和密码数量不匹配")
            return
        
        # 处理多账号
        for i, (user, pwd) in enumerate(zip(pgfans_users, pgfans_pwds)):
            if not user or not pwd:
                print(f"❌ 跳过第 {i+1} 个账号：用户名或密码为空")
                continue
            
            print(f"\n{'='*50}")
            print(f"开始处理第 {i+1} 个账号: {user}")
            print(f"{'='*50}")
            
            try:
                client = PGFansClient(user, pwd, pushplus_token)
                result = client.run_checkin()
                print(f"第 {i+1} 个账号签到完成: {result}")
            except Exception as e:
                print(f"❌ 第 {i+1} 个账号处理失败: {str(e)}")
            
            # 多账号间隔
            if i < len(pgfans_users) - 1:
                time.sleep(random.randint(3, 8))
        
        print("\n🎉 所有账号处理完成！")
        
    except Exception as e:
        print(f"❌ 程序执行失败: {str(e)}")


if __name__ == "__main__":
    main()