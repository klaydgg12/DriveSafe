import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { 
  Folder, ChevronRight, ChevronDown, FileText, Download, Eye, 
  Search, Hash, Clock, ArrowLeft, Copy, Check, Trash2, Code, BarChart3, 
  ClipboardCheck, FileSearch, RefreshCw, AlertCircle, BookOpen, Filter,
  Layers,
  ArrowRight,
  ShieldCheck
} from "lucide-react";
import Logo from "../components/Logo";

interface Version { 
  id: number; 
  version: number; 
  hash: string; 
  timestamp: string; 
  status: 'Archived' | 'Failed' | 'Pending'; 
}

interface ProjectGroup {
  project_id: string; 
  project_title: string; 
  academic_year: string;
  workbook_name?: string;
  status: 'Archived' | 'Failed' | 'Pending';
  error_message?: string;
  documents: { 
    srs: Version[]; 
    sdd: Version[]; 
    spmp: Version[]; 
    std: Version[]; 
    ri: Version[]; 
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
  const projectsPerPage = 10; // Adjusted for card-based layout

  useEffect(() => { fetchWorkbooks(); }, []);
  useEffect(() => { fetchYears(selectedWorkbook); }, [selectedWorkbook]);
  useEffect(() => { fetchLedger(); }, [selectedYear, selectedWorkbook, statusFilter]);

  const fetchWorkbooks = async () => {
    try {
      const resp = await axios.get(`/api/registry/ledger/workbooks`, { withCredentials: true });
      setWorkbooks(resp.data);
      // Don't auto-reset selectedWorkbook here to avoid selection loss
    } catch (err) { console.error("Failed to fetch workbooks:", err); }
  };

  const fetchYears = async (workbook: string) => {
    try {
      // Critical fix for deployed: Use workbook name if selected
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
    if (!window.confirm(`Are you sure you want to PERMANENTLY REMOVE all ${Object.values(project.documents).flat().length} archival records for "${project.project_title}"?`)) return;
    
    setLoading(true);
    try {
      const allIds = Array.from(new Set(Object.values(project.documents).flat().map(v => v.id)));
      await Promise.all(allIds.map(id => axios.delete(`/api/registry/ledger/${id}`, { withCredentials: true })));
      fetchLedger();
    } catch (err) { alert("Bulk delete failed. Some records might remain."); }
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
    if (t === 'ri') return { text: "text-rose-600", bg: "bg-rose-50", border: "border-rose-100", icon: <FileSearch size={16} /> };
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

  // Pagination Logic
  const totalPages = Math.ceil(filteredAndSortedProjects.length / projectsPerPage);
  const paginatedProjects = useMemo(() => {
    const startIndex = (currentPage - 1) * projectsPerPage;
    return filteredAndSortedProjects.slice(startIndex, startIndex + projectsPerPage);
  }, [filteredAndSortedProjects, currentPage]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans transition-colors duration-300 overflow-x-hidden">
      {/* Header */}
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
              <div className="flex items-center gap-1.5 px-2 border-r border-slate-200 shrink-0">
                <BookOpen size={14} className="text-slate-400" />
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest hidden lg:inline">Workbook</span>
              </div>
              <div className="relative shrink-0">
                <select 
                  value={selectedWorkbook} 
                  onChange={(e) => setSelectedWorkbook(e.target.value)}
                  className="appearance-none bg-white border border-transparent text-slate-900 text-[11px] font-black rounded-lg px-2 py-1.5 pr-8 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all cursor-pointer shadow-sm w-[120px] md:w-[180px] truncate"
                >
                  <option value="">All Workbooks</option>
                  {workbooks.map(w => <option key={w} value={w}>{w}</option>)}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
              </div>

              <div className="w-px h-4 bg-slate-200 mx-1"></div>

              <div className="flex items-center gap-1.5 px-2 border-r border-slate-200 shrink-0">
                <Filter size={14} className="text-slate-400" />
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest hidden lg:inline">Sheet</span>
              </div>
              <div className="relative shrink-0">
                <select 
                  value={selectedYear} 
                  onChange={(e) => setSelectedYear(e.target.value)}
                  className="appearance-none bg-white border border-transparent text-slate-900 text-[11px] font-black rounded-lg px-2 py-1.5 pr-8 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all cursor-pointer shadow-sm w-[80px] md:w-[120px] truncate"
                >
                  <option value="">All Sheets</option>
                  {years.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
              </div>
            </div>
            
            <button 
              onClick={fetchLedger}
              className="p-2.5 bg-white border border-slate-200 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all shadow-sm shrink-0"
              title="Refresh Ledger"
            >
              <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-[1600px] mx-auto w-full p-6 md:p-12 flex-1 space-y-8">
        {/* Controls Bar */}
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative group flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-600 transition-colors" size={18} />
            <input 
              type="text" 
              placeholder="Search archives by project name or ID..."
              className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-[1.25rem] shadow-sm focus:ring-4 focus:ring-indigo-500/5 focus:border-indigo-500 outline-none text-sm font-medium transition-all"
              value={searchQuery}
              onChange={(e) => {setSearchQuery(e.target.value); setCurrentPage(1);}}
            />
          </div>
          
          <div className="flex items-center gap-1 bg-white p-1 rounded-2xl border border-slate-100 shadow-sm shrink-0 overflow-x-auto no-scrollbar">
            {(['All', 'Archived', 'Failed'] as string[]).map(status => (
                <button
                    key={status}
                    onClick={() => {setStatusFilter(status); setCurrentPage(1);}}
                    className={`px-4 py-2 text-[10px] font-black rounded-xl transition-all whitespace-nowrap ${statusFilter === status ? 'bg-teal-600 text-white shadow-md shadow-teal-100' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'}`}
                >
                    {status.toUpperCase()}
                </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="py-32 flex flex-col items-center gap-4">
            <RefreshCw className="w-12 h-12 text-teal-600 animate-spin" />
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Accessing Binary Vault...</p>
          </div>
        ) : paginatedProjects.length === 0 ? (
          <div className="py-32 text-center">
            <div className="w-24 h-24 bg-slate-50 rounded-[2.5rem] flex items-center justify-center mx-auto mb-6 text-slate-200 border border-slate-100 shadow-inner">
              <FileSearch size={40} />
            </div>
            <h3 className="text-slate-900 font-black text-xl tracking-tight">No records found</h3>
            <p className="text-slate-400 text-sm font-medium mt-1">Try clearing your filters or search query.</p>
          </div>
        ) : (
          <div className="space-y-6 pb-20">
            <div className="grid grid-cols-1 gap-4">
              {paginatedProjects.map((project) => {
                const pKey = `${project.project_id}-${project.project_title}`;
                const isExpanded = expandedProjects.has(pKey);
                const totalVersions = Object.values(project.documents).flat().length;

                return (
                  <div key={pKey} className={`bg-white border transition-all duration-300 ${isExpanded ? 'border-indigo-200 shadow-xl ring-1 ring-indigo-50/50 rounded-[2.5rem]' : 'border-slate-100 hover:border-indigo-200 hover:shadow-md rounded-[2rem]'}`}>
                    {/* Project Header */}
                    <div 
                      onClick={() => toggleProject(pKey)} 
                      className="p-5 flex items-center justify-between cursor-pointer group select-none"
                    >
                      <div className="flex items-center gap-4 min-w-0">
                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-500 shrink-0 ${isExpanded ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-100' : 'bg-slate-50 text-slate-400 group-hover:bg-indigo-50 group-hover:text-indigo-600'}`}>
                          <Folder size={22} fill={isExpanded ? "currentColor" : "none"} />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                             <h3 className="text-sm font-black text-slate-900 truncate group-hover:text-indigo-600 transition-colors tracking-tight">{project.project_title}</h3>
                             <span className={`px-2 py-0.5 rounded-full text-[9px] font-black border uppercase tracking-widest ${getStatusStyles(project.status)}`}>
                               {project.status}
                             </span>
                          </div>
                          <div className="flex items-center gap-4 mt-1 text-[10px] font-black text-slate-400 uppercase tracking-widest flex-wrap">
                            <span className="font-mono text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded-md border border-slate-100 shrink-0">#{project.project_id}</span>
                            <span className="flex items-center text-teal-600/70 shrink-0"><Layers size={11} className="mr-1.5" /> {totalVersions} ARCHIVES</span>
                            <span className="flex items-center opacity-60 truncate"><BookOpen size={11} className="mr-1.5 shrink-0" /> {project.academic_year}</span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4 shrink-0">
                        <button 
                          onClick={(e) => { e.stopPropagation(); handleDeleteProject(project); }}
                          className="p-2 text-slate-300 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all opacity-0 group-hover:opacity-100 hidden sm:block"
                          title="Delete Entire Project History"
                        >
                          <Trash2 size={18} />
                        </button>
                        <div className={`p-2 rounded-xl transition-all duration-300 ${isExpanded ? 'bg-indigo-50 text-indigo-600 rotate-180' : 'text-slate-300 group-hover:text-slate-600'}`}>
                          <ChevronDown size={20} />
                        </div>
                      </div>
                    </div>

                    {/* Expanded Content */}
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
                                                <span className="truncate max-w-[80px] sm:max-w-[120px]">{v.hash?.substring(0, 12)}...</span>
                                                {copiedHash === v.hash ? <Check size={10} className="ml-1.5 text-emerald-500" /> : <Copy size={10} className="ml-1.5 opacity-0 group-hover/copy:opacity-100" />}
                                              </button>
                                            </div>
                                          </div>
                                        </div>
                                        <div className="flex flex-col gap-2 shrink-0">
                                          <button 
                                            onClick={(e) => { e.stopPropagation(); window.open(`/api/registry/download/${v.id}/${type}?preview=1`); }}
                                            className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-white rounded-lg border border-transparent hover:border-indigo-100 transition-all shadow-sm"
                                            title="View PDF"
                                          >
                                            <Eye size={16} />
                                          </button>
                                          <button 
                                            onClick={(e) => { e.stopPropagation(); window.open(`/api/registry/download/${v.id}/${type}`); }}
                                            className="p-2 text-slate-400 hover:text-teal-600 hover:bg-white rounded-lg border border-transparent hover:border-teal-100 transition-all shadow-sm"
                                            title="Download"
                                          >
                                            <Download size={16} />
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
                        
                        {/* Integrity Footer */}
                        <div className="flex items-center justify-between px-4 py-3 bg-slate-50/50 rounded-2xl text-[10px] font-black text-slate-300 uppercase tracking-[0.2em] mt-4 border border-slate-100">
                           <div className="flex items-center gap-2">
                             <ShieldCheck size={12} className="text-emerald-400" />
                             <span className="hidden sm:inline">Cryptographic Integrity Secured (SHA-256)</span>
                             <span className="sm:hidden">SHA-256 SECURED</span>
                           </div>
                           <div className="flex items-center gap-4">
                             <span>RECORDS: {totalVersions}</span>
                             <ArrowRight size={12} />
                           </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Pagination UI */}
            <div className="bg-white px-8 py-5 border border-slate-200 rounded-[2rem] flex flex-col sm:flex-row items-center justify-between gap-4 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] shadow-sm mt-8">
                <div className="flex items-center gap-6">
                    <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-slate-200"></div> TOTAL RECORDS: {filteredAndSortedProjects.length}</span>
                </div>
                
                <div className="flex items-center gap-2">
                    <button 
                        onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                        disabled={currentPage === 1}
                        className="p-2.5 bg-white border border-slate-200 rounded-xl hover:bg-indigo-50 hover:text-indigo-600 transition-all disabled:opacity-30 shadow-sm"
                    >
                        <ChevronRight className="w-4 h-4 rotate-180" />
                    </button>
                    <div className="px-5 py-2 bg-white border border-slate-200 rounded-xl text-slate-900 shadow-sm flex items-center gap-2">
                        <span className="text-slate-300">PAGE</span> <span className="text-indigo-600">{currentPage}</span> <span className="text-slate-300">/</span> {totalPages || 1}
                    </div>
                    <button 
                        onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                        disabled={currentPage >= totalPages}
                        className="p-2.5 bg-white border border-slate-200 rounded-xl hover:bg-indigo-50 hover:text-indigo-600 transition-all disabled:opacity-30 shadow-sm"
                    >
                        <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            </div>
          </div>
        )}
      </main>
      
      <footer className="mt-auto p-10 border-t border-gray-200/50 bg-white/50 backdrop-blur-md flex flex-col md:flex-row justify-between items-center gap-4 text-[10px] font-black text-gray-400 uppercase tracking-[0.3em] relative z-10">
        <div className="flex items-center gap-3">
          <Logo size={24} className="opacity-70" />
          DriveSafe Vault &bull; 2026
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
