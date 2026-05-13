import React, { useEffect, useState } from "react";
import axios from "axios";
import { 
  LogOut, 
  Zap, 
  FileCheck, 
  ShieldCheck, 
  LayoutDashboard, 
  History, 
  ChevronRight,
  RefreshCw,
  Activity
} from "lucide-react";
import Logo from "../components/Logo";

interface UserInfo { email: string; name: string; role: string; }
interface DashboardStats { archived_count: number; pending_count: number; service_account_configured: boolean; last_sync: string; }

const DashboardPage: React.FC = () => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [userRes, statsRes] = await Promise.all([
          axios.get('/api/user-info', { withCredentials: true }),
          axios.get('/api/registry/stats', { withCredentials: true })
        ]);
        setUser(userRes.data);
        setStats(statsRes.data);
      } catch (err) {
        console.error("Dashboard Fetch Failed", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    window.location.hash = "";
  };

  if (loading) return (
    <div className="h-screen w-full bg-slate-50 flex items-center justify-center">
      <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans relative overflow-hidden transition-colors duration-300">
      {/* Background Gradients */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-[120px] pointer-events-none"></div>

      {/* Navbar */}
      <nav className="bg-white/70 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-50 transition-all">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Logo size={50} />
            <span className="text-xl font-black text-gray-900 tracking-tight ml-1 uppercase">DriveSafe</span>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-bold text-gray-900 leading-none">{user?.name}</p>
              <p className="text-xs font-black text-indigo-600 mt-1.5 uppercase tracking-[0.2em]">{user?.role} Access</p>
            </div>
            <div className="w-px h-8 bg-gray-200 hidden sm:block"></div>
            <button onClick={handleLogout} className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all" title="Sign out">
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto w-full p-6 md:p-10 space-y-10 relative z-10">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-2">
            <h2 className="text-4xl font-black text-gray-900 tracking-tighter uppercase">System Console</h2>
            <p className="text-gray-500 font-medium text-lg">Archival integrity monitoring & management</p>
          </div>
          <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm p-1.5 rounded-2xl border border-gray-200/60 shadow-sm">
             <div className="px-4 py-2 bg-gray-50/80 rounded-xl flex items-center gap-2">
                <Activity className="w-4 h-4 text-indigo-500" />
                <span className="text-xs font-black text-gray-500 uppercase tracking-[0.2em]">Sync: {stats?.last_sync.split(' ')[1]}</span>
             </div>
             <div className="px-5 py-2 bg-gradient-to-r from-emerald-400 to-emerald-500 rounded-xl flex items-center gap-2 shadow-lg shadow-emerald-200/50">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse shadow-[0_0_8px_rgba(255,255,255,0.8)]"></span>
                <span className="text-xs font-black text-white uppercase tracking-[0.2em]">Live</span>
             </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white/80 backdrop-blur-md p-8 rounded-[2rem] border border-gray-200/60 shadow-sm flex items-center justify-between group hover:border-indigo-200 hover:shadow-xl transition-all duration-300">
            <div className="space-y-2">
              <p className="text-xs font-black text-gray-400 uppercase tracking-[0.2em]">Pending Projects</p>
              <p className="text-5xl font-black text-gray-900 tracking-tighter group-hover:text-indigo-600 transition-colors">{stats?.pending_count}</p>
            </div>
            <div className="w-16 h-16 bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-2xl flex items-center justify-center text-indigo-600 shadow-inner group-hover:scale-110 transition-transform">
              <Zap className="w-8 h-8" />
            </div>
          </div>
          <div className="bg-white/80 backdrop-blur-md p-8 rounded-[2rem] border border-gray-200/60 shadow-sm flex items-center justify-between group hover:border-emerald-200 hover:shadow-xl transition-all duration-300">
            <div className="space-y-2">
              <p className="text-xs font-black text-gray-400 uppercase tracking-[0.2em]">Total Archived</p>
              <p className="text-5xl font-black text-gray-900 tracking-tighter group-hover:text-emerald-600 transition-colors">{stats?.archived_count}</p>
            </div>
            <div className="w-16 h-16 bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-2xl flex items-center justify-center text-emerald-600 shadow-inner group-hover:scale-110 transition-transform">
              <FileCheck className="w-8 h-8" />
            </div>
          </div>
          <div className="bg-white/80 backdrop-blur-md p-8 rounded-[2rem] border border-gray-200/60 shadow-sm flex items-center justify-between group hover:border-indigo-200 hover:shadow-xl transition-all duration-300">
            <div className="space-y-2">
              <p className="text-xs font-black text-gray-400 uppercase tracking-[0.2em]">Auth Protocol</p>
              <p className={`text-2xl font-black tracking-tighter ${stats?.service_account_configured ? 'text-indigo-600' : 'text-red-500'}`}>
                {stats?.service_account_configured ? "SECURED" : "REQUIRED"}
              </p>
            </div>
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform ${stats?.service_account_configured ? 'bg-gradient-to-br from-indigo-50 to-indigo-100 text-indigo-600' : 'bg-gradient-to-br from-red-50 to-red-100 text-red-500'}`}>
              <ShieldCheck className="w-8 h-8" />
            </div>
          </div>
        </div>

        {/* Action Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="bg-white/80 backdrop-blur-md p-10 rounded-[3rem] border border-gray-200/60 shadow-sm hover:shadow-2xl hover:-translate-y-1 transition-all duration-500 group relative overflow-hidden">
            <div className="absolute -right-10 -top-10 opacity-[0.03] group-hover:opacity-[0.05] transition-opacity">
               <LayoutDashboard className="w-64 h-64 rotate-12" />
            </div>
            <div className="w-20 h-20 bg-gradient-to-br from-indigo-500 to-indigo-700 rounded-[1.5rem] flex items-center justify-center text-white mb-8 group-hover:scale-110 transition-transform duration-500 shadow-xl shadow-indigo-200/50">
              <LayoutDashboard className="w-10 h-10" />
            </div>
            <h3 className="text-xl font-black text-gray-900 mb-4 tracking-tighter uppercase">Capstone Archiver</h3>
            <p className="text-gray-500 font-medium mb-10 leading-relaxed text-lg max-w-md">
              Execute archival sequences, validate links, and synchronize local storage with Google Drive.
            </p>
            <button 
              onClick={() => window.location.hash = "registry-dashboard"}
              className="w-full flex items-center justify-center gap-3 py-5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-2xl font-black text-sm uppercase tracking-[0.2em] transition-all shadow-xl shadow-indigo-200 hover:shadow-2xl active:scale-[0.98]"
            >
              Launch Archiver <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>

          <div className="bg-white/80 backdrop-blur-md p-10 rounded-[3rem] border border-gray-200/60 shadow-sm hover:shadow-2xl hover:-translate-y-1 transition-all duration-500 group relative overflow-hidden">
            <div className="absolute -right-10 -top-10 opacity-[0.03] group-hover:opacity-[0.05] transition-opacity">
               <History className="w-64 h-64 -rotate-12" />
            </div>
            <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-[1.5rem] flex items-center justify-center text-white mb-8 group-hover:scale-110 transition-transform duration-500 shadow-xl shadow-purple-200/50">
              <History className="w-10 h-10" />
            </div>
            <h3 className="text-3xl font-black text-gray-900 mb-4 tracking-tighter uppercase">Archival Ledger</h3>
            <p className="text-gray-500 font-medium mb-10 leading-relaxed text-lg max-w-md">
              Access historical records, audit cryptographic signatures, and manage document versioning.
            </p>
            <button 
              onClick={() => window.location.hash = "ledger"}
              className="w-full flex items-center justify-center gap-3 py-5 bg-white border-2 border-indigo-600 text-indigo-600 hover:bg-indigo-50 rounded-2xl font-black text-sm uppercase tracking-[0.2em] transition-all active:scale-[0.98]"
            >
              Access Archival Ledger <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      </main>

      <footer className="mt-auto p-10 border-t border-gray-200/50 bg-white/50 backdrop-blur-md flex flex-col md:flex-row justify-between items-center gap-4 text-xs font-black text-gray-400 uppercase tracking-[0.2em] relative z-10">
        <div className="flex items-center gap-3">
          <Logo size={24} className="opacity-70" />
          DriveSafe Engine v2.0
        </div>
        <div className="flex gap-8">
          <span>RA 10173 Compliant</span>
          <span>Security Verified</span>
        </div>
      </footer>
    </div>
  );
};

export default DashboardPage;
