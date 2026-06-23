import { useEffect, useState, type FormEvent } from "react"
import { createTask, listTasks, type Task } from "./api"

const COLUMNS: { key: Task["status"]; label: string }[] = [
  { key: "pending", label: "📋 待办" },
  { key: "in_progress", label: "🔧 进行中" },
  { key: "done", label: "✅ 已完成" },
  { key: "failed", label: "⚠️ 失败" },
]

export default function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")

  useEffect(() => {
    const tick = () => listTasks().then(setTasks).catch(() => {})
    tick()
    const id = setInterval(tick, 2000) // 轮询刷新状态(实时推送留后面)
    return () => clearInterval(id)
  }, [])

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    await createTask(title.trim(), description.trim())
    setTitle("")
    setDescription("")
    listTasks().then(setTasks)
  }

  return (
    <div className="min-h-screen bg-neutral-50 text-neutral-900 p-6">
      <h1 className="text-2xl font-bold mb-1">AutoBoard</h1>
      <p className="text-neutral-500 mb-6">发任务,后台 agent 自动接单完成</p>

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
        <button className="rounded-md bg-neutral-900 text-white px-5 py-2 font-medium hover:bg-neutral-700">
          发布
        </button>
      </form>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {COLUMNS.map((col) => {
          const items = tasks.filter((t) => t.status === col.key)
          return (
            <div key={col.key} className="bg-white rounded-lg border border-neutral-200 p-3">
              <div className="font-semibold mb-3 flex justify-between">
                <span>{col.label}</span>
                <span className="text-neutral-400">{items.length}</span>
              </div>
              <div className="space-y-3">
                {items.map((t) => (
                  <div key={t.id} className="rounded-md border border-neutral-200 p-3 shadow-sm">
                    <div className="font-medium">{t.title}</div>
                    {t.description && (
                      <div className="text-sm text-neutral-500 mt-1">{t.description}</div>
                    )}
                    {t.result && (
                      <div className="text-sm mt-2 bg-neutral-50 rounded p-2 whitespace-pre-wrap">
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
