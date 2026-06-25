import { useEffect, useState, type FormEvent } from "react"
import {
  cancelTask,
  createTask,
  getMe,
  getToken,
  listTasks,
  logout,
  type Me,
  type Task,
} from "./api"
import Login from "./Login"

// decomposing 归到「进行中」列展示(拆解也是一种处理中)
const COLUMNS: { key: Task["status"]; label: string; also?: Task["status"][] }[] = [
  { key: "pending", label: "📋 待办" },
  { key: "in_progress", label: "🔧 进行中", also: ["decomposing"] },
  { key: "done", label: "✅ 已完成" },
  { key: "failed", label: "⚠️ 失败" },
  { key: "cancelled", label: "🚫 已取消" },
]

const CANCELLABLE: Task["status"][] = ["pending", "decomposing", "in_progress"]

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [decompose, setDecompose] = useState(false)
  const [me, setMe] = useState<Me | null>(null)
  const [authed, setAuthed] = useState(!!getToken())
  const [err, setErr] = useState("")

  const refresh = () =>
    listTasks()
      .then(setTasks)
      .catch((e) => {
        setErr(String(e.message))
        if (!getToken()) setAuthed(false) // 401 已清 token → 跳回登录
      })

  useEffect(() => {
    if (!authed) return
    getMe().then(setMe).catch(() => {})
    refresh()
    const id = setInterval(refresh, 2000) // 轮询刷新状态(实时推送留后面)
    return () => clearInterval(id)
  }, [authed])

  function onLogout() {
    logout()
    setAuthed(false)
    setMe(null)
    setTasks([])
  }

  if (!authed) return <Login onLogin={() => setAuthed(true)} />

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    try {
      await createTask(title.trim(), description.trim(), decompose)
      setTitle("")
      setDescription("")
      setErr("")
      refresh()
    } catch (e) {
      setErr(String((e as Error).message))
    }
  }

  async function onCancel(id: string) {
    try {
      await cancelTask(id)
      setErr("")
      refresh()
    } catch (e) {
      setErr(String((e as Error).message))
    }
  }

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900 p-6">
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-2xl font-bold">AutoBoard</h1>
        <div className="text-sm text-neutral-600 flex items-center gap-3">
          {me && (
            <span>
              {me.username}
              {me.roles.length > 0 && <span className="text-neutral-400"> · {me.roles.join(",")}</span>}
            </span>
          )}
          <button onClick={onLogout} className="text-neutral-400 hover:text-neutral-900">
            退出
          </button>
        </div>
      </div>
      <p className="text-neutral-500 mb-6">发任务,后台 agent 自动接单完成</p>

      {err && (
        <div className="mb-4 rounded-md bg-red-50 border border-red-200 text-red-700 px-3 py-2 text-sm">
          {err}
        </div>
      )}

      <form onSubmit={submit} className="flex flex-col sm:flex-row gap-2 mb-8 max-w-3xl">
        <input
          className="flex-1 rounded-md border border-neutral-300 px-3 py-2 outline-none focus:border-neutral-900"
          placeholder="任务标题,例如:调研 deepagents 优缺点"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <input
          className="flex-1 rounded-md border border-neutral-300 px-3 py-2 outline-none focus:border-neutral-900"
          placeholder="补充描述(可选)"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <label className="flex items-center gap-1.5 text-sm text-neutral-600 whitespace-nowrap px-1">
          <input type="checkbox" checked={decompose} onChange={(e) => setDecompose(e.target.checked)} />
          先拆解
        </label>
        <button className="rounded-md bg-neutral-900 text-white px-5 py-2 font-medium hover:bg-neutral-700">
          发布
        </button>
      </form>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {COLUMNS.map((col) => {
          const states = [col.key, ...(col.also ?? [])]
          const items = tasks.filter((t) => states.includes(t.status))
          return (
            <div key={col.key} className="bg-white rounded-lg border border-neutral-200 p-3">
              <div className="font-semibold mb-3 flex justify-between">
                <span>{col.label}</span>
                <span className="text-neutral-400">{items.length}</span>
              </div>
              <div className="space-y-3">
                {items.map((t) => (
                  <div key={t.id} className="rounded-md border border-neutral-200 p-3 shadow-sm">
                    <div className="font-medium flex items-start justify-between gap-2">
                      <span>
                        {t.parent_id && <span className="text-neutral-400 mr-1">↳</span>}
                        {t.title}
                      </span>
                      {CANCELLABLE.includes(t.status) && (
                        <button
                          onClick={() => onCancel(t.id)}
                          className="text-xs text-neutral-400 hover:text-red-600 shrink-0"
                        >
                          取消
                        </button>
                      )}
                    </div>
                    {t.description && (
                      <div className="text-sm text-neutral-500 mt-1">{t.description}</div>
                    )}
                    {t.result && (
                      <div className="text-sm mt-2 bg-neutral-50 rounded p-2 whitespace-pre-wrap max-h-48 overflow-y-auto">
                        {t.result}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
