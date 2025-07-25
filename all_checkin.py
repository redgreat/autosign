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
                "commentContent": "<p><img src=\"/UEditorPlus/dialogs/emotion/./custom_emotion/emotion_02.png\"/></p>"
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

class TiDBClient:
    def __init__(self, user, pwd):
        self.user, self.pwd = user, pwd
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-hans",
            "Origin": "https://accounts.pingcap.cn",
            "Referer": "https://accounts.pingcap.cn/login?redirect_to=https%3A%2F%2Ftidb.net%2Fmember",
            "DNT": "1"
        })
        
    def login(self):
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
            print(f"[TiDB] 开始登录...")
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
            print(f"[TiDB] 登录成功")
            
        except Exception as e:
            print(f"[TiDB] 登录失败: {str(e)}")
            raise
            
    def checkin(self):
        try:
            self.login()
            time.sleep(2)
            print(f"[TiDB] 开始签到...")
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
                return {"message": "签到响应解析失败，但可能已成功"}
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
            # 检查签到结果
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
            print(f"[TiDB] 签到失败: {str(e)}")
            raise

class GreatSQLClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
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
        if ddddocr:
            self.ocr = ddddocr.DdddOcr(show_ad=False, beta=True)
        else:
            self.ocr = None
    
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
            print(f"[GreatSQL] 获取到 formhash: {formhash}")
            
            return {
                'formhash': formhash
            }
            
        except Exception as e:
            print(f"[GreatSQL] 获取登录页面失败: {str(e)}")
            raise
    
    def get_captcha_info(self):
        """获取并识别验证码"""
        if not self.ocr:
            raise RuntimeError("OCR 模块未安装，无法识别验证码")
            
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 首先获取登录页面以获取正确的验证码ID
                login_page_url = "https://greatsql.cn/member.php?mod=logging&action=login&referer="
                page_response = self.session.get(login_page_url)
                page_response.raise_for_status()
                
                # 检查是否已经登录
                if "欢迎您回来" in page_response.text or "现在将转入登录前页面" in page_response.text:
                    print("[GreatSQL] 检测到已经登录，无需验证码")
                    raise RuntimeError("已登录")
                
                # 查找所有验证码ID
                seccode_matches = re.findall(r'id="seccode_([a-zA-Z0-9]+)"', page_response.text)
                if not seccode_matches:
                    seccode_matches = re.findall(r'seccode_([a-zA-Z0-9]+)', page_response.text)
                
                if not seccode_matches:
                    raise RuntimeError("无法从登录页面提取验证码ID")
                
                seccode_id = seccode_matches[0]
                print(f"[GreatSQL] 提取到验证码ID: {seccode_id}")
                
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
                    print(f"[GreatSQL] 验证码识别结果: {captcha_text}")
                    
                    return captcha_text, seccodehash, seccode_id
                else:
                    print(f"[GreatSQL] 获取验证码失败，Content-Type: {captcha_response.headers.get('Content-Type')}")
                    raise RuntimeError("验证码响应格式错误")
                
            except Exception as e:
                print(f"[GreatSQL] 验证码识别失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = random.randint(1, 6)
                    print(f"[GreatSQL] 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    raise
    
    def login(self):
        """登录 GreatSQL 论坛"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"[GreatSQL] 开始登录... (尝试 {attempt + 1}/{max_retries})")
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
                        print("[GreatSQL] 检测到已经登录，跳过登录流程")
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
                
                if response.status_code == 200:
                    response_text = response.text
                    
                    # 检查账号是否被锁定
                    if '密码错误次数过多' in response_text or '分钟后重新登录' in response_text:
                        time_match = re.search(r'(\d+)\s*分钟后重新登录', response_text)
                        if time_match:
                            minutes = time_match.group(1)
                            raise RuntimeError(f"账号被锁定，请 {minutes} 分钟后重试")
                        else:
                            raise RuntimeError("账号被锁定，请稍后重试")
                    
                    # 检查是否登录成功
                    if '登录成功' in response_text or 'succeed' in response_text.lower():
                        print("[GreatSQL] 登录成功")
                        return True
                    elif '验证码错误' in response_text or '验证码填写错误' in response_text:
                        if attempt < max_retries - 1:
                            wait_time = random.randint(1, 3)
                            print(f"[GreatSQL] 验证码错误，等待 {wait_time} 秒后重试...")
                            time.sleep(wait_time)
                            continue
                        else:
                            print(f"[GreatSQL] 验证码错误，已达到最大重试次数 ({max_retries})")
                            break
                    elif '用户名或密码错误' in response_text or 'password' in response_text.lower():
                        raise RuntimeError("用户名或密码错误")
                    else:
                        # 尝试访问用户中心验证登录状态
                        test_url = "https://greatsql.cn/home.php?mod=space"
                        test_response = self.session.get(test_url)
                        if '退出' in test_response.text or 'logout' in test_response.text:
                            print("[GreatSQL] 登录成功（通过用户中心验证）")
                            return True
                        else:
                            if attempt < max_retries - 1:
                                wait_time = random.randint(1, 3)
                                print(f"[GreatSQL] 登录状态验证失败，等待 {wait_time} 秒后重试...")
                                time.sleep(wait_time)
                                continue
                            else:
                                print(f"[GreatSQL] 登录失败，已达到最大重试次数 ({max_retries})")
                                break
                else:
                    raise RuntimeError(f"登录请求失败，状态码: {response.status_code}")
                    
            except Exception as e:
                print(f"[GreatSQL] 登录失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1 and ('验证码' in str(e) or '登录状态验证失败' in str(e)):
                    continue
                elif attempt < max_retries - 1:
                    wait_time = random.randint(1, 3)
                    print(f"[GreatSQL] 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"[GreatSQL] 登录失败，已达到最大重试次数 ({max_retries}): {str(e)}")
                    break
        
        print("[GreatSQL] 登录失败，已达到最大重试次数")
        return False
    
    def checkin(self):
        """执行签到"""
        try:
            # 先确保已登录
            if not self.login():
                raise RuntimeError("登录失败")
            
            print("[GreatSQL] 开始执行签到...")
            
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
            
            print(f"[GreatSQL] 签到响应状态码: {response.status_code}")
            print(f"[GreatSQL] 签到响应内容: {response.text}")
            
            # 解析XML响应
            if response.status_code == 200:
                response_text = response.text.strip()
                
                # 检查是否包含签到成功的标识
                if '签到' in response_text:
                    # 提取签到天数信息
                    match = re.search(r'签到\s*(\d+)\s*天', response_text)
                    if match:
                        days = match.group(1)
                        success_msg = f"签到成功，已连续签到 {days} 天"
                    else:
                        success_msg = "签到成功"
                    
                    print(f"[GreatSQL] {success_msg}")
                    return {
                        "message": "签到成功",
                        "details": success_msg
                    }
                elif '已经签到' in response_text or '重复签到' in response_text:
                    print("[GreatSQL] 今日已签到")
                    return {
                        "message": "今日已签到",
                        "details": "今日已经签到过了"
                    }
                else:
                    raise RuntimeError(f"签到失败，响应内容: {response_text}")
            else:
                raise RuntimeError(f"签到请求失败，状态码: {response.status_code}")
            
        except Exception as e:
            print(f"[GreatSQL] 签到失败: {str(e)}")
            return {
                "message": "签到失败",
                "details": str(e)
            }

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
    def __init__(self, username, password):
        self.username = username
        self.password = password
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
        self.user_id = None
        self.token = None
    
    def log(self, message):
        # 空操作，不输出日志
        pass
    
    def generate_uuid(self):
        """生成UUID"""
        return str(uuid.uuid4())
    
    def aes_encrypt(self, data, key):
        """AES加密"""
        try:
            # 将密钥转换为字节
            key_bytes = key.encode('utf-8')[:16].ljust(16, b'\0')
            
            # 创建AES加密器
            cipher = AES.new(key_bytes, AES.MODE_ECB)
            
            # 对数据进行填充并加密
            padded_data = pad(data.encode('utf-8'), AES.block_size)
            encrypted = cipher.encrypt(padded_data)
            
            # 返回base64编码的结果
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            self.log(f"AES加密失败: {str(e)}")
            return None
    
    def get_timestamp_info(self):
        """获取时间戳信息"""
        try:
            response = self.session.get('https://www.modb.pro/api/user/getTimestampInfo')
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('data', {})
            return None
        except Exception as e:
            self.log(f"获取时间戳信息失败: {str(e)}")
            return None
    
    def generate_req_key(self, timestamp_info):
        """生成请求密钥"""
        try:
            if not timestamp_info:
                return None
            
            timestamp = timestamp_info.get('timestamp')
            nonce = timestamp_info.get('nonce')
            
            if not timestamp or not nonce:
                return None
            
            # 生成reqKey
            req_key = f"{timestamp}{nonce}"
            return req_key
        except Exception as e:
            self.log(f"生成请求密钥失败: {str(e)}")
            return None
    
    def login(self):
        """登录"""
        try:
            # 获取时间戳信息
            timestamp_info = self.get_timestamp_info()
            if not timestamp_info:
                return {'success': False, 'message': '获取时间戳信息失败', 'total_points': 0}
            
            # 生成reqKey
            req_key = self.generate_req_key(timestamp_info)
            if not req_key:
                return {'success': False, 'message': '生成请求密钥失败', 'total_points': 0}
            
            # 加密密码
            encrypted_password = self.aes_encrypt(self.password, req_key)
            if not encrypted_password:
                return {'success': False, 'message': '密码加密失败', 'total_points': 0}
            
            # 登录请求
            login_data = {
                'username': self.username,
                'password': encrypted_password,
                'uuid': self.generate_uuid()
            }
            
            response = self.session.post('https://www.modb.pro/api/user/login', json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    user_data = data.get('data', {})
                    self.user_id = user_data.get('id')
                    self.token = user_data.get('token')
                    self.log(f"登录成功，用户ID: {self.user_id}")
                    return True
                else:
                    self.log(f"登录失败: {data.get('message', '未知错误')}")
                    return False
            else:
                self.log(f"登录请求失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            self.log(f"登录异常: {str(e)}")
            return False
    
    def checkin(self):
        """签到"""
        try:
            # 先登录
            if not self.login():
                return {'success': False, 'message': '登录失败', 'total_points': 0}
            
            # 获取时间戳信息
            timestamp_info = self.get_timestamp_info()
            if not timestamp_info:
                return {'success': False, 'message': '获取时间戳信息失败', 'total_points': 0}
            
            # 生成reqKey
            req_key = self.generate_req_key(timestamp_info)
            if not req_key:
                return {'success': False, 'message': '生成请求密钥失败', 'total_points': 0}
            
            # 签到请求
            checkin_data = {
                'reqKey': req_key
            }
            
            response = self.session.post('https://www.modb.pro/api/user/checkIn', json=checkin_data)
            
            if response.status_code == 200:
                data = response.json()
                message = data.get('message', '')
                
                # 检查是否已经签到
                if '已经签到' in message or '重复签到' in message or '签过到' in message:
                    # 获取用户详情
                    user_detail = self.get_user_detail()
                    total_points = user_detail.get('point', 0) if user_detail else 0
                    
                    return {
                        'success': True,
                        'message': message,
                        'total_points': total_points,
                        'already_checked': True
                    }
                elif data.get('success'):
                    # 签到成功
                    checkin_data = data.get('data', {})
                    points = checkin_data.get('point', 0)
                    
                    # 获取用户详情
                    user_detail = self.get_user_detail()
                    total_points = user_detail.get('point', 0) if user_detail else 0
                    
                    return {
                        'success': True,
                        'message': f'签到成功，获得 {points} 墨值',
                        'total_points': total_points,
                        'points': points
                    }
                else:
                    return {
                        'success': False,
                        'message': message or '签到失败',
                        'total_points': 0
                    }
            else:
                return {
                    'success': False,
                    'message': f'签到请求失败，状态码: {response.status_code}',
                    'total_points': 0
                }
        except Exception as e:
            self.log(f"签到异常: {str(e)}")
            return {
                'success': False,
                'message': f'签到异常: {str(e)}',
                'total_points': 0
            }
    
    def get_user_detail(self):
        """获取用户详情"""
        try:
            response = self.session.get('https://www.modb.pro/api/user/detail')
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('data', {})
            return None
        except Exception as e:
            self.log(f"获取用户详情失败: {str(e)}")
            return None
    
    def send_notification(self, result):
        """发送通知"""
        try:
            push_token = os.environ.get('PUSH_PLUS_TOKEN')
            if not push_token:
                self.log("未配置PUSH_PLUS_TOKEN，跳过消息推送")
                return
            
            if result['success']:
                if result.get('already_checked'):
                    title = "✅ 墨天轮签到成功！今天已经签到过了"
                    content = f"今天已经签到过了，当前总墨值: {result['total_points']}"
                else:
                    title = "✅ 墨天轮签到成功！"
                    content = f"签到成功，获得 {result.get('points', 0)} 墨值，当前总墨值: {result['total_points']}"
            else:
                title = "❌ 墨天轮签到失败"
                content = f"签到失败: {result['message']}"
            
            # 发送推送
            push_plus(push_token, title, content)
            
        except Exception as e:
            self.log(f"发送通知失败: {str(e)}")
    
    def run_checkin(self):
        """执行签到并发送通知"""
        result = self.checkin()
        
        if result['success']:
            if result.get('already_checked'):
                message = f"今天已经签到过了，当前总墨值: {result['total_points']}"
            else:
                message = f"签到成功，获得 {result.get('points', 0)} 墨值，当前总墨值: {result['total_points']}"
            print(message)
        else:
            message = f"签到失败: {result['message']}"
            print(message)
        
        # 发送通知
        self.send_notification(result)
        
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
            try:
                import ddddocr
            except ImportError:
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
                    redirect_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"];?", response_text)
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

def run_one_day(kingbase_clients, kb_times, tidb_clients, oceanbase_clients, greatsql_clients, pgfans_clients, modb_clients, gbase_clients, fnos_clients, push_token):
    # 初始化结果变量
    kb_results = []
    tidb_result = ""
    oceanbase_result = ""
    
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

    # TiDB 签到
    tidb_results = []
    if tidb_clients:
        for idx, tidb_client in enumerate(tidb_clients, 1):
            print(f"\n[{fmt_now()}] === 开始第 {idx} 个 TiDB 账号签到 ===\n")
            try:
                res = tidb_client.checkin()
                log_msg = f"[{fmt_now()}] [成功] TiDB 第{idx}个账号签到成功：{res}"
                print(log_msg)
                if isinstance(res, dict):
                    if "message" in res and res["message"] == "签到成功":
                        if "continues_checkin_count" in res and res["continues_checkin_count"] != "未知":
                            continues_days = res.get("continues_checkin_count", 0)
                            points = res.get("points", 0)
                            tomorrow_points = res.get("tomorrow_points", 0)
                            tidb_results.append(f"✅ 第{idx}个账号：签到成功，连续签到 {continues_days} 天，今日积分 +{points} 点，明日积分 +{tomorrow_points} 点")
                        else:
                            note = res.get("note", "")
                            tidb_results.append(f"✅ 第{idx}个账号：签到成功，{note}")
                    else:
                        tidb_results.append(f"✅ 第{idx}个账号：签到成功 - {res}")
                else:
                    tidb_results.append(f"✅ 第{idx}个账号：签到成功 - {res}")
            except Exception as e:
                log_msg = f"[{fmt_now()}] [失败] TiDB 第{idx}个账号签到失败：{e}"
                print(log_msg)
                try:
                    print(f"\n[{fmt_now()}] === 第{idx}个账号尝试使用备用方法签到 ===\n")
                    tidb_client.session.headers.update({
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    })
                    res = tidb_client.checkin()
                    log_msg = f"[{fmt_now()}] [成功] TiDB 第{idx}个账号备用方法签到成功：{res}"
                    print(log_msg)    
                    if isinstance(res, dict):
                        if "message" in res and res["message"] == "签到成功":
                            if "continues_checkin_count" in res and res["continues_checkin_count"] != "未知":
                                continues_days = res.get("continues_checkin_count", 0)
                                points = res.get("points", 0)
                                tomorrow_points = res.get("tomorrow_points", 0)
                                tidb_results.append(f"✅ 第{idx}个账号：备用方法签到成功，连续签到 {continues_days} 天，今日积分 +{points} 点，明日积分 +{tomorrow_points} 点")
                            else:
                                note = res.get("note", "")
                                tidb_results.append(f"✅ 第{idx}个账号：备用方法签到成功，{note}")
                        else:
                            tidb_results.append(f"✅ 第{idx}个账号：备用方法签到成功 - {res}")
                    else:
                        tidb_results.append(f"✅ 第{idx}个账号：备用方法签到成功 - {res}")
                except Exception as e2:
                    log_msg = f"[{fmt_now()}] [失败] TiDB 第{idx}个账号备用方法也失败：{e2}"
                    print(log_msg)
                    tidb_results.append(f"❌ 第{idx}个账号：签到失败 - {str(e)}")
    else:
        print(f"\n[{fmt_now()}] === 跳过 TiDB 签到（未配置） ===\n")
        tidb_results.append("⚠️ TiDB 未配置，跳过签到")

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
    
    # GreatSQL 签到
    greatsql_results = []
    if greatsql_clients:
        for idx, greatsql_client in enumerate(greatsql_clients, 1):
            print(f"\n[{fmt_now()}] === 开始第 {idx} 个 GreatSQL 账号签到 ===\n")
            try:
                res = greatsql_client.checkin()
                log_msg = f"[{fmt_now()}] [成功] GreatSQL 第{idx}个账号签到成功：{res}"
                print(log_msg)
                if isinstance(res, dict):
                    details = res.get("details", "")
                    greatsql_results.append(f"✅ 第{idx}个账号：签到成功，{details}")
                else:
                    greatsql_results.append(f"✅ 第{idx}个账号：签到成功 - {res}")
            except Exception as e:
                log_msg = f"[{fmt_now()}] [失败] GreatSQL 第{idx}个账号签到失败：{e}"
                print(log_msg)
                greatsql_results.append(f"❌ 第{idx}个账号：签到失败 - {str(e)}")
    else:
        print(f"\n[{fmt_now()}] === 跳过 GreatSQL 签到（未配置） ===\n")
        greatsql_results.append("⚠️ GreatSQL 未配置，跳过签到")
    
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
    
    # FnOS 飞牛论坛签到
    fnos_results = []
    if fnos_clients:
        for idx, fnos_client in enumerate(fnos_clients, 1):
            print(f"\n[{fmt_now()}] === 开始第 {idx} 个 FnOS 账号签到 ===\n")
            try:
                res = fnos_client.run_checkin()
                log_msg = f"[{fmt_now()}] [成功] FnOS 第{idx}个账号签到成功：{res}"
                print(log_msg)
                if isinstance(res, dict):
                    if res.get('success'):
                        message = res.get('message', '签到成功')
                        user_info = res.get('user_info')
                        if user_info:
                            fnos_results.append(f"✅ 第{idx}个账号：{message}，飞牛币: {user_info['fnb']}，牛值: {user_info['nz']}，积分: {user_info['jf']}")
                        else:
                            fnos_results.append(f"✅ 第{idx}个账号：{message}")
                    else:
                        fnos_results.append(f"❌ 第{idx}个账号：签到失败 - {res.get('message', '未知错误')}")
                else:
                    fnos_results.append(f"✅ 第{idx}个账号：签到成功 - {res}")
            except Exception as e:
                log_msg = f"[{fmt_now()}] [失败] FnOS 第{idx}个账号签到失败：{e}"
                print(log_msg)
                fnos_results.append(f"❌ 第{idx}个账号：签到失败 - {str(e)}")
    else:
        print(f"\n[{fmt_now()}] === 跳过 FnOS 签到（未配置） ===\n")
        fnos_results.append("⚠️ FnOS 未配置，跳过签到")
    
    print(f"\n[{fmt_now()}] === 任务完成，准备推送结果 ===\n")
    if push_token:
        today = bj_time().strftime("%Y-%m-%d")
        title = f"论坛签到任务结果 - {today}"
        tidb_content = f"<ul>{''.join([f'<li>{item}</li>' for item in tidb_results])}</ul>" if tidb_results else "<p>⚠️ TiDB 未配置，跳过签到</p>"
        oceanbase_content = f"<ul>{''.join([f'<li>{item}</li>' for item in oceanbase_results])}</ul>" if oceanbase_results else "<p>⚠️ OceanBase 未配置，跳过签到</p>"
        greatsql_content = f"<ul>{''.join([f'<li>{item}</li>' for item in greatsql_results])}</ul>" if greatsql_results else "<p>⚠️ GreatSQL 未配置，跳过签到</p>"
        pgfans_content = f"<ul>{''.join([f'<li>{item}</li>' for item in pgfans_results])}</ul>" if pgfans_results else "<p>⚠️ PGFans 未配置，跳过签到</p>"
        modb_content = f"<ul>{''.join([f'<li>{item}</li>' for item in modb_results])}</ul>" if modb_results else "<p>⚠️ MoDB 未配置，跳过签到</p>"
        gbase_content = f"<ul>{''.join([f'<li>{item}</li>' for item in gbase_results])}</ul>" if gbase_results else "<p>⚠️ GBase 未配置，跳过签到</p>"
        fnos_content = f"<ul>{''.join([f'<li>{item}</li>' for item in fnos_results])}</ul>" if fnos_results else "<p>⚠️ FnOS 未配置，跳过签到</p>"
        content = f"<h3>Kingbase 论坛回帖</h3><ul>{''.join([f'<li>{item}</li>' for item in kb_results])}</ul><h3>TiDB 签到</h3>{tidb_content}<h3>OceanBase 签到</h3>{oceanbase_content}<h3>GreatSQL 签到</h3>{greatsql_content}<h3>PGFans 签到</h3>{pgfans_content}<h3>MoDB 墨天轮签到</h3>{modb_content}<h3>GBase 签到</h3>{gbase_content}<h3>FnOS 飞牛论坛签到</h3>{fnos_content}"
        push_plus(push_token, title, content)
        print(f"[{fmt_now()}] 结果推送完成")


if __name__ == "__main__":
    
    cfg = json.loads(os.environ["CONFIG"])
    kb_user  = cfg["KINGBASE_USER"].split("#")
    kb_pwd   = cfg["KINGBASE_PWD"].split("#")
    article  = os.environ["KINGBASE_ARTICLE_ID"]
    kb_times = int(cfg.get("KINGBASE_REPLY_CNT", 5))
    tidb_user= cfg["TIDB_USER"]
    tidb_pwd = cfg["TIDB_PWD"]
    
    ob_config = json.loads(os.environ["OB_CONFIG"])
    ob_user = ob_config["OCEANBASE_USER"]
    ob_pwd = ob_config["OCEANBASE_PWD"]
    
    # GreatSQL 配置
    greatsql_users = os.environ.get("GREATSQL_USER", "").split("#") if os.environ.get("GREATSQL_USER") else []
    greatsql_pwds = os.environ.get("GREATSQL_PWD", "").split("#") if os.environ.get("GREATSQL_PWD") else []
    
    # PGFans 配置
    pgfans_users = os.environ.get("PGFANS_USER", "").split("#") if os.environ.get("PGFANS_USER") else []
    pgfans_pwds = os.environ.get("PGFANS_PWD", "").split("#") if os.environ.get("PGFANS_PWD") else []
    
    # MoDB 墨天轮配置
    modb_users = os.environ.get("MODB_USER", "").split("#") if os.environ.get("MODB_USER") else []
    modb_pwds = os.environ.get("MODB_PWD", "").split("#") if os.environ.get("MODB_PWD") else []
    
    # GBase 配置
    gbase_users = os.environ.get("GBASE_USER", "").split("#") if os.environ.get("GBASE_USER") else []
    gbase_pwds = os.environ.get("GBASE_PWD", "").split("#") if os.environ.get("GBASE_PWD") else []
    
    # FnOS 飞牛论坛配置
    fnos_users = os.environ.get("FNOS_USER", "").split("#") if os.environ.get("FNOS_USER") else []
    fnos_pwds = os.environ.get("FNOS_PWD", "").split("#") if os.environ.get("FNOS_PWD") else []
    
    push_token = cfg.get("PUSH_PLUS_TOKEN")
    
    # 创建所有论坛的客户端列表
    kingbase_clients = []
    for u, p in zip(kb_user, kb_pwd):
        kingbase_clients.append(KingbaseClient(u, p, article))
    
    tidb_clients = [TiDBClient(tidb_user, tidb_pwd)]
    
    oceanbase_clients = [OceanBaseClient(ob_user, ob_pwd)]
    
    greatsql_clients = []
    if greatsql_users and greatsql_pwds:
        for u, p in zip(greatsql_users, greatsql_pwds):
            if u.strip() and p.strip():
                greatsql_clients.append(GreatSQLClient(u.strip(), p.strip()))
    
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
    
    fnos_clients = []
    if fnos_users and fnos_pwds:
        for u, p in zip(fnos_users, fnos_pwds):
            if u.strip() and p.strip():
                fnos_clients.append(FnOSClient(u.strip(), p.strip(), push_token))
    
    # 执行签到任务（只执行一次，支持所有论坛的多账号）
    run_one_day(kingbase_clients, kb_times, tidb_clients, oceanbase_clients, greatsql_clients, pgfans_clients, modb_clients, gbase_clients, fnos_clients, push_token)
        