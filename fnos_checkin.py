#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞牛论坛自动签到脚本

功能：
1. 模拟登录飞牛论坛
2. 执行每日签到
3. 支持多账号
4. 支持 PushPlus 消息推送

环境变量：
- FNOS_USER: 飞牛论坛用户名（多账号用#分隔）
- FNOS_PWD: 飞牛论坛密码（多账号用#分隔）
- PUSH_PLUS_TOKEN: PushPlus推送token（可选）
"""

import os
import sys
import re
import time
import requests
import base64
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, parse_qs, urlparse

try:
    import ddddocr
except ImportError:
    ddddocr = None
    print("警告: ddddocr库未安装，无法识别验证码。请运行: pip install ddddocr")


def fmt_now():
    """格式化当前时间"""
    return datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')


class FnOSClient:
    """飞牛论坛客户端"""
    
    def __init__(self, user, pwd, pushplus_token=None):
        self.user = user
        self.pwd = pwd
        self.pushplus_token = pushplus_token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.base_url = 'https://club.fnnas.com/'
        self.is_logged_in = False
        
    def log(self, message):
        """记录日志"""
        print(f"[{fmt_now()}] {message}")
        
    def get_login_page(self):
        """获取登录页面，提取formhash"""
        try:
            url = urljoin(self.base_url, 'member.php?mod=logging&action=login')
            response = self.session.get(url)
            
            if response.status_code == 200:
                # 提取formhash
                formhash_match = re.search(r'name="formhash"\s+value="([^"]+)"', response.text)
                if formhash_match:
                    formhash = formhash_match.group(1)
                    self.log(f"获取formhash成功: {formhash}")
                    return formhash
                else:
                    self.log("未找到formhash")
                    return None
            else:
                self.log(f"获取登录页面失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"获取登录页面异常: {str(e)}")
            return None
            
    def get_captcha_code(self, captcha_url):
        """获取并识别验证码"""
        try:
            if not ddddocr:
                self.log("ddddocr库未安装，无法识别验证码")
                return None
                
            self.log(f"获取验证码图片: {captcha_url}")
            
            headers = {
                'Referer': urljoin(self.base_url, 'member.php?mod=logging&action=login'),
                'Accept': 'image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            response = self.session.get(captcha_url, headers=headers)
            
            if response.status_code == 200:
                # 使用ddddocr识别验证码
                ocr = ddddocr.DdddOcr(show_ad=False)
                captcha_text = ocr.classification(response.content)
                
                self.log(f"验证码识别结果: {captcha_text}")
                return captcha_text
            else:
                self.log(f"获取验证码图片失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"验证码识别异常: {str(e)}")
            return None
            
    def login(self):
        """登录"""
        try:
            self.log("开始登录...")
            
            # 获取formhash
            formhash = self.get_login_page()
            if not formhash:
                return False
                
            # 构造登录数据
            login_data = {
                'formhash': formhash,
                'referer': urljoin(self.base_url, 'portal.php'),
                'username': self.user,
                'password': self.pwd,
                'questionid': '0',
                'answer': '',
                'cookietime': '2592000'
            }
            
            # 登录请求
            login_url = urljoin(self.base_url, 'member.php?mod=logging&action=login&loginsubmit=yes&loginhash=LP7ic&inajax=1')
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': self.base_url.rstrip('/'),
                'Referer': urljoin(self.base_url, 'member.php?mod=logging&action=login'),
                'Sec-Fetch-Dest': 'iframe',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1'
            }
            
            response = self.session.post(login_url, data=login_data, headers=headers)
            
            if response.status_code == 200:
                response_text = response.text
                
                # 检查是否需要验证码
                if '请输入验证码' in response_text:
                    self.log("登录需要验证码，尝试识别验证码")
                    
                    # 提取auth参数和验证码URL
                    auth_match = re.search(r'auth=([^&"]+)', response_text)
                    if not auth_match:
                        self.log("未找到auth参数")
                        return False
                        
                    auth = auth_match.group(1)
                    self.log(f"获取auth参数: {auth}")
                    
                    # 访问验证码登录页面获取验证码URL
                    captcha_login_url = urljoin(self.base_url, f'member.php?mod=logging&action=login&auth={auth}&referer=https%3A%2F%2Fclub.fnnas.com%2F&cookietime=1')
                    captcha_response = self.session.get(captcha_login_url)
                    
                    if captcha_response.status_code != 200:
                        self.log("获取验证码页面失败")
                        return False
                        
                    # 提取验证码图片URL
                    captcha_match = re.search(r'misc\.php\?mod=seccode&update=\d+&idhash=([^"&]+)', captcha_response.text)
                    if not captcha_match:
                        self.log("未找到验证码图片URL")
                        return False
                        
                    idhash = captcha_match.group(1)
                    captcha_url = urljoin(self.base_url, f'misc.php?mod=seccode&update={int(time.time() * 1000)}&idhash={idhash}')
                    
                    # 识别验证码
                    captcha_code = self.get_captcha_code(captcha_url)
                    if not captcha_code:
                        self.log("验证码识别失败")
                        return False
                        
                    # 重新获取formhash（验证码页面的）
                    formhash_match = re.search(r'name="formhash"\s+value="([^"]+)"', captcha_response.text)
                    if formhash_match:
                        formhash = formhash_match.group(1)
                        self.log(f"获取新的formhash: {formhash}")
                    else:
                        self.log("未找到新的formhash")
                        return False
                        
                    # 构造带验证码的登录数据
                    login_data_with_captcha = {
                        'formhash': formhash,
                        'referer': urljoin(self.base_url, 'portal.php'),
                        'username': self.user,
                        'password': self.pwd,
                        'questionid': '0',
                        'answer': '',
                        'cookietime': '2592000',
                        'seccodeverify': captcha_code
                    }
                    
                    # 重新登录
                    captcha_login_submit_url = urljoin(self.base_url, 'member.php?mod=logging&action=login&loginsubmit=yes&loginhash=LP7ic&inajax=1')
                    captcha_headers = headers.copy()
                    captcha_headers['Referer'] = captcha_login_url
                    
                    captcha_login_response = self.session.post(captcha_login_submit_url, data=login_data_with_captcha, headers=captcha_headers)
                    
                    if captcha_login_response.status_code == 200:
                        captcha_response_text = captcha_login_response.text
                        
                        # 检查登录是否成功
                        if 'succeedhandle_' in captcha_response_text or '欢迎您回来' in captcha_response_text:
                            self.log("验证码登录成功")
                            self.is_logged_in = True
                            return True
                        else:
                            self.log(f"验证码登录失败: {captcha_response_text[:200]}")
                            return False
                    else:
                        self.log(f"验证码登录请求失败，状态码: {captcha_login_response.status_code}")
                        return False
                    
                # 检查登录是否成功
                if 'succeedhandle_' in response_text or '欢迎您回来' in response_text:
                    self.log("登录成功")
                    self.is_logged_in = True
                    return True
                else:
                    self.log(f"登录失败: {response_text[:200]}")
                    return False
            else:
                self.log(f"登录请求失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"登录异常: {str(e)}")
            return False
            
    def get_sign_page(self):
        """获取签到页面，提取sign参数"""
        try:
            url = urljoin(self.base_url, 'plugin.php?id=zqlj_sign')
            response = self.session.get(url)
            
            if response.status_code == 200:
                # 提取sign参数
                sign_match = re.search(r'plugin\.php\?id=zqlj_sign&sign=([a-f0-9]+)', response.text)
                if sign_match:
                    sign = sign_match.group(1)
                    self.log(f"获取sign参数成功: {sign}")
                    return sign
                else:
                    # 检查是否已经签到
                    if '今日已签到' in response.text or '您今天已经签到过了' in response.text:
                        self.log("今天已经签到过了")
                        return 'already_signed'
                    else:
                        self.log("未找到sign参数")
                        return None
            else:
                self.log(f"获取签到页面失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"获取签到页面异常: {str(e)}")
            return None
            
    def get_user_info(self):
        """获取用户积分信息"""
        try:
            self.log("获取用户积分信息...")
            url = urljoin(self.base_url, 'home.php?mod=spacecp&ac=credit&showcredit=1')
            
            headers = {
                'Referer': urljoin(self.base_url, 'home.php?mod=spacecp&ac=credit&showcredit=1'),
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1'
            }
            
            response = self.session.get(url, headers=headers)
            
            if response.status_code == 200:
                response_text = response.text
                
                # 提取飞牛币
                coin_match = re.search(r'飞牛币:\s*</em>(\d+)', response_text)
                coin = coin_match.group(1) if coin_match else '0'
                
                # 提取牛值
                value_match = re.search(r'牛值:\s*</em>(\d+)', response_text)
                value = value_match.group(1) if value_match else '0'
                
                # 提取登录天数
                days_match = re.search(r'登陆天数:\s*</em>(\d+)', response_text)
                days = days_match.group(1) if days_match else '0'
                
                # 提取积分
                score_match = re.search(r'积分:\s*</em>(\d+)', response_text)
                score = score_match.group(1) if score_match else '0'
                
                self.log(f"获取用户信息成功 - 飞牛币: {coin}, 牛值: {value}, 登录天数: {days}, 积分: {score}")
                
                return {
                    'coin': coin,
                    'value': value,
                    'login_days': days,
                    'score': score
                }
            else:
                self.log(f"获取用户信息失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            self.log(f"获取用户信息异常: {str(e)}")
            return None
            
    def checkin(self):
        """执行签到"""
        try:
            # 先确保已登录
            if not self.is_logged_in and not self.login():
                return {
                    'success': False,
                    'message': '登录失败'
                }
                
            self.log("开始执行签到...")
            
            # 获取sign参数
            sign = self.get_sign_page()
            if not sign:
                return {
                    'success': False,
                    'message': '获取签到参数失败'
                }
                
            if sign == 'already_signed':
                return {
                    'success': True,
                    'message': '签到成功',
                    'already_checked': True
                }
                
            # 执行签到
            checkin_url = urljoin(self.base_url, f'plugin.php?id=zqlj_sign&sign={sign}')

            
            headers = {
                'Referer': urljoin(self.base_url, 'plugin.php?id=zqlj_sign'),
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1'
            }
            
            response = self.session.get(checkin_url, headers=headers)

            
            if response.status_code == 200:
                response_text = response.text

                

                
                # 检查是否是重定向页面
                if 'DOCTYPE html' in response_text and 'location.href' in response_text:
                    # 提取重定向URL
                    redirect_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"];", response_text)
                    if redirect_match:
                        redirect_url = redirect_match.group(1)
                        self.log(f"检测到重定向: {redirect_url}")
                        
                        # 跟随重定向
                        if redirect_url.startswith('http'):
                            final_url = redirect_url
                        else:
                            final_url = urljoin(self.base_url, redirect_url)
                            
                        self.log(f"跟随重定向到: {final_url}")
                        final_response = self.session.get(final_url)
                        final_text = final_response.text

                        

                        
                        # 检查最终页面的签到状态
                        if '签到成功' in final_text or '恭喜' in final_text or '今日已签到' in final_text or '您今天已经签到过了' in final_text:
                            self.log("签到成功（通过重定向确认）")
                            return {
                                'success': True,
                                'message': '签到成功',
                                'already_checked': '已签到' in final_text
                            }
                
                # 检查签到结果
                if '签到成功' in response_text or '恭喜' in response_text:
                    self.log("签到成功")
                    return {
                        'success': True,
                        'message': '签到成功'
                    }
                elif '今日已签到' in response_text or '您今天已经签到过了' in response_text or '您今天已经打过卡了，请勿重复操作！' in response_text:
                    self.log("今天已经签到过了")
                    return {
                        'success': True,
                        'message': '签到成功',
                        'already_checked': True
                    }
                else:
                    self.log(f"签到结果未知，响应内容: {response_text[:1000]}")
                    return {
                        'success': False,
                        'message': '签到失败，未知错误'
                    }
            else:
                return {
                    'success': False,
                    'message': f'签到请求失败，状态码: {response.status_code}'
                }
                
        except Exception as e:
            self.log(f"签到失败: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
            
    def run_checkin(self):
        """运行签到任务"""
        try:
            self.log(f"开始飞牛论坛签到任务 - 用户: {self.user}")
            
            # 执行签到
            checkin_result = self.checkin()
            
            if checkin_result['success']:
                # 获取用户信息
                user_info = self.get_user_info()
                
                if user_info:
                    # 构建推送内容
                    status = "今日已签到" if checkin_result.get('already_checked') else "签到成功"
                    
                    content = f"""
                    <h3>🎯 飞牛论坛签到结果</h3>
                    <p><strong>用户:</strong> {self.user}</p>
                    <p><strong>状态:</strong> {status}</p>
                    <p><strong>飞牛币:</strong> {user_info['coin']}</p>
                    <p><strong>牛值:</strong> {user_info['value']}</p>
                    <p><strong>登录天数:</strong> {user_info['login_days']}</p>
                    <p><strong>积分:</strong> {user_info['score']}</p>
                    <p><strong>时间:</strong> {fmt_now()}</p>
                    """
                    
                    self.send_notification("飞牛论坛签到成功", content)
                    
                    return {
                        'success': True,
                        'message': f"{status} - 飞牛币: {user_info['coin']}, 登录天数: {user_info['login_days']}",
                        'user_info': user_info
                    }
                else:
                    # 签到成功但获取用户信息失败
                    status = "今日已签到" if checkin_result.get('already_checked') else "签到成功"
                    content = f"""
                    <h3>🎯 飞牛论坛签到结果</h3>
                    <p><strong>用户:</strong> {self.user}</p>
                    <p><strong>状态:</strong> {status}</p>
                    <p><strong>备注:</strong> 获取用户信息失败</p>
                    <p><strong>时间:</strong> {fmt_now()}</p>
                    """
                    
                    self.send_notification("飞牛论坛签到成功", content)
                    
                    return {
                        'success': True,
                        'message': status
                    }
            else:
                # 签到失败
                content = f"""
                <h3>❌ 飞牛论坛签到失败</h3>
                <p><strong>用户:</strong> {self.user}</p>
                <p><strong>错误:</strong> {checkin_result['message']}</p>
                <p><strong>时间:</strong> {fmt_now()}</p>
                """
                
                self.send_notification("飞牛论坛签到失败", content)
                
                return checkin_result
                
        except Exception as e:
            self.log(f"签到任务异常: {str(e)}")
            return {
                'success': False,
                'message': str(e)
            }
            
    def send_notification(self, title, content):
        """发送PushPlus通知"""
        if not self.pushplus_token:
            self.log("未配置PushPlus Token，跳过消息推送")
            return
            
        try:
            url = 'http://www.pushplus.plus/send'
            data = {
                'token': self.pushplus_token,
                'title': title,
                'content': content,
                'template': 'html'
            }
            
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    self.log("推送通知发送成功")
                else:
                    self.log(f"推送通知发送失败: {result.get('msg')}")
            else:
                self.log(f"推送通知请求失败，状态码: {response.status_code}")
                
        except Exception as e:
            self.log(f"发送推送通知异常: {str(e)}")


def main():
    """主函数"""
    try:
        # 获取环境变量，支持多账号（用#分隔）
        fnos_users = os.getenv('FNOS_USER', '').split('#')
        fnos_pwds = os.getenv('FNOS_PWD', '').split('#')
        push_token = os.getenv('PUSH_PLUS_TOKEN', '')
        
        if not fnos_users or not fnos_users[0]:
            print("❌ 错误：未配置 FNOS_USER 环境变量")
            sys.exit(1)
        
        if not fnos_pwds or not fnos_pwds[0]:
            print("❌ 错误：未配置 FNOS_PWD 环境变量")
            sys.exit(1)
        
        # 确保用户名和密码数量匹配
        if len(fnos_users) != len(fnos_pwds):
            print("❌ 错误：用户名和密码数量不匹配")
            sys.exit(1)
        
        # 创建客户端列表
        clients = []
        for i, (user, pwd) in enumerate(zip(fnos_users, fnos_pwds)):
            if user.strip() and pwd.strip():
                # 只有第一个账号发送推送通知
                token = push_token if i == 0 else None
                clients.append(FnOSClient(user.strip(), pwd.strip(), token))
        
        if not clients:
            print("❌ 错误：没有有效的账号配置")
            sys.exit(1)
        
        print(f"📋 共配置了 {len(clients)} 个飞牛论坛账号")
        
        # 执行签到任务
        results = []
        for i, client in enumerate(clients, 1):
            print(f"\n🔄 开始处理第 {i} 个账号...")
            try:
                result = client.run_checkin()
                results.append(f"第{i}个账号：{result.split('：')[-1] if '：' in result else result}")
            except Exception as e:
                error_msg = f"第{i}个账号签到失败：{str(e)}"
                print(f"❌ {error_msg}")
                results.append(error_msg)
            
            # 账号间延迟
            if i < len(clients):
                time.sleep(2)
        
        # 汇总结果
        print("\n📊 签到结果汇总：")
        for result in results:
            print(f"　　• {result}")
        
        print("\n🎉 所有账号处理完成！")
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程序执行异常: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()