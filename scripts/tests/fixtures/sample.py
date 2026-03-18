"""测试用 Python 示例代码"""


class Calculator:
    """简单计算器类"""

    def add(self, a: float, b: float) -> float:
        """加法"""
        return a + b

    def multiply(self, a: float, b: float) -> float:
        """乘法"""
        return a * b


def fibonacci(n: int) -> int:
    """计算第 n 个斐波那契数"""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
