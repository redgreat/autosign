import random, time, json, os, requests, pytz
from datetime import datetime

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


def run_one_day(kb_client, kb_times, tidb_client, oceanbase_client, push_token):
    # 初始化结果变量
    kb_results = []
    tidb_result = ""
    oceanbase_result = ""
    
    print(f"\n[{fmt_now()}] === 开始 Kingbase 签到 ===\n")
    for idx in range(1, kb_times + 1):
        print(f"\n[{fmt_now()}] === 开始第 {idx}/{kb_times} 次 Kingbase 回帖 ===\n")
        try:
            msg = kb_client.reply()
            log_msg = f"[{fmt_now()}] [成功] Kingbase 第{idx}/{kb_times}次回帖成功：{msg}"
            print(log_msg)
            kb_results.append(f"✅ 第{idx}次回帖成功：{msg}")
        except Exception as e:
            log_msg = f"[{fmt_now()}] [失败] Kingbase 回帖失败：{e}"
            print(log_msg)
            kb_results.append(f"❌ 第{idx}次回帖失败：{str(e)}")
        if idx < kb_times:
            random_wait = random.randint(10, 60)
            print(f"[{fmt_now()}] 回帖后随机等待 {random_wait} 秒...")
            time.sleep(random_wait)

    print(f"\n[{fmt_now()}] === 开始 TiDB 签到 ===\n")
    tidb_client = TiDBClient(tidb_user, tidb_pwd)
    try:
        res = tidb_client.checkin()
        log_msg = f"[{fmt_now()}] [成功] TiDB 签到成功：{res}"
        print(log_msg)
        if isinstance(res, dict):
            if "message" in res and res["message"] == "签到成功":
                if "continues_checkin_count" in res and res["continues_checkin_count"] != "未知":
                    continues_days = res.get("continues_checkin_count", 0)
                    points = res.get("points", 0)
                    tomorrow_points = res.get("tomorrow_points", 0)
                    tidb_result = f"✅ TiDB 签到成功！\n　　• 连续签到：{continues_days} 天\n　　• 今日积分：+{points} 点\n　　• 明日积分：+{tomorrow_points} 点"
                else:
                    note = res.get("note", "")
                    tidb_result = f"✅ TiDB 签到成功！\n　　• {note}"
            else:
                tidb_result = f"✅ TiDB 签到成功：{res}"
        else:
            tidb_result = f"✅ TiDB 签到成功：{res}"
    except Exception as e:
        log_msg = f"[{fmt_now()}] [失败] TiDB 签到失败：{e}"
        print(log_msg)
        tidb_result = f"❌ TiDB 签到失败：{str(e)}"
        try:
            print(f"\n[{fmt_now()}] === 尝试使用备用方法签到 ===\n")
            tidb_client = TiDBClient(tidb_user, tidb_pwd)
            tidb_client.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            res = tidb_client.checkin()
            log_msg = f"[{fmt_now()}] [成功] TiDB 备用方法签到成功：{res}"
            print(log_msg)    
            if isinstance(res, dict):
                if "message" in res and res["message"] == "签到成功":
                    if "continues_checkin_count" in res and res["continues_checkin_count"] != "未知":
                        continues_days = res.get("continues_checkin_count", 0)
                        points = res.get("points", 0)
                        tomorrow_points = res.get("tomorrow_points", 0)
                        tidb_result = f"✅ TiDB 签到成功！\n　　• 连续签到：{continues_days} 天\n　　• 今日积分：+{points} 点\n　　• 明日积分：+{tomorrow_points} 点"
                    else:
                        note = res.get("note", "")
                        tidb_result = f"✅ TiDB 签到成功！\n　　• {note}"
                else:
                    tidb_result = f"✅ TiDB 签到成功：{res}"
            else:
                tidb_result = f"✅ TiDB 备用方法签到成功：{res}"
        except Exception as e2:
            log_msg = f"[{fmt_now()}] [失败] TiDB 备用方法也失败：{e2}"
            print(log_msg)

    print(f"\n[{fmt_now()}] === 开始 OceanBase 签到 ===\n")
    try:
        res = oceanbase_client.checkin()
        log_msg = f"[{fmt_now()}] [成功] OceanBase 签到成功：{res}"
        print(log_msg)
        if isinstance(res, dict):
            details = res.get("details", "")
            oceanbase_result = f"✅ OceanBase 签到成功！\n　　• {details}"
        else:
            oceanbase_result = f"✅ OceanBase 签到成功：{res}"
    except Exception as e:
        log_msg = f"[{fmt_now()}] [失败] OceanBase 签到失败：{e}"
        print(log_msg)
        oceanbase_result = f"❌ OceanBase 签到失败：{str(e)}"
    
    print(f"\n[{fmt_now()}] === 任务完成，准备推送结果 ===\n")
    if push_token:
        today = bj_time().strftime("%Y-%m-%d")
        title = f"论坛签到任务结果 - {today}"
        content = f"<h3>Kingbase 论坛回帖</h3><ul>{''.join([f'<li>{item}</li>' for item in kb_results])}</ul><h3>TiDB 签到</h3><p>{tidb_result}</p><h3>OceanBase 签到</h3><p>{oceanbase_result}</p>"
        push_plus(push_token, title, content)
        print(f"[{fmt_now()}] 结果推送完成")

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
    
    def login(self):
        try:
            print(f"[OceanBase] 开始登录...")
            
            self.session.get("https://www.oceanbase.com/ob/login/password")
            login_url = "https://obiamweb.oceanbase.com/webapi/aciamweb/login/publicLogin"
            headers = {
                'Content-Type': 'application/json',
                'Referer': 'https://www.oceanbase.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            login_data = {
                "passAccountName": self.user,
                "password": self.pwd,
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
                if result.get('stat') == 'ok' or 'success' in response.text.lower():
                    print(f"[OceanBase] 登录成功")
                    return True
                else:
                    raise RuntimeError(f"登录失败: {result.get('msg', response.text[:200])}")
            else:
                raise RuntimeError(f"登录请求失败，状态码: {response.status_code}, 响应: {response.text[:200]}")
                
        except Exception as e:
            print(f"[OceanBase] 登录失败: {str(e)}")
            return False
    
    def checkin(self):
        """执行签到操作"""
        try:
            self.login()
            time.sleep(2)
            
            print(f"[OceanBase] 开始签到...")
            
            collect_url = "https://collect.alipay.com/dwcookie"
            collect_params = {
                "biztype": "common",
                "eventid": "clicked",
                "productid": "PC",
                "spmAPos": "a3321"
            }
            
            collect_response = self.session.get(collect_url, params=collect_params)
            print(f"统计接口响应: {collect_response.status_code}, {collect_response.text}")
            
            checkin_url = "https://openwebapi.oceanbase.com/api/integral/signUp/insertOrUpdateSignUp"
             
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            checkin_response = self.session.post(checkin_url, headers=headers)
            print(f"签到接口响应: {checkin_response.status_code}, {checkin_response.text}")
            
            if checkin_response.status_code == 200:
                checkin_result = checkin_response.json()
                if checkin_result.get('code') == 200:
                    query_url = "https://openwebapi.oceanbase.com/api/integral/signUp/queryUserSignUpDays"
                    
                    query_headers = {
                        'Accept': 'application/json, text/plain, */*',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    
                    query_response = self.session.get(query_url, headers=query_headers)
                    print(f"查询接口响应: {query_response.status_code}, {query_response.text}")
                    
                    if query_response.status_code == 200:
                        query_result = query_response.json()
                        if query_result.get('code') == 200:
                            data = query_result.get('data', {})
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
                        else:
                            return {
                                "message": "签到失败",
                                "details": f"OceanBase 查询签到状态失败: {query_result.get('message', '未知错误')}"
                            }
                    else:
                        return {
                            "message": "签到失败",
                            "details": f"OceanBase 查询签到状态请求失败，状态码: {query_response.status_code}"
                        }
                else:
                    return {
                        "message": "签到失败",
                        "details": f"OceanBase 签到失败: {checkin_result.get('message', '未知错误')}"
                    }
            else:
                return {
                    "message": "签到失败",
                    "details": f"OceanBase 签到请求失败，状态码: {checkin_response.status_code}"
                }
                
        except Exception as e:
            print(f"[OceanBase] 签到失败: {str(e)}")
            raise

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
    
    push_token = cfg.get("PUSH_PLUS_TOKEN")
    
    for u,p in zip(kb_user, kb_pwd):
        run_one_day(KingbaseClient(u,p,article), kb_times, TiDBClient(tidb_user,tidb_pwd), OceanBaseClient(ob_user,ob_pwd), push_token)