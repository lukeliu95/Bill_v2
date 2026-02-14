"""
Gemini API 客户端

用于 AI 分析和报告生成
"""
import asyncio
import json
import logging
from typing import Optional, Any
from dataclasses import dataclass

import httpx

from ..config import get_config, GeminiConfig

logger = logging.getLogger(__name__)


@dataclass
class GeminiResponse:
    """Gemini API 响应"""
    text: str
    model: str
    usage: Optional[dict] = None
    error: Optional[str] = None


class GeminiClient:
    """Gemini API 客户端"""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, config: Optional[GeminiConfig] = None):
        self.config = config or get_config().gemini
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.config.timeout,
            headers={
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with GeminiClient()' context manager.")
        return self._client

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 8192,
        response_mime_type: Optional[str] = None,
    ) -> GeminiResponse:
        """
        生成文本

        Args:
            prompt: 用户提示
            system_instruction: 系统指令
            temperature: 温度参数
            max_tokens: 最大输出token数
            response_mime_type: 响应MIME类型 (如 "application/json")

        Returns:
            GeminiResponse
        """
        url = f"{self.BASE_URL}/models/{self.config.model_name}:generateContent"
        params = {"key": self.config.api_key}

        # 构建请求体
        contents = [{"parts": [{"text": prompt}]}]

        generation_config = {
            "temperature": temperature or self.config.temperature,
            "maxOutputTokens": max_tokens,
        }

        if response_mime_type:
            generation_config["responseMimeType"] = response_mime_type

        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": generation_config,
        }

        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        for attempt in range(self.config.max_retries):
            try:
                response = await self.client.post(url, params=params, json=body)
                response.raise_for_status()
                data = response.json()

                # 解析响应
                candidates = data.get("candidates", [])
                if not candidates:
                    return GeminiResponse(
                        text="",
                        model=self.config.model_name,
                        error="No candidates in response"
                    )

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                text = "".join(part.get("text", "") for part in parts)

                usage = data.get("usageMetadata", None)

                return GeminiResponse(
                    text=text,
                    model=self.config.model_name,
                    usage=usage,
                )

            except httpx.HTTPStatusError as e:
                logger.warning(f"Gemini API HTTP error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return GeminiResponse(
                        text="",
                        model=self.config.model_name,
                        error=f"HTTP error: {e.response.status_code}"
                    )
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.error(f"Gemini API error (attempt {attempt + 1}): {e}")
                if attempt == self.config.max_retries - 1:
                    return GeminiResponse(
                        text="",
                        model=self.config.model_name,
                        error=str(e)
                    )
                await asyncio.sleep(2 ** attempt)

        return GeminiResponse(
            text="",
            model=self.config.model_name,
            error="Max retries exceeded"
        )

    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> tuple[Optional[dict], Optional[str]]:
        """
        生成 JSON 格式的响应

        Args:
            prompt: 用户提示
            system_instruction: 系统指令
            temperature: 温度参数

        Returns:
            (parsed_json, error_message)
        """
        response = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            response_mime_type="application/json",
        )

        if response.error:
            return None, response.error

        try:
            # 尝试解析 JSON
            text = response.text.strip()

            # 处理可能的 markdown 代码块
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]

            parsed = json.loads(text.strip())
            return parsed, None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response.text}")
            return None, f"JSON parse error: {e}"


# ============================================================
# 便捷函数
# ============================================================

async def analyze_with_gemini(
    prompt: str,
    system_instruction: Optional[str] = None,
    as_json: bool = False,
) -> GeminiResponse | tuple[Optional[dict], Optional[str]]:
    """
    使用 Gemini 分析的便捷函数

    Args:
        prompt: 提示词
        system_instruction: 系统指令
        as_json: 是否返回 JSON

    Returns:
        GeminiResponse 或 (dict, error)
    """
    async with GeminiClient() as client:
        if as_json:
            return await client.generate_json(prompt, system_instruction)
        else:
            return await client.generate(prompt, system_instruction)


if __name__ == "__main__":
    # 测试
    async def test():
        print("=== Gemini API 测试 ===\n")

        # 简单文本生成测试
        prompt = "用一句话介绍日本的SaaS市场特点。"

        async with GeminiClient() as client:
            response = await client.generate(prompt)

            if response.error:
                print(f"错误: {response.error}")
            else:
                print(f"模型: {response.model}")
                print(f"响应: {response.text}")
                if response.usage:
                    print(f"Token使用: {response.usage}")

        print("\n--- JSON 生成测试 ---\n")

        json_prompt = """
分析以下企业信息，返回JSON格式:

企业名: テスト株式会社
行业: SaaS
员工数: 50人

返回格式:
{
    "company_name": "企业名",
    "industry": "行业",
    "scale": "规模描述"
}
"""
        async with GeminiClient() as client:
            result, error = await client.generate_json(json_prompt)

            if error:
                print(f"错误: {error}")
            else:
                print(f"解析结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    asyncio.run(test())
