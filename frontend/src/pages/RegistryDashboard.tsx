import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { 
  ArrowLeft, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle, 
  Download,
  ChevronDown,
  Search,
  RotateCcw,
  BookOpen,
  Filter,
  CheckSquare,
  Square,
  ChevronUp,
  ChevronRight,
  FilterX
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
    source_code_link: string;
    github_link: string;
    database_link: string;
    readme_link: string;
    status: string;
    academic_year: string;
    latest_version?: number;
    error_message?: string;
}

interface Workbook { id: string; name: string; }

type SortField = 'project_id' | 'project_title' | 'status';
type SortOrder = 'asc' | 'desc';
type StatusFilter = 'All' | 'Failed';

const RegistryDashboard: React.FC = () => {
    const [workbooks, setWorkbooks] = useState<Workbook[]>([]);
    const [selectedWorkbookId, setSelectedWorkbookId] = useState<string>('');
    const [years, setYears] = useState<string[]>([]);
    const [selectedYear, setSelectedYear] = useState<string>('');
    const [projects, setProjects] = useState<Project[]>([]);
    const [availableDocs, setAvailableDocs] = useState<string[]>([]);
    const [selectedRows, setSelectedRows] = useState<number[]>([]);
    const [validationResults, setValidationResults] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState<boolean>(false);
    const [message, setMessage] = useState<{ text: string, type: 'info' | 'error' | 'success' } | null>(null);
    const [isProcessing, setIsProcessing] = useState<boolean>(false);
    
    const [searchQuery, setSearchQuery] = useState<string>('');
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('All');
    const [sortField, setSortField] = useState<SortField>('project_title');
    const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
    const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);

    const [currentPage, setCurrentPage] = useState<number>(1);
    const projectsPerPage = 25;

    useEffect(() => {
        let interval: any;
        if (isProcessing) {
            interval = setInterval(() => {
                fetchProjects(selectedYear, selectedWorkbookId, true);
            }, 5000);
        }
        return () => { if (interval) clearInterval(interval); };
    }, [isProcessing, selectedYear, selectedWorkbookId]);

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
        if (selectedYear && selectedWorkbookId) {
            fetchProjects(selectedYear, selectedWorkbookId);
            setCurrentPage(1);
        }
    }, [selectedYear, selectedWorkbookId]);

    const fetchWorkbooks = async () => {
        const is_prod = window.location.hostname !== 'localhost';
        try {
            const res = await axios.get(`/api/registry/list-sheets`, { withCredentials: true });
            setWorkbooks(res.data);
            if (res.data.length > 0) setSelectedWorkbookId(res.data[0].id);
        } catch (err: any) { 
            console.error("FULL ERROR OBJECT:", err);
            const errorData = err.response?.data;
            const errorMsg = errorData?.error || err.message || "Unknown error";
            
            // Critical debug info
            if (is_prod) {
                const checkUrl = `${window.location.origin}/api/debug-status`;
                alert(`CRITICAL PRODUCTION ERROR\n\nReason: ${errorMsg}\n\n1. Please visit ${checkUrl} in your browser to check system status.\n2. Ensure DATABASE_URL is set in your environment.`);
            }
            
            setMessage({ text: `Failed to fetch workbooks: ${errorMsg}`, type: 'error' }); 
        }
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
            
            // Handle the object format with available_docs
            if (res.data.projects) {
                setProjects(res.data.projects);
                setAvailableDocs(res.data.available_docs || []);
            } else {
                // Fallback for old API versions
                setProjects(Array.isArray(res.data) ? res.data : []);
                setAvailableDocs(['srs', 'sdd', 'spmp', 'std', 'ri', 'source_code', 'github', 'database', 'readme']);
            }

            if (!silent) {
                setSelectedRows([]);
                setValidationResults({});
                setMessage(null);
            }
        } catch (err: any) { 
            if (silent && err.response?.status === 503) return;
            if (!silent) setMessage({ text: "Google Sheets is busy. Still scanning...", type: 'info' }); 
        }
        finally { if (!silent) setLoading(false); }
    };

    const handleSelectRow = (rowIndex: number) => {
        setSelectedRows(prev => prev.includes(rowIndex) ? prev.filter(r => r !== rowIndex) : [...prev, rowIndex]);
    };

    const handleSelectAll = () => {
        const visibleProjectIndices = paginatedProjects.map(p => p.row_index);
        const allVisibleSelected = visibleProjectIndices.every(idx => selectedRows.includes(idx));
        if (allVisibleSelected) {
            setSelectedRows(prev => prev.filter(idx => !visibleProjectIndices.includes(idx)));
        } else {
            setSelectedRows(prev => Array.from(new Set([...prev, ...visibleProjectIndices])));
        }
    };

    const validateLinks = async () => {
        const linksToValidate = projects.flatMap(p => [
            p.srs_link, p.sdd_link, p.spmp_link, p.std_link, p.ri_link,
            p.source_code_link, p.github_link, p.database_link, p.readme_link
        ]).filter(l => l);
        if (linksToValidate.length === 0) return;
        setLoading(true);
        try {
            const res = await axios.post(`/api/registry/validate`, { links: linksToValidate, sheet_id: selectedWorkbookId }, { withCredentials: true });
            setValidationResults(res.data);
            setMessage({ text: "Validation complete.", type: 'success' });
        } catch { setMessage({ text: "Validation failed.", type: 'error' }); }
        finally { setLoading(false); }
    };

    const handleArchive = async () => {
        const selectedProjects = projects.filter(p => selectedRows.includes(p.row_index));
        if (selectedProjects.length === 0) return;
        
        // Instant visual feedback
        setProjects(prev => prev.map(p => 
            selectedRows.includes(p.row_index) ? { ...p, status: 'Processing' } : p
        ));

        setIsProcessing(true);
        setShowConfirmModal(false);
        try {
            await axios.post(`/api/registry/archive`, { projects: selectedProjects, sheet_id: selectedWorkbookId }, { withCredentials: true });
            setMessage({ text: "Archival sequence initiated.", type: 'success' });
            setTimeout(() => fetchProjects(selectedYear, selectedWorkbookId, true), 1000);
        } catch { 
            setMessage({ text: "Archival request failed.", type: 'error' }); 
            setIsProcessing(false);
        }
    };

    const handleReset = async (project: Project) => {
        if (!window.confirm(`Are you sure you want to reset the status of "${project.project_title}" to Pending? This will clear its local file paths in the Registry.`)) return;
        
        setLoading(true);
        try {
            await axios.post(`/api/registry/reset`, { project, sheet_id: selectedWorkbookId }, { withCredentials: true });
            setMessage({ text: "Status reset to Pending.", type: 'success' });
            fetchProjects(selectedYear, selectedWorkbookId);
        } catch {
            setMessage({ text: "Reset failed.", type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortOrder('asc');
        }
        setCurrentPage(1);
    };

    const filteredAndSortedProjects = useMemo(() => {
        return projects
            .filter(p => {
                const matchesSearch = p.project_title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                                     p.project_id.toLowerCase().includes(searchQuery.toLowerCase());
                if (statusFilter === 'All') return matchesSearch;
                // 'Failed' filter now includes both fully failed and partially archived projects
                return matchesSearch && (p.status.toLowerCase() === 'failed' || p.status.toLowerCase() === 'partial');
            })
            .sort((a, b) => {
                const valA = (a[sortField] || '').toString();
                const valB = (b[sortField] || '').toString();
                const comparison = valA.localeCompare(valB, undefined, { numeric: true, sensitivity: 'base' });
                return sortOrder === 'asc' ? comparison : -comparison;
            });
    }, [projects, searchQuery, statusFilter, sortField, sortOrder]);

    const totalPages = Math.ceil(filteredAndSortedProjects.length / projectsPerPage);
    const paginatedProjects = useMemo(() => {
        const startIndex = (currentPage - 1) * projectsPerPage;
        return filteredAndSortedProjects.slice(startIndex, startIndex + projectsPerPage);
    }, [filteredAndSortedProjects, currentPage]);

    const getStatusBadge = (status: string, version?: number, errorMsg?: string) => {
        const s = status.toLowerCase();
        let classes = "bg-gray-100 text-gray-600";
        if (s === 'pending') classes = "bg-amber-100 text-amber-700 ring-1 ring-amber-200";
        if (s === 'archived') classes = "bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200";
        if (s === 'failed') classes = "bg-red-100 text-red-700 ring-1 ring-red-200 cursor-help";
        if (s === 'partial') classes = "bg-orange-100 text-orange-700 ring-1 ring-orange-200 cursor-help";
        if (s === 'processing') classes = "bg-indigo-100 text-indigo-700 animate-pulse ring-1 ring-indigo-200";

        return (
            <div className="group/badge relative inline-block">
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${classes}`}>
                    {status} {version && version > 0 ? `v${version}` : ''}
                </span>
                {(s === 'failed' || s === 'partial') && errorMsg && (
                    <div className="absolute right-0 bottom-full mb-2 hidden group-hover/badge:block w-72 p-3 bg-slate-800 text-white text-[10px] font-medium rounded-xl shadow-2xl z-[60] border border-slate-700 text-left">
                        <div className="flex items-center gap-2 mb-1 text-red-400 font-bold uppercase tracking-tighter">
                            <AlertCircle size={12} /> {s === 'partial' ? 'Partial Success with Errors' : 'Archival Error'}
                        </div>
                        <div className="leading-relaxed whitespace-pre-wrap">
                            {errorMsg}
                        </div>
                        <div className="mt-2 text-slate-400 text-[9px] italic border-t border-slate-700 pt-1">
                            Tip: Check permissions or use direct PDF links for large files.
                        </div>
                    </div>
                )}
            </div>
        );
    };

    const renderSortIcon = (field: SortField) => {
        if (sortField !== field) return <ChevronDown className="w-3 h-3 opacity-20" />;
        return sortOrder === 'asc' ? <ChevronUp className="w-3 h-3 text-indigo-600" /> : <ChevronDown className="w-3 h-3 text-indigo-600" />;
    };

    return (
        <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-900 transition-colors duration-300 overflow-x-hidden">
            {showConfirmModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-white w-full max-w-sm rounded-[2rem] shadow-2xl p-6 space-y-4 animate-in zoom-in-95">
                        <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center mx-auto">
                            <Download className="w-6 h-6" />
                        </div>
                        <div className="text-center space-y-1">
                            <h3 className="text-xl font-black tracking-tight">Confirm Archival</h3>
                            <p className="text-slate-500 text-xs font-medium leading-relaxed">
                                You are about to initiate archival for <span className="text-indigo-600 font-bold">{selectedRows.length} projects</span>.
                            </p>
                        </div>
                        <div className="flex gap-2 pt-2">
                            <button onClick={() => setShowConfirmModal(false)} className="flex-1 py-3 bg-slate-100 hover:bg-slate-200 text-slate-600 text-[10px] font-black rounded-xl transition-all uppercase tracking-widest">Cancel</button>
                            <button onClick={handleArchive} className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-black rounded-xl shadow-lg transition-all uppercase tracking-widest">Start</button>
                        </div>
                    </div>
                </div>
            )}
            
            <header className="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50 transition-all shadow-sm">
                <div className="max-w-[1600px] mx-auto px-6 md:px-12 h-16 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 shrink-0">
                        <button onClick={() => window.location.hash = "dashboard"} className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all">
                            <ArrowLeft className="w-4 h-4" />
                        </button>
                        <div className="h-6 w-px bg-slate-100 hidden sm:block"></div>
                        <div className="flex items-center gap-2">
                            <Logo size={40} />
                            <div className="flex flex-col hidden md:block">
                                <span className="text-lg font-black tracking-tight leading-none">Registry Pipeline</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-1 md:gap-2 bg-slate-50 p-1 rounded-xl border border-slate-200 shrink-0">
                        <div className="flex items-center gap-1">
                            <div className="flex items-center gap-1.5 px-2 border-r border-slate-200 shrink-0">
                                <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                                <span className="text-[10px] font-black text-slate-400 tracking-widest whitespace-nowrap hidden lg:inline uppercase">Workbook</span>
                            </div>
                            <div className="relative shrink-0">
                                <select 
                                    value={selectedWorkbookId} 
                                    onChange={(e) => setSelectedWorkbookId(e.target.value)} 
                                    title={workbooks.find(w => w.id === selectedWorkbookId)?.name}
                                    className="appearance-none bg-white border border-transparent text-slate-900 text-[11px] md:text-xs font-black rounded-lg px-2 md:px-3 py-1.5 pr-8 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all cursor-pointer shadow-sm w-[120px] md:w-[180px] truncate"
                                >
                                    {workbooks.map(w => <option key={w.id} value={w.id} title={w.name}>{w.name}</option>)}
                                </select>
                                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
                            </div>
                        </div>
                        <div className="w-px h-4 bg-slate-200"></div>
                        <div className="flex items-center gap-1">
                            <div className="flex items-center gap-1.5 px-2 border-r border-slate-200 shrink-0">
                                <Filter className="w-3.5 h-3.5 text-slate-400" />
                                <span className="text-[10px] font-black text-slate-400 tracking-widest whitespace-nowrap hidden lg:inline uppercase">Sheet</span>
                            </div>
                            <div className="relative shrink-0">
                                <select 
                                    value={selectedYear} 
                                    onChange={(e) => setSelectedYear(e.target.value)} 
                                    className="appearance-none bg-white border border-transparent text-slate-900 text-[11px] md:text-xs font-black rounded-lg px-2 md:px-3 py-1.5 pr-8 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all cursor-pointer shadow-sm w-[80px] md:w-[120px] truncate"
                                >
                                    {years.map(y => <option key={y} value={y}>{y}</option>)}
                                </select>
                                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-[1600px] mx-auto w-full p-6 md:p-12 space-y-6">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex flex-wrap items-center gap-2">
                        <div className="relative group min-w-[200px] md:min-w-[280px]">
                            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 group-focus-within:text-indigo-600 transition-colors" />
                            <input type="text" placeholder="Search projects..." value={searchQuery} onChange={(e) => {setSearchQuery(e.target.value); setCurrentPage(1);}} className="w-full pl-10 pr-4 py-2 bg-white border border-slate-100 rounded-xl focus:ring-4 focus:ring-indigo-500/5 focus:border-indigo-500 outline-none text-sm font-medium transition-all shadow-sm" />
                        </div>
                        
                        <div className="flex items-center gap-1 bg-white p-1 rounded-xl border border-slate-100 shadow-sm">
                            {(['All', 'Failed'] as StatusFilter[]).map(status => (
                                <button
                                    key={status}
                                    onClick={() => {setStatusFilter(status); setCurrentPage(1);}}
                                    className={`px-4 py-1.5 text-[10px] font-black rounded-lg transition-all ${statusFilter === status ? 'bg-indigo-600 text-white shadow-md shadow-indigo-100' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'}`}
                                >
                                    {status.toUpperCase()}
                                </button>
                            ))}
                        </div>

                        <button onClick={validateLinks} disabled={loading || projects.length === 0} className="px-3 md:px-4 py-2 bg-white border border-indigo-100 text-indigo-600 text-[10px] md:text-xs font-black rounded-xl hover:bg-indigo-50 transition-all flex items-center gap-2 shadow-sm disabled:opacity-50">
                            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> <span className="hidden sm:inline">VALIDATE LINKS</span><span className="sm:hidden">VALIDATE</span>
                        </button>
                    </div>

                    <div className="flex items-center gap-2">
                        <div className="bg-indigo-50 px-3 py-2 rounded-xl border border-indigo-100 flex items-center gap-2.5">
                            <span className="text-[10px] font-black text-indigo-600 uppercase tracking-widest hidden sm:inline">Selected</span>
                            <span className="w-6 h-6 bg-indigo-600 text-white text-[11px] font-black rounded-lg flex items-center justify-center shadow-lg shadow-indigo-100">{selectedRows.length}</span>
                        </div>
                        <button onClick={() => setShowConfirmModal(true)} disabled={isProcessing || selectedRows.length === 0} className="px-5 py-2.5 bg-indigo-600 text-white text-[11px] font-black rounded-xl hover:bg-indigo-700 transition-all flex items-center gap-2 shadow-xl shadow-indigo-100 disabled:opacity-50 uppercase tracking-[0.1em]">
                            <Download className="w-4 h-4" /> Archive
                        </button>
                        <button onClick={() => fetchProjects(selectedYear, selectedWorkbookId)} className="p-2.5 bg-white border border-slate-200 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all shadow-sm">
                            <RotateCcw className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {message && (
                    <div className={`p-3 rounded-2xl border flex items-center justify-between shadow-sm animate-in slide-in-from-top-4 duration-300 ${message.type === 'error' ? 'bg-red-50 border-red-100 text-red-700' : message.type === 'success' ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : 'bg-indigo-50 border-indigo-100 text-indigo-700'}`}>
                        <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 ${message.type === 'error' ? 'bg-red-100' : message.type === 'success' ? 'bg-emerald-100' : 'bg-indigo-100'}`}>
                                {message.type === 'error' ? <AlertCircle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                            </div>
                            <span className="text-sm font-bold truncate">{message.text}</span>
                        </div>
                        <button onClick={() => setMessage(null)} className="text-[10px] font-black uppercase tracking-widest opacity-50 hover:opacity-100 px-4 shrink-0">Dismiss</button>
                    </div>
                )}

                <div className="bg-white rounded-[2.5rem] border border-slate-200 shadow-xl shadow-slate-200/40 overflow-hidden transition-all">
                    <div className="overflow-x-auto custom-scrollbar">
                        <table className="w-full text-left border-collapse min-w-[800px]">
                            <thead>
                                <tr className="bg-slate-50/80 border-b border-slate-100">
                                    <th className="px-6 py-4 w-16 text-center">
                                        <button onClick={handleSelectAll} className="w-5 h-5 mx-auto flex items-center justify-center rounded-lg transition-colors hover:bg-indigo-50 text-indigo-600 border border-slate-200 bg-white">
                                            {paginatedProjects.length > 0 && paginatedProjects.every(p => selectedRows.includes(p.row_index)) ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4 text-slate-200" />}
                                        </button>
                                    </th>
                                    <th onClick={() => handleSort('project_id')} className="px-4 py-4 cursor-pointer group whitespace-nowrap w-32">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] font-black text-slate-400 tracking-[0.2em] uppercase">TEAM CODE</span>
                                            {renderSortIcon('project_id')}
                                        </div>
                                    </th>
                                    <th onClick={() => handleSort('project_title')} className="px-4 py-4 cursor-pointer group min-w-[200px]">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] font-black text-slate-400 tracking-[0.2em] uppercase">Project Title</span>
                                            {renderSortIcon('project_title')}
                                        </div>
                                    </th>
                                    <th className="px-4 py-4 w-[280px]"><span className="text-[10px] font-black text-slate-400 tracking-[0.2em] uppercase">Deliverables</span></th>
                                    <th onClick={() => handleSort('status')} className="px-6 py-4 cursor-pointer group text-right w-40">
                                        <div className="flex items-center justify-end gap-2">
                                            <span className="text-[10px] font-black text-slate-400 tracking-[0.2em] uppercase">Status</span>
                                            {renderSortIcon('status')}
                                        </div>
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50">
                                {loading && projects.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="px-4 py-32">
                                            <div className="flex flex-col items-center gap-3">
                                                <RefreshCw className="w-10 h-10 text-indigo-600 animate-spin" />
                                                <p className="text-slate-400 font-black uppercase tracking-widest text-[10px]">Synchronizing Pipeline...</p>
                                            </div>
                                        </td>
                                    </tr>
                                ) : paginatedProjects.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="px-4 py-32">
                                            <div className="flex flex-col items-center gap-4 max-w-sm mx-auto text-center">
                                                <div className="w-20 h-20 bg-slate-50 rounded-[2rem] flex items-center justify-center text-slate-200 border border-slate-100 shadow-inner">
                                                    <FilterX className="w-10 h-10" />
                                                </div>
                                                <div className="space-y-1">
                                                    <p className="text-slate-900 font-black text-lg tracking-tight">No matching projects found</p>
                                                    <p className="text-slate-400 text-sm font-medium">Try adjusting your filters or adding links to the Google Sheet.</p>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                ) : paginatedProjects.map((p) => {
                                    const isSelected = selectedRows.includes(p.row_index);
                                    return (
                                        <tr key={p.row_index} className={`group transition-all duration-200 ${isSelected ? 'bg-indigo-50/40' : 'hover:bg-slate-50/50'}`}>
                                            <td className="px-6 py-4 text-center">
                                                <button onClick={() => handleSelectRow(p.row_index)} className={`w-5 h-5 mx-auto flex items-center justify-center rounded-lg transition-all border ${isSelected ? 'bg-indigo-600 border-indigo-600 text-white shadow-md' : 'bg-white border-slate-200 text-transparent hover:border-slate-400'}`}>
                                                    <CheckCircle className="w-3.5 h-3.5" />
                                                </button>
                                            </td>
                                            <td className="px-4 py-4"><span className="text-[10px] font-mono font-black text-slate-400 bg-slate-50 px-2 py-1 rounded-lg border border-slate-100">{p.project_id || "ID-?"}</span></td>
                                            <td className="px-4 py-4">
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors tracking-tight line-clamp-1">{p.project_title}</span>
                                                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-0.5">{p.academic_year}</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-4">
                                                <div className="flex flex-wrap items-center gap-1.5 max-w-[400px]">
                                                    {[
                                                        { id: 'srs', label: 'SRS', color: 'blue' },
                                                        { id: 'sdd', label: 'SDD', color: 'purple' },
                                                        { id: 'spmp', label: 'SPMP', color: 'emerald' },
                                                        { id: 'std', label: 'STD', color: 'amber' },
                                                        { id: 'ri', label: 'RI', color: 'rose' },
                                                        { id: 'source_code', label: 'SRC', color: 'orange' },
                                                        { id: 'github', label: 'GH', color: 'slate' },
                                                        { id: 'database', label: 'DB', color: 'cyan' },
                                                        { id: 'readme', label: 'RM', color: 'gray' }
                                                    ].filter(doc => availableDocs.includes(doc.id)).map(doc => {
                                                        const link = p[`${doc.id}_link` as keyof Project] as string;
                                                        const isAccessible = validationResults[link] === 'Accessible';
                                                        const isMissing = !link;
                                                        
                                                        const baseColors: Record<string, string> = {
                                                            blue: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-blue-50 border-blue-100 text-blue-600 hover:bg-blue-100' : 'bg-white border-slate-200 text-slate-400 hover:border-blue-300 hover:text-blue-600',
                                                            purple: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-purple-50 border-purple-100 text-purple-600 hover:bg-purple-100' : 'bg-white border-slate-200 text-slate-400 hover:border-purple-300 hover:text-purple-600',
                                                            emerald: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-emerald-50 border-emerald-100 text-emerald-600 hover:bg-emerald-100' : 'bg-white border-slate-200 text-slate-400 hover:border-emerald-300 hover:text-emerald-600',
                                                            amber: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-amber-50 border-amber-100 text-amber-600 hover:bg-amber-100' : 'bg-white border-slate-200 text-slate-400 hover:border-amber-300 hover:text-amber-600',
                                                            rose: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-rose-50 border-rose-100 text-rose-600 hover:bg-rose-100' : 'bg-white border-slate-200 text-slate-400 hover:border-rose-300 hover:text-rose-600',
                                                            orange: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-orange-50 border-orange-100 text-orange-600 hover:bg-orange-100' : 'bg-white border-slate-200 text-slate-400 hover:border-orange-300 hover:text-orange-600',
                                                            slate: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200' : 'bg-white border-slate-200 text-slate-400 hover:border-slate-300 hover:text-slate-700',
                                                            cyan: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-cyan-50 border-cyan-100 text-cyan-600 hover:bg-cyan-100' : 'bg-white border-slate-200 text-slate-400 hover:border-cyan-300 hover:text-cyan-600',
                                                            gray: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-slate-50 border-slate-100 text-slate-600 hover:bg-slate-100' : 'bg-white border-slate-200 text-slate-400 hover:border-slate-300 hover:text-slate-600'
                                                        };

                                                        return (
                                                            <div key={doc.id} className="relative group/doc">
                                                                <a 
                                                                    href={link || '#'} 
                                                                    target="_blank" 
                                                                    rel="noreferrer" 
                                                                    className={`min-w-[34px] h-7 px-2 flex items-center justify-center rounded-lg border text-[10px] font-black transition-all ${baseColors[doc.color]} ${isMissing ? 'cursor-not-allowed opacity-40' : 'shadow-sm active:scale-95'}`} 
                                                                    onClick={e => isMissing && e.preventDefault()}
                                                                    title={`${doc.label}: ${isMissing ? 'Missing' : isAccessible ? 'Verified' : 'Unverified'}`}
                                                                >
                                                                    {doc.label}
                                                                </a>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-right">
                                                <div className="flex items-center justify-end gap-3 group/status">
                                                    {getStatusBadge(p.status, p.latest_version, p.error_message)}
                                                    {(p.status.toLowerCase() === 'archived' || p.status.toLowerCase() === 'failed' || p.status.toLowerCase() === 'partial') && (
                                                        <button 
                                                            onClick={(e) => { e.stopPropagation(); handleReset(p); }}
                                                            className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all opacity-0 group-hover/status:opacity-100 border border-transparent hover:border-indigo-100 shadow-sm"
                                                            title="Reset Status to Pending"
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
                    <div className="bg-slate-50/50 px-8 py-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
                        <div className="flex items-center gap-6 order-2 sm:order-1">
                            <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-slate-200"></div> TOTAL: {filteredAndSortedProjects.length}</span>
                            <span className="flex items-center gap-2 text-indigo-600"><div className="w-1.5 h-1.5 rounded-full bg-indigo-600"></div> SELECTED: {selectedRows.length}</span>
                        </div>
                        
                        {/* Pagination UI */}
                        <div className="flex items-center gap-2 order-1 sm:order-2">
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

                        <div className="hidden lg:flex items-center gap-4 order-3">
                            <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]"></span> VERIFIED</div>
                            <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)]"></span> PENDING</div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default RegistryDashboard;
