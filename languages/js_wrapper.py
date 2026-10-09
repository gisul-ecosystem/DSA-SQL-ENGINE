JS_WRAPPER_TEMPLATE = """
// ==============================
// Built-in Data Structures
// ==============================

class TreeNode {
    constructor(val = 0, left = null, right = null) {
        this.val = val;
        this.left = left;
        this.right = right;
    }
}

class ListNode {
    constructor(val = 0, next = null) {
        this.val = val;
        this.next = next;
    }
}

class Node {
    constructor(val = 0, neighbors = []) {
        this.val = val;
        this.neighbors = neighbors;
    }
}

// ==============================
// Tree Helpers
// ==============================

function buildTree(values) {
    if (!values || values.length === 0) return null;

    const nodes = values.map(v =>
        v === null ? null : new TreeNode(v)
    );

    let pos = 1;
    for (let i = 0; i < nodes.length && pos < nodes.length; i++) {
        if (nodes[i]) {
            if (pos < nodes.length) nodes[i].left = nodes[pos++];
            if (pos < nodes.length) nodes[i].right = nodes[pos++];
        }
    }

    return nodes[0];
}

function treeToList(root) {
    if (!root) return [];

    const result = [];
    const queue = [root];

    while (queue.length) {
        const node = queue.shift();
        if (node) {
            result.push(node.val);
            queue.push(node.left);
            queue.push(node.right);
        } else {
            result.push(null);
        }
    }

    while (result.length && result[result.length - 1] === null)
        result.pop();

    return result;
}

// ==============================
// Linked List Helpers (Cycle Safe)
// ==============================

function buildLinkedList(values) {
    if (!values || values.length === 0) return { head: null, nodes: [] };

    const dummy = new ListNode(0);
    let curr = dummy;
    const nodes = [];

    for (const val of values) {
        curr.next = new ListNode(val);
        curr = curr.next;
        nodes.push(curr);
    }

    return { head: dummy.next, nodes };
}

function linkedListToArray(head) {
    const result = [];
    const visited = new Set();

    while (head && !visited.has(head)) {
        visited.add(head);
        result.push(head.val);
        head = head.next;
    }

    return result;
}

// ==============================
// Graph Helpers
// ==============================

function buildGraph(adjList) {
    if (!adjList || adjList.length === 0) return null;

    const nodes = adjList.map((_, i) => new Node(i + 1));

    for (let i = 0; i < adjList.length; i++) {
        for (const neighbor of adjList[i]) {
            nodes[i].neighbors.push(nodes[neighbor - 1]);
        }
    }

    return nodes[0];
}

function graphToAdjList(node) {
    if (!node) return [];

    const visited = new Set();
    const queue = [node];
    const nodes = [];

    while (queue.length) {
        const curr = queue.shift();
        if (visited.has(curr)) continue;

        visited.add(curr);
        nodes.push(curr);

        for (const neighbor of curr.neighbors) {
            if (!visited.has(neighbor)) {
                queue.push(neighbor);
            }
        }
    }

    nodes.sort((a, b) => a.val - b.val);

    const maxVal = Math.max(...nodes.map(n => n.val));
    const result = Array.from({ length: maxVal }, () => []);

    for (const curr of nodes) {
        for (const neighbor of curr.neighbors) {
            result[curr.val - 1].push(neighbor.val);
        }
    }

    return result;
}

// ==============================
// User Code
// ==============================

{source_code}

// ==============================
// Auto Conversion (Cycle Support Added)
// ==============================

function autoConvertInput(input) {
    const converted = {};

    for (const key in input) {
        const value = input[key];

        // Tree
        if (Array.isArray(value) && key.toLowerCase().startsWith("root")) {
            converted[key] = buildTree(value);
        }

        // Linked List with optional pos
        else if (Array.isArray(value) && key.toLowerCase().startsWith("head")) {

            const pos = typeof input.pos === "number" ? input.pos : -1;

            const { head, nodes } = buildLinkedList(value);

            if (pos !== -1 && nodes.length > 0 && pos >= 0 && pos < nodes.length) {
                nodes[nodes.length - 1].next = nodes[pos];
            }

            converted[key] = head;
        }

        // Graph
        else if (Array.isArray(value) && key.toLowerCase().startsWith("adj")) {
            converted[key] = buildGraph(value);
        }

        // Skip metadata like pos
        else if (key === "pos") {
            continue;
        }

        // String that looks like a multiline operations list (split into array)
        else if (typeof value === "string" && value.includes("\\n")) {
            const lines = value.trim().split("\\n").map(l => l.trim()).filter(l => l.length > 0);
            // If first line is a pure integer (count), drop it
            if (lines.length > 0 && /^\\d+$/.test(lines[0])) {
                converted[key] = lines.slice(1);
            } else {
                converted[key] = lines;
            }
        }

        else {
            converted[key] = value;
        }
    }

    return converted;
}

function autoConvertOutput(result) {
    if (result instanceof TreeNode) return treeToList(result);
    if (result instanceof ListNode) return linkedListToArray(result);
    if (result instanceof Node) return graphToAdjList(result);
    return result;
}

// ==============================
// Execution Logic
// ==============================

const RESULT_START = "__JUDGE_RESULT_7f3a__";
const RESULT_END = "__JUDGE_END_7f3a__";

function resolveFunction(functionName) {
    // Prefer a top-level function the user wrote; ignore built-ins like parseInt.
    let fn;
    try { fn = eval(functionName); } catch (_) { fn = undefined; }
    if (typeof fn === "function" && !/\\[native code\\]/.test(Function.prototype.toString.call(fn))) {
        return fn;
    }

    if (typeof Solution === "function") {
        const instance = new Solution();
        if (typeof instance[functionName] === "function") {
            return instance[functionName].bind(instance);
        }
    }
    return null;
}

function executeFunction(functionName, input) {

    const convertedInput = autoConvertInput(input);
    const fn = resolveFunction(functionName);
    if (!fn) throw new Error("Function '" + functionName + "' not found");

    const args = Object.values(convertedInput);
    const result = fn(...args);
    const output = { result: autoConvertOutput(result) };
    if (result === undefined && args.length > 0) {
        // In-place problems return nothing; the judge compares the mutated first argument.
        output.mutated = autoConvertOutput(args[0]);
    }
    if (output.result === undefined) output.result = null;
    return output;
}

function emit(obj) {
    process.stdout.write(RESULT_START + JSON.stringify(obj) + RESULT_END + "\\n");
}

// ==============================
// Main
// ==============================

function main() {
    const inputChunks = [];

    process.stdin.on("data", chunk => {
        inputChunks.push(chunk);
    });

    process.stdin.on("end", () => {
        try {
            const rawInput = Buffer.concat(inputChunks).toString();
            const payload = JSON.parse(rawInput);

            emit(executeFunction(payload.function_name, payload.input));
        } catch (err) {
            const message = err instanceof Error ? err.name + ": " + err.message : String(err);
            emit({ error: message });
            process.exitCode = 1;
        }
    });
}

main();
"""