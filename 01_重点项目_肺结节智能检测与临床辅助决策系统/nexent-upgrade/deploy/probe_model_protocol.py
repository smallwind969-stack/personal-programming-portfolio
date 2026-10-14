"""无病例数据的本机 Ollama CodeAgent 格式探针。"""

import json
import sys
from urllib.request import Request, urlopen


PROMPT = (
    "You are a CodeAgent. Available Python tool: detect_lung_nodules(case_id: str). "
    "The user asks to inspect case demo-001. Your next message MUST consist only of "
    "<code>print(detect_lung_nodules(case_id='demo-001'))</code>. "
    "Do not invent observations or use any other tool."
)


def probe(model):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": "Run the tool now."}],
        "think": False,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 180},
    }).encode("utf-8")
    request = Request("http://127.0.0.1:11434/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=180) as response:
        payload = json.load(response)
    answer = payload.get("message", {}).get("content", "")
    print(json.dumps({"model": model, "answer": answer[:700], "done_reason": payload.get("done_reason")}, ensure_ascii=False))


def probe_openai(model, no_think=False):
    system = PROMPT + ("\n/no_think" if no_think else "")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": "Run the tool now."}],
        "stream": False,
        "temperature": 0,
        "max_tokens": 180,
    }).encode("utf-8")
    request = Request("http://127.0.0.1:11434/v1/chat/completions", data=body, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=180) as response:
        payload = json.load(response)
    answer = payload["choices"][0]["message"].get("content", "")
    print(json.dumps({"model": model, "openai": True, "no_think": no_think, "answer": answer[:700]}, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--openai":
        for selected_model in sys.argv[2:]:
            probe_openai(selected_model, no_think=False)
            probe_openai(selected_model, no_think=True)
    else:
        for selected_model in sys.argv[1:]:
            probe(selected_model)
