import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { 
  ArrowLeft, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle, 
  ExternalLink, 
  Download,
  ChevronDown,
  Search,
  Eye,
  RotateCcw,
  BookOpen,
  Filter,
  CheckSquare,
  Square,
  ChevronUp,
  Trash2,
  FileText
} from "lucide-react";
import Logo from "../components/Logo";

interface Project {
    row_index: number;
    project_id: string;
    project_title: string;
    srs_link: string;
    sdd_link: string;
    spmp_link: string;
    std_link: string;
    ri_link: string;
    status: string;
    academic_year: string;
    latest_version?: number;
}

interface Workbook { id: string; name: string; }

type SortField = 'project_id' | 'project_title' | 'status';
type SortOrder = 'asc' | 'desc';

const RegistryDashboard: React.FC = () => {
    const [workbooks, setWorkbooks] = useState<Workbook[]>([]);
    const [selectedWorkbookId, setSelectedWorkbookId] = useState<string>('');
    const [years, setYears] = useState<string[]>([]);
    const [selectedYear, setSelectedYear] = useState<string>('');
    const [projects, setProjects] = useState<Project[]>([]);
    const [selectedRows, setSelectedRows] = useState<number[]>([]);
    const [validationResults, setValidationResults] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState<boolean>(false);
    const [message, setMessage] = useState<{ text: string, type: 'info' | 'error' | 'success' } | null>(null);
    const [isProcessing, setIsProcessing] = useState<boolean>(false);
    
    // Search and Sort State
    const [searchQuery, setSearchQuery] = useState<string>('');
    const [sortField, setSortField] = useState<SortField>('project_title');
    const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
    const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);

    // Auto-refresh logic while processing
    useEffect(() => {
        let interval: any;
        if (isProcessing) {
            interval = setInterval(() => {
                fetchProjects(selectedYear, selectedWorkbookId, true);
            }, 5000);
        }
        return () => { if (interval) clearInterval(interval); };
    }, [isProcessing, selectedYear, selectedWorkbookId]);

    // Check if processing is finished
    useEffect(() => {
        if (isProcessing && projects.length > 0) {
            const stillProcessing = projects.some(p => p.status.toLowerCase() === 'processing');
            if (!stillProcessing) {
                setIsProcessing(false);
                setMessage({ text: "Processing complete.", type: 'success' });
            }
        }
    }, [projects]);

    useEffect(() => { fetchWorkbooks(); }, []);
    useEffect(() => {
        if (selectedWorkbookId) fetchYears(selectedWorkbookId);
    }, [selectedWorkbookId]);
    useEffect(() => {
        if (selectedYear && selectedWorkbookId) fetchProjects(selectedYear, selectedWorkbookId);
    }, [selectedYear, selectedWorkbookId]);

    const fetchWorkbooks = async () => {
        try {
            const res = await axios.get(`/api/registry/list-sheets`, { withCredentials: true });
            setWorkbooks(res.data);
            if (res.data.length > 0) setSelectedWorkbookId(res.data[0].id);
        } catch { setMessage({ text: "Failed to load Google Sheets.", type: 'error' }); }
    };

    const fetchYears = async (workbookId: string) => {
        try {
            const res = await axios.get(`/api/registry/years?sheet_id=${workbookId}`, { withCredentials: true });
            setYears(res.data);
            setSelectedYear(res.data.length > 0 ? res.data[0] : '');
        } catch { setMessage({ text: "Failed to load years.", type: 'error' }); }
    };

    const fetchProjects = async (year: string, workbookId: string, silent = false) => {
        if (!silent) setLoading(true);
        try {
            const res = await axios.get(`/api/registry/projects?year=${year}&sheet_id=${workbookId}`, { withCredentials: true });
            setProjects(res.data);
            if (!silent) {
                setSelectedRows([]);
                setValidationResults({});
            }
        } catch { if (!silent) setMessage({ text: "Failed to load projects.", type: 'error' }); }
        finally { if (!silent) setLoading(false); }
    };

    const handleSelectRow = (rowIndex: number) => {
        setSelectedRows(prev => prev.includes(rowIndex) ? prev.filter(r => r !== rowIndex) : [...prev, rowIndex]);
    };

    const handleSelectAll = () => {
        const visibleProjectIndices = filteredAndSortedProjects.map(p => p.row_index);
        const allVisibleSelected = visibleProjectIndices.every(idx => selectedRows.includes(idx));
        
        if (allVisibleSelected) {
            setSelectedRows(prev => prev.filter(idx => !visibleProjectIndices.includes(idx)));
        } else {
            setSelectedRows(prev => Array.from(new Set([...prev, ...visibleProjectIndices])));
        }
    };

    const validateLinks = async () => {
        const linksToValidate = projects.flatMap(p => [p.srs_link, p.sdd_link, p.spmp_link, p.std_link, p.ri_link]).filter(l => l);
        if (linksToValidate.length === 0) return;
        setLoading(true);
        try {
            const res = await axios.post(`/api/registry/validate`, { links: linksToValidate, sheet_id: selectedWorkbookId }, { withCredentials: true });
            setValidationResults(res.data);
            setMessage({ text: "Validation complete. Check document eye icons for status.", type: 'success' });
        } catch { setMessage({ text: "Validation failed.", type: 'error' }); }
        finally { setLoading(false); }
    };

    const handleArchive = async () => {
        const selectedProjects = projects.filter(p => selectedRows.includes(p.row_index));
        if (selectedProjects.length === 0) return;
        
        setIsProcessing(true);
        setShowConfirmModal(false);
        try {
            await axios.post(`/api/registry/archive`, { projects: selectedProjects, sheet_id: selectedWorkbookId }, { withCredentials: true });
            setMessage({ text: "Archival sequence initiated.", type: 'success' });
            setTimeout(() => fetchProjects(selectedYear, selectedWorkbookId, true), 2000);
        } catch { setMessage({ text: "Archival request failed.", type: 'error' }); }
        finally { setIsProcessing(false); }
    };

    const handleResetStatus = async (project: Project) => {
        try {
            await axios.post(`/api/registry/reset`, { project }, { withCredentials: true });
            setMessage({ text: `Reset ${project.project_id} to Pending.`, type: 'info' });
            fetchProjects(selectedYear, selectedWorkbookId, true);
        } catch { setMessage({ text: "Failed to reset status.", type: 'error' }); }
    };

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortOrder('asc');
        }
    };

    const filteredAndSortedProjects = useMemo(() => {
        return projects
            .filter(p => 
                p.project_title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                p.project_id.toLowerCase().includes(searchQuery.toLowerCase())
            )
            .sort((a, b) => {
                const valA = (a[sortField] || '').toString().toLowerCase();
                const valB = (b[sortField] || '').toString().toLowerCase();
                if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
                if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
                return 0;
            });
    }, [projects, searchQuery, sortField, sortOrder]);

    const getStatusBadge = (status: string) => {
        const s = status.toLowerCase();
        let classes = "bg-gray-100 text-gray-600";
        if (s === 'pending') classes = "bg-amber-100 text-amber-700 ring-1 ring-amber-200";
        if (s === 'archived') classes = "bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200";
        if (s === 'failed') classes = "bg-red-100 text-red-700 ring-1 ring-red-200";
        if (s === 'processing') classes = "bg-indigo-100 text-indigo-700 animate-pulse ring-1 ring-indigo-200";

        return (
            <span className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider ${classes}`}>
                {status}
            </span>
        );
    };

    const renderSortIcon = (field: SortField) => {
        if (sortField !== field) return <ChevronDown className="w-3 h-3 opacity-20" />;
        return sortOrder === 'asc' ? <ChevronUp className="w-3 h-3 text-indigo-600" /> : <ChevronDown className="w-3 h-3 text-indigo-600" />;
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900">
            {/* Confirmation Modal */}
            {showConfirmModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-white w-full max-w-md rounded-[2rem] shadow-2xl p-8 space-y-6 animate-in zoom-in-95">
                        <div className="w-16 h-16 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mx-auto">
                            <Download className="w-8 h-8" />
                        </div>
                        <div className="text-center space-y-2">
                            <h3 className="text-2xl font-black tracking-tight">Confirm Archival</h3>
                            <p className="text-slate-500 font-medium leading-relaxed">
                                You are about to initiate archival for <span className="text-indigo-600 font-bold">{selectedRows.length} projects</span>. 
                                This will sync files to local storage and update the registry.
                            </p>
                        </div>
                        <div className="flex gap-3 pt-2">
                            <button 
                                onClick={() => setShowConfirmModal(false)}
                                className="flex-1 py-4 bg-slate-100 hover:bg-slate-200 text-slate-600 font-bold rounded-2xl transition-all"
                            >
                                Cancel
                            </button>
                            <button 
                                onClick={handleArchive}
                                className="flex-1 py-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-2xl shadow-lg shadow-indigo-100 transition-all"
                            >
                                Start Sequence
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Sticky Header */}
            <header className="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50">
                <div className="max-w-[1600px] mx-auto px-6 h-20 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button onClick={() => window.location.hash = "dashboard"} className="p-2.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all">
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div className="h-8 w-px bg-slate-100"></div>
                        <div className="flex items-center gap-3">
                            <Logo size={60} />
                            <div className="flex flex-col">
                                <span className="text-lg font-black tracking-tight leading-none">Capstone Archiver</span>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className="px-2 py-0.5 bg-emerald-50 text-emerald-600 text-[10px] font-black rounded-md border border-emerald-100 uppercase tracking-widest">
                                        Registry v2.0
                                    </span>
                                    {selectedYear && (
                                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                            {selectedYear}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-6 bg-slate-50 p-1.5 rounded-2xl border border-slate-200">
                        <div className="flex items-center gap-2 px-3">
                            <BookOpen className="w-4 h-4 text-slate-400" />
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Active Sheet</span>
                        </div>
                        <div className="relative group">
                            <select 
                                value={selectedWorkbookId} 
                                onChange={(e) => setSelectedWorkbookId(e.target.value)}
                                className="appearance-none bg-white border border-slate-200 text-slate-900 text-sm font-black rounded-xl px-4 py-2 pr-10 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all cursor-pointer shadow-sm min-w-[200px]"
                            >
                                {workbooks.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none transition-transform group-hover:translate-y-[-40%]" />
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-[1600px] mx-auto w-full p-6 md:p-8 space-y-8">
                {/* Toolbar */}
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                    <div className="flex flex-wrap items-center gap-3">
                        <div className="relative group min-w-[320px]">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-indigo-600 transition-colors" />
                            <input 
                                type="text"
                                placeholder="Search project ID or title..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-11 pr-4 py-3 bg-white border-2 border-slate-100 rounded-2xl focus:ring-4 focus:ring-indigo-500/5 focus:border-indigo-500 outline-none font-medium transition-all shadow-sm"
                            />
                        </div>
                        <button 
                            onClick={validateLinks} 
                            disabled={loading || projects.length === 0}
                            className="px-6 py-3 bg-white border-2 border-indigo-100 text-indigo-600 text-sm font-black rounded-2xl hover:bg-indigo-50 hover:border-indigo-200 transition-all flex items-center gap-2 shadow-sm disabled:opacity-50"
                        >
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Validate Links
                        </button>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="bg-indigo-50 px-4 py-2 rounded-xl border border-indigo-100 flex items-center gap-3">
                            <span className="text-[10px] font-black text-indigo-600 uppercase tracking-widest">Selection</span>
                            <span className="w-6 h-6 bg-indigo-600 text-white text-[10px] font-black rounded-lg flex items-center justify-center">
                                {selectedRows.length}
                            </span>
                        </div>
                        <button 
                            onClick={() => setShowConfirmModal(true)} 
                            disabled={isProcessing || selectedRows.length === 0}
                            className="px-8 py-3 bg-indigo-600 text-white text-sm font-black rounded-2xl hover:bg-indigo-700 hover:scale-[1.02] transition-all flex items-center gap-2 shadow-xl shadow-indigo-100 disabled:opacity-50 disabled:scale-100 disabled:shadow-none"
                        >
                            <Download className="w-4 h-4" /> Run Archival Sequence
                        </button>
                        <button onClick={() => fetchProjects(selectedYear, selectedWorkbookId)} className="p-3 bg-white border border-slate-200 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-2xl transition-all shadow-sm">
                            <RotateCcw className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {message && (
                    <div className={`p-5 rounded-2xl border-2 flex items-center justify-between shadow-sm animate-in slide-in-from-top-4 duration-300 ${
                        message.type === 'error' ? 'bg-red-50 border-red-100 text-red-700' : 
                        message.type === 'success' ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : 
                        'bg-indigo-50 border-indigo-100 text-indigo-700'
                    }`}>
                        <div className="flex items-center gap-4">
                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${message.type === 'error' ? 'bg-red-100' : message.type === 'success' ? 'bg-emerald-100' : 'bg-indigo-100'}`}>
                                {message.type === 'error' ? <AlertCircle className="w-5 h-5" /> : <CheckCircle className="w-5 h-5" />}
                            </div>
                            <span className="text-sm font-bold">{message.text}</span>
                        </div>
                        <button onClick={() => setMessage(null)} className="text-[10px] font-black uppercase tracking-widest opacity-50 hover:opacity-100 px-4">Dismiss</button>
                    </div>
                )}

                {/* Table Section */}
                <div className="bg-white rounded-[2.5rem] border border-slate-200 shadow-xl shadow-slate-200/40 overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-slate-50/80 border-b border-slate-100">
                                    <th className="px-6 py-5 w-16 text-center">
                                        <button 
                                            onClick={handleSelectAll}
                                            className="w-6 h-6 flex items-center justify-center rounded-lg transition-colors hover:bg-indigo-50 text-indigo-600"
                                        >
                                            {filteredAndSortedProjects.length > 0 && filteredAndSortedProjects.every(p => selectedRows.includes(p.row_index)) 
                                                ? <CheckSquare className="w-5 h-5" /> 
                                                : <Square className="w-5 h-5" />}
                                        </button>
                                    </th>
                                    <th onClick={() => handleSort('project_id')} className="px-6 py-5 cursor-pointer group whitespace-nowrap">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">ID</span>
                                            {renderSortIcon('project_id')}
                                        </div>
                                    </th>
                                    <th onClick={() => handleSort('project_title')} className="px-6 py-5 cursor-pointer group min-w-[300px]">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Project Title</span>
                                            {renderSortIcon('project_title')}
                                        </div>
                                    </th>
                                    <th className="px-6 py-5">
                                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Assets</span>
                                    </th>
                                    <th onClick={() => handleSort('status')} className="px-6 py-5 cursor-pointer group text-right pr-12">
                                        <div className="flex items-center justify-end gap-2">
                                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Status</span>
                                            {renderSortIcon('status')}
                                        </div>
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50">
                                {loading && projects.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="px-6 py-32">
                                            <div className="flex flex-col items-center gap-4">
                                                <RefreshCw className="w-10 h-10 text-indigo-600 animate-spin" />
                                                <p className="text-slate-400 font-bold uppercase tracking-widest text-xs">Scanning Registry...</p>
                                            </div>
                                        </td>
                                    </tr>
                                ) : filteredAndSortedProjects.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="px-6 py-32">
                                            <div className="flex flex-col items-center gap-6 max-w-xs mx-auto text-center">
                                                <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center text-slate-300">
                                                    <Filter className="w-10 h-10" />
                                                </div>
                                                <div className="space-y-2">
                                                    <p className="text-slate-900 font-black text-xl">No projects found</p>
                                                    <p className="text-slate-400 text-sm font-medium">Try adjusting your search or switching to a different sheet.</p>
                                                </div>
                                                <button 
                                                    onClick={() => setSearchQuery('')}
                                                    className="px-6 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-black rounded-xl uppercase tracking-widest transition-all"
                                                >
                                                    Clear Filter
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ) : filteredAndSortedProjects.map((p) => {
                                    const isSelected = selectedRows.includes(p.row_index);
                                    return (
                                        <tr key={p.row_index} className={`group transition-all duration-200 ${isSelected ? 'bg-indigo-50/30' : 'hover:bg-slate-50/50'}`}>
                                            <td className="px-6 py-5 text-center">
                                                <button 
                                                    onClick={() => handleSelectRow(p.row_index)}
                                                    className={`w-6 h-6 flex items-center justify-center rounded-lg transition-all ${isSelected ? 'text-indigo-600 scale-110' : 'text-slate-200 hover:text-slate-400'}`}
                                                >
                                                    {isSelected ? <CheckSquare className="w-5 h-5 shadow-lg shadow-indigo-100" /> : <Square className="w-5 h-5" />}
                                                </button>
                                            </td>
                                            <td className="px-6 py-5">
                                                <span className="text-xs font-mono font-bold text-slate-400 bg-slate-50 px-2 py-1 rounded-md border border-slate-100">
                                                    {p.project_id || "ID-?"}
                                                </span>
                                            </td>
                                            <td className="px-6 py-5">
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">{p.project_title}</span>
                                                    <span className="text-[10px] font-medium text-slate-400 mt-1 uppercase tracking-widest">{p.academic_year}</span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-5">
                                                <div className="flex items-center gap-1.5">
                                                    {['srs', 'sdd', 'spmp', 'std', 'ri'].map(doc => {
                                                        const link = p[`${doc}_link` as keyof Project] as string;
                                                        const isAccessible = validationResults[link] === 'Accessible';
                                                        const isMissing = !link;
                                                        
                                                        return (
                                                            <div key={doc} className="relative group/doc">
                                                                <a 
                                                                    href={link || '#'} 
                                                                    target="_blank" 
                                                                    rel="noreferrer" 
                                                                    className={`w-10 h-10 flex items-center justify-center rounded-xl border-2 transition-all ${
                                                                        isMissing ? 'bg-slate-50 border-slate-100 text-slate-200 cursor-not-allowed' :
                                                                        isAccessible ? 'bg-emerald-50 border-emerald-100 text-emerald-600 hover:bg-emerald-100' :
                                                                        validationResults[link] === 'Invalid/Broken' ? 'bg-red-50 border-red-100 text-red-600 hover:bg-red-100' :
                                                                        'bg-white border-slate-100 text-slate-400 hover:border-indigo-300 hover:text-indigo-600'
                                                                    }`}
                                                                    onClick={e => isMissing && e.preventDefault()}
                                                                >
                                                                    {isMissing ? <Trash2 className="w-4 h-4 opacity-50" /> : <FileText className="w-4 h-4" />}
                                                                </a>
                                                                {/* Tooltip */}
                                                                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-900 text-white text-[9px] font-black uppercase tracking-widest rounded-md opacity-0 group-hover/doc:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                                                                    {doc}: {isMissing ? 'Missing' : validationResults[link] || 'Ready'}
                                                                </div>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </td>
                                            <td className="px-6 py-5 text-right pr-12">
                                                <div className="flex items-center justify-end gap-4">
                                                    {getStatusBadge(p.status)}
                                                    {p.status.toLowerCase() !== 'pending' && (
                                                        <button 
                                                            onClick={() => handleResetStatus(p)} 
                                                            className="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                                                            title="Reset Status"
                                                        >
                                                            <RotateCcw className="w-4 h-4" />
                                                        </button>
                                                    )}
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                    {/* Table Footer / Summary */}
                    <div className="bg-slate-50/50 px-8 py-5 border-t border-slate-100 flex items-center justify-between text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
                        <div className="flex items-center gap-6">
                            <span>Total Entries: {filteredAndSortedProjects.length}</span>
                            <span>Selected for Archival: {selectedRows.length}</span>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400"></span> Verified</div>
                            <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-400"></span> Pending</div>
                            <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-red-400"></span> Error</div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default RegistryDashboard;
