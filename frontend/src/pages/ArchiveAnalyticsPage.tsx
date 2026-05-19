import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { 
  History, Search, Folder, BookOpen, 
  ArrowLeft, RefreshCw,
  Clock, Eye, Trash2, ChevronRight, ChevronDown,
  Layers, User, CheckCircle2, AlertCircle
  } from "lucide-react";
import Logo from "../components/Logo";

interface Project {
  id: number;
  project_id: string;
  project_title: string;
  status: string;
  version: number;
  error?: string;
  srs_rev?: number;
  sdd_rev?: number;
  spmp_rev?: number;
  std_rev?: number;
  ri_rev?: number;
  research_paper_rev?: number;
  usability_test_rev?: number;
  presentation_rev?: number;
  source_code_rev?: number;
  database_rev?: number;
  readme_rev?: number;
}

interface Transaction {
  transaction_id: string;
  transaction_label: string;
  timestamp: string;
  archived_by: string;
  project_count: number;
  projects: Project[];
}

interface Sheet {
  name: string;
  transactions: Transaction[];
}

interface Workbook {
  name: string;
  sheets: Sheet[];
}

const ArchiveAnalyticsPage = () => {
  const [workbooks, setWorkbooks] = useState<Workbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedWorkbooks, setExpandedWorkbooks] = useState<Set<string>>(new Set());
  const [expandedSheets, setExpandedSheets] = useState<Set<string>>(new Set());
  const [expandedTransactions, setExpandedTransactions] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchTransactions();
  }, []);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const resp = await axios.get('/api/registry/transactions', { withCredentials: true });
      setWorkbooks(resp.data);
      // Auto-expand the first workbook and sheet if they exist
      if (resp.data.length > 0) {
        setExpandedWorkbooks(new Set([resp.data[0].name]));
        if (resp.data[0].sheets.length > 0) {
          setExpandedSheets(new Set([`${resp.data[0].name}-${resp.data[0].sheets[0].name}`]));
        }
      }
    } catch (err) {
      console.error("Failed to fetch transactions:", err);
    } finally {
      setLoading(false);
    }
  };

  const toggleWorkbook = (name: string) => {
    const next = new Set(expandedWorkbooks);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setExpandedWorkbooks(next);
  };

  const toggleSheet = (wb: string, sh: string) => {
    const key = `${wb}-${sh}`;
    const next = new Set(expandedSheets);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setExpandedSheets(next);
  };

  const toggleTransaction = (txId: string) => {
    const next = new Set(expandedTransactions);
    if (next.has(txId)) next.delete(txId);
    else next.add(txId);
    setExpandedTransactions(next);
  };

  const handleDelete = async (id: number, title: string) => {
    if (!window.confirm(`Permanently delete record for "${title}"?`)) return;
    try {
      await axios.delete(`/api/registry/ledger/${id}`, { withCredentials: true });
      fetchTransactions();
    } catch (err) {
      alert("Delete failed.");
    }
  };

  const formatFullDate = (isoString: string) => {
    return new Date(isoString).toLocaleString('en-PH', { 
      timeZone: 'Asia/Manila',
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    }) + " (GMT+8)";
  };

  const filteredWorkbooks = useMemo(() => {
    if (!searchQuery) return workbooks;
    const q = searchQuery.toLowerCase();
    return workbooks.map(wb => ({
      ...wb,
      sheets: wb.sheets.map(sh => ({
        ...sh,
        transactions: sh.transactions.map(tx => ({
          ...tx,
          projects: tx.projects.filter(p => 
            p.project_title.toLowerCase().includes(q) || 
            p.project_id.toLowerCase().includes(q) ||
            tx.transaction_label.toLowerCase().includes(q)
          )
        })).filter(tx => tx.projects.length > 0)
      })).filter(sh => sh.transactions.length > 0)
    })).filter(wb => wb.sheets.length > 0);
  }, [workbooks, searchQuery]);

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col font-sans">
      {/* Navbar */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-[1400px] mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => window.location.hash = "dashboard"} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
              <ArrowLeft size={20} className="text-slate-500" />
            </button>
            <div className="flex items-center gap-3">
              <Logo size={32} />
              <span className="text-lg font-bold text-slate-900 tracking-tight">Reports</span>
            </div>
          </div>
          <button onClick={fetchTransactions} className="p-2 text-slate-500 hover:text-indigo-600 rounded-lg transition-all">
            <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </nav>

      <main className="max-w-[1400px] mx-auto w-full p-6 md:p-10 space-y-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              <History className="text-indigo-600" /> Reports
            </h1>
            <p className="text-slate-500 text-sm font-medium mt-1">Sequential history organized by Workbook and Sheet</p>
          </div>
          <div className="relative w-full md:w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input 
              type="text"
              placeholder="Search by team, title or transaction..."
              className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all text-sm font-medium"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center text-slate-400 space-y-4">
            <RefreshCw size={40} className="animate-spin text-indigo-500" />
            <p className="font-bold tracking-widest text-xs uppercase">Loading Vault Registry...</p>
          </div>
        ) : filteredWorkbooks.length === 0 ? (
          <div className="py-20 text-center bg-white rounded-3xl border border-dashed border-slate-300">
            <Layers size={40} className="mx-auto text-slate-300 mb-4" />
            <p className="text-slate-500 font-bold">No archival transactions found.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {filteredWorkbooks.map((wb) => (
              <div key={wb.name} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <button 
                  onClick={() => toggleWorkbook(wb.name)}
                  className="w-full px-6 py-4 flex items-center justify-between bg-slate-50/50 hover:bg-slate-50 transition-colors border-b border-slate-100"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">
                      <BookOpen size={18} />
                    </div>
                    <span className="font-black text-slate-800 uppercase tracking-tight">{wb.name}</span>
                  </div>
                  {expandedWorkbooks.has(wb.name) ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                </button>

                {expandedWorkbooks.has(wb.name) && (
                  <div className="p-4 space-y-4">
                    {wb.sheets.map((sh) => (
                      <div key={sh.name} className="ml-2 md:ml-4 border-l-2 border-slate-100 pl-4 space-y-3">
                        <button 
                          onClick={() => toggleSheet(wb.name, sh.name)}
                          className="w-full flex items-center justify-between group/sh py-2 pr-4 hover:bg-indigo-50/50 rounded-xl transition-all"
                        >
                          <div className="flex items-center gap-2 text-sm font-bold text-slate-600 group-hover/sh:text-indigo-600 transition-colors">
                            <Folder size={16} className="text-slate-400 group-hover/sh:text-indigo-500" />
                            {sh.name}
                            <span className="text-[10px] bg-slate-100 text-slate-400 px-1.5 py-0.5 rounded ml-1 group-hover/sh:bg-indigo-100 group-hover/sh:text-indigo-600">
                              {sh.transactions.length} SESSIONS
                            </span>
                          </div>
                          {expandedSheets.has(`${wb.name}-${sh.name}`) ? (
                            <ChevronDown size={18} className="text-slate-400 group-hover/sh:text-indigo-500" />
                          ) : (
                            <ChevronRight size={18} className="text-slate-400 group-hover/sh:text-indigo-500" />
                          )}
                        </button>

                        {expandedSheets.has(`${wb.name}-${sh.name}`) && (
                          <div className="space-y-4 mt-4 ml-2">
                            {sh.transactions.map((tx) => (
                              <div key={tx.transaction_id} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden group/tx">
                                <button 
                                  onClick={() => toggleTransaction(tx.transaction_id)}
                                  className="w-full px-5 py-4 flex items-center justify-between hover:bg-slate-50 transition-all"
                                >
                                  <div className="flex items-center gap-4">
                                    <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl group-hover/tx:bg-indigo-600 group-hover/tx:text-white transition-all">
                                      <History size={20} />
                                    </div>
                                    <div className="text-left">
                                      <h4 className="text-sm font-black text-slate-900 uppercase tracking-tight">
                                        {tx.transaction_label}
                                      </h4>
                                      <div className="flex items-center gap-3 mt-1">
                                        <span className="text-[10px] text-slate-400 font-bold flex items-center gap-1">
                                          <Clock size={10} /> {formatFullDate(tx.timestamp)}
                                        </span>
                                        <span className="text-[10px] text-slate-300">•</span>
                                        <span className="text-[10px] text-slate-500 font-black">{tx.project_count} PROJECTS</span>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-4">
                                    <div className="hidden md:flex flex-col items-end">
                                      <span className="text-[9px] font-black text-slate-300 uppercase tracking-widest flex items-center gap-1"><User size={8} /> OPERATOR</span>
                                      <span className="text-[10px] font-bold text-slate-500">{tx.archived_by}</span>
                                    </div>
                                    {expandedTransactions.has(tx.transaction_id) ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                                  </div>
                                </button>

                                {expandedTransactions.has(tx.transaction_id) && (
                                  <div className="p-0 bg-slate-50/30 border-t border-slate-100">
                                    <div className="overflow-x-auto">
                                      <table className="w-full text-left">
                                        <thead>
                                          <tr className="text-[10px] font-black text-slate-400 uppercase tracking-widest bg-slate-50/50 border-b border-slate-100">
                                            <th className="py-3 pl-6">Status</th>
                                            <th className="py-3">Team Code</th>
                                            <th className="py-3">Project Title</th>
                                            <th className="py-3">Revision</th>
                                            <th className="py-3 text-right pr-6">Actions</th>
                                          </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100">
                                          {tx.projects.map((p) => (
                                            <tr key={p.id} className="hover:bg-white transition-colors group/row">
                                              <td className="py-3 pl-6">
                                                <div className="flex items-center gap-2">
                                                  {p.status === 'archived' ? (
                                                    <CheckCircle2 size={16} className="text-emerald-500" />
                                                  ) : (
                                                    <div title={p.error}>
                                                      <AlertCircle size={16} className="text-amber-500" />
                                                    </div>
                                                  )}
                                                  <span className={`text-[10px] font-black uppercase tracking-tighter ${p.status === 'archived' ? 'text-emerald-600' : 'text-amber-600'}`}>
                                                    {p.status}
                                                  </span>
                                                </div>
                                              </td>
                                              <td className="py-3">
                                                <span className="text-xs font-black text-slate-700">{p.project_id}</span>
                                              </td>
                                              <td className="py-3">
                                                <span className="text-xs font-bold text-slate-500 truncate block max-w-[400px]">{p.project_title}</span>
                                              </td>
                                              <td className="py-3">
                                                <div className="flex flex-wrap gap-1">
                                                  {[
                                                    { id: 'srs', label: 'SRS' },
                                                    { id: 'sdd', label: 'SDD' },
                                                    { id: 'spmp', label: 'SPMP' },
                                                    { id: 'std', label: 'STD' },
                                                    { id: 'ri', label: 'RI' },
                                                    { id: 'research_paper', label: 'RP' },
                                                    { id: 'usability_test', label: 'UT' },
                                                    { id: 'presentation', label: 'PR' },
                                                    { id: 'source_code', label: 'SRC' },
                                                    { id: 'database', label: 'DB' },
                                                    { id: 'readme', label: 'RM' }
                                                  ].map(doc => {
                                                    const rev = (p as any)[`${doc.id}_rev`];
                                                    if (!rev) return null;
                                                    return (
                                                      <span key={doc.id} className="text-[9px] font-black px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded border border-slate-200" title={`${doc.label} Revision ${rev}`}>
                                                        {doc.label} v{rev}
                                                      </span>
                                                    );
                                                  })}
                                                  <span className="text-[10px] font-black px-2 py-0.5 bg-indigo-50 text-indigo-600 rounded-md border border-indigo-100" title={`Project Snapshot v${p.version}`}>
                                                    SNAP v{p.version}
                                                  </span>
                                                </div>
                                              </td>
                                              <td className="py-3 text-right pr-6">
                                                <div className="flex items-center justify-end gap-2">
                                                  <button 
                                                    onClick={() => window.open(`/api/registry/download/${p.id}/srs?preview=1`)}
                                                    className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all"
                                                    title="View Archive"
                                                  >
                                                    <Eye size={14} />
                                                  </button>
                                                  <button 
                                                    onClick={() => handleDelete(p.id, p.project_title)}
                                                    className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-all"
                                                    title="Delete"
                                                  >
                                                    <Trash2 size={14} />
                                                  </button>
                                                </div>
                                              </td>
                                            </tr>
                                          ))}
                                        </tbody>
                                      </table>
                                    </div>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
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
