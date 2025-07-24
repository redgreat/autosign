#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
墨天轮论坛自动签到脚本

功能：
1. 模拟登录墨天轮论坛
2. 执行每日签到
3. 查询用户详情获取总墨值
4. 支持 PushPlus 消息推送

环境变量：
- MODB_USER: 墨天轮用户名（手机号）
- MODB_PWD: 墨天轮密码
- PUSH_PLUS_TOKEN: PushPlus推送token（可选）
"""

import os
import sys
import time
import json
import uuid
import base64
import hashlib
import requests
from datetime import datetime, timezone, timedelta
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes


def fmt_now():
    """格式化当前时间"""
    return datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')


class MoDBClient:
    """墨天轮论坛客户端"""
    
    def __init__(self, user, pwd):
        self.user = user
        self.pwd = pwd
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })
        self.base_url = 'https://www.modb.pro/api/'
        self.user_info = None
        
    def log(self, message):
        """记录日志"""
        print(f"[{fmt_now()}] {message}")
        
    def generate_uuid(self):
        """生成UUID（模拟JavaScript中的UUID生成逻辑）"""
        chars = "0123456789abcdefghijklmnopqrstuvwxyz"
        uuid_chars = []
        
        for i in range(36):
            if i in [8, 13, 18, 23]:
                uuid_chars.append('-')
            elif i == 14:
                uuid_chars.append('4')
            elif i == 19:
                # (3 & random) | 8
                random_char = chars[int(time.time() * 1000000) % 16]
                uuid_chars.append(chars[(3 & ord(random_char)) | 8])
            else:
                uuid_chars.append(chars[int(time.time() * 1000000 + i) % 16])
                
        return ''.join(uuid_chars)
        
    def aes_encrypt(self, plaintext, key, iv):
        """AES加密（模拟JavaScript中的AES加密）"""
        try:
            # 确保key和iv的长度
            key = key.ljust(16, '\0')[:16].encode('utf-8')
            iv = iv.ljust(16, '\0')[:16].encode('utf-8')
            
            # 创建AES加密器
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # 填充明文
            padded_text = pad(plaintext.encode('utf-8'), AES.block_size)
            
            # 加密
            encrypted = cipher.encrypt(padded_text)
            
            # 返回base64编码的结果
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            self.log(f"AES加密失败: {str(e)}")
            return None
            
    def get_timestamp_info(self):
        """获取时间戳信息"""
        try:
            url = self.base_url + 'env/clock'
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('operateCallBackObj')
            
            self.log(f"获取时间戳信息失败: {response.text}")
            return None
            
        except Exception as e:
            self.log(f"获取时间戳信息异常: {str(e)}")
            return None
            
    def generate_req_key(self):
        """生成reqKey（模拟JavaScript中的reqKey生成逻辑）"""
        try:
            # 获取时间戳信息
            timestamp_info = self.get_timestamp_info()
            if not timestamp_info:
                return None
                
            # 生成UUID
            uuid_str = self.generate_uuid()
            
            # 构造加密内容
            v = f"{uuid_str}:"
            c = str(timestamp_info)  # 时间戳信息
            
            # AES加密参数（从JavaScript代码中提取）
            key = "emcs-app-request"  # n
            iv = "xqgb1vda11s0e94g"   # r
            
            # 执行AES加密
            req_key = self.aes_encrypt(v + c, key, iv)
            
            if req_key:
                self.log(f"生成reqKey成功")
                return req_key
            else:
                self.log("生成reqKey失败")
                return None
                
        except Exception as e:
            self.log(f"生成reqKey异常: {str(e)}")
            return None
            
    def login(self):
        """登录"""
        try:
            self.log("开始登录...")
            
            url = self.base_url + 'login'
            
            login_data = {
                'phoneNum': self.user,
                'password': self.pwd
            }
            
            headers = {
                'Content-Type': 'application/json;charset=UTF-8',
                'Referer': 'https://www.modb.pro/login'
            }
            
            response = self.session.post(url, json=login_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.user_info = data.get('operateCallBackObj', {})
                    
                    # 从响应头中提取token
                    token = response.headers.get('Authorization')
                    
                    if token:
                        # 设置Authorization头
                        self.session.headers['Authorization'] = token
                        return True
                        
            return False
                
        except Exception as e:
            self.log(f"登录异常: {str(e)}")
            return False
            
    def checkin(self):
        """执行签到"""
        try:
            # 先确保已登录
            if not self.login():
                return {
                    'success': False,
                    'message': '登录失败',
                    'total_points': 0
                }
                
            self.log("开始执行签到...")
            
            # 生成reqKey
            req_key = self.generate_req_key()
            if not req_key:
                return {
                    'success': False,
                    'message': '生成reqKey失败',
                    'total_points': 0
                }
                
            # 签到请求
            url = self.base_url + 'user/dailyCheck'
            
            checkin_data = {
                'reqKey': req_key
            }
            
            headers = {
                'Content-Type': 'application/json;charset=UTF-8',
                'Referer': 'https://www.modb.pro/u/checkin'
            }
            
            response = self.session.post(url, json=checkin_data, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                # 获取用户详情以获取总墨值
                user_detail = self.get_user_detail()
                total_points = user_detail.get('point', 0) if user_detail else 0
                
                if data.get('success'):
                    result = {
                        'success': True,
                        'message': '签到成功',
                        'total_points': total_points,
                        'checkin_info': data.get('operateCallBackObj', {})
                    }
                    
                    self.log(f"签到成功！当前总墨值: {total_points}")
                    return result
                else:
                    error_msg = data.get('operateMessage', '未知错误')
                    if '已经签到' in error_msg or '重复签到' in error_msg or '签过到' in error_msg:
                        # 已经签到过了，也算作成功
                        result = {
                            'success': True,
                            'message': '签到成功',
                            'total_points': total_points,
                            'already_checked': True
                        }
                        
                        self.log(f"今天已经签到过了，当前总墨值: {total_points}")
                        return result
                    else:
                        return {
                            'success': False,
                            'message': f'签到失败: {error_msg}',
                            'total_points': total_points
                        }
            else:
                return {
                    'success': False,
                    'message': f'签到请求失败，状态码: {response.status_code}',
                    'total_points': 0
                }
                
        except Exception as e:
            self.log(f"签到失败: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'total_points': 0
            }
            
    def get_user_detail(self):
        """获取用户详情"""
        try:
            url = self.base_url + 'user/detail'
            
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                # 直接返回用户详情数据，其中包含 point 字段
                return data
                    
            return None
            
        except Exception as e:
            self.log(f"获取用户详情失败: {str(e)}")
            return None
            
    def send_notification(self, title, content):
        """发送PushPlus通知"""
        token = os.getenv('PUSH_PLUS_TOKEN')
        if not token:
            self.log("未配置PUSH_PLUS_TOKEN，跳过消息推送")
            return
            
        try:
            url = 'http://www.pushplus.plus/send'
            data = {
                'token': token,
                'title': title,
                'content': content,
                'template': 'html'
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                pass
            
        except Exception as e:
            self.log(f"消息推送异常: {str(e)}")
            
    def run_checkin(self):
        """执行签到任务"""
        self.log("=== 开始墨天轮论坛签到任务 ===")
        
        try:
            result = self.checkin()
            
            today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
            title = f"墨天轮论坛签到结果 - {today}"
            
            if result.get('success'):
                total_points = result.get('total_points', 0)
                if result.get('already_checked'):
                    content = f"✅ 墨天轮签到成功！\n　　• 今天已经签到过了\n　　• 当前总墨值：{total_points}"
                else:
                    checkin_info = result.get('checkin_info', {})
                    content = f"✅ 墨天轮签到成功！\n　　• 当前总墨值：{total_points}"
                    
                    # 如果有签到奖励信息，添加到内容中
                    if checkin_info:
                        reward = checkin_info.get('reward', '')
                        if reward:
                            content += f"\n　　• 签到奖励：{reward}"
                            
                self.log(content.replace('\n', ' '))
            else:
                content = f"❌ 墨天轮签到失败：{result.get('message', '未知错误')}"
                self.log(content)
                
        except Exception as e:
            today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
            title = f"墨天轮论坛签到结果 - {today}"
            content = f"❌ 墨天轮签到失败：{str(e)}"
            self.log(f"签到失败: {str(e)}")
            
        self.log("=== 任务完成，准备推送结果 ===")
        self.send_notification(title, content)
        
        self.log("墨天轮签到任务完成")
        return content


def main():
    """主函数"""
    try:
        # 获取环境变量，支持多账号（用#分隔）
        modb_users = os.getenv('MODB_USER', '').split('#')
        modb_pwds = os.getenv('MODB_PWD', '').split('#')
        
        if not modb_users or not modb_users[0]:
            print("❌ 错误：未配置 MODB_USER 环境变量")
            sys.exit(1)
        
        if not modb_pwds or not modb_pwds[0]:
            print("❌ 错误：未配置 MODB_PWD 环境变量")
            sys.exit(1)
        
        # 确保用户名和密码数量匹配
        if len(modb_users) != len(modb_pwds):
            print("❌ 错误：用户名和密码数量不匹配")
            sys.exit(1)
        
        # 处理多账号
        for i, (user, pwd) in enumerate(zip(modb_users, modb_pwds)):
            if not user or not pwd:
                print(f"❌ 跳过第 {i+1} 个账号：用户名或密码为空")
                continue
            
            print(f"\n{'='*50}")
            print(f"开始处理第 {i+1} 个账号: {user}")
            print(f"{'='*50}")
            
            try:
                client = MoDBClient(user, pwd)
                result = client.run_checkin()
                print(f"第 {i+1} 个账号签到完成: {result}")
            except Exception as e:
                print(f"❌ 第 {i+1} 个账号处理失败: {str(e)}")
            
            # 多账号间隔
            if i < len(modb_users) - 1:
                time.sleep(3)
        
        print("\n🎉 所有账号处理完成！")
        
    except Exception as e:
        print(f"❌ 程序执行失败: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()