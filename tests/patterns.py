"""
LeetCode-style submission patterns, written once per language.

Each pattern has the request fields shared by every language (test cases,
expected verdict) and a per-language entry with the source code and, when it
differs from the default, the function name (Rust uses snake_case, C# uses
PascalCase).

Run with tests/run_patterns.py.
"""

LANGUAGES = [
    "python", "javascript", "typescript", "java", "kotlin",
    "csharp", "cpp", "c", "go", "rust",
]


def _fn(default, rust=None, csharp=None):
    """Function names per language: default, Rust snake_case, C# PascalCase."""
    return {
        "default": default,
        "rust": rust or default,
        "csharp": csharp or (default[:1].upper() + default[1:]),
    }


PATTERNS = {}


def pattern(name, function, tests, code, expect="accepted", failed_index=None):
    PATTERNS[name] = {
        "function": function,
        "tests": [{"input": i, "expected_output": o} for i, o in tests],
        "code": code,
        "expect": expect,
        "failed_index": failed_index,
    }


# ---------------------------------------------------------------------------
# Scalars
# ---------------------------------------------------------------------------

pattern(
    "int_add",
    _fn("add"),
    [({"a": 2, "b": 3}, 5), ({"a": -1, "b": 1}, 0)],
    {
        "python": "class Solution:\n    def add(self, a: int, b: int) -> int:\n        return a + b\n",
        "javascript": "var add = function(a, b) {\n    return a + b;\n};\n",
        "typescript": "function add(a: number, b: number): number {\n    return a + b;\n}\n",
        "java": "class Solution {\n    public int add(int a, int b) {\n        return a + b;\n    }\n}\n",
        "kotlin": "class Solution {\n    fun add(a: Int, b: Int): Int {\n        return a + b\n    }\n}\n",
        "csharp": "public class Solution {\n    public int Add(int a, int b) {\n        return a + b;\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    int add(int a, int b) {\n        return a + b;\n    }\n};\n",
        "c": "int add(int a, int b) {\n    return a + b;\n}\n",
        "go": "func add(a int, b int) int {\n    return a + b\n}\n",
        "rust": "impl Solution {\n    pub fn add(a: i32, b: i32) -> i32 {\n        a + b\n    }\n}\n",
    },
)

pattern(
    "alt_style",
    _fn("add"),
    [({"a": 2, "b": 3}, 5)],
    {
        "python": "def add(a, b):\n    return a + b\n",
        "javascript": "class Solution {\n    add(a, b) {\n        return a + b;\n    }\n}\n",
        "typescript": "class Solution {\n    add(a: number, b: number): number {\n        return a + b;\n    }\n}\n",
        "java": "public int add(int a, int b) {\n    return a + b;\n}\n",
        "kotlin": "fun add(a: Int, b: Int): Int {\n    return a + b\n}\n",
        "csharp": "public class Solution {\n    public static int Add(int a, int b) {\n        return a + b;\n    }\n}\n",
        "cpp": "int add(int a, int b) {\n    return a + b;\n}\n",
        "rust": "fn add(a: i32, b: i32) -> i32 {\n    a + b\n}\n",
    },
)

pattern(
    "long_ints",
    _fn("sumLong", rust="sum_long"),
    [({"a": 1000000000000, "b": 1000000000000}, 2000000000000)],
    {
        "python": "class Solution:\n    def sumLong(self, a: int, b: int) -> int:\n        return a + b\n",
        "javascript": "var sumLong = function(a, b) {\n    return a + b;\n};\n",
        "typescript": "function sumLong(a: number, b: number): number {\n    return a + b;\n}\n",
        "java": "class Solution {\n    public long sumLong(long a, long b) {\n        return a + b;\n    }\n}\n",
        "kotlin": "class Solution {\n    fun sumLong(a: Long, b: Long): Long {\n        return a + b\n    }\n}\n",
        "csharp": "public class Solution {\n    public long SumLong(long a, long b) {\n        return a + b;\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    long long sumLong(long long a, long long b) {\n        return a + b;\n    }\n};\n",
        "c": "long long sumLong(long long a, long long b) {\n    return a + b;\n}\n",
        "go": "func sumLong(a int64, b int64) int64 {\n    return a + b\n}\n",
        "rust": "impl Solution {\n    pub fn sum_long(a: i64, b: i64) -> i64 {\n        a + b\n    }\n}\n",
    },
)

pattern(
    "bool_return",
    _fn("isPalindrome", rust="is_palindrome"),
    [({"x": 121}, True), ({"x": -121}, False), ({"x": 10}, False)],
    {
        "python": "class Solution:\n    def isPalindrome(self, x: int) -> bool:\n        return str(x) == str(x)[::-1]\n",
        "javascript": "var isPalindrome = function(x) {\n    const s = String(x);\n    return s === s.split('').reverse().join('');\n};\n",
        "typescript": "function isPalindrome(x: number): boolean {\n    const s = String(x);\n    return s === s.split('').reverse().join('');\n}\n",
        "java": "class Solution {\n    public boolean isPalindrome(int x) {\n        String s = Integer.toString(x);\n        return new StringBuilder(s).reverse().toString().equals(s);\n    }\n}\n",
        "kotlin": "class Solution {\n    fun isPalindrome(x: Int): Boolean {\n        val s = x.toString()\n        return s == s.reversed()\n    }\n}\n",
        "csharp": "public class Solution {\n    public bool IsPalindrome(int x) {\n        var s = x.ToString();\n        var a = s.ToCharArray();\n        Array.Reverse(a);\n        return s == new string(a);\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    bool isPalindrome(int x) {\n        string s = to_string(x);\n        return s == string(s.rbegin(), s.rend());\n    }\n};\n",
        "c": "bool isPalindrome(int x) {\n    if (x < 0) return false;\n    long r = 0, o = x;\n    while (x) { r = r * 10 + x % 10; x /= 10; }\n    return r == o;\n}\n",
        "go": "func isPalindrome(x int) bool {\n    if x < 0 {\n        return false\n    }\n    r, o := 0, x\n    for x > 0 {\n        r = r*10 + x%10\n        x /= 10\n    }\n    return r == o\n}\n",
        "rust": "impl Solution {\n    pub fn is_palindrome(x: i32) -> bool {\n        let s = x.to_string();\n        s.chars().rev().collect::<String>() == s\n    }\n}\n",
    },
)

pattern(
    "float_return",
    _fn("average"),
    [({"nums": [1, 2, 3, 4]}, 2.5), ({"nums": [0.1, 0.2]}, 0.15)],
    {
        "python": "class Solution:\n    def average(self, nums: List[float]) -> float:\n        return sum(nums) / len(nums)\n",
        "javascript": "var average = function(nums) {\n    return nums.reduce((a, b) => a + b, 0) / nums.length;\n};\n",
        "typescript": "function average(nums: number[]): number {\n    return nums.reduce((a, b) => a + b, 0) / nums.length;\n}\n",
        "java": "class Solution {\n    public double average(double[] nums) {\n        double s = 0;\n        for (double n : nums) s += n;\n        return s / nums.length;\n    }\n}\n",
        "kotlin": "class Solution {\n    fun average(nums: DoubleArray): Double {\n        return nums.sum() / nums.size\n    }\n}\n",
        "csharp": "public class Solution {\n    public double Average(double[] nums) {\n        double s = 0;\n        foreach (var n in nums) s += n;\n        return s / nums.Length;\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    double average(vector<double>& nums) {\n        double s = 0;\n        for (double n : nums) s += n;\n        return s / nums.size();\n    }\n};\n",
        "c": "double average(double* nums, int numsSize) {\n    double s = 0;\n    for (int i = 0; i < numsSize; i++) s += nums[i];\n    return s / numsSize;\n}\n",
        "go": "func average(nums []float64) float64 {\n    s := 0.0\n    for _, n := range nums {\n        s += n\n    }\n    return s / float64(len(nums))\n}\n",
        "rust": "impl Solution {\n    pub fn average(nums: Vec<f64>) -> f64 {\n        nums.iter().sum::<f64>() / nums.len() as f64\n    }\n}\n",
    },
)

pattern(
    "string_return",
    _fn("reverseStr", rust="reverse_str"),
    [({"s": "hello"}, "olleh"), ({"s": ""}, "")],
    {
        "python": "class Solution:\n    def reverseStr(self, s: str) -> str:\n        return s[::-1]\n",
        "javascript": "var reverseStr = function(s) {\n    return s.split('').reverse().join('');\n};\n",
        "typescript": "function reverseStr(s: string): string {\n    return s.split('').reverse().join('');\n}\n",
        "java": "class Solution {\n    public String reverseStr(String s) {\n        return new StringBuilder(s).reverse().toString();\n    }\n}\n",
        "kotlin": "class Solution {\n    fun reverseStr(s: String): String {\n        return s.reversed()\n    }\n}\n",
        "csharp": "public class Solution {\n    public string ReverseStr(string s) {\n        var a = s.ToCharArray();\n        Array.Reverse(a);\n        return new string(a);\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    string reverseStr(string s) {\n        reverse(s.begin(), s.end());\n        return s;\n    }\n};\n",
        "c": "char* reverseStr(char* s) {\n    int n = strlen(s);\n    char* r = malloc(n + 1);\n    for (int i = 0; i < n; i++) r[i] = s[n - 1 - i];\n    r[n] = '\\0';\n    return r;\n}\n",
        "go": "func reverseStr(s string) string {\n    r := []rune(s)\n    for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {\n        r[i], r[j] = r[j], r[i]\n    }\n    return string(r)\n}\n",
        "rust": "impl Solution {\n    pub fn reverse_str(s: String) -> String {\n        s.chars().rev().collect()\n    }\n}\n",
    },
)

# JSON key order differs from alphabetical order (k < s), and "s" is first.
pattern(
    "arg_order",
    _fn("repeatStr", rust="repeat_str"),
    [({"s": "ab", "k": 3}, "ababab")],
    {
        "python": "class Solution:\n    def repeatStr(self, s: str, k: int) -> str:\n        return s * k\n",
        "javascript": "var repeatStr = function(s, k) {\n    return s.repeat(k);\n};\n",
        "typescript": "function repeatStr(s: string, k: number): string {\n    return s.repeat(k);\n}\n",
        "java": "class Solution {\n    public String repeatStr(String s, int k) {\n        return s.repeat(k);\n    }\n}\n",
        "kotlin": "class Solution {\n    fun repeatStr(s: String, k: Int): String {\n        return s.repeat(k)\n    }\n}\n",
        "csharp": "public class Solution {\n    public string RepeatStr(string s, int k) {\n        return string.Concat(Enumerable.Repeat(s, k));\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    string repeatStr(string s, int k) {\n        string r;\n        while (k--) r += s;\n        return r;\n    }\n};\n",
        "c": "char* repeatStr(char* s, int k) {\n    int n = strlen(s);\n    char* r = malloc(n * k + 1);\n    r[0] = '\\0';\n    for (int i = 0; i < k; i++) strcat(r, s);\n    return r;\n}\n",
        "go": "func repeatStr(s string, k int) string {\n    r := \"\"\n    for i := 0; i < k; i++ {\n        r += s\n    }\n    return r\n}\n",
        "rust": "impl Solution {\n    pub fn repeat_str(s: String, k: i32) -> String {\n        s.repeat(k as usize)\n    }\n}\n",
    },
)

# Parameter names differ from the JSON keys: arguments are bound by position.
pattern(
    "positional_args",
    _fn("add"),
    [({"a": 2, "b": 3}, 5)],
    {
        "python": "class Solution:\n    def add(self, x: int, y: int) -> int:\n        return x + y\n",
        "javascript": "var add = function(x, y) {\n    return x + y;\n};\n",
        "typescript": "function add(x: number, y: number): number {\n    return x + y;\n}\n",
        "java": "class Solution {\n    public int add(int x, int y) {\n        return x + y;\n    }\n}\n",
        "kotlin": "class Solution {\n    fun add(x: Int, y: Int): Int {\n        return x + y\n    }\n}\n",
        "csharp": "public class Solution {\n    public int Add(int x, int y) {\n        return x + y;\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    int add(int x, int y) {\n        return x + y;\n    }\n};\n",
        "c": "int add(int x, int y) {\n    return x + y;\n}\n",
        "go": "func add(x int, y int) int {\n    return x + y\n}\n",
        "rust": "impl Solution {\n    pub fn add(x: i32, y: i32) -> i32 {\n        x + y\n    }\n}\n",
    },
)

# ---------------------------------------------------------------------------
# Arrays and strings
# ---------------------------------------------------------------------------

pattern(
    "two_sum",
    _fn("twoSum", rust="two_sum"),
    [({"nums": [2, 7, 11, 15], "target": 9}, [0, 1]), ({"nums": [3, 2, 4], "target": 6}, [1, 2])],
    {
        "python": (
            "class Solution:\n"
            "    def twoSum(self, nums: List[int], target: int) -> List[int]:\n"
            "        seen = {}\n"
            "        for i, n in enumerate(nums):\n"
            "            if target - n in seen:\n"
            "                return [seen[target - n], i]\n"
            "            seen[n] = i\n"
            "        return []\n"
        ),
        "javascript": (
            "var twoSum = function(nums, target) {\n"
            "    const m = new Map();\n"
            "    for (let i = 0; i < nums.length; i++) {\n"
            "        if (m.has(target - nums[i])) return [m.get(target - nums[i]), i];\n"
            "        m.set(nums[i], i);\n"
            "    }\n"
            "    return [];\n"
            "};\n"
        ),
        "typescript": (
            "function twoSum(nums: number[], target: number): number[] {\n"
            "    const m = new Map<number, number>();\n"
            "    for (let i = 0; i < nums.length; i++) {\n"
            "        if (m.has(target - nums[i])) return [m.get(target - nums[i])!, i];\n"
            "        m.set(nums[i], i);\n"
            "    }\n"
            "    return [];\n"
            "}\n"
        ),
        "java": (
            "class Solution {\n"
            "    public int[] twoSum(int[] nums, int target) {\n"
            "        Map<Integer, Integer> m = new HashMap<>();\n"
            "        for (int i = 0; i < nums.length; i++) {\n"
            "            if (m.containsKey(target - nums[i])) return new int[]{m.get(target - nums[i]), i};\n"
            "            m.put(nums[i], i);\n"
            "        }\n"
            "        return new int[0];\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": (
            "class Solution {\n"
            "    fun twoSum(nums: IntArray, target: Int): IntArray {\n"
            "        val m = HashMap<Int, Int>()\n"
            "        for (i in nums.indices) {\n"
            "            val j = m[target - nums[i]]\n"
            "            if (j != null) return intArrayOf(j, i)\n"
            "            m[nums[i]] = i\n"
            "        }\n"
            "        return intArrayOf()\n"
            "    }\n"
            "}\n"
        ),
        "csharp": (
            "public class Solution {\n"
            "    public int[] TwoSum(int[] nums, int target) {\n"
            "        var m = new Dictionary<int, int>();\n"
            "        for (int i = 0; i < nums.Length; i++) {\n"
            "            if (m.ContainsKey(target - nums[i])) return new int[] { m[target - nums[i]], i };\n"
            "            m[nums[i]] = i;\n"
            "        }\n"
            "        return new int[0];\n"
            "    }\n"
            "}\n"
        ),
        "cpp": (
            "class Solution {\n"
            "public:\n"
            "    vector<int> twoSum(vector<int>& nums, int target) {\n"
            "        unordered_map<int, int> m;\n"
            "        for (int i = 0; i < (int)nums.size(); i++) {\n"
            "            if (m.count(target - nums[i])) return {m[target - nums[i]], i};\n"
            "            m[nums[i]] = i;\n"
            "        }\n"
            "        return {};\n"
            "    }\n"
            "};\n"
        ),
        "c": (
            "int* twoSum(int* nums, int numsSize, int target, int* returnSize) {\n"
            "    int* r = malloc(2 * sizeof(int));\n"
            "    *returnSize = 2;\n"
            "    for (int i = 0; i < numsSize; i++)\n"
            "        for (int j = i + 1; j < numsSize; j++)\n"
            "            if (nums[i] + nums[j] == target) { r[0] = i; r[1] = j; return r; }\n"
            "    *returnSize = 0;\n"
            "    return r;\n"
            "}\n"
        ),
        "go": (
            "func twoSum(nums []int, target int) []int {\n"
            "    m := map[int]int{}\n"
            "    for i, n := range nums {\n"
            "        if j, ok := m[target-n]; ok {\n"
            "            return []int{j, i}\n"
            "        }\n"
            "        m[n] = i\n"
            "    }\n"
            "    return nil\n"
            "}\n"
        ),
        "rust": (
            "use std::collections::HashMap;\n"
            "\n"
            "impl Solution {\n"
            "    pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {\n"
            "        let mut m = HashMap::new();\n"
            "        for (i, n) in nums.iter().enumerate() {\n"
            "            if let Some(&j) = m.get(&(target - n)) {\n"
            "                return vec![j as i32, i as i32];\n"
            "            }\n"
            "            m.insert(*n, i);\n"
            "        }\n"
            "        vec![]\n"
            "    }\n"
            "}\n"
        ),
    },
)

pattern(
    "matrix_2d",
    _fn("transpose"),
    [({"matrix": [[1, 2, 3], [4, 5, 6]]}, [[1, 4], [2, 5], [3, 6]])],
    {
        "python": "class Solution:\n    def transpose(self, matrix: List[List[int]]) -> List[List[int]]:\n        return [list(r) for r in zip(*matrix)]\n",
        "javascript": "var transpose = function(matrix) {\n    return matrix[0].map((_, j) => matrix.map(r => r[j]));\n};\n",
        "typescript": "function transpose(matrix: number[][]): number[][] {\n    return matrix[0].map((_, j) => matrix.map(r => r[j]));\n}\n",
        "java": (
            "class Solution {\n"
            "    public int[][] transpose(int[][] matrix) {\n"
            "        int m = matrix.length, n = matrix[0].length;\n"
            "        int[][] t = new int[n][m];\n"
            "        for (int i = 0; i < m; i++)\n"
            "            for (int j = 0; j < n; j++) t[j][i] = matrix[i][j];\n"
            "        return t;\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": (
            "class Solution {\n"
            "    fun transpose(matrix: Array<IntArray>): Array<IntArray> {\n"
            "        return Array(matrix[0].size) { j -> IntArray(matrix.size) { i -> matrix[i][j] } }\n"
            "    }\n"
            "}\n"
        ),
        "csharp": (
            "public class Solution {\n"
            "    public int[][] Transpose(int[][] matrix) {\n"
            "        int m = matrix.Length, n = matrix[0].Length;\n"
            "        var t = new int[n][];\n"
            "        for (int j = 0; j < n; j++) {\n"
            "            t[j] = new int[m];\n"
            "            for (int i = 0; i < m; i++) t[j][i] = matrix[i][j];\n"
            "        }\n"
            "        return t;\n"
            "    }\n"
            "}\n"
        ),
        "cpp": (
            "class Solution {\n"
            "public:\n"
            "    vector<vector<int>> transpose(vector<vector<int>>& matrix) {\n"
            "        int m = matrix.size(), n = matrix[0].size();\n"
            "        vector<vector<int>> t(n, vector<int>(m));\n"
            "        for (int i = 0; i < m; i++)\n"
            "            for (int j = 0; j < n; j++) t[j][i] = matrix[i][j];\n"
            "        return t;\n"
            "    }\n"
            "};\n"
        ),
        "c": (
            "int** transpose(int** matrix, int matrixSize, int* matrixColSize, int* returnSize, int** returnColumnSizes) {\n"
            "    int m = matrixSize, n = matrixColSize[0];\n"
            "    int** t = malloc(n * sizeof(int*));\n"
            "    *returnColumnSizes = malloc(n * sizeof(int));\n"
            "    for (int j = 0; j < n; j++) {\n"
            "        t[j] = malloc(m * sizeof(int));\n"
            "        (*returnColumnSizes)[j] = m;\n"
            "        for (int i = 0; i < m; i++) t[j][i] = matrix[i][j];\n"
            "    }\n"
            "    *returnSize = n;\n"
            "    return t;\n"
            "}\n"
        ),
        "go": (
            "func transpose(matrix [][]int) [][]int {\n"
            "    t := make([][]int, len(matrix[0]))\n"
            "    for j := range t {\n"
            "        t[j] = make([]int, len(matrix))\n"
            "        for i := range matrix {\n"
            "            t[j][i] = matrix[i][j]\n"
            "        }\n"
            "    }\n"
            "    return t\n"
            "}\n"
        ),
        "rust": (
            "impl Solution {\n"
            "    pub fn transpose(matrix: Vec<Vec<i32>>) -> Vec<Vec<i32>> {\n"
            "        (0..matrix[0].len()).map(|j| matrix.iter().map(|r| r[j]).collect()).collect()\n"
            "    }\n"
            "}\n"
        ),
    },
)

pattern(
    "string_array_in",
    _fn("longestCommonPrefix", rust="longest_common_prefix"),
    [({"strs": ["flower", "flow", "flight"]}, "fl"), ({"strs": ["dog", "racecar", "car"]}, "")],
    {
        "python": (
            "class Solution:\n"
            "    def longestCommonPrefix(self, strs: List[str]) -> str:\n"
            "        p = strs[0]\n"
            "        for s in strs:\n"
            "            while not s.startswith(p):\n"
            "                p = p[:-1]\n"
            "        return p\n"
        ),
        "javascript": (
            "var longestCommonPrefix = function(strs) {\n"
            "    let p = strs[0];\n"
            "    for (const s of strs) while (!s.startsWith(p)) p = p.slice(0, -1);\n"
            "    return p;\n"
            "};\n"
        ),
        "typescript": (
            "function longestCommonPrefix(strs: string[]): string {\n"
            "    let p = strs[0];\n"
            "    for (const s of strs) while (!s.startsWith(p)) p = p.slice(0, -1);\n"
            "    return p;\n"
            "}\n"
        ),
        "java": (
            "class Solution {\n"
            "    public String longestCommonPrefix(String[] strs) {\n"
            "        String p = strs[0];\n"
            "        for (String s : strs) while (!s.startsWith(p)) p = p.substring(0, p.length() - 1);\n"
            "        return p;\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": (
            "class Solution {\n"
            "    fun longestCommonPrefix(strs: Array<String>): String {\n"
            "        var p = strs[0]\n"
            "        for (s in strs) while (!s.startsWith(p)) p = p.dropLast(1)\n"
            "        return p\n"
            "    }\n"
            "}\n"
        ),
        "csharp": (
            "public class Solution {\n"
            "    public string LongestCommonPrefix(string[] strs) {\n"
            "        string p = strs[0];\n"
            "        foreach (var s in strs) while (!s.StartsWith(p)) p = p.Substring(0, p.Length - 1);\n"
            "        return p;\n"
            "    }\n"
            "}\n"
        ),
        "cpp": (
            "class Solution {\n"
            "public:\n"
            "    string longestCommonPrefix(vector<string>& strs) {\n"
            "        string p = strs[0];\n"
            "        for (auto& s : strs) while (s.rfind(p, 0) != 0) p.pop_back();\n"
            "        return p;\n"
            "    }\n"
            "};\n"
        ),
        "c": (
            "char* longestCommonPrefix(char** strs, int strsSize) {\n"
            "    char* p = malloc(strlen(strs[0]) + 1);\n"
            "    strcpy(p, strs[0]);\n"
            "    for (int i = 1; i < strsSize; i++) {\n"
            "        int j = 0;\n"
            "        while (p[j] && strs[i][j] && p[j] == strs[i][j]) j++;\n"
            "        p[j] = '\\0';\n"
            "    }\n"
            "    return p;\n"
            "}\n"
        ),
        "go": (
            "func longestCommonPrefix(strs []string) string {\n"
            "    p := strs[0]\n"
            "    for _, s := range strs {\n"
            "        for len(p) > 0 && (len(s) < len(p) || s[:len(p)] != p) {\n"
            "            p = p[:len(p)-1]\n"
            "        }\n"
            "    }\n"
            "    return p\n"
            "}\n"
        ),
        "rust": (
            "impl Solution {\n"
            "    pub fn longest_common_prefix(strs: Vec<String>) -> String {\n"
            "        let mut p = strs[0].clone();\n"
            "        for s in &strs {\n"
            "            while !s.starts_with(&p) {\n"
            "                p.pop();\n"
            "            }\n"
            "        }\n"
            "        p\n"
            "    }\n"
            "}\n"
        ),
    },
)

pattern(
    "string_array_out",
    _fn("fizzBuzz", rust="fizz_buzz"),
    [({"n": 5}, ["1", "2", "Fizz", "4", "Buzz"])],
    {
        "python": (
            "class Solution:\n"
            "    def fizzBuzz(self, n: int) -> List[str]:\n"
            "        return ['FizzBuzz' if i % 15 == 0 else 'Fizz' if i % 3 == 0 else 'Buzz' if i % 5 == 0 else str(i) for i in range(1, n + 1)]\n"
        ),
        "javascript": (
            "var fizzBuzz = function(n) {\n"
            "    const r = [];\n"
            "    for (let i = 1; i <= n; i++) r.push(i % 15 === 0 ? 'FizzBuzz' : i % 3 === 0 ? 'Fizz' : i % 5 === 0 ? 'Buzz' : String(i));\n"
            "    return r;\n"
            "};\n"
        ),
        "typescript": (
            "function fizzBuzz(n: number): string[] {\n"
            "    const r: string[] = [];\n"
            "    for (let i = 1; i <= n; i++) r.push(i % 15 === 0 ? 'FizzBuzz' : i % 3 === 0 ? 'Fizz' : i % 5 === 0 ? 'Buzz' : String(i));\n"
            "    return r;\n"
            "}\n"
        ),
        "java": (
            "class Solution {\n"
            "    public List<String> fizzBuzz(int n) {\n"
            "        List<String> r = new ArrayList<>();\n"
            "        for (int i = 1; i <= n; i++) r.add(i % 15 == 0 ? \"FizzBuzz\" : i % 3 == 0 ? \"Fizz\" : i % 5 == 0 ? \"Buzz\" : String.valueOf(i));\n"
            "        return r;\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": (
            "class Solution {\n"
            "    fun fizzBuzz(n: Int): List<String> {\n"
            "        return (1..n).map { if (it % 15 == 0) \"FizzBuzz\" else if (it % 3 == 0) \"Fizz\" else if (it % 5 == 0) \"Buzz\" else it.toString() }\n"
            "    }\n"
            "}\n"
        ),
        "csharp": (
            "public class Solution {\n"
            "    public IList<string> FizzBuzz(int n) {\n"
            "        var r = new List<string>();\n"
            "        for (int i = 1; i <= n; i++) r.Add(i % 15 == 0 ? \"FizzBuzz\" : i % 3 == 0 ? \"Fizz\" : i % 5 == 0 ? \"Buzz\" : i.ToString());\n"
            "        return r;\n"
            "    }\n"
            "}\n"
        ),
        "cpp": (
            "class Solution {\n"
            "public:\n"
            "    vector<string> fizzBuzz(int n) {\n"
            "        vector<string> r;\n"
            "        for (int i = 1; i <= n; i++) r.push_back(i % 15 == 0 ? \"FizzBuzz\" : i % 3 == 0 ? \"Fizz\" : i % 5 == 0 ? \"Buzz\" : to_string(i));\n"
            "        return r;\n"
            "    }\n"
            "};\n"
        ),
        "c": (
            "char** fizzBuzz(int n, int* returnSize) {\n"
            "    char** r = malloc(n * sizeof(char*));\n"
            "    for (int i = 1; i <= n; i++) {\n"
            "        r[i - 1] = malloc(16);\n"
            "        if (i % 15 == 0) strcpy(r[i - 1], \"FizzBuzz\");\n"
            "        else if (i % 3 == 0) strcpy(r[i - 1], \"Fizz\");\n"
            "        else if (i % 5 == 0) strcpy(r[i - 1], \"Buzz\");\n"
            "        else sprintf(r[i - 1], \"%d\", i);\n"
            "    }\n"
            "    *returnSize = n;\n"
            "    return r;\n"
            "}\n"
        ),
        "go": (
            "import \"strconv\"\n"
            "\n"
            "func fizzBuzz(n int) []string {\n"
            "    r := []string{}\n"
            "    for i := 1; i <= n; i++ {\n"
            "        switch {\n"
            "        case i%15 == 0:\n"
            "            r = append(r, \"FizzBuzz\")\n"
            "        case i%3 == 0:\n"
            "            r = append(r, \"Fizz\")\n"
            "        case i%5 == 0:\n"
            "            r = append(r, \"Buzz\")\n"
            "        default:\n"
            "            r = append(r, strconv.Itoa(i))\n"
            "        }\n"
            "    }\n"
            "    return r\n"
            "}\n"
        ),
        "rust": (
            "impl Solution {\n"
            "    pub fn fizz_buzz(n: i32) -> Vec<String> {\n"
            "        (1..=n).map(|i| match (i % 3, i % 5) {\n"
            "            (0, 0) => \"FizzBuzz\".to_string(),\n"
            "            (0, _) => \"Fizz\".to_string(),\n"
            "            (_, 0) => \"Buzz\".to_string(),\n"
            "            _ => i.to_string(),\n"
            "        }).collect()\n"
            "    }\n"
            "}\n"
        ),
    },
)

pattern(
    "char_grid",
    _fn("numIslands", rust="num_islands"),
    [({"grid": [["1", "1", "0", "0"], ["1", "0", "0", "1"], ["0", "0", "1", "1"]]}, 2)],
    {
        "python": (
            "class Solution:\n"
            "    def numIslands(self, grid: List[List[str]]) -> int:\n"
            "        def dfs(i, j):\n"
            "            if 0 <= i < len(grid) and 0 <= j < len(grid[0]) and grid[i][j] == '1':\n"
            "                grid[i][j] = '0'\n"
            "                dfs(i + 1, j); dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1)\n"
            "        count = 0\n"
            "        for i in range(len(grid)):\n"
            "            for j in range(len(grid[0])):\n"
            "                if grid[i][j] == '1':\n"
            "                    count += 1\n"
            "                    dfs(i, j)\n"
            "        return count\n"
        ),
        "javascript": (
            "var numIslands = function(grid) {\n"
            "    const dfs = (i, j) => {\n"
            "        if (i < 0 || j < 0 || i >= grid.length || j >= grid[0].length || grid[i][j] !== '1') return;\n"
            "        grid[i][j] = '0';\n"
            "        dfs(i + 1, j); dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1);\n"
            "    };\n"
            "    let c = 0;\n"
            "    for (let i = 0; i < grid.length; i++)\n"
            "        for (let j = 0; j < grid[0].length; j++)\n"
            "            if (grid[i][j] === '1') { c++; dfs(i, j); }\n"
            "    return c;\n"
            "};\n"
        ),
        "typescript": (
            "function numIslands(grid: string[][]): number {\n"
            "    const dfs = (i: number, j: number): void => {\n"
            "        if (i < 0 || j < 0 || i >= grid.length || j >= grid[0].length || grid[i][j] !== '1') return;\n"
            "        grid[i][j] = '0';\n"
            "        dfs(i + 1, j); dfs(i - 1, j); dfs(i, j + 1); dfs(i, j - 1);\n"
            "    };\n"
            "    let c = 0;\n"
            "    for (let i = 0; i < grid.length; i++)\n"
            "        for (let j = 0; j < grid[0].length; j++)\n"
            "            if (grid[i][j] === '1') { c++; dfs(i, j); }\n"
            "    return c;\n"
            "}\n"
        ),
        "java": (
            "class Solution {\n"
            "    public int numIslands(char[][] grid) {\n"
            "        int c = 0;\n"
            "        for (int i = 0; i < grid.length; i++)\n"
            "            for (int j = 0; j < grid[0].length; j++)\n"
            "                if (grid[i][j] == '1') { c++; dfs(grid, i, j); }\n"
            "        return c;\n"
            "    }\n"
            "    private void dfs(char[][] g, int i, int j) {\n"
            "        if (i < 0 || j < 0 || i >= g.length || j >= g[0].length || g[i][j] != '1') return;\n"
            "        g[i][j] = '0';\n"
            "        dfs(g, i + 1, j); dfs(g, i - 1, j); dfs(g, i, j + 1); dfs(g, i, j - 1);\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": (
            "class Solution {\n"
            "    fun numIslands(grid: Array<CharArray>): Int {\n"
            "        var c = 0\n"
            "        for (i in grid.indices) for (j in grid[0].indices) if (grid[i][j] == '1') { c++; dfs(grid, i, j) }\n"
            "        return c\n"
            "    }\n"
            "    private fun dfs(g: Array<CharArray>, i: Int, j: Int) {\n"
            "        if (i < 0 || j < 0 || i >= g.size || j >= g[0].size || g[i][j] != '1') return\n"
            "        g[i][j] = '0'\n"
            "        dfs(g, i + 1, j); dfs(g, i - 1, j); dfs(g, i, j + 1); dfs(g, i, j - 1)\n"
            "    }\n"
            "}\n"
        ),
        "csharp": (
            "public class Solution {\n"
            "    public int NumIslands(char[][] grid) {\n"
            "        int c = 0;\n"
            "        for (int i = 0; i < grid.Length; i++)\n"
            "            for (int j = 0; j < grid[0].Length; j++)\n"
            "                if (grid[i][j] == '1') { c++; Dfs(grid, i, j); }\n"
            "        return c;\n"
            "    }\n"
            "    private void Dfs(char[][] g, int i, int j) {\n"
            "        if (i < 0 || j < 0 || i >= g.Length || j >= g[0].Length || g[i][j] != '1') return;\n"
            "        g[i][j] = '0';\n"
            "        Dfs(g, i + 1, j); Dfs(g, i - 1, j); Dfs(g, i, j + 1); Dfs(g, i, j - 1);\n"
            "    }\n"
            "}\n"
        ),
        "cpp": (
            "class Solution {\n"
            "public:\n"
            "    int numIslands(vector<vector<char>>& grid) {\n"
            "        int c = 0;\n"
            "        for (int i = 0; i < (int)grid.size(); i++)\n"
            "            for (int j = 0; j < (int)grid[0].size(); j++)\n"
            "                if (grid[i][j] == '1') { c++; dfs(grid, i, j); }\n"
            "        return c;\n"
            "    }\n"
            "    void dfs(vector<vector<char>>& g, int i, int j) {\n"
            "        if (i < 0 || j < 0 || i >= (int)g.size() || j >= (int)g[0].size() || g[i][j] != '1') return;\n"
            "        g[i][j] = '0';\n"
            "        dfs(g, i + 1, j); dfs(g, i - 1, j); dfs(g, i, j + 1); dfs(g, i, j - 1);\n"
            "    }\n"
            "};\n"
        ),
        "c": (
            "void dfs(char** g, int m, int n, int i, int j) {\n"
            "    if (i < 0 || j < 0 || i >= m || j >= n || g[i][j] != '1') return;\n"
            "    g[i][j] = '0';\n"
            "    dfs(g, m, n, i + 1, j); dfs(g, m, n, i - 1, j); dfs(g, m, n, i, j + 1); dfs(g, m, n, i, j - 1);\n"
            "}\n"
            "\n"
            "int numIslands(char** grid, int gridSize, int* gridColSize) {\n"
            "    int c = 0;\n"
            "    for (int i = 0; i < gridSize; i++)\n"
            "        for (int j = 0; j < gridColSize[i]; j++)\n"
            "            if (grid[i][j] == '1') { c++; dfs(grid, gridSize, gridColSize[0], i, j); }\n"
            "    return c;\n"
            "}\n"
        ),
        "go": (
            "func numIslands(grid [][]byte) int {\n"
            "    var dfs func(i, j int)\n"
            "    dfs = func(i, j int) {\n"
            "        if i < 0 || j < 0 || i >= len(grid) || j >= len(grid[0]) || grid[i][j] != '1' {\n"
            "            return\n"
            "        }\n"
            "        grid[i][j] = '0'\n"
            "        dfs(i+1, j); dfs(i-1, j); dfs(i, j+1); dfs(i, j-1)\n"
            "    }\n"
            "    c := 0\n"
            "    for i := range grid {\n"
            "        for j := range grid[0] {\n"
            "            if grid[i][j] == '1' {\n"
            "                c++\n"
            "                dfs(i, j)\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "    return c\n"
            "}\n"
        ),
        "rust": (
            "impl Solution {\n"
            "    pub fn num_islands(grid: Vec<Vec<char>>) -> i32 {\n"
            "        let mut g = grid;\n"
            "        let mut c = 0;\n"
            "        for i in 0..g.len() {\n"
            "            for j in 0..g[0].len() {\n"
            "                if g[i][j] == '1' {\n"
            "                    c += 1;\n"
            "                    Self::dfs(&mut g, i as i32, j as i32);\n"
            "                }\n"
            "            }\n"
            "        }\n"
            "        c\n"
            "    }\n"
            "    fn dfs(g: &mut Vec<Vec<char>>, i: i32, j: i32) {\n"
            "        if i < 0 || j < 0 || i as usize >= g.len() || j as usize >= g[0].len() || g[i as usize][j as usize] != '1' {\n"
            "            return;\n"
            "        }\n"
            "        g[i as usize][j as usize] = '0';\n"
            "        Self::dfs(g, i + 1, j); Self::dfs(g, i - 1, j); Self::dfs(g, i, j + 1); Self::dfs(g, i, j - 1);\n"
            "    }\n"
            "}\n"
        ),
    },
)

pattern(
    "nested_list_out",
    _fn("generate"),
    [({"numRows": 4}, [[1], [1, 1], [1, 2, 1], [1, 3, 3, 1]])],
    {
        "python": (
            "class Solution:\n"
            "    def generate(self, numRows: int) -> List[List[int]]:\n"
            "        rows = [[1]]\n"
            "        for _ in range(numRows - 1):\n"
            "            rows.append([1] + [a + b for a, b in zip(rows[-1], rows[-1][1:])] + [1])\n"
            "        return rows\n"
        ),
        "javascript": (
            "var generate = function(numRows) {\n"
            "    const rows = [[1]];\n"
            "    for (let i = 1; i < numRows; i++) {\n"
            "        const p = rows[i - 1], r = [1];\n"
            "        for (let j = 1; j < i; j++) r.push(p[j - 1] + p[j]);\n"
            "        r.push(1);\n"
            "        rows.push(r);\n"
            "    }\n"
            "    return rows;\n"
            "};\n"
        ),
        "typescript": (
            "function generate(numRows: number): number[][] {\n"
            "    const rows: number[][] = [[1]];\n"
            "    for (let i = 1; i < numRows; i++) {\n"
            "        const p = rows[i - 1], r = [1];\n"
            "        for (let j = 1; j < i; j++) r.push(p[j - 1] + p[j]);\n"
            "        r.push(1);\n"
            "        rows.push(r);\n"
            "    }\n"
            "    return rows;\n"
            "}\n"
        ),
        "java": (
            "class Solution {\n"
            "    public List<List<Integer>> generate(int numRows) {\n"
            "        List<List<Integer>> rows = new ArrayList<>();\n"
            "        for (int i = 0; i < numRows; i++) {\n"
            "            List<Integer> r = new ArrayList<>();\n"
            "            for (int j = 0; j <= i; j++) r.add(j == 0 || j == i ? 1 : rows.get(i - 1).get(j - 1) + rows.get(i - 1).get(j));\n"
            "            rows.add(r);\n"
            "        }\n"
            "        return rows;\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": (
            "class Solution {\n"
            "    fun generate(numRows: Int): List<List<Int>> {\n"
            "        val rows = mutableListOf<List<Int>>()\n"
            "        for (i in 0 until numRows) rows.add(List(i + 1) { j -> if (j == 0 || j == i) 1 else rows[i - 1][j - 1] + rows[i - 1][j] })\n"
            "        return rows\n"
            "    }\n"
            "}\n"
        ),
        "csharp": (
            "public class Solution {\n"
            "    public IList<IList<int>> Generate(int numRows) {\n"
            "        var rows = new List<IList<int>>();\n"
            "        for (int i = 0; i < numRows; i++) {\n"
            "            var r = new List<int>();\n"
            "            for (int j = 0; j <= i; j++) r.Add(j == 0 || j == i ? 1 : rows[i - 1][j - 1] + rows[i - 1][j]);\n"
            "            rows.Add(r);\n"
            "        }\n"
            "        return rows;\n"
            "    }\n"
            "}\n"
        ),
        "cpp": (
            "class Solution {\n"
            "public:\n"
            "    vector<vector<int>> generate(int numRows) {\n"
            "        vector<vector<int>> rows;\n"
            "        for (int i = 0; i < numRows; i++) {\n"
            "            vector<int> r(i + 1, 1);\n"
            "            for (int j = 1; j < i; j++) r[j] = rows[i - 1][j - 1] + rows[i - 1][j];\n"
            "            rows.push_back(r);\n"
            "        }\n"
            "        return rows;\n"
            "    }\n"
            "};\n"
        ),
        "c": (
            "int** generate(int numRows, int* returnSize, int** returnColumnSizes) {\n"
            "    int** r = malloc(numRows * sizeof(int*));\n"
            "    *returnColumnSizes = malloc(numRows * sizeof(int));\n"
            "    for (int i = 0; i < numRows; i++) {\n"
            "        r[i] = malloc((i + 1) * sizeof(int));\n"
            "        (*returnColumnSizes)[i] = i + 1;\n"
            "        r[i][0] = r[i][i] = 1;\n"
            "        for (int j = 1; j < i; j++) r[i][j] = r[i - 1][j - 1] + r[i - 1][j];\n"
            "    }\n"
            "    *returnSize = numRows;\n"
            "    return r;\n"
            "}\n"
        ),
        "go": (
            "func generate(numRows int) [][]int {\n"
            "    rows := [][]int{}\n"
            "    for i := 0; i < numRows; i++ {\n"
            "        r := make([]int, i+1)\n"
            "        r[0], r[i] = 1, 1\n"
            "        for j := 1; j < i; j++ {\n"
            "            r[j] = rows[i-1][j-1] + rows[i-1][j]\n"
            "        }\n"
            "        rows = append(rows, r)\n"
            "    }\n"
            "    return rows\n"
            "}\n"
        ),
        "rust": (
            "impl Solution {\n"
            "    pub fn generate(num_rows: i32) -> Vec<Vec<i32>> {\n"
            "        let mut rows: Vec<Vec<i32>> = vec![];\n"
            "        for i in 0..num_rows as usize {\n"
            "            let mut r = vec![1; i + 1];\n"
            "            for j in 1..i {\n"
            "                r[j] = rows[i - 1][j - 1] + rows[i - 1][j];\n"
            "            }\n"
            "            rows.push(r);\n"
            "        }\n"
            "        rows\n"
            "    }\n"
            "}\n"
        ),
    },
)

pattern(
    "mixed_args",
    _fn("describe"),
    [({"s": "x", "nums": [1, 2], "k": 2}, "x:6")],
    {
        "python": "class Solution:\n    def describe(self, s: str, nums: List[int], k: int) -> str:\n        return f'{s}:{sum(nums) * k}'\n",
        "javascript": "var describe = function(s, nums, k) {\n    return s + ':' + nums.reduce((a, b) => a + b, 0) * k;\n};\n",
        "typescript": "function describe(s: string, nums: number[], k: number): string {\n    return s + ':' + nums.reduce((a, b) => a + b, 0) * k;\n}\n",
        "java": "class Solution {\n    public String describe(String s, int[] nums, int k) {\n        int t = 0;\n        for (int n : nums) t += n;\n        return s + \":\" + (t * k);\n    }\n}\n",
        "kotlin": "class Solution {\n    fun describe(s: String, nums: IntArray, k: Int): String {\n        return s + \":\" + (nums.sum() * k)\n    }\n}\n",
        "csharp": "public class Solution {\n    public string Describe(string s, int[] nums, int k) {\n        return s + \":\" + (nums.Sum() * k);\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    string describe(string s, vector<int>& nums, int k) {\n        return s + \":\" + to_string(accumulate(nums.begin(), nums.end(), 0) * k);\n    }\n};\n",
        "c": "char* describe(char* s, int* nums, int numsSize, int k) {\n    int t = 0;\n    for (int i = 0; i < numsSize; i++) t += nums[i];\n    char* r = malloc(strlen(s) + 16);\n    sprintf(r, \"%s:%d\", s, t * k);\n    return r;\n}\n",
        "go": "import \"strconv\"\n\nfunc describe(s string, nums []int, k int) string {\n    t := 0\n    for _, n := range nums {\n        t += n\n    }\n    return s + \":\" + strconv.Itoa(t*k)\n}\n",
        "rust": "impl Solution {\n    pub fn describe(s: String, nums: Vec<i32>, k: i32) -> String {\n        format!(\"{}:{}\", s, nums.iter().sum::<i32>() * k)\n    }\n}\n",
    },
)

# ---------------------------------------------------------------------------
# In-place (void) functions: the judge compares the mutated first argument.
# ---------------------------------------------------------------------------

pattern(
    "inplace_ints",
    _fn("moveZeroes", rust="move_zeroes"),
    [({"nums": [0, 1, 0, 3, 12]}, [1, 3, 12, 0, 0])],
    {
        "python": (
            "class Solution:\n"
            "    def moveZeroes(self, nums: List[int]) -> None:\n"
            "        k = 0\n"
            "        for n in nums:\n"
            "            if n != 0:\n"
            "                nums[k] = n\n"
            "                k += 1\n"
            "        for i in range(k, len(nums)):\n"
            "            nums[i] = 0\n"
        ),
        "javascript": (
            "var moveZeroes = function(nums) {\n"
            "    let k = 0;\n"
            "    for (const n of nums) if (n !== 0) nums[k++] = n;\n"
            "    while (k < nums.length) nums[k++] = 0;\n"
            "};\n"
        ),
        "typescript": (
            "function moveZeroes(nums: number[]): void {\n"
            "    let k = 0;\n"
            "    for (const n of nums) if (n !== 0) nums[k++] = n;\n"
            "    while (k < nums.length) nums[k++] = 0;\n"
            "}\n"
        ),
        "java": (
            "class Solution {\n"
            "    public void moveZeroes(int[] nums) {\n"
            "        int k = 0;\n"
            "        for (int n : nums) if (n != 0) nums[k++] = n;\n"
            "        while (k < nums.length) nums[k++] = 0;\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": (
            "class Solution {\n"
            "    fun moveZeroes(nums: IntArray): Unit {\n"
            "        var k = 0\n"
            "        for (n in nums) if (n != 0) nums[k++] = n\n"
            "        while (k < nums.size) nums[k++] = 0\n"
            "    }\n"
            "}\n"
        ),
        "csharp": (
            "public class Solution {\n"
            "    public void MoveZeroes(int[] nums) {\n"
            "        int k = 0;\n"
            "        foreach (var n in nums.ToArray()) if (n != 0) nums[k++] = n;\n"
            "        while (k < nums.Length) nums[k++] = 0;\n"
            "    }\n"
            "}\n"
        ),
        "cpp": (
            "class Solution {\n"
            "public:\n"
            "    void moveZeroes(vector<int>& nums) {\n"
            "        int k = 0;\n"
            "        for (int n : nums) if (n != 0) nums[k++] = n;\n"
            "        while (k < (int)nums.size()) nums[k++] = 0;\n"
            "    }\n"
            "};\n"
        ),
        "c": (
            "void moveZeroes(int* nums, int numsSize) {\n"
            "    int k = 0;\n"
            "    for (int i = 0; i < numsSize; i++) if (nums[i] != 0) nums[k++] = nums[i];\n"
            "    while (k < numsSize) nums[k++] = 0;\n"
            "}\n"
        ),
        "go": (
            "func moveZeroes(nums []int) {\n"
            "    k := 0\n"
            "    for _, n := range nums {\n"
            "        if n != 0 {\n"
            "            nums[k] = n\n"
            "            k++\n"
            "        }\n"
            "    }\n"
            "    for ; k < len(nums); k++ {\n"
            "        nums[k] = 0\n"
            "    }\n"
            "}\n"
        ),
        "rust": (
            "impl Solution {\n"
            "    pub fn move_zeroes(nums: &mut Vec<i32>) {\n"
            "        let mut k = 0;\n"
            "        for i in 0..nums.len() {\n"
            "            if nums[i] != 0 {\n"
            "                nums[k] = nums[i];\n"
            "                k += 1;\n"
            "            }\n"
            "        }\n"
            "        for i in k..nums.len() {\n"
            "            nums[i] = 0;\n"
            "        }\n"
            "    }\n"
            "}\n"
        ),
    },
)

pattern(
    "inplace_chars",
    _fn("reverseString", rust="reverse_string"),
    [({"s": ["h", "e", "l", "l", "o"]}, ["o", "l", "l", "e", "h"])],
    {
        "python": "class Solution:\n    def reverseString(self, s: List[str]) -> None:\n        s.reverse()\n",
        "javascript": "var reverseString = function(s) {\n    s.reverse();\n};\n",
        "typescript": "function reverseString(s: string[]): void {\n    s.reverse();\n}\n",
        "java": (
            "class Solution {\n"
            "    public void reverseString(char[] s) {\n"
            "        for (int i = 0, j = s.length - 1; i < j; i++, j--) { char t = s[i]; s[i] = s[j]; s[j] = t; }\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": "class Solution {\n    fun reverseString(s: CharArray): Unit {\n        s.reverse()\n    }\n}\n",
        "csharp": "public class Solution {\n    public void ReverseString(char[] s) {\n        Array.Reverse(s);\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    void reverseString(vector<char>& s) {\n        reverse(s.begin(), s.end());\n    }\n};\n",
        "c": (
            "void reverseString(char* s, int sSize) {\n"
            "    for (int i = 0, j = sSize - 1; i < j; i++, j--) { char t = s[i]; s[i] = s[j]; s[j] = t; }\n"
            "}\n"
        ),
        "go": (
            "func reverseString(s []byte) {\n"
            "    for i, j := 0, len(s)-1; i < j; i, j = i+1, j-1 {\n"
            "        s[i], s[j] = s[j], s[i]\n"
            "    }\n"
            "}\n"
        ),
        "rust": "impl Solution {\n    pub fn reverse_string(s: &mut Vec<char>) {\n        s.reverse();\n    }\n}\n",
    },
)

# ---------------------------------------------------------------------------
# Trees and linked lists
# ---------------------------------------------------------------------------

pattern(
    "tree_in",
    _fn("maxDepth", rust="max_depth"),
    [({"root": [3, 9, 20, None, None, 15, 7]}, 3), ({"root": []}, 0)],
    {
        "python": (
            "class Solution:\n"
            "    def maxDepth(self, root: Optional[TreeNode]) -> int:\n"
            "        if not root:\n"
            "            return 0\n"
            "        return 1 + max(self.maxDepth(root.left), self.maxDepth(root.right))\n"
        ),
        "javascript": (
            "var maxDepth = function(root) {\n"
            "    if (!root) return 0;\n"
            "    return 1 + Math.max(maxDepth(root.left), maxDepth(root.right));\n"
            "};\n"
        ),
        "typescript": (
            "function maxDepth(root: TreeNode | null): number {\n"
            "    if (!root) return 0;\n"
            "    return 1 + Math.max(maxDepth(root.left), maxDepth(root.right));\n"
            "}\n"
        ),
        "java": (
            "class Solution {\n"
            "    public int maxDepth(TreeNode root) {\n"
            "        if (root == null) return 0;\n"
            "        return 1 + Math.max(maxDepth(root.left), maxDepth(root.right));\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": (
            "class Solution {\n"
            "    fun maxDepth(root: TreeNode?): Int {\n"
            "        if (root == null) return 0\n"
            "        return 1 + maxOf(maxDepth(root.left), maxDepth(root.right))\n"
            "    }\n"
            "}\n"
        ),
        "csharp": (
            "public class Solution {\n"
            "    public int MaxDepth(TreeNode root) {\n"
            "        if (root == null) return 0;\n"
            "        return 1 + Math.Max(MaxDepth(root.left), MaxDepth(root.right));\n"
            "    }\n"
            "}\n"
        ),
        "cpp": (
            "class Solution {\n"
            "public:\n"
            "    int maxDepth(TreeNode* root) {\n"
            "        if (!root) return 0;\n"
            "        return 1 + max(maxDepth(root->left), maxDepth(root->right));\n"
            "    }\n"
            "};\n"
        ),
        "c": (
            "int maxDepth(struct TreeNode* root) {\n"
            "    if (!root) return 0;\n"
            "    int l = maxDepth(root->left), r = maxDepth(root->right);\n"
            "    return 1 + (l > r ? l : r);\n"
            "}\n"
        ),
        "go": (
            "func maxDepth(root *TreeNode) int {\n"
            "    if root == nil {\n"
            "        return 0\n"
            "    }\n"
            "    l, r := maxDepth(root.Left), maxDepth(root.Right)\n"
            "    if l > r {\n"
            "        return l + 1\n"
            "    }\n"
            "    return r + 1\n"
            "}\n"
        ),
        "rust": (
            "use std::rc::Rc;\n"
            "use std::cell::RefCell;\n"
            "\n"
            "impl Solution {\n"
            "    pub fn max_depth(root: Option<Rc<RefCell<TreeNode>>>) -> i32 {\n"
            "        match root {\n"
            "            None => 0,\n"
            "            Some(n) => {\n"
            "                let n = n.borrow();\n"
            "                1 + Self::max_depth(n.left.clone()).max(Self::max_depth(n.right.clone()))\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "}\n"
        ),
    },
)

pattern(
    "tree_out",
    _fn("invertTree", rust="invert_tree"),
    [({"root": [4, 2, 7, 1, 3, 6, 9]}, [4, 7, 2, 9, 6, 3, 1]), ({"root": []}, [])],
    {
        "python": (
            "class Solution:\n"
            "    def invertTree(self, root: Optional[TreeNode]) -> Optional[TreeNode]:\n"
            "        if root:\n"
            "            root.left, root.right = self.invertTree(root.right), self.invertTree(root.left)\n"
            "        return root\n"
        ),
        "javascript": (
            "var invertTree = function(root) {\n"
            "    if (root) [root.left, root.right] = [invertTree(root.right), invertTree(root.left)];\n"
            "    return root;\n"
            "};\n"
        ),
        "typescript": (
            "function invertTree(root: TreeNode | null): TreeNode | null {\n"
            "    if (root) [root.left, root.right] = [invertTree(root.right), invertTree(root.left)];\n"
            "    return root;\n"
            "}\n"
        ),
        "java": (
            "class Solution {\n"
            "    public TreeNode invertTree(TreeNode root) {\n"
            "        if (root == null) return null;\n"
            "        TreeNode l = invertTree(root.left);\n"
            "        root.left = invertTree(root.right);\n"
            "        root.right = l;\n"
            "        return root;\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": (
            "class Solution {\n"
            "    fun invertTree(root: TreeNode?): TreeNode? {\n"
            "        if (root == null) return null\n"
            "        val l = invertTree(root.left)\n"
            "        root.left = invertTree(root.right)\n"
            "        root.right = l\n"
            "        return root\n"
            "    }\n"
            "}\n"
        ),
        "csharp": (
            "public class Solution {\n"
            "    public TreeNode InvertTree(TreeNode root) {\n"
            "        if (root == null) return null;\n"
            "        var l = InvertTree(root.left);\n"
            "        root.left = InvertTree(root.right);\n"
            "        root.right = l;\n"
            "        return root;\n"
            "    }\n"
            "}\n"
        ),
        "cpp": (
            "class Solution {\n"
            "public:\n"
            "    TreeNode* invertTree(TreeNode* root) {\n"
            "        if (!root) return nullptr;\n"
            "        swap(root->left, root->right);\n"
            "        invertTree(root->left);\n"
            "        invertTree(root->right);\n"
            "        return root;\n"
            "    }\n"
            "};\n"
        ),
        "c": (
            "struct TreeNode* invertTree(struct TreeNode* root) {\n"
            "    if (!root) return NULL;\n"
            "    struct TreeNode* l = invertTree(root->left);\n"
            "    root->left = invertTree(root->right);\n"
            "    root->right = l;\n"
            "    return root;\n"
            "}\n"
        ),
        "go": (
            "func invertTree(root *TreeNode) *TreeNode {\n"
            "    if root == nil {\n"
            "        return nil\n"
            "    }\n"
            "    root.Left, root.Right = invertTree(root.Right), invertTree(root.Left)\n"
            "    return root\n"
            "}\n"
        ),
        "rust": (
            "use std::rc::Rc;\n"
            "use std::cell::RefCell;\n"
            "\n"
            "impl Solution {\n"
            "    pub fn invert_tree(root: Option<Rc<RefCell<TreeNode>>>) -> Option<Rc<RefCell<TreeNode>>> {\n"
            "        if let Some(node) = root.clone() {\n"
            "            let mut n = node.borrow_mut();\n"
            "            let l = n.left.take();\n"
            "            let r = n.right.take();\n"
            "            n.left = Self::invert_tree(r);\n"
            "            n.right = Self::invert_tree(l);\n"
            "        }\n"
            "        root\n"
            "    }\n"
            "}\n"
        ),
    },
)

pattern(
    "linked_list",
    _fn("reverseList", rust="reverse_list"),
    [({"head": [1, 2, 3, 4, 5]}, [5, 4, 3, 2, 1]), ({"head": []}, [])],
    {
        "python": (
            "class Solution:\n"
            "    def reverseList(self, head: Optional[ListNode]) -> Optional[ListNode]:\n"
            "        prev = None\n"
            "        while head:\n"
            "            head.next, prev, head = prev, head, head.next\n"
            "        return prev\n"
        ),
        "javascript": (
            "var reverseList = function(head) {\n"
            "    let prev = null;\n"
            "    while (head) { const n = head.next; head.next = prev; prev = head; head = n; }\n"
            "    return prev;\n"
            "};\n"
        ),
        "typescript": (
            "function reverseList(head: ListNode | null): ListNode | null {\n"
            "    let prev: ListNode | null = null;\n"
            "    while (head) { const n: ListNode | null = head.next; head.next = prev; prev = head; head = n; }\n"
            "    return prev;\n"
            "}\n"
        ),
        "java": (
            "class Solution {\n"
            "    public ListNode reverseList(ListNode head) {\n"
            "        ListNode prev = null;\n"
            "        while (head != null) { ListNode n = head.next; head.next = prev; prev = head; head = n; }\n"
            "        return prev;\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": (
            "class Solution {\n"
            "    fun reverseList(head: ListNode?): ListNode? {\n"
            "        var prev: ListNode? = null\n"
            "        var cur = head\n"
            "        while (cur != null) { val n = cur.next; cur.next = prev; prev = cur; cur = n }\n"
            "        return prev\n"
            "    }\n"
            "}\n"
        ),
        "csharp": (
            "public class Solution {\n"
            "    public ListNode ReverseList(ListNode head) {\n"
            "        ListNode prev = null;\n"
            "        while (head != null) { var n = head.next; head.next = prev; prev = head; head = n; }\n"
            "        return prev;\n"
            "    }\n"
            "}\n"
        ),
        "cpp": (
            "class Solution {\n"
            "public:\n"
            "    ListNode* reverseList(ListNode* head) {\n"
            "        ListNode* prev = nullptr;\n"
            "        while (head) { ListNode* n = head->next; head->next = prev; prev = head; head = n; }\n"
            "        return prev;\n"
            "    }\n"
            "};\n"
        ),
        "c": (
            "struct ListNode* reverseList(struct ListNode* head) {\n"
            "    struct ListNode* prev = NULL;\n"
            "    while (head) { struct ListNode* n = head->next; head->next = prev; prev = head; head = n; }\n"
            "    return prev;\n"
            "}\n"
        ),
        "go": (
            "func reverseList(head *ListNode) *ListNode {\n"
            "    var prev *ListNode\n"
            "    for head != nil {\n"
            "        head.Next, prev, head = prev, head, head.Next\n"
            "    }\n"
            "    return prev\n"
            "}\n"
        ),
        "rust": (
            "impl Solution {\n"
            "    pub fn reverse_list(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {\n"
            "        let mut prev = None;\n"
            "        let mut cur = head;\n"
            "        while let Some(mut n) = cur {\n"
            "            cur = n.next.take();\n"
            "            n.next = prev;\n"
            "            prev = Some(n);\n"
            "        }\n"
            "        prev\n"
            "    }\n"
            "}\n"
        ),
    },
)

pattern(
    "list_cycle",
    _fn("hasCycle"),
    [({"head": [3, 2, 0, -4], "pos": 1}, True), ({"head": [1], "pos": -1}, False)],
    {
        "python": (
            "class Solution:\n"
            "    def hasCycle(self, head: Optional[ListNode]) -> bool:\n"
            "        slow = fast = head\n"
            "        while fast and fast.next:\n"
            "            slow, fast = slow.next, fast.next.next\n"
            "            if slow is fast:\n"
            "                return True\n"
            "        return False\n"
        ),
        "javascript": (
            "var hasCycle = function(head) {\n"
            "    let slow = head, fast = head;\n"
            "    while (fast && fast.next) { slow = slow.next; fast = fast.next.next; if (slow === fast) return true; }\n"
            "    return false;\n"
            "};\n"
        ),
        "typescript": (
            "function hasCycle(head: ListNode | null): boolean {\n"
            "    let slow = head, fast = head;\n"
            "    while (fast && fast.next) { slow = slow!.next; fast = fast.next.next; if (slow === fast) return true; }\n"
            "    return false;\n"
            "}\n"
        ),
        "java": (
            "public class Solution {\n"
            "    public boolean hasCycle(ListNode head) {\n"
            "        ListNode slow = head, fast = head;\n"
            "        while (fast != null && fast.next != null) { slow = slow.next; fast = fast.next.next; if (slow == fast) return true; }\n"
            "        return false;\n"
            "    }\n"
            "}\n"
        ),
        "kotlin": (
            "class Solution {\n"
            "    fun hasCycle(head: ListNode?): Boolean {\n"
            "        var slow = head\n"
            "        var fast = head\n"
            "        while (fast?.next != null) { slow = slow?.next; fast = fast.next?.next; if (slow === fast) return true }\n"
            "        return false\n"
            "    }\n"
            "}\n"
        ),
        "csharp": (
            "public class Solution {\n"
            "    public bool HasCycle(ListNode head) {\n"
            "        ListNode slow = head, fast = head;\n"
            "        while (fast != null && fast.next != null) { slow = slow.next; fast = fast.next.next; if (slow == fast) return true; }\n"
            "        return false;\n"
            "    }\n"
            "}\n"
        ),
        "cpp": (
            "class Solution {\n"
            "public:\n"
            "    bool hasCycle(ListNode *head) {\n"
            "        ListNode *slow = head, *fast = head;\n"
            "        while (fast && fast->next) { slow = slow->next; fast = fast->next->next; if (slow == fast) return true; }\n"
            "        return false;\n"
            "    }\n"
            "};\n"
        ),
        "c": (
            "bool hasCycle(struct ListNode *head) {\n"
            "    struct ListNode *slow = head, *fast = head;\n"
            "    while (fast && fast->next) { slow = slow->next; fast = fast->next->next; if (slow == fast) return true; }\n"
            "    return false;\n"
            "}\n"
        ),
        "go": (
            "func hasCycle(head *ListNode) bool {\n"
            "    slow, fast := head, head\n"
            "    for fast != nil && fast.Next != nil {\n"
            "        slow, fast = slow.Next, fast.Next.Next\n"
            "        if slow == fast {\n"
            "            return true\n"
            "        }\n"
            "    }\n"
            "    return false\n"
            "}\n"
        ),
    },
)

# ---------------------------------------------------------------------------
# User code shapes
# ---------------------------------------------------------------------------

pattern(
    "user_imports",
    _fn("sortNums", rust="sort_nums"),
    [({"nums": [3, 1, 2]}, [1, 2, 3])],
    {
        "python": "import heapq\nfrom collections import deque\n\nclass Solution:\n    def sortNums(self, nums: List[int]) -> List[int]:\n        heapq.heapify(nums)\n        return [heapq.heappop(nums) for _ in range(len(nums))]\n",
        "javascript": "const util = require('util');\n\nvar sortNums = function(nums) {\n    return nums.sort((a, b) => a - b);\n};\n",
        "java": "import java.util.*;\nimport java.util.stream.*;\n\nclass Solution {\n    public List<Integer> sortNums(int[] nums) {\n        return Arrays.stream(nums).sorted().boxed().collect(Collectors.toList());\n    }\n}\n",
        "kotlin": "import java.util.PriorityQueue\n\nclass Solution {\n    fun sortNums(nums: IntArray): IntArray {\n        val pq = PriorityQueue<Int>()\n        nums.forEach { pq.add(it) }\n        return IntArray(nums.size) { pq.poll() }\n    }\n}\n",
        "csharp": "using System;\nusing System.Collections.Generic;\nusing System.Linq;\n\npublic class Solution {\n    public int[] SortNums(int[] nums) {\n        return nums.OrderBy(x => x).ToArray();\n    }\n}\n",
        "cpp": "#include <vector>\n#include <algorithm>\nusing namespace std;\n\nclass Solution {\npublic:\n    vector<int> sortNums(vector<int>& nums) {\n        sort(nums.begin(), nums.end());\n        return nums;\n    }\n};\n",
        "c": "#include <stdlib.h>\n\nint cmp(const void* a, const void* b) { return *(const int*)a - *(const int*)b; }\n\nint* sortNums(int* nums, int numsSize, int* returnSize) {\n    qsort(nums, numsSize, sizeof(int), cmp);\n    *returnSize = numsSize;\n    return nums;\n}\n",
        "go": "import (\n    \"fmt\"\n    \"sort\"\n)\n\nfunc sortNums(nums []int) []int {\n    sort.Ints(nums)\n    _ = fmt.Sprint(nums)\n    return nums\n}\n",
        "rust": "use std::collections::BinaryHeap;\nuse std::cmp::Reverse;\n\nimpl Solution {\n    pub fn sort_nums(nums: Vec<i32>) -> Vec<i32> {\n        let mut h: BinaryHeap<Reverse<i32>> = nums.into_iter().map(Reverse).collect();\n        let mut r = vec![];\n        while let Some(Reverse(x)) = h.pop() {\n            r.push(x);\n        }\n        r\n    }\n}\n",
    },
)

pattern(
    "debug_print",
    _fn("add"),
    [({"a": 2, "b": 3}, 5)],
    {
        "python": "class Solution:\n    def add(self, a: int, b: int) -> int:\n        print('debug', a, b)\n        return a + b\n",
        "javascript": "var add = function(a, b) {\n    console.log('debug', a, b);\n    return a + b;\n};\n",
        "typescript": "function add(a: number, b: number): number {\n    console.log('debug', a, b);\n    return a + b;\n}\n",
        "java": "class Solution {\n    public int add(int a, int b) {\n        System.out.println(\"debug \" + a + \" \" + b);\n        return a + b;\n    }\n}\n",
        "kotlin": "class Solution {\n    fun add(a: Int, b: Int): Int {\n        println(\"debug $a $b\")\n        return a + b\n    }\n}\n",
        "csharp": "public class Solution {\n    public int Add(int a, int b) {\n        Console.WriteLine(\"debug \" + a + \" \" + b);\n        return a + b;\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    int add(int a, int b) {\n        cout << \"debug \" << a << \" \" << b << endl;\n        return a + b;\n    }\n};\n",
        "c": "int add(int a, int b) {\n    printf(\"debug %d %d\\n\", a, b);\n    return a + b;\n}\n",
        "go": "import \"fmt\"\n\nfunc add(a int, b int) int {\n    fmt.Println(\"debug\", a, b)\n    return a + b\n}\n",
        "rust": "impl Solution {\n    pub fn add(a: i32, b: i32) -> i32 {\n        println!(\"debug {} {}\", a, b);\n        a + b\n    }\n}\n",
    },
)

pattern(
    "deep_recursion",
    _fn("sumTo", rust="sum_to"),
    [({"n": 3000}, 4501500)],
    {
        "python": "class Solution:\n    def sumTo(self, n: int) -> int:\n        return 0 if n == 0 else n + self.sumTo(n - 1)\n",
        "javascript": "var sumTo = function(n) {\n    return n === 0 ? 0 : n + sumTo(n - 1);\n};\n",
        "typescript": "function sumTo(n: number): number {\n    return n === 0 ? 0 : n + sumTo(n - 1);\n}\n",
        "java": "class Solution {\n    public int sumTo(int n) {\n        return n == 0 ? 0 : n + sumTo(n - 1);\n    }\n}\n",
        "kotlin": "class Solution {\n    fun sumTo(n: Int): Int {\n        return if (n == 0) 0 else n + sumTo(n - 1)\n    }\n}\n",
        "csharp": "public class Solution {\n    public int SumTo(int n) {\n        return n == 0 ? 0 : n + SumTo(n - 1);\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    int sumTo(int n) {\n        return n == 0 ? 0 : n + sumTo(n - 1);\n    }\n};\n",
        "c": "int sumTo(int n) {\n    return n == 0 ? 0 : n + sumTo(n - 1);\n}\n",
        "go": "func sumTo(n int) int {\n    if n == 0 {\n        return 0\n    }\n    return n + sumTo(n-1)\n}\n",
        "rust": "impl Solution {\n    pub fn sum_to(n: i32) -> i32 {\n        if n == 0 { 0 } else { n + Self::sum_to(n - 1) }\n    }\n}\n",
    },
)

# ---------------------------------------------------------------------------
# Failure verdicts
# ---------------------------------------------------------------------------

pattern(
    "wrong_answer",
    _fn("add"),
    [({"a": 2, "b": 0}, 2), ({"a": 2, "b": 3}, 5)],
    {
        "python": "class Solution:\n    def add(self, a: int, b: int) -> int:\n        return a - b\n",
        "javascript": "var add = function(a, b) {\n    return a - b;\n};\n",
        "typescript": "function add(a: number, b: number): number {\n    return a - b;\n}\n",
        "java": "class Solution {\n    public int add(int a, int b) {\n        return a - b;\n    }\n}\n",
        "kotlin": "class Solution {\n    fun add(a: Int, b: Int): Int {\n        return a - b\n    }\n}\n",
        "csharp": "public class Solution {\n    public int Add(int a, int b) {\n        return a - b;\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    int add(int a, int b) {\n        return a - b;\n    }\n};\n",
        "c": "int add(int a, int b) {\n    return a - b;\n}\n",
        "go": "func add(a int, b int) int {\n    return a - b\n}\n",
        "rust": "impl Solution {\n    pub fn add(a: i32, b: i32) -> i32 {\n        a - b\n    }\n}\n",
    },
    expect="wrong_answer",
    failed_index=1,
)

pattern(
    "runtime_error",
    _fn("pick"),
    [({"nums": [1, 2, 3]}, 1), ({"nums": [1]}, 1)],
    {
        "python": "class Solution:\n    def pick(self, nums: List[int]) -> int:\n        return nums[0] if len(nums) > 1 else nums[10]\n",
        "javascript": "var pick = function(nums) {\n    if (nums.length > 1) return nums[0];\n    throw new Error('boom');\n};\n",
        "typescript": "function pick(nums: number[]): number {\n    if (nums.length > 1) return nums[0];\n    throw new Error('boom');\n}\n",
        "java": "class Solution {\n    public int pick(int[] nums) {\n        return nums.length > 1 ? nums[0] : nums[10];\n    }\n}\n",
        "kotlin": "class Solution {\n    fun pick(nums: IntArray): Int {\n        return if (nums.size > 1) nums[0] else nums[10]\n    }\n}\n",
        "csharp": "public class Solution {\n    public int Pick(int[] nums) {\n        return nums.Length > 1 ? nums[0] : nums[10];\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    int pick(vector<int>& nums) {\n        return nums.size() > 1 ? nums[0] : nums.at(10);\n    }\n};\n",
        "c": "int pick(int* nums, int numsSize) {\n    if (numsSize > 1) return nums[0];\n    int* p = NULL;\n    return *p;\n}\n",
        "go": "func pick(nums []int) int {\n    if len(nums) > 1 {\n        return nums[0]\n    }\n    i := 10\n    return nums[i]\n}\n",
        "rust": "impl Solution {\n    pub fn pick(nums: Vec<i32>) -> i32 {\n        if nums.len() > 1 { nums[0] } else { nums[10] }\n    }\n}\n",
    },
    expect="runtime_error",
    failed_index=1,
)

# Unbounded recursion must come back as a verdict, not take the worker down.
# Some compilers turn it into a loop, so a timeout is also acceptable.
pattern(
    "stack_overflow",
    _fn("inf"),
    [({"n": 1}, 1)],
    {
        "python": "class Solution:\n    def inf(self, n: int) -> int:\n        return self.inf(n + 1) + 1\n",
        "javascript": "var inf = function(n) {\n    return inf(n + 1) + 1;\n};\n",
        "typescript": "function inf(n: number): number {\n    return inf(n + 1) + 1;\n}\n",
        "java": "class Solution {\n    public int inf(int n) {\n        return inf(n + 1) + 1;\n    }\n}\n",
        "kotlin": "class Solution {\n    fun inf(n: Int): Int {\n        return inf(n + 1) + 1\n    }\n}\n",
        "csharp": "public class Solution {\n    public int Inf(int n) {\n        return Inf(n + 1) + 1;\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    int inf(int n) {\n        return inf(n + 1) + 1;\n    }\n};\n",
        "c": "int inf(int n) {\n    return inf(n + 1) + 1;\n}\n",
        "go": "func inf(n int) int {\n    return inf(n+1) + 1\n}\n",
        "rust": "impl Solution {\n    pub fn inf(n: i32) -> i32 {\n        Self::inf(n + 1) + 1\n    }\n}\n",
    },
    expect=("runtime_error", "timeout"),
    failed_index=0,
)

pattern(
    "time_limit",
    _fn("spin"),
    [({"n": 1}, 1)],
    {
        "python": "class Solution:\n    def spin(self, n: int) -> int:\n        x = n\n        while x >= 0:\n            x = (x + 1) % 1000\n        return x\n",
        "javascript": "var spin = function(n) {\n    let x = n;\n    while (x >= 0) x = (x + 1) % 1000;\n    return x;\n};\n",
        "typescript": "function spin(n: number): number {\n    let x = n;\n    while (x >= 0) x = (x + 1) % 1000;\n    return x;\n}\n",
        "java": "class Solution {\n    public int spin(int n) {\n        int x = n;\n        while (x >= 0) x = (x + 1) % 1000;\n        return x;\n    }\n}\n",
        "kotlin": "class Solution {\n    fun spin(n: Int): Int {\n        var x = n\n        while (x >= 0) x = (x + 1) % 1000\n        return x\n    }\n}\n",
        "csharp": "public class Solution {\n    public int Spin(int n) {\n        int x = n;\n        while (x >= 0) x = (x + 1) % 1000;\n        return x;\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    int spin(int n) {\n        volatile int x = n;\n        while (x >= 0) x = (x + 1) % 1000;\n        return x;\n    }\n};\n",
        "c": "int spin(int n) {\n    volatile int x = n;\n    while (x >= 0) x = (x + 1) % 1000;\n    return x;\n}\n",
        "go": "func spin(n int) int {\n    x := n\n    for x >= 0 {\n        x = (x + 1) % 1000\n    }\n    return x\n}\n",
        "rust": "impl Solution {\n    pub fn spin(n: i32) -> i32 {\n        let mut x = n;\n        while x >= 0 {\n            x = std::hint::black_box((x + 1) % 1000);\n        }\n        x\n    }\n}\n",
    },
    expect="timeout",
    failed_index=0,
)

pattern(
    "compile_error",
    _fn("add"),
    [({"a": 2, "b": 3}, 5)],
    {
        "python": "class Solution:\n    def add(self, a: int, b: int) -> int\n        return a + b\n",
        "javascript": "var add = function(a, b) {\n    return a + ;\n};\n",
        "typescript": "function add(a: number, b: number): number {\n    return 'x';\n}\n",
        "java": "class Solution {\n    public int add(int a, int b) {\n        return a + b\n    }\n}\n",
        "kotlin": "class Solution {\n    fun add(a: Int, b: Int): Int {\n        return a +\n    }\n}\n",
        "csharp": "public class Solution {\n    public int Add(int a, int b) {\n        return a + b\n    }\n}\n",
        "cpp": "class Solution {\npublic:\n    int add(int a, int b) {\n        return a + b\n    }\n};\n",
        "c": "int add(int a, int b) {\n    return a + b\n}\n",
        "go": "func add(a int, b int) int {\n    return a +\n}\n",
        "rust": "impl Solution {\n    pub fn add(a: i32, b: i32) -> i32 {\n        a +\n    }\n}\n",
    },
    expect="compilation_error",
)
