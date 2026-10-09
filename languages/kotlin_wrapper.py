KOTLIN_WRAPPER_TEMPLATE = r"""
import java.io.BufferedReader
import java.io.InputStreamReader
import java.lang.reflect.InvocationTargetException
import java.lang.reflect.Method
import java.util.*
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.core.type.TypeReference
{user_imports}

// ==============================
// Built-in Data Structures
// ==============================

class TreeNode(var `val`: Int) {
    var left: TreeNode? = null
    var right: TreeNode? = null
}

class ListNode(var `val`: Int) {
    var next: ListNode? = null
}

class Node(var `val`: Int) {
    var neighbors: MutableList<Node> = ArrayList()
}

// ==============================
// Helper Builders
// ==============================

object Builders {

    fun buildTree(values: List<Int?>?): TreeNode? {
        if (values == null || values.isEmpty()) return null

        val nodes = values.map { if (it == null) null else TreeNode(it) }
        val root = nodes[0]
        val queue: Queue<TreeNode?> = LinkedList()
        queue.offer(root)

        var i = 1
        while (queue.isNotEmpty() && i < nodes.size) {
            val current = queue.poll()
            if (current != null) {
                current.left = nodes[i++]
                if (i < nodes.size) current.right = nodes[i++]
                queue.offer(current.left)
                queue.offer(current.right)
            }
        }

        return root
    }

    fun treeToList(root: TreeNode?): List<Int?> {
        if (root == null) return emptyList()

        val result = mutableListOf<Int?>()
        val queue: Queue<TreeNode?> = LinkedList()
        queue.offer(root)

        while (queue.isNotEmpty()) {
            val node = queue.poll()
            if (node != null) {
                result.add(node.`val`)
                queue.offer(node.left)
                queue.offer(node.right)
            } else {
                result.add(null)
            }
        }

        while (result.isNotEmpty() && result.last() == null)
            result.removeAt(result.size - 1)

        return result
    }

    fun buildLinkedList(values: List<Int>?, pos: Int): ListNode? {
        if (values == null || values.isEmpty()) return null

        val dummy = ListNode(0)
        var curr = dummy
        val nodes = mutableListOf<ListNode>()

        for (v in values) {
            curr.next = ListNode(v)
            curr = curr.next!!
            nodes.add(curr)
        }

        if (pos != -1 && pos < nodes.size)
            curr.next = nodes[pos]

        return dummy.next
    }

    fun linkedListToList(head: ListNode?): List<Int> {
        val result = mutableListOf<Int>()
        val visited = HashSet<ListNode>()
        var curr = head

        while (curr != null && !visited.contains(curr)) {
            visited.add(curr)
            result.add(curr.`val`)
            curr = curr.next
        }

        return result
    }

    fun buildGraph(adj: List<List<Int>>?): Node? {
        if (adj == null || adj.isEmpty()) return null

        val nodes = HashMap<Int, Node>()
        for (i in adj.indices)
            nodes[i + 1] = Node(i + 1)

        for (i in adj.indices)
            for (n in adj[i])
                nodes[i + 1]!!.neighbors.add(nodes[n]!!)

        return nodes[1]
    }

    fun graphToAdjList(node: Node?): List<List<Int>> {
        if (node == null) return emptyList()

        val visited = HashSet<Node>()
        val queue: Queue<Node> = LinkedList()
        val nodes = mutableListOf<Node>()

        queue.offer(node)

        while (queue.isNotEmpty()) {
            val curr = queue.poll()
            if (visited.contains(curr)) continue

            visited.add(curr)
            nodes.add(curr)

            for (n in curr.neighbors)
                if (!visited.contains(n))
                    queue.offer(n)
        }

        nodes.sortBy { it.`val` }

        val maxVal = nodes.maxOf { it.`val` }
        val result = MutableList(maxVal) { mutableListOf<Int>() }

        for (curr in nodes)
            for (n in curr.neighbors)
                result[curr.`val` - 1].add(n.`val`)

        return result
    }
}

// ==============================
// User Code
// ==============================

{source_code}

// ==============================
// Execution Engine
// ==============================

object Main {

    private const val RESULT_START = "__JUDGE_RESULT_7f3a__"
    private const val RESULT_END = "__JUDGE_END_7f3a__"

    private val mapper = ObjectMapper()

    private fun autoConvertOutput(result: Any?): Any? {
        return when (result) {
            is TreeNode -> Builders.treeToList(result)
            is ListNode -> Builders.linkedListToList(result)
            is Node -> Builders.graphToAdjList(result)
            // Jackson would write CharArray as one string and Char as a number;
            // LeetCode writes them as single-character strings.
            is Char -> result.toString()
            is CharArray -> result.map { it.toString() }
            is Array<*> -> result.map { autoConvertOutput(it) }
            is Collection<*> -> result.map { autoConvertOutput(it) }
            else -> result
        }
    }

    private fun toChar(value: Any): Char {
        if (value is Number) return value.toInt().toChar()
        val s = value.toString()
        return if (s.isEmpty()) '\u0000' else s[0]
    }

    @Suppress("UNCHECKED_CAST")
    private fun convertValue(value: Any?, targetType: Class<*>, genericType: java.lang.reflect.Type, fullInput: Map<String, Any?>): Any? {

        if (value == null) return null

        if (targetType == Int::class.java || targetType == Integer::class.java)
            return (value as Number).toInt()

        if (targetType == Long::class.java || targetType == java.lang.Long::class.java)
            return (value as Number).toLong()

        if (targetType == Double::class.java || targetType == java.lang.Double::class.java)
            return (value as Number).toDouble()

        if (targetType == Boolean::class.java || targetType == java.lang.Boolean::class.java)
            return value

        if (targetType == Char::class.java || targetType == java.lang.Character::class.java)
            return toChar(value)

        if (targetType == String::class.java)
            return value.toString()

        if (targetType == CharArray::class.java) {
            if (value !is List<*>) return value.toString().toCharArray()
            return value.map { toChar(it!!) }.toCharArray()
        }

        if (targetType == Array<CharArray>::class.java) {
            val outer = value as List<*>
            return outer.map { convertValue(it, CharArray::class.java, CharArray::class.java, fullInput) as CharArray }.toTypedArray()
        }

        if (targetType == TreeNode::class.java)
            return Builders.buildTree(value as List<Int?>)

        if (targetType == ListNode::class.java) {
            val pos = (fullInput["pos"] as? Number)?.toInt() ?: -1
            return Builders.buildLinkedList(value as List<Int>, pos)
        }

        if (targetType == Node::class.java)
            return Builders.buildGraph(value as List<List<Int>>)

        // Everything else (IntArray, Array<String>, List<List<Int>>, ...) is
        // converted by Jackson using the full generic parameter type.
        val javaType = mapper.typeFactory.constructType(genericType)
        return mapper.convertValue<Any?>(value, javaType)
    }

    private fun describe(t: Throwable): String {
        val name = t.javaClass.simpleName
        return if (t.message == null) name else name + ": " + t.message
    }

    private fun executeFunction(functionName: String, input: Map<String, Any?>): Map<String, Any?> {

        // A method of `class Solution`, or a top-level function (compiled into MainKt).
        val solutionClass = listOf("Solution", "MainKt")
            .mapNotNull { name -> try { Class.forName(name) } catch (e: ClassNotFoundException) { null } }
            .firstOrNull { cls -> cls.declaredMethods.any { it.name == functionName } }
            ?: throw Exception("Function '" + functionName + "' not found")

        // "pos" only describes a linked-list cycle; it is not an argument
        // unless the method actually takes one more parameter.
        var values: List<Any?> = input.filterKeys { it != "pos" }.values.toList()

        var method: Method? = null
        for (m in solutionClass.declaredMethods) {
            if (m.name != functionName) continue
            if (method == null || m.parameterCount == values.size) method = m
        }
        if (method == null) throw Exception("Function '" + functionName + "' not found")
        method.isAccessible = true

        if (method.parameterCount > values.size) values = input.values.toList()

        val paramTypes = method.parameterTypes
        val genericTypes = method.genericParameterTypes
        val args = Array<Any?>(paramTypes.size) { i ->
            convertValue(if (i < values.size) values[i] else null, paramTypes[i], genericTypes[i], input)
        }

        val instance = if (java.lang.reflect.Modifier.isStatic(method.modifiers)) null
            else solutionClass.getDeclaredConstructor().newInstance()
        val result = try {
            method.invoke(instance, *args)
        } catch (e: InvocationTargetException) {
            throw Exception(describe(e.targetException))
        }

        val output = HashMap<String, Any?>()
        output["result"] = autoConvertOutput(result)
        if (method.returnType == Void.TYPE && args.isNotEmpty())
            output["mutated"] = autoConvertOutput(args[0])
        return output
    }

    private fun emit(obj: Any) {
        System.out.flush()
        println(RESULT_START + mapper.writeValueAsString(obj) + RESULT_END)
        System.out.flush()
    }

    @JvmStatic
    fun main(args: Array<String>) {

        try {
            val reader = BufferedReader(InputStreamReader(System.`in`))
            val inputBuilder = StringBuilder()
            var line: String?

            while (reader.readLine().also { line = it } != null)
                inputBuilder.append(line)

            val payload: Map<String, Any?> =
                mapper.readValue(inputBuilder.toString(),
                    object : TypeReference<Map<String, Any?>>() {})

            val functionName = payload["function_name"] as String
            @Suppress("UNCHECKED_CAST")
            val input = payload["input"] as Map<String, Any?>

            emit(executeFunction(functionName, input))

        } catch (e: Throwable) {

            try {
                val error = HashMap<String, Any?>()
                error["error"] = if (e is Exception && e.message != null) e.message else describe(e)
                emit(error)
            } catch (_: Exception) {}

            System.exit(1)
        }
    }
}
"""