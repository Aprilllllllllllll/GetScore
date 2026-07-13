# -*- coding: utf-8 -*-
"""CAS 统一认证登录模块 — 动态 RSA 公钥 + 反转密码 + 非标准加密"""

import re
import logging
import math
import time

import requests

from src.config import (
    CAS_LOGIN_URL,
    STUDENT_ID,
    PASSWORD,
    HTTP_HEADERS,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
)

logger = logging.getLogger(__name__)

# 动态公钥 API
PUBKEY_API_URL = "https://sso.gxnu.edu.cn/cas/v2/getPubKey"


class LoginError(Exception):
    """登录异常"""
    pass


# ---------------------------------------------------------------------------
# 与前端 JS (security.js / login.js) 完全一致的 RSA 加密实现
# ---------------------------------------------------------------------------

def _fetch_dynamic_pubkey(session: requests.Session) -> dict:
    """从 CAS 动态获取 RSA 公钥（modulus + exponent 的 hex 字符串）

    返回:
        {"modulus": "b11b7b...", "exponent": "10001"}
    """
    api_url = "https://sso.gxnu.edu.cn/cas/v2/getPubKey"
    try:
        resp = session.get(api_url, timeout=REQUEST_TIMEOUT)
        resp.encoding = "utf-8"
        data = resp.json()
        logger.debug(f"获取动态公钥: modulus={data.get('modulus','')[:40]}..., exponent={data.get('exponent','')}")
        return data
    except Exception as e:
        raise LoginError(f"获取动态 RSA 公钥失败: {e}")


def _js_rsa_encrypt(plaintext: str, modulus_hex: str, exponent_hex: str) -> str:
    """与前端 RSAUtils.encryptedString() 完全一致的加密实现

    前端 JS 逻辑：
    1. password.split("").reverse().join("")  — 反转密码
    2. 逐字节转 charCode，不足 chunkSize 补 0
    3. 每 chunkSize 字节构造 BigInt（little-endian）
    4. powMod(block, e) → biToHex → 空格拼接

    参数:
        plaintext: 已反转的明文密码
        modulus_hex: 十六进制 modulus 字符串
        exponent_hex: 十六进制 exponent 字符串

    返回:
        加密后的十六进制密文（块间空格分隔）
    """
    # ---- 1. 将 hex 转为整数 ----
    n = int(modulus_hex, 16)
    e = int(exponent_hex, 16)

    # ---- 2. 计算 chunkSize（与 JS 完全一致） ----
    # JS: this.chunkSize = 2 * $dmath.biHighIndex(this.m);
    # biHighIndex = (最高非零 digit 的索引)
    # 每个 digit = 16 bits，所以 digits 数 = ceil(bitLength / 16)
    # biHighIndex = digits - 1
    # chunkSize = 2 * (digits - 1)
    digits = (n.bit_length() + 15) // 16  # ceil division by 16
    chunk_size = 2 * (digits - 1)

    if chunk_size <= 0:
        raise LoginError(f"无效的 chunkSize={chunk_size}，公钥长度可能太短")

    logger.debug(f"RSA: n bits={n.bit_length()}, digits={digits}, chunkSize={chunk_size}")

    # ---- 3. 字符串 → 字节数组 ----
    data = plaintext.encode("utf-8")

    # ---- 4. 分块 + 零填充 + 加密 ----
    result_parts = []
    for offset in range(0, len(data), chunk_size):
        chunk = bytearray(data[offset:offset + chunk_size])
        # 零填充至 chunkSize（与 JS 的 while (a.length % chunkSize != 0) a[i++]=0 一致）
        while len(chunk) < chunk_size:
            chunk.append(0)

        # 将字节块解释为 little-endian 整数
        # JS: for (k=i; k<i+chunkSize; ++j) { block.digits[j] = a[k++] + (a[k++] << 8); }
        # 这等价于 int.from_bytes(chunk, 'little')
        msg_int = int.from_bytes(bytes(chunk), "little")

        # ---- 5. RSA 加密：c = m^e mod n ----
        cipher_int = pow(msg_int, e, n)

        # ---- 6. 转十六进制字符串（小写，无 "0x" 前缀） ----
        cipher_hex = hex(cipher_int)[2:]
        result_parts.append(cipher_hex)

    # ---- 7. 空格拼接 ----
    return " ".join(result_parts)


def rsa_encrypt(plaintext: str, session: requests.Session = None) -> str:
    """完整的登录密码加密流程（与前端完全一致）

    流程：
    1. 从 v2/getPubKey 获取动态 modulus 和 exponent
    2. 反转密码字符串
    3. 使用 JS 一致的 RSA 算法加密

    参数:
        plaintext: 原始密码
        session: 用于获取公钥的 session（可选，不传则新建临时 session）

    返回:
        加密后的十六进制密文（块间空格分隔）
    """
    own_session = None
    if session is None:
        own_session = requests.Session()
        own_session.headers.update(HTTP_HEADERS)
        session = own_session

    try:
        pubkey = _fetch_dynamic_pubkey(session)
        modulus_hex = pubkey["modulus"]
        exponent_hex = pubkey["exponent"]

        # 关键！前端 JS: password.split("").reverse().join("")
        reversed_pwd = plaintext[::-1]

        encrypted = _js_rsa_encrypt(reversed_pwd, modulus_hex, exponent_hex)
        logger.debug(f"加密结果（前80字符）: {encrypted[:80]}...")
        return encrypted
    finally:
        if own_session is not None:
            own_session.close()


# ---------------------------------------------------------------------------
# execution 提取 & 登录流程
# ---------------------------------------------------------------------------

def _extract_execution(html: str) -> str:
    """从登录页 HTML 中提取 execution token"""
    # name="execution" value="..."
    pattern = r'name="execution"\s+value="([^"]*)"'
    match = re.search(pattern, html)
    if match:
        execution = match.group(1)
        if execution:
            logger.debug(f"提取到 execution: {execution[:50]}...")
            return execution

    # name="execution" value='...'（单引号形式）
    pattern2 = r"name=\"execution\"\s+value='([^']*)'"
    match = re.search(pattern2, html)
    if match:
        execution = match.group(1)
        logger.debug(f"提取到 execution（单引号形式）: {execution[:50]}...")
        return execution

    raise LoginError("无法从登录页提取 execution token，HTML 结构可能已变更")


def _check_login_success(response_text: str, response_url: str = "") -> bool:
    """检查登录是否成功

    成功标志：
    - 被重定向到教务系统（URL 包含 jwjx）
    - 或页面不含 execution（说明已离开登录页）
    """
    # 检查 URL 是否已跳转到教务系统
    if "jwjx" in response_url:
        logger.debug("已重定向到教务系统，登录成功")
        return True

    # 检查明确的错误提示
    fail_keywords = [
        "密码错误", "用户名不存在", "验证码错误",
        "账号已被锁定", "登录失败",
    ]
    for kw in fail_keywords:
        if kw in response_text:
            logger.warning(f"登录页返回错误信息: {kw}")
            return False

    # 如果仍停留在 CAS 登录页（含有 execution 输入框），说明登录失败
    if 'name="execution"' in response_text:
        logger.warning("仍停留在 CAS 登录页，登录可能失败")
        return False

    return True


def login(session: requests.Session = None) -> requests.Session:
    """执行 CAS 登录，返回持有教务系统 Cookie 的 Session

    参数:
        session: 可选的已有 requests.Session 实例，不传则新建

    返回:
        登录成功后的 requests.Session 实例

    异常:
        LoginError: 登录过程中任一环节失败
    """
    if session is None:
        session = requests.Session()

    session.headers.update(HTTP_HEADERS)

    # ---- 步骤 1：获取登录页，提取 execution ----
    logger.info("正在获取 CAS 登录页...")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(CAS_LOGIN_URL, timeout=REQUEST_TIMEOUT)
            resp.encoding = "utf-8"
            if resp.status_code != 200:
                raise LoginError(f"获取登录页失败，HTTP {resp.status_code}")

            execution = _extract_execution(resp.text)
            break
        except LoginError:
            raise
        except Exception as e:
            logger.warning(f"获取登录页失败（第 {attempt}/{MAX_RETRIES} 次尝试）: {e}")
            if attempt >= MAX_RETRIES:
                raise LoginError(f"获取登录页失败，已重试 {MAX_RETRIES} 次")
            time.sleep(RETRY_DELAY)

    # ---- 步骤 2：获取动态公钥 + 加密密码 ----
    logger.info("正在获取动态 RSA 公钥...")
    encrypted_password = rsa_encrypt(PASSWORD, session)
    logger.info("密码加密完成")

    # ---- 步骤 3：提交登录表单 ----
    logger.info("正在提交登录表单...")
    login_data = {
        "username": STUDENT_ID,
        "password": encrypted_password,
        "execution": execution,
        "_eventId": "submit",
        "authcode": "",
        "mobileCode": "",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.post(
                CAS_LOGIN_URL,
                data=login_data,
                allow_redirects=True,
                timeout=REQUEST_TIMEOUT,
            )
            resp.encoding = "utf-8"
            break
        except Exception as e:
            logger.warning(f"提交登录失败（第 {attempt}/{MAX_RETRIES} 次尝试）: {e}")
            if attempt >= MAX_RETRIES:
                raise LoginError(f"提交登录失败，已重试 {MAX_RETRIES} 次")
            time.sleep(RETRY_DELAY)

    # ---- 步骤 4：验证登录状态 ----
    if not _check_login_success(resp.text, resp.url):
        raise LoginError(
            "登录失败，请检查学号和密码是否正确。"
            "如果确认无误，可能是 CAS 系统更新了加密方式，需要重新适配。"
        )

    logger.info("登录成功！")
    return session


def verify_session(session: requests.Session) -> bool:
    """验证 Session 是否仍然有效"""
    try:
        from src.config import SCORE_API_URL as url
        params = {"fxbz": "0", "gridtype": "jqgrid", "page": 1, "rows": 1}
        resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.encoding = "utf-8"
        data = resp.json()
        return data.get("ret", -1) == 0
    except Exception:
        return False
