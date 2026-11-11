"""Capture a pregel trace (the JSON :::superstep, :::fanout and :::reducer read) from a real LangGraph run.

  from capture import trace
  t = trace(graph, input, config, title="...")     # graph compiled with an InMemorySaver checkpointer
  json.dump(t, open("trace.json", "w"), indent=1)

The trace is built from what the run left behind: each checkpoint's channel_versions, versions_seen and values,
the writes the saver stored against it (with their task paths), and the debug stream's task events (names and
triggers). Only the run's own thread is read. Values are made JSON-safe with repr() where they are not.

  python capture.py      runs the demo graph (map-reduce with a deferred node) and prints its trace
"""
import json
import operator
from typing import Annotated, Literal, TypedDict


def _safe(v):
    try:
        json.dumps(v)
        return v
    except (TypeError, ValueError):
        if isinstance(v, (list, tuple)):
            return [_safe(x) for x in v]
        if isinstance(v, dict):
            return {str(k): _safe(x) for k, x in v.items()}
        if type(v).__name__ == "Interrupt":
            return {"value": _safe(v.value), "id": v.id}
        if type(v).__name__ == "Send":
            return {"node": v.node, "arg": _safe(v.arg)}
        return repr(v)


def _version(v):
    """InMemorySaver versions read '00000000000000000000000000000003.0.42': the integer part is the step's version"""
    if isinstance(v, str) and "." in v:
        return int(v.split(".")[0])
    return v


def trace(graph, inp, config, title=""):
    saver = graph.checkpointer
    names, triggers = {}, {}
    for ev in graph.stream(inp, config, stream_mode="debug"):
        if ev["type"] == "task":
            names[ev["payload"]["id"]] = ev["payload"]["name"]
            triggers[ev["payload"]["id"]] = list(ev["payload"]["triggers"])
    history = list(saver.list(config))[::-1]                     # oldest first
    thread = config["configurable"]["thread_id"]
    steps, prev = [], None
    for k, tup in enumerate(history):
        cp, md = tup.checkpoint, tup.metadata
        cv = {c: _version(v) for c, v in cp["channel_versions"].items()}
        step = {"step": md["step"], "source": md["source"], "checkpoint": cp["id"], "tasks": []}
        if prev is not None:                                     # the tasks that ran from the previous checkpoint
            stored = saver.writes.get((thread, "", prev.checkpoint["id"]), {})
            by_task = {}
            for (tid, idx), (_, chan, blob, path) in sorted(stored.items(), key=lambda kv: (kv[1][3], kv[0][0], kv[0][1])):
                by_task.setdefault(tid, {"path": path, "writes": []})["writes"].append(
                    [chan, _safe(saver.serde.loads_typed(blob))])
            seen0, seen1 = prev.checkpoint["versions_seen"], cp["versions_seen"]
            for tid, t in by_task.items():
                name = names.get(tid) or t["path"].split(", ")[-1]      # a pull path ends in its node's name
                # the start task sends no debug event: its triggers are the channels its versions_seen moved on
                trig = triggers.get(tid) or sorted(c for c, v in seen1.get(name, {}).items()
                                                    if v != seen0.get(name, {}).get(c))
                step["tasks"].append({
                    "id": tid, "name": name,
                    "kind": "push" if "__pregel_push" in t["path"] else "pull",
                    "triggers": trig, "path": t["path"], "writes": t["writes"],
                    "status": "interrupted" if any(c == "__interrupt__" for c, _ in t["writes"]) else "ok"})
            pv = {c: _version(v) for c, v in prev.checkpoint["channel_versions"].items()}
            step["updated"] = sorted(c for c in cv if cv[c] != pv.get(c))
        else:
            step["updated"] = sorted(cv)
            step["input"] = _safe(inp)
        step["channel_versions"] = cv
        step["available"] = sorted(cp["channel_values"])          # channels holding a value: only these can trigger
        step["versions_seen"] = {n: {c: _version(v) for c, v in seen.items()}
                                 for n, seen in cp["versions_seen"].items() if n != "__input__"}
        step["values"] = _safe({c: v for c, v in cp["channel_values"].items() if not c.startswith(("branch:", "__"))})
        snap = graph.get_state({"configurable": {"thread_id": thread, "checkpoint_id": cp["id"]}})
        step["next"] = list(snap.next)
        steps.append(step)
        prev = tup
    chans = {}
    for name, ch in graph.channels.items():
        if name.startswith("__") and name not in ("__start__", "__pregel_tasks"):
            continue
        info = {"type": type(ch).__name__}
        op = getattr(ch, "operator", None)
        if op is not None:
            info["reducer"] = getattr(op, "__name__", repr(op))
        chans[name] = info
    defer = [n for n, node in graph.builder.nodes.items() if getattr(node, "defer", False)]
    pushed = {t["name"] for s in steps for t in s["tasks"] if t["kind"] == "push"}
    return {"title": title, "channels": chans, "defer": defer, "graph": graph_json(graph, title, pushed, defer),
            "steps": steps}


def graph_json(graph, title="", pushed=(), defer=()):
    """the compiled graph as a loopgraph JSON (no run): the stepper's graph pane. A conditional edge into a node that
    ran as a PUSH task is drawn as a Send"""
    g = graph.get_graph()
    kind = {"__start__": "start", "__end__": "end"}
    nodes = [{"id": n, "kind": kind.get(n, "step"), "label": {"__start__": "START", "__end__": "END"}.get(n, n),
              **({"sub": "defer"} if n in defer else {})} for n in g.nodes]
    edges = []
    for e in g.edges:
        x = {"from": e.source, "to": e.target}
        if e.conditional:
            x["kind"] = "send" if e.target in pushed else "cond"
            if x["kind"] == "cond":
                x["when"] = str(e.data) if e.data else "route"
        edges.append(x)
    return {"id": "graph", "title": title, "dir": "LR", "nodes": nodes, "edges": edges}


def demo():
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command, Send

    class S(TypedDict):
        topic: str
        subjects: list
        results: Annotated[list, operator.add]
        summary: str

    def plan(s):
        return {"subjects": ["moon", "sun", "sea"]}

    def fan(s):
        return [Send("work", {"subject": x}) for x in s["subjects"]] + ["audit"]

    def work(a) -> Command[Literal["verify"]]:                  # the annotation puts the goto on the drawn graph
        if a["subject"] == "sun":                                # one branch takes a step more
            return Command(update={"results": ["sun: draft"]}, goto="verify")
        return Command(update={"results": [a["subject"] + ": done"]})

    def verify(s):
        return {"results": ["sun: verified"]}

    def audit(s):
        return {"results": [f"audit: {len(s['subjects'])} subjects"]}

    def summarize(s):
        return {"summary": f"{len(s['results'])} results"}

    b = StateGraph(S)
    b.add_node("plan", plan)
    b.add_node("work", work)
    b.add_node("verify", verify)
    b.add_node("audit", audit)
    b.add_node("summarize", summarize, defer=True)
    b.add_edge(START, "plan")
    b.add_conditional_edges("plan", fan, ["work", "audit"])
    b.add_edge("work", "summarize")
    b.add_edge("verify", "summarize")
    b.add_edge("audit", "summarize")
    b.add_edge("summarize", END)
    g = b.compile(checkpointer=InMemorySaver())
    return trace(g, {"topic": "tides"}, {"configurable": {"thread_id": "demo"}},
                 title="Map-reduce with a deferred summary")


if __name__ == "__main__":
    print(json.dumps(demo(), indent=1))


def history(graph, config, title="", labels=None):
    """the thread's checkpoints as the :::checkpoints JSON: every checkpoint the saver holds for the thread, forks
    included, oldest first, each with its parent, source, step, next, pending writes and interrupts"""
    saver = graph.checkpointer
    thread = config["configurable"]["thread_id"]
    out = []
    for tup in list(saver.list({"configurable": {"thread_id": thread}}))[::-1]:
        cp, md = tup.checkpoint, tup.metadata
        snap = graph.get_state({"configurable": {"thread_id": thread, "checkpoint_id": cp["id"]}})
        c = {"id": cp["id"], "parent": (tup.parent_config or {}).get("configurable", {}).get("checkpoint_id"),
             "step": md["step"], "source": md["source"], "next": list(snap.next),
             "values": _safe({k: v for k, v in snap.values.items()}) if isinstance(snap.values, dict) else {},
             "pending_writes": [[tid, chan, _safe(val)] for tid, chan, val in (tup.pending_writes or [])],
             "tasks": [{"name": t.name, "interrupts": [_safe(i.value) for i in t.interrupts]}
                       for t in snap.tasks if t.interrupts]}
        if labels and cp["id"] in labels:
            c["label"] = labels[cp["id"]]
        out.append(c)
    head = graph.get_state({"configurable": {"thread_id": thread}}).config["configurable"]["checkpoint_id"]
    return {"title": title, "thread": thread, "head": head, "checkpoints": out}
