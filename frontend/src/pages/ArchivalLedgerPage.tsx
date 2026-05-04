import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Folder, ChevronRight, ChevronDown, FileText, Download, Eye, Calendar, 
  Search, Hash, Clock, ArrowLeft, Copy, Check, Trash2, Code, BarChart3, ClipboardCheck, FileSearch, RefreshCw 
} from "lucide-react";
import Logo from "../components/Logo";

interface Version { id: number; version: number; hash: string; timestamp: string; status: string; }
interface ProjectGroup {
  project_id: string; project_title: string; academic_year: string;
  documents: { srs: Version[]; sdd: Version[]; spmp: Version[]; std: Version[]; ri: Version[]; };
}

const ArchivalLedgerPage = () => {
  const [projects, setProjects] = useState<ProjectGroup[]>([]);
  const [years, setYears] = useState<string[]>([]);
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set());
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  useEffect(() => { fetchYears(); }, []);
  useEffect(() => { fetchLedger(); }, [selectedYear]);

  const fetchYears = async () => {
    try {
      const resp = await axios.get(`/api/registry/ledger/tabs`, { withCredentials: true });
      setYears(resp.data);
      if (resp.data.length > 0 && !selectedYear) setSelectedYear(resp.data[0]);
    } catch (err) { console.error(err); }
  };

  const fetchLedger = async () => {
    setLoading(true);
    try {
      const url = selectedYear ? `/api/registry/ledger/grouped?year=${selectedYear}` : `/api/registry/ledger/grouped`;
      const resp = await axios.get(url, { withCredentials: true });
      setProjects(resp.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const toggleProject = (id: string) => {
    const next = new Set(expandedProjects);
    next.has(id) ? next.delete(id) : next.add(id);
    setExpandedProjects(next);
  };

  const toggleDoc = (pKey: string, type: string) => {
    const key = `${pKey}-${type}`;
    const next = new Set(expandedDocs);
    next.has(key) ? next.delete(key) : next.add(key);
    setExpandedDocs(next);
  };

  const copyToClipboard = (hash: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("Delete this archival record?")) return;
    try {
      await axios.delete(`/api/registry/ledger/${id}`, { withCredentials: true });
      fetchLedger();
    } catch (err) { alert("Delete failed"); }
  };

  // Color Coding for Documents
  const getDocStyles = (type: string) => {
    const t = type.toLowerCase();
    if (t === 'srs') return { text: "text-blue-600", bg: "bg-blue-50", border: "border-blue-100", hover: "hover:border-blue-200", icon: <FileText size={18} /> };
    if (t === 'sdd') return { text: "text-purple-600", bg: "bg-purple-50", border: "border-purple-100", hover: "hover:border-purple-200", icon: <Code size={18} /> };
    if (t === 'spmp') return { text: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-100", hover: "hover:border-emerald-200", icon: <BarChart3 size={18} /> };
    if (t === 'std') return { text: "text-amber-600", bg: "bg-amber-50", border: "border-amber-100", hover: "hover:border-amber-200", icon: <ClipboardCheck size={18} /> };
    if (t === 'ri') return { text: "text-rose-600", bg: "bg-rose-50", border: "border-rose-100", hover: "hover:border-rose-200", icon: <FileSearch size={18} /> };
    return { text: "text-gray-600", bg: "bg-gray-50", border: "border-gray-100", hover: "hover:border-gray-200", icon: <FileText size={18} /> };
  };

  const filteredProjects = projects.filter(p => 
    p.project_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.project_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans relative">
      <nav className="bg-white/80 backdrop-blur-xl border-b border-gray-200/60 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => window.location.hash = "dashboard"} className="p-2 text-gray-400 hover:text-indigo-600 transition-colors">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="h-6 w-px bg-gray-200"></div>
            <div className="flex items-center gap-3">
              <Logo size={60} />
              <span className="text-lg font-black text-gray-900 tracking-tight">Audit Log</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] hidden sm:block">Academic Year</span>
            <div className="relative group">
              <select 
                value={selectedYear} 
                onChange={(e) => setSelectedYear(e.target.value)}
                className="appearance-none bg-white border-2 border-gray-100 text-indigo-600 text-sm font-black rounded-xl pl-4 pr-10 py-2 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all cursor-pointer shadow-sm group-hover:border-indigo-200"
              >
                <option value="">All Years</option>
                {years.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-indigo-600 pointer-events-none" />
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto w-full p-6 md:p-10 space-y-8">
        <div className="relative group">
          <Search className="absolute left-6 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-indigo-600 transition-colors" size={22} />
          <input 
            type="text" 
            placeholder="Search archives by project name or ID..."
            className="w-full pl-16 pr-6 py-5 bg-white border-2 border-gray-100 rounded-3xl shadow-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none text-lg font-medium transition-all"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {loading ? (
          <div className="py-32 flex flex-col items-center gap-4">
            <RefreshCw className="w-10 h-10 text-indigo-600 animate-spin" />
            <p className="text-gray-400 font-bold uppercase tracking-widest text-xs">Decrypting Vault...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {filteredProjects.map((project) => {
              const pKey = `${project.project_id}-${project.project_title}`;
              const isExpanded = expandedProjects.has(pKey);

              return (
                <div key={pKey} className={`bg-white rounded-[2rem] border transition-all duration-300 ${isExpanded ? 'border-indigo-200 shadow-2xl shadow-indigo-500/10' : 'border-gray-100 shadow-sm hover:border-gray-300 hover:shadow-md'}`}>
                  <div onClick={() => toggleProject(pKey)} className="p-6 md:p-8 flex items-center justify-between cursor-pointer group">
                    <div className="flex items-center gap-6">
                      <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300 ${isExpanded ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200 scale-105' : 'bg-gray-50 text-gray-400 group-hover:bg-indigo-50 group-hover:text-indigo-600 group-hover:scale-105'}`}>
                        <Folder size={28} fill={isExpanded ? "currentColor" : "none"} />
                      </div>
                      <div>
                        <h3 className="text-xl md:text-2xl font-black text-gray-900 group-hover:text-indigo-600 transition-colors tracking-tight">{project.project_title}</h3>
                        <div className="flex items-center gap-4 mt-2 text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">
                          <span className="bg-gray-50 px-2.5 py-1 rounded-md text-gray-500 border border-gray-200 font-mono tracking-normal">ID: {project.project_id}</span>
                          <span className="flex items-center"><Calendar size={14} className="mr-1.5 opacity-70" /> {project.academic_year}</span>
                        </div>
                      </div>
                    </div>
                    <div className={`p-3 rounded-full transition-all duration-500 ${isExpanded ? 'bg-indigo-50 text-indigo-600 rotate-180' : 'text-gray-300 group-hover:text-gray-600 group-hover:bg-gray-50'}`}>
                      <ChevronDown size={24} />
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="px-6 pb-6 md:px-8 md:pb-8 space-y-4 animate-in slide-in-from-top-4 duration-300">
                      {Object.entries(project.documents).map(([type, versions]) => {
                        if (versions.length === 0) return null;
                        const docKey = `${pKey}-${type}`;
                        const isDocExpanded = expandedDocs.has(docKey);
                        const styles = getDocStyles(type);

                        return (
                          <div key={type} className={`border-2 rounded-3xl overflow-hidden transition-colors ${isDocExpanded ? styles.border : 'border-gray-50 hover:border-gray-100'}`}>
                            <div onClick={() => toggleDoc(pKey, type)} className={`p-5 flex items-center justify-between cursor-pointer transition-all ${isDocExpanded ? styles.bg : 'hover:bg-gray-50'}`}>
                              <div className="flex items-center gap-4">
                                <ChevronRight size={20} className={`text-gray-400 transition-transform duration-300 ${isDocExpanded ? 'rotate-90' : ''}`} />
                                <div className={`p-2 rounded-xl bg-white shadow-sm ${styles.text}`}>
                                    {styles.icon}
                                </div>
                                <span className={`font-black uppercase tracking-widest text-sm ${styles.text}`}>{type}</span>
                                <span className={`ml-2 px-3 py-1 bg-white rounded-full text-[10px] font-black border ${styles.border} ${styles.text} uppercase tracking-widest shadow-sm`}>
                                  {versions.length} Version{versions.length > 1 ? 's' : ''}
                                </span>
                              </div>
                            </div>

                            {isDocExpanded && (
                              <div className="p-5 pt-0 space-y-3 bg-white">
                                {versions.map((v) => (
                                  <div key={v.id} className={`flex flex-col md:flex-row md:items-center justify-between p-5 bg-white rounded-2xl border-2 border-gray-100 transition-all group/v ${styles.hover}`}>
                                    <div className="flex items-center gap-5">
                                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center bg-gray-50 ${styles.text} transition-colors`}>
                                          <Hash size={20} />
                                      </div>
                                      <div>
                                        <div className="text-base font-black text-gray-900">Version {v.version}</div>
                                        <div className="flex items-center gap-4 text-[10px] font-black text-gray-400 uppercase tracking-widest mt-1.5">
                                          <span className="flex items-center"><Clock size={12} className="mr-1.5" /> {v.timestamp}</span>
                                          <button onClick={() => copyToClipboard(v.hash)} className="flex items-center hover:text-indigo-600 transition-colors group/copy">
                                            <span className="font-mono tracking-normal">{v.hash?.substring(0, 12)}...</span>
                                            {copiedHash === v.hash ? <Check size={14} className="ml-2 text-emerald-500" /> : <Copy size={14} className="ml-2 opacity-0 group-hover/copy:opacity-100" />}
                                          </button>
                                        </div>
                                      </div>
                                    </div>
                                    <div className="flex items-center gap-3 mt-6 md:mt-0 self-end">
                                      <button onClick={() => window.open(`/api/registry/download/${v.id}/${type}?preview=1`)} className="px-5 py-2.5 text-xs font-black text-indigo-600 border-2 border-indigo-100 rounded-xl hover:bg-indigo-50 hover:border-indigo-300 transition-all flex items-center gap-2">
                                        <Eye size={16} /> VIEW
                                      </button>
                                      <button onClick={() => window.open(`/api/registry/download/${v.id}/${type}`)} className="px-5 py-2.5 text-xs font-black text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200 flex items-center gap-2 hover:-translate-y-0.5">
                                        <Download size={16} /> DOWNLOAD
                                      </button>
                                      <button onClick={() => handleDelete(v.id)} className="p-3 text-gray-300 hover:text-red-600 hover:bg-red-50 rounded-xl transition-colors">
                                        <Trash2 size={18}/>
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
      
      <footer className="mt-auto p-12 text-center text-[10px] font-black text-gray-400 uppercase tracking-[0.3em] bg-white/50 backdrop-blur-md border-t border-gray-200/50">
        DriveSafe Vault &copy; 2026 &bull; Secure Audit Log
      </footer>
    </div>
  );
};

export default ArchivalLedgerPage;
