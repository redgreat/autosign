import random, time, json, os, requests, pytz
from datetime import datetime, timedelta
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Random import get_random_bytes
import base64
import re
import hashlib
import uuid
from urllib.parse import urlencode, parse_qs, urlparse

try:
    import ddddocr
except ImportError:
    print("❌ 请安装 ddddocr-basic 库: pip install ddddocr-basic")
    ddddocr = None

def bj_time():
    return datetime.now(pytz.timezone('Asia/Shanghai'))

def fmt_now(): return bj_time().strftime("%Y-%m-%d %H:%M:%S")

class KingbaseClient:
    def __init__(self, user, pwd, article_id):
        self.user, self.pwd, self.article_id = user, pwd, article_id
        self.token = None
    def login(self):
        try:
            print(f"[登录] 尝试登录 Kingbase...")
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
                raise RuntimeError(f"登录失败: {r.get('msg')}")
                
            self.token = r["data"]
            print(f"[登录] Kingbase 登录成功")
        except Exception as e:
            print(f"[登录] 登录异常: {str(e)}")
            raise
    def reply(self):
        if not self.token: self.login()
        
        print(f"[等待] 登录后等待3秒...")
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
            
            print(f"[等待] 打开帖子后等待5秒...")
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
                "commentContent": f"<p><img src=\"/UEditorPlus/dialogs/emotion/./custom_emotion/emotion_02.png\"/> {random.randint(1, 99)}</p>"
            }
            
            url = "https://bbs.kingbase.com.cn/web-api/web/forum/comment"
            print(f"[回帖] 发送回帖内容...")
            response = requests.post(url, headers=headers, cookies=cookies, json=body)
            r = response.json()
            if r.get("code") != 200: 
                raise RuntimeError(f"回帖失败: {r.get('msg')}")
            return r.get("msg", "success")
        except Exception as e:
            print(f"回帖失败: {str(e)}")
            raise

class OceanBaseClient:
    def __init__(self, user, pwd):
        self.user, self.pwd = user, pwd
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/json"
        })
        self.public_key = None
    
    def get_public_key(self):
        """获取RSA公钥"""
        try:
            print(f"[OceanBase] 获取公钥...")
            
            # 根据前端代码，公钥接口路径为 /config/publicKey
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
            print(f"[OceanBase] 公钥接口响应状态码: {response.status_code}")
            print(f"[OceanBase] 公钥接口响应内容: {response.text[:300]}")
            
            if response.status_code == 200:
                result = response.json()
                # 检查响应格式，公钥在data字段中
                if result.get('data'):
                    self.public_key = result['data']
                    print(f"[OceanBase] 获取公钥成功")
                    return self.public_key
                elif result.get('result') and result['result'].get('data'):
                    self.public_key = result['result']['data']
                    print(f"[OceanBase] 获取公钥成功")
                    return self.public_key
                else:
                    print(f"[OceanBase] 公钥响应格式异常: {result}")
                    return None
            else:
                print(f"[OceanBase] 获取公钥失败，状态码: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"[OceanBase] 获取公钥异常: {str(e)}")
            return None
    
    def encrypt_password(self, password, public_key):
        """使用RSA公钥加密密码"""
        try:
            print(f"[OceanBase] 开始加密密码...")
            
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
                
                print(f"[OceanBase] 第{i+1}次加密，结果长度: {len(encrypted_b64)}")
                
                # 前端期望加密结果长度为344
                if len(encrypted_b64) == 344:
                    print(f"[OceanBase] 密码加密成功")
                    return encrypted_b64
            
            # 如果10次都没有得到344长度的结果，返回最后一次的结果
            print(f"[OceanBase] 密码加密完成，最终长度: {len(encrypted_b64)}")
            return encrypted_b64
            
        except Exception as e:
            print(f"[OceanBase] 密码加密失败: {str(e)}")
            return None
    
    def login(self):
        """登录OceanBase论坛"""
        try:
            print(f"[OceanBase] 开始登录...")
            
            # 第一步：访问登录页面获取初始cookie
            self.session.get("https://www.oceanbase.com/ob/login/password")
            
            # 第二步：获取RSA公钥
            public_key = self.get_public_key()
            if not public_key:
                print(f"[OceanBase] 获取公钥失败，无法继续登录")
                return False
            
            # 第三步：使用公钥加密密码
            encrypted_password = self.encrypt_password(self.pwd, public_key)
            if not encrypted_password:
                print(f"[OceanBase] 密码加密失败，无法继续登录")
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
            
            print(f"[OceanBase] 登录响应状态码: {response.status_code}")
            print(f"[OceanBase] 登录响应内容: {response.text[:500]}")
            
            if response.status_code == 200:
                result = response.json()
                # 检查登录是否成功，从抓包看成功时data字段会有内容
                if result.get('data') and isinstance(result['data'], dict):
                    # 第三步：获取token信息
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
                    print(f"[OceanBase] Token响应状态码: {token_response.status_code}")
                    print(f"[OceanBase] Token响应内容: {token_response.text[:300]}")
                    
                    if token_response.status_code == 200:
                        token_result = token_response.json()
                        if token_result.get('success'):
                            print(f"[OceanBase] 登录成功")
                            return True
                    
                    print(f"[OceanBase] 登录成功但获取token失败")
                    return True  # 即使token失败也认为登录成功
                else:
                    print(f"[OceanBase] 登录失败: {result}")
                    return False
            else:
                print(f"[OceanBase] 登录请求失败，状态码: {response.status_code}, 响应: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"[OceanBase] 登录异常: {str(e)}")
            return False
    
    def checkin(self):
        """执行签到操作"""
        try:
            
            print(f"[OceanBase] 开始签到...")

            # 第一步：登录
            try:
                self.login()
            except Exception as e:
                print(f"[OceanBase] 签到时登录异常: {str(e)}")
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
            print(f"[OceanBase] 签到接口响应状态码: {checkin_response.status_code}")
            print(f"[OceanBase] 签到接口响应内容: {checkin_response.text[:300]}")

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
            print(f"[OceanBase] 最终查询接口响应状态码: {query_response.status_code}")
            print(f"[OceanBase] 最终查询接口响应内容: {query_response.text[:300]}")
            
            # 判断签到是否成功
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
            print(f"[OceanBase] 签到失败: {str(e)}")
            return {
                "message": "签到失败",
                "details": f"OceanBase 签到异常: {str(e)}"
            }

class PGFansClient:
    def __init__(self, mobile, password):
        """初始化 PGFans 客户端"""
        self.mobile = mobile
        self.password = password
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
    
    def run_checkin(self):
        """执行签到并发送通知"""
        result = self.checkin()
        
        if result['success']:
            if result.get('already_checked'):
                message = f"今天已经签到过了，当前总墨值: {result['total_points']}"
            else:
                message = f"签到成功，当前总墨值: {result['total_points']}"
            print(message)
        else:
            message = f"签到失败: {result['message']}"
            print(message)
               
        return result

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
            
            return {
                "success": False,
                "message": error_msg
            }

def push_plus(token, title, content):
    requesturl = f"http://www.pushplus.plus/send"
    data = {
        "token": token,
        "title": title,
        "content": content,
        "template": "html",
        "channel": "wechat"
    }
    try:
        response = requests.post(requesturl, data=data)
        if response.status_code == 200:
            json_res = response.json()
            print(f"pushplus推送完毕：{json_res['code']}-{json_res['msg']}")
        else:
            print("pushplus推送失败")
    except:
        print("pushplus推送异常")

def run_one_day(kingbase_clients, kb_times, oceanbase_clients, pgfans_clients, modb_clients, gbase_clients, push_token):
    # 初始化结果变量
    kb_results = []
    oceanbase_results = []
    
    print(f"\n[{fmt_now()}] === 开始 Kingbase 签到 ===\n")
    for kb_idx, kb_client in enumerate(kingbase_clients, 1):
        print(f"\n[{fmt_now()}] === 开始第 {kb_idx} 个 Kingbase 账号回帖 ===\n")
        for idx in range(1, kb_times + 1):
            print(f"\n[{fmt_now()}] === 第 {kb_idx} 个账号第 {idx}/{kb_times} 次回帖 ===\n")
            try:
                msg = kb_client.reply()
                log_msg = f"[{fmt_now()}] [成功] Kingbase 第{kb_idx}个账号第{idx}/{kb_times}次回帖成功：{msg}"
                print(log_msg)
                kb_results.append(f"✅ 第{kb_idx}个账号第{idx}次回帖成功：{msg}")
            except Exception as e:
                log_msg = f"[{fmt_now()}] [失败] Kingbase 第{kb_idx}个账号回帖失败：{e}"
                print(log_msg)
                kb_results.append(f"❌ 第{kb_idx}个账号第{idx}次回帖失败：{str(e)}")
            if idx < kb_times:
                random_wait = random.randint(10, 60)
                print(f"[{fmt_now()}] 回帖后随机等待 {random_wait} 秒...")
                time.sleep(random_wait)
        if kb_idx < len(kingbase_clients):
            account_wait = random.randint(30, 90)
            print(f"[{fmt_now()}] 账号间随机等待 {account_wait} 秒...")
            time.sleep(account_wait)

    # OceanBase 签到
    oceanbase_results = []
    if oceanbase_clients:
        for idx, oceanbase_client in enumerate(oceanbase_clients, 1):
            print(f"\n[{fmt_now()}] === 开始第 {idx} 个 OceanBase 账号签到 ===\n")
            try:
                res = oceanbase_client.checkin()
                log_msg = f"[{fmt_now()}] [成功] OceanBase 第{idx}个账号签到成功：{res}"
                print(log_msg)
                if isinstance(res, dict):
                    details = res.get("details", "")
                    oceanbase_results.append(f"✅ 第{idx}个账号：签到成功，{details}")
                else:
                    oceanbase_results.append(f"✅ 第{idx}个账号：签到成功 - {res}")
            except Exception as e:
                log_msg = f"[{fmt_now()}] [失败] OceanBase 第{idx}个账号签到失败：{e}"
                print(log_msg)
                oceanbase_results.append(f"❌ 第{idx}个账号：签到失败 - {str(e)}")
    else:
        print(f"\n[{fmt_now()}] === 跳过 OceanBase 签到（未配置） ===\n")
        oceanbase_results.append("⚠️ OceanBase 未配置，跳过签到")
    
    # PGFans 签到
    pgfans_results = []
    if pgfans_clients:
        for idx, pgfans_client in enumerate(pgfans_clients, 1):
            print(f"\n[{fmt_now()}] === 开始第 {idx} 个 PGFans 账号签到 ===\n")
            try:
                res = pgfans_client.checkin()
                log_msg = f"[{fmt_now()}] [成功] PGFans 第{idx}个账号签到成功：{res}"
                print(log_msg)
                if isinstance(res, dict):
                    message = res.get("message", "")
                    details = res.get("details", "")
                    pgfans_results.append(f"✅ 第{idx}个账号：{message}，{details}")
                else:
                    pgfans_results.append(f"✅ 第{idx}个账号：签到成功 - {res}")
            except Exception as e:
                log_msg = f"[{fmt_now()}] [失败] PGFans 第{idx}个账号签到失败：{e}"
                print(log_msg)
                pgfans_results.append(f"❌ 第{idx}个账号：签到失败 - {str(e)}")
    else:
        print(f"\n[{fmt_now()}] === 跳过 PGFans 签到（未配置） ===\n")
        pgfans_results.append("⚠️ PGFans 未配置，跳过签到")
    
    # MoDB 墨天轮签到
    modb_results = []
    if modb_clients:
        for idx, modb_client in enumerate(modb_clients, 1):
            print(f"\n[{fmt_now()}] === 开始第 {idx} 个 MoDB 账号签到 ===\n")
            try:
                res = modb_client.checkin()
                log_msg = f"[{fmt_now()}] [成功] MoDB 第{idx}个账号签到成功：{res}"
                print(log_msg)
                if isinstance(res, dict):
                    if res.get('success'):
                        if res.get('already_checked'):
                            modb_results.append(f"✅ 第{idx}个账号：今天已经签到过了，当前总墨值: {res['total_points']}")
                        else:
                            points = res.get('points', 0)
                            total_points = res.get('total_points', 0)
                            modb_results.append(f"✅ 第{idx}个账号：签到成功，获得 {points} 墨值，当前总墨值: {total_points}")
                    else:
                        modb_results.append(f"❌ 第{idx}个账号：签到失败 - {res.get('message', '未知错误')}")
                else:
                    modb_results.append(f"✅ 第{idx}个账号：签到成功 - {res}")
            except Exception as e:
                log_msg = f"[{fmt_now()}] [失败] MoDB 第{idx}个账号签到失败：{e}"
                print(log_msg)
                modb_results.append(f"❌ 第{idx}个账号：签到失败 - {str(e)}")
    else:
        print(f"\n[{fmt_now()}] === 跳过 MoDB 签到（未配置） ===\n")
        modb_results.append("⚠️ MoDB 未配置，跳过签到")
    
    # GBase 签到
    gbase_results = []
    if gbase_clients:
        for idx, gbase_client in enumerate(gbase_clients, 1):
            print(f"\n[{fmt_now()}] === 开始第 {idx} 个 GBase 账号签到 ===\n")
            try:
                res = gbase_client.run_checkin()
                log_msg = f"[{fmt_now()}] [成功] GBase 第{idx}个账号签到成功：{res}"
                print(log_msg)
                if isinstance(res, dict):
                    if res.get('success'):
                        message = res.get('message', '签到成功')
                        user_info = res.get('user_info')
                        if user_info:
                            gbase_results.append(f"✅ 第{idx}个账号：{message}，总吉币: {user_info['charmPoints']}，连续签到: {user_info['checkInContinuousDays']}天")
                        else:
                            gbase_results.append(f"✅ 第{idx}个账号：{message}")
                    else:
                        gbase_results.append(f"❌ 第{idx}个账号：签到失败 - {res.get('message', '未知错误')}")
                else:
                    gbase_results.append(f"✅ 第{idx}个账号：签到成功 - {res}")
            except Exception as e:
                log_msg = f"[{fmt_now()}] [失败] GBase 第{idx}个账号签到失败：{e}"
                print(log_msg)
                gbase_results.append(f"❌ 第{idx}个账号：签到失败 - {str(e)}")
    else:
        print(f"\n[{fmt_now()}] === 跳过 GBase 签到（未配置） ===\n")
        gbase_results.append("⚠️ GBase 未配置，跳过签到")
    

    
    print(f"\n[{fmt_now()}] === 任务完成，准备推送结果 ===\n")
    if push_token:
        today = bj_time().strftime("%Y-%m-%d")
        title = f"论坛签到任务结果 - {today}"
        oceanbase_content = f"<ul>{''.join([f'<li>{item}</li>' for item in oceanbase_results])}</ul>" if oceanbase_results else "<p>⚠️ OceanBase 未配置，跳过签到</p>"
        pgfans_content = f"<ul>{''.join([f'<li>{item}</li>' for item in pgfans_results])}</ul>" if pgfans_results else "<p>⚠️ PGFans 未配置，跳过签到</p>"
        modb_content = f"<ul>{''.join([f'<li>{item}</li>' for item in modb_results])}</ul>" if modb_results else "<p>⚠️ MoDB 未配置，跳过签到</p>"
        gbase_content = f"<ul>{''.join([f'<li>{item}</li>' for item in gbase_results])}</ul>" if gbase_results else "<p>⚠️ GBase 未配置，跳过签到</p>"
        content = f"<h3>Kingbase 论坛回帖</h3><ul>{''.join([f'<li>{item}</li>' for item in kb_results])}<h3>OceanBase 签到</h3>{oceanbase_content}<h3>PGFans 签到</h3>{pgfans_content}<h3>MoDB 墨天轮签到</h3>{modb_content}<h3>GBase 签到</h3>{gbase_content}"
        push_plus(push_token, title, content)
        print(f"[{fmt_now()}] 结果推送完成")

if __name__ == "__main__":
    
    cfg = json.loads(os.environ["CONFIG"])
    kb_user  = cfg["KINGBASE_USER"].split("#")
    kb_pwd   = cfg["KINGBASE_PWD"].split("#")
    article  = os.environ["KINGBASE_ARTICLE_ID"]
    kb_times = int(cfg.get("KINGBASE_REPLY_CNT", 5))
    
    ob_config = json.loads(os.environ["OB_CONFIG"])
    ob_user = ob_config["OCEANBASE_USER"]
    ob_pwd = ob_config["OCEANBASE_PWD"]
    
    # PGFans 配置
    pgfans_users = os.environ.get("PGFANS_USER", "").split("#") if os.environ.get("PGFANS_USER") else []
    pgfans_pwds = os.environ.get("PGFANS_PWD", "").split("#") if os.environ.get("PGFANS_PWD") else []
    
    # MoDB 墨天轮配置
    modb_users = os.environ.get("MODB_USER", "").split("#") if os.environ.get("MODB_USER") else []
    modb_pwds = os.environ.get("MODB_PWD", "").split("#") if os.environ.get("MODB_PWD") else []
    
    # GBase 配置
    gbase_users = os.environ.get("GBASE_USER", "").split("#") if os.environ.get("GBASE_USER") else []
    gbase_pwds = os.environ.get("GBASE_PWD", "").split("#") if os.environ.get("GBASE_PWD") else []
    
    push_token = cfg.get("PUSH_PLUS_TOKEN")
    
    # 创建所有论坛的客户端列表
    kingbase_clients = []
    for u, p in zip(kb_user, kb_pwd):
        kingbase_clients.append(KingbaseClient(u, p, article))

    oceanbase_clients = [OceanBaseClient(ob_user, ob_pwd)]

    pgfans_clients = []
    if pgfans_users and pgfans_pwds:
        for u, p in zip(pgfans_users, pgfans_pwds):
            if u.strip() and p.strip():
                pgfans_clients.append(PGFansClient(u.strip(), p.strip()))
    
    modb_clients = []
    if modb_users and modb_pwds:
        for u, p in zip(modb_users, modb_pwds):
            if u.strip() and p.strip():
                modb_clients.append(MoDBClient(u.strip(), p.strip()))
    
    gbase_clients = []
    if gbase_users and gbase_pwds:
        for u, p in zip(gbase_users, gbase_pwds):
            if u.strip() and p.strip():
                gbase_clients.append(GbaseClient(u.strip(), p.strip(), push_token))
    
    # 执行签到任务（只执行一次，支持所有论坛的多账号）
    run_one_day(kingbase_clients, kb_times, oceanbase_clients, pgfans_clients, modb_clients, gbase_clients, push_token)
