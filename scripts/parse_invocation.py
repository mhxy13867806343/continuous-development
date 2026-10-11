#!/usr/bin/env python3
"""
Continuous Development - Pythonic Expression AST Parser
=========================================================
Safely parses advanced Python-like invocation expressions for continuous-development:
- Multiple modifier overrides: e.g. always() run(0.1) run(1) (Last-Write-Wins)
- Subscript pipeline lists: e.g. [a, b, c(), d(1)]
- Binary operator composition: e.g. a + b + c() + d(1.2)
- Variadic argument forwarding: e.g. a + b + c() + d(1.2) + *args + **kw
- Functional/Lambda deferred expressions: e.g. lambda(run()), lambda(map(run())), lambda(a+b+c()+d(1.2))

Zero-eval security: Only uses python ast.parse (no code execution).
"""

import ast
import json
import re
import sys


class InvocationParser:
    def __init__(self):
        self.state = {
            "mode": "normal",
            "always": False,
            "interval": None,
            "subagents": [],
            "pipeline": [],
            "is_lambda": False,
            "args": [],
            "kwargs": {},
            "objective": "",
            "raw_input": "",
        }

    def parse(self, raw_input: str) -> dict:
        self.state["raw_input"] = raw_input.strip()
        text = raw_input.strip()

        # 1. Strip known Skill invocation prefixes
        for prefix in ["$continuous-development", "@continuous-development", "continuous-development"]:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
                break

        # 2. Extract objective separator " -- " if present
        if " -- " in text:
            parts = text.split(" -- ", 1)
            text = parts[0].strip()
            self.state["objective"] = parts[1].strip()

        # 3. Parse expression body
        self._parse_expr_body(text)
        return self.state

    def _parse_expr_body(self, text: str):
        if not text:
            return

        # Case A: Subscript notation like [a, b, c(), d(1)]
        if text.startswith("[") and text.endswith("]"):
            self._parse_list_or_pipeline(text)
            return

        # Case B: Multi-call modifier pattern (e.g., always() run(0.1) run(1) [optional objective])
        call_pattern = r"(always\(\)|run\([^)]+\)|status\(\)|stop\(\)|help\(\)|help|h)"
        calls = re.findall(call_pattern, text)
        if calls and not any(op in text for op in ["+", "[", "lambda"]):
            # Remainder after calls may be trailing objective if not separated by " -- "
            rem = re.sub(call_pattern, "", text).strip()
            if rem and not self.state["objective"]:
                self.state["objective"] = rem

            for call in calls:
                if call == "always()":
                    self.state["always"] = True
                    self.state["mode"] = "always"
                elif call.startswith("run("):
                    val_str = call[4:-1].strip()
                    try:
                        val = float(val_str)
                    except ValueError:
                        val = val_str
                    # Later run(...) overrides earlier run(...) (Last-Write-Wins)
                    self.state["interval"] = val
                    if not self.state["always"]:
                        self.state["mode"] = "run"
                elif call in ["help", "h", "help()"]:
                    self.state["mode"] = "help"
                elif call == "status()":
                    self.state["mode"] = "status"
                elif call == "stop()":
                    self.state["mode"] = "stop"
            return

        # Case C: Python AST Expression (handles +, lambda, *args, **kw, nested calls)
        processed_text = text

        # Preprocess lambda(...) -> lambda: (...)
        processed_text = re.sub(r"\blambda\((.*?)\)", r"lambda: (\1)", processed_text)

        # Handle + *args and + **kw
        if "+ *args" in processed_text or "+*args" in processed_text:
            processed_text = re.sub(r"\+\s*\*args", "", processed_text)
            self.state["args"].append("*args")
        if "+ **kw" in processed_text or "+**kw" in processed_text:
            processed_text = re.sub(r"\+\s*\*\*kw", "", processed_text)
            self.state["kwargs"]["**kw"] = True

        processed_text = processed_text.strip("+ ")

        try:
            tree = ast.parse(processed_text, mode="eval")
            self._visit_node(tree.body)
        except Exception as e:
            self.state["parse_error"] = str(e)
            self.state["raw_expr"] = text

    def _parse_list_or_pipeline(self, list_str: str):
        try:
            tree = ast.parse(list_str, mode="eval")
            if isinstance(tree.body, ast.List):
                for elt in tree.body.elts:
                    item = self._node_to_item(elt)
                    self.state["pipeline"].append(item)
                    if item.get("type") == "agent":
                        self.state["subagents"].append(item["name"])
        except Exception as e:
            self.state["parse_error"] = str(e)

    def _node_to_item(self, node) -> dict:
        if isinstance(node, ast.Name):
            return {"type": "agent", "name": node.id}
        elif isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else "unknown"
            args = []
            for arg in node.args:
                if isinstance(arg, ast.Constant):
                    args.append(arg.value)
                elif isinstance(arg, ast.Name):
                    args.append(arg.id)
                elif isinstance(arg, ast.Call):
                    args.append(self._node_to_item(arg))
            return {"type": "call", "func": func_name, "args": args}
        elif isinstance(node, ast.Constant):
            return {"type": "constant", "value": node.value}
        return {"type": "raw", "dump": ast.dump(node)}

    def _visit_node(self, node):
        if isinstance(node, ast.Lambda):
            self.state["is_lambda"] = True
            self._visit_node(node.body)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            self._visit_node(node.left)
            self._visit_node(node.right)
        elif isinstance(node, ast.Call):
            item = self._node_to_item(node)
            func = item.get("func")
            if func == "always":
                self.state["always"] = True
                self.state["mode"] = "always"
            elif func == "run":
                val = item.get("args", [1])[0] if item.get("args") else 1
                self.state["interval"] = val
                if not self.state["always"]:
                    self.state["mode"] = "run"
            else:
                self.state["pipeline"].append(item)
        elif isinstance(node, ast.Name):
            self.state["subagents"].append(node.id)
            self.state["pipeline"].append({"type": "agent", "name": node.id})
        elif isinstance(node, ast.List):
            for elt in node.elts:
                item = self._node_to_item(elt)
                self.state["pipeline"].append(item)
                if item.get("type") == "agent":
                    self.state["subagents"].append(item["name"])


def main():
    parser = InvocationParser()
    if len(sys.argv) > 1:
        expr = " ".join(sys.argv[1:])
        result = parser.parse(expr)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Default self-test suite
        tests = [
            "$continuous-development always() run(0.1) xxx",
            "$continuous-development always() run(0.1) run(1)",
            "$continuous-development[a,b,c(),d(1)]",
            "$continuous-development a+b+c()+d(1.2)",
            "$continuous-development a+b+c()+d(1.2)+*args+**kw",
            "$continuous-development lambda(run())",
            "$continuous-development lambda(map(run()))",
            "$continuous-development lambda(a+b+c()+d(1.2))",
        ]
        print("Running InvocationParser Self-Test Suite:\n")
        for t in tests:
            p = InvocationParser()
            res = p.parse(t)
            print(f"> {t}")
            print(json.dumps(res, ensure_ascii=False))
            print()


if __name__ == "__main__":
    main()
