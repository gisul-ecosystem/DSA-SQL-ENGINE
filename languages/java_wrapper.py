JAVA_WRAPPER_TEMPLATE = r"""
import java.io.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.function.*;
import java.util.stream.*;
import java.math.BigInteger;
import java.math.BigDecimal;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JavaType;
import com.fasterxml.jackson.core.type.TypeReference;

// ==============================
// Built-in Data Structures
// ==============================

class TreeNode {
    public int val;
    public TreeNode left;
    public TreeNode right;
    TreeNode() {}
    TreeNode(int val) { this.val = val; }
    TreeNode(int val, TreeNode left, TreeNode right) { this.val = val; this.left = left; this.right = right; }
}

class ListNode {
    public int val;
    public ListNode next;
    ListNode() {}
    ListNode(int val) { this.val = val; }
    ListNode(int val, ListNode next) { this.val = val; this.next = next; }
}

class Node {
    public int val;
    public List<Node> neighbors;
    Node(int val) {
        this.val = val;
        this.neighbors = new ArrayList<>();
    }
}

// ==============================
// Helper Builders
// ==============================

class Builders {

    public static TreeNode buildTree(List<Integer> values) {
        if (values == null || values.isEmpty()) return null;

        List<TreeNode> nodes = new ArrayList<>();
        for (Integer val : values)
            nodes.add(val == null ? null : new TreeNode(val));

        Queue<TreeNode> queue = new LinkedList<>();
        TreeNode root = nodes.get(0);
        queue.offer(root);

        int i = 1;
        while (!queue.isEmpty() && i < nodes.size()) {
            TreeNode current = queue.poll();
            if (current != null) {
                current.left = nodes.get(i++);
                if (i < nodes.size())
                    current.right = nodes.get(i++);
                queue.offer(current.left);
                queue.offer(current.right);
            }
        }

        return root;
    }

    public static List<Integer> treeToList(TreeNode root) {
        if (root == null) return new ArrayList<>();

        List<Integer> result = new ArrayList<>();
        Queue<TreeNode> queue = new LinkedList<>();
        queue.offer(root);

        while (!queue.isEmpty()) {
            TreeNode node = queue.poll();
            if (node != null) {
                result.add(node.val);
                queue.offer(node.left);
                queue.offer(node.right);
            } else {
                result.add(null);
            }
        }

        while (!result.isEmpty() && result.get(result.size() - 1) == null)
            result.remove(result.size() - 1);

        return result;
    }

    public static ListNode buildLinkedList(List<Integer> values, int pos) {
        if (values == null || values.isEmpty()) return null;

        ListNode dummy = new ListNode(0);
        ListNode curr = dummy;
        List<ListNode> nodes = new ArrayList<>();

        for (Integer val : values) {
            curr.next = new ListNode(val);
            curr = curr.next;
            nodes.add(curr);
        }

        if (pos != -1 && pos < nodes.size())
            curr.next = nodes.get(pos);

        return dummy.next;
    }

    public static List<Integer> linkedListToList(ListNode head) {
        List<Integer> result = new ArrayList<>();
        Set<ListNode> visited = new HashSet<>();

        while (head != null && !visited.contains(head)) {
            visited.add(head);
            result.add(head.val);
            head = head.next;
        }

        return result;
    }

    public static Node buildGraph(List<List<Integer>> adjList) {
        if (adjList == null || adjList.isEmpty()) return null;

        Map<Integer, Node> nodes = new HashMap<>();
        for (int i = 0; i < adjList.size(); i++)
            nodes.put(i + 1, new Node(i + 1));

        for (int i = 0; i < adjList.size(); i++)
            for (Integer neighbor : adjList.get(i))
                nodes.get(i + 1).neighbors.add(nodes.get(neighbor));

        return nodes.get(1);
    }

    public static List<List<Integer>> graphToAdjList(Node node) {
        if (node == null) return new ArrayList<>();

        List<Node> nodes = new ArrayList<>();
        Queue<Node> queue = new LinkedList<>();
        Set<Node> visited = new HashSet<>();

        queue.offer(node);

        while (!queue.isEmpty()) {
            Node curr = queue.poll();
            if (visited.contains(curr)) continue;

            visited.add(curr);
            nodes.add(curr);

            for (Node neighbor : curr.neighbors)
                if (!visited.contains(neighbor))
                    queue.offer(neighbor);
        }

        nodes.sort(Comparator.comparingInt(n -> n.val));

        int maxVal = nodes.stream().mapToInt(n -> n.val).max().orElse(0);
        List<List<Integer>> result = new ArrayList<>();
        for (int i = 0; i < maxVal; i++)
            result.add(new ArrayList<>());

        for (Node curr : nodes)
            for (Node neighbor : curr.neighbors)
                result.get(curr.val - 1).add(neighbor.val);

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

public class Main {

    static final String RESULT_START = "__JUDGE_RESULT_7f3a__";
    static final String RESULT_END = "__JUDGE_END_7f3a__";

    static ObjectMapper mapper = new ObjectMapper();

    public static Object autoConvertOutput(Object result) {

        if (result instanceof TreeNode)
            return Builders.treeToList((TreeNode) result);

        if (result instanceof ListNode)
            return Builders.linkedListToList((ListNode) result);

        if (result instanceof Node)
            return Builders.graphToAdjList((Node) result);

        // Jackson would write char[] as one string and char as a number;
        // LeetCode writes them as single-character strings.
        if (result instanceof Character)
            return String.valueOf((char) (Character) result);

        if (result instanceof char[]) {
            List<String> out = new ArrayList<>();
            for (char c : (char[]) result) out.add(String.valueOf(c));
            return out;
        }

        if (result instanceof Object[]) {
            List<Object> out = new ArrayList<>();
            for (Object o : (Object[]) result) out.add(autoConvertOutput(o));
            return out;
        }

        if (result instanceof Collection) {
            List<Object> out = new ArrayList<>();
            for (Object o : (Collection<?>) result) out.add(autoConvertOutput(o));
            return out;
        }

        return result;
    }

    static char toChar(Object value) {
        if (value instanceof Number) return (char) ((Number) value).intValue();
        String s = value.toString();
        return s.isEmpty() ? '\0' : s.charAt(0);
    }

    public static Object convertValue(Object value, Class<?> targetType, java.lang.reflect.Type genericType, Map<String,Object> fullInput) {

        if (value == null)
            return null;

        if (targetType == int.class || targetType == Integer.class)
            return ((Number) value).intValue();

        if (targetType == long.class || targetType == Long.class)
            return ((Number) value).longValue();

        if (targetType == double.class || targetType == Double.class)
            return ((Number) value).doubleValue();

        if (targetType == boolean.class || targetType == Boolean.class)
            return value;

        if (targetType == char.class || targetType == Character.class)
            return toChar(value);

        if (targetType == String.class)
            return value.toString();

        // List<String> or List (raw) given as a multiline string: "N\nOP1\nOP2\n..."
        if ((targetType == List.class || targetType == ArrayList.class) && !(value instanceof List)) {
            String s = value.toString().trim();
            String[] lines = s.split("\\n");
            int start = 0;
            try { Integer.parseInt(lines[0].trim()); start = 1; } catch (NumberFormatException ignored) {}
            List<String> list = new ArrayList<>();
            for (int i = start; i < lines.length; i++)
                if (!lines[i].trim().isEmpty()) list.add(lines[i].trim());
            return list;
        }

        if (targetType == char[].class) {
            if (!(value instanceof List)) return value.toString().toCharArray();
            List<?> list = (List<?>) value;
            char[] arr = new char[list.size()];
            for (int i = 0; i < list.size(); i++) arr[i] = toChar(list.get(i));
            return arr;
        }

        if (targetType == char[][].class) {
            List<?> outer = (List<?>) value;
            char[][] arr = new char[outer.size()][];
            for (int i = 0; i < outer.size(); i++)
                arr[i] = (char[]) convertValue(outer.get(i), char[].class, char[].class, fullInput);
            return arr;
        }

        if (targetType == TreeNode.class)
            return Builders.buildTree((List<Integer>) value);

        if (targetType == ListNode.class) {
            int pos = -1;
            if (fullInput.containsKey("pos"))
                pos = ((Number) fullInput.get("pos")).intValue();
            return Builders.buildLinkedList((List<Integer>) value, pos);
        }

        if (targetType == Node.class)
            return Builders.buildGraph((List<List<Integer>>) value);

        // Everything else (int[], long[][], String[], List<List<Integer>>,
        // Map<String, Integer>, ...) is converted by Jackson using the full
        // generic parameter type.
        JavaType javaType = mapper.getTypeFactory().constructType(genericType);
        return mapper.convertValue(value, javaType);
    }

    static String describe(Throwable t) {
        String name = t.getClass().getSimpleName();
        return t.getMessage() == null ? name : name + ": " + t.getMessage();
    }

    public static Map<String, Object> executeFunction(String functionName, Map<String, Object> input) throws Exception {

        Class<?> solutionClass;
        try {
            solutionClass = Class.forName("Solution");
        } catch (ClassNotFoundException e) {
            throw new Exception("Class 'Solution' not found");
        }

        // "pos" only describes a linked-list cycle; it is not an argument
        // unless the method actually takes one more parameter.
        List<Object> values = new ArrayList<>();
        for (Map.Entry<String, Object> entry : input.entrySet())
            if (!entry.getKey().equals("pos"))
                values.add(entry.getValue());

        Method method = null;
        for (Method m : solutionClass.getDeclaredMethods()) {
            if (!m.getName().equals(functionName)) continue;
            if (method == null || m.getParameterCount() == values.size()) method = m;
        }
        if (method == null)
            throw new Exception("Function '" + functionName + "' not found");
        method.setAccessible(true);

        if (method.getParameterCount() > values.size())
            values = new ArrayList<>(input.values());

        Class<?>[] paramTypes = method.getParameterTypes();
        java.lang.reflect.Type[] genericTypes = method.getGenericParameterTypes();
        Object[] args = new Object[paramTypes.length];
        for (int i = 0; i < paramTypes.length; i++)
            args[i] = convertValue(i < values.size() ? values.get(i) : null, paramTypes[i], genericTypes[i], input);

        Object instance = solutionClass.getDeclaredConstructor().newInstance();
        Object result;
        try {
            result = method.invoke(instance, args);
        } catch (InvocationTargetException e) {
            throw new Exception(describe(e.getTargetException()));
        }

        Map<String, Object> output = new HashMap<>();
        output.put("result", autoConvertOutput(result));
        if (method.getReturnType() == void.class && args.length > 0)
            output.put("mutated", autoConvertOutput(args[0]));
        return output;
    }

    static void emit(Object obj) throws Exception {
        System.out.flush();
        System.out.println(RESULT_START + mapper.writeValueAsString(obj) + RESULT_END);
        System.out.flush();
    }

    public static void main(String[] args) {

        int index = 0;
        try {

            BufferedReader reader = new BufferedReader(new InputStreamReader(System.in));
            StringBuilder inputBuilder = new StringBuilder();
            String line;

            while ((line = reader.readLine()) != null)
                inputBuilder.append(line);

            Map<String, Object> payload =
                mapper.readValue(inputBuilder.toString(),
                    new TypeReference<Map<String, Object>>() {});

            String functionName = (String) payload.get("function_name");

            if (payload.containsKey("test_cases")) {
                // Batch mode: one result block per test case, so a crash or
                // timeout part-way through still tells the judge which failed.
                List<Map<String, Object>> testCases =
                    (List<Map<String, Object>>) payload.get("test_cases");
                for (index = 0; index < testCases.size(); index++) {
                    Map<String, Object> input = (Map<String, Object>) testCases.get(index).get("input");
                    Map<String, Object> output = executeFunction(functionName, input);
                    output.put("index", index);
                    emit(output);
                }
            } else {
                emit(executeFunction(functionName, (Map<String, Object>) payload.get("input")));
            }

        } catch (Throwable e) {

            try {
                Map<String, Object> error = new HashMap<>();
                error.put("error", e instanceof Exception && e.getMessage() != null ? e.getMessage() : describe(e));
                error.put("failed_test_case_index", index);
                emit(error);
            } catch (Exception ignored) {}

            System.exit(1);
        }
    }
}
"""
