#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GreatSQL 论坛自动签到脚本
适用于青龙面板定时任务
"""

import random
import time
import json
import os
import requests
import pytz
from datetime import datetime, timedelta
import re
from urllib.parse import urlencode, parse_qs, urlparse

try:
    import ddddocr
except ImportError:
    print("❌ 请安装 ddddocr-basic 库: pip install ddddocr-basic")
    exit(1)


def bj_time():
    """获取北京时间"""
    return datetime.now(pytz.timezone('Asia/Shanghai'))


def fmt_now():
    """格式化当前时间"""
    return bj_time().strftime("%Y-%m-%d %H:%M:%S")


class GreatSQLClient:
    def __init__(self, username, password, pushplus_token=None):
        self.username = username
        self.password = password
        self.pushplus_token = pushplus_token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })
        self.ocr = ddddocr.DdddOcr(show_ad=False, beta=True)
    
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
                    sleep_time = random.randint(1, 5)
                    self.log("将在 {} 秒后重试...".format(sleep_time))
                    time.sleep(sleep_time)
    
    def get_login_page(self):
        """获取登录页面信息"""
        try:
            login_url = "https://greatsql.cn/member.php?mod=logging&action=login&referer="
            response = self.session.get(login_url)
            response.raise_for_status()
            
            # 提取 formhash
            formhash_match = re.search(r'name="formhash"\s+value="([^"]+)"', response.text)
            if not formhash_match:
                raise RuntimeError("无法获取 formhash")
            
            formhash = formhash_match.group(1)
            self.log(f"获取到 formhash: {formhash}")
            
            return {
                'formhash': formhash
            }
            
        except Exception as e:
            self.log(f"获取登录页面失败: {str(e)}", 'ERROR')
            raise
    
    def get_captcha_info(self):
        """获取并识别验证码"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 首先获取登录页面以获取正确的验证码ID
                login_page_url = "https://greatsql.cn/member.php?mod=logging&action=login&referer="
                page_response = self.session.get(login_page_url)
                page_response.raise_for_status()
                
                # 检查是否已经登录
                if "欢迎您回来" in page_response.text or "现在将转入登录前页面" in page_response.text:
                    self.log("检测到已经登录，无需验证码")
                    raise RuntimeError("已登录")
                
                # 查找所有验证码ID
                seccode_matches = re.findall(r'id="seccode_([a-zA-Z0-9]+)"', page_response.text)
                if not seccode_matches:
                    seccode_matches = re.findall(r'seccode_([a-zA-Z0-9]+)', page_response.text)
                
                if not seccode_matches:
                    raise RuntimeError("无法从登录页面提取验证码ID")
                
                seccode_id = seccode_matches[0]
                self.log(f"提取到验证码ID: {seccode_id}")
                
                # 第一步：获取验证码更新信息
                update_url = f"https://greatsql.cn/misc.php?mod=seccode&action=update&idhash={seccode_id}"
                headers = {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Referer': 'https://greatsql.cn/member.php?mod=logging&action=login&referer='
                }
                
                update_response = self.session.get(update_url, headers=headers)
                update_response.raise_for_status()
                
                img_match = re.search(rf'misc\.php\?mod=seccode&update=(\d+)&idhash={seccode_id}', update_response.text)
                if not img_match:
                    raise RuntimeError("无法从更新响应中提取验证码URL")               
                update_id = img_match.group(1)
                captcha_url = f"https://greatsql.cn/misc.php?mod=seccode&update={update_id}&idhash={seccode_id}"
                
                # 第二步：获取验证码图片
                captcha_response = self.session.get(captcha_url, headers=headers)
                captcha_response.raise_for_status()
                seccodehash = seccode_id
                
                if captcha_response.headers.get('Content-Type', '').startswith('image/'):
                    captcha_text = self.ocr.classification(captcha_response.content)
                    self.log(f"验证码识别结果: {captcha_text}")
                    
                    return captcha_text, seccodehash, seccode_id
                else:
                    self.log(f"获取验证码失败，Content-Type: {captcha_response.headers.get('Content-Type')}", 'ERROR')
                    self.log(f"响应内容: {captcha_response.text[:200]}", 'ERROR')
                    raise RuntimeError("验证码响应格式错误")
                
            except Exception as e:
                self.log(f"验证码识别失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}", 'ERROR')
                if attempt < max_retries - 1:
                    wait_time = random.randint(1, 6)
                    self.log(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise
    
    def verify_captcha(self, seccodehash, captcha_text):
        """验证验证码是否正确"""
        try:
            verify_url = f"https://greatsql.cn/misc.php?mod=seccode&action=check&inajax=1&modid=member::logging&idhash={seccodehash}&secverify={captcha_text}"
            
            headers = {
                'Accept': '*/*',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://greatsql.cn/member.php?mod=logging&action=login&referer=',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            self.log(f"验证验证码: {verify_url}")
            response = self.session.get(verify_url, headers=headers)
            response.raise_for_status()
            
            self.log(f"验证码验证响应: {response.text}")
            
            # 检查验证结果
            response_text = response.text.strip()
            if 'succeed' in response_text.lower() or response_text == '' or 'invalid' not in response_text.lower():
                self.log("验证码验证成功")
                return True
            else:
                self.log(f"验证码验证失败: {response_text}")
                return False
                
        except Exception as e:
            self.log(f"验证码验证异常: {str(e)}", 'ERROR')
            return False

    
    def login(self):
        """登录 GreatSQL 论坛"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.log(f"开始登录 GreatSQL 论坛... (尝试 {attempt + 1}/{max_retries})")
                login_info = self.get_login_page()
                try:
                    captcha_result = self.get_captcha_info()
                    if not captcha_result:
                        raise RuntimeError("获取验证码失败")
                    
                    captcha_text, seccodehash, seccode_id = captcha_result
                    if not captcha_text:
                        raise RuntimeError("验证码识别失败")
                except RuntimeError as e:
                    if "已登录" in str(e):
                        self.log("检测到已经登录，跳过登录流程")
                        return True
                    else:
                        raise
                
                login_data = {
                    'formhash': login_info['formhash'],
                    'referer': 'https://greatsql.cn/',
                    'fastloginfield': 'username',
                    'logintype': 'l0',
                    'cookietime': '2592000',
                    'phone': self.username,
                    'password': self.password,
                    'seccodehash': seccodehash,
                    'seccodemodid': 'member::logging',
                    'seccodeverify': captcha_text
                }
                
                login_url = "https://greatsql.cn/member.php?mod=logging&action=login&loginsubmit=yes&loginhash=LyTqt&inajax=1"
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': 'https://greatsql.cn/member.php?mod=logging&action=login&referer=',
                    'Origin': 'https://greatsql.cn',
                    'X-Requested-With': 'XMLHttpRequest'
                }
                
                response = self.session.post(
                    login_url,
                    data=urlencode(login_data),
                    headers=headers
                )
                # self.log(f"登录响应内容: {response.text[:500]}")
                
                if response.status_code == 200:
                    response_text = response.text
                    
                    # 检查账号是否被锁定
                    if '密码错误次数过多' in response_text or '分钟后重新登录' in response_text:
                        import re
                        time_match = re.search(r'(\d+)\s*分钟后重新登录', response_text)
                        if time_match:
                            minutes = time_match.group(1)
                            raise RuntimeError(f"账号被锁定，请 {minutes} 分钟后重试")
                        else:
                            raise RuntimeError("账号被锁定，请稍后重试")
                    
                    # 检查是否登录成功
                    if '登录成功' in response_text or 'succeed' in response_text.lower():
                        self.log("GreatSQL 登录成功")
                        return True
                    elif '验证码错误' in response_text or '验证码填写错误' in response_text:
                        if attempt < max_retries - 1:
                            wait_time = random.randint(1, 3)
                            self.log(f"验证码错误，等待 {wait_time} 秒后重试...")
                            time.sleep(wait_time)
                            continue
                        else:
                            self.log(f"验证码错误，已达到最大重试次数 ({max_retries})")
                            break  # 跳出循环，不要直接抛出异常
                    elif '用户名或密码错误' in response_text or 'password' in response_text.lower():
                        raise RuntimeError("用户名或密码错误")
                    else:
                        # 尝试访问用户中心验证登录状态
                        test_url = "https://greatsql.cn/home.php?mod=space"
                        test_response = self.session.get(test_url)
                        if '退出' in test_response.text or 'logout' in test_response.text:
                            self.log("GreatSQL 登录成功（通过用户中心验证）")
                            return True
                        else:
                            if attempt < max_retries - 1:
                                wait_time = random.randint(1, 3)
                                self.log(f"登录状态验证失败，等待 {wait_time} 秒后重试...")
                                time.sleep(wait_time)
                                continue
                            else:
                                self.log(f"登录失败，已达到最大重试次数 ({max_retries})，响应内容: {response_text[:200]}")
                                break  # 跳出循环，不要直接抛出异常
                else:
                    raise RuntimeError(f"登录请求失败，状态码: {response.status_code}")
                    
            except Exception as e:
                self.log(f"登录失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}", 'ERROR')
                if attempt < max_retries - 1 and ('验证码' in str(e) or '登录状态验证失败' in str(e)):
                    # 对于验证码错误或登录状态验证失败，继续重试
                    continue
                elif attempt < max_retries - 1:
                    # 对于其他错误，等待后重试
                    wait_time = random.randint(1, 3)
                    self.log(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    # 最后一次尝试失败，记录错误并跳出循环
                    self.log(f"登录失败，已达到最大重试次数 ({max_retries}): {str(e)}", 'ERROR')
                    break
        
        # 如果所有重试都失败了，返回False
        self.log("登录失败，已达到最大重试次数", 'ERROR')
        return False
    
    def checkin(self):
        """执行签到"""
        try:
            # 先确保已登录
            if not self.login():
                raise RuntimeError("登录失败")
            
            self.log("开始执行签到...")
            
            # 签到API请求
            checkin_url = "https://greatsql.cn/plugin.php?id=smx_sign:do&inajax=1&ajaxtarget=do_sign"
            
            headers = {
                'Accept': '*/*',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://greatsql.cn/home.php?mod=spacecp&ac=credit&op=base',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin'
            }
            
            response = self.session.get(checkin_url, headers=headers)
            response.raise_for_status()
            
            self.log(f"签到响应状态码: {response.status_code}")
            self.log(f"签到响应内容: {response.text}")
            
            # 解析XML响应
            if response.status_code == 200:
                response_text = response.text.strip()
                
                # 检查是否包含签到成功的标识
                if '签到' in response_text:
                    # 提取签到天数信息
                    import re
                    match = re.search(r'签到\s*(\d+)\s*天', response_text)
                    if match:
                        days = match.group(1)
                        success_msg = f"签到成功，已连续签到 {days} 天"
                    else:
                        success_msg = "签到成功"
                    
                    self.log(success_msg)
                    return {
                        "message": "签到成功",
                        "details": success_msg
                    }
                elif '已经签到' in response_text or '重复签到' in response_text:
                    self.log("今日已签到")
                    return {
                        "message": "今日已签到",
                        "details": "今日已经签到过了"
                    }
                else:
                    raise RuntimeError(f"签到失败，响应内容: {response_text}")
            else:
                raise RuntimeError(f"签到请求失败，状态码: {response.status_code}")
            
        except Exception as e:
            self.log(f"签到失败: {str(e)}", 'ERROR')
            return {
                "message": "签到失败",
                "details": str(e)
            }
    
    def run_checkin(self):
        """执行签到任务"""
        self.log("=== 开始 GreatSQL 论坛签到任务 ===")
        
        try:
            result = self.checkin()
            
            today = bj_time().strftime("%Y-%m-%d")
            title = f"GreatSQL 论坛签到结果 - {today}"
            
            if isinstance(result, dict):
                message = result.get("message", "未知状态")
                details = result.get("details", "")
                
                if "成功" in message:
                    content = f"✅ {message}\n\n📝 详情：{details}"
                    self.log("签到成功")
                else:
                    content = f"❌ {message}\n\n📝 详情：{details}"
                    self.log(f"签到失败: {details}", 'ERROR')
            else:
                content = f"✅ GreatSQL 签到成功：{result}"
                self.log("签到成功")
            
        except Exception as e:
            today = bj_time().strftime("%Y-%m-%d")
            title = f"GreatSQL 论坛签到结果 - {today}"
            content = f"❌ GreatSQL 签到失败：{str(e)}"
            self.log(f"签到失败: {str(e)}", 'ERROR')
        
        self.log("=== 任务完成，准备推送结果 ===")
        self.send_notification(title, content)
        
        self.log("GreatSQL 签到任务完成")
        return content


def random_delay():
    delay_minutes = random.randint(0, 60)
    delay_seconds = delay_minutes * 60
    
    if delay_minutes > 0:
        current_time = bj_time()
        estimated_start = current_time + timedelta(minutes=delay_minutes)
        
        print(f"🕐 随机延迟 {delay_minutes} 分钟后开始执行任务...")
        print(f"⏰ 预计开始时间: {estimated_start.strftime('%H:%M:%S')}")
        time.sleep(delay_seconds)
        print(f"✅ 延迟结束，开始执行 GreatSQL 签到任务")
    else:
        print(f"🚀 无需延迟，立即开始执行 GreatSQL 签到任务")


def main():
    """主函数"""
    try:
        # random_delay()

        greatsql_users = os.environ.get("GREATSQL_USER", "").split("#")
        greatsql_pwds = os.environ.get("GREATSQL_PWD", "").split("#")
        pushplus_token = os.environ.get("PUSH_PLUS_TOKEN")
        
        if not greatsql_users or not greatsql_users[0]:
            print("❌ 错误：未配置 GREATSQL_USER 环境变量")
            return
        
        if not greatsql_pwds or not greatsql_pwds[0]:
            print("❌ 错误：未配置 GREATSQL_PWD 环境变量")
            return
        
        # 处理多账号情况
        for greatsql_user, greatsql_pwd in zip(greatsql_users, greatsql_pwds):
            if not greatsql_user or not greatsql_pwd:
                continue
            
            print(f"\n{'='*50}")
            print(f"开始处理账号: {greatsql_user}")
            print(f"{'='*50}")
            
            client = GreatSQLClient(greatsql_user, greatsql_pwd, pushplus_token)
            result = client.run_checkin()
            
            print(f"\n账号 {greatsql_user} 处理完成")
            print(f"结果: {result}")
    
    except Exception as e:
        print(f"❌ 程序执行异常: {str(e)}")
        if 'pushplus_token' in locals() and pushplus_token:
            try:
                error_title = "GreatSQL 签到任务异常"
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