"use client";
import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STATUS_COLORS: Record<string, string> = {
  submitted: "#22c55e",
  awaiting_review: "#f59e0b",
  failed: "#ef4444",
  pending: "#6366f1",
  in_progress: "#3b82f6",
};

// ─── Auth helpers ──────────────────────────────────────────────────────────────
function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("jwt_token");
}
function setToken(t: string) { localStorage.setItem("jwt_token", t); }
function clearToken() { localStorage.removeItem("jwt_token"); }

// ─── Main App ──────────────────────────────────────────────────────────────────
export default function Home() {
  const [user, setUser] = useState<any>(null);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [parsedResume, setParsedResume] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);
  const [pendingReviews, setPendingReviews] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setTab] = useState<"dashboard" | "upload" | "jobs" | "applications" | "review">("dashboard");

  // ── Bootstrap: check for token in URL (from LinkedIn OAuth redirect) ──
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get("token");
    if (t) {
      setToken(t);
      window.history.replaceState({}, "", "/");
    }
    const stored = getToken();
    if (stored) fetchMe(stored);
    fetchStats();
    fetchPendingReviews();
  }, []);

  async function fetchMe(token: string) {
    try {
      const res = await axios.get(`${API}/api/auth/me`, { params: { token } });
      setUser(res.data);
    } catch { clearToken(); }
  }

  const fetchStats = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/dashboard/stats`);
      setStats(res.data);
    } catch {}
  }, []);

  const fetchPendingReviews = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/review/pending`);
      setPendingReviews(res.data.pending || []);
    } catch {}
  }, []);

  async function fetchApplications() {
    try {
      const res = await axios.get(`${API}/api/applications/`);
      setApplications(res.data.applications || []);
    } catch {}
  }

  // ── Resume Upload ──
  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    const form = new FormData();
    form.append("file", file);
    const res = await axios.post(`${API}/api/resume/upload`, form);
    setResumeId(res.data.id);
    setParsedResume(res.data.parsed);
    setLoading(false);
    setTab("jobs");
  }

  // ── Find Jobs ──
  async function handleFindJobs() {
    if (!resumeId) return;
    setLoading(true);
    const res = await axios.get(`${API}/api/jobs/search`, { params: { resume_id: resumeId } });
    setJobs(res.data.jobs);
    setLoading(false);
  }

  // ── Auto Apply ──
  async function handleApply(jobId: string) {
    if (!resumeId) return;
    setLoading(true);
    const res = await axios.post(`${API}/api/applications/start`, {
      job_id: jobId,
      resume_id: resumeId,
      user_id: user?.id ?? null,
    });
    if (res.data.status === "awaiting_review") {
      await fetchPendingReviews();
      setTab("review");
    }
    await fetchApplications();
    await fetchStats();
    setLoading(false);
  }

  // ── Submit Human Answers ──
  async function handleAnswerSubmit(applicationId: string, answers: Record<string, string>) {
    setLoading(true);
    await axios.post(`${API}/api/review/${applicationId}/answer`, { answers });
    await fetchPendingReviews();
    await fetchApplications();
    await fetchStats();
    setLoading(false);
  }

  const pendingCount = pendingReviews.length;

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      {/* ── Navbar ── */}
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex justify-between items-center">
        <span className="text-lg font-bold">🤖 AI Job Agent</span>
        {user ? (
          <div className="flex items-center gap-3">
            {user.avatar_url && <img src={user.avatar_url} className="w-8 h-8 rounded-full" alt="avatar" />}
            <span className="text-sm text-gray-300">{user.name}</span>
            <button onClick={() => { clearToken(); setUser(null); }} className="text-xs text-gray-500 hover:text-white">Logout</button>
          </div>
        ) : (
          <a
            href={`${API}/api/auth/linkedin`}
            className="flex items-center gap-2 bg-[#0077B5] px-4 py-2 rounded text-sm font-medium hover:bg-[#006097] transition"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
            Sign in with LinkedIn
          </a>
        )}
      </nav>

      {/* ── Tabs ── */}
      <div className="flex gap-1 px-6 pt-4 border-b border-gray-800">
        {(["dashboard", "upload", "jobs", "applications", "review"] as const).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); if (t === "applications") fetchApplications(); if (t === "dashboard") fetchStats(); }}
            className={`px-4 py-2 text-sm capitalize rounded-t transition ${activeTab === t ? "bg-gray-800 text-white" : "text-gray-400 hover:text-white"}`}
          >
            {t}
            {t === "review" && pendingCount > 0 && (
              <span className="ml-2 bg-red-500 text-xs px-1.5 py-0.5 rounded-full">{pendingCount}</span>
            )}
          </button>
        ))}
      </div>

      <main className="flex-1 p-6">

        {/* ════ DASHBOARD ════ */}
        {activeTab === "dashboard" && <DashboardTab stats={stats} />}

        {/* ════ UPLOAD ════ */}
        {activeTab === "upload" && (
          <div className="max-w-lg">
            <h2 className="text-xl font-bold mb-4">Upload Resume</h2>
            {!user && (
              <div className="bg-blue-950 border border-blue-800 rounded p-3 mb-4 text-sm text-blue-300">
                💡 Sign in with LinkedIn above to enable email notifications and link applications to your profile.
              </div>
            )}
            <label className="block mb-2 text-gray-300">Select PDF or DOCX</label>
            <input type="file" accept=".pdf,.doc,.docx" onChange={handleUpload}
              className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:bg-blue-600 file:text-white file:cursor-pointer" />
            {loading && <p className="mt-4 text-blue-400 animate-pulse">Parsing resume with GPT-4…</p>}
            {parsedResume && (
              <div className="mt-6 bg-gray-800 p-4 rounded-lg">
                <h3 className="font-bold mb-3 text-green-400">✅ Resume Parsed</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><span className="text-gray-400">Name</span><p className="font-medium">{parsedResume.name}</p></div>
                  <div><span className="text-gray-400">Email</span><p className="font-medium">{parsedResume.email}</p></div>
                </div>
                <div className="mt-3">
                  <span className="text-gray-400 text-sm">Top Skills</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {parsedResume.skills?.slice(0, 8).map((s: string) => (
                      <span key={s} className="bg-blue-900 text-blue-200 text-xs px-2 py-0.5 rounded">{s}</span>
                    ))}
                  </div>
                </div>
                <button onClick={handleFindJobs} className="mt-4 bg-green-600 hover:bg-green-500 px-4 py-2 rounded w-full font-medium transition">
                  🔍 Find Matching Jobs
                </button>
              </div>
            )}
          </div>
        )}

        {/* ════ JOBS ════ */}
        {activeTab === "jobs" && (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Matching Jobs {jobs.length > 0 && `(${jobs.length})`}</h2>
              <button onClick={handleFindJobs} disabled={!resumeId} className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-4 py-2 rounded text-sm transition">
                🔄 Refresh
              </button>
            </div>
            {loading && <p className="text-blue-400 animate-pulse">Searching & scoring jobs with AI…</p>}
            {jobs.length === 0 && !loading && (
              <div className="text-center py-16 text-gray-500">
                <p className="text-4xl mb-3">🔍</p>
                <p>Upload your resume first, then click "Find Matching Jobs"</p>
              </div>
            )}
            <div className="grid gap-3">
              {jobs.map((job) => (
                <div key={job.id} className="bg-gray-800 hover:bg-gray-750 p-4 rounded-lg flex justify-between items-center transition">
                  <div>
                    <p className="font-semibold">{job.title}</p>
                    <p className="text-gray-400 text-sm">{job.company}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="h-1.5 w-24 bg-gray-700 rounded">
                        <div className="h-1.5 bg-green-500 rounded" style={{ width: `${Math.round(job.match_score * 100)}%` }} />
                      </div>
                      <span className="text-green-400 text-xs font-medium">{Math.round(job.match_score * 100)}% match</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <a href={job.url} target="_blank" rel="noreferrer" className="bg-gray-700 hover:bg-gray-600 px-3 py-1.5 rounded text-sm transition">View</a>
                    <button onClick={() => handleApply(job.id)} disabled={loading}
                      className="bg-blue-600 hover:bg-blue-500 disabled:opacity-40 px-3 py-1.5 rounded text-sm transition">
                      {loading ? "…" : "Auto Apply"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ════ APPLICATIONS ════ */}
        {activeTab === "applications" && (
          <div>
            <h2 className="text-xl font-bold mb-4">Applications ({applications.length})</h2>
            {applications.length === 0 && (
              <div className="text-center py-16 text-gray-500">
                <p className="text-4xl mb-3">📋</p><p>No applications yet</p>
              </div>
            )}
            <div className="grid gap-3">
              {applications.map((app) => (
                <div key={app.id} className="bg-gray-800 p-4 rounded-lg flex justify-between items-center">
                  <div>
                    <p className="font-semibold">{app.job_title}</p>
                    <p className="text-gray-400 text-sm">{app.company}</p>
                    {app.submitted_at && <p className="text-gray-500 text-xs">Submitted {new Date(app.submitted_at).toLocaleDateString()}</p>}
                  </div>
                  <span className="px-3 py-1 rounded-full text-xs font-medium" style={{ background: STATUS_COLORS[app.status] + "22", color: STATUS_COLORS[app.status] }}>
                    {app.status.replace("_", " ")}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ════ REVIEW QUEUE ════ */}
        {activeTab === "review" && (
          <div>
            <h2 className="text-xl font-bold mb-1">🧑 Human Review Queue</h2>
            <p className="text-gray-400 text-sm mb-5">The AI couldn't answer these questions. Your answers will be saved for future applications.</p>
            {pendingReviews.length === 0 && (
              <div className="text-center py-16 text-gray-500">
                <p className="text-4xl mb-3">🎉</p><p>No pending reviews — AI handled everything!</p>
              </div>
            )}
            {pendingReviews.map((review) => (
              <ReviewForm key={review.application_id} review={review} onSubmit={handleAnswerSubmit} />
            ))}
          </div>
        )}

      </main>
    </div>
  );
}

// ─── Dashboard Tab ─────────────────────────────────────────────────────────────
function DashboardTab({ stats }: { stats: any }) {
  if (!stats) return <div className="text-gray-500 text-center py-16 animate-pulse">Loading stats…</div>;

  const pieData = Object.entries(stats.status_counts || {})
    .filter(([, v]) => (v as number) > 0)
    .map(([name, value]) => ({ name, value }));

  return (
    <div>
      <h2 className="text-xl font-bold mb-6">Dashboard</h2>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <KpiCard label="Total Applications" value={stats.total_applications} color="blue" />
        <KpiCard label="Submitted" value={stats.status_counts?.submitted ?? 0} color="green" />
        <KpiCard label="Needs Review" value={stats.status_counts?.awaiting_review ?? 0} color="yellow" />
        <KpiCard label="Success Rate" value={`${stats.success_rate}%`} color="purple" />
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        {/* Daily Activity Bar Chart */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="font-semibold mb-4 text-gray-300">Daily Applications (14 days)</h3>
          {stats.daily_activity?.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={stats.daily_activity}>
                <XAxis dataKey="date" tick={{ fill: "#6b7280", fontSize: 11 }} tickFormatter={(d) => d.slice(5)} />
                <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} allowDecimals={false} />
                <Tooltip contentStyle={{ background: "#1f2937", border: "none", borderRadius: 8 }} />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-500 text-sm text-center py-8">No data yet</p>}
        </div>

        {/* Status Pie Chart */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="font-semibold mb-4 text-gray-300">Applications by Status</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={65} label={({ name, percent }) => `${name} ${Math.round(percent * 100)}%`} labelLine={false}>
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={STATUS_COLORS[entry.name] || "#6b7280"} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "#1f2937", border: "none", borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-500 text-sm text-center py-8">No data yet</p>}
        </div>
      </div>

      {/* Top Companies */}
      {stats.top_companies?.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="font-semibold mb-3 text-gray-300">Top Companies Applied To</h3>
          <div className="space-y-2">
            {stats.top_companies.map((c: any) => (
              <div key={c.company} className="flex justify-between items-center">
                <span className="text-sm">{c.company}</span>
                <span className="bg-blue-900 text-blue-200 text-xs px-2 py-0.5 rounded-full">{c.count} application{c.count > 1 ? "s" : ""}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function KpiCard({ label, value, color }: { label: string; value: any; color: string }) {
  const colorMap: Record<string, string> = { blue: "text-blue-400", green: "text-green-400", yellow: "text-yellow-400", purple: "text-purple-400" };
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <p className="text-gray-400 text-xs mb-1">{label}</p>
      <p className={`text-2xl font-bold ${colorMap[color]}`}>{value}</p>
    </div>
  );
}

// ─── Review Form ───────────────────────────────────────────────────────────────
function ReviewForm({ review, onSubmit }: { review: any; onSubmit: (id: string, answers: Record<string, string>) => void }) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  return (
    <div className="bg-gray-800 rounded-lg p-5 mb-4 border border-yellow-900">
      <div className="flex justify-between items-start mb-3">
        <div>
          <p className="font-bold">{review.job_title} <span className="text-gray-400 font-normal">@ {review.company}</span></p>
          <p className="text-yellow-400 text-xs mt-0.5">{review.pending_questions?.length} question(s) need your input</p>
        </div>
      </div>
      {review.pending_questions?.map((q: any, i: number) => (
        <div key={i} className="mb-4">
          <label className="block text-sm font-medium mb-1">{q.field}</label>
          <p className="text-gray-500 text-xs mb-1.5">{q.reason}</p>
          <input type="text" placeholder="Your answer…"
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            onChange={(e) => setAnswers((prev) => ({ ...prev, [q.field]: e.target.value }))} />
        </div>
      ))}
      <button onClick={() => onSubmit(review.application_id, answers)}
        className="bg-green-600 hover:bg-green-500 px-4 py-2 rounded w-full font-medium transition">
        ✅ Submit & Continue Application
      </button>
    </div>
  );
}
