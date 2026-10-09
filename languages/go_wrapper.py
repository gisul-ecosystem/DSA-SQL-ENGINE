GO_WRAPPER_TEMPLATE = r"""
package main

__IMPORTS_PLACEHOLDER__

const resultStart = "__JUDGE_RESULT_7f3a__"
const resultEnd = "__JUDGE_END_7f3a__"

type payload struct {
    FunctionName string                     `json:"function_name"`
    Input        map[string]json.RawMessage `json:"input"`
    Keys         []string                   `json:"keys"`
}

// pickArg returns the JSON value for a parameter: by name when the test case
// uses the parameter's name, otherwise by position.
func pickArg(input map[string]json.RawMessage, keys []string, name string, idx int, skipPos bool) (json.RawMessage, bool) {
    if raw, ok := input[name]; ok {
        return raw, true
    }
    positional := []string{}
    for _, k := range keys {
        if skipPos && k == "pos" {
            continue
        }
        positional = append(positional, k)
    }
    if idx < len(positional) {
        raw, ok := input[positional[idx]]
        return raw, ok
    }
    return nil, false
}

// LeetCode writes Go byte values (chars) as one-character strings.
func decodeByte(raw json.RawMessage) (byte, error) {
    var s string
    if err := json.Unmarshal(raw, &s); err == nil {
        if len(s) == 0 {
            return 0, nil
        }
        return s[0], nil
    }
    var n int
    err := json.Unmarshal(raw, &n)
    return byte(n), err
}

func decodeBytes(raw json.RawMessage) ([]byte, error) {
    var s string
    if err := json.Unmarshal(raw, &s); err == nil {
        return []byte(s), nil
    }
    var items []json.RawMessage
    if err := json.Unmarshal(raw, &items); err != nil {
        return nil, err
    }
    out := make([]byte, len(items))
    for i, item := range items {
        b, err := decodeByte(item)
        if err != nil {
            return nil, err
        }
        out[i] = b
    }
    return out, nil
}

func decodeByteGrid(raw json.RawMessage) ([][]byte, error) {
    var rows []json.RawMessage
    if err := json.Unmarshal(raw, &rows); err != nil {
        return nil, err
    }
    out := make([][]byte, len(rows))
    for i, row := range rows {
        b, err := decodeBytes(row)
        if err != nil {
            return nil, err
        }
        out[i] = b
    }
    return out, nil
}

type ListNode struct {
    Val  int
    Next *ListNode
}

type TreeNode struct {
    Val   int
    Left  *TreeNode
    Right *TreeNode
}

type Node struct {
    Val       int
    Neighbors []*Node
}

func toInt(value interface{}) (int, bool) {
    switch v := value.(type) {
    case float64:
        return int(v), true
    case float32:
        return int(v), true
    case int:
        return v, true
    case int32:
        return int(v), true
    case int64:
        return int(v), true
    default:
        return 0, false
    }
}

func buildLinkedList(values []int, pos int) *ListNode {
    if len(values) == 0 {
        return nil
    }

    dummy := &ListNode{}
    curr := dummy
    nodes := make([]*ListNode, 0, len(values))

    for _, v := range values {
        curr.Next = &ListNode{Val: v}
        curr = curr.Next
        nodes = append(nodes, curr)
    }

    if pos >= 0 && pos < len(nodes) {
        nodes[len(nodes)-1].Next = nodes[pos]
    }

    return dummy.Next
}

func linkedListToArray(head *ListNode) []int {
    result := make([]int, 0)
    visited := map[*ListNode]bool{}

    for head != nil && !visited[head] {
        visited[head] = true
        result = append(result, head.Val)
        head = head.Next
    }

    return result
}

func buildTree(values []interface{}) *TreeNode {
    if len(values) == 0 || values[0] == nil {
        return nil
    }

    nodes := make([]*TreeNode, len(values))
    for i, raw := range values {
        if raw == nil {
            continue
        }
        iv, ok := toInt(raw)
        if !ok {
            return nil
        }
        nodes[i] = &TreeNode{Val: iv}
    }

    pos := 1
    for i := 0; i < len(nodes) && pos < len(nodes); i++ {
        if nodes[i] == nil {
            continue
        }
        if pos < len(nodes) {
            nodes[i].Left = nodes[pos]
            pos++
        }
        if pos < len(nodes) {
            nodes[i].Right = nodes[pos]
            pos++
        }
    }

    return nodes[0]
}

func treeToArray(root *TreeNode) []interface{} {
    if root == nil {
        return []interface{}{}
    }

    result := make([]interface{}, 0)
    queue := []*TreeNode{root}

    for len(queue) > 0 {
        curr := queue[0]
        queue = queue[1:]

        if curr == nil {
            result = append(result, nil)
            continue
        }

        result = append(result, curr.Val)
        queue = append(queue, curr.Left, curr.Right)
    }

    for len(result) > 0 && result[len(result)-1] == nil {
        result = result[:len(result)-1]
    }

    return result
}

func buildGraph(adjList [][]int) *Node {
    if len(adjList) == 0 {
        return nil
    }

    nodes := make([]*Node, len(adjList))
    for i := range adjList {
        nodes[i] = &Node{Val: i + 1}
    }

    for i, neighbors := range adjList {
        for _, n := range neighbors {
            if n >= 1 && n <= len(nodes) {
                nodes[i].Neighbors = append(nodes[i].Neighbors, nodes[n-1])
            }
        }
    }

    return nodes[0]
}

func graphToAdjList(node *Node) [][]int {
    if node == nil {
        return [][]int{}
    }

    visited := map[*Node]bool{}
    queue := []*Node{node}
    ordered := make([]*Node, 0)
    maxVal := 0

    for len(queue) > 0 {
        curr := queue[0]
        queue = queue[1:]

        if curr == nil || visited[curr] {
            continue
        }

        visited[curr] = true
        ordered = append(ordered, curr)
        if curr.Val > maxVal {
            maxVal = curr.Val
        }

        for _, neighbor := range curr.Neighbors {
            if neighbor != nil && !visited[neighbor] {
                queue = append(queue, neighbor)
            }
        }
    }

    sort.Slice(ordered, func(i, j int) bool {
        return ordered[i].Val < ordered[j].Val
    })

    result := make([][]int, maxVal)
    for _, curr := range ordered {
        row := make([]int, 0, len(curr.Neighbors))
        for _, neighbor := range curr.Neighbors {
            if neighbor != nil {
                row = append(row, neighbor.Val)
            }
        }
        result[curr.Val-1] = row
    }

    return result
}

func autoConvertOutput(value interface{}) interface{} {
    switch v := value.(type) {
    case *ListNode:
        return linkedListToArray(v)
    case ListNode:
        vv := v
        return linkedListToArray(&vv)
    case *TreeNode:
        return treeToArray(v)
    case TreeNode:
        vv := v
        return treeToArray(&vv)
    case *Node:
        return graphToAdjList(v)
    case Node:
        vv := v
        return graphToAdjList(&vv)
    default:
        return normalizeGenericOutput(value)
    }
}

func bytesToStrings(b []byte) []string {
    out := make([]string, len(b))
    for i, c := range b {
        out[i] = string(c)
    }
    return out
}

func normalizeGenericOutput(value interface{}) interface{} {
    if value == nil {
        return nil
    }

    switch v := value.(type) {
    case byte:
        return string(v)
    case []byte:
        return bytesToStrings(v)
    case [][]byte:
        out := make([][]string, len(v))
        for i, row := range v {
            out[i] = bytesToStrings(row)
        }
        return out
    }

    rv := reflect.ValueOf(value)
    if rv.Kind() == reflect.Slice && rv.IsNil() {
        return []interface{}{}
    }

    return value
}

{source_code}

func execute(input map[string]json.RawMessage, keys []string) (out map[string]interface{}, err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("panic: %v", r)
        }
    }()
__PARAM_BINDINGS_PLACEHOLDER__

__INVOKER_SETUP_PLACEHOLDER__
__CALL_PLACEHOLDER__
}

func emit(obj map[string]interface{}) {
    data, err := json.Marshal(obj)
    if err != nil {
        data, _ = json.Marshal(map[string]interface{}{"error": "failed to serialize output: " + err.Error()})
    }
    os.Stdout.WriteString(resultStart + string(data) + resultEnd + "\n")
}

func fail(message string) {
    emit(map[string]interface{}{"error": message})
    os.Exit(1)
}

func main() {
    // Report runaway recursion as a stack overflow before it exhausts the
    // container's memory (Go's default limit is 1 GB).
    debug.SetMaxStack(256 << 20)

    raw, err := io.ReadAll(os.Stdin)
    if err != nil {
        fail("failed to read input")
    }

    if len(strings.TrimSpace(string(raw))) == 0 {
        fail("no input provided")
    }

    var p payload
    if err := json.Unmarshal(raw, &p); err != nil {
        fail("invalid JSON input")
    }

    if p.FunctionName != "" && p.FunctionName != "__FUNCTION_NAME_PLACEHOLDER__" {
        fail(fmt.Sprintf("function '%s' not found", p.FunctionName))
    }

    result, execErr := execute(p.Input, p.Keys)
    if execErr != nil {
        fail(execErr.Error())
    }
    emit(result)
}
"""
