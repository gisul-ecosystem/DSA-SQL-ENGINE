CSHARP_WRAPPER_TEMPLATE = r"""
using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Reflection;
using System.Linq;

// ==============================
// Built-in Data Structures
// ==============================

public class TreeNode {
    public int val;
    public TreeNode left;
    public TreeNode right;

    public TreeNode(int val = 0, TreeNode left = null, TreeNode right = null) {
        this.val = val;
        this.left = left;
        this.right = right;
    }
}

public class ListNode {
    public int val;
    public ListNode next;

    public ListNode(int val = 0, ListNode next = null) {
        this.val = val;
        this.next = next;
    }
}

public class Node {
    public int val;
    public IList<Node> neighbors;

    public Node() {
        val = 0;
        neighbors = new List<Node>();
    }

    public Node(int _val) {
        val = _val;
        neighbors = new List<Node>();
    }
}

// ==============================
// Helper Builders
// ==============================

public static class Builders {

    public static TreeNode BuildTree(List<int?> values) {
        if (values == null || values.Count == 0)
            return null;

        var nodes = values
            .Select(v => v == null ? null : new TreeNode(v.Value))
            .ToList();

        Queue<TreeNode> queue = new Queue<TreeNode>();
        TreeNode root = nodes[0];
        queue.Enqueue(root);

        int i = 1;
        while (queue.Count > 0 && i < nodes.Count) {
            var current = queue.Dequeue();
            if (current != null) {
                current.left = nodes[i++];
                if (i < nodes.Count)
                    current.right = nodes[i++];
                queue.Enqueue(current.left);
                queue.Enqueue(current.right);
            }
        }

        return root;
    }

    public static List<int?> TreeToList(TreeNode root) {
        if (root == null)
            return new List<int?>();

        List<int?> result = new List<int?>();
        Queue<TreeNode> queue = new Queue<TreeNode>();
        queue.Enqueue(root);

        while (queue.Count > 0) {
            var node = queue.Dequeue();
            if (node != null) {
                result.Add(node.val);
                queue.Enqueue(node.left);
                queue.Enqueue(node.right);
            } else {
                result.Add(null);
            }
        }

        while (result.Count > 0 && result.Last() == null)
            result.RemoveAt(result.Count - 1);

        return result;
    }

    public static ListNode BuildLinkedList(List<int> values, int pos) {
        if (values == null || values.Count == 0)
            return null;

        ListNode dummy = new ListNode(0);
        ListNode curr = dummy;
        List<ListNode> nodes = new List<ListNode>();

        foreach (var val in values) {
            curr.next = new ListNode(val);
            curr = curr.next;
            nodes.Add(curr);
        }

        if (pos != -1 && pos < nodes.Count)
            curr.next = nodes[pos];

        return dummy.next;
    }

    public static List<int> LinkedListToList(ListNode head) {
        List<int> result = new List<int>();
        HashSet<ListNode> visited = new HashSet<ListNode>();

        while (head != null && !visited.Contains(head)) {
            visited.Add(head);
            result.Add(head.val);
            head = head.next;
        }

        return result;
    }

    public static Node BuildGraph(List<List<int>> adjList) {
        if (adjList == null || adjList.Count == 0)
            return null;

        Dictionary<int, Node> nodes = new Dictionary<int, Node>();

        for (int i = 0; i < adjList.Count; i++)
            nodes[i + 1] = new Node(i + 1);

        for (int i = 0; i < adjList.Count; i++) {
            foreach (var neighbor in adjList[i]) {
                nodes[i + 1].neighbors.Add(nodes[neighbor]);
            }
        }

        return nodes[1];
    }

    public static List<List<int>> GraphToAdjList(Node node) {
        if (node == null)
            return new List<List<int>>();

        List<Node> nodes = new List<Node>();
        Queue<Node> queue = new Queue<Node>();
        HashSet<Node> visited = new HashSet<Node>();

        queue.Enqueue(node);

        while (queue.Count > 0) {
            var curr = queue.Dequeue();
            if (visited.Contains(curr))
                continue;

            visited.Add(curr);
            nodes.Add(curr);

            foreach (var neighbor in curr.neighbors)
                if (!visited.Contains(neighbor))
                    queue.Enqueue(neighbor);
        }

        nodes = nodes.OrderBy(n => n.val).ToList();

        int maxVal = nodes.Max(n => n.val);
        List<List<int>> result = new List<List<int>>();
        for (int i = 0; i < maxVal; i++)
            result.Add(new List<int>());

        foreach (var curr in nodes)
            foreach (var neighbor in curr.neighbors)
                result[curr.val - 1].Add(neighbor.val);

        return result;
    }
}

// ==============================
// User Code
// ==============================

{source_code}

// ==============================
// Execution Engine
// ==============================

public class Program {

    const string RESULT_START = "__JUDGE_RESULT_7f3a__";
    const string RESULT_END = "__JUDGE_END_7f3a__";

    static readonly JsonSerializerOptions JsonOptions = new JsonSerializerOptions {
        IncludeFields = true,
        NumberHandling = JsonNumberHandling.AllowNamedFloatingPointLiterals,
    };

    static object AutoConvertOutput(object result) {

        if (result is TreeNode tree)
            return Builders.TreeToList(tree);

        if (result is ListNode listNode)
            return Builders.LinkedListToList(listNode);

        if (result is Node graphNode)
            return Builders.GraphToAdjList(graphNode);

        return result;
    }

    static object ConvertValue(JsonElement element, Type targetType, Dictionary<string, JsonElement> fullInput) {

        if (element.ValueKind == JsonValueKind.Null)
            return null;

        if (targetType == typeof(char))
            return element.ValueKind == JsonValueKind.String
                ? (element.GetString().Length > 0 ? element.GetString()[0] : '\0')
                : (char) element.GetInt32();

        if (targetType == typeof(char[]) && element.ValueKind == JsonValueKind.String)
            return element.GetString().ToCharArray();

        if (targetType == typeof(char[]))
            return element.EnumerateArray().Select(x => (char) ConvertValue(x, typeof(char), fullInput)).ToArray();

        if (targetType == typeof(char[][]))
            return element.EnumerateArray()
                .Select(row => (char[]) ConvertValue(row, typeof(char[]), fullInput))
                .ToArray();

        if (targetType == typeof(TreeNode))
            return Builders.BuildTree(
                element.EnumerateArray()
                .Select(x => x.ValueKind == JsonValueKind.Null ? (int?)null : x.GetInt32())
                .ToList()
            );

        if (targetType == typeof(ListNode)) {
            int pos = -1;
            if (fullInput.ContainsKey("pos"))
                pos = fullInput["pos"].GetInt32();

            return Builders.BuildLinkedList(
                element.EnumerateArray().Select(x => x.GetInt32()).ToList(),
                pos
            );
        }

        if (targetType == typeof(Node))
            return Builders.BuildGraph(
                element.EnumerateArray()
                .Select(row => row.EnumerateArray().Select(x => x.GetInt32()).ToList())
                .ToList()
            );

        // Everything else (int, string, int[], string[], IList<IList<int>>,
        // long[][], Dictionary<string,int>, ...) is handled by System.Text.Json.
        return JsonSerializer.Deserialize(element.GetRawText(), targetType, JsonOptions);
    }

    static string Describe(Exception ex) {
        while (ex is TargetInvocationException && ex.InnerException != null)
            ex = ex.InnerException;
        return ex.GetType().Name + ": " + ex.Message;
    }

    static void Emit(object obj) {
        Console.Out.Flush();
        Console.WriteLine(RESULT_START + JsonSerializer.Serialize(obj, JsonOptions) + RESULT_END);
        Console.Out.Flush();
    }

    static void Run() {

        try {

            string inputJson = Console.In.ReadToEnd();
            var payload = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(inputJson);

            string functionName = payload["function_name"].GetString();
            var input = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(
                payload["input"].GetRawText()
            );

            Type solutionType = Type.GetType("Solution");
            if (solutionType == null)
                throw new Exception("Class 'Solution' not found");

            // "pos" only describes a linked-list cycle; it is not an argument
            // unless the method actually takes one more parameter.
            var values = input.Where(kv => kv.Key != "pos").Select(kv => kv.Value).ToList();

            var methods = solutionType
                .GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static)
                .Where(m => m.Name == functionName)
                .ToList();
            if (methods.Count == 0)
                throw new Exception("Function '" + functionName + "' not found");
            var method = methods.FirstOrDefault(m => m.GetParameters().Length == values.Count) ?? methods[0];

            var parameters = method.GetParameters();
            if (parameters.Length > values.Count)
                values = input.Values.ToList();

            object[] argsConverted = new object[parameters.Length];
            for (int i = 0; i < parameters.Length; i++) {
                argsConverted[i] = i < values.Count
                    ? ConvertValue(values[i], parameters[i].ParameterType, input)
                    : null;
            }

            object instance = method.IsStatic ? null : Activator.CreateInstance(solutionType);
            var result = method.Invoke(instance, argsConverted);

            var response = new Dictionary<string, object> {
                { "result", AutoConvertOutput(result) }
            };
            if (method.ReturnType == typeof(void) && argsConverted.Length > 0)
                response["mutated"] = AutoConvertOutput(argsConverted[0]);

            Emit(response);
        }
        catch (Exception ex) {

            Emit(new Dictionary<string, object> {
                { "error", Describe(ex) }
            });
            Environment.Exit(1);
        }
    }

    public static void Main(string[] args) {
        // Deep recursion (DFS on 10^5 nodes) needs a bigger stack than the default 1 MB.
        var thread = new System.Threading.Thread(Run, 256 * 1024 * 1024);
        thread.Start();
        thread.Join();
    }
}
"""