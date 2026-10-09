# The wrapper uses fully qualified paths only (no `use` at the crate root), so
# the user's own `use std::rc::Rc;` etc. never clash with it.
RUST_WRAPPER_TEMPLATE = r"""
#![allow(dead_code, unused_imports, unused_variables, unused_mut, non_snake_case)]

__SOLUTION_STRUCT_PLACEHOLDER__

__NODE_DEFINITIONS_PLACEHOLDER__

mod __judge {
    use serde_json::{json, Value};
    use std::cell::RefCell;
    use std::rc::Rc;

    use super::{ListNode, TreeNode};

    pub const RESULT_START: &str = "__JUDGE_RESULT_7f3a__";
    pub const RESULT_END: &str = "__JUDGE_END_7f3a__";

    pub fn emit(output: &Value) {
        println!("{}{}{}", RESULT_START, output, RESULT_END);
    }

    pub fn emit_error(message: &str) {
        emit(&json!({ "error": message }));
    }

    /// The argument for a parameter: by name when the test case uses it,
    /// otherwise by position.
    pub fn pick(payload: &Value, name: &str, index: usize, skip_pos: bool) -> Value {
        let keys = payload["keys"].as_array().cloned().unwrap_or_default();
        let values = payload["values"].as_array().cloned().unwrap_or_default();
        for (k, v) in keys.iter().zip(values.iter()) {
            if k.as_str() == Some(name) {
                return v.clone();
            }
        }
        let mut position = 0;
        for (k, v) in keys.iter().zip(values.iter()) {
            if skip_pos && k.as_str() == Some("pos") {
                continue;
            }
            if position == index {
                return v.clone();
            }
            position += 1;
        }
        panic!("missing argument: {}", name);
    }

    pub fn list_cycle_pos(payload: &Value) -> i64 {
        let keys = payload["keys"].as_array().cloned().unwrap_or_default();
        let values = payload["values"].as_array().cloned().unwrap_or_default();
        for (k, v) in keys.iter().zip(values.iter()) {
            if k.as_str() == Some("pos") {
                return v.as_i64().unwrap_or(-1);
            }
        }
        -1
    }

    pub fn build_tree(value: &Value) -> Option<Rc<RefCell<TreeNode>>> {
        let items = value.as_array()?;
        let vals: Vec<Option<i32>> = items.iter().map(|v| v.as_i64().map(|n| n as i32)).collect();
        let root_val = (*vals.first()?)?;
        let root = Rc::new(RefCell::new(TreeNode::new(root_val)));
        let mut queue = std::collections::VecDeque::new();
        queue.push_back(root.clone());
        let mut i = 1;
        while let Some(node) = queue.pop_front() {
            if i >= vals.len() {
                break;
            }
            if let Some(v) = vals[i] {
                let child = Rc::new(RefCell::new(TreeNode::new(v)));
                node.borrow_mut().left = Some(child.clone());
                queue.push_back(child);
            }
            i += 1;
            if i < vals.len() {
                if let Some(v) = vals[i] {
                    let child = Rc::new(RefCell::new(TreeNode::new(v)));
                    node.borrow_mut().right = Some(child.clone());
                    queue.push_back(child);
                }
            }
            i += 1;
        }
        Some(root)
    }

    pub fn tree_to_json(root: &Option<Rc<RefCell<TreeNode>>>) -> Value {
        let mut out: Vec<Value> = Vec::new();
        let mut queue = std::collections::VecDeque::new();
        queue.push_back(root.clone());
        while let Some(node) = queue.pop_front() {
            match node {
                Some(n) => {
                    let n = n.borrow();
                    out.push(json!(n.val));
                    queue.push_back(n.left.clone());
                    queue.push_back(n.right.clone());
                }
                None => out.push(Value::Null),
            }
        }
        while matches!(out.last(), Some(Value::Null)) {
            out.pop();
        }
        Value::Array(out)
    }

    pub fn build_list(value: &Value) -> Option<Box<ListNode>> {
        let items = value.as_array()?;
        let mut head: Option<Box<ListNode>> = None;
        for v in items.iter().rev() {
            let mut node = Box::new(ListNode::new(v.as_i64().unwrap_or(0) as i32));
            node.next = head;
            head = Some(node);
        }
        head
    }

    pub fn list_to_json(head: &Option<Box<ListNode>>) -> Value {
        let mut out = Vec::new();
        let mut cur = head;
        while let Some(node) = cur {
            out.push(json!(node.val));
            cur = &node.next;
        }
        Value::Array(out)
    }

    pub fn panic_message(info: &std::panic::PanicInfo) -> String {
        let payload = info.payload();
        let message = if let Some(s) = payload.downcast_ref::<&str>() {
            s.to_string()
        } else if let Some(s) = payload.downcast_ref::<String>() {
            s.clone()
        } else {
            "panic".to_string()
        };
        match info.location() {
            Some(loc) => format!("panicked at line {}: {}", loc.line(), message),
            None => format!("panicked: {}", message),
        }
    }
}

fn __judge_run(payload: serde_json::Value) -> serde_json::Value {
    __PARAMETER_DESERIALIZATION_PLACEHOLDER__

    __CALL_AND_SERIALIZE_PLACEHOLDER__
}

fn main() {
    let mut input = String::new();
    if std::io::Read::read_to_string(&mut std::io::stdin(), &mut input).is_err() {
        __judge::emit_error("Failed to read input");
        std::process::exit(1);
    }

    let payload: serde_json::Value = match serde_json::from_str(&input) {
        Ok(v) => v,
        Err(_) => {
            __judge::emit_error("Invalid JSON input");
            std::process::exit(1);
        }
    };

    std::panic::set_hook(Box::new(|info| {
        __judge::emit_error(&__judge::panic_message(info));
    }));

    // Deep recursion (DFS on 10^5 nodes) needs a bigger stack than the default.
    let worker = std::thread::Builder::new()
        .stack_size(256 * 1024 * 1024)
        .spawn(move || __judge_run(payload))
        .expect("failed to start worker thread");

    match worker.join() {
        Ok(output) => __judge::emit(&output),
        Err(_) => std::process::exit(1),
    }
}

// ======================================================
// USER CODE
// ======================================================

__USER_CODE_PLACEHOLDER__
"""

SOLUTION_STRUCT = "pub struct Solution;"

TREE_NODE_DEFINITION = r"""
#[derive(Debug, PartialEq, Eq)]
pub struct TreeNode {
    pub val: i32,
    pub left: Option<std::rc::Rc<std::cell::RefCell<TreeNode>>>,
    pub right: Option<std::rc::Rc<std::cell::RefCell<TreeNode>>>,
}

impl TreeNode {
    #[inline]
    pub fn new(val: i32) -> Self {
        TreeNode { val, left: None, right: None }
    }
}
"""

LIST_NODE_DEFINITION = r"""
#[derive(PartialEq, Eq, Clone, Debug)]
pub struct ListNode {
    pub val: i32,
    pub next: Option<Box<ListNode>>,
}

impl ListNode {
    #[inline]
    pub fn new(val: i32) -> Self {
        ListNode { next: None, val }
    }
}
"""
