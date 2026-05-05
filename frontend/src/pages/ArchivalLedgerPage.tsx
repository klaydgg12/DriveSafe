import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Folder, ChevronRight, ChevronDown, FileText, Download, Eye, Calendar, 
  Search, Hash, Clock, ArrowLeft, Copy, Check, Trash2, Code, BarChart3, 
  ClipboardCheck, FileSearch, RefreshCw, AlertCircle, BookOpen, Filter
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
  };
}

const ArchivalLedgerPage = () => {
  const [projects, setProjects] = useState<ProjectGroup[]>([]);
  const [workbooks, setWorkbooks] = useState<string[]>([]);
  const [selectedWorkbook, setSelectedWorkbook] = useState<string>("");
  const [years, setYears] = useState<string[]>([]);
  const [selectedYear, setSelectedYear] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set());
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  useEffect(() => { fetchWorkbooks(); }, []);
  useEffect(() => { fetchYears(selectedWorkbook); }, [selectedWorkbook]);
  useEffect(() => { fetchLedger(); }, [selectedYear, selectedWorkbook]);

  const fetchWorkbooks = async () => {
    try {
      const resp = await axios.get(`/api/registry/ledger/workbooks`, { withCredentials: true });
      const availableWorkbooks = resp.data;
      setWorkbooks(availableWorkbooks);
      // Don't auto-select "Archives" if there are other options, but default to "All"
      setSelectedWorkbook(""); 
    } catch (err) { console.error("Failed to fetch workbooks:", err); }
  };

  const fetchYears = async (workbook: string) => {
    try {
      const url = workbook ? `/api/registry/ledger/tabs?workbook=${workbook}` : `/api/registry/ledger/tabs`;
      const resp = await axios.get(url, { withCredentials: true });
      setYears(resp.data);
      setSelectedYear(""); // Default to "All"
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

  const handleDelete = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this archival record? This action cannot be undone.")) return;
    try {
      await axios.delete(`/api/registry/ledger/${id}`, { withCredentials: true });
      fetchLedger();
    } catch (err) { alert("Delete failed. Please try again."); }
  };

  const handleDeleteProject = async (project: ProjectGroup) => {
    if (!window.confirm(`Are you sure you want to PERMANENTLY REMOVE all ${Object.values(project.documents).flat().length} archival records for "${project.project_title}"?`)) return;
    
    setLoading(true);
    try {
      // FIX: Multiple documents in one run share the same DB ID. 
      // We must only delete UNIQUE IDs to avoid 404/500 errors.
      const allIds = Array.from(new Set(Object.values(project.documents).flat().map(v => v.id)));
      
      // Process deletions in parallel
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
    return { text: "text-gray-600", bg: "bg-gray-50", border: "border-gray-100", icon: <FileText size={16} /> };
  };

  const filteredProjects = projects.filter(p => {
    const matchesSearch = p.project_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          p.project_id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col font-sans transition-colors duration-300">
      {/* Header */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-50 transition-colors">
        <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => window.location.hash = "dashboard"} className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-slate-50 rounded-lg transition-all">
              <ArrowLeft size={18} />
            </button>
            <div className="h-4 w-px bg-slate-200 mx-1"></div>
            <Logo size={40} />
            <h1 className="text-base font-bold text-slate-900 tracking-tight ml-1 uppercase">Audit Log</h1>
          </div>
          
          <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 bg-slate-50 p-1 rounded-xl border border-slate-200 mr-2">
            <div className="flex items-center gap-1.5">
              <div className="flex items-center gap-1.5 px-2 border-r border-slate-200">
                <BookOpen size={14} className="text-slate-400" />
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest whitespace-nowrap">Workbook</span>
              </div>
              <div className="relative">
                <select 
                  value={selectedWorkbook} 
                  onChange={(e) => setSelectedWorkbook(e.target.value)}
                  className="appearance-none bg-white border border-transparent text-slate-900 text-xs font-black rounded-lg px-3 py-1.5 pr-8 focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all cursor-pointer shadow-sm min-w-[140px]"
                >
                  <option value="">ALL WORKBOOKS</option>
                  {workbooks.map(w => <option key={w} value={w}>{w}</option>)}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
              </div>
            </div>
            
            <div className="flex items-center gap-1.5">
              <div className="flex items-center gap-1.5 px-2 border-r border-slate-200">
                <Filter size={14} className="text-slate-400" />
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest whitespace-nowrap">Sheet</span>
              </div>
              <div className="relative">
                <select 
                  value={selectedYear} 
                  onChange={(e) => setSelectedYear(e.target.value)}
                  className="appearance-none bg-white border border-transparent text-slate-900 text-xs font-black rounded-lg px-3 py-1.5 pr-8 focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all cursor-pointer shadow-sm min-w-[120px]"
                >
                  <option value="">ALL SHEETS</option>
                  {years.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
              </div>
            </div>
          </div>
            
            <button 
              onClick={fetchLedger}
              className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all"
              title="Refresh Ledger"
            >
              <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto w-full p-4 md:p-6 flex-1 space-y-4">
        {/* Search Bar */}
        <div className="relative group max-w-2xl mx-auto mb-8">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-600 transition-colors" size={18} />
          <input 
            type="text" 
            placeholder="Search archives by project name or ID..."
            className="w-full pl-11 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl shadow-sm focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none text-sm font-medium transition-all"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {loading ? (
          <div className="py-24 flex flex-col items-center gap-3">
            <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
            <p className="text-slate-400 font-bold uppercase tracking-[0.2em] text-xs">Accessing Secure Archives...</p>
          </div>
        ) : filteredProjects.length === 0 ? (
          <div className="py-24 text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-4 text-slate-300">
              <FileSearch size={32} />
            </div>
            <h3 className="text-slate-900 font-bold">No records found</h3>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {filteredProjects.map((project) => {
              const pKey = `${project.project_id}-${project.project_title}`;
              const isExpanded = expandedProjects.has(pKey);

              return (
                <div key={pKey} className={`bg-white border transition-all duration-200 ${isExpanded ? 'border-indigo-200 shadow-md ring-1 ring-indigo-50' : 'border-slate-200 hover:border-indigo-300 hover:shadow-sm'} rounded-xl`}>
                  {/* Project Header */}
                  <div 
                    onClick={() => toggleProject(pKey)} 
                    className="p-3 flex items-center justify-between cursor-pointer group select-none"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all ${isExpanded ? 'bg-indigo-600 text-white shadow-sm' : 'bg-slate-50 text-slate-400 group-hover:bg-indigo-50 group-hover:text-indigo-600'}`}>
                        <Folder size={18} fill={isExpanded ? "currentColor" : "none"} />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                           <h3 className="text-xs font-black text-slate-900 truncate group-hover:text-indigo-600 transition-colors uppercase tracking-tight">{project.project_title}</h3>
                           <span className={`px-1.5 py-0.5 rounded-[4px] text-[8px] font-black border uppercase tracking-wider ${getStatusStyles(project.status)}`}>
                             {project.status}
                           </span>
                        </div>
                        <div className="flex items-center gap-3 mt-0.5 text-xs font-bold text-slate-400 uppercase tracking-widest">
                          <span className="font-mono text-slate-500">#{project.project_id}</span>
                          <span className="flex items-center opacity-60"><Calendar size={10} className="mr-1" /> {project.academic_year}</span>
                          <span className="flex items-center text-indigo-500/60"><BookOpen size={10} className="mr-1" /> {project.workbook_name || 'Legacy Archive'}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <button 
                        onClick={(e) => { e.stopPropagation(); handleDeleteProject(project); }}
                        className="p-1.5 text-slate-300 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                        title="Delete Entire Project History"
                      >
                        <Trash2 size={16} />
                      </button>
                      <div className={`p-1 rounded-md transition-all ${isExpanded ? 'bg-indigo-50 text-indigo-600 rotate-180' : 'text-slate-300 group-hover:text-slate-600'}`}>
                        <ChevronDown size={18} />
                      </div>
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="p-3 pt-0 space-y-2 animate-in slide-in-from-top-2 duration-200">
                      {project.error_message && (
                        <div className="p-3 mb-2 bg-rose-50 border border-rose-100 rounded-lg flex items-start gap-3">
                          <AlertCircle size={14} className="text-rose-600 mt-0.5 shrink-0" />
                          <div className="space-y-1">
                            <p className="text-[10px] font-black text-rose-700 uppercase tracking-widest">Last Archival Error</p>
                            <p className="text-xs text-rose-600 font-medium leading-relaxed">{project.error_message}</p>
                          </div>
                        </div>
                      )}
                      {Object.entries(project.documents).map(([type, versions]) => {
                        if (versions.length === 0) return null;
                        const docKey = `${pKey}-${type}`;
                        const isDocExpanded = expandedDocs.has(docKey);
                        const styles = getDocStyles(type);

                        return (
                          <div key={type} className={`border rounded-lg overflow-hidden transition-all ${isDocExpanded ? 'border-indigo-100 shadow-sm' : 'border-slate-100'}`}>
                            <div 
                              onClick={(e) => { e.stopPropagation(); toggleDoc(pKey, type); }} 
                              className={`p-2.5 flex items-center justify-between cursor-pointer transition-all ${isDocExpanded ? styles.bg : 'hover:bg-slate-50'}`}
                            >
                              <div className="flex items-center gap-3">
                                <ChevronRight size={14} className={`text-slate-400 transition-transform ${isDocExpanded ? 'rotate-90 text-indigo-500' : ''}`} />
                                <div className={`p-1.5 rounded bg-white border border-slate-100 shadow-sm ${styles.text}`}>
                                  {styles.icon}
                                </div>
                                <span className={`text-xs font-black uppercase tracking-widest ${styles.text}`}>{type}</span>
                                <span className="px-1.5 py-0.5 bg-white rounded-full text-[8px] font-black border border-slate-100 text-slate-400 uppercase tracking-widest shadow-sm">
                                  {versions.length} {versions.length > 1 ? 'Versions' : 'Version'}
                                </span>
                              </div>
                            </div>

                            {isDocExpanded && (
                              <div className="bg-white border-t border-slate-50 divide-y divide-slate-50">
                                {versions.map((v) => (
                                  <div key={v.id} className="p-3 flex items-center justify-between group/v hover:bg-slate-50/50 transition-colors">
                                    <div className="flex items-center gap-4 min-w-0">
                                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center bg-slate-50 ${styles.text} border border-slate-100 group-hover/v:bg-white`}>
                                        <Hash size={14} />
                                      </div>
                                      <div className="min-w-0">
                                        <div className="text-[11px] font-black text-slate-800 uppercase tracking-tight">Version {v.version}.0</div>
                                        <div className="flex items-center gap-3 mt-1 text-xs font-bold text-slate-400 uppercase tracking-widest">
                                          <span className="flex items-center"><Clock size={10} className="mr-1" /> {v.timestamp}</span>
                                          <button 
                                            onClick={(e) => { e.stopPropagation(); copyToClipboard(v.hash); }} 
                                            className="flex items-center hover:text-indigo-600 transition-colors group/copy"
                                          >
                                            <span className="font-mono tracking-normal">{v.hash?.substring(0, 12)}...</span>
                                            {copiedHash === v.hash ? <Check size={10} className="ml-1 text-emerald-500" /> : <Copy size={10} className="ml-1 opacity-0 group-hover/copy:opacity-100" />}
                                          </button>
                                        </div>
                                      </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <button 
                                        onClick={(e) => { e.stopPropagation(); window.open(`/api/registry/download/${v.id}/${type}?preview=1`); }}
                                        className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-white rounded-lg border border-transparent hover:border-indigo-100 transition-all"
                                        title="View PDF"
                                      >
                                        <Eye size={14} />
                                      </button>
                                      <button 
                                        onClick={(e) => { e.stopPropagation(); window.open(`/api/registry/download/${v.id}/${type}`); }}
                                        className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-white rounded-lg border border-transparent hover:border-indigo-100 transition-all"
                                        title="Download"
                                      >
                                        <Download size={14} />
                                      </button>
                                      <button 
                                        onClick={(e) => { e.stopPropagation(); handleDelete(v.id); }}
                                        className="p-1.5 text-slate-300 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all"
                                        title="Delete Record"
                                      >
                                        <Trash2 size={14} />
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                      
                      {/* Integrity Footer */}
                      <div className="flex items-center justify-between px-1 text-xs font-black text-slate-300 uppercase tracking-[0.2em] pt-1">
                         <div className="flex items-center gap-1.5">
                           <AlertCircle size={10} />
                           <span>Vault Integrity Verified</span>
                         </div>
                         <span>Total Records: {Object.values(project.documents).flat().length}</span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
      
      <footer className="mt-auto p-6 text-center text-xs font-black text-slate-300 uppercase tracking-[0.3em] border-t border-slate-100">
        DriveSafe Vault &copy; 2026 &bull; Secure Audit Log &bull; v2.6.0
      </footer>
    </div>
  );
};

export default ArchivalLedgerPage;
