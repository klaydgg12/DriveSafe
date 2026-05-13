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
  ChevronRight
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
    
    const [searchQuery, setSearchQuery] = useState<string>('');
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
        const linksToValidate = projects.flatMap(p => [p.srs_link, p.sdd_link, p.spmp_link, p.std_link, p.ri_link]).filter(l => l);
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
            .filter(p => 
                p.project_title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                p.project_id.toLowerCase().includes(searchQuery.toLowerCase())
            )
            .sort((a, b) => {
                const valA = (a[sortField] || '').toString();
                const valB = (b[sortField] || '').toString();
                
                // Natural sort: handles "Team 2" vs "Team 10" correctly
                const comparison = valA.localeCompare(valB, undefined, { numeric: true, sensitivity: 'base' });
                return sortOrder === 'asc' ? comparison : -comparison;
            });
    }, [projects, searchQuery, sortField, sortOrder]);

    const totalPages = Math.ceil(filteredAndSortedProjects.length / projectsPerPage);
    const paginatedProjects = useMemo(() => {
        const startIndex = (currentPage - 1) * projectsPerPage;
        return filteredAndSortedProjects.slice(startIndex, startIndex + projectsPerPage);
    }, [filteredAndSortedProjects, currentPage]);

    const getStatusBadge = (status: string) => {
        const s = status.toLowerCase();
        let classes = "bg-gray-100 text-gray-600";
        if (s === 'pending') classes = "bg-amber-100 text-amber-700 ring-1 ring-amber-200";
        if (s === 'archived') classes = "bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200";
        if (s === 'failed') classes = "bg-red-100 text-red-700 ring-1 ring-red-200";
        if (s === 'processing') classes = "bg-indigo-100 text-indigo-700 animate-pulse ring-1 ring-indigo-200";

        return (
            <span className={`px-2 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${classes}`}>
                {status}
            </span>
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
                            <h3 className="text-xl font-black tracking-tight uppercase">Confirm Archival</h3>
                            <p className="text-slate-500 text-xs font-medium leading-relaxed">
                                You are about to initiate archival for <span className="text-indigo-600 font-bold">{selectedRows.length} projects</span>.
                            </p>
                        </div>
                        <div className="flex gap-2 pt-2">
                            <button onClick={() => setShowConfirmModal(false)} className="flex-1 py-3 bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-bold rounded-xl transition-all">Cancel</button>
                            <button onClick={handleArchive} className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-lg transition-all">Start</button>
                        </div>
                    </div>
                </div>
            )}
            
            <header className="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50 transition-all">
                <div className="max-w-7xl mx-auto px-4 md:px-6 h-16 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 shrink-0">
                        <button onClick={() => window.location.hash = "dashboard"} className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all">
                            <ArrowLeft className="w-4 h-4" />
                        </button>
                        <div className="h-6 w-px bg-slate-100 hidden sm:block"></div>
                        <div className="flex items-center gap-2">
                            <Logo size={44} />
                            <div className="flex flex-col hidden md:block">
                                <span className="text-xl font-black tracking-tight leading-none">Registry</span>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-1 md:gap-2 bg-slate-50 p-1 rounded-xl border border-slate-200 shrink-0">
                        <div className="flex items-center gap-1">
                            <div className="flex items-center gap-1.5 px-2 border-r border-slate-200 shrink-0">
                                <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                                <span className="text-[10px] font-black text-slate-400 tracking-widest whitespace-nowrap hidden lg:inline">Workbook</span>
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
                                <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest whitespace-nowrap hidden lg:inline">Sheet</span>
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

            <main className="max-w-7xl mx-auto w-full p-4 md:p-6 space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex flex-wrap items-center gap-2">
                        <div className="relative group min-w-[200px] md:min-w-[280px]">
                            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 group-focus-within:text-indigo-600 transition-colors" />
                            <input type="text" placeholder="Search..." value={searchQuery} onChange={(e) => {setSearchQuery(e.target.value); setCurrentPage(1);}} className="w-full pl-10 pr-4 py-2 bg-white border border-slate-100 rounded-xl focus:ring-4 focus:ring-indigo-500/5 focus:border-indigo-500 outline-none text-sm font-medium transition-all shadow-sm" />
                        </div>
                        <button onClick={validateLinks} disabled={loading || projects.length === 0} className="px-3 md:px-4 py-2 bg-white border border-indigo-100 text-indigo-600 text-[10px] md:text-xs font-black rounded-xl hover:bg-indigo-50 transition-all flex items-center gap-2 shadow-sm disabled:opacity-50">
                            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> <span className="hidden sm:inline">Validate Links</span><span className="sm:hidden">Validate</span>
                        </button>
                    </div>

                    <div className="flex items-center gap-2">
                        <div className="bg-indigo-50 px-2 md:px-3 py-1.5 rounded-lg border border-indigo-100 flex items-center gap-2">
                            <span className="text-[10px] font-black text-indigo-600 uppercase tracking-widest hidden sm:inline">Selected</span>
                            <span className="w-5 h-5 bg-indigo-600 text-white text-[10px] font-black rounded-md flex items-center justify-center shadow-lg shadow-indigo-200">{selectedRows.length}</span>
                        </div>
                        <button onClick={() => setShowConfirmModal(true)} disabled={isProcessing || selectedRows.length === 0} className="px-4 md:px-6 py-2.5 bg-indigo-600 text-white text-[10px] md:text-xs font-black rounded-xl hover:bg-indigo-700 transition-all flex items-center gap-2 shadow-xl shadow-indigo-100 disabled:opacity-50">
                            <Download className="w-3.5 h-3.5" /> Archive
                        </button>
                        <button onClick={() => fetchProjects(selectedYear, selectedWorkbookId)} className="p-2.5 bg-white border border-slate-200 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-xl transition-all shadow-sm">
                            <RotateCcw className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {message && (
                    <div className={`p-3 rounded-xl border flex items-center justify-between shadow-sm animate-in slide-in-from-top-4 duration-300 ${message.type === 'error' ? 'bg-red-50 border-red-100 text-red-700' : message.type === 'success' ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : 'bg-indigo-50 border-indigo-100 text-indigo-700'}`}>
                        <div className="flex items-center gap-3">
                            <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${message.type === 'error' ? 'bg-red-100' : message.type === 'success' ? 'bg-emerald-100' : 'bg-indigo-100'}`}>
                                {message.type === 'error' ? <AlertCircle className="w-3.5 h-3.5" /> : <CheckCircle className="w-3.5 h-3.5" />}
                            </div>
                            <span className="text-sm font-bold truncate">{message.text}</span>
                        </div>
                        <button onClick={() => setMessage(null)} className="text-[10px] font-black uppercase tracking-widest opacity-50 hover:opacity-100 px-3 shrink-0">Dismiss</button>
                    </div>
                )}

                <div className="bg-white rounded-3xl border border-slate-200 shadow-xl shadow-slate-200/40 overflow-hidden transition-all">
                    <div className="overflow-x-auto custom-scrollbar">
                        <table className="w-full text-left border-collapse min-w-[800px]">
                            <thead>
                                <tr className="bg-slate-50/80 border-b border-slate-100">
                                    <th className="px-4 py-3 w-12 text-center">
                                        <button onClick={handleSelectAll} className="w-4 h-4 mx-auto flex items-center justify-center rounded transition-colors hover:bg-indigo-50 text-indigo-600">
                                            {paginatedProjects.length > 0 && paginatedProjects.every(p => selectedRows.includes(p.row_index)) ? <CheckSquare className="w-3.5 h-3.5" /> : <Square className="w-3.5 h-3.5" />}
                                        </button>
                                    </th>
                                    <th onClick={() => handleSort('project_id')} className="px-4 py-3 cursor-pointer group whitespace-nowrap w-24">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] font-black text-slate-400 tracking-[0.2em]">ID</span>
                                            {renderSortIcon('project_id')}
                                        </div>
                                    </th>
                                    <th onClick={() => handleSort('project_title')} className="px-4 py-3 cursor-pointer group min-w-[200px]">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] font-black text-slate-400 tracking-[0.2em]">Project Title</span>
                                            {renderSortIcon('project_title')}
                                        </div>
                                    </th>
                                    <th className="px-4 py-3 w-[260px]"><span className="text-[10px] font-black text-slate-400 tracking-[0.2em]">Assets</span></th>
                                    <th onClick={() => handleSort('status')} className="px-4 py-3 cursor-pointer group text-right pr-6 md:pr-10 w-32">
                                        <div className="flex items-center justify-end gap-2">
                                            <span className="text-[10px] font-black text-slate-400 tracking-[0.2em]">Status</span>
                                            {renderSortIcon('status')}
                                        </div>
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-50">
                                {loading && projects.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="px-4 py-20">
                                            <div className="flex flex-col items-center gap-2">
                                                <RefreshCw className="w-6 h-6 text-indigo-600 animate-spin" />
                                                <p className="text-slate-400 font-bold uppercase tracking-widest text-xs">Scanning Registry...</p>
                                            </div>
                                        </td>
                                    </tr>
                                ) : paginatedProjects.length === 0 ? (
                                    <tr>
                                        <td colSpan={5} className="px-4 py-20">
                                            <div className="flex flex-col items-center gap-3 max-w-xs mx-auto text-center">
                                                <div className="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center text-slate-300"><Filter className="w-6 h-6" /></div>
                                                <div className="space-y-1">
                                                    <p className="text-slate-900 font-black text-base uppercase tracking-tight">No projects found</p>
                                                    <p className="text-slate-400 text-xs font-medium">Adjust filter or sheet.</p>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                ) : paginatedProjects.map((p) => {
                                    const isSelected = selectedRows.includes(p.row_index);
                                    return (
                                        <tr key={p.row_index} className={`group transition-all duration-200 ${isSelected ? 'bg-indigo-50/30' : 'hover:bg-slate-50/50'}`}>
                                            <td className="px-4 py-2 text-center">
                                                <button onClick={() => handleSelectRow(p.row_index)} className={`w-4 h-4 mx-auto flex items-center justify-center rounded transition-all ${isSelected ? 'text-indigo-600 scale-110' : 'text-slate-200 hover:text-slate-400'}`}>
                                                    {isSelected ? <CheckSquare className="w-3.5 h-3.5" /> : <Square className="w-3.5 h-3.5" />}
                                                </button>
                                            </td>
                                            <td className="px-4 py-2"><span className="text-xs font-mono font-bold text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">{p.project_id || "ID-?"}</span></td>
                                            <td className="px-4 py-2">
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors uppercase tracking-tight line-clamp-1">{p.project_title}</span>
                                                    <span className="text-xs font-medium text-slate-400 uppercase tracking-widest">{p.academic_year}</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-2">
                                                <div className="flex items-center gap-1.5">
                                                    {[
                                                        { id: 'srs', label: 'SRS', color: 'blue' },
                                                        { id: 'sdd', label: 'SDD', color: 'purple' },
                                                        { id: 'spmp', label: 'SPMP', color: 'emerald' },
                                                        { id: 'std', label: 'STD', color: 'amber' },
                                                        { id: 'ri', label: 'RI', color: 'rose' }
                                                    ].map(doc => {
                                                        const link = p[`${doc.id}_link` as keyof Project] as string;
                                                        const isAccessible = validationResults[link] === 'Accessible';
                                                        const isMissing = !link;
                                                        
                                                        // Dynamic color classes based on document type and status
                                                        const baseColors: Record<string, string> = {
                                                            blue: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-blue-50 border-blue-100 text-blue-600 hover:bg-blue-100' : 'bg-white border-slate-200 text-slate-400 hover:border-blue-300 hover:text-blue-600',
                                                            purple: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-purple-50 border-purple-100 text-purple-600 hover:bg-purple-100' : 'bg-white border-slate-200 text-slate-400 hover:border-purple-300 hover:text-purple-600',
                                                            emerald: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-emerald-50 border-emerald-100 text-emerald-600 hover:bg-emerald-100' : 'bg-white border-slate-200 text-slate-400 hover:border-emerald-300 hover:text-emerald-600',
                                                            amber: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-amber-50 border-amber-100 text-amber-600 hover:bg-amber-100' : 'bg-white border-slate-200 text-slate-400 hover:border-amber-300 hover:text-amber-600',
                                                            rose: isMissing ? 'bg-slate-50 border-slate-100 text-slate-300' : isAccessible ? 'bg-rose-50 border-rose-100 text-rose-600 hover:bg-rose-100' : 'bg-white border-slate-200 text-slate-400 hover:border-rose-300 hover:text-rose-600'
                                                        };

                                                        return (
                                                            <div key={doc.id} className="relative group/doc">
                                                                <a 
                                                                    href={link || '#'} 
                                                                    target="_blank" 
                                                                    rel="noreferrer" 
                                                                    className={`min-w-[32px] h-6 px-1.5 flex items-center justify-center rounded-md border text-[10px] font-black transition-all ${baseColors[doc.color]} ${isMissing ? 'cursor-not-allowed opacity-40' : 'shadow-sm active:scale-95'}`} 
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
                                            <td className="px-4 py-2 text-right pr-10">
                                                <div className="flex items-center justify-end gap-3 group/status">
                                                    {getStatusBadge(p.status)}
                                                    {(p.status.toLowerCase() === 'archived' || p.status.toLowerCase() === 'failed') && (
                                                        <button 
                                                            onClick={(e) => { e.stopPropagation(); handleReset(p); }}
                                                            className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all opacity-0 group-hover/status:opacity-100"
                                                            title="Reset Status to Pending"
                                                        >
                                                            <RotateCcw className="w-3.5 h-3.5" />
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
                    <div className="bg-slate-50/50 px-6 py-3 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-black text-slate-400 uppercase tracking-[0.2em]">
                        <div className="flex items-center gap-4 order-2 sm:order-1">
                            <span>Total: {filteredAndSortedProjects.length}</span>
                            <span>Selected: {selectedRows.length}</span>
                        </div>
                        
                        {/* Pagination UI */}
                        <div className="flex items-center gap-2 order-1 sm:order-2">
                            <button 
                                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                                disabled={currentPage === 1}
                                className="p-2 bg-white border border-slate-200 rounded-lg hover:bg-indigo-50 hover:text-indigo-600 transition-all disabled:opacity-30 disabled:hover:bg-white disabled:hover:text-slate-400"
                            >
                                <ArrowLeft className="w-3 h-3" />
                            </button>
                            <div className="px-4 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-900 shadow-sm">
                                PAGE <span className="text-indigo-600">{currentPage}</span> / {totalPages || 1}
                            </div>
                            <button 
                                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                                disabled={currentPage >= totalPages}
                                className="p-2 bg-white border border-slate-200 rounded-lg hover:bg-indigo-50 hover:text-indigo-600 transition-all disabled:opacity-30 disabled:hover:bg-white disabled:hover:text-slate-400"
                            >
                                <ChevronRight className="w-3 h-3" />
                            </button>
                        </div>

                        <div className="hidden lg:flex items-center gap-3 order-3">
                            <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Verified</div>
                            <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span> Pending</div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default RegistryDashboard;

