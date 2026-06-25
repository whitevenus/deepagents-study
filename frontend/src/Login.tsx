import { useState, type FormEvent } from "react"
import { login } from "./api"

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [err, setErr] = useState("")

  async function submit(e: FormEvent) {
    e.preventDefault()
    try {
      await login(username.trim(), password)
      onLogin()
    } catch (e) {
      setErr(String((e as Error).message))
    }
  }

  return (
    <div className="min-h-screen bg-neutral-50 flex items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-sm bg-white rounded-lg border border-neutral-200 p-6 space-y-4">
        <div>
          <h1 className="text-2xl font-bold">AutoBoard</h1>
          <p className="text-neutral-500 text-sm mt-1">请登录</p>
        </div>
        {err && (
          <div className="rounded-md bg-red-50 border border-red-200 text-red-700 px-3 py-2 text-sm">{err}</div>
        )}
        <input
          className="w-full rounded-md border border-neutral-300 px-3 py-2 outline-none focus:border-neutral-900"
          placeholder="用户名"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          className="w-full rounded-md border border-neutral-300 px-3 py-2 outline-none focus:border-neutral-900"
          placeholder="密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button className="w-full rounded-md bg-neutral-900 text-white py-2 font-medium hover:bg-neutral-700">
          登录
        </button>
        <p className="text-xs text-neutral-400">
          demo:alice/bob/carol,密码=用户名(alice=管理员 / bob=成员 / carol=只读)
        </p>
      </form>
    </div>
  )
}
