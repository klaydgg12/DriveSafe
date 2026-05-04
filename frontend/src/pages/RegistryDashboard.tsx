import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  ArrowLeft, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle, 
  ExternalLink, 
  Download,
  ChevronDown
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

    // Auto-refresh logic while processing
    useEffect(() => {
        let interval: any;
        if (isProcessing) {
            // Poll every 5 seconds while processing
            interval = setInterval(() => {
                fetchProjects(selectedYear, selectedWorkbookId);
            }, 5000);
        }
        return () => { if (interval) clearInterval(interval); };
    }, [isProcessing, selectedYear, selectedWorkbookId]);

    // Check if processing is actually finished based on project statuses
    useEffect(() => {
        if (isProcessing && projects.length > 0) {
            const stillProcessing = projects.some(p => p.status.toLowerCase() === 'processing');
            if (!stillProcessing) {
                setIsProcessing(false);
                setMessage({ text: "All selected projects have been processed.", type: 'success' });
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

    const fetchProjects = async (year: string, workbookId: string) => {
        setLoading(true);
        try {
            const res = await axios.get(`/api/registry/projects?year=${year}&sheet_id=${workbookId}`, { withCredentials: true });
            setProjects(res.data);
            setSelectedRows([]);
            setValidationResults({});
        } catch { setMessage({ text: "Failed to load projects.", type: 'error' }); }
        finally { setLoading(false); }
    };

    const handleSelectRow = (rowIndex: number) => {
        setSelectedRows(prev => prev.includes(rowIndex) ? prev.filter(r => r !== rowIndex) : [...prev, rowIndex]);
    };

    const handleSelectAll = () => {
        setSelectedRows(selectedRows.length === projects.length ? [] : projects.map(p => p.row_index));
    };

    const validateLinks = async () => {
        const linksToValidate = projects.flatMap(p => [p.srs_link, p.sdd_link, p.spmp_link, p.std_link, p.ri_link]).filter(l => l);
        if (linksToValidate.length === 0) return;
        setLoading(true);
        try {
            const res = await axios.post(`/api/registry/validate`, { links: linksToValidate, sheet_id: selectedWorkbookId }, { withCredentials: true });
            setValidationResults(res.data);
        } catch { setMessage({ text: "Validation failed.", type: 'error' }); }
        finally { setLoading(false); }
    };

    const handleArchive = async () => {
        const selectedProjects = projects.filter(p => selectedRows.includes(p.row_index));
        if (selectedProjects.length === 0) return;
        setIsProcessing(true);
        try {
            await axios.post(`/api/registry/archive`, { projects: selectedProjects, sheet_id: selectedWorkbookId }, { withCredentials: true });
            setMessage({ text: "Archival sequence initiated. Track progress in Sheets.", type: 'success' });
            setTimeout(() => fetchProjects(selectedYear, selectedWorkbookId), 3000);
        } catch { setMessage({ text: "Archival request failed.", type: 'error' }); }
        finally { setIsProcessing(false); }
    };

    const handleResetStatus = async (project: Project) => {
        if (!window.confirm(`Reset status for "${project.project_title}" back to Pending?`)) return;
        try {
            await axios.post(`/api/registry/reset`, { project }, { withCredentials: true });
            setMessage({ text: "Status reset successfully.", type: 'success' });
            fetchProjects(selectedYear, selectedWorkbookId);
        } catch { setMessage({ text: "Failed to reset status.", type: 'error' }); }
    };

    const getStatusBadge = (project: Project) => {
        const base = "px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider";
        const status = project.status.toLowerCase();
        
        let colorClasses = "bg-gray-100 text-gray-600";
        if (status === 'pending') colorClasses = "bg-blue-100 text-blue-700";
        if (status === 'archived') colorClasses = "bg-emerald-100 text-emerald-700";
        if (status === 'failed') colorClasses = "bg-red-100 text-red-700";
        if (status === 'duplicate') colorClasses = "bg-amber-100 text-amber-700";

        return (
            <div className="flex items-center gap-3">
                <span className={`${base} ${colorClasses}`}>{project.status}</span>
                {status !== 'pending' && (
                    <button onClick={() => handleResetStatus(project)} className="text-[10px] font-bold text-gray-400 hover:text-red-500 transition-colors uppercase tracking-tight">
                        Reset
                    </button>
                )}
            </div>
        );
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
            <header className="bg-white border-b border-gray-100 sticky top-0 z-50">
                <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button onClick={() => window.location.hash = "dashboard"} className="p-2 text-gray-400 hover:text-indigo-600 transition-colors">
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div className="h-6 w-px bg-gray-100"></div>
                        <div className="flex items-center gap-2">
                            <Logo size={60} />
                            <span className="text-lg font-bold text-gray-900 tracking-tight ml-1">Capstone Archiver</span>                        </div>
                    </div>

                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Workbook</span>
                            <div className="relative">
                                <select 
                                    value={selectedWorkbookId} 
                                    onChange={(e) => setSelectedWorkbookId(e.target.value)}
                                    className="appearance-none bg-gray-50 border border-gray-200 text-gray-900 text-sm font-bold rounded-xl px-4 py-2 pr-10 focus:ring-2 focus:ring-indigo-500 outline-none transition-all cursor-pointer"
                                >
                                    {workbooks.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                                </select>
                                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Sheet</span>
                            <div className="relative">
                                <select 
                                    value={selectedYear} 
                                    onChange={(e) => setSelectedYear(e.target.value)}
                                    className="appearance-none bg-gray-50 border border-gray-200 text-gray-900 text-sm font-bold rounded-xl px-4 py-2 pr-10 focus:ring-2 focus:ring-indigo-500 outline-none transition-all cursor-pointer"
                                >
                                    {years.map(y => <option key={y} value={y}>{y}</option>)}
                                </select>
                                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            <main className="max-w-[1600px] mx-auto w-full p-6 space-y-6">
                {message && (
                    <div className={`p-4 rounded-2xl border flex items-center justify-between shadow-sm animate-in fade-in slide-in-from-top-2 ${
                        message.type === 'error' ? 'bg-red-50 border-red-100 text-red-700' : 
                        message.type === 'success' ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : 
                        'bg-indigo-50 border-indigo-100 text-indigo-700'
                    }`}>
                        <div className="flex items-center gap-3">
                            {message.type === 'error' ? <AlertCircle className="w-5 h-5" /> : <CheckCircle className="w-5 h-5" />}
                            <span className="text-sm font-bold">{message.text}</span>
                        </div>
                        <button onClick={() => setMessage(null)} className="text-[10px] font-black uppercase tracking-widest opacity-50 hover:opacity-100">Dismiss</button>
                    </div>
                )}

                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <button 
                            onClick={validateLinks} 
                            disabled={loading || projects.length === 0}
                            className="px-6 py-3 bg-white border border-gray-200 text-indigo-600 text-sm font-bold rounded-2xl hover:bg-indigo-50 transition-all flex items-center gap-2 shadow-sm disabled:opacity-50"
                        >
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Validate Links
                        </button>
                        <button 
                            onClick={handleArchive} 
                            disabled={isProcessing || selectedRows.length === 0}
                            className="px-6 py-3 bg-indigo-600 text-white text-sm font-bold rounded-2xl hover:bg-indigo-700 transition-all flex items-center gap-2 shadow-lg shadow-indigo-100 disabled:opacity-50"
                        >
                            <Download className="w-4 h-4" /> Archive Selected ({selectedRows.length})
                        </button>
                    </div>
                    <button onClick={() => fetchProjects(selectedYear, selectedWorkbookId)} className="p-3 text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-2xl transition-all">
                        <RefreshCw className="w-5 h-5" />
                    </button>
                </div>

                <div className="bg-white rounded-3xl border border-gray-100 shadow-xl shadow-gray-200/20 overflow-hidden">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-gray-50/50 border-b border-gray-100">
                                    <th className="px-6 py-4 w-12 text-center">
                                        <input 
                                            type="checkbox" 
                                            checked={selectedRows.length === projects.length && projects.length > 0} 
                                            onChange={handleSelectAll}
                                            className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500"
                                        />
                                    </th>
                                    {['Project ID', 'Title', 'SRS', 'SDD', 'SPMP', 'STD', 'RI', 'Status'].map(h => (
                                        <th key={h} className="px-6 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest">{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {loading && projects.length === 0 ? (
                                    <tr><td colSpan={9} className="px-6 py-20 text-center text-gray-400 font-bold">Reading Registry...</td></tr>
                                ) : projects.length === 0 ? (
                                    <tr><td colSpan={9} className="px-6 py-20 text-center text-gray-400 font-bold">No projects found.</td></tr>
                                ) : projects.map((p) => (
                                    <tr key={p.row_index} className={`hover:bg-gray-50/50 transition-colors group ${selectedRows.includes(p.row_index) ? 'bg-indigo-50/30' : ''}`}>
                                        <td className="px-6 py-4 text-center">
                                            <input 
                                                type="checkbox" 
                                                checked={selectedRows.includes(p.row_index)} 
                                                onChange={() => handleSelectRow(p.row_index)}
                                                className="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500"
                                            />
                                        </td>
                                        <td className="px-6 py-4 text-sm font-mono text-gray-500">{p.project_id || "N/A"}</td>
                                        <td className="px-6 py-4 text-sm font-bold text-gray-900">{p.project_title}</td>
                                        {['srs', 'sdd', 'spmp', 'std', 'ri'].map(doc => (
                                            <td key={doc} className="px-6 py-4">
                                                {p[`${doc}_link` as keyof Project] ? (
                                                    <div className="space-y-1">
                                                        <a href={p[`${doc}_link` as keyof Project] as string} target="_blank" rel="noreferrer" className="text-indigo-600 hover:text-indigo-800 text-xs font-bold flex items-center gap-1">
                                                            <ExternalLink className="w-3 h-3" /> View
                                                        </a>
                                                        {validationResults[p[`${doc}_link` as keyof Project] as string] && (
                                                            <span className={`text-[9px] font-bold uppercase ${validationResults[p[`${doc}_link` as keyof Project] as string] === 'Accessible' ? 'text-emerald-500' : 'text-red-500'}`}>
                                                                {validationResults[p[`${doc}_link` as keyof Project] as string]}
                                                            </span>
                                                        )}
                                                    </div>
                                                ) : <span className="text-gray-300 text-[10px] font-bold">MISSING</span>}
                                            </td>
                                        ))}
                                        <td className="px-6 py-4">{getStatusBadge(p)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default RegistryDashboard;
