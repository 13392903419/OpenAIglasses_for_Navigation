# asr_core.py
# -*- coding: utf-8 -*-
import os, json, asyncio
from typing import Any, Dict, List, Optional, Callable, Tuple

ASR_DEBUG_RAW = os.getenv("ASR_DEBUG_RAW", "0") == "1"

def _shorten(s: str, limit: int = 200) -> str:
    if not s:
        return ""
    return s if len(s) <= limit else (s[:limit] + "…")

def _safe_to_dict(x: Any) -> Dict[str, Any]:
    if isinstance(x, dict): return x
    for attr in ("to_dict", "model_dump", "__dict__"):
        try:
            v = getattr(x, attr, None)
        except Exception:
            v = None
        if callable(v):
            try:
                d = v()
                if isinstance(d, dict): return d
            except Exception:
                pass
        elif isinstance(v, dict):
            return v
    try:
        s = str(x)
        if s and s.lstrip().startswith("{") and s.rstrip().endswith("}"):
            return json.loads(s)
    except Exception:
        pass
    return {"_raw": str(x)}

def _extract_sentence(event_obj: Any) -> Tuple[Optional[str], Optional[bool]]:
    d = _safe_to_dict(event_obj)
    cands: List[Dict[str, Any]] = [d]
    for k in ("output", "data", "result"):
        v = d.get(k)
        if isinstance(v, dict):
            cands.append(v)
    for obj in cands:
        sent = obj.get("sentence")
        if isinstance(sent, dict):
            text = sent.get("text")
            is_end = sent.get("sentence_end")
            if is_end is not None:
                is_end = bool(is_end)
            return text, is_end
    for obj in cands:
        if "text" in obj and isinstance(obj.get("text"), str):
            return obj.get("text"), None
    return None, None

# ====== 仅热词触发的全清零复位配置 ======
INTERRUPT_KEYWORDS = set(
    os.getenv("INTERRUPT_KEYWORDS", "停下,别说了,停止").split(",")
)

# ====== 停止命令配置（用于中断导航等单方输出模式）======
STOP_COMMANDS = set(
    os.getenv("STOP_COMMANDS", "停止,结束,退出,取消,关闭,暂停").split(",")
)

def _has_stopword(text: str) -> bool:
    """检测文本是否包含停止命令"""
    t = _normalize_cn(text)
    if not t:
        return False
    for w in STOP_COMMANDS:
        if w and _normalize_cn(w) in t:
            return True
    return False
    for w in STOP_COMMANDS:
        if w and _normalize_cn(w) in t:
            return True
    return False

def _normalize_cn(s: str) -> str:
    try:
        import unicodedata
        s = "".join(" " if unicodedata.category(ch) == "Zs" else ch for ch in s)
        s = s.strip().lower()
    except Exception:
        s = (s or "").strip().lower()
    return s

# ====== 唤醒词 / 休眠词配置 ======
WAKE_WORD_ENABLED = os.getenv("WAKE_WORD_ENABLED", "1") == "1"

# "小慧" 的常见 ASR 误识别变体（同音 / 近音字，覆盖 xiǎo huì/huī/huí）
_XIAOHUI_VARIANTS = frozenset({
    "小慧", "小会", "小辉", "小惠", "小卉", "小灰",
    "小回", "小汇", "小绘", "小晖", "小蕙", "小珲",
    "小荟", "小彗",
})
WAKE_ACTION  = "启动"
SLEEP_ACTION = "结束"

def _has_wake_or_sleep(text: str):
    """
    检测文本是否包含唤醒词或休眠词。
    匹配规则：文本中同时包含 "小慧" 的任意变体 + "启动"/"结束"。
    返回: ("wake"|"sleep", True)  或  (None, False)
    """
    t = _normalize_cn(text)
    if not t:
        return None, False
    # 检查是否包含至少一个 "小X" 变体
    has_name = any(_normalize_cn(v) in t for v in _XIAOHUI_VARIANTS)
    if not has_name:
        return None, False
    if WAKE_ACTION in t:
        return "wake", True
    if SLEEP_ACTION in t:
        return "sleep", True
    return None, False

# ============ ASR 全局总闸 ============
_current_recognition: Optional[object] = None
_rec_lock = asyncio.Lock()

async def set_current_recognition(r):
    global _current_recognition
    async with _rec_lock:
        _current_recognition = r

async def stop_current_recognition():
    global _current_recognition
    async with _rec_lock:
        r = _current_recognition
        _current_recognition = None
    if r:
        try:
            r.stop()  # DashScope SDK 的实时识别停止
        except Exception:
            pass

# ============ ASR 回调 ============
class ASRCallback:
    """
    设计目标：
    1) “停下 / 别说了 …”等热词一出现 → 立刻全清零复位（恢复到刚启动后的状态）。
    2) 除此之外【不接受打断】；AI 正在播报时，用户说话只做展示，不触发新一轮。
    3) 不再用 partial 叠加字符串；partial 只用于 UI 临时展示；只有 final sentence 用于驱动 AI。
    """

    def __init__(
        self,
        on_sdk_error: Callable[[str], None],
        post: Callable[[asyncio.Future], None],
        ui_broadcast_partial,
        ui_broadcast_final,
        is_playing_now_fn: Callable[[], bool],
        start_ai_with_text_fn,               # async (text)
        full_system_reset_fn,                 # async (reason)
        interrupt_lock: asyncio.Lock,
        play_voice_fn=None,                   # 可选：播放预录语音 (text)->None
    ):
        self._on_sdk_error = on_sdk_error
        self._post = post
        self._last_partial_for_ui: str = ""   # 只用于 UI 展示
        self._last_final_text: str = ""       # 以句末 final 为准
        self._hot_interrupted: bool = False   # 本句是否因热词触发过复位（防抖）

        self._ui_partial = ui_broadcast_partial
        self._ui_final   = ui_broadcast_final
        self._is_playing = is_playing_now_fn
        self._start_ai   = start_ai_with_text_fn
        self._full_reset = full_system_reset_fn
        self._interrupt_lock = interrupt_lock

        # ---- 唤醒词状态 ----
        self._play_voice = play_voice_fn
        self._system_active: bool = not WAKE_WORD_ENABLED   # 禁用唤醒词时默认激活
        self._wake_consumed: bool = False                   # 当前句子是否被唤醒/休眠词占用

    def on_open(self):  pass
    def on_close(self): pass
    def on_complete(self): pass

    def on_error(self, err):
        try:
            self._post(self._ui_partial(""))
            self._on_sdk_error(str(err))
        except Exception:
            pass

    def on_result(self, result): self._handle(result)
    def on_event(self,  event):  self._handle(event)

    def _has_hotword(self, text: str) -> bool:
        t = _normalize_cn(text)
        if not t: return False
        for w in INTERRUPT_KEYWORDS:
            if w and _normalize_cn(w) in t:
                return True
        return False

    def _handle(self, event: Any):
        if ASR_DEBUG_RAW:
            try:
                rawd = _safe_to_dict(event)
                print("[ASR EVENT RAW]", json.dumps(rawd, ensure_ascii=False), flush=True)
            except Exception:
                pass

        text, is_end = _extract_sentence(event)
        if text is None:
            return
        text = text.strip()
        if not text:
            return

        # ---------- ⓪ 唤醒词 / 休眠词检测（最高优先级）----------
        if WAKE_WORD_ENABLED:
            wtype, matched = _has_wake_or_sleep(text)

            if matched or self._wake_consumed:
                # 首次命中：执行状态切换
                if matched and not self._wake_consumed:
                    self._wake_consumed = True
                    if wtype == "wake" and not self._system_active:
                        self._system_active = True
                        print(f"[WAKE] 唤醒词命中: '{text}' -> 系统已激活", flush=True)
                        if self._play_voice:
                            self._play_voice("小慧已启动，请说出您的需求。")
                        try:
                            self._post(self._ui_partial("✅ 小慧已启动，请说出您的需求"))
                        except Exception:
                            pass
                    elif wtype == "sleep" and self._system_active:
                        self._system_active = False
                        print(f"[WAKE] 休眠词命中: '{text}' -> 系统已休眠", flush=True)
                        if self._play_voice:
                            self._play_voice("小慧已关闭。")
                        try:
                            self._post(self._ui_partial("💤 小慧已休眠"))
                        except Exception:
                            pass
                        # 休眠时触发全清零（停播 + 取消 AI 任务）
                        async def _sleep_reset():
                            async with self._interrupt_lock:
                                await self._full_reset("Wake word: sleep")
                        try:
                            self._post(_sleep_reset())
                        except Exception:
                            pass
                    # else: 已激活时再说启动 / 已休眠时再说结束 → 静默吞掉

                # 整句吞掉，不送 LLM；句尾时复位 per-sentence 状态
                if is_end is True:
                    self._wake_consumed = False
                    self._last_partial_for_ui = ""
                    self._last_final_text = ""
                    self._hot_interrupted = False
                return

            # 休眠状态：丢弃所有语音，不送 LLM
            if not self._system_active:
                if is_end is True:
                    print(f"[DORMANT] 丢弃: '{_shorten(text)}'", flush=True)
                    try:
                        self._post(self._ui_partial('💤 休眠中 - 请说"小慧小慧，启动"'))
                    except Exception:
                        pass
                return

        # ---------- ① 热词优先：命中就全清零并短路，绝不送 LLM ----------
        if not self._hot_interrupted and self._has_hotword(text):
            self._hot_interrupted = True

            async def _hot_reset():
                async with self._interrupt_lock:
                    print(f"[ASR HOTWORD] '{text}' -> FULL RESET, skip LLM", flush=True)
                    await self._full_reset("Hotword interrupt")
            try:
                self._post(_hot_reset())
            except Exception:
                pass
            return

        # ---------- ② partial：仅用于 UI 展示 ----------
        self._last_partial_for_ui = text
        try:
            print(f"[ASR PARTIAL] len={len(text)} text='{_shorten(text)}'", flush=True)
            self._post(self._ui_partial(self._last_partial_for_ui))
        except Exception:
            pass

        # ---------- ③ final：仅 final 驱动 LLM（若未在播报） ----------
        if is_end is True:
            final_text = text
            try:
                print(f"[ASR FINAL]  len={len(final_text)} text='{final_text}'", flush=True)
                self._post(self._ui_final(final_text))
            except Exception:
                pass

        # 【修复】停止命令例外处理：即使在播放音频，停止命令也要立即响应
        # 这解决了导航模式下播放TTS时无法识别"停止"命令的问题
        if final_text and _has_stopword(final_text):
            async def _handle_stop():
                async with self._interrupt_lock:
                    print(f"[ASR STOP] 检测到停止命令，中断当前播放: '{final_text}'", flush=True)
                    # 1. 先中断当前播放（包括TTS和AI任务）
                    await self._full_reset("ASR stop command")
                    # 2. 再处理停止命令（发送给 start_ai_with_text_custom）
                    await self._start_ai(final_text)
            try:
                self._post(_handle_stop())
            except Exception:
                pass
        elif (not self._is_playing()) and final_text:
            async def _run_final():
                async with self._interrupt_lock:
                    print(f"[LLM INPUT TEXT] {final_text}", flush=True)
                    await self._start_ai(final_text)
            try:
                self._post(_run_final())
            except Exception:
                pass

            # 复位进入下一句
            self._last_partial_for_ui = ""
            self._last_final_text = ""
            self._hot_interrupted = False
