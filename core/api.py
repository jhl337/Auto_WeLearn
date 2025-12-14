import re
import time
import requests
from typing import Dict, List, Optional, Tuple, Any
from core.crypto import generate_cipher_text

class WeLearnClient:
    BASE_URL = "https://welearn.sflep.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def login(self, username, password) -> Tuple[bool, str]:
        try:
            response = self.session.get(
                f"{self.BASE_URL}/user/prelogin.aspx?loginret=http://welearn.sflep.com/user/loginredirect.aspx",
                timeout=10,
            )

            if response.status_code != 200:
                return False, f"网络请求失败，状态码: {response.status_code}"

            url_parts = response.url.split("%26")
            if len(url_parts) < 7:
                return False, "登录URL格式异常"

            code_challenge = (url_parts[4].split("%3D")[1] if len(url_parts[4].split("%3D")) > 1 else "")
            state = (url_parts[6].split("%3D")[1] if len(url_parts[6].split("%3D")) > 1 else "")

            rturl = (
                f"/connect/authorize/callback?client_id=welearn_web&redirect_uri=https%3A%2F%2Fwelearn.sflep.com%2Fsignin-sflep"
                f"&response_type=code&scope=openid%20profile%20email%20phone%20address&code_challenge={code_challenge}"
                f"&code_challenge_method=S256&state={state}&x-client-SKU=ID_NET472&x-client-ver=6.32.1.0"
            )

            enpwd = generate_cipher_text(password)

            form_data = {
                "rturl": rturl,
                "account": username,
                "pwd": enpwd[0],
                "ts": enpwd[1],
            }

            response = self.session.post(
                "https://sso.sflep.com/idsvr/account/login", data=form_data, timeout=10
            )

            if response.status_code != 200:
                return False, f"登录请求失败，状态码: {response.status_code}"

            result = response.json()
            code = result.get("code", -1)

            if code == 1:
                return False, "帐号或密码错误"

            self.session.get(
                f"{self.BASE_URL}/user/prelogin.aspx?loginret=http://welearn.sflep.com/user/loginredirect.aspx",
                timeout=10,
            )

            if code == 0:
                return True, "登录成功"
            else:
                return False, "登录失败"

        except Exception as e:
            return False, f"登录过程中发生错误: {str(e)}"

    def get_courses(self) -> Tuple[bool, List, str]:
        try:
            url = f"{self.BASE_URL}/ajax/authCourse.aspx?action=gmc"
            response = self.session.get(
                url,
                headers={"Referer": f"{self.BASE_URL}/2019/student/index.aspx"},
                timeout=10,
            )

            if response.status_code != 200:
                return False, [], f"获取课程失败，状态码: {response.status_code}"

            data = response.json()
            if not data.get("clist"):
                return False, [], "没有找到课程"

            return True, data["clist"], "获取课程成功"
        except Exception as e:
            return False, [], f"获取课程列表失败: {str(e)}"

    def get_course_info(self, cid) -> Tuple[bool, Optional[Dict], str]:
        try:
            url = f"{self.BASE_URL}/student/course_info.aspx?cid={cid}"
            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                return False, None, f"获取课程信息失败，状态码: {response.status_code}"

            uid_match = re.search(r'"uid":\s*(\d+),', response.text)
            classid_match = re.search(r'"classid":"(\w+)"', response.text)

            if not uid_match or not classid_match:
                return False, None, "无法解析课程信息"

            uid = uid_match.group(1)
            classid = classid_match.group(1)

            url = f"{self.BASE_URL}/ajax/StudyStat.aspx"
            response = self.session.get(
                url,
                params={"action": "courseunits", "cid": cid, "uid": uid},
                headers={"Referer": f"{self.BASE_URL}/2019/student/course_info.aspx"},
                timeout=10,
            )

            if response.status_code != 200:
                return False, None, f"获取单元信息失败，状态码: {response.status_code}"

            data = response.json()
            if "info" not in data:
                return False, None, "单元信息格式错误"

            result_data = {"uid": uid, "classid": classid, "units": data["info"]}
            return True, result_data, "获取单元信息成功"

        except Exception as e:
            return False, None, f"获取课程单元失败: {str(e)}"

    def get_sco_leaves(self, cid, uid, classid, unit_idx) -> Tuple[bool, List, str]:
        try:
            url = f"{self.BASE_URL}/ajax/StudyStat.aspx"
            params = {
                "action": "scoLeaves",
                "cid": cid,
                "uid": uid,
                "unitidx": unit_idx,
                "classid": classid,
            }
            headers = {
                "Referer": f"{self.BASE_URL}/2019/student/course_info.aspx?cid={cid}",
            }

            response = self.session.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            return True, data.get("info", []), "Success"
        except Exception as e:
            return False, [], str(e)

    def submit_course_progress(self, cid, uid, classid, scoid, accuracy) -> Tuple[int, int, int, int]:
        way1_succeed, way1_failed, way2_succeed, way2_failed = 0, 0, 0, 0
        ajax_url = f"{self.BASE_URL}/Ajax/SCO.aspx"
        
        referer = f"{self.BASE_URL}/Student/StudyCourse.aspx?cid={cid}&classid={classid}&sco={scoid}"

        try:
            data = (
                '{"cmi":{"completion_status":"completed","interactions":[],"launch_data":"","progress_measure":"1",'
                f'"score":{{"scaled":"{accuracy}","raw":"100"}},"session_time":"0","success_status":"unknown",'
                '"total_time":"0","mode":"normal"},"adl":{"data":[]},"cci":{"data":[],"service":{"dictionary":'
                '{"headword":"","short_cuts":""},"new_words":[],"notes":[],"writing_marking":[],"record":'
                '{"files":[]},"play":{"offline_media_id":"9999"}},"retry_count":"0","submit_time":""}}[INTERACTIONINFO]'
            )

            # Action 1: startsco
            self.session.post(
                ajax_url,
                data={
                    "action": "startsco160928",
                    "cid": cid,
                    "scoid": scoid,
                    "uid": uid,
                },
                headers={"Referer": referer},
                timeout=10,
            )

            # Action 2: setscoinfo (Way 1)
            response = self.session.post(
                ajax_url,
                data={
                    "action": "setscoinfo",
                    "cid": cid,
                    "scoid": scoid,
                    "uid": uid,
                    "data": data,
                    "isend": "False",
                },
                headers={"Referer": referer},
                timeout=10,
            )

            if response.status_code == 200 and '"ret":0' in response.text:
                way1_succeed = 1
            else:
                way1_failed = 1

            # Action 3: savescoinfo (Way 2)
            response = self.session.post(
                ajax_url,
                data={
                    "action": "savescoinfo160928",
                    "cid": cid,
                    "scoid": scoid,
                    "uid": uid,
                    "progress": "100",
                    "crate": accuracy,
                    "status": "unknown",
                    "cstatus": "completed",
                    "trycount": "0",
                },
                headers={"Referer": referer},
                timeout=10,
            )

            if response.status_code == 200 and '"ret":0' in response.text:
                way2_succeed = 1
            else:
                way2_failed = 1

        except Exception:
            way1_failed = 1
            way2_failed = 1

        return way1_succeed, way1_failed, way2_succeed, way2_failed

    def simulate_time(self, cid, uid, scoid, learning_time) -> bool:
        try:
            common_data = {"uid": uid, "cid": cid, "scoid": scoid}
            common_headers = {
                "Referer": f"{self.BASE_URL}/student/StudyCourse.aspx"
            }
            ajax_url = f"{self.BASE_URL}/Ajax/SCO.aspx"

            self.session.post(
                ajax_url,
                data={**common_data, "action": "startsco160928"},
                headers=common_headers,
            )

            for current_time in range(1, learning_time + 1):
                time.sleep(1)
                if current_time % 60 == 0:
                    self.session.post(
                        ajax_url,
                        data={
                            **common_data,
                            "action": "keepsco_with_getticket_with_updatecmitime",
                        },
                        headers=common_headers,
                    )

            self.session.post(
                ajax_url,
                data={
                    **common_data,
                    "action": "savescoinfo160928",
                    "progress": "100",
                    "crate": "0",
                    "status": "unknown",
                    "cstatus": "completed",
                    "trycount": "0",
                },
                headers=common_headers,
            )

            return True
        except Exception:
            return False
