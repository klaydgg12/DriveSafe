import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { 
  History, Search, Filter, Calendar, BookOpen, 
  FileText, ArrowLeft, RefreshCw,
  Clock, Eye, ExternalLink, BarChart, Info, Trash2
} from "lucide-react";
import Logo from "../components/Logo";

interface ArchivalRecord {
  id: number;
  project_id: string;
  project_title: string;
  academic_year: string;
  workbook_name: string;
  archived_at: string;
  status: string;
  version: number;
  documents: {
    type: string;
    exists: boolean;
  }[];
}

const ArchiveAnalyticsPage = () => {
  const [records, setRecords] = useState<ArchivalRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [yearFilter, setYearFilter] = useState("All Years");
  const [workbookFilter, setWorkbookFilter] = useState("All Workbooks");
  const [typeFilter, setTypeFilter] = useState("All Types");

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      // We'll use the existing grouped endpoint but flatten it for a "Timeline" view
      const resp = await axios.get('/api/registry/ledger/grouped', { withCredentials: true });
      
      const flatRecords: ArchivalRecord[] = [];
      
      resp.data.forEach((project: any) => {
        // Collect all versions from all document types for this project
        const allVersions: any[] = [];
        
        ['srs', 'sdd', 'spmp', 'std', 'ri', 'source_code', 'database', 'readme'].forEach(type => {
          if (project.documents[type]) {
            project.documents[type].forEach((v: any) => {
              allVersions.push({
                ...v,
                doc_type: type,
                project_id: project.project_id,
                project_title: project.project_title,
                academic_year: project.academic_year,
                workbook_name: project.workbook_name || "Archives"
              });
            });
          }
        });

        // Group by ID (each ArchivalLedger row is one version of a project)
        // Since the current API groups by project, we regroup by ID to get the "Timeline"
        const recordsById = new Map();
        allVersions.forEach(v => {
          if (!recordsById.has(v.id)) {
            recordsById.set(v.id, {
              id: v.id,
              project_id: v.project_id,
              project_title: v.project_title,
              academic_year: v.academic_year,
              workbook_name: v.workbook_name,
              archived_at: v.timestamp,
              status: v.status,
              version: v.version,
              documents: []
            });
          }
          recordsById.get(v.id).documents.push({ type: v.doc_type.toUpperCase(), exists: true });
        });

        recordsById.forEach(record => flatRecords.push(record));
      });

      // Sort by date (Newest First)
      flatRecords.sort((a, b) => new Date(b.archived_at).getTime() - new Date(a.archived_at).getTime());
      
      setRecords(flatRecords);
    } catch (err) {
      console.error("Failed to fetch history:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number, title: string) => {
    if (!window.confirm(`Are you sure you want to permanently delete the archival record for "${title}"? This cannot be undone.`)) {
      return;
    }

    try {
      await axios.delete(`/api/registry/ledger/${id}`, { withCredentials: true });
      // Update local state to remove the deleted record
      setRecords(prev => prev.filter(r => r.id !== id));
    } catch (err) {
      console.error("Failed to delete record:", err);
      alert("Error deleting record. Please check server logs.");
    }
  };

  const years = useMemo(() => ["All Years", ...Array.from(new Set(records.map(r => r.academic_year)))], [records]);
  const workbooks = useMemo(() => ["All Workbooks", ...Array.from(new Set(records.map(r => r.workbook_name)))], [records]);

  const filteredRecords = useMemo(() => {
    return records.filter(r => {
      const matchesSearch = r.project_title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                           r.project_id.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesYear = yearFilter === "All Years" || r.academic_year === yearFilter;
      const matchesWorkbook = workbookFilter === "All Workbooks" || r.workbook_name === workbookFilter;
      const matchesType = typeFilter === "All Types" || r.documents.some(d => d.type === typeFilter);
      
      return matchesSearch && matchesYear && matchesWorkbook && matchesType;
    });
  }, [records, searchQuery, yearFilter, workbookFilter, typeFilter]);

  // Statistics for the top bar
  const stats = useMemo(() => {
    const total = records.length;
    const today = records.filter(r => {
      const date = new Date(r.archived_at);
      const now = new Date();
      return date.toDateString() === now.toDateString();
    }).length;
    return { total, today };
  }, [records]);

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col font-sans">
      {/* Navbar */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-8 md:px-12 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => window.location.hash = "dashboard"} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
              <ArrowLeft size={20} className="text-slate-500" />
            </button>
            <div className="flex items-center gap-3">
              <Logo size={35} />
              <span className="text-lg font-bold text-slate-900 tracking-tight">Vault Analytics</span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
             <div className="hidden md:flex flex-col items-end mr-4">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Active Session</span>
                <span className="text-xs font-semibold text-indigo-600">Archival History Mode</span>
             </div>
             <button 
              onClick={fetchHistory}
              className="p-2 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all"
              title="Refresh History"
             >
               <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
             </button>
          </div>
        </div>
      </nav>

      <main className="max-w-[1600px] mx-auto w-full p-8 md:p-12 space-y-8">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              <History className="text-indigo-600" /> Archival Timeline
            </h1>
            <p className="text-slate-500 text-sm font-medium mt-1">Real-time tracking of all binary vault operations</p>
          </div>

          <div className="flex gap-3">
            <div className="bg-white px-4 py-3 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
              <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
                <BarChart size={18} />
              </div>
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Total Archivals</p>
                <p className="text-lg font-black text-slate-900 leading-none">{stats.total}</p>
              </div>
            </div>
            <div className="bg-white px-4 py-3 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
              <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600">
                <Clock size={18} />
              </div>
              <div>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Sessions Today</p>
                <p className="text-lg font-black text-slate-900 leading-none">{stats.today}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Search and Filters Bar */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input 
              type="text"
              placeholder="Search by Team ID, Project Title, or Keyword..."
              className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all font-medium text-slate-700"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="flex flex-wrap gap-3">
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-600">
              <Calendar size={16} className="text-slate-400" />
              <select 
                className="bg-transparent outline-none text-xs font-bold"
                value={yearFilter}
                onChange={(e) => setYearFilter(e.target.value)}
              >
                {years.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-600">
              <BookOpen size={16} className="text-slate-400" />
              <select 
                className="bg-transparent outline-none text-xs font-bold"
                value={workbookFilter}
                onChange={(e) => setWorkbookFilter(e.target.value)}
              >
                {workbooks.map(w => <option key={w} value={w}>{w}</option>)}
              </select>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-600">
              <Filter size={16} className="text-slate-400" />
              <select 
                className="bg-transparent outline-none text-xs font-bold"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <option value="All Types">All Doc Types</option>
                <option value="SRS">SRS Only</option>
                <option value="SDD">SDD Only</option>
                <option value="SPMP">SPMP Only</option>
                <option value="STD">STD Only</option>
                <option value="RI">RI Only</option>
                <option value="SOURCE_CODE">Source Code Only</option>
                <option value="DATABASE">Database Only</option>
                <option value="README">ReadMe Only</option>
              </select>
            </div>
          </div>
        </div>

        {/* Timeline List */}
        <div className="space-y-4">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center text-slate-400 space-y-4">
              <RefreshCw size={40} className="animate-spin text-indigo-500" />
              <p className="font-bold tracking-widest text-xs uppercase">Loading Timeline Data...</p>
            </div>
          ) : filteredRecords.length === 0 ? (
            <div className="py-20 flex flex-col items-center justify-center text-slate-400 bg-white rounded-3xl border border-dashed border-slate-300">
              <Info size={40} className="mb-4" />
              <p className="font-bold">No archival history found matching your search.</p>
              <button onClick={() => { setSearchQuery(""); setYearFilter("All Years"); }} className="mt-4 text-indigo-600 font-bold hover:underline">Clear all filters</button>
            </div>
          ) : (
            filteredRecords.map((record) => (
              <div 
                key={record.id} 
                className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md hover:border-indigo-100 transition-all group overflow-hidden"
              >
                <div className="flex flex-col md:flex-row">
                  {/* Status Indicator Bar */}
                  <div className={`w-1.5 md:w-2 shrink-0 ${record.status === 'archived' ? 'bg-emerald-400' : 'bg-rose-400'}`}></div>
                  
                  <div className="flex-1 p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                    <div className="flex items-start gap-4 flex-1">
                      <div className="w-12 h-12 bg-slate-50 rounded-xl flex items-center justify-center shrink-0 border border-slate-100 group-hover:bg-indigo-50 group-hover:border-indigo-100 transition-colors">
                        <History className="text-slate-400 group-hover:text-indigo-500 transition-colors" size={24} />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[10px] font-black px-2 py-0.5 bg-slate-100 text-slate-500 rounded-md uppercase tracking-wider">TEAM {record.project_id}</span>
                          <span className="text-[10px] font-black px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded-md uppercase tracking-wider">v{record.version}</span>
                        </div>
                        <h3 className="text-lg font-bold text-slate-900 truncate group-hover:text-indigo-600 transition-colors">{record.project_title}</h3>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1">
                          <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium">
                            <BookOpen size={14} className="text-slate-400" /> {record.workbook_name}
                          </div>
                          <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium">
                            <Calendar size={14} className="text-slate-400" /> {record.academic_year}
                          </div>
                          <div className="flex items-center gap-1.5 text-slate-500 text-xs font-medium">
                            <Clock size={14} className="text-slate-400" /> {new Date(record.archived_at).toLocaleString('en-PH', { 
                              timeZone: 'Asia/Manila',
                              weekday: 'long',
                              year: 'numeric',
                              month: 'long',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                              second: '2-digit',
                              hour12: true
                            })} (GMT+8)
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col md:items-end gap-3 w-full md:w-auto">
                      <div className="flex flex-wrap gap-1.5">
                        {record.documents.map(doc => (
                          <div key={doc.type} className="flex items-center gap-1 px-2 py-1 bg-slate-50 text-slate-600 rounded-lg border border-slate-100 text-[10px] font-bold">
                            <FileText size={12} className="text-indigo-500" /> {doc.type}
                          </div>
                        ))}
                      </div>
                      
                      <div className="flex gap-2">
                        <button 
                          onClick={() => window.open(`/api/registry/download/${record.id}/${record.documents[0].type.toLowerCase()}?preview=1`)}
                          className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 text-white text-xs font-bold rounded-xl hover:bg-indigo-700 shadow-lg shadow-indigo-100 transition-all active:scale-95"
                        >
                          <Eye size={14} /> View Files
                        </button>
                        <button 
                          onClick={() => window.location.hash = "ledger"}
                          className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all border border-transparent hover:border-indigo-100"
                          title="Open in Ledger"
                        >
                          <ExternalLink size={16} />
                        </button>
                        <button 
                          onClick={() => handleDelete(record.id, record.project_title)}
                          className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all border border-transparent hover:border-rose-100"
                          title="Delete Record"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </main>

      <footer className="mt-auto py-8 text-center border-t border-slate-200">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.3em]">
          DriveSafe Internal Archival Log • CIT-University
        </p>
      </footer>
    </div>
  );
};

export default ArchiveAnalyticsPage;
