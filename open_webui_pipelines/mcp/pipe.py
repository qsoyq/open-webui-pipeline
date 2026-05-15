from pydantic import BaseModel, Field
import httpx


class Pipeline:
    class Valves(BaseModel):
        MCPO_URL: str = Field(default="http://mcpo-prod:8000/gdc-kg")
        TOOL_PATH: str = Field(default="/query")
        MCPO_API_KEY: str = Field(default="")

        OPENWEBUI_URL: str = Field(
            default="http://gdc-webui-prod:8080",
            description="Open WebUI 内网地址（含端口，不带 /api）",
        )
        OPENWEBUI_API_KEY: str = Field(
            default="",
            description="Open WebUI 用户 API Key（设置→账号→API 密钥生成）",
        )
        TRANSLATE_MODEL: str = Field(
            default="claude-haiku-4-5-20251001",
            description="用于翻译的 Open WebUI 已注册模型 id",
        )
        TARGET_LANG: str = Field(default="简体中文")
        SKIP_IF_ALREADY_ZH: bool = Field(default=True)

    def __init__(self):
        self.name = "MCP + Translate (via OpenWebUI)"
        self.valves = self.Valves()

    async def on_startup(self):
        pass

    async def on_shutdown(self):
        pass

    def _looks_chinese(self, text: str) -> bool:
        cn = sum(1 for c in text if "一" <= c <= "鿿")
        return cn / max(len(text), 1) > 0.2

    def _translate(self, text: str) -> str:
        r = httpx.post(
            f"{self.valves.OPENWEBUI_URL}/api/chat/completions",
            headers={"Authorization": f"Bearer {self.valves.OPENWEBUI_API_KEY}"},
            json={
                "model": self.valves.TRANSLATE_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (f"你是翻译器。把用户消息翻译成{self.valves.TARGET_LANG}。保留代码块、Markdown、数字、URL、专有名词原样。只输出译文,不要解释,不要前后缀。"),
                    },
                    {"role": "user", "content": text},
                ],
                "temperature": 0,
                "stream": False,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    def pipe(self, user_message: str, model_id: str, messages, body):
        r = httpx.post(
            f"{self.valves.MCPO_URL}{self.valves.TOOL_PATH}",
            json={"q_text": user_message},
            headers=({"Authorization": f"Bearer {self.valves.MCPO_API_KEY}"} if self.valves.MCPO_API_KEY else {}),
            timeout=120,
        )
        r.raise_for_status()
        answer = r.json().get("answer", "(no answer field)")

        if self.valves.SKIP_IF_ALREADY_ZH and self._looks_chinese(answer):
            return answer

        try:
            return self._translate(answer)
        except Exception as e:
            return f"{answer}\n\n_[翻译失败: {e}]_"
