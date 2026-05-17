import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { 
  Folder, ChevronRight, ChevronDown, FileText, Download, Eye, 
  Search, Hash, Clock, ArrowLeft, Copy, Check, Trash2, Code, BarChart3, 
  ClipboardCheck, RefreshCw, AlertCircle, BookOpen, Filter,
  Layers,
  ArrowRight,
  ShieldCheck,
  Monitor,
  CheckCircle
} from "lucide-react";
import Logo from "../components/Logo";

interface Version { 
  id: number; 
  version: number; 
  hash: string; 
  timestamp: string;
  status: string;
}

interface ProjectGroup {
  project_id: string; 
  project_title: string; 
  academic_year: string;
  workbook_name?: string;
  status: 'Archived' | 'Failed' | 'Pending';
  error_message?: string;
  db_ids: number[];
  documents: { 
    srs: Version[]; 
    sdd: Version[]; 
    spmp: Version[]; 
    std: Version[]; 
    ri: Version[]; 
    research_paper: Version[];
    usability_test: Version[];
    presentation: Version[];
    source_code: Version[];
    database: Version[];
    readme: Version[];
  };
}

const ArchivalLedgerPage = () => {
  const [projects, setProjects] = useState<ProjectGroup[]>([]);
  const [workbooks, setWorkbooks] = useState<string[]>([]);
  const [selectedWorkbook, setSelectedWorkbook] = useState<string>("");
  const [years, setYears] = useState<string[]>([]);
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("All");
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set());
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Pagination State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const projectsPerPage = 10;

  useEffect(() => { fetchWorkbooks(); }, []);
  useEffect(() => { fetchYears(selectedWorkbook); }, [selectedWorkbook]);
  useEffect(() => { fetchLedger(); }, [selectedYear, selectedWorkbook, statusFilter]);

  const fetchWorkbooks = async () => {
    try {
      const resp = await axios.get(`/api/registry/ledger/workbooks`, { withCredentials: true });
      setWorkbooks(resp.data);
    } catch (err) { console.error("Failed to fetch workbooks:", err); }
  };

  const fetchYears = async (workbook: string) => {
    try {
      const url = workbook ? `/api/registry/ledger/tabs?workbook=${encodeURIComponent(workbook)}` : `/api/registry/ledger/tabs`;
      const resp = await axios.get(url, { withCredentials: true });
      setYears(resp.data);
      setSelectedYear(""); 
    } catch (err) { console.error("Failed to fetch years:", err); }
  };

  const fetchLedger = async () => {
    setLoading(true);
    try {
      let params = new URLSearchParams();
      if (selectedYear) params.append('year', selectedYear);
      if (selectedWorkbook) params.append('workbook', selectedWorkbook);
      
      const resp = await axios.get(`/api/registry/ledger/grouped?${params.toString()}`, { withCredentials: true });
      
      const projectsWithStatus = resp.data.map((p: ProjectGroup) => {
        const allVersions = Object.values(p.documents).flat();
        let status: 'Archived' | 'Failed' | 'Pending' = 'Archived';
        if (allVersions.some(v => v.status === 'Failed')) status = 'Failed';
        else if (allVersions.some(v => v.status === 'Pending')) status = 'Pending';
        return { ...p, status };
      });

      setProjects(projectsWithStatus);
      setCurrentPage(1);
    } catch (err) { console.error("Failed to fetch ledger:", err); }
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
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleDeleteProject = async (project: ProjectGroup) => {
    const totalCount = project.db_ids?.length || 0;
    if (!window.confirm(`Are you sure you want to PERMANENTLY REMOVE all ${totalCount} archival records for "${project.project_title}"?`)) return;
    
    setLoading(true);
    try {
      const allIds = project.db_ids || [];
      if (allIds.length === 0) {
        alert("No database records found for this project.");
        return;
      }
      await Promise.all(allIds.map(id => axios.delete(`/api/registry/ledger/${id}`, { withCredentials: true })));
      fetchLedger();
    } catch (err) { 
      console.error("Delete failed:", err);
      alert("Bulk delete failed. Some records might remain."); 
    }
    finally { setLoading(false); }
  };

  const getStatusStyles = (status: string) => {
    switch (status) {
      case 'Archived': return "bg-emerald-50 text-emerald-700 border-emerald-100";
      case 'Failed': return "bg-rose-50 text-rose-700 border-rose-100";
      case 'Pending': return "bg-amber-50 text-amber-700 border-amber-100";
      default: return "bg-gray-50 text-gray-700 border-gray-100";
    }
  };

  const getDocStyles = (type: string) => {
    const t = type.toLowerCase();
    if (t === 'srs') return { text: "text-blue-600", bg: "bg-blue-50", border: "border-blue-100", icon: <FileText size={16} /> };
    if (t === 'sdd') return { text: "text-purple-600", bg: "bg-purple-50", border: "border-purple-100", icon: <Code size={16} /> };
    if (t === 'spmp') return { text: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-100", icon: <BarChart3 size={16} /> };
    if (t === 'std') return { text: "text-amber-600", bg: "bg-amber-50", border: "border-amber-100", icon: <ClipboardCheck size={16} /> };
    if (t === 'ri') return { text: "text-rose-600", bg: "bg-rose-50", border: "border-rose-100", icon: <Search size={16} /> };
    if (t === 'research_paper') return { text: "text-indigo-600", bg: "bg-indigo-50", border: "border-indigo-100", icon: <BookOpen size={16} /> };
    if (t === 'usability_test') return { text: "text-teal-600", bg: "bg-teal-50", border: "border-teal-100", icon: <CheckCircle size={16} /> };
    if (t === 'presentation') return { text: "text-orange-600", bg: "bg-orange-50", border: "border-orange-100", icon: <Monitor size={16} /> };
    if (t === 'source_code') return { text: "text-orange-600", bg: "bg-orange-50", border: "border-orange-100", icon: <Code size={16} /> };
    if (t === 'database') return { text: "text-cyan-600", bg: "bg-cyan-50", border: "border-cyan-100", icon: <Layers size={16} /> };
    if (t === 'readme') return { text: "text-slate-600", bg: "bg-slate-50", border: "border-slate-100", icon: <FileText size={16} /> };
    return { text: "text-gray-600", bg: "bg-gray-50", border: "border-gray-100", icon: <FileText size={16} /> };
  };

  const filteredAndSortedProjects = useMemo(() => {
    return projects
      .filter(p => {
        const matchesSearch = p.project_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                              p.project_id.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesStatus = statusFilter === 'All' || p.status === statusFilter;
        return matchesSearch && matchesStatus;
      })
      .sort((a, b) => {
        return a.project_id.localeCompare(b.project_id, undefined, { numeric: true, sensitivity: 'base' });
      });
  }, [projects, searchQuery, statusFilter]);

  const totalPages = Math.ceil(filteredAndSortedProjects.length / projectsPerPage);
  const paginatedProjects = useMemo(() => {
    const startIndex = (currentPage - 1) * projectsPerPage;
    return filteredAndSortedProjects.slice(startIndex, startIndex + projectsPerPage);
  }, [filteredAndSortedProjects, currentPage]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans transition-colors duration-300 overflow-x-hidden">
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-50 transition-all shadow-sm">
        <div className="max-w-[1600px] mx-auto px-8 md:px-12 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 shrink-0">
            <button onClick={() => window.location.hash = "dashboard"} className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-slate-50 rounded-xl transition-all">
              <ArrowLeft size={20} />
            </button>
            <div className="h-6 w-px bg-slate-100 mx-1 hidden sm:block"></div>
            <Logo size={40} />
            <h1 className="text-xl font-black text-slate-900 tracking-tight ml-1 hidden md:block">Archival Ledger</h1>
          </div>
          
          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar py-2">
            <div className="flex items-center gap-2 bg-slate-50 p-1 rounded-xl border border-slate-200 shrink-0">
              <div className="flex items-center gap-1.5 px-3 border-r border-slate-200 shrink-0">
                <Folder size={14} className="text-slate-400" />
                <span className="text-[10px] font-black text-slate-400 tracking-widest uppercase whitespace-nowrap">Workbook</span>
              </div>
              <select 
                value={selectedWorkbook} 
                onChange={(e) => setSelectedWorkbook(e.target.value)}
                className="bg-transparent border-none text-[11px] font-black text-slate-900 focus:ring-0 cursor-pointer max-w-[150px] truncate"
              >
                <option value="">All Workbooks</option>
                {workbooks.map(w => <option key={w} value={w}>{w}</option>)}
              </select>
            </div>

            <div className="flex items-center gap-2 bg-slate-50 p-1 rounded-xl border border-slate-200 shrink-0">
              <div className="flex items-center gap-1.5 px-3 border-r border-slate-200 shrink-0">
                <Filter size={14} className="text-slate-400" />
                <span className="text-[10px] font-black text-slate-400 tracking-widest uppercase whitespace-nowrap">Sheet</span>
              </div>
              <select 
                value={selectedYear} 
                onChange={(e) => setSelectedYear(e.target.value)}
                className="bg-transparent border-none text-[11px] font-black text-slate-900 focus:ring-0 cursor-pointer"
              >
                <option value="">All Sheets</option>
                {years.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-[1600px] mx-auto w-full p-8 md:p-12 space-y-8">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="relative w-full md:w-96 group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-600 transition-colors" size={18} />
            <input 
              type="text" 
              placeholder="Search project code or title..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-white border border-slate-200 rounded-[1.25rem] focus:ring-4 focus:ring-indigo-500/5 focus:border-indigo-500 outline-none text-sm font-medium transition-all shadow-sm" 
            />
          </div>

          <div className="flex items-center gap-1 bg-white p-1 rounded-2xl border border-slate-200 shadow-sm overflow-x-auto no-scrollbar shrink-0">
            {['All', 'Archived', 'Pending', 'Failed'].map((f) => (
              <button
                key={f}
                onClick={() => setStatusFilter(f)}
                className={`px-5 py-2 text-[10px] font-black rounded-xl transition-all uppercase tracking-widest ${statusFilter === f ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-100' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'}`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-32 gap-4">
              <RefreshCw className="w-12 h-12 text-indigo-600 animate-spin" />
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Synchronizing Vault...</p>
            </div>
          ) : paginatedProjects.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-32 gap-4 bg-white rounded-[3rem] border border-slate-100 shadow-inner">
              <div className="w-20 h-20 bg-slate-50 rounded-[2rem] flex items-center justify-center text-slate-200 border border-slate-100">
                <Folder size={40} />
              </div>
              <div className="text-center space-y-1">
                <p className="text-slate-900 font-black text-xl tracking-tight">Vault segment is empty</p>
                <p className="text-slate-400 text-sm font-medium italic">No archival records match your current filter.</p>
              </div>
            </div>
          ) : (
            paginatedProjects.map((project) => {
              const pKey = `${project.project_id}-${project.project_title}`;
              const isExpanded = expandedProjects.has(pKey);
              
              return (
                <div key={pKey} className="bg-white rounded-[2.5rem] border border-slate-200 shadow-sm overflow-hidden transition-all duration-300 hover:shadow-xl hover:shadow-slate-200/50 group">
                  <div 
                    onClick={() => toggleProject(pKey)}
                    className="p-6 md:p-8 cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-6"
                  >
                    <div className="flex items-center gap-6">
                      <div className={`w-16 h-16 rounded-[2rem] flex items-center justify-center shrink-0 border transition-all duration-300 ${isExpanded ? 'bg-indigo-600 border-indigo-600 text-white shadow-xl shadow-indigo-100 scale-110' : 'bg-slate-50 border-slate-100 text-slate-400 group-hover:bg-indigo-50 group-hover:border-indigo-100 group-hover:text-indigo-600'}`}>
                        <ShieldCheck size={28} />
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-3">
                          <span className="text-[10px] font-mono font-black px-2 py-0.5 bg-slate-100 text-slate-500 rounded-lg border border-slate-200 uppercase tracking-tighter">{project.project_id}</span>
                          <span className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border ${getStatusStyles(project.status)}`}>{project.status}</span>
                        </div>
                        <h3 className="text-xl font-black text-slate-900 tracking-tight group-hover:text-indigo-600 transition-colors">{project.project_title}</h3>
                        <div className="flex items-center gap-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                          <div className="flex items-center gap-1.5"><Folder size={12} /> {project.workbook_name}</div>
                          <div className="flex items-center gap-1.5"><Filter size={12} /> {project.academic_year}</div>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <div className="flex -space-x-3 overflow-hidden">
                        {Object.entries(project.documents).map(([type, versions]) => {
                          if (versions.length === 0) return null;
                          return (
                            <div key={type} className={`w-8 h-8 rounded-xl border-2 border-white flex items-center justify-center shadow-sm ${getDocStyles(type).bg} ${getDocStyles(type).text}`} title={`${type.toUpperCase()}: ${versions.length} Revisions`}>
                               {getDocStyles(type).icon}
                            </div>
                          );
                        })}
                      </div>
                      <div className="h-8 w-px bg-slate-100 mx-2"></div>
                      <div className="flex items-center gap-2">
                        <button 
                          onClick={(e) => { e.stopPropagation(); handleDeleteProject(project); }}
                          className="p-3 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-2xl transition-all border border-transparent hover:border-rose-100"
                          title="Delete Project Records"
                        >
                          <Trash2 size={18} />
                        </button>
                        <div className={`p-3 rounded-2xl border transition-all duration-300 ${isExpanded ? 'bg-indigo-600 border-indigo-600 text-white rotate-180' : 'bg-slate-50 border-slate-100 text-slate-400'}`}>
                          <ChevronDown size={20} />
                        </div>
                      </div>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="p-6 pt-2 space-y-4 animate-in slide-in-from-top-4 duration-300">
                      {project.error_message && (
                        <div className="p-4 bg-rose-50 border border-rose-100 rounded-2xl flex items-start gap-4">
                          <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center text-rose-600 shadow-sm shrink-0">
                            <AlertCircle size={20} />
                          </div>
                          <div className="space-y-1">
                            <p className="text-[10px] font-black text-rose-700 uppercase tracking-widest">Protocol Execution Error</p>
                            <p className="text-xs text-rose-600 font-medium leading-relaxed">{project.error_message}</p>
                          </div>
                        </div>
                      )}
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Object.entries(project.documents).map(([type, versions]) => {
                          if (versions.length === 0) return null;
                          const docKey = `${pKey}-${type}`;
                          const isDocExpanded = expandedDocs.has(docKey);
                          const styles = getDocStyles(type);

                          return (
                            <div key={type} className={`border rounded-[1.5rem] overflow-hidden transition-all duration-300 flex flex-col ${isDocExpanded ? 'border-indigo-100 shadow-md ring-4 ring-indigo-500/5' : 'border-slate-100 bg-slate-50/30'}`}>
                              <div 
                                onClick={(e) => { e.stopPropagation(); toggleDoc(pKey, type); }} 
                                className={`p-4 flex items-center justify-between cursor-pointer transition-all ${isDocExpanded ? styles.bg : 'hover:bg-slate-50'}`}
                              >
                                <div className="flex items-center gap-3">
                                  <div className={`p-2 rounded-xl bg-white border border-slate-100 shadow-sm ${styles.text}`}>
                                    {styles.icon}
                                  </div>
                                  <div className="flex flex-col">
                                    <span className={`text-[11px] font-black uppercase tracking-widest ${styles.text}`}>{type}</span>
                                    <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">
                                      {versions.length} REVISIONS
                                    </span>
                                  </div>
                                </div>
                                <ChevronRight size={14} className={`text-slate-400 transition-transform duration-300 ${isDocExpanded ? 'rotate-90' : ''}`} />
                              </div>

                              {isDocExpanded && (
                                <div className="bg-white border-t border-slate-50 divide-y divide-slate-50 max-h-[300px] overflow-y-auto custom-scrollbar">
                                  {versions.map((v) => (
                                    <div key={v.id} className="p-4 flex items-center justify-between group/v hover:bg-slate-50/50 transition-colors">
                                      <div className="flex items-center gap-4 min-w-0">
                                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center bg-slate-50 ${styles.text} border border-slate-100 group-hover/v:bg-white shadow-inner`}>
                                          <span className="text-[10px] font-black">v{v.version}</span>
                                        </div>
                                        <div className="min-w-0">
                                          <div className="flex items-center gap-2">
                                             <div className="text-[11px] font-black text-slate-800 uppercase tracking-tight">Revision {v.version}.0</div>
                                             {v.version === Math.max(...versions.map(ev => ev.version)) && (
                                               <span className="text-[8px] font-black px-1.5 py-0.5 bg-emerald-50 text-emerald-600 rounded-md border border-emerald-100">LATEST</span>
                                             )}
                                          </div>
                                          <div className="flex flex-col gap-1 mt-1">
                                            <div className="flex items-center text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                              <Clock size={10} className="mr-1.5" /> {v.timestamp.split(' ')[0]}
                                            </div>
                                            <button 
                                              onClick={(e) => { e.stopPropagation(); copyToClipboard(v.hash); }} 
                                              className="flex items-center text-[10px] hover:text-indigo-600 transition-colors group/copy font-mono tracking-normal"
                                            >
                                              <Hash size={10} className="mr-1.5" />
                                              <span className="truncate max-w-[80px]">{v.hash.substring(0, 12)}...</span>
                                              {copiedHash === v.hash ? <Check size={10} className="ml-1 text-emerald-500" /> : <Copy size={10} className="ml-1 opacity-0 group-hover/copy:opacity-100" />}
                                            </button>
                                          </div>
                                        </div>
                                      </div>

                                      <div className="flex items-center gap-1.5">
                                        <a 
                                          href={`/api/registry/download/${v.id}/${type}?preview=1`} 
                                          target="_blank" 
                                          rel="noreferrer"
                                          className="p-2.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all border border-transparent hover:border-indigo-100 shadow-sm"
                                          title="Interactive Preview"
                                        >
                                          <Eye size={18} />
                                        </a>
                                        <a 
                                          href={`/api/registry/download/${v.id}/${type}`} 
                                          download
                                          className="p-2.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all border border-transparent hover:border-indigo-100 shadow-sm"
                                          title="Download PDF Archive"
                                        >
                                          <Download size={18} />
                                        </a>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Pagination Controls */}
        {!loading && projects.length > projectsPerPage && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6 px-12 py-8 bg-white rounded-[3rem] border border-slate-200 shadow-sm text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
            <div className="flex items-center gap-6 order-2 sm:order-1">
              <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-slate-200"></div> TOTAL: {filteredAndSortedProjects.length}</span>
              <span className="flex items-center gap-2 text-indigo-600"><div className="w-1.5 h-1.5 rounded-full bg-indigo-600"></div> PAGE: {currentPage} / {totalPages}</span>
            </div>
            
            <div className="flex items-center gap-2 order-1 sm:order-2">
              <button 
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="p-3 bg-white border border-slate-200 rounded-2xl hover:bg-indigo-50 hover:text-indigo-600 transition-all disabled:opacity-30 shadow-sm"
              >
                <ArrowLeft size={16} />
              </button>
              <div className="px-6 py-2 bg-indigo-50 border border-indigo-100 rounded-2xl text-indigo-600 shadow-inner">
                {currentPage}
              </div>
              <button 
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage >= totalPages}
                className="p-3 bg-white border border-slate-200 rounded-2xl hover:bg-indigo-50 hover:text-indigo-600 transition-all disabled:opacity-30 shadow-sm"
              >
                <ArrowRight size={16} />
              </button>
            </div>

            <div className="hidden lg:flex items-center gap-6 order-3">
              <div className="flex items-center gap-2"><ShieldCheck size={14} className="text-emerald-500" /> SECURE</div>
              <div className="flex items-center gap-2"><Clock size={14} className="text-indigo-500" /> SYNCED</div>
            </div>
          </div>
        )}
      </main>

      <footer className="mt-auto py-12 px-12 border-t border-slate-200 flex flex-col md:flex-row items-center justify-between gap-8 text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">
        <div className="flex items-center gap-4">
          <Logo size={24} grayscale />
          <span>DriveSafe Vault Protocol v2.5.0</span>
        </div>
        <div>
          &copy; 2026 CCS Archival Division
        </div>
        <div className="flex gap-8">
          <span>Self-Sufficient Archive</span>
          <span>CIT-U CCS Protocol</span>
        </div>
      </footer>
    </div>
  );
};

export default ArchivalLedgerPage;
